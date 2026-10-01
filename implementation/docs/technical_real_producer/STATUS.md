# TECHNICAL_REAL_PRODUCER_V1 — status

Takeover file. Do not depend on the chat that wrote it.

| Item | Value |
|---|---|
| Branch | `feature/technical-real-producer-v1` |
| Code commit | `9ebf1799649a0142d7a59c41ba0db924bcb87845` |
| Base / canonical HEAD at start | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` (`claude/investment-system-top500-validation-alrugm`) |
| Not merged | canonical, PR #4 Track C, PR #5 Web, PR #6 search, PR #7 entity metadata, PR #9 producer infra |
| Engine | `technical/engine.py` byte-identical (`f7268f52…`). Fingerprint `28e910f3…` |
| Sample | 3 names (aapl, nvda, msft), decision `2024-12-31T23:59:59Z`, lookback 60 **caller** bars. Not Top-500 |

## Audit

See `AUDIT.md`. The approved design does not freeze an indicator set, a price-to-return map, or a regime rule. The code's only calculator is the v0.6 placeholder. Result-affecting gaps are `POLICY_BLOCKED` and were not implemented.

## Sample (LIVE_FETCH, payloads not committed)

Evidence: `evidence/sample_2024-12-31.json`, records: `evidence/company_records_2024-12-31.json`.

| Ticker | Input | Outputs | Future bars excluded | Window end |
|---|---|---|---|---|
| AAPL | PASS | NOT_AVAILABLE | 437 | 2024-12-31T14:30:00Z |
| NVDA | PASS | NOT_AVAILABLE | 437 | 2024-12-31T14:30:00Z |
| MSFT | PASS | NOT_AVAILABLE | 437 | 2024-12-31T14:30:00Z |

AAPL at `2024-06-30` hashes differently (`aa212f18…` vs `76ad2b62…`) and its last bar is `2024-06-28` (no forward fill). Source: Yahoo chart `5y`, stored only under a local `RawDatasetStore`. Offline replay of that store repeated the semantic hashes.

`synthetic=false` describes the **input bytes**, not a live model. `model_applied=false`.

## Tests

`tests/test_technical_real_producer.py` (16) plus full `tools/mini_pytest.py`: **412 passed / 0 failed**. Runner: mini_pytest shim, not pytest. No network in that run.

Covered: PIT pass, future input fail, missing provenance fail, missing lookback fail, null volume not filled, synthetic→LIVE fail, semantic hash stability, different as_of, company identity, demo output exact match, exporter does not call the engine, partial batch, offline store replay, no urllib in `technical/`, engine fingerprint, QGV/Macro/Portfolio/integration source hashes.

Workflow: `.github/workflows/technical-real-producer.yml` (offline full mini_pytest). Actions result is whatever that workflow reports after push; do not treat a local 412 as a GitHub Actions run until the check exists.

## Producer Infrastructure

Adapter output equals `not_available(section=technical, reason_code=TECHNICAL_NO_REAL_MODEL)` from PR #9 @ `6fe9eee`. Golden: `evidence/producer_not_available_golden.json`. `validate_snapshot` accepted that object in this session. The `producers/` package was not copied onto this branch.

## Readiness

| State | Verdict |
|---|---|
| TECHNICAL_REAL_INPUT_READY | YES for the PIT gate. Demonstrated on 3 LIVE_FETCH names only. Not a Top-500 claim |
| TECHNICAL_PER_COMPANY_SNAPSHOT_READY | YES for `TECHNICAL_COMPANY_RECORD` (lineage + explicit NOT_AVAILABLE outputs) |
| TECHNICAL_EXPORTER_READY | YES for fail-closed `NOT_AVAILABLE`. Not ready to export model fields |
| PRODUCER_INFRA_COMPATIBLE | YES via the adapter. PR #9 is not merged |
| REAL_TECHNICAL_RESEARCH_PRODUCER_READY | NO. No research score is produced. U-01 / price series / return transform are POLICY_BLOCKED |
| OFFICIAL_TECHNICAL_PRODUCER_READY | NO. No approved model. Track C C7–C10 not assumed. Holdout not used |

## Cross-track

No edits under `qgv/`, `macro/`, `portfolio` paths, `integration/`, `contracts/`, `providers/`, `validation/`, Track A evidence, or Track C. Source hashes in the new test lock those files.

## Next step

Do not add indicators or feed bars into `TechnicalEngine` until the owner freezes, in writing, the price field, the return transform, and the lookback as a model parameter. Until then the Web section stays `NOT_AVAILABLE`. Integration owner only merges this branch, and only after that policy exists if the goal is a published model. This branch's job stops at the input record and the fail-closed export.
