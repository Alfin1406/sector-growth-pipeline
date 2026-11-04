"""Normalize Detik.com V5 results to the four established Sector 3 topics.

Reads:  data/processed/detik_sector3_filtered_all_classified_v5.csv
Writes:
  data/processed/detik_sector3_filtered_all_classified_four_topics_v5.csv
  data/processed/detik_sector3_filtered_four_topics_v5.csv
  data/processed/detik_sector3_filter_review_required_four_topics_v5.csv
  data/processed/detik_sector3_filter_out_of_scope_four_topics_v5.csv
  data/processed/detik_sector3_topic_normalization_v5_report.csv

The original V5 labels are preserved in *_v5_original columns. Articles under
Enterprise Data & AI are assigned to one of the four categories only when the
title contains a sufficiently strong topical signal. Otherwise the article is
moved to Perlu Tinjau rather than forced into a category.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
INPUT_FILE = DATA_DIR / "detik_sector3_filtered_all_classified_v5.csv"
OUTPUT_ALL = DATA_DIR / "detik_sector3_filtered_all_classified_four_topics_v5.csv"
OUTPUT_RELEVANT = DATA_DIR / "detik_sector3_filtered_four_topics_v5.csv"
OUTPUT_REVIEW = DATA_DIR / "detik_sector3_filter_review_required_four_topics_v5.csv"
OUTPUT_OUT_OF_SCOPE = DATA_DIR / "detik_sector3_filter_out_of_scope_four_topics_v5.csv"
OUTPUT_REPORT = DATA_DIR / "detik_sector3_topic_normalization_v5_report.csv"

FOUR_TOPICS = [
    "Enterprise Software",
    "Cyber Security",
    "Digital Transformation",
    "Cloud Enterprise",
]
SOURCE_EXTRA_TOPIC = "Enterprise Data & AI"
ALLOWED_RELEVANCE = {"Relevan", "Perlu Tinjau", "Di Luar Cakupan"}

# These phrases are domain-specific signals, not a claim that every mention
# alone proves relevance. Title hits dominate; body/candidate hits are supporting.
SIGNALS: dict[str, dict[str, list[str]]] = {
    "Cyber Security": {
        "title": [
            "cyber security", "cybersecurity", "keamanan siber", "serangan siber",
            "ancaman siber", "malware", "ransomware", "phishing", "spyware",
            "hacker", "peretas", "diretas", "meretas", "peretasan", "dibobol",
            "kebocoran data", "data breach", "data leak", "pencurian kredensial",
            "pencurian password", "celah keamanan", "kerentanan", "eksploit",
            "serangan api", "keamanan chatbot", "siluman ai", "retas perusahaan",
            "serangan siber ke", "serangan siber terhadap", "keamanan mobile banking",
        ],
        "body": [
            "cyber security", "cybersecurity", "keamanan siber", "serangan siber",
            "malware", "ransomware", "phishing", "spyware", "peretasan", "peretas",
            "kebocoran data", "data breach", "data leak", "celah keamanan",
            "kerentanan", "eksploit", "pencurian kredensial", "serangan api",
        ],
    },
    "Cloud Enterprise": {
        "title": [
            "data center", "data centre", "pusat data", "cloud", "komputasi awan",
            "storage", "server", "gpu", "chip ai", "chip", "semikonduktor",
            "pabrik ai", "ai factory", "infrastruktur ai", "infrastruktur komputasi",
            "ai grid", "ai-ran", "5g", "fiber optik", "kabel laut", "kabel optik",
            "satelit", "frekuensi", "telekomunikasi", "jaringan 5g", "jaringan internet",
            "jaringan telekomunikasi", "broadband", "kabel bawah laut", "bts",
            "cloud computing", "ai compute", "nvidia vera rubin", "data warehouse",
            "chip 2nm", "kabel fiber", "koneksi satelit", "infrastruktur jaringan",
        ],
        "body": [
            "data center", "data centre", "pusat data", "cloud computing", "cloud",
            "gpu", "semikonduktor", "chip ai", "server", "storage", "infrastruktur ai",
            "ai-ran", "5g", "fiber optik", "kabel laut", "satelit", "frekuensi",
            "jaringan telekomunikasi", "infrastruktur jaringan", "broadband", "data warehouse",
        ],
    },
    "Enterprise Software": {
        "title": [
            "enterprise software", "software bisnis", "perangkat lunak", "software erp",
            "sistem erp", "erp", "crm", "hris", "hcm", "saas", "sap ", "oracle",
            "salesforce", "platform", "suite", "workflow", "voice agent", "asisten kerja",
            "aplikasi bisnis", "aplikasi untuk bisnis", "layanan pelanggan", "customer service",
            "sistem komunikasi", "sistem informasi", "perangkat lunak", "solusi software",
            "software ai", "ai untuk layanan", "ai untuk pelanggan", "ai marketing",
            "platform digital marketing", "ai dan solusi digital terpadu", "ai assistant",
        ],
        "body": [
            "enterprise software", "software erp", "erp", "crm", "hris", "hcm", "saas",
            "perangkat lunak", "platform bisnis", "workflow", "layanan pelanggan",
            "customer service", "sistem informasi", "aplikasi bisnis", "agentic ai",
            "solusi digital", "platform ai", "otomasi layanan pelanggan",
        ],
    },
    "Digital Transformation": {
        "title": [
            "transformasi digital", "digitalisasi", "akselerasi digital", "adopsi ai",
            "adopsi kecerdasan buatan", "penerapan ai", "implementasi ai", "menggunakan ai",
            "memakai ai", "pakai ai", "ai ubah", "ai mengubah", "mengubah cara",
            "produktivitas", "otomasi", "otomatisasi", "robot", "rantai pasok",
            "logistik", "operasional", "efisiensi operasional", "perusahaan siap ai",
            "perusahaan sudah pakai ai", "ai untuk industri", "industri manufaktur",
            "modernisasi workflow", "ai jadi aksi nyata", "perusahaan indonesia pakai ai",
            "ai di sektor", "ai untuk operasional", "ai mengubah hidup", "proses bisnis",
            "kerja dokter", "karyawan", "talenta kreatif", "akselerasi bisnis digital",
            "ai dongkrak", "ai dorong produktivitas", "ai meningkatkan produktivitas",
        ],
        "body": [
            "transformasi digital", "digitalisasi", "adopsi ai", "penerapan ai", "implementasi ai",
            "produktivitas", "otomasi", "otomatisasi", "rantai pasok", "logistik", "operasional",
            "efisiensi operasional", "proses bisnis", "karyawan", "industri manufaktur",
            "akselerasi digital", "digitalisasi proses", "AI untuk operasional".lower(),
        ],
    },
}


def text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def phrases_found(haystack: str, phrases: list[str]) -> list[str]:
    haystack = haystack.lower()
    return list(dict.fromkeys(p for p in phrases if p.strip() and p.lower() in haystack))


def category_scores(row: pd.Series) -> tuple[dict[str, float], dict[str, dict[str, list[str]]]]:
    title = text(row.get("title", "")).lower()
    body = text(row.get("content", ""))[:3000].lower()
    candidates = text(row.get("sector3_topic_candidates", "")).lower()
    all_hits: dict[str, dict[str, list[str]]] = {}
    scores: dict[str, float] = {}
    for category, terms in SIGNALS.items():
        title_hits = phrases_found(title, terms["title"])
        body_hits = phrases_found(body, terms["body"])
        candidate_hit = category.lower() in candidates
        # Cap title/body contributions so a word-rich title or body cannot dominate.
        score = min(len(title_hits), 2) * 5.0
        score += min(len(body_hits), 4) * 0.35
        score += 0.9 if candidate_hit else 0.0
        scores[category] = score
        all_hits[category] = {
            "title": title_hits,
            "body": body_hits,
            "candidate": [category] if candidate_hit else [],
        }
    return scores, all_hits


def normalize_ai_topic(row: pd.Series) -> tuple[str | None, str, str, dict[str, float]]:
    """Return mapped topic or None, status, explanation, scores."""
    scores, hits = category_scores(row)
    title_scores = {
        cat: min(len(hits[cat]["title"]), 2) * 5.0
        for cat in FOUR_TOPICS
    }
    # Require a strong title signal and let it outrank body-only mentions.
    # Body/candidate evidence is only a tie-breaker when the title contains
    # strong signals for more than one of the four domains.
    best_title_score = max(title_scores.values())
    if best_title_score >= 5.0:
        title_leaders = [cat for cat in FOUR_TOPICS if title_scores[cat] == best_title_score]
        if len(title_leaders) == 1:
            winner = title_leaders[0]
            evidence = ", ".join(hits[winner]["title"][:4])
            return winner, "Mapped", f"Dipetakan otomatis ke {winner} berdasarkan sinyal judul: {evidence}.", scores

        tied = sorted(title_leaders, key=lambda cat: scores[cat], reverse=True)
        leader_margin = scores[tied[0]] - scores[tied[1]]
        if leader_margin >= 1.0:
            winner = tied[0]
            evidence = ", ".join(hits[winner]["title"][:4])
            return winner, "Mapped", f"Dipetakan otomatis ke {winner}; sinyal judul berimbang dan konteks pendukung mengungguli alternatif. Bukti: {evidence}.", scores

        return None, "Needs review", "Judul memuat sinyal kuat yang seimbang untuk lebih dari satu topik; tidak dipaksakan ke satu kategori.", scores

    return None, "Needs review", "Tidak ada sinyal judul yang cukup spesifik untuk dipetakan ke empat topik proyek; dipindahkan ke Perlu Tinjau.", scores


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"[ERROR] Input tidak ditemukan: {INPUT_FILE}")
        return 1
    try:
        df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig", keep_default_na=False)
    except Exception as exc:
        print(f"[ERROR] Gagal membaca CSV: {exc}")
        return 1
    if df.empty:
        print("[ERROR] Input kosong.")
        return 1
    required = {"title", "url", "sector3_topic", "relevance_level"}
    missing = required - set(df.columns)
    if missing:
        print(f"[ERROR] Kolom wajib tidak tersedia: {sorted(missing)}")
        return 1

    original_topic = df["sector3_topic"].astype(str).str.strip()
    original_label = df["relevance_level"].astype(str).str.strip()
    df["sector3_topic_v5_original"] = original_topic
    df["relevance_level_v5_original"] = original_label
    df["sector3_topic_normalization_status"] = "Unchanged"
    df["topic_normalization_reason"] = "Label V5 dipertahankan."
    df["topic_normalization_confidence"] = "Tinggi"
    df["topic_normalization_scores"] = ""

    normalized_topics: list[str] = []
    normalized_labels: list[str] = []
    statuses: list[str] = []
    reasons: list[str] = []
    confidences: list[str] = []
    score_texts: list[str] = []

    for _, row in df.iterrows():
        topic = text(row.get("sector3_topic"))
        label = text(row.get("relevance_level"))
        norm_topic = topic
        norm_label = label
        status = "Unchanged"
        reason = "Label V5 dipertahankan."
        confidence = "Tinggi"
        scores_as_text = ""

        if topic in FOUR_TOPICS:
            status = "Already one of the four topics"
            reason = f"Topik V5 sudah termasuk empat topik proyek: {topic}."
        elif topic == SOURCE_EXTRA_TOPIC and label in {"Relevan", "Perlu Tinjau"}:
            mapped, map_status, reason, scores = normalize_ai_topic(row)
            scores_as_text = "; ".join(f"{cat}={scores[cat]:.2f}" for cat in FOUR_TOPICS)
            if mapped:
                norm_topic = mapped
                status = "Mapped"
                confidence = "Sedang" if max(scores.values()) < 7 else "Tinggi"
                if label == "Relevan":
                    norm_label = "Relevan"
            else:
                norm_topic = "Perlu Tinjau"
                norm_label = "Perlu Tinjau"
                status = "Needs review"
                confidence = "Rendah"
        elif label == "Relevan" and topic not in FOUR_TOPICS:
            norm_topic = "Perlu Tinjau"
            norm_label = "Perlu Tinjau"
            status = "Needs review"
            reason = f"Topik sumber '{topic}' belum dapat dinormalisasi ke empat topik proyek."
            confidence = "Rendah"
        elif label == "Perlu Tinjau" and topic not in FOUR_TOPICS:
            norm_topic = "Perlu Tinjau"
            norm_label = "Perlu Tinjau"
            status = "Needs review"
            reason = f"Artikel masih berstatus Perlu Tinjau dan tidak dipaksakan ke salah satu topik. Topik sumber: '{topic}'."
            confidence = "Rendah"
        elif label == "Di Luar Cakupan":
            norm_topic = "Di Luar Cakupan"
            norm_label = "Di Luar Cakupan"
            status = "Out of scope preserved"
            reason = "Label Di Luar Cakupan dari V5 dipertahankan."
            confidence = "Tinggi"

        normalized_topics.append(norm_topic)
        normalized_labels.append(norm_label)
        statuses.append(status)
        reasons.append(reason)
        confidences.append(confidence)
        score_texts.append(scores_as_text)

    df["sector3_topic"] = normalized_topics
    df["relevance_level"] = normalized_labels
    df["sector3_topic_normalization_status"] = statuses
    df["topic_normalization_reason"] = reasons
    df["topic_normalization_confidence"] = confidences
    df["topic_normalization_scores"] = score_texts

    # Split without dropping traceability columns.
    relevant = df[(df["relevance_level"] == "Relevan") & df["sector3_topic"].isin(FOUR_TOPICS)].copy()
    review = df[df["relevance_level"] == "Perlu Tinjau"].copy()
    out_scope = df[df["relevance_level"] == "Di Luar Cakupan"].copy()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        (df, OUTPUT_ALL),
        (relevant, OUTPUT_RELEVANT),
        (review, OUTPUT_REVIEW),
        (out_scope, OUTPUT_OUT_OF_SCOPE),
    ]
    try:
        for frame, path in outputs:
            temp = path.with_name(path.stem + ".tmp.csv")
            frame.to_csv(temp, index=False, encoding="utf-8-sig")
            temp.replace(path)

        # Overall transition report.
        report = (
            df.groupby(
                ["relevance_level_v5_original", "sector3_topic_v5_original", "relevance_level", "sector3_topic", "sector3_topic_normalization_status"],
                dropna=False,
            ).size().reset_index(name="article_count")
            .sort_values(["relevance_level_v5_original", "sector3_topic_v5_original", "relevance_level", "sector3_topic"])
        )
        report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")
    except Exception as exc:
        print(f"[ERROR] Gagal menyimpan output: {exc}")
        return 1

    print("=" * 72)
    print("NORMALISASI DETIK V5 KE 4 TOPIK PROYEK")
    print("=" * 72)
    print(f"Input                        : {INPUT_FILE} ({len(df):,} artikel)")
    print(f"Semua hasil ternormalisasi  : {OUTPUT_ALL}")
    print(f"Relevan dalam 4 topik       : {OUTPUT_RELEVANT} ({len(relevant):,})")
    print(f"Perlu Tinjau                : {OUTPUT_REVIEW} ({len(review):,})")
    print(f"Di Luar Cakupan             : {OUTPUT_OUT_OF_SCOPE} ({len(out_scope):,})")
    print(f"Laporan transisi            : {OUTPUT_REPORT}")
    print("\nDistribusi status hasil normalisasi:")
    print(df["relevance_level"].value_counts(dropna=False).to_string())
    print("\nDistribusi topik pada artikel Relevan:")
    print(relevant["sector3_topic"].value_counts(dropna=False).to_string())
    print("\nPerpindahan dari Enterprise Data & AI:")
    ai = df[df["sector3_topic_v5_original"].eq(SOURCE_EXTRA_TOPIC)]
    print(pd.crosstab(ai["relevance_level"], ai["sector3_topic"], dropna=False).to_string())
    print("\nCatatan: hasil ini berbasis aturan; artikel yang tidak memiliki sinyal judul kuat tetap di Perlu Tinjau.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
