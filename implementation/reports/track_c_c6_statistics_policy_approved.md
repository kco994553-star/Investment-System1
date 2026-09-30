# TC-D3P-004 A — APPROVED

Approval recorded at actual current clock: 2026-09-30T20:16:28+09:00 (KST / UTC+9).
User explicitly approved option A items 1–8 unchanged.
Approved proposal Git blob: 3e86579cd45c98cf44811d6aeab00b9dc8a42ecf.
Approved source HEAD: 34d9c3d127eb02f73cb19a0447aadd39828b8e75.
Scope: C6 statistical experiment-family and resampling methods; no C7/C8 threshold
default, promotion permission or Holdout consumption.

## User constraints attached to approval

- Complete candidate family; no post-selection shrinking.
- Approved Net-of-Trading-Cost Pre-Tax arithmetic risk-free excess Sharpe.
- Both DSR trial-count sensitivity views with independent count provenance.
- Full-family CSCV/PBO, joint circular-block bootstrap and full-family Reality Check.
- No invented/interpolated aligned evidence.
- Insufficient diagnostic evidence is NOT_RUN, never PASS.
- Diagnostic outcomes must explicitly distinguish PASS / FAIL / NOT_RUN.
- C6 Freeze requires an authoritative MANDATORY / ADVISORY classification.
- MANDATORY + evidence-insufficient NOT_RUN blocks C6 SOFTWARE FROZEN.
- ADVISORY NOT_RUN requires reason, missing evidence and impact scope.
- If classification requires a new result-impact policy, stop at the D3-P approval boundary.

This approval supersedes the proposal's historical NOT APPROVED status, but does
not itself execute diagnostics or declare C6 frozen.

## Preserved approved option A items 1–8

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



## Implementation boundary

Approved mathematical methods are unchanged. Diagnostic status semantics, complete
Freeze-role mapping and Freeze-evidence scope require reconciliation before a
C6 acceptance evaluator can treat any method output as PASS. See
track_c_c6_freeze_policy_proposal.md (TC-D3P-005, NOT APPROVED).
