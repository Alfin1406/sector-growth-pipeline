
import requests
import csv
import re
from bs4 import BeautifulSoup, Comment
from pathlib import Path
from datetime import datetime

# ==========================================================
# KONFIGURASI
# ==========================================================

URL = "https://www.bankmandiri.co.id/mandiri-career"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "raw_data" / "careerpages"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "mandiri_jobs.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

PANEL_CATEGORY = {
    "karir-faq-1": "Officer Development Program",
    "karir-faq-2": "Banking Staff",
    "karir-faq-3": "Experienced Hire",
    "karir-faq-4": "Kriya Mandiri",
    "karir-faq-5": "Job at Bank Mandiri Subsidiaries",
    "karir-faq-6": "CPDK",
    "karir-faq-7": "Mandiri Internship Program",
}

TAB_LOCATION = {
    "tab2-1": "Head Office",
    "tab2-2": "Sumatera",
    "tab2-3": "Jabodetabek",
    "tab2-4": "Jawa",
    "tab2-5": "Kalimantan",
    "tab2-6": "Sulawesi & Maluku",
    "tab2-7": "Bali & Nusa Tenggara",
    "tab2-8": "Papua",
    "tab3-1": "Corporate Banking",
    "tab3-2": "Information Technology",
    "tab3-3": "Keuangan dan Strategi",
    "tab3-4": "Hubungan Kelembagaan",
    "tab3-5": "Jaringan & Retail Banking",
    "tab4-1": "Nasional",
    "tab4-2": "IT",
    "tab4-3": "Sumatera",
    "tab4-4": "Jabodetabek",
    "tab4-5": "Jawa",
    "tab4-6": "Kalimantan",
    "tab4-7": "Sulawesi & Maluku",
    "tab4-8": "Bali & Nusa Tenggara",
    "tab4-9": "Papua",
    "tab5-1": "Mandiri Tunas Finance",
    "tab6-1": "Nasional",
    "tab7-1": "Nasional",
}

# ==========================================================
# TAHAP 1 - AKSES HALAMAN
# ==========================================================

print("=" * 65)
print("SCRAPING CAREER PAGE BANK MANDIRI")
print("=" * 65)

print("\n[TAHAP 1] Mengakses halaman...")

response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

print(f"HTTP Status : {response.status_code}")
print("Halaman berhasil diakses.")

# ==========================================================
# TAHAP 2 - EKSTRAKSI KARTU LOWONGAN
# ==========================================================

print("\n[TAHAP 2] Mengekstrak kartu lowongan...")

# Hanya mengambil kartu yang benar-benar berada
# di dalam daftar pekerjaan.
cards = soup.select(".ag-job-list .ag-card")

print(f"Kartu lowongan ditemukan: {len(cards)}")

records = []
seen = set()

for index, card in enumerate(cards, 1):

    title_element = card.select_one(".ag-card__title")
    status_element = card.select_one(".ag-card__status")

    if not title_element:
        continue

    job_title = title_element.get_text(" ", strip=True)

    status = (
        status_element.get_text(" ", strip=True)
        if status_element else ""
    )

    # Cari kategori dari panel induk
    panel = card.find_parent(
        "div",
        class_="ag-panel-collapse"
    )

    panel_id = panel.get("id", "") if panel else ""

    category = PANEL_CATEGORY.get(panel_id, "")

    # Cari tab lokasi atau subkategori
    tab = card.find_parent("div", class_="tab-pane")
    tab_id = tab.get("id", "") if tab else ""

    location = TAB_LOCATION.get(tab_id, "")

    # Koreksi struktur HTML Mandiri Internship
    if panel_id == "karir-faq-7":
        category = "Mandiri Internship Program"
        location = "Nasional"

    # Koreksi kategori anak perusahaan
    company = (
        "Mandiri Tunas Finance"
        if panel_id == "karir-faq-5"
        else "Bank Mandiri"
    )

    # Ambil deskripsi program dari panel
    description = ""

    if panel:
        description_element = panel.find("p")

        if description_element:
            description = description_element.get_text(
                " ", strip=True
            )

    # Ambil URL dari komentar HTML
    application_url = ""

    for item in card.descendants:
        if isinstance(item, Comment):
            match = re.search(
                r'href=["\'](https?://[^"\']+)["\']',
                str(item)
            )

            if match:
                application_url = match.group(1)
                break

    # Hilangkan duplikasi berdasarkan posisi, kategori,
    # lokasi dan perusahaan.
    key = (
        job_title.lower(),
        category.lower(),
        location.lower(),
        company.lower()
    )

    if key in seen:
        continue

    seen.add(key)

    records.append({
        "job_title": job_title,
        "company": company,
        "sector": "Perbankan",
        "location": location,
        "date_posted": "",
        "skills": "",
        "description": description,
        "employment_type": "",
        "education": "",
        "experience": "",
        "deadline": "",
        "category": category,
        "status": status,
        "application_url": application_url,
        "job_url": URL,
        "source": "Bank Mandiri Career",
        "scraped_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    })

    print(
        f"[{len(records)}] {job_title} | "
        f"{category} | {location} | {status}"
    )

# ==========================================================
# TAHAP 3 - SIMPAN CSV
# ==========================================================

print("\n[TAHAP 3] Menyimpan CSV...")

fieldnames = [
    "job_title",
    "company",
    "sector",
    "location",
    "date_posted",
    "skills",
    "description",
    "employment_type",
    "education",
    "experience",
    "deadline",
    "category",
    "status",
    "application_url",
    "job_url",
    "source",
    "scraped_at"
]

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
        delimiter=";"
    )

    writer.writeheader()
    writer.writerows(records)

# ==========================================================
# TAHAP 4 - VALIDASI DATA
# ==========================================================

print("\n[TAHAP 4] Validasi kelengkapan kolom...")

print("\nKelengkapan setiap kolom:")

for field in fieldnames:
    filled = sum(
        1 for row in records
        if str(row[field]).strip()
    )

    print(
        f"{field:20} : {filled}/{len(records)}"
    )

closed = sum(
    1 for row in records
    if row["status"].upper() == "CLOSED"
)

print("\n" + "=" * 65)
print("RINGKASAN SCRAPING BANK MANDIRI")
print("=" * 65)

print(f"Jumlah kartu HTML : {len(cards)}")
print(f"Data unik         : {len(records)}")
print(f"Status CLOSED    : {closed}")
print(f"Status lainnya   : {len(records) - closed}")
print(
    "URL pendaftaran  :",
    sum(bool(row["application_url"]) for row in records)
)
print(f"Output            : {OUTPUT_FILE}")

print("\nScraping selesai.")
