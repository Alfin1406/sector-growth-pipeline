"""create raw bi seki table

Membuat raw table untuk menampung data kredit perbankan SEKI Bank Indonesia
(Lapangan Usaha dan Bukan Lapangan Usaha/Konsumsi).

Revision ID: 002
Revises: 001
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.raw_bi_seki_kredit (
            id serial NOT NULL,
            sheet_name varchar(50),
            kelompok_bank varchar(150),
            kategori_pinjaman varchar(100),
            sektor_kbli text,
            periode_tahun integer,
            periode_bulan varchar(50),
            kredit_miliar_rp numeric(18, 2),
            source_file varchar(150) DEFAULT 'TABEL1_4.xls',
            waktu_ingest timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT raw_bi_seki_kredit_pkey PRIMARY KEY (id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.raw_bi_seki_kredit")