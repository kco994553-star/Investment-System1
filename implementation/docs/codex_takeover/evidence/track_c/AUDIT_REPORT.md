# Exact-SHA Track C takeover audit

Read-only owner/source audit with new evidence only. All executed examples and
fixtures were synthetic. This report is **EVIDENCE / NOT_AN_APPROVAL**.

## Source and scope

| Field | Exact value |
|---|---|
| Owner branch | `ccr-22e3ff16-p7n5k5` |
| Audited owner HEAD | `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565` |
| PR #4 branch HEAD | `feature/track-c-evl` at `ff78c4f6c4a1a8fd15db21807de6be3905c89548` |
| Owner vs PR #4 | 9 ahead, 0 behind |
| Canonical / merge-base | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Owner vs canonical | 63 ahead, 0 behind |
| Global routing read | `integration/global-handoff-v1` at `f26dc7adbfedd9209e757b5e8566c665c7bbd677` |
| Operational contract | PR #21 exact HEAD `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798`, blob `617ef6d485db85cbe4d22376d06c472902ed10e8` |
| Audit worktree | `/workspace/track-c-audit`, detached owner HEAD |
| Audit mutations | New files under `/workspace/takeover-evidence/track_c/` only; owner source/tests untouched; worktree clean |
| Maturity before → after | `SYNTHETIC_VERIFIED → SYNTHETIC_VERIFIED` (approved software subset; no capability-stage increase) |
| Freeze | C0–C7 SOFTWARE_FROZEN preserved; C8 NOT_FROZEN; C9/C10 policy proposals inactive |
| BRANCH_STATE | Exact owner source independently synthetic-tested; exact-HEAD Actions SUCCESS observed |
| INTEGRATION_STATE | Combined trial NOT_RUN by this auditor; root integration worker owns that separate evidence |
| CANONICAL_STATE | NOT_MERGED |

Source Git blobs:

- `evl/superiority.py`: `8a1254d7b77514f6015dfff4af0e4a53f57f22af`
- `tests/evl_c8_gsup_oracle.py`: `a5f00fa9b928a8916fde30c53f1fc432dffd7a9f`
- `tests/test_evl_c8_gsup.py`: `c1e91024ce9663c9b166ded11ef2eef695c23b71`
- scoped Decision Register: `62f0034cf7a91b4744aa944baf463d0c2c08e7bb`

## Actually executed validation

| Execution | Runtime | Actual result | Evidence |
|---|---|---|---|
| Initial C8 pytest attempt | default Python lacked pytest | exit 1, NOT_RUN; retained | `c8_targeted.log` |
| Whole C8 targeted tests | Python 3.12.14 / pytest 9.1.1 | **200 passed**, 207.96 s | `c8_targeted_pytest.log` |
| G-SUP targeted | Python 3.12.14 / pytest 9.1.1 | **84 passed**, 11.30 s | `gsup_targeted_pytest.log` |
| G-SUP targeted matching workflow Python minor | Python 3.11.16 / pytest 9.1.1 | **84 passed**, 13.79 s | `gsup_targeted_pytest311.log` |
| Independent oracle and protocol probes | Python 3.12.14 and 3.11.16 | exit 0 in both; JSON byte-identical | `independent_c8_audit.py`, `independent_c8_audit{,311}.json` |
| C6 boundary / C7 preservation / C8 preservation functions | Python 3.12.14 | PASS; 225 C7 and 232 pre-C8 existing source/test blobs preserved | `preservation.json` |
| Full repository tests | this auditor | NOT_RUN; root runs separate combined trial | — |
| Full C6/C7/C8 acceptance fixture runners | this auditor | NOT_RUN; preservation functions only | — |
| Actions dispatch by this auditor | this auditor | NOT_RUN | — |

Latest observed exact-HEAD Actions: run **37097149378**, workflow
`track-c-evl-validation`, `workflow_dispatch`, owner SHA `b9e01a97`, SUCCESS,
created `2026-10-03T04:37:19Z`, updated `2026-10-03T04:52:10Z`. The workflow pins
Python 3.11. This is a fresh GitHub snapshot read through the root's
`runtime/actions-latest.json`, not an auditor-dispatched run. See
`actions_snapshot.json`.

## Independent M-B versus kernel results

The new oracle owns its seeded block-index loop and arithmetic. It ports the
approved simulation's M-B variance/scoring rules onto the same existing C6
index convention to isolate the two method differences. It does not import the
kernel or existing oracle to compute its reference outputs.

| Case | Synthetic input / evaluation-only configuration | M-B | Implemented kernel |
|---|---|---|---|
| CE1 | `[.03,-.01,.02,.01]`, n=4,L=2,B=19,seed=1 | NOT_RUN: one variance block | p=.30: two full blocks |
| CE2 | `[.03,-.01,.02,.01,0,.02]`, n=6,L=2,B=19,seed=1 | p=.05 | p=.10 |
| CE3 | `[.03,-.01,.02,.01,0]`, n=5,L=2,B=19,seed=1 | p=.05 | p=.05 |
| CE4 | `[-.016,-.007,.053,.023,.005]`, n=5,L=2,B=19,seed=200 | p=.10 | p=.15 |
| CE5 | `[.008,.003,-.02,.019,.012,-.01,.019,.002]`, n=8,L=2,B=19,seed=18 | p=.30, 3 blocks | p=.25, 4 blocks |

CE4 flips a hard decision at illustrative alpha .10. CE1 changes runnability.
All five owner counterexamples reproduced. **300/300** randomized comparisons
matched the implemented kernel; **281/281** eligible comparisons matched M-B
when L does not divide n and no degenerate replicate occurs. Numeric values are
evaluation fixtures, not calibration defaults or grants.

Exact differences remain unresolved: M-B uses `ceil(n/L)-1` variance blocks and
degenerate replicates never exceed; kernel uses `n//L` blocks and degenerate
replicates count as exceedances. The existing oracle verifies kernel arithmetic
but cannot decide which convention the user authorized. No convention was
changed here.

## Approved-policy guard audit and additional weakness

CURRENT owner fixes correctly reject a changed campaign with unchanged verify
commitment in the same shared registry, and reject uncommitted Development
series despite a claimed Development label. These cases independently confirm
the scoped CDR-005 repairs. They do not prove universal identity protection.

An additional synthetic one-shot representation weakness is reproduced:

- Same verify dataset ID, profile/role, shared access registry and numerically
  identical observations, but float versus integer JSON encoding.
- The preregistered raw cohort commitments and access keys differ.
- A second registration and target read are accepted; both return STAT_PASS,
  with all eight cell outputs identical.
- Final decision stays NOT_RUN_EFFECT_FLOOR_DEFERRED; Official stays false.

Current preregistration provides an opaque content digest and caller label, but
no authoritative source/vintage/sample resolver. A label-key add-on would still
permit simultaneous relabeling/reencoding; a post-read normalized digest would
discover the duplicate after the forbidden read. No cosmetic patch or invented
source identity was applied. This is an existing-policy identity gap whose
robust implementation is **DEPENDENCY_BLOCKED on scoped source-identity
authority**. Reviewable proposal:
`PROPOSED_SOURCE_IDENTITY_CONTRACT.md` (**PROPOSED / NOT_APPROVED**).

The hardcoded `.99` envelope cap was also reconfirmed. It is already disclosed
by GIE-004 items 1/16; it is not a new approval or freshly discovered policy.
No arbitrary replacement cap, estimator or process family was selected.

## Current versus historical authority

| Item | Classification | Reason |
|---|---|---|
| Q1–Q6 method approval at 2026-10-02T20:43:44+09:00 | CURRENT | Conditional method scope, numerics pending; runtime-pinned approval evidence |
| CDR-005 owner repairs at 9a9364c / b9e01a97 | CURRENT | Later scoped Decision Register and exact source; original two probes now reject |
| GIE-004 original fail-open behavior at 97d1b94 | SUPERSEDED as current defect status; HISTORICAL evidence retained | Repairs apply approved policy; new representation probe is separate evidence |
| C7 Freeze source c5932f9 / C6 Freeze source 166dcba | CURRENT for exact Frozen scope; HISTORICAL test execution | Their tested SHA remains distinct from current owner; preservation verified |
| Earlier C8 blanket NOT_IMPLEMENTED / A6 METHOD_PENDING text | SUPERSEDED for current approved subset | Later scoped approvals/software records change only their exact scope |
| Foundation runner A6 PROPOSED label versus scoped conditional approval | CONFLICT in current display label; authority resolved to scoped register | Frozen foundation constant unchanged; its label cannot downgrade or expand policy |
| M-B approval-evidence convention versus implemented v1 semantics | CONFLICT / USER_DECISION_REQUIRED | Same method label does not resolve result-changing D1/D2 differences |
| Global references to old Track C tip or pending Actions | SUPERSEDED freshness snapshot | Exact owner b9e01a97 and completed exact-HEAD run observed |
| CDR-004 IF-1 A1 + owner adoption | CURRENT routing authority | Any old open A/B merge-order question is superseded; no Track C Frozen rewrite authorized |

## Decision and next action

**Primary method decision:** Which convention is authoritative?

- K: keep implemented kernel; establish size evidence for its exact conventions.
- M: adopt the approved simulation convention under a new version; retain v1.
- C: another explicitly selected convention with new evidence.

No option is selected. Numeric configuration remains a separate approval gate
before any real CAL_VERIFY. A8/A10, C9/C10, Holdout, Official and publication
remain unapproved/inactive within this audit scope.

**Source identity decision:** Review the proposed current-resolving
source/vintage/sample descriptor contract and the consumption grouping boundary
before implementing a robust pre-access replay fix. The existing separate
foundation/G-SUP access-registry limitation is not silently resolved.

Next autonomous action outside these method/identity gates: continue approved
producer owner adoption/re-pin, combined trial integration, and Web integration
preparation on new proposal branches. No canonical merge, remote owner write,
history rewrite, publication or real data access occurred in this audit.
