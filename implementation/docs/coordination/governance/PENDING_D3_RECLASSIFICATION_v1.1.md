# PENDING D3 RECLASSIFICATION · v1.1

Status: STARTED / MAIN INITIAL PASS
Authority: CDR-024 §§25, 26A, 26B, 26D, 26F
Recorded: 2026-10-05
Global input: implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md @ blob 890976f8d146f8ee13cc830e15ea5ea8fb09c9e8
QGV input: architecture reconciliation scoped Handoff (fresh-read in this Main pass)
Platform input: product-platform scoped Handoff (fresh-read in this Main pass)

This is a reclassification inventory, not approval fabrication. Items requiring 26B remain CANDIDATE until an independent execution returns PASS.

| ID | Prior label / source | v1.1 classification | semantic_delta | Basis | Next action |
|---|---|---|---|---|---|
| RD3-01 | Track C C8→C10 numeric configuration and method choices (historical USER_DECISION_REQUIRED queue) | D3-R | UNCLEAR | §§23,26A: new method/numeric configuration affects research/statistical behavior | Present once under §26E when the Track C lane is otherwise ready; no CAL_VERIFY/Holdout |
| RD3-02 | QGV actual method / normalization / composite / numeric selection | D3-R | SCORING_SEMANTIC_CHANGE | §§23,26A,26F: scoring/factor/method semantic changes are reserved | Keep QGV method lane WAIT; bundle exact alternatives under §26E |
| RD3-03 | QGV consumer/runtime wiring using already-approved semantics, with no score/method change | D3-A CANDIDATE | IMPLEMENTATION_ONLY or BEHAVIOR_PRESERVING | §§20,26A Cross-Work,26B,26D,26F | Require exact approved semantics pin + rollback plan + independent 26B verification before execution |
| RD3-04 | QGV migration / historical score rewrite / Official activation | D3-R | IRREVERSIBLE_STATE_CHANGE or SCORING_SEMANTIC_CHANGE | §§23,26A,26F | Keep dependent migration/promotion lane WAIT |
| RD3-05 | Leaderboard within-tie ordering policy | D3-R | SCORING_SEMANTIC_CHANGE | ranking semantics are a protected semantic surface under §26A | Request only when publication lane is ready |
| RD3-06 | P01 research-display/publication grant / Official-like publication authority | D3-R | UNCLEAR | §23 reserves Official/LIVE/publication-authority changes where existing grant is NONE | Keep grant-dependent lane WAIT; integration/audit work may continue |
| RD3-07 | RIG/news provider selection where cost/provider authority is unresolved | D3-R | UNCLEAR | paid resource is reserved; unproven alignment defaults D3-R (§§23,26) | Resolve provider/cost facts first; if free + semantics-preserving, re-evaluate as D3-A candidate |
| RD3-08 | Canonical merges outside the explicitly executed PR #48 Global merge | D3-R | IRREVERSIBLE_STATE_CHANGE | CDR-024 adoption itself did not authorize canonical merge; protected promotion remains reserved | Keep canonical merge lanes WAIT pending explicit scoped decision |
| RD3-09 | FPIA independent verifier/launcher/runtime authority and exact merge-result acceptance | WAIT_DEPENDENCY, not D3 by label alone | NONE/UNCLEAR | current Global says technical CI/raw FPIA PASS but independent authority/GIE/exact merge-result remain open evidence gates | Consume exact independent evidence when returned; only escalate if a protected authority change is actually required |
| RD3-10 | Chart Portfolio/Identity owner-unassigned and source/write-set gaps | WAIT_DEPENDENCY, not D3 | NONE | missing owner/evidence is dependency, not a user decision | Route/consume owner evidence; do not ask user merely because lane is blocked |
| RD3-11 | Platform nine Product blockers with source-owner ACK/adoption absent | WAIT_DEPENDENCY, not D3 | NONE | current scoped handoff states concrete pending D3 decisions = 0; blockers are owner/evidence gaps | Continue owner return path; escalate only a concrete protected decision |

## Initial result

- Confirmed D3-R groups in this pass: RD3-01,02,04,05,06,07,08.
- D3-A candidates requiring §26B independent verification: RD3-03.
- Reclassified away from "user decision" to evidence/dependency handling: RD3-09,10,11.
- No D3-A candidate is executed by this inventory.
- No method, numeric value, grant, canonical merge, deployment, credential, Holdout, Official/LIVE or irreversible migration is approved here.

## Next automatic actions

1. Create independent verification request for RD3-03 only when exact QGV approved-semantics and consumer/runtime diff are available.
2. Convert old generic USER_DECISION_REQUIRED labels to the exact rows above as affected lanes fresh-read.
3. Present D3-R under §26E only when the dependent lane is otherwise ready; do not repeatedly ask on unchanged state.
4. Continue independent D1/D2/D3-A work in other lanes.
