
from pathlib import Path
import html
import re
import unicodedata
from urllib.parse import urlparse, urlunparse

import pandas as pd


# ============================================================
# 1. PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "antara_search_content_prepared.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "antara_search_cleaned.csv"

REVIEW_FILE = (
    OUTPUT_DIR / "antara_search_cleaning_review.csv"
)

JAKARTA_TZ = "Asia/Jakarta"

# Mengikuti cutoff yang digunakan pipeline ANTARA sebelumnya.
START_DATE = pd.Timestamp(
    "2026-01-01 00:00:00",
    tz=JAKARTA_TZ
)


# ============================================================
# 2. REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "article_id",
    "source",
    "channel",
    "title",
    "url",
    "published_at",
    "summary",
    "content",
    "content_status",
    "search_query",
    "content_preparation_status",
]


# ============================================================
# 3. TEXT CLEANING
# ============================================================

def clean_text(value):
    """Membersihkan teks tanpa mengubah substansinya."""

    if value is None or pd.isna(value):
        return ""

    text = html.unescape(str(value))

    text = unicodedata.normalize("NFKC", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove control characters
    text = "".join(
        char for char in text
        if char.isprintable() or char.isspace()
    )

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# 4. URL VALIDATION
# ============================================================

def validate_url(value):

    if value is None or pd.isna(value):
        return False

    value = str(value).strip()

    if not value:
        return False

    try:
        parsed = urlparse(value)

        hostname = (
            parsed.hostname.lower().rstrip(".")
            if parsed.hostname
            else ""
        )

        valid_domain = (
            hostname == "antaranews.com"
            or hostname.endswith(".antaranews.com")
        )

        return (
            parsed.scheme.lower() == "https"
            and valid_domain
            and parsed.path.startswith("/berita/")
            and parsed.username is None
            and parsed.password is None
        )

    except (ValueError, TypeError):
        return False


def normalize_url_key(value):
    """
    Membuat URL key untuk mendeteksi duplikasi.
    Tidak mengubah URL asli.
    """

    if not validate_url(value):
        return ""

    parsed = urlparse(str(value).strip())

    path = parsed.path.rstrip("/") or "/"

    return urlunparse((
        "https",
        "antaranews.com",
        path,
        "",
        parsed.query,
        "",
    ))


# ============================================================
# 5. LOAD DATA
# ============================================================

def load_data():

    print("=" * 65)
    print("ANTARA SEARCH - DATA CLEANING")
    print("=" * 65)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
        dtype={"article_id": "string"},
        keep_default_na=False,
    )

    if df.empty:
        raise ValueError("Dataset input kosong.")

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {missing_columns}"
        )

    # Pastikan kolom teks konsisten
    text_columns = [
        "source",
        "channel",
        "title",
        "url",
        "published_at",
        "summary",
        "content",
        "content_status",
        "search_query",
        "content_preparation_status",
    ]

    for col in text_columns:
        df[col] = df[col].astype("string").fillna("")

    print(f"\nInput          : {INPUT_FILE}")
    print(f"Total artikel  : {len(df)}")

    return df


# ============================================================
# 6. CLEAN AND VALIDATE DATA
# ============================================================

def clean_data(df):

    print("\nMembersihkan dan memvalidasi data...")

    df = df.copy()

    # --------------------------------------------------------
    # A. CLEAN TEXT
    # --------------------------------------------------------

    df["title_clean"] = df["title"].apply(clean_text)

    df["summary_clean"] = df["summary"].apply(clean_text)

    # Summary-only: prepared text berasal dari judul + summary
    df["prepared_text"] = df.apply(
        lambda row: ". ".join(
            part for part in [
                row["title_clean"],
                row["summary_clean"],
            ]
            if part
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # B. DATE NORMALIZATION
    # --------------------------------------------------------

    raw_dates = (
        df["published_at"]
        .astype("string")
        .str.strip()
    )

    raw_dates = raw_dates.mask(
        raw_dates.eq(""),
        pd.NA
    )

    parsed_dates = pd.to_datetime(
    raw_dates,
    errors="coerce",
    utc=True,
    )

    jakarta_dates = parsed_dates.dt.tz_convert(
        JAKARTA_TZ
    )

    # Simpan published_at dalam format ISO 8601 Jakarta
    df["published_at"] = jakarta_dates.apply(
        lambda value: value.isoformat()
        if pd.notna(value)
        else ""
    )

    # --------------------------------------------------------
    # C. URL VALIDATION
    # --------------------------------------------------------

    df["url_valid"] = df["url"].apply(validate_url)

    # --------------------------------------------------------
    # D. DUPLICATE DETECTION
    # --------------------------------------------------------

    article_ids = (
        df["article_id"]
        .astype("string")
        .str.strip()
    )

    duplicate_article_id = (
        article_ids.ne("")
        & article_ids.duplicated(keep=False)
    )

    url_keys = df["url"].apply(normalize_url_key)

    duplicate_url = (
        url_keys.ne("")
        & url_keys.duplicated(keep=False)
    )

    df["duplicate_article_id"] = duplicate_article_id
    df["duplicate_url"] = duplicate_url

    # --------------------------------------------------------
    # E. CONTENT STATUS VALIDATION
    # --------------------------------------------------------

    content_status = (
        df["content_status"]
        .str.strip()
        .str.lower()
    )

    preparation_status = (
        df["content_preparation_status"]
        .str.strip()
        .str.lower()
    )

    content_present = df["content"].str.strip().ne("")

    # Tidak menimpa content_status asli.
    # Status summary_only harus tetap konsisten.

    # --------------------------------------------------------
    # F. VALIDATION REASONS
    # --------------------------------------------------------

    now_jakarta = pd.Timestamp.now(
        tz=JAKARTA_TZ
    )

    reasons = []

    for pos in range(len(df)):

        row = df.iloc[pos]

        errors = []

        # Article ID
        if not article_ids.iloc[pos]:
            errors.append("missing_article_id")

        if duplicate_article_id.iloc[pos]:
            errors.append("duplicate_article_id")

        # Title
        if not row["title_clean"]:
            errors.append("missing_title")

        # Summary
        if not row["summary_clean"]:
            errors.append("missing_summary")

        # URL
        if not row["url_valid"]:
            errors.append("invalid_url")

        if duplicate_url.iloc[pos]:
            errors.append("duplicate_url")

        # Publication date
        published = jakarta_dates.iloc[pos]

        if pd.isna(published):

            errors.append("invalid_published_at")

        else:

            if published < START_DATE:
                errors.append("date_before_cutoff")

            elif published > now_jakarta:
                errors.append("future_published_at")

        # Preparation status
        if preparation_status.iloc[pos] != "ready":
            errors.append("preparation_not_ready")

        # Content status
        if content_status.iloc[pos] != "summary_only":
            errors.append("unexpected_content_status")

        # Summary-only consistency
        if (
            content_status.iloc[pos] == "summary_only"
            and content_present.iloc[pos]
        ):
            errors.append(
                "content_nonempty_with_summary_only_status"
            )

        reasons.append("; ".join(errors))

    df["cleaning_errors"] = reasons

    df["cleaning_status"] = [
        "valid" if not error else "review"
        for error in reasons
    ]

    # Temporary URL key tidak disertakan dalam output
    del url_keys

    return df


# ============================================================
# 7. SAVE OUTPUT
# ============================================================

def save_output(df):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    valid_df = df[
        df["cleaning_status"] == "valid"
    ].copy()

    review_df = df[
        df["cleaning_status"] == "review"
    ].copy()

    # Pastikan tidak ada artikel yang hilang
    if len(valid_df) + len(review_df) != len(df):
        raise RuntimeError(
            "Jumlah output tidak sama dengan jumlah input."
        )

    valid_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    review_df.to_csv(
        REVIEW_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    return valid_df, review_df


# ============================================================
# 8. REPORT
# ============================================================

def print_report(df, valid_df, review_df):

    print("\n" + "=" * 65)
    print("ANTARA SEARCH - CLEANING REPORT")
    print("=" * 65)

    print(f"Total input                  : {len(df)}")
    print(f"Artikel valid                : {len(valid_df)}")
    print(f"Perlu review                 : {len(review_df)}")

    print("\nVALIDASI DATA")

    print(
        "Judul kosong                 : ",
        df["title_clean"].eq("").sum()
    )

    print(
        "Summary kosong               : ",
        df["summary_clean"].eq("").sum()
    )

    print(
        "URL tidak valid              : ",
        (~df["url_valid"]).sum()
    )

    print(
        "Tanggal tidak terbaca        : ",
        df["published_at"].eq("").sum()
    )

    print(
        "ID duplikat (baris terdampak): ",
        df["duplicate_article_id"].sum()
    )

    print(
        "URL duplikat (baris terdampak): ",
        df["duplicate_url"].sum()
    )

    print("\nCONTENT STATUS")

    print(
        df["content_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nCLEANING STATUS")

    print(
        df["cleaning_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # REVIEW REASON DISTRIBUTION
    # --------------------------------------------------------

    print("\nALASAN REVIEW")

    reason_counts = {}

    for error_string in review_df["cleaning_errors"]:

        if not error_string:
            continue

        for reason in error_string.split("; "):

            reason_counts[reason] = (
                reason_counts.get(reason, 0) + 1
            )

    if reason_counts:

        for reason, count in sorted(
            reason_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(f"{reason:<45}: {count}")

    else:
        print("Tidak ada artikel yang perlu ditinjau.")

    print("\nINTEGRITAS DATA")

    print(
        "Total valid + review          : ",
        len(valid_df) + len(review_df)
    )

    print(
        "Artikel multi-query           : ",
        df["search_query"]
        .str.contains(";", regex=False)
        .sum()
    )

    print("\nOUTPUT")

    print(f"Cleaned : {OUTPUT_FILE}")
    print(f"Review  : {REVIEW_FILE}")

    print("\n" + "=" * 65)
    print("ANTARA SEARCH CLEANING SELESAI")
    print("=" * 65)


# ============================================================
# 9. MAIN
# ============================================================

def main():

    df = load_data()

    df = clean_data(df)

    valid_df, review_df = save_output(df)

    print_report(
        df,
        valid_df,
        review_df
    )


if __name__ == "__main__":
    main() 
