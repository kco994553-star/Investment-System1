"""Isolate the TMPDIR-symlink failure of the v2 codex replay: the unmodified Runner.hardened 'script' profile
(as Audit.script_run calls it) on acaf1b5's tree, reached directly vs through a symlinked directory."""
import json, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = HERE.parent.parent
sys.path.insert(0, str(W / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia_runner as frun
base = HERE / "r3real"
if base.exists():
    shutil.rmtree(base)
(base / "trees" / "T").mkdir(parents=True)
subprocess.run("git -C %s archive acaf1b5a82859ac2750a130ebe88f8b4d272ac66 | tar -x -C %s" % (W / "repo", base / "trees" / "T"), shell=True, check=True)
link = HERE / "r3link"
if link.is_symlink():
    link.unlink()
link.symlink_to(base)
out = {}
for label, b in (("real", base), ("symlinked", link)):
    root = b / "trees" / "T"
    runner = frun.Runner(b / ("exec-" + label))
    script = str(root / "implementation/tools/verify_gsup_v2_arithmetic.py")
    res = runner.hardened("probe-" + label, root, root, "script", [os.path.dirname(script)],
                          {"script": script, "args": []}, audit=False)
    out[label] = {"rc": res.rc, "stdout_len": len(res.stdout), "stderr_tail": res.stderr[-1200:]}
print(json.dumps(out, indent=1))
