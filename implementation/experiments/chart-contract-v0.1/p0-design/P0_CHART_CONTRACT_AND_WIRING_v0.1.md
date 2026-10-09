# P0 Chart Data Contract · Production Wiring Design v0.1

Status: DESIGN_REVIEWED / IMPLEMENTATION_NOT_STARTED. This document defines a proposed shared product contract and source-mapped gaps. It does not activate a schema, provider, publication grant, renderer, Official/LIVE state, numeric policy, Frozen change or canonical merge.

## 1. Objective, scope and fixed baseline

목표는 기존 domain/provider 계산을 재사용해 Market daily OHLCV와 Portfolio 필수 3시각화를 운영 데이터에 연결할 계약·gap·dependency를 확정하는 것이다. 113개를 개별 구현하지 않는다.

| Baseline | Exact source |
|---|---|
| Chart audit / PR41 | `8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf` |
| Canonical default | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Combined trial / PR40 | `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` — NON_CANONICAL |
| Global handoff | `bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88`, GCH-014 |
| Fresh evidence | `EVIDENCE.json`: observed refs, exact source blobs, audit baseline hashes, checks |

Scope ledger is immutable for this design: **Core 81 / Extended 24 / Research Candidate 8**. Core A–H=81; Extended I17+J7=24; Candidate K8=8. J7 remains REQUIREMENT_IDENTIFIED_NOT_REAUDITED; it is not newly certified by this P0 design. Candidate hypotheses are not production requirements. No coverage denominator or audit layer verdict is rewritten.

In scope: daily OHLCV contract, industry composition donut, independent type composition donuts, exact-membership overlap; transport/publication boundary; required verification specification. Target and actual are separate snapshot products. Intraday/live feed implementation, Technical indicators, valuation calculations and every other chart are outside this increment.

V, Reverse DCF, Margin-of-Safety, valuation ranges and scenario-target semantics are **DEFERRED_TO_V_QGV_RECONCILIATION**. No formula, score, unit, threshold, rubric, scenario probability or custom-weight rule is selected here. A future chart may carry an opaque versioned upstream snapshot reference after reconciliation; P0 composition does not require a QGV score/version to exist.

Risk: DEEP for design accuracy and PIT/ownership uncertainty; CRITICAL boundaries are observed, not changed. Authority: D1/D2 read-only source inspection and own scoped design documentation. Source changes in other owners/protected paths must be reported before implementation.

## 2. Source evidence and reuse map

Paths below are relative to `implementation/src/investment_system/` unless prefixed otherwise. `C`=canonical SHA above, `T`=trial SHA above, `A`=PR41 baseline. Exact Git blob/byte hashes and source links are in EVIDENCE.json. Read `reviews/` for independent lenses.

| Existing code / symbol | Pin | Reuse | Verified limit |
|---|---|---|---|
| `ingestion/raw_store.py: RawDatasetStore` | C | Original response storage, manifest/hash creation and history | Reads do not themselves verify bytes: use PR41 bridge / producer verify_inputs. Latest slot can be overwritten; persistence time is not source availability |
| `providers/yahoo_chart.py: fetch_chart, parse_bars, to_price_point` | C | Existing acquisition route; source format knowledge | parse_bars has close/adjclose, no full OHLCV; currency fallback; to_price_point sets available_at=observed_at; not strict daily-final PIT |
| `contracts/raw.py: PricePoint` | C | Existing single-price consumers stay unchanged | A scalar price is not an OHLCV series |
| `contracts/global_universe.py: IssuerIdentity, SecurityIdentity, ListingIdentity, FXSnapshot` | C | Issuer/security/listing hierarchy, dated listing and PIT FX concepts | Identity classes do not supply a real source crosswalk or listing-evidence history |
| `personal/security.py: SecurityRecord, InMemorySecurityResolver, CompanyLink` | C | Personal identity resolution and explicit company link boundary | CompanyLink remains PROPOSED; no automatic unification with company_id or global security namespace |
| `sessions/calendar.py, listing.py, binder.py: CalendarVintage, ListingEvidence, bind_yahoo_bars` | T | Vintage, MIC/listing and daily-session validation | US-specific; source vintage still needed; BoundBar retains close+volume, not O/H/L; session-close eligibility is not source availability |
| `technical/pit_market.py: bars_from_yahoo_chart` | T | Existing close/volume Technical input stays owner-controlled | Cannot recover missing O/H/L or certify provider publication from bar timestamp |
| `personal/portfolio.py: ModelPortfolioSnapshot, ActualPortfolioSnapshot.total_value/weights, portfolio_gap` | C | Target/actual distinction; Decimal actual values/weights; multi-account aggregation; descriptive gap | P0 Frozen contracts, not broker ingestion; missing source/available-at history; actual snapshot completeness must be carried |
| `personal/money.py: Money, convert` / `personal/timecontract.py` | C | Explicit FX and available_at<=decision_time | Conversion max_age is caller policy, not a new chart default; converted inputs need retained source references |
| `personal/ports.py: BrokerAdapter` | C | Interface for later broker/user-input boundary | Protocol only; no production synchronizer established by this audit |
| `contracts/portfolio_input.py` / `qgv/portfolio.py` | C | Generic target inputs / reference fixtures | QGV Holding.actual_weight is model-side, not broker actual; QGV gap direction differs from personal gap |
| `qgv/identifiers.py` | C | Existing company labels and user portfolio grouping | Semicap/AI/BigTech/Other is not sourced GICS; no company type-history provenance |
| `product/entity_metadata.py` / `entity_catalog.py` | T | Search-only display labels | SEARCH_PRESENTATION_ONLY explicitly excludes Portfolio/PIT input; cannot act as classification source |
| `producers/contract.py: make_snapshot, validate_snapshot, verify_inputs`; `serialization.py` | T | Existing producer identities, input hashes, canonical serialization and validation | make_snapshot alone does not validate; Decimal unsupported; allowed sections do not include market/charts |
| `producers/adapters.py, assembler.py` | T | Existing verbatim domain-output assembly philosophy | portfolio_section consumes model PortfolioSnapshot, not personal ActualPortfolioSnapshot; schema compatibility PARTIAL |
| `publication/envelope.py, predicate.py, authorization.py` | T | Existing grant/subject/invalidation authority boundary | All active grants NONE; chart subjects not authorized by a generic PASS |
| `product/web_mvp.py` / `product/web_assets/app.js` | T | Existing product shell, state presentation, renderer integration point | No market section/chart route; protected digest and owner coordination apply |
| `implementation/experiments/chart-contract-v0.1/contract.mjs`, `raw_store_bridge.mjs` | A | Full OHLCV extraction, null/zero, envelope/order/hash tests and source-preflight behavior | Candidate only; caller identity unverified; real data deliberately blocked; transport and source origin currently mixed |
| `implementation/experiments/chart-contract-v0.1/portfolio_contract.mjs`, `portfolio_app.js` | A | Validated overlap semantics, cash/unknown presentation, SVG renderer | Integer-unit demo input is not a lossless production adapter for Decimal/float weights; observed renderer blocked |

## 3. One shared domain/product path

Recommended design: **one versioned ChartDocument, one materialization/validation path, several consumers**. Do not add a financial engine for each renderer or transport.

1. Existing provider/store or portfolio source supplies immutable, hash-addressed input evidence.
2. Domain owners resolve identity/time/FX and produce their existing values. ActualPortfolioSnapshot owns actual weights; the target owner owns target weights. Session owner supplies dated sessions. No renderer or MCP calculates them.
3. A shared chart projection adapter joins those outputs with point-in-time classification and source facts. Market extraction preserves O/H/L/C/V from the same raw row. One portfolio composition projection supplies all three views.
4. A proposed ChartDocument validator checks identity, lineage, temporal use, numeric encoding and per-view capability. Existing producer hash/input verification is reused once the owner registers the new product contract.
5. Existing product/publication authority makes the display decision for the exact subject hash, scope and consumer. Unknown/absent authority remains blocked. Chart validation never grants publication.
6. API and future read-only MCP return the **same validated payload, version, hash, state and reasons** for the same authorized request. Web consumes that payload. Renderers only layout/format and convert explicit values to display coordinates.

Recommended product placement: an additive versioned chart document referenced by a product manifest/sidecar, leaving Web schema-1 section data intact. This is a DESIGN, not a bypass: it still requires a registered validator, issuer/subject authorization, UI guard, lifecycle/invalidation wiring and product-owner integration. Do not smuggle Market into Technical, label actual as qgv PortfolioSnapshot, invent a schema-1 REFERENCE/LIVE state, or publish an unguarded sidecar URL. Owner acceptance of the extension and any protected digest changes precedes implementation.

Alternative rejected: separate Market/Portfolio/MCP calculation implementations. Alternative deferred: directly widen Web schema-1 `SECTIONS` and protected assembler. It introduces unnecessary owner coupling before data semantics are resolved.

### 3.1 Logical operations (not implemented endpoints)

| Operation | Inputs | Output / constraint |
|---|---|---|
| Read market chart | explicit listing identity, interval, range, adjustment request, knowledge cutoff, vintage/revision selector | Verified ChartDocument or structured unavailable result; ticker lookup is a separate identity operation |
| Read portfolio composition | portfolio/snapshot ref, TARGET or ACTUAL, classification snapshot/version, knowledge cutoff | One composition document containing industry/type/exact-overlap views; no implicit latest mix |
| Read evidence | authorized document ref/hash | Evidence metadata with restricted raw references; no account credentials/raw private positions in public URLs |

API and MCP are alternative transports, not consecutive calculations. MCP tool execution and HTTP status200 are not validation evidence. Cache keys include exact subject, domain/calculation version, source/identity/session/classification vintages, range, basis, cutoff and snapshot hash. Cache invalidation follows existing subject invalidation; a refreshed source cannot overwrite an older snapshot. Private actual-portfolio access uses the same account scope for both transports. No new credential storage, live broker link, HTTP server or MCP server is built here.

## 4. Common contract (proposed logical schema)

The names below are proposed semantic fields, **not adopted schema enums**. Implementation must use owner-approved envelope names and existing state vocabulary. Diagnostic candidates may contain nulls plus reasons; publishable values must satisfy their capability requirements.

| Group | Fields / semantics | Required verification |
|---|---|---|
| Contract identity | contract_id, schema_version, document_id, payload_hash, chart_kind, producer_id/version, projection_version | Version registered and hash recomputed from canonical bytes; no silent migration |
| Subject | subject_kind, subject_ref/hash, company/issuer/security/listing refs where applicable | Dated evidence and namespace crosswalks, not labels/tickers as keys |
| Data origin | OBSERVED / USER_ENTERED / MODEL_TARGET / REFERENCE / SYNTHETIC classification with source refs | Distinct from schema-1 data_state; never inferred real from synthetic=false alone |
| Time | requested_as_of, data_as_of, knowledge_cutoff, generated_at; input observed_at/available_at; acquired_at, persisted_at | Timezone-aware; event, availability, acquisition, storage and generation are different facts |
| Provenance | per-input artifact_id+hash+size, source/provider/reference, source vintage/revision, request basis, evidence refs | Original bytes resolvable; manifest label is not enough; joins retain every input dependency |
| Computation | domain snapshot refs, calculation/methodology versions, numeric_encoding/precision/context refs | Existing financial computation only; proposed projection version covers aggregation/serialization, not new scoring |
| Assessment | structural checks, source replay checks, temporal-use assessment, identity/session/classification checks, per-capability state/reasons | PASS tied to exact payload/input/code hashes; one generic boolean cannot certify all facets |
| Publication | existing publication subject/decision reference, scope, current grant/invalidation result | Existing authority only; verified data does not imply LIVE/Official or a research-display grant |
| Freshness | source-specific freshness policy ref, expires_at/usable_until when required by existing state, checked_at | Preserve producer policy; no new delay/TTL/staleness defaults; separate from historical-PIT and quote state |
| Coverage | required/present/missing fields, range coverage, null reasons, unsupported capabilities | Missing≠0; unavailable≠empty; no filled bars, implicit classification or renamed states |

`as_of` is not overloaded as bar time or latest fetch. `knowledge_cutoff` identifies when information may be used; `data_as_of` identifies what the result describes. A retrospective view of current-source historical prices is not a historical-decision replay. If provider availability/vintage is not established, historical-PIT capability stays unavailable; a later permitted retrospective display must declare that limitation and pass its applicable publication gate. No claim that acquisition proves earlier knowability.

Historical replay requires every material input (price revision, listing, calendar, action, classification, FX, position/target revision) to be admissible at the requested cutoff, plus effective validity at the subject date. Unknown available_at blocks replay. New corrective releases append a revision with their own availability; do not overwrite earlier inputs.

### 4.1 Numeric representation

Preserve upstream authoritative values. Proposed Decimal transport is a lossless tagged decimal string with original calculation/context reference; it is an encoding, not a new precision/rounding policy. Existing model floats remain their original representation with source type declared. Never multiply weights by100/10000 and round them into PR41 integer demo units. Never derive actual amounts from displayed percentages.

Reject non-finite values (NaN, positive/negative Infinity, including tagged Decimal strings) for Portfolio as well as Market before hashing or rendering. A generic PortfolioInput is not a validated producer output. Target inputs must carry successful authoritative producer validation of the applicable total/weight constraints, in addition to chart structural checks. Invalid or unvalidated target totals are unavailable; do not renormalize, add an epsilon, or change the Frozen validator to make them pass. Actual monetary values and domain outputs also require finite-value admission; preservation of a source value does not imply it is admissible.

Existing producer serializer does not support Decimal: an explicit registered chart encoding adapter is required before using its canonical hash functions. No edit to the shared serializer is assumed. A browser may convert validated values for pixel placement/labels, but API/MCP authoritative values and evidence hashes stay unchanged. Financial totals, FX, weights and group aggregation are calculated once upstream; display rounding cannot repair failed reconciliation. Exact aggregation order/precision must reuse the domain owner's numeric contract; where unspecified, this is an implementation prerequisite, not a chart-selected epsilon/default.

## 5. Market daily OHLCV contract

| Field group | Proposed contents | Gap / interpretation |
|---|---|---|
| Identity | issuer_id, security_id, listing_id, MIC, dated ticker, share-class/security type, currency, identity_evidence_ref/hash, valid interval, mapping available_at | Reuse global hierarchy; real sourced crosswalk absent from NVDA sample; personal/global IDs require explicit reviewed mapping |
| Series identity | interval, range_requested, range_returned, source series/revision id, adjustment_request and effective adjustment basis | P0 is daily; range is not interval; intraday/extended hours not automatically supported |
| Time/session | source timestamp, timestamp_role, session_date, session_open/end UTC, IANA timezone, tzdata version, calendar id/vintage/hash, session status | Provider epoch can label session open; it is not daily-final availability. Existing US session binder must be joined without dropping O/H/L |
| Bars | stable bar identity (listing+interval+session+revision), open/high/low/close/volume, currency, price/volume units, field-null reasons | Complete candle needs O/H/L/C. Volume is independent; no volume => candle may be eligible, candle+volume is not READY |
| Bar lifecycle | observed_at, available_at and evidence, finality, revision id, source message/acquisition refs | Provisional/final/revised distinguished; calendar close alone cannot establish provider finality |
| Adjustment/actions | price basis, volume basis, action coverage, action ids/hashes/types, effective dates, announced/available-at, adjustment methodology/vintage | Empty events list does not prove no corporate actions; no adjusted-close substitution into raw OHLC; split source sample is not a transformation engine |
| Quote state | sourced real-time/delayed/close/unknown classification, feed, timestamp, declared delay when evidenced; session status separate | Polling frequency cannot prove real-time; closed market does not prove official close; never reuse schema-1 LIVE as quote state |
| Reproducibility | source/provider/feed, raw bytes hash, retrieval request, acquired/persisted timestamps, source vintage, validator versions | Same snapshot+inputs must reproduce same domain values; missing historical bytes remain explicit blockers |

Market invariants:

- All OHLC values in a candle share listing/currency/basis/session/revision. Finite numeric values, high/low envelope validated; null stays null. Volume zero differs from missing and negative volume is rejected.
- Unique ordered bars; ambiguous duplicate/revised rows require source revision selection, not silent last-write-wins. Pagination/truncation and session gaps are explicit. No interpolation or automatic holiday/weekend bars.
- Listing validity and source mapping are checked at every relevant session; ticker reuse/venue transfer is not stitched across identities. The existing US-only session scope is reported; it does not cover Tokyo Electron or Korean listings by inference.
- A known calendar does not cure missing source available_at or unknown adjustment basis. `pit_bar(observed_at<=as_of)` alone is insufficient.
- Final historical daily bar use requires evidence of source availability no earlier than applicable completed session semantics; session-only lower bounds are not asserted exact provider timestamps. Intraday/provisional data requires a separate supported capability and source evidence.
- Current close/adjusted series is never relabelled total-return. Chart-side corporate-action recomputation is not allowed. Reuse an owner-validated transformation or leave requested basis unavailable.
- Chart tools (crosshair, zoom, pan) consume the same bar IDs/series; tooltips show basis, source, time/session and null reasons. They do not fetch or normalize a second competing series.

## 6. Portfolio composition contract

### 6.1 Separate target and actual

| Kind | Existing authority | Proposed chart projection |
|---|---|---|
| TARGET | ModelPortfolioSnapshot / explicitly versioned PortfolioInput | snapshot ref/hash, strategy/portfolio version, effective period, available_at/source, target weights + cash target, target grouping/classification refs |
| ACTUAL | ActualPortfolioSnapshot from BROKER or USER_ENTERED positions | actual snapshot ref/hash, account-scope reference, position/price times, complete/sync quality, base currency, monetary values and domain-computed weights, cash, FX provenance |
| REFERENCE | Official v1.1 reference weights in qgv/portfolio.py | Remains reference TARGET. Extraction timestamp is not historic publication or actual-account valuation |

A requested TARGET never falls back to ACTUAL and vice versa. No actual holdings are inferred from a model/reference input. Comparison, if added later, references both immutable snapshots and alignment metadata; no generic `weight` field silently changes meaning. Existing `personal.portfolio_gap` means target−actual, whereas QGV evaluate uses actual−target; P0 adds no gap calculation.

Current trial frontend uses `actual_weight ?? target_weight`. That fallback is incompatible with this production contract and requires Web-owner replacement with explicit basis-specific data. Search presentation metadata must not be repurposed as portfolio classification evidence. Neither path is modified in this design.

Actual positions of the same security across accounts are aggregated by existing `ActualPortfolioSnapshot.weights()`, not rejected as duplicates by the old JS demo or recomputed in each chart. Preserve account-scope completeness, missing accounts, stale prices, unresolved securities and FX. A complete positive long-only/cash snapshot is the initial eligible donut capability; incomplete, nonpositive or signed-exposure cases receive an explicit unsupported/unavailable reason for this P0 view, without altering the domain portfolio or pretending missing values are zero. A future partial/gross/net view requires an explicitly defined denominator, not silent renormalization.

### 6.2 Classification records and historical joins

Each classification record carries classification_record_id, entity level (issuer/security/portfolio row), entity ref, taxonomy namespace/id/version, assignment revision, source/artifact/hash, effective_from/to, observed_at, available_at, and evidence/method reference. Unknown fields stay unknown. Custom grouping is a separately named namespace, not silently GICS. A supplied taxonomy catalog does not prove company assignments.

Industry composition uses an explicit single-partition classification at the selected level; ambiguous/multiple industry assignment has a reason and cannot be arbitrarily selected or double-counted. The 30/25/20/25 portfolio grouping remains USER_ALLOCATION_GROUP, not standard industry exposure. No taxonomy/provider is purchased or chosen by this design.

Type classification supports multiple memberships by design. A record states whether the supplied set is complete: a complete empty set means explicitly no catalog types; missing/incomplete set is unknown. Never infer that all non-listed types are false. P0 can treat incompletely known sets as unknown rather than invent per-type negatives; finer partial-membership display is a later explicit contract extension. Approved catalog/version and membership evidence are separate dependencies. No QGV threshold is invented to derive Growth/Value/Quality/etc.

Historical classification selection uses both effective dates and information availability at the snapshot cutoff. Today's revised taxonomy must not leak into old quarterly snapshots. Persist original target/actual refs, classification refs, FX refs and projection version for every immutable quarterly snapshot. Calendar-quarter boundaries alone do not establish knowledge availability.

### 6.3 Three views from one composition projection

| View | Output | Conservation / semantics |
|---|---|---|
| Industry donut | labelled industry/group buckets + unknown + cash; denominator and basis explicit | Every eligible holding contributes once, no source-free normalization; actual/target separate |
| Type donuts | per type member / known non-member / unknown / cash, all using same portfolio denominator | Each ring covers its denominator. Sum of type membership exposures may exceed100%; never normalize across types |
| Overlap | exact sorted membership-set buckets + known no-types + unknown + cash | Disjoint sets count each holding once. Not pairwise correlation, not a probability. A Growth+Quality+Value row is not silently assigned to Growth+Quality |

One projection groups existing domain weights using a versioned numeric contract. It returns exact value/denominator metadata and source membership trace once; renderer, API and MCP consume it. Display tests from PR41 (Growth65%+Quality40%; overlap100%) are reusable semantic oracles, not proof of a real company classification feed.

## 7. Confirmed gap matrix

`EXISTS` below means source code exists at the stated pin, not canonical production readiness. Missing-source findings are scoped to fetched repository and captured evidence, not external accounts or unavailable artifacts.

| ID | Required capability | Existing source / reuse | Missing work | Dependency / owner boundary |
|---|---|---|---|---|
| M1 | Complete OHLCV | PR41 extraction + raw store; source NVDA5-day sample | Shared owner adapter retains full fields; stable production schema and real-source contract replay | Chart adapter + ingestion/domain owners; Frozen parser unchanged |
| M2 | Dated security/listing binding | Global hierarchy, personal resolver, T ListingEvidence | Sourced crosswalk/evidence; namespace reconciliation; reject ticker collisions | Identity owner; no C-25/CompanyLink resolution by inference |
| M3 | Session/timezone | T CalendarVintage/bind_yahoo_bars | Exchange-issued vintage replay, O/H/L-preserving join; non-US coverage explicit | Session/Technical owner; US feature is NON_CANONICAL |
| M4 | Point availability/revisions | Existing PIT helpers; acquisition/hash evidence | Provider availability and historical vintage per revision; no observed-at substitution | Data/source owner; no PIT relaxation |
| M5 | Price/volume adjustment & actions | Raw quote/adjclose, split events; Track A CA evidence | Chart-specific all-OHLC+volume basis proof, action coverage and owner transform if needed | Track A unit reconciliation is not automatically chart adjustment; Frozen unchanged |
| M6 | Quote/feed state | Provider metadata; PR41 UNKNOWN | Evidence-backed delayed/live/final-close mapping and feed scope | Source/feed owner; no delay/TTL defaults or grant |
| M7 | Immutable historical raw replay | RawDatasetStore and hash guards | Pin and resolve correct bytes per vintage; latest slot is insufficient | Data retention owner; fresh download cannot replace historical evidence |
| P1 | Actual source & target lineage | Model/Actual snapshots; BrokerAdapter Protocol | Real user/broker snapshots, availability/artifact history, completeness; target revisions | Personal owner; no account connection requested in this design |
| P2 | Lossless numeric product encoding | Decimal domain weights, current serializer, integer demo | Registered Decimal/float-preserving adapter and owner numeric aggregation context | Producer + Personal owner; no quantization or epsilon |
| P3 | Industry / type history | Registry user-groups; PR41 null/multiple types | Source/versioned assignments, taxonomy availability/effective history, entity mapping | Classification owner/data; no invented type taxonomy/assignments |
| P4 | Composition projection | Domain weights + PR41 aggregation semantics | One projection for3views with source trace, multi-account/cash/unknown reconciliation | Chart projection owner; not3independent calculations |
| P5 | Quarterly immutable snapshots | Existing versioning/hash and conceptual portfolio snapshots | Persist target/actual/classification/FX versions and replay historical cutoff | Personal storage owner; no inferred history |
| X1 | Product contract registration | T producer contract/adapters/assembler | New chart document registration; current no market section, actual shape mismatch | Producer/Web/P01 owners; protected digest changes reported first |
| X2 | Publication / invalidation | T P01 predicate/envelope + render guard | Chart subject facts/extractor+scope registration and legitimate display decision | Publication owner; grants NONE stay NONE |
| X3 | API / MCP / Web wiring | Existing product shell + PR41 renderers | One read service and thin transports; renderer consumes authorized ChartDocument | API/MCP not implemented; schema compatibility and actual access scope |
| X4 | Production validation | PR41 75 tests + captured replay + browser; existing owner tests | Exact proposed-schema/source integration tests and affected owner regression | Current results apply to PR41 experiment only; no new runtime PASS claimed |

Frontend-only gap: renderers can largely be reused once the validated projection exists, including candle/volume, independent type rings and exact-set overlap. **Neither Market+Volume nor all3 Portfolio views is currently a frontend-only task**: identity/time/basis and actual/classification/encoding gaps remain upstream.

## 8. Dependency sequence and acceptance gates

1. **Design checkpoint (this increment):** preserve A audit, define shared contract, source-map gaps and owner boundaries; no runtime edits.
2. **Owner interface alignment:** identity crosswalk, session contract, Decimal wire encoding/aggregation context, product sidecar registration and publication subject. Existing domains remain calculation owners. Report proposed exact paths before any protected change.
3. **Independent data work:** Market identity+session+availability+basis and Portfolio target/actual+classification+FX histories can progress independently; no need to wait for V/QGV scoring for composition.
4. **Shared adapters and projection:** implement only after interfaces/routing accepted; one Market extractor and one portfolio projection. Reuse source parser guards/domain calculations; no second Yahoo provider or alternative Portfolio weight engine.
5. **Read service and product integration:** schema validator+source verification→existing publication decision→API/Web; MCP reuses the same output after API parity tests. A sidecar is not a permission bypass.
6. **Exact-tree verification:** targeted source replay, domain/projection parity, publication-negative cases, browser mobile/desktop; affected owner regression and exact merge-result FPIA per Integration owner. Canonical merge and grants remain separate decisions.

Critical path is real source metadata/history → owner contract registration → adapter validation → product publication/wiring. More chart components will not resolve it. Portfolio's target-reference grouping can be demonstrated now but cannot count as actual or full classified production. V-related charts remain on their separate reconciliation dependency and do not block P0 composition design.

### Required implementation verification cases (planned; NOT_RUN here)

| ID | Case | Expected result |
|---|---|---|
| V01 | The same immutable materialized document retrieved through API and MCP | Same verified document hash/value/state. Consumer response metadata stays outside hashed document content; original acquisition provenance stays inside. Independent acquisitions can legitimately produce different document hashes |
| V02 | Same ticker reused, share-class mismatch, venue transfer, unresolved CompanyLink | Explicit identity refusal; no guessing or stitch |
| V03 | DST/early close/holiday, known US vintage, non-US listing | Reuse owner session results; no invented calendar; unsupported scope explicit |
| V04 | Session-open timestamp with daily close values; source unavailable after cutoff | Historical replay blocked even if observed_at<=cutoff |
| V05 | Null OHLC, zero/null volume, malformed arrays, duplicate/revised bars, truncated range | Field-level capability and reason correct; no volume or bar fabrication |
| V06 | Split/reverse split/dividend adjustment, mixed raw OHLC+adjclose, missing action coverage | Never mixed basis; unsupported transformation blocked; source vintage preserved |
| V07 | Raw hash mismatch/missing original/replaced latest slot; tampered identity/calendar ref | No source replay PASS; historical snapshot cannot silently change |
| V08 | Target fixture submitted as actual; model Holding.actual_weight submitted as broker | Rejected; target/reference role retained |
| V09 | Same security in2accounts, cash, FX unavailable/stale, incomplete account list | Domain weights reused; no duplicate-ID rejection before aggregation; missing≠0 |
| V10 | Repeating Decimal weight, float target weights, precision/serialization roundtrip; NaN/Infinity including Decimal strings; invalid/unvalidated target totals | Finite authoritative values preserved; non-finite/invalid/unvalidated inputs rejected or unavailable; no basis-point quantization, epsilon or total repair |
| V11 | Classification unknown vs known-empty vs multitype, conflicting taxonomy/version | Unknown preserved; version pinned; no inferred membership |
| V12 | Classification revision arrives after old quarter cutoff | Excluded from historical snapshot; old snapshot/hash unchanged |
| V13 | Growth65+Quality40 demo and independent real snapshot oracle | Type exposures may exceed100; exact-set overlap totals one denominator; cash/unknown retained |
| V14 | Valid document but missing/revoked/wrong-subject grant; stale cache or changed source | No publication upgrade; both API/MCP obey same authority and invalidation |
| V15 | Real renderer on360/390/1280px, tooltips, switch target/actual, empty/blocked state | No stale values or identity/state mislabelling; accessibility/overflow verified |
| V16 | Extended24/Candidate8 or V semantics accidentally activated | Scope/semantic guard fails; no auto-promotion |

## 9. Protected changes: report before implementation

| Proposed future action | Current permission/result |
|---|---|
| Own scoped design files under this experiment | Authorized now; implemented only as documentation |
| Edit Frozen `personal/*`, Track A parser/unit policy, identity contract or Track C records | NOT done; avoid by additive owner adapters; if unavoidable report concrete diff/impact first |
| Add package Python even outside Track C | Changes whole-package `code_hash`; Integration owner's CDR-014 FPIA must assess exact tree; never normalize divergence to PASS |
| Change Web `SECTIONS`/validator or producer assembler | Owner routing + P01 protected-digest implications; no silent repin |
| New publication subject/facts or research-display grant | Owner schema work separately; grant issuance is not authorized by this design |
| Official/LIVE, Holdout, numeric policy, canonical merge | No change or consumption; separate authority required |
| Define V/Reverse DCF/MOS/scenario targets | Wait for V/QGV scoring reconciliation; no chart-driven semantic commitment |

No user decision is needed to accept delivery of this design. Production implementation must first identify the exact owner-approved adapter/registration paths and genuine data gaps. If it requires protected changes, a concrete path/diff/impact report comes before implementation, per the user's instruction. This document is not an implicit approval request for a broad merge or policy package.

## 10. Design verification and completion

Acceptance for this increment: fresh baseline pins; preserved81/24/8 ledger; Market and Portfolio required fields/invariants; reusable sources; actual gap matrix; one API/MCP path; explicit V deferral; owner/Frozen/publication dependencies; no runtime changes. Evidence is file/source inspection and independent Market, Portfolio and integration-boundary reviews, not agent majority.

The previous75-test result remains historical evidence for the exact PR41 experiment. No source code changes require a new full runtime regression here. Planned V01–V16 are NOT_RUN until implementation. Scope/path/hash checks and reviewer findings are recorded in EVIDENCE.json and DESIGN_REVIEW.md. Baseline inventory, acceptance records, fixtures and runtime files are unchanged.
