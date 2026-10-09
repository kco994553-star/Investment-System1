# P0 Market/OHLCV contract and wiring review

Read-only source review. No feature implementation, calculation policy, publication grant, Frozen or owner source was changed. PR #41 audit scope stays Core 81 / Extended 24 / Research Candidate 8.

## Exact source baselines

- Canonical: `b8e39a2196a6d7794a04a0cd5393c68329e126ca` (C below).
- Integration trial #40: `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` (T below), explicitly non-canonical.
- Chart owner #41: `8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf` (P below), explicitly non-canonical.
- Global handoff context supplied by fresh-fetch parent: `bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88`.
- Source reads were `git show`/`git grep` at these commits, not prior summaries. No execution test was needed for this design-only read; previous tests remain historical baseline evidence.

All paths below are repository-relative.

## Reuse and actual limits

| Source / symbol | What exists | What it does NOT establish |
|---|---|---|
| C `implementation/src/investment_system/contracts/global_universe.py`: `IssuerIdentity`, `SecurityIdentity`, `ListingIdentity`, `ListingIdentity.active_on` | Issuer→security→dated listing, ticker attribute, MIC, currency, exclusive end date; explicit identity invariants | Populated, provider-bound, historical security/listing mapping for all chart requests; generic company_id is not the same key as issuer_id |
| C `.../contracts/models.py`: `DataStamp` | published_at, available_at, observed_at, provider/reference, synthetic, quality flags | Source evidence is not enforced just by constructing this dataclass; `market_time_status='CLOSE'` is a default, not verified finality |
| C `.../contracts/raw.py`: `PricePoint` | company-level one price with stamp/currency | OHLCV series, security/listing binding, session, adjustment lineage |
| C `.../ingestion/raw_store.py`: `RawDatasetStore`; `.../ingestion/manifest.py`: `RawArtifactManifest`, `build_manifest` | Original bytes, source URL/kind, SHA/byte count, fetcher/HTTP result; replaced blobs archived in history | Source availability; manifest fetched_at is persistence/ingestion time; latest-slot key is not an immutable vintage selector |
| C `implementation/tools/fetch_real_data.py`: `YAHOO_CHART_URL`, `_fetch_one`, `run`; split-event URL/optional fetch | Daily Yahoo OHLCV raw response retrieval/storage; separate split-event original bytes | All required metadata verification; dividend/merger/spinoff complete event coverage; exchange feed entitlement/live delay |
| C `.../providers/yahoo_chart.py`: `parse_chart`, `parse_bars`, `pit_bar`, `to_price_point` | Existing price consumers; close/adjclose extraction and bar-date filter | `parse_bars` drops O/H/L/V and selects adjclose for generic price; `parse_chart` defaults currency to USD and missing time to now; `to_price_point` assigns available_at=observed_at. Do not promote these shortcuts into verified OHLCV contract |
| C `implementation/tests/test_yahoo_adjclose_bars.py` | Tests close vs adjclose choice for existing price path | No complete candle/volume, session, availability, adjusted-OHLC integrity proof |
| C `.../markets/us.py`: `US_LISTINGS`, `OUT_OF_US_TRACK`; `.../qgv/identifiers.py` | Existing company/provider symbol registry | Full security/listing/vintage identity. Tokyo Electron excluded unresolved and Hanmi deferred in this US scope; never infer US TEL |
| C `.../universe/sources.py`: `official_mcap500_snapshot_from_store` | Gate-audited candidates branch reuses approved raw-close × post-as_of split factor for market-cap basis | General-purpose candle adjustment policy. Keep this protected market-cap path untouched |
| T `.../technical/pit_market.py`: `PitBar`, `InputProvenance`, `bars_from_yahoo_chart`, `select_window`, `series_sha256` | Close/adjclose/volume; original-byte validation; chronological uniqueness; missing/future bar handling | Open/high/low; session close availability. `bars_from_yahoo_chart` intentionally inherits available_at=bar timestamp; not an independently certified final-bar historical availability model |
| T `.../technical/real_model_v1.py`: `publish_web_research` | Always raises PublicationError while P01 undecided | General permission to publish research indicators merely because market data is renderable |
| T `.../product/web_mvp.py` | Product states LIVE/FROZEN_SNAPSHOT/DEMO/NOT_AVAILABLE; LIVE timestamp metadata checks | LIVE here is product publication state, not a real-time quote entitlement/latency guarantee |
| P `implementation/experiments/chart-contract-v0.1/contract.mjs`: `normalizeStoredResponse`, `validateCandidate`, `renderInput` | Full explicit daily OHLCV, aligned arrays, nulls, finite/envelope/order checks, raw SHA check; separate Yahoo and Alpaca decoding; metadata unknowns preserved | Caller identity independently verified; source availability; action basis; live/delay/finality; real renderer intentionally blocked. Alpaca is schema-fixture-supported, not proven ingestion |
| P `.../raw_store_bridge.mjs`: `inspectStoredArtifact`, `readYahooRawCandidate` | Existing store layout read-only adapter, source-kind vs misleading artifact name checks, URL/request/size/hash validation, path safety | History/vintage reads, other sources, acquisition time, verified security mapping; real candidate remains NOT_AVAILABLE |
| P `.../source_replay.test.mjs`, `.../evidence/2026-10-04-source/` | Five daily NVDA OHLCV original bytes and reproducible preflight; split-event source artifact | Production series contract, all symbols, all sessions or PIT accuracy |

## Proposed shared envelope (design, not active schema)

One verified domain snapshot supplies a product projection; transport wrappers must not compute prices or financial metrics. Reuse existing identity objects and byte store. Preserve identifiers/enum meanings through references; do not invent parallel company or listing registries.

- Contract identity: schema version, domain kind, immutable snapshot/content identifier, producer and adapter version, source snapshot IDs.
- Query context: requested observation cutoff `as_of`; explicit intended usage (current display versus historical decision/replay) with capability status and reason codes. Historical usage needs a decision-time cutoff distinct from retrieval time.
- Availability/provenance: actual source `observed_at`, provider publication/availability if evidenced, acquisition_at when separately evidenced, store_persisted_at, generated_at, source vintage/revision and raw artifact immutable hash+manifest reference. Null with a reason is distinct from proven absence.
- Eligibility: product data state, PIT status, separate publication eligibility/reference, per-capability ready/partial/blocked reasons. A content hash proves identity, not publication or financial correctness. Do not equate REAL source, LIVE_FETCH, product LIVE, live market quote, and PIT_VERIFIED.
- Consumer rule: frontend/API/MCP receive the same typed validated snapshot/product projection and cannot upgrade states. MCP may add delivery envelope, never recompute or supply missing provenance. No MCP server is required to approve this design.

## Proposed Market payload and invariants

| Group | Required semantics / proposed fields | Gap / rule |
|---|---|---|
| Identity | issuer/security/listing refs, dated provider symbol mapping ref+version+source; MIC, currency; company_id retained only as explicit existing mapping | Require resolved listing for bar date and provider identity cross-check. Ticker alone, arbitrary caller IDs, or CIK alone are insufficient |
| Time | source bar timestamp and documented meaning; interval; bar_start/bar_end when known; session date/id/type; IANA exchange timezone; calendar version/source | Daily timestamp is not automatically close time or available_at. Session boundary, DST, holidays, early closes, and extended hours need an evidenced calendar adapter; unknown remains unknown |
| Values | O/H/L/C/V as explicit finite values or null with reason; price currency/units; volume unit/semantics | All present OHLC obey envelope; volume nonnegative; chronological unique bars. No null→0 or forward-fill. Candles and volume advertise separate capabilities; absent volume blocks combined-ready claim |
| Basis | quote/price adjustment basis and separate volume basis; upstream declaration vs verified status; action coverage and event refs; adjustment version/vintage | Never mix adjusted close into raw O/H/L; never assume Yahoo quotes raw/unadjusted because raw JSON was captured. Do not synthesize split/dividend adjustment factors or new policy. Empty event list cannot mean verified no actions |
| Availability | per-bar observed_at, source-available_at and evidence/reason; decision cutoff; selected raw vintage/revision | available_at must be <= decision_time for historical decision-eligible bars. fetched/persisted_at cannot stand in for source availability. Today’s revised series must not silently answer prior-as-known queries |
| Market status | feed/provider and entitlement/latency evidence, explicit live/delayed/close/unknown state, bar forming/final/corrected state; separate market session status | Product LIVE is orthogonal. No default freshness TTL/delay duration or finality from elapsed clock; late trades/revisions must preserve version lineage |
| Coverage | requested and returned range, interval, missing intervals, complete/partial, pagination status | No interval/range support advertised beyond proven source. Range selection/zoom is slice/projection; resampling would be an explicit shared-domain operation/policy, not client/individual-chart calculation |

`as_of` needs one documented meaning within each domain request. Avoid reuse as a synonym for observed_at, published_at, acquired_at, valuation time, or generated_at. A current display can explicitly show a provider series with PIT_NOT_VERIFIED only if the existing product policy permits that labelled mode; it cannot become historical-decision-ready by relaxing a gate. No new approval is assumed here.

## Production wiring and dependency order

1. Reuse existing authorized acquisition runner and RawDatasetStore; bind request/provider/source_kind to immutable selected artifact+hash. Extend selection adapter to explicit vintage refs (design only), not mutable latest-slot replay.
2. Resolve existing issuer/security/listing identities and dated provider mapping, preserving provenance. This is an adapter/binding gap, not a license to create fake IDs.
3. Use one additive MarketSeries domain adapter over original bytes. Reuse/refactor PR41 shape guards; reuse existing store/provenance checks. Leave existing canonical price-only and Technical calculations unchanged. Shared adapter ownership/versioning must be agreed before source integration, to avoid forever maintaining duplicate Yahoo parsers.
4. Verify session/calendar, timestamp meaning, adjustment/action basis, availability and finality. Advertise only attained capabilities. These are the production blockers, not lack of a renderer.
5. Produce one immutable verified MarketSeries snapshot → one product projection → renderer and read-only API → future MCP. Candles/volume/tooltip/range draw the same series; neither frontend nor MCP recomputes domain values.
6. Validate real-source replay and bad-input cases at the new contract boundary, API/MCP parity, renderer mobile/desktop. Existing Technical PIT tests are reusable regression guards, not proof of newly asserted availability.

## Required implementation acceptance cases (not executed in this design review)

- Ticker collision/delisting/rename/share class and dated listing mismatch; company-to-issuer mapping mismatch.
- Missing O/H/L/C or V separately; mismatched lengths, duplicate/unsorted timestamps, negative volume, invalid OHLC envelope; no fabricated fills.
- Daily stamp at session open vs final bar, DST/holiday/early close and forming/final/corrected distinction.
- Unknown currency/timezone cannot become USD/current time; product LIVE cannot become quote LIVE.
- Mixed adjustment basis, future-known action factors, incomplete corporate-action coverage and revised current data offered as prior-known history.
- Source available_at later than historical decision; fetched_at earlier/later but not substituted; pinned older vintage survives latest raw replacement.
- Artifact-key source-kind mismatch (Yahoo-named TIINGO record), SHA/size mismatch, invalid snapshot/publication capability, unknown source metadata.
- API and MCP projection parity by snapshot/hash, missing data reasons survive transport/UI, renderer can never promote NOT_AVAILABLE to verified.

## Protected dependencies / decisions

- Existing DataStamp/yahoo/Technical semantics are consumers of Frozen/protected paths; changing their availability logic is an owner-level change, not part of P0 chart design. Adapter design can proceed without rewriting them.
- Track C code_hash covers package Python: adding a Python adapter within `src/investment_system` can affect identity even without editing Track C files. Coordinate Integration owner before that implementation placement.
- Market session calendar and provider basis/availability evidence remain unresolved source dependencies; choose no unapproved paid feed, publication-lag default or action factor policy.
- No cross-owner product/LIVE/publication changes, canonical merge, Official, Track A/C Frozen, Holdout use are authorized by this design artifact.
- V/Reverse DCF/MOS/scenario target semantics excluded; leave typed version/reference dependency to QGV/V reconciliation, not provisional formulas or fake readiness.

Conclusion: Market price source ingestion/store and renderer foundations are reusable. Production readiness is blocked by verified identity mapping, temporal/session semantics, action/adjustment provenance, selected vintage, source availability, product publication wiring—not by 81 independent renderer implementations.
