import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = (
    "data/processed/"
    "bisnis_cyber_clean.csv"
)

OUTPUT_FILE = (
    "data/processed/"
    "bisnis_cyber_filtered.csv"
)


# ============================================================
# KEYWORDS
# ============================================================

CYBER_KEYWORDS = [
    "keamanan siber",
    "keamanan cyber",
    "cyber security",
    "cybersecurity",
    "serangan siber",
    "serangan cyber",
    "ransomware",
    "malware",
    "phishing",
    "data breach",
    "kebocoran data",
    "hacker",
    "peretas",
    "cyber attack",
    "serangan bot",
    "bot ai",
    "ddos",
    "zero trust",
    "siem",
    "edr",
    "xdr",
    "iam",
    "soc",
    "vulnerability",
    "exploit",
    "enkripsi",
    "encryption",
    "perlindungan data",
    "pelindungan data",
    "privasi data",
    "keamanan data",
    "penjahat siber",
    "kejahatan siber",
    "cybercrime",
    "disadap",
    "penyadapan",
    "spionase siber",
    "cyber espionage",
    "akun diretas",
    "diretas",
]


ENTERPRISE_KEYWORDS = [
    "perusahaan",
    "korporasi",
    "enterprise",
    "organisasi",
    "institusi",
    "bank",
    "perbankan",
    "finansial",
    "pemerintah",
    "kementerian",
    "bumn",
    "telekomunikasi",
    "operator",
    "e-commerce",
    "startup",
    "industri",
    "fbi",
    "lembaga",
    "infrastruktur",
    "sistem perusahaan",
]


CONSUMER_KEYWORDS = [
    "ponsel disadap",
    "hp disadap",
    "akun pribadi",
    "whatsapp pribadi",
    "instagram pribadi",
    "facebook pribadi",
    "cara cek hp",
]


IRRELEVANT_KEYWORDS = [
    "senjata di orbit",
    "senjata orbit",
    "timnas",
    "sepak bola",
    "mobil",
    "motor",
    "gadget",
    "smartphone",
]


# ============================================================
# HELPER
# ============================================================

def normalize_text(value):
    """
    Mengubah text menjadi lowercase
    dan merapikan whitespace.
    """

    if pd.isna(value):
        return ""

    text = str(value).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# CLASSIFY ARTICLE
# ============================================================

def classify_article(row):
    """
    Menentukan apakah artikel relevan
    dengan Cyber Security dalam konteks
    Digital Transformation & IT Enterprise.
    """

    title = normalize_text(
        row.get("title", "")
    )

    channel = normalize_text(
        row.get("channel", "")
    )

    content = normalize_text(
        row.get("content", "")
    )

    # Gabungkan informasi yang tersedia.
    text = " ".join(
        [
            title,
            channel,
            content,
        ]
    )

    # --------------------------------------------------------
    # 1. CEK CYBER SECURITY
    # --------------------------------------------------------

    cyber_matches = [
        keyword
        for keyword in CYBER_KEYWORDS
        if keyword in text
    ]

    has_cyber = len(
        cyber_matches
    ) > 0

    if not has_cyber:

        return {
            "is_relevant": False,
            "relevance_type": "Not Cyber Security",
            "matched_keywords": "",
            "filter_reason": (
                "Tidak ditemukan indikator "
                "cyber security."
            ),
        }

    # --------------------------------------------------------
    # 2. EXCLUDE IRRELEVANT TOPICS
    # --------------------------------------------------------

    irrelevant_matches = [
        keyword
        for keyword in IRRELEVANT_KEYWORDS
        if keyword in text
    ]

    if irrelevant_matches:

        return {
            "is_relevant": False,
            "relevance_type": "Irrelevant Topic",
            "matched_keywords": ", ".join(
                irrelevant_matches
            ),
            "filter_reason": (
                "Topik tidak relevan dengan "
                "Cyber Security Enterprise."
            ),
        }

    # --------------------------------------------------------
    # 3. EXCLUDE CONSUMER-ONLY ARTICLES
    # --------------------------------------------------------

    consumer_matches = [
        keyword
        for keyword in CONSUMER_KEYWORDS
        if keyword in text
    ]

    enterprise_matches = [
        keyword
        for keyword in ENTERPRISE_KEYWORDS
        if keyword in text
    ]

    # Jika consumer-only dan tidak ada
    # indikator enterprise
    if (
        consumer_matches
        and not enterprise_matches
    ):

        return {
            "is_relevant": False,
            "relevance_type": "Consumer Cyber Security",
            "matched_keywords": ", ".join(
                consumer_matches
            ),
            "filter_reason": (
                "Cyber security bersifat "
                "consumer/personal dan tidak "
                "menunjukkan konteks enterprise."
            ),
        }

    # --------------------------------------------------------
    # 4. RELEVANT
    # --------------------------------------------------------

    return {
        "is_relevant": True,
        "relevance_type": "Enterprise Cyber Security",
        "matched_keywords": ", ".join(
            sorted(
                set(
                    cyber_matches
                    + enterprise_matches
                )
            )
        ),
        "filter_reason": (
            "Artikel memiliki indikator "
            "Cyber Security dan konteks "
            "enterprise/organisasi."
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("04 FILTERING - CYBER SECURITY ENTERPRISE")
    print("=" * 70)

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    df = pd.read_csv(
        INPUT_FILE
    )

    
    print(
        f"\n[INFO] Data masuk: {len(df)} artikel"
    )

    # --------------------------------------------------------
    # FILTER TAHUN PUBLIKASI
    # --------------------------------------------------------

    if "published_at" not in df.columns:
        raise ValueError(
            "Kolom published_at tidak ditemukan."
        )

    df["published_at"] = pd.to_datetime(
        df["published_at"],
        errors="coerce"
    )

    total_awal = len(df)

    # Hanya artikel dengan tanggal valid pada tahun 2026.
    df = df[
        df["published_at"].notna()
        & (df["published_at"].dt.year == 2026)
    ].copy()

    print(
        f"[INFO] Artikel tanpa tanggal valid / di luar 2026: "
        f"{total_awal - len(df)}"
    )
    print(
        f"[INFO] Artikel tahun 2026 yang diproses: {len(df)}"
    )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------


    classification = df.apply(
        classify_article,
        axis=1
    )

    classification_df = pd.DataFrame(
        classification.tolist()
    )

    # Gabungkan dengan dataset
    df_result = pd.concat(
        [
            df.reset_index(drop=True),
            classification_df,
        ],
        axis=1
    )

    # --------------------------------------------------------
    # SIMPAN SEMUA HASIL KLASIFIKASI
    # --------------------------------------------------------

    df_result.to_csv(
        OUTPUT_FILE.replace(
            ".csv",
            "_all_classified.csv"
        ),
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # FILTER RELEVAN SAJA
    # --------------------------------------------------------

    df_filtered = df_result[
        df_result["is_relevant"] == True
    ].copy()

    df_filtered = df_filtered.reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # SAVE FILTERED DATA
    # --------------------------------------------------------

    df_filtered.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    relevant_count = len(
        df_filtered
    )

    irrelevant_count = (
        len(df_result)
        - relevant_count
    )

    print("\n" + "=" * 70)
    print("FILTERING SELESAI")
    print("=" * 70)

    print(
        f"Total awal       : {len(df_result)}"
    )

    print(
        f"Relevan          : {relevant_count}"
    )

    print(
        f"Tidak relevan    : {irrelevant_count}"
    )

    print(
        f"Output filtered  : {OUTPUT_FILE}"
    )

    # --------------------------------------------------------
    # DISTRIBUTION
    # --------------------------------------------------------

    print("\nDistribusi klasifikasi:")

    print(
        df_result[
            "relevance_type"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # PREVIEW
    # --------------------------------------------------------

    print("\nArtikel yang dipertahankan:")

    if not df_filtered.empty:

        print(
            df_filtered[
                [
                    "title",
                    "channel",
                    "relevance_type",
                    "matched_keywords",
                ]
            ].to_string(
                index=False
            )
        )

    else:

        print(
            "[WARNING] Tidak ada artikel yang "
            "lolos filtering."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()