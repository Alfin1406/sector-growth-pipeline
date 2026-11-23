
import re
import csv
import time
import requests
import pdfplumber

from bs4 import BeautifulSoup
from pathlib import Path
from io import BytesIO
from urllib.parse import urljoin


# =========================================================
# KONFIGURASI
# =========================================================

BASE_URL = "https://www.beacukai.go.id"
BTKI_URL = f"{BASE_URL}/btki-dan-tarif"

PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = PROJECT_ROOT / "raw_data" / "beacukai"
OUTPUT_FILE = OUTPUT_DIR / "btki_hs4_all_chapters.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)

CSV_COLUMNS = [
    "hs_code",
    "commodity_id",
    "description_en",
    "chapter",
    "chapter_name",
    "source"
]


# =========================================================
# MEMBERSIHKAN TEKS
# =========================================================

def clean_text(value):
    if value is None:
        return ""

    value = str(value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_hs4(value):
    """
    Mengambil kode HS tepat 4 digit.
    Contoh:
    84.01 -> 8401
    8401  -> 8401

    Kode 8 digit tidak akan dianggap HS 4 digit.
    """

    value = clean_text(value)

    match = re.fullmatch(
        r"(\d{2})[.\s]?(\d{2})",
        value
    )

    if not match:
        return ""

    return match.group(1) + match.group(2)


# =========================================================
# MENGAMBIL DAFTAR PDF DARI WEBSITE BEA CUKAI
# =========================================================

def get_chapter_links():
    print("Membuka halaman resmi BTKI Bea Cukai...")

    response = session.get(
        BTKI_URL,
        timeout=60
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    chapters = {}

    for link in soup.select("a[href]"):

        title = clean_text(link.get_text(" ", strip=True))

        match = re.search(
            r"Chapter\s+(\d{1,2})\s*-\s*(.+)",
            title,
            re.IGNORECASE
        )

        if not match:
            continue

        chapter_number = int(match.group(1))
        chapter_name = clean_text(match.group(2))

        href = link.get("href", "")

        if not href:
            continue

        pdf_url = urljoin(
            response.url,
            href
        )

        if not pdf_url.lower().endswith(".pdf"):
            continue

        chapters[chapter_number] = {
            "chapter": f"{chapter_number:02d}",
            "chapter_name": chapter_name,
            "pdf_url": pdf_url
        }

    return chapters


# =========================================================
# DOWNLOAD PDF
# =========================================================

def download_pdf(pdf_url):
    response = session.get(
        pdf_url,
        timeout=90
    )

    response.raise_for_status()

    if not response.content.startswith(b"%PDF"):
        raise ValueError("File yang diterima bukan PDF.")

    return BytesIO(response.content)


# =========================================================
# EKSTRAKSI TABEL PDF
# =========================================================


def extract_hs4_from_pdf(pdf_file, chapter, chapter_name):
    results = []

    with pdfplumber.open(pdf_file) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()

            if not tables:
                continue

            for table in tables:
                for row in table:
                    if not row:
                        continue

                    cells = [clean_text(cell) for cell in row]
                    cells = [cell for cell in cells if cell]

                    if len(cells) < 2:
                        continue

                    # Cari kode HS 4 digit pada seluruh sel tabel
                    hs_code = ""

                    for cell in cells:
                        candidate = normalize_hs4(cell)

                        if candidate and candidate[:2] == chapter:
                            hs_code = candidate
                            break

                    if not hs_code:
                        continue

                    # Ambil uraian Indonesia dan Inggris
                    hs_index = next(
                        (
                            i for i, cell in enumerate(cells)
                            if normalize_hs4(cell) == hs_code
                        ),
                        -1
                    )

                    if hs_index == -1:
                        continue

                    descriptions = cells[hs_index + 1:]

                    if not descriptions:
                        continue

                    description_id = descriptions[0]
                    description_en = (
                        descriptions[1] if len(descriptions) > 1 else ""
                    )

                    if not description_id:
                        continue

                    results.append({
                        "hs_code": hs_code,
                        "commodity_id": description_id,
                        "description_en": description_en,
                        "chapter": chapter,
                        "chapter_name": chapter_name,
                        "source": "Bea Cukai BTKI 2022"
                    })

    return results

# =========================================================
# SIMPAN SATU CSV
# =========================================================

def save_csv(data):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    unique_data = {}

    for item in data:
        unique_data[item["hs_code"]] = item

    final_data = list(unique_data.values())

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_COLUMNS,
            delimiter=";",
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(final_data)

    print("\nCSV berhasil disimpan:")
    print(OUTPUT_FILE)

    print("Jumlah HS Code unik:", len(final_data))

    return final_data


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 65)
    print("BEA CUKAI - BTKI HS CODE SCRAPER")
    print("SELURUH CHAPTER 01-97")
    print("=" * 65)

    # Mengambil daftar PDF
    try:
        chapters = get_chapter_links()

    except requests.RequestException as error:
        print("Gagal membuka halaman BTKI:", error)
        return

    if not chapters:
        print(
            "Tidak ditemukan tautan PDF chapter. "
            "Struktur halaman perlu diperiksa."
        )
        return

    print("\nJumlah PDF chapter ditemukan:", len(chapters))

    all_data = []
    failed_chapters = []

    # Memproses seluruh PDF
    for chapter_number in sorted(chapters):

        chapter = chapters[chapter_number]

        print("\n" + "-" * 65)

        print(
            f"CHAPTER {chapter['chapter']} - "
            f"{chapter['chapter_name']}"
        )

        print("URL:", chapter["pdf_url"])

        try:
            pdf_file = download_pdf(
                chapter["pdf_url"]
            )

            data = extract_hs4_from_pdf(
                pdf_file,
                chapter["chapter"],
                chapter["chapter_name"]
            )

            all_data.extend(data)

            print("HS 4 digit ditemukan:", len(data))

        except Exception as error:

            print("GAGAL:", error)

            failed_chapters.append(
                chapter["chapter"]
            )

        time.sleep(1)

    # Menghapus duplikasi dan menyimpan hasil
    final_data = save_csv(all_data)

    # Ringkasan
    print("\n" + "=" * 65)
    print("SCRAPING SELESAI")
    print("=" * 65)

    print("PDF chapter ditemukan:", len(chapters))
    print("Total HS 4 digit unik:", len(final_data))

    print(
        "Chapter berhasil:",
        len(chapters) - len(failed_chapters)
    )

    print(
        "Chapter gagal:",
        len(failed_chapters)
    )

    if failed_chapters:
        print(
            "Daftar chapter gagal:",
            ", ".join(failed_chapters)
        )

    print("\nOutput:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
