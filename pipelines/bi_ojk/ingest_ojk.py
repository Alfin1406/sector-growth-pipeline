import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.bi_ojk.scrape_ojk import scrape_all_ojk
from pipelines.common.db import get_engine_with_retry, upsert_records

INDO_MONTHS = {
    "januari": "January",
    "februari": "February",
    "maret": "March",
    "april": "April",
    "mei": "May",
    "juni": "June",
    "juli": "July",
    "agustus": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "desember": "December",
}

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
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s else None


def _normalize_indo_months(date_str: str) -> str:
    result = date_str
    for id_month, en_month in INDO_MONTHS.items():
        result = re.sub(rf"\b{id_month}\b", en_month, result, flags=re.IGNORECASE)
    return result


def parse_pengumuman_date(val):
    s = clean_str(val)
    if not s:
        return None
    normalized = _normalize_indo_months(s)
    dt = pd.to_datetime(normalized, errors="coerce")
    return dt.date() if pd.notna(dt) else None


def parse_regulasi_satker_date(val):
    """
    Memecah format:
    - 'PVML 10/9/2026'    -> ('PVML', date(2026, 10, 9))
    - 'OJK 1 Januari 2010' -> ('OJK', date(2010, 1, 1))
    """
    s = clean_str(val)
    if not s:
        return None, None

    # Pola 1: <satker> MM/DD/YYYY
    match_slash = re.search(r"(\d{1,2}/\d{1,2}/\d{4})$", s)
    if match_slash:
        date_str = match_slash.group(1)
        satker = s[: match_slash.start()].strip() or None
        dt = pd.to_datetime(date_str, format="%m/%d/%Y", errors="coerce")
        return satker, (dt.date() if pd.notna(dt) else None)

    # Pola 2: <satker> DD Bulan YYYY (bahasa Indonesia / Inggris)
    month_pattern = "|".join(INDO_MONTHS.keys()) + "|" + "|".join(INDO_MONTHS.values())
    match_text = re.search(
        rf"(\d{{1,2}}\s+(?:{month_pattern})\s+\d{{4}})$", s, flags=re.IGNORECASE
    )
    if match_text:
        date_str = _normalize_indo_months(match_text.group(1))
        satker = s[: match_text.start()].strip() or None
        dt = pd.to_datetime(date_str, errors="coerce")
        return satker, (dt.date() if pd.notna(dt) else None)

    dt = pd.to_datetime(_normalize_indo_months(s), errors="coerce")
    return None, (dt.date() if pd.notna(dt) else None)


def get_existing_links_from_db(engine, table_name: str) -> set[str]:
    """Mengambil daftar link_halaman yang sudah tersimpan di Neon DB untuk early stop."""
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT link_halaman FROM public.{table_name}")).fetchall()
    return {row[0] for row in rows if row[0]}


def _dedup_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in rows:
        link = clean_str(r.get("link"))
        if link and link not in seen:
            seen.add(link)
            unique.append(r)
    return unique


def ingest_pengumuman_rows(engine, rows: list[dict]) -> int:
    rows = _dedup_rows(rows)
    if not rows:
        print("OJK Pengumuman: Tidak ada data baru untuk di-UPSERT.")
        return 0

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
        for r in rows
    ]

    processed = upsert_records(engine, UPSERT_PENGUMUMAN_SQL, records)
    print(f"OJK Pengumuman selesai: {processed} baris diproses (UPSERT).")
    return processed


def ingest_regulasi_rows(engine, rows: list[dict]) -> int:
    rows = _dedup_rows(rows)
    if not rows:
        print("OJK Rancangan Regulasi: Tidak ada data baru untuk di-UPSERT.")
        return 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    records = []
    for r in rows:
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
    return processed


def find_csv(filename: str) -> Path:
    matches = sorted((PROJECT_ROOT / "raw_data").rglob(filename))
    if not matches:
        raise FileNotFoundError(f"File {filename} tidak ditemukan di raw_data/.")
    return matches[-1]


def run_ojk_pipeline(
    max_pages_pengumuman: int = 5,
    max_pages_regulasi: int = 3,
    from_csv: bool = False,
    pengumuman_csv: str | None = None,
    regulasi_csv: str | None = None,
) -> None:
    """Entrypoint utama (siap dipanggil PythonOperator Airflow maupun CLI)."""
    engine = get_engine_with_retry()
    try:
        if from_csv:
            p_path = Path(pengumuman_csv) if pengumuman_csv else find_csv("ojk_pengumuman_raw.csv")
            r_path = Path(regulasi_csv) if regulasi_csv else find_csv("ojk_rancangan_regulasi_raw.csv")
            print(f"Mode CSV -> {p_path} & {r_path}")
            p_rows = pd.read_csv(p_path, sep=";", encoding="utf-8-sig").to_dict("records")
            r_rows = pd.read_csv(r_path, sep=";", encoding="utf-8-sig").to_dict("records")
        else:
            existing_p = get_existing_links_from_db(engine, "ojk_pengumuman")
            existing_r = get_existing_links_from_db(engine, "ojk_rancangan_regulasi")
            print(
                f"Existing di Neon DB -> Pengumuman: {len(existing_p)} link, "
                f"Rancangan Regulasi: {len(existing_r)} link"
            )
            p_rows, r_rows = scrape_all_ojk(
                existing_pengumuman=existing_p,
                existing_regulasi=existing_r,
                max_pages_pengumuman=max_pages_pengumuman,
                max_pages_regulasi=max_pages_regulasi,
                fetch_details=True,
            )

        ingest_pengumuman_rows(engine, p_rows)
        ingest_regulasi_rows(engine, r_rows)
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline OJK in-memory ke Neon DB.")
    parser.add_argument("--max-pages-pengumuman", type=int, default=5)
    parser.add_argument("--max-pages-regulasi", type=int, default=3)
    parser.add_argument("--from-csv", action="store_true", help="Fallback baca dari CSV lokal.")
    parser.add_argument("--pengumuman-csv", type=str, default=None)
    parser.add_argument("--regulasi-csv", type=str, default=None)
    args = parser.parse_args()

    run_ojk_pipeline(
        max_pages_pengumuman=args.max_pages_pengumuman,
        max_pages_regulasi=args.max_pages_regulasi,
        from_csv=args.from_csv,
        pengumuman_csv=args.pengumuman_csv,
        regulasi_csv=args.regulasi_csv,
    )