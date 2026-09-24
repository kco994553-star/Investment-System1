from investment_system.markets.kr import KR_DEFERRED
from investment_system.markets.us import OUT_OF_US_TRACK, US_LISTINGS, US_WORKING_TARGETS
from investment_system.qgv.portfolio import OFFICIAL_V11_TARGETS, PortfolioEngine
from investment_system.qgv.us_live import run_us_synthetic_working
from investment_system.versions import PORTFOLIO_OFFICIAL, PORTFOLIO_US_WORKING
from datetime import datetime, timezone

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_us_track_excludes_korea_and_tel():
    assert "hanmi" not in US_LISTINGS
    assert "tokyo_electron" not in US_LISTINGS
    assert OUT_OF_US_TRACK["hanmi"] == "KR_DEFERRED"
    assert "hanmi" in KR_DEFERRED
    assert set(US_LISTINGS) <= set(OFFICIAL_V11_TARGETS)
    assert abs(sum(US_WORKING_TARGETS.values()) - 1.0) < 1e-12
    assert len(US_LISTINGS) == 17


def test_official_book_still_has_nineteen_names():
    pf = PortfolioEngine().official_v11(AS_OF)
    assert pf.portfolio_version == PORTFOLIO_OFFICIAL
    assert len(pf.holdings) == 19
    assert {h.company_id for h in pf.holdings} == set(OFFICIAL_V11_TARGETS)


def test_us_working_book_is_provisional_not_official():
    pf = PortfolioEngine().us_working(AS_OF)
    assert pf.portfolio_version == PORTFOLIO_US_WORKING
    assert len(pf.holdings) == 17
    assert "hanmi" not in {h.company_id for h in pf.holdings}
    assert abs(pf.weight_sum - 1.0) < 1e-12


def test_us_synthetic_working_runner():
    result = run_us_synthetic_working(AS_OF)
    assert result["names"] == 17
    assert result["track"] == "US"
    assert "v_null" in result
    assert "hanmi" not in result["company_ids"]
