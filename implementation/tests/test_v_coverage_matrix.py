from datetime import datetime, timezone
from pathlib import Path

from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import run_as_of, v_coverage_matrix
from investment_system.validation.records import ScopedTrackStore

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)
PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {"end": "2024-12-31", "val": 100, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"},
                        {"end": "2025-12-31", "val": 130, "filed": "2026-02-01", "form": "10-K", "fy": 2025, "fp": "FY", "accn": "b"},
                    ]
                }
            },
            "EarningsPerShareDiluted": {
                "units": {"USD/shares": [{"end": "2025-12-31", "val": 2.0, "filed": "2026-02-01", "form": "10-K", "fy": 2025, "fp": "FY", "accn": "b"}]}
            },
        }
    }
}
BARS = [{"price": 40.0, "observed_at": datetime(2026, 9, 1, tzinfo=timezone.utc), "adjusted": True}]


def test_v_matrix_is_prior_not_calibrated(tmp_path):
    ids = ("nvda", "msft")
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "m.json"))
    row = run_as_of(AS_OF, {c: PAYLOAD for c in ids}, {c: BARS for c in ids}, store, ids)
    mat = v_coverage_matrix(row)
    assert mat["calibrated"] is False
    assert mat["real_data_verified"] is False
    assert mat["present"]["fundamental_value"] == 2
    assert mat["present"]["peer_relative_value"] == 2
    assert mat["present"]["theme_premium_discount"] == 0
