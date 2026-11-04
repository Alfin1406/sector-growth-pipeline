import pandas as pd
import re


INPUT_FILE = "data_center_antaranews_current.csv"
OUTPUT_FILE = "data_center_antaranews_business_insight.csv"


# =========================================================
# HELPER
# =========================================================

def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text)


def unique_join(items):
    result = []

    for item in items:
        item = item.strip()

        if item and item not in result:
            result.append(item)

    return "; ".join(result)


def get_context(text, position, window=220):
    start = max(0, position - window)
    end = min(len(text), position + window)

    return text[start:end]


# =========================================================
# TECHNOLOGY
# =========================================================

def extract_technology(text):

    text_lower = text.lower()

    technologies = []

    technology_keywords = {
        "Geothermal": [
            "geothermal",
            "panas bumi"
        ],

        "Renewable Energy": [
            "renewable energy",
            "energi terbarukan",
            "energi baru terbarukan",
            "ebt",
            "green energy"
        ],

        "Cloud": [
            "cloud computing",
            "cloud"
        ],

        "AI Data Center": [
            "ai data center",
            "pusat data berbasis ai",
            "data center berbasis ai",
            "artificial intelligence",
            "kecerdasan buatan"
        ],

        "Liquid Cooling": [
            "liquid cooling",
            "pendingin cair",
            "direct to chip"
        ],

        "5G": [
            "5g"
        ],

        "Fiber Optic": [
            "fiber optik",
            "serat optik"
        ],

        "Cybersecurity": [
            "cybersecurity",
            "keamanan siber"
        ]
    }

    # Hanya masukkan teknologi jika benar-benar
    # berkaitan dengan konteks digital/data center/AI
    digital_context = [
        "data center",
        "pusat data",
        "digital",
        "komputasi",
        "ai",
        "kecerdasan buatan",
        "cloud",
        "5g"
    ]

    has_digital_context = any(
        keyword in text_lower
        for keyword in digital_context
    )

    if not has_digital_context:
        return ""

    for technology, keywords in technology_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:
                technologies.append(technology)
                break

    return unique_join(technologies)


# =========================================================
# INVESTMENT
# =========================================================

def extract_investment(text):

    text_lower = text.lower()

    # Contoh:
    # US$15-20 miliar
    # US$23,3 miliar
    # Rp2,3 triliun
    # Rp498,79 triliun
    money_pattern = r"""
        (?:
            us\$|usd|\$
        )
        \s*
        [\d.,]+
        (?:
            \s*-\s*[\d.,]+
        )?
        \s*
        (?:
            miliar|juta|triliun|
            billion|million|trillion
        )
        |
        (?:
            rp|idr
        )
        \s*
        [\d.,]+
        (?:
            \s*-\s*[\d.,]+
        )?
        \s*
        (?:
            miliar|juta|triliun
        )
    """

    matches = list(
        re.finditer(
            money_pattern,
            text_lower,
            flags=re.IGNORECASE | re.VERBOSE
        )
    )

    investment_values = []
    investment_types = []
    investment_contexts = []

    # Kata yang harus dekat dengan angka
    investment_keywords = [
        "investasi",
        "investor",
        "investment",
        "pendanaan",
        "funding",
        "financing",
        "nilai proyek",
        "nilai investasi",
        "investment pipeline",
        "pipeline investasi"
    ]

    data_center_keywords = [
        "data center",
        "pusat data",
        "data centre"
    ]

    market_keywords = [
        "pasar",
        "market",
        "ukuran pasar",
        "market size",
        "nilai pasar"
    ]

    for match in matches:

        value = match.group(0).strip()
        position = match.start()

        context = get_context(
            text_lower,
            position,
            window=250
        )

        # Harus ada konteks data center
        has_data_center = any(
            keyword in context
            for keyword in data_center_keywords
        )

        # Harus ada konteks investasi
        has_investment = any(
            keyword in context
            for keyword in investment_keywords
        )

        has_market = any(
            keyword in context
            for keyword in market_keywords
        )

        # Kalau angka tidak berhubungan dengan data center,
        # jangan dimasukkan
        if not has_data_center:
            continue

        if not has_investment and not has_market:
            continue

        # Tentukan jenis nilai
        if has_market:
            investment_type = "Market Value"

        elif (
            "pipeline" in context
            or "on the pipeline" in context
        ):
            investment_type = "Investment Pipeline"

        elif (
            "pendanaan" in context
            or "funding" in context
            or "financing" in context
        ):
            investment_type = "Funding"

        else:
            investment_type = "Project Investment"

        # Ambil konteks
        context_clean = re.sub(
            r"\s+",
            " ",
            text[
                max(0, position - 150):
                min(len(text), position + 200)
            ]
        ).strip()

        investment_values.append(value)
        investment_types.append(investment_type)
        investment_contexts.append(context_clean)

    return (
        unique_join(investment_values),
        unique_join(investment_types),
        unique_join(investment_contexts)
    )


# =========================================================
# CAPACITY
# =========================================================

def extract_capacity(text):

    text_lower = text.lower()

    capacity_pattern = r"""
        \b
        \d+(?:[.,]\d+)?
        (?:
            \s*-\s*
            \d+(?:[.,]\d+)?
        )?
        \s*
        (?:
            mw|
            megawatt|
            megawatts|
            gw|
            gigawatt|
            gigawatts|
            mva|
            kva
        )
        \b
    """

    matches = list(
        re.finditer(
            capacity_pattern,
            text_lower,
            flags=re.IGNORECASE | re.VERBOSE
        )
    )

    capacity_values = []
    capacity_types = []
    capacity_contexts = []

    capacity_keywords = [
        "data center",
        "pusat data",
        "kapasitas data center",
        "kapasitas pusat data",
        "proyek data center",
        "pembangunan data center",
        "listrik untuk data center"
    ]

    for match in matches:

        value = match.group(0).strip()
        position = match.start()

        context = get_context(
            text_lower,
            position,
            window=250
        )

        # Harus ada hubungan dengan data center
        has_data_center = any(
            keyword in context
            for keyword in capacity_keywords
        )

        if not has_data_center:
            continue

        # -----------------------------------------
        # Tentukan tipe kapasitas
        # -----------------------------------------

        if any(
            keyword in context
            for keyword in [
                "tambahan",
                "additional",
                "akan dibangun",
                "rencana",
                "rencananya",
                "pipeline",
                "minat investor",
                "investor berminat"
            ]
        ):
            capacity_type = "Planned / Additional"

        elif any(
            keyword in context
            for keyword in [
                "telah beroperasi",
                "sudah beroperasi",
                "operasional",
                "existing",
                "terpasang"
            ]
        ):
            capacity_type = "Existing"

        elif any(
            keyword in context
            for keyword in [
                "pasok listrik",
                "suplai listrik",
                "menyuplai listrik",
                "supply listrik",
                "daya listrik"
            ]
        ):
            capacity_type = "Power Supply"

        else:
            capacity_type = "Capacity"

        context_clean = re.sub(
            r"\s+",
            " ",
            text[
                max(0, position - 150):
                min(len(text), position + 200)
            ]
        ).strip()

        capacity_values.append(value)
        capacity_types.append(capacity_type)
        capacity_contexts.append(context_clean)

    return (
        unique_join(capacity_values),
        unique_join(capacity_types),
        unique_join(capacity_contexts)
    )


# =========================================================
# COMPANY
# =========================================================

def extract_company(text):

    text_lower = text.lower()

    company_keywords = {
        "PLN": [
            "pt pln",
            "pln (persero)",
            "pln"
        ],

        "Pertamina Geothermal Energy": [
            "pertamina geothermal energy",
            "pge"
        ],

        "Danantara": [
            "danantara"
        ],

        "JLL": [
            "jll",
            "jones lang lasalle"
        ],

        "Telkom": [
            "telkom"
        ],

        "Nvidia": [
            "nvidia"
        ],

        "Schneider Electric": [
            "schneider electric"
        ],

        "DAMAC Digital": [
            "damac digital"
        ],

        "Arm": [
            "arm ltd",
            "arm"
        ]
    }

    companies = []

    for company, keywords in company_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:
                companies.append(company)
                break

    return unique_join(companies)


# =========================================================
# ORGANIZATION
# =========================================================

def extract_organization(text):

    text_lower = text.lower()

    organization_keywords = {
        "Kementerian ESDM": [
            "kementerian energi dan sumber daya mineral",
            "esdm"
        ],

        "Kementerian Investasi / BKPM": [
            "kementerian investasi",
            "bkpm",
            "badan koordinasi penanaman modal"
        ],

        "Kementerian Komunikasi dan Digital": [
            "kementerian komunikasi dan digital",
            "komdigi"
        ],

        "Kementerian Koordinator Bidang Perekonomian": [
            "kementerian koordinator bidang perekonomian",
            "menko perekonomian"
        ],

        "IDPRO": [
            "idpro",
            "indonesia data center provider organization"
        ]
    }

    organizations = []

    for organization, keywords in organization_keywords.items():

        for keyword in keywords:

            if keyword in text_lower:
                organizations.append(organization)
                break

    return unique_join(organizations)


# =========================================================
# PROJECT LOCATION
# =========================================================

def extract_project_location(text):

    text_lower = text.lower()

    # Lokasi yang relevan untuk proyek/infrastruktur data center.
    # Indonesia tidak dimasukkan karena terlalu umum.
    locations = {
        "Jakarta": [
            "jakarta"
        ],

        "Batam": [
            "batam",
            "nongsa"
        ],

        "Karawang": [
            "karawang"
        ],

        "Cikarang": [
            "cikarang"
        ],

        "Bekasi": [
            "bekasi"
        ],

        "Jawa Barat": [
            "jawa barat",
            "bandung"
        ],

        "Kepulauan Riau": [
            "kepulauan riau"
        ],

        "Surabaya": [
            "surabaya"
        ]
    }

    # Frasa yang secara eksplisit menghubungkan lokasi
    # dengan data center/proyek/site.
    explicit_location_patterns = [
        r"(?:data center|data centre|pusat data)\s+(?:yang\s+)?(?:berlokasi|berada|dibangun|akan dibangun|dikembangkan|didirikan)\s+(?:di|pada)\s+{location}",
        r"(?:data center|data centre|pusat data)\s+(?:di|pada)\s+{location}",
        r"(?:lokasi|site)\s+(?:data center|data centre|pusat data)\s+(?:berada\s+)?(?:di|pada)?\s*{location}",
        r"(?:berlokasi|berada|dibangun|akan dibangun|dikembangkan|didirikan)\s+(?:di|pada)\s+{location}\s+(?:dan\s+)?(?:data center|data centre|pusat data)",
        r"(?:membangun|mengembangkan|mendirikan)\s+(?:data center|data centre|pusat data)\s+(?:di|pada)\s+{location}",
        r"(?:proyek|pembangunan|kawasan)\s+(?:data center|data centre|pusat data)\s+(?:di|pada)\s+{location}",
    ]

    # Nama kawasan/site yang sangat spesifik.
    # Ini boleh menjadi indikator lokasi meskipun frasa
    # "data center di ..." tidak digunakan persis.
    site_contexts = {
        "Batam": [
            "kabil industrial estate",
            "nongsa digital park",
            "nongsa"
        ],
        "Karawang": [
            "suryacipta",
            "karawang"
        ],
        "Cikarang": [
            "cikarang"
        ],
        "Jawa Barat": [
            "suryacipta",
            "jawa barat"
        ],
        "Kepulauan Riau": [
            "kabil industrial estate",
            "nongsa digital park"
        ]
    }

    project_locations = []

    # ---------------------------------------------------------
    # 1. Cek pola eksplisit per lokasi
    # ---------------------------------------------------------
    for location, keywords in locations.items():

        found = False

        for keyword in keywords:

            escaped_location = re.escape(keyword)

            for pattern_template in explicit_location_patterns:

                pattern = pattern_template.format(
                    location=escaped_location
                )

                if re.search(pattern, text_lower):
                    project_locations.append(location)
                    found = True
                    break

            if found:
                break

    # ---------------------------------------------------------
    # 2. Cek site/kawasan yang sangat spesifik
    # ---------------------------------------------------------
    for location, site_keywords in site_contexts.items():

        found = False

        for site_keyword in site_keywords:

            if site_keyword not in text_lower:
                continue

            # Ambil konteks sekitar nama site untuk memastikan
            # pembahasannya memang terkait data center/pusat data.
            for match in re.finditer(
                re.escape(site_keyword),
                text_lower
            ):

                context = get_context(
                    text_lower,
                    match.start(),
                    window=250
                )

                has_data_center_context = any(
                    keyword in context
                    for keyword in [
                        "data center",
                        "data centre",
                        "pusat data"
                    ]
                )

                if has_data_center_context:
                    project_locations.append(location)
                    found = True
                    break

            if found:
                break

    return unique_join(project_locations)


# =========================================================
# INSIGHT TYPE
# =========================================================

def determine_insight_type(row):

    insight_types = []

    if row["investment_value"]:
        insight_types.append("Investment")

    if row["capacity"]:
        insight_types.append("Capacity")

    if row["technology"]:
        insight_types.append("Technology")

    if row["company"]:
        insight_types.append("Company")

    if row["project_location"]:
        insight_types.append("Location")

    return unique_join(insight_types)


# =========================================================
# MAIN
# =========================================================

print("====================================")
print("BUSINESS INSIGHT EXTRACTION")
print("====================================")

df = pd.read_csv(
    INPUT_FILE,
    encoding="utf-8-sig"
)

print(f"Total artikel: {len(df)}")


# Gabungkan teks
df["text_analysis"] = (
    df["title"].fillna("").astype(str)
    + " "
    + df["summary"].fillna("").astype(str)
    + " "
    + df["content_clean"].fillna("").astype(str)
)


# =========================================================
# RELEVANCE CHECK
# =========================================================

data_center_keywords = [
    "data center",
    "data centre",
    "pusat data"
]

# Keyword yang menunjukkan bahwa artikel memang membahas
# data center sebagai topik utama
strong_topic_keywords = [
    "data center",
    "data centre",
    "pusat data",
    "data center indonesia",
    "pusat data indonesia",
    "infrastruktur data center",
    "infrastruktur pusat data"
]


def contains_data_center(text):
    text_lower = str(text).lower()

    return any(
        keyword in text_lower
        for keyword in data_center_keywords
    )


def calculate_relevance(row):

    title = str(row.get("title", "")).lower()
    summary = str(row.get("summary", "")).lower()
    content = str(row.get("content_clean", "")).lower()

    score = 0

    # -----------------------------------------------------
    # 1. JUDUL
    # -----------------------------------------------------
    # Jika data center menjadi topik di judul,
    # berikan bobot paling besar.
    if any(keyword in title for keyword in strong_topic_keywords):
        score += 5

    # -----------------------------------------------------
    # 2. SUMMARY
    # -----------------------------------------------------
    if any(keyword in summary for keyword in data_center_keywords):
        score += 2

    # -----------------------------------------------------
    # 3. CONTENT
    # -----------------------------------------------------
    # Hitung berapa kali istilah data center muncul
    content_count = sum(
        content.count(keyword)
        for keyword in data_center_keywords
    )

    if content_count >= 3:
        score += 3
    elif content_count >= 1:
        score += 1

    # -----------------------------------------------------
    # 4. TOPIC
    # -----------------------------------------------------
    topic = str(row.get("topic", "")).lower()

    if topic in [
        "infrastructure",
        "investment",
        "energy",
        "cloud",
        "market",
        "government & regulation"
    ]:
        score += 1

    # -----------------------------------------------------
    # HAS DATA CENTER CONTEXT
    # -----------------------------------------------------
    has_context = (
        contains_data_center(title)
        or contains_data_center(summary)
        or contains_data_center(content)
    )

    # -----------------------------------------------------
    # CLASSIFICATION
    # -----------------------------------------------------
    if not has_context:
        return "Not Relevant", score

    if score >= 5:
        return "Relevant", score

    elif score >= 2:
        return "Review", score

    else:
        return "Not Relevant", score


# =========================================================
# APPLY RELEVANCE CHECK
# =========================================================

before_relevance_filter = len(df)

df[["relevance_check", "relevance_check_score"]] = df.apply(
    lambda row: calculate_relevance(row),
    axis=1,
    result_type="expand"
)

print("\n====================================")
print("RELEVANCE CHECK")
print("====================================")

print(
    df["relevance_check"]
    .value_counts()
)

print("\n====================================")
print("ARTIKEL REVIEW")
print("====================================")

print(
    df[df["relevance_check"] == "Review"][
        ["title", "relevance_check_score"]
    ].to_string(index=False)
)

# Hanya lanjutkan artikel Relevant dan Review.
df = df[
    df["relevance_check"].isin([
        "Relevant",
        "Review"
    ])
].copy()

print(
    f"\nArtikel setelah relevance check : {len(df)} "
    f"(dari {before_relevance_filter})"
)
# =========================================================
# REVIEW FILTER
# =========================================================

exclude_title_keywords = [
    "jampidsus mundur",
    "dampak fta"
]

def is_excluded_review(title):
    title_lower = str(title).lower()

    return any(
        keyword in title_lower
        for keyword in exclude_title_keywords
    )

before_review_filter = len(df)

df = df[
    ~(
        (df["relevance_check"] == "Review") &
        (df["title"].apply(is_excluded_review))
    )
].copy()

print(
    f"Artikel setelah review filter : {len(df)} "
    f"(dari {before_review_filter})"
)


# =========================================================
# HAPUS KOLOM SEMENTARA
# =========================================================

df.drop(
    columns=[
        "relevance_check",
        "relevance_check_score"
    ],
    inplace=True,
    errors="ignore"
)


# =========================================================
# TECHNOLOGY
# =========================================================

df["technology"] = df["text_analysis"].apply(
    extract_technology
)


# =========================================================
# INVESTMENT
# =========================================================

investment_result = df["text_analysis"].apply(
    extract_investment
)

df["investment_value"] = investment_result.apply(
    lambda x: x[0]
)

df["investment_type"] = investment_result.apply(
    lambda x: x[1]
)

df["investment_context"] = investment_result.apply(
    lambda x: x[2]
)


# =========================================================
# CAPACITY
# =========================================================

capacity_result = df["text_analysis"].apply(
    extract_capacity
)

df["capacity"] = capacity_result.apply(
    lambda x: x[0]
)

df["capacity_type"] = capacity_result.apply(
    lambda x: x[1]
)

df["capacity_context"] = capacity_result.apply(
    lambda x: x[2]
)


# =========================================================
# COMPANY
# =========================================================

df["company"] = df["text_analysis"].apply(
    extract_company
)


# =========================================================
# ORGANIZATION
# =========================================================

df["organization"] = df["text_analysis"].apply(
    extract_organization
)


# =========================================================
# PROJECT LOCATION
# =========================================================

df["project_location"] = df["text_analysis"].apply(
    extract_project_location
)


# =========================================================
# SECTOR
# =========================================================

df["sector"] = "Data Center & Cloud"


# =========================================================
# INSIGHT TYPE
# =========================================================

df["insight_type"] = df.apply(
    determine_insight_type,
    axis=1
)


# =========================================================
# HAPUS KOLOM LOCATION LAMA
# =========================================================

if "location" in df.columns:
    df.drop(columns=["location"], inplace=True)


# =========================================================
# URUTKAN KOLOM
# =========================================================

preferred_columns = [
    "title",
    "published_date",
    "summary",
    "article_url",
    "image_url",
    "source",
    "tag",
    "sector",
    "topic",
    "relevance",
    "relevance_score",

    "technology",

    "investment_value",
    "investment_type",
    "investment_context",

    "capacity",
    "capacity_type",
    "capacity_context",

    "company",
    "organization",
    "project_location",

    "insight_type",

    "content_clean",
    "scraped_at",
    "text_analysis"
]

existing_columns = [
    col
    for col in preferred_columns
    if col in df.columns
]

df = df[existing_columns]


# =========================================================
# SIMPAN
# =========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# SUMMARY
# =========================================================

print()
print("====================================")
print("EXTRACTION SELESAI")
print("====================================")

print(f"Total artikel        : {len(df)}")

print(
    "Technology           :",
    (df["technology"] != "").sum()
)

print(
    "Investment           :",
    (df["investment_value"] != "").sum()
)

print(
    "Capacity             :",
    (df["capacity"] != "").sum()
)

print(
    "Company              :",
    (df["company"] != "").sum()
)

print(
    "Organization         :",
    (df["organization"] != "").sum()
)

print(
    "Project Location     :",
    (df["project_location"] != "").sum()
)

print()
print("====================================")
print("DISTRIBUSI INVESTMENT TYPE")
print("====================================")

print(
    df["investment_type"]
    .replace("", "Tidak ada")
    .value_counts()
)

print()
print("====================================")
print("DISTRIBUSI CAPACITY TYPE")
print("====================================")

print(
    df["capacity_type"]
    .replace("", "Tidak ada")
    .value_counts()
)

print()
print("File:")
print(OUTPUT_FILE)
