# TC-D3P-004 — C6 statistical experiment-family / resampling policy

Recorded 2026-09-30 KST. Status: PROPOSED / NOT APPROVED / NOT ACTIVE.
TC-D3P-003 v1 remains APPROVED; its execution implementation is separately verified.
No statistical method/result/threshold is invented or applied by this proposal.

## Verified unresolved decisions

EVL_SPEC_v0.1 §§5–6 requires PSR, DSR, PBO, bootstrap, multiple-testing-aware benchmarks
and Reality Check when required. The repository contains the requirements and method references,
but no registered C6 statistical family/resampling contract. C3 defines sample-SD Sharpe and
C5 retains failed/rejected/partial-rung attempts, but neither chooses how those attempts define a
DSR family or an aligned PBO matrix. C5 records aggregate metrics, not complete aligned return
series for every screening attempt. A partial-rung success is explicitly not complete candidate
evidence. Counting rungs as independent strategies, silently dropping failed attempts, filling
missing returns with zero, selecting favorable OOS columns or choosing a bootstrap after results
would change inference and can create false skill evidence.

This is a proposed reusable research inference policy, not a numeric promotion threshold.
C8 threshold calibration remains separate; no Official PASS is conferred by diagnostic statistics.
Stop is required by the user's explicit instruction for new result-impact policies.
C6 remains IMPLEMENTING / NOT FROZEN; C7–C10 remain NOT STARTED.

## Concrete approval option A: preregistered full-family diagnostic contract v1

1. Before inference, bind the complete candidate roster and all attempt IDs from append-only C1/C5,
   code/evaluator/data identities, partition/variant, return-series convention, method versions,
   benchmark/control identities, seed and all resampling dimensions. Reuse C2 retained partitions,
   immutable C4 predictions and hash-bound C6 execution reports. No fitting or selection during inference.
   Never include Holdout, cross-partition or invalidated evidence. Preserve rolling/expanding and
   primary/gap-stress results separately, without choosing the better variant.
2. Primary statistic is period-level Net-of-Trading-Cost Pre-Tax arithmetic risk-free excess
   Sharpe, with C3's sample-SD convention and explicit frequency. PSR reports against a preregistered
   reference Sharpe in period units; use the published PSR moment correction, no guessed reference.
   Missing variance/moments/sample support returns NOT_RUN/UNDEFINED, never zero or a PASS.
3. DSR reports two explicit trial-count sensitivity views: (a) distinct registered full candidate
   parameter/evaluator identities; (b) total charged ledger evaluation attempts, including screening,
   rejection and failure. Both counts and all statuses are disclosed. Neither is described as an
   empirically estimated effective independent-trial count. Use the published Gaussian expected-maximum
   Sharpe approximation with registered cross-candidate Sharpe variance from complete aligned eligible
   series; no variance inferred from missing/failed runs. Incomplete family support means NOT_RUN for
   the affected inference, not a smaller post-result family. No winner/Official choice from either view.
4. PBO uses a preregistered complete aligned candidate-return matrix, an explicitly supplied even
   CSCV block count S, all S-choose-S/2 train/complement partitions, and the same Sharpe score.
   CSCV is a diagnostic partition of already frozen research outcomes, not a replacement C2 training
   split and never a retuning input. Invalid/missing or zero-variance block scores fail closed.
   For tied in-sample maxima report each tied selection; use average OOS ranks and retain all tied
   outcomes. Declare the weighting rule in registration (equal weight to each partition, then equal
   weight among its tied maxima). PBO is the share whose OOS relative rank is below the median.
   Median equality is reported explicitly. No tie-breaking by favorable OOS return.
5. Bootstrap uses circular moving blocks with explicit positive block length L, replicate count B,
   seed and requested quantiles registered before outputs. Apply identical sampled time indices across
   every candidate and benchmark to preserve cross-sectional dependence. No IID independence claim,
   adaptive block-length selection or result-driven replicate extension. Report sensitivity lengths
   only if preregistered; retain all of them. Missing valid L/B/coverage means NOT_RUN.
6. White Reality Check is always reported for the preregistered eligible candidate family relative to
   the registered equal-weight/simple and market-cap baselines, using aligned net-return differentials,
   the maximum mean differential statistic and the same joint centered block resampling.
   Include no-trade/zero excess baseline only if explicitly registered upstream.
   Never replace the family with just the selected candidate. Statistical significance levels and
   economic materiality are not defaulted here; C8 must freeze its threshold contract before decisions.
7. Parameter/regime/universe perturbations, random ranking, randomized weights, equal-weight/simple
   and market-cap controls require explicit pre-result scenario definitions, upstream PIT snapshot refs,
   frozen evaluator identity and valid execution inputs. Parameter changes are confined to the approved
   cash_buffer/technical_lookback domains. No new QGV controls or investor weights; no Track A source
   artifact mutation. Incomplete upstream paths are NOT_RUN, not simulated skill evidence.
   Parameter drift has a registered coordinate/scale/time convention, with all raw values retained.
8. All diagnostic executions consume registered budget and retain terminal ledger statuses and report
   hashes. Failed/incomplete/invalidated families cannot support a full C6 robustness acceptance or C8
   promotion. All results are Pre-Tax; software fixtures are labeled synthetic. Statistical diagnostics
   do not on their own imply NO_EVIDENCE_OF_SKILL or skill; C8 applies its separately frozen
   indistinguishability/hard-gate contract. No automatic optimization or promotion.

Option A advantages: one reusable deterministic inference contract; dependence-aware joint resampling;
complete reporting; no hidden effective-count estimate or threshold default. Limitations: both DSR counts
are sensitivity assumptions rather than identified effective independence; aligned complete-family
requirements can yield NOT_RUN after screening; Sharpe-centric PBO does not capture every profile
objective; circular blocks still assume a locally stationary resampling interpretation.

## Alternative B: supply a different explicit methodology before implementation

User may specify an alternative primary return statistic/DSR effective-count estimator, CSCV ranking
and tie policy, stationary vs moving-block bootstrap, or the conditions making Reality Check mandatory.
Each alternative must include complete-family/missing-data handling and pre-result registration rules;
raw ledger completeness, PIT/Holdout isolation and no fabricated values remain locked.

Technical effects:
- Estimated effective trial counts can account for correlations but require a specified estimator,
  adequate paired series and new estimator uncertainty; raw counts can penalize correlated screening.
- Gross CAGR/PBO vs net-excess Sharpe changes the ranking/overfitting question and comparability.
- IID bootstrap is simpler but removes serial dependence; stationary bootstrap randomizes block lengths
  and requires its parameter and random-generation contract; moving blocks fix a supplied length.
- Conditional Reality Check reduces diagnostic runs but requires an objective preregistered trigger.
- Post-result family pruning invalidates multiple-testing interpretation and is not an allowed option.

No recommendation is made. Approving A means items 1–8 as written, with numerical L/B/S/quantiles/reference
Sharpe explicitly supplied by preregistration rather than invented defaults. Choosing B requires a concrete
revised proposal. Neither option authorizes a C7/C8 promotion threshold, synthetic Investor-QGV input,
Holdout consumption, core-score redesign or broker execution claim.
