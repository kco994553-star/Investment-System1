"""Tiingo end-of-day fallback prices (user decision 2026-09-25) for eligible issuers / priced share classes
whose Yahoo chart has no bar on/before as_of (delisted after as_of, renamed, or truncated Yahoo payloads).

Tiingo 'close' is the raw (unadjusted) traded close, i.e. exactly the as-of price the market-cap formula
needs; the converted chart is stored under the replay id yahoo_chart:<SYM>:<range> with source_kind
TIINGO_DAILY_RAW, and audit_mcap_store.load_splits returns no post-as_of split factor for that kind (the
price is not split-adjusted back in time). The raw JSON is kept as tiingo_eod:<SYM>.

Before anything is written, a calibration compares Tiingo raw closes with Yahoo closes on the last session
on/before as_of for control symbols without post-as_of splits; every available control must agree within
0.5 % (fail-closed otherwise). The API token is read from TIINGO_API_KEY and sent only as an
'Authorization: Token ...' header: it never appears in URLs, manifests, logs or commits.

Usage:
  TIINGO_API_KEY=... python tools/fetch_tiingo_prices.py --store data/raw --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from urllib.parse import quote
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_price_bars, load_submissions_merged  # noqa: E402

TIINGO_URL = "https://api.tiingo.com/tiingo/daily/{sym}/prices?startDate={start}&format=json"
TIINGO_SEARCH_URL = "https://api.tiingo.com/tiingo/utilities/search?query={q}&limit=25"
MAX_BAR_GAP_DAYS = 7  # an alternate series must have traded within a week before as_of
CONTROLS = ("AAPL", "MSFT", "JPM", "XOM", "PG", "KO")
CALIBRATION_TOLERANCE = 0.005
SOURCE_KIND = "TIINGO_DAILY_RAW"
FETCHER = "tools/fetch_tiingo_prices.py v1"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_ftp_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tiingo_symbol(sym: str) -> str:
    return sym.strip().lower().replace(".", "-")


def parse_eod(body: bytes) -> list[tuple[datetime, float]]:
    """[(bar time 21:00 UTC of the session date, raw close)] from Tiingo JSON; [] for errors/non-lists."""
    try:
        rows = json.loads(body)
    except ValueError:
        return []
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        try:
            d = datetime.fromisoformat(str(r["date"])[:10]).replace(hour=21, tzinfo=timezone.utc)
            c = float(r["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if c > 0:
            out.append((d, c))
    return sorted(out)


def norm_name(n: str) -> str:
    """Company-name key: upper case, punctuation dropped, corporate suffixes removed."""
    words = re.sub(r"[^A-Z0-9 ]", " ", str(n or "").upper().replace("&", " AND ")).split()
    return " ".join(w for w in words if w not in NAME_SUFFIXES)


NAME_SUFFIXES = {"INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "PLC", "LLC", "LP", "THE", "DE", "NEW"}


def search_candidates(body: bytes, names: set[str], exclude: str) -> list[str]:
    """Tiingo ids (ticker, then permaTicker) of search hits whose name equals one of the SEC names of the
    issuer (current or former). The ticker that already failed is not retried under the same id."""
    try:
        hits = json.loads(body)
    except ValueError:
        return []
    out = []
    for h in hits if isinstance(hits, list) else []:
        if not isinstance(h, dict) or norm_name(h.get("name")) not in names:
            continue
        if str(h.get("assetType") or "Stock") != "Stock":
            continue
        for k in ("ticker", "permaTicker"):
            v = str(h.get(k) or "").strip().lower()
            if v and v != exclude and v not in out:
                out.append(v)
    return out


def to_chart(bars: list[tuple[datetime, float]], symbol: str) -> bytes:
    return json.dumps({"chart": {"result": [{
        "meta": {"symbol": symbol, "currency": "USD", "source": "tiingo", "price_basis": "raw_close"},
        "timestamp": [int(d.timestamp()) for d, _ in bars],
        "indicators": {"quote": [{"close": [c for _, c in bars]}]}}], "error": None}}, separators=(",", ":")).encode()


def run(store_dir: Path, as_of: datetime, symbols: list[str], token: str | None, chart_range: str = "5y", sleep: float = 1.5,
        names: dict[str, list[str]] | None = None) -> dict:
    frd = _load("fetch_real_data")
    store = RawDatasetStore(store_dir)
    frd._BLOCKED_HOSTS.clear()
    log: list[dict] = []
    report = {"kind": "TIINGO_FALLBACK_RUN", "as_of": as_of.isoformat(), "n_targets": len(symbols), "targets": symbols}
    if not token:
        report.update({"status": "NO_TIINGO_API_KEY", "written": []})
        return _finish(store, frd, report, log)
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    start = (as_of - timedelta(days=5 * 365)).date().isoformat()

    def fetch(sym: str, tid: str | None = None) -> list[tuple[datetime, float]]:
        aid = f"tiingo_eod:{(tid or sym).upper()}"
        url = TIINGO_URL.format(sym=tid or tiingo_symbol(sym), start=start)
        frd._fetch_one(store, aid, url, "TIINGO_EOD_JSON", frd.YAHOO_UA, log, False, headers=headers)
        frd._throttle(log, sleep)
        if store.has(aid) and not parse_eod(store.get_bytes(aid)) and not store.list_history(aid):
            # an empty '[]' reply (seen for EQR) is retried exactly once; the empty bytes stay in history/
            frd._fetch_one(store, aid, url, "TIINGO_EOD_JSON", frd.YAHOO_UA, log, True, headers=headers)
            frd._throttle(log, sleep)
        return parse_eod(store.get_bytes(aid)) if store.has(aid) else []

    calib = []
    for c in CONTROLS:
        tb = [b for b in fetch(c) if b[0] <= as_of]
        yb = [b for b in load_price_bars(store, c, chart_range) if b["observed_at"] <= as_of]
        if not tb or not yb:
            calib.append({"symbol": c, "status": "UNAVAILABLE"})
            continue
        y, t = yb[-1], tb[-1]
        diff = abs(t[1] - y["close"]) / y["close"]
        calib.append({"symbol": c, "tiingo_date": t[0].date().isoformat(), "tiingo_close": t[1],
                      "yahoo_date": y["observed_at"].date().isoformat(), "yahoo_close": y["close"], "rel_diff": diff,
                      "status": "OK" if diff <= CALIBRATION_TOLERANCE else "MISMATCH"})
    calibrated = sum(r["status"] == "OK" for r in calib) >= 3 and not any(r["status"] == "MISMATCH" for r in calib)
    def alternate(sym: str) -> tuple[str | None, list[tuple[datetime, float]], dict]:
        """Ticker changed or reused after as_of: search Tiingo by the issuer's SEC names; accept only a UNIQUE
        name-matched series with a bar within MAX_BAR_GAP_DAYS before as_of."""
        keys = {norm_name(n) for n in (names or {}).get(sym, []) if norm_name(n)}
        if not keys:
            return None, [], {"status": "NO_SEC_NAME"}
        # Tiingo search matches plain words ('Premier, Inc.' returned []): query the normalised current SEC
        # name, then (renamed after as_of, e.g. EQR -> Vivmark) the most recent former name; the query is part
        # of the artifact id so an earlier empty reply for another query stays evidence and is not reused
        queries = list(dict.fromkeys(norm_name(n) for n in (names or {})[sym][:2] if norm_name(n)))
        cands, sids = [], []
        for q in queries:
            sid = f"tiingo_search:{sym.upper()}:{q.replace(' ', '_')}"
            sids.append(sid)
            frd._fetch_one(store, sid, TIINGO_SEARCH_URL.format(q=quote(q)), "TIINGO_SEARCH_JSON", frd.YAHOO_UA, log, False, headers=headers)
            frd._throttle(log, sleep)
            cands = search_candidates(store.get_bytes(sid), keys, tiingo_symbol(sym)) if store.has(sid) else []
            if cands:
                break
        ok = {}
        for tid in cands:
            bars = [b for b in fetch(sym, tid) if b[0] <= as_of]
            if bars and (as_of - bars[-1][0]).days <= MAX_BAR_GAP_DAYS:
                ok[tid] = bars
        closes = {round(b[-1][1], 4) for b in ok.values()}
        ev = {"search_ids": sids, "candidates": cands, "with_as_of_bar": sorted(ok)}
        if len(closes) == 1:  # ticker and permaTicker of one series agree; several distinct series are ambiguous
            tid = sorted(ok)[0]
            return tid, ok[tid], {**ev, "status": "UNIQUE"}
        return None, [], {**ev, "status": "AMBIGUOUS" if ok else "NONE"}

    results, written, alternates = {}, [], {}
    for sym in symbols:
        bars = fetch(sym)
        src = tiingo_symbol(sym)
        if not any(d <= as_of for d, _ in bars) and names:
            tid, alt_bars, ev = alternate(sym)
            alternates[sym] = ev
            if tid:
                bars, src = alt_bars, tid
        if not bars:
            results[sym] = "NO_TIINGO_DATA"
        elif not any(d <= as_of for d, _ in bars):
            results[sym] = "NO_TIINGO_BAR_ON_OR_BEFORE_AS_OF"
        elif not calibrated:
            results[sym] = "NOT_WRITTEN_CALIBRATION_FAILED"
        elif any(b["observed_at"] <= as_of for b in load_price_bars(store, sym, chart_range)):
            results[sym] = "YAHOO_AS_OF_BAR_PRESENT"
        else:
            store.put(f"yahoo_chart:{sym.upper()}:{chart_range}", to_chart(bars, sym.upper()),
                      TIINGO_URL.format(sym=src, start=start), SOURCE_KIND, "application/json", FETCHER, 200,
                      notes="Tiingo raw daily close (not split-adjusted); fallback because Yahoo had no as-of bar"
                            + ("" if src == tiingo_symbol(sym) else f"; Tiingo series '{src}' matched by SEC issuer name"))
            written.append(sym)
            results[sym] = "WRITTEN_TIINGO_FALLBACK"
    report.update({"status": "OK", "calibration": calib, "calibrated": calibrated, "tolerance": CALIBRATION_TOLERANCE,
                   "results": results, "written": written,
                   "alternates": alternates})
    return _finish(store, frd, report, log)


def _finish(store, frd, report: dict, log: list[dict]) -> dict:
    report["log"] = log
    report["egress_blocked_hosts"] = sorted(frd._BLOCKED_HOSTS)
    report["real_data_verified"] = False
    (store.root / f"tiingo_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    return report


def sec_names(store: RawDatasetStore, rows: dict, syms: set[str]) -> dict[str, list[str]]:
    """symbol -> SEC registrant names (current + former) of the listing's CIK."""
    out: dict[str, list[str]] = {}
    for m in rows.values():
        sym, c = str(m.get("yahoo") or ""), str(m.get("cik") or "")
        if sym not in syms or not c.isdigit():
            continue
        sub = load_submissions_merged(store, c.zfill(10))[0] or {}
        former = sorted((f for f in sub.get("formerNames") or [] if isinstance(f, dict) and f.get("name")),
                        key=lambda f: str(f.get("to") or ""), reverse=True)  # most recent former name first
        ns = [sub.get("name")] + [f["name"] for f in former]
        out[sym] = [n for n in ns if n]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=ROOT / "reports" / "gate_evidence" / "missing_large_cap_priority_plan_2024-12-31.json")
    ap.add_argument("--cik-candidates", type=Path, default=ROOT / "reports" / "gate_evidence" / "delisted_cik_candidates_2024-12-31.json")
    ap.add_argument("--extra-listings", type=Path, action="append", default=[])
    a = ap.parse_args()
    chain = _load("run_top500_gate_chain")
    fsp = _load("fetch_stooq_prices")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
    base = rd(a.listings) or {}
    for x in a.extra_listings:
        base.update(rd(x) or {})
    rows, _ = chain.extend_listings(store, base, rd(a.plan), chain.verify_cik_candidates(store, rd(a.cik_candidates)))
    syms = fsp.target_symbols(store, rows, d, chain)
    rep = run(Path(a.store), d, syms, os.environ.get("TIINGO_API_KEY"), names=sec_names(store, rows, set(syms)))
    print(json.dumps({k: v for k, v in rep.items() if k != "log"}, indent=2)[:6000])


if __name__ == "__main__":
    main()
