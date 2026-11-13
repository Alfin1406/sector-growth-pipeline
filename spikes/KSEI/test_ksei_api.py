import requests
import json

def test_ksei_api():
    # URL API rahasia yang kita temukan dari tab Network (pakai underscore)
    api_url = "https://www.ksei.co.id/en/regulations/ksei-regulations"
    
    # Parameter yang dikirim persis seperti saat kamu mengetik di search bar
    params = {
        "locale": "en",
        "search": "data center",
        "page": "1"
    }
    
    # KUNCI UTAMA: Kita memalsukan diri sebagai browser yang sedang melakukan AJAX
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest", # Ini password rahasia agar WAF KSEI mengira ini koneksi API resmi
        "Referer": "https://www.ksei.co.id/en/regulations/ksei-regulations"
    }
    
    print(f"Mencoba menembus API: {api_url}")
    try:
        # Kita tembak pakai modul requests biasa (tanpa curl_cffi, tanpa selenium)
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        response.raise_for_status() 
        
        print(f"✔️ Status Code: {response.status_code} (Berhasil Tembus!)")
        
        # Mari kita lihat apakah KSEI membalas dengan JSON yang rapi
        try:
            data = response.json()
            print("\n🎉 JACKPOT! Server merespons dengan JSON murni:")
            # Print sebagian hasilnya agar tidak kepanjangan di terminal
            print(json.dumps(data, indent=2)[:800] + "\n\n... (teks dipotong)")
        except ValueError:
            print("\n⚠️ Respons berhasil, tapi bukan JSON murni. Ini adalah HTML partial:")
            print(response.text[:800] + "\n\n... (teks dipotong)")
            
    except requests.exceptions.Timeout:
        print("❌ Gagal: Kena Timeout lagi. WAF-nya sangat ketat memblokir request Python murni.")
    except Exception as e:
        print(f"❌ Gagal dengan error lain: {e}")

if __name__ == "__main__":
    test_ksei_api()