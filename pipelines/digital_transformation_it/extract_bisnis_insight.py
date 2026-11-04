import hashlib
import os
import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "data/processed/bisnis_filtered.csv"
OUTPUT_FILE = "data/processed/bisnis_insight.csv"


# ============================================================
# HELPER
# ============================================================

def normalize_text(value):
    if pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def generate_article_id(url):
    if not url:
        return None

    return hashlib.sha256(
        str(url).strip().encode("utf-8")
    ).hexdigest()


def find_matches(text, keyword_dict):
    detected = []

    for category, keywords in keyword_dict.items():

        for keyword in keywords:

            pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"

            if re.search(
                pattern,
                text,
                re.IGNORECASE
            ):
                detected.append(category)
                break

    return detected


# ============================================================
# EVENT TYPE
# ============================================================

def detect_event_type(title, content, topic):

    title_text = normalize_text(title).lower()
    text = f"{title} {content}".lower()

    # Prioritas judul
    if any(k in title_text for k in [
        "akuisisi",
        "mengakuisisi",
        "acquisition"
    ]):
        return "Acquisition"

    if any(k in title_text for k in [
        "rekomendasi",
        "alternatif",
        "pilihan",
        "cara",
        "tips"
    ]):
        return "Product / Solution Evaluation"

    if any(k in title_text for k in [
        "beralih",
        "adopsi",
        "adopsi",
        "menggunakan",
        "implementasi",
        "diterapkan"
    ]):
        return "Adoption / Implementation"

    if topic == "Cyber Security":

        if any(k in text for k in [
            "serangan",
            "diretas",
            "peretas",
            "ransomware",
            "malware",
            "phishing",
            "disadap",
            "bot attack"
        ]):
            return "Cyber Incident / Threat"

        if any(k in text for k in [
            "kerja sama",
            "kolaborasi",
            "partnership"
        ]):
            return "Security Partnership"

        return "Cyber Security Activity"

    if topic == "Digital Transformation":

        if any(k in text for k in [
            "otomatisasi",
            "automasi",
            "digitalisasi"
        ]):
            return "Business Process Automation"

        if any(k in text for k in [
            "transformasi digital",
            "digital transformation"
        ]):
            return "Digital Transformation"

        return "Digital Transformation Activity"

    if topic == "Cloud Enterprise":

        if any(k in text for k in [
            "migrasi cloud",
            "cloud migration",
            "adopsi cloud",
            "cloud adoption"
        ]):
            return "Cloud Adoption / Migration"

        return "Cloud Enterprise Activity"

    if topic == "Enterprise Data & AI":

        if any(k in text for k in [
            "menggunakan ai",
            "adopsi ai",
            "implementasi ai",
            "kecerdasan buatan",
            "artificial intelligence"
        ]):
            return "Enterprise AI Adoption"

        return "Enterprise Data & AI Activity"

    return "Enterprise Software Activity"


# ============================================================
# TECHNOLOGY
# ============================================================

TECHNOLOGY_KEYWORDS = {
    "Artificial Intelligence": [
        "artificial intelligence",
        "kecerdasan buatan",
        "generative ai",
        "genai",
        "ai",
    ],

    "Cloud": [
        "cloud",
        "cloud computing",
        "komputasi awan",
        "cloud-based",
        "hybrid cloud",
        "multicloud",
        "multi-cloud",
    ],

    "ERP": [
        "erp",
        "enterprise resource planning",
        "sap",
        "oracle erp",
        "microsoft dynamics",
        "netsuite",
    ],

    "CRM": [
        "crm",
        "customer relationship management",
        "salesforce",
        "zoho crm",
        "qontak",
    ],

    "HRIS / HCM": [
        "hris",
        "hcm",
        "human resource information system",
        "human capital management",
        "successfactors",
        "workday",
        "sunfish",
    ],

    "SaaS": [
        "saas",
        "software as a service",
        "saas ecosystem",
    ],

    "RPA": [
        "robotic process automation",
        "rpa",
    ],

    "Encryption": [
        "enkripsi",
        "encryption",
    ],

    "IAM": [
        "identity access management",
        "identity and access management",
        "access management",
        "iam",
    ],

    "Zero Trust": [
        "zero trust",
    ],

    "Endpoint Security": [
        "endpoint security",
        "endpoint",
        "edr",
        "xdr",
    ],
}


# ============================================================
# INDUSTRY
# ============================================================

INDUSTRY_KEYWORDS = {
    "Banking & Finance": [
        "bank",
        "perbankan",
        "finansial",
        "keuangan",
        "pembiayaan",
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

    "Technology / Software": [
        "perusahaan teknologi",
        "software",
        "startup software",
        "perusahaan it",
        "saas",
    ],

    "Healthcare": [
        "kesehatan",
        "rumah sakit",
        "healthcare",
    ],

    "Travel / Aviation": [
        "airasia",
        "maskapai",
        "penerbangan",
        "airline",
        "travel",
    ],

    "Manufacturing": [
        "manufaktur",
        "pabrik",
        "manufacturing",
    ],
}


# ============================================================
# BUSINESS ACTION
# ============================================================

BUSINESS_ACTION_KEYWORDS = {
    "Software Adoption": [
        "mengadopsi",
        "adopsi",
        "menggunakan",
        "implementasi",
        "diterapkan",
        "digunakan",
    ],

    "Process Automation": [
        "otomatisasi",
        "automasi",
        "mengotomatisasi",
        "rpa",
        "robotic process automation",
    ],

    "Corporate Acquisition": [
        "akuisisi",
        "mengakuisisi",
        "acquisition",
    ],

    "Software Evaluation": [
        "rekomendasi",
        "alternatif",
        "pilihan",
        "memilih",
    ],

    "Investment / Expansion": [
        "investasi",
        "invest",
        "ekspansi",
        "pendanaan",
    ],

    "Partnership": [
        "kerja sama",
        "kerjasama",
        "kolaborasi",
        "kemitraan",
        "partnership",
    ],

    "Security Response": [
        "menangani serangan",
        "respons terhadap serangan",
        "mitigasi",
        "penanganan serangan",
    ],

    "Capability Development": [
        "penguatan sdm",
        "pengembangan sdm",
        "peningkatan kapasitas",
        "capacity building",
    ],
}


# ============================================================
# IMPACT
# ============================================================

IMPACT_KEYWORDS = {
    "Operational Efficiency": [
        "efisiensi",
        "meningkatkan produktivitas",
        "menyederhanakan operasi",
        "operasional lebih efisien",
    ],

    "Cost Reduction": [
        "mengurangi biaya",
        "mengurangi biaya operasional",
        "hemat biaya",
    ],

    "Process Automation": [
        "otomatisasi",
        "automasi",
        "mengotomatisasi",
    ],

    "Data Integration": [
        "integrasi data",
        "terintegrasi",
        "data tersentralisasi",
        "single source of truth",
    ],

    "Decision Support": [
        "pengambilan keputusan",
        "keputusan berbasis data",
        "analitik",
    ],

    "Customer Experience": [
        "customer experience",
        "layanan pelanggan",
        "pengalaman pelanggan",
        "kepercayaan pelanggan",
    ],

    "Security Risk": [
        "risiko keamanan",
        "risiko siber",
        "ancaman keamanan",
        "security risk",
    ],

    "Operational Risk": [
        "gangguan operasional",
        "gangguan layanan",
        "disrupsi operasional",
        "downtime",
    ],

    "Data Risk": [
        "kebocoran data",
        "data breach",
        "pencurian data",
        "kehilangan data",
    ],

    "Reputational Risk": [
        "risiko reputasi",
        "kerusakan reputasi",
        "kepercayaan pelanggan menurun",
    ],
}


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("05 INSIGHT - BISNIS.COM")
    print("GENERIC SECTOR 3 INSIGHT EXTRACTION")
    print("=" * 70)

    if not os.path.exists(INPUT_FILE):

        raise FileNotFoundError(
            f"File input tidak ditemukan: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )

    print()
    print(
        f"Input dataset : {len(df)} rows"
    )

    if df.empty:

        print(
            "Dataset kosong."
        )

        return

    required_columns = [
        "title",
        "url",
        "topic",
        "subtopic"
    ]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "Kolom wajib tidak ditemukan: "
            + ", ".join(missing)
        )

    results = []

    for _, row in df.iterrows():

        title = normalize_text(
            row.get("title", "")
        )

        content = normalize_text(
            row.get("content", "")
        )

        topic = normalize_text(
            row.get("topic", "")
        )

        subtopic = normalize_text(
            row.get("subtopic", "")
        )

        combined_text = (
            f"{title} {content}"
        )

        # ----------------------------------------
        # TECHNOLOGY
        # ----------------------------------------

        technologies = find_matches(
            combined_text,
            TECHNOLOGY_KEYWORDS
        )

        if not technologies:

            technologies = [
                "Not Detected"
            ]

        # ----------------------------------------
        # INDUSTRY
        # ----------------------------------------

        industries = find_matches(
            combined_text,
            INDUSTRY_KEYWORDS
        )

        if not industries:

            industries = [
                "General"
            ]

        # ----------------------------------------
        # BUSINESS ACTION
        # ----------------------------------------

        business_actions = find_matches(
            combined_text,
            BUSINESS_ACTION_KEYWORDS
        )

        if not business_actions:

            business_actions = [
                "Not Detected"
            ]

        # ----------------------------------------
        # IMPACT
        # ----------------------------------------

        impacts = find_matches(
            combined_text,
            IMPACT_KEYWORDS
        )

        if not impacts:

            impacts = [
                "Not Detected"
            ]

        # ----------------------------------------
        # EVENT TYPE
        # ----------------------------------------

        event_type = detect_event_type(
            title,
            content,
            topic
        )

        # ----------------------------------------
        # SUMMARY
        # ----------------------------------------

        technology_text = ", ".join(
            technologies
        )

        industry_text = ", ".join(
            industries
        )

        action_text = ", ".join(
            business_actions
        )

        impact_text = ", ".join(
            impacts
        )

        insight_summary = (
            f"Artikel membahas {subtopic} "
            f"dalam topik {topic}. "
            f"Event utama: {event_type}. "
            f"Teknologi teridentifikasi: "
            f"{technology_text}. "
            f"Konteks industri: "
            f"{industry_text}. "
            f"Tindakan bisnis: "
            f"{action_text}. "
            f"Dampak yang teridentifikasi: "
            f"{impact_text}."
        )

        # ----------------------------------------
        # OUTPUT ROW
        # ----------------------------------------

        results.append({

            "article_id":
                generate_article_id(
                    row.get("url", "")
                ),

            "title":
                row.get("title", ""),

            "url":
                row.get("url", ""),

            "published_at":
                row.get("published_at", ""),

            "channel":
                row.get("channel", "Teknologi"),

            "source":
                row.get("source", "Bisnis.com"),

            "topic":
                topic,

            "subtopic":
                subtopic,

            "event_type":
                event_type,

            "technology":
                technology_text,

            "industry":
                industry_text,

            "business_action":
                action_text,

            "impact":
                impact_text,

            "insight_summary":
                insight_summary,

            "content_status":
                row.get(
                    "content_status",
                    ""
                ),

            "scraped_at":
                row.get(
                    "scraped_at",
                    ""
                ),
        })

    # ========================================================
    # SAVE
    # ========================================================

    result_df = pd.DataFrame(
        results
    )

    result_df = (
        result_df
        .drop_duplicates(
            subset=["url"]
        )
        .reset_index(drop=True)
    )

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("INSIGHT EXTRACTION SELESAI")
    print("=" * 70)

    print(
        f"Total articles : {len(result_df)}"
    )

    print(
        f"Output         : {OUTPUT_FILE}"
    )

    print()
    print("TOPIC:")

    print(
        result_df["topic"]
        .value_counts()
        .to_string()
    )

    print()
    print("SUBTOPIC:")

    print(
        result_df["subtopic"]
        .value_counts()
        .to_string()
    )

    print()
    print("EVENT TYPE:")

    print(
        result_df["event_type"]
        .value_counts()
        .to_string()
    )

    print()
    print("INDUSTRY:")

    print(
        result_df["industry"]
        .value_counts()
        .to_string()
    )

    print()
    print("PREVIEW:")

    print(
        result_df[
            [
                "title",
                "topic",
                "subtopic",
                "event_type",
                "technology",
                "industry",
                "business_action",
                "impact",
            ]
        ].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()