# RIG_NEWS_INGEST v1

Provider-neutral news ingestion boundary. It does not fetch, translate, score,
or choose a vendor. Code: `implementation/src/investment_system/rig/ingest/`.
Frozen RIG P0–P4 modules are not modified.

Code under test for this baseline: `f8539087837bd67efa3aa87d618313a333746446`
on `feature/rig-news-real-ingestion-v1`. Base
`b8e39a2196a6d7794a04a0cd5393c68329e126ca`. The rules below are the locked
scope. This version does not add a news provider, a semantic-similarity
threshold, a sentiment or impact model, a consensus source, or a LIVE expiry
policy. Disposition: INTEGRATION WAIT. PR #13 stays draft and unmerged.

`NormalizedNewsItem` is the normalized representation of one supplied article.
It is **not** `rig.model.NewsEvent`. That frozen type remains a real-world
economic event (`CONTRACT`, `CUSTOMER_WIN`, …). This package does not create a
second Event store.

## Pipeline

```text
NewsRawItem
  -> provenance (source, source item id, canonical URL, fetched_at, raw hash)
  -> published_at <= available_at <= fetched_at, all <= caller clock
  -> exact company_id resolution (ENTITY_MATCH_V1)
  -> exact duplicate / source-asserted group
  -> NormalizedNewsItem
  -> RIG input (SourceRef + Evidence; NewsEvent only if kind and claim are supplied)
  -> PRODUCER_SNAPSHOT v1 section "news", or NOT_AVAILABLE
```

Raw bytes stay in `IngestResult.raw_by_hash`. The public normalized JSON stores
`raw_hash` and `body_sha256`, never the body. `display_locale` is rejected if
placed on an item and ignored if passed to `ingest`. It does not change
`source_language`, ids, or hashes.

## Preserved fields

source, source_item_id, canonical_url, title, published_at, available_at,
fetched_at, source_language, raw_hash, provenance, canonical_entity_ids,
duplicate_group_id, methodology (`RIG_NEWS_INGEST` / `1`).

## Identity and time

- Canonical URL: lowercase scheme and host, drop fragment, sort query, reject
  credentials. Tracking parameters are not stripped (no approved denylist).
- Future timestamps relative to the caller-supplied `now` are `FUTURE`.
- `published_at > available_at` or `available_at > fetched_at` is `TIME_ORDER`.
- Same `(source, source_item_id)` with a different payload is `CONFLICT`.
- Same raw hash and same content mapping is an exact duplicate. The first item
  stays; the repeat is withheld from the feed and from RIG input.

## Entities

`AliasIndex` resolves an explicit mention to an existing `company_id`.
Match key is NFKC + casefold + punctuation-to-space. Tickers also drop spaces.
That is equality, not a similarity score. Unknown stays `UNKNOWN`. Two
company_ids for one key stay `AMBIGUOUS` and are not chosen.

`index_from_registry` reads a PR #7 `ENTITY_SEARCH_METADATA_REGISTRY` v1
document. This branch does not copy that registry and does not import
`product.entity_metadata`. Audited read-only SHA:
`a013f1c1758642f90a65fe11df69fc234c143a48`.

`issuer_id` is applied only from a caller-supplied `company_id -> issuer_id`
map. Tickers are never turned into issuers.

## Duplicates versus same-event repeats

| Rule | Result |
|---|---|
| Identical raw bytes and content mapping | `EXACT_DUPLICATE`, shared `duplicate_group_id` |
| Provider `source_asserted_group_id` shared by two different payloads | both kept, `SOURCE_ASSERTED_REPEAT` |
| Similar titles, no asserted group | not grouped |
| Semantic similarity | `POLICY_BLOCKED` (`assign_semantic_group` always raises). No threshold constant exists |

`UPDATE` / `FOLLOW_UP` remain RIG `EventLink` values. Ingestion does not infer them.
Cards for canonical items use status `NEW`. Exact duplicates are omitted from the
producer data list.

## RIG input

`to_rig_input` builds frozen `SourceRef(kind=NEWS)` and `Evidence`.
`promote_news_event` builds `Claim` + `NewsEvent` only when `EconomicEventKind`,
statement, and `ClaimPolarity` are all supplied. `occurred_on` stays `None`.
Sentiment and impact scores are not fields.

## Producer snapshot

Emits the audited PRODUCER_SNAPSHOT v1 shape (SHA `6fe9eee5668388fa4a200904520a0b5a46c90b6f`)
without importing that unmerged package.

- No batch: `NOT_AVAILABLE`, `reason_code=NEWS_NO_SOURCE`.
- Reviewed non-synthetic batch: `FROZEN_SNAPSHOT`, validation `PASS`, scope `DOCUMENT`.
- `LIVE` requires a caller-supplied `expires_at`. No TTL is defined here.
- `DEMO` only when every included item is `synthetic=true`.
- Section `consensus` is not part of PRODUCER_SNAPSHOT v1 and is not emitted.
  News cards have no `consensus` field.

Web MVP (unmerged) reads `event_id`, `headline`, `issuer_ids`, `available_at`,
`status`, `source_language`. Those keys are present. `event_id` here is the
normalized news id, not a frozen `NewsEvent` id, until explicit promotion.
`issuer_ids` are empty unless the caller passes the company/issuer map.
