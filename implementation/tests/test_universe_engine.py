from datetime import datetime, timezone

from investment_system.contracts.universe import (
    EventKind,
    OFFICIAL_UNIVERSE_STATUS,
    UniverseKind,
    UniverseMember,
    UniversePolicyStatus,
)
from investment_system.universe.engine import UniverseEngine, members_at
from investment_system.universe.events import dirty_from_events, make_event
from investment_system.universe.recon import daily_reconciliation


AS = datetime(2024, 6, 30, tzinfo=timezone.utc)


def test_official_universe_is_resolved_to_us_mcap_top500():
    # C-18 RESOLVED 2026-09-23 (explicit user decision). See universe/sources.py:
    # official_mcap500_snapshot for the one sanctioned way to mint this.
    st = UniverseEngine().official_status()
    assert st["decision_required"] is False
    assert st["official_kind"] == "US_MCAP_TOP500_OFFICIAL"
    assert st["official_n"] == 500
    assert st["sp500_equals_mcap500"] is False
    assert st["sp500_status"] == "BENCHMARK_RESEARCH_ONLY"
    assert OFFICIAL_UNIVERSE_STATUS is UniversePolicyStatus.OFFICIAL


def test_membership_is_as_of_not_current():
    roster = (
        UniverseMember("old", "OLD", entered_on="2020-01-01", exited_on="2023-12-31"),
        UniverseMember("now", "NOW", entered_on="2024-01-01", exited_on=None),
        UniverseMember("future", "FUT", entered_on="2025-01-01", exited_on=None),
    )
    early = members_at(datetime(2022, 6, 1, tzinfo=timezone.utc), roster)
    mid = members_at(AS, roster)
    assert [m.company_id for m in early] == ["old"]
    assert [m.company_id for m in mid] == ["now"]


def test_fundamental_dirties_one_company_not_all():
    events = [
        make_event(EventKind.FUNDAMENTAL, AS, "nvda"),
        make_event(EventKind.MACRO, AS),
        make_event(EventKind.NEWS, AS, "nvda"),
        make_event(EventKind.PRICE, AS, "msft"),
    ]
    dirty = dirty_from_events(events)
    assert dirty["qgv"] == {"nvda"}
    assert dirty["technical"] == {"msft"}
    assert dirty["macro"] is True
    assert dirty["evidence"] == {"nvda"}


def test_daily_recon_does_not_recompute_unchanged():
    uni = UniverseEngine().snapshot(
        AS,
        roster=(UniverseMember("nvda", "NVDA"), UniverseMember("msft", "MSFT")),
        kind=UniverseKind.EXPLICIT,
    )
    report = daily_reconciliation(AS, uni, {})
    assert report["recompute_unchanged"] is False
    assert report["missing_updates"] == ["msft", "nvda"]
    assert report["full_pit_pass"] is False
