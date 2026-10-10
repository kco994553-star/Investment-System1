"""Independent test generation for GSQ-010; no captured price payload is read.

Session fundamentals reuse the established synthetic catalog. Identifiers and
quote inputs are generated here and never derived from archived market values.
"""
from dataclasses import replace
import json


def session_inputs(monkeypatch, tmp_path):
    from investment_system.qgv import us_live
    from investment_system.providers.catalog import iter_official_raw

    source = [raw for raw in iter_official_raw() if raw.company_id in us_live.US_LISTINGS]
    identifiers = {raw.company_id: f"cleanup_case_{i:02d}" for i, raw in enumerate(source, 1)}
    rows = [replace(raw, company_id=identifiers[raw.company_id], stamp=replace(
        raw.stamp, source_reference="independent-cleanup-test", synthetic=True)) for raw in source]
    listings = {cid: {"yahoo": cid.upper(), "cik": f"SYNTHETIC_{i}", "exchange": "TEST"}
                for i, cid in enumerate(identifiers.values(), 1)}
    weights = {identifiers[old]: us_live.US_WORKING_TARGETS[old] for old in identifiers}
    monkeypatch.setattr(us_live, "iter_official_raw", lambda *args, **kwargs: rows)
    monkeypatch.setattr(us_live, "US_LISTINGS", listings)
    monkeypatch.setattr(us_live, "US_WORKING_TARGETS", weights)
    monkeypatch.setenv("INVESTMENT_SYSTEM_REPORTS_DIR", str(tmp_path))
    ids = list(listings)
    # Authored arithmetic sequence; unrelated to any captured input or issuer.
    prices = {cid: {"price": (701 + i * 37) / 8, "evidence": "SYNTHETIC_TEST_INPUT"}
              for i, cid in enumerate(ids[:2], 1)}
    return {"prices": prices}, ids


def class_rights_case(store, *, paired=False, partial=False, filed="2024-01-15"):
    """Invented classes, shares, quotes and price for the unchanged verifier."""
    cik, accession = "0000000777", "SYNTHETIC-CLAIM-001"
    aid = f"sec_filing_doc:{cik}:{accession}"
    member = "CommonClassCMember" if paired else "CommonClassBMember"
    quote = (
        "Synthetic Class C Shares, together with the related units, exchange on a one-for-one basis into listed Class A Shares."
        if paired else
        "Synthetic Class B Shares are convertible on a one-for-one basis into one share of listed Class A Shares."
    )
    supports = ["pairing", "exchange_ratio"] if paired else ["conversion_ratio"]
    body = ("<html><p>Independent test preamble.</p><p>" + quote + "</p></html>").encode()
    store.put(aid, body, "synthetic:test", "SEC", "text/html", "independent-test", filed)
    recent = {"form": ["10-Q"], "filingDate": [filed], "accessionNumber": [accession], "primaryDocument": ["synthetic.htm"]}
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": recent}}).encode(),
              "synthetic:test", "SEC", "application/json", "independent-test", filed)
    price = 31 / 4
    classes = [{"member": "CommonClassAMember", "shares": 19, "price": price},
               {"member": member, "shares": 23, "price": None}]
    if partial:
        classes.append({"member": "CommonClassDMember", "shares": 29, "price": None})
    override = {"mcap": classes[0]["shares"] * price, "status": "COVER_CLASS_SUM_LOWER_BOUND", "classes": classes}
    det = {"symbol": "SYNTHETIC_RIGHTS", "listed_member": "CommonClassAMember", "classes": {
        member: {"basis": "PAIRED_UNITS_EXCHANGEABLE_INTO_LISTED" if paired else "CONVERTIBLE_INTO_LISTED",
                 "ratio": 1, "citations": [{"artifact_id": aid, "accession": accession,
                    "filed": filed, "quote": quote, "supports": supports}]}}}
    return cik, override, det, body
