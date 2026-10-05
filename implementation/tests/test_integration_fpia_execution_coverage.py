"""PIW-D003/D005: an integrity-bound raw PASS must not hide execution gaps."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/integration/track_c_fpia_execution_coverage.py"


def consumer():
    assert TOOL.is_file(), "PIW execution coverage consumer is not implemented"
    spec = importlib.util.spec_from_file_location("coverage_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def document():
    # Synthetic protocol fixture, never an authenticated receipt.
    result = {
        "schema": "TRACK_C_FPIA/2", "subject": {"tree": "a" * 40},
        "fpia": {"status": "FPIA_PASS"},
        "integration_interference": {
            "dynamic_invocation_detection": "NOT_CLAIMED",
            "out_of_tree_code_analysis": "NOT_ANALYSED", "spawns": [],
            "workflow_analysis": {
                "dynamic_invocation_detection": "NOT_CLAIMED",
                "out_of_tree_code_analysis": "NOT_ANALYSED",
                "out_of_tree_references": [
                    {"in": ".github/workflows/example.yml", "uses": "example/action@v1"}
                ],
            },
        },
    }
    return bound(result)


def bound(result):
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {"schema": "TRACK_C_FPIA/2", "result": result,
            "result_sha256": hashlib.sha256(raw).hexdigest()}


def assess(doc):
    return consumer().assess_coverage(doc, "a" * 40, doc["result_sha256"])


def test_raw_pass_remains_blocked_and_inputs_remain_unchanged():
    doc = document()
    before = copy.deepcopy(doc)
    r = assess(doc)
    assert r["status"] == "COVERAGE_BLOCKED"
    assert {b["code"] for b in r["blockers"]} == {
        "DYNAMIC_EXECUTION_UNCOVERED", "EXTERNAL_EXECUTION_UNANALYSED"}
    assert r["raw_fpia_status"] == "FPIA_PASS"
    assert r["external_reference_count"] == 1
    assert r["authentication"] == "NOT_VERIFIED"
    assert r["integration_acceptance"] == "BLOCKED"
    assert doc == before


@pytest.mark.parametrize("field", ["subject", "hash", "external_anchor", "schema"])
def test_stale_or_substituted_evidence_is_unavailable(field):
    doc = document()
    subject, anchor = "a" * 40, doc["result_sha256"]
    if field == "subject":
        subject = "b" * 40
    elif field == "hash":
        doc["result"]["fpia"]["status"] = "FPIA_FAIL"
    elif field == "external_anchor":
        anchor = "b" * 64
    else:
        doc["schema"] = "UNKNOWN"
    r = consumer().assess_coverage(doc, subject, anchor)
    assert r["status"] == "COVERAGE_UNAVAILABLE"
    assert r["integration_acceptance"] == "BLOCKED"


@pytest.mark.parametrize("missing", ["integration_interference", "workflow_analysis", "spawns",
                                     "out_of_tree_references", "dynamic_invocation_detection"])
def test_missing_coverage_never_means_no_gap(missing):
    doc = document()
    r = doc["result"]
    if missing == "integration_interference":
        del r[missing]
    elif missing in ("workflow_analysis", "spawns"):
        del r["integration_interference"][missing]
    else:
        del r["integration_interference"]["workflow_analysis"][missing]
    assert assess(bound(r))["status"] == "COVERAGE_UNAVAILABLE"


def test_self_asserted_completion_does_not_clear_unknown_execution():
    doc = document()
    i = doc["result"]["integration_interference"]
    for section in (i, i["workflow_analysis"]):
        section["dynamic_invocation_detection"] = "PASS"
        section["out_of_tree_code_analysis"] = "PASS"
    i["workflow_analysis"]["out_of_tree_references"] = []
    r = assess(bound(doc["result"]))
    assert r["status"] == "COVERAGE_BLOCKED"
    assert r["integration_acceptance"] == "BLOCKED"


def test_grandchild_spawn_and_container_record_are_preserved_as_gaps():
    doc = document()
    i = doc["result"]["integration_interference"]
    i["spawns"] = [{"argv": ["python", "-c", "print('child')"], "by": "tests/example.py"}]
    i["workflow_analysis"]["out_of_tree_references"] = [{"container_image": "example/image@sha256:digest"}]
    r = assess(bound(doc["result"]))
    assert "DESCENDANT_EXECUTION_UNCOVERED" in {b["code"] for b in r["blockers"]}
    assert r["spawn_count"] == r["external_reference_count"] == 1


def test_non_ascii_result_uses_the_existing_fpia_hash_protocol():
    doc = document()
    doc["result"]["diagnostic"] = "실행 범위"
    assert assess(bound(doc["result"]))["status"] == "COVERAGE_BLOCKED"


@pytest.mark.parametrize("text", ['{"result":{},"result":{}}', '{"result":{"x":NaN}}'])
def test_cli_rejects_ambiguous_json_and_does_not_write_input(tmp_path, text):
    consumer()
    source = tmp_path / "input.json"
    source.write_text(text)
    run = subprocess.run([sys.executable, str(TOOL), "--evidence", str(source),
                          "--subject", "a" * 40, "--result-sha256", "b" * 64],
                         capture_output=True, text=True)
    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "COVERAGE_UNAVAILABLE"
    assert source.read_text() == text


def test_cli_outputs_bound_blockers_and_fails_closed(tmp_path):
    consumer()
    doc = document()
    source = tmp_path / "fpia.json"
    source.write_text(json.dumps(doc))
    run = subprocess.run([sys.executable, str(TOOL), "--evidence", str(source),
                          "--subject", "a" * 40, "--result-sha256", doc["result_sha256"]],
                         capture_output=True, text=True)
    assert run.returncode == 1
    assert json.loads(run.stdout)["status"] == "COVERAGE_BLOCKED"
