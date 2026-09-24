from datetime import datetime, timezone
from pathlib import Path

from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import attach_name_outcomes, run_as_of
from investment_system.validation.records import ScopedTrackStore

AS_B = datetime(2025, 3, 15, tzinfo=timezone.utc)
AS_C = datetime(2025, 9, 1, tzinfo=timezone.utc)

PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {"end": "2024-12-31", "val": 100, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"},
                    ]
                }
            }
        }
    }
}

BARS = [
    {"price": 100.0, "observed_at": datetime(2025, 3, 1, tzinfo=timezone.utc)},
    {"price": 125.0, "observed_at": datetime(2025, 8, 15, tzinfo=timezone.utc)},
]


def test_outcomes_are_children_and_not_verified(tmp_path):
    ids = ("nvda", "msft")
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "o.json"))
    payloads = {cid: PAYLOAD for cid in ids}
    bars = {cid: BARS for cid in ids}
    row = run_as_of(AS_B, payloads, bars, store, ids)
    assert row["official_pass"] is False
    linked = attach_name_outcomes(store, row["name_records"], AS_B, AS_C, bars)
    assert linked["nvda"]["status"] == "LINKED"
    assert linked["nvda"]["parent_payload_intact"] is True
    assert abs(linked["nvda"]["realized_return"] - 0.25) < 1e-9
    parent = store.store.get(row["name_records"]["nvda"])
    assert parent.outcome_metrics is None
    assert row["real_data_verified"] is False
