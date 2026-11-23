import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ojk.go.id"
URL_PENGUMUMAN = f"{BASE_URL}/id/berita-dan-kegiatan/pengumuman/Default.aspx"
URL_REGULASI = f"{BASE_URL}/id/regulasi/otoritas-jasa-keuangan/rancangan-regulasi/Default.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}


def bersihkan_teks(teks) -> str:
    if not teks:
        return ""
    teks_bersih = (
        str(teks)
        .replace("\u200b", "")
        .replace("â€‹", "")
        .replace("â€", "")
        .replace("Â", "")
    )
    return re.sub(r"\s+", " ", teks_bersih).strip()


def _extract_links_from_soup(soup: BeautifulSoup, kategori: str) -> list[dict]:
    url_filter = (
        "/pengumuman/Pages/"
        if kategori == "Pengumuman"
        else "/rancangan-regulasi/Pages/"
    )
    items = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        judul = bersihkan_teks(a_tag.get_text(strip=True))
        link = a_tag["href"]

        if len(judul) > 25 and url_filter in link:
            if link.startswith("/"):
                link = BASE_URL + link
            if link not in seen:
                seen.add(link)
                items.append({"kategori": kategori, "judul": judul, "link": link})

    return items


def _find_postback_for_page(soup: BeautifulSoup, target_page: int) -> tuple[str, str] | None:
    """Mencari target __doPostBack untuk nomor halaman berikutnya."""
    target_text = str(target_page)
    for a_tag in soup.find_all("a", href=True):
        if a_tag.get_text(strip=True) == target_text and "__doPostBack" in a_tag["href"]:
            match = re.search(
                r"__doPostBack\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)",
                a_tag["href"],
            )
            if match:
                return match.group(1), match.group(2)
    return None


def _build_postback_payload(
    soup: BeautifulSoup, event_target: str, event_arg: str
) -> tuple[str | None, dict]:
    """Menyusun seluruh form field ASP.NET/SharePoint agar postback halaman valid."""
    form = soup.find("form", id="aspnetForm") or soup.find("form")
    if not form:
        return None, {}

    payload = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        inp_type = (inp.get("type") or "text").lower()
        if inp_type in ("submit", "button", "image", "reset", "file"):
            continue
        if inp_type in ("checkbox", "radio") and not inp.has_attr("checked"):
            continue
        payload[name] = inp.get("value", "")

    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        payload[name] = opt.get("value", "") if opt else ""

    payload["__EVENTTARGET"] = event_target
    payload["__EVENTARGUMENT"] = event_arg
    return form.get("action"), payload


def ekstrak_detail_ojk(
    url_detail: str, session: requests.Session | None = None
) -> tuple[str, str, str] | None:
    """Mengambil tanggal_rilis, isi_teks, dan link lampiran dari halaman detail OJK."""
    client = session or requests
    try:
        resp = client.get(url_detail, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        kontainer_utama = (
            soup.find("div", class_="content")
            or soup.find("div", id="ctl00_PlaceHolderMain")
            or soup
        )

        # 1. Ekstrak tanggal rilis (biarkan kosong jika tidak ketemu, jangan dipalsukan)
        tanggal_rilis = ""
        tag_tanggal = soup.find("time") or soup.find(
            class_=re.compile(r"date|tanggal|waktu", re.I)
        )
        if tag_tanggal:
            tanggal_rilis = bersihkan_teks(tag_tanggal.get_text())

        if not tanggal_rilis:
            pola_tanggal = (
                r"\b(\d{1,2}\s+"
                r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|"
                r"September|Oktober|November|Desember)\s+\d{4})\b"
            )
            match = re.search(pola_tanggal, kontainer_utama.get_text(), re.IGNORECASE)
            if match:
                tanggal_rilis = match.group(1)

        # 2. Ekstrak link lampiran dokumen
        lampiran = []
        for a in kontainer_utama.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip")):
                if href.startswith("/"):
                    href = BASE_URL + href
                if href not in lampiran:
                    lampiran.append(href)
                a.decompose()

        # 3. Ekstrak teks paragraf utama
        teks_valid = []
        teks_sampah = [
            "Lembaga negara independen yang mempunyai fungsi",
            "Gedung Sumitro Djojohadikusumo",
            "Page Content",
        ]
        for p in kontainer_utama.find_all("p"):
            teks_p = p.get_text(strip=True)
            if len(teks_p) > 30 and not any(s in teks_p for s in teks_sampah):
                teks_valid.append(teks_p)

        teks_isi = bersihkan_teks(" ".join(teks_valid))
        return tanggal_rilis, teks_isi, ", ".join(lampiran)

    except Exception as e:
        print(f"   [WARN] Gagal mengambil detail {url_detail}: {e}")
        return None


def scrape_ojk(
    url: str,
    kategori: str,
    existing_links: set[str] | None = None,
    max_pages: int = 3,
    delay_seconds: float = 1.5,
    fetch_details: bool = True,
) -> list[dict]:
    """
    Crawl daftar dokumen OJK hingga max_pages halaman secara in-memory.
    Otomatis berhenti lebih awal jika semua link di suatu halaman sudah ada di DB.
    """
    existing_links = existing_links or set()
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"\n[*] Memindai {kategori} OJK (maks {max_pages} halaman)...")
    targets_baru: list[dict] = []
    seen_in_run: set[str] = set()
    soup = None
    current_url = url

    for page_num in range(1, max_pages + 1):
        try:
            if page_num == 1:
                resp = session.get(url, timeout=20)
            else:
                postback = _find_postback_for_page(soup, page_num)
                if not postback:
                    print(f"    [Page {page_num}] Tombol halaman {page_num} tidak ditemukan. Berhenti.")
                    break

                event_target, event_arg = postback
                action, payload = _build_postback_payload(soup, event_target, event_arg)
                post_url = urljoin(current_url, action) if action else current_url
                resp = session.post(
                    post_url,
                    data=payload,
                    headers={"Referer": current_url},
                    timeout=20,
                )

            resp.raise_for_status()
            resp.encoding = "utf-8"
            current_url = resp.url
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"    [ERROR] Gagal membuka {kategori} halaman {page_num}: {e}")
            break

        page_items = _extract_links_from_soup(soup, kategori)
        fresh_items = [item for item in page_items if item["link"] not in seen_in_run]

        if page_num > 1 and not fresh_items:
            print(f"    [WARN] Halaman {page_num} mengembalikan link yang sama dengan halaman sebelumnya. Berhenti.")
            break

        for item in fresh_items:
            seen_in_run.add(item["link"])

        new_on_page = [item for item in fresh_items if item["link"] not in existing_links]
        print(
            f"    [Page {page_num}] Ditemukan {len(fresh_items)} link "
            f"({len(new_on_page)} baru, {len(fresh_items) - len(new_on_page)} sudah ada di DB)."
        )
        targets_baru.extend(new_on_page)

        # Early stop: jika seluruh halaman sudah ada di DB, halaman berikutnya pasti lebih lama
        if existing_links and not new_on_page:
            print(f"    [STOP] Semua link di halaman {page_num} sudah ada di DB. Early stop aktif.")
            break

        if page_num < max_pages:
            time.sleep(delay_seconds)

    if not fetch_details:
        return targets_baru

    print(f"[*] Mengeksekusi deep crawling untuk {len(targets_baru)} dokumen baru ({kategori})...")
    hasil_final: list[dict] = []
    for idx, item in enumerate(targets_baru, start=1):
        print(f"    ({idx}/{len(targets_baru)}) Sedot: {item['judul'][:55]}...")
        detail = ekstrak_detail_ojk(item["link"], session=session)
        if detail is None:
            continue

        tanggal_rilis, isi_teks, link_dokumen = detail
        hasil_final.append(
            {
                "kategori": item["kategori"],
                "tanggal_rilis": tanggal_rilis,
                "judul": item["judul"],
                "link": item["link"],
                "isi_teks": isi_teks,
                "link_dokumen_lampiran": link_dokumen,
            }
        )
        time.sleep(delay_seconds)

    return hasil_final


def scrape_all_ojk(
    existing_pengumuman: set[str] | None = None,
    existing_regulasi: set[str] | None = None,
    max_pages_pengumuman: int = 5,
    max_pages_regulasi: int = 3,
    fetch_details: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Helper utama untuk dipanggil langsung oleh ingest_ojk.py (in-memory)."""
    data_pengumuman = scrape_ojk(
        URL_PENGUMUMAN,
        "Pengumuman",
        existing_links=existing_pengumuman,
        max_pages=max_pages_pengumuman,
        fetch_details=fetch_details,
    )
    data_regulasi = scrape_ojk(
        URL_REGULASI,
        "Rancangan Regulasi",
        existing_links=existing_regulasi,
        max_pages=max_pages_regulasi,
        fetch_details=fetch_details,
    )
    return data_pengumuman, data_regulasi


if __name__ == "__main__":
    # Tes cepat pagination (2 halaman per kategori, tanpa sedot halaman detail dulu)
    p_links, r_links = scrape_all_ojk(
        max_pages_pengumuman=2,
        max_pages_regulasi=2,
        fetch_details=False,
    )
    print(f"\nRingkasan tes pagination -> Pengumuman: {len(p_links)} link, Regulasi: {len(r_links)} link")