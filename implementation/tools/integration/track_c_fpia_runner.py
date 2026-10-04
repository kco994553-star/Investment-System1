"""FPIA execution: hardened and verbatim child runs, trace validation, pytest session evidence and
runtime provenance. Exact equality only; no timeouts, tolerances or thresholds."""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata as metadata
import io
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from . import track_c_fpia_git as fgit
except ImportError:  # executed as a script directory member
    import track_c_fpia_git as fgit

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / "track_c_fpia_child.py"
COUNTERFACTUAL = HERE / "track_c_fpia_counterfactual.py"
# Loaders that execute the audited source file itself (pytest's assertion rewriter compiles the
# test/conftest source; with -B and a fresh pycache prefix nothing is read from or written to the tree).
SOURCE_LOADERS = ("SourceFileLoader", "AssertionRewritingHook")
# Parent environment names never passed to children; their presence is recorded by name only.
SCRUBBED_PREFIXES = ("PYTEST_", "PYTHON", "GIT_", "PIP_", "VIRTUAL_ENV", "CONDA", "LD_", "DYLD_")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ignored_parent_env():
    return sorted(k for k in os.environ if k.startswith(SCRUBBED_PREFIXES) or k in ("HOME", "TMPDIR", "PATH"))


class RunResult(dict):
    rc = property(lambda self: self["rc"])
    stdout = property(lambda self: self["stdout"])
    stderr = property(lambda self: self["stderr"])
    trace = property(lambda self: self.get("trace"))


class Runner:
    def __init__(self, work: Path, python=None, autoload_disabled=True):
        self.work = Path(work)
        self.autoload_disabled = autoload_disabled
        self.python = python or sys.executable
        self.launch_dir = self.work / "launcher"
        self.launch_dir.mkdir(parents=True, exist_ok=True)
        self.launcher = self.launch_dir / LAUNCHER.name
        self.counterfactual = self.launch_dir / COUNTERFACTUAL.name
        shutil.copyfile(LAUNCHER, self.launcher)
        shutil.copyfile(COUNTERFACTUAL, self.counterfactual)
        self.launcher_sha256 = sha256_file(self.launcher)
        self.counterfactual_sha256 = sha256_file(self.counterfactual)
        self.counter = 0
        self.runs = []
        import threading
        self._lock = threading.Lock()
        self.child_path = os.pathsep.join([str(Path(self.python).parent), fgit.system_path()])

    def _fresh(self, label):
        with self._lock:
            self.counter += 1
            n = self.counter
        d = self.work / "runs" / ("%03d-%s" % (n, label.replace("/", "_")[:60]))
        for sub in ("home", "tmp", "pycache"):
            (d / sub).mkdir(parents=True)
        return d

    def env(self, run_dir, pythonpath=None, extra=None):
        env = {"PATH": self.child_path, "HOME": str(run_dir / "home"), "TMPDIR": str(run_dir / "tmp"),
               "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONPYCACHEPREFIX": str(run_dir / "pycache"), "PYTHONNOUSERSITE": "1"}
        if not self.autoload_disabled:     # test-only override (recorded as a non-default option)
            env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
        if pythonpath:
            env["PYTHONPATH"] = pythonpath
        env.update(extra or {})
        return env

    def hardened(self, label, tree_root, cwd, profile, sys_path, spec_extra=None, pythonpath=None,
                 audit=False, sites=()):
        run_dir = self._fresh(label)
        spec = {"profile": profile, "cwd": str(cwd), "sys_path": [str(p) for p in sys_path],
                "trace": str(run_dir / "trace.json"), "audit": audit, "tree_root": str(tree_root),
                "sites": [list(s) for s in sites], "counterfactual_module": str(self.counterfactual),
                "probe_dir": str(run_dir / "tmp" / "probe")}
        spec.update(spec_extra or {})
        (run_dir / "spec.json").write_text(json.dumps(spec, sort_keys=True))
        cmd = [self.python, "-I", "-B", "-X", "pycache_prefix=" + str(run_dir / "pycache"),
               str(self.launcher), str(run_dir / "spec.json")]
        env = self.env(run_dir, pythonpath)
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True)
        trace = None
        if (run_dir / "trace.json").exists():
            trace = json.loads((run_dir / "trace.json").read_text())
        tr = os.path.realpath(str(tree_root))
        allowed_sp = sorted({os.path.relpath(os.path.realpath(p), tr) if os.path.realpath(p) != tr else ""
                             for p in spec["sys_path"] if os.path.realpath(p).startswith(tr)})
        result = RunResult(label=label, mode="HARDENED", profile=profile, rc=proc.returncode, allowed_sys_path=allowed_sp,
                           stdout=proc.stdout.decode("utf-8", "replace"), stderr=proc.stderr.decode("utf-8", "replace"),
                           trace=trace, run_dir=str(run_dir), cwd=str(cwd), env_names=sorted(env),
                           pythonpath=pythonpath, tmp=str(run_dir / "tmp"), pycache=str(run_dir / "pycache"))
        self._release(run_dir)
        self.runs.append({"label": label, "mode": "HARDENED", "profile": profile, "rc": proc.returncode})
        return result

    @staticmethod
    def _release(run_dir):
        """Drop the child's private TMPDIR once it has exited. Nothing reads it afterwards (the trace,
        junit files and outputs live elsewhere); test sessions can leave hundreds of MB there each."""
        shutil.rmtree(run_dir / "tmp", ignore_errors=True)

    def verbatim(self, label, cwd, argv, pythonpath=None):
        """Exactly the workflow command (``python ...``) with the whitelist environment, no -I."""
        run_dir = self._fresh(label)
        env = self.env(run_dir, pythonpath)
        cmd = [self.python] + list(argv)
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True)
        result = RunResult(label=label, mode="VERBATIM", rc=proc.returncode,
                           stdout=proc.stdout.decode("utf-8", "replace"), stderr=proc.stderr.decode("utf-8", "replace"),
                           stdout_raw=proc.stdout, stderr_raw=proc.stderr,
                           trace=None, run_dir=str(run_dir), cwd=str(cwd), env_names=sorted(env), pythonpath=pythonpath,
                           tmp=str(run_dir / "tmp"))
        self._release(run_dir)
        self.runs.append({"label": label, "mode": "VERBATIM", "argv": list(argv), "rc": proc.returncode})
        return result


# ---- trace validation -------------------------------------------------------------------------------
def runtime_dirs():
    paths = sysconfig.get_paths()
    out = set()
    for k in ("stdlib", "platstdlib", "purelib", "platlib"):
        if k in paths:
            out.add(os.path.realpath(paths[k]))
            out.add(os.path.abspath(paths[k]))
    out.add(os.path.realpath(os.path.dirname(os.__file__)))
    return sorted(out)


def tree_sys_path(result, tree_root):
    """sys.path entries inside the tree (repo-relative) recorded at the end of a hardened run."""
    tree_root = os.path.realpath(str(tree_root))
    out = []
    for entry in (result.trace or {}).get("sys_path", []):
        if not entry:
            continue
        real = os.path.realpath(entry)
        if real == tree_root:
            out.append("")
        elif real.startswith(tree_root + "/"):
            out.append(real[len(tree_root) + 1:])
    return sorted(set(out))


def check_trace(result, tree_root, entries, allowed_paths, baseline_meta_path, *, track_c=True,
                allowed_extra_dirs=(), complement=frozenset(), sites=(), launcher_dir=None, site_roots=(),
                reference_sys_path=()):
    """Return a list of findings (each a dict) for one hardened run."""
    findings = []
    trace = result.trace
    if trace is None:
        return [{"id": "AC-26", "finding": "trace missing", "run": result["label"]}]
    tree_root = os.path.realpath(str(tree_root))
    prefix = tree_root + "/"
    rdirs = runtime_dirs()
    tmp = os.path.realpath(result["tmp"])
    launcher_dir = os.path.realpath(str(launcher_dir)) if launcher_dir else None
    flags = trace.get("flags", {})
    for flag in ("isolated", "ignore_environment", "no_user_site", "dont_write_bytecode"):
        if not flags.get(flag):
            findings.append({"id": "AC-29", "finding": "child flag not set: " + flag, "run": result["label"]})
    for name, info in sorted(trace.get("modules", {}).items()):
        origin = info.get("origin")
        if not origin or origin in ("built-in", "frozen") or not os.path.isabs(str(origin)):
            continue
        real = os.path.realpath(origin)
        if real.startswith(prefix):
            rel = real[len(prefix):]
            if info.get("loader") not in SOURCE_LOADERS:
                findings.append({"id": "AC-26", "finding": "non-source loader from tree", "module": name,
                                 "path": rel, "loader": info.get("loader"), "run": result["label"]})
            e = entries.get(rel)
            if e is None:
                findings.append({"id": "AC-26", "finding": "module from untracked tree file", "module": name,
                                 "path": rel, "run": result["label"]})
            else:
                with open(real, "rb") as handle:
                    if fgit.blob_id(handle.read()) != e.sha:
                        findings.append({"id": "AC-26", "finding": "executed bytes differ from audited blob",
                                         "module": name, "path": rel, "run": result["label"]})
            if track_c and rel not in allowed_paths:
                findings.append({"id": "AC-26", "finding": "Track C run executed a complement module",
                                 "module": name, "path": rel, "run": result["label"]})
            cached = info.get("cached")
            if cached and os.path.realpath(cached).startswith(prefix):
                findings.append({"id": "AC-26", "finding": "bytecode cache inside tree", "module": name,
                                 "cached": cached, "run": result["label"]})
            continue
        absolute = os.path.abspath(origin)
        if any(x == d or x.startswith(d + "/") for d in rdirs for x in (real, absolute)):
            continue
        if real.startswith(tmp + "/") or (launcher_dir and real.startswith(launcher_dir + "/")):
            continue
        findings.append({"id": "AC-26", "finding": "module origin outside runtime, tree and run tmp",
                         "module": name, "origin": origin, "run": result["label"]})
    allowed_meta = set(baseline_meta_path) | {"_pytest.assertion.rewrite.AssertionRewritingHook"}
    for mp in trace.get("meta_path", []):
        if mp not in allowed_meta:
            findings.append({"id": "AC-26", "finding": "unexpected meta_path finder", "finder": mp,
                             "run": result["label"]})
    if track_c:
        allowed_sp = set(result.get("allowed_sys_path", ())) | set(reference_sys_path)
        for rel in tree_sys_path(result, tree_root):
            if rel not in allowed_sp:
                findings.append({"id": "AC-26", "finding": "unexpected sys.path entry inside tree", "entry": rel,
                                 "run": result["label"]})
    # file access provenance (review: audit hook): Track C code may read or enumerate only
    # projection and attributed (A_V) content, except the code-identity sites' *.py enumeration.
    if track_c:
        site_roots = sorted(set(site_roots))

        def names_under(paths, d):
            pre = (d + "/") if d else ""
            return {q[len(pre):].split("/")[0] for q in paths if q.startswith(pre)}

        tree_paths = set(entries)
        for ev in trace.get("events", []):
            kind = ev.get("event")
            by = ev.get("by")
            if by and by in complement:
                findings.append({"id": "AC-26.file", "finding": "complement code active in Track C run",
                                 "by": by, "run": result["label"]})
            if kind == "read":
                p = ev["path"]
                if p in complement:
                    exempt = ev.get("site") and p.endswith(".py") and any(p.startswith(r + "/") for r in site_roots)
                    if not exempt:
                        findings.append({"id": "AC-26.file", "finding": "Track C run read a complement file",
                                         "path": p, "by": by, "run": result["label"]})
            elif kind == "enumerate":
                d = ev["path"].rstrip("/")
                extra = sorted(names_under(tree_paths, d) - names_under(allowed_paths, d))
                if extra:
                    exempt = ev.get("site") and any(d == r or d.startswith(r + "/") for r in site_roots)
                    if not exempt:
                        findings.append({"id": "AC-26.file",
                                         "finding": "Track C run enumerated a directory with complement entries",
                                         "path": d, "complement_entries": extra[:10], "by": by,
                                         "run": result["label"]})
            elif kind == "glob":
                findings.append({"id": "AC-26.file", "finding": "glob by Track C code (not attributable)",
                                 "pattern": ev.get("path"), "by": by, "run": result["label"]})
    return findings


def check_spawns(result, tree_root, allowed_paths, complement):
    """Grandchild processes: script must be Track C; no complement startup hooks on their path."""
    findings = []
    trace = result.trace or {}
    tree_root = os.path.realpath(str(tree_root))
    prefix = tree_root + "/"
    startup = {c for c in complement if c.rsplit("/", 1)[-1] in ("sitecustomize.py", "usercustomize.py")
               or c.endswith(".pth") or c.rsplit("/", 1)[-1].startswith(("sitecustomize.", "usercustomize."))}
    spawns = []
    for ev in trace.get("events", []):
        if ev.get("event") != "spawn":
            continue
        argv = ev.get("argv") or []
        exe = os.path.basename(argv[0]) if argv else ""
        record = {"argv": argv[:6], "cwd": ev.get("cwd"), "by": ev.get("by"),
                  "env_names": (ev.get("env") or {}).get("__names__")}
        spawns.append(record)
        if not exe.startswith("python"):
            continue
        cwd = ev.get("cwd") or ""
        script = None
        for a in argv[1:]:
            if a.startswith("-"):
                continue
            script = a
            break
        dirs = []
        if script and script.endswith(".py"):
            full = os.path.realpath(os.path.join(cwd, script))
            if full.startswith(prefix):
                rel = full[len(prefix):]
                if rel not in allowed_paths:
                    findings.append({"id": "AC-26.spawn", "finding": "grandchild runs a non-Track C script",
                                     "script": rel, "run": result["label"]})
                dirs.append(os.path.dirname(rel))
        pp = None
        env = ev.get("env")
        if env and "PYTHONPATH" in env:
            pp = env["PYTHONPATH"]
        elif ev.get("inherits_env"):
            pp = ev.get("parent_pythonpath")
        for entry in (pp or "").split(os.pathsep):
            if not entry:
                continue
            full = os.path.realpath(os.path.join(cwd, entry))
            if full.startswith(prefix):
                dirs.append(full[len(prefix):])
            elif full == tree_root:
                dirs.append("")
        for d in dirs:
            hits = sorted(s for s in startup if (s.rsplit("/", 1)[0] if "/" in s else "") == d)
            if hits:
                findings.append({"id": "AC-26.spawn", "finding": "grandchild import path holds complement startup hook",
                                 "dir": d, "files": hits, "run": result["label"]})
    return findings, spawns


def verify_tree_after(result, tree_root, entries, allowed_extra_dirs):
    problems = fgit.verify_tree(tree_root, entries, allowed_extra_dirs)
    return [{"id": "AC-31", "finding": "tree changed during run", "problem": list(p), "run": result["label"]}
            for p in problems]


# ---- pytest evidence ------------------------------------------------------------------------------
def junit_counts(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    out = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for s in suites:
        for k in out:
            out[k] += int(s.get(k, "0"))
    return out


def node_outcomes(reports):
    out = {}
    for node, phases in reports.items():
        if phases.get("setup") == "failed" or phases.get("teardown") == "failed":
            out[node] = "error"
        elif "call" in phases:
            out[node] = phases["call"]
        elif phases.get("setup") == "skipped":
            out[node] = "skipped"
        else:
            out[node] = phases.get("setup", "unknown")
    return out


def recorder_counts(reports):
    outcomes = node_outcomes(reports)
    counts = {"tests": len(outcomes), "failures": 0, "errors": 0, "skipped": 0}
    for node, phases in reports.items():
        if phases.get("call") == "failed":
            counts["failures"] += 1
        if phases.get("setup") == "failed" or phases.get("teardown") == "failed":
            counts["errors"] += 1
        if outcomes[node] in ("skipped", "xfailed"):
            counts["skipped"] += 1
    return counts


def normalise_node(nodeid, rootdir_rel):
    """Node id with its file part made repository-relative."""
    if not rootdir_rel:
        return nodeid
    return rootdir_rel.rstrip("/") + "/" + nodeid


# ---- runtime provenance ---------------------------------------------------------------------------------
def distributions():
    out = {}
    for dist in metadata.distributions():
        name = (dist.metadata["Name"] or "").lower()
        out[name] = dist.version
    return dict(sorted(out.items()))


def verify_site_packages():
    """Hash-check every installed distribution's RECORD and every startup hook file in site dirs."""
    problems = []
    listed = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        record = dist.read_text("RECORD")
        if record is None:
            problems.append({"dist": name, "problem": "no RECORD"})
            continue
        base = Path(dist.locate_file(""))
        for row in csv.reader(io.StringIO(record)):
            if not row:
                continue
            rel, digest = row[0], row[1] if len(row) > 1 else ""
            full = (base / rel).resolve()
            listed[str(full)] = digest
            if not digest:
                continue
            if "__pycache__" in Path(rel).parts and rel.endswith(".pyc"):
                # Hardened and verbatim children run with a fresh pycache prefix, so installed
                # bytecode caches are never read; they are regenerated caches, not RECORD content.
                continue
            algo, _, value = digest.partition("=")
            if algo != "sha256":
                problems.append({"dist": name, "file": rel, "problem": "unsupported digest " + algo})
                continue
            try:
                data = full.read_bytes()
            except OSError:
                problems.append({"dist": name, "file": rel, "problem": "missing"})
                continue
            import base64
            actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            if actual != value:
                problems.append({"dist": name, "file": rel, "problem": "hash mismatch"})
    hooks = []
    for d in {sysconfig.get_paths()[k] for k in ("purelib", "platlib")}:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".pth") or name.split(".")[0] in ("sitecustomize", "usercustomize"):
                full = str(Path(d, name).resolve())
                hooks.append({"file": full, "sha256": sha256_file(full), "listed_in_RECORD": full in listed})
                if full not in listed or not listed[full]:
                    problems.append({"file": full, "problem": "startup hook not hash-listed in any RECORD"})
    for d in {sysconfig.get_paths()[k] for k in ("stdlib", "platstdlib")}:
        for name in ("sitecustomize.py", "usercustomize.py"):
            full = os.path.join(d, name)
            if os.path.exists(full):
                data = Path(full).read_bytes()
                import ast as _ast
                try:
                    inert = not _ast.parse(data).body
                except SyntaxError:
                    inert = False
                hooks.append({"file": full, "sha256": hashlib.sha256(data).hexdigest(), "interpreter_owned": True,
                              "inert": inert})
                if not inert:
                    problems.append({"file": full, "problem": "non-inert startup hook in the interpreter stdlib dir"})
    return problems, hooks
