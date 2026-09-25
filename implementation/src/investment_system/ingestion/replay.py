"""Offline replay: the Analysis Engine reads previously-fetched raw data with
zero network access. NEW IMPLEMENTATION. No urllib import in this module.

Artifact id convention the network runner must follow so replay finds things:
  companyfacts:<CIK10>          raw SEC companyfacts JSON bytes
  submissions:<CIK10>           raw SEC submissions JSON bytes
  yahoo_chart:<SYMBOL>:<range>  raw Yahoo chart JSON bytes
  sec_tickers                   raw company_tickers.json bytes
  sp500_intervals               raw ticker,start_date,end_date CSV bytes

Missing artifacts return None / [] — the same MISSING behaviour run_as_of /
parse_us_company already have for absent data. Nothing here fabricates a value.
"""

from __future__ import annotations

import json

from ..providers.yahoo_chart import parse_bars
from .raw_store import RawDatasetStore


def _cik10(cik: str) -> str:
    return str(int(cik)).zfill(10)


def load_companyfacts(store: RawDatasetStore, cik: str) -> dict | None:
    aid = f"companyfacts:{_cik10(cik)}"
    return json.loads(store.get_bytes(aid)) if store.has(aid) else None


def load_submissions(store: RawDatasetStore, cik: str) -> dict | None:
    aid = f"submissions:{_cik10(cik)}"
    return json.loads(store.get_bytes(aid)) if store.has(aid) else None


def submission_page_id(name: str) -> str:
    return f"submissions_page:{name}"


def load_submissions_merged(store: RawDatasetStore, cik: str) -> tuple[dict | None, bool]:
    """(submissions with 'recent' extended by every stored older page, pages_complete).
    SEC keeps only the latest ~1000 filings in 'recent'; older ones live in filings.files pages."""
    sub = load_submissions(store, cik)
    if sub is None:
        return None, False
    filings = sub.get("filings") or {}
    rec = {k: list(v) for k, v in (filings.get("recent") or {}).items() if isinstance(v, list)}
    complete = True
    for f in filings.get("files") or []:
        aid = submission_page_id(str(f.get("name") or ""))
        if not store.has(aid):
            complete = False
            continue
        page = json.loads(store.get_bytes(aid))
        for k in list(rec):
            rec[k].extend(page.get(k) or [None] * len(page.get("form") or []))
    return {**sub, "filings": {**filings, "recent": rec}}, complete


def load_price_bars(store: RawDatasetStore, symbol: str, chart_range: str = "5d") -> list[dict]:
    aid = f"yahoo_chart:{symbol.upper()}:{chart_range}"
    if not store.has(aid):
        return []
    return parse_bars(json.loads(store.get_bytes(aid)))  # reuse the existing parser; no new PIT logic


def build_payloads_and_bars(
    store: RawDatasetStore,
    listings: dict[str, dict],
    chart_range: str = "5d",
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """listings: company_id -> {"cik": ..., "yahoo": ...}.

    Returns (payloads, bars_by_id) in exactly the shape
    validation.historical.run_as_of already consumes — no signature change needed there.
    """
    payloads: dict[str, dict] = {}
    bars: dict[str, list[dict]] = {}
    for cid, meta in listings.items():
        cik = meta.get("cik")
        if cik:
            cf = load_companyfacts(store, cik)
            if cf is not None:
                payloads[cid] = cf
        sym = meta.get("yahoo")
        if sym:
            b = load_price_bars(store, sym, chart_range)
            if b:
                bars[cid] = b
    return payloads, bars
