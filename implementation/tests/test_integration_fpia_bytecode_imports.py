"""Committed bytecode, extension modules, import shadowing, closure resolution and executed-vs-audited
source (CDR-014 §7; rv1 #3a/#3b/#3c/#7/rc5; rv2 #1/#7a/rc1/rc6; review MEDIUM file access and
grandchild provenance)."""
import importlib.machinery
import importlib.util
import os
import py_compile
import tempfile
from pathlib import Path

import pytest

from tests import integration_fpia_testkit as tk

SRC = "implementation/src/investment_system/"
EVL = SRC + "evl/"


def pyc_bytes(source, unchecked=True):
    d = Path(tempfile.mkdtemp())
    src = d / "m.py"
    src.write_text(source)
    out = d / "m.pyc"
    mode = py_compile.PycInvalidationMode.UNCHECKED_HASH if unchecked else py_compile.PycInvalidationMode.TIMESTAMP
    py_compile.compile(str(src), cfile=str(out), invalidation_mode=mode, doraise=True)
    return out.read_bytes()


def t1_changes(w):
    lineage = w.git.read(w.c["T0"], tk.LINEAGE).decode()
    tag = importlib.util.MAGIC_NUMBER and "cpython-%d%d" % __import__("sys").version_info[:2]
    path = tk.LINEAGE.rsplit("/", 1)[0] + "/__pycache__/lineage.%s.pyc" % tag
    return {path: pyc_bytes(lineage + "\n_SHADOW_MARKER = True\n")}


def static_ids(w, T):
    a = w.audit(T, w.register(w.c["R0"], [w.c["V0"]], [T]))
    assert a.ref_status == "PASS"
    return a, {f["id"] for f in a.static_findings}


@pytest.mark.parametrize("case", ["a_t1_unchecked_hash_pyc", "b_sourceless_json_pyc", "c_init_pyc_package",
                                  "d_tagged_extensions"])
def test_bytecode_and_extensions_found(tmp_path, case):
    w = tk.variant(tmp_path)
    if case == "a_t1_unchecked_hash_pyc":
        changes = t1_changes(w)
    elif case == "b_sourceless_json_pyc":
        changes = {"implementation/json.pyc": pyc_bytes("MARK = 1\n")}
    elif case == "c_init_pyc_package":
        changes = {SRC + "rig/pkg/__init__.pyc": pyc_bytes("MARK = 1\n"), SRC + "rig/pkg.py": "X = 1\n"}
    else:
        ext = importlib.machinery.EXTENSION_SUFFIXES[0]
        changes = {EVL + "walkforward" + ext: os.urandom(64), SRC + "rig/x.abi3.so": os.urandom(64)}
    T2 = w.git.change(w.c["T0"], changes, case)
    a, ids = static_ids(w, T2)
    assert "AC-23" in ids, a.static_findings
    if case == "d_tagged_extensions":
        assert any(f["id"] in ("AC-24", "AC-21") and "walkforward" in f["path"] for f in a.static_findings)


@pytest.mark.parametrize("case", ["a_tools_init", "b_tools_json", "c_src_tests_init", "d_package_over_module",
                                  "e_cross_root_tool"])
def test_shadowing_found(tmp_path, case):
    w = tk.variant(tmp_path)
    path = {"a_tools_init": "implementation/tools/__init__.py", "b_tools_json": "implementation/tools/json.py",
            "c_src_tests_init": "implementation/src/tests/__init__.py",
            "d_package_over_module": EVL + "walkforward/__init__.py",
            "e_cross_root_tool": "implementation/src/tools/" + tk.C6_PATH.rsplit("/", 1)[1]}[case]
    T2 = w.git.change(w.c["T0"], {path: "MARK = 1\n"}, case)
    a, ids = static_ids(w, T2)
    assert "AC-24" in ids, (case, a.static_findings)


def test_new_subpackage_not_shadow(tmp_path):
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {SRC + "newcap/__init__.py": "", SRC + "newcap/core.py": "X = 1\n"}, "new capability")
    a, ids = static_ids(w, T2)
    assert not a.static_findings, a.static_findings


def test_closure_resolution_changes(tmp_path):
    w = tk.variant(tmp_path)
    p = tk.LINEAGE[:-3] + "/__init__.py"            # contracts/lineage/__init__.py shadows contracts/lineage.py
    T2 = w.git.change(w.c["T0"], {p: "_SHADOW_MARKER = True\n"}, "package over the lineage module")
    a, ids = static_ids(w, T2)
    assert "AC-25" in ids and "AC-24" in ids, a.static_findings


@pytest.mark.parametrize("case", ["a_sourceless_json_loaded", "b_t1_pyc_neutralised", "c_complement_rewrites_src"])
def test_dynamic_trace_violations(tmp_path, case):
    w = tk.variant(tmp_path)
    g = w.git
    if case == "a_sourceless_json_loaded":
        changes, lanes = {"implementation/json.pyc": pyc_bytes("MARK = 1\n")}, ["T"]
    elif case == "b_t1_pyc_neutralised":
        changes, lanes = t1_changes(w), ["R", "T"]
    else:
        changes = {"implementation/tests/test_zz_rewrite.py":
                   "from pathlib import Path\n\n\ndef test_rewrite():\n"
                   "    p = Path(__file__).resolve().parents[1] / 'src' / 'investment_system' / 'evl' / 'walkforward.py'\n"
                   "    p.write_text(p.read_text() + '\\n# rewritten\\n')\n"}
        lanes = ["T-full"]
    T2 = g.change(w.c["T0"], changes, case)
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": lanes, "static_layer": False})
    inter = r["integration_interference"]
    assert r["static_layer"]["disabled_for_test"]
    if case != "c_complement_rewrites_src":            # a runtime rewrite is not statically visible
        assert r["static_layer"]["would_have_found"]
    if case == "a_sourceless_json_loaded":
        assert any(f["id"] == "AC-26" and f.get("path") == "implementation/json.pyc" for f in inter["findings"]), inter
    elif case == "b_t1_pyc_neutralised":
        lineage_findings = [f for f in inter["findings"] if "lineage" in str(f)]
        assert not lineage_findings, lineage_findings
        cf = [c for c in inter["counterfactual"] if c["reference"] == "R"]
        assert cf and all(c["reproduced"] for c in cf)          # marker absent: lineage ran from source
    else:
        assert any(f["id"] == "AC-31" for f in inter["findings"]), inter["findings"]


def test_dynamic_data_read_outside_projection_found(tmp_path):
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {"implementation/tests/zz_note.txt": "complement data\n"}, "complement data")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["T", "V"], "static_layer": False})
    found = [f for f in r["integration_interference"]["findings"] if f["id"] == "AC-26.file"]
    assert any(f.get("path") == "implementation/tests/zz_note.txt" for f in found), found


def test_grandchild_shadow_found(tmp_path):
    w = tk.variant(tmp_path)
    marker = tmp_path / "grandchild-marker"
    T2 = w.git.change(w.c["T0"], {SRC[:-len("investment_system/")] + "sitecustomize.py":
                                  "open(%r, 'w').write('ran')\n" % str(marker)}, "src sitecustomize")
    a, ids = static_ids(w, T2)
    assert "AC-28" in ids
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": ["T", "V"], "static_layer": False})
    spawn = [f for f in r["integration_interference"]["findings"] if f["id"] == "AC-26.spawn"]
    assert spawn, r["integration_interference"]["findings"]
