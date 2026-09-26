"""Independent dated PIT large-cap reference from SEC N-PORT (Sufficiency path, user decision 2026-09-25).

The iShares Russell 1000 ETF (IWB) reports its full holdings to the SEC on Form NPORT-P; 2024-12-31 is a
fiscal quarter end for the fund, so that report is public. This tool (SEC only, same UA/throttle/resume as
fetch_real_data.py):
  1. reads the registrant's submissions (iShares Trust, name verified) and lists NPORT-P filings whose
     reportDate == as_of,
  2. fetches each filing's small index-headers page until the one whose series name is exactly
     --series-name is found (artifact edgar_index_headers:<accession>),
  3. fetches that filing's primary N-PORT XML (artifact nport:<accession>) and parses equity holdings,
  4. resolves each holding to an SEC CIK by a UNIQUE normalised-name match (current company_tickers titles,
     then cik-lookup-data.txt); ambiguous or unmatched names are reported, never guessed.
Writes reports/gate_evidence/russell1000_nport_<as_of>.json (reference_role SUPERSET_REFERENCE, members =
CIK10 strings) and russell1000_extra_listings_<as_of>.json (members not yet in the pool).

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/fetch_nport_reference.py --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_submissions_merged  # noqa: E402
from investment_system.providers.sec_cover_shares import (  # noqa: E402
    class_symbols, instance_name, pages_needed, parse_cover, pit_filer_status, select_filing)

GE = ROOT / "reports" / "gate_evidence"
REGISTRANT_CIK = "0001100663"  # iShares Trust (verified against the submissions name at run time)
REGISTRANT_NAME_TOKEN = "ISHARES TRUST"
SERIES_NAME = "iShares Russell 1000 ETF"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
INDEX_HEADERS_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{accn}-index-headers.html"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"
CIK_LOOKUP_URL = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_fnr_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def nport_filings_for(submissions: dict, as_of: str) -> list[dict]:
    rec = (submissions.get("filings") or {}).get("recent") or {}
    out = []
    for i, form in enumerate(rec.get("form") or []):
        if form != "NPORT-P":
            continue
        try:
            if str(rec["reportDate"][i]) != as_of:
                continue
            out.append({"accn": str(rec["accessionNumber"][i]), "filed": str(rec["filingDate"][i]),
                        "doc": str((rec.get("primaryDocument") or [""] * (i + 1))[i] or "primary_doc.xml")})
        except (KeyError, IndexError):
            continue
    return out


def raw_xml_doc(primary_document: str) -> str:
    """submissions list NPORT-P primaryDocument as 'xslFormNPORT-P_X01/primary_doc.xml', which EDGAR serves as an
    XSL-rendered HTML page; the raw XML is the same file name without the xsl* directory."""
    parts = primary_document.split("/")
    return "/".join(p for p in parts if not p.lower().startswith("xsl")) or primary_document


def series_names(index_headers: bytes) -> list[str]:
    """Series names in an EDGAR index-headers page (SGML header shown as text, tags possibly HTML-escaped)."""
    text = index_headers.decode("utf-8", errors="replace").replace("&lt;", "<").replace("&gt;", ">")
    return [m.strip() for m in re.findall(r"<SERIES-NAME>([^\n<]+)", text) if m.strip()]


def parse_nport(xml_bytes: bytes) -> dict:
    """{'report_date', 'series_name', 'holdings': [{name, cusip, isin, asset_cat, country, value}]}."""
    root = ET.fromstring(xml_bytes)
    out = {"report_date": None, "series_name": None, "holdings": []}
    for e in root.iter():
        n = _local(e.tag)
        if n == "repPdDate" and out["report_date"] is None:
            out["report_date"] = (e.text or "").strip()
        elif n == "seriesName" and out["series_name"] is None:
            out["series_name"] = (e.text or "").strip()
        elif n == "invstOrSec":
            h = {"name": None, "cusip": None, "isin": None, "asset_cat": None, "country": None, "value": None}
            for c in e.iter():
                cn = _local(c.tag)
                if cn == "name" and h["name"] is None:
                    h["name"] = (c.text or "").strip()
                elif cn == "cusip":
                    h["cusip"] = (c.text or "").strip()
                elif cn == "isin":
                    h["isin"] = c.get("value") or (c.text or "").strip()
                elif cn == "assetCat":
                    h["asset_cat"] = (c.text or "").strip()
                elif cn == "invCountry":
                    h["country"] = (c.text or "").strip()
                elif cn == "valUSD":
                    try:
                        h["value"] = float(c.text)
                    except (TypeError, ValueError):
                        pass
            out["holdings"].append(h)
    return out


SUFFIXES = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "PLC", "LLC", "LP", "HOLDINGS", "HOLDING",
            "GROUP", "THE", "SA", "NV", "N", "V", "AG", "CLASS", "A", "B", "C", "INCORPORATED", "INCORPORATION", "COM",
            "NEW", "DEL", "REIT", "PUBLIC", "LIMITED", "NATIONAL", "ASSOCIATION", "AND"}


def norm_name(n: str, join_dotted: bool = False) -> str:
    """Order-insensitive token key. SEC titles carry state tags ('/MA/', '/DE/', 'INC/CA', 'INC /NY') and reorder
    names ('BERKLEY W R CORP'); fund reports spell out forms ('PUBLIC LIMITED COMPANY'). join_dotted collapses
    dotted acronyms ('U.S.A.' -> 'USA') for a second key."""
    s = str(n or "").upper().replace("&", " AND ")
    s = re.sub(r"\s*[/\\]\s*[A-Z]{1,4}\s*[/\\]?\s*$", " ", s)   # trailing state tag ('/CA', '\\DE\\')
    s = re.sub(r"[/\\][A-Z ]{1,4}[/\\]", " ", s)                      # embedded state/country tags
    s = re.sub(r"['\u2019`]", "", s)                          # LOWE'S -> LOWES
    if join_dotted:
        s = re.sub(r"\b([A-Z])\.(?=[A-Z]\.)", r"\1", s).replace(".", "")
    words = re.sub(r"[^A-Z0-9 ]", " ", s).split()
    return " ".join(sorted(w for w in words if w not in SUFFIXES))


def name_index(store: RawDatasetStore) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str]]:
    """(current title -> CIKs, historical name -> CIKs, CIK -> current ticker)."""
    cur, tick = {}, {}
    if store.has("sec_tickers"):
        for row in json.loads(store.get_bytes("sec_tickers")).values():
            c = str(row.get("cik_str")).zfill(10)
            for k in {norm_name(row.get("title")), norm_name(row.get("title"), True)}:
                cur.setdefault(k, set()).add(c)
            tick.setdefault(c, str(row.get("ticker") or "").upper().replace(".", "-"))
    hist = {}
    if store.has("sec_cik_lookup"):
        for ln in store.get_bytes("sec_cik_lookup").decode("latin-1", errors="replace").splitlines():
            parts = ln.rsplit(":", 2)
            if len(parts) >= 3 and parts[1].strip().isdigit():
                for k in {norm_name(parts[0]), norm_name(parts[0], True)}:
                    hist.setdefault(k, set()).add(parts[1].strip().zfill(10))
    return cur, hist, tick


def resolve(holdings: list[dict], cur: dict, hist: dict, pool_ciks: set[str] | None = None) -> tuple[dict[str, dict], list[dict]]:
    """CIK10 -> {names, cusips}; unresolved holdings. Share classes of one issuer collapse to one CIK.
    Ties are broken only by independent evidence: exactly one candidate is a current registrant / already in the pool."""
    members, unresolved = {}, []
    current_ciks = {c for cs in cur.values() for c in cs}
    pool_ciks = pool_ciks or set()
    for h in holdings:
        c, method = set(), "SEC_TICKERS_TITLE"
        for k in (norm_name(h["name"]), norm_name(h["name"], True)):
            c = cur.get(k) or set()
            if len(c) > 1 and len(c & pool_ciks) == 1:
                c, method = c & pool_ciks, "SEC_TICKERS_TITLE_UNIQUE_IN_POOL"
            if len(c) == 1:
                break
        k = norm_name(h["name"])
        if len(c) != 1:
            # both keys: 'SKECHERS U.S.A., INC.' only matches its historical title with dotted acronyms joined
            c, method = (hist.get(k) or set()) | (hist.get(norm_name(h["name"], True)) or set()), "SEC_CIK_LOOKUP"
            if len(c) > 1:
                # several historical entities share the name: accept only if exactly one is a current SEC registrant
                active = {x for x in c if x in current_ciks}
                if len(active) == 1:
                    c, method = active, "SEC_CIK_LOOKUP_UNIQUE_ACTIVE"
                elif len(c & pool_ciks) == 1:
                    c, method = c & pool_ciks, "SEC_CIK_LOOKUP_UNIQUE_IN_POOL"
        if len(c) != 1:
            unresolved.append({**h, "name_matches": len(c), "candidates": sorted(c)[:8]})
            continue
        cik = next(iter(c))
        m = members.setdefault(cik, {"names": [], "cusips": [], "method": method, "methods": []})
        m["names"].append(h["name"])
        m["cusips"].append(h["cusip"])
        m["methods"].append(method)
    return split_collisions(members, unresolved, holdings, cur, hist)


METHOD_RANK = ("SEC_TICKERS_TITLE", "SEC_TICKERS_TITLE_UNIQUE_IN_POOL", "SEC_CIK_LOOKUP", "SEC_CIK_LOOKUP_UNIQUE_ACTIVE",
               "SEC_CIK_LOOKUP_UNIQUE_IN_POOL")


def issuer_prefix(cusip) -> str:
    """CUSIP issuer number (first 6 characters): share classes of one issuer share it (BF-A/BF-B 115637)."""
    return str(cusip or "").strip().upper()[:6]


def split_collisions(members: dict, unresolved: list, holdings: list, cur: dict, hist: dict) -> tuple[dict, list]:
    """One CIK must not absorb holdings of DIFFERENT issuers (distinct CUSIP issuer numbers). Run #53 (N-PORT
    cross-check) found 'DUN & BRADSTREET HOLDINGS, INC.' resolved to Moody's CIK and 'F.N.B. CORPORATION' to V.F.'s
    on every as_of -- D&B and F.N.B. were silently missing from the reference and the pool. The issuer group matched
    by the strongest method keeps the CIK (a tie keeps none); every other group retries its name without that CIK and
    is resolved only if exactly one candidate remains, else it is unresolved (fail-closed)."""
    by_name = {h["name"]: h for h in holdings}
    out = {}
    for cik, m in members.items():
        groups = {}
        for n, cu, me in zip(m["names"], m["cusips"], m.get("methods") or [m["method"]] * len(m["names"])):
            groups.setdefault(issuer_prefix(cu) or f"NOCUSIP:{n}", []).append((n, cu, me))
        if len(groups) == 1:
            out[cik] = {k: v for k, v in m.items() if k != "methods"}
            continue
        rank = {g: min(METHOD_RANK.index(me) if me in METHOD_RANK else len(METHOD_RANK) for _, _, me in rows)
                for g, rows in groups.items()}
        best = min(rank.values())
        winners = [g for g, r in rank.items() if r == best]
        keep = winners[0] if len(winners) == 1 else None
        for g, rows in groups.items():
            if g == keep:
                out[cik] = {"names": [r[0] for r in rows], "cusips": [r[1] for r in rows], "method": rows[0][2],
                            "collision_winner_over": sorted(x for x in groups if x != g)}
                continue
            for n, cu, _ in rows:
                c = set()
                for k in (norm_name(n), norm_name(n, True)):
                    c |= (cur.get(k) or set()) | (hist.get(k) or set())
                c.discard(cik)
                if len(c) == 1:
                    alt = next(iter(c))
                    mm = out.setdefault(alt, members.get(alt) and {k: v for k, v in members[alt].items() if k != "methods"}
                                        or {"names": [], "cusips": [], "method": "COLLISION_RETRY_SEC_CIK_LOOKUP"})
                    mm["names"].append(n)
                    mm["cusips"].append(cu)
                    mm.setdefault("collision_retry_from", []).append(cik)
                else:
                    unresolved.append({**by_name.get(n, {"name": n, "cusip": cu}), "name_matches": len(c),
                                       "candidates": sorted(c)[:8], "reason": "CIK_COLLISION_DISTINCT_CUSIP_ISSUERS",
                                       "collided_with": cik})
    return out, unresolved


ATTEST_MAX_DOCS = 10


def name_candidates(name: str, cur: dict, hist: dict) -> set[str]:
    """Every CIK whose current or historical SEC name matches the holding name (both keys); a tracking-group suffix
    ('LIBERTY MEDIA CORP - FORMULA ONE GROUP') is also tried without the suffix. Candidates only -- identity is decided
    by CUSIP attestation."""
    names = [name] + ([name.split(" - ", 1)[0]] if " - " in name else [])
    out = set()
    for n in names:
        for k in (norm_name(n), norm_name(n, True)):
            out |= (cur.get(k) or set()) | (hist.get(k) or set())
    return out


def attest_by_cusip(store: RawDatasetStore, get, candidates: list[str], cusip: str, as_of: datetime, npr, frc) -> dict:
    """The candidate CIK whose OWN ownership filings (Schedule 13G/13D on it as subject company, filed <= as_of) print
    the holding's CUSIP. Exactly one attested candidate -> identity; none or several -> unresolved (fail-closed)."""
    hits, checked = [], []
    for c in candidates[:8]:
        get(f"submissions:{c}", SUBMISSIONS_URL.format(cik=c), "SEC_SUBMISSIONS")
        sub = load_submissions_merged(store, c)[0] or {}
        # a tracking-stock issuer files one 13G per group/class: read up to 10 of its latest ownership filings
        for f in npr.ownership_filings(sub, as_of, ATTEST_MAX_DOCS):
            aid = f"sec_filing_doc:{c}:{f['accn']}"
            get(aid, npr.ARCHIVE_URL.format(cik=int(c), nodash=f["accn"].replace("-", ""), doc=f["primary_document"]),
                "SEC_FILING_DOCUMENT")
            snip = npr.cusip_attested(frc.html_text(store.get_bytes(aid)), cusip) if store.has(aid) else None
            checked.append({"cik": c, "artifact_id": aid, "filed": f["filed"], "form": f["form"], "cusip_found": bool(snip)})
            if snip:
                hits.append({"cik": c, "artifact_id": aid, "filed": f["filed"], "snippet": snip})
                break
    ciks = sorted({h["cik"] for h in hits})
    if len(ciks) > 1:
        # several entities print the CUSIP (e.g. a predecessor of the same name): only a registrant filing
        # 10-K/10-Q around as_of can be the listed issuer at as_of; exactly one such -> identity
        pit = [c for c in ciks if pit_registrant(store, c, as_of)]
        if len(pit) == 1:
            return {"cik": pit[0], "attested": hits, "checked": checked, "status": "UNIQUE_PIT_REGISTRANT_AMONG_ATTESTED",
                    "attested_ciks": ciks}
    return {"cik": ciks[0] if len(ciks) == 1 else None, "attested": hits, "checked": checked,
            "status": "UNIQUE" if len(ciks) == 1 else f"ATTESTED_{len(ciks)}"}


def pit_registrant(store: RawDatasetStore, cik: str, as_of: datetime, lookback_days: int = 400) -> bool:
    """Domestic filer at as_of with a 10-K/10-Q filed within lookback_days before as_of (from stored submissions)."""
    sub, complete = load_submissions_merged(store, cik, as_of)
    if not sub or pit_filer_status(sub, as_of, complete) != "DOMESTIC":
        return False
    f = select_filing(sub, as_of)
    return bool(f) and (as_of.date() - datetime.fromisoformat(f["filed"]).date()).days <= lookback_days


def as_of_symbol(store: RawDatasetStore, cik: str, as_of: datetime) -> str | None:
    """Ticker the issuer registered AT as_of: dei:TradingSymbol on the latest 10-K/10-Q cover filed <= as_of."""
    f = select_filing(load_submissions_merged(store, cik, as_of)[0] or {}, as_of)
    aid = f"xbrl_instance:{cik}:{f['accn']}" if f else None
    if not aid or not store.has(aid):
        return None
    try:
        syms = [s for s in class_symbols(parse_cover(store.get_bytes(aid))).values() if s and " " not in s]
    except Exception:  # noqa: BLE001
        return None
    return sorted(syms, key=len)[0].replace(".", "-") if syms else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--series-name", default=SERIES_NAME)
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=GE / "missing_large_cap_priority_plan_2024-12-31.json")
    a = ap.parse_args()
    frd = _load("fetch_real_data")
    chain = _load("run_top500_gate_chain")
    store = RawDatasetStore(a.store)
    log: list[dict] = []
    get = lambda aid, url, kind: (frd._fetch_one(store, aid, url, kind, frd.UA, log, False), frd._throttle(log, 0.15))  # noqa: E731
    get(f"submissions:{REGISTRANT_CIK}", SUBMISSIONS_URL.format(cik=REGISTRANT_CIK), "SEC_SUBMISSIONS")
    get("sec_cik_lookup", CIK_LOOKUP_URL, "SEC_CIK_LOOKUP")
    report = {"kind": "NPORT_REFERENCE_RUN", "as_of": a.as_of, "series_name": a.series_name}
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    sub = load_submissions_merged(store, REGISTRANT_CIK)[0] or {}
    if REGISTRANT_NAME_TOKEN not in str(sub.get("name") or "").upper():
        report["status"] = "REGISTRANT_NOT_VERIFIED"
    else:
        # N-PORT reports for a period are filed ~60 days later; older submissions pages may hold them
        page_mod = _load("fetch_cover_xbrl")
        for f in (sub.get("filings") or {}).get("files") or []:
            if str(f.get("filingTo") or "9999") >= a.as_of:
                get(f"submissions_page:{f['name']}", page_mod.SUBMISSIONS_PAGE_URL.format(name=f["name"]), "SEC_SUBMISSIONS_PAGE")
        sub = load_submissions_merged(store, REGISTRANT_CIK)[0] or {}
        cands = nport_filings_for(sub, a.as_of)
        report["n_candidate_filings"] = len(cands)
        chosen = None
        for f in cands:
            nodash = f["accn"].replace("-", "")
            hid = f"edgar_index_headers:{f['accn']}"
            get(hid, INDEX_HEADERS_URL.format(cik=int(REGISTRANT_CIK), nodash=nodash, accn=f["accn"]), "SEC_INDEX_HEADERS")
            if store.has(hid) and any(s.lower() == a.series_name.lower() for s in series_names(store.get_bytes(hid))):
                chosen = f
                break
        if chosen is None:
            report["status"] = "SERIES_FILING_NOT_FOUND"
        else:
            nid = f"nport_xml:{chosen['accn']}"
            doc_url = DOC_URL.format(cik=int(REGISTRANT_CIK), nodash=chosen["accn"].replace("-", ""), doc=raw_xml_doc(chosen["doc"]))
            get(nid, doc_url, "SEC_NPORT_XML")
            try:
                doc = parse_nport(store.get_bytes(nid)) if store.has(nid) else {"holdings": []}
            except ET.ParseError as e:
                doc = {"holdings": [], "parse_error": str(e)}
                report["parse_error"] = str(e)
            eq = [h for h in doc["holdings"] if h["asset_cat"] == "EC"]
            report.update({"filing": chosen, "nport_report_date": doc.get("report_date"), "nport_series": doc.get("series_name"),
                           "n_holdings": len(doc["holdings"]), "n_equity_common": len(eq)})
            if doc.get("report_date") != a.as_of or len(eq) < 900:
                report["status"] = "REJECTED_REPORT_DATE_OR_TOO_FEW_HOLDINGS"
            else:
                cur, hist, tick = name_index(store)
                rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
                rows, _ = chain.extend_listings(store, rd(a.listings) or {}, rd(a.plan))
                pool_ciks = {str(m.get("cik") or "").zfill(10) for m in rows.values()}
                members, unresolved = resolve(eq, cur, hist, pool_ciks)
                # (0) unresolved equity holdings (ambiguous name, name not found, dead namesake, collision loser):
                # identity by CUSIP attestation in the candidate issuer's own 13G/13D filed <= as_of
                npr, frc = _load("nport_reported_prices"), _load("fetch_class_rights_evidence")
                still0, attestations = [], {}
                for u in unresolved:
                    cu = str(u.get("cusip") or "")
                    if not cu or "ESC" in cu.upper()[3:9]:
                        still0.append(u)
                        continue
                    cands = sorted(set(u.get("candidates") or []) | name_candidates(u["name"], cur, hist))
                    att = attest_by_cusip(store, get, cands, cu, d, npr, frc)
                    attestations[u["name"] + "|" + cu] = {"candidates": cands, **att}
                    if att["cik"] and pit_registrant(store, att["cik"], d):
                        m = members.setdefault(att["cik"], {"names": [], "cusips": [], "method": "CUSIP_ATTESTED_OWNERSHIP_FILING"})
                        m["names"].append(u["name"])
                        m["cusips"].append(cu)
                    else:
                        still0.append({**u, "cusip_attestation": att["status"], "candidates": cands[:8]})
                unresolved = still0
                report["cusip_attestations"] = attestations
                # (1) name collisions: accept the unique candidate that was a domestic SEC registrant at as_of
                cover_mod = _load("fetch_cover_xbrl")
                still = []
                for u in unresolved:
                    cands = u.get("candidates") or []
                    for c in cands:
                        get(f"submissions:{c}", SUBMISSIONS_URL.format(cik=c), "SEC_SUBMISSIONS")
                    ok = [c for c in cands if pit_registrant(store, c, d)]
                    if 1 < len(cands) and len(ok) == 1:
                        m = members.setdefault(ok[0], {"names": [], "cusips": [], "method": "SEC_CIK_LOOKUP_UNIQUE_PIT_REGISTRANT"})
                        m["names"].append(u["name"])
                        m["cusips"].append(u.get("cusip"))
                    else:
                        still.append({**u, "pit_registrant_candidates": ok})
                unresolved = still
                # a unique HISTORICAL name match can be a dead namesake (e.g. an old 'U.S. BANCORP' entity):
                # accept it only if that CIK was a domestic SEC registrant filing 10-K/10-Q around as_of
                for c in [c for c, v in members.items() if v["method"].startswith(("SEC_CIK_LOOKUP", "COLLISION_RETRY"))]:
                    get(f"submissions:{c}", SUBMISSIONS_URL.format(cik=c), "SEC_SUBMISSIONS")
                    if not pit_registrant(store, c, d):
                        v = members.pop(c)
                        unresolved.append({"name": v["names"][0], "cusip": v["cusips"][0], "name_matches": 1,
                                           "reason": "HISTORICAL_NAME_MATCH_NOT_A_PIT_REGISTRANT", "candidates": [c]})
                # (2) members not in the pool without a current ticker: ticker AT as_of from the cover page
                as_of_ticker = {}
                for c in sorted(c for c in members if c not in pool_ciks and not tick.get(c)):
                    get(f"submissions:{c}", SUBMISSIONS_URL.format(cik=c), "SEC_SUBMISSIONS")
                    for name in pages_needed(load_submissions_merged(store, c)[0] or {}, d):
                        get(f"submissions_page:{name}", cover_mod.SUBMISSIONS_PAGE_URL.format(name=name), "SEC_SUBMISSIONS_PAGE")
                    f = select_filing(load_submissions_merged(store, c, d)[0] or {}, d)
                    if f:
                        get(f"xbrl_instance:{c}:{f['accn']}", cover_mod.ARCHIVE_URL.format(
                            cik=int(c), accn=f["accn"].replace("-", ""), doc=instance_name(f["primary_document"])), "SEC_XBRL_INSTANCE")
                    sym = as_of_symbol(store, c, d)
                    if sym:
                        as_of_ticker[c] = sym
                extra = {f"r1000:{c}": {"yahoo": tick.get(c) or as_of_ticker[c], "cik": c, "cik_method": v["method"],
                                        "symbol_basis": "SEC_TICKERS_CURRENT" if tick.get(c) else "COVER_TRADING_SYMBOL_AT_AS_OF",
                                        "reference_name": v["names"][0]}
                         for c, v in members.items() if c not in pool_ciks and (tick.get(c) or as_of_ticker.get(c))}
                no_ticker = sorted(c for c in members if c not in pool_ciks and not tick.get(c) and not as_of_ticker.get(c))
                ref = {"name": "RUSSELL1000_IWB_NPORT", "kind": "SEC_NPORT_FUND_HOLDINGS",
                       "source": f"SEC Form NPORT-P {chosen['accn']} ({a.series_name}), report date {a.as_of}",
                       "source_url": doc_url,
                       "source_vintage": chosen["filed"], "as_of": a.as_of + "T00:00:00+00:00",
                       "membership_basis": "DATED_FUND_HOLDINGS", "reference_role": "SUPERSET_REFERENCE", "survivorship_risk": False,
                       "member_id_type": "CIK10", "members": sorted(members), "member_names": {c: v["names"] for c, v in members.items()},
                       "member_cusips": {c: v["cusips"] for c, v in members.items()},
                       "member_methods": {c: v["method"] for c, v in members.items()},
                       "cusip_attestations": report.get("cusip_attestations") or {},
                       "unresolved_holdings": unresolved, "members_not_in_pool_without_current_ticker": no_ticker,
                       "note": ("Russell 1000 fund holdings as reported to the SEC for the as_of date (filed after as_of: a dated "
                                "historical record, used for validation, not as information available at as_of).")}
                (GE / f"russell1000_nport_{a.as_of}.json").write_text(json.dumps(ref, indent=2) + "\n", encoding="utf-8")
                (GE / f"russell1000_extra_listings_{a.as_of}.json").write_text(json.dumps(extra, indent=2) + "\n", encoding="utf-8")
                report.update({"status": "OK", "n_members_cik": len(members), "n_unresolved": len(unresolved),
                               "n_as_of_ticker_from_cover": len(as_of_ticker),
                               "n_extra": len(extra), "n_not_in_pool_without_current_ticker": len(no_ticker)})
    report["log"] = log
    (store.root / f"nport_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    print(json.dumps({k: v for k, v in report.items() if k != "log"}, indent=2)[:4000])


if __name__ == "__main__":
    main()
