import pandas as pd


INPUT_FILE = "data_center_kompas_all.csv"
OUTPUT_FILE = "data_center_kompas_curated.csv"


# ==========================================
# LOAD DATA
# ==========================================

df = pd.read_csv(
    INPUT_FILE,
    encoding="utf-8-sig"
)

print("Total data awal:", len(df))


# ==========================================
# CLEAN TEXT
# ==========================================

text_columns = [
    "title",
    "summary",
    "content"
]

for column in text_columns:

    df[column] = (
        df[column]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


# ==========================================
# CLEAN DUPLICATE
# ==========================================

df = df.drop_duplicates(
    subset=["article_url"]
)

print(
    "Setelah hapus duplikat:",
    len(df)
)


# ==========================================
# KEYWORD
# ==========================================

indonesia_keywords = [
    "indonesia",
    "indonesian",
    "ri ",
    "jakarta",
    "banten",
    "tangerang",
    "bsd",
    "karawang",
    "cikarang",
    "bekasi",
    "jawa barat",
    "jawa timur",
    "jawa tengah",
    "batam",
    "kepulauan riau",
    "surabaya",
    "pln",
    "telkom indonesia",
    "indosat",
    "dci indonesia",
    "neutradc",
    "danantara"
]


data_center_keywords = [
    "data center",
    "data centre",
    "pusat data",
    "hyperscale",
    "data center indonesia",
    "pusat data indonesia"
]


foreign_keywords = [
    "korea selatan",
    "south korea",
    "finlandia",
    "finland",
    "amerika serikat",
    "amerika",
    "cina",
    "china",
    "singapura",
    "singapore"
]


irrelevant_keywords = [
    "ihsg",
    "wall street",
    "saham",
    "indeks harga saham"
]


# ==========================================
# RELEVANCE FUNCTION
# ==========================================

def check_relevance(row):

    title = row["title"].lower()

    text = (
        row["title"]
        + " "
        + row["summary"]
        + " "
        + row["content"]
    ).lower()


    # --------------------------------------
    # 1. TOPIK YANG JELAS BUKAN FOKUS
    # --------------------------------------

    if any(
        keyword in title
        for keyword in irrelevant_keywords
    ):
        return "Not Relevant"


    # --------------------------------------
    # 2. DATA CENTER LUAR NEGERI
    # --------------------------------------

    if any(
        keyword in title
        for keyword in foreign_keywords
    ):
        return "Not Relevant"


    # --------------------------------------
    # 3. HARUS ADA DATA CENTER
    # --------------------------------------

    has_data_center = any(
        keyword in text
        for keyword in data_center_keywords
    )

    if not has_data_center:
        return "Not Relevant"


    # --------------------------------------
    # 4. HARUS ADA INDIKASI INDONESIA
    # --------------------------------------

    has_indonesia = any(
        keyword in text
        for keyword in indonesia_keywords
    )

    if has_indonesia:
        return "Relevant"


    # --------------------------------------
    # 5. MASIH BERKAITAN
    # --------------------------------------

    return "Review"


# ==========================================
# APPLY RELEVANCE
# ==========================================

df["relevance"] = df.apply(
    check_relevance,
    axis=1
)


# ==========================================
# FILTER
# ==========================================

df_curated = df[
    df["relevance"].isin(
        ["Relevant", "Review"]
    )
].copy()


# ==========================================
# SAVE
# ==========================================

df_curated.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# RESULT
# ==========================================

print()
print("=" * 50)
print("CLEANING & FILTER KOMPAS SELESAI")
print("=" * 50)

print(
    "Relevant:",
    len(
        df[df["relevance"] == "Relevant"]
    )
)

print(
    "Review:",
    len(
        df[df["relevance"] == "Review"]
    )
)

print(
    "Not Relevant:",
    len(
        df[df["relevance"] == "Not Relevant"]
    )
)

print(
    "Total disimpan:",
    len(df_curated)
)

print()
print(
    f"File output: {OUTPUT_FILE}"
)