# QGV Real Producer v1 — Status / Handoff (FREEZE / INTEGRATION-READY)

Recorded 2026-10-01 (UTC). This file is enough to take over from GitHub; no chat history is needed.
Read with `AUDIT.md` (pre-implementation audit), `CONTRACT.md` (formats, rules, integration requirements) and `evidence/validation.json`.

| Item | Value |
|---|---|
| Branch | `ccr-db5d5960-qen9yi` (the session's designated branch, used in place of the suggested `feature/qgv-real-producer-v1`). Not merged, no PR |
| Baseline canonical | `claude/investment-system-top500-validation-alrugm@b8e39a2` (Track A FROZEN_VERIFIED) |
| Validated code commit | `4b772c2`. Real-data evidence commit `81b87b8` (written by Actions run `36852186517`) |
| Read-only dependency | Producer Infrastructure v1 `feature/producer-infrastructure-v1@5fa7ce0`. Checked out separately in CI; not merged, not modified, not copied |
| Raw data | Track A Frozen artifact `c21-raw-store-36305927245` (expires **2026-12-26**). Every used blob re-hashed against the committed `STORE_INDEX.json`; replay offline (0 network attempts) |

## Results (Actions run 36852186517)

| as_of | Scope | Records | PASS/FAIL/NOT_RUN | Engine coverage | Frozen Track A replay | Before/after numbers |
|---|---|---|---|---|---|---|
| 2024-06-30 | FULL (Official `uni_cb35a6200b61`) | 500 | 500/0/0 | 471 PARTIAL, 29 BLOCKED; Q&G 471; V 443 | PASS: counts, universe, 471-name selected list exact | plain = captured `ranked_sha256` |
| 2024-09-30 | FULL (`uni_12c3852b8333`) | 500 | 500/0/0 | 469 PARTIAL, 31 BLOCKED; Q&G 469; V 443 | PASS: counts, universe, 469-name selected list exact | equal |
| 2024-12-31 | FULL (`uni_0d1a30b1ee47`) | 500 | 500/0/0 | 468 PARTIAL, 32 BLOCKED; Q&G 468; V 439 | PASS: counts, universe exact (no Frozen list for this date) | equal |
| 2024-12-31 | SAMPLE aapl, brk_b, jpm, msft, nvda | 5 | 5/0/0 | — | PASS | records hash-identical to the FULL run |

- **Record PASS** means the engine output was persisted with valid PIT, lineage, identity and research state. It does **not** mean "fully scored". The engine's own `coverage_state` (no name is READY; rubric inputs are absent) and null Q/G/V are preserved verbatim. 3/5/6 names have neither Q nor G.
- **Numerical invariance:**
  - The plain engine run (no capture) and the captured run give identical ranked Q/G/V fingerprints on all dates.
  - Persisted Q/G/V equal the engine values exactly.
  - Versus Frozen Track A, every count, universe id and selected list is exact.
  - The post-as_of equal-weight return differs by ≤ 8.3e-17 (float sum; not a QGV field). It is accepted within 1e-15 and the exact difference is recorded.
  - Run #1 (`36851716398`) failed on a bit-exact comparison of that return. The tolerance was added in `4b772c2`.
- **Determinism:** an independent re-run of 2024-12-31 gave identical hashes for all 500 records and an identical manifest hash. Engine snapshot UUIDs differed as expected (operational field).
- **Producer Infrastructure compatibility (Infrastructure's own validators):** PASS for full and sample.
  - The research candidate is rejected with `ResearchStatusError`.
  - A shape-only probe validates, so research status is the only blocker.
  - Published state is `NOT_AVAILABLE` / `QGV_RESEARCH_ONLY_NO_EXPORT`.
  - `assemble_bundle` + `web_mvp.validate_bundle` PASS.
  - INFO: ids from earlier dates are outside the 2024-12-31 Web company list.
- **Regression:** 424/424 under both the mini_pytest shim and pytest (baseline 396 + 28 new), locally and in CI.
- **Cross-track:** the diff vs `b8e39a2` touches only `qgv_producer/`, `tools/qgv_producer*.py`, `tests/test_qgv_producer*.py`, `docs/qgv_producer/`, `reports/qgv_producer/` and `.github/workflows/qgv-producer-real.yml`. Track A source and evidence, data/raw, Track B/C/D/E, Web PR #5/#6/#7, Technical, Macro and Portfolio are unchanged. CI also asserts `git diff --exit-code -- reports/gate_evidence data/raw`.

## Readiness verdicts

| State | Verdict | Basis |
|---|---|---|
| QGV_PER_COMPANY_PERSISTENCE_READY | **YES** | 1,500 real records with verbatim snapshot, sub-factors, PIT, lineage hashes and semantic hash. Reload and rebuild byte-identical |
| QGV_EXPORTER_READY | **YES** | Validate/persist/serialize only, atomic. Proven not to modify scores or ranks |
| QGV_BATCH_READY | **YES** for the 3 Frozen as_of dates | 500/500 per date, explicit counts, deterministic manifest. Partial batches are reported, never hidden |
| PRODUCER_INFRA_COMPATIBLE | **YES (against pinned 5fa7ce0; dependency unmerged)** | Infrastructure validators PASS. Re-run the compat check after any Infrastructure change |
| REAL_QGV_RESEARCH_PRODUCER_READY | **YES (research grade, export-blocked)** | Real, PIT-validated, reproducible output. Web publication blocked by P01 |
| OFFICIAL_QGV_PRODUCER_READY | **NO** | Track C C7–C10 not complete; methodology stays `PROVISIONAL_RESEARCH`; V is `PROVISIONAL_INITIAL_PRIOR`; P01 not approved |

## Blockers (not implemented here, by scope)

1. **P01:** a research data state in Web schema-1. Until then QGV publishes `NOT_AVAILABLE` (CONTRACT IR-1/IR-2).
2. **Track C:** C7 (TC-D3P-006) approval and C8–C10. Official promotion and profiles belong to Track C. No result assumed, Holdout never read, no Investor-QGV ProfileConfig applied.
3. **P02:** no Universe after 2024-12-31 and no carry-forward policy. No new Universe was created.
4. **P03 / raw durability:** the only blob copy expires 2026-12-26. After that real re-runs are impossible (IR-6).
5. **Known PIT limitation, carried in every record:** `SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED`.
6. Engine coverage: no name reaches READY. Rubric Q/G inputs (competitive advantage, management, durability…) have no source. This is a methodology/data question, not a producer one.

## Exact next step

The integration owner decides **P01**. Then, after Producer Infrastructure v1 is merged (canonical ← #5 ← #6 ← infra), register a QGV producer. It reads `reports/qgv_producer/full/` through `infra_boundary.build_infra_snapshots` and publishes in the approved research state, applying IR-3 (snapshot UUID in `data_sha256`).
To re-run: push to this branch (or `workflow_dispatch` once the workflow is on the default branch) → `.github/workflows/qgv-producer-real.yml`.

This scope is frozen. No further features are planned on this branch.
