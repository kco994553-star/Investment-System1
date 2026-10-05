# QGV Missing-Data Gate — scoped handoff · 2026-10-05

**STATUS: DECISION_READY / RECOMMENDED_NOT_APPROVED / INACTIVE / SPEC-ONLY.**

This is an additive Phase B continuation. Read this handoff and
[DECISION_PACKAGE.md](DECISION_PACKAGE.md) before starting work. Do not repeat
Remote Recovery or the complete earlier QGV audit.

## Authoritative input pins and current publication

| Item | Exact pin / result |
|---|---|
| Canonical | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| PR #44 | Draft/Open/unmerged; `cb1906b207623168fd70f3dcdb5b30f2d82d807d` |
| PR #44 package tree | `a951276e66ed01614e27b0b00c4c14bb4f3e00ca` |
| Original local identity | `4b3919715a71c146c088a5530851e0761e7a9396`; same tree, different commit identity |
| Immutable publication evidence | `11cd2f5ac545af54d943dc206396c1fb6926689c` |
| Latest integration candidate | `integration/fpia-hardened-v1` @ `523e702a806a718d163cfbf62aa3fc29d8c3ef3c` |
| Global routing head | `9d9b2b2b942cfa6d1f7b296ad81d380ec6a70b3e` |
| Phase B scoped branch | `codex/qgv-missing-data-decision-gate-2026-10-05`, based on publication evidence head |

PR #44 remains **REMOTE_VERIFIED / DRAFT_PR_CI_VERIFIED**. Push Actions
`37245014376` and PR Actions `37245037812` are both completed SUCCESS. The
publication record verifies remote targeted 39, contract/isolation/provenance 92,
golden 71 and full regression 488 PASS. This task fresh-read those results and
did not rerun or relabel them as new Phase B CI. Original and transport trees
match, and integration has not advanced, so no new source-impact regression
was justified. Retain its scoped compatibility PASS; full integration acceptance
and real PIT/OOS remain NOT_RUN.

The new Phase B publication commit is identified by this branch's exact remote
HEAD and delivery receipt. This document pins its input/source authorities;
it does not attempt a self-referential commit hash. A later worker must fresh-read
that HEAD and inspect only relevant drift before continuing.

## What Phase B completed

- Reconciled current Q/G/V prior, research V candidates, raw/provider/history,
  applicability, zero-weight and metadata flows against the existing audit.
- Added scoped current-behavior probes: 77 actual synthetic snapshots and 18
  reducer zero-weight diagnostic cases, plus independent arithmetic/PIT entry/
  history anchors. Existing runtime functions and weights are unmodified.
- Compared fail-closed, available-weight estimate, fixed partial contribution and
  guarded requiredness/applicability Hybrid across 14 investment-model dimensions.
- Added a standalone read-only synthetic/golden-input policy comparison. Exact
  final scenario/output/check counts are recorded in `SIMULATION.md` and
  `simulation_results.json`; original golden and pinned source hashes match.
- Prepared five minimum independent policy decisions, the Work recommendation,
  migration/approval boundaries and next semantic dependencies.
- Added a scoped proposal register. No M1–M5 approval was inferred.

## Current behavior findings

Q/G/V prior retain a nominal full denominator of 1 and skip missing contribution;
some evidence can emit PARTIAL. Applicable BLOCKED_DEPENDENCY blocks the axis.
V candidates require all seven factors and retain their research lifecycle;
numeric N/A/integrity statuses can be included. Financial ROIC applicability
excludes the observation before its quality is read. Ordinary missing, genuine
N/A and integrity failure are therefore not consistently expressed today.

Provider admission guards both available_at and published_at; direct raw/factor
entry has different preconditions. Numeric nonfinite/integrity flags may reach
the reducer. These observations are future admission questions, not a finding
that all historical Official evidence leaked or is invalid. No current path was
fixed. Snapshot coverage considers Q/G only; V Quality metadata reuse remains
a separate preserved issue.

## M1–M5 and recommendation

All IDs are local **PROPOSED / NOT_APPROVED / INACTIVE**, under QCC-P01 with
QCC-P02 cross-cutting admission. They are not approved global CDRs.

| ID | Recommended policy principle |
|---|---|
| M1 | Method-requiredness and economic applicability independent of weights/presence; pinned predicate/role evidence, unresolved policy remains blocked |
| M2 | Preserve reasons; relevant/consumed PIT/integrity/config failure blocks its explicit dependency scope before weights |
| M3 | Ordinary missing retains planned applicable active denominator; only proven N/A is excluded; no available-only reweight |
| M4 | Optional missing permits diagnostic PARTIAL_CONTRIBUTION; new complete score/rank eligibility needs applicable positive-weight and method-required evidence complete |
| M5 | Zero removes contribution, not method-requiredness or related/shared PIT/integrity; Official validity remains immutable under Personal changes |

The financial Q example can change from legacy 56 to a new applicable-basis 70.
This is real effective redistribution through a denominator, despite unchanged
stored weights, and requires D3 semantic approval. Available-only reweight can
increase a sparse company's estimate after a weak observation is hidden. Such
examples are synthetic policy illustrations; no Official score or board changed.

## Remaining binding questions / approval gates

- Method/profile-specific required/optional/conditional roles for the existing
  20 factors; actual applicability predicates and evidence, without new defaults.
- State/admission mapping for stale/estimated/conflicting sources, dated identity
  changes and source/PIT precision; exact dependency/consumption scope.
- Score-kind/completeness/consumer acceptance, comparable version/profile cohorts,
  source/age/sector attrition and rank-impact evidence.
- Registry maturity/authority C-24/C-30, factor-node map, storage/cache isolation
  and authorized Personal configuration binding.

Current audit/docs/simulation are D1; conservative recommendation is D2.
Adopting result-affecting M1–M5 policies is **D3-P/equivalent plus explicit user
approval**. A design-policy approval still does not authorize factor-role defaults,
production implementation, migration, Official/publication promotion or merge.

## Protected boundaries and next gate

Production Q/G/V, factors/weights, G 3–5Y revenue-YoY proxy, EPS→FCF current
fallback, V normalization/metadata, `(Q+G)/2`, WeightOverride runtime, Official
Leaderboard/TrackRecord, history/frozen artifacts and PIT protections remain
unchanged. Holdout is UNCONSUMED. Canonical, PR #44 and integration branches are
not modified or merged. Existing golden expectations and earlier spec/status/
publication records remain byte-preserved.

**Next single user decision:** approve or amend the explicitly enumerated
M1–M5 guarded-Hybrid policy principles in `DECISION_PACKAGE.md`.

After policy acceptance, assemble the exact method/profile binding and impact
package. Review G 3–5Y and EPS→FCF together for dependencies but decide them
separately; review V normalization and metadata independently; then composite
meaning and finally authorized runtime WeightOverride wiring. No production
migration starts automatically at any of these design gates.

## Coordination note for the Primary Integration Writer

Global GCH-014/GSI-020 and root Master Status contain stale parallel-work/current
publication statements. This task records the exact PR #44 and scoped Phase B
pins for the routing writer to incorporate under its own authority. No shared
Global Handoff, Global status/history or coordination register was edited by
this worker. Earlier contradictory upload-blocked statements stay historical.

## Automatic continuation setup

Two enabled automations target this Work's chat: PR-event resume
`6ac2f22087288191abd144fb4a7655f8` (exact #44/#42) and separate hourly CI
follow-up `6ac2efbd34fc8191a60dccbbe338c291`. See [control](automation/CONTROL.md)
and [state](automation/STATE.json). Real webhook delivery is NOT_TESTED;
no pending run is fabricated. Phase B has no PR number at this checkpoint.
M1-M5 remain NOT_APPROVED. Own-branch optimistic leases, event receipts and
control-only change exclusions protect duplicate writes/self-trigger loops.
