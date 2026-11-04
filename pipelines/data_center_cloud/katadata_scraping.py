import requests
from bs4 import BeautifulSoup
import csv
import time


URL = "https://katadata.co.id/tags/data-center"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )
}

OUTPUT_FILE = "data_center_katadata_all.csv"


def scrape_katadata():

    print("Mengakses halaman Katadata...")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("Status:", response.status_code)

    if response.status_code != 200:
        print("Gagal mengakses halaman Katadata.")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []

    # Cari semua link artikel
    for link in soup.find_all("a", href=True):

        href = link.get("href")
        title = link.get_text(" ", strip=True)

        # Pastikan hanya mengambil link artikel Katadata
        if not href:
            continue

        if href.startswith("/"):
            href = "https://katadata.co.id" + href

        # Filter link yang merupakan artikel
        if (
            "katadata.co.id/digital/" in href
            or "katadata.co.id/berita/" in href
            or "katadata.co.id/finansial/" in href
            or "katadata.co.id/ekonomi/" in href
        ):

            if len(title) < 20:
                continue

            # Hindari duplikat
            if any(article["article_url"] == href for article in articles):
                continue

            articles.append({
                "title": title,
                "article_url": href
            })

    print(f"Artikel ditemukan: {len(articles)}")

    # Simpan ke CSV
    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "title",
                "article_url"
            ]
        )

        writer.writeheader()
        writer.writerows(articles)

    print(f"Data berhasil disimpan ke: {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape_katadata()