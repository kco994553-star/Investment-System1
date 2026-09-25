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
from investment_system.ingestion.replay import load_companyfacts, load_price_bars, load_submissions, load_submissions_merged  # noqa: E402
from investment_system.providers.sec_cover_shares import class_symbols, parse_cover, pit_filer_status, select_filing  # noqa: E402
from investment_system.universe.sources import pit_shares  # noqa: E402
from investment_system.universe.resolve import current_ticker_map  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_chain_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_cik_candidates(store: RawDatasetStore, candidates: dict | None) -> dict[str, dict]:
    """ticker -> {cik, verified, sec_name}. A candidate CIK is accepted only when the stored SEC
    submissions name (or a former name) contains one of its expected tokens."""
    out: dict[str, dict] = {}
    for c in (candidates or {}).get("candidates", []):
        t, cik = str(c["ticker"]).upper(), str(c["cik"]).zfill(10)
        sub = load_submissions(store, cik) or {}
        names = [str(sub.get("name") or "")] + [str(f.get("name") or "") for f in sub.get("formerNames") or []]
        ok = bool(sub) and any(tok.upper() in n.upper() for tok in c.get("expect_name_tokens", []) for n in names)
        out[t] = {"cik": cik, "verified": ok, "sec_name": sub.get("name"), "replace": bool(c.get("replaces_current_cik")),
                  "status": "VERIFIED_SEC_SUBMISSIONS_NAME" if ok else ("NAME_MISMATCH" if sub else "SUBMISSIONS_NOT_IN_STORE")}
    return out


def extend_listings(store: RawDatasetStore, listings: dict, plan: dict | None,
                    verified_ciks: dict[str, dict] | None = None) -> tuple[dict, list[str]]:
    """Add plan names not already listed (by normalized ticker). CIK from the plan,
    else from the stored sec_tickers artifact; unresolved names are returned, not invented."""
    amc = _load("audit_mcap_store")
    out = dict(listings)
    # PIT identity: a listed ticker whose current CIK is a successor entity created after as_of
    # (e.g. a 2025 holding-company reorganisation) uses its verified as-of CIK instead.
    for cid, m in listings.items():
        v = (verified_ciks or {}).get(amc._norm_ticker(m.get("yahoo"))) or {}
        if v.get("verified") and v.get("replace") and str(m.get("cik") or "").zfill(10) != v["cik"]:
            out[cid] = {**m, "cik": v["cik"], "cik_replaced_from": m.get("cik")}
    have = {amc._norm_ticker(m.get("yahoo")) for m in listings.values()}
    tmap = current_ticker_map(json.loads(store.get_bytes("sec_tickers"))) if store.has("sec_tickers") else {}
    unresolved = []
    for row in (plan or {}).get("priority_fetch_plan", []):
        t = amc._norm_ticker(row.get("ticker"))
        if not t or t in have:
            continue
        v = (verified_ciks or {}).get(t) or {}
        pit = v["cik"] if v.get("verified") and v.get("replace") else None  # same PIT identity rule as listed names
        cik = pit or row.get("cik") or tmap.get(t) or tmap.get(t.replace("-", ".")) or (v.get("cik") if v.get("verified") else None)
        if not cik:
            unresolved.append(t)
            continue
        out[f"plan:{t.lower()}"] = {"yahoo": t, "cik": str(cik).zfill(10)}
        have.add(t)
    return out, unresolved


def company_level_listings(store: RawDatasetStore, listings: dict) -> tuple[dict, dict]:
    """One row per issuer (CIK). The row-level listings map carries preferreds (BAC-PB),
    OTC foreign lines (ASMLF) and extra share classes under the same CIK; ranking each
    as a separate company multiplies one issuer's total shares by every line's price.
    Primary line = first SEC submissions `tickers` entry present among the issuer's lines,
    else the shortest symbol (ties alphabetical). Returns (listings, report)."""
    amc = _load("audit_mcap_store")
    groups: dict[str, list[tuple[str, dict]]] = {}
    for cid, m in listings.items():
        key = str(m.get("cik") or "").strip()
        key = str(int(key)).zfill(10) if key.isdigit() else f"nocik:{cid}"
        groups.setdefault(key, []).append((cid, m))
    out, dropped, methods = {}, [], {"SINGLE_LINE": 0, "SEC_SUBMISSIONS_PRIMARY": 0, "SHORTEST_SYMBOL_FALLBACK": 0}
    for key, rows in groups.items():
        if len(rows) == 1:
            out[rows[0][0]] = rows[0][1]
            methods["SINGLE_LINE"] += 1
            continue
        by_sym = {amc._norm_ticker(m.get("yahoo")): (cid, m) for cid, m in rows}
        sub = load_submissions(store, key) if not key.startswith("nocik:") else None
        pick = next((by_sym[amc._norm_ticker(t)] for t in (sub or {}).get("tickers") or [] if amc._norm_ticker(t) in by_sym), None)
        if pick is not None:
            methods["SEC_SUBMISSIONS_PRIMARY"] += 1
        else:
            pick = by_sym[min(by_sym, key=lambda t: (len(t), t))]
            methods["SHORTEST_SYMBOL_FALLBACK"] += 1
        out[pick[0]] = pick[1]
        dropped.append({"cik": key, "kept": pick[1].get("yahoo"),
                        "dropped": sorted(m.get("yahoo") for cid, m in rows if cid != pick[0])})
    return out, {"n_rows": len(listings), "n_companies": len(out), "n_dropped_rows": len(listings) - len(out),
                 "methods": methods, "multi_line_issuers": dropped}


FOREIGN_FORMS = {"20-F", "20-F/A", "40-F", "40-F/A"}


DOMESTIC_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
ELIGIBILITY_RULE = ("US_DOMESTIC_FILER_AT_AS_OF: the latest periodic report the issuer filed on or before as_of is a "
                    "10-K/10-Q. Foreign private issuers at as_of (20-F/40-F) are excluded from the US Market-Cap Top 500 "
                    "(user decision 2026-09-25; their US lines are mostly ADRs whose ratio is not in SEC data). Issuers with "
                    "no SEC filing by as_of did not exist as registrants then and are excluded. Basis: SEC submissions "
                    "'recent' + older filing pages, filingDate <= as_of (PIT; today's forms are not applied backward). "
                    "An issuer with neither a periodic report nor a traded price by as_of was not listed then (excluded).")


def _filer_status(store: RawDatasetStore, cik: str, as_of) -> str:
    sub, complete = load_submissions_merged(store, cik, as_of) if cik else (None, False)
    return pit_filer_status(sub, as_of, complete) if sub else "UNKNOWN"


def eligibility_filter(store: RawDatasetStore, listings: dict, as_of) -> tuple[dict, dict]:
    kept, excluded, not_registered, unknown, not_trading = {}, [], [], [], []
    for cid, m in listings.items():
        st = _filer_status(store, str(m.get("cik") or ""), as_of)
        if st == "UNKNOWN" and not any(b["observed_at"] <= as_of for b in load_price_bars(store, str(m.get("yahoo") or ""), "5y")):
            # no periodic report AND no traded price by as_of (e.g. a Form-10 spin-off listed in 2025): not listed then
            not_trading.append(m.get("yahoo"))
            continue
        if st == "FOREIGN":
            excluded.append(m.get("yahoo"))
        elif st == "NOT_REGISTERED_AT_AS_OF":
            not_registered.append(m.get("yahoo"))
        else:
            if st == "UNKNOWN":
                unknown.append(m.get("yahoo"))
            kept[cid] = {**m, "pit_filer_status": st}
    return kept, {"rule": ELIGIBILITY_RULE, "n_in": len(listings), "n_kept": len(kept),
                  "excluded_foreign_private_issuers": sorted(excluded),
                  "excluded_not_registered_at_as_of": sorted(not_registered),
                  "excluded_not_trading_at_as_of": sorted(not_trading),
                  "eligibility_unknown_kept": sorted(unknown)}


def _as_of_price(store: RawDatasetStore, symbol: str, as_of, chart_range: str):
    amc = _load("audit_mcap_store")
    bars = [b for b in load_price_bars(store, symbol, chart_range) if b["observed_at"] <= as_of]
    return amc.mcap_price(bars[-1], amc.load_splits(store, symbol, chart_range), as_of) if bars else None


def cover_mcap_overrides(store: RawDatasetStore, listings: dict, as_of, chart_range: str = "5y") -> tuple[dict, dict]:
    """company_id -> {'mcap', 'status', 'classes'} from the cover-page XBRL instance (tools/fetch_cover_xbrl.py).
    Listed classes: class shares x that class's as-of price. Unlisted/unpriced classes are not guessed
    (no conversion ratio in the data): the sum is then a LOWER BOUND."""
    out, unresolved = {}, {}
    for cid, m in listings.items():
        c = str(m.get("cik") or "")
        if not c.isdigit():
            continue
        c = c.zfill(10)
        f = select_filing(load_submissions_merged(store, c)[0] or {}, as_of)
        aid = f"xbrl_instance:{c}:{f['accn']}" if f else None
        if not aid or not store.has(aid):
            continue
        try:
            cover = parse_cover(store.get_bytes(aid))
        except Exception as e:  # noqa: BLE001
            unresolved[cid] = f"PARSE_ERROR_{type(e).__name__}"
            continue
        classes, syms = cover["classes"], class_symbols(cover)
        if not classes:
            unresolved[cid] = "NO_COVER_SHARES"
            continue
        if len(classes) == 1 and classes[0]["member"] is None:
            cf = load_companyfacts(store, c)
            sh = pit_shares(cf, as_of) if cf is not None else None
            if sh and sh["status"] == "OK" and (sh["shares"] or 0) > 0:
                continue  # companyfacts already resolves a single class
            px = _as_of_price(store, str(m.get("yahoo") or ""), as_of, chart_range)
            if px:
                out[cid] = {"mcap": classes[0]["shares"] * px, "status": "COVER_SINGLE_CLASS", "source": aid,
                            "classes": [{**classes[0], "symbol": m.get("yahoo"), "price": px}]}
            else:
                unresolved[cid] = "NO_PRICE"
            continue
        total, parts, lower = 0.0, [], False
        for cl in classes:
            sym = syms.get(cl["member"])
            px = _as_of_price(store, sym.replace(".", "-"), as_of, chart_range) if sym else None
            if px:
                total += cl["shares"] * px
            else:
                lower = True
            parts.append({**cl, "symbol": sym, "price": px})
        if total > 0:
            out[cid] = {"mcap": total, "status": "COVER_CLASS_SUM_LOWER_BOUND" if lower else "COVER_CLASS_SUM",
                        "source": aid, "classes": parts}
        else:
            unresolved[cid] = "NO_PRICED_CLASS"
    return out, unresolved


def mcap_quality_flags(store: RawDatasetStore, detail: dict) -> list[str]:
    """Reasons a row's PIT market cap is not yet trustworthy for Official promotion
    (contract: duplicate listings/share classes/ADR must be resolved first)."""
    flags = []
    st = detail.get("pit_filer_status")  # same PIT test as eligibility_filter
    if st == "FOREIGN":
        flags.append("FOREIGN_ISSUER_ADR_RATIO_UNRESOLVED")
    elif st == "UNKNOWN":
        flags.append("ELIGIBILITY_PIT_UNKNOWN")  # SEC shares are ordinary shares; the US line may be an ADR
    if detail.get("split_events") == "MISSING":
        flags.append("SPLIT_EVENTS_MISSING")
    return flags


def normalize_reference(ref: dict) -> dict:
    """Reference files store as_of as a date and the retrieval date inside 'source' text
    (e.g. sp500_reconstructed_2024-12-31.json: "... (fetched 2026-09-25)"). Normalise to the gate's
    shape; only values stated in the file are used (no vintage is invented)."""
    import re
    out = dict(ref)
    a = str(out.get("as_of") or "")
    if a and "T" not in a:
        out["as_of"] = a + "T00:00:00+00:00"
    if not out.get("source_vintage"):
        m = re.search(r"fetched (\d{4}-\d{2}-\d{2})", str(out.get("source") or ""))
        out["source_vintage"] = m.group(1) if m else None
    out.setdefault("name", out.get("kind"))
    return out


def _nodot(t) -> str:
    import re
    return re.sub(r"[^A-Z0-9]", "", str(t or "").upper())


def map_superset_members(ref: dict, row_listings: dict, pre_elig: dict, eligible: dict, amc) -> tuple[list[str], list[str]]:
    """Map reference tickers to pool symbols (iShares 'BRKB' == pool 'BRK-B'), and split out members whose
    issuer the documented eligibility rule excluded (foreign private / not registered at as_of): those are
    consistent with the rule, not missing. Members with no pool line keep their ticker (-> missing_from_pool)."""
    by_nodot = {_nodot(m.get("yahoo")): m for m in row_listings.values() if m.get("yahoo")}
    # CIK-identified members (e.g. SEC N-PORT holdings) map to the issuer's primary eligible line
    by_cik = {str(m.get("cik") or "").zfill(10): m for m in list(row_listings.values()) + list(pre_elig.values()) if m.get("cik")}
    by_cik.update({str(m.get("cik") or "").zfill(10): m for m in pre_elig.values() if m.get("cik")})
    cik_ids = ref.get("member_id_type") == "CIK10"
    elig_ciks = {str(m.get("cik") or "").zfill(10) for m in eligible.values()}
    pre_ciks = {str(m.get("cik") or "").zfill(10) for m in pre_elig.values()}
    mapped, excluded = [], []
    for t in ref.get("members") or []:
        m = by_cik.get(str(t).zfill(10)) if cik_ids else by_nodot.get(_nodot(t))
        if m is None:
            mapped.append(f"CIK{t}" if cik_ids else t)  # not in the pool -> reported as missing_from_pool
            continue
        c = str(m.get("cik") or "").zfill(10)
        if c in pre_ciks and c not in elig_ciks:
            excluded.append(t)
            continue
        mapped.append(m.get("yahoo"))
    return mapped, excluded


def eligibility_evidence_from_superset(sufficiency: dict, refs: list[dict], audit: dict) -> dict | None:
    """Base-gate eligibility attestation derived ONLY from a passed SUPERSET_REFERENCE: the pool contains, rankable,
    every member of an independent dated superset of the US top 500 (rule-excluded members listed)."""
    for r, full in zip(sufficiency.get("references") or [], refs):
        if r.get("reference_role") == "SUPERSET_REFERENCE" and r.get("passed"):
            return {"source": r["source"], "source_vintage": r["source_vintage"], "as_of": audit["as_of"],
                    "eligibility_complete": True, "basis": "SUPERSET_REFERENCE_FULLY_COVERED",
                    "reference_name": r["name"], "n_reference_members": r["n_members"],
                    "excluded_by_eligibility_rule": r.get("excluded_by_eligibility_rule")}
    return None


def run_chain(store: RawDatasetStore, listings: dict, as_of: str, detector_refs: list[dict],
              sufficiency_refs: list[dict], exchange_reference: dict | None, eligibility_evidence: dict | None,
              plan: dict | None = None, chart_range: str = "5y", cik_candidates: dict | None = None) -> dict:
    amc = _load("audit_mcap_store")
    d = amc._dt(as_of if "T" in as_of else as_of + "T00:00:00+00:00")
    cand = verify_cik_candidates(store, cik_candidates)
    row_listings, unresolved = extend_listings(store, listings, plan, cand)
    row_audit = amc.audit(store, row_listings, d, chart_range)
    # Official Top-500 is company-level: rank one line per issuer.
    listings, dedupe = company_level_listings(store, row_listings)
    listings_pre_elig = listings
    listings, eligibility = eligibility_filter(store, listings, d)
    overrides, cover_unresolved = cover_mcap_overrides(store, listings, d, chart_range)
    audit = amc.audit(store, listings, d, chart_range, overrides)
    top = amc.ranked_top500(store, listings, d, chart_range, overrides)
    cutoff = top[499]["mcap"] if len(top) >= 500 else None
    ranked_cids = {r["company_id"] for r in top}
    ranked_ciks = {str(listings[c].get("cik") or "").zfill(10) for c in ranked_cids}
    # every line of a ranked issuer counts as ranked for reference identity (GOOG == GOOGL issuer)
    ranked = {m.get("yahoo") for m in row_listings.values() if str(m.get("cik") or "").zfill(10) in ranked_ciks and m.get("yahoo")}
    refs = []
    detector_refs = [normalize_reference(r) for r in detector_refs]
    sufficiency_refs = [normalize_reference(r) for r in sufficiency_refs]
    for ref in detector_refs:
        refs.append({**amc.evaluate_reference_coverage(store, row_listings, ranked, ref, chart_range),
                     "reference_role": "MISSING_LARGE_CAP_DETECTOR"})
    for ref in sufficiency_refs:
        mapped, excluded_rule = map_superset_members(ref, row_listings, listings_pre_elig, listings, amc)
        cov = amc.evaluate_reference_coverage(store, row_listings, ranked, {**ref, "members": mapped}, chart_range)
        refs.append({**cov, "members": ref.get("members"), "excluded_by_eligibility_rule": excluded_rule})
    completeness = amc.build_universe_completeness_gate(audit, exchange_reference) if exchange_reference else None
    sufficiency = amc.build_top500_sufficiency_gate(audit, refs)
    derived_eligibility = None
    if eligibility_evidence is None:
        derived_eligibility = eligibility_evidence_from_superset(sufficiency, refs, audit)
        eligibility_evidence = derived_eligibility
    gate_v2 = amc.build_promotion_gate_v2(audit, eligibility_evidence, completeness, sufficiency)
    n_blobs = sum(1 for aid in store.list_ids() if store.has(aid))
    top_rows = []
    for r in top:
        det = {**amc.row_detail(store, listings[r["company_id"]], d, chart_range),
               "pit_filer_status": listings[r["company_id"]].get("pit_filer_status")}
        ov = overrides.get(r["company_id"])
        top_rows.append({**r, "cik": listings[r["company_id"]].get("cik"), "detail": det, "cover_override": ov,
                         "quality_flags": mcap_quality_flags(store, det) if not ov else
                         [f for f in mcap_quality_flags(store, det) if f != "SPLIT_EVENTS_MISSING"],
                         "notes": ["RANK_IS_LOWER_BOUND"] if ov and ov["status"].endswith("LOWER_BOUND") else []})
    flag_counts: dict[str, int] = {}
    for r in top_rows:
        for f in r["quality_flags"]:
            flag_counts[f] = flag_counts.get(f, 0) + 1
    by_norm = {amc._norm_ticker(m.get("yahoo")): m for m in row_listings.values()}
    not_rankable_detail = {t: amc.row_detail(store, by_norm[amc._norm_ticker(t)], d, chart_range)
                           for ref in refs for t in ref["present_not_rankable"] if amc._norm_ticker(t) in by_norm}
    # A lower-bound issuer ranked outside the top 500 might belong inside it: membership is undetermined.
    lb_outside = sorted(listings[c].get("yahoo") for c, o in overrides.items()
                        if o["status"].endswith("LOWER_BOUND") and c not in ranked_cids)
    # Diagnostic only: why each eligible issuer is not rankable (base gate: ELIGIBLE_LISTINGS_NOT_FULLY_RANKABLE).
    unrankable = {}
    for cid, m in listings.items():
        if cid in overrides:
            continue
        det = amc.row_detail(store, m, d, chart_range)
        if det["mcap"] and det["mcap"] > 0:
            continue
        reason = (f"SHARES_{det['shares_status']}" if det["shares"] is None else
                  "NO_AS_OF_PRICE" if det["mcap_price"] is None else "NON_POSITIVE_SHARES_OR_PRICE")
        unrankable[m.get("yahoo")] = {"reason": reason, "cik": m.get("cik"), "shares": det["shares"],
                                      "price_observed_at": det["price_observed_at"], "pit_filer_status": m.get("pit_filer_status")}
    official_blockers = ([] if gate_v2["passed"] else ["PROMOTION_GATE_V2_FAILED"]) + \
        [f"TOP500_ROWS_{k}" for k in sorted(flag_counts)] + \
        (["LOWER_BOUND_ISSUERS_OUTSIDE_TOP500"] if lb_outside else [])
    official = not official_blockers
    return {
        "kind": "TOP500_GATE_CHAIN_RUN", "as_of": audit["as_of"],
        "store": {"dir": str(store.root), "n_artifacts": n_blobs,
                  "status": "EMPTY_NO_RAW_DATA" if n_blobs == 0 else "PRESENT"},
        "listings": len(listings), "plan_names_unresolved": unresolved, "cik_candidate_verification": cand,
        "ranking_basis": "COMPANY_LEVEL_ONE_LINE_PER_CIK; US_DOMESTIC_FILERS; COVER_XBRL_CLASS_SUM_FOR_MULTI_CLASS",
        "row_level_audit": {k: row_audit[k] for k in ("listings", "rankable", "top_cutoff_mcap_if_500_rankable")},
        "company_dedupe": dedupe, "eligibility": eligibility,
        "cover_overrides": {listings[c].get("yahoo"): {k: v for k, v in o.items()} for c, o in overrides.items()},
        "cover_unresolved": {listings[c].get("yahoo"): v for c, v in cover_unresolved.items()},
        "lower_bound_issuers_outside_top500": lb_outside, "unrankable_issuers": unrankable,
        "audit": audit, "rankable": audit["rankable"], "cutoff_500_mcap": cutoff,
        "top500": top_rows, "top500_quality_flag_counts": flag_counts,
        "reference_not_rankable_detail": not_rankable_detail,
        "reference_coverage": [{"name": r.get("name"), "role": r.get("reference_role") or "SUFFICIENCY",
                                "n_members": len(r.get("members") or []),
                                "n_missing_from_pool": len(r["missing_from_pool"]),
                                "n_present_not_rankable": len(r["present_not_rankable"]),
                                "n_present_rankable_outside_top500": len(r["present_rankable_outside_top500"]),
                                "missing_from_pool": r["missing_from_pool"]} for r in refs],
        "universe_completeness_gate": completeness, "top500_sufficiency_gate": sufficiency,
        "promotion_gate_v2": gate_v2, "eligibility_evidence_derived_from_superset": derived_eligibility,
        "official_top500_declared": official, "official_blockers": official_blockers,
        "real_data_verified": False,
        "walk_forward": "NOT_RUN_OFFICIAL_BLOCKED" if not official else "PENDING",
        "benchmark_500": "NOT_RUN_OFFICIAL_BLOCKED" if not official else "PENDING",
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
    ap.add_argument("--extra-listings", type=Path, action="append", default=[],
                    help="additional listings JSON (e.g. russell1000_extra_listings_<as_of>.json)")
    ap.add_argument("--sufficiency-reference", type=Path, action="append", default=[],
                    help="independent dated PIT large-cap ranking reference that may count toward Sufficiency")
    ap.add_argument("--exchange-reference", type=Path, default=GE / "exchange_reference_wfe_2024-12-31.json")
    ap.add_argument("--eligibility-evidence", type=Path)
    ap.add_argument("--chart-range", default="5y")
    ap.add_argument("--cik-candidates", type=Path, default=GE / "delisted_cik_candidates_2024-12-31.json")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    rd = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    det = a.detector_reference or [GE / "sp500_reconstructed_2024-12-31.json"]
    base = rd(a.listings)
    for x in a.extra_listings:
        if x.exists():
            base.update(rd(x))
    rep = run_chain(RawDatasetStore(a.store), base, a.as_of, [rd(p) for p in det],
                    [rd(p) for p in a.sufficiency_reference], rd(a.exchange_reference) if a.exchange_reference else None,
                    rd(a.eligibility_evidence) if a.eligibility_evidence else None,
                    rd(a.plan) if a.plan and a.plan.exists() else None, a.chart_range,
                    rd(a.cik_candidates) if a.cik_candidates and a.cik_candidates.exists() else None)
    s = json.dumps(rep, indent=2)
    if a.out:
        a.out.write_text(s + "\n", encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("as_of", "store", "listings", "rankable", "cutoff_500_mcap",
                                          "official_top500_declared", "walk_forward", "benchmark_500")}, indent=2))


if __name__ == "__main__":
    main()
