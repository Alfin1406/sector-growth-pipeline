
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Halaman pencarian Jobnesia
url = "https://jobnesia.id/jobs/?q=data&location=term%3AJakarta-selatan-jakarta-raya"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; AcademicResearch/1.0)"
}

response = requests.get(
    url,
    headers=headers,
    timeout=20
)

print("Status Code:", response.status_code)
print("Content Type:", response.headers.get("Content-Type"))
print("URL:", response.url)

soup = BeautifulSoup(response.text, "html.parser")

print("\nJudul Halaman:")
print(soup.title.get_text(strip=True) if soup.title else "Tidak ditemukan")

# Mencari link detail lowongan
print("\n=== LINK DETAIL LOWONGAN ===\n")

job_links = []

for link in soup.find_all("a", href=True):
    href = urljoin(url, link["href"])
    text = link.get_text(" ", strip=True)

    if "/jobs/" in href and href.rstrip("/") != "https://jobnesia.id/jobs":
        if "?" not in href and href not in job_links:
            job_links.append(href)

            print("Judul:", text)
            print("URL:", href)
            print("-" * 50)

print("\nTotal link ditemukan:", len(job_links))

# Memeriksa struktur HTML di sekitar link lowongan
print("\n=== STRUKTUR HTML KARTU LOWONGAN ===\n")

if job_links:
    first_link = soup.find("a", href=True)

    for link in soup.find_all("a", href=True):
        if urljoin(url, link["href"]) == job_links[0]:
            parent = link

            for level in range(1, 5):
                parent = parent.parent

                if parent:
                    print(f"\nLevel {level}:")
                    print("Tag:", parent.name)
                    print("Class:", parent.get("class"))
                    print("ID:", parent.get("id"))
                    print("Teks:", parent.get_text(" ", strip=True)[:300])
            break
else:
    print("Belum ditemukan link detail lowongan.")
