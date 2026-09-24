from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.enums import CoverageState, QualityState
from investment_system.contracts.models import DataStamp
from investment_system.contracts.raw import PricePoint, RawFundamentals
from investment_system.providers.memory import MemoryFundamentalsProvider, MemoryPriceProvider
from investment_system.providers.sec_companyfacts import facts_to_raw, load_facts_file, try_fetch_companyfacts
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.raw_map import map_raw

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)
PAST = datetime(2025, 3, 1, tzinfo=timezone.utc)
FUTURE = datetime(2026, 12, 1, tzinfo=timezone.utc)
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "sec_companyfacts_mini.json"


def _stamp(sid: str, when: datetime, synthetic: bool = True) -> DataStamp:
    return DataStamp(
        data_stamp_id=sid,
        source_provider="fixture",
        source_type="fundamentals",
        source_reference="test",
        published_at=when,
        available_at=when,
        observed_at=when,
        synthetic=synthetic,
    )


def _raw(**kwargs) -> RawFundamentals:
    base = dict(
        company_id="nvda",
        stamp=_stamp("r1", PAST),
        revenue=130_000,
        revenue_prev=60_000,
        ebit=80_000,
        fcf=50_000,
        net_income=70_000,
        invested_capital=90_000,
        cash=10_000,
        total_debt=8_000,
        eps=3.0,
        eps_prev=1.5,
        industry_revenue_growth=0.20,
        market_share=0.20,
        peer_median_market_share=0.10,
        wacc=0.10,
        competitive_advantage_rubric=80,
        management_quality_rubric=70,
        growth_durability_rubric=75,
        dcf_value=180.0,
        price=150.0,
        peer_median_multiple=30.0,
        own_multiple=28.0,
        hist_valuation_percentile=60.0,
        sector_context_score=55.0,
        theme_premium_score=58.0,
        reverse_dcf_implied_growth=0.12,
        source_kind="SYNTHETIC",
    )
    base.update(kwargs)
    return RawFundamentals(**base)


def test_map_raw_does_not_zero_fill_missing_rubric():
    raw = _raw(competitive_advantage_rubric=None)
    obs = map_raw(raw)
    assert obs["competitive_advantage"].quality == QualityState.MISSING_DATA
    assert obs["competitive_advantage"].score_0_100 is None
    assert obs["revenue_growth"].score_0_100 is not None


def test_pipeline_from_raw_uses_provisional_v():
    snap = AnalysisPipeline().analyze_raw(_raw())
    assert snap.synthetic is True
    assert snap.V_policy_status.value == "PROVISIONAL_INITIAL_PRIOR"
    assert snap.Q_score is not None
    assert snap.G_score is not None
    assert snap.coverage_state in {CoverageState.SYNTHETIC, CoverageState.READY, CoverageState.PARTIAL}


def test_memory_provider_pit_hides_future_raw():
    provider = MemoryFundamentalsProvider()
    provider.put(_raw(stamp=_stamp("future", FUTURE)))
    provider.put(_raw(stamp=_stamp("past", PAST), revenue=10))
    got = provider.get("nvda", AS_OF)
    assert got is not None
    assert got.stamp.data_stamp_id == "past"
    assert provider.get("nvda", datetime(2024, 1, 1, tzinfo=timezone.utc)) is None


def test_price_provider_pit():
    px = MemoryPriceProvider()
    px.put(PricePoint("nvda", _stamp("px1", PAST), 100.0))
    px.put(PricePoint("nvda", _stamp("px2", FUTURE), 999.0))
    hit = px.get("nvda", AS_OF)
    assert hit is not None
    assert hit.price == 100.0
    assert px.price_stamp("missing", AS_OF) is None


def test_sec_fixture_parser_extracts_revenue():
    payload = load_facts_file(FIX)
    raw = facts_to_raw("nvda", "0001045810", payload, AS_OF, synthetic=True)
    assert raw.revenue == 130497000000
    assert raw.source_kind == "SYNTHETIC"
    snap = AnalysisPipeline().analyze_raw(raw)
    assert snap.company_id == "nvda"
    assert snap.V_policy_status.value == "PROVISIONAL_INITIAL_PRIOR"


def test_sec_fixture_respects_as_of_before_filing():
    payload = load_facts_file(FIX)
    early = datetime(2023, 1, 1, tzinfo=timezone.utc)
    raw = facts_to_raw("nvda", "0001045810", payload, early, synthetic=True)
    assert raw.revenue is None


def test_live_sec_fetch_is_optional_and_not_stage2():
    payload = try_fetch_companyfacts("0001045810", timeout=6.0)
    if payload is None:
        assert True  # fail-closed; environment has no live SEC
        return
    raw = facts_to_raw("nvda", "0001045810", payload, AS_OF, synthetic=False)
    assert raw.source_kind == "LIVE_FETCH"
    # Live pull ≠ official Stage 2 PASS. Single-company only.
    assert raw.company_id == "nvda"
