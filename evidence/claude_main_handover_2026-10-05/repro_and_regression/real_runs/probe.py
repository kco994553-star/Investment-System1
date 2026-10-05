"""v2-real static screen: the unmodified Audit.run() of the verifier checkout (523e702) runs through
check_caller_repository, resolve, populate, authenticate, derive, reference_checks,
caller_fetch_problems and static_phase; only runtime_phase / dynamic_phase / compose_components are
replaced by no-ops in a subclass. READ-ONLY with respect to the FPIA sources.
usage: probe.py <repo> <tree> <out.json>"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "repo" / "implementation" / "tools" / "integration"
sys.path.insert(0, str(SRC))
import track_c_fpia as F  # noqa: E402
import track_c_fpia_workflows as fw  # noqa: E402


class ProbeAudit(F.Audit):
    def runtime_phase(self):
        self.st["runtime_provenance"] = "PROBE_STOPPED"

    def dynamic_phase(self):
        raise AssertionError("not reached")

    def compose_components(self):
        self.reached_static = True


def main():
    repo, tree, out = sys.argv[1], sys.argv[2], sys.argv[3]
    (HERE / "work").mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="probe-", dir=str(HERE / "work")))
    au = ProbeAudit(repo, tree, "f36292689eabf7ba3700d57a949fa0fb7343a2c6", "CDR-014", work, None)
    r = au.run()
    o = {"tree": tree, "repo": repo, "fpia": r.get("fpia"),
         "authority_status": (r.get("authority") or {}).get("status"),
         "authority_not_pass_checks": [c for c in (r.get("authority") or {}).get("checks", [])
                                       if c.get("status") != "PASS"],
         "handoff_tip": (r.get("authority") or {}).get("handoff_tip"),
         "environment": r.get("environment"),
         "caller_fetch_problems": au.caller_fetch_problems(),
         "caller_fetches": [{k: f.get(k) for k in ("label", "rc", "rejected", "missing")}
                            for f in au.sb.fetch_log if f.get("source") == au.repo],
         "reached_static": getattr(au, "reached_static", False),
         "loader": fw.loader_info(), "yaml_module_file": getattr(fw.yaml, "__file__", None)}
    if o["reached_static"]:
        ii = r["integration_interference"]
        o["static_findings"] = au.static_findings
        o["static_not_run"] = au.static_not_run
        o["interference_static"] = "INTEGRATION_INTERFERENCE_FOUND" if au.static_findings else "NONE(static part)"
        o["dynamic_invocation_detection"] = ii.get("dynamic_invocation_detection")
        o["dynamic_non_claim_in_non_claims"] = fw.DYNAMIC_NON_CLAIM in r.get("non_claims", [])
        o["workflow_analysis"] = ii.get("workflow_analysis")
        o["complement_count"] = ii.get("complement_count")
        o["v2_static"] = ("FAIL" if any(c["status"] == "FAIL" for c in au.v2_checks)
                          else ("NOT_APPLICABLE" if not any(au.v_applies.values()) else "PASS(static part)"))
    shutil.rmtree(work, ignore_errors=True)
    Path(out).write_text(json.dumps(o, indent=1, sort_keys=True, default=str) + "\n")
    print(tree, o["fpia"], o["authority_status"], o.get("interference_static"), len(o.get("static_findings") or []))


main()
