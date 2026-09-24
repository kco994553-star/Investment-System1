"""End-to-end: (stubbed) network runner -> RawDatasetStore -> vertical slice.

Proves the wiring the real ingestion run will use, without claiming real data.
"""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.universe import UniverseMember
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.universe.engine import UniverseEngine
from investment_system.validation.vertical_slice import run_vertical_slice_from_store, run_walk_forward_from_store

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def _chart(symbol, prices, start=1_700_000_000):
    ts = [start + i * 86400 for i in range(len(prices))]
    return {"chart": {"result": [{"meta": {"symbol": symbol, "currency": "USD"}, "timestamp": ts,
            "indicators": {"quote": [{"close": prices}], "adjclose": [{"adjclose": prices}]}}]}}


def _facts(rev_by_year):
    rows = [{"end": f"{y}-12-31", "val": v, "filed": f"{y + 1}-02-01", "form": "10-K", "fy": y, "fp": "FY", "accn": f"a{y}"} for y, v in rev_by_year.items()]
    eps = [{"end": f"{y}-12-31", "val": v / 100, "filed": f"{y + 1}-02-01", "form": "10-K", "fy": y, "fp": "FY", "accn": f"a{y}"} for y, v in rev_by_year.items()]
    return {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rows}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
        "NetIncomeLoss": {"units": {"USD": [{**r, "val": r["val"] * 0.1} for r in rows]}},
        "OperatingIncomeLoss": {"units": {"USD": [{**r, "val": r["val"] * 0.12} for r in rows]}},
        "StockholdersEquity": {"units": {"USD": [{**r, "val": r["val"] * 0.6} for r in rows]}},
    }}}


def test_stubbed_ingest_then_vertical_slice_then_walk_forward(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("frd", ROOT / "tools" / "fetch_real_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ciks = {"a": "1000001", "b": "1000002", "c": "1000003"}
    syms = {"a": "AAA", "b": "BBB", "c": "CCC"}
    routes = {mod.SEC_TICKERS_URL: (b"{}", 200)}
    for cid, cik in ciks.items():
        routes[mod.SEC_FACTS_URL.format(cik=cik.zfill(10))] = (json.dumps(_facts({2024: 100 + ord(cid), 2025: 120 + ord(cid)})).encode(), 200)
        routes[mod.SEC_SUBS_URL.format(cik=cik.zfill(10))] = (b'{"filings":{"recent":{"form":[],"filingDate":[],"accessionNumber":[]}}}', 200)
    for cid, sym in syms.items():
        routes[mod.YAHOO_CHART_URL.format(symbol=sym, range="5y")] = (json.dumps(_chart(sym, [10.0, 11.0, 12.0, 13.0])).encode(), 200)

    def fake(req, timeout=0):
        class R:
            def __init__(s, b, st): s.body, s.status, s.headers = b, st, {}
            def read(s): return s.body
            def __enter__(s): return s
            def __exit__(s, *a): return False
        body, status = routes[req.full_url]
        return R(body, status)

    monkeypatch.setattr(mod, "urlopen", fake)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    rep = mod.run(Path(tmp_path) / "store", list(ciks.values()), list(syms.values()), "5y", 0.0, skip_tickers=False)
    assert rep["n_failed"] == 0

    store = RawDatasetStore(Path(tmp_path) / "store")
    roster = tuple(UniverseMember(cid, sym, entered_on="2015-01-01", cik=ciks[cid]) for cid, sym in syms.items())
    t0 = datetime(2026, 3, 31, tzinfo=UTC)
    t1 = datetime(2026, 9, 30, tzinfo=UTC)
    uni = UniverseEngine().snapshot(t0, roster=roster, source_vintage="2026-09-23")
    res = run_vertical_slice_from_store(store, t0, t1, uni, chart_range="5y", store_path=Path(tmp_path) / "s.json")
    assert res["real_data_verified"] is False and not res["name_errors"]
    assert set(res["ranked"][0].keys()) >= {"Q", "G", "V", "company_id"}
    assert all(r["Q"] is not None for r in res["ranked"])  # store-fed data scored through the real engine

    wf = run_walk_forward_from_store(store, [t0, t1], lambda d: UniverseEngine().snapshot(d, roster=roster, source_vintage="2026-09-23"), chart_range="5y", store_path=Path(tmp_path) / "w.json")
    assert wf["fit_to_outcomes"] is False and len(wf["steps"]) == 1
