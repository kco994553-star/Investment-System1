from datetime import datetime, timezone

from investment_system.providers.sec_submissions import latest_annual, parse_filings

PAYLOAD = {
    "filings": {
        "recent": {
            "form": ["20-F", "6-K", "20-F"],
            "filingDate": ["2024-02-14", "2024-03-01", "2025-02-12"],
            "accessionNumber": ["20-24", "6k", "20-25"],
        }
    }
}


def test_foreign_issuer_uses_20f_not_fake_10k():
    as_of = datetime(2024, 12, 31, tzinfo=timezone.utc)
    rows = parse_filings(PAYLOAD, as_of)
    assert [r["form"] for r in rows] == ["20-F"]
    hit = latest_annual(PAYLOAD, as_of)
    assert hit["form"] == "20-F"
    assert hit["filingDate"] == "2024-02-14"
