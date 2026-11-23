import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records

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


def main(csv_path: str | None = None) -> None:
    file_path = Path(csv_path) if csv_path else find_csv()
    print(f"Membaca IDX Corporate Actions: {file_path}")

    df = pd.read_csv(file_path, sep=";")
    df["TanggalPencatatan"] = pd.to_datetime(df["TanggalPencatatan"], errors="coerce").dt.date
    df = df.dropna(subset=["KodeEmiten", "TanggalPencatatan", "JenisTindakan"])
    df = df.drop_duplicates(subset=["KodeEmiten", "TanggalPencatatan", "JenisTindakan"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = [
        {
            "kode_emiten": str(r["KodeEmiten"]).strip(),
            "tanggal_pencatatan": r["TanggalPencatatan"],
            "jenis_tindakan": str(r["JenisTindakan"]).strip(),
            "jumlah_saham": None if pd.isna(r["JumlahSaham"]) else float(r["JumlahSaham"]),
            "jumlah_saham_setelah_tindakan": (
                None
                if pd.isna(r["JumlahSahamSetelahTindakan"])
                else float(r["JumlahSahamSetelahTindakan"])
            ),
            "created_at": now,
        }
        for _, r in df.iterrows()
    ]

    engine = get_engine_with_retry()
    try:
        processed = upsert_records(engine, UPSERT_SQL, records)
        print(f"IDX Corporate Actions selesai: {processed} baris diproses (UPSERT).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg_path)