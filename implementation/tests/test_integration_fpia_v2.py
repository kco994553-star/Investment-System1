"""CDR-012/v2 binding and behavioural rerun; attribution needs authenticated lineage (CDR-014 §6, §12;
rv2 #6/rc5; review MEDIUM A_V data closure, complement workflow spoofing; AC-34 and the FAIL-ONLY
counterfactual of the PIW ruling D3-B)."""
import pytest

from tests import integration_fpia_testkit as tk

EVL = "implementation/src/investment_system/evl/"
V2SRC = EVL + "superiority_v2.py"
CARRIER = "implementation/docs/codex_test/v2/CDR_TEST_APPROVAL.json"


def findings(a, cid=None):
    return [f for f in a.static_findings if cid is None or f["id"] == cid]


def test_v2_bytes_without_v_ancestry_fail(tmp_path):
    w = tk.variant(tmp_path)
    g, R, V = w.git, w.c["R0"], w.c["V0"]
    av = [V2SRC, CARRIER, "implementation/tests/test_evl_gsup_v2_basic.py", "implementation/tools/verify_v2_test.py"]
    T2 = g.change(R, {p: g.read(V, p) for p in av}, "byte copies of v2 files without V ancestry")
    G = w.register(R, [V], [T2])
    a = w.audit(T2, G)
    assert a.v_applies[V] is False
    paths = {f["path"] for f in findings(a, "AC-21")}
    assert V2SRC in paths and "implementation/tests/test_evl_gsup_v2_basic.py" in paths
    r = w.fpia(T2, G, options={"lanes": []})
    assert r["statuses"]["v2_binding"] == "NOT_APPLICABLE"
    assert r["fpia"]["status"] == "FPIA_FAIL"


def test_arbitrary_branch_cannot_be_declared_v(tmp_path):
    w = tk.variant(tmp_path)
    g, R, T = w.git, w.c["R0"], w.c["T0"]
    Vx = g.change(R, {EVL + "x.py": "X = 1\n"}, "V' arbitrary branch on R")
    T2 = g.merge(T, Vx, "merge V'")
    a = w.audit(T2, w.register(R, [w.c["V0"]], [T2]))
    assert any(f["path"] == EVL + "x.py" for f in findings(a, "AC-21"))


def test_two_v_references_disagree(tmp_path):
    w = tk.variant(tmp_path)
    g, R, V = w.git, w.c["R0"], w.c["V0"]
    V1 = g.change(R, {V2SRC: g.read(V, V2SRC).decode() + "\nOTHER = 1\n"}, "V1 with different v2 bytes")
    T2 = g.merge(V, V1, "merge both v2 heads", resolve={V2SRC: g.read(V, V2SRC)})
    G = w.register(R, [V, V1], [T2])
    a = w.audit(T2, G)
    assert a.auth["status"] == "PASS" and len(a.Vs) == 2
    assert any(c["id"] == "AC-06" and c["path"] == V2SRC for c in a.v2_checks)


@pytest.mark.parametrize("case", ["a_v2_byte_flip", "b_new_ns_file", "c_foreign_importer_static",
                                  "c_foreign_importer_dynamic_constant", "d_workflow_change_no_v", "e_approval_carrier_flip"])
def test_v2_binding_failures(tmp_path, case):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    if case == "a_v2_byte_flip":
        changes = {V2SRC: g.read(T, V2SRC).decode().replace("v * v", "v ** 2")}
    elif case == "b_new_ns_file":
        changes = {EVL + "new.py": "N = 1\n", "implementation/tests/test_evl_c9_x.py": "def test_x():\n    pass\n",
                   "implementation/reports/track_c_x.json": "{}\n"}
    elif case == "c_foreign_importer_static":
        changes = {"implementation/src/investment_system/rig/uses_evl.py": "from investment_system.evl import walkforward\n"}
    elif case == "c_foreign_importer_dynamic_constant":
        changes = {"implementation/src/investment_system/rig/uses_evl.py":
                   "import importlib\nM = importlib.import_module('investment_system.evl')\n"}
    elif case == "d_workflow_change_no_v":
        changes = {tk.WORKFLOW: g.read(T, tk.WORKFLOW).decode().replace("Full regression", "Full regression (edited)")}
    else:
        changes = {CARRIER: g.read(T, CARRIER).decode().replace("v2", "v3")}
    T2 = g.change(T, changes, "v2 tamper " + case)
    a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
    if case in ("a_v2_byte_flip", "e_approval_carrier_flip"):
        assert any(c["id"] == "AC-21" and c["status"] == "FAIL" for c in a.v2_checks), a.v2_checks
    elif case == "d_workflow_change_no_v":
        assert any(c["id"] == "AC-21" and c["status"] == "NOT_PRESERVED" for c in a.projection_checks)
    else:
        assert findings(a, "AC-21"), (case, a.static_findings)


def test_complement_workflow_spoofs_track_c_name_found(tmp_path):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    spoof = "name: track-c-evl-validation\non:\n  push:\njobs:\n  validate:\n    runs-on: ubuntu-latest\n" \
            "    steps:\n      - run: echo ok\n"
    runner = "name: other\non:\n  push:\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n" \
             "      - run: cd implementation && python -m pytest tests/test_evl_c8*.py\n"
    T2 = g.change(T, {".github/workflows/zz-spoof.yml": spoof, ".github/workflows/zz-runner.yml": runner}, "spoof")
    a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
    paths = {f["path"] for f in findings(a, "AC-32.spoof")}
    assert paths == {".github/workflows/zz-spoof.yml", ".github/workflows/zz-runner.yml"}
    # V's readiness workflow runs an A_V replay tool and is attributed (T == V): not a finding
    a0 = w.audit(w.c["T0"], w.register(w.c["R0"], [w.c["V0"]], [w.c["T0"]]))
    assert not findings(a0, "AC-32.spoof")


def _v_variant(w, changes):
    V1 = w.git.change(w.c["V0"], changes, "V1 variant")
    return V1


def test_replay_divergence_fails(tmp_path):
    w = tk.variant(tmp_path)
    g = w.git
    tool = "implementation/tools/verify_v2_test.py"
    V1 = _v_variant(w, {tool: g.read(w.c["V0"], tool).decode().replace(
        "from investment_system.evl.superiority_v2 import statistic  # noqa: E402",
        "from investment_system.evl.superiority_v2 import statistic  # noqa: E402\n"
        "from investment_system.evl import calibration_contracts as cc  # noqa: E402")
        .replace('"status": "PASS"', '"status": "PASS", "identity": cc.code_hash()')})
    T2 = g.merge(V1, w.c["F"], "merge foreign")
    r = w.fpia(T2, w.register(w.c["R0"], [V1], [T2]), options={"lanes": ["V", "T"]})
    rep = r["v2_binding"]["codex_replay"]
    assert rep and rep[0]["rc_V"] == 0 and rep[0]["rc_T"] == 0 and rep[0]["byte_identical"] is False
    assert r["statuses"]["v2_binding"] == "FAIL"


def test_v2_test_outcome_divergence_fails(tmp_path):
    w = tk.variant(tmp_path)
    g = w.git
    test = "implementation/tests/test_evl_gsup_v2_basic.py"
    V1 = _v_variant(w, {test: g.read(w.c["V0"], test).decode()
                        + "\n\ndef test_v2_no_extra_marker():\n    from pathlib import Path\n"
                          "    assert not (Path(__file__).parent / 'zz_v2_extra.txt').exists()\n"})
    F1 = g.change(w.c["F"], {"implementation/tests/zz_v2_extra.txt": "complement data\n"}, "foreign data file")
    T2 = g.merge(V1, F1, "merge foreign")
    r = w.fpia(T2, w.register(w.c["R0"], [V1], [T2]), options={"lanes": ["V", "T"]})
    assert r["statuses"]["v2_binding"] == "FAIL"
    assert any("outcomes differ" in f["finding"] for f in r["integration_interference"]["findings"])


def test_computation_on_t_status_failure_found(tmp_path):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    T2 = g.change(T, {"implementation/tests/zz_block.txt": "complement file\n"}, "complement blocks C6 status")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]),
               options={"lanes": ["R", "T", "V"], "static_layer": False})
    assert any(f["id"] == "AC-34" for f in r["integration_interference"]["findings"])
    assert r["statuses"]["integration_interference"] == "INTEGRATION_INTERFERENCE_FOUND"


def test_counterfactual_digest_change_found(tmp_path):
    """A complement artefact that changes a Track C digest but not its status (PIW D3-B, FAIL-ONLY)."""
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    T2 = g.change(T, {"implementation/tests/zz_note.txt": "complement note\n"}, "complement note")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]),
               options={"lanes": ["R", "T", "V", "E"], "static_layer": False})
    inter = r["integration_interference"]
    assert any(f["id"] == "COUNTERFACTUAL" for f in inter["findings"])
    assert all(m["rc"] == 0 for m in inter["computations_on_T"])            # status unchanged
    assert r["statuses"]["code_identity"] == "CODE_IDENTITY_DIVERGED" or r["statuses"]["code_identity"] == "CODE_IDENTITY_SAME"
    assert not any(c.get("reproduced") is True and c["reference"] == "R" and "c6" in c["tool"] for c in inter["counterfactual"])
