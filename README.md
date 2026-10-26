# Sector Growth Pipeline

Repo untuk pipeline pengumpulan data (Airflow) dan riwayat migrasi database PostgreSQL
pada proyek Sector Growth Insight (PLN Icon Plus).
Dashboard Streamlit ada di repo terpisah: **sector-growth-dashboard**.

## Struktur
- `docs/` source register dan schema blueprint
- `spikes/` skrip uji kelayakan (sekali pakai)
- `airflow/dags/` penjadwalan (satu DAG per sumber)
- `pipelines/` kode ekstraksi per sumber
- `database/migrations/` riwayat DDL bernomor (`001_...sql`, `002_...sql`)
- `tests/`

## Aturan
- Satu sumber = satu DAG dan satu tabel, supaya modular dan mudah di-debug.
- Perubahan database hanya lewat file migrasi bernomor.
- Jangan commit `.env` atau API key. Salin `.env.example` menjadi `.env` lalu isi nilai asli.
- Setiap orang bekerja di branch sendiri (`alfin`, `arza`, `atha`), digabung ke `develop`.
  `main` dipakai untuk deployment.