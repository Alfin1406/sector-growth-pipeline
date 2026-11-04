import os
import re
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options 


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://teknologi.bisnis.com"

DISCOVERY_URLS = [
    "https://teknologi.bisnis.com/",
    "https://teknologi.bisnis.com/sains-teknologi",
    "https://teknologi.bisnis.com/startup",
    "https://teknologi.bisnis.com/telekomunikasi",
]

OUTPUT_FILE = "data/raw/bisnis_raw.csv"

MAX_ARTICLES = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}


# ============================================================
# SESSION
# ============================================================

def create_session():

    session = requests.Session()

    session.headers.update(HEADERS)

    return session


# ============================================================
# DISCOVERY
# ============================================================

def get_article_urls(session):

    print("=" * 60)
    print("DISCOVERY BISNIS.COM")
    print("=" * 60)

    article_urls = []
    seen = set()

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        for discovery_url in DISCOVERY_URLS:

            print()
            print("Scraping discovery page:")
            print(discovery_url)

            try:
                driver.get(discovery_url)

                # Tunggu sebentar agar halaman selesai dimuat
                import time
                time.sleep(3)

                soup = BeautifulSoup(
                    driver.page_source,
                    "html.parser"
                )

                page_count = 0

                for a in soup.find_all("a", href=True):

                    href = a.get("href", "").strip()

                    if not href.startswith(
                        f"{BASE_URL}/read/"
                    ):
                        continue

                    if href in seen:
                        continue

                    seen.add(href)
                    article_urls.append(href)
                    page_count += 1

                print(
                    f"Artikel ditemukan: {page_count}"
                )

            except Exception as e:
                print(
                    f"ERROR discovery {discovery_url}: {e}"
                )

    finally:
        driver.quit()

    article_urls = article_urls[:MAX_ARTICLES]

    print()
    print("=" * 60)
    print(
        f"TOTAL UNIQUE ARTICLE URL: "
        f"{len(article_urls)}"
    )
    print("=" * 60)

    for i, url in enumerate(
        article_urls,
        start=1
    ):
        print(f"{i}. {url}")

    return article_urls 


# ============================================================
# DETAIL ARTICLE
# ============================================================

def scrape_article(session, url):

    try:

        response = session.get(
            url,
            timeout=20
        )

        if response.status_code != 200:

            print(
                f"Status {response.status_code}: {url}"
            )

            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = ""

        og_title = soup.find(
            "meta",
            property="og:title"
        )

        if og_title:

            title = og_title.get(
                "content",
                ""
            ).strip()

        if not title and soup.title:

            title = soup.title.get_text(
                " ",
                strip=True
            )

        # ----------------------------------------------------
        # PUBLISHED AT
        # ----------------------------------------------------

        published_at = None

        meta_published = soup.find(
            "meta",
            attrs={
                "property": "article:published_time"
            }
        )

        if meta_published:

            published_at = meta_published.get(
                "content"
            )

        # ----------------------------------------------------
        # CHANNEL
        # ----------------------------------------------------

        channel = "Tekno"

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        return {
            "title": title,
            "url": url,
            "published_at": published_at,
            "channel": channel,
            "source": "Bisnis.com",
            "scraped_at": datetime.now(),
        }

    except Exception as e:

        print(
            f"ERROR article: {url}"
        )

        print(e)

        return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("01 SCRAPING - BISNIS.COM")
    print("=" * 60)

    session = create_session()

    # --------------------------------------------------------
    # DISCOVERY
    # --------------------------------------------------------

    article_urls = get_article_urls(
        session
    )

    if not article_urls:

        print(
            "Tidak ada artikel ditemukan."
        )

        return

    # --------------------------------------------------------
    # SCRAPE DETAIL
    # --------------------------------------------------------

    rows = []

    for i, url in enumerate(
        article_urls,
        start=1
    ):

        print()
        print(
            f"[{i}/{len(article_urls)}] "
            f"Scraping article..."
        )

        result = scrape_article(
            session,
            url
        )

        if result:

            print(
                "Title:",
                result["title"][:100]
            )

            print(
                "Published:",
                result["published_at"]
            )

            rows.append(result)

    # --------------------------------------------------------
    # DATAFRAME
    # --------------------------------------------------------

    df = pd.DataFrame(rows)

    if df.empty:

        print(
            "Tidak ada data berhasil dikumpulkan."
        )

        return

    # Deduplicate URL
    df = df.drop_duplicates(
        subset=["url"],
        keep="first"
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    os.makedirs(
        "data/raw",
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("SCRAPING BISNIS.COM SELESAI")
    print("=" * 60)

    print(
        "Total articles:",
        len(df)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print()
    print(
        df[
            [
                "title",
                "published_at"
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()