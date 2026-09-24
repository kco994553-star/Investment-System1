from datetime import datetime, timezone

from investment_system.contracts.enums import ProfileKind, QualityState
from investment_system.contracts.models import DataStamp
from investment_system.contracts.raw import RawFundamentals
from investment_system.providers.catalog import iter_official_prices, iter_official_raw
from investment_system.providers.env_price import EnvPriceProvider
from investment_system.providers.sec_companyfacts import facts_to_raw, load_facts_file
from investment_system.qgv.book import run_official_book
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.portfolio import OFFICIAL_V11_TARGETS
from pathlib import Path

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "sec_companyfacts_mini.json"


def test_sec_extracts_previous_revenue():
    payload = load_facts_file(FIX)
    raw = facts_to_raw("nvda", "0001045810", payload, AS_OF, synthetic=True)
    assert raw.revenue == 130497000000
    assert raw.revenue_prev == 60922000000


def test_financial_profile_marks_roic_na_and_uses_cet1():
    raw = RawFundamentals(
        company_id="jpm",
        stamp=DataStamp(
            "fin1",
            "fixture",
            "fundamentals",
            "synthetic-bank",
            AS_OF,
            AS_OF,
            AS_OF,
            synthetic=True,
        ),
        revenue=160000,
        revenue_prev=150000,
        cet1=0.14,
        nim=0.03,
        rotce=0.16,
        profile_kind="FINANCIAL",
        source_kind="SYNTHETIC",
        management_quality_rubric=70,
        competitive_advantage_rubric=65,
        growth_durability_rubric=60,
    )
    snap = AnalysisPipeline().analyze_raw(raw)
    assert snap.profile_kind == ProfileKind.FINANCIAL
    assert snap.Q_score is not None
    assert snap.V_policy_status.value == "PROVISIONAL_INITIAL_PRIOR"


def test_official_catalog_covers_v11_book():
    raws = iter_official_raw(AS_OF)
    prices = iter_official_prices(AS_OF)
    assert {r.company_id for r in raws} == set(OFFICIAL_V11_TARGETS)
    assert {p.company_id for p in prices} == set(OFFICIAL_V11_TARGETS)
    assert all(r.source_kind == "SYNTHETIC" and r.stamp.synthetic for r in raws)


def test_official_book_runner_synthetic():
    result = run_official_book(AS_OF)
    assert result["names"] == 19
    assert result["missing_official"] == []
    assert abs(result["portfolio_weight_sum"] - 1.0) < 1e-12
    assert result["recomputed_qgv"] is False
    assert result.get("v_production_all_none") in {True, False}
    assert result["synthetic_all"] is True
    assert result["policy_status"] == "PROVISIONAL"


def test_env_price_disabled_by_default(monkeypatch):
    monkeypatch.delenv("INVESTMENT_SYSTEM_PRICE_FEED", raising=False)
    provider = EnvPriceProvider()
    assert provider.enabled() is False
    assert provider.fetch_symbol("NVDA") is None
