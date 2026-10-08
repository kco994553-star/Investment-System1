#!/usr/bin/env python3
"""Replay current TARGET identity evidence; no provider calls or portfolio calculations."""
from __future__ import annotations

import hashlib
import json
import gzip
from datetime import datetime
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "implementation" / "src"))
from investment_system.contracts.global_universe import IssuerIdentity, SecurityIdentity


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def child_text(element, key):
    matches = [child.text for child in element if local_name(child) == key]
    require(len(matches) == 1, f"missing/ambiguous NPORT field {key}")
    return matches[0]


def source_rows(raw):
    result = []
    for element in ET.fromstring(raw).iter():
        if local_name(element) != "invstOrSec":
            continue
        isins = [x.attrib["value"] for x in element.iter() if local_name(x) == "isin"]
        result.append({
            "name": child_text(element, "name"),
            "title": child_text(element, "title"),
            "cusip": child_text(element, "cusip"),
            "isins": isins,
            "asset_category": child_text(element, "assetCat"),
            "currency": child_text(element, "curCd"),
            "investment_country": child_text(element, "invCountry"),
            "lei": child_text(element, "lei"),
        })
    return result


def target_rows(text):
    rows = []
    theme = None
    for line in text.splitlines():
        match = re.match(r"\s*- theme_id: ([a-z_]+)\s*$", line)
        if match:
            theme = match[1]
        if not re.match(r"\s*- \{ label:", line):
            continue
        match = re.fullmatch(
            r'\s*- \{ label:\s*(.+?),\s*ticker_hint:\s*("[^"]+"|[^,]+),\s*listing:\s*("[^"]+"|[^,]+),\s*weight_units:\s*(\d+)\s*\}\s*', line)
        require(match is not None and theme is not None, "unsupported TARGET holding syntax")
        label, ticker, listing, units = match.groups()
        rows.append({"label": label.strip(), "ticker_hint": ticker.strip().strip('"'),
                     "listing": listing.strip().strip('"'), "weight_units": int(units), "theme_id": theme})
    require(len(rows) == 19, "TARGET must contain exact19 rows")
    return rows


def verify(document=None):
    document = document or json.loads((HERE / "CURRENT_TARGET_IDENTITY_MAP.json").read_text())
    require(document["autonomy_mode"] == "READ_ONLY", "autonomy mode changed")
    require(document["source_values_changed"] is False, "source values were changed")
    require(document["current_only_no_historical_backdating"] is True, "mapping PIT scope changed")
    require(datetime.fromisoformat(document["mapping_effective_from"]) == datetime.fromisoformat(document["mapping_available_at"]),
            "mapping availability/effective clock disagreement")
    require(datetime.fromisoformat(document["mapping_available_at"]) >= datetime.fromisoformat(document["target_effective_at"]),
            "new mapping was backdated before TARGET adoption")
    for name, pin in document["source_pins"].items():
        raw = (ROOT / pin["replay_path"]).read_bytes()
        if pin.get("compression") == "gzip":
            require(hashlib.sha256(raw).hexdigest() == pin["compressed_sha256"], f"compressed source hash mismatch: {name}")
            raw = gzip.decompress(raw)
        require(len(raw) == pin["bytes"], f"source size mismatch: {name}")
        require(hashlib.sha256(raw).hexdigest() == pin["sha256"], f"source hash mismatch: {name}")
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == pin["git_blob"],
                f"source Git blob mismatch: {name}")
    def read_source(name):
        pin = document["source_pins"][name]
        raw = (ROOT / pin["replay_path"]).read_bytes()
        return gzip.decompress(raw) if pin.get("compression") == "gzip" else raw
    target = target_rows(read_source("target_v0").decode())
    sec_map = json.loads(read_source("frozen_sec_associations"))
    ingested_map = json.loads(read_source("frozen_ingested_associations"))
    nport_report = json.loads(read_source("frozen_nport_reference"))
    nport_manifest = json.loads(read_source("frozen_nport_manifest"))
    nport_raw = read_source("frozen_nport_original_replay")
    require(hashlib.sha256(nport_raw).hexdigest() == nport_manifest["sha256"], "NPORT does not match Frozen manifest")
    require(len(nport_raw) == nport_manifest["bytes"], "NPORT does not match Frozen byte count")
    holdings = source_rows(nport_raw)
    association_raw = json.loads(read_source("sec_exchange_original"))
    fields = association_raw["fields"]
    association_rows = [dict(zip(fields, row)) for row in association_raw["data"]]
    require(len(document["rows"]) == 19, "mapping must contain exact19 rows")
    seen = set()
    c39_objects = 0
    for index, (row, authored) in enumerate(zip(document["rows"], target)):
        require(row["row_index"] == index, "row order changed")
        require(row["mapping_available_at"] == document["mapping_available_at"] and
                row["mapping_effective_from"] == document["mapping_effective_from"], "row clock disagreement")
        require(row["target_row"] == authored, f"authored TARGET changed in row{index}")
        require(row["mapping_status"] == "RESOLVED_CURRENT_TARGET_SCOPE", f"row{index} not resolved")
        ref = row["security_ref"]
        key = json.dumps(ref, sort_keys=True)
        require(key not in seen, "duplicate security reference")
        seen.add(key)
        require(row["dated_listing_identity"] is None, "unsupported dated ListingIdentity")
        if ref["scheme"] == "EXCHANGE_CODE":
            expected = ("TSE", "8035") if authored["label"] == "Tokyo Electron" else ("KRX", "042700")
            require((ref["exchange"], ref["code"]) == expected, "foreign user choice changed")
            require(authored["ticker_hint"] == expected[1] and "USER_DECIDED" in authored["listing"], "foreign ref lacks user source")
            require(row["c39_security_identity"] is None and row["c39_issuer_identity"] is None,
                    "full non-US hierarchy cannot be claimed from listing pair alone")
            require(row["security_id"] is None, "exchange/code is not an invented standalone security ID")
            continue
        require(ref["scheme"] == "ISIN", "unsupported security-reference scheme")
        cik = row["issuer_ref"]["value"]
        cid = row["frozen_company_key"]
        require(sec_map[cid]["cik"] == cik == ingested_map[cid]["cik"], "Frozen CIK disagreement")
        require(sec_map[cid]["yahoo"] == authored["ticker_hint"] == ingested_map[cid]["yahoo"], "Frozen symbol disagreement")
        hits = [r for r in association_rows if str(r["cik"]).zfill(10) == cik and r["ticker"] == authored["ticker_hint"]]
        require(len(hits) == 1, "issuer/exchange/ticker join is uncertain")
        require(hits[0]["exchange"] == row["current_listing_observation"]["exchange"], "exchange disagrees")
        require(row["security_id"] == ref["value"], "ISIN is not a source-native SecurityIdentity ID")
        security = row["c39_security_identity"]
        issuer = row["c39_issuer_identity"]
        require(security["security_id"] == ref["value"] and security["issuer_id"] == issuer["issuer_id"] == cik,
                "CIK/ISIN hierarchy changed")
        require(["ISIN", ref["value"]] in security["identifiers"], "missing explicit ISIN namespace")
        require(["CIK", cik] in issuer["identifiers"], "missing explicit CIK namespace")
        IssuerIdentity(**{**issuer, "identifiers": tuple(tuple(x) for x in issuer["identifiers"])})
        SecurityIdentity(**{**security, "identifiers": tuple(tuple(x) for x in security["identifiers"])})
        c39_objects += 1
        if cid == "asml":
            text = read_source("asml_share_form_extract").decode()
            require("NASDAQ ASML USN070592100 / N07059210 US Dollar" in text, "ASML NASDAQ identifiers not sourced")
            require(ref["value"] == "USN070592100" and security["security_type"] == "ORDINARY_SHARES", "ASML instrument changed")
            require(row["share_form"] == "REGISTERED_NASDAQ_ORDINARY_SHARES", "ASML was misclassified as ADR")
        else:
            cusip = row["security_evidence"]["cusip"]
            require(cusip in nport_report["member_cusips"][cik], "NPORT CUSIP has no Frozen issuer link")
            matches = [h for h in holdings if h["cusip"] == cusip and ref["value"] in h["isins"]]
            require(len(matches) == 1, "ambiguous/missing exact NPORT instrument")
            holding = matches[0]
            require(holding["name"] in nport_report["member_names"][cik], "NPORT issuer-name join changed")
            require(holding["asset_category"] == "EC", "NPORT instrument is not common equity")
            require(holding["title"] == row["security_evidence"]["title"], "NPORT security title changed")
            require(holding["currency"] == row["current_listing_observation"]["currency"], "currency changed")
            if cid == "googl":
                require(holding["title"] == "ALPHABET INC CLASS A" and cusip == "02079K305", "Alphabet Class A changed")
                require(security["share_class"] == "A", "Alphabet Class A not bound")
    require(c39_objects == 17, "US17 C39 binding incomplete")
    counts = document["counts"]
    require(counts["attempted"] == counts["resolved_current_target_refs"] == 19 and counts["unresolved_current_target_refs"] == 0,
            "current TARGET counts disagree")
    require(counts["dated_listing_identities_bound"] == 0, "dated Market admission overstated")
    return {"status": "PASS", "current_target_refs": "19/19", "c39_issuer_security_pairs": "17/17",
            "user_exchange_code_refs": "2/2", "dated_listing_identity": "0/19", "source_pins": len(document["source_pins"])}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
