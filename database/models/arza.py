
from datetime import datetime

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    JSON,
    UniqueConstraint,
    CheckConstraint,
)

from . import Base


# ==========================================
# 1. JOB PORTAL & CAREER PAGES
# ==========================================
class ArzaJobMarket(Base):
    __tablename__ = "arza_job_market"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    source = Column(String(50), nullable=False)
    source_job_id = Column(String(150))
    record_hash = Column(String(64), nullable=False)

    job_title = Column(Text, nullable=False)
    company = Column(Text)
    sector = Column(String(150))
    location = Column(Text)
    salary = Column(Text)

    employment_type = Column(String(100))
    work_mode = Column(String(100))
    category = Column(String(150))

    education = Column(Text)
    education_level = Column(Text)
    experience = Column(Text)
    majors = Column(Text)
    skills = Column(Text)
    requirements = Column(Text)
    qualifications = Column(Text)
    documents = Column(Text)

    description = Column(Text)
    job_description = Column(Text)
    additional_information = Column(Text)

    test_location = Column(Text)
    placement_location = Column(Text)
    selection_stages = Column(Text)
    duration = Column(Text)

    date_posted = Column(Date)
    published_date = Column(Date)
    deadline = Column(Date)
    announcement_date = Column(Date)
    application_period = Column(Text)

    job_url = Column(Text)
    application_url = Column(Text)

    status = Column(
        String(20),
        nullable=False,
        default="UNKNOWN",
    )

    scraped_at = Column(DateTime(timezone=True))
    raw_data = Column(JSON)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "source",
            "record_hash",
            name="uq_arza_job_market_source_hash",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'CLOSED', 'UNKNOWN')",
            name="ck_arza_job_market_status",
        ),
    )


# ==========================================
# 2. BPS EKSPOR IMPOR NASIONAL BULANAN
# ==========================================
class ArzaBpsEximMonthly(Base):
    __tablename__ = "arza_bps_exim_monthly"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    tahun = Column(Integer, nullable=False)
    bulan = Column(Integer, nullable=False)

    nilai_ekspor_usd = Column(Numeric(20, 2))
    berat_ekspor_kg = Column(Numeric(20, 2))

    nilai_impor_usd = Column(Numeric(20, 2))
    berat_impor_kg = Column(Numeric(20, 2))

    source_file = Column(String(255))
    raw_data = Column(JSON)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tahun",
            "bulan",
            name="uq_arza_bps_exim_monthly_period",
        ),
        CheckConstraint(
            "bulan BETWEEN 1 AND 12",
            name="ck_arza_bps_monthly_bulan",
        ),
    )


# ==========================================
# 3. BPS EKSPOR IMPOR BERDASARKAN HS2
# ==========================================
class ArzaBpsEximHs2(Base):
    __tablename__ = "arza_bps_exim_hs2"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    tahun = Column(Integer, nullable=False)
    bulan = Column(Integer, nullable=False)

    kode_hs = Column(String(2), nullable=False)
    deskripsi_hs = Column(Text)

    nilai_ekspor_usd = Column(Numeric(20, 2))
    berat_ekspor_kg = Column(Numeric(20, 2))

    nilai_impor_usd = Column(Numeric(20, 2))
    berat_impor_kg = Column(Numeric(20, 2))

    source_file = Column(String(255))
    raw_data = Column(JSON)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tahun",
            "bulan",
            "kode_hs",
            name="uq_arza_bps_exim_hs2_period",
        ),
        CheckConstraint(
            "bulan BETWEEN 1 AND 12",
            name="ck_arza_bps_hs2_bulan",
        ),
    )
