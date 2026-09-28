# C3 Metrics — SOFTWARE FROZEN

Contract: EVL_SPEC_v0.1 §§7–9; formulas/conventions in track_c_c3_metric_conventions.md.
No new D3-P, numeric promotion threshold, upstream score or tax policy change.

- PASS: distinct Gross / Net-of-Trading-Cost / Real / Risk-Free Excess Pre-Tax views.
- PASS: CAGR, sample-SD Sharpe, downside-RMS Sortino, Calmar, initial-wealth MDD,
  drawdown duration/censoring, downside capture, discrete tail return and turnover.
- PASS: explicit frequency/currency and continuous period alignment; finite inputs.
- PASS: missing/undefined denominators produce None; returns below -100% are rejected.
- PASS: risk-free inputs PIT at period start; outcome/inflation publication by
  evaluation time; vintage/source identity retained; inflation is ex-post attribution.
- PASS: hand-calculated and metamorphic cost-stress checks; no new dependency.
- Targeted C0–C3: 56/56 PASS; full: 452/452 PASS; normal-merge integration: 452/452 PASS.
- Canonical b8e39a2 unchanged; Track A/B/D/E runtime/data/spec changes = 0.

Logs: track_c_c3_targeted.txt, track_c_c3_full.txt, track_c_c3_integration.txt.
This is software acceptance only. No production dataset qualification, Official
profile, statistical skill, calibrated gate or Forward Validation is claimed.

## Next phase boundary

C4 is BLOCKED_UPSTREAM_CONTRACT; C4–C10 are not implemented/frozen. Readiness
inspection is NOT a substitute for C4 acceptance. Existing TechnicalSnapshot
lacks available_at/source-vintage binding, and TechnicalEngine consumes an
untimestamped return list. Do not manufacture available_at from as_of.

For C5 readiness, six CONFIGURABLE_KEYS have no direct consumers outside their
strategy contract. IntegrationEngine takes profile_id/parameter_set_hash only as
metadata; a test varying those fields leaves target weights unchanged. A separate
fixture halves ProvisionalPolicy.rm_default but normalization leaves target
weights unchanged (max absolute delta 0). These results identify the tested
boundaries; they do not assert that every possible strategy/risk parameter is inert.

Existing conflicts C-28 and C-30 remain upstream items. EVL_SPEC_v0.1 §13 requires
reporting an existing SSoT/architecture conflict instead of inferring a replacement.
Track C does not rewrite Technical, Macro, Integration or QGV core contracts.
Required upstream deliverables: input-derived Technical PIT lineage, a timestamped
integrated evaluator with adequate registered window coverage, and behaviorally
verified parameter bindings before C5 search. No additional user policy approval
is requested or inferred. Details: track_c_c4_upstream_readiness.json.
