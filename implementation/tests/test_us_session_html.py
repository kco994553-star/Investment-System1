"""Independent generated session prices and identities; no captured inputs."""
from datetime import datetime, timezone
import pytest
from investment_system.providers.us_sec import parse_us_company
from investment_system.qgv.html_sample import render_us_book_html
from investment_system.qgv.us_live import evaluate_current_session
from tests.synthetic_cleanup_inputs import session_inputs


def test_us_sec_rejects_korea():
    with pytest.raises(KeyError):
        parse_us_company("hanmi")


def test_us_sec_parses_independent_fixture():
    payload = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"end": "2024-12-31", "val": 3700, "filed": "2025-02-03", "form": "10-K"}
    ]}}}}}
    raw = parse_us_company("cleanup_sec_case", as_of=datetime(2026, 1, 5, tzinfo=timezone.utc),
                           payload=payload, listings={"cleanup_sec_case": {"cik": "SYNTHETIC_SEC"}})
    assert raw.company_id == "cleanup_sec_case"
    assert raw.revenue == 3700


def test_session_evaluate_uses_injected_synthetic_prices(monkeypatch, tmp_path):
    live, ids = session_inputs(monkeypatch, tmp_path)
    # A present zero and an absent quote must remain distinguishable.
    live["prices"][ids[1]]["price"] = 0.0
    session = evaluate_current_session(live_prices=live)
    assert session["names"] == len(ids)
    assert session["stage2"] is False
    assert session["historical_as_of_attached"] is False
    rows = {row["company_id"]: row for row in session["rows"]}
    assert rows[ids[0]]["price"] == live["prices"][ids[0]]["price"]
    assert rows[ids[0]]["price_evidence"] == "SYNTHETIC_TEST_INPUT"
    assert rows[ids[1]]["price"] == 0.0
    assert rows[ids[2]]["price"] is None
    assert all(row["synthetic_qgv"] for row in rows.values())
    html = render_us_book_html(session)
    assert "US Working Book" in html
    assert "NOT STAGE 2" in html
    assert ids[0] in html
