"""Investment System integration flow v1.1 + v1.2 PROVISIONAL config.

QGV Snapshot + Technical Snapshot + Macro Snapshot
→ Gate → Integration → Portfolio/Risk → Target Weight → Order intent.
Final decision stays in this layer. NEW IMPLEMENTATION.
"""

from __future__ import annotations

from datetime import datetime

from ..contracts.enums import ExecutionZone, GateDecision, MacroState
from ..contracts.models import IntegrationResult, MacroSnapshot, PortfolioSnapshot, TechnicalSnapshot
from .policy import DEFAULT_PROVISIONAL_POLICY, ProvisionalPolicy


class IntegrationEngine:
    def __init__(self, policy: ProvisionalPolicy | None = None):
        self.policy = policy or DEFAULT_PROVISIONAL_POLICY

    def run(
        self,
        as_of: datetime,
        portfolio: PortfolioSnapshot,
        technical_by_company: dict[str, TechnicalSnapshot],
        macro: MacroSnapshot,
        profile_id: str | None = None,
        parameter_set_hash: str | None = None,
    ) -> IntegrationResult:
        reasons: list[str] = []
        gate = GateDecision.PASS
        if macro.state == MacroState.EMERGENCY:
            gate = GateDecision.BLOCK
            reasons.append("macro EMERGENCY")
        elif macro.state == MacroState.WARNING:
            gate = GateDecision.HOLD
            reasons.append("macro WARNING")

        targets: dict[str, float] = {}
        orders: list[dict] = []
        qgv_refs: list[str] = []
        for h in portfolio.holdings:
            base = h.target_weight
            tech = technical_by_company.get(h.company_id)
            om = self.policy.om_default
            tm = self.policy.tm_default
            mm = self.policy.mm_default
            rm = self.policy.rm_default
            if tech and tech.execution_zone == ExecutionZone.RISK_REDUCTION:
                tm = 0.7
            if tech and tech.execution_zone == ExecutionZone.WAIT:
                tm = 0.85
            if gate == GateDecision.HOLD:
                mm = 0.8
            if gate == GateDecision.BLOCK:
                mm = 0.0
            raw = base * om * tm * mm * rm
            targets[h.company_id] = raw
            if h.qgv_snapshot_id:
                qgv_refs.append(h.qgv_snapshot_id)
            gap = (h.actual_weight or h.target_weight) - h.target_weight
            if abs(gap) * 100 >= self.policy.deadband_pp and gate != GateDecision.BLOCK:
                stage = self.policy.staged_entry[0]
                orders.append(
                    {
                        "company_id": h.company_id,
                        "side": "BUY" if gap < 0 else "SELL",
                        "intent_weight": abs(gap) * stage,
                        "policy_status": self.policy.status,
                    }
                )

        # Renormalize remaining risk-on weights when not blocked.
        total = sum(targets.values())
        if gate != GateDecision.BLOCK and total > 0:
            targets = {k: v / total * (1.0 - portfolio.cash_weight) for k, v in targets.items()}
        elif gate == GateDecision.BLOCK:
            targets = {k: 0.0 for k in targets}
            orders = []

        return IntegrationResult(
            as_of=as_of,
            gate=gate,
            gate_reasons=reasons,
            target_weights=targets,
            order_intents=orders,
            policy_status=self.policy.status,
            qgv_refs=qgv_refs,
            technical_ref=next(iter(technical_by_company.values())).technical_snapshot_id if technical_by_company else None,
            macro_ref=macro.macro_snapshot_id,
            profile_id=profile_id,
            parameter_set_hash=parameter_set_hash,
        )
