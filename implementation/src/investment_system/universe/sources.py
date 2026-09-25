"""Historical membership sources. NEW IMPLEMENTATION.

C-18 RESOLVED 2026-09-23 (explicit user decision): Official Default Universe
is US Market-Cap Top 500, PIT. official_mcap500_snapshot() below is the one
sanctioned constructor for it (built on mcap_top_n_snapshot(n=500), then
promoted to OFFICIAL — see contracts/universe.py OFFICIAL_UNIVERSE_*).

Two candidate builders remain, both still RESEARCH-status unless promoted:
  A. S&P 500 history from a dated-interval file (e.g. fja05680/sp500
     sp500_ticker_start_end.csv, header ticker,start_date,end_date; MIT).
     Kept as Benchmark/Research per user instruction — not deleted, not Official.
  B. US market-cap top-N ranked from PIT shares x PIT price (generic; any N).
No network here: callers pass text/rows they fetched elsewhere.
"""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Callable

from ..contracts.universe import (
    OFFICIAL_UNIVERSE_DECIDED_AT,
    OFFICIAL_UNIVERSE_DECIDED_BY,
    OFFICIAL_UNIVERSE_KIND,
    OFFICIAL_UNIVERSE_N,
    UniverseKind,
    UniverseMember,
    UniversePolicyStatus,
)
from .engine import UniverseEngine

SP500_INTERVALS_SOURCE = "fja05680/sp500:sp500_ticker_start_end.csv"  # Benchmark/Research only (C-18 RESOLVED)
EXPECTED_HEADER = ("ticker", "start_date", "end_date")


def parse_ticker_intervals_csv(
    text: str,
    resolve_ticker: Callable[[str], str | None] | None = None,
    end_date_inclusive: bool = True,
) -> dict:
    """Parse ticker,start_date,end_date rows into a dated roster.

    The file is ticker-keyed. Tickers get reused by different companies, so an
    unresolved ticker keeps a ``tkr:`` id instead of being guessed onto a
    company_id. end_date semantics are not documented by the source; the flag
    records the assumption (inclusive last day -> exclusive exit = end + 1 day).
    """
    reader = csv.reader(io.StringIO(text))
    header = tuple(h.strip().lower() for h in next(reader, ()))
    if header[:3] != EXPECTED_HEADER:
        raise ValueError(f"unexpected header {header!r}; expected {EXPECTED_HEADER}")
    members, unresolved, bad_rows = [], [], []
    for n, row in enumerate(reader, start=2):
        if not row or not row[0].strip():
            continue
        ticker = row[0].strip().upper()
        try:
            start = date.fromisoformat(row[1].strip()).isoformat()
            end_raw = row[2].strip() if len(row) > 2 else ""
            exit_ = None
            if end_raw:
                end = date.fromisoformat(end_raw)
                exit_ = (end + timedelta(days=1) if end_date_inclusive else end).isoformat()
        except ValueError:
            bad_rows.append(n)
            continue
        cid = resolve_ticker(ticker) if resolve_ticker else None
        if cid is None:
            unresolved.append(ticker)
            cid = f"tkr:{ticker}"
        members.append(UniverseMember(cid, ticker, entered_on=start, exited_on=exit_))
    return {
        "roster": tuple(members),
        "n_rows": len(members),
        "unresolved_tickers": sorted(set(unresolved)),
        "bad_rows": bad_rows,
        "end_date_inclusive_assumed": end_date_inclusive,
        "source": SP500_INTERVALS_SOURCE,
        "c18_candidate": "S&P 500",
        "official": False,
    }


def sp500_history_snapshot(parsed: dict, as_of: datetime, source_vintage: str):
    """Candidate A snapshot. Later-vintage reconstruction is labelled as such."""
    return UniverseEngine().snapshot(
        as_of,
        roster=parsed["roster"],
        kind=UniverseKind.SP500_HISTORY_CANDIDATE,
        policy_status=UniversePolicyStatus.RESEARCH,
        source=parsed["source"],
        source_vintage=source_vintage,
    )


def mcap_top_n_snapshot(
    candidates: list[dict],
    as_of: datetime,
    n: int = 500,
    source: str = "PIT_SHARES_X_PIT_PRICE",
):
    """Candidate B snapshot: rank by PIT market cap at as_of.

    Each candidate: company_id, ticker, shares, shares_available_at,
    price, price_observed_at (optional cik). Values not available at as_of or
    missing are excluded and reported, never imputed.
    """
    ranked, excluded = [], []
    for c in candidates:
        cid = c["company_id"]
        sh, px = c.get("shares"), c.get("price")
        sh_at, px_at = c.get("shares_available_at"), c.get("price_observed_at")
        if sh is None or px is None or sh_at is None or px_at is None:
            excluded.append({"company_id": cid, "reason": "MISSING_INPUT"})
            continue
        if sh_at > as_of or px_at > as_of:
            excluded.append({"company_id": cid, "reason": "NOT_AVAILABLE_AT_AS_OF"})
            continue
        if sh <= 0 or px <= 0:
            excluded.append({"company_id": cid, "reason": "NON_POSITIVE"})
            continue
        ranked.append((sh * px, cid, c))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    top = ranked[:n]
    roster = tuple(UniverseMember(cid, c["ticker"], cik=c.get("cik")) for _, cid, c in top)
    snap = UniverseEngine().snapshot(
        as_of,
        roster=roster,
        kind=UniverseKind.MCAP_TOP_N_CANDIDATE,
        policy_status=UniversePolicyStatus.RESEARCH,
        source=source,
    )
    # Membership is derived from as_of data itself, so it is PIT by construction
    # as far as the candidate pool is PIT. The pool's own completeness is not proven.
    snap = replace(snap, membership_basis="DERIVED_AT_AS_OF", survivorship_risk=False)
    return snap, {
        "n_requested": n,
        "n_ranked": len(ranked),
        "n_selected": len(top),
        "excluded": excluded,
        "cutoff_mcap": top[-1][0] if top else None,
        "candidate_pool_complete": False,
        "c18_candidate": "US market-cap top N",
        "official": False,
    }


def _pit_rows(payload: dict, taxonomy: str, concept: str, unit: str, as_of: datetime) -> list[dict]:
    node = ((payload.get("facts") or {}).get(taxonomy) or {}).get(concept) or {}
    rows = []
    for r in (node.get("units") or {}).get(unit) or []:
        try:
            filed = datetime.fromisoformat(str(r["filed"]) + "T00:00:00+00:00")
        except (KeyError, ValueError):
            continue
        if filed <= as_of and r.get("val") is not None:
            rows.append({**r, "_filed": filed})
    return rows


def pit_shares(payload: dict, as_of: datetime) -> dict:
    """Shares outstanding known at as_of. Cover-page dei first, then us-gaap.

    If the latest filing carries several different values for the same concept
    (typical for multi-class issuers once dimensions are dropped), the result is
    MULTI_CLASS_AMBIGUOUS and no number is returned. Classes are not summed by guess.
    """
    for taxonomy, concept in (("dei", "EntityCommonStockSharesOutstanding"), ("us-gaap", "CommonStockSharesOutstanding")):
        rows = _pit_rows(payload, taxonomy, concept, "shares", as_of)
        if not rows:
            continue
        latest = max(r["_filed"] for r in rows)
        top = [r for r in rows if r["_filed"] == latest]
        # One filing often reports the concept at several dates (e.g. period end and prior
        # year end); only different values at the SAME latest date indicate share classes.
        last_end = max(str(r.get("end") or "") for r in top)
        top = [r for r in top if str(r.get("end") or "") == last_end]
        vals = {float(r["val"]) for r in top}
        if len(vals) > 1:
            return {"status": "MULTI_CLASS_AMBIGUOUS", "shares": None, "source": f"{taxonomy}:{concept}", "available_at": latest}
        return {"status": "OK", "shares": vals.pop(), "source": f"{taxonomy}:{concept}", "available_at": latest}
    return {"status": "MISSING", "shares": None, "source": None, "available_at": None}


def mcap_candidates_from_payloads(
    meta: dict[str, dict],
    payloads: dict[str, dict],
    bars_by_id: dict[str, list],
    as_of: datetime,
) -> list[dict]:
    """Build candidate-B inputs (for mcap_top_n_snapshot) from companyfacts + price bars.

    meta: company_id -> {"ticker", "cik"}. Only data available at as_of is used.
    """
    out = []
    for cid, m in meta.items():
        sh = pit_shares(payloads.get(cid) or {}, as_of)
        bars = [b for b in (bars_by_id.get(cid) or []) if b["observed_at"] <= as_of]
        px = bars[-1] if bars else None
        out.append({
            "company_id": cid,
            "ticker": m["ticker"],
            "cik": m.get("cik"),
            "shares": sh["shares"],
            "shares_available_at": sh["available_at"],
            "shares_status": sh["status"],
            "price": None if px is None else px["price"],
            "price_observed_at": None if px is None else px["observed_at"],
        })
    return out


def official_mcap500_snapshot(candidates: list[dict], as_of: datetime, source: str = "PIT_SHARES_X_PIT_PRICE"):
    """Official Default Universe: US Market-Cap Top 500, PIT.

    C-18 RESOLVED 2026-09-23 by explicit user decision — this function is the
    ONE place in the codebase that mints an OFFICIAL universe snapshot.
    UniverseEngine.snapshot() itself refuses policy_status=OFFICIAL; this
    builds the ranking through the ordinary RESEARCH path
    (mcap_top_n_snapshot, n=500, same PIT rules — no value used unless
    available at as_of, no imputation, no current-roster-applied-backward)
    and only then promotes the result. That keeps the ranking logic identical
    to the generic/candidate-B path: nothing about the math changes because
    the output is now Official, only the label and status do.

    ``candidates`` must be a real PIT candidate pool (every US-listed filer
    with shares+price data at as_of, not a hand-picked subset) for the result
    to actually BE the Top 500 rather than the top of whatever subset was
    passed. The report's candidate_pool_complete flag is never set True here;
    the caller must be able to justify pool completeness before treating a
    given run as the true Official universe for that as_of.
    """
    snap, report = mcap_top_n_snapshot(candidates, as_of, n=OFFICIAL_UNIVERSE_N, source=source)
    official = replace(
        snap,
        universe_kind=OFFICIAL_UNIVERSE_KIND,
        policy_status=UniversePolicyStatus.OFFICIAL,
    )
    report = {
        **report,
        "official": True,
        "c18_status": "RESOLVED",
        "c18_decision": "US_MCAP_TOP500_PIT",
        "decided_at": OFFICIAL_UNIVERSE_DECIDED_AT,
        "decided_by": OFFICIAL_UNIVERSE_DECIDED_BY,
    }
    return official, report


def official_mcap500_snapshot_from_store(store, listings: dict[str, dict], as_of, chart_range: str = "5y"):
    """official_mcap500_snapshot fed from a previously-ingested RawDatasetStore.

    listings: company_id -> {"yahoo": ticker, "cik": ...} — same shape ingestion
    .replay.build_payloads_and_bars and vertical_slice.run_*_from_store already
    use, for the full PIT candidate pool (every name to be ranked, not just
    current top names — completeness is the caller's responsibility, same
    caveat as official_mcap500_snapshot). Absent companyfacts/price artifacts
    simply drop that name from the pool (mcap_candidates_from_payloads already
    reports missing/unavailable via shares_status / price_observed_at=None),
    never fabricated.
    """
    from ..ingestion.replay import build_payloads_and_bars  # local import: avoid a hard dep for callers who don't ingest

    payloads, bars = build_payloads_and_bars(store, listings, chart_range=chart_range)
    meta = {cid: {"ticker": v["yahoo"], "cik": v.get("cik")} for cid, v in listings.items()}
    candidates = mcap_candidates_from_payloads(meta, payloads, bars, as_of)
    return official_mcap500_snapshot(candidates, as_of)
