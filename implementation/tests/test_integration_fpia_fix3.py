"""Fix round 3 (CDR-014 §14): AC-32.spoof as a conservative over-approximation (H1 identity keys with
GitHub constant-expression folding, H2 mention-based detection of what a complement workflow can run),
environment independence of the verdict and result_sha256 (H3), the output verifier (H4), fetch status
lines split on LF only (H5), AC-04 wording (H6) and verifier provenance of every file under
tools/integration (H7).

Every variant of the previous adversarial round (v2-adversarial classification, 156 variants) is pinned
below with its expected component/status: the 22 D1 and 41 D2 variants and S24V2 must be FOUND
(AC-32.spoof, INTEGRATION_INTERFERENCE_FOUND); the open user decisions are pinned as current behaviour,
never decided: D3-c (dynamically constructed invocations: dynamic_invocation_detection stays NOT_CLAIMED;
variants that literally name a Track C file are caught by the mention rule as a side effect, the others
stay NOT_FOUND), D3-e (code from outside T: out_of_tree_code_analysis NOT_ANALYSED, recorded and named in
the summary; same-repository remote workflows are FOUND fail-closed) and D3-b (job id collisions stay notes).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia
from tools.integration import track_c_fpia_auth as fauth
from tools.integration import track_c_fpia_checks as fchk
from tools.integration import track_c_fpia_derive as fd
from tools.integration import track_c_fpia_git as fgit
from tools.integration import track_c_fpia_runner as frun
from tools.integration import track_c_fpia_workflows as fw

# ---- the previous round's variant battery (ported verbatim; Track C names are the synthetic world's) -----
TC = "track-c-evl-validation"
TOOL = "implementation/tools/track_c_c6_acceptance.py"
WF = ".github/workflows/probe-a.yml"


def wf(steps, name="probe", extra_top="", job_extra="", runs_on="ubuntu-latest"):
    body = "".join("      - %s\n" % s.replace("\n", "\n      ") for s in steps)
    return ("name: %s\n%son: [push]\njobs:\n  check:\n    runs-on: %s\n%s    steps:\n%s"
            % (name, extra_top, runs_on, job_extra, body))


V = []


def add(vid, group, desc, files, expect, run=None, note=None):
    V.append({"id": vid, "group": group, "desc": desc, "files": files, "expect": expect, "run": run, "note": note})


JOB = "jobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"

# ------------------------------------------------------------------------------------------------ controls
add("C00", "control", "base acaf1b5 + benign workflow", {WF: wf(["run: echo hi"])}, "NOT_FOUND")
add("C01", "control", "S0: exact Track C name", {WF: "name: %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("C02", "control", "S9: bash script running Track C tool", {
    WF: wf(["run: bash scripts/ci_probe.sh"]),
    "scripts/ci_probe.sh": "cd implementation && PYTHONPATH=src:. python tools/track_c_c6_acceptance.py\n"},
    "FOUND", run=True)
add("C03", "control", "S15: string-concatenated path (D3-c non-claim)", {
    WF: wf(["run: python scripts/probe_runner.py"]),
    "scripts/probe_runner.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "implementation/tools/" + "track_c_c6_acceptance.py"], check=True)\n'},
    "NOT_FOUND(D3-c)", run=True)
add("C04", "control", "bash -c with cd (claimed handled)", {
    WF: wf(["run: bash -c 'cd implementation/tools && python track_c_c6_acceptance.py'"])}, "FOUND", run=True)
add("C05", "control", "working-directory: implementation/tools + relative tool", {
    WF: wf(["run: python track_c_c6_acceptance.py\n  working-directory: implementation/tools"])}, "FOUND", run=True)

# ------------------------------------------------------------------------------------------------ G1 YAML forms
add("Y01", "G1", "name via alias of an anchor defined on an env value", {
    WF: "env:\n  X: &n %s\nname: *n\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y02", "G1", "name via alias, anchor defined later in a job env (forward ref invalid YAML)", {
    WF: "name: *n\non: [push]\nenv:\n  X: &n %s\n%s" % (TC, JOB)}, "FOUND(fail-closed)")
add("Y03", "G1", "name inside a root merge key (<<: {name: ...})", {
    WF: "<<: {name: %s}\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y04", "G1", "multi-document: doc1 benign, doc2 Track C name", {
    WF: "name: probe\non: [push]\n%s---\nname: %s\non: [push]\n%s" % (JOB, TC, JOB)}, "FOUND(fail-closed)")
add("Y05", "G1", "explicit document markers ---/... single doc", {
    WF: "%%YAML 1.1\n---\nname: %s\non: [push]\n%s...\n" % (TC, JOB)}, "FOUND")
add("Y06", "G1", "flow-style whole workflow", {
    WF: "{name: %s, on: [push], jobs: {check: {runs-on: ubuntu-latest, steps: [{run: echo hi}]}}}\n" % TC}, "FOUND")
add("Y07", "G1", "block literal strip |-", {WF: "name: |-\n  %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y08", "G1", "block literal keep |+ with trailing blank lines", {WF: "name: |+\n  %s\n\n\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y09", "G1", "folded >- split across lines with no space (escaped in double quotes)", {
    WF: 'name: "track-c-evl-\\\n  validation"\non: [push]\n%s' % JOB}, "FOUND")
add("Y10", "G1", "block literal with indentation indicator |2- (leading space in value)", {
    WF: "name: |2-\n   %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y11", "G1", "verbatim tag !<tag:yaml.org,2002:str>", {WF: "name: !<tag:yaml.org,2002:str> %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y12", "G1", "%TAG handle !e! -> !e!str", {WF: "%%TAG !e! tag:yaml.org,2002:\n---\nname: !e!str %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y13", "G1", "local tag !foo on quoted name", {WF: 'name: !foo "%s"\non: [push]\n%s' % (TC, JOB)}, "FOUND")
add("Y14", "G1", "UTF-8 BOM", {WF: ("\ufeffname: %s\non: [push]\n%s" % (TC, JOB)).encode("utf-8")}, "FOUND")
add("Y15", "G1", "CRLF line endings", {WF: ("name: %s\non: [push]\n%s" % (TC, JOB)).replace("\n", "\r\n")}, "FOUND")
add("Y16", "G1", "lone CR line endings", {WF: ("name: %s\non: [push]\n%s" % (TC, JOB)).replace("\n", "\r")}, "FOUND")
add("Y17", "G1", "tab after colon (name:\\tvalue)", {WF: "name:\t%s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y18", "G1", "trailing tab inside quoted value", {WF: 'name: "%s\\t"\non: [push]\n%s' % (TC, JOB)}, "FOUND")
add("Y19", "G1", "duplicate name keys, Track C second", {WF: "name: probe\nname: %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y20", "G1", "duplicate name keys, Track C first", {WF: "name: %s\nname: probe\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y21", "G1", "very long line: 200k spaces then comment after name", {
    WF: "name: %s%s# c\non: [push]\n%s" % (TC, " " * 200000, JOB)}, "FOUND")
add("Y22", "G1", "very long implicit key (>1024 chars) before name", {
    WF: "env:\n  %s: x\nname: %s\non: [push]\n%s" % ("K" * 1100, TC, JOB)}, "FOUND")
add("Y23", "G1", "complex key ? name : value", {WF: "? name\n: %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y24", "G1", "escaped key \"na\\u006De\"", {WF: '"na\\u006De": %s\non: [push]\n%s' % (TC, JOB)}, "FOUND")
add("Y25", "G1", "NEL (U+0085) as line break between keys", {WF: "name: probe\x85name2: x\nname: %s\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y26", "G1", "comment ending in U+2028 then name key (PyYAML sees key; 1.2 parser sees comment)", {
    WF: "# c\u2028name: %s\nname: probe\non: [push]\n%s" % (TC, JOB)}, "NOT_FOUND?")
add("Y27", "G1", "run-name constant expression ${{ 'track-c-evl-validation' }}", {
    WF: "name: probe\nrun-name: ${{ '%s' }}\non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y28", "G1", "run-name format() expression", {
    WF: "name: probe\nrun-name: ${{ format('track-c-{0}-validation', 'evl') }}\non: [push]\n%s" % JOB}, "FOUND")
add("Y29", "G1", "run-name with embedded expression track-c-${{ 'evl' }}-validation", {
    WF: "name: probe\nrun-name: track-c-${{ 'evl' }}-validation\non: [push]\n%s" % JOB}, "FOUND")
add("Y30", "G1", "name contains expression syntax (workflow name does not evaluate)", {
    WF: "name: ${{ '%s' }}\non: [push]\n%s" % (TC, JOB)}, "NOT_FOUND")
# ------------------------------------------------------------------------------------------------ G1 confusables
for vid, desc, nm in [
    ("U01", "trailing U+2800 BRAILLE PATTERN BLANK", TC + "\u2800"),
    ("U02", "U+2800 replacing nothing, inserted mid-name", "track-c-evl\u2800-validation"),
    ("U03", "trailing U+1D159 MUSICAL SYMBOL NULL NOTEHEAD", TC + "\U0001D159"),
    ("U04", "dotless i + U+0307 COMBINING DOT ABOVE for each i", TC.replace("i", "\u0131\u0307")),
    ("U05", "U+2011 NON-BREAKING HYPHEN for hyphens", TC.replace("-", "\u2011")),
    ("U06", "U+FE63 SMALL HYPHEN-MINUS", TC.replace("-", "\ufe63")),
    ("U07", "U+2E3A/2014? EM DASH for hyphens", TC.replace("-", "\u2014")),
    ("U08", "U+00AD SOFT HYPHEN for hyphens (renders invisible)", TC.replace("-", "\u00ad")),
    ("U09", "U+FFFC OBJECT REPLACEMENT trailing", TC + "\ufffc"),
    ("U10", "U+FFF9 INTERLINEAR ANNOTATION ANCHOR trailing", TC + "\ufff9"),
    ("U11", "Cyrillic a/c/e/o/i mix", "tr\u0430\u0441k-\u0441-\u0435vl-v\u0430lid\u0430t\u0456\u043en"),
    ("U12", "U+0130 capital I with dot (casefold i + U+0307)", TC.replace("i", "\u0130")),
    ("U13", "U+2024 ONE DOT LEADER? no - U+A4FE? use U+02D7 MODIFIER MINUS for hyphen", TC.replace("-", "\u02d7")),
    ("U14", "U+0332 combining low line after every char? no: single U+034F CGJ (DI)", TC.replace("-", "-\u034f")),
    ("U15", "trailing U+3164 HANGUL FILLER (DI)", TC + "\u3164"),
    ("U16", "trailing U+115F + U+1160 (DI)", TC + "\u115f\u1160"),
    ("U17", "trailing U+2028 LINE SEPARATOR in quoted scalar", TC + "\u2028"),
    ("U18", "U+0627 ARABIC ALEF for l (RTL)", TC.replace("l", "\u0627")),
    ("U19", "l -> U+05C0 HEBREW PUNCTUATION PASEQ", TC.replace("l", "\u05c0")),
    ("U20", "trailing U+180E MONGOLIAN VOWEL SEPARATOR", TC + "\u180e"),
    ("U21", "U+2063 INVISIBLE SEPARATOR mid", "track-c\u2063-evl-validation"),
    ("U22", "trailing U+1BCA1 SHORTHAND FORMAT CONTINUING OVERLAP (DI)", TC + "\U0001BCA1"),
    ("U23", "U+0338? no: U+20E0? -> trailing U+200B ZWSP (DI)", TC + "\u200b"),
    ("U24", "trailing U+E0020 TAG SPACE (DI)", TC + "\U000E0020"),
    ("U25", "trailing ideographic space U+3000 (NFKC space, strip)", TC + "\u3000"),
    ("U26", "trailing U+16FE4 KHITAN FILLER (Cf, not DI in Unicode 15.1)", TC + "\U00016FE4"),
]:
    add(vid, "G1-confusable", desc, {WF: ('name: "%s"\non: [push]\n%s' % (nm.encode("unicode_escape").decode().replace('"', '\\"'), JOB))},
        "FOUND?", note=repr(nm))

# filename stems
add("F01", "G1-stem", "no name; file track-c-evl-validation.yaml", {
    ".github/workflows/track-c-evl-validation.yaml": "on: [push]\n" + JOB}, "FOUND")
add("F02", "G1-stem", "no name; file Track-C-EVL-Validation.YML", {
    ".github/workflows/Track-C-EVL-Validation.YML": "on: [push]\n" + JOB}, "FOUND")
add("F03", "G1-stem", "no name; stem with trailing U+2800", {
    ".github/workflows/track-c-evl-validation\u2800.yml": "on: [push]\n" + JOB}, "FOUND?")
add("F04", "G1-stem", "no name; file in subdirectory (GitHub ignores)", {
    ".github/workflows/sub/track-c-evl-validation.yml": "on: [push]\n" + JOB}, "NOT_FOUND(ignored by GitHub)")

# ------------------------------------------------------------------------------------------------ G2 invocation
def g2(vid, desc, steps, extra_files=None, expect="FOUND", job_extra="", runs_on="ubuntu-latest", extra_top="", note=None):
    files = {WF: wf(steps, job_extra=job_extra, runs_on=runs_on, extra_top=extra_top)}
    files.update(extra_files or {})
    add(vid, "G2", desc, files, expect, run=True, note=note)


g2("I01", "cd ${{ github.workspace }}/implementation/tools && python <tool>",
   ["run: cd ${{ github.workspace }}/implementation/tools && python track_c_c6_acceptance.py"])
g2("I02", "cd \"$GITHUB_WORKSPACE/implementation/tools\" && python <tool>",
   ['run: cd "$GITHUB_WORKSPACE/implementation/tools" && python track_c_c6_acceptance.py'])
g2("I03", "working-directory: ${{ github.workspace }}/implementation/tools",
   ["run: python track_c_c6_acceptance.py\n  working-directory: ${{ github.workspace }}/implementation/tools"])
g2("I04", "pushd implementation/tools",
   ["run: pushd implementation/tools && python track_c_c6_acceptance.py"])
g2("I05", "cd -P implementation/tools",
   ["run: cd -P implementation/tools && python track_c_c6_acceptance.py"])
g2("I06", "cd -- implementation/tools",
   ["run: cd -- implementation/tools && python track_c_c6_acceptance.py"])
g2("I07", "env -C implementation/tools python <tool>",
   ["run: env -C implementation/tools python track_c_c6_acceptance.py"])
g2("I08", "bash -ec 'cd implementation/tools && python <tool>' (combined flags)",
   ["run: bash -ec 'cd implementation/tools && python track_c_c6_acceptance.py'"])
g2("I09", "sh -xc 'cd ... && python <tool>'",
   ["run: sh -xc 'cd implementation/tools && python track_c_c6_acceptance.py'"])
g2("I10", "PYTHONPATH=implementation/tools python -m track_c_c6_acceptance",
   ["run: PYTHONPATH=implementation/tools python -m track_c_c6_acceptance"])
g2("I11", "python -m <tree module> (implementation/src/ci_probe/__main__.py) calling the tool with subprocess cwd=",
   ["run: cd implementation && PYTHONPATH=src python -m ci_probe"],
   {"implementation/src/ci_probe/__init__.py": "",
    "implementation/src/ci_probe/__main__.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "track_c_c6_acceptance.py"], cwd="tools", check=True)\n'})
g2("I12", "python script: os.chdir('implementation/tools') then os.system('python track_c_c6_acceptance.py')",
   ["run: python ci/run_tc.py"],
   {"ci/run_tc.py": 'import os\nos.chdir("implementation/tools")\nos.system("python track_c_c6_acceptance.py")\n'})
g2("I13", "make target running the tool (Makefile recipe)",
   ["run: make tc"],
   {"Makefile": "tc:\n\tpython implementation/tools/track_c_c6_acceptance.py\n"})
g2("I14", "npm script running the tool (package.json)",
   ["run: npm run tc"],
   {"package.json": '{"name": "x", "version": "1.0.0", "scripts": {"tc": "python implementation/tools/track_c_c6_acceptance.py"}}\n'})
g2("I15", "bash -o pipefail ci/tc.sh (option with value before script)",
   ["run: bash -o pipefail ci/tc.sh"],
   {"ci/tc.sh": "python implementation/tools/track_c_c6_acceptance.py\n"},
   note="the script itself contains the literal tool path; only reached if followed")
g2("I16", "bash --noprofile --norc -eo pipefail ci/tc.sh (GitHub's own bash template)",
   ["run: bash --noprofile --norc -eo pipefail ci/tc.sh"],
   {"ci/tc.sh": "cd implementation/tools\npython track_c_c6_acceptance.py\n"})
g2("I17", "timeout 600 bash ci/tc.sh (wrapper not in WRAPPERS)",
   ["run: timeout 600 bash ci/tc.sh"],
   {"ci/tc.sh": "cd implementation/tools\npython track_c_c6_acceptance.py\n"})
g2("I18", "nice -n 5 python ci/run.py (wrapper with option)",
   ["run: nice -n 5 python ci/run.py"],
   {"ci/run.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "track_c_c6_acceptance.py"], cwd="implementation/tools", check=True)\n'})
g2("I19", "extension-less, shebang-less executable script ./ci/run-tc (bash ENOEXEC fallback)",
   ["run: ./ci/run-tc"],
   {"ci/run-tc": ("100755", "cd implementation/tools\npython track_c_c6_acceptance.py\n")})
g2("I20", "shell line continuation splitting the path (implementation/to\\<NL>ols/...)",
   ["run: |\n    python implementation/to\\\n    ols/track_c_c6_acceptance.py"],
   note="bash joins backslash-newline with no space")
g2("I21", "ANSI-C quoting $'\\x69mplementation/tools/...'",
   ["run: python $'\\x69mplementation/tools/track_c_c6_acceptance.py'"])
g2("I22", "brace expansion implementation/t{o,}ols/... (extra argv ignored by the tool? python runs first)",
   ["run: python implementation/t{o,}ols/track_c_c6_acceptance.py"])
g2("I23", "absolute runner path /home/runner/work/<repo>/<repo>/implementation/tools/<tool>",
   ["run: python /home/runner/work/Investment-System1/Investment-System1/implementation/tools/track_c_c6_acceptance.py"],
   note="literal absolute path of the GitHub-hosted runner workspace")
g2("I24", "$PWD prefix: python \"$PWD/implementation/tools/<tool>\"",
   ['run: python "$PWD/implementation/tools/track_c_c6_acceptance.py"'])
g2("I25", "${PWD} prefix", ['run: python "${PWD}/implementation/tools/track_c_c6_acceptance.py"'])
g2("I26", "python f-string with cwd prefix in a followed script",
   ["run: python ci/run2.py"],
   {"ci/run2.py": 'import os, subprocess, sys\nsubprocess.run([sys.executable, f"{os.getcwd()}/implementation/tools/track_c_c6_acceptance.py"], check=True)\n'})
g2("I27", "env indirection, literal full path in env (claimed: all scalars scanned)",
   ["run: python \"$SCRIPT\"\n  env:\n    SCRIPT: implementation/tools/track_c_c6_acceptance.py"], expect="FOUND")
g2("I28", "env indirection, directory in env + cd $D (paths in shell variables: D3-c)",
   ["run: cd \"$D\" && python track_c_c6_acceptance.py\n  env:\n    D: implementation/tools"], expect="NOT_FOUND(D3-c)")
g2("I29", "reusable workflow (job uses ./.github/workflows/x.yml) whose step uses cd ${{ github.workspace }}/...",
   ["run: echo caller"],
   {".github/workflows/x.yml": "name: x\non: [workflow_call]\njobs:\n  inner:\n    runs-on: ubuntu-latest\n    steps:\n      - run: cd ${{ github.workspace }}/implementation/tools && python track_c_c6_acceptance.py\n"},
   note="caller job below replaced")
g2("I30", "reusable workflow from the same repository by remote ref (owner/repo/.github/workflows/track-c-evl-validation.yml@ref)",
   ["run: echo caller"], note="caller job replaced; calls the Track C workflow itself at another ref")
g2("I31", "composite action runs ${{ github.action_path }}/run.sh which calls the tool",
   ["uses: ./.github/actions/tc"],
   {".github/actions/tc/action.yml": "name: tc\nruns:\n  using: composite\n  steps:\n    - run: bash ${{ github.action_path }}/run.sh\n      shell: bash\n",
    ".github/actions/tc/run.sh": "python implementation/tools/track_c_c6_acceptance.py\n"})
g2("I32", "composite action runs $GITHUB_ACTION_PATH/run.sh",
   ["uses: ./.github/actions/tc"],
   {".github/actions/tc/action.yml": "name: tc\nruns:\n  using: composite\n  steps:\n    - run: bash \"$GITHUB_ACTION_PATH/run.sh\"\n      shell: bash\n",
    ".github/actions/tc/run.sh": "python implementation/tools/track_c_c6_acceptance.py\n"})
g2("I33", "node local action (runs.using node20, main index.js) spawning the tool",
   ["uses: ./.github/actions/tcnode"],
   {".github/actions/tcnode/action.yml": "name: tcnode\nruns:\n  using: node20\n  main: index.js\n",
    ".github/actions/tcnode/index.js": "require('child_process').execFileSync('python', ['implementation/tools/track_c_c6_acceptance.py'], {stdio: 'inherit'});\n"})
g2("I34", "docker local action (Dockerfile ENTRYPOINT with /github/workspace path)",
   ["uses: ./.github/actions/tcdocker"],
   {".github/actions/tcdocker/action.yml": "name: tcdocker\nruns:\n  using: docker\n  image: Dockerfile\n",
    ".github/actions/tcdocker/Dockerfile": "FROM python:3.11\nENTRYPOINT [\"python\", \"/github/workspace/implementation/tools/track_c_c6_acceptance.py\"]\n"})
g2("I35", "pytest @argsfile (-k evl_c6 inside the file)",
   ["run: cd implementation && PYTHONPATH=src python -m pytest -q @../ci/tc.args"],
   {"ci/tc.args": "-k\nevl_c6\n"})
g2("I36", "PYTEST_ADDOPTS='-k evl_c6' + bare pytest",
   ["run: cd implementation && PYTHONPATH=src python -m pytest -q\n  env:\n    PYTEST_ADDOPTS: -k evl_c6"])
g2("I37", "pytest -c custom ini with addopts -k evl_c6",
   ["run: cd implementation && PYTHONPATH=src python -m pytest -q -c ../ci/tc.ini --rootdir=."],
   {"ci/tc.ini": "[pytest]\naddopts = -k evl_c6\n"})
g2("I38", "pytest -o testpaths=tests/test_evl_c6*.py (selection through an ini override)",
   ["run: cd implementation && PYTHONPATH=src python -m pytest -q -o 'testpaths=tests/test_evl_c6_*.py'"])
g2("I39", "pytest --ignore-glob selecting only Track C tests",
   ["run: cd implementation && PYTHONPATH=src python -m pytest -q tests --ignore-glob='tests/test_[!e]*'"])
g2("I40", "pytest.main(['-k','evl_c6']) in a followed python script",
   ["run: cd implementation && PYTHONPATH=src python ../ci/run_tests.py"],
   {"ci/run_tests.py": 'import sys, pytest\nsys.exit(pytest.main(["-q", "-k", "evl_c6"]))\n'})
g2("I41", "Windows runner, backslash path",
   ["run: python implementation\\tools\\track_c_c6_acceptance.py\n  shell: pwsh"], runs_on="windows-latest")
g2("I42", "matrix value supplies the tool file name (expression: D3-c)",
   ["run: python ${{ matrix.tool }}\n  working-directory: implementation/tools"],
   job_extra="    strategy:\n      matrix:\n        tool: [track_c_c6_acceptance.py]\n", expect="NOT_FOUND(D3-c)")
g2("I43", "uv run --directory implementation/tools python <tool>",
   ["run: uv run --directory implementation/tools python track_c_c6_acceptance.py"])
g2("I44", "subshell ( cd implementation/tools; python <tool> )",
   ["run: ( cd implementation/tools; python track_c_c6_acceptance.py )"])
g2("I45", "python -c with runpy.run_path literal (control)",
   ["run: python -c \"import runpy; runpy.run_path('implementation/tools/track_c_c6_acceptance.py', run_name='__main__')\""])
g2("I46", "git -C implementation/tools ls-files | python? -> git -C then python via xargs (dynamic: D3-c)",
   ["run: cd implementation/tools && ls track_c_c6_acceptance.py | xargs python"])
g2("I47", "export then cd: cd implementation; cd tools (two cds on separate lines)",
   ["run: |\n    cd implementation\n    cd tools\n    python track_c_c6_acceptance.py"])
g2("I48", "cd inside if-block: if true; then cd implementation/tools; fi; python <tool>",
   ["run: if true; then cd implementation/tools; fi; python track_c_c6_acceptance.py"])
g2("I49", "heredoc to bash: bash <<EOF with cd/python inside",
   ["run: |\n    bash <<EOF\n    cd implementation/tools\n    python track_c_c6_acceptance.py\n    EOF"])
g2("I50", "python script with cwd kwarg via pathlib constant parts",
   ["run: python ci/run3.py"],
   {"ci/run3.py": 'import subprocess, sys\nfrom pathlib import Path\nsubprocess.run([sys.executable, "track_c_c6_acceptance.py"], cwd=Path("implementation") / "tools", check=True)\n'})

# job-level reusable-workflow callers (replace the step-based caller)
for v in V:
    if v["id"] == "I29":
        v["files"][WF] = "name: probe\non: [push]\njobs:\n  call:\n    uses: ./.github/workflows/x.yml\n"
    if v["id"] == "I30":
        v["files"][WF] = ("name: probe\non: [push]\njobs:\n  call:\n    uses: kco994553-star/Investment-System1/"
                          ".github/workflows/x.yml@feature/other\n")
        v["note"] = "x.yml is not in T; it is read from another branch of the same repository at run time"

# ICU-confusable substitutions that FPIA's NFKC-first order misses (from unicode/icu_vs_fpia.json)
for vid, desc, nm in [
    ("U27", "U+03F2 GREEK LUNATE SIGMA SYMBOL for c (ICU skeleton c; NFKC -> final sigma)", TC.replace("c", "\u03f2")),
    ("U28", "U+FE58 SMALL EM DASH for hyphens (ICU skeleton '-'; NFKC -> em dash)", TC.replace("-", "\ufe58")),
    ("U29", "U+FFE8 HALFWIDTH FORMS LIGHT VERTICAL for l (ICU skeleton l; NFKC -> U+2502)", TC.replace("l", "\uffe8")),
    ("U30", "U+02DB OGONEK for i (ICU skeleton i)", TC.replace("i", "\u02db")),
    ("U31", "U+037A GREEK YPOGEGRAMMENI for i (ICU skeleton i)", TC.replace("i", "\u037a")),
    ("U32", "single U+03F2 for the lone c in 'track' only", "tra\u03f2k-c-evl-validation"),
]:
    add(vid, "G1-confusable-icu", desc, {WF: ('name: "%s"\non: [push]\n%s' % (nm.encode("unicode_escape").decode(), JOB))},
        "FOUND", note=repr(nm))

# control characters (escaped in a double-quoted scalar)
for vid, desc, esc in [
    ("U33", "trailing DEL via \\x7f escape", "\\x7f"),
    ("U34", "trailing C1 control U+0080 via \\x80 escape", "\\x80"),
    ("U35", "trailing NEL via \\N escape", "\\N"),
    ("U36", "trailing U+001F via \\x1f escape (Python strip() treats it as whitespace)", "\\x1f"),
    ("U37", "trailing U+0001 via \\x01 escape", "\\x01"),
    ("U38", "trailing U+009F via \\x9f escape", "\\x9f"),
]:
    add(vid, "G1-control", desc, {WF: 'name: "%s%s"\non: [push]\n%s' % (TC, esc, JOB)}, "FOUND?")

g2("I51", "multi-line quoted argument: cd + python on a line whose quote closes on the next line",
   ["run: |\n    cd implementation/tools && python track_c_c6_acceptance.py \"arg\n    continued\""])
g2("I52", "CDPATH=implementation cd tools", ["run: CDPATH=implementation cd tools && python track_c_c6_acceptance.py"])
g2("I53", "cd with a glob: cd implementation/tool*", ["run: cd implementation/tool* && python track_c_c6_acceptance.py"])

g2("I54", "step env SCRIPT relative to the step working-directory + python \"$SCRIPT\" (shell variable: D3-c)",
   ["run: python \"$SCRIPT\"\n  working-directory: implementation/tools\n  env:\n    SCRIPT: track_c_c6_acceptance.py"],
   expect="NOT_FOUND(D3-c)")
g2("I55", "python -m <tree package> whose __main__ calls the tool by its full literal path (control)",
   ["run: cd implementation && PYTHONPATH=src python -m ci_probe2"],
   {"implementation/src/ci_probe2/__init__.py": "",
    "implementation/src/ci_probe2/__main__.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "tools/track_c_c6_acceptance.py"], check=True)\n'})
g2("I56", "PYTHONPATH=ci python -m runner (module only on PYTHONPATH) calling the tool by full literal path",
   ["run: PYTHONPATH=ci python -m runner"],
   {"ci/runner.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "implementation/tools/track_c_c6_acceptance.py"], check=True)\n'})
g2("I57", "reusable workflow with the literal tool path (control)",
   ["run: echo caller"],
   {".github/workflows/x.yml": "name: x\non: [workflow_call]\njobs:\n  inner:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python implementation/tools/track_c_c6_acceptance.py\n"})
for v in V:
    if v["id"] == "I57":
        v["files"][WF] = "name: probe\non: [push]\njobs:\n  call:\n    uses: ./.github/workflows/x.yml\n"

# ------------------------------------------------------------------------------------------------ resume round additions
# aliases / merge keys carrying the run text or the working-directory (G1 x G2)
add("Y31", "G1xG2", "run text via alias of an anchored env value", {
    WF: "name: probe\non: [push]\nenv:\n  R: &r python implementation/tools/track_c_c6_acceptance.py\n"
        "jobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: *r\n"}, "FOUND", run=True)
add("Y32", "G1xG2", "working-directory via alias (anchor on an env value) + bare tool name", {
    WF: "name: probe\non: [push]\nenv:\n  D: &d implementation/tools\n"
        "jobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python track_c_c6_acceptance.py\n        working-directory: *d\n"},
    "FOUND", run=True)
add("Y33", "G1xG2", "step mapping through a merge key (<<: {working-directory: ...}) + bare tool name", {
    WF: "name: probe\non: [push]\n"
        "jobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - <<: {working-directory: implementation/tools}\n        run: python track_c_c6_acceptance.py\n"},
    "FOUND", run=True)
add("Y34", "G1", "name via alias whose anchor is a job name defined earlier (name key placed after jobs)", {
    WF: "on: [push]\njobs:\n  check:\n    name: &n %s\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\nname: *n\n" % TC},
    "FOUND")
add("Y35", "G1", "deeply nested flow sequence (RecursionError in the loader) + Track C name", {
    WF: "name: %s\non: [push]\nenv:\n  X: %s%s\n%s" % (TC, "[" * 3000, "]" * 3000, JOB)}, "FOUND(fail-closed)")
add("Y36", "G1", "1 MB workflow (1000-line block scalar) with a benign name (loader cost; control NOT_FOUND)", {
    WF: "name: probe\non: [push]\nenv:\n  BIG: |\n%s%s" % (("    " + "x" * 1000 + "\n") * 1000, JOB)}, "NOT_FOUND")
add("Y37", "G1", "folded block scalar >- over two lines joining 'track-c-evl-' and 'validation' with no space? (folding inserts a space)", {
    WF: "name: >-\n  track-c-evl-\n  validation\non: [push]\n%s" % JOB}, "NOT_FOUND(GitHub shows 'track-c-evl- validation')")
add("Y38", "G1", "literal block |- with trailing spaces stripped by strip()", {
    WF: "name: |-\n  %s   \non: [push]\n%s" % (TC, JOB)}, "FOUND")
add("Y39", "G1", "single-quoted with escaped quote doubling and line folding", {
    WF: "name: 'track-c-evl-\n  validation'\non: [push]\n%s" % JOB}, "NOT_FOUND(folds to a space)")
add("Y40", "G1", "double-quoted with escaped line break (no space)", {
    WF: 'name: "track-c-evl-\\\n  validation"\non: [push]\n%s' % JOB}, "FOUND")
g2("I58", "find ... -exec python {} \\; (tool selected by a glob in find)",
   ["run: find implementation/tools -name 'track_c_c6*.py' -exec python {} \\;"])
g2("I59", "shell: python {0} with os.chdir + subprocess bare tool name",
   ["run: |\n    import os, subprocess, sys\n    os.chdir('implementation/tools')\n    subprocess.run([sys.executable, 'track_c_c6_acceptance.py'], check=True)\n  shell: python {0}"])
g2("I60", "python ${{ github.workspace }}/implementation/tools/<tool> (rooted argument, control)",
   ["run: python ${{ github.workspace }}/implementation/tools/track_c_c6_acceptance.py"])
g2("I61", "cd implementation && cd tools && python <tool> on one line",
   ["run: cd implementation && cd tools && python track_c_c6_acceptance.py"])
g2("I62", "symlink ci/tc.py -> ../implementation/tools/track_c_c6_acceptance.py run as python ci/tc.py",
   ["run: python ci/tc.py"], {"ci/tc.py": ("120000", "../implementation/tools/track_c_c6_acceptance.py")})
g2("I63", "symlinked directory ci/tools -> ../implementation/tools; cd ci/tools && python <tool>",
   ["run: cd ci/tools && python track_c_c6_acceptance.py"], {"ci/tools": ("120000", "../implementation/tools")})
g2("I64", "uses: ./ (root composite action action.yml at repository root)",
   ["uses: ./"], {"action.yml": "name: root\nruns:\n  using: composite\n  steps:\n    - run: cd implementation/tools && python track_c_c6_acceptance.py\n      shell: bash\n"})
g2("I65", "job-level defaults.run.working-directory via ${{ github.workspace }}",
   ["run: python track_c_c6_acceptance.py"],
   job_extra="    defaults:\n      run:\n        working-directory: ${{ github.workspace }}/implementation/tools\n")
g2("Y41", "working-directory given as a literal expression ${{ 'implementation/tools' }} + bare tool name",
   ["run: python track_c_c6_acceptance.py\n  working-directory: ${{ 'implementation/tools' }}"])
g2("Y42", "whole run command as one literal expression ${{ 'cd implementation/tools && python <tool>' }}",
   ["run: ${{ 'cd implementation/tools && python track_c_c6_acceptance.py' }}"])
g2("Y43", "run-name literal expression with the Track C name and a step running the tool by literal path (control for G2)",
   ["run: python implementation/tools/track_c_c6_acceptance.py"])

assert TOOL == tk.C6_PATH and TC == fd.parse_workflow(tk.workflow(["C6"]))["name"]

# S24V2: the round-2 end-to-end bypass (full CLI FPIA_PASS at the previous head): a blank-suffixed Track C
# name plus a workspace-rooted cd running the C6 tool.
add("S24V2", "G1xG2", "trailing U+2800 Track C name + cd ${{ github.workspace }}/implementation/tools && python <tool>", {
    WF: 'name: "%s\\u2800"\non:\n  pull_request:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n'
        '  validate:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n'
        '      - run: cd ${{ github.workspace }}/implementation/tools && PYTHONPATH=../src:.. python %s\n'
        % (TC, TOOL.rsplit("/", 1)[1])}, "FOUND")
# D3-e (open user decision): code from outside T is not analysed; recorded, never FOUND by itself
add("E01", "D3-e", "remote reusable workflow of another repository", {
    WF: "name: probe\non: [push]\njobs:\n  call:\n    uses: other-org/other-repo/.github/workflows/x.yml@v1\n"},
    "NOT_FOUND(D3-e)")
add("E02", "D3-e", "third-party action and a container image", {
    WF: wf(["uses: some-org/some-action@v2", "uses: docker://alpine:3"])}, "NOT_FOUND(D3-e)")

# round-2 classification (v2-adversarial out/v3/classification.json)
D1 = ["I01", "I02", "I03", "I05", "I06", "I08", "I09", "I15", "I16", "I19", "I20", "I29", "I31", "I32", "U27", "U28",
      "U29", "U30", "U31", "U32", "I51", "I65"]
D2 = ["Y27", "Y28", "Y29", "Y30", "U01", "U03", "U04", "U10", "U26", "F03", "I04", "I07", "I10", "I11", "I12", "I13",
      "I14", "I17", "I18", "I21", "I22", "I23", "I33", "I34", "I35", "I36", "I37", "I39", "I40", "I41", "I43", "I48",
      "U33", "U34", "U37", "U38", "I52", "I56", "I59", "Y41", "Y42"]
D3C = ["C03", "I24", "I25", "I26", "I28", "I42", "I50", "I54", "I58"]
D3E_SAME_REPOSITORY = ["I30"]          # the round-2 NEW_D3 candidate, same-repository part: FOUND fail-closed (H2)
D3E = ["E01", "E02"]
FOUND_REQUIRED = D1 + D2 + ["S24V2"] + D3E_SAME_REPOSITORY
assert len(D1) == 22 and len(D2) == 41 and len(D3C) == 9
# Observed fix-round-3 outcome of every variant (identical on the synthetic world and on the real tree
# acaf1b5 overlay). D3-c, pinned as current behaviour: all nine variants literally name a Track C file or
# a glob over one, so the mention rule catches them as a side effect - this is not a detection claim
# (dynamic_invocation_detection stays NOT_CLAIMED; a truly computed name stays undetected, S16). The
# round-2 "not a confusable" rows (U02, U07, U08, U09, U12) and the folded-space names Y37/Y39 are now
# FOUND by the substring identity keys (conservative); only the benign controls and D3-e stay NOT_FOUND.
NOT_FOUND_NOW = ["C00", "Y36", "E01", "E02"]
EXPECTED = {v["id"]: ("NOT_FOUND" if v["id"] in NOT_FOUND_NOW else "FOUND") for v in V}


# ---- overlay of a variant on the synthetic T0 (the audit's own static-phase arguments) --------------------
class _Overlay:
    """T0's tree plus the variant files (real git blob ids), read through the audit's sandbox."""

    def __init__(self, sb, base):
        self.sb, self.base, self.files, self.extra = sb, base, {}, {}

    def set(self, files):
        self.files, self.extra = {}, {}
        for p, v in files.items():
            mode, data = ("100644", v) if isinstance(v, (bytes, str)) else v
            data = data.encode() if isinstance(data, str) else data
            sha = fgit.blob_id(data)
            self.extra[sha] = data
            self.files[p] = fgit.Entry(mode, "blob", sha)

    def tree(self, rev):
        if rev == "VARIANT":
            t = dict(self.sb.tree(self.base))
            t.update(self.files)
            return t
        return self.sb.tree(rev)

    def blob(self, sha):
        return self.extra[sha] if sha in self.extra else self.sb.blob(sha)

    def __getattr__(self, name):
        return getattr(self.sb, name)


class Battery:
    def __init__(self, a):
        assert a.ref_status == "PASS" and a.static_findings == [], a.static_findings
        self.a, self.osb = a, _Overlay(a.sb, a.T)

    def run(self, files):
        a = self.a
        self.osb.set(files)
        info = {}
        av_applied = {p for p in a.av if any(a.v_applies.get(V) for V in a.Vs)}
        _, findings = fchk.complement_static(self.osb, "VARIANT", a.R, a.Vs, a.v_applies, a.proj, av_applied, a.tcm_all,
                                             a.config_names or [], set(a.result["integration_interference"]["config_dirs"]),
                                             fd.TRACK_C_WORKFLOW, None, info=info, av_all=set(a.av),
                                             repo_ids=a.repo_ids, verifier_self=a.verifier_self)
        return findings, info


@pytest.fixture(scope="module")
def battery(tmp_path_factory):
    w = tk.variant(tmp_path_factory.mktemp("fix3-battery"))
    return Battery(w.audit(w.c["T0"]))


def _outcome(battery, v):
    findings, info = battery.run(v["files"])
    spoof = [f for f in findings if f["id"] == "AC-32.spoof"]
    return ("FOUND" if spoof else "NOT_FOUND"), spoof, findings, info


@pytest.mark.parametrize("vid", [v["id"] for v in V])
def test_round2_variant_pinned(battery, vid):
    """Every round-2 variant (and S24V2, E01, E02) pinned with its component (AC-32.spoof) and status."""
    v = [x for x in V if x["id"] == vid][0]
    got, spoof, findings, info = _outcome(battery, v)
    expected = "FOUND" if vid in FOUND_REQUIRED else EXPECTED[vid]
    assert got == expected, (vid, v["desc"], spoof or findings)
    status = "INTEGRATION_INTERFERENCE_FOUND" if findings else "INTEGRATION_INTERFERENCE_NONE"
    if vid in FOUND_REQUIRED:
        assert status == "INTEGRATION_INTERFERENCE_FOUND"
        assert any(f["path"] in v["files"] for f in spoof), spoof
    wa = info["workflow_analysis"]
    assert wa["dynamic_invocation_detection"] == "NOT_CLAIMED" and wa["out_of_tree_code_analysis"] == "NOT_ANALYSED"
    assert info.get("not_run", []) == []


def test_round2_d1_d2_all_found(battery):
    """The 22 D1 and 41 D2 variants of the previous round (FPIA claimed or could cover them; NOT_FOUND at
    the previous head) and S24V2 are all FOUND, each by AC-32.spoof on the variant's workflow."""
    missed = []
    for v in V:
        if v["id"] in D1 + D2 + ["S24V2"]:
            got, spoof, _, _ = _outcome(battery, v)
            if got != "FOUND":
                missed.append(v["id"])
    assert missed == []


def test_d3c_pinned_as_current_behaviour(battery):
    """D3-c (open user decision) is not decided: nothing is claimed for dynamically constructed invocations
    (dynamic_invocation_detection NOT_CLAIMED); the variants whose text names a Track C file are caught by
    the mention rule (a side effect), the others stay NOT_FOUND."""
    for vid in D3C:
        v = [x for x in V if x["id"] == vid][0]
        got, _, _, info = _outcome(battery, v)
        assert got == EXPECTED[vid], vid
        assert info["workflow_analysis"]["dynamic_invocation_detection"] == "NOT_CLAIMED"
    assert fw.DYNAMIC_NON_CLAIM in fpia.NON_CLAIMS


def test_d3e_out_of_tree_recorded_not_decided(battery):
    """D3-e (open user decision): remote workflows of other repositories, third-party actions and container
    images are not analysed - recorded as out_of_tree_code_analysis NOT_ANALYSED, never FOUND by themselves
    and never listed as an approved non-claim; a same-repository remote workflow is FOUND fail-closed."""
    for vid, uses in (("E01", ["other-org/other-repo/.github/workflows/x.yml@v1"]),
                      ("E02", ["some-org/some-action@v2", "docker://alpine:3"])):
        v = [x for x in V if x["id"] == vid][0]
        got, _, findings, info = _outcome(battery, v)
        assert got == "NOT_FOUND" and findings == [], findings
        refs = info["workflow_analysis"]["out_of_tree_references"]
        assert sorted(r["uses"] for r in refs if r["workflow"] == WF) == sorted(uses), refs
    assert not any("D3-e" in x for x in fpia.NON_CLAIMS)
    v = [x for x in V if x["id"] == "I30"][0]
    got, spoof, _, _ = _outcome(battery, v)
    assert got == "FOUND" and any("same-repository remote workflow" in r for r in spoof[0]["reasons"]), spoof


def test_s24v2_end_to_end_component_status(tmp_path):
    """S24V2 (previous round: full CLI FPIA_PASS / INTEGRATION_INTERFERENCE_NONE) now gives
    INTEGRATION_INTERFERENCE_FOUND and FPIA_FAIL, and the summary names the open non-claims."""
    w = tk.variant(tmp_path)
    v = [x for x in V if x["id"] == "S24V2"][0]
    T2 = w.git.change(w.c["T0"], v["files"], "S24V2")
    r = w.fpia(T2, w.register(w.c["R0"], [w.c["V0"]], [T2]), options={"lanes": []})
    assert r["statuses"]["integration_interference"] == "INTEGRATION_INTERFERENCE_FOUND"
    assert r["fpia"]["status"] == "FPIA_FAIL"
    spoof = [f for f in r["integration_interference"]["static_findings"] if f["id"] == "AC-32.spoof"]
    assert [f["path"] for f in spoof] == [WF]
    reasons = " ".join(spoof[0]["reasons"])
    assert "claims the Track C identity" in reasons and "mentions Track C scope" in reasons
    assert "dynamic_invocation_detection NOT_CLAIMED (D3-c)" in r["summary"]
    assert "out_of_tree_code_analysis NOT_ANALYSED (D3-e)" in r["summary"]     # actions/checkout


# ---- H1: identity keys, constant-expression folding ----------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("${{ 'a''b' }}", "a'b"),
    ("x-${{ 'evl' }}-y", "x-evl-y"),
    ("${{ format('track-c-{0}-{1}', 'evl', format('{0}', 'validation')) }}", "track-c-evl-validation"),
    ("${{ format('{{0}}{0}', true) }}", "{0}true"),
    ("${{ null }}${{ 7 }}", "7"),
    ("${{  'a'  }}", "a"),
])
def test_constant_expressions_fold(text, expected):
    assert fw.fold_expressions(text) == (expected, [])


@pytest.mark.parametrize("text", ["${{ github.ref }}", "${{ inputs.name }}", "${{ format('{1}', 'a') }}",
                                  "${{ toJSON('a') }}", "${{ 'a' || 'b' }}", "${{ 'unterminated }}", "${{ 1.5 }}"])
def test_non_foldable_expressions_reported(text):
    folded, bad = fw.fold_expressions(text)
    assert bad, text


@pytest.mark.parametrize("name", [
    "track-c-evl-validation-extended", "[ci] TRACK C EVL VALIDATION", "track c evl validation",
    "track-c-evl-validation\u2800", "track-c-evl-validation\U0001D159", "track-c-evl-validation\ufff9",
    "track-c-evl-validation\U00016FE4", "track-c-evl-validation\x7f", "track-c-evl-validation\x01",
    "track-c-evl-val\u0131\u0307dation", "tra\u03f2k-c-evl-validation", "track\ufe58c\ufe58evl-validation",
    "track-c-ev\uffe8-validation", "track-c-evl-val\u02dbdation", "track-c-evl-val\u037adation",
    "track\u00adc\u00adevl\u00advalidation", "track-c-evl\u2800-validation", "\u0130track-c-evl-validation",
])
def test_identity_key_substring_claims(name):
    assert fw.identity_claim(name, ["track-c-evl-validation"]), name


@pytest.mark.parametrize("name", ["track-c-fpia", "web-mvp-validation", "track-c-evl", "evl-validation",
                                  "codex-integration-readiness"])
def test_identity_key_non_claims(name):
    assert fw.identity_claim(name, ["track-c-evl-validation"]) is None


def test_skeleton_applied_before_nfkc():
    """D1 (round 2): U+03F2, U+FE58, U+FFE8, U+02DB, U+037A are ICU 74.2 confusables lost when NFKC runs
    before the skeleton; the table now keeps NFKC-unstable sources."""
    for ch, proto in (("\u03f2", "c"), ("\ufe58", "-"), ("\uffe8", "l"), ("\u02db", "i"), ("\u037a", "i")):
        assert fw.skeleton(ch) == proto, hex(ord(ch))
    assert len(fw._PROTO) == 1788 and fw.CONFUSABLE_SOURCE["runtime_download"] is False


@pytest.mark.parametrize("line", ["name: ${{ github.event.pull_request.title }}", "run-name: deploy ${{ github.actor }}",
                                  "name: ${{ format('{0}', inputs.x) }}"])
def test_non_foldable_name_is_found_fail_closed(battery, line):
    text = "%s\non: [push]\n%s" % (line, JOB)
    got, spoof, _, _ = _outcome(battery, {"files": {WF: text}})
    assert got == "FOUND" and any("identity not statically determinable" in r for r in spoof[0]["reasons"]), spoof


def test_identity_claim_never_attributed(battery):
    """A V-carried workflow is attributable only without an identity claim (unchanged attribution)."""
    findings, _ = battery.run({WF: "name: x-${{ 'track-c-evl' }}-validation\non: [push]\n" + JOB})
    assert [f["path"] for f in findings if f["id"] == "AC-32.spoof"] == [WF]


# ---- H2: the mention set and the over-approximation ---------------------------------------------------
def test_mention_set_from_authenticated_references(battery):
    _, info = battery.run({})
    m = info["workflow_analysis"]["mention_set"]
    assert tk.C6_PATH.rsplit("/", 1)[1] in m["tool"] and tk.C6_PATH.rsplit("/", 1)[1][:-3] in m["tool"]
    assert "test_evl_c6_basic" in m["test"] and "investment_system.evl.walkforward" in m["module"]
    assert "verify_v2_test.py" in m["av"] and fd.TRACK_C_WORKFLOW in m["workflow"]
    # nothing from the complement: a foreign module is not a Track C name
    assert not any("rig" in x for k in m for x in m[k])


@pytest.mark.parametrize("text", [
    "cd ${{ github.workspace }}/implementation/tools && python %s",
    "cd \"$GITHUB_WORKSPACE/implementation/tools\" && python %s",
    "bash -ec 'cd implementation/tools && python %s'",
    "timeout 600 nice -n 5 env -C implementation/tools python %s",
    "python implementation\\tools\\%s",
    "python Implementation/Tools/%s",
    "echo %s",
])
def test_mention_detected_whatever_surrounds_it(battery, text):
    got, spoof, _, _ = _outcome(battery, {"files": {WF: wf(["run: " + text % TOOL.rsplit("/", 1)[1]])}})
    assert got == "FOUND" and any("mentions Track C scope" in r for r in spoof[0]["reasons"]), spoof


@pytest.mark.parametrize("files", [
    {WF: wf(["run: ./ci/x"]), "ci/x": "cd implementation/tools; python %s\n" % TOOL.rsplit("/", 1)[1]},
    {WF: wf(["run: make all"]), "sub/dir/rules.mk": "all:\n\tpython %s\n" % TOOL},
    {WF: wf(["run: tox"]), "tox.ini": "[testenv]\ncommands = python %s\n" % TOOL},
    {WF: wf(["run: PYTHONPATH=ci python -m deep.mod"]), "ci/deep/mod.py": "import os\nos.system('python %s')\n" % TOOL},
    {WF: wf(["run: python -m pytest @ci/sel.txt"]), "ci/sel.txt": "-k evl_c6\n"},
    {WF: wf(["uses: ./.github/actions/n"]), ".github/actions/n/action.yml": "runs:\n  using: node20\n  main: d/i.js\n",
     ".github/actions/n/d/i.js": "require('child_process').execSync('python %s')\n" % TOOL},
])
def test_reached_files_scanned(battery, files):
    got, spoof, _, _ = _outcome(battery, {"files": files})
    assert got == "FOUND", files
    assert spoof[0].get("reached"), spoof


def test_data_files_and_whole_suite_are_not_spoofing(battery):
    """A Track C name inside a data file a workflow merely names is not code (D3-c territory); pytest over
    the whole suite stays a note."""
    files = {WF: wf(["run: cat docs/notes.md && cd implementation && python -m pytest -q"]),
             "docs/notes.md": "see %s\n" % TOOL}
    got, _, findings, info = _outcome(battery, {"files": files})
    assert got == "NOT_FOUND", findings
    notes = [n for n in info["workflow_analysis"]["notes"] if n["path"] == WF]
    assert notes and any("whole pytest suite" in x for x in notes[0]["notes"])


def test_resolver_output_is_evidence_only(battery):
    """The fix-round-2 resolver result is kept as evidence (resolver_reasons) next to the verdict basis."""
    v = [x for x in V if x["id"] == "C02"][0]
    _, spoof, _, _ = _outcome(battery, v)
    assert spoof[0]["resolver_reasons"] and spoof[0]["reasons"]
    assert all(r not in spoof[0]["reasons"] for r in spoof[0]["resolver_reasons"])


def test_verifier_own_files_are_self_placement_but_a_modified_copy_is_scanned(battery):
    """FPIA's own files byte-identical to the running verifier are the auditor itself (AC-41); one changed
    byte makes the file ordinary complement content that is scanned."""
    src = (tk.TOOLS_DIR / "integration" / "track_c_fpia.py").read_bytes()
    runner = wf(["run: python implementation/tools/integration/track_c_fpia.py --help"])
    findings, info = battery.run({WF: runner, "implementation/tools/integration/track_c_fpia.py": src})
    assert [f for f in findings if f["id"] == "AC-32.spoof"] == []
    assert {"workflow": WF, "path": "implementation/tools/integration/track_c_fpia.py",
            "blob": fgit.blob_id(src)} in info["workflow_analysis"]["self_placement"]
    changed = src + ("\n# run %s\n" % TOOL).encode()
    findings, _ = battery.run({WF: runner, "implementation/tools/integration/track_c_fpia.py": changed})
    assert [f["path"] for f in findings if f["id"] == "AC-32.spoof"] == [WF]


# ---- H3: environment independence -------------------------------------------------------------------------
DRIVER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from tools.integration import track_c_fpia as fpia
a = json.loads(sys.argv[2])
d = fpia.run_fpia(a["repo"], a["T"], a["G"], a["cdr"], work_dir=a.get("work"),
                  options={"authority_remote": a["repo"], "require_clean_verifier": False,
                           "lanes": ["R", "R-verbatim", "T", "PI"]})
r = d["result"]
plugins = [f for f in r["integration_interference"].get("findings", []) if f.get("id") == "AC-28"]
print(json.dumps({"sha": d["result_sha256"], "fpia": r["fpia"]["status"], "statuses": r["statuses"],
                  "plugins": len(plugins), "work": d["run"]["work_dir"], "prefix": sys.prefix}))
"""


def _drive(py, w, tmp_path, name, env_extra=None, work=True):
    arg = {"repo": str(w.repo), "T": w.c["T0"], "G": w.c["G0"], "cdr": tk.TEST_CDR}
    if work:
        arg["work"] = str(tmp_path / (name + "-work"))
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "PYTHONHOME")}
    env.update(env_extra or {})
    proc = subprocess.run([str(py), "-c", DRIVER, str(tk.IMPL_DIR), json.dumps(arg)], capture_output=True, text=True,
                          env=env, cwd=str(tk.IMPL_DIR))
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout.strip().split("\n")[-1])


def test_symlinked_venv_tmpdir_and_user_give_same_verdict_and_sha(tmp_path):
    """Round 2 G5: an interpreter reached through a symlinked venv path gave 360 'unexpected pytest
    plugin' findings, and a work directory under a symlinked TMPDIR broke node-id equivalence and the v2
    replay; pytest's basetemp carried the OS user name. Same T, same verifier -> same verdict and sha."""
    from tests.test_integration_fpia_fix2 import _clone_interpreter
    w = tk.base_world()
    venv = tmp_path / "real" / "venv"
    py = _clone_interpreter(venv)
    (tmp_path / "link").symlink_to(tmp_path / "real")
    real_tmp = tmp_path / "tmp-real"
    real_tmp.mkdir()
    (tmp_path / "tmp-link").symlink_to(real_tmp)
    base = _drive(py, w, tmp_path, "base")
    linked = _drive(tmp_path / "link" / "venv" / "bin" / "python", w, tmp_path, "venvlink")
    # the default work directory (tempfile.mkdtemp) under TMPDIR given as the real directory vs as a symlink
    # to it (TMPDIR is set in both: its presence is disclosed by name in runtime_provenance.ignored_parent_env)
    tmpreal = _drive(py, w, tmp_path, "tmpreal", {"TMPDIR": str(real_tmp)}, work=False)
    tmpdir = _drive(py, w, tmp_path, "tmplink", {"TMPDIR": str(tmp_path / "tmp-link")}, work=False)
    user = _drive(py, w, tmp_path, "user", {"USER": "fpia-other-user", "LOGNAME": "fpia-other-user"})
    assert base["statuses"]["runtime_provenance"] == "PASS", base                # a verified runtime
    assert base["statuses"]["integration_interference"] != "INTEGRATION_INTERFERENCE_FOUND", base
    assert base["plugins"] == 0 and linked["plugins"] == 0, (base, linked)
    assert tmpdir["work"].startswith(os.path.realpath(str(real_tmp)))
    for ref, other in ((base, linked), (base, user), (tmpreal, tmpdir), (base, tmpdir)):
        assert other["fpia"] == ref["fpia"] and other["statuses"] == ref["statuses"], (ref, other)
    assert linked["sha"] == base["sha"] and user["sha"] == base["sha"], (base, linked, user)
    assert tmpdir["sha"] == tmpreal["sha"], (tmpreal, tmpdir)


def test_pytest_basetemp_user_normalised():
    """pytest's basetemp of FPIA's own child runs (under the work directory) carries the OS user name
    (root locally, runner on GitHub): written as pytest-of-<user>; other paths are left as they are."""
    a = fpia.scrub({"argv": ["/x/exec/runs/1/tmp/pytest-of-root/pytest-0/t0/0.json"]}, "/x")
    b = fpia.scrub({"argv": ["/x/exec/runs/1/tmp/pytest-of-runner/pytest-0/t0/0.json"]}, "/x")
    assert a == b == {"argv": ["<work>/exec/runs/1/tmp/pytest-of-<user>/pytest-0/t0/0.json"]}
    assert fpia.normalise_work(b"/w/x/pytest-of-runner/p", "/w") == b"<work>/x/pytest-of-<user>/p"
    assert fpia.scrub("/tmp/pytest-of-root/remote.git", "/x") == "/tmp/pytest-of-root/remote.git"


def test_plugin_findings_compare_realpath_to_realpath(tmp_path):
    """A pytest reported through a symlinked directory is still pytest's own plugin."""
    real = tmp_path / "site"
    (real / "_pytest").mkdir(parents=True)
    (real / "pytest").mkdir()
    (real / "_pytest" / "x.py").write_text("")
    (real / "pytest" / "__init__.py").write_text("")
    (tmp_path / "linked").symlink_to(real)
    session = {"label": "s", "pytest_file": str(tmp_path / "linked" / "pytest" / "__init__.py"),
               "plugins": [{"name": "x", "file": str(real / "_pytest" / "x.py")}]}
    a = fpia.Audit.__new__(fpia.Audit)
    assert a.plugin_findings(session, tmp_path / "root") == []


# ---- H4: output and verifier ----------------------------------------------------------------------------
def _written(w, tmp_path, name):
    out = tmp_path / name / "fpia.json"
    out.parent.mkdir(parents=True)
    d = w.fpia(w.c["T0"], options={"lanes": ["T-frozen"]}, out=str(out), doc=True, work=tmp_path / ("w" + name))
    return out, d


def test_verify_rejects_duplicate_keys_and_non_basename_side_files(tmp_path, capsys):
    w = tk.base_world()
    out, d = _written(w, tmp_path, "a")
    assert fpia.verify_output(str(out), d["result_sha256"])[0] == "VERIFIED"
    text = out.read_text(encoding="utf-8")
    # a duplicate top-level key: a first-wins reader would see another result
    dup = tmp_path / "dup.json"
    dup.write_text(text.rstrip().rstrip("}") + ', "result": {"fpia": {"status": "FPIA_PASS"}}}\n', encoding="utf-8")
    st, rep = fpia.verify_output(str(dup))
    assert st == "MISMATCH" and any("duplicate" in json.dumps(c) for c in rep["checks"]), rep
    assert fpia.main(["--verify-output", str(dup)]) == 1
    # a side-file name that leaves the side-file directory is never read
    secret = tmp_path / "outside.txt"
    secret.write_text("x\n")
    doc = json.loads(text)
    step = [s for s in doc["result"]["frozen_tools_on_T"]["steps"] if s.get("verbatim")][0]
    step["verbatim"]["stdout"].update(file="../../outside.txt", sha256=hashlib.sha256(b"x\n").hexdigest(), bytes=2)
    doc["result_sha256"] = fpia.sha256(fpia.canonical_bytes(doc["result"]))
    out.write_text(json.dumps(doc), encoding="utf-8")
    st, rep = fpia.verify_output(str(out))
    assert st == "MISMATCH" and any("plain basename" in c["check"] for c in rep["checks"]), rep
    capsys.readouterr()


def test_run_section_hash_recorded_printed_and_checked(tmp_path, capsys):
    w = tk.base_world()
    out, d = _written(w, tmp_path, "r")
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["run_sha256"] == fpia.run_sha256(doc) == d["run_sha256"]
    assert "run_sha256" not in json.dumps(doc["result"])                       # not part of result_sha256
    capsys.readouterr()
    assert fpia.main(["--verify-output", str(out)]) == 0
    lines = capsys.readouterr().out.strip().split("\n")
    assert lines[-1] == "fpia-output: VERIFIED" and lines[-2].startswith("run_sha256: " + doc["run_sha256"])
    doc["run"]["authority_transport"]["values_recorded"] = True                 # tamper the run section
    out.write_text(json.dumps(doc), encoding="utf-8")
    st, rep = fpia.verify_output(str(out), d["result_sha256"])
    assert st == "MISMATCH" and rep["run_sha256"] != doc["run_sha256"]


ASCII_ENV = {"LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0", "PYTHONIOENCODING": ""}


def test_utf8_whatever_the_locale(tmp_path):
    """Round 2: under an ASCII locale the verifier said NOT_RUN on a genuine file and the writer crashed."""
    w = tk.base_world()
    out = tmp_path / "o" / "fpia.json"
    out.parent.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("LC_")}
    env.update(ASCII_ENV)
    code = ("import json, sys, locale; sys.path.insert(0, sys.argv[1]); from tools.integration import track_c_fpia as f;"
            "assert locale.getpreferredencoding(False).lower() in ('ascii', 'ansi_x3.4-1968'), locale.getpreferredencoding(False);"
            "a = json.loads(sys.argv[2]);"
            "d = f.run_fpia(a['repo'], a['T'], a['G'], a['cdr'], out=a['out'], work_dir=a['work'],"
            " options={'authority_remote': a['repo'], 'require_clean_verifier': False, 'lanes': ['T-frozen']});"
            "print(d['result_sha256'])")
    arg = {"repo": str(w.repo), "T": w.c["T0"], "G": w.c["G0"], "cdr": tk.TEST_CDR, "out": str(out),
           "work": str(tmp_path / "w")}
    proc = subprocess.run([sys.executable, "-c", code, str(tk.IMPL_DIR), json.dumps(arg)], capture_output=True,
                          text=True, env=env, cwd=str(tk.IMPL_DIR))
    assert proc.returncode == 0, proc.stderr[-2000:]
    raw = out.read_bytes()
    assert any(b > 127 for b in raw)                                          # non-ASCII content was written
    sha = proc.stdout.strip().split("\n")[-1]
    proc = subprocess.run([sys.executable, str(tk.TOOLS_DIR / "integration" / "track_c_fpia.py"), "--verify-output",
                           str(out), "--expect-result-sha256", sha], capture_output=True, env=env, cwd=str(tk.IMPL_DIR))
    assert proc.returncode == 0 and proc.stdout.decode("utf-8").strip().endswith("fpia-output: VERIFIED"), proc.stderr[-2000:]


def test_out_directory_preflight(tmp_path):
    """Round 2: an --out under a missing directory crashed after the full audit and left the work dir."""
    w = tk.base_world()
    missing = tmp_path / "missing" / "fpia.json"
    d = fpia.run_fpia(str(w.repo), w.c["T0"], w.c["G0"], tk.TEST_CDR, out=str(missing),
                      work_dir=str(tmp_path / "w-missing"), options={"authority_remote": str(w.repo),
                                                                     "require_clean_verifier": False})
    assert d["result"]["fpia"]["status"] == "FPIA_NOT_RUN" and "does not exist" in d["result"]["fpia"]["reasons"][0]
    assert not missing.parent.exists() and not (tmp_path / "w-missing").exists()
    assert fpia.main(["--repo", str(w.repo), "--tree", w.c["T0"], "--register-commit", w.c["G0"], "--cdr",
                      tk.TEST_CDR, "--out", str(missing)]) == 2
    ro = tmp_path / "ro"
    ro.mkdir()
    os.chmod(ro, 0o500)
    try:
        if os.access(str(ro), os.W_OK):            # privileged user: the permission bit does not bind
            assert fpia.output_preflight(str(ro / "fpia.json")) is None
        else:
            assert "not writable" in fpia.output_preflight(str(ro / "fpia.json"))
    finally:
        os.chmod(ro, 0o700)


# ---- H5: fetch status lines split on LF only ---------------------------------------------------------------
@pytest.mark.parametrize("sep", ["\u2028", "\u2029", "\u0085"])
def test_rejected_ref_names_with_unicode_line_separators(sep):
    line = " ! [rejected]        a%sb       -> refs/fpia/src/heads/a%sb  (non-fast-forward)" % (sep, sep)
    assert fgit.rejected_lines("From x\n" + line + "\n") == [line.strip()]
    assert fgit.rejected_lines(" * [new branch]      a%sb -> refs/fpia/src/heads/a%sb\n" % (sep, sep)) == []


def test_ls_remote_ref_names_with_unicode_line_separators(tmp_path):
    w = tk.variant(tmp_path)
    w.git.ref("refs/heads/odd\u2028name", w.c["T0"])
    sb = fgit.Sandbox(tmp_path / "sb")
    refs = sb.ls_remote(str(w.repo), "refs/heads/odd*")
    assert refs == {"refs/heads/odd\u2028name": w.c["T0"]}


# ---- H6: AC-04 counts every Track C-namespace path at T ----------------------------------------------------
def test_ac04_counts_track_c_namespace_paths_not_in_r(tmp_path):
    w = tk.variant(tmp_path)
    K = w.c["K"]
    X = w.git.change(K, {"implementation/src/investment_system/evl/not_in_r.py": "X = 1\n"}, "Track C-namespace file only")
    w.git.ref("refs/heads/ns-only", X)
    r = w.fpia(X, w.register(w.c["R0"], [], [X]), options={"lanes": []})
    c = [x for x in r["authority"]["checks"] if x["id"] == "AC-04" and x["status"] == "FAIL"]
    assert len(c) == 1 and c[0]["case"] == "R_ABSENT_TRACK_C_NAMESPACE_PATHS_PRESENT", c
    assert "not integrated" not in c[0]["detail"] and c[0]["track_c_paths_present_at_T"] == 1
    assert c[0]["track_c_paths_not_in_R_present_at_T"] == 1 and c[0]["track_c_paths_of_R_present_at_T"] == 0
    assert r["statuses"]["authority"] == "FAIL" and r["fpia"]["status"] == "FPIA_FAIL"


# ---- H7: verifier provenance lists every file under tools/integration --------------------------------------
def test_verifier_provenance_lists_vendored_files(tmp_path):
    prov = fpia.verifier_provenance(frun.HERE, tmp_path)
    files = prov["files"]
    vendored = sorted(p for p in files if p.startswith("_vendor/"))
    assert "_vendor/yaml/__init__.py" in vendored and "track_c_fpia.py" in files
    on_disk = sorted(p.relative_to(frun.HERE).as_posix() for p in frun.HERE.rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo"))
    assert sorted(files) == on_disk
    assert files["_vendor/yaml/__init__.py"] == fgit.blob_id((frun.HERE / "_vendor" / "yaml" / "__init__.py").read_bytes())
