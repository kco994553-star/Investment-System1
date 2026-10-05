"""Isolate the run2 verdict flip with the unmodified 523e702 functions (no full audit):
1) Audit.plugin_findings with the interpreter's site-packages reached through a symlinked venv path;
2) Audit.determine_rootdir with a tree root reached through a symlinked directory (TMPDIR symlink)."""
import json, os, subprocess, sys, types, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = HERE.parent.parent
sys.path.insert(0, str(W / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia as F
out = {}
VENV, VLINK = W / "venv", W / "det" / "venvlink"
sp = "lib/python3.11/site-packages"
stub = types.SimpleNamespace(sb=None, R=None)
for label, base in (("real_venv_path", VENV), ("symlinked_venv_path", VLINK)):
    session = {"label": "probe", "pytest_file": str(base / sp / "pytest" / "__init__.py"),
               "plugins": [{"name": "assertion", "file": str(base / sp / "_pytest" / "assertion" / "__init__.py")},
                           {"name": "python", "file": str(base / sp / "_pytest" / "python.py")}]}
    out["plugin_findings/" + label] = F.Audit.plugin_findings(stub, session, "/nonexistent-root")
# 2) rootdir: a materialised tree reached directly and through a symlink
tree = HERE / "realtree"
if tree.exists():
    shutil.rmtree(tree)
tree.mkdir()
subprocess.run("git -C %s archive acaf1b5a82859ac2750a130ebe88f8b4d272ac66 implementation/tests/test_evl_c6_execution.py implementation/tests/test_evl_c6_robustness.py implementation/tests/evl_c6_fixture.py 2>/dev/null | tar -x -C %s" % (W / "repo", tree), shell=True)
files = sorted(p.name for p in (tree / "implementation" / "tests").glob("*.py"))
link = HERE / "treelink"
if link.is_symlink():
    link.unlink()
link.symlink_to(tree)
for label, root in (("real_root", tree), ("symlinked_root", link)):
    out["determine_rootdir/" + label] = list(F.Audit.determine_rootdir(stub, Path(root), "implementation", ["tests/" + f for f in files]))
out["files"] = files
print(json.dumps(out, indent=1))
