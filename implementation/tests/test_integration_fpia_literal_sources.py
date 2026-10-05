"""Successor probes: literal execution sources and explicit external image evidence.

These are bounded repairs to fix3's declared source coverage, not dynamic invocation
or external-code safety claims. The original fix3 battery and history stay intact.
"""
import pytest

from tests.test_integration_fpia_fix3 import TOOL, WF, _outcome, battery, wf
from tests import integration_fpia_testkit as tk


@pytest.mark.parametrize("command,files", [
    ("bash ci/commands.txt", {"ci/commands.txt": "python " + TOOL + "\n"}),
    ("python ci/commands.txt", {"ci/commands.txt":
        "import subprocess\nsubprocess.run(['python', '" + TOOL + "'])\n"}),
    ('bash "ci/run commands.sh"', {"ci/run commands.sh": "python " + TOOL + "\n"}),
    ("bash ci/entry.sh", {"ci/entry.sh": "bash ci/nested.txt\n",
                           "ci/nested.txt": "python " + TOOL + "\n"}),
])
def test_literal_executable_source_is_scanned(battery, command, files):
    got, spoof, _, info = _outcome(battery, {"files": {WF: wf(["run: " + command]), **files}})
    assert got == "FOUND", (command, info["workflow_analysis"])
    assert any("mentions Track C scope" in reason for reason in spoof[0]["reasons"])
    assert set(files) <= set(spoof[0]["reached"])


@pytest.mark.parametrize("command,files", [
    ("cat ci/commands.txt", {"ci/commands.txt": "python " + TOOL + "\n"}),
    ('bash "ci/run commands.sh"', {"ci/run commands.sh": "echo ordinary\n"}),
    ("bash ci/commands.txt", {"ci/commands.txt": "echo ordinary\n"}),
])
def test_literal_source_benign_controls(battery, command, files):
    got, _, findings, _ = _outcome(battery, {"files": {WF: wf(["run: " + command]), **files}})
    assert got == "NOT_FOUND" and not findings


@pytest.mark.parametrize("extra,expected", [
    ("    container: alpine:3.20\n", [("job_container", "alpine:3.20")]),
    ("    container:\n      image: alpine:3.20\n", [("job_container", "alpine:3.20")]),
    ("    services:\n      data:\n        image: redis:7\n", [("service_container", "redis:7")]),
])
def test_explicit_external_images_recorded_without_safety_claim(battery, extra, expected):
    got, _, findings, info = _outcome(battery, {"files": {WF: wf(["run: echo ordinary"], job_extra=extra)}})
    assert got == "NOT_FOUND" and not findings
    wa = info["workflow_analysis"]
    refs = [r for r in wa["out_of_tree_references"] if r["workflow"] == WF]
    assert sorted((r["kind"], r["image"]) for r in refs) == expected
    assert wa["out_of_tree_code_analysis"] == "NOT_ANALYSED"


def test_arbitrary_image_input_is_not_job_container(battery):
    text = wf(["uses: other-org/action@v1\n  with:\n    image: documentation-only"])
    _, _, _, info = _outcome(battery, {"files": {WF: text}})
    refs = [r for r in info["workflow_analysis"]["out_of_tree_references"] if r["workflow"] == WF]
    assert refs == [{"workflow": WF, "in": WF, "uses": "other-org/action@v1"}]


def test_literal_script_end_to_end_status(tmp_path):
    w = tk.variant(tmp_path)
    tree = w.git.change(w.c["T0"], {
        WF: wf(["run: bash ci/commands.txt"]),
        "ci/commands.txt": "python " + TOOL + "\n",
    }, "literal script counterexample")
    result = w.fpia(tree, w.register(w.c["R0"], [w.c["V0"]], [tree]))
    assert result["fpia"]["status"] == "FPIA_FAIL"
    assert result["statuses"]["integration_interference"] == "INTEGRATION_INTERFERENCE_FOUND"
    assert result["statuses"]["runtime_provenance"] == "PASS"
    assert result["statuses"]["full_regression"] == "PASS"
    assert result["statuses"]["code_identity"] == "CODE_IDENTITY_DIVERGED"
