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
    # fix round F3: A_V-type paths in T without V ancestry are a v2 binding FAIL, not NOT_APPLICABLE
    assert r["statuses"]["v2_binding"] == "FAIL"
    assert set(r["v2_binding"]["A_V_paths_in_T"]) >= set(av) and r["v2_binding"]["V_not_ancestor_of_T"] == [V]
    assert all(c["bytes_equal_V"] for c in r["v2_binding"]["checks"])
    assert r["fpia"]["status"] == "FPIA_FAIL"


def test_stale_v2_bytes_without_v_ancestry_fail(tmp_path):
    """F3: T carries a v2-type path (A_V derived from V) whose bytes differ from V, without V ancestry
    (the 0d31e06 shape: stale v2 files of an older head)."""
    w = tk.variant(tmp_path)
    g, R, V = w.git, w.c["R0"], w.c["V0"]
    stale = g.read(V, V2SRC).decode().replace("v * v", "v ** 2")
    T2 = g.merge(g.change(R, {V2SRC: stale}, "stale v2 source"), w.c["F"], "merge foreign")
    G = w.register(R, [V], [T2])
    r = w.fpia(T2, G, options={"lanes": []})
    assert r["statuses"]["v2_binding"] == "FAIL"
    bad = [c for c in r["v2_binding"]["checks"] if c["path"] == V2SRC]
    assert bad and bad[0]["bytes_equal_V"] is False and "also differ" in bad[0]["detail"]
    assert r["fpia"]["status"] == "FPIA_FAIL"


def test_v2_not_applicable_only_without_av_paths(tmp_path):
    """F3: NOT_APPLICABLE only when T has no A_V-type path at all."""
    w = tk.variant(tmp_path)
    T2 = w.git.merge(w.c["R0"], w.c["F"], "Track C plus a foreign capability, no v2")
    G = w.register(w.c["R0"], [w.c["V0"]], [T2])
    r = w.fpia(T2, G, options={"lanes": []})
    assert r["statuses"]["v2_binding"] == "NOT_APPLICABLE"
    assert r["v2_binding"]["checks"] == []


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


WEB_WORKFLOW = """name: web-mvp-validation
on:
  pull_request:
    paths: ['implementation/src/investment_system/product/**', '.github/workflows/web-mvp-validation.yml']
permissions:
  contents: read
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python -m pip install pytest
      - run: PYTHONPATH=src python -m pytest -q
        working-directory: implementation
"""


def test_generic_job_id_collision_is_not_spoof(tmp_path):
    """F5: a Track C-lineage tree plus a Web-chain workflow whose job id is the generic 'validate'
    (equal to the Track C workflow's job id), without V, is not FOUND for that reason alone."""
    w = tk.variant(tmp_path)
    g = w.git
    web = g.change(w.c["K"], {".github/workflows/web-mvp-validation.yml": WEB_WORKFLOW}, "Web chain workflow")
    T2 = g.merge(w.c["R0"], web, "Track C lineage plus the Web chain, without V")
    a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
    assert a.ref_status == "PASS" and a.v_applies[w.c["V0"]] is False
    assert "validate" in tk.fd.parse_workflow(WEB_WORKFLOW)["jobs"]
    assert not findings(a, "AC-32.spoof"), findings(a, "AC-32.spoof")


def test_spoof_named_track_c_found_even_when_carried_by_v(tmp_path):
    """F5: a workflow named like the Track C workflow is spoofing and never attributable, even when it is
    byte-identical to a workflow in V's tree and references an A_V path."""
    w = tk.variant(tmp_path)
    g = w.git
    spoof = ("name: track-c-evl-validation\non:\n  push:\njobs:\n  check:\n    runs-on: ubuntu-latest\n"
             "    steps:\n      - run: python implementation/tools/verify_v2_test.py\n")
    V1 = _v_variant(w, {".github/workflows/zz-spoof.yml": spoof})
    T2 = g.merge(V1, w.c["F"], "merge foreign")
    a = w.audit(T2, w.register(w.c["R0"], [V1], [T2]))
    assert a.ref_status == "PASS" and a.v_applies[V1] is True
    paths = {f["path"] for f in findings(a, "AC-32.spoof")}
    assert ".github/workflows/zz-spoof.yml" in paths


def test_v_whole_tree_does_not_attribute_track_c_runner(tmp_path):
    """F5: attribution is limited to V's Track C additions (workflows carrying A_V content); a V-tree
    workflow that runs Track C tests under its own conditions is FOUND even though its bytes equal V's."""
    w = tk.variant(tmp_path)
    g = w.git
    runner = ("name: other-in-v\non:\n  push:\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n"
              "      - run: cd implementation && python -m pytest -q -p no:randomly tests/test_evl_c8*.py\n")
    V1 = _v_variant(w, {".github/workflows/zz-runner-in-v.yml": runner})
    T2 = g.merge(V1, w.c["F"], "merge foreign")
    a = w.audit(T2, w.register(w.c["R0"], [V1], [T2]))
    assert a.ref_status == "PASS" and a.v_applies[V1] is True
    paths = {f["path"] for f in findings(a, "AC-32.spoof")}
    assert ".github/workflows/zz-runner-in-v.yml" in paths
    # V's own A_V replay workflow stays attributed
    assert ".github/workflows/codex-test-readiness.yml" not in paths


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
