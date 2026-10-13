"""Local PREVIEW recalculation using copies of the adopted v1 leaf weights.

Weights exposed here use percentages; the existing reducer uses fractions.
Q/G retain the existing analysis average and V remains separate. No official
Q/G/V parent weights are defined, and this module has no persistence or wire API.

Missing factors (user decision 2026-10-13, QGV_V2_CANDIDATE.md §2, applied to v1 and v2): an axis is the
weighted mean over the computed factors in their original weight ratios (renormalized), produced only when
>= 50% of the applicable axis weight is computed; below that the axis is NOT_AVAILABLE (score None, coverage
BLOCKED). A missing factor is never counted as 0. NOT_APPLICABLE factors leave both numerator and denominator.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType

from ..contracts.enums import CoverageState, ProfileKind, QualityState
from ..contracts.models import FactorObservation
from .factors import (
    G_WEIGHTS,
    Q_WEIGHTS,
    V_INITIAL_PRIOR,
    factor_applicable,
    missing_is_not_zero,
)
from ..personal.weights import SIBLING_SUM_TOLERANCE


@dataclass(frozen=True)
class AxisPreview:
    score: float | None = field(repr=False)
    coverage: CoverageState
    missing_factor_ids: tuple[str, ...]
    not_applicable_ids: tuple[str, ...]
    factors_available: int = 0
    factors_total: int = 0

    @property
    def missing_factor_count(self) -> int:
        return len(self.missing_factor_ids)


def _immutable_weights(
    weights: Mapping[str, Mapping[str, float]],
) -> Mapping[str, Mapping[str, float]]:
    return MappingProxyType({
        axis: MappingProxyType(dict(factors)) for axis, factors in weights.items()
    })


@dataclass(frozen=True)
class StrategyPreviewResult:
    axes: Mapping[str, AxisPreview]
    qg_preview_total: float | None = field(repr=False)
    official_weights: Mapping[str, Mapping[str, float]] = field(repr=False)
    effective_weights: Mapping[str, Mapping[str, float]] = field(repr=False)
    role: str = field(default="PREVIEW", init=False)
    parent_mix_note: str = field(default="UNDEFINED_PARENT_WEIGHTS", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "axes", MappingProxyType(dict(self.axes)))
        object.__setattr__(self, "official_weights", _immutable_weights(self.official_weights))
        object.__setattr__(self, "effective_weights", _immutable_weights(self.effective_weights))


MIN_AXIS_WEIGHT = 0.5


def _renormalized(fractions, observations, profile_kind):
    """Renormalized weighted mean over computed factors; (score, coverage, available, total)."""
    total_w = 0.0
    used = 0.0
    acc = 0.0
    blocked = False
    missing_any = False
    available = 0
    applicable = 0
    for fid, w in fractions.items():
        if not factor_applicable(fid, profile_kind):
            continue
        applicable += 1
        total_w += w
        obs = observations.get(fid)
        if obs is None:
            missing_any = True
            continue
        if obs.quality == QualityState.BLOCKED_DEPENDENCY:
            blocked = True
            continue
        score = missing_is_not_zero(obs.score_0_100, obs.quality)
        if score is None:
            missing_any = True
            continue
        available += 1
        acc += w * score
        used += w
    if blocked or used == 0 or total_w <= 0 or used / total_w < MIN_AXIS_WEIGHT:
        return None, CoverageState.BLOCKED, available, applicable
    coverage = CoverageState.PARTIAL if missing_any or used < total_w - 1e-12 else CoverageState.READY
    return acc / used, coverage, available, applicable


def official_v1_weight_copy() -> dict[str, dict[str, float]]:
    """Return fresh, mutable percentage copies in authoritative factor order."""
    return {
        axis: {factor_id: weight * 100.0 for factor_id, weight in factors.items()}
        for axis, factors in (("Q", Q_WEIGHTS), ("G", G_WEIGHTS), ("V", V_INITIAL_PRIOR))
    }


def _validate_percentage(value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0.0 <= value <= 100.0
        or not isfinite(value)
    ):
        raise ValueError("scores and weights must be finite numbers in [0, 100]")


def _validated_observations(
    observations: Mapping[str, FactorObservation],
) -> dict[str, FactorObservation]:
    if not isinstance(observations, Mapping):
        raise ValueError("observations must be a mapping of factor IDs to FactorObservation")
    copied = dict(observations)
    for factor_id, observation in copied.items():
        if (
            not isinstance(factor_id, str)
            or not isinstance(observation, FactorObservation)
            or observation.factor_id != factor_id
            or not isinstance(observation.quality, QualityState)
        ):
            raise ValueError("observations require matching factor IDs and QualityState values")
        if observation.score_0_100 is not None:
            _validate_percentage(observation.score_0_100)
    return copied


def recalculate_strategy_preview(
    observations: Mapping[str, FactorObservation],
    user_weights: Mapping[str, Mapping[str, float]] | None = None,
    profile_kind: ProfileKind = ProfileKind.GENERAL_CORPORATE,
) -> StrategyPreviewResult:
    """Apply complete axis weights or sparse overrides to an official copy.

    Every effective axis must sum to 100%, within the existing sibling tolerance
    expressed in percentage units. Inputs are rejected rather than normalized.
    Missing factors are renormalized (>= 50% of axis weight, else NOT_AVAILABLE);
    blocked and financial-profile behavior follow the existing semantics.
    """
    if not isinstance(profile_kind, ProfileKind):
        raise ValueError("profile_kind must be a ProfileKind")
    copied_observations = _validated_observations(observations)
    official = official_v1_weight_copy()
    effective = {axis: dict(factors) for axis, factors in official.items()}
    if user_weights is not None:
        if not isinstance(user_weights, Mapping):
            raise ValueError("user_weights must be a mapping of axes to factor weights")
        for axis, overrides in user_weights.items():
            if axis not in effective:
                raise ValueError("user_weights contains an unknown axis")
            if not isinstance(overrides, Mapping):
                raise ValueError("axis weights must be a mapping of factor IDs to percentages")
            for factor_id, value in overrides.items():
                if factor_id not in effective[axis]:
                    raise ValueError("user_weights contains an unknown factor for its axis")
                _validate_percentage(value)
                effective[axis][factor_id] = float(value)
    axes: dict[str, AxisPreview] = {}
    for axis, weights in effective.items():
        if abs(sum(weights.values()) - 100.0) > SIBLING_SUM_TOLERANCE * 100.0:
            raise ValueError("each axis weight sum must equal 100 percent")
        fractions = {factor_id: weight / 100.0 for factor_id, weight in weights.items()}
        score, coverage, available, applicable = _renormalized(fractions, copied_observations, profile_kind)
        missing: list[str] = []
        not_applicable: list[str] = []
        for factor_id in weights:
            if not factor_applicable(factor_id, profile_kind):
                not_applicable.append(factor_id)
                continue
            observation = copied_observations.get(factor_id)
            if observation is None or missing_is_not_zero(
                observation.score_0_100, observation.quality
            ) is None:
                missing.append(factor_id)
        axes[axis] = AxisPreview(score, coverage, tuple(missing), tuple(not_applicable), available, applicable)
    q, g = axes["Q"].score, axes["G"].score
    total = None if q is None or g is None else round((q + g) / 2.0, 4)
    return StrategyPreviewResult(axes, total, official, effective)
