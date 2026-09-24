from datetime import datetime, timezone

from investment_system.qgv.g_horizon import GHorizonConfig
from investment_system.qgv.quarterly_series import monitor_from_facts

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def _q(end, val, start, form="10-Q"):
    return {
        "end": end,
        "val": val,
        "filed": end,
        "form": form,
        "fy": int(end[:4]),
        "fp": "Q1",
        "accn": end,
        "start": start,
    }


SPANS = [
    ("2022-01-01", "2022-03-31"),
    ("2022-04-01", "2022-06-30"),
    ("2022-07-01", "2022-09-30"),
    ("2023-01-01", "2023-03-31"),
    ("2023-04-01", "2023-06-30"),
    ("2023-07-01", "2023-09-30"),
    ("2024-01-01", "2024-03-31"),
    ("2024-04-01", "2024-06-30"),
    ("2024-07-01", "2024-09-30"),
    ("2025-01-01", "2025-03-31"),
    ("2025-04-01", "2025-06-30"),
    ("2025-07-01", "2025-09-30"),
    ("2026-01-01", "2026-03-31"),
    ("2026-04-01", "2026-06-30"),
]


def _payload():
    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [_q(b, 100 + i, a) for i, (a, b) in enumerate(SPANS)]
                    }
                }
            }
        }
    }


def test_3y_window_is_12_and_1q_has_no_yoy():
    payload = _payload()
    mon3 = monitor_from_facts(payload, AS_OF, GHorizonConfig("3Y"))
    mon1 = monitor_from_facts(payload, AS_OF, GHorizonConfig("1Q"))
    assert mon3["available_quarters_total"] == 14
    assert mon3["window_quarters"] == 12
    assert mon3["horizon"] == "3Y"
    assert mon1["window_quarters"] == 1
    assert mon1["revenue"]["yoy"] is None
    assert mon3["note"].startswith("RAW_EVIDENCE_ONLY")
