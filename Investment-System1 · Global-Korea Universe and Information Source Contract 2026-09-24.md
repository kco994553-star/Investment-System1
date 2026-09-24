# Investment-System1 · Global/Korea Universe & Information Source Contract
Date: 2026-09-24
Status: PROVISIONAL IMPLEMENTED CONTRACT (identity/context); provider/data coverage not yet verified

## Boundary lock
- Existing US Official Default Universe remains US Market-Cap Top 500 PIT. C-18 stays RESOLVED.
- Korea Universe and Global Universe are extensions of Investment-System1, not the separate Korean Market System.
- No Korean Market System A/B/C/B-E/B-G logic, weights, scores, or track record is imported.
- Korea/Global Top N remain PROVISIONAL until empirical coverage/eligibility validation.

## Identity/context contract
- Economic identity: Issuer -> Security -> Listing. Ticker is a listing attribute, not a permanent identity.
- Analysis Universe, Network Region, and News Region are separate contexts.
- Search result / relationship node does not imply universe membership.
- Global issuer ranking must resolve duplicate listings/share classes/ADR before official promotion.
- Historical FX is PIT input and must satisfy available_at <= as_of.

## Practical source architecture
Use source adapters -> immutable raw blobs + manifest -> normalized records -> PIT gate -> entity/claim/event resolver -> snapshots. Never let UI fetch providers directly.

### US/company fundamentals
- SEC EDGAR submissions + companyfacts/bulk archives: primary filing/XBRL source; existing fetch_real_data.py + RawDatasetStore path is reused.
- Nasdaq Trader symbol directories: current listed-symbol/security metadata only; not sufficient alone for historical PIT membership.
- Price source currently Yahoo adapter is operational evidence only; long-term production/licensing decision remains open.

### Korea universe/market data
- Primary candidate: KRX Data Marketplace Open API for listed-equity daily trading/statistical data. Requires account, API key/application/approval; documented coverage begins 2010 for listed stock daily trading API.
- A separate KRX provider must write raw responses into RawDatasetStore; it must not call the separate Korean Market System.
- Historical delisting/listing/security-master completeness must be tested before Korea Top N can be Official.

### Global universe
- No single free source is assumed sufficient. Provider adapters must supply: security master/listing history, PIT shares, PIT prices, FX, corporate actions and delistings.
- Global provider promotion is blocked until ADR/cross-listing/share-class normalization and historical coverage are measured.
- Use source priority per field; never silently merge conflicting identities.

### News / relationship graph
- Preferred evidence order: issuer/regulator/exchange primary source -> reputable/licensed news metadata/full text when permitted -> community sentiment.
- NewsItem -> Claim -> Event is normalized once; Feed/Network/Sentiment/History reuse the same IDs.
- RelationshipEdge requires evidence IDs, valid_from/valid_to, available_at, confidence, type and direction. Industry/type similarity may create discovery candidates but not an asserted business relationship without evidence.
- Community sentiment never directly mutates Q/G/V or Technical predictions.

### Reddit
- Integrate only through permitted Reddit Data API terms/approved access. Store IDs, timestamps, derived aggregates and permitted text according to terms/retention requirements.
- Pipeline: posts/comments -> entity linking -> spam/bot/duplicate controls -> mention volume + unique authors + bull/bear claims + sentiment/narrative -> Fundamental Alignment/Divergence.
- If API access is unavailable, feature state is BLOCKED_DEPENDENCY, not scraped around.

### YouTube / investment programs
- YouTube Data API can provide video/channel metadata. Official captions endpoints require authorization and captions.list does not itself return transcript text; therefore do not assume arbitrary public-video transcript download is available through the official API.
- Transcript hierarchy: publisher-provided/licensed transcript or permitted caption access -> user-provided transcript -> metadata-only summary. No invented video summary when transcript/content is unavailable.
- TV/investment programs: prefer official episode pages/transcripts/RSS or licensed feeds. Extract individual claims with speaker, horizon, evidence cited, counter-evidence, published_at and outcome status.
- Evaluate claims, not personalities. Historical claim metrics are descriptive track-record measurements.

## Processing topology
Network-enabled collectors -> RawDatasetStore (raw + provenance + vintage) -> Normalizers -> Entity Resolver (issuer/security/listing) -> Claim/Event Resolver -> Relationship Graph Store / Sentiment Store -> QGV/Technical read-only evidence adapters -> Integration -> Track Record.

Incremental updates use stable source IDs/content hashes for deduplication. Corrections create a new vintage; old raw data remains reproducible. All historical evaluation gates on source_available_at <= as_of.

## Implementation state
Implemented now: global_universe contract with Region, AnalysisUniverse, IssuerIdentity, SecurityIdentity, ListingIdentity, UniverseContext, FXSnapshot PIT gate, EligibilityRecord; regression tests added.
Not implemented/verified: KRX collector, global security-master provider, Reddit collector, YouTube metadata collector, licensed TV/news feeds, relationship/event stores, Korea/Global real-data coverage, official Top N.
