from datetime import datetime, timezone

from investment_system.providers.sec_vintage import resolve_vintages, select_latest

AS_OF = datetime(2024, 12, 31, tzinfo=timezone.utc)
PAYLOAD = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"start": "2023-11-01", "end": "2024-01-28", "val": 1, "filed": "2024-02-21", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "q"},
                        {"start": "2023-01-30", "end": "2024-01-28", "val": 60, "filed": "2024-02-21", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"},
                    ]
                }
            }
        }
    }
}

def test_10k_drops_sub_annual_duration():
    rows = resolve_vintages(PAYLOAD, "us-gaap", "Revenues", "USD", AS_OF, "10-K")
    assert [r.value for r in rows] == [60.0]
    assert select_latest(rows).accn == "a"
