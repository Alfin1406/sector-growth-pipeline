import pandas as pd
import re


# ==========================================================
# 1. FILE INPUT
# ==========================================================

input_file = "data_center_kompas_curated.csv"

output_file = "data_center_kompas_business_insight.csv"


# ==========================================================
# 2. BACA DATA
# ==========================================================

df = pd.read_csv(
    input_file,
    encoding="utf-8-sig"
)

print("====================================")
print("BUSINESS INSIGHT KOMPAS")
print("====================================")

print("Total artikel:", len(df))


# ==========================================================
# 3. GABUNGKAN TEXT
# ==========================================================

df["analysis_text"] = (
    df["title"].fillna("") + " " +
    df["summary"].fillna("") + " " +
    df["content"].fillna("")
).str.replace(
    r"\s+",
    " ",
    regex=True
)


# ==========================================================
# 4. EXTRACT TECHNOLOGY
# ==========================================================

def extract_technology(text):

    technologies = []

    keyword_mapping = {

        "AI": [
            "artificial intelligence",
            "kecerdasan buatan",
            " AI ",
            "AI,"
            "AI."
        ],

        "Cloud": [
            "cloud",
            "cloud computing"
        ],

        "GPU": [
            "GPU",
            "grafis"
        ],

        "Server": [
            "server",
            "server AI"
        ],

        "Storage": [
            "storage",
            "penyimpanan data",
            "petabyte"
        ],

        "Data Center": [
            "data center",
            "data centre",
            "pusat data"
        ]
    }

    text_lower = text.lower()

    for technology, keywords in keyword_mapping.items():

        for keyword in keywords:

            if keyword.lower() in text_lower:

                technologies.append(
                    technology
                )

                break

    return ", ".join(
        dict.fromkeys(technologies)
    )


# ==========================================================
# 5. EXTRACT INVESTMENT VALUE
# ==========================================================

def extract_investment(text):

    patterns = [

        r"Rp\s?[\d.,]+\s?(?:triliun|miliar|juta)",

        r"Rp[\d.,]+",

        r"\$\s?[\d.,]+\s?(?:miliar|juta|billion|million)",

        r"USD\s?[\d.,]+\s?(?:miliar|juta|billion|million)"
    ]

    results = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        results.extend(matches)

    return ", ".join(
        dict.fromkeys(results)
    )


# ==========================================================
# 6. EXTRACT CAPACITY
# ==========================================================

def extract_capacity(text):

    patterns = [

        r"[\d.,]+\s?MW",

        r"[\d.,]+\s?GW",

        r"[\d.,]+\s?GWh",

        r"[\d.,]+\s?MW\s?data center"
    ]

    results = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        results.extend(matches)

    return ", ".join(
        dict.fromkeys(results)
    )


# ==========================================================
# 7. EXTRACT COMPANY
# ==========================================================

def extract_company(text):

    companies = [

        "Telkom",
        "TelkomGroup",
        "Google",
        "Microsoft",
        "Amazon",
        "AWS",
        "Nvidia",
        "Intel",
        "AMD",
        "Meta",
        "OpenAI",
        "Cisco",
        "Huawei",
        "PLN",
        "TrendAI",
        "Digital Edge",
        "TikTok",
        "SpaceX",
        "Alibaba",
        "SoftBank"
    ]

    found = []

    text_lower = text.lower()

    for company in companies:

        if company.lower() in text_lower:

            found.append(company)

    return ", ".join(
        dict.fromkeys(found)
    )


# ==========================================================
# 8. EXTRACT ORGANIZATION
# ==========================================================

def extract_organization(text):

    organizations = [

        "Pemerintah",
        "Kementerian",
        "PLN",
        "SKK Migas",
        "BP Batam",
        "Komdigi",
        "Deloitte",
        "Forbes"
    ]

    found = []

    text_lower = text.lower()

    for organization in organizations:

        if organization.lower() in text_lower:

            found.append(organization)

    return ", ".join(
        dict.fromkeys(found)
    )


# ==========================================================
# 9. EXTRACT PROJECT LOCATION
# ==========================================================

def extract_location(text):

    locations = [

        "Jakarta",
        "Batam",
        "Bekasi",
        "Cikarang",
        "Jatiluhur",
        "Surabaya",
        "Papua",
        "Jayapura",
        "Jawa Barat",
        "Jawa Tengah",
        "Jawa Timur",
        "Indonesia",
        "Finlandia",
        "Bahrain",
        "Malaysia",
        "Singapura",
        "India",
        "Dubai",
        "Kenya"
    ]

    found = []

    text_lower = text.lower()

    for location in locations:

        if location.lower() in text_lower:

            found.append(location)

    return ", ".join(
        dict.fromkeys(found)
    )


# ==========================================================
# 10. APPLY EXTRACTION
# ==========================================================

df["technology"] = df[
    "analysis_text"
].apply(
    extract_technology
)

df["investment_value"] = df[
    "analysis_text"
].apply(
    extract_investment
)

df["capacity"] = df[
    "analysis_text"
].apply(
    extract_capacity
)

df["company"] = df[
    "analysis_text"
].apply(
    extract_company
)

df["organization"] = df[
    "analysis_text"
].apply(
    extract_organization
)

df["project_location"] = df[
    "analysis_text"
].apply(
    extract_location
)


# ==========================================================
# 11. INVESTMENT TYPE
# ==========================================================

def determine_investment_type(row):

    text = row["analysis_text"]

    if row["investment_value"]:

        if any(
            word in text.lower()
            for word in [
                "investasi",
                "investor",
                "pendanaan",
                "modal"
            ]
        ):
            return "Investment"

        elif any(
            word in text.lower()
            for word in [
                "akuisisi",
                "beli",
                "membeli"
            ]
        ):
            return "Acquisition"

    return ""


df["investment_type"] = df.apply(
    determine_investment_type,
    axis=1
)


# ==========================================================
# 12. CAPACITY TYPE
# ==========================================================

def determine_capacity_type(text):

    text_lower = text.lower()

    if "mw" in text_lower or "gw" in text_lower:

        return "Power Capacity"

    elif "gwh" in text_lower:

        return "Energy Consumption"

    elif "petabyte" in text_lower:

        return "Storage Capacity"

    return ""


df["capacity_type"] = df[
    "analysis_text"
].apply(
    determine_capacity_type
)


# ==========================================================
# 13. DETERMINE TOPIC
# ==========================================================

def determine_topic(row):

    text = row["analysis_text"].lower()

    # ------------------------------------------
    # INVESTMENT
    # ------------------------------------------

    if (
        row["investment_type"] == "Investment"
        or row["investment_value"]
        or "investasi" in text
        or "investor" in text
        or "pendanaan" in text
        or "modal" in text
        or "akuisisi" in text
    ):
        return "Investment"

    # ------------------------------------------
    # ENERGY
    # ------------------------------------------

    if (
        "energi" in text
        or "listrik" in text
        or "power" in text
        or "air" in text
        or "kwh" in text
        or "gwh" in text
    ):
        return "Energy"

    # ------------------------------------------
    # TECHNOLOGY
    # ------------------------------------------

    if row["technology"]:
        return "Technology"

    # ------------------------------------------
    # GOVERNMENT & REGULATION
    # ------------------------------------------

    if (
        "pemerintah" in text
        or "kementerian" in text
        or "regulasi" in text
        or "aturan" in text
        or "izin" in text
        or "amdal" in text
    ):
        return "Government & Regulation"

    # ------------------------------------------
    # INFRASTRUCTURE
    # ------------------------------------------

    if (
        row["capacity"]
        or row["capacity_type"]
        or "data center" in text
        or "data centre" in text
        or "pusat data" in text
        or "server" in text
        or "gedung" in text
        or "fasilitas" in text
    ):
        return "Infrastructure"

    return ""


df["topic"] = df.apply(
    determine_topic,
    axis=1
)


# ==========================================================
# 15. INSIGHT TYPE
# ==========================================================

df["insight_type"] = df["topic"]

# ==========================================================
# 15. HAPUS KOLOM SEMENTARA
# ==========================================================

df = df.drop(
    columns=["analysis_text"]
)


# ==========================================================
# 16. SIMPAN
# ==========================================================

df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================================
# 17. HASIL
# ==========================================================

print("\n====================================")
print("BUSINESS INSIGHT SELESAI")
print("====================================")

print(
    "Technology terisi:",
    (df["technology"] != "").sum()
)

print(
    "Investment terisi:",
    (df["investment_value"] != "").sum()
)

print(
    "Capacity terisi:",
    (df["capacity"] != "").sum()
)

print(
    "Company terisi:",
    (df["company"] != "").sum()
)

print(
    "Organization terisi:",
    (df["organization"] != "").sum()
)

print(
    "Location terisi:",
    (df["project_location"] != "").sum()
)

print("\nTopic distribution:")

print(
    df["topic"].value_counts()
)

print("\nFile output:")

print(output_file)