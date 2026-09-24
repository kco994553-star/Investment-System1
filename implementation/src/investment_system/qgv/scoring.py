"""Q/G aggregation and calibration-ready V candidates. NEW IMPLEMENTATION."""

from __future__ import annotations

from typing import Mapping

from ..contracts.enums import CalibrationLifecycle, CoverageState, ProfileKind, QualityState
from ..contracts.models import FactorObservation, VCandidate
from .factors import (
    G_WEIGHTS,
    Q_WEIGHTS,
    V_CANDIDATES,
    V_FACTORS,
    factor_applicable,
    missing_is_not_zero,
    validate_q_g_weights,
    validate_v_candidate_weights,
)


validate_q_g_weights()


def _weighted(weights: dict[str, float], observations: Mapping[str, FactorObservation], profile: ProfileKind) -> tuple[float | None, CoverageState, list[str]]:
    used = 0.0
    acc = 0.0
    blocked = False
    missing_any = False
    notes: list[str] = []
    for fid, w in weights.items():
        if not factor_applicable(fid, profile):
            notes.append(f"{fid}=NOT_APPLICABLE")
            continue
        obs = observations.get(fid)
        if obs is None:
            missing_any = True
            notes.append(f"{fid}=MISSING")
            continue
        score = missing_is_not_zero(obs.score_0_100, obs.quality)
        if obs.quality == QualityState.BLOCKED_DEPENDENCY:
            blocked = True
            notes.append(f"{fid}=BLOCKED")
            continue
        if score is None:
            missing_any = True
            notes.append(f"{fid}={obs.quality.value}")
            continue
        acc += w * score
        used += w
    if blocked:
        return None, CoverageState.BLOCKED, notes
    if used == 0:
        return None, CoverageState.BLOCKED, notes
    # Do not renormalize missing components (freeze rule).
    if missing_any or used < 1.0 - 1e-12:
        return acc, CoverageState.PARTIAL, notes
    return acc, CoverageState.READY, notes


def score_q(observations: Mapping[str, FactorObservation], profile: ProfileKind) -> tuple[float | None, CoverageState, list[str]]:
    return _weighted(Q_WEIGHTS, observations, profile)


def score_g(observations: Mapping[str, FactorObservation], profile: ProfileKind) -> tuple[float | None, CoverageState, list[str]]:
    return _weighted(G_WEIGHTS, observations, profile)


def score_v_candidates(observations: Mapping[str, FactorObservation]) -> tuple[VCandidate, ...]:
    out: list[VCandidate] = []
    for cid, spec in V_CANDIDATES.items():
        weights: dict[str, float] = spec["weights"]
        errors = validate_v_candidate_weights(weights)
        if errors:
            out.append(
                VCandidate(
                    candidate_id=cid,
                    lifecycle=spec["lifecycle"],
                    weights=weights,
                    v_score=None,
                    blocked_reason=";".join(errors),
                )
            )
            continue
        acc = 0.0
        used = 0.0
        blocked = False
        for fid in V_FACTORS:
            obs = observations.get(fid)
            if obs is None or obs.score_0_100 is None:
                blocked = True
                break
            if obs.quality in {QualityState.MISSING_DATA, QualityState.BLOCKED_DEPENDENCY, QualityState.PIT_UNAVAILABLE}:
                blocked = True
                break
            acc += weights[fid] * obs.score_0_100
            used += weights[fid]
        if blocked or abs(used - 1.0) > 1e-9:
            out.append(
                VCandidate(
                    candidate_id=cid,
                    lifecycle=spec["lifecycle"],
                    weights=weights,
                    v_score=None,
                    blocked_reason="incomplete V factors; no auto-reweight",
                )
            )
        else:
            out.append(
                VCandidate(
                    candidate_id=cid,
                    lifecycle=spec["lifecycle"],
                    weights=weights,
                    v_score=acc,
                    blocked_reason=None,
                )
            )
    return tuple(out)


def score_v_prior(observations: Mapping[str, FactorObservation], profile: ProfileKind) -> tuple[float | None, CoverageState, list[str]]:
    from .factors import V_INITIAL_PRIOR

    return _weighted(V_INITIAL_PRIOR, observations, profile)


def production_v_score(candidates: tuple[VCandidate, ...], prior_score: float | None = None, prior_cov=None) -> tuple[float | None, CalibrationLifecycle]:
    """Emit Initial Prior V when computable. Status is never STANDARD/CALIBRATED here."""
    return prior_score, CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR


def attractiveness_10(q: float | None, g: float | None) -> float | None:
    """NEW IMPLEMENTATION heuristic. PROVISIONAL. Not an official freeze constant."""
    if q is None or g is None:
        return None
    return round(((q + g) / 2.0) / 10.0, 2)
