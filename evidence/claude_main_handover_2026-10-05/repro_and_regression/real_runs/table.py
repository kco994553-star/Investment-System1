"""v2-real resume: one line per full CLI output (file sha256, result_sha256, verdict, exit, wall, verify)."""
import hashlib, json, re
from pathlib import Path
W = Path("/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real/out")
rows = []
for j in sorted(W.glob("fpia_*.json")):
    lab = j.name[len("fpia_"):-len(".json")]
    d = json.loads(j.read_text()); r = d["result"]
    summ = (W / ("fpia_%s.summary" % lab)).read_text()
    ver = (W / ("fpia_%s.verify" % lab)).read_text()
    pre = (W / ("fpia_%s.pre" % lab)).read_text()
    ii = r.get("integration_interference") or {}
    rows.append({
        "label": lab, "tree": r["subject"]["tree"], "verifier": r["runtime_provenance"]["verifier"]["commit"],
        "handoff_tip": r["authority"].get("handoff_tip"),
        "python": re.search(r"python=(\S+)", pre).group(1), "repo_refs_sha256": re.search(r"repo_refs_sha256=(\S+)", pre).group(1),
        "start": (W / ("fpia_%s.start" % lab)).read_text().strip(), "end": (W / ("fpia_%s.end" % lab)).read_text().strip(),
        "exit": re.search(r"exit=(\d+)", summ).group(1), "wall_s": re.search(r"wall_s=(\d+)", summ).group(1),
        "verify": "VERIFIED" if "fpia-output: VERIFIED" in ver and "verify_exit=0" in ver else "NOT_VERIFIED",
        "file_sha256": hashlib.sha256(j.read_bytes()).hexdigest(), "result_sha256": d["result_sha256"],
        "fpia": r["fpia"]["status"], "reasons": r["fpia"]["reasons"], "statuses": r["statuses"],
        "summary": r["summary"],
        "interference_findings": [(f.get("id"), f.get("path"), f.get("reasons")) for f in ii.get("findings", [])],
        "dynamic_invocation_detection": ii.get("dynamic_invocation_detection"),
        "complement_count": ii.get("complement_count"),
        "side_files": sorted(p.name for p in (W / (j.name + ".verbatim")).iterdir()) if (W / (j.name + ".verbatim")).is_dir() else [],
    })
print(json.dumps(rows, indent=1))
