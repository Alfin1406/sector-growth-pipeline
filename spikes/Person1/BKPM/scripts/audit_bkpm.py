from pathlib import Path
import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw"
REPORT_DIR = BASE_DIR / "reports"

QUARTERS = ["2026_TW1", "2026_TW2", "2026_TW3"]

def audit_quarter(quarter):
    folder = RAW_DIR / quarter / "extracted"
    csv_files = list(folder.glob("*.csv"))

    if len(csv_files) != 1:
        raise RuntimeError(
            f"{quarter}: Diharapkan 1 CSV, ditemukan {len(csv_files)}"
        )

    csv_path = csv_files[0]

    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )

    # Rapikan whitespace pada nama kolom, tanpa mengubah file sumber.
    df.columns = df.columns.str.strip()

    report = {
        "quarter": quarter,
        "filename": csv_path.name,
        "rows": int(len(df)),
        "columns_count": int(len(df.columns)),
        "columns": df.columns.tolist(),
        "empty_cells": int(
            df.apply(lambda col: col.str.strip().eq("")).sum().sum()
        ),
        "duplicate_identical_rows": int(df.duplicated().sum()),
        "file_size_bytes": csv_path.stat().st_size,
    }

    return report


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    reports = []

    print("\n========== BKPM DATA AUDIT ==========")

    for quarter in QUARTERS:
        report = audit_quarter(quarter)
        reports.append(report)

        print(f"\n--- {quarter} ---")
        print(f"File       : {report['filename']}")
        print(f"Rows       : {report['rows']:,}")
        print(f"Columns    : {report['columns_count']}")
        print(f"Empty      : {report['empty_cells']:,}")
        print(f"Duplicates : {report['duplicate_identical_rows']:,}")
        print("Column names:")

        for index, column in enumerate(report["columns"], start=1):
            print(f"  {index:02d}. {column}")

    reference_columns = reports[0]["columns"]

    print("\n========== SCHEMA COMPARISON ==========")

    for report in reports:
        same_schema = report["columns"] == reference_columns
        print(
            f"{report['quarter']}: "
            f"{'MATCH' if same_schema else 'MISMATCH'}"
        )

    total_rows = sum(report["rows"] for report in reports)

    output = {
        "dataset": "BKPM Realisasi Investasi 2026",
        "total_rows": total_rows,
        "quarters": reports,
        "schema_consistent": all(
            report["columns"] == reference_columns
            for report in reports
        ),
    }

    report_path = REPORT_DIR / "bkpm_2026_audit.json"

    report_path.write_text(
        json.dumps(output, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n========== FINAL SUMMARY ==========")
    print(f"Total rows : {total_rows:,}")
    print(f"Schema     : {'CONSISTENT' if output['schema_consistent'] else 'INCONSISTENT'}")
    print(f"Report     : {report_path}")

    if not output["schema_consistent"]:
        raise SystemExit("Audit gagal: skema antarperiode berbeda.")


if __name__ == "__main__":
    main()
