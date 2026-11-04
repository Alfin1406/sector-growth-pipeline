import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = (
    "data/processed/"
    "bisnis_cyber_with_content.csv"
)

OUTPUT_FILE = (
    "data/processed/"
    "bisnis_cyber_clean.csv"
)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):
    """
    Membersihkan whitespace berlebih,
    newline, dan karakter kosong.
    """

    if pd.isna(value):
        return ""

    text = str(value)

    # Ganti newline/tab menjadi spasi
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Hapus spasi berlebih
    text = text.strip()

    return text


# ============================================================
# CLEAN URL
# ============================================================

def clean_url(value):
    """
    Membersihkan URL dari whitespace.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


# ============================================================
# NORMALIZE STATUS
# ============================================================

def normalize_status(value):
    """
    Memastikan content_status
    hanya mempunyai nilai yang konsisten.
    """

    if pd.isna(value):
        return "UNKNOWN"

    value = str(value).strip().upper()

    allowed_status = {
        "SUCCESS",
        "BLOCKED",
        "FAILED",
    }

    if value in allowed_status:
        return value

    return "UNKNOWN"


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("03 CLEANING - BISNIS.COM CYBER SECURITY")
    print("=" * 70)

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    print("\n[INFO] Membaca dataset...")

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"[INFO] Jumlah baris awal: "
        f"{len(df)}"
    )

    # --------------------------------------------------------
    # CLEAN COLUMN NAMES
    # --------------------------------------------------------

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    # --------------------------------------------------------
    # CLEAN TEXT COLUMNS
    # --------------------------------------------------------

    text_columns = [
        "title",
        "title_detail",
        "channel",
        "category",
        "source",
        "author",
        "content",
        "content_status",
    ]

    for column in text_columns:

        if column in df.columns:

            df[column] = df[column].apply(
                clean_text
            )

    # --------------------------------------------------------
    # CLEAN URL
    # --------------------------------------------------------

    if "url" in df.columns:

        df["url"] = df["url"].apply(
            clean_url
        )

    # --------------------------------------------------------
    # NORMALIZE CONTENT STATUS
    # --------------------------------------------------------

    if "content_status" in df.columns:

        df["content_status"] = (
            df["content_status"]
            .apply(normalize_status)
        )

    # --------------------------------------------------------
    # GUNAKAN TITLE RAW SEBAGAI TITLE UTAMA
    # --------------------------------------------------------

    if "title" in df.columns:

        df["title"] = (
            df["title"]
            .fillna("")
            .str.strip()
        )

    # --------------------------------------------------------
    # NORMALIZE PUBLISHED DATE
    # --------------------------------------------------------

    if "published_at" in df.columns:

        print(
            "\n[INFO] Normalisasi tanggal publikasi..."
        )

        # Contoh:
        # "29 Sep 2026 | 18:29 WIB"
        #
        # Kita ubah bagian "|"
        # menjadi spasi.

        df["published_at"] = (
            df["published_at"]
            .fillna("")
            .str.replace(
                "|",
                "",
                regex=False
            )
            .str.replace(
                "WIB",
                "",
                regex=False
            )
            .str.strip()
        )

        # Ubah ke datetime
        if "published_at" in df.columns:
            print("\n[INFO] Normalisasi tanggal publikasi...")

            import re

            month_map = {
                "Jan": "Jan", "Feb": "Feb", "Mar": "Mar",
                "Apr": "Apr", "Mei": "May", "Jun": "Jun",
                "Jul": "Jul", "Agt": "Aug", "Agu": "Aug",
                "Sep": "Sep", "Okt": "Oct", "Nov": "Nov",
                "Des": "Dec",
            }

            def parse_published_at(value):
                if pd.isna(value):
                    return pd.NaT

                value = str(value).strip()
                if not value:
                    return pd.NaT

                match = re.match(
                    r"^(\d{1,2})\s+([A-Za-z]{3})\s+"
                    r"(\d{4})(?:\s*\|\s*(\d{2}):(\d{2}))?",
                    value,
                )

                if not match:
                    return pd.NaT

                day, month, year, hour, minute = match.groups()
                month = month_map.get(month, month)

                date_text = f"{day} {month} {year}"
                if hour and minute:
                    date_text += f" {hour}:{minute}"
                    date_format = "%d %b %Y %H:%M"
                else:
                    date_format = "%d %b %Y"

                return pd.to_datetime(
                    date_text,
                    format=date_format,
                    errors="coerce",
                )

            df["published_at"] = df["published_at"].apply(
                parse_published_at
            )

            print(
                "[INFO] Tanggal publikasi valid:",
                int(df["published_at"].notna().sum()),
            )
            print(
                "[INFO] Tanggal publikasi kosong/tidak valid:",
                int(df["published_at"].isna().sum()),
            )  


    # --------------------------------------------------------
    # NORMALIZE SCRAPED_AT
    # --------------------------------------------------------

    if "scraped_at" in df.columns:

        df["scraped_at"] = pd.to_datetime(
            df["scraped_at"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # NORMALIZE SCRAPED_AT_CONTENT
    # --------------------------------------------------------

    if "scraped_at_content" in df.columns:

        df["scraped_at_content"] = pd.to_datetime(
            df["scraped_at_content"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # DROP ROW TANPA TITLE / URL
    # --------------------------------------------------------

    before_drop = len(df)

    df = df[
        (df["title"].str.len() > 0)
        &
        (df["url"].str.len() > 0)
    ].copy()

    removed_invalid = (
        before_drop - len(df)
    )

    print(
        f"\n[INFO] Baris tanpa title/url "
        f"dihapus: {removed_invalid}"
    )

    # --------------------------------------------------------
    # DROP DUPLICATE URL
    # --------------------------------------------------------

    before_duplicate = len(df)

    df = df.drop_duplicates(
        subset=["url"],
        keep="first"
    ).copy()

    duplicate_removed = (
        before_duplicate - len(df)
    )

    print(
        f"[INFO] Duplicate URL dihapus: "
        f"{duplicate_removed}"
    )

    # --------------------------------------------------------
    # BUAT CONTENT LENGTH
    # --------------------------------------------------------

    if "content" in df.columns:

        df["content_length"] = (
            df["content"]
            .fillna("")
            .str.len()
        )

    # --------------------------------------------------------
    # FLAG CONTENT
    # --------------------------------------------------------

    if "content_status" in df.columns:

        df["has_content"] = (
            df["content_status"]
            == "SUCCESS"
        )

    # --------------------------------------------------------
    # SORT BY PUBLISHED DATE
    # --------------------------------------------------------

    if "published_at" in df.columns:

        df = df.sort_values(
            by="published_at",
            ascending=False,
            na_position="last"
        ).reset_index(
            drop=True
        )

    # --------------------------------------------------------
    # SAVE CLEAN DATA
    # --------------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("CLEANING SELESAI")
    print("=" * 70)

    print(
        f"Jumlah baris akhir: "
        f"{len(df)}"
    )

    if "content_status" in df.columns:

        print("\nContent Status:")

        print(
            df["content_status"]
            .value_counts()
            .to_string()
        )

    if "has_content" in df.columns:

        print(
            f"\nContent tersedia: "
            f"{df['has_content'].sum()}"
        )

        print(
            f"Content tidak tersedia: "
            f"{(~df['has_content']).sum()}"
        )

    print(
        f"\nOutput: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()