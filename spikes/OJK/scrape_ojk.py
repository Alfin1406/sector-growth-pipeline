import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import csv
import os
from datetime import datetime

# ==========================================
# 1. SETUP FOLDER & PATH OUTPUT
# ==========================================
RAW_DIR = "raw_data/OJK"
os.makedirs(RAW_DIR, exist_ok=True)

FILE_PENGUMUMAN = os.path.join(RAW_DIR, "ojk_pengumuman_raw.csv")
FILE_REGULASI = os.path.join(RAW_DIR, "ojk_rancangan_regulasi_raw.csv")

# ==========================================
# 2. FUNGSI UTILITAS & IDEMPOTENCY
# ==========================================
def bersihkan_teks(teks):
    if pd.isna(teks) or not teks:
        return ""
    teks_bersih = str(teks).replace('\u200b', '').replace('â€‹', '').replace('â€', '').replace('Â', '')
    teks_bersih = re.sub(r'\s+', ' ', teks_bersih)
    return teks_bersih.strip()

def get_existing_links(filepath):
    """Membaca CSV lama untuk mendapatkan daftar link yang SUDAH pernah ditarik."""
    if os.path.exists(filepath):
        try:
            df_existing = pd.read_csv(filepath, sep=';', encoding='utf-8-sig')
            return set(df_existing['link'].dropna().tolist())
        except Exception:
            return set()
    return set()

def append_to_csv(df_new, filepath):
    """Menyimpan data baru ke CSV (Append jika sudah ada, Bikin baru jika belum)"""
    if not df_new.empty:
        # Susun urutan kolom agar sesuai skema database
        df_new = df_new[['kategori', 'tanggal_rilis', 'judul', 'link', 'isi_teks', 'link_dokumen_lampiran']]
        
        if os.path.exists(filepath):
            df_new.to_csv(filepath, mode='a', header=False, index=False, sep=';', quoting=csv.QUOTE_ALL, encoding='utf-8-sig')
        else:
            df_new.to_csv(filepath, index=False, sep=';', quoting=csv.QUOTE_ALL, encoding='utf-8-sig')
        print(f"📂 SUPERB! {len(df_new)} data baru ditambahkan ke {filepath}")
    else:
        print(f"✨ Tidak ada data baru untuk {filepath} (Sudah up-to-date).")

# ==========================================
# 3. FUNGSI CRAWLING UTAMA
# ==========================================
def ekstrak_detail_ojk(url_detail):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url_detail, headers=headers, timeout=15)
        resp.encoding = 'utf-8' 
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        kontainer_utama = soup.find('div', class_='content') or soup.find('div', id='ctl00_PlaceHolderMain') or soup
        
        # --- FITUR BARU: EKSTRAK TANGGAL RILIS ---
        tanggal_rilis = ""
        # 1. Coba cari tag HTML khusus tanggal
        tag_tanggal = soup.find('time') or soup.find(class_=re.compile(r'date|tanggal|waktu', re.I))
        if tag_tanggal:
            tanggal_rilis = bersihkan_teks(tag_tanggal.get_text())
        
        # 2. Pelindung Regex: Cari pola "13 November 2026" di seluruh teks jika tag tidak ketemu
        if not tanggal_rilis:
            pola_tanggal = r'\b(\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4})\b'
            match = re.search(pola_tanggal, kontainer_utama.get_text(), re.IGNORECASE)
            if match:
                tanggal_rilis = match.group(1)
                
        # 3. Fallback jika benar-benar kosong
        if not tanggal_rilis:
            tanggal_rilis = datetime.now().strftime("%d %B %Y")
            
        # --- EKSTRAK LAMPIRAN ---
        lampiran = []
        for a in kontainer_utama.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip')):
                if href.startswith('/'):
                    href = "https://www.ojk.go.id" + href
                lampiran.append(href)
                a.decompose() # Hancurkan tag agar tidak tersedot teks paragraf
                
        # --- EKSTRAK TEKS ISI ---
        paragraf = kontainer_utama.find_all('p')
        teks_valid = []
        teks_sampah = ["Lembaga negara independen yang mempunyai fungsi", "Gedung Sumitro Djojohadikusumo", "Page Content"]
        
        for p in paragraf:
            teks_p = p.get_text(strip=True)
            if len(teks_p) > 30 and not any(sampah in teks_p for sampah in teks_sampah):
                teks_valid.append(teks_p)
                
        teks_isi = bersihkan_teks(" ".join(teks_valid))
        lampiran = list(set(lampiran))
        
        return tanggal_rilis, teks_isi, ", ".join(lampiran)
        
    except Exception as e:
        return "", f"Error: {e}", ""

def scrape_ojk(url, kategori, existing_links):
    print(f"\n[*] Memindai halaman {kategori} OJK...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url_filter = "/pengumuman/Pages/" if kategori == "Pengumuman" else "/rancangan-regulasi/Pages/"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        data_baru = []
        link_targets = []
        
        for a_tag in soup.find_all('a', href=True):
            judul = bersihkan_teks(a_tag.get_text(strip=True))
            link = a_tag['href']
            
            if len(judul) > 25 and url_filter in link:
                if link.startswith('/'):
                    link = "https://www.ojk.go.id" + link
                
                if not any(d.get('link') == link for d in link_targets):
                    link_targets.append({"kategori": kategori, "judul": judul, "link": link})
        
        # LOGIKA IDEMPOTENCY: Buang link yang sudah ada di database lokal
        targets_baru = [item for item in link_targets if item['link'] not in existing_links]
        
        print(f"[*] Total {len(link_targets)} link di halaman. ({len(link_targets) - len(targets_baru)} diabaikan karena sudah ada).")
        print(f"[*] Mengeksekusi Deep Crawling untuk {len(targets_baru)} dokumen BARU...")
        
        for item in targets_baru:
            print(f" -> Sedot data: {item['judul'][:40]}...")
            tanggal_rilis, isi_teks, link_dokumen = ekstrak_detail_ojk(item['link'])
            
            item['tanggal_rilis'] = tanggal_rilis
            item['isi_teks'] = isi_teks
            item['link_dokumen_lampiran'] = link_dokumen
            data_baru.append(item)
            time.sleep(1.5) # Jeda sopan agar IP tidak di-ban
            
        return pd.DataFrame(data_baru)
            
    except Exception as e:
        print(f"❌ Gagal mengakses web OJK: {e}")
        return pd.DataFrame()

# ==========================================
# 4. EKSEKUSI UTAMA
# ==========================================
if __name__ == "__main__":
    url_pengumuman = "https://www.ojk.go.id/id/berita-dan-kegiatan/pengumuman/Default.aspx"
    url_regulasi = "https://www.ojk.go.id/id/regulasi/otoritas-jasa-keuangan/rancangan-regulasi/Default.aspx"
    
    # Baca riwayat link yang sudah ada di lokal
    riwayat_pengumuman = get_existing_links(FILE_PENGUMUMAN)
    riwayat_regulasi = get_existing_links(FILE_REGULASI)
    
    # Jalankan Scraper (Hanya akan mengekstrak yang baru)
    df_pengumuman = scrape_ojk(url_pengumuman, "Pengumuman", riwayat_pengumuman)
    df_regulasi = scrape_ojk(url_regulasi, "Rancangan Regulasi", riwayat_regulasi)
    
    # Simpan ke CSV masing-masing
    append_to_csv(df_pengumuman, FILE_PENGUMUMAN)
    append_to_csv(df_regulasi, FILE_REGULASI)