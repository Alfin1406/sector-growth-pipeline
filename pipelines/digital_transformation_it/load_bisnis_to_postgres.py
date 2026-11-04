import os
import hashlib
import pandas as pd
from sqlalchemy import create_engine, text


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "bisnis_insight.csv"
)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "market_intelligence")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD") 


# ============================================================
# VALIDATION
# ============================================================

if not DB_PASSWORD:
    raise ValueError(
        "DB_PASSWORD belum diset sebagai environment variable."
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)  


# ============================================================
# LOAD CSV
# ============================================================

print("=" * 70)
print("06 DATABASE - BISNIS.COM")
print("LOAD TO GENERIC SECTOR 3 TABLE")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"\nInput dataset : {len(df)} rows")


# ============================================================
# ARTICLE ID
# ============================================================




# ============================================================
# DATETIME
# ============================================================

df["published_at"] = pd.to_datetime(
    df["published_at"],
    errors="coerce"
)

df["scraped_at"] = pd.to_datetime(
    df["scraped_at"],
    errors="coerce"
)

# Ubah NaT menjadi None supaya PostgreSQL menerima sebagai NULL
df["published_at"] = df["published_at"].apply(
    lambda x: x.to_pydatetime() if pd.notna(x) else None
)

df["scraped_at"] = df["scraped_at"].apply( 
    lambda x: x.to_pydatetime() if pd.notna(x) else None
) 


# ============================================================
# COLUMN ORDER
# ============================================================

columns = [
    "article_id",
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
    "scraped_at"
]

df = df[columns]


# ============================================================
# INSERT / UPSERT
# ============================================================

sql = text("""
    INSERT INTO sector3_articles (
        article_id,
        title,
        url,
        published_at,
        channel,
        source,
        topic,
        subtopic,
        event_type,
        technology,
        industry,
        business_action,
        impact,
        insight_summary,
        content_status,
        scraped_at
    )
    VALUES (
        :article_id,
        :title,
        :url,
        :published_at,
        :channel,
        :source,
        :topic,
        :subtopic,
        :event_type,
        :technology,
        :industry,
        :business_action,
        :impact,
        :insight_summary,
        :content_status,
        :scraped_at
    )
    ON CONFLICT (url)
    DO UPDATE SET
        title = EXCLUDED.title,
        published_at = COALESCE(
            EXCLUDED.published_at,
            sector3_articles.published_at
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
""")


# ============================================================
# EXECUTE
# ============================================================

records = df.to_dict("records")

for record in records:
    value = record.get("published_at")
    if pd.isna(value):
        record["published_at"] = None
    elif isinstance(value, pd.Timestamp):
        record["published_at"] = value.to_pydatetime()

    value = record.get("scraped_at")
    if pd.isna(value):
        record["scraped_at"] = None
    elif isinstance(value, pd.Timestamp):
        record["scraped_at"] = value.to_pydatetime()

# ============================================================
# INSERT / UPSERT EXECUTION
# ============================================================

with engine.begin() as conn:
    for record in records:
        conn.execute(sql, record) 


# ============================================================
# VERIFICATION
# ============================================================

with engine.connect() as conn:

    total = conn.execute(
        text("SELECT COUNT(*) FROM sector3_articles")
    ).scalar()

    bisnis = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM sector3_articles
            WHERE source = 'Bisnis.com'
        """)
    ).scalar()

    cyber = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM sector3_articles
            WHERE topic = 'Cyber Security'
        """)
    ).scalar()

    print("\n" + "=" * 70)
    print("DATABASE LOAD SELESAI")
    print("=" * 70)

    print(f"Total sector3_articles : {total}")
    print(f"Total Bisnis.com       : {bisnis}")
    print(f"Total Cyber Security   : {cyber}")