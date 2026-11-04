import os
import re
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "data/processed/bisnis_cyber_clean.csv"

OUTPUT_ALL = (
    "data/processed/"
    "bisnis_filtered_all_classified.csv"
)

OUTPUT_FILTERED = (
    "data/processed/"
    "bisnis_filtered.csv"
)


# ============================================================
# COMMON SECTOR 3 TAXONOMY
# ============================================================

TOPIC_KEYWORDS = {

    "Cyber Security": {
        "Cyber Threat": [
            "ransomware",
            "malware",
            "phishing",
            "serangan siber",
            "serangan cyber",
            "cyber attack",
            "data breach",
            "kebocoran data",
            "hacker",
            "peretas",
            "diretas",
            "kejahatan siber",
            "keamanan siber",
            "cyber security",
            "keamanan cyber",
            "serangan bot",
            "bot ai",
            "penjahat siber",
            "disadap",
            "penyadapan",
            "spyware",
            "cyber crime",
            "kejahatan cyber", 
        ],
        "Cyber Technology": [
            "cloud security",
            "endpoint security",
            "edr",
            "xdr",
            "siem",
            "zero trust",
            "iam",
            "identity access management",
            "enkripsi",
            "encryption",
        ],
    },

    "Enterprise Software": {
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
            "sap successfactors",
            "oracle hcm",
            "workday",
            "sunfish",
        ],
        "SaaS": [
            "saas",
            "software as a service",
            "saas ecosystem",
            "business software",
            "cloud-based software",
        ],
        "Procurement / SCM": [
            "procurement",
            "supply chain",
            "supply chain management",
            "sap ariba",
            "oracle procurement",
        ],
    },

    "Digital Transformation": {
        "Digitalization": [
            "transformasi digital",
            "digital transformation",
            "digitalisasi",
            "go digital",
        ],
        "Automation": [
            "otomatisasi proses",
            "automasi proses",
            "business process automation",
            "robotic process automation",
            "rpa",
        ],
        "Legacy Modernization": [
            "modernisasi sistem",
            "modernisasi aplikasi",
            "legacy modernization",
            "legacy system",
        ],
        "Digital Platform": [
            "digital platform",
            "platform digital",
            "aplikasi digital",
            "layanan digital",
        ],
    },

    "Cloud Enterprise": {
        "Cloud Adoption": [
            "cloud adoption",
            "adopsi cloud",
            "cloud migration",
            "migrasi cloud",
            "komputasi awan",
            "cloud computing",
        ],
        "Hybrid / Multi Cloud": [
            "hybrid cloud",
            "multicloud",
            "multi-cloud",
        ],
        "Enterprise Cloud": [
            "enterprise cloud",
            "cloud enterprise",
            "aws",
            "microsoft azure",
            "google cloud",
        ],
    },

    "Enterprise Data & AI": {
        "Enterprise AI": [
            "enterprise ai",
            "ai untuk perusahaan",
            "ai untuk bisnis",
            "artificial intelligence",
            "kecerdasan buatan",
            "generative ai",
        ],
        "Data Platform": [
            "data platform",
            "enterprise data",
            "data warehouse",
            "data lake",
            "data analytics",
            "business intelligence",
            "analitik data",
        ],
    },
}


# ============================================================
# HELPER
# ============================================================

def normalize_text(text):

    if pd.isna(text):
        return ""

    text = str(text)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def find_keyword_matches(text, keywords):

    matches = []

    for keyword in keywords:

        pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(
            pattern,
            text,
            re.IGNORECASE
        ):
            matches.append(keyword)

    return matches


# ============================================================
# TOPIC CLASSIFIER
# ============================================================

def classify_topic(row):

    title = normalize_text(
        row.get("title", "")
    )

    content = normalize_text(
        row.get("content", "")
    )

    title_text = title.lower()

    full_text = (
        f"{title} {content}"
    )

    topic_scores = {}
    topic_matches = {}

    for topic, subtopics in TOPIC_KEYWORDS.items():

        total_score = 0
        all_matches = []

        for subtopic, keywords in subtopics.items():

            matches = find_keyword_matches(
                full_text,
                keywords
            )

            for keyword in matches:

                # Keyword di TITLE lebih kuat
                if re.search(
                    rf"\b{re.escape(keyword)}\b",
                    title_text,
                    re.IGNORECASE
                ):
                    total_score += 5
                else:
                    total_score += 1

            all_matches.extend(matches)

        if total_score > 0:

            topic_scores[topic] = total_score

            topic_matches[topic] = list(
                dict.fromkeys(all_matches)
            )

    # Tidak ada topic yang cocok
    if not topic_scores:

        return {
            "is_relevant": False,
            "topic": "Other",
            "subtopic": "Other",
            "matched_keywords": "",
            "classification_score": 0,
        }

    # ========================================================
    # PRIORITY
    # ========================================================

    priority = {
        "Cyber Security": 5,
        "Enterprise Software": 4,
        "Digital Transformation": 3,
        "Cloud Enterprise": 2,
        "Enterprise Data & AI": 1,
    }

    selected_topic = max(
        topic_scores,
        key=lambda topic: (
            topic_scores[topic],
            priority[topic]
        )
    )

    selected_matches = topic_matches[
        selected_topic
    ]

    # ========================================================
    # SUBTOPIC
    # ========================================================

    subtopic_scores = {}

    for subtopic, keywords in (
        TOPIC_KEYWORDS[selected_topic].items()
    ):

        score = 0

        for keyword in keywords:

            pattern = rf"\b{re.escape(keyword)}\b"

            if re.search(
                pattern,
                full_text,
                re.IGNORECASE
            ):

                score += 1

                if re.search(
                    pattern,
                    title_text,
                    re.IGNORECASE
                ):
                    score += 5

        if score > 0:

            subtopic_scores[subtopic] = score

    selected_subtopic = max(
        subtopic_scores,
        key=subtopic_scores.get
    )

    return {
        "is_relevant": True,
        "topic": selected_topic,
        "subtopic": selected_subtopic,
        "matched_keywords": ", ".join(
            selected_matches
        ),
        "classification_score": topic_scores[
            selected_topic
        ],
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("04 FILTERING - BISNIS.COM")
    print("COMMON SECTOR 3 TOPIC CLASSIFIER")
    print("=" * 70)

    if not os.path.exists(INPUT_FILE):

        raise FileNotFoundError(
            f"File tidak ditemukan: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig"
    )

    print()
    print(
        f"Input dataset : {len(df)} rows"
    )

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    if "title" in df.columns:

        df["title"] = df["title"].apply(
            normalize_text
        )

    if "content" in df.columns:

        df["content"] = df["content"].apply(
            normalize_text
        )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    results = df.apply(
        classify_topic,
        axis=1,
        result_type="expand"
    )

    df = pd.concat(
        [
            df,
            results
        ],
        axis=1
    )

    # --------------------------------------------------------
    # SAVE ALL
    # --------------------------------------------------------

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_ALL,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # FILTER RELEVANT
    # --------------------------------------------------------

    filtered = df[
        df["is_relevant"] == True
    ].copy()

    filtered.to_csv(
        OUTPUT_FILTERED,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FILTERING SELESAI")
    print("=" * 70)

    print(
        f"Total input    : {len(df)}"
    )

    print(
        f"Relevan        : {len(filtered)}"
    )

    print(
        f"Tidak relevan  : "
        f"{len(df) - len(filtered)}"
    )

    print()
    print("TOPIC DISTRIBUTION")

    print(
        filtered[
            "topic"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("SUBTOPIC DISTRIBUTION")

    print(
        filtered[
            "subtopic"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("DETAIL CLASSIFICATION")

    print(
        filtered[
            [
                "title",
                "topic",
                "subtopic",
                "matched_keywords",
                "classification_score",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print(
        "Output all       :",
        OUTPUT_ALL
    )

    print(
        "Output filtered  :",
        OUTPUT_FILTERED
    )


if __name__ == "__main__":
    main()