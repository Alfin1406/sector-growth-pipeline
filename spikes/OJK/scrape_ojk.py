import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import csv

def bersihkan_teks(teks):
    if pd.isna(teks) or not teks:
        return ""
    # 1. Hapus karakter alien/mojibake bawaan dari copy-paste MS Word OJK
    teks_bersih = str(teks).replace('\u200b', '').replace('â€‹', '').replace('â€', '').replace('Â', '')
    # 2. Ratakan spasi/enter
    teks_bersih = re.sub(r'\s+', ' ', teks_bersih)
    return teks_bersih.strip()

def ekstrak_detail_ojk(url_detail):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url_detail, headers=headers, timeout=15)
        resp.encoding = 'utf-8' # Paksa baca sebagai UTF-8 agar karakter tidak rusak
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        kontainer_utama = soup.find('div', class_='content') or soup.find('div', id='ctl00_PlaceHolderMain') or soup
        
        # LANGKAH 1: Ekstrak Lampiran Dulu & Hancurkan Tag-nya!
        lampiran = []
        for a in kontainer_utama.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip')):
                if href.startswith('/'):
                    href = "https://www.ojk.go.id" + href
                lampiran.append(href)
                # Operasi Bedah: Hapus elemen <a> ini dari HTML agar namanya tidak ikut tersedot ke teks paragraf
                a.decompose() 
                
        # LANGKAH 2: Ekstrak Teks Isi (Sekarang sudah bersih dari teks link lampiran)
        paragraf = kontainer_utama.find_all('p')
        teks_valid = []
        
        teks_sampah = [
            "Lembaga negara independen yang mempunyai fungsi",
            "Gedung Sumitro Djojohadikusumo",
            "Page Content"
        ]
        
        for p in paragraf:
            teks_p = p.get_text(strip=True)
            if len(teks_p) > 30 and not any(sampah in teks_p for sampah in teks_sampah):
                teks_valid.append(teks_p)
                
        teks_isi = " ".join(teks_valid)
        teks_isi = bersihkan_teks(teks_isi)
        
        lampiran = list(set(lampiran))
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
            judul = bersihkan_teks(judul) 
            link = a_tag['href']
            
            if len(judul) > 25 and url_filter in link:
                if link.startswith('/'):
                    link = "https://www.ojk.go.id" + link
                
                if not any(d.get('link') == link for d in link_targets):
                    link_targets.append({"kategori": kategori, "judul": judul, "link": link})
        
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
        output_csv = 'raw_data/hasil_ojk_deep_raw.csv'
        # Tambahan utf-8-sig agar Excel tidak menampilkan karakter alien
        df_final.to_csv(output_csv, index=False, sep=';', quoting=csv.QUOTE_ALL, encoding='utf-8-sig')
        print(f"\n📂 SUPERB! Data Deep Crawling disimpan ke {output_csv}")