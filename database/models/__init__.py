from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .alfin import (
    SekiKredit,
    IdxFinancial,
    IdxCorporateAction,
    OjkDokumen,
)

from .arza import (
    ArzaJobMarket,
    ArzaBpsEximMonthly,
    ArzaBpsEximHs2,
)

from .atha import (
    BPSObservation,
    BPSSectorTimeSeries,
    BPSPDRBReconciliation,
    BKPMInvestment,
)