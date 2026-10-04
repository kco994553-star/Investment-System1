"""Sanitised isolated execution, raw-blob materialisation, attributes, sandbox refs and runtime
provenance (CDR-014 §7; rv2 #7b/rc6; review HIGH #4, LOW verifier/runtime provenance)."""
import os
import subprocess
from pathlib import Path

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_git as fgit
from tools.integration import track_c_fpia_runner as frun


def test_hostile_parent_env_ignored(tmp_path, monkeypatch):
    w = tk.variant(tmp_path)
    hostile = tmp_path / "hostile"
    hostile.mkdir()
    marker = tmp_path / "marker"
    (hostile / "sitecustomize.py").write_text("open(%r, 'w').write('site')\n" % str(marker))
    (hostile / "zz_evil_plugin.py").write_text("def pytest_collection_modifyitems(items):\n    items.clear()\n")
    (hostile / "startup.py").write_text("open(%r, 'w').write('startup')\n" % str(marker))
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k 'not holdout'")
    monkeypatch.setenv("PYTEST_PLUGINS", "zz_evil_plugin")
    monkeypatch.setenv("PYTHONPATH", str(hostile))
    monkeypatch.setenv("PYTHONSTARTUP", str(hostile / "startup.py"))
    r = w.fpia(w.c["T0"], options={"lanes": ["T", "V"]})
    inter = r["integration_interference"]
    assert not marker.exists()
    assert not [f for f in inter["findings"] if f["id"] in ("AC-30", "AC-28")], inter["findings"]
    ignored = set(r["runtime_provenance"]["ignored_parent_env"])
    assert {"PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH", "PYTHONSTARTUP"} <= ignored


def test_gitattributes_ident_eol_found(tmp_path):
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {".gitattributes": "*.py ident\n*.md eol=crlf\n"}, "attributes")
    a = w.audit(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]))
    assert any(f["id"] == "AC-31" for f in a.static_findings), a.static_findings
    dest = tmp_path / "mat"
    entries = a.sb.materialise(T2, dest)
    assert fgit.verify_tree(dest, entries) == []          # raw blobs: no ident/eol conversion


def test_materialisation_tamper_detected(tmp_path):
    w = tk.variant(tmp_path)
    sb = fgit.Sandbox(tmp_path / "sb")
    sb.fetch(str(w.repo), ["%s:refs/fpia/in/t" % w.c["T0"]])
    dest = tmp_path / "m"
    entries = sb.materialise(w.c["T0"], dest)
    target = dest / "implementation/src/investment_system/evl/walkforward.py"
    target.write_text(target.read_text() + "# tampered\n")
    (dest / "implementation/extra.txt").write_text("x")
    problems = fgit.verify_tree(dest, entries)
    assert ("content", "implementation/src/investment_system/evl/walkforward.py") in problems
    assert ("extra", "implementation/extra.txt") in problems


def test_ref_shadow_neutralised(tmp_path):
    w = tk.variant(tmp_path)
    g = w.git
    g.ref("refs/heads/origin/" + tk.BRANCH, w.c["S6"])
    g("tag", tk.BRANCH.replace("/", "-"), w.c["S6"])
    g.ref("refs/tags/origin/" + tk.BRANCH, w.c["S6"])
    a = w.audit(w.c["T0"])
    dest = tmp_path / "m"
    a.sb.materialise(w.c["T0"], dest, refs={tk.CANON_REF: w.c["K"]})
    assert a.sb.refs_in(dest) == [tk.CANON_REF + " " + w.c["K"]]
    out = subprocess.run(["git", "-C", str(dest), "rev-parse", "origin/" + tk.BRANCH], capture_output=True,
                         text=True, env=a.sb.env).stdout.strip()
    assert out == w.c["K"]


def test_version_pin_mismatch_not_run(tmp_path):
    w = tk.base_world()
    r = w.fpia(w.c["T0"], options={"installed_versions": {"python": "3.11", "pytest": "0.0.0"}, "lanes": []})
    assert r["statuses"]["runtime_provenance"] == "NOT_RUN"
    assert any(c["id"] == "AC-36" and c.get("dist") == "pytest" for c in r["runtime_provenance"]["checks"])
    assert r["fpia"]["status"] == "FPIA_NOT_RUN"


def test_site_packages_verification_records_hooks():
    problems, hooks = frun.verify_site_packages()
    assert isinstance(problems, list) and isinstance(hooks, list)
    for h in hooks:
        assert len(h["sha256"]) == 64


def test_verifier_dirty_not_run(tmp_path):
    repo = tmp_path / "v"
    here = repo / "fpia"
    here.mkdir(parents=True)
    for p in sorted((tk.TOOLS_DIR / "integration").glob("track_c_fpia*.py")):
        (here / p.name).write_bytes(p.read_bytes())
    env = {"PATH": fgit.system_path(), "HOME": str(tmp_path), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@invalid"}
    subprocess.run(["git", "init", "-q", str(repo)], env=env, check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], env=env, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "fpia"], env=env, check=True)
    clean = fpia.verifier_provenance(here, tmp_path)
    assert clean["clean"] is True and len(clean["files"]) >= 7
    (here / "track_c_fpia_derive.py").write_text("# tampered verifier\n")
    dirty = fpia.verifier_provenance(here, tmp_path)
    assert dirty["clean"] is False and dirty["dirty"]


def test_unknown_option_rejected(tmp_path):
    w = tk.base_world()
    r = fpia.run_fpia(str(w.repo), w.c["T0"], w.c["G0"], tk.TEST_CDR, work_dir=str(tmp_path / "x"),
                      options={"authority_remote": str(w.repo), "trust_me": True})
    assert r["result"]["fpia"]["status"] == "FPIA_NOT_RUN"


def test_launcher_child_flags_and_baseline(tmp_path):
    runner = frun.Runner(tmp_path / "exec")
    res = runner.hardened("baseline", tmp_path, tmp_path, "baseline", [])
    assert res.rc == 0
    flags = res.trace["flags"]
    assert flags["isolated"] and flags["ignore_environment"] and flags["no_user_site"] and flags["dont_write_bytecode"]
    assert res.trace["pycache_prefix"] and Path(res.trace["pycache_prefix"]).is_dir()
