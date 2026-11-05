
import os
import time
import pandas as pd
import psycopg2
from pathlib import Path
from psycopg2.extras import execute_values


# ==========================================
# KONFIGURASI
# ==========================================

PIPELINE_DIR = Path("/opt/airflow/sector-growth-pipeline/pipelines/data_center_cloud")
CSV_FILE = PIPELINE_DIR / "data_center_kompas_business_insight.csv"

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
}

TARGET_COLUMNS = [
    "title",
    "published_date",
    "summary",
    "article_url",
    "image_url",
    "source",
    "tag",
    "sector",
    "topic",
    "relevance",
    "relevance_score",
    "technology",
    "investment_value",
    "investment_type",
    "capacity",
    "capacity_type",
    "company",
    "organization",
    "project_location",
    "insight_type",
    "subtopic",
    "content",
]


# ==========================================
# KONEKSI DATABASE DENGAN RETRY
# ==========================================

def connect_with_retry(max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Mencoba koneksi Neon ({attempt}/{max_retries})...")

            config = DB_CONFIG.copy()
            config["connect_timeout"] = 20

            conn = psycopg2.connect(**config)

            print("Koneksi Neon berhasil!")
            return conn

        except psycopg2.OperationalError as e:
            print(f"Koneksi gagal: {e}")

            if attempt == max_retries:
                raise

            wait_time = 15 * attempt
            print(f"Mencoba kembali dalam {wait_time} detik...")
            time.sleep(wait_time)


# ==========================================
# LOAD CSV
# ==========================================

print("=" * 50)
print("LOAD KOMPAS BUSINESS INSIGHT")
print("=" * 50)

if not CSV_FILE.exists():
    raise FileNotFoundError(f"CSV tidak ditemukan: {CSV_FILE}")

df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
print(f"Total data CSV: {len(df)}")

for column in TARGET_COLUMNS:
    if column not in df.columns:
        df[column] = None

df["source"] = "KOMPAS"
df["sector"] = "Data Center & Cloud"

if (
    df["subtopic"].isna().any()
    or df["subtopic"].astype(str).str.strip().eq("").any()
):
    raise ValueError(
        "Ada subtopic kosong. Periksa task classify_subtopic_kompas."
    )

if df["article_url"].isna().any() or df["article_url"].astype(str).str.strip().eq("").any():
    raise ValueError("Ada article_url kosong pada data Kompas.")

print("\nDistribusi subtopic KOMPAS:")
print(df["subtopic"].value_counts(dropna=False).to_string())

df = df[TARGET_COLUMNS]
df = df.astype(object).where(pd.notnull(df), None)


# ==========================================
# INSERT / UPSERT
# ==========================================

conn = connect_with_retry()

try:
    with conn.cursor() as cursor:

        columns_sql = ", ".join(TARGET_COLUMNS)

        update_columns = [
            column for column in TARGET_COLUMNS
            if column not in ("article_url", "subtopic")
        ]

        update_assignments = [
            f"{column} = EXCLUDED.{column}"
            for column in update_columns
        ]

        update_assignments.append("""
            subtopic = CASE
                WHEN arza_data_center_news.subtopic IS NULL
                     OR BTRIM(arza_data_center_news.subtopic) = ''
                THEN EXCLUDED.subtopic
                ELSE arza_data_center_news.subtopic
            END
        """)

        update_sql = ", ".join(update_assignments)

        query = f"""
            INSERT INTO arza_data_center_news ({columns_sql})
            VALUES %s
            ON CONFLICT (article_url)
            DO UPDATE SET
                {update_sql};
        """

        values = [
            tuple(row[column] for column in TARGET_COLUMNS)
            for _, row in df.iterrows()
        ]

        if values:
            execute_values(cursor, query, values)

        conn.commit()

        print(f"\nTotal data diproses: {len(values)}")
        print("Mode: INSERT / UPDATE berdasarkan article_url")
        print("Subtopic lama yang sudah terisi dipertahankan.")

except Exception:
    conn.rollback()
    raise

finally:
    conn.close()


# ==========================================
# HASIL
# ==========================================

print("\n" + "=" * 50)
print("HASIL LOAD KOMPAS")
print("=" * 50)
print(f"Total CSV      : {len(df)}")
print(f"Data diproses  : {len(values)}")
print("Mode           : UPSERT")
print("Status         : BERHASIL")
print("=" * 50)
