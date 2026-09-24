from datetime import datetime, timezone

from investment_system.providers.sec_accn_reconcile import reconcile_revenue_accn

AS_OF = datetime(2024, 12, 31, tzinfo=timezone.utc)
FACTS = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {
                            "end": "2024-01-28",
                            "val": 60,
                            "filed": "2024-02-21",
                            "form": "10-K",
                            "fy": 2024,
                            "fp": "FY",
                            "accn": "0001045810-24-000029",
                        }
                    ]
                }
            }
        }
    }
}
SUBS = {
    "filings": {
        "recent": {
            "form": ["10-K"],
            "filingDate": ["2024-02-21"],
            "accessionNumber": ["0001045810-24-000029"],
        }
    }
}


def test_accn_match_is_not_full_pit():
    out = reconcile_revenue_accn(FACTS, SUBS, AS_OF)
    assert out["match"] is True
    assert out["full_pit_pass"] is False
