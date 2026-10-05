"""Run the variant battery: FPIA (unmodified 523e702 sources, real static-phase audit of acaf1b5 + overlay),
the GitHub TS parser oracle, and (for G2 variants) a local bash emulation as ground truth."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import variants as VV  # noqa
from harness import Harness  # noqa

REPO = str(HERE / "repo")
T = subprocess.check_output(["git", "-C", REPO, "rev-parse", "acaf1b5"]).decode().strip()
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
VENV_BIN = HERE / "venv" / "bin"
sys.path.insert(0, str(HERE / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia_workflows as fw  # noqa


def as_bytes(v):
    data = v[1] if isinstance(v, tuple) else v
    return data.encode() if isinstance(data, str) else data


def gh_oracle(vid, files):
    paths = [p for p in files if p.endswith((".yml", ".yaml", ".YML")) and (p.startswith(".github/workflows/"))]
    if not paths:
        return {}
    d = Path(tempfile.mkdtemp(prefix="gh-", dir=str(HERE / "work")))
    m = {}
    for i, p in enumerate(paths):
        f = d / ("f%d.yml" % i)
        f.write_bytes(as_bytes(files[p]))
        m[str(f)] = p
    try:
        proc = subprocess.run(["node", str(HERE / "ghparser" / "gh_parse.mjs")] + list(m), capture_output=True,
                              cwd=str(HERE / "ghparser"), timeout=120)
        res = json.loads(proc.stdout.decode() or "{}")
    except Exception as exc:  # noqa
        res = {"_error": str(exc)}
    shutil.rmtree(d, ignore_errors=True)
    return {m.get(k, k): v for k, v in res.items()}


STUBS = {
    "implementation/tools/track_c_c6_acceptance.py":
        "import os, sys\nopen(os.environ['MARK'], 'a').write('TRACK_C_TOOL track_c_c6_acceptance argv=%r cwd=%s\\n' % (sys.argv, os.getcwd()))\n",
    "implementation/tests/test_evl_c6_stub.py":
        "import os\n\ndef test_evl_c6_stub():\n    open(os.environ['MARK'], 'a').write('TRACK_C_TEST test_evl_c6_stub\\n')\n",
    "implementation/tests/test_other_stub.py":
        "import os\n\ndef test_other_stub():\n    open(os.environ['MARK'], 'a').write('OTHER_TEST test_other_stub\\n')\n",
    "implementation/tests/conftest.py": "",
    "implementation/src/.keep": "",
}


def subst(text, ws, action_path=None, matrix=None):
    text = re.sub(r"\$\{\{\s*'([^']*)'\s*\}\}", lambda m: m.group(1), text)
    text = re.sub(r"\$\{\{\s*github\.workspace\s*\}\}", str(ws), text)
    if action_path:
        text = re.sub(r"\$\{\{\s*github\.action_path\s*\}\}", str(action_path), text)
    for k, v in (matrix or {}).items():
        text = re.sub(r"\$\{\{\s*matrix\.%s\s*\}\}" % re.escape(k), v, text)
    return text


def run_steps(steps, ws, mark, log, wd_default="", action_path=None, matrix=None, env_extra=None, depth=0):
    import yaml as _y  # vendored loader not needed: plain PyYAML from the vendored module
    for st in steps or []:
        if not isinstance(st, dict):
            continue
        env = dict(os.environ)
        env.update({"PATH": "%s:%s" % (VENV_BIN, os.environ["PATH"]), "GITHUB_WORKSPACE": str(ws), "MARK": str(mark),
                    "HOME": str(ws.parent / "home"), "PYTHONDONTWRITEBYTECODE": "1"})
        if action_path:
            env["GITHUB_ACTION_PATH"] = str(action_path)
        for k, v in (env_extra or {}).items():
            env[k] = str(v)
        for k, v in (st.get("env") or {}).items():
            env[k] = str(v)
        wd = subst(st.get("working-directory") or wd_default or "", ws, action_path, matrix)
        cwd = Path(wd) if wd.startswith("/") else ws / wd
        if "run" in st:
            script = subst(st["run"], ws, action_path, matrix)
            f = ws.parent / ("step%d.sh" % len(log))
            f.write_text(script)
            shell = st.get("shell") or "bash"
            if shell not in ("bash", "sh"):
                log.append({"skipped": "shell %s not emulated" % shell})
                continue
            cmd = ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(f)] if shell == "bash" else ["sh", "-e", str(f)]
            try:
                p = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, timeout=300)
                log.append({"run": script[:200], "cwd": str(cwd.relative_to(ws)) if str(cwd).startswith(str(ws)) else str(cwd),
                            "rc": p.returncode, "stderr_tail": p.stderr.decode("utf-8", "replace")[-300:]})
            except Exception as exc:  # noqa
                log.append({"run": script[:200], "error": str(exc)})
        elif "uses" in st and str(st["uses"]).startswith("./") and depth < 4:
            target = ws / st["uses"][2:]
            meta = target / "action.yml"
            if not meta.exists():
                log.append({"uses": st["uses"], "skipped": "no action.yml"})
                continue
            a = _y.safe_load(meta.read_text())
            runs = a.get("runs") or {}
            if runs.get("using") == "composite":
                run_steps(runs.get("steps"), ws, mark, log, wd_default=wd_default, action_path=target, depth=depth + 1)
            elif str(runs.get("using", "")).startswith("node"):
                p = subprocess.run(["node", str(target / runs["main"])], cwd=str(ws), env=env, capture_output=True, timeout=300)
                log.append({"node": runs["main"], "rc": p.returncode, "stderr_tail": p.stderr.decode("utf-8", "replace")[-300:]})
            else:
                log.append({"uses": st["uses"], "skipped": "using %s not emulated" % runs.get("using")})


def emulate(v):
    import importlib
    sys.path.insert(0, str(HERE / "repo" / "implementation" / "tools" / "integration"))
    from _vendor import yaml as Y  # vendored PyYAML (same as FPIA's loader)
    sys.modules.setdefault("yaml", Y)
    base = Path(tempfile.mkdtemp(prefix="emu-%s-" % v["id"], dir=str(HERE / "work")))
    ws = base / "ws"
    (base / "home").mkdir(parents=True)
    for p, data in list(STUBS.items()) + list(v["files"].items()):
        f = ws / p
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, tuple) and data[0] == "120000":
            if f.exists() or f.is_symlink():
                f.unlink()
            f.symlink_to(as_bytes(data).decode())
            continue
        f.write_bytes(as_bytes(data))
        if isinstance(data, tuple) and data[0] == "100755":
            f.chmod(0o755)
    mark = base / "mark.txt"
    mark.write_text("")
    log = []
    try:
        doc = Y.safe_load(as_bytes(v["files"][VV.WF]).decode())
        for jid, job in (doc.get("jobs") or {}).items():
            matrix = {}
            mx = ((job.get("strategy") or {}).get("matrix") or {})
            for k, vals in mx.items():
                if isinstance(vals, list) and vals:
                    matrix[k] = str(vals[0])
            if "uses" in job and str(job["uses"]).startswith("./"):
                called = Y.safe_load((ws / job["uses"][2:]).read_text())
                for j2 in (called.get("jobs") or {}).values():
                    run_steps(j2.get("steps"), ws, mark, log, (((j2.get("defaults") or {}).get("run") or {}).get("working-directory") or ""))
                continue
            if "uses" in job:
                log.append({"skipped": "remote reusable workflow %s not emulated" % job["uses"]})
                continue
            wd = (((job.get("defaults") or {}).get("run") or {}).get("working-directory")
                  or ((doc.get("defaults") or {}).get("run") or {}).get("working-directory") or "")
            if "windows" in str(job.get("runs-on")):
                log.append({"skipped": "windows runner not emulated"})
                continue
            run_steps(job.get("steps"), ws, mark, log, wd, matrix=matrix)
    except Exception as exc:  # noqa
        log.append({"error": "%s: %s" % (type(exc).__name__, exc)})
    marks = [x for x in mark.read_text().splitlines() if x]
    shutil.rmtree(base, ignore_errors=True)
    tc = [m for m in marks if m.startswith(("TRACK_C_TOOL", "TRACK_C_TEST"))]
    return {"track_c_executed": bool(tc), "marks": marks, "log": log}


def main(ids=None):
    h = Harness(REPO, T)
    rows = []
    for v in VV.V:
        if ids and v["id"] not in ids:
            continue
        files = v["files"]
        res = h.run(files)
        paths = set(files)
        fnd = [f for f in res["findings"]]
        row = {"id": v["id"], "group": v["group"], "desc": v["desc"], "expect": v["expect"], "note": v.get("note"),
               "fpia": "FOUND" if fnd else "NOT_FOUND",
               "findings": [{k: f.get(k) for k in ("id", "finding", "path", "reasons", "identity_claims") if f.get(k)} for f in fnd],
               "wa_status": res["wa_status"], "not_run": res["not_run"],
               "notes": [n for n in res["wa_notes"] if n.get("path") in paths]}
        # decoded name per FPIA's own loader (for comparison with the GitHub oracle)
        try:
            ident = fw.identity(fw.load(as_bytes(files[VV.WF]))) if VV.WF in files else None
            row["fpia_decoded_names"] = ident["names"] if ident else None
        except Exception as exc:  # noqa
            row["fpia_decoded_names"] = "Unparseable: %s" % str(exc)[:200]
        row["gh_oracle"] = gh_oracle(v["id"], files)
        if v.get("run"):
            row["emulation"] = emulate(v)
        rows.append(row)
        gh = row["gh_oracle"].get(VV.WF) or next(iter(row["gh_oracle"].values()), {}) if row["gh_oracle"] else {}
        print("%-4s %-14s fpia=%-9s expect=%-18s gh_err=%s gh_name=%r gh_run=%r emu=%s | %s" % (
            v["id"], v["group"], row["fpia"], v["expect"], bool(gh.get("errors")) if gh else None,
            gh.get("name") if gh else None, gh.get("runName") if gh else None,
            row.get("emulation", {}).get("track_c_executed"), v["desc"][:70]), flush=True)
    return rows


if __name__ == "__main__":
    ids = set(sys.argv[2:]) or None
    rows = main(ids)
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
