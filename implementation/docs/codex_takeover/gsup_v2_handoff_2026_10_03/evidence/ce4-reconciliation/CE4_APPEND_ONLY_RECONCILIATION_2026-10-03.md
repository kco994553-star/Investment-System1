# CE4 historical helper / literal Q1 / preserved v1 reconciliation

Recorded 2026-10-03T10:33:28Z. This new addendum preserves the completed arithmetic evidence package and every historical source/report unchanged. It selects no arithmetic reduction, numeric configuration, or statistical policy.

The exact historical CE4 record is **M-B p=.10 / preserved v1 p=.15**, with r=1 / r=2 and one degenerate replicate in each. Both its JSON keys and Markdown columns record that direction. The historical artifacts are consistent with the completed current decision evidence; no conflicting owner result was found for this case.

Read-only source checkpoint is `675d0d298fbaab5b8473ed048a561ef84e2f3e78`. Source identities:

- Historical scalar helper: Git blob `f2b2b1e53dfb70beee74baf0b34b178e6a20e0c3`, SHA-256 `403d662c1f8d4176bd3004e9ce0b5557f9c28e14a9ad308412d2b38995c7721b`.
- Historical JSON: Git blob `2cba1cc5d3f5b177e984291074193ee6eab3ba6c`, SHA-256 `e78ac3e735bd8c4683d536dc23cbba4ed422ac650008efb7eda54f7cb13d3b5b`.
- Historical Markdown: Git blob `62d8cd4c451325051a07b003a801d8454bff3b21`, SHA-256 `2157fd76c53d19132f7ea497ad473d81110f41dae9b4b75768d1a5de213e4a1c`.
- Preserved actual `superiority.py`: Git blob `8a1254d7b77514f6015dfff4af0e4a53f57f22af`, SHA-256 `c61268921e5a9147e90810747e9ab6cd2896dd2fab89cb314d390dc0ff760498`.

## Actual replay and smallest result impact

The historical helper's exact `mb_reference` AST was executed without changing its statements. Only its function was extracted; the surrounding script's search, machine-specific import path and file-writing code were not executed. The preserved production `studentized_cbb` was called directly with this same fixed synthetic input. Both used the actual Frozen C6 `circular_block_indices` function.

Input: `[-.016,-.007,.053,.023,.005]`, n=5/L=2/B=19/seed=200, all pre-existing synthetic evidence values. One fresh process each on CPython 3.11.16, 3.12.14 and 3.13.5 returned:

- Exact historical helper: **r=1, degenerate=1, p=.10**.
- Actual preserved v1: **r=2, degenerate=1, p=.15**.

For every runtime, the unique difference in replicate exceedance is **replicate 10 (one-based)**. Its Frozen C6 indices are `[1,2,1,2,3]`, sample `[-.007,.053,-.007,.053,.023]`, mean `.023`, and both full block sums `.046`. Both methods classify its variance as exactly zero, `0x0.0p+0`.

M-B's approved rule treats that degenerate replicate as a non-exceedance; historical v1 counts it as an exceedance. Consequently v1 adds exactly one to r and `.05` to p, using the same `(r+1)/(B+1)` denominator. There is no input, RNG, index, or variance-block-count difference: `ceil(5/2)-1 == floor(5/2) == 2`. Float grouping is not needed to explain this CE4 result difference. The other 18 exceedance decisions agree.

The new narrow replay reads the already-completed arithmetic replay files without modifying them. Those files confirm CE4 M-B p=.10 for fsum, actual builtin sum on every available runtime, and literal NumPy 2.3.5 on its supported runtimes. The literal Q1 S_plus1 p-hex check remains EXACT_P_HEX_MATCH for this case and 7/7 computable fixtures overall. NumPy 2.3.5/Python 3.13 remains NOT_RUN; no unsupported literal candidate was executed here.

## Classification and limits

The historical CE4 JSON/Markdown/helper are **HISTORICAL_REPRODUCED**, with correct M-B .10 / v1 .15 direction. The current arithmetic package is **CURRENT_SYNTHETIC_DIAGNOSTIC_RECONFIRMED**. These do not conflict for CE4.

The historical helper's phrase "exact scalar port" and the historical report's "only two differences" are understood as their analytic convention comparison and finite recorded counterexamples. The helper uses direct blocks and the interpreter's actual builtin sum, while the original Q1 simulation uses NumPy cumulative differences and NumPy reductions. They are not a universal assertion of binary floating transport equivalence. The completed arithmetic package separately records cases where those transports change degeneracy, ties and r. This limitation leaves the historical CE4 evidence intact and does not infer an approved arithmetic choice.

The raw outputs retain all 19 index/sample/mean/block/variance/statistic/exceedance rows with float hex, the exact historical records, the actual v1 result, source hashes, prior replay hashes and runtime details. `EXECUTION_COMMANDS.json` records the three executed commands; all exited 0 and stderr was empty. This task added no fixtures or repository tests and did not rerun the completed six-process arithmetic package or the whole repository suite. Whole repository regression and GitHub Actions: **NOT_RUN by this narrow reconciliation worker**.

The driver accepts explicit repository/prior-replay/output paths and uses `-B`/disabled bytecode writes. Reproduce to a new output path using `replay_exact_ce4.py --repository <repo-root> --prior-replay <matching-runtime-original-replay.json> --out <new-output.json>` with the matching interpreter.

Acceptance: exact old helper/current source identities checked; actual helper/v1 replay performed; unique replicate effect isolated; classifications and arithmetic limitations recorded. **4/4**. Authoritative v2 and its production oracle remain pending the arithmetic decision. CAL_VERIFY accesses 0; Holdout consumptions 0; numeric configuration choices 0; C8 Freeze 0; publication/grants 0; canonical merges 0.
