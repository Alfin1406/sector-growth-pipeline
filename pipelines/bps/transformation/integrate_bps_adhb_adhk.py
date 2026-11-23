#!/usr/bin/env python3
"""Integrate prepared BPS ADHB and ADHK outputs into three combined CSVs.

Uses only Python standard library. Run from any working directory:
    python spikes/Person1/BPS/integrate_bps_adhb_adhk.py --dry-run
    python spikes/Person1/BPS/integrate_bps_adhb_adhk.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

BPS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "bps" / "processed"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "bps" / "processed"

# Expected row counts from the successfully audited ADHB and ADHK outputs.
DATASETS = {
    "normalized": {
        "adhb": "bps_adhb_observations_normalized.csv",
        "adhk": "bps_adhk_observations_normalized.csv",
        "output": "bps_adhb_adhk_observations_normalized.csv",
        "expected_each": 59_624,
        "key": ["price_basis", "variable_id", "period_id", "vervar_id", "turvar_id", "subperiod_id"],
        "required": ["variable_id", "period_id", "vervar_id", "turvar_id", "subperiod_id", "value"],
        "expected_variables": {"adhb": {"2533", "2776"}, "adhk": {"2534", "2775"}},
    },
    "timeseries": {
        "adhb": "bps_adhb_sector_timeseries.csv",
        "adhk": "bps_adhk_sector_timeseries.csv",
        "output": "bps_adhb_adhk_sector_timeseries.csv",
        "expected_each": 45_232,
        "key": ["price_basis", "source_variable_id", "period_id", "subperiod_id", "vervar_id", "series_name"],
        "required": ["source_variable_id", "period_id", "subperiod_id", "vervar_id", "series_name", "value"],
        "expected_variables": {"adhb": {"2533", "2776"}, "adhk": {"2534", "2775"}},
    },
    "reconciliation": {
        "adhb": "bps_adhb_2026_reconciliation.csv",
        "adhk": "bps_adhk_2026_reconciliation.csv",
        "output": "bps_adhb_adhk_2026_reconciliation.csv",
        "expected_each": 1_028,
        "key": ["price_basis", "period_id", "subperiod_id", "vervar_id"],
        "required": ["period_id", "subperiod_id", "vervar_id", "difference_total_minus_industries", "within_review_tolerance"],
        "expected_variables": None,
    },
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if not columns:
            raise ValueError(f"Header CSV tidak ditemukan: {path.name}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV kosong: {path.name}")
    return columns, rows


def count_duplicate_keys(rows: list[dict[str, Any]], key_columns: list[str]) -> int:
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    for row in rows:
        key = tuple(str(row[column]) for column in key_columns)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def validate_and_combine(
    name: str,
    config: dict[str, Any],
    input_dir: Path,
) -> tuple[list[str], list[dict[str, str]], dict[str, Any]]:
    basis_rows: dict[str, list[dict[str, str]]] = {}
    canonical_columns: list[str] | None = None
    report: dict[str, Any] = {}

    for basis, label in (("adhb", "ADHB"), ("adhk", "ADHK")):
        path = input_dir / config[basis]
        columns, rows = read_csv(path)

        missing = sorted(set(config["required"]) - set(columns))
        if missing:
            raise ValueError(f"{path.name}: kolom wajib tidak ada: {missing}")
        if "price_basis" in columns:
            raise ValueError(f"{path.name}: kolom price_basis sudah ada; hentikan agar tidak menggandakan label")
        if len(rows) != config["expected_each"]:
            raise ValueError(
                f"{path.name}: jumlah baris {len(rows):,}; ekspektasi {config['expected_each']:,}"
            )

        if canonical_columns is None:
            canonical_columns = columns
        elif columns != canonical_columns:
            only_first = sorted(set(canonical_columns) - set(columns))
            only_current = sorted(set(columns) - set(canonical_columns))
            raise ValueError(
                f"Skema {path.name} tidak identik. Hanya file pertama={only_first}; "
                f"hanya file ini={only_current}; urutan kolom juga harus sama."
            )

        if config["expected_variables"] is not None:
            variable_column = "variable_id" if name == "normalized" else "source_variable_id"
            actual_variables = {row[variable_column].strip() for row in rows}
            expected_variables = config["expected_variables"][basis]
            if actual_variables != expected_variables:
                raise ValueError(
                    f"{path.name}: {variable_column} {sorted(actual_variables)}; "
                    f"ekspektasi {sorted(expected_variables)}"
                )

        # Preserve all source values and append a clear price-basis discriminator.
        for row in rows:
            row["price_basis"] = label
        basis_rows[basis] = rows
        report[basis] = {"file": path.name, "rows": len(rows)}

    assert canonical_columns is not None
    output_columns = canonical_columns + ["price_basis"]
    combined = basis_rows["adhb"] + basis_rows["adhk"]

    missing_values = sum(
        not str(row.get(column, "")).strip()
        for row in combined
        for column in config["required"]
    )
    duplicate_keys = count_duplicate_keys(combined, config["key"])
    if missing_values:
        raise ValueError(f"{name}: ditemukan {missing_values:,} nilai kosong pada kolom wajib")
    if duplicate_keys:
        raise ValueError(f"{name}: ditemukan {duplicate_keys:,} duplicate key setelah penggabungan")

    if name == "reconciliation":
        invalid_flags = sum(
            row["within_review_tolerance"].strip().lower() != "true"
            for row in combined
        )
        if invalid_flags:
            raise ValueError(
                f"Rekonsiliasi gabungan memiliki {invalid_flags:,} baris di luar/bertanda tidak lolos toleransi"
            )
        report["reconciliation_flags_pass"] = len(combined)

    report.update({
        "combined_rows": len(combined),
        "columns": len(output_columns),
        "duplicate_keys": duplicate_keys,
        "missing_required_values": missing_values,
    })
    return output_columns, combined, report


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gabungkan output BPS ADHB dan ADHK dengan penanda price_basis."
    )
    parser.add_argument(
        "--input-dir", type=Path, default=DEFAULT_INPUT_DIR,
        help="Folder input ADHB/ADHK (default: folder processed BPS).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Folder output gabungan (default: folder processed BPS).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validasi semua file tanpa menulis output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 72)
    print("BPS ADHB + ADHK INTEGRATION")
    print("=" * 72)
    print("Input  :", args.input_dir)
    print("Output :", args.output_dir)
    print("Dry run:", args.dry_run)

    prepared: list[tuple[Path, list[str], list[dict[str, str]], dict[str, Any]]] = []
    for name, config in DATASETS.items():
        columns, rows, report = validate_and_combine(name, config, args.input_dir)
        output_path = args.output_dir / config["output"]
        prepared.append((output_path, columns, rows, report))
        print(f"\n[PASS] {name.upper()}")
        print(f"  ADHB rows            : {report['adhb']['rows']:,}")
        print(f"  ADHK rows            : {report['adhk']['rows']:,}")
        print(f"  Combined rows        : {report['combined_rows']:,}")
        print(f"  Output columns       : {report['columns']}")
        print(f"  Duplicate keys       : {report['duplicate_keys']}")
        print(f"  Missing required vals: {report['missing_required_values']}")
        if name == "reconciliation":
            print(f"  Reconciliation PASS  : {report['reconciliation_flags_pass']:,}")

    print("\n" + "=" * 72)
    print("INTEGRATION SUMMARY")
    print("=" * 72)
    for output_path, columns, rows, _ in prepared:
        print(f"{output_path.name}: {len(rows):,} rows x {len(columns)} columns")

    if args.dry_run:
        print("\n[DRY RUN] Validasi berhasil. Tidak ada file output yang ditulis.")
        return 0

    for output_path, columns, rows, _ in prepared:
        write_csv(output_path, columns, rows)
        print("[WRITTEN]", output_path)

    print("\n[SUCCESS] Integrasi ADHB dan ADHK selesai.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
