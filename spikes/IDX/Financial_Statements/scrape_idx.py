from curl_cffi import requests
import pandas as pd

def scrape_idx_financials():
    print("Mengeksekusi ekstraksi Financial Statements IDX...\n")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.idx.co.id/"
    }
    
    session = requests.Session(impersonate="chrome120")
    url_fin = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"
    
    # PARAMETER FINAL DENGAN REPORT TYPE
    params_fin = {
        "kodeEmiten": "BBCA",
        "year": 2023,
        "reportType": 0,       # 0 biasanya kode untuk Laporan Keuangan Tahunan
        "periode": "Audit",    # Coba "Audit", jika kosong bisa diganti "tw4"
        "indexFrom": 1,
        "pageSize": 10
    }
    
    try:
        resp_fin = session.get(url_fin, headers=headers, params=params_fin, timeout=20)
        
        if resp_fin.status_code == 200:
            data_fin = resp_fin.json()
            
            # Mengambil data dari key 'Results'
            if 'Results' in data_fin and len(data_fin['Results']) > 0:
                df_fin = pd.DataFrame(data_fin['Results'])
                print("✅ [BINGO!] Berhasil menembus Cloudflare dan mengekstrak Data Laporan Keuangan!")
                
                # Tampilkan beberapa kolom saja agar rapi
                kolom_penting = ['KodeEmiten', 'Year', 'Periode', 'Report_Type']
                kolom_ada = [col for col in kolom_penting if col in df_fin.columns]
                
                if kolom_ada:
                    print(df_fin[kolom_ada].head(3))
                else:
                    print(df_fin.head(3)) # Tampilkan apa adanya jika nama kolom berbeda
                
                output_csv = 'raw_data/hasil_idx_statements_raw.csv'
                df_fin.to_csv(output_csv, index=False)
                print(f"\n📂 File terstruktur disimpan ke: {output_csv}")
            else:
                print("⚠️ API sukses, tapi 'Results' kosong.")
        else:
            print(f"❌ Gagal (HTTP {resp_fin.status_code})")
            
    except Exception as e:
        print(f"❌ Error Sistem: {e}")

if __name__ == "__main__":
    scrape_idx_financials()