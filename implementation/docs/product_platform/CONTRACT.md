# Product Platform Foundation v0.1 — synthetic read-only contract

Authority: attached `Investment-System1_Product_Platform_Main_Work_v1.0.md`, §§36–44. Scope is additive D1/D2 on canonical b8e39a2196a6d7794a04a0cd5393c68329e126ca. Current scoped no-merge/no-deployment/no-real-credential instructions are narrower than Global CDR-015 and govern this Work. No existing source, Frozen record or owner branch is edited.

## One contract, multiple consumers

`investment_system.product_platform.domain` owns platform types and validation. Auth, connector, storage, service, API and UI consume it. Global IssuerIdentity → SecurityIdentity → dated ListingIdentity and personal Money/Position/ActualPortfolioSnapshot remain the existing authorities. Company links are never inferred from security IDs or tickers.

Principal = immutable user_id + tenant_id + session_id, issued only after server-side session validation. HTTP clients cannot provide tenant/user ownership fields. Every store operation uses both user and tenant, including raw receipts, revisions, jobs, cursor, snapshots and export. An unauthorized ID is indistinguishable from a missing ID.

`ReadPage(resource, body, next_cursor, complete)` is a provider response. Body is exact UTF-8 JSON bytes with `schema_version=synthetic-financial-v1`, `effective_at`, `available_at`, `provider_reported_at`, `data_state=DEMO`, and `records`. Resources: accounts, balances, positions, transactions, statements. Provider cursor is opaque; accepted only in its authorized connection/resource context. A provider-neutral FinancialConnector offers connection_status, list_accounts, sync_balances, sync_positions, sync_transactions, sync_statements and revoke_connection. Reads must advertise only READ_ACCOUNT/READ_BALANCE/READ_POSITION/READ_TRANSACTION/READ_STATEMENT. Any unknown/write capability rejects the connection and each sync. Historical BUY/SELL/TRANSFER/DEPOSIT records are input data and never execute an action.

Each record requires provider `id`, positive integer `revision`, and provider account ID (account resource uses its own ID). Reusing a revision with different normalized content fails; a higher revision appends history. Identity references require exact security/listing and dated issuer hierarchy, not ticker-only matching. Unresolved positions remain visible; analytics requiring resolved identity are unavailable.

Money/quantity is finite decimal text, with provider precision preserved; no binary float, FX, inferred cost basis, rounding or tolerance policy. Account currency must match related values. Balances: `cash`, `total`; positions: `quantity`, `market_value`, optional `security_id`/`listing_id`; transactions: `kind`, `amount`, optional security reference; statements: reference metadata only, no arbitrary URL dereference. Closed accounts remain historical records.

Raw receipts are written before normalization, scoped to ownership+connection+resource and content hash. Every normalized revision links its raw receipt. Reads verify receipt hash; raw is never replaced by normalized output. Secret-like provider keys are rejected before persistence; real credentials are not accepted. Storage is local SQLite for synthetic fixtures, not a production secret vault. SecretStorage is an adapter boundary; synthetic implementation holds only synthetic references.

All timestamps are timezone-aware; `available_at <= decision_time`, `effective_at <= decision_time`, and provider_reported_at cannot be in the future. Fetched time is never substituted for available time. Historical requests select only revisions available by that decision time. Unknown availability fails. No freshness TTL is invented: provider STALE/DELAYED is propagated, and last successful sync time remains visible.

SyncRun status: QUEUED/RUNNING/PARTIAL/SUCCEEDED/FAILED/REVOKED. Normalize a complete resource group atomically; every raw attempt remains. Pagination detects loops, bad continuation and revision collisions. Cursor advances only with committed transaction pages; partial/failed runs never replace the last complete portfolio. Same-user background operation revalidates connection scope/revocation. No cache is shared between tenants; no search/global account cache exists.

Reconciliation compares provider position market values + cash against same-time same-currency reported total exactly using existing Decimal values. Difference remains MISMATCH, never tolerance-adjusted. Transaction-to-position reconciliation is NOT_COMPARABLE absent opening balance/corporate-action history; statement reconciliation is NOT_COMPARABLE absent a statement balance. No computed transaction balance is represented as reconciled.

ActualPortfolioSnapshot is reused only for synthetic reported actual holdings, exposed as `portfolio_kind=ACTUAL`, `data_state=DEMO`, `is_real=false`. TARGET and research engine outputs stay separate. Account closure, unresolved security, partial resources, currency mismatch and stale data prevent a fully validated current snapshot. Existing analytics reuse total_value/weights; QGV/Technical/Macro outputs require their producer/publication authority and remain NOT_AVAILABLE without it.

Auth is a trusted-provider adapter and opaque server-side session abstraction, not a password/cryptography system. Synthetic login is explicitly a local fixture and cannot be production authentication. Expiry, logout, revocation, tampering, CSRF for mutations, authorization, secret-free audit and rate-limit configuration are required. Explicit test-only TTL/rate limits are not production defaults.

## Implementation/write set

- New source only: `implementation/src/investment_system/product_platform/`.
- New tests only: `implementation/tests/product_platform/`.
- New tools only: `implementation/tools/product_platform/`.
- New docs/evidence only: `implementation/docs/product_platform/`.
- New scoped workflow only: `.github/workflows/product-platform-synthetic.yml`.

Existing Web assets are consumed verbatim in an isolated integration workspace, not patched. ChartDocument has no admitted production implementation in canonical; exact Chart owner contract must be consumed when ready. A unavailable chart is reported NOT_AVAILABLE; no competing chart schema or financial calculations are added in JavaScript. This dependency blocks final end-to-end Foundation acceptance, not auth/sync/isolation work.

## Maturity / gates

Module TEST_VERIFIED means local synthetic tests passed. It does not mean REAL/LIVE/PRODUCTION_READY. Foundation complete additionally requires existing Web/PWA+ChartDocument integration, mobile browser proof, owner receipts, affected regression and security review. Production auth provider, credential vault, encryption/retention policy, real brokerage access, paid resources, deployment and canonical merge remain outside this synthetic implementation.

Acceptance tests: A/B object access including raw/export/sync/cursor, expired/revoked/tampered sessions and CSRF; capability escalation; duplicate/replayed payload/revision collision/correction/partial/outage; invalid decimal/currency/time/identity; provenance tampering; mismatch; ACTUAL≠TARGET and DEMO≠REAL; preserved existing source and regression. Every failure/repair is recorded.
