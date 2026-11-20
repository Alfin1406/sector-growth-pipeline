from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .alfin import (
    SekiKredit,
    IdxFinancial,
    IdxCorporateAction,
    OjkPengumuman,
    OjkRancanganRegulasi,
)

from .arza import (
    ArzaJobPortal,
    ArzaCareerPage,
    ArzaBpsEximMonthly,
    ArzaBpsEximHs2,
)

from .atha import (
    BPSObservation,
    BPSSectorTimeSeries,
    BPSPDRBReconciliation,
    BKPMInvestment,
)