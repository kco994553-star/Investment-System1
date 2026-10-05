"""Fix round 2 (CDR-014 §14): AC-32.spoof read with YAML and normalised names (G1), what complement
workflows run resolved through YAML decoding, working-directory, shell tokens, local scripts, composite
actions and pytest selections (G2), structural fetch-rejection parsing (G3), --out refusal and the
side-file verifier (G4), result_sha256 independent of the interpreter/venv location (G5), AC-04
wording (G6), the PR trigger scope (G7) and authority transport disclosure (F2).

Every adversarial probe of the previous verification round is pinned here with its expected
component/status: S0-S19, S21, S24 (spoof workflows), F1-E5 (a ref named like "rejected") and the
F4 --out reuse. Open user decisions are pinned as current behaviour, not decided: D3-b (a job id/name
collision alone is a note, S17) and D3-c (dynamically constructed invocations are NOT_CLAIMED, S15/S16).
Fix round 3 (H1/H2) changed the reason texts pinned here (identity keys, mention-based detection) and S15,
whose string-built path names the C6 tool literally, is now found by the mention rule (see
test_integration_fpia_fix3.py); no other expectation changed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_git as fgit
from tools.integration import track_c_fpia_workflows as fw

C6 = tk.C6_PATH                                   # implementation/tools/<C6 tool>
C6_NAME = C6.rsplit("/", 1)[1]
WF = ".github/workflows/"


def _wf(name_line, job="check", steps=("      - run: echo ok",), extra_job=()):
    lines = ([name_line] if name_line is not None else []) + ["on: [push]", "jobs:", "  %s:" % job] + list(extra_job) + \
            ["    runs-on: ubuntu-latest", "    steps:"] + list(steps)
    return "\n".join(lines) + "\n"


def _wd(wd):
    return ["    defaults:", "      run:", "        working-directory: %s" % wd]


# (probe id, files added to T0, expected static findings {(id, path)}, expected reason fragment or None)
PROBES = [
    ("S0_name_exact", {WF + "probe-a.yml": _wf("name: track-c-evl-validation")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S1_name_comment", {WF + "probe-a.yml": _wf("name: track-c-evl-validation # same name, YAML comment")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S2_name_nextline", {WF + "probe-a.yml": _wf("name:\n  track-c-evl-validation")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S3_name_quotedkey", {WF + "probe-a.yml": _wf('"name": track-c-evl-validation')},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S4_name_tag", {WF + "probe-a.yml": _wf("name: !!str track-c-evl-validation")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S5_name_case", {WF + "probe-a.yml": _wf("name: Track-C-EVL-Validation")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S6_name_homoglyph", {WF + "probe-a.yml": _wf("name: track-c-evl-validat\u0456on")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S7_name_zwsp", {WF + "probe-a.yml": _wf("name: track-c-evl-validation\u200b")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S8_noname_samefile", {WF + "track-c-evl-validation.yaml": _wf(None)},
     {("AC-32.spoof", WF + "track-c-evl-validation.yaml")}, "filename stem"),
    ("S8b_case_filename", {WF + "Track-C-EVL-Validation.yml": _wf(None)},
     {("AC-32.spoof", WF + "Track-C-EVL-Validation.yml"), ("AC-19", WF + "Track-C-EVL-Validation.yml")},
     "filename stem"),
    ("S9_indirect_sh", {WF + "probe-a.yml": _wf("name: probe", steps=["      - run: bash scripts/ci_probe.sh"]),
                        "scripts/ci_probe.sh": "cd implementation && PYTHONPATH=src:. python tools/%s\n" % C6_NAME},
     {("AC-32.spoof", WF + "probe-a.yml")}, "via scripts/ci_probe.sh"),
    ("S10_wd_tools", {WF + "probe-a.yml": _wf("name: probe", extra_job=_wd("implementation/tools"),
                                              steps=["      - run: PYTHONPATH=../src:.. python %s" % C6_NAME])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "mentions Track C scope: tool " + C6_NAME),
    ("S11_shell_quote", {WF + "probe-a.yml": _wf("name: probe", steps=[
        '      - run: PYTHONPATH=implementation/src:implementation python implementation/too"ls"/%s' % C6_NAME])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "names a Track C file: " + C6),
    ("S12_yaml_escape", {WF + "probe-a.yml": _wf("name: probe", steps=[
        '      - run: "python implementation\\x2Ftools\\x2F%s"' % C6_NAME])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "names a Track C file: " + C6),
    ("S13_pytest_k", {WF + "probe-a.yml": _wf("name: probe", extra_job=_wd("implementation"),
                                              steps=["      - run: PYTHONPATH=src python -m pytest -q -k evl_c6"])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "selects Track C tests: -k evl_c6"),
    ("S14_control_direct", {WF + "probe-a.yml": _wf("name: probe", extra_job=_wd("implementation"),
                                                    steps=["      - run: PYTHONPATH=src:. python tools/%s" % C6_NAME])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "names a Track C file: " + C6),
    # D3-c (open user decision): dynamically constructed invocations are NOT_CLAIMED. Fix round 3: S15's
    # string-built path still names the C6 tool's basename literally, so the mention rule (H2) finds it as a
    # side effect (pinned as current behaviour; no detection claim). S16's computed module name stays
    # not found.
    ("S15_indirect_py", {WF + "probe-a.yml": _wf("name: probe", steps=["      - run: python scripts/probe_runner.py"]),
                         "scripts/probe_runner.py": 'import subprocess, sys\nsubprocess.run([sys.executable, '
                                                    '"implementation/tools/" + "%s"], check=True)\n' % C6_NAME},
     {("AC-32.spoof", WF + "probe-a.yml")}, "mentions Track C scope"),
    ("S16_dyn_import", {WF + "probe-a.yml": _wf("name: probe", steps=[
        "      - run: PYTHONPATH=implementation/src python scripts/dyn.py"]),
                        "scripts/dyn.py": 'import importlib\nm = importlib.import_module("investment_system." + '
                                          '"evl.walkforward")\nprint(m)\n'},
     set(), None),
    # D3-b (open user decision): a job id/name collision alone stays a note - pinned as not found
    ("S17_job_collision", {WF + "probe-a.yml": _wf("name: probe", job="validate", extra_job=["    name: validate"])},
     set(), None),
    ("S18_comment_plus_validate", {WF + "probe-a.yml": _wf("name: track-c-evl-validation # same name", job="validate")},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
    ("S19_escape_plus_validate", {WF + "probe-a.yml": _wf("name: probe", job="validate", steps=[
        '      - run: "python implementation\\x2Ftools\\x2F%s"' % C6_NAME])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "names a Track C file: " + C6),
    ("S21_composite_action", {WF + "probe-a.yml": _wf("name: probe", steps=["      - uses: actions/checkout@v4",
                                                                            "      - uses: ./.github/actions/tc"]),
                              ".github/actions/tc/action.yml": "name: tc\nruns:\n  using: composite\n  steps:\n    - run: "
                              "PYTHONPATH=implementation/src:implementation python %s\n      shell: bash\n" % C6},
     {("AC-32.spoof", WF + "probe-a.yml")}, "via .github/actions/tc/action.yml"),
    ("S24_combined_spoof", {WF + "probe-a.yml": _wf("name: track-c-evl-validation # spoof", job="validate", steps=[
        "      - uses: actions/checkout@v4",
        '      - run: "PYTHONPATH=implementation/src:implementation python implementation\\x2Ftools\\x2F%s"' % C6_NAME])},
     {("AC-32.spoof", WF + "probe-a.yml")}, "workflow name claims the Track C identity"),
]


@pytest.fixture(scope="module")
def probe_world(tmp_path_factory):
    return tk.variant(tmp_path_factory.mktemp("fix2-probes"))


def _audit(w, changes, msg="probe"):
    T2 = w.git.change(w.c["T0"], changes, msg)
    return w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2])), T2


@pytest.mark.parametrize("probe,changes,expected,fragment", PROBES, ids=[p[0] for p in PROBES])
def test_adversarial_spoof_probe_pinned(probe_world, probe, changes, expected, fragment):
    a, _ = _audit(probe_world, changes, probe)
    assert a.ref_status == "PASS" and a.v_applies[probe_world.c["V0"]] is True
    got = {(f["id"], f.get("path")) for f in a.static_findings}
    assert got == expected, (probe, a.static_findings)
    if fragment:
        spoof = [f for f in a.static_findings if f["id"] == "AC-32.spoof"][0]
        assert any(fragment in r for r in spoof["reasons"]), spoof
    ii = a.result["integration_interference"]
    assert ii["dynamic_invocation_detection"] == "NOT_CLAIMED"
    assert ii["static_not_run"] == []


def test_s17_s18_s19_collision_is_a_note_only(probe_world):
    """D3-b pinned: the collision with the Track C job id 'validate' is a note on a real finding only."""
    a, _ = _audit(probe_world, dict(PROBES[[p[0] for p in PROBES].index("S18_comment_plus_validate")][1]), "S18")
    spoof = [f for f in a.static_findings if f["id"] == "AC-32.spoof"][0]
    assert spoof["job_id_collision_note"] == ["validate"]
    a17, _ = _audit(probe_world, dict(PROBES[[p[0] for p in PROBES].index("S17_job_collision")][1]), "S17")
    assert a17.static_findings == []
    assert fw.JOB_COLLISION_POLICY in json.dumps(a17.result["integration_interference"]["workflow_analysis"])


def test_s24_end_to_end_component_status(tmp_path):
    """S24 (previous round: full CLI audit FPIA_PASS / INTEGRATION_INTERFERENCE_NONE) now gives
    INTEGRATION_INTERFERENCE_FOUND and FPIA_FAIL."""
    w = tk.variant(tmp_path)
    changes = dict(PROBES[[p[0] for p in PROBES].index("S24_combined_spoof")][1])
    T2 = w.git.change(w.c["T0"], changes, "S24")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": []})
    assert r["statuses"]["integration_interference"] == "INTEGRATION_INTERFERENCE_FOUND"
    assert r["fpia"]["status"] == "FPIA_FAIL"
    assert any("integration_interference INTEGRATION_INTERFERENCE_FOUND" in x for x in r["fpia"]["reasons"])
    assert r["integration_interference"]["dynamic_invocation_detection"] == "NOT_CLAIMED"
    assert fw.DYNAMIC_NON_CLAIM in r["non_claims"]


# ---- G1: YAML-equivalent identity ---------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "name: TRACK-C-EVL-VALIDATION",                       # case (N1)
    "name: track-c-evI-validation",                       # capital I for l (UTS #39 skeleton, N2)
    "name: \uff54\uff52\uff41\uff43\uff4b-c-evl-validation",  # fullwidth (NFKC)
    "name: track-c-ev\u2060l-validation",                  # word joiner (default ignorable)
    "name: 'track-c-evl-validation'",
    "name: |\n  track-c-evl-validation",
    "run-name: track-c-evl-validation\nname: other",
    "name: other\nname: track-c-evl-validation",          # duplicate keys: every value is considered
    "x: &n track-c-evl-validation\nname: *n",             # alias
])
def test_yaml_equivalent_name_claims_found(probe_world, text):
    a, _ = _audit(probe_world, {WF + "probe-n.yml": _wf(text)}, "name variant")
    assert [f["path"] for f in a.static_findings if f["id"] == "AC-32.spoof"] == [WF + "probe-n.yml"], text


def test_unparseable_workflow_fail_closed(probe_world):
    bad = {WF + "probe-bad.yml": "name: probe\non: [push\njobs: {}\n", WF + "probe-nojobs.yml": "name: probe\non: [push]\n",
           WF + "probe-list.yml": "- just\n- a list\n"}
    a, _ = _audit(probe_world, bad, "unparseable")
    found = {f["path"]: f["reasons"] for f in a.static_findings if f["id"] == "AC-32.spoof"}
    assert set(found) == set(bad)
    assert all(any(r.startswith("unparseable workflow") for r in rs) for rs in found.values())


def test_byte_identical_track_c_workflow_copy_is_not_a_claim(probe_world):
    """'unless it is byte-identical to the authenticated R/V Track C workflow'."""
    w = probe_world
    data = w.git.read(w.c["V0"], tk.WORKFLOW)
    a, _ = _audit(w, {WF + "track-c-evl-validation.yaml": data}, "identical copy")
    assert [f for f in a.static_findings if f["id"] == "AC-32.spoof"] == []
    notes = a.result["integration_interference"]["workflow_analysis"]["notes"]
    assert {"path": WF + "track-c-evl-validation.yaml",
            "notes": ["byte-identical to the authenticated Track C workflow"]} in notes
    # one changed byte makes it a claim again
    a2, _ = _audit(w, {WF + "track-c-evl-validation.yaml": data + b"\n"}, "changed copy")
    assert [f["path"] for f in a2.static_findings if f["id"] == "AC-32.spoof"] == [WF + "track-c-evl-validation.yaml"]


def test_normalisation_helpers_and_confusable_source():
    assert fw.same_name("Track-C-EVL-Validation", "track-c-evl-validation") == "N1"
    assert fw.same_name("track-c-evI-validation", "track-c-evl-validation") == "N2"
    assert fw.same_name("track-c-evl-validat\u0456on", "track-c-evl-validation") == "N1"
    assert fw.same_name("web-mvp-validation", "track-c-evl-validation") is None
    assert fw.same_name("track-c-fpia", "track-c-evl-validation") is None
    assert fw.is_default_ignorable("\u200b") and fw.is_default_ignorable("\ufeff") and not fw.is_default_ignorable("a")
    assert fw.CONFUSABLE_SOURCE["runtime_download"] is False and "UTS #39" in fw.CONFUSABLE_SOURCE["table"]
    assert fw.loader_info()["version"]


def test_yaml_loader_unavailable_is_not_run(tmp_path, monkeypatch):
    """Fail-closed: without a YAML loader the workflow analysis is NOT_RUN, never NONE."""
    w = tk.variant(tmp_path)
    monkeypatch.setattr(fw, "yaml", None)
    r = w.fpia(w.c["T0"], options={"lanes": []})
    ii = r["integration_interference"]
    assert any("YAML loader" in x for x in ii["static_not_run"]), ii["static_not_run"]
    assert ii["workflow_analysis"]["status"] == "NOT_RUN"
    assert r["statuses"]["integration_interference"] == "NOT_RUN"
    assert any("YAML loader" in x for x in ii["not_run"])


# ---- G2: what a complement workflow runs ----------------------------------------------------------------
G2_FOUND = [
    ("node_id", _wf("name: probe", extra_job=_wd("implementation"),
                    steps=["      - run: python -m pytest -q tests/test_evl_c6_basic.py::test_c6_acceptance"]), {},
     "names a Track C file: implementation/tests/test_evl_c6_basic.py"),
    ("track_c_dir_glob", _wf("name: probe", extra_job=_wd("implementation"),
                             steps=["      - run: python -m pytest tests/test_evl_c[0-9]*.py tests/test_other_capability.py"]),
     {}, "glob matches Track C paths: tests/test_evl_c[0-9]*.py"),
    ("k_function_name", _wf("name: probe", extra_job=_wd("implementation"),
                            steps=["      - run: python -m pytest -q tests -k holdout_boundary"]), {},
     "selects Track C tests: -k holdout_boundary"),
    ("reusable_workflow", _wf("name: probe", steps=["      - run: echo ok"]).replace(
        "  check:\n", "  call:\n    uses: ./.github/workflows/zz-reusable.yml\n  check:\n"),
     {WF + "zz-reusable.yml": "name: zz\non: [workflow_call]\njobs:\n  r:\n    runs-on: ubuntu-latest\n    steps:\n"
                              "      - run: cd implementation && python tools/%s\n" % C6_NAME},
     "via .github/workflows/zz-reusable.yml"),
    ("python_argv_list", _wf("name: probe", steps=["      - run: python scripts/runner.py"]),
     {"scripts/runner.py": "import subprocess, sys\nsubprocess.run([sys.executable, %r], check=True)\n" % C6},
     "via scripts/runner.py"),
    ("inline_python_import", _wf("name: probe", steps=[
        "      - run: PYTHONPATH=implementation/src python -c 'import investment_system.evl.walkforward'"]), {},
     "imports Track C modules"),
    ("heredoc_python", _wf("name: probe", steps=["      - run: |", "          python - <<'PY'",
                                                 "          import subprocess",
                                                 "          subprocess.run(['python', '%s'])" % C6, "          PY"]), {},
     "names a Track C file: " + C6),
    ("script_cycle", _wf("name: probe", steps=["      - run: bash scripts/a.sh"]),
     {"scripts/a.sh": "bash scripts/b.sh\n", "scripts/b.sh": "bash scripts/a.sh\npython %s\n" % C6},
     "via scripts/b.sh"),
    ("with_input", _wf("name: probe", steps=["      - uses: some/action@v1", "        with:",
                                             "          script: python %s" % C6]), {},
     "names a Track C file: " + C6),
    ("python_m_module", _wf("name: probe", extra_job=_wd("implementation"),
                            steps=["      - run: python -m tools.%s" % C6_NAME[:-3]]), {},
     "runs a Track C module: -m tools." + C6_NAME[:-3]),
    ("workspace_prefix", _wf("name: probe", steps=["      - run: python ${{ github.workspace }}/%s" % C6]), {},
     "names a Track C file: " + C6),
]


@pytest.mark.parametrize("case,text,extra,fragment", G2_FOUND, ids=[c[0] for c in G2_FOUND])
def test_complement_workflow_running_track_c_found(probe_world, case, text, extra, fragment):
    a, _ = _audit(probe_world, dict({WF + "probe-g2.yml": text}, **extra), case)
    spoof = [f for f in a.static_findings if f["id"] == "AC-32.spoof" and f["path"] == WF + "probe-g2.yml"]
    assert spoof, (case, a.static_findings)
    assert any(fragment in r for r in spoof[0]["reasons"]), spoof[0]


@pytest.mark.parametrize("cmd,wd", [("python -m pytest -q", "implementation"), ("python -m pytest -q tests", "implementation"),
                                    ("cd implementation && PYTHONPATH=src python -m pytest -q", None),
                                    ("python tools/mini_suite.py", "implementation")])
def test_whole_suite_run_is_a_note_not_a_spoof(probe_world, cmd, wd):
    extra = {"implementation/tools/mini_suite.py": "import subprocess, sys\n"
                                                   "subprocess.run([sys.executable, '-m', 'pytest', '-q'])\n"}
    text = _wf("name: other-capability", extra_job=_wd(wd) if wd else (), steps=["      - run: " + cmd])
    a, _ = _audit(probe_world, dict({WF + "probe-suite.yml": text}, **extra), "whole suite")
    assert [f for f in a.static_findings if f["id"] == "AC-32.spoof"] == [], a.static_findings
    notes = [n for n in a.result["integration_interference"]["workflow_analysis"]["notes"]
             if n["path"] == WF + "probe-suite.yml"]
    assert notes and any("whole pytest suite" in x for x in notes[0]["notes"])


def test_other_capability_selection_is_not_a_spoof(probe_world):
    text = _wf("name: rig", extra_job=_wd("implementation"),
               steps=["      - run: PYTHONPATH=src python -m pytest -q tests/test_rig_news.py -k headline"])
    a, _ = _audit(probe_world, {WF + "probe-rig.yml": text}, "rig selection")
    assert a.static_findings == []


# ---- G3: fetch status lines parsed structurally -----------------------------------------------------------
def test_rejected_lines_structural():
    benign = "\n".join([
        "From file:///x",
        " * [new branch]      feature/rejected-ideas -> refs/fpia/src/heads/feature/rejected-ideas",
        " * [new tag]         Rejected   -> refs/fpia/src/tags/Rejected",
        " + 1234567...89abcde rejected/x -> refs/y/rejected/x  (forced update)",
        "   1234567..89abcde  x(rejected) -> refs/x(rejected)",
        " = [up to date]      rejected  -> refs/rejected",
        "hint: rejected", "remote: rejected"])
    assert fgit.rejected_lines(benign) == []
    real = [" ! [rejected]        main       -> refs/fpia/src/heads/main  (non-fast-forward)",
            " ! 1234567..89abcde  dev        -> refs/fpia/src/heads/dev  (unable to update local ref)",
            "   1234567..89abcde  ok         -> refs/ok  (rejected by policy)",
            "warning: rejected refs/heads/x because shallow roots are not allowed to be updated",
            "error: cannot lock ref 'refs/x'"]
    assert fgit.rejected_lines("\n".join(real)) == [x.strip() for x in real]


def test_branch_named_rejected_is_not_a_fetch_rejection(tmp_path):
    """F1-E5 pinned: a caller branch feature/rejected-ideas (and a tag Rejected) must not make FPIA
    NOT_RUN; the previous round gave AC-01 NOT_RUN."""
    w = tk.variant(tmp_path)
    w.git.ref("refs/heads/feature/rejected-ideas", w.c["T0"])
    w.git.ref("refs/tags/Rejected", w.c["T0"])
    sb = fgit.Sandbox(tmp_path / "sb")
    sb.fetch(str(w.repo), ["+refs/heads/*:refs/fpia/src/heads/*", "+refs/tags/*:refs/fpia/src/tags/*"], label="caller-repo")
    assert sb.fetch_log[-1]["rejected"] == []
    r = w.fpia(w.c["T0"], options={"lanes": []})
    assert r["statuses"]["authority"] == "PASS", r["authority"]
    assert r["environment"]["caller_repository"]["status"] == "PASS"


def test_real_rejection_at_exit_zero_still_not_run(tmp_path, monkeypatch):
    """A '!' status line with exit 0 still raises (fail-closed)."""
    w = tk.variant(tmp_path)
    sb = fgit.Sandbox(tmp_path / "sb")
    real_run = fgit.Sandbox.run

    def fake_run(self, args, **kw):
        proc = real_run(self, args, **kw)
        if "fetch" in args:
            proc = subprocess.CompletedProcess(proc.args, 0, proc.stdout, proc.stderr +
                                               b" ! [rejected]        main -> refs/fpia/src/heads/main  (non-fast-forward)\n")
        return proc

    monkeypatch.setattr(fgit.Sandbox, "run", fake_run)
    with pytest.raises(fgit.GitError, match="rejected"):
        sb.fetch(str(w.repo), ["+refs/heads/*:refs/fpia/src/heads/*"], label="caller-repo")


# ---- G4: --out refusal and the side-file verifier ---------------------------------------------------------
def _side_run(w, tmp_path, name):
    out = tmp_path / name / "fpia.json"
    out.parent.mkdir(parents=True)
    d = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]}, out=str(out), doc=True, work=tmp_path / ("w" + name))
    return out, d


def test_out_reuse_refused_never_stale_side_files(tmp_path):
    """F4 reuse pinned: a second run with the same --out (previous round: a NOT_RUN JSON written next to
    six stale side files) is refused - nothing is written and nothing is run."""
    w = tk.base_world()
    out, d = _side_run(w, tmp_path, "a")
    vdir = Path(str(out) + fpia.VERBATIM_DIR_SUFFIX)
    before = {p.name: p.read_bytes() for p in vdir.iterdir()}
    json_before = out.read_bytes()
    assert before and d["run"]["verbatim_files"] == sorted(before)
    shallow = w.shallow_clone(tmp_path / "shallow.git")
    d2 = fpia.run_fpia(str(shallow), w.c["T0"], w.c["G0"], tk.TEST_CDR, out=str(out), work_dir=str(tmp_path / "w2"),
                       options={"authority_remote": str(w.repo), "require_clean_verifier": False})
    assert d2["result"]["fpia"]["status"] == "FPIA_NOT_RUN" and d2["run"]["written"] is False
    assert "output refused" in d2["result"]["fpia"]["reasons"][0]
    assert out.read_bytes() == json_before
    assert {p.name: p.read_bytes() for p in vdir.iterdir()} == before
    assert not (tmp_path / "w2").exists()
    # a stale side-file directory alone is refused too
    out3 = tmp_path / "c" / "fpia.json"
    stale = Path(str(out3) + fpia.VERBATIM_DIR_SUFFIX)
    stale.mkdir(parents=True)
    (stale / "07-x.stderr").write_text("stale\n")
    assert "side-file directory" in fpia.output_preflight(str(out3))
    assert fpia.main(["--repo", str(w.repo), "--tree", w.c["T0"], "--register-commit", w.c["G0"], "--cdr",
                      tk.TEST_CDR, "--out", str(out3)]) == 2
    assert not out3.exists()
    # an empty existing --out and an empty side-file directory are accepted
    out4 = tmp_path / "d" / "fpia.json"
    Path(str(out4) + fpia.VERBATIM_DIR_SUFFIX).mkdir(parents=True)
    out4.write_text("")
    assert fpia.output_preflight(str(out4)) is None


def test_verify_output_detects_tampering(tmp_path, capsys):
    """F4 T0-T4 pinned against the shipped verifier (previous round: no verifier shipped)."""
    w = tk.base_world()
    out, d = _side_run(w, tmp_path, "v")
    vdir = Path(str(out) + fpia.VERBATIM_DIR_SUFFIX)
    status, rep = fpia.verify_output(str(out), d["result_sha256"])
    assert status == "VERIFIED" and rep["side_files"] == len(d["run"]["verbatim_files"]) > 0
    assert fpia.main(["--verify-output", str(out), "--expect-result-sha256", d["result_sha256"]]) == 0
    files = sorted(vdir.iterdir())
    # T1 one byte flipped
    data = files[0].read_bytes()
    files[0].write_bytes((data[:-1] + bytes([data[-1] ^ 1])) if data else b"x")
    assert fpia.verify_output(str(out))[0] == "MISMATCH"
    assert fpia.main(["--verify-output", str(out)]) == 1
    files[0].write_bytes(data)
    # T2 two side files swapped
    x, y = files[0].read_bytes(), files[1].read_bytes()
    if x != y:
        files[0].write_bytes(y)
        files[1].write_bytes(x)
        assert fpia.verify_output(str(out))[0] == "MISMATCH"
        files[0].write_bytes(x)
        files[1].write_bytes(y)
    # T3 an unreferenced extra file
    (vdir / "99-extra.stderr").write_text("x\n")
    st, rep = fpia.verify_output(str(out))
    assert st == "MISMATCH" and any(c.get("unreferenced") == ["99-extra.stderr"] for c in rep["checks"])
    (vdir / "99-extra.stderr").unlink()
    # T4 a consistent forgery passes self-verification and is caught only by the external anchor
    doc = json.loads(out.read_text())
    step = [s for s in doc["result"]["frozen_tools_on_T"]["steps"] if s.get("verbatim")][0]
    forged = b"forged\n"
    (vdir / step["verbatim"]["stderr"]["file"]).write_bytes(forged)
    step["verbatim"]["stderr"].update(sha256=hashlib.sha256(forged).hexdigest(), bytes=len(forged))
    doc["result_sha256"] = fpia.sha256(fpia.canonical_bytes(doc["result"]))
    out.write_text(json.dumps(doc))
    assert fpia.verify_output(str(out))[0] == "VERIFIED"
    assert fpia.verify_output(str(out), d["result_sha256"])[0] == "MISMATCH"
    # unreadable output
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    assert fpia.verify_output(str(bad))[0] == "NOT_RUN"
    assert fpia.main(["--verify-output", str(bad)]) == 2
    capsys.readouterr()


# ---- G5: result_sha256 independent of the interpreter / venv location ---------------------------------------
def test_env_paths_scrubbed_to_tokens():
    tokens = fpia.path_token_record()
    assert "<python>" in tokens and "<site-packages>" in tokens and "<stdlib>" in tokens
    py = sys.executable
    assert fpia.normalise_env_paths(py) == "<python>"
    assert fpia.normalise_env_paths(py + "3.99") != "<python>3.99"            # path boundary respected
    site = tokens["<site-packages>"][0]
    assert fpia.normalise_env_paths(site + "/x.pth") == "<site-packages>/x.pth"
    assert fpia.normalise_env_paths(os.fsencode(site + "/y")) == b"<site-packages>/y"
    scrubbed = fpia.scrub({"spawns": [{"argv": [py, "-c", "1"]}], "hooks": [{"file": site + "/a.pth"}]}, "/nonexistent-work")
    assert scrubbed == {"spawns": [{"argv": ["<python>", "-c", "1"]}], "hooks": [{"file": "<site-packages>/a.pth"}]}


def _clone_interpreter(dest):
    """A venv at ``dest`` holding byte copies of every RECORD-listed file of the running interpreter's
    distributions (same packages, same RECORD hashes, different location)."""
    import importlib.metadata as md
    import sysconfig
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(dest)], check=True, capture_output=True)
    py = dest / "bin" / "python"
    site = Path(subprocess.run([str(py), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
                               capture_output=True, text=True, check=True).stdout.strip())
    here = {Path(sysconfig.get_paths()[k]).resolve() for k in ("purelib", "platlib")}
    root = Path(dest).resolve()
    for dist in md.distributions():
        base = Path(dist.locate_file("")).resolve()
        if base not in here:
            continue
        for f in dist.files or []:
            src = (base / f).resolve()
            if not src.is_file():
                continue
            target = Path(os.path.normpath(site / os.path.relpath(src, base)))
            if os.path.commonpath([str(target), str(root)]) != str(root):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
    return py


DRIVER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from tools.integration import track_c_fpia as fpia
a = json.loads(sys.argv[2])
d = fpia.run_fpia(a["repo"], a["T"], a["G"], a["cdr"], work_dir=a["work"],
                  options={"authority_remote": a["repo"], "require_clean_verifier": False,
                                                   "lanes": ["R", "R-verbatim", "T", "PI"]})
r = d["result"]
print(json.dumps({"sha": d["result_sha256"], "spawn0": [s["argv"][0] for s in r["integration_interference"].get("spawns", [])][:1],
                  "hooks": [h["file"] for h in r["runtime_provenance"].get("site_startup_hooks", [])],
                  "prefix": sys.prefix, "fpia": r["fpia"]["status"], "runtime": r["statuses"]["runtime_provenance"]}))
"""


def test_result_sha256_independent_of_venv_location(tmp_path):
    """The previous round's cross-environment run differed only by the absolute venv path
    (spawns[].argv[0], runtime_provenance.site_startup_hooks[].file). Two interpreters with identical
    packages at different locations must give the identical result_sha256."""
    w = tk.base_world()
    outs = []
    for name in ("one/venv-a", "elsewhere/deeper/venv-b"):
        py = _clone_interpreter(tmp_path / name)
        arg = {"repo": str(w.repo), "T": w.c["T0"], "G": w.c["G0"], "cdr": tk.TEST_CDR,
               "work": str(tmp_path / (name.replace("/", "_") + "-work"))}
        env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "PYTHONHOME")}
        proc = subprocess.run([str(py), "-c", DRIVER, str(tk.IMPL_DIR), json.dumps(arg)], capture_output=True,
                              text=True, env=env, cwd=str(tk.IMPL_DIR))
        assert proc.returncode == 0, proc.stderr[-3000:]
        outs.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    a, b = outs
    assert a["prefix"] != b["prefix"]
    assert a["runtime"] == b["runtime"] == "PASS", (a, b)          # both interpreters are verified runtimes
    assert a["spawn0"] == b["spawn0"] == ["<python>"], (a, b)
    assert a["hooks"] == b["hooks"] and all(not h.startswith(("/", a["prefix"], b["prefix"])) for h in a["hooks"])
    assert a["sha"] == b["sha"], (a, b)


# ---- G6: AC-04 wording; summary ---------------------------------------------------------------------------
def test_ac04_distinguishes_absent_track_c_from_non_merge_landing(tmp_path):
    w = tk.variant(tmp_path)
    g = w.git
    # (a) pre-Track C tree: R absent, no Track C projection path present
    K = w.c["K"]
    r = w.fpia(K, w.register(w.c["R0"], [], [K]), options={"lanes": []})
    c = [x for x in r["authority"]["checks"] if x["id"] == "AC-04" and x["status"] == "FAIL"]
    assert len(c) == 1 and c[0]["case"] == "R_ABSENT_TRACK_C_NOT_INTEGRATED"
    assert "Track C not integrated in this tree" in c[0]["detail"] and c[0]["track_c_paths_present_at_T"] == 0
    assert r["statuses"]["authority"] == "FAIL" and r["fpia"]["status"] == "FPIA_FAIL"
    assert "NOT_RUN ()" not in r["summary"] and r["summary"].split(" | ")[1] == "NOT_RUN"
    # (b) squash landing: R's tree committed on K without R's ancestry
    tree = g("rev-parse", w.c["R0"] + "^{tree}")
    S = g("commit-tree", tree, "-p", K, "-m", "squash of Track C")
    w.git.ref("refs/heads/squash-landing", S)
    r2 = w.fpia(S, w.register(w.c["R0"], [], [S]), options={"lanes": []})
    c2 = [x for x in r2["authority"]["checks"] if x["id"] == "AC-04" and x["status"] == "FAIL"]
    assert len(c2) == 1 and c2[0]["case"] == "NON_MERGE_PRESERVING_LANDING" and c2[0]["track_c_paths_present_at_T"] > 0
    assert "non-merge-preserving landing" in c2[0]["detail"]
    assert r2["statuses"]["authority"] == "FAIL"


def test_summary_without_site_values_has_no_empty_parentheses():
    result = {"fpia": {"status": "FPIA_NOT_RUN"}, "statuses": {"code_identity": "NOT_RUN"}}
    assert "NOT_RUN ()" not in fpia.summary_line(result)


# ---- G7: PR trigger scope; PyYAML vendored, not installed ----------------------------------------------------
def test_workflow_pull_request_scope_uses_authenticated_applicability():
    yaml = fw.yaml
    path = tk.REPO_ROOT / ".github" / "workflows" / "track-c-fpia.yml"
    doc = yaml.safe_load(path.read_text())
    on = doc.get("on", doc.get(True))
    assert "pull_request" in on and "workflow_dispatch" in on
    assert not (on["pull_request"] or {}).get("branches")
    job = doc["jobs"]["fpia"]
    assert "if" not in job  # every PR must reach the authenticated applicability preflight
    applicability = next(s for s in job["steps"] if s.get("id") == "applicability")
    assert applicability["name"] == "Branch-independent authenticated applicability"
    audit = next(s for s in job["steps"] if s.get("name", "").startswith("FPIA audit"))
    assert " ".join(audit["if"].split()) == "steps.applicability.outputs.applies == 'true'"
    install = [s["run"] for s in doc["jobs"]["fpia"]["steps"] if "pip install" in s.get("run", "")]
    assert install and "PyYAML" not in install[0] and "pytest==9.1.1" in install[0]   # the audit uses _vendor/yaml
    assert "authenticated ancestry/content/import applicability" in path.read_text()


# ---- F2: authority transport disclosure (names only) ---------------------------------------------------------
def test_authority_transport_names_recorded_without_values(tmp_path, monkeypatch):
    w = tk.variant(tmp_path)
    for name in fgit.NETWORK_ENV_NAMES + fgit.IGNORED_NETWORK_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.2:9")
    monkeypatch.setenv("HTTP_PROXY", "http://user:secret@127.0.0.2:9")
    sb = fgit.Sandbox(tmp_path / "sb")
    with pytest.raises(fgit.GitError):
        sb.ls_remote("https://127.0.0.1:9/none.git", "refs/heads/x", network=True, label="authority-canonical")
    e = sb.transport_log[-1]
    assert e["op"] == "ls-remote" and e["network"] is True and e["proxy_or_ca_env_present"] is True
    assert e["proxy_or_ca_env_passed"] == ["HTTPS_PROXY"] and "HTTP_PROXY" in e["ignored_proxy_like_env_present"]
    assert "127.0.0.2" not in json.dumps(sb.transport_log) and "secret" not in json.dumps(sb.transport_log)
    d = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]}, doc=True)
    tr = d["run"]["authority_transport"]
    labels = {(q["op"], q["label"]) for q in tr["queries"]}
    assert ("fetch", "authority-remote") in labels and ("ls-remote", "authority-canonical") in labels
    assert all(q["network"] is False and q["proxy_or_ca_env_passed"] == [] for q in tr["queries"])
    assert tr["values_recorded"] is False and "secret" not in json.dumps(d["run"])
    q = d["run"]["canonical_ref_query"]
    assert q["proxy_or_ca_env_present"] is False and "HTTP_PROXY" in q["ignored_proxy_like_env_present"]
