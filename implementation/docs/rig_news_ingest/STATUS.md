# RIG news real ingestion — status

Recorded 2026-10-01. Branch `feature/rig-news-real-ingestion-v1`.
Base: canonical `claude/investment-system-top500-validation-alrugm` @ `b8e39a2`.
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

Full canonical regression after this change: 410 passed, 0 failed, mini_pytest shim
(396 existing + 14 new). Frozen `rig/` modules outside `ingest/` match the
canonical SHA-256 list in `tests/test_rig_news_ingest.py`.

## Blockers

1. No legally reviewed, keyless news provider is activated. See `PROVIDER_CANDIDATES.md`.
2. Semantic same-event grouping needs an approved threshold before any code may group by text similarity.
3. `issuer_id` for Web company filters needs the upstream company↔issuer map. It is not guessed from tickers.
4. Producer Infrastructure and Entity Metadata are still draft PRs. Compatibility was checked against pinned SHAs, not by merging them.
5. `LIVE` news has no approved `expires_at` policy, so this package will not invent a TTL.
