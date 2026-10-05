"""Hash-seed determinism of the static analysis on a multi-reason variant (unmodified 523e702 sources)."""
import hashlib, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = HERE.parent
sys.path.insert(0, str(W))
from harness import Harness  # noqa
import variants as VV  # noqa
T = subprocess.check_output(["git", "-C", str(W / "repo"), "rev-parse", "acaf1b5"]).decode().strip()
multi = {VV.WF: ("name: TRACK-C-EVL-VALIDATION\nrun-name: track-c-evI-validation\non: [push]\nenv:\n  A: implementation/tools/track_c_c6_acceptance.py\n"
                 "  B: implementation/tools/track_c_c7_acceptance.py\n  G: implementation/tools/track_c_c*.py\n"
                 "jobs:\n  validate:\n    runs-on: ubuntu-latest\n    steps:\n"
                 "      - run: bash ci/a.sh && python -m pytest -q -k evl_c6 && python ci/b.py\n        working-directory: .\n"
                 "      - uses: ./.github/actions/tc\n"),
         "ci/a.sh": "python implementation/tools/track_c_c8_partial_acceptance.py\n",
         "ci/b.py": "import investment_system.evl\nimport subprocess\nsubprocess.run(['python', 'implementation/tools/track_c_c7_acceptance.py'])\n",
         ".github/actions/tc/action.yml": "name: tc\nruns:\n  using: composite\n  steps:\n    - run: python implementation/tools/track_c_c6_acceptance.py\n      shell: bash\n"}
h = Harness(str(W / "repo"), T)
res = h.run(multi)
b = json.dumps(res, sort_keys=True, ensure_ascii=False).encode()
print(hashlib.sha256(b).hexdigest(), len(res["findings"]), sum(len(f.get("reasons", [])) for f in res["findings"]))
(HERE / ("seed_%s.json" % sys.argv[1])).write_bytes(b)
