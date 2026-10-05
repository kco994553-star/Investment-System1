# Product Platform Audit · STATUS

Status date: 2026-10-05
Owner branch: `codex/product-platform-audit-v1`
Base: canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`

## Fresh baseline

- Global routing observed at `b3532a2ebbe95310bbf222937466eb04a0211263`; CDR-017 assigns Product Platform auth/tenant/connector/reconciliation to this scoped Work.
- No Product Platform owner branch or PR existed at audit start.
- Reused Track B contracts: READ-ONLY `BrokerAdapter`, BROKER/USER_ENTERED `ActualPortfolioSnapshot`, PIT-aware `TimeStamps`.
- Reused Web boundary: PR #5 is static/read-only and consumes producer-reviewed bundles; later Web/P01 work remains other-owner scope.

## Capability matrix

| Capability | Fresh state | Evidence / blocker |
|---|---|---|
| Auth / login | NOT_STARTED | no product login/session/auth-provider implementation found |
| Tenant isolation | IMPLEMENTED (contract layer) | fail-closed tenant context added; no service/database enforcement |
| Financial Connector | PARTIAL | existing Track B BrokerAdapter is read-only; no real provider |
| Financial record sync/import | PARTIAL | adapter sync contract + immutable/idempotent import oracle; no durable/provider sync |
| Reconciliation | IMPLEMENTED (contract layer) | deterministic source-to-normalized lineage check; no account E2E |
| Immutable/auditable records | IMPLEMENTED (contract layer) | immutable source ref, version, hash, raw ref, timestamps; no durable append-only store |
| Read-only hard gate | IMPLEMENTED (contract layer) | exact BrokerAdapter allowlist, unknown/write methods fail closed; no API boundary yet |
| Product API | NOT_STARTED | no authenticated service/API layer found |
| Web/PWA | PARTIAL | static Web MVP/presentation guards exist; no login/PWA/service backend |
| Investment-engine integration | PARTIAL | Web consumes finished bundles; Track B ports preserve upstream boundaries |
| Provenance/publication authority | PARTIAL | producer/P01 contracts exist separately; account-page authority unresolved |
| Security/privacy | PARTIAL | fail-closed contracts; real auth/secrets/tenant service absent |
| Failure recovery | DESIGN_ONLY | sync status exists; no durable checkpoint/revocation/recovery |

No capability is promoted to VERIFIED: no real auth, multi-tenant service, financial account, or persistent store has been exercised E2E.

## New D1/D2 work

1. Reuse existing BrokerAdapter rather than create a second connector interface.
2. Add exact allowlist read-only hard gate.
3. Add fail-closed tenant scoping with no global fallback.
4. Add immutable provider-record identity and explicit source version/hash/raw reference/timestamps.
5. Add idempotent import oracle: exact replay is duplicate; conflicting same-version content fails.
6. Add deterministic reconciliation for missing/orphan lineage, duplicate normalized IDs, and cross-tenant outputs.

These are non-production contracts/mocks only.

## Findings

- PPA-F01 BLOCKING: no authentication/session implementation.
- PPA-F02 BLOCKING: no runtime tenant enforcement beyond the new contract layer.
- PPA-F03 BLOCKING: no concrete financial connector, consent/token store, revocation, durable checkpoint, or pagination state.
- PPA-F04 BLOCKING: no authenticated Product API; static Web must not be treated as secure personal-data hosting.
- PPA-F05 BLOCKING: no durable append-only financial-record ledger.
- PPA-F06 POSITIVE: existing BrokerAdapter already excludes trading/transfers; explicit gate now enforces that allowlist.
- PPA-F07 POSITIVE: actual portfolio remains separate from model target weights.

## Owner routing

Primary Integration Coordinator should route:
- Product/P01: publication/read authority for account-derived/user-authored pages.
- Web/Product: authenticated API projection route without frontend financial recomputation.
- Portfolio/Identity: authoritative imported-position security mapping.
- Integration/FPIA: acceptance once package-level production code is proposed.

No paid connector or real credential action is requested.
