import pandas as pd
import numpy as np

def clean_and_normalize():
    print("Memulai proses pembersihan dan normalisasi data...")
    
    # 1. Baca data mentah
    df = pd.read_csv('raw_data/hasil_insight_financial_final.csv', sep=';')
    awal_baris = len(df)
    
    # 2. Hapus emiten yang datanya kosong (Null/NaN di kolom Kas atau Aset)
    df = df.dropna(subset=['Kas_CurrentYear', 'Kas_PriorYear', 'TotalAset_CurrentYear', 'TotalAset_PriorYear'])
    print(f"✔️ Dihapus {awal_baris - len(df)} baris yang memiliki nilai kosong.")
    
    # 3. Normalisasi Skala Angka berdasarkan Tingkat Pembulatan
    # Membuat kamus pengali
    multiplier = {
        'Satuan Penuh / Full Amount': 1,
        'Ribuan / In Thousand': 1_000,
        'Jutaan / In Million': 1_000_000,
        'Miliaran / In Billion': 1_000_000_000
    }
    
    # Terapkan pengali ke dalam kolom baru (atau timpa kolom lama)
    kolom_angka = ['Kas_CurrentYear', 'Kas_PriorYear', 'TotalAset_CurrentYear', 'TotalAset_PriorYear']
    
    for idx, row in df.iterrows():
        pengali = multiplier.get(row['Tingkat_Pembulatan'], 1) # Default x1 jika tidak dikenali
        
        for col in kolom_angka:
            df.at[idx, col] = row[col] * pengali
            
    print("✔️ Skala pembulatan berhasil dinormalisasi ke Satuan Penuh.")
    
    # 4. Hapus kolom Tingkat_Pembulatan karena semua sudah menjadi Satuan Penuh
    df = df.drop(columns=['Tingkat_Pembulatan'])
    
    # 5. Simpan sebagai file siap pakai (Production Ready)
    output_file = 'raw_data/financial_data_clean_ready.csv'
    df.to_csv(output_file, index=False, sep=';')
    print(f"🎉 Selesai! {len(df)} data bersih dan terseragamkan disimpan di: {output_file}")

if __name__ == "__main__":
    clean_and_normalize()