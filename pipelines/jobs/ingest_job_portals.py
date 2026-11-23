#!/usr/bin/env python3
"""Ingest CSV Job Portals ke public.arza_job_portals."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from psycopg2.extras import Json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry, upsert_records

UPSERT_SQL = """
INSERT INTO public.arza_job_portals (
    source, source_job_id, record_hash, job_title, company, sector, location,
    salary, employment_type, work_mode, category, education, education_level,
    experience, majors, skills, requirements, qualifications, documents,
    description, job_description, additional_information, test_location,
    placement_location, selection_stages, duration, date_posted, published_date,
    deadline, announcement_date, application_period, job_url, application_url,
    status, scraped_at, raw_data, created_at, updated_at
) VALUES (
    :source, :source_job_id, :record_hash, :job_title, :company, :sector, :location,
    :salary, :employment_type, :work_mode, :category, :education, :education_level,
    :experience, :majors, :skills, :requirements, :qualifications, :documents,
    :description, :job_description, :additional_information, :test_location,
    :placement_location, :selection_stages, :duration, :date_posted, :published_date,
    :deadline, :announcement_date, :application_period, :job_url, :application_url,
    :status, :scraped_at, :raw_data, :created_at, :updated_at
)
ON CONFLICT (source, record_hash) DO UPDATE SET
    source_job_id = EXCLUDED.source_job_id,
    job_title = EXCLUDED.job_title,
    company = EXCLUDED.company,
    sector = EXCLUDED.sector,
    location = EXCLUDED.location,
    salary = EXCLUDED.salary,
    employment_type = EXCLUDED.employment_type,
    work_mode = EXCLUDED.work_mode,
    category = EXCLUDED.category,
    education = EXCLUDED.education,
    education_level = EXCLUDED.education_level,
    experience = EXCLUDED.experience,
    majors = EXCLUDED.majors,
    skills = EXCLUDED.skills,
    requirements = EXCLUDED.requirements,
    qualifications = EXCLUDED.qualifications,
    documents = EXCLUDED.documents,
    description = EXCLUDED.description,
    job_description = EXCLUDED.job_description,
    additional_information = EXCLUDED.additional_information,
    test_location = EXCLUDED.test_location,
    placement_location = EXCLUDED.placement_location,
    selection_stages = EXCLUDED.selection_stages,
    duration = EXCLUDED.duration,
    date_posted = EXCLUDED.date_posted,
    published_date = EXCLUDED.published_date,
    deadline = EXCLUDED.deadline,
    announcement_date = EXCLUDED.announcement_date,
    application_period = EXCLUDED.application_period,
    job_url = EXCLUDED.job_url,
    application_url = EXCLUDED.application_url,
    status = EXCLUDED.status,
    scraped_at = EXCLUDED.scraped_at,
    raw_data = EXCLUDED.raw_data,
    updated_at = EXCLUDED.updated_at
"""

def val(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value) and str(value).strip():
            return value
    return None

def clean(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value or None

def parse_date(value):
    value = clean(value)
    if not value:
        return None
    dt = pd.to_datetime(value, errors="coerce", dayfirst=True, utc=True)
    return None if pd.isna(dt) else dt.date()

def parse_datetime(value, fallback):
    value = clean(value)
    if not value:
        return fallback
    dt = pd.to_datetime(value, errors="coerce", utc=True)
    return fallback if pd.isna(dt) else dt.to_pydatetime()

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

def make_hash(source, source_id, url, title, company, location):
    identity = clean(source_id) or clean(url)
    if not identity:
        identity = "|".join([clean(title) or "", clean(company) or "", clean(location) or ""])
    raw = f"{(clean(source) or 'UNKNOWN').lower()}|{identity.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def discover_files(root: Path):
    patterns = ("magenta_jobs*.csv", "jobnesia_jobs*.csv", "bersamabumn_jobs*.csv")
    return sorted({p.resolve() for pattern in patterns for p in root.rglob(pattern)})

def normalize(row, now):
    title = clean(val(row, "job_title", "title", "position"))
    if not title:
        raise ValueError("Kolom job_title kosong.")
    source = clean(val(row, "source")) or "UNKNOWN"
    company = clean(val(row, "company", "company_name"))
    location = clean(val(row, "location"))
    url = clean(val(row, "job_url", "url", "link"))
    status_text = clean(val(row, "status"))
    status = status_text.upper() if status_text and status_text.upper() in {"OPEN", "CLOSED", "UNKNOWN"} else "UNKNOWN"
    return {
        "source": source,
        "source_job_id": clean(val(row, "source_job_id", "job_id", "id")),
        "record_hash": make_hash(source, val(row, "source_job_id", "job_id", "id"), url, title, company, location),
        "job_title": title,
        "company": company,
        "sector": clean(val(row, "sector", "industry")),
        "location": location,
        "salary": clean(val(row, "salary", "salary_range")),
        "employment_type": clean(val(row, "employment_type", "job_type")),
        "work_mode": clean(val(row, "work_mode")),
        "category": clean(val(row, "category")),
        "education": clean(val(row, "education")),
        "education_level": clean(val(row, "education_level")),
        "experience": clean(val(row, "experience")),
        "majors": clean(val(row, "majors")),
        "skills": clean(val(row, "skills")),
        "requirements": clean(val(row, "requirements")),
        "qualifications": clean(val(row, "qualifications")),
        "documents": clean(val(row, "documents")),
        "description": clean(val(row, "description")),
        "job_description": clean(val(row, "job_description")),
        "additional_information": clean(val(row, "additional_information")),
        "test_location": clean(val(row, "test_location")),
        "placement_location": clean(val(row, "placement_location")),
        "selection_stages": clean(val(row, "selection_stages")),
        "duration": clean(val(row, "duration")),
        "date_posted": parse_date(val(row, "date_posted", "posting_date")),
        "published_date": parse_date(val(row, "published_date")),
        "deadline": parse_date(val(row, "deadline", "closing_date")),
        "announcement_date": parse_date(val(row, "announcement_date")),
        "application_period": clean(val(row, "application_period")),
        "job_url": url,
        "application_url": clean(val(row, "application_url", "apply_url")),
        "status": status,
        "scraped_at": parse_datetime(val(row, "scraped_at"), now),
        "raw_data": json_value(row),
        "created_at": now,
        "updated_at": now,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(PROJECT_ROOT / "raw_data" / "jobportal"))
    parser.add_argument("--files", nargs="*", help="Path CSV spesifik; jika diisi, discovery otomatis tidak digunakan.")
    args = parser.parse_args()
    files = [Path(x).resolve() for x in args.files] if args.files else discover_files(Path(args.input_dir).resolve())
    if not files:
        raise FileNotFoundError(f"Tidak ditemukan CSV Job Portals di {args.input_dir}")

    engine = get_engine_with_retry()
    total = 0
    try:
        for path in files:
            print(f"Membaca {path}")
            df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            now = datetime.now(timezone.utc)
            records = [normalize(row, now) for row in df.to_dict(orient="records")]
            count = upsert_records(engine, UPSERT_SQL, records)
            total += count
            print(f"{path.name}: {len(df)} dibaca, {count} UPSERT.")
        print(f"Total Job Portals: {total} baris UPSERT.")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
