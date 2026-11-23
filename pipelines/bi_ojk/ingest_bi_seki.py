import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.bi_ojk.scrape_bi_seki import scrape_bi_seki
from pipelines.common.db import get_engine_with_retry, upsert_records

BULAN_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "mei": 5, "jun": 6, "jul": 7,
    "aug": 8, "agu": 8, "sep": 9, "oct": 10,
    "okt": 10, "nov": 11, "dec": 12, "des": 12,
}

UPSERT_SQL = """
    INSERT INTO public.seki_kredit_sektor (
        sheet_asal,
        tahun,
        bulan,
        kelompok_bank,
        kategori_pinjaman,
        sektor_kbli,
        nilai_kredit_miliar_rp,
        created_at
    ) VALUES (
        :sheet_asal,
        :tahun,
        :bulan,
        :kelompok_bank,
        :kategori_pinjaman,
        :sektor_kbli,
        :nilai_kredit_miliar_rp,
        :created_at
    )
    ON CONFLICT (tahun, bulan, kelompok_bank, kategori_pinjaman, sektor_kbli)
    DO UPDATE SET
        sheet_asal = EXCLUDED.sheet_asal,
        nilai_kredit_miliar_rp = EXCLUDED.nilai_kredit_miliar_rp,
        created_at = EXCLUDED.created_at
"""


def find_latest_seki_csv() -> Path:
    candidates = sorted((PROJECT_ROOT / "raw_data").rglob("hasil_seki_bi_*.csv"))
    if not candidates:
        raise FileNotFoundError("File hasil_seki_bi_*.csv tidak ditemukan di raw_data/.")
    return candidates[-1]


def ingest_seki_rows(engine, rows: list[dict]) -> int:
    if not rows:
        print("SEKI BI: Tidak ada data untuk di-UPSERT.")
        return 0

    df = pd.DataFrame(rows)
    df["bulan_num"] = (
        df["Bulan"].astype(str).str.strip().str.lower().str[:3].map(BULAN_MAP)
    )

    if df["bulan_num"].isna().any():
        bad = df.loc[df["bulan_num"].isna(), "Bulan"].unique().tolist()
        raise ValueError(f"Format bulan tidak dikenali: {bad}")

    df = df.drop_duplicates(
        subset=["Tahun", "bulan_num", "Kelompok_Bank", "Kategori_Pinjaman", "Sektor_KBLI"]
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = [
        {
            "sheet_asal": str(r["Sheet_Asal"]).strip() if pd.notna(r["Sheet_Asal"]) else None,
            "tahun": int(r["Tahun"]),
            "bulan": int(r["bulan_num"]),
            "kelompok_bank": str(r["Kelompok_Bank"]).strip(),
            "kategori_pinjaman": str(r["Kategori_Pinjaman"]).strip(),
            "sektor_kbli": str(r["Sektor_KBLI"]).strip(),
            "nilai_kredit_miliar_rp": float(r["Nilai_Kredit_Miliar_Rp"]),
            "created_at": now,
        }
        for _, r in df.iterrows()
    ]

    processed = upsert_records(engine, UPSERT_SQL, records)
    print(f"SEKI BI selesai: {processed} baris diproses (UPSERT) ke seki_kredit_sektor.")
    return processed


def run_bi_seki_pipeline(
    lookback_months: int = 4,
    from_csv: bool = False,
    csv_path: str | None = None,
) -> None:
    """Entrypoint utama (siap dipanggil PythonOperator Airflow maupun CLI)."""
    if from_csv:
        file_path = Path(csv_path) if csv_path else find_latest_seki_csv()
        print(f"Mode CSV -> {file_path}")
        rows = pd.read_csv(file_path, sep=",").to_dict("records")
    else:
        rows = scrape_bi_seki(lookback_months=lookback_months)

    engine = get_engine_with_retry()
    try:
        ingest_seki_rows(engine, rows)
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline BI SEKI in-memory ke Neon DB.")
    parser.add_argument("--lookback-months", type=int, default=4)
    parser.add_argument("--from-csv", action="store_true", help="Fallback baca dari CSV lokal.")
    parser.add_argument("--csv-path", type=str, default=None)
    args = parser.parse_args()

    run_bi_seki_pipeline(
        lookback_months=args.lookback_months,
        from_csv=args.from_csv,
        csv_path=args.csv_path,
    )