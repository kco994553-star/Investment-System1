"""Frozen Q/G weights and V candidate constraints. NEW IMPLEMENTATION.

Source: QGV Analysis v1.7.6 §18.3
Q7 remains Management Quality (C-03 OPEN vs Integrated Spec Capital Allocation).
V production aggregate is not emitted.
"""

from __future__ import annotations

from ..contracts.enums import CalibrationLifecycle, ProfileKind, QualityState


Q_WEIGHTS = {
    "competitive_advantage": 0.20,
    "roic_wacc": 0.20,
    "market_position": 0.15,
    "fcf_quality": 0.15,
    "margin_quality": 0.10,
    "financial_health": 0.10,
    "management_quality": 0.10,  # C-03: do not rename to capital_allocation
}

G_WEIGHTS = {
    "next_3_5y_growth": 0.25,
    "growth_efficiency": 0.20,
    "revenue_growth": 0.15,
    "eps_fcf_per_share_growth": 0.15,
    "growth_durability": 0.15,
    "excess_growth_vs_industry": 0.10,
}

V_FACTORS = (
    "fundamental_value",
    "peer_relative_value",
    "historical_valuation",
    "sector_context",
    "theme_premium_discount",
    "reverse_dcf",
    "margin_of_safety",
)

FINANCIAL_NOT_APPLICABLE = frozenset({"roic_wacc"})


def validate_q_g_weights() -> None:
    if abs(sum(Q_WEIGHTS.values()) - 1.0) > 1e-12:
        raise ValueError("Q weights must sum to 1")
    if abs(sum(G_WEIGHTS.values()) - 1.0) > 1e-12:
        raise ValueError("G weights must sum to 1")


def validate_v_candidate_weights(weights: dict[str, float]) -> list[str]:
    errors: list[str] = []
    if set(weights) != set(V_FACTORS):
        errors.append("V candidate must include exactly the 7 frozen V factors")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        errors.append(f"V weights must sum to 1, got {total}")
    for k, w in weights.items():
        if w < 0.05 - 1e-12 or w > 0.30 + 1e-12:
            errors.append(f"{k} weight {w} outside 5-30% constraint")
    return errors


# User-directed Initial Prior. PROVISIONAL. Not STANDARD / not CALIBRATED.
V_INITIAL_PRIOR = {
    "fundamental_value": 0.25,
    "reverse_dcf": 0.20,
    "peer_relative_value": 0.15,
    "historical_valuation": 0.15,
    "margin_of_safety": 0.10,
    "sector_context": 0.10,
    "theme_premium_discount": 0.05,
}

EQUAL_V_RESEARCH = {k: 1.0 / 7.0 for k in V_FACTORS}

# Research-only candidates. Not production.
V_CANDIDATES = {
    "initial_prior": {
        "lifecycle": CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR,
        "weights": V_INITIAL_PRIOR,
    },
    "equal_research": {
        "lifecycle": CalibrationLifecycle.RESEARCH,
        "weights": EQUAL_V_RESEARCH,
    },
    "mos_tilt_research": {
        "lifecycle": CalibrationLifecycle.RESEARCH,
        "weights": {
            "fundamental_value": 0.15,
            "peer_relative_value": 0.15,
            "historical_valuation": 0.10,
            "sector_context": 0.10,
            "theme_premium_discount": 0.10,
            "reverse_dcf": 0.15,
            "margin_of_safety": 0.25,
        },
    },
}


def factor_applicable(factor_id: str, profile: ProfileKind) -> bool:
    if profile == ProfileKind.FINANCIAL and factor_id in FINANCIAL_NOT_APPLICABLE:
        return False
    return True


def missing_is_not_zero(obs_score: float | None, quality: QualityState) -> float | None:
    if quality in {
        QualityState.MISSING_DATA,
        QualityState.BLOCKED_DEPENDENCY,
        QualityState.PIT_UNAVAILABLE,
        QualityState.NOT_APPLICABLE,
    }:
        return None
    return obs_score
