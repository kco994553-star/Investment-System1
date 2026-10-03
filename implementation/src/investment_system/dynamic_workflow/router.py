"""M0 deterministic risk router for Investment-System1.

Design invariants:
- governance-critical work always routes CRITICAL;
- HIGH impact + HIGH uncertainty routes CRITICAL;
- either HIGH impact or HIGH uncertainty routes DEEP;
- everything else routes FAST;
- routing never performs an investment calculation or mutation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Impact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Uncertainty(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WorkflowProfile(str, Enum):
    FAST = "FAST"
    DEEP = "DEEP"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Governance:
    d3_required: bool = False
    frozen_affected: bool = False
    official_affected: bool = False
    pit_policy_affected: bool = False
    holdout_affected: bool = False

    @property
    def critical(self) -> bool:
        return any((
            self.d3_required,
            self.frozen_affected,
            self.official_affected,
            self.pit_policy_affected,
            self.holdout_affected,
        ))


@dataclass(frozen=True)
class RouteRequest:
    request_id: str
    impact: Impact
    uncertainty: Uncertainty
    governance: Governance = Governance()


@dataclass(frozen=True)
class RouteResult:
    request_id: str
    profile: WorkflowProfile
    reasons: Tuple[str, ...]
    escalation_allowed: bool = True
    automatic_downgrade_allowed: bool = False

    def trace(self) -> dict:
        return {
            "request_id": self.request_id,
            "profile": self.profile.value,
            "reasons": list(self.reasons),
            "escalation_allowed": self.escalation_allowed,
            "automatic_downgrade_allowed": self.automatic_downgrade_allowed,
        }


def route(request: RouteRequest) -> RouteResult:
    reasons = []

    if request.governance.critical:
        if request.governance.d3_required:
            reasons.append("D3_REQUIRED")
        if request.governance.frozen_affected:
            reasons.append("FROZEN_AFFECTED")
        if request.governance.official_affected:
            reasons.append("OFFICIAL_AFFECTED")
        if request.governance.pit_policy_affected:
            reasons.append("PIT_POLICY_AFFECTED")
        if request.governance.holdout_affected:
            reasons.append("HOLDOUT_AFFECTED")
        return RouteResult(request.request_id, WorkflowProfile.CRITICAL, tuple(reasons))

    if request.impact is Impact.HIGH and request.uncertainty is Uncertainty.HIGH:
        return RouteResult(
            request.request_id,
            WorkflowProfile.CRITICAL,
            ("HIGH_IMPACT", "HIGH_UNCERTAINTY"),
        )

    if request.impact is Impact.HIGH or request.uncertainty is Uncertainty.HIGH:
        if request.impact is Impact.HIGH:
            reasons.append("HIGH_IMPACT")
        if request.uncertainty is Uncertainty.HIGH:
            reasons.append("HIGH_UNCERTAINTY")
        return RouteResult(request.request_id, WorkflowProfile.DEEP, tuple(reasons))

    return RouteResult(
        request.request_id,
        WorkflowProfile.FAST,
        ("NO_ESCALATION_SIGNAL",),
    )
