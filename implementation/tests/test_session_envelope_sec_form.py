"""Independent SEC-form and session-envelope test inputs (GSQ-010)."""
from datetime import datetime, timezone
import json
from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.qgv.us_live import evaluate_current_session
from tests.synthetic_cleanup_inputs import session_inputs

AS_OF = datetime(2026, 1, 5, tzinfo=timezone.utc)
MIXED = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
    {"end": "2024-01-01", "val": 2400, "filed": "2024-02-01", "form": "10-K"},
    {"end": "2024-10-01", "val": 900, "filed": "2024-11-01", "form": "10-Q"},
    {"end": "2025-01-01", "val": 4800, "filed": "2025-02-01", "form": "10-K"},
]}}}}}


def test_sec_prefers_10k_pair_for_yoy():
    raw = facts_to_raw("cleanup_sec_case", "SYNTHETIC_SEC", MIXED, AS_OF, synthetic=True, form_filter="10-K")
    assert raw.revenue == 4800
    assert raw.revenue_prev == 2400
    assert raw.stamp.synthetic is True


def test_session_persists_envelope_not_history(monkeypatch, tmp_path):
    live, ids = session_inputs(monkeypatch, tmp_path)
    session = evaluate_current_session(live_prices=live)
    assert session["historical_as_of_attached"] is False
    assert session["profile_id"]
    assert len(session["parameter_set_hash"]) == 64
    assert session["track_record_id"].startswith("tr_")
    assert session["gate"] in {"PASS", "HOLD", "BLOCK"}
    assert session["real_data_verified"] is False
    persisted = json.loads((tmp_path / "us_session_track_record.json").read_text())
    assert persisted["historical_as_of_attached"] is False
    assert persisted["envelope"]["profile_id"] == session["profile_id"]
    assert set(persisted["envelope"]["prediction"]["Q_by_id"]) == set(ids)
