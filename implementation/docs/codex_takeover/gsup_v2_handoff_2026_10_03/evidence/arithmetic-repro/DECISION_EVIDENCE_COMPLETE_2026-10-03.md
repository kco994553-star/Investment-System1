# G-SUP arithmetic reduction — completed decision evidence

Recorded at 2026-10-03T10:23:59Z. Status: **EVIDENCE_COMPLETE / USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION**. No candidate is selected, recommended as an approval, installed as a method, or used to rewrite a v1 result. This is an additive synthetic diagnostic, with zero new fixture definitions and zero new repository test cases.

Source checkpoint: PR #31, `codex/track-c-gsup-v2-2026-10-03`, exact `675d0d298fbaab5b8473ed048a561ef84e2f3e78`; integration base/merge-base `86ad3628dd5c62c6d873e42511e577f24f4fb588`; read-only owner `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`; canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. These are source bindings, not claims that the new evidence already exists at those commits.

## Authority and exact source identity

The historical Q1/M-B proposal is a historical method-selection package. Its applicable index and statistic conventions are retained under the later explicit M approval, recorded in the approval JSON. The package's original PROPOSED/NOT APPROVED heading does not supersede that later explicit approval. The M choice remains approved; the result-changing arithmetic choice remains unapproved under the current user instruction.

- M-B/Q1 package: `implementation/reports/track_c_c8_a6_method_decision_package_2026-10-02.md`, Git blob `54872fdf13a66d848772bb62dfdb2f7138170fb6`; SHA-256 `b98c35420b529e4b9b02e429115ff0cd6c24339de01af074f6731b3264656042`.
- Original NumPy simulation: `implementation/reports/track_c_c8_a6_method_simulation_source_2026-10-02.py`, Git blob `e112f41f34d4ead287699657750875770b4c4705`; SHA-256 `c1f56a3f709c5fed65336fb5f33473f957c8caad706bfc4e48534ca3161f34ce`.
- Explicit M-v2/source-descriptor approval: Git blob `a5279d516c028f0a8cb9166ee2d54366da00877b`; SHA-256 `0fc8ed2b55b3aba4cf566f0e7c9e7146324ae4aec5e22c307fd9a9a8ae9991d8`.
- Frozen C6 source: `statistical_kernels.py`, Git blob `28e1c1842625bacabc6ffc9c9b172261e7d6585a`; SHA-256 `61f70937456d8a54cb027a7522f2a2d1c890bccc92f9f19de28082a2001e12d1`.
- Preserved v1 source: `superiority.py`, Git blob `8a1254d7b77514f6015dfff4af0e4a53f57f22af`; SHA-256 `c61268921e5a9147e90810747e9ab6cd2896dd2fab89cb314d390dc0ff760498`.
- Existing diagnostic source: `gsup_mb_reduction_diagnostic.py`, Git blob `5baa1adb6db32f0f1f8ff3f0dffbfd34e9086571`; SHA-256 `b793a1e76d2a4dbe5f79152a04b18ebe0aa5006f0efd2e1542fc720b701ab3d5`.

Every fresh process checked the pinned source blob identities before replay. The full bound-source list, including the preserved counterexample sources, appears in each raw replay and `COMPARISON_RESULTS.json`.

## What was actually executed

Six fresh processes replayed the same nine already-published synthetic fixtures: two processes each on CPython **3.11.16 / NumPy 2.3.5**, CPython **3.12.14 / NumPy 2.3.5**, and CPython **3.13.5 / NumPy 2.2.4**. The literal NumPy 2.3.5 candidate is **NOT_RUN on 3.13** because that version is not installed for that interpreter. NumPy 2.2.4 was not substituted into the candidate. No packages or network resources were fetched.

Every process compared an independent PythonRandom index construction with the exact read-only Frozen C6 function: 44 explicit n/L combinations × four seeds, or **176 combinations per process**, plus all nine fixture streams. The grid output digest is identical across all six processes: `679f4fc26848fda68b65890e8dc4bf94b99ca01f8ff8be9b3f7a4b0eb7a7e34b`. Synthetic B/L/seed values are the pre-existing fixture values, not actual numeric configuration or defaults.

All candidates retain the approved M-B original statistic, first `ceil(n/L)-1` replicate variance blocks, at least two such blocks, denominator `(ceil(n/L)-1)*L`, `>=` equality ties, degenerate non-exceedance, and `(r+1)/(B+1)`. No tolerance, quantization, epsilon, new threshold, alternative denominator, or excluded replicate is introduced. Undefined original statistics remain fail-closed NOT_RUN.

For the literal candidate, the driver also executes the pinned original `run()` statements through creation of `out`, removes only the unused subsequent M-C/BM_t alternative, and supplies exactly the Frozen C6 starts to the source's `rng.integers` interface. It does not rewrite any S_plus1 expression. Literal S_plus1 p-value hex matches the diagnostic exactly in **7/7 computable fixtures on both supported runtimes**. The two non-computable boundaries are recorded explicitly: insufficient blocks transport NaN in the original simulation; an undefined original statistic transports a raw .05 after NaN comparisons in that exploratory script. The diagnostic instead fails closed, as required by the preserved G-SUP boundary. This is not a claim that the entire exploratory simulation script is a production contract.

Every result includes float `repr` and `float.hex()` for inputs, observed statistics, circular block sums, replicate means, block sums, variances, and statistics. Integer exceedance, tie, and degenerate counts, p-value hex, exact index streams, library configuration, interpreter/compiler/platform/libc and binary-module SHA-256 values are retained. Candidate digests exclude the reduction label and compare the actual numerical payload.

## Reproducibility observed

Each runtime's two complete raw output files is byte-identical: **3/3 process pairs**. This establishes fresh-process reproducibility for these exact runtimes, fixture cases and host, with Linux x86_64/glibc 2.41. It does not establish arbitrary-platform, future-version or whole-distribution equivalence.

- CPython 3.11.16 / NumPy 2.3.5: complete output SHA-256 `ab9e39f1954f19ef04ac211e4ae1a9d88f450aa05962811d5b533edc6fe32d6e`; canonical numeric digest `89f42083caa6bfa030695fb8ca06f2c467f5ae7ff7bbbf91236b164c2824df7b`.
- CPython 3.12.14 / NumPy 2.3.5: complete output SHA-256 `f95d7515ed924d8a4c994e9125436b39cf5196cf45ee06bbd8e4bee9d2052bb1`; canonical numeric digest `2e773f6fbc5d715de368bd11066fbc58126bca5afdbe96788f3b36aba0e25fa1`.
- CPython 3.13.5 / installed NumPy 2.2.4: complete output SHA-256 `0c1cf30d3a0a7f32bba0f8c52ffe42058f46af78d5d6046469c1f0894b181be5`; canonical numeric digest `a26158485dfd0f6e865089824e378163dbe5a65f6ddaed0b7f7db3d48d9f5e73`. The unsupported literal candidate is represented as NOT_RUN.

Within a candidate, `math.fsum` and the explicit Python 3.11 left-sum reconstruction have **9/9 exact numerical payload matches across all three Python runtimes**. Literal NumPy 2.3.5 has **9/9 exact numerical payload matches between 3.11 and 3.12**. Actual builtin sum has only **2/9 exact numerical payload matches between 3.11 and either 3.12 or 3.13**: those two are NOT_RUN fixtures; every computable full trace differs. Actual builtin sum on 3.12 and 3.13 has 9/9 matches for these cases.

## Result-changing counterexamples

Counts are `(r, ties, degenerate; p)`; all use identical Frozen C6 indices. All numbers below are synthetic evidence only.

- `ARITHMETIC_NUMPY_FLIP`: `[.01,.01,-.01,-.02,.02,.01,.01,.01]`, n=8/L=3/B=19/seed=46. Literal NumPy 2.3.5 gives **(3,0,0; .20)**; fsum and actual builtin sum on each tested runtime give **(1,0,2; .10)**. Replicates 6 and 12 have fsum variance exactly `0x0.0p+0`, versus literal variances `0x1.5555555555555p-119` and `0x1.5555555555555p-117`. Both literal replicates are nondegenerate exceedances. Delta: **r +2**, degenerate **−2**, p **+.10**. The degenerate rule is the same; the arithmetic determines whether its predicate is true.
- `ARITHMETIC_LEFT_SUM`: `[-.02,.01,.02,0,.01,.01,.01,-.01,.01]`, n=9/L=4/B=19/seed=34. Actual builtin sum on **3.11** gives **(7,0,0; .40)**. Literal NumPy 2.3.5, fsum, and actual builtin sum on **3.12/3.13** give **(6,0,1; .35)**. Replicate 13 has fsum zero variance versus 3.11 builtin variance `0x1.0000000000000p-116`. Delta from fsum to 3.11 builtin: **r +1**, degenerate **−1**, p **+.05**.
- `ARITHMETIC_TIE`: `[.02,0,-.02,-.01,.01,0]`, n=6/L=2/B=19/seed=72. Literal NumPy 2.3.5, fsum and actual builtin sum on 3.12/3.13 give **(8,3,2; .45)**; actual builtin sum on 3.11 gives **(7,1,2; .40)**. The observed statistic is zero for all. Replicate 11 is an exact fsum equality tie, but its 3.11 builtin statistic is `-0x1.241e62f2d89f7p-54`; it becomes a non-exceedance. Delta from fsum to 3.11 builtin: **r −1**, ties **−2**, p **−.05**. No equality rule was changed.

The five original method-comparison fixtures also ran: CE1 is NOT_RUN for M-B; CE2=.05, CE3=.05, CE4=.10, and CE5=.30 under every available candidate. The CE2 degenerate count still differs: one under scalar candidates, zero under literal NumPy. Equal p-values do not imply identical variance transport. `UNDEFINED_ORIGINAL` is fail-closed NOT_RUN under every available candidate.

## Neutral candidate comparison

**Literal NumPy 2.3.5 cumulative formula.** This preserves the original simulation's operation structure: cumulative sum and subtraction for block sums, NumPy mean for the original mean, sums of full block sums plus the final partial block for the replicate mean, and NumPy reduction for squared block deviations. It matches the read-only extracted original S_plus1 expressions on the seven computable fixtures. Its rounded intermediate values differ from scalar direct-block addition and can change degeneracy and r. The historical simulation did not record a NumPy version, so current 2.3.5 reproduction cannot prove historical bitwise identity. NumPy version, dtype, operation ordering and runtime/platform must be explicit in any future choice; unsupported runtimes must not silently fall back.

**`math.fsum`.** This preserves the analytic M-B statistic/block/variance/tie convention while summing the scalar observations and direct blocks with fsum. It follows the existing scalar diagnostic and v1 arithmetic transport, with the approved M-B block and degenerate rules applied separately. The original simulation uses cumulative block subtraction and NumPy reductions, so fsum is not its literal numerical transport. Nine-fixture cross-runtime repeatability is observed; universal compatibility with the simulation is refuted by the fixed NumPy-flip example. This option does not authorize rewriting v1 outputs.

**Actual Python builtin `sum`.** This also preserves the analytic M-B conventions, using the interpreter's actual builtin for the scalar reductions. It is not a single numerical convention without an explicit interpreter identity. On these fixtures the actual 3.11 builtin exactly matches the separately named left-sum reconstruction; the actual 3.12 and 3.13 builtins exactly match fsum's nine numerical payloads. Those finite-case observations do not prove a universal equality to either algorithm. The synthetic cancellation probe `[-2e16,1.0,2e16]` gives actual builtin **0.0 on 3.11**, **1.0 on 3.12/3.13**, explicit left reconstruction **0.0 on every runtime**, and fsum **1.0 on every runtime**. Labeling the old left_sum function as the builtin on newer Python would be inaccurate.

Selecting the reduction therefore requires a user decision, including the relevant runtime/library identity. The evidence does not add a rounding or tolerance option, a new policy default, or a statistical preference. The existing M approval and profile/role grouping remain unchanged.

## Reproduction and completion boundary

`EXECUTION_COMMANDS.json` records all six actual invocations and exit code 0, with stdout/stderr preserved. The executed driver is portable: its source accepts explicit `--repository` and `--out` arguments, and it imports only the pinned diagnostic at that repository path. Reproduce using a new writable output path, for example:

```bash
python -B <archived-evidence>/replay_arithmetic_candidates.py --repository <repository-root> --out <new-synthetic-output.json>
python -B <archived-evidence>/compare_replays.py
```

The comparison command reads the six archived replay files and regenerates its comparison output, so run it on a copy to preserve the committed evidence. It is not a statistical method execution. `compare_replays.py` exited 0; `COMPARISON_RESULTS.json` SHA-256 is `5ef3031e0b96a6b7c2e3b10bdea9640aff8b70b073ed703cb74f27a556a0132a`. The exact executed replay driver SHA-256 is `908085730799a76bf86fc5a43cbc43343445b72a83702a489a3675e7c080d4ec`.

Acceptance: pinned original authority/provenance complete; three candidate transports and separate left reconstruction replayed; two fresh processes per available runtime with full hex/digests/counts complete; neutral source/numeric/reproducibility comparison and limitations complete. **4/4 decision-evidence criteria**. Authoritative v2 implementation and production-kernel independent oracle: **NOT_IMPLEMENTED / NOT_RUN pending arithmetic decision**. Whole repository regression and GitHub Actions: **NOT_RUN by this diagnostic worker**, tracked separately by the primary writer. New repository tests **+0**, fixture definitions **+0**, capability maturity **Δ0**.

CAL_VERIFY accesses **0**, Holdout consumptions **0**, actual numeric configuration choices **0**, C8 Freeze **0**, publication/grants **0**, canonical merges **0**. Original source, tests, historical evidence, approval record and v1 results are read-only and unchanged by this task. Evidence handoff is ready; the unresolved arithmetic decision remains visible.
