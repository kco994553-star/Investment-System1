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


def _never_files_periodic(store: RawDatasetStore, cik: str) -> bool:
    """Submissions exist (all pages stored) and contain no 10-K/10-Q/20-F/40-F at ANY date (an IPO that files its
    first 10-Q after as_of is therefore NOT caught here)."""
    sub, complete = load_submissions_merged(store, cik) if cik else (None, False)
    if not sub or not complete:
        return False
    forms = set(((sub.get("filings") or {}).get("recent") or {}).get("form") or [])
    return bool(forms) and not forms & (DOMESTIC_FORMS | FOREIGN_FORMS)


def eligibility_filter(store: RawDatasetStore, listings: dict, as_of) -> tuple[dict, dict]:
    kept, excluded, not_registered, unknown, not_trading, no_sec_periodic = {}, [], [], [], [], []
    for cid, m in listings.items():
        st = _filer_status(store, str(m.get("cik") or ""), as_of)
        if st == "UNKNOWN" and not any(b["observed_at"] <= as_of for b in load_price_bars(store, str(m.get("yahoo") or ""), "5y")):
            # no periodic report AND no traded price by as_of (e.g. a Form-10 spin-off listed in 2025): not listed then
            not_trading.append(m.get("yahoo"))
            continue
        if st == "UNKNOWN" and _never_files_periodic(store, str(m.get("cik") or "")):
            # e.g. a bank that files its 10-K/10-Q with a bank regulator, not the SEC: not an SEC periodic filer (rule)
            no_sec_periodic.append(m.get("yahoo"))
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
                  "excluded_no_sec_periodic_reports": sorted(no_sec_periodic),
                  "eligibility_unknown_kept": sorted(unknown)}


def _as_of_price(store: RawDatasetStore, symbol: str, as_of, chart_range: str):
    amc = _load("audit_mcap_store")
    bars = [b for b in load_price_bars(store, symbol, chart_range) if b["observed_at"] <= as_of]
    return amc.mcap_price(bars[-1], amc.load_splits(store, symbol, chart_range), as_of) if bars else None


SCALE_RATIO_BAND = (0.5, 2.0)


def share_fact_stale(store: RawDatasetStore, cik10: str, sh: dict | None, as_of) -> bool:
    """True when the companyfacts share fact pit_shares chose was NOT filed with the issuer's latest 10-K/10-Q filed on or
    before as_of. Every periodic report tags the cover share count; if the latest one has no undimensioned fact the
    filing reported it per class (dimensions are dropped by companyfacts) and the older value is stale (PPLI 2020 zero,
    MA/CME/IBKR one class only)."""
    if not sh or sh.get("available_at") is None:
        return False
    f = select_filing(load_submissions_merged(store, cik10)[0] or {}, as_of)
    if not f:
        return False
    return str(sh["available_at"])[:10] < f["filed"]


def share_scale_check(cf: dict, as_of, shares: float) -> dict:
    """Cross-check a companyfacts share count against the same issuer's latest basic weighted-average share count
    (period ending and filed on or before as_of). A ratio outside SCALE_RATIO_BAND flags a possible XBRL scale error
    (HXL 2024-10: 81,002,128,000,000 tagged for 81,002,128). No reference -> not flagged (nothing to compare)."""
    from investment_system.universe.sources import _pit_rows
    cut = as_of.date().isoformat()
    rows = [r for r in _pit_rows(cf or {}, "us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", "shares", as_of)
            if str(r.get("end") or "9999") <= cut and float(r["val"]) > 0]
    if not rows or not shares:
        return {"flagged": False, "reference": None}
    ref = max(rows, key=lambda r: (str(r.get("end")), str(r["_filed"])))
    ratio = shares / float(ref["val"])
    return {"flagged": not (SCALE_RATIO_BAND[0] <= ratio <= SCALE_RATIO_BAND[1]), "ratio": ratio,
            "reference": {"concept": "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic", "val": ref["val"],
                          "end": ref.get("end"), "filed": str(ref["_filed"])[:10], "accn": ref.get("accn")}}


def cover_text_share_count(text: str, shares: float) -> tuple[int | None, int | None, str | None]:
    """(k, count, quote): the unique k in (0, 3, 6, 9) such that shares / 10^k is an exact integer printed (with thousands
    separators) in the filing's cover text near 'outstanding'. k = 0 confirms the XBRL value as printed."""
    import re
    found = []
    for k in (0, 3, 6, 9):
        if shares % (10 ** k):
            continue
        cnt = int(shares // (10 ** k))
        if cnt < 1000:
            continue
        for m in re.finditer(re.escape(f"{cnt:,}"), text):
            ctx = text[max(0, m.start() - 250):m.end() + 250]
            whole = not re.match(r",?\d", text[m.end():m.end() + 2]) and not re.search(r"[\d,]$", text[max(0, m.start() - 1):m.start()])
            if whole and re.search(r"outstanding", ctx, re.I):
                found.append((k, cnt, ctx))
                break
    ks = {f[0] for f in found}
    return (found[0][0], found[0][1], found[0][2]) if len(ks) == 1 else (None, None, None)


def share_scale_overrides(store: RawDatasetStore, listings: dict, overrides: dict, as_of, chart_range: str = "5y") -> dict:
    """For companyfacts-ranked issuers whose share count fails share_scale_check: use the count printed in the cover text
    of the latest 10-K/10-Q filed <= as_of (sec_filing_doc artifact) when exactly one power-of-ten reading matches;
    otherwise EXCLUDE the issuer (not rankable, fail-closed). Never approximates."""
    frc = _load("fetch_class_rights_evidence")
    ev = {}
    for cid, m in listings.items():
        if cid in overrides:
            continue
        c = str(m.get("cik") or "")
        if not c.isdigit():
            continue
        c = c.zfill(10)
        cf = load_companyfacts(store, c)
        sh = pit_shares(cf, as_of) if cf is not None else None
        if not sh or sh["status"] != "OK" or not sh["shares"]:
            continue
        chk = share_scale_check(cf, as_of, sh["shares"])
        if not chk["flagged"]:
            continue
        rec = {"cik": c, "xbrl_shares": sh["shares"], "check": chk}
        f = select_filing(load_submissions_merged(store, c)[0] or {}, as_of)
        did = f"sec_filing_doc:{c}:{f['accn']}" if f else None
        k = cnt = quote = None
        if did and store.has(did):
            k, cnt, quote = cover_text_share_count(frc.html_text(store.get_bytes(did)), sh["shares"])
        px = _as_of_price(store, str(m.get("yahoo") or ""), as_of, chart_range)
        if cnt and px:
            status = "SHARE_COUNT_CONFIRMED_BY_COVER_TEXT" if k == 0 else "SHARE_SCALE_CORRECTED_FROM_COVER_TEXT"
            rec.update({"status": status, "document": did, "scale_power": k, "shares": cnt, "quote": quote,
                        "formula": f"{cnt} shares (cover text) x {px}"})
            overrides[cid] = {"mcap": cnt * px, "status": status, "source": did, "classes": [], "share_scale": rec}
        else:
            rec.update({"status": "SHARE_SCALE_UNVERIFIED", "document": did, "document_in_store": bool(did and store.has(did))})
            overrides[cid] = {"mcap": None, "exclude": True, "status": "SHARE_SCALE_UNVERIFIED", "source": did, "classes": [],
                              "share_scale": rec}
        ev[m.get("yahoo")] = rec
    return ev


def exclude_stale_unresolved(store: RawDatasetStore, listings: dict, overrides: dict, as_of) -> dict:
    """An issuer still priced from companyfacts although that share fact is stale (not filed with the latest 10-K/10-Q
    <= as_of: per-class counts were dropped) and the cover route could not resolve it: its count may be one class only,
    so it is EXCLUDED (not rankable) instead of ranked on a possibly wrong number."""
    out = {}
    for cid, m in listings.items():
        if cid in overrides:
            continue
        c = str(m.get("cik") or "")
        if not c.isdigit():
            continue
        c = c.zfill(10)
        cf = load_companyfacts(store, c)
        sh = pit_shares(cf, as_of) if cf is not None else None
        if sh and sh["status"] == "OK" and share_fact_stale(store, c, sh, as_of):
            rec = {"cik": c, "shares": sh["shares"], "fact_filed": str(sh["available_at"])[:10], "status": "STALE_SHARE_FACT_UNRESOLVED"}
            overrides[cid] = {"mcap": None, "exclude": True, "status": rec["status"], "source": None, "classes": [], "stale": rec}
            out[m.get("yahoo")] = rec
    return out


def same_cik_ticker(store: RawDatasetStore, cik10: str, symbol: str) -> str | None:
    """The issuer's own SEC ticker equal to a cover TradingSymbol once separators are removed ('BFB' -> 'BF-B'), same
    CIK only and unique; None otherwise."""
    tickers = (load_submissions_merged(store, cik10)[0] or {}).get("tickers") or []
    hits = sorted({str(t).replace(".", "-") for t in tickers if _nodot(t) == _nodot(symbol)})
    return hits[0] if len(hits) == 1 else None


def _as_of_bar(store: RawDatasetStore, symbol: str, as_of, chart_range: str):
    """(price as used by the gate, observed_at) of the last bar on/before as_of, or (None, None)."""
    amc = _load("audit_mcap_store")
    bars = [b for b in load_price_bars(store, symbol, chart_range) if b["observed_at"] <= as_of]
    if not bars:
        return None, None
    return amc.mcap_price(bars[-1], amc.load_splits(store, symbol, chart_range), as_of), bars[-1]["observed_at"]


def _filed_dt(store: RawDatasetStore, cik10: str, accn: str | None):
    from datetime import datetime as _dt
    rec = ((load_submissions_merged(store, cik10)[0] or {}).get("filings") or {}).get("recent") or {}
    for a, f in zip(rec.get("accessionNumber") or [], rec.get("filingDate") or []):
        if a == accn:
            return _dt.fromisoformat(str(f) + "T00:00:00+00:00")
    return None


def gate_audited_candidates(store: RawDatasetStore, listings: dict, overrides: dict, as_of, chart_range: str = "5y") -> list[dict]:
    """The candidate representation the Promotion Gate actually ranked, in official_mcap500_snapshot's input shape
    (company_id, ticker, cik, shares, shares_available_at, price, price_observed_at) plus provenance
    (shares_basis, price_basis, gate_mcap). Overrides are expressed as equivalent shares of the reference price
    (gate_mcap / price); excluded issuers are left out. Nothing is recomputed differently from the gate."""
    from datetime import datetime as _dt
    out = []
    for cid, m in listings.items():
        c = str(m.get("cik") or "").zfill(10)
        ov = overrides.get(cid)
        base = {"company_id": cid, "ticker": m.get("yahoo"), "cik": m.get("cik")}
        if ov and ov.get("exclude"):
            continue
        if ov and ov.get("mcap"):
            if ov["status"] == "NPORT_REPORTED_VALUE":
                px = ov["nport_reported_value"]["price"]
                vd = _dt.fromisoformat(str(ov["valuation_date"]) + "T21:00:00+00:00")  # fund valuation at the 2024-12-31 close
                cf = load_companyfacts(store, c)
                shr = pit_shares(cf, as_of) if cf is not None else None
                out.append({**base, "shares": ov["mcap"] / px, "price": px, "price_observed_at": vd,
                            "shares_available_at": shr["available_at"] if shr else None,
                            "shares_basis": "COMPANYFACTS_PIT", "price_basis": "NPORT_REPORTED_VALUE", "gate_mcap": ov["mcap"]})
                continue
            priced = [x for x in ov.get("classes") or [] if x.get("price")]
            if priced:
                ref = priced[0]
                sym = str(ref.get("price_symbol") or ref.get("symbol") or m.get("yahoo") or "").replace(".", "-")
                px, obs = _as_of_bar(store, sym, as_of, chart_range)
                px = ref["price"]
            else:  # text-corrected / confirmed single count priced on the primary line
                px, obs = _as_of_bar(store, str(m.get("yahoo") or ""), as_of, chart_range)
            src = str(ov.get("source") or "")
            accn = src.split(":")[2] if src.count(":") == 2 else None
            sh_at = _filed_dt(store, c, accn)
            for fd in [x.get("filed") for x in ((ov.get("class_economics") or {}).get("citations") or [])]:
                t = _dt.fromisoformat(str(fd) + "T00:00:00+00:00")
                sh_at = t if sh_at is None or t > sh_at else sh_at
            out.append({**base, "shares": ov["mcap"] / px if px else None, "price": px, "price_observed_at": obs,
                        "shares_available_at": sh_at, "shares_basis": ov["status"], "price_basis": "CLOSE_X_POST_AS_OF_SPLIT_FACTOR",
                        "gate_mcap": ov["mcap"]})
            continue
        cf = load_companyfacts(store, c) if str(m.get("cik") or "").isdigit() else None
        shr = pit_shares(cf, as_of) if cf is not None else None
        if not shr or shr["shares"] is None:
            continue
        px, obs = _as_of_bar(store, str(m.get("yahoo") or ""), as_of, chart_range)
        if not px or shr["shares"] <= 0:
            continue
        out.append({**base, "shares": shr["shares"], "price": px, "price_observed_at": obs, "shares_available_at": shr["available_at"],
                    "shares_basis": "COMPANYFACTS_PIT", "price_basis": "CLOSE_X_POST_AS_OF_SPLIT_FACTOR", "gate_mcap": shr["shares"] * px})
    return out


def gate_snapshot_consistency(store: RawDatasetStore, listings: dict, top: list[dict], candidates: list[dict], as_of) -> dict:
    """official_mcap500_snapshot_from_store(gate_candidates=...) must reproduce the gate's top 500: same members, same
    order, same market caps (relative 1e-9). Any difference blocks the Official declaration."""
    from investment_system.universe.sources import official_mcap500_snapshot_from_store
    snap, rep = official_mcap500_snapshot_from_store(store, listings, as_of, gate_candidates=candidates)
    gate_ids = [r["company_id"] for r in top]
    snap_ids = list(snap.ids())
    cand = {c["company_id"]: c for c in candidates}
    gate_mcap = {r["company_id"]: r["mcap"] for r in top}
    diffs = [cid for cid in snap_ids if cid in gate_mcap and abs(cand[cid]["shares"] * cand[cid]["price"] - gate_mcap[cid]) > 1e-9 * gate_mcap[cid]]
    lost = [c for c in candidates if c["gate_mcap"] and c["company_id"] in gate_mcap and c["company_id"] not in snap_ids]
    only_gate, only_snap = sorted(set(gate_ids) - set(snap_ids)), sorted(set(snap_ids) - set(gate_ids))
    order_same = gate_ids == snap_ids
    by_basis: dict[str, int] = {}
    for cid in snap_ids:
        by_basis[cand[cid]["shares_basis"]] = by_basis.get(cand[cid]["shares_basis"], 0) + 1
    return {"passed": bool(snap_ids) and not only_gate and not only_snap and order_same and not diffs,
            "n_gate": len(gate_ids), "n_snapshot": len(snap_ids), "only_in_gate": only_gate, "only_in_snapshot": only_snap,
            "order_identical": order_same, "mcap_mismatch": diffs,
            "gate_members_excluded_by_snapshot": [{"company_id": c["company_id"], "price_basis": c["price_basis"]} for c in lost],
            "snapshot_excluded": rep.get("excluded", [])[:50], "shares_basis_counts": by_basis,
            "universe_id": snap.universe_id, "snapshot_cutoff_mcap": rep.get("cutoff_mcap")}


NOT_LISTED = r"not (?:be )?listed|no (?:established )?public (?:trading )?market|not (?:publicly )?traded"


def cover_text_single_count(text: str) -> int | None:
    """Single-class cover sentence '<n> shares of [the registrant's|our] Common Stock outstanding' (MTD); the unique count
    or None."""
    import re
    pat = r"([\d,]{6,})\s+shares\s+of\s+(?:the\s+registrant['’]s\s+|our\s+|its\s+)?common\s+stock[^.;]{0,80}?outstanding"
    vals = {int(m.group(1).replace(",", "")) for m in re.finditer(pat, text, re.I) if re.fullmatch(r"\d{1,3}(,\d{3})+", m.group(1))}
    return vals.pop() if len(vals) == 1 else None


def verify_symbol_mapping(store: RawDatasetStore, cik10: str, cover: dict, det: dict | None, symbol: str, as_of) -> tuple[str | None, list]:
    """Reviewed mapping of an undimensioned TradingSymbol to one class member (symbol_mappings_<as_of>.json). Accepted
    only if a quote found verbatim in a filing of that CIK filed on or before as_of either names every OTHER class as not
    listed/traded (DKS: 'Class B common stock ... not listed or traded on any stock exchange'), or names the listed
    member's class together with the symbol. Returns (member, checked citations) or (None, failures)."""
    import re
    if not det or det.get("symbol") != symbol:
        return None, ["NO_REVIEWED_MAPPING"]
    frc = _load("fetch_class_rights_evidence")
    members = [c["member"] for c in cover["classes"]]
    listed = det.get("listed_member")
    if listed not in members:
        return None, ["LISTED_MEMBER_NOT_ON_COVER"]
    others = [m for m in members if m != listed]
    fails, ok = [], []
    for q in det.get("citations") or []:
        aid, quote = str(q.get("artifact_id") or ""), re.sub(r"\s+", " ", str(q.get("quote") or "")).strip()
        parts = aid.split(":")
        if len(parts) != 3 or parts[1] != cik10 or not store.has(aid) or not _filed_on_or_before(store, cik10, parts[2], as_of):
            fails.append(f"CITATION_INVALID:{aid}")
            continue
        if len(quote) < 40 or quote not in frc.html_text(store.get_bytes(aid)):
            fails.append(f"QUOTE_NOT_IN_FILING:{aid}")
            continue
        names_others_unlisted = bool(re.search(NOT_LISTED, quote, re.I)) and all(
            any(p in quote for p in frc.class_phrases(o)) for o in others)
        names_listed_with_symbol = re.search(rf"\b{re.escape(symbol)}\b", quote) and any(p in quote for p in frc.class_phrases(listed))
        if names_others_unlisted or names_listed_with_symbol:
            ok.append({"artifact_id": aid, "quote": quote})
        else:
            fails.append(f"QUOTE_DOES_NOT_ESTABLISH_LISTING:{aid}")
    return (listed, ok) if ok else (None, fails)


def cover_text_symbol_member(text: str, cover: dict) -> tuple[str | None, str | None]:
    """Listed member from the cover-page TEXT of the same filing when XBRL tags one undimensioned TradingSymbol for several
    classes and the Security12bTitle names no class letter (IAC: title 'Common stock', members CommonClassA/B). The title's
    head ('Common stock') must be followed directly by the exact share count of exactly ONE member (whole document text:
    the iXBRL hidden header can precede the cover page by tens of KB), not preceded by
    'Class X' ("Common Stock 80,479,073 Class B common stock 5,789,499"). Returns (member, verbatim quote) or (None, None)."""
    import re
    titles = cover["titles"].get(None) or []
    if len(titles) != 1 or re.search(r"Class\s+[A-Z]\b", titles[0]):
        return None, None
    head = titles[0].split(",")[0].strip()
    if not head:
        return None, None
    counts = {f"{int(c['shares']):,}": c["member"] for c in cover["classes"] if c.get("member") and c.get("shares")}
    hits = set()
    quote = None
    for m in re.finditer(r"(?<!Class [A-Z] )" + re.escape(head) + r"\s+([\d,]{5,})", text, re.I):
        if m.group(1) in counts:
            hits.add(counts[m.group(1)])
            quote = text[max(0, m.start() - 120):m.end() + 60]
    return (hits.pop(), quote) if len(hits) == 1 else (None, None)


def cover_mcap_overrides(store: RawDatasetStore, listings: dict, as_of, chart_range: str = "5y",
                         symbol_mappings: dict | None = None) -> tuple[dict, dict]:
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
        text_basis = None
        undim = sorted(set(cover["symbols"].get(None) or []))
        did = f"sec_filing_doc:{c}:{f['accn']}"
        if not syms and len(undim) == 1 and len(classes) > 1 and store.has(did):
            member, quote = cover_text_symbol_member(_load("fetch_class_rights_evidence").html_text(store.get_bytes(did)), cover)
            if member:
                syms = {member: undim[0]}
                text_basis = {"basis": "COVER_TEXT_TITLE_COUNT_MATCH", "document": did, "quote": quote}
        if not syms and len(undim) == 1 and len(classes) > 1:
            member, cites = verify_symbol_mapping(store, c, cover, ((symbol_mappings or {}).get("issuers") or {}).get(c), undim[0], as_of)
            if member:
                syms = {member: undim[0]}
                text_basis = {"basis": "REVIEWED_FILING_QUOTE", "citations": cites}
        if not classes:
            cf0 = load_companyfacts(store, c)
            cnt = (cover_text_single_count(_load("fetch_class_rights_evidence").html_text(store.get_bytes(did)))
                   if len(undim) == 1 and not [k for k in cover["symbols"] if k] and store.has(did) else None)
            px = _as_of_price(store, str(m.get("yahoo") or ""), as_of, chart_range)
            if cnt and px and cf0 is not None and not share_scale_check(cf0, as_of, float(cnt))["flagged"] \
                    and undim[0].replace(".", "-") == str(m.get("yahoo") or ""):
                out[cid] = {"mcap": cnt * px, "status": "COVER_TEXT_SINGLE_COUNT", "source": did,
                            "classes": [{"member": None, "shares": float(cnt), "symbol": undim[0], "price": px,
                                         "symbol_basis": {"basis": "COVER_TEXT_SINGLE_COUNT", "document": did}}]}
            else:
                unresolved[cid] = "NO_COVER_SHARES"
            continue
        if len(classes) == 1 and classes[0]["member"] is None:
            cf = load_companyfacts(store, c)
            sh = pit_shares(cf, as_of) if cf is not None else None
            if sh and sh["status"] == "OK" and (sh["shares"] or 0) > 0 and not share_fact_stale(store, c, sh, as_of):
                continue  # companyfacts already resolves a single class
            if cf is not None and share_scale_check(cf, as_of, classes[0]["shares"])["flagged"]:
                unresolved[cid] = "COVER_SHARES_FAIL_SCALE_CHECK"  # same scale error in the instance (HXL): text route
                continue
            px = _as_of_price(store, str(m.get("yahoo") or ""), as_of, chart_range)
            if px:
                out[cid] = {"mcap": classes[0]["shares"] * px, "status": "COVER_SINGLE_CLASS", "source": aid,
                            "classes": [{**classes[0], "symbol": m.get("yahoo"), "price": px}]}
            else:
                unresolved[cid] = "NO_PRICE"
            continue
        total, parts, lower = 0.0, [], False
        listed = [cl for cl in classes if syms.get(cl["member"])]
        for cl in classes:
            sym = syms.get(cl["member"])
            px = _as_of_price(store, sym.replace(".", "-"), as_of, chart_range) if sym else None
            if sym and not px:
                alt = same_cik_ticker(store, c, sym)
                if alt and alt != sym.replace(".", "-"):
                    px = _as_of_price(store, alt, as_of, chart_range)
                    if px:
                        cl = {**cl, "price_symbol": alt, "price_basis": "SAME_CIK_TICKER_SEPARATOR_NORMALISED"}
            if text_basis and sym and px and sym.replace(".", "-") != str(m.get("yahoo") or ""):
                # a symbol mapped from cover text must agree with the same-CIK primary line when both have a close
                prim = _as_of_price(store, str(m.get("yahoo") or ""), as_of, chart_range)
                if prim and abs(px - prim) / prim > 0.005:
                    px, cl = None, {**cl, "price_conflict": {"symbol_close": px, "primary_line_close": prim}}
            if sym and not px and len(listed) == 1 and "price_conflict" not in cl:
                # ticker changed after as_of (SQ -> XYZ): the issuer's only listed class trades as its primary line
                px = _as_of_price(store, str(m.get("yahoo") or ""), as_of, chart_range)
                if px:
                    cl = {**cl, "price_symbol": m.get("yahoo"), "price_basis": "PRIMARY_LINE_SAME_CIK_TICKER_CHANGE"}
            if px:
                total += cl["shares"] * px
            else:
                lower = True
            parts.append({**cl, "symbol": sym, "price": px, **({"symbol_basis": text_basis} if text_basis and sym else {})})
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


def equal_economics_upper_bound(override: dict) -> float | None:
    """Lower bound + every unpriced class valued at the issuer's highest priced class price per share."""
    priced = [c["price"] for c in override.get("classes") or [] if c.get("price")]
    if not priced:
        return None
    return override["mcap"] + sum(c["shares"] * max(priced) for c in override["classes"] if not c.get("price"))


# Claims a verbatim filing quote must support before an unlisted class counts in listed-class equivalents.
RATIO_ONE = (r"one[- ]for[- ]one|1:1|1-for-1|one-to-one|on a one for one basis|share[- ]for[- ]share|into one share of|"
             r"for one share of|an equal number of")
CLAIM_PATTERNS = {"conversion_ratio": RATIO_ONE, "exchange_ratio": RATIO_ONE,
                  # 'one share of our Class B', 'an equal number of shares of TKO Class B', 'a corresponding number of shares of our Class D'
                  "pairing": r"(one|a|an equal number of|an equivalent number of|corresponding number of) shares? of (?:[\w’']+ ){0,2}Class [A-Z]|"
                             r"an (?:equal|equivalent) number of(?: [\w’'-]+){0,5} Class [A-Z]|"
                             r"equal to the number of|for each (?:\w+ )?units?",
                  "identical_rights": r"identical in all respects|share ratably with|same rights and privileges"}
BASIS_CLAIMS = {"CONVERTIBLE_INTO_LISTED": {"conversion_ratio"},
                "PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED": {"pairing", "exchange_ratio"},
                "ECONOMICALLY_IDENTICAL_TO_LISTED": {"identical_rights"}}


def _filed_on_or_before(store: RawDatasetStore, cik10: str, accn: str, as_of) -> str | None:
    rec = ((load_submissions_merged(store, cik10)[0] or {}).get("filings") or {}).get("recent") or {}
    for a, f in zip(rec.get("accessionNumber") or [], rec.get("filingDate") or []):
        if a == accn and str(f) <= as_of.date().isoformat():
            return str(f)
    return None


def verify_class_economics(store: RawDatasetStore, cik10: str, override: dict, det: dict, as_of) -> tuple[float | None, dict]:
    """Economic-equivalent listed shares of a lower-bound issuer from a reviewed determination whose every claim is
    backed by a VERBATIM quote found in an SEC filing of that CIK filed on or before as_of (sec_filing_doc artifact).
    Returns (market cap, evidence); (None, evidence with failures) when anything is unproven (fail-closed)."""
    import re
    frc = _load("fetch_class_rights_evidence")
    fails, used, texts = [], [], {}
    classes = override.get("classes") or []
    listed = [c for c in classes if c.get("price")]
    if len(listed) != 1 or listed[0].get("member") != det.get("listed_member"):
        return None, {"status": "NOT_DETERMINED", "failures": ["LISTED_CLASS_MISMATCH"]}
    px, eq_shares, terms = listed[0]["price"], listed[0]["shares"], [f"{listed[0]['member']} {listed[0]['shares']:.0f} x 1"]
    for c in classes:
        if c.get("price"):
            continue
        cd = (det.get("classes") or {}).get(c.get("member"))
        if not cd:
            fails.append(f"NO_DETERMINATION:{c.get('member')}")
            continue
        need = set(BASIS_CLAIMS.get(cd.get("basis"), {"UNKNOWN_BASIS"}))
        if "UNKNOWN_BASIS" in need or cd.get("ratio") != 1:
            fails.append(f"UNSUPPORTED_BASIS_OR_RATIO:{c.get('member')}")
            continue
        phrases = frc.class_phrases(c.get("member"))
        got = set()
        for q in cd.get("citations") or []:
            aid, quote = str(q.get("artifact_id") or ""), re.sub(r"\s+", " ", str(q.get("quote") or "")).strip()
            parts = aid.split(":")
            if len(parts) != 3 or parts[0] != "sec_filing_doc" or parts[1] != cik10 or not store.has(aid):
                fails.append(f"CITATION_ARTIFACT_INVALID:{aid}")
                continue
            filed = _filed_on_or_before(store, cik10, parts[2], as_of)
            if not filed:
                fails.append(f"CITATION_NOT_FILED_ON_OR_BEFORE_AS_OF:{aid}")
                continue
            if aid not in texts:
                texts[aid] = frc.html_text(store.get_bytes(aid))
            if len(quote) < 40 or quote not in texts[aid]:
                fails.append(f"QUOTE_NOT_IN_FILING:{aid}")
                continue
            names_class = any(p in quote for p in phrases)
            inst = str(cd.get("paired_instrument") or "")
            if not names_class and not (inst and inst in quote and q.get("supports") == ["exchange_ratio"]):
                fails.append(f"QUOTE_DOES_NOT_NAME_CLASS:{aid}")
                continue
            if not names_class:
                q = {**q, "_instrument_only": True}
            for claim in q.get("supports") or []:
                if claim in need and re.search(CLAIM_PATTERNS[claim], quote, re.I):
                    got.add(claim)
            used.append({"class": c.get("member"), "artifact_id": aid, "filed": filed, "supports": sorted(got & need), "quote": quote,
                         **({"names": "PAIRED_INSTRUMENT_ONLY"} if q.get("_instrument_only") else {})})
        inst = str(cd.get("paired_instrument") or "")
        if inst and any(u.get("names") == "PAIRED_INSTRUMENT_ONLY" for u in used if u["class"] == c.get("member")):
            # a ratio quote naming only the unit counts only if a verified pairing quote names both the unit and the class
            if not any("pairing" in u["supports"] and inst in u["quote"] and any(p in u["quote"] for p in phrases)
                       for u in used if u["class"] == c.get("member") and u.get("names") != "PAIRED_INSTRUMENT_ONLY"):
                got.discard("exchange_ratio")
        if need - got:
            fails.append(f"CLAIMS_UNPROVEN:{c.get('member')}:{','.join(sorted(need - got))}")
            continue
        eq_shares += cd["ratio"] * c["shares"]
        terms.append(f"{c.get('member')} {c['shares']:.0f} x {cd['ratio']}")
    if fails:
        return None, {"status": "NOT_DETERMINED", "failures": fails, "citations_checked": used}
    return eq_shares * px, {"status": "ECONOMIC_EQUIVALENT_DETERMINED", "listed_price": px, "economic_equivalent_listed_shares": eq_shares,
                            "formula": f"({' + '.join(terms)}) x {px}", "double_count_check": det.get("double_count_check"),
                            "citations": used}


def apply_class_economics(store: RawDatasetStore, overrides: dict, listings: dict, determinations: dict | None, as_of) -> dict:
    """Replace verified lower-bound overrides by their economic-equivalent market cap (status COVER_ECONOMIC_EQUIVALENT)."""
    ev = {}
    for cid, o in list(overrides.items()):
        c = str(listings[cid].get("cik") or "").zfill(10)
        det = ((determinations or {}).get("issuers") or {}).get(c)
        if not det or not o["status"].endswith("LOWER_BOUND"):
            continue
        mcap, e = verify_class_economics(store, c, o, det, as_of)
        ev[listings[cid].get("yahoo")] = {**e, "lower_bound": o["mcap"]}
        if mcap:
            overrides[cid] = {**o, "mcap": mcap, "status": "COVER_ECONOMIC_EQUIVALENT", "lower_bound": o["mcap"], "class_economics": e}
    return ev


def apply_nport_reported_prices(store: RawDatasetStore, overrides: dict, listings: dict, exception: dict | None,
                                evidence: dict | None, as_of, chart_range: str = "5y") -> dict:
    """User decision 2026-09-26: issuers listed in the exception file (PINC, WOLF) that have NO market close on/before
    as_of may be valued with the N-PORT reported value per share (valUSD / balance, report date = as_of). Price type
    NPORT_REPORTED_VALUE, never mixed with closes. Everything is re-verified from stored raw artifacts (fail-closed)."""
    npr = _load("nport_reported_prices")
    frc = _load("fetch_class_rights_evidence")
    allowed = (exception or {}).get("issuers") or {}
    out = {}
    for cid, m in listings.items():
        sym, cik = m.get("yahoo"), str(m.get("cik") or "").zfill(10)
        if sym not in allowed:
            continue  # never extended beyond the listed issuers
        fails = []
        ev = ((evidence or {}).get("issuers") or {}).get(sym) or {}
        if allowed[sym] != cik:
            fails.append("CIK_MISMATCH")
        if cid in overrides:
            fails.append("ALREADY_DETERMINED")
        if _as_of_price(store, str(sym), as_of, chart_range):
            fails.append("MARKET_CLOSE_AVAILABLE")  # a real close always wins; the exception is for missing closes only
        if ev.get("status") != "IDENTITY_AND_PRICE_VERIFIED":
            fails.append("EVIDENCE_NOT_VERIFIED")
        nid = str((evidence or {}).get("source_artifact") or "")
        px = h = None
        if not fails:
            if not store.has(nid):
                fails.append("NPORT_XML_NOT_IN_STORE")
            else:
                raw = store.get_bytes(nid)
                if (_load("fetch_nport_reference").parse_nport(raw).get("report_date") or "") != as_of.date().isoformat():
                    fails.append("NPORT_REPORT_DATE_NOT_AS_OF")
                want = ev.get("holding_raw") or {}
                hits = [x for x in npr.raw_holdings(raw) if x["cusip"] == want.get("cusip") and x["name"] == want.get("name")]
                if len(hits) != 1:
                    fails.append(f"HOLDING_NOT_UNIQUE_{len(hits)}")
                else:
                    h = hits[0]
                    px, why = npr.reported_price(h)
                    if px is None or abs(px - float(ev.get("price") or 0)) > 1e-9 * px:
                        fails.append(f"PRICE_NOT_REPRODUCED_{why}")
        attested = []
        if not fails:
            for x in ev.get("cusip_attestation") or []:
                aid = str(x.get("artifact_id") or "")
                parts = aid.split(":")
                if (len(parts) == 3 and parts[1] == cik and store.has(aid) and _filed_on_or_before(store, cik, parts[2], as_of)
                        and npr.cusip_attested(frc.html_text(store.get_bytes(aid)), h["cusip"])):
                    attested.append({"artifact_id": aid, "form": x.get("form"), "filed": x.get("filed")})
            if not attested:
                fails.append("CUSIP_NOT_ATTESTED")
        sh = None
        if not fails:
            cf = load_companyfacts(store, cik)
            shr = pit_shares(cf, as_of) if cf is not None else None
            sh = shr["shares"] if shr and shr["status"] == "OK" else None
            if not sh or sh <= 0:
                fails.append("NO_PIT_SHARES")
            elif share_fact_stale(store, cik, shr, as_of):
                fails.append("STALE_SHARE_FACT")
        rec = {"cik": cik, "price_type": npr.PRICE_TYPE, "valuation_date": (evidence or {}).get("valuation_date"),
               "market_close_basis_of_other_issuers": "last close on/before as_of (2024-12-30 session)",
               "status": "APPLIED" if not fails else "NOT_APPLIED", "failures": fails}
        if not fails:
            rec.update({"price": px, "shares": sh, "mcap": sh * px, "source_artifact": nid, "cusip": h["cusip"],
                        "cusip_attested_by": attested,
                        "formula": f"{sh:.0f} shares x (valUSD {h['val_usd']} / balance {h['balance']} {h['units']}) = {sh * px:.2f}"})
            overrides[cid] = {"mcap": sh * px, "status": npr.PRICE_TYPE, "source": nid, "price_type": npr.PRICE_TYPE,
                              "valuation_date": rec["valuation_date"], "classes": [], "nport_reported_value": rec}
        out[sym] = rec
    return out


def run_chain(store: RawDatasetStore, listings: dict, as_of: str, detector_refs: list[dict],
              sufficiency_refs: list[dict], exchange_reference: dict | None, eligibility_evidence: dict | None,
              plan: dict | None = None, chart_range: str = "5y", cik_candidates: dict | None = None,
              class_economics: dict | None = None, nport_exception: dict | None = None,
              nport_prices: dict | None = None, symbol_mappings: dict | None = None) -> dict:
    amc = _load("audit_mcap_store")
    d = amc._dt(as_of if "T" in as_of else as_of + "T00:00:00+00:00")
    cand = verify_cik_candidates(store, cik_candidates)
    row_listings, unresolved = extend_listings(store, listings, plan, cand)
    row_audit = amc.audit(store, row_listings, d, chart_range)
    # Official Top-500 is company-level: rank one line per issuer.
    listings, dedupe = company_level_listings(store, row_listings)
    listings_pre_elig = listings
    listings, eligibility = eligibility_filter(store, listings, d)
    overrides, cover_unresolved = cover_mcap_overrides(store, listings, d, chart_range, symbol_mappings)
    class_econ = apply_class_economics(store, overrides, listings, class_economics, d)
    share_scale = share_scale_overrides(store, listings, overrides, d, chart_range)
    nport_px = apply_nport_reported_prices(store, overrides, listings, nport_exception, nport_prices, d, chart_range)
    stale_excluded = exclude_stale_unresolved(store, listings, overrides, d)
    price_exceptions = {"price_type": "NPORT_REPORTED_VALUE", "issuers": nport_px,
                        "note": ("Valued at the SEC N-PORT reported value per share on 2024-12-31 (filed after as_of), not a market "
                                 "close; all other issuers use their last close on/before as_of (2024-12-30 session). "
                                 "Exception limited to the user-approved issuers (PINC, WOLF).")} if nport_px else None
    audit = amc.audit(store, listings, d, chart_range, overrides)
    top = amc.ranked_top500(store, listings, d, chart_range, overrides)
    cutoff = top[499]["mcap"] if len(top) >= 500 else None
    ranked_cids = {r["company_id"] for r in top}
    ranked_ciks = {str(listings[c].get("cik") or "").zfill(10) for c in ranked_cids}
    # every line of a ranked issuer counts as ranked for reference identity (GOOG == GOOGL issuer)
    ranked = {m.get("yahoo") for m in row_listings.values() if str(m.get("cik") or "").zfill(10) in ranked_ciks and m.get("yahoo")}
    # A lower-bound issuer ranked outside the top 500 might belong inside it. Rule (b), user decision 2026-09-25:
    # an unpriced share class is worth at most the highest priced class of the same issuer per share
    # (equal economics). If even that upper bound is below the #500 cutoff the issuer is settled outside.
    lb_settled, lb_outside = {}, []
    for c, o in overrides.items():
        if not o["status"].endswith("LOWER_BOUND") or c in ranked_cids:
            continue
        ub = equal_economics_upper_bound(o)
        if cutoff is not None and ub is not None and ub < cutoff:
            lb_settled[listings[c].get("yahoo")] = {"lower_bound": o["mcap"], "upper_bound": ub}
        else:
            lb_outside.append(listings[c].get("yahoo"))
    lb_outside.sort()
    # issuers whose market cap is determined by an override (ranked in the top 500, or settled outside by the
    # upper bound) are rankable for reference coverage; undetermined lower bounds stay not rankable.
    settled_syms = set(lb_settled)
    determined_ciks = {str(listings[c].get("cik") or "").zfill(10) for c in overrides
                       if not overrides[c].get("exclude") and (c in ranked_cids or listings[c].get("yahoo") in settled_syms
                                                               or not overrides[c]["status"].endswith("LOWER_BOUND"))}
    cik_of = {amc._norm_ticker(m.get("yahoo")): str(m.get("cik") or "").zfill(10) for m in row_listings.values()}

    undetermined_ciks = {str(listings[c].get("cik") or "").zfill(10) for c in overrides} - determined_ciks

    def _determined(cov: dict) -> dict:
        keep, moved = [], []
        for t in cov["present_not_rankable"]:
            (moved if cik_of.get(amc._norm_ticker(t)) in determined_ciks else keep).append(t)
        outside, undetermined = [], []
        for t in list(cov["present_rankable_outside_top500"]) + moved:
            (undetermined if cik_of.get(amc._norm_ticker(t)) in undetermined_ciks else outside).append(t)
        return {**cov, "present_not_rankable": keep + undetermined, "present_rankable_outside_top500": outside,
                "determined_by_cover_override": moved, "membership_undetermined_lower_bound": undetermined}
    refs = []
    detector_refs = [normalize_reference(r) for r in detector_refs]
    sufficiency_refs = [normalize_reference(r) for r in sufficiency_refs]
    for ref in detector_refs:
        refs.append({**_determined(amc.evaluate_reference_coverage(store, row_listings, ranked, ref, chart_range)),
                     "reference_role": "MISSING_LARGE_CAP_DETECTOR"})
    for ref in sufficiency_refs:
        mapped, excluded_rule = map_superset_members(ref, row_listings, listings_pre_elig, listings, amc)
        cov = _determined(amc.evaluate_reference_coverage(store, row_listings, ranked, {**ref, "members": mapped}, chart_range))
        refs.append({**cov, "members": ref.get("members"), "excluded_by_eligibility_rule": excluded_rule})
    completeness = amc.build_universe_completeness_gate(audit, exchange_reference) if exchange_reference else None
    sufficiency = amc.build_top500_sufficiency_gate(audit, refs)
    if price_exceptions:
        sufficiency = {**sufficiency, "price_basis_exceptions": price_exceptions}
    derived_eligibility = None
    if eligibility_evidence is None:
        derived_eligibility = eligibility_evidence_from_superset(sufficiency, refs, audit)
        eligibility_evidence = derived_eligibility
    gate_v2 = amc.build_promotion_gate_v2(audit, eligibility_evidence, completeness, sufficiency)
    if price_exceptions:
        gate_v2 = {**gate_v2, "price_basis_exceptions": price_exceptions}
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
    # Diagnostic only: why each eligible issuer is not rankable (base gate: ELIGIBLE_LISTINGS_NOT_FULLY_RANKABLE).
    unrankable = {}
    for cid, m in listings.items():
        if cid in overrides and overrides[cid].get("exclude"):
            unrankable[m.get("yahoo")] = {"reason": overrides[cid]["status"], "cik": m.get("cik"),
                                          "share_scale": overrides[cid].get("share_scale"), "stale": overrides[cid].get("stale")}
            continue
        if cid in overrides:
            continue
        det = amc.row_detail(store, m, d, chart_range)
        if det["mcap"] and det["mcap"] > 0:
            continue
        reason = (f"SHARES_{det['shares_status']}" if det["shares"] is None else
                  "NO_AS_OF_PRICE" if det["mcap_price"] is None else "NON_POSITIVE_SHARES_OR_PRICE")
        unrankable[m.get("yahoo")] = {"reason": reason, "cik": m.get("cik"), "shares": det["shares"],
                                      "price_observed_at": det["price_observed_at"], "pit_filer_status": m.get("pit_filer_status")}
    candidates = gate_audited_candidates(store, listings, overrides, d, chart_range)
    consistency = gate_snapshot_consistency(store, listings, top, candidates, d)
    official_blockers = ([] if gate_v2["passed"] else ["PROMOTION_GATE_V2_FAILED"]) + \
        ([] if consistency["passed"] else ["GATE_SNAPSHOT_INCONSISTENT"]) + \
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
        "lower_bound_issuers_outside_top500": lb_outside, "lower_bound_settled_outside_by_upper_bound": lb_settled,
        "class_economics_verification": class_econ, "price_basis_exceptions": price_exceptions,
        "share_scale_checks": share_scale, "stale_share_facts_excluded": stale_excluded,
        "gate_snapshot_consistency": consistency,
        "unrankable_issuers": unrankable,
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
    ap.add_argument("--class-economics", type=Path, help="reviewed determinations (default class_economics_<as_of>.json if present)")
    ap.add_argument("--nport-exception", type=Path, help="default nport_price_exception_<as_of>.json if present")
    ap.add_argument("--symbol-mappings", type=Path, help="default symbol_mappings_<as_of>.json if present")
    ap.add_argument("--nport-prices", type=Path, help="default nport_reported_prices_<as_of>.json if present")
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
                    rd(a.cik_candidates) if a.cik_candidates and a.cik_candidates.exists() else None,
                    rd(ce) if (ce := a.class_economics or GE / f"class_economics_{a.as_of}.json").exists() else None,
                    rd(ne) if (ne := a.nport_exception or GE / f"nport_price_exception_{a.as_of}.json").exists() else None,
                    rd(npp) if (npp := a.nport_prices or GE / f"nport_reported_prices_{a.as_of}.json").exists() else None,
                    rd(sm) if (sm := a.symbol_mappings or GE / f"symbol_mappings_{a.as_of}.json").exists() else None)
    s = json.dumps(rep, indent=2)
    if a.out:
        a.out.write_text(s + "\n", encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("as_of", "store", "listings", "rankable", "cutoff_500_mcap",
                                          "official_top500_declared", "walk_forward", "benchmark_500")}, indent=2))


if __name__ == "__main__":
    main()
