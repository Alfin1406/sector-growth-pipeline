
import requests
import re

URL = "https://www.klob.id/static/js/main.e5775d60.chunk.js"

response = requests.get(URL, timeout=30)
js = response.text

# Cari semua pemanggilan API yang berkaitan dengan halaman detail pekerjaan
keywords = [
    "klobvacancyId",
    "jobDetail",
    "positionName",
    "employmentStatus",
    "corporateId",
    "UPDATE_DETAIL_JOB_VACANCY",
]

print("=" * 75)
print("ANTAM - ANALISIS FUNGSI DETAIL LOWONGAN")
print("=" * 75)

for keyword in keywords:
    matches = list(re.finditer(re.escape(keyword), js, re.IGNORECASE))

    print(f"\n[{keyword}] ditemukan: {len(matches)}")

    for match in matches[:8]:
        start = max(0, match.start() - 2500)
        end = min(len(js), match.end() + 3500)

        context = js[start:end]

        # Tampilkan konteks yang lebih mudah dibaca
        print("\n" + "-" * 60)
        print(context)

print("\n" + "=" * 75)
print("SELESAI")
print("=" * 75)
