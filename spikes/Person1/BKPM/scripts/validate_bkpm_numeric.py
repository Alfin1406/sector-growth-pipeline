from pathlib import Path
import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw"
REPORT_DIR = BASE_DIR / "reports"

QUARTERS = ["2026_TW1", "2026_TW2", "2026_TW3"]
NUMERIC_COLUMNS = [
    "investasi_rp_juta",
    "investasi_us_ribu",
    "tki",
]


def parse_numeric(series):
    # Format sumber: titik ribuan dan koma desimal.
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def validate_quarter(quarter):
    folder = RAW_DIR / quarter / "extracted"
    files = list(folder.glob("*.csv"))

    if len(files) != 1:
        raise RuntimeError(
            f"{quarter}: Diharapkan 1 CSV, ditemukan {len(files)}"
        )

    df = pd.read_csv(
        files[0],
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )

    report = {
        "quarter": quarter,
        "rows": int(len(df)),
        "numeric_columns": {},
    }

    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            raise RuntimeError(f"Kolom tidak ditemukan: {column}")

        original = df[column].astype(str).str.strip()
        parsed = parse_numeric(original)

        invalid_mask = parsed.isna() & original.ne("")

        report["numeric_columns"][column] = {
            "invalid_values": int(invalid_mask.sum()),
            "empty_values": int(original.eq("").sum()),
            "negative_values": int((parsed < 0).sum()),
            "minimum": (
                float(parsed.min()) if parsed.notna().any() else None
            ),
            "maximum": (
                float(parsed.max()) if parsed.notna().any() else None
            ),
        }

    return report


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = []

    print("\n========== BKPM NUMERIC VALIDATION ==========")

    for quarter in QUARTERS:
        report = validate_quarter(quarter)
        reports.append(report)

        print(f"\n--- {quarter} ({report['rows']:,} rows) ---")

        for column, result in report["numeric_columns"].items():
            print(
                f"{column}: "
                f"invalid={result['invalid_values']}, "
                f"empty={result['empty_values']}, "
                f"negative={result['negative_values']}, "
                f"min={result['minimum']}, "
                f"max={result['maximum']}"
            )

    output = {
        "dataset": "BKPM Realisasi Investasi 2026",
        "quarters": reports,
    }

    output_path = REPORT_DIR / "bkpm_2026_numeric_validation.json"
    output_path.write_text(
        json.dumps(output, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== FINAL SUMMARY ==========")
    print(f"Report: {output_path}")
    print("Numeric validation selesai.")


if __name__ == "__main__":
    main()
