# GIE-010 · CDR-011 re-verification of Codex #31 v2 and #35; CDR-011 combined trial #39 · 2026-10-04

**Authority: none.** Integration evidence by the Primary Integration Writer. Codex owns #31 and #35 (CDR-008); nothing was committed, pushed or commented on any `codex/*` branch. Codex's PASS claims were not copied: every row below was established with the verifiers' own commands, oracle or probes. No CAL_VERIFY, Holdout or real-provider access. Canonical `b8e39a2` unchanged.

Workflow `wf_8f1764e8-c3c` (7 agents, 0 errors): four independent verifiers (preservation/regression/Actions, v2 vs the pre-built CDR-010 oracle, an adversarial refuter, identity/registry), a skeptic synthesis, the trial, and an adversarial trial check. Raw results: `GIE-010_cdr011_reverification_trial39_2026-10-04.json`. Hardened harness used by the trial: `GIE-010_next_trial_harness_hardened.sh.txt` (sha256 `2e2d45f6…`).

Subjects: #31 `codex/track-c-gsup-v2-2026-10-03` @ `e0b6d80` (`ACCEPTANCE_MANIFEST_V2.json`: HANDOFF_READY_APPROVED_SYNTHETIC_V2_SCOPE); #35 `codex/integration-hardening-2026-10-03` @ `8318b78` (= `e0b6d80` merged into the verified F1 fix `722c812`).

## 1. Verification table

**Verdict: VERIFIED_WITH_FINDINGS. No blocking finding.** Items 5 and the two oracle rows are PASS_WITH_CONDITIONAL_DECISION because of the squaring axis (§2).

| Row | Status | Evidence (short) |
|---|---|---|
| 1 Exact HEAD | PASS | `e0b6d80` = refs/pull/31/head; `8318b78` = refs/pull/35/head; one v2 commit on `29c2c20`; #35's F1 patch byte-equal to the `722c812` patch (sha256 `22283ec2…`) |
| 2 Approval record | PASS | `CDR010_APPROVAL.json` quotes the CDR-010 routing block byte-for-byte (source commit, blob and sha256 recomputed). Scoped register: +26 lines, 0 removed, byte-prefix extension; no out-of-scope approval |
| 3 Changed files / workflows | PASS | 21 A, 7 M, 0 D. Workflow changes: pinned `numpy==2.3.5` (fixes N3), `shell: bash` with pipefail on the qgv and leaderboard offline jobs (fixes NB4 masking), readiness path triggers, 5 allowlist entries, a new CDR-010 replay step. Nothing weakened |
| 4 v1 preservation | PASS | `evl/superiority.py` `8a1254d7`, the v1 oracle and tests, 43/49 existing evl and test_evl files, 199 report JSONs unchanged; runtime check: importing and using v2 leaves every v1 global identical |
| 5 M-B ↔ v2 exact agreement | PASS_WITH_CONDITIONAL_DECISION (F1) | v2 equals the oracle's `pow`-squaring variant on 676/676 graded cases including all 71,004 replicate t bits, and equals the GIE-008c "fsum / blocks" probe that CDR-010 cites on 676/676. Against the oracle's `d*d` default: r, deg, ties and p 676/676; T bits differ on 12 cases |
| 6a Historical CE4 | PASS | M-B .10 vs v1 .15, the single zero-variance replicate counted only by v1 |
| 6b Production-v2 counterexample | PASS | production v2: CE4 r1/d1/t0 p .10 vs v1 .15 on the same tree; identical at `8318b78` |
| 7 Identity negatives | PASS | own harness 87/87 at both heads; GIE-008 harness 151/151 plus 8/8 |
| 8 Re-encoding | PASS | 14/14, 0 provider reads |
| 9 Campaign/root/label bypass | PASS | 52/52, including v1 ↔ v2 method switches refused; SIGKILL replays at 6 points make 0 reads; races admit exactly one in 11/11 rounds |
| 10 Targeted regression | PASS | gsup + c8 files 430 passed; v2 files 118 (86 + 21 + 11) |
| 11 Full regression | PASS | `e0b6d80` 1395 passed, `8318b78` 1413 passed, 0 failed/errors/skips, locally and in CI logs |
| 12 Actions | PASS | #31: 8 runs on `e0b6d80` all success (37164876759 and 7 siblings); #35: 7 runs on `8318b78` all success (37164938869 and 6) |
| 13 CAL_VERIFY / Holdout | PASS | no data, gate_evidence, holdout or cal_verify paths; no network patterns; real paths fail closed |
| CE4 / FLIP / LEFT_SUM / TIE / seed 275 | PASS | production v2 p .10 / .10 / .35 / .45 / .55 (v1 .15 / .20 / .40 / .55 / .60) |
| Exact decimal comparison | PASS (information) | fixtures 5/5 equal exact decimal; battery 619/675 where defined, differences are decimal ties/degeneracy under the mandated float predicate |
| Degeneracy handling | PASS | subnormal 10/10 bit-exact; 720,641 refuter replicates, 0 predicate mismatches; truly zero-SE cases fail closed |
| Source identity preservation | PASS | `gsup_source_identity.py` `fa93bf88` and `superiority_source_identity.py` `71bf7375` unchanged at `29c2c20`, `e0b6d80`, `8318b78` |
| #35 F1 on new head | PASS | patch equality, +18 tests passing, CI 1413 on exact `8318b78` |

## 2. Conditional user decisions found

1. **F1 squaring operator.** `evl/superiority_v2.py` L75 and L91 square with Python `** 2`, which calls libm `pow` and is not always correctly rounded on glibc 2.39. The approved simulation's NumPy squares, and a plain `d*d`, are correctly rounded. CDR-010 does not name the squaring operator, and v2 matches the GIE-008 column it cites, so this is not a defect.
   - Effect on the oracle battery: T bits in 12/676 cases, t bits in 17/71,004 replicates; r and p unchanged.
   - Effect on constructed near-tie inputs (refuter): p changes. `[8.7,0,0,0,-2.9,2.9,2.9,8.7,-2.9]`, L=2, B=19, seed 11: v2 .20 vs `d*d` .15. A second input: .15 vs .10.
   - With `pow`, T and t bits, and in rare near-ties p, can depend on the platform's libm. Cross-platform behaviour was not measured.
   - Codex's own test oracle also uses `** 2` and none of its fixtures exercise this axis, so Codex's suite cannot detect it. Codex's manifest does not disclose the choice.
2. **F3 undefined or near-undefined statistic.** When the exact long-run variance is zero but float64 leaves a tiny positive residue, v2 returns a p instead of failing closed. Example, reproduced by the Primary Integration Writer on production v2 at `e0b6d80`: `[-0.2,-0.1]*6`, L=2, B=19 gives mean −0.15, long-run variance 1.54e−33 (exactly 0 in real arithmetic), statistic ≈ −1.32e16, 19/19 replicates degenerate, and the minimum p .05 at both seed 7 and seed 11. The synthesis reported v1 1.0 and literal `run()` .90 on the same input. A constant positive series `[0.05]*12` likewise gives statistic ≈ +1.77e16 and p .05. The refuter reports that a registry built from such cells can reach REJECT_H0 / STAT_PASS (the synthesis reproduced the kernel level). This is CDR-010-literal behaviour and matches every reference, including the GIE-008 probe. Any guard is a new rule, so it is a user decision.
3. **Identity hardening before real sources (carried over).** N2: identity strings are not canonicalized and descriptor issuance has no capability gate. The frozen plain v1 registry can coexist with v2 unless its records sit in the coordinator-pinned store. Neither is required in synthetic scope; both are needed before any real-source work.

Other non-blocking findings: `CDR010_APPROVAL.json`'s enum omits the replicate-mean formula and the squaring operator (the verbatim quote is exact); #31's preservation gate predicate does not cover `tests/evl_c8_gsup_v2_oracle.py`, so the gate counts 10 additions, not 11 (harmless; Codex-owned); `qgv-producer-real` still uses a shallow checkout (push-only).

## 3. CDR-011 combined trial · PR #39

| Field | Value |
|---|---|
| Branch / head | `integration/cdr011-trial-2026-10-04` @ `0d31e06` (merge 1 `5d0a49b`), tree `2a9b7998` |
| Inputs (fresh, 01:47Z) | #38 `7e3861b` + #31 `e0b6d80` + #35 `8318b78`; `--no-ff`, 0 conflicts, no auto-merged paths |
| Local harness | hardened `next_trial.sh`, label CDR011_TRIAL: every step rc=0. Full suite **1441 passed**, 0 failed/errors/skips. Fingerprints `f690f9c0…`. `web_mvp.py` `10ad8c76`. #35 protection with live tamper probe. #31 preservation gate verbatim: 41 owner files, 10 additions. v2 blob `370e9b42` = `e0b6d80`. Register append-only. No data/gate_evidence change. Runtime grants all NONE; 77 + 257 escalation hits reviewed, none activates anything. All browser/E2E steps pass |
| CI | Draft PR #39, base #30: **10/10 PR workflows success** on `0d31e06` (runs 37169669821 … 37169669875; 11 jobs). `codex-integration-readiness` on the exact head reports 1441 passed |
| Adversarial trial check | no blocking finding: both merge trees reproduced in a temp store; CI head_sha confirmed; fingerprint, gate, protection (all 15 shared paths), targeted tests (255 + 200) re-run; all 77 delta escalation hits reviewed plus broader sweeps. Corrections are descriptive only (the `shell: bash` workflow change was omitted from one description; escalation hit counts slightly undercounted) |
| #38 reuse | none: 1441 tests here vs 1193 on #38 |

States: BRANCH_STATE #39 `0d31e06` pushed. INTEGRATION_STATE CI_VERIFIED trial. CANONICAL_STATE NOT_MERGED; canonical merge is USER_DECISION_REQUIRED.

Maturity transitions: none. Track C C8 stays SYNTHETIC_VERIFIED and NOT FROZEN; v2 is now implemented and verified in synthetic scope. Nothing here approves numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, grants, Official/LIVE or a canonical merge.
