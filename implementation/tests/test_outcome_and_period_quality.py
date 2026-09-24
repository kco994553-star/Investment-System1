from datetime import datetime, timedelta, timezone

from investment_system.contracts.enums import TrackScope
from investment_system.providers.sec_companyfacts import facts_to_raw, load_facts_file
from investment_system.validation.outcome import HorizonNotElapsed, link_outcome
from investment_system.validation.records import ScopedTrackStore
from pathlib import Path

AS_OF = datetime(2026, 9, 1, tzinfo=timezone.utc)
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "sec_companyfacts_mini.json"

LABELED = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2024-01-28", "val": 60, "filed": "2024-02-21", "form": "10-K"},
                        {"end": "2025-01-26", "val": 130, "filed": "2025-02-26", "form": "10-K"},
                    ]
                }
            }
        }
    }
}


def test_unlabeled_sec_is_partial_not_verified():
    raw = facts_to_raw("nvda", "0001045810", load_facts_file(FIX), datetime(2026, 9, 14, tzinfo=timezone.utc), synthetic=True)
    assert raw.period_quality == "PARTIAL"
    assert "UNLABELED_SEC_FORM" in raw.stamp.quality_flags
    labeled = facts_to_raw("nvda", "0001045810", LABELED, datetime(2026, 9, 23, tzinfo=timezone.utc), synthetic=True)
    assert labeled.period_quality == "FORM_ALIGNED"
    assert labeled.revenue == 130
    assert labeled.revenue_prev == 60


def test_outcome_is_child_and_horizon_gated():
    store = ScopedTrackStore()
    rec = store.record(
        TrackScope.QGV,
        "nvda",
        AS_OF,
        ("snap1",),
        {
            "prediction": {"expected_return": 0.05},
            "decision": {"gate": "PASS"},
            "evaluation_horizon": "20d",
        },
    )
    parent_payload = dict(rec.payload)
    try:
        link_outcome(store, rec.track_record_id, AS_OF + timedelta(days=5), {"realized_return": 0.02})
        assert False
    except HorizonNotElapsed:
        pass
    child = link_outcome(store, rec.track_record_id, AS_OF + timedelta(days=21), {"realized_return": 0.02})
    assert child.record_type == "OUTCOME"
    assert child.track_record_id != rec.track_record_id
    assert rec.track_record_id in child.source_snapshot_refs
    assert child.outcome_metrics["error"]["delta"] == 0.02 - 0.05
    assert child.outcome_metrics["parent_mutated"] is False
    assert store.store.get(rec.track_record_id).payload == parent_payload
