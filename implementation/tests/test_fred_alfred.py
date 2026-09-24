from datetime import datetime, timezone

from investment_system.providers.fred_alfred import collect_indicators_alfred, parse_observations
from investment_system.validation.historical import live_macro

AS_OF = datetime(2025, 6, 30, tzinfo=timezone.utc)

PAYLOAD = {
    "observations": [
        {"date": "2024-06-01", "value": "100"},
        {"date": "2025-06-01", "value": "103"},
    ]
}


def test_alfred_parse_and_prior_as_of():
    rows = parse_observations(PAYLOAD, "INDPRO")
    assert rows[-1]["value"] == 103


def test_alfred_collect_from_fixture_not_verified():
    pack = collect_indicators_alfred(
        AS_OF,
        {
            "INDPRO": PAYLOAD,
            "CPIAUCSL": PAYLOAD,
            "DGS10": {"observations": [{"date": "2025-06-27", "value": "4.25"}]},
            "WALCL": {"observations": [{"date": "2025-06-25", "value": "6700000"}]},
            "BAMLH0A0HYM2": {"observations": [{"date": "2025-06-27", "value": "3.1"}]},
        },
    )
    assert pack["vintage"] == "ALFRED_AS_OF"
    assert pack["real_data_verified"] is False
    assert "growth" in pack["values"]
    snap = live_macro(AS_OF, None, prefer_alfred=False)
    assert snap.environment["real_data_verified"] is False
