from datetime import datetime, timezone

from investment_system.providers.fred_alfred import collect_indicators_alfred, parse_observations
from investment_system.validation.historical import live_macro

AS_OF = datetime(2024, 12, 31, tzinfo=timezone.utc)

PAYLOAD = {
    "observations": [
        {"date": "2024-11-01", "value": "100", "realtime_end": "2024-12-01"},
        {"date": "2024-12-01", "value": "102", "realtime_end": "2024-12-20"},
        {"date": "2025-01-15", "value": "999", "realtime_end": "2025-01-16"},
        {"date": "2024-10-01", "value": "90", "realtime_end": "2025-02-01"},
    ]
}


def test_alfred_drops_future_available_at_and_future_obs():
    rows = parse_observations(PAYLOAD, "INDPRO")
    kept = [r for r in rows if r["date"] <= AS_OF and r["available_at"] <= AS_OF]
    assert all(r["value"] != 999 for r in kept)
    assert all(r["value"] != 90 for r in kept)
    assert [r["value"] for r in kept] == [100.0, 102.0]


def test_live_macro_uses_alfred_fixture_not_csv_current():
    fixtures = {
        "INDPRO": PAYLOAD,
        "CPIAUCSL": PAYLOAD,
        "DGS10": {"observations": [{"date": "2024-12-30", "value": "4.50", "realtime_end": "2024-12-30"}]},
        "WALCL": {"observations": [{"date": "2024-12-25", "value": "6600000", "realtime_end": "2024-12-26"}]},
        "BAMLH0A0HYM2": {"observations": [{"date": "2024-12-30", "value": "3.00", "realtime_end": "2024-12-30"}]},
    }
    pack = collect_indicators_alfred(AS_OF, fixtures)
    assert pack["vintage"] == "ALFRED_AS_OF"
    snap = live_macro(AS_OF, fixtures, prefer_alfred=True)
    assert snap.environment.get("vintage") == "ALFRED_AS_OF"
    assert snap.environment.get("fallback_reason") in {None, "None"}
    assert snap.regime != "UNAVAILABLE"
