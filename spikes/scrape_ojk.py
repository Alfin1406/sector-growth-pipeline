import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re  # <--- Modul baru untuk mencuci teks

def bersihkan_teks(teks):
    """Fungsi ajaib untuk melibas Enter (\n), Tab (\t), dan spasi ganda"""
    if pd.isna(teks) or not teks:
        return ""
    # Ganti semua karakter spasi berlebih/enter/tab dengan 1 spasi saja
    teks_bersih = re.sub(r'\s+', ' ', str(teks))
    return teks_bersih.strip()

def ekstrak_detail_ojk(url_detail):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url_detail, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Ekstrak Teks Isi
        paragraf = soup.find_all('p')
        teks_isi = " ".join([p.get_text(strip=True) for p in paragraf if len(p.get_text(strip=True)) > 30])
        
        # Cuci teks isi agar tidak merusak format CSV
        teks_isi = bersihkan_teks(teks_isi)
        
        # 2. Ekstrak Link Lampiran
        lampiran = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                if href.startswith('/'):
                    href = "https://www.ojk.go.id" + href
                lampiran.append(href)
                
        return teks_isi, ", ".join(lampiran)
    except Exception as e:
        return f"Error: {e}", ""

def scrape_ojk(url, kategori):
    print(f"\nMencari daftar link {kategori} OJK...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url_filter = "/pengumuman/Pages/" if kategori == "Pengumuman" else "/rancangan-regulasi/Pages/"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        data = []
        
        link_targets = []
        for a_tag in soup.find_all('a', href=True):
            judul = a_tag.get_text(strip=True)
            judul = bersihkan_teks(judul) # Cuci judul dari enter/spasi berlebih
            link = a_tag['href']
            
            if len(judul) > 25 and url_filter in link:
                if link.startswith('/'):
                    link = "https://www.ojk.go.id" + link
                
                # Hindari duplikasi link
                if not any(d.get('link') == link for d in link_targets):
                    link_targets.append({"kategori": kategori, "judul": judul, "link": link})
        
        # link_targets = link_targets[:3] # Tetap dimatikan agar ambil semua data di halaman 1
        print(f"Ditemukan {len(link_targets)} link valid. Mulai Deep Crawling ke dalam halaman...")
        
        for item in link_targets:
            print(f" -> Mengekstrak isi: {item['judul'][:40]}...")
            isi_teks, link_dokumen = ekstrak_detail_ojk(item['link'])
            
            item['isi_teks'] = isi_teks
            item['link_dokumen_lampiran'] = link_dokumen
            data.append(item)
            time.sleep(1) 
            
        return pd.DataFrame(data)
            
    except Exception as e:
        print(f"❌ Gagal mengakses OJK: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    url_pengumuman = "https://www.ojk.go.id/id/berita-dan-kegiatan/pengumuman/Default.aspx"
    url_regulasi = "https://www.ojk.go.id/id/regulasi/otoritas-jasa-keuangan/rancangan-regulasi/Default.aspx"
    
    df_pengumuman = scrape_ojk(url_pengumuman, "Pengumuman")
    df_regulasi = scrape_ojk(url_regulasi, "Rancangan Regulasi")
    
    df_final = pd.concat([df_pengumuman, df_regulasi], ignore_index=True)
    if not df_final.empty:
        # Gunakan quoting untuk menjaga agar koma di dalam teks tidak merusak kolom
        import csv
        output_csv = 'raw_data/hasil_ojk_deep_raw.csv'
        df_final.to_csv(output_csv, index=False, sep=';', quoting=csv.QUOTE_ALL)
        print(f"\n📂 SUPERB! Data Deep Crawling yang sudah DICUCI disimpan ke {output_csv}")