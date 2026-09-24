"""File store: one serialization per immutable record, same reloadable JSON array."""

import json
from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.enums import TrackScope
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.records import ScopedTrackStore

AS = datetime(2025, 3, 31, tzinfo=timezone.utc)


def test_encoded_once_and_reload_equivalent(tmp_path):
    path = Path(tmp_path) / "s.json"
    fs = FileTrackRecordStore(path)
    st = ScopedTrackStore(fs)
    ids = [st.record(TrackScope.QGV, f"c{i}", AS, (f"s{i}",), {"prediction": {"i": i}}).track_record_id for i in range(40)]
    child = st.outcome(ids[0], "20d", {"realized_return": 0.1})
    assert len(fs._encoded) == 41
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert [r["track_record_id"] for r in rows] == ids + [child.track_record_id]
    again = FileTrackRecordStore(path)
    assert again.get(ids[0]).outcome_metrics is None  # parent untouched by child outcome
    assert again.get(child.track_record_id).outcome_metrics["realized_return"] == 0.1
    assert again.get(ids[39]).payload["prediction"]["i"] == 39
