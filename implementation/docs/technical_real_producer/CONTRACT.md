# TECHNICAL_REAL_PRODUCER_V1 — contract

Branch: `feature/technical-real-producer-v1`. Base: canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.

Does not merge PR #4, #5, #6, #7, or #9. Does not replace `TechnicalEngine.evaluate`.

## Paths

| Path | When | Engine | synthetic | Web state |
|---|---|---|---|---|
| `REAL_INPUT` | `evidence_class=LIVE_FETCH`, provenance hash matches, synthetic false | not called | false on the **input** record | `NOT_AVAILABLE` |
| `FIXTURE` | structural bytes, synthetic true | not called | true | `NOT_AVAILABLE` |
| `DEMO` | caller-supplied `returns` | `TechnicalEngine.evaluate(..., synthetic=True)` unchanged | true | not exported |

`LIVE_FETCH` plus `synthetic=true` raises `SYNTHETIC_LIVE`. Export `data_state=LIVE` raises `SYNTHETIC_LIVE`. Any other publish state raises `PUBLICATION_BLOCKED`.

## PIT input

For every bar that enters the window:

- `observed_at <= decision_time`
- `volume_observed_at <= decision_time` (Yahoo daily quote uses the bar timestamp)
- `available_at <= decision_time` (`available_at = observed_at`, existing Yahoo stamp)
- `close` and `volume` are present. Nulls are skipped and counted, never filled
- timestamps are unique and already chronological; the producer does not reorder

`on_future=exclude` (raw chart replay) drops later bars and records `future_excluded`.
`on_future=reject` (curated input) raises `FUTURE_INPUT`.

`lookback_id` and `lookback_bars` are required. They are an input identity (`INPUT_IDENTITY_NOT_A_MODEL_PARAMETER`), not an approved indicator window. Too few complete bars raises `MISSING_LOOKBACK`.

Chart `meta.symbol` must equal `ticker`. `company_id` is the caller's id and is not inferred. A mismatch raises `COMPANY_IDENTITY`.

Provenance is `artifact_id`, sha256 of the raw bytes, byte length, `source_provider`, `source_reference`. A mismatch raises `MISSING_PROVENANCE`.

## Company record

`TECHNICAL_COMPANY_RECORD` schema 1. This is the upstream artifact, not a second producer-snapshot schema.

Fields: `company_id`, `ticker`, `as_of`, `available_at` (max stamp in the window), `lookback`, `technical_outputs`, `methodology`, `input_lineage`, `source_hashes`, `generated_at`, `synthetic`, `validation`, `research_state`, `policy_blockers`.

`technical_outputs.status` is `NOT_AVAILABLE` and `reason_code` is `TECHNICAL_NO_REAL_MODEL` on REAL_INPUT and FIXTURE. Regime, zone, indicators, and scenarios are null. `model_applied` is false.

Semantic hash excludes `generated_at`, `record_id`, `semantic_hash`, and `engine_snapshot_id`. Same semantic input → same hash. A different `as_of` changes the hash.

`universe_claim` is false. A partial batch reports `coverage=PARTIAL` and is not a 500-name result.

## Exporter

`technical/exporter.py` emits the same JSON as PR #9 `producers.contract.not_available` for section `technical` (golden file, validated in this session against `6fe9eee`). `data` is null. The exporter does not import `TechnicalEngine`.

Reason text is the Web default `운영 Snapshot이 연결되지 않았습니다.` Reason code `TECHNICAL_NO_REAL_MODEL`.

## Network

`technical/*.py` does not import urllib. `tools/technical_real_sample.py --fetch` is the only network path. `--from` an existing store is offline. Yahoo payloads stay out of git.
