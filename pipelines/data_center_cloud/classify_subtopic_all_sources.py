
import pandas as pd
from pathlib import Path
import re

# ==========================================
# KONFIGURASI FILE
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

SOURCES = {
    "ANTARA": {
        "input": "data_center_antaranews_business_insight.csv",
        "output": "data_center_antaranews_with_subtopic.csv",
    },
    "KATADATA": {
        "input": "data_center_katadata_business_insight.csv",
        "output": "data_center_katadata_with_subtopic.csv",
    },
    "KOMPAS": {
        "input": "data_center_kompas_business_insight.csv",
        "output": "data_center_kompas_with_subtopic.csv",
    },
}


# ==========================================
# HELPER
# ==========================================

def clean_text(value):
    if pd.isna(value):
        return ""

    return re.sub(r"\s+", " ", str(value)).strip().lower()


def contains_keyword(text, keywords):
    return any(keyword in text for keyword in keywords)


# ==========================================
# KLASIFIKASI SUBTOPIC
# ==========================================

def determine_subtopic(row):
    title = clean_text(row.get("title", ""))
    summary = clean_text(row.get("summary", ""))

    # Mendukung format ANTARA maupun Katadata/KOMPAS
    content = clean_text(row.get("content_clean", ""))

    if not content:
        content = clean_text(row.get("content", ""))

    primary_text = f"{title} {summary}"
    full_text = f"{primary_text} {content}"

    # 1. Transfer Teknologi
    if contains_keyword(primary_text, [
        "transfer teknologi",
        "alih teknologi",
        "peningkatan kompetensi sdm",
        "kemampuan nasional",
        "tenaga kerja lokal",
    ]):
        return "Transfer Teknologi"

    # 2. Konektivitas Digital
    if contains_keyword(primary_text, [
        "konektivitas digital",
        "konektivitas jaringan",
        "jaringan telekomunikasi",
        "konektivitas internet",
    ]):
        return "Konektivitas Digital"

    # 3. Teknologi Pendinginan
    if contains_keyword(primary_text, [
        "liquid cooling",
        "pendingin cair",
        "direct to chip",
        "teknologi pendinginan",
        "sistem pendingin",
    ]):
        return "Teknologi Pendinginan"

    # 4. Kebutuhan Energi
    if contains_keyword(primary_text, [
        "kebutuhan listrik",
        "pasokan listrik",
        "pasok listrik",
        "suplai listrik",
        "daya listrik",
        "panas bumi",
        "geothermal",
        "energi terbarukan",
        "green data center",
        "krisis listrik",
        "boros listrik",
        "pasokan energi",
        "kebutuhan energi",
        "megawatt",
        "gigawatt",
        "mva",
        "listrik baseload",
    ]):
        return "Kebutuhan Energi"

    # 5. Infrastruktur AI
    if contains_keyword(primary_text, [
        "infrastruktur ai",
        "ai data center",
        "data center ai",
        "ai factory",
        "gpu",
        "komputasi ai",
        "chip ai",
        "chip semikonduktor",
        "infrastruktur kecerdasan buatan",
        "pusat data ai",
    ]):
        return "Infrastruktur AI"

    # Isi artikel dipakai sebagai fallback apabila judul
    # dan ringkasan belum menunjukkan kategori yang spesifik.
    if contains_keyword(primary_text, [
        "data center",
        "pusat data",
    ]):
        if contains_keyword(full_text, [
            "ai factory",
            "infrastruktur ai",
            "gpu untuk ai",
            "komputasi ai",
            "infrastruktur kecerdasan buatan",
        ]):
            return "Infrastruktur AI"

    # 6. Cloud Computing
    if contains_keyword(primary_text, [
        "cloud computing",
        "layanan cloud",
        "cloud service",
        "komputasi awan",
        "cloud provider",
        "penyedia cloud",
    ]):
        return "Cloud Computing"

    # 7. Regulasi dan Perizinan
    if contains_keyword(primary_text, [
        "perizinan",
        "izin pembangunan",
        "izin proyek",
        "regulasi",
        "kebijakan pemerintah",
        "aturan pemerintah",
        "moratorium",
        "rekomendasi kebijakan",
        "amdal",
        "persetujuan lingkungan",
    ]):
        return "Regulasi dan Perizinan"

    # 8. Investasi dan Pendanaan
    if contains_keyword(primary_text, [
        "investasi",
        "investor",
        "pendanaan",
        "funding",
        "danantara",
        "peluang investasi",
        "minat investor",
        "suntikan dana",
        "modal proyek",
        "pembelian saham",
        "foreign direct investment",
        "penanaman modal",
    ]):
        return "Investasi dan Pendanaan"

    # 9. Infrastruktur Data Center
    if contains_keyword(full_text, [
        "data center",
        "pusat data",
    ]):
        return "Infrastruktur Data Center"

    # 10. Kategori cadangan
    return "Lainnya"


# ==========================================
# PROSES SEMUA SUMBER
# ==========================================

def main():
    print("=" * 50)
    print("KLASIFIKASI SUBTOPIC SEMUA SUMBER")
    print("=" * 50)

    for source, config in SOURCES.items():
        input_path = BASE_DIR / config["input"]
        output_path = BASE_DIR / config["output"]

        if not input_path.exists():
            print(f"\n[LEWATI] {source}: file tidak ditemukan")
            print(f"File: {input_path}")
            continue

        try:
            df = pd.read_csv(input_path)

            if "title" not in df.columns:
                print(f"\n[LEWATI] {source}: kolom title tidak ditemukan")
                continue

            # Klasifikasi ulang ke kolom baru.
            # File input tidak ditimpa.
            df["subtopic"] = df.apply(determine_subtopic, axis=1)

            df.to_csv(output_path, index=False, encoding="utf-8-sig")

            print(f"\nSumber: {source}")
            print(f"Jumlah artikel: {len(df)}")
            print("Distribusi subtopic:")
            print(df["subtopic"].value_counts(dropna=False).to_string())
            print(f"Output: {output_path.name}")

        except Exception as error:
            print(f"\n[ERROR] {source}: {error}")

    print("\n" + "=" * 50)
    print("PROSES SELESAI")
    print("=" * 50)


if __name__ == "__main__":
    main()
