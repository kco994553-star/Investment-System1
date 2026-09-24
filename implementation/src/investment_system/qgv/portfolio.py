"""Portfolio engine on generic input. NEW IMPLEMENTATION.

official_v11 / us_working are REFERENCE_FIXTURE constructors only.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.models import Holding, PortfolioSnapshot, QGVSnapshot
from ..contracts.portfolio_input import ROLE_FIXTURE, ROLE_GENERIC, PortfolioInput
from ..markets.us import US_WORKING_TARGETS
from ..versions import IMPLEMENTATION_KIND, PORTFOLIO_OFFICIAL, PORTFOLIO_US_WORKING
from .identifiers import IdentifierRegistry

# Official v1.1 target weights. Cash 0% is official snapshot state, not a global freeze.
OFFICIAL_V11_TARGETS = {
    "asml": 0.09,
    "lrcx": 0.06,
    "klac": 0.055,
    "tokyo_electron": 0.05,
    "hanmi": 0.045,
    "nvda": 0.08,
    "amd": 0.05,
    "avgo": 0.05,
    "qcom": 0.04,
    "intc": 0.03,
    "msft": 0.07,
    "googl": 0.07,
    "amzn": 0.06,
    "rtx": 0.06,
    "stry": 0.055,
    "etn": 0.05,
    "hubb": 0.035,
    "gev": 0.03,
    "rok": 0.02,
}


class PortfolioEngine:
    def __init__(self, registry: IdentifierRegistry | None = None, cash_weight: float = 0.0):
        self.registry = registry or IdentifierRegistry()
        self.cash_weight = cash_weight

    def from_input(self, spec: PortfolioInput, snapshot_at: datetime, qgv_by_company: dict[str, QGVSnapshot] | None = None) -> PortfolioSnapshot:
        qgv_by_company = qgv_by_company or {}
        holdings = []
        for item in spec.holdings:
            ident = None
            try:
                ident = self.registry.get(item.company_id)
            except Exception:
                ident = None
            snap = qgv_by_company.get(item.company_id)
            holdings.append(
                Holding(
                    company_id=item.company_id,
                    ticker=item.ticker or (ident.ticker if ident else item.company_id),
                    target_weight=item.target_weight,
                    actual_weight=item.target_weight if spec.cash_weight == 0 else item.target_weight * (1 - spec.cash_weight),
                    weight_gap=0.0,
                    qgv_snapshot_id=snap.qgv_snapshot_id if snap else None,
                    ambiguity_flags=ident.ambiguity_flags if ident else (),
                )
            )
        return PortfolioSnapshot(
            portfolio_snapshot_id=f"pf_{uuid4().hex[:12]}",
            portfolio_version=spec.version,
            snapshot_at=snapshot_at,
            base_currency=spec.base_currency,
            holdings=tuple(holdings),
            cash_weight=spec.cash_weight,
            weight_sum=spec.weight_sum(),
            policy_version=spec.version,
            implementation_kind=IMPLEMENTATION_KIND,
            synthetic=any(s.synthetic for s in qgv_by_company.values()) if qgv_by_company else True,
            role=spec.role,
        )

    def official_v11(self, snapshot_at: datetime, qgv_by_company: dict[str, QGVSnapshot] | None = None) -> PortfolioSnapshot:
        qgv_by_company = qgv_by_company or {}
        holdings = []
        for cid, w in OFFICIAL_V11_TARGETS.items():
            ident = self.registry.get(cid)
            snap = qgv_by_company.get(cid)
            holdings.append(
                Holding(
                    company_id=cid,
                    ticker=ident.ticker,
                    target_weight=w,
                    actual_weight=w if self.cash_weight == 0 else w * (1 - self.cash_weight),
                    weight_gap=0.0,
                    qgv_snapshot_id=snap.qgv_snapshot_id if snap else None,
                    ambiguity_flags=ident.ambiguity_flags,
                )
            )
        weight_sum = sum(h.target_weight for h in holdings) + self.cash_weight
        return PortfolioSnapshot(
            portfolio_snapshot_id=f"pf_{uuid4().hex[:12]}",
            portfolio_version=PORTFOLIO_OFFICIAL,
            snapshot_at=snapshot_at,
            base_currency="USD",
            holdings=tuple(holdings),
            cash_weight=self.cash_weight,
            weight_sum=weight_sum,
            policy_version=PORTFOLIO_OFFICIAL,
            implementation_kind=IMPLEMENTATION_KIND,
            synthetic=any(s.synthetic for s in qgv_by_company.values()) if qgv_by_company else True,
            role=ROLE_FIXTURE,
        )

    def us_working(self, snapshot_at: datetime, qgv_by_company: dict[str, QGVSnapshot] | None = None) -> PortfolioSnapshot:
        """US-listed working book. Does not replace Official v1.1."""
        qgv_by_company = qgv_by_company or {}
        holdings = []
        for cid, w in US_WORKING_TARGETS.items():
            ident = self.registry.get(cid)
            snap = qgv_by_company.get(cid)
            holdings.append(
                Holding(
                    company_id=cid,
                    ticker=ident.ticker,
                    target_weight=w,
                    actual_weight=w if self.cash_weight == 0 else w * (1 - self.cash_weight),
                    weight_gap=0.0,
                    qgv_snapshot_id=snap.qgv_snapshot_id if snap else None,
                    ambiguity_flags=ident.ambiguity_flags,
                )
            )
        return PortfolioSnapshot(
            portfolio_snapshot_id=f"pf_us_{uuid4().hex[:12]}",
            portfolio_version=PORTFOLIO_US_WORKING,
            snapshot_at=snapshot_at,
            base_currency="USD",
            holdings=tuple(holdings),
            cash_weight=self.cash_weight,
            weight_sum=sum(h.target_weight for h in holdings) + self.cash_weight,
            policy_version=PORTFOLIO_US_WORKING,
            implementation_kind=IMPLEMENTATION_KIND,
            synthetic=any(s.synthetic for s in qgv_by_company.values()) if qgv_by_company else True,
            role=ROLE_FIXTURE,
        )

    def evaluate(self, portfolio: PortfolioSnapshot, prices: dict[str, float]) -> PortfolioSnapshot:
        valued = []
        market_values = []
        for h in portfolio.holdings:
            px = prices.get(h.company_id)
            if h.shares is not None and px is not None:
                mv = h.shares * px
            else:
                mv = None
            market_values.append(mv)
            valued.append((h, px, mv))
        known = [mv for mv in market_values if mv is not None]
        total = sum(known) if known else None
        out = []
        for h, px, mv in valued:
            actual = (mv / total) if (mv is not None and total) else h.actual_weight
            gap = (actual - h.target_weight) if actual is not None else None
            out.append(
                Holding(
                    company_id=h.company_id,
                    ticker=h.ticker,
                    target_weight=h.target_weight,
                    shares=h.shares,
                    average_cost=h.average_cost,
                    price=px,
                    actual_weight=actual,
                    weight_gap=gap,
                    qgv_snapshot_id=h.qgv_snapshot_id,
                    ambiguity_flags=h.ambiguity_flags,
                )
            )
        return PortfolioSnapshot(
            portfolio_snapshot_id=f"pf_{uuid4().hex[:12]}",
            portfolio_version=portfolio.portfolio_version,
            snapshot_at=portfolio.snapshot_at,
            base_currency=portfolio.base_currency,
            holdings=tuple(out),
            cash_weight=portfolio.cash_weight,
            weight_sum=sum(h.target_weight for h in out) + portfolio.cash_weight,
            policy_version=portfolio.policy_version,
            implementation_kind=IMPLEMENTATION_KIND,
            synthetic=portfolio.synthetic,
            role=portfolio.role,
        )
