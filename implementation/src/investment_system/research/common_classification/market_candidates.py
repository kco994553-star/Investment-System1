"""Classify an offline SEC delivery against a privately verified market master."""
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
import re
from urllib.parse import urlparse

from .subindustry import distribution, load_dictionary

VENUES = {"NASDAQ": "NAS", "NYSE": "NYS", "NYSE AMERICAN": "AMS", "NYSE MKT": "AMS"}
NONCOMMON = {"UNIT", "PREFERRED", "WARRANT", "RIGHT", "DEBT", "FUND"}


def utc(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}(?:\.[0-9]+)?(?:Z|\+00:00)", value):
        raise ValueError("INVALID_UTC")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def source(record):
    host = urlparse(record["source_url"]).hostname or ""
    if (urlparse(record["source_url"]).scheme != "https" or
            not (host == "sec.gov" or host.endswith(".sec.gov")) or
            not re.fullmatch("[0-9a-f]{64}", record["source_sha256"])):
        raise ValueError("INVALID_SEC_PROVENANCE")


def read_snapshot(folder, expected_manifest_sha256):
    manifest_bytes = (folder / "manifest.json").read_bytes()
    if sha256(manifest_bytes).hexdigest() != expected_manifest_sha256:
        raise ValueError("SEC_MANIFEST_HASH")
    manifest = json.loads(manifest_bytes)
    body = (folder / "issuers.ndjson").read_bytes()
    if (manifest["schema_version"] != "sec-issuer-sic/1" or manifest["complete"] is not True
            or not isinstance(manifest["snapshot_id"], str) or not manifest["snapshot_id"].strip()
            or sha256(body).hexdigest() != manifest["issuers_sha256"] or not body.endswith(b"\n")
            or b"\r" in body):
        raise ValueError("INVALID_OR_PARTIAL_SEC_DELIVERY")
    source(manifest)
    collected = utc(manifest["collected_at"])
    rows = []
    counts = Counter()
    for line in body[:-1].decode("utf-8").split("\n"):
        r = json.loads(line)
        if (not re.fullmatch("[0-9]{10}", r["cik"]) or (rows and rows[-1]["cik"] >= r["cik"])
                or not isinstance(r["issuer_name"], str) or not r["issuer_name"].strip()
                or (r["sic"] is not None and not re.fullmatch("[0-9]{4}", r["sic"]))
                or not isinstance(r["sic_description"], (str, type(None)))
                or not isinstance(r["source_member"], (str, type(None)))
                or not isinstance(r["listings"], list) or utc(r["observed_at"]) > collected):
            raise ValueError("INVALID_SEC_ROW")
        source(r)
        for listing in r["listings"]:
            if (not isinstance(listing["ticker"], str) or not listing["ticker"].strip()
                    or not isinstance(listing["exchange"], (str, type(None)))):
                raise ValueError("INVALID_SEC_LISTING")
        rows.append(r)
        counts.update(issuer_count=1, listing_count=len(r["listings"]),
                      missing_sic_count=int(r["sic"] is None), no_listing_count=int(not r["listings"]))
    if any(type(manifest[k]) is not int or manifest[k] != v for k, v in counts.items()):
        raise ValueError("SEC_MANIFEST_COUNTS")
    return rows


def _security_type(evidence):
    if not evidence or evidence == {"UNVERIFIED"}:
        return "UNVERIFIED"
    if len(evidence) != 1:
        return "CONFLICT"
    kind, = evidence
    if kind == "COMMON" or kind in NONCOMMON:
        return kind
    raise ValueError("INVALID_SECURITY_KIND")


def _outcome(reason=None, *, sector=None, industry=None, excluded=False):
    status = "NOT_APPLICABLE" if excluded else ("ASSIGNED" if industry else "UNKNOWN")
    return dict(sector_id=sector, industry_id=industry, status=status, reason=reason)


def _issuer_assignment(sic, exact, guarded):
    if not sic:
        return _outcome("SIC_MISSING")
    direct = exact.get(sic, [])
    review = guarded.get(sic, [])
    if len(direct) == 1 and not review:
        return _outcome(sector=direct[0]["parent_sector"], industry=direct[0]["id"])
    parents = {g["parent_sector"] for g in direct + review}
    sector = next(iter(parents)) if len(parents) == 1 else None
    return _outcome("ACTIVITY_REVIEW_REQUIRED" if parents else "SIC_UNMAPPED", sector=sector)


def _multiple_listings(issuer_counts):
    multiples = [n for n in issuer_counts.values() if n > 1]
    return {"issuers_with_multiple_securities": len(multiples),
            "securities_of_these_issuers": sum(multiples)}


def _coverage(rows, groups):
    assigned = Counter(r["issuer_id"] for r in rows if r["industry_id"])
    return {
        "sector_rows": sum(bool(r["sector_id"]) for r in rows),
        "sector_issuers": len({r["issuer_id"] for r in rows if r["sector_id"]}),
        "sector_only_rows": sum(bool(r["sector_id"]) and not r["industry_id"] for r in rows),
        "industry_rows": sum(assigned.values()), "industry_issuers": len(assigned),
        "remaining_rows": len(rows) - sum(assigned.values()),
        "by_status": dict(Counter(r["status"] for r in rows)),
        "remaining_reasons": dict(Counter(r["reason"] for r in rows if r["reason"])),
        "assigned_multiple_listings": _multiple_listings(assigned),
        **distribution(rows, groups)}


def classify_market(master, issuers, security_evidence):
    """Master tuples are (venue, symbol, kind, currency, DR flag) from read_master.
    Class evidence keys are (venue, normalized symbol, exact SEC CIK), with a set
    of verified instrument kinds. An empty set is valid and leaves type open.
    """
    listings = defaultdict(set)
    unresolved_venue = defaultdict(set)
    by_cik = {row["cik"]: row for row in issuers}
    for row in issuers:
        for listing in row["listings"]:
            symbol = listing["ticker"].strip().upper()
            exchange = (listing["exchange"] or "").strip().upper()
            if exchange in VENUES:
                listings[VENUES[exchange], symbol].add(row["cik"])
            elif not exchange:
                unresolved_venue[symbol].add(row["cik"])
    groups = {g["id"]: g for g in load_dictionary()["industries"]}
    exact, needs_activity = defaultdict(list), defaultdict(list)
    for g in groups.values():
        for code in g["sic_codes"]:
            exact[code].append(g)
        for code in g["sic_requires_activity"]:
            needs_activity[code].append(g)
    master_keys = Counter((market, symbol.strip().upper()) for market, symbol, *_ in master)
    activity_counts = dict.fromkeys(sorted(needs_activity), 0)
    rows = []
    for market, raw_symbol, kind, currency, _ in master:
        if kind != "2":
            continue
        symbol = raw_symbol.strip().upper()
        key = market, symbol
        candidates = listings[key]
        cik = None
        security_type = "UNVERIFIED"
        if master_keys[key] != 1:
            candidate = _outcome("DUPLICATE_MASTER_KEY")
        elif len(candidates) > 1 or (candidates and unresolved_venue[symbol] - candidates):
            candidate = _outcome("AMBIGUOUS_ISSUER")
        elif not candidates:
            candidate = _outcome("VENUE_UNKNOWN" if unresolved_venue[symbol] else "NO_EXACT_ISSUER")
        else:
            cik, = candidates
            security_type = _security_type(security_evidence.get((market, symbol, cik), set()))
            sic = by_cik[cik]["sic"]
            if sic in activity_counts:
                activity_counts[sic] += 1
            if sic == "6770":
                candidate = _outcome("BLANK_CHECK", excluded=True)
            elif security_type in NONCOMMON:
                candidate = _outcome(security_type, excluded=True)
            elif currency != "USD":
                candidate = _outcome("CURRENCY_UNVERIFIED")
            elif security_type == "CONFLICT":
                candidate = _outcome("SECURITY_TYPE_CONFLICT")
            else:
                candidate = _issuer_assignment(sic, exact, needs_activity)

        strict = candidate
        if cik and currency == "USD" and security_type == "UNVERIFIED" and candidate["status"] != "NOT_APPLICABLE":
            strict = _outcome("COMMON_NOT_VERIFIED")
        rows.append(dict(market=market, symbol=symbol, issuer_id=cik, **strict,
                         security_type=security_type, issuer_candidate=candidate,
                         grade="CANDIDATE", accounting_model="UNKNOWN"))

    strict_counts = _coverage(rows, groups)
    candidate_counts = _coverage([dict(issuer_id=r["issuer_id"], **r["issuer_candidate"]) for r in rows], groups)
    linked = Counter(r["issuer_id"] for r in rows if r["issuer_id"])
    # Preserve the original strict row and count fields for existing private readers.
    return rows, {
        "stock_rows": len(rows), "linked_rows": sum(linked.values()), "linked_issuers": len(linked),
        "linked_multiple_listings": _multiple_listings(linked),
        "linked_security_types": dict(Counter(r["security_type"] for r in rows if r["issuer_id"])),
        "activity_rows_by_sic": activity_counts,
        "strict": strict_counts, "issuer_candidate": candidate_counts, **strict_counts}
