import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re


# ==========================================================
# 1. PERIODE 12 BULAN
# ==========================================================

today = datetime.now()
start_date = today - timedelta(days=365)

print("===================================")
print("SCRAPING KOMPAS - 12 BULAN")
print("===================================")

print("Periode:")
print(
    start_date.strftime("%Y-%m-%d"),
    "sampai",
    today.strftime("%Y-%m-%d")
)


# ==========================================================
# 2. URL DASAR
# ==========================================================

base_url = "https://www.kompas.com/tag/data-center"


# ==========================================================
# 3. HEADER
# ==========================================================

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}


# ==========================================================
# 4. SESSION REQUESTS
# ==========================================================

session = requests.Session()
session.headers.update(headers)


# ==========================================================
# 5. TEMPAT DATA
# ==========================================================

data = []

stop_scraping = False
page = 1


# ==========================================================
# 6. LOOP HALAMAN
# ==========================================================

while not stop_scraping:

    url = (
        f"{base_url}"
        f"?type=artikel"
        f"&sort=terbaru"
        f"&page={page}"
    )

    print("\n===================================")
    print(f"Membuka halaman {page}")
    print("===================================")
    print(url)

    try:

        response = session.get(
            url,
            timeout=30
        )

        response.raise_for_status()

    except Exception as e:

        print("Gagal membuka halaman:", e)
        break


    # ======================================================
    # 7. PARSING HALAMAN
    # ======================================================

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # ======================================================
    # 8. CARI ARTIKEL
    # ======================================================

    articles = soup.select(
        "div.articleList div.articleItem"
    )

    print(
        "Artikel ditemukan:",
        len(articles)
    )


    if not articles:

        print(
            "Tidak ada artikel. "
            "Proses dihentikan."
        )

        break


    # ======================================================
    # 9. LOOP ARTIKEL
    # ======================================================

    for article in articles:

        # --------------------------------------------------
        # Judul
        # --------------------------------------------------

        title_tag = article.select_one(
            "h2.articleTitle"
        )

        if not title_tag:
            continue

        title = title_tag.get_text(
            " ",
            strip=True
        )


        # --------------------------------------------------
        # URL
        # --------------------------------------------------

        link_tag = article.select_one(
            "a.article-link"
        )

        if not link_tag:
            continue

        article_url = link_tag.get(
            "href"
        )

        if not article_url:
            continue


        # --------------------------------------------------
        # TANGGAL
        # --------------------------------------------------

        post_tag = article.select_one(
            "div.articlePost"
        )

        published_date = None

        if post_tag:

            post_text = post_tag.get_text(
                " ",
                strip=True
            )

            # Format:
            # 27 September 2026

            match = re.search(
                r"\d{1,2}\s+"
                r"(Januari|Februari|Maret|April|Mei|Juni|"
                r"Juli|Agustus|September|Oktober|November|Desember)"
                r"\s+\d{4}",
                post_text
            )

            if match:

                date_text = match.group(0)

                month_mapping = {

                    "Januari": "January",
                    "Februari": "February",
                    "Maret": "March",
                    "April": "April",
                    "Mei": "May",
                    "Juni": "June",
                    "Juli": "July",
                    "Agustus": "August",
                    "September": "September",
                    "Oktober": "October",
                    "November": "November",
                    "Desember": "December"

                }

                for indo, english in month_mapping.items():

                    date_text = date_text.replace(
                        indo,
                        english
                    )

                try:

                    published_date = datetime.strptime(
                        date_text,
                        "%d %B %Y"
                    )

                except:

                    published_date = None


        # --------------------------------------------------
        # JIKA TANGGAL TIDAK TERBACA
        # --------------------------------------------------

        if published_date is None:

            print(
                "Tanggal tidak terbaca:",
                title
            )

            continue


        # ==================================================
        # CEK BATAS 12 BULAN
        # ==================================================

        if published_date < start_date:

            print(
                "\nArtikel sudah melewati "
                "periode 12 bulan:"
            )

            print(
                published_date.strftime(
                    "%Y-%m-%d"
                ),
                "-",
                title
            )

            print(
                "\nSTOP SCRAPING."
            )

            stop_scraping = True

            break


        # ==================================================
        # GAMBAR
        # ==================================================

        image_url = None

        image_tag = article.select_one(
            "img"
        )

        if image_tag:

            image_url = (
                image_tag.get("src")
                or image_tag.get("data-src")
                or image_tag.get("data-original")
            )


        # ==================================================
        # SUMMARY
        # ==================================================

        summary = None

        summary_tag = article.select_one(
            "p"
        )

        if summary_tag:

            summary = summary_tag.get_text(
                " ",
                strip=True
            )


        # ==================================================
        # AMBIL ISI ARTIKEL
        # ==================================================

        print(
            "\nMengambil artikel:"
        )

        print(title)

        content = None

        try:

            article_response = session.get(
                article_url,
                timeout=30
            )

            article_response.raise_for_status()

            article_soup = BeautifulSoup(
                article_response.text,
                "html.parser"
            )


            # --------------------------------------------------
            # CARI CONTENT
            # --------------------------------------------------

            content_container = (
                article_soup.select_one(
                    ".read__content"
                )
                or
                article_soup.select_one(
                    ".read__content__body"
                )
                or
                article_soup.select_one(
                    "div.read__content"
                )
            )


            if content_container:

                paragraphs = content_container.select(
                    "p"
                )

                content = "\n".join(
                    p.get_text(
                        " ",
                        strip=True
                    )
                    for p in paragraphs
                    if p.get_text(
                        " ",
                        strip=True
                    )
                )


        except Exception as e:

            print(
                "Gagal mengambil content:",
                e
            )


        # ==================================================
        # SIMPAN DATA
        # ==================================================

        data.append({

            "title": title,

            "published_date":
                published_date.strftime(
                    "%Y-%m-%d"
                ),

            "summary": summary,

            "content": content,

            "article_url": article_url,

            "image_url": image_url,

            "source": "KOMPAS",

            "tag": "Data Center",

            "scraped_at":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })


    # ======================================================
    # NEXT PAGE
    # ======================================================

    if stop_scraping:

        break


    page += 1

    print(
        "\nLanjut ke halaman:",
        page
    )

    time.sleep(2)


# ==========================================================
# DATAFRAME
# ==========================================================

df = pd.DataFrame(data)


# ==========================================================
# HAPUS DUPLIKAT
# ==========================================================

if not df.empty:

    df = df.drop_duplicates(
        subset=["article_url"]
    )


# ==========================================================
# SORTING
# ==========================================================

if not df.empty:

    df["published_date"] = pd.to_datetime(
        df["published_date"]
    )

    df = df.sort_values(
        by="published_date",
        ascending=False
    )

    df["published_date"] = (
        df["published_date"]
        .dt.strftime("%Y-%m-%d")
    )


# ==========================================================
# HASIL
# ==========================================================

print("\n===================================")
print("SCRAPING KOMPAS SELESAI")
print("===================================")

print(
    "Total artikel:",
    len(df)
)


# ==========================================================
# SIMPAN CSV
# ==========================================================

filename = (
    "data_center_kompas_all.csv"
)

df.to_csv(
    filename,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================================
# PREVIEW
# ==========================================================

print("\nData berhasil disimpan:")
print(filename)

print("\nKolom:")
print(df.columns.tolist())

print("\n5 data terbaru:")

if not df.empty:

    print(
        df[
            [
                "title",
                "published_date",
                "source"
            ]
        ].head().to_string(
            index=False
        )
    )

else:

    print("Tidak ada data.")


print("\n===================================")
print("PROSES SELESAI")
print("===================================")