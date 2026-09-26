"""Primary documents for issuers whose companyfacts share count fails the scale cross-check (run_top500_gate_chain.
share_scale_check: dei/us-gaap shares vs latest basic weighted-average shares, ratio outside [0.5, 2]).

For each flagged eligible issuer, fetch the primary document of the latest 10-K/10-Q filed on or before --as-of
(artifact sec_filing_doc:<CIK10>:<accession>), so the gate chain can read the share count printed on the cover page.
Writes data/raw/share_scale_run_<ts>.json (flagged issuers, ratio, reference fact). Nothing is corrected here.

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/fetch_share_scale_docs.py --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_companyfacts, load_submissions_merged  # noqa: E402
from investment_system.providers.sec_cover_shares import select_filing  # noqa: E402
from investment_system.universe.sources import pit_shares  # noqa: E402

ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_fss_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flagged_issuers(store: RawDatasetStore, listings: dict, as_of: datetime, chain) -> list[dict]:
    out = []
    for m in listings.values():
        c = str(m.get("cik") or "")
        if not c.isdigit():
            continue
        c = c.zfill(10)
        cf = load_companyfacts(store, c)
        sh = pit_shares(cf, as_of) if cf is not None else None
        if not sh or sh["status"] != "OK" or not sh["shares"]:
            continue
        chk = chain.share_scale_check(cf, as_of, sh["shares"])
        if chk["flagged"]:
            out.append({"cik": c, "symbol": m.get("yahoo"), "shares": sh["shares"], **chk})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=ROOT / "reports" / "gate_evidence" / "missing_large_cap_priority_plan_2024-12-31.json")
    ap.add_argument("--cik-candidates", type=Path, help="default delisted_cik_candidates_<as_of>.json, else the 2024-12-31 file")
    ap.add_argument("--extra-listings", type=Path, action="append", default=[])
    a = ap.parse_args()
    if a.cik_candidates is None:  # point-in-time CIK corrections are per as_of (e.g. BLK holding-company reorganisation 2024-10-01)
        _ge = ROOT / "reports" / "gate_evidence"
        a.cik_candidates = next(p for p in (_ge / f"delisted_cik_candidates_{a.as_of}.json", _ge / "delisted_cik_candidates_2024-12-31.json")
                                if p.exists() or p.name.endswith("2024-12-31.json"))
    frd, chain = _load("fetch_real_data"), _load("run_top500_gate_chain")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
    base = rd(a.listings) or {}
    for x in a.extra_listings:
        base.update(rd(x) or {})
    rows, _ = chain.extend_listings(store, base, rd(a.plan), chain.verify_cik_candidates(store, rd(a.cik_candidates)))
    listings, _ = chain.company_level_listings(store, rows)
    listings, _ = chain.eligibility_filter(store, listings, d)
    flagged = flagged_issuers(store, listings, d, chain)
    # issuers the cover route leaves unresolved also need their cover-page text (MTD: no dei fact; DKS/IBKR mappings)
    _, unresolved = chain.cover_mcap_overrides(store, listings, d)
    seen = {r["cik"] for r in flagged}
    for cid in unresolved:
        c = str(listings[cid].get("cik") or "")
        if c.isdigit() and c.zfill(10) not in seen:
            flagged.append({"cik": c.zfill(10), "symbol": listings[cid].get("yahoo"), "reason": f"COVER_UNRESOLVED:{unresolved[cid]}"})
            seen.add(c.zfill(10))
    log: list[dict] = []
    for r in flagged:
        f = select_filing(load_submissions_merged(store, r["cik"])[0] or {}, d)
        if not f:
            continue
        did = f"sec_filing_doc:{r['cik']}:{f['accn']}"
        r["document"] = did
        frd._fetch_one(store, did, ARCHIVE_URL.format(cik=int(r["cik"]), nodash=f["accn"].replace("-", ""), doc=f["primary_document"]),
                       "SEC_FILING_DOCUMENT", frd.UA, log, False)
        frd._throttle(log, 0.15)
    rep = {"kind": "SHARE_SCALE_DOC_RUN", "as_of": a.as_of, "n_eligible": len(listings), "n_flagged": len(flagged),
           "flagged": flagged, "log": log}
    (store.root / f"share_scale_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(rep, indent=1, default=str))
    frd.write_store_index(store)
    print(json.dumps({"n_eligible": len(listings), "n_flagged": len(flagged),
                      "flagged": [(r["symbol"], round(r["ratio"], 4) if "ratio" in r else r.get("reason")) for r in flagged]}, indent=1)[:4000])


if __name__ == "__main__":
    main()
