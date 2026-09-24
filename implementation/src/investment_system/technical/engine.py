"""Technical snapshot contract. NEW IMPLEMENTATION.

Must not mutate QGV raw scores. STRUCTURAL FREEZE v0.6 respected as contract,
not claimed as recovered v0.6 package.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.enums import ExecutionZone, TechnicalRegime
from ..contracts.models import QGVSnapshot, TechnicalSnapshot
from ..versions import IMPLEMENTATION_KIND, TECHNICAL_STRUCTURAL


class TechnicalEngine:
    def evaluate(
        self,
        company_id: str,
        as_of: datetime,
        returns: list[float],
        qgv: QGVSnapshot | None = None,
        synthetic: bool = True,
    ) -> TechnicalSnapshot:
        if qgv is not None:
            _ = qgv.qgv_snapshot_id
            # C-15: Q/G/V scores are not inputs to regime/zone.
        regime = TechnicalRegime.UNKNOWN
        zone = ExecutionZone.WAIT
        if returns:
            last = returns[-1]
            vol = (sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(returns)) ** 0.5
            if vol > 0.04:
                regime = TechnicalRegime.HIGH_VOL
                zone = ExecutionZone.RISK_REDUCTION
            elif last > 0 and sum(returns[-5:]) > 0:
                regime = TechnicalRegime.TREND_UP
                zone = ExecutionZone.ADD if last > 0.01 else ExecutionZone.ENTRY
            elif last < 0 and sum(returns[-5:]) < 0:
                regime = TechnicalRegime.TREND_DOWN
                zone = ExecutionZone.WAIT
            else:
                regime = TechnicalRegime.RANGE
                zone = ExecutionZone.WAIT
        scenarios = tuple(
            {"name": f"S{i}", "return_shock": shock, "kind": "structural-placeholder"}
            for i, shock in enumerate((-0.1, 0.0, 0.1), start=1)
        )
        return TechnicalSnapshot(
            technical_snapshot_id=f"ta_{uuid4().hex[:12]}",
            company_id=company_id,
            as_of=as_of,
            technical_version=TECHNICAL_STRUCTURAL,
            implementation_kind=IMPLEMENTATION_KIND,
            regime=regime,
            execution_zone=zone,
            scenarios=scenarios,
            invalidation="close below last swing low (placeholder, NEW IMPLEMENTATION)",
            drawdown_recheck=False,
            qgv_snapshot_id_ref=qgv.qgv_snapshot_id if qgv else None,
            mutated_qgv=False,
            synthetic=synthetic,
        )
