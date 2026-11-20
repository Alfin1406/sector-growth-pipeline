from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Text,
    Date,
    DateTime,
    UniqueConstraint,
)

from . import Base


# ==========================================
# 1. TABEL BANK INDONESIA (SEKI)
# ==========================================
class SekiKredit(Base):
    __tablename__ = "seki_kredit_sektor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sheet_asal = Column(String(20))
    tahun = Column(Integer, nullable=False)
    bulan = Column(Integer, nullable=False)  # 1-12 agar sorting time-series rapi
    kelompok_bank = Column(String(100), nullable=False)
    kategori_pinjaman = Column(String(100), nullable=False)
    sektor_kbli = Column(String(150), nullable=False)
    nilai_kredit_miliar_rp = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tahun",
            "bulan",
            "kelompok_bank",
            "kategori_pinjaman",
            "sektor_kbli",
            name="uix_seki_kredit",
        ),
    )


# ==========================================
# 2. TABEL BURSA EFEK INDONESIA (IDX)
# ==========================================
class IdxFinancial(Base):
    __tablename__ = "idx_financial_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_emiten = Column(String(10), nullable=False)
    nama_perusahaan = Column(String(150), nullable=False)
    sektor = Column(String(100))
    subsektor = Column(String(100))
    industri = Column(String(100))
    subindustri = Column(String(100))
    tanggal_laporan = Column(Date)
    tahun = Column(Integer, nullable=False)
    kuartal = Column(String(5), nullable=False)
    mata_uang = Column(String(50), nullable=False)
    cash_current = Column(Numeric)
    cash_prior = Column(Numeric)
    total_asset_current = Column(Numeric)
    total_asset_prior = Column(Numeric)
    total_liabilitas_current = Column(Numeric)
    total_liabilitas_prior = Column(Numeric)
    total_ekuitas_current = Column(Numeric)
    total_ekuitas_prior = Column(Numeric)
    link_sumber = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "kode_emiten",
            "tahun",
            "kuartal",
            name="uix_idx_financial",
        ),
    )


class IdxCorporateAction(Base):
    __tablename__ = "idx_corporate_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_emiten = Column(String(10), nullable=False)
    tanggal_pencatatan = Column(Date, nullable=False)
    jenis_tindakan = Column(String(100), nullable=False)
    jumlah_saham = Column(Numeric)
    jumlah_saham_setelah_tindakan = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "kode_emiten",
            "tanggal_pencatatan",
            "jenis_tindakan",
            name="uix_idx_corporate_action",
        ),
    )


# ==========================================
# 3. TABEL OTORITAS JASA KEUANGAN (OJK)
# ==========================================
class OjkPengumuman(Base):
    __tablename__ = "ojk_pengumuman"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tanggal_rilis = Column(Date)
    judul = Column(Text, nullable=False)
    link_halaman = Column(Text, nullable=False)
    isi_teks = Column(Text)
    link_lampiran = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "link_halaman",
            name="uix_ojk_pengumuman_link",
        ),
    )


class OjkRancanganRegulasi(Base):
    __tablename__ = "ojk_rancangan_regulasi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    satker = Column(String(50))  # Contoh: PVML, PPDP, Pasar Modal, OJK
    tanggal_rilis = Column(Date)
    judul = Column(Text, nullable=False)
    link_halaman = Column(Text, nullable=False)
    isi_teks = Column(Text)
    link_lampiran = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "link_halaman",
            name="uix_ojk_regulasi_link",
        ),
    )