import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=UserWarning)

file_path = 'raw_data/TABEL1_4.xls'

# 1. Cek semua nama sheet yang ada di dalam file Excel
xl = pd.ExcelFile(file_path)
print("=== DAFTAR SHEET ===")
print(xl.sheet_names)

# 2. Baca sheet I.4_1 tanpa skiprows untuk melihat posisi header Tahun & Bulan
df_raw = pd.read_excel(file_path, sheet_name='I.4_1', header=None)
print("\n=== 15 BARIS PERTAMA (CEK POSISI HEADER TAHUN & BULAN) ===")
print(df_raw.iloc[:15, :10].to_string())

# 3. Lihat seluruh daftar Sektor & Kelompok Bank dari baris 0 sampai akhir
print("\n=== DAFTAR LENGKAP BARIS (KOLOM 0 SAMPAI 3) ===")
for idx, row in df_raw.iterrows():
    val0 = str(row[0]).strip() if pd.notna(row[0]) else ""
    val1 = str(row[1]).strip() if pd.notna(row[1]) else ""
    val2 = str(row[2]).strip() if pd.notna(row[2]) else ""
    val3 = str(row[3]).strip() if pd.notna(row[3]) else ""
    if any([val0, val1, val2, val3]):
        print(f"Baris {idx:3d} | [0]: {val0} | [1]: {val1} | [2]: {val2} | [3]: {val3}")