import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://career.astra.co.id"
URLS = [urljoin(BASE, "/robots.txt"), urljoin(BASE, "/lowongan")]

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0; +https://example.com/bot-info)"
}
session = requests.Session()
session.headers.update(headers)

for url in URLS:
    print("\n" + "=" * 80)
    print("URL:", url)
    try:
        response = session.get(url, timeout=25)
        print("HTTP status :", response.status_code)
        print("Final URL   :", response.url)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Size        :", len(response.text), "characters")

        if url.endswith("robots.txt"):
            print("\n--- ROBOTS.TXT CONTENT (first 5000 chars) ---")
            print(response.text[:5000])
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        print("\nPage title  :", soup.title.get_text(" ", strip=True) if soup.title else "(no title)")
        print("Visible text:", soup.get_text(" ", strip=True)[:700])

        scripts = [urljoin(response.url, s.get("src")) for s in soup.find_all("script") if s.get("src")]
        print("\n--- JAVASCRIPT FILES ---")
        for item in scripts[:30]:
            print(item)

        print("\n--- LINKS CONTAINING 'lowongan' OR 'detail' ---")
        found = 0
        for a in soup.find_all("a", href=True):
            href = urljoin(response.url, a["href"])
            label = a.get_text(" ", strip=True)
            if "lowongan" in href.lower() or "detail" in href.lower():
                print(f"{label[:80]!r} -> {href}")
                found += 1
                if found >= 30:
                    break
        if found == 0:
            print("(Tidak ditemukan link lowongan/detail pada HTML awal.)")

        print("\n--- POSSIBLE API REFERENCES IN HTML ---")
        patterns = [
            r'https?://[^"\']+',
            r'["\']([^"\']*(?:api|graphql|vacanc|job|career)[^"\']*)["\']',
        ]
        matches = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, response.text, flags=re.I))
        unique = []
        for item in matches:
            if item not in unique:
                unique.append(item)
        for item in unique[:40]:
            print(item[:300])

        print("\n--- HTML PREVIEW ---")
        print(response.text[:1800])

    except requests.RequestException as exc:
        print("REQUEST ERROR:", repr(exc))

print("\nSelesai. Ini hanya pemeriksaan akses dan struktur HTML, belum mengambil seluruh lowongan.")
