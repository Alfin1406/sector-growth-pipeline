import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records
from pipelines.idx.scrape_idx_financials import (
    PERIODE_TO_KUARTAL,
    scrape_idx_financials,
)

UPSERT_SQL = """
    INSERT INTO public.idx_financial_statements (
        kode_emiten,
        nama_perusahaan,
        sektor,
        subsektor,
        industri,
        subindustri,
        tanggal_laporan,
        tahun,
        kuartal,
        mata_uang,
        cash_current,
        cash_prior,
        total_asset_current,
        total_asset_prior,
        total_liabilitas_current,
        total_liabilitas_prior,
        total_ekuitas_current,
        total_ekuitas_prior,
        link_sumber,
        created_at
    ) VALUES (
        :kode_emiten,
        :nama_perusahaan,
        :sektor,
        :subsektor,
        :industri,
        :subindustri,
        :tanggal_laporan,
        :tahun,
        :kuartal,
        :mata_uang,
        :cash_current,
        :cash_prior,
        :total_asset_current,
        :total_asset_prior,
        :total_liabilitas_current,
        :total_liabilitas_prior,
        :total_ekuitas_current,
        :total_ekuitas_prior,
        :link_sumber,
        :created_at
    )
    ON CONFLICT (kode_emiten, tahun, kuartal)
    DO UPDATE SET
        nama_perusahaan = EXCLUDED.nama_perusahaan,
        sektor = EXCLUDED.sektor,
        subsektor = EXCLUDED.subsektor,
        industri = EXCLUDED.industri,
        subindustri = EXCLUDED.subindustri,
        tanggal_laporan = EXCLUDED.tanggal_laporan,
        mata_uang = EXCLUDED.mata_uang,
        cash_current = EXCLUDED.cash_current,
        cash_prior = EXCLUDED.cash_prior,
        total_asset_current = EXCLUDED.total_asset_current,
        total_asset_prior = EXCLUDED.total_asset_prior,
        total_liabilitas_current = EXCLUDED.total_liabilitas_current,
        total_liabilitas_prior = EXCLUDED.total_liabilitas_prior,
        total_ekuitas_current = EXCLUDED.total_ekuitas_current,
        total_ekuitas_prior = EXCLUDED.total_ekuitas_prior,
        link_sumber = EXCLUDED.link_sumber,
        created_at = EXCLUDED.created_at
"""


def clean_str(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s else None


def clean_num(val):
    if val is None or pd.isna(val):
        return None
    return float(val)


def clean_date(val):
    if val is None or pd.isna(val):
        return None
    dt = pd.to_datetime(val, errors="coerce")
    return dt.date() if pd.notna(dt) else None


def find_csv() -> Path:
    matches = sorted((PROJECT_ROOT / "raw_data").rglob("financial_data_clean_ready*.csv"))
    if not matches:
        raise FileNotFoundError("File financial_data_clean_ready*.csv tidak ditemukan di raw_data/.")
    return matches[-1]


def get_existing_emiten(engine, tahun: int, kuartal: str) -> set[str]:
    """Mengambil daftar kode_emiten yang sudah ada di DB untuk resume tanpa CSV lokal."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT kode_emiten FROM public.idx_financial_statements "
                "WHERE tahun = :tahun AND kuartal = :kuartal"
            ),
            {"tahun": tahun, "kuartal": kuartal},
        ).fetchall()
    return {r[0] for r in rows if r[0]}


def ingest_financial_rows(engine, rows: list[dict]) -> int:
    if not rows:
        return 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seen = set()
    records = []

    for r in rows:
        key = (clean_str(r.get("KodeEmiten")), int(r["Tahun"]), clean_str(r.get("Periode")))
        if not key[0] or key in seen:
            continue
        seen.add(key)

        records.append(
            {
                "kode_emiten": key[0],
                "nama_perusahaan": clean_str(r.get("Nama_Entitas")),
                "sektor": clean_str(r.get("Sektor")),
                "subsektor": clean_str(r.get("Subsektor")),
                "industri": clean_str(r.get("Industri")),
                "subindustri": clean_str(r.get("Subindustri")),
                "tanggal_laporan": clean_date(r.get("Tanggal_Laporan")),
                "tahun": key[1],
                "kuartal": key[2],
                "mata_uang": clean_str(r.get("Mata_Uang")),
                "cash_current": clean_num(r.get("Kas_CurrentYear")),
                "cash_prior": clean_num(r.get("Kas_PriorYear")),
                "total_asset_current": clean_num(r.get("TotalAset_CurrentYear")),
                "total_asset_prior": clean_num(r.get("TotalAset_PriorYear")),
                "total_liabilitas_current": clean_num(r.get("TotalLiabilitas_CurrentYear")),
                "total_liabilitas_prior": clean_num(r.get("TotalLiabilitas_PriorYear")),
                "total_ekuitas_current": clean_num(r.get("TotalEkuitas_CurrentYear")),
                "total_ekuitas_prior": clean_num(r.get("TotalEkuitas_PriorYear")),
                "link_sumber": clean_str(r.get("Link_Sumber")),
                "created_at": now,
            }
        )

    processed = upsert_records(engine, UPSERT_SQL, records)
    print(f"    -> Batch UPSERT selesai: {processed} baris diproses.")
    return processed


def run_idx_financials_pipeline(
    year: int = 2026,
    periode: str = "TW1",
    limit: int | None = None,
    force_refresh: bool = False,
    from_csv: bool = False,
    csv_path: str | None = None,
) -> None:
    """Entrypoint utama (siap dipanggil PythonOperator Airflow maupun CLI)."""
    engine = get_engine_with_retry()
    try:
        if from_csv:
            file_path = Path(csv_path) if csv_path else find_csv()
            print(f"Mode CSV -> {file_path}")
            rows = pd.read_csv(file_path, sep=";").to_dict("records")
            total = ingest_financial_rows(engine, rows)
            print(f"IDX Financials (CSV) selesai: {total} baris diproses.")
            return

        kuartal = PERIODE_TO_KUARTAL.get(periode, periode)
        existing = set() if force_refresh else get_existing_emiten(engine, year, kuartal)
        print(f"Existing di Neon DB ({year} {kuartal}): {len(existing)} emiten.")

        total_upserted = 0

        def _flush_batch(batch: list[dict]) -> None:
            nonlocal total_upserted
            total_upserted += ingest_financial_rows(engine, batch)

        scrape_idx_financials(
            year=year,
            periode=periode,
            existing_emiten=existing,
            limit=limit,
            batch_size=25,
            on_batch=_flush_batch,
        )
        print(f"IDX Financials pipeline selesai: total {total_upserted} baris diproses (UPSERT).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline IDX Financials in-memory ke Neon DB.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--periode", type=str, default="TW1", choices=["TW1", "TW2", "TW3", "audit"])
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah emiten untuk tes cepat.")
    parser.add_argument("--force-refresh", action="store_true", help="Tarik ulang semua emiten meski sudah ada di DB.")
    parser.add_argument("--from-csv", action="store_true", help="Fallback baca dari CSV lokal.")
    parser.add_argument("--csv-path", type=str, default=None)
    args = parser.parse_args()

    run_idx_financials_pipeline(
        year=args.year,
        periode=args.periode,
        limit=args.limit,
        force_refresh=args.force_refresh,
        from_csv=args.from_csv,
        csv_path=args.csv_path,
    )