from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records  # noqa: E402


TABLE_CONFIGS: list[dict[str, Any]] = [
    {
        "table": "bps_observations",
        "file": "bps_adhb_adhk_observations_normalized.csv",
        "columns": [
            "source", "domain", "subject", "vervar_id", "vervar_label",
            "variable_id", "variable_label", "turvar_id", "turvar_label",
            "period_id", "period_label", "subperiod_id", "subperiod_label",
            "value", "unit", "last_update", "datacontent_key", "decode_status",
            "year", "frequency", "quarter", "category_type", "sector_group",
            "is_aggregate", "aggregation_method", "price_basis",
        ],
        "integer_fields": {
            "domain", "vervar_id", "variable_id", "turvar_id", "period_id",
            "period_label", "subperiod_id", "datacontent_key", "year",
        },
        "decimal_fields": {"value"},
        "boolean_fields": {"is_aggregate"},
        "nullable_fields": {"quarter"},
        "unique_key": [
            "price_basis", "variable_id", "period_id", "vervar_id",
            "turvar_id", "subperiod_id",
        ],
    },
    {
        "table": "bps_sector_timeseries",
        "file": "bps_adhb_adhk_sector_timeseries.csv",
        "columns": [
            "source", "source_variable_id", "source_variable_label", "domain",
            "subject", "year", "period_id", "frequency", "subperiod_id",
            "subperiod_label", "quarter", "vervar_id", "vervar_label",
            "series_name", "sector_group", "value", "unit", "is_aggregate",
            "aggregation_method", "source_record_count", "source_category_ids",
            "source_datacontent_keys", "last_update", "price_basis",
        ],
        "integer_fields": {
            "source_variable_id", "domain", "year", "period_id", "subperiod_id",
            "vervar_id", "source_record_count",
        },
        "decimal_fields": {"value"},
        "boolean_fields": {"is_aggregate"},
        "nullable_fields": {"quarter"},
        "unique_key": [
            "price_basis", "source_variable_id", "period_id", "subperiod_id",
            "vervar_id", "series_name",
        ],
    },
    {
        "table": "bps_pdrb_reconciliation",
        "file": "bps_adhb_adhk_2026_reconciliation.csv",
        "columns": [
            "year", "period_id", "subperiod_id", "subperiod_label", "quarter",
            "vervar_id", "vervar_label", "unit", "published_pdrb_total",
            "sum_of_17_industries", "difference_total_minus_industries",
            "review_tolerance_miliar", "within_review_tolerance", "price_basis",
        ],
        "integer_fields": {"year", "period_id", "subperiod_id", "vervar_id"},
        "decimal_fields": {
            "published_pdrb_total", "sum_of_17_industries",
            "difference_total_minus_industries", "review_tolerance_miliar",
        },
        "boolean_fields": {"within_review_tolerance"},
        "nullable_fields": set(),
        "unique_key": ["price_basis", "period_id", "subperiod_id", "vervar_id"],
    },
]


def parse_bool(value: str, column: str, row_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Baris {row_number}: nilai boolean tidak valid pada {column}: {value!r}")


def convert_value(value: str, column: str, config: dict[str, Any], row_number: int) -> Any:
    if value == "" and column in config["nullable_fields"]:
        return None
    if column in config["integer_fields"]:
        try:
            numeric_value = Decimal(value.strip())
            if numeric_value != numeric_value.to_integral_value():
                raise ValueError
            return int(numeric_value)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Baris {row_number}: integer tidak valid pada {column}: {value!r}")
    if column in config["decimal_fields"]:
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            raise ValueError(f"Baris {row_number}: angka desimal tidak valid pada {column}: {value!r}")
    if column in config["boolean_fields"]:
        return parse_bool(value, column, row_number)
    return value


def load_csv_records(csv_path: Path, config: dict[str, Any], limit: int | None) -> list[dict[str, Any]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"File tidak ditemukan: {csv_path}")

    frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [column for column in config["columns"] if column not in frame.columns]
    if missing:
        raise ValueError(f"{csv_path.name}: kolom wajib tidak ditemukan: {missing}")
    if limit is not None:
        frame = frame.head(limit)

    records: list[dict[str, Any]] = []
    for row_number, row in enumerate(frame[config["columns"]].to_dict(orient="records"), start=2):
        records.append({
            column: convert_value(value, column, config, row_number)
            for column, value in row.items()
        })

    keys = config["unique_key"]
    key_tuples = [tuple(record[key] for key in keys) for record in records]
    if len(key_tuples) != len(set(key_tuples)):
        raise ValueError(
            f"{csv_path.name}: ditemukan duplicate natural key untuk {config['table']}. "
            "Loader dihentikan agar konflik data tidak tertimpa tanpa pemeriksaan."
        )
    return records


def build_upsert_sql(config: dict[str, Any]) -> str:
    columns = config["columns"]
    keys = config["unique_key"]
    column_sql = ", ".join(columns)
    value_sql = ", ".join(f":{column}" for column in columns)
    update_columns = [column for column in columns if column not in keys]
    update_sql = ",\n        ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    key_sql = ", ".join(keys)
    return (
        f"INSERT INTO public.{config['table']} ({column_sql})\n"
        f"VALUES ({value_sql})\n"
        f"ON CONFLICT ({key_sql}) DO UPDATE SET\n        {update_sql}"
    )


def get_row_count(engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT COUNT(*) FROM public.{table}")).scalar_one())


def main() -> int:
    parser = argparse.ArgumentParser(description="Load hasil transformasi BPS ke Neon menggunakan shared DB helper.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "raw_data" / "bps",
        help="Folder CSV BPS (default: raw_data/bps).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah baris per tabel untuk smoke test.")
    parser.add_argument("--dry-run", action="store_true", help="Validasi file dan mapping tanpa koneksi database.")
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit harus lebih besar dari 0")

    print("=" * 72)
    print("BPS → NEON DATABASE LOADER")
    print(f"Input directory : {args.input_dir.resolve()}")
    print(f"Dry run         : {args.dry_run}")
    print(f"Limit/table     : {args.limit if args.limit else 'Tidak dibatasi'}")
    print("=" * 72)

    prepared: list[tuple[dict[str, Any], list[dict[str, Any]], str]] = []
    for config in TABLE_CONFIGS:
        csv_path = args.input_dir / config["file"]
        records = load_csv_records(csv_path, config, args.limit)
        sql = build_upsert_sql(config)
        prepared.append((config, records, sql))
        print(f"[READY] {config['table']}: {len(records):,} records | {len(config['columns'])} columns")
        print(f"        Unique key: {', '.join(config['unique_key'])}")

    if args.dry_run:
        print("\nDRY RUN BERHASIL. Tidak ada koneksi atau perubahan ke Neon DB.")
        return 0

    engine = get_engine_with_retry()
    try:
        for config, records, sql in prepared:
            table = config["table"]
            before = get_row_count(engine, table)
            processed = upsert_records(engine, sql, records, chunk_size=500)
            after = get_row_count(engine, table)
            print(f"\n[UPSERT] {table}")
            print(f"  Records diproses : {processed:,}")
            print(f"  Rows sebelum     : {before:,}")
            print(f"  Rows sesudah     : {after:,}")
            print(f"  Perubahan jumlah : {after - before:+,}")
        print("\nBPS LOAD SELESAI.")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
