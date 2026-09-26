# Investment-System1 · Experiment & Validation Layer Specification v0.1

Contract ID: `EVL_SPEC_v0.1`

Short name: Track C / EVL v0.1

Status: **DESIGN FROZEN / IMPLEMENTATION NOT STARTED**

Registered: 2026-09-27 KST

Authority: additive to the existing Investment-System1 SSoT; it does not replace Track A, Track B, QGV, Technical,
Macro, Portfolio/Risk, Simulation, Leaderboard, or Track Record contracts.

## 1. Track C 공식 정의

Track C owns PIT experiment design, validation, integrated-profile evaluation, and Promotion decisions for the
Aggressive / Balanced / Defensive profiles. It consumes, but never redefines, QGV, Technical, Macro, Portfolio/Risk,
Universe, or provenance contracts.

Ownership boundary:

- Track A owns REAL-DATA, PIT Universe, source provenance/vintage, Official snapshots, and invalidation of those inputs.
- Track C owns Experiment/Validation lineage and Official integrated-profile promotion.
- Track B consumes Track C Official profiles; it does not promote them.
- Existing QGV profile definitions and core scores remain upstream inputs. Track C profile promotion does not mutate them.

Implementation is gated on a Track A REAL-DATA baseline Freeze. The current Track A state has only two corrected Official
dates and is not frozen, so no Track C implementation phase is open.

## 2. Locked Rules

The following cannot be relaxed by a parameter search, profile, Custom strategy, or Promotion decision:

- PIT Universe.
- `available_at <= decision_time`.
- No look-ahead.
- Source provenance and vintage.
- Complete append-only Trial Ledger.
- Final Holdout isolation.
- Official / Custom isolation.
- QGV / Technical / Macro core-score immutability.
- Promotion Gate integrity.
- Upstream invalidation propagation.
- Tax exclusion from all Official results.
- Fail-closed handling of material uncertainty.

## 3. Dataset / Walk-Forward

Lifecycle:

`Development → Calibration → Final Holdout → Live Forward`

- Development: parameter research is allowed under the registered search contract.
- Calibration: threshold-only calibration; model/parameter research is closed.
- Final Holdout: no parameter or threshold changes.
- Live Forward: real-time validation after promotion.

Baseline split is `Train 5Y + Validation 1Y + OOS Test 1Y`. Rolling and Expanding forms must both be compared.
Re-optimization cadence is annual. Purge and Embargo are derived from the label horizon and rebalance interval rather
than chosen after results are observed.

## 4. Parameter Explosion / Search

Every run pre-registers:

- `ExperimentSpec`
- `ParameterSpace`
- `SearchBudget`
- `DatasetSplit`
- `MetricSet`
- seed
- code hash
- data hash/vintage

Search order is:

`Baseline → QGV → Technical → Macro → Integration → Portfolio/Risk → Interaction`

The first implementation uses constrained coarse/grid search. Search applies Coarse → Refine, Early Reject,
Successive Filtering, Search Budget, Complexity Budget, and weight-precision limits.

Candidate selection order is:

`Pareto Frontier → Stable Plateau → Low Complexity → Low Drift → Representative Center`

Choose the plateau rather than the peak.

## 5. Trial Ledger / Overfitting

The Trial Ledger is append-only and records every success, rejected, early-stopped, failed, and invalidated trial.
Unlogged trials cannot support Promotion.

Statistical controls include:

- Probabilistic Sharpe Ratio.
- Deflated Sharpe Ratio.
- Probability of Backtest Overfitting.
- Bootstrap analysis.
- Multiple-testing-aware benchmark tests, including a Reality Check family test when required.

## 6. Robustness / Controls

Required robustness checks:

- Parameter perturbation.
- Trading-cost stress at 1x / 2x / 3x.
- Execution delay.
- Regime perturbation.
- Universe perturbation.
- Bootstrap.
- Parameter drift.

Negative controls include random ranking, randomized weights, equal-weight/simple baseline, and market-cap baseline.
An indistinguishable result is recorded as `NO_EVIDENCE_OF_SKILL`; it is not promoted.

## 7. Risk-Free / Economic Value

Preserve these distinct result views:

- Gross Pre-Tax.
- Net-of-Trading-Cost Pre-Tax.
- Real Pre-Tax.
- Risk-Free Excess Pre-Tax.

Risk-free inputs remain PIT data with provenance, vintage, and `available_at`.

Economic Value Gate order:

`nominal positive → real positive → risk-free excess → required risk premium → benchmark opportunity cost → risk-adjusted return`

## 8. Tax Policy — LOCKED

`TAX_MODE = EXCLUDED`

All Official analysis, backtests, Promotion, and Forward Validation are Pre-Tax. Tax engine, tax-lot optimization,
tax-loss harvesting, and an after-tax Official score are out of scope. Track B must not infer an after-tax Official
profile from Track C outputs.

## 9. Profiles

All three profiles use the same Candidate Landscape.

- Aggressive: long-term excess CAGR centered, with hard constraints for MDD, tail risk, required risk premium,
  turnover, and OOS behavior.
- Balanced: balance of CAGR, Sharpe, Sortino, Calmar, MDD, OOS consistency, and risk premium.
- Defensive: MDD, downside capture, recovery, Sortino, real return, and risk-free excess centered, with a minimum
  growth requirement.

If profile candidates are not distinct OOS, record `PROFILE_NOT_DISTINCT`.

## 10. Threshold / Promotion / Holdout

Threshold classes:

- Universal.
- Statistical.
- Economic.

Universal thresholds are not calibrated. Statistical and Economic thresholds follow:

`Candidate range → Coarse grid → Sensitivity → Stable plateau → Rounded value → Freeze`

A hard-gate failure cannot be offset by higher return.

State machine:

`DRAFT → RESEARCH → CANDIDATE → VALIDATED → FROZEN → HOLDOUT_TESTED → OFFICIAL → FORWARD_MONITORED → FORWARD_VALIDATED`

Exceptional terminal/reopen states are `REJECTED`, `RESEARCH_REOPENED`, and `INVALIDATED`.

The Final Holdout is isolated from the research optimizer and can be consumed once. Consumption sets
`HOLDOUT_CONSUMED=true`. A failed Holdout is not reused for tuning.

## 11. Champion / Invalidation / Ownership

Each profile has one Champion and one Challenger. There is no automatic re-optimization and no automatic promotion.

Required lineage:

`Dataset → Experiment → WalkForward → Robustness → ProfileCandidate → OfficialProfile`

An invalidated Track A dataset, Universe, source, or Official snapshot propagates to dependent Track C artifacts as
`SUSPENDED` or `INVALIDATED`; downstream results cannot remain Official.

A Freeze Manifest is required for a frozen/promotion artifact and must bind the selected candidate to the registered
spec, lineage, code/data hashes, dataset vintage, parameters/thresholds, profile, Holdout-consumption state, and
Promotion state. The concrete serialization belongs to C0 Contracts and is not implemented by this design registration.

## 12. Official / Custom / Complexity

- Track C owns Official integrated profiles.
- Custom strategies are isolated namespaces and cannot mutate Official profiles, Trial Ledger, Track Record, or scores.
- Core QGV / Technical / Macro scores are immutable inputs.
- An extra parameter, rule, or interaction requires added OOS evidence.
- When performance differences are not meaningful, select the simpler candidate.

## 13. Track C 구현 순서

Implementation remains closed until Track A REAL-DATA baseline Freeze.

`C0 Contracts → C1 Experiment Ledger → C2 Dataset Split/PIT Guard → C3 Metrics → C4 Walk-Forward → C5 Search → C6 Robustness/Statistics → C7 Profile Selection → C8 Promotion Gate → C9 Holdout Runner → C10 Forward Monitor`

Stop and report rather than infer when:

- an existing SSoT or architecture-level conflict is found;
- Track B P1+ implementation appears necessary;
- Track A REAL-DATA priority would be displaced.

## Design Freeze Acceptance

- Contract registered under `EVL_SPEC_v0.1`.
- All Locked Rules above are binding.
- Track A / B / C ownership is separated.
- No Track C code, experiment result, Official profile, or Freeze Manifest is claimed by this document.
- Status remains **DESIGN FROZEN / IMPLEMENTATION NOT STARTED** until the Track A dependency is satisfied.
