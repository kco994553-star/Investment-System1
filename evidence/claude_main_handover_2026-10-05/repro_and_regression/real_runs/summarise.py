"""Key facts of FPIA output JSON files (v2-real)."""
import hashlib, json, sys
from pathlib import Path
rows = {}
for f in sys.argv[1:]:
    p = Path(f)
    d = json.loads(p.read_text())
    r = d["result"]
    ii = r.get("integration_interference") or {}
    fr = r.get("full_regression") or {}
    ft = r.get("frozen_tools_on_T") or {}
    auth = r.get("authority") or {}
    run = d.get("run") or {}
    rows[p.name] = {
        "file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "result_sha256": d["result_sha256"],
        "recomputed_ok": None,
        "fpia": r["fpia"], "statuses": r.get("statuses"), "summary": r.get("summary"),
        "evidence_validity": r.get("evidence_validity"),
        "subject": r.get("subject"),
        "authority_checks": [(c.get("id"), c.get("status"), c.get("detail", "")[:200]) for c in auth.get("checks", [])],
        "handoff_tip": auth.get("handoff_tip"), "R": auth.get("R"), "Vs": auth.get("Vs"),
        "complement_count": ii.get("complement_count"),
        "static_findings": ii.get("static_findings"),
        "ii_findings": ii.get("findings"),
        "dynamic_invocation_detection": ii.get("dynamic_invocation_detection"),
        "static_not_run": ii.get("static_not_run"),
        "loader": (ii.get("workflow_analysis") or {}).get("loader"),
        "full_regression": {k: fr.get(k) for k in ("status", "rc", "counts", "track_c_nodes", "deselected", "non_track_c_failures", "collect_errors")},
        "frozen_tools_on_T": {"status": ft.get("status"), "evidence_class": ft.get("evidence_class"),
                              "steps": [(s.get("step") or s.get("name"), s.get("rc")) for s in ft.get("steps", [])],
                              "verbatim": [(s.get("verbatim") or {}).get(k, {}).get("file") for s in ft.get("steps", []) for k in ("stdout", "stderr") if isinstance((s.get("verbatim") or {}).get(k), dict)]},
        "v2_binding": (r.get("v2_binding") or {}).get("status") if isinstance(r.get("v2_binding"), dict) else r.get("v2_binding"),
        "verifier": {k: (r.get("runtime_provenance") or {}).get("verifier", {}).get(k) for k in ("commit", "clean", "dirty")},
        "installed": (r.get("runtime_provenance") or {}).get("installed"),
        "run_duration_s": run.get("duration_s"), "run_argv": run.get("argv"), "verbatim_files": run.get("verbatim_files"),
        "path_tokens": run.get("path_tokens"),
    }
    sys.path.insert(0, "/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real/repo/implementation/tools/integration")
print(json.dumps(rows, indent=1, sort_keys=True, default=str))
