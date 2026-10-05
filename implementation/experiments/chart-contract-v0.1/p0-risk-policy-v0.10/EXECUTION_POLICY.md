# Chart Risk-Proportional Verification v0.10

Authority: latest explicit user Chart policy, 2026-10-05. Effective at the existing safe checkpoint; this supplements v0.7 continuation policy and supersedes its default verification cost where applicable. Existing design, owner acceptance, write-set, D1/D2 autonomy, D3 and protected boundaries remain in force.

Goal: converge one verified vertical slice to a production candidate. Completion means an implemented and verified Chart capability, not more findings or a larger audit.

| Class | Actual change | Required verification | Close condition |
| --- | --- | --- | --- |
| FAST | Layout, responsive UI, tooltip, legend, labels, CSS, renderer, presentation-only component, fixture, synthetic series, demo export | Targeted renderer test, then browser/mobile check | PASS; close the affected presentation gap |
| STANDARD | ChartDocument, serialization, adapter, Portfolio transformation, Product API chart endpoint, frontend/backend wiring, target allocation | Contract test, negative test, affected integration test, browser test | Relevant checks pass; close the affected contract/wiring gap |
| CRITICAL | PIT, historical availability, security identity, session/calendar, corporate actions, adjusted basis, Target vs Actual, financial numeric meaning, provenance, QGV methodology-derived values | Necessary independent verification of the changed semantic boundary, plus affected integration checks | Semantic invariants and applicable owner/governance evidence verified |

A renderer that displays financial data remains FAST when it only changes presentation. A change to missing-data interpretation, allocation arithmetic, identity or provenance is CRITICAL for that affected part. Mixed work separates the checks by impact; it does not upgrade every file to CRITICAL.

Do not run full Python/repository regression, FPIA or adversarial review by default for UI work. Expand verification only for an actual shared backend/core contract change, an applicable protected integration requirement, or a concrete unresolved failure. Exact merge-result FPIA required by existing integration governance remains required at that boundary; historical FPIA CI PASS is not governance closure.

Use fresh GitHub HEADs and scoped state/handoffs to identify material changes. Reuse compatible existing evidence by exact source/input/output identity. Do not claim a new test PASS when reusing an old receipt. Re-read the changed owner result and exact pending CI subject; do not repeat the same known-gap audit, expand the 113 requirement inventory or recollect the immutable 19-symbol/23,155-row dataset for a UI change.

For a known D1/D2 gap: implement or route the exact owner handoff, run targeted checks, verify the browser where behavior changed, close. Missing owner/source/governance evidence blocks only the dependent portion. Continue independent authorized work. Do not ask to continue D1/D2. Actual D3 remains a user decision.

Default agent budget: one Chart owner/auditor. Add at most one backend/PIT verifier only when financial semantics need it. No visual-only multi-agent adversarial panel. This scoped user budget takes precedence over a generic delegation suggestion.

Priority: Current Target Strategy Theme → Portfolio charts → Market OHLCV → technical overlays → QGV/Valuation → Consensus. Keep other requirements as inventory. TARGET and ACTUAL remain separate; no Actual source means NOT_AVAILABLE. Keep GICS, Strategy Theme, Investment Type and Type Overlap separate. Missing values are not zero. Show basis time, unit, denominator and overlap; label fixture/synthetic data SAMPLE. GICS/Type/Actual absence is not a new first-Theme dependency.

Every meaningful run reports: requirements closed; blockers closed; new blockers; vertical slice progress; production-ready contracts; frontend-ready contracts. Count policy/task configuration changes separately from product requirements and six production gates.

Read current policy through automation/STATE.json.execution_policy.path. Existing Main and CI tasks use the same remote atomic lease, pending queue, watermarks, no-op and self-event controls. No new task/framework/cadence, canonical merge, Global single-writer change, protected production change, Frozen/Holdout/PIT relaxation, Official/LIVE/grant, paid resource, credentials/auth/tenant/deployment or other-owner branch write is authorized here.

Visual work fast. Financial semantics strict. One vertical slice at a time. Stop auditing known gaps; implement them.
