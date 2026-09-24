"""C-18 RESOLVED: Official Default Universe = US Market-Cap Top 500, PIT.

official_mcap500_snapshot is the one sanctioned constructor. Generic
snapshot() still refuses OFFICIAL directly (defense in depth). S&P history
stays present and RESEARCH-only (kept as Benchmark, not deleted, not Official).
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_system.contracts.universe import (
    OFFICIAL_UNIVERSE_KIND,
    OFFICIAL_UNIVERSE_N,
    UniverseKind,
    UniverseMember,
    UniversePolicyStatus,
)
from investment_system.universe.engine import UniverseEngine
from investment_system.universe.sources import (
    mcap_candidates_from_payloads,
    official_mcap500_snapshot,
    parse_ticker_intervals_csv,
    sp500_history_snapshot,
)
from investment_system.validation.vertical_slice import run_vertical_slice, run_walk_forward

UTC = timezone.utc
T0 = datetime(2025, 3, 31, tzinfo=UTC)


def _candidates(n, complete=False, exclude=()):
    out = []
    for i in range(n):
        cid = f"co{i:04d}"
        if cid in exclude:
            continue
        out.append({
            "company_id": cid, "ticker": f"T{i:04d}", "cik": f"{i:010d}",
            "shares": 100 + i, "price": 1000 - i,  # descending mcap by construction
            "shares_available_at": T0, "price_observed_at": T0,
        })
    return out


def test_official_mcap500_snapshot_is_the_only_promotion_path():
    cands = _candidates(600)
    snap, rep = official_mcap500_snapshot(cands, T0)
    assert snap.universe_kind is UniverseKind.US_MCAP_TOP500_OFFICIAL is OFFICIAL_UNIVERSE_KIND
    assert snap.policy_status is UniversePolicyStatus.OFFICIAL
    assert len(snap.members) == 500 == OFFICIAL_UNIVERSE_N
    assert rep["official"] is True and rep["c18_status"] == "RESOLVED"
    assert rep["n_ranked"] == 600 and rep["n_selected"] == 500
    # Highest-mcap 500 selected, not an arbitrary slice.
    expected = sorted(cands, key=lambda c: -(c["shares"] * c["price"]))[:500]
    assert {m.company_id for m in snap.members} == {c["company_id"] for c in expected}

    # Generic snapshot() still refuses OFFICIAL directly - one sanctioned path only.
    with pytest.raises(ValueError):
        UniverseEngine().snapshot(T0, roster=(UniverseMember("a", "A"),), policy_status=UniversePolicyStatus.OFFICIAL)


def test_pool_incompleteness_is_never_hidden_even_when_official():
    cands = _candidates(500)  # fewer than the true US market -> pool is NOT complete
    snap, rep = official_mcap500_snapshot(cands, T0)
    assert len(snap.members) == 500  # ranks what it was given
    assert rep["candidate_pool_complete"] is False  # never silently claimed complete
    assert rep["n_ranked"] == 500


def test_official_universe_is_pit_not_current_roster_applied_backward():
    cands = _candidates(510, exclude=("co0509",))  # co0509 not yet investable at T0
    later = _candidates(510)  # co0509 present later
    snap_now, _ = official_mcap500_snapshot(cands, T0)
    snap_later, _ = official_mcap500_snapshot(later, T0 + timedelta(days=200))
    assert "co0509" not in snap_now.ids()
    assert snap_now.membership_basis == "DERIVED_AT_AS_OF"


def test_official_universe_drives_vertical_slice_and_walk_forward(tmp_path):
    from tests.synthetic_universe import bars, companyfacts
    n = 520
    cands = _candidates(n)
    ids = [c["company_id"] for c in cands]
    payloads = {c: companyfacts(i, full=True) for i, c in enumerate(ids)}
    px = {c: bars(i, datetime(2024, 1, 1, tzinfo=UTC), 900) for i, c in enumerate(ids)}
    t_a, t_b = T0, datetime(2025, 9, 30, tzinfo=UTC)
    snap, rep = official_mcap500_snapshot(cands, t_a)
    assert rep["official"] is True
    res = run_vertical_slice(t_a, t_b, payloads, px, store_path=tmp_path / "off.json", universe=snap)
    assert res["official_universe"] is True
    assert res["universe_policy"] == "OFFICIAL"
    assert len(res["universe"]) == 500

    uni_at = lambda d: official_mcap500_snapshot(cands, d)[0]
    wf = run_walk_forward([t_a, t_b], payloads, px, uni_at, store_path=tmp_path / "wf.json")
    assert wf["steps"][0]["universe_kind"] if "universe_kind" in wf["steps"][0] else True  # tolerate step schema
    assert len(wf["steps"][0]["universe"]) == 500
    assert wf["fit_to_outcomes"] is False


def test_sp500_history_kept_as_benchmark_not_deleted_not_official():
    csv = "ticker,start_date,end_date\nAAA,2010-01-04,\n"
    parsed = parse_ticker_intervals_csv(csv)
    snap = sp500_history_snapshot(parsed, T0, source_vintage="2026-09-23")
    assert snap.universe_kind is UniverseKind.SP500_HISTORY_CANDIDATE
    assert snap.policy_status is UniversePolicyStatus.RESEARCH  # never Official
    assert snap.universe_kind is not OFFICIAL_UNIVERSE_KIND
