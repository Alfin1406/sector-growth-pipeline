import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "data/raw/bisnis_cyber_raw.csv" 
OUTPUT_FILE = "data/processed/bisnis_cyber_with_content.csv"

# Testing awal.
# Setelah PoC berhasil, ubah menjadi None.
MAX_ARTICLES = 10


# ============================================================
# SELENIUM DRIVER
# ============================================================

def create_driver(): 
    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")

    return webdriver.Chrome(
        service=service,
        options=options
    ) 


# ============================================================
# DETEKSI HALAMAN BLOCKED
# ============================================================

def is_blocked_page(driver):
    """
    Mengecek apakah halaman yang dibuka
    merupakan halaman proteksi seperti 'Just a moment...'.
    """

    page_title = driver.title.strip().lower()

    blocked_titles = [
        "just a moment...",
        "just a moment",
        "attention required",
    ]

    if any(
        blocked_title in page_title
        for blocked_title in blocked_titles
    ):
        return True

    # Tambahan pengecekan isi halaman
    try:
        body_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text.lower()

        blocked_keywords = [
            "performing security verification",
            "checking your browser",
            "enable javascript and cookies",
        ]

        if any(
            keyword in body_text
            for keyword in blocked_keywords
        ):
            return True

    except Exception:
        pass

    return False


# ============================================================
# SCRAPE SATU ARTIKEL
# ============================================================

def scrape_article(driver, url):
    """
    Membuka satu artikel dan mengambil informasi.
    Tidak melakukan retry.
    """

    print("\n[INFO] Membuka artikel:")
    print(url)

    driver.get(url)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(3)

    # --------------------------------------------------------
    # CEK BLOCKED
    # --------------------------------------------------------

    if is_blocked_page(driver):

        print(
            "[WARNING] Halaman terkena "
            "proteksi / Cloudflare."
        )

        return {
            "title_detail": "",
            "author": "",
            "content": "",
            "image_url": "",
            "content_status": "BLOCKED",
        }

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print(
        f"[DEBUG] Current URL : "
        f"{driver.current_url}"
    )

    print(
        f"[DEBUG] Page title  : "
        f"{driver.title.strip()}"
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = ""

    try:
        meta_title = driver.find_element(
            By.CSS_SELECTOR,
            'meta[property="og:title"]'
        )

        title = (
            meta_title
            .get_attribute("content")
            or ""
        ).strip()

    except Exception:
        pass

    if not title:

        try:
            h1 = driver.find_element(
                By.TAG_NAME,
                "h1"
            )

            title = h1.text.strip()

        except Exception:
            pass

    # --------------------------------------------------------
    # AUTHOR
    # --------------------------------------------------------

    author = ""

    author_selectors = [
        'meta[name="author"]',
        'meta[property="article:author"]',
    ]

    for selector in author_selectors:

        try:

            element = driver.find_element(
                By.CSS_SELECTOR,
                selector
            )

            author = (
                element
                .get_attribute("content")
                or ""
            ).strip()

            if author:
                break

        except Exception:
            continue

    # --------------------------------------------------------
    # CONTENT
    # --------------------------------------------------------

    content = ""

    content_selectors = [
        ".detailsContent",
        ".detailsContent p",
        ".article-content",
        ".article-content p",
        ".detail__body",
        ".detail__body p",
    ]

    for selector in content_selectors:

        try:

            element = driver.find_element(
                By.CSS_SELECTOR,
                selector
            )

            paragraphs = element.find_elements(
                By.TAG_NAME,
                "p"
            )

            paragraph_texts = []

            for paragraph in paragraphs:

                text = paragraph.text.strip()

                if text:
                    paragraph_texts.append(text)

            if paragraph_texts:

                content = "\n".join(
                    paragraph_texts
                )

                break

            raw_text = element.text.strip()

            if raw_text:
                content = raw_text
                break

        except Exception:
            continue

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image_url = ""

    try:

        image = driver.find_element(
            By.CSS_SELECTOR,
            'meta[property="og:image"]'
        )

        image_url = (
            image
            .get_attribute("content")
            or ""
        ).strip()

    except Exception:
        pass

    if not image_url:

        try:

            image = driver.find_element(
                By.CSS_SELECTOR,
                "article img"
            )

            image_url = (
                image
                .get_attribute("src")
                or ""
            ).strip()

        except Exception:
            pass

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not title and not content:

        print(
            "[WARNING] Halaman terbuka, "
            "tetapi data artikel tidak ditemukan."
        )

        return {
            "title_detail": "",
            "author": author,
            "content": "",
            "image_url": image_url,
            "content_status": "FAILED",
        }

    print(
        "[SUCCESS] Artikel berhasil dibaca."
    )

    print(
        f"[INFO] Content length: "
        f"{len(content)} karakter"
    )

    return {
        "title_detail": title,
        "author": author,
        "content": content,
        "image_url": image_url,
        "content_status": "SUCCESS",
    }


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # LOAD RAW DATA
    # --------------------------------------------------------

    print("[INFO] Membaca raw dataset...")

    df = pd.read_csv(INPUT_FILE)

    print(
        f"[INFO] Total raw artikel: {len(df)}"
    )

    # --------------------------------------------------------
    # TESTING LIMIT
    # --------------------------------------------------------

    if MAX_ARTICLES is not None:

        df = df.head(
            MAX_ARTICLES
        ).copy()

        print(
            f"[INFO] Mode testing: "
            f"{len(df)} artikel"
        )

    # --------------------------------------------------------
    # OUTPUT SCHEMA
    # --------------------------------------------------------

    output_columns = [
        "title",
        "url",
        "channel",
        "published_at",
        "category",
        "source",
        "scraped_at",
        "title_detail",
        "author",
        "content",
        "image_url",
        "content_status",
        "scraped_at_content",
    ]

    results = []

    # --------------------------------------------------------
    # BROWSER
    # --------------------------------------------------------

    driver = create_driver()

    try:

        # ====================================================
        # LOOP ARTIKEL
        # ====================================================

        for index, row in df.iterrows():

            print("\n" + "=" * 70)

            print(
                f"[INFO] Artikel "
                f"{index + 1}/{len(df)}"
            )

            print("=" * 70)

            url = row["url"]

            try:

                # ------------------------------------------------
                # SCRAPE ARTICLE
                # ------------------------------------------------

                article_data = scrape_article(
                    driver,
                    url
                )

            except Exception as error:

                print(
                    "[ERROR] Gagal membuka artikel:"
                )

                print(error)

                article_data = {
                    "title_detail": "",
                    "author": "",
                    "content": "",
                    "image_url": "",
                    "content_status": "FAILED",
                }

            # ------------------------------------------------
            # GABUNGKAN RAW + CONTENT
            # ------------------------------------------------

            result = {
                "title": row.get(
                    "title",
                    ""
                ),

                "url": row.get(
                    "url",
                    ""
                ),

                "channel": row.get(
                    "channel",
                    ""
                ),

                "published_at": row.get(
                    "published_at",
                    ""
                ),

                "category": row.get(
                    "category",
                    ""
                ),

                "source": row.get(
                    "source",
                    "Bisnis.com"
                ),

                "scraped_at": row.get(
                    "scraped_at",
                    ""
                ),

                "title_detail": article_data[
                    "title_detail"
                ],

                "author": article_data[
                    "author"
                ],

                "content": article_data[
                    "content"
                ],

                "image_url": article_data[
                    "image_url"
                ],

                "content_status": article_data[
                    "content_status"
                ],

                "scraped_at_content": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }

            results.append(result)

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            print(
                f"[INFO] Status: "
                f"{result['content_status']}"
            )

            print(
                f"[INFO] Content: "
                f"{len(result['content'])} karakter"
            )

            # ------------------------------------------------
            # SAVE PROGRESS
            # ------------------------------------------------

            progress_df = pd.DataFrame(
                results,
                columns=output_columns
            )

            progress_df.to_csv(
                OUTPUT_FILE,
                index=False,
                encoding="utf-8-sig"
            )

            print(
                f"[INFO] Progress tersimpan: "
                f"{len(progress_df)} artikel"
            )

            # Jeda antar artikel
            time.sleep(3)

    finally:

        print(
            "\n[INFO] Menutup browser..."
        )

        driver.quit()

    # --------------------------------------------------------
    # FINAL DATA
    # --------------------------------------------------------

    result_df = pd.DataFrame(
        results,
        columns=output_columns
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    success_count = (
        result_df["content_status"]
        == "SUCCESS"
    ).sum()

    blocked_count = (
        result_df["content_status"]
        == "BLOCKED"
    ).sum()

    failed_count = (
        result_df["content_status"]
        == "FAILED"
    ).sum()

    print("\n" + "=" * 70)
    print("CONTENT SCRAPING SELESAI")
    print("=" * 70)

    print(
        f"Artikel diproses : "
        f"{len(result_df)}"
    )

    print(
        f"SUCCESS         : "
        f"{success_count}"
    )

    print(
        f"BLOCKED         : "
        f"{blocked_count}"
    )

    print(
        f"FAILED          : "
        f"{failed_count}"
    )

    print(
        f"Output          : "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()