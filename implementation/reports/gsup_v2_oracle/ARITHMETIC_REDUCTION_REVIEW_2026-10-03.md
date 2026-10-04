# G-SUP M-B v2 arithmetic review — synthetic diagnostic only

Base: `8230007f5edb86aec949166e25fd62a680db3ae2`, which records the explicit M-B v2 and synthetic source-descriptor approvals. M remains approved. **No arithmetic reduction is selected by this diagnostic.** Numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, Official/publication and canonical merge remain unapproved.

The approved package `track_c_c8_a6_method_decision_package_2026-10-02.md` lines 21, 122 and 145 explicitly retain the frozen C6 circular-index convention and Python `random.Random`. The NumPy simulation RNG is an evaluation generator, not a replacement for the approved production index stream. The simulation source (`run`, lines 23–35) specifies first `ceil(n/L)-1` replicate variance blocks, at least two such blocks, and degenerate non-exceedance. The preserved counterexample record lines 6 and 12–14 specifies `>=` ties and plus-one p-values. Undefined original statistics remain fail-closed NOT_RUN; the simulation's NaN transport is not decision authority.

With identical frozen indices, formulas and inputs, floating reductions can change integer exceedance counts:

| Synthetic input | n, L, B, seed | Reduction | exceedances | degenerate replicates | p |
|---|---|---|---:|---:|---:|
| `[.01,.01,-.01,-.02,.02,.01,.01,.01]` | 8, 3, 19, 46 | existing `math.fsum` formula | 1 | 2 | .10 |
| same | same | literal NumPy cumulative-block formula | 3 | 0 | .20 |
| `[-.02,.01,.02,0,.01,.01,.01,-.01,.01]` | 9, 4, 19, 34 | Python 3.11 left-to-right `sum` | 7 | 0 | .40 |
| same | same | existing `math.fsum` formula | 6 | 1 | .35 |

These are synthetic evaluation values, not configuration defaults. The first example changes the illustrative comparison at .10. No tolerance, rounding, quantization, replicate exclusion, modified denominator, or new threshold has been introduced. The existing v1 source and historical results are preserved.

The initial NumPy probe used NumPy 2.3.5 on Python 3.12.14. This worker independently reproduced both displayed differences in a separate **Python 3.11.16 / NumPy 2.3.5** diagnostic environment. `ARITHMETIC_REDUCTION_TRACES_2026-10-03.json` contains all inputs, index streams, observed statistics/variances, every replicate block sum/variance/statistic, degeneracy, equality ties and exceedance counts. It binds the preserved sources and approval record by Git blob and SHA-256. The original simulation's NumPy version was not recorded; literal floating identity to that historical environment cannot be assumed.

Additional fixed equality-tie example: `[.02,0,-.02,-.01,.01,0]`, n=6/L=2/B=19/seed=72, has observed statistic zero. `math.fsum` records three nondegenerate equality ties, r=8 and p=.45; Python 3.11 left-to-right sum records one tie, r=7 and p=.40. Both use the approved `>=` rule. This difference is arithmetic, not a new tie policy.

## Executed independent validation

- `PYTHONPATH=src /workspace/gsup-v2-oracle-venv311/bin/python -m pytest -q tests/test_evl_gsup_mb_reduction_diagnostic.py --junitxml=reports/gsup_v2_oracle/DIAGNOSTIC_TESTS_2026-10-03.xml`: **20 passed**. This includes frozen-index agreement across 44 explicit n/L combinations and four seeds, fixed CE1–CE5 method comparisons, arithmetic counterexamples, undefined-original fail-closed, nonfinite/implicit-dimension rejection, authority-tamper rejection and fresh-process byte determinism.
- `tools/gsup_mb_reduction_diagnostic.py --out reports/gsup_v2_oracle/ARITHMETIC_REDUCTION_TRACES_2026-10-03.json`: completed in Python 3.11.16 / NumPy 2.3.5, with nine fixed synthetic fixtures and three independent M-B reduction transports. Historical v1 reconstruction is comparison-only; no production statistical kernel is imported.
- Full repository regression: **NOT_RUN by this worker**; primary integration writer owns that separate execution. GitHub Actions: **NOT_RUN by this worker**.

Acceptance criteria completed: (1) normative citations and original-statistic boundary; (2) three independent references without production imports; (3) deterministic complete counterexample traces and negative regressions; (4) scoped evidence, hashes and normal commit. **4/4, task 100%**; this is diagnostic-task completion and does not activate v2 or resolve the arithmetic decision.

Before → after: existing tracked files changed **0 (+0)**; active statistical methods added **0 (+0)**; synthetic diagnostic tools **+1**; synthetic diagnostic test modules **+1**; real-data accesses **0 (+0)**; Holdout consumptions **0 (+0)**. Existing v1 and Frozen source/test/evidence bytes are preserved. Track C C8 maturity remains the prior synthetic-verified approved subset; new G-SUP v2 kernel remains DESIGN pending arithmetic authority.

BRANCH_STATE: diagnostic implemented and synthetically verified on `codex/gsup-v2-oracle-2026-10-03`. INTEGRATION_STATE: not merged by this worker. CANONICAL_STATE: not merged. Base and merge-base: `8230007f5edb86aec949166e25fd62a680db3ae2`.

Status: **USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION**. Independent source-identity implementation can continue while this decision is pending.
