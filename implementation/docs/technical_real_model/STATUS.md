# TECHNICAL_REAL_MODEL_V1 — status

M1 and M2 are implemented as a separate research record. The v0.6 placeholder engine is byte-identical and is not called.

M3 is not implemented. Scenario output is `NOT_AVAILABLE` / `M3_NOT_APPROVED`.

Track C was not modified. Holdout was not read. No canonical merge. PR #11 was not updated.

| State | Verdict |
|---|---|
| M1 feature engine | Implemented for explicit session indexes and an explicit split status |
| M2 regime/zone | Implemented. Missing mandatory input stays `NOT_AVAILABLE` |
| M3 scenarios | NOT APPROVED / not implemented |
| Web research publication | BLOCKED until P01. Exporter remains `NOT_AVAILABLE` |
| REAL_TECHNICAL_RESEARCH_PRODUCER_READY | NO. Real chart bytes still have no verified exchange session index |
| OFFICIAL_TECHNICAL_PRODUCER_READY | NO |

Do not feed stored bars into `TechnicalEngine`. Do not derive `session_index` from a calendar-day rule.

## Verification against the M1/M2/M4 approval

Checked on `4c69ceddef9ce7b37ebdf7ab9af35f50e3245fd4`. Diff vs producer HEAD is only this model, its tests, this contract/status, and `.github/workflows/technical-real-model.yml`.

| Check | Result |
|---|---|
| Targeted M1/M2 tests | Present in `implementation/tests/test_technical_real_model_v1.py` |
| PIT / no lookahead | Future bars raise `FutureInputError`. Current session is not a confirmed swing |
| Corporate-action fail-closed | `split_status=UNKNOWN` → price features `CORPORATE_ACTION_UNKNOWN`. Close is not rewritten. `adjclose` is not read |
| Missing feature | One missing mandatory feature sets regime and zone to `NOT_AVAILABLE`. Other computable features stay |
| SPY alignment | `rs_20` uses the same session indexes. Missing SPY does not block regime |
| Determinism | Semantic hash ignores `generated_at` and changes when close changes |
| Placeholder regression | `engine.py` sha256 `f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf` unchanged. Demo path still `STRUCTURAL_PLACEHOLDER` |
| QGV / Macro / Portfolio / Leaderboard / Track C | Not in the diff |
| Full regression | GitHub Actions `offline` **PASS**, `431 passed, 0 failed` (mini_pytest shim) |

Workflow: `.github/workflows/technical-real-model.yml`. Actions on `4c69ced`:

- push [36859147939](https://github.com/kco994553-star/Investment-System1/actions/runs/36859147939) SUCCESS (35s)
- pull_request [36859156534](https://github.com/kco994553-star/Investment-System1/actions/runs/36859156534) SUCCESS (34s)

Producer workflow on the same head also SUCCESS: [36859156349](https://github.com/kco994553-star/Investment-System1/actions/runs/36859156349).

## Readiness re-judgment

`REAL_TECHNICAL_RESEARCH_PRODUCER_READY` stays **NO**. M1/M2 software runs only when the caller supplies an explicit `session_index` on every stored observation and an explicit split status. Live Yahoo chart bytes do not carry a verified exchange session index, and this module does not invent one. `gap_rule_days` is null.

`OFFICIAL_TECHNICAL_PRODUCER_READY` stays **NO**. This is not an Official Technical model, not Track C validation, and not a Web publication. M3 remains unimplemented. Draft PR #15 is not a merge.

## C-28 upstream adoption — additive note (2026-10-03)

The Technical owner adoption record for Track C `2137883` (additive `available_at` / `data_stamp_refs` / `source_vintages` / `input_hash` fields and `evaluate_stamped`, adopted as the shape of the canonical C-28 upstream patch per user CDR-004) is `docs/technical_real_producer/C28_UPSTREAM_ADOPTION_2026-10-03.md`; it is referenced here, not duplicated. This model never calls `TechnicalEngine`, so its research records and the `produce_demo` output are identical before and after the adoption: `evidence/c28_adoption_invariance_2026-10-03.json` (PASS, zero field differences; recorded before the pin edit). `tests/test_technical_real_model_v1.py` keeps the pre-adoption engine pin `f7268f52…` and adds the adopted pin `86607bf7…`, selected state-exactly from the adopted feature itself. The "Placeholder regression" row above stays true for this branch's own delta: the adopted `technical/engine.py` bytes arrive via integration of the Track C tip, not via this PR. M1/M2 formulas, M3 status, regime/zone values and `real_model_v1.py` bytes are unchanged. Prepared by the Primary Integration Writer; becomes the owner's adoption when merged into `feature/technical-real-model-v1`. `CANONICAL_STATE`: NOT_MERGED.
