from datetime import datetime, timezone
from pathlib import Path

from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import (
    attach_name_outcomes,
    full_pit_candidate_eval,
    prediction_realized_table,
    run_as_of,
)
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
    {"price": 11.0, "observed_at": datetime(2026, 6, 20, tzinfo=timezone.utc), "adjusted": True},
]


def test_prediction_realized_is_not_calibration(tmp_path):
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "c.json"))
    row = run_as_of(AS0, {"nvda": PAYLOAD}, {"nvda": BARS}, store, ("nvda",))
    links = attach_name_outcomes(store, row["name_records"], AS0, AS1, {"nvda": BARS})
    table = prediction_realized_table(row, {"links": links})
    assert table["calibrated"] is False
    assert table["oos"] is False
    assert table["n"] == 1
    ev = full_pit_candidate_eval([row, {"quality": {}}], [{"links": links}])
    assert ev["full_pit_pass"] is False
    assert ev["checks"]["parent_immutable"] is True
    assert ev["checks"]["v_weights_not_refit"] is True
