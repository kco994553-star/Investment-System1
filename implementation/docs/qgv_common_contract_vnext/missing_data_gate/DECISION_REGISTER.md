# QGV Missing-Data scoped Decision Register

**Current: M1–M5 policy principles APPROVED; concrete bindings/runtime NOT APPROVED.**
Historical proposal entries below are preserved.

This additive register subdivides the existing local QCC-P01 proposal. It does
not rename global CDR decisions, change Context AP1–AP3, or edit Frozen records.
QCC-P02 is referenced for validation/PIT admission. Date: 2026-10-05 KST.

## Historical proposal table — ed907b8 before limited user approval

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

## Append-only user approval event — 2026-10-05T09:57:52+09:00

Approval ID: QCC-P01-M1-M5-PRINCIPLES-2026-10-05.
Authority: explicit user message in this Work; no PR/CI-derived approval.
Record: [implementation_contract/approval.json](implementation_contract/approval.json).
Record SHA-256: `65a360a410121aeca7f17fbc93369dae59f57e2ed9265f33aeb52c9263a448cf`.
Prior proposal: ed907b8f5a046008319cddecc6ef40b9bd6759dc,
DECISION_PACKAGE SHA-256 4688ce49186906f0878809113c921eec60ed28d5291a3ba4b6b9be4a5338ae6f.

| Clause | Approved scope | Current status |
|---|---|---|
| M1 | Separate requiredness and economic applicability | APPROVED_PRINCIPLE_ONLY |
| M2 | Ordinary missing vs related PIT/integrity; admission before weights; no weight/denominator bypass | APPROVED_PRINCIPLE_ONLY |
| M3 | Ordinary missing keeps planned denominator; proven contract N/A may be excluded | APPROVED_PRINCIPLE_ONLY |
| M4 | Diagnostic/partial contribution distinct from complete/ranking eligibility | APPROVED_PRINCIPLE_ONLY |
| M5 | Zero removes numeric contribution, not evidence/requiredness/applicability/PIT/integrity/provenance; Official/Custom isolation | APPROVED_PRINCIPLE_ONLY |

No actual role/predicate/taxonomy/coverage/ranking method/cutoff, numeric policy,
financial score recalculation, G/FCF/V/composite change, runtime wiring, Official
weight, implementation/version migration, history rewrite, Holdout or merge is
approved. Older all-active completeness/ranking, mandatory N/A exclusion and
optional-zero input suppression remain proposals. New Implementation Contract
is INACTIVE/DESIGN-ONLY. This append changes current principle status without
rewriting historical proposal/simulation evidence.


## Append-only Binding Gate technical recommendation — 2026-10-05

Explicit current user request authorizes D1/D2 binding/consumer audit, independent
recommendation, synthetic verification, automation failure/continuation repair,
scoped evidence/Handoff and owner publication. See binding_gate/work_authority.json.
No B policy adoption is inferred from this authorization or technical review.

| ID | Current technical verdict | Unapproved production value/adoption |
|---|---|---|
| B1 | MORE_EVIDENCE_REQUIRED for factor roles; authority mechanism recommended | All20 actual requiredness assignments |
| B2 | APPROVE_RECOMMENDED modified proof/context/permission boundary | Actual N/A predicates/classification/exclusion |
| B3 | APPROVE_RECOMMENDED scoped admission-before-weights | Exact reason/rubric/scope and runtime policy |
| B4 | APPROVE_RECOMMENDED factor vs immutable method/version identity | Actual method replacement/calculation migration |
| B5 | APPROVE_RECOMMENDED independent result assessments | Actual completeness/validity criteria |
| B6 | APPROVE_RECOMMENDED scoped consumer matrix, P01 partial disclosure preserved | Ranking/cohort/selection/publication adoption |
| B7 | APPROVE_RECOMMENDED numeric-only permitted profile mutation | Node authority/runtime wiring/inclusion |

Package: binding_gate/DECISION_PACKAGE.md; independent review:
binding_gate/INDEPENDENT_REVIEW.md. B4 characterization6cases/17checks, consumer
5families/20checks, control32tests PASS; score/policy unchanged. Actual scheduler
HOP1/HOP2 remains NOT_EXECUTED/NOT_VERIFIED. M1–M5 principle approval is preserved.
