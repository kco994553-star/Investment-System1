# Provider-neutral statement/raw admission fixture — 2026-10-05

Continues the user's Risk-Proportional Verification policy in the independent audit write set. One auditor; no second Product implementation. The owner source is unchanged at 78a51462f89eac8e34647cddc4e53ed97e831178, so prior SA01/SA02, 9+78 owner checks and completed repository/CI receipts were not replayed. Supabase remains NOT_CONFIRMED / NOT_RUN without further discovery.

## Fresh owner/Main intake

Canonical remains b8e39a2196a6d7794a04a0cd5393c68329e126ca. Global was read at 51056c1c1ba051a1892801c7763cd86ada505f7d; current Main CDR-018 writer is gpt-work-main-2026-10-05-3a80dcef6444, with no active lease in that observed state. Global remains read-only here. Main's [return5989182963](https://github.com/kco994553-star/Investment-System1/pull/45#issuecomment-5989182963) consumes independent report11dba838 and routes SA01/SA02 once. It explicitly requires an accountable Platform source writer/write set; delivery is not that owner's ACK. The later b517a098 transferable patch has no observed Main acceptance yet.

The synthetic fixture below is independently executable while owner action is pending. It provides concrete acceptance examples for PPF-004 financial completeness, PPF-006 raw preservation and SA03 source-version conflict admission. It does not close any of them on an actual Product runtime.

## New artifacts and verification

[fixture.json](fixture.json) supplies four exact raw files: opening, historical BUY, historical DIVIDEND, closing statement. Every raw byte sequence has a pinned SHA-256 and an owner SourceRecord. Existing owner ImportLedger deduplicates replay and rejects conflicting content for an identical source version before the owner lineage helper is called. Metadata/hash checks remain a local fixture wrapper in [oracle.py](oracle.py), not an adopted production boundary.

The independently specified fixture values are:

| Quantity | Opening | Explicit reported deltas | Closing statement |
|---|---|---|---|
| Cash, USD | 1000.00 | -125.00 +10.00 | 885.00 |
| Synthetic instrument quantity | 10.000 | +5.000 +0.000 | 15.000 |
| Closing value | — | 15 × reported closing price25.00 | 375.00 |
| Total, USD | — | closing cash885.00 + market value375.00 | 1260.00 |

This oracle consumes explicit reported deltas using exact Fraction arithmetic; it does not derive trade execution, settlement, tax, cost basis, FX or corporate actions. No tolerance/rounding policy is added. Original decimal strings/precision remain in the raw files; rational result strings are test output only. The statement's included-record list is an explicit synthetic coverage assertion, not proof of an external provider's completeness.

[tests.py](tests.py): **23/23 PASS**, stdlib unittest, [GREEN.txt](GREEN.txt). Includes valid statement, input-order independence and exact replay; missing/empty/raw-tampered input; same-version conflicting content; retained correction versions; foreign tenant/context; raw-account metadata binding; mixed currency; exact tiny cash mismatch, quantity/market-value/total mismatch; no ACTUAL fallback from TARGET; extra secret-like fields; duplicate JSON keys; future availability; omitted statement manifest entry; nonfinite/binary-float numbers. Existing owner lineage/ImportLedger are consumed, not rewritten.

Tests were written against an intentionally incomplete local scaffold first: [RED.txt](RED.txt), 20 tests with17 assertion failures and2 missing-report errors,1 control PASS. These are scaffold failures, **not19 new owner defects**. [FIRST_GREEN.txt](FIRST_GREEN.txt) records20/20; three extra numeric/order controls motivated by the new oracle's trust boundary produce the final23/23. This is a finite new-fixture check, not a repeat of prior owner counterexamples or a full regression.

No same-tenant cross-user service/auth check was executed by this fixture, because the owner has no authenticated runtime. Existing fixture auth/session/user-access receipts are retained; Product cross-user prevention, Auth/session/revocation and trusted runtime ownership remain unverified. Original-byte hash matching here proves correspondence to a local pinned fixture manifest, not external authentication, signature authority, remote immutability or durable storage. Retaining v1/v2 in an input map does not choose a correction revision for an account view.

## Owner handoff and actual blocker outcome

Current Main should route [MAIN_HANDOFF.md](MAIN_HANDOFF.md) and the prior [SA01/SA02 source patch](../risk_proportional_2026-10-05/SA01_SA02_candidate.patch) to an accountable source owner. New fixture acceptance preparation is complete; Main consumption of these artifacts and owner adoption remain NOT_CONFIRMED. Any GitHub routing comment is delivery only.

| Metric | This execution |
|---|---|
| Product blockers start | 9, same deduplicated inventory as b517a098 |
| Closed on actual owner implementation | 0 |
| New Product blockers | 0 |
| End / net reduction | 9 / **0; target >0 not achieved** |
| Verified whole Product capabilities | 0 |
| Owner actions remaining | 9 groups; SA01/SA02 patch-ready, reconciliation/raw groups now have concrete fixture evidence |
| Tool-blocked items | 1: optional Supabase remote audit, approved DEV target absent |

Do not turn this completed fixture preparation into Product blocker closure. The current source owner has not returned a successor. Main routing progress is recorded separately and does not change these counts.

| Capability | Current maturity | Exact verified scope / remaining boundary |
|---|---|---|
| Auth | NOT_STARTED | No admitted Product login/session/revocation |
| Tenant isolation | PARTIAL | Owner tenant contracts reused; new foreign-tenant negatives PASS; runtime user+tenant enforcement absent |
| Financial Connector | PARTIAL | Existing read-only abstraction; no real provider/consent/token lifecycle |
| Financial sync/import | PARTIAL | Existing version/replay ledger consumed in new raw fixture; actual durable/provider sync absent |
| Reconciliation | PARTIAL | New conditional single-currency statement fixture23/23; actual completeness/amount admission unimplemented |
| Immutable/auditable records | PARTIAL | Pinned local original bytes/hash binding and correction-retention fixture; authenticated durable external ledger absent |
| Read-only hard gate | PARTIAL | Prior source-patch/dispatch receipts retained; historical BUY is input only, execution NOT_RUN; owner/runtime adoption absent |
| Product API | NOT_STARTED | No admitted authenticated API |
| Web/PWA | PARTIAL | Existing static Web; PPA-F08 owner action and runtime/PWA/browser acceptance pending |
| Investment-engine integration | PARTIAL | Existing types/synthetic reuse retained; production Platform admission and exact-result FPIA unverified |

Actual tools: GitHub MCP fresh reads/publication/routing, local Git/Python deterministic fixture verification, existing Automations prompt checkpoint update. No new Context7 query or external service-resource call; prior official version-matched docs and current-stage Superpowers verification/TDD procedure are retained. Source owner, Global/canonical, existing harness source, tenant policy, production auth, real accounts/credentials, paid resources, protected semantics and deployment are unchanged. All artifacts are confined to own audit documentation/fixtures.
