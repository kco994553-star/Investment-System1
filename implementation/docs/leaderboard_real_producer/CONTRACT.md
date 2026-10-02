# Leaderboard REAL Producer v1 — Contract

Code: `src/investment_system/leaderboard_producer/`.
Tools: `tools/leaderboard_producer.py`, `tools/leaderboard_producer_infra_compat.py`.
Tests: `tests/test_leaderboard_real_producer.py`, `tests/test_leaderboard_producer_infra_compat.py`.
CI: `.github/workflows/leaderboard-real-producer.yml`.

**Single responsibility:** replay the existing `LeaderboardEngine` on QGV Real Producer snapshots and persist the result.
This producer does **not** define a new score, weight, cutoff, tie-break, eligibility filter or Official state.

## 1. Flow

```
QGV PR #10 persisted export (read-only pin 5eec129)
  → verify semantic hashes, PIT, provenance, research flags, universe members hash
Frozen Official snapshot on canonical (members hash must match the QGV manifest)
  → LeaderboardEngine.build (unchanged)
  → LEADERBOARD_COMPANY_RESULT v1 + LEADERBOARD_PRODUCER_BATCH_MANIFEST v1
  → exporter: validate, persist, serialize (does not rank)
  → infra_boundary: Producer Infrastructure v1 (read-only) → published state NOT_AVAILABLE
```

Raw QGV is not recomputed. The raw store is not required and is not fetched.
As-of dates other than `2024-06-30`, `2024-09-30`, `2024-12-31` raise `POLICY_BLOCKED` (P02). No new Universe is created.

## 2. Ranking

Engine key, unchanged (`qgv/leaderboard.py`):

```
(total_score is not None, total_score or -1, Q_score or -1)  reverse=True
```

- Scores on the record are the QGV snapshot values, including null and `0.0`. Nothing is filled.
- `qgv_cross_section_rank` is copied and `qgv_cross_section_rank_used` is false.
- `market_cap_rank` is copied from `official_snapshot.members[].rank` with `market_cap_rank_used_in_ranking=false`.
- Input order for the stable sort is QGV record order (`company_id` ascending). `input_order_is_tie_break_policy` is false.
- If `tie_size>1`, `within_tie_order_approval=POLICY_BLOCKED`. `rank_band_start` is shared. Engine ranks inside the band are an artifact of the stable sort, not an approved ordering.
- `ranking_fingerprint` is the sha256 of the ranked rows (company, engine rank, band, tie size, approval, Q/G/V/total, coverage, QGV semantic hash). It does not include operational UUIDs or `generated_at`.

`PASS` means persistence, identity, lineage and this contract. See `not_implied` on every record. It is not a buy signal and not "fully scored".

## 3. Record — LEADERBOARD_COMPANY_RESULT v1

Semantic (hashed): as_of, company_id, ticker, status, eligibility (RANKED or NOT_RANKED plus upstream QGV status and coverage), ranking or null, scores or null, QGV `semantic_sha256`, display fields, universe identity and `members_sha256`, methodology versions and `weights_sha256`, verbatim `research_state`, PIT timestamps and known limitations, raw input ids and hashes, QGV manifest hash, official snapshot sha256, publication `NOT_AVAILABLE`.

Operational (not hashed): `generated_at`, `code_commit`, `run_id`, `leaderboard_snapshot_id`, `qgv_snapshot_id`.

Every Universe member is persisted. Upstream FAIL/NOT_RUN become `NOT_RANKED` with a reason. They are not given a score. A hash, PIT, provenance, synthetic or promotion failure aborts the batch (no partial ranking file from `build_leaderboard`).

## 4. Batch manifest

`expected_count`, `eligible_count` (PASS snapshots given to the engine), `ranked_count`, `not_ranked_count`, upstream FAIL and NOT_RUN counts, coverage counts, null-total count, informational `qgv_cross_section_eligible_count` (not a filter), tie group count, tied company count, ranking fingerprint, input hashes, methodology, research state, lineage hash, web field classes.

`eligible_count == ranked_count`. `ranked + not_ranked == expected`. A short batch is `PARTIAL_BATCH_HIDDEN`.

## 5. Web fields

| Field | Status |
|---|---|
| rank, company_id, ticker, total_score | AVAILABLE (total may be null) |
| market_cap_rank | DERIVABLE_WITHOUT_SEMANTIC_CHANGE on the producer record only |
| daily_move | DATA_BLOCKED |
| consensus | NOT_AVAILABLE |
| scenario | DATA_BLOCKED |
| reevaluation_trigger | NOT_AVAILABLE |

The Infrastructure adapter still serializes `LeaderboardSnapshot` only, so the Web bundle does not gain the five missing engine-row fields. That is intentional: the adapter must not reshape. `WEB_LEADERBOARD_CONTRACT_READY` stays no.

Consensus provider contract, if an owner later approves one: a separate snapshot with provider id, as-of, mean target, observation count and its own methodology. It must not be filled from QGV or from price momentum. No provider is selected here.

## 6. Publication

Research candidate (`FROZEN_SNAPSHOT` + `methodology.status=PROVISIONAL_RESEARCH`) is built with Infrastructure `make_snapshot` and must be rejected with `ResearchStatusError`.
Published section: `not_available`, reason code `LEADERBOARD_RESEARCH_ONLY_NO_EXPORT`.
PR #9's placeholder `LEADERBOARD_NO_UPSTREAM_QGV` is recorded as stale and is not rewritten.

Not Official. Not LIVE. Track C is not consulted and cannot be attested by this producer. Portfolio holdings do not affect rank.

`data_state`, producer validation, methodology lifecycle, Track C, and data completeness are different axes. Producer PASS does not select a Web state. The same predicate, with no QGV-only branch, also covers PR #10, PR #12, and PR #15. See `RESEARCH_PUBLICATION.md`. `RESEARCH` is not a schema-1 state. A hypothetical label still cannot become `LIVE` or `OFFICIAL` and does not clear `within_tie_order_approval=POLICY_BLOCKED`.

## 7. Pins

- QGV evidence: `ccr-db5d5960-qen9yi@5eec129ef81641f0bc11f5adbb43d0b2122ee24b`
- Infrastructure: `feature/producer-infrastructure-v1@6fe9eee5668388fa4a200904520a0b5a46c90b6f`
- Canonical base: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`
