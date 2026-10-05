import json, sys, time
sys.path.insert(0, ".")
from harness import Harness, summarise
t=time.time()
h = Harness(sys.argv[1], sys.argv[2])
print("base static findings", len(h.base_static), "secs", round(time.time()-t,1))
wf = """name: track-c-evl-validation
on: [push]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""
res = h.run({".github/workflows/probe-a.yml": wf})
print(json.dumps(summarise(res, {".github/workflows/probe-a.yml"}), indent=1))
res = h.run({})
print("empty variant findings", len(res["findings"]), res["wa_status"])
