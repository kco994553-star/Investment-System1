# Leaderboard REAL Producer v1 — Status / Handoff

**State: IMPLEMENTATION BASELINE / INTEGRATION WAIT**

Do not merge automatically. Do not add a new ranking feature on this branch.

| Item | Value |
|---|---|
| Branch | `feature/leaderboard-real-producer-v1` |
| Implementation commit | `11e18d8be60c20480b6ab3d2241d752e96b0cd47` (evidence `operational.code_commit` points here; the evidence commit itself is the following one) |
| Base | canonical `claude/investment-system-top500-validation-alrugm@b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Why this base | The leaderboard engine and Official snapshots live on canonical. PR #9 and PR #10 are read-only pins, not merge parents |
| QGV input pin | PR #10 `ccr-db5d5960-qen9yi@5eec129` |
| Infrastructure pin | PR #9 `6fe9eee` (code `bcfdcd2`) |
| Track C observed, not used | `feature/track-c-evl@885c673` |

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

- New tests: 18 passed under pytest  and under the `mini_pytest` shim. Coverage includes determinism, identity, universe hash, QGV hash, no silent drop, null not filled, PARTIAL/BLOCKED kept, PIT / provenance / synthetic / promotion failures, tie `POLICY_BLOCKED`, exporter does not call the engine, search rank not an input.
- Full suite: **414 passed, 0 failed** with `python tools/mini_pytest.py` and with `python -m pytest`.
- Infrastructure compat against pin `6fe9eee`, all three dates: **PASS**. Research candidate rejected with `ResearchStatusError`. Published state `NOT_AVAILABLE` / `LEADERBOARD_RESEARCH_ONLY_NO_EXPORT`. `assemble_bundle` + `validate_bundle` PASS. Engine not called on the export path. Report: `evidence/infra_compat.json`.

## Cross-track

Diff vs `b8e39a2` is only `leaderboard_producer/`, the two tools, the two tests, `docs/leaderboard_real_producer/`, `reports/leaderboard_producer/` and `.github/workflows/leaderboard-real-producer.yml`.
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
