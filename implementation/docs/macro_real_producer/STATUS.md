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
