import io
import warnings
import zipfile
from datetime import datetime

import pandas as pd
import requests

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
warnings.filterwarnings("ignore", message="The xlrd engine is deprecated")
warnings.filterwarnings("ignore", category=FutureWarning)

BULAN_INDO = {
    1: "JANUARI",
    2: "FEBRUARI",
    3: "MARET",
    4: "APRIL",
    5: "MEI",
    6: "JUNI",
    7: "JULI",
    8: "AGUSTUS",
    9: "SEPTEMBER",
    10: "OKTOBER",
    11: "NOVEMBER",
    12: "DESEMBER",
}

BULAN_VALID = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TARGET_SHEETS = ["I.4_1", "I.4_2", "I.4_3"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _klasifikasi_baris(val) -> str:
    teks = str(val).strip()
    if teks.startswith(("1.", "2.", "3.", "4.", "5.", "6.")):
        return "BANK"
    if teks.startswith("Pinjaman"):
        return "KATEGORI"
    return "SEKTOR"


def download_latest_seki_excel(lookback_months: int = 4) -> tuple[bytes, str, int]:
    """Mencari dan mengunduh file Excel TABEL1_4 dari ZIP SEKI BI terbaru secara in-memory."""
    current_date = datetime.now()

    for i in range(lookback_months):
        target_bulan = current_date.month - i
        target_tahun = current_date.year
        while target_bulan <= 0:
            target_bulan += 12
            target_tahun -= 1

        nama_bulan = BULAN_INDO[target_bulan]
        url_bi = (
            "https://www.bi.go.id/id/statistik/ekonomi-keuangan/seki/Documents/"
            f"SEKI_{nama_bulan}_{target_tahun}.zip"
        )
        print(f"[*] Mengecek: SEKI {nama_bulan} {target_tahun}...")

        try:
            resp = requests.get(url_bi, headers=HEADERS, timeout=60)
        except Exception as e:
            print(f"[-] Gagal koneksi ke {url_bi}: {e}. Mundur...")
            continue

        if resp.status_code == 200:
            try:
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zip_ref:
                    for nama_file in zip_ref.namelist():
                        if "TABEL1_4" in nama_file.upper() and nama_file.lower().endswith((".xls", ".xlsx")):
                            print(f"[*] Ketemu file Excel: {nama_file}")
                            return zip_ref.read(nama_file), nama_bulan.capitalize(), target_tahun
            except zipfile.BadZipFile:
                print("[-] Belum rilis (respons 200 tetapi bukan ZIP). Mundur...")
        else:
            print(f"[-] Belum rilis (Status {resp.status_code}). Mundur...")

    raise RuntimeError(f"File SEKI BI tidak ditemukan dalam {lookback_months} bulan terakhir.")


def parse_seki_excel(xls_bytes: bytes, tahun_rilis: int) -> list[dict]:
    """Cleansing (forward-fill) & unpivot sheet I.4_1 s.d. I.4_3 secara in-memory."""
    print("[*] Memulai proses cleansing & unpivot data Excel SEKI BI...")
    excel_file = pd.ExcelFile(io.BytesIO(xls_bytes))
    list_df_clean = []

    for sheet_name in TARGET_SHEETS:
        if sheet_name not in excel_file.sheet_names:
            continue

        df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=4)
        if "Unnamed: 2" not in df.columns:
            continue

        df = df.rename(columns={"Unnamed: 2": "Deskripsi"})
        df = df.dropna(subset=["Deskripsi"]).copy()
        df["Kelompok_Bank"] = None
        df["Kategori_Pinjaman"] = None

        tipe_baris = df["Deskripsi"].apply(_klasifikasi_baris)
        df.loc[tipe_baris == "BANK", "Kelompok_Bank"] = df["Deskripsi"]
        df.loc[tipe_baris == "KATEGORI", "Kategori_Pinjaman"] = df["Deskripsi"]

        df["Kelompok_Bank"] = df["Kelompok_Bank"].ffill()
        df["Kategori_Pinjaman"] = df["Kategori_Pinjaman"].ffill()

        df = df[tipe_baris == "SEKTOR"].rename(columns={"Deskripsi": "Sektor_KBLI"})
        month_cols = [c for c in df.columns if str(c).split(".")[0] in BULAN_VALID]

        df_melted = df.melt(
            id_vars=["Sektor_KBLI", "Kelompok_Bank", "Kategori_Pinjaman"],
            value_vars=month_cols,
            var_name="Bulan_Tahun",
            value_name="Nilai_Kredit_Miliar_Rp",
        )

        df_melted["Nilai_Kredit_Miliar_Rp"] = pd.to_numeric(
            df_melted["Nilai_Kredit_Miliar_Rp"], errors="coerce"
        )
        df_melted = df_melted.dropna(subset=["Nilai_Kredit_Miliar_Rp"])

        df_melted["Bulan"] = df_melted["Bulan_Tahun"].apply(lambda x: str(x).split(".")[0])
        df_melted["Tahun"] = df_melted["Bulan_Tahun"].apply(
            lambda x: int(tahun_rilis) if ".1" in str(x) else int(tahun_rilis - 1)
        )
        df_melted["Sheet_Asal"] = sheet_name

        df_clean = df_melted[
            [
                "Sheet_Asal",
                "Tahun",
                "Bulan",
                "Kelompok_Bank",
                "Kategori_Pinjaman",
                "Sektor_KBLI",
                "Nilai_Kredit_Miliar_Rp",
            ]
        ]
        list_df_clean.append(df_clean)

    if not list_df_clean:
        return []

    df_final = pd.concat(list_df_clean, ignore_index=True)
    print(f"[*] Parsing SEKI BI selesai: {len(df_final)} baris bersih siap di-UPSERT.")
    return df_final.to_dict("records")


def scrape_bi_seki(lookback_months: int = 4) -> list[dict]:
    """Wrapper utama untuk dipanggil langsung oleh ingest_bi_seki.py."""
    xls_bytes, bulan_rilis, tahun_rilis = download_latest_seki_excel(lookback_months=lookback_months)
    print(f"[*] Memproses rilis SEKI {bulan_rilis} {tahun_rilis}...")
    return parse_seki_excel(xls_bytes, tahun_rilis=tahun_rilis)


if __name__ == "__main__":
    rows = scrape_bi_seki(lookback_months=4)
    print(f"Ringkasan tes -> {len(rows)} baris SEKI BI.")