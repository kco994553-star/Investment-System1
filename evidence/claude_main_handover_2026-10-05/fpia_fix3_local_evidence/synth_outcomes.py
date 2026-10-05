import sys, json, tempfile
from pathlib import Path
IMPL = Path(sys.argv[1]); sys.path[:0] = [str(IMPL), str(IMPL / "src")]
from tests import integration_fpia_testkit as tk
from tests import test_integration_fpia_fix3 as t3
w = tk.variant(Path(tempfile.mkdtemp(prefix="so-", dir=sys.argv[2])))
b = t3.Battery(w.audit(w.c["T0"]))
out = {}
for v in t3.V:
    got, spoof, findings, info = t3._outcome(b, v)
    out[v["id"]] = {"got": got, "reasons": [r for f in spoof for r in f["reasons"]],
                    "other": [(f["id"], f.get("path"), f.get("finding")) for f in findings if f["id"] != "AC-32.spoof"]}
    print("%-6s %-9s %s | %s" % (v["id"], got, "; ".join(out[v["id"]]["reasons"])[:170], out[v["id"]]["other"][:2]), flush=True)
Path(sys.argv[3]).write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True))
