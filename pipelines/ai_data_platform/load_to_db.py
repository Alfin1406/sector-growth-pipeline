import os
import time
import json
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from datetime import datetime

# ==============================================================
# 1. SETUP KONEKSI DATABASE NEON DENGAN FITUR RETRY
# ==============================================================
def get_engine_with_retry(max_retries=5):
    # Mengambil kredensial dari Environment Variables
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_pass = os.getenv("POSTGRES_PASSWORD")
    db_ssl = os.getenv("POSTGRES_SSLMODE", "require")

    if not all([db_host, db_name, db_user, db_pass]):
        raise ValueError(
            "Environment variables untuk database Neon "
            "belum disetel di Airflow!"
        )

    # URL.create lebih aman untuk password dengan karakter khusus
    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_user,
        password=db_pass,
        host=db_host,
        port=int(db_port),
        database=db_name,
        query={"sslmode": db_ssl}
    )

    engine = create_engine(
        database_url,
        connect_args={"connect_timeout": 20},
        pool_pre_ping=True
    )

    for attempt in range(1, max_retries + 1):
        try:
            print(
                f"Mencoba koneksi ke Neon DB "
                f"({attempt}/{max_retries})..."
            )

            # Test koneksi ringan
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            print("Koneksi Neon berhasil!")
            return engine

        except Exception as e:
            print(f"Koneksi gagal: {e}")

            if attempt == max_retries:
                engine.dispose()
                raise

            wait_time = 15 * attempt
            print(
                f"Mencoba kembali dalam {wait_time} detik..."
            )
            time.sleep(wait_time)


# ==============================================================
# 2. PROSES UTAMA (ETL)
# ==============================================================
def main():
    # Menggunakan absolute path agar aman saat dijalankan Airflow Docker
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        base_dir,
        "data",
        "berita_new_enriched.json"
    )

    print(f"Membaca file {file_path}...")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    except FileNotFoundError:
        raise FileNotFoundError(
            "File JSON tidak ditemukan. "
            "Pastikan task AI Enrichment berjalan sukses sebelumnya."
        )

    if not isinstance(data, list):
        raise ValueError(
            "Format berita_new_enriched.json harus berupa JSON list."
        )

    if not data:
        print("Tidak ada data untuk dimasukkan ke database.")
        return

    # Transformasi Data Pandas
    df = pd.DataFrame(data)

    # Menghapus duplikasi berdasarkan link
    df = df.drop_duplicates(subset=["link"])

    # Mengolah tanggal dengan aman
    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce"
    ).dt.date

    # Mengolah teknologi_dibahas
    if "teknologi_dibahas" in df.columns:
        df["teknologi_dibahas"] = df["teknologi_dibahas"].apply(
            lambda x: [
                item.strip() for item in x.split(",") if item.strip()
            ] if isinstance(x, str) else (
                x if isinstance(x, list) else []
            )
        )

    print("Memulai proses UPSERT ke database Neon...")

    data_to_insert = df.to_dict(orient="records")

    # Panggil engine dengan fitur retry
    engine = get_engine_with_retry()

    query = text("""
        INSERT INTO public.alfin_berita_ai (
            judul,
            tanggal,
            link,
            gambar,
            isi_berita,
            sumber,
            kategori_bisnis,
            ringkasan_ai,
            teknologi_dibahas,
            kategori_lisensi,
            skor_relevansi_it,
            waktu_scrape
        ) VALUES (
            :judul,
            :tanggal,
            :link,
            :gambar,
            :isi_berita,
            :sumber,
            :kategori_bisnis,
            :ringkasan_ai,
            CAST(:teknologi_dibahas AS text[]),
            :kategori_lisensi,
            :skor_relevansi_it,
            :waktu_scrape
        )
        ON CONFLICT (link) DO UPDATE SET
            judul = EXCLUDED.judul,
            tanggal = EXCLUDED.tanggal,
            gambar = EXCLUDED.gambar,
            isi_berita = EXCLUDED.isi_berita,
            sumber = EXCLUDED.sumber,
            kategori_bisnis = EXCLUDED.kategori_bisnis,
            ringkasan_ai = EXCLUDED.ringkasan_ai,
            teknologi_dibahas = EXCLUDED.teknologi_dibahas,
            kategori_lisensi = EXCLUDED.kategori_lisensi,
            skor_relevansi_it = EXCLUDED.skor_relevansi_it,
            waktu_scrape = EXCLUDED.waktu_scrape
    """)

    berita_diproses = 0
    berita_dilewati = 0

    try:
        with engine.begin() as connection:
            for baris in data_to_insert:

                # Lewati artikel tanpa link
                if not baris.get("link"):
                    berita_dilewati += 1
                    print("Artikel dilewati karena tidak memiliki link.")
                    continue

                teknologi = baris.get("teknologi_dibahas") or []

                # Pastikan teknologi berbentuk Python list
                if not isinstance(teknologi, list):
                    teknologi = []

                # Parameter untuk query UPSERT
                params = {
                    "judul": baris.get("judul", ""),
                    "tanggal": baris.get("tanggal"),
                    "link": baris["link"],
                    "gambar": baris.get("gambar", ""),
                    "isi_berita": baris.get("isi_berita", ""),
                    "sumber": baris.get("sumber", ""),
                    "kategori_bisnis": baris.get("kategori_bisnis", ""),
                    "ringkasan_ai": baris.get("ringkasan_ai", ""),
                    "teknologi_dibahas": [
                        str(item) for item in teknologi
                    ],
                    "kategori_lisensi": baris.get(
                        "kategori_lisensi", ""
                    ),
                    "skor_relevansi_it": baris.get(
                        "skor_relevansi_it", 0
                    ),
                    "waktu_scrape": datetime.now()
                }

                connection.execute(query, params)
                berita_diproses += 1

        print("--------------------------------------")
        print("PROSES TRUE INCREMENTAL LOAD (UPSERT) SELESAI!")
        print(f"Berhasil diproses : {berita_diproses} berita")
        print(f"Dilewati          : {berita_dilewati} berita")
        print("--------------------------------------")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
