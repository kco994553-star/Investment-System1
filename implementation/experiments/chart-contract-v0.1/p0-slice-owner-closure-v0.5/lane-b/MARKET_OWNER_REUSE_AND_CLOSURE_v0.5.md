# Lane B — existing owner capability reuse and admission closure v0.5

Read-only assessment at Chart PR #41 `d93c7ace37603d91f1d9342152c97e8acb3d4e8c`; canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`; US Session PR #18 `2c088cea34314af0ccc33fd2e2dc1ccf21502cb4`; Integration PR #42 `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`. Parent work fresh-read these refs. Commit-pinned bytes are audited here. No price/action/source fetch, calendar construction, security-ID allocation, package modification, or source admission occurred.

## Verdict

**Production Market admission remains 0/19, BLOCKED 19/19. Eight shared evidence families and 152 non-ready cells remain unchanged.** The existing engines reduce future implementation work; their presence does not supply admitted input records. No new existing source closes a required production cell. The retained 23,155 rows, structural 17 READY / 2 PARTIAL, and five anomaly records remain unchanged.

This bounded delta identifies exact reusable owner functions, input preconditions and acceptance receipts. The prior v0.3/v0.4 field matrix, raw payloads, hashes, anomaly causes and history are referenced rather than rewritten. These outputs are evidence/design proposals, not production contract adoption or an FPIA review.

## Existing identity contracts and actual lookup data

| Existing capability | Reuse | What is still absent |
|---|---|---|
| `contracts/global_universe.py`: `IssuerIdentity`, `SecurityIdentity`, `ListingIdentity`, `EligibilityRecord` | Use the canonical issuer → security → dated listing shapes, half-open listing dates, and explicit eligibility PIT/evidence check | Loaded, owner-admitted issuer/security/listing records for the 19 priced instruments and intervals |
| `rig/gate.py`: `IdentityLookup` | Existing read-only interface to Track A-owned common identity records | Production implementation/data for this Chart set; protocol presence is not a lookup |
| `personal/security.py`: `InMemorySecurityResolver.resolve` | Resolve only explicit active records; strong ISIN/FIGI or ticker+venue; ambiguity fails closed | Actual 19 records, economic evidence and explicit link to common identity; no new IDs may be derived from strings |
| `personal/security.py`: `CompanyLink` | Preserve the separate personal `security_id` ↔ legacy `company_id` boundary | The existing contract defaults to PROPOSED; no reviewed mapping for these rows |
| `qgv/identifiers.py`: `IdentifierRegistry` | Keep existing aliases and TEL ambiguity | Nineteen company-level aliases are not issuer/security/listing admission; Tokyo's legacy TEL does not authorize a domestic-8035 or ADR mapping |
| `universe/resolve.py`: `resolve_roster`, `current_ticker_map` | Reuse dated ticker→CIK/company resolution within its own roster scope | CIK/company resolution is not economic security/share-class/listing continuity; current map must not be applied backward |

Constructor searches across source, tools and tests found common identity and personal explicit security records only in fixtures; no production 19-security lookup was found. The Track A price-identity report has source-name/CIK candidates for all 17 US symbols, but its own scope states that name tokens are not legal security identity proof. The report's provider hashes identify older observations, not the current Chart payloads. This is corroboration, not admitted ID generation. The Target-source lane uses the same null security boundary independently.

## PR #18 session reuse: exact contract, no second engine

The `sessions` code is absent from canonical/Chart HEAD and present byte-identically in PR #18 and PR #42. Reuse requires the selected owner-approved integration tree; Chart does not copy the package into its branch.

| Reusable function/object | Required inputs and exact refusal boundary |
|---|---|
| `calendar.load_calendar_vintage` / `CalendarVintage` | Immutable schema body/hash, venue, complete explicit OPEN/CLOSED rows, source hashes/notices, `row_available_at`, exact runtime IANA version; absent rows are not generated sessions |
| `listing.ListingEvidence` | One common `ListingIdentity`, timezone-aware evidence availability, evidence ID/hash; constructor validates shape, not the underlying source's economic facts |
| `binder.listing_refusal` | More than one interval is not stitched; ticker reuse/venue transfers remain split |
| `binder.bind_yahoo_bars` | Exact raw body/hash, admitted calendar and listing at decision time, explicit NMS→XNAS/NYQ→XNYS/PCX→ARCX relation, every timestamp equals one OPEN-row UTC open, one listing covers every row, chronological unique bars |
| `research.bind_research_inputs` | Reuses binder before the unchanged Technical model; lineage carries calendar/listing/tzdata/raw hashes; readiness flags remain false |

The calendar v1 is **US REGULAR / America/New_York only**. JPX lunch break and dated close change, KRX CSAT exception and provider label conflict require their own owner evidence/contract; these are not US calendar aliases. No foreign calendar or session engine is built here.

The loader checks notice bytes when `notices` is supplied; that argument is optional. For production admission the owner must provide/cross-check the actual pinned notice bytes and the source-supported meaning of each row's availability. A caller-supplied date passing a constructor is not evidence of public availability. `CalendarVintage.admissible_at` checks *all* row availability times; a future-known row makes the entire supplied vintage inadmissible.

`bind_yahoo_bars` returns close/volume plus session identity, not full OHLCV/basis admission. It does not supply an economic identity catalogue, adjustment semantics, source historical publication/finality, or quote-state. Its meta checks do not independently certify price currency; a Chart owner binding must retain/validate that relation separately.

## Close guard is not historical source availability

`research.GUARD` explicitly declares `CANONICAL_SESSION_CLOSE_LOWER_BOUND`, `provider_publication_timestamp=False`, `observed_at_overwritten=False`. The binder uses `eligible = decision_time >= row.close_utc`. This blocks a daily close before the dated session close; it does **not** claim Yahoo published/finalized that exact bar at close.

The inherited `technical/pit_market.py::bars_from_yahoo_chart` still assigns `available_at = observed_at = Yahoo bar timestamp`, and the older provider stamp uses the same value for published/available/observed. PR #18 explicitly leaves those legacy stamps untouched. Existing software behavior is not newly admitted historical evidence. Neither a close guard nor a passing test converts the provider bar label/open, source latest quote time, calendar notice date, present acquisition/ingestion time or final market close into historical per-bar `available_at`.

Time roles remain separate: bar date/label; event time; dated session open/close; provider timestamp; current collector observation; historical source availability; knowledge/access time; ingestion/persistence. Unproved values remain null/UNKNOWN/NOT_AVAILABLE. No PIT relaxation is proposed.

## Existing provider, parser, store and corporate-action reuse

| Capability | Reuse scope | Restriction for OHLCV production |
|---|---|---|
| `RawDatasetStore.get_bytes/get_manifest/list_history` and acquisition `_get` | Original bytes and immutable hash/provenance/history conventions; original Chart captures stay at their current paths | Manifests alone are not bytes; fetched time is ingestion, not historical availability; do not ingest/rewrite originals to manufacture a vintage |
| `providers/yahoo_chart.py::parse_bars` / `ingestion.replay.load_price_bars` | Existing close/adjclose scalar replay and provider symbol facts | Casts values to float, skips null-close rows, omits O/H/L/V; therefore cannot be used as a lossless full-candle admission adapter |
| `technical/pit_market.py::bars_from_yahoo_chart` | Retains null close/volume and source ordering for the Technical/session scope | Omits O/H/L, uses float and inherited availability stamp; not a full candle/basis/availability contract |
| `audit_mcap_store.py::load_splits`, `split_factor_after`, `mcap_price` | Existing split discovery/reconstruction for historical market-cap scalar close | Market-cap policy/assumptions do not authorize adjusted OHLCV, dividends/volume transforms, return-series choice or complete action ledger |
| `ca_unit_policy.py::provider_events`, `document_errors`, `reconcile` | Verified primary-document bytes/hash/url/quoted facts and transactionally reviewed share-unit normalization | This is share-count/mcap reconciliation, not a candle adjustment engine or price publication/finality source |
| `prepare_ca_unit_evidence.py` and approved `ca_unit_policy_v1.json` | Existing source pins and event evidence can be referenced without copying or refetching | NVDA has one reviewed 2024 split event. GE's reviewed parent spin-off is scoped to GE, not a GEV identity/listing/action admission. Neither is complete five-year 19-instrument history |
| `fetch_tiingo_prices.py` | Existing close-only raw fallback in its approved market-cap scope | Derived close-only payload has fixed 21:00 UTC date labels; no OHLCV recovery, session proof or historical availability may be inferred |

The bundled NVDA primary source matches its policy hash. This supplies a reusable event/source fact, not a new production-readiness promotion. Other current provider action candidates and exact adjclose differences remain the prior observations. No new adjustment engine is designed or executed, and token differences are not asserted to be economic revisions.

## Prioritized owner action receipts

All actions are **OWNER_ACTION_REQUIRED**. Exact machine input fields, source refs and acceptance conditions are in `MARKET_OWNER_ACTIONS_v0.5.json`.

| Priority / gap | Status for 19 | Owner receipt that can close the exact field scope |
|---|---|---|
| B01 Security identity | BLOCKED | Track A/common identity owner: source-admitted issuer/security/share-form records and explicit current/historical applicability, linked to existing IDs |
| B02 Listing/provider interval | BLOCKED | Identity/market source owner: internal dated listing/MIC/currency and exact provider-series intervals, change/reuse/delisting/continuity evidence; GEV first three rows remain unstitched |
| B03 Exchange/session/timezone | PARTIAL | Session owner PR #18 for US: real source-backed calendar vintages/notices and availability/tzdata. JP/KR owners: separate dated venue semantics including breaks/close changes/exceptions |
| B04 Dated session join | BLOCKED | Session/market owners: replay exact Chart bytes through admitted listing/calendar relation, retain every missing/conflicting bar and reason, separate source bar label from actual session open |
| B05 Adjustment basis | PARTIAL | Provider/Track A source owner: exact O/H/L/C/V/adjclose semantics, source/transform/version/revision behavior; partial scalar evidence is not full-candle basis |
| B06 Corporate action basis | PARTIAL | Source/CA owner: complete identity-continuous action ledger, source/hash and distinct announcement/record/ex/legal-effect/adjusted-trading/availability roles |
| B07 Historical available_at | NOT_AVAILABLE | Provider/PIT source owner: actual per-bar/action historical publication/revision/finality/access evidence. Absent proof stays absent; close is not proof |
| B08 Quote-state | UNKNOWN | Provider owner: exact response/feed/row state and finality semantics supported by source evidence. LIVE/DELAYED/CLOSE feed state remains distinct from Product Official/LIVE authority |

These are eight shared families, not 152 unrelated decisions. Partial symbol/interval closure may be reported without admitting the others. Anomaly/render policy and common Product/P01/code_hash/FPIA gates are separate dependencies; they do not change this family count. GICS, Type, ACTUAL, quarterly history and QGV vNext are not Market evidence sources or prerequisites to current Target Theme.

## Minimum immutable reference cases

`IMMUTABLE_MARKET_ADMISSION_CASES_v0.5.json` contains reference-only cases using existing original payload paths, full hashes, exact indices/JSON pointers and lossless raw numeric tokens. It has no invented calendar, identity, timestamp or source facts. All current identity/listing/calendar/availability/quote-state admission fields are null/unadmitted.

Cases cover: one US bar reference; GEV's three pre-regular-way candidate rows; JPX's retained envelope failure; KRX's three envelope failures plus null row; and the KRX CSAT timestamp/open conflict. The examples can be combined with real owner receipts later. A fixture with invented IDs/notice dates/calendar rows cannot close these source gates.

## Verification and boundary

Commit-pinned function/source hashes, parity of unchanged canonical/common identity and PR #18/PR #42 sessions, all 19 original payload hashes/row counts, unchanged 19×8 statuses, all five preserved anomaly tokens/indices, source-pin NVDA bytes, parser/guard semantics and the minimal raw-reference cases are checked offline by `verify_owner_reuse.py`. It reads existing evidence and prints a receipt; it writes no source files and makes no network requests. This is evidence verification, not production regression or end-to-end source admission. Production tests and Chart merge-result FPIA remain NOT_RUN.

Only new files under this scoped non-package lane are written. Protected Web/assembler/P01 digest files, package Python, Frozen contracts, owner branches, grants, Holdout, Official/LIVE and canonical are unchanged. The same upcoming owner-approved tree must be evaluated for P01 digest, whole-package Track C code_hash and exact merge-result FPIA by the Integration owner; present green FPIA is not Chart approval.

Next exact step: obtain B01/B02 owner-admitted existing-ID and provider-interval receipts, then apply the existing US session binder to actual source-backed calendar/listing inputs. In parallel request B05/B06 basis receipts; B07/B08 cannot be closed by guessed timestamps or UI calculations. Keep readiness blocked until the relevant exact symbol/interval predicates pass.
