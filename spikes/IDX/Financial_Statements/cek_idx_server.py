import requests

# URL target (misalnya halaman data saham IDX)
target_url = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles"

try:
    print("Mencoba mengakses server IDX tanpa lisensi API resmi...")
    # Pipeline Airflow standar biasanya menggunakan header default python-requests
    response = requests.get(target_url, timeout=10)
    
    print(f"HTTP Status Code: {response.status_code}")
    if response.status_code == 403:
        print("BUKTI: Akses ditolak (403 Forbidden). Server IDX mendeteksi bot/script dan memblokir akses.")
    else:
        print(f"Response: {response.text[:200]}")

except requests.exceptions.RequestException as e:
    print(f"BUKTI: Koneksi gagal atau Timeout. Detail error: {e}")