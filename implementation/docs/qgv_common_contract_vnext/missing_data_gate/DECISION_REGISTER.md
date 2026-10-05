# QGV Missing-Data scoped Decision Register

**Proposal record only. No production policy is approved or active.**

This additive register subdivides the existing local QCC-P01 proposal. It does
not rename global CDR decisions, change Context AP1–AP3, or edit Frozen records.
QCC-P02 is referenced for validation/PIT admission. Date: 2026-10-05 KST.

| Local proposal ID | Policy surface | Recommendation | Class if adopted for production semantics | Status |
|---|---|---|---|---|
| QCC-P01.M1 | Requiredness / applicability | Pin economic applicability separately from method-requiredness and weight; unresolved binding blocks new admission | D3-P / current equivalent | PROPOSED / NOT_APPROVED / INACTIVE |
| QCC-P01.M2 | Missing reason / scoped admission | Ordinary absence differs from relevant PIT/integrity/config failure; guards precede weight and preserve lineage | D3-P / current equivalent; QCC-P02 dependency | PROPOSED / NOT_APPROVED / INACTIVE |
| QCC-P01.M3 | Denominator | Only proven N/A changes planned applicable basis; ordinary missing never triggers available-only reweight | D3-P / current equivalent | PROPOSED / NOT_APPROVED / INACTIVE |
| QCC-P01.M4 | Partial / complete / rank validity | Partial contribution is diagnostic; complete applicable active and method-required evidence precedes new comparable/rank eligibility | D3-P / current equivalent | PROPOSED / NOT_APPROVED / INACTIVE |
| QCC-P01.M5 | Zero weight / isolation | Contribution exclusion does not waive method-requiredness or related/shared PIT/integrity; no Official validity mutation | D3-P / current equivalent | PROPOSED / NOT_APPROVED / INACTIVE |

Source: [DECISION_PACKAGE.md](DECISION_PACKAGE.md), [POLICY_COMPARISON.md](POLICY_COMPARISON.md),
[CURRENT_BEHAVIOR.md](CURRENT_BEHAVIOR.md), [SIMULATION.md](SIMULATION.md).

## Append-only event — 2026-10-05

- User authorized Phase B audit, inactive alternatives, synthetic/golden impact
  illustration, minimum decision surface, recommendation and scoped Handoff.
- PR #44 and both recorded Actions are verified at exact published HEAD
  `cb1906b207623168fd70f3dcdb5b30f2d82d807d`; publication authority does not approve
  these Missing-Data proposals.
- Work recommends M1–M5 as an enumerated guarded-Hybrid design bundle.
- No user selection/approval of M1–M5 is present in this task.
- New role tables, predicates, quality rubrics, numeric thresholds/defaults,
  production implementation, migration, Official/ranking/publication promotion,
  Holdout, canonical and PR #44 merge remain unauthorized.
- All legacy source, golden, previous spec/status/publication history remain
  byte-preserved. Simulation role assignments are hypothetical, not decisions.

Future user approval must be added as a new event with actual KST timestamp,
exact approved clause/version/document hash, authority and exclusions. Do not
replace this proposal event or infer approval from successful tests. Policy
acceptance and runtime authorization must be separate recorded grants.
