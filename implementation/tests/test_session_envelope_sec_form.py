from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.qgv.us_live import evaluate_current_session


AS_OF = datetime(2026, 9, 23, tzinfo=timezone.utc)

MIXED = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2024-01-28", "val": 60, "filed": "2024-02-21", "form": "10-K"},
                        {"end": "2024-10-27", "val": 35, "filed": "2024-11-20", "form": "10-Q"},
                        {"end": "2025-01-26", "val": 130, "filed": "2025-02-26", "form": "10-K"},
                    ]
                }
            }
        }
    }
}


def test_sec_prefers_10k_pair_for_yoy():
    raw = facts_to_raw("nvda", "0001045810", MIXED, AS_OF, synthetic=True, form_filter="10-K")
    assert raw.revenue == 130
    assert raw.revenue_prev == 60


def test_session_persists_envelope_not_history():
    live = {"prices": {"nvda": {"price": 228.87, "evidence": "LIVE_FETCH"}}}
    session = evaluate_current_session(live_prices=live)
    assert session["historical_as_of_attached"] is False
    assert session["profile_id"]
    assert session["parameter_set_hash"]
    assert len(session["parameter_set_hash"]) == 64
    assert session["track_record_id"].startswith("tr_")
    assert session["gate"] in {"PASS", "HOLD", "BLOCK"}
    assert session["real_data_verified"] is False
