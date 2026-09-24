"""Macro confirmed v0.1.1 contract. NEW IMPLEMENTATION.

Does not promote v0.1.4 Candidate. Does not mutate QGV raw scores.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.enums import MacroState
from ..contracts.models import MacroSnapshot
from ..versions import IMPLEMENTATION_KIND, MACRO_CANDIDATE, MACRO_CONFIRMED


class MacroEngine:
    confirmed_version = MACRO_CONFIRMED
    candidate_version = MACRO_CANDIDATE  # exposed but not used as default

    def evaluate(self, as_of: datetime, indicators: dict[str, float] | None = None, synthetic: bool = True) -> MacroSnapshot:
        indicators = indicators or {}
        state = MacroState.NORMAL
        regime = "NEUTRAL"
        growth = indicators.get("growth", 0.0)
        inflation = indicators.get("inflation", 0.0)
        if inflation > 0.08:
            state = MacroState.EMERGENCY
            regime = "INFLATION_SHOCK"
        elif inflation > 0.05 and growth < 0:
            state = MacroState.WARNING
            regime = "STAGFLATION_RISK"
        elif growth > 0.03 and inflation < 0.03:
            regime = "EXPANSION"
        return MacroSnapshot(
            macro_snapshot_id=f"mac_{uuid4().hex[:12]}",
            as_of=as_of,
            macro_version=self.confirmed_version,
            implementation_kind=IMPLEMENTATION_KIND,
            state=state,
            regime=regime,
            environment={"indicators": indicators, "candidate_not_applied": MACRO_CANDIDATE},
            mutated_qgv=False,
            synthetic=synthetic,
        )
