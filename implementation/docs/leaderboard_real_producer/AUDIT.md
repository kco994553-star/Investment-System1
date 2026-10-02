# Leaderboard REAL Producer v1 — Pre-implementation audit

Recorded 2026-10-01 (UTC) from `git fetch origin` before this branch's code was written.
GitHub is the source of truth. This file is enough to take over without the chat.

## 0. Pinned refs

| Ref | Commit | Role |
|---|---|---|
| canonical `claude/investment-system-top500-validation-alrugm` | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` | Base of this branch. Track A FROZEN_VERIFIED is merged |
| QGV Real Producer PR #10 `ccr-db5d5960-qen9yi` | `5eec129ef81641f0bc11f5adbb43d0b2122ee24b` | **Read-only input.** Persisted QGV_COMPANY_RESULT v1 for the three Frozen as-of dates. Not merged. Source is not copied here |
| Producer Infrastructure PR #9 `feature/producer-infrastructure-v1` | `6fe9eee5668388fa4a200904520a0b5a46c90b6f` (code `bcfdcd2487f643feddda7a0fa2cace085ffc28a3`; `implementation/src` unchanged since `5fa7ce0647b6af91d767c54ecaaa3e31d1ab63e4`) | **Read-only.** Not stacked as the PR base. `src` is not copied |
| Web MVP PR #5 `feature/web-mvp-v1` | `a4e49c83f5783c19617fb609b8f95b179cb13e84` | Web schema-1 leaderboard fields |
| Global Language/Search PR #6 | `eda65bf5d9203aee05f4d28992d1ccfcd815ebd4` | Search rank is a different function |
| Entity Metadata PR #7 | `a013f1c1758642f90a65fe11df69fc234c143a48` | Search/display only. Not an identity source |
| Track C PR #4 `feature/track-c-evl` | `885c673d59bf95ca1a4c0aea96f0f6a77a0c2725` | Not read. Not assumed complete |
| Technical PR #11 | `a2e0790dd7fb267ebaa7d052acae59220ecf631e` | Not an input. Not merged |
| Macro PR #12 | `61d3352d5d68c7830e924f17613598ca79fcec6f` | Not an input. Not merged |
| No `feature/leaderboard-real-producer-v1` existed at audit time | — | This branch was created from canonical |

## 1. Answers

1. **Entry point.** `qgv/leaderboard.py` `LeaderboardEngine.build`. Callers: `universe/events.py` `IncrementalEngine.refresh_leaderboard` (current members that already have a snapshot), `tools/run_pipeline.py` (synthetic demo), `qgv/book.py` (synthetic book). There is no separate real-data leaderboard entry point on canonical.
2. **Calculation path.** The engine does not rescore. It sorts the given `QGVSnapshot`s with  
   `(total_score is not None, total_score or -1, Q_score or -1)` reverse=True, then assigns `rank = 1..n` in that order (`leaderboard.py` lines 30–34). Python's sort is stable, so ties keep input order.  
   This is **not** `validation/vertical_slice.rank_cross_section` (eligible if Q and G are present, then Q, G, V, with `or 0.0` inside the key). QGV PR #10 stores that other rank as `cross_section.rank`. It is lineage only here.
3. **Inputs.** `universe_id`, `generated_at`, a list of `QGVSnapshot`, and an optional `tickers` map used only when `IdentifierRegistry` does not already know the `company_id`. Scores are read, not computed.
4. **QGV relationship.** `recomputed_qgv=False`. The row copies Q/G/V/`total_score` and `qgv_snapshot_id`. `total_score` on the engine is `(Q+G)/2` rounded to 4 decimals when both exist, else null (`analysis.py`). V is `PROVISIONAL_INITIAL_PRIOR` and is not in `total_score`. This producer does not change that.
5. **Technical / Macro / Portfolio.** `LeaderboardEngine` does not read them. Spec sections 7, 12 and 18 name scenario, portfolio and reassessment columns. Those producers are not integration-ready (Technical PR #11 model `NOT_AVAILABLE`; Macro PR #12 is a separate baseline; Portfolio has no actual holdings). They are not added as ranking inputs.
6. **Synthetic / fixture.** `tools/run_pipeline.py` and `qgv/book.py` build synthetic leaderboards. Unit tests use synthetic snapshots. Canonical has no real leaderboard export.
7. **Real evidence before this work.** None for a leaderboard. QGV PR #10 has 500/500 PASS persisted records for 2024-06-30, 2024-09-30 and 2024-12-31. PASS there means valid persistence, not fully scored and not investment-ready. Observed coverage on 2024-12-31: PARTIAL 468, BLOCKED 32, READY 0. Null `total_score` 32. Same pattern on the earlier dates (PARTIAL/BLOCKED only).
8. **Web schema.** PR #5 `web_assets/app.js` `leaderboard()` reads `rows[].rank`, `company_id`, `ticker`, `market_cap_rank`, `total_score`, `daily_move`, `consensus`, `scenario`, `reevaluation_trigger`. Missing values render as not provided. PR #9 `adapters.WEB_READS['leaderboard']` lists the same fields. `leaderboard_section` serializes `LeaderboardSnapshot` verbatim and rejects `recomputed_qgv`.
9. **Fields the engine row does not have.** `market_cap_rank`, `daily_move`, `consensus`, `scenario`, `reevaluation_trigger`. Classification:

   | Field | Class | Why |
   |---|---|---|
   | rank, company_id, ticker, total_score | AVAILABLE | Engine row. `total_score` may be null; null is kept |
   | market_cap_rank | DERIVABLE_WITHOUT_SEMANTIC_CHANGE | Official snapshot `members[].rank` (+ `rank_is_lower_bound`). Display only. Not on `LeaderboardRow`, so the Infrastructure adapter still omits it |
   | daily_move | DATA_BLOCKED | Not on the QGV snapshot. Not computed. Technical producer is not an input |
   | consensus | NOT_AVAILABLE | No consensus provider or snapshot anywhere in the repo |
   | scenario | DATA_BLOCKED | Spec points at QGV scenarios; `QGVSnapshot` has none. Technical scenarios are not used |
   | reevaluation_trigger | NOT_AVAILABLE | Spec §18–20 is design-only. No threshold is invented |

10. **Consensus.** No source. Not replaced by QGV or price momentum. A future provider would need its own snapshot id, as-of, observation count and methodology, distinct from QGV. None is chosen here.
11. **Producer Infrastructure.** Section `leaderboard` is registered as `NOT_AVAILABLE` / `LEADERBOARD_NO_UPSTREAM_QGV` (`producers/registry.py`). That placeholder is now stale relative to PR #10, but this branch does not edit PR #9. Publication of `PROVISIONAL_RESEARCH` as `LIVE` or `FROZEN_SNAPSHOT` raises `ResearchStatusError`. P01 is still a proposal. Shape compatibility of `LeaderboardSnapshot` is PARTIAL.
12. **Track C.** PR #4 head `885c673` is not treated as validation or promotion. Holdout is not read. Nothing is labeled OFFICIAL, VALIDATED or LIVE_OFFICIAL. `research_state.track_c_validated` must stay false.
13. **Search rank.** PR #6 `web_assets/entity-search.js` ranks matches by match type (exact ticker, prefix, substring, fuzzy). It does not read leaderboard rank. Web MVP text says market-cap rank and QGV rank are different. This producer does not import search.
14. **Replay.** The three Frozen as-of dates have Official universe snapshots on canonical (`uni_cb35a6200b61`, `uni_12c3852b8333`, `uni_0d1a30b1ee47`) and QGV exports on PR #10. Given the same snapshots, methodology and the declared input order, `LeaderboardEngine` is deterministic except `leaderboard_snapshot_id` (UUID) and `generated_at`. Those stay operational. Dates after 2024-12-31 have no approved Universe (P02) and are `POLICY_BLOCKED`, not a new current leaderboard.

## 2. Ranking semantics that this work does not change

- Sort key above, including the existing `or -1` sentinel. A stored Q of `0.0` stays `0.0`. The sentinel is not written back as a score. Ten names on 2024-12-31 have Q exactly 0.0 (bac, c, lly, ms, nem, o, plan:dd, plan:mtb, usb, well); their totals differ, so they are not a tie.
- No new weight, cutoff, Top-N, sector or volatility adjustment.
- No fill of missing Q/G/V with 0, a peer, a history or a current value.
- No use of `cross_section.rank` or `cross_section.eligible` as the leaderboard order. On 2024-12-31 the cross-section eligible count is 468; the leaderboard still ranks all 500 snapshots.
- **Ties.** The only tie on each Frozen date is the null-total group (Q null and total null): 29 / 31 / 32 names, which is exactly the BLOCKED set. They share the engine key `(False, -1, -1)`. Spec §5 says the ticker itself is not a rank key. There is no approved tie-break. Distinct engine ranks inside that band follow stable sort of the declared input order (QGV export order, `company_id` ascending). That order is recorded and **`within_tie_order_approval=POLICY_BLOCKED`**. It is not promoted to a rule. `rank_band_start` is the same for the whole group (469 on 2024-12-31).
- **PARTIAL / BLOCKED.** No leaderboard contract defines include vs exclude. The existing engine ranks every snapshot it is given, and `refresh_leaderboard` already passes every current member that has a snapshot. This producer does the same. It does not add a filter and does not add a "place last" penalty beyond the existing key (null totals sort after present totals because `total_score is not None` is false).
- **Eligibility counts.** `eligible_count` means "PASS QGV snapshot handed to the existing engine". It is not the vertical-slice eligible set. FAIL/NOT_RUN (none on these three dates) are persisted as `NOT_RANKED` with the upstream status kept. They are not dropped and not given a synthetic score.

## 3. What PASS means

A leaderboard record `PASS` means valid persistence, identity, lineage and application of the existing ranking contract. It does **not** mean the company is attractive, QGV is fully scored, the strategy is validated, there is statistical skill, or anyone should buy.

## 4. Feature classification

| Item | Class |
|---|---|
| LeaderboardEngine sort and row copy | IMPLEMENTED |
| Real persisted leaderboard (before this branch) | DATA_BLOCKED (QGV exports exist only on PR #10) |
| Synthetic demo entry points | FIXTURE_ONLY |
| Separate eligibility / tie-break / consensus / reassessment | POLICY_BLOCKED or NOT_AVAILABLE (see above) |
| Web publication of research output | POLICY_BLOCKED (P01 + Track C) |
| Post-2024-12-31 universe | POLICY_BLOCKED (P02) |

## 5. Later observation (2026-10-02)

The tables in §0 are the pins at audit time. They are not rewritten. Tips re-checked before the research-publication probe, still read-only:

| Ref | Commit now | Still |
|---|---|---|
| This branch before the probe | `1f6b2d2f020843b13222b66a3f9bce82cded5bef` | Draft PR #14. Replay evidence unchanged |
| QGV PR #10 | `5eec129ef81641f0bc11f5adbb43d0b2122ee24b` | Unchanged since the audit |
| Macro PR #12 | `61d3352d5d68c7830e924f17613598ca79fcec6f` | Unchanged since the audit |
| Technical PR #15 `feature/technical-real-model-v1` | `ce587040e7beb31b66a423eab6ca89767f2a2cf8` | Not an input. M1/M2 research record. Web publication blocked. Not PR #11 |
| Technical PR #11 | `a2e0790dd7fb267ebaa7d052acae59220ecf631e` | Unchanged. Model was `NOT_AVAILABLE` there |
| Track C PR #4 | `31e7aedaac4b7fb9c8058cd8bc5959a80db0e9a0` | Still not read. The audit pin `885c673` is the older observation, not a validation result |
| Infrastructure PR #9 | `6fe9eee5668388fa4a200904520a0b5a46c90b6f` | Unchanged |
| Canonical | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` | Unchanged |

No new eligibility, tie-break, ranking formula, consensus source, scenario, or reassessment threshold was added. The common publication probe is recorded in `RESEARCH_PUBLICATION.md`.
