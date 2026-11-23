import csv
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. KONFIGURASI
# ==========================================

BASE_URL = "https://jobnesia.id"
SEARCH_URL = f"{BASE_URL}/jobs/"

KEYWORDS = [""]

LOCATION = ""  # Kosongkan untuk semua lokasi
# Lokasi utama project sector-growth-pipeline
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "raw_data", "jobportal")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "jobnesia_jobs.csv")

MAX_SEARCH_PAGES = 30       # Maksimal halaman per keyword
MAX_DETAIL_PAGES = 1000      # Maksimal detail lowongan unik
REQUEST_DELAY = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AcademicResearch/1.0)"
}

session = requests.Session()
session.headers.update(HEADERS)


# ==========================================
# 2. REQUEST HTML
# ==========================================

def get_soup(url, params=None):
    try:
        response = session.get(url, params=params, timeout=20)
        print("URL:", response.url)
        print("Status:", response.status_code)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as error:
        print("Gagal mengambil halaman:", error)
        return None


# ==========================================
# 3. LINK LOWONGAN DAN PAGINATION
# ==========================================

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def get_job_links(soup):
    links = []

    for tag in soup.find_all("a", href=True):
        url = normalize_url(urljoin(BASE_URL, tag["href"]))
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        if parsed.netloc != urlparse(BASE_URL).netloc:
            continue
        if not path.startswith("/jobs/"):
            continue
        if path == "/jobs" or re.match(r"^/jobs/page/\d+$", path):
            continue
        if url not in links:
            links.append(url)

    return links


def get_next_page_url(soup, current_url, keyword):
    next_link = None

    # Cari tombol halaman berikutnya
    for tag in soup.find_all("a", href=True):
        label = tag.get_text(" ", strip=True).lower()
        aria = tag.get("aria-label", "").lower()
        rel = tag.get("rel", [])

        if isinstance(rel, str):
            rel = [rel]

        if (
            "next" in rel
            or "berikutnya" in label
            or "selanjutnya" in label
            or "next" in label
            or "next" in aria
        ):
            next_link = tag
            break

    if not next_link:
        return None

    next_url = urljoin(current_url, next_link["href"])
    parsed = urlparse(next_url)

    if parsed.netloc != urlparse(BASE_URL).netloc:
        return None

    query = parse_qs(parsed.query)
    query["q"] = [keyword]

    if LOCATION:
        query["location"] = [LOCATION]

    return urlunparse(
        parsed._replace(query=urlencode(query, doseq=True))
    )


def collect_all_job_links():
    jobs_by_url = {}

    print("\n=== MENGUMPULKAN SELURUH LINK LOWONGAN ===")

    visited_pages = set()
    current_url = SEARCH_URL
    params = {}

    if LOCATION:
        params["location"] = LOCATION

    for page in range(1, MAX_SEARCH_PAGES + 1):
        print(f"\n--- Halaman pencarian {page} ---")

        if current_url in visited_pages:
            print("Halaman sudah pernah dikunjungi.")
            break

        visited_pages.add(current_url)

        soup = get_soup(
            current_url,
            params=params if page == 1 else None
        )

        if soup is None:
            print("Halaman gagal diakses.")
            break

        page_links = get_job_links(soup)
        new_count = 0

        for job_url in page_links:
            if job_url not in jobs_by_url:
                jobs_by_url[job_url] = set()
                new_count += 1

        print("Link ditemukan:", len(page_links))
        print("Link unik baru:", new_count)
        print("Total link unik:", len(jobs_by_url))

        next_url = get_next_page_url(
            soup,
            current_url,
            ""
        )

        if not next_url:
            print("Halaman terakhir tercapai.")
            break

        current_url = next_url
        time.sleep(REQUEST_DELAY)

    print("\n=== PENGUMPULAN SELESAI ===")
    print("Total halaman dikunjungi:", len(visited_pages))
    print("Total link lowongan unik:", len(jobs_by_url))

    return jobs_by_url

# ==========================================
# 4. EKSTRAK DATA JSON-LD
# ==========================================

def extract_job_schema(soup):
    def find_job_posting(data):
        if isinstance(data, list):
            for item in data:
                result = find_job_posting(item)
                if result:
                    return result

        elif isinstance(data, dict):
            schema_type = data.get("@type", [])
            if isinstance(schema_type, str):
                schema_type = [schema_type]

            if "JobPosting" in schema_type:
                return data

            if "@graph" in data:
                return find_job_posting(data["@graph"])

        return {}

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text())
            result = find_job_posting(data)
            if result:
                return result
        except (json.JSONDecodeError, TypeError):
            continue

    return {}


# ==========================================
# 5. KLASIFIKASI SEKTOR DAN RELEVANSI
# ==========================================

def classify_sector(company):
    # Gunakan nama perusahaan agar kata di deskripsi tidak memicu
    # klasifikasi sektor yang keliru.
    company_text = (company or "").lower()

    company_rules = [
        ("Insurance", ["insurance", "asuransi"]),
        ("Financial Services", ["finance", "financial", "pembiayaan"]),
        ("Banking", ["bank "]),
        ("Agribusiness", ["pt smart,tbk", "pt smart tbk", "sinar mas agribusiness"]),
        ("Food & Beverage", ["indofood", "mayora", "ultrajaya"]),
        ("Healthcare", ["rumah sakit", "healthcare", "klinik"]),
        ("Telecommunications", ["telkom", "telekomunikasi"]),
        ("Logistics", ["logistics", "logistik"]),
        ("Information Technology", ["technology", "teknologi", "software"]),
    ]

    for sector, keywords in company_rules:
        if any(keyword in company_text for keyword in keywords):
            return sector

    return "Other / Unclassified"


def normalize_text(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def assess_relevance(job_title, matched_keywords):
    """
    Menilai relevansi berdasarkan judul posisi, bukan keyword pencarian saja.
    Semua data tetap disimpan; status hanya membantu proses review.
    """
    title = normalize_text(job_title)

    relevant_patterns = [
        r"\bdata analyst\b",
        r"\bdata engineer\b",
        r"\bdata scientist\b",
        r"\bbusiness analyst\b",
        r"\bbusiness reporting analyst\b",
        r"\bbi analyst\b",
        r"\bbusiness intelligence analyst\b",
        r"\bsystem analyst\b",
        r"\bit analyst\b",
        r"\bproduct analyst\b",
        r"\bdata insight specialist\b",
        r"\bsoftware engineer\b",
        r"\bbackend engineer\b",
        r"\bback end engineer\b",
        r"\bfrontend engineer\b",
        r"\bfront end engineer\b",
        r"\bdeveloper\b",
        r"\bprogrammer\b",
        r"\bproduct manager\b",
        r"\btechnical staff\b",
    ]

    review_patterns = [
        r"\banalyst\b",
        r"\bengineer\b",
        r"\bengineering\b",
        r"\binformation technology\b",
        r"\btechnology\b",
        r"\btechnical\b",
        r"\berp\b",
        r"\bbi\b",
    ]

    if any(re.search(pattern, title) for pattern in relevant_patterns):
        return "Relevant"
    if any(re.search(pattern, title) for pattern in review_patterns):
        return "Review"
    return "Not Relevant"



# ==========================================
# 6. EKSTRAK WORK MODE
# ==========================================

def extract_work_mode(schema, description):
    location_type = str(schema.get("jobLocationType", "")).upper()

    if "TELECOMMUTE" in location_type:
        return "Remote"

    text = (description or "").lower()

    if re.search(r"\b(on[\s-]?site|onsite|work from office|wfo)\b", text):
        return "On-site"
    if re.search(r"\b(hybrid|hibrid)\b", text):
        return "Hybrid"
    if re.search(r"\b(remote|work from home|wfh)\b", text):
        return "Remote"

    return ""


# ==========================================
# 7. EKSTRAK DETAIL LOWONGAN
# ==========================================
def extract_salary(schema, soup):
    # Ambil gaji dari JSON-LD jika tersedia
    salary_data = schema.get("baseSalary", {})

    if isinstance(salary_data, dict):
        currency = salary_data.get("currency", "IDR")
        value = salary_data.get("value", {})

        if isinstance(value, dict):
            minimum = value.get("minValue")
            maximum = value.get("maxValue")
            amount = value.get("value")
            unit = value.get("unitText", "")

            if minimum and maximum:
                return f"{currency} {minimum} - {maximum} {unit}".strip()

            if amount:
                return f"{currency} {amount} {unit}".strip()

            if minimum:
                return f"{currency} {minimum} {unit}".strip()

        elif value:
            return f"{currency} {value}".strip()

    # Jika JSON-LD tidak menyediakan gaji,
    # cari nominal pada teks halaman lowongan.
    page_text = soup.get_text(" ", strip=True)

    salary_pattern = (
        r"(?:Rp\.?\s*|IDR\s*)"
        r"\d[\d.,]*"
        r"(?:\s*(?:-|–|sampai|hingga)\s*"
        r"(?:Rp\.?\s*|IDR\s*)?\d[\d.,]*)?"
        r"(?:\s*/\s*(?:bulan|bln|month|tahun|year))?"
    )

    # Utamakan nominal yang berada dekat label gaji.
    salary_context = re.search(
        r"(?:gaji|salary|upah|remunerasi|kompensasi)"
        r"[^.;]{0,120}",
        page_text,
        re.IGNORECASE
    )

    if salary_context:
        amounts = re.findall(
            salary_pattern,
            salary_context.group(0),
            re.IGNORECASE
        )

        if amounts:
            return " ".join(amounts).strip()

    # Periksa nominal dengan format Rupiah di halaman.
    amounts = re.findall(
        salary_pattern,
        page_text,
        re.IGNORECASE
    )

    if amounts:
        return amounts[0].strip()

    return "Perusahaan tidak menampilkan gaji"


def extract_job_detail(job_url, matched_keywords):
    soup = get_soup(job_url)
    if soup is None:
        return None

    schema = extract_job_schema(soup)

    title_tag = soup.find("h1")
    job_title = schema.get("title") or (
        title_tag.get_text(" ", strip=True) if title_tag else ""
    )

    company_data = schema.get("hiringOrganization", {})
    company = (
        company_data.get("name", "")
        if isinstance(company_data, dict) else ""
    )

    location_data = schema.get("jobLocation", {})
    if isinstance(location_data, list):
        location_data = location_data[0] if location_data else {}

    location = ""
    if isinstance(location_data, dict):
        address = location_data.get("address", {})
        if isinstance(address, dict):
            location = ", ".join(
                str(address[field])
                for field in (
                    "addressLocality",
                    "addressRegion",
                    "addressCountry"
                )
                if address.get(field)
            )

    description_html = schema.get("description", "")
    description = (
        BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
        if description_html else ""
    )

    salary = extract_salary(schema, soup)

    employment_type = schema.get("employmentType", "")
    if isinstance(employment_type, list):
        employment_type = ", ".join(employment_type)

    posting_date = schema.get("datePosted", "")
    work_mode = extract_work_mode(schema, description)

    return {
        "job_title": job_title,
        "company": company,
        "sector": classify_sector(company),
        "location": location,
        "salary": salary,
        "employment_type": employment_type,
        "work_mode": work_mode,
        "posting_date": posting_date,
        "description": description,
        "job_url": job_url,
        "source": "Jobnesia",
    }

# ==========================================
# 8. TAMPILKAN HASIL DI TERMINAL
# ==========================================

def display_job_details(df):
    print("\n" + "=" * 70)
    print("             DETAIL HASIL SCRAPING JOBNESIA")
    print("=" * 70)

    for index, row in df.iterrows():
        print(f"\nLOWONGAN {index + 1}")
        print("-" * 70)
        print(f"Keyword cocok   : {row['matched_keywords'] or 'Tidak tersedia'}")
        print(f"Relevansi       : {row['relevance_status']}")
        print(f"Perusahaan      : {row['company'] or 'Tidak tersedia'}")
        print(f"Posisi          : {row['job_title'] or 'Tidak tersedia'}")
        print(f"Sektor          : {row['sector'] or 'Tidak tersedia'}")
        print(f"Lokasi          : {row['location'] or 'Tidak tersedia'}")
        print(f"Gaji            : {row['salary'] or 'Tidak tersedia'}")
        print(f"Tipe pekerjaan  : {row['employment_type'] or 'Tidak tersedia'}")
        print(f"Work mode       : {row['work_mode'] or 'Tidak tersedia'}")
        print(f"Tanggal posting : {row['posting_date'] or 'Tidak tersedia'}")

        description = row["description"]
        print("\nDeskripsi:")
        print(
            description[:500]
            if isinstance(description, str) and description
            else "Tidak tersedia"
        )
        if isinstance(description, str) and len(description) > 500:
            print("... (deskripsi dipotong di terminal)")

        print("\nLink lowongan:")
        print(row["job_url"])

    print("\n" + "=" * 70)
    print(f"TOTAL LOWONGAN: {len(df)}")
    print("=" * 70)


# ==========================================
# 9. SIMPAN CSV
# ==========================================

def save_results(df):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    export_df = df.copy()

    for column in export_df.select_dtypes(include="object").columns:
        export_df[column] = export_df[column].apply(
            lambda value: " ".join(value.split())
            if isinstance(value, str) else value
        )

    try:
        export_df.to_csv(
            OUTPUT_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig",
            quoting=csv.QUOTE_ALL
        )
        output_path = OUTPUT_FILE

    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            OUTPUT_DIR,
            f"jobnesia_jobs_{timestamp}.csv"
        )
        export_df.to_csv(
            output_path,
            index=False,
            sep=";",
            encoding="utf-8-sig",
            quoting=csv.QUOTE_ALL
        )
        print("CSV utama sedang terkunci. Menggunakan nama file alternatif.")

    print("\nCSV berhasil disimpan:", output_path)
    return export_df, output_path


# ==========================================
# 10. PROSES UTAMA
# ==========================================

def main():
    print("\n=== JOBNESIA MULTI-KEYWORD SCRAPING ===\n")
    print("Daftar keyword:")
    for keyword in KEYWORDS:
        print("-", keyword)

    print("Location:", LOCATION if LOCATION else "Semua lokasi")
    print("Maksimal halaman per keyword:", MAX_SEARCH_PAGES)
    print("Maksimal detail lowongan unik:", MAX_DETAIL_PAGES)
    print(
        "\nCatatan: proses dibatasi dan diberi jeda. "
        "Pastikan penggunaan otomatis telah diizinkan oleh situs."
    )

    jobs_by_url = collect_all_job_links()

    print("\n=== TOTAL LINK LOWONGAN ===")
    print("Total link unik:", len(jobs_by_url))

    if not jobs_by_url:
        print("Tidak ada link lowongan ditemukan.")
        return

    selected_jobs = list(jobs_by_url.items())[:MAX_DETAIL_PAGES]
    job_data = []

    print("\n=== MENGAMBIL DETAIL LOWONGAN ===")

    for index, (job_url, matched_keywords) in enumerate(selected_jobs, start=1):
        print(f"\nLowongan {index}/{len(selected_jobs)}")

        try:
            result = extract_job_detail(job_url, matched_keywords)
            if result:
                job_data.append(result)
        except Exception as error:
            print("Gagal mengambil detail:", error)

        if index < len(selected_jobs):
            time.sleep(REQUEST_DELAY)

    if not job_data:
        print("\nBelum ada data yang berhasil diekstrak.")
        return

    df = pd.DataFrame(job_data)
    export_df, output_path = save_results(df)

    print("\n=== RINGKASAN HASIL SCRAPING ===")
    print("Jumlah keyword:", len(KEYWORDS))
    print("Total link unik ditemukan:", len(jobs_by_url))
    print("Total detail berhasil diambil:", len(export_df))
    print("Status relevansi:")
    if "relevance_status" in export_df.columns:
        print(
            export_df["relevance_status"]
            .value_counts(dropna=False)
            .to_string()
        )
    else:
        print("Kolom relevance_status tidak ditemukan.")
        print("File CSV:", output_path)

    display_job_details(export_df)


if __name__ == "__main__":
    main()