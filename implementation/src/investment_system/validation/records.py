"""Scoped track records wrapping the existing immutable store."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.enums import TrackScope
from ..contracts.models import TrackRecord
from ..contracts.prediction import PredictionEnvelope
from ..qgv.track_record import ImmutableTrackRecordError, TrackRecordStore
from ..versions import IMPLEMENTATION_LINE, QGV_ANALYSIS_CONTRACT


class ScopedTrackStore:
    def __init__(self, store: TrackRecordStore | None = None) -> None:
        self.store = TrackRecordStore() if store is None else store

    def record(self, scope: TrackScope, subject_id: str, decision_at: datetime, refs: tuple[str, ...], payload: dict) -> TrackRecord:
        env = PredictionEnvelope(
            prediction_id=payload.get("prediction_id") or f"pred_{uuid4().hex[:12]}",
            as_of=decision_at,
            system_version=payload.get("system_version") or IMPLEMENTATION_LINE,
            module_version=payload.get("module_version") or QGV_ANALYSIS_CONTRACT,
            profile_id=payload.get("profile_id") or "unspecified",
            parameter_set_hash=payload.get("parameter_set_hash") or "none",
            input_snapshot_ids=refs,
            prediction=payload.get("prediction") or payload,
            decision=payload.get("decision") or {},
            scope=scope.value,
            evaluation_horizon=payload.get("evaluation_horizon"),
        )
        body = env.to_payload()
        body["kind"] = "TRACK_RECORD"
        return self.store.record_decision(f"{scope.value}_PREDICTION", subject_id, decision_at, refs, body)

    def outcome(self, track_record_id: str, window: str, metrics: dict) -> TrackRecord:
        return self.store.evaluate_outcome(track_record_id, window, metrics)
