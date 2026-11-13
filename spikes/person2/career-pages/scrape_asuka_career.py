
import requests
from collections import Counter
from urllib.parse import urljoin

BASE_URL = "https://careers.asukaindonesia.co.id"
API_URL = f"{BASE_URL}/api/jobs"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

print("=" * 70)
print("VERIFIKASI SELURUH LOWONGAN ASUKA")
print("=" * 70)

# ==========================================================
# TAHAP 1 - AMBIL SELURUH HALAMAN API
# ==========================================================

print("\n[TAHAP 1] Mengambil seluruh halaman API...")

page = 1
page_size = 12
all_jobs = []

while True:

    response = session.get(
        API_URL,
        params={
            "page": page,
            "pageSize": page_size
        },
        timeout=30
    )

    response.raise_for_status()
    result = response.json()

    jobs = result.get("data", [])
    total_count = result.get("totalCount", 0)

    print(
        f"Halaman {page}: "
        f"{len(jobs)} data"
    )

    if not jobs:
        break

    all_jobs.extend(jobs)

    if len(all_jobs) >= total_count:
        break

    page += 1

print("\nTotal data API :", len(all_jobs))
print("Total menurut API:", total_count)


# ==========================================================
# TAHAP 2 - STATUS LOWONGAN
# ==========================================================

print("\n[TAHAP 2] Menghitung status lowongan...")

status_counts = Counter(
    str(job.get("status") or "kosong").lower()
    for job in all_jobs
)

for status, count in status_counts.items():
    print(f"{status:15}: {count}")

# Hanya OPEN secara eksplisit
open_jobs = [
    job for job in all_jobs
    if str(job.get("status", "")).lower() == "open"
    and job.get("is_published") is True
    and job.get("deleted_at") is None
]

print("\nTotal lowongan OPEN dan published:", len(open_jobs))


# ==========================================================
# TAHAP 3 - DAFTAR LOWONGAN OPEN
# ==========================================================

print("\n[TAHAP 3] Daftar lowongan OPEN...")

for index, job in enumerate(open_jobs, 1):

    department = job.get("department") or {}

    if isinstance(department, dict):
        department_name = department.get("name", "")
    else:
        department_name = ""

    print(f"\n{index}. {job.get('title', '-')}")
    print("   Departemen :", department_name or "-")
    print("   Lokasi     :", job.get("location") or "-")
    print("   Tipe       :", job.get("employment_type") or "-")
    print("   Pendidikan :", job.get("education_requirement") or "-")
    print("   Pengalaman :", job.get("min_experience") or "-")
    print("   Deadline   :", job.get("application_deadline") or "-")
    print("   Slug       :", job.get("slug") or "-")
    print("   Deskripsi  :", "Ada" if job.get("description") else "Kosong")
    print("   Persyaratan:", "Ada" if job.get("requirements") else "Kosong")


# ==========================================================
# TAHAP 4 - PERIKSA HALAMAN DETAIL
# ==========================================================

print("\n[TAHAP 4] Memeriksa halaman detail lowongan...")

if open_jobs:

    sample = open_jobs[0]
    slug = sample.get("slug")

    if slug:

        detail_url = urljoin(
            BASE_URL,
            f"/jobs/{slug}"
        )

        detail_response = session.get(
            detail_url,
            timeout=30
        )

        print("URL Detail  :", detail_url)
        print("HTTP Status :", detail_response.status_code)
        print("Ukuran HTML :", len(detail_response.text))

        print("\nCuplikan HTML detail:")
        print(detail_response.text[:5000])

else:
    print("Tidak ada lowongan OPEN untuk diperiksa.")


# ==========================================================
# RINGKASAN
# ==========================================================

print("\n" + "=" * 70)
print("VERIFIKASI SELESAI")
print("=" * 70)
