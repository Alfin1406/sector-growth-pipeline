#!/usr/bin/env python3
"""Ingest BPS Ekspor-Impor (bulanan dan HS2) ke tabel Person 2."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from psycopg2.extras import Json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records

MONTH_MAP = {
    "jan": 1, "januari": 1, "january": 1,
    "feb": 2, "februari": 2, "february": 2,
    "mar": 3, "maret": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5, "mei": 5,
    "jun": 6, "juni": 6, "june": 6,
    "jul": 7, "juli": 7, "july": 7,
    "aug": 8, "agu": 8, "agustus": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "okt": 10, "oktober": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "des": 12, "desember": 12, "december": 12,
}

MONTHLY_SQL = """
INSERT INTO public.arza_bps_exim_monthly (
    tahun, bulan, nilai_ekspor_usd, berat_ekspor_kg,
    nilai_impor_usd, berat_impor_kg, source_file, raw_data, created_at
) VALUES (
    :tahun, :bulan, :nilai_ekspor_usd, :berat_ekspor_kg,
    :nilai_impor_usd, :berat_impor_kg, :source_file, :raw_data, :created_at
)
ON CONFLICT (tahun, bulan) DO UPDATE SET
    nilai_ekspor_usd = EXCLUDED.nilai_ekspor_usd,
    berat_ekspor_kg = EXCLUDED.berat_ekspor_kg,
    nilai_impor_usd = EXCLUDED.nilai_impor_usd,
    berat_impor_kg = EXCLUDED.berat_impor_kg,
    source_file = EXCLUDED.source_file,
    raw_data = EXCLUDED.raw_data
"""

HS2_SQL = """
INSERT INTO public.arza_bps_exim_hs2 (
    tahun, bulan, kode_hs, deskripsi_hs, nilai_ekspor_usd,
    berat_ekspor_kg, nilai_impor_usd, berat_impor_kg,
    source_file, raw_data, created_at
) VALUES (
    :tahun, :bulan, :kode_hs, :deskripsi_hs, :nilai_ekspor_usd,
    :berat_ekspor_kg, :nilai_impor_usd, :berat_impor_kg,
    :source_file, :raw_data, :created_at
)
ON CONFLICT (tahun, bulan, kode_hs) DO UPDATE SET
    deskripsi_hs = EXCLUDED.deskripsi_hs,
    nilai_ekspor_usd = EXCLUDED.nilai_ekspor_usd,
    berat_ekspor_kg = EXCLUDED.berat_ekspor_kg,
    nilai_impor_usd = EXCLUDED.nilai_impor_usd,
    berat_impor_kg = EXCLUDED.berat_impor_kg,
    source_file = EXCLUDED.source_file,
    raw_data = EXCLUDED.raw_data
"""


def clean(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def month_number(value):
    token = clean(value)
    if not token:
        raise ValueError("Bulan kosong.")
    token = token.lower()
    month = int(token) if token.isdigit() else MONTH_MAP.get(token) or MONTH_MAP.get(token[:3])
    if not month or not 1 <= int(month) <= 12:
        raise ValueError(f"Bulan tidak dikenali: {value!r}")
    return int(month)


def number(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    token = str(value).strip().replace(" ", "")
    # Format angka BPS: titik desimal; dukung juga format Indonesia 1.234,56.
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+,\d+", token):
        token = token.replace(".", "").replace(",", ".")
    elif "," in token and "." not in token:
        token = token.replace(",", ".")

    try:
        return float(token)
    except ValueError as exc:
        raise ValueError(f"Angka tidak dapat diparsing: {value!r}") from exc


def json_value(row):
    safe = {}
    for key, value in row.items():
        if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)):
            safe[str(key)] = None
        elif hasattr(value, "item"):
            safe[str(key)] = value.item()
        else:
            safe[str(key)] = value
    return Json(safe, dumps=lambda obj: json.dumps(obj, ensure_ascii=False, default=str))


def find_one(root, patterns):
    matches = {
        path.resolve()
        for pattern in patterns
        for path in root.rglob(pattern)
        if path.is_file()
    }
    return max(matches, key=lambda path: path.stat().st_mtime) if matches else None


def parse_hs(value):
    value = clean(value)
    if not value:
        raise ValueError("Kode HS dan Deskripsi kosong.")
    match = re.match(r"^\s*\[?(\d{2})\]?\s*[-–:]?\s*(.*?)\s*$", value)
    if not match:
        raise ValueError(f"Format kode HS tidak dikenali: {value!r}")
    return match.group(1), clean(match.group(2))


def read_csv(path):
    return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")


def ingest_monthly(engine, path):
    df = read_csv(path)
    now = datetime.now(timezone.utc)
    by_key = {}

    for row in df.to_dict(orient="records"):
        record = {
            "tahun": int(row["Tahun"]),
            "bulan": month_number(row["Bulan"]),
            "nilai_ekspor_usd": number(row.get("Nilai Ekspor (USD)")),
            "berat_ekspor_kg": number(row.get("Berat Ekspor (Kg)")),
            "nilai_impor_usd": number(row.get("Nilai Impor (USD)")),
            "berat_impor_kg": number(row.get("Berat Impor (Kg)")),
            "source_file": path.name,
            "raw_data": json_value(row),
            "created_at": now,
        }
        by_key[(record["tahun"], record["bulan"])] = record

    records = list(by_key.values())
    count = upsert_records(engine, MONTHLY_SQL, records) if records else 0
    print(f"Monthly {path.name}: {len(df)} dibaca, {count} UPSERT.")
    return count


def ingest_hs2(engine, path):
    df = read_csv(path)
    now = datetime.now(timezone.utc)
    by_key = {}

    for row in df.to_dict(orient="records"):
        kode, deskripsi = parse_hs(
            row.get("Kode HS dan Deskripsi", row.get("kode_hs"))
        )
        record = {
            "tahun": int(row["Tahun"]),
            "bulan": month_number(row["Bulan"]),
            "kode_hs": kode,
            "deskripsi_hs": deskripsi,
            "nilai_ekspor_usd": number(row.get("Nilai Ekspor (USD)")),
            "berat_ekspor_kg": number(row.get("Berat Ekspor (Kg)")),
            "nilai_impor_usd": number(row.get("Nilai Impor (USD)")),
            "berat_impor_kg": number(row.get("Berat Impor (Kg)")),
            "source_file": path.name,
            "raw_data": json_value(row),
            "created_at": now,
        }
        by_key[(record["tahun"], record["bulan"], kode)] = record

    records = list(by_key.values())
    count = upsert_records(engine, HS2_SQL, records) if records else 0
    print(f"HS2 {path.name}: {len(df)} dibaca, {count} UPSERT.")
    return count


def main():
    parser = argparse.ArgumentParser(description="Ingest BPS ekspor-impor Person 2.")
    parser.add_argument("--input-dir", default=str(PROJECT_ROOT / "raw_data" / "beacukai"))
    parser.add_argument("--monthly", help="Path CSV BPS ekspor-impor bulanan.")
    parser.add_argument("--hs2", help="Path CSV BPS ekspor-impor HS2.")
    args = parser.parse_args()

    root = Path(args.input_dir).resolve()
    monthly = Path(args.monthly).resolve() if args.monthly else find_one(
        root, ["bps_ekspor_impor_bulanan*.csv"]
    )
    hs2 = Path(args.hs2).resolve() if args.hs2 else find_one(
        root, ["bps_ekspor_impor_hs2*.csv"]
    )

    if not monthly and not hs2:
        raise FileNotFoundError(f"CSV BPS bulanan/HS2 tidak ditemukan di {root}")

    engine = get_engine_with_retry()
    try:
        monthly_count = ingest_monthly(engine, monthly) if monthly else 0
        hs2_count = ingest_hs2(engine, hs2) if hs2 else 0
        print(f"Total BPS: monthly={monthly_count}; HS2={hs2_count}.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()