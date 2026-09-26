"""Personal Fit v1 (PIL §15): a multi-axis Decision Context, not a single score. Decision states are not BUY/SELL.
Upstream QGV / Technical / Macro scores are referenced by snapshot id only and never modified.

No decision policy is implemented in P0 (decision_policy_version must be supplied by a later, reviewed policy)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .quality import DataQuality


class FitAxis(str, Enum):
    FUNDAMENTAL = "FUNDAMENTAL"
    TECHNICAL = "TECHNICAL"
    MACRO = "MACRO"
    PORTFOLIO_FIT = "PORTFOLIO_FIT"
    RISK = "RISK"
    ACCOUNT_CONTEXT = "ACCOUNT_CONTEXT"


class DecisionState(str, Enum):
    OBSERVE = "OBSERVE"
    ELIGIBLE_TO_ADD = "ELIGIBLE_TO_ADD"
    HOLD_CONTEXT = "HOLD_CONTEXT"
    REBALANCE_REVIEW = "REBALANCE_REVIEW"
    RISK_REVIEW = "RISK_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AxisContext:
    axis: FitAxis
    quality: DataQuality
    reason_codes: tuple[str, ...]
    source_snapshot_ref: Optional[str] = None  # e.g. a QGV snapshot id; the upstream value itself is not stored here


@dataclass(frozen=True)
class PersonalFitSnapshot:
    strategy_version_id: str
    security_id: str
    axes: tuple[AxisContext, ...]
    decision_state: DecisionState
    decision_policy_version: str
    reason_codes: tuple[str, ...]
    calculated_at: datetime
    qgv_snapshot_id: Optional[str] = None
    technical_snapshot_id: Optional[str] = None
    macro_snapshot_id: Optional[str] = None
    model_portfolio_snapshot_hash: Optional[str] = None
    actual_portfolio_snapshot_ref: Optional[str] = None
    gap_snapshot_ref: Optional[str] = None

    def __post_init__(self) -> None:
        axes = [a.axis for a in self.axes]
        if len(axes) != len(set(axes)):
            raise ValueError("duplicate axis")
        if not self.decision_policy_version:
            raise ValueError("decision_policy_version is required (no default policy in P0)")
        # a critical axis that is unresolved/invalid can only yield a restricted state
        bad = any(a.quality in (DataQuality.UNRESOLVED, DataQuality.INVALID) for a in self.axes)
        if bad and self.decision_state not in (DecisionState.OBSERVE, DecisionState.BLOCKED):
            raise ValueError("unresolved/invalid axis allows only OBSERVE or BLOCKED")
