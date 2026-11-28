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
    rows = []
    for market, raw_symbol, kind, currency, _ in master:
        if kind != "2":
            continue
        symbol = raw_symbol.strip().upper()
        key = market, symbol
        candidates = listings[key]
        cik = None
        sector = group = None
        status = "UNKNOWN"
        if master_keys[key] != 1:
            reason = "DUPLICATE_MASTER_KEY"
        elif len(candidates) > 1 or (candidates and unresolved_venue[symbol] - candidates):
            reason = "AMBIGUOUS_ISSUER"
        elif not candidates:
            reason = "VENUE_UNKNOWN" if unresolved_venue[symbol] else "NO_EXACT_ISSUER"
        else:
            cik, = candidates
            evidence = security_evidence.get((market, symbol, cik), set())
            sic = by_cik[cik]["sic"]
            if sic == "6770":
                status, reason = "NOT_APPLICABLE", "BLANK_CHECK"
            elif len(evidence) == 1 and evidence <= NONCOMMON:
                status, reason = "NOT_APPLICABLE", next(iter(evidence))
            elif currency != "USD":
                reason = "CURRENCY_UNVERIFIED"
            elif evidence != {"COMMON"}:
                reason = "SECURITY_TYPE_CONFLICT" if len(evidence) > 1 else "COMMON_NOT_VERIFIED"
            elif not sic:
                reason = "SIC_MISSING"
            else:
                options = exact[sic] + needs_activity[sic]
                parents = {g["parent_sector"] for g in options}
                if len(exact[sic]) == 1 and not needs_activity[sic]:
                    group = exact[sic][0]["id"]
                    sector = exact[sic][0]["parent_sector"]
                    status, reason = "ASSIGNED", None
                else:
                    # Codes guarded for boundary/activity review cannot establish a parent alone.
                    if len(parents) == 1 and exact[sic]:
                        sector, = parents
                    reason = "ACTIVITY_REVIEW_REQUIRED" if options else "SIC_UNMAPPED"
        rows.append(dict(market=market, symbol=symbol, issuer_id=cik, sector_id=sector,
                         industry_id=group, status=status, reason=reason, grade="CANDIDATE",
                         accounting_model="UNKNOWN"))
    return rows, {
        "stock_rows": len(rows), "linked_rows": sum(bool(r["issuer_id"]) for r in rows),
        "linked_issuers": len({r["issuer_id"] for r in rows if r["issuer_id"]}),
        "sector_rows": sum(bool(r["sector_id"]) for r in rows),
        "industry_rows": sum(bool(r["industry_id"]) for r in rows),
        "remaining_rows": sum(r["status"] != "ASSIGNED" for r in rows),
        "by_status": dict(Counter(r["status"] for r in rows)),
        "remaining_reasons": dict(Counter(r["reason"] for r in rows if r["reason"])),
        **distribution(rows, groups)}
