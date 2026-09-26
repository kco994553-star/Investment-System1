"""Model / Actual / Gap (PIL §9, §13, §14). Separate immutable objects; the gap is descriptive, never an order.

C-26: ActualPortfolioSnapshot is built only from broker/user position data (source BROKER / USER_ENTERED); the existing
contracts.models.Holding.actual_weight is a model-side value and is never accepted here.
C-27: PortfolioGap has no side/quantity; it is not IntegrationResult.order_intents and uses gap = model - actual.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from .money import Money
from .quality import DataQuality, worst
from .versioning import content_hash


class PositionSource(str, Enum):
    BROKER = "BROKER"
    USER_ENTERED = "USER_ENTERED"


@dataclass(frozen=True)
class ModelHolding:
    security_id: str
    target_weight: float
    rank: Optional[int] = None
    reason_codes: tuple[str, ...] = ()
    qgv_snapshot_ref: Optional[str] = None  # references only; upstream scores are never copied or altered
    technical_snapshot_ref: Optional[str] = None
    macro_snapshot_ref: Optional[str] = None


@dataclass(frozen=True)
class ModelPortfolioSnapshot:
    strategy_version_id: str
    as_of: datetime
    universe_snapshot_id: str
    holdings: tuple[ModelHolding, ...]
    cash_target: float
    portfolio_policy_id: str
    calculation_version: str

    def __post_init__(self) -> None:
        ids = [h.security_id for h in self.holdings]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate security_id in model portfolio")
        if any(h.target_weight < 0 for h in self.holdings) or self.cash_target < 0:
            raise ValueError("negative target weight")
        if abs(sum(h.target_weight for h in self.holdings) + self.cash_target - 1.0) > 1e-9:
            raise ValueError("model weights + cash_target must sum to 1")

    @property
    def snapshot_hash(self) -> str:
        return content_hash(self)


@dataclass(frozen=True)
class Position:
    account_id: str
    security_id: str
    quantity: Decimal
    market_value: Money
    price_as_of: datetime
    position_as_of: datetime
    source: PositionSource
    data_quality: DataQuality
    average_cost: Optional[Money] = None


@dataclass(frozen=True)
class ActualPortfolioSnapshot:
    """What the user actually holds. complete=False means the positions list may be missing accounts/positions: absent
    securities are then UNKNOWN, not zero (Missing != zero)."""

    user_id: str
    account_scope: tuple[str, ...]
    as_of: datetime
    positions: tuple[Position, ...]
    cash: tuple[Money, ...]
    base_currency: str
    complete: bool
    sync_quality: DataQuality

    def __post_init__(self) -> None:
        for p in self.positions:
            if not isinstance(p.source, PositionSource):
                raise TypeError("positions must come from BROKER or USER_ENTERED data")
            if p.account_id not in self.account_scope:
                raise ValueError(f"position account {p.account_id} outside account_scope")
        for mv in [p.market_value for p in self.positions] + list(self.cash):
            if mv.currency != self.base_currency:
                raise ValueError("amounts must be converted to base_currency explicitly (money.convert) before aggregation")

    def total_value(self) -> Decimal:
        return sum((p.market_value.amount for p in self.positions), Decimal(0)) + sum((c.amount for c in self.cash), Decimal(0))

    def weights(self) -> dict[str, Decimal]:
        """security_id -> weight of total value (positions of the same security across accounts are summed)."""
        tot = self.total_value()
        if tot <= 0:
            return {}
        out: dict[str, Decimal] = {}
        for p in self.positions:
            out[p.security_id] = out.get(p.security_id, Decimal(0)) + p.market_value.amount
        return {k: v / tot for k, v in out.items()}


@dataclass(frozen=True)
class GapRow:
    security_id: str
    model_weight: Optional[float]
    actual_weight: Optional[float]
    gap: Optional[float]  # model - actual; None when either side is unknown
    quality_status: DataQuality
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PortfolioGapSnapshot:
    model_snapshot_hash: str
    actual_snapshot_ref: str
    calculated_at: datetime
    rows: tuple[GapRow, ...]
    quality_status: DataQuality
    note: str = "Descriptive difference between model and actual weights. Not a BUY/SELL signal or order quantity."


def portfolio_gap(model: ModelPortfolioSnapshot, actual: ActualPortfolioSnapshot, actual_ref: str,
                  calculated_at: datetime) -> PortfolioGapSnapshot:
    """gap = model_weight - actual_weight per security. A security held but not in the model has model_weight 0
    (the model is complete by construction); a model security absent from an INCOMPLETE actual snapshot has
    actual_weight None (unknown) and gap None."""
    aw = {k: float(v) for k, v in actual.weights().items()}
    pos_q = {}
    for p in actual.positions:
        pos_q[p.security_id] = worst(pos_q.get(p.security_id, DataQuality.VALID), p.data_quality)
    rows = []
    for sid in sorted({h.security_id for h in model.holdings} | set(aw)):
        mw = next((h.target_weight for h in model.holdings if h.security_id == sid), 0.0)
        if sid in aw:
            a, q, rc = aw[sid], worst(pos_q[sid], actual.sync_quality), ()
        elif actual.complete:
            a, q, rc = 0.0, actual.sync_quality, ("NOT_HELD",)
        else:
            a, q, rc = None, DataQuality.UNRESOLVED, ("ACTUAL_UNKNOWN_INCOMPLETE_SNAPSHOT",)
        rows.append(GapRow(sid, mw, a, None if a is None else mw - a, q, rc))
    return PortfolioGapSnapshot(model.snapshot_hash, actual_ref, calculated_at, tuple(rows),
                                worst(*(r.quality_status for r in rows)) if rows else actual.sync_quality)
