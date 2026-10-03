# QGV Real Producer v1 — Pre-implementation audit (GitHub SSoT)

Recorded 2026-10-01 (UTC), before any code was written. Every answer cites repository evidence.
Scope: the QGV-specific producer/exporter only. Methodology, Universe, Track A/B/C/D/E and Web are read-only.

## 0. Pinned refs (`git fetch origin`, 2026-10-01)

| Ref | Commit | Role here |
|---|---|---|
| canonical `claude/investment-system-top500-validation-alrugm` | `b8e39a2` | Base of this branch. Track A FROZEN_VERIFIED is merged (PR #3) |
| `feature/producer-infrastructure-v1` | `5fa7ce0` (code `bcfdcd2`) | **Read-only dependency.** PRODUCER_SNAPSHOT v1 / PRODUCER_BUNDLE v1. Unmerged, stacked on PR #6 → PR #5 |
| `ccr-e0fc1e48-9tcto3` | `f415615` | Producer Readiness Audit (`reports/producer_readiness_audit_2026-10-01.*`) |
| PR #4 `feature/track-c-evl` | `15fed50` | Track C: C6 frozen; C7 selection policy TC-D3P-006 awaiting approval; C8–C10 not started |
| PR #5 `feature/web-mvp-v1` | `a4e49c8` | Web schema-1 (`product/web_mvp.py`), states `LIVE/FROZEN_SNAPSHOT/DEMO/NOT_AVAILABLE` |
| PR #6 `feature/global-language-search-v1` | `eda65bf` | Language & Search, stacked on #5 |
| PR #7 `ccr-41677301-10nj3u` | `a013f1c` | Entity Metadata (search/presentation only), stacked on #6 |
| Frozen raw store | Actions run `36305927245` (c21 #70), artifact `c21-raw-store-36305927245`, digest `sha256:712e43bc…f94`, expires 2026-12-26 | The only copy of the raw blobs. `.gitignore` excludes `data/raw/blobs`; git keeps manifests + `STORE_INDEX.json` (6808 artifacts with sha256) |

The cloud container cannot download the artifact (egress denied), so real-data runs execute on a GitHub runner.

## 1. Answers

1. **Real-data entry point.** `tools/official_pipeline.py` → `load_official(as_of)` (rebuilds the Official snapshot from gate evidence and checks members/order) → `validation/vertical_slice.run_vertical_slice_from_store` → `run_vertical_slice` → `validation/historical.run_as_of` → `qgv/pipeline.AnalysisPipeline.analyze_raw` → `qgv/analysis.AnalysisEngine.analyze`. Cross-section rank is `vertical_slice.rank_cross_section`; selection is `select_provisional`.
2. **Inputs.** Raw store via `ingestion/replay.build_payloads_and_bars`: `companyfacts:<CIK10>` (SEC XBRL) and `yahoo_chart:<TICKER>:5y`. `run_as_of` sets the PIT price from `pit_bar(bars, as_of)`, the own P/E, the 1-year-ago P/E percentile and a cross-section peer-median P/E. Note: if a companyfacts payload is absent, `parse_us_company` would try a live SEC fetch (`try_fetch_companyfacts`). All 3×500 Frozen members have both artifacts in `STORE_INDEX.json`.
3. **As-of with real evidence.** 2024-06-30, 2024-09-30, 2024-12-31 (`reports/gate_evidence/official_pipeline_2024-06-30_2024-12-31.json`, `track_a_freeze_readiness_2026-09-27.json`): 500 members each, selected/linked 471/469/468, universe ids `uni_cb35a6200b61` / `uni_12c3852b8333` / `uni_0d1a30b1ee47`.
4. **Per-company output today.** In memory only: `QGVSnapshot` per company (Q/G/V, total, coverage, V factor table, Q/G notes), the `quality[cid]` dict, `ranked[]` rows with rank. The Q/G sub-factor scores (`FactorObservation`s from `qgv/raw_map.map_raw`) exist only inside `analyze_raw`.
5. **Why not persisted.** `official_pipeline.py` keeps only aggregates (`n_selected`, `equal_weight_realized`, counts). `run_as_of` writes TrackRecords (Q/G/V only) to a temp file store. No writer for `QGVSnapshot` exists.
6. **Aggregate report contents.** Per date: universe id/kind/policy, n_selected, equal-weight realized return, rule id/status, counts (universe/investable/missing/name errors/linked). Walk-forward steps also keep the `selected` id list for 06-30 and 09-30. No Q/G/V values.
7. **Provenance.** Raw artifact sha256/bytes/fetched_at in `data/raw/manifests` + `STORE_INDEX.json`; Universe in gate evidence + Official snapshot; `DataStamp` (`sec_<cid>_<date>`, `available_at` = latest filed date used). The `QGVSnapshot` itself only references the stamp id: no artifact hash.
8. **Methodology/version.** `versions.py`: `QGV_SYSTEM_LINE=v1.7`, `QGV_STANDARD=v1.5-balanced`, `QGV_ANALYSIS_CONTRACT=v1.7.6`, `IMPLEMENTATION_LINE=investment_system_impl-v0.2.0`. These are copied onto each `QGVSnapshot`. Weights live in `qgv/factors.py`.
9. **Synthetic vs real.** `RawFundamentals.source_kind` (`SYNTHETIC` vs `LIVE_FETCH`; store replay also yields `LIVE_FETCH`), `DataStamp.synthetic`, `QGVSnapshot.synthetic`, `coverage_state=SYNTHETIC`, `QualityState.SYNTHETIC`.
10. **PROVISIONAL_RESEARCH.** `vertical_slice.RULE_STATUS`. The selection rule `PROVISIONAL_QG_PRESENT_EQUAL_WEIGHT` (all Q-and-G-present names, no return-fitted cutoff) is a research rule. Every output carries `official_selection=false`, `official_pass=false`, `full_pit_pass=false`, `calibrated=false`, `real_data_verified=false`. V is `PROVISIONAL_INITIAL_PRIOR` and excluded from `total_score`.
11. **Why not Official.** The Universe is Official (Track A), but the QGV result is not: no Track C validation (C7 unapproved; C8–C10 and real PIT validation not run), V not calibrated, `pit_integrity_report` gap `SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED`, Official profiles are owned by Track C.
12. **Track C dependency.** Official promotion, Official profiles and Investor-QGV belong to Track C. This producer assumes no C7–C10 result, reads no Holdout and applies no ProfileConfig.

## 2. Producer Infrastructure v1 (read-only) — what the QGV producer must fit

- PRODUCER_SNAPSHOT v1 (`producers/contract.py`). The QGV section is `ENTITY_MAP` built by `adapters.qgv_section(Iterable[QGVSnapshot])`, which serializes each existing `QGVSnapshot` verbatim (COMPATIBLE).
- `methodology.status ∈ RESEARCH_STATUSES` (includes `PROVISIONAL_RESEARCH`) cannot be `LIVE`/`FROZEN_SNAPSHOT` (`ResearchStatusError`). P01 (a Web research state) is PROPOSED, not approved. So QGV must publish `NOT_AVAILABLE`. The registry code is `QGV_RESEARCH_ONLY_NO_EXPORT`.
- Provenance inputs are `file:` / `raw:` ids with sha256, re-verified by `verify_inputs`.

## 3. Consequences for this work

- Persist the **existing** `QGVSnapshot` verbatim per company. Do not invent a new score model. Add only the QGV-specific lineage, PIT and sub-factor context the snapshot lacks.
- Do not create a second PRODUCER_SNAPSHOT/Bundle schema. Emit the arguments the Infrastructure needs and validate them with the Infrastructure's own code (pinned `5fa7ce0`) in CI.
- Export state stays **blocked** (`NOT_AVAILABLE`) until P01 is approved and Track C completes.
- Real runs happen on a GitHub runner from the pinned artifact. The runner checks each blob's sha256 against the committed `STORE_INDEX.json`, then compares with the Frozen aggregates and selection lists.
