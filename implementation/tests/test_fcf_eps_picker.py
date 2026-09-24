from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.qgv.pipeline import AnalysisPipeline

AS_OF = datetime(2025, 6, 30, tzinfo=timezone.utc)

PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": [
                    {"end": "2023-12-31", "val": 80, "filed": "2024-02-01", "form": "10-K", "fy": 2023, "fp": "FY", "accn": "r0"},
                    {"end": "2024-12-31", "val": 100, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "r1"},
                ]}
            },
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [{"end": "2024-12-31", "val": 30, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "c"}]}
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {"USD": [{"end": "2024-12-31", "val": 10, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "x"}]}
            },
            "EarningsPerShareDiluted": {
                "units": {"USD/shares": [
                    {"end": "2023-12-31", "val": 1.0, "filed": "2024-02-01", "form": "10-K", "fy": 2023, "fp": "FY", "accn": "e0"},
                    {"end": "2024-12-31", "val": 1.2, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "e1"},
                ]}
            },
            "NetIncomeLoss": {"units": {"USD": [{"end": "2024-12-31", "val": 20, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "n"}]}},
            "StockholdersEquity": {"units": {"USD": [{"end": "2024-12-31", "val": 50, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "eq"}]}},
        }
    }
}


def test_fcf_from_cfo_minus_capex_and_eps_series():
    raw = facts_to_raw("nvda", "0001045810", PAYLOAD, AS_OF, synthetic=True)
    assert raw.fcf == 20
    assert raw.eps == 1.2
    assert raw.eps_prev == 1.0
    snap = AnalysisPipeline().analyze_raw(raw, as_of=AS_OF)
    assert snap.G_score is not None
    assert snap.coverage_state.value in {"PARTIAL", "SYNTHETIC", "READY"}
