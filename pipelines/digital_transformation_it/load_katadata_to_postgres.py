"""Load Katadata Sector 3 insight data into PostgreSQL.

Input : data/processed/katadata_enterprise_insight.csv
Target: market_intelligence.sector3_articles

This loader preserves the `topic` and `subtopic` values produced by
extract_enterprise_insight.py. It does not force all rows into
"Enterprise Software".
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent 
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "katadata_enterprise_insight.csv"
TABLE_NAME = "sector3_articles"

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SSLMODE = os.getenv("POSTGRES_SSLMODE", "require")

REQUIRED_COLUMNS = [
    "title",
    "url",
    "published_at",
    "channel",
    "source",
    "topic",
    "subtopic",
    "event_type",
    "technology",
    "industry",
    "business_action",
    "impact",
    "insight_summary",
    "content_status",
    "scraped_at",
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

UPSERT_SQL = f"""
INSERT INTO {TABLE_NAME} (
    article_id, title, url, published_at, channel, source,
    topic, subtopic, event_type, technology, industry,
    business_action, impact, insight_summary, content_status, scraped_at
) VALUES (
    :article_id, :title, :url, :published_at, :channel, :source,
    :topic, :subtopic, :event_type, :technology, :industry,
    :business_action, :impact, :insight_summary, :content_status, :scraped_at
)
ON CONFLICT (url) DO UPDATE SET
    title = EXCLUDED.title,
    published_at = COALESCE(
        EXCLUDED.published_at,
        {TABLE_NAME}.published_at 
    ),
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
    scraped_at = EXCLUDED.scraped_at;
"""


def generate_article_id(url: Any) -> str | None:
    """Return a stable SHA-256 identifier when article_id is missing."""
    if pd.isna(url) or not str(url).strip():
        return None
    return hashlib.sha256(str(url).strip().encode("utf-8")).hexdigest()


def scalar_or_none(value: Any) -> Any:
    """Convert pandas missing values and timestamps to DB-compatible values."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def main() -> None:
    print("=" * 68)
    print("LOAD KATADATA SECTOR 3 INSIGHT TO POSTGRESQL")
    print("=" * 68)

    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        raise RuntimeError(
            "Konfigurasi Neon belum lengkap. Periksa environment variable POSTGRES_*."
        )

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)
    print(f"Input file : {INPUT_FILE}")
    print(f"Input rows : {len(df)}")

    if df.empty:
        print("[WARNING] File input kosong. Tidak ada data yang dimuat.")
        return

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(missing))

    # Clean URL/title and reject rows without a stable URL/title.
    df["url"] = df["url"].astype("string").str.strip()
    df["title"] = df["title"].astype("string").str.strip()
    before = len(df)
    df = df[
        df["url"].notna()
        & df["url"].ne("")
        & df["title"].notna()
        & df["title"].ne("")
    ].copy()
    print(f"Invalid URL/title removed: {before - len(df)}")

    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="last").copy()
    print(f"Duplicate URLs removed: {before - len(df)}")

    # Ensure stable IDs exist. Retain IDs produced by the insight script.
    if "article_id" not in df.columns:
        df["article_id"] = df["url"].apply(generate_article_id)
    else:
        needs_id = df["article_id"].isna() | df["article_id"].astype(str).str.strip().eq("")
        df.loc[needs_id, "article_id"] = df.loc[needs_id, "url"].apply(generate_article_id)

    # Preserve topic/subtopic from the insight CSV. Do not force topic=Enterprise Software.
    for col in ["published_at", "scraped_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    db_columns = [
        "article_id", "title", "url", "published_at", "channel", "source",
        "topic", "subtopic", "event_type", "technology", "industry",
        "business_action", "impact", "insight_summary", "content_status", "scraped_at",
    ]
    df = df[db_columns].copy()

    records = [
        {key: scalar_or_none(value) for key, value in record.items()}
        for record in df.to_dict(orient="records")
    ]

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        query={"sslmode": DB_SSLMODE},
    )
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.begin() as conn:
            conn.execute(text(CREATE_TABLE_SQL))

            # Use execute with a list of records for an efficient batch upsert.
            conn.execute(text(UPSERT_SQL), records)

        with engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar_one()
            katadata_total = conn.execute(
                text(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE source = :source"),
                {"source": "Katadata"},
            ).scalar_one()
            topic_rows = conn.execute(
                text(f"""
                    SELECT subtopic, COUNT(*) AS total
                    FROM {TABLE_NAME}
                    WHERE source = :source
                    GROUP BY subtopic
                    ORDER BY total DESC, subtopic
                """),
                {"source": "Katadata"},
            ).all()

        print("\n[ SUCCESS ] LOAD COMPLETED")
        print(f"Rows processed : {len(df)}")
        print(f"Total DB rows  : {total}")
        print(f"Katadata rows  : {katadata_total}")
        print("\nKatadata category distribution (subtopic):")
        for row in topic_rows:
            print(f"  {row.subtopic or 'NULL'}: {row.total}")
        print(f"\nTable: {TABLE_NAME}")
        print(f"Database: {DB_NAME}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
