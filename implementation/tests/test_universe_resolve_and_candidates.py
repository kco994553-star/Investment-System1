"""Dated CIK resolution + candidate-B pool + symmetric A/B vertical slices. SYNTHETIC."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_system.contracts.universe import UniverseKind, UniverseMember
from investment_system.universe.resolve import current_ticker_map, resolve_roster
from investment_system.universe.sources import (
    mcap_candidates_from_payloads,
    mcap_top_n_snapshot,
    parse_ticker_intervals_csv,
    pit_shares,
    sp500_history_snapshot,
)
from investment_system.validation.vertical_slice import run_walk_forward

from .synthetic_universe import bars, companyfacts

UTC = timezone.utc
T0 = datetime(2025, 3, 31, tzinfo=UTC)

TICKERS = {
    "0": {"cik_str": 111, "ticker": "AAA", "title": "Alpha"},
    "1": {"cik_str": 222, "ticker": "REUS", "title": "Today's REUS holder"},
    "2": {"cik_str": 333, "ticker": "OLD", "title": "Old Co"},
    "3": {"cik_str": 444, "ticker": "DUP", "title": "Dup one"},
    "4": {"cik_str": 555, "ticker": "DUP", "title": "Dup two"},
}


def _subs(days):
    return {"filings": {"recent": {"form": ["10-K"] * len(days), "filingDate": list(days), "accessionNumber": [f"x{i}" for i in range(len(days))]}}}


def test_current_map_is_not_applied_to_closed_interval_without_evidence():
    assert "DUP" not in current_ticker_map(TICKERS)  # ambiguous in the map itself
    roster = (
        UniverseMember("tkr:AAA", "AAA", entered_on="2010-01-01"),                          # open -> CURRENT_OPEN
        UniverseMember("tkr:REUS", "REUS", entered_on="2001-01-01", exited_on="2005-01-01"),  # closed, no filings by 222 then
        UniverseMember("tkr:OLD", "OLD", entered_on="2012-01-01", exited_on="2019-06-01"),    # closed, 333 filed inside
        UniverseMember("tkr:GONE", "GONE", entered_on="2000-01-01", exited_on="2008-01-01"),  # not in map
        UniverseMember("tkr:ALS", "ALS", entered_on="2003-01-01", exited_on="2009-01-01"),    # dated alias
    )
    subs = {"0000000222": _subs(["2020-02-01"]), "0000000333": _subs(["2015-02-01", "2016-02-01"])}
    res = resolve_roster(
        roster, TICKERS, "2026-09-23",
        aliases=({"ticker": "ALS", "from": "2000-01-01", "to": "2010-01-01", "cik": 999},),
        submissions_for=subs.get,
    )
    ids = {m.ticker: m.company_id for m in res["roster"]}
    assert ids["AAA"] == "cik:0000000111"
    assert ids["REUS"] == "tkr:REUS"        # reuse risk: current holder never filed in 2001-2005
    assert ids["OLD"] == "cik:0000000333"
    assert ids["GONE"] == "tkr:GONE"
    assert ids["ALS"] == "cik:0000000999"
    assert res["methods"] == {"ALIAS": 1, "CURRENT_OPEN": 1, "VERIFIED_FILINGS": 1, "UNRESOLVED": 2}
    # Without a submissions source, closed intervals stay unresolved (fail closed).
    res2 = resolve_roster(roster[2:3], TICKERS, "2026-09-23")
    assert res2["roster"][0].company_id == "tkr:OLD"


def _with_shares(payload, rows):
    p = {"facts": dict(payload["facts"])}
    p["facts"]["dei"] = {"EntityCommonStockSharesOutstanding": {"units": {"shares": rows}}}
    return p


def test_pit_shares_as_of_and_multiclass_not_summed():
    base = companyfacts(1)
    p = _with_shares(base, [
        {"end": "2024-10-01", "val": 100, "filed": "2024-11-01", "form": "10-Q"},
        {"end": "2025-04-01", "val": 120, "filed": "2025-05-01", "form": "10-Q"},
    ])
    s = pit_shares(p, T0)
    assert s["status"] == "OK" and s["shares"] == 100 and s["source"].startswith("dei:")
    multi = _with_shares(base, [
        {"end": "2024-10-01", "val": 100, "filed": "2024-11-01", "form": "10-Q", "accn": "q"},
        {"end": "2024-10-01", "val": 40, "filed": "2024-11-01", "form": "10-Q", "accn": "q"},
    ])
    assert pit_shares(multi, T0)["status"] == "MULTI_CLASS_AMBIGUOUS"
    assert pit_shares(base, T0)["status"] == "MISSING"


def test_both_c18_candidates_run_through_the_same_slice_engine(tmp_path):
    n = 8
    meta = {f"cik:{9000000 + i:010d}": {"ticker": f"S{i}", "cik": f"{9000000 + i:010d}"} for i in range(n)}
    ids = list(meta)
    payloads = {c: _with_shares(companyfacts(i, full=True), [{"end": "2024-12-31", "val": 1000 * (i + 1), "filed": "2025-01-20", "form": "10-K"}]) for i, c in enumerate(ids)}
    px = {c: bars(i, datetime(2024, 1, 1, tzinfo=UTC), 900) for i, c in enumerate(ids)}
    dates = [T0, datetime(2025, 9, 30, tzinfo=UTC), datetime(2026, 3, 31, tzinfo=UTC)]

    # Candidate A: interval file -> dated resolver -> snapshot.
    csv = "ticker,start_date,end_date\n" + "".join(
        f"S{i},{'2025-06-01' if i == 7 else '2015-01-01'},\n" for i in range(n)
    )
    tick = {str(i): {"cik_str": 9000000 + i, "ticker": f"S{i}", "title": f"s{i}"} for i in range(n)}
    parsed = parse_ticker_intervals_csv(csv)
    resolved = resolve_roster(parsed["roster"], tick, "2026-09-23")
    parsed = {**parsed, "roster": resolved["roster"]}
    a = run_walk_forward(dates, payloads, px, lambda d: sp500_history_snapshot(parsed, d, "2026-09-23"), store_path=Path(tmp_path) / "a.json")
    assert "cik:0009000007" not in a["steps"][0]["universe"]
    assert "cik:0009000007" in a["steps"][1]["universe"]

    # Candidate B: PIT shares x PIT price -> top-N snapshot.
    def uni_b(d):
        snap, rep = mcap_top_n_snapshot(mcap_candidates_from_payloads(meta, payloads, px, d), d, n=5)
        assert rep["official"] is False
        return snap

    b = run_walk_forward(dates, payloads, px, uni_b, store_path=Path(tmp_path) / "b.json")
    assert len(b["steps"][0]["universe"]) == 5
    for res in (a, b):
        assert res["fit_to_outcomes"] is False and res["real_data_verified"] is False
        assert all(s["n_linked"] >= 1 for s in res["steps"])
    assert uni_b(T0).universe_kind is UniverseKind.MCAP_TOP_N_CANDIDATE
