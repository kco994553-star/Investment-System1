# PRODUCER_INFRASTRUCTURE_V1 — Status / Handoff

Recorded: 2026-10-01 (UTC). Use this file to take over from GitHub alone; no chat history is needed.

| Item | Value |
|---|---|
| Branch | `feature/producer-infrastructure-v1` (new; not merged anywhere) |
| Base | `feature/global-language-search-v1@eda65bf` (PR #6, stacked on PR #5 `a4e49c8`; canonical `b8e39a2`) |
| Why this base | The Web schema-1 contract (`product/web_mvp.py`) exists only on PR #5/#6. The exporter must validate against it |
| Validated code commit | `bcfdcd2` (code/tests/tools/raw-persistence report). Later commits on this branch are docs/evidence only |
| Preceding audit | `ccr-e0fc1e48-9tcto3@f415615`: `implementation/reports/producer_readiness_audit_2026-10-01.{md,json}` (preserved, not rewritten) |
| Merge order if accepted | canonical ← PR #5 ← PR #6 ← this branch. Integration owner only |

## Delivered
- `producers/` package:
  - `contract`: PRODUCER_SNAPSHOT v1 + typed fail-closed validation + source re-hash
  - `freshness`: FRESH / STALE / NOT_USABLE / NOT_APPLICABLE
  - `serialization`: canonical JSON and sha256
  - `registry`: Producer interface, frozen Universe, explicit NOT_AVAILABLE producers
  - `adapters`: verbatim upstream adapters plus a compatibility table
  - `assembler`: deterministic schema-1 bundle with atomic write
  - `raw_persistence`: dataset manifest and retention audit
- `tools/export_web_bundle.py`: producer snapshots → validated bundle (→ optional static Web build)
- `tools/raw_persistence_audit.py` → `reports/raw_persistence/raw_dataset_manifest_2026-10-01.json`
- `tools/producer_engine_fingerprint.py`: numerical invariance check for QGV/Technical/Macro/Leaderboard/Portfolio
- `product/web_mvp.py`: a LIVE section without `expires_at`, or a missing section, now raises `ValueError` instead of a raw `KeyError`. The accept/reject set is unchanged
- Docs: `CONTRACT.md`, `PROPOSAL_P01_RESEARCH_DATA_STATE.md`, `PROPOSAL_P02_UNIVERSE_INTERIM_POLICY.md`, `RAW_PERSISTENCE_OPTIONS.md`, `evidence/validation.json`

## Verification (details in evidence/validation.json)
- New tests: 22 passed.
- Full branch suite: 431 passed with pytest and 431 passed / 0 failed with the mini_pytest shim.
- Trial merge with Track C `15fed50` (local `commit-tree` only, nothing pushed):
  - no conflict;
  - full suite 664 passed.
- Trial merge with `ccr-41677301-10nj3u` (search metadata): no conflict.
- Web browser regression, local Chromium, on a bundle built by the new exporter:
  - Web MVP 10/10, no page errors;
  - Language & Search 8/8, Node 26/26.
- Engine fingerprints (fixtures; random ids excluded) are identical to the base and repeatable. QGV, Technical, Macro, Leaderboard and Portfolio numbers are unchanged.
- Default export is byte-identical on rerun. Its semantics equal the existing `repository_bundle()`.
- Cross-track: 0 changed files in qgv/technical/macro/universe/personal/rig/prompt_library/ingestion/validation/contracts/providers, Track A gate evidence, data/raw and Track C.

## Verdicts
| Status | Verdict |
|---|---|
| PRODUCER_INFRASTRUCTURE_IMPLEMENTED | **YES** |
| WEB_BUNDLE_EXPORTER_READY | **YES** for the contract. It currently exports Universe FROZEN_SNAPSHOT plus explicit NOT_AVAILABLE |
| RAW_ARTIFACT_PERSISTENCE_DESIGNED | **YES**. Not yet durable: AT_RISK, loss deadline 2026-12-26T08:21:15Z |
| REAL_PRODUCER_READY | **NO**. No section has a real, publishable, non-synthetic producer |
| DAILY_OPERATION_READY | **NO**. No producer, no schedule, no Universe interim policy, no hosting |

## Open decisions (BLOCKED; not implemented)
- **P01**: Web state for research/provisional outputs (QGV PROVISIONAL_RESEARCH). Until decided, the QGV section stays NOT_AVAILABLE.
- **P02 (D3-P)**: Universe between Official dates (carry-forward / quarterly / daily reconstruction / interpolation / staleness limit).
- **P03**: Durable raw storage location, the public-redistribution question, and an optional refresh stopgap. **Time-bound: 2026-12-26.**
  The detailed comparison is in `P03_RAW_STORAGE_COMPARISON.md`. The read-only restore check (run 36850391139) PASSED 6808/6808.
  Recommended: private GitHub repo Release (primary), a user-held copy, and optionally R2/B2. Never place third-party (Yahoo/Tiingo/Stooq) payloads in public locations.
- Macro Web shape mapping and exposure producer (owner decision). The adapter raises `IncompatibleShapeError` today.
- Technical real model (owner); Track B P1+ holdings; news/consensus provider; hosting provider.
- Track C C7–C10 / Official profiles / Investor-QGV (FUTURE_TRACK_C_INPUT). No Track C result is assumed and Holdout is never read.

## How a real producer connects later (no code change needed in the assembler)
1. Emit a PRODUCER_SNAPSHOT v1 JSON with real `provenance.inputs` hashes (`file:` or `raw:` ids), `validation.status=PASS`, a tz-aware `as_of`/`generated_at`, and a producer-chosen `expires_at` (plus `usable_until` if wanted).
2. `python tools/export_web_bundle.py --now <tz ISO> --snapshot <file> [--raw-store data/raw] --out bundle.json --build-web <dir>`.
3. The section is rejected if any of these hold:
   - it is synthetic but labelled LIVE;
   - its status is research;
   - its hashes don't verify;
   - the Web cannot represent its shape.

Required secrets/APIs for this infrastructure: **none**. Existing data runners still use `SEC_USER_AGENT` (required) and `TIINGO_API_KEY` (optional).
