# EVL-SPLIT-01 v1.1 — APPROVED

Decision: TC-D3P-001, user approval 2026-09-28 20:48:39 KST:
“그래 승인해. 계속 진행”. Approval refers to the immediately preceding revised
recommendation, not the superseded mandatory extra-gap proposal v1.0.

## Binding rules

- Preserve nominal Train 5Y / Validation 1Y / OOS 1Y; annual rolling and expanding
  comparison. New intervals are half-open; C0 inclusive intervals need an explicit
  microsecond-resolution adapter, never silent reinterpretation.
- Primary: exclude fitting/calibration observations unless label_end and
  label_available_at are strictly before the next evaluation boundary. Feature
  inputs require available_at <= decision_time with provenance/vintage.
- Stress: report a separate, preregistered variant that additionally moves each
  fitting cutoff to the immediately preceding registered rebalance timestamp.
  Never choose between primary/stress based on realized performance.
- Record maximum label horizon, actual rebalance schedule, both variants, retained
  and excluded IDs/reasons, effective sample counts and data/spec hashes before
  using results. No month=30-day or trading-day=calendar-day substitution.
- Unknown metadata fails closed. Empty required partitions are insufficient data,
  never PASS. No unsupported minimum sample/significance threshold is invented.
- Final Holdout is excluded from research splitting; no retrospective Track A
  exception, tax change, Official promotion or upstream score mutation is granted.
- Differences between primary/stress results must be retained; any statistical
  pass/fail standard belongs to preregistered C6, not result-driven C2 tuning.
- Later applications of this exact approved rule are autonomous D3-C. Changes to
  these general semantics require a new D3-P. Original v1.0 remains historical.

For boundary B=2020-02-01, preceding registered rebalance=2020-01-01:
label_end/publication Jan 15 qualifies for primary but not stress; Jan 1 equality
is excluded from stress; Feb 1 equality is excluded from both. Features available
exactly at their decision timestamp remain eligible under the locked <= rule.

Software acceptance does not establish real-data coverage, statistical skill or
an Official profile. C0/C1 are preserved and EVL_SPEC_v0.1 is not rewritten.
