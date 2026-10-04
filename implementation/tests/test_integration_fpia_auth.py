"""Reference authentication (CDR-014 §4; rv1 #5/rc7; rv2 #6/rc5; review HIGH #3, #4)."""
import json
import subprocess

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_auth as fauth


def statuses(a):
    return a.auth["status"], [c for c in a.auth["checks"] if c["status"] != "PASS"]


def test_cli_rejects_reference_sha_options(capsys):
    for opt in ("--track-c-ref", "--v2-ref", "--reference", "--deselect-non-track-c"):
        with pytest.raises(SystemExit) as exc:
            fpia.main(["--repo", ".", "--tree", "a", "--register-commit", "b", "--cdr", "c", "--out", "o", opt, "x"])
        assert exc.value.code == 2
    assert "usage error" in capsys.readouterr().err


def test_verification_subject_is_not_a_reference(tmp_path):
    w = tk.variant(tmp_path)
    a = w.audit(w.c["T0"])
    assert a.auth["status"] == "PASS"
    assert a.R == w.c["R0"] and a.Vs == [w.c["V0"]] and w.c["T0"] not in (a.R, *a.Vs)
    manifest = {"cdr": tk.TEST_CDR, "verification_subjects": [{"sha": w.c["T0"], "quoted_as": w.c["T0"][:7]}]}
    G = w.register(w.c["R0"], [], subjects=[w.c["T0"]], manifest=manifest)
    a2 = w.audit(w.c["T0"], G)
    assert a2.auth["status"] == "NOT_RUN" and "R" not in a2.auth


CASES = ["a_prose_only", "b_inside_longer_hex", "c_two_blocks", "d_block_under_other_cdr", "e_not_prefix",
         "f_cdr_mismatch", "g_bad_json"]


@pytest.mark.parametrize("case", CASES)
def test_manifest_reference_rejections(tmp_path, case):
    w = tk.variant(tmp_path)
    R, V, T = w.c["R0"], w.c["V0"], w.c["T0"]
    text = w.register_text(R, [V], [T])
    if case == "a_prose_only":
        text = text.replace('> Track C reference "%s"' % R[:7], '> Track C reference "(see prose)"') \
            + "\nProse mentions %s outside the verbatim lines.\n" % R[:7]
    elif case == "b_inside_longer_hex":
        text = text.replace('"%s"' % R[:7], '"%sabc"' % R[:7], 1)
    elif case == "c_two_blocks":
        block = text[text.index("```fpia-reference-manifest"):]
        text = text + "\n" + block
    elif case == "d_block_under_other_cdr":
        block = text[text.index("```fpia-reference-manifest"):]
        text = text[:text.index("```fpia-reference-manifest")] + "\n## CDR-OTHER · elsewhere\n> other\n\n" + block
    elif case == "e_not_prefix":
        text = text.replace('"quoted_as": "%s"' % R[:7], '"quoted_as": "%s"' % V[:7])
    elif case == "f_cdr_mismatch":
        text = text.replace('"cdr": "%s"' % tk.TEST_CDR, '"cdr": "CDR-ELSE"')
    elif case == "g_bad_json":
        text = text.replace('"track_c_reference"', 'track_c_reference')
    G = w.register(R, [V], text=text)
    a = w.audit(T, G)
    status, bad = statuses(a)
    assert status == "FAIL", (case, a.auth)
    assert any(c["id"] == "AC-02" for c in bad)
    r = w.fpia(T, G)
    assert r["fpia"]["status"] == "FPIA_FAIL"


@pytest.mark.parametrize("case", ["a_side_branch", "b_tip_rewrites_earlier_byte", "c_handoff_ref_deleted",
                                  "d_forged_local_handoff_ref", "e_later_conflicting_manifest"])
def test_register_provenance(tmp_path, case):
    w = tk.variant(tmp_path)
    R, V, T, G0 = w.c["R0"], w.c["V0"], w.c["T0"], w.c["G0"]
    G, remote, expected = G0, str(w.repo), None
    if case == "a_side_branch":
        G = w.register(R, [V], [T], parent=w.c["K"], move_tip=False)
        expected = "FAIL"
    elif case == "b_tip_rewrites_earlier_byte":
        text = w.git.read(G0, tk.REGISTER).decode().replace("nothing here", "nothing  here")
        w.register(R, [V], text=text, parent=G0)
        expected = "FAIL"
    elif case == "c_handoff_ref_deleted":
        w.git("update-ref", "-d", tk.HANDOFF)
        expected = "NOT_RUN"
    elif case == "d_forged_local_handoff_ref":
        # --repo carries a forged remote-tracking handoff ref and a forged register naming a broadened R';
        # FPIA must read the tip from the authority remote, never from --repo.
        forged_R = w.git.change(R, {"implementation/tools/track_c_extra_acceptance_note.md": "x\n"}, "R' forged")
        forged = w.git.change(G0, {tk.REGISTER: w.register_text(forged_R, [V], [T])}, "forged register")
        w.git.ref("refs/remotes/origin/" + fauth.HANDOFF_BRANCH, forged)
        authority = tk.base_world()        # the authority remote (true handoff branch)
        a = w.audit(T, forged, options={"authority_remote": str(authority.repo)})
        assert a.auth["status"] != "PASS"
        assert a.auth.get("R") != forged_R
        return
    elif case == "e_later_conflicting_manifest":
        text = w.git.read(G0, tk.REGISTER).decode() + "\n" + w.register_text(w.c["E8"], [V], [T], cdr="CDR-LATER") \
            .split("\n", 2)[2].replace("## CDR-OLD · earlier\n> nothing here\n\n", "")
        w.register(R, [V], text=text, parent=G0)
        expected = "NOT_RUN"
    a = w.audit(T, G, options={"authority_remote": remote})
    assert a.auth["status"] == expected, (case, a.auth["checks"])


@pytest.mark.parametrize("case", ["a_squash_landing", "b_v_not_descendant_of_r", "c_record_head_not_ancestor",
                                  "d_approval_canonical_mismatch"])
def test_ancestry_failures(tmp_path, case):
    w = tk.variant(tmp_path)
    g, R, V, T = w.git, w.c["R0"], w.c["V0"], w.c["T0"]
    if case == "a_squash_landing":
        squash = g.commit(g("rev-parse", T + "^{tree}"), [w.c["K"]], "squash of T0")
        G = w.register(R, [V], [squash])
        a = w.audit(squash, G)
    elif case == "b_v_not_descendant_of_r":
        Vx = g.change(w.c["E8"], {"implementation/src/investment_system/evl/x.py": "X = 1\n"}, "V' off R")
        G = w.register(R, [Vx], [T])
        a = w.audit(T, G)
    elif case == "c_record_head_not_ancestor":
        stray = g.change(w.c["K"], {"stray.md": "x\n"}, "stray head")
        rec = json.loads(g.read(R, "implementation/reports/track_c_c6_acceptance_2001.json"))
        rec["evidence"]["boundary_audit"]["tested_head"] = stray
        R2 = g.change(R, {"implementation/reports/track_c_c6_acceptance_2001.json": json.dumps(rec)}, "R' bad record")
        G = w.register(R2, [], [R2])
        a = w.audit(R2, G)
    else:
        path = "implementation/reports/track_c_c8_partial_approval_2001.json"
        rec = json.loads(g.read(R, path))
        rec["canonical_head"] = w.c["S6"]
        body = json.dumps(rec, indent=1)
        contracts = "implementation/src/investment_system/evl/calibration_contracts.py"
        src = g.read(R, contracts).decode().replace(tk.fgit.blob_id(g.read(R, path)), tk.fgit.blob_id(body.encode()))
        R2 = g.change(R, {path: body, contracts: src}, "R' approval canonical mismatch")
        G = w.register(R2, [], [R2])
        a = w.audit(R2, G)
    assert a.auth["status"] == "PASS"
    assert a.ref_status == "FAIL", (case, a.result["authority"]["checks"])
    assert any(c["id"] == "AC-04" and c["status"] == "FAIL" for c in a.result["authority"]["checks"])


@pytest.mark.parametrize("case", ["a_admitted_prefix_src", "b_unattributed_literal", "c_canonical_changed",
                                  "d_overlays_extended"])
def test_tool_lineage_broadening(tmp_path, case):
    w = tk.variant(tmp_path)
    g, R = w.git, w.c["R0"]
    c6, c8 = tk.C6_PATH, tk.C8_PATH
    if case == "a_admitted_prefix_src":
        src = g.read(R, c6).decode().replace("or p.startswith('implementation/tools/track_c_'))]",
                                             "or p.startswith('implementation/tools/track_c_')\n"
                                             "             or p.startswith('implementation/src/'))]")
        changes = {c6: src}
    elif case == "b_unattributed_literal":
        src = g.read(R, c8).decode().replace('RUNNER = "', 'RUNNER_EXTRA = ["implementation/docs/ghost.md"]\nRUNNER = "') \
            .replace("p not in GSUP_FILES and p != RUNNER", "p not in GSUP_FILES and p not in RUNNER_EXTRA and p != RUNNER")
        changes = {c8: src}
    elif case == "c_canonical_changed":
        src = g.read(R, c6).decode().replace(w.c["K"], w.c["S6"])
        changes = {c6: src}
    else:
        src = g.read(R, c8).decode().replace('OVERLAYS = (\n', 'OVERLAYS = (\n    "implementation/reports/other.md",\n')
        changes = {c8: src}
    assert changes[next(iter(changes))] != g.read(R, next(iter(changes))).decode()
    R2 = g.change(R, changes, "R' broadened tool " + case)
    G = w.register(R2, [], [R2])
    a = w.audit(R2, G)
    assert a.auth["status"] == "PASS" and a.shape_error is None
    assert a.ref_status == "FAIL", (case, a.result["authority"]["checks"])
    assert any(c["id"] == "AC-07" for c in a.result["authority"]["checks"] if c["status"] == "FAIL")


def test_repo_replace_ref_ignored(tmp_path):
    """--repo has refs/replace substituting R's c6 tool blob; FPIA reads the true object."""
    w = tk.variant(tmp_path)
    g, R = w.git, w.c["R0"]
    true_blob = g("rev-parse", "%s:%s" % (R, tk.C6_PATH))
    fake = g.blob(g.read(R, tk.C6_PATH).decode().replace("canonical advanced", "canonical moved"))
    g("replace", true_blob, fake)
    assert g("for-each-ref", "refs/replace/")
    a = w.audit(w.c["T0"])
    assert a.auth["status"] == "PASS"
    assert a.sb.tree(R)[tk.C6_PATH].sha == true_blob
    assert b"canonical advanced" in a.sb.read(R, tk.C6_PATH)


def test_repo_graft_cannot_fake_ancestry(tmp_path):
    """--repo/info/grafts makes a squash commit appear to have R as parent; AC-04 still FAILs."""
    w = tk.variant(tmp_path)
    g, R, V, T = w.git, w.c["R0"], w.c["V0"], w.c["T0"]
    squash = g.commit(g("rev-parse", T + "^{tree}"), [w.c["K"]], "squash")
    (w.repo / "info").mkdir(exist_ok=True)
    (w.repo / "info" / "grafts").write_text("%s %s %s\n" % (squash, w.c["K"], V))
    g.ref("refs/heads/squash", squash)
    out = subprocess.run(["git", "--git-dir", str(w.repo), "merge-base", "--is-ancestor", R, squash],
                         env=g.env, capture_output=True)
    G = w.register(R, [V], [squash])
    a = w.audit(squash, G)
    assert a.auth["status"] == "PASS"
    assert a.ref_status == "FAIL"
    assert any(c["id"] == "AC-04" and "squash" in c["detail"] for c in a.result["authority"]["checks"])
    assert out.returncode in (0, 1)
