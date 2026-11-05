import hashlib
import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = (
    "data/processed/"
    "bisnis_cyber_insight.csv"
)


DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SSLMODE = os.getenv("POSTGRES_SSLMODE", "require")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    raise RuntimeError(
        "Konfigurasi Neon belum lengkap. Periksa environment variable POSTGRES_*."
    )

TABLE_NAME = "atha_sector3_articles"


# ============================================================
# DATABASE CONNECTION
# ============================================================

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
    query={"sslmode": DB_SSLMODE},
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "title",
    "url",
    "published_at",
    "channel",
    "source",
    "content_status",
    "threat_type",
    "technology",
    "industry",
    "business_action",
    "impact",
    "business_topic",
    "insight_summary",
]


# ============================================================
# HELPER
# ============================================================

def generate_article_id(url):
    """
    Membuat ID artikel berdasarkan URL.
    Hash digunakan agar ID konsisten setiap pipeline dijalankan.
    """

    if pd.isna(url) or not str(url).strip():
        return None

    return hashlib.sha256(
        str(url).strip().encode("utf-8")
    ).hexdigest()


def clean_value(value):
    """
    Mengubah NaN menjadi None agar kompatibel dengan PostgreSQL.
    """

    if pd.isna(value):
        return None

    return value


# ============================================================
# CREATE TABLE
# ============================================================

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
    technology TEXT,
    industry TEXT,
    business_action TEXT,
    impact TEXT,
    insight_summary TEXT,
    content_status TEXT,
    scraped_at TIMESTAMP NULL,
    event_type TEXT
);
"""


# ============================================================
# UPSERT SQL
# ============================================================


UPSERT_SQL = f"""
INSERT INTO {TABLE_NAME} (
    article_id,
    source,
    channel,
    title,
    url,
    published_at,
    scraped_at,
    content_status,
    topic,
    subtopic,
    event_type,
    technology,
    industry,
    business_action,
    impact,
    insight_summary
)
VALUES (
    :article_id,
    :source,
    :channel,
    :title,
    :url,
    :published_at,
    :scraped_at,
    :content_status,
    :topic,
    :subtopic,
    :event_type,
    :technology,
    :industry,
    :business_action,
    :impact,
    :insight_summary
)
ON CONFLICT (url)
DO UPDATE SET
    source = EXCLUDED.source,
    channel = EXCLUDED.channel,
    title = EXCLUDED.title,
    published_at = EXCLUDED.published_at,
    scraped_at = EXCLUDED.scraped_at,
    content_status = EXCLUDED.content_status,
    topic = EXCLUDED.topic,
    subtopic = EXCLUDED.subtopic,
    event_type = EXCLUDED.event_type,
    technology = EXCLUDED.technology,
    industry = EXCLUDED.industry,
    business_action = EXCLUDED.business_action,
    impact = EXCLUDED.impact,
    insight_summary = EXCLUDED.insight_summary;
"""


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("06 DATABASE - CYBER SECURITY")
    print("=" * 70)

    # --------------------------------------------------------
    # CHECK INPUT FILE
    # --------------------------------------------------------

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"File tidak ditemukan: {INPUT_FILE}"
        )

    # --------------------------------------------------------
    # LOAD CSV
    # --------------------------------------------------------

    df = pd.read_csv(INPUT_FILE)

    if "scraped_at" not in df.columns:
        print(
            "[WARNING] Kolom scraped_at tidak ditemukan. "
            "Nilai akan disimpan sebagai NULL."
        )
        df["scraped_at"] = pd.NaT

    print(
        f"\n[INFO] Data masuk : {len(df)} artikel"
    )

    # --------------------------------------------------------
    # VALIDATE COLUMNS
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Kolom berikut tidak ditemukan:\n"
            + "\n".join(missing_columns)
        )

    # --------------------------------------------------------
    # GENERATE ARTICLE ID
    # --------------------------------------------------------

    df["article_id"] = (
        df["url"]
        .apply(generate_article_id)
    )

    # --------------------------------------------------------
    # DATETIME NORMALIZATION
    # --------------------------------------------------------

    df["published_at"] = pd.to_datetime(
        df["published_at"],
        errors="coerce"
    )

    if "scraped_at" in df.columns:

        df["scraped_at"] = pd.to_datetime(
            df["scraped_at"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # REMOVE INVALID URL
    # --------------------------------------------------------

    before = len(df)

    df = df[
        df["url"].notna()
        & (df["url"].astype(str).str.strip() != "")
    ].copy()

    removed = before - len(df)

    print(
        f"[INFO] URL tidak valid dihapus : {removed}"
    )

    # --------------------------------------------------------
    # REMOVE DUPLICATE URL
    # --------------------------------------------------------

    before = len(df)

    df = df.drop_duplicates(
        subset=["url"],
        keep="last"
    )

    duplicates_removed = before - len(df)

    print(
        f"[INFO] Duplicate URL dihapus : "
        f"{duplicates_removed}"
    )


    # --------------------------------------------------------
    # MAP CSV COLUMNS TO SECTOR 3 SCHEMA
    # --------------------------------------------------------

    df["topic"] = "Cyber Security"
    df["subtopic"] = df["business_topic"]
    df["event_type"] = df["threat_type"]

    # --------------------------------------------------------
    # SELECT DATABASE COLUMNS
    # --------------------------------------------------------

    database_columns = [
        "article_id",
        "source",
        "channel",
        "title",
        "url",
        "published_at",
        "scraped_at",
        "content_status",
        "topic",
        "subtopic",
        "event_type",
        "technology",
        "industry",
        "business_action",
        "impact",
        "insight_summary",
    ]



    missing_database_columns = [
        column
        for column in database_columns
        if column not in df.columns
    ]

    if missing_database_columns:
        raise ValueError(
            "Kolom database tidak tersedia di DataFrame: "
            + ", ".join(missing_database_columns)
        )

    df = df[database_columns].copy()


    # --------------------------------------------------------
    # CREATE DATABASE ENGINE
    # --------------------------------------------------------

    print("\n[INFO] Menghubungkan ke PostgreSQL...")

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

    # --------------------------------------------------------
    # TEST CONNECTION
    # --------------------------------------------------------

    with engine.connect() as connection:

        connection.execute(
            text("SELECT 1")
        )

    print(
        "[INFO] Koneksi PostgreSQL berhasil."
    )

    # --------------------------------------------------------
    # CREATE TABLE
    # --------------------------------------------------------

    with engine.begin() as connection:

        connection.execute(
            text(CREATE_TABLE_SQL)
        )

    print(
        f"[INFO] Table siap : {TABLE_NAME}"
    )

    # --------------------------------------------------------
    # UPSERT DATA
    # --------------------------------------------------------

    records = df.to_dict(
        orient="records"
    )

    cleaned_records = []

    for record in records:

        cleaned_record = {
            key: clean_value(value)
            for key, value in record.items()
        }

        cleaned_records.append(
            cleaned_record
        )

    with engine.begin() as connection:

        for record in cleaned_records:

            connection.execute(
                text(UPSERT_SQL),
                record
            )

    # --------------------------------------------------------
    # CHECK TOTAL DATA
    # --------------------------------------------------------

    with engine.connect() as connection:

        result = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {TABLE_NAME}
                """
            )
        )

        total_data = result.scalar()

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DATABASE LOAD SELESAI")
    print("=" * 70)

    print(
        f"Data diproses      : {len(df)}"
    )

    print(
        f"Total data di DB   : {total_data}"
    )

    print(
        f"Table              : {TABLE_NAME}"
    )

    print(
        f"Database            : {DB_NAME}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
