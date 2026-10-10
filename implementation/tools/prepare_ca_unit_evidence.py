"""Install hash-pinned CA primary evidence and reviewed historical price repair.

This is an offline replay step. Bundled sources are retained retrievals, not
invented issuer announcements. RawDatasetStore preserves replaced artifacts.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from investment_system.ingestion.raw_store import RawDatasetStore

GE = ROOT / "reports" / "gate_evidence"


def checked(path, sha):
    data = (GE / path).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise ValueError(f"PINNED_SOURCE_HASH_MISMATCH:{path}")
    return data


def prepare(store):
    from investment_system.public_price_boundary import block_public_route
    block_public_route()
    policy = json.loads((GE / "ca_unit_policy_v1.json").read_text())
    for e in policy["events"]:
        for d in e["documents"]:
            body = checked(d["bundled_path"], d["sha256"])
            if not store.has(d["artifact_id"]) or store.get_bytes(d["artifact_id"]) != body:
                store.put(d["artifact_id"], body, d["url"], "PINNED_PRIMARY_SOURCE_RETRIEVAL",
                          "text/html",
                          "prepare_ca_unit_evidence.py", notes="Replay of retained primary retrieval; publication date is separate in CA policy.")
    repair = json.loads((GE / "ca_unit_price_identity_repair.json").read_text())
    for key in ("mapping_document", "source", "normalized"):
        checked(repair[key]["path"], repair[key]["sha256"])
    source = json.loads(checked(repair["source"]["path"], repair["source"]["sha256"]))["chart"]["result"][0]
    body = checked(repair["normalized"]["path"], repair["normalized"]["sha256"])
    normalized = json.loads(body)["chart"]["result"][0]
    source_prices = dict(zip(source["timestamp"], source["indicators"]["quote"][0]["close"]))
    if not all(source_prices[t] == p for t, p in zip(normalized["timestamp"], normalized["indicators"]["quote"][0]["close"])):
        raise ValueError("HISTORICAL_PRICES_CHANGED")
    if normalized["meta"]["historical_cik"] != repair["cik"]:
        raise ValueError("HISTORICAL_ISSUER_MISMATCH")
    for prefix in ("yahoo_chart", "yahoo_events"):
        aid = f'{prefix}:{repair["symbol"]}:5y'
        if not store.has(aid) or store.get_bytes(aid) != body:
            store.put(aid, body, repair["source"]["url"], "YAHOO_HISTORICAL_IDENTITY_REPAIR", "application/json",
                      "prepare_ca_unit_evidence.py", notes="Exact historical observations from retained provider source; see ca_unit_price_identity_repair.json. Rejected original retained in store history.")
    return {"primary_events": len(policy["events"]), "historical_identity_repair": repair["symbol"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    print(json.dumps(prepare(RawDatasetStore(ap.parse_args().store))))
