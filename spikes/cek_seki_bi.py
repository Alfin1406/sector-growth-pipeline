import pandas as pd
import warnings

# Mengabaikan warning format file Excel lama (BI sering pakai format lama)
warnings.simplefilter(action='ignore', category=UserWarning)

def parse_bi_seki(file_path):
    print(f"Mencoba membaca {file_path}...")
    
    # 1. BACA EXCEL & POTONG HEADER
    # skiprows=9 karena data Sektor Ekonomi biasanya mulai di baris ke-11
    # sheet_name='I.4_1' sesuai dengan struktur Excel BI
    df = pd.read_excel(file_path, sheet_name='I.4_1', skiprows=9)
    
    # 2. AMBIL KOLOM YANG DIBUTUHKAN SAJA
    # Ambil kolom Nama Sektor (indeks 2) dan data bulan-bulan (mulai indeks 4)
    kolom_penting = [2] + list(range(4, len(df.columns) - 2)) 
    df_clean = df.iloc[:, kolom_penting]
    
    # 3. FILTER BARIS (HANYA SEKTOR UTAMA KBLI)
    # Potong DataFrame agar hanya mengambil baris ke-1 sampai ke-9
    df_sectors = df_clean.iloc[1:10].copy()
    
    # Ganti nama kolom pertama agar rapi
    df_sectors.rename(columns={df_sectors.columns[0]: 'sektor_kbli'}, inplace=True)
    
    # 4. MELT / UNPIVOT
    # Ubah tabel menyamping jadi menurun agar siap masuk database
    df_final = df_sectors.melt(id_vars=['sektor_kbli'], var_name='bulan', value_name='kredit_miliar_rp')
    
    # Bersihkan nama sektor (hapus spasi berlebih)
    df_final['sektor_kbli'] = df_final['sektor_kbli'].str.strip()
    
    return df_final

if __name__ == "__main__":
    # Jalankan simulasi ekstraksi
    hasil_df = parse_bi_seki('raw_data/TABEL1_4.xls')
    print("\nEkstraksi Berhasil! Ini 5 baris pertama hasilnya:")
    print(hasil_df.head())
    print(f"\nTotal baris data yang diekstrak: {len(hasil_df)}")