import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records

UPSERT_PENGUMUMAN_SQL = """
    INSERT INTO public.ojk_pengumuman (
        tanggal_rilis,
        judul,
        link_halaman,
        isi_teks,
        link_lampiran,
        created_at
    ) VALUES (
        :tanggal_rilis,
        :judul,
        :link_halaman,
        :isi_teks,
        :link_lampiran,
        :created_at
    )
    ON CONFLICT (link_halaman)
    DO UPDATE SET
        tanggal_rilis = EXCLUDED.tanggal_rilis,
        judul = EXCLUDED.judul,
        isi_teks = EXCLUDED.isi_teks,
        link_lampiran = EXCLUDED.link_lampiran,
        created_at = EXCLUDED.created_at
"""

UPSERT_REGULASI_SQL = """
    INSERT INTO public.ojk_rancangan_regulasi (
        satker,
        tanggal_rilis,
        judul,
        link_halaman,
        isi_teks,
        link_lampiran,
        created_at
    ) VALUES (
        :satker,
        :tanggal_rilis,
        :judul,
        :link_halaman,
        :isi_teks,
        :link_lampiran,
        :created_at
    )
    ON CONFLICT (link_halaman)
    DO UPDATE SET
        satker = EXCLUDED.satker,
        tanggal_rilis = EXCLUDED.tanggal_rilis,
        judul = EXCLUDED.judul,
        isi_teks = EXCLUDED.isi_teks,
        link_lampiran = EXCLUDED.link_lampiran,
        created_at = EXCLUDED.created_at
"""


def clean_str(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def parse_pengumuman_date(val):
    s = clean_str(val)
    if not s:
        return None
    dt = pd.to_datetime(s, errors="coerce")
    return dt.date() if pd.notna(dt) else None


def parse_regulasi_satker_date(val):
    """Memecah 'PVML 10/9/2026' -> ('PVML', date(2026, 10, 9))."""
    s = clean_str(val)
    if not s:
        return None, None
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})$", s)
    if match:
        date_str = match.group(1)
        satker = s[: match.start()].strip() or None
        dt = pd.to_datetime(date_str, format="%m/%d/%Y", errors="coerce")
        return satker, (dt.date() if pd.notna(dt) else None)
    dt = pd.to_datetime(s, errors="coerce")
    return None, (dt.date() if pd.notna(dt) else None)


def find_csv(filename: str) -> Path:
    matches = sorted((PROJECT_ROOT / "raw_data").rglob(filename))
    if not matches:
        raise FileNotFoundError(f"File {filename} tidak ditemukan di raw_data/.")
    return matches[-1]


def ingest_pengumuman(engine, file_path: Path) -> None:
    print(f"Membaca OJK Pengumuman: {file_path}")
    df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig")
    df = df.dropna(subset=["link"]).drop_duplicates(subset=["link"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = [
        {
            "tanggal_rilis": parse_pengumuman_date(r.get("tanggal_rilis")),
            "judul": clean_str(r.get("judul")) or "",
            "link_halaman": clean_str(r.get("link")),
            "isi_teks": clean_str(r.get("isi_teks")),
            "link_lampiran": clean_str(r.get("link_dokumen_lampiran")),
            "created_at": now,
        }
        for _, r in df.iterrows()
    ]

    processed = upsert_records(engine, UPSERT_PENGUMUMAN_SQL, records)
    print(f"OJK Pengumuman selesai: {processed} baris diproses (UPSERT).")


def ingest_rancangan_regulasi(engine, file_path: Path) -> None:
    print(f"Membaca OJK Rancangan Regulasi: {file_path}")
    df = pd.read_csv(file_path, sep=";", encoding="utf-8-sig")
    df = df.dropna(subset=["link"]).drop_duplicates(subset=["link"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = []
    for _, r in df.iterrows():
        satker, tgl = parse_regulasi_satker_date(r.get("tanggal_rilis"))
        records.append(
            {
                "satker": satker,
                "tanggal_rilis": tgl,
                "judul": clean_str(r.get("judul")) or "",
                "link_halaman": clean_str(r.get("link")),
                "isi_teks": clean_str(r.get("isi_teks")),
                "link_lampiran": clean_str(r.get("link_dokumen_lampiran")),
                "created_at": now,
            }
        )

    processed = upsert_records(engine, UPSERT_REGULASI_SQL, records)
    print(f"OJK Rancangan Regulasi selesai: {processed} baris diproses (UPSERT).")


def main(pengumuman_path: str | None = None, regulasi_path: str | None = None) -> None:
    p_path = Path(pengumuman_path) if pengumuman_path else find_csv("ojk_pengumuman_raw.csv")
    r_path = Path(regulasi_path) if regulasi_path else find_csv("ojk_rancangan_regulasi_raw.csv")

    engine = get_engine_with_retry()
    try:
        ingest_pengumuman(engine, p_path)
        ingest_rancangan_regulasi(engine, r_path)
    finally:
        engine.dispose()


if __name__ == "__main__":
    p_arg = sys.argv[1] if len(sys.argv) > 1 else None
    r_arg = sys.argv[2] if len(sys.argv) > 2 else None
    main(p_arg, r_arg)