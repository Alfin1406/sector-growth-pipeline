import requests
from bs4 import BeautifulSoup
import pandas as pd
import time


# ==========================================
# 1. BACA DATA HASIL SCRAPING SEBELUMNYA
# ==========================================

input_file = "data_center_antaranews_all.csv"

df = pd.read_csv(
    input_file,
    encoding="utf-8-sig"
)

print("Total artikel:", len(df))


# ==========================================
# 2. HEADER
# ==========================================

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/153.0.0.0 Safari/537.36"
}


# ==========================================
# 3. TEMPAT MENYIMPAN DATA
# ==========================================

contents = []
image_urls = []


# ==========================================
# 4. LOOP SETIAP ARTIKEL
# ==========================================

for index, row in df.iterrows():

    url = row["article_url"]

    print(f"\n[{index + 1}/{len(df)}] Mengambil artikel:")
    print(url)

    try:

        # ==================================
        # REQUEST HALAMAN ARTIKEL
        # ==================================

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        print("Status:", response.status_code)

        if response.status_code != 200:
            contents.append(None)
            image_urls.append(None)
            continue


        # ==================================
        # PARSING HTML
        # ==================================

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # ==================================
        # 5. AMBIL CONTENT ARTIKEL
        # ==================================

        article_content = soup.select_one(
            "div.wrap__article-detail-content.post-content"
        )


        if article_content:

            paragraphs = article_content.find_all("p")

            content = "\n".join(
                p.get_text(" ", strip=True)
                for p in paragraphs
            )

        else:

            content = None

            print("Content tidak ditemukan.")


        # ==================================
        # 6. AMBIL GAMBAR UTAMA
        # ==================================

        image_tag = soup.select_one(
            "div.wrap__article-detail-image img.img-fluid"
        )


        # Kalau selector pertama tidak ditemukan
        if not image_tag:

            image_tag = soup.select_one(
                "div.wrap__article-detail-image img"
            )


        # Kalau masih tidak ditemukan,
        # gunakan og:image
        if image_tag:

            image_url = image_tag.get("src")

        else:

            og_image = soup.select_one(
                'meta[property="og:image"]'
            )

            if og_image:

                image_url = og_image.get("content")

            else:

                image_url = None


        print("Content:", "Berhasil" if content else "Gagal")
        print("Image:", image_url)


        # ==================================
        # 7. SIMPAN HASIL
        # ==================================

        contents.append(content)
        image_urls.append(image_url)


        # ==================================
        # 8. JEDA
        # ==================================

        time.sleep(2)


    except Exception as e:

        print("Error:", e)

        contents.append(None)
        image_urls.append(None)


# ==========================================
# 9. TAMBAHKAN CONTENT DAN IMAGE
# ==========================================

df["content"] = contents

df["image_url"] = image_urls


# ==========================================
# 10. SIMPAN HASIL
# ==========================================

output_file = "data_center_antaranews_with_content.csv"

df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 11. HASIL AKHIR
# ==========================================

print("\n===================================")
print("SCRAPING SELESAI")
print("===================================")

print("Total artikel:", len(df))

print(
    "Content berhasil:",
    df["content"].notna().sum()
)

print(
    "Image berhasil:",
    df["image_url"].notna().sum()
)

print(
    "Content gagal:",
    df["content"].isna().sum()
)

print(
    "Image gagal:",
    df["image_url"].isna().sum()
)

print("\nFile berhasil disimpan:")
print(output_file)