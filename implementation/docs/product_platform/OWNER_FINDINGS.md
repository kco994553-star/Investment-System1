# Product Platform owner findings — independent pinned review

This is an audit packet in the independent Product Platform audit Work's scope. It is not an owner handoff, branch takeover, production contract, implementation approval, or integration result. Only this document is written by this review.

**Current re-consumed subject:** `c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9`. PPF-001 and PPF-002 are CLOSED at that successor; PPF-003–006 remain OPEN in the bounded senses recorded in the successor section below. Exact package import/export and seven owner contract tests were independently exercised with a source-pinned import loader and mini_pytest shim. The initial `9e524ef` findings and absence-of-artifact observations below are historical and are not current import blockers or current claims that the owner has no handoff/tests/state.

## Exact subjects and freshness

| Subject | Pinned identity |
|---|---|
| Canonical baseline | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Inspected owner branch | `origin/codex/product-platform-audit-v1` |
| Inspected owner HEAD | `9e524ef2033d5ee99961d5b88fbc3e92836b8305` |
| Owner publication time | `2026-10-05T13:20:39+09:00` from the commit |
| Inspected Global / routing HEAD | `b3532a2ebbe95310bbf222937466eb04a0211263` |
| Coordinator authority | `implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md`, CDR-017, decided `2026-10-05 13:05 KST` |

The inspected owner HEAD adds two files through three commits above canonical. These findings apply only to those exact bytes. Fresh owner output may repair or supersede them; re-read the owner HEAD and scoped evidence before deciding whether a finding remains open. An earlier finding is preserved as history, not projected onto a newer subject.

| Owner path | Git blob | SHA-256 of exact file bytes |
|---|---|---|
| `implementation/src/investment_system/platform/__init__.py` | `434ba9b1d7c494680beffeb17c9c97db87c42690` | `80217fec298f8f1015e67d6d9b770fd2dbbfe62d044bb5f8280de4aa797afe5b` |
| `implementation/src/investment_system/platform/contracts.py` | `99a1f4b36a2e174569158194ed067274084a0031` | `0827f626ffe95291ad57c817f9b11e28992e0881f222e6e7b984e6cdb1e233a5` |

No new scoped owner handoff, capability matrix, approval record, lease/state file, tests or workflow was present in that inspected branch tree. This is an observation about published artifacts, not proof that the owner is idle or lacks authorization. Recent publication is evidence of owner activity. **Absence of published lease evidence never authorizes takeover, concurrent writes or editing the owner branch.**

## Observed findings

| ID | Observation at the pinned subject | Consequence / owner disposition needed |
|---|---|---|
| PPF-001 | Compiling the exact `platform/__init__.py` bytes raises `SyntaxError: unexpected character after line continuation character`, line 1. The file contains literal backslash-n sequences outside its docstring. | Package import is blocked. Owner repairs actual newlines and verifies ordinary package import at its successor HEAD. |
| PPF-002 | `__init__.py` imports and exports `ReconciliationReport`; `contracts.py` defines no such symbol. | A second export/import defect remains after the syntax repair unless the owner implements or removes the export consistently. |
| PPF-003 | `SourceRecordRef('t', '', '', '', 'bad')` is accepted. `NormalizedFinancialRecord('t', 'row', (42,))` is accepted, and subsequently causes `AttributeError: 'int' object has no attribute 'tenant_id'` in reconciliation. | Declared lineage types do not validate provenance identity/hash or reference shape. Owner rejects malformed references before record admission and returns an explicit failed input result or typed integrity error without a success claim. |
| PPF-004 | `reconcile_records(TenantContext('t', 'p'), [], [])` returns `passed=True`. The function compares reference coverage, not financial amounts, balances or portfolio completeness. | Empty set equality must not be consumed as verified financial reconciliation. Owner defines explicit lineage-only semantics and financial acceptance; missing data remains NO_DATA / NOT_COMPARABLE / equivalent non-verified state. |
| PPF-005 | `TenantContext(' ', ' ')` is accepted. Tenant context is caller supplied; the inspected package has no authenticated session boundary or user-and-tenant storage authorization. | Owner validates nonblank principal/tenant identity and documents where trusted session ownership originates. Primitive equality checks cannot certify product tenant isolation. |
| PPF-006 | `ImportLedger` is in-memory and trusts `payload_sha256`; it does not verify the raw bytes or immutable receipt. `SourceRecord` checks digest syntax, not content authenticity. | Retain this as a declared-hash helper until a verified raw receipt/persistence boundary exists. Exact raw hash, correction history, tenant/connection binding and duplicate/replay acceptance evidence are needed for ingestion readiness. |

PPF-003 and PPF-004 are security/data-admission findings, not proposals to rewrite Frozen personal P0. A lineage helper may intentionally accept empty collections internally, but its result then needs an explicit scope and must not confer financial or production VERIFIED status.

## Independent evidence and reproduction

This review obtained both files with `git show 9e524ef2033d5ee99961d5b88fbc3e92836b8305:<path>`, computed their SHA-256, compiled the initializer directly, and inspected the contracts AST for defined names. To inspect contracts behavior despite the initializer failure, the exact contracts bytes were executed in a temporary in-memory module with package `investment_system.platform`; its existing relative `personal.ports` dependency came from canonical. This deliberately bypassed the broken initializer for diagnostic probes. It is **not** a successful ordinary package import, production test or integration result. No source was copied or modified.

Observed stdout:

```text
subject 9e524ef2033d5ee99961d5b88fbc3e92836b8305
__init__.py sha256 80217fec298f8f1015e67d6d9b770fd2dbbfe62d044bb5f8280de4aa797afe5b
contracts.py sha256 0827f626ffe95291ad57c817f9b11e28992e0881f222e6e7b984e6cdb1e233a5
PACKAGE_COMPILE FAIL SyntaxError unexpected character after line continuation character (__init__.py, line 1)
RECONCILIATION_REPORT_DEFINED False
EMPTY_RECONCILIATION {'missing': (), 'orphan': (), 'duplicates': (), 'cross_tenant': (), 'passed': True}
MALFORMED_REF_ACCEPTED SourceRecordRef(tenant_id='t', connection_id='', source_record_id='', source_version='', payload_sha256='bad')
NON_REFERENCE_LINEAGE_ACCEPTED NormalizedFinancialRecord(tenant_id='t', normalized_id='row', source_refs=(42,))
MALFORMED_LINEAGE_RECONCILIATION AttributeError 'int' object has no attribute 'tenant_id'
WHITESPACE_TENANT_ACCEPTED TenantContext(tenant_id=' ', principal_id=' ')
```

No owner pytest, full regression, Actions, browser, security closure, FPIA, merge or deployment success is claimed by this packet.

## Required owner return and acceptance

The following are requested artifacts, not files written by this audit. The owner may choose equivalent scoped paths but must publish the exact paths and containing commit; no ownership of these proposed paths is acquired here.

| Required artifact / proposed owner path | Minimum content and acceptance |
|---|---|
| Owner handoff: `implementation/docs/platform/HANDOFF.md` | Exact owner HEAD/base, scope, maturity per capability, actual dependencies, active-writer/lease routing, next actionable work and preserved failure history. |
| Owner write set: `implementation/docs/platform/WRITE_SET.md` | Explicit owner acceptance for `implementation/src/investment_system/platform/`, `implementation/tests/platform/`, owner docs and selected workflow paths. Address semantic overlap with the independent `product_platform/` audit harness; exclude this audit's paths and other owners' branches. |
| Contracts successor: existing `implementation/src/investment_system/platform/__init__.py` and `contracts.py` | Ordinary `import investment_system.platform` succeeds; every public export exists; malformed provenance/ref shapes fail before admission; missing input does not become financial VERIFIED. Publish exact successor source hashes. |
| Targeted tests: `implementation/tests/platform/test_contracts.py` | Cover PPF-001–006, valid controls, foreign tenant/context, malformed hash, wrong reference type, empty source/row sets, unknown reference, orphan, duplicate normalized ID, source-version content collision, identical replay and denied unknown/write operations. Separate lineage checks from financial reconciliation. |
| Trusted ownership/ingestion acceptance: `implementation/docs/platform/CONTRACT.md` | Identify authenticated ownership source, user+tenant isolation boundary, verified raw receipt and hash relation, immutable correction/replay behavior, read-only operation enforcement, completeness/data availability and explicit synthetic/real state. Do not infer production capability from protocol presence. |
| Verification receipt: `implementation/docs/platform/evidence/verification.json` | Exact source/test hashes, runner identity, actual failures/repairs, observed test results and scope. Record Actions/FPIA as NOT_RUN unless observed on the exact subject. Link affected regression evidence and owner read/write-set acceptance. |

On owner return, the independent audit fresh-reads its HEAD, verifies the exact source hashes and evidence, re-runs the affected negative probes, and marks each finding CLOSED / OPEN / SUPERSEDED with a reason. A changed HEAD alone does not close a finding. An owner-authored completion claim alone does not establish independent VERIFIED status.

## Coordinator route, overlap and protected boundaries

CDR-017 designates Claude Main / Integration as Primary Integration Coordinator. Auth/Tenant/Connector/Reconciliation remain the Product Platform Work's specialist responsibility. The appropriate route is:

`this scoped finding packet → coordinator owner routing → Platform owner action and exact artifacts → independent re-consumption → blocker re-judgement`.

No message to another person or write to Global/owner branches is performed by this document. Global remains read-only for this Work. Any delivery must use an already authorized coordination surface and preserve single-writer controls.

Our `implementation/src/investment_system/product_platform/` namespace is file-disjoint from the inspected owner's `platform/`, but **semantically overlaps** tenant, connector, source identity, sync/idempotency, provenance and reconciliation responsibilities. Our source/tests/tools/docs are retained as an explicitly synthetic independent audit harness. They are not admitted production Platform contracts, a competing owner authority or a reason to replace the other branch. Shared-contract adoption, compatibility adapters and production write sets require explicit owner/coordinator acceptance after fresh review.

Do not edit either owner's branch to resolve this overlap unilaterally. Do not infer authority from missing lease records. No canonical merge, deployment, real credential/financial-account connection, production auth, tenant-policy change, paid connector, trading execution, protected semantic change, Frozen/history rewrite or PIT relaxation is authorized by this packet. Existing synthetic audit work may continue in its accepted independent scope.

## Successor re-consumption — c9e1adb

This bounded follow-up reads only the affected owner source, focused tests, scoped handoff/status/state and workflow published after the first pin. It does not repeat the broad repository audit, change any owner file or claim a production result.

| Successor subject | Observed value |
|---|---|
| Owner HEAD | `c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9` |
| Publication time | `2026-10-05T13:25:58+09:00` |
| Intervening evidence/test commit | `f5c6b0a68abaccdd38e1ab35533cc0886b757709`, `2026-10-05T13:22:45+09:00` |
| New handoff path | `implementation/docs/product_platform_audit/CURRENT_HANDOFF.md` |
| Capability matrix / owner findings | `implementation/docs/product_platform_audit/STATUS.md` |
| Owner state | `implementation/docs/product_platform_audit/automation/STATE.json` |
| Focused owner tests | `implementation/tests/test_product_platform_contracts.py` |
| New workflow | `.github/workflows/product-platform-audit.yml` |

| Exact successor path | SHA-256 |
|---|---|
| `implementation/src/investment_system/platform/__init__.py` | `d293e02f1cdc26d1af81a8ab7b56a9bac93c8ccb94f552203f10e332c3dd21b2` |
| `implementation/src/investment_system/platform/contracts.py` | `75eceb8960e59a6813b025a85e0d9b54a0c5c8ea5f0f6acd18ff292d57d31ef9` |
| `implementation/tests/test_product_platform_contracts.py` | `6becc00ac7bf9301859f85972367d2d66a0ac395048ff8afb4758e32f5eb6ab0` |
| `implementation/docs/product_platform_audit/CURRENT_HANDOFF.md` | `a71c55c457a5d27a217d623d8e5022e0a2ff8248b3bfa1e4ab79ccf2de5e8615` |
| `implementation/docs/product_platform_audit/STATUS.md` | `edbbcb08a5e727a298771d3626213a80293a281b9548a97ae436ddbd82362ddf` |
| `implementation/docs/product_platform_audit/automation/STATE.json` | `9231f25f1fb674352f9afed591be6299f742bda0eea44b39abccb783e91f6ba3` |
| `.github/workflows/product-platform-audit.yml` | `ac716599670742f702c88e6f9cfb275dc07c2e782e81dfacdb30d8aa4d3b0259` |

### Finding closure at this exact successor

| ID | Current judgement | Re-consumed evidence / limit |
|---|---|---|
| PPF-001 | **CLOSED** | Initializer now contains actual newlines. Normal Python import machinery with an in-memory source-pinned loader successfully executes the exact package/contract sources. This is independent package-source verification, not installation, deployment or a full checkout regression. |
| PPF-002 | **CLOSED** | Missing `ReconciliationReport` import/export removed. Every member of successor `__all__` exists. This closes the import/export defect; it does not supply a financial reconciliation report contract. |
| PPF-003 | **OPEN** | `SourceRecordRef('t', '', '', '', 'bad')` remains accepted. Successor `NormalizedFinancialRecord('t', 'row', 'POSITION', (42,))` remains accepted and reconciliation still raises `AttributeError`. New required `record_type` and SourceRecord account/source fields do not validate reference shape or referenced evidence. |
| PPF-004 | **OPEN — financial admission boundary; scope partially clarified** | Empty sources/rows still return `passed=True`. Owner STATUS now explicitly calls the operation a deterministic source-to-normalized lineage check and says no account E2E or operational platform claim. That clarification is accepted; empty lineage equality must still not become financial VERIFIED at a future API/consumer. The follow-up does not call an explicitly internal set comparison an amount-reconciliation algorithm. |
| PPF-005 | **OPEN** | Whitespace principal/tenant still accepted. Owner STATUS explicitly acknowledges no auth/session implementation and no runtime tenant service/database enforcement. No service-level tenant-isolation closure is inferred from the seven contract tests. |
| PPF-006 | **OPEN** | Declared account ID, record type and source are now required on SourceRecord, improving metadata shape. ImportLedger remains in-memory and does not authenticate raw bytes. Owner STATUS acknowledges no durable append-only store/checkpoint/provider sync. |

The owner also replaced the dynamically derived connector allowlist with a fixed explicit set and added `validate_broker_contract()` to reject missing, unexpected or forbidden BrokerAdapter public methods. Its focused tests exercise the existing contract and deny unknown/write operation names. This is a useful bounded successor improvement, not a runtime adapter/API execution or real connector verification.

### Focused independent execution receipt

Exact owner files were loaded using `git show <successor>:<path>` without checkout or branch mutation. A temporary `importlib.abc.MetaPathFinder` / loader fed only `investment_system.platform` and `investment_system.platform.contracts` their pinned bytes; normal import machinery executed them and their canonical personal dependency. The exact focused test source then ran its seven `test_*` functions with the repository `tools/mini_pytest.py` shim's `pytest.raises` support. No pytest installation, network test, broad owner suite or CI success is claimed.

```text
subject c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9
PACKAGE_IMPORT PASS ALL_EXPORTS_EXIST True
EMPTY_RECONCILIATION {'missing': (), 'orphan': (), 'duplicates': (), 'cross_tenant': (), 'passed': True}
MALFORMED_REF_ACCEPTED SourceRecordRef(tenant_id='t', connection_id='', source_record_id='', source_version='', payload_sha256='bad')
NON_REFERENCE_LINEAGE_ACCEPTED NormalizedFinancialRecord(tenant_id='t', normalized_id='row', record_type='POSITION', source_refs=(42,))
MALFORMED_LINEAGE_RECONCILIATION AttributeError 'int' object has no attribute 'tenant_id'
WHITESPACE_TENANT_ACCEPTED TenantContext(tenant_id=' ', principal_id=' ')
OWNER_TARGETED_TESTS 7 passed; mini_pytest shim, not pytest; source-pinned import loader
```

### Current owner metadata and next route

The owner now publishes `CURRENT_HANDOFF.md`, `STATUS.md`, `THREAT_MODEL.md`, automation state, seven focused tests and a workflow. Earlier absence-of-artifact findings are **SUPERSEDED** by those exact successor artifacts. The workflow's existence is not an observed Actions result. Owner handoff says contract foundation only; no operational platform claim. Owner capability matrix promotes no capability to VERIFIED and retains auth/API/durable sync/store gaps.

Owner state pins canonical `b8e39a2`, Global `b3532a2` and FPIA PR42 `11d2f25`; it records `lease: null`, `pending_ci: []`, `checkpoint: initial_contract_foundation`. Null lease is recorded metadata, not inactivity proof or authority for another writer. The owner branch remains read-only to this audit.

The existing owner paths above supersede the proposed generic `implementation/docs/platform/` locations in the initial request where equivalent artifacts now exist. Remaining return requirements are current reference-validation/missing-data closure, authenticated user+tenant/raw-record boundaries when implemented, exact independent evidence, and an explicit write-set/overlap acceptance document such as `implementation/docs/product_platform_audit/WRITE_SET.md` (not present at this pin). Owner test location is the actual `implementation/tests/test_product_platform_contracts.py`; do not require a duplicate test tree solely to satisfy a proposed path.

CDR-017 coordinator routing still applies. Our `product_platform/` remains a synthetic independent audit harness semantically overlapping the owner's contract foundation; neither new owner files nor passing focused tests admit our namespace as production authority. Continue file-disjoint independent audit work, route the remaining exact findings and write-set decision through the coordinator, and re-consume owner evidence before closing current blockers.
