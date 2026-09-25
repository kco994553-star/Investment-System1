"""Offline, memory-bounded audit of PIT market-cap coverage in RawDatasetStore.

Input is an explicit listings JSON mapping:
  {"company_id": {"cik": "...", "yahoo": "..."}, ...}
The tool does not infer historical eligibility and never marks a pool complete.
It loads one issuer at a time so a full SEC bulk store can be audited without
materialising all companyfacts payloads in memory.
"""
from __future__ import annotations
import argparse, json, sys, heapq
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.ingestion.replay import load_companyfacts, load_price_bars
from investment_system.universe.sources import pit_shares

def _dt(s:str)->datetime:
    d=datetime.fromisoformat(s.replace('Z','+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def load_splits(store:RawDatasetStore, symbol:str, chart_range:str='5y')->list[tuple[datetime,float]]|None:
    """Split events from the yahoo_events:<SYM>:<range> artifact (fetch_real_data.py --with-split-events).
    None = artifact absent (split status unknown)."""
    aid=f'yahoo_events:{str(symbol or "").upper()}:{chart_range}'
    if not symbol or not store.has(aid):
        return None
    try:
        res=(json.loads(store.get_bytes(aid)).get('chart') or {}).get('result') or [{}]
        ev=((res[0] or {}).get('events') or {}).get('splits') or {}
    except (ValueError, AttributeError):
        return None
    out=[]
    for v in ev.values():
        try:
            num,den=float(v['numerator']),float(v['denominator'])
            if num>0 and den>0:
                out.append((datetime.fromtimestamp(int(v['date']),tz=timezone.utc),num/den))
        except (KeyError,TypeError,ValueError):
            continue
    return sorted(out)

def split_factor_after(splits:list|None, as_of:datetime)->float:
    f=1.0
    for d,r in splits or []:
        if d>as_of: f*=r
    return f

def mcap_price(bar:dict, splits:list|None, as_of:datetime)->float:
    """As-of traded price for market cap: Yahoo 'close' is split-adjusted back in time (never use the
    dividend-adjusted 'adjclose'); undo splits that happened after as_of."""
    close=bar.get('close')
    return (close if close is not None else bar['price'])*split_factor_after(splits,as_of)

def audit(store:RawDatasetStore,listings:dict,as_of:datetime,chart_range='5y')->dict:
    counts={'listings':len(listings),'companyfacts':0,'price':0,'rankable':0,'missing_companyfacts':0,'missing_price':0,
            'missing_shares':0,'ambiguous_shares':0,'non_positive':0}
    ranked=[]
    for cid,m in listings.items():
        cf=load_companyfacts(store,str(m.get('cik',''))) if m.get('cik') else None
        if cf is None:
            counts['missing_companyfacts']+=1; continue
        counts['companyfacts']+=1
        sh=pit_shares(cf,as_of)
        if sh['shares'] is None:
            counts['ambiguous_shares' if sh['status']=='MULTI_CLASS_AMBIGUOUS' else 'missing_shares']+=1; continue
        bars=[b for b in load_price_bars(store,str(m.get('yahoo','')),chart_range) if b['observed_at']<=as_of] if m.get('yahoo') else []
        if not bars:
            counts['missing_price']+=1; continue
        counts['price']+=1
        px=mcap_price(bars[-1],load_splits(store,str(m.get('yahoo','')),chart_range),as_of)
        if sh['shares']<=0 or px<=0:
            counts['non_positive']+=1; continue
        counts['rankable']+=1
        ranked.append((sh['shares']*px,cid,m.get('yahoo')))
    ranked.sort(reverse=True)
    return {'kind':'PIT_MCAP_STORE_COVERAGE_AUDIT','as_of':as_of.isoformat(),'chart_range':chart_range,
            **counts,'top_cutoff_mcap_if_500_rankable': ranked[499][0] if len(ranked)>=500 else None,
            'candidate_pool_complete':False,'justified_official_top500':False,
            'note':'Diagnostic only. Explicit listings input is not proof of historical US-listing completeness.'}

def _top500_push(heap:list, mcap:float, cid:str, symbol:str|None)->None:
    """Keep only the 500 largest rows; heap[0] is the current cutoff."""
    row=(mcap,cid,symbol)
    if len(heap)<500:
        heapq.heappush(heap,row)
    elif row>heap[0]:
        heapq.heapreplace(heap,row)

def audit_many(store:RawDatasetStore,listings:dict,as_ofs:list[datetime],chart_range='5y')->list[dict]:
    """Audit many PIT dates with bounded memory and one parse per issuer.

    Each issuer's raw artifacts are loaded once. Price lookup uses binary search
    over its parsed bars, and each date retains only a 500-row min-heap rather
    than every company's ranking row. Memory is therefore one issuer working
    set + O(500 x dates), independent of universe size.
    """
    dates=sorted(as_ofs)
    states=[]
    for d in dates:
        states.append({'as_of':d,'counts':{'listings':len(listings),'companyfacts':0,'price':0,'rankable':0,
            'missing_companyfacts':0,'missing_price':0,'missing_shares':0,'ambiguous_shares':0,'non_positive':0},'top500':[]})
    for cid,m in listings.items():
        cf=load_companyfacts(store,str(m.get('cik',''))) if m.get('cik') else None
        bars=load_price_bars(store,str(m.get('yahoo','')),chart_range) if m.get('yahoo') else []
        bar_times=[b['observed_at'] for b in bars]
        splits=load_splits(store,str(m.get('yahoo','')),chart_range) if bars else None
        for st in states:
            c=st['counts']; d=st['as_of']
            if cf is None:
                c['missing_companyfacts']+=1; continue
            c['companyfacts']+=1
            sh=pit_shares(cf,d)
            if sh['shares'] is None:
                c['ambiguous_shares' if sh['status']=='MULTI_CLASS_AMBIGUOUS' else 'missing_shares']+=1; continue
            idx=bisect_right(bar_times,d)-1
            if idx<0:
                c['missing_price']+=1; continue
            c['price']+=1; px=mcap_price(bars[idx],splits,d)
            if sh['shares']<=0 or px<=0:
                c['non_positive']+=1; continue
            c['rankable']+=1
            _top500_push(st['top500'],sh['shares']*px,cid,m.get('yahoo'))
    out=[]
    for st in states:
        c=st['counts']; heap=st['top500']
        out.append({'kind':'PIT_MCAP_STORE_COVERAGE_AUDIT','as_of':st['as_of'].isoformat(),'chart_range':chart_range,**c,
            'top_cutoff_mcap_if_500_rankable':heap[0][0] if c['rankable']>=500 else None,
            'candidate_pool_complete':False,'justified_official_top500':False,
            'note':'Diagnostic only. Explicit listings input is not proof of historical US-listing completeness.'})
    return out

def build_ingestion_plan(store:RawDatasetStore, listings:dict, chart_range='5y')->dict:
    """Return a deterministic resume plan for artifacts absent from the store.

    This is an artifact-presence plan only; it does not claim listing completeness
    or that present artifacts contain usable PIT shares/prices. It lets a
    network-enabled runner fetch only missing inputs instead of re-fetching the
    whole candidate map.
    """
    missing_ciks=[]; missing_symbols=[]; unresolved=[]
    for cid in sorted(listings):
        meta=listings[cid]
        cik=str(meta.get('cik') or '').strip()
        sym=str(meta.get('yahoo') or '').strip().upper()
        if not cik or not sym:
            unresolved.append(cid)
        if cik:
            try: c10=str(int(cik)).zfill(10)
            except ValueError: c10=''
            if not c10:
                unresolved.append(cid)
            elif not store.has(f'companyfacts:{c10}'):
                missing_ciks.append(c10)
        if sym and not store.has(f'yahoo_chart:{sym}:{chart_range}'):
            missing_symbols.append(sym)
    return {
        'kind':'PIT_MCAP_INGESTION_RESUME_PLAN',
        'chart_range':chart_range,
        'listings':len(listings),
        'missing_companyfacts':len(set(missing_ciks)),
        'missing_price_artifacts':len(set(missing_symbols)),
        'unresolved_identifiers':sorted(set(unresolved)),
        'ciks':sorted(set(missing_ciks)),
        'symbols':sorted(set(missing_symbols)),
        'candidate_pool_complete':False,
        'note':'Artifact-presence plan only; does not prove historical listing completeness or usable PIT fields.',
    }

def build_pit_gap_plan(store:RawDatasetStore, listings:dict, as_ofs:list[datetime], chart_range='5y')->dict:
    """Classify *usable PIT* gaps, not merely absent artifacts.

    Present raw blobs can still be unusable for a requested historical date.
    This report separates absent artifacts from present-but-unusable PIT inputs so
    a network runner does not blindly refetch an artifact that already exists.
    It is diagnostic only and never proves universe completeness.
    """
    dates=sorted(as_ofs)
    per_date={d.isoformat():{'rankable':0,'absent_companyfacts':[], 'absent_price':[],
        'missing_shares_in_present_companyfacts':[], 'ambiguous_shares':[],
        'no_pit_price_in_present_artifact':[], 'non_positive':[]} for d in dates}
    for cid in sorted(listings):
        meta=listings[cid]
        cik=str(meta.get('cik') or '').strip(); sym=str(meta.get('yahoo') or '').strip().upper()
        try: c10=str(int(cik)).zfill(10) if cik else ''
        except ValueError: c10=''
        cf=load_companyfacts(store,c10) if c10 else None
        bars=load_price_bars(store,sym,chart_range) if sym else []
        bar_times=[b['observed_at'] for b in bars]
        for d in dates:
            st=per_date[d.isoformat()]
            if cf is None:
                st['absent_companyfacts'].append(cid); continue
            sh=pit_shares(cf,d)
            if sh['shares'] is None:
                st['ambiguous_shares' if sh['status']=='MULTI_CLASS_AMBIGUOUS' else 'missing_shares_in_present_companyfacts'].append(cid); continue
            if not bars:
                st['absent_price'].append(cid); continue
            idx=bisect_right(bar_times,d)-1
            if idx<0:
                st['no_pit_price_in_present_artifact'].append(cid); continue
            px=bars[idx]['price']
            if sh['shares']<=0 or px<=0:
                st['non_positive'].append(cid); continue
            st['rankable']+=1
    for st in per_date.values():
        for k,v in list(st.items()):
            if isinstance(v,list): st[k]=sorted(v)
    return {'kind':'PIT_MCAP_USABLE_GAP_PLAN','chart_range':chart_range,'listings':len(listings),
        'dates':per_date,'candidate_pool_complete':False,
        'note':'Diagnostic only. Present-but-unusable PIT inputs are separated from absent artifacts; no completeness claim.'}


def build_official_promotion_gate(audit_result:dict, eligibility_evidence:dict|None=None)->dict:
    """Fail-closed gate for treating a ranked run as the true Official Top-500.

    Ranking >=500 is necessary but not sufficient.  Until a dated eligibility
    source explicitly attests that the listings input is the complete investable
    US-listed candidate pool for the same as_of, this gate cannot pass.  The
    first implementation is intentionally strict: every eligible listing must
    also be rankable.  A future evidence-backed upper-bound method may relax
    that without changing the default fail-closed behavior.
    """
    ev=eligibility_evidence or {}
    as_of=str(audit_result.get('as_of') or '')
    evidence_as_of=str(ev.get('as_of') or '')
    listings=int(audit_result.get('listings') or 0)
    rankable=int(audit_result.get('rankable') or 0)
    source=str(ev.get('source') or '').strip()
    source_vintage=str(ev.get('source_vintage') or '').strip()
    eligibility_complete=ev.get('eligibility_complete') is True
    same_as_of=bool(as_of and evidence_as_of and as_of==evidence_as_of)
    all_rankable=listings>0 and rankable==listings
    enough=rankable>=500
    reasons=[]
    if not source: reasons.append('MISSING_ELIGIBILITY_SOURCE')
    if not source_vintage: reasons.append('MISSING_SOURCE_VINTAGE')
    if not eligibility_complete: reasons.append('ELIGIBILITY_COMPLETENESS_NOT_ATTESTED')
    if not same_as_of: reasons.append('EVIDENCE_AS_OF_MISMATCH')
    if not enough: reasons.append('FEWER_THAN_500_RANKABLE')
    if not all_rankable: reasons.append('ELIGIBLE_LISTINGS_NOT_FULLY_RANKABLE')
    passed=not reasons
    return {
        'kind':'OFFICIAL_MCAP500_PROMOTION_GATE', 'as_of':as_of,
        'passed':passed, 'candidate_pool_complete':passed,
        'justified_official_top500':passed, 'rankable':rankable, 'listings':listings,
        'eligibility_source':source or None, 'source_vintage':source_vintage or None,
        'reasons':reasons,
        'note':'Fail-closed. >=500 ranked alone never proves Official Top-500 completeness.',
    }

def build_universe_completeness_gate(audit_result: dict, exchange_reference: dict | None = None) -> dict:
    """Universe Completeness Gate: has the *whole* investable US universe been recovered?

    exchange_reference is an external, dated benchmark of total listed-company
    counts (e.g. WFE monthly statistics) used only to size the universe -- it
    NEVER by itself proves candidate_pool_complete. A candidate pool could hit
    the same total count while containing the wrong 598 names; this gate checks
    magnitude, not identity, and is explicitly weaker than that guarantee.
    Passing this gate is sufficient but not required for Official promotion --
    build_top500_sufficiency_gate below is the other, independent path.
    """
    ev = exchange_reference or {}
    as_of = str(audit_result.get("as_of") or "")
    evidence_as_of = str(ev.get("as_of") or "")
    companyfacts = int(audit_result.get("companyfacts") or 0)
    rankable = int(audit_result.get("rankable") or 0)
    source = str(ev.get("source") or "").strip()
    source_vintage = str(ev.get("source_vintage") or "").strip()
    low = ev.get("total_estimate_low")
    high = ev.get("total_estimate_high")
    same_as_of = bool(as_of and evidence_as_of and as_of == evidence_as_of)
    reasons = []
    if not source:
        reasons.append("MISSING_BENCHMARK_SOURCE")
    if not source_vintage:
        reasons.append("MISSING_BENCHMARK_VINTAGE")
    if low is None or high is None:
        reasons.append("MISSING_BENCHMARK_RANGE")
    if not same_as_of:
        reasons.append("BENCHMARK_AS_OF_MISMATCH")
    coverage_ratio = (companyfacts / low) if (isinstance(low, (int, float)) and low > 0) else None
    if coverage_ratio is None or coverage_ratio < 1.0:
        reasons.append("COMPANYFACTS_COVERAGE_BELOW_BENCHMARK_LOW_ESTIMATE")
    passed = not reasons
    return {
        "kind": "UNIVERSE_COMPLETENESS_GATE", "as_of": as_of, "passed": passed,
        "companyfacts": companyfacts, "rankable": rankable,
        "benchmark_source": source or None, "benchmark_source_vintage": source_vintage or None,
        "benchmark_low": low, "benchmark_high": high, "coverage_ratio": coverage_ratio,
        "reasons": reasons,
        "note": ("Sizes the universe only; identity completeness (candidate_pool_complete) is never "
                 "set True by this gate. An independent path to Official promotion -- see "
                 "build_top500_sufficiency_gate for the other."),
    }


def build_top500_sufficiency_gate(audit_result: dict, large_cap_references: list[dict]) -> dict:
    """Top-500 Sufficiency Gate: even without full universe recovery, is there
    positive evidence no missed company could displace the computed top 500?

    Each reference in large_cap_references is:
      {"name": str, "source": str, "source_vintage": str, "as_of": str,
       "membership_basis": str, "survivorship_risk": bool, "members": [ticker,...]}
    "members" must be the PIT membership for `as_of` (e.g. an S&P 500 roster
    reconstructed from dated addition/removal history) -- not today's roster
    applied backward. A reference whose membership_basis is UNDATED_ROSTER (the
    current-list-looks-like-history failure mode) or whose as_of does not match
    the audit's as_of is rejected outright: that is exactly the
    survivorship/look-ahead contamination this gate exists to catch.

    membership presence in the audit's raw listings/companyfacts is checked by
    the caller via `coverage` (see build_top500_sufficiency_gate_from_store),
    because this function is store-independent and only aggregates
    per-reference coverage dicts the caller supplies alongside each reference:
      reference["missing_from_pool"] = [tickers absent from listings entirely]
      reference["present_not_rankable"] = [tickers present but excluded from ranking]
      reference["present_rankable_outside_top500"] = [tickers ranked > 500]
    """
    as_of = str(audit_result.get("as_of") or "")
    rankable = int(audit_result.get("rankable") or 0)
    cutoff = audit_result.get("top_cutoff_mcap_if_500_rankable")
    reasons: list[str] = []
    ref_reports = []
    usable_refs = 0
    if not large_cap_references:
        reasons.append("NO_LARGE_CAP_REFERENCE_SUPPLIED")
    for ref in large_cap_references or []:
        rname = str(ref.get("name") or "UNNAMED")
        r_as_of = str(ref.get("as_of") or "")
        source = str(ref.get("source") or "").strip()
        source_vintage = str(ref.get("source_vintage") or "").strip()
        basis = str(ref.get("membership_basis") or "")
        members = list(ref.get("members") or [])
        missing = sorted(set(ref.get("missing_from_pool") or []))
        unranked = sorted(set(ref.get("present_not_rankable") or []))
        outside = sorted(set(ref.get("present_rankable_outside_top500") or []))
        r_reasons = []
        if not source:
            r_reasons.append("MISSING_REFERENCE_SOURCE")
        if not source_vintage:
            r_reasons.append("MISSING_REFERENCE_VINTAGE")
        if not members:
            r_reasons.append("EMPTY_REFERENCE_MEMBERSHIP")
        if not r_as_of or r_as_of != as_of:
            r_reasons.append("REFERENCE_AS_OF_MISMATCH")
        if basis == "UNDATED_ROSTER":
            r_reasons.append("UNDATED_ROSTER_SURVIVORSHIP_RISK")  # current list, not PIT -- look-ahead contamination
        if missing:
            r_reasons.append("MISSING_LARGE_CAP_NAMES")
        if unranked:
            r_reasons.append("REFERENCE_MEMBERS_PRESENT_BUT_NOT_RANKABLE")
        if outside:
            r_reasons.append("REFERENCE_MEMBERS_RANKED_OUTSIDE_TOP500")
        ref_ok = not r_reasons
        detector_only = ref.get("reference_role") == "MISSING_LARGE_CAP_DETECTOR"
        if ref_ok and not detector_only:
            usable_refs += 1
        ref_reports.append({
            "name": rname, "source": source or None, "source_vintage": source_vintage or None,
            "n_members": len(members), "missing_from_pool": missing, "present_not_rankable": unranked,
            "present_rankable_outside_top500": outside, "reasons": r_reasons, "passed": ref_ok,
            "reference_role": ref.get("reference_role"),
        })
    if rankable < 500:
        reasons.append("FEWER_THAN_500_RANKABLE")
    if cutoff is None:
        reasons.append("NO_CUTOFF_MCAP_COMPUTED")
    if usable_refs == 0:
        if any(r["passed"] and r["reference_role"] == "MISSING_LARGE_CAP_DETECTOR" for r in ref_reports):
            # e.g. S&P 500: index-committee membership (float/profitability/domicile rules) is not a
            # market-cap ranking, so full coverage only means "no missed S&P name", not sufficiency.
            reasons.append("ONLY_DETECTOR_REFERENCES_PASSED")
        else:
            reasons.append("NO_REFERENCE_PASSED_ITS_OWN_CHECKS")
    passed = not reasons
    return {
        "kind": "TOP500_SUFFICIENCY_GATE", "as_of": as_of, "passed": passed,
        "rankable": rankable, "cutoff_mcap": cutoff,
        "n_references_supplied": len(large_cap_references or []), "n_references_usable": usable_refs,
        "references": ref_reports, "reasons": reasons,
        "note": ("Does not require universe completeness. Passes only when >=1 independently sourced, "
                 "dated (PIT) large-cap reference has every member present, rankable, and inside the "
                 "computed top 500 -- i.e. positive evidence no plausible missed company changes the top 500."),
    }


def _norm_ticker(t) -> str:
    return str(t or "").strip().upper().replace(".", "-")


def ranked_top500(store: RawDatasetStore, listings: dict, as_of: datetime, chart_range: str = "5y") -> list[dict]:
    """Rank rows (mcap desc, max 500) using the same inputs/rules as audit(); #500 = last row."""
    heap: list = []
    for cid, m in listings.items():
        cf = load_companyfacts(store, str(m.get("cik", ""))) if m.get("cik") else None
        if cf is None:
            continue
        sh = pit_shares(cf, as_of)
        if sh["shares"] is None:
            continue
        bars = [b for b in load_price_bars(store, str(m.get("yahoo", "")), chart_range) if b["observed_at"] <= as_of] if m.get("yahoo") else []
        px = mcap_price(bars[-1], load_splits(store, str(m.get("yahoo", "")), chart_range), as_of) if bars else 0
        if not bars or sh["shares"] <= 0 or px <= 0:
            continue
        _top500_push(heap, sh["shares"] * px, cid, m.get("yahoo"))
    rows = sorted(heap, reverse=True)
    return [{"rank": i + 1, "company_id": cid, "yahoo": sym, "mcap": mc} for i, (mc, cid, sym) in enumerate(rows)]


def row_detail(store: RawDatasetStore, m: dict, as_of: datetime, chart_range: str = "5y") -> dict:
    """Per-issuer PIT market-cap inputs, for diagnosis and data-quality flags."""
    cf = load_companyfacts(store, str(m.get("cik", ""))) if m.get("cik") else None
    sh = pit_shares(cf, as_of) if cf is not None else {"status": "NO_COMPANYFACTS", "shares": None, "source": None, "available_at": None}
    sym = str(m.get("yahoo") or "")
    bars = [b for b in load_price_bars(store, sym, chart_range) if b["observed_at"] <= as_of] if sym else []
    splits = load_splits(store, sym, chart_range)
    bar = bars[-1] if bars else None
    px = mcap_price(bar, splits, as_of) if bar else None
    return {"yahoo": sym, "cik": m.get("cik"), "shares_status": sh["status"], "shares": sh["shares"],
            "shares_source": sh["source"], "shares_available_at": str(sh["available_at"]) if sh["available_at"] else None,
            "price_observed_at": bar["observed_at"].isoformat() if bar else None,
            "close": bar.get("close") if bar else None, "adjclose": bar.get("adjclose") if bar else None,
            "split_events": "MISSING" if splits is None else len(splits),
            "split_factor_after_as_of": split_factor_after(splits, as_of), "mcap_price": px,
            "mcap": (sh["shares"] * px) if (sh["shares"] and px) else None,
            "share_concepts_present": _share_concepts(cf, as_of) if sh["shares"] is None and cf is not None else None}


def _share_concepts(cf: dict, as_of: datetime) -> dict:
    """Diagnostic only: share-count concepts in the payload with their latest as-of row."""
    out = {}
    for tax, concepts in (cf.get("facts") or {}).items():
        for name, node in concepts.items():
            if "Shares" not in name or not any(k in name for k in ("Outstanding", "Issued", "Treasury")):
                continue
            rows = [r for r in (node.get("units") or {}).get("shares") or [] if str(r.get("filed") or "") <= as_of.date().isoformat()]
            if rows:
                r = max(rows, key=lambda x: (str(x.get("filed")), str(x.get("end"))))
                out[f"{tax}:{name}"] = {k: r.get(k) for k in ("end", "val", "filed", "form")}
    return out


def evaluate_reference_coverage(store: RawDatasetStore, listings: dict, ranked_top500_tickers: set[str],
                                 reference: dict, chart_range: str = "5y") -> dict:
    """Fill missing_from_pool / present_not_rankable / present_rankable_outside_top500
    for one reference by checking store presence per member ticker. Identity-only
    for missing_from_pool (no re-parse needed); companyfacts/price presence for the rest.
    """
    as_of = _dt(reference["as_of"]) if isinstance(reference.get("as_of"), str) else reference["as_of"]
    # Share-class tickers: references use 'BRK.B', listings/Yahoo use 'BRK-B' (same security).
    by_ticker = {_norm_ticker(m.get("yahoo")): (cid, m) for cid, m in listings.items()}
    ranked_norm = {_norm_ticker(x) for x in ranked_top500_tickers}
    missing, unranked, outside = [], [], []
    for raw_ticker in reference.get("members", []):
        t = raw_ticker.upper()
        hit = by_ticker.get(_norm_ticker(t))
        if hit is None:
            missing.append(t)
            continue
        cid, m = hit
        if _norm_ticker(t) in ranked_norm:
            continue
        cf = load_companyfacts(store, str(m.get("cik", ""))) if m.get("cik") else None
        if cf is None:
            unranked.append(t)
            continue
        sh = pit_shares(cf, as_of)
        sym = str(m.get("yahoo") or "")
        bars = [b for b in load_price_bars(store, sym, chart_range) if b["observed_at"] <= as_of] if sym else []
        if sh["shares"] is None or not bars:
            unranked.append(t)
        else:
            outside.append(t)  # present, has both inputs, computed rank must be > 500 since not in ranked set
    return {**reference, "missing_from_pool": missing, "present_not_rankable": unranked,
            "present_rankable_outside_top500": outside}


def build_promotion_gate_v2(audit_result: dict, eligibility_evidence: dict | None,
                             completeness_gate: dict | None, sufficiency_gate: dict | None) -> dict:
    """Extends build_official_promotion_gate (kept unchanged, still callable on its own)
    with the two independent paths this round adds. The original numeric/rankability
    checks still apply; on top of them, Official promotion needs EITHER full universe
    completeness OR positive top-500 sufficiency evidence -- neither is required to be
    the only route, matching how real index providers justify a cap without claiming
    they have enumerated every micro-cap in existence.
    """
    base = build_official_promotion_gate(audit_result, eligibility_evidence)
    completeness_ok = bool(completeness_gate and completeness_gate.get("passed"))
    sufficiency_ok = bool(sufficiency_gate and sufficiency_gate.get("passed"))
    reasons = list(base["reasons"])
    if not base["passed"]:
        pass  # base reasons already explain the numeric/eligibility failure
    if not (completeness_ok or sufficiency_ok):
        reasons.append("NEITHER_COMPLETENESS_NOR_SUFFICIENCY_GATE_PASSED")
    passed = base["passed"] and (completeness_ok or sufficiency_ok)
    return {
        "kind": "OFFICIAL_MCAP500_PROMOTION_GATE_V2", "as_of": base["as_of"], "passed": passed,
        "candidate_pool_complete": passed, "justified_official_top500": passed,
        "base_gate": base, "completeness_gate_passed": completeness_ok, "sufficiency_gate_passed": sufficiency_ok,
        "reasons": reasons,
        "note": "Fail-closed. Requires base numeric/eligibility checks AND (universe completeness OR top-500 sufficiency).",
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--store',default=str(ROOT/'data'/'raw')); ap.add_argument('--listings',type=Path,required=True)
    ap.add_argument('--as-of',required=True,action='append',help='Repeat for multi-date audit; issuer blobs are parsed once per run.'); ap.add_argument('--chart-range',default='5y'); ap.add_argument('--out',type=Path); ap.add_argument('--plan-out',type=Path,help='Write missing-artifact resume plan for a network-enabled runner.'); ap.add_argument('--gap-plan-out',type=Path,help='Write usable-PIT gap classification; distinguishes absent from present-but-unusable inputs.'); ap.add_argument('--eligibility-evidence',type=Path,help='Dated eligibility-completeness evidence JSON used only by the fail-closed Official promotion gate.'); ap.add_argument('--gate-out',type=Path,help='Write Official Top-500 promotion-gate result; requires --eligibility-evidence and a single --as-of.')
    ap.add_argument('--exchange-reference',type=Path,help='Dated total-listed-company benchmark JSON (e.g. WFE) for the Universe Completeness Gate.')
    ap.add_argument('--completeness-gate-out',type=Path,help='Write Universe Completeness Gate result; requires --exchange-reference and a single --as-of.')
    ap.add_argument('--large-cap-references',type=Path,help='JSON list of dated PIT large-cap reference sets (with missing_from_pool/present_not_rankable/present_rankable_outside_top500 already filled by evaluate_reference_coverage) for the Top-500 Sufficiency Gate.')
    ap.add_argument('--sufficiency-gate-out',type=Path,help='Write Top-500 Sufficiency Gate result; requires --large-cap-references and a single --as-of.')
    ap.add_argument('--gate-v2-out',type=Path,help='Write the combined v2 Promotion Gate (base AND (completeness OR sufficiency)); requires --eligibility-evidence and a single --as-of; uses --exchange-reference/--large-cap-references if given.')
    a=ap.parse_args(); listings=json.loads(a.listings.read_text(encoding='utf-8')); store=RawDatasetStore(a.store)
    dates=[_dt(x) for x in a.as_of]
    r=audit(store,listings,dates[0],a.chart_range) if len(dates)==1 else audit_many(store,listings,dates,a.chart_range); s=json.dumps(r,indent=2)
    if a.out: a.out.write_text(s+'\n',encoding='utf-8')
    if a.plan_out:
        a.plan_out.write_text(json.dumps(build_ingestion_plan(store,listings,a.chart_range),indent=2)+'\n',encoding='utf-8')
    if a.gap_plan_out:
        a.gap_plan_out.write_text(json.dumps(build_pit_gap_plan(store,listings,dates,a.chart_range),indent=2)+'\n',encoding='utf-8')
    completeness_gate = sufficiency_gate = None
    if a.exchange_reference:
        exref = json.loads(a.exchange_reference.read_text(encoding='utf-8'))
        completeness_gate = build_universe_completeness_gate(r, exref)
        if a.completeness_gate_out:
            a.completeness_gate_out.write_text(json.dumps(completeness_gate,indent=2)+'\n',encoding='utf-8')
    if a.large_cap_references:
        refs = json.loads(a.large_cap_references.read_text(encoding='utf-8'))
        sufficiency_gate = build_top500_sufficiency_gate(r, refs)
        if a.sufficiency_gate_out:
            a.sufficiency_gate_out.write_text(json.dumps(sufficiency_gate,indent=2)+'\n',encoding='utf-8')
    if a.gate_out:
        if not a.eligibility_evidence:
            ap.error('--gate-out requires --eligibility-evidence')
        if len(dates)!=1:
            ap.error('--gate-out currently requires exactly one --as-of')
        ev=json.loads(a.eligibility_evidence.read_text(encoding='utf-8'))
        gate=build_official_promotion_gate(r,ev)
        a.gate_out.write_text(json.dumps(gate,indent=2)+'\n',encoding='utf-8')
    if a.gate_v2_out:
        if not a.eligibility_evidence:
            ap.error('--gate-v2-out requires --eligibility-evidence')
        if len(dates)!=1:
            ap.error('--gate-v2-out currently requires exactly one --as-of')
        ev=json.loads(a.eligibility_evidence.read_text(encoding='utf-8'))
        gate2=build_promotion_gate_v2(r,ev,completeness_gate,sufficiency_gate)
        a.gate_v2_out.write_text(json.dumps(gate2,indent=2)+'\n',encoding='utf-8')
    print(s)
if __name__=='__main__': main()
