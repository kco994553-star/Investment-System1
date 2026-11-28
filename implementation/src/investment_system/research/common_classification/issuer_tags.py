"""Offline issuer filters for the pinned SEC market snapshot."""
from collections import Counter
import csv
from pathlib import Path

COUNTRY_VERSION = "edgar-countries/2"
TAG_KEYS = ("incorporation_code", "business_address_code", "recent_reporting_form")
FORM_FAMILIES = {form + suffix: family
                 for family, forms in (("DOMESTIC_FORM", ("10-K", "10-Q", "8-K")),
                                       ("FOREIGN_FORM", ("20-F", "40-F", "6-K")))
                 for form in forms for suffix in ("", "/A")}


def validate_tags(row):
    if any(k not in row or (row[k] is not None and
           (not isinstance(row[k], str) or not row[k].strip())) for k in TAG_KEYS):
        raise ValueError("INVALID_SEC_TAG_FIELDS")
    if row["recent_reporting_form"] is not None and row["recent_reporting_form"] not in FORM_FAMILIES:
        raise ValueError("INVALID_SEC_REPORTING_FORM")


def _place(raw, codes):
    if raw is None:
        return {"raw_code": None, "country_code": None, "country_name_ko": None, "status": "MISSING"}
    code, name = codes.get(raw, (None, None))
    status = "MAPPED" if code else ("SOURCE_UNKNOWN" if raw in codes else "UNMAPPED")
    return {"raw_code": raw, "country_code": code, "country_name_ko": name, "status": status}


def summarize_issuer_tags(rows, issuers):
    """Return private tags by linked CIK and a separately publishable count summary."""
    with Path(__file__).with_name("edgar_countries_v2.csv").open(encoding="utf-8", newline="") as stream:
        codes = {r["edgar_code"]: (r["country_code"] or None, r["country_name_ko"] or None)
                 for r in csv.DictReader(stream)}
    securities = Counter(row["issuer_id"] for row in rows if row["issuer_id"] is not None)
    unlinked = len(rows) - sum(securities.values())
    by_cik = {}
    hq_counts, names, unknown, forms = Counter(), {}, Counter(), Counter()
    if unlinked:
        unknown["UNLINKED"] = unlinked
    comparable_rows = comparable_issuers = different_rows = different_issuers = 0
    for issuer in issuers:
        cik = issuer["cik"]
        if cik not in securities:
            continue
        count = securities[cik]
        incorporation = _place(issuer["incorporation_code"], codes)
        business = _place(issuer["business_address_code"], codes)
        form = issuer["recent_reporting_form"]
        family = FORM_FAMILIES.get(form, "UNKNOWN")
        by_cik[cik] = dict(incorporation=incorporation, business_address=business,
                           recent_reporting_form=form, reporting_type=family)
        forms[family] += 1
        hq = business["country_code"]
        if hq:
            hq_counts[hq] += count
            names[hq] = business["country_name_ko"]
        else:
            unknown[business["status"]] += count
        if hq and incorporation["country_code"]:
            comparable_rows += count
            comparable_issuers += 1
            if hq != incorporation["country_code"]:
                different_rows += count
                different_issuers += 1
    ranking = sorted(hq_counts.items(), key=lambda item: (-item[1], item[0]))
    return by_cik, {
        "country_dictionary_version": COUNTRY_VERSION,
        "business_address_top10": [dict(country_code=c, country_name_ko=names[c], stock_rows=n)
                                   for c, n in ranking[:10]],
        "business_address_other_known_rows": sum(n for _, n in ranking[10:]),
        "business_address_unknown_rows": sum(unknown.values()),
        "business_address_unknown_reasons": dict(unknown),
        "comparable_country_rows": comparable_rows, "different_country_rows": different_rows,
        "comparable_country_issuers": comparable_issuers, "different_country_issuers": different_issuers,
        "reporting_type_issuers": {f: forms[f] for f in ("DOMESTIC_FORM", "FOREIGN_FORM", "UNKNOWN")},
        "master_dr_rows_by_raw_flag": dict(Counter(r["master_dr_flag"] for r in rows)),
    }
