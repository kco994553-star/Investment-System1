"""Determinism probe (static part): unmodified Audit.run() to static_phase, work dir from tempfile.mkdtemp
(default TMPDIR, as run_fpia does), then the CLI's own scrub + JSON round trip + canonical sha256."""
import hashlib, json, sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import ProbeAudit, REGISTER, F
repo, tree, out = sys.argv[1], sys.argv[2], sys.argv[3]
work = Path(tempfile.mkdtemp(prefix="track-c-fpia-"))
au = ProbeAudit(repo, tree, REGISTER, "CDR-014", work, None)
r = au.run()
r = F.scrub(r, work.resolve())
r = json.loads(json.dumps(r, sort_keys=True, default=str))
shutil.rmtree(work, ignore_errors=True)
b = F.canonical_bytes(r)
Path(out).write_bytes(b)
print(hashlib.sha256(b).hexdigest(), str(work))
