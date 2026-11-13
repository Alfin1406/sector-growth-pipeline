
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import time

# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[3]

OUTPUT_DIR = BASE_DIR / "raw_data" / "jobportal"
OUTPUT_FILE = OUTPUT_DIR / "linkedin_jobs.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "JobResearchBot/1.0"
}

TIMEOUT = 20

FIELDNAMES = [
    "job_title",
    "company",
    "sector",
    "location",
    "posting_date",
    "job_description",
    "skills",
    "job_url",
    "source"
]

# Masukkan URL HTML dari sumber yang mengizinkan
# pengambilan data otomatis.
HTML_URLS = []


# ==========================================
# HELPER
# ==========================================

def get_text(element):
    if element:
        return element.get_text(" ", strip=True)
    return ""


# ==========================================
# SCRAPING
# ==========================================

def scrape_job_page(url):

    print(f"\nProcessing: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        print(f"Status: {response.status_code}")

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

        # Selector contoh untuk HTML sumber
        # yang memang mengizinkan scraping.
        cards = soup.select(".job-card")

        if not cards:
            print("Tidak ditemukan elemen job-card.")
            return jobs

        for card in cards:

            title = card.select_one(".job-title")
            company = card.select_one(".company-name")
            sector = card.select_one(".company-sector")
            location = card.select_one(".job-location")
            date = card.select_one("time")
            description = card.select_one(".job-description")
            skills = card.select_one(".job-skills")
            link = card.select_one("a")

            job_url = ""

            if link and link.get("href"):
                job_url = requests.compat.urljoin(
                    url,
                    link.get("href")
                )

            job = {
                "job_title": get_text(title),
                "company": get_text(company),
                "sector": get_text(sector),
                "location": get_text(location),
                "posting_date": (
                    date.get("datetime", "")
                    if date else ""
                ),
                "job_description": get_text(description),
                "skills": get_text(skills),
                "job_url": job_url,
                "source": "LinkedIn"
            }

            if job["job_title"]:
                jobs.append(job)

        print(f"Jobs collected: {len(jobs)}")

        return jobs

    except requests.RequestException as e:
        print(f"Request error: {e}")
        return []


# ==========================================
# SAVE CSV
# ==========================================

def save_to_csv(jobs):

    if not jobs:
        print("\nTidak ada data baru.")
        print("CSV sebelumnya tidak akan ditimpa.")
        return

    df = pd.DataFrame(
        jobs,
        columns=FIELDNAMES
    )

    # Hapus duplikasi berdasarkan URL
    df = df.drop_duplicates(
        subset=["job_url"],
        keep="first"
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCSV berhasil disimpan!")
    print(f"Lokasi: {OUTPUT_FILE}")
    print(f"Total data: {len(df)}")


# ==========================================
# MAIN
# ==========================================

def main():

    print("=" * 50)
    print("       LINKEDIN JOB COLLECTION")
    print("=" * 50)

    print(f"Output directory: {OUTPUT_DIR}")

    if not HTML_URLS:
        print("\nBelum ada URL sumber yang diizinkan.")
        print("Tidak ada proses scraping yang dijalankan.")
        print("CSV sebelumnya tidak akan ditimpa.")
        return

    all_jobs = []

    for index, url in enumerate(HTML_URLS, 1):

        print(f"\nLowongan sumber ke-{index}/{len(HTML_URLS)}")

        jobs = scrape_job_page(url)

        all_jobs.extend(jobs)

        time.sleep(2)

    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)

    print(f"Total sumber diproses: {len(HTML_URLS)}")
    print(f"Total jobs collected: {len(all_jobs)}")

    save_to_csv(all_jobs)

    print("\nProcess completed!")


if __name__ == "__main__":
    main()
