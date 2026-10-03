# Technical REAL Producer — audit (canonical b8e39a2)

Recorded before implementation. GitHub is the source. No other agent branch was modified.

## What the engine actually calculates

`technical/engine.py` `TechnicalEngine.evaluate` is a structural placeholder:

- input is an untimestamped `returns: list[float]`
- population standard deviation `> 0.04` → `HIGH_VOL` / `RISK_REDUCTION`
- else last return and the sum of the last five returns choose `TREND_UP` (`ADD` if last `> 0.01`, else `ENTRY`), `TREND_DOWN` / `WAIT`, or `RANGE` / `WAIT`
- empty returns → `UNKNOWN` / `WAIT`
- scenarios are three fixed shocks `(-0.1, 0.0, 0.1)` labelled `structural-placeholder`
- invalidation text is the placeholder sentence
- `synthetic` defaults to `True`
- QGV scores are read only as an id (C-15). `mutated_qgv` stays false

That formula was not changed. Fingerprint `28e910f3005c74888aa33e9b6f45b8d94fc70d4f023e1bc49a6af4100ea9ede6`.

## Placeholder vs real

The engine, its scenarios, and its invalidation string are placeholders. `validation/adapters.TechnicalAdapter` calls `evaluate` without forcing the flag, so the default `synthetic=True` stands. There is no `available_at` on `TechnicalSnapshot` (conflict C-28). Track C's unmerged `evaluate_stamped` is not on canonical and was not copied.

## Where the design is

- `Technical Analysis System · Consolidated Record v0.1.md`
- `Technical Analysis · Decision History v0.1.md` (U-01..U-12 unresolved)
- `Technical Analysis System · Latest Status Update 2026-09-22.md` (Phase 6 structural freeze, not a forecast validation)
- Code contract: `TECHNICAL_STRUCTURAL = v0.6-STRUCTURAL-FREEZE`

The v0.6 package that the status page calls "159/159" is not in this repository (`Missing Artifact Register`).

## Design vs code

| Item | Class |
|---|---|
| Separate Technical layer; do not overwrite QGV raw scores | IMPLEMENTED |
| `TechnicalSnapshot` fields, regime enum, execution-zone enum | IMPLEMENTED |
| Placeholder regime/zone function above | IMPLEMENTED (synthetic). Not promoted |
| Research indicators vs model indicator set | DESIGNED_NOT_IMPLEMENTED (U-01) |
| TSV weights, RS, structure, volume/flow features | DESIGNED_NOT_IMPLEMENTED |
| Regime algorithm as an approved rule | POLICY_BLOCKED (U-04). Placeholder thresholds stay inside DEMO only |
| S=1..N scenarios, similarity, probability, calibration | DESIGNED_NOT_IMPLEMENTED (U-05..U-07) |
| Forecast horizon 120/252 as an official constant | DESIGNED_NOT_IMPLEMENTED (U-08) |
| QGV fusion output | DESIGNED_NOT_IMPLEMENTED (U-09) |
| Which price becomes a return (close, adjclose, Track A `CLOSE_X_POST_AS_OF_SPLIT_FACTOR`) | POLICY_BLOCKED |
| Simple vs log return | POLICY_BLOCKED |
| Official lookback length | POLICY_BLOCKED (U-02). A caller-supplied window is an input identity only |
| Volume indicator | POLICY_BLOCKED. Volume is an input fact only |
| Chart UI / realtime provider choice | DESIGNED_NOT_IMPLEMENTED (U-10, U-11) |

## Price source and PIT

Canonical price bytes are Yahoo chart artifacts `yahoo_chart:<SYMBOL>:<range>` in `RawDatasetStore` (`ingestion/replay.load_price_bars` → `yahoo_chart.parse_bars`). `parse_bars` drops volume. This producer reads volume from the same JSON without changing `parse_bars`.

Existing stamp, reused and not redefined: `yahoo_chart.to_price_point` sets `available_at = observed_at`. Ingestion `fetched_at` is not a PIT timestamp (`ingestion/manifest.py`).

`parse_bars` prefers adjclose for the single `price` field used by market-cap code. That choice is not an approved Technical return. Both `close` and `adjclose` are hashed into the window identity and neither is selected.

Blobs are not in git (Actions artifact, audit B9). This branch does not commit Yahoo payloads.

## Producer Infrastructure and Web

PR #9 (`feature/producer-infrastructure-v1` @ `6fe9eee`, not merged) publishes technical as `NOT_AVAILABLE` / `TECHNICAL_NO_REAL_MODEL` because the engine is the placeholder. Web schema-1 (PR #5, not on canonical) reads `regime`, `execution_zone`, `invalidation` and rejects synthetic data unless `DEMO`. C-28: do not invent `available_at` on `TechnicalSnapshot`.

Track C (`feature/track-c-evl`) consumes `evaluate_stamped` returns. That method is not assumed and that branch was not edited. Holdout was not read.

## What this branch can make real without breaking a freeze

PIT screening, provenance, explicit lookback identity, company record, DEMO/REAL separation, and a fail-closed `PRODUCER_SNAPSHOT` `NOT_AVAILABLE` adapter. It cannot turn the placeholder into a live model.
