"""fix3 battery: the 156 round-2 variants (wf16 v2-adversarial variants.py, read-only) overlaid on a real T
(default acaf1b5), analysed by the NEW static phase (complement_static + workflow_spoof + closure) of the
fix3 sources, with the audit's own arguments (av_all, repo identity, verifier self)."""
import json, sys, tempfile, shutil, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) / "implementation" / "tools" / "integration"
sys.path.insert(0, str(SRC))
import track_c_fpia as F  # noqa
import track_c_fpia_checks as fchk  # noqa
import track_c_fpia_derive as fd  # noqa
import track_c_fpia_git as fgit  # noqa
import track_c_fpia_workflows as fw  # noqa
import track_c_fpia_auth as fauth  # noqa
import track_c_fpia_runner as frun  # noqa
spec = importlib.util.spec_from_file_location("variants", str(HERE.parents[2] / "wf16/v2-adversarial/variants.py"))
VV = importlib.util.module_from_spec(spec); spec.loader.exec_module(VV)
REGISTER = "f36292689eabf7ba3700d57a949fa0fb7343a2c6"
import os, time as _time
if os.environ.get("SCAN_TRACE"):
    _orig = fw.Scan.scan_file
    def _traced(self, p, data, *a, **k):
        t = _time.time()
        r = _orig(self, p, data, *a, **k)
        dt = _time.time() - t
        print("  scan %-70s %8d bytes %.2fs (wf %s)" % (p[:70], len(data), dt, self.path), file=sys.stderr, flush=True)
        return r
    fw.Scan.scan_file = _traced
VT = "VARIANT_T"


class ProbeAudit(F.Audit):
    def runtime_phase(self):
        self.st["runtime_provenance"] = "PROBE_STOPPED"
    def dynamic_phase(self):
        raise AssertionError("not reached")
    def compose_components(self):
        self.reached_static = True


class OverlaySB:
    def __init__(self, sb, base_T):
        self.sb, self.base_T = sb, base_T
    def set_variant(self, files):
        self.files, self.extra = {}, {}
        for p, v in files.items():
            mode, data = ("100644", v) if isinstance(v, (bytes, str)) else v
            data = data.encode() if isinstance(data, str) else data
            sha = fgit.blob_id(data)
            self.extra[sha] = data
            self.files[p] = fgit.Entry(mode, "blob", sha)
    def tree(self, rev):
        if rev == VT:
            t = dict(self.sb.tree(self.base_T)); t.update(self.files); return t
        return self.sb.tree(rev)
    def blob(self, sha):
        return self.extra[sha] if sha in self.extra else self.sb.blob(sha)
    def __getattr__(self, n):
        return getattr(self.sb, n)


def main():
    repo, base, out = sys.argv[2], sys.argv[3], sys.argv[4]
    ids = set(sys.argv[5:])
    work = Path(tempfile.mkdtemp(prefix="bat-", dir=str(HERE)))
    au = ProbeAudit(repo, base, REGISTER, "CDR-014", work, None)
    r = au.run()
    assert getattr(au, "reached_static", False), r.get("fpia")
    osb = OverlaySB(au.sb, au.T)
    av_applied = {p for p in au.av if any(au.v_applies.get(V) for V in au.Vs)}
    config_dirs = set(r["integration_interference"]["config_dirs"])
    repo_ids = sorted({x for x in (fw.repo_identity(fauth.AUTHORITY_REMOTE), fw.repo_identity(au.opts["authority_remote"])) if x})
    vself = fw.VerifierSelf(frun.HERE, fgit.base_env(work))
    base_static = au.static_findings
    _orig_wf = fw.is_workflow_path
    current = {"files": set()}
    fw.is_workflow_path = lambda q: _orig_wf(q) and q in current["files"]   # only the variant's workflows
    rows = []
    cls = {c["id"]: c for c in json.load(open(HERE.parents[2] / "wf16/v2-adversarial/out/v3/classification.json"))}
    for v in VV.V:
        if ids and v["id"] not in ids:
            continue
        osb.set_variant(v["files"])
        current["files"] = set(v["files"])
        info = {}
        comp, findings = fchk.complement_static(osb, VT, au.R, au.Vs, au.v_applies, au.proj, av_applied, au.tcm_all,
                                                au.config_names or [], config_dirs, fd.TRACK_C_WORKFLOW, None, info=info,
                                                av_all=set(au.av), repo_ids=repo_ids, verifier_self=vself)
        orders = [("tools", list(fd.STATIC_ROOTS)), ("pytest", ["implementation", "implementation/src"])]
        closure, _ = fchk.closure_identity(osb, VT, au.R, au.Vs, au.v_applies, au.proj, au.av, orders)
        allf = findings + closure
        new = [f for f in allf if f not in base_static]
        wa = info.get("workflow_analysis") or {}
        c = cls.get(v["id"], {})
        rows.append({"id": v["id"], "group": v["group"], "desc": v["desc"], "class_round2": c.get("class"),
                     "observed_round2": c.get("observed_fpia"), "fpia": "FOUND" if new else "NOT_FOUND",
                     "findings": [{k: f.get(k) for k in ("id", "finding", "path", "reasons") if f.get(k)} for f in new],
                     "out_of_tree": [x for x in wa.get("out_of_tree_references", []) if x["workflow"] in v["files"]],
                     "not_run": info.get("not_run", [])})
        print("%-4s %-18s %-28s r2=%-9s fix3=%-9s %s" % (v["id"], v["group"], (c.get("class") or "")[:28],
              c.get("observed_fpia"), rows[-1]["fpia"],
              "; ".join(x for f in new for x in (f.get("reasons") or [f.get("finding")]))[:150]), flush=True)
    Path(out).write_text(json.dumps({"base": au.T, "base_static_findings": base_static, "rows": rows}, indent=1,
                                    ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)


main()
