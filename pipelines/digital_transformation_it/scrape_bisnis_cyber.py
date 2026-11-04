import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# CONFIGURATION
# ============================================================

TOPIC_URL = "https://www.bisnis.com/topic/45191/keamanan-siber"

OUTPUT_FILE = "data/raw/bisnis_cyber_raw.csv"

MAX_PAGES = 3
MAX_PAGE_RETRIES = 2


# ============================================================
# SETUP DRIVER
# ============================================================

from selenium import webdriver
from selenium.webdriver.chrome.service import Service


def create_driver():
    options = webdriver.ChromeOptions()

    # Wajib untuk Chromium di container Linux
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Mengurangi penggunaan resource
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    # Gunakan Chromium dan ChromeDriver yang kita install sendiri
    options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    return driver


# ============================================================
# SCRAPE SATU HALAMAN
# ============================================================

def scrape_page(driver, page):
    url = f"{TOPIC_URL}?page={page}"

    print("\n" + "=" * 70)
    print(f"[INFO] Mengambil halaman {page}")
    print(f"[INFO] URL: {url}")
    print("=" * 70)

    driver.get(url)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "div.artWrap.-row.-center"
            )
        )
    )

    time.sleep(2)

    article_items = driver.find_elements(
        By.CSS_SELECTOR,
        "div.artWrap.-row.-center div.artItem"
    )

    print(
        f"[INFO] Ditemukan {len(article_items)} artikel"
    )

    articles = []

    for item in article_items:

        try:

            # ------------------------------------------------
            # URL
            # ------------------------------------------------

            link_element = item.find_element(
                By.CSS_SELECTOR,
                "a.artLink.artLinkImg"
            )

            article_url = (
                link_element
                .get_attribute("href")
                .strip()
            )

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            try:

                image = link_element.find_element(
                    By.CSS_SELECTOR,
                    "img[alt]"
                )

                title = (
                    image
                    .get_attribute("alt")
                    .strip()
                )

            except Exception:

                title = ""

            # ------------------------------------------------
            # CHANNEL
            # ------------------------------------------------

            try:

                channel = item.find_element(
                    By.CSS_SELECTOR,
                    ".artChannel a"
                ).text.strip()

            except Exception:

                channel = ""

            # ------------------------------------------------
            # PUBLISHED DATE
            # ------------------------------------------------

            published_at = ""

            try:

                date_elements = item.find_elements(
                    By.XPATH,
                    ".//*[contains(text(),'WIB')]"
                )

                for element in date_elements:

                    text = element.text.strip()

                    if text:
                        published_at = text
                        break

            except Exception:
                pass

            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if not title or not article_url:
                continue

            articles.append(
                {
                    "title": title,
                    "url": article_url,
                    "channel": channel,
                    "published_at": published_at,
                    "category": "Keamanan Siber",
                    "source": "Bisnis.com",
                    "scraped_at": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )

        except Exception as error:

            print(
                f"[WARNING] Gagal membaca artikel: "
                f"{error}"
            )

    return articles


# ============================================================
# SCRAPE PAGE DENGAN RETRY
# ============================================================

def scrape_page_with_retry(page):
    """
    Setiap percobaan membuat Chrome Driver baru.
    Ini mencegah driver yang bermasalah dipakai terus.
    """

    for attempt in range(
        1,
        MAX_PAGE_RETRIES + 1
    ):

        driver = None

        try:

            print(
                f"\n[INFO] Page {page} - "
                f"Percobaan {attempt}/{MAX_PAGE_RETRIES}"
            )

            driver = create_driver()

            articles = scrape_page(
                driver,
                page
            )

            if articles:

                print(
                    f"[SUCCESS] Page {page} berhasil."
                )

                return articles

            print(
                f"[WARNING] Page {page} "
                f"tidak menghasilkan artikel."
            )

        except Exception as error:

            print(
                f"[WARNING] Page {page} "
                f"percobaan {attempt} gagal:"
            )

            print(error)

        finally:

            if driver is not None:

                try:
                    driver.quit()
                except Exception:
                    pass

        if attempt < MAX_PAGE_RETRIES:

            print(
                "[INFO] Restart browser "
                "sebelum mencoba lagi..."
            )

            time.sleep(5)

    return []


# ============================================================
# MAIN
# ============================================================

def main():

    all_articles = []

    successful_pages = []
    failed_pages = []

    # ========================================================
    # LOOP PAGES
    # ========================================================

    for page in range(
        1,
        MAX_PAGES + 1
    ):

        page_articles = scrape_page_with_retry(
            page
        )

        if page_articles:

            all_articles.extend(
                page_articles
            )

            successful_pages.append(
                page
            )

        else:

            failed_pages.append(
                page
            )

        time.sleep(2)

    # ========================================================
    # CHECK RESULT
    # ========================================================

    if not all_articles: 
        raise RuntimeError(
            "Scraping Bisnis.com gagal: tidak ada artikel yang berhasil diambil."
    )

    # ========================================================
    # DATAFRAME
    # ========================================================

    df = pd.DataFrame(
        all_articles
    )

    # Deduplicate berdasarkan URL
    df = df.drop_duplicates(
        subset=["url"]
    ).reset_index(drop=True)

    # ========================================================
    # SAVE
    # ========================================================

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("SCRAPING SELESAI")
    print("=" * 70)

    print(
        f"Page berhasil : {successful_pages}"
    )

    print(
        f"Page gagal    : {failed_pages}"
    )

    print(
        f"Total artikel : {len(df)}"
    )

    print(
        f"Output        : {OUTPUT_FILE}"
    )

    print("\nPreview:")

    print(
        df[
            [
                "title",
                "published_at",
                "channel",
                "url"
            ]
        ].head(10).to_string(index=False)
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()