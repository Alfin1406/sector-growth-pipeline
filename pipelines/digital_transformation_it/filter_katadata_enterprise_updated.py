"""Filter Katadata articles using integrated Sector 3 audit labels.

Place this file at: 04_filtering/filter_katadata_enterprise.py
Input:
  data/processed/katadata_enterprise_clean.csv
Outputs:
  data/processed/katadata_enterprise_filtered_all_classified.csv
  data/processed/katadata_enterprise_filtered.csv
  data/processed/katadata_enterprise_filter_review_required.csv
  data/processed/katadata_enterprise_filter_out_of_scope.csv

Priority:
1) Manual audit label (audit_relevance_level) when available.
2) Scraper's automatic label (relevance_level) for new URLs that have not
   been manually audited yet.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "data" / "processed" / "katadata_enterprise_clean.csv"
OUTPUT_ALL = ROOT / "data" / "processed" / "katadata_enterprise_filtered_all_classified.csv"
OUTPUT_FILTERED = ROOT / "data" / "processed" / "katadata_enterprise_filtered.csv"
OUTPUT_REVIEW = ROOT / "data" / "processed" / "katadata_enterprise_filter_review_required.csv"
OUTPUT_OUT_OF_SCOPE = ROOT / "data" / "processed" / "katadata_enterprise_filter_out_of_scope.csv"

VALID_LABELS = {"Relevan", "Perlu Tinjau", "Di Luar Cakupan"}


def clean_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def classify_from_labels(row: pd.Series) -> dict[str, Any]:
    """Use audit labels where present; avoid rescoring the whole article with ERP-only keywords."""
    audit_level = clean_value(row.get("audit_relevance_level"))
    auto_level = clean_value(row.get("relevance_level"))
    audit_topic = clean_value(row.get("audit_sector3_topic"))
    auto_topic = clean_value(row.get("sector3_topic"))

    if audit_level in VALID_LABELS:
        chosen_level = audit_level
        chosen_topic = audit_topic or auto_topic or "Belum diklasifikasikan"
        reason = clean_value(row.get("audit_reason")) or clean_value(row.get("classification_reason"))
        classification_source = "Manual audit"
    elif auto_level in VALID_LABELS:
        chosen_level = auto_level
        chosen_topic = auto_topic or "Belum diklasifikasikan"
        reason = clean_value(row.get("classification_reason"))
        classification_source = "Automatic scraper classification"
    else:
        # Unknown/unlabelled articles should not be silently treated as relevant.
        chosen_level = "Perlu Tinjau"
        chosen_topic = auto_topic or "Belum diklasifikasikan"
        reason = "Label relevansi tidak tersedia atau tidak dikenali; perlu pemeriksaan manual."
        classification_source = "Fallback review"

    is_relevant = chosen_level == "Relevan"
    matched = clean_value(row.get("matched_keywords"))
    if not matched:
        # For the audit-driven flow this field is intentionally explanatory,
        # rather than a fabricated keyword match.
        matched = chosen_topic if is_relevant else ""

    return {
        "is_relevant": is_relevant,
        "subtopic": chosen_topic,
        "matched_keywords": matched,
        "filter_reason": reason,
        "filter_relevance_level": chosen_level,
        "filter_classification_source": classification_source,
    }


def main() -> None:
    print("=" * 64)
    print("FILTERING KATADATA - SECTOR 3")
    print("=" * 64)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig", low_memory=False)
    print(f"Input dataset: {len(df)} rows")

    required = {"url", "title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak tersedia: {sorted(missing)}")

    # Ensure output doesn't duplicate fields when re-run over an already filtered CSV.
    generated_columns = [
        "is_relevant", "subtopic", "matched_keywords", "filter_reason",
        "filter_relevance_level", "filter_classification_source",
    ]
    df = df.drop(columns=[c for c in generated_columns if c in df.columns], errors="ignore")

    results = df.apply(classify_from_labels, axis=1, result_type="expand")
    classified = pd.concat([df.reset_index(drop=True), results.reset_index(drop=True)], axis=1)

    OUTPUT_ALL.parent.mkdir(parents=True, exist_ok=True)
    classified.to_csv(OUTPUT_ALL, index=False, encoding="utf-8-sig")

    relevant = classified[classified["filter_relevance_level"].eq("Relevan")].copy()
    review = classified[classified["filter_relevance_level"].eq("Perlu Tinjau")].copy()
    out_of_scope = classified[classified["filter_relevance_level"].eq("Di Luar Cakupan")].copy()

    relevant.to_csv(OUTPUT_FILTERED, index=False, encoding="utf-8-sig")
    review.to_csv(OUTPUT_REVIEW, index=False, encoding="utf-8-sig")
    out_of_scope.to_csv(OUTPUT_OUT_OF_SCOPE, index=False, encoding="utf-8-sig")

    print("\nFILTERING SELESAI")
    print("-" * 64)
    print(f"Semua terklasifikasi : {OUTPUT_ALL} ({len(classified)} rows)")
    print(f"Relevan              : {OUTPUT_FILTERED} ({len(relevant)} rows)")
    print(f"Perlu tinjau         : {OUTPUT_REVIEW} ({len(review)} rows)")
    print(f"Di luar cakupan      : {OUTPUT_OUT_OF_SCOPE} ({len(out_of_scope)} rows)")

    print("\nDistribusi status relevansi:")
    print(classified["filter_relevance_level"].value_counts(dropna=False).to_string())

    print("\nDistribusi topik Sector 3 (artikel relevan):")
    if len(relevant):
        print(relevant["subtopic"].value_counts(dropna=False).to_string())
    else:
        print("Tidak ada artikel berstatus Relevan.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
