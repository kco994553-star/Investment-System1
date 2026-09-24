from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import facts_to_raw

AS_OF = datetime(2025, 6, 30, tzinfo=timezone.utc)

PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"EUR": [{"end": "2024-12-31", "val": 28, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "r"}]}
            },
            "NetIncomeLoss": {
                "units": {
                    "USD": [{"end": "2010-12-31", "val": 1, "filed": "2011-02-01", "form": "20-F", "fy": 2010, "fp": "FY", "accn": "old"}],
                    "EUR": [{"end": "2024-12-31", "val": 8, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "n"}],
                }
            },
            "StockholdersEquity": {
                "units": {"EUR": [{"end": "2024-12-31", "val": 40, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "e"}]}
            },
            "CashAndCashEquivalentsAtCarryingValue": {
                "units": {"EUR": [{"end": "2024-12-31", "val": 5, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "c"}]}
            },
            "OperatingIncomeLoss": {
                "units": {"EUR": [{"end": "2024-12-31", "val": 9, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "o"}]}
            },
        }
    }
}


def test_statement_fields_use_latest_end_not_stale_usd():
    raw = facts_to_raw("asml", "0000937966", PAYLOAD, AS_OF, synthetic=True)
    assert raw.revenue == 28
    assert raw.net_income == 8
    assert raw.equity == 40
    assert raw.cash == 5
    assert raw.ebit == 9
    assert raw.reporting_currency == "EUR"
