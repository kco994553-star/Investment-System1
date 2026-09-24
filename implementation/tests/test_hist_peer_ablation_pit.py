from datetime import datetime, timezone
from pathlib import Path

from investment_system.validation.ablation import pit_ablation_dataset
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import attach_name_outcomes, run_as_of, v_coverage_matrix
from investment_system.validation.records import ScopedTrackStore

AS0 = datetime(2025, 6, 30, tzinfo=timezone.utc)
AS1 = datetime(2026, 6, 30, tzinfo=timezone.utc)
PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "val": 80, "filed": "2024-02-01", "form": "10-K", "fy": 2023, "fp": "FY", "accn": "z"},
                        {"end": "2024-12-31", "val": 100, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"},
                    ]
                }
            },
            "EarningsPerShareDiluted": {
                "units": {
                    "USD/shares": [
                        {"end": "2023-12-31", "val": 1.0, "filed": "2024-02-01", "form": "10-K", "fy": 2023, "fp": "FY", "accn": "z"},
                        {"end": "2024-12-31", "val": 2.0, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"},
                    ]
                }
            },
        }
    }
}
BARS = [
    {"price": 20.0, "observed_at": datetime(2024, 6, 30, tzinfo=timezone.utc), "adjusted": True},
    {"price": 40.0, "observed_at": datetime(2025, 6, 15, tzinfo=timezone.utc), "adjusted": True},
    {"price": 50.0, "observed_at": datetime(2026, 6, 15, tzinfo=timezone.utc), "adjusted": True},
]


def test_hist_and_peer_provenance_and_no_future_price(tmp_path):
    ids = ("nvda", "msft")
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "h.json"))
    row0 = run_as_of(AS0, {c: PAYLOAD for c in ids}, {c: BARS for c in ids}, store, ids)
    assert row0["quality"]["nvda"]["peer_n"] == 2
    assert row0["quality"]["nvda"]["peer_confidence"] == "LOW"
    assert row0["quality"]["nvda"]["hist_valuation"] is not None
    assert row0["quality"]["nvda"]["pit_price"] == 40.0
    mat = v_coverage_matrix(row0)
    assert mat["present"]["historical_valuation"] == 2
    assert mat["present"]["sector_context"] == 0
    assert mat["present"]["theme_premium_discount"] == 0
    row1 = run_as_of(AS1, {c: PAYLOAD for c in ids}, {c: BARS for c in ids}, store, ids)
    linked = attach_name_outcomes(store, row0["name_records"], AS0, AS1, {c: BARS for c in ids})
    assert linked["nvda"]["parent_payload_intact"] is True
    ab = pit_ablation_dataset(row0, row1)
    assert ab["kind"] == "ABLATION_PIT_DATASET"
    assert ab["full_pit_pass"] is False
    assert set(ab["rows"]) == {
        "qgv",
        "technical",
        "macro",
        "qgv+technical",
        "qgv+macro",
        "technical+macro",
        "qgv+technical+macro",
    }
    assert all(v["mutates_inputs"] is False for v in ab["rows"].values())
