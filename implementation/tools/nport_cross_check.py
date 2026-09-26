"""INVESTIGATION ONLY — does a fund's N-PORT holding value reproduce the as-of market close? (WRK 2024-06-30)

For an issuer with no permitted market close (Yahoo 404, Tiingo no bar, Stooq bot challenge not bypassed), the only
filed per-share values are fund N-PORT holdings (report date = as_of, filed ~60 days later). Before any policy
decision this tool measures, per N-PORT filing:
  (1) CALIBRATION: for every Official-gate top-500 issuer priced by a market close, valUSD / balance of its common
      holding (units NS, USD) vs that close (unadjusted, session on/before as_of) -> share within 0.1 % / 0.5 %;
  (2) TARGETS: the holding of each --cusip (value per share, fairValLevel, balance, valUSD, name).
Filings: the Russell 1000 reference N-PORT already in the store, plus --extra "REGISTRANT_CIK|NAME_TOKEN|SERIES NAME"
(e.g. a different fund sponsor = an independent valuation). Output reports/gate_evidence/nport_cross_check_<as_of>.json
with status INVESTIGATION_ONLY_NOT_APPLIED. The gate chain never reads it.

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/nport_cross_check.py --as-of 2024-06-30 \
      --cusip 96145D105 --extra "0000036405|VANGUARD INDEX FUNDS|Vanguard Total Stock Market Index Fund"
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_submissions_merged  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"
TOL_TIGHT, TOL = 0.001, 0.005


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_ncc_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def per_share(h: dict) -> float | None:
    try:
        bal, val = float(h["balance"]), float(h["val_usd"])
    except (TypeError, ValueError, KeyError):
        return None
    if h.get("units") != "NS" or h.get("cur_cd") not in (None, "", "USD") or bal <= 0 or val <= 0:
        return None
    return val / bal


def cusip_to_cik(ref_holdings: list[dict], member_names: dict) -> dict:
    """CUSIP -> CIK from the reference N-PORT (holding name resolved to a CIK by the reference tool)."""
    by_name = {n: cik for cik, names in member_names.items() for n in names}
    out = {}
    for h in ref_holdings:
        if h.get("asset_cat") == "EC" and h.get("cusip") and h.get("name") in by_name:
            out.setdefault(h["cusip"], set()).add(by_name[h["name"]])
    return {c: next(iter(s)) for c, s in out.items() if len(s) == 1}


def market_closes(gate: dict) -> dict:
    """CIK -> unadjusted as-of close of top-500 rows priced by a market close (single listed line, no N-PORT basis)."""
    out = {}
    for r in gate.get("top500") or []:
        det = r.get("detail") or {}
        if r.get("cover_override") or det.get("price_type") or not det.get("mcap_price"):
            continue
        out[str(r.get("cik") or "").zfill(10)] = float(det["mcap_price"])
    return out


def calibrate(holdings: list[dict], cmap: dict, closes: dict) -> dict:
    rows = []
    for h in holdings:
        cik = cmap.get(h.get("cusip") or "")
        px = per_share(h) if h.get("asset_cat") == "EC" else None
        if cik in closes and px:
            rows.append({"cik": cik, "name": h.get("name"), "nport": px, "close": closes[cik],
                         "rel_diff": abs(px - closes[cik]) / closes[cik], "fair_val_level": h.get("fair_val_level")})
    if not rows:
        return {"n": 0}
    d = [r["rel_diff"] for r in rows]
    return {"n": len(rows), "within_0_1pct": sum(x <= TOL_TIGHT for x in d), "within_0_5pct": sum(x <= TOL for x in d),
            "median_rel_diff": statistics.median(d), "max_rel_diff": max(d),
            "fair_val_levels": {lv: sum(r["fair_val_level"] == lv for r in rows) for lv in {r["fair_val_level"] for r in rows}},
            "outside_0_5pct": sorted([r for r in rows if r["rel_diff"] > TOL], key=lambda r: -r["rel_diff"])[:25]}


def targets(holdings: list[dict], cusips: list[str]) -> dict:
    out = {}
    for c in cusips:
        hits = [h for h in holdings if (h.get("cusip") or "").upper() == c.upper() and h.get("asset_cat") == "EC"]
        out[c] = ({"status": f"HOLDINGS_{len(hits)}"} if len(hits) != 1 else
                  {"status": "UNIQUE", "value_per_share": per_share(hits[0]), **{k: hits[0].get(k) for k in
                   ("name", "balance", "val_usd", "units", "cur_cd", "fair_val_level", "isin")}})
    return out


def fetch_series_nport(store, frd, fnr, page_mod, log, registrant: str, token: str, series: str, as_of: str) -> dict:
    get = lambda aid, url, kind: (frd._fetch_one(store, aid, url, kind, frd.UA, log, False), frd._throttle(log, 0.15))  # noqa: E731
    get(f"submissions:{registrant}", fnr.SUBMISSIONS_URL.format(cik=registrant), "SEC_SUBMISSIONS")
    sub = load_submissions_merged(store, registrant)[0] or {}
    if token not in str(sub.get("name") or "").upper():
        return {"status": "REGISTRANT_NOT_VERIFIED", "registrant_name": sub.get("name")}
    for f in (sub.get("filings") or {}).get("files") or []:
        if str(f.get("filingTo") or "9999") >= as_of:
            get(f"submissions_page:{f['name']}", page_mod.SUBMISSIONS_PAGE_URL.format(name=f["name"]), "SEC_SUBMISSIONS_PAGE")
    sub = load_submissions_merged(store, registrant)[0] or {}
    for f in fnr.nport_filings_for(sub, as_of):
        hid = f"edgar_index_headers:{f['accn']}"
        get(hid, fnr.INDEX_HEADERS_URL.format(cik=int(registrant), nodash=f["accn"].replace("-", ""), accn=f["accn"]),
            "SEC_INDEX_HEADERS")
        if store.has(hid) and any(s.lower() == series.lower() for s in fnr.series_names(store.get_bytes(hid))):
            nid = f"nport_xml:{f['accn']}"
            get(nid, fnr.DOC_URL.format(cik=int(registrant), nodash=f["accn"].replace("-", ""), doc=fnr.raw_xml_doc(f["doc"])),
                "SEC_NPORT_XML")
            return {"status": "FOUND", "accession": f["accn"], "filed": f["filed"], "artifact": nid,
                    "registrant_name": sub.get("name")}
    return {"status": "SERIES_FILING_NOT_FOUND", "registrant_name": sub.get("name")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--cusip", action="append", default=[])
    ap.add_argument("--extra", action="append", default=[], help="REGISTRANT_CIK|NAME_TOKEN|SERIES NAME")
    a = ap.parse_args()
    frd, fnr, npr, page_mod = _load("fetch_real_data"), _load("fetch_nport_reference"), _load("nport_reported_prices"), _load("fetch_cover_xbrl")
    store = RawDatasetStore(a.store)
    log: list[dict] = []
    ref = json.loads((GE / f"russell1000_nport_{a.as_of}.json").read_text(encoding="utf-8"))
    gate = json.loads((GE / f"gate_chain_{a.as_of}_real_gha.json").read_text(encoding="utf-8"))
    ref_accn = ref["source"].split("NPORT-P ")[1].split(" ")[0]
    ref_h = npr.raw_holdings(store.get_bytes(f"nport_xml:{ref_accn}")) if store.has(f"nport_xml:{ref_accn}") else []
    cmap, closes = cusip_to_cik(ref_h, ref["member_names"]), market_closes(gate)
    filings = [{"label": ref["source"], "status": "FOUND", "accession": ref_accn, "filed": ref.get("source_vintage"),
                "artifact": f"nport_xml:{ref_accn}"}]
    for spec in a.extra:
        reg, token, series = (s.strip() for s in spec.split("|", 2))
        filings.append({"label": f"{series} ({reg})", **fetch_series_nport(store, frd, fnr, page_mod, log, reg.zfill(10),
                                                                              token.upper(), series, a.as_of)})
    for f in filings:
        if f["status"] != "FOUND" or not store.has(f["artifact"]):
            continue
        h = npr.raw_holdings(store.get_bytes(f["artifact"]))
        f.update({"n_holdings": len(h), "calibration_vs_as_of_close": calibrate(h, cmap, closes), "targets": targets(h, a.cusip)})
    doc = {"kind": "NPORT_CROSS_CHECK", "as_of": a.as_of, "status": "INVESTIGATION_ONLY_NOT_APPLIED",
           "n_control_closes": len(closes), "n_cusip_to_cik": len(cmap), "filings": filings, "log": log,
           "note": ("Measures whether N-PORT per-share values reproduce the as-of market close. Filed after as_of "
                    "(look-ahead); never applied to ranking without a user decision. Cutoff/rank is not an input.")}
    (GE / f"nport_cross_check_{a.as_of}.json").write_text(json.dumps(doc, indent=1, default=str) + "\n", encoding="utf-8")
    frd.write_store_index(store)
    print(json.dumps([{k: f.get(k) for k in ("label", "status", "filed")} | {
        "cal": {k: (f.get("calibration_vs_as_of_close") or {}).get(k) for k in ("n", "within_0_1pct", "within_0_5pct", "max_rel_diff")},
        "targets": f.get("targets")} for f in filings], indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
