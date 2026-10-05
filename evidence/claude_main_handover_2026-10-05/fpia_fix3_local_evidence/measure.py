"""H8 measurement: the static phase (complement_static + workflow_spoof + closure, via the unmodified
Audit.static_phase of the given FPIA sources) on a list of real trees. One authenticated audit (to the static
phase) on the first tree; for every further tree the same Audit re-runs static_phase with T, v_applies and the
Track C workflow at T recomputed. Usage: measure.py <fpia_src_dir> <repo> <out.json> <label=commit> ..."""
import json, sys, tempfile, shutil, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[1])
import track_c_fpia as F  # noqa
import track_c_fpia_derive as fd  # noqa
REGISTER = "f36292689eabf7ba3700d57a949fa0fb7343a2c6"


class ProbeAudit(F.Audit):
    def runtime_phase(self):
        self.st["runtime_provenance"] = "PROBE_STOPPED"
    def dynamic_phase(self):
        raise AssertionError("not reached")
    def compose_components(self):
        self.reached_static = True


def summarise(au, label, T, t0):
    r = au.result
    ii = r.get("integration_interference") or {}
    wa = ii.get("workflow_analysis") or {}
    return {"label": label, "T": T, "v_applies": au.v_applies, "seconds": round(time.time() - t0, 1),
            "static_findings": au.static_findings, "static_not_run": getattr(au, "static_not_run", None),
            "complement_count": ii.get("complement_count"),
            "analysed": wa.get("analysed"), "notes": wa.get("notes"), "reached": wa.get("reached"),
            "out_of_tree_references": wa.get("out_of_tree_references"), "self_placement": wa.get("self_placement"),
            "mention_set": wa.get("mention_set"), "track_c_identity": wa.get("track_c_identity")}


def main():
    repo, out = sys.argv[2], sys.argv[3]
    pairs = [a.split("=", 1) for a in sys.argv[4:]]
    work = Path(tempfile.mkdtemp(prefix="h8-", dir=str(HERE)))
    rows = []
    t0 = time.time()
    label, T = pairs[0]
    au = ProbeAudit(repo, T, REGISTER, "CDR-014", work, None)
    r = au.run()
    assert getattr(au, "reached_static", False), r.get("fpia")
    rows.append(summarise(au, label, au.T, t0))
    print(label, T[:12], len(au.static_findings), flush=True)
    for label, T in pairs[1:]:
        t0 = time.time()
        T = au.resolve(T, "--tree")
        if not au.sb.has_commit(T):
            au.sb.fetch(repo, ["%s:refs/fpia/in/%s" % (T, T)], label="h8")
        au.T = T
        au.v_applies = {V: au.sb.is_ancestor(V, T) for V in au.Vs}
        au.wf_T = au.workflow(T) if au.sb.read(T, fd.TRACK_C_WORKFLOW) is not None else None
        au.result = {"authority": au.result["authority"], "derivation": au.result.get("derivation", {}),
                     "statuses": {}, "checks": {}}
        au.st = au.result["statuses"]
        au.static_phase()
        rows.append(summarise(au, label, T, t0))
        print(label, T[:12], len(au.static_findings), flush=True)
    Path(out).write_text(json.dumps({"fpia_src": sys.argv[1], "rows": rows}, indent=1, sort_keys=True,
                                    ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)


main()
