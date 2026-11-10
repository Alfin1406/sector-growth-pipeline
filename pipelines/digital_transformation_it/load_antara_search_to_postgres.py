"""Load ANTARA Search relevant articles into PostgreSQL.

Default input:
    data/processed/antara_search_filtered_v5.csv

For Airflow production, pass:
    --input data/processed/antara_search_filtered_v4.csv

Target:
    public.sector3_articles

Safety:
- Inserts only; never updates or deletes existing rows.
- Uses SHA-256(URL) as article_id.
- Checks BOTH article_id and URL before inserting.
- A rerun skips rows already loaded from the same ANTARA Search channel.
- Any conflicting ID/URL metadata stops the transaction.
- --dry-run validates the CSV without connecting to PostgreSQL.
- --check-db checks database conflicts without writing anything.

PowerShell:
    python .\\06_database\\load_antara_search_to_postgres.py --dry-run
    python .\\06_database\\load_antara_search_to_postgres.py --check-db
    $env:DB_PASSWORD = "<your-postgres-password>"
    python .\\06_database\\load_antara_search_to_postgres.py

Connection variables:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Any

import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "antara_search_filtered_v5.csv"
)

SCHEMA_NAME = "public"
TABLE_NAME = "atha_sector3_articles"
FULL_TABLE_NAME = f"{SCHEMA_NAME}.{TABLE_NAME}"

SOURCE_NAME = "ANTARA News"
CHANNEL_NAME = "ANTARA Search"
TOPIC_NAME = "IT Enterprise"
CONTENT_STATUS_NAME = "SUMMARY_ONLY"
TIMEZONE_NAME = "Asia/Jakarta"

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SSLMODE = os.getenv("POSTGRES_SSLMODE", "require")

ALLOWED_SUBTOPICS = {
    "Cloud Enterprise",
    "Cyber Security",
    "Digital Transformation",
    "Enterprise Software",
}


# ============================================================
# 2. INPUT AND DATABASE COLUMNS
# ============================================================

REQUIRED_INPUT_COLUMNS = [
    "article_id",
    "source",
    "channel",
    "title",
    "url",
    "published_at",
    "content",
    "content_status",
    "scraped_at",
    "summary",
    "sector3_topic",
    "relevance_level",
]

DB_COLUMNS = [
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
    "scraped_at",
]


# ============================================================
# 3. INSERT SQL
# ============================================================

INSERT_SQL = f"""
INSERT INTO {FULL_TABLE_NAME} (
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
) VALUES (
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
);
"""


# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def stable_id(url: Any) -> str | None:
    """Generate deterministic SHA-256 ID from URL."""

    if pd.isna(url) or not str(url).strip():
        return None

    return hashlib.sha256(
        str(url).strip().encode("utf-8")
    ).hexdigest()


def parse_local_timestamp(
    series: pd.Series,
    column_name: str
) -> pd.Series:
    """
    Parse ISO timestamps, convert to Asia/Jakarta,
    then remove timezone information.

    Destination columns use TIMESTAMP WITHOUT TIME ZONE.
    """

    parsed = pd.to_datetime(
    series,
    errors="coerce",
    utc=True,
    )

    invalid = parsed.isna()

    if invalid.any():
        rows = (
            invalid[invalid].index + 2
        ).tolist()[:10]

        raise ValueError(
            f"Ada {int(invalid.sum())} timestamp "
            f"{column_name} tidak valid. "
            f"Contoh nomor baris CSV: {rows}"
        )

    return (
        parsed
        .dt.tz_convert(TIMEZONE_NAME)
        .dt.tz_localize(None)
    )


def db_scalar(value: Any) -> Any:
    """Convert pandas/numpy values to native Python values."""

    if value is None or pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    return value


# ============================================================
# 5. LOAD AND VALIDATE CSV
# ============================================================

def load_and_validate(
    input_file: Path = INPUT_FILE
) -> pd.DataFrame:

    input_file = (
        input_file
        if input_file.is_absolute()
        else PROJECT_ROOT / input_file
    )

    input_file = input_file.resolve()

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan: {input_file}\n"
            "Pastikan file hasil filtering ANTARA Search tersedia "
            "di data/processed."
        )

    df = pd.read_csv(
        input_file,
        encoding="utf-8-sig"
    )

    print(f"Input file : {input_file}")
    print(f"Input rows : {len(df):,}")

    if df.empty:
        raise ValueError(
            "CSV input kosong; tidak ada data yang akan dimuat."
        )

    missing = [
        column
        for column in REQUIRED_INPUT_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Kolom wajib tidak ditemukan: "
            + ", ".join(missing)
        )

    # Normalize important text columns.
    for column in [
        "article_id",
        "title",
        "url",
        "source",
        "channel",
        "content_status",
        "summary",
        "sector3_topic",
        "relevance_level",
    ]:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Validate required values.
    required_values = [
        "article_id",
        "title",
        "url",
        "summary",
    ]

    if df[required_values].isna().any().any():
        raise ValueError(
            "Ada article_id, title, URL, atau summary yang kosong."
        )

    for column in required_values:
        if df[column].eq("").any():
            raise ValueError(
                f"Ada nilai kosong pada kolom {column}."
            )

    # Detect duplicate article IDs.
    if df["article_id"].duplicated().any():
        duplicates = (
            df.loc[
                df["article_id"].duplicated(False),
                "article_id"
            ].tolist()
        )

        raise ValueError(
            f"Duplikasi article_id di CSV: {duplicates[:10]}"
        )

    # Detect duplicate URLs.
    if df["url"].duplicated().any():
        duplicates = (
            df.loc[
                df["url"].duplicated(False),
                "url"
            ].tolist()
        )

        raise ValueError(
            f"Duplikasi URL di CSV: {duplicates[:10]}"
        )

    # Validate source.
    allowed_sources = set(
        df["source"].dropna().astype(str)
    )

    if allowed_sources != {SOURCE_NAME}:
        raise ValueError(
            f"Input harus hanya berisi source {SOURCE_NAME}; "
            f"ditemukan: {sorted(allowed_sources)}"
        )

    # Validate channel.
    allowed_channels = set(
        df["channel"].dropna().astype(str)
    )

    if allowed_channels != {CHANNEL_NAME}:
        raise ValueError(
            f"Input harus hanya berisi channel {CHANNEL_NAME}; "
            f"ditemukan: {sorted(allowed_channels)}"
        )

    # Only relevant articles can be loaded.
    statuses = set(
        df["relevance_level"].dropna().astype(str)
    )

    if statuses != {"Relevan"}:
        raise ValueError(
            "File input harus berisi artikel Relevan saja; "
            + ", ".join(sorted(statuses))
        )

    # Validate summary-only status.
    content_statuses = {
        value.lower()
        for value in df["content_status"].dropna().astype(str)
    }

    if content_statuses != {"summary_only"}:
        raise ValueError(
            "ANTARA Search harus berstatus summary_only; "
            + ", ".join(sorted(content_statuses))
        )

    # Content must remain empty.
    content_values = (
        df["content"]
        .fillna("")
        .astype("string")
        .str.strip()
    )

    if content_values.ne("").any():
        raise ValueError(
            "Ditemukan kolom content berisi teks. "
            "Loader ini khusus summary-only."
        )

    # Validate four official Sector 3 topics.
    df["sector3_topic"] = (
        df["sector3_topic"]
        .astype("string")
        .str.strip()
    )

    unexpected = sorted(
        set(
            df["sector3_topic"]
            .dropna()
            .astype(str)
        ) - ALLOWED_SUBTOPICS
    )

    if unexpected:
        raise ValueError(
            "Ditemukan sector3_topic di luar empat kategori: "
            + ", ".join(unexpected)
        )

    if (
        df["sector3_topic"].isna().any()
        or df["sector3_topic"].eq("").any()
    ):
        raise ValueError(
            "Ada artikel tanpa sector3_topic."
        )

    # Generate SHA-256 ID from article URL.
    df["article_id_source"] = df["article_id"]

    df["article_id"] = df["url"].apply(stable_id)

    if (
        df["article_id"].isna().any()
        or df["article_id"].eq("").any()
    ):
        raise ValueError(
            "Gagal membentuk article_id SHA-256 dari URL."
        )

    if df["article_id"].str.len().ne(64).any():
        raise ValueError(
            "Ada article_id hasil hash yang bukan 64 karakter."
        )

    if df["article_id"].duplicated().any():
        raise ValueError(
            "Ada benturan SHA-256 article_id di dalam CSV."
        )

    # Convert timestamps to Jakarta local time.
    df["published_at"] = parse_local_timestamp(
        df["published_at"],
        "published_at"
    )

    df["scraped_at"] = parse_local_timestamp(
        df["scraped_at"],
        "scraped_at"
    )

    # Build insight summary.
    df["insight_summary"] = (
        df["title"].astype(str)
        + ". Ringkasan ANTARA: "
        + df["summary"].astype(str)
    )

    # Database taxonomy mapping.
    df["source"] = SOURCE_NAME
    df["channel"] = CHANNEL_NAME
    df["topic"] = TOPIC_NAME
    df["subtopic"] = df["sector3_topic"]

    df["content_status"] = CONTENT_STATUS_NAME

    # Fields not available or verified in Search data.
    for column in [
        "event_type",
        "technology",
        "industry",
        "business_action",
        "impact",
    ]:
        df[column] = None

    df = df[DB_COLUMNS].copy()

    return df


# ============================================================
# 6. PRINT SUMMARY
# ============================================================

def print_summary(
    df: pd.DataFrame,
    heading: str = "VALIDASI INPUT"
) -> None:

    print("\n" + "=" * 70)
    print(heading)
    print("=" * 70)

    print(f"Rows in input       : {len(df):,}")
    print(f"Unique URLs         : {df['url'].nunique():,}")
    print(
        f"Unique DB article_id: "
        f"{df['article_id'].nunique():,}"
    )

    print(f"Source              : {SOURCE_NAME}")
    print(f"Channel             : {CHANNEL_NAME}")
    print(f"Topic               : {TOPIC_NAME}")
    print(f"Content status      : {CONTENT_STATUS_NAME}")

    print("Subtopic distribution:")

    for subtopic, count in (
        df["subtopic"]
        .value_counts()
        .sort_index()
        .items()
    ):
        print(f"  {subtopic}: {count}")


# ============================================================
# 7. DATABASE CONNECTION
# ============================================================

def create_engine_from_env():

    if not DB_PASSWORD:
        raise RuntimeError(
            "DB_PASSWORD belum diset. Di PowerShell jalankan:\n"
            '$env:POSTGRES_PASSWORD = "<password PostgreSQL kamu>"\n'
            "Jangan menulis password langsung di dalam script."
        )

    if not all([DB_HOST, DB_NAME, DB_USER]):
        raise RuntimeError(
            "Konfigurasi Neon belum lengkap. "
            "Pastikan POSTGRES_HOST, POSTGRES_DB, dan POSTGRES_USER tersedia."
        )

    from sqlalchemy import create_engine
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

    return create_engine(
        db_url,
        pool_pre_ping=True
    )

# ============================================================
# 8. CHECK DATABASE SCHEMA
# ============================================================

def check_table_schema(conn) -> None:

    from sqlalchemy import text

    exists = conn.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema_name
                  AND table_name = :table_name
            )
        """),
        {
            "schema_name": SCHEMA_NAME,
            "table_name": TABLE_NAME,
        },
    ).scalar_one()

    if not exists:
        raise RuntimeError(
            f"Tabel {FULL_TABLE_NAME} tidak ditemukan. "
            "Loader ini tidak membuat atau memigrasikan tabel."
        )

    required_db_columns = set(DB_COLUMNS)

    actual_columns = set(
        conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema_name
                  AND table_name = :table_name
            """),
            {
                "schema_name": SCHEMA_NAME,
                "table_name": TABLE_NAME,
            },
        ).scalars().all()
    )

    missing_db_columns = sorted(
        required_db_columns - actual_columns
    )

    if missing_db_columns:
        raise RuntimeError(
            f"Kolom tabel {FULL_TABLE_NAME} tidak lengkap: "
            + ", ".join(missing_db_columns)
        )


# ============================================================
# 9. CHECK EXISTING IDS AND URLS
# ============================================================

def find_existing_conflicts(
    conn,
    df: pd.DataFrame
):
    """Find already-loaded records and identity conflicts."""

    from sqlalchemy import bindparam, text

    urls = df["url"].tolist()
    ids = df["article_id"].tolist()

    by_url_stmt = text(f"""
        SELECT article_id, url, source, channel
        FROM {FULL_TABLE_NAME}
        WHERE url IN :values
    """).bindparams(
        bindparam("values", expanding=True)
    )

    by_id_stmt = text(f"""
        SELECT article_id, url, source, channel
        FROM {FULL_TABLE_NAME}
        WHERE article_id IN :values
    """).bindparams(
        bindparam("values", expanding=True)
    )

    url_rows = (
        conn.execute(
            by_url_stmt,
            {"values": urls}
        )
        .mappings()
        .all()
    )

    id_rows = (
        conn.execute(
            by_id_stmt,
            {"values": ids}
        )
        .mappings()
        .all()
    )

    existing_by_url = {
        row["url"]: dict(row)
        for row in url_rows
    }

    existing_by_id = {
        row["article_id"]: dict(row)
        for row in id_rows
    }

    already_loaded = []
    new_records = []
    conflicts = []

    for record in df.to_dict(orient="records"):

        expected_id = record["article_id"]
        expected_url = record["url"]

        existing_url = existing_by_url.get(expected_url)
        existing_id = existing_by_id.get(expected_id)

        if (
            existing_url is None
            and existing_id is None
        ):
            new_records.append(record)
            continue

        # Safe rerun:
        # skip only if ID, URL, source, and channel all match.
        if (
            existing_url is not None
            and existing_id is not None
            and existing_url["article_id"] == expected_id
            and existing_id["url"] == expected_url
            and existing_url["source"] == SOURCE_NAME
            and existing_url["channel"] == CHANNEL_NAME
        ):
            already_loaded.append(record)
            continue

        conflicts.append({
            "expected_article_id": expected_id,
            "expected_url": expected_url,
            "existing_by_url": existing_url,
            "existing_by_id": existing_id,
        })

    return (
        new_records,
        already_loaded,
        conflicts,
    )


# ============================================================
# 10. PRINT CONFLICT DETAILS
# ============================================================

def print_conflicts(conflicts) -> None:

    print("\nKONFLIK IDENTITAS DATABASE:")

    for item in conflicts[:10]:

        print(f"- URL input: {item['expected_url']}")
        print(f"  ID input : {item['expected_article_id']}")

        if item["existing_by_url"]:
            print(
                "  Baris URL yang ada: "
                f"{item['existing_by_url']}"
            )

        if item["existing_by_id"]:
            print(
                "  Baris ID yang ada : "
                f"{item['existing_by_id']}"
            )

    if len(conflicts) > 10:
        print(
            f"... dan {len(conflicts) - 10} konflik lainnya."
        )


# ============================================================
# 11. DATABASE CHECK AND INSERT
# ============================================================

def run_database_check(
    df: pd.DataFrame,
    insert: bool
) -> None:

    from sqlalchemy import text

    engine = create_engine_from_env()

    try:

        with engine.begin() as conn:

            check_table_schema(conn)

            (
                new_records,
                already_loaded,
                conflicts,
            ) = find_existing_conflicts(conn, df)

            print_summary(
                df,
                "PEMERIKSAAN DATABASE ANTARA SEARCH"
            )

            print(
                f"Artikel baru        : {len(new_records):,}"
            )

            print(
                f"Sudah pernah dimuat : {len(already_loaded):,}"
            )

            print(
                f"Konflik ID/URL      : {len(conflicts):,}"
            )

            if conflicts:

                print_conflicts(conflicts)

                raise RuntimeError(
                    "Ditemukan konflik article_id/URL. "
                    "Tidak ada data yang diinsert."
                )

            if not insert:

                print(
                    "\nCHECK DATABASE BERHASIL: "
                    "tidak ada perubahan database. "
                    "Gunakan tanpa --check-db atau --dry-run "
                    "untuk melakukan INSERT."
                )

                return

            if not new_records:

                print(
                    "\nTidak ada artikel baru. "
                    "Database tidak diubah."
                )

            else:

                records = [
                    {
                        key: db_scalar(value)
                        for key, value in record.items()
                    }
                    for record in new_records
                ]

                result = conn.execute(
                    text(INSERT_SQL),
                    records
                )

                print(
                    f"\nBaris INSERT diproses: "
                    f"{result.rowcount:,}"
                )

        # Read-after-write verification.
        with engine.connect() as conn:

            total = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM {FULL_TABLE_NAME}"
                )
            ).scalar_one()

            antara_search_total = conn.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM {FULL_TABLE_NAME}
                    WHERE source = :source
                      AND channel = :channel
                """),
                {
                    "source": SOURCE_NAME,
                    "channel": CHANNEL_NAME,
                },
            ).scalar_one()

            topic_rows = conn.execute(
                text(f"""
                    SELECT
                        subtopic,
                        COUNT(*) AS total
                    FROM {FULL_TABLE_NAME}
                    WHERE source = :source
                      AND channel = :channel
                    GROUP BY subtopic
                    ORDER BY subtopic
                """),
                {
                    "source": SOURCE_NAME,
                    "channel": CHANNEL_NAME,
                },
            ).all()

        print("\nLOAD ANTARA SEARCH BERHASIL")

        print(
            f"Total seluruh sumber di DB : {total:,}"
        )

        print(
            f"Total ANTARA Search di DB  : "
            f"{antara_search_total:,}"
        )

        print(
            "Distribusi subtopic ANTARA Search:"
        )

        for row in topic_rows:
            print(
                f"  {row.subtopic or 'NULL'}: "
                f"{row.total}"
            )

        print(
            f"Database: {DB_NAME}; "
            f"tabel: {FULL_TABLE_NAME}"
        )

    finally:
        engine.dispose()


# ============================================================
# 12. MAIN
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Load ANTARA Search relevant articles "
            "to PostgreSQL (insert-only)."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_FILE,
        help=(
            "CSV artikel Relevan; default mengarah "
            "ke output batch V5."
        ),
    )

    modes = parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validasi CSV saja; tidak menghubungi PostgreSQL."
        ),
    )

    modes.add_argument(
        "--check-db",
        action="store_true",
        help=(
            "Periksa skema dan konflik database "
            "tanpa melakukan INSERT."
        ),
    )

    args = parser.parse_args()

    print("=" * 70)
    print("LOAD ANTARA SEARCH TO POSTGRESQL")
    print("=" * 70)

    df = load_and_validate(args.input)

    print_summary(df)

    if args.dry_run:

        print(
            "\nDRY RUN BERHASIL: CSV valid; "
            "tidak ada koneksi atau perubahan database."
        )

        return

    run_database_check(
        df,
        insert=not args.check_db
    )


if __name__ == "__main__":
    main() 