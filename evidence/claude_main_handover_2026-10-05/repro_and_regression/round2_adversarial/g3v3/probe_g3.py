"""G3 probes: real git fetch stderr fed to the unmodified fgit.rejected_lines and fgit.Sandbox.fetch (523e702)."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia_git as fgit
B = HERE / "w"
if B.exists():
    shutil.rmtree(B)
B.mkdir()
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, LANG="C", LC_ALL="C",
           GIT_AUTHOR_NAME="p", GIT_AUTHOR_EMAIL="p@l", GIT_COMMITTER_NAME="p", GIT_COMMITTER_EMAIL="p@l")
def git(*a, cwd=None, check=True):
    p = subprocess.run(["git"] + list(a), cwd=cwd, env=ENV, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "replace"))
    return p
NAMES = {"ls": "x y", "ps": "x y", "nel": "x\u0085y", "plain": "plainz", "arrow": "a->b",
         "paren": "q(non-fast-forward)", "rejword": "feature/rejected-ideas"}
out = {"git_version": git("--version").stdout.decode().strip(), "cases": {}}
# 1) non-fast-forward rejections (no '+') for each name
src = B / "src"; dst = B / "dst"
git("init", "-q", "-b", "master", str(src)); git("init", "-q", "--bare", str(dst))
(src / "f").write_text("1"); git("add", "f", cwd=src); git("commit", "-qm", "c1", cwd=src)
c1 = git("rev-parse", "HEAD", cwd=src).stdout.decode().strip()
for k, n in NAMES.items():
    git("branch", n, cwd=src)
specs = ["refs/heads/%s:refs/o/%s" % (n, n) for n in NAMES.values()]
git("fetch", str(src), *specs, cwd=dst)
(src / "f").write_text("2"); git("commit", "-qam", "c2", cwd=src)
git("checkout", "-q", "--orphan", "other", cwd=src); (src / "g").write_text("x"); git("add", "g", cwd=src)
git("commit", "-qm", "unrelated", cwd=src)
for n in NAMES.values():
    git("branch", "-f", n, "other", cwd=src)   # every branch now non-fast-forward relative to dst refs
p = git("-c", "fetch.output=full", "fetch", "--no-tags", str(src), *specs, cwd=dst, check=False)
err = p.stderr.decode("utf-8", "replace")
lines = fgit.rejected_lines(err)
out["cases"]["non_ff"] = {"rc": p.returncode, "stderr_lines": err.split("\n"),
                          "rejected_lines": lines,
                          "per_name_detected": {k: any(n.split(" ")[0].split(" ")[0].split("\u0085")[0] in l and "rejected" in l for l in lines)
                                                for k, n in NAMES.items()}}
# 2) the same through the unmodified Sandbox.fetch (exit code of git is 1 here, so GitError is expected either way)
# 3) shallow-source rejection lines ("warning: rejected ... because shallow roots ...") with a U+2028 ref name
full = B / "full"; git("init", "-q", "-b", "master", str(full))
for i in range(3):
    (full / "f").write_text(str(i)); git("add", "f", cwd=full); git("commit", "-qm", "c%d" % i, cwd=full)
git("branch", NAMES["ls"], cwd=full); git("branch", "plainbranch", cwd=full)
shallow = B / "shallow"
git("clone", "-q", "--depth", "1", "--no-single-branch", "file://" + str(full), str(shallow))
sb_root = B / "sandbox"
sb = fgit.Sandbox(sb_root)
res = {}
try:
    sb.fetch(str(shallow), ["+refs/remotes/origin/*:refs/fpia/src/remotes/*", "+refs/heads/*:refs/fpia/src/heads/*"], label="probe-shallow")
    res["raised"] = None
except fgit.GitError as exc:
    res["raised"] = str(exc)[:600]
res["fetch_log"] = sb.fetch_log
out["cases"]["shallow_source_via_Sandbox_fetch"] = res
# raw stderr of the same fetch with plain git for the record
d2 = B / "d2"; git("init", "-q", "--bare", str(d2))
p = git("fetch", "--no-tags", "file://" + str(shallow), "+refs/remotes/origin/*:refs/x/*", cwd=d2, check=False)
e2 = p.stderr.decode("utf-8", "replace")
out["cases"]["shallow_source_plain_git"] = {"rc": p.returncode, "stderr_lines": e2.split("\n"),
                                            "rejected_lines": fgit.rejected_lines(e2)}
print(json.dumps(out, indent=1, ensure_ascii=True, default=str))
