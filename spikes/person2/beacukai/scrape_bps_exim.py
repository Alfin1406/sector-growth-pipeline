
import os
import re
import time
import requests
import pandas as pd

from datetime import datetime
from dotenv import load_dotenv

# =========================================================
# KONFIGURASI
# =========================================================

load_dotenv()

API_KEY = os.getenv("BPS_API_KEY")

BASE_URL = "https://webapi.bps.go.id/v1/api/dataexim"

CURRENT_YEAR = datetime.now().year

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..")
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "raw_data",
    "beacukai"
)

HS_CODES = [f"{i:02d}" for i in range(1, 100)]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# AMBIL DATA DARI BPS API
# =========================================================

def fetch_exim(source, hs_code, year):
    url = (
        f"{BASE_URL}/sumber/{source}"
        f"/kodehs/{hs_code}"
        f"/jenishs/1"
        f"/tahun/{year}"
        f"/periode/1"
        f"/key/{API_KEY}/"
    )

    for attempt in range(3):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            if result.get("status") != "OK":
                raise RuntimeError(
                    f"API BPS error: {result}"
                )

            if result.get("data-availability") != "available":
                return []

            return result.get("data", [])

        except Exception as error:
            if attempt == 2:
                raise RuntimeError(
                    f"Gagal mengambil tahun {year}, "
                    f"HS {hs_code}, sumber {source}: {error}"
                )

            time.sleep(3 * (attempt + 1))

    return []


# =========================================================
# NORMALISASI DATA
# =========================================================

def normalize_records(records, source, hs_code, year):
    normalized = []

    for row in records:
        month_text = str(row.get("bulan", ""))

        match = re.search(r"\[(\d{1,2})\]", month_text)

        if not match:
            continue

        month = int(match.group(1))

        if not 1 <= month <= 12:
            continue

        normalized.append({
            "year": year,
            "month": month,
            "hs_code": hs_code,
            "hs_description": row.get("kodehs", ""),
            "value": float(row.get("value") or 0),
            "netweight": float(row.get("netweight") or 0),
            "source": source
        })

    return normalized


# =========================================================
# DOWNLOAD SEMUA DATA HS
# =========================================================

def collect_all_data(year):
    all_records = []

    total = len(HS_CODES) * 2
    counter = 0

    for hs_code in HS_CODES:
        for source in [1, 2]:

            counter += 1

            source_name = (
                "EKSPOR" if source == 1 else "IMPOR"
            )

            print(
                f"[{counter}/{total}] "
                f"{source_name} HS {hs_code} - {year}"
            )

            records = fetch_exim(
                source,
                hs_code,
                year
            )

            normalized = normalize_records(
                records,
                source,
                hs_code,
                year
            )

            all_records.extend(normalized)

            # Jeda agar tidak membebani API BPS
            time.sleep(1)

    return pd.DataFrame(all_records)


# =========================================================
# FILE 1: TOTAL EKSPOR IMPOR BULANAN NASIONAL
# =========================================================

def create_monthly_file(df):
    if df.empty:
        raise ValueError("Data API kosong.")

    grouped = (
        df.groupby(["year", "month", "source"])
        [["value", "netweight"]]
        .sum()
        .reset_index()
    )

    export = grouped[grouped["source"] == 1].copy()
    import_ = grouped[grouped["source"] == 2].copy()

    export = export.rename(columns={
        "value": "Nilai Ekspor (USD)",
        "netweight": "Berat Ekspor (Kg)"
    })

    import_ = import_.rename(columns={
        "value": "Nilai Impor (USD)",
        "netweight": "Berat Impor (Kg)"
    })

    export = export.drop(columns=["source"])
    import_ = import_.drop(columns=["source"])

    result = pd.merge(
        export,
        import_,
        on=["year", "month"],
        how="outer"
    )

    result = result.fillna(0)

    month_names = {
        1: "Januari", 2: "Februari",
        3: "Maret", 4: "April",
        5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober",
        11: "November", 12: "Desember"
    }

    result["Bulan"] = result["month"].map(month_names)
    result["Tahun"] = result["year"]

    result = result[[
        "Tahun",
        "Bulan",
        "Nilai Ekspor (USD)",
        "Berat Ekspor (Kg)",
        "Nilai Impor (USD)",
        "Berat Impor (Kg)"
    ]]

    result = result.sort_values(
        ["Tahun", "Bulan"],
        key=lambda col: col.map(
            {name: number for number, name in month_names.items()}
        ) if col.name == "Bulan" else col
    )

    result.to_csv(
        f"{OUTPUT_DIR}/bps_ekspor_impor_bulanan.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nFile bulanan berhasil dibuat.")
    print(result.to_string(index=False))


# =========================================================
# FILE 2: EKSPOR IMPOR HS 2 DIGIT BULAN TERBARU
# =========================================================

def create_hs2_file(df):
    if df.empty:
        raise ValueError("Data HS tidak tersedia.")

    latest_period = (
        df[["year", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month"])
        .iloc[-1]
    )

    latest_year = int(latest_period["year"])
    latest_month = int(latest_period["month"])

    september = df[
        (df["year"] == latest_year) &
        (df["month"] == latest_month)
    ].copy()

    grouped = (
        september.groupby(
            ["hs_code", "hs_description", "source"]
        )[["value", "netweight"]]
        .sum()
        .reset_index()
    )

    export = grouped[grouped["source"] == 1].copy()
    import_ = grouped[grouped["source"] == 2].copy()

    export = export.rename(columns={
        "value": "Nilai Ekspor (USD)",
        "netweight": "Berat Ekspor (Kg)"
    })

    import_ = import_.rename(columns={
        "value": "Nilai Impor (USD)",
        "netweight": "Berat Impor (Kg)"
    })

    export = export.drop(columns=["source"])
    import_ = import_.drop(columns=["source"])

    result = pd.merge(
        export,
        import_,
        on=["hs_code", "hs_description"],
        how="outer"
    )

    result = result.fillna(0)

    result = result.rename(columns={
        "hs_description": "Kode HS dan Deskripsi"
    })

    result["Tahun"] = latest_year

    month_names = {
        1: "Januari", 2: "Februari",
        3: "Maret", 4: "April",
        5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober",
        11: "November", 12: "Desember"
    }

    result["Bulan"] = month_names[latest_month]

    result = result[[
        "Tahun",
        "Bulan",
        "Kode HS dan Deskripsi",
        "Nilai Ekspor (USD)",
        "Berat Ekspor (Kg)",
        "Nilai Impor (USD)",
        "Berat Impor (Kg)"
    ]]

    result = result.sort_values("Kode HS dan Deskripsi")

    result.to_csv(
        f"{OUTPUT_DIR}/bps_ekspor_impor_hs2_bulanan_terbaru.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nFile HS 2 Digit berhasil dibuat.")
    print("Periode:", month_names[latest_month], latest_year)
    print("Jumlah baris:", len(result))
    print(result.head(10).to_string(index=False))


# =========================================================
# MAIN
# =========================================================

def main():
    if not API_KEY:
        raise ValueError(
            "BPS_API_KEY tidak ditemukan di file .env"
        )

    print("=" * 60)
    print("BPS EXPORT IMPORT DATA COLLECTOR")
    print("=" * 60)

    df = pd.DataFrame()

    # Coba tahun berjalan terlebih dahulu.
    # Jika belum tersedia, coba maksimal 2 tahun sebelumnya.
    for year in range(CURRENT_YEAR, CURRENT_YEAR - 3, -1):

        print(f"\nMencoba mengambil data tahun {year}...")

        df = collect_all_data(year)

        if not df.empty:
            print(f"\nData tahun {year} berhasil ditemukan.")
            break

        print(f"Data tahun {year} belum tersedia.")

    if df.empty:
        raise ValueError(
            "Data BPS tidak ditemukan dalam 3 tahun terakhir."
        )

    print("\nTotal record API:", len(df))

    create_monthly_file(df)
    create_hs2_file(df)

    print("\n" + "=" * 60)
    print("PROSES SELESAI")
    print("Folder output:", OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
