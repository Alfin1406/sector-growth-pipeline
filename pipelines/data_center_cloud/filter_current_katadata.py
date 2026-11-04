
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta


# ==========================================
# 1. FILE INPUT DAN OUTPUT
# ==========================================

INPUT_FILE = "data_center_katadata_curated.csv"
OUTPUT_FILE = "data_center_katadata_current.csv"
REVIEW_FILE = "data_center_katadata_review.csv"


# ==========================================
# 2. BACA DATA
# ==========================================

df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

print("====================================")
print("FILTER DATA KATADATA")
print("====================================")
print("Total data curated:", len(df))


# ==========================================
# 3. KONVERSI TANGGAL INDONESIA
# ==========================================

month_mapping = {
    "januari": "January",
    "februari": "February",
    "maret": "March",
    "april": "April",
    "mei": "May",
    "juni": "June",
    "juli": "July",
    "agustus": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "desember": "December",
}


def convert_indonesian_date(value):
    if pd.isna(value):
        return pd.NaT

    date_text = str(value).strip()

    for indo, english in month_mapping.items():
        date_text = date_text.replace(
            indo, english
        ).replace(
            indo.capitalize(), english
        )

    return pd.to_datetime(
        date_text,
        errors="coerce"
    )


df["published_date_parsed"] = df[
    "published_date"
].apply(convert_indonesian_date)


# ==========================================
# 4. CEK TANGGAL GAGAL DIPROSES
# ==========================================

invalid_dates = df["published_date_parsed"].isna().sum()

print("Tanggal gagal dibaca:", invalid_dates)

if invalid_dates > 0:
    print("\nContoh tanggal yang gagal dibaca:")
    print(
        df.loc[
            df["published_date_parsed"].isna(),
            ["title", "published_date"]
        ].to_string(index=False)
    )


# ==========================================
# 5. PERIODE 12 BULAN TERAKHIR
# ==========================================

today = pd.Timestamp(datetime.now().date())
start_date = today - pd.DateOffset(months=12)

print("\nPeriode filter:")
print("Mulai :", start_date.strftime("%Y-%m-%d"))
print("Sampai:", today.strftime("%Y-%m-%d"))


# ==========================================
# 6. FILTER ARTIKEL
# ==========================================

mask_current = (
    (df["published_date_parsed"] >= start_date)
    & (df["published_date_parsed"] <= today)
)

df_current = df.loc[mask_current].copy()
df_review = df.loc[~mask_current].copy()


# ==========================================
# 7. URUTKAN BERDASARKAN TANGGAL
# ==========================================

df_current = df_current.sort_values(
    by="published_date_parsed",
    ascending=False
)

df_review = df_review.sort_values(
    by="published_date_parsed",
    ascending=False
)


# ==========================================
# 8. HAPUS KOLOM BANTU
# ==========================================

df_current = df_current.drop(
    columns=["published_date_parsed"]
)

df_review = df_review.drop(
    columns=["published_date_parsed"]
)


# ==========================================
# 9. SIMPAN HASIL
# ==========================================

df_current.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

df_review.to_csv(
    REVIEW_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 10. RINGKASAN
# ==========================================

print("\n====================================")
print("HASIL FILTER KATADATA")
print("====================================")
print("Total artikel awal :", len(df))
print("Artikel current    :", len(df_current))
print("Artikel review     :", len(df_review))

print("\nDistribusi relevansi current:")
if "relevance" in df_current.columns:
    print(df_current["relevance"].value_counts())

print("\nFile output:")
print(OUTPUT_FILE)
print(REVIEW_FILE)
print("\nProses selesai.")
