from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.qgv.pipeline import AnalysisPipeline

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)

ASML_EPS = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"EUR": [
                    {"end": "2024-12-31", "val": 28, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "r0"},
                    {"end": "2025-12-31", "val": 32, "filed": "2026-02-25", "form": "20-F", "fy": 2025, "fp": "FY", "accn": "r1"},
                ]}
            },
            "EarningsPerShareDiluted": {
                "units": {"EUR/shares": [
                    {"end": "2024-12-31", "val": 19.24, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "e0"},
                    {"end": "2025-12-31", "val": 24.71, "filed": "2026-02-25", "form": "20-F", "fy": 2025, "fp": "FY", "accn": "e1"},
                ]}
            },
        }
    }
}


def test_asml_eps_eur_per_share_and_horizon_does_not_change_g():
    raw = facts_to_raw("asml", "0000937966", ASML_EPS, AS_OF, synthetic=True)
    assert raw.eps == 24.71
    assert raw.eps_prev == 19.24
    pipe = AnalysisPipeline()
    a = pipe.analyze_raw(raw, as_of=AS_OF, available_quarters=0)
    b = pipe.analyze_raw(raw, as_of=AS_OF, available_quarters=8)
    assert a.G_score == b.G_score
    assert b.g_horizon["mutates_g_score"] is False
    assert b.g_horizon["requested"] == "3Y"
    assert b.g_horizon["fallback_used"] is True
