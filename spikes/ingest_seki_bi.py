import pandas as pd
import numpy as np
import warnings

# Membisukan warning Pandas agar terminal tetap bersih
warnings.filterwarnings("ignore")

def proses_sheet_bi(filepath, sheet_name):
    print(f"Mengekstrak sheet: {sheet_name}...")
    
    # 1. Baca data kasar, lewati 3 baris pertama
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None, skiprows=3)
    
    # 2. PERBAIKAN FINAL: Deteksi Tahun Berdasarkan Munculnya Bulan "Jan"
    row_year_raw = pd.to_numeric(df_raw.iloc[0], errors='coerce').dropna().tolist() 
    baris_bulan = df_raw.iloc[1].tolist()
    
    header_baru = []
    year_idx = -1  # Indeks pelacak tahun
    
    for b in baris_bulan:
        if pd.notna(b):
            b_str = str(b).strip()
            # Setiap kali ketemu "Jan", maju ke tahun berikutnya
            if b_str == 'Jan':
                year_idx += 1
            
            # Pasangkan tahun dengan bulannya (Contoh: 2025_Mar)
            if year_idx >= 0 and year_idx < len(row_year_raw):
                current_year = int(row_year_raw[year_idx])
                if b_str not in ['NaN', 'GROUP OF BANKS AND ECONOMIC SECTOR', 'Dec']:
                    header_baru.append(f"{current_year}_{b_str}")
                else:
                    header_baru.append("Kolom_Abaikan")
            else:
                header_baru.append("Kolom_Abaikan")
        else:
            header_baru.append("Kolom_Abaikan")
    
    # 3. Potong DataFrame (Mulai dari baris ke-2)
    df_data = df_raw.iloc[2:].copy()
    
    # Penyesuaian jumlah kolom (Ada kolom NaN tersembunyi di Excel BI)
    df_data.columns = ['Nomor', 'Kolom_NaN', 'Uraian'] + header_baru[3:] 
    
    # Buang kolom yang tidak perlu
    kolom_valid = ['Uraian'] + [col for col in df_data.columns if "_" in col]
    df_data = df_data[kolom_valid]
    
    # 4. Paksa kolom Uraian menjadi String sebelum memanggil .str
    df_data['Uraian'] = df_data['Uraian'].astype(str).str.strip()
    df_data = df_data[(df_data['Uraian'] != 'nan') & (df_data['Uraian'] != 'None')]
    
    # 5. Pembersihan Data & Propagasi Kelompok Bank
    df_data['Kelompok_Bank'] = np.where(df_data['Uraian'].str.match(r'^\d+\.\sBank'), df_data['Uraian'], np.nan)
    df_data['Kelompok_Bank'] = df_data['Kelompok_Bank'].ffill() 
    
    df_data['Kategori_Pinjaman'] = np.where(df_data['Uraian'].str.contains('Pinjaman Berdasarkan|Pinjaman Kepada|Jumlah'), df_data['Uraian'], np.nan)
    df_data['Kategori_Pinjaman'] = df_data['Kategori_Pinjaman'].ffill()
    
    df_data['Sektor_KBLI'] = np.where(~df_data['Uraian'].isin(df_data['Kelompok_Bank']) & 
                                      ~df_data['Uraian'].isin(df_data['Kategori_Pinjaman']), 
                                      df_data['Uraian'], np.nan)
    
    df_data = df_data.dropna(subset=['Sektor_KBLI']) 
    
    # 6. UNPIVOT / MELT (Mengubah kolom bulan menjadi baris)
    kolom_id = ['Kelompok_Bank', 'Kategori_Pinjaman', 'Sektor_KBLI']
    kolom_value = [col for col in df_data.columns if "_" in col]
    
    df_melt = pd.melt(df_data, id_vars=kolom_id, value_vars=kolom_value, 
                      var_name='Periode_Raw', value_name='Nilai_Kredit_Miliar_Rp')
    
    # Pecah Periode_Raw ("2025_Jan") menjadi Tahun dan Bulan
    df_melt[['Tahun', 'Bulan']] = df_melt['Periode_Raw'].str.split('_', expand=True)
    df_melt['Sheet_Asal'] = sheet_name
    
    df_final = df_melt[['Sheet_Asal', 'Tahun', 'Bulan', 'Kelompok_Bank', 'Kategori_Pinjaman', 'Sektor_KBLI', 'Nilai_Kredit_Miliar_Rp']]
    
    df_final['Nilai_Kredit_Miliar_Rp'] = pd.to_numeric(df_final['Nilai_Kredit_Miliar_Rp'], errors='coerce')
    df_final = df_final.dropna(subset=['Nilai_Kredit_Miliar_Rp'])
    
    return df_final

if __name__ == "__main__":
    filepath = 'raw_data/TABEL1_4.xls'
    sheet_targets = ['I.4_1', 'I.4_2', 'I.4_3']
    
    all_data = []
    for sheet in sheet_targets:
        try:
            df_sheet = proses_sheet_bi(filepath, sheet)
            all_data.append(df_sheet)
            print(f"✅ {sheet} berhasil diproses ({len(df_sheet)} baris).")
        except Exception as e:
            print(f"❌ Gagal memproses {sheet}: {e}")
            
    if all_data:
        df_master = pd.concat(all_data, ignore_index=True)
        output_path = 'raw_data/hasil_seki_bi_raw_master.csv'
        df_master.to_csv(output_path, index=False)
        print(f"\n📂 SUPERB! Seluruh data sukses diekstrak ({len(df_master)} baris) ke: {output_path}")