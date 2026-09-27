"""C-39 shared Global/Korea identity and PIT context regressions."""

from dataclasses import fields
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from investment_system.contracts.global_universe import (
    AnalysisUniverse,
    EligibilityRecord,
    FXSnapshot,
    IssuerIdentity,
    ListingIdentity,
    Region,
    SecurityIdentity,
    UniverseContext,
)
from investment_system.contracts.universe import UniversePolicyStatus


AS_OF = datetime(2024, 6, 30, 21, tzinfo=timezone.utc)


def test_identity_is_issuer_then_security_then_dated_listing():
    issuer = IssuerIdentity("issuer_apple", "Apple Inc.", "US", (("CIK", "0000320193"),))
    security = SecurityIdentity("security_aapl_common", issuer.issuer_id, "COMMON_STOCK",
                                identifiers=(("ISIN", "US0378331005"),))
    listing = ListingIdentity("listing_aapl_xnas", security.security_id, "AAPL", "XNAS", "USD",
                              date(1980, 12, 12))
    assert listing.active_on(date(2024, 6, 30))
    assert "ticker" not in {f.name for f in fields(IssuerIdentity)}
    assert "ticker" not in {f.name for f in fields(SecurityIdentity)}
    assert listing.listing_id != listing.ticker


def test_listing_history_is_half_open_and_rejects_invalid_range():
    old = ListingIdentity("wolf_old", "security_wolf_old", "WOLF", "XNYS", "USD",
                          date(2021, 10, 4), date(2025, 9, 29))
    assert old.active_on(date(2025, 9, 28)) and not old.active_on(date(2025, 9, 29))
    with pytest.raises(ValueError):
        ListingIdentity("bad", "security", "BAD", "XNYS", "USD", date(2025, 1, 1), date(2025, 1, 1))


def test_analysis_network_and_news_contexts_are_independent():
    analysis = AnalysisUniverse("us_top500_2024-06-30", Region.US, UniversePolicyStatus.OFFICIAL,
                                "PIT_SHARES_X_PIT_PRICE")
    context = UniverseContext(analysis, Region.GLOBAL, Region.KOREA, AS_OF, AS_OF - timedelta(minutes=1))
    assert context.analysis_universe.region is Region.US
    assert context.network_region is Region.GLOBAL
    assert context.news_region is Region.KOREA
    with pytest.raises(ValueError):
        AnalysisUniverse("kr_top500", Region.KOREA, UniversePolicyStatus.OFFICIAL, "PIT_MCAP")


def test_fx_snapshot_is_decimal_provenanced_and_pit_fail_closed():
    fx = FXSnapshot("fx_usdkrw", "USD", "KRW", Decimal("1384.25"), AS_OF,
                    AS_OF - timedelta(minutes=5), "provider", "raw:fx:1")
    assert fx.convert_base_to_quote(Decimal("2")) == Decimal("2768.50")
    with pytest.raises(TypeError):
        fx.convert_base_to_quote(2.0)
    with pytest.raises(ValueError):
        FXSnapshot("future", "USD", "KRW", Decimal("1384.25"), AS_OF,
                   AS_OF + timedelta(seconds=1), "provider", "raw:fx:2")
    with pytest.raises(ValueError):
        FXSnapshot("float", "USD", "KRW", 1384.25, AS_OF, AS_OF, "provider", "raw:fx:3")


def test_eligibility_requires_pit_evidence_and_reason_when_excluded():
    ok = EligibilityRecord("elig_1", "listing_aapl_xnas", "us_top500_2024-06-30", True,
                           AS_OF, AS_OF, ("raw:nasdaq:1",))
    assert ok.eligible is True
    with pytest.raises(ValueError):
        EligibilityRecord("elig_future", "listing", "universe", True, AS_OF,
                          AS_OF + timedelta(seconds=1), ("raw:future",))
    with pytest.raises(ValueError):
        EligibilityRecord("elig_no_evidence", "listing", "universe", True, AS_OF, AS_OF, ())
    with pytest.raises(ValueError):
        EligibilityRecord("elig_no_reason", "listing", "universe", False, AS_OF, AS_OF, ("raw:1",))


def test_identifier_schemes_are_unique_and_identity_fields_are_required():
    with pytest.raises(ValueError):
        IssuerIdentity("issuer", "Name", "US", (("CIK", "1"), ("cik", "2")))
    with pytest.raises(ValueError):
        SecurityIdentity("", "issuer", "COMMON_STOCK")
