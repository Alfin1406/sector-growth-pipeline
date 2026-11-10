from curl_cffi import requests

def inspeksi_api_idx():
    print("Melakukan inspeksi parameter & struktur JSON API IDX...\n")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.idx.co.id/"
    }
    session = requests.Session(impersonate="chrome120")
    
    # ========================================================
    # 1. Inspeksi Laporan Keuangan (Kita pakai Emiten BBCA agar pasti ada isi)
    # ========================================================
    print("[1] Test Financial Statements (Emiten: BBCA, 2023)...")
    url_fin = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"
    
    # Mencoba kombinasi parameter yang umum dipakai IDX
    params_fin = {"emitent": "BBCA", "year": 2023, "periode": "Audit"} 
    
    resp_fin = session.get(url_fin, headers=headers, params=params_fin)
    print(f"Status HTTP: {resp_fin.status_code}")
    if resp_fin.status_code == 200:
        print("Response JSON (Bocoran Struktur):")
        print(resp_fin.text[:400]) # Tampilkan 400 karakter pertama agar terminal tidak penuh
    
    print("\n" + "-" * 60 + "\n")
    
    # ========================================================
    # 2. Inspeksi Corporate Actions (Mencari URL yang benar)
    # ========================================================
    print("[2] Test Corporate Actions (Mencari Endpoint yang Tepat)...")
    # Daftar kemungkinan URL di server IDX
    url_variations = [
        "https://www.idx.co.id/primary/CorporateAction/GetDividend",
        "https://www.idx.co.id/primary/ListedCompany/GetCorporateAction",
        "https://www.idx.co.id/primary/ListedCompany/GetDividendInfo",
        "https://www.idx.co.id/primary/CorporateAction/GetDividenInfo" # URL salah kita yang lama
    ]
    
    for url in url_variations:
        print(f"Mencoba path URL: {url.split('/primary/')[1]}...")
        # Kita tembak menggunakan BBCA 
        resp_corp = session.get(url, headers=headers, params={"emitent": "BBCA", "year": 2024})
        
        print(f"  -> Status: {resp_corp.status_code}")
        if resp_corp.status_code == 200:
            print("  -> 🔥 BINGO! URL Ini Benar. Response:")
            print("  ->", resp_corp.text[:300])
            break # Berhenti jika sudah nemu 1 URL yang 200 OK

if __name__ == "__main__":
    inspeksi_api_idx()