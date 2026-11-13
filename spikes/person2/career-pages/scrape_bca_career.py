
import csv
import re
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# KONFIGURASI
# ============================================================

BASE_URL = "https://karir.bca.co.id"
LIST_URL = f"{BASE_URL}/candidate/id/career"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "raw_data" / "careerpages"
OUTPUT_FILE = OUTPUT_DIR / "bca_jobs.csv"

DELAY = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": LIST_URL
}

FIELDS = [
    "job_title",
    "company",
    "sector",
    "location",
    "test_location",
    "placement_location",
    "date_posted",
    "application_period",
    "deadline",
    "employment_type",
    "category",
    "description",
    "requirements",
    "selection_stages",
    "additional_information",
    "skills",
    "job_url",
    "source",
    "scraped_at"
]

SECTION_NAMES = [
    "Tentang Pekerjaan",
    "Persyaratan",
    "Tahapan Seleksi",
    "Lokasi Tes",
    "Lokasi Penempatan",
    "Informasi Tambahan"
]

MONTHS = (
    "Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|"
    "September|Oktober|November|Desember"
)

DATE_PATTERN = (
    rf"\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}}"
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{4}"
)


# ============================================================
# FUNGSI BANTU
# ============================================================

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_page(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_lines(soup):
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return [
        clean_text(line)
        for line in soup.get_text("\n").splitlines()
        if clean_text(line)
    ]


def extract_title(soup):
    for tag in ["h1", "h2"]:
        element = soup.find(tag)
        if element:
            return clean_text(element.get_text(" ", strip=True))
    return ""


def extract_section(lines, section_name):
    target = section_name.lower()
    start = None

    for i, line in enumerate(lines):
        if line.lower().strip() == target:
            start = i + 1
            break

    if start is None:
        return ""

    result = []

    for line in lines[start:]:
        if line.lower().strip() in [
            name.lower() for name in SECTION_NAMES
        ]:
            break

        result.append(line)

    return " | ".join(result)


# ============================================================
# EKSTRAKSI METADATA BAGIAN ATAS HALAMAN
# ============================================================

def extract_header_metadata(lines, title):
    category = ""
    employment_type = ""
    application_period = ""

    title_index = None

    for i, line in enumerate(lines):
        if line.lower() == title.lower():
            title_index = i
            break

    if title_index is None:
        return category, employment_type, application_period

    # Informasi metadata berada setelah judul
    # dan sebelum bagian Tentang Pekerjaan.
    metadata_lines = []

    for line in lines[title_index + 1:]:
        if line.lower().strip() in [
            name.lower() for name in SECTION_NAMES
        ]:
            break

        if line not in ["•", "-", "|", "Share", "Daftar"]:
            metadata_lines.append(line)

    for line in metadata_lines:
        normalized = line.strip()

        # Kategori
        if normalized.lower() in [
            "fresh graduate",
            "experienced"
        ]:
            category = normalized

        # Jenis pekerjaan
        elif normalized.lower() in [
            "program trainee",
            "permanent",
            "contract",
            "internship",
            "full time",
            "part time"
        ]:
            employment_type = normalized

    # Cari periode berdasarkan rentang tanggal
    for line in metadata_lines:
        dates = re.findall(
            DATE_PATTERN,
            line,
            re.IGNORECASE
        )

        if len(dates) >= 2:
            application_period = f"{dates[0]} - {dates[1]}"
            break

    return category, employment_type, application_period


def extract_skills(text):
    keywords = [
        "communication",
        "analytical thinking",
        "problem solving",
        "leadership",
        "teamwork",
        "interpersonal",
        "english",
        "microsoft excel",
        "microsoft office",
        "python",
        "sql",
        "data analysis",
        "programming",
        "critical thinking"
    ]

    found = []

    for keyword in keywords:
        if re.search(re.escape(keyword), text, re.IGNORECASE):
            found.append(keyword.title())

    return ", ".join(found)


# ============================================================
# TAHAP 1 - SCRAPING DAFTAR LOWONGAN
# ============================================================

def scrape_job_links(session):
    print("\n" + "=" * 75)
    print("TAHAP 1 - MENGAMBIL DAFTAR LOWONGAN")
    print("=" * 75)

    soup = get_page(session, LIST_URL)

    links = []

    for anchor in soup.find_all("a", href=True):
        url = urljoin(BASE_URL, anchor["href"]).split("#")[0]

        if "/candidate/id/career/" not in url:
            continue

        if url.rstrip("/") == LIST_URL.rstrip("/"):
            continue

        if url not in links:
            links.append(url)

    print("Halaman sumber :", LIST_URL)
    print("Link unik      :", len(links))

    return links


# ============================================================
# TAHAP 2 - SCRAPING DETAIL LOWONGAN
# ============================================================

def scrape_job_detail(session, url):
    soup = get_page(session, url)
    lines = get_lines(soup)

    title = extract_title(soup)

    description = extract_section(
        lines, "Tentang Pekerjaan"
    )

    requirements = extract_section(
        lines, "Persyaratan"
    )

    selection = extract_section(
        lines, "Tahapan Seleksi"
    )

    test_location = extract_section(
        lines, "Lokasi Tes"
    )

    placement = extract_section(
        lines, "Lokasi Penempatan"
    )

    additional = extract_section(
        lines, "Informasi Tambahan"
    )

    category, employment_type, application_period = (
        extract_header_metadata(lines, title)
    )

    # Deadline diambil dari tanggal akhir periode.
    deadline = ""

    if application_period:
        dates = re.findall(
            DATE_PATTERN,
            application_period,
            re.IGNORECASE
        )

        if len(dates) >= 2:
            deadline = dates[-1]

    # Tidak ditemukan tanggal publikasi pada
    # struktur halaman yang telah diperiksa.
    date_posted = ""

    combined_text = description + " " + requirements

    return {
        "job_title": title,
        "company": "PT Bank Central Asia Tbk",
        "sector": "Perbankan",
        "location": placement,
        "test_location": test_location,
        "placement_location": placement,
        "date_posted": date_posted,
        "application_period": application_period,
        "deadline": deadline,
        "employment_type": employment_type,
        "category": category,
        "description": description,
        "requirements": requirements,
        "selection_stages": selection,
        "additional_information": additional,
        "skills": extract_skills(combined_text),
        "job_url": url,
        "source": "BCA Career",
        "scraped_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }


# ============================================================
# TAHAP 3 - VALIDASI DAN SIMPAN CSV
# ============================================================

def main():
    print("=" * 75)
    print("BCA CAREER SCRAPER")
    print("=" * 75)

    print("Project root :", PROJECT_ROOT)
    print("Output       :", OUTPUT_FILE)
    print("Delimiter    : ';'")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    results = []
    failed = []

    try:
        links = scrape_job_links(session)

        if not links:
            print("Tidak ditemukan lowongan.")
            return

        print("\n" + "=" * 75)
        print("TAHAP 2 - SCRAPING DETAIL LOWONGAN")
        print("=" * 75)

        for index, url in enumerate(links, 1):
            print(f"\n[{index}/{len(links)}] {url}")

            try:
                data = scrape_job_detail(session, url)
                results.append(data)

                print("Judul           :", data["job_title"])
                print("Kategori        :", data["category"] or "(tidak ditemukan)")
                print("Jenis pekerjaan :", data["employment_type"] or "(tidak ditemukan)")
                print("Periode         :", data["application_period"] or "(tidak ditemukan)")
                print("Deadline        :", data["deadline"] or "(tidak ditemukan)")
                print("Deskripsi       :", bool(data["description"]))
                print("Persyaratan     :", bool(data["requirements"]))

            except Exception as error:
                failed.append((url, str(error)))
                print("GAGAL:", error)

            time.sleep(DELAY)

        # Simpan CSV
        with open(
            OUTPUT_FILE,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS,
                delimiter=";"
            )

            writer.writeheader()
            writer.writerows(results)

        # Validasi jumlah kolom
        print("\n" + "=" * 75)
        print("TAHAP 3 - KELENGKAPAN DATA")
        print("=" * 75)

        print("Lowongan ditemukan :", len(links))
        print("Detail tersimpan   :", len(results))
        print("Gagal              :", len(failed))

        for field in FIELDS:
            filled = sum(
                1 for row in results if row.get(field)
            )

            print(f"{field:25}: {filled}/{len(results)}")

        print("\nCSV:", OUTPUT_FILE)
        print("=" * 75)
        print("SCRAPING SELESAI")

    except requests.RequestException as error:
        print("Gagal mengakses halaman:", error)


if __name__ == "__main__":
    main()
