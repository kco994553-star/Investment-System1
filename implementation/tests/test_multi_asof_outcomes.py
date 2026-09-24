from datetime import datetime, timezone
from pathlib import Path

from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import attach_name_outcomes, run_as_of
from investment_system.validation.records import ScopedTrackStore

AS0 = datetime(2025, 6, 30, tzinfo=timezone.utc)
AS1 = datetime(2026, 6, 30, tzinfo=timezone.utc)
PAYLOAD = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2024-12-31", "val": 100, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"}
                    ]
                }
            }
        }
    }
}
BARS = [
    {"price": 10.0, "observed_at": datetime(2025, 6, 20, tzinfo=timezone.utc), "adjusted": True},
    {"price": 12.0, "observed_at": datetime(2026, 6, 20, tzinfo=timezone.utc), "adjusted": True},
]


def test_child_outcome_does_not_rewrite_parent(tmp_path):
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "o.json"))
    row = run_as_of(AS0, {"nvda": PAYLOAD}, {"nvda": BARS}, store, ("nvda",))
    links = attach_name_outcomes(store, row["name_records"], AS0, AS1, {"nvda": BARS})
    assert links["nvda"]["status"] == "LINKED"
    assert links["nvda"]["parent_payload_intact"] is True
    parent = store.store.get(row["name_records"]["nvda"])
    assert parent.payload["prediction"].get("as_of") == AS0.isoformat()
    assert "px1" not in parent.payload["prediction"]
