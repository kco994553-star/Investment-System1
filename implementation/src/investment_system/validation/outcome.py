"""Link outcomes to immutable predictions. Child records only. NEW IMPLEMENTATION."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..qgv.track_record import TrackRecordStore
from .records import ScopedTrackStore


class HorizonNotElapsed(RuntimeError):
    pass


def parse_horizon(window: str) -> timedelta:
    raw = window.strip().lower()
    if raw.endswith("d"):
        return timedelta(days=int(raw[:-1]))
    if raw.endswith("h"):
        return timedelta(hours=int(raw[:-1]))
    raise ValueError(f"unsupported horizon {window}")


def link_outcome(
    store: ScopedTrackStore | TrackRecordStore,
    prediction_record_id: str,
    evaluate_at: datetime,
    realized: dict,
    window: str | None = None,
):
    inner = store.store if isinstance(store, ScopedTrackStore) else store
    parent = inner.get(prediction_record_id)
    if parent.record_type == "OUTCOME":
        raise ValueError("cannot attach outcome to an outcome")
    horizon = window or parent.payload.get("evaluation_horizon") or parent.outcome_window or "20d"
    due = parent.decision_at + parse_horizon(str(horizon))
    if evaluate_at < due:
        raise HorizonNotElapsed(f"{evaluate_at.isoformat()} before horizon {due.isoformat()}")
    predicted = (parent.payload.get("prediction") or {}).get("expected_return")
    realized_ret = realized.get("realized_return")
    error = None
    if predicted is not None and realized_ret is not None:
        error = {"expected_return": predicted, "realized_return": realized_ret, "delta": realized_ret - predicted}
    metrics = {
        "realized": dict(realized),
        "error": error,
        "calibration_result": None,
        "official_pass": False,
        "parent_mutated": False,
    }
    child = inner.evaluate_outcome(prediction_record_id, str(horizon), metrics)
    # parent payload must stay bit-identical
    after = inner.get(prediction_record_id)
    if after.payload != parent.payload:
        raise RuntimeError("parent prediction mutated")
    return child
