from datetime import datetime, timezone

from investment_system.contracts.enums import QualityState
from investment_system.contracts.models import FactorObservation
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_FACTORS

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def complete_obs(score: float = 70.0) -> dict[str, FactorObservation]:
    out = {}
    for fid in list(Q_WEIGHTS) + list(G_WEIGHTS) + list(V_FACTORS):
        out[fid] = FactorObservation(
            factor_id=fid,
            raw_value=score,
            score_0_100=score,
            quality=QualityState.OK,
            stamp_id="syn_1",
            notes="SYNTHETIC",
        )
    return out
