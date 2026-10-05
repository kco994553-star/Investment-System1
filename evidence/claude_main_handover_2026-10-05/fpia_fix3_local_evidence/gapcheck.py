import sys, tempfile
from pathlib import Path
IMPL = Path(sys.argv[1]); sys.path[:0] = [str(IMPL), str(IMPL / "src")]
from tests import integration_fpia_testkit as tk
from tests import test_integration_fpia_fix3 as t3
w = tk.variant(Path(tempfile.mkdtemp(prefix="gap-", dir=sys.argv[2])))
b = t3.Battery(w.audit(w.c["T0"]))
cases = {
 "py_json": {t3.WF: t3.wf(["run: python ci/tool.json"]), "ci/tool.json": "import subprocess\nsubprocess.run(['python', '%s'])\n" % t3.TOOL},
 "bash_md": {t3.WF: t3.wf(["run: bash ci/notes.md"]), "ci/notes.md": "python %s\n" % t3.TOOL},
 "py_txt_via_sh": {t3.WF: t3.wf(["run: bash ci/a.sh"]), "ci/a.sh": "python ci/b.txt\n", "ci/b.txt": "import os\nos.system('python %s')\n" % t3.TOOL},
}
for k, files in cases.items():
    got, spoof, findings, info = t3._outcome(b, {"files": files})
    print(k, got, [r for f in spoof for r in f["reasons"]][:2])
