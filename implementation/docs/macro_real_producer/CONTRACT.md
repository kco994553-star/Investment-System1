# MACRO_REAL_PRODUCER_V1 — Contract

Scope: connect point-in-time macro vintages to the existing confirmed Macro engine and hand Producer Infrastructure a snapshot it can consume. No investment rule is added or changed.

Code: `implementation/src/investment_system/macro/real_producer.py`. Tests: `implementation/tests/test_macro_real_producer.py`.

## Ownership

- This branch only. Do not merge into canonical, PR #5/#6, PR #7, PR #9, or `feature/track-c-evl`.
- Producer Infrastructure (`producers/`) is a read-only dependency. Its snapshot schema, adapter, assembler, and default registry are not modified.
- `macro/engine.py` is not modified. Confirmed rules remain: inflation > 0.08 → EMERGENCY / INFLATION_SHOCK; inflation > 0.05 and growth < 0 → WARNING / STAGFLATION_RISK; growth > 0.03 and inflation < 0.03 → NORMAL / EXPANSION; otherwise NORMAL / NEUTRAL. Missing keys still default to 0.0 **inside the engine**. This producer does not call the engine unless growth and inflation survived the PIT filter.

## Pipeline

```text
ALFRED vintage records
  → provenance + available_at checks
  → latest vintage with available_at <= decision_time (later revisions ignored)
  → existing collect_indicators_alfred (row date and row available_at <= decision_time)
  → existing MacroEngine.evaluate
  → research MacroSnapshot (existing dataclass)
  → PRODUCER_SNAPSHOT v1 NOT_AVAILABLE (POLICY_BLOCKED)
  → existing assembler / Web schema-1
```

`company_industry_exposure` raises `PolicyBlocked`. It returns no coefficient.

## Input

`VintageSeries` is one existing series from `fred_csv.SERIES` (`INDPRO`, `CPIAUCSL`, `DGS10`, `WALCL`, `BAMLH0A0HYM2`). Any other series id is rejected. Required pillars are growth and inflation; the other three stay optional and unscored beyond what the existing collector already stores.

| Field | Rule |
|---|---|
| `available_at` | Required, timezone-aware. A vintage later than `decision_time` is not eligible |
| `vintage_kind` | Only `ALFRED_AS_OF`. `CURRENT_REVISED_NOT_ALFRED` raises `RevisedHistoryError` |
| `artifact_id`, `source` | Required, non-empty. Duplicate artifact ids are rejected |
| `sha256` | 64 lowercase hex of the canonical JSON of `payload` (`producers.serialization`) |
| `vintage_at`, `release_at`, `ingested_at` | Optional. Preserved when supplied. Not invented |
| `synthetic` | `true` raises `SyntheticLiveError` before the engine runs |

If every vintage of a required series is still in the future, the call raises `FutureReleaseError`. If a required pillar is simply absent, the call raises `MacroInputError`. It does not substitute 0.0.

`decision_time` and `generated_at` are timezone-aware and `decision_time <= generated_at`.

## Research snapshot

The returned `MacroSnapshot` uses `macro_version=v0.1.1`, `synthetic=false`, `mutated_qgv=false`, and `environment.candidate_not_applied=v0.1.4-CANDIDATE`. `macro_snapshot_id` is `mac_` plus 12 hex chars of the canonical hash of the decision, indicator values, regime, version, and selected artifacts. Same inputs and `generated_at` produce the same snapshot and the same producer JSON.

`environment.pit.series` records the selected artifact id, sha256, source, `available_at`, and any supplied `vintage_at` / `release_at` / `ingested_at`. `real_data_verified` stays false. `fallback_reason` stays null: this path never calls the revised CSV collector.

## Web / Producer Infrastructure

Publication is `POLICY_BLOCKED`. The producer snapshot is `not_available(...)` with `reason_code=POLICY_BLOCKED` and `methodology.status=PROVISIONAL`. `data` is null. Reasons, all required together:

1. `SERIES_MAPPING_PROVISIONAL` — the existing FRED map is marked provisional. Publishing its regime as LIVE or FROZEN_SNAPSHOT would promote it.
2. `EXPOSURE_NOT_APPROVED` — no approved company or industry coefficient.
3. `WEB_INDICATORS_NOT_RESHAPED` — `environment.indicators` is not renamed to Web `indicators`. PR #9 `macro_section` still raises `IncompatibleShapeError`.
4. `NO_APPROVED_LIVE_EXPIRY` — no TTL is invented, so LIVE cannot be formed.

The default registry is unchanged (`MACRO_SHAPE_INCOMPATIBLE`). An operator may pass this snapshot to `tools/export_web_bundle.py --snapshot`. The assembler then validates it with the existing contract. No competing snapshot schema is defined.

## Out of scope

Live FRED authentication, REAL-DATA VERIFIED promotion, Official readiness, Track C `evaluate_stamped`, exposure math, and any edit to QGV, Technical, Portfolio, Leaderboard, Universe, RIG, or Prompt Library.
