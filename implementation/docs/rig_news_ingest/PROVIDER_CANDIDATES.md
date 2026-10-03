# News provider candidates — not activated

Surveyed 2026-10-01. Nothing in this file is wired, fetched, or given a secret.
`REAL_NEWS_PROVIDER_READY=NO` until a later decision selects one source and a
separate change implements the fetch. This package only accepts bytes the caller
already holds.

| Candidate | Cost | Legal / technical note | Decision |
|---|---|---|---|
| SEC EDGAR submissions / full-text search (`data.sec.gov`, `efts.sec.gov`) | Free, no API key | Public US filings, not a news wire. Fair-access requires a contact `User-Agent` and a rate cap. Track A already owns SEC raw storage. Creating `SEC_USER_AGENT` is out of scope here. | NOT_ACTIVATED. If used later, `SourceKind` is `PRIMARY_DISCLOSURE`, not general news. |
| Issuer IR RSS | Free to fetch per site | Each site's terms differ. No single redistribution license. Not a universe-wide feed. | NOT_ACTIVATED |
| GDELT DOC | Free query API | Full-text redistribution is restricted. Not reviewed as a store-the-body license. | NOT_ACTIVATED |
| NewsAPI, GNews, NewsData, Finnhub, Polygon, Benzinga, and similar wires | Key and/or paid | Forbidden for this stage: no paid API and no new secret. | PROVIDER_BLOCKED |
| Unkeyed aggregator sites claiming full article bodies | Advertised as free | Copyright of the underlying articles is not established by the aggregator's marketing page. | NOT_ACTIVATED |

Activation, if any, belongs in its own change: a named provider, a reviewed
license, provenance back to the origin URL, and no invented sentiment.
