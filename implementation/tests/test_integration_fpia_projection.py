"""Track C projection: derivation, byte identity, overlays, register attribution, variants and the
projection replay (CDR-014 §5, §8, §9, §13; rv1 #4/rc6; rv2 #3/#4/#7c; first design NC1-NC5)."""
import json

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia_derive as fd

EVL = "implementation/src/investment_system/evl/"


def proj_checks(a):
    return [c for c in a.projection_checks if c["status"] != "PASS"]


def test_derivation_matches_tools_on_W(tmp_path):
    w = tk.variant(tmp_path)
    a = w.audit(w.c["T0"])
    assert a.ref_status == "PASS" and a.shape_error is None
    counts = a.proj.counts()
    assert counts["FROZEN_TOOL"] == 3 and counts["NS_OVERLAY"] == 1 and counts["INFRA_REPLACE"] == 1
    assert counts["SHARED_OVERLAY"] == len(tk.ROOT_OVERLAYS)
    assert a.proj.classes[tk.HANDOFF_HISTORY] == "STRICT"          # c8 protects it although c6/c7 allow it
    for p in tk.IF1 + [tk.LINEAGE]:
        assert a.proj.classes[p] == "STRICT"
    assert a.proj.classes[tk.DR] == "NS_OVERLAY"
    assert a.proj.ns(EVL + "anything.py") and a.proj.ns("implementation/tests/test_evl_c9_x.py")
    assert not a.proj.ns("implementation/src/investment_system/rig/news.py")
    assert not a.proj.ns("implementation/tests/test_other_capability.py")
    assert sorted(a.av) == sorted(["implementation/docs/codex_test/v2/CDR_TEST_APPROVAL.json",
                                   EVL + "superiority_v2.py", "implementation/tests/test_evl_gsup_v2_basic.py",
                                   "implementation/tools/verify_v2_test.py"])


def test_tool_shape_change_not_run(tmp_path):
    w = tk.variant(tmp_path)
    g, R = w.git, w.c["R0"]
    src = g.read(R, tk.C6_PATH).decode().replace("allowed={", "permitted={").replace("p not in allowed]", "p not in permitted]") \
        .replace("for p in allowed:", "for p in permitted:")
    R2 = g.change(R, {tk.C6_PATH: src}, "renamed role")
    G = w.register(R2, [], [R2])
    a = w.audit(R2, G)
    assert a.shape_error, a.result["authority"]["checks"]
    r = w.fpia(R2, G, options={"lanes": []})
    assert r["fpia"]["status"] == "FPIA_NOT_RUN"


TAMPER = ["a_evl_byte_flip", "b_post_anchor_report_edit", "c_if1_drift", "d_tool_allowlist_only_edit",
          "e_mode_change", "f_track_c_test_deleted", "g_symlink_substitution", "h_handoff_history_append"]


@pytest.mark.parametrize("case", TAMPER)
def test_strict_path_tamper(tmp_path, case):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    modes = None
    if case == "a_evl_byte_flip":
        p = EVL + "walkforward.py"
        changes = {p: g.read(T, p).decode().replace("sort_keys=True", "sort_keys=False")}
    elif case == "b_post_anchor_report_edit":
        p = "implementation/reports/track_c_policy_note_2001.md"
        changes = {p: "policy preparation (edited by a foreign capability)\n"}
    elif case == "c_if1_drift":
        changes = {tk.IF1[0]: g.read(T, tk.IF1[0]).decode() + "DRIFT = 1\n"}
    elif case == "d_tool_allowlist_only_edit":
        changes = {tk.C8_PATH: g.read(T, tk.C8_PATH).decode().replace('INFRA = (', 'INFRA = ("x.yml",\n         ')}
    elif case == "e_mode_change":
        p = "implementation/tests/test_evl_c6_basic.py"
        changes, modes = {}, {p: "100755"}
    elif case == "f_track_c_test_deleted":
        changes = {"implementation/tests/test_evl_c7_selection.py": None}
    elif case == "g_symlink_substitution":
        p = "implementation/tests/evl_c7_fixture.py"
        changes, modes = {p: "evl_c7_fixture_copy.py", "implementation/tests/evl_c7_fixture_copy.py": g.read(T, p)}, \
            {p: "120000"}
    else:
        changes = {tk.HANDOFF_HISTORY: g.read(T, tk.HANDOFF_HISTORY).decode() + "- foreign append\n"}
    T2 = g.change(T, changes, "tamper " + case, modes=modes)
    G = w.register(w.c["R0"], [w.c["V0"]], [T2])
    a = w.audit(T2, G)
    assert a.ref_status == "PASS"
    bad = proj_checks(a)
    assert bad and all(c["status"] == "NOT_PRESERVED" for c in bad), (case, bad)


def test_decision_register_foreign_append(tmp_path):
    """T4: a non-V append to the Track C register passes the tools' C8.3 prefix predicate but FAILs FPIA."""
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    body = g.read(T, tk.DR) + b"\n## RIG approval (foreign)\n> approved by another capability\n"
    T4 = g.change(T, {tk.DR: body}, "foreign register append")
    assert body.startswith(g.read(w.c["B8"], tk.DR))          # the frozen tools' C8.3 predicate holds
    G = w.register(w.c["R0"], [w.c["V0"]], [T4])
    a = w.audit(T4, G)
    bad = proj_checks(a)
    assert any(c["id"] == "AC-17" and c["path"] == tk.DR for c in bad)
    r = w.fpia(T4, G, options={"lanes": []})
    assert r["statuses"]["track_c_projection"] == "TRACK_C_PROJECTION_NOT_PRESERVED"


def test_register_v_plus_extra_line(tmp_path):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    T2 = g.change(T, {tk.DR: g.read(w.c["V0"], tk.DR) + b"extra line\n"}, "V register plus a line")
    a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
    assert any(c["id"] == "AC-17" for c in proj_checks(a))


@pytest.mark.parametrize("case", ["a_non_append_edit", "b_X_canonical_order", "c_X_R_first_conflict",
                                  "d_conflict_markers", "e_foreign_append_after_landing"])
def test_shared_overlay(tmp_path, case):
    w = tk.variant(tmp_path)
    g, K, R, V, T = w.git, w.c["K"], w.c["R0"], w.c["V0"], w.c["T0"]
    overlay = tk.ROOT_OVERLAYS[0]
    if case == "a_non_append_edit":
        T2 = g.change(T, {overlay: g.read(T, overlay).decode().replace("canonical entry", "rewritten entry")}, "edit")
    elif case in ("b_X_canonical_order", "c_X_R_first_conflict"):
        X = g.change(K, {overlay: g.read(K, overlay).decode() + "- X capability entry\n"}, "X lands first")
        kx, rx = g.read(X, overlay).decode(), g.read(R, overlay).decode()
        resolved = kx + "- Track C entry\n" if case == "b_X_canonical_order" else rx + "- X capability entry\n"
        T2 = g.merge(X, V, "merge Track C after X", resolve={overlay: resolved})
    elif case == "d_conflict_markers":
        T2 = g.change(T, {overlay: g.read(T, overlay).decode() + "<<<<<<< ours\n- a\n=======\n- b\n>>>>>>> theirs\n"},
                      "markers")
    else:
        T2 = g.change(T, {overlay: g.read(T, overlay).decode() + "- foreign entry after landing\n"}, "append")
    G = w.register(R, [V], [T2])
    a = w.audit(T2, G)
    if case == "e_foreign_append_after_landing":
        assert a.ref_status == "PASS"
        assert not proj_checks(a) and not [c for c in a.provenance_checks if c["status"] != "PASS"]
        return
    if a.ref_status != "PASS":
        assert a.ref_status == "FAIL"
        return
    bad = proj_checks(a) + [c for c in a.provenance_checks if c["status"] != "PASS"]
    assert bad, case
    assert {c["id"] for c in bad} & {"AC-18", "AC-20"}


@pytest.mark.parametrize("case", ["a_case_variant", "b_nfd_variant", "c_complement_symlink", "d_gitlink"])
def test_variant_substitution(tmp_path, case):
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    modes = None
    if case == "a_case_variant":
        changes = {"implementation/src/investment_system/EVL/walkforward.py": "def digest(o):\n    return 'x'\n"}
    elif case == "b_nfd_variant":
        import unicodedata
        nfd = unicodedata.normalize("NFD", tk.NFC_REPORT)
        assert nfd != tk.NFC_REPORT and tk.NFC_REPORT in g.files(T)
        changes = {nfd: "y\n"}
    elif case == "c_complement_symlink":
        changes, modes = {"implementation/tests/zz_link.py": "../src/investment_system/evl/walkforward.py"}, \
            {"implementation/tests/zz_link.py": "120000"}
    else:
        files = g.files(T)
        files["implementation/vendor/sub"] = ("160000", w.c["K"])
        T2 = g.commit(g.tree(files), [T], "gitlink")
        a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
        assert any(f["id"] == "AC-19" for f in a.static_findings)
        return
    T2 = g.change(T, changes, "variant " + case, modes=modes)
    a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
    found = [f for f in a.static_findings if f["id"] in ("AC-19", "AC-21", "AC-24")]
    assert found, (case, a.static_findings)


def test_projection_replay_detects_post_anchor_src_change(tmp_path):
    """NC5b: a protected source change in T makes the unmodified tools at Π diverge from R."""
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    p = EVL + "profile_selection.py"
    T2 = g.change(T, {p: 'STAGES = ("CENTER", "PLATEAU", "EXTRA")\n'}, "post-anchor src change")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["R", "PI"]})
    assert r["statuses"]["track_c_projection"] == "TRACK_C_PROJECTION_NOT_PRESERVED"
    tools = r["track_c_projection"]["projection_replay"]["tools"]
    assert any(t["status"] == "NOT_PRESERVED" for t in tools)


def test_strip_is_path_exact():
    models = {k: fd.ToolModel(v[0], v[1].encode()) for k, v in tk.TOOLS.items()}
    paths = fd.boundary_paths(models)
    assert paths["C6"] == [("boundary_audit",)]
    assert paths["C7"] == [("preservation", "boundary")] and paths["C8_PARTIAL"] == [("preservation", "canonical_boundary")]
    ev = {"tested_head": "h", "boundary_audit": {"tested_head": "h", "merge_base": "m", "ahead": 1, "behind": 0,
                                                 "extra": {"tested_head": "kept"}}, "acceptance": {"tested_head": "kept"}}
    stripped, removed = fd.strip_evidence(ev, paths["C6"])
    assert stripped == {"boundary_audit": {"extra": {"tested_head": "kept"}}, "acceptance": {"tested_head": "kept"}}
    assert sorted(removed) == ["/boundary_audit/ahead", "/boundary_audit/behind", "/boundary_audit/merge_base",
                               "/boundary_audit/tested_head", "/tested_head"]


def test_frozen_record_rewrite(tmp_path):
    """AC-16 / AC-12(d): a Frozen record rewritten in T fails both projection and historical identity."""
    w = tk.variant(tmp_path)
    g, T = w.git, w.c["T0"]
    p = "implementation/reports/track_c_c6_acceptance_2001.json"
    rec = json.loads(g.read(T, p))
    rec["status"] = "REWRITTEN"
    T2 = g.change(T, {p: json.dumps(rec, indent=1)}, "rewrite record")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["E", "R"]})
    assert r["statuses"]["track_c_projection"] == "TRACK_C_PROJECTION_NOT_PRESERVED"
    assert r["statuses"]["historical_frozen_identity"] == "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED"
    assert any(c["id"] == "AC-16" for c in r["historical_frozen_identity"]["checks"])
