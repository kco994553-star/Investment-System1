"""G3b: a fetch that exits 0 whose ONLY refusal names a ref containing U+2028, through the unmodified Sandbox.fetch."""
import json, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia_git as fgit
B = HERE / "w2"
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
F = B / "F"; git("init", "-q", "-b", "master", str(F))
for i in range(3):
    (F / "f").write_text(str(i)); git("add", "f", cwd=F); git("commit", "-qm", "c%d" % i, cwd=F)
S = B / "S"; git("init", "-q", "-b", "good", str(S))
(S / "g").write_text("g"); git("add", "g", cwd=S); git("commit", "-qm", "good", cwd=S)
weird = "x y"
git("fetch", "-q", "--depth", "1", "file://" + str(F), "master:refs/heads/" + weird, cwd=S)
res = {"source_is_shallow_per_git": git("rev-parse", "--is-shallow-repository", cwd=S).stdout.decode().strip()}
sb = fgit.Sandbox(B / "sandbox")
try:
    sb.fetch(str(S), ["+refs/heads/*:refs/fpia/src/heads/*"], label="probe")
    res["Sandbox.fetch"] = "returned normally (no GitError)"
except fgit.GitError as exc:
    res["Sandbox.fetch"] = "GitError: " + str(exc)[:400]
res["fetch_log"] = sb.fetch_log
res["sandbox_refs"] = sb.out("for-each-ref", "--format=%(refname)").split("\n")
d2 = B / "d2"; git("init", "-q", "--bare", str(d2))
p = git("fetch", "--no-tags", "file://" + str(S), "+refs/heads/*:refs/x/*", cwd=d2, check=False)
res["plain_git_rc"] = p.returncode
res["plain_git_stderr"] = p.stderr.decode("utf-8", "replace").split("\n")
try:
    sb.source_is_shallow(str(S)); res["Sandbox.source_is_shallow"] = sb.source_is_shallow(str(S))
except fgit.GitError as exc:
    res["Sandbox.source_is_shallow"] = "GitError " + str(exc)[:200]
print(json.dumps(res, indent=1, ensure_ascii=True))
