# PRODUCER_INFRASTRUCTURE_V1 — Contract

Scope: the common infrastructure that later connects real producers to the Web MVP safely.
It performs **no investment calculation**. It validates, serializes, hashes and assembles what upstream owners produce.
It **fails closed** in two ways:
- Anything missing, unverifiable or mislabelled raises an error.
- Anything valid that the Web cannot represent is published as `NOT_AVAILABLE`.

Code: `implementation/src/investment_system/producers/`. CLIs: `tools/export_web_bundle.py`, `tools/raw_persistence_audit.py`,
`tools/producer_engine_fingerprint.py`. Tests: `tests/test_producer_infrastructure.py`.

## 1. Reuse — no duplicate schema

| Concern | Reused existing contract | Added here |
|---|---|---|
| Data states | `product.web_mvp.STATES` = `LIVE`, `FROZEN_SNAPSHOT`, `DEMO`, `NOT_AVAILABLE` | none (imported, not copied) |
| Sections | `product.web_mvp.SECTIONS` + `universe` | none |
| Web bundle | Web schema-1 (`validate_bundle`, `build --input`) | additive `producer` key per section and `producer_manifest` (ignored by the UI; shown in Evidence) |
| Synthetic marker | Same predicate as `validate_bundle` | snapshot-level check |
| Research status | `vertical_slice.RULE_STATUS="PROVISIONAL_RESEARCH"`, `CalibrationLifecycle` | Blocked from publication (see §4) |
| Raw provenance | `ingestion.RawDatasetStore` + `RawArtifactManifest` | Dataset-level persistence manifest and retention audit |
| Freshness enum | `contracts.enums.Freshness` GREEN/YELLOW/RED has **no thresholds** anywhere in the repo | Not mapped; no TTL invented |

## 2. PRODUCER_SNAPSHOT v1 (`producers/contract.py`)

| Field | Rule |
|---|---|
| `contract`, `schema_version` | `"PRODUCER_SNAPSHOT"`, `1`. Any other value → `SchemaVersionError` |
| `producer_id`, `producer_version` | Non-empty strings |
| `section` | `universe` or a Web section |
| `data_state` | Exactly one Web schema-1 state. `STALE`, `RESEARCH`, `PROVISIONAL_RESEARCH` and similar → `UnsupportedStateError` |
| `requested_as_of` | Optional, tz-aware. This is what the scheduler asked for |
| `as_of` | The actual data as_of. Tz-aware. Must be ≤ `generated_at` and ≤ `requested_as_of` |
| `generated_at` | Tz-aware. When the producer ran |
| `expires_at` | **Required for LIVE.** Tz-aware, > `as_of`. Declared by the producer, never defaulted |
| `usable_until` | Optional, ≥ `expires_at`. Producer-declared hard limit (see §3) |
| `methodology` | `{id, version, status}`. `status` is copied verbatim from upstream |
| `synthetic` | Bool. `true` ⇒ only `DEMO`. A synthetic marker inside `data` ⇒ must be `true` |
| `provenance` | `{source, inputs:[{artifact_id, sha256 (64 lowercase hex), bytes?}]}`, ≥1 input, no duplicate ids |
| `validation` | `{status ∈ PASS/FAIL/NOT_RUN, checks}`. `LIVE`/`FROZEN_SNAPSHOT` require `PASS` |
| `scope` | `{kind ∈ ENTITY_MAP/ROWS/DOCUMENT, entity_ids}`. `entity_ids` must equal the ids in `data` |
| `data`, `data_sha256` | `data_sha256` = sha256 of the canonical JSON of `data` |
| `reason`, `reason_code` | Required reason for `NOT_AVAILABLE`, which must carry no data |

Errors are typed (`producers/errors.py`). All subclass `ValueError`, so existing fail-closed callers still catch them.
Types: `SchemaVersionError`, `MissingFieldError`, `TimestampError`, `FreshnessContractError`, `ProvenanceError`, `SourceHashError`,
`SyntheticStateError`, `UnsupportedStateError`, `ResearchStatusError`, `ValidationStatusError`, `IdentityError`,
`IncompatibleShapeError`, `SerializationError`.

Source re-verification: `verify_inputs(snapshot, resolver)` recomputes each input hash from real bytes.
- `file:<path>` resolves under the repository (no path escape).
- `raw:<id>` resolves from a `RawDatasetStore`.
- An input that cannot be resolved, or whose bytes don't match, fails.

## 3. Freshness (`producers/freshness.py`)

Deterministic: the evaluation clock `now` is always passed explicitly and must be tz-aware.

| Result | Condition | Bundle effect |
|---|---|---|
| `FRESH` | LIVE, now < `expires_at` | LIVE |
| `STALE` | LIVE, now ≥ `expires_at`, and no `usable_until` or now < `usable_until` | LIVE envelope keeps `expires_at`. The Web shows a STALE badge (existing contract) |
| `NOT_USABLE` | LIVE, now ≥ producer-declared `usable_until` | Data withheld → `NOT_AVAILABLE`, `reason_code=EXPIRED_NOT_USABLE` |
| `NOT_APPLICABLE` | `FROZEN_SNAPSHOT`, `DEMO`, `NOT_AVAILABLE` | Unchanged; frozen data is point-in-time by definition |

A snapshot whose `as_of` is later than `now` raises `FreshnessContractError`.
No TTL or cadence number is defined in this infrastructure.

## 4. Research / provisional outputs

The Web schema-1 has no state for validated-research data. Publishing `PROVISIONAL_RESEARCH` (or the `CalibrationLifecycle` values
IDEA / RESEARCH / PROVISIONAL / PROVISIONAL_INITIAL_PRIOR) as `LIVE` or `FROZEN_SNAPSHOT` raises `ResearchStatusError`.
Until `PROPOSAL_P01_RESEARCH_DATA_STATE.md` is approved, such producers must emit `NOT_AVAILABLE`.

## 5. Producer interface (`producers/registry.py`)

`ProduceRequest(requested_as_of, now)` (both tz-aware) → `Producer.produce()` → PRODUCER_SNAPSHOT v1.
A producer declares `producer_id`, `section` and `cadence`. Registered producers today:

| Section | Producer | State | Reason code / blocker |
|---|---|---|---|
| universe | `FrozenUniverseProducer` (reuses hash-verified `web_mvp.repository_bundle`) | FROZEN_SNAPSHOT 2024-12-31 | Interim Universe policy = P02 |
| qgv | `UnavailableProducer` | NOT_AVAILABLE | `QGV_RESEARCH_ONLY_NO_EXPORT` |
| technical | 〃 | NOT_AVAILABLE | `TECHNICAL_NO_REAL_MODEL` |
| macro | 〃 | NOT_AVAILABLE | `MACRO_SHAPE_INCOMPATIBLE` |
| portfolio | 〃 | NOT_AVAILABLE | `PORTFOLIO_NO_ACTUAL_HOLDINGS` |
| leaderboard | 〃 | NOT_AVAILABLE | `LEADERBOARD_NO_UPSTREAM_QGV` |
| news | 〃 | NOT_AVAILABLE | `NEWS_NO_SOURCE` |
| relationships | 〃 | NOT_AVAILABLE | `RELATIONSHIPS_OUT_OF_BUNDLE` (use `web_mvp --rig-page`) |
| changes | 〃 | NOT_AVAILABLE | `CHANGES_NO_PRODUCER` |

No schedule is activated. All producers report `cadence` only as information.

## 6. Upstream adapters (`producers/adapters.py`)

Adapters serialize verbatim: no rename, reshape, fill or rescore.

| Section | Upstream type | Compatibility | Web fields absent upstream |
|---|---|---|---|
| qgv | `QGVSnapshot` | COMPATIBLE | — |
| technical | `TechnicalSnapshot` | COMPATIBLE (shape only; engine is a synthetic placeholder) | — |
| macro | `MacroSnapshot` | **INCOMPATIBLE** → `IncompatibleShapeError` | `indicators` (upstream `environment.indicators`), `exposures` |
| portfolio | `PortfolioSnapshot` | PARTIAL | `return`, `market_value`, `currency` (upstream `base_currency`), `exposure` |
| leaderboard | `LeaderboardSnapshot` (rejected if `recomputed_qgv`) | PARTIAL | `market_cap_rank`, `daily_move`, `consensus`, `scenario`, `reevaluation_trigger` |
| news, changes | none | NO_UPSTREAM | all |

Fields the Web reads but the upstream type lacks are left absent; the Web shows them as "미제공" (not provided), never as zero.

## 7. PRODUCER_BUNDLE v1 (`producers/assembler.py`)

`assemble_bundle(companies, snapshots, now)`:
- Every section needs an explicit snapshot (an absent section is an error).
- Each snapshot must declare its own section and pass validation, then freshness is classified.
- The result is the Web schema-1 envelope (`state`, `as_of`, `source`, `data`, `expires_at` for LIVE) plus `producer` metadata: ids, versions, the four timestamps, methodology, validation, source inputs, `data_sha256`, `snapshot_sha256`, freshness and reason code.
- The bundle also gets `producer_manifest` (contract, version, assembled_at, companies hash, per-section summary).
- Finally the existing `web_mvp.validate_bundle` runs.

The result is deterministic: identical inputs and `now` give byte-identical canonical JSON, so the bundle hash is reproducible.
`write_bundle_atomic` validates first, writes via temp file + fsync + `os.replace`, then writes `<bundle>.sha256`.
On failure the previous bundle stays untouched.

Default export (`tools/export_web_bundle.py`) is semantically identical to the existing Web default (`repository_bundle()`):
- same companies, Universe data and source;
- same NOT_AVAILABLE sections and reasons;
- plus provenance.

## 8. Canonical serialization (`producers/serialization.py`)

Settings: sorted keys, compact separators, UTF-8, no NaN/Infinity. Enum values and dataclass fields are expanded.
Naive datetimes and sets are rejected.

## 9. Web change (minimal, semantics preserved)

In `product/web_mvp.validate_bundle`:
- A LIVE section without `as_of`/`expires_at` now raises `ValueError('LIVE requires expires_at')` instead of a raw `KeyError`.
- A missing or malformed section raises `ValueError` instead of a raw `KeyError`.

Every input that was accepted before is still accepted, and every input that was rejected is still rejected.
