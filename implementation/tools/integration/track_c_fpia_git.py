"""FPIA git sandbox: every git operation FPIA performs runs here, never in the caller's repository.

The sandbox is a fresh bare repository populated by fetching from the caller's repository (and,
for authority only, from the authority remote) with ``transfer.fsckObjects=true``. index-pack
therefore re-hashes every received object, the caller's commit-graph, replace refs, grafts,
alternates and configuration are never consulted, and FPIA's own git processes run with a
sanitised environment (``GIT_NO_REPLACE_OBJECTS=1``, no system or global configuration).

Trees are materialised by raw blob writes (``git cat-file --batch``): no checkout, no filters,
no attributes. Each materialisation is verified against the tree's path set and blob ids.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

HEX40 = re.compile(r"^[0-9a-f]{40}$")
# Attribute neutralisation for every sandbox and materialisation git directory: "!" leaves each
# attribute unspecified, overriding any in-tree .gitattributes with git's own default behaviour.
NEUTRAL_ATTRIBUTES = ("* !merge !text !eol !crlf !ident !filter !diff !working-tree-encoding "
                      "!export-subst !export-ignore\n")
# Environment variable names passed only to the authority-remote network operation (proxy and
# TLS trust). They cannot change object content: index-pack re-hashes every received object.
NETWORK_ENV_NAMES = ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy", "GIT_SSL_CAINFO",
                     "SSL_CERT_FILE", "SSL_CERT_DIR", "CURL_CA_BUNDLE")
# Proxy/CA-like names that are NOT passed to any git process; their presence is disclosed by name only.
IGNORED_NETWORK_ENV_NAMES = ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy", "GIT_PROXY_COMMAND",
                             "GIT_SSL_CAPATH", "GIT_SSL_NO_VERIFY", "REQUESTS_CA_BUNDLE")
# A fetch can exit 0 while refusing ref updates (e.g. "warning: rejected <ref> because shallow roots
# are not allowed to be updated" from a shallow source; " ! [rejected] ..." status lines). The output
# is inspected, not only the exit code; any such line makes the fetch incomplete (fail-closed).
# Fix round 2 (G3): the status lines are parsed structurally - " <flag> <summary> <from> -> <to>
# [(<reason>)]" - and a refusal is the flag column "!", the summary "[rejected]" or a reason field
# naming "rejected"; ref names (e.g. a branch feature/rejected-ideas) are never matched as text.
STATUS_LINE = re.compile(r"^ (?P<flag>[ +\-t*!=]) (?P<summary>\[[^\]]*\]|\S+)\s+(?P<src>\S+)\s+->\s+(?P<dst>\S+)"
                         r"(?:\s+\((?P<reason>[^()]*)\))?\s*$")
SHALLOW_REJECTION = re.compile(r"^warning: rejected (?P<ref>\S+) because (?P<why>.+)$")
REJECTED_REASON = re.compile(r"\brejected\b", re.I)


class GitError(RuntimeError):
    """A git operation failed; callers turn this into NOT_RUN (never PASS)."""


def system_path():
    """The POSIX default utility path; never the caller's PATH."""
    return os.confstr("CS_PATH") if hasattr(os, "confstr") else "/usr/bin:/bin"


def git_executable():
    found = shutil.which("git", path=system_path())
    if not found:
        raise GitError("git not found on the system default path")
    return os.path.realpath(found)


def base_env(home):
    return {"PATH": system_path(), "HOME": str(home), "LANG": "C", "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0", "GIT_ATTR_NOSYSTEM": "1", "GIT_NO_LAZY_FETCH": "1",
            "GIT_ASKPASS": "", "SSH_ASKPASS": ""}


def rejected_lines(stderr_text):
    """Ref-update refusals reported on a fetch's stderr (remote-side chatter is ignored): ``error:``
    lines, ``warning: rejected <ref> because ...`` lines and status lines whose flag column is ``!``,
    whose summary is ``[rejected]`` or whose reason field names a rejection (G3)."""
    out = []
    for line in stderr_text.splitlines():
        if line.startswith(("remote:", "hint:")):
            continue
        if line.lower().startswith("error:") or SHALLOW_REJECTION.match(line):
            out.append(line.strip())
            continue
        m = STATUS_LINE.match(line)
        if m and (m.group("flag") == "!" or m.group("summary") == "[rejected]"
                  or REJECTED_REASON.search(m.group("reason") or "")):
            out.append(line.strip())
    return out


def network_env(network):
    """(names passed to a network git operation, proxy/CA-like names present but never passed)."""
    passed = sorted(n for n in NETWORK_ENV_NAMES if network and n in os.environ)
    ignored = sorted(n for n in IGNORED_NETWORK_ENV_NAMES if n in os.environ)
    return passed, ignored


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class Entry(tuple):
    """(mode, type, sha) of one tree entry."""
    __slots__ = ()

    def __new__(cls, mode, typ, sha):
        return tuple.__new__(cls, (mode, typ, sha))

    mode = property(lambda self: self[0])
    type = property(lambda self: self[1])
    sha = property(lambda self: self[2])


class Sandbox:
    """A bare object store plus helpers. ``log`` records every ref write FPIA performs."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.git_dir = self.root / "sandbox.git"
        self.home = self.root / "home"
        self.home.mkdir(parents=True, exist_ok=True)
        self.git_bin = git_executable()
        self.env = base_env(self.home)
        self.ref_log = []
        self.fetch_log = []
        self.transport_log = []
        self._trees = {}
        self._blobs = {}
        self.run(["init", "--bare", "-q", str(self.git_dir)], git_dir=False)
        for key, value in (("core.commitGraph", "false"), ("core.autocrlf", "false"),
                           ("core.fsmonitor", "false"), ("core.hooksPath", os.devnull),
                           ("gc.auto", "0"), ("transfer.fsckObjects", "true"),
                           ("fetch.fsckObjects", "true"), ("receive.fsckObjects", "true"),
                           ("fetch.writeCommitGraph", "false"), ("protocol.file.allow", "always")):
            self.run(["config", key, value])
        (self.git_dir / "info").mkdir(exist_ok=True)
        (self.git_dir / "info" / "attributes").write_text(NEUTRAL_ATTRIBUTES)

    # -- low level -----------------------------------------------------------------------
    def run(self, args, *, git_dir=True, input=None, env=None, check=True, cwd=None, text=False):
        cmd = [self.git_bin, "-c", "core.commitGraph=false", "-c", "core.hooksPath=" + os.devnull]
        if git_dir:
            cmd += ["--git-dir", str(self.git_dir)]
        cmd += list(args)
        proc = subprocess.run(cmd, input=input, capture_output=True, env=env or self.env,
                              cwd=cwd or str(self.root), text=text)
        if check and proc.returncode != 0:
            err = proc.stderr if text else proc.stderr.decode(errors="replace")
            raise GitError("git %s failed (%d): %s" % (" ".join(args[:3]), proc.returncode, err.strip()[-800:]))
        return proc

    def out(self, *args, check=True):
        return self.run(list(args), check=check).stdout.decode()

    # -- population ----------------------------------------------------------------------
    def fetch(self, source: str, refspecs, *, network=False, label=""):
        """Fetch with fsck into the sandbox. ``source`` is a local path or URL."""
        env = dict(self.env)
        if network:
            for name in NETWORK_ENV_NAMES:
                if name in os.environ:
                    env[name] = os.environ[name]
        url = source
        if not network and not re.match(r"^[a-z]+://", source):
            url = "file://" + str(Path(source).resolve())
        args = ["-c", "transfer.fsckObjects=true", "-c", "fetch.fsckObjects=true", "fetch", "--no-tags",
                "--no-write-fetch-head", "--no-recurse-submodules", "--no-auto-gc", url, *refspecs]
        proc = self.run(args, env=env, check=False)
        rejected = rejected_lines(proc.stderr.decode(errors="replace"))
        entry = {"label": label, "source": source, "network": network, "refspecs": list(refspecs),
                 "rc": proc.returncode, "rejected": rejected,
                 "network_env_names": sorted(n for n in NETWORK_ENV_NAMES if network and n in os.environ)}
        self.fetch_log.append(entry)
        self._transport("fetch", label, source, network, proc.returncode)
        if proc.returncode != 0:
            raise GitError("fetch %s failed: %s" % (label or source, proc.stderr.decode(errors="replace").strip()[-800:]))
        if rejected:
            raise GitError("fetch %s rejected %d ref update(s) although it exited 0 (incomplete source; environment "
                           "unverified): %s" % (label or source, len(rejected), rejected[:5]))
        # every explicit <40-hex>:<ref> refspec must have landed exactly (objects present and ref written)
        missing = []
        for spec in refspecs:
            src, _, dst = spec.lstrip("+").partition(":")
            if HEX40.match(src) and dst:
                got = self.run(["rev-parse", "--verify", "--quiet", dst + "^{commit}"], check=False).stdout.decode().strip()
                if got != src:
                    missing.append(src)
        if missing:
            entry["missing"] = missing
            raise GitError("fetch %s did not deliver %s (incomplete source; environment unverified)"
                           % (label or source, missing[:5]))
        return proc

    def is_shallow(self):
        """True when the sandbox itself became shallow (it must never be)."""
        return self.out("rev-parse", "--is-shallow-repository").strip() != "false"

    def source_is_shallow(self, source):
        """``git rev-parse --is-shallow-repository`` of a local source repository (read-only).
        Raises GitError when it cannot be determined (fail-closed: environment unverified)."""
        proc = self.run(["-C", str(source), "rev-parse", "--is-shallow-repository"], git_dir=False, check=False)
        answer = proc.stdout.decode(errors="replace").strip()
        if proc.returncode != 0 or answer not in ("true", "false"):
            raise GitError("cannot determine whether --repo is shallow: %s"
                           % proc.stderr.decode(errors="replace").strip()[-300:])
        return answer == "true"

    def _transport(self, op, label, source, network, rc):
        """F2 disclosure: whether proxy/CA environment variables were present (names only, never values)."""
        passed, ignored = network_env(network)
        self.transport_log.append({"op": op, "label": label, "remote": source, "network": network, "rc": rc,
                                   "proxy_or_ca_env_passed": passed, "proxy_or_ca_env_present": bool(passed),
                                   "ignored_proxy_like_env_present": ignored})

    def ls_remote(self, source, *patterns, network=False, label=""):
        env = dict(self.env)
        if network:
            for name in NETWORK_ENV_NAMES:
                if name in os.environ:
                    env[name] = os.environ[name]
        url = source
        if not network and not re.match(r"^[a-z]+://", source):
            url = "file://" + str(Path(source).resolve())
        proc = self.run(["ls-remote", url, *patterns], env=env, check=False, git_dir=True)
        self._transport("ls-remote", label, source, network, proc.returncode)
        if proc.returncode != 0:
            raise GitError("ls-remote failed: " + proc.stderr.decode(errors="replace").strip()[-400:])
        refs = {}
        for line in proc.stdout.decode().splitlines():
            sha, ref = line.split("\t", 1)
            refs[ref] = sha
        return refs

    def update_ref(self, ref, sha, purpose):
        old = self.out("rev-parse", "--verify", "--quiet", ref, check=False).strip() or None
        self.run(["update-ref", ref, sha])
        self.ref_log.append({"git_dir": "sandbox", "ref": ref, "old": old, "new": sha, "purpose": purpose})

    # -- object queries ------------------------------------------------------------------
    def commit(self, rev):
        out = self.run(["rev-parse", "--verify", "--quiet", rev + "^{commit}"], check=False)
        sha = out.stdout.decode().strip()
        if out.returncode != 0 or not HEX40.match(sha):
            raise GitError("not a commit in the sandbox: " + rev)
        return sha

    def has_commit(self, rev):
        try:
            self.commit(rev)
            return True
        except GitError:
            return False

    def is_ancestor(self, a, b):
        proc = self.run(["merge-base", "--is-ancestor", a, b], check=False)
        if proc.returncode not in (0, 1):
            raise GitError("merge-base --is-ancestor failed for %s %s" % (a, b))
        return proc.returncode == 0

    def tree(self, rev):
        """{path: Entry} for every non-tree entry (blobs, symlinks, gitlinks)."""
        proc = self.run(["rev-parse", "--verify", "--quiet", rev + "^{tree}"], check=False)
        sha = proc.stdout.decode().strip()
        if proc.returncode != 0 or not HEX40.match(sha):
            raise GitError("not a tree-ish in the sandbox: " + rev)
        if sha in self._trees:
            return self._trees[sha]
        raw = self.run(["ls-tree", "-r", "-z", "--full-tree", sha]).stdout
        out = {}
        for item in raw.split(b"\0"):
            if not item:
                continue
            meta, path = item.split(b"\t", 1)
            mode, typ, obj = meta.decode().split()
            out[path.decode("utf-8", "surrogateescape")] = Entry(mode, typ, obj)
        self._trees[sha] = out
        return out

    def tree_id(self, rev):
        return self.out("rev-parse", "--verify", rev + "^{tree}").strip()

    def blobs(self, shas):
        """{sha: bytes} for blob ids, via one cat-file --batch call."""
        want = [s for s in dict.fromkeys(shas) if s not in self._blobs]
        if want:
            raw = self.run(["cat-file", "--batch"], input=("\n".join(want) + "\n").encode()).stdout
            i = 0
            for sha in want:
                nl = raw.index(b"\n", i)
                header = raw[i:nl].decode().split()
                if len(header) != 3 or header[1] != "blob":
                    raise GitError("expected blob %s, got %s" % (sha, header))
                size = int(header[2])
                data = raw[nl + 1:nl + 1 + size]
                if blob_id(data) != sha:
                    raise GitError("blob hash mismatch " + sha)
                self._blobs[sha] = data
                i = nl + 1 + size + 1
        return {s: self._blobs[s] for s in shas}

    def blob(self, sha):
        return self.blobs([sha])[sha]

    def read(self, rev, path):
        entry = self.tree(rev).get(path)
        if entry is None or entry.type != "blob":
            return None
        return self.blob(entry.sha)

    def rev_list(self, *args):
        return [l for l in self.out("rev-list", *args).splitlines() if l]

    def parents(self, commit):
        line = self.out("rev-list", "--parents", "-n", "1", commit).split()
        return line[1:]

    def changed_paths(self, parent, child):
        raw = self.run(["diff-tree", "-r", "-z", "--no-renames", "--name-only", parent, child]).stdout
        return [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]

    def merge_tree(self, a, b):
        """(clean, tree_sha, conflicted_paths) from ``git merge-tree --write-tree``."""
        proc = self.run(["merge-tree", "--write-tree", "-z", "--name-only", "--no-messages", a, b], check=False)
        if proc.returncode not in (0, 1):
            raise GitError("merge-tree failed: " + proc.stderr.decode(errors="replace")[-400:])
        parts = proc.stdout.split(b"\0")
        tree = parts[0].decode().strip()
        conflicted = sorted({p.decode("utf-8", "surrogateescape") for p in parts[1:] if p})
        return proc.returncode == 0, tree, conflicted

    def commit_tree(self, tree, parents, message):
        env = dict(self.env, GIT_AUTHOR_NAME="track-c-fpia", GIT_AUTHOR_EMAIL="track-c-fpia@invalid",
                   GIT_COMMITTER_NAME="track-c-fpia", GIT_COMMITTER_EMAIL="track-c-fpia@invalid",
                   GIT_AUTHOR_DATE="2000-01-01T00:00:00Z", GIT_COMMITTER_DATE="2000-01-01T00:00:00Z")
        args = ["commit-tree", tree]
        for p in parents:
            args += ["-p", p]
        args += ["-m", message]
        return self.run(args, env=env).stdout.decode().strip()

    def make_tree(self, entries):
        """Write a tree from {path: Entry} through a private index file."""
        self._index_counter = getattr(self, "_index_counter", 0) + 1
        index = self.root / ("fpia-index-%d" % self._index_counter)
        env = dict(self.env, GIT_INDEX_FILE=str(index))
        self.run(["read-tree", "--empty"], env=env)
        lines = "".join("%s %s\t%s\0" % (e.mode, e.sha, p) for p, e in sorted(entries.items()))
        self.run(["update-index", "-z", "--index-info"], input=lines.encode("utf-8", "surrogateescape"), env=env)
        tree = self.run(["write-tree"], env=env).stdout.decode().strip()
        index.unlink()
        return tree

    def feature_probe(self):
        probes = {}
        probes["version"] = self.out("version").strip()
        for name, args in (("merge-tree --write-tree", ["merge-tree", "-h"]),
                           ("check-attr --source", ["check-attr", "-h"])):
            proc = self.run(args, check=False)
            text = (proc.stdout + proc.stderr).decode(errors="replace")
            probes[name] = ("--write-tree" in text) if name.startswith("merge") else ("--source" in text)
        return probes

    def check_attr(self, source, paths):
        """{path: {attr: value}} using ``git check-attr --source`` (all attributes)."""
        if not paths:
            return {}
        data = "\0".join(paths) + "\0"
        # Use a scratch git dir WITHOUT the neutral info/attributes so in-tree attributes show.
        scratch = self.root / "attr.git"
        if not scratch.exists():
            self.run(["init", "--bare", "-q", str(scratch)], git_dir=False)
            (scratch / "objects" / "info").mkdir(parents=True, exist_ok=True)
            (scratch / "objects" / "info" / "alternates").write_text(str(self.git_dir / "objects") + "\n")
        cmd = [self.git_bin, "--git-dir", str(scratch), "check-attr", "--source=" + source, "-a", "-z", "--stdin"]
        proc = subprocess.run(cmd, input=data.encode("utf-8", "surrogateescape"), capture_output=True, env=self.env)
        if proc.returncode != 0:
            raise GitError("check-attr failed: " + proc.stderr.decode(errors="replace")[-400:])
        parts = proc.stdout.split(b"\0")
        out = {}
        for i in range(0, len(parts) - 2, 3):
            path, attr, value = (x.decode("utf-8", "surrogateescape") for x in parts[i:i + 3])
            out.setdefault(path, {})[attr] = value
        return out

    # -- materialisation -----------------------------------------------------------------
    def materialise(self, rev, dest: Path, refs=None, purpose=""):
        """Raw-blob materialisation of ``rev`` into ``dest`` plus a private git dir.

        The private git dir uses this sandbox's object store as alternates, has HEAD detached at
        ``rev``, an index read from ``rev``, neutral info/attributes and ONLY the refs in ``refs``.
        Returns the verified {path: Entry} map.
        """
        commit = self.commit(rev)
        entries = self.tree(commit)
        dest = Path(dest)
        if dest.exists():
            raise GitError("materialisation target exists: %s" % dest)
        dest.mkdir(parents=True)
        blobs = self.blobs([e.sha for e in entries.values() if e.type == "blob"])
        for path, e in sorted(entries.items()):
            target = dest / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if e.type == "commit":          # gitlink: an empty directory, as a checkout leaves it
                target.mkdir(exist_ok=True)
                continue
            data = blobs[e.sha]
            if e.mode == "120000":
                os.symlink(data.decode("utf-8", "surrogateescape"), target)
                continue
            target.write_bytes(data)
            os.chmod(target, 0o755 if e.mode == "100755" else 0o644)
        gd = dest / ".git"
        self.run(["init", "-q", str(dest)], git_dir=False, cwd=str(self.root))
        (gd / "objects" / "info").mkdir(parents=True, exist_ok=True)
        (gd / "objects" / "info" / "alternates").write_text(str((self.git_dir / "objects").resolve()) + "\n")
        (gd / "info").mkdir(exist_ok=True)
        (gd / "info" / "attributes").write_text(NEUTRAL_ATTRIBUTES)
        for key, value in (("core.commitGraph", "false"), ("core.autocrlf", "false"),
                           ("core.fsmonitor", "false"), ("core.hooksPath", os.devnull), ("gc.auto", "0")):
            self.run(["--git-dir", str(gd), "config", key, value], git_dir=False)
        (gd / "HEAD").write_text(commit + "\n")
        for name in list((gd / "refs" / "heads").iterdir()) if (gd / "refs" / "heads").exists() else []:
            name.unlink()
        for ref, sha in sorted((refs or {}).items()):
            self.run(["--git-dir", str(gd), "update-ref", ref, sha], git_dir=False)
            self.ref_log.append({"git_dir": str(dest.name), "ref": ref, "old": None, "new": sha, "purpose": purpose})
        self.run(["--git-dir", str(gd), "--work-tree", str(dest), "read-tree", commit], git_dir=False)
        self.run(["--git-dir", str(gd), "--work-tree", str(dest), "update-index", "-q", "--refresh"],
                 git_dir=False, check=False)
        problems = verify_tree(dest, entries)
        if problems:
            raise GitError("materialisation verification failed: %s" % problems[:5])
        return entries

    def refs_in(self, dest: Path):
        gd = Path(dest) / ".git"
        out = self.run(["--git-dir", str(gd), "for-each-ref", "--format=%(refname) %(objectname)"],
                       git_dir=False).stdout.decode()
        return sorted(out.splitlines())


def verify_tree(dest: Path, entries, allowed_extra_dirs=()):
    """Compare the worktree at ``dest`` with ``entries``; returns a list of problems.

    Extra files are allowed only below ``allowed_extra_dirs`` (repo-relative directories).
    """
    problems = []
    dest = Path(dest)
    seen = set()
    for dirpath, dirnames, filenames in os.walk(dest, followlinks=False):
        rel_dir = os.path.relpath(dirpath, dest)
        if rel_dir == ".":
            rel_dir = ""
        if rel_dir == ".git" or rel_dir.startswith(".git" + os.sep):
            dirnames[:] = []
            continue
        if rel_dir == "":
            dirnames[:] = [d for d in dirnames if d != ".git"]
        names = list(filenames) + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]
        for name in names:
            rel = (rel_dir + "/" + name) if rel_dir else name
            rel = rel.replace(os.sep, "/")
            seen.add(rel)
            e = entries.get(rel)
            full = os.path.join(dirpath, name)
            if e is None:
                if not any(rel.startswith(d.rstrip("/") + "/") for d in allowed_extra_dirs):
                    problems.append(("extra", rel))
                continue
            st = os.lstat(full)
            if e.mode == "120000":
                if not stat.S_ISLNK(st.st_mode) or blob_id(os.readlink(full).encode("utf-8", "surrogateescape")) != e.sha:
                    problems.append(("symlink", rel))
                continue
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
                problems.append(("type", rel))
                continue
            with open(full, "rb") as handle:
                if blob_id(handle.read()) != e.sha:
                    problems.append(("content", rel))
            if (e.mode == "100755") != bool(st.st_mode & 0o100):
                problems.append(("mode", rel))
    for path, e in entries.items():
        if e.type == "commit":
            continue
        if path not in seen:
            problems.append(("missing", path))
    return problems
