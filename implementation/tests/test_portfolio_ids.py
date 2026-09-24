from datetime import datetime, timezone

from investment_system.contracts.enums import QualityState
from investment_system.qgv.identifiers import IdentifierRegistry
from investment_system.qgv.portfolio import OFFICIAL_V11_TARGETS, PortfolioEngine

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_official_weights_sum_to_one():
    assert abs(sum(OFFICIAL_V11_TARGETS.values()) - 1.0) < 1e-12


def test_tel_is_tokyo_electron_not_us_tel():
    reg = IdentifierRegistry()
    ident = reg.get("tokyo_electron")
    assert ident.ticker == "TEL"
    assert ident.legal_name.startswith("Tokyo Electron")
    assert "C-08_TEL_MARKET_ID_UNFIXED" in ident.ambiguity_flags
    assert reg.resolve_ticker("TEL") == QualityState.IDENTIFIER_AMBIGUOUS


def test_portfolio_snapshot_preserves_ambiguity():
    pf = PortfolioEngine().official_v11(AS_OF)
    tel = next(h for h in pf.holdings if h.company_id == "tokyo_electron")
    assert tel.ticker == "TEL"
    assert tel.ambiguity_flags
    assert abs(pf.weight_sum - 1.0) < 1e-12
    assert pf.portfolio_version.startswith("v1.1")
