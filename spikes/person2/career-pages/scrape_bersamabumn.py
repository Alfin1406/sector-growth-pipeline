"""
BersamaBUMN Career Pages Scraper
--------------------------------
Mengambil lowongan publik dari BersamaBUMN.com menggunakan requests + BeautifulSoup.
Hasil disimpan ke raw_data/careerpages/bersamabumn_jobs.csv

Catatan:
- Portal ini merupakan agregator independen, bukan portal resmi FHCI/RBB.
- Gunakan permintaan secara wajar dan patuhi ketentuan situs.
- Script hanya mengambil informasi lowongan publik, bukan data pelamar.
"""

import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.bersamabumn.com"
START_URL = f"{BASE_URL}/lowongan/"
OUTPUT_DIR = Path("raw_data/careerpages")
OUTPUT_FILE = OUTPUT_DIR / "bersamabumn_jobs.csv"

REQUEST_DELAY = 1.5
TIMEOUT = 30
MAX_LISTING_PAGES = 30  # Batas pengaman; naikkan jika memang diperlukan.

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

CSV_FIELDS = [
    "job_title",
    "company",
    "location",
    "date_posted",
    "deadline",
    "employment_type",
    "education",
    "experience",
    "category",
    "description",
    "job_url",
    "source",
]

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    """Mengambil halaman dan mengembalikan BeautifulSoup."""
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as exc:
        print(f"[ERROR] Gagal mengakses {url}: {exc}")
        return None


def is_job_detail_url(url):
    """
    URL detail lowongan pada hasil pemeriksaan memiliki pola:
    /lowongan/nama-posisi/ID/
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path.startswith("/lowongan/"):
        return False

    excluded_parts = (
        "/posisi/",
        "/lokasi/",
        "/status/",
        "/pendidikan/",
        "/page/",
    )
    if any(part in path for part in excluded_parts):
        return False

    return bool(re.search(r"/\d+$", path))


def get_listing_links(soup):
    """Mengambil URL detail lowongan dari satu halaman arsip."""
    links = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, anchor["href"])
        if urlparse(href).netloc.endswith("bersamabumn.com"):
            if is_job_detail_url(href):
                links.add(href.split("#")[0])

    return links


def get_next_page(soup, current_url):
    """Mencari tautan pagination berikutnya dari HTML."""
    # Prioritas 1: rel=next
    next_anchor = soup.find("a", rel=lambda value: value and "next" in value)
    if next_anchor and next_anchor.get("href"):
        return urljoin(current_url, next_anchor["href"])

    # Prioritas 2: teks tombol pagination
    for anchor in soup.find_all("a", href=True):
        label = anchor.get_text(" ", strip=True).lower()
        if "berikutnya" in label or label in {"next", "next page", "→"}:
            return urljoin(current_url, anchor["href"])

    return None


def walk_jsonld(value):
    """Menelusuri objek JSON-LD, termasuk @graph dan list."""
    if isinstance(value, list):
        for item in value:
            yield from walk_jsonld(item)
    elif isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph:
            yield from walk_jsonld(graph)


def extract_jobposting_objects(soup):
    """Mengambil seluruh objek bertipe JobPosting dari JSON-LD."""
    jobs = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for item in walk_jsonld(data):
            item_type = item.get("@type", [])
            if isinstance(item_type, str):
                item_type = [item_type]

            if "JobPosting" in item_type:
                jobs.append(item)

    return jobs


def clean_html(value):
    """Mengubah deskripsi HTML menjadi teks biasa."""
    if not value:
        return ""

    soup = BeautifulSoup(str(value), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def get_name(value):
    """Mengambil nama dari field yang dapat berupa string atau object."""
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "").strip()

    if isinstance(value, list):
        values = [get_name(item) for item in value]
        return "; ".join(item for item in values if item)

    return ""


def extract_location(job):
    """Mengambil lokasi dari jobLocation JSON-LD."""
    locations = job.get("jobLocation", [])
    if isinstance(locations, dict):
        locations = [locations]

    results = []
    for location in locations or []:
        if not isinstance(location, dict):
            continue

        address = location.get("address", {})
        if isinstance(address, str):
            results.append(address)
            continue

        if isinstance(address, dict):
            parts = [
                address.get("streetAddress"),
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            text = ", ".join(str(part).strip() for part in parts if part)
            if text:
                results.append(text)

    return "; ".join(dict.fromkeys(results))


def extract_education(job):
    value = job.get("educationRequirements")
    if isinstance(value, dict):
        return (
            value.get("credentialCategory")
            or value.get("name")
            or value.get("description")
            or ""
        )
    return get_name(value)


def extract_experience(job):
    value = job.get("experienceRequirements")

    if isinstance(value, dict):
        months = value.get("monthsOfExperience")
        if months is not None:
            try:
                years = float(months) / 12
                if years.is_integer():
                    return f"{int(years)} tahun"
                return f"{years:g} tahun"
            except (TypeError, ValueError):
                pass

        return (
            value.get("description")
            or value.get("monthsOfExperience")
            or ""
        )

    return get_name(value)


def normalize_job(job, page_url):
    organization = job.get("hiringOrganization", {})
    if not isinstance(organization, dict):
        organization = {}

    job_url = job.get("url") or page_url
    if isinstance(job_url, list):
        job_url = job_url[0] if job_url else page_url
    job_url = urljoin(BASE_URL, str(job_url))

    title = job.get("title") or ""
    description = clean_html(job.get("description"))
    category = get_name(job.get("occupationalCategory"))

    return {
        "job_title": str(title).strip(),
        "company": get_name(organization),
        "location": extract_location(job),
        "date_posted": job.get("datePosted", ""),
        "deadline": job.get("validThrough", ""),
        "employment_type": get_name(job.get("employmentType")),
        "education": extract_education(job),
        "experience": extract_experience(job),
        "category": category,
        "description": description,
        "job_url": job_url,
        "source": "BersamaBUMN",
    }


def crawl_listing_pages():
    """Mengumpulkan URL detail dari semua halaman daftar lowongan."""
    all_links = set()
    visited_pages = set()
    current_url = START_URL

    print("\n========== TAHAP 1: DAFTAR LOWONGAN ==========")

    for page_number in range(1, MAX_LISTING_PAGES + 1):
        if not current_url or current_url in visited_pages:
            break

        visited_pages.add(current_url)
        print(f"\n[LISTING] Halaman {page_number}: {current_url}")

        soup = get_soup(current_url)
        if soup is None:
            break

        links = get_listing_links(soup)
        before = len(all_links)
        all_links.update(links)
        added = len(all_links) - before

        print(f"  Link detail ditemukan: {len(links)}")
        print(f"  Link baru: {added}")
        print(f"  Total unik sementara: {len(all_links)}")

        next_url = get_next_page(soup, current_url)
        if not next_url or next_url in visited_pages:
            print("[INFO] Tidak ditemukan halaman berikutnya.")
            break

        current_url = next_url
        time.sleep(REQUEST_DELAY)

    return sorted(all_links)


def scrape_detail_pages(detail_urls):
    """Mengambil seluruh JobPosting dari setiap halaman detail."""
    print("\n========== TAHAP 2: DETAIL LOWONGAN ==========")

    all_jobs = {}
    total_urls = len(detail_urls)

    for index, url in enumerate(detail_urls, start=1):
        print(f"\n[DETAIL {index}/{total_urls}] {url}")

        soup = get_soup(url)
        if soup is None:
            continue

        job_objects = extract_jobposting_objects(soup)
        print(f"  Objek JobPosting ditemukan: {len(job_objects)}")

        for job_object in job_objects:
            row = normalize_job(job_object, url)
            key = row["job_url"] or (
                row["job_title"].lower(),
                row["company"].lower(),
            )

            if isinstance(key, str):
                key = key.rstrip("/").lower()

            if row["job_title"]:
                all_jobs[key] = row

        time.sleep(REQUEST_DELAY)

    return list(all_jobs.values())


def save_csv(rows):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[SELESAI] CSV tersimpan: {OUTPUT_FILE.resolve()}")


def main():
    print("==============================================")
    print(" SCRAPER BERSAMABUMN - CAREER PAGES")
    print("==============================================")
    print(f"URL awal : {START_URL}")
    print(f"Output   : {OUTPUT_FILE}")

    listing_urls = crawl_listing_pages()
    print(f"\n[HASIL] Total URL detail unik: {len(listing_urls)}")

    if not listing_urls:
        print(
            "[PERINGATAN] Tidak ada URL detail yang ditemukan. "
            "Periksa kembali pola URL halaman daftar."
        )
        return

    jobs = scrape_detail_pages(listing_urls)

    # Pengurutan terbaru lebih dahulu jika tanggal tersedia.
    jobs.sort(
        key=lambda row: row.get("date_posted") or "",
        reverse=True,
    )

    save_csv(jobs)

    print("\n========== RINGKASAN ==========")
    print(f"Total halaman detail : {len(listing_urls)}")
    print(f"Total lowongan unik  : {len(jobs)}")
    print(f"Perusahaan terisi    : {sum(bool(x['company']) for x in jobs)}")
    print(f"Lokasi terisi        : {sum(bool(x['location']) for x in jobs)}")
    print(f"Tanggal terisi       : {sum(bool(x['date_posted']) for x in jobs)}")
    print(f"Deskripsi terisi     : {sum(bool(x['description']) for x in jobs)}")
    print(f"File CSV             : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
