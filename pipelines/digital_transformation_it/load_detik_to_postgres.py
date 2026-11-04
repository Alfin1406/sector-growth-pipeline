"""Load Detik.com four-topic insight data into PostgreSQL.

Input : data/processed/detik_sector3_insight_four_topics_v5.csv
Target: market_intelligence.sector3_articles

The loader is idempotent for URL conflicts (UPSERT) and preserves the four
canonical project categories in `subtopic`. It never deletes unrelated rows.

Usage:
    python .\\06_database\\load_detik_to_postgres.py --dry-run
    $env:DB_PASSWORD = "<your-postgres-password>"
    python .\\06_database\\load_detik_to_postgres.py

Connection settings can be overridden with DB_HOST, DB_PORT, DB_NAME, DB_USER,
and DB_PASSWORD environment variables. Do not hardcode credentials in this file.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "detik_sector3_insight_four_topics_v5.csv"
TABLE_NAME = "sector3_articles"
SOURCE_NAME = "Detik.com"

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SSLMODE = os.getenv("POSTGRES_SSLMODE", "require")

ALLOWED_SUBTOPICS = {
    "Enterprise Software",
    "Cyber Security",
    "Digital Transformation",
    "Cloud Enterprise",
}

REQUIRED_COLUMNS = [
    "title", "url", "published_at", "channel", "source", "topic", "subtopic",
    "event_type", "technology", "industry", "business_action", "impact",
    "insight_summary", "content_status", "scraped_at",
]
DB_COLUMNS = [
    "article_id", "title", "url", "published_at", "channel", "source", "topic",
    "subtopic", "event_type", "technology", "industry", "business_action",
    "impact", "insight_summary", "content_status", "scraped_at",
]

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    article_id VARCHAR(64) PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at TIMESTAMP NULL,
    channel TEXT,
    source TEXT,
    topic TEXT,
    subtopic TEXT,
    event_type TEXT,
    technology TEXT,
    industry TEXT,
    business_action TEXT,
    impact TEXT,
    insight_summary TEXT,
    content_status TEXT,
    scraped_at TIMESTAMP NULL
);
"""

# The table may have been created by an older pipeline. Add non-key columns
# safely if missing; do not drop/recreate or delete any existing data.
MIGRATION_SQL = [
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS published_at TIMESTAMP NULL;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS channel TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS source TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS topic TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS subtopic TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS event_type TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS technology TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS industry TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS business_action TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS impact TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS insight_summary TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS content_status TEXT;",
    f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMP NULL;",
]

UPSERT_SQL = f"""
INSERT INTO {TABLE_NAME} (
    article_id, title, url, published_at, channel, source, topic, subtopic,
    event_type, technology, industry, business_action, impact, insight_summary,
    content_status, scraped_at
) VALUES (
    :article_id, :title, :url, :published_at, :channel, :source, :topic, :subtopic,
    :event_type, :technology, :industry, :business_action, :impact, :insight_summary,
    :content_status, :scraped_at
)
ON CONFLICT (url) DO UPDATE SET
    title = EXCLUDED.title,
    published_at = COALESCE(EXCLUDED.published_at, {TABLE_NAME}.published_at),
    channel = EXCLUDED.channel,
    source = EXCLUDED.source,
    topic = EXCLUDED.topic,
    subtopic = EXCLUDED.subtopic,
    event_type = EXCLUDED.event_type,
    technology = EXCLUDED.technology,
    industry = EXCLUDED.industry,
    business_action = EXCLUDED.business_action,
    impact = EXCLUDED.impact,
    insight_summary = EXCLUDED.insight_summary,
    content_status = EXCLUDED.content_status,
    scraped_at = COALESCE(EXCLUDED.scraped_at, {TABLE_NAME}.scraped_at);
"""


def stable_id(url: Any) -> str | None:
    if pd.isna(url) or not str(url).strip():
        return None
    return hashlib.sha256(str(url).strip().encode("utf-8")).hexdigest()


def db_scalar(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    # Convert numpy scalar values to native Python objects for SQLAlchemy.
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return value


def load_and_validate() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan: {INPUT_FILE}\n"
            "Pastikan normalisasi dan Insight Extraction empat topik sudah berhasil."
        )

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    print(f"Input file : {INPUT_FILE}")
    print(f"Input rows : {len(df):,}")
    if df.empty:
        raise ValueError("CSV insight kosong; tidak ada data yang akan dimuat.")

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(missing))

    df["url"] = df["url"].astype("string").str.strip()
    df["title"] = df["title"].astype("string").str.strip()
    before = len(df)
    df = df[
        df["url"].notna() & df["url"].ne("") & df["title"].notna() & df["title"].ne("")
    ].copy()
    print(f"Baris tanpa title/URL valid dihapus: {before - len(df)}")

    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="last").copy()
    print(f"Duplikat URL dalam CSV dihapus: {before - len(df)}")

    if "article_id" not in df.columns:
        df["article_id"] = df["url"].apply(stable_id)
    else:
        missing_id = df["article_id"].isna() | df["article_id"].astype("string").str.strip().eq("")
        df.loc[missing_id, "article_id"] = df.loc[missing_id, "url"].apply(stable_id)

    df["article_id"] = df["article_id"].astype("string").str.strip()
    if df["article_id"].isna().any() or df["article_id"].eq("").any():
        raise ValueError("Ada artikel tanpa article_id dan ID fallback tidak dapat dibuat.")

    # This loader is specifically for the Detik four-topic normalized output.
    df["subtopic"] = df["subtopic"].astype("string").str.strip()
    unexpected = sorted(set(df["subtopic"].dropna().astype(str)) - ALLOWED_SUBTOPICS)
    if unexpected:
        raise ValueError(
            "Ditemukan subtopic di luar empat kategori dashboard: " + ", ".join(unexpected)
            + ". Jalankan normalisasi empat topik sebelum loading."
        )

    df["source"] = df["source"].fillna(SOURCE_NAME).astype("string").str.strip()
    other_sources = sorted(s for s in set(df["source"].dropna().astype(str)) if s != SOURCE_NAME)
    if other_sources:
        raise ValueError(
            f"Input seharusnya hanya berisi source {SOURCE_NAME}; ditemukan: "
            + ", ".join(other_sources)
        )
    df["source"] = SOURCE_NAME

    for col in ["published_at", "scraped_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df = df[DB_COLUMNS].copy()
    return df


def print_summary(df: pd.DataFrame, title: str = "VALIDASI INPUT") -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)
    print(f"Rows to load      : {len(df):,}")
    print(f"Unique URLs       : {df['url'].nunique():,}")
    print(f"Unique article_id : {df['article_id'].nunique():,}")
    print("Source             : Detik.com")
    print("Category distribution:")
    for subtopic, count in df["subtopic"].value_counts(dropna=False).items():
        print(f"  {subtopic}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Detik four-topic insight data to PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Validasi CSV tanpa menghubungi PostgreSQL.")
    args = parser.parse_args()

    print("=" * 68)
    print("LOAD DETIK.COM FOUR-TOPIC INSIGHT TO POSTGRESQL")
    print("=" * 68)
    df = load_and_validate()
    print_summary(df)

    if args.dry_run:
        print("\nDRY RUN BERHASIL: CSV valid; tidak ada koneksi atau perubahan database.")
        return

    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        raise RuntimeError(
            "Konfigurasi Neon belum lengkap. Periksa environment variable POSTGRES_*."
        )

    # Import database dependencies only for an actual load.
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        query={"sslmode": DB_SSLMODE},
    )
    engine = create_engine(db_url, pool_pre_ping=True)

    try:
        with engine.begin() as conn:
            # Tabel dan kolom sudah tersedia di Neon.
            # Tidak perlu CREATE TABLE atau ALTER TABLE.

            records = [
                {key: db_scalar(value) for key, value in record.items()}
                for record in df.to_dict(orient="records")
            ]

            # Masukkan atau perbarui artikel berdasarkan unique URL.
            conn.execute(text(UPSERT_SQL), records)

        with engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar_one()
            detik_total = conn.execute(
                text(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE source = :source"),
                {"source": SOURCE_NAME},
            ).scalar_one()
            topic_rows = conn.execute(
                text(f"""
                    SELECT subtopic, COUNT(*) AS total
                    FROM {TABLE_NAME}
                    WHERE source = :source
                    GROUP BY subtopic
                    ORDER BY total DESC, subtopic
                """),
                {"source": SOURCE_NAME},
            ).all()

        print("\nLOAD BERHASIL")
        print(f"Baris diproses : {len(df):,}")
        print(f"Total semua sumber di DB : {total:,}")
        print(f"Total Detik.com di DB    : {detik_total:,}")
        print("Distribusi subtopic Detik.com di database:")
        for row in topic_rows:
            print(f"  {row.subtopic or 'NULL'}: {row.total}")
        print(f"Database: {DB_NAME}; tabel: {TABLE_NAME}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
