# QGV Real Producer v1 — Contract

Code: `src/investment_system/qgv_producer/`.
Tools: `tools/qgv_producer.py`, `tools/qgv_producer_infra_compat.py`.
Tests: `tests/test_qgv_producer.py`, `tests/test_qgv_producer_infra_compat.py`.
CI: `.github/workflows/qgv-producer-real.yml`.

**Single responsibility:** preserve the existing QGV engine result per company, reproducibly, and hand it to Producer Infrastructure v1.
The producer **does not** compute, rescore, normalize, re-rank, choose a Universe or change any status.

## 1. Flow

```
Frozen Official Universe (tools/official_pipeline.load_official; Track A gate evidence, exact member/order check)
  → existing engine, unchanged: run_vertical_slice_from_store → run_as_of → AnalysisPipeline/AnalysisEngine
      (observed by capture.capture_qgv_engine: args + return values recorded, passed through untouched)
  → batch.run_qgv_batch: one QGV_COMPANY_RESULT per Universe member (PASS / FAIL / NOT_RUN) + batch manifest
  → exporter.export_batch: validate → persist → serialize (atomic)
  → infra_boundary: Producer Infrastructure v1 adapters/contract (read-only dependency) → NOT_AVAILABLE today
  → Web bundle (Infrastructure assembler; unchanged)
```

## 2. QGV_COMPANY_RESULT v1 (`record.py`)

QGV-specific persistence record. It is **not** a Producer Snapshot. It wraps the existing `contracts.models.QGVSnapshot`.

| Key | Content |
|---|---|
| `record_kind`, `record_version` | `QGV_COMPANY_RESULT`, `1` |
| `semantic.company_id`, `ticker`, `cik` | Universe member identity: canonical `company_id` from the Official snapshot. PR #7 metadata is never the identity source |
| `semantic.as_of` | Prediction date (tz-aware) |
| `semantic.status`, `status_reasons` | `PASS` / `FAIL` / `NOT_RUN` (existing vocabulary) and sorted reason codes |
| `semantic.qgv` | **Verbatim** `QGVSnapshot` (Q/G/V, total, attractiveness, coverage, factor_breakdown, V candidates, g_horizon, versions, synthetic…) minus `qgv_snapshot_id` |
| `semantic.sub_factors` | The `FactorObservation`s the engine scored: `raw_value`, `score_0_100`, `quality`, `stamp_id`, `notes` |
| `semantic.cross_section` | The engine's own `rank`, `eligible`, `selected_provisional`, `n_cross_section` |
| `semantic.methodology` | QGV system/standard/analysis-contract/implementation versions (must equal the snapshot's); `weights_sha256` of the frozen `qgv/factors.py` weights; run profile id and parameter hash; cross-section rule id/status |
| `semantic.research_state` | `status=PROVISIONAL_RESEARCH`, `rule_id`, `v_policy_status`; `official_selection`/`official_pass`/`full_pit_pass`/`calibrated`/`track_c_validated` = false |
| `semantic.pit` | Fundamentals `available_at`, stamp id, flags, source kind; PIT price `observed_at`; prior-year price `observed_at`; known limitation `SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED` |
| `semantic.lineage.inputs` | `raw:companyfacts:<CIK10>` and `raw:yahoo_chart:<TICKER>:5y`, each with sha256 of the actual bytes, size, source kind/url and fetched_at |
| `semantic.universe` | `universe_id`, kind, policy, membership basis, `available_at`, member position, evidence files with sha256 |
| `semantic.synthetic` | Bool; must agree with every synthetic marker |
| `semantic_sha256` | sha256 of canonical JSON of `semantic` (sorted keys, compact, UTF-8, no NaN; same settings as Infrastructure `serialization.py`) |
| `operational` | `generated_at`, `code_commit`, `run_id`, `qgv_snapshot_id` (engine UUID). **Excluded from the semantic hash** |

`qgv_snapshot_from_record()` rebuilds the exact `QGVSnapshot`. A round trip is checked to be byte-identical.

## 3. Status rules (fail-closed)

| Condition | Status |
|---|---|
| Engine raised for the name (`name_errors`) | FAIL `CALCULATION_ERROR` |
| No fundamentals at as_of (engine returned no raw) | NOT_RUN `NO_FUNDAMENTALS_AT_AS_OF` (+ `LINEAGE_MISSING:*` if the blob is absent) |
| Blob bytes ≠ store manifest or committed `STORE_INDEX.json` | FAIL `SOURCE_HASH_MISMATCH_*` |
| Fundamentals source absent from the lineage, or no hashed input | FAIL `MISSING_PROVENANCE` |
| `available_at` > as_of, or a price `observed_at` > as_of | FAIL `PIT_VIOLATION`. Upstream, `run_as_of` already aborts the run on fundamental lookahead |
| Missing/naive PIT timestamp | FAIL `PIT_EVIDENCE_MISSING` |
| `synthetic` disagrees with any marker, or synthetic at all for this real producer | FAIL `SYNTHETIC_STATE` |
| Research status other than `PROVISIONAL_RESEARCH`, a promoted V policy, or a research flag set true | FAIL `PROMOTION_FORBIDDEN` |
| Post-as_of keys (`realized_return`, `px1`, `horizon_as_of`, `outcomes`, …) anywhere | FAIL `OUTCOME_LEAK` |
| Captured snapshot ≠ engine ranking values / PIT price | FAIL `CAPTURE_MISMATCH` |
| Missing price chart only | PASS with `PRICE_INPUT_ABSENT` (the engine's canonical MISSING behaviour; nothing filled) |

No interpolation, forward-fill, current-value substitution, peer substitution or synthetic fundamentals. Replay is offline: `tools/qgv_producer.py` refuses sockets, so an absent companyfacts blob stays MISSING and is never fetched live.

## 4. Batch manifest — QGV_PRODUCER_BATCH_MANIFEST v1 (`batch.py`)

`semantic`:
- `as_of`, `scope` (`FULL_UNIVERSE` | `SAMPLE` + note "not a Universe validation"), `sample_ids`;
- `universe` (id, kind, policy, n_members, `members_sha256` of ordered (company_id, ticker, cik), evidence sha256s);
- `expected_count`, `persisted_count`, `counts{PASS,FAIL,NOT_RUN}`, `complete`;
- `records[]{company_id,status,status_reasons,semantic_sha256}`, `records_sha256`;
- `methodology`, `research_state`;
- `engine_run` (n_cross_section, n_selected, n_investable, n_missing, n_name_errors, `ranked_sha256` = numerical fingerprint of the engine's ranked Q/G/V, `selected_sha256`);
- `data_lineage` (raw source, `store_index_sha256`, `n_inputs`, `inputs_sha256` over **all** members' inputs, because V's peer median depends on the whole cross-section).

`semantic_sha256` covers all of `semantic`. `operational`: generated_at, code_commit, run_id, written file sha256.

A SAMPLE batch runs the full cross-section and persists fewer names. Its records are hash-identical to the same names in a FULL batch.
The exporter refuses a manifest whose persisted count differs from the expected count (`PARTIAL_BATCH_HIDDEN`) or whose counts/rows disagree with the records.

## 5. Persistence format (`exporter.py`)

- `<out>/qgv_company_snapshots_<as_of>.jsonl`: one canonical-JSON record per line, sorted by `company_id`, every status included.
- `<out>/qgv_batch_manifest_<as_of>.json`: indented, sorted keys.
- `<out>/qgv_producer_run_<as_of>.json` (tool only): invariance and run report.

Writes use temp file + fsync + `os.replace`; on failure the previous files stay.
`load_export` re-checks the file sha256, every record hash, rows and counts.

## 6. Producer Infrastructure v1 boundary (`infra_boundary.py`)

- Read-only dependency pinned at `feature/producer-infrastructure-v1@5fa7ce0` (code `bcfdcd2`). No contract copied.
- `load_infra()` imports `investment_system.producers`. On this branch it returns None (not merged).
- `build_infra_snapshots()`:
  - rebuilds `QGVSnapshot`s;
  - calls `adapters.qgv_section` (ENTITY_MAP, verbatim);
  - builds the research candidate with `contract.make_snapshot` (state `FROZEN_SNAPSHOT`, `methodology.status=PROVISIONAL_RESEARCH`, `file:` inputs with sha256);
  - validates the candidate and expects `ResearchStatusError`;
  - returns the publishable `contract.not_available(... reason_code=QGV_RESEARCH_ONLY_NO_EXPORT)`.
- Consumed API: `EXPECTED_INFRA_API`. `tools/qgv_producer_infra_compat.py` fails if any name is missing.

## 7. Integration requirements (for Producer Infrastructure / Web owners; not implemented here)

| ID | Requirement | Why |
|---|---|---|
| IR-1 | A Web/Producer data state for real-but-research outputs (P01 option B or equivalent), shown with a "research / not validated" badge, never counted as LIVE | QGV is `PROVISIONAL_RESEARCH`. Until then the QGV section is `NOT_AVAILABLE` (export-blocked) |
| IR-2 | Map `methodology.status=PROVISIONAL_RESEARCH` (and `V_policy_status=PROVISIONAL_INITIAL_PRIOR`) to that state | Statuses are copied verbatim; the Infrastructure must not rename them |
| IR-3 | The QGV ENTITY_MAP `data_sha256` includes `qgv_snapshot_id` (a per-run UUID). Use the QGV `semantic_sha256` / manifest hash for change detection, or exclude `qgv_snapshot_id` | Otherwise identical results look changed on every run |
| IR-4 | A Web field or panel for `research_state`, `pit.known_limitations`, `cross_section.rank` (if wanted) | `WEB_READS['qgv']` reads only Q/G/V/total/confidence/coverage_state |
| IR-5 | Web `companies` comes from the 2024-12-31 Universe only. Earlier-date QGV ids may be absent from it | Multi-date display needs per-as_of company lists |
| IR-6 | Durable raw storage (Infrastructure P03). The only blob copy expires **2026-12-26** | After that, real re-runs are impossible |
| IR-7 | Entity Metadata (PR #7) joins on `company_id` → display/search only | QGV identity stays the Universe `company_id` |
