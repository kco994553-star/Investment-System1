# QGV / Product Platform takeover intake

Read-only dependency recovery for the new Main. No owner branch, lease, source, automation or remote object was modified. Repository inputs were freshly read through GitHub connector refs/files and local Git objects. This is coordination evidence, not a repeated domain audit.

## Fresh exact inputs

| Scope | Branch | Exact HEAD |
|---|---|---|
| Missing-data owner | codex/qgv-missing-data-decision-gate-2026-10-05 | 4fb08a05728d83519b72a2bd995669f0cb06003a |
| QGV independent reconciliation | codex/qgv-architecture-reconciliation-review-2026-10-05 | 17a442e7b247e9426e6bc1ee8e91e3cc2f541505 |
| Product Platform audit | codex/product-platform-audit-v1 | c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9 |

Fresh GitHub open-PR collection has no PR for any of these three branches. PR #44 is the old inactive common-contract input, NOT the current missing-data owner PR. #44 current head is cb1906b207623168fd70f3dcdb5b30f2d82d807d.

## Ownership and concurrency

QGV missing-data `automation/STATE.json` is authoritative current control: status `RUNNING_B4_B7_INACTIVE_CONTRACT_AND_CONSOLIDATION`; active lease token `qgv-b47-muupb538`, owner `manual-B4-B7-explicit-user-approval`, input head `36b6b1840fe4bd22d7bb310407e2cea4050e0c2d`, claimed `2026-10-05T12:39:35.838071+09:00`, expiry null. It must not be stolen based on elapsed time. Older owner Handoff says lease released and B4/B7 recommended; the newer STATE claim and reconciliation handoff explicitly identify owner work in progress. Do not infer completed publication of the approval records from that old prose.

QGV reconciliation is an evidence-only independent review branch, NOT an owner successor. Its inherited missing-data STATE is historical input, not live control. It preserves missing-owner active lease. Scoped `CURRENT_HANDOFF.md` says explicit B4/B7 principle approvals are retained but their owner remote recording was still in progress. No Main domain decision is needed to reproduce the already finished audit. Reconciliation work may independently design V alternatives while G waits for accepted owner manifest.

Platform `automation/STATE.json` has lease null, pending_ci [], checkpoint `initial_contract_foundation`. CDR-017 assigns Product Platform auth/tenant/connector/reconciliation capability to the scoped Work. Existing branch is an audit plus bounded non-production contract implementation. It does not prove a separate runtime implementation owner exists, nor authorize Main to become that implementer. A runtime Product API proposal needs an explicit owner/write-set/base before parallel implementation.

## New evidence recovered: Platform exact-head CI

Run https://github.com/kco994553-star/Investment-System1/actions/runs/37263497936

- Exact subject head: c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9.
- Event push; workflow `product-platform-audit`; status completed; conclusion success.
- Job 111615381958 `verify`: SUCCESS.
- `Targeted platform and Track B contract tests`: SUCCESS.
- `Full regression`: SUCCESS.
- Workflow source `.github/workflows/product-platform-audit.yml` runs `PYTHONPATH=src python -m pytest -q tests/test_product_platform_contracts.py tests/test_pil_p0_contracts.py`, then `PYTHONPATH=src python -m pytest -q`, in implementation.
- Numeric test totals were not retrieved; do not invent them.
- This satisfies the Platform handoff's pending exact-head CI collection task. It is a new coordinator evidence receipt, not proof the scoped owner has consumed it. No duplicate CI is warranted without a source delta/failure.

The workflow/readback confirms contract tests, not real login, real tenant service, database or connected account E2E. No whole capability becomes VERIFIED.

## Platform maturity grounded in exact source

Source: `implementation/docs/product_platform_audit/STATUS.md`, `CURRENT_HANDOFF.md`, `automation/STATE.json`; `implementation/src/investment_system/platform/contracts.py`; `implementation/tests/test_product_platform_contracts.py` at c9e1adb.

| Capability | State | Practical boundary |
|---|---|---|
| Auth/login | NOT_STARTED | No session/provider/service implementation |
| Tenant isolation | IMPLEMENTED, contract layer only | TenantContext/require_tenant fail closed; no service/database enforcement |
| Financial Connector | PARTIAL | Reuses read-only Track B BrokerAdapter; no real provider |
| Financial sync/import | PARTIAL | In-memory ImportLedger exact replay/conflict oracle; no durable/provider sync |
| Reconciliation | IMPLEMENTED, contract layer only | Missing/orphan/duplicate/cross-tenant lineage report; no account E2E |
| Immutable/auditable records | IMPLEMENTED, contract layer only | Frozen dataclasses, source version/hash/ref/time; no durable append-only store |
| Read-only hard gate | IMPLEMENTED, contract layer only | Exact 11-operation allowlist; missing/forbidden/unexpected BrokerAdapter methods fail closed; no authenticated API boundary |
| Product API | NOT_STARTED | No authenticated service layer |
| Web/PWA | PARTIAL | Existing static Web and presentation guards; no login/PWA backend |
| Engine integration | PARTIAL | Existing finished-bundle presentation and Track B upstream ports |
| Provenance/publication authority | PARTIAL | Producer/P01 separate; account-page authority unresolved |
| Security/privacy | PARTIAL | Contract guards only; no real auth/secrets/tenant service |
| Failure recovery | DESIGN_ONLY | No durable checkpoint/revocation/recovery |

Existing blocking findings remain PPA-F01 Auth, F02 runtime tenant enforcement, F03 provider/consent/token/checkpoint/pagination, F04 authenticated API, F05 durable ledger. CI success does not close these five product gaps.

## QGV current state and actual immediate dependency

M1–M5 are approved principles only. Missing-data binding gate is inactive/spec-only; all 20 actual requiredness roles remain unassigned. Reconciliation retains B4/B7 principles but no production adoption. Existing findings include G 3–5Y label still mapping revenue YoY, FCF fallback dividing by prior revenue, quarterly total FCF in a per-share field, V result-admission/metadata differences, Q/G-only composite, and numeric Personal weights lacking QGV runtime binding. Those are owner findings, not new Main repairs.

Reconciliation handoff reports bounded verification: 22 V + 20 G/Profile characterizations; 13 selected unchanged tests; 32 continuation tests. These are reported source-pinned evidence, not new Main reruns or economic-correctness approval.

The missing owner has ready scheduler task `QGV_AUTO_HOP1_LEGACY_METHOD_MANIFEST`, output path `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/canary/hop1_method_replay_manifest.json`. Git tree at 4fb08a0 contains no `automation/canary/` files. HOP2 is still an unbound template requiring the exact accepted HOP1 output digest. Actual scheduler continuation remains 0/2, UNVERIFIED. Manual Main work cannot count as either hop.

Reconciliation's next G input-lineage readiness matrix depends on accepted HOP1 publication and owner lease release. This is the genuine immediate cross-owner handoff. No other owner needs to solve QGV's domain semantic choices. Independent V alternative impact design can proceed without that dependency.

Consumer findings provide future compatibility inputs, not activation authorization: producer PASS != complete/valid/rankable/publishable; P01 partial research display remains exact-grant/veto bound; active grants NONE; actual holdings can remain accessible when QGV context is blocked; Web/API consume producer-owned states and do not re-score. Main should not broadcast all inactive design findings as production blockers.

## Proposed routing packets (not sent by this agent)

All packets below are FOUND, not ROUTED/RECEIVED. Main must deduplicate existing delivery and record actual delivery/receipt separately.

### QGV-MANIFEST-TO-RECONCILIATION

- Finding: dependent G lineage matrix lacks accepted owner HOP1 output; active owner lease must be preserved.
- Authoritative owner: Missing-data owner branch above; downstream independent QGV reconciliation Work.
- Required artifact: exact HOP1 manifest plus accepted scheduler receipt, source/authority/validator/output hashes and lease-release/current control checkpoint.
- Existing acceptance contract: `implementation/docs/qgv_common_contract_vnext/missing_data_gate/automation/CANARY_ACCEPTANCE.md`, `CONTINUATION_PROTOCOL.md`, `STATE.json` at 4fb08a0. Do not invent a new manifest shape or scheduler hop.
- Acceptance: all20 legacy methods accounted; semantic pins/authority exact; no new methods/roles/defaults; accepted receipt actually proves source/validator/output; reconcile branch consumes exact digest; HOP2 remains a distinct real scheduler execution.
- Delivery: Global material routing packet is an input the owner instructions read. PR #44/#42 are registered event-input channels, not the missing-owner PR. Bot/API comment must not be called a proven automatic wake.
- Next: publish only the dependency request; owner releases/updates its own lease. Downstream consumes after acceptance. Do not run HOP1 as Main.

### PLATFORM-EXACT-CI-RECEIPT

- Finding: Platform `CURRENT_HANDOFF.md` next task is exact-head CI consumption; run is already green.
- Owner: Product Platform audit Work, c9e1adb.
- Required artifact: scoped receipt referencing run37263497936, job111615381958, exact c9e1adb and both successful test steps; updated own pending state if appropriate.
- Acceptance: no rerun needed absent changed subject; no VERIFIED/E2E overclaim; actual scoped owner readback tracked.
- Delivery: no owner PR exists. Use Global owner-consumable packet and existing Platform Work automation state input. Main should not write the Platform branch.

### PLATFORM-ACCOUNT-PUBLICATION-APPLICABILITY

- Finding: Platform STATUS explicitly asks Product/P01 for account-derived/user-authored page read/publication authority.
- Owner candidate: Product/P01 capability, existing `feature/p01-research-publication-v1`, PR17, scoped `implementation/docs/research_publication/STATUS.md`. Existing Global index identifies this capability; Main must confirm current authoritative owner, not assume all old PR authors are active owners.
- Required artifact: bounded applicability response distinguishing authenticated private account data vs QGV research display; existing grant/veto/currentness contract reuse; exact relevant paths and exclusions; no real credential or grant activation.
- Acceptance: no equation of private account read permission with P01 research publication grant; tenant/principal and source rights remain separate; no Official/LIVE promotion; record unresolved authority explicitly.
- Dependencies: Platform API design and existing P01 authority only, not choice of QGV formulas.

### PLATFORM-WEB-API-PROJECTION

- Finding: no authenticated API service; scoped Platform next design needs a shared boundary.
- Owner candidates: Web/Product + Platform (existing Web `feature/web-mvp-v1` PR5 / current Web successor routing in Global). Establish exact runtime implementer/write-set/base rather than assume audit branch owns deployment.
- Required artifact: accepted inactive API projection contract preserving tenant/read-only gates, upstream bundle/source versions, supplied states/reasons, error/failure states and prohibition on frontend financial/QGV recalculation.
- Acceptance: no production auth activation or account credentials; server-side identity/isolation acceptance deferred with explicit owner; source validity/ranking/publication remain distinct; no duplicate frontend or engine.

### PLATFORM-IMPORTED-POSITION-IDENTITY

- Finding: imported actual position identity needs authoritative Security/Listing binding; existing platform contract does not provide it.
- Owner: Portfolio/Identity authoritative owner to be resolved via Global; no matching dedicated owner branch was established in this intake. Do not appoint PPA audit automatically.
- Required artifact: Issuer → Security → dated Listing mapping contract/source refs suitable for imported positions, unresolved cases fail closed, exact owner and write-set.
- Acceptance: ticker-only lookup insufficient; dates/exchange/share class/currency/identity provenance preserved; ACTUAL and TARGET remain separate; no reuse of Chart target weights as account positions.
- This packet can share owner discovery with Chart security routing but is a separate actual-position use case. Do not add ACTUAL dependency to Chart Target Theme slice.

### PLATFORM-INTEGRATION-ADMISSION (deferred dependency)

- Finding: Platform requests Integration/FPIA acceptance when production package is proposed.
- Owner: Main Integration.
- Required artifact: proposed exact source tree/owner base/write-set and relevant FPIA acceptance on eventual integration subject.
- Acceptance: do not hold current non-production audit/design waiting for FPIA; do not call c9e1adb branch CI an integrated subject acceptance. Actual production package is not yet proposed.

## Automation observations

QGV owner automation IDs `6ac2f22087288191abd144fb4a7655f8` event and `6ac2efbd34fc8191a60dccbbe338c291` followup are preserved in current STATE/CONTROL. Registered exact input PRs are44/42. Comment events historically specify human-created comments/reviews; APIs may attribute connector commits/comments to humans, so attribution is not delivery proof. Global-only pushes and Actions completion are not assumed webhook families. The followup handles finite state work independently of empty CI. Event conversation6ac230f1-0ff0-83ee-a932-45244e2c4afe differs hourly6ac3012d-9bf4-83e8-b2ba-bb8c3ab9d10a; shared repository lease prevents competing writes but same-chat delivery is unverified.

Reconciliation handoff also records QGV re-audit automation6ac31fdb7f388191be588ea61f5a2009 readback enabled, no new watcher or run_now. This is owner-reported configuration evidence, not a fresh automation inventory from this subagent and not END_TO_END_VERIFIED.

Platform STATE has no automation ID. `.github/workflows/product-platform-audit.yml` is GitHub CI, not proof of ChatGPT autonomous owner continuation. Main automation inventory must correlate the existing Platform Work separately.

## Protected boundaries

No domain formula/method/requiredness/normalization/rank admission, runtime override or migration adopted. No auth/credentials/account connector/trade/order/fund-transfer action. No canonical merge/deploy. No owner state mutation. No new tests were run: existing exact-head successful tests were sufficient for this evidence-recovery task.
