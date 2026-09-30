# C6 execution implementation — IMPLEMENTING / NOT FROZEN

Recorded 2026-09-30 KST. TC-D3P-003 v1 explicitly APPROVED at 2026-09-30 19:38:07 KST.
This is the approved execution subsection of C6, not complete C6 Robustness/Statistics.

Implementation: evl/execution.py, additive to unchanged C0–C5.
- Immutable experiment/split/input/plan registration, fixed six delay × cost scenarios.
- Explicit frozen upstream order quantities/source references. No invented target-weight sizing.
- Baseline first eligible registered opportunity strictly after decision; delay next eligible opportunity.
- Missing chosen-slot quote fails closed; never skip to a later best price.
- Full-fill cash and position reconciliation, opening/closing marks and actual gross P&L.
- Costs explicitly evidenced and separated from components embedded in price.
- Fixed-path 1x/2x/3x changes only the monetary cost fraction; gross P&L, fills and opening equity retained.
- Source/vintage/availability/timezone/estimated/synthetic qualification checks.
- Execution outcome evidence can be later than decision, only available by evaluation; no prediction callback receives it.
- C3 evaluator wiring preserves all four Pre-Tax views.
- C2 retained partition validation rejects mixed Train/Validation/OOS and Holdout/crossing/future features.
- Ledger budget, rejection/failure, interrupted-attempt recovery, report hash and invalidation reuse C1/C4 primitives.
- No short, simultaneous-fill priority, partial-fill, retry/cancel, capacity, auction or impact model invented.
- Software fixtures remain labeled synthetic. No broker accuracy, skill, robustness PASS, promotion or real-data coverage claim.

Phase status remains IMPLEMENTING until the entire C6 EVL_SPEC §§5–6 statistics, perturbation,
negative-control, drift and multiple-testing acceptance is completed. Execution acceptance alone cannot freeze C6.
Targeted/full tests and CI must be recorded from the implementation commit before acceptance.

Cross-track: this commit adds only Track C source, test and report; authorized upstream repair unchanged;
Track A frozen evidence and Track B/D/E/Web untouched. Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT.
