import pandas as pd
from curl_cffi import requests
import io
import time
import random
import os

def extract_financial_data():
    print("Tahap 2: Mengekstrak Seluruh Laporan Keuangan IDX (Production Mode v2)...")
    
    file_links = 'raw_data/idx_financial_links_2026_q1.csv'
    try:
        df_links = pd.read_csv(file_links, sep=';')
    except Exception as e:
        print(f"❌ Gagal membaca file: {e}")
        return

    df_sample = df_links 
    
    # FITUR RESUME: Membaca memori CSV yang sudah ada (Menggunakan nama file v2)
    file_hasil = 'raw_data/hasil_insight_financial_final_v2.csv'
    if os.path.exists(file_hasil):
        df_existing = pd.read_csv(file_hasil, sep=';')
        hasil_akhir = df_existing.to_dict('records')
        emiten_sukses = set(df_existing['KodeEmiten'].tolist())
        print(f"🔄 Resume Mode: Melanjutkan dari {len(emiten_sukses)} emiten yang sudah diamankan...")
    else:
        emiten_sukses = set()
        hasil_akhir = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.idx.co.id/",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/octet-stream, */*"
    }
    
    total_emiten = len(df_sample['KodeEmiten'].unique())
    print(f"Total target unik: ~{total_emiten} Emiten. Estimasi waktu: 1 - 1.5 Jam.\n")

    for index, row in df_sample.iterrows():
        kode = row['KodeEmiten']
        url_excel = row['Excel_Link']
        
        if kode in emiten_sukses:
            continue
            
        print(f"[{len(emiten_sukses)+1}] Memproses {kode}: {url_excel[:45]}...")
        
        max_retries = 3
        success_download = False
        
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(4.0, 7.5))
                response = requests.get(url_excel, headers=headers, impersonate="chrome120", timeout=45)
                
                if response.status_code == 200:
                    success_download = True
                    break
                elif response.status_code == 403:
                    print(f"    ⚠️ Terblokir (403). Istirahat sebentar, lalu mencoba ulang {attempt+1}/{max_retries}...")
                    time.sleep(random.uniform(10.0, 15.0)) 
            except Exception as e:
                print(f"    ⚠️ Gagal koneksi: {e}")
        
        if not success_download:
            print(f"  ❌ {kode}: Gagal diunduh setelah {max_retries} percobaan.")
            continue

        try:
            xls = pd.ExcelFile(io.BytesIO(response.content), engine='openpyxl')
            
            if '1000000' in xls.sheet_names and '1210000' in xls.sheet_names:
                df_umum = pd.read_excel(xls, sheet_name='1000000', header=None)
                df_neraca = pd.read_excel(xls, sheet_name='1210000', header=None)
                
                # --- EKSTRAKSI SHEET 1000000 (Informasi Umum) ---
                nama_entitas_row = df_umum[df_umum[0] == 'Nama entitas']
                nama_entitas = nama_entitas_row.iloc[0, 1] if not nama_entitas_row.empty else None
                
                mata_uang_row = df_umum[df_umum[0] == 'Mata uang pelaporan']
                mata_uang = mata_uang_row.iloc[0, 1] if not mata_uang_row.empty else None
                
                sektor_row = df_umum[df_umum[0] == 'Sektor']
                sektor = sektor_row.iloc[0, 1] if not sektor_row.empty else None
                
                # HIERARKI INDUSTRI BARU
                subsektor_row = df_umum[df_umum[0] == 'Subsektor']
                subsektor = subsektor_row.iloc[0, 1] if not subsektor_row.empty else None
                
                industri_row = df_umum[df_umum[0] == 'Industri']
                industri = industri_row.iloc[0, 1] if not industri_row.empty else None
                
                subindustri_row = df_umum[df_umum[0] == 'Subindustri']
                subindustri = subindustri_row.iloc[0, 1] if not subindustri_row.empty else None
                
                # TANGGAL BARU
                tanggal_row = df_umum[df_umum[0] == 'Tanggal akhir periode berjalan']
                tanggal = tanggal_row.iloc[0, 1] if not tanggal_row.empty else None
                
                pembulatan_row = df_umum[df_umum[0].str.contains('pembulatan|rounding', na=False, case=False)]
                pembulatan = pembulatan_row.iloc[0, 1] if not pembulatan_row.empty else None
                
                # --- EKSTRAKSI SHEET 1210000 (Neraca) ---
                kas_row = df_neraca[df_neraca[0] == 'Kas dan setara kas']
                kas_current = kas_row.iloc[0, 1] if not kas_row.empty else None
                kas_prior = kas_row.iloc[0, 2] if not kas_row.empty else None
                
                # EXACT MATCH PERBAIKAN ASET
                aset_row = df_neraca[df_neraca[0].isin(['Jumlah aset', 'Total aset'])]
                aset_current = aset_row.iloc[0, 1] if not aset_row.empty else None
                aset_prior = aset_row.iloc[0, 2] if not aset_row.empty else None
                
                # EXACT MATCH BARU: LIABILITAS & EKUITAS
                liabilitas_row = df_neraca[df_neraca[0].isin(['Jumlah liabilitas', 'Total liabilitas'])]
                liabilitas_current = liabilitas_row.iloc[0, 1] if not liabilitas_row.empty else None
                liabilitas_prior = liabilitas_row.iloc[0, 2] if not liabilitas_row.empty else None
                
                ekuitas_row = df_neraca[df_neraca[0].isin(['Jumlah ekuitas', 'Total ekuitas'])]
                ekuitas_current = ekuitas_row.iloc[0, 1] if not ekuitas_row.empty else None
                ekuitas_prior = ekuitas_row.iloc[0, 2] if not ekuitas_row.empty else None
                
                hasil_akhir.append({
                    "KodeEmiten": kode,
                    "Nama_Entitas": nama_entitas,
                    "Sektor": sektor,
                    "Subsektor": subsektor,
                    "Industri": industri,
                    "Subindustri": subindustri,
                    "Tanggal_Laporan": tanggal,
                    "Tahun": row['Tahun'],
                    "Periode": row['Periode'],
                    "Mata_Uang": mata_uang,
                    "Tingkat_Pembulatan": pembulatan,
                    "Kas_CurrentYear": kas_current,
                    "Kas_PriorYear": kas_prior,
                    "TotalAset_CurrentYear": aset_current,
                    "TotalAset_PriorYear": aset_prior,
                    "TotalLiabilitas_CurrentYear": liabilitas_current,
                    "TotalLiabilitas_PriorYear": liabilitas_prior,
                    "TotalEkuitas_CurrentYear": ekuitas_current,
                    "TotalEkuitas_PriorYear": ekuitas_prior,
                    "Link_Sumber": url_excel
                })
                emiten_sukses.add(kode)
                print(f"  ✅ [SUKSES] Data {kode} berhasil diamankan.")
                
            else:
                print(f"  ⚠️ {kode}: Excel tidak standar / Sheet tidak lengkap.")

        except Exception as e:
            print(f"  ❌ {kode} Error saat parsing Excel: {e}")
            
        if len(emiten_sukses) % 50 == 0 and len(hasil_akhir) > 0:
            pd.DataFrame(hasil_akhir).to_csv(file_hasil, index=False, sep=';')
            print(f"  💾 [CHECKPOINT] Data sementara disimpan ({len(emiten_sukses)} emiten).")
            
    if hasil_akhir:
        df_hasil = pd.DataFrame(hasil_akhir)
        df_hasil.to_csv(file_hasil, index=False, sep=';')
        print(f"\n🎉 MISI SELESAI! Total {len(hasil_akhir)} emiten berhasil diproses.")
        print(f"File akhir tersimpan di: {file_hasil}")
    else:
        print("\n⚠️ Tidak ada data yang berhasil diekstrak.")

if __name__ == "__main__":
    extract_financial_data()