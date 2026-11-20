from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Project paths and source configuration
# ---------------------------------------------------------------------------
BPS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLES_DIR = REPO_ROOT / "data" / "bps" / "raw"
REFERENCE_FILE = BPS_DIR.parent / "reference" / "bps_adhk_sector_mapping.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "bps" / "processed"

HISTORICAL_PERIODS = (122, 123, 124, 125)
HISTORICAL_VARIABLE = 2534  # ADHK 2010=100: published broad sector groups
CURRENT_VARIABLE = 2775    # ADHK 2010=100: 17 industries + published PDRB
CURRENT_PERIOD = 126       # 2026
EXPECTED_REGIONS = 514
EXPECTED_HISTORICAL_ROWS_PER_PERIOD = 10_280
EXPECTED_CURRENT_ROWS = 18_504
REVIEW_TOLERANCE_DEFAULT = Decimal("0.20")

HISTORICAL_EXPECTED_GROUP_COUNTS = {
    "Primer": 1,
    "Sekunder": 1,
    "Tersier": 1,
}
CURRENT_EXPECTED_GROUP_COUNTS = {
    "Primer": 2,
    "Sekunder": 4,
    "Tersier": 11,
}

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


# ---------------------------------------------------------------------------
# Parsing and CSV helpers (kept consistent with the ADHB preparation script)
# ---------------------------------------------------------------------------
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
        quarter_number = {"I": 1, "II": 2, "III": 3, "IV": 4}[roman]
        return "quarterly", f"Q{quarter_number}"
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


def locate_source_file(variable_id: int, period_id: int) -> Path:
    """Find canonical batch file or timestamped decoded export for a source pair."""
    canonical = SAMPLES_DIR / (
        f"batch_data_var_{variable_id}_period_{period_id}_decoded.csv"
    )
    if canonical.exists():
        return canonical

    pattern = f"*data_var_{variable_id}_period_{period_id}_decoded.csv"
    candidates = list(SAMPLES_DIR.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"Tidak ditemukan file untuk variable {variable_id}, period {period_id} "
            f"di {SAMPLES_DIR}. Pola yang dicari: {pattern}"
        )

    # Multiple exports can exist after repeated downloads. Use the most recently
    # modified export and print the choice so it is visible in the run report.
    candidates.sort(key=lambda item: (item.stat().st_mtime_ns, item.name))
    selected = candidates[-1]
    if len(candidates) > 1:
        print(
            f"[INFO] Ada {len(candidates)} file untuk variable {variable_id}/period "
            f"{period_id}; menggunakan file terbaru: {selected.name}"
        )
    return selected


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
            f"{source_name}: jumlah baris {len(rows):,}; ekspektasi {expected_rows:,}"
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
        raise ValueError(
            f"{source_name}: ditemukan {duplicates} datacontent_key duplikat"
        )


def load_mapping(
    path: Path,
    historical_rows: list[dict[str, str]],
    current_rows: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    """Load and validate the combined 2534 + 2775 ADHK category crosswalk."""
    if not path.exists():
        raise FileNotFoundError(f"File referensi mapping tidak ditemukan: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        mapping_rows = list(csv.DictReader(handle))

    required = {
        "variable_id", "turvar_id", "turvar_label", "sector_group", "is_aggregate"
    }
    if not mapping_rows or not required.issubset(mapping_rows[0]):
        raise ValueError(f"Kolom mapping harus mencakup: {sorted(required)}")

    mapping: dict[tuple[str, str], dict[str, str]] = {}
    for raw in mapping_rows:
        row = {key: (value or "").strip() for key, value in raw.items()}
        variable_id = row["variable_id"]
        category_id = row["turvar_id"]
        key = (variable_id, category_id)

        if variable_id not in {str(HISTORICAL_VARIABLE), str(CURRENT_VARIABLE)}:
            raise ValueError(f"Mapping memuat variable_id yang tidak diharapkan: {variable_id}")
        if not category_id:
            raise ValueError("Mapping memiliki turvar_id kosong")
        if key in mapping:
            raise ValueError(f"Mapping duplikat untuk variable_id/turvar_id: {key}")
        if row["is_aggregate"].lower() not in {"true", "false"}:
            raise ValueError(f"is_aggregate tidak valid untuk kategori {key}")
        if row["sector_group"] not in {"Primer", "Sekunder", "Tersier", "PDRB"}:
            raise ValueError(f"sector_group tidak valid untuk kategori {key}: {row['sector_group']!r}")
        mapping[key] = row

    def validate_source_categories(
        rows: list[dict[str, str]], variable_id: int, expected_count: int
    ) -> None:
        source_categories: dict[str, str] = {}
        for row in rows:
            category_id = row["turvar_id"].strip()
            label = row["turvar_label"].strip()
            if category_id in source_categories and source_categories[category_id] != label:
                raise ValueError(f"Label kategori berubah untuk variable {variable_id}, turvar_id {category_id}")
            source_categories[category_id] = label

        mapped_categories = {
            category_id: entry
            for (mapped_variable, category_id), entry in mapping.items()
            if mapped_variable == str(variable_id)
        }
        if set(source_categories) != set(mapped_categories):
            raise ValueError(
                f"Kategori CSV variable {variable_id} tidak sama dengan mapping. "
                f"CSV saja={sorted(set(source_categories) - set(mapped_categories))}; "
                f"Mapping saja={sorted(set(mapped_categories) - set(source_categories))}"
            )
        if len(mapped_categories) != expected_count:
            raise ValueError(
                f"Mapping variable {variable_id} harus memiliki {expected_count} kategori; "
                f"ditemukan {len(mapped_categories)}"
            )
        for category_id, label in source_categories.items():
            if mapped_categories[category_id]["turvar_label"] != label:
                raise ValueError(
                    f"Label mapping tidak cocok untuk variable {variable_id}, "
                    f"turvar_id {category_id}: mapping={mapped_categories[category_id]['turvar_label']!r}, "
                    f"CSV={label!r}"
                )

    validate_source_categories(historical_rows, HISTORICAL_VARIABLE, 4)
    validate_source_categories(current_rows, CURRENT_VARIABLE, 18)

    historical_mapping = {
        category_id: entry
        for (variable_id, category_id), entry in mapping.items()
        if variable_id == str(HISTORICAL_VARIABLE)
    }
    historical_group_counts = {
        group: sum(
            entry["sector_group"] == group and entry["is_aggregate"].lower() == "false"
            for entry in historical_mapping.values()
        )
        for group in HISTORICAL_EXPECTED_GROUP_COUNTS
    }
    historical_aggregates = sum(
        entry["is_aggregate"].lower() == "true" for entry in historical_mapping.values()
    )
    if historical_group_counts != HISTORICAL_EXPECTED_GROUP_COUNTS or historical_aggregates != 1:
        raise ValueError(
            "Mapping historis 2534 harus berisi satu kategori untuk tiap kelompok "
            f"Primer/Sekunder/Tersier dan satu agregat PDRB. Ditemukan: "
            f"{historical_group_counts}, agregat={historical_aggregates}"
        )
    if any(
        entry["is_aggregate"].lower() == "true" and entry["sector_group"] != "PDRB"
        for entry in historical_mapping.values()
    ):
        raise ValueError("Kategori agregat historis harus memiliki sector_group='PDRB'")

    current_mapping = {
        category_id: entry
        for (variable_id, category_id), entry in mapping.items()
        if variable_id == str(CURRENT_VARIABLE)
    }
    current_group_counts = {
        group: sum(
            entry["sector_group"] == group and entry["is_aggregate"].lower() == "false"
            for entry in current_mapping.values()
        )
        for group in CURRENT_EXPECTED_GROUP_COUNTS
    }
    current_aggregates = sum(
        entry["is_aggregate"].lower() == "true" for entry in current_mapping.values()
    )
    if current_group_counts != CURRENT_EXPECTED_GROUP_COUNTS or current_aggregates != 1:
        raise ValueError(
            "Mapping 2026 harus berisi 17 kategori (Primer 2, Sekunder 4, "
            f"Tersier 11) + 1 agregat. Ditemukan: {current_group_counts}, "
            f"agregat={current_aggregates}"
        )
    if any(
        entry["is_aggregate"].lower() == "true" and entry["sector_group"] != "PDRB"
        for entry in current_mapping.values()
    ):
        raise ValueError("Kategori agregat 2026 harus memiliki sector_group='PDRB'")

    if len(mapping) != 22:
        raise ValueError(f"Mapping ADHK harus memiliki 22 baris; ditemukan {len(mapping)}")

    return mapping


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


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------
def build(args: argparse.Namespace) -> int:
    print("=" * 72)
    print("BPS ADHK TIME-SERIES PREPARATION")
    print("=" * 72)
    print("Input samples :", SAMPLES_DIR)
    print("Mapping       :", REFERENCE_FILE)
    print("Output        :", args.output_dir)
    print("Dry run       :", args.dry_run)
    print("Tolerance     :", args.tolerance, "miliar rupiah")

    historical_files: list[tuple[int, Path, list[dict[str, str]], list[str]]] = []
    canonical_columns: list[str] | None = None

    for period_id in HISTORICAL_PERIODS:
        path = locate_source_file(HISTORICAL_VARIABLE, period_id)
        columns, rows = read_csv(path)
        if canonical_columns is None:
            canonical_columns = columns
        elif columns != canonical_columns:
            raise ValueError(f"Skema kolom tidak konsisten pada {path.name}")

        validate_source_rows(
            rows,
            variable_id=HISTORICAL_VARIABLE,
            period_id=period_id,
            expected_rows=EXPECTED_HISTORICAL_ROWS_PER_PERIOD,
            source_name=path.name,
        )
        years = {row["period_label"].strip() for row in rows}
        if len(years) != 1:
            raise ValueError(f"{path.name}: period_label tidak konsisten: {sorted(years)}")
        expected_year = str(2022 + (period_id - 122))
        if years != {expected_year}:
            raise ValueError(
                f"{path.name}: periode {period_id} seharusnya tahun {expected_year}, "
                f"ditemukan {sorted(years)}"
            )
        historical_files.append((period_id, path, rows, columns))
        print(
            f"[PASS] Variable {HISTORICAL_VARIABLE} / period {period_id}: "
            f"{len(rows):,} rows ({path.name})"
        )

    current_path = locate_source_file(CURRENT_VARIABLE, CURRENT_PERIOD)
    current_columns, all_2026_rows = read_csv(current_path)
    if canonical_columns is not None and current_columns != canonical_columns:
        raise ValueError(
            f"Skema kolom variable {CURRENT_VARIABLE} tidak konsisten: {current_path.name}"
        )
    validate_source_rows(
        all_2026_rows,
        variable_id=CURRENT_VARIABLE,
        period_id=CURRENT_PERIOD,
        expected_rows=EXPECTED_CURRENT_ROWS,
        source_name=current_path.name,
    )
    current_years = {row["period_label"].strip() for row in all_2026_rows}
    if current_years != {"2026"}:
        raise ValueError(f"File 2775/126 seharusnya tahun 2026; ditemukan {sorted(current_years)}")

    # Mapping is keyed by (variable_id, turvar_id), because category identifiers
    # belong to their source variable and must not be mixed across variables.
    all_historical_rows = [row for _, _, rows, _ in historical_files for row in rows]
    mapping = load_mapping(REFERENCE_FILE, all_historical_rows, all_2026_rows)
    print(f"[PASS] Category crosswalk: {len(mapping)} entries across variables 2534 and 2775")
    print(f"[PASS] 2026 categories: 17 detailed industries + 1 published PDRB aggregate")

    # Normalized output: preserve every source observation, without summing.
    normalized: list[dict[str, Any]] = []
    source_columns = current_columns

    for _, _, rows, columns in historical_files:
        for row in rows:
            category_id = row["turvar_id"].strip()
            entry = mapping[(str(HISTORICAL_VARIABLE), category_id)]
            aggregate = entry["is_aggregate"].lower() == "true"
            normalized.append(normalized_row(
                row,
                columns,
                category_type="aggregate" if aggregate else "published_sector_group",
                sector_group="Total PDRB" if aggregate else entry["sector_group"],
                is_aggregate=aggregate,
                aggregation_method="published_by_bps",
            ))

    for row in all_2026_rows:
        category_id = row["turvar_id"].strip()
        entry = mapping[(str(CURRENT_VARIABLE), category_id)]
        aggregate = entry["is_aggregate"].lower() == "true"
        normalized.append(normalized_row(
            row,
            source_columns,
            category_type="aggregate" if aggregate else "industry",
            sector_group="Total PDRB" if aggregate else entry["sector_group"],
            is_aggregate=aggregate,
            aggregation_method="published_by_bps" if aggregate else "not_aggregated",
        ))

    # Comparable time series: published broad groups for 2022-2025, then
    # derived broad groups plus the published PDRB aggregate for 2026.
    timeseries: list[dict[str, str]] = []
    for _, _, rows, _ in historical_files:
        for row in rows:
            category_id = row["turvar_id"].strip()
            entry = mapping[(str(HISTORICAL_VARIABLE), category_id)]
            aggregate = entry["is_aggregate"].lower() == "true"
            group = entry["sector_group"]
            timeseries.append(timeseries_row(
                base=row,
                series_name="PDRB" if aggregate else f"Sektor {group}",
                sector_group="Total PDRB" if aggregate else group,
                value=parse_value(row["value"], context=row["datacontent_key"]),
                is_aggregate=aggregate,
                aggregation_method="published_by_bps",
                source_rows=[row],
            ))

    # Index 2026 source observations by region-quarter-unit.
    records_by_key: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in all_2026_rows:
        key = (
            row["vervar_id"].strip(),
            row["period_id"].strip(),
            row["subperiod_id"].strip(),
            row["unit"].strip(),
        )
        records_by_key[key].append(row)

    base_keys = set(records_by_key)
    if len(base_keys) != EXPECTED_REGIONS * 2:
        raise ValueError(
            f"Ekspektasi {EXPECTED_REGIONS * 2:,} kombinasi wilayah-triwulan 2026; "
            f"ditemukan {len(base_keys):,}"
        )
    region_ids = {key[0] for key in base_keys}
    period_ids = {key[1] for key in base_keys}
    subperiod_ids = {key[2] for key in base_keys}
    if len(region_ids) != EXPECTED_REGIONS or period_ids != {str(CURRENT_PERIOD)} or len(subperiod_ids) != 2:
        raise ValueError(
            "Cakupan 2026 tidak sesuai: "
            f"wilayah={len(region_ids)}, period={sorted(period_ids)}, "
            f"subperiode={sorted(subperiod_ids)}"
        )

    expected_ids_by_group: dict[str, set[str]] = defaultdict(set)
    expected_all_detail_ids: set[str] = set()
    current_mapping = {
        category_id: entry
        for (variable_id, category_id), entry in mapping.items()
        if variable_id == str(CURRENT_VARIABLE)
    }
    for category_id, entry in current_mapping.items():
        if entry["is_aggregate"].lower() == "false":
            expected_ids_by_group[entry["sector_group"]].add(category_id)
            expected_all_detail_ids.add(category_id)

    reconciliation: list[dict[str, str]] = []
    for key in sorted(base_keys):
        region_id, period_id, subperiod_id, unit = key
        records = records_by_key[key]
        if len(records) != 18:
            raise ValueError(
                f"Wilayah {region_id}, subperiode {subperiod_id}: seharusnya 18 "
                f"observasi kategori, ditemukan {len(records)}"
            )

        detail_rows = [
            row for row in records
            if current_mapping[row["turvar_id"].strip()]["is_aggregate"].lower() == "false"
        ]
        detail_ids = [row["turvar_id"].strip() for row in detail_rows]
        if len(detail_ids) != 17 or set(detail_ids) != expected_all_detail_ids or len(set(detail_ids)) != 17:
            raise ValueError(
                f"Kategori 2026 tidak lengkap/duplikat untuk wilayah {region_id}, "
                f"periode {period_id}, subperiode {subperiod_id}"
            )

        total_records = [
            row for row in records
            if current_mapping[row["turvar_id"].strip()]["is_aggregate"].lower() == "true"
        ]
        if len(total_records) != 1:
            raise ValueError(
                f"Harus ada satu agregat PDRB untuk wilayah {region_id}, "
                f"subperiode {subperiod_id}; ditemukan {len(total_records)}"
            )

        base = records[0]
        total = parse_value(
            total_records[0]["value"], context=total_records[0]["datacontent_key"]
        )
        sector_sums: dict[str, Decimal] = {}

        for group_name, expected_ids in expected_ids_by_group.items():
            group_rows = [
                row for row in detail_rows
                if current_mapping[row["turvar_id"].strip()]["sector_group"] == group_name
            ]
            actual_ids = {row["turvar_id"].strip() for row in group_rows}
            if len(group_rows) != len(expected_ids) or actual_ids != expected_ids:
                raise ValueError(
                    f"Kategori kelompok {group_name} tidak lengkap untuk wilayah "
                    f"{region_id}, subperiode {subperiod_id}"
                )
            sector_sum = sum(
                (parse_value(row["value"], context=row["datacontent_key"]) for row in group_rows),
                Decimal("0"),
            )
            sector_sums[group_name] = sector_sum
            timeseries.append(timeseries_row(
                base=base,
                series_name=f"Sektor {group_name}",
                sector_group=group_name,
                value=sector_sum,
                is_aggregate=False,
                aggregation_method="sum_of_mapped_17_industry_categories",
                source_rows=group_rows,
            ))

        # Keep the published PDRB total as its own non-additive aggregate series.
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

    historical_ts_count = sum(len(rows) for _, _, rows, _ in historical_files)
    expected_current_ts_count = EXPECTED_REGIONS * 2 * 4
    expected_ts_count = historical_ts_count + expected_current_ts_count
    if len(timeseries) != expected_ts_count:
        raise ValueError(
            f"Jumlah time-series tidak sesuai: {len(timeseries):,}; "
            f"ekspektasi {expected_ts_count:,}"
        )
    if len(normalized) != 59_624:
        raise ValueError(
            f"Jumlah normalized observations tidak sesuai: {len(normalized):,}; "
            "ekspektasi 59.624"
        )
    if len(reconciliation) != 1_028:
        raise ValueError(
            f"Jumlah baris reconciliation tidak sesuai: {len(reconciliation):,}; "
            "ekspektasi 1.028"
        )

    ts_keys = [
        (row["source_variable_id"], row["period_id"], row["subperiod_id"],
         row["vervar_id"], row["series_name"])
        for row in timeseries
    ]
    if len(ts_keys) != len(set(ts_keys)):
        raise ValueError("Ditemukan duplikasi key pada output comparable time-series")

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
    print(
        f"PDRB total vs 17 sectors di luar toleransi "
        f"Rp{args.tolerance} miliar: {outside_tolerance}"
    )
    print(f"Maximum absolute difference: {format_decimal(max_difference)} miliar rupiah")

    if args.dry_run:
        print("\n[DRY RUN] Tidak ada file output yang ditulis.")
        return 0

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_columns = list(canonical_columns or []) + NORMALIZED_EXTRA_COLUMNS

    observations_path = output_dir / "bps_adhk_observations_normalized.csv"
    timeseries_path = output_dir / "bps_adhk_sector_timeseries.csv"
    reconciliation_path = output_dir / "bps_adhk_2026_reconciliation.csv"

    write_csv(observations_path, normalized_columns, normalized)
    write_csv(timeseries_path, TIMESERIES_COLUMNS, timeseries)
    write_csv(reconciliation_path, RECONCILIATION_COLUMNS, reconciliation)

    print("\n=== OUTPUT FILES ===")
    print("Normalized observations:", observations_path)
    print("Comparable time-series :", timeseries_path)
    print("2026 reconciliation    :", reconciliation_path)
    print("\n[SUCCESS] BPS ADHK time-series preparation selesai.")
    if outside_tolerance:
        print(
            "[WARNING] Ada selisih total PDRB terhadap penjumlahan 17 kategori "
            "di luar toleransi review yang dipilih. Periksa file reconciliation."
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalisasi dan bentuk comparable time series BPS ADHK PDRB."
    )
    parser.add_argument(
        "--input-dir", type=Path, default=SAMPLES_DIR,
        help="Folder raw JSON/CSV hasil ingestion BPS.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validasi dan hitung transformasi tanpa menulis output.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Folder output (default: data/bps/processed).",
    )
    parser.add_argument(
        "--tolerance", type=Decimal, default=REVIEW_TOLERANCE_DEFAULT,
        help="Toleransi diagnostik selisih PDRB vs jumlah 17 kategori (miliar rupiah).",
    )
    return parser.parse_args()


def main() -> int:
    global SAMPLES_DIR
    args = parse_args()
    SAMPLES_DIR = args.input_dir.expanduser().resolve()
    if not SAMPLES_DIR.is_dir():
        raise FileNotFoundError(f"Input directory tidak ditemukan: {SAMPLES_DIR}")
    if args.tolerance < 0:
        raise ValueError("Toleransi tidak boleh negatif")
    return build(args)


if __name__ == "__main__":
    raise SystemExit(main())
