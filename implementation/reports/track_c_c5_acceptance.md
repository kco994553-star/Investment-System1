# C5 constrained search — acceptance record

Policy TC-D3P-002 approved by user “어 진행해”, 2026-09-29 19:19:50 KST.
Scope: cash_buffer and technical_lookback; other stages/controls remain explicitly
fixed/unsupported as approved. EVL_SPEC_v0.1 and phase order unchanged.

Acceptance implemented and targeted-verified:
- Immutable hash-bound preregistration: experiment, split, train dataset, baseline,
  coarse/fine domains, screening resource sizes/cutoffs, metric directions,
  evaluator identity, seed, code/data identity and primary/stress variant.
- Only the selected variant's retained Train samples enter search. Validation,
  OOS, Holdout, future features, changed data/config or unsupported controls fail closed.
- Mandated seven-stage order; QGV/Macro/Integration explicitly report
  NO_ELIGIBLE_BOUND_PARAMETER; no metadata-only pseudo-strategy trials.
- Constrained Coarse -> Refine around every surviving coarse point, not a peak;
  deterministic deduplication and reproducibility. Fine grid is preregistered.
- Increasing training-prefix resource levels with fixed successive screening;
  complexity counts departures from registered baseline, precision uses decimal
  cash-weight places. Violations reject before callback execution.
- Budget checked before every evaluation/rejection; all screening evaluations
  count as attempts. Failed/early-stopped/rejected trials and pending crash
  recovery use existing C1/C4 accounting. No silent resampling/restart.
- Actual integrated engine evaluation changes results for approved controls.
- Full-resource survivors returned without champion/plateau selection (C7 owns it).
  Partial-rung SUCCESS is not complete-candidate evidence; report marks this explicitly.

Trusted versioned callbacks are not a security sandbox. Software/fixture evidence
only, no qualified real-data experiment, skill, Official profile, Holdout or Forward
claim. Costs/execution/robustness are not implied by target-weight performance.
Final regression counts and freeze state are recorded in track_c_c5_evidence.json.
C6 preflight identifies a new execution-policy decision: TC-D3P-003.

Final status: SOFTWARE FROZEN at 2026-09-29T19:27:45.256043+09:00. Targeted 103/103; full 499/499; normal-merge integration 499/499 PASS.
