"""FPIA hardened child launcher (copied into the FPIA work directory before every use).

Run as ``python -I -B -X pycache_prefix=<fresh> <copy of this file> <spec.json>``. ``-I`` implies
``-E -P -s``: no PYTHON* environment, no script directory or cwd on sys.path, no user site. The
launcher reproduces the workflow step's sys.path order explicitly, optionally installs an audit
hook (file reads, directory enumeration, process spawns), runs one profile and always writes a
trace (module origins, loaders, sys.path, meta_path, flags, events, pytest plugins) to the spec's
``trace`` path.

Profiles: ``tool`` and ``script`` (run a file as __main__), ``pytest`` (pytest.main with the FPIA
recorder plugin), ``site_eval`` (unmodified code-identity sites), ``main_block`` (a tool's main
block with only its audit-call assignment rebound; optional counterfactual pins applied by the
separate counterfactual module), ``registration_probe`` and ``baseline`` (interpreter defaults).
"""
import sys
_STARTUP = sorted(sys.modules)
import ast  # noqa: E402  (launcher-only imports are evicted from sys.modules before the payload)
import importlib  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import runpy  # noqa: E402
import traceback  # noqa: E402

with open(sys.argv[1], encoding="utf-8") as _spec:
    SPEC = json.load(_spec)
TRACE = {"profile": SPEC["profile"], "startup_modules": _STARTUP, "events": [],
         "flags": {k: getattr(sys.flags, k) for k in ("isolated", "ignore_environment", "no_user_site",
                                                         "dont_write_bytecode", "safe_path", "no_site")},
         "pycache_prefix": sys.pycache_prefix, "executable": sys.executable}
TREE = SPEC.get("tree_root")
TREE_PREFIX = (TREE.rstrip("/") + "/") if TREE else None
SITES = [(os.path.join(TREE, p), kind, name) for p, kind, name in SPEC.get("sites", [])] if TREE else []
_IN_HOOK = [False]


def _attribute(frame):
    """(innermost in-tree frame file relative to the tree, via_import_machinery, site_exempt).

    ``via_import`` is true when import machinery sits between the event and the innermost in-tree
    frame; ``site`` is true when a code-identity site (function or module body) is on the stack."""
    via_import = False
    site = False
    origin = None
    f = frame
    while f is not None:
        fn = f.f_code.co_filename
        if origin is None and fn.startswith("<frozen importlib"):
            via_import = True
        for path, kind, name in SITES:
            if fn == path and ((kind == "call" and f.f_code.co_name == name)
                               or (kind == "attribute" and f.f_code.co_name == "<module>")):
                site = True
        if origin is None and TREE_PREFIX and fn.startswith(TREE_PREFIX):
            origin = fn[len(TREE_PREFIX):]
        f = f.f_back
    return origin, via_import, site


def _rel(path):
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    if hasattr(path, "__fspath__"):
        path = os.fspath(path)
    if not isinstance(path, str):
        return None
    full = os.path.abspath(path)
    if full == TREE:
        return ""
    if TREE_PREFIX and full.startswith(TREE_PREFIX):
        return full[len(TREE_PREFIX):]
    return None


def _hook(event, args):
    if _IN_HOOK[0]:
        return
    _IN_HOOK[0] = True
    try:
        if event == "open":
            path, mode = args[0], args[1]
            rel = _rel(path)
            if rel is not None:
                writing = isinstance(mode, str) and any(c in mode for c in "wax+")
                flags = args[2] if len(args) > 2 else 0
                if mode is None and isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
                    writing = True
                origin, via_import, site = _attribute(sys._getframe(1))
                if origin is not None and not via_import:
                    TRACE["events"].append({"event": "write" if writing else "read", "path": rel,
                                            "by": origin, "site": site})
        elif event in ("os.listdir", "os.scandir"):
            rel = _rel(args[0] if args and args[0] is not None else ".")
            if rel is not None:
                origin, via_import, site = _attribute(sys._getframe(1))
                if origin is not None and not via_import:
                    TRACE["events"].append({"event": "enumerate", "path": rel, "by": origin, "site": site})
        elif event == "glob.glob":
            rel = _rel(args[0])
            if rel is not None:
                origin, via_import, site = _attribute(sys._getframe(1))
                if origin is not None and not via_import:
                    TRACE["events"].append({"event": "glob", "path": rel, "by": origin, "site": site})
        elif event in ("subprocess.Popen", "os.posix_spawn", "os.exec", "os.system", "os.spawn"):
            origin, _, _ = _attribute(sys._getframe(1))
            if event == "subprocess.Popen":
                executable, argv, cwd, env = args[0], args[1], args[2], args[3]
            elif event == "os.system":
                executable, argv, cwd, env = None, [args[0]], None, None
            else:
                executable, argv, cwd, env = args[0], args[1], None, args[2] if len(args) > 2 else None
            if isinstance(argv, (str, bytes)):
                argv = [argv]
            env_view = None
            if env is not None:
                try:
                    env_view = {os.fsdecode(k): os.fsdecode(v) for k, v in dict(env).items()
                                if os.fsdecode(k) in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONSAFEPATH")}
                    env_view["__names__"] = sorted(os.fsdecode(k) for k in dict(env))
                except Exception:
                    env_view = {"__unreadable__": True}
            TRACE["events"].append({"event": "spawn", "kind": event,
                                    "argv": [os.fsdecode(a) if isinstance(a, (bytes, str)) else str(a) for a in (argv or [])],
                                    "executable": os.fsdecode(executable) if isinstance(executable, (str, bytes)) else None,
                                    "cwd": os.fsdecode(cwd) if isinstance(cwd, (str, bytes)) else (str(cwd) if cwd else os.getcwd()),
                                    "env": env_view, "inherits_env": env is None, "by": origin,
                                    "parent_pythonpath": os.environ.get("PYTHONPATH")})
    finally:
        _IN_HOOK[0] = False


class Recorder:
    """pytest plugin registered via pytest.main(plugins=[...]); records collection and outcomes."""

    def __init__(self):
        self.collected, self.deselected, self.collect_errors = [], [], []
        self.reports = {}
        self.plugins = []

    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]

    def pytest_deselected(self, items):
        self.deselected.extend(item.nodeid for item in items)

    def pytest_collectreport(self, report):
        if report.failed:
            self.collect_errors.append(report.nodeid)

    def pytest_runtest_logreport(self, report):
        entry = self.reports.setdefault(report.nodeid, {})
        outcome = report.outcome
        if hasattr(report, "wasxfail"):
            outcome = "xfailed" if report.skipped else "xpassed"
        entry[report.when] = outcome

    def pytest_sessionfinish(self, session, exitstatus):
        for name, plugin in session.config.pluginmanager.list_name_plugin():
            if plugin is None:
                continue
            if plugin is self:
                self.plugins.append({"name": "fpia-recorder", "file": None, "fpia": True})
                continue
            mod = plugin if type(plugin).__name__ == "module" else sys.modules.get(type(plugin).__module__)
            self.plugins.append({"name": str(name), "module": getattr(mod, "__name__", None),
                                 "file": getattr(mod, "__file__", None), "fpia": False})


def _module_table():
    out = {}
    for name, mod in list(sys.modules.items()):
        spec = getattr(mod, "__spec__", None)
        origin = getattr(spec, "origin", None) if spec else getattr(mod, "__file__", None)
        cached = getattr(spec, "cached", None) if spec else None
        loader = type(spec.loader).__name__ if spec is not None and spec.loader is not None else None
        locations = list(spec.submodule_search_locations) if spec is not None and spec.submodule_search_locations else None
        out[name] = {"origin": origin, "cached": cached, "loader": loader, "locations": locations,
                     "file": getattr(mod, "__file__", None)}
    return out


def _instrumented_main(tool_path, audit_line, recorder_name="__fpia_audit_recorder__"):
    """The tool module with ONLY the main block's audit-call assignment rebound."""
    source = open(tool_path, "rb").read()
    tree = ast.parse(source, filename=tool_path)
    hits = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and node.lineno == audit_line and isinstance(node.value, ast.Call) \
                and isinstance(node.value.func, ast.Name) and not node.value.args:
            node.value = ast.Call(func=ast.Name(id=recorder_name, ctx=ast.Load()), args=[], keywords=[])
            hits += 1
    if hits != 1:
        raise RuntimeError("audit-call assignment not found exactly once")
    ast.fix_missing_locations(tree)
    return compile(tree, tool_path, "exec")


def run_profile():
    profile = SPEC["profile"]
    if profile == "baseline":
        return 0
    if profile in ("tool", "script", "main_block"):
        script = SPEC["script"]
        sys.argv = [script] + list(SPEC.get("args", []))
        if profile in ("tool", "script"):
            runpy.run_path(script, run_name="__main__")
            return 0
        if SPEC.get("pins"):
            cf = importlib.util.spec_from_file_location("track_c_fpia_counterfactual", SPEC["counterfactual_module"])
            module = importlib.util.module_from_spec(cf)
            cf.loader.exec_module(module)
            TRACE["pins_applied"] = module.apply_pins(SPEC["pins"])
        code = _instrumented_main(script, SPEC["audit_line"])
        namespace = {"__name__": "__main__", "__file__": script, "__builtins__": __builtins__,
                     "__fpia_audit_recorder__": lambda: {"status": "PASS", "fpia_instrumented": True}}
        exec(code, namespace)
        return 0
    if profile == "pytest":
        import pytest
        recorder = Recorder()
        try:
            rc = pytest.main(list(SPEC["args"]), plugins=[recorder])
        finally:
            TRACE["pytest"] = {"collected": recorder.collected, "deselected": recorder.deselected,
                               "collect_errors": recorder.collect_errors, "reports": recorder.reports,
                               "plugins": recorder.plugins, "pytest_file": pytest.__file__}
        return int(rc)
    if profile == "site_eval":
        values = {}
        for module_name, kind, name in SPEC["site_specs"]:
            mod = importlib.import_module(module_name)
            value = getattr(mod, name)
            values[module_name + ":" + name] = value() if kind == "call" else value
        TRACE["site_values"] = values
        print(json.dumps(values, sort_keys=True))
        return 0
    if profile == "registration_probe":
        probe = SPEC["probe"]
        fixture = importlib.import_module(probe["fixture_module"])
        missing = [n for n in ("prepare_source", "setup", "register") if not callable(getattr(fixture, n, None))]
        if missing:
            TRACE["probe"] = {"status": "API_ABSENT", "missing": missing}
            return 0
        work = SPEC["probe_dir"]
        source = fixture.prepare_source(pathlib.Path(work) / "source")
        rig = fixture.setup(pathlib.Path(work) / "rig", source)
        if not isinstance(rig, dict) or not isinstance(rig.get("plan"), dict) or probe["key"] not in rig["plan"]:
            TRACE["probe"] = {"status": "API_ABSENT", "missing": ["plan." + probe["key"]]}
            return 0
        rig["plan"][probe["key"]] = probe["bound_value"]
        try:
            fixture.register(rig)
            TRACE["probe"] = {"status": "REGISTERED"}
        except Exception as exc:
            TRACE["probe"] = {"status": "RAISED", "exception": type(exc).__name__, "message": str(exc)}
        return 0
    raise SystemExit("unknown profile " + profile)


def main():
    if SPEC.get("audit"):
        sys.addaudithook(_hook)
    for entry in reversed(SPEC.get("sys_path", [])):
        sys.path.insert(0, entry)
    os.chdir(SPEC["cwd"])
    # Evict launcher-only modules so the payload resolves every import itself (fidelity: a tree
    # file shadowing e.g. json must be seen by the dynamic trace, not masked by the launcher).
    keep = set(_STARTUP)
    for name in list(sys.modules):
        if name not in keep:
            del sys.modules[name]
    TRACE["sys_path_initial"] = list(sys.path)
    rc = 1
    try:
        rc = run_profile()
    except SystemExit as exc:
        code = exc.code
        TRACE["system_exit"] = code if isinstance(code, (int, type(None))) else str(code)
        rc = code if isinstance(code, int) else (0 if code is None else 1)
        if not isinstance(code, (int, type(None))):
            sys.stderr.write(str(code) + "\n")
    except BaseException as exc:
        TRACE["exception"] = {"type": type(exc).__name__, "message": str(exc)[:4000]}
        traceback.print_exc()
        rc = 1
    finally:
        TRACE["modules"] = _module_table()
        TRACE["sys_path"] = list(sys.path)
        TRACE["meta_path"] = [type(f).__module__ + "." + type(f).__qualname__ if not isinstance(f, type)
                              else f.__module__ + "." + f.__qualname__ for f in sys.meta_path]
        TRACE["path_hooks"] = [getattr(h, "__qualname__", type(h).__qualname__) for h in sys.path_hooks]
        TRACE["rc"] = rc
        sys.stdout.flush()
        with open(SPEC["trace"], "w", encoding="utf-8") as handle:
            json.dump(TRACE, handle, sort_keys=True, default=str)
    return rc


if __name__ == "__main__":
    sys.exit(main())
