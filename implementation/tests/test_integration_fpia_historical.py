"""Historical Frozen identity: content-derived Frozen universe (tools, records, CI-log evidence lines,
code-referenced approvals) and exact-tree replay at each evidence head (CDR-014 §3, §10; rv2 #5/rc4;
review HIGH #1; stop condition S1 / latent L5: no normalisation)."""
import json

import pytest

from tests import integration_fpia_testkit as tk

REPORTS = "implementation/reports/"


def new_reference(w, changes, msg):
    R2 = w.git.change(w.c["R0"], changes, msg)
    return R2, w.register(R2, [], [R2])


@pytest.mark.parametrize("case", ["a_c9_tool", "b_c9_record", "c_workflow_invokes_missing_tool",
                                  "d_validation_record_unbound_key", "e_ci_log_line_unbound_head",
                                  "f_unpinned_approval_literal"])
def test_unknown_frozen_universe_not_run(tmp_path, case):
    w = tk.variant(tmp_path)
    g, R = w.git, w.c["R0"]
    static = True
    if case == "a_c9_tool":
        wf = g.read(R, tk.WORKFLOW).decode() + "      - name: C9\n        run: PYTHONPATH=src:. python tools/track_c_c9_acceptance.py\n"
        changes = {"implementation/tools/track_c_c9_acceptance.py": g.read(R, tk.C6_PATH), tk.WORKFLOW: wf}
    elif case == "b_c9_record":
        changes = {REPORTS + "track_c_c9_acceptance_2001.json":
                   json.dumps({"tested_head": w.c["E8"], "evidence": {"tested_head": w.c["E8"], "c9": "PASS"}})}
        static = False
    elif case == "c_workflow_invokes_missing_tool":
        wf = g.read(R, tk.WORKFLOW).decode() + "      - name: C8 full\n        run: PYTHONPATH=src:. python tools/track_c_c8_acceptance.py\n"
        changes = {tk.WORKFLOW: wf}
    elif case == "d_validation_record_unbound_key":
        changes = {REPORTS + "track_c_c9_validation_2001.json":
                   json.dumps({"tested_head": w.c["E6b"], "actual_C9_evidence": {"boundary_audit": {"tested_head": w.c["E6b"]},
                                                                                   "c9_key": 1}})}
        static = False
    elif case == "e_ci_log_line_unbound_head":
        changes = {REPORTS + "track_c_c9_ci_log_2001.txt":
                   tk.logline(1, 'TRACK_C_C9_EVIDENCE=' + json.dumps({"tested_head": w.c["E8"]})) + "\n"}
        static = False
    else:
        evl = "implementation/src/investment_system/evl/"
        changes = {REPORTS + "track_c_c9_approval_2001.json": "{}\n",
                   evl + "c9_policy.py": "from pathlib import Path\nAPPROVAL = Path(__file__).resolve().parents[3] / "
                                         "'reports' / 'track_c_c9_approval_2001.json'\n"}
    R2, G = new_reference(w, changes, "R' " + case)
    a = w.audit(R2, G)
    assert a.auth["status"] == "PASS"
    if static:
        assert a.shape_error or a.ref_status == "NOT_RUN", (case, a.result["authority"]["checks"])
        r = w.fpia(R2, G, options={"lanes": []})
        assert r["fpia"]["status"] == "FPIA_NOT_RUN"
    else:
        r = w.fpia(R2, G, options={"lanes": ["E", "R"]})
        assert r["statuses"]["historical_frozen_identity"] == "NOT_RUN", r["historical_frozen_identity"]["checks"]
        assert r["fpia"]["status"] != "FPIA_PASS"


@pytest.mark.parametrize("case", ["a_record_hash_differs", "b_logged_line_one_char", "c_raw_log_sha256",
                                  "e_replay_rc_nonzero"])
def test_historical_mismatch(tmp_path, case):
    w = tk.variant(tmp_path)
    g, R = w.git, w.c["R0"]
    if case == "a_record_hash_differs":
        p = REPORTS + "track_c_c6_acceptance_2001.json"
        rec = json.loads(g.read(R, p))
        rec["evidence"]["acceptance_hash"] = "0" * 64
        changes = {p: json.dumps(rec, indent=1)}
    elif case == "b_logged_line_one_char":
        p = REPORTS + "track_c_c7_acceptance_ci_log_2001.txt"
        changes = {p: g.read(R, p).decode().replace('"official":false', '"official":true', 1)}
    elif case == "c_raw_log_sha256":
        p = REPORTS + "track_c_c8_partial_foundation_verification_2001.json"
        rec = json.loads(g.read(R, p))
        rec["actions"]["raw_log_sha256"] = "f" * 64
        changes = {p: json.dumps(rec, indent=1)}
    else:
        bad = g.change(R, {"stray_root_file.txt": "outside authorized Track C\n"}, "E_bad")
        line = tk.logline(1, "TRACK_C_C6_EVIDENCE=" + json.dumps({"boundary_audit": {"tested_head": bad}}))
        R2 = g.change(bad, {REPORTS + "track_c_c6_extra_ci_log_2001.txt": line + "\n"}, "R' claims evidence at E_bad")
        G = w.register(R2, [], [R2])
        r = w.fpia(R2, G, options={"lanes": ["E"]})
        checks = r["historical_frozen_identity"]["checks"]
        assert any(c["status"] == "NOT_PRESERVED" and c.get("head") == bad and "rc" in c["detail"] for c in checks), checks
        assert r["statuses"]["historical_frozen_identity"] == "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED"
        return
    R2, G = new_reference(w, changes, "R' " + case)
    r = w.fpia(R2, G, options={"lanes": ["E", "R"]})
    assert r["statuses"]["historical_frozen_identity"] == "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED", \
        r["historical_frozen_identity"]["checks"]


def test_exact_replay_reproduces_records(tmp_path):
    w = tk.base_world()
    r = w.fpia(w.c["T0"], options={"lanes": ["E", "R"]})
    assert r["statuses"]["historical_frozen_identity"] == "HISTORICAL_FROZEN_IDENTITY_PRESERVED", \
        r["historical_frozen_identity"]["checks"]
    heads = r["derivation"]["frozen_universe"]["replay_heads"]
    assert sorted(heads) == sorted([w.c["E6"], w.c["E6b"], w.c["E7"], w.c["E8"]])
    claims = [c["claim"] for c in r["equality_claims"] if c["source"] == "EXACT_CONDITION_REPLAY_UNMODIFIED_TOOL"]
    assert len([c for c in claims if c.startswith("logged evidence line")]) == 7
    assert any("track_c_policy_preparation_validation_2001.json" in c for c in claims)   # 'validation' record replayed
    assert any("verification record" in c for c in claims)
    for E, rep in r["historical_frozen_identity"]["replays"].items():
        assert all(t["rc"] == 0 for t in rep["tools"])
        assert rep["canonical_ref_pinned_to"] == w.c["K"]


def test_approvals_bound_by_code_pin(tmp_path):
    w = tk.base_world()
    a = w.audit(w.c["T0"])
    approvals = a.frozen["approvals"]
    assert approvals and all(x["code_pinned"] for x in approvals)
    assert {x["path"] for x in approvals} == {REPORTS + "track_c_c8_partial_approval_2001.json"}
