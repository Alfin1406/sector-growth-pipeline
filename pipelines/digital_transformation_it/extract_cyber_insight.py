import re
from pathlib import Path

import pandas as pd


# ============================================================
# 05 INSIGHT - CYBER SECURITY
# ============================================================
# Input  : data/processed/bisnis_cyber_filtered.csv
# Output : data/processed/bisnis_cyber_insight.csv
#
# Tujuan:
# - Mengambil insight terstruktur dari artikel yang sudah lolos filtering.
# - Menghindari false positive pada keyword pendek seperti "ai".
# - Memisahkan Threat, Technology, Industry, Business Action, Impact.
# - Menentukan Business Topic berdasarkan hasil klasifikasi,
#   bukan pencarian substring mentah.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/processed/bisnis_cyber_filtered.csv")
OUTPUT_FILE = Path("data/processed/bisnis_cyber_insight.csv")


# ============================================================
# KEYWORD DICTIONARIES
# ============================================================

THREAT_KEYWORDS = {
    "Ransomware": [
        "ransomware",
    ],
    "Malware": [
        "malware",
    ],
    "Phishing": [
        "phishing",
    ],
    "Data Breach": [
        "data breach",
        "kebocoran data",
        "kebocoran informasi",
    ],
    "Cyber Attack": [
        "serangan siber",
        "serangan cyber",
        "cyber attack",
    ],
    "Hacking": [
        "diretas",
        "peretas",
        "hacker",
        "penjahat siber",
        "kejahatan siber",
        "akun diretas",
        "penyadapan",
        "disadap",
    ],
    "Bot Attack": [
        "serangan bot",
        "bot ai",
    ],
}


TECHNOLOGY_KEYWORDS = {
    "Artificial Intelligence": [
        "ai",
        "artificial intelligence",
        "kecerdasan buatan",
        "generative ai",
        "genai",
    ],
    "Encryption": [
        "enkripsi",
        "encryption",
    ],
    "Cloud Security": [
        "cloud security",
        "cloud computing",
        "komputasi awan",
        "cloud",
    ],
    "Endpoint Security": [
        "endpoint",
        "edr",
        "xdr",
    ],
    "SIEM": [
        "siem",
    ],
    "Identity & Access Management": [
        "iam",
        "identity access management",
        "identity and access management",
        "access management",
    ],
    "Zero Trust": [
        "zero trust",
    ],
    "Data Security": [
        "keamanan data",
        "perlindungan data",
        "pelindungan data",
        "privasi data",
        "data protection",
        "data security",
    ],
}


INDUSTRY_KEYWORDS = {
    "Banking & Finance": [
        "bank",
        "perbankan",
        "finansial",
        "keuangan",
        "perusahaan pembiayaan",
    ],
    "Government": [
        "pemerintah",
        "kementerian",
        "instansi pemerintah",
        "bumn",
        "lembaga pemerintah",
    ],
    "Telecommunication": [
        "telekomunikasi",
        "operator telekomunikasi",
        "telko",
    ],
    "E-Commerce": [
        "e-commerce",
        "ecommerce",
        "marketplace",
    ],
    "Technology": [
        "perusahaan teknologi",
        "software",
        "perusahaan it",
        "information technology",
    ],
    "Education": [
        "pendidikan",
        "universitas",
        "kampus",
        "sekolah",
    ],
    "Healthcare": [
        "kesehatan",
        "rumah sakit",
        "healthcare",
    ],
}


BUSINESS_ACTION_KEYWORDS = {
    "Security Upgrade": [
        "memperkuat",
        "penguatan keamanan",
        "penguatan siber",
        "meningkatkan keamanan",
        "meningkatkan perlindungan",
        "security upgrade",
        "upgrade keamanan",
    ],
    "Deployment": [
        "menerapkan",
        "implementasi",
        "implementasi sistem",
        "deploy",
        "deployment",
        "diterapkan",
    ],
    "Investment": [
        "investasi",
        "invest",
        "pendanaan",
        "anggaran",
        "belanja",
    ],
    "Incident Response": [
        "incident response",
        "respons insiden",
        "respons terhadap serangan",
        "menangani serangan",
        "penanganan serangan",
        "mitigasi serangan",
    ],
    "Partnership": [
        "kerja sama",
        "kerjasama",
        "kolaborasi",
        "kemitraan",
        "partnership",
    ],
    "Awareness": [
        "edukasi",
        "kesadaran keamanan",
        "awareness",
        "pelatihan keamanan",
        "training keamanan",
    ],
    "Capability Development": [
        "penguatan sdm",
        "pengembangan sdm",
        "peningkatan kapasitas",
        "capacity building",
    ],
}


IMPACT_KEYWORDS = {
    "Operational Risk": [
        "gangguan operasional",
        "operasional terganggu",
        "gangguan layanan",
        "disrupsi operasional",
        "downtime",
        "operational risk",
    ],
    "Financial Risk": [
        "kerugian finansial",
        "kerugian ekonomi",
        "kerugian bisnis",
        "financial loss",
        "financial risk",
    ],
    "Data Risk": [
        "kebocoran data",
        "data bocor",
        "data breach",
        "pencurian data",
        "kehilangan data",
        "data risk",
    ],
    "Reputational Risk": [
        "kerusakan reputasi",
        "risiko reputasi",
        "reputational risk",
        "kepercayaan pelanggan menurun",
    ],
    "Compliance Risk": [
        "risiko kepatuhan",
        "kepatuhan regulasi",
        "compliance risk",
        "pelanggaran regulasi",
        "pelanggaran aturan",
    ],
    "Security Risk": [
        "risiko keamanan",
        "security risk",
        "risiko siber",
        "ancaman keamanan",
    ],
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def normalize_text(value):
    """Normalisasi teks agar aman untuk proses keyword matching."""
    if pd.isna(value):
        return ""

    text = str(value).lower()
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_categories(text, keyword_dictionary):
    """
    Deteksi kategori berdasarkan keyword dengan word boundary.

    Contoh penting:
    keyword 'ai' hanya cocok dengan kata 'ai',
    bukan bagian dari kata lain seperti 'melainkan'.
    """
    detected = []

    for category, keywords in keyword_dictionary.items():
        for keyword in keywords:
            keyword = normalize_text(keyword)
            if not keyword:
                continue

            pattern = re.escape(keyword)

            if re.search(rf"(?<!\w){pattern}(?!\w)", text):
                detected.append(category)
                break

    return detected


def determine_business_topic(threats, technologies):
    """
    Menentukan business_topic berdasarkan hasil klasifikasi yang sudah dibuat.

    Prioritas:
    1. Data Protection
    2. AI & Cyber Security
    3. Cloud Security
    4. Cyber Threat
    5. Cyber Security

    Dengan cara ini kita tidak lagi mencari substring mentah seperti
    'ai' in combined_text yang dapat menghasilkan false positive.
    """
    threat_set = set(threats)
    technology_set = set(technologies)

    # Data Protection
    if (
        "Data Breach" in threat_set
        or "Encryption" in technology_set
        or "Data Security" in technology_set
    ):
        return "Data Protection"

    # AI & Cyber Security
    if "Artificial Intelligence" in technology_set:
        return "AI & Cyber Security"

    # Cloud Security
    if "Cloud Security" in technology_set:
        return "Cloud Security"

    # Cyber Threat
    if any(
        threat in threat_set
        for threat in [
            "Ransomware",
            "Malware",
            "Phishing",
            "Cyber Attack",
            "Hacking",
            "Bot Attack",
            "Other Cyber Threat",
        ]
    ):
        return "Cyber Threat"

    return "Cyber Security"


def build_insight_summary(threats, technologies, industries, actions, impacts, business_topic):
    """Membuat ringkasan insight berbasis hasil klasifikasi."""
    threat_text = ", ".join(threats)
    technology_text = ", ".join(technologies)
    industry_text = ", ".join(industries)
    action_text = ", ".join(actions)
    impact_text = ", ".join(impacts)

    return (
        f"Artikel membahas {threat_text} dengan indikasi teknologi "
        f"{technology_text}. Konteks industri: {industry_text}. "
        f"Tindakan bisnis yang teridentifikasi: {action_text}. "
        f"Dampak yang teridentifikasi: {impact_text}. "
        f"Topik bisnis yang teridentifikasi adalah {business_topic}."
    )


# ============================================================
# MAIN
# ============================================================


def main():
    print("=" * 70)
    print("05 INSIGHT - CYBER SECURITY")
    print("=" * 70)

    # --------------------------------------------------------
    # VALIDASI FILE
    # --------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File input tidak ditemukan: {INPUT_FILE}"
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

    print(f"\n[INFO] Data masuk: {len(df)} artikel")

    if df.empty:
        print("[WARNING] File input kosong. Tidak ada data untuk diproses.")
        return

    # Pastikan kolom minimum tersedia.
    required_columns = ["title", "url"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {', '.join(missing_columns)}"
        )

    insight_rows = []

    # --------------------------------------------------------
    # PROCESS EACH ARTICLE
    # --------------------------------------------------------

    for _, row in df.iterrows():
        title = normalize_text(row.get("title", ""))
        content = normalize_text(row.get("content", ""))

        # Gabungkan judul + isi untuk klasifikasi.
        combined_text = f"{title} {content}".strip()

        # ----------------------------------------------------
        # EXTRACT CATEGORIES
        # ----------------------------------------------------

        threats = detect_categories(
            combined_text,
            THREAT_KEYWORDS,
        )

        technologies = detect_categories(
            combined_text,
            TECHNOLOGY_KEYWORDS,
        )

        industries = detect_categories(
            combined_text,
            INDUSTRY_KEYWORDS,
        )

        business_actions = detect_categories(
            combined_text,
            BUSINESS_ACTION_KEYWORDS,
        )

        impacts = detect_categories(
            combined_text,
            IMPACT_KEYWORDS,
        )

        # ----------------------------------------------------
        # DEFAULT VALUES
        # ----------------------------------------------------

        if not threats:
            threats = ["Other Cyber Threat"]

        if not technologies:
            technologies = ["Not Detected"]

        if not industries:
            industries = ["General"]

        if not business_actions:
            business_actions = ["Not Detected"]

        if not impacts:
            impacts = ["Not Detected"]

        # ----------------------------------------------------
        # BUSINESS TOPIC
        # ----------------------------------------------------

        business_topic = determine_business_topic(
            threats,
            technologies,
        )

        # ----------------------------------------------------
        # INSIGHT SUMMARY
        # ----------------------------------------------------

        summary = build_insight_summary(
            threats=threats,
            technologies=technologies,
            industries=industries,
            actions=business_actions,
            impacts=impacts,
            business_topic=business_topic,
        )

        # ----------------------------------------------------
        # SAVE RESULT
        # ----------------------------------------------------

        insight_rows.append(
            {
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "published_at": row.get("published_at", ""),
                "channel": row.get("channel", ""),
                "source": row.get("source", "Bisnis.com"),
                "scraped_at": row.get("scraped_at", ""),
                "content_status": row.get("content_status", ""),
                "threat_type": ", ".join(threats),
                "technology": ", ".join(technologies),
                "industry": ", ".join(industries),
                "business_action": ", ".join(business_actions),
                "impact": ", ".join(impacts),
                "business_topic": business_topic,
                "insight_summary": summary,
            }
        )

    # --------------------------------------------------------
    # CREATE OUTPUT DATAFRAME
    # --------------------------------------------------------

    insight_df = pd.DataFrame(insight_rows)

    # Hapus duplicate URL jika ternyata ada dari input.
    insight_df = insight_df.drop_duplicates(
        subset=["url"],
        keep="first",
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # SAVE OUTPUT
    # --------------------------------------------------------

    insight_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # SUMMARY OUTPUT
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("INSIGHT EXTRACTION SELESAI")
    print("=" * 70)
    print(f"Artikel diproses : {len(insight_df)}")
    print(f"Output           : {OUTPUT_FILE}")

    print("\nBusiness Topic:")
    print(
        insight_df["business_topic"]
        .value_counts()
        .to_string()
    )

    print("\nThreat Type:")
    print(
        insight_df["threat_type"]
        .str.split(", ")
        .explode()
        .value_counts()
        .to_string()
    )

    print("\nTechnology:")
    print(
        insight_df["technology"]
        .str.split(", ")
        .explode()
        .value_counts()
        .to_string()
    )

    print("\nIndustry:")
    print(
        insight_df["industry"]
        .str.split(", ")
        .explode()
        .value_counts()
        .to_string()
    )

    print("\nBusiness Action:")
    print(
        insight_df["business_action"]
        .str.split(", ")
        .explode()
        .value_counts()
        .to_string()
    )

    print("\nImpact:")
    print(
        insight_df["impact"]
        .str.split(", ")
        .explode()
        .value_counts()
        .to_string()
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()