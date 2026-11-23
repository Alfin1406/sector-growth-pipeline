import random
import time
from datetime import datetime, timedelta

from curl_cffi import requests

IDX_CORP_ACTION_URL = "https://www.idx.co.id/primary/ListingActivity/GetIssuedHistory"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Connection": "keep-alive",
    "Origin": "https://www.idx.co.id",
    "Referer": "https://www.idx.co.id/en/listed-companies/corporate-actions/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def scrape_idx_corp_actions(days_back: int = 90, max_retries: int = 3) -> list[dict]:
    """Menarik data Corporate Actions dari API IDX secara in-memory."""
    today = datetime.now()
    start_date = today - timedelta(days=days_back)

    params = {
        "caType": "",
        "dateFrom": start_date.strftime("%Y%m%d"),
        "dateTo": today.strftime("%Y%m%d"),
        "start": 0,
        "length": 9999,
        "language": "en-us",
    }

    print(
        f"[*] Menarik IDX Corporate Actions ({start_date.strftime('%Y-%m-%d')} "
        f"s.d. {today.strftime('%Y-%m-%d')})..."
    )

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                IDX_CORP_ACTION_URL,
                params=params,
                headers=HEADERS,
                impersonate="chrome124",
                timeout=30,
            )
            if resp.status_code == 200:
                payload = resp.json()
                rows = payload.get("data", [])
                print(f"[*] Berhasil menarik {len(rows)} baris Corporate Actions dari API IDX.")
                return rows

            print(
                f"    [WARN] HTTP {resp.status_code} (percobaan {attempt}/{max_retries}): "
                f"{resp.text[:100]}"
            )
        except Exception as e:
            print(f"    [WARN] Gagal koneksi (percobaan {attempt}/{max_retries}): {e}")

        if attempt < max_retries:
            time.sleep(random.uniform(5.0, 10.0))

    raise RuntimeError(f"Gagal menarik IDX Corporate Actions setelah {max_retries} percobaan.")


if __name__ == "__main__":
    data = scrape_idx_corp_actions(days_back=90)
    print(f"Ringkasan tes -> {len(data)} data ditarik.")