"""Create a local-only commit = acaf1b5 + variant files (plumbing, temporary index, no worktree change).
Writes refs/heads/v2adv/<id> in the private clone (push disabled)."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import variants as VV
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repo")
def git(*a, inp=None, env=None):
    return subprocess.run(["git", "-C", REPO] + list(a), input=inp, capture_output=True, check=True, env=env).stdout.decode().strip()
def make(vid, files, base="acaf1b5a82859ac2750a130ebe88f8b4d272ac66"):
    idx = tempfile.mktemp(prefix="idx-", dir=os.path.join(os.path.dirname(REPO), "work"))
    env = dict(os.environ, GIT_INDEX_FILE=idx, GIT_AUTHOR_NAME="v2adv", GIT_AUTHOR_EMAIL="v2adv@local",
               GIT_COMMITTER_NAME="v2adv", GIT_COMMITTER_EMAIL="v2adv@local",
               GIT_AUTHOR_DATE="2026-10-04T00:00:00Z", GIT_COMMITTER_DATE="2026-10-04T00:00:00Z")
    git("read-tree", base, env=env)
    for p, v in files.items():
        mode, data = ("100644", v) if not isinstance(v, tuple) else v
        data = data.encode() if isinstance(data, str) else data
        sha = git("hash-object", "-w", "--stdin", inp=data)
        git("update-index", "--add", "--cacheinfo", "%s,%s,%s" % (mode, sha, p), env=env)
    tree = git("write-tree", env=env)
    c = git("commit-tree", tree, "-p", base, "-m", "v2-adversarial probe %s (local only)" % vid, env=env)
    git("update-ref", "refs/heads/v2adv/" + vid, c)
    os.unlink(idx)
    return c
if __name__ == "__main__":
    extra = {}
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "combined.py")).read(), extra)
    allv = {v["id"]: v["files"] for v in VV.V}
    allv.update(extra["COMBINED"])
    for vid in sys.argv[1:]:
        print(vid, make(vid, allv[vid]))
