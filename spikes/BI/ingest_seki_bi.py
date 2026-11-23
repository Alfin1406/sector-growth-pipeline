import requests
import zipfile
import io
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings

# Matikan warning Pandas
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
warnings.filterwarnings("ignore", message="The xlrd engine is deprecated")
warnings.filterwarnings("ignore", category=FutureWarning)

# 1. SETUP FOLDER LOKAL (Kunci Path di dalam Root)
PROJECT_ROOT = os.getcwd() 
RAW_DIR = os.path.join(PROJECT_ROOT, "raw_data", "BI (SEKI)")
os.makedirs(RAW_DIR, exist_ok=True)

bulan_indo = {
    1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL", 
    5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS", 
    9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER"
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
print("[*] Memulai Ingest End-to-End Data SEKI BI...")

current_date = datetime.now()
target_xls_bytes = None
bulan_rilis, tahun_rilis = "", 0

# 2. LOOPING DOWNLOAD ZIP OTOMATIS
for i in range(4):
    target_bulan = current_date.month - i
    target_tahun = current_date.year
    if target_bulan <= 0:
        target_bulan += 12
        target_tahun -= 1
        
    nama_bulan = bulan_indo[target_bulan]
    url_bi = f"https://www.bi.go.id/id/statistik/ekonomi-keuangan/seki/Documents/SEKI_{nama_bulan}_{target_tahun}.zip"
    
    print(f"[*] Mengecek: SEKI {nama_bulan} {target_tahun}...")
    response = requests.get(url_bi, headers=headers)
    
    if response.status_code == 200:
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                for nama_file in zip_ref.namelist():
                    if "TABEL1_4" in nama_file.upper() and nama_file.endswith(('.xls', '.xlsx')):
                        print(f"[*] Ketemu file Excel: {nama_file}")
                        target_xls_bytes = zip_ref.read(nama_file)
                        bulan_rilis = nama_bulan.capitalize()
                        tahun_rilis = target_tahun
                        break
            if target_xls_bytes: break
        except zipfile.BadZipFile:
            print(f"[-] Belum rilis (Server merespons 200, tapi bukan ZIP). Mundur...")
    else:
        print(f"[-] Belum rilis (Status {response.status_code}). Mundur...")

# 3. PROSES CLEANSING TINGKAT TINGGI DENGAN FORWARD FILL
if target_xls_bytes:
    print("\n[*] Memulai proses Cleansing & Unpivot data Excel...")
    excel_file = pd.ExcelFile(io.BytesIO(target_xls_bytes))
    list_df_clean = []
    
    for sheet_name in ['I.4_1', 'I.4_2', 'I.4_3']:
        if sheet_name in excel_file.sheet_names:
            # Baca file mulai baris ke-5 agar header bulan terbaca lurus
            df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=4)
            
            # Kolom deskripsi (Nama Bank, Pinjaman, Sektor) ada di kolom 'Unnamed: 2'
            if 'Unnamed: 2' not in df.columns: continue
            df = df.rename(columns={'Unnamed: 2': 'Deskripsi'})
            df = df.dropna(subset=['Deskripsi'])
            
            # --- LOGIKA KECERDASAN BUATAN UNTUK MEMBACA BARIS EXCEL ---
            # Menggunakan None agar tipe datanya ter-set sebagai Object (bisa menampung teks)
            df['Kelompok_Bank'] = None
            df['Kategori_Pinjaman'] = None
            
            def klasifikasi_baris(val):
                teks = str(val).strip()
                if teks.startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                    return 'BANK'
                elif teks.startswith('Pinjaman'):
                    return 'KATEGORI'
                else:
                    return 'SEKTOR'
                    
            tipe_baris = df['Deskripsi'].apply(klasifikasi_baris)
            
            # Pindahkan data ke kolom yang sesuai
            df.loc[tipe_baris == 'BANK', 'Kelompok_Bank'] = df['Deskripsi']
            df.loc[tipe_baris == 'KATEGORI', 'Kategori_Pinjaman'] = df['Deskripsi']
            
            # FORWARD FILL: Tarik nilai Bank dan Kategori ke bawah mengisi baris yang kosong
            df['Kelompok_Bank'] = df['Kelompok_Bank'].ffill()
            df['Kategori_Pinjaman'] = df['Kategori_Pinjaman'].ffill()
            
            # Sisakan HANYA baris yang merupakan rincian SEKTOR
            df = df[tipe_baris == 'SEKTOR']
            df = df.rename(columns={'Deskripsi': 'Sektor_KBLI'})
            
            # Filter hanya kolom bulan untuk proses unpivot
            bulan_valid = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            month_cols = [c for c in df.columns if str(c).split('.')[0] in bulan_valid]
            
            # UNPIVOT
            df_melted = df.melt(id_vars=['Sektor_KBLI', 'Kelompok_Bank', 'Kategori_Pinjaman'], 
                                value_vars=month_cols, var_name='Bulan_Tahun', value_name='Nilai_Kredit_Miliar_Rp')
            
            df_melted = df_melted.dropna(subset=['Nilai_Kredit_Miliar_Rp'])
            df_melted = df_melted[pd.to_numeric(df_melted['Nilai_Kredit_Miliar_Rp'], errors='coerce').notnull()]
            
            # Ekstrak Tahun dan Bulan ('Jan.1' berarti tahun berjalan, 'Jan' berarti tahun lalu)
            df_melted['Bulan'] = df_melted['Bulan_Tahun'].apply(lambda x: x.split('.')[0])
            df_melted['Tahun'] = df_melted['Bulan_Tahun'].apply(lambda x: str(tahun_rilis) if '.1' in str(x) else str(tahun_rilis - 1))
            
            df_melted['Sheet_Asal'] = sheet_name
            
            # Rapikan Kolom
            df_clean = df_melted[['Sheet_Asal', 'Tahun', 'Bulan', 'Kelompok_Bank', 'Kategori_Pinjaman', 'Sektor_KBLI', 'Nilai_Kredit_Miliar_Rp']]
            list_df_clean.append(df_clean)

    if list_df_clean:
        df_final = pd.concat(list_df_clean, ignore_index=True)
        
        # Simpan CSV persis di folder proyekmu
        nama_file_csv = f"hasil_seki_bi_{bulan_rilis}_{tahun_rilis}.csv"
        path_csv = os.path.join(RAW_DIR, nama_file_csv)
        df_final.to_csv(path_csv, index=False)
        
        print(f"\n[v] PIPELINE SUKSES! {len(df_final)} baris data master CSV berhasil dibuat di:")
        print(f"    {path_csv}")
    else:
        print("[!] Gagal melakukan pembersihan data Excel.")
else:
    print("[!] Pipeline terhenti karena file Excel tidak didapatkan.")