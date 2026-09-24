"""Universe PIT correctness + incremental event pipeline. SYNTHETIC VERIFIED scope."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_system.contracts.universe import (
    EventKind,
    UniverseKind,
    UniverseMember,
    UniversePolicyStatus,
)
from investment_system.providers.memory import MemoryFundamentalsProvider
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.universe.engine import UniverseEngine, members_at
from investment_system.universe.events import IncrementalEngine, make_event
from investment_system.universe.recon import daily_reconciliation
from investment_system.universe.sources import (
    mcap_top_n_snapshot,
    parse_ticker_intervals_csv,
    sp500_history_snapshot,
)
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import run_as_of
from investment_system.validation.records import ScopedTrackStore
from investment_system.validation.vertical_slice import run_vertical_slice, run_walk_forward

from .synthetic_universe import bars, cid, companyfacts, raw, roster

UTC = timezone.utc
T0 = datetime(2025, 3, 31, tzinfo=UTC)


# ---------- membership PIT ----------

def test_membership_rejects_non_iso_and_overlap_but_allows_reentry():
    with pytest.raises(ValueError):
        members_at(T0, (UniverseMember("a", "A", entered_on="2024-6-1"),))
    with pytest.raises(ValueError):
        members_at(T0, (
            UniverseMember("a", "A", entered_on="2020-01-01", exited_on="2023-01-01"),
            UniverseMember("a", "A", entered_on="2022-06-01"),
        ))
    reentry = (
        UniverseMember("a", "A", entered_on="2018-01-01", exited_on="2020-01-01"),
        UniverseMember("a", "A", entered_on="2022-01-01"),
    )
    assert [m.company_id for m in members_at(datetime(2019, 1, 1, tzinfo=UTC), reentry)] == ["a"]
    assert members_at(datetime(2021, 1, 1, tzinfo=UTC), reentry) == ()
    assert [m.company_id for m in members_at(T0, reentry)] == ["a"]


def test_exit_is_exclusive_and_entry_inclusive():
    r = (UniverseMember("a", "A", entered_on="2025-03-31", exited_on="2025-04-01"),)
    assert len(members_at(T0, r)) == 1
    assert members_at(T0 + timedelta(days=1), r) == ()
    assert members_at(T0 - timedelta(days=1), r) == ()


def test_basis_labels_and_official_is_refused():
    eng = UniverseEngine()
    canary = eng.research_canary(T0)
    assert canary.membership_basis == "UNDATED_ROSTER" and canary.survivorship_risk is True
    dated = eng.snapshot(T0, roster=roster(3), source_vintage="2026-09-23")
    assert dated.membership_basis == "RECONSTRUCTED_LATER_VINTAGE" and dated.survivorship_risk is False
    with pytest.raises(ValueError):
        eng.snapshot(T0, roster=roster(3), policy_status=UniversePolicyStatus.OFFICIAL)


# ---------- C-18 candidate sources (both research-only) ----------

CSV = """ticker,start_date,end_date
AAA,2010-01-04,
BBB,2012-05-01,2024-12-20
BBB,2025-06-02,
CCC,2026-01-05,
BAD,not-a-date,
"""


def test_sp500_interval_csv_is_candidate_not_official():
    parsed = parse_ticker_intervals_csv(CSV, resolve_ticker={"AAA": "aaa"}.get)
    assert parsed["bad_rows"] == [6]
    assert "BBB" in parsed["unresolved_tickers"]
    snap = sp500_history_snapshot(parsed, T0, source_vintage="2026-09-23")
    assert snap.universe_kind is UniverseKind.SP500_HISTORY_CANDIDATE
    assert snap.policy_status is UniversePolicyStatus.RESEARCH
    assert snap.membership_basis == "RECONSTRUCTED_LATER_VINTAGE"
    # BBB left 2024-12-20 (inclusive) and re-entered after T0; CCC joined later.
    assert snap.ids() == ("aaa",)
    later = sp500_history_snapshot(parsed, datetime(2026, 2, 1, tzinfo=UTC), source_vintage="2026-09-23")
    assert set(later.ids()) == {"aaa", "tkr:BBB", "tkr:CCC"}
    with pytest.raises(ValueError):
        parse_ticker_intervals_csv("symbol,from,to\nA,2020-01-01,\n")


def test_mcap_top_n_uses_only_as_of_inputs():
    cands = [
        {"company_id": "big", "ticker": "BIG", "shares": 100, "price": 10, "shares_available_at": T0, "price_observed_at": T0},
        {"company_id": "mid", "ticker": "MID", "shares": 50, "price": 10, "shares_available_at": T0, "price_observed_at": T0},
        {"company_id": "fut", "ticker": "FUT", "shares": 999, "price": 99, "shares_available_at": T0 + timedelta(days=1), "price_observed_at": T0},
        {"company_id": "gap", "ticker": "GAP", "shares": None, "price": 10, "shares_available_at": T0, "price_observed_at": T0},
    ]
    snap, rep = mcap_top_n_snapshot(cands, T0, n=1)
    assert snap.ids() == ("big",)
    assert snap.universe_kind is UniverseKind.MCAP_TOP_N_CANDIDATE
    assert snap.policy_status is UniversePolicyStatus.RESEARCH
    assert {e["company_id"]: e["reason"] for e in rep["excluded"]} == {"fut": "NOT_AVAILABLE_AT_AS_OF", "gap": "MISSING_INPUT"}
    assert rep["official"] is False and rep["candidate_pool_complete"] is False


# ---------- incremental engine on the real calculation engine ----------

def _world(n: int):
    prov = MemoryFundamentalsProvider()
    for i in range(n):
        prov.put(raw(i, T0 - timedelta(days=30)))
    pipe = AnalysisPipeline(fundamentals=prov)
    calls: list[str] = []

    def recompute(company_id, as_of):
        calls.append(company_id)
        r = prov.get(company_id, as_of)
        return None if r is None else pipe.analyze_raw(r, as_of=as_of)

    return prov, recompute, calls


def test_single_fundamental_event_recomputes_one_of_500():
    n = 500
    prov, recompute, calls = _world(n)
    uni = UniverseEngine().snapshot(T0, roster=roster(n))
    eng = IncrementalEngine()
    full = eng.full_batch(uni, T0, recompute)
    assert full["qgv_recomputed"] == n and not full["errors"]
    before = {c: s.qgv_snapshot_id for c, s in eng.qgv.items()}
    calls.clear()
    t1 = T0 + timedelta(days=1)
    prov.put(raw(7, t1, tag="b", bump=1.3))
    events = [
        make_event(EventKind.FUNDAMENTAL, t1, cid(7)),
        make_event(EventKind.NEWS, t1, cid(8)),
        make_event(EventKind.PRICE, t1, cid(9)),
        make_event(EventKind.MACRO, t1),
        make_event(EventKind.FUNDAMENTAL, t1, cid(10), available_at=t1 + timedelta(hours=1)),
        make_event(EventKind.FUNDAMENTAL, t1, "not_a_member"),
    ]
    rep = eng.process(events, t1, uni, recompute, recompute_technical=lambda c, a: {"c": c}, refresh_macro=lambda a: {"m": 1})
    assert calls == [cid(7)]
    assert rep["qgv_recomputed"] == [cid(7)]
    assert rep["untouched_qgv"] == n - 1
    assert len(rep["deferred_not_available"]) == 1
    assert rep["ignored_not_member"] == ["not_a_member"]
    assert rep["technical_recomputed"] == [cid(9)] and rep["macro_refreshed"] is True
    assert rep["evidence_only"] == [cid(8)] and eng.evidence[cid(8)]
    after = {c: s.qgv_snapshot_id for c, s in eng.qgv.items()}
    changed = {c for c in before if before[c] != after[c]}
    assert changed == {cid(7)}  # NEWS/PRICE/MACRO/deferred left every other QGV snapshot identical
    assert "st_syn007_b" in eng.qgv[cid(7)].data_stamp_refs
    lb = eng.refresh_leaderboard(uni, t1)
    assert len(lb.rows) == n and lb.recomputed_qgv is False


def test_recompute_error_is_isolated_and_old_snapshot_kept():
    prov, recompute, _ = _world(5)
    uni = UniverseEngine().snapshot(T0, roster=roster(5))
    eng = IncrementalEngine()
    eng.full_batch(uni, T0, recompute)
    keep = eng.qgv[cid(2)].qgv_snapshot_id

    def flaky(company_id, as_of):
        if company_id == cid(2):
            raise RuntimeError("bad filing")
        return recompute(company_id, as_of)

    rep = eng.process([make_event(EventKind.FUNDAMENTAL, T0, cid(2)), make_event(EventKind.FUNDAMENTAL, T0, cid(3))], T0, uni, flaky)
    assert rep["errors"][0]["company_id"] == cid(2)
    assert rep["qgv_recomputed"] == [cid(3)]
    assert eng.qgv[cid(2)].qgv_snapshot_id == keep


def test_daily_recon_finds_missed_event_and_skips_clean():
    n = 50
    prov, recompute, calls = _world(n)
    uni = UniverseEngine().snapshot(T0, roster=roster(n))
    eng = IncrementalEngine()
    eng.full_batch(uni, T0, recompute)
    t1 = T0 + timedelta(days=1)
    prov.put(raw(4, t1, tag="late"))   # arrived but its event was lost
    del eng.qgv[cid(5)]                 # never computed
    latest = lambda c, a: (prov.get(c, a) or None) and prov.get(c, a).stamp
    rep = daily_reconciliation(t1, uni, eng.qgv, latest_stamp=latest)
    assert rep["stale_data"] == [cid(4)]
    assert rep["missing_updates"] == [cid(5)]
    assert rep["recompute_set"] == [cid(4), cid(5)]
    assert rep["clean_skipped"] == n - 2


# ---------- PIT historical path ----------

def test_run_as_of_isolates_malformed_payload(tmp_path):
    ids = ("nvda", "msft")
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "x.json"))
    good = companyfacts(1)
    px = {c: bars(1, datetime(2024, 1, 1, tzinfo=UTC), 500) for c in ids}
    row = run_as_of(T0, {"nvda": good, "msft": {"facts": "garbage"}}, px, store, ids)
    assert "msft" in row["name_errors"]
    assert row["quality"]["msft"]["raw"] is False
    assert "nvda" in row["name_records"]


def test_vertical_slice_cross_section_is_as_of_membership(tmp_path):
    n = 6
    ros = list(roster(n))
    late = UniverseMember(cid(99), "S099", entered_on="2025-09-01", cik="0009000099")
    ros.append(late)
    ros = tuple(ros)
    ids = [m.company_id for m in ros]
    payloads = {c: companyfacts(i) for i, c in enumerate(ids)}
    px = {c: bars(i, datetime(2024, 1, 1, tzinfo=UTC), 900) for i, c in enumerate(ids)}
    t_a, t_b, t_c = T0, datetime(2025, 9, 30, tzinfo=UTC), datetime(2026, 3, 31, tzinfo=UTC)
    uni_at = lambda d: UniverseEngine().snapshot(d, roster=ros, source_vintage="2026-09-23")
    res = run_vertical_slice(t_a, t_b, payloads, px, store_path=Path(tmp_path) / "s.json", universe=uni_at(t_a))
    assert cid(99) not in res["universe"]
    assert all(cid(99) not in (r["company_id"],) for r in res["ranked"])
    assert res["membership_basis"] == "RECONSTRUCTED_LATER_VINTAGE"
    assert res["official_universe"] is False and res["universe_policy"] == "RESEARCH"
    wf = run_walk_forward([t_a, t_b, t_c], payloads, px, uni_at, store_path=Path(tmp_path) / "w.json")
    assert cid(99) not in wf["steps"][0]["universe"]
    assert cid(99) in wf["steps"][1]["universe"]
    assert wf["fit_to_outcomes"] is False and wf["oos_claimed"] is False
    with pytest.raises(ValueError):
        run_vertical_slice(t_a, t_b, payloads, px, universe=uni_at(t_b))
