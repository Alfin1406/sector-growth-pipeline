import os
import pdfplumber

def analyze_ksei_local_pdfs():
    # Folder tempat kamu menyimpan PDF KSEI yang didownload manual
    folder_path = 'raw_data/KSEI' 
    
    # Pastikan foldernya ada
    if not os.path.exists(folder_path):
        print(f"Folder '{folder_path}' tidak ditemukan. Buat foldernya dan taruh PDF KSEI di sana.")
        return

    # Cari semua file PDF di dalam folder
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"Tidak ada file PDF di dalam folder '{folder_path}'.")
        return

    print(f"Ditemukan {len(pdf_files)} file PDF regulasi KSEI.")
    
    # Daftar Kata Kunci (Keywords) untuk Icon Plus
    keywords = ['data center', 'cloud', 'integrasi', 'infrastruktur', 'jaringan', 'keamanan siber', 'cyber security', 'electronic', 'sistem elektronik']
    
    print("\nMemulai analisis dokumen...")
    
    for filename in pdf_files:
        file_path = os.path.join(folder_path, filename)
        print(f"\nMenganalisis: {filename}")
        
        try:
            full_text = ""
            # Buka dan ekstrak teks pakai pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text.lower()
            
            # Cocokkan kata kunci
            found_keywords = []
            for kw in keywords:
                if kw in full_text:
                    found_keywords.append(kw)
                    
            if found_keywords:
                print(f"  🚨 [INSIGHT DITEMUKAN] Regulasi ini menyebutkan: {', '.join(found_keywords)}")
                print(f"  💡 Tindakan: Beritahu tim Sales Icon+ terkait potensi proyek infrastruktur.")
            else:
                print("  ⚪ Tidak ada kata kunci infrastruktur IT yang ditemukan.")
                
        except Exception as e:
             print(f"  ❌ Gagal membaca PDF {filename}: {e}")

if __name__ == "__main__":
    analyze_ksei_local_pdfs()