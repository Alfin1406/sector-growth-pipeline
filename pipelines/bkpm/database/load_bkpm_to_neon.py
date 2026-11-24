from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = next(
    (
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "pipelines" / "common" / "db.py").is_file()
    ),
    None,
)

if PROJECT_ROOT is None:
    raise RuntimeError("Root repository tidak ditemukan: pipelines/common/db.py tidak tersedia.")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records  # noqa: E402


TABLE = "bkpm_investments"
CSV_FILE = "bkpm_2026_combined.csv"
DB_COLUMNS = [
    "periode", "status_penanaman_modal", "regional", "negara", "sektor_utama",
    "nama_sektor", "deskripsi_kbli_2digit", "provinsi", "kabupaten_kota",
    "jawa_luar_jawa", "pulau", "investasi_rp_juta", "investasi_us_ribu", "tki",
]
EXTRA_COLUMNS = ["source_quarter", "tki_negative_flag"]
DECIMAL_FIELDS = {"investasi_rp_juta", "investasi_us_ribu"}
INTEGER_FIELDS = {"tki"}
UNIQUE_KEY = [
    "periode", "status_penanaman_modal", "regional", "negara", "sektor_utama",
    "nama_sektor", "deskripsi_kbli_2digit", "provinsi", "kabupaten_kota",
    "jawa_luar_jawa", "pulau",
]


def load_records(csv_path: Path, limit: int | None) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"File tidak ditemukan: {csv_path}")

    frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = DB_COLUMNS + EXTRA_COLUMNS
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan pada {csv_path.name}: {missing}")
    if limit is not None:
        frame = frame.head(limit).copy()

    records: list[dict[str, Any]] = []
    for row_number, row in enumerate(frame[DB_COLUMNS].to_dict(orient="records"), start=2):
        record: dict[str, Any] = {}
        for column, value in row.items():
            value = value.strip() if isinstance(value, str) else value
            if column in DECIMAL_FIELDS:
                try:
                    record[column] = Decimal(value)
                except InvalidOperation:
                    raise ValueError(f"Baris {row_number}: nilai desimal tidak valid pada {column}: {value!r}")
            elif column in INTEGER_FIELDS:
                try:
                    numeric_value = Decimal(value)
                    if numeric_value != numeric_value.to_integral_value():
                        raise ValueError
                    record[column] = int(numeric_value)
                except (InvalidOperation, ValueError):
                    raise ValueError(f"Baris {row_number}: nilai integer tidak valid pada {column}: {value!r}")
            else:
                # Kolom teks pada model bersifat nullable=False; string kosong dipertahankan sebagai ''.
                record[column] = value
        records.append(record)

    key_tuples = [tuple(record[key] for key in UNIQUE_KEY) for record in records]
    if len(key_tuples) != len(set(key_tuples)):
        raise ValueError(
            "Ditemukan duplicate natural key pada CSV BKPM sesuai uq_bkpm_investment_natural_key. "
            "Loader dihentikan agar konflik tidak tertimpa tanpa pemeriksaan."
        )

    return records, frame


def build_upsert_sql() -> str:
    column_sql = ", ".join(DB_COLUMNS)
    value_sql = ", ".join(f":{column}" for column in DB_COLUMNS)
    key_sql = ", ".join(UNIQUE_KEY)
    update_columns = [column for column in DB_COLUMNS if column not in UNIQUE_KEY]
    update_sql = ",\n        ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return (
        f"INSERT INTO public.{TABLE} ({column_sql})\n"
        f"VALUES ({value_sql})\n"
        f"ON CONFLICT ({key_sql}) DO UPDATE SET\n        {update_sql}"
    )


def get_row_count(engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT COUNT(*) FROM public.{TABLE}")).scalar_one())


def main() -> int:
    parser = argparse.ArgumentParser(description="Load BKPM 2026 combined CSV ke Neon menggunakan shared DB helper.")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=PROJECT_ROOT / "raw_data" / "bkpm" / CSV_FILE,
        help="Path CSV BKPM (default: raw_data/bkpm/bkpm_2026_combined.csv).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah baris untuk smoke test.")
    parser.add_argument("--dry-run", action="store_true", help="Validasi file dan mapping tanpa koneksi database.")
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit harus lebih besar dari 0")

    print("=" * 72)
    print("BKPM → NEON DATABASE LOADER")
    print(f"Input file  : {args.input_file.resolve()}")
    print(f"Dry run     : {args.dry_run}")
    print(f"Limit       : {args.limit if args.limit else 'Tidak dibatasi'}")
    print("=" * 72)

    records, frame = load_records(args.input_file, args.limit)
    flagged_count = 0
    if "tki_negative_flag" in frame.columns:
        flagged_count = sum(value.strip().lower() in {"true", "1", "yes", "y"} for value in frame["tki_negative_flag"])
    source_distribution = frame["source_quarter"].value_counts(dropna=False).to_dict()

    print(f"[READY] {TABLE}: {len(records):,} records | {len(DB_COLUMNS)} kolom database")
    print(f"[INFO] Kolom lokal yang tidak ada pada model DB: {', '.join(EXTRA_COLUMNS)}")
    print(f"[INFO] Baris ditandai tki_negative_flag: {flagged_count:,}")
    print(f"[INFO] Distribusi source_quarter: {source_distribution}")
    print(f"[INFO] Unique key: {', '.join(UNIQUE_KEY)}")

    if args.dry_run:
        print("\nDRY RUN BERHASIL. Tidak ada koneksi atau perubahan ke Neon DB.")
        return 0

    engine = get_engine_with_retry()
    try:
        before = get_row_count(engine)
        processed = upsert_records(engine, build_upsert_sql(), records, chunk_size=500)
        after = get_row_count(engine)
        print(f"\n[UPSERT] {TABLE}")
        print(f"  Records diproses : {processed:,}")
        print(f"  Rows sebelum     : {before:,}")
        print(f"  Rows sesudah     : {after:,}")
        print(f"  Perubahan jumlah : {after - before:+,}")
        print("\nBKPM LOAD SELESAI.")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
