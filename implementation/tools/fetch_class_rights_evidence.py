"""Economic rights of UNLISTED share classes, from SEC filings available at as_of (no network in the chain).

For every issuer the gate chain left as an undetermined cover-page LOWER BOUND (lower_bound_issuers_outside_top500),
fetch the primary document of the latest 10-K and of the latest 10-Q filed on or before --as-of
(artifact sec_filing_doc:<CIK10>:<accession>) and extract verbatim passages that mention an unlisted class together
with conversion / exchange / economic-rights wording, plus unit / noncontrolling-interest facts of the stored
cover XBRL instance. Output: reports/gate_evidence/class_rights_passages_<as_of>.json, the material a reviewer
uses to write class_economics_<as_of>.json (determinations with verbatim quotes that the chain re-verifies).

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/fetch_class_rights_evidence.py --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import html
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

ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{doc}"
GE = ROOT / "reports" / "gate_evidence"
RIGHTS_WORDS = re.compile(r"exchang|convert|conver|economic|dividend|one-for-one|one for one|redeem|redemption|"
                          r"units?\b|vote|voting|liquidat|paired|cancel", re.I)
FACT_WORDS = re.compile(r"Unit|NoncontrollingInterest|Ownership|Exchang|Conver", re.I)
MAX_PASSAGES = 60
PASSAGE_CHARS = 700


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":")[-1]


def doc_id(cik10: str, accn: str) -> str:
    return f"sec_filing_doc:{cik10}:{accn}"


def latest_forms(submissions: dict, as_of: datetime) -> list[dict]:
    """Latest 10-K and latest 10-Q (amendments excluded) filed on or before as_of."""
    rec = (submissions.get("filings") or {}).get("recent") or {}
    cut = as_of.date().isoformat()
    best: dict[str, dict] = {}
    for i, form in enumerate(rec.get("form") or []):
        if form not in ("10-K", "10-Q"):
            continue
        try:
            filed, accn, doc = str(rec["filingDate"][i]), str(rec["accessionNumber"][i]), str(rec["primaryDocument"][i] or "")
        except (KeyError, IndexError):
            continue
        if filed <= cut and doc and (form not in best or filed > best[form]["filed"]):
            best[form] = {"form": form, "filed": filed, "accn": accn, "primary_document": doc}
    return [best[f] for f in ("10-K", "10-Q") if f in best]


def html_text(body: bytes) -> str:
    """Plain text of an (i)XBRL/HTML filing: tags dropped, entities unescaped, whitespace collapsed."""
    t = body.decode("utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t).replace("\xa0", " ")).strip()


def class_phrases(member: str) -> list[str]:
    """Text names of an XBRL class member: CommonClassBMember -> 'Class B common stock' / 'Class B Common Stock'."""
    m = re.fullmatch(r"CommonClass([A-Z])Member", member or "")
    if m:
        return [f"Class {m.group(1)} common stock", f"Class {m.group(1)} Common Stock", f"Class {m.group(1)} Shares",
                f"Class {m.group(1)} shares"]
    if member == "NonvotingCommonStockMember":
        return ["Nonvoting Class A", "nonvoting Class A", "Nonvoting Common Stock", "nonvoting common stock"]
    words = re.sub(r"Member$", "", member or "")
    return [re.sub(r"(?<!^)(?=[A-Z])", " ", words)]


UNIT_RATIO = re.compile(r"\bunits?\b.*(one[- ]for[- ]one|one-to-one|1:1|equal number|share[- ]for[- ]share)|"
                        r"(one[- ]for[- ]one|one-to-one|1:1|share[- ]for[- ]share).*\bunits?\b", re.I)


def passages(text: str, phrases: list[str]) -> list[dict]:
    """Sentences containing one of the class phrases AND rights wording, plus sentences stating an exchange ratio for
    paired units (they often name only the unit, e.g. 'LLC Common Units ... on a one-for-one basis'). Verbatim, with offset."""
    out, seen = [], set()
    for s in re.finditer(r"[^.;]*(?:[.;]|$)", text):
        sent = s.group(0).strip()
        named = any(p in sent for p in phrases) and RIGHTS_WORDS.search(sent)
        if len(sent) < 40 or not (named or UNIT_RATIO.search(sent)):
            continue
        key = sent[:200]
        if key in seen:
            continue
        seen.add(key)
        out.append({"offset": s.start(), "text": sent[:PASSAGE_CHARS]})
        if len(out) >= MAX_PASSAGES:
            break
    return out


def unit_facts(xml_bytes: bytes) -> list[dict]:
    """Unit / noncontrolling-interest facts of an XBRL instance: concept, value, date, dimension members."""
    root = ET.fromstring(xml_bytes)
    ctx = {}
    for c in root.iter():
        if _local(c.tag) != "context":
            continue
        dims, date = [], None
        for e in c.iter():
            n = _local(e.tag)
            if n == "explicitMember":
                dims.append(f"{_local(str(e.get('dimension') or ''))}={_local((e.text or '').strip())}")
            elif n in ("instant", "endDate"):
                date = (e.text or "").strip()
        ctx[str(c.get("id"))] = {"dims": dims, "date": date}
    out = []
    for e in root.iter():
        n = _local(e.tag)
        if e.get("contextRef") is None or not FACT_WORDS.search(n):
            continue
        v = (e.text or "").strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?", v):
            continue
        c = ctx.get(str(e.get("contextRef"))) or {}
        out.append({"concept": n, "value": float(v), "date": c.get("date"), "dims": c.get("dims"), "unit": e.get("unitRef")})
    return out[:400]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--chain", type=Path, help="gate chain evidence (default: gate_chain_<as_of>_real_gha.json)")
    a = ap.parse_args()
    frd = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("_fcr_frd", ROOT / "tools" / "fetch_real_data.py"))
    spec.loader.exec_module(frd)
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    chain_path = a.chain or GE / f"gate_chain_{a.as_of}_real_gha.json"
    if not chain_path.exists():  # first run for this as_of: no lower-bound issuers known yet
        print(json.dumps({"status": "NO_CHAIN_EVIDENCE_FOR_AS_OF", "as_of": a.as_of}))
        return
    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    log: list[dict] = []
    issuers = {}
    for sym in chain.get("lower_bound_issuers_outside_top500") or []:
        ov = (chain.get("cover_overrides") or {}).get(sym) or {}
        src = str(ov.get("source") or "")
        if not src.startswith("xbrl_instance:"):
            continue
        cik = src.split(":")[1]
        unlisted = [c for c in ov.get("classes") or [] if not c.get("price")]
        phrases = sorted({p for c in unlisted for p in class_phrases(c.get("member"))})
        sub = load_submissions_merged(store, cik, d)[0] or {}
        docs = []
        for f in latest_forms(sub, d):
            aid = doc_id(cik, f["accn"])
            frd._fetch_one(store, aid, ARCHIVE_URL.format(cik=int(cik), accn=f["accn"].replace("-", ""), doc=f["primary_document"]),
                           "SEC_FILING_DOCUMENT", frd.UA, log, False)
            frd._throttle(log, 0.15)
            if store.has(aid):
                docs.append({**f, "artifact_id": aid, "passages": passages(html_text(store.get_bytes(aid)), phrases)})
        facts = unit_facts(store.get_bytes(src)) if store.has(src) else []
        issuers[sym] = {"cik": cik, "cover_source": src, "entity_name": sub.get("name"),
                        "classes": ov.get("classes"), "unlisted_members": [c.get("member") for c in unlisted],
                        "phrases": phrases, "documents": docs, "cover_instance_unit_facts": facts}
    path = GE / f"class_rights_passages_{a.as_of}.json"
    # merge: issuers reviewed in earlier runs stay (their determinations cite these passages); this run adds/refreshes
    prev = json.loads(path.read_text(encoding="utf-8")).get("issuers") or {} if path.exists() else {}
    out = {"kind": "CLASS_RIGHTS_PASSAGES", "as_of": a.as_of,
           "note": "Verbatim passages from filings filed on or before as_of; review material, not a determination.",
           "issuers": {**prev, **issuers}}
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    (store.root / f"class_rights_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps({"log": log}, indent=1))
    frd.write_store_index(store)
    print(json.dumps({s: {"docs": [(x["form"], x["filed"], len(x["passages"])) for x in v["documents"]],
                          "facts": len(v["cover_instance_unit_facts"])} for s, v in issuers.items()}, indent=1))


if __name__ == "__main__":
    main()
