# Product Platform storage/auth and tool-first-use audit

User directions received 2026-10-05 14:12:50 and 14:18:43 Asia/Seoul supplement the existing Work. Completed design/source/test receipts are retained. This is an independent audit continuation, not a backend replacement or a production activation.

Overall **PARTIAL**. Supabase is **NOT_ADOPTED_IN_OBSERVED_SCOPE**; no approved adoption decision, client/config/schema/migration, project locator or development environment mapping exists in the observed fetched refs. The scan covers 60 refs/58 distinct tips, including symbolic origin/HEAD, with 120 successful filenames-only searches and zero matches. See [ADOPTION.md](ADOPTION.md) and [adoption.json](adoption.json) for the exact immutable subjects and limitations. Absence here does not prove absence from private accounts, external deployment configuration or history-only/deleted branches.

There is no identified Supabase development project. Its schema, RLS/access policies, auth configuration and logs are therefore **NOT_RUN**, not verified. No account/project was guessed, no Supabase resource API was called, and no backend, tenant policy or production auth was changed. To resume a targeted remote inspection, supply the approved development project URL/ref and development-versus-production designation, or the GitHub handoff containing both. No new project or credential is requested.

## Current authority and structure

| Subject | Exact HEAD / evidence | Interpretation |
|---|---|---|
| Canonical | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` | Unchanged; local file-backed research raw storage, Frozen BrokerAdapter contract |
| Global | `426c8bb750a5237403fee8336be4714548752094` | CDR-018 makes GPT Work `gpt-work-main-2026-10-05-3a80dcef6444` the Integration Coordinator; this Work does not write Global |
| Product owner | `78a51462f89eac8e34647cddc4e53ed97e831178` | Nonproduction contracts, no authenticated service/database or durable raw store; source repairs independently reconsumed |
| Owner tested source | `603d1c64b005e07dedebcf9ea733e4ed00b504d0` | Contracts/tests/workflow unchanged through owner78a5146; run37265731093 attempt1 terminal SUCCESS; targeted/full steps independently read back |
| Existing audit PR45 | `17244b4f1be0d3b2423d91f76af8b0ad2c262a65` | Separate SQLite, SyntheticIdentityProvider and in-memory SessionAuth; audit-only, not admitted Product authority |

The latest owner closes PPF-003 malformed reference/lineage and PPF-005 blank identity **construction** defects. Their trusted runtime ownership boundary remains open. PPF-004 financial completeness and PPF-006 durable authenticated records remain open. Older Global intake labels do not override the newer source/independent evidence. Current owner STATE has lease=null and pending_ci=[]; this is not permission to take over its branch.

## Requested capability rejudgement

| Capability | Product state | Verified evidence and remaining scope |
|---|---|---|
| Auth | NOT_STARTED | Owner has no Product login; existing audit-only session fixture receipt retained |
| Tenant isolation | PARTIAL | Foreign-tenant contract denial verified; authenticated user+tenant runtime/database isolation absent |
| Financial Connector | PARTIAL | Existing read-only BrokerAdapter reused; no actual provider/consent/token/project established |
| Financial records sync/import | PARTIAL | Declared source identity replay/collision helper verified; durable sync/import and raw-byte authentication absent |
| Reconciliation | PARTIAL | Missing/orphan/duplicate normalized/cross-tenant lineage checks verified; financial amount/completeness remains open; new hash-case counterexample reproduced |
| Immutable/auditable records | PARTIAL | Frozen source/ref objects and declared version/hash checks verified; externally authenticated original-byte ledger absent |
| Read-only hard gate | PARTIAL | All11 admitted names and19 denied aliases verified; synthetic inherited write-method drift is missed by class-dictionary validator; actual trade operation still denied |
| Product API | NOT_STARTED | No owner-authenticated API; existing separate fixture API is audit-only |
| Web/PWA | PARTIAL | Existing static Web, unavailable production account/Chart boundary; browser/mobile NOT_RUN receipt retained; PWA not established |
| Investment engines | PARTIAL | Existing types/actual portfolio fixture reuse retained; production owner integration/publication/exact-result FPIA not admitted |

## Findings, reproduction, repair proposal and actual verification

All below run against the exact owner source through a source-pinned in-memory loader. Seven reviewed source/test/shim files execute; package initializers, real providers, credential reads, network/DB operations do not. [owner_probes.py](owner_probes.py), [owner_probes.json](owner_probes.json) and [owner_probes.txt](owner_probes.txt) preserve the reproduction.

| ID | Observed behavior and cause | Repair proposal / verified scope | Current state |
|---|---|---|---|
| SA-01 | Direct SourceRecordRef accepts uppercase SHA-256, while SourceRecord.ref lowercases it; the same digest yields missing+orphan and passed=False | Consistently canonicalize validated digest representation. Original assertion RED; separate audit-only canonical-ref fixture GREEN | OWNER_ACTION_REQUIRED; owner code not repaired here |
| SA-02 | A synthetic interface with all11 allowed direct methods and an inherited callable trade passes validate_broker_contract(); validator iterates only direct __dict__ | Inspect effective inherited public callable members. Original denial assertion RED; separate MRO-aware fixture GREEN. Existing operation gate still denies trade | OWNER_ACTION_REQUIRED; future admission gap, no current trade/runtime exploit established |
| SA-03 | Same source identity/version with two hashes can pass set-lineage reconciliation when both supplied; ImportLedger separately rejects the conflict | Require proven pre-admitted input or explicitly report source-version conflict. Amount/cardinality semantics remain owner contract decisions | OPEN design/integration requirement; no source mutation |
| SA-04 | Empty inputs, identical duplicate sources and a ref reused by distinct normalized IDs can pass set coverage | Define financial completeness and normalization cardinality before financial verification; do not invent a one-to-one rule for valid aggregation | OPEN, no financial reconciliation claim |
| SA-05 | Same-tenant/different-principal replay and changed metadata with same identity/hash return DUPLICATE in the helper | Trusted auth→user+tenant ownership and actual raw/provenance persistence must be implemented and exercised | Acknowledged missing runtime, not an established service leak |

Bounded candidates stay entirely in the audit fixture. No owner contract, source schema/API semantics, numeric policy, tenant policy or backend is changed. Accepting a candidate requires an actual owner successor plus independent affected tests; a fixture GREEN is not owner/product completion.

## Verification and reuse

Fresh pinned owner tests **9/9 PASS** using the existing mini_pytest shim, not pytest; additional independent assertions **78/78 PASS**. Eight boundary observations are separate from passing checks. Original two candidate assertions produce expected RED; the two local audit-only candidate fixtures produce GREEN. See machine receipts for exact counts and runner/source hashes.

Owner Actions [37265731093](https://github.com/kco994553-star/Investment-System1/actions/runs/37265731093), attempt1 on603d1c64, is independently confirmed terminal SUCCESS, with targeted and full-regression steps SUCCESS. Counts22/405 are the owner's published CI receipt, not a new local full run. The source/workflow comparison from603d1c64 to78a5146 has zero changes; only scoped docs/STATE changed.

All19 original harness source-manifest entries match exactly; previous local84/396 and their terminal Actions receipts are retained and not rerun for tool activation. No claim of a new full suite, browser run, Supabase query or scheduler hop is made. Local Python is3.12.14; CI pins3.11, with its successful run recorded separately.

This delta is documentation and local audit-fixture evidence only. It is published on a separate descendant audit branch of PR45 so its source-test workflow does not repeat already completed suites for a docs-only push. GitHub remains code/contract/verification authority; no canonical/deploy or other-owner mutation occurs.

## Actual tools and first-use boundaries

| Tool / capability | Purpose, target and scope | Actual result |
|---|---|---|
| GitHub MCP | This repository; read branches/owner contracts/handoff/Actions/permissions; publish only own audit evidence | Read permission and repository push permission verified; source/CI evidence retrieved; publication identity supplied by containing commit |
| Context7 MCP | Public Python3.11 documentation for inherited-method inspection; no source/credential sent | One library resolution and one query succeeded; selected official /python/cpython/v3.11.14, matching CI minor version; no dependency install/change |
| Superpowers skills | Parallel review, systematic debugging, tests-first candidate fixtures, verification before claims | Applied only to current audit stage; no completed design restarted |
| Supabase skill + official changelog web read | Adoption/target guard and future inspection criteria | Skill read; official changelog index retrieved after markdown fetch failure; Supabase project/resource APIs NOT_RUN |
| Local Python/Git | Source-pinned mock/fixture tests and immutable hash comparison | No real provider, credential, remote DB or network execution |
| Existing automation | Preserve existing task/destination/cadence; add current tool-use and receipt policy | No duplicate scheduler; update/readback recorded in publication metadata |
| Figma / MagicPath / Linear / Vercel | Callable tools are exposed, but current storage/auth audit needs no design, issue tracker or deployment resource | NOT_USED; service access/project readiness not tested or assumed; future design uses one accepted primary tool per screen |

Python reference retrieved through Context7: [CPython3.11.14 descriptor guide](https://github.com/python/cpython/blob/v3.11.14/Doc/howto/descriptor.rst) and [inspect reference](https://github.com/python/cpython/blob/v3.11.14/Doc/library/inspect.rst). Direct class dictionaries and inherited member lookup are distinct; the fixture tests exercise the actual owner validator rather than assuming the documentation proves its behavior.

D1/D2 audit, mocks/fixtures, bounded repairs and tests continue without redundant approval. Actual financial accounts/credentials, production auth, tenant policies, paid resources, protected semantics, canonical changes and deployment remain D3. Only their dependent action waits; independent audit work continues.
