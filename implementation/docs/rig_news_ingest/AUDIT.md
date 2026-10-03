# RIG / News ingestion — audit

Recorded: 2026-10-01. Code under test: `feature/rig-news-real-ingestion-v1` @ `f8539087837bd67efa3aa87d618313a333746446`. Base: canonical `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Merge-base is that canonical SHA. This branch is 1 code commit ahead and 0 behind. This file is the documentation lock on top of that commit. It does not change ingestion behavior.

Labels: `IMPLEMENTED` (this branch does this), `FIXTURE_ONLY`, `DESIGNED_NOT_IMPLEMENTED`, `PROVIDER_BLOCKED`, `POLICY_BLOCKED`, `NOT_AVAILABLE`.

| Item | Where inspected | Label |
|---|---|---|
| Provider-neutral `RIG_NEWS_INGEST` v1: raw bytes stay off the public record; provenance, time order, canonical URL, exact `company_id`, exact duplicate vs source-asserted repeat, normalized item | `rig/ingest/` on `f853908` | IMPLEMENTED |
| Frozen RIG P0–P4 outside `rig/ingest/` | SHA-256 list in `tests/test_rig_news_ingest.py` (`FROZEN_RIG`, 20 files). Tree fingerprint excluding `ingest/` matches canonical | IMPLEMENTED, FROZEN, unchanged |
| `tests/rig_fixtures.py` economic events | Canonical tests. Not a news feed | FIXTURE_ONLY |
| Frozen `rig.model.NewsEvent` | `rig/model.py` unchanged. `promote_news_event` builds one only when kind, statement, and polarity are all supplied. `occurred_on` stays `None` | IMPLEMENTED as the frozen type. Headline-to-kind inference is not implemented (`EXPLICIT_ONLY`) |
| Global/Korea `NewsItem -> Claim -> Event` as an automatic normalizer | Design only. This branch does not infer the sentence | DESIGNED_NOT_IMPLEMENTED |
| Canonical Web News UI | Not on this branch. Unmerged PR #5 `a4e49c8` and PR #6 `eda65bf` | DESIGNED_NOT_IMPLEMENTED on canonical. Presentation on those drafts is not ingestion |
| PR #7 entity metadata | `origin/ccr-41677301-10nj3u` @ `a013f1c1758642f90a65fe11df69fc234c143a48`. `index_from_registry` reads a document in memory. Package is not imported and not copied | IMPLEMENTED on that draft. Read-only here. Not merged |
| `company_id` ↔ `issuer_id` | Caller map only. Tickers are not turned into issuers | DESIGNED_NOT_IMPLEMENTED as a production map |
| PR #9 producer infrastructure | `origin/feature/producer-infrastructure-v1` @ `6fe9eee5668388fa4a200904520a0b5a46c90b6f`. Snapshot shape is emitted without importing that package. News there remains `UnavailableProducer` / `NEWS_NO_SOURCE` | IMPLEMENTED on that draft. Not edited and not merged |
| Exact duplicate vs source-asserted repeat | `dedup.py`. Similar titles are not grouped | IMPLEMENTED |
| Semantic similarity threshold | `SEMANTIC_GROUPING = "POLICY_BLOCKED"`. `assign_semantic_group` always raises. No cutoff constant | POLICY_BLOCKED |
| News sentiment / impact score | Not fields. Cards reject `sentiment` and `impact_score` | POLICY_BLOCKED |
| Paid or keyed news APIs | `PROVIDER_CANDIDATES.md`. No client, secret, or fetch | PROVIDER_BLOCKED |
| Keyless candidates (EDGAR, IR RSS, GDELT, aggregators) | Survey only | NOT_ACTIVATED. Not added by this lock |
| Consensus source or consensus section | Not part of PRODUCER_SNAPSHOT v1. Not emitted. Leaderboard consensus untouched | NOT_AVAILABLE |
| LIVE `expires_at` policy / TTL | `build_news_snapshot` refuses LIVE without a caller-supplied `expires_at`. No duration is defined | POLICY_BLOCKED as an invented TTL. Caller-supplied expiry is only a required input, not a policy |

No new provider, semantic-similarity threshold, sentiment or impact model, consensus source, or LIVE expiry policy is introduced.

## Unresolved scope frozen with this baseline

| Unresolved item | Why it stays open |
|---|---|
| News provider activation | No reviewed keyless source is wired. Selecting one is a later change |
| Semantic same-event grouping | Architecture v0.1 names grouping and publishes no threshold |
| Sentiment / impact model | No approved news-score design. Frozen P2 relationship materiality is not reused |
| Consensus | No source. Absence stays `NOT_AVAILABLE` |
| LIVE expiry | No approved TTL. This package will not invent one |
| `issuer_id` production map | Upstream company↔issuer map is not on this branch |
| PR #7 and PR #9 merge | Compatibility was checked against the pinned SHAs only |

## Readiness at `f853908`

| Flag | Verdict |
|---|---|
| RIG_INGESTION_CONTRACT_READY | YES |
| ENTITY_RESOLUTION_READY | YES |
| DEDUP_READY | YES for exact duplicate and source-asserted repeat only |
| REAL_NEWS_PROVIDER_READY | NO |
| RIG_REAL_PRODUCER_READY | NO. A reviewed batch can emit a news snapshot. Unattended output is `NOT_AVAILABLE` / `NEWS_NO_SOURCE` |
| CONSENSUS_PRODUCER_READY | NO |

GitHub combined status for `f853908` was `pending` with `total_count=0` and `check_runs=0`. That is not a pass. The only workflow on this branch is `c21-real-data`, and it is `workflow_dispatch` only.
