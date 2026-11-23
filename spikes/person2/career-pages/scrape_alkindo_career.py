
import requests
import csv
import re
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

# ==========================================================
# KONFIGURASI
# ==========================================================

URL = "https://career.alkindo.co.id/index.php?lang=id"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "raw_data" / "careerpages"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "alkindo_jobs.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SKILL_KEYWORDS = [
    "python", "sql", "excel", "microsoft excel",
    "power bi", "tableau", "machine learning",
    "data analysis", "data analytics", "statistics",
    "bpmn", "uml", "system design", "erp",
    "server", "virtualisasi", "jaringan",
    "networking", "database", "postgresql",
    "mysql", "communication", "leadership",
    "troubleshooting", "maintenance",
    "microsoft office", "pivot table", "vlookup",
    "negosiasi", "administrasi"
]

FIELDNAMES = [
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
    "requirements",
    "status",
    "application_url",
    "job_url",
    "source",
    "scraped_at"
]


# ==========================================================
# FUNGSI BANTU
# ==========================================================

def clean_text(value):
    """
    Membersihkan teks agar tidak memiliki baris baru,
    tab, atau spasi berlebihan.
    """

    if not value:
        return ""

    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)

    value = str(value)

    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_date_period(text):

    pattern = (
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"
        r"\s*[–-]\s*"
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"
    )

    match = re.search(pattern, text)

    if match:
        return match.group(1), match.group(2)

    return "", ""


def extract_experience(text):

    patterns = [
        r"(?:minimal|minimum|min\.?)\s*(\d+)\s*tahun",
        r"pengalaman kerja\s*(?:minimal)?\s*(\d+)\s*tahun",
        r"pengalaman.*?(\d+)\s*tahun"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return f"{match.group(1)} tahun"

    if re.search(r"fresh graduate", text, re.IGNORECASE):
        return "Fresh Graduate"

    return ""


def extract_skills(text):

    found = []
    text_lower = text.lower()

    for skill in SKILL_KEYWORDS:

        # Mencegah pencocokan singkatan di dalam kata lain
        pattern = (
            r"(?<!\w)"
            + re.escape(skill.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, text_lower):
            found.append(skill)

    return ", ".join(found)


def extract_section(modal, heading_keyword):

    for section in modal.select(".job-section"):

        heading = section.find(["h4", "h5", "h6"])

        if not heading:
            continue

        if heading_keyword.lower() in clean_text(heading).lower():

            paragraph = section.find("p")

            if paragraph:
                return clean_text(paragraph)

            items = section.find_all("li")

            if items:
                return clean_text(
                    " ".join(
                        item.get_text(" ", strip=True)
                        for item in items
                    )
                )

    return ""


# ==========================================================
# TAHAP 1 - AKSES WEBSITE
# ==========================================================

print("=" * 70)
print("SCRAPING CAREER PAGE PT ALKINDO NARATAMA TBK")
print("=" * 70)

print("\n[TAHAP 1] Mengakses website...")

session = requests.Session()
session.headers.update(HEADERS)

response = session.get(URL, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

print(f"HTTP Status : {response.status_code}")
print(f"Ukuran HTML : {len(response.text):,} karakter")
print("Website berhasil diakses.")


# ==========================================================
# TAHAP 2 - MENEMUKAN LOWONGAN AKTIF
# ==========================================================

print("\n[TAHAP 2] Memeriksa daftar lowongan...")

cards = soup.select(".job-card-minimal")

print(f"Total kartu ditemukan : {len(cards)}")

active_jobs = []
seen = set()

for card in cards:

    status_element = card.select_one(".job-status")
    title_element = card.select_one(".job-title")

    if not status_element or not title_element:
        continue

    status = clean_text(status_element)

    # Hanya menyimpan lowongan dengan status Aktif
    if status.lower() != "aktif":
        continue

    job_title = clean_text(title_element)

    detail_button = card.select_one("[data-bs-target]")

    if not detail_button:
        print(f"[SKIP] Modal tidak ditemukan: {job_title}")
        continue

    modal_id = detail_button.get(
        "data-bs-target", ""
    ).lstrip("#")

    modal = soup.find(id=modal_id)

    if not modal:
        print(f"[SKIP] Detail tidak ditemukan: {job_title}")
        continue

    # Verifikasi ulang status dari modal
    modal_status = modal.select_one(".job-status")

    if not modal_status:
        print(f"[SKIP] Status detail kosong: {job_title}")
        continue

    if clean_text(modal_status).lower() != "aktif":
        continue

    title_detail = modal.select_one(".modal-job-title")

    if title_detail:
        job_title = clean_text(title_detail)

    key = (job_title.lower(), modal_id)

    if key in seen:
        continue

    seen.add(key)

    active_jobs.append({
        "card": card,
        "modal": modal,
        "title": job_title,
        "modal_id": modal_id
    })

print(f"Total lowongan aktif : {len(active_jobs)}")


# ==========================================================
# TAHAP 3 - EKSTRAKSI DETAIL
# ==========================================================

print("\n[TAHAP 3] Mengekstrak detail lowongan...")

records = []

for index, job in enumerate(active_jobs, 1):

    modal = job["modal"]
    job_title = job["title"]

    print(
        f"\n[{index}/{len(active_jobs)}] {job_title}"
    )

    # Pendidikan
    education_element = modal.select_one(
        ".modal-education-tag strong"
    )

    education = clean_text(education_element)

    # Periode tanggal
    meta_element = modal.select_one(".job-meta")
    meta_text = clean_text(meta_element)

    date_posted, deadline = extract_date_period(meta_text)

    # Deskripsi pekerjaan
    description = extract_section(
        modal,
        "Deskripsi Pekerjaan"
    )

    # Persyaratan
    requirements = extract_section(
        modal,
        "Persyaratan"
    )

    # Skills berdasarkan kata kunci
    combined_text = f"{description} {requirements}"
    skills = extract_skills(combined_text)

    # Pengalaman
    experience = extract_experience(requirements)

    # URL pendaftaran
    apply_button = modal.select_one(
        ".btn-apply-modal[href]"
    )

    application_url = ""

    if apply_button:
        application_url = urljoin(
            URL,
            apply_button.get("href", "")
        )

    record = {
        "job_title": clean_text(job_title),
        "company": "PT Alkindo Naratama Tbk",
        "sector": "Manufaktur/Kemasan",
        "location": "",
        "date_posted": clean_text(date_posted),
        "skills": clean_text(skills),
        "description": clean_text(description),
        "employment_type": "",
        "education": clean_text(education),
        "experience": clean_text(experience),
        "deadline": clean_text(deadline),
        "requirements": clean_text(requirements),
        "status": "OPEN",
        "application_url": clean_text(application_url),
        "job_url": URL + "#" + job["modal_id"],
        "source": "Alkindo Career",
        "scraped_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    records.append(record)

    print(f"  Pendidikan : {education or '-'}")
    print(f"  Deadline   : {deadline or '-'}")
    print(f"  Skills     : {skills or '-'}")
    print(f"  Deskripsi  : {'Ada' if description else 'Tidak ada'}")
    print(f"  Persyaratan: {'Ada' if requirements else 'Tidak ada'}")


# ==========================================================
# TAHAP 4 - VALIDASI DAN MEMBERSIHKAN DATA
# ==========================================================

print("\n[TAHAP 4] Membersihkan dan memvalidasi data...")

for record in records:

    for field in FIELDNAMES:

        if isinstance(record[field], str):
            record[field] = clean_text(record[field])

print("Pembersihan teks selesai.")
print("Baris baru dan spasi berlebih telah dibersihkan.")


# ==========================================================
# TAHAP 5 - MENYIMPAN CSV
# ==========================================================

print("\n[TAHAP 5] Menyimpan data ke CSV...")

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=FIELDNAMES,
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL
    )

    writer.writeheader()
    writer.writerows(records)


# ==========================================================
# TAHAP 6 - VALIDASI KELENGKAPAN
# ==========================================================

print("\n[TAHAP 6] Validasi kelengkapan data...")

print("\nKelengkapan kolom:")

for field in FIELDNAMES:

    filled = sum(
        1 for row in records
        if str(row[field]).strip()
    )

    print(
        f"{field:20} : {filled}/{len(records)}"
    )


# ==========================================================
# RINGKASAN
# ==========================================================

print("\n" + "=" * 70)
print("RINGKASAN SCRAPING ALKINDO")
print("=" * 70)

print(f"Total kartu HTML     : {len(cards)}")
print(f"Total lowongan aktif : {len(records)}")

print(
    "Memiliki deskripsi  :",
    sum(bool(r["description"]) for r in records)
)

print(
    "Memiliki persyaratan:",
    sum(bool(r["requirements"]) for r in records)
)

print(
    "Memiliki deadline   :",
    sum(bool(r["deadline"]) for r in records)
)

print(f"\nFile CSV : {OUTPUT_FILE}")
print("Delimiter: Semicolon (;)")
print("Encoding : UTF-8-SIG")
print("Format   : Satu lowongan per baris")

print("\nSCRAPING SELESAI.")
