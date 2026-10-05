# GIE-014 · CDR-014 hardened Frozen Projection Identity Audit (FPIA): implementation, fix rounds, verification · 2026-10-04

**Authority: none.** Integration evidence by the Primary Integration Writer under CDR-014. The FPIA is an additive PIW tool on a PIW branch. Nothing was merged to canonical; no frozen tool (`track_c_c6_acceptance.py` `a60c4c5f`, `track_c_c7_acceptance.py` `6b9362d0`, `track_c_c8_partial_acceptance.py` `e587a8d5`), Frozen record, approval record, hash, decision history, v1 file, owner or Codex branch, or PR #40 was modified or relabelled. No CAL_VERIFY, Holdout or real-provider access. Canonical `b8e39a2` unchanged.

Raw results: `GIE-014_cdr014_hardened_fpia_2026-10-04.json` (workflows `wf_d1bfad32-955` plan / review / implementation / verification / completeness, `wf_b4bdc699-5b8` fix round 1, `wf_91d664d4-8f3` fix round 2). Every run used private full clones; nothing was registered as a worktree in the main checkout.

## 1. Subject

| Field | Value |
|---|---|
| Branch | `integration/fpia-hardened-v1` (PIW), Draft PR #42, base `integration/cdr012-successor-trial-2026-10-04` (#40 `acaf1b5`) |
| Commits | `dc0bf79` implementation (22 new files) → `465354a` fix round 1 (F1–F7) → `babf0a4` fix round 2 (G1–G7, F2 disclosure) → `@@HEAD@@` vendored YAML loader (§7) |
| Files | `implementation/tools/integration/track_c_fpia*.py` (9 modules), `implementation/tools/integration/_vendor/` (PyYAML 6.0.1 pure Python, MIT), `implementation/tests/test_integration_fpia_*.py`, `integration_fpia_testkit.py`, `integration_fpia_real_history_checks.py`, `.github/workflows/track-c-fpia.yml`. All under paths outside every Track C namespace; no file under `implementation/src/` |
| References | R = Track C `b9e01a9`, V = v2 `c9e0fa7`, read only from the CDR-014 `fpia-reference-manifest` in the register at `f362926`; each SHA must occur as a delimited token in the user-verbatim `> ` lines of CDR-014. #40 `acaf1b5` is a verification subject, never a reference |

## 2. FPIA contract (as implemented)

```
python implementation/tools/integration/track_c_fpia.py --repo PATH --tree <T> --register-commit <G> --cdr CDR-014 --out FILE.json
exit 0 FPIA_PASS · 1 FPIA_FAIL · 2 FPIA_NOT_RUN (usage errors included)
```

- **Subject.** One exact commit T, an actual history-preserving merge result. FPIA never predicts or simulates a merge, never writes to the caller's repository, never pushes. No reference-SHA options exist.
- **Authority (short-circuit).** Manifest authenticated as above; G must be an ancestor of the authority handoff tip and its register a byte prefix of the tip's; R must be an ancestor of T (a squash or rebase of Track C fails AC-04). The canonical ref used by the frozen tools is read with `git ls-remote` from the authority remote, never from caller tracking refs.
- **PASS is a conjunction** of authority, runtime provenance, historical Frozen identity, Track C projection, integration interference, v2 binding and full regression; code identity must be determinate (SAME or DIVERGED) and the frozen tools must have run on T. Any FAIL gives FPIA_FAIL; anything undetermined gives FPIA_NOT_RUN, never PASS.
- **Statuses.** `HISTORICAL_FROZEN_IDENTITY_PRESERVED` (the unmodified tools replayed at their own evidence heads reproduce the recorded hashes); `CODE_IDENTITY_SAME/DIVERGED` (unmodified `code_hash()` and `CODE` recomputed on T, compared with R, reported as fact, never normalised); `TRACK_C_PROJECTION_PRESERVED` (protected source, test, tool and Frozen-evidence bytes identical to R; Track C decision register a byte-prefix append with exact attribution; shared overlays append-only; no deletion, substitution, mode, symlink, case or Unicode variant); `INTEGRATION_INTERFERENCE_NONE/FOUND` (bytecode or extensions, import shadowing, import-closure change, executed vs audited source, pytest config, plugins, `.pth`, `sitecustomize`, `conftest`, unattributed importers of Track C, complement workflows that spoof or run Track C); v2 binding (A_V paths byte-equal to V, v2 tests and Codex replay rerun differentially at V and T); full regression (whole suite on T, collection equality, no deselection except the one network node, junit consistency).
- **Separate evidence class.** `FROZEN_TOOLS_ON_T_PASS/FAIL`: the three frozen tools run unmodified on T, stdout/stderr kept verbatim as side files with sha256 (BRANCH_FROZEN_VALIDATION). Their FAIL from the canonical pin or the closed-world new-file lists is recorded verbatim, never converted, and is not an FPIA conjunct.
- **Counterfactual (fail-only).** With code identity normalised in memory, the Track C acceptance computations on T must reproduce the Frozen hashes; this can only fail the audit and is never reported as an equality claim.
- **Environment.** A shallow, partial or graft-cut repo, a fetch that refuses or does not deliver a ref, or a missing reference/evidence object gives FPIA_NOT_RUN. Child runs use `-E -P -s`, sanitised environment, explicit `sys.path`, audit hooks; an unverified environment fails closed.
- **Output.** Schema `TRACK_C_FPIA/2`: canonical `result`, its `result_sha256` (independent of interpreter and venv paths), `run` metadata, `<out>.verbatim/` side files; an existing `--out` is refused; `--verify-output` rechecks result and side files.
- **Constant non-claims.** No ordering claim; no new threshold, tolerance or default; no SHA or PR literal; dynamically constructed invocations are `NOT_CLAIMED` (D3-c); a job id/name collision alone is a note (D3-b).

## 3. Adversarial findings turned into regressions

43 acceptance criteria (AC-01 … AC-43) were derived from CDR-014 §1–§16 and every refuting finding of GIE-012 §4 (rv1 #1–9, rv2 #1–7). The plan review refuted the first plan; all 17 required changes were adopted before implementation (D3-A: full regression is a PASS conjunct; D3-B: the normalised-code-identity counterfactual is fail-only). Each GIE-012 counterexample is pinned as a Tier 1 regression:

| GIE-012 refuting finding | Now |
|---|---|
| code identity pinned to PASS | reported SAME/DIVERGED from the unmodified functions; counterfactual fail-only; no FPIA source names the code-identity symbols (self-test) |
| committed `.pyc`/`__pycache__`, extension suffixes | INTEGRATION_INTERFERENCE_FOUND (AC-23) |
| `*.dist-info` pytest11 plugin, `.pth`, `sitecustomize`, `conftest` | FOUND (AC-28) |
| `pytest.toml`, `.pytest.toml`, `.pytest.ini`, `setup.cfg`/`tox.ini` sections | FOUND (AC-27) |
| `.gitattributes` filters, eol, ident | raw-blob materialisation; FOUND (AC-31) |
| unattributed append to the Track C decision register | TRACK_C_PROJECTION_NOT_PRESERVED (AC-17) |
| free CLI reference heads | no such options; manifest-only (AC-01/02) |
| fixed three-tool set | tool and record universe derived from the Track C workflow and evidence; unknown gives NOT_RUN (AC-11) |
| hidden ordering assumption | audits only the actual merge result; no ordering claim (AC-42) |

Verification round 1 (`dc0bf79`) and its adversarial and completeness reviews found seven defects (F1–F7), fixed in `465354a` with 14 regressions that fail on `dc0bf79`. A shallow `--repo` gave a false frozen-tool FAIL next to FPIA_PASS; the canonical ref was read from the caller; v2 was NOT_APPLICABLE where FAIL was right; verbatim output was truncated; spoof attribution used V's whole tree; there was no CI trigger.

Verification round 2 (`465354a`) found G1–G7, fixed in `babf0a4`:

- **G1.** Workflow names were read with a regex. YAML-legal forms of `track-c-evl-validation` passed (S24 gave FPIA_PASS). Names are now read with a YAML loader and normalised: NFKC, casefold, default-ignorables removed, UTS #39 skeleton.
- **G2.** What complement workflows run is now resolved through YAML, working-directory, shell tokens, local scripts and composite actions.
- **G3.** Fetch status is parsed structurally; a ref named like "rejected" no longer gives a false NOT_RUN.
- **G4.** `--out` reuse is refused, and a side-file verifier was added.
- **G5.** `result_sha256` no longer depends on the venv path.
- **G6.** AC-04 wording.
- **G7.** The PR trigger is scoped to `integration/**` base or head branches.

F2 transport disclosure records environment-variable names only.

@@ROUND2_VERIFICATION@@

## 4. Results

| Case | T | FPIA | Code identity | Frozen tools on T | Notes |
|---|---|---|---|---|---|
| Baseline | `b9e01a9` | **PASS** | **SAME** | PASS | full regression 925 passed |
| PR #40 | `acaf1b5` | **PASS** | **DIVERGED** (`0ef3a900` → `df34b84f`) | FAIL (verbatim: canonical pin, new-file lists) | v2 binding PASS (307 v2 tests equal; Codex replay byte-identical); full regression 1517 passed |
| Shallow clone | `b9e01a9`, depth 50 | NOT_RUN | — | — | environment unverified |
| Landing-shaped L1 | `--no-ff` merge of `b9e01a9` onto `b8e39a2` | PASS | SAME | PASS | tree byte-identical to `b9e01a9` |
| Landing-shaped L2 | #21, then `b9e01a9` | PASS | SAME | FAIL (#21's files are new non-Track-C files) | interference NONE |
| T28 | #40 + #28 | **FAIL** | — | — | AC-21: unattributed importer `docs/codex_takeover/evidence/track_c/independent_c8_audit.py` |
| Canonical | `b8e39a2` | FAIL | — | — | authority AC-04 (R not an ancestor) |
| #39 | `0d31e06` | FAIL | — | — | Track C files not preserved (stale `e0b6d80` v2), 22 interference findings |
| FPIA branch | `dc0bf79`, `465354a` | PASS | DIVERGED | FAIL | self-placement clean |
| 24 tamper trees on `acaf1b5` | — | FAIL each on the right component | — | — | empty foreign `.py`: DIVERGED, projection preserved, FAIL only via RIG's own exact-file-set test |

Every T was run sequentially with default options, register commit `f362926`, CDR-014; results reproduce byte for byte across independent runs once the venv path is normalised.

## 5. Code identity SAME / DIVERGED

SAME only where T's `src/investment_system/**/*.py` equals R's (`b9e01a9`, L1, L2). Every integrated tree that adds Python under `src/investment_system` reports DIVERGED with the new value, as fact; it is neither a PASS nor an automatic violation (CDR-014 §2). Per §11 (GIE-012 §5-2), Track C registrations bound to R's identity fail closed on such a tree; registrations for a future run belong on the final canonical tree after the last code change.

## 6. Provenance verification

Per commit and per path (AC-20): every Track C path on T traces to R's history, or to V's history for the A_V v2 paths (byte-bound to `c9e0fa7`), through merge commits that are recomputed and must reproduce their recorded trees. The Track C register on T must be a byte-prefix append of R's whose extra lines come from V's lineage only. Squashes, rebases, foreign appends, and stale v2 files (`e0b6d80`) fail. Grafts and replace refs that fake ancestry give the truthful AC-04 FAIL, never PASS.

## 7. Full regression and CI

@@REGRESSION_CI@@

## 8. Completeness (CDR-014 §1–§16)

@@COMPLETENESS@@

## 9. Open D3 items, blockers, recommended order

@@OPEN@@

Maturity transitions: none. Track C C8 stays SYNTHETIC_VERIFIED and NOT FROZEN. An FPIA_PASS is integration-acceptance evidence for one exact merge-result SHA; it is not a Frozen PASS, not Track C acceptance by its owner tools, and not merge approval. Nothing here approves numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, grants, Official/LIVE, the #17 digest repin or a canonical merge.
