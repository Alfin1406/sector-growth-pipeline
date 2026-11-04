import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta


# ==========================================================
# 1. FILE INPUT
# ==========================================================

input_file = "data_center_kompas_curated.csv"


# ==========================================================
# 2. BACA DATA
# ==========================================================

df = pd.read_csv(
    input_file,
    encoding="utf-8-sig"
)

print("====================================")
print("FILTER DATA KOMPAS")
print("====================================")

print("Total data awal:", len(df))


# ==========================================================
# 3. KONVERSI TANGGAL
# ==========================================================

df["published_date"] = pd.to_datetime(
    df["published_date"],
    errors="coerce"
)


# ==========================================================
# 4. CEK TANGGAL
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
# 6. FILTER 12 BULAN TERAKHIR
# ==========================================================

current_df = df[
    (df["published_date"] >= start_date) &
    (df["published_date"] <= today)
].copy()


# ==========================================================
# 7. URUTKAN DATA
# ==========================================================

current_df = current_df.sort_values(
    by="published_date",
    ascending=False
)


# ==========================================================
# 8. SIMPAN DATA CURRENT
# ==========================================================

current_file = "data_center_kompas_current.csv"

current_df.to_csv(
    current_file,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================================
# 9. HASIL FILTER
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


# ==========================================================
# 10. 5 DATA TERBARU
# ==========================================================

print("\n====================================")
print("5 DATA TERBARU")
print("====================================")

print(
    current_df[
        [
            "title",
            "published_date",
            "source"
        ]
    ]
    .head(5)
    .to_string(index=False)
)


# ==========================================================
# 11. RENTANG DATA FINAL
# ==========================================================

if len(current_df) > 0:

    print("\n====================================")
    print("RENTANG DATA FINAL")
    print("====================================")

    print(
        "Tanggal paling lama :",
        current_df["published_date"].min()
    )

    print(
        "Tanggal paling baru :",
        current_df["published_date"].max()
    )


# ==========================================================
# 12. FILE OUTPUT
# ==========================================================

print("\n====================================")
print("FILE BERHASIL DIBUAT")
print("====================================")

print("1.", current_file)

print("\n====================================")
print("PROSES SELESAI")
print("====================================")