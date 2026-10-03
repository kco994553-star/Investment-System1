"""Existing producer admission versus exact owner JS guard; synthetic test vectors only."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from investment_system.producers.contract import make_snapshot, validate_snapshot

root = Path(__file__).resolve().parent
bundle = json.loads((root.parent / "test-vector.schema1.json").read_text())
data = deepcopy(bundle["qgv"]["data"])
data["G3_SYNTHETIC_TEST_VECTOR_ONLY"]["diagnostics"] = {
    "old_candidate": {"research_state": {"status": "IDEA"}}
}
methodology = {"id": "TEST_VECTOR_ONLY", "version": "TEST_ONLY", "status": "CERTIFIED_TEST_VECTOR_ONLY"}
rows = []
for state in ("LIVE", "FROZEN_SNAPSHOT"):
    snapshot = make_snapshot(
        producer_id="G3_TEST_VECTOR_ONLY", producer_version="TEST_ONLY", section="qgv",
        data_state=state, as_of=bundle["qgv"]["as_of"], generated_at="2026-10-03T00:01:00Z",
        expires_at=bundle["qgv"]["expires_at"] if state == "LIVE" else None,
        methodology=methodology, synthetic=False,
        provenance={"source": "G3 test vector only", "inputs": [{"artifact_id": "G3_TEST_VECTOR_ONLY", "sha256": "0" * 64}]},
        validation={"status": "PASS", "checks": ["TEST_VECTOR_ONLY"]}, data=deepcopy(data), scope_kind="ENTITY_MAP",
    )
    before = deepcopy(snapshot)
    validate_snapshot(snapshot)
    assert snapshot == before
    rows.append({"state": state, "actual_existing_producer_admission": "ACCEPTED", "methodology_status": methodology["status"],
                 "unrelated_diagnostic_status": "IDEA", "snapshot_unchanged": True})
source = Path("/workspace/web-g3-upstream-readonly/implementation/src/investment_system/producers/contract.py")
receipt = {"upstream_head": "2b53b27fe0f570557159d02552911e9e1cc7be9c", "producer_source_sha256": sha256(source.read_bytes()).hexdigest(),
           "scope": "SYNTHETIC_TEST_VECTOR_ONLY; NO_GRANT", "cases": rows,
           "policy_parity": "Exact upstream JS recursively withholds this diagnostic shape; existing producer admission accepts it.",
           "source_mutations": 0, "real_data_provider_calls": 0}
(root / "producer-policy-parity.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"accepted_test_vectors": len(rows), "real_data_provider_calls": 0}))
