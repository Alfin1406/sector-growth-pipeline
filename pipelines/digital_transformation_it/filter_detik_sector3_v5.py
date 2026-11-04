"""Detik.com Sector 3 filtering V5 candidate, informed by the V4 sample review.

Reads detik_sector3_clean.csv and writes versioned outputs ending in _v5.csv.
The original filtering script and outputs are not overwritten. Rules remain provisional
until a domain reviewer validates the relevance scope and an independent sample.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
INPUT_FILE = DATA_DIR / "detik_sector3_clean.csv"
TARGET_YEAR = 2026

OUTPUT_ALL = DATA_DIR / "detik_sector3_filtered_all_classified_v5.csv"
OUTPUT_RELEVANT = DATA_DIR / "detik_sector3_filtered_v5.csv"
OUTPUT_REVIEW = DATA_DIR / "detik_sector3_filter_review_required_v5.csv"
OUTPUT_OUT_OF_SCOPE = DATA_DIR / "detik_sector3_filter_out_of_scope_v5.csv"
OUTPUT_REPORT = DATA_DIR / "detik_sector3_filter_comparison_v5.csv"

# Strong = a specific technology/incident phrase. Weak = a term that is
# ambiguous without supporting context (e.g., "hacker", "AI", "ERP", "SAP").
TOPIC_RULES: dict[str, dict[str, list[str]]] = {
    "Cyber Security": {
        "strong": [
            "keamanan siber", "serangan siber", "cyber security", "cybersecurity",
            "ransomware", "malware", "phishing", "spyware", "ddos", "botnet",
            "backdoor", "trojan", "celah keamanan", "zero-day", "zero day",
            "ancaman siber", "eksploitasi keamanan", "data breach", "security incident",
            "kerentanan keamanan", "serangan hacker", "diserang hacker", "hacker pakai ai", "satpam siber",
            "ai untuk keamanan siber", "keamanan siber berbasis ai", "serangan berbantuan ai",
            "cyber warfare", "perang siber", "ancaman komputasi kuantum",
            "penipuan berkedok promo", "rekayasa sosial", "social engineering", "smishing",
            "tautan berbahaya", "tautan palsu", "link palsu", "penipuan whatsapp",
            "modus penipuan digital", "phishing whatsapp", "penjahat siber", "kejahatan siber",
            "kejahatan siber terorganisasi", "crime-as-a-service", "pencurian kredensial",
            "serangan proxy", "jaringan proxy raksasa",
            "kredensial dicuri", "password stealer", "insider threat", "apt42", "apt33",
            "pencurian data", "kebocoran data", "kebocoran informasi", "serangan api",
            "vulnerability", "exploit", "malicious software", "akun dibobol",
            "celah kritis", "zero-click", "zero click", "pencuri password", "jaringan proxy", "proxy raksasa",
        ],
        "weak": [
            "hacker", "peretas", "peretasan", "diretas", "dibobol", "membobol",
            "bobol", "serangan digital", "keamanan digital", "data bocor",
        ],
    },
    "Enterprise Software": {
        "strong": [
            "enterprise software", "software enterprise", "aplikasi enterprise",
            "aplikasi bisnis", "software bisnis", "sistem erp", "enterprise resource planning",
            "cloud erp", "sap cloud erp", "sap s/4hana", "salesforce", "microsoft dynamics",
            "workday", "servicenow", "oracle netsuite", "procurement software",
            "supply chain management", "sistem manajemen perusahaan",
            "customer relationship management", "human resource management system",
            "platform crm", "sistem crm", "software procurement", "software rantai pasok",
            "contact center", "contact centre", "customer experience platform", "omnichannel",
            "crm platform", "customer service platform", "ai gateway", "lintas channel",
            "respons pelanggan", "lisensi windows", "pembajakan windows", "aktivasi windows",
            "sistem erp perusahaan", "aplikasi erp",
            "pengelolaan lisensi software", "pembajakan software", "perusahaan software",
            "sistem hris", "sistem hcm", "aplikasi sdm perusahaan", "aplikasi crm",
            "transformasi hris", "hris perusahaan",
        ],
        "weak": ["erp", "sap", "oracle", "crm", "hris", "hcm", "saas", "software perusahaan"],
    },
    "Digital Transformation": {
        "strong": [
            "transformasi digital", "digital transformation", "otomatisasi bisnis",
            "otomasi proses bisnis", "integrasi sistem", "modernisasi sistem",
            "industri 4.0", "smart factory", "proses bisnis digital", "digitalisasi layanan",
            "digitalisasi operasional", "otomatisasi proses", "workflow automation", "kedaulatan digital",
            "solusi ict terintegrasi", "sistem digital terintegrasi", "data maritim", "ais data",
            "digitalisasi korporasi", "digitalisasi perusahaan", "solusi digital enterprise",
            "digitalisasi industri", "transformasi digital korporasi",
        ],
        "weak": ["digitalisasi", "adopsi teknologi", "operasional digital", "efisiensi operasional"],
    },
    "Cloud Enterprise": {
        "strong": [
            "cloud computing", "komputasi awan", "hybrid cloud", "private cloud", "public cloud",
            "migrasi cloud", "cloud infrastructure", "cloud service", "infrastruktur cloud",
            "data center", "data centre", "pusat data", "ai factory", "cloud region",
            "hyperscaler", "colocation", "interkoneksi data center", "kabel laut",
            "kabel bawah laut", "kabel submarine", "submarine cable", "backbone internet",
            "infrastruktur komputasi ai", "high-performance computing", "high performance computing",
            "infrastruktur digital", "digital infrastructure", "cloud-native infrastructure",
            "data center tier iv", "pusat komputasi", "konektivitas data center", "hub internet", "pusat konektivitas",
            "konektivitas internasional", "konektivitas global", "internet asia pasifik",
            "jaringan backbone", "infrastruktur telekomunikasi", "infrastruktur konektivitas",
            "spektrum frekuensi", "frekuensi 700 mhz", "frekuensi 2,6 ghz", "frekuensi 2.6 ghz",
            "menara telekomunikasi", "riset antena", "jaringan 6g", "teknologi 6g",
            "b2b ict", "solusi b2b ict", "solusi ict", "managed services",
            "pabrik ram", "pabrik chip", "pabrik semikonduktor", "semikonduktor",
            "chip memori", "memori dram", "dram", "nand",
        ],
        "weak": [
            "cloud", "google cloud", "aws", "amazon web services", "microsoft azure",
            "infrastruktur jaringan", "bandwidth", "server", "gpu", "komputasi", "interkoneksi",
            "starlink", "satelit", "jaringan satelit", "blue origin", "terawave",
        ],
    },
    "Enterprise Data & AI": {
        "strong": [
            "artificial intelligence", "kecerdasan buatan", "generative ai", "generative artificial intelligence",
            "ai generatif", "machine learning", "pembelajaran mesin", "big data", "analitik data",
            "data analytics", "business intelligence", "data governance", "data management",
            "data platform", "agentic ai", "enterprise ai", "ai perusahaan",
            "otomatisasi berbasis ai", "analitik bisnis", "data perusahaan", "large language model",
            "model bahasa besar", "ai agent", "agen ai", "llm", "genai", "gpu ai",
            "chip ai", "chip kecerdasan buatan", "ai inference", "pelatihan model ai",
            "data science", "analitik prediktif", "data warehouse", "data lakehouse",
            "strategi adopsi ai", "adopsi ai perusahaan", "implementasi ai", "penerapan ai",
            "proyek ai", "proyek kecerdasan buatan", "ai untuk jaringan", "ai di jaringan",
            "optimasi jaringan dengan ai", "ai untuk operasional", "ai dalam operasional",
            "ai di sektor keuangan", "ai di sektor kesehatan", "tata kelola ai", "ai governance",
            "chatgpt", "openai", "startup ai", "adopsi ai", "modernisasi workflow",
            "workflow pakai ai", "ai dalam workflow", "penjualan chip canggih", "permintaan chip ai",
            "ais data", "data maritim", "platform data maritim",
        ],
        "weak": ["ai", "nvidia", "gpu", "chip", "algoritma", "analisis data"],
    },
}

# Context that materially indicates an organization, enterprise deployment,
# public-sector service, industrial operation, digital infrastructure, or market signal.
ORG_CONTEXT = [
    "perusahaan", "korporasi", "enterprise", "b2b", "bumn", "instansi pemerintah",
    "pemerintah", "kementerian", "organisasi", "sektor publik", "perbankan", "bank",
    "pabrik", "industri", "operasional perusahaan", "rantai pasok", "sistem produksi",
    "data pelanggan", "sistem perusahaan", "sistem internal", "karyawan", "layanan korporasi",
    "pelanggan korporasi", "pengguna enterprise", "workflow", "contact center", "pusat data",
    "data center", "ai factory", "kabel laut", "kabel bawah laut", "backbone", "cloud region",
    "interkoneksi", "layanan cloud", "perusahaan energi", "operator telekomunikasi",
    "infrastruktur jaringan", "transformasi bisnis", "efisiensi operasional", "layanan publik",
    "rumah sakit", "puskesmas", "data maritim", "infrastruktur digital", "komputasi ai",
    "perusahaan teknologi", "perusahaan telekomunikasi", "operator telekomunikasi",
    "operator seluler", "jaringan 5g", "jaringan 6g", "layanan digital korporasi",
    "digitalisasi korporasi", "strategi adopsi ai", "proyek ai", "penerapan ai",
    "komputer industri", "sistem industri",
    "keamanan informasi", "implementasi erp", "implementasi sap", "erp perusahaan",
]

MARKET_OR_DEPLOYMENT_CONTEXT = [
    "investasi", "pendanaan", "ekspansi", "membangun", "bangun", "belanja modal",
    "kapasitas komputasi", "rantai pasok", "pasar chip", "permintaan chip", "valuasi",
    "akuisisi", "kontrak", "implementasi", "mengimplementasikan", "meluncurkan solusi",
    "diadopsi perusahaan", "adopsi ai", "menggunakan sap", "memakai sap", "menggunakan erp",
    "investor", "pendanaan", "funding", "putaran pendanaan", "valuasi", "raih dana", "triliun",
    "otomatisasi workflow", "proses bisnis", "operasi jaringan", "kapasitas data center",
    "pengembangan data center", "layanan perusahaan", "perusahaan menggunakan", "di sektor publik",
    "optimasi jaringan", "operasi jaringan 5g", "pengembangan jaringan seluler",
    "investasi semikonduktor", "pabrik ram", "permintaan chip memori",
]

# Article types that are usually consumer-only/general-interest unless a concrete
# cybersecurity threat or clear enterprise/infrastructure context is present.
CONSUMER_ONLY_PATTERNS = [
    r"\bpaket roaming\b", r"\bbundling\b.*\b(iphone|spotify|netflix|ponsel)\b",
    r"\bcara blokir scam\b", r"\bwhatsapp call\b.*\b(cara|blokir|fitur)\b",
    r"\bblokir scam\b.*\bwhatsapp\b", r"\btransformasi gaya hidup digital\b",
    r"\btarif internet\b", r"\bpaket internet\b", r"\bperlukah upgrade ke 5g\b",
    r"\bcara mengaktifkan\b.*\b(paket|roaming)\b", r"\bsmart home\b",
    r"\bgame pc\b", r"\blibur sekolah\b", r"\bcentang biru\b.*\bpenipu\b",
    r"\b(sinyal|jangkauan) 5g\b.*\b(rumah|gedung)\b", r"\bpelanggan xl\b.*\broaming\b",
    r"\bpengguna (android|iphone|hp|ponsel)\b.*\b(diimbau|waspada|hati-hati)\b",
    r"\b(tv|televisi)\b.*\bvision ai\b",
    r"\bbeli kuota\b.*\b(gemini|ai plus)\b",
    r"\bbonus\b.*\b(gemini|ai plus)\b",
    r"\bai\b.*\bkreator\b.*\bmonetisasi\b",
    r"\bkreator\b.*\b(ai|fitur)\b.*\bmonetisasi\b",
    # Consumer mobile-service/how-to coverage should not enter the enterprise queue
    # merely because the article body/sidebar contains unrelated technical keywords.
    r"\b(apa manfaat|manfaat)\b.*\b5g\b.*\b(traveling|streaming|ponsel|kuota)\b",
    r"\b5g\b.*\b(traveling|streaming|kuota|cek coverage|coverage|sinyal|hp|ponsel)\b",
    r"\b(hp|ponsel|smartphone)\b.*\b(5g|sinyal|coverage)\b",
    r"\b(cara cek|cek)\b.*\bcoverage\b.*\b(telkomsel|5g|jaringan)\b",
    r"\bpaket (indosat|telkomsel|xl|tri|internet|data|kuota)\b.*\b(kuota|rollover|hangus|bonus)\b",
    r"\b(kuota internet|penerapan kuota)\b.*\b(hangus|rollover|tak hangus)\b",
    r"\bapa bedanya? 5g\b",
    r"\bapa saja kelebihan\b.*\b5g\b.*\bpengguna\b",
    r"\bseberapa cepat\b.*\b5g\b",
    r"\b(apakah|kenapa|mengapa)\b.*\b5g\b.*\b(lebih cepat dari wifi|kuota|sinyal|lemot|coverage)\b",
    r"\bvideo call\b.*\bstreaming\b.*\bgame\b.*\b5g\b",
    r"\btelkomsel 5g ada di mana saja\b",
    r"\bmengapa koneksi saya lemot\b.*\b5g\b",
]

HARD_OUT_OF_SCOPE_PATTERNS = [
    r"electronic road pricing",
    r"jalan berbayar",
    r"ojek online.*\berp\b",
    r"\berp\b.*ruas jalan",
]

# Generic/off-topic context helps prevent a lone weak keyword from becoming a
# relevant technology story (e.g., a historical sports-related hacker profile).
OFF_TOPIC_PATTERNS = [
    r"\bmanchester city\b", r"\bskandal finansial\b.*\b(sepak bola|klub|liga)\b",
    r"\bperang kata\b", r"\bliburan sekolah\b", r"\bpaket roaming haji\b",
    r"\bmenantu jadi bos\b.*\bnepotisme\b", r"\bnepotisme\b.*\bmenantu jadi bos\b",
]

# These cues distinguish meaningful enterprise/infrastructure context from generic mentions
# such as "perusahaan" or "investasi" that can occur in almost any business article.
BODY_ENTERPRISE_CUES = [
    r"\bb2b\b", r"\benterprise\b", r"\bkorporasi\b", r"\blayanan korporasi\b",
    r"\bsolusi ict\b", r"\bsolusi digital enterprise\b", r"\bdigitalisasi korporasi\b",
    r"\bdata center\b", r"\bdata centre\b", r"\bpusat data\b", r"\bai factory\b",
    r"\binfrastruktur cloud\b", r"\binfrastruktur digital\b", r"\binfrastruktur telekomunikasi\b",
    r"\binfrastruktur konektivitas\b", r"\bkabel laut\b", r"\bbackbone internet\b",
    r"\bspektrum frekuensi\b", r"\bmenara telekomunikasi\b", r"\bpabrik (ram|chip|semikonduktor)\b",
    r"\bsemikonduktor\b", r"\bchip memori\b", r"\bkapasitas komputasi\b",
    r"\bstrategi adopsi ai\b", r"\bimplementasi ai\b", r"\bpenerapan ai\b",
    r"\bproyek ai\b", r"\bai untuk (jaringan|perusahaan|operasional|industri)\b",
    r"\boptimasi jaringan\b", r"\boperator telekomunikasi\b", r"\bkeamanan siber\b",
    r"\bcontact center\b", r"\bworkflow automation\b", r"\bdata governance\b",
]

AI_USE_CASE_PATTERNS = [
    r"\b(proyek|implementasi|penerapan|adopsi|strategi|tata kelola|penggunaan)\b.{0,45}\b(ai|kecerdasan buatan|model ai)\b",
    r"\b(ai|kecerdasan buatan)\b.{0,55}\b(jaringan|operasional|produksi|perusahaan|korporasi|industri|keuangan|rumah sakit|dokter|layanan|workflow|karyawan)\b",
    r"\b(jaringan|operasional|produksi|perusahaan|korporasi|industri|keuangan|rumah sakit|dokter|layanan|workflow|karyawan)\b.{0,55}\b(ai|kecerdasan buatan)\b",
    r"\b(jaringan 5g|operator telekomunikasi)\b.{0,45}\b(ai|kecerdasan buatan)\b",
    r"\b(ai|kecerdasan buatan)\b.{0,45}\b(jaringan 5g|operator telekomunikasi)\b",
]

HEADLINE_TECH_CONTEXT = [
    r"\bteknologi\b", r"\bdigitalisasi\b", r"\btransformasi digital\b",
    r"\bdata\b", r"\bai\b", r"\bcloud\b", r"\bsoftware\b", r"\bsistem\b",
    r"\bkabel laut\b", r"\bsatelit\b", r"\bkomputasi\b", r"\bchip\b",
    r"\bgpu\b", r"\bkeamanan siber\b", r"\bcybersecurity\b", r"\bmalware\b",
    r"\bphishing\b", r"\berp\b", r"\bcrm\b", r"\bhris\b", r"\bsap\b",
    r"\bcloud computing\b", r"\bdata center\b", r"\bpusat data\b",
    r"\binternet asia pasifik\b", r"\bhub internet\b", r"\bkedaulatan digital\b",
    r"\bfrekuensi\b", r"\bspektrum\b", r"\bjaringan 5g\b", r"\bjaringan 6g\b",
    r"\binfrastruktur telekomunikasi\b", r"\bmenara telekomunikasi\b",
    r"\bsemikonduktor\b", r"\bpabrik ram\b", r"\bpabrik chip\b",
    r"\bb2b ict\b", r"\bdigitalisasi korporasi\b", r"\bsolusi digital enterprise\b",
]


def normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    value = str(value).lower()
    value = re.sub(r"[\u200b-\u200f\ufeff]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


@lru_cache(maxsize=128)
def _compiled_terms(terms: tuple[str, ...]):
    """Compile all terms into one alternation to avoid rescanning long articles per keyword."""
    # Match longer phrases first, so e.g. "data center tier iv" wins over "data center".
    ordered = sorted(enumerate(terms), key=lambda item: len(item[1]), reverse=True)
    branches = []
    group_to_term = {}
    for original_index, term in ordered:
        group_name = f"k{original_index}"
        branches.append(f"(?P<{group_name}>{re.escape(term.lower())})")
        group_to_term[group_name] = term
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(branches) + r")(?!\w)", re.IGNORECASE)
    return pattern, group_to_term


def find_matches(text: str, terms: list[str]) -> list[str]:
    if not text or not terms:
        return []
    pattern, group_to_term = _compiled_terms(tuple(terms))
    found = set()
    for match in pattern.finditer(text):
        # lastgroup points directly to the matched named alternative.
        group_name = match.lastgroup
        if group_name in group_to_term:
            found.add(group_to_term[group_name])
    # Preserve the maintainable taxonomy order in CSV output.
    return [term for term in terms if term in found]


def matched_patterns(text: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if re.search(p, text, flags=re.IGNORECASE)]


def score_topic(title: str, content: str, rules: dict[str, list[str]]) -> dict[str, Any]:
    title_strong = find_matches(title, rules["strong"])
    content_strong = find_matches(content, rules["strong"])
    title_weak = find_matches(title, rules["weak"])
    content_weak = find_matches(content, rules["weak"])

    # Cap synonym-heavy scores so repeated words do not dominate classification.
    score = 0.0
    if title_strong:
        score += 5.0 + min(len(title_strong) - 1, 2) * 0.8
    score += min(len(content_strong), 3) * 1.6
    if title_weak:
        score += 1.7 + min(len(title_weak) - 1, 2) * 0.35
    score += min(len(content_weak), 3) * 0.45

    return {
        "score": score,
        "title_strong": title_strong,
        "content_strong": content_strong,
        "title_weak": title_weak,
        "content_weak": content_weak,
        "all_matches": list(dict.fromkeys(title_strong + title_weak + content_strong + content_weak)),
    }


# V4 audit-informed overrides. These rules are deliberately narrow and are
# applied before general keyword scoring because the 100-row audit showed that
# several specific story types are systematically ambiguous for keyword rules.
# They remain candidate rules and require domain-owner validation.
AUDIT_OUT_OF_SCOPE_RULES = [
    (r"\b(pengguna|versi)\b.{0,35}\bchatgpt\b.{0,30}\b(gratis|free)\b.{0,25}\b(iklan|ads)\b",
     "Fokus berita adalah iklan pada versi ChatGPT gratis untuk pengguna umum, bukan penerapan teknologi enterprise."),
    (r"\bkisah\b.{0,45}\bnvidia\b.{0,80}\b(sega|hampir bangkrut|bangkrut)\b",
     "Artikel bersifat retrospektif/historis dan tidak membahas perkembangan teknologi enterprise saat ini."),
    (r"\bdaftar lengkap pemenang\b.{0,60}\b(apresiasi|penghargaan|konektivitas digital)\b",
     "Artikel berupa daftar pemenang/apresiasi tanpa informasi teknis atau operasional yang cukup untuk intelijen IT."),
    (r"\brupst\b.{0,100}\bbuyback saham\b",
     "Fokus utama adalah tata kelola dan aksi korporasi, bukan perkembangan teknologi atau layanan digital."),
    (r"\btelkom\b.{0,50}\btutup\s+\d+\s+anak usaha\b",
     "Fokus utama adalah restrukturisasi korporasi tanpa hubungan teknologi yang dijelaskan pada judul."),
    (r"\bspacex\b.{0,70}\b(perusahaan publik|tak lagi privat|go public|ipo)\b",
     "Fokus utama adalah status kepemilikan/pasar modal, bukan teknologi atau layanan konektivitas."),
    (r"\balutsista\b.{0,100}\b(perang|iran|militer|pertempuran)\b",
     "Fokus utama adalah persenjataan/geopolitik militer, di luar cakupan IT enterprise yang ditetapkan."),
]

AUDIT_REVIEW_RULES = [
    (r"\b(settingan|pengaturan|tips|cara)\b.{0,80}\bwhatsapp\b.{0,70}\b(bobol|dibobol|aman|keamanan|akun)\b",
     "Panduan keamanan akun konsumen; relevansi untuk threat intelligence enterprise perlu ditetapkan secara konsisten."),
    (r"\bstartup\b.{0,40}\bai\b.{0,90}\b(pendanaan|raih pendanaan|ekspansi|investasi)\b",
     "Berita pendanaan startup AI; relevansi tergantung apakah cakupan mencakup seluruh pasar startup AI atau hanya use case enterprise."),
    (r"\bceo nvidia\b.{0,100}\b(phk|pecat|karyawan|pemutusan hubungan kerja)\b.{0,40}\bai\b|\b(phk|karyawan)\b.{0,50}\b(ai|kecerdasan buatan)\b",
     "Artikel membahas dampak AI terhadap tenaga kerja/opini pasar, bukan implementasi atau produk teknologi tertentu."),
    (r"\bdata center\b.{0,80}\b(tembaga|tambang|bahan baku|mikroorganisme)\b",
     "Hubungan terhadap data center bersifat rantai pasok tidak langsung; tinjau hanya jika supply chain teknologi termasuk cakupan."),
    (r"\b(kelangkaan|krisis|kekurangan)\b.{0,55}\b(chip memori|memori|ram)\b.{0,60}\b(ponsel murah|ponsel|pc|komputer)\b",
     "Isu supply chain hardware berfokus pada perangkat konsumen; hubungan ke komputasi enterprise belum jelas."),
    (r"\bpangsa pasar\b.{0,50}\b(cpu|prosesor)\b",
     "Berita pangsa pasar CPU adalah tren hardware umum; relevansi komputasi enterprise perlu dikonfirmasi."),
    (r"\b5g\b.{0,80}\b(2031|diprediksi|diproyeksikan|pengguna di indonesia tembus)\b",
     "Proyeksi pasar 5G relevan sebagai konteks industri, tetapi perlu tinjau apakah proyeksi pasar masuk cakupan utama dashboard."),
    (r"\b(rupiah|dolar|kurs)\b.{0,100}\b(indosat|xlsmart|xl smart|telkom|bisnis internet|bisnis telekomunikasi)\b",
     "Artikel berfokus pada dampak makroekonomi ke bisnis operator; belum menunjukkan hubungan langsung dengan teknologi atau layanan."),
    (r"\bderetan manusia super elit\b.{0,80}\b(trump|china|tiongkok)\b",
     "Artikel berorientasi politik/personalia; cuplikan belum menunjukkan kebijakan teknologi yang konkret."),
    (r"\b80 tahun galva\b",
     "Profil/perayaan perusahaan; sistem peringatan dini hanya disebut sekilas pada judul dan perlu pemeriksaan isi."),
    (r"\bbos baru telkom\b.{0,100}\b(arahan|perombakan direksi|komisaris)\b",
     "Berita perubahan pimpinan dan arahan korporasi; tinjau hanya jika isi memuat prioritas teknologi yang konkret."),
    (r"\b(telkom gelar rupst|telkom akan tutup anak usaha|space ?x bakal jadi perusahaan publik)\b",
     "Berita tata kelola/restrukturisasi atau pasar modal tanpa fokus teknologi yang jelas."),
]

AUDIT_RELEVANT_RULES = [
    # Digital infrastructure/connectivity and B2B operator activity
    (r"\btelin\b.{0,80}\b(batic|kolaborasi digital global|konektivitas global)\b", "Cloud Enterprise", "Kerja sama Telin/BATIC terkait ekosistem konektivitas dan telekomunikasi B2B."),
    (r"\b(telkom|telkom indonesia)\b.{0,80}\b(bisnis enterprise|pengembangan bisnis enterprise|layanan enterprise)\b", "Cloud Enterprise", "Judul secara eksplisit membahas pengembangan layanan/pasar enterprise Telkom."),
    (r"\b(perusahaan china tantang starlink|spacesail)\b", "Cloud Enterprise", "Persaingan penyedia satelit/konektivitas merupakan perkembangan pasar infrastruktur digital."),
    (r"\bcommunity gateway\b.{0,80}\b(konektivitas|papua|digital)\b", "Cloud Enterprise", "Pengembangan gateway untuk memperluas konektivitas digital."),
    (r"\b(nqi|china satcom|telkomsat)\b.{0,100}\b(internet satelit|layanan internet satelit|konektivitas satelit|china telecom|daerah 3t)\b", "Cloud Enterprise", "Kemitraan/layanan internet satelit merupakan perkembangan infrastruktur konektivitas."),
    (r"\bmenkomdigi\b.{0,80}\bbts\b.{0,60}\b(pulih|perbaikan|pemulihan)\b", "Cloud Enterprise", "Pemulihan BTS menyangkut ketahanan dan kontinuitas infrastruktur jaringan."),
    (r"\b(perbatasan|ujung negeri|daerah 3t)\b.{0,100}\b(konektivitas|internet|satelit|jaringan)\b", "Cloud Enterprise", "Perluasan konektivitas ke wilayah terpencil merupakan pengembangan infrastruktur digital."),
    (r"\bdata satelit\b.{0,80}\b(mitigasi bencana|bencana)\b", "Enterprise Data & AI", "Penggunaan data satelit untuk mitigasi bencana adalah use case data yang konkret."),
    (r"\blinknet\b.{0,80}\b(fiber|serat optik|jaringan)\b", "Cloud Enterprise", "Ekspansi jaringan fiber adalah pengembangan infrastruktur konektivitas."),
    (r"\braia grid\b", "Cloud Enterprise", "Platform/jaringan digital berkapasitas tinggi merupakan infrastruktur konektivitas."),
    (r"\b(apjatel|penataan kabel fiber optik|kabel fiber optik)\b.{0,100}\b(penataan|pengelolaan|infrastruktur|berulang|kabel)\b", "Cloud Enterprise", "Pengelolaan kabel fiber berkaitan langsung dengan infrastruktur jaringan."),
    (r"\b(integrasi jaringan|jaringan sudah 96%)\b.{0,100}\b(xlsmart|merger|integrasi)\b|\bxlsmart\b.{0,100}\bintegrasi jaringan\b", "Cloud Enterprise", "Integrasi jaringan pascamerger adalah perubahan operasional infrastruktur telekomunikasi."),
    # Cybersecurity/privacy events and concrete enterprise software use cases
    (r"\breset password instagram\b.{0,100}\b(massal|investigasi|menyeluruh|akun)\b", "Cyber Security", "Reset password massal dan desakan investigasi merupakan sinyal insiden keamanan akun/platform."),
    (r"\b(bitlocker|kunci enkripsi)\b.{0,100}\b(fbi|kunci|enkripsi)\b", "Cyber Security", "Akses ke kunci enkripsi berkaitan dengan keamanan data, enkripsi, dan tata kelola akses."),
    (r"\b(aplikasi mata-mata palsu|spyware palsu|aplikasi spyware)\b", "Cyber Security", "Aplikasi spyware palsu merupakan ancaman keamanan yang konkret."),
    (r"\bandroid\b.{0,100}\b(m-banking|mobile banking)\b.{0,80}\b(aman|aplikasi|hapus)\b", "Cyber Security", "Ancaman aplikasi Android terhadap keamanan mobile banking merupakan risiko siber konkret."),
    (r"\b(registrasi sim biometrik|biometrik wajah)\b.{0,100}\b(sim|registrasi|telkomsel|grapari)\b", "Cyber Security", "Sistem identitas biometrik untuk registrasi SIM berkaitan dengan identitas digital dan privasi data."),
    (r"\b(data pribadi|transfer data)\b.{0,80}\b(as|amerika serikat|lintas negara|pemerintah)\b", "Cyber Security", "Transfer data lintas negara dan perlindungan data pribadi merupakan isu tata kelola/privasi digital."),
    (r"\bapple\b.{0,80}\bumkm\b.{0,100}\b(kelola karyawan|mengelola karyawan|konten)\b", "Enterprise Software", "Use case teknologi untuk pengelolaan karyawan/operasional UMKM merupakan penerapan software bisnis."),
    (r"\bpendapatan induk google\b.{0,80}\bcloud\b", "Cloud Enterprise", "Kinerja bisnis Google Cloud menjadi sinyal pasar cloud enterprise."),
    (r"\bak amai\b.{0,80}\b(ai grid|nvidia|rtx pro)\b|\bakamai\b.{0,80}\b(ai grid|nvidia|rtx pro)\b", "Enterprise Data & AI", "Implementasi infrastruktur AI/GPU oleh Akamai merupakan perkembangan AI komputasi/edge."),
    (r"\b5g ai ran\b|\bai ran\b", "Enterprise Data & AI", "Penerapan AI-RAN pada jaringan operator adalah use case AI untuk infrastruktur telekomunikasi."),
]



# V5 rules informed by the V4 holdout-style sample review.
# Important: V2-V4 audit labels available so far were generated/assisted using title
# and excerpts. These remain candidate business rules; do not treat them as independent
# ground truth until a domain reviewer validates the articles.
V5_OUT_OF_SCOPE_RULES = [
    (r"\bkaryawan meta\b.{0,100}\b(wfh|phk|pemutusan hubungan kerja|vonis phk)\b",
     "Berita berfokus pada kebijakan kerja/PHK internal perusahaan dan tidak menunjukkan isu teknologi enterprise yang konkret."),
    (r"\b(adu cepat internet|tes kecepatan internet)\b.{0,100}\b(semifinalis|piala dunia|argentina|sepak bola)\b",
     "Perbandingan kecepatan internet hanya menjadi unsur trivia/hiburan olahraga, bukan analisis infrastruktur digital."),
    (r"\bharga tv\b.{0,80}\b(anjlok|turun|murah|penyebab)\b",
     "Fokusnya tren harga elektronik konsumen, bukan komputasi enterprise atau infrastruktur digital."),
]

V5_REVIEW_RULES = [
    (r"\bpemuda\.ai\b|\bplatform pengatur penggunaan token ai\b",
     "Platform manajemen penggunaan token AI bisa relevan untuk tata kelola AI, tetapi ringkasan belum cukup menjelaskan sasaran dan use case organisasinya."),
    (r"(?=.*\btelkomsel\b)(?=.*\btransformasi digital\b)(?=.*\b(wef|davos)\b)",
     "Pernyataan/promosi transformasi digital di forum belum menjelaskan implementasi atau hasil teknologi yang konkret."),
    (r"\b(sim card|kartu sim|registrasi sim|nomor hp|nomor telepon)\b.{0,100}\b(biometrik|biometrik wajah|face recognition|gugat|mahkamah konstitusi|kk)\b|\b(biometrik|face recognition)\b.{0,100}\b(sim card|kartu sim|registrasi sim|telkomsel|indosat|grapari)\b",
     "Berita registrasi SIM/biometrik menyentuh identitas digital dan privasi, tetapi perlu keputusan apakah kebijakan/layanan konsumen masuk cakupan utama."),
    (r"\bkomunitas pendorong internet untuk rakyat\b|\brelawan tik aceh\b",
     "Inisiatif komunitas inklusi digital relevan sebagai konteks, tetapi tidak menjelaskan implementasi teknologi/infrastruktur secara memadai pada judul."),
    (r"\bcegah penipuan digital\b.{0,100}\b(dana|dompet digital|lindungi pengguna)\b",
     "Panduan perlindungan pengguna layanan konsumen; perlu konsistensi batas cakupan antara threat intelligence konsumen dan ancaman organisasi."),
    (r"\bindustri telko\b.{0,100}\bmakin kompak\b|\bdemi indonesia emas 2045\b",
     "Pernyataan industri yang bersifat umum; belum ada teknologi, program operasional, atau infrastruktur spesifik yang bisa diklasifikasikan."),
    (r"\bxlsmart\b.{0,100}\b(operator 5g terbesar|klaim jadi operator 5g|terbesar di ri)\b",
     "Klaim promosi pangsa pasar operator; perlu bukti mengenai rollout, cakupan, kapasitas, atau arsitektur jaringan sebelum dilabeli relevan."),
    (r"\basal usul nomor hp\b.{0,100}\b(ganti operator|digugat|mk)\b|\bnomor hp tetap sama\b.{0,100}\b(ganti operator|mahkamah konstitusi|mk)\b",
     "Berita regulasi/portabilitas nomor lebih dominan daripada rincian teknologi atau infrastruktur; perlu keputusan cakupan kebijakan telekomunikasi."),
]

V5_RELEVANT_RULES = [
    # Ordered-independent phrasing variants observed in the V4 audit sample.
    (r"\binfranexia\b.{0,120}\bfiber optik\b|\bfiber optik\b.{0,120}\binfranexia\b", "Cloud Enterprise", "Pengelolaan jaringan fiber berskala besar adalah perkembangan infrastruktur konektivitas."),
    (r"(?=.*\bspektrum\b)(?=.*\b5g\b)(?=.*\b(ideal|maksimal|kapasitas|pengalaman)\b)", "Cloud Enterprise", "Spektrum merupakan faktor teknis penting bagi kapasitas dan kualitas layanan 5G."),
    (r"(?=.*\binternet dari langit\b)(?=.*\b(aturan|asosiasi|pasar|konektivitas|jaringan)\b)", "Cloud Enterprise", "Layanan internet berbasis platform udara/satelit dan regulasinya adalah bagian dari ekosistem infrastruktur digital."),
    (r"(?=.*\btelkom\b)(?=.*\bstrategi\b)(?=.*\bbangun infrastruktur digital\b)", "Cloud Enterprise", "Strategi pembangunan infrastruktur digital secara langsung termasuk cakupan infrastruktur enterprise."),
    # Network, spectrum, fiber, satellite and telecom service resilience.
    (r"\b(peta penguasaan frekuensi|hasil lelang frekuensi|lelang spektrum|spektrum frekuensi)\b", "Cloud Enterprise", "Kebijakan dan alokasi spektrum berpengaruh langsung pada kapasitas dan rollout jaringan operator."),
    (r"\b(haps|internet dari stratosfer|internet satelit|jaringan satelit|teknologi satelit|teknologi skymast)\b.{0,120}\b(5g|internet|konektivitas|wilayah 3t|pulau terpencil|sinyal|jaringan)\b|\b(mitratel|airbus|pelni|telkomsat|buanterone)\b.{0,100}\b(satelit|haps|konektivitas|komunikasi)\b", "Cloud Enterprise", "Teknologi satelit/HAPS untuk konektivitas adalah perkembangan infrastruktur komunikasi digital."),
    (r"\b(fiber optik|serat optik|kabel fiber|kabel laut|kabel bawah laut|kabel submarine|submarine cable)\b.{0,120}\b(infrastruktur|jaringan|konsorsium|penataan|bahan baku|naik|ekspansi|pengembangan|kelola|km fiber)\b|\b(penataan kabel|konsorsium fiber optik|bahan baku fiber optik)\b", "Cloud Enterprise", "Pengembangan/penataan fiber dan kabel laut berhubungan langsung dengan infrastruktur konektivitas."),
    (r"\b(5g private|private 5g|jaringan private 5g)\b|\b(bedanya 5g dengan 5g private)\b", "Cloud Enterprise", "Private 5G merupakan jaringan khusus yang dapat mendukung konektivitas operasional dan industri."),
    (r"\b(internet ri masih tertinggal|kualitas internet indonesia|1\.600 isp|1600 isp|internet bakti)\b|\b(wilayah 3t|perbatasan|pulau terpencil)\b.{0,100}\b(internet|konektivitas|satelit|jaringan|trafik)\b", "Cloud Enterprise", "Kapasitas ISP dan pemerataan konektivitas menggambarkan kondisi infrastruktur digital nasional."),
    (r"\b(bts|jaringan|layanan)\b.{0,100}\b(pulih|pemulihan|pulih 100%|pasca gempa|terdampak gempa|gangguan tinggal)\b|\b(pemulihan layanan|pulihkan jaringan)\b.{0,100}\b(indosat|xlsmart|telkomsel|bts|gempa)\b", "Cloud Enterprise", "Pemulihan jaringan/BTS menunjukkan resiliensi dan kontinuitas infrastruktur telekomunikasi."),
    (r"\b(otomatisasi dan aplikasi pintar|aplikasi pintar)\b.{0,100}\b(bisnis|kelola pekerja|karyawan|pekerja)\b|\bteknologi ubah cara bisnis kelola pekerja\b", "Enterprise Software", "Otomatisasi dan aplikasi untuk pengelolaan tenaga kerja merupakan use case software/proses bisnis."),
    # Explicit cyber incidents and consumer-to-enterprise threat signals, when concrete.
    (r"\b(2[,.]?8 miliar password dicuri|password dicuri sepanjang tahun|miliaran password dicuri)\b", "Cyber Security", "Pencurian kredensial berskala besar adalah indikator ancaman siber yang dapat berdampak lintas sektor."),
    (r"\b(scan|memindai)\b.{0,70}\b(qr code|kode qr)\b.{0,100}\b(ahli siber|bahaya|serangan|penipuan|peringatan)\b|\b(nekat scan sembarang qr code|scan sembarang qr code)\b", "Cyber Security", "Peringatan tentang pemindaian QR yang berisiko berkaitan dengan phishing dan rekayasa sosial."),
    (r"\b(ubah foto pribadi jadi animasi|foto pribadi jadi animasi)\b.{0,100}\b(ahli siber|peringatan|privasi|penyalahgunaan|bahaya)\b", "Cyber Security", "Penyalahgunaan foto dengan AI menimbulkan risiko privasi dan konten sintetis."),
    (r"\b(aplikasi ai)\b.{0,100}\b(bocorkan|bocor|kebocoran)\b.{0,100}\b(data|pengguna|jutaan)\b|\b(bocorkan jutaan data pengguna android|jutaan data pengguna android)\b", "Cyber Security", "Kebocoran data aplikasi adalah insiden keamanan/privasi konkret."),
    # Enterprise AI, AI-compute and semiconductor supply chain.
    (r"\b(lonjakan pemakaian ai|pemakaian ai)\b.{0,100}\b(perusahaan|storage|krisis storage|penyimpanan)\b", "Enterprise Data & AI", "Lonjakan beban AI dan kebutuhan storage adalah sinyal kapasitas infrastruktur data perusahaan."),
    (r"\b(lintasarta)\b.{0,100}\b( investasi ai|investasi ai|akselerasi digital|berbasis ai|ai di tengah)\b|\b(bpd)\b.{0,80}\b(berbasis ai|ai)\b.{0,80}\b(digital|transformasi|akselerasi)\b", "Enterprise Data & AI", "Investasi atau implementasi AI untuk layanan/perbankan organisasi merupakan use case enterprise."),
    (r"\b(nvidia|tsmc|amd|intel)\b.{0,100}\b(chip|semikonduktor|gpu|prosesor|ai|terafab|pasokan|pelanggan terbesar|hel i os|helios|pendapatan)\b|\b(chip|semikonduktor|gpu|prosesor|terafab|helios)\b.{0,100}\b(nvidia|tsmc|amd|intel)\b", "Enterprise Data & AI", "Berita langsung tentang rantai pasok chip/komputasi AI memberi sinyal kapasitas dan pasar infrastruktur AI."),
    (r"\b(pendapatan intel|intel cetak pendapatan|intel turun di q4)\b.{0,120}\b(ai|chip|pasokan|semikonduktor)\b", "Enterprise Data & AI", "Kinerja/ketahanan pasokan semikonduktor berkaitan dengan ekosistem komputasi dan AI."),
]


def _v5_override_result(topic: str, label: str, reason: str, cue: str) -> dict[str, Any]:
    if label == "Di Luar Cakupan":
        return result_out_of_scope("Aturan V5 berbasis pola audit: " + reason)
    confidence = "Tinggi" if label == "Relevan" else "Sedang"
    return {
        "sector3_topic": topic,
        "relevance_level": label,
        "matched_keywords": cue,
        "classification_reason": "Aturan V5 berbasis pola audit: " + reason,
        "title_topic_hits": cue,
        "content_topic_hits": "",
        "enterprise_context_hits": "",
        "market_context_hits": "",
        "sector3_topic_candidates": topic,
        "classification_confidence": confidence,
    }


def apply_v5_audit_overrides(title: str, content: str) -> dict[str, Any] | None:
    """Apply narrow V5 rules, then fall back to V4 overrides/general scoring."""
    combined = f"{title} {content}".strip()
    for pattern, reason in V5_OUT_OF_SCOPE_RULES:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return _v5_override_result("Di Luar Cakupan", "Di Luar Cakupan", reason, "aturan cakupan V5")
    for pattern, reason in V5_REVIEW_RULES:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return _v5_override_result("Perlu Tinjau", "Perlu Tinjau", reason, "aturan review V5")
    for pattern, topic, reason in V5_RELEVANT_RULES:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return _v5_override_result(topic, "Relevan", reason, f"V5 audit override: {topic}")
    # Existing V4 overrides are retained for previously observed, narrowly specified cases.
    legacy = apply_v4_audit_overrides(title)
    if legacy is not None:
        # Keep a transparent V4 reason; this identifies rules carried forward unchanged.
        return legacy
    return None


def _audit_override_result(topic: str, label: str, reason: str, cue: str) -> dict[str, Any]:
    if label == "Di Luar Cakupan":
        return result_out_of_scope("Aturan V4 berbasis audit: " + reason)
    confidence = "Tinggi" if label == "Relevan" else "Sedang"
    return {
        "sector3_topic": topic,
        "relevance_level": label,
        "matched_keywords": cue,
        "classification_reason": "Aturan V4 berbasis audit: " + reason,
        "title_topic_hits": cue,
        "content_topic_hits": "",
        "enterprise_context_hits": "",
        "market_context_hits": "",
        "sector3_topic_candidates": topic,
        "classification_confidence": confidence,
    }


def apply_v4_audit_overrides(title: str) -> dict[str, Any] | None:
    """Apply narrow, explicit title rules learned from the V3 disagreement audit."""
    for pattern, reason in AUDIT_OUT_OF_SCOPE_RULES:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return _audit_override_result("Di Luar Cakupan", "Di Luar Cakupan", reason, "aturan cakupan V4")
    for pattern, reason in AUDIT_REVIEW_RULES:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return _audit_override_result("Perlu Tinjau", "Perlu Tinjau", reason, "aturan review V4")
    for pattern, topic, reason in AUDIT_RELEVANT_RULES:
        if re.search(pattern, title, flags=re.IGNORECASE):
            cue = f"V4 audit override: {topic}"
            return _audit_override_result(topic, "Relevan", reason, cue)
    return None


def classify_article(row: pd.Series) -> dict[str, Any]:
    title = normalize_text(row.get("title", ""))
    # Supports clean dataset ('content') and the audit sample ('content_excerpt').
    content = normalize_text(row.get("content", row.get("content_excerpt", "")))
    combined = f"{title} {content}".strip()

    audit_override = apply_v5_audit_overrides(title, content)
    if audit_override is not None:
        return audit_override

    if any(re.search(p, title, flags=re.IGNORECASE) for p in HARD_OUT_OF_SCOPE_PATTERNS):
        return result_out_of_scope("Tidak termasuk cakupan: istilah ERP merujuk pada kebijakan jalan berbayar.")

    topic_signals = {
        topic: score_topic(title, content, rules)
        for topic, rules in TOPIC_RULES.items()
    }
    nonzero = {topic: sig for topic, sig in topic_signals.items() if sig["score"] > 0}
    if not nonzero:
        return result_out_of_scope("Tidak ditemukan indikator teknologi yang cukup spesifik untuk cakupan Sector 3.")

    # Best topic: highest weighted score; stable order only breaks exact ties.
    ordered_topics = sorted(
        nonzero.keys(), key=lambda t: (-nonzero[t]["score"], list(TOPIC_RULES).index(t))
    )
    chosen_topic = ordered_topics[0]
    chosen = topic_signals[chosen_topic]
    second_score = nonzero[ordered_topics[1]]["score"] if len(ordered_topics) > 1 else 0.0
    close_competition = len(ordered_topics) > 1 and abs(chosen["score"] - second_score) < 1.1

    title_context = find_matches(title, ORG_CONTEXT)
    content_context = find_matches(content, ORG_CONTEXT)
    market_context = find_matches(combined, MARKET_OR_DEPLOYMENT_CONTEXT)
    has_org_context = bool(title_context or content_context)
    has_market_context = bool(market_context)
    consumer_only = bool(matched_patterns(title, CONSUMER_ONLY_PATTERNS))
    off_topic = bool(matched_patterns(title, OFF_TOPIC_PATTERNS))
    any_title_topic_signal = any(
        sig["title_strong"] or sig["title_weak"] for sig in topic_signals.values()
    )
    # Prevent incidental body mentions (e.g. a generic earnings/celebrity story
    # mentioning Oracle or cloud) from becoming an in-scope item. If the headline
    # signals an organization but not a topic, retain it for review below.
    headline_has_tech_context = bool(matched_patterns(title, HEADLINE_TECH_CONTEXT))
    if not any_title_topic_signal and not headline_has_tech_context:
        # V2 dropped every article whose headline was not technology-oriented,
        # even when the full body had strong technology signals plus enterprise/market context.
        # V3 sends those borderline cases to review instead of automatically excluding them.
        body_has_strong_signal = any(sig["content_strong"] for sig in topic_signals.values())
        body_has_specific_enterprise_cue = bool(matched_patterns(content, BODY_ENTERPRISE_CUES))
        if (body_has_strong_signal and body_has_specific_enterprise_cue
                and (has_org_context or has_market_context) and not consumer_only and not off_topic):
            return build_result(
                chosen_topic, "Perlu Tinjau", chosen, title_context, content_context, market_context,
                "Rendah",
                "Judul tidak menyebut teknologi secara eksplisit, tetapi isi memuat sinyal teknologi yang kuat bersama konteks organisasi/pasar; perlu pemeriksaan isi lengkap sebelum dikeluarkan.",
                ordered_topics,
            )
        return result_out_of_scope(
            "Tidak ada sinyal teknologi yang memadai pada judul; kecocokan isi saja belum cukup untuk dimasukkan tanpa bukti kuat lain."
        )

    strong_title = bool(chosen["title_strong"])
    strong_content = chosen["content_strong"]
    weak_only = not strong_title and not strong_content
    strong_cyber = chosen_topic == "Cyber Security" and (strong_title or bool(strong_content))

    # A weak ambiguous token in an unmistakably unrelated headline must not be
    # labelled relevant. Other ambiguous cases are retained for human review.
    if off_topic and weak_only:
        return result_out_of_scope(
            "Kata kunci bersifat ambigu dan konteks utama artikel tidak terkait teknologi enterprise."
        )

    # General consumer how-to/promotion stories are excluded unless the article
    # describes a concrete technical cyber incident/threat or enterprise context.
    if consumer_only and not (chosen_topic == "Cyber Security" and strong_title) and not title_context:
        return result_out_of_scope(
            "Fokus judul adalah layanan/panduan konsumen; kata kunci teknologi dalam isi tidak cukup untuk mengubahnya menjadi berita enterprise."
        )

    # Direct cyber threats are in scope because threat intelligence can be useful
    # even if the immediate victim/user is a consumer. Weak-only 'hacker' mentions
    # do not qualify automatically.
    if chosen_topic == "Cyber Security" and strong_cyber:
        # Require the headline to establish the incident/topic, or at least a weak
        # cyber term in the headline corroborated by a strong technical signal in body.
        title_establishes_cyber = strong_title or (bool(chosen["title_weak"]) and bool(strong_content))
        if close_competition and not strong_title:
            relevance = "Perlu Tinjau"
            confidence = "Sedang"
            reason = "Sinyal keamanan siber ada, tetapi ada topik lain dengan kekuatan serupa; perlu validasi topik utama."
        elif title_establishes_cyber:
            relevance = "Relevan"
            confidence = "Tinggi" if strong_title else "Sedang"
            reason = "Judul mengindikasikan isu keamanan siber dan isi mendukung dengan indikator teknis (misalnya malware, phishing, kerentanan, atau kebocoran data)."
        else:
            relevance = "Perlu Tinjau"
            confidence = "Rendah"
            reason = "Indikator keamanan siber ditemukan di isi, tetapi judul belum cukup membuktikan bahwa itu fokus utama artikel."
        return build_result(chosen_topic, relevance, chosen, title_context, content_context, market_context,
                            confidence, reason, ordered_topics)

    # Network/data-centre infrastructure is intrinsically within the digital
    # infrastructure remit; provider names or generic bandwidth alone are not.
    infra_terms = {
        "data center", "data centre", "pusat data", "ai factory", "cloud computing",
        "komputasi awan", "hybrid cloud", "private cloud", "public cloud", "migrasi cloud",
        "cloud infrastructure", "infrastruktur cloud", "kabel laut", "kabel bawah laut",
        "submarine cable", "backbone internet", "interkoneksi data center", "cloud region",
        "colocation", "data center tier iv", "konektivitas data center", "high-performance computing",
        "infrastruktur telekomunikasi", "infrastruktur konektivitas", "spektrum frekuensi",
        "frekuensi 700 mhz", "frekuensi 2,6 ghz", "frekuensi 2.6 ghz", "menara telekomunikasi",
        "jaringan 6g", "teknologi 6g", "b2b ict", "solusi b2b ict", "solusi ict",
        "pabrik ram", "pabrik chip", "pabrik semikonduktor", "semikonduktor", "chip memori", "memori dram",
    }
    infra_title = any(t in chosen["title_strong"] for t in infra_terms)
    infra_content = any(t in chosen["content_strong"] for t in infra_terms)

    software_terms = {
        "enterprise software", "software enterprise", "aplikasi enterprise", "aplikasi bisnis",
        "software bisnis", "sistem erp", "enterprise resource planning", "cloud erp",
        "sap cloud erp", "sap s/4hana", "salesforce", "microsoft dynamics", "workday",
        "servicenow", "oracle netsuite", "procurement software", "supply chain management",
        "customer relationship management", "platform crm", "sistem crm", "aplikasi crm",
        "contact center", "contact centre", "customer experience platform", "omnichannel",
        "crm platform", "customer service platform", "ai gateway", "lintas channel",
        "respons pelanggan", "transformasi hris", "hris perusahaan", "lisensi windows",
        "pembajakan windows", "aktivasi windows", "pengelolaan lisensi software",
        "pembajakan software", "perusahaan software", "aplikasi erp", "sistem erp perusahaan",
    }
    software_specific = any(t in chosen["title_strong"] for t in software_terms)
    digital_specific = any(t in chosen["title_strong"] for t in {
        "transformasi digital", "digital transformation", "otomatisasi bisnis", "otomasi proses bisnis",
        "integrasi sistem", "modernisasi sistem", "industri 4.0", "smart factory",
        "digitalisasi layanan", "digitalisasi operasional", "solusi ict terintegrasi",
        "data maritim", "ais data", "kedaulatan digital",
    })
    ai_market_cues = any(term in combined for term in [
        "chip ai", "gpu ai", "ai factory", "kapasitas komputasi", "investasi ai",
        "pendanaan ai", "pasar ai", "permintaan chip", "server ai", "infrastruktur komputasi ai",
        "pelatihan model ai", "data center", "hyperscaler", "chip memori", "semikonduktor",
    ])
    ai_use_case_title = bool(matched_patterns(title, AI_USE_CASE_PATTERNS))
    ai_use_case_content = bool(matched_patterns(content, AI_USE_CASE_PATTERNS))

    if chosen_topic == "Cloud Enterprise" and (
        infra_title or (bool(chosen["title_weak"]) and infra_content and (has_org_context or has_market_context))
    ):
        relevance = "Relevan"
        confidence = "Tinggi" if infra_title else "Sedang"
        reason = "Judul menunjukkan infrastruktur cloud/data center/konektivitas, atau istilah cloud pada judul diperkuat bukti infrastruktur di isi."
    elif chosen_topic == "Enterprise Software" and (software_specific and (has_org_context or has_market_context)):
        relevance = "Relevan"
        confidence = "Tinggi" if has_org_context else "Sedang"
        reason = "Ada indikator software enterprise yang spesifik beserta konteks organisasi, implementasi, atau bisnis."
    elif chosen_topic == "Digital Transformation" and (digital_specific and (has_org_context or has_market_context)):
        relevance = "Relevan"
        confidence = "Tinggi" if has_org_context else "Sedang"
        reason = "Transformasi/digitalisasi dikaitkan dengan layanan organisasi, proses operasional, integrasi, atau implementasi teknologi."
    elif chosen_topic == "Enterprise Data & AI" and (
        (strong_title and (has_org_context or has_market_context or ai_market_cues))
        or (ai_use_case_title and (has_org_context or has_market_context))
        or (ai_use_case_content and has_org_context and has_market_context and (strong_title or strong_content))
    ):
        relevance = "Relevan"
        confidence = "Tinggi" if (strong_title or ai_use_case_title) and (has_org_context or ai_market_cues) else "Sedang"
        reason = "Ada sinyal AI/data yang spesifik atau pola use case AI, didukung konteks penerapan organisasi, infrastruktur, atau pasar teknologi."
    elif weak_only and not has_org_context and not has_market_context:
        relevance = "Perlu Tinjau"
        confidence = "Rendah"
        reason = "Hanya ditemukan kata kunci ambigu; konteks enterprise/penerapan belum cukup untuk label Relevan."
    elif (strong_title or strong_content) and (has_org_context or has_market_context):
        relevance = "Perlu Tinjau"
        confidence = "Sedang"
        reason = "Topik teknologi dan konteks organisasi/pasar terdeteksi, tetapi hubungan langsung dengan cakupan Sector 3 belum cukup kuat."
    elif (strong_title or strong_content) and not (has_org_context or has_market_context):
        relevance = "Perlu Tinjau"
        confidence = "Rendah"
        reason = "Topik teknologi terdeteksi, tetapi relevansi enterprise atau konteks penerapan belum terlihat jelas."
    else:
        relevance = "Perlu Tinjau"
        confidence = "Rendah"
        reason = "Kecocokan hanya berupa sinyal lemah; perlu validasi manual sebelum dimasukkan ke insight."

    if close_competition and relevance == "Relevan" and not strong_title:
        relevance = "Perlu Tinjau"
        confidence = "Sedang"
        reason = "Dua kategori teknologi memiliki bukti yang hampir seimbang dan judul belum mengunci kategori utama; perlu verifikasi. " + reason

    return build_result(chosen_topic, relevance, chosen, title_context, content_context, market_context,
                        confidence, reason, ordered_topics)


def result_out_of_scope(reason: str) -> dict[str, Any]:
    return {
        "sector3_topic": "Di Luar Cakupan",
        "relevance_level": "Di Luar Cakupan",
        "matched_keywords": "",
        "classification_reason": reason,
        "title_topic_hits": "",
        "content_topic_hits": "",
        "enterprise_context_hits": "",
        "market_context_hits": "",
        "sector3_topic_candidates": "",
        "classification_confidence": "Tinggi",
    }


def build_result(
    topic: str,
    relevance: str,
    signal: dict[str, Any],
    title_context: list[str],
    content_context: list[str],
    market_context: list[str],
    confidence: str,
    reason: str,
    topic_candidates: list[str],
) -> dict[str, Any]:
    return {
        "sector3_topic": topic,
        "relevance_level": relevance,
        "matched_keywords": ", ".join(signal["all_matches"]),
        "classification_reason": reason,
        "title_topic_hits": ", ".join(signal["title_strong"] + signal["title_weak"]),
        "content_topic_hits": ", ".join(signal["content_strong"] + signal["content_weak"]),
        "enterprise_context_hits": ", ".join(list(dict.fromkeys(title_context + content_context))),
        "market_context_hits": ", ".join(market_context),
        "sector3_topic_candidates": ", ".join(topic_candidates[:3]),
        "classification_confidence": confidence,
    }


def main() -> None:
    print("=" * 72)
    print("FILTERING DETIK.COM - SECTOR 3 (V5 CANDIDATE, AUDIT-INFORMED)")
    print("=" * 72)
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    print(f"Input dataset: {len(df):,} baris")
    required = {"title", "url", "published_at", "content", "channel", "source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {sorted(missing)}")
    if df.empty:
        raise ValueError("Dataset input kosong; proses filtering dihentikan.")

    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    before_date_filter = len(df)
    df = df[df["published_at"].notna() & (df["published_at"].dt.year == TARGET_YEAR)].copy()
    print(f"Artikel tanpa tanggal valid/di luar {TARGET_YEAR}: {before_date_filter - len(df)}")
    if df.empty:
        raise ValueError("Tidak ada artikel valid tahun 2026. File output lama tidak ditimpa.")

    original_cols = list(df.columns)
    classifications = df.apply(classify_article, axis=1, result_type="expand")
    # Avoid accidentally duplicating classification columns if the input is rerun from an old classified file.
    df = df.drop(columns=[c for c in classifications.columns if c in df.columns], errors="ignore")
    df = pd.concat([df.reset_index(drop=True), classifications.reset_index(drop=True)], axis=1)

    relevant = df[df["relevance_level"] == "Relevan"].copy()
    review = df[df["relevance_level"] == "Perlu Tinjau"].copy()
    out_scope = df[df["relevance_level"] == "Di Luar Cakupan"].copy()

    OUTPUT_ALL.parent.mkdir(parents=True, exist_ok=True)
    for frame, path in [
        (df, OUTPUT_ALL),
        (relevant, OUTPUT_RELEVANT),
        (review, OUTPUT_REVIEW),
        (out_scope, OUTPUT_OUT_OF_SCOPE),
    ]:
        frame.to_csv(path, index=False, encoding="utf-8-sig")

    # Comparison with prior classification when present.
    old_file = DATA_DIR / "detik_sector3_filtered_all_classified_v4.csv"
    if old_file.exists():
        old = pd.read_csv(old_file, encoding="utf-8-sig")
        keys = [k for k in ["article_id", "url"] if k in old.columns and k in df.columns]
        if keys:
            old_small = old[keys + [c for c in ["relevance_level", "sector3_topic"] if c in old.columns]].copy()
            new_small = df[keys + ["relevance_level", "sector3_topic"]].copy()
            old_small = old_small.rename(columns={"relevance_level": "relevance_level_v4", "sector3_topic": "sector3_topic_v4"})
            new_small = new_small.rename(columns={"relevance_level": "relevance_level_v5", "sector3_topic": "sector3_topic_v5"})
            report = old_small.merge(new_small, on=keys, how="outer", indicator=True)
            report["status_changed"] = report["relevance_level_v4"].fillna("") != report["relevance_level_v5"].fillna("")
            report["topic_changed"] = report["sector3_topic_v4"].fillna("") != report["sector3_topic_v5"].fillna("")
            report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")
            print(f"Comparison report: {OUTPUT_REPORT}")
            print("\nPerubahan status (V4 -> V5):")
            print(pd.crosstab(report["relevance_level_v4"], report["relevance_level_v5"], dropna=False).to_string())

    print("\nHASIL V5 CANDIDATE")
    print(f"Semua terklasifikasi : {OUTPUT_ALL} ({len(df):,})")
    print(f"Relevan              : {OUTPUT_RELEVANT} ({len(relevant):,})")
    print(f"Perlu Tinjau         : {OUTPUT_REVIEW} ({len(review):,})")
    print(f"Di Luar Cakupan      : {OUTPUT_OUT_OF_SCOPE} ({len(out_scope):,})")
    print("\nDistribusi status:")
    print(df["relevance_level"].value_counts(dropna=False).to_string())
    print("\nDistribusi topik pada artikel Relevan:")
    print(relevant["sector3_topic"].value_counts(dropna=False).to_string())
    print("\nPerhatian: hasil tetap berbasis aturan; validasi sampel manual diperlukan sebelum dijadikan ground truth bisnis.")


if __name__ == "__main__":
    main()
