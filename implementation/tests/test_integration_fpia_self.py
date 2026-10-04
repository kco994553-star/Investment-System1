"""FPIA self-constraints: closed path literals, no numeric thresholds, no SHA/PR literals, clean
placement (AC-14, AC-39, AC-40, AC-41) and the workflow contract (pull_request + dispatch, F6)."""
import ast
import re

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia_checks as fchk
from tools.integration import track_c_fpia_derive as fd

FPIA_DIR = tk.TOOLS_DIR / "integration"
SOURCES = sorted(FPIA_DIR.glob("track_c_fpia*.py"))
TESTS = sorted((tk.IMPL_DIR / "tests").glob("test_integration_fpia_*.py")) + [
    tk.IMPL_DIR / "tests" / "integration_fpia_testkit.py", tk.IMPL_DIR / "tests" / "integration_fpia_real_history_checks.py"]
WORKFLOW = tk.REPO_ROOT / ".github" / "workflows" / "track-c-fpia.yml"
# The only repository locations FPIA names (discovery anchors) plus the single network node.
ANCHORS = {fd.TRACK_C_WORKFLOW, fd.WORKFLOW_DIR, fd.TOOL_GLOB, fd.RECORD_GLOB, fd.CI_LOG_GLOB, fd.IMPL,
           "implementation/tools", "implementation/src", "implementation/tests",
           "implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md",
           "tests/test_raw_and_providers.py::test_live_sec_fetch_is_optional_and_not_stage2", "implementation/"}


def strings(path):
    return [n.value for n in ast.walk(ast.parse(path.read_bytes())) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_fpia_path_literals_closed():
    for path in SOURCES:
        for s in strings(path):
            if s.startswith(("implementation/", ".github/", "tools/track_c_", "tests/test_evl")):
                assert s in ANCHORS, (path.name, s)


def test_no_numeric_thresholds():
    for path in SOURCES:
        tree = ast.parse(path.read_bytes())
        for n in ast.walk(tree):
            assert not (isinstance(n, ast.Constant) and isinstance(n.value, float)), (path.name, n.lineno)
            if isinstance(n, ast.Call):
                name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
                assert name not in ("isclose", "allclose"), (path.name, n.lineno)
                assert not any(k.arg == "timeout" for k in n.keywords), (path.name, n.lineno)
            if isinstance(n, ast.Compare) and any(isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)) for op in n.ops):
                consts = [c for c in [n.left] + n.comparators if isinstance(c, ast.Constant) and isinstance(c.value, (int, float))]
                assert all(c.value in (0, 1, 2) for c in consts), (path.name, n.lineno)


def test_no_sha_or_pr_literals():
    files = SOURCES + TESTS + [WORKFLOW]
    for path in files:
        assert path.exists(), path
        text = path.read_text()
        assert not re.search(r"(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])", text), path.name
        pr_patterns = ["P" "R #", "pu" "ll/", "#" "40" + r"\b"]
        assert not any(re.search(pat, text) for pat in pr_patterns), path.name
        if path.suffix == ".py":
            for s in strings(path):
                assert not (re.fullmatch(r"[0-9a-f]{7,40}", s) and re.search(r"\d", s) and re.search(r"[a-f]", s)), \
                    (path.name, s)


def test_no_pinning_or_monkeypatch_in_fpia_sources():
    """Attribute rebinding of imported modules exists only in the counterfactual profile module, and
    no FPIA module names the Track C code-identity symbols (they are discovered by AST)."""
    for path in SOURCES:
        tree = ast.parse(path.read_bytes())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "setattr"]
        if path.name == "track_c_fpia_counterfactual.py":
            assert calls
            continue
        assert not calls, path.name
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | set(strings(path))
        assert "code_hash" not in names and "CODE" not in names, path.name


def test_no_track_c_imports_in_fpia():
    tcm = {"investment_system.evl", "tests.evl_c6_fixture", "tools.track_c_c6_acceptance"}
    for path in SOURCES + TESTS:
        names = fd.module_imports(path.read_bytes(), "implementation/tools/integration/" + path.name, fd.STATIC_ROOTS)
        assert names is not None
        assert not fchk.references_track_c(names, tcm), path.name


def test_fpia_files_complement_clean(tmp_path):
    """FPIA's own files, added to T0, raise no complement finding (self-placement, AC-41)."""
    w = tk.variant(tmp_path)
    changes = {}
    for path in SOURCES:
        changes["implementation/tools/integration/" + path.name] = path.read_bytes()
    for path in TESTS:
        changes["implementation/tests/" + path.name] = path.read_bytes()
    changes[".github/workflows/track-c-fpia.yml"] = WORKFLOW.read_bytes()
    vendor = "implementation/tools/integration/_vendor/"
    for path in sorted((FPIA_DIR / "_vendor").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            changes[vendor + path.relative_to(FPIA_DIR / "_vendor").as_posix()] = path.read_bytes()
    assert vendor + "yaml/__init__.py" in changes
    T = w.git.change(w.c["T0"], changes, "add FPIA files")
    a = w.audit(T)
    assert a.ref_status == "PASS"
    assert a.static_findings == [], a.static_findings
    for p in changes:
        assert not a.proj.ns(p), p
        assert "conftest" not in p
        assert not p.endswith("__init__.py") or p.startswith(vendor), p   # packages only in FPIA's new _vendor tree


def test_workflow_contract_pull_request_and_dispatch():
    """Fix round F6: pull_request (PR head SHA as the subject, not the synthetic merge) plus
    workflow_dispatch; read-only; the job fails only through FPIA's own exit code (1 FAIL, 2 NOT_RUN)."""
    text = WORKFLOW.read_text()
    wf = fd.parse_workflow(text)
    assert wf["name"] == "track-c-fpia" and "validate" not in wf["jobs"]
    on = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "\n  pull_request:" in "\n" + on and "\n  workflow_dispatch:" in "\n" + on
    assert "\n  push:" not in "\n" + on
    assert "contents: read" in text and "write" not in text.split("\npermissions:", 1)[1].split("\njobs:", 1)[0]
    assert "fetch-depth: 0" in text and "timeout-minutes:" in text
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in text
    assert "github.event.pull_request.head.sha" in text.split("FPIA_TREE:", 1)[1].split("\n", 1)[0]
    runs = "\n".join(s["run"] for s in wf["steps"])
    assert "${{" not in runs                        # event data reaches the shell only through env
    assert "GITHUB_STEP_SUMMARY" in text and "FPIA_REQUIRE_HISTORY" in text
    audit = [s for s in wf["steps"] if "track_c_fpia.py" in s["run"]]
    assert len(audit) == 1 and audit[0]["run"].rstrip().endswith("exit $rc")
    assert "--out \"$out/fpia.json\"" in audit[0]["run"] and 'r["statuses"]' in audit[0]["run"]
    gated = [s for s in wf["steps"] if "-m pytest" in s["run"]]      # Tier 1/2 run on dispatch only
    assert gated and all("if: github.event_name == 'workflow_dispatch'" in text.split(s["run"], 1)[0].rsplit("- name:", 1)[1]
                         for s in gated)
    upload = text.split("actions/upload-artifact", 1)[1]
    assert "if: always()" in upload and "fpia-out/" in upload
