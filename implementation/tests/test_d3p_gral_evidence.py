"""Regression for the reviewed GRAL first-subsequent-periodic evidence."""

import json
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from investment_system.ingestion.raw_store import RawDatasetStore


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "reports" / "gate_evidence" / "corporate_action_policy_2024-06-30.json"


def _chain():
    spec = spec_from_file_location("chain_gral_evidence", ROOT / "tools" / "run_top500_gate_chain.py")
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gral_policy_cites_actual_first_subsequent_10q_and_exact_issuance(tmp_path):
    chain = _chain()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    cik = "0001699031"
    row = policy["share_reconstruction"][cik]
    doc = row["first_subsequent_periodic_document"]
    assert (doc["accession"], doc["form"], doc["filed"], doc["period_end"]) == (
        "0001628280-24-036965", "10-Q", "2024-08-13", "2024-06-30"
    )

    store = RawDatasetStore(tmp_path)
    store.put(f"submissions:{cik}", json.dumps({"filings": {"recent": {
        "form": ["10-Q", "10-Q", "10-K"],
        "filingDate": ["2024-08-13", "2024-11-13", "2025-03-05"],
        "accessionNumber": ["0001628280-24-036965", "0001628280-24-047606", "0001699031-25-000041"],
        "primaryDocument": ["gral-20240630.htm", "gral-20240930.htm", "gral-20241231.htm"],
    }}}).encode(), "u", "SEC", "application/json", "t", 200)
    store.put(doc["artifact_id"], (
        b"The Spin-Off was completed through a distribution of approximately 85.5% of our "
        b"outstanding common stock to the holders of record (the Distribution), which resulted "
        b"in the issuance of 31,049,148 shares of common stock."
    ), doc["url"], "SEC", "text/html", "t", 200)
    store.put("yahoo_chart:GRAL:5y", json.dumps({"chart": {"result": [{
        "timestamp": [1719619200],
        "indicators": {"quote": [{"close": [15.0]}]},
    }]}}).encode(), "u", "Yahoo", "application/json", "t", 200)

    overrides = {}
    result = chain.apply_corporate_action_share_counts(
        store, overrides, {"gral": {"cik": cik, "yahoo": "GRAL"}}, policy,
        datetime(2024, 6, 30, tzinfo=timezone.utc),
    )
    assert result["GRAL"]["status"] == "APPLIED"
    assert overrides["gral"]["shares"] == 31_049_148
