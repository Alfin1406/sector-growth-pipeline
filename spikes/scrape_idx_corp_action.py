from curl_cffi import requests
import pandas as pd
from datetime import datetime, timedelta

def scrape_corporate_action():
    print("Mengekstrak Corporate Actions dari API Asli IDX (ListingActivity)...")
    
    # URL 100% Akurat dari hasil inspeksi Alfin
    url_api = "https://www.idx.co.id/primary/ListingActivity/GetIssuedHistory"
    
    # Rentang waktu: 90 hari ke belakang dari hari ini
    today = datetime.now()
    start_date = today - timedelta(days=90)
    
    # Parameter persis seperti yang disadap dari browser
    params = {
        "caType": "",                               # Kosong = ambil semua jenis aksi
        "dateFrom": start_date.strftime("%Y%m%d"),  
        "dateTo": today.strftime("%Y%m%d"),
        "start": 0,
        "length": 9999,                             # IDX menggunakan 9999 untuk mengambil semua data
        "language": "en-us"                         # Parameter wajib dari IDX
    }
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Connection": "keep-alive",
        "Origin": "https://www.idx.co.id",
        "Referer": "https://www.idx.co.id/en/listed-companies/corporate-actions/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Menembak langsung ke API dengan penyamaran tingkat tinggi
        response = requests.get(url_api, params=params, headers=headers, impersonate="chrome120", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if "data" in data and len(data["data"]) > 0:
                df = pd.DataFrame(data["data"])
                
                output_file = 'raw_data/hasil_idx_corporate_actions.csv'
                # Simpan dengan titik koma (;) agar bersahabat dengan Excel
                df.to_csv(output_file, index=False, sep=';')
                
                print(f"✅ BINGO! Cloudflare hancur! {len(df)} data Corporate Action sukses ditarik ke {output_file}")
            else:
                print("⚠️ API tembus (Status 200), tapi tabel kosong di rentang waktu ini.")
        else:
            print(f"❌ Error HTTP: {response.status_code} - Tanggapan Server: {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ Gagal mengeksekusi request: {e}")

if __name__ == "__main__":
    scrape_corporate_action()