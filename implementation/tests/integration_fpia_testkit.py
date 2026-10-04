"""Synthetic world W for the FPIA Tier 1 tests.

Everything is generated at test time in a temporary directory: a git repository with a canonical
commit K, a Track C lineage (START6 -> E6 -> ... -> R0) whose frozen tools are the REAL in-tree tool
sources with only their 40-hex anchor constants rewritten to W's commits, Frozen records and CI logs
produced by actually running those tools at W's evidence heads, a v2 head V0, a foreign capability
merge T0, and a handoff branch carrying a CDR-TEST register section with an fpia-reference-manifest.
No fixture bytes, bytecode, plugins or configuration are committed to the repository.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMPL_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = IMPL_DIR / "tools"
REPO_ROOT = IMPL_DIR.parent

from tools.integration import track_c_fpia as fpia  # noqa: E402
from tools.integration import track_c_fpia_auth as fauth  # noqa: E402
from tools.integration import track_c_fpia_derive as fd  # noqa: E402
from tools.integration import track_c_fpia_git as fgit  # noqa: E402

REGISTER = fauth.REGISTER_PATH
HANDOFF = "refs/heads/" + fauth.HANDOFF_BRANCH
WORKFLOW = fd.TRACK_C_WORKFLOW
TEST_CDR = "CDR-TEST"


def _tool_sources():
    out = {}
    for p in sorted(TOOLS_DIR.glob("track_c_*acceptance*.py")):
        model = fd.ToolModel("implementation/tools/" + p.name, p.read_bytes())
        out[model.kind] = ("implementation/tools/" + p.name, p.read_text())
    return out


TOOLS = _tool_sources()
C6_PATH, C7_PATH, C8_PATH = TOOLS["C6"][0], TOOLS["C7"][0], TOOLS["C8_PARTIAL"][0]
_MODELS = {k: fd.ToolModel(v[0], v[1].encode()) for k, v in TOOLS.items()}
OVERLAYS = sorted(_MODELS["C8_PARTIAL"].append_only)
DR = [p for p in OVERLAYS if p.startswith("implementation/reports/")][0]
ROOT_OVERLAYS = [p for p in OVERLAYS if not p.startswith("implementation/")]
HANDOFF_HISTORY = sorted(p for p in _MODELS["C6"].allowed if not p.startswith("implementation/") and p not in OVERLAYS)[0]
IF1 = sorted(p for p in _MODELS["C6"].allowed if p.startswith("implementation/src/"))
LINEAGE = _MODELS["C6"].start_equal_literals[0]
BRANCH = _MODELS["C6"].consts["BRANCH"]
CANON_REF = "refs/remotes/origin/" + BRANCH
NETWORK_FILE = "implementation/" + fpia.NETWORK_NODE.split("::")[0]
NFC_REPORT = "implementation/reports/track_c_r\u00e9sum\u00e9_2001.md"
NETWORK_TEST = fpia.NETWORK_NODE.split("::")[1]


def rewrite_constants(source, mapping):
    """Rewrite only module-level 40-hex string constants NAME='...' (the tool's anchors)."""
    out = source
    for name, value in mapping.items():
        out, n = re.subn(r"(?m)^(%s\s*=\s*)(['\"])[0-9a-f]{40}\2" % re.escape(name), lambda m: m.group(1) + m.group(2) + value + m.group(2), out)
        if n != 1:
            raise AssertionError("constant %s not rewritten exactly once" % name)
    return out


def pins_line():
    import importlib.metadata as md
    pins = ["pytest==" + md.version("pytest")]
    try:
        pins.append("numpy==" + md.version("numpy"))
    except md.PackageNotFoundError:
        pass
    return " ".join(pins)


def workflow(kinds, pinned=True):
    steps = ["      - name: Fetch current canonical and Track C remotes",
             "        run: git fetch --no-tags origin %s feature/track-c-evl" % BRANCH,
             "      - uses: actions/setup-python@v5",
             "        with:",
             '          python-version: "%d.%d"' % sys.version_info[:2],
             "      - name: Install pytest",
             "        run: python -m pip install %s" % (pins_line() if pinned else "pytest")]
    for k in ("8", "7", "6"):
        if ("C8_PARTIAL" if k == "8" else "C" + k) in kinds:
            steps += ["      - name: Targeted C%s tests" % k, "        run: PYTHONPATH=src python -m pytest -q tests/test_evl_c%s*.py" % k]
    steps += ["      - name: Previous phase C0-C5 regression", "        run: PYTHONPATH=src python -m pytest -q tests/test_evl_c[0-5]*.py",
              "      - name: Full regression", "        run: PYTHONPATH=src python -m pytest -q"]
    for kind in ("C6", "C7", "C8_PARTIAL"):
        if kind in kinds:
            steps += ["      - name: %s acceptance" % kind,
                      "        run: PYTHONPATH=src:. python tools/%s" % TOOLS[kind][0].rsplit("/", 1)[1]]
    head = ["name: track-c-evl-validation", "on:", "  workflow_dispatch:", "permissions:", "  contents: read", "jobs:",
            "  validate:", "    runs-on: ubuntu-latest", "    defaults:", "      run:", "        working-directory: implementation",
            "    steps:", "      - uses: actions/checkout@v4", "        with:", "          fetch-depth: 0"]
    return "\n".join(head + steps) + "\n"


# ---- doubles (file contents) -----------------------------------------------------------------------
WALKFORWARD = '''import hashlib
import json


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
'''
C6_FIXTURE = '''from hashlib import sha256
import json
from pathlib import Path

from investment_system.contracts import lineage as _lineage
from investment_system.evl.walkforward import digest

_SOURCE = Path(__file__).resolve().parents[1] / "src" / "investment_system"
CODE = sha256(b"".join(p.relative_to(_SOURCE).as_posix().encode() + b"\\\\0" + p.read_bytes()
                       for p in sorted(_SOURCE.rglob("*.py")))).hexdigest()


def full_acceptance(path):
    path.mkdir(parents=True, exist_ok=True)
    note = Path(__file__).resolve().parent / "zz_note.txt"
    result = {"status": "PASS", "scope": "SYNTHETIC", "code": CODE, "families": ["a", "b"],
              "note": note.read_text() if note.exists() else None,
              "lineage_marker": getattr(_lineage, "_SHADOW_MARKER", None)}
    if (Path(__file__).resolve().parent / "zz_block.txt").exists():
        result["status"] = "BLOCKED"
    (path / "families.json").write_text(json.dumps(result, sort_keys=True))
    return result
'''
C0_TEST = '''from investment_system.evl.walkforward import digest


def test_digest_is_stable():
    assert digest({"a": 1}) == digest({"a": 1})


def test_no_lookahead_boundary_fails_closed():
    assert digest({"t": 1}) != digest({"t": 2})
'''
C6_TEST = '''from tests.evl_c6_fixture import full_acceptance


def test_c6_acceptance(tmp_path):
    assert full_acceptance(tmp_path)["status"] == "PASS"


def test_holdout_boundary_is_unconsumed(tmp_path):
    assert full_acceptance(tmp_path / "h")["scope"] == "SYNTHETIC"
'''
PROFILE_SELECTION = 'STAGES = ("CENTER", "PLATEAU")\n'
C7_FIXTURE = '''import json

from tests.evl_c6_fixture import CODE
from investment_system.evl.profile_selection import STAGES
from investment_system.evl.walkforward import digest


def full_acceptance(path):
    selection = path / "selection"
    selection.mkdir(parents=True, exist_ok=True)
    report = {"output": {"stages": [{"stage": s} for s in STAGES]}, "code": CODE}
    (selection / "selection-report.json").write_text(json.dumps(report, sort_keys=True))
    return {"acceptance": {"status": "PASS"}, "report_hash": digest(report), "code_hash": CODE}
'''
C7_TEST = '''from tests.evl_c7_fixture import full_acceptance


def test_c7_acceptance(tmp_path):
    assert full_acceptance(tmp_path)["acceptance"]["status"] == "PASS"


def test_c7_future_feature_rejected():
    assert True
'''
CONTRACTS = '''from hashlib import sha1, sha256
import json
from pathlib import Path

POLICY = "TC-TEST-POLICY"
APPROVAL_BLOB = "{blob}"
APPROVAL_PATH = Path(__file__).resolve().parents[3] / "reports" / "{approval}"
BLOCKED = ("A6",)


class IntegrityFailure(ValueError):
    """Synthetic integrity failure."""


def authority():
    raw = APPROVAL_PATH.read_bytes()
    if sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest() != APPROVAL_BLOB:
        raise IntegrityFailure("changed/missing current partial approval authority")
    return json.loads(raw)


def code_hash():
    root = Path(__file__).resolve().parents[1]
    return sha256(b"".join(p.relative_to(root).as_posix().encode() + b"\\0" + p.read_bytes()
                           for p in sorted(root.rglob("*.py")))).hexdigest()


def validate_plan(plan):
    p = dict(plan)
    authority()
    if p["code_hash"] != code_hash():
        raise IntegrityFailure("current code identity mismatch")
    return p
'''
PROTOCOL = '''from .calibration_contracts import code_hash, validate_plan


def register_calibration(ledger, plan):
    validate_plan(plan)
    return {"registered": True, "code": code_hash()}
'''
PROTOCOL_SKIPPING = '''from .calibration_contracts import code_hash, validate_plan


def register_calibration(ledger, plan):
    return {"registered": True, "code": code_hash()}
'''
C8_FIXTURE = '''from investment_system.evl.calibration_contracts import APPROVAL_BLOB, code_hash
from investment_system.evl.calibration_protocol import register_calibration


def prepare_source(path):
    path.mkdir(parents=True, exist_ok=True)
    return {"source": "synthetic"}


def setup(path, source):
    return {"plan": {"code_hash": code_hash(), "approval_blob": APPROVAL_BLOB}, "source": source}


def register(rig):
    return register_calibration(None, rig["plan"])


def full_acceptance(path):
    rig = setup(path, prepare_source(path / "source"))
    register(rig)
    artifact = {"code_hash": code_hash(), "software_freeze_eligible": False, "real_pit_research_validated": False,
                "research_state": None, "promotion_authority": None, "official": False,
                "real_holdout_eligible": False}
    return {"status": "APPROVED_FOUNDATION_PROTOCOL_PASS", "C8_SOFTWARE_FROZEN": False, "artifact": artifact}
'''
C8_TEST = '''import pytest

from investment_system.evl.calibration_contracts import IntegrityFailure
from tests import evl_c8_fixture as fx


def test_registration_binds_current_code(tmp_path):
    rig = fx.setup(tmp_path, fx.prepare_source(tmp_path / "s"))
    assert fx.register(rig)["registered"]


def test_stale_code_identity_fails_closed(tmp_path):
    rig = fx.setup(tmp_path, fx.prepare_source(tmp_path / "s"))
    rig["plan"]["code_hash"] = "stale"
    with pytest.raises(IntegrityFailure):
        fx.register(rig)


def test_calibration_boundary_and_identity_fail_closed_holdout_role():
    assert True


def test_no_lookahead_future_dataset():
    assert True
'''
SIMPLE_TEST = '''def test_{name}():
    assert True
'''
V2_SOURCE = '''from hashlib import sha1
import json
from pathlib import Path

from .walkforward import digest

APPROVAL_PATH = (Path(__file__).resolve().parents[3] / "docs/codex_test/"
                 "v2/CDR_TEST_APPROVAL.json")
APPROVAL_BLOB = "{blob}"


def authority():
    raw = APPROVAL_PATH.read_bytes()
    if sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest() != APPROVAL_BLOB:
        raise ValueError("changed v2 approval")
    return json.loads(raw)


def statistic(values):
    authority()
    return {"value": sum(v * v for v in values), "digest": digest(list(values))}
'''
V2_TEST = '''import os
import subprocess
import sys

from investment_system.evl.superiority_v2 import statistic


def test_v2_statistic():
    assert statistic([1.0, 2.0])["value"] == 5.0


def test_v2_grandchild_process():
    proc = subprocess.run([sys.executable, "-c", "print(1)"], env=dict(os.environ, PYTHONPATH="src"),
                          capture_output=True, text=True)
    assert proc.returncode == 0
'''
V2_TOOL = '''import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from investment_system.evl.superiority_v2 import statistic  # noqa: E402

print(json.dumps({"status": "PASS", "statistic": statistic([1.0, 2.0, 3.0])}, sort_keys=True))
'''
V2_WORKFLOW = '''name: codex-test-readiness
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  combined-offline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: v2 replay
        run: python implementation/tools/verify_v2_test.py > /tmp/v2.json
'''
FOREIGN_WORKFLOW = '''name: rig-news
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: rig tests
        run: cd implementation && PYTHONPATH=src python -m pytest -q tests/test_rig_news.py
'''


# ---- git plumbing --------------------------------------------------------------------------------------
class Git:
    def __init__(self, repo: Path, home: Path):
        self.repo = Path(repo)
        self.env = {"PATH": fgit.system_path(), "HOME": str(home), "LANG": "C", "LC_ALL": "C",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "w", "GIT_AUTHOR_EMAIL": "w@invalid", "GIT_COMMITTER_NAME": "w",
                    "GIT_COMMITTER_EMAIL": "w@invalid"}
        self.tick = 0

    def __call__(self, *args, input=None, env=None, check=True, text=True):
        e = dict(self.env)
        e.update(env or {})
        proc = subprocess.run(["git", "--git-dir", str(self.repo)] + list(args), input=input, capture_output=True,
                              env=e, text=text)
        if check and proc.returncode != 0:
            raise RuntimeError("git %s: %s" % (" ".join(args[:3]), proc.stderr))
        return proc.stdout.strip() if text else proc.stdout

    def blob(self, data):
        if isinstance(data, str):
            data = data.encode()
        return subprocess.run(["git", "--git-dir", str(self.repo), "hash-object", "-w", "--stdin"], input=data,
                              capture_output=True, env=self.env, check=True).stdout.decode().strip()

    def files(self, rev):
        out = {}
        raw = self("ls-tree", "-r", "-z", "--full-tree", rev, text=False)
        for item in raw.split(b"\0"):
            if not item:
                continue
            meta, path = item.split(b"\t", 1)
            mode, typ, sha = meta.decode().split()
            out[path.decode()] = (mode, sha)
        return out

    def read(self, rev, path):
        return self("cat-file", "blob", "%s:%s" % (rev, path), text=False)

    def tree(self, files):
        """files: {path: (mode, sha)}"""
        idx = self.repo / ("idx-%d" % os.getpid())
        env = {"GIT_INDEX_FILE": str(idx)}
        self("read-tree", "--empty", env=env)
        lines = "".join("%s %s\t%s\0" % (m, s, p) for p, (m, s) in sorted(files.items()))
        self("update-index", "-z", "--index-info", input=lines, env=env)
        tree = self("write-tree", env=env)
        idx.unlink()
        return tree

    def commit(self, tree, parents, msg):
        self.tick += 1
        date = "2001-01-01T00:%02d:%02dZ" % divmod(self.tick, 60)
        args = ["commit-tree", tree]
        for p in parents:
            args += ["-p", p]
        return self(*args, "-m", msg, env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})

    def change(self, parent, changes, msg, parents=None, modes=None):
        files = dict(self.files(parent)) if parent else {}
        for path, data in changes.items():
            if data is None:
                files.pop(path, None)
            else:
                files[path] = ((modes or {}).get(path, "100644"), self.blob(data))
        for path, mode in (modes or {}).items():
            if path in files and path not in changes:
                files[path] = (mode, files[path][1])
        return self.commit(self.tree(files), parents if parents is not None else ([parent] if parent else []), msg)

    def merge(self, a, b, msg, resolve=None):
        proc = subprocess.run(["git", "--git-dir", str(self.repo), "merge-tree", "--write-tree", "--name-only",
                               "--no-messages", a, b], capture_output=True, text=True, env=self.env)
        tree = proc.stdout.split("\n")[0].strip()
        conflicted = [l for l in proc.stdout.split("\n")[1:] if l.strip()]
        if conflicted:
            if not resolve:
                raise RuntimeError("conflict: %s" % conflicted)
            files = self.files(tree)
            for path, data in resolve.items():
                files[path] = ("100644", self.blob(data))
            tree = self.tree(files)
        elif resolve:
            files = self.files(tree)
            for path, data in resolve.items():
                if data is None:
                    files.pop(path, None)
                else:
                    files[path] = ("100644", self.blob(data))
            tree = self.tree(files)
        return self.commit(tree, [a, b], msg)

    def ref(self, ref, sha):
        self("update-ref", ref, sha)


def run_tool(git, commit, tool_path, canonical, scratch):
    """Run a tool at ``commit`` exactly as the workflow step does; returns the evidence line."""
    d = Path(tempfile.mkdtemp(prefix="w-tool-", dir=scratch))
    env = dict(git.env)
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", str(git.repo), str(d)], env=env, check=True,
                   stderr=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(d), "-c", "advice.detachedHead=false", "checkout", "-q", commit], env=env, check=True)
    subprocess.run(["git", "-C", str(d), "update-ref", CANON_REF, canonical], env=env, check=True)
    for ref in subprocess.run(["git", "-C", str(d), "for-each-ref", "--format=%(refname)"], env=env, check=True,
                              capture_output=True, text=True).stdout.split():
        if ref != CANON_REF:
            subprocess.run(["git", "-C", str(d), "update-ref", "-d", ref], env=env, check=True)
    cenv = {"PATH": fgit.system_path(), "HOME": str(d), "LANG": "C.UTF-8", "PYTHONPATH": "src:.",
            "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    proc = subprocess.run([sys.executable, tool_path.split("implementation/", 1)[1]], cwd=str(d / "implementation"),
                          env=cenv, capture_output=True, text=True)
    shutil.rmtree(d, ignore_errors=True)
    if proc.returncode != 0:
        raise RuntimeError("tool %s failed at %s: %s" % (tool_path, commit[:10], proc.stderr[-2000:]))
    lines = [l for l in proc.stdout.split("\n") if "_EVIDENCE=" in l]
    assert len(lines) == 1
    return lines[0]


def logline(n, body):
    return "2001-01-01T00:00:%02d.%07dZ %s" % (n, n * 1111, body)


def evidence(line):
    return json.loads(line.split("=", 1)[1])


class World:
    """A built synthetic world (bare repository) with named commits."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.home = self.root / "home"
        self.home.mkdir(parents=True, exist_ok=True)
        self.repo = self.root / "w.git"
        self.git = Git(self.repo, self.home)
        self.c = {}

    # -- construction ----------------------------------------------------------------------------
    def build(self):
        g = self.git
        subprocess.run(["git", "init", "-q", "--bare", str(self.repo)], env=g.env, check=True)
        base = {".gitignore": "__pycache__/\n*.pyc\n",
                "implementation/src/investment_system/__init__.py": "",
                "implementation/src/investment_system/contracts/__init__.py": "",
                LINEAGE: "LINEAGE = 1\n",
                "implementation/src/investment_system/rig/__init__.py": "",
                "implementation/tests/__init__.py": "",
                "implementation/tests/conftest.py": "import pytest  # noqa: F401\n",
                NETWORK_FILE: SIMPLE_TEST.format(name=NETWORK_TEST[len("test_"):]) + "\n\n" + SIMPLE_TEST.format(name="offline_parse"),
                "implementation/tests/test_other_capability.py": SIMPLE_TEST.format(name="other"),
                HANDOFF_HISTORY: "# history\n\n- K\n"}
        for p in IF1:
            parts = p.split("/")
            for i in range(len(parts) - 1):
                d = "/".join(parts[:i + 1])
                if d.startswith("implementation/src/investment_system/") and d != "implementation/src/investment_system":
                    base.setdefault(d + "/__init__.py", "")
            base[p] = "ENGINE = '%s'\n" % parts[-2]
        for p in ROOT_OVERLAYS:
            base[p] = "# %s\n\n- canonical entry\n" % p
        K = g.change(None, base, "K canonical")
        self.c["K"] = K
        evl = "implementation/src/investment_system/evl/"
        S6 = g.change(K, {evl + "__init__.py": "", evl + "walkforward.py": WALKFORWARD,
                          "implementation/tests/test_evl_c0_basic.py": C0_TEST,
                          WORKFLOW: workflow([], pinned=False)}, "S6 Track C start")
        self.c["S6"] = S6
        c6src = rewrite_constants(TOOLS["C6"][1], {"CANONICAL": K, "START": S6})
        E6 = g.change(S6, {"implementation/tests/evl_c6_fixture.py": C6_FIXTURE,
                           "implementation/tests/test_evl_c6_basic.py": C6_TEST,
                           C6_PATH: c6src, WORKFLOW: workflow(["C6"], pinned=False)}, "E6 C6 evidence head")
        self.c["E6"] = E6
        scratch = self.root / "scratch"
        scratch.mkdir(exist_ok=True)
        l6 = run_tool(g, E6, C6_PATH, K, scratch)
        log6 = "\n".join([logline(1, "##[group]Run python -m pip install pytest"),
                          logline(2, "Successfully installed pytest-%s" % __import__("importlib.metadata").metadata.version("pytest")),
                          logline(3, l6), ""])
        rec6 = {"status": "SOFTWARE_FROZEN", "phase": "C6", "tested_head": E6, "evidence": evidence(l6)}
        R6 = g.change(E6, {"implementation/reports/track_c_c6_acceptance_2001.json": json.dumps(rec6, indent=1),
                           "implementation/reports/track_c_c6_acceptance_ci_log_2001.txt": log6,
                           DR: "# Track C decision register\n\n## D-1 synthetic\n> owner decision\n"}, "R6 C6 record")
        E6b = g.change(R6, {"implementation/reports/track_c_policy_note_2001.md": "policy preparation\n"}, "E6b policy head")
        self.c["E6b"] = E6b
        l6b = run_tool(g, E6b, C6_PATH, K, scratch)
        logb = "\n".join([logline(4, "Successfully installed pytest-%s" % __import__("importlib.metadata").metadata.version("pytest")),
                          logline(5, l6b), ""])
        recb = {"recorded_at_utc": "2001", "status": "PASS", "tested_head": E6b, "actual_C6_evidence": evidence(l6b)}
        S7 = g.change(E6b, {"implementation/reports/track_c_policy_preparation_validation_2001.json": json.dumps(recb, indent=1),
                            "implementation/reports/track_c_policy_preparation_preservation_ci_log_2001.txt": logb},
                      "S7 policy record")
        self.c["S7"] = S7
        c7src = rewrite_constants(TOOLS["C7"][1], {"START": S7})
        E7 = g.change(S7, {evl + "profile_selection.py": PROFILE_SELECTION,
                           "implementation/tests/evl_c7_fixture.py": C7_FIXTURE,
                           "implementation/tests/test_evl_c7_selection.py": C7_TEST,
                           C7_PATH: c7src, WORKFLOW: workflow(["C6", "C7"], pinned=False)}, "E7 C7 evidence head")
        self.c["E7"] = E7
        l6_7 = run_tool(g, E7, C6_PATH, K, scratch)
        l7 = run_tool(g, E7, C7_PATH, K, scratch)
        ev7 = evidence(l7)
        log7 = "\n".join([logline(6, "Successfully installed pytest-%s" % __import__("importlib.metadata").metadata.version("pytest")),
                          logline(7, l6_7), logline(8, l7), ""])
        b7 = ev7["preservation"]["boundary"]
        rec7 = {"record_kind": "SOFTWARE_FREEZE_EVIDENCE", "phase": "C7", "code_validated_head": E7,
                "code_hash": ev7["integrated"]["code_hash"], "software_acceptance_report_hash": ev7["integrated"]["report_hash"],
                "current_resolved_acceptance": ev7, "canonical": b7["canonical"], "merge_base": b7["merge_base"],
                "ahead": b7["ahead"], "behind": b7["behind"]}
        B8 = g.change(E7, {"implementation/reports/track_c_c7_acceptance_2001.json": json.dumps(rec7, indent=1),
                           "implementation/reports/track_c_c7_acceptance_ci_log_2001.txt": log7}, "B8 C7 record")
        self.c["B8"] = B8
        approval_name = "track_c_c8_partial_approval_2001.json"
        approval = json.dumps({"record_id": "TC-TEST-POLICY", "canonical_head": K, "baseline_head": B8,
                               "approval_recorded_at_kst": "2001-01-01T09:00:00+09:00"}, indent=1)
        ablob = fgit.blob_id(approval.encode())
        c8files = {evl + "calibration_contracts.py": CONTRACTS.replace("{blob}", ablob).replace("{approval}", approval_name),
                   evl + "calibration_protocol.py": PROTOCOL,
                   evl + "calibration_ledger.py": "VERSION = 1\n", evl + "calibration_evidence.py": "VERSION = 1\n",
                   "implementation/tests/evl_c8_fixture.py": C8_FIXTURE,
                   "implementation/tests/test_evl_c8_contracts.py": C8_TEST,
                   "implementation/tests/test_evl_c8_ledger.py": SIMPLE_TEST.format(name="ledger"),
                   "implementation/tests/test_evl_c8_protocol.py": SIMPLE_TEST.format(name="protocol"),
                   "implementation/tests/test_evl_c8_evidence.py": SIMPLE_TEST.format(name="evidence"),
                   "implementation/reports/" + approval_name: approval,
                   C8_PATH: rewrite_constants(TOOLS["C8_PARTIAL"][1], {"BASE": B8}),
                   WORKFLOW: workflow(["C6", "C7", "C8_PARTIAL"], pinned=False)}
        missing = [p for p in _MODELS["C8_PARTIAL"].consts["NEW_SOURCE_TESTS"] if p not in c8files]
        assert not missing, missing
        E8 = g.change(B8, c8files, "E8 C8 partial evidence head")
        self.c["E8"] = E8
        lines8 = [run_tool(g, E8, p, K, scratch) for p in (C6_PATH, C7_PATH, C8_PATH)]
        log8 = "\n".join([logline(9, "Successfully installed pytest-%s" % __import__("importlib.metadata").metadata.version("pytest"))]
                         + [logline(10 + i, l) for i, l in enumerate(lines8)] + [""])
        ev8 = evidence(lines8[2])
        cb = ev8["preservation"]["canonical_boundary"]
        rec8 = {"record_kind": "TRACK_C_C8_PARTIAL_FOUNDATION_ACTIONS_VERIFICATION", "validated_head": E8,
                "approval_blob": ablob, "acceptance": {"C6": "PASS", "C7": "PASS", "C8_partial": ev8["status"]},
                "actions": {"raw_log": "track_c_c8_partial_foundation_ci_log_2001.txt",
                            "raw_log_sha256": hashlib.sha256(log8.encode()).hexdigest()},
                "C8_SOFTWARE_FROZEN": False, "official": False, "canonical": cb["canonical"],
                "ahead": cb["ahead"], "behind": cb["behind"]}
        changes = {NFC_REPORT: "r\u00e9sum\u00e9 of the Track C lineage\n",
                   "implementation/reports/track_c_c8_partial_foundation_verification_2001.json": json.dumps(rec8, indent=1),
                   "implementation/reports/track_c_c8_partial_foundation_ci_log_2001.txt": log8,
                   DR: g.read(E8, DR).decode() + "\n## D-2 owner append\n> C8 partial recorded\n"}
        for p in ROOT_OVERLAYS:
            changes[p] = g.read(E8, p).decode() + "- Track C entry\n"
        R0 = g.change(E8, changes, "R0 Track C accepted head")
        self.c["R0"] = R0
        # v2 head
        v2approval = json.dumps({"cdr": "CDR-TEST", "approved": "v2"}, indent=1)
        vblob = fgit.blob_id(v2approval.encode())
        V0 = g.change(R0, {evl + "superiority_v2.py": V2_SOURCE.replace("{blob}", vblob),
                           "implementation/docs/codex_test/v2/CDR_TEST_APPROVAL.json": v2approval,
                           "implementation/tests/test_evl_gsup_v2_basic.py": V2_TEST,
                           "implementation/tools/verify_v2_test.py": V2_TOOL,
                           ".github/workflows/codex-test-readiness.yml": V2_WORKFLOW,
                           "implementation/docs/codex_test/notes.md": "v2 notes (not Track C)\n",
                           DR: g.read(R0, DR).decode() + "\n## V-1 additive v2 approval\n> v2 recorded\n",
                           WORKFLOW: workflow(["C6", "C7", "C8_PARTIAL"], pinned=True)}, "V0 v2 head")
        self.c["V0"] = V0
        F = g.change(K, {"implementation/src/investment_system/rig/news.py": "def headline():\n    return 'x'\n",
                         "implementation/tests/test_rig_news.py": "from investment_system.rig.news import headline\n\n\n"
                                                                   "def test_headline():\n    assert headline() == 'x'\n",
                         ".github/workflows/rig-news.yml": FOREIGN_WORKFLOW}, "F foreign capability")
        self.c["F"] = F
        T0 = g.merge(V0, F, "T0 merge foreign capability into v2 head")
        self.c["T0"] = T0
        g.ref(CANON_REF, K)
        g.ref("refs/heads/main", T0)
        G0 = self.register(R0, [V0], subjects=[T0], parent=K)
        self.c["G0"] = G0
        return self

    # -- register / authority ------------------------------------------------------------------------
    def register_text(self, R, Vs, subjects=(), cdr=TEST_CDR, extra_sections="", quote_R=None, manifest=None,
                      verbatim_extra=""):
        quote_R = quote_R or R[:7]
        v_lines = " and ".join('"%s"' % v for v in Vs)
        man = manifest or {"cdr": cdr, "track_c_reference": {"sha": R, "quoted_as": quote_R, "role": "Track C"}}
        if manifest is None and Vs:
            refs = [{"sha": v, "quoted_as": v, "role": "v2"} for v in Vs]
            man["v2_reference"] = refs[0] if len(refs) == 1 else refs
        if manifest is None:
            man["verification_subjects"] = [{"sha": s, "quoted_as": s[:7], "role": "subject"} for s in subjects]
        lines = ["# COORDINATION_DECISION_REGISTER (synthetic)", "", "## CDR-OLD · earlier", "> nothing here", "",
                 "## %s · synthetic FPIA approval" % cdr,
                 '> Track C reference "%s"%s.' % (quote_R, (" and v2 head " + v_lines) if Vs else ""),
                 "> verification subject %s is not a reference." % (" ".join(s[:7] for s in subjects) or "none")]
        if verbatim_extra:
            lines.append(verbatim_extra)
        lines += ["", "```fpia-reference-manifest", json.dumps(man), "```", ""]
        return "\n".join(lines) + extra_sections

    def register(self, R, Vs, subjects=(), parent=None, text=None, move_tip=True, evidence=True, **kw):
        g = self.git
        if parent is None and self._has(HANDOFF):
            parent = g("rev-parse", HANDOFF)
        body = text if text is not None else self.register_text(R, Vs, subjects, **kw)
        changes = {REGISTER: body}
        if evidence and Vs:
            # integration evidence that verified V (the external premise for V's register appends)
            changes[REGISTER.rsplit("/", 1)[0] + "/evidence/GIE-TEST.json"] = json.dumps(
                {"verified_v2_head": Vs[0], "scoped_register": "byte-prefix append; no out-of-scope approval"})
        G = g.change(parent, changes, "register")
        if move_tip:
            g.ref(HANDOFF, G)
        return G

    def _has(self, ref):
        return subprocess.run(["git", "--git-dir", str(self.repo), "rev-parse", "--verify", "--quiet", ref],
                              capture_output=True, env=self.git.env).returncode == 0

    # -- variants ----------------------------------------------------------------------------------
    def clone(self, dest: Path):
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        w = World(dest)
        subprocess.run(["git", "clone", "-q", "--mirror", "--shared", str(self.repo), str(w.repo)], env=self.git.env, check=True)
        w.c = dict(self.c)
        w.git.tick = self.git.tick + 1000
        return w

    def fpia(self, T, G=None, cdr=TEST_CDR, options=None, keep=False, work=None):
        opts = {"authority_remote": str(self.repo), "require_clean_verifier": False}
        opts.update(options or {})
        work = Path(work) if work else Path(tempfile.mkdtemp(prefix="w-fpia-", dir=self.root))
        if work.exists() and any(work.iterdir()):
            work = Path(tempfile.mkdtemp(prefix="w-fpia-", dir=self.root))
        doc = fpia.run_fpia(str(self.repo), T, G or self.c["G0"], cdr, work_dir=str(work / "w"), keep_work=keep,
                            options=opts)
        return doc["result"]

    def audit(self, T, G=None, cdr=TEST_CDR, options=None):
        """Static-phase audit object (authority, derivation, reference checks, static checks)."""
        opts = {"authority_remote": str(self.repo), "require_clean_verifier": False}
        opts.update(options or {})
        work = Path(tempfile.mkdtemp(prefix="w-audit-", dir=self.root))
        a = fpia.Audit(str(self.repo), T, G or self.c["G0"], cdr, work, opts)
        a.T = a.resolve(T, "t")
        a.G = a.resolve(G or self.c["G0"], "g")
        a.populate([a.T, a.G])
        a.result["subject"] = {}
        auth = fauth.authenticate(a.sb, a.G, cdr, a.fetch_refs, opts["authority_remote"])
        a.result["authority"] = dict(auth)
        a.auth = auth
        if auth["status"] != "PASS":
            return a
        a.R, a.Vs = auth["R"], auth["Vs"]
        try:
            a.derive()
        except fd.ShapeError as exc:
            a.shape_error = str(exc)
            return a
        a.shape_error = None
        a.ref_status = a.reference_checks()
        if a.ref_status == "PASS":
            a.static_phase()
        return a


_BASE = {}


def base_world():
    """The base world, built once per process."""
    if "w" not in _BASE:
        root = Path(tempfile.mkdtemp(prefix="fpia-world-"))
        atexit.register(shutil.rmtree, root, True)
        _BASE["w"] = World(root / "base").build()
        _BASE["root"] = root
    return _BASE["w"]


def variant(tmp_path):
    return base_world().clone(Path(tmp_path) / "variant")


def ids(findings):
    return sorted({f.get("id") for f in findings})
