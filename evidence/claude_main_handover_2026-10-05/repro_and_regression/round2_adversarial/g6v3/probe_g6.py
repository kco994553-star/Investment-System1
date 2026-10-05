"""G6 (AC-04 wording) probes: unmodified Audit.run() of the 523e702 sources on committed trees."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = HERE.parent
sys.path.insert(0, str(W))
import mkcommit  # noqa
from harness import ProbeAudit, REGISTER  # noqa
REPO = str(W / "repo")
K = "b8e39a2196a6d7794a04a0cd5393c68329e126ca"
P2 = mkcommit.make("P2", {"implementation/tools/track_c_c9_probe.py": "print('track c namespace file not in R')\n"}, base=K)
P4 = mkcommit.make("P4", {"implementation/tools/track_c_c6_acceptance.py": "# replaced content, same path as R\n"}, base=K)
cases = {"K_canonical": K, "P1_one_R_path": subprocess.check_output(["git", "-C", REPO, "rev-parse", "v2adv/P1"]).decode().strip(),
         "P2_ns_path_not_in_R": P2, "P3_squash": subprocess.check_output(["git", "-C", REPO, "rev-parse", "v2adv/P3"]).decode().strip(),
         "P4_R_path_with_other_bytes": P4}
out = {}
for name, T in cases.items():
    work = Path(tempfile.mkdtemp(prefix="g6-", dir=str(W / "work")))
    au = ProbeAudit(REPO, T, REGISTER, "CDR-014", work, None)
    r = au.run()
    ac04 = [c for c in (r.get("authority") or {}).get("checks", []) if c.get("id") == "AC-04"]
    out[name] = {"tree": T, "fpia": r["fpia"]["status"], "authority": (r.get("authority") or {}).get("status"),
                 "AC-04": ac04, "summary": r.get("summary")}
    shutil.rmtree(work, ignore_errors=True)
    print(name, T[:12], r["fpia"]["status"], [(c.get("case"), c.get("track_c_paths_present_at_T")) for c in ac04], flush=True)
(HERE / "g6_result.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
