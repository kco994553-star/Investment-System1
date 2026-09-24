from datetime import datetime, timezone

from investment_system.providers.sec_submissions import latest_indexed, parse_filings

PAYLOAD = {
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q", "8-K", "10-K"],
            "filingDate": ["2024-02-21", "2024-05-29", "2024-06-01", "2025-02-26"],
            "accessionNumber": ["0001-24", "0002-24", "0003-24", "0004-25"],
        }
    }
}


def test_submissions_drop_future_and_non_periodic():
    as_of = datetime(2024, 12, 31, tzinfo=timezone.utc)
    rows = parse_filings(PAYLOAD, as_of)
    assert [r["filingDate"] for r in rows] == ["2024-02-21", "2024-05-29"]
    hit = latest_indexed(PAYLOAD, as_of, "10-K")
    assert hit["filingDate"] == "2024-02-21"
    later = latest_indexed(PAYLOAD, datetime(2025, 6, 30, tzinfo=timezone.utc), "10-K")
    assert later["filingDate"] == "2025-02-26"
