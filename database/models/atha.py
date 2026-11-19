
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from database.models import Base


# ============================================================
# 1. BADAN PUSAT STATISTIK (BPS)
# ============================================================

class BPSObservation(Base):
    """
    Observasi PDRB berdasarkan ADHB dan ADHK.
    Data ADHB dan ADHK digabung dalam satu tabel,
    dibedakan melalui kolom price_basis.
    """

    __tablename__ = "bps_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    source = Column(String(50), nullable=False)
    domain = Column(Integer, nullable=False)
    subject = Column(Text, nullable=False)

    vervar_id = Column(Integer, nullable=False)
    vervar_label = Column(Text, nullable=False)

    variable_id = Column(Integer, nullable=False)
    variable_label = Column(Text, nullable=False)

    turvar_id = Column(Integer, nullable=False)
    turvar_label = Column(Text, nullable=False)

    period_id = Column(Integer, nullable=False)
    period_label = Column(Integer, nullable=False)

    subperiod_id = Column(Integer, nullable=False)
    subperiod_label = Column(String(50), nullable=False)

    value = Column(Numeric(30, 10), nullable=False)
    unit = Column(String(100), nullable=False)
    last_update = Column(String(50), nullable=False)

    datacontent_key = Column(BigInteger, nullable=False)

    decode_status = Column(String(50), nullable=False)

    year = Column(Integer, nullable=False)
    frequency = Column(String(20), nullable=False)
    quarter = Column(String(5), nullable=True)

    category_type = Column(String(100), nullable=False)
    sector_group = Column(String(100), nullable=False)

    is_aggregate = Column(Boolean, nullable=False)
    aggregation_method = Column(String(100), nullable=False)

    price_basis = Column(String(10), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "price_basis",
            "variable_id",
            "period_id",
            "vervar_id",
            "turvar_id",
            "subperiod_id",
            name="uq_bps_observation_natural_key",
        ),
    )


class BPSSectorTimeSeries(Base): 
    """
    Time series PDRB berdasarkan kelompok sektor.
    ADHB dan ADHK dibedakan melalui price_basis.
    """

    __tablename__ = "bps_sector_timeseries"

    id = Column(Integer, primary_key=True, autoincrement=True)

    source = Column(String(50), nullable=False)

    source_variable_id = Column(Integer, nullable=False)
    source_variable_label = Column(Text, nullable=False)

    domain = Column(Integer, nullable=False)
    subject = Column(Text, nullable=False)

    year = Column(Integer, nullable=False)
    period_id = Column(Integer, nullable=False)
    frequency = Column(String(20), nullable=False)

    subperiod_id = Column(Integer, nullable=False)
    subperiod_label = Column(String(50), nullable=False)
    quarter = Column(String(5), nullable=True)

    vervar_id = Column(Integer, nullable=False)
    vervar_label = Column(Text, nullable=False)

    series_name = Column(Text, nullable=False)
    sector_group = Column(String(100), nullable=False)

    value = Column(Numeric(30, 10), nullable=False)
    unit = Column(String(100), nullable=False)

    is_aggregate = Column(Boolean, nullable=False)
    aggregation_method = Column(String(100), nullable=False)

    source_record_count = Column(Integer, nullable=False)

    source_category_ids = Column(Text, nullable=False)
    source_datacontent_keys = Column(Text, nullable=False)

    last_update = Column(String(50), nullable=False)

    price_basis = Column(String(10), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "price_basis",
            "source_variable_id",
            "period_id",
            "subperiod_id",
            "vervar_id",
            "series_name",
            name="uq_bps_timeseries_natural_key",
        ),
    ) 


# ============================================================
# 2. BADAN PUSAT STATISTIK (BPS) - PDRB RECONCILIATION
# ============================================================

class BPSPDRBReconciliation(Base):
    """
    Hasil rekonsiliasi PDRB tahun 2026.
    Membandingkan PDRB total yang dipublikasikan BPS
    dengan penjumlahan 17 industri.

    ADHB dan ADHK dibedakan melalui price_basis.
    """

    __tablename__ = "bps_pdrb_reconciliation"

    id = Column(Integer, primary_key=True, autoincrement=True)

    year = Column(Integer, nullable=False)
    period_id = Column(Integer, nullable=False)
    subperiod_id = Column(Integer, nullable=False)

    subperiod_label = Column(String(50), nullable=False)
    quarter = Column(String(5), nullable=False)

    vervar_id = Column(Integer, nullable=False)
    vervar_label = Column(Text, nullable=False) 

    unit = Column(String(100), nullable=False)

    published_pdrb_total = Column(Numeric(30, 10), nullable=False)
    sum_of_17_industries = Column(Numeric(30, 10), nullable=False)

    difference_total_minus_industries = Column(
        Numeric(30, 10),
        nullable=False
    )

    review_tolerance_miliar = Column(Numeric(30, 10), nullable=False)

    within_review_tolerance = Column(Boolean, nullable=False)

    price_basis = Column(String(10), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "price_basis",
            "period_id",
            "subperiod_id",
            "vervar_id",
            name="uq_bps_pdrb_reconciliation",
        ),
    )
 


# ============================================================
# 2. BADAN KOORDINASI PENANAMAN MODAL (BKPM)
# ============================================================

class BKPMInvestment(Base):
    """
    Data realisasi investasi BKPM tahun 2026.
    Mencakup PMA dan PMDN berdasarkan periode triwulan,
    sektor, negara, dan wilayah.
    """

    __tablename__ = "bkpm_investments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    periode = Column(String(50), nullable=False)
    status_penanaman_modal = Column(String(20), nullable=False)

    regional = Column(String(100), nullable=False)
    negara = Column(String(150), nullable=False)

    sektor_utama = Column(String(100), nullable=False)
    nama_sektor = Column(String(200), nullable=False)
    deskripsi_kbli_2digit = Column(Text, nullable=False)

    provinsi = Column(String(150), nullable=False)
    kabupaten_kota = Column(String(150), nullable=False)

    jawa_luar_jawa = Column(String(50), nullable=False)
    pulau = Column(String(100), nullable=False)

    investasi_rp_juta = Column(Numeric(24, 8), nullable=False)
    investasi_us_ribu = Column(Numeric(24, 8), nullable=False)

    tki = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "periode",
            "status_penanaman_modal",
            "regional",
            "negara",
            "sektor_utama",
            "nama_sektor",
            "deskripsi_kbli_2digit",
            "provinsi",
            "kabupaten_kota", 
            "jawa_luar_jawa",
            "pulau",
            name="uq_bkpm_investment_natural_key",
        ),
    )
 