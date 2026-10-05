# Fresh takeover and first implementation gate

Canonical: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Global: `5e33b30ce47b1875ae3b91fb3ba25d3158947e66` (GCH-015 + CDR-016). Fresh clone and independent GitHub branch/PR API reads executed. Canonical worktree was empty after no-checkout clone, then initialized on a new scoped branch; no existing work discarded. No AGENTS.md exists in this tree. Operational worker contract #21 exact `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798` read; current attached Work scope takes precedence.

| Area | Existing authority / exact owner | Reuse / additive gap |
|---|---|---|
| Identity | canonical contracts/global_universe.py | Reuse IssuerIdentity/SecurityIdentity/ListingIdentity, dated listing; production mappings absent; synthetic records explicitly fixture-only |
| Broker | canonical personal/ports.py | Reuse BrokerAdapter read-only contract through candidate bridge; add runtime capability rejection and tenant context |
| Money / actual portfolio | canonical personal/money.py, personal/portfolio.py | Reuse Decimal Money and ActualPortfolioSnapshot.total_value/weights; externally reject nonfinite/mixed currency/incomplete denominator; no Frozen patch |
| Target/model | canonical qgv/book.py, qgv/portfolio.py | Model/reference only; not accepted as actual account input |
| Raw/PIT | canonical ingestion/raw_store.py, personal/timecontract.py | Research raw store is unscoped/unverified on read; financial receipts need private scoped storage and hash verification; available time must be explicit |
| Auth/Tenant | no implemented canonical auth/session/tenant service | Add trusted auth adapter, fixture sessions, authorization, scoped SQLite, synthetic audit; real provider/vault pending |
| Producer | #9 f8af596df4d235fee1f29bf0cb6c9a3cc0f89f36 | Existing producer envelope and validation remain authoritative; no rewrite; operational outputs missing |
| Web | #5 a4e49c83f5783c19617fb609b8f95b179cb13e84; #36 fb086eac4321140493ce554a541343cebbb81ed6 | Isolated verbatim build; preserve assets; separate additive account UI/API; no security→company inference |
| P01 | #17 21039a0a7f9677b123abd8587fd8d89784a73a3c | Research grants NONE; target authority unresolved; do not fabricate permission for actual/synthetic finance |
| Chart | #41 74df6784071137bdca911964af94c8e1b6928c92 | ChartDocument v0.2 PROPOSED, production API/renderer absent, six owner gates; explicitly unavailable adapter |
| QGV vNext | spec #44 cb1906b207623168fd70f3dcdb5b30f2d82d807d; decision branch 4fb08a05728d83519b72a2bd995669f0cb06003a | INACTIVE/SPEC-ONLY; runtime/missing-data/V/composite remain untouched |
| Technical/Macro/RIG | existing engines plus owner branches | Preserve semantics; do not execute integrated order_intents; unavailable producer authority remains visible |
| Integration/FPIA | #42 523e702a806a718d163cfbf62aa3fc29d8c3ef3c | Existing owner round-3 repairs ongoing; added package changes whole-package identity on later merge; exact integrated-tree FPIA remains NOT_RUN |
| Track C | owner #31 c9e0fa7e4078290b5db9cb798cf52c0d0cd66240; #4 ff78c4f6c4a1a8fd15db21807de6be3905c89548 | No imports, method changes, Holdout or freeze operations; seven-file P01 source bytes unchanged, whole-package hash DIVERGED upon integration |

Focused existing read-only tests: identity/money/portfolio/P0/common hierarchy **35 PASS via mini_pytest shim**. Probes exposed existing nonfinite Money acceptance, first-strong-key resolution, incomplete denominator ratios and model-side "actual" weights; these are guarded at the additive adapter boundary, not repaired in Frozen source.

## Gap / implementation gate

Auth, tenant authorization, immutable normalized financial revisions, connection/SyncRun/cursor, reconciliation, private raw provenance, account API and read-only hard gate are D2 additive gaps. Shared contract and negative-test design are in CONTRACT.md. Independent auth and connector writers consume that single domain module; root owns storage/service; no overlapping write paths.

First runnable scope: two fixture users → fixture login/session → synthetic connection → account/balances/positions/transactions → append-only sync → reported-value reconciliation → existing ActualPortfolioSnapshot calculations → authorized API and mobile account view. This advances synthetic module maturity only.

Full first-slice acceptance is dependency-blocked on an admitted production ChartDocument/renderer and accepted Web/Product integration contract. Existing research scores are NOT_AVAILABLE, not zero. Broker credential/provider onboarding, real vault, retention/legal choices, paid API, deployment and canonical merge are outside the current attached scope. No additional user decision is needed to implement and test the independent synthetic slice.

## Fresh final intake delta

Global advanced to `b3532a2ebbe95310bbf222937466eb04a0211263` (CDR-017 coordinator routing). Chart advanced to `ebeb8b1f2693703d33cff2610c277c7ce3dcbb18`, retaining six OPEN gates and 0/19 market admission. FPIA round-3 subject is `11d2f25ef8bef3459ca969f50eec190099f15ecb`; its exact FPIA run remains pending at intake.

New `codex/product-platform-audit-v1` owner `9e524ef2033d5ee99961d5b88fbc3e92836b8305` adds `investment_system.platform` contracts. Those are source-pinned reviewed in OWNER_FINDINGS.md and not overwritten. Our separate `product_platform` implementation remains synthetic audit-only despite semantic overlap. Owner source/handoff must be fresh-read before any contract reuse or production admission. Earlier table pins are preserved as intake history, not current claims. Final STATUS.md/evidence provide the current subjects.

Pre-publication owner successor `c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9` was fresh-read with its new `implementation/docs/product_platform_audit/CURRENT_HANDOFF.md`, STATUS and STATE. Independent package import/all exports and 7 focused owner tests pass; initial import findings are CLOSED. Malformed provenance, trusted runtime ownership and durable authenticated ledger remain open/acknowledged. Auth and admitted Product API are NOT_STARTED; our separate audit fixtures are not promoted into owner product status.
