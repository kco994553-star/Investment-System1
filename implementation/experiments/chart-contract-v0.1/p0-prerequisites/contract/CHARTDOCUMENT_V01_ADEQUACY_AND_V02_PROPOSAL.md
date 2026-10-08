# ChartDocument v0.1 evidence adequacy / v0.2 correction proposal

Status: **PROPOSED / NOT_APPROVED / NOT_ACTIVE**. Evidence review only. No executable schema, contract implementation, numeric policy, enum adoption, provider selection, production Python, protected edit, grant, promotion or merge.

Baseline: PR #41 `97685dd`, its audit `8668c69`, and immutable `p0-design/P0_CHART_CONTRACT_AND_WIRING_v0.1.md`. Integrated source inspection: noncanonical PR #40 `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`. Coordination: `bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88`, GCH-014 / CDR-014. Core 81 / Extended 24 / Research Candidate 8 preserved. V/QGV valuation semantics stay deferred.

## Finding

v0.1 is adequate as a **logical design and fail-closed invariant baseline**. It is not an implemented or registered machine schema. The observed Market and Portfolio inputs can be represented without inventing values only if the unavailable facts remain explicit and the affected capabilities stay unavailable. No evidence reviewed establishes a publishable complete real Market document or actual-account composition.

Seven proposed v0.2 corrections make evidence bindings and wire boundaries precise. They do not replace v0.1 or approve production semantics. Three refine already specified intent; four require a missing structural dependency. Source gaps must not be disguised as schema defects: adding a field cannot create provider publication history, a real actual position, classification assignment or grant.

## Actual evidence exercised

1. PR41 Yahoo NVDA 5-day response is present as **original 1,758 bytes**. Recomputed SHA-256 is `469e185faec7925e724efdc23546967e86f6b3ccbc3ba8d05a2767f968f722a6`, matching the manifest and request evidence. It contains five aligned O/H/L/C/V rows and separate adjclose. It supplies neither source `available_at` nor a source revision identifier. Those must remain unknown.
2. Request capture reports start `2026-10-04T10:23:16.489426+00:00`, completion `2026-10-04T10:23:22.885843+00:00`; the raw-store `fetched_at` is `2026-10-04T10:24:05.100367+00:00`. The latter is explicitly persistence time. None is historical provider publication time. They need distinct role bindings, even though current legacy field names overlap.
3. Last bar timestamp is `1790947800`; `meta.regularMarketTime` is `1790971201`. They differ materially. CurrentTradingPeriod contains a current session, not a complete dated session vintage for all rows. IANA timezone metadata is useful evidence; it does not alone prove historical exchange-session validity.
4. Canonical personal domain separates ModelPortfolioSnapshot and ActualPortfolioSnapshot. Actual weights are Decimal; repeated security IDs across accounts are summed by `weights()`. Existing `producers.serialization.canonical_bytes(Decimal(...))` raises `SerializationError: unsupported type Decimal`.
5. Read-only synthetic diagnostic: a position value of 1 and cash of 2 yields `0.3333333333` under Decimal precision 10 and `0.3333333333333333333333333333` under precision 28. Snapshot input content hash is unchanged. These are **probe contexts, not selected defaults or a real account**. The domain method reads ambient Decimal context; lossless string encoding alone cannot establish reproducible computation. Owner-supplied context/output materialization is a prerequisite.
6. `money.convert()` returns ConvertedMoney with original value and FxRate; Position stores only Money. ActualPortfolioSnapshot stores positions/cash but no per-input artifacts, available_at or conversion link. v0.1 intends retained source references; existing shape does not provide them.
7. PR41 portfolio reference evidence explicitly says TARGET_REFERENCE_ONLY_NOT_ACCOUNT, unresolved security IDs, authored allocation groups rather than GICS, and null company types. It is valid reference evidence, not actual holdings/classification history.

These are source/shape probes, not a new production test suite or a replay of the prior 75-test result. No real-user account data was created or inferred.

## Adequacy matrix

| Dimension | v0.1 intent | Evidence outcome | Remaining prerequisite / v0.2 correction |
|---|---|---|---|
| Decimal preservation | Adequate: tagged exact value, no quantization | Existing producer serializer rejects Decimal; owner arithmetic context absent from result | C02: preserve numeric type, upstream result, context/order provenance; registered adapter later |
| TARGET/ACTUAL | Adequate: separate requests/snapshots, no fallback | Model and Actual domains exist; actual source is not established | C04: basis-specific root dependency; absent ACTUAL yields existing NOT_AVAILABLE |
| Missing actual / empty positions | Adequate principle | No source is different from a verified complete account with no securities; nonpositive denominator is unsupported | C03: explicit result/capability absence with coverage and diagnostic reference |
| Null/zero OHLCV | Adequate | Real sample complete; null/zero adversarial requirements remain planned | C03: preserve per-field absence and distinguish candle from candle+volume capabilities |
| Time / PIT | Adequate separation | Raw epoch, current regularMarketTime, request and persistence times available; source earliest availability absent | C05: time facts bind role, evidence and exact/unknown/bound meaning; no scalar substitution |
| Raw provenance | Adequate hash/replay intent | NVDA original-byte hash verifies; legacy resolver is artifact-ID based | C01/C04: document/input-hash identity and immutable component dependency resolution |
| Position/valuation/FX provenance | Adequate requirement, missing shape | ConvertedMoney retains original+FX; Position discards conversion relationship | C04: valuation and conversion dependency link for each relevant position/cash input |
| Classification version/effective/available | Adequate full logical record | No real versioned per-company type feed proven; reference grouping available | C06: separate taxonomy catalog from dated assignment revision and bind each entity |
| Known-empty vs unknown types | Adequate and necessary | DEMO supports [] vs null; production complete-set evidence absent | C03/C06: completeness belongs to each membership assignment, not one global flag |
| Multi-type exposure / exact Overlap | Adequate: exposures may exceed 100%; holding counted once per exact set | Existing DEMO is a semantic oracle, not source evidence | C02/C06: typed canonical set identity and one owner numeric projection; no pairwise substitute |
| Snapshot history | Adequate revision/cutoff intention | Model has as_of/hash; actual has no input availability/history refs | C04/C05: immutable snapshot/source/classification/FX graph; no synthetic quarterly history |
| Publication/invalidation | Adequate authority separation, ambiguous hash boundary | P01 attaches decision outside data; active grants NONE; chain resolver exists | C01/C07: immutable subject hash plus decision-time authorization/invalidation envelope |
| API/MCP parity | Adequate | No production transports implemented | C01/C07: same document at same request+authorization resolution; transport metadata outside hash |
| Production readiness | Adequate planned acceptance | No executable registered chart schema or real-source producer | Source/owner/FPIA prerequisites still required; metadata collection does not activate a chart |

## v0.2 correction proposals

**C01 — Immutable payload and subject hash boundary. STRUCTURAL_DEPENDENCY.**

v0.1 lists document/payload hashes, generated metadata and current publication/invalidation facts in one logical document without a concrete hashing boundary. Propose an immutable materialized semantic payload with an explicit canonical encoding/hash definition, plus a separately bound access/assessment response. Its self hash is excluded from its own hash preimage; the publication decision references that exact hash and does not become part of it. Preserve original source artifacts and materialization provenance in the immutable subject. Response request time, current authorization/invalidation decision and transport metadata stay outside the subject hash. Pin distinct existing upstream content-hash algorithms; never treat `personal.versioning.content_hash` as the same algorithm as producer canonical JSON. This matches the existing producer data hash and outside-data P01 envelope design; it does not widen either existing contract.

**C02 — Numeric type, owner context and materialized-output binding. STRUCTURAL_DEPENDENCY.**

Tagged Decimal strings must preserve authoritative finite Decimal values and value type, including the upstream context/calculation reference. Model float input remains a float of its original representation. Exact digits are not generated by passing through JS Number. The materialized source result should identify the owner computation and its actual context/order where required for replay; a product hash alone over input dataclasses does not capture ambient context. Preserve denominator, source market values, upstream actual weights and exact projection outputs without deriving amounts from displayed percentages. A change in context/output requires a new materialization identity. No precision, rounding, epsilon, aggregate order or tolerance is chosen here. Existing finite-value requirements remain; Decimal NaN/Infinity cannot be admitted merely because an upstream string/hash can contain it.

**C03 — Unavailable result versus diagnostic evidence versus valid empty coverage. CLARIFICATION.**

Use existing state vocabulary for public results: requested ACTUAL with no actual source is NOT_AVAILABLE with a reason, and never a reference TARGET. `producers.contract.not_available()` and validation already require data=None. Do not place diagnostic candidate positions/bars inside that public data field. Preserve authorized diagnostics in a separate immutable evidence/readiness artifact reference. Define per-capability checks and field-null reasons: candle can be usable while volume is unavailable; a complete sourced zero-security/cash-only account differs from no source; zero/nonpositive total is not a fake empty donut. Distinguish verified empty requested range from missing/truncated source through coverage evidence, not `bars=[]` alone. Machine field names/enum membership are owner decisions later.

**C04 — Input dependency graph with row/value bindings. STRUCTURAL_DEPENDENCY.**

A generic snapshot-level artifact list cannot identify which price, position, FX rate, identity mapping or classification produced a specific value. Propose explicit dependency references from each series/bar/holding or upstream grouped-security row to the relevant immutable component hash+revision, and a document input-closure list. For ACTUAL, retain raw/source position ref, account scope/completeness, valuation ref/times/basis, original currency and ConvertedMoney/FX reference when converted. Preserve many-account positions and link their one aggregated security output rather than introducing duplicate-ID rejection. For TARGET, preserve only its own producer validation and revision source. This is an additive binding prerequisite; do not add fields to Frozen Position/Actual/Model contracts now. Artifact-ID resolvers must pin the expected hash/vintage and fail if latest-slot bytes differ. No new historical bytes or source availability is inferred.

**C05 — Time-fact evidence and separate decision clocks. CLARIFICATION.**

Bind provider epoch, session open/close, quote timestamp, source publication/availability, request receipt and persistence to their distinct roles. An exact source publication fact requires its own evidence; an observation at receipt or a session-derived bound is recorded as that fact and never assigned to unknown exact `available_at`. Separate data date, requested knowledge cutoff and product access/publication decision time. The current request record provides completion and persistence, not historic first publication. Historical knowledge checks include every material dependency, with effective-date validity separately. Do not weaken existing PIT rules; unknown availability leaves historical replay unavailable. Proposed descriptions here do not adopt a time-evidence enum or approximation rule.

**C06 — Catalog/assignment identities and exact-membership completeness. CLARIFICATION.**

Pin the taxonomy catalog namespace/version/hash separately from each sourced entity assignment revision/effective interval/available_at. Bind the entity level and the identity mapping used for that join. A whole-document `classification.version` is insufficient when holdings use differing assignment revisions or industry and type use different taxonomies. Require completeness on each type-set record: known complete [] is no catalog type; missing/incomplete is unknown. Use namespace/version/type identifiers for the exact sorted set key, keeping labels for display only. A row with three types belongs only to that exact three-type bucket. No taxonomy, company membership or QGV-derived type threshold is adopted.

**C07 — Exact subject lifecycle / access decision binding. STRUCTURAL_DEPENDENCY.**

Bind the exact immutable payload hash to an existing-owner publication eligibility fact and a separately evaluated authorization/invalidation response with its decision clock, authority snapshot/evidence ref, current resolution and reasons. Do not freeze a stale `publication=true` inside cached chart data. Resolve dependency invalidations as well as the root where the owner's registered lifecycle requires it; original data remains immutable, but returned permission must follow current applicable authority. Historical knowledge validity and present ability to display are independent questions. Existing P01 cannot currently issue LIVE/Official from `decide()`, and production attachment keeps display unavailable while grants are empty. Chart-specific extractor/subject/scope registration is missing; reuse requires owner work, not a generic `PASS` or an unguarded sidecar. At equal document/request/decision authority API/MCP must return equal authoritative payload, hash, state and reasons; independent acquisitions may correctly have different hashes.

## Implementation dependency classification

The columns describe direct byte/hash effect; they are not authorization or a landing exemption.

| Work item / concrete path family | No protected change possible now | P01 protected effect | Track C package code_hash | Integration/FPIA |
|---|---|---|---|---|
| This scoped Markdown/JSON review; source manifests/readiness evidence | Yes | No direct 7-file digest change | No | Exact candidate landing still audited |
| Read-only raw restoration/hash inventory and evidence-time/source classification audit | Yes; no source metadata rewrite | No | No | Evidence may inform later acceptance; does not establish it |
| Nondeployed schema example or trace matrix outside package, with NOT_ACTIVE markings | Yes | No direct digest | No | Any incorporated candidate addition needs closed-world assessment |
| Experiment JS Decimal/absence/overlap oracle or browser fixture | Potential isolated future work; no production claim | No direct digest | No | Required before any production landing; no bypass by path placement |
| Add production chart Python anywhere under src/investment_system | **No; deferred by current user instruction** | Not inherently one of 7 files | **Yes**, even a new unrelated .py file | Exact tree FPIA and owner checks required |
| Extend producer registry/extractor/read service as package Python | Deferred | Depends on exact existing files; owner routing required | Yes | FPIA + relevant producer/publication checks |
| Change product/web_mvp.py or producers/assembler.py | **Forbidden now** | **Yes**, explicitly in 7-file digest | Yes | FPIA plus separately authorized P01 protected change; FPIA does not authorize repin |
| Edit web_assets/app.js actual/target fallback and chart route | Deferred production owner work | Not direct 7-file byte digest | No, if JS only | Web-owner regression and exact merge-result FPIA; broad protected ownership still applies |
| Actual source ingestion/classification storage using existing read paths | Evidence discovery permitted; production writes not decided | Path-specific | Path-specific | Exact proposed mutation path must be classified first |
| Frozen contract edits, grants, Official/LIVE or canonical merge | **Forbidden** | Separate protected/authority impact | Path-specific | FPIA alone supplies no approval |

### Exact code evidence for the boundaries

* `implementation/tests/test_p01_research_publication.py:429` builds a SHA-256 from exact relative path then bytes for **qgv/pipeline.py, qgv/leaderboard.py, qgv/book.py, technical/engine.py, macro/engine.py, product/web_mvp.py, producers/assembler.py**. An adopted-state selector chooses a fixed expected digest; matching some other pin is not permission to edit it.
* `implementation/src/investment_system/evl/calibration_contracts.py:74` sets root to the package and hashes relative path + NUL + bytes of **every sorted root.rglob("*.py")**. This includes new chart/provider/product Python outside Track C. A package-only addition changes source identity even if existing financial outputs stay equal.
* Fresh GCH-014 says CDR-014 hardened FPIA is approved and **implementation/verification IN_PROGRESS**; no completed exact-tree FPIA acceptance is established. PR40's 1,518 tests / 10 CI successes are separate evidence.
* CDR-014 requires history-preserving exact merge-result audit, authenticated reference manifest, explicit CODE_IDENTITY_SAME/DIVERGED, no divergence normalization, and preregistration at the final candidate after capability integration. It explicitly does **not** approve #17 protected digest repin, Frozen rewrite, grants, promotion, numeric defaults, Holdout or canonical merge.

## Source anchors

All runtime source anchors below are at PR40 `acaf1b5`; the PR41 sources are at `97685dd`.

| Source | Relevant symbol / evidence |
|---|---|
| personal/portfolio.py | ModelPortfolioSnapshot:37; Position:61; ActualPortfolioSnapshot:74; total_value:97; weights:100 |
| personal/money.py | Money:14; FxRate:26; ConvertedMoney:42; convert:50 |
| personal/versioning.py | `_canon`; content_hash:44; Provenance:51 |
| producers/serialization.py | to_jsonable:15; canonical_bytes:44; canonical_sha256:53 |
| producers/contract.py | make_snapshot:86; not_available:109; NOT_AVAILABLE branch:143; verify_inputs:208; store_resolver |
| sessions/binder.py | BoundBar:29 retains close/volume only; bind_yahoo_bars:83 joins vintage/listing; session-close eligibility is not source availability |
| publication/envelope.py | attach_publication_envelope:22, outside-data additive decision and unchanged schema-1 |
| publication/predicate.py | decide:42; explicit empty grants prevent display; producer PASS is not a grant |
| publication/invalidation.py | resolve_target:109; append-only authenticated target chain, available_at visibility |
| PR41 evidence/2026-10-04-source | fetch-evidence.json; raw-store manifest/blob `yahoo_chart__NVDA__5d`; current raw/source roles |
| PR41 evidence/portfolio-reference-source.json | Target reference source and classification/identity limitations |
| PR41 portfolio_contract.mjs | Integer DEMO, global classification metadata and unknown/known-empty semantic oracle; not production Decimal schema |
| Coordination branch @bb4cb174 | GLOBAL_CURRENT_HANDOFF.md; COORDINATION_DECISION_REGISTER.md CDR-014 / fpia-reference-manifest |

No v0.1 file was rewritten. The JSON adequacy matrix alongside this document contains evidence mapping, corrections, synthetic probe record and exact source SHA-256 values. It is an assessment artifact, not an adopted schema.

## Additive review: expanded source coverage and source conflicts

This section records later evidence without changing the preceding v0.1 assessment or adopting the v0.2 proposals. `MARKET_EVIDENCE.json` retains its earlier four-probe inventory of 4,953 rows; `MARKET_REFERENCE_COVERAGE.json` is the expanded 19-request coverage artifact. These scopes are distinct, not contradictory.

Independent read-only replay of all 19 coverage-linked original responses verified every recorded SHA-256 and reproduced **23,155 rows / 23,154 complete OHLCV rows / 23,150 complete rows with finite values, nonnegative volume and a valid OHLC envelope**. No numeric tolerance or repair was applied. All 19 requests succeeded, but every provider-symbol series remains production-identity unbound and historical-PIT unavailable. The original NVDA 5-day response remains separate acquisition evidence; later 5-year acquisition does not replace its provenance.

| Observed provider symbol / timestamp | Raw failure | Required capability disposition |
|---|---|---|
| `8035.T` / 2022-05-17 00:00 UTC | close 3869.333251953125 exceeds high 3866.666748046875 | Preserve raw bytes and report failed OHLC-envelope admission; do not clamp high/close |
| `042700.KS` / 2024-01-15 00:00 UTC | close 56200 is below low 56600 | Preserve row failure and unavailable candle capability |
| `042700.KS` / 2024-10-14 00:00 UTC | close 109500 is below low 110200 | Same; no source-free correction |
| `042700.KS` / 2025-04-09 00:00 UTC | close 61200 exceeds high 60700 | Same; no tolerance/default introduced |
| `042700.KS` / 2025-09-19 00:00 UTC | all O/H/L/C/V values null | Missing source fields remain null with coverage reason; this is not five numeric zeros |

The Japanese and Korean symbols are exploratory provider-label matches. The table identifies source rows; it does not certify issuer/security/listing mappings. Passing shape/envelope checks on the other 23,150 rows proves neither corporate-action basis nor exchange-session validity, source earliest availability, finality, quote state or publication authority.

The raw Korean response reports current regular end at 06:00 UTC (15:00 in the supplied Asia/Seoul zone) and regularMarketTime 06:30:19 UTC. The Market primary-source audit reports exchange regular close 15:30, and Japan's regular close change from 15:00 to 15:30 effective 2024-11-05. Those are source-conflict/effective-schedule findings, not a calendar vintage accepted by this review. A current provider trading period cannot supply all historical dates or resolve its own contradiction by fiat. Authoritative dated session/calendar evidence and its knowledge availability remain prerequisites.

| Existing correction | New evidence binding / supplement |
|---|---|
| C03 unavailable/diagnostic separation | Failed candle envelope and all-null row require field/capability reasons; HTTP 200 and array completeness are insufficient admission checks. Counts of present rows and admitted rows remain separate |
| C04 immutable per-input dependency closure | Each row validation must bind the original response hash, row/timestamp, requested series and identity/session/basis evidence; a label-only symbol match cannot complete the join |
| C05 time facts and decision clocks | Dated regular-session segments and schedule revision effective periods, IANA/tzdata evidence, exchange/calendar source hashes and conflict reasons must accompany the time facts. Bar epoch, regularMarketTime, declared session end and captured availability stay distinct |
| C06 catalog/assignment/identity completeness | Exploratory provider labels and exchange metadata cannot become a company industry/type assignment or sourced security-to-issuer crosswalk. Namespace/catalog/assignment identity joins stay independently evidenced |

Market adjustment and action basis supplement C04/C05: record exact source price/volume basis, action coverage, each effective/release fact and the existing owner transformation reference where one exists. The evidence proves no new adjustment engine, numeric policy or LIVE state. A failed OHLC envelope remains a failure even if a future hypothesis suggests a vendor-adjustment cause; diagnosis is not an authorized correction.

### Mapping the root's eight operational groups to seven correction categories

The root summary organizes operational requirements; this report groups schema corrections. The different counts are deliberate views of the same prerequisite set.

| Root operational group | This report's correction categories |
|---|---|
| Root C1 immutable data/current authority | C01 immutable hash boundary + C07 exact subject authority/lifecycle |
| Root C2 unavailable/diagnostics | C03 |
| Root C3 numeric execution | C02 |
| Root C4 per-input temporal dependency | C04 + C05 |
| Root C5 dated session segments/conflicts | C04 evidence closure + C05 role/effective schedule/conflict time facts |
| Root C6 classification identity/coverage | C06 |
| Root C7 completeness/basis-specific snapshots | C03 absence/capability distinction + C04 source/completeness and TARGET/ACTUAL roots |
| Root C8 range/bar lifecycle/action coverage | C03 coverage/capability + C04 immutable row/basis dependencies + C05 revisions/effective/available facts |

### Independent root-summary review

Reviewed `P0_IMPLEMENTATION_PREREQUISITES_v0.2.md` after the expanded evidence arrived. No blocking overclaim or protected-boundary contradiction was found: production wiring remains NOT_STARTED, ACTUAL is NOT_AVAILABLE, schemas remain proposals, current-source acquisition is distinct from historical restoration, and PR40 CI is not labeled FPIA acceptance. The preimplementation package/protected pause is the current user's explicit scope restriction; exact-result FPIA after implementation remains a separate verification gate.

Two nonblocking clarity points were sent to the root: include the group mapping above; and distinguish current dated-classification admission from optional quarterly-history capability in the dependency graph so missing old quarters do not unnecessarily block a separately eligible current TARGET composition. These do not relax source, PIT or publication requirements. Final root edits should be checked at their own final artifact hash; this review does not certify future revisions automatically.

**Additive resolution record.** The root subsequently reported both clarity points resolved: the current root summary now uses the same seven C01–C07 correction categories; Market session/range/conflict remains C03/C05 obligations. Its graph separates dated classification→current composition from historical snapshots→optional quarterly-history capability, with an explicit note that missing quarterly history does not block an otherwise eligible current TARGET composition. The eight-group mapping above is retained as review history, not the current root categorization. No new independent runtime or final-root certification is claimed by this resolution record.
