# Source Register — Phase 0: Feasibility Check

**Tujuan:** mengonfirmasi akses/API, syarat penggunaan (*terms of use*), dan kebaruan data tiap kandidat sumber, lalu memberi keputusan **GO / GO-MANUAL / NO-GO** sebelum pipeline dibangun.

**Exit criteria Phase 0:** setiap sumber punya keputusan akhir, minimal 3 sumber berstatus GO (atau GO-MANUAL), dan minimal satu di antaranya dari *hiring* atau *news*.

**Legenda status**

| Status | Arti |
| :--- | :--- |
| PENDING | Belum diuji |
| GO | Bisa diakses otomatis, syarat penggunaan aman, data cukup segar |
| GO-MANUAL | Tidak bisa otomatis, tapi layak lewat unggah manual / unduh berkala |
| NO-GO | Tidak layak (diblokir, terlarang oleh ToS, atau data tidak memadai) |

> Aturan pengisian: keputusan harus punya **bukti uji** (tanggal, hasil, link ke skrip di `spikes/` atau tangkapan layar) dan **alasan satu kalimat**. Jangan menandai GO tanpa bukti.

---

## 1. Ringkasan

| # | Sumber | Owner | Cadence / lead time | Status | Tgl. keputusan |
| :-- | :--- | :--- | :--- | :--- | :--- |
| 1 | BPS (Official API) | TBD | Kuartalan, lagging | PENDING | |
| 2 | BKPM / Kementerian Investasi | TBD | Kuartalan, medium | PENDING | |
| 3 | Regulator umum (DPR / MK / Energi) | TBD | Bulanan/kuartalan, medium | PENDING | |
| 4 | Job portals (Jobstreet, Indeed, dll.) | TBD | Harian/mingguan, leading | PENDING | |
| 5 | Career pages perusahaan besar | TBD | Mingguan | PENDING | |
| 6 | Bea Cukai (impor per HS code) | TBD | Bulanan, medium | PENDING | |
| 7 | Existing news pipeline | TBD | Real time | PENDING | |
| 8 | IDX (Bursa Efek Indonesia) | TBD (kandidat: Personel 1 atau 3) | Harian/mingguan, medium | PENDING | |
| 9 | Bank Indonesia / OJK | TBD (ingesti Fase 2: Personel 1) | Bulanan, lagging | PENDING | |

**Hitungan exit criteria:** GO/GO-MANUAL = 0 dari minimal 3 · termasuk hiring atau news? belum

---

## 2. Detail per sumber

Salin blok "Hasil uji" untuk setiap sumber dan isi saat pengujian.

### 1. BPS (Official API)
- **Target data:** GDP per sektor (basis KBLI), indeks produksi industri (IPI), output sektor regional, ketenagakerjaan per sektor
- **Insight:** pertumbuhan sektor (YoY/QoQ), regional hotspots
- **Cek Phase 0:** akses, opsi API, ketersediaan tabel sektor/GDP/IPI, granularitas (nasional vs regional), tanggal pembaruan
- **Risiko:** data hanya tersedia sebagai PDF/tabel statis
- **Fallback:** unduh tabel berkala / unggah manual
- **Hasil uji:**
  - Tanggal uji:
  - Metode akses (API / bulk download / scrape / manual):
  - Format data:
  - Granularitas sektor (KBLI level berapa) & wilayah:
  - Data terbaru periode:
  - Syarat penggunaan / lisensi (link + ringkasan):
  - Respons server / kendala akses:
  - Bukti (link skrip/tangkapan layar):
- **Keputusan:** PENDING — alasan:

### 2. BKPM / Kementerian Investasi
- **Target data:** realisasi investasi (domestik & asing) per sektor dan wilayah, jumlah proyek
- **Insight:** aliran komitmen modal, momentum sektor
- **Cek Phase 0:** ada API, bulk download, atau hanya tabel publikasi
- **Risiko:** data hanya PDF/tabel
- **Fallback:** unduh tabel berkala / unggah manual
- **Hasil uji:** (salin kolom dari blok 1)
- **Keputusan:** PENDING — alasan:

### 3. Regulator umum (DPR / MK / Energi)
- **Target data:** regulasi bisnis baru, arah kebijakan yang akan diatur
- **Insight:** fokus pemerintah, syarat kepatuhan, potensi bisnis baru
- **Cek Phase 0:** cari regulasi baru yang bisa diunduh atau di-scrape
- **Risiko:** dokumen berupa PDF
- **Fallback:** kurasi manual daftar regulasi
- **Hasil uji:** (salin kolom dari blok 1)
- **Keputusan:** PENDING — alasan:

### 4. Job portals (Jobstreet, Indeed, dll.)
- **Target data:** judul posisi, perusahaan, sektor, lokasi, tanggal posting, skills (tanpa data pribadi)
- **Insight:** total lowongan per sektor (ekspansi), porsi posisi IT/digital per sektor
- **Cek Phase 0:** uji akses 2–3 portal (catat per portal)
- **Risiko:** nilai tertinggi tapi risiko tertinggi (terms & blocking)
- **Fallback:** career pages atau unggah manual
- **Hasil uji (per portal):**
  - Portal / tanggal uji:
  - robots.txt & ToS (ringkasan, izin scraping?):
  - Respons server (HTTP code, captcha, rate limit):
  - Field yang tersedia:
  - Bukti:
- **Keputusan:** PENDING — alasan:

### **5. Career pages perusahaan besar**
- **Target data:** kolom sama dengan job portals, meliputi nama posisi (role title), nama perusahaan (company), sektor (sector), lokasi (location), tanggal publikasi (post date), dan keterampilan yang dibutuhkan (skills).
- **Insight:** cross-check data lowongan dari job portals dengan informasi rekrutmen resmi perusahaan untuk memvalidasi kebutuhan tenaga kerja, tren perekrutan, dan permintaan posisi digital/IT di masing-masing sektor.

- **Cek Phase 0:** telah meninjau 8 perusahaan besar dari sektor energi, pertambangan, perbankan, dan manufaktur.

  **Daftar perusahaan yang diperiksa:**

  | No. | Sektor | Perusahaan | Struktur halaman dan hasil pemeriksaan |
  |---|---|---|---|
  | 1 | Energi | PLN | Portal rekrutmen publik, tersedia menu All Jobs dan filter jenjang, legal entity, serta program studi. Saat pemeriksaan tidak ditemukan lowongan yang ditampilkan. |
  | 2 | Energi | Pertamina | Website e-Recruitment dapat diakses publik. Terdapat halaman Pertamina Talent Candidate, tetapi jalur yang diuji mengarah ke login untuk melanjutkan. |
  | 3 | Pertambangan | MIND ID | Portal karier publik dengan pencarian dan filter lokasi, perusahaan, kategori, serta tipe pekerjaan. Saat pemeriksaan tidak ditemukan lowongan yang ditampilkan. |
  | 4 | Pertambangan | Freeport Indonesia | Halaman karier resmi dapat diakses publik dan memiliki filter kategori. Saat pemeriksaan tidak tersedia lowongan pekerjaan. |
  | 5 | Pertambangan | ANTAM | Halaman karier melalui portal Klob menampilkan daftar lowongan dan detail pekerjaan, termasuk posisi, perusahaan, lokasi, batas waktu aplikasi, deskripsi, serta persyaratan. Login diperlukan untuk melanjutkan proses melamar. |
  | 6 | Perbankan | BCA | Portal karier publik menyediakan pencarian dan filter lokasi, pengalaman, serta nama posisi. Daftar lowongan dan detail pekerjaan dapat dilihat tanpa login, termasuk kategori, bidang pekerjaan, periode, lokasi, deskripsi, dan persyaratan. |
  | 7 | Perbankan | Bank Mandiri | Halaman karier publik menampilkan kategori ODP, Banking Staff, Experienced Hire, dan CPDK. Informasi posisi, bidang pekerjaan, wilayah, deskripsi program, serta status lowongan dapat dilihat tanpa login. |
  | 8 | Manufaktur | Astra | Portal karier publik menampilkan 168 pekerjaan saat pemeriksaan. Tersedia filter perusahaan, fungsi, dan jenjang. Detail lowongan dapat dilihat tanpa login, termasuk nama posisi, perusahaan, fungsi, batas lamaran, deskripsi, dan persyaratan. |

- **Risiko:**
  1. Akses dan ketentuan penggunaan setiap career page berbeda-beda.
  2. Beberapa perusahaan tidak menampilkan lowongan saat pemeriksaan.
  3. Sebagian informasi rekrutmen hanya dapat dilanjutkan melalui login atau pendaftaran.
  4. Struktur halaman dan format data antarperusahaan tidak seragam.
  5. Izin automated scraping belum diverifikasi untuk seluruh perusahaan sehingga tidak dapat diasumsikan bahwa informasi publik boleh diambil secara otomatis.

- **Fallback:** pengumpulan informasi lowongan secara manual melalui halaman karier resmi perusahaan, kemudian memasukkan data yang relevan ke dalam dataset secara manual (unggah manual).

- **Hasil uji:**

  | Aspek pemeriksaan | Hasil |
  |---|---|
  | Jumlah perusahaan diperiksa | 8 perusahaan |
  | Akses halaman karier | Seluruh halaman yang diuji dapat diakses secara publik |
  | Daftar lowongan | Tersedia pada ANTAM, BCA, Bank Mandiri, dan Astra |
  | Detail pekerjaan | Berhasil diperiksa pada ANTAM, BCA, dan Astra |
  | Informasi kategori dan bidang pekerjaan | Tersedia pada beberapa portal, termasuk BCA, Bank Mandiri, dan Astra |
  | Informasi lokasi | Tersedia pada beberapa portal, termasuk ANTAM, BCA, Bank Mandiri, dan Astra |
  | Informasi keterampilan/persyaratan | Berhasil diperiksa pada ANTAM, BCA, dan Astra |
  | Informasi tanggal | Batas waktu aplikasi terlihat pada ANTAM, BCA, dan Astra; tanggal publikasi belum selalu tersedia |
  | Kebutuhan login | Tidak diperlukan untuk melihat informasi publik pada ANTAM, BCA, Bank Mandiri, dan Astra; jalur lowongan Pertamina yang diuji mengarah ke login |
  | Izin scraping otomatis | Belum diverifikasi secara menyeluruh |

  **Catatan:** Hasil pemeriksaan menunjukkan kondisi halaman pada tanggal 5 November 2026. Tidak ditemukannya lowongan pada suatu halaman hanya menggambarkan kondisi saat pengujian, bukan berarti perusahaan tidak membuka rekrutmen melalui kanal lain.

- **Keputusan:** PENDING — akses informasi publik berhasil diperiksa pada 8 perusahaan, tetapi izin automated scraping dan ketentuan legal masing-masing situs belum diverifikasi secara menyeluruh. Pengumpulan data secara manual dapat digunakan sebagai fallback sambil menunggu kepastian izin akses otomatis.

### 6. Bea Cukai (impor per HS code)
- **Target data:** impor per HS code, nilai, volume
- **Insight:** tren impor peralatan per sektor (turbin, server, mesin industri)
- **Cek Phase 0:** cara memperoleh data (portal, unduhan, API) dan granularitas HS code
- **Risiko:** akses & syarat legal
- **Fallback:** (isi rencana cadangan, mis. data agregat BPS)
- **Hasil uji:** (salin kolom dari blok 1)
- **Keputusan:** PENDING — alasan:

### 7. Existing news pipeline
- **Target data:** artikel tema Data Center/Cloud, AI/Data, Digital Transformation
- **Insight:** sector events (proyek baru, ekspansi, regulasi, investasi: tipe, sektor, nominal, wilayah)
- **Cek Phase 0:** tinjau output pipeline saat ini dan hitung persentase artikel relevan sector-event
- **Risiko:** akurasi tagging sector-event
- **Rencana Fase 2:** rules/keywords dulu, lalu pelabelan berbantuan LLM
- **Hasil uji:**
  - Tanggal & periode sampel:
  - Ukuran sampel (artikel):
  - Jumlah relevan sector-event / persentase:
  - Sebaran per event type (New Project / Expansion / Regulation / Investment):
  - Sebaran per sektor (indikatif):
  - Catatan kualitas (duplikat, sumber dominan):
- **Keputusan:** PENDING — alasan: (isi setelah persentase relevansi terukur)

### 8. IDX (Bursa Efek Indonesia)
- **Target data:** aksi korporasi, judul pengumuman, klasifikasi industri IDX, rasio keuangan
- **Insight:** pengumuman capex/ekspansi per sektor, distribusi ukuran perusahaan tercatat per sektor
- **Cek Phase 0:** uji endpoint, akses server, dan terms
- **Risiko:** pemblokiran akses oleh IDX
- **Fallback:** unduh manual berkala / unggah manual; atau NO-GO
- **Catatan:** tugas ini bisa dipindah ke Personel 1 (usulan mentor)
- **Hasil uji:**
  - Endpoint/halaman yang dicek:
  - Terms & robots.txt (ringkasan):
  - Respons server:
  - Bukti:
- **Keputusan:** PENDING — alasan:

### 9. Bank Indonesia / OJK
- **Target data:** kredit per sektor, pertumbuhan pinjaman
- **Insight:** sektor tujuan kredit dan momentum pembiayaan
- **Cek Phase 0:** temukan tabel credit-by-sector dan periksa format
- **Risiko:** format tabel sulit diolah / PDF
- **Fallback:** unduh Excel berkala / unggah manual
- **Catatan:** ingesti BI/OJK di Fase 2 dikerjakan Personel 1
- **Hasil uji:**
  - URL tabel & nama tabel:
  - Format (Excel/PDF/HTML) & frekuensi update:
  - Granularitas sektor (selaras KBLI?):
  - Ada API atau tidak:
- **Keputusan:** PENDING — alasan:

---

## 3. Checklist tambahan Phase 0
- [ ] Everyone: shared repo, struktur folder, source register template
- [ ] Everyone: common schema disepakati dan didokumentasikan di `docs/schema.md`
- [ ] Tim: draf 8–10 sektor prioritas
