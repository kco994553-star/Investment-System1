# Leaderboard REAL Producer v1 — Status / Handoff

**State: IMPLEMENTATION BASELINE / INTEGRATION WAIT**

Draft PR [#14](https://github.com/kco994553-star/Investment-System1/pull/14). Base is canonical `b8e39a2`. Do not merge automatically. Do not add a new ranking feature on this branch.

| Item | Value |
|---|---|
| Branch | `feature/leaderboard-real-producer-v1` |
| Implementation commit | `11e18d8be60c20480b6ab3d2241d752e96b0cd47` (`operational.code_commit` in the Frozen manifests; unchanged by the publication probe) |
| Evidence commit | `a045768bae9488db35087dc4e4faadef327bdeea` |
| Handoff before the publication probe | `1f6b2d2f020843b13222b66a3f9bce82cded5bef` |
| Publication-probe commit | `c38ea87e9d796f1f7b8e1c19c69aca6e12f06792` |
| Branch HEAD | the commit that records this line. Its parent must be the probe commit above. Replay fingerprints are not in either commit |
| Base | canonical `claude/investment-system-top500-validation-alrugm@b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Why this base | The leaderboard engine and Official snapshots live on canonical. PR #9 and PR #10 are read-only pins, not merge parents |
| QGV input pin | PR #10 `ccr-db5d5960-qen9yi@5eec129` |
| Infrastructure pin | PR #9 `6fe9eee` (code `bcfdcd2`) |
| Track C observed, not used | `feature/track-c-evl@31e7aedaac4b7fb9c8058cd8bc5959a80db0e9a0` (2026-10-02). Not a validation result. Audit-time pin remains `885c673` in `AUDIT.md` |
| Technical candidate observed, not an input | PR #15 `ce587040e7beb31b66a423eab6ca89767f2a2cf8` |

Read with `AUDIT.md` and `CONTRACT.md`.

## Real replay (offline, no refetch)

QGV exports at the pin, Official snapshots from canonical. `tools/leaderboard_producer.py --now 2026-10-01T11:40:00+00:00`.

| as_of | universe | expected | eligible | ranked | not ranked | PARTIAL | BLOCKED | READY | null total | tie groups | tied names | within-tie | ranking fingerprint |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2024-06-30 | `uni_cb35a6200b61` | 500 | 500 | 500 | 0 | 471 | 29 | 0 | 29 | 1 | 29 | POLICY_BLOCKED | `b02a64f64ecee7e5d5c4bb1771020418bbcfa6c7c6c4d880fb559b015437857e` |
| 2024-09-30 | `uni_12c3852b8333` | 500 | 500 | 500 | 0 | 469 | 31 | 0 | 31 | 1 | 31 | POLICY_BLOCKED | `7073bfd9890e3839ce77d5519019d598198bedd273e1c3c6fd330ad81febdb1c` |
| 2024-12-31 | `uni_0d1a30b1ee47` | 500 | 500 | 500 | 0 | 468 | 32 | 0 | 32 | 1 | 32 | POLICY_BLOCKED | `754a7cee04b941d9d2936880b90368f5f7c1e2e3625a4e9ff1e61635809ded5a` |

Upstream FAIL 0, NOT_RUN 0 on all three dates. Manifest semantic hashes:

- 2024-06-30 `a878988a49d5edee2a9200069d7c15bdaff01680a0da69729b757fa5a6409741`
- 2024-09-30 `707efa49a7784427d3e7c401a21f9e4da5ebd9a941e2fe8adc56e36dfa51b49f`
- 2024-12-31 `54685a6905d57064e60564ca2d405217efd91292ebf6ea6902ea63f31d1bf665`

2024-12-31 rank 1 is `nvda` (total 50.1613, market-cap rank 2, QGV cross-section rank 21). Those three ranks are different on purpose. The null-total band starts at engine rank 469 (`rank_band_start` 469, tie size 32).

500/500 here means 500 persisted engine applications. It does **not** mean 500 fully scored or 500 investment-ready. READY coverage is 0.

## Tests

- New tests: 18 producer tests plus 10 research-publication counterexamples (28) under pytest and under the `mini_pytest` shim. Producer coverage is unchanged: determinism, identity, universe hash, QGV hash, no silent drop, null not filled, PARTIAL/BLOCKED kept, PIT / provenance / synthetic / promotion failures, tie `POLICY_BLOCKED`, exporter does not call the engine, search rank not an input. The 10 counterexamples are in `tests/test_research_publication_contract.py`.
- Full suite: **424 passed, 0 failed** with `python tools/mini_pytest.py` and with `python -m pytest` (was 414 before the publication probe).
- Infrastructure compat against pin `6fe9eee`, all three dates: **PASS** (unchanged evidence `evidence/infra_compat.json`). Research candidate rejected with `ResearchStatusError`. Published state `NOT_AVAILABLE` / `LEADERBOARD_RESEARCH_ONLY_NO_EXPORT`. `assemble_bundle` + `validate_bundle` PASS. Engine not called on the export path.

## Cross-track

Diff vs `b8e39a2` is only `leaderboard_producer/`, the two tools, the producer tests plus `test_research_publication_contract.py`, `docs/leaderboard_real_producer/`, `reports/leaderboard_producer/` and `.github/workflows/leaderboard-real-producer.yml`.
Pinned sha256 of `qgv/leaderboard.py`, `scoring.py`, `factors.py`, `analysis.py`, `technical/engine.py`, `macro/engine.py`, `qgv/portfolio.py`, `personal/portfolio.py`, `validation/vertical_slice.py` are asserted in `test_cross_track_sources_are_unchanged`.
Q/G/V/total on every ranked row equal the QGV snapshot. Technical, Macro and Portfolio are not inputs.

## Readiness

| State | Verdict |
|---|---|
| LEADERBOARD_ENGINE_AUDITED | **YES** |
| LEADERBOARD_REAL_INPUT_READY | **YES** for the three Frozen dates (QGV pin `5eec129`, research grade, not Official) |
| LEADERBOARD_SNAPSHOT_READY | **YES** (research snapshot persisted; publication blocked) |
| LEADERBOARD_BATCH_READY | **YES** for the three dates |
| LEADERBOARD_EXPORTER_READY | **YES** (validate/persist/serialize only) |
| PRODUCER_INFRA_COMPATIBLE | **YES** against pin `6fe9eee`. Re-check if that branch's `src` changes |
| WEB_LEADERBOARD_CONTRACT_READY | **NO** — daily_move DATA_BLOCKED, consensus NOT_AVAILABLE, scenario DATA_BLOCKED, reevaluation_trigger NOT_AVAILABLE. market_cap_rank is on the producer record only, not on the adapter's `LeaderboardRow` |
| REAL_LEADERBOARD_RESEARCH_PRODUCER_READY | **YES** (research grade, export-blocked, within-tie order POLICY_BLOCKED) |
| OFFICIAL_LEADERBOARD_PRODUCER_READY | **NO** — Track C not complete, P01 not approved, tie-break not approved, consensus absent |
| COMMON_RESEARCH_PUBLICATION_PREDICATE | **APPLICABLE, NOT ADOPTED** — one predicate fits PR #10, #12, #14, and #15 with no QGV-only branch. Schema-1 does not gain `RESEARCH`. See `RESEARCH_PUBLICATION.md` |

## Research publication (verification only)

`data_state`, producer validation, methodology lifecycle, Track C, and data completeness stay separate. Producer PASS on QGV, Macro, and this leaderboard does not select `LIVE` or `OFFICIAL`. Macro's lifecycle is `PROVISIONAL`, not `PROVISIONAL_RESEARCH`. Technical PR #15 has no methodology status; `m1`/`m2` `APPROVED` is not Track C, and feature/`M3` `NOT_AVAILABLE` is completeness, not the Web state. A hypothetical `RESEARCH` label does not set `track_c_validated` and cannot be promoted. Within-tie order stays `POLICY_BLOCKED`. No new eligibility, tie-break, ranking, consensus, scenario, or reassessment threshold was added.

Defined leaderboard scope stays closed. Stop at **IMPLEMENTATION BASELINE / INTEGRATION WAIT**. PR #14 stays Draft, open, and unmerged.

## Policy blockers (not decided here)

1. P01 research publication state.
2. P02 any as-of after 2024-12-31.
3. Within-tie unique order (no approved tie-break).
4. No written rule for whether PARTIAL/BLOCKED should be excluded. Existing engine includes them. A different rule would be a ranking change.
5. Consensus provider. Reassessment thresholds. Scenario snapshot owner.
6. Track C C7–C10 before any Official label.
7. PR #9 registry still says `LEADERBOARD_NO_UPSTREAM_QGV`. Integration owner updates that after this evidence is accepted. This branch does not edit it.

## Exact next step

Integration owner, after P01 and after Infrastructure is on canonical (canonical ← #5 ← #6 ← #9): point the leaderboard section at `reports/leaderboard_producer/full` through `infra_boundary.build_infra_snapshots`, keep publication in the approved research state, and do not treat engine ranks inside the null-total band as a decided order.
Do not merge this PR to produce an Official leaderboard.

Re-run: check out PR #10 exports read-only and run `python tools/leaderboard_producer.py` (see the module docstring). The tool reads local files only.
