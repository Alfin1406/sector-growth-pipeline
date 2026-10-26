# Common Schema — Sector Growth Intelligence

> **Status:** Draft v0.2 (Phase 0) · **Diperbarui:** 2026-10-23 · **Pemilik:** seluruh tim (Alfin, Arza, Atha)
> **Catatan status (2026-10-23, arahan mentor):** dokumen ini adalah *blueprint* target tahap optimasi (lapisan Gold / Data Mart, Fase 3–4). Saat ini data tiap sumber tetap disimpan di tabel terpisah (Bronze → Silver) tanpa dilebur ke `clean.news_events`. Padanan istilah: `raw` = Bronze, `clean` = Silver, `mart` = Gold.
>
> Dokumen ini adalah "kontrak bersama". Semua pipeline menulis ke bentuk data yang sama supaya sinyal dari berita, statistik resmi, hiring, dan perdagangan bisa digabung menjadi *Sector Heat Table* di Phase 3. Perubahan skema dilakukan lewat Pull Request ke dokumen ini **dan** file migrasi di `database/migrations/`.

---

## 1. Arsitektur Penyimpanan (`raw` / `clean` / `mart`)

Di Phase 0 tim hanya **menyepakati skema target**. Tabel eksisting masing-masing tidak diubah atau dihapus; pembuatan schema dan migrasi data dilakukan di Phase 1 lewat `database/migrations/`.

| Lapisan | Isi | Aturan |
| :--- | :--- | :--- |
| `raw` | Data asli per sumber, apa adanya (tanpa transformasi) | Penamaan `raw.<source_id>_<entity>`. Tidak pernah diedit manual. Tabel lama disalin sebagai `raw.legacy_*` |
| `clean` | Tabel standar yang sudah diseragamkan, divalidasi, dan dideduplikasi | Struktur kolom mengikuti dokumen ini. Satu entitas = satu baris unik |
| `mart` | Agregasi sinyal per sektor dan *sector heat score* | Dibuat dari `clean`. Dashboard membaca dari sini (dan dari `clean` untuk artikel/evidence pendukung) |

**Aliran data:** `Airflow / pipelines → raw → clean → mart → Streamlit`. Pipeline tidak menulis langsung ke `mart` dari sumber, dan dashboard tidak membaca `raw`.

**Tabel eksisting yang akan dilebur ke `clean.news_events`:**

| Pemilik | Tabel | Database | Kolom | Baris |
| :--- | :--- | :--- | :-: | :-: |
| Alfin | `public.tabel_berita_ai` | (DB Alfin) | 12 | 192 |
| Arza | `public.data_center_news` | `data_center_insight` | 24 | 276 |
| Atha | `public.sector3_articles` | `market_intelligence` | 16 | 37 |

Ketiganya berada di database berbeda, jadi harus dikumpulkan dulu ke satu PostgreSQL terpusat (keputusan hosting dibahas terpisah dalam blueprint).

**Konvensi umum**
- Nama schema, tabel, dan kolom: `snake_case`, bahasa Inggris.
- Waktu dengan jam: `TIMESTAMPTZ`, disimpan sebagai UTC. Tanggal tanpa jam: `DATE`.
- Nilai kosong disimpan sebagai `NULL`, bukan string kosong.
- URL disimpan utuh sebagai `TEXT` (jangan `VARCHAR` pendek agar tidak terpotong).
- Kolom yang menunggu `sector_taxonomy_v1` (Phase 1) boleh `NULL` dulu; `NULL` berarti "belum dipetakan", bukan "tidak ada".

---

## 2. Spesifikasi Tabel Berita Utama: `clean.news_events`

| # | Kolom | Tipe | Constraint | Keterangan dan alasan |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `article_id` | `VARCHAR(64)` | **PK** | SHA-256 (hex) dari *canonical URL*. Dasar deduplikasi lintas tabel. Aturan canonical di bawah tabel |
| 2 | `title` | `TEXT` | NOT NULL | Judul artikel |
| 3 | `published_at` | `TIMESTAMPTZ` | NOT NULL | Waktu rilis berita; dasar filter periode dan YoY/QoQ. Jika sumber hanya punya tanggal, isi 00:00 WIB (Asia/Jakarta) |
| 4 | `source_url` | `TEXT` | NOT NULL | **Evidence link** wajib untuk setiap skor/angka di dashboard (syarat mentor) |
| 5 | `source_name` | `VARCHAR(100)` | | Nama portal media |
| 6 | `content` | `TEXT` | | Teks mentah artikel, untuk pemrosesan ulang LLM jika perlu |
| 7 | `summary` | `TEXT` | | Ringkasan inti hasil ekstraksi AI |
| 8 | `sector_code` | `VARCHAR(50)` | NULL sampai taxonomy v1 | Kode sektor mengacu ke `sector_taxonomy_v1` (10 sektor prioritas). Akan menjadi FK di Phase 1 |
| 9 | `event_type` | `VARCHAR(20)` | CHECK | `New Project`, `Expansion`, `Regulation`, `Investment`, `General`. **`NULL` = belum dilabeli**, `General` = sudah dilabeli dan bukan sector-event |
| 10 | `amount` | `NUMERIC(20,2)` | | Estimasi nilai nominal dalam **IDR** (hasil normalisasi). Teks aslinya disimpan di `extra_metadata.amount_raw` |
| 11 | `region` | `VARCHAR(200)` | | Wilayah/lokasi proyek atau ekspansi |
| 12 | `company_entity` | `TEXT` | | Perusahaan/organisasi terkait (belum untuk entity linking, itu di luar scope sampai setelah Phase 5) |
| 13 | `topic_tags` | `TEXT[]` | NOT NULL, default `'{}'` | Label subtopik/teknologi dari fase sebelumnya agar filter lama tetap berjalan |
| 14 | `relevance_score` | `INTEGER` | CHECK 0–100 | Skor relevansi terhadap tema pipeline asal, skala **0–100**. Bukan ukuran "ini sector-event" (itu peran `event_type` + `label_confidence`) |
| 15 | `scraped_at` | `TIMESTAMPTZ` | NOT NULL | Waktu penarikan data, untuk *freshness check* dan panel *Source Status* |
| 16 | `extra_metadata` | `JSONB` | NOT NULL, default `'{}'` | Kolom unik dari pipeline lama agar tidak ada data hilang (lihat bagian 3) |
| 17 | `label_method` | `VARCHAR(20)` | CHECK | Metode pelabelan `sector_code`/`event_type`: `rules`, `llm`, `manual`. `NULL` jika belum dilabeli |
| 18 | `label_confidence` | `NUMERIC(4,3)` | CHECK 0–1 | Keyakinan label (0.000–1.000). `NULL` untuk label berbasis rules yang tidak punya skor keyakinan, dan untuk baris belum dilabeli |

**Aturan canonical URL untuk `article_id`:** huruf kecil untuk scheme dan host, buang fragment (`#...`), buang parameter pelacak (`utm_*`, `fbclid`, `gclid`), buang trailing slash, dan urutkan parameter query. Hasilnya di-hash dengan SHA-256.

**Kunci `extra_metadata` yang baku:** `legacy_source` (contoh `alfin.tabel_berita_ai`), `legacy_id`, `amount_raw`, `raw_sector`, `relevance_score_raw`, `insight_type_raw`, `legacy_event_type`.

**Indeks yang disarankan:** PK pada `article_id`; `(sector_code, published_at DESC)`; `(event_type)`; GIN pada `topic_tags`.

**Aturan deduplikasi (usulan):** satu URL kanonik = satu baris. Jika artikel sama muncul di lebih dari satu tabel lama, nilai non-NULL menang; bila bentrok, prioritas Arza > Atha > Alfin (kolom sector-event paling lengkap ada di tabel Arza). Semua asal dicatat di `extra_metadata.legacy_source`.

**Pemenuhan syarat mentor:** atribut sector-event (`sector_code`, `event_type`, `amount`, `region`) dan evidence link (`source_url` NOT NULL) sudah tercakup.

**Perubahan dari usulan awal (mohon dikonfirmasi tim):**
- `sector` → `sector_code`, konsisten dengan rencana common schema sebelumnya.
- `published_at` diputuskan `TIMESTAMPTZ`; `amount` diputuskan `NUMERIC` (IDR) dengan teks asli di JSONB; `scraped_at` dibuat `TIMESTAMPTZ`.
- Ditambah `CHECK` pada `event_type` dan `relevance_score`, dan `topic_tags` dipastikan `TEXT[]`.
- **v0.2:** ditambah `label_method` dan `label_confidence` (kolom 17–18).

---

## 3. Matriks Mapping Tabel Eksisting → `clean.news_events`

| Kolom `clean` | Alfin (`tabel_berita_ai`) | Arza (`data_center_news`) | Atha (`sector3_articles`) |
| :--- | :--- | :--- | :--- |
| `article_id` | hash dari `link` | hash dari `article_url` (`id` lama → `extra.legacy_id`) | `article_id` (format 64 hex; cek kecocokan algoritma, jika beda hitung ulang dari `url`) |
| `title` | `judul` | `title` | `title` |
| `published_at` | `tanggal` (DATE → 00:00 WIB) | `published_date` (DATE → 00:00 WIB) | `published_at` |
| `source_url` | `link` | `article_url` | `url` |
| `source_name` | `sumber` | `source` | `source` |
| `content` | `isi_berita` | `content` | — (`NULL`) |
| `summary` | `ringkasan_ai` | `summary` | `insight_summary` |
| `sector_code` | `NULL` (lihat 3.3) | `NULL` sampai taxonomy v1 | `NULL` sampai taxonomy v1 |
| `event_type` | `NULL` | dari `insight_type` (aturan 3.1) | `NULL` (aturan 3.1) |
| `amount` | — | `investment_value` (parse teks → IDR) | — |
| `region` | — | `project_location` | — |
| `company_entity` | — | `company`, fallback `organization` | — |
| `topic_tags` | `teknologi_dibahas` | `subtopic`, `technology`, `topic`, `tag`, plus tag topik dari `insight_type` (lihat 3.1), dipecah jadi array | `subtopic`, `technology`, `topic` |
| `relevance_score` | `skor_relevansi_it` (langsung) | `NULL` dulu (lihat 3.2) | `NULL` |
| `scraped_at` | `waktu_scrape` | `pipeline_last_updated` (catatan: waktu update terakhir, bukan scrape pertama) | `scraped_at` |
| `label_method` | `NULL` | `rules` jika `event_type` terisi, selain itu `NULL` | `NULL` |
| `label_confidence` | `NULL` | `NULL` | `NULL` |

**Masuk ke `extra_metadata`:**

| Sumber | Kolom yang disimpan di JSONB |
| :--- | :--- |
| Alfin | `gambar`, `kategori_lisensi`, `raw_sector` (= `kategori_bisnis`), `legacy_source` |
| Arza | `image_url`, `capacity`, `capacity_type`, `investment_type`, `amount_raw` (= `investment_value`), `organization` (jika `company` terisi), `relevance`, `relevance_score_raw`, `insight_type_raw`, `raw_sector` (= `sector`), `tag`, `legacy_id`, `legacy_source` |
| Atha | `channel`, `business_action`, `impact`, `content_status`, `legacy_event_type`, `raw_sector` (= `industry`), `legacy_source` |

### 3.1 Aturan pemetaan `event_type`

**Arza (`insight_type` multi-label, dipisah `"; "`).** Simpan string asli di `extra_metadata.insight_type_raw`, lalu petakan dengan urutan prioritas (token dicocokkan persis, bukan substring):

| Prioritas | Jika mengandung token | `event_type` |
| :-: | :--- | :--- |
| 1 | `Investment` | `Investment` |
| 2 | `Project` | `New Project` |
| 3 | `Capacity` | `Expansion` |
| — | selain itu (termasuk `NULL`) | `NULL` (belum dilabeli) |

```sql
CASE
  WHEN 'Investment' = ANY(string_to_array(insight_type, '; ')) THEN 'Investment'
  WHEN 'Project'    = ANY(string_to_array(insight_type, '; ')) THEN 'New Project'
  WHEN 'Capacity'   = ANY(string_to_array(insight_type, '; ')) THEN 'Expansion'
  ELSE NULL
END
```

- Token yang bersifat topik (`Energy`, `Technology`, `Infrastructure`) masuk ke `topic_tags`.
- Token `Company` dan `Location` adalah penanda bahwa entitas/lokasi berhasil diekstrak, bukan topik, jadi tidak masuk `topic_tags`; cukup tersimpan di `insight_type_raw`.
- Baris yang terpetakan diberi `label_method = 'rules'`.
- **Keterbatasan:** `event_type` hanya satu nilai sedangkan sumbernya multi-label, jadi prioritas membuang informasi tambahan (mis. artikel `Investment; Project` hanya menjadi `Investment`). Teks aslinya tetap aman di `insight_type_raw`. Aturan `Capacity → Expansion` adalah heuristik awal dan harus divalidasi di sampel ±200 berita (Phase 2).

**Atha.** `event_type` Atha berisi kategori insiden/aktivitas keamanan siber dan IT, bukan 5 nilai baku sector-event. Nilai asli disimpan di `extra_metadata.legacy_event_type`, dan `clean.news_events.event_type` diisi `NULL` untuk dilabeli ulang oleh rules/LLM sesuai taksonomi sector-event.

**Alfin.** Tidak ada kolom setara, `event_type = NULL`.

### 3.2 Aturan `relevance_score`

- Skala kolom utama: **0–100**.
- Alfin: `skor_relevansi_it` (rentang 15–100) masuk langsung.
- Arza: `relevance_score` (rentang 1–17) adalah hitungan poin/keyword hit mentah, bukan skala yang sama. Nilai aslinya disimpan di `extra_metadata.relevance_score_raw`, dan kolom utama diisi `NULL` sampai rumus normalisasi disepakati (skala linear 17 → 100 dihindari karena menyiratkan kesetaraan yang belum terbukti).
- Atha: tidak ada skor, `NULL`.

### 3.3 Aturan nilai sektor mentah

Selama `sector_code` masih `NULL`, nilai asli `kategori_bisnis` (Alfin), `sector` (Arza), dan `industry` (Atha) disimpan di `extra_metadata.raw_sector`.

Catatan: seluruh 192 baris Alfin bernilai `"AI & Data Infrastruktur"`, yaitu label **tema pipeline**, bukan sektor industri. Nilai ini **tidak boleh** dipetakan langsung ke `sector_code`. Sektor yang dibahas sebuah artikel (mis. perbankan yang mengadopsi AI) harus ditentukan dari isi artikel lewat pelabelan di Phase 2.

---

## 4. Konvensi Kolom Pengikat Lintas Sumber (non-berita)

Semua tabel `clean` dari sumber non-berita (BPS, BKPM, regulator, job portal, career page, Bea Cukai, IDX, BI/OJK) **wajib** memiliki kolom berikut agar bisa digabung di Phase 3:

| Kolom | Tipe | Wajib | Keterangan |
| :--- | :--- | :-: | :--- |
| `source_id` | `VARCHAR(50)` | Ya | ID sumber sesuai `docs/source_register.md` (contoh: `bps`, `bkpm`, `idx`) |
| `sector_code` | `VARCHAR(50)` | Ya* | Mengacu ke `sector_taxonomy_v1`. *Boleh `NULL` sementara sampai taxonomy v1 selesai |
| `period_start` | `DATE` | Ya | Awal periode data (kuartal Q2 2026 → `2026-04-01`) |
| `period_end` | `DATE` | Ya | Akhir periode data (`2026-06-30`). Untuk data harian, sama dengan `period_start` |
| `source_url` | `TEXT` | Ya | Evidence link untuk setiap angka |
| `scraped_at` | `TIMESTAMPTZ` | Ya | Waktu penarikan data, untuk freshness check |
| `extra_metadata` | `JSONB` | Disarankan | Kolom unik per sumber |

Untuk tabel sinyal numerik, disarankan pola *long format*: `metric_name`, `value NUMERIC`, `unit`. Bentuk final tabel `mart` (perubahan YoY/QoQ, rolling average, skor gabungan) didefinisikan di Phase 3.

---

## 5. Keputusan Terbuka dan Pekerjaan Lanjutan

- [x] **Skala `relevance_score`:** ditetapkan 0–100; Alfin langsung, Arza `NULL` dulu (nilai mentah di JSONB). Rumus normalisasi Arza masih terbuka.
- [x] **Mapping nilai `event_type`:** Arza dengan aturan prioritas (3.1), Atha `NULL`. Validasi akurasi di sampel Phase 2.
- [x] **`link` Alfin `VARCHAR(255)`:** hasil audit 0 URL terpotong.
- [x] **`label_method` dan `label_confidence`:** ditambahkan sebagai kolom 17–18.
- [ ] **Algoritma hash Atha:** format 64 hex sudah sesuai SHA-256, tetapi belum diverifikasi apakah dihitung dari URL yang sama dengan aturan canonical. Jika tidak cocok, hitung ulang untuk semua baris.
- [ ] **Zona waktu kolom `timestamp without time zone`** di tabel lama: tetapkan asumsinya (usulan: WIB).
- [ ] **Mapping `raw_sector` → `sector_code`:** menunggu `sector_taxonomy_v1` (Phase 1) dan pelabelan berbasis isi artikel (Phase 2).
- [ ] **Normalisasi `relevance_score` Arza** (1–17 → 0–100) atau tetap `NULL`.
- [ ] **Multi-label `event_type`:** pertimbangkan `event_types TEXT[]` bila satu nilai dirasa kurang.
- [ ] **Konsolidasi tiga database** ke satu PostgreSQL terpusat.

---

## Lampiran A. Hasil Audit Data Eksisting (2026-10-23)

| Sumber | Temuan |
| :--- | :--- |
| Alfin (192 baris) | 0 URL terpotong; `skor_relevansi_it` 15–100; `kategori_bisnis` seragam `"AI & Data Infrastruktur"` (label tema) |
| Arza (276 baris) | `relevance_score` 1–17; `insight_type` multi-label (`"; "`); 3 baris `NULL` |
| Atha (37 baris) | `event_type` berisi 14 kategori keamanan siber/IT (mis. `Cyber Attack / Security Incident`, `Data Exposure / Leak Report`); `article_id` berformat 64 karakter hex |

**Dampak aturan 3.1 pada data Arza** (dihitung dari distribusi `insight_type` hasil audit; verifikasi ulang dengan query di repo): `Investment` 138, `New Project` 11, `Expansion` 12, `NULL` 115, total 276. Jika digabung dengan Alfin dan Atha (yang `event_type`-nya `NULL`), baru 161 dari 505 baris (±32%) yang punya `event_type` awal.

---

## Riwayat Perubahan

| Versi | Tanggal | Perubahan |
| :--- | :--- | :--- |
| v0.1 | 2026-10-22 | Draf awal Phase 0 |
| v0.2 | 2026-10-23 | Aturan mapping `event_type`, `relevance_score`, `raw_sector`; kolom `label_method` dan `label_confidence`; hasil audit; checklist diperbarui |
