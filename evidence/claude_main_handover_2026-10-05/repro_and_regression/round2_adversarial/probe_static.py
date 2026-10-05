"""Real static-phase probe: unmodified Audit.run() (523e702 sources) on a committed tree, stopped after
static_phase (runtime/dynamic/compose no-ops). Same method as the fix2/v2-real probes."""
import json, sys, tempfile, shutil
from pathlib import Path
from harness import ProbeAudit, REGISTER
HERE = Path(__file__).resolve().parent
repo, tree, out = sys.argv[1], sys.argv[2], sys.argv[3]
work = Path(tempfile.mkdtemp(prefix="probe-", dir=str(HERE / "work")))
au = ProbeAudit(repo, tree, REGISTER, "CDR-014", work, None)
r = au.run()
o = {"tree": tree, "fpia": r.get("fpia"), "authority_status": (r.get("authority") or {}).get("status"),
     "reached_static": getattr(au, "reached_static", False)}
if o["reached_static"]:
    o["static_findings"] = au.static_findings
    o["static_not_run"] = au.static_not_run
    o["interference_static"] = "FOUND" if au.static_findings else "NONE(static part)"
    wa = r["integration_interference"]["workflow_analysis"]
    o["workflow_notes"] = [n for n in wa.get("notes", []) if "probe" in n.get("path", "")]
    o["dynamic_invocation_detection"] = r["integration_interference"].get("dynamic_invocation_detection")
shutil.rmtree(work, ignore_errors=True)
Path(out).write_text(json.dumps(o, indent=1, sort_keys=True, default=str, ensure_ascii=False) + "\n")
print(tree[:12], o.get("interference_static"), [f.get("id") + ":" + f.get("finding", "")[:40] for f in o.get("static_findings", [])])
