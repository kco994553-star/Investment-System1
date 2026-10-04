"""Pytest configuration manipulation, plugin injection, collection equality and cross-test
interference (CDR-014 §7; rv1 #2/rc4; rv2 #2/rc1; review MEDIUM on -c pinning; review HIGH on
full regression and deselection)."""
import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_checks as fchk

DESELECT = 'not holdout and not Holdout and not lookahead and not future'
NAMES = fchk.config_names_from_pytest()
DIRS = ["implementation/tests", "implementation", ""]


def config_body(name):
    if name.endswith(".toml") and name != "pyproject.toml":
        return '[pytest]\naddopts = ["-k", "%s"]\n' % DESELECT
    if name == "pyproject.toml":
        return '[tool.pytest.ini_options]\naddopts = "-k \'%s\'"\n' % DESELECT
    if name == "setup.cfg":
        return "[tool:pytest]\naddopts = -k '%s'\n" % DESELECT
    return "[pytest]\naddopts = -k '%s'\n" % DESELECT


def static_ids(w, T):
    a = w.audit(T, w.register(w.c["R0"], [w.c["V0"]], [T]))
    assert a.ref_status == "PASS"
    return a, {f["id"] for f in a.static_findings}


def test_config_names_are_derived_from_installed_pytest():
    assert {"pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini"} <= set(NAMES)


@pytest.mark.parametrize("name", NAMES + ["pyproject.toml#plain", "setup.py"])
@pytest.mark.parametrize("directory", DIRS)
def test_config_files_found(tmp_path, name, directory):
    w = tk.variant(tmp_path)
    if name == "pyproject.toml#plain":
        name, body = "pyproject.toml", "[project]\nname = 'x'\n"
    elif name == "setup.py":
        body = "from setuptools import setup\nsetup()\n"
    else:
        body = config_body(name)
    path = (directory + "/" + name) if directory else name
    T2 = w.git.change(w.c["T0"], {path: body}, "config " + path)
    a, ids = static_ids(w, T2)
    assert "AC-27" in ids, (path, a.static_findings)


def test_rv1_pytest_toml_deselection_on_world(tmp_path):
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {"implementation/tests/.pytest.toml": config_body(".pytest.toml")}, "rv1 config")
    a, ids = static_ids(w, T2)
    assert "AC-27" in ids
    G = w.register(w.c["R0"], [w.c["V0"]], [T2])
    # (b) static layer AND -c pinning disabled: collection equality FAILs naming exactly the deselected nodes
    r = w.fpia(T2, G, options={"lanes": ["T", "V"], "static_layer": False, "pytest_config_pinning": False})
    desel = sorted({n for f in r["integration_interference"]["findings"]
                    if f["finding"] == "tests deselected in a Track C session" for n in f["nodes"]})
    assert desel == ["implementation/tests/test_evl_c0_basic.py::test_no_lookahead_boundary_fails_closed",
                     "implementation/tests/test_evl_c6_basic.py::test_holdout_boundary_is_unconsumed",
                     "implementation/tests/test_evl_c7_selection.py::test_c7_future_feature_rejected",
                     "implementation/tests/test_evl_c8_contracts.py::test_calibration_boundary_and_identity_fail_closed_holdout_role",
                     "implementation/tests/test_evl_c8_contracts.py::test_no_lookahead_future_dataset"], desel
    # (c) pinning on: every node executes and passes
    r2 = w.fpia(T2, G, options={"lanes": ["T", "V"], "static_layer": False})
    assert not [f for f in r2["integration_interference"]["findings"] if f["id"] == "AC-30"]
    for rec in r2["integration_interference"]["targeted_tests"]:
        assert rec["counts"]["failures"] == 0 and rec["counts"]["errors"] == 0


def test_t2_distinfo_plugin(tmp_path):
    w = tk.variant(tmp_path)
    plugin = ("import pytest\n\n\n@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n"
              "    outcome = yield\n    report = outcome.get_result()\n    if report.failed:\n"
              "        report.outcome = 'passed'\n")
    changes = {"implementation/zz_ci_helper-0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: zz-ci-helper\nVersion: 0.0\n",
               "implementation/zz_ci_helper-0.0.dist-info/entry_points.txt": "[pytest11]\nzz = tests.zz_ci_helper\n",
               "implementation/tests/zz_ci_helper.py": plugin,
               "implementation/tests/test_zz_should_fail.py": "def test_should_fail():\n    assert False\n"}
    T2 = w.git.change(w.c["T0"], changes, "rv2 T2")
    a, ids = static_ids(w, T2)
    assert "AC-28" in ids
    G = w.register(w.c["R0"], [w.c["V0"]], [T2])
    r = w.fpia(T2, G, options={"lanes": ["T-full"], "static_layer": False})
    assert r["statuses"]["full_regression"] == "FAIL"            # autoload disabled: the failure stays a failure
    r2 = w.fpia(T2, G, options={"lanes": ["T-full"], "static_layer": False, "plugin_autoload_disabled": False})
    assert any(f["id"] == "AC-28" and f["finding"] == "unexpected pytest plugin"
               for f in r2["integration_interference"]["findings"])
    assert r2["statuses"]["runtime_provenance"] == "FAIL"


@pytest.mark.parametrize("path", ["implementation/conftest.py", "implementation/tests/sub/conftest.py",
                                  "implementation/src/sitecustomize.py", "implementation/usercustomize.py",
                                  "implementation/src/zz.pth"])
def test_conftest_sitecustomize_pth_found(tmp_path, path):
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {path: "import sys\n"}, "hook " + path)
    a, ids = static_ids(w, T2)
    assert "AC-28" in ids


def test_sitecustomize_not_imported_by_hardened_children(tmp_path):
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {"implementation/src/sitecustomize.py": "SITE_MARKER = 1\n"}, "sitecustomize")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["T", "V"], "static_layer": False})
    findings = r["integration_interference"]["findings"]
    assert not [f for f in findings if f.get("module") == "sitecustomize"], findings   # -I children never import it
    assert any(f["id"] == "AC-26.spawn" for f in findings)       # the v2 grandchild (no -I) is flagged


def test_collection_missing_nodes_fails(tmp_path):
    w = tk.variant(tmp_path)
    conftest = ("def pytest_collection_modifyitems(session, config, items):\n"
                "    items[:] = [i for i in items if 'holdout' not in i.nodeid]\n")
    T2 = w.git.change(w.c["T0"], {"implementation/conftest.py": conftest}, "item-removing conftest")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["T", "V"], "static_layer": False})
    findings = r["integration_interference"]["findings"]
    assert any(f["finding"] == "collected node set differs from the reference" for f in findings), findings
    assert any(f["id"] == "AC-28" for f in findings)


def _session(**kw):
    base = {"label": "s", "deselected": [], "collected": ["a::t"], "outcomes": {"a::t": "passed"},
            "junit": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0},
            "recorder_counts": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}, "collect_errors": [], "rc": 0}
    base.update(kw)
    return base


def test_junit_recorder_mismatch_fails():
    assert fpia.session_consistency(_session()) == []
    bad = fpia.session_consistency(_session(junit={"tests": 2, "failures": 0, "errors": 0, "skipped": 0}))
    assert [f["finding"] for f in bad] == ["junit counts differ from recorder counts"]
    bad = fpia.session_consistency(_session(deselected=["a::u"]))
    assert bad and bad[0]["finding"] == "tests deselected in a Track C session"
    bad = fpia.session_consistency(_session(collected=["a::t", "a::u"]))
    assert bad and bad[0]["finding"] == "executed node set differs from the collected set"


def test_reference_not_clean_not_run():
    assert fpia.reference_clean(_session())
    assert not fpia.reference_clean(_session(outcomes={"a::t": "failed"}))
    assert not fpia.reference_clean(_session(rc=1))


def test_cross_test_monkeypatch_found(tmp_path):
    w = tk.variant(tmp_path)
    interferer = ("import sys\n\n\ndef test_aaa_patch():\n    name = 'investment_system.evl.' + 'calibration' + '_contracts'\n"
                  "    __import__(name)\n    setattr(sys.modules[name], 'code' + '_hash', lambda: 'patched')\n")
    T2 = w.git.change(w.c["T0"], {"implementation/tests/test_aaa_interferer.py": interferer}, "cross-test interferer")
    a, ids = static_ids(w, T2)
    assert "implementation/tests/test_aaa_interferer.py" not in {f["path"] for f in a.static_findings}
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["T", "T-full"]})
    assert any(f["id"] == "AC-35" for f in r["integration_interference"]["findings"]), \
        r["integration_interference"]["findings"]


def test_deselecting_track_c_node_rejected(tmp_path):
    w = tk.base_world()
    r = w.fpia(w.c["T0"], options={"lanes": ["T-full", "T"]})
    assert r["full_regression"]["deselected"] == ["implementation/" + fpia.NETWORK_NODE]
    a = w.audit(w.c["T0"])
    assert not a.proj.ns(tk.NETWORK_FILE)        # the single deselected node is never a Track C node
