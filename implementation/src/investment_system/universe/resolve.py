"""Dated ticker -> CIK resolution for historical membership rows. NEW IMPLEMENTATION.

SEC company_tickers.json ({"0": {"cik_str", "ticker", "title"}}) is a CURRENT map.
Applying it to a closed historical interval is the current-applied-backward error
(tickers get reused). So a row resolves only with evidence, in this order:

  ALIAS             explicit dated alias (ticker, from, to, cik) covering the interval
  CURRENT_OPEN      interval still open at the map vintage and ticker is in the map
  VERIFIED_FILINGS  ticker in the map, interval closed, and that CIK filed a periodic
                    report (10-K/10-Q/20-F/40-F) inside the interval (submissions index)
  UNRESOLVED        anything else. Never guessed.

Resolved company_id = "cik:<10 digits>". Unresolved keeps "tkr:<TICKER>".
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from typing import Callable

from ..contracts.universe import UniverseMember
from ..providers.sec_submissions import parse_filings


def cik10(value) -> str:
    return str(int(value)).zfill(10)


def company_id_for(cik: str) -> str:
    return f"cik:{cik10(cik)}"


def current_ticker_map(company_tickers: dict) -> dict[str, str]:
    """Ticker -> cik10. A ticker listed under two CIKs is dropped (ambiguous)."""
    seen: dict[str, set[str]] = {}
    for row in company_tickers.values():
        t = str(row.get("ticker") or "").upper().strip()
        if t and row.get("cik_str") is not None:
            seen.setdefault(t, set()).add(cik10(row["cik_str"]))
    return {t: next(iter(c)) for t, c in seen.items() if len(c) == 1}


def filed_within(submissions: dict, start: str, end_exclusive: str | None) -> bool:
    lo = datetime.fromisoformat(start + "T00:00:00+00:00")
    hi = datetime.fromisoformat(end_exclusive + "T00:00:00+00:00") if end_exclusive else datetime.now(timezone.utc)
    return any(lo <= r["filed"] < hi for r in parse_filings(submissions, hi))


def resolve_roster(
    roster: tuple[UniverseMember, ...],
    company_tickers: dict,
    map_vintage: str,
    aliases: tuple[dict, ...] = (),
    submissions_for: Callable[[str], dict | None] | None = None,
) -> dict:
    tmap = current_ticker_map(company_tickers)
    vintage = date.fromisoformat(map_vintage).isoformat()
    out, methods = [], {"ALIAS": 0, "CURRENT_OPEN": 0, "VERIFIED_FILINGS": 0, "UNRESOLVED": 0}
    unresolved = []
    for m in roster:
        start, end = m.entered_on or "0000-01-01", m.exited_on
        cik, how = None, "UNRESOLVED"
        for a in aliases:
            if a["ticker"].upper() == m.ticker.upper() and a["from"] <= start and (a.get("to") is None or (end is not None and end <= a["to"])):
                cik, how = cik10(a["cik"]), "ALIAS"
                break
        if cik is None and m.ticker.upper() in tmap:
            cand = tmap[m.ticker.upper()]
            if end is None or end > vintage:
                cik, how = cand, "CURRENT_OPEN"
            elif submissions_for is not None:
                subs = submissions_for(cand)
                if subs and filed_within(subs, start, end):
                    cik, how = cand, "VERIFIED_FILINGS"
        methods[how] += 1
        if cik is None:
            unresolved.append({"ticker": m.ticker, "entered_on": m.entered_on, "exited_on": m.exited_on})
            out.append(m)
        else:
            out.append(replace(m, company_id=company_id_for(cik), cik=cik))
    return {
        "roster": tuple(out),
        "methods": methods,
        "unresolved": unresolved,
        "map_vintage": vintage,
        "note": "current ticker map is not applied to closed intervals without filing evidence",
    }
