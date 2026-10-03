# GIE-001 · Trial integration of all open PR tips · 2026-10-03

Read-only trial. All merges were made in throwaway local worktrees and nothing was pushed. No capability branch, PR or canonical ref was changed. This is integration evidence, not canonical integration, and it is **not CI_VERIFIED**: every run below is local, in the Claude Code container.

| Field | Value |
|---|---|
| Writer | Primary Integration Writer, session `session_019znshzTYgyBnuuBmSxdPFN` |
| Remote snapshot | `git fetch --prune` at 2026-10-03T01:07Z; 28 refs |
| Canonical | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |
| Runner | Python 3.11.15. pytest 9.1.1, installed locally for this run, because the Track C tests need `pytest.mark.parametrize` and the `tools/mini_pytest.py` shim cannot import them. `PYTHONPATH=src`, same as the Track C workflow |
| Machine-readable copy | `GIE-001_trial_integration_2026-10-03.json` |

## 1. Pairwise text merge (`git merge-tree --write-tree`)

The 13 tips merged pairwise (78 pairs) were #7, #19, #12, #10, #14, #18, #16, #4, `ccr-22e3ff16`, `docs/qgv-context-policy-approvals`, `ccr-e0fc1e48`, #20 and #21. Stacked bases are contained in these tips.

Result: 1 conflict, **#20 × #21** (add/add on `CLAUDE.md` and `implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md`). Every other pair is clean.

#21 (`f1b5afb`) was also merge-tree-checked against all 26 other remote branches at 2026-10-03T01:05Z, before #20 existed: 0 conflicts.

## 2. Sequential trial merge: all open capability PR tips

Each tip was merged onto canonical with `git merge --no-ff` (ort), in dependency order:

| Step | Merged tip | Tip SHA | Trial commit | Trial tree |
|---|---|---|---|---|
| 1 | #7 (contains #6, #5) | `a013f1c` | `5b59c20` | `ccd6bd4` |
| 2 | #19 (contains #17, #9) | `c3dbf8a` | `f3d9d7c` | `bd63a66` |
| 3 | #12 Macro | `61d3352` | `5524297` | `891712e` |
| 4 | #10 QGV | `5eec129` | `63a45a8` | `0f2128f` |
| 5 | #14 Leaderboard | `0d48d86` | `478599f` | `c71f069` |
| 6 | #18 (contains #15, #11) | `2c088ce` | `c35d09f` | `86bf35c` |
| 7 | #16 (contains #13) | `ef65caa` | `a15abd4` | `6e2f09b` |
| 8 | #4 Track C | `ff78c4f` | `6ba15a5` | `5af0858` |

- Text conflicts: **0**.
- Combined diff vs canonical: 339 files, +116,223 / −0.
- Trial commit SHAs carry local author metadata and are not reproducible identities. The tree SHAs are content identities.

## 3. Regression results

| Tree | Runner | Result |
|---|---|---|
| canonical `b8e39a2` | mini_pytest shim | 396 passed, 0 failed |
| A: all tips including Track C (tree `5af0858`) | mini_pytest shim | 616 passed, 25 failed. 15 are shim import errors on Track C `pytest.mark.parametrize` (runner failures, not code failures), 7 are IF-1 and 3 are IF-2 |
| A: all tips including Track C (tree `5af0858`) | pytest | **1058 passed, 10 failed** in 417 s. The failures are exactly the 7 IF-1 guards and the 3 IF-2 sentinels. All Track C tests pass in the combined tree |
| B: all tips except Track C (tree `6e2f09b`) | pytest | 619 passed, 3 failed (all IF-2 sentinels) |
| #12 Macro exact HEAD `61d3352` | pytest | 442 passed, 0 failed |
| #13 RIG exact HEAD `8bb990b` | pytest | 410 passed, 0 failed |
| Track C tip `ccr-22e3ff16` `97d1b94` | pytest | IN_PROGRESS at this commit; the result is appended in a later commit |

## 4. Engine fingerprint (`tools/producer_engine_fingerprint.py src`; random ids and timestamps excluded by the tool)

| Section | Pinned (#9 / #12 STATUS) | Tree B (no Track C) | #9 `f8af596` + Track C `ff78c4f` | Tree A |
|---|---|---|---|---|
| qgv | `a1714480…` | equal | equal | equal |
| technical | `82165414…` | equal | **`66cb2383…`** | **`66cb2383…`** |
| macro | `7bbfad69…` | equal | **`7e427949…`** | **`7e427949…`** |
| leaderboard | `112b245b…` | equal | equal | equal |
| portfolio_official_book | `53d930a7…` | equal | equal | equal |

Field-level diff of the normalized Technical and Macro snapshots, #9 alone vs #9 + Track C: 92 lines added, **0 lines removed or changed**. Each of the 23 snapshots gains exactly four fields: `available_at: null`, `data_stamp_refs: []`, `source_vintages: []` and `input_hash: null`. No existing value changes.

## 5. Findings

### IF-1 · Track C cross-track source overlap (merge-order decision)

Track C commit `2137883` (2026-09-29, `fix(evl-upstream): derive PIT lineage and bind supported research controls`) is the four-file C4 upstream repair that the Track C handoffs record as "retained". It adds 88 lines and deletes 0:

| File | Change |
|---|---|
| `src/investment_system/contracts/lineage.py` | +66 (`StampedValue`, `derived_lineage`) |
| `src/investment_system/contracts/models.py` | +12: four optional lineage fields on `TechnicalSnapshot` and `MacroSnapshot` (default None or empty) |
| `src/investment_system/technical/engine.py` | +16: `TechnicalEngine.evaluate_stamped` wraps the unchanged `evaluate` |
| `src/investment_system/macro/engine.py` | +10: `MacroEngine.evaluate_stamped` wraps the unchanged `evaluate` |

Effect in tree A: the following 7 guards pin the canonical engine bytes (`technical/engine.py` sha256 `f7268f52…`) or the pre-change fingerprints, and they fail:

- #11 `test_technical_real_producer.py::test_engine_fingerprint_and_cross_track_sources_unchanged`
- #15 `test_technical_real_model_v1.py::test_placeholder_engine_is_unchanged_and_not_used_by_the_real_model`
- #18 `test_us_equity_session_v1.py::test_model_bytes_and_session_source_stay_in_contract`
- #12 `test_macro_real_producer.py::test_existing_engine_qgv_technical_portfolio_leaderboard_bytes_unchanged`
- #14 `test_leaderboard_real_producer.py::test_cross_track_sources_are_unchanged`
- #17 `test_p01_research_publication.py::test_engine_fingerprints_match_the_pre_change_pin`
- #17 `test_p01_research_publication.py::test_protected_engine_bytes_are_unchanged`

In tree B none of these fail, and every fingerprint equals its pin.

Because `to_dict()` serializes the new fields, a producer that persists a full `TechnicalSnapshot` or `MacroSnapshot` would have a different persisted semantic hash after Track C merges, even though no value changes.

No Technical or Macro owner approval of the Track C edit to those engine files was found. Accepting it is a protected-boundary decision (contract §N). The merge order is USER_DECISION_REQUIRED; see GLOBAL_CURRENT_HANDOFF §4.2.

### IF-2 · Branch-isolation sentinels (owner action at integration time)

| PR | Test | Assertion | Fails when |
|---|---|---|---|
| #10 | `test_qgv_producer_infra_compat.py::test_qgv_export_is_compatible_with_pinned_producer_infrastructure` | `infra_boundary.load_infra() is None` when `QGV_PRODUCER_INFRA_SRC` is unset | #9 is in the tree |
| #14 | `test_leaderboard_producer_infra_compat.py::…` | same pattern | #9 is in the tree |
| #13 | `test_rig_news_ingest.py::test_pr7_registry_is_read_only_and_not_copied` | `implementation/reports/entity_metadata` does not exist | #7 is in the tree |

Proposal for the owners (not applied): when the dependency is present in the tree, run the existing compatibility check against the in-tree code instead of asserting absence. For #13, assert that the in-tree registry is byte-identical to the audited PR #7 blob instead of asserting the path is absent. These are test-precondition changes only and touch no production semantics.

### IF-3 · Worker Contract duplicate

PR #20 (`integration/claude-worker-contract-v1` @ `d87d4cd`, created 2026-10-03T01:04:35Z) and PR #21 (`ccr-2e16018a-qukwmg` @ `f1b5afb`, created 01:06:07Z) both add the same two paths as v1.0. Semantic differences against the user's 2026-10-03 specification:

| Clause | Specification | #21 | #20 |
|---|---|---|---|
| §J no future fill | "미래정보를 보간·추정·현재값으로 대체하지 않는다" | verbatim | adds "unless an approved contract explicitly permits it" |
| §M invariance check | "numerical/semantic invariance" | verbatim | "where an existing approved fingerprint exists" |
| §4 versioning metadata (reason, approval basis, effective_from) | required on change | header + change log row | rule only, no v1.0 metadata |
| §5 relationship to other documents | required | §0.1 and §S, including the Multi-AI Relay Protocol | header line "Policy authority: none" |
| Global handoff location | — | §0.2 | absent |

### IF-4 · CI gaps

| Branch | Actions on any commit | Local exact-HEAD result (this checkpoint) |
|---|---|---|
| #12 `feature/macro-real-producer-v1` | none | 442 passed |
| #13 `feature/rig-news-real-ingestion-v1` | none | 410 passed |
| `ccr-22e3ff16-p7n5k5` (Track C C8 G-SUP) | none (the workflow triggers on `feature/track-c-evl` only) | IN_PROGRESS at this commit |

Owner action: add or extend a workflow trigger for these branches, or push to a triggered branch. Not done here.
