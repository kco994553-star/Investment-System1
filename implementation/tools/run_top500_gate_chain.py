"""Offline C-21 gate chain over the persistent RawDatasetStore. No network.

Runs, in order, using the existing functions in tools/audit_mcap_store.py:
  listings (+ plan names whose CIK is known/resolvable from the stored sec_tickers)
  -> audit (rankable) -> ranked_top500 (#500 cutoff)
  -> evaluate_reference_coverage (S&P 500 = MISSING_LARGE_CAP_DETECTOR role only)
  -> Universe Completeness Gate -> Top-500 Sufficiency Gate -> Promotion Gate v2

Stops there. Official Top-500 is declared only when Promotion Gate v2 passes on
this evidence; walk-forward and the 500-company benchmark are reported
NOT_RUN otherwise. rankable >= 500 alone never promotes.

Usage:
  python tools/run_top500_gate_chain.py --store data/raw --as-of 2024-12-31 \
      --out reports/gate_evidence/gate_chain_2024-12-31.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.universe.resolve import current_ticker_map  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_chain_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extend_listings(store: RawDatasetStore, listings: dict, plan: dict | None) -> tuple[dict, list[str]]:
    """Add plan names not already listed (by normalized ticker). CIK from the plan,
    else from the stored sec_tickers artifact; unresolved names are returned, not invented."""
    amc = _load("audit_mcap_store")
    out = dict(listings)
    have = {amc._norm_ticker(m.get("yahoo")) for m in listings.values()}
    tmap = current_ticker_map(json.loads(store.get_bytes("sec_tickers"))) if store.has("sec_tickers") else {}
    unresolved = []
    for row in (plan or {}).get("priority_fetch_plan", []):
        t = amc._norm_ticker(row.get("ticker"))
        if not t or t in have:
            continue
        cik = row.get("cik") or tmap.get(t) or tmap.get(t.replace("-", "."))
        if not cik:
            unresolved.append(t)
            continue
        out[f"plan:{t.lower()}"] = {"yahoo": t, "cik": str(cik).zfill(10)}
        have.add(t)
    return out, unresolved


def run_chain(store: RawDatasetStore, listings: dict, as_of: str, detector_refs: list[dict],
              sufficiency_refs: list[dict], exchange_reference: dict | None, eligibility_evidence: dict | None,
              plan: dict | None = None, chart_range: str = "5y") -> dict:
    amc = _load("audit_mcap_store")
    d = amc._dt(as_of if "T" in as_of else as_of + "T00:00:00+00:00")
    listings, unresolved = extend_listings(store, listings, plan)
    audit = amc.audit(store, listings, d, chart_range)
    top = amc.ranked_top500(store, listings, d, chart_range)
    cutoff = top[499]["mcap"] if len(top) >= 500 else None
    ranked = {r["yahoo"] for r in top if r["yahoo"]}
    refs = []
    for ref in detector_refs:
        refs.append({**amc.evaluate_reference_coverage(store, listings, ranked, ref, chart_range),
                     "reference_role": "MISSING_LARGE_CAP_DETECTOR"})
    for ref in sufficiency_refs:
        refs.append(amc.evaluate_reference_coverage(store, listings, ranked, ref, chart_range))
    completeness = amc.build_universe_completeness_gate(audit, exchange_reference) if exchange_reference else None
    sufficiency = amc.build_top500_sufficiency_gate(audit, refs)
    gate_v2 = amc.build_promotion_gate_v2(audit, eligibility_evidence, completeness, sufficiency)
    n_blobs = sum(1 for aid in store.list_ids() if store.has(aid))
    official = bool(gate_v2["passed"])
    return {
        "kind": "TOP500_GATE_CHAIN_RUN", "as_of": audit["as_of"],
        "store": {"dir": str(store.root), "n_artifacts": n_blobs,
                  "status": "EMPTY_NO_RAW_DATA" if n_blobs == 0 else "PRESENT"},
        "listings": len(listings), "plan_names_unresolved": unresolved,
        "audit": audit, "rankable": audit["rankable"], "cutoff_500_mcap": cutoff,
        "reference_coverage": [{"name": r.get("name"), "role": r.get("reference_role") or "SUFFICIENCY",
                                "n_members": len(r.get("members") or []),
                                "n_missing_from_pool": len(r["missing_from_pool"]),
                                "n_present_not_rankable": len(r["present_not_rankable"]),
                                "n_present_rankable_outside_top500": len(r["present_rankable_outside_top500"]),
                                "missing_from_pool": r["missing_from_pool"]} for r in refs],
        "universe_completeness_gate": completeness, "top500_sufficiency_gate": sufficiency,
        "promotion_gate_v2": gate_v2,
        "official_top500_declared": official,
        "real_data_verified": False,
        "walk_forward": "NOT_RUN_GATE_V2_FAILED" if not official else "PENDING",
        "benchmark_500": "NOT_RUN_GATE_V2_FAILED" if not official else "PENDING",
        "note": "Fail-closed chain. S&P 500 is a missing-large-cap detector only and cannot by itself pass Sufficiency.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=GE / "missing_large_cap_priority_plan_2024-12-31.json")
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--detector-reference", type=Path, action="append",
                    help="PIT large-cap reference used only to detect missing names (default: reconstructed S&P 500)")
    ap.add_argument("--sufficiency-reference", type=Path, action="append", default=[],
                    help="independent dated PIT large-cap ranking reference that may count toward Sufficiency")
    ap.add_argument("--exchange-reference", type=Path, default=GE / "exchange_reference_wfe_2024-12-31.json")
    ap.add_argument("--eligibility-evidence", type=Path)
    ap.add_argument("--chart-range", default="5y")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    rd = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    det = a.detector_reference or [GE / "sp500_reconstructed_2024-12-31.json"]
    rep = run_chain(RawDatasetStore(a.store), rd(a.listings), a.as_of, [rd(p) for p in det],
                    [rd(p) for p in a.sufficiency_reference], rd(a.exchange_reference) if a.exchange_reference else None,
                    rd(a.eligibility_evidence) if a.eligibility_evidence else None,
                    rd(a.plan) if a.plan and a.plan.exists() else None, a.chart_range)
    s = json.dumps(rep, indent=2)
    if a.out:
        a.out.write_text(s + "\n", encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("as_of", "store", "listings", "rankable", "cutoff_500_mcap",
                                          "official_top500_declared", "walk_forward", "benchmark_500")}, indent=2))


if __name__ == "__main__":
    main()
