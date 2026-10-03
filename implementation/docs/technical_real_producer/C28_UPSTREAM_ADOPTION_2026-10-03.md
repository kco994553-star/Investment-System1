# C-28 upstream adoption — Technical owner adoption of Track C 2137883 (2026-10-03)

| Field | Value |
|---|---|
| Record | `TECHNICAL_C28_UPSTREAM_ADOPTION_2026-10-03` |
| Kind | Current owner adoption record (history-preserving, additive). Not a retroactive approval, not a formula/value change, not a canonical merge |
| Scope | Technical real producer (`feature/technical-real-producer-v1`, PR #11) |
| Authority | User decision CDR-004, 2026-10-03 (quoted verbatim in section 1) |
| Integration target | Track C commit `21378835883c5a9740143899c70d75d6405aa55a` ("fix(evl-upstream): derive PIT lineage and bind supported research controls"), as carried unchanged by the Track C owner tip `origin/ccr-22e3ff16-p7n5k5` @ `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565` at the time of this record (blobs verified identical by `git ls-tree`) |
| Canonical baseline | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca` (not moved) |
| Canonical register item | C-28, root `Investment-System1 · Contract Conflict Register 2026-09-23.md` L348-353 (quoted in section 2). The root register is not edited by this record |
| Effective | Current owner adoption, effective when merged into the owner branch `feature/technical-real-producer-v1` by the owner or the user |
| Prepared by | Primary Integration Writer, Claude Code session `session_019znshzTYgyBnuuBmSxdPFN`, under user CDR-004 2026-10-03, on proposal branch `integration/a1-adoption/pr11-technical-producer` |
| Evidence | `evidence/c28_adoption_invariance_2026-10-03.json` (independent before/after comparison, verdict PASS, recorded before any pin was edited) |

## 1. Authority (CDR-004, verbatim)

> IF-1은 A1 + Technical/Macro owner adoption으로 승인한다. Track C 2137883의 additive lineage/schema 변경을 integration target으로 유지한다. Technical은 canonical C-28의 upstream ownership과 정합시키고, Macro는 동일 변경에 대한 별도 additive owner adoption record를 작성한다. 이 승인은 기존 Technical/Macro 계산식, 값, regime, zone, Macro state, QGV, ranking을 변경하는 승인이 아니다. Producer owners는 새 schema를 대상으로 기존 numerical/semantic invariance를 다시 검증한 뒤 필요한 byte constants/fingerprints를 history-preserving 방식으로 repin한다. 단순히 테스트를 통과시키기 위해 pin을 변경하지 말고, 이전/이후 기존 필드 값과 계산 결과가 동일하다는 independent comparison을 먼저 PASS해야 한다. Track C Frozen chain은 rewrite하지 않는다. #10/#14 및 dependency-not-merged sentinel은 실제 integration context에 맞게 별도 compatibility repair 대상으로 처리한다. Macro의 이 adoption을 과거 승인으로 소급하지 말고 현재 owner adoption으로 기록한다. canonical merge는 아직 수행하지 않는다.

This record is the Technical side only. The Macro side is a separate additive owner adoption record under the Macro scope; it is not written here.

## 2. What is adopted

Canonical C-28 (register L348-353): "Technical output has no available_at → OPEN-BLOCKING for PIL P4 only … Decision: PIL must not create times. Fix belongs to the Technical system (upstream PATCH: add available_at from input data stamps)".

The Technical owner adopts Track C 2137883's additive change as the shape of that upstream patch:

| Element | Content of 2137883 (unchanged at the Track C tip) |
|---|---|
| `contracts/lineage.py` (new, sha256 `ddfac6ef9bac1eb3a54a60bfbd78218d8f0aa57b91185ffadaaa5458aeb9c454`) | `StampedValue` and `derived_lineage(...)`: lineage is derived from input data stamps; never from `as_of` |
| `contracts/models.py` (`5313bbd4…` → `fa386626…`) | Four optional fields appended to `TechnicalSnapshot` and to `MacroSnapshot`: `available_at: Optional[datetime] = None`, `data_stamp_refs: tuple[str, ...] = ()`, `source_vintages: tuple[tuple[str, str], ...] = ()`, `input_hash: Optional[str] = None`. Comment in source: "None/empty on legacy unqualified outputs; never inferred from as_of" |
| `technical/engine.py` (`f7268f52…` → `86607bf7…`, +16 lines, no line removed or modified) | `TechnicalEngine.evaluate_stamped(company_id, as_of, returns: tuple[StampedValue, ...], qgv=None, synthetic=False)`: validates unique chronological stamps, computes `derived_lineage`, calls the existing `evaluate()` on the raw values, and returns `dataclasses.replace(output, **lineage)` |
| `macro/engine.py` (`c593a2ef…` → `a0a7c983…`, +10 lines, no line removed or modified) | `MacroEngine.evaluate_stamped(as_of, indicators: dict[str, StampedValue], synthetic=False)` with the same pattern |

The adoption is of the schema shape and the stamped entry point. It is not an approval of any Technical calculation.

## 3. What is unchanged (verified, not assumed)

- `TechnicalEngine.evaluate()` and `MacroEngine.evaluate()` bodies: byte-identical (the diff canonical → Track C tip on both files is purely additive: two imports and one new method each).
- For every legacy `evaluate()` output used by this PR's fingerprint (six fixed return series, `as_of = 2026-09-14T00:00:00Z`, `synthetic=True`): `regime`, `execution_zone`, `invalidation`, `scenarios`, `drawdown_recheck`, `qgv_snapshot_id_ref`, `mutated_qgv`, `synthetic`, `technical_version`, `implementation_kind`, `company_id`, `as_of` — all identical before and after. The only difference in the normalized `asdict()` dicts is the four added keys `available_at=null`, `data_stamp_refs=[]`, `source_vintages=[]`, `input_hash=null` (24 additions over six dicts; 4 more on the one `MacroEngine.evaluate()` dict compared).
- `produce_company` fixture records (default, volume hole, later decision, later `generated_at`), `produce_batch` partial batch, `produce_demo` output, `export_producer_snapshot` output (equal to the committed golden before and after), `semantic_hash` recomputation of the three committed `company_records_2024-12-31.json` records (3/3 match before and after): zero field differences.
- No formula, threshold, default, regime rule, zone rule, Macro state rule, QGV scoring or ranking is touched by 2137883 or by this record.
- Committed evidence hashes of this PR are unchanged under the adopted tree; no post-adoption evidence record was needed for them.

## 4. Stamped path vs legacy path (factual)

- The stamped path (`evaluate_stamped`) propagates `available_at`, `data_stamp_refs`, `source_vintages`, `input_hash` from the input stamps via `derived_lineage`. The legacy path (`evaluate`) leaves them `None` / empty.
- No real-data Technical producer has used the stamped path yet. On this branch, `produce_demo` calls legacy `evaluate()` (DEMO, `synthetic=True`); `produce_company` does not call the engine at all (`technical_outputs.status = NOT_AVAILABLE`, `model_applied=false`), and its record-level `available_at` comes from the input bars, not from `TechnicalSnapshot`. The only caller of `evaluate_stamped` in the integrated tree is Track C's `evl/bindings.py`.
- Consequently, C-28's OPEN-BLOCKING status is for the register owner to update; this record states the facts and does not edit the root register.

## 5. Pins: history-preserving, state-exact

`tests/test_technical_real_producer.py` keeps the pre-adoption constants and adds the adopted constants. The expected value is selected from the adopted feature itself (`hasattr(TechnicalEngine, "evaluate_stamped")`, `hasattr(MacroEngine, "evaluate_stamped")`, and the four field names on both snapshots), never from bytes; a partially adopted tree selects a digest no file has and fails. Nothing is loosened to "either value accepted", `norm()` is unchanged, and no key is stripped from the fingerprint (option A2 is not approved).

| Pin | Pre-adoption (2026-10-01, PR #11 @ 9ebf179, canonical b8e39a2 bytes) | Adopted (C-28 upstream adoption of Track C 2137883 per user CDR-004 2026-10-03) |
|---|---|---|
| `ENGINE_FINGERPRINT` | `28e910f3005c74888aa33e9b6f45b8d94fc70d4f023e1bc49a6af4100ea9ede6` | `0b26c7d1a199b270568e65cb4dc9c41cca4160e8a0ed7494244266a54e8d1a4a` |
| `SOURCE_SHA256["src/investment_system/technical/engine.py"]` | `f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf` | `86607bf7004804b923f50cda1db7dbffaf4dd782002a7e0f56ca3c95be625c2c` |
| `SOURCE_SHA256["src/investment_system/macro/engine.py"]` | `c593a2ef3b1be06960dde46ccc34db9f1858d1357336614ccf15bbb57ccec80b` | `a0a7c983bebd098aeb8bed81095d849c5bec2dbfd18233408b6ba8929573ee10` |
| `qgv/scoring.py`, `qgv/leaderboard.py`, `qgv/portfolio.py`, `integration/engine.py` pins | unchanged | unchanged |

Order of operations: the independent comparison (section 3, evidence JSON) was recorded on throwaway trees first; the pins were edited afterwards.

## 6. Not changed by this record

- No source change under `implementation/src`. The adopted bytes arrive by integrating the Track C tip, not by this proposal.
- Dependency-not-merged sentinels and the CI-mode `models.py` compare in #10/#14: not touched (separate compatibility-repair items per CDR-004).
- Track C Frozen chain: not rewritten. Canonical: not merged. Holdout / CAL_VERIFY: not accessed.
- Existing STATUS/AUDIT/CONTRACT text of this scope: not rewritten; an additive note points here.

## 7. State

`BRANCH_STATE`: proposal branch `integration/a1-adoption/pr11-technical-producer` from PR #11 tip `a2e0790dd7fb267ebaa7d052acae59220ecf631e`. `INTEGRATION_STATE`: trial-merged with the Track C tip `b9e01a9` on a throwaway tree, 0 conflicts; not merged into the owner branch. `CANONICAL_STATE`: NOT_MERGED.
