from curl_cffi import requests
import pandas as pd

def get_financial_report_links():
    print("Tahap 1: Mengekstrak Tautan Excel Laporan Keuangan dari API IDX...")
    
    url_api = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"
    
    # Parameter untuk Tahun 2026, Q1 (TW1)
    params = {
        "periode": "TW1",         # TW1 = Q1, TW2 = Q2, TW3 = Q3, audit = Tahunan
        "year": "2026",
        "indexFrom": 1,
        "pageSize": 2000,         # Kapasitas maksimal agar menampung seluruh ~1000 emiten
        "reportType": "rdf",
        "kodeEmiten": ""          # Dibiarkan kosong agar API memuntahkan semua perusahaan
    }
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Connection": "keep-alive",
        "Origin": "https://www.idx.co.id",
        "Referer": "https://www.idx.co.id/en/listed-companies/financial-statements-and-annual-report/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Menggunakan curl_cffi untuk menghancurkan tameng Cloudflare
        response = requests.get(url_api, params=params, headers=headers, impersonate="chrome120", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            excel_links = []
            
            # Data array utama IDX biasanya disimpan di dalam key "Results"
            results = data.get("Results", data.get("data", []))
            
            for item in results:
                kode = item.get("KodeEmiten", "UNKNOWN")
                attachments = item.get("Attachments", [])
                
                # Membedah array lampiran untuk setiap emiten
                for att in attachments:
                    file_path = att.get("File_Path", "")
                    
                    # Logika filter: Abaikan PDF/ZIP, ambil hanya Excel (.xlsx)
                    if file_path.lower().endswith(".xlsx"):
                        
                        # Pembersihan Path: Database IDX sering menggunakan backslash (\)
                        clean_path = file_path.replace("\\", "/")
                        
                        if not clean_path.startswith("/"):
                            clean_path = "/" + clean_path
                        
                        full_url = f"https://www.idx.co.id{clean_path}"
                        
                        excel_links.append({
                            "KodeEmiten": kode,
                            "Tahun": 2026,
                            "Periode": "Q1",
                            "Excel_Link": full_url
                        })
            
            df = pd.DataFrame(excel_links)
            
            if not df.empty:
                output_file = 'raw_data/idx_financial_links_2026_q1.csv'
                df.to_csv(output_file, index=False, sep=';')
                print(f"✅ BINGO! Berhasil menemukan {len(df)} link Excel Laporan Keuangan!")
                print(f"Data tersimpan di: {output_file}")
            else:
                print("⚠️ API tembus (Status 200), tapi tidak ada satupun link .xlsx yang ditemukan.")
                print(f"Contoh struktur JSON mentah untuk inspeksi: {results[:1] if results else 'Kosong'}")
                
        else:
            print(f"❌ Error HTTP: {response.status_code} - {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ Gagal mengeksekusi request: {e}")

if __name__ == "__main__":
    get_financial_report_links()