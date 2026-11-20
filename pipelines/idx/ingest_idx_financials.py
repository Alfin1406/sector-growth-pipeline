import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records

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
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def clean_num(val):
    return None if pd.isna(val) else float(val)


def find_csv() -> Path:
    matches = sorted((PROJECT_ROOT / "raw_data").rglob("financial_data_clean_ready*.csv"))
    if not matches:
        raise FileNotFoundError("File financial_data_clean_ready*.csv tidak ditemukan di raw_data/.")
    return matches[-1]


def main(csv_path: str | None = None) -> None:
    file_path = Path(csv_path) if csv_path else find_csv()
    print(f"Membaca IDX Financials: {file_path}")

    df = pd.read_csv(file_path, sep=";")
    df["Tanggal_Laporan"] = pd.to_datetime(df["Tanggal_Laporan"], errors="coerce").dt.date
    df = df.drop_duplicates(subset=["KodeEmiten", "Tahun", "Periode"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = [
        {
            "kode_emiten": clean_str(r["KodeEmiten"]),
            "nama_perusahaan": clean_str(r["Nama_Entitas"]),
            "sektor": clean_str(r.get("Sektor")),
            "subsektor": clean_str(r.get("Subsektor")),
            "industri": clean_str(r.get("Industri")),
            "subindustri": clean_str(r.get("Subindustri")),
            "tanggal_laporan": r["Tanggal_Laporan"] if pd.notna(r["Tanggal_Laporan"]) else None,
            "tahun": int(r["Tahun"]),
            "kuartal": clean_str(r["Periode"]),
            "mata_uang": clean_str(r["Mata_Uang"]),
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
        for _, r in df.iterrows()
    ]

    engine = get_engine_with_retry()
    try:
        processed = upsert_records(engine, UPSERT_SQL, records)
        print(f"IDX Financials selesai: {processed} baris diproses (UPSERT).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg_path)