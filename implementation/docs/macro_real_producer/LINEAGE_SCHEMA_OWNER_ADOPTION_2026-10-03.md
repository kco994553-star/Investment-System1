# Lineage schema owner adoption — Macro owner adoption of Track C 2137883 (2026-10-03)

| Field | Value |
|---|---|
| Record | `MACRO_LINEAGE_SCHEMA_OWNER_ADOPTION_2026-10-03` |
| Kind | **Current** owner adoption record (history-preserving, additive). Not retroactive. Not a formula/value change. Not a canonical merge. Not a v0.1.4 promotion |
| Scope | Macro real producer (`feature/macro-real-producer-v1`, PR #12) |
| Authority | User decision CDR-004, 2026-10-03 (quoted verbatim in section 1) |
| Integration target | Track C commit `21378835883c5a9740143899c70d75d6405aa55a` ("fix(evl-upstream): derive PIT lineage and bind supported research controls"), as carried unchanged by the Track C owner tip `origin/ccr-22e3ff16-p7n5k5` @ `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565` at the time of this record (blobs of `contracts/lineage.py`, `contracts/models.py`, `macro/engine.py`, `technical/engine.py` verified identical by `git ls-tree`) |
| Canonical baseline | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca` (not moved) |
| Register item | **None exists for Macro.** Canonical C-28 (root `Investment-System1 · Contract Conflict Register 2026-09-23.md` L348-353) concerns the Technical output only. This record does not create a register item and does not edit the root register |
| Effective | Current owner adoption, **effective when merged into the owner branch `feature/macro-real-producer-v1`** by the owner or the user |
| Prepared by | Primary Integration Writer, Claude Code session `session_019znshzTYgyBnuuBmSxdPFN`, under user CDR-004 2026-10-03, on proposal branch `integration/a1-adoption/pr12-macro-producer` |
| Evidence | `evidence/c28_adoption_invariance_2026-10-03.json` (independent before/after comparison, verdict PASS, recorded before any pin was edited); `evidence/validation_post_adoption_2026-10-03.json` (additive post-adoption fingerprint record) |

## 0. Not retroactive

This is a current (2026-10-03) owner adoption. **No prior approval covered `MacroSnapshot` lineage fields, and no register item exists for Macro.** Nothing recorded before 2026-10-03 is reinterpreted by this record: the PR #12 STATUS/CONTRACT/AUDIT statements that "Track C `evaluate_stamped` is not on this branch" and "`macro/engine.py` byte-identical to the base" remain the correct description of the branch until the Track C tip is actually integrated, and they are not rewritten.

## 1. Authority (CDR-004, verbatim)

> IF-1은 A1 + Technical/Macro owner adoption으로 승인한다. Track C 2137883의 additive lineage/schema 변경을 integration target으로 유지한다. Technical은 canonical C-28의 upstream ownership과 정합시키고, Macro는 동일 변경에 대한 별도 additive owner adoption record를 작성한다. 이 승인은 기존 Technical/Macro 계산식, 값, regime, zone, Macro state, QGV, ranking을 변경하는 승인이 아니다. Producer owners는 새 schema를 대상으로 기존 numerical/semantic invariance를 다시 검증한 뒤 필요한 byte constants/fingerprints를 history-preserving 방식으로 repin한다. 단순히 테스트를 통과시키기 위해 pin을 변경하지 말고, 이전/이후 기존 필드 값과 계산 결과가 동일하다는 independent comparison을 먼저 PASS해야 한다. Track C Frozen chain은 rewrite하지 않는다. #10/#14 및 dependency-not-merged sentinel은 실제 integration context에 맞게 별도 compatibility repair 대상으로 처리한다. Macro의 이 adoption을 과거 승인으로 소급하지 말고 현재 owner adoption으로 기록한다. canonical merge는 아직 수행하지 않는다.

This record is the Macro side only ("Macro는 동일 변경에 대한 별도 additive owner adoption record를 작성한다"). The Technical side is the separate record under the Technical scope (`docs/technical_real_producer/C28_UPSTREAM_ADOPTION_2026-10-03.md` on its own proposal branch); it is not written here.

## 2. What is adopted

| Element | Content of 2137883 (unchanged at the Track C tip `b9e01a9`) |
|---|---|
| `contracts/models.py` (`5313bbd4…` → `fa386626…`) | Four optional fields appended to `MacroSnapshot` (and, in the same commit, to `TechnicalSnapshot`): `available_at: Optional[datetime] = None`, `data_stamp_refs: tuple[str, ...] = ()`, `source_vintages: tuple[tuple[str, str], ...] = ()`, `input_hash: Optional[str] = None`. Source comment: "None/empty on legacy unqualified outputs; never inferred from as_of" |
| `macro/engine.py` (`c593a2ef…` → `a0a7c983…`, +10 lines, no line removed or modified) | `MacroEngine.evaluate_stamped(as_of, indicators: dict[str, StampedValue], synthetic=False)`: requires **exactly** `{"growth", "inflation"}` as the indicator keys (`ValueError("strict Macro evaluation requires growth and inflation")` otherwise), computes `derived_lineage(indicators, as_of, synthetic=synthetic)`, calls the existing `evaluate()` on the raw values, and returns `dataclasses.replace(output, **lineage)`. Two imports are added (`dataclasses.replace`; `StampedValue, derived_lineage`) |
| `contracts/lineage.py` (new, sha256 `ddfac6ef9bac1eb3a54a60bfbd78218d8f0aa57b91185ffadaaa5458aeb9c454`) | `StampedValue` and `derived_lineage(...)`: lineage is derived from input data stamps (`available_at = max(stamp.available_at)`, sorted `data_stamp_refs`, sorted `source_vintages`, `input_hash` over the stamped payload); never from `as_of`. Dependency of the stamped path only |

The adoption is of the schema shape and the stamped entry point. It is not an approval of any Macro calculation, threshold, indicator, regime rule, exposure coefficient or Web mapping.

## 3. What is unchanged (verified on throwaway trees, not assumed)

- `MacroEngine.evaluate()` body: byte-identical (the diff canonical → Track C tip on `macro/engine.py` is purely additive).
- v0.1.1 state rules as already documented in `CONTRACT.md` (inflation > 0.08 → EMERGENCY / INFLATION_SHOCK; inflation > 0.05 and growth < 0 → WARNING / STAGFLATION_RISK; growth > 0.03 and inflation < 0.03 → NORMAL / EXPANSION; otherwise NORMAL / NEUTRAL): no rule, threshold or default touched by 2137883 or by this record. `MACRO_CONFIRMED` stays `v0.1.1`; `environment.candidate_not_applied` stays `v0.1.4-CANDIDATE`.
- State/regime values for this PR's own fixtures, before and after: decision 2024-12-31 → `EXPANSION` / `NORMAL`, inflation `0.020000000000000018`; decision 2025-03-15 (sees the revision) → `INFLATION_SHOCK` / `EMERGENCY`, inflation `0.10000000000000009`; replay of 2024-12-31 after the revision → `EXPANSION` / `NORMAL`; direct engine `neutral` / `shock` / `stag` / `expansion` dicts identical.
- `macro_snapshot_id` identical (`mac_560ba7bdee89`, `mac_35acb549cbc8`): the id is the canonical hash of the identity dict (`as_of`, `indicators`, `state`, `regime`, `macro_version`, `artifacts`), which does not serialize the `MacroSnapshot`.
- `PRODUCER_SNAPSHOT` v1 (`not_available(...)`, `reason_code=POLICY_BLOCKED`, `methodology.status=PROVISIONAL`, `data=null`): identical; canonical sha256 identical for every case. `assemble_bundle` output and `bundle_sha256` (`c1a8eb0bec09cea27527fd19fe1834f7cfe3f4d38c1969094557bc5c59441822`) identical. `adapters.macro_section` still raises `IncompatibleShapeError`.
- No exposure coefficient: `company_industry_exposure(...)` still raises `PolicyBlocked` with the identical message; `PUBLICATION` and the four `PUBLICATION_REASONS` identical. Fail-closed paths (`FutureReleaseError`, `MacroInputError`, `SyntheticLiveError`, `RevisedHistoryError`, `MacroProvenanceError`) identical.
- The committed evidence sample (`evidence/validation.json` → `sample`) reproduces identically before and after.
- The research `MacroSnapshot.to_dict()` of this producer keeps every pre-existing field value; the **only** difference after adoption is the four added keys with legacy values: `available_at=null`, `data_stamp_refs=[]`, `source_vintages=[]`, `input_hash=null` (140 added keys over 35 serialized snapshots in the comparison; 0 other differences).

## 4. Stamped path vs legacy path (factual)

- This producer calls the legacy `MacroEngine.evaluate()` (`real_producer.py` line 252). After adoption its research `MacroSnapshot` therefore carries the four fields with legacy values (`None` / `()` / `()` / `None`); its point-in-time lineage continues to live in `environment.pit.series` (`artifact_id`, `sha256`, `source`, `available_at`, `vintage_at`, `release_at`, `ingested_at`) and in `MacroProducerResult.provenance`.
- Whether this producer should later route through `evaluate_stamped` (which would populate the four fields from the selected vintages, without changing any state/regime value) is a separate owner item. It is **not decided** by this record and no such source change is made here.
- The only caller of `MacroEngine.evaluate_stamped` in the integrated tree is Track C's `evl/bindings.py`.

## 5. Committed semantic hashes that change post-adoption (additive record, nothing overwritten)

`tools/producer_engine_fingerprint.py` hashes `dataclasses.asdict()` of the engine outputs (random ids and wall-clock fields excluded). Because `MacroSnapshot` and `TechnicalSnapshot` gain four keys, two of the five committed sections change once the Track C tip is integrated:

| Section | Pre-adoption (committed 2026-10-01 in `STATUS.md` and `evidence/validation.json`, reproduced on the BEFORE tree) | Post-adoption (AFTER tree = PR tip + Track C tip `b9e01a9`) | Why |
|---|---|---|---|
| macro | `7bbfad69ac46b5886fb30f32b871ce68983adbc089d7ea21ae3b6317d108732f` | `7e427949a4c15ebaf78304cfec2d7a952f8bfec2a694371801ad90d09fe0c501` | 4 dicts × 4 added keys with legacy values; every pre-existing key identical |
| technical | `82165414a2c86c5c489b7c071c44b967c344dd654238af445714bb0fe14097c7` | `66cb23830d65d1867df895a52d6cf3adef52c84a8ee2645d2c06617711a5e655` | 19 dicts × 4 added keys with legacy values; every pre-existing key identical |
| qgv, leaderboard, portfolio_official_book | unchanged | unchanged | not a `MacroSnapshot` / `TechnicalSnapshot` |

The pre-adoption values in `STATUS.md` and `evidence/validation.json` are **not overwritten**. The post-adoption values are recorded additively in `evidence/validation_post_adoption_2026-10-03.json` and in the additive STATUS note. No committed hash of this PR other than these two fingerprint sections covers a `MacroSnapshot` serialization (`macro_snapshot_id`, the producer snapshot, the bundle hash and the evidence sample are unchanged, see section 3).

Observation outside this scope (not touched): `docs/producer_infrastructure/evidence/validation.json` (PR #9) carries the same pre-adoption `macro` / `technical` fingerprint values; that is the #9 owner's item.

## 6. Pins: history-preserving, state-exact

`tests/test_macro_real_producer.py` keeps the pre-adoption constants and adds the adopted constants. The expected value is selected from the adopted feature itself (`hasattr(MacroEngine, "evaluate_stamped")`, `hasattr(TechnicalEngine, "evaluate_stamped")`, and the four field names on `MacroSnapshot` and `TechnicalSnapshot`), never from bytes; a partially adopted tree selects the sentinel `C28_ADOPTION_STATE_INCONSISTENT`, which no file hashes to, and fails; an adopted tree whose bytes differ from the adopted digest fails. Nothing is loosened to "either value accepted"; no key is stripped from any fingerprint (option A2 is not approved).

| Pin (`_ENGINE_HASHES`) | Pre-adoption (2026-10-01, PR #12 @ 38e3dff, canonical b8e39a2 bytes) | Adopted (C-28 upstream adoption of Track C 2137883 per user CDR-004 2026-10-03) |
|---|---|---|
| `src/investment_system/macro/engine.py` | `c593a2ef3b1be06960dde46ccc34db9f1858d1357336614ccf15bbb57ccec80b` | `a0a7c983bebd098aeb8bed81095d849c5bec2dbfd18233408b6ba8929573ee10` |
| `src/investment_system/technical/engine.py` | `f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf` | `86607bf7004804b923f50cda1db7dbffaf4dd782002a7e0f56ca3c95be625c2c` |
| `qgv/analysis.py`, `qgv/portfolio.py`, `qgv/leaderboard.py` | unchanged | unchanged |

Order of operations: the independent comparison (section 3, evidence JSON) was recorded on throwaway trees first; the pins were edited afterwards.

## 7. Not changed by this record

- No source change under `implementation/src`. The adopted bytes arrive by integrating the Track C tip, not by this proposal.
- Dependency-not-merged sentinels and the CI-mode `models.py` compare in #10/#14: not touched (separate compatibility-repair items per CDR-004).
- Track C Frozen chain: not rewritten. Canonical: not merged. Holdout / CAL_VERIFY: not accessed. No live FRED request.
- Existing STATUS / AUDIT / CONTRACT / `evidence/validation.json` of this scope: not rewritten; additive notes point here.
- v0.1.4 candidate, exposure coefficients, Web `indicators` mapping, `CURRENT_REVISED_NOT_ALFRED`: still unresolved / POLICY_BLOCKED exactly as before.

## 8. State

`BRANCH_STATE`: proposal branch `integration/a1-adoption/pr12-macro-producer` from PR #12 tip `61d3352d5d68c7830e924f17613598ca79fcec6f`. `INTEGRATION_STATE`: trial-merged with the Track C tip `b9e01a9` on a throwaway tree (`84cd6b5`), 0 conflicts; not merged into the owner branch. `CANONICAL_STATE`: NOT_MERGED.
