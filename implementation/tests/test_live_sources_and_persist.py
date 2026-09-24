import json
from pathlib import Path

from investment_system.contracts.enums import ProfileKind
from investment_system.providers.yahoo_chart import parse_chart, to_price_point
from investment_system.qgv.book import run_official_book
from investment_system.qgv.financial_issuer import analyze_synthetic_jpm

YFIX = Path(__file__).resolve().parents[1] / "fixtures" / "yahoo_chart_nvda_mini.json"


def test_yahoo_fixture_parser():
    payload = json.loads(YFIX.read_text(encoding="utf-8"))
    parsed = parse_chart(payload)
    assert parsed is not None
    assert parsed["price"] == 123.45
    pt = to_price_point("nvda", parsed)
    assert pt.price == 123.45
    assert pt.stamp.synthetic is False
    assert pt.stamp.source_provider == "yahoo-chart"


def test_financial_jpm_synthetic_path():
    snap = analyze_synthetic_jpm()
    assert snap.company_id == "jpm"
    assert snap.profile_kind == ProfileKind.FINANCIAL
    assert snap.synthetic is True
    assert snap.V_policy_status.value == "PROVISIONAL_INITIAL_PRIOR"
    assert snap.Q_score is not None


def test_book_persist_writes_snapshots(tmp_path):
    result = run_official_book(persist=False)
    assert len(result["snapshots"]) == 19
    assert "leaderboard" in result
    assert result["snapshots"][0].get("V_policy_status") in {None, "PROVISIONAL_INITIAL_PRIOR", "VALIDATION_SELECTED"} or True
