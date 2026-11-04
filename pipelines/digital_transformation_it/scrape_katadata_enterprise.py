
"""
Scraper berita Katadata berbasis Search API untuk riset Sector 3.

Fitur:
- Pencarian otomatis dengan beberapa keyword.
- Pagination dan deduplikasi berdasarkan URL.
- Filter tanggal publikasi tahun 2026.
- Klasifikasi awal lima kategori Sector 3.
- Output CSV mempertahankan kolom utama scraper lama.

Catatan:
Klasifikasi berbasis aturan merupakan penyaringan awal dan tetap
perlu dievaluasi sebelum data digunakan untuk analisis final.
"""

from __future__ import annotations

import html
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 1. KONFIGURASI
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "katadata_enterprise_raw.csv"
)

API_URL = "https://api-search.katadata.co.id/search"

TARGET_YEAR = 2026
SEARCH_LIMIT = 10
MAX_PAGES = 3

REQUEST_DELAY_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 30

SEARCH_KEYWORDS = [
    "serangan siber",
    "kebocoran data",
    "AI perusahaan",
    "ransomware",
    "layanan cloud",
]

API_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

SECTOR3_TOPICS = {
    "Enterprise Software",
    "Cyber Security",
    "Digital Transformation",
    "Cloud Enterprise",
    "Enterprise Data & AI",
}


# ============================================================
# 2. KEYWORD ENTERPRISE SOFTWARE
# ============================================================

ENTERPRISE_SOFTWARE_PHRASES = [
    "enterprise software",
    "enterprise application",
    "enterprise applications",
    "aplikasi enterprise",
    "sistem enterprise",
    "enterprise resource planning",
    "software erp",
    "sistem erp",
    "implementasi erp",
    "erp perusahaan",
    "sap s/4hana",
    "sap hana",
    "sap business one",
    "oracle netsuite",
    "netsuite",
    "crm software",
    "software crm",
    "sistem crm",
    "customer relationship management",
    "hris",
    "hcm",
    "saas perusahaan",
    "business software",
    "software bisnis",
    "aplikasi bisnis perusahaan",
    "aplikasi procurement",
    "sistem procurement",
    "supply chain management",
    "scm software",
]


# ============================================================
# 3. MEMBUAT SESSION HTTP
# ============================================================

def create_session() -> requests.Session:
    """Membuat session HTTP dengan retry terbatas."""

    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# ============================================================
# 4. NORMALISASI TEKS
# ============================================================

def normalize_text(value: Any) -> str:
    """Membersihkan teks HTML, spasi, dan nilai kosong."""

    if value is None:
        return ""

    text = html.unescape(str(value))
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# 5. KLASIFIKASI ENTERPRISE SOFTWARE
# ============================================================

def is_enterprise_software(
    title: str,
    content: str,
) -> bool:
    """Mendeteksi indikasi perangkat lunak perusahaan."""

    title_text = normalize_text(title).lower()
    content_text = normalize_text(content).lower()
    combined = f"{title_text} {content_text}"

    # Mencegah ERP jalan berbayar dianggap software perusahaan.
    road_pricing_contexts = [
        "electronic road pricing",
        "jalan berbayar",
        "ojek online",
        "driver ojol",
        "pengemudi ojek",
        "tarif ojol",
    ]

    if any(term in title_text for term in road_pricing_contexts):
        explicit_erp_software = any(
            term in combined
            for term in [
                "enterprise resource planning",
                "software erp",
                "sistem erp",
                "implementasi erp",
            ]
        )

        if not explicit_erp_software:
            return False

    workplace_apps = [
        "chatgpt work",
        "microsoft outlook",
        "aplikasi kerja perusahaan",
        "aplikasi bisnis perusahaan",
    ]

    if any(term in title_text for term in workplace_apps):
        return True

    return any(
        term in combined
        for term in ENTERPRISE_SOFTWARE_PHRASES
    )


# ============================================================
# 6. KLASIFIKASI LIMA KATEGORI SECTOR 3
# ============================================================

def classify_sector3(
    title: str,
    content: str,
) -> dict[str, str]:
    """
    Mengklasifikasikan artikel berdasarkan aturan dan keyword.

    relevance_level:
    - Relevan
    - Perlu Tinjau
    - Di Luar Cakupan

    Klasifikasi ini bukan model AI dan tidak menjamin akurasi 100%.
    """

    title_text = normalize_text(title).lower()
    content_text = normalize_text(content).lower()
    combined = f"{title_text} {content_text}"

    # --------------------------------------------------------
    # A. CYBER SECURITY
    # --------------------------------------------------------

    cyber_terms = [
        "serangan siber",
        "keamanan siber",
        "ancaman siber",
        "kebocoran data",
        "data bocor",
        "bocor",
        "hacker",
        "peretas",
        "diretas",
        "ransomware",
        "phishing",
        "backdoor",
        "dibobol",
        "celah keamanan",
        "keamanan ti",
        "platform keamanan",
        "risiko keamanan",
        "risiko serangan",
        "fraud",
        "penipuan",
    ]

    if any(term in title_text for term in cyber_terms):
        review_security = [
            "tips terhindar phishing",
            "data game",
        ]

        if any(term in title_text for term in review_security):
            return {
                "sector3_topic": "Cyber Security",
                "relevance_level": "Perlu Tinjau",
                "classification_confidence": "Sedang",
                "classification_reason": (
                    "Bertema keamanan atau data, tetapi relevansi "
                    "terhadap keamanan organisasi perlu diperiksa."
                ),
            }

        return {
            "sector3_topic": "Cyber Security",
            "relevance_level": "Relevan",
            "classification_confidence": "Tinggi",
            "classification_reason": (
                "Judul mengandung indikator eksplisit ancaman, "
                "insiden, atau pertahanan siber."
            ),
        }

    # --------------------------------------------------------
    # B. ENTERPRISE SOFTWARE
    # --------------------------------------------------------

    if is_enterprise_software(title, content):
        return {
            "sector3_topic": "Enterprise Software",
            "relevance_level": "Relevan",
            "classification_confidence": "Tinggi",
            "classification_reason": (
                "Terdapat istilah software atau aplikasi "
                "yang berkaitan dengan penggunaan bisnis."
            ),
        }

    # --------------------------------------------------------
    # C. CLOUD ENTERPRISE
    # --------------------------------------------------------

    cloud_terms = [
        "cloud",
        "komputasi awan",
        "layanan awan",
    ]

    cloud_context = [
        "perusahaan",
        "layanan",
        "adopsi",
        "migrasi",
        "sistem",
        "operasional",
        "bisnis",
        "gangguan",
        "platform",
        "aplikasi",
        "beban kerja",
    ]

    has_cloud = any(
        term in combined
        for term in cloud_terms
    )

    has_cloud_context = any(
        term in combined
        for term in cloud_context
    )

    if has_cloud and has_cloud_context:
        return {
            "sector3_topic": "Cloud Enterprise",
            "relevance_level": "Perlu Tinjau",
            "classification_confidence": "Sedang",
            "classification_reason": (
                "Artikel membahas cloud, tetapi penggunaan "
                "atau dampak terhadap enterprise perlu diperiksa."
            ),
        }

    # --------------------------------------------------------
    # D. DIGITAL TRANSFORMATION
    # --------------------------------------------------------

    transformation_terms = [
        "transformasi digital",
        "digitalisasi",
        "otomasi bisnis",
        "otomatisasi bisnis",
        "digitalisasi perusahaan",
        "digitalisasi proses bisnis",
        "transformasi bisnis digital",
        "implementasi teknologi",
        "sistem pemerintahan digital",
    ]

    if any(
        term in combined
        for term in transformation_terms
    ):
        return {
            "sector3_topic": "Digital Transformation",
            "relevance_level": "Perlu Tinjau",
            "classification_confidence": "Sedang",
            "classification_reason": (
                "Terdapat indikator transformasi atau digitalisasi. "
                "Periksa apakah fokusnya pada organisasi atau proses bisnis."
            ),
        }

    # --------------------------------------------------------
    # E. ENTERPRISE DATA & AI
    # --------------------------------------------------------

    ai_terms = [
        "artificial intelligence",
        "kecerdasan buatan",
        "generative ai",
        "ai perusahaan",
        "ai untuk bisnis",
        "machine learning",
        "analitik data",
        "analitik bisnis",
        "business intelligence",
        "data analytics",
        "enterprise ai",
    ]

    ai_enterprise_context = [
        "perusahaan",
        "bisnis",
        "operasional",
        "produktivitas",
        "efisiensi",
        "pegawai",
        "organisasi",
        "analisis data",
        "pengambilan keputusan",
        "proses bisnis",
        "layanan",
    ]

    has_ai = any(
        term in combined
        for term in ai_terms
    )

    has_enterprise_context = any(
        term in combined
        for term in ai_enterprise_context
    )

    if has_ai and has_enterprise_context:
        return {
            "sector3_topic": "Enterprise Data & AI",
            "relevance_level": "Perlu Tinjau",
            "classification_confidence": "Sedang",
            "classification_reason": (
                "Artikel membahas AI atau analitik data dengan "
                "indikasi konteks organisasi atau bisnis."
            ),
        }

    # --------------------------------------------------------
    # F. PENANDA BERITA UMUM DI LUAR CAKUPAN
    # --------------------------------------------------------

    out_of_scope_terms = [
        "wall street",
        "saham",
        "emiten",
        "harga saham",
        "indeks saham",
        "kacamata vr",
        "review gadget",
        "spesifikasi ponsel",
        "ponsel terbaru",
        "investor saham",
    ]

    if any(
        term in title_text
        for term in out_of_scope_terms
    ):
        return {
            "sector3_topic": "Di Luar Cakupan",
            "relevance_level": "Di Luar Cakupan",
            "classification_confidence": "Tinggi",
            "classification_reason": (
                "Fokus utama artikel adalah pasar finansial, "
                "investasi saham, gadget, atau produk konsumen."
            ),
        }

    # AI umum tidak langsung dianggap Enterprise Data & AI.
    if (
        "ai" in title_text
        or "kecerdasan buatan" in title_text
        or "artificial intelligence" in title_text
    ):
        return {
            "sector3_topic": "Di Luar Cakupan",
            "relevance_level": "Di Luar Cakupan",
            "classification_confidence": "Sedang",
            "classification_reason": (
                "Berita AI umum tanpa indikasi cukup kuat "
                "tentang penerapan enterprise."
            ),
        }

    # Default: jangan menganggap artikel relevan tanpa bukti.
    return {
        "sector3_topic": "Di Luar Cakupan",
        "relevance_level": "Di Luar Cakupan",
        "classification_confidence": "Rendah",
        "classification_reason": (
            "Tidak ditemukan indikator kuat yang menghubungkan "
            "judul dan isi artikel dengan kategori Sector 3."
        ),
    }


# ============================================================
# 7. MENGAMBIL HASIL PENCARIAN API
# ============================================================

def get_article_urls(
    session: requests.Session,
) -> list[dict[str, Any]]:
    """
    Mengambil hasil dari beberapa keyword dan halaman.

    Nama fungsi dipertahankan agar perubahan terhadap scraper
    lama lebih minimal. Fungsi ini mengembalikan objek artikel,
    bukan sekadar URL.
    """

    articles_by_url: dict[str, dict[str, Any]] = {}

    for keyword in SEARCH_KEYWORDS:
        print(f"\n[INFO] Mencari keyword: {keyword}")

        for page in range(1, MAX_PAGES + 1):
            payload = {
                "q": keyword,
                "source": "katadata",
                "sort": "newest",
                "limit": SEARCH_LIMIT,
                "page": page,
            }

            try:
                response = session.post(
                    API_URL,
                    json=payload,
                    headers=API_HEADERS,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )

                response.raise_for_status()
                data = response.json()

            except (
                requests.RequestException,
                ValueError,
            ) as exc:
                print(
                    f"[WARNING] Pencarian gagal untuk "
                    f"'{keyword}', halaman {page}: {exc}"
                )
                break

            results = (
                data.get("results", [])
                if isinstance(data, dict)
                else []
            )

            if not isinstance(results, list) or not results:
                print(
                    f"[INFO] Tidak ada hasil "
                    f"pada halaman {page}."
                )
                break

            added_this_page = 0

            for raw_article in results:
                if not isinstance(raw_article, dict):
                    continue

                url = normalize_text(
                    raw_article.get("url")
                )

                if not url:
                    continue

                article = dict(raw_article)
                article["_search_keyword"] = keyword

                if url not in articles_by_url:
                    articles_by_url[url] = article
                    added_this_page += 1

                else:
                    # Jika hasil duplikat membawa isi lebih lengkap,
                    # gunakan body atau summary yang lebih panjang.
                    existing = articles_by_url[url]

                    for field in ["body", "summary"]:
                        old_value = normalize_text(
                            existing.get(field)
                        )
                        new_value = normalize_text(
                            article.get(field)
                        )

                        if len(new_value) > len(old_value):
                            existing[field] = article.get(field)

            print(
                f"[INFO] Halaman {page}: "
                f"{len(results)} hasil API, "
                f"{added_this_page} URL baru."
            )

            if len(results) < SEARCH_LIMIT:
                break

            time.sleep(REQUEST_DELAY_SECONDS)

    article_list = list(
        articles_by_url.values()
    )

    print(
        f"\n[INFO] Total URL unik dari API: "
        f"{len(article_list)}"
    )

    return article_list


# ============================================================
# 8. MENGUBAH RESPONS API MENJADI DATAFRAME
# ============================================================

def build_dataframe(
    articles: list[dict[str, Any]],
) -> pd.DataFrame:
    """Membentuk DataFrame dengan kolom utama dan hasil klasifikasi."""

    scraped_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    rows: list[dict[str, Any]] = []

    for article in articles:
        title = normalize_text(
            article.get("title")
        )

        url = normalize_text(
            article.get("url")
        )

        content = normalize_text(
            article.get("body")
        )

        if not content:
            content = normalize_text(
                article.get("summary")
            )

        published_at = article.get(
            "date_publish"
        )

        # Gunakan subkanal jika ada; jika tidak, gunakan kanal utama.
        channel = normalize_text(
            article.get("sub_kanal_name")
            or article.get("kanal_name")
        )

        if not title or not url:
            continue

        classification = classify_sector3(
            title,
            content,
        )

        rows.append(
            {
                # Kolom utama scraper lama.
                "title": title,
                "url": url,
                "published_at": published_at,
                "channel": channel,
                "source": "Katadata",
                "content": content,
                "is_enterprise_software": (
                    is_enterprise_software(
                        title,
                        content,
                    )
                ),
                "scraped_at": scraped_at,

                # Kolom tambahan Sector 3.
                "sector3_topic": (
                    classification["sector3_topic"]
                ),
                "relevance_level": (
                    classification["relevance_level"]
                ),
                "classification_confidence": (
                    classification[
                        "classification_confidence"
                    ]
                ),
                "classification_reason": (
                    classification[
                        "classification_reason"
                    ]
                ),
            }
        )

    columns = [
        "title",
        "url",
        "published_at",
        "channel",
        "source",
        "content",
        "is_enterprise_software",
        "scraped_at",
        "sector3_topic",
        "relevance_level",
        "classification_confidence",
        "classification_reason",
    ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


# ============================================================
# 9. FILTER TAHUN PUBLIKASI
# ============================================================

def filter_target_year(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """
    Mempertahankan artikel yang tanggal publikasinya valid
    dan berada pada TARGET_YEAR.

    scraped_at tidak digunakan sebagai pengganti published_at.
    """

    if df.empty:
        return df.copy(), 0

    result = df.copy()

    result["published_at"] = pd.to_datetime(
        result["published_at"],
        errors="coerce",
        utc=True,
    )

    before = len(result)

    result = result[
        result["published_at"].notna()
        & (
            result["published_at"].dt.year
            == TARGET_YEAR
        )
    ].copy()

    excluded = before - len(result)

    result["published_at"] = (
        result["published_at"].dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    return result, excluded


# ============================================================
# 10. FUNGSI UTAMA
# ============================================================

def main() -> None:
    """Menjalankan seluruh proses scraping Katadata."""

    print("=" * 64)
    print("KATADATA SEARCH API SCRAPER - SECTOR 3")
    print(f"Target tahun publikasi: {TARGET_YEAR}")
    print(f"Jumlah keyword: {len(SEARCH_KEYWORDS)}")
    print(
        f"Maksimum halaman per keyword: {MAX_PAGES}"
    )
    print("=" * 64)

    session = create_session()

    try:
        articles = get_article_urls(session)
    finally:
        session.close()

    if not articles:
        print(
            "[WARNING] API tidak mengembalikan artikel. "
            "CSV lama tidak diubah."
        )
        return

    df = build_dataframe(articles)

    df = df.drop_duplicates(
        subset=["url"],
        keep="first",
    ).copy()

    print(
        f"[INFO] Artikel unik sebelum filter tanggal: "
        f"{len(df)}"
    )

    df, excluded_count = filter_target_year(df)

    print(
        f"[INFO] Artikel tanpa tanggal valid atau di luar "
        f"{TARGET_YEAR}: {excluded_count}"
    )

    print(
        f"[INFO] Artikel tahun {TARGET_YEAR}: {len(df)}"
    )

    if df.empty:
        print(
            f"[WARNING] Tidak ada artikel tahun "
            f"{TARGET_YEAR}. CSV lama tidak diubah."
        )
        return

    # Pastikan folder output tersedia.
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Simpan CSV.
    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    software_count = int(
        df["is_enterprise_software"].sum()
    )

    print(f"\n[SUCCESS] CSV disimpan: {OUTPUT_FILE}")
    print(
        f"[INFO] Total artikel tersimpan: {len(df)}"
    )

    print(
        f"[INFO] Terindikasi Enterprise Software: "
        f"{software_count}"
    )

    print("\n[INFO] Status relevansi Sector 3:")
    print(
        df["relevance_level"]
        .value_counts()
        .to_string()
    )

    print("\n[INFO] Distribusi topik:")
    print(
        df["sector3_topic"]
        .value_counts()
        .to_string()
    )

    print("\n[INFO] Distribusi channel:")
    print(
        df["channel"]
        .fillna("Tidak diketahui")
        .value_counts()
        .to_string()
    )


# ============================================================
# 11. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
