"""Fix round F1/F2/F4 (CDR-014 §7, §14): an incomplete caller repository makes FPIA NOT_RUN (never a
determinate FAIL or PASS); the canonical premise of FROZEN_TOOLS_ON_T comes from the authority remote
(git ls-remote), never from a caller-local remote-tracking ref; the frozen tools' complete streams on T
are kept as side files next to the JSON output with their sha256 in the JSON."""
import hashlib
import json
from pathlib import Path

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_git as fgit


def _absent_sha():
    return hashlib.sha1(b"fpia-test: an object that exists nowhere").hexdigest()


# ---- F1: shallow / incomplete --repo -------------------------------------------------------------------
def test_shallow_repo_is_not_run_never_a_determinate_frozen_tools_fail(tmp_path):
    """The CDR-014 §7/§14 defect: a shallow --repo whose fetch refuses every ref update but exits 0 gave a
    spurious FROZEN_TOOLS_ON_T_FAIL. It must be NOT_RUN (environment unverified) for the component and
    the overall verdict."""
    w = tk.variant(tmp_path)
    shallow = w.shallow_clone(tmp_path / "shallow.git")
    r = w.fpia(w.c["T0"], repo=shallow, options={"lanes": ["T-frozen"]})
    assert r["statuses"]["frozen_tools_on_T"] == "NOT_RUN"         # was a spurious FROZEN_TOOLS_ON_T_FAIL
    assert r["statuses"]["authority"] == "NOT_RUN"
    assert r["fpia"]["status"] == "FPIA_NOT_RUN"
    assert r["environment"]["caller_repository"]["shallow"] is True
    assert r["environment"]["caller_repository"]["status"] == "NOT_RUN"
    assert any(c["id"] == "AC-01" and "shallow" in c["detail"] for c in r["authority"]["checks"])


def test_fetch_that_rejects_refs_but_exits_zero_is_an_error(tmp_path):
    """Inspect the fetch output, not only the exit code."""
    w = tk.variant(tmp_path)
    shallow = w.shallow_clone(tmp_path / "shallow.git")
    sb = fgit.Sandbox(tmp_path / "sb")
    with pytest.raises(fgit.GitError, match="rejected"):
        sb.fetch(str(shallow), ["+refs/heads/*:refs/fpia/src/heads/*"], label="caller-repo")
    assert sb.fetch_log[-1]["rc"] == 0 and sb.fetch_log[-1]["rejected"]
    assert any("shallow" in line for line in sb.fetch_log[-1]["rejected"])
    # a complete source fetches cleanly and records no rejection
    sb2 = fgit.Sandbox(tmp_path / "sb2")
    sb2.fetch(str(w.repo), ["+refs/heads/*:refs/fpia/src/heads/*", "%s:refs/fpia/in/%s" % (w.c["T0"], w.c["T0"])])
    assert sb2.fetch_log[-1]["rejected"] == [] and not sb2.is_shallow()


def test_fetch_must_deliver_explicit_refs(tmp_path):
    w = tk.variant(tmp_path)
    sb = fgit.Sandbox(tmp_path / "sb")
    with pytest.raises(fgit.GitError):
        sb.fetch(str(w.repo), ["%s:refs/fpia/in/x" % _absent_sha()], label="references")


def test_missing_evidence_head_object_is_not_run_not_fail(tmp_path):
    """A Frozen record at R naming a head whose object --repo lacks: NOT_RUN (environment unverified),
    never the determinate AC-04 FAIL reserved for an existing head that is not an ancestor of R."""
    w = tk.variant(tmp_path)
    g, R = w.git, w.c["R0"]
    path = "implementation/reports/track_c_c6_acceptance_2001.json"
    rec = json.loads(g.read(R, path))
    rec["evidence"]["boundary_audit"]["tested_head"] = _absent_sha()
    R2 = g.change(R, {path: json.dumps(rec)}, "R' names an unavailable head")
    G = w.register(R2, [], [R2])
    a = w.audit(R2, G)
    assert a.auth["status"] == "PASS"
    assert a.ref_status == "NOT_RUN", a.result["authority"]["checks"]
    assert any(c["id"] == "AC-04" and c["status"] == "NOT_RUN" and "unavailable" in c["detail"]
               for c in a.result["authority"]["checks"])
    assert not any(c["id"] == "AC-04" and c["status"] == "FAIL" for c in a.result["authority"]["checks"])
    r = w.fpia(R2, G, options={"lanes": []})
    assert r["statuses"]["authority"] == "NOT_RUN" and r["fpia"]["status"] == "FPIA_NOT_RUN"


# ---- F2: canonical premise from the authority remote ---------------------------------------------------
def test_canonical_value_comes_from_authority_not_caller_tracking_ref(tmp_path):
    """The caller-local refs/remotes/origin/<BRANCH> is stale (K); the authority remote advertises the
    advanced canonical. FROZEN_TOOLS_ON_T must use (and record) the authority value."""
    w = tk.variant(tmp_path)
    advanced = w.git.merge(w.c["K"], w.c["R0"], "canonical advanced: Track C landing")
    w.set_canonical(advanced, caller_tracking=False)
    assert w.git("rev-parse", tk.CANON_REF) == w.c["K"]
    d = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]}, doc=True)
    r = d["result"]
    canon = r["frozen_tools_on_T"]["canonical_ref"]
    assert canon["value"] == advanced and canon["status"] == "PASS"
    assert canon["source"]["remote"] == str(w.repo) and canon["source"]["ref"] == tk.CANON_HEAD
    assert "ls-remote" in canon["source"]["method"]
    query = d["run"]["canonical_ref_query"]
    assert query["value"] == advanced and query["queried_utc"] and query["remote"] == str(w.repo)
    first = [s for s in r["frozen_tools_on_T"]["steps"] if s["kind"] == "tool"][0]
    assert first["matched_tool_message"] == "canonical advanced; fresh integration audit required"
    assert r["statuses"]["frozen_tools_on_T"] == "FROZEN_TOOLS_ON_T_FAIL"


def test_canonical_absent_at_authority_is_not_run(tmp_path):
    """Only the caller-local remote-tracking ref exists: the canonical premise is unavailable, so the
    frozen tools are not run and FROZEN_TOOLS_ON_T is NOT_RUN (never FAIL)."""
    w = tk.variant(tmp_path)
    w.git("update-ref", "-d", tk.CANON_HEAD)
    assert w.git("rev-parse", tk.CANON_REF) == w.c["K"]
    r = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]})
    ft = r["frozen_tools_on_T"]
    assert r["statuses"]["frozen_tools_on_T"] == "NOT_RUN"         # never a determinate FAIL
    assert ft["canonical_ref"]["status"] == "NOT_RUN" and ft["canonical_ref"]["value"] is None
    assert "absent" in ft["canonical_ref"]["detail"]
    assert ft["steps"] == [] and r["statuses"]["frozen_tools_on_T"] == "NOT_RUN"
    assert r["fpia"]["status"] == "FPIA_NOT_RUN"


def test_canonical_unreachable_authority_is_not_run(tmp_path):
    w = tk.variant(tmp_path)
    a = w.audit(w.c["T0"])
    assert a.ref_status == "PASS"
    a.opts["authority_remote"] = str(tmp_path / "no-such-remote.git")
    rec = a.canonical_from_authority()
    assert rec["status"] == "NOT_RUN" and rec["value"] is None and "unreachable" in rec["detail"]


# ---- F4: complete frozen-tool streams as side files ----------------------------------------------------
def test_frozen_tool_streams_kept_verbatim_next_to_output(tmp_path):
    w = tk.base_world()
    out = tmp_path / "a" / "fpia.json"
    out.parent.mkdir()
    d = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]}, out=str(out), doc=True, work=tmp_path / "wa")
    r = d["result"]
    tools = [s for s in r["frozen_tools_on_T"]["steps"] if s["kind"] == "tool"]
    assert tools and all(s["rc"] != 0 for s in tools)
    assert all("verbatim" in s for s in tools), tools
    side = Path(str(out) + fpia.VERBATIM_DIR_SUFFIX)
    assert d["run"]["verbatim_dir"] == str(side)
    for s in tools:
        v = s["verbatim"]
        assert s["matched_tool_message"]                     # kept
        for kind in ("stdout", "stderr"):
            data = (side / v[kind]["file"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == v[kind]["sha256"] and len(data) == v[kind]["bytes"]
            assert d["run"]["verbatim_raw"][v[kind]["file"]]["sha256"]
        text = (side / v["stderr"]["file"]).read_text()
        assert "Traceback (most recent call last)" in text
        assert s["first_error"] == [l for l in text.strip().split("\n") if l][-1]   # untruncated
    # the work-directory normalisation keeps the result deterministic across work directories (AC-38)
    out2 = tmp_path / "b" / "fpia.json"
    out2.parent.mkdir()
    d2 = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]}, out=str(out2), doc=True, work=tmp_path / "wb")
    assert d2["result_sha256"] == d["result_sha256"]
