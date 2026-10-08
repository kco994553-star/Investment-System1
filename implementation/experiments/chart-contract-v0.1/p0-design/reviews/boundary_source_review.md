# P0 Chart Contract — independent architecture / protected-boundary review

Read-only review. No source, owner branch, publication grant, Frozen record or canonical change. The current user request authorizes contract/gap/dependency design, not production activation. Findings use fresh local Git objects supplied by the parent audit, not previous conversation claims.

## Pinned evidence

- Canonical: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
- PR #41 audit/experiment baseline: `8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf`.
- Integration trial #40: `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` (non-canonical).
- Global routing handoff: `bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88`, `implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md`, GCH-014.
- All `pr/40` paths below are reviewed from that trial, not assumed present on canonical. PR #41 is isolated on canonical.

## Overall judgment

Shared domain/product contract is the correct next dependency, but there is no existing production chart section to turn on. A single owner-controlled assembly path must create immutable chart documents from existing verified source/domain outputs. API, browser and future MCP consume the same document ID/hash and capability-specific state. They must not independently fetch, classify, aggregate financial values or upgrade publication eligibility.

Keep the audit denominator split exactly: Core 81 / Extended 24 / Research Candidate 8. Nothing here promotes candidates or creates 113 implementation tickets. Scope for the first operational increment is daily Market OHLCV plus Portfolio industry composition, type exposure and exact-set type overlap. V/Reverse DCF/MOS/scenario-target semantics remain a dependency on QGV scoring reconciliation, not fields with provisional production numbers.

## Existing reusable boundaries and actual gaps

| Existing path | Actual capability | Gap / implication |
|---|---|---|
| `producers/serialization.py:to_jsonable, canonical_bytes, canonical_sha256` | One deterministic, finite-valued canonical JSON path | Reuse canonical hashing; don't create transport-specific payload/hash rules. Decimal portfolio serialization requires an explicit adapter preserving existing precision; current serializer has no Decimal branch. |
| `producers/contract.py:make_snapshot, validate_snapshot, verify_inputs` | Timestamp/state checks, source artifact hashes, payload hash, synthetic and validation/publication checks | Has section allowlist from Web schema 1; no Market section and no typed OHLCV payload semantics. Schema validation alone does not verify actual referenced bytes: call `verify_inputs` with the store resolver. |
| `producers/assembler.py:assemble_bundle, write_bundle_atomic` | Validates and combines all existing sections without calculation, preserves producer metadata and hashes | Rejects unknown sections. A Market section cannot be silently injected. Changing assembler is a protected owner task. |
| `producers/adapters.py:portfolio_section` | Verbatim legacy `contracts.models.PortfolioSnapshot` serialization | Explicit compatibility table says PARTIAL: return, market_value, currency and exposure absent. No conversion to actual holdings or industrial/type chart datasets. |
| `personal/portfolio.py:ModelPortfolioSnapshot, ActualPortfolioSnapshot, weights, portfolio_gap` | Distinct model target and actual broker/user positions; cross-account aggregation, base-currency guard, incomplete snapshot missing != zero | Reuse these domain objects/calculations. Legacy `Holding.actual_weight` is explicitly prohibited as an actual position input. Actual ingestion and sourced classification snapshots still need wiring. |
| `personal/money.py:convert`; `personal/timecontract.py`; `personal/security.py` | Existing FX/time/identity boundaries | Preserve their policy and provenance; don't introduce chart-side FX or merge company/security identities. Broker adapter interface in `personal/ports.py` is not proof of operational ingestion. |
| `sessions/binder.py:bind_yahoo_bars`; `sessions/calendar.py`; `sessions/listing.py` | Hash-pinned raw bars, listing/calendar/timezone identity and close lower-bound eligibility | `BoundBar` contains close and volume only, not OHLC. Close lower bound is not vendor publication time. Current STATUS explicitly has no exchange-issued real vintage replay. Must reuse owner session logic, request additive owner extension if OHLC preservation is needed. |
| `product/web_mvp.py:validate_bundle, build` | Static read-only product builder; no engine execution | Existing sections lack Market. Existing Portfolio frontend expects a different summary shape. New schema/manifest route must be designed with Web owner before modifying it. |
| `publication/predicate.py:decide`; `publication/envelope.py:attach_publication_envelope` | P01 grants and non-promotion; default active grants empty; additive envelope outside section data | Producer PASS is not a grant. Production attach cannot activate DISPLAY_RESEARCH. Chart contract must not use verified=true as authority to bypass P01. |
| `product/web_assets/app.js:guardSections`; `tests/test_web_research_guard.py` | Render-time mirror rejects research/invalid production-labelled payloads | Apply same guard to new chart surfaces and all API/MCP responses; do not send withheld values and merely hide them in browser. |
| PR41 `contract.mjs`, `raw_store_bridge.mjs`, `portfolio_contract.mjs` | Useful immutable candidate normalizer, source-byte checks, synthetic/reference chart projections | Explicitly nonproduction. Market identity strings are supplied, not verified; availability/finality/basis remain unknown. Portfolio integer-unit demonstration must not silently replace Decimal/float owner arithmetic or create a rounding policy. |

## Proposed separation of responsibilities (design only)

1. Existing provider/raw store acquires bytes and preserves fetch time, request, original source and hash.
2. Existing domain owners validate security/listing/session/adjustment/availability or model/actual portfolio snapshots. Join sourced classification assertions by stable identity and time; never infer type from display text.
3. One chart product adapter produces a versioned immutable document, carries domain references and scoped quality/availability reasons, and derives only presentation-ready grouping of already authoritative weights. Industry/type/overlap projections share the same resolved holdings, denominator and classification snapshot.
4. Existing provenance and publication decisions bind to that document hash. Public product output is withheld if no supported eligible state exists. Internal diagnostic candidates may retain evidence but must be inaccessible through a production-display bypass.
5. Static Web manifest, read API and future MCP expose identical authorized document identity/content. API/MCP filter/search/range requests must identify the same immutable source snapshot and semantics. They do not separately rescore, reweight, guess sessions or fetch current data to fill historical holes.

A sidecar chart document referenced by a versioned product manifest is a viable additive design, but it is not an authorization loophole. Whether to extend schema 1 or introduce a successor product manifest is an owner integration decision because section guards and P01 digest pins cover current entrypoints. Do not choose a new deployed route solely to avoid existing tests.

## Contract constraints that must remain explicit

- Verification, source actuality, publication eligibility, freshness and quote delivery state are independent axes. A valid real daily bar is not automatically LIVE, PIT-safe, officially approved or even display-authorized.
- Market `observed_at`/bar timestamp, session start/end, vendor `available_at`, local fetch/persist time, requested `as_of` and vintage time are distinct. A historical session timestamp cannot become availability; session close proves only a lower bound. Retrieval today cannot establish past knowability.
- `security_id`, `company_id`, `listing_id`, symbol and exchange must remain distinct; source mapping has effective interval and availability provenance. `TEL` cannot resolve by ticker string alone.
- Price and volume basis require explicit scope: raw/split/dividend/total-return semantics, source corporate-action evidence and adjusted-vintage cutoff. Do not mix adjclose with unadjusted OHL or imply adjusted volume from adjusted close.
- Unknown source fields remain null with reasons. Do not interpolate bars, fabricate volume, use current exchange state to label historical bars, or infer real-time/delayed status from fetch time.
- Portfolio TARGET and ACTUAL snapshots retain separate identities, timestamps and source sets. Actual incomplete account scope cannot become a complete allocation pie. Existing actual weights may represent only captured holdings; completeness must be preserved and full-portfolio coverage not asserted.
- Industry user allocation groups and standard taxonomy classifications must be visibly distinguished. Each classification has subject, taxonomy/version, assertion source/hash, effective interval and known-at/available-at evidence. Unknown versus explicit no-type must remain distinct.
- Type exposure sums may exceed 100%; independent type rings use one portfolio denominator. Exact-set overlap partitions are mutually exclusive and sum to the covered denominator, including explicit unknown/no-types/cash as applicable. Neither chart should normalize overlapping exposures back to 100%.
- Transport contract should omit raw account identifiers where unnecessary; preserve scoped provenance references without exposing broker credentials or account details. No credentials are needed for this design review.

## Protected changes requiring report/owner action before implementation

| Proposed operation | Why coordination is required |
|---|---|
| Modify `product/web_mvp.py` or `producers/assembler.py` | Exact bytes are in `tests/test_p01_research_publication.py:test_protected_engine_bytes_are_unchanged` (lines 425–449). GCH-014 §5.1c explicitly says Web validator hardening needs protected-digest repin and is not autonomous. |
| Add/change Python under `src/investment_system` | `evl/calibration_contracts.py:code_hash` (74–77) hashes every package `*.py`. Even unrelated additions cause Track C source identity DIVERGED. CDR-014 FPIA acceptance is owned by Primary Integration Writer; preserve old exact-tree evidence and never normalize hashes. |
| Change session/calendar/listing code, provider parser or Technical output | Different owner branch and scoped contract. Request additive field-preserving reuse rather than editing them in chart work. No new calendar/provider availability policy. |
| Change Track B actual/FX/weight calculations or taxonomy methodology | P0 Frozen and explicit numeric/identity boundaries. Chart layer consumes output; arithmetic changes require scoped owner/user decision as applicable. |
| Enable publication, LIVE, Official, or research display | Grants remain NONE. Data/contract checks are not publication approval. |
| Canonical merge | Always separately gated and requires exact merge-result FPIA/integration evidence. |

These are implementation boundaries, not blockers to completing the present design. Documentation, gap evidence and nondeployed schema examples can be prepared now.

## Minimal dependency and verification sequence

1. Pin baseline audit scopes and reuse mapping; document proposed typed Market and Portfolio payloads and provenance/common envelope. Preserve current PR41 demos unchanged.
2. Confirm owner routing for product schema/manifest and source-hash impact. Resolve sourced security/listing records and exchange-calendar vintage for Market; sourced target/actual snapshot plus classification vintages for Portfolio.
3. Implement only after owner-boundary disposition: one source/domain adapter per domain, one product projection shared by all three Portfolio charts; one authorized delivery payload for browser/API/MCP.
4. Cheapest trustworthy checks: schema rejection vectors; original-byte replay and source hashes; real listing/session/basis/availability adversarial cases; portfolio denominator/completeness/multi-membership checks with independent oracle; payload identity across transports; renderer withheld/stale/unknown behavior; then owner-required regression/FPIA on exact proposed merge-result.
5. Production-ready declaration requires real evidence on that exact version, not only fixture/browser PASS. Existing 75 PR41 tests remain valuable regression evidence but prove candidate/reference/DEMO scope only.

Tests were not rerun for this read-only architecture review; relevant code and existing test definitions were inspected. No new policy, numeric threshold, epsilon, taxonomy assignment, provider subscription or grant was introduced.
