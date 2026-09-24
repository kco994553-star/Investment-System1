"""Immutable track record store. NEW IMPLEMENTATION."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ..contracts.models import TrackRecord


class ImmutableTrackRecordError(RuntimeError):
    pass


class TrackRecordStore:
    def __init__(self) -> None:
        self._records: dict[str, TrackRecord] = {}

    def record_decision(
        self,
        record_type: str,
        subject_id: str,
        decision_at: datetime,
        source_snapshot_refs: tuple[str, ...],
        payload: dict,
    ) -> TrackRecord:
        rec = TrackRecord(
            track_record_id=f"tr_{uuid4().hex[:12]}",
            record_type=record_type,
            subject_id=subject_id,
            decision_at=decision_at,
            source_snapshot_refs=source_snapshot_refs,
            payload=dict(payload),
            immutable=True,
        )
        self._records[rec.track_record_id] = rec
        return rec

    def get(self, track_record_id: str) -> TrackRecord:
        return self._records[track_record_id]

    def overwrite(self, track_record_id: str, **_kwargs) -> None:
        raise ImmutableTrackRecordError(f"cannot mutate {track_record_id}")

    def evaluate_outcome(self, track_record_id: str, window: str, metrics: dict) -> TrackRecord:
        old = self._records[track_record_id]
        child = TrackRecord(
            track_record_id=f"tr_{uuid4().hex[:12]}",
            record_type="OUTCOME",
            subject_id=old.subject_id,
            decision_at=old.decision_at,
            source_snapshot_refs=old.source_snapshot_refs + (old.track_record_id,),
            payload=dict(old.payload),
            outcome_window=window,
            outcome_metrics=dict(metrics),
            immutable=True,
        )
        self._records[child.track_record_id] = child
        return child

    def __len__(self) -> int:
        return len(self._records)
