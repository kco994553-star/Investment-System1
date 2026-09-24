from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.quarterly_series import monitor_from_facts, quarterly_points_from_facts

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def _q(end, val, filed, form="10-Q", fp="Q1", start=None):
    row = {"end": end, "val": val, "filed": filed, "form": form, "fy": int(end[:4]), "fp": fp, "accn": end}
    if start:
        row["start"] = start
    return row


PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        _q("2025-03-31", 100, "2025-05-01", "10-Q", "Q1", "2025-01-01"),
                        _q("2025-06-30", 110, "2025-08-01", "10-Q", "Q2", "2025-04-01"),
                        _q("2025-09-30", 120, "2025-11-01", "10-Q", "Q3", "2025-07-01"),
                        _q("2025-12-31", 130, "2026-02-01", "10-K", "FY", "2025-01-01"),
                        _q("2026-03-31", 120, "2026-05-01", "10-Q", "Q1", "2026-01-01"),
                        _q("2026-06-30", 143, "2026-08-01", "10-Q", "Q2", "2026-04-01"),
                    ]
                }
            }
        }
    }
}


def test_10q_points_exclude_10k_and_feed_monitor():
    pts = quarterly_points_from_facts(PAYLOAD, AS_OF)
    assert [p.period_end.isoformat() for p in pts] == [
        "2025-03-31",
        "2025-06-30",
        "2025-09-30",
        "2026-03-31",
        "2026-06-30",
    ]
    mon = monitor_from_facts(PAYLOAD, AS_OF)
    assert mon["status"] == "READY"
    assert mon["quarter_count"] == 5
    assert mon["revenue"]["qoq"] is not None
    assert mon["revenue"]["yoy"] is not None
    assert "does not mutate Frozen G score" in mon["note"]


def test_no_10q_is_missing_not_fabricated():
    annual = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [_q("2025-12-31", 200, "2026-02-01", "10-K", "FY", "2025-01-01")]}
                }
            }
        }
    }
    assert monitor_from_facts(annual, AS_OF)["status"] == "MISSING"
    raw = facts_to_raw("nvda", "0001045810", annual, AS_OF, synthetic=True)
    a = AnalysisPipeline().analyze_raw(raw, as_of=AS_OF, available_quarters=0)
    b = AnalysisPipeline().analyze_raw(raw, as_of=AS_OF, available_quarters=5)
    assert a.G_score == b.G_score
