# -*- coding: utf-8 -*-
"""v2-adversarial variant battery. Each variant: id, group, desc, files {path: text|bytes|(mode, data)},
expect (what a correct AC-32.spoof should report: FOUND / NOT_FOUND / NOTE), and, for G2 variants, the
run steps the local bash emulation executes (ground truth: does Track C code actually run?)."""

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
    ("U27", "U+03F2 GREEK LUNATE SIGMA SYMBOL for c (ICU skeleton c; NFKC -> final sigma)", TC.replace("c", "ϲ")),
    ("U28", "U+FE58 SMALL EM DASH for hyphens (ICU skeleton '-'; NFKC -> em dash)", TC.replace("-", "﹘")),
    ("U29", "U+FFE8 HALFWIDTH FORMS LIGHT VERTICAL for l (ICU skeleton l; NFKC -> U+2502)", TC.replace("l", "￨")),
    ("U30", "U+02DB OGONEK for i (ICU skeleton i)", TC.replace("i", "˛")),
    ("U31", "U+037A GREEK YPOGEGRAMMENI for i (ICU skeleton i)", TC.replace("i", "ͺ")),
    ("U32", "single U+03F2 for the lone c in 'track' only", "traϲk-c-evl-validation"),
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
g2("I58", "find ... -exec python {} \; (tool selected by a glob in find)",
   ["run: find implementation/tools -name 'track_c_c6*.py' -exec python {} \;"])
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
