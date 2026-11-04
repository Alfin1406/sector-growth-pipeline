import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time


# ==========================================
# 1. URL DASAR
# ==========================================

base_url = "https://www.antaranews.com/tag/data-center-di-indonesia"


# ==========================================
# 2. HEADER
# ==========================================

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/153.0.0.0 Safari/537.36"
}


# ==========================================
# 3. TEMPAT MENYIMPAN SEMUA DATA
# ==========================================

data = []


# ==========================================
# 4. LOOP HALAMAN 1 - 8
# ==========================================

for page in range(1, 9):

    # Halaman 1 tidak memiliki /1
    if page == 1:
        url = base_url
    else:
        url = f"{base_url}/{page}"

    print(f"\nMengambil halaman {page}:")
    print(url)

    # Request
    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print("Status code:", response.status_code)

    if response.status_code != 200:
        print("Gagal mengambil halaman.")
        continue

    # Parsing HTML
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # Cari semua artikel
    articles = soup.select(
        "div.wrapper__list__article "
        "div.card__post.card__post-list"
    )

    print("Artikel ditemukan:", len(articles))


    # ======================================
    # 5. LOOP SETIAP ARTIKEL
    # ======================================

    for article in articles:

        # -------------------------------
        # Judul + URL
        # -------------------------------

        title_tag = article.select_one(
            ".card__post__title h2 a"
        )

        if title_tag:
            title = title_tag.get_text(strip=True)
            article_url = title_tag.get("href")
        else:
            title = None
            article_url = None


        # -------------------------------
        # Tanggal
        # -------------------------------

        date_tag = article.select_one(
            ".card__post__author-info span"
        )

        if date_tag:
            published_date = date_tag.get_text(strip=True)
        else:
            published_date = None


        # -------------------------------
        # Summary
        # -------------------------------

        summary_tag = article.select_one("p")

        if summary_tag:
            summary = summary_tag.get_text(strip=True)
        else:
            summary = None


        # -------------------------------
        # Simpan data
        # -------------------------------

        data.append({
            "title": title,
            "published_date": published_date,
            "summary": summary,
            "article_url": article_url,
            "source": "ANTARA",
            "tag": "Data Center di Indonesia",
            "scraped_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        })


    # ======================================
    # 6. JEDA ANTAR HALAMAN
    # ======================================

    time.sleep(2)


# ==========================================
# 7. BUAT DATAFRAME
# ==========================================

df = pd.DataFrame(data)


# ==========================================
# 8. HAPUS DATA DUPLIKAT
# ==========================================

df = df.drop_duplicates(
    subset=["article_url"]
)


# ==========================================
# 9. TAMPILKAN HASIL
# ==========================================

print("\n===================================")
print("SCRAPING SELESAI")
print("===================================")

print("Total artikel:", len(df))

print("\n5 data pertama:")
print(df.head())


# ==========================================
# 10. SIMPAN KE CSV
# ==========================================

filename = "data_center_antaranews_all.csv"

df.to_csv(
    filename,
    index=False,
    encoding="utf-8-sig"
)

print("\nData berhasil disimpan:")
print(filename)