import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from psycopg2.extras import execute_batch
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_project_env() -> None:
    """Memuat .env di root proyek tanpa menimpa env vars yang sudah diset Airflow."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


def get_engine_with_retry(max_retries: int = 5):
    """Membuat SQLAlchemy engine ke Neon DB sesuai standar tim dengan fitur retry."""
    load_project_env()

    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_pass = os.getenv("POSTGRES_PASSWORD")
    db_ssl = os.getenv("POSTGRES_SSLMODE", "prefer")
    database_url_env = os.getenv("DATABASE_URL")

    if all([db_host, db_name, db_user, db_pass]):
        database_url = URL.create(
            drivername="postgresql+psycopg2",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=int(db_port),
            database=db_name,
            query={"sslmode": db_ssl},
        )
    elif database_url_env:
        # Fallback jika lokal hanya mengisi DATABASE_URL
        database_url = database_url_env
    else:
        raise ValueError(
            "Kredensial database belum lengkap. Isi POSTGRES_HOST, POSTGRES_DB, "
            "POSTGRES_USER, POSTGRES_PASSWORD (atau DATABASE_URL) di .env / Airflow."
        )

    engine = create_engine(
        database_url,
        connect_args={"connect_timeout": 20},
        pool_pre_ping=True,
    )

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Mencoba koneksi ke Neon DB ({attempt}/{max_retries})...")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Koneksi Neon berhasil!")
            return engine
        except Exception as e:
            print(f"Koneksi gagal: {e}")
            if attempt == max_retries:
                engine.dispose()
                raise
            wait_time = 15 * attempt
            print(f"Mencoba kembali dalam {wait_time} detik...")
            time.sleep(wait_time)


def upsert_records(engine, query_sql: str, records: list[dict], chunk_size: int = 500) -> int:
    """Menjalankan UPSERT dalam paket batch (execute_batch) agar cepat untuk koneksi cloud Neon."""
    if not records:
        return 0

    # Konversi named parameter gaya SQLAlchemy (:kolom) ke format psycopg2 (%(kolom)s)
    # tanpa mengganggu type cast PostgreSQL seperti ::integer atau ::text[]
    pg_sql = re.sub(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)", r"%(\1)s", query_sql)

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            execute_batch(cur, pg_sql, records, page_size=chunk_size)
        raw_conn.commit()
        return len(records)
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()