"""G4 probes against the unmodified 523e702 CLI (--verify-output and --out handling).
Base: a copy of v2-real's complete, VERIFIED FPIA output of acaf1b5 at 523e702 (read-only source)."""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
W = HERE.parent
PY = str(W / "venv" / "bin" / "python")
CLI = str(W / "repo" / "implementation" / "tools" / "integration" / "track_c_fpia.py")
SRC = Path("/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real/out/fpia_c1_acaf1b5_A.json")
CASES = HERE / "cases"
if CASES.exists():
    shutil.rmtree(CASES)
CASES.mkdir()
sys.path.insert(0, str(W / "repo" / "implementation" / "tools" / "integration"))
import track_c_fpia as F  # noqa  (for canonical_bytes only)
base_doc = json.loads(SRC.read_text(encoding="utf-8"))
ANCHOR = base_doc["result_sha256"]
out = {"base": str(SRC), "base_result_sha256": ANCHOR, "cases": {}}


def mk(name, doc_text=None, doc=None):
    d = CASES / name
    d.mkdir()
    shutil.copytree(str(SRC) + ".verbatim", d / "fpia.json.verbatim")
    if doc is not None:
        doc_text = json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    (d / "fpia.json").write_text(doc_text if doc_text is not None else SRC.read_text(encoding="utf-8"), encoding="utf-8")
    return d / "fpia.json"


def verify(p, anchor=ANCHOR, env=None):
    args = [PY, CLI, "--verify-output", str(p)] + (["--expect-result-sha256", anchor] if anchor else [])
    r = subprocess.run(args, capture_output=True, env=dict(os.environ, **(env or {})))
    last = [l for l in r.stdout.decode("utf-8", "replace").splitlines() if l.startswith("fpia-output:")]
    rep = None
    try:
        rep = json.loads(r.stdout.decode("utf-8", "replace").rsplit("fpia-output:", 1)[0])
    except Exception:  # noqa
        pass
    bad = [c["check"] for c in (rep or {}).get("checks", []) if c["status"] != "PASS"]
    return {"rc": r.returncode, "status_line": last[-1] if last else None, "failed_checks": bad,
            "error": (rep or {}).get("error"), "stderr_tail": r.stderr.decode("utf-8", "replace")[-300:]}


def case(name, expect, observed, note=""):
    out["cases"][name] = {"expect": expect, "observed": observed, "note": note}


# B0 genuine copy
p = mk("B0_genuine")
case("B0_genuine", "VERIFIED (with and without anchor)", {"anchor": verify(p), "no_anchor": verify(p, None)})

# T1 run section tampered (F2 transport disclosure, path tokens, argv, fetch log) - outside result_sha256
d = json.loads(SRC.read_text(encoding="utf-8"))
d["run"]["authority_transport"]["queries"] = []
d["run"]["authority_transport"]["env_names_passed_to_network_git"] = []
d["run"]["canonical_ref_query"] = None
d["run"]["path_tokens"] = {}
d["run"]["fetches"] = []
d["run"]["argv"] = [a.replace("acaf1b5a82859ac2750a130ebe88f8b4d272ac66", "b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565") for a in d["run"]["argv"]]
d["run"]["verbatim_raw"] = {}
p = mk("T1_run_section", doc=d)
case("T1_run_section", "MISMATCH or a declared non-verifiable run.* scope (only run.verbatim_raw is declared)",
     {"anchor": verify(p)}, "run.authority_transport (F2), run.canonical_ref_query, run.path_tokens (G5), run.fetches, run.argv emptied/changed")

# T2 duplicate top-level keys: a fake 'result' first, the genuine one last (Python json keeps the last)
fake = json.loads(json.dumps(base_doc["result"]))
fake["fpia"] = {"status": "FPIA_FAIL", "reasons": ["integration_interference INTEGRATION_INTERFERENCE_FOUND"]}
fake["summary"] = "FPIA_FAIL | fake first copy"
genuine_text = SRC.read_text(encoding="utf-8")
assert genuine_text.startswith("{\n")
dup_text = '{\n "result": ' + json.dumps(fake, sort_keys=True, ensure_ascii=False) + ',\n' + genuine_text[2:]
p = mk("T2_duplicate_result_key", doc_text=dup_text)
first = json.loads(dup_text, object_pairs_hook=lambda kv: {k: v for k, v in reversed(kv)})
case("T2_duplicate_result_key", "MISMATCH/NOT_RUN (non-canonical JSON with two 'result' members)",
     {"anchor": verify(p), "first_wins_reader_sees": first["result"]["fpia"]["status"],
      "last_wins_reader_sees": json.loads(dup_text)["result"]["fpia"]["status"]})

# T3 consistent re-hash: side file changed, its sha/bytes in result updated, result_sha256 recomputed
d = json.loads(SRC.read_text(encoding="utf-8"))
p = mk("T3_consistent_rehash", doc=d)
vd = p.parent / "fpia.json.verbatim"
step = [s for s in d["result"]["frozen_tools_on_T"]["steps"] if (s.get("verbatim") or {}).get("stdout")][0]
fn = step["verbatim"]["stdout"]["file"]
data = b"TAMPERED STREAM\n"
(vd / fn).write_bytes(data)
step["verbatim"]["stdout"].update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
d["result_sha256"] = hashlib.sha256(F.canonical_bytes(d["result"])).hexdigest()
p.write_text(json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
case("T3_consistent_rehash", "VERIFIED without anchor (declared non-verifiable); MISMATCH with the external anchor",
     {"no_anchor": verify(p, None), "anchor": verify(p)})

# T4 hidden extra file in the side-file directory
p = mk("T4_hidden_extra")
(p.parent / "fpia.json.verbatim" / ".hidden").write_text("x")
case("T4_hidden_extra", "MISMATCH (unreferenced file)", {"anchor": verify(p)})

# T5 side file replaced by a symlink to an identical copy outside the directory
p = mk("T5_symlink_side_file")
vd = p.parent / "fpia.json.verbatim"
name = sorted(os.listdir(vd))[0]
outside = p.parent / ("outside-" + name)
shutil.copyfile(vd / name, outside)
(vd / name).unlink()
(vd / name).symlink_to(outside)
case("T5_symlink_side_file", "VERIFIED is acceptable (identical bytes)", {"anchor": verify(p)})

# T6 verifier under a non-UTF-8 (ASCII) locale with locale coercion and UTF-8 mode disabled
p = mk("T6_ascii_locale")
case("T6_ascii_locale", "VERIFIED (the file is genuine)",
     {"anchor": verify(p, env={"LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"}),
      "same_with_utf8": verify(p)})

# CLI --out handling (fast: a 40-hex --tree that does not exist gives a quick FPIA_NOT_RUN)
NOPE = "0" * 39 + "1"
REPO = str(W / "repo")
TMP = HERE / "tmp"
TMP.mkdir(exist_ok=True)


def cli(outp, env=None, extra=()):
    e = dict(os.environ, TMPDIR=str(TMP), **(env or {}))
    r = subprocess.run([PY, CLI, "--repo", REPO, "--tree", NOPE, "--register-commit",
                        "f36292689eabf7ba3700d57a949fa0fb7343a2c6", "--cdr", "CDR-014", "--out", str(outp)] + list(extra),
                       capture_output=True, env=e, cwd=REPO)
    return {"rc": r.returncode, "stdout_tail": r.stdout.decode("utf-8", "replace")[-200:],
            "stderr_tail": r.stderr.decode("utf-8", "replace")[-400:], "written": Path(outp).exists()}


c = CASES / "C1_parent_missing"
c.mkdir()
case("C1_out_parent_missing", "refused up front with FPIA_NOT_RUN exit 2 (G4: nothing runs when the output cannot be written)",
     cli(c / "no" / "such" / "dir" / "fpia.json"),
     "the audit runs to the end first; with a real tree that is 25-45 min of work before the crash")
c = CASES / "C2_ascii_locale"
c.mkdir()
case("C2_cli_ascii_locale", "a result file written (UTF-8) and exit 2 (FPIA_NOT_RUN)",
     cli(c / "fpia.json", env={"LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"}))
c = CASES / "C3_dangling_symlink"
c.mkdir()
target = HERE / "elsewhere" / "planted.json"
(HERE / "elsewhere").mkdir(exist_ok=True)
if target.exists():
    target.unlink()
(c / "fpia.json").symlink_to(target)
r = cli(c / "fpia.json")
r["target_written"] = target.exists()
case("C3_out_dangling_symlink", "refused, or written at --out itself", r)
c = CASES / "C4_existing_empty_file"
c.mkdir()
(c / "fpia.json").write_text("")
case("C4_out_existing_empty_file", "accepted (empty file)", cli(c / "fpia.json"))
c = CASES / "C5_nonempty"
c.mkdir()
(c / "fpia.json").write_text("{}")
case("C5_out_nonempty", "refused, exit 2, nothing written", cli(c / "fpia.json"))
print(json.dumps(out, indent=1, ensure_ascii=False))
