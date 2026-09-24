"""File-backed immutable Track Record store. NEW IMPLEMENTATION."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..contracts.models import TrackRecord
from ..qgv.track_record import ImmutableTrackRecordError, TrackRecordStore


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def record_from_dict(row: dict) -> TrackRecord:
    return TrackRecord(
        track_record_id=row["track_record_id"],
        record_type=row["record_type"],
        subject_id=row["subject_id"],
        decision_at=_parse_dt(row["decision_at"]),
        source_snapshot_refs=tuple(row.get("source_snapshot_refs") or ()),
        payload=dict(row.get("payload") or {}),
        outcome_window=row.get("outcome_window"),
        outcome_metrics=row.get("outcome_metrics"),
        immutable=True,
    )


class FileTrackRecordStore(TrackRecordStore):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Records are immutable (outcomes are new child records), so each one is
        # serialized once. Re-serializing the whole store on every write made a
        # 500-name as_of run O(n^2) (~41s). The file stays one complete JSON array
        # rewritten on each write, so reload and crash behaviour are unchanged.
        self._encoded: dict[str, str] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
            for row in raw:
                rec = record_from_dict(row)
                self._records[rec.track_record_id] = rec

    def _flush(self) -> None:
        for rid, rec in self._records.items():
            if rid not in self._encoded:
                self._encoded[rid] = json.dumps(rec.to_dict(), indent=2, default=str)
        body = ",\n".join(self._encoded[rid] for rid in self._records)
        self.path.write_text("[\n" + body + "\n]" if body else "[]", encoding="utf-8")

    def record_decision(self, *args, **kwargs) -> TrackRecord:
        rec = super().record_decision(*args, **kwargs)
        self._flush()
        return rec

    def evaluate_outcome(self, track_record_id: str, window: str, metrics: dict) -> TrackRecord:
        child = super().evaluate_outcome(track_record_id, window, metrics)
        self._flush()
        return child

    def overwrite(self, track_record_id: str, **_kwargs) -> None:
        raise ImmutableTrackRecordError(f"cannot mutate {track_record_id}")
