
import requests
import urllib3
import json

urllib3.disable_warnings()

BASE = "https://api-gateway.jasamarga.co.id/prd/webkorporat/api/public"

headers = {
    "Content-Type": "application/json",
    "x-api-key": "a186751c-791c-4bf3-8fd5-5bd27e220f59"
}

print("=" * 65)
print("PEMERIKSAAN API CAREER JASA MARGA")
print("=" * 65)

try:
    response = requests.get(
        f"{BASE}/page/karir/",
        params={"lang": "id"},
        headers=headers,
        timeout=30
    )

    print("HTTP STATUS:", response.status_code)

    try:
        data = response.json()
        print("\nRESPONS API:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:10000])
    except ValueError:
        print(response.text[:5000])

except requests.RequestException as e:
    print("ERROR:", e)
