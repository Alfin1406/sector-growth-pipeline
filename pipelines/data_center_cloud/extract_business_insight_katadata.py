import pandas as pd
import re


INPUT_FILE = "data_center_katadata_current.csv"
OUTPUT_FILE = "data_center_katadata_business_insight.csv"


# ==========================================
# LOAD DATA
# ==========================================

df = pd.read_csv(
    INPUT_FILE,
    encoding="utf-8-sig"
)

print("Total artikel:", len(df))


# ==========================================
# HELPER
# ==========================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def find_keywords(text, keywords):
    found = []

    text_lower = text.lower()

    for keyword in keywords:
        if keyword.lower() in text_lower:
            if keyword not in found:
                found.append(keyword)

    return found


# ==========================================
# TECHNOLOGY
# ==========================================

def extract_technology(text):

    technologies = []

    technology_keywords = {
        "AI": [
            "artificial intelligence",
            "kecerdasan buatan",
            "ai"
        ],
        "Cloud": [
            "cloud",
            "cloud computing"
        ],
        "Data Center": [
            "data center",
            "data centre",
            "pusat data"
        ],
        "Green Data Center": [
            "green data center",
            "energi terbarukan",
            "renewable energy",
            "panas bumi"
        ],
        "Fiber Optic": [
            "fiber optik",
            "fiber"
        ]
    }

    text_lower = text.lower()

    for technology, keywords in technology_keywords.items():

        if any(
            keyword in text_lower
            for keyword in keywords
        ):
            technologies.append(
                technology
            )

    return "; ".join(technologies)


# ==========================================
# CAPACITY
# ==========================================

def extract_capacity(text):

    # Fokus pada angka yang langsung berkaitan
    # dengan kapasitas data center

    patterns = [
        r"(?:kapasitas|capacity|berkapasitas|mencapai|sebesar|hingga|total)\s*(?:sekitar\s*)?(\d+(?:[.,]\d+)?)\s*(MW|GW)",
        r"(\d+(?:[.,]\d+)?)\s*(MW|GW)\s*(?:data center|pusat data)"
    ]

    capacities = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for number, unit in matches:

            value = f"{number} {unit}"

            if value not in capacities:
                capacities.append(value)

    return "; ".join(capacities)


# ==========================================
# INVESTMENT
# ==========================================

def extract_investment(text):

    # Cari nilai yang berada dekat dengan
    # konteks investasi / proyek / dana

    investment_sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    patterns = [
        r"Rp\s?[\d.,]+\s?(?:triliun|miliar|juta)",
        r"US\$?\s?[\d.,]+\s?(?:triliun|miliar|juta|billion|million|trillion)",
        r"\$\s?[\d.,]+\s?(?:billion|million|trillion)"
    ]

    investments = []

    investment_keywords = [
        "investasi",
        "investasikan",
        "menanamkan",
        "dana",
        "modal",
        "proyek",
        "investor",
        "pendanaan"
    ]

    for sentence in investment_sentences:

        sentence_lower = sentence.lower()

        if not any(
            keyword in sentence_lower
            for keyword in investment_keywords
        ):
            continue

        for pattern in patterns:

            matches = re.findall(
                pattern,
                sentence,
                flags=re.IGNORECASE
            )

            for match in matches:

                match = match.strip()

                if match not in investments:
                    investments.append(match)

    return "; ".join(investments)


# ==========================================
# COMPANY
# ==========================================

def extract_company(text):

    company_keywords = [
        "PLN",
        "PLN Icon Plus",
        "Telkom Indonesia",
        "Telkom",
        "Indosat",
        "DCI Indonesia",
        "NeutraDC",
        "Danantara",
        "Google",
        "Microsoft",
        "Amazon",
        "AWS",
        "TikTok",
        "Meta",
        "Alibaba",
        "PGEO",
        "Pertamina",
        "JLL",
        "DMAS"
    ]

    found = find_keywords(
        text,
        company_keywords
    )

    return "; ".join(found)


# ==========================================
# LOCATION
# ==========================================

def extract_location(text):

    location_keywords = [
        "Jakarta",
        "Banten",
        "Tangerang",
        "BSD",
        "Karawang",
        "Cikarang",
        "Bekasi",
        "Jawa Barat",
        "Jawa Tengah",
        "Jawa Timur",
        "Batam",
        "Kepulauan Riau",
        "Surabaya",
        "Serang"
    ]

    found = find_keywords(
        text,
        location_keywords
    )

    return "; ".join(found)


# ==========================================
# INSIGHT TYPE
# ==========================================

def determine_insight_type(
    investment,
    capacity,
    technology,
    text
):

    insight = []

    text_lower = text.lower()

    if investment:
        insight.append("Investment")

    if capacity:
        insight.append("Capacity")

    # Technology hanya masuk jika memang
    # ada teknologi spesifik selain data center
    if any(
        tech in technology
        for tech in [
            "AI",
            "Cloud",
            "Green Data Center",
            "Fiber Optic"
        ]
    ):
        insight.append("Technology")

    if any(
        keyword in text_lower
        for keyword in [
            "proyek data center",
            "pembangunan data center",
            "bangun data center",
            "membangun data center"
        ]
    ):
        insight.append("Project")

    if any(
        keyword in text_lower
        for keyword in [
            "pasokan listrik",
            "kebutuhan listrik",
            "energi terbarukan",
            "panas bumi"
        ]
    ):
        insight.append("Energy")

    return "; ".join(
        dict.fromkeys(insight)
    )


# ==========================================
# PROCESS
# ==========================================

results = []

for _, row in df.iterrows():

    title = clean_text(
        row["title"]
    )

    summary = clean_text(
        row["summary"]
    )

    content = clean_text(
        row["content"]
    )

    text = (
        title
        + " "
        + summary
        + " "
        + content
    )

    technology = extract_technology(
        text
    )

    capacity = extract_capacity(
        text
    )

    investment = extract_investment(
        text
    )

    company = extract_company(
        text
    )

    location = extract_location(
        text
    )

    insight_type = determine_insight_type(
        investment,
        capacity,
        technology,
        text
    )

    # ======================================
    # INVESTMENT TYPE
    # ======================================

    if investment:
        investment_type = "Project Investment"
    else:
        investment_type = "Tidak ada"


    # ======================================
    # CAPACITY TYPE
    # ======================================

    capacity_type = "Tidak ada"

    if capacity:

        text_lower = text.lower()

        if any(
            keyword in text_lower
            for keyword in [
                "rencana",
                "direncanakan",
                "akan membangun",
                "akan dibangun",
                "target"
            ]
        ):
            capacity_type = "Planned / Additional"

        elif any(
            keyword in text_lower
            for keyword in [
                "saat ini",
                "existing",
                "telah beroperasi",
                "sudah beroperasi"
            ]
        ):
            capacity_type = "Existing"

        else:
            capacity_type = "Capacity"


    # ======================================
    # RESULT
    # ======================================

    results.append({

        "title":
            title,

        "published_date":
            row["published_date"],

        "summary":
            summary,

        "article_url":
            row["article_url"],

        "image_url":
            row["image_url"],

        "source":
            "Katadata",

        "sector":
            "Data Center & Cloud",

        "topic":
            "Data Center",

        "relevance":
            row["relevance"],

        "technology":
            technology,

        "investment_value":
            investment,

        "investment_type":
            investment_type,

        "capacity":
            capacity,

        "capacity_type":
            capacity_type,

        "company":
            company,

        "organization":
            company,

        "project_location":
            location,

        "insight_type":
            insight_type,

        "content":
            content
    })


# ==========================================
# SAVE
# ==========================================

result_df = pd.DataFrame(
    results
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# SUMMARY
# ==========================================

print()
print("=" * 50)
print("BUSINESS INSIGHT KATADATA V2 SELESAI")
print("=" * 50)

print(
    "Total artikel:",
    len(result_df)
)

print(
    "Technology terisi:",
    result_df["technology"].astype(bool).sum()
)

print(
    "Capacity terisi:",
    result_df["capacity"].astype(bool).sum()
)

print(
    "Investment terisi:",
    result_df["investment_value"].astype(bool).sum()
)

print(
    "Company terisi:",
    result_df["company"].astype(bool).sum()
)

print(
    "Project Location terisi:",
    result_df["project_location"].astype(bool).sum()
)

print()
print(
    f"Output: {OUTPUT_FILE}"
)