
from pathlib import Path
import html
import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

INPUT_FILE = (
    PROJECT_ROOT / "data" / "raw" / "antara_search_raw.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "antara_search_content_prepared.csv"
)

REQUIRED_COLUMNS = [
    "article_id",
    "title",
    "url",
    "published_at",
    "summary",
    "content",
    "content_status",
    "search_query",
]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """Membersihkan teks tanpa mengubah substansi."""
    if pd.isna(value):
        return ""

    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def combine_text(title, summary):
    """Menggabungkan judul dan ringkasan untuk analisis."""
    parts = [part for part in [title, summary] if part]

    return ". ".join(parts)


# ============================================================
# MAIN PROCESS
# ============================================================

def main():

    print("=" * 65)
    print("ANTARA SEARCH - CONTENT PREPARATION")
    print("=" * 65)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"File input tidak ditemukan: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"Input: {INPUT_FILE}")
    print(f"Jumlah artikel: {len(df)}")

    # Validasi struktur kolom
    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {missing_columns}"
        )

    # Salin data agar tidak memodifikasi sumber asli
    df = df.copy()

    # Bersihkan judul dan ringkasan
    df["title_clean"] = df["title"].apply(clean_text)
    df["summary_clean"] = df["summary"].apply(clean_text)

    # Siapkan teks untuk proses filtering dan insight
    df["prepared_text"] = df.apply(
        lambda row: combine_text(
            row["title_clean"],
            row["summary_clean"]
        ),
        axis=1
    )

    
    # Validasi tanggal ISO 8601
    # Mempertahankan timezone asli dari sumber (+07:00).
    published_at_values = (
        df["published_at"]
        .astype("string")
        .str.strip()
    )

    published_at_values = published_at_values.mask(
        published_at_values.eq(""),
        pd.NA
    )

    parsed_dates = pd.to_datetime(
    published_at_values,
    errors="coerce",
    utc=True
    )

    # Validasi URL ANTARA
    valid_url = (
        df["url"]
        .fillna("")
        .str.startswith(
            "https://www.antaranews.com/berita/"
        )
    )

    # Status persiapan konten
    valid_title = df["title_clean"].ne("")
    valid_summary = df["summary_clean"].ne("")
    valid_date = parsed_dates.notna()

    ready = (
        valid_title
        & valid_summary
        & valid_url
        & valid_date
    )

    df["content_preparation_status"] = (
        "review_required"
    )

    df.loc[
        ready,
        "content_preparation_status"
    ] = "ready"

    # Content tetap kosong jika sumber hanya menyediakan summary.
    # Tidak mengubah summary_only menjadi full_content.
    df["content"] = df["content"].fillna("")

    # Simpan output
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # REPORT
    # ========================================================

    print("\n" + "=" * 65)
    print("CONTENT PREPARATION REPORT")
    print("=" * 65)

    print(f"Total input                 : {len(df)}")
    print(f"Artikel siap                : {ready.sum()}")
    print(f"Perlu ditinjau              : {(~ready).sum()}")

    print("\nVALIDASI DATA")
    print(f"Judul kosong                : {(~valid_title).sum()}")
    print(f"Ringkasan kosong            : {(~valid_summary).sum()}")
    print(f"URL tidak valid             : {(~valid_url).sum()}")
    print(f"Tanggal tidak terbaca       : {(~valid_date).sum()}")

    print("\nKETERSEDIAAN KONTEN")
    print(
        "Content kosong             : "
        f"{df['content'].str.strip().eq('').sum()}"
    )
    print(
        "Summary kosong             : "
        f"{df['summary_clean'].eq('').sum()}"
    )

    print("\nSTATUS PERSIAPAN")
    print(
        df["content_preparation_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nDISTRIBUSI ASAL PENCARIAN")
    print(
        df["search_query"]
        .value_counts(dropna=False)
        .head(10)
        .to_string()
    )

    multi_query = (
        df["search_query"]
        .fillna("")
        .str.contains(";", regex=False)
    )

    print(
        "\nArtikel dengan beberapa asal pencarian: "
        f"{multi_query.sum()}"
    )

    print("\nPREVIEW PREPARED TEXT")

    for _, row in df.head(5).iterrows():
        print(f"\nJudul   : {row['title_clean']}")
        print(
            "Prepared: "
            f"{row['prepared_text'][:250]}"
        )

    print("\n" + "=" * 65)
    print(f"OUTPUT: {OUTPUT_FILE}")
    print("CONTENT PREPARATION SELESAI")
    print("=" * 65)


if __name__ == "__main__":
    main()
 