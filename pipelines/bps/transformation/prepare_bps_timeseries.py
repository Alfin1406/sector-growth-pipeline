#!/usr/bin/env python3
"""Prepare BPS ADHB observations and comparable sector time series.

Inputs are the decoded BPS CSVs produced by download_bps_batch.py and the
category crosswalk in reference/bps_sector_mapping.csv. No network or database
access is performed.

Outputs:
  processed/bps_adhb_observations_normalized.csv
      Original observations retained, with standardized period/category fields.
  processed/bps_adhb_sector_timeseries.csv
      Comparable series: published 4-group data for 2022-2025 and 3 mapped
      sector aggregates plus the published PDRB aggregate for 2026.
  processed/bps_adhb_2026_reconciliation.csv
      Checks the sum of the 17 detailed categories against published PDRB total
      for each region-quarter. Differences are reported, not silently adjusted.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

BPS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLES_DIR = REPO_ROOT / "data" / "bps" / "raw"
REFERENCE_FILE = BPS_DIR.parent / "reference" / "bps_sector_mapping.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "bps" / "processed"

HISTORICAL_PERIODS = (122, 123, 124, 125)
HISTORICAL_VARIABLE = 2533
CURRENT_VARIABLE = 2776
CURRENT_PERIOD = 126

REQUIRED_SOURCE_COLUMNS = {
    "source", "domain", "subject", "vervar_id", "vervar_label",
    "variable_id", "variable_label", "turvar_id", "turvar_label",
    "period_id", "period_label", "subperiod_id", "subperiod_label",
    "value", "unit", "last_update", "datacontent_key", "decode_status",
}

NORMALIZED_EXTRA_COLUMNS = [
    "year", "frequency", "quarter", "category_type", "sector_group",
    "is_aggregate", "aggregation_method",
]

TIMESERIES_COLUMNS = [
    "source", "source_variable_id", "source_variable_label", "domain",
    "subject", "year", "period_id", "frequency", "subperiod_id",
    "subperiod_label", "quarter", "vervar_id", "vervar_label",
    "series_name", "sector_group", "value", "unit", "is_aggregate",
    "aggregation_method", "source_record_count", "source_category_ids",
    "source_datacontent_keys", "last_update",
]

RECONCILIATION_COLUMNS = [
    "year", "period_id", "subperiod_id", "subperiod_label", "quarter",
    "vervar_id", "vervar_label", "unit", "published_pdrb_total",
    "sum_of_17_industries", "difference_total_minus_industries",
    "review_tolerance_miliar", "within_review_tolerance",
]

HISTORICAL_GROUPS = {
    "PDRB": ("Total PDRB", True),
    "Sektor Primer": ("Primer", False),
    "Sektor Sekunder": ("Sekunder", False),
    "Sektor Tersier": ("Tersier", False),
}

EXPECTED_GROUP_CATEGORY_COUNTS = {
    "Primer": 2,
    "Sekunder": 4,
    "Tersier": 11,
}


def parse_value(raw: str, *, context: str) -> Decimal:
    """Parse a numeric BPS value without silently guessing separators."""
    value = (raw or "").strip()
    if not value:
        raise ValueError(f"Nilai kosong pada {context}")
    if "," in value and "." in value:
        raise ValueError(
            f"Format angka ambigu pada {context}: {value!r}. "
            "Perlu aturan pemisah angka yang eksplisit."
        )
    if "," in value:
        value = value.replace(",", ".")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Nilai bukan angka pada {context}: {raw!r}") from exc
    if not number.is_finite():
        raise ValueError(f"Nilai tidak finite pada {context}: {raw!r}")
    return number


def format_decimal(value: Decimal) -> str:
    """Avoid scientific notation while retaining exact Decimal precision."""
    return format(value, "f")


def derive_frequency_and_quarter(label: str) -> tuple[str, str]:
    label = (label or "").strip()
    if label.lower() == "tahunan":
        return "annual", ""
    match = re.fullmatch(r"Triwulan\s+(I|II|III|IV)", label, flags=re.IGNORECASE)
    if match:
        roman = match.group(1).upper()
        return "quarterly", f"Q{ {'I': 1, 'II': 2, 'III': 3, 'IV': 4}[roman] }"
    return "unknown", ""


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        missing = sorted(REQUIRED_SOURCE_COLUMNS - set(columns))
        if missing:
            raise ValueError(f"Kolom wajib tidak ditemukan di {path.name}: {missing}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV kosong: {path}")
    return columns, rows


def load_mapping(path: Path, category_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"File referensi mapping tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        mapping_rows = list(csv.DictReader(handle))

    required = {"variable_id", "turvar_id", "turvar_label", "sector_group", "is_aggregate"}
    if not mapping_rows or not required.issubset(mapping_rows[0]):
        raise ValueError(f"Kolom mapping harus mencakup: {sorted(required)}")

    mapping: dict[str, dict[str, str]] = {}
    for row in mapping_rows:
        category_id = row["turvar_id"].strip()
        if row["variable_id"].strip() != str(CURRENT_VARIABLE):
            raise ValueError(
                f"Mapping {category_id} bukan untuk variable_id {CURRENT_VARIABLE}"
            )
        if category_id in mapping:
            raise ValueError(f"turvar_id duplikat dalam mapping: {category_id}")
        if row["is_aggregate"].strip().lower() not in {"true", "false"}:
            raise ValueError(f"is_aggregate tidak valid untuk kategori {category_id}")
        mapping[category_id] = {k: v.strip() for k, v in row.items()}

    source_categories: dict[str, str] = {}
    for row in category_rows:
        cid = row["turvar_id"].strip()
        label = row["turvar_label"].strip()
        if cid in source_categories and source_categories[cid] != label:
            raise ValueError(f"Label kategori berubah untuk turvar_id {cid}")
        source_categories[cid] = label

    if set(source_categories) != set(mapping):
        raise ValueError(
            "Kategori CSV variable 2776 tidak sama dengan mapping. "
            f"CSV saja={sorted(set(source_categories) - set(mapping))}; "
            f"Mapping saja={sorted(set(mapping) - set(source_categories))}"
        )

    for cid, label in source_categories.items():
        if mapping[cid]["turvar_label"] != label:
            raise ValueError(
                f"Label mapping tidak cocok untuk turvar_id {cid}: "
                f"mapping={mapping[cid]['turvar_label']!r}, CSV={label!r}"
            )

    if len(mapping) != 18:
        raise ValueError(f"Mapping harus memiliki 18 kategori, ditemukan {len(mapping)}")

    detailed_count = sum(
        row["is_aggregate"].lower() == "false" for row in mapping.values()
    )
    aggregate_count = sum(
        row["is_aggregate"].lower() == "true" for row in mapping.values()
    )
    if detailed_count != 17 or aggregate_count != 1:
        raise ValueError(
            f"Ekspektasi mapping 17 industri + 1 agregat; "
            f"ditemukan {detailed_count} + {aggregate_count}"
        )

    for group, expected in EXPECTED_GROUP_CATEGORY_COUNTS.items():
        actual = sum(
            row["sector_group"] == group and row["is_aggregate"].lower() == "false"
            for row in mapping.values()
        )
        if actual != expected:
            raise ValueError(
                f"Jumlah kategori kelompok {group} seharusnya {expected}, ditemukan {actual}"
            )

    return mapping


def validate_source_rows(
    rows: list[dict[str, str]],
    *,
    variable_id: int,
    period_id: int,
    expected_rows: int,
    source_name: str,
) -> None:
    if len(rows) != expected_rows:
        raise ValueError(
            f"{source_name}: jumlah baris {len(rows)}; ekspektasi {expected_rows}"
        )
    for row in rows:
        if row["variable_id"].strip() != str(variable_id):
            raise ValueError(f"{source_name}: variable_id tidak sesuai")
        if row["period_id"].strip() != str(period_id):
            raise ValueError(f"{source_name}: period_id tidak sesuai")
        if row["decode_status"].strip() != "decoded":
            raise ValueError(
                f"{source_name}: ditemukan decode_status {row['decode_status']!r}"
            )
        for column in (
            "vervar_id", "vervar_label", "turvar_id", "turvar_label",
            "subperiod_id", "subperiod_label", "value", "unit",
            "datacontent_key",
        ):
            if not row[column].strip():
                raise ValueError(f"{source_name}: nilai kosong pada kolom {column}")
        parse_value(row["value"], context=f"{source_name}/{row['datacontent_key']}")

    keys = [row["datacontent_key"] for row in rows]
    duplicates = len(keys) - len(set(keys))
    if duplicates:
        raise ValueError(f"{source_name}: ditemukan {duplicates} datacontent_key duplikat")


def normalized_row(
    row: dict[str, str],
    original_columns: list[str],
    *,
    category_type: str,
    sector_group: str,
    is_aggregate: bool,
    aggregation_method: str,
) -> dict[str, Any]:
    frequency, quarter = derive_frequency_and_quarter(row["subperiod_label"])
    output = {column: row.get(column, "") for column in original_columns}
    output.update({
        "year": row["period_label"].strip(),
        "frequency": frequency,
        "quarter": quarter,
        "category_type": category_type,
        "sector_group": sector_group,
        "is_aggregate": str(is_aggregate).lower(),
        "aggregation_method": aggregation_method,
    })
    return output


def timeseries_row(
    *,
    base: dict[str, str],
    series_name: str,
    sector_group: str,
    value: Decimal,
    is_aggregate: bool,
    aggregation_method: str,
    source_rows: list[dict[str, str]],
) -> dict[str, str]:
    frequency, quarter = derive_frequency_and_quarter(base["subperiod_label"])
    return {
        "source": base["source"],
        "source_variable_id": base["variable_id"],
        "source_variable_label": base["variable_label"],
        "domain": base["domain"],
        "subject": base["subject"],
        "year": base["period_label"],
        "period_id": base["period_id"],
        "frequency": frequency,
        "subperiod_id": base["subperiod_id"],
        "subperiod_label": base["subperiod_label"],
        "quarter": quarter,
        "vervar_id": base["vervar_id"],
        "vervar_label": base["vervar_label"],
        "series_name": series_name,
        "sector_group": sector_group,
        "value": format_decimal(value),
        "unit": base["unit"],
        "is_aggregate": str(is_aggregate).lower(),
        "aggregation_method": aggregation_method,
        "source_record_count": str(len(source_rows)),
        "source_category_ids": ";".join(sorted({r["turvar_id"] for r in source_rows})),
        "source_datacontent_keys": ";".join(r["datacontent_key"] for r in source_rows),
        "last_update": max((r["last_update"] for r in source_rows), default=""),
    }


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build(args: argparse.Namespace) -> int:
    print("=" * 72)
    print("BPS ADHB TIME-SERIES PREPARATION")
    print("=" * 72)
    print("Input samples :", SAMPLES_DIR)
    print("Mapping       :", REFERENCE_FILE)
    print("Output        :", args.output_dir)
    print("Dry run       :", args.dry_run)

    historical_files: list[tuple[int, Path, list[dict[str, str]], list[str]]] = []
    all_2026_rows: list[dict[str, str]] = []
    current_columns: list[str] | None = None
    canonical_columns: list[str] | None = None

    for period_id in HISTORICAL_PERIODS:
        path = SAMPLES_DIR / (
            f"batch_data_var_{HISTORICAL_VARIABLE}_period_{period_id}_decoded.csv"
        )
        columns, rows = read_csv(path)
        if canonical_columns is None:
            canonical_columns = columns
        elif columns != canonical_columns:
            raise ValueError(f"Skema kolom tidak konsisten pada {path.name}")
        validate_source_rows(
            rows,
            variable_id=HISTORICAL_VARIABLE,
            period_id=period_id,
            expected_rows=10_280,
            source_name=path.name,
        )
        categories = {row["turvar_label"].strip() for row in rows}
        if categories != set(HISTORICAL_GROUPS):
            raise ValueError(
                f"{path.name}: kategori historis tidak sesuai: {sorted(categories)}"
            )
        years = {row["period_label"].strip() for row in rows}
        if len(years) != 1:
            raise ValueError(f"{path.name}: period_label tidak konsisten: {years}")
        historical_files.append((period_id, path, rows, columns))
        print(f"[PASS] Variable {HISTORICAL_VARIABLE} / period {period_id}: {len(rows):,} rows")

    current_path = SAMPLES_DIR / (
        f"batch_data_var_{CURRENT_VARIABLE}_period_{CURRENT_PERIOD}_decoded.csv"
    )
    current_columns, all_2026_rows = read_csv(current_path)
    if canonical_columns is not None and current_columns != canonical_columns:
        raise ValueError(f"Skema kolom variable 2776 tidak konsisten dengan variable 2533: {current_path.name}")
    validate_source_rows(
        all_2026_rows,
        variable_id=CURRENT_VARIABLE,
        period_id=CURRENT_PERIOD,
        expected_rows=18_504,
        source_name=current_path.name,
    )
    mapping = load_mapping(REFERENCE_FILE, all_2026_rows)
    print(f"[PASS] Variable {CURRENT_VARIABLE} / period {CURRENT_PERIOD}: {len(all_2026_rows):,} rows")
    print(f"[PASS] Category crosswalk: {len(mapping)} categories (17 industries + 1 aggregate)")

    # Build normalized detail output: preserve all source rows without summing.
    normalized: list[dict[str, Any]] = []
    source_columns = current_columns or []
    for _, _, rows, columns in historical_files:
        for row in rows:
            label = row["turvar_label"].strip()
            group, aggregate = HISTORICAL_GROUPS[label]
            normalized.append(normalized_row(
                row, columns,
                category_type="aggregate" if aggregate else "published_sector_group",
                sector_group=group,
                is_aggregate=aggregate,
                aggregation_method="published_by_bps",
            ))

    for row in all_2026_rows:
        crosswalk = mapping[row["turvar_id"].strip()]
        aggregate = crosswalk["is_aggregate"].lower() == "true"
        normalized.append(normalized_row(
            row, source_columns,
            category_type="aggregate" if aggregate else "industry",
            sector_group=crosswalk["sector_group"],
            is_aggregate=aggregate,
            aggregation_method="published_by_bps" if aggregate else "not_aggregated",
        ))

    # Comparable time series: historical 4 published series, 2026 3 derived
    # sector groups plus the original published PDRB aggregate.
    timeseries: list[dict[str, str]] = []
    for _, _, rows, _ in historical_files:
        for row in rows:
            label = row["turvar_label"].strip()
            sector_group, aggregate = HISTORICAL_GROUPS[label]
            timeseries.append(timeseries_row(
                base=row,
                series_name="PDRB" if aggregate else label,
                sector_group=sector_group,
                value=parse_value(row["value"], context=row["datacontent_key"]),
                is_aggregate=aggregate,
                aggregation_method="published_by_bps",
                source_rows=[row],
            ))

    # Index 2026 observations by region-quarter and category.
    records_by_key: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)

    for row in all_2026_rows:
        key = (
            row["vervar_id"], row["period_id"], row["subperiod_id"], row["unit"]
        )
        crosswalk = mapping[row["turvar_id"].strip()]
        records_by_key[key].append(row)

    # Validate every region-quarter has exactly one row for each 17 detailed categories
    # and exactly one published PDRB aggregate row.
    expected_ids_by_group: dict[str, set[str]] = defaultdict(set)
    expected_all_detail_ids: set[str] = set()
    for cid, entry in mapping.items():
        if entry["is_aggregate"].lower() == "false":
            expected_ids_by_group[entry["sector_group"]].add(cid)
            expected_all_detail_ids.add(cid)

    base_keys = {(r["vervar_id"], r["period_id"], r["subperiod_id"], r["unit"]) for r in all_2026_rows}
    if len(base_keys) != 514 * 2:
        raise ValueError(f"Ekspektasi 1.028 kombinasi wilayah-triwulan; ditemukan {len(base_keys)}")

    reconciliation: list[dict[str, str]] = []
    for key in sorted(base_keys):
        region_id, period_id, subperiod_id, unit = key
        records = records_by_key[key]
        detail_ids = [r["turvar_id"].strip() for r in records if mapping[r["turvar_id"].strip()]["is_aggregate"].lower() == "false"]
        if len(detail_ids) != 17 or set(detail_ids) != expected_all_detail_ids or len(set(detail_ids)) != 17:
            raise ValueError(
                f"Kategori 2026 tidak lengkap/duplikat untuk wilayah {region_id}, "
                f"periode {period_id}, subperiode {subperiod_id}"
            )
        total_records = [r for r in records if mapping[r["turvar_id"].strip()]["is_aggregate"].lower() == "true"]
        if len(total_records) != 1:
            raise ValueError(
                f"Harus ada satu agregat PDRB untuk wilayah {region_id}, "
                f"subperiode {subperiod_id}; ditemukan {len(total_records)}"
            )

        # Locate a source row for consistent labels and metadata.
        base = records[0]
        total = parse_value(total_records[0]["value"], context=total_records[0]["datacontent_key"])
        sector_sums: dict[str, Decimal] = {}
        sector_sources: dict[str, list[dict[str, str]]] = {}
        for group_name, expected_ids in expected_ids_by_group.items():
            group_rows = [
                r for r in records
                if mapping[r["turvar_id"].strip()]["sector_group"] == group_name
                and mapping[r["turvar_id"].strip()]["is_aggregate"].lower() == "false"
            ]
            actual_ids = {r["turvar_id"].strip() for r in group_rows}
            if len(group_rows) != len(expected_ids) or actual_ids != expected_ids:
                raise ValueError(
                    f"Kategori kelompok {group_name} tidak lengkap untuk wilayah {region_id}, "
                    f"subperiode {subperiod_id}"
                )
            sector_sources[group_name] = group_rows
            sector_sums[group_name] = sum(
                (parse_value(r["value"], context=r["datacontent_key"]) for r in group_rows),
                Decimal("0"),
            )

            timeseries.append(timeseries_row(
                base=base,
                series_name=f"Sektor {group_name}",
                sector_group=group_name,
                value=sector_sums[group_name],
                is_aggregate=False,
                aggregation_method="sum_of_mapped_17_industry_categories",
                source_rows=group_rows,
            ))

        # Include the published PDRB total as a separate, non-additive aggregate.
        timeseries.append(timeseries_row(
            base=total_records[0],
            series_name="PDRB",
            sector_group="Total PDRB",
            value=total,
            is_aggregate=True,
            aggregation_method="published_by_bps",
            source_rows=total_records,
        ))

        industry_sum = sum(sector_sums.values(), Decimal("0"))
        difference = total - industry_sum
        frequency, quarter = derive_frequency_and_quarter(base["subperiod_label"])
        reconciliation.append({
            "year": base["period_label"],
            "period_id": period_id,
            "subperiod_id": subperiod_id,
            "subperiod_label": base["subperiod_label"],
            "quarter": quarter,
            "vervar_id": region_id,
            "vervar_label": base["vervar_label"],
            "unit": unit,
            "published_pdrb_total": format_decimal(total),
            "sum_of_17_industries": format_decimal(industry_sum),
            "difference_total_minus_industries": format_decimal(difference),
            "review_tolerance_miliar": format_decimal(args.tolerance),
            "within_review_tolerance": str(abs(difference) <= args.tolerance).lower(),
        })

    # Detect unexpected overlap or missing time-series row counts.
    historical_ts_count = sum(len(rows) for _, _, rows, _ in historical_files)
    expected_current_ts_count = 514 * 2 * 4  # 3 groups + 1 published total
    expected_ts_count = historical_ts_count + expected_current_ts_count
    if len(timeseries) != expected_ts_count:
        raise ValueError(
            f"Jumlah time-series tidak sesuai: {len(timeseries)}; "
            f"ekspektasi {expected_ts_count}"
        )
    if len(normalized) != 59_624:
        raise ValueError(
            f"Jumlah normalized observations tidak sesuai: {len(normalized)}; "
            "ekspektasi 59.624"
        )

    differences = [
        abs(Decimal(row["difference_total_minus_industries"]))
        for row in reconciliation
    ]
    outside_tolerance = sum(
        row["within_review_tolerance"] == "false" for row in reconciliation
    )
    max_difference = max(differences, default=Decimal("0"))

    print("\n=== TRANSFORMATION SUMMARY ===")
    print(f"Normalized observations : {len(normalized):,}")
    print(f"Comparable time-series  : {len(timeseries):,}")
    print(f"2026 reconciliation rows: {len(reconciliation):,}")
    print(f"PDRB total vs 17 sectors di luar toleransi Rp{args.tolerance} miliar: {outside_tolerance}")
    print(f"Maximum absolute difference: {format_decimal(max_difference)} miliar rupiah")

    if args.dry_run:
        print("\n[DRY RUN] Tidak ada file output yang ditulis.")
        return 0

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Source schema is consistent across the current CSV set; use the first
    # historical schema and append normalized fields.
    normalized_columns = list(historical_files[0][3]) + NORMALIZED_EXTRA_COLUMNS
    observations_path = output_dir / "bps_adhb_observations_normalized.csv"
    timeseries_path = output_dir / "bps_adhb_sector_timeseries.csv"
    reconciliation_path = output_dir / "bps_adhb_2026_reconciliation.csv"

    write_csv(observations_path, normalized_columns, normalized)
    write_csv(timeseries_path, TIMESERIES_COLUMNS, timeseries)
    write_csv(reconciliation_path, RECONCILIATION_COLUMNS, reconciliation)

    print("\n=== OUTPUT FILES ===")
    print("Normalized observations:", observations_path)
    print("Comparable time-series :", timeseries_path)
    print("2026 reconciliation    :", reconciliation_path)
    print("\n[SUCCESS] BPS ADHB time-series preparation selesai.")
    if outside_tolerance:
        print(
            "[WARNING] Ada selisih total PDRB terhadap penjumlahan 17 kategori "
            "di luar toleransi review yang dipilih. Periksa file reconciliation."
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare normalized BPS ADHB observations and sector time-series."
    )
    parser.add_argument(
        "--input-dir", type=Path, default=SAMPLES_DIR,
        help="Folder raw JSON/CSV hasil ingestion BPS."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validasi dan hitung transformasi tanpa menulis output."
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Folder output (default: data/bps/processed)."
    )
    parser.add_argument(
        "--tolerance", type=Decimal, default=Decimal("0.20"),
        help=(
            "Toleransi diagnostik selisih PDRB vs jumlah 17 kategori, "
            "dalam miliar rupiah (default 0.20; bukan ambang resmi BPS)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    global SAMPLES_DIR
    args = parse_args()
    SAMPLES_DIR = args.input_dir.expanduser().resolve()
    if not SAMPLES_DIR.is_dir():
        print(f"[ERROR] Input directory tidak ditemukan: {SAMPLES_DIR}", file=sys.stderr)
        return 1
    if args.tolerance < 0:
        print("[ERROR] --tolerance tidak boleh negatif.", file=sys.stderr)
        return 2
    try:
        return build(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
