import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_ojk(url, kategori):
    print(f"Mencoba mengakses {kategori} OJK...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        data = []
        
        # Tentukan kata kunci wajib di dalam URL berdasarkan kategori yang sedang dicari
        url_filter = "/pengumuman/Pages/" if kategori == "Pengumuman" else "/rancangan-regulasi/Pages/"
        
        for a_tag in soup.find_all('a', href=True):
            judul = a_tag.get_text(strip=True)
            link = a_tag['href']
            
            # FILTER KETAT: 
            # Link HARUS mengandung path kategori spesifiknya agar tidak tertukar dengan widget
            if len(judul) > 25 and url_filter in link:
                if link.startswith('/'):
                    link = "https://www.ojk.go.id" + link
                    
                data.append({
                    "kategori": kategori,
                    "judul": judul,
                    "link": link
                })
                
        df = pd.DataFrame(data).drop_duplicates(subset=['link']).head(10)
        
        if not df.empty:
            print(f"✅ Berhasil mendapatkan {len(df)} data bersih {kategori}.")
            return df
        else:
            print(f"⚠️ Halaman diakses, tapi tidak ada artikel dengan filter '{url_filter}'.")
            return pd.DataFrame()
            
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
        output_csv = 'raw_data/hasil_ojk_raw.csv'
        df_final.to_csv(output_csv, index=False)
        print(f"\n📂 Sampel data BERSIH disimpan ke {output_csv}")