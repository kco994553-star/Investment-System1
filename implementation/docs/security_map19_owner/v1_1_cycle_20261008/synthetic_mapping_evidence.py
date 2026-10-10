"""Independent identity-only evidence for verifier tests, without market inputs.

Retained identity/target metadata supplies the named regression cases (including
the verifier's explicit ASML/Alphabet rules). All source envelopes and XML are
generated here; no captured N-PORT input, price, share count or value is read.
"""
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def build(root):
    document = json.loads((Path(__file__).parent / "CURRENT_TARGET_IDENTITY_MAP.json").read_text())
    document["source_pins"] = {}
    document["test_lineage"] = "INDEPENDENT_IDENTITY_ONLY_SOURCES_NO_MARKET_VALUES"

    def source(name, value, compressed=False):
        data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
        stored = gzip.compress(data, mtime=0) if compressed else data
        path = name + (".xml.gz" if compressed else ".fixture")
        (root / path).write_bytes(stored)
        pin = {"replay_path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
               "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
        if compressed:
            pin.update(compression="gzip", compressed_sha256=hashlib.sha256(stored).hexdigest())
        document["source_pins"][name] = pin

    target, associations, registry = [], [], {}
    nport_report = {"member_cusips": {}, "member_names": {}}
    xml = ET.Element("syntheticIdentityEvidence")
    for index, row in enumerate(document["rows"]):
        authored = row["target_row"]
        target.extend([f'  - theme_id: {authored["theme_id"]}',
                       f'    - {{ label: {authored["label"]}, ticker_hint: "{authored["ticker_hint"]}", listing: "{authored["listing"]}", weight_units: {authored["weight_units"]} }}'])
        if row["security_ref"]["scheme"] != "ISIN":
            continue
        cik, cid = row["issuer_ref"]["value"], row["frozen_company_key"]
        registry[cid] = {"cik": cik, "yahoo": authored["ticker_hint"]}
        associations.append([cik, authored["ticker_hint"], row["current_listing_observation"]["exchange"]])
        if cid == "asml":
            continue
        name = f"INDEPENDENT_SYNTHETIC_ISSUER_{index}"
        cusip = row["security_evidence"]["cusip"]
        nport_report["member_cusips"][cik] = [cusip]
        nport_report["member_names"][cik] = [name]
        holding = ET.SubElement(xml, "invstOrSec")
        fields = {"name": name, "title": row["security_evidence"]["title"], "cusip": cusip,
                  "assetCat": "EC", "curCd": row["current_listing_observation"]["currency"],
                  "invCountry": "TEST", "lei": "INDEPENDENT_SYNTHETIC_LEI"}
        for key, value in fields.items():
            ET.SubElement(holding, key).text = value
        ET.SubElement(holding, "isin", value=row["security_ref"]["value"])
    raw = ET.tostring(xml)
    source("target_v0", "\n".join(target).encode())
    source("frozen_sec_associations", registry)
    source("frozen_ingested_associations", registry)
    source("frozen_nport_reference", nport_report)
    source("frozen_nport_manifest", {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    source("frozen_nport_original_replay", raw, compressed=True)
    source("sec_exchange_original", {"fields": ["cik", "ticker", "exchange"], "data": associations})
    source("asml_share_form_extract", b"Synthetic identity regression: NASDAQ ASML USN070592100 / N07059210 US Dollar")
    return document
