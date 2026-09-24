"""QGV Compatibility annotation. NEW IMPLEMENTATION.

Replaces in-Technical QGV Fusion (C-15). Does not change Q/G/V or Technical scores.
Does not emit target weights or orders.
"""

from __future__ import annotations

from enum import Enum

from ..contracts.models import QGVSnapshot, TechnicalSnapshot


class CompatibilityLabel(str, Enum):
    ALIGNED = "ALIGNED"
    ENTRY_CONFLICT = "ENTRY_CONFLICT"
    FUNDAMENTAL_CONFLICT = "FUNDAMENTAL_CONFLICT"
    ALIGNED_NEGATIVE = "ALIGNED_NEGATIVE"
    INSUFFICIENT = "INSUFFICIENT"


def _qgv_strong(snap: QGVSnapshot | None) -> bool | None:
    if snap is None or snap.Q_score is None or snap.G_score is None:
        return None
    return ((snap.Q_score + snap.G_score) / 2.0) >= 50.0


def _ta_strong(snap: TechnicalSnapshot | None) -> bool | None:
    if snap is None:
        return None
    name = snap.regime.value
    if name in {"UNKNOWN"}:
        return None
    return name in {"TREND_UP"}


def annotate(qgv: QGVSnapshot | None, technical: TechnicalSnapshot | None) -> dict:
    qs = _qgv_strong(qgv)
    ts = _ta_strong(technical)
    if qs is None or ts is None:
        label = CompatibilityLabel.INSUFFICIENT
    elif qs and ts:
        label = CompatibilityLabel.ALIGNED
    elif qs and not ts:
        label = CompatibilityLabel.ENTRY_CONFLICT
    elif (not qs) and ts:
        label = CompatibilityLabel.FUNDAMENTAL_CONFLICT
    else:
        label = CompatibilityLabel.ALIGNED_NEGATIVE
    return {
        "label": label.value,
        "mutates_qgv": False,
        "mutates_technical": False,
        "mutates_macro": False,
        "emits_target_weight": False,
        "emits_order": False,
        "canonical": "QGV_COMPATIBILITY",
        "legacy_alias": "QGV_FUSION_ANNOTATION_ONLY",
    }
