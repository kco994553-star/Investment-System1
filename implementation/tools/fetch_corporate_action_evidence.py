"""Fetch only the SEC documents named by a reviewed D3-P corporate-action policy evidence file.

The policy file is the authority for *which* documents may be fetched.  This tool does not
decide whether a policy applies; the offline gate re-verifies the stored bytes and fails closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"


def policy_documents(policy: dict) -> list[dict]:
    docs = []
    for row in (policy.get("price_reconstruction") or {}).values():
        if row.get("document"):
            docs.append(row["document"])
    for row in (policy.get("share_reconstruction") or {}).values():
        if row.get("first_subsequent_periodic_document"):
            docs.append(row["first_subsequent_periodic_document"])
    for row in (policy.get("reference_exclusions") or {}).values():
        docs.extend(row.get("documents") or [])
    return docs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", required=True)
    a = ap.parse_args()
    path = GE / f"corporate_action_policy_{a.as_of}.json"
    if not path.exists():
        print(json.dumps({"status": "NO_POLICY_FOR_AS_OF", "as_of": a.as_of}))
        return
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("as_of") != a.as_of or not policy.get("result_independent") or not policy.get("rank_and_cutoff_not_inputs"):
        raise SystemExit("corporate-action policy metadata is incomplete or for another as_of")

    spec = importlib.util.spec_from_file_location("_ca_fetch_real_data", ROOT / "tools" / "fetch_real_data.py")
    frd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frd)
    store, log = RawDatasetStore(a.store), []
    for doc in policy_documents(policy):
        aid, url = str(doc.get("artifact_id") or ""), str(doc.get("url") or "")
        if not aid.startswith("sec_filing_doc:") or not url.startswith("https://www.sec.gov/Archives/"):
            raise SystemExit(f"invalid reviewed SEC document: {aid}")
        frd._fetch_one(store, aid, url, "SEC_FILING_DOCUMENT", frd.UA, log, False)
        frd._throttle(log, 0.15)
    frd.write_store_index(store)
    print(json.dumps({"status": "DONE", "as_of": a.as_of, "documents": len(log), "log": log}, indent=2))


if __name__ == "__main__":
    main()
