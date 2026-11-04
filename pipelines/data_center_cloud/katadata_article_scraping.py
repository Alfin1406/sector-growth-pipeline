import requests
from bs4 import BeautifulSoup
import csv
import time
import re


INPUT_FILE = "data_center_katadata_all.csv"
OUTPUT_FILE = "data_center_katadata_with_content.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )
}


def scrape_article(url):

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:
            print(f"Gagal: {response.status_code}")
            return None, None, None, None, None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # =========================
        # TITLE
        # =========================

        title_tag = soup.find("h1")

        if title_tag:
            title = title_tag.get_text(
                " ",
                strip=True
            )
        else:
            title = ""

        # =========================
        # DATE
        # =========================

        date = ""

        months = (
            "Januari|Februari|Maret|April|Mei|Juni|"
            "Juli|Agustus|September|Oktober|November|Desember"
        )

        date_pattern = re.compile(
            rf"\d{{1,2}}\s+({months})\s+\d{{4}}"
            rf"(?:,\s*\d{{1,2}}:\d{{2}})?"
            rf"(?:\s*WIB)?",
            re.IGNORECASE
        )

        # Cari tanggal dari seluruh teks halaman
        page_text = soup.get_text(
            " ",
            strip=True
        )

        date_match = date_pattern.search(
            page_text
        )

        if date_match:
            date = date_match.group(0).strip()

        # =========================
        # SUMMARY
        # =========================

        summary = ""

        # Prioritas 1: bagian Ringkasan
        ringkasan = soup.find(
            lambda tag:
            tag.name in ["h2", "h3", "strong"]
            and "Ringkasan" in tag.get_text(
                " ",
                strip=True
            )
        )

        if ringkasan:

            parent = ringkasan.parent

            summary = parent.get_text(
                " ",
                strip=True
            )

            # Hapus kata "Ringkasan" dari hasil
            summary = re.sub(
                r"^Ringkasan\s*:?\s*",
                "",
                summary,
                flags=re.IGNORECASE
            ).strip()

        # Prioritas 2: meta description
        if not summary:

            meta_description = soup.find(
                "meta",
                attrs={
                    "name": "description"
                }
            )

            if (
                meta_description
                and meta_description.get("content")
            ):
                summary = meta_description.get(
                    "content"
                ).strip()

        # Prioritas 3: og:description
        if not summary:

            og_description = soup.find(
                "meta",
                property="og:description"
            )

            if (
                og_description
                and og_description.get("content")
            ):
                summary = og_description.get(
                    "content"
                ).strip()

        # =========================
        # IMAGE
        # =========================

        image_url = ""

        # Prioritas 1: og:image
        og_image = soup.find(
            "meta",
            property="og:image"
        )

        if (
            og_image
            and og_image.get("content")
        ):
            image_url = og_image.get(
                "content"
            )

        # Prioritas 2: twitter:image
        if not image_url:

            twitter_image = soup.find(
                "meta",
                attrs={
                    "name": "twitter:image"
                }
            )

            if (
                twitter_image
                and twitter_image.get("content")
            ):
                image_url = twitter_image.get(
                    "content"
                )

        # Prioritas 3: gambar artikel
        if not image_url:

            article_image = soup.find(
                "img"
            )

            if article_image:

                image_url = (
                    article_image.get("src")
                    or article_image.get("data-src")
                    or ""
                )

        # =========================
        # CONTENT
        # =========================

        content_parts = []

        paragraphs = soup.find_all("p")

        for p in paragraphs:

            text = p.get_text(
                " ",
                strip=True
            )

            if not text:
                continue

            if len(text) < 30:
                continue

            content_parts.append(text)

        content = "\n".join(
            content_parts
        )

        return (
            title,
            date,
            summary,
            image_url,
            content
        )

    except Exception as e:

        print(
            "Error:",
            e
        )

        return (
            None,
            None,
            None,
            None,
            None
        )


def main():

    # =========================
    # BACA CSV
    # =========================

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        articles = list(reader)

    print(
        f"Total artikel yang akan diproses: "
        f"{len(articles)}"
    )

    results = []

    # =========================
    # SCRAPING
    # =========================

    for i, article in enumerate(
        articles,
        start=1
    ):

        url = article["article_url"]

        print(
            f"[{i}/{len(articles)}] "
            f"{article['title']}"
        )

        (
            title,
            date,
            summary,
            image_url,
            content
        ) = scrape_article(url)

        article["title"] = (
            title
            or article["title"]
        )

        article["published_date"] = date

        article["summary"] = summary

        article["image_url"] = image_url

        article["content"] = content

        article["source"] = "Katadata"

        results.append(article)

        time.sleep(1)

    # =========================
    # SIMPAN CSV
    # =========================

    fieldnames = [
        "title",
        "published_date",
        "summary",
        "article_url",
        "image_url",
        "content",
        "source"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    print()
    print("=" * 50)
    print(
        "SCRAPING ARTIKEL KATADATA SELESAI"
    )
    print("=" * 50)

    print(
        f"Data berhasil disimpan: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()