from __future__ import annotations

import argparse
import hashlib
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
import pytz

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========================== CONFIG ==========================
TARGET_YEAR = 2026
LOCAL_TZ = pytz.timezone("Asia/Jakarta")
MAX_PAGES_PER_CHANNEL = 1  # not a 10-article limit
OLD_ONLY_PAGES_TO_STOP = 2
EMPTY_PAGES_TO_STOP = 2
REQUEST_DELAY_SECONDS = 0.35
OUTPUT_FILE = Path("data/raw/detik_sector3_raw.csv")

CHANNELS = [
    {
        "channel": "Security",
        "index_url": "https://inet.detik.com/security/indeks",
        "article_sections": {"security"},
    },
    {
        "channel": "Business & Policy",
        "index_url": "https://inet.detik.com/business/indeks",
        "article_sections": {"business"}, 
    },
    {
        "channel": "Telecommunication",
        "index_url": "https://inet.detik.com/telecommunication/indeks",
        "article_sections": {"telecommunication"},
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

COLUMNS = [
    "article_id", "title", "url", "published_at", "channel", "source",
    "content", "content_status", "scraped_at",
]

MONTHS = {
    "januari": "January", "jan": "Jan", "februari": "February", "feb": "Feb",
    "maret": "March", "mar": "Mar", "april": "April", "apr": "Apr",
    "mei": "May", "may": "May", "juni": "June", "jun": "Jun",
    "juli": "July", "jul": "Jul", "agustus": "August", "agu": "Aug",
    "agt": "Aug", "september": "September", "sep": "Sep",
    "oktober": "October", "okt": "Oct", "november": "November", "nov": "Nov",
    "desember": "December", "des": "Dec",
}
WEEKDAY_RE = re.compile(
    r"\b(senin|selasa|rabu|kamis|jumat|sabtu|minggu)\b[,]?", re.I
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
DATE_SHAPE_RE = re.compile(
    r"(?:\b\d{1,2}\s+[A-Za-z]{3,9}\s+(?:19|20)\d{2}\b)"
    r"|(?:\b[A-Za-z]{3,9}\s+\d{1,2},?\s+(?:19|20)\d{2}\b)"
    r"|(?:\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b)"
    r"|(?:\b(?:19|20)\d{2}-\d{1,2}-\d{1,2}\b)", re.I
)


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3, connect=3, read=2, backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}), raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def text_of(node) -> str:
    return clean_text(node.get_text(" ", strip=True)) if node else ""


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    path = re.sub(r"/+", "/", parts.path).rstrip("/")
    # Strip query/tracking parameters and fragments for stable deduplication.
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def localize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = LOCAL_TZ.localize(value)
    return value.astimezone(LOCAL_TZ)


def parse_datetime(value: str | None) -> datetime | None:
    """Parse publish dates but avoid guessing a date from arbitrary article text."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    # Relative labels are only used as hints from index cards.
    relative = re.search(
        r"(\d+)\s*(menit|jam|hari|minggu)\s*(yang\s*lalu|lalu)",
        raw, flags=re.I,
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2).lower()
        delta = {
            "menit": timedelta(minutes=amount), "jam": timedelta(hours=amount),
            "hari": timedelta(days=amount), "minggu": timedelta(weeks=amount),
        }[unit]
        return datetime.now(LOCAL_TZ) - delta
    if re.search(r"\bkemarin\b", raw, flags=re.I):
        return datetime.now(LOCAL_TZ) - timedelta(days=1)

    normalized = raw
    for old, new in sorted(MONTHS.items(), key=lambda x: -len(x[0])):
        normalized = re.sub(rf"\b{re.escape(old)}\b", new, normalized, flags=re.I)
    normalized = WEEKDAY_RE.sub("", normalized)
    normalized = re.sub(r"\bWIB\b", "+0700", normalized, flags=re.I)
    normalized = re.sub(r"\bWITA\b", "+0800", normalized, flags=re.I)
    normalized = re.sub(r"\bWIT\b", "+0900", normalized, flags=re.I)

    # Require an explicit year and date shape; don't infer a date from numbers in a title.
    if not YEAR_RE.search(normalized) or not DATE_SHAPE_RE.search(normalized):
        return None
    try:
        return localize_datetime(date_parser.parse(normalized, fuzzy=True, dayfirst=True))
    except (ValueError, TypeError, OverflowError):
        return None


def listing_date_hint(anchor) -> datetime | None:
    """Try to obtain a date from a listing card before fetching its article page."""
    current = anchor
    for _ in range(6):
        if current is None:
            break
        for node in current.select('time[datetime], time, [class*="date"], [class*="time"]')[:8]:
            value = node.get("datetime") or node.get("content") or text_of(node)
            parsed = parse_datetime(value)
            if parsed and 2000 <= parsed.year <= 2100:
                return parsed
        parent_text = text_of(current)
        if len(parent_text) <= 900:
            parsed = parse_datetime(parent_text)
            if parsed and 2000 <= parsed.year <= 2100:
                return parsed
        current = current.parent
    return None


def extract_article_links(soup: BeautifulSoup, article_sections: set[str]) -> list[dict]:
    found: dict[str, dict] = {}
    for anchor in soup.find_all("a", href=True):
        url = normalize_url(urljoin("https://inet.detik.com/", anchor.get("href", "")))
        parts = urlsplit(url)
        if parts.netloc.lower() not in {"inet.detik.com", "www.inet.detik.com"}:
            continue
        path_parts = [part for part in parts.path.split("/") if part]
        if len(path_parts) < 2 or path_parts[0].lower() not in article_sections:
            continue
        if not re.search(r"/d-\d+", parts.path):
            continue
        title = text_of(anchor)
        if len(title) < 8 or url in found:
            continue
        found[url] = {
            "url": url,
            "listing_title": title,
            "listing_date": listing_date_hint(anchor),
        }
    return list(found.values())


def article_publish_datetime(soup: BeautifulSoup) -> datetime | None:
    selectors = [
        'meta[property="article:published_time"]',
        'meta[property="og:article:published_time"]',
        'meta[name="publishdate"]', 'meta[name="publish_date"]',
        'meta[name="pubdate"]', 'meta[name="date"]',
        'meta[itemprop="datePublished"]', '[itemprop="datePublished"][content]',
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            parsed = parse_datetime(node.get("content") or node.get("datetime") or text_of(node))
            if parsed:
                return parsed

    for selector in (
        "time[datetime]", "time", ".detail__date", ".date",
        ".detail-date", ".media__date", ".detail__info",
    ):
        for node in soup.select(selector)[:4]:
            parsed = parse_datetime(node.get("datetime") or text_of(node))
            if parsed and 2000 <= parsed.year <= 2100:
                return parsed
    return None


def extract_article_content(soup: BeautifulSoup) -> str:
    candidates = []
    for selector in (".detail__body-text", ".itp_bodycontent", ".detail__body", "article"):
        for original in soup.select(selector)[:3]:
            node = BeautifulSoup(str(original), "html.parser")
            for unwanted in node.select(
                "script, style, iframe, noscript, figure, .detail__media, "
                ".detail__date, .detail__info, .detail__related, .detail__body-tag, "
                ".parallax, .ads, .ad-container, .detail__author, .video__wrap"
            ):
                unwanted.decompose()
            paragraphs = [
                clean_text(p.get_text(" ", strip=True))
                for p in node.select("p")
            ]
            body = "\n".join(p for p in paragraphs if len(p) > 25)
            if not body:
                body = clean_text(node.get_text(" ", strip=True))
            if body:
                candidates.append(body)
    return max(candidates, key=len) if candidates else ""


def fetch_article(session: requests.Session, candidate: dict) -> dict:
    url = candidate["url"]
    response = session.get(url, timeout=(10, 30))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = ""
    for selector in (
        'meta[property="og:title"]', 'meta[name="twitter:title"]',
        "h1.detail__title", "h1",
    ):
        node = soup.select_one(selector)
        if node:
            title = node.get("content") or text_of(node)
            if title:
                break
    title = re.sub(r"\s*[|–-]\s*detikInet\s*$", "", title, flags=re.I).strip()
    title = title or candidate["listing_title"]

    published = article_publish_datetime(soup) or candidate["listing_date"]
    if published is None:
        return {"published_dt": None, "record": None}
    if published.year != TARGET_YEAR:
        return {"published_dt": published, "record": None}

    content = extract_article_content(soup)
    content_status = "SUCCESS" if len(content) >= 200 else ("PARTIAL" if content else "EMPTY")
    record = {
        "article_id": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        "title": title,
        "url": url,
        "published_at": published.strftime("%Y-%m-%d %H:%M:%S"),
        "channel": "",
        "source": "Detik.com",
        "content": content,
        "content_status": content_status,
        "scraped_at": datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }
    return {"published_dt": published, "record": record}


def scrape_channel(session: requests.Session, config: dict) -> list[dict]:
    name = config["channel"]
    index_url = config["index_url"]
    sections = config["article_sections"]
    records: list[dict] = []
    seen_urls: set[str] = set()
    seen_page_signatures: set[str] = set()
    old_streak = 0
    empty_streak = 0

    print(f"\n{'=' * 68}\n[CHANNEL] {name}\n[INDEX] {index_url}\n{'=' * 68}")

    for page in range(1, MAX_PAGES_PER_CHANNEL + 1):
        page_url = f"{index_url}?page={page}"
        print(f"\n[INFO] Halaman {page}: {page_url}")
        try:
            response = session.get(page_url, timeout=(10, 30))
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[WARN] Gagal membuka halaman indeks: {exc}")
            empty_streak += 1
            if empty_streak >= EMPTY_PAGES_TO_STOP:
                print("[STOP] Dua halaman indeks berturut-turut gagal.")
                break
            time.sleep(REQUEST_DELAY_SECONDS * 2)
            continue

        candidates = extract_article_links(BeautifulSoup(response.text, "html.parser"), sections)
        print(f"[INFO] Kandidat artikel: {len(candidates)}")

        # If pagination serves the exact same URL set again, stop instead of
        # crawling the same listing hundreds of times (seen on some Detik pages).
        if candidates:
            unique_page_urls = sorted({item["url"] for item in candidates})
            page_signature = hashlib.sha256(
                "\n".join(unique_page_urls).encode("utf-8")
            ).hexdigest()
            if page_signature in seen_page_signatures:
                print(
                    "[STOP] Halaman mengembalikan kumpulan URL yang sama seperti "
                    "halaman sebelumnya yang sudah diproses. Paginasi dihentikan "
                    "agar tidak mengulang hasil yang sama."
                )
                break
            seen_page_signatures.add(page_signature)

        if not candidates:
            empty_streak += 1
            if empty_streak >= EMPTY_PAGES_TO_STOP:
                print("[STOP] Dua halaman berturut-turut tidak berisi kandidat artikel.")
                break
            time.sleep(REQUEST_DELAY_SECONDS)
            continue
        empty_streak = 0

        valid_dates = 0
        old_articles = 0
        target_articles = 0
        unknown_dates = 0

        for item in candidates:
            url = item["url"]
            listing_dt = item["listing_date"]

            # Listing pages are newest-first; dated pre-2026 cards need no article fetch.
            if listing_dt and listing_dt.year < TARGET_YEAR:
                valid_dates += 1
                old_articles += 1
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                parsed = fetch_article(session, item)
            except requests.RequestException as exc:
                print(f"[WARN] Artikel gagal: {url} | {exc}")
                unknown_dates += 1
                time.sleep(REQUEST_DELAY_SECONDS)
                continue
            except Exception as exc:
                print(f"[WARN] Gagal memproses artikel: {url} | {exc}")
                unknown_dates += 1
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            published = parsed["published_dt"]
            if published is None:
                unknown_dates += 1
            else:
                valid_dates += 1
                if published.year < TARGET_YEAR:
                    old_articles += 1
                elif published.year == TARGET_YEAR:
                    target_articles += 1
                    if parsed["record"]:
                        parsed["record"]["channel"] = name
                        records.append(parsed["record"])
            time.sleep(REQUEST_DELAY_SECONDS)

        print(
            f"[INFO] Tahun {TARGET_YEAR}: {target_articles} | sebelum {TARGET_YEAR}: "
            f"{old_articles} | tanggal tidak diketahui: {unknown_dates} | "
            f"total tahun {TARGET_YEAR} kanal ini: {len(records)}"
        )

        if (
            valid_dates > 0 and old_articles == valid_dates
            and target_articles == 0 and unknown_dates == 0
        ):
            old_streak += 1
            print(f"[INFO] Halaman lama beruntun: {old_streak}")
        else:
            old_streak = 0
        if old_streak >= OLD_ONLY_PAGES_TO_STOP:
            print(f"[STOP] Dua halaman berturut-turut hanya berisi artikel sebelum {TARGET_YEAR}.")
            break
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"[RESULT] {name}: {len(records)} artikel tahun {TARGET_YEAR}")
    return records


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scraper Detik.com Sector 3 dengan filter tahun publikasi."
    )
    parser.add_argument(
        "--channel",
        choices=[config["channel"] for config in CHANNELS],
        help="Jalankan satu kanal saja, misalnya: --channel \"Business & Policy\". "
             "Tanpa opsi ini, semua kanal diproses.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_channels = [
        config for config in CHANNELS
        if args.channel is None or config["channel"] == args.channel
    ]

    print("=" * 68)
    print("DETIK.COM SCRAPER - SECTOR 3")
    print(f"Tahun target: {TARGET_YEAR}")
    print(f"Kanal yang diproses: {', '.join(c['channel'] for c in selected_channels)}")
    print(f"Batas teknis halaman per kanal: {MAX_PAGES_PER_CHANNEL}")
    print("Tidak ada batas tetap 10 artikel; URL halaman yang berulang akan dihentikan.")
    print("Hasil baru akan digabung dengan CSV lama agar kanal lain tidak hilang saat uji satu kanal.")
    print("=" * 68)

    all_records: list[dict] = []
    failed_channels: list[str] = []
    with build_session() as session:
        for config in selected_channels:
            try:
                all_records.extend(scrape_channel(session, config))
            except Exception as exc:
                print(f"[ERROR] Kanal {config['channel']} gagal: {exc}")
                failed_channels.append(config["channel"])
            time.sleep(1.0)

    if not all_records:
        print("\n[WARNING] Tidak ada artikel baru yang berhasil dikumpulkan.")
        if failed_channels:
            print(f"[WARNING] Kanal gagal: {failed_channels}")
        print("[INFO] CSV yang sudah ada tidak ditimpa.")
        return

    fresh_df = pd.DataFrame(all_records, columns=COLUMNS)
    fresh_df["published_at"] = pd.to_datetime(fresh_df["published_at"], errors="coerce")
    fresh_df = fresh_df[
        fresh_df["published_at"].notna()
        & (fresh_df["published_at"].dt.year == TARGET_YEAR)
    ].copy()

    # Load existing raw rows first, then append fresh rows so refreshed data
    # wins for duplicate URLs while records from unselected channels are retained.
    existing_df = pd.DataFrame(columns=COLUMNS)
    if OUTPUT_FILE.exists():
        try:
            existing_df = pd.read_csv(
                OUTPUT_FILE,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
            )
            existing_df = existing_df.reindex(columns=COLUMNS, fill_value="")
            existing_df["published_at"] = pd.to_datetime(
                existing_df["published_at"], errors="coerce"
            )
            existing_df = existing_df[
                existing_df["published_at"].notna()
                & (existing_df["published_at"].dt.year == TARGET_YEAR)
            ].copy()
        except Exception as exc:
            print(f"[WARN] CSV raw lama tidak dapat dibaca, tidak dipakai untuk merge: {exc}")
            existing_df = pd.DataFrame(columns=COLUMNS)

    existing_count = len(existing_df)
    combined_df = pd.concat([existing_df, fresh_df], ignore_index=True)
    combined_df["published_at"] = pd.to_datetime(
        combined_df["published_at"], errors="coerce"
    )
    combined_df = combined_df[
        combined_df["published_at"].notna()
        & (combined_df["published_at"].dt.year == TARGET_YEAR)
        & combined_df["url"].astype(str).str.startswith("https://inet.detik.com/")
    ].copy()
    combined_df = combined_df.drop_duplicates(subset=["url"], keep="last")
    combined_df = combined_df.sort_values(
        "published_at", ascending=False
    ).reset_index(drop=True)
    combined_df["published_at"] = combined_df["published_at"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 68)
    print("SCRAPING DETIK.COM SELESAI")
    print("=" * 68)
    print(f"CSV output                 : {OUTPUT_FILE.resolve()}")
    print(f"Artikel baru dari run ini  : {len(fresh_df)}")
    print(f"Baris lama sebelum merge   : {existing_count}")
    print(f"Total artikel tersimpan    : {len(combined_df)}")
    print(f"URL unik                   : {combined_df['url'].nunique()}")
    print(f"Tanggal terawal            : {combined_df['published_at'].min()}")
    print(f"Tanggal terbaru            : {combined_df['published_at'].max()}")
    print("\nDistribusi kanal:\n" + combined_df["channel"].value_counts().to_string())
    print("\nDistribusi content_status:\n" + combined_df["content_status"].value_counts().to_string())
    print("\nPreview:\n" + combined_df[["title", "published_at", "channel", "content_status"]].head(15).to_string(index=False))
    if failed_channels:
        print(f"\n[WARNING] Kanal gagal: {failed_channels}")


if __name__ == "__main__":
    main()
