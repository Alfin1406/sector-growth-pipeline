import io
import random
import re
import time
import warnings
from typing import Callable
from urllib.parse import quote, unquote

import pandas as pd
from curl_cffi import requests

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

IDX_API_URL = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"

PERIODE_TO_KUARTAL = {
    "TW1": "Q1",
    "TW2": "Q2",
    "TW3": "Q3",
    "audit": "FY",
}

MULTIPLIER = {
    "Satuan Penuh / Full Amount": 1,
    "Ribuan / In Thousand": 1_000,
    "Jutaan / In Million": 1_000_000,
    "Miliaran / In Billion": 1_000_000_000,
}

METRIC_KEYS = [
    "Kas_CurrentYear",
    "Kas_PriorYear",
    "TotalAset_CurrentYear",
    "TotalAset_PriorYear",
    "TotalLiabilitas_CurrentYear",
    "TotalLiabilitas_PriorYear",
    "TotalEkuitas_CurrentYear",
    "TotalEkuitas_PriorYear",
]

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Origin": "https://www.idx.co.id",
    "Referer": "https://www.idx.co.id/en/listed-companies/financial-statements-and-annual-report/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

EXCEL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.idx.co.id/",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/octet-stream, */*",
}


def _build_clean_idx_url(file_path: str) -> str:
    clean_path = re.sub(r"/+", "/", unquote(file_path).replace("\\", "/"))
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return f"https://www.idx.co.id{quote(clean_path, safe='/:-_.~()')}"


def fetch_financial_report_links(year: int = 2026, periode: str = "TW1") -> list[dict]:
    """Tahap 1 (in-memory): Ambil daftar URL Excel (.xlsx) laporan keuangan dari API IDX."""
    kuartal = PERIODE_TO_KUARTAL.get(periode, periode)
    params = {
        "periode": periode,
        "year": str(year),
        "indexFrom": 1,
        "pageSize": 2000,
        "reportType": "rdf",
        "kodeEmiten": "",
    }

    print(f"[*] Mengambil daftar tautan Excel IDX ({year} - {periode}/{kuartal})...")
    resp = requests.get(
        IDX_API_URL,
        params=params,
        headers=API_HEADERS,
        impersonate="chrome124",
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("Results", data.get("data", []))

    excel_links: list[dict] = []
    seen_emiten: set[str] = set()

    for item in results:
        kode = (item.get("KodeEmiten") or "").strip()
        if not kode or kode in seen_emiten:
            continue

        for att in item.get("Attachments", []):
            file_path = att.get("File_Path", "")
            if file_path.lower().endswith(".xlsx"):
                seen_emiten.add(kode)
                excel_links.append(
                    {
                        "KodeEmiten": kode,
                        "Tahun": int(year),
                        "Periode": kuartal,
                        "Excel_Link": _build_clean_idx_url(file_path),
                    }
                )
                break

    print(f"[*] Ditemukan {len(excel_links)} tautan Excel emiten unik.")
    return excel_links


def _to_float(val) -> float | None:
    if val is None or pd.isna(val):
        return None
    num = pd.to_numeric(val, errors="coerce")
    return None if pd.isna(num) else float(num)


def parse_and_normalize_excel(
    content: bytes, kode: str, tahun: int, kuartal: str, url_excel: str
) -> dict | None:
    """Tahap 2 & 3 (in-memory): Ekstrak sheet 1000000 & 1210000 lalu normalisasi pembulatan."""
    if b"PK" not in content[:4]:
        return None

    xls = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
    if "1000000" not in xls.sheet_names or "1210000" not in xls.sheet_names:
        return None

    df_umum = pd.read_excel(xls, sheet_name="1000000", header=None)
    df_neraca = pd.read_excel(xls, sheet_name="1210000", header=None)

    def get_umum(label: str):
        row = df_umum[df_umum[0] == label]
        return row.iloc[0, 1] if not row.empty else None

    def get_neraca(labels: list[str]) -> tuple[float | None, float | None]:
        row = df_neraca[df_neraca[0].isin(labels)]
        if row.empty:
            return None, None
        return _to_float(row.iloc[0, 1]), _to_float(row.iloc[0, 2])

    pembulatan_row = df_umum[
        df_umum[0].astype(str).str.contains("pembulatan|rounding", na=False, case=False)
    ]
    pembulatan = pembulatan_row.iloc[0, 1] if not pembulatan_row.empty else None
    pengali = MULTIPLIER.get(str(pembulatan).strip(), 1)

    kas_cur, kas_pri = get_neraca(["Kas dan setara kas"])
    aset_cur, aset_pri = get_neraca(["Jumlah aset", "Total aset"])
    liab_cur, liab_pri = get_neraca(["Jumlah liabilitas", "Total liabilitas"])
    ekui_cur, ekui_pri = get_neraca(["Jumlah ekuitas", "Total ekuitas"])

    raw_metrics = {
        "Kas_CurrentYear": kas_cur,
        "Kas_PriorYear": kas_pri,
        "TotalAset_CurrentYear": aset_cur,
        "TotalAset_PriorYear": aset_pri,
        "TotalLiabilitas_CurrentYear": liab_cur,
        "TotalLiabilitas_PriorYear": liab_pri,
        "TotalEkuitas_CurrentYear": ekui_cur,
        "TotalEkuitas_PriorYear": ekui_pri,
    }

    # Sesuai aturan step3: hanya lolos jika 8 metrik utama terisi lengkap
    if any(raw_metrics[k] is None for k in METRIC_KEYS):
        return None

    normalized_metrics = {k: v * pengali for k, v in raw_metrics.items()}

    return {
        "KodeEmiten": kode,
        "Nama_Entitas": get_umum("Nama entitas"),
        "Sektor": get_umum("Sektor"),
        "Subsektor": get_umum("Subsektor"),
        "Industri": get_umum("Industri"),
        "Subindustri": get_umum("Subindustri"),
        "Tanggal_Laporan": get_umum("Tanggal akhir periode berjalan"),
        "Tahun": tahun,
        "Periode": kuartal,
        "Mata_Uang": get_umum("Mata uang pelaporan"),
        **normalized_metrics,
        "Link_Sumber": url_excel,
    }


def scrape_idx_financials(
    year: int = 2026,
    periode: str = "TW1",
    existing_emiten: set[str] | None = None,
    limit: int | None = None,
    batch_size: int = 25,
    on_batch: Callable[[list[dict]], None] | None = None,
) -> list[dict]:
    """
    Menarik, mengekstrak, dan menormalisasi laporan keuangan IDX secara in-memory.
    Melewati emiten yang sudah ada di Neon DB dan mendukung batch callback ke DB.
    """
    existing_emiten = existing_emiten or set()
    all_links = fetch_financial_report_links(year=year, periode=periode)
    pending = [row for row in all_links if row["KodeEmiten"] not in existing_emiten]

    print(
        f"[*] Target pending: {len(pending)} emiten "
        f"({len(all_links) - len(pending)} dilewati karena sudah ada di DB)."
    )
    if limit is not None:
        pending = pending[:limit]
        print(f"[*] Mode dibatasi: memproses maksimal {len(pending)} emiten.")

    all_records: list[dict] = []
    batch_buffer: list[dict] = []

    for idx, row in enumerate(pending, start=1):
        kode = row["KodeEmiten"]
        url_excel = row["Excel_Link"]
        print(f"[{idx}/{len(pending)}] Memproses {kode}...")

        content = None
        for attempt in range(1, 4):
            try:
                time.sleep(random.uniform(4.0, 7.5))
                resp = requests.get(
                    url_excel,
                    headers=EXCEL_HEADERS,
                    impersonate="chrome124",
                    timeout=45,
                )
                if resp.status_code == 200 and b"PK" in resp.content[:4]:
                    content = resp.content
                    break
                if resp.status_code == 403:
                    print(f"    [WARN] {kode} 403 Cloudflare, retry {attempt}/3...")
                    time.sleep(random.uniform(10.0, 15.0))
                else:
                    print(f"    [WARN] {kode} HTTP {resp.status_code}, retry {attempt}/3...")
            except Exception as e:
                print(f"    [WARN] {kode} gagal koneksi: {e}")

        if not content:
            print(f"    [SKIP] {kode} gagal diunduh.")
            continue

        try:
            parsed = parse_and_normalize_excel(
                content=content,
                kode=kode,
                tahun=row["Tahun"],
                kuartal=row["Periode"],
                url_excel=url_excel,
            )
            if parsed is None:
                print(f"    [SKIP] {kode} sheet/metrik tidak lengkap.")
                continue

            all_records.append(parsed)
            batch_buffer.append(parsed)
            print(f"    [OK] {kode} ({parsed['Mata_Uang']}) bersih & ternormalisasi.")

            if on_batch and len(batch_buffer) >= batch_size:
                on_batch(batch_buffer)
                batch_buffer = []
        except Exception as e:
            print(f"    [ERROR] {kode} gagal parsing Excel: {e}")

    if on_batch and batch_buffer:
        on_batch(batch_buffer)

    return all_records


if __name__ == "__main__":
    sample = scrape_idx_financials(year=2026, periode="TW1", limit=2)
    print(f"\nRingkasan tes -> berhasil ekstrak {len(sample)} emiten.")