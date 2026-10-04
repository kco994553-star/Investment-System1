"""FPIA self-constraints: closed path literals, no numeric thresholds, no SHA/PR literals, clean
placement (AC-14, AC-39, AC-40, AC-41) and the dispatch-only workflow contract."""
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
    T = w.git.change(w.c["T0"], changes, "add FPIA files")
    a = w.audit(T)
    assert a.ref_status == "PASS"
    assert a.static_findings == [], a.static_findings
    for p in changes:
        assert not a.proj.ns(p), p
        assert not p.endswith("__init__.py") and "conftest" not in p


def test_dispatch_workflow_contract():
    text = WORKFLOW.read_text()
    wf = fd.parse_workflow(text)
    assert wf["name"] == "track-c-fpia" and "validate" not in wf["jobs"]
    assert "workflow_dispatch:" in text and "pull_request" not in text and "\n  push:" not in text
    assert "contents: read" in text and "fetch-depth: 0" in text
    assert "GITHUB_STEP_SUMMARY" in text and "FPIA_REQUIRE_HISTORY" in text
    assert "${{ inputs." not in "\n".join(s["run"] for s in wf["steps"])
