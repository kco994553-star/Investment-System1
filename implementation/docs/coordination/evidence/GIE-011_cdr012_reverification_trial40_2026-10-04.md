# GIE-011 · CDR-012 re-verification of Codex #31 (`c9e0fa7`); successor trial PR #40; RIG → SEC 8-K readiness · 2026-10-04

**Authority: none.** Integration evidence by the Primary Integration Writer. Codex owns #31 and #35 (CDR-008); nothing was committed, pushed or commented on any `codex/*` branch, and Codex's PASS claims were not copied. No CAL_VERIFY, Holdout or real-provider data was used. Canonical `b8e39a2` unchanged.

Raw results:

- `GIE-011a_cdr012_prep_rig_audit_2026-10-04.json`: workflow `wf_3f7c60ef-5ab` (5 agents): CDR-012 expectations, successor-trial harness, RIG → SEC 8-K audit with adversarial verification, completeness critic. All prep finished before or independently of Codex's repair.
- `GIE-011_cdr012_reverification_trial40_2026-10-04.json`: workflow `wf_4e6007e2-97e` (7 agents): four independent verifiers, skeptic synthesis, successor trial, adversarial trial check.
- `GIE-011_successor_trial_harness.sh.txt` (sha256 `e5b7fb94…`): the harness as used for PR #40, plus two later fixes (§4).

## 1. CDR-012 re-verification of #31 `c9e0fa7`

Subject: `codex/track-c-gsup-v2-2026-10-03` @ `c9e0fa7` ("Repair approved CDR-012 v2 squaring and all-degenerate fail-closed"; `ACCEPTANCE_MANIFEST_CDR012.json` HANDOFF_READY_APPROVED_SYNTHETIC_V2_SCOPE). One commit on the verified `e0b6d80`: 25 added, 7 modified, 0 deleted.

**Verdict: VERIFIED_WITH_FINDINGS. 19/19 rows PASS. No blocking finding.**

| Row | Status | Evidence (short) |
|---|---|---|
| Exact HEAD | PASS | origin = refs/pull/31/head = `c9e0fa7`, unchanged through the run |
| CDR-012 approval record | PASS | `CDR012_APPROVAL.json` quotes the CDR-012 routing block byte-for-byte (source `1620f71`, blob `bc402d6b` recomputed); its contract adds `squaring=MULTIPLICATION`, `all_degenerate=NOT_RUN`; scoped register is a byte-prefix append; no out-of-scope approval |
| Diff classification | PASS | `superiority_v2.py` changes exactly two things: squaring via `d*d` (L89–90, L106–107) and `if degenerate == replicates: raise MissingStatisticalEvidence("all bootstrap replicates degenerate")` (L124–125). The v2 test, replay tool and readiness workflow were edited in place; old pinned traces are byte-identical; no assertion was removed. Evidence, approval, oracle and pins are additive |
| F1 implementation | PASS | no `** 2`, `pow` or `round` in v2; every multiply listed |
| F3 implementation | PASS | NOT_RUN only when every replicate is degenerate |
| No new epsilon/tolerance/threshold | PASS | none added (scan of numeric literals and comparisons); epsilon mutants are caught by the oracle |
| Independent oracle (CDR-012 expectations) | PASS | `compare_cdr012.py` with the strict F3 message: EXACT_MATCH_ALL_GRADED, 747 graded (710 bit-exact STAT, 37 NOT_RUN). Control at `e0b6d80`: 68 mismatches |
| F1 detectors | PASS | 0/16 mismatches; the two p-flip inputs give `d*d` p .15 and .10 |
| All-degenerate → NOT_RUN | PASS | 0/37 at kernel level; registry probe: all-degenerate cells NOT_RUN, no STAT_PASS |
| `deg == B−1` boundary | PASS | 0/17; still produces a p |
| Near-undefined, not all degenerate | PASS | 0/14; `[0.05]*12` keeps p .05 (CDR-012 approves no epsilon) |
| GIE-008 fixtures on production v2 | PASS | CE4 .10 (v1 .15), FLIP .10, LEFT_SUM .35, TIE .45, seed 275 .55 |
| v1 preservation | PASS | `superiority.py` `8a1254d7`, `statistical_kernels.py` `28e1c184` and every v1 test/oracle unchanged |
| Source identity; no reopen after F3 | PASS | identity modules unchanged; an all-degenerate NOT_RUN keeps the source consumed; retries with changed labels, root or method are refused |
| Targeted regression | PASS | v2, identity and C8 files all pass |
| Full regression | PASS | 1472 at `c9e0fa7` (CI ran all 1472; local runs deselect one live-SEC test) |
| Actions | PASS | all check runs on `c9e0fa7` success; #35 readiness run 37175320382 needed a second attempt after attempt 1 failed in the pre-existing live SEC network test (IncompleteRead) |
| Engine fingerprints | PASS | `f690f9c0…` |
| #35 state | PASS | `4cf8ead` = `c9e0fa7` merged into the F1 fix; F1 source/test patch byte-equal to `722c812`; the merge also adds 6 Codex docs files |

Findings (non-blocking):

- **F1 scope question.** Frozen v1 `superiority.py:247` (`development_dependence_estimate`) still squares with `(v - m) ** 2`. v2 reaches it through the inherited pre-access `record_feasibility`. It feeds only the Development dependence envelope for FEASIBLE/INFEASIBLE, never a p-value. CDR-012's wording ("G-SUP M-B v2의 squaring") and GIE-010 F1 concern the M-B statistic, which complies fully. If the user means CDR-012 to cover v2's whole path, a v2-only additive estimator would be needed, since v1 must stay unchanged.
- The v2 METHOD/POLICY IDs are unchanged although the arithmetic changed in place; outputs of `e0b6d80` and `c9e0fa7` are distinguishable by the `arithmetic_contract` and the CDR-012 supplement pin.
- The F3 refusal shares the `MissingStatisticalEvidence` class with zero-SE refusals; only the message distinguishes it. Verification used the strict message mapping.
- Two golden-trace assertions in `test_evl_gsup_v2_arithmetic.py` now check the historical oracle rather than production; production still matches all 9 pins bit for bit and is pinned through the new CDR-012 test.
- Carried over: N2 identity canonicalization and issuance gate before real sources; the plain frozen v1 registry can coexist with v2 for the same content.

## 2. Successor trial · PR #40

| Field | Value |
|---|---|
| Branch / head | `integration/cdr012-successor-trial-2026-10-04` @ `acaf1b5` (merge 1 `368b5a1`), tree `40220de1` |
| Inputs (fresh) | #39 `0d31e06` + #31 `c9e0fa7` + #35 `4cf8ead` (STACKED); `--no-ff`, 0 conflicts; tree differs from #39 (not NO_NEW_CONTENT) |
| Local harness | every step rc=0: 25 PASS, 2 REVIEW_REQUIRED (reviewed: negated two-line sentences and a renamed CI step). Full suite **1518 passed**, 0 failed/errors/skips. Preservation gate verbatim: 41 owner files, 13 additions. #35 protection with tamper probe. v2 blob `8e56a66e` = `c9e0fa7`. Fingerprints `f690f9c0…`. Browser/E2E pass |
| Harness patch (disclosed) | the prepared harness compared the CI allowlist (13) with the whole reviewed list (36, incl. docs), which can never match; the trial used a patched copy comparing the gate-protected part (13 = 13) while still byte-comparing all 36 files |
| Independent oracle on the trial tree | `compare_cdr012.py` rc=0 (default and strict), EXACT_MATCH_ALL_GRADED; registry probe rc=0 |
| CI | **10/10 PR workflows, 11/11 jobs success** on `acaf1b5` (runs 37179194343 … 37179194479) |
| Adversarial trial check | no blocking finding; tree reproduced; CI head_sha confirmed; gate, protection, fingerprint, oracle, registry probe and targeted tests (534) re-run; all escalation hits reviewed |
| #39 reuse | none |

Note: the full suite contains the pre-existing `test_raw_and_providers.py::test_live_sec_fetch_is_optional_and_not_stage2`, which attempts a live SEC request and passes on its fail-closed branch. No provider data was used. The maintained harness now deselects it (§4).

States: BRANCH_STATE #40 `acaf1b5` pushed. INTEGRATION_STATE CI_VERIFIED trial. CANONICAL_STATE NOT_MERGED.

## 3. RIG → SEC 8-K chain and #21 (readiness, before Codex's repair)

| Scenario | Full suite | Fingerprint |
|---|---|---|
| S1 chain alone on canonical | 423 passed | pre-adoption `4ba44a8c…` |
| S2 Track C first | 953 passed | post-adoption `f690f9c0…` |
| S3a / S3b with the Web chain (either order) | 467 passed, 1 failed (the IF-2 sentinel) | `4ba44a8c…` |
| S4 Track C, then Web, then RIG | 997 passed, 1 failed (same sentinel) | `f690f9c0…` |

- **Verdict: READY_AFTER_OWNER_ACTIONS** (upheld by the adversarial verifier and the critic). 0 conflicts in every order.
- Owner actions: convert the sentinel `test_rig_news_ingest.py:192` (fails whenever #7's `reports/entity_metadata` is present), byte-identical to whatever the #30 lineage adopts; fix GIE-006 F6 (the RIG test creates and reuses the fixed-path worktree `/tmp/rig-news-producer-ro`; present in both vehicles); lift the "Do not merge / INTEGRATION WAIT" dispositions.
- CI gaps: #13 has never run on Actions; #16's owner workflow fails on re-run today (422 passed, 1 failed) because its shallow fetch no longer contains the pinned `6fe9eee`; RIG tests need objects `a013f1c` and `6fe9eee`, so shallow full-suite workflows elsewhere will fail once RIG is on their branches.
- **#21 (Worker Contract, docs only):** merges cleanly (396 passed, fingerprint unchanged), already inside #30/#38/#39/#40. Ready for a canonical-merge decision, but **not order-free**: like any canonical advance or new non-Track-C file, it makes Track C's frozen acceptance tools fail (MAC-X1).
- Remaining canonical-package gaps (critic): the all-chains owner-route union trial has never been run; the Track C landing vehicle is undecided and only the #30 lineage carries v2/CDR-012; MAC-X1 affects every merge before Track C lands.

## 4. Harness maintenance

The maintained successor harness (`GIE-011_successor_trial_harness.sh.txt`) is the patched copy used for #40 plus two fixes:

- the full suite deselects the live SEC test, so no network connection is attempted;
- a non-dry run is refused unless the #31 head equals the independently verified v2 commit.

Maturity transitions: none. Track C C8 stays SYNTHETIC_VERIFIED and NOT FROZEN. Nothing here approves numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, grants, Official/LIVE or a canonical merge.
