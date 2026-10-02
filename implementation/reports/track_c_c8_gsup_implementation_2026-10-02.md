# Track C C8 G-SUP implementation (A6 S1–S8 + method Q1–Q6) — SOFTWARE CONTRACT ONLY / NOT FROZEN

Recorded: 2026-10-02T21:08:47+09:00 (KST). Source commit `a156a35` on `ccr-22e3ff16-p7n5k5`
(base `ff78c4f` feature/track-c-evl). Authority: `track_c_c8_a6_partial_approval_2026-10-02.json` (blob 4f897ec…)
and `track_c_c8_a6_method_approval_2026-10-02.json` (blob a6f9941…), both runtime-pinned in the new module.

## Added (additive only; no existing source/test blob changed)
| File | Blob | Content |
|---|---|---|
| `src/investment_system/evl/superiority.py` | c83e22d | `C8_GSUP_STUDENTIZED_CBB_v1` kernel, registration contract, Development-only dependence estimate, stricter-envelope feasibility gate, exclusive one-shot registry |
| `tests/evl_c8_gsup_oracle.py` | a5f00fa | independent oracle (own index stream/loops, no package import) |
| `tests/test_evl_c8_gsup.py` | 64dfa5e | 68 tests: authority, S1 substitutes, real-scope NOT_RUN, no numeric/effect-floor default, unsupported single-draw controls, exact conjunction, method/no-fallback, block rule, A10 dependency, oracle equality, determinism/one-sidedness, undefined→NOT_RUN, nonfinite→FAIL, Development-only estimate, envelope union, α reachability/support/blocks, strong-dependence INFEASIBLE, one-shot, crash no-retry, wrong target, access order, tamper |
Tool allowlists extended (C6/C7/C8 runners) for exactly these three files.

## Behaviour
- Hard-decision method = studentized CBB bootstrap-t using frozen C6 `circular_block_indices`; p=(r+1)/(B+1); ties and degenerate replicates count as exceedances (conservative).
- Existing unstudentized kernel retained only as `COMPARISON_EVIDENCE_ONLY_NOT_DECISION` (singleton `family_reality_check`). Batch-means t: INACTIVE, no fallback.
- Controls: exactly EQUAL_SIMPLE + MARKET_CAP; RANDOM_RANKING / RANDOMIZED_WEIGHTS → `UNSUPPORTED_SINGLE_DRAW`. Claim = all controls × all 4 required cohorts.
- Pre-access feasibility: α reachability at B, minimum support, ≥2 full blocks, synthetic boundary-null empirical size ≤ α+tolerance on every point of (conservative envelope ∪ Development estimate+margin). Otherwise `NOT_RUN_INFEASIBLE` without any CAL_VERIFY read; no retest (registry slots are config-independent per target).
- One-shot: durable exclusive access intent before provider call; crash → `CRASH_NO_RETRY`; second assess refused.
- Output: `statistical_status` ∈ STAT_PASS/STAT_FAIL/NOT_RUN/NOT_RUN_INFEASIBLE; `decision` stays `NOT_RUN_EFFECT_FLOOR_DEFERRED` (A6-S7). official=false, no promotion authority, no Holdout eligibility.
- Scope: only `SYNTHETIC_SOFTWARE_VALIDATION` with `SYNTHETIC_SOFTWARE_VALIDATION_ONLY` values; real scope, real provider, non-fixture role designation (A10) → NOT_RUN.

## Local verification (this environment; not GitHub Actions)
C8 targeted 184 (116 existing + 68 new), C7 97, C6 130, C0–C5 103, full 910 PASS; C6, C7 and C8-partial acceptance runners exit 0 / PASS,
no unauthorized or unexpected files. Log: `track_c_c8_gsup_local_verification_2026-10-02.txt`. The CI workflow triggers only on
`feature/track-c-evl`; no Actions run exists for this commit.

## Implementation-defined method details requiring confirmation before any real use (not silently approved)
1. Dependence estimator `AR1_LAG1_AUTOCORRELATION_v1` (Q3 requires a predefined estimator; identity not chosen by the user).
2. Envelope process family `AR1_GAUSSIAN` only (heavy tails / GARCH / MA overlap not representable).
3. Degenerate replicate (zero replicate variance) counted as exceedance; statistic ties counted as exceedance.
4. Replicate variance uses the n//L full blocks only; original-sample LRV uses all n overlapping circular blocks.
5. Feasibility uses the registered decision seed for every synthetic replication.

## Known label discrepancy
The frozen foundation constant `calibration_contracts.BLOCKED` still lists A6, so the C8-partial runner prints
`"A6":"PROPOSED_NOT_APPROVED_NOT_ACTIVE"`. Foundation source is intentionally untouched; authoritative A6 status is
`METHOD_APPROVED_CONDITIONAL / NUMERIC_CONFIG_PENDING` per the approval records above.

## Status / stop
A6 software contract implemented (synthetic scope). C8 NOT FROZEN; 8/11 = 72.7%; A8/A10 NOT APPROVED; Holdout UNCONSUMED; Package B/C unchanged.
STOP: next steps require actual numeric configuration (α, B, L/rule, seed, size tolerance, envelope values/margin, minimum support,
feasibility replications/seed) and confirmation of items 1–5, then real CAL_VERIFY access — all need explicit approval.
