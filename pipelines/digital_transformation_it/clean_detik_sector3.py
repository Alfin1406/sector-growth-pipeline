import hashlib
import html
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "detik_sector3_raw.csv"
)

OUTPUT_FILE = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "detik_sector3_clean.csv"
)

TARGET_YEAR = 2026

REQUIRED_COLUMNS = [
    "article_id",
    "title",
    "url",
    "published_at",
    "channel",
    "source",
    "content",
    "content_status",
    "scraped_at",
]

print("=" * 65)
print("CLEANING DETIK.COM - SECTOR 3")
print("=" * 65)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """Membersihkan HTML, whitespace, dan karakter tak terlihat."""

    if pd.isna(value):
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)

    # Hapus karakter zero-width dan BOM.
    value = re.sub(r"[\u200b-\u200f\ufeff]", "", value)

    # Rapikan whitespace berulang.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(value):
    """Menormalkan URL agar variasi tracking tidak membuat duplikat."""

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if not value:
        return ""

    try:
        parts = urlsplit(value)

        if parts.scheme.lower() not in {"http", "https"}:
            return ""

        if not parts.netloc:
            return ""

        # Parameter query dan fragment dibuang karena URL berita
        # Detik.com yang digunakan scraper adalah URL artikel.
        path = parts.path.rstrip("/")

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                path,
                "",
                "",
            )
        )

    except ValueError:
        return ""


def generate_article_id(url):
    """Membuat ID artikel stabil berdasarkan URL."""

    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()


# ============================================================
# LOAD DATA
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"File input tidak ditemukan: {INPUT_FILE}"
    )

df = pd.read_csv(
    INPUT_FILE,
    encoding="utf-8-sig",
)

print(f"Input file          : {INPUT_FILE}")
print(f"Raw dataset         : {len(df)} baris")

if df.empty:
    raise ValueError(
        "Dataset raw kosong. File output tidak diperbarui."
    )

missing_columns = [
    col for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Kolom wajib tidak ditemukan: {missing_columns}"
    )

df = df[REQUIRED_COLUMNS].copy()


# ============================================================
# CLEAN TEXT
# ============================================================

text_columns = [
    "title",
    "channel",
    "source",
    "content",
    "content_status",
]

for col in text_columns:
    df[col] = df[col].map(clean_text)

# Normalisasi URL.
df["url"] = df["url"].map(normalize_url)

# Dataset ini hanya berasal dari Detik.com.
df["source"] = "Detik.com"

# Hilangkan spasi di kolom ID.
df["article_id"] = (
    df["article_id"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# VALIDATE REQUIRED DATA
# ============================================================

before_validation = len(df)

df = df[
    (df["title"] != "")
    & (df["url"] != "")
].copy()

invalid_title_or_url = (
    before_validation - len(df)
)

print(
    f"Baris tanpa judul/URL dihapus : "
    f"{invalid_title_or_url}"
)


# ============================================================
# VALIDATE PUBLICATION DATE
# ============================================================

# published_at diproses tanpa menggantinya dengan scraped_at.
# Timestamp sumber scraper disimpan dalam waktu lokalnya.
df["published_at"] = pd.to_datetime(
    df["published_at"],
    errors="coerce",
)

missing_date = int(
    df["published_at"].isna().sum()
)

before_year_filter = len(df)

df = df[
    df["published_at"].notna()
    & (df["published_at"].dt.year == TARGET_YEAR)
].copy()

excluded_date = before_year_filter - len(df)

print(f"Tanggal publikasi tidak valid : {missing_date}")
print(
    f"Artikel tanpa tanggal valid/"
    f"di luar {TARGET_YEAR} : {excluded_date}"
)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

before_dedup = len(df)

# Pilih versi dengan konten terpanjang jika URL yang sama
# muncul lebih dari sekali.
df["_content_length"] = (
    df["content"].fillna("").astype(str).str.len()
)

df = (
    df.sort_values(
        by="_content_length",
        ascending=False,
        kind="stable",
    )
    .drop_duplicates(
        subset=["url"],
        keep="first",
    )
    .drop(columns=["_content_length"])
)

duplicates_removed = before_dedup - len(df)

# Pastikan article_id stabil dan konsisten dengan URL.
df["article_id"] = df["url"].map(generate_article_id)


# ============================================================
# NORMALIZE TIMESTAMPS
# ============================================================

df["published_at"] = df["published_at"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)

# scraped_at adalah waktu pengambilan data, bukan tanggal publikasi.
df["scraped_at"] = pd.to_datetime(
    df["scraped_at"],
    errors="coerce",
).dt.strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# SORT AND SAVE
# ============================================================

df = df.sort_values(
    by="published_at",
    ascending=False,
).reset_index(drop=True)

if df.empty:
    raise ValueError(
        "Tidak ada artikel valid tahun 2026. "
        "File output lama tidak diperbarui."
    )

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("CLEANING SELESAI")
print("=" * 65)

print(f"Output file           : {OUTPUT_FILE}")
print(f"Raw input             : {before_validation} baris")
print(f"Dataset final         : {len(df)} baris")
print(f"Baris invalid dihapus : {invalid_title_or_url}")
print(f"Duplikat URL dihapus  : {duplicates_removed}")
print(f"Tanggal tidak valid   : {missing_date}")
print(f"Target tahun          : {TARGET_YEAR}")
print(f"URL unik              : {df['url'].nunique()}")

print("\nDistribusi channel:")
print(
    df["channel"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nContent status:")
print(
    df["content_status"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nRentang publikasi:")
print(f"Terawal : {df['published_at'].min()}")
print(f"Terbaru : {df['published_at'].max()}")

print("\nPreview:")
print(
    df[
        [
            "title",
            "published_at",
            "channel",
            "content_status",
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\n[SUCCESS] File cleaning berhasil disimpan.")