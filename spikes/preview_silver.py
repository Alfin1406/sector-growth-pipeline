import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.common.db import get_engine_with_retry

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)
pd.set_option("display.max_colwidth", 48)

QUERIES = {
    "1A. KPI BI SEKI - Total Kredit B2B Bulan Terakhir & YoY": r"""
        WITH silver AS (
            SELECT
                MAKE_DATE(tahun, bulan, 1) AS periode_date,
                nilai_kredit_miliar_rp
            FROM public.seki_kredit_sektor
            WHERE kelompok_bank NOT LIKE '6.%'
              AND kategori_pinjaman NOT ILIKE '%Bukan Lapangan Usaha%'
        ),
        latest_dt AS (SELECT MAX(periode_date) AS max_dt FROM silver),
        agg AS (
            SELECT
                (SELECT max_dt FROM latest_dt) AS periode_terakhir,
                SUM(CASE WHEN s.periode_date = ld.max_dt THEN s.nilai_kredit_miliar_rp END) AS cur_miliar,
                SUM(CASE WHEN s.periode_date = (ld.max_dt - INTERVAL '1 year')::date THEN s.nilai_kredit_miliar_rp END) AS py_miliar
            FROM silver s CROSS JOIN latest_dt ld
        )
        SELECT
            periode_terakhir,
            ROUND((cur_miliar / 1000.0)::numeric, 2) AS total_kredit_triliun_rp,
            ROUND((py_miliar / 1000.0)::numeric, 2) AS kredit_tahun_lalu_triliun_rp,
            ROUND((((cur_miliar - py_miliar) / NULLIF(py_miliar, 0)) * 100.0)::numeric, 2) AS yoy_growth_pct
        FROM agg
    """,
    "1B. TOP 5 SEKTOR KBLI B2B - Pertumbuhan YoY Tertinggi (Bulan Terakhir)": r"""
        WITH silver AS (
            SELECT
                MAKE_DATE(tahun, bulan, 1) AS periode_date,
                TRIM(sektor_kbli) AS sektor_kbli,
                nilai_kredit_miliar_rp
            FROM public.seki_kredit_sektor
            WHERE kelompok_bank NOT LIKE '6.%'
              AND kategori_pinjaman NOT ILIKE '%Bukan Lapangan Usaha%'
        ),
        latest_dt AS (SELECT MAX(periode_date) AS max_dt FROM silver),
        cur AS (
            SELECT s.sektor_kbli, SUM(s.nilai_kredit_miliar_rp) AS cur_miliar
            FROM silver s JOIN latest_dt ld ON s.periode_date = ld.max_dt
            GROUP BY s.sektor_kbli
        ),
        py AS (
            SELECT s.sektor_kbli, SUM(s.nilai_kredit_miliar_rp) AS py_miliar
            FROM silver s JOIN latest_dt ld ON s.periode_date = (ld.max_dt - INTERVAL '1 year')::date
            GROUP BY s.sektor_kbli
        )
        SELECT
            cur.sektor_kbli,
            ROUND((cur.cur_miliar / 1000.0)::numeric, 2) AS kredit_triliun_rp,
            ROUND((((cur.cur_miliar - py.py_miliar) / NULLIF(py.py_miliar, 0)) * 100.0)::numeric, 2) AS yoy_growth_pct
        FROM cur
        LEFT JOIN py ON py.sektor_kbli = cur.sektor_kbli
        ORDER BY yoy_growth_pct DESC NULLS LAST
        LIMIT 5
    """,
    "2A. KPI IDX FINANCIALS - Ringkasan Kesehatan & Cash Growth (IDR)": r"""
        WITH silver AS (
            SELECT
                kode_emiten,
                ((cash_current - cash_prior) / NULLIF(ABS(cash_prior), 0)) * 100.0 AS cash_growth_pct,
                CASE
                    WHEN total_ekuitas_current <= 0 THEN 'Defisiensi Modal (High Risk)'
                    WHEN (total_liabilitas_current / NULLIF(total_ekuitas_current, 0)) > 2.0 THEN 'High Leverage (DER > 2)'
                    ELSE 'Sehat'
                END AS financial_health_flag
            FROM public.idx_financial_statements
        )
        SELECT
            COUNT(*) AS total_emiten,
            COUNT(*) FILTER (WHERE cash_growth_pct > 10) AS emiten_cash_growth_gt_10pct,
            COUNT(*) FILTER (WHERE financial_health_flag = 'Sehat') AS sehat,
            COUNT(*) FILTER (WHERE financial_health_flag = 'High Leverage (DER > 2)') AS high_leverage,
            COUNT(*) FILTER (WHERE financial_health_flag = 'Defisiensi Modal (High Risk)') AS defisiensi_modal
        FROM silver
    """,
    "2B. PREVIEW SILVER IDX FINANCIALS - Top 8 Emiten Kas Terbesar (Sudah Konversi IDR)": r"""
        WITH base AS (
            SELECT
                kode_emiten,
                nama_perusahaan,
                CASE WHEN sektor LIKE '%. %' THEN TRIM(SUBSTRING(sektor FROM POSITION('. ' IN sektor) + 2)) ELSE sektor END AS sektor_nama,
                mata_uang,
                CASE
                    WHEN UPPER(COALESCE(mata_uang, '')) LIKE '%USD%' THEN
                        CASE tanggal_laporan
                            WHEN DATE '2026-03-31' THEN 16993.0
                            WHEN DATE '2026-06-30' THEN 17708.0
                            ELSE 16993.0
                        END
                    ELSE 1.0
                END AS kurs_idr,
                cash_current,
                cash_prior,
                total_liabilitas_current,
                total_ekuitas_current
            FROM public.idx_financial_statements
        )
        SELECT
            kode_emiten,
            nama_perusahaan,
            sektor_nama,
            mata_uang,
            ROUND(((cash_current * kurs_idr) / 1e12)::numeric, 2) AS cash_triliun_idr,
            ROUND((((cash_current - cash_prior) / NULLIF(ABS(cash_prior), 0)) * 100.0)::numeric, 2) AS cash_growth_pct,
            CASE
                WHEN total_ekuitas_current > 0 THEN ROUND((total_liabilitas_current / total_ekuitas_current)::numeric, 2)
                ELSE NULL
            END AS der_ratio,
            CASE
                WHEN total_ekuitas_current <= 0 THEN 'Defisiensi Modal'
                WHEN (total_liabilitas_current / NULLIF(total_ekuitas_current, 0)) > 2.0 THEN 'High Leverage'
                ELSE 'Sehat'
            END AS health_flag
        FROM base
        ORDER BY cash_current * kurs_idr DESC
        LIMIT 8
    """,
    "3. PREVIEW SILVER IDX CORPORATE ACTIONS - Sebaran Sinyal Bisnis": r"""
        SELECT
            CASE
                WHEN jenis_tindakan IN ('Warrant', 'Preemptive Rights', 'Non-Preemptive Rights', 'Mandatory Convertible Bond')
                    THEN 'Sinyal Ekspansi / Pendanaan'
                WHEN jenis_tindakan IN ('Delisting', 'Partial Delisting')
                    THEN 'Risiko Tinggi (Delisting)'
                WHEN jenis_tindakan = 'Stock Split'
                    THEN 'Aksi Likuiditas Pasar'
                ELSE 'Lainnya'
            END AS kategori_sinyal,
            jenis_tindakan,
            COUNT(*) AS jumlah_aksi
        FROM public.idx_corporate_actions
        GROUP BY 1, 2
        ORDER BY 1, 3 DESC
    """,
    "4. PREVIEW SILVER OJK PENGUMUMAN - Verifikasi Tagging (Target 'Lainnya' = 0)": r"""
        WITH tagged AS (
            SELECT
                tanggal_rilis,
                CASE
                    WHEN judul ~* '(cabut izin|sanksi administratif|perintah tindakan tertentu|pembubaran|penolakan permohonan)'
                        THEN 'Red Flag (Sanksi / Cabut Izin / Tutup)'
                    WHEN judul ~* '(perubahan nama|pemberlakuk?an izin|penetapan penggunaan izin)'
                        THEN 'Update Entitas (Rebranding)'
                    WHEN judul ~* '(pemberian izin usaha|pengesahan pembentukan)'
                        THEN 'Prospek Baru (Izin Usaha Baru)'
                    ELSE 'Lainnya'
                END AS kategori_pengumuman
            FROM public.ojk_pengumuman
        )
        SELECT
            kategori_pengumuman,
            COUNT(*) AS jumlah_dokumen,
            MIN(tanggal_rilis) AS dari_tgl,
            MAX(tanggal_rilis) AS sampai_tgl
        FROM tagged
        GROUP BY kategori_pengumuman
        ORDER BY jumlah_dokumen DESC
    """,
    "5. PREVIEW SILVER OJK RANCANGAN REGULASI - Target Industri per Satker": r"""
        SELECT
            satker,
            CASE satker
                WHEN 'PPDP' THEN 'Asuransi, Penjaminan & Dana Pensiun'
                WHEN 'PVML' THEN 'Pembiayaan, Modal Ventura, Pergadaian & LKM'
                WHEN 'Pasar Modal' THEN 'Emiten, Manajer Investasi & Sekuritas'
                WHEN 'Perbankan' THEN 'Bank Umum & BPR/BPRS'
                WHEN 'ITSK' THEN 'Fintech, Inovasi Teknologi & Aset Kripto'
                WHEN 'EPK' THEN 'Edukasi & Pelindungan Konsumen'
                ELSE 'Lintas Sektor / Konglomerasi Keuangan'
            END AS target_industri,
            COUNT(*) AS jumlah_rancangan
        FROM public.ojk_rancangan_regulasi
        GROUP BY 1, 2
        ORDER BY jumlah_rancangan DESC
    """,
}


def main() -> None:
    engine = get_engine_with_retry()
    try:
        with engine.connect() as conn:
            for title, sql in QUERIES.items():
                print(f"\n{'=' * 95}\n{title}\n{'=' * 95}")
                df = pd.read_sql(text(sql), conn)
                print(df.to_string(index=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()