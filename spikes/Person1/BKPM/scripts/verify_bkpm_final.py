from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "processed" / "bkpm_2026_combined.csv"

EXPECTED_ROWS = 98306
EXPECTED_DISTRIBUTION = {
    "2026_TW1": 34643,
    "2026_TW2": 33641,
    "2026_TW3": 30022,
}

print("\n========== FINAL DATASET VERIFICATION ==========")

df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

checks = {
    "row_count": len(df) == EXPECTED_ROWS,
    "column_count": len(df.columns) == 16,
    "source_quarter": df["source_quarter"].value_counts().to_dict()
        == EXPECTED_DISTRIBUTION,
    "numeric_dtypes": all(
        pd.api.types.is_numeric_dtype(df[col])
        for col in ["investasi_rp_juta", "investasi_us_ribu", "tki"]
    ),
    "anomaly_flag": int(df["tki_negative_flag"].sum()) == 1,
    "negative_tki": int((df["tki"] < 0).sum()) == 1,
}

for name, passed in checks.items():
    print(f"{name:20}: {'PASS' if passed else 'FAIL'}")

print("\nRows       :", f"{len(df):,}")
print("Columns    :", len(df.columns))
print("\nPeriod distribution:")
print(df["source_quarter"].value_counts().sort_index().to_string())

print("\nNegative TKI records:")
print(
    df.loc[df["tki"] < 0, [
        "periode", "status_penanaman_modal",
        "provinsi", "kabupaten_kota", "tki",
        "source_quarter", "tki_negative_flag"
    ]].to_string(index=False)
)

print("\nOverall result:", "PASS" if all(checks.values()) else "FAIL")

if not all(checks.values()):
    raise SystemExit("Final verification failed.")
