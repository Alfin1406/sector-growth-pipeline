import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta


# ==========================================================
# 1. FILE INPUT
# ==========================================================

input_file = "data_center_antaranews_curated.csv"


# ==========================================================
# 2. BACA DATA
# ==========================================================

df = pd.read_csv(
    input_file,
    encoding="utf-8-sig"
)

print("====================================")
print("FILTER DATA ANTARA")
print("====================================")

print("Total data awal:", len(df))


# ==========================================================
# 3. KONVERSI TANGGAL INDONESIA
# ==========================================================

month_mapping = {
    "Januari": "January",
    "Februari": "February",
    "Maret": "March",
    "April": "April",
    "Mei": "May",
    "Juni": "June",
    "Juli": "July",
    "Agustus": "August",
    "September": "September",
    "Oktober": "October",
    "November": "November",
    "Desember": "December"
}


def convert_indonesian_date(date):

    # Jika data kosong
    if pd.isna(date):
        return pd.NaT

    date = str(date).strip()

    # Ubah nama bulan Indonesia menjadi Inggris
    for indo, english in month_mapping.items():
        date = date.replace(indo, english)

    # Konversi menjadi format tanggal
    return pd.to_datetime(
        date,
        errors="coerce"
    )


df["published_date"] = df["published_date"].apply(
    convert_indonesian_date
)


# ==========================================================
# 4. CEK TANGGAL YANG GAGAL DIKONVERSI
# ==========================================================

invalid_date = df["published_date"].isna().sum()

print("\nTanggal gagal dibaca:", invalid_date)

if invalid_date > 0:

    print("\nData dengan tanggal tidak terbaca:")

    print(
        df.loc[
            df["published_date"].isna(),
            ["title", "published_date"]
        ].to_string(index=False)
    )


# ==========================================================
# 5. TENTUKAN PERIODE 12 BULAN
# ==========================================================

today = datetime.now()

start_date = today - relativedelta(months=12)

print("\n====================================")
print("PERIODE DATA")
print("====================================")

print(
    "Mulai :",
    start_date.strftime("%Y-%m-%d")
)

print(
    "Sampai:",
    today.strftime("%Y-%m-%d")
)


# ==========================================================
# 6. FILTER BERITA 12 BULAN TERAKHIR
# ==========================================================

current_df = df[
    (df["published_date"] >= start_date) &
    (df["published_date"] <= today)
].copy()


# ==========================================================
# 7. FILTER STATUS RELEVANSI
# ==========================================================

current_relevant = current_df[
    current_df["relevance"].isin([
        "Relevant",
        "Review"
    ])
].copy()


# ==========================================================
# 8. AMBIL DATA REVIEW
# ==========================================================

review_df = current_df[
    current_df["relevance"] == "Review"
].copy()


# ==========================================================
# 9. URUTKAN DATA BERDASARKAN TANGGAL
# ==========================================================

current_relevant = current_relevant.sort_values(
    by="published_date",
    ascending=False
)

review_df = review_df.sort_values(
    by="published_date",
    ascending=False
)


# ==========================================================
# 10. SIMPAN DATA CURRENT
# ==========================================================

current_file = "data_center_antaranews_current.csv"

current_relevant.to_csv(
    current_file,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================================
# 11. SIMPAN DATA REVIEW
# ==========================================================

review_file = "data_center_antaranews_review.csv"

review_df.to_csv(
    review_file,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================================
# 12. HASIL FILTER
# ==========================================================

print("\n====================================")
print("HASIL FILTER")
print("====================================")

print(
    "Total artikel awal        :",
    len(df)
)

print(
    "Artikel 12 bulan terakhir :",
    len(current_df)
)

print(
    "Current Relevant + Review :",
    len(current_relevant)
)

print(
    "Artikel Review            :",
    len(review_df)
)


# ==========================================================
# 13. DISTRIBUSI TOPIK
# ==========================================================

print("\n====================================")
print("DISTRIBUSI TOPIC CURRENT")
print("====================================")

print(
    current_relevant["topic"].value_counts()
)


# ==========================================================
# 14. DISTRIBUSI RELEVANSI
# ==========================================================

print("\n====================================")
print("DISTRIBUSI RELEVANCE CURRENT")
print("====================================")

print(
    current_relevant["relevance"].value_counts()
)


# ==========================================================
# 15. INFORMASI DATA REVIEW
# ==========================================================

print("\n====================================")
print("DATA REVIEW")
print("====================================")

if len(review_df) > 0:

    print(
        review_df[
            [
                "title",
                "published_date",
                "topic",
                "relevance_score"
            ]
        ].to_string(index=False)
    )

else:

    print("Tidak ada artikel yang perlu direview.")


# ==========================================================
# 16. FILE OUTPUT
# ==========================================================

print("\n====================================")
print("FILE BERHASIL DIBUAT")
print("====================================")

print("1.", current_file)
print("2.", review_file)

print("\n====================================")
print("PROSES SELESAI")
print("====================================")