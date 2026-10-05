"""G4b: side-file name with path components (read outside <out>.verbatim/), consistent re-hash, no anchor."""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = HERE.parent
PY = str(W / "venv" / "bin" / "python")
CLI = str(W / "repo" / "implementation" / "tools" / "integration" / "track_c_fpia.py")
SRC = Path("/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real/out/fpia_c1_acaf1b5_A.json")
sys.path.insert(0, str(W / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia as F  # noqa
d = HERE / "cases" / "T7_side_file_path_traversal"
if d.exists():
    shutil.rmtree(d)
d.mkdir(parents=True)
shutil.copytree(str(SRC) + ".verbatim", d / "fpia.json.verbatim")
secret = HERE / "cases" / "outside-secret.txt"
secret.write_text("not a side file\n")
doc = json.loads(SRC.read_text(encoding="utf-8"))
step = [s for s in doc["result"]["frozen_tools_on_T"]["steps"] if (s.get("verbatim") or {}).get("stdout")][0]
orig = step["verbatim"]["stdout"]["file"]
(d / "fpia.json.verbatim" / orig).unlink()
data = secret.read_bytes()
step["verbatim"]["stdout"].update(file="../../outside-secret.txt", sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
doc["result_sha256"] = hashlib.sha256(F.canonical_bytes(doc["result"])).hexdigest()
(d / "fpia.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
r = subprocess.run([PY, CLI, "--verify-output", str(d / "fpia.json")], capture_output=True)
txt = r.stdout.decode()
rep = json.loads(txt.rsplit("fpia-output:", 1)[0])
print(json.dumps({"rc": r.returncode, "status": txt.strip().splitlines()[-1],
                  "checks_mentioning_traversal": [c for c in rep["checks"] if "outside" in c["check"]]}, indent=1))
