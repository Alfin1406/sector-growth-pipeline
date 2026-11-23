
import requests
from bs4 import BeautifulSoup
import json

BASE = "https://karier.kai.id"
session = requests.Session()

page = session.get(f"{BASE}/lowongan", timeout=30)
soup = BeautifulSoup(page.text, "html.parser")
csrf = soup.find("meta", attrs={"name": "csrf-token"})["content"]

payload = {
    "method": "GET",
    "endpoint": "/api/vacancy/list-vacancy",
    "query": {
        "keyword": "",
        "lokasiId": None,
        "companyCode": None,
        "page": 1,
        "size": 100,
        "sortBy": 1
    }
}

headers = {
    "X-CSRF-TOKEN": csrf,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE}/lowongan",
    "Origin": BASE,
    "Accept": "application/json"
}

r = session.post(
    f"{BASE}/send-request-portal",
    json=payload,
    headers=headers,
    timeout=30
)
r.raise_for_status()

result = r.json()
print("TOTAL DATA:", result.get("pagination", {}).get("totalData"))

for item in result.get("data", []):
    print("\n" + "=" * 65)
    print("ID             :", item.get("vacancyId"))
    print("JUDUL          :", item.get("judul"))
    print("STATUS         :", item.get("status"))
    print("APPROVED       :", item.get("isApprove"))
    print("PERUSAHAAN     :", item.get("companyName"))
    print("COMPANY CODE   :", item.get("companyCode"))
    print("JENIS LOWONGAN :", item.get("vacancyTypeDisplayName"))
    print("TANGGAL MULAI  :", item.get("startValidDate"))
    print("TANGGAL AKHIR  :", item.get("endValidDate"))
    print("TANGGAL LAMAR  :", item.get("applyDate"))
    print("URL DETAIL     :", f"{BASE}/lowongan-detail/{item.get('vacancyId')}")

    print("\n--- LOKASI ---")
    print(json.dumps(
        item.get("vacancyLocations"),
        indent=2,
        ensure_ascii=False
    )[:3000])

    print("\n--- FORMASI ---")
    print(json.dumps(
        item.get("vacancyFormations"),
        indent=2,
        ensure_ascii=False
    )[:5000])

    print("\n--- SELEKSI ---")
    print(json.dumps(
        item.get("vacancySelections"),
        indent=2,
        ensure_ascii=False
    )[:3000])

    print("\n--- DESKRIPSI (TEKS AWAL) ---")
    desc = BeautifulSoup(
        item.get("description") or "",
        "html.parser"
    ).get_text(" ", strip=True)
    print(desc[:1500])
