# ChartDocument v0.2 Proposal

**PROPOSAL_NOT_ADOPTED / NO_RUNTIME_SCHEMA / NO_PRODUCTION_APPROVAL**.

This additive proposal follows P0 Chart Contract v0.1 at PR41 `54ee254` and the seven corrections in P0 Implementation Prerequisites v0.2. Both files, prior evidence, and Core81/Extended24/Candidates8 are unchanged. v0.3 is the audit checkpoint version, not the proposed ChartDocument version.

## Evidence-driven decisions

| Candidate | Decision | Retained or refined responsibility |
|---|---|---|
| C01 | KEEP | Immutable payload/input/request-revision identity and hash separate from current authority envelope |
| C02 | KEEP | Original numeric representation, owner calculation context/result/hash and lossless wire preservation |
| C03 | CHANGE | Per-capability source absence, diagnostic invalid data, partial coverage, known zero and verified empty |
| C04 | CHANGE | Independent TARGET allocation lineage and ACTUAL account/position/cash/valuation/FX lineage |
| C05 | CHANGE | Explicit timestamp roles, listing/trading regime, source-backed session/calendar, availability versus observed access |
| C06 | CHANGE | Industry/Theme/Type catalogs and assignment revisions, exact membership completeness and derived Overlap |
| C07 | KEEP | Exact subject publication/invalidation and consumer/decision-time authority binding |
| Additional C08 | PROPOSE | Source-use rights evidence separate from internal publication authority |

DROP: none. C08 does not establish rights, define a new permission enum or issue a grant. The source owner must supply actual entitlement evidence for the intended use if the capability requires it. Unknown rights stay UNKNOWN. A legal current source does not by itself prove historical knowability.

## Proposed object responsibilities

Names describe logical roles only; no JSON/Python schema, Frozen class, defaults, validation thresholds or serialization policy is adopted here.

| Object role | Required relationship / evidence |
|---|---|
| ImmutableDocumentPayload | Versioned hash preimage; exact source/input revisions, owner outputs, calculation/classification selection and evidence references. Never mutate after invalidation |
| CurrentAuthorityEnvelope | Existing owner decision for exact immutable subject hash, consumer/scope, decision time and current invalidation chain. Evaluated separately from immutable payload |
| SourceUseEvidence | Source/contract/version, permitted use/retention/display/derived-output/third-party/API/MCP scope and evidence when supplied. Product grant/FPIA cannot substitute |
| SourceRevisionRef | Provider/source, immutable artifact hash/bytes/request, revision identity, original numeric token/type and transformation lineage. Different observations may have different hashes |
| TemporalEvidence | event/bar/session time; raw provider timestamp and role; provider available_at, observed_at, ingestion and knowledge-access/cutoff facts; effective interval and source vintage. Missing roles stay UNKNOWN |
| ListingSeriesBinding | Internal subject and listing namespace; issuer/share-form evidence; provider symbol, effective interval and trading_regime; continuity/change/delisting evidence. No ticker-only stitching |
| SessionEvidence | Exchange/timezone, dated calendar version/source, open/close/early-close/holiday/exception facts and per-bar binding. Provider epoch is not automatically actual open/close |
| PortfolioSnapshotRef | One TARGET or ACTUAL root/revision, scope, source/calculation refs, data_as_of/cutoff/completeness and authoritative denominator |
| TargetAllocationEvidence | Authored target row/value/cash/strategy refs. No fabricated quantity, market value, account, price or FX inputs |
| ActualPositionEvidence | Actual account/position/security/valuation sources; original money, conversion/FX availability/context and result; cash source/account/time and completeness |
| ClassificationCatalogRef | Explicit dimension/taxonomy namespace, hierarchy/level, catalog version, source/methodology and validity/availability. Catalog is not subject assignment |
| ClassificationAssignmentRevision | Exact subject/granularity, source/hash/methodology/version, assignment revision, effective interval/available_at and membership completeness. Confidence only if source supports it |
| ClassificationExposure | One owner-produced projection of authoritative weights/amounts, denominator/coverage, exact catalog/assignment selection and arithmetic context/output hash |
| CapabilityAssessment | Field/range/capability reason and evidence. READY source fields, ready domain output and authorized product are separate assessments |

Industry explicitly names GICS only after lawful assignment admission, or another admitted taxonomy by its own name. Sector default/drill-down is conditional proposal. StrategyTheme is user/system-defined and strategy-scoped, including legacy authored buckets. InvestmentType is multi-label. TypeOverlap is derived from complete exact Type concept sets, not a fourth independently assigned taxonomy.

## Invariants proposed for owner alignment

- TARGET and ACTUAL have independent roots/shapes/denominators. Missing ACTUAL returns NOT_AVAILABLE; neither model actual_weight nor target values fill it.
- Current TARGET Theme can be admitted independently of unavailable GICS/Type/ACTUAL or quarterly history. Historical capability additionally requires admissible input/classification/valuation revisions at its own cutoff.
- Type membership totals may exceed100%. Exact Overlap counts each authoritative exposure unit once; preserve cash, unknown, partial and complete-empty categories. Partial positive memberships cannot establish an exact set.
- Preserve Decimal source/context/result, float source representation when applicable, and upstream validation. Display encoding/pixel conversion does not set precision/rounding, recompute financial totals or renormalize values. Nonfinite/invalid data remains inadmissible.
- Each OHLCV field has a declared evidenced basis. Adjclose cannot replace close alone in a full candle. Corporate effective/distribution/first-adjusted-trade dates remain separate roles; action absence is not proof of no actions.
- GEV pre-Apr2 bars require trading-regime binding; Hanmi CSAT09:00 raw timestamp does not mean10:00 actual session open. Do not backdate available_at to bar/session close or receipt dates.
- Invalid source values remain immutable diagnostics. Owner must select explicit block/degrade/annotate policy before product rendering; no silent repair/drop/interpolation.
- Verified Source → Domain Calculation → Product/Chart Contract → API → Web. Future MCP consumes the same materialized result/authority; renderers/transports do not classify subjects or recompute financial values.
- Feed LIVE/DELAYED/CLOSE/UNKNOWN is independent of Official/LIVE. Valid data, source rights and internal authority are separate gates.

Evidence counterexamples: 19 original price responses / 23,155 rows; five unchanged anomalies;10,862 exact adjclose cross-request differences with cause UNKNOWN; absent actual source; all19 Type assignments unresolved; legal GICS assignments admitted0/19; ambient Decimal context/serializer gap in existing prerequisites. See [full candidate review](contract-integration/CHARTDOCUMENT_V02_CANDIDATE_AND_FPIA_REVIEW_v0.3.md) and [Portfolio architecture](portfolio-architecture/PORTFOLIO_CLASSIFICATION_ARCHITECTURE_v0.3.md).

## Adoption dependency

Owner/source alignment and exact path/impact review must precede implementation. Any package Python changes affect Track C code_hash; protected Web/assembler changes affect P01. Integration PR42 head FPIA PASS does not close existing D3/independent review/GIE gates, authorize digest repin, or certify Chart's later merge result. Exact implemented tree then needs source/domain parity, PIT/negative/publication/browser checks and Integration/FPIA. Production schema adoption, Frozen changes, grant, Official/LIVE, Holdout and canonical merge remain outside this proposal.
