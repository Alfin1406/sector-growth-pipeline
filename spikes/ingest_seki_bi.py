import pandas as pd
import warnings
import os

# Abaikan warning format Excel lama
warnings.simplefilter(action='ignore', category=UserWarning)

def ingest_bi_seki(file_path):
    print(f"Membaca {file_path}...")
    df_raw = pd.read_excel(file_path, sheet_name='I.4_1', header=None, engine='calamine')
    
    tahun_row = df_raw.iloc[3, 3:].tolist()
    bulan_row = df_raw.iloc[4, 3:].tolist()
    tahun_list = pd.Series(tahun_row).ffill().tolist()
    
    data_bersih = []
    current_kelompok_bank = ""
    current_kategori = ""
    
    for idx, row in df_raw.iloc[5:55].iterrows():
        teks = str(row[2]).strip() if pd.notna(row[2]) else ""
        if not teks:
            continue
            
        if teks[0].isdigit() and ". " in teks[:3]:
            current_kelompok_bank = teks
            continue
        elif "Pinjaman Berdasarkan" in teks or "Pinjaman Kepada Bukan" in teks:
            current_kategori = teks
            continue
        else:
            sektor_kbli = teks
            for col_idx, (thn, bln) in enumerate(zip(tahun_list, bulan_row), start=3):
                if pd.isna(bln): 
                    continue
                
                nilai_kredit = row[col_idx]
                if pd.notna(nilai_kredit) and str(nilai_kredit).strip() != "":
                    try:
                        nilai_kredit = float(nilai_kredit)
                    except ValueError:
                        nilai_kredit = 0.0
                        
                    data_bersih.append({
                        "sheet_name": "I.4_1",
                        "kelompok_bank": current_kelompok_bank,
                        "kategori_pinjaman": current_kategori,
                        "sektor_kbli": sektor_kbli,
                        "periode_tahun": int(thn),
                        "periode_bulan": bln,
                        "kredit_miliar_rp": nilai_kredit,
                        "source_file": os.path.basename(file_path)
                    })

    df_final = pd.DataFrame(data_bersih)
    print(f"Berhasil merapikan {len(df_final)} baris data. Contoh hasil:")
    print(df_final.head(3))
    
    # SIMPAN KE CSV SEBAGAI BUKTI SEMENTARA
    output_csv = 'raw_data/hasil_seki_bi_raw.csv'
    df_final.to_csv(output_csv, index=False)
    print(f"\n✅ Data SEKI berhasil diekstrak dan disimpan ke: {output_csv}")
    print("Kode to_sql() ke database ditunda menunggu Arza mengeksekusi migrasi tabel.")

if __name__ == "__main__":
    ingest_bi_seki('raw_data/TABEL1_4.xls')