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

### **4. Job portals (JobStreet, Indeed, dll.)**
- **Target data:** judul posisi, perusahaan, sektor, lokasi, tanggal posting, skills (tanpa data pribadi).
- **Insight:** total lowongan per sektor (ekspansi), porsi posisi IT/digital per sektor.
- **Cek Phase 0:** telah melakukan pengujian akses pada 3 portal lowongan kerja, yaitu JobStreet, Indeed, dan Glints Indonesia.

  **Hasil sementara per portal:**
  | No. | Portal | Hasil sementara |
  | --- | --- | --- |
  | 1 | JobStreet Indonesia | NO-GO — Terms of Service melarang agregasi, penyalinan konten, data mining, screen scraping, dan pengambilan data otomatis tanpa persetujuan tertulis. |
  | 2 | Indeed Indonesia | NO-GO — Terms of Service Bagian 21 melarang penggunaan bot, scraper, spider, AI, atau AI Agent untuk mengakses dan mengambil data tanpa izin tertulis. |
  | 3 | Glints Indonesia | NO-GO — Terms of Service Bagian 2 poin (h) melarang pengambilan dan ekstraksi data otomatis tanpa persetujuan tertulis. |

- **Risiko:** nilai potensi data tinggi, tetapi risiko penggunaan otomatis juga tinggi karena pembatasan Terms of Service, robots.txt, dan kemungkinan pemblokiran akses.

- **Fallback:** menggunakan career pages resmi perusahaan atau mengunggah data secara manual dari sumber yang penggunaannya diizinkan.

- **Hasil uji (per portal):**

  - **Portal / tanggal uji:**
    - JobStreet Indonesia — 5 November 2026.
    - Indeed Indonesia — 5 November 2026.
    - Glints Indonesia — 5 November 2026.

  - **robots.txt & ToS (ringkasan, izin scraping?):**
    - JobStreet: Terms melarang agregasi/penyalinan konten serta data mining, screen scraping, dan pengambilan data otomatis tanpa persetujuan tertulis. robots.txt memiliki aturan Disallow untuk sejumlah pola halaman lowongan, parameter pencarian, dan endpoint tertentu. **Scraping otomatis tanpa izin tidak diperbolehkan.**
    - Indeed: Bagian 21 Terms melarang penggunaan bot, scraper, spider, AI, atau AI Agent untuk mengakses dan mengambil data tanpa izin tertulis. robots.txt memiliki aturan Disallow untuk sejumlah pola halaman lowongan dan endpoint terkait. **Scraping otomatis tanpa izin tidak diperbolehkan.**
    - Glints: Bagian 2 poin (h) Terms melarang pencurian data, penambangan data, penggunaan robot, serta alat pengumpulan dan ekstraksi data serupa tanpa persetujuan tertulis. robots.txt memiliki aturan Disallow untuk sejumlah halaman rekomendasi, bookmark, halaman eksplorasi dengan parameter tertentu, dan endpoint tertentu. **Pengambilan data otomatis tanpa izin tertulis tidak diperbolehkan.**

  - **Respons server (HTTP code, captcha, rate limit):**
    - JobStreet: HTTP `200 OK` pada request utama halaman lowongan. CAPTCHA dan login tidak ditemukan saat pemeriksaan manual. Rate limit tidak diuji secara aktif.
    - Indeed: HTTP `200 OK` pada request utama halaman pencarian lowongan. CAPTCHA dan login tidak ditemukan saat pemeriksaan manual. Rate limit tidak diuji secara aktif.
    - Glints: HTTP `200 OK` pada request utama halaman detail lowongan. CAPTCHA dan login tidak ditemukan saat pemeriksaan manual. Rate limit tidak diuji secara aktif.
    - Ketiga portal berhasil diakses melalui browser. Pemeriksaan rate limit tidak dilakukan secara aktif untuk menghindari request berulang yang berpotensi melanggar ketentuan penggunaan.

  - **Field yang tersedia:**
    - JobStreet: judul posisi, perusahaan, klasifikasi pekerjaan, lokasi, tanggal posting, skills/kualifikasi, jenis pekerjaan, dan kisaran gaji pada contoh lowongan yang diperiksa.
    - Indeed: judul posisi, perusahaan, lokasi, kisaran gaji, tipe pekerjaan, deskripsi pekerjaan, pendidikan, pengalaman, skills, dan kualifikasi pada contoh lowongan yang diperiksa. Tanggal posting belum terlihat pada contoh yang diperiksa.
    - Glints: judul posisi, perusahaan, kategori pekerjaan, lokasi, tanggal relatif posting, kisaran gaji, tipe pekerjaan, sistem kerja, pendidikan, pengalaman, skills, persyaratan, deskripsi pekerjaan, serta informasi profil perusahaan pada contoh lowongan yang diperiksa.

  - **Bukti:**
    - JobStreet: `docs/images/person-2/test-hiring-access/jobstreet/`
    - Indeed: `docs/images/person-2/test-hiring-access/indeed_id/`
    - Glints: `docs/images/person-2/test-hiring-access/glints/`

- **Keputusan:**
  - JobStreet: **NO-GO** untuk scraping otomatis tanpa izin karena pembatasan dalam Terms of Service.
  - Indeed: **NO-GO** untuk scraping otomatis tanpa izin karena pembatasan dalam Terms of Service dan aturan robots.txt.
  - Glints: **NO-GO** untuk pengambilan data otomatis tanpa persetujuan tertulis karena pembatasan dalam Terms of Service dan aturan robots.txt.
  - Pengujian akses manual berhasil pada ketiga portal dengan HTTP `200 OK`. Field target tersedia pada contoh lowongan yang diperiksa. Namun, keberhasilan akses manual tidak berarti scraping otomatis diperbolehkan.
  - **Fallback:** menggunakan career pages resmi perusahaan atau unggah data secara manual dari sumber yang penggunaannya diizinkan.

### **5. Career pages perusahaan besar**

- **Target data:** kolom sama dengan job portals, meliputi nama posisi (role title), nama perusahaan (company), sektor (sector), lokasi (location), tanggal publikasi (post date), dan keterampilan yang dibutuhkan (skills).

- **Insight:** cross-check data lowongan dari job portals dengan informasi rekrutmen resmi perusahaan untuk memvalidasi kebutuhan tenaga kerja, tren perekrutan, dan permintaan posisi digital/IT di masing-masing sektor.

- **Cek Phase 0:** telah meninjau 8 perusahaan besar dari sektor energi, pertambangan, perbankan, dan manufaktur.

  **Daftar perusahaan yang diperiksa:**

  | No. | Perusahaan | Sektor | Hasil sementara |
  | --- | --- | --- | --- |
  | 1 | PLN | Energi | PENDING — halaman rekrutmen dapat diakses, tetapi tidak ada lowongan ditampilkan saat pemeriksaan. |
  | 2 | Pertamina | Energi | PENDING — website e-Recruitment dapat diakses, tetapi jalur informasi lowongan yang diuji mengarah ke login. |
  | 3 | MIND ID | Pertambangan | PENDING — portal karier dapat diakses, tetapi tidak ada lowongan ditemukan saat pemeriksaan. |
  | 4 | Freeport Indonesia | Pertambangan | PENDING — halaman karier dapat diakses, tetapi tidak ada lowongan tersedia saat pemeriksaan. |
  | 5 | ANTAM | Pertambangan | GO — daftar dan detail lowongan dapat diakses publik tanpa login. |
  | 6 | BCA | Perbankan | GO — daftar dan detail lowongan dapat dilihat tanpa login, termasuk posisi, kategori, lokasi, periode, deskripsi, dan persyaratan. |
  | 7 | Bank Mandiri | Perbankan | GO — kategori rekrutmen, nama posisi, bidang pekerjaan, wilayah, deskripsi program, dan status lowongan dapat dilihat tanpa login. |
  | 8 | Astra | Manufaktur | GO — daftar 168 pekerjaan dan detail lowongan dapat diakses tanpa login, termasuk posisi, perusahaan, fungsi, batas lamaran, deskripsi, dan persyaratan. |

- **Risiko:**

  1. Akses dan ketentuan penggunaan setiap career page berbeda-beda.
  2. Beberapa perusahaan tidak menampilkan lowongan saat pemeriksaan.
  3. Sebagian informasi rekrutmen hanya dapat dilanjutkan melalui login atau pendaftaran.
  4. Struktur halaman dan format data antarperusahaan tidak seragam.
  5. Izin automated scraping belum diverifikasi untuk seluruh perusahaan sehingga tidak dapat diasumsikan bahwa informasi publik boleh diambil secara otomatis.

- **Fallback:** pengumpulan informasi lowongan secara manual melalui halaman karier resmi perusahaan, kemudian memasukkan data yang relevan ke dalam dataset secara manual (unggah manual).

- **Hasil uji:**

  | Aspek pemeriksaan | Hasil |
  | --- | --- |
  | Jumlah perusahaan diperiksa | 8 perusahaan |
  | Akses halaman karier | Seluruh halaman yang diuji dapat diakses secara publik |
  | Daftar lowongan | Ditemukan pada ANTAM, BCA, Bank Mandiri, dan Astra |
  | Detail pekerjaan | Berhasil diperiksa pada ANTAM, BCA, dan Astra |
  | Informasi kategori dan bidang pekerjaan | Tersedia pada beberapa portal, termasuk BCA, Bank Mandiri, dan Astra |
  | Informasi lokasi | Tersedia pada beberapa portal, termasuk ANTAM, BCA, Bank Mandiri, dan Astra |
  | Informasi keterampilan/persyaratan | Berhasil diperiksa pada ANTAM, BCA, dan Astra |
  | Informasi tanggal | Batas waktu aplikasi terlihat pada ANTAM, BCA, dan Astra; tanggal publikasi belum selalu tersedia |
  | Kebutuhan login | Informasi publik dapat dilihat tanpa login pada ANTAM, BCA, Bank Mandiri, dan Astra; jalur lowongan Pertamina yang diuji mengarah ke login |
  | Izin scraping otomatis | Belum diverifikasi secara menyeluruh |

  **Catatan:** Hasil pemeriksaan menunjukkan kondisi halaman pada tanggal 5 November 2026. Status PENDING pada PLN, Pertamina, MIND ID, dan Freeport bukan berarti scraping dilarang, tetapi informasi lowongan yang dibutuhkan belum berhasil diverifikasi secara lengkap. Status GO pada ANTAM, BCA, Bank Mandiri, dan Astra hanya menunjukkan keberhasilan akses informasi publik, bukan izin automated scraping.

- **Keputusan:** PENDING — pemeriksaan akses informasi publik berhasil dilakukan pada 8 perusahaan. ANTAM, BCA, Bank Mandiri, dan Astra dapat digunakan sebagai referensi lowongan publik, sedangkan PLN, Pertamina, MIND ID, dan Freeport masih memerlukan pemeriksaan lanjutan. Izin automated scraping dan ketentuan legal masing-masing situs belum diverifikasi secara menyeluruh. Pengumpulan data manual dapat digunakan sebagai fallback.

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
