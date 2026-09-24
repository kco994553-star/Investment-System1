from datetime import datetime, timezone

from investment_system.providers.sec_vintage import resolve_vintages, select_latest

PAYLOAD = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "val": 100, "filed": "2024-02-01", "form": "10-K", "fy": 2023, "fp": "FY", "accn": "0001"},
                        {"end": "2023-12-31", "val": 90, "filed": "2024-06-15", "form": "10-K/A", "fy": 2023, "fp": "FY", "accn": "0002"},
                    ]
                }
            }
        }
    }
}


def test_restatement_after_as_of_is_invisible():
    early = datetime(2024, 3, 1, tzinfo=timezone.utc)
    late = datetime(2024, 7, 1, tzinfo=timezone.utc)
    a = select_latest(resolve_vintages(PAYLOAD, "us-gaap", "Revenues", "USD", early, "10-K"))
    b = select_latest(resolve_vintages(PAYLOAD, "us-gaap", "Revenues", "USD", late, None))
    assert a is not None and a.value == 100.0 and a.accn == "0001"
    assert b is not None and b.value == 90.0 and b.accn == "0002"
