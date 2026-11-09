from __future__ import annotations

"""ANTARA Search Sector 3 filtering V4.

V4 is a conservative, auditable rule-based classifier for ANTARA Search records
whose available text consists of title + short search-result summary (summary-only).
It does not fetch article pages or infer facts absent from the supplied text.

Default input:
    data/processed/antara_search_cleaned.csv

Outputs (all versioned; V1/V2/V3 are not overwritten):
    antara_search_all_classified_v4.csv
    antara_search_filtered_v4.csv
    antara_search_review_v4.csv
    antara_search_out_of_scope_v4.csv
    antara_search_filter_report_v4.csv
    antara_search_filter_comparison_v3_v4.csv (when V3 output exists)
    antara_search_review_audit_v4.csv
"""

import argparse
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


# ============================================================================
# 1. PATHS AND CONTRACT
# ============================================================================

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PROJECT_DIR / "data" / "processed"
DEFAULT_INPUT = DEFAULT_DATA_DIR / "antara_search_cleaned.csv"

OUTPUT_NAMES = {
    "all": "antara_search_all_classified_v4.csv",
    "relevant": "antara_search_filtered_v4.csv",
    "review": "antara_search_review_v4.csv",
    "out_scope": "antara_search_out_of_scope_v4.csv",
    "report": "antara_search_filter_report_v4.csv",
    "comparison": "antara_search_filter_comparison_v3_v4.csv",
    "review_audit": "antara_search_review_audit_v4.csv",
}

VERSION = "antara_search_v4_candidate_summary_only"
EXPECTED_CONTENT_STATUS = "summary_only"
TOPIC_ORDER = [
    "Cloud Enterprise",
    "Cyber Security",
    "Digital Transformation",
    "Enterprise Software",
]

REQUIRED_COLUMNS = [
    "article_id",
    "source",
    "channel",
    "title",
    "title_clean",
    "url",
    "published_at",
    "summary",
    "summary_clean",
    "prepared_text",
    "content",
    "content_status",
    "content_preparation_status",
    "cleaning_status",
    "search_query",
]

SCORE_COLUMNS = {
    "Cloud Enterprise": "topic_score_cloud_enterprise",
    "Cyber Security": "topic_score_cyber_security",
    "Digital Transformation": "topic_score_digital_transformation",
    "Enterprise Software": "topic_score_enterprise_software",
}


# ============================================================================
# 2. FOUR-TOPIC TAXONOMY
#    Generic AI/digital mentions are intentionally not strong by themselves.
# ============================================================================

TOPIC_RULES: dict[str, dict[str, list[str]]] = {
    "Cloud Enterprise": {
        "strong": [
            "sovereign cloud", "cloud-native infrastructure", "cloud computing",
            "komputasi awan", "hybrid cloud", "private cloud", "public cloud",
            "cloud migration", "migrasi cloud", "cloud infrastructure",
            "infrastruktur cloud", "cloud region", "cloud platform",
            "data center", "data centre", "pusat data", "interkoneksi data center",
            "konektivitas data center", "hyperscaler", "colocation",
            "backbone internet", "jaringan backbone", "kabel laut",
            "kabel bawah laut", "submarine cable", "infrastruktur telekomunikasi",
            "infrastruktur konektivitas", "infrastruktur digital", "digital infrastructure",
            "pusat komputasi", "high-performance computing", "high performance computing",
            "infrastruktur komputasi ai", "ai factory", "kapasitas komputasi",
            "menara telekomunikasi", "spektrum frekuensi", "frekuensi 700 mhz",
            "frekuensi 2,6 ghz", "frekuensi 2.6 ghz", "jaringan 5g", "jaringan 6g",
            "teknologi 6g", "fiber optik", "serat optik", "kabel fiber optik",
            "private 5g", "jaringan private 5g", "managed services", "b2b ict",
            "solusi b2b ict", "infrastruktur jaringan fiber", "jaringan fiber optik",
        ],
        "weak": [
            "cloud", "google cloud", "aws", "amazon web services", "microsoft azure",
            "server", "gpu", "komputasi", "bandwidth", "interkoneksi",
            "infrastruktur jaringan", "satelit", "internet satelit", "jaringan satelit",
            "konektivitas", "telekomunikasi", "storage", "penyimpanan data",
        ],
    },
    "Cyber Security": {
        "strong": [
            "keamanan siber", "keamanan cyber", "cyber security", "cybersecurity",
            "serangan siber", "ancaman siber", "spionase digital", "spionase siber",
            "operasi siber", "kejahatan siber", "penjahat siber", "ransomware",
            "malware", "phishing", "smishing", "spyware", "zero-day", "zero day",
            "celah keamanan", "kerentanan keamanan", "eksploitasi keamanan",
            "data breach", "kebocoran data", "kebocoran informasi", "pencurian data",
            "pencurian kredensial", "social engineering", "rekayasa sosial",
            "serangan ddos", "botnet", "backdoor", "trojan", "serangan hacker",
            "serangan api", "akun dibobol", "password stealer", "insider threat",
            "cyber warfare", "perang siber", "tautan berbahaya", "tautan palsu",
            "link palsu", "penipuan digital", "modus penipuan digital", "serangan proxy",
            "industrial cyber resilience", "cyber resilience", "ot cyber", "industrial cyber",
            "keamanan jaringan industri", "perlindungan jaringan industri",
            "ancaman komputasi kuantum", "domain abuse", "domain abuse data exchange",
            "firewall upgrade", "network security", "intrusion detection", "intrusion prevention",
            "endpoint detection", "security operations center", "keamanan produk digital",
            "product security", "perlindungan sistem", "akses tidak sah",
        ],
        "weak": [
            "hacker", "peretas", "peretasan", "diretas", "dibobol", "membobol", "bobol",
            "serangan digital", "keamanan digital", "data bocor", "privasi data",
            "perlindungan data", "enkripsi", "firewall", "zero trust", "keamanan informasi",
            "keamanan data",
        ],
    },
    "Digital Transformation": {
        "strong": [
            "transformasi digital", "digital transformation", "transformasi digital korporasi",
            "digitalisasi korporasi", "digitalisasi perusahaan", "digitalisasi operasional",
            "digitalisasi layanan", "digitalisasi industri", "otomatisasi bisnis",
            "otomasi proses bisnis", "otomatisasi proses bisnis", "otomatisasi proses",
            "integrasi sistem", "modernisasi sistem", "modernisasi aplikasi",
            "proses bisnis digital", "workflow automation", "otomatisasi workflow",
            "industri 4.0", "smart factory", "sistem digital terintegrasi",
            "solusi ict terintegrasi", "solusi digital enterprise", "layanan digital pemerintah",
            "digitalisasi pelayanan publik", "implementasi ai", "penerapan ai",
            "adopsi ai perusahaan", "otomatisasi berbasis ai", "ai untuk operasional",
            "ai dalam operasional", "ai untuk proses bisnis", "ai dalam proses bisnis",
            "ai untuk layanan perusahaan", "agen ai untuk karyawan", "agen ai untuk operasional",
            "smart manufacturing", "manufaktur pintar", "integrasi proses bisnis",
            "transformasi operasional", "otomatisasi alur kerja", "digitalisasi proses bisnis",
        ],
        "weak": [
            "digitalisasi", "adopsi teknologi", "teknologi digital", "operasional digital",
            "efisiensi operasional", "otomatisasi", "otomasi", "inovasi teknologi",
            "layanan digital", "platform digital",
        ],
    },
    "Enterprise Software": {
        "strong": [
            "enterprise software", "software enterprise", "aplikasi enterprise",
            "aplikasi bisnis", "software bisnis", "enterprise resource planning",
            "sistem erp", "aplikasi erp", "software erp", "erp platform", "cloud erp",
            "sap s/4hana", "sap cloud erp", "microsoft dynamics", "oracle netsuite",
            "salesforce platform", "customer relationship management", "platform crm",
            "sistem crm", "aplikasi crm", "crm platform", "human resource management system",
            "sistem hris", "sistem hcm", "aplikasi sdm perusahaan", "supply chain management",
            "procurement software", "software procurement", "software rantai pasok",
            "business intelligence", "contact center platform", "customer experience platform",
            "customer service platform", "omnichannel platform", "ai gateway untuk perusahaan",
            "ai dalam sistem erp", "ai dalam platform crm", "klikpajak", "aplikasi perpajakan",
            "software pajak", "platform perpajakan", "software terintegrasi perusahaan",
            "enterprise software terintegrasi", "sistem pengelolaan pajak",
            "enterprise content management", "content management system",
            "document management system", "document management", "content services platform",
            "business process management", "workflow management system", "application integration",
            "integration platform as a service", "ipaas", "software manajemen dokumen",
            "sistem manajemen dokumen", "platform integrasi aplikasi", "software manajemen sdm",
            "sistem informasi sumber daya manusia", "human capital management",
        ],
        "weak": [
            "erp", "sap", "oracle", "crm", "hris", "hcm", "saas",
            "software perusahaan", "aplikasi perusahaan", "sistem informasi",
            "platform bisnis", "document workflow", "workflow software", "aplikasi pajak",
        ],
    },
}


# ============================================================================
# 3. CONTEXT, AI MAPPING, AND EXCLUSION RULES
# ============================================================================

ORG_CONTEXT = [
    "perusahaan", "korporasi", "enterprise", "b2b", "bumn", "instansi pemerintah",
    "kementerian", "pemerintah daerah", "organisasi", "sektor publik", "perbankan",
    "bank", "pabrik", "industri", "operasional perusahaan", "rantai pasok",
    "sistem produksi", "data pelanggan", "sistem perusahaan", "sistem internal",
    "karyawan", "layanan korporasi", "pelanggan korporasi", "pengguna enterprise",
    "contact center", "pusat data", "data center", "cloud region", "interkoneksi",
    "operator telekomunikasi", "perusahaan energi", "infrastruktur jaringan",
    "layanan publik", "rumah sakit", "perusahaan teknologi", "operator seluler",
    "layanan digital korporasi", "direktorat jenderal", "lembaga pemerintah",
]

SPECIFIC_ENTERPRISE_CUES = [
    "b2b", "enterprise", "layanan korporasi", "solusi ict", "solusi digital enterprise",
    "digitalisasi korporasi", "implementasi erp", "implementasi sap", "sistem erp perusahaan",
    "sistem crm", "sistem hris", "data center", "data centre", "pusat data",
    "infrastruktur cloud", "infrastruktur digital", "infrastruktur telekomunikasi",
    "infrastruktur konektivitas", "kabel laut", "backbone internet", "kapasitas komputasi",
    "workflow automation", "otomatisasi proses bisnis", "operasional perusahaan",
    "sistem produksi", "pengelolaan rantai pasok", "layanan perusahaan",
    "penerapan ai di perusahaan", "ai untuk operasional", "klikpajak", "software pajak",
    "enterprise content management", "document management system", "ipass", "procurement software",
]

MARKET_OR_DEPLOYMENT_CONTEXT = [
    "investasi", "pendanaan", "ekspansi", "membangun", "pembangunan", "belanja modal",
    "kapasitas komputasi", "rantai pasok", "pasar chip", "permintaan chip", "akuisisi",
    "kontrak", "implementasi", "mengimplementasikan", "meluncurkan solusi",
    "diadopsi perusahaan", "adopsi ai", "menggunakan sap", "menggunakan erp",
    "otomatisasi workflow", "proses bisnis", "operasi jaringan", "kapasitas data center",
    "pengembangan data center", "pengembangan jaringan", "rollout jaringan",
    "penerapan sistem", "transformasi operasional", "layanan komersial", "pengadaan sistem",
    "mempercepat proses", "meningkatkan produktivitas", "mengelola karyawan",
]

CONCRETE_ACTION_CUES = [
    "menerapkan", "penerapan", "implementasi", "mengimplementasikan", "mengadopsi",
    "adopsi", "meluncurkan", "mengintegrasikan", "integrasi", "otomatisasi", "otomasi",
    "memodernisasi", "modernisasi", "mengembangkan", "pengembangan", "menggunakan",
    "memanfaatkan", "mempercepat proses", "meningkatkan produktivitas", "mengelola karyawan",
    "memperkuat kinerja", "memperkuat operasional", "membangun sistem", "membangun platform",
]

AI_CONTEXT_PATTERNS: dict[str, list[str]] = {
    "Cyber Security": [
        r"(?P<left>\b(?:ai|kecerdasan buatan|agen ai|model ai)\b).{0,80}(?P<right>\b(?:bobol|membobol|dibobol|serangan|ancaman|malware|phishing|keamanan|siber)\b)",
        r"(?P<left>\b(?:bobol|membobol|dibobol|serangan|ancaman|malware|phishing|keamanan|siber)\b).{0,80}(?P<right>\b(?:ai|kecerdasan buatan|agen ai|model ai)\b)",
    ],
    "Cloud Enterprise": [
        r"(?P<left>\b(?:ai|kecerdasan buatan)\b).{0,70}(?P<right>\b(?:data center|pusat data|gpu|kapasitas komputasi|server|cloud|infrastruktur|storage)\b)",
        r"(?P<left>\b(?:data center|pusat data|gpu|kapasitas komputasi|server|cloud|infrastruktur|storage)\b).{0,70}(?P<right>\b(?:ai|kecerdasan buatan)\b)",
    ],
    "Enterprise Software": [
        r"(?P<left>\b(?:ai|kecerdasan buatan|agen ai)\b).{0,65}(?P<right>\b(?:erp|crm|hris|hcm|software bisnis|aplikasi bisnis|content management|document management|workflow|sistem perusahaan)\b)",
        r"(?P<left>\b(?:erp|crm|hris|hcm|software bisnis|aplikasi bisnis|content management|document management|workflow|sistem perusahaan)\b).{0,65}(?P<right>\b(?:ai|kecerdasan buatan|agen ai)\b)",
    ],
    "Digital Transformation": [
        r"(?P<left>\b(?:implementasi|penerapan|adopsi|otomatisasi|otomasi|transformasi|mengintegrasikan|meningkatkan produktivitas|memperkuat kinerja)\b).{0,60}(?P<right>\b(?:ai|kecerdasan buatan|agen ai|machine learning)\b)",
        r"(?P<left>\b(?:ai|kecerdasan buatan|agen ai|machine learning)\b).{0,65}(?P<right>\b(?:operasional|proses bisnis|workflow|produksi|manufaktur|layanan|perusahaan|industri|karyawan|tenaga kerja)\b)",
        r"(?P<left>\b(?:operasional|proses bisnis|workflow|produksi|manufaktur|layanan|perusahaan|industri|karyawan|tenaga kerja)\b).{0,65}(?P<right>\b(?:ai|kecerdasan buatan|agen ai|machine learning)\b)",
    ],
}

# Generic exclusions are applied only when no sufficiently specific topic evidence
# or concrete deployment evidence overrides them. They are not broad keyword bans.
CLEAR_OUT_OF_SCOPE_RULES: list[dict[str, str]] = [
    {
        "rule_id": "nontech_financial_results",
        "pattern": r"\b(?:catat|mencatat|membukukan|raih)\b.{0,65}\b(?:laba bersih|laba|pendapatan|penghargaan finansial|financial awards)\b",
        "reason": "Judul berfokus pada kinerja keuangan atau penghargaan finansial tanpa isu teknologi Sector 3 yang spesifik.",
    },
    {
        "rule_id": "nontech_corporate_governance_award",
        "pattern": r"\b(?:gcg awards|good corporate governance|indonesia excellence gcg awards)\b",
        "reason": "Berita berfokus pada tata kelola korporasi/penghargaan, bukan implementasi teknologi atau layanan digital.",
    },
    {
        "rule_id": "nontech_general_award",
        "pattern": r"\b(?:raih|meraih|menerima|umumkan)\b.{0,75}\b(?:penghargaan|award|awards)\b",
        "reason": "Fokus berita adalah penghargaan; tidak ada rincian penerapan teknologi yang cukup pada judul dan ringkasan.",
    },
    {
        "rule_id": "nontech_education_talent",
        "pattern": r"\b(?:beasiswa|siswa berprestasi|talenta muda|pemuda jadi inovator|mencetak talenta|cetak talenta|meraih gelar doktor|raih doktor|gelar doktor|riset doktor)\b",
        "reason": "Fokus berita adalah pendidikan, beasiswa, atau pengembangan talenta, bukan penerapan teknologi pada operasi organisasi.",
    },
    {
        "rule_id": "nontech_health_story",
        "pattern": r"\b(?:keterlambatan penanganan stroke|tambal gigi di puskesmas)\b",
        "reason": "Fokus utama berita adalah layanan/kondisi kesehatan; tidak ada bukti bahwa topik utamanya termasuk empat cakupan Sector 3.",
    },
    {
        "rule_id": "nontech_sustainability_profile",
        "pattern": r"\b(?:laporan keberlanjutan|sustainability report)\b",
        "reason": "Berita berfokus pada laporan keberlanjutan perusahaan tanpa sinyal implementasi teknologi yang spesifik.",
    },
    {
        "rule_id": "nontech_hajj_finance_forum",
        "pattern": r"\b(?:hajj fund forum|dana haji|dana keberlanjutan dana haji)\b",
        "reason": "Fokus berita adalah forum/pengelolaan dana haji, bukan teknologi enterprise.",
    },
    {
        "rule_id": "nontech_agriculture_event",
        "pattern": r"\b(?:pertanian rendah emisi|forum pertukaran pengetahuan pertanian)\b",
        "reason": "Fokus berita adalah forum pertanian/keberlanjutan dan tidak menunjukkan teknologi dalam empat topik Sector 3.",
    },
    {
        "rule_id": "nontech_engineering_event",
        "pattern": r"\b(?:iee series|indonesia energy & engineering|praktik berkelanjutan)\b",
        "reason": "Fokus berita adalah agenda industri/rekayasa umum, tanpa rincian IT enterprise atau infrastruktur digital.",
    },
    {
        "rule_id": "nontech_executive_appointment",
        "pattern": r"\b(?:tunjuk|menunjuk|diangkat|ditunjuk)\b.{0,90}\b(?:country gm|general manager|direktur utama|chief executive officer|ceo)\b",
        "reason": "Fokus berita adalah penunjukan pimpinan; tidak ada perkembangan teknologi atau implementasi layanan digital yang dibahas.",
    },
    {
        "rule_id": "nontech_academic_conference",
        "pattern": r"\b(?:siswa|mahasiswa|pemuda)\b.{0,90}\b(?:konferensi|conference|forum|beasiswa)\b",
        "reason": "Fokus berita adalah partisipasi pendidikan/konferensi, bukan penggunaan teknologi enterprise.",
    },
    {
        "rule_id": "nontech_gaming_safety_feature",
        "pattern": r"\bpengembang gim\b.{0,100}\b(?:kekerasan seksual|fitur keselamatan|sarana pencegahan)\b",
        "reason": "Fokus berita adalah fitur keselamatan/kebijakan pada gim konsumen, bukan sistem enterprise atau salah satu dari empat topik Sector 3.",
    },
]

HARD_OUT_OF_SCOPE_PATTERNS = [
    r"\belectronic road pricing\b",
    r"\bjalan berbayar\b",
    r"\bojek online\b.{0,60}\berp\b",
    r"\berp\b.{0,60}\b(?:ruas jalan|jalan berbayar)\b",
]

CONSUMER_ONLY_PATTERNS = [
    r"\bpaket (?:internet|data|kuota)\b",
    r"\btarif internet\b",
    r"\bbeli kuota\b",
    r"\bbonus kuota\b",
    r"\bcara (?:mengaktifkan|cek|menggunakan)\b.{0,55}\b(?:paket|kuota|roaming|sinyal|coverage)\b",
    r"\b(?:paket roaming|roaming haji)\b",
    r"\bsmart home\b",
    r"\bgame pc\b",
    r"\bharga (?:iphone|ponsel|smartphone|tv)\b",
    r"\b(?:review|rekomendasi) smartphone\b",
    r"\bseberapa cepat\b.{0,40}\b(?:5g|wifi|internet rumah)\b",
]

SPECIAL_REVIEW_RULES: list[dict[str, str]] = [
    {
        "rule_id": "health_tech_screening_use_case_review",
        "pattern": r"\bherlens\b|\bdeteksi kanker serviks\b",
        "topic": "Belum Ditentukan",
        "reason": "Berita berpotensi membahas solusi teknologi kesehatan, tetapi snippet belum menjelaskan apakah ada software, AI, atau sistem digital yang termasuk cakupan Sector 3.",
    },
    {
        "rule_id": "cyber_conference_event_review",
        "pattern": r"\bgovware\b.{0,140}\b(?:pemimpin keamanan siber|keamanan siber global|agentic ai)\b|\b(?:pemimpin keamanan siber global|konferensi keamanan siber)\b",
        "topic": "Cyber Security",
        "reason": "Berita berfokus pada agenda/forum keamanan siber; relevansi teknisnya perlu diperiksa sebelum dianggap sebagai intelijen ancaman atau solusi.",
    },
    {
        "rule_id": "eucc_network_camera_certification",
        "pattern": r"\beucc\b.{0,100}\bnetwork camera\b|\bnetwork camera\b.{0,100}\beucc\b",
        "topic": "Cyber Security",
        "reason": "Sertifikasi EUCC pada network camera berpotensi berkaitan dengan keamanan produk, tetapi snippet belum menjelaskan ruang lingkup sertifikasinya.",
    },
    {
        "rule_id": "government_data_security_context",
        "pattern": r"\bdukcapil\b.{0,100}\bkeamanan data\b|\bkeamanan data\b.{0,100}\bdukcapil\b",
        "topic": "Cyber Security",
        "reason": "Perlindungan data lembaga pemerintah terdeteksi, tetapi snippet belum menunjukkan kontrol atau insiden keamanan yang konkret.",
    },
    {
        "rule_id": "enterprise_content_agentic_platform_review",
        "pattern": r"\bhyland\b.{0,120}\b(?:agentic enterprise|konten|data pelanggan)\b|\bagentic enterprise\b.{0,120}\b(?:konten|data pelanggan)\b",
        "topic": "Enterprise Software",
        "reason": "Platform berbasis konten untuk enterprise berpotensi merupakan enterprise content management; detail fungsi dan penerapan belum cukup pada snippet.",
    },
    {
        "rule_id": "ai_commerce_platform_review",
        "pattern": r"\bsynagie\b.{0,120}\b(?:ai commerce|ekosistem|platform)\b|\bai commerce\b.{0,120}\b(?:platform|ekosistem)\b",
        "topic": "Enterprise Software",
        "reason": "Platform AI Commerce berpotensi menjadi software bisnis, tetapi fungsi dan pengguna organisasinya perlu diverifikasi.",
    },
    {
        "rule_id": "enterprise_hr_data_workflow_review",
        "pattern": r"\bheb construction\b.{0,150}\b(?:data sdm|respons tender|sumber data)\b|\bdata sdm\b.{0,100}\b(?:tender|karyawan|perusahaan)\b",
        "topic": "Enterprise Software",
        "reason": "Penggunaan data SDM untuk respons tender menunjukkan workflow bisnis, tetapi sistem/software yang digunakan belum jelas.",
    },
    {
        "rule_id": "public_digital_border_system_review",
        "pattern": r"\bpagar digital\b.{0,120}\b(?:imigrasi|pengawasan perbatasan)\b|\b(?:imigrasi|pengawasan perbatasan)\b.{0,120}\bpagar digital\b",
        "topic": "Digital Transformation",
        "reason": "Sistem digital untuk pengawasan perbatasan berpotensi menjadi use case pemerintah, tetapi mekanisme dan teknologi belum cukup dijelaskan.",
    },
    {
        "rule_id": "b2b_ict_service_expansion_review",
        "pattern": r"\btelkom solution\b.{0,120}\bb2b ict\b|\bb2b ict\b.{0,120}\b(?:enterprise|telkom)\b",
        "topic": "Cloud Enterprise",
        "reason": "Layanan B2B ICT dan pasar enterprise terdeteksi, tetapi komponen infrastruktur/layanan teknis spesifik perlu diperiksa.",
    },
    {
        "rule_id": "enterprise_ai_infrastructure_vendor_review",
        "pattern": r"\baltos\b.{0,120}\b(?:infrastruktur enterprise|beban kerja ai|workload ai)\b|\b(?:infrastruktur enterprise|beban kerja ai|workload ai)\b.{0,120}\baltos\b",
        "topic": "Cloud Enterprise",
        "reason": "Solusi infrastruktur untuk beban kerja AI berpotensi terkait komputasi enterprise, tetapi spesifikasi infrastruktur belum tampak di snippet.",
    },
    {
        "rule_id": "enterprise_storage_solution_review",
        "pattern": r"\b(?:hiksemi|penyimpanan data)\b.{0,120}\b(?:ai|solusi penyimpanan|storage)\b",
        "topic": "Cloud Enterprise",
        "reason": "Solusi penyimpanan data dapat menjadi komponen infrastruktur, tetapi konteks data center/enterprise belum cukup jelas.",
    },
]

# Narrow, explainable overrides for explicit solution/incident evidence observed in
# the current baseline. Rules are text-based (not article-ID based) and remain subject
# to a human audit; confidence is not automatically set to High.
RELEVANT_RULES: list[dict[str, str]] = [
    {
        "rule_id": "industrial_cyber_resilience_center",
        "pattern": r"\bindustrial cyber resilience center\b|\bot cyber\b",
        "topic": "Cyber Security",
        "reason": "Judul menyebut pusat ketahanan siber industri/OT Cyber secara eksplisit.",
        "confidence": "Tinggi",
    },
    {
        "rule_id": "ai_agent_government_system_breach",
        "pattern": r"\b(?:agen ai|model kecerdasan buatan|openai)\b.{0,100}\b(?:bobol|membobol|dibobol)\b.{0,70}\b(?:portal|sistem pemerintah)\b|\b(?:bobol|membobol|dibobol)\b.{0,70}\bportal pemerintah\b",
        "topic": "Cyber Security",
        "reason": "Judul/ringkasan menunjukkan insiden akses tidak sah terhadap portal atau sistem pemerintah.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "proactive_cybersecurity_service",
        "pattern": r"\bhorizon3\b.{0,120}\b(?:keamanan proaktif|cybersecurity|keamanan siber)\b|\b(?:keamanan proaktif berbasis ai|industrial cyber resilience)\b",
        "topic": "Cyber Security",
        "reason": "Fokus berita adalah solusi atau layanan keamanan siber proaktif.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "domain_abuse_data_exchange",
        "pattern": r"\bidadx\b|\bdomain abuse data exchange\b",
        "topic": "Cyber Security",
        "reason": "IDADX disebut sebagai pertukaran data penyalahgunaan domain untuk membantu perlindungan ekosistem domain.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "bssn_ai_cyber_threat",
        "pattern": r"\bbssn\b.{0,130}\b(?:serangan siber|ancaman siber|lanskap serangan)\b|\b(?:serangan siber|ancaman siber)\b.{0,100}\b(?:ai|kecerdasan buatan)\b.{0,80}\b(?:keuangan|perbankan|finansial)\b",
        "topic": "Cyber Security",
        "reason": "Berita mengaitkan AI dengan serangan/ancaman siber pada sektor keuangan.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "mekari_tax_business_software",
        "pattern": r"\bmekari\b.{0,100}\bklikpajak\b|\bklikpajak\b.{0,100}\b(?:bukti potong|perpajakan|pajak)\b",
        "topic": "Enterprise Software",
        "reason": "Klikpajak disebut sebagai layanan software untuk proses perpajakan bisnis yang terintegrasi.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "scaleocean_erp_business_software",
        "pattern": r"\bscaleocean\b.{0,130}\berp\b|\berp\b.{0,130}\bscaleocean\b",
        "topic": "Enterprise Software",
        "reason": "ERP ditawarkan untuk mengatasi bottleneck operasional perusahaan; fungsi software bisnisnya eksplisit.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "integrated_enterprise_software",
        "pattern": r"\bintegrasi software\b.{0,120}\bperusahaan\b|\benterprise software terintegrasi\b",
        "topic": "Enterprise Software",
        "reason": "Judul/ringkasan menyebut kebutuhan integrasi enterprise software pada proses perusahaan.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "corporate_ai_agents_workforce",
        "pattern": r"\b(?:indosat|perusahaan)\b.{0,120}\b(?:agen ai|ai agent)\b.{0,120}\b(?:karyawan|produktivitas|operasional)\b|\b(?:agen ai|ai agent)\b.{0,100}\b(?:karyawan|produktivitas kerja)\b",
        "topic": "Digital Transformation",
        "reason": "Agen AI ditujukan untuk produktivitas karyawan atau proses operasional organisasi.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "agentic_ai_manufacturing_operations",
        "pattern": r"\b(?:agen ai terkelola|agentic ai|ai agents?)\b.{0,120}\b(?:operasi manufaktur|manufaktur|produksi)\b|\b(?:operasi manufaktur|manufaktur|produksi)\b.{0,120}\b(?:agen ai terkelola|agentic ai|ai agents?)\b",
        "topic": "Digital Transformation",
        "reason": "Kemitraan memperkenalkan agen AI ke dalam operasi manufaktur, menunjukkan use case AI pada proses operasional industri.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "smart_manufacturing_industry_40",
        "pattern": r"\b(?:nec|manufaktur)\b.{0,130}\b(?:smart manufacturing|manufaktur pintar|industri 4\.0|transformasi industri)\b|\b(?:smart manufacturing|manufaktur pintar)\b",
        "topic": "Digital Transformation",
        "reason": "Solusi manufaktur pintar/Industri 4.0 merupakan use case transformasi proses industri.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "quantum_computing_cyber_threat",
        "pattern": r"\bkomputasi kuantum\b.{0,100}\b(?:ancaman|keamanan data|perlindungan data)\b|\b(?:ancaman|keamanan data|perlindungan data)\b.{0,100}\bkomputasi kuantum\b",
        "topic": "Cyber Security",
        "reason": "Judul secara eksplisit membahas ancaman komputasi kuantum terhadap keamanan data; detail ancaman masih perlu verifikasi.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "firewall_security_technical_publication",
        "pattern": r"\bhuawei\b.{0,100}\bfirewall upgrade\b|\bfirewall upgrade\b.{0,100}\btechnical white paper\b",
        "topic": "Cyber Security",
        "reason": "Publikasi teknis secara spesifik membahas peningkatan firewall, yaitu teknologi keamanan jaringan.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "spionage_digital_threat_intelligence",
        "pattern": r"\bancaman spionase digital\b|\bspionase digital\b.{0,100}\b(?:data|informasi|strategis)\b",
        "topic": "Cyber Security",
        "reason": "Judul membahas spionase digital dan perlindungan informasi strategis, yang merupakan isu threat intelligence/data security.",
        "confidence": "Sedang",
    },
    {
        "rule_id": "iif_digital_financing_platform_process_improvement",
        "pattern": r"\biif\b.{0,180}\b(?:platform digital|memangkas waktu|penilaian awal pembiayaan)\b|\bplatform digital\b.{0,140}\b(?:pembiayaan infrastruktur|penilaian awal)\b",
        "topic": "Digital Transformation",
        "reason": "Platform digital IIF dikaitkan dengan percepatan proses penilaian awal pembiayaan infrastruktur; ringkasan menyebut dampak efisiensi proses bisnis.",
        "confidence": "Sedang",
    },
]


# ============================================================================
# 4. TEXT MATCHING AND SCORING HELPERS
# ============================================================================


def normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"[\u200b-\u200f\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@lru_cache(maxsize=512)
def _compiled_terms(terms: tuple[str, ...]) -> re.Pattern[str] | None:
    if not terms:
        return None
    ordered = sorted(terms, key=len, reverse=True)
    branches = [re.escape(term.lower()) for term in ordered]
    return re.compile(r"(?<!\w)(?:" + "|".join(branches) + r")(?!\w)", re.IGNORECASE)


def find_term_evidence(text: str, terms: list[str]) -> list[str]:
    """Return actual matched phrases from text, never raw regex definitions."""
    if not text or not terms:
        return []
    pattern = _compiled_terms(tuple(terms))
    if pattern is None:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        phrase = re.sub(r"\s+", " ", match.group(0)).strip()
        key = phrase.casefold()
        if key not in seen:
            seen.add(key)
            found.append(phrase)
    return found


def find_pattern_evidence(text: str, patterns: list[str]) -> list[str]:
    """Return the literal text that matched each regex pattern."""
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        try:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                named_parts = [value for value in match.groupdict().values() if value]
                if len(named_parts) >= 2:
                    phrase = " ↔ ".join(re.sub(r"\s+", " ", value).strip() for value in named_parts)
                else:
                    phrase = re.sub(r"\s+", " ", match.group(0)).strip()
                if not phrase:
                    continue
                key = phrase.casefold()
                if key not in seen:
                    seen.add(key)
                    found.append(phrase)
        except re.error as exc:
            raise ValueError(f"Regex rule tidak valid: {pattern!r}: {exc}") from exc
    return found


def normalize_url_key(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        parsed = urlparse(str(value).strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme.lower() != "https":
            return ""
        if not (host == "antaranews.com" or host.endswith(".antaranews.com")):
            return ""
        if not parsed.path.startswith("/berita/"):
            return ""
        if parsed.username or parsed.password:
            return ""
        return f"https://{host}{parsed.path.rstrip('/')}"
    except (TypeError, ValueError):
        return ""


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def score_topic(title: str, summary: str, rules: dict[str, list[str]]) -> dict[str, Any]:
    title_strong = find_term_evidence(title, rules["strong"])
    summary_strong = find_term_evidence(summary, rules["strong"])
    title_weak = find_term_evidence(title, rules["weak"])
    summary_weak = find_term_evidence(summary, rules["weak"])

    score = 0.0
    if title_strong:
        score += 5.0 + min(len(title_strong) - 1, 2) * 0.8
    score += min(len(summary_strong), 3) * 2.2
    if title_weak:
        score += 1.4 + min(len(title_weak) - 1, 2) * 0.3
    score += min(len(summary_weak), 3) * 0.55

    return {
        "score": round(score, 3),
        "title_strong": title_strong,
        "summary_strong": summary_strong,
        "title_weak": title_weak,
        "summary_weak": summary_weak,
        "all_matches": list(dict.fromkeys(title_strong + title_weak + summary_strong + summary_weak)),
        "contextual_ai_hits": [],
    }


def get_context(title: str, summary: str) -> dict[str, list[str]]:
    combined = f"{title} {summary}".strip()
    return {
        "title_org": find_term_evidence(title, ORG_CONTEXT),
        "summary_org": find_term_evidence(summary, ORG_CONTEXT),
        "specific_enterprise": find_term_evidence(combined, SPECIFIC_ENTERPRISE_CUES),
        "market": find_term_evidence(combined, MARKET_OR_DEPLOYMENT_CONTEXT),
        "actions": find_term_evidence(combined, CONCRETE_ACTION_CUES),
    }


def add_contextual_ai_signals(
    signals: dict[str, dict[str, Any]], title: str, summary: str
) -> None:
    combined = f"{title} {summary}".strip()
    for topic, patterns in AI_CONTEXT_PATTERNS.items():
        evidence = find_pattern_evidence(combined, patterns)
        if evidence:
            signals[topic]["contextual_ai_hits"] = evidence
            signals[topic]["score"] = round(signals[topic]["score"] + 1.35, 3)


def topic_evidence_summary(signals: dict[str, dict[str, Any]]) -> str:
    parts: list[str] = []
    for topic in TOPIC_ORDER:
        evidence = signals[topic]["all_matches"] + signals[topic]["contextual_ai_hits"]
        if evidence:
            parts.append(f"{topic}: " + ", ".join(dict.fromkeys(evidence)))
    return " | ".join(parts)


def summary_is_truncated(summary: str) -> bool:
    text = str(summary or "").rstrip()
    return text.endswith(("...", "…"))


def classify_non_sector(title: str, summary: str, has_specific_topic: bool) -> dict[str, str] | None:
    """Apply narrowly-scoped non-sector rules only when no specific technical evidence exists."""
    combined = f"{title} {summary}".strip()
    if has_specific_topic:
        return None
    for rule in CLEAR_OUT_OF_SCOPE_RULES:
        if re.search(rule["pattern"], combined, flags=re.IGNORECASE):
            return rule
    return None


def find_special_rule(
    title: str, summary: str, rules: list[dict[str, str]]
) -> dict[str, str] | None:
    combined = f"{title} {summary}".strip()
    for rule in rules:
        match = re.search(rule["pattern"], combined, flags=re.IGNORECASE)
        if match:
            enriched = dict(rule)
            enriched["evidence"] = re.sub(r"\s+", " ", match.group(0)).strip()
            return enriched
    return None


# ============================================================================
# 5. RESULT BUILDERS
# ============================================================================


def build_result(
    *,
    topic: str,
    relevance: str,
    confidence: str,
    reason: str,
    signals: dict[str, dict[str, Any]],
    contexts: dict[str, list[str]],
    candidates: list[str],
    title: str,
    summary: str,
    rule_id: str = "",
    rule_evidence: str = "",
    review_priority: str = "Low",
    manual_review_recommended: bool | None = None,
) -> dict[str, Any]:
    selected = signals.get(topic, {})
    title_hits = list(dict.fromkeys(selected.get("title_strong", []) + selected.get("title_weak", [])))
    summary_hits = list(dict.fromkeys(selected.get("summary_strong", []) + selected.get("summary_weak", [])))
    topical_all = list(dict.fromkeys(
        phrase
        for name in TOPIC_ORDER
        for phrase in (signals[name]["all_matches"] + signals[name]["contextual_ai_hits"])
    ))
    contextual_ai = list(dict.fromkeys(
        phrase
        for name in TOPIC_ORDER
        for phrase in signals[name]["contextual_ai_hits"]
    ))
    enterprise_context = list(dict.fromkeys(
        contexts["title_org"] + contexts["summary_org"] + contexts["specific_enterprise"]
    ))
    evidence = []
    if title_hits:
        evidence.append("title=" + ", ".join(title_hits))
    if summary_hits:
        evidence.append("summary=" + ", ".join(summary_hits))
    if contextual_ai:
        evidence.append("contextual_ai=" + ", ".join(contextual_ai))
    if enterprise_context:
        evidence.append("enterprise_context=" + ", ".join(enterprise_context))
    if contexts["market"]:
        evidence.append("market_context=" + ", ".join(contexts["market"]))
    if rule_evidence:
        evidence.append("rule_match=" + rule_evidence)
    if not evidence:
        evidence.append("Tidak ada frasa topik/konteks yang cocok pada title atau summary yang tersedia.")

    if manual_review_recommended is None:
        manual_review_recommended = relevance == "Perlu Tinjau"

    result: dict[str, Any] = {
        "sector3_topic": topic,
        "relevance_level": relevance,
        "matched_keywords": "; ".join(topical_all),
        "title_topic_hits": "; ".join(title_hits),
        "summary_topic_hits": "; ".join(summary_hits),
        "contextual_ai_hits": "; ".join(contextual_ai),
        "enterprise_context_hits": "; ".join(enterprise_context),
        "market_context_hits": "; ".join(contexts["market"]),
        "topic_candidates": "; ".join(candidates) if candidates else "Belum Ditentukan",
        "classification_confidence": confidence,
        "classification_reason": reason,
        "classification_evidence": " | ".join(evidence),
        "classification_version": VERSION,
        "classification_method": "rule_based_title_summary_only_v4",
        "classification_rule_override": rule_id,
        "classification_rule_evidence": rule_evidence,
        "review_priority": review_priority,
        "manual_review_recommended": bool(manual_review_recommended),
        "summary_character_count": len(summary.strip()),
        "summary_truncated_indicator": summary_is_truncated(summary),
    }
    for topic, column in SCORE_COLUMNS.items():
        result[column] = signals[topic]["score"]
    result["topic_evidence_by_category"] = topic_evidence_summary(signals)
    return result


def build_out_of_scope(
    reason: str,
    signals: dict[str, dict[str, Any]],
    contexts: dict[str, list[str]],
    candidates: list[str],
    title: str,
    summary: str,
    rule_id: str,
    confidence: str = "Sedang",
    rule_evidence: str = "",
) -> dict[str, Any]:
    return build_result(
        topic="Di Luar Cakupan",
        relevance="Di Luar Cakupan",
        confidence=confidence,
        reason=reason,
        signals=signals,
        contexts=contexts,
        candidates=candidates,
        title=title,
        summary=summary,
        rule_id=rule_id,
        rule_evidence=rule_evidence,
        review_priority="Low",
        manual_review_recommended=False,
    )


# ============================================================================
# 6. CLASSIFICATION
# ============================================================================


def classify_article(row: pd.Series, duplicate_id: bool, duplicate_url: bool) -> dict[str, Any]:
    title = normalize_text(row.get("title_clean") or row.get("title", ""))
    summary = normalize_text(row.get("summary_clean") or row.get("summary", ""))
    combined = f"{title} {summary}".strip()

    signals = {
        topic: score_topic(title, summary, rules)
        for topic, rules in TOPIC_RULES.items()
    }
    add_contextual_ai_signals(signals, title, summary)
    contexts = get_context(title, summary)

    ranked = sorted(
        [topic for topic in TOPIC_ORDER if signals[topic]["score"] > 0],
        key=lambda topic: (-signals[topic]["score"], TOPIC_ORDER.index(topic)),
    )
    candidates = ranked[:4]
    chosen_topic = ranked[0] if ranked else "Belum Ditentukan"

    # Metadata/contract validation. Any failure goes to review, never silently dropped.
    metadata_errors: list[str] = []
    if not str(row.get("article_id", "")).strip():
        metadata_errors.append("article_id kosong")
    if str(row.get("cleaning_status", "")).strip().lower() != "valid":
        metadata_errors.append("cleaning_status bukan valid")
    if str(row.get("content_preparation_status", "")).strip().lower() != "ready":
        metadata_errors.append("content_preparation_status bukan ready")
    if str(row.get("content_status", "")).strip().lower() != EXPECTED_CONTENT_STATUS:
        metadata_errors.append("content_status bukan summary_only")
    if str(row.get("content", "")).strip():
        metadata_errors.append("content terisi padahal status summary_only")
    if not summary:
        metadata_errors.append("summary_clean kosong")
    if not normalize_url_key(row.get("url", "")):
        metadata_errors.append("URL ANTARA tidak valid")
    date_value = pd.to_datetime(
    row.get("published_at", ""),
    errors="coerce",
    utc=True
    )
    if pd.isna(date_value):
        metadata_errors.append("published_at tidak valid")
    if duplicate_id:
        metadata_errors.append("article_id duplikat")
    if duplicate_url:
        metadata_errors.append("URL duplikat")

    if metadata_errors:
        return build_result(
            topic=chosen_topic,
            relevance="Perlu Tinjau",
            confidence="Rendah",
            reason="Validasi prasyarat data gagal: " + "; ".join(metadata_errors),
            signals=signals,
            contexts=contexts,
            candidates=candidates,
            title=title,
            summary=summary,
            rule_id="metadata_validation_review",
            review_priority="High",
        )

    # Explicitly outside Sector 3 (for example, alternate meanings of ERP).
    hard_out = find_pattern_evidence(combined, HARD_OUT_OF_SCOPE_PATTERNS)
    if hard_out:
        return build_out_of_scope(
            "Terkena aturan pengecualian eksplisit di luar cakupan Sector 3: " + ", ".join(hard_out),
            signals, contexts, candidates, title, summary, "hard_out_of_scope_pattern", "Tinggi",
            "; ".join(hard_out)
        )

    any_specific_topic = any(
        signals[topic]["title_strong"] or signals[topic]["summary_strong"]
        for topic in TOPIC_ORDER
    )
    non_sector = classify_non_sector(title, summary, any_specific_topic)
    if non_sector:
        return build_out_of_scope(
            non_sector["reason"], signals, contexts, candidates, title, summary,
            non_sector["rule_id"], "Sedang",
            find_pattern_evidence(combined, [non_sector["pattern"]])[0] if find_pattern_evidence(combined, [non_sector["pattern"]]) else ""
        )

    # Specific cases where the snippet supports a review, but not an automatic approval.
    special_review = find_special_rule(title, summary, SPECIAL_REVIEW_RULES)
    if special_review:
        return build_result(
            topic=special_review["topic"],
            relevance="Perlu Tinjau",
            confidence="Sedang",
            reason=special_review["reason"],
            signals=signals,
            contexts=contexts,
            candidates=list(dict.fromkeys([special_review["topic"]] + candidates)),
            title=title,
            summary=summary,
            rule_id=special_review["rule_id"],
            rule_evidence=special_review.get("evidence", ""),
            review_priority="High",
        )

    # Narrow text-based rules for explicit incidents and business-software use cases.
    relevant_rule = find_special_rule(title, summary, RELEVANT_RULES)
    if relevant_rule:
        return build_result(
            topic=relevant_rule["topic"],
            relevance="Relevan",
            confidence=relevant_rule["confidence"],
            reason=relevant_rule["reason"],
            signals=signals,
            contexts=contexts,
            candidates=list(dict.fromkeys([relevant_rule["topic"]] + candidates)),
            title=title,
            summary=summary,
            rule_id=relevant_rule["rule_id"],
            rule_evidence=relevant_rule.get("evidence", ""),
            review_priority="Low",
            manual_review_recommended=False,
        )

    if not ranked:
        # A truncated search snippet cannot prove absence of a relevant topic.
        # Keep it in Review unless a clear non-sector rule above matched.
        if summary_is_truncated(summary) or len(summary) < 220:
            return build_result(
                topic="Belum Ditentukan",
                relevance="Perlu Tinjau",
                confidence="Rendah",
                reason="Tidak ditemukan sinyal topik yang cukup pada judul/snippet; ringkasan terpotong sehingga relevansi belum dapat dipastikan.",
                signals=signals,
                contexts=contexts,
                candidates=[],
                title=title,
                summary=summary,
                rule_id="insufficient_truncated_source_text",
                review_priority="Low",
            )
        return build_out_of_scope(
            "Tidak ditemukan indikator teknologi yang cukup spesifik pada judul maupun ringkasan yang tersedia.",
            signals, contexts, candidates, title, summary, "no_topic_signal_complete_text", "Sedang"
        )

    chosen = signals[chosen_topic]
    second_score = signals[ranked[1]]["score"] if len(ranked) > 1 else 0.0
    score_gap = round(chosen["score"] - second_score, 3)
    close_competition = len(ranked) > 1 and score_gap < 1.25

    has_org_context = bool(contexts["title_org"] or contexts["summary_org"])
    has_specific_enterprise = bool(contexts["specific_enterprise"])
    has_market_context = bool(contexts["market"])
    has_enterprise_support = has_specific_enterprise or (has_org_context and has_market_context)
    combined_has_action = bool(contexts["actions"])
    truncated = summary_is_truncated(summary)

    # Consumer-oriented content is excluded only when there is no direct cyber
    # incident and no specific enterprise implementation signal.
    consumer_evidence = find_pattern_evidence(title, CONSUMER_ONLY_PATTERNS)
    cyber_direct = bool(
        signals["Cyber Security"]["title_strong"]
        or signals["Cyber Security"]["summary_strong"]
    )
    if consumer_evidence and not cyber_direct and not has_specific_enterprise:
        return build_out_of_scope(
            "Fokus judul merupakan layanan/panduan konsumen; tidak ditemukan bukti kuat penerapan enterprise atau ancaman siber konkret.",
            signals, contexts, candidates, title, summary, "consumer_only_without_enterprise_or_cyber"
        )

    # If the top two categories are close, do not automatically force a primary topic.
    runner_up = ranked[1] if len(ranked) > 1 else None
    runner_up_only_weak = bool(runner_up) and not (
        signals[runner_up]["title_strong"] or signals[runner_up]["summary_strong"]
    )
    selected_has_strong_title = bool(chosen["title_strong"])
    if close_competition and not (selected_has_strong_title and runner_up_only_weak):
        return build_result(
            topic=chosen_topic,
            relevance="Perlu Tinjau",
            confidence="Sedang",
            reason=f"Skor dua topik teratas berdekatan (selisih {score_gap}); topik utama perlu diverifikasi.",
            signals=signals,
            contexts=contexts,
            candidates=candidates,
            title=title,
            summary=summary,
            rule_id="close_topic_competition",
            review_priority="High",
        )

    # Cyber Security: direct threats/incidents and security technology are in scope.
    if chosen_topic == "Cyber Security":
        cyber_title_strong = bool(chosen["title_strong"])
        cyber_summary_strong = bool(chosen["summary_strong"])
        if cyber_title_strong and (cyber_summary_strong or has_org_context or has_market_context or chosen["contextual_ai_hits"]):
            return build_result(
                topic=chosen_topic,
                relevance="Relevan",
                confidence="Tinggi" if cyber_summary_strong and not truncated else "Sedang",
                reason="Judul memuat ancaman/teknologi keamanan siber spesifik dan ringkasan atau konteks mendukung fokus keamanan.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="direct_cyber_title_and_support",
                review_priority="Low", manual_review_recommended=False,
            )
        if cyber_title_strong:
            return build_result(
                topic=chosen_topic,
                relevance="Perlu Tinjau",
                confidence="Sedang",
                reason="Judul memuat istilah keamanan siber spesifik, tetapi ringkasan belum cukup menguatkan dampak, penerapan, atau konteks teknis.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="cyber_title_signal_needs_support",
                review_priority="High",
            )
        if cyber_summary_strong:
            return build_result(
                topic=chosen_topic,
                relevance="Perlu Tinjau",
                confidence="Sedang",
                reason="Ringkasan memuat indikator keamanan siber konkret, tetapi judul belum menegaskan isu tersebut sebagai fokus utama.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="cyber_summary_signal_needs_title",
                review_priority="Medium",
            )
        return build_result(
            topic=chosen_topic,
            relevance="Perlu Tinjau",
            confidence="Rendah",
            reason="Kecocokan keamanan siber masih berupa sinyal lemah/atribusi pakar; perlu bukti ancaman, kontrol, atau implementasi yang lebih spesifik.",
            signals=signals, contexts=contexts, candidates=candidates,
            title=title, summary=summary, rule_id="weak_cyber_signal",
            review_priority="Medium",
        )

    # Cloud Enterprise: infrastructure is a direct signal; generic provider names
    # and generic AI/cloud mentions are not enough on their own.
    if chosen_topic == "Cloud Enterprise":
        cloud_direct_title = find_term_evidence(title, [
            "sovereign cloud", "cloud-native infrastructure", "cloud computing", "komputasi awan",
            "hybrid cloud", "private cloud", "public cloud", "cloud infrastructure",
            "infrastruktur cloud", "data center", "data centre", "pusat data", "hyperscaler",
            "colocation", "backbone internet", "kabel laut", "kabel bawah laut", "submarine cable",
            "infrastruktur telekomunikasi", "infrastruktur konektivitas", "spektrum frekuensi",
            "fiber optik", "serat optik", "ai factory", "infrastruktur komputasi ai", "private 5g",
        ])
        if cloud_direct_title:
            return build_result(
                topic=chosen_topic,
                relevance="Relevan",
                confidence="Tinggi" if not truncated else "Sedang",
                reason="Judul secara eksplisit menunjukkan cloud, pusat data, komputasi, atau infrastruktur konektivitas.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="direct_cloud_infrastructure_title",
                review_priority="Low", manual_review_recommended=False,
            )
        if (chosen["title_strong"] or chosen["summary_strong"]) and has_enterprise_support:
            return build_result(
                topic=chosen_topic,
                relevance="Perlu Tinjau" if truncated else "Relevan",
                confidence="Sedang",
                reason="Sinyal cloud/konektivitas disertai konteks organisasi atau penerapan; detail infrastruktur masih perlu dipastikan dari snippet.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="cloud_signal_with_enterprise_context",
                review_priority="Medium" if truncated else "Low",
            )
        return build_result(
            topic=chosen_topic,
            relevance="Perlu Tinjau",
            confidence="Rendah",
            reason="Istilah cloud, jaringan, penyimpanan, atau komputasi ditemukan, tetapi bukti infrastruktur enterprise belum cukup spesifik.",
            signals=signals, contexts=contexts, candidates=candidates,
            title=title, summary=summary, rule_id="cloud_signal_needs_infrastructure_context",
            review_priority="Medium",
        )

    # Enterprise Software: require a recognizable business system/application or
    # a concrete enterprise workflow, not just generic 'platform'/'software'.
    if chosen_topic == "Enterprise Software":
        has_business_system = bool(chosen["title_strong"] or chosen["summary_strong"])
        if has_business_system and (has_specific_enterprise or has_org_context or has_market_context):
            return build_result(
                topic=chosen_topic,
                relevance="Relevan" if not truncated or chosen["title_strong"] else "Perlu Tinjau",
                confidence="Sedang",
                reason="Terdapat indikator aplikasi/sistem bisnis dan konteks organisasi, proses kerja, atau implementasi perusahaan.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="business_software_with_org_context",
                review_priority="Medium" if truncated else "Low",
            )
        return build_result(
            topic=chosen_topic,
            relevance="Perlu Tinjau",
            confidence="Rendah",
            reason="Software atau platform terdeteksi, tetapi fungsi aplikasi bisnis dan konteks penggunaan enterprise belum cukup jelas.",
            signals=signals, contexts=contexts, candidates=candidates,
            title=title, summary=summary, rule_id="software_signal_needs_business_context",
            review_priority="Medium",
        )

    # Digital Transformation: generic AI/digital words do not qualify. Require an
    # explicit process, service, workforce, manufacturing, or operational use case.
    if chosen_topic == "Digital Transformation":
        direct_transform_title = bool(chosen["title_strong"])
        direct_transform_summary = bool(chosen["summary_strong"])
        action_support = bool(contexts["actions"])
        use_case_patterns = [
            r"\b(?:ai|kecerdasan buatan|agen ai)\b.{0,65}\b(?:karyawan|tenaga kerja|operasional|proses bisnis|workflow|produksi|manufaktur|layanan perusahaan)\b",
            r"\b(?:karyawan|tenaga kerja|operasional|proses bisnis|workflow|produksi|manufaktur|layanan perusahaan)\b.{0,65}\b(?:ai|kecerdasan buatan|agen ai)\b",
            r"\b(?:otomatisasi|otomasi|integrasi sistem|modernisasi sistem|digitalisasi operasional|smart manufacturing|manufaktur pintar)\b",
        ]
        use_case_evidence = find_pattern_evidence(combined, use_case_patterns)
        has_use_case = bool(use_case_evidence) or (
            direct_transform_title and action_support and has_org_context
        )
        if (direct_transform_title or direct_transform_summary) and has_use_case and (has_org_context or has_market_context):
            return build_result(
                topic=chosen_topic,
                relevance="Relevan" if direct_transform_title else "Perlu Tinjau",
                confidence="Sedang",
                reason="Transformasi digital dikaitkan dengan use case proses/layanan/operasional organisasi; ringkasan tetap terbatas.",
                signals=signals, contexts=contexts, candidates=candidates,
                title=title, summary=summary, rule_id="digital_transformation_concrete_use_case",
                review_priority="Low" if direct_transform_title else "Medium",
                manual_review_recommended=not direct_transform_title,
            )
        return build_result(
            topic=chosen_topic,
            relevance="Perlu Tinjau",
            confidence="Rendah" if not has_org_context else "Sedang",
            reason="Sinyal digitalisasi/AI terdeteksi, tetapi belum cukup membuktikan perubahan proses, layanan, atau operasional organisasi.",
            signals=signals, contexts=contexts, candidates=candidates,
            title=title, summary=summary, rule_id="digital_signal_needs_concrete_use_case",
            review_priority="Medium" if has_org_context else "Low",
        )

    return build_result(
        topic=chosen_topic,
        relevance="Perlu Tinjau",
        confidence="Rendah",
        reason="Tidak ada aturan keputusan yang cukup kuat; diperlukan validasi manual.",
        signals=signals, contexts=contexts, candidates=candidates,
        title=title, summary=summary, rule_id="fallback_manual_review",
        review_priority="Low",
    )


# ============================================================================
# 7. INPUT, CLASSIFICATION, REPORTING, AND OUTPUTS
# ============================================================================


def load_data(input_file: Path) -> pd.DataFrame:
    if not input_file.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {input_file}")
    df = pd.read_csv(
        input_file,
        encoding="utf-8-sig",
        dtype={"article_id": "string"},
        keep_default_na=False,
    )
    if df.empty:
        raise ValueError("Dataset input kosong; filtering dihentikan.")
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {missing}")
    if df.columns.duplicated().any():
        dup_cols = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(f"Kolom duplikat ditemukan: {dup_cols}")
    return df


def classify_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    article_ids = out["article_id"].astype("string").fillna("").str.strip()
    id_duplicate = article_ids.ne("") & article_ids.duplicated(keep=False)
    url_keys = out["url"].apply(normalize_url_key)
    url_duplicate = url_keys.ne("") & url_keys.duplicated(keep=False)

    out["filter_duplicate_article_id"] = id_duplicate
    out["filter_duplicate_url"] = url_duplicate

    results = [
        classify_article(row, bool(id_duplicate.iloc[idx]), bool(url_duplicate.iloc[idx]))
        for idx, (_, row) in enumerate(out.iterrows())
    ]
    result_df = pd.DataFrame(results, index=out.index)
    out = out.drop(columns=list(result_df.columns), errors="ignore")
    return pd.concat([out.reset_index(drop=True), result_df.reset_index(drop=True)], axis=1)


def build_report(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(report_type: str, topic: str, metric: str, count: int, notes: str) -> None:
        rows.append({
            "report_type": report_type,
            "topic": topic,
            "metric": metric,
            "count": int(count),
            "notes": notes,
        })

    for status in ["Relevan", "Perlu Tinjau", "Di Luar Cakupan"]:
        add("relevance_distribution", "ALL", status, (df["relevance_level"] == status).sum(),
            "Jumlah artikel berdasarkan keputusan klasifikasi V4.")

    add("dataset_integrity", "ALL", "total_input", len(df), "Jumlah baris yang dibaca dari input.")
    add("dataset_integrity", "ALL", "unique_article_id", df["article_id"].nunique(), "Jumlah article_id unik.")
    add("dataset_integrity", "ALL", "duplicate_article_id_rows", df["filter_duplicate_article_id"].sum(), "Baris ID duplikat; tidak dihapus, diarahkan ke Review.")
    add("dataset_integrity", "ALL", "duplicate_url_rows", df["filter_duplicate_url"].sum(), "Baris URL duplikat; tidak dihapus, diarahkan ke Review.")
    add("source_quality", "ALL", "truncated_summary_rows", df["summary_truncated_indicator"].sum(), "Snippet yang secara eksplisit berakhir dengan ellipsis.")

    for topic in TOPIC_ORDER:
        add("primary_topic_distribution", topic, "Relevan", ((df["sector3_topic"] == topic) & (df["relevance_level"] == "Relevan")).sum(),
            "Artikel Relevan dengan topik utama tersebut.")
        add("primary_topic_distribution", topic, "Perlu Tinjau", ((df["sector3_topic"] == topic) & (df["relevance_level"] == "Perlu Tinjau")).sum(),
            "Artikel Review dengan topik utama sementara tersebut.")
        score_col = SCORE_COLUMNS[topic]
        add("topic_signal_distribution", topic, "score_nonzero", (df[score_col].astype(float) > 0).sum(),
            "Artikel dengan sinyal untuk topik; distribusi dapat tumpang tindih.")

    for priority in ["High", "Medium", "Low"]:
        add("review_priority_distribution", "ALL", priority,
            ((df["relevance_level"] == "Perlu Tinjau") & (df["review_priority"] == priority)).sum(),
            "Jumlah artikel Review menurut prioritas audit manual.")

    for rule_id, count in df["classification_rule_override"].replace("", pd.NA).value_counts().items():
        add("rule_usage", "ALL", str(rule_id), int(count), "Jumlah artikel yang diputuskan/diprioritaskan oleh rule ID tersebut.")

    return pd.DataFrame(rows)


def build_review_audit(review: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "article_id", "title", "summary", "url", "published_at", "search_query",
        "sector3_topic", "topic_candidates", "relevance_level", "classification_confidence",
        "review_priority", "classification_reason", "classification_evidence",
        "classification_rule_evidence", "matched_keywords", "topic_evidence_by_category", "classification_rule_override",
        "topic_score_cloud_enterprise", "topic_score_cyber_security",
        "topic_score_digital_transformation", "topic_score_enterprise_software",
    ]
    columns = [c for c in preferred if c in review.columns]
    audit = review[columns].copy()
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    audit["_priority_order"] = audit["review_priority"].map(priority_order).fillna(3)
    audit = audit.sort_values(["_priority_order", "sector3_topic", "article_id"]).drop(columns="_priority_order")
    audit["manual_relevance"] = ""
    audit["manual_topic"] = ""
    audit["audit_notes"] = ""
    return audit


def build_comparison(df: pd.DataFrame, v3_file: Path) -> pd.DataFrame | None:
    if not v3_file.exists():
        return None
    old = pd.read_csv(v3_file, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if "article_id" not in old.columns:
        return None
    keep = [c for c in ["article_id", "sector3_topic", "relevance_level", "classification_confidence"] if c in old.columns]
    old_small = old[keep].drop_duplicates("article_id").rename(columns={
        "sector3_topic": "sector3_topic_v3",
        "relevance_level": "relevance_level_v3",
        "classification_confidence": "confidence_v3",
    })
    new_small = df[["article_id", "sector3_topic", "relevance_level", "classification_confidence"]].copy().rename(columns={
        "sector3_topic": "sector3_topic_v4",
        "relevance_level": "relevance_level_v4",
        "classification_confidence": "confidence_v4",
    })
    comparison = old_small.merge(new_small, on="article_id", how="outer", indicator=True)
    comparison["status_changed"] = comparison["relevance_level_v3"].fillna("") != comparison["relevance_level_v4"].fillna("")
    comparison["topic_changed"] = comparison["sector3_topic_v3"].fillna("") != comparison["sector3_topic_v4"].fillna("")
    return comparison


def save_outputs(
    df: pd.DataFrame,
    output_dir: Path,
    v3_file: Path | None = None,
) -> dict[str, pd.DataFrame]:
    relevant = df[df["relevance_level"] == "Relevan"].copy()
    review = df[df["relevance_level"] == "Perlu Tinjau"].copy()
    out_scope = df[df["relevance_level"] == "Di Luar Cakupan"].copy()

    partition_total = len(relevant) + len(review) + len(out_scope)
    if partition_total != len(df):
        raise RuntimeError(f"Partisi tidak konsisten: input={len(df)}, partisi={partition_total}")
    if df["article_id"].astype(str).str.strip().eq("").any():
        raise RuntimeError("Ada article_id kosong setelah klasifikasi; periksa hasil Review.")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {key: output_dir / value for key, value in OUTPUT_NAMES.items()}
    for frame, key in [
        (df, "all"), (relevant, "relevant"), (review, "review"), (out_scope, "out_scope")
    ]:
        frame.to_csv(paths[key], index=False, encoding="utf-8-sig")

    report = build_report(df)
    report.to_csv(paths["report"], index=False, encoding="utf-8-sig")

    review_audit = build_review_audit(review)
    review_audit.to_csv(paths["review_audit"], index=False, encoding="utf-8-sig")

    comparison = build_comparison(df, v3_file) if v3_file else None
    if comparison is not None:
        comparison.to_csv(paths["comparison"], index=False, encoding="utf-8-sig")

    return {
        "all": df,
        "relevant": relevant,
        "review": review,
        "out_scope": out_scope,
        "report": report,
        "review_audit": review_audit,
        "comparison": comparison,
        "paths": paths,
    }


def print_report(result: dict[str, Any], input_file: Path) -> None:
    df = result["all"]
    relevant = result["relevant"]
    review = result["review"]
    out_scope = result["out_scope"]
    print("=" * 72)
    print("ANTARA SEARCH - FILTERING REPORT (V4 CANDIDATE)")
    print("=" * 72)
    print(f"Input dataset             : {input_file}")
    print(f"Total artikel input       : {len(df)}")
    print(f"Relevan                   : {len(relevant)}")
    print(f"Perlu Tinjau              : {len(review)}")
    print(f"Di Luar Cakupan           : {len(out_scope)}")
    print(f"Total partisi             : {len(relevant) + len(review) + len(out_scope)}")
    print(f"Snippet summary terpotong : {int(df['summary_truncated_indicator'].sum())}")
    print(f"Duplikat article_id       : {int(df['filter_duplicate_article_id'].sum())}")
    print(f"Duplikat URL              : {int(df['filter_duplicate_url'].sum())}")

    print("\nDISTRIBUSI STATUS")
    print(df["relevance_level"].value_counts(dropna=False).to_string())

    print("\nDISTRIBUSI TOPIK UTAMA - RELEVAN")
    print(relevant["sector3_topic"].value_counts(dropna=False).to_string() if not relevant.empty else "Tidak ada artikel Relevan.")

    print("\nDISTRIBUSI TOPIK UTAMA - REVIEW")
    print(review["sector3_topic"].value_counts(dropna=False).to_string() if not review.empty else "Tidak ada artikel Review.")

    print("\nPRIORITAS AUDIT REVIEW")
    print(review["review_priority"].value_counts(dropna=False).to_string() if not review.empty else "Tidak ada artikel Review.")

    print("\nCONFIDENCE - RELEVAN")
    print(relevant["classification_confidence"].value_counts(dropna=False).to_string() if not relevant.empty else "Tidak ada artikel Relevan.")

    print("\nPREVIEW HASIL")
    preview_cols = [
        "article_id", "sector3_topic", "relevance_level", "classification_confidence",
        "review_priority", "classification_rule_override", "title",
    ]
    print(df[preview_cols].head(15).to_string(index=False))

    if result["comparison"] is not None:
        comp = result["comparison"]
        print("\nPERUBAHAN STATUS V3 -> V4")
        print(pd.crosstab(comp["relevance_level_v3"], comp["relevance_level_v4"], dropna=False).to_string())

    print("\nOUTPUT FILES")
    for key, path in result["paths"].items():
        if key == "comparison" and result["comparison"] is None:
            continue
        print(f"{key:14}: {path}")

    print("\nCATATAN")
    print("V4 adalah kandidat rule-based berbasis title + summary; bukan ground truth.")
    print("Summary terpotong tetap membatasi confidence. Audit manual tetap diperlukan.")
    print("=" * 72)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ANTARA Search Sector 3 Filtering V4")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path CSV cleaned input.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA_DIR, help="Folder output V4.")
    parser.add_argument(
        "--v3-file", type=Path, default=None,
        help="Optional V3 all-classified CSV for a V3-to-V4 comparison report."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = args.input.resolve()
    output_dir = args.output_dir.resolve()
    v3_file = args.v3_file
    if v3_file is None:
        candidate = output_dir / "antara_search_all_classified_v3.csv"
        v3_file = candidate if candidate.exists() else None
    else:
        v3_file = v3_file.resolve()

    df = load_data(input_file)
    classified = classify_data(df)
    result = save_outputs(classified, output_dir, v3_file)
    print_report(result, input_file)


if __name__ == "__main__":
    main()
