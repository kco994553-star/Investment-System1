# MACRO_REAL_PRODUCER_V1 — Status

Recorded: 2026-10-01 (KST).

| Item | Value |
|---|---|
| Branch | `feature/macro-real-producer-v1` |
| Base | `feature/producer-infrastructure-v1` @ `6fe9eee` (PR #9, read-only) |
| Canonical | `b8e39a2` fetched, not merged |
| Other agents | Not modified: `feature/track-c-evl`, PR #5, PR #6, PR #7 |
| Engine | `macro/engine.py` byte-identical to the base |

## What landed

- `macro/real_producer.py`: PIT vintage selection, existing ALFRED collector, existing v0.1.1 engine, deterministic research `MacroSnapshot`, fail-closed `PRODUCER_SNAPSHOT` v1.
- Exposure entry point that raises `PolicyBlocked` and returns no number.
- Tests and this audit / contract / evidence. No producer-infrastructure file is edited, so the default Web export stays the PR #9 export.

## Verification

Runner: `python3 tools/mini_pytest.py` (shim, not pytest; this sandbox has no pytest wheel).

| Run | Result |
|---|---|
| `tests/test_macro_real_producer.py` | 11 passed, 0 failed |
| Full suite on this branch | 442 passed, 0 failed in 22.10s |

The 11 new tests cover a valid PIT input, future-release rejection, revised vintage not rewriting the earlier decision, missing provenance, deterministic snapshot, methodology preservation, synthetic and `CURRENT_REVISED_NOT_ALFRED` rejection, no silent NEUTRAL on a missing pillar, exposure policy block, Producer Infrastructure plus Web fail-closed assembly, and unchanged bytes for the Macro engine, QGV analysis, Technical engine, Portfolio, and Leaderboard.

Engine fingerprint (`tools/producer_engine_fingerprint.py src`), random ids excluded:

| Section | sha256 |
|---|---|
| qgv | `a17144803746000dc11efa630797fccbf76d2985e58ca7ae55797e7842d7ce3e` |
| technical | `82165414a2c86c5c489b7c071c44b967c344dd654238af445714bb0fe14097c7` |
| macro | `7bbfad69ac46b5886fb30f32b871ce68983adbc089d7ea21ae3b6317d108732f` |
| leaderboard | `112b245b4f9963787ab7b2780f287e99515f05c231bfc127f656a57736e9b4c1` |
| portfolio_official_book | `53d930a7e3d2009347ac36f84e8a3b7504e6e5e9b0a4fe62fa5d1fb1be5a4a68` |

No live FRED request was made. `real_data_verified` remains false.

## Verdicts

| Status | Verdict |
|---|---|
| MACRO_REAL_INPUT_READY | **YES** for caller-supplied ALFRED vintages with `available_at` and a matching canonical sha256. **NO** live key check and **NO** REAL-DATA VERIFIED claim |
| MACRO_SNAPSHOT_READY | **YES** for the research `MacroSnapshot` only (deterministic, v0.1.1, PIT-selected). Not a Web payload |
| MACRO_EXPOSURE_READY | **NO** — POLICY_BLOCKED. No approved coefficient |
| MACRO_EXPORTER_READY | **YES** for a fail-closed `NOT_AVAILABLE` snapshot the existing exporter accepts. **NO** for publishing macro numbers to the Web |
| PRODUCER_INFRA_COMPATIBLE | **YES**. Existing `validate_snapshot` / `assemble_bundle`. No schema added. PR #9 files untouched |
| REAL_MACRO_RESEARCH_PRODUCER_READY | **YES** inside the boundary above. Not Official and not Web-LIVE |
| OFFICIAL_MACRO_PRODUCER_READY | **NO**. Track C has not validated this producer. Series map is provisional. Exposure is unapproved. Forward validation has not run |

Official promotion stays blocked until Track C (and any other required validation) is actually run against this boundary.

## Remote reconfirm (2026-10-01, after fetch)

| Check | Result |
|---|---|
| PR | [#12](https://github.com/kco994553-star/Investment-System1/pull/12) `draft=true`, `state=open`, `merged=false`, `mergeable_state=clean` |
| Head | `feature/macro-real-producer-v1`. Code under test `38e3dff`. This lock is docs-only on top of that commit |
| Base | `feature/producer-infrastructure-v1` @ `6fe9eee5668388fa4a200904520a0b5a46c90b6f` |
| Merge-base | `6fe9eee` (code commit is 1 ahead of the base; the following commit is documentation only) |
| Diff | 6 files, all additions. No edits under `qgv/`, `technical/`, `portfolio`, `leaderboard`, `rig/`, `prompt_library/`, `validation/`, `universe/`, `evl/`, `providers/`, `producers/`, `contracts/`, or `macro/engine.py` |
| Not incorporated | Track C moved to `88f66c5`. `feature/technical-real-producer-v1` exists at `a2e0790`. Neither is merged here |
| CI | Combined status `pending`, `total_count=0`, `check_runs=0`. Not a pass. `c21-real-data` is `workflow_dispatch` only. `raw-artifact-restore-check` pushes only on `feature/producer-infrastructure-v1` and its own paths. `web-mvp-validation` does not match this diff |

Re-run on this tree, same shim: targeted 11 passed / 0 failed; full suite 442 passed / 0 failed in 23.51s. Fingerprints above are unchanged.

## Unresolved scope (do not implement on this baseline)

| Item | Label |
|---|---|
| v0.1.4 scenario / transmission / stress | DESIGNED_NOT_IMPLEMENTED |
| Company / industry exposure coefficients | POLICY_BLOCKED |
| Web `indicators` mapping (`environment.indicators` → `data.indicators`) | POLICY_BLOCKED |
| `CURRENT_REVISED_NOT_ALFRED` as a decision input | POLICY_BLOCKED (`RevisedHistoryError`) |

## Locked verdict grounds

REAL_MACRO_RESEARCH_PRODUCER_READY = **YES**

- Input is an `ALFRED_AS_OF` vintage with `artifact_id`, `source`, and a canonical `sha256`.
- A vintage with `available_at` after `decision_time` is not used. Replaying the earlier decision after a later revision still selects the earlier vintage.
- Synthetic input and `CURRENT_REVISED_NOT_ALFRED` raise before the engine runs.
- Missing growth or inflation does not fall through to the engine's 0.0 default.
- Output is a deterministic v0.1.1 `MacroSnapshot` (`mutated_qgv=false`, `real_data_verified=false`). The Web section is `NOT_AVAILABLE`.

OFFICIAL_MACRO_PRODUCER_READY = **NO**

- Track C `evaluate_stamped` is not on this branch and has not validated this producer.
- Series mapping remains provisional. Exposure coefficients do not exist. Web indicators are not mapped.
- No live FRED fetch, no forward validation, no REAL-DATA VERIFIED flag.
- GitHub reported no check runs for `38e3dff`. Absence of CI is not a green result.

## Disposition

MACRO REAL PRODUCER IMPLEMENTATION BASELINE / INTEGRATION WAIT

Defined scope is closed. Do not merge PR #12. Integration waits for the owner. This branch does not take Track C, Technical REAL Producer, Web, or Entity Metadata work.


## Lineage schema owner adoption — additive note (2026-10-03)

Owner adoption record: `LINEAGE_SCHEMA_OWNER_ADOPTION_2026-10-03.md` — a **current** (not retroactive) Macro owner adoption of Track C `2137883`'s additive lineage/schema change (four optional fields `available_at` / `data_stamp_refs` / `source_vintages` / `input_hash` on `MacroSnapshot`, plus `MacroEngine.evaluate_stamped` requiring exactly growth + inflation), per user CDR-004 2026-10-03. No prior approval covered `MacroSnapshot` lineage fields and no register item exists for Macro. Independent before/after invariance comparison, recorded before any pin edit: `evidence/c28_adoption_invariance_2026-10-03.json` (PASS; every pre-existing field value, `macro_snapshot_id`, producer snapshot, bundle hash and evidence sample identical; the only differences are the four added keys with legacy values). `tests/test_macro_real_producer.py` now carries both the pre-adoption pins (`c593a2ef…`, `f7268f52…`) and the adopted pins (`a0a7c983…`, `86607bf7…`), selected state-exactly from the adopted feature itself; nothing is loosened. The "Engine" row and the "Track C `evaluate_stamped` is not on this branch" statement above stay the correct description of this branch until the Track C tip is integrated and are not rewritten. No formula, value, regime or Macro state changed; no source under `implementation/src` changed. Prepared by the Primary Integration Writer; becomes the owner's adoption when merged into `feature/macro-real-producer-v1`. `CANONICAL_STATE`: NOT_MERGED.

### Post-adoption engine fingerprint (additive record; the 2026-10-01 table above is the pre-adoption record and is not overwritten)

`tools/producer_engine_fingerprint.py` hashes `asdict()` of the engine outputs, so the `macro` and `technical` sections change once the four lineage keys exist. Measured on a throwaway tree = this PR tip `61d3352` + Track C tip `b9e01a9` (0 conflicts); every pre-existing key in the normalized dicts is identical. Detail: `evidence/validation_post_adoption_2026-10-03.json`.

| Section | Pre-adoption (2026-10-01) | Post-adoption (Track C 2137883 integrated) |
|---|---|---|
| qgv | `a17144803746000dc11efa630797fccbf76d2985e58ca7ae55797e7842d7ce3e` | unchanged |
| technical | `82165414a2c86c5c489b7c071c44b967c344dd654238af445714bb0fe14097c7` | `66cb23830d65d1867df895a52d6cf3adef52c84a8ee2645d2c06617711a5e655` |
| macro | `7bbfad69ac46b5886fb30f32b871ce68983adbc089d7ea21ae3b6317d108732f` | `7e427949a4c15ebaf78304cfec2d7a952f8bfec2a694371801ad90d09fe0c501` |
| leaderboard | `112b245b4f9963787ab7b2780f287e99515f05c231bfc127f656a57736e9b4c1` | unchanged |
| portfolio_official_book | `53d930a7e3d2009347ac36f84e8a3b7504e6e5e9b0a4fe62fa5d1fb1be5a4a68` | unchanged |

Reason: C-28 upstream adoption of Track C 2137883 per user CDR-004 2026-10-03 (schema keys added with legacy values; no computed value changed). `macro_snapshot_id` (`mac_560ba7bdee89`, `mac_35acb549cbc8`), the `PRODUCER_SNAPSHOT` v1 and its canonical hash, `bundle_sha256` and the evidence `sample` do not change.
