"""FPIA Tier 2: adversarial regressions on the REAL repository history.

Not collected by the default full regression (the file name does not match ``test_*.py``) so that a
missing history can never surface there as a skip; run explicitly, e.g.
``FPIA_REQUIRE_HISTORY=1 PYTHONPATH=src python -m pytest tests/integration_fpia_real_history_checks.py``.
With FPIA_REQUIRE_HISTORY=1 (the FPIA workflow) a missing history or authority FAILS; without it the
module reports an explicit NOT_RUN skip. R and V are taken from the authenticated manifest found by
walking the handoff branch history; there are no SHA literals. Tampered commits are written only
into a private bare mirror in a temporary directory.
"""
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_auth as fauth

REQUIRE = os.environ.get("FPIA_REQUIRE_HISTORY") == "1"
RV1_NODES = sorted(["test_calibration_boundary_and_identity_fail_closed[holdout_role]",
                    "test_no_lookahead_and_primary_stress_boundaries_before_content_access[future_feature]",
                    "test_no_lookahead_and_primary_stress_boundaries_before_content_access[future_dataset]",
                    "test_no_lookahead_and_primary_stress_boundaries_before_content_access[long_label]",
                    "test_no_lookahead_and_primary_stress_boundaries_before_content_access[publication_equality]",
                    "test_holdout_boundary_is_bound_to_current_registered_upstream_metadata",
                    "test_no_holdout_read_function_even_with_provider_argument"])


def _missing(reason):
    if REQUIRE:
        pytest.fail("FPIA_REQUIRE_HISTORY=1 but " + reason)
    pytest.skip("NOT_RUN: " + reason)


def _git(*args, cwd=None):
    env = {"PATH": tk.fgit.system_path(), "HOME": tempfile.gettempdir(), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1"}
    return subprocess.run(["git", *args], cwd=cwd or str(tk.REPO_ROOT), capture_output=True, text=True, env=env)


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    head = _git("rev-parse", "HEAD").stdout.strip()
    ref = "refs/remotes/origin/" + fauth.HANDOFF_BRANCH
    if _git("rev-parse", "--verify", "--quiet", ref).returncode != 0 or not head:
        _missing("handoff branch history is not present in this checkout")
    commits = _git("rev-list", "--reverse", ref, "--", fauth.REGISTER_PATH).stdout.split()
    found = None
    for c in commits:
        text = _git("show", "%s:%s" % (c, fauth.REGISTER_PATH)).stdout
        if "```" + fauth.FENCE in text:
            lines = text.split("\n")
            idx = [i for i, l in enumerate(lines) if l.strip() == "```" + fauth.FENCE][0]
            cdr = [l for l in lines[:idx] if l.startswith("## ")][-1].split()[1]
            found = (c, cdr)
            break
    if found is None:
        _missing("no fpia-reference-manifest on the handoff branch")
    root = tmp_path_factory.mktemp("real")
    mirror = root / "mirror.git"
    proc = _git("clone", "-q", "--mirror", "--shared", str(tk.REPO_ROOT), str(mirror))
    if proc.returncode != 0:
        _missing("cannot mirror the checkout: " + proc.stderr[-200:])
    for line in _git("for-each-ref", "--format=%(objectname) %(refname)", "refs/remotes/").stdout.splitlines():
        sha, name = line.split()
        _git("--git-dir", str(mirror), "update-ref", name, sha)
    w = tk.World(root / "w")
    w.repo = mirror
    w.git = tk.Git(mirror, w.home)
    w.c = {"HEAD": head, "G": found[0]}
    a = fpia.Audit(str(mirror), head, found[0], found[1], root / "audit", {"require_clean_verifier": False})
    a.T, a.G = head, found[0]
    a.populate([a.T, a.G])
    auth = fauth.authenticate(a.sb, a.G, found[1], a.fetch_refs)
    if auth["status"] != "PASS":
        _missing("authority not authenticated: %s" % auth["checks"][-1:])
    a.R, a.Vs = auth["R"], auth["Vs"]
    a.result["authority"] = dict(auth)
    a.derive()
    return {"w": w, "cdr": found[1], "G": found[0], "R": auth["R"], "Vs": auth["Vs"], "head": head, "audit": a}


def audit_tampered(real, changes, msg, parent=None, merge_with=None, resolve=None):
    w = real["w"]
    g = w.git
    base = parent or real["head"]
    T = g.change(base, changes, msg) if changes else base
    if merge_with:
        T = g.merge(T, merge_with, msg, resolve=resolve)
    a = fpia.Audit(str(w.repo), T, real["G"], real["cdr"], Path(tempfile.mkdtemp(dir=w.root)),
                   {"require_clean_verifier": False})
    a.T, a.G = T, real["G"]
    a.populate([a.T, a.G])
    auth = fauth.authenticate(a.sb, a.G, real["cdr"], a.fetch_refs)
    a.result["authority"] = dict(auth)
    assert auth["status"] == "PASS"
    a.R, a.Vs = auth["R"], auth["Vs"]
    a.derive()
    a.ref_status = a.reference_checks()
    if a.ref_status == "PASS":
        a.static_phase()
    return a


def test_real_derivation_and_universe(real):
    a = real["audit"]
    counts = a.proj.counts()
    assert counts["FROZEN_TOOL"] == 3 and counts["NS_OVERLAY"] == 1 and counts["INFRA_REPLACE"] == 1
    assert counts["SHARED_OVERLAY"] == 5
    assert len(a.av) == 23
    assert len(a.frozen["heads"]) == 4 and not a.frozen["unbound"]
    assert len(a.frozen["approvals"]) == 3 and all(x["code_pinned"] for x in a.frozen["approvals"])
    assert {s["kind"] for s in a.sites} == {"call", "attribute"}


def test_real_head_static_clean(real):
    a = audit_tampered(real, {}, "no tamper")
    assert a.ref_status == "PASS"
    assert a.static_findings == [] and not [c for c in a.projection_checks if c["status"] != "PASS"]
    assert not [c for c in a.provenance_checks if c["status"] != "PASS"]


def test_t1_pyc_on_head(real):
    lineage = [p for p in real["audit"].proj.classes if p.endswith("contracts/lineage.py")][0]
    import py_compile
    d = Path(tempfile.mkdtemp())
    (d / "m.py").write_bytes(real["w"].git.read(real["head"], lineage) + b"\n_SHADOW_MARKER = True\n")
    py_compile.compile(str(d / "m.py"), cfile=str(d / "m.pyc"),
                       invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
    path = lineage.rsplit("/", 1)[0] + "/__pycache__/lineage.cpython-311.pyc"
    a = audit_tampered(real, {path: (d / "m.pyc").read_bytes()}, "T1")
    assert any(f["id"] == "AC-23" for f in a.static_findings)


def test_t2_plugin_on_head(real):
    changes = {"implementation/zz_ci_helper-0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: zz\nVersion: 0.0\n",
               "implementation/zz_ci_helper-0.0.dist-info/entry_points.txt": "[pytest11]\nzz = tests.zz_ci_helper\n",
               "implementation/tests/zz_ci_helper.py": "import pytest\n",
               "implementation/tests/test_zz_should_fail.py": "def test_x():\n    assert False\n"}
    a = audit_tampered(real, changes, "T2")
    assert any(f["id"] == "AC-28" for f in a.static_findings)


def test_t4_register_append_on_head(real):
    dr = real["audit"].proj.of("NS_OVERLAY")[0]
    body = real["w"].git.read(real["head"], dr) + b"\n## Foreign approval\n> appended by another capability\n"
    a = audit_tampered(real, {dr: body}, "T4")
    assert any(c["id"] == "AC-17" and c["status"] == "NOT_PRESERVED" for c in a.projection_checks)


def test_v2_byte_flip_on_head(real):
    v2 = sorted(p for p in real["audit"].av if p.endswith("superiority_v2.py"))[0]
    body = real["w"].git.read(real["head"], v2) + b"\n# flipped\n"
    a = audit_tampered(real, {v2: body}, "v2 flip")
    assert any(c["id"] == "AC-21" and c["status"] == "FAIL" for c in a.v2_checks)


def test_x_overlay_conflict_on_real_canonical(real):
    a0 = real["audit"]
    K = a0.K
    overlay = [p for p in a0.proj.of("SHARED_OVERLAY") if "CURRENT_HANDOFF" in p][0]
    g = real["w"].git
    X = g.change(K, {overlay: g.read(K, overlay) + b"\n- X capability entry\n"}, "X lands first")
    resolved = g.read(X, overlay) + g.read(real["R"], overlay)[len(g.read(K, overlay)):]
    a = audit_tampered(real, {}, "merge Track C after X", parent=X, merge_with=real["Vs"][0] if real["Vs"] else real["R"],
                       resolve={overlay: resolved})
    bad = [c for c in a.projection_checks + a.provenance_checks if c["status"] != "PASS"]
    assert any(c["id"] in ("AC-18", "AC-20") for c in bad), bad


def test_rv1_pytest_toml_deselection_on_head(real):
    """rv1 #2 on the real C8 contract/protocol tests: (a) static FOUND; (b) with the static layer and
    -c pinning disabled the 7 Holdout/no-lookahead nodes are deselected and AC-30 names exactly them;
    (c) with pinning on all nodes execute and pass."""
    body = ('[pytest]\naddopts = ["-k", "not holdout and not Holdout and not lookahead and not future"]\n')
    a = audit_tampered(real, {"implementation/tests/.pytest.toml": body}, "rv1 config")
    assert any(f["id"] == "AC-27" for f in a.static_findings)
    files = ["tests/test_evl_c8_contracts.py", "tests/test_evl_c8_protocol.py"]
    a.opts["pytest_config_pinning"] = False
    root, entries = a.materialise("rv1-T", a.T, {})
    unpinned = a.pytest_session("T", "rv1-unpinned", root, entries, "implementation", files, audit=False)
    names = sorted(n.split("::", 1)[1] for n in unpinned["deselected"])
    assert names == RV1_NODES, names
    assert [f["finding"] for f in fpia.session_consistency(unpinned)][:1] == ["tests deselected in a Track C session"]
    a.opts["pytest_config_pinning"] = True
    pinned = a.pytest_session("T", "rv1-pinned", root, entries, "implementation", files, audit=False)
    assert not pinned["deselected"] and pinned["recorder_counts"]["failures"] == 0
    assert set(n.split("::", 1)[1] for n in pinned["collected"]) >= set(RV1_NODES)
    assert fpia.session_consistency(pinned) == []


def test_validation_record_replayed_on_real_history(real, tmp_path):
    """Plan-review HIGH #1 (Tier 2 positive): the 'validation'-named Frozen record found by content is
    replayed at its own head with that head's tools and canonical pin; the embedded evidence and the
    logged CI line are reproduced byte for byte (any mismatch is NOT_PRESERVED, never normalised)."""
    a = real["audit"]
    recs = [r for r in a.frozen["records"] if "validation" in r["path"] and r["embedded"]]
    assert recs
    head = recs[0]["embedded"][0]["head"]
    lines = [x for x in a.frozen["logs"] if x["head"] == head]
    assert lines
    w = real["w"]
    doc = fpia.run_fpia(str(w.repo), real["head"], real["G"], real["cdr"], work_dir=str(tmp_path / "w"),
                        options={"require_clean_verifier": False, "lanes": ["E", "R"]})
    r = doc["result"]
    assert r["statuses"]["historical_frozen_identity"] == "HISTORICAL_FROZEN_IDENTITY_PRESERVED", \
        r["historical_frozen_identity"]["checks"]
    claims = [c["claim"] for c in r["equality_claims"]]
    assert any(recs[0]["path"] in c for c in claims)
    assert any(lines[0]["path"] in c for c in claims)
