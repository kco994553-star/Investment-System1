from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import load_facts_file
from investment_system.providers.us_sec import parse_us_company
from investment_system.qgv.html_sample import render_us_book_html
from investment_system.qgv.us_live import evaluate_current_session
from pathlib import Path

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "sec_companyfacts_mini.json"
AS_OF = datetime(2026, 9, 23, tzinfo=timezone.utc)


def test_us_sec_rejects_korea():
    try:
        parse_us_company("hanmi")
        assert False, "hanmi must not parse on US track"
    except KeyError:
        pass


def test_us_sec_parses_fixture_nvda():
    raw = parse_us_company("nvda", as_of=AS_OF, payload=load_facts_file(FIX))
    assert raw is not None
    assert raw.company_id == "nvda"
    assert raw.revenue is not None
    assert raw.stamp.synthetic is False or raw.source_kind in {"LIVE_FETCH", "SYNTHETIC"}


def test_session_evaluate_uses_injected_live_prices():
    live = {
        "prices": {
            "nvda": {"price": 228.87, "evidence": "LIVE_FETCH"},
            "msft": {"price": 498.0, "evidence": "LIVE_FETCH"},
        }
    }
    session = evaluate_current_session(live_prices=live)
    assert session["names"] == 17
    assert session["stage2"] is False
    assert session["historical_as_of_attached"] is False
    nvda = next(r for r in session["rows"] if r["company_id"] == "nvda")
    assert nvda["price"] == 228.87
    assert nvda.get("V") is None or isinstance(nvda.get("V"), (int, float))
    assert "hanmi" not in {r["company_id"] for r in session["rows"]}
    html = render_us_book_html(session)
    assert "US Working Book" in html
    assert "NOT STAGE 2" in html
    assert "nvda" in html
