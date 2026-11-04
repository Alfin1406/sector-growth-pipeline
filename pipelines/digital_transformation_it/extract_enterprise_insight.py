"""Insight extraction for Katadata Sector 3 / IT Enterprise articles.

Input : data/processed/katadata_enterprise_filtered.csv
Output: data/processed/katadata_enterprise_insight.csv

The output schema is compatible with the sector3_articles table:
article_id, title, url, published_at, channel, source, topic, subtopic,
event_type, technology, industry, business_action, impact,
insight_summary, content_status, scraped_at.

Classification is rule-based: labels are preliminary structured indicators,
not verified facts or a substitute for reviewing the article itself.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


# ---------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "katadata_enterprise_filtered.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "katadata_enterprise_insight.csv"

# Umbrella topic; the five Sector 3 themes are recorded in `subtopic`.
TOPIC_NAME = "IT Enterprise"
ALLOWED_SECTOR3_TOPICS = {
    "Enterprise Software",
    "Cyber Security",
    "Digital Transformation",
    "Cloud Enterprise",
    "Enterprise Data & AI",
}

OUTPUT_COLUMNS = [
    "article_id", "title", "url", "published_at", "channel", "source",
    "topic", "subtopic", "event_type", "technology", "industry",
    "business_action", "impact", "insight_summary", "content_status",
    "scraped_at",
]


def clean_text(value: Any) -> str:
    """Normalize text and safely handle missing values."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text: str, keywords: list[str]) -> bool:
    """Case-insensitive keyword detection for Indonesian/English text."""
    text = text.lower()
    return any(term.lower() in text for term in keywords)


def focused_text(title: str, content: str, body_chars: int = 700) -> str:
    """Use title and beginning of article to reduce irrelevant body matches."""
    return f"{title} {content[:body_chars]}".lower()


def get_article_id(url: str) -> str:
    """Extract the Katadata article ID from its URL."""
    parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    if len(parts) >= 2 and re.fullmatch(r"[0-9a-fA-F]{8,32}", parts[-2]):
        return parts[-2]
    if parts and re.fullmatch(r"[0-9a-fA-F]{8,32}", parts[-1]):
        return parts[-1]
    if parts:
        return parts[-1][:64]
    return re.sub(r"\W+", "", url)[-64:] or "unknown"


# ---------------------------------------------------------------------
# 2. Event type
# ---------------------------------------------------------------------
def detect_event_type(title: str, content: str, category: str) -> str:
    t = title.lower()
    body = content.lower()[:1200]
    text = f"{t} {body}"

    # Product releases should not be mislabeled as incidents simply because
    # the release is intended to prevent a security problem.
    if contains_any(t, ["luncurkan", "meluncurkan", "diluncurkan", "perkenalkan", "memperkenalkan", "fitur baru"]):
        return "Product / Solution Launch"

    if category == "Cyber Security":
        # Headlines describing a warning, trend, or risk rather than a confirmed
        # attack are classified as assessment/reporting.
        warning_cues = [
            "peringatkan", "waspada", "waswas", "antisipasi", "risiko",
            "ancaman", "celah utama", "sasaran empuk", "masuk 10 besar",
            "catat kasus", "meningkat", "makin cepat", "mulai bidik",
            "potensi", "dugaan", "diduga", "isu kebocoran", "disebut bocor",
        ]
        title_has_specific_incident = contains_any(t, [
            "serangan siber ke ", "serangan siber terhadap ", "peretas serang",
            "hacker iran disebut serang", "serang produsen", "diretas hacker",
            "dibobol", "data menteri diduga bocor", "data kementerian esdm diduga bocor",
            "komdigi buka suara soal dugaan kebocoran", "data pengembang game diduga bocor",
        ])
        if contains_any(t, ["ransomware"]):
            if contains_any(t, ["riset", "bisa menyebar", "tren", "ancaman", "dapat menyebar"]):
                return "Ransomware Threat / Research"
            return "Ransomware Incident / Threat"
        if contains_any(t, ["kebocoran data", "data bocor", "data ... bocor", "diduga bocor", "dugaan kebocoran", "isu kebocoran", "data menteri diduga bocor"]):
            return "Data Exposure / Leak Report"
        if title_has_specific_incident and not contains_any(t, warning_cues):
            return "Cyber Attack / Security Incident"
        if contains_any(t, warning_cues):
            if contains_any(t, ["meningkat", "makin cepat", "mulai bidik", "masuk 10 besar", "sasaran empuk", "catat kasus"]):
                return "Cyber Threat Landscape / Trend"
            return "Security Warning / Threat Assessment"
        if title_has_specific_incident:
            return "Cyber Attack / Security Incident"
        if contains_any(t, ["serangan siber", "serangan hacker", "menyerang", "meretas", "diretas", "dibobol", "hacker", "peretas"]):
            return "Cyber Attack / Security Incident"
        if contains_any(text, ["phishing", "spyware", "malware", "backdoor", "celah keamanan", "kerentanan", "vulnerability", "exploit"]):
            return "Cyber Threat / Vulnerability"
        return "Cybersecurity Development"

    # Non-cyber incident types (e.g. service outage or cloud infrastructure event).
    if contains_any(t, ["gangguan layanan", "layanan terganggu", "sempat terganggu", "sistem down", "layanan down", "outage", "downtime", "setop pemesanan", "setop pemesanan online", "terbakar", "gangguan sistem"]):
        return "Service Disruption / Infrastructure Incident"
    if contains_any(t, ["akuisisi", "mengakuisisi", "diakuisisi", "acquisition"]):
        return "Acquisition"
    if contains_any(t, ["kemitraan", "kolaborasi", "kerja sama", "bekerja sama", "gandeng", "partnership"]):
        return "Partnership / Collaboration"
    if contains_any(t, ["rekomendasi", "alternatif", "pilihan", "memilih", "terbaik"]):
        return "Product / Solution Evaluation"
    if contains_any(text, ["mengadopsi", "adopsi", "implementasi", "mengimplementasikan", "menerapkan", "migrasi ke", "beralih ke"]):
        return "Adoption / Implementation"
    if contains_any(text, ["investasi", "investor", "pendanaan", "funding", "mendanai"]):
        return "Technology Investment / Funding"
    if contains_any(text, ["peraturan", "regulasi", "kebijakan pemerintah", "aturan baru"]):
        return "Regulatory / Policy Update"
    if contains_any(text, ["tren", "meningkat", "pertumbuhan", "diprediksi", "diperkirakan", "prospek"]):
        return "Market / Technology Trend"

    return {
        "Cloud Enterprise": "Cloud Technology Development",
        "Enterprise Data & AI": "Enterprise Data / AI Development",
        "Digital Transformation": "Digital Transformation Development",
        "Enterprise Software": "Enterprise Software Activity",
    }.get(category, "Enterprise Technology Event")


# ---------------------------------------------------------------------
# 3. Technology and vendor detection
# ---------------------------------------------------------------------
def detect_technology(title: str, content: str, category: str) -> str:
    # Prioritize title; inspect only the opening of the story if title alone
    # does not identify a vendor/technology. This reduces noise from body text.
    title_text = title.lower()
    opening_text = f"{title} {content[:500]}".lower()

    # Include technology vendors/platforms, not organizations merely affected by an incident.
    # Victims/impacted entities (e.g. KFC, Stryker, Tata Electronics, Apple, Tesla)
    # are classified under `industry` where applicable, not as `technology`.
    vendor_map = {
        "Microsoft": ["microsoft", "outlook", "microsoft 365", "azure"],
        "Google / Google Cloud": ["google cloud", "google", "gemini"],
        "OpenAI / ChatGPT": ["openai", "chatgpt"],
        "Oracle": ["oracle", "netsuite"],
        "Amazon / AWS": ["aws", "amazon web services", "amazon", "amazon cloud"],
        "Alibaba Cloud": ["alibaba cloud"],
        "Huawei": ["huawei cloud", "huawei"],
        "IBM": ["ibm", "watson"],
        "SAP": ["sap", "successfactors", "sap ariba"],
        "Salesforce": ["salesforce"],
        "Zoho": ["zoho"],
        "Mekari": ["mekari", "talenta"],
        "Nvidia": ["nvidia"],
        "Anthropic / Claude": ["anthropic", "claude"],
        "DeepSeek": ["deepseek"],
        "Kaspersky": ["kaspersky"],
        "Cisco": ["cisco"],
        "Akamai": ["akamai"],
        "CrowdStrike": ["crowdstrike"],
        "Fortinet": ["fortinet"],
        "Palo Alto Networks": ["palo alto networks"],
    }

    technologies: list[str] = []
    for vendor, terms in vendor_map.items():
        if contains_any(title_text, terms):
            technologies.append(vendor)

    # If headline does not identify a specific vendor, inspect opening lines.
    if not technologies:
        for vendor, terms in vendor_map.items():
            if contains_any(opening_text, terms):
                technologies.append(vendor)

    technology_terms = [
        ("Ransomware", ["ransomware"]),
        ("Phishing", ["phishing"]),
        ("Malware / Spyware", ["malware", "spyware", "trojan"]),
        ("Backdoor", ["backdoor"]),
        ("Identity and Access Management", ["identity access management", "multi-factor authentication", "multifactor authentication"]),
        ("Encryption", ["enkripsi", "encryption"]),
        ("Cloud Computing", ["cloud computing", "komputasi awan", "layanan cloud", "cloud"]),
        ("Artificial Intelligence", ["artificial intelligence", "kecerdasan buatan", "generative ai", "machine learning", "model ai", "agen ai"]),
        ("Data Analytics", ["analitik data", "data analytics", "big data", "business intelligence"]),
        ("Enterprise Software", ["enterprise software", "enterprise resource planning", "software erp", "saas", "hris", "crm"]),
        ("Cybersecurity", ["keamanan siber", "serangan siber", "cyber security", "cybersecurity", "keamanan data", "lockdown mode"]),
        ("Human Factors / Security Awareness", ["kelalaian manusia", "human error", "kesadaran keamanan"]),
        ("Critical Infrastructure / CCTV", ["kamera cctv", "cctv"]),
    ]
    for label, terms in technology_terms:
        if contains_any(opening_text, terms):
            technologies.append(label)

    # Deduplicate while preserving order.
    technologies = list(dict.fromkeys(technologies))
    if not technologies:
        fallbacks = {
            "Cyber Security": "Cybersecurity (specific technology not detected)",
            "Cloud Enterprise": "Cloud Enterprise (specific technology not detected)",
            "Enterprise Data & AI": "Enterprise Data & AI (specific technology not detected)",
            "Digital Transformation": "Digital Transformation (specific technology not detected)",
            "Enterprise Software": "Enterprise Software (specific technology not detected)",
        }
        technologies = [fallbacks.get(category, "Not Detected")]
    return ", ".join(technologies)


# ---------------------------------------------------------------------
# 4. Industry detection (headline first, short opening fallback)
# ---------------------------------------------------------------------
def detect_industry(title: str, content: str) -> str:
    title_text = title.lower()
    opening_text = f"{title} {content[:450]}".lower()

    industry_rules = [
        ("Banking & Finance", ["sistem keuangan", "jasa keuangan", "perbankan", "bank-bank", "bank ", "bank,", "ojk", "bursa", "asuransi", "nasabah"]),
        ("Gaming / Digital Services", ["pengembang game", "pengembang gim", "gim", "game developer", "igrs", "indonesia game rating system"]),
        ("Small Business / Critical Infrastructure", ["umkm", "usaha kecil", "kamera cctv", "cctv", "infrastruktur kritis"]),
        ("Government / Public Sector", ["bssn", "komdigi", "kementerian", "pemerintah", "pemerintahan", "instansi pemerintah", "lembaga pemerintah", "esdm", "pemprov", "luhut", "layanan publik"]),
        ("Healthcare", ["alat kesehatan", "produsen alat kesehatan", "rumah sakit", "kesehatan", "healthcare", "medis", "farmasi", "pasien", "stryker"]),
        ("Food / Consumer Services", ["kfc", "rantai pasok pangan", "restoran", "makanan", "food supply"]),
        ("Retail / E-Commerce", ["ritel", "retail", "e-commerce", "ecommerce", "belanja online", "toko online"]),
        ("Education", ["mahasiswa", "universitas", "kampus", "sekolah", "pendidikan"]),
        ("Manufacturing / Supply Chain", ["tata electronics", "manufaktur", "pabrik", "produksi", "rantai pasok", "supply chain", "tesla", "apple supplier"]),
        ("Energy / Utilities", ["esdm", "energi", "kelistrikan", "listrik", "minyak", "gas bumi", "pertamina", "pln"]),
        ("Transportation / Logistics", ["transportasi", "logistik", "maskapai", "penerbangan", "bandara", "pelabuhan", "airasia"]),
        ("Cloud Services / Technology Infrastructure", ["pusat data", "data center", "layanan cloud", "amazon web services", "aws", "cloud region"]),
        ("Technology / Software", ["perusahaan teknologi", "vendor teknologi", "penyedia cloud", "perusahaan keamanan siber", "software", "perangkat lunak", "itsec asia", "nvidia", "openai", "google", "microsoft", "chatgpt"]),
    ]

    # Headline has priority so a passing mention in the article body doesn't
    # override the industry that the story is mainly about.
    for industry, terms in industry_rules:
        if contains_any(title_text, terms):
            return industry
    for industry, terms in industry_rules:
        if contains_any(opening_text, terms):
            return industry
    return "General / Not Explicitly Stated"


# ---------------------------------------------------------------------
# 5. Business action and impact
# ---------------------------------------------------------------------
def detect_business_action(title: str, content: str, category: str, event_type: str) -> str:
    t = title.lower()
    text = f"{title} {content[:900]}".lower()

    if category == "Cyber Security":
        if contains_any(t, ["investigasi", "menyelidiki", "investigating", "diinvestigasi", "komdigi buka suara", "bssn memastikan"]):
            return "Incident Verification / Investigation"
        if contains_any(t, ["minta bank antisipasi", "antisipasi", "perkuat keamanan", "memperkuat keamanan", "cegah", "untuk cegah", "lockdown mode"]):
            return "Security Preparedness / Risk Mitigation"
        if contains_any(t, ["peringatkan", "waspada", "waswas", "risiko", "ancaman", "celah utama", "sasaran empuk", "masuk 10 besar", "meningkat", "makin cepat", "mulai bidik", "catat kasus"]):
            return "Threat Monitoring / Risk Assessment"
        if contains_any(t, ["luncurkan", "meluncurkan", "platform keamanan", "fitur baru"]):
            return "Security Solution Deployment / Launch"
        if event_type in ["Data Exposure / Leak Report", "Cyber Attack / Security Incident", "Ransomware Incident / Threat"]:
            if contains_any(t, ["serang", "menyerang", "diretas", "dibobol", "bocor", "kebocoran", "ransomware"]):
                return "Security Incident / Threat Disclosure"
        if contains_any(text, ["menangani insiden", "respons insiden", "memulihkan sistem", "pemulihan sistem", "incident response"]):
            return "Incident Response / Recovery"
        return "Security Monitoring / Risk Assessment"

    if event_type == "Service Disruption / Infrastructure Incident":
        return "Service Continuity / Incident Management"
    if event_type == "Acquisition":
        return "Corporate Acquisition"
    if event_type == "Partnership / Collaboration":
        return "Business / Technology Partnership"
    if event_type == "Product / Solution Launch":
        return "Product / Solution Launch"
    if event_type == "Product / Solution Evaluation":
        return "Product / Solution Evaluation"
    if event_type == "Adoption / Implementation":
        return "Technology Adoption / Implementation"
    if event_type == "Technology Investment / Funding":
        return "Technology Investment / Funding"
    if event_type == "Regulatory / Policy Update":
        return "Regulatory Compliance / Policy Response"
    if contains_any(text, ["otomatisasi", "automasi", "efisiensi", "produktivitas"]):
        return "Operational Improvement / Automation"
    return "Not Explicitly Stated"


def detect_impact(title: str, content: str, category: str) -> str:
    # Headline and opening segment only, to avoid accumulating every topic
    # mentioned anywhere in a long article.
    text = focused_text(title, content, body_chars=650)
    impact_rules = [
        ("Data Confidentiality / Exposure Risk", ["kebocoran data", "data bocor", "diduga bocor", "data leak", "data breach", "exfiltration", "data sensitif"]),
        ("Operational Disruption", ["gangguan layanan", "layanan terganggu", "sistem down", "operasi terhenti", "berhenti beroperasi", "downtime", "outage", "setop pemesanan", "gangguan jaringan", "layanan cloud terguncang", "terbakar"]),
        ("Financial Loss / Cost Impact", ["kerugian finansial", "kerugian", "tebusan", "ransom payment", "denda", "biaya operasional"]),
        ("Reputational / Trust Risk", ["reputasi", "kepercayaan pelanggan", "kepercayaan pengguna", "citra perusahaan"]),
        ("Regulatory / Compliance Risk", ["kepatuhan", "regulasi", "sanksi", "aturan perlindungan data", "ojk minta", "regulator"]),
        ("Cybersecurity Risk / Threat Exposure", ["serangan siber", "ransomware", "phishing", "hacker", "peretas", "malware", "ancaman siber", "celah keamanan", "kerentanan keamanan", "serangan berbasis ai"]),
        ("Access Control / Data Protection", ["mengendalikan agen ai", "batas akses", "mencegah data exfiltration", "lockdown mode", "melindungi data"]),
        ("Operational Efficiency", ["efisiensi", "meningkatkan produktivitas", "operasional lebih efisien", "menyederhanakan proses", "hemat hingga"]),
        ("Process Automation", ["otomatisasi", "automasi", "mengotomatisasi"]),
        ("Data Integration / Availability", ["integrasi data", "data terintegrasi", "data tersentralisasi", "akses data"]),
        ("Decision Support", ["pengambilan keputusan", "keputusan berbasis data", "analitik bisnis"]),
        ("Customer Experience", ["pengalaman pelanggan", "customer experience", "layanan pelanggan"]),
        ("Business Scalability", ["skalabilitas", "scalable", "ekspansi bisnis", "pertumbuhan perusahaan"]),
    ]

    impacts = [label for label, terms in impact_rules if contains_any(text, terms)]
    if not impacts:
        if category == "Cyber Security":
            return "Cybersecurity relevance identified; specific impact not explicit"
        return "Not Explicitly Stated"
    return ", ".join(impacts[:3])


# ---------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------
def main() -> None:
    print("=" * 64)
    print("INSIGHT EXTRACTION - KATADATA SECTOR 3")
    print("=" * 64)
    print(f"Input : {INPUT_FILE}")

    if not INPUT_FILE.exists():
        print(f"[ERROR] File input tidak ditemukan: {INPUT_FILE}")
        print("Pastikan tahap filtering berhasil dijalankan terlebih dahulu.")
        return

    try:
        df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    except Exception as exc:
        print(f"[ERROR] Gagal membaca input CSV: {exc}")
        return

    print(f"Input dataset: {len(df)} rows")
    if df.empty:
        print("[WARNING] Input kosong. Output tidak dibuat.")
        return

    missing_required = {"title", "url"} - set(df.columns)
    if missing_required:
        print(f"[ERROR] Kolom wajib hilang: {sorted(missing_required)}")
        return

    # This script expects the 'relevant' output from filtering. Safety guard
    # avoids processing review/out-of-scope records if they appear in the file.
    if "filter_relevance_level" in df.columns:
        is_relevant = df["filter_relevance_level"].astype(str).str.strip().str.lower().eq("relevan")
        excluded = int((~is_relevant).sum())
        if excluded:
            print(f"[INFO] Mengeluarkan {excluded} artikel yang bukan berstatus Relevan.")
            df = df.loc[is_relevant].copy()

    if df.empty:
        print("[WARNING] Tidak ada artikel relevan untuk diekstrak.")
        return

    # Guarantee source columns exist and normalize text values.
    text_columns = [
        "title", "url", "published_at", "channel", "source", "content",
        "subtopic", "sector3_topic", "audit_sector3_topic", "content_status", "scraped_at",
    ]
    for col in text_columns:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(clean_text)

    df = df[df["url"].str.strip().ne("")].copy()
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first").copy()
    print(f"Duplikat URL dihapus: {before_dedup - len(df)}")
    if df.empty:
        print("[WARNING] Tidak ada URL valid untuk diproses.")
        return

    # Preserve the sector classification established by the audit/filter stage.
    def resolve_category(row: pd.Series) -> str:
        for field in ("subtopic", "sector3_topic", "audit_sector3_topic"):
            value = clean_text(row.get(field, ""))
            if value in ALLOWED_SECTOR3_TOPICS:
                return value
        return "IT Enterprise - Unclassified"

    df["subtopic"] = df.apply(resolve_category, axis=1)
    df["topic"] = TOPIC_NAME
    df["article_id"] = df["url"].apply(get_article_id)

    df["event_type"] = df.apply(
        lambda row: detect_event_type(row["title"], row["content"], row["subtopic"]),
        axis=1,
    )
    df["technology"] = df.apply(
        lambda row: detect_technology(row["title"], row["content"], row["subtopic"]),
        axis=1,
    )
    df["industry"] = df.apply(
        lambda row: detect_industry(row["title"], row["content"]),
        axis=1,
    )
    df["business_action"] = df.apply(
        lambda row: detect_business_action(row["title"], row["content"], row["subtopic"], row["event_type"]),
        axis=1,
    )
    df["impact"] = df.apply(
        lambda row: detect_impact(row["title"], row["content"], row["subtopic"]),
        axis=1,
    )

    def make_summary(row: pd.Series) -> str:
        # Clearly describes detected information without presenting it as fact
        # if the classifier has only inferred it from keywords.
        return (
            f'Artikel "{clean_text(row.get("title"))}" diklasifikasikan dalam kategori '
            f'{clean_text(row.get("subtopic"))}. Jenis peristiwa yang terdeteksi: '
            f'{clean_text(row.get("event_type"))}. Teknologi/vendor yang teridentifikasi '
            f'dari judul dan bagian awal teks: {clean_text(row.get("technology"))}. '
            f'Industri yang terindikasi: {clean_text(row.get("industry"))}. '
            f'Tindakan bisnis yang terdeteksi: {clean_text(row.get("business_action"))}. '
            f'Dampak yang disebutkan atau terindikasi dari teks: {clean_text(row.get("impact"))}.'
        )

    df["insight_summary"] = df.apply(make_summary, axis=1)

    # Normalize dates into naive timestamps for PostgreSQL TIMESTAMP.
    for date_col in ("published_at", "scraped_at"):
        parsed = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        formatted = parsed.dt.tz_convert(None).dt.strftime("%Y-%m-%d %H:%M:%S")
        df[date_col] = formatted.where(parsed.notna(), None)

    calculated_content_status = df["content"].apply(
        lambda value: "SUCCESS" if len(clean_text(value)) > 100 else "EMPTY"
    )
    existing_status = df["content_status"].astype(str).str.strip().str.upper()
    acceptable_status = {"SUCCESS", "EMPTY", "BLOCKED", "FAILED"}
    df["content_status"] = existing_status.where(
        existing_status.isin(acceptable_status), calculated_content_status
    )

    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df_final = df[OUTPUT_COLUMNS].copy()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = OUTPUT_FILE.with_name(OUTPUT_FILE.stem + ".tmp.csv")
    try:
        df_final.to_csv(temp_file, index=False, encoding="utf-8-sig")
        temp_file.replace(OUTPUT_FILE)
    except Exception as exc:
        if temp_file.exists():
            temp_file.unlink()
        print(f"[ERROR] Gagal menyimpan output: {exc}")
        return

    print("\nINSIGHT EXTRACTION SELESAI")
    print("-" * 64)
    print(f"Total artikel : {len(df_final)}")
    print(f"Output        : {OUTPUT_FILE}")
    print(f"Topic         : {TOPIC_NAME}")

    for label, column in [
        ("Kategori Sector 3", "subtopic"),
        ("Event Type", "event_type"),
        ("Industry", "industry"),
        ("Business Action", "business_action"),
    ]:
        print(f"\nDistribusi {label}:")
        print(df_final[column].value_counts(dropna=False).to_string())

    preview_columns = ["title", "subtopic", "event_type", "technology", "industry", "business_action", "impact"]
    print("\nPreview:")
    print(df_final[preview_columns].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
