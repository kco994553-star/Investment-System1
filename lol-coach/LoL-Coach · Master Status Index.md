# LoL-Coach · Master Status Index

Updated: 2026-09-28 19:35 KST (R1)
Project Version: v0.1-core (core byte-identical to R0) + R1 validation layer

| Module | File | Status | Tests |
|---|---|---|---|
| GameState minimum model | backend/state/models.py | IMPORTED (as received) | baseline + R1 |
| Action taxonomy | backend/decision/actions.py | IMPORTED · INCOMPLETE (9/16 defined OI-1; risk/purpose unused OI-7) | covered by baseline |
| Opportunity detection | backend/decision/opportunity.py | IMPORTED (PUNISH only) | covered by baseline |
| Permission calculation | backend/decision/permission.py | IMPORTED | covered by baseline |
| Action validity evaluation | backend/decision/evaluator.py | IMPORTED | covered by baseline |
| Recommendation selection | backend/decision/selector.py | IMPORTED | covered by baseline |
| Decision trace | backend/decision/trace.py | IMPORTED · PARTIAL (no action-level trace, OI-3) | covered by baseline |
| Engine orchestration | backend/decision/engine.py | IMPORTED | covered by baseline |
| Fixture runner | validation/fixture_runner.py | IMPLEMENTED (R1) | GF 2 + CF 10 PASS |
| Metamorphic validation | validation/metamorphic.py | IMPLEMENTED (R1) | MR 8/8 PASS, exhaustive 1,296 states |
| Replay | — | NOT STARTED | — |
| Windows Bridge | — | NOT STARTED | — |
| AI/API analysis | — | NOT STARTED | — |
| React UI | — | NOT STARTED | — |
| SQLite persistence | — | NOT STARTED | — |

Validation Level (2026-09-28 R1, Python 3.11.15, pydantic 2.13.5, pytest 9.1.1)
- pytest: 32/32 PASS (R0 baseline 11 + R1 21, incl. runner self-tests and core sha256 guard).
- Scenario fixtures: GF-001, GF-002 PASS; counterfactual CF-001-A..H, CF-002-A..B PASS.
- Metamorphic: MR-01..05 (DESIGN) + MR-06..08 (CURRENT, tied to OI-5/3/4) PASS, 19,411 checks.
- Replay / live-game validation: NOT RUN.
- All PASS results pin behaviour as received; they do not certify coaching correctness.
  GF expectations are PROVISIONAL until compared with the original design in R2.
