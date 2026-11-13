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
  - Tanggal uji: 6 November 2026 (https://www.bps.go.id/id/statistics-table/2/MjI2OCMy/-seri-2010--pdrb-triwulanan-atas-dasar-harga-berlaku-menurut-lapangan-usaha-di-provinsi-seluruh-indonesia--milyar-rupiah-.html)
  - Metode akses: Penelusuran portal webAPI BPS, pembuatan akun developer, dan pendaftaran aplikasi. Uji coba penarikan data via skrip Python belum dieksekusi.
  - Format data: JSON/XML (berdasarkan dokumentasi).
  - Granularitas sektor: KBLI level 1 dan 2.
  - Syarat penggunaan / lisensi: Membutuhkan registrasi API Key gratis. ToS secara tegas melarang penempatan API Key pada repositori publik (harus diamankan menggunakan file `.env`).
  - Respons server / kendala akses: Portal API lancar diakses.
  - Bukti: Tangkapan layar portal webAPI BPS dan dokumen Terms of Use.
- **Keputusan:** **PENDING** — Alasan: Pengecekan skrip ekstraksi baru akan dilakukan setelah checkpoint, namun kemungkinan besar berstatus GO karena ToS mengizinkan akses selama API Key diamankan menggunakan file `.env`.

### 2. BKPM / Kementerian Investasi
- **Target data:** realisasi investasi (domestik & asing) per sektor dan wilayah, jumlah proyek
- **Insight:** aliran komitmen modal, momentum sektor
- **Cek Phase 0:** ada API, bulk download, atau hanya tabel publikasi
- **Risiko:** data hanya PDF/tabel
- **Fallback:** unduh tabel berkala / unggah manual
- **Hasil uji:** 
  - Tanggal uji: 5 November 2026 (https://bkpm.go.id/id/info/realisasi-investasi)
  - Metode akses: Mengakses web BKPM dan mengunduh rilis "Capaian Realisasi Investasi" terbaru.
  - Format data: File unduhan berupa dokumen PDF presentasi bergambar / infografis, bukan tabel mentah.
  - Granularitas sektor: Sektor prioritas investasi.
  - Syarat penggunaan / lisensi: Data publik terbuka.
  - Respons server / kendala akses: Tidak ada API.
  - Bukti: Tangkapan layar dokumen PDF presentasi BKPM (infografis).
- **Keputusan:** **GO-MANUAL** — Alasan: Format PDF infografis sangat berisiko tinggi (*high risk*) menyebabkan *error* jika teksnya diekstrak oleh skrip otomatis karena tata letak visualnya tidak beraturan, sehingga angka harus disalin manual ke CSV oleh tim.

### 3. Regulator umum (DPR / MK / Energi)
- **Target data:** regulasi bisnis baru, arah kebijakan yang akan diatur
- **Insight:** fokus pemerintah, syarat kepatuhan, potensi bisnis baru
- **Cek Phase 0:** cari regulasi baru yang bisa diunduh atau di-scrape
- **Risiko:** dokumen berupa PDF
- **Fallback:** kurasi manual daftar regulasi
- **Hasil uji:** 
  - Tanggal uji: 5 November 2026 (https://jdihn.go.id/)
  - Metode akses: Mengakses portal JDIHN dan mengunduh sampel dokumen regulasi.
  - Format data: Dokumen hukum berupa teks PDF murni yang tebal.
  - Granularitas sektor: Bergantung pada penafsiran manual per regulasi.
  - Syarat penggunaan / lisensi: Dokumen negara, domain publik.
  - Respons server / kendala akses: -
  - Bukti: Tangkapan layar dokumen JDIHN.
- **Keputusan:** **GO-MANUAL** — Alasan: Skrip otomatis (mesin) belum memiliki nalar untuk menyimpulkan sentimen kebijakan (mendukung/menghambat sektor tertentu) secara akurat dari teks hukum tebal, sehingga tetap membutuhkan kurasi dan interpretasi manusia untuk dimasukkan ke CSV.

### **4. Job Portals (JobStreet, Indeed, dll.)**

- **Target data:** judul posisi, perusahaan, sektor, lokasi, tanggal posting, dan skills (tanpa data pribadi).
- **Insight:** total lowongan per sektor (ekspansi) dan porsi posisi IT/digital per sektor.
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
    - Glints: Bagian 2 poin (h) Terms melarang penggunaan screen scraping, data mining, robot, serta alat pengumpulan dan ekstraksi data serupa tanpa persetujuan tertulis. robots.txt memiliki aturan Disallow untuk sejumlah halaman rekomendasi, bookmark, halaman eksplorasi dengan parameter tertentu, dan endpoint tertentu. **Pengambilan data otomatis tanpa izin tertulis tidak diperbolehkan.**

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

### **4.1 Tautan Referensi Resmi Job Portals**

Tautan berikut digunakan sebagai referensi untuk memeriksa halaman lowongan, ketentuan penggunaan (Terms of Service), dan aturan robots.txt masing-masing portal.

| No. | Portal | Halaman Lowongan | Terms of Service | robots.txt |
| --- | --- | --- | --- | --- |
| 1 | JobStreet Indonesia | [Halaman Lowongan](https://id.jobstreet.com/id/id-jobs) | [Terms of Service](https://id.jobstreet.com/id/terms) | [robots.txt](https://id.jobstreet.com/robots.txt) |
| 2 | Indeed Indonesia | [Halaman Lowongan](https://id.indeed.com/jobs) | [Ketentuan Layanan](https://id.indeed.com/legal?hl=in) | [robots.txt](https://id.indeed.com/robots.txt) |
| 3 | Glints Indonesia | [Halaman Lowongan](https://glints.com/id/opportunities/jobs/explore?countries=id) | [Terms of Use](https://glints.com/id/about/terms) | [robots.txt](https://glints.com/robots.txt) |

### **4.2 LinkedIn — Hiring & Company Intelligence**

- **Target data:**
  - **LinkedIn Jobs:** judul posisi, perusahaan, sektor, lokasi, tanggal posting, jenis pekerjaan, sistem kerja (Remote/Hybrid/On-site), deskripsi pekerjaan, kualifikasi, dan skills.
  - **LinkedIn Company Feeds:** nama perusahaan, tanggal posting, isi posting, topik, URL posting, serta informasi interaksi (jumlah likes, komentar, dan repost jika terlihat).
  - **LinkedIn Company Profile:** nama perusahaan, industri, lokasi, jumlah pengikut, rentang jumlah karyawan, dan deskripsi perusahaan.
  - Tidak mengambil data pribadi pengguna LinkedIn.

- **Insight:**
  - Total lowongan per sektor untuk melihat indikasi ekspansi perusahaan.
  - Porsi posisi IT/digital pada setiap sektor.
  - Tren skills yang paling banyak dibutuhkan perusahaan.
  - Aktivitas dan perkembangan perusahaan berdasarkan postingan.
  - Identifikasi tren teknologi, ekspansi bisnis, perekrutan, dan investasi perusahaan.

- **Cek Phase 0:** telah melakukan pengujian akses terhadap LinkedIn Jobs, LinkedIn Company Profile, dan LinkedIn Company Feeds menggunakan akun LinkedIn pribadi yang sudah login.

  **Hasil sementara:**

  | No. | Komponen | Hasil sementara |
  | --- | --- | --- |
  | 1 | LinkedIn Jobs | GO — halaman pencarian dan detail lowongan berhasil diakses secara manual menggunakan akun yang sudah login. |
  | 2 | LinkedIn Company Feeds | GO — postingan perusahaan dan informasi interaksi berhasil diamati secara manual. |
  | 3 | LinkedIn Company Profile | GO — profil perusahaan Shopee berhasil dibuka dan diamati. |
  | 4 | Scraping otomatis | NO-GO — tanpa izin resmi LinkedIn, pengambilan data otomatis tidak diperbolehkan. |
  | 5 | API resmi | NO-GO (sementara) — belum dilakukan pengujian API secara langsung dan akses API untuk kebutuhan proyek belum diperoleh. |
  | 6 | robots.txt | NO-GO — berdasarkan pemeriksaan robots.txt, penggunaan robot atau metode otomatis tanpa izin resmi dibatasi. |

- **Risiko:** nilai potensi data tinggi karena LinkedIn menyediakan informasi lowongan pekerjaan, profil perusahaan, dan aktivitas bisnis. Namun, risiko penggunaan otomatis tinggi karena pembatasan Terms of Service, aturan robots.txt, serta persyaratan akses API LinkedIn.

- **Fallback:** menggunakan career pages resmi perusahaan, sumber berita perusahaan yang mengizinkan pengambilan data otomatis, atau data yang diperoleh melalui API maupun izin resmi.

- **Hasil uji:**

  - **Portal / tanggal uji:**
    - LinkedIn Jobs — 10 November 2026.
    - LinkedIn Company Profile (Shopee) — 10 November 2026.
    - LinkedIn Company Feeds (Shopee) — 10 November 2026.
    - LinkedIn Developer Portal — 10 November 2026.
    - LinkedIn API Products — 10 November 2026.
    - Chrome DevTools Network — 10 November 2026.
    - LinkedIn robots.txt — 10 November 2026.

  - **Terms of Service (ringkasan, izin scraping?):**
    - LinkedIn User Agreement Bagian 8.2 membatasi penggunaan software, script, robot, crawler, browser plugin, dan teknologi otomatis lainnya untuk melakukan scraping atau menyalin data dari layanan LinkedIn tanpa izin.
    - Ketentuan tersebut menjadi dasar bahwa scraping otomatis tanpa izin resmi LinkedIn tidak diperbolehkan.
    - **Kesimpulan: scraping otomatis tanpa izin resmi LinkedIn tidak diperbolehkan.**

  - **robots.txt (aturan crawling):**
    - LinkedIn: file `https://www.linkedin.com/robots.txt` berhasil dibuka dan diperiksa.
    - Pada bagian awal file terdapat pemberitahuan bahwa penggunaan robot atau metode otomatis untuk mengakses LinkedIn tanpa izin resmi dilarang.
    - LinkedIn menyediakan mekanisme pengajuan izin crawling melalui email `whitelist-crawl@linkedin.com`.
    - File robots.txt memiliki aturan berbeda untuk sejumlah User-agent crawler. Aturan perlu dibaca sesuai User-agent yang digunakan.
    - **Pengambilan data otomatis tanpa izin resmi LinkedIn tidak diperbolehkan.**
    - Pemeriksaan dilakukan terhadap file robots.txt, bukan pengujian crawling langsung ke halaman Jobs atau Company Feeds.

  - **Respons server (HTTP code, CAPTCHA, rate limit):**
    - LinkedIn Jobs: halaman pencarian lowongan berhasil dibuka menggunakan akun LinkedIn pribadi yang sudah login.
    - LinkedIn Company Profile: halaman profil perusahaan Shopee berhasil dibuka menggunakan akun yang sama.
    - LinkedIn Company Feeds: postingan perusahaan dan informasi interaksi dapat diamati.
    - Selama pengujian manual tidak ditemukan CAPTCHA yang menghalangi akses halaman.
    - HTTP status code halaman dan rate limit belum diuji secara khusus.
    - Pemeriksaan Network menemukan dua request dengan status `200 OK (from disk cache)`. Status tersebut merupakan respons dari cache browser, bukan bukti keberhasilan pengambilan data lowongan.
    - Tidak dilakukan percobaan bypass login, CAPTCHA, pembatasan akses, maupun rate limit.

  - **Pemeriksaan API melalui Chrome DevTools:**
    - Pemeriksaan dilakukan melalui tab Network dengan filter Fetch/XHR pada browser Google Chrome.
    - Ditemukan request `voyager-web-jobs` dengan URL `https://platform.linkedin.com/litms/allowlist/voyager-web-jobs`. Request menggunakan metode GET, memiliki status `200 OK (from disk cache)`, dan Content-Type `application/json`. Request ini merupakan konfigurasi allowlist, bukan endpoint yang terbukti mengembalikan data lowongan.
    - Ditemukan request `voyager-web-global` dengan URL `https://platform.linkedin.com/litms/allowlist/voyager-web-global`. Request menggunakan metode GET, memiliki status `200 OK (from disk cache)`, dan Content-Type `application/json`. Request ini merupakan konfigurasi allowlist global.
    - Kedua request berhasil ditemukan, tetapi tidak memberikan bukti bahwa data Jobs atau Company Feeds berhasil diperoleh melalui API.
    - **Hasil: belum ditemukan endpoint API yang terbukti dapat digunakan untuk mengambil data lowongan atau postingan perusahaan.**

  - **Pemeriksaan LinkedIn Developer Portal:**
    - Halaman LinkedIn Developer Portal berhasil dibuka.
    - Halaman API Products berhasil diakses.
    - Halaman My Apps dan formulir Create an App berhasil dibuka.
    - Formulir pembuatan aplikasi belum diisi dan aplikasi belum dibuat.
    - Belum dilakukan autentikasi OAuth maupun pengujian pemanggilan API resmi.
    - **Hasil: pemeriksaan portal berhasil, tetapi akses API belum diperoleh dan belum diuji secara langsung.**

  - **Field yang tersedia:**
    - LinkedIn Jobs: judul posisi, perusahaan, lokasi, tanggal atau waktu relatif posting, jenis pekerjaan, sistem kerja, deskripsi pekerjaan, kualifikasi, dan skills pada contoh lowongan yang diperiksa.
    - LinkedIn Company Profile: nama perusahaan, industri, lokasi, jumlah pengikut, rentang jumlah karyawan, deskripsi perusahaan, dan website pada profil yang diperiksa.
    - LinkedIn Company Feeds: nama perusahaan, tanggal relatif posting, isi postingan, topik, URL postingan, serta jumlah likes, komentar, dan repost jika terlihat.
    - Field tersebut merupakan hasil pengamatan manual dan belum diperoleh melalui API.

  - **Bukti:**
    - LinkedIn Jobs: `docs/images/person-2/test-hiring-access/linkedin/`
    - LinkedIn Company Profile: `docs/images/person-2/test-hiring-access/linkedin/`
    - LinkedIn Company Feeds: `docs/images/person-2/test-hiring-access/linkedin/`
    - Pemeriksaan Network: `docs/images/person-2/test-hiring-access/linkedin/`
    - Pemeriksaan robots.txt: `docs/images/person-2/test-hiring-access/linkedin/`

- **Keputusan:**
  - LinkedIn Jobs: **GO** untuk akses dan observasi manual, tetapi belum berhasil memperoleh akses API untuk mengambil data lowongan.
  - LinkedIn Company Feeds: **GO** untuk akses dan observasi manual, tetapi API resmi belum diuji secara langsung.
  - LinkedIn Company Profile: **GO** untuk akses dan observasi manual, tetapi API resmi belum diuji secara langsung.
  - Scraping otomatis: **NO-GO** tanpa izin resmi LinkedIn karena pembatasan dalam Terms of Service.
  - robots.txt: **NO-GO** untuk crawling otomatis tanpa izin resmi LinkedIn.
  - API resmi: **NO-GO (sementara)** karena belum dilakukan pengujian autentikasi OAuth maupun pemanggilan API resmi, dan akses API untuk kebutuhan proyek belum diperoleh.
  - Pemeriksaan Network berhasil menemukan dua request konfigurasi allowlist, tetapi belum menemukan endpoint yang terbukti dapat digunakan untuk mengambil data Jobs maupun Company Feeds.
  - Pengujian akses manual berhasil menggunakan akun LinkedIn pribadi yang sudah login. Namun, keberhasilan akses manual tidak berarti scraping otomatis diperbolehkan.
  - **Fallback:** menggunakan career pages resmi perusahaan atau sumber berita dan platform lain yang mengizinkan pengambilan data otomatis.

### **4.2.1 Tautan Referensi LinkedIn**

Tautan berikut merupakan halaman yang telah digunakan dalam pemeriksaan LinkedIn pada Phase 0.

| No. | Komponen | Tautan |
| --- | --- | --- |
| 1 | LinkedIn Jobs | [Halaman Lowongan](https://www.linkedin.com/jobs/) |
| 2 | LinkedIn Company Page | [Shopee Company Page](https://www.linkedin.com/company/shopee/) |
| 3 | LinkedIn Developer Portal | [Developer Portal](https://www.linkedin.com/developers/) |
| 4 | LinkedIn API Products | [API Products](https://developer.linkedin.com/product-catalog) |
| 5 | LinkedIn User Agreement | [Terms of Service](https://www.linkedin.com/legal/user-agreement) |
| 6 | LinkedIn robots.txt | [robots.txt](https://www.linkedin.com/robots.txt) |
---

### **5. Career Pages Perusahaan Besar**

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

### **5.1 Tautan Referensi Resmi Career Pages**

Tautan berikut merupakan halaman karier atau portal rekrutmen resmi perusahaan yang diperiksa selama pengujian Phase 0.

| No. | Perusahaan | Sektor | Tautan Career Page |
| --- | --- | --- | --- |
| 1 | PLN | Energi | [PLN Recruitment](https://rekrutmen.pln.co.id/) |
| 2 | Pertamina | Energi | [Pertamina e-Recruitment](https://recruitment.pertamina.com/) |
| 3 | MIND ID | Pertambangan | [MIND ID Career](https://mind.id/pages/karir) · [Portal Rekrutmen Grup MIND ID](https://career.mind.id/) |
| 4 | Freeport Indonesia | Pertambangan | [Freeport Indonesia Career](https://ptfi.co.id/index.php/en/career?kat=2) |
| 5 | ANTAM | Pertambangan | [ANTAM Experience Hire 2026 — Portal KLOB](https://www.klob.id/experiencehireANTAM2026/vacancies) |
| 6 | BCA | Perbankan | [BCA Karir](https://karir.bca.co.id/) |
| 7 | Bank Mandiri | Perbankan | [Mandiri Career](https://www.bankmandiri.co.id/mandiri-career) |
| 8 | Astra | Manufaktur | [Astra Career — Lowongan](https://career.astra.co.id/lowongan) |

**Catatan Referensi:**
- Tautan di atas merupakan referensi halaman resmi atau portal rekrutmen yang digunakan untuk pemeriksaan.
- Status GO dan PENDING tetap mengacu pada hasil pengujian tanggal 5 November 2026, bukan kondisi lowongan saat tautan dibuka di kemudian hari.
- Tautan career page yang dapat diakses publik tidak otomatis memberikan izin untuk melakukan scraping otomatis.
- Ketentuan penggunaan dan izin pengambilan data otomatis masing-masing perusahaan masih perlu diperiksa secara terpisah.

## 6. Bea Cukai & INSW — Penilaian Akses Data Impor

### Tujuan
Menyelidiki apakah data impor Indonesia dapat diakses melalui platform resmi Bea Cukai atau INSW, termasuk akses portal, ketersediaan dataset yang dapat diunduh, ketersediaan API, serta tingkat kedalaman klasifikasi HS Code.

### 6.1 Hasil Pengujian Akses

| No. | Sumber / Platform | Hasil Pengujian Akses | Data yang Tersedia | Status |
|---|---|---|---|---|
| 1 | Bea Cukai — Portal Pengguna Jasa (CEISA) | Portal memerlukan registrasi dan autentikasi pengguna. Fitur Browse Data PIB ditujukan bagi pengguna untuk memantau dokumen kepabeanan milik mereka sendiri. | Informasi PIB milik pengguna dan status layanan kepabeanan. | PENDING |
| 2 | Bea Cukai — CEISA Open API | Dokumentasi API resmi tersedia. Akses memerlukan pengguna jasa CEISA yang telah terdaftar serta kredensial yang sesuai. | Dokumen kepabeanan, status dokumen, larangan dan pembatasan, nilai tukar, manifes, serta layanan tarif. | PENDING |
| 3 | Bea Cukai — Statistik Resmi | Halaman statistik publik dapat diakses. Halaman yang diuji terutama menyediakan statistik penerimaan dan penerimaan pajak impor. | Statistik penerimaan dan pajak impor, bukan rincian nilai serta kuantitas transaksi impor berdasarkan HS Code. | NO-GO |
| 4 | INSW — INTR (Indonesia National Trade Repository) | Pencarian HS Code dan halaman detail komoditas dapat diakses secara publik tanpa login. | Klasifikasi HS, informasi tarif, regulasi impor, larangan dan pembatasan, serta referensi komoditas. | GO — Hanya untuk Data Referensi |
| 5 | INSW — Informasi Publik | Halaman informasi publik dan pencarian dokumen dapat diakses. Pencarian menggunakan kata kunci "impor" dan "statistik" tidak menemukan dataset transaksi impor secara terperinci. | Dokumen informasi publik, regulasi, dan informasi kelembagaan. | NO-GO — Berdasarkan Pengujian Saat Ini |
| 6 | Bea Cukai — PPID | Prosedur resmi permohonan informasi publik tersedia melalui e-PPID Kemenkeu, email, atau pengajuan langsung. Belum ada permohonan yang diajukan. | Potensi memperoleh informasi kepabeanan yang diminta, bergantung pada ketersediaan data dan persetujuan. | PENDING |

### 6.2 Pengujian Tingkat Kedalaman HS Code

Pengujian pencarian HS Code publik dilakukan melalui INSW INTR dengan menggunakan kode HS `8471`.

Hasil pencarian menunjukkan tingkatan klasifikasi sebagai berikut:

| Tingkat HS | HS Code | Deskripsi |
|---|---|---|
| 4 digit | 8471 | Mesin pengolah data otomatis dan unitnya |
| 6 digit | 847130 | Mesin pengolah data otomatis portabel dengan berat tidak lebih dari 10 kg |
| 8 digit | 84713020 | Laptop, termasuk notebook dan subnotebook |

Halaman detail HS Code juga menampilkan:
- Deskripsi komoditas dalam Bahasa Indonesia dan Bahasa Inggris.
- Informasi bea masuk dan pajak.
- Regulasi impor dan larangan serta pembatasan.
- Dokumen yang dipersyaratkan dan regulasi yang berlaku.
- Satuan barang atau satuan pengukuran komoditas.

**Temuan:** Informasi klasifikasi HS Code publik berhasil dikonfirmasi hingga 8 digit untuk komoditas yang diuji. Hal ini membuktikan tingkat kedalaman klasifikasi data referensi, bukan ketersediaan statistik transaksi impor pada tingkat yang sama.

### 6.3 Penilaian Permohonan Informasi melalui PPID

Situs resmi Bea Cukai menyediakan prosedur permohonan informasi publik melalui PPID Pelaksana DJBC.

Saluran pengajuan permohonan yang tersedia:
1. Pengajuan digital melalui e-PPID Kemenkeu.
2. Mengunduh formulir permohonan dan mengirimkannya melalui email ke `ppid.beacukai@kemenkeu.go.id`.
3. Pengajuan secara langsung ke Kantor Pusat DJBC melalui loket Pelayanan Terpadu Satu Pintu (PTSP).

Prosedur yang dipublikasikan menyebutkan bahwa:
- Identitas pemohon harus diverifikasi.
- Persyaratan yang belum lengkap dapat dilengkapi dalam waktu 3 hari kerja.
- Pemberitahuan tertulis awal diberikan paling lambat 10 hari kerja.
- Jangka waktu tersebut dapat diperpanjang selama 7 hari kerja berikutnya.

Belum ada permohonan informasi resmi yang diajukan selama pengujian ini.

### 6.4 Klarifikasi Data yang Dibutuhkan

Informasi berikut masih perlu dikonfirmasi kepada PPID DJBC:

- Apakah data agregat impor Indonesia tersedia berdasarkan HS Code 8 digit.
- Apakah data mencakup periode bulanan atau tahunan.
- Apakah tersedia informasi nilai dan kuantitas/volume impor.
- Apakah data historis dapat diberikan.
- Apakah data dapat disediakan dalam format CSV atau Excel.
- Apakah data dapat digunakan untuk keperluan penelitian dan analisis.

### 6.5 Bukti Pengujian

Bukti screenshot disimpan di dalam folder:

`docs/images/person-2/bea-cukai/`

Bukti yang didokumentasikan meliputi:
- Akses Portal Pengguna Jasa CEISA dan persyaratan registrasi.
- Dokumentasi CEISA Open API.
- Statistik resmi Bea Cukai.
- Hasil pencarian HS Code melalui INSW INTR.
- Detail komoditas HS Code 8 digit.
- Informasi tarif dan regulasi impor.
- Hasil pencarian informasi publik INSW.
- Prosedur permohonan informasi publik PPID Bea Cukai.
- Dokumen Daftar Informasi Publik PPID Kemenkeu, termasuk pemeriksaan informasi INTR dan dwelling time.

### 6.6 Tautan Referensi Resmi

| No. | Sumber / Platform | Tautan Referensi |
|---|---|---|
| 1 | Bea Cukai — Portal Pengguna Jasa (CEISA) | [Portal Pengguna Jasa](https://customer.beacukai.go.id/index.html?pages=browse-data-pib) · [Persyaratan Pengguna](https://customer.beacukai.go.id/index.html?page=requirement) |
| 2 | Bea Cukai — CEISA Open API | [Developer Portal CEISA](https://openapi.beacukai.go.id/) |
| 3 | Bea Cukai — Statistik Resmi | [Statistik Penerimaan Bea Cukai](https://beacukai.go.id/statistik-penerimaan) |
| 4 | INSW — INTR | [Indonesia National Trade Repository](https://www.insw.go.id/intr) |
| 5 | INSW — Informasi Publik | [Website INSW](https://www.insw.go.id/) · [Informasi Publik Tersedia Setiap Saat](https://insw.go.id/tersedia-setiap-saat) |
| 6 | Bea Cukai — PPID | [Permintaan Informasi Publik DJBC](https://www.beacukai.go.id/permintaan-informasi) · [Halaman Utama PPID DJBC](https://beacukai.go.id/halaman-utama-ppid) |

**Dokumen Pendukung:**
- [Keputusan PPID Kemenkeu Nomor KEP-4/PPID/2026 (PDF)](https://api.insw.go.id/assets/upload/cms/1790321106935_cms.pdf)

### 6.7 Penilaian dan Alternatif Sumber Data

**Penilaian saat ini: PENDING untuk data transaksi impor.**

Informasi referensi HS Code publik dapat diakses melalui INSW INTR. Namun, akses publik terhadap statistik transaksi impor secara terperinci berdasarkan HS Code 8 digit belum berhasil dikonfirmasi.

Langkah selanjutnya:
- Meminta klarifikasi kepada PPID DJBC mengenai ketersediaan data agregat impor.
- Jika data yang dibutuhkan tidak tersedia atau akses tidak diberikan, mencari sumber statistik impor alternatif lainnya yang resmi dan memiliki izin penggunaan.

Tidak ada proses web scraping otomatis maupun pengajuan permohonan informasi resmi yang dilakukan selama pengujian ini.

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
- **Keputusan:** PENDING — alasan: (Untuk bagian Alfin dan Arza udah di uji coba dan relevan dan untuk punya atha masih di uji namun hasilnya masih lebih banyak non relevan)

### 8. IDX (Bursa Efek Indonesia)
- **Target data:** Pergerakan harga saham, valuasi, dan kinerja sektor (IDX-IC)
- **Insight:** Sentimen pasar dan pertumbuhan valuasi bisnis per sektor
- **Cek Phase 0:** test the endpoints, server access and terms
- **Risiko:** Pemblokiran IP, pembatasan akses server, dan pelanggaran lisensi komersial
- **Fallback:** Gunakan API Yahoo Finance (`yfinance`) untuk data pasar saham emiten Indonesia (menggunakan suffix `.JK`).
- **Hasil uji:**
  - Tanggal uji: 4 November 2026 (https://data.idx.co.id/catalog_product2.php)
  - Endpoints & Server access: Tidak ada *public REST API* gratis. API internal web IDX memblokir akses dari *automated script* (Airflow/Python) melalui sistem proteksi anti-scraping.
  - Terms: API resmi (IDX Data Services) berbayar/premium (USD 550 - USD 2,100). Scraping tidak direkomendasikan karena menyalahi *Terms of Service* (ToS).
  - Pengujian Fallback: Library `yfinance` terbukti dapat menarik data OHLC (Open, High, Low, Close) emiten BEI secara bebas tanpa kendala otentikasi.
  - Bukti: Tangkapan layar katalog harga API komersial IDX Data Services.
- **Keputusan:** **NO-GO** (untuk API resmi) / **GO** (menggunakan Fallback) — Alasan: Akses web resmi terkendala sistem anti-scraping dan API resmi IDX merupakan lisensi berbayar/komersial. Sebagai gantinya, berstatus GO menggunakan library Yahoo Finance sebagai fallback utama di Fase 2.

### 9. Bank Indonesia / OJK
- **Target data:** kredit per sektor, pertumbuhan pinjaman
- **Insight:** sektor tujuan kredit dan momentum pembiayaan
- **Cek Phase 0:** temukan tabel credit-by-sector dan periksa format
- **Risiko:** format tabel sulit diolah / PDF
- **Fallback:** unduh Excel berkala / unggah manual
- **Catatan:** Ingesti BI/OJK di Fase 2 dikerjakan Personel 3 (Alfin).
- **Hasil uji:**
  - Tanggal uji: 4 November 2026 (https://www.bi.go.id/id/statistik/ekonomi-keuangan/seki/default.aspx) (https://data.ojk.go.id/SJKPublic/Dataset/Dataset/Dataset/340)
  - Metode akses: Mengunduh file ZIP SEKI dari web BI secara manual, dan memfilter Sektor Ekonomi di dashboard SJK publik OJK.
  - Format data: Setelah ZIP diekstrak, format data adalah Excel murni (.xls / .xlsx) yang diperbarui bulanan (Time-Series Cumulative).
  - Granularitas sektor: KBLI Level 1 (Pertanian, Pertambangan, Industri Pengolahan, dll).
  - Syarat penggunaan / lisensi: Data publik resmi, bebas digunakan.
  - Respons server / kendala akses: Tidak ada API publik yang tersedia, sehingga penarikan awal harus diunduh manual.
  - Bukti: Skrip `spikes/cek_seki_bi.py` yang berhasil mengekstrak data menggunakan Pandas & `docs/images/seki_zip_structure.png`.
- **Keputusan:** **GO-MANUAL** — Alasan: File Excel lawas dari BI terbukti sangat ramah diproses menggunakan Pandas, namun ketiadaan API mengharuskan file tersebut diunduh manual dari portal setiap bulannya sebelum masuk ke *pipeline* otomatis.

---

## 3. Checklist tambahan Phase 0
- [x] Everyone: shared repo, struktur folder, source register template
- [x] Tim: draf 8–10 sektor prioritas
  **Daftar Sektor Prioritas (KBLI Level 1):**
  1. Pertanian, Peternakan, Kehutanan & Perikanan
  2. Pertambangan dan Penggalian
  3. Industri Pengolahan / Manufaktur
  4. Listrik, Gas dan Air Bersih / Energi
  5. Konstruksi  
  6. Perdagangan, Hotel dan Restoran
  7. Pengangkutan dan Komunikasi
  8. Keuangan, Real Estat dan Jasa Perusahaan