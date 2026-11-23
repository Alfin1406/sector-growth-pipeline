from pathlib import Path
import json
import importlib.util
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "bkpm" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "bkpm" / "processed"
REPORT_DIR = REPO_ROOT / "data" / "bkpm" / "reports"

QUARTERS = ["2026_TW1", "2026_TW2", "2026_TW3"]

EXPECTED_COLUMNS = [
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
    "investasi_rp_juta",
    "investasi_us_ribu",
    "tki",
]

NUMERIC_COLUMNS = [
    "investasi_rp_juta",
    "investasi_us_ribu",
    "tki",
]


def parse_numeric(series):
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def load_quarter(quarter):
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

    if df.columns.tolist() != EXPECTED_COLUMNS:
        raise RuntimeError(
            f"Schema mismatch pada {quarter}.\n"
            f"Kolom aktual: {df.columns.tolist()}"
        )

    # Konversi kolom numerik.
    for column in NUMERIC_COLUMNS:
        original = df[column].astype(str).str.strip()
        converted = parse_numeric(original)

        invalid = converted.isna() & original.ne("")

        if invalid.any():
            examples = original[invalid].head(5).tolist()
            raise RuntimeError(
                f"{quarter}: Gagal konversi {column}. "
                f"Contoh: {examples}"
            )

        if original.eq("").any():
            raise RuntimeError(
                f"{quarter}: Ada nilai kosong pada {column}"
            )

        df[column] = converted

    # Metadata asal dataset.
    df["source_quarter"] = quarter

    # Tandai anomali tanpa menghapus atau mengubah nilai aslinya.
    df["tki_negative_flag"] = df["tki"] < 0

    return df


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = []

    print("\n========== BKPM STANDARDIZATION ==========")

    for quarter in QUARTERS:
        df = load_quarter(quarter)
        datasets.append(df)

        print(
            f"{quarter}: {len(df):,} rows | "
            f"{len(df.columns)} columns | "
            f"Negative TKI: {int(df['tki_negative_flag'].sum())}"
        )

    combined = pd.concat(datasets, ignore_index=True)

    expected_total = sum(len(df) for df in datasets)

    if len(combined) != expected_total:
        raise RuntimeError("Jumlah baris setelah penggabungan tidak sesuai.")

    # Pastikan tidak ada nilai numerik yang gagal dikonversi.
    for column in NUMERIC_COLUMNS:
        if combined[column].isna().any():
            raise RuntimeError(
                f"Ditemukan NaN pada kolom numerik {column}"
            )

    csv_path = PROCESSED_DIR / "bkpm_2026_combined.csv"
    combined.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    parquet_path = PROCESSED_DIR / "bkpm_2026_combined.parquet"
    parquet_created = False

    if (
        importlib.util.find_spec("pyarrow")
        or importlib.util.find_spec("fastparquet")
    ):
        combined.to_parquet(parquet_path, index=False)
        parquet_created = True

    anomaly_rows = combined[combined["tki_negative_flag"]]

    report = {
        "dataset": "BKPM Realisasi Investasi 2026",
        "quarters": QUARTERS,
        "total_rows": int(len(combined)),
        "total_columns": int(len(combined.columns)),
        "columns": combined.columns.tolist(),
        "numeric_dtypes": {
            col: str(combined[col].dtype)
            for col in NUMERIC_COLUMNS
        },
        "source_quarter_distribution": {
            key: int(value)
            for key, value in
            combined["source_quarter"].value_counts().items()
        },
        "negative_tki_count": int(len(anomaly_rows)),
        "parquet_created": parquet_created,
        "outputs": {
            "csv": str(csv_path),
            "parquet": str(parquet_path) if parquet_created else None,
        },
    }

    report_path = REPORT_DIR / "bkpm_2026_standardization_report.json"
    report_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    if not anomaly_rows.empty:
        anomaly_path = REPORT_DIR / "bkpm_2026_flagged_anomalies.csv"
        anomaly_rows.to_csv(
            anomaly_path,
            index=False,
            encoding="utf-8-sig",
        )
        print(f"Flagged anomalies: {anomaly_path}")

    print("\n========== FINAL SUMMARY ==========")
    print(f"Total rows      : {len(combined):,}")
    print(f"Total columns   : {len(combined.columns)}")
    print(f"Numeric dtypes  : {report['numeric_dtypes']}")
    print(f"Negative TKI    : {len(anomaly_rows)}")
    print(f"CSV             : {csv_path}")
    print(f"Parquet created : {parquet_created}")
    print(f"Report          : {report_path}")
    print("\nSTANDARDIZATION COMPLETED")


if __name__ == "__main__":
    main()
