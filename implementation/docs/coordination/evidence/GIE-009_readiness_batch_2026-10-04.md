# GIE-009 · Canonical-merge readiness audits, CDR-010 oracle prep, next-trial harness prep · 2026-10-03/04

**Authority: none.** Integration evidence by the Primary Integration Writer. Nothing was merged, pushed or commented. All trials were local, in temporary object stores. No CAL_VERIFY, Holdout or real-provider access. Canonical `b8e39a2` unchanged.

Workflow `wf_fad367d7-0f1`: 11 agents, 0 errors. Raw results: `GIE-009_readiness_batch_2026-10-04.json`. Each chain audit was followed by an adversarial verifier that re-derived its load-bearing claims; a completeness critic reviewed the whole batch.

Scenarios used in every chain audit:

- **S1:** the chain alone, merged `--no-ff` onto canonical `b8e39a2` in stack order.
- **S2:** Track C owner tip `b9e01a9` merged first, then the chain. This is how the A1 guards see the C-28-adopted state.

## 1. Consolidated readiness (after adversarial verification)

| Chain | Verdict | S1 full suite | S2 full suite | Main blockers |
|---|---|---|---|---|
| QGV → Leaderboard (#10, #14 + #26, docs/qgv-context) | READY_AFTER_OWNER_ACTIONS | 452 passed | 982 passed | #26 into #14; IF-2 sentinel conversions in #10 and #14; QL-B5 (below) |
| Producer Infrastructure / Web (#5, #6, #7 + #33, #9 + #32, #17 + #27, #19, #29, #34, #36) | READY_AFTER_OWNER_ACTIONS | 498 passed | 1028 passed (chain ends `b8db8fb0` / `7af98f43`, local only) | A1 proposals into owner branches (#27 required with Track C); #17/#19 workflows run the mini_pytest shim, which cannot import pytest.mark tests |
| Technical / US Equity Session (#11 + #22, #15 + #23, #18 + #24) | READY_AFTER_OWNER_ACTIONS | 454 passed | 984 passed | A1 forward-merges; chain workflows need the `0ea00d2` runtime repair plus numpy 2.3.5; new owner trees have no Actions |
| Macro (#5, #6, #9 + #32, #12 + #25) | READY_AFTER_OWNER_ACTIONS (S1) | 442 passed | 972 passed | #25 into #12; #12 owner disposition "Draft, INTEGRATION WAIT"; no full-suite Actions on any #12/#25 tree |
| Track C (#4 / `b9e01a9` / #31 + #35) | NOT_AUDITED_IN_BATCH | | | landing vehicle not decided; re-verification of #31 v2 runs separately (GIE-010) |
| RIG → SEC 8-K (#13, #16) | NOT_AUDITED (gap) | | | sentinel conversions against the #7 registry; only exercised inside #30/#38 |
| Worker Contract #21, #37, #28 | NOT_AUDITED; scope undecided | | | user scope decision |

All merges in all orders had 0 conflicts. In every S2 end state the engine fingerprints equal the post-adoption values (technical `66cb2383`, macro `7e427949`, combined output `f690f9c0…`); every S1 end state equals the pre-adoption pins (combined `4ba44a8c…`). Negative controls confirmed each A1 proposal is required once Track C is present: without #26, #24 or #25, exactly the expected guard test fails.

## 2. Cross-chain ordering constraints

1. **QL-B5 (found by the QGV verifier, confirmed by the critic).** `leaderboard-real-producer.yml` has an unmasked step that diffs the owner branch against *live canonical* over whole cross-track directories. Once Track C, the Technical chain, the Macro chain or #35 lands on canonical, every later push to the Leaderboard owner branch fails CI. The Leaderboard owner pushes (#26 fast-forward, IF-2 conversion, pipefail) must therefore be CI-green before any of those land, or the owner changes that step to diff against the merge-base.
2. **IF-2 second-merger rule.** The sentinel conversions in #10, #14/#26, #13 and #16 are preconditions of whichever of {#9 or #7} and {#10/#14 or #13/#16} merges second. The Web audit's claim that downstream sentinels do not block its own merge holds only if QGV and RIG are not yet on canonical.
3. **CI runtime ports.** Owner workflows for #11, #15, #18, #17 and #19 need the `0ea00d2` form (Python 3.11, pytest 9.1.1, native pytest, fetch-depth 0) and, if Track C lands via #31/#35, numpy 2.3.5 (Codex `f29ea6e`). Without it they go red on any tree that contains Track C, from the #17 step onward in S2.
4. **Track C acceptance tools on integrated trees (MAC-X1).** `tools/track_c_c6/c7/c8_partial_acceptance.py` reject every non-Track-C file and pin canonical to `b8e39a2`. They fail on any integrated tree and after any canonical move. Changing them alters SOFTWARE FROZEN Track C tooling, so the critic reclassified this from OWNER_ACTION to **USER_DECISION_REQUIRED**: how Track C acceptance is certified on integrated trees or an advanced canonical.
5. **No post-merge CI on canonical.** No workflow triggers on a push to canonical. Two workflows become dispatchable on canonical and push to the branch they run on (`qgv-producer-real` commit-back with `| tail` masking; `entity-metadata-ingest` real-provider fetch plus push). Owners should add ref guards and pipefail before any canonical merge.
6. **Time bound.** The c21 raw-store artifact that the QGV real job needs expires 2026-12-26.

## 3. CDR-010 reference oracle (prep for GIE-010)

Built before Codex's v2 existed, under the Primary Integration Writer's scratch space (not in the repository).

- C6 index-stream replica: 0 mismatches over 3,000 combinations and 113,013 replicates against the real v1 kernel generator.
- Five GIE-008 fixtures under CDR-010: CE4 .10, FLIP .10, LEFT_SUM .35, TIE .45, seed 275 .55, equal to GIE-008 §2.
- Battery: 681 cases (676 graded, 71,004 replicates). A second implementation with no shared code (exact-rational IEEE emulation) is bit-identical on 681/681.
- Two axes that CDR-010 does not pin literally were flagged as conditional:
  - **F1 squaring:** `d*d` (correctly rounded, as NumPy in the approved `run()`) vs Python `d**2` (libm `pow`, not correctly rounded on glibc 2.39 for about 0.04–0.09% of doubles).
  - **F2 partial addition:** `fsum(full) + partial` (oracle default; matches the GIE-008 column CDR-010 cites) vs `fsum(full + [partial])`.
- Critic spot-check against Codex's v2 at `e0b6d80` (the formal result is in GIE-010): v2 squares with `** 2`. r, deg, ties and p match the oracle on 676/676 graded cases; 27 cases differ only in T or single-replicate t bits, exactly the oracle's `pow` variant. F2 does not apply: v2 adds the partial after `fsum`.

## 4. Next combined-trial harness (prep for the CDR-011 trial)

- Harness `next_trial.sh` (Primary Integration Writer scratch). Dry run on #38 `7e3861b` + #31 `29c2c20` + #35 `722c812`, labelled `DRY_RUN_PRE_V2`: all 22 steps passed, full suite 1323/1323. This is harness validation only and is **not** the CDR-011 trial.
- The critic found checks that could pass silently. The Primary Integration Writer hardened the harness on 2026-10-04 before the CDR-011 trial:
  - the Track C additions check now fails unless the trial's declared allowlist equals the reviewed 11-entry set (6 entries verified at `29c2c20` plus the 5 v2 files) and no addition falls outside it;
  - the full-suite junit check requires zero skips and at least 1323 tests;
  - a new check requires the trial's `evl/superiority_v2.py` blob to equal the blob at the independently verified `e0b6d80`.
  - Smoke test on #35 `8318b78`: all hardened checks pass and the live tamper probe still fails as intended.
- Publishing the trial PR against base #30 makes all 10 PR-triggered workflows, including `codex-integration-readiness`, run without dispatch.
- #34's `tests/test_web_research_guard.py` uses `pytest.mark`, which the mini_pytest shim in the #17/#19 owner workflows cannot import. #34 is left unchanged: rewriting it would fix only S1, and the owner-workflow runtime port (item 3 in §2) fixes both scenarios. #30-based trials already carry that port, which is why #38's p01 and qgv checks are green.

## 5. Stale routing entries corrected by this batch

- #22–#27 and #26 have exact-head Actions (for example #26 run 37101443041; #22 run 37098417854). GSI entries showing NOT_RUN were stale.
- #25 has only a targeted 11-test check (Codex's macro job on `4a07099`), not a full-suite run.

Maturity transitions: none. No canonical merge.
