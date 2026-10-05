"""v2-adversarial fast harness (READ-ONLY w.r.t. FPIA sources).

1. Runs the unmodified Audit.run() of the 523e702 FPIA sources on a base T (acaf1b5) up to and including
   static_phase (runtime/dynamic/compose replaced by no-ops), exactly like the earlier probe harnesses.
2. For each variant (a dict of path -> bytes, optional mode), overlays the files on T's tree through a
   wrapper sandbox (real git blob ids) and re-runs the unmodified fchk.complement_static and
   fchk.closure_identity with the audit's own arguments. Prints/collects findings.
"""
import json, os, sys, tempfile, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "repo" / "implementation" / "tools" / "integration"
sys.path.insert(0, str(SRC))
import track_c_fpia as F  # noqa
import track_c_fpia_checks as fchk  # noqa
import track_c_fpia_derive as fd  # noqa
import track_c_fpia_git as fgit  # noqa

REGISTER = "f36292689eabf7ba3700d57a949fa0fb7343a2c6"
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
        self.files = {}
        self.blobs_extra = {}

    def set_variant(self, files, remove=()):
        self.files = {}
        self.blobs_extra = {}
        self.remove = set(remove)
        for p, v in files.items():
            mode, data = ("100644", v) if isinstance(v, (bytes, str)) else v
            if isinstance(data, str):
                data = data.encode()
            sha = fgit.blob_id(data)
            self.blobs_extra[sha] = data
            self.files[p] = fgit.Entry(mode, "blob", sha)

    def tree(self, rev):
        if rev == VT:
            t = dict(self.sb.tree(self.base_T))
            for p in self.remove:
                t.pop(p, None)
            t.update(self.files)
            return t
        return self.sb.tree(rev)

    def blob(self, sha):
        if sha in self.blobs_extra:
            return self.blobs_extra[sha]
        return self.sb.blob(sha)

    def blobs(self, shas):
        return {s: self.blob(s) for s in shas}

    def __getattr__(self, name):
        return getattr(self.sb, name)


class Harness:
    def __init__(self, repo, tree):
        self.work = Path(tempfile.mkdtemp(prefix="v2adv-", dir=str(HERE / "work")))
        self.au = ProbeAudit(repo, tree, REGISTER, "CDR-014", self.work, None)
        self.r = self.au.run()
        assert getattr(self.au, "reached_static", False), self.r.get("fpia")
        au = self.au
        self.base_static = au.static_findings
        self.osb = OverlaySB(au.sb, au.T)
        self.av_applied = {p for p in au.av if any(au.v_applies.get(V) for V in au.Vs)}
        self.config_dirs = set(self.r["integration_interference"]["config_dirs"])

    def run(self, files, remove=()):
        au = self.au
        self.osb.set_variant(files, remove)
        info = {}
        comp, findings = fchk.complement_static(self.osb, VT, au.R, au.Vs, au.v_applies, au.proj,
                                                self.av_applied, au.tcm_all, au.config_names or [],
                                                self.config_dirs, fd.TRACK_C_WORKFLOW, None, info=info)
        orders = [("tools", list(fd.STATIC_ROOTS)), ("pytest", ["implementation", "implementation/src"])]
        closure, _ = fchk.closure_identity(self.osb, VT, au.R, au.Vs, au.v_applies, au.proj, au.av, orders)
        return {"findings": findings + closure, "not_run": info.get("not_run", []),
                "wa_notes": (info.get("workflow_analysis") or {}).get("notes", []),
                "wa_status": (info.get("workflow_analysis") or {}).get("status")}


def summarise(res, paths):
    out = []
    for f in res["findings"]:
        if f.get("path") in paths or f.get("id") != "AC-32.spoof":
            out.append({k: f.get(k) for k in ("id", "finding", "path", "reasons", "identity_claims") if f.get(k)})
    return out
