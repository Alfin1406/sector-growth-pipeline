from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base

# Catatan: Jika di file ini Arza sudah mendefinisikan 'Base = declarative_base()', 
# kamu bisa menghapus baris di bawah ini agar tidak bentrok. Jika file ini kosong, biarkan saja.
Base = declarative_base()

# ==========================================
# 1. TABEL BANK INDONESIA (SEKI)
# ==========================================
class SekiKredit(Base):
    __tablename__ = 'seki_kredit_sektor'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tahun = Column(Integer, nullable=False)
    bulan = Column(String(15), nullable=False)
    kelompok_bank = Column(String(100), nullable=False)
    kategori_pinjaman = Column(String(100), nullable=False)
    sektor_kbli = Column(String(150), nullable=False)
    nilai_kredit_miliar_rp = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tahun', 'bulan', 'kelompok_bank', 'kategori_pinjaman', 'sektor_kbli', name='uix_seki_kredit'),
    )

# ==========================================
# 2. TABEL BURSA EFEK INDONESIA (IDX)
# ==========================================
class IdxFinancial(Base):
    __tablename__ = 'idx_financial_statements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_emiten = Column(String(10), nullable=False)
    nama_perusahaan = Column(String(150), nullable=False)
    sektor = Column(String(100))
    tahun = Column(Integer, nullable=False)
    kuartal = Column(String(5), nullable=False)
    cash_current = Column(Numeric)
    cash_prior = Column(Numeric)
    total_asset_current = Column(Numeric)
    total_asset_prior = Column(Numeric)
    total_liabilitas_current = Column(Numeric)
    total_ekuitas_current = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('kode_emiten', 'tahun', 'kuartal', name='uix_idx_financial'),
    )

class IdxCorporateAction(Base):
    __tablename__ = 'idx_corporate_actions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_emiten = Column(String(10), nullable=False)
    tanggal_pencatatan = Column(Date, nullable=False)
    jenis_tindakan = Column(String(100), nullable=False)
    jumlah_saham = Column(Numeric)
    jumlah_saham_setelah_tindakan = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('kode_emiten', 'tanggal_pencatatan', 'jenis_tindakan', name='uix_idx_corporate_action'),
    )

# ==========================================
# 3. TABEL OTORITAS JASA KEUANGAN (OJK)
# ==========================================
class OjkDokumen(Base):
    __tablename__ = 'ojk_dokumen'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kategori = Column(String(50), nullable=False)
    tanggal_rilis = Column(String(50))
    judul = Column(Text, nullable=False)
    isi_teks = Column(Text)
    link_lampiran = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('link_lampiran', name='uix_ojk_link'),
    )