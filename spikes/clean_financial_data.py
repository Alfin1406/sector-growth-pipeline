import pandas as pd
import numpy as np

def clean_and_normalize():
    print("Memulai proses pembersihan dan normalisasi data v2...")
    
    # 1. Baca data mentah v2
    file_input = 'raw_data/hasil_insight_financial_final_v2.csv'
    try:
        df = pd.read_csv(file_input, sep=';')
    except Exception as e:
        print(f"❌ Gagal membaca file {file_input}: {e}")
        return
        
    awal_baris = len(df)
    
    # 2. Hapus emiten yang datanya kosong (Null/NaN) di semua kolom metrik
    kolom_angka = [
        'Kas_CurrentYear', 'Kas_PriorYear', 
        'TotalAset_CurrentYear', 'TotalAset_PriorYear',
        'TotalLiabilitas_CurrentYear', 'TotalLiabilitas_PriorYear',
        'TotalEkuitas_CurrentYear', 'TotalEkuitas_PriorYear'
    ]
    df = df.dropna(subset=kolom_angka)
    print(f"✔️ Dihapus {awal_baris - len(df)} baris yang memiliki nilai metrik kosong.")
    
    # 3. Normalisasi Skala Angka berdasarkan Tingkat Pembulatan
    multiplier = {
        'Satuan Penuh / Full Amount': 1,
        'Ribuan / In Thousand': 1_000,
        'Jutaan / In Million': 1_000_000,
        'Miliaran / In Billion': 1_000_000_000
    }
    
    for idx, row in df.iterrows():
        pengali = multiplier.get(row['Tingkat_Pembulatan'], 1) 
        
        # Kalikan HANYA jika nilainya tidak null/kosong
        for col in kolom_angka:
            if pd.notnull(row[col]):
                df.at[idx, col] = row[col] * pengali
                
    print("✔️ Skala pembulatan berhasil dinormalisasi ke Satuan Penuh.")
    
    # 4. Hapus kolom Tingkat_Pembulatan karena semua sudah menjadi Satuan Penuh
    df = df.drop(columns=['Tingkat_Pembulatan'])
    
    # 5. Simpan sebagai file siap pakai (Production Ready)
    output_file = 'raw_data/financial_data_clean_ready_v2.csv'
    df.to_csv(output_file, index=False, sep=';')
    print(f"🎉 Selesai! {len(df)} data bersih dan terseragamkan disimpan di: {output_file}")

if __name__ == "__main__":
    clean_and_normalize()