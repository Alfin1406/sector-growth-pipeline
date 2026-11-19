from pathlib import Path
import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw"
REPORT_DIR = BASE_DIR / "reports"

QUARTERS = ["2026_TW1", "2026_TW2", "2026_TW3"]

BUSINESS_KEY = [
    "periode",
    "status_penanaman_modal",
    "regional",
    "negara",
    "sektor_utama",
    "nama_sektor",
    "deskripsi_kbli_2digit",
    "provinsi",
    "kabupaten_kota",
    "jawa_luar_jawa",
    "pulau",
]

METRIC_COLUMNS = [
    "investasi_rp_juta",
    "investasi_us_ribu",
    "tki",
]


def load_data(quarter):
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

    df.columns = df.columns.str.strip()

    return df


def parse_numeric(series):
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def audit_quarter(quarter):
    df = load_data(quarter)

    missing = [
        col for col in BUSINESS_KEY + METRIC_COLUMNS
        if col not in df.columns
    ]
    if missing:
        raise RuntimeError(f"{quarter}: Kolom hilang: {missing}")

    # Business-key duplicate check
    duplicate_mask = df.duplicated(
        subset=BUSINESS_KEY,
        keep=False
    )
    duplicate_rows = df[duplicate_mask].copy()

    duplicate_groups = (
        duplicate_rows.groupby(BUSINESS_KEY, dropna=False)
        .size()
        .reset_index(name="jumlah_baris")
    )

    # Cek apakah metrik berbeda dalam satu business key
    conflicting_groups = []

    for _, group in duplicate_rows.groupby(
        BUSINESS_KEY, dropna=False
    ):
        if any(
            group[col].nunique(dropna=False) > 1
            for col in METRIC_COLUMNS
        ):
            conflicting_groups.append(group)

    if conflicting_groups:
        conflicting_rows = pd.concat(
            conflicting_groups,
            ignore_index=True
        )
    else:
        conflicting_rows = pd.DataFrame(columns=df.columns)

    # Anomaly check
    negative_records = []

    for column in METRIC_COLUMNS:
        numeric = parse_numeric(df[column])
        mask = numeric < 0

        if mask.any():
            temp = df.loc[mask].copy()
            temp.insert(0, "quarter_audit", quarter)
            temp.insert(1, "anomaly_column", column)
            negative_records.append(temp)

    negative_df = (
        pd.concat(negative_records, ignore_index=True)
        if negative_records
        else pd.DataFrame()
    )

    report = {
        "quarter": quarter,
        "rows": int(len(df)),
        "duplicate_key_rows": int(duplicate_mask.sum()),
        "duplicate_key_groups": int(len(duplicate_groups)),
        "conflicting_metric_groups": int(len(conflicting_groups)),
        "negative_values": {
            col: int((parse_numeric(df[col]) < 0).sum())
            for col in METRIC_COLUMNS
        },
    }

    return report, duplicate_rows, conflicting_rows, negative_df


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    reports = []
    all_duplicates = []
    all_conflicts = []
    all_anomalies = []

    print("\n========== BKPM DUPLICATE & ANOMALY AUDIT ==========")

    for quarter in QUARTERS:
        report, duplicates, conflicts, anomalies = audit_quarter(quarter)
        reports.append(report)

        print(f"\n--- {quarter} ---")
        print(f"Rows                    : {report['rows']:,}")
        print(f"Duplicate-key rows      : {report['duplicate_key_rows']:,}")
        print(f"Duplicate-key groups    : {report['duplicate_key_groups']:,}")
        print(f"Conflicting metric groups: {report['conflicting_metric_groups']:,}")
        print(f"Negative values         : {report['negative_values']}")

        if not duplicates.empty:
            duplicates.insert(0, "quarter_audit", quarter)
            all_duplicates.append(duplicates)

        if not conflicts.empty:
            conflicts.insert(0, "quarter_audit", quarter)
            all_conflicts.append(conflicts)

        if not anomalies.empty:
            all_anomalies.append(anomalies)

    duplicate_output = (
        pd.concat(all_duplicates, ignore_index=True)
        if all_duplicates else pd.DataFrame()
    )
    conflict_output = (
        pd.concat(all_conflicts, ignore_index=True)
        if all_conflicts else pd.DataFrame()
    )
    anomaly_output = (
        pd.concat(all_anomalies, ignore_index=True)
        if all_anomalies else pd.DataFrame()
    )

    if not duplicate_output.empty:
        duplicate_output.to_csv(
            REPORT_DIR / "bkpm_2026_duplicate_key_rows.csv",
            index=False,
            encoding="utf-8-sig",
        )

    if not conflict_output.empty:
        conflict_output.to_csv(
            REPORT_DIR / "bkpm_2026_conflicting_metric_rows.csv",
            index=False,
            encoding="utf-8-sig",
        )

    if not anomaly_output.empty:
        anomaly_output.to_csv(
            REPORT_DIR / "bkpm_2026_negative_value_rows.csv",
            index=False,
            encoding="utf-8-sig",
        )

    output = {
        "dataset": "BKPM Realisasi Investasi 2026",
        "business_key": BUSINESS_KEY,
        "metric_columns": METRIC_COLUMNS,
        "quarters": reports,
        "total_duplicate_key_rows": sum(
            r["duplicate_key_rows"] for r in reports
        ),
        "total_duplicate_key_groups": sum(
            r["duplicate_key_groups"] for r in reports
        ),
        "total_conflicting_metric_groups": sum(
            r["conflicting_metric_groups"] for r in reports
        ),
    }

    report_path = REPORT_DIR / "bkpm_2026_duplicate_anomaly_audit.json"
    report_path.write_text(
        json.dumps(output, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== FINAL SUMMARY ==========")
    print(f"Duplicate-key rows       : {output['total_duplicate_key_rows']:,}")
    print(f"Duplicate-key groups     : {output['total_duplicate_key_groups']:,}")
    print(f"Conflicting metric groups: {output['total_conflicting_metric_groups']:,}")
    print(f"Report                   : {report_path}")
    print("Audit selesai.")


if __name__ == "__main__":
    main()
