import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records
from pipelines.idx.scrape_idx_corp_actions import scrape_idx_corp_actions

UPSERT_SQL = """
    INSERT INTO public.idx_corporate_actions (
        kode_emiten,
        tanggal_pencatatan,
        jenis_tindakan,
        jumlah_saham,
        jumlah_saham_setelah_tindakan,
        created_at
    ) VALUES (
        :kode_emiten,
        :tanggal_pencatatan,
        :jenis_tindakan,
        :jumlah_saham,
        :jumlah_saham_setelah_tindakan,
        :created_at
    )
    ON CONFLICT (kode_emiten, tanggal_pencatatan, jenis_tindakan)
    DO UPDATE SET
        jumlah_saham = EXCLUDED.jumlah_saham,
        jumlah_saham_setelah_tindakan = EXCLUDED.jumlah_saham_setelah_tindakan,
        created_at = EXCLUDED.created_at
"""


def find_csv() -> Path:
    matches = sorted((PROJECT_ROOT / "raw_data").rglob("hasil_idx_corporate_actions*.csv"))
    if not matches:
        raise FileNotFoundError("File hasil_idx_corporate_actions*.csv tidak ditemukan di raw_data/.")
    return matches[-1]


def ingest_corp_action_rows(engine, rows: list[dict]) -> int:
    if not rows:
        print("IDX Corporate Actions: Tidak ada data untuk di-UPSERT.")
        return 0

    df = pd.DataFrame(rows)
    df["TanggalPencatatan"] = pd.to_datetime(df["TanggalPencatatan"], errors="coerce").dt.date
    df = df.dropna(subset=["KodeEmiten", "TanggalPencatatan", "JenisTindakan"])
    df = df.drop_duplicates(subset=["KodeEmiten", "TanggalPencatatan", "JenisTindakan"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = [
        {
            "kode_emiten": str(r["KodeEmiten"]).strip(),
            "tanggal_pencatatan": r["TanggalPencatatan"],
            "jenis_tindakan": str(r["JenisTindakan"]).strip(),
            "jumlah_saham": None if pd.isna(r.get("JumlahSaham")) else float(r["JumlahSaham"]),
            "jumlah_saham_setelah_tindakan": (
                None
                if pd.isna(r.get("JumlahSahamSetelahTindakan"))
                else float(r["JumlahSahamSetelahTindakan"])
            ),
            "created_at": now,
        }
        for _, r in df.iterrows()
    ]

    processed = upsert_records(engine, UPSERT_SQL, records)
    print(f"IDX Corporate Actions selesai: {processed} baris diproses (UPSERT).")
    return processed


def run_idx_corp_actions_pipeline(
    days_back: int = 90,
    from_csv: bool = False,
    csv_path: str | None = None,
) -> None:
    """Entrypoint utama (siap dipanggil PythonOperator Airflow maupun CLI)."""
    if from_csv:
        file_path = Path(csv_path) if csv_path else find_csv()
        print(f"Mode CSV -> {file_path}")
        rows = pd.read_csv(file_path, sep=";").to_dict("records")
    else:
        rows = scrape_idx_corp_actions(days_back=days_back)

    engine = get_engine_with_retry()
    try:
        ingest_corp_action_rows(engine, rows)
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline IDX Corporate Actions in-memory ke Neon DB.")
    parser.add_argument("--days-back", type=int, default=90)
    parser.add_argument("--from-csv", action="store_true", help="Fallback baca dari CSV lokal.")
    parser.add_argument("--csv-path", type=str, default=None)
    args = parser.parse_args()

    run_idx_corp_actions_pipeline(
        days_back=args.days_back,
        from_csv=args.from_csv,
        csv_path=args.csv_path,
    )