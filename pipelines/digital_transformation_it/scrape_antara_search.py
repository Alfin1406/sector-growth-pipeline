
import argparse
import csv
import hashlib
import logging
import re
import time

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup


# ============================================================
# 1. CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "antara_search_raw.csv"

WIB = timezone(timedelta(hours=7))

START_DATE = datetime(
    2026, 1, 1, 0, 0, 0,
    tzinfo=WIB
)

REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.5
MAX_RETRIES = 3

BASE_URL = "https://www.antaranews.com/search"

SEARCH_SOURCES = {
    "Cloud Enterprise": "Cloud Enterprise",
    "Cyber Security": "Cyber security",
    "Digital Transformation": "digital Transformation",
    "Enterprise Software": "Enterprise Software",
}

MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}

DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+"
    r"(Januari|Februari|Maret|April|Mei|Juni|"
    r"Juli|Agustus|September|Oktober|November|Desember)"
    r"\s+(\d{4})\b",
    re.IGNORECASE,
)

RELATIVE_PATTERN = re.compile(
    r"(\d+)\s+"
    r"(detik|menit|jam|hari|minggu|bulan|tahun)"
    r"\s+lalu",
    re.IGNORECASE,
)


# ============================================================
# 2. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


# ============================================================
# 3. HTTP SESSION
# ============================================================

def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
    })

    return session


# ============================================================
# 4. FETCH SEARCH PAGE
# ============================================================

def fetch_page(session, query, page):

    params = {
        "page": page,
        "q": query,
    }

    url = f"{BASE_URL}?{urlencode(params)}"

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            return soup, url

        except requests.RequestException as error:

            logger.warning(
                "Request gagal: query=%s page=%s attempt=%s/%s: %s",
                query,
                page,
                attempt,
                MAX_RETRIES,
                error,
            )

            # Jangan mencoba melewati pembatasan akses
            if response_status_is_restricted(error):
                logger.error("Akses dibatasi server. Proses dihentikan.")
                return None, url

            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)

    return None, url


def response_status_is_restricted(error):

    response = getattr(error, "response", None)

    return (
        response is not None
        and response.status_code in (401, 403, 429)
    )


# ============================================================
# 5. TEXT NORMALIZATION
# ============================================================

def clean_text(value):

    if not value:
        return ""

    text = value.get_text(" ", strip=True) if hasattr(
        value, "get_text"
    ) else str(value)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# 6. DATE PARSING
# ============================================================

def parse_publication_date(text, date_attribute=None):

    now = datetime.now(WIB)

    # Priority 1: machine-readable datetime
    if date_attribute:

        raw = str(date_attribute).strip()

        try:
            parsed = datetime.fromisoformat(
                raw.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=WIB)

            return parsed.astimezone(WIB)

        except ValueError:
            pass

    text = str(text or "").strip().lower()

    # Priority 2: relative time
    relative = RELATIVE_PATTERN.search(text)

    if relative:

        amount = int(relative.group(1))
        unit = relative.group(2).lower()

        if unit == "detik":
            return now - timedelta(seconds=amount)

        if unit == "menit":
            return now - timedelta(minutes=amount)

        if unit == "jam":
            return now - timedelta(hours=amount)

        if unit == "hari":
            return now - timedelta(days=amount)

        if unit == "minggu":
            return now - timedelta(weeks=amount)

        if unit == "bulan":
            return now - timedelta(days=amount * 30)

        if unit == "tahun":
            return now - timedelta(days=amount * 365)

    # Priority 3: Kemarin / hari ini
    if "kemarin" in text or "hari ini" in text:

        clock = re.search(r"(\d{1,2}):(\d{2})", text)

        base_date = now.date()

        if "kemarin" in text:
            base_date -= timedelta(days=1)

        hour = int(clock.group(1)) if clock else 0
        minute = int(clock.group(2)) if clock else 0

        return datetime(
            base_date.year,
            base_date.month,
            base_date.day,
            hour,
            minute,
            tzinfo=WIB,
        )

    # Priority 4: Absolute Indonesian date
    match = DATE_PATTERN.search(text)

    if match:

        day = int(match.group(1))
        month = MONTHS[match.group(2).lower()]
        year = int(match.group(3))

        clock = re.search(r"(\d{1,2}):(\d{2})", text)

        hour = int(clock.group(1)) if clock else 0
        minute = int(clock.group(2)) if clock else 0

        try:
            return datetime(
                year,
                month,
                day,
                hour,
                minute,
                tzinfo=WIB,
            )
        except ValueError:
            return None

    return None


# ============================================================
# 7. ARTICLE CARD DETECTION
# ============================================================

def contains_date(text):

    text = str(text or "")

    return bool(
        DATE_PATTERN.search(text)
        or RELATIVE_PATTERN.search(text)
        or re.search(r"\bkemarin\b|\bhari ini\b", text, re.I)
    )


def get_article_card(anchor):

    current = anchor

    for _ in range(7):

        if current is None:
            break

        text = clean_text(current)

        if (
            len(text) <= 2000
            and contains_date(text)
        ):
            return current

        current = current.parent

    return anchor.parent


# ============================================================
# 8. EXTRACT TITLE, DATE, SUMMARY
# ============================================================

def extract_title(anchor):

    title = clean_text(anchor)

    if not title:

        image = anchor.find("img")

        if image:
            title = image.get("alt", "").strip()

    return title


def extract_date(card):

    # Check machine-readable datetime first
    for node in card.find_all(True):

        date_attr = node.get("datetime")

        if date_attr:

            parsed = parse_publication_date(
                "",
                date_attr,
            )

            if parsed:
                return parsed

    # Fallback to visible text
    return parse_publication_date(
        clean_text(card)
    )


def extract_summary(card, title):

    paragraphs = card.find_all("p")

    for paragraph in paragraphs:

        text = clean_text(paragraph)

        if len(text) < 35:
            continue

        if text.casefold() == title.casefold():
            continue

        if contains_date(text):
            continue

        return text[:1500]

    return ""


# ============================================================
# 9. ARTICLE ID
# ============================================================

def generate_article_id(url):

    match = re.search(
        r"/berita/(\d+)",
        urlparse(url).path,
    )

    if match:
        return f"antara_{match.group(1)}"

    digest = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]

    return f"antara_{digest}"


# ============================================================
# 10. PAGINATION
# ============================================================

def has_next_page(soup, current_page, query):

    for anchor in soup.find_all("a", href=True):

        href = urljoin(
            BASE_URL,
            anchor["href"],
        )

        parsed = urlparse(href)
        params = parse_qs(parsed.query)

        if not parsed.path.rstrip("/").endswith("/search"):
            continue

        page_value = params.get("page", ["1"])[0]
        query_value = params.get("q", [""])[0]

        try:
            next_page = int(page_value)
        except ValueError:
            continue

        if (
            next_page == current_page + 1
            and query_value.casefold() == query.casefold()
        ):
            return True

    return False


# ============================================================
# 11. EXTRACT SEARCH RESULTS
# ============================================================


def extract_page_articles(soup, topic, query, page):

    results = {}
    now = datetime.now(WIB)

    # Satu kartu = satu artikel
    cards = soup.select(
        "div.card__post.card__post-list"
    )

    skipped_title = 0
    skipped_url = 0
    skipped_date = 0
    skipped_period = 0
    empty_summary = 0

    for card in cards:

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title_node = card.select_one(
            ".card__post__title h2.h5"
        )

        if not title_node:
            skipped_title += 1
            continue

        title = clean_text(title_node)

        if not title:
            skipped_title += 1
            continue

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        link_node = card.select_one(
            ".card__post__title a[href*='/berita/']"
        )

        if not link_node:
            skipped_url += 1
            continue

        url = urljoin(
            BASE_URL,
            link_node.get("href", "")
        )

        parsed_url = urlparse(url)

        if (
            parsed_url.hostname not in (
                "www.antaranews.com",
                "antaranews.com",
            )
            or not parsed_url.path.startswith("/berita/")
        ):
            skipped_url += 1
            continue

        # ----------------------------------------------------
        # PUBLISHED DATE
        # ----------------------------------------------------

        date_node = card.select_one(
            ".card__post__author-info span.text-dark.text-capitalize"
        )

        if not date_node:
            skipped_date += 1
            continue

        published_text = clean_text(date_node)

        published = parse_publication_date(
            published_text
        )

        if published is None:
            skipped_date += 1
            continue

        # ----------------------------------------------------
        # DATE FILTER
        # ----------------------------------------------------

        if published < START_DATE or published > now:
            skipped_period += 1
            continue

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary_node = card.select_one(
            ".card__post__content p"
        )

        summary = clean_text(summary_node)

        if not summary:
            empty_summary += 1

        # ----------------------------------------------------
        # BUILD ARTICLE
        # ----------------------------------------------------

        article = {
            "article_id": generate_article_id(url),
            "source": "ANTARA News",

            # Ini asal pencarian, bukan hasil klasifikasi.
            "channel": "ANTARA Search",

            "title": title,
            "url": url,
            "published_at": published.isoformat(),

            # Tidak mengklaim ringkasan sebagai konten lengkap.
            "content": "",
            "content_status": (
                "summary_only" if summary
                else "metadata_only"
            ),

            "scraped_at": now.isoformat(),
            "summary": summary,

            # Klasifikasi aktual dilakukan di tahap Filtering.
            "topic_candidate": "",
            "classification_status": "unclassified",

            # Menyimpan asal kata kunci pencarian.
            "search_query": query,
            "search_page": page,
        }

        results[url] = article

    logger.info(
        "Page %s | Kartu: %s | Valid: %s | "
        "Judul kosong: %s | URL tidak valid: %s | "
        "Tanggal tidak terbaca: %s | "
        "Di luar periode: %s | Ringkasan kosong: %s",
        page,
        len(cards),
        len(results),
        skipped_title,
        skipped_url,
        skipped_date,
        skipped_period,
        empty_summary,
    )

    return list(results.values()), skipped_date, skipped_period 


# ============================================================
# 12. SCRAPE ONE QUERY
# ============================================================

def scrape_query(
    session,
    topic,
    query,
    max_pages,
):

    logger.info("=" * 60)
    logger.info("TOPIC: %s", topic)
    logger.info("QUERY: %s", query)
    logger.info("=" * 60)

    collected = []
    seen_page_signatures = set()

    for page in range(1, max_pages + 1):

        soup, page_url = fetch_page(
            session,
            query,
            page,
        )

        if soup is None:
            break

        page_articles, skipped_date, skipped_period = (
            extract_page_articles(
                soup,
                topic,
                query,
                page,
            )
        )

        signature = tuple(
            article["url"]
            for article in page_articles
        )

        # Stop if repeated page
        if signature and signature in seen_page_signatures:

            logger.warning(
                "Halaman berulang ditemukan: %s",
                page,
            )
            break

        seen_page_signatures.add(signature)

        collected.extend(page_articles)

        logger.info(
            "Page %s | Artikel valid: %s | "
            "Tanggal tidak terbaca: %s | Di luar periode: %s",
            page,
            len(page_articles),
            skipped_date,
            skipped_period,
        )

        logger.info("URL: %s", page_url)

        # Stop when the next page is not available
        if not has_next_page(soup, page, query):

            logger.info(
                "Pagination selesai pada page %s",
                page,
            )
            break

        # All parsed results on this page are older than the cutoff
        dates = [
            datetime.fromisoformat(row["published_at"])
            for row in page_articles
        ]

        if dates and max(dates) < START_DATE:

            logger.info(
                "Artikel pada halaman ini sudah sebelum cutoff."
            )
            break

        time.sleep(REQUEST_DELAY)

    logger.info(
        "Total hasil query %s: %s",
        topic,
        len(collected),
    )

    return collected


# ============================================================
# 13. DEDUPLICATION
# ============================================================

def deduplicate_articles(articles):

    grouped = {}

    for article in articles:

        key = article["url"].rstrip("/").lower()

        if key not in grouped:

            grouped[key] = article.copy()

        else:

            existing = grouped[key]

            channels = existing["channel"].split("; ")

            if article["channel"] not in channels:
                channels.append(article["channel"])

            existing["channel"] = "; ".join(channels)

            queries = existing["search_query"].split("; ")

            if article["search_query"] not in queries:
                queries.append(article["search_query"])

            existing["search_query"] = "; ".join(queries)

            # Keep the richer visible summary
            if len(article["summary"]) > len(existing["summary"]):
                existing["summary"] = article["summary"]

    return list(grouped.values())


# ============================================================
# 14. MERGE PREVIOUS SEARCH CSV
# ============================================================

def merge_existing(new_articles):

    if not OUTPUT_FILE.exists():
        return new_articles

    with OUTPUT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        old_articles = list(csv.DictReader(file))

    combined = {}

    for row in old_articles + new_articles:

        key = row["url"].strip().rstrip("/").lower()

        if key not in combined:
            combined[key] = row

        else:

            existing = combined[key]

            channels = set(
                filter(
                    None,
                    existing.get("channel", "").split("; "),
                )
            )

            channels.update(
                filter(
                    None,
                    row.get("channel", "").split("; "),
                )
            )

            existing["channel"] = "; ".join(sorted(channels))

            if len(row.get("summary", "")) > len(
                existing.get("summary", "")
            ):
                existing["summary"] = row["summary"]

    return list(combined.values())


# ============================================================
# 15. SAVE CSV
# ============================================================

CSV_FIELDS = [
    "article_id",
    "source",
    "channel",
    "title",
    "url",
    "published_at",
    "content",
    "content_status",
    "scraped_at",
    "summary",
    "topic_candidate",
    "classification_status",
    "search_query",
    "search_page",
]


def save_csv(articles, merge=False):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if merge:
        articles = merge_existing(articles)

    articles.sort(
        key=lambda row: row["published_at"],
        reverse=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(articles)

    logger.info("CSV tersimpan: %s", OUTPUT_FILE)

    return articles


# ============================================================
# 16. REPORT
# ============================================================

def print_report(articles):

    logger.info("=" * 60)
    logger.info("ANTARA SEARCH SCRAPING REPORT")
    logger.info("=" * 60)

    logger.info("Total artikel unik: %s", len(articles))

    logger.info(
        "Ringkasan kosong: %s",
        sum(
            not row.get("summary", "").strip()
            for row in articles
        ),
    )

   
    logger.info("\nDISTRIBUSI ASAL PENCARIAN")

    for topic, query in SEARCH_SOURCES.items():

        count = sum(
            query in row.get("search_query", "").split("; ")
            for row in articles
        )

        logger.info("%-25s : %s", topic, count) 

    logger.info("\nRENTANG PUBLIKASI")

    if articles:

        dates = [
            datetime.fromisoformat(row["published_at"])
            for row in articles
        ]

        logger.info("Terlama : %s", min(dates))
        logger.info("Terbaru : %s", max(dates))

    logger.info("\nPREVIEW ARTIKEL")

    for row in articles[:10]:

        logger.info(
            "[%s] %s",
            row["channel"],
            row["title"],
        )


# ============================================================
# 17. MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="ANTARA four-topic search metadata collector"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help="Maksimum halaman per topik. Default 2 untuk uji awal.",
    )

    parser.add_argument(
        "--merge",
        action="store_true",
        help="Gabungkan dengan hasil pencarian ANTARA sebelumnya.",
    )

    args = parser.parse_args()

    if args.max_pages < 1:
        raise ValueError("--max-pages minimal 1.")

    logger.info("=" * 60)
    logger.info("SECTOR 3 - ANTARA SEARCH SCRAPER")
    logger.info("=" * 60)

    logger.info("Tanggal mulai: %s", START_DATE.date())
    logger.info("Jumlah topik: %s", len(SEARCH_SOURCES))
    logger.info("Maksimum halaman per topik: %s", args.max_pages)

    session = create_session()

    raw_articles = []

    try:

        for topic, query in SEARCH_SOURCES.items():

            articles = scrape_query(
                session,
                topic,
                query,
                args.max_pages,
            )

            raw_articles.extend(articles)

            time.sleep(REQUEST_DELAY)

    finally:
        session.close()

    unique_articles = deduplicate_articles(
        raw_articles
    )

    final_articles = save_csv(
        unique_articles,
        merge=args.merge,
    )

    print_report(final_articles)

    logger.info("=" * 60)
    logger.info("ANTARA SEARCH SCRAPING SELESAI")
    logger.info("=" * 60)


if __name__ == "__main__":
    main() 
 