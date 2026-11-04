
import sys
from pathlib import Path

import pandas as pd
from classify_subtopic_all_sources import determine_subtopic


PIPELINE_DIR = Path(__file__).resolve().parent

SOURCE_FILES = {
    "antaranews": "data_center_antaranews_business_insight.csv",
    "katadata": "data_center_katadata_business_insight.csv",
    "kompas": "data_center_kompas_business_insight.csv",
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SOURCE_FILES:
        raise ValueError(
            "Pilih sumber: antaranews, katadata, atau kompas"
        )

    source = sys.argv[1]
    csv_file = PIPELINE_DIR / SOURCE_FILES[source]

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV tidak ditemukan: {csv_file}")

    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    df["subtopic"] = df.apply(determine_subtopic, axis=1)

    df.to_csv(csv_file, index=False, encoding="utf-8-sig")

    print(f"Sumber: {source}")
    print(f"Total artikel: {len(df)}")
    print("\nDistribusi subtopic:")
    print(df["subtopic"].value_counts(dropna=False).to_string())
    print("\nKlasifikasi selesai.")


if __name__ == "__main__":
    main()
