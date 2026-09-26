"""NPORT_REPORTED_VALUE price exception (user decision 2026-09-26, option 2) — ONLY for the issuers listed in
reports/gate_evidence/nport_price_exception_<as_of>.json (PINC, WOLF). Never extended automatically.

Price = valUSD / balance of the issuer's common-equity holding in the SEC Form NPORT-P already used as the Russell 1000
superset reference (report date = as_of). It is the fund's reported valuation on the report date (2024-12-31), NOT a
market close: every other issuer uses its last close on/before as_of (2024-12-30 session). The type is recorded as
NPORT_REPORTED_VALUE and never mixed with Yahoo/Tiingo closes.

Identity must be deterministic:
  (1) the holding's name resolves to the CIK in the reference (member_names), exactly one EC holding for that CIK;
  (2) the holding's CUSIP appears in an SEC ownership filing (Schedule 13G/13D) whose subject company is that CIK,
      filed on or before as_of (artifact sec_filing_doc:<CIK>:<accn>);
  (3) balance units NS (shares), currency USD, balance > 0 and valUSD > 0.
Output: reports/gate_evidence/nport_reported_prices_<as_of>.json (raw strings, formula, identity evidence). The gate chain
recomputes the price from the stored N-PORT XML and re-checks the CUSIP attestation before using it.

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/nport_reported_prices.py --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_submissions_merged  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"
OWNERSHIP_FORMS = ("SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A", "SCHEDULE 13D", "SCHEDULE 13D/A")
PRICE_TYPE = "NPORT_REPORTED_VALUE"
MAX_OWNERSHIP_DOCS = 3


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":")[-1]


def raw_holdings(xml_bytes: bytes) -> list[dict]:
    """Every invstOrSec with the raw text of the fields the price and identity need (strings kept verbatim)."""
    out = []
    for e in ET.fromstring(xml_bytes).iter():
        if _local(e.tag) != "invstOrSec":
            continue
        h = {"name": None, "lei": None, "title": None, "cusip": None, "isin": None, "ticker": None, "balance": None,
             "units": None, "cur_cd": None, "val_usd": None, "asset_cat": None, "issuer_cat": None, "country": None,
             "fair_val_level": None}
        for c in e:
            n, t = _local(c.tag), (c.text or "").strip()
            key = {"name": "name", "lei": "lei", "title": "title", "cusip": "cusip", "balance": "balance", "units": "units",
                   "curCd": "cur_cd", "valUSD": "val_usd", "assetCat": "asset_cat", "issuerCat": "issuer_cat",
                   "invCountry": "country", "fairValLevel": "fair_val_level"}.get(n)
            if key:
                h[key] = t
            elif n == "identifiers":
                for i in c:
                    if _local(i.tag) == "isin":
                        h["isin"] = i.get("value")
                    elif _local(i.tag) == "ticker":
                        h["ticker"] = i.get("value")
        out.append(h)
    return out


def holding_for(holdings: list[dict], names: list[str]) -> tuple[dict | None, str]:
    """The single common-equity holding whose name is one of the reference names of the CIK."""
    hits = [h for h in holdings if h["name"] in set(names) and h["asset_cat"] == "EC"]
    if len(hits) != 1:
        return None, f"EC_HOLDINGS_FOR_CIK_{len(hits)}"
    return hits[0], "UNIQUE"


def reported_price(h: dict) -> tuple[float | None, str]:
    """valUSD / balance for a share-denominated USD holding; (None, reason) otherwise."""
    if h.get("units") != "NS":
        return None, f"UNITS_NOT_SHARES_{h.get('units')}"
    if h.get("cur_cd") not in (None, "", "USD"):
        return None, f"CURRENCY_{h.get('cur_cd')}"
    try:
        bal, val = float(h["balance"]), float(h["val_usd"])
    except (TypeError, ValueError):
        return None, "NON_NUMERIC"
    if bal <= 0 or val <= 0:
        return None, "NON_POSITIVE"
    return val / bal, "OK"


def cusip_pattern(cusip: str) -> re.Pattern:
    """CUSIP as printed in ownership filings, spaces allowed between characters ('74051N 10 2')."""
    return re.compile(r"\s*".join(re.escape(ch) for ch in cusip), re.I)


def cusip_attested(text: str, cusip: str) -> str | None:
    m = cusip_pattern(cusip).search(text or "")
    return text[max(0, m.start() - 80):m.end() + 40] if m else None


def ownership_filings(submissions: dict, as_of: datetime) -> list[dict]:
    rec = (submissions.get("filings") or {}).get("recent") or {}
    rows = []
    for i, f in enumerate(rec.get("form") or []):
        try:
            filed, accn, doc = str(rec["filingDate"][i]), str(rec["accessionNumber"][i]), str(rec["primaryDocument"][i] or "")
        except (KeyError, IndexError):
            continue
        if f in OWNERSHIP_FORMS and filed <= as_of.date().isoformat() and doc:
            rows.append({"form": f, "filed": filed, "accn": accn, "primary_document": doc})
    return sorted(rows, key=lambda r: r["filed"], reverse=True)[:MAX_OWNERSHIP_DOCS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("_npr_frd", ROOT / "tools" / "fetch_real_data.py")
    frd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frd)
    frc_spec = importlib.util.spec_from_file_location("_npr_frc", ROOT / "tools" / "fetch_class_rights_evidence.py")
    frc = importlib.util.module_from_spec(frc_spec)
    frc_spec.loader.exec_module(frc)
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    exc_path = GE / f"nport_price_exception_{a.as_of}.json"
    if not exc_path.exists():  # the exception is per as_of and user-approved; none for this date -> nothing to do
        print(json.dumps({"status": "NO_EXCEPTION_FOR_AS_OF", "as_of": a.as_of}))
        return
    exc = json.loads(exc_path.read_text(encoding="utf-8"))
    ref = json.loads((GE / f"russell1000_nport_{a.as_of}.json").read_text(encoding="utf-8"))
    accn = ref["source"].split("NPORT-P ")[1].split(" ")[0]
    nid = f"nport_xml:{accn}"
    holdings = raw_holdings(store.get_bytes(nid)) if store.has(nid) else []
    log: list[dict] = []
    out = {}
    for sym, cik in exc["issuers"].items():
        names = ref["member_names"].get(cik) or []
        h, how = holding_for(holdings, names)
        rec = {"cik": cik, "reference_names": names, "holding_match": how, "status": "NOT_DETERMINED", "failures": []}
        if h is None:
            rec["failures"].append(how)
            out[sym] = rec
            continue
        px, why = reported_price(h)
        rec.update({"holding_raw": h, "price": px, "price_check": why,
                    "formula": f"valUSD {h['val_usd']} / balance {h['balance']} ({h['units']})"})
        if px is None:
            rec["failures"].append(why)
        sub = load_submissions_merged(store, cik)[0] or {}
        att = []
        for f in ownership_filings(sub, d):
            aid = f"sec_filing_doc:{cik}:{f['accn']}"
            frd._fetch_one(store, aid, ARCHIVE_URL.format(cik=int(cik), nodash=f["accn"].replace("-", ""), doc=f["primary_document"]),
                           "SEC_FILING_DOCUMENT", frd.UA, log, False)
            frd._throttle(log, 0.15)
            snip = cusip_attested(frc.html_text(store.get_bytes(aid)), h["cusip"] or "") if store.has(aid) and h.get("cusip") else None
            att.append({**f, "artifact_id": aid, "cusip_found": bool(snip), "snippet": snip})
        rec["cusip_attestation"] = att
        if not any(x["cusip_found"] for x in att):
            rec["failures"].append("CUSIP_NOT_ATTESTED_BY_OWNERSHIP_FILING_ON_OR_BEFORE_AS_OF")
        if not rec["failures"]:
            rec["status"] = "IDENTITY_AND_PRICE_VERIFIED"
        out[sym] = rec
    doc = {"kind": "NPORT_REPORTED_PRICES", "as_of": a.as_of, "price_type": PRICE_TYPE, "source_accession": accn,
           "source_artifact": nid, "valuation_date": ref.get("as_of", "")[:10], "source_filed": ref.get("source_vintage"),
           "basis_note": ("Fund-reported fair value per share on the N-PORT report date (2024-12-31), filed after as_of; "
                          "all other issuers use their last market close on/before as_of (2024-12-30 session). "
                          "Applies only to the issuers in nport_price_exception_<as_of>.json."),
           "issuers": out, "log": log}
    (GE / f"nport_reported_prices_{a.as_of}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    frd.write_store_index(store)
    print(json.dumps({s: (v["status"], v.get("price"), v["failures"]) for s, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
