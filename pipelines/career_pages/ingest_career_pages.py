#!/usr/bin/env python3
"""Ingest CSV Career Pages ke public.arza_career_pages."""

import argparse
import hashlib
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

UPSERT_SQL = """
INSERT INTO public.arza_career_pages (
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
    job_title = EXCLUDED.job_title, company = EXCLUDED.company,
    sector = EXCLUDED.sector, location = EXCLUDED.location,
    salary = EXCLUDED.salary, employment_type = EXCLUDED.employment_type,
    work_mode = EXCLUDED.work_mode, category = EXCLUDED.category,
    education = EXCLUDED.education, education_level = EXCLUDED.education_level,
    experience = EXCLUDED.experience, majors = EXCLUDED.majors,
    skills = EXCLUDED.skills, requirements = EXCLUDED.requirements,
    qualifications = EXCLUDED.qualifications, documents = EXCLUDED.documents,
    description = EXCLUDED.description, job_description = EXCLUDED.job_description,
    additional_information = EXCLUDED.additional_information,
    test_location = EXCLUDED.test_location, placement_location = EXCLUDED.placement_location,
    selection_stages = EXCLUDED.selection_stages, duration = EXCLUDED.duration,
    date_posted = EXCLUDED.date_posted, published_date = EXCLUDED.published_date,
    deadline = EXCLUDED.deadline, announcement_date = EXCLUDED.announcement_date,
    application_period = EXCLUDED.application_period, job_url = EXCLUDED.job_url,
    application_url = EXCLUDED.application_url, status = EXCLUDED.status,
    scraped_at = EXCLUDED.scraped_at, raw_data = EXCLUDED.raw_data,
    updated_at = EXCLUDED.updated_at
"""


def clean(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def val(row, *keys):
    return next((row[k] for k in keys if k in row and clean(row[k]) is not None), None)


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    is_iso = bool(re.match(r"^\d{4}-\d{2}-\d{2}", value))
    result = pd.to_datetime(value, errors="coerce", dayfirst=not is_iso, utc=True)
    return None if pd.isna(result) else result.date()


def make_hash(source, source_id, url, title, company, location):
    identity = clean(source_id) or clean(url) or "|".join(
        clean(x) or "" for x in (title, company, location)
    )
    return hashlib.sha256(f"{source.lower()}|{identity.lower()}".encode()).hexdigest()


def normalize(row, now):
    title = clean(val(row, "job_title", "title", "position"))
    if not title:
        return None  # Baris tanpa judul tidak layak menjadi record.

    source = clean(val(row, "source")) or "UNKNOWN"
    company = clean(val(row, "company", "company_name"))
    location = clean(val(row, "location"))
    url = clean(val(row, "job_url", "url", "link"))

    raw_status = clean(val(row, "status"))
    status = raw_status.upper() if raw_status else "UNKNOWN"
    if status not in {"OPEN", "CLOSED", "UNKNOWN"}:
        status = "UNKNOWN"

    source_id = val(row, "source_job_id", "job_id", "id")
    get = lambda *keys: clean(val(row, *keys))

    raw = {
        k: (v.item() if hasattr(v, "item") else v)
        for k, v in row.items()
    }
    raw = {k: (None if pd.isna(v) else v) for k, v in raw.items()}

    return {
        "source": source,
        "source_job_id": clean(source_id),
        "record_hash": make_hash(source, source_id, url, title, company, location),
        "job_title": title, "company": company, "sector": get("sector", "industry"),
        "location": location, "salary": get("salary", "salary_range"),
        "employment_type": get("employment_type", "job_type"),
        "work_mode": get("work_mode"), "category": get("category"),
        "education": get("education"), "education_level": get("education_level"),
        "experience": get("experience"), "majors": get("majors"),
        "skills": get("skills"), "requirements": get("requirements"),
        "qualifications": get("qualifications"), "documents": get("documents"),
        "description": get("description"), "job_description": get("job_description"),
        "additional_information": get("additional_information"),
        "test_location": get("test_location"), "placement_location": get("placement_location"),
        "selection_stages": get("selection_stages"), "duration": get("duration"),
        "date_posted": parse_date(val(row, "date_posted", "posting_date")),
        "published_date": parse_date(val(row, "published_date")),
        "deadline": parse_date(val(row, "deadline", "closing_date")),
        "announcement_date": parse_date(val(row, "announcement_date")),
        "application_period": get("application_period"),
        "job_url": url, "application_url": get("application_url", "apply_url"),
        "status": status,
        "scraped_at": pd.to_datetime(get("scraped_at"), errors="coerce", utc=True).to_pydatetime()
            if get("scraped_at") and not pd.isna(pd.to_datetime(get("scraped_at"), errors="coerce", utc=True))
            else now,
        "raw_data": Json(raw, dumps=lambda obj: json.dumps(obj, ensure_ascii=False, default=str)),
        "created_at": now, "updated_at": now,
    }


def discover_files(folder):
    patterns = ("alkindo_jobs*.csv", "bca_jobs*.csv", "bersamabumn_jobs*.csv")
    return sorted({p.resolve() for pattern in patterns for p in folder.rglob(pattern) if p.is_file()})


def main():
    parser = argparse.ArgumentParser(description="Ingest Career Pages ke Neon DB.")
    parser.add_argument("--input-dir", default=str(PROJECT_ROOT / "raw_data" / "careerpages"))
    parser.add_argument("--files", nargs="*", help="Path CSV spesifik.")
    args = parser.parse_args()

    folder = Path(args.input_dir).resolve()
    files = [Path(p).resolve() for p in args.files] if args.files else discover_files(folder)
    if not files:
        raise FileNotFoundError(f"Tidak ditemukan CSV Career Pages di {folder}")

    print(f"File ditemukan: {len(files)}")
    for path in files:
        print(f" - {path.name}")

    engine = get_engine_with_retry()
    total_upsert, total_closed, total_invalid = 0, 0, 0
    try:
        for path in files:
            df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            now = datetime.now(timezone.utc)
            records, closed, invalid = [], 0, 0

            for row in df.to_dict(orient="records"):
                record = normalize(row, now)
                if record is None:
                    invalid += 1
                elif record["status"] == "CLOSED":
                    closed += 1
                else:  # OPEN dan UNKNOWN disimpan; UNKNOWN tidak dianggap lowongan aktif.
                    records.append(record)

            count = upsert_records(engine, UPSERT_SQL, records) if records else 0
            total_upsert += count
            total_closed += closed
            total_invalid += invalid
            print(f"{path.name}: {len(df)} dibaca, {count} UPSERT, "
                  f"{closed} CLOSED dilewati, {invalid} tanpa judul dilewati.")

        print("-" * 55)
        print(f"Total UPSERT: {total_upsert}")
        print(f"Total CLOSED dilewati: {total_closed}")
        print(f"Total tanpa judul dilewati: {total_invalid}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()