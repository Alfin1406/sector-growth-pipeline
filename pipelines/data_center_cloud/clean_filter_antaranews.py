import pandas as pd
import re


# ==================================================
# 1. BACA DATA HASIL SCRAPING
# ==================================================

input_file = "data_center_antaranews_with_content.csv"

df = pd.read_csv(
    input_file,
    encoding="utf-8-sig"
)

print("====================================")
print("DATA AWAL")
print("====================================")
print("Jumlah artikel:", len(df))


# ==================================================
# 2. CLEANING TEXT
# ==================================================

def clean_text(text):

    if pd.isna(text):
        return ""

    text = str(text)

    # Hapus bagian Baca juga
    text = re.sub(
        r'Baca juga:\s*[^\n]+',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Hapus informasi pewarta
    text = re.sub(
        r'Pewarta:\s*[^\n]+',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Hapus copyright
    text = re.sub(
        r'Copyright\s*©?.*',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Hapus peringatan crawling/scraping
    text = re.sub(
        r'Dilarang keras.*',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Rapikan spasi
    text = re.sub(
        r'\s+',
        ' ',
        text
    )

    return text.strip()


df["content_clean"] = df["content"].apply(clean_text)


# ==================================================
# 3. GABUNGKAN TEKS UNTUK ANALISIS
# ==================================================

df["text_analysis"] = (
    df["title"].fillna("") + " " +
    df["summary"].fillna("") + " " +
    df["content_clean"].fillna("")
).str.lower()


# ==================================================
# 4. KEYWORD UNTUK TOPIK
# ==================================================

topic_keywords = {

    "Investment": [
        "investasi",
        "investor",
        "pendanaan",
        "modal",
        "dana",
        "invest",
        "proyek"
    ],

    "Infrastructure": [
        "data center",
        "data centre",
        "pusat data",
        "infrastruktur",
        "kapasitas",
        "fasilitas",
        "server"
    ],

    "Energy": [
        "listrik",
        "energi",
        "geothermal",
        "panas bumi",
        "energi terbarukan",
        "energi baru terbarukan",
        "green data center",
        "pendingin",
        "cooling"
    ],

    "Cloud": [
        "cloud",
        "cloud computing",
        "cloud infrastructure",
        "cloud region",
        "hyperscaler"
    ],

    "Market": [
        "pasar",
        "pertumbuhan",
        "permintaan",
        "peluang",
        "bisnis",
        "regional"
    ],

    "Government & Regulation": [
        "pemerintah",
        "kementerian",
        "regulasi",
        "kebijakan",
        "aturan",
        "bkpm"
    ]
}


# ==================================================
# 5. TENTUKAN TOPIK
# ==================================================

def detect_topic(text):

    scores = {}

    for topic, keywords in topic_keywords.items():

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        scores[topic] = score


    # Jika tidak ada keyword
    if max(scores.values()) == 0:
        return "Other"


    # Ambil topic dengan skor tertinggi
    return max(
        scores,
        key=scores.get
    )


df["topic"] = df["text_analysis"].apply(
    detect_topic
)


# ==================================================
# 6. CEK RELEVANSI
# ==================================================

relevant_keywords = [

    "data center",
    "data centre",
    "pusat data",

    "cloud computing",
    "cloud infrastructure",

    "hyperscaler",

    "green data center",

    "infrastruktur data center",

    "investasi data center",

    "pembangunan data center",

    "kapasitas data center",

    "fasilitas data center"
]


def check_relevance(text):

    score = 0

    for keyword in relevant_keywords:

        if keyword in text:
            score += 1


    return score


df["relevance_score"] = df["text_analysis"].apply(
    check_relevance
)


# ==================================================
# 7. TENTUKAN RELEVANT / REVIEW
# ==================================================

def relevance_status(score):

    if score >= 2:
        return "Relevant"

    elif score == 1:
        return "Review"

    else:
        return "Not Relevant"


df["relevance"] = df["relevance_score"].apply(
    relevance_status
)


# ==================================================
# 8. SECTOR
# ==================================================

df["sector"] = "Data Center & Cloud"


# ==================================================
# 9. HAPUS DUPLIKAT
# ==================================================

df = df.drop_duplicates(
    subset=["article_url"]
)


# ==================================================
# 10. PILIH KOLOM FINAL
# ==================================================

final_columns = [

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

    "content_clean",

    "scraped_at"
]


df_final = df[final_columns]


# ==================================================
# 11. SIMPAN DATA CURATED
# ==================================================

output_file = "data_center_antaranews_curated.csv"

df_final.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)


# ==================================================
# 12. TAMPILKAN HASIL
# ==================================================

print("\n====================================")
print("FILTER SELESAI")
print("====================================")

print("Total artikel:", len(df_final))

print("\nStatus relevansi:")

print(
    df_final["relevance"].value_counts()
)

print("\nTopik:")

print(
    df_final["topic"].value_counts()
)

print("\nFile:")
print(output_file)