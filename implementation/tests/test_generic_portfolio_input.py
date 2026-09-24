from datetime import datetime, timezone

from investment_system.contracts.portfolio_input import ROLE_FIXTURE, ROLE_GENERIC, equal_weight_input
from investment_system.qgv.portfolio import PortfolioEngine

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_generic_input_is_not_official_or_us_working():
    spec = equal_weight_input("probe", (("nvda", "NVDA"), ("msft", "MSFT"), ("asml", "ASML")))
    pf = PortfolioEngine().from_input(spec, AS_OF)
    assert pf.role == ROLE_GENERIC
    assert pf.portfolio_version == "generic-equal-weight"
    assert "v1.1" not in pf.portfolio_version
    assert "us-working" not in pf.portfolio_version
    assert abs(sum(h.target_weight for h in pf.holdings) - 1.0) < 1e-12
    assert {h.company_id for h in pf.holdings} == {"nvda", "msft", "asml"}


def test_official_and_us_working_are_reference_fixtures():
    official = PortfolioEngine().official_v11(AS_OF)
    working = PortfolioEngine().us_working(AS_OF)
    assert official.role == ROLE_FIXTURE
    assert working.role == ROLE_FIXTURE
    evaluated = PortfolioEngine().evaluate(official, {"nvda": 100.0})
    assert evaluated.role == ROLE_FIXTURE
