"""Clean Katadata articles and apply manual Sector 3 audit labels by URL.

Place this file at: 03_cleaning/clean_katadata_enterprise.py
Expected project files:
  data/raw/katadata_enterprise_raw.csv
  data/processed/katadata_sector3_audit.csv
Output:
  data/processed/katadata_enterprise_clean.csv

Manual audit labels override automatic scraper labels for known URLs.
New URLs without a manual audit keep their automatic labels and are
marked classification_source='Automatic scraper classification'.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_FILE = ROOT / "data" / "raw" / "katadata_enterprise_raw.csv"
AUDIT_FILE = ROOT / "data" / "katadata_sector3_audit.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "katadata_enterprise_clean.csv"

AUDIT_COLUMNS = [
    "audit_sector3_topic",
    "audit_relevance_level",
    "audit_confidence",
    "audit_action",
    "audit_reason",
]


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def parse_datetime(series: pd.Series) -> pd.Series:
    """Parse timestamps safely and return naive UTC timestamps for CSV/SQL."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_convert(None)


def normalize_boolean(series: pd.Series) -> pd.Series:
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
    }
    return series.astype(str).str.strip().str.lower().map(mapping).astype("boolean")


def load_and_merge_audit(raw: pd.DataFrame) -> pd.DataFrame:
    if not AUDIT_FILE.exists():
        raise FileNotFoundError(
            f"File audit tidak ditemukan: {AUDIT_FILE}\n"
            "Simpan katadata_sector3_audit.csv di data/processed terlebih dahulu."
        )

    audit = pd.read_csv(AUDIT_FILE, encoding="utf-8-sig", low_memory=False)
    if "url" not in audit.columns:
        raise ValueError("Kolom 'url' tidak ditemukan pada CSV audit.")

    # The audit export contains all original article fields. Only join
    # audit-specific columns to avoid overwriting raw article content.
    for col in AUDIT_COLUMNS:
        if col not in audit.columns:
            audit[col] = pd.NA

    audit_small = audit[["url", *AUDIT_COLUMNS]].copy()
    audit_small["url"] = normalize_url(audit_small["url"])
    audit_small = audit_small[audit_small["url"] != ""]

    if audit_small["url"].duplicated().any():
        duplicates = int(audit_small["url"].duplicated().sum())
        raise ValueError(f"CSV audit memiliki {duplicates} URL duplikat.")

    raw["url"] = normalize_url(raw["url"])
    merged = raw.merge(
        audit_small,
        on="url",
        how="left",
        validate="many_to_one",
    )

    # Preserve the scraper's original automatic classification for traceability.
    pairs = [
        ("sector3_topic", "original_sector3_topic"),
        ("relevance_level", "original_relevance_level"),
        ("classification_confidence", "original_classification_confidence"),
        ("classification_reason", "original_classification_reason"),
    ]
    for current, original in pairs:
        if current in merged.columns and original not in merged.columns:
            merged[original] = merged[current]

    manual_match = merged["audit_relevance_level"].fillna("").astype(str).str.strip().ne("")

    # Manual audit overrides automatic labels only when the audit has a valid label.
    overrides = [
        ("sector3_topic", "audit_sector3_topic"),
        ("relevance_level", "audit_relevance_level"),
        ("classification_confidence", "audit_confidence"),
        ("classification_reason", "audit_reason"),
    ]
    for target, source in overrides:
        if target not in merged.columns:
            merged[target] = pd.NA
        if source in merged.columns:
            usable = merged[source].notna() & merged[source].astype(str).str.strip().ne("")
            merged.loc[usable, target] = merged.loc[usable, source]

    merged["classification_source"] = "Automatic scraper classification"
    merged.loc[manual_match, "classification_source"] = "Manual audit"

    return merged


def main() -> None:
    print("=" * 64)
    print("CLEANING KATADATA - SECTOR 3")
    print("=" * 64)

    if not RAW_FILE.exists():
        raise FileNotFoundError(f"File raw tidak ditemukan: {RAW_FILE}")

    df = pd.read_csv(RAW_FILE, encoding="utf-8-sig", low_memory=False)
    print(f"Raw input           : {len(df)} rows")

    required = {"url", "title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak tersedia di raw CSV: {sorted(missing)}")

    # Ensure expected content field exists.
    if "content" not in df.columns:
        df["content"] = ""
    if "published_at" not in df.columns:
        df["published_at"] = pd.NA
    if "scraped_at" not in df.columns:
        df["scraped_at"] = pd.NA

    df["title"] = df["title"].apply(clean_text)
    df["content"] = df["content"].apply(clean_text)
    df["url"] = normalize_url(df["url"])

    # Remove duplicate URLs and invalid core fields.
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first").copy()
    duplicates_removed = before_dedup - len(df)

    df = df[df["url"].ne("")].copy()
    df = df[df["title"].ne("")].copy()

    df["published_at"] = parse_datetime(df["published_at"])
    df["scraped_at"] = parse_datetime(df["scraped_at"])

    if "is_enterprise_software" in df.columns:
        df["is_enterprise_software"] = normalize_boolean(df["is_enterprise_software"])
    else:
        df["is_enterprise_software"] = pd.Series(pd.NA, index=df.index, dtype="boolean")

    df = load_and_merge_audit(df)

    df["content_status"] = df["content"].apply(
        lambda value: "SUCCESS" if isinstance(value, str) and len(value.strip()) > 100 else "EMPTY"
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M:%S")

    manual_count = int(df["classification_source"].eq("Manual audit").sum())
    automatic_count = len(df) - manual_count

    print("\nCLEANING SELESAI")
    print("-" * 64)
    print(f"Output              : {OUTPUT_FILE}")
    print(f"Final dataset       : {len(df)} rows")
    print(f"Duplicate dihapus   : {duplicates_removed}")
    print(f"Label manual audit  : {manual_count}")
    print(f"Label otomatis      : {automatic_count}")

    print("\nContent status:")
    print(df["content_status"].value_counts(dropna=False).to_string())

    print("\nStatus relevansi aktif:")
    if "relevance_level" in df.columns:
        print(df["relevance_level"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
