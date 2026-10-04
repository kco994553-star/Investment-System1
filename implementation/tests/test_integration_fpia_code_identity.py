"""Code identity SAME/DIVERGED from the unmodified sites, never pinned; registration consequence and
the binding probe (CDR-014 §2, §10, §11; rv1 #1/#8/#9/rc1-rc3/rc8-1; review MEDIUM AC-09)."""
import hashlib
import json

from tests import integration_fpia_testkit as tk

SRC = "implementation/src/investment_system/"


def recompute(w, rev):
    files = sorted((p, sha) for p, (mode, sha) in w.git.files(rev).items() if p.startswith(SRC) and p.endswith(".py"))
    files.sort(key=lambda x: tuple(x[0][len(SRC):].split("/")))
    nul = hashlib.sha256(b"".join(p[len(SRC):].encode() + b"\0" + w.git.read(rev, p) for p, _ in files)).hexdigest()
    lit = hashlib.sha256(b"".join(p[len(SRC):].encode() + b"\\0" + w.git.read(rev, p) for p, _ in files)).hexdigest()
    return nul, lit


def test_empty_foreign_py_reports_diverged(tmp_path):
    """rv1 #1: an EMPTY foreign .py changes the whole-package identity -> DIVERGED (reported as fact);
    the FPIA verdict then depends on projection and interference, not on DIVERGED itself (CDR-014 §2)."""
    w = tk.variant(tmp_path)
    T2 = w.git.change(w.c["T0"], {SRC + "rig/foreign_capability_note.py": ""}, "empty foreign module")
    G = w.register(w.c["R0"], [w.c["V0"]], [T2])
    r = w.fpia(T2, G)
    ci = r["code_identity"]
    assert ci["status"] == "CODE_IDENTITY_DIVERGED"
    vals = {k.split(":")[1]: v for k, v in ci["site_values"].items()}
    nul_R, lit_R = recompute(w, w.c["R0"])
    nul_T, lit_T = recompute(w, T2)
    names = sorted(vals)
    fn = [n for n in names if vals[n]["R"] == nul_R]
    attr = [n for n in names if vals[n]["R"] == lit_R]
    assert fn and attr and vals[fn[0]]["T"] == nul_T and vals[attr[0]]["T"] == lit_T
    assert "CODE_IDENTITY_SAME" not in json.dumps(r)
    assert r["statuses"]["track_c_projection"] == "TRACK_C_PROJECTION_PRESERVED"
    assert r["statuses"]["integration_interference"] == "INTEGRATION_INTERFERENCE_NONE"
    assert r["fpia"]["status"] == "FPIA_PASS"          # DIVERGED is not by itself a Frozen violation
    assert "CODE_IDENTITY_DIVERGED" in r["summary"]


def test_registration_note_iff_diverged(tmp_path):
    w = tk.base_world()
    diverged = w.fpia(w.c["T0"], options={"lanes": ["R", "T"]})
    assert diverged["code_identity"]["status"] == "CODE_IDENTITY_DIVERGED"
    assert diverged["code_identity"]["registration_binding"].startswith("PRIOR_TRACK_C_REGISTRATIONS_FAIL_CLOSED_ON_T")
    assert diverged["integration_interference"]["registration_probe"]["status"] == "AGREES"
    assert diverged["integration_interference"]["registration_probe"]["expected_raise"] is True
    v = tk.variant(tmp_path)
    G = v.register(v.c["R0"], [], [v.c["R0"]])
    same = v.fpia(v.c["R0"], G, options={"lanes": ["R", "T"]})
    assert same["code_identity"]["status"] == "CODE_IDENTITY_SAME"
    assert "registration_binding" not in same["code_identity"]
    assert same["integration_interference"]["registration_probe"]["status"] == "AGREES"
    assert same["integration_interference"]["registration_probe"]["expected_raise"] is False


def test_registration_probe_inconsistent_found(tmp_path):
    """A registration path that ignores code identity breaks Track C's fail-closed binding on T."""
    w = tk.variant(tmp_path)
    g = w.git
    protocol = SRC + "evl/calibration_protocol.py"
    R2 = g.change(w.c["R0"], {protocol: tk.PROTOCOL_SKIPPING}, "registration skips validation")
    T2 = g.change(R2, {SRC + "rig/foreign_capability_note.py": ""}, "foreign module")
    G = w.register(R2, [], [T2])
    r = w.fpia(T2, G, options={"lanes": ["R", "T"]})
    assert r["code_identity"]["status"] == "CODE_IDENTITY_DIVERGED"
    assert r["integration_interference"]["registration_probe"]["status"] == "DISAGREES"
    assert any(f["id"] == "AC-09" for f in r["integration_interference"]["findings"])


def test_unsupported_site_kind_not_run(tmp_path):
    w = tk.variant(tmp_path)
    src = ("from pathlib import Path\n\n\nclass Identity:\n"
           "    VALUE = sorted(Path(__file__).resolve().parent.rglob('*.py'))\n")
    R2 = w.git.change(w.c["R0"], {SRC + "evl/identity_class.py": src}, "class-attribute site")
    G = w.register(R2, [], [R2])
    a = w.audit(R2, G)
    assert a.shape_error and "unsupported" in a.shape_error
    r = w.fpia(R2, G, options={"lanes": []})
    assert r["fpia"]["status"] == "FPIA_NOT_RUN"
