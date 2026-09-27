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
from collections.abc import Mapping

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


def load_submissions_merged(store: RawDatasetStore, cik: str, as_of=None) -> tuple[dict | None, bool]:
    """(submissions with 'recent' extended by every stored older page, pages_complete).
    SEC keeps only the latest ~1000 filings in 'recent'; older ones live in filings.files pages.
    With as_of, completeness only requires the pages that pages_needed(as_of) asks for."""
    sub = load_submissions(store, cik)
    if sub is None:
        return None, False
    filings = sub.get("filings") or {}
    rec = {k: list(v) for k, v in (filings.get("recent") or {}).items() if isinstance(v, list)}
    needed = None
    if as_of is not None:
        from ..providers.sec_cover_shares import pages_needed
        needed = set(pages_needed(sub, as_of))
    complete = True
    for f in filings.get("files") or []:
        name = str(f.get("name") or "")
        aid = submission_page_id(name)
        if not store.has(aid):
            if needed is None or name in needed:
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
    lazy_companyfacts: bool = False,
) -> tuple[Mapping[str, dict], dict[str, list[dict]]]:
    """listings: company_id -> {"cik": ..., "yahoo": ...}.

    Returns (payloads, bars_by_id) in exactly the shape
    validation.historical.run_as_of already consumes — no signature change needed there.
    """
    payloads: dict[str, dict] = {}
    bars: dict[str, list[dict]] = {}
    for cid, meta in listings.items():
        cik = meta.get("cik")
        if cik and not lazy_companyfacts:
            cf = load_companyfacts(store, cik)
            if cf is not None:
                payloads[cid] = cf
        sym = meta.get("yahoo")
        if sym:
            b = load_price_bars(store, sym, chart_range)
            if b:
                bars[cid] = b
    return (_StoreCompanyFacts(store, listings) if lazy_companyfacts else payloads), bars


class _StoreCompanyFacts(Mapping):
    """Read one issuer on demand; a 500-name replay must not retain every SEC JSON tree."""
    def __init__(self, store, listings):
        self.store = store
        self.ciks = {cid: meta["cik"] for cid, meta in listings.items()
                     if meta.get("cik") and store.has(f"companyfacts:{_cik10(meta['cik'])}")}

    def __getitem__(self, company_id):
        return load_companyfacts(self.store, self.ciks[company_id])

    def __iter__(self):
        return iter(self.ciks)

    def __len__(self):
        return len(self.ciks)
