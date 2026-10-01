# RIG news real ingestion — status

Recorded 2026-10-01. Branch `feature/rig-news-real-ingestion-v1`.
Code under test: `f8539087837bd67efa3aa87d618313a333746446`.
Base: canonical `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
Not merged. No other agent branch was modified.

Shared `CURRENT_HANDOFF.md` was not edited, so this record cannot collide with
parallel Track C, QGV, Technical, Macro, or Producer Infrastructure work.

## Judgments

| Flag | Verdict | Why |
|---|---|---|
| RIG_INGESTION_CONTRACT_READY | YES | `RIG_NEWS_INGEST` v1 parses, hashes, orders time, and normalizes deterministically. Raw body stays off the normalized record. |
| ENTITY_RESOLUTION_READY | YES | Exact ticker/name/alias → `company_id`, unknown and ambiguous fail closed. PR #7 registry is readable in memory from the audited SHA and is not copied. |
| DEDUP_READY | YES | Exact duplicates and source-asserted repeated coverage are distinct. Semantic grouping is POLICY_BLOCKED, not an unimplemented approved rule. |
| REAL_NEWS_PROVIDER_READY | NO | No provider is activated. No secret, paid API, or network fetch was added. |
| RIG_REAL_PRODUCER_READY | NO | A reviewed batch can emit a valid news `PRODUCER_SNAPSHOT`. Unattended output is `NOT_AVAILABLE` / `NEWS_NO_SOURCE`. That is not a real news producer. |
| CONSENSUS_PRODUCER_READY | NO | No consensus source exists. No consensus section or number is emitted. Leaderboard consensus stays absent. |

## Audit classification

| Area | Class |
|---|---|
| RIG P0–P4 (identity, PIT gate, News/Network views, intel, myview, discovery) on canonical | IMPLEMENTED, FROZEN. Hashes unchanged by this branch. |
| `tests/rig_fixtures.py` economic events | FIXTURE_ONLY |
| Global/Korea `NewsItem -> Claim -> Event` sentence | DESIGNED_NOT_IMPLEMENTED as a runtime normalizer before this branch |
| Canonical Web News UI | DESIGNED_NOT_IMPLEMENTED. The UI is on unmerged `feature/web-mvp-v1` (PR #5) and `feature/global-language-search-v1` (PR #6). |
| Web News UI on those branches | IMPLEMENTED presentation. It renders a bundle. It does not ingest. `display_locale` and `source_language` are already separate there. |
| PR #7 entity metadata (`ccr-41677301-10nj3u` @ `a013f1c`) | IMPLEMENTED on that draft branch. Read-only dependency. Not merged and not copied. |
| PR #9 producer infrastructure (`feature/producer-infrastructure-v1` @ `6fe9eee`) | IMPLEMENTED on that draft branch. News is `UnavailableProducer` / `NEWS_NO_SOURCE`. This branch does not edit it. |
| `company_id` ↔ `issuer_id` production map | DESIGNED_NOT_IMPLEMENTED. P0 left it as an integration item. This branch accepts an explicit map only. |
| Economic-event kind from a headline | Not inferred (`EXPLICIT_ONLY`). |
| Semantic near-duplicate threshold | POLICY_BLOCKED. Architecture v0.1 and the Global/Korea contract name same-event grouping and publish no cutoff. |
| News sentiment / impact score | POLICY_BLOCKED. No approved news-score design. Relationship materiality in frozen P2 is not reused as one. |
| Paid or keyed news APIs | PROVIDER_BLOCKED. Not selected. |
| Consensus data | NOT_AVAILABLE. No source. |

## Evidence

`implementation/docs/rig_news_ingest/evidence/validation.json`

Full canonical regression on `f853908`, reconfirmed 2026-10-01: 410 passed, 0 failed
in 18.34s, mini_pytest shim (396 existing + 14 new). Targeted
`tests/test_rig_news_ingest.py`: 14 passed, 0 failed in 0.29s. Frozen `rig/`
modules outside `ingest/` match the canonical SHA-256 list in that test.
Sibling track trees match canonical (see evidence fingerprints).

## Blockers

1. No legally reviewed, keyless news provider is activated. See `PROVIDER_CANDIDATES.md`.
2. Semantic same-event grouping needs an approved threshold before any code may group by text similarity.
3. `issuer_id` for Web company filters needs the upstream company↔issuer map. It is not guessed from tickers.
4. Producer Infrastructure and Entity Metadata are still draft PRs. Compatibility was checked against pinned SHAs, not by merging them.
5. `LIVE` news has no approved `expires_at` policy, so this package will not invent a TTL.

## Remote reconfirm (2026-10-01, after fetch)

| Check | Result |
|---|---|
| PR | [#13](https://github.com/kco994553-star/Investment-System1/pull/13) `draft=true`, `state=open`, `merged=false`, `mergeable_state=clean` at `f853908` |
| Code under test | `f8539087837bd67efa3aa87d618313a333746446`. This lock is docs-only on top of that commit |
| Base / merge-base | `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Code commit is 1 ahead, 0 behind |
| Code diff | Additions only: `rig/ingest/` (10 modules) and `tests/test_rig_news_ingest.py`. No edits under `qgv/`, `technical/`, `macro/`, `personal/`, `prompt_library/`, `validation/`, `contracts/`, `product/`, `providers/`, `universe/`, `ingestion/`, `integration/`, `markets/`, `pit/`, or frozen `rig/` outside `ingest/` |
| Audited pins still current | PR #7 `a013f1c1758642f90a65fe11df69fc234c143a48`. PR #9 `6fe9eee5668388fa4a200904520a0b5a46c90b6f`. Neither is an ancestor |
| Not incorporated | Track C `885c673d59bf95ca1a4c0aea96f0f6a77a0c2725`. Web #5 `a4e49c83f5783c19617fb609b8f95b179cb13e84`. Language #6 `eda65bf5d9203aee05f4d28992d1ccfcd815ebd4`. QGV #10 `5eec129ef81641f0bc11f5adbb43d0b2122ee24b`. Technical #11 `a2e0790dd7fb267ebaa7d052acae59220ecf631e`. Macro #12 `61d3352d5d68c7830e924f17613598ca79fcec6f` |
| Already in the canonical base, not moved | Track D `feature/track-d-rig-news` @ `da86dfc26dcaa5c32c60762683dcca702a0c57b8`. Track E `feature/track-e-prompt-library-v1` @ `d226481e1b49e0910642478ae80545598e2e5a98` |
| CI | Combined status `pending`, `total_count=0`, `check_runs=0` for `f853908`. Not a pass. `c21-real-data` is `workflow_dispatch` only |

## Unresolved scope (do not implement on this baseline)

| Item | Label |
|---|---|
| Any new news provider, including the surveyed keyless candidates | NOT_ACTIVATED. Keyed or paid APIs stay PROVIDER_BLOCKED |
| Semantic-similarity threshold | POLICY_BLOCKED |
| Sentiment or impact model | POLICY_BLOCKED |
| Consensus source | NOT_AVAILABLE |
| LIVE expiry / TTL | POLICY_BLOCKED. Caller-supplied `expires_at` is required for LIVE and is not a policy |

## Disposition

RIG / NEWS INGESTION IMPLEMENTATION BASELINE / INTEGRATION WAIT

Defined scope is closed at `f853908`. Do not merge PR #13. Integration waits for the owner. This branch does not take Track C, QGV, Technical, Macro, Web, Entity Metadata, or Producer Infrastructure work.

