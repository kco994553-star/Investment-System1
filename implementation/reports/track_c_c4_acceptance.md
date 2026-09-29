# C4 Walk-Forward — SOFTWARE FROZEN

Spec remains EVL_SPEC_v0.1; split policy remains approved EVL-SPLIT-01 v1.1.
Tested implementation: 0cb9a7c (upstream repair b1e3eff).

- PASS: preregistered experiment, split, runner, dataset digest, seed and code identity.
- PASS: annual 5Y/1Y/1Y rolling AND expanding orchestration; both primary and registered rebalance-gap stress retained, no winner selection.
- PASS: Train-only fitting, Validation-only threshold calibration, unchanged model/parameters during calibration, unchanged model/thresholds during OOS prediction. Prediction callback receives no outcome labels; metric evaluation follows prediction.
- PASS: integrated Technical/Macro/Portfolio/Integration fixture reaches C3's four Pre-Tax views. Changing OOS labels changes metrics but not fitted model or predictions.
- PASS: rejected/failed attempts recorded, budget checked before evaluation, duplicate identity blocked, interrupted-attempt journal recovered as FAILED. Reports are hash-bound from terminal Trial Ledger records.
- PASS: strict input-derived Technical/Macro lineage, future/missing/estimated metadata rejected. Legacy APIs retain existing decisions and unknown qualification.
- PASS: cash buffer changes exposure, technical lookback changes inputs/decisions, deadband changes order intents. Deadband is excluded from target-weight-return optimization without an execution model.
- targeted: 88/88. full: 484/484. normal merge integration against canonical b8e39a2: 484/484.

## Scope and boundaries

SOFTWARE acceptance only, not seven years of qualified real observations, full-year investment performance, proof of skill, Official profile, consumed Holdout or Forward validation. Sparse synthetic fixtures exercise orchestration; real data acceptance must separately establish coverage, source/vintage and all upstream eligibility. Callbacks are trusted versioned code, not a security sandbox; callers must bind predictor features to verified provenance. C5 search inside a fit hook requires its own complete C1 ledger. C8 must verify report digests and upstream invalidations before using any evidence.

The user's 2026-09-29 continuation authorized repair of the former upstream blocker. Additive changes outside EVL are limited to contracts/lineage.py, contracts/models.py, technical/engine.py and macro/engine.py. Existing core formulas are preserved; the previous claim of zero upstream file changes no longer applies. QGV, Track A evidence and B/D/E code are unchanged.

C5 may search executable cash_buffer and technical_lookback settings. risk_multiplier, signal_threshold and macro_warning_sensitivity remain unbound/fail-closed; no new financial meaning is inferred from their provisional profile numbers. Stages without eligible controls must be explicitly reported, not simulated as distinct strategies. No new D3-P has been introduced by this software repair.
