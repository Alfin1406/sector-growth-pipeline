import csv
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =========================================================
# KONFIGURASI
# =========================================================

BASE_URL = "https://magentaku.id"
LIST_URL = f"{BASE_URL}/lowongan"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "raw_data" / "jobportal"
OUTPUT_FILE = OUTPUT_DIR / "magenta_jobs.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}

CSV_COLUMNS = [
    "job_title",
    "company",
    "sector",
    "location",
    "test_location",
    "education_level",
    "majors",
    "documents",
    "duration",
    "closing_date",
    "published_date",
    "announcement_date",
    "qualifications",
    "job_description",
    "job_url",
    "source",
]

MONTHS = {
    "januari": "01", "january": "01",
    "februari": "02", "february": "02",
    "maret": "03", "march": "03",
    "april": "04",
    "mei": "05", "may": "05",
    "juni": "06", "june": "06",
    "juli": "07", "july": "07",
    "agustus": "08", "august": "08",
    "september": "09",
    "oktober": "10", "october": "10",
    "november": "11",
    "desember": "12", "december": "12",
}

session = requests.Session()
session.headers.update(HEADERS)


# =========================================================
# UTILITAS
# =========================================================

def clean_text(value):
    if value is None:
        return ""

    value = str(value)

    if "<" in value and ">" in value:
        value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)

    return re.sub(r"\s+", " ", value).strip()


def clean_lines(lines):
    cleaned = []

    for line in lines:
        line = clean_text(line)
        if line and line not in cleaned:
            cleaned.append(line)

    return " | ".join(cleaned)


def get_soup(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_text_lines(soup):
    lines = []

    for line in soup.get_text("\n", strip=True).splitlines():
        line = clean_text(line)
        if line and (not lines or line != lines[-1]):
            lines.append(line)

    return lines


def parse_date(value):
    if not value:
        return None

    value = clean_text(value).lower().replace(",", "")

    for month, number in MONTHS.items():
        value = re.sub(rf"\b{month}\b", number, value)

    for date_format in ("%d %m %Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass

    return None


# =========================================================
# PAGINATION DAN DAFTAR LOWONGAN
# =========================================================

def get_listing_pages():
    soup = get_soup(LIST_URL)
    page_numbers = {1}

    for link in soup.select("a[href]"):
        match = re.search(r"[?&]page=(\d+)", link.get("href", ""))
        if match:
            page_numbers.add(int(match.group(1)))

    return [f"{LIST_URL}?page={number}" for number in sorted(page_numbers)]


def get_detail_url(card, job_id):
    location_id = card.get("data-kota", "").strip()

    if not job_id or not location_id:
        return ""

    return f"{LIST_URL}?posting={job_id}&lokasi={location_id}#features"


def get_job_cards(page_url):
    soup = get_soup(page_url)
    cards = soup.select(".job-posting-item[data-id]")
    jobs = []

    for card in cards:
        job_id = card.get("data-id", "").strip()
        title_element = card.select_one(".title")
        title = clean_text(title_element.get_text()) if title_element else ""

        details = card.select(".content-detail")
        company = clean_text(details[0].get_text()) if len(details) > 0 else ""
        location = clean_text(details[1].get_text()) if len(details) > 1 else ""

        closing_date = ""
        published_date = ""

        for element in card.select(".caption"):
            caption = clean_text(element.get_text())

            if re.search(r"penutupan", caption, re.IGNORECASE):
                closing_date = re.sub(
                    r"(?i)^.*?penutupan\s*:?", "", caption
                ).strip()
            elif re.search(r"diterbitkan", caption, re.IGNORECASE):
                published_date = re.sub(
                    r"(?i)^.*?diterbitkan\s*:?", "", caption
                ).strip()

        if not job_id or not title:
            continue

        detail_url = get_detail_url(card, job_id)

        jobs.append({
            "job_id": job_id,
            "job_title": title,
            "company": company,
            "location": location,
            "closing_date": closing_date,
            "published_date": published_date,
            "detail_url": detail_url,
        })

    return jobs


# =========================================================
# EKSTRAKSI INFORMASI DETAIL
# =========================================================

def find_label_index(lines, labels):
    if isinstance(labels, str):
        labels = [labels]

    labels = [label.lower().strip() for label in labels]

    for index, line in enumerate(lines):
        normalized = line.lower().strip()

        for label in labels:
            if normalized == label or normalized.startswith(label + ":"):
                return index

    return -1


def value_after_label(lines, labels, stop_labels=None):
    if isinstance(labels, str):
        labels = [labels]

    stop_labels = [item.lower().strip() for item in (stop_labels or [])]
    index = find_label_index(lines, labels)

    if index == -1:
        return ""

    current = lines[index]

    if ":" in current:
        value = current.split(":", 1)[1].strip()
        if value:
            return value

    for line in lines[index + 1:index + 5]:
        normalized = line.lower().strip()

        if normalized in stop_labels or any(
            normalized.startswith(label + ":") for label in stop_labels
        ):
            break

        if normalized not in {"", ":", "•", "-", "|"}:
            return line.strip()

    return ""


def extract_section(lines, start_labels, end_labels):
    start = find_label_index(lines, start_labels)

    if start == -1:
        return []

    start += 1
    end = len(lines)
    end_labels = [label.lower().strip() for label in end_labels]

    for index in range(start, len(lines)):
        normalized = lines[index].lower().strip()

        if normalized in end_labels or any(
            normalized.startswith(label + ":") for label in end_labels
        ):
            end = index
            break

    return lines[start:end]


def extract_education(lines):
    section = extract_section(
        lines,
        "Pendidikan",
        [
            "Persyaratan Dokumen",
            "Tanggal penting",
            "Rincian Lowongan",
            "Tentang Perusahaan",
        ],
    )

    education_level = value_after_label(
        section, ["Jenjang pendidikan", "Jenjang Pendidikan"]
    )
    majors = value_after_label(section, "Jurusan")

    return education_level, majors


def extract_documents(lines):
    section = extract_section(
        lines,
        "Persyaratan Dokumen",
        ["Tanggal penting", "Rincian Lowongan", "Tentang Perusahaan"],
    )
    return clean_lines(section)


def extract_important_dates(lines):
    section = extract_section(
        lines,
        "Tanggal penting",
        ["Rincian Lowongan", "Tentang Perusahaan"],
    )

    duration = value_after_label(
        section,
        "Durasi",
        ["Penutupan lamaran", "Pengumuman lolos seleksi"],
    )
    closing_date = value_after_label(
        section, "Penutupan lamaran", ["Pengumuman lolos seleksi"]
    )
    announcement_date = value_after_label(
        section, "Pengumuman lolos seleksi"
    )

    return duration, closing_date, announcement_date


def extract_job_details(lines):
    section = extract_section(
        lines, "Rincian Lowongan", ["Tentang Perusahaan"]
    )

    if not section:
        return "", ""

    qualification_index = find_label_index(section, "Kualifikasi")
    description_index = find_label_index(
        section, ["Jobdesc", "Job Description"]
    )

    qualifications = ""
    job_description = ""

    if qualification_index != -1:
        end = (
            description_index
            if description_index > qualification_index
            else len(section)
        )
        qualification_lines = section[qualification_index:end]

        if qualification_lines:
            qualification_lines[0] = re.sub(
                r"(?i)^kualifikasi\s*:?\s*",
                "",
                qualification_lines[0],
            )

        qualifications = clean_lines(qualification_lines)

    if description_index != -1:
        job_description = clean_lines(section[description_index + 1:])

    return qualifications, job_description


def extract_test_location(lines):
    return value_after_label(
        lines, ["Lokasi Tes", "Lokasi Seleksi", "Tempat Tes"]
    )


def has_active_apply_button(soup):
    for element in soup.select("a, button"):
        label = clean_text(element.get_text()).lower()

        if "daftar sekarang" not in label:
            continue

        classes = " ".join(element.get("class", [])).lower()

        if element.has_attr("disabled"):
            continue
        if "disabled" in classes:
            continue
        if element.get("aria-disabled", "").lower() == "true":
            continue

        return True

    return False


# =========================================================
# AMBIL DETAIL LOWONGAN
# =========================================================

def get_job_detail(job):
    detail_url = job["detail_url"]

    if not detail_url:
        print("  URL detail tidak tersedia.")
        return None

    try:
        soup = get_soup(detail_url)
        lines = get_text_lines(soup)

        page_text = " ".join(lines).lower()
        if job["job_title"].lower() not in page_text:
            print("  Judul lowongan tidak ditemukan di halaman detail.")
            return None

        education_level, majors = extract_education(lines)
        documents = extract_documents(lines)

        duration, closing_detail, announcement_date = (
            extract_important_dates(lines)
        )

        qualifications, job_description = extract_job_details(lines)
        test_location = extract_test_location(lines)

        closing_date = closing_detail or job["closing_date"]
        closing = parse_date(closing_date)
        apply_available = has_active_apply_button(soup)

        # Status OPEN hanya diberikan jika tombol daftar aktif dan
        # tanggal penutupan berhasil dibaca serta belum lewat.
        is_open = (
            apply_available
            and closing is not None
            and closing >= datetime.now().date()
        )

        return {
            "job_title": job["job_title"],
            "company": job["company"],
            "sector": "",
            "location": job["location"],
            "test_location": test_location,
            "education_level": education_level,
            "majors": majors,
            "documents": documents,
            "duration": duration,
            "closing_date": closing_date,
            "published_date": job["published_date"],
            "announcement_date": announcement_date,
            "qualifications": qualifications,
            "job_description": job_description,
            "job_url": detail_url,
            "source": "Magenta",
            "_is_open": is_open,
        }

    except requests.RequestException as error:
        print(f"  Gagal mengambil detail: {error}")
        return None


# =========================================================
# SIMPAN CSV
# =========================================================

def save_csv(data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_COLUMNS,
            delimiter=";",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(data)

    print(f"\nCSV tersimpan: {OUTPUT_FILE}")
    print("Jumlah baris:", len(data))


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MAGENTA JOB PORTAL SCRAPER")
    print("=" * 60)

    try:
        pages = get_listing_pages()
    except requests.RequestException as error:
        print(f"Gagal mengambil halaman utama: {error}")
        return

    print("Jumlah halaman:", len(pages))

    all_jobs = {}

    for page in pages:
        print("\nMengambil:", page)

        try:
            jobs = get_job_cards(page)

            for job in jobs:
                all_jobs[job["job_id"]] = job

            print("Lowongan ditemukan:", len(jobs))

        except requests.RequestException as error:
            print(f"Gagal mengambil halaman: {error}")

        time.sleep(1)

    print("\nTotal lowongan unik:", len(all_jobs))

    active_jobs = []
    detail_success = 0
    detail_failed = 0

    for index, job in enumerate(all_jobs.values(), start=1):
        print(
            f"\n[{index}/{len(all_jobs)}] "
            f"{job['company']} - {job['job_title']}"
        )
        print("  URL detail:", job["detail_url"])

        detail = get_job_detail(job)

        if detail is None:
            detail_failed += 1
            continue

        detail_success += 1

        print("  Diterbitkan:", detail["published_date"])
        print("  Penutupan:", detail["closing_date"])
        print("  Pendidikan:", detail["education_level"])
        print("  Jurusan:", detail["majors"])
        print("  Status:", "OPEN" if detail["_is_open"] else "TIDAK OPEN")

        if detail["_is_open"]:
            detail.pop("_is_open")
            active_jobs.append(detail)

        time.sleep(1)

    save_csv(active_jobs)

    print("\n" + "=" * 60)
    print("SCRAPING SELESAI")
    print("=" * 60)
    print("Total lowongan ditemukan:", len(all_jobs))
    print("Detail berhasil diambil:", detail_success)
    print("Detail gagal:", detail_failed)
    print("OPEN terverifikasi:", len(active_jobs))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
