from datetime import datetime, timezone
from pathlib import Path

from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import run_as_of, summarize_multi_pit
from investment_system.validation.records import ScopedTrackStore

AS_OF = datetime(2025, 3, 15, tzinfo=timezone.utc)
PAYLOAD = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2024-01-28", "val": 60, "filed": "2024-02-21", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"}
                    ]
                }
            }
        }
    }
}


def test_pit_row_exposes_independent_snapshots(tmp_path):
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "t.json"))
    row = run_as_of(AS_OF, {"nvda": PAYLOAD}, {"nvda": []}, store, ("nvda",))
    assert row["ablation_ready"] is True
    assert "qgv+technical+macro" in row["ablation_arms"]
    assert "nvda" in row["snapshot_ids"]["qgv"]
    assert row["compatibility"]["nvda"]["mutates_qgv"] is False
    summary = summarize_multi_pit({"rows": [row]})
    assert summary["calibrated"] is False
    assert summary["full_pit_pass"] is False
