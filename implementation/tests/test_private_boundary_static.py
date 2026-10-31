"""Public / private boundary, repository side (owner approval 2026-10-31; design PRIVATE_AREA_KIS_DESIGN_20261031.md §7, §18.3,
§20.1). Owner rule: "공개 저장소, Pages, 공개 Actions 로그·결과물에는 KIS 자료를 절대 넣지 않는다."

Static and offline. Files: `git ls-files --cached --others --exclude-standard` (tracked plus not-yet-added files, so a new file
is checked before it is committed; a plain walk if git is unavailable), `.gz` members decompressed.
- no file carries a `kis-` schema (a schema / schema_version value), in raw text or anywhere in a parsed JSON, or the CSV
  ledger comment `# schema: kis-…` (security review B1, 10/31: collector CSV ledgers start with that line, chart files carry
  a `kis-bars` schema);
- no code or data file (Markdown documentation excepted) carries a private-area schema name: the new private-area families
  (`private-bars/`, `private-quote/`, `private-liquidity/` + version, anywhere) or any other `private-` schema value, except
  the legacy names in LEGACY_PRIVATE_SCHEMAS, each of which must still be present (no stale entry);
- KIS hosts and TR ids appear only in KIS_MARKER_FILES (each with its reason); FUTURE_MARKER_FILES may exist later;
- no public workflow references secrets.KIS_*, the KIS Secret names, a KIS host or TR id, the collector module, or runs
  anything from the private_area package;
- the public web app and web_assets sources request no private Worker path (/kis/, /lab/, /private/).
- the two KIS Secret names (any spelling, GUARD.KIS_SECRET_NAME) appear in no public code, config, workflow or data file:
  the KIS keys live only in the private repository investment-system1-kis-private (owner 2026-10-31); only Markdown
  documentation may name them.
The KIS marker and private-path patterns are the Pages guard's own (tools/pages_artifact_guard.py), so the two cannot drift.
Canaries below are assembled at run time so this file carries no marker itself.
"""
import gzip
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
_SPEC = importlib.util.spec_from_file_location("private_boundary_guard", ROOT / "tools" / "pages_artifact_guard.py")
GUARD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(GUARD)

# Files allowed to name a KIS host or TR id, with the reason. An entry that exists must still contain a marker (no stale entry).
KIS_MARKER_FILES = {
    "implementation/docs/manual_quotes_owner/KIS_DIRECT_API_RESEARCH_26E.md":
        "KIS Open API research (2026-10-09): official hosts and quotation TR ids, prose only",
    "implementation/docs/manual_quotes_owner/KIS_DIRECT_API_SOURCES_26E.json":
        "source excerpts of that research (official KIS API pages as fetched)",
    "implementation/docs/manual_quotes_owner/DIRECT_API_SOURCES_26E.json":
        "source excerpts of the direct-API service comparison, the KIS pages included",
    "implementation/docs/manual_quotes_owner/DIRECT_API_SERVICE_OPTIONS_26E.md":
        "direct-API service comparison that names the KIS host",
    "implementation/docs/private_area/PRIVATE_AREA_KIS_DESIGN_20261031.md":
        "private-area design (#436): KIS routes, TR ids and hosts in prose",
    "implementation/docs/private_area/OWNER_PHONE_SETUP_PRIVATE_AREA_20261031.md":
        "owner phone steps for the private area (KIS portal host)",
    "implementation/src/investment_system/private_area/kis_routes.py":
        "the KIS route allow list: the one quotation TR id, no host",
}
# Not written yet (collector PR, design §3.2 / §13 step 2). Allowed when they appear; no marker required.
FUTURE_MARKER_FILES = {
    "implementation/src/investment_system/private_area/kis_collector.py": "the collector module (private repository Actions only)",
    "implementation/tests/test_kis_collector.py": "its tests on synthetic data",
}
COLLECTOR_MODULE = "kis_collector"
WEB_SOURCE_DIRS = ("implementation/src/investment_system/product/web_app/",
                   "implementation/src/investment_system/product/web_assets/")
WEB_SOURCE_FILES = ("implementation/src/investment_system/product/web_mvp.py",)
WEB_TEXT_SUFFIXES = (".js", ".mjs", ".cjs", ".html", ".css", ".json", ".txt", ".webmanifest", ".svg")
MAX_GZIP_BYTES = 64 * 1024 * 1024

KIS_SCHEMA_TEXT = re.compile(r"""(?m)["']schema(?:_version)?["']\s*:\s*["']\s*kis-|^\s*schema(?:_version)?\s*:\s*["']?\s*kis-"""
                             r"""|^\ufeff?\s*#\s*schema(?:_version)?\s*[:=]\s*["']?\s*kis-""")   # CSV ledger comment line
# Private-area schema names (security review B1, 10/31). Legacy: the names the existing device price-history code uses today.
LEGACY_PRIVATE_SCHEMAS = {
    "private-history/1": "the existing /history Worker answer (device RAM only), read by the web assets, tools and fixtures",
    "private-history/2": "a refused-version input in tests/test_chart_bars.py (the reader must reject it)",
}
NEW_PRIVATE_SCHEMA_NAME = re.compile(r"(?i)(?<![a-z0-9_-])private-(?:bars|quote|liquidity)/[0-9]+")
PRIVATE_SCHEMA_TEXT = re.compile(
    r"""(?im)(?:(?<![a-z0-9])schema(?:_version)?["'`]?\s*(?:===?|[:=])\s*["'`]\s*"""
    r"""|^\ufeff?\s*(?:#\s*)?schema(?:_version)?\s*[:=]\s*["']?\s*)(private-[^\s"'`,;)}\]]*)""")
WORKFLOW_SECRET = re.compile(r"""secrets\s*(?:\.\s*|\[\s*["']\s*)kis_""")          # casefolded text: GitHub names ignore case
WORKFLOW_PACKAGE_RUN = re.compile(r"python[^\n]*private_area")


def _file_list() -> list:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=REPO,
                             capture_output=True, check=True).stdout
        names = sorted({name for name in out.decode("utf-8", errors="surrogateescape").split("\0") if name})
    except (OSError, subprocess.CalledProcessError):
        # No git: walk everything except caches and the git-ignored raw blob / history stores (multi-GB, never committed).
        skip = {".git", "node_modules", "__pycache__", ".pytest_cache"}
        ignored = ("implementation/data/raw/blobs/", "implementation/data/raw/history/")
        names = sorted(name for name in (p.relative_to(REPO).as_posix() for p in REPO.rglob("*")
                                         if p.is_file() and not skip & set(p.relative_to(REPO).parts))
                       if not name.startswith(ignored))
    return [n for n in names if (REPO / n).is_file() and not (REPO / n).is_symlink()]


def _payload(name: str, data: bytes) -> bytes:
    if name.endswith(".gz"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as handle:
                inflated = handle.read(MAX_GZIP_BYTES + 1)
            if len(inflated) <= MAX_GZIP_BYTES:
                return inflated
        except (OSError, EOFError):
            pass
    return data


@pytest.fixture(scope="module")
def files():
    """(relative path, bytes, .gz inflated) of every file; read once for all tests here."""
    return [(name, _payload(name, (REPO / name).read_bytes())) for name in _file_list()]


def _data(content) -> bytes:
    return content.encode("utf-8") if isinstance(content, str) else content


def _text(content) -> str:
    return content if isinstance(content, str) else content.decode("utf-8", errors="replace")


# ASCII prefilter on lowered bytes (the KIS markers are ASCII); a file that passes it is judged by the guard's own function.
_KIS_HINTS_ASCII = tuple(hint.encode("ascii") for hint in GUARD._KIS_HINTS)
HOST_AND_TR = (GUARD.KIS_HOST, GUARD.KIS_TR_ID)   # the repository rule names hosts and TR ids (Secret names: workflows only)


# ---- the checks (plain functions so the self-tests below can feed synthetic files) ----------------------------------------
def _json_kis_schema(value, depth=0) -> bool:
    if depth > 200:
        return True    # fail closed on absurd nesting
    if isinstance(value, dict):
        for key, child in value.items():
            if re.sub(r"[^a-z0-9]", "", key.casefold()) in {"schema", "schemaversion"} and isinstance(child, str) \
                    and child.strip().casefold().startswith("kis-"):
                return True
            if _json_kis_schema(child, depth + 1):
                return True
    elif isinstance(value, list):
        return any(_json_kis_schema(child, depth + 1) for child in value)
    return False


def kis_schema_files(pairs) -> list:
    found = []
    for name, content in pairs:
        low = _data(content).lower()
        if b"kis-" in low and KIS_SCHEMA_TEXT.search(_text(content).casefold()):
            found.append(name)
            continue
        # A parsed JSON can only add a hit through an escape (e.g. \u006b) or the plain prefix.
        if (name.endswith(".json") or name.endswith(".json.gz")) and (b"kis-" in low or b"\\u" in low):
            try:
                value = json.loads(_text(content))
            except (ValueError, RecursionError):
                continue      # not JSON: the raw-text pattern above already ran
            if _json_kis_schema(value):
                found.append(name)
    return found


def _json_schema_values(value, depth=0):
    """Every string under a schema / schema_version key (any spelling) of a parsed JSON value."""
    if depth > 200:
        yield "private-nesting-limit"      # fail closed on absurd nesting
    elif isinstance(value, dict):
        for key, child in value.items():
            if re.sub(r"[^a-z0-9]", "", key.casefold()) in {"schema", "schemaversion"} and isinstance(child, str):
                yield child.strip()
            yield from _json_schema_values(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _json_schema_values(child, depth + 1)


def private_schema_names(name: str, content) -> set:
    """Private-area schema names of one non-Markdown file that are not legacy (exact spelling)."""
    if name.lower().endswith(".md"):
        return set()
    low = _data(content).lower()
    if b"private-" not in low and b"\\u" not in low:
        return set()
    text = _text(content)
    found = {m.group(0) for m in NEW_PRIVATE_SCHEMA_NAME.finditer(text)}
    found |= {m.group(1) for m in PRIVATE_SCHEMA_TEXT.finditer(text)}
    if name.endswith(".json") or name.endswith(".json.gz"):
        try:
            value = json.loads(text)
        except (ValueError, RecursionError):
            value = None
        found |= {v for v in _json_schema_values(value) if v.casefold().startswith("private-")}
    return found - set(LEGACY_PRIVATE_SCHEMAS)


def private_schema_files(pairs) -> list:
    return [name for name, content in pairs if private_schema_names(name, content)]


def legacy_private_schemas_in_use(pairs) -> set:
    """The legacy names that non-Markdown files still use as a schema value."""
    used = set()
    for name, content in pairs:
        if name.lower().endswith(".md") or b"private-history/" not in _data(content):
            continue
        used |= {m.group(1) for m in PRIVATE_SCHEMA_TEXT.finditer(_text(content))} & set(LEGACY_PRIVATE_SCHEMAS)
    return used


def kis_marker_files(pairs, markers=HOST_AND_TR) -> set:
    found = set()
    for name, content in pairs:
        low = _data(content).lower()
        if any(hint in low for hint in _KIS_HINTS_ASCII) and GUARD.kis_marker_count(_text(content), markers):
            found.add(name)
    return found


def workflow_findings(pairs) -> list:
    found = []
    for name, content in pairs:
        if not name.startswith(".github/workflows/"):
            continue
        text = _text(content)
        folded = text.casefold()
        for kind, hit in (("kis_secret", WORKFLOW_SECRET.search(folded)), ("kis_marker", GUARD.kis_marker_count(text)),
                          ("collector", COLLECTOR_MODULE in folded), ("private_area_run", WORKFLOW_PACKAGE_RUN.search(folded))):
            if hit:
                found.append((name, kind))
    return found


def web_private_path_files(pairs) -> list:
    return [name for name, content in pairs
            if (name.startswith(WEB_SOURCE_DIRS) and name.endswith(WEB_TEXT_SUFFIXES) or name in WEB_SOURCE_FILES)
            and GUARD.private_code_paths(_text(content))]


def kis_secret_name_files(pairs) -> list:
    """Non-Markdown files naming a KIS Secret (the guard's own pattern, any letter case)."""
    return [name for name, content in pairs
            if not name.lower().endswith(".md") and b"kis_app" in _data(content).lower()
            and GUARD.KIS_SECRET_NAME.search(_text(content).casefold())]


# ---- repository ----------------------------------------------------------------------------------------------------------
def test_file_list_covers_the_repository(files):
    names = {name for name, _ in files}
    assert len(names) > 1000
    assert {"implementation/tools/pages_artifact_guard.py", ".github/workflows/cockpit-pages.yml",
            "implementation/docs/private_area/PRIVATE_AREA_KIS_DESIGN_20261031.md"} <= names
    assert any(name.endswith(".gz") for name in names)


def test_no_file_carries_a_kis_schema(files):
    assert kis_schema_files(files) == []


def test_no_code_or_data_file_carries_a_private_area_schema(files):
    assert private_schema_files(files) == []
    # The legacy set is exactly the private-history names that code and fixtures still use (no stale entry).
    assert legacy_private_schemas_in_use(files) == set(LEGACY_PRIVATE_SCHEMAS)
    assert all(reason.strip() for reason in LEGACY_PRIVATE_SCHEMAS.values())


def test_kis_hosts_and_tr_ids_appear_only_in_the_allow_list(files):
    allowed = set(KIS_MARKER_FILES) | set(FUTURE_MARKER_FILES)
    assert kis_marker_files(files) - allowed == set()
    # Every listed file that exists still names a marker, so the list cannot keep stale entries.
    for name in KIS_MARKER_FILES:
        assert (REPO / name).is_file(), name
        assert GUARD.kis_marker_count((REPO / name).read_text(encoding="utf-8"), HOST_AND_TR), name
    assert all(reason.strip() for reason in {**KIS_MARKER_FILES, **FUTURE_MARKER_FILES}.values())


def test_kis_secret_names_only_in_markdown_docs(files):
    # Owner 2026-10-31: the KIS keys live only in investment-system1-kis-private; no public code may read or name them.
    assert kis_secret_name_files(files) == []


def test_kis_secret_name_check_catches_every_spelling():
    for name in ("KIS_APP" + "_KEY", "KIS_APP" + "_SECRET", "KIS_APP" + "KEY", "kis_app" + "secret"):
        for path in ("implementation/tools/x.py", ".github/workflows/x.yml", "implementation/x.json", "x.sh"):
            assert kis_secret_name_files([(path, "env = os.environ['" + name + "']")]) == [path], (path, name)
    assert kis_secret_name_files([("implementation/docs/x.md", "KIS_APP" + "_KEY")]) == []


def test_public_workflows_never_reach_kis(files):
    workflows = [(name, text) for name, text in files if name.startswith(".github/workflows/")]
    assert len(workflows) >= 5
    assert workflow_findings(workflows) == []


def test_push_workflow_runs_only_this_test_with_no_secret():
    # Security review B2 (10/31): every push to any branch runs this file; detection after exposure, not prevention.
    # The workflow itself waits for the owner's approval (workflow changes only after approval) and lands in its own PR;
    # until then this test has nothing to pin. Once the file exists, its shape is pinned here.
    path = REPO / ".github/workflows/private-boundary-push.yml"
    if not path.exists():
        pytest.skip("private-boundary-push.yml waits for owner approval (design §20.1)")
    text = path.read_text(encoding="utf-8")
    assert "\non:\n  push:\n    branches: ['**']\npermissions:\n  contents: read\njobs:\n" in text
    assert "secrets" not in text.casefold() and "pull_request_target" not in text and "write" not in text
    assert text.count("\n      - uses: ") == 2 and "persist-credentials: false" in text
    assert text.count("pip install") == 1 and "python -m pip install pytest==9.1.1\n" in text
    assert text.count("python -m pytest") == 1
    assert "python -m pytest -q --tb=short -p no:cacheprovider tests/test_private_boundary_static.py\n" in text
    for forbidden in ("actions/upload", "actions/cache", "GITHUB_STEP_SUMMARY", "concurrency:", "continue-on-error"):
        assert forbidden not in text, forbidden
    assert workflow_findings([(".github/workflows/private-boundary-push.yml", text)]) == []


def test_public_web_sources_request_no_private_worker_path(files):
    web = [(name, text) for name, text in files if name.startswith(WEB_SOURCE_DIRS) or name in WEB_SOURCE_FILES]
    assert len(web) > 100 and any(name.endswith("web_app/core.js") for name, _ in web)
    assert web_private_path_files(web) == []


# ---- the checks catch synthetic violations ----------------------------------------------------------------------------------
KIS = "k" + "is"


def test_kis_schema_check_catches_every_form():
    escaped = json.dumps({"a": [{"Schema_Version": "X"}]}).replace('"X"', '"\\u006b' + 'is-us-daily/1"')
    samples = {
        "a.json": json.dumps({"deep": [{"schema": KIS + "-us-daily/1"}]}),
        "b.json": escaped,
        "c.py": "row = {'schema_version': '" + KIS.upper() + "-x/2'}",
        "d.yml": "schema: " + KIS + "-bars/1\n",
        "e.json.gz": json.dumps({"schema": " " + KIS + "-x"}),
    }
    assert sorted(kis_schema_files(samples.items())) == sorted(samples)
    data = gzip.compress(samples["e.json.gz"].encode())
    assert _payload("e.json.gz", data).decode() == samples["e.json.gz"]
    clean = {"f.json": json.dumps({"schema": "research-request/1", "note": KIS + "-prefix in prose"}),
             "g.py": "SCHEMA = '" + KIS + "-us-daily/1'  # a constant, not a record"}
    assert kis_schema_files(clean.items()) == []


def test_kis_schema_check_catches_the_csv_ledger_comment():
    samples = {
        "ohlcv/A/AAPL/2026.csv": "# schema: " + KIS + "-ohlcv/1\ndate,open,high,low,close,volume\n2026-01-02,1,2,0.5,1.5,100\n",
        "b.csv": "\ufeff#schema=" + KIS.upper() + "-ohlcv/1\n",
        "c.csv.gz": "x,y\n# schema: '" + KIS + "-ohlcv/2'\n",
        "d.txt": "  #  schema_version : " + KIS + "-bars/1\n",
    }
    assert sorted(kis_schema_files(samples.items())) == sorted(samples)
    clean = {"e.csv": "# schema: ohlcv/1\n", "f.py": "HEADER = '# schema: " + KIS + "-ohlcv/1'  # written by the collector",
             "g.md": "Ledgers start with `# schema: " + KIS + "-ohlcv/1`."}
    assert kis_schema_files(clean.items()) == []


PRIV = "private"


def test_private_schema_check_catches_new_and_unknown_names():
    legacy, other = PRIV + "-history/1", PRIV + "-history/2"
    escaped = json.dumps({"a": [{"Schema": "X"}]}).replace('"X"', '"\\u0070rivate-bars/1"')
    samples = {
        "chart/A/AAPL.json": json.dumps({"schema": PRIV + "-bars/1", "provider": "KIS"}),
        "b.json": escaped,
        "c.js": "const S = '" + PRIV + "-quote/1';",
        "d.py": "row = {'schema_version': '" + PRIV.upper() + "-Liquidity/2'}",
        "e.yml": "schema: " + PRIV + "-subset-result/1\n",
        "f.json.gz": json.dumps({"deep": [{"schema_version": " " + PRIV + "-anything/3"}]}),
        "g.mjs": "if (h.schema === '" + PRIV + "-history/9') {}",
        "h.csv": "# schema: " + PRIV + "-ohlcv/1\n",
        "i.js": "x = {schema:'" + legacy.replace("p", "P", 1) + "'}",           # the legacy name only in its exact spelling
        "j.json": json.dumps({"schema": PRIV + "-bars/1"}).replace("schema", "Schema-Version"),
        "k.txt": "notes: " + PRIV + "-bars/1 rows",                                 # a new-family name anywhere
    }
    assert sorted(private_schema_files(samples.items())) == sorted(samples)
    clean = {"l.json": json.dumps({"schema": legacy, "bars": []}), "m.py": "h.update(schema='" + other + "')",
             "n.js": "if (v.schema !== '" + legacy + "') return null;", "o.md": "schema: " + PRIV + "-bars/1",
             "p.json": json.dumps({"note": PRIV + "-equity fund", "schema": "research-request/1"}),
             "q.py": "PATH = '/" + PRIV + "-subset-root'"}
    assert private_schema_files(clean.items()) == []
    assert legacy_private_schemas_in_use(clean.items()) == {legacy, other}


def test_marker_check_uses_the_guard_patterns():
    host, tr, order_tr, name = "openapivts.korea" + "investment.com", "FHKST" + "03010100", "TTTC" + "0802U", "KIS_APP" + "_SECRET"
    samples = {"a.md": "see " + host, "b.py": "TR = '" + tr + "'", "c.txt": order_tr.lower(), "d.json.gz": "OpenAPI.Korea" + "Investment.COM"}
    assert kis_marker_files(samples.items()) == set(samples)
    # Security review B4 (10/31): the families the guard missed, from the one list in kis_routes.
    for tr_id in ("TTTT" + "1002U", "TTTT" + "1006U", "TTTO" + "1101U", "CTSC" + "9115R", "CTOS" + "4001R"):
        assert kis_marker_files({"x.py": "TR = '" + tr_id + "'"}.items()) == {"x.py"}, tr_id
    assert kis_marker_files({"e.md": "KIS research notes, no host", "f.md": name}.items()) == set()   # names: workflow rule
    assert kis_marker_files({"f.md": name}.items(), GUARD.KIS_MARKERS) == {"f.md"}


@pytest.mark.parametrize("line,kind", [
    ("      KEY: ${{ secrets." + KIS.upper() + "_APP_KEY }}", "kis_secret"),
    ("      KEY: ${{ secrets['" + KIS + "_token'] }}", "kis_secret"),
    ("      KEY: ${{ secrets [ \"" + KIS.upper() + "_X\" ] }}", "kis_secret"),
    ("      run: echo $" + KIS.upper() + "_APP" + "_KEY", "kis_marker"),
    ("      run: curl https://openapi.korea" + "investment.com:9443", "kis_marker"),
    ("      run: python -m investment_system.private_area." + KIS + "_collector", "collector"),
    ("      run: python implementation/src/investment_system/private_area/" + KIS + "_collector.py", "collector"),
    ("      run: python -m investment_system.private_area.research_request", "private_area_run"),
])
def test_workflow_check_catches_each_reference(line, kind):
    text = "name: x\non: push\njobs:\n  a:\n    steps:\n" + line + "\n"
    assert (".github/workflows/x.yml", kind) in workflow_findings([(".github/workflows/x.yml", text)])
    assert workflow_findings([("docs/x.yml", text)]) == []


def test_workflow_check_allows_test_runs_and_path_filters():
    text = ("on:\n  pull_request:\n    paths:\n      - 'implementation/src/investment_system/private_area/**'\n"
            "jobs:\n  t:\n    steps:\n      - run: python -m pytest -q tests/test_research_request.py\n")
    assert workflow_findings([(".github/workflows/t.yml", text)]) == []


@pytest.mark.parametrize("source", ["fetch(W + '/" + KIS + "/us-daily')", "const P = '/lab/backtest';",
                                    "u + '/private'", "url('/" + KIS + "?x=1')"])
def test_web_check_catches_private_paths(source):
    for name in ("implementation/src/investment_system/product/web_app/private-x.js",
                 "implementation/src/investment_system/product/web_assets/app.js",
                 "implementation/src/investment_system/product/web_mvp.py"):
        assert web_private_path_files([(name, source)]) == [name]
    assert web_private_path_files([("implementation/worker/src/index.js", source)]) == []


def test_web_check_keeps_the_app_hash_route():
    route = "{id:'lab',no:'n+1',ko:'Lab',path:'/lab'}"
    assert web_private_path_files([("implementation/src/investment_system/product/web_app/core.js", route)]) == []


def test_file_list_falls_back_to_a_walk_without_git(monkeypatch):
    def no_git(*args, **kwargs):
        raise OSError("git unavailable")
    monkeypatch.setattr(subprocess, "run", no_git)
    names = _file_list()
    assert "implementation/tools/pages_artifact_guard.py" in names
    assert not any(n == ".git" or n.startswith(".git/") or "/__pycache__/" in n for n in names)
