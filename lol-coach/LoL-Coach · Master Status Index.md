# LoL-Coach · Master Status Index

Updated: 2026-09-27 20:50 KST (R0)
Project Version: v0.1-core

| Module | File | Status | Tests |
|---|---|---|---|
| GameState minimum model | backend/state/models.py | IMPORTED (as received) | covered by baseline |
| Action taxonomy | backend/decision/actions.py | IMPORTED · INCOMPLETE (9/16 actions defined, OI-1) | covered by baseline |
| Opportunity detection | backend/decision/opportunity.py | IMPORTED (PUNISH only) | covered by baseline |
| Permission calculation | backend/decision/permission.py | IMPORTED | covered by baseline |
| Action validity evaluation | backend/decision/evaluator.py | IMPORTED | covered by baseline |
| Recommendation selection | backend/decision/selector.py | IMPORTED | covered by baseline |
| Decision trace | backend/decision/trace.py | IMPORTED · PARTIAL (no action-level trace, OI-3) | covered by baseline |
| Engine orchestration | backend/decision/engine.py | IMPORTED | covered by baseline |
| Fixture runner | — | NOT STARTED | — |
| Replay | — | NOT STARTED | — |
| Windows Bridge | — | NOT STARTED | — |
| AI/API analysis | — | NOT STARTED | — |
| React UI | — | NOT STARTED | — |
| SQLite persistence | — | NOT STARTED | — |

Validation Level
- Unit / characterization: 11/11 PASS (2026-09-27, Python 3.11.15, pydantic 2.13.5, pytest 9.1.1).
- Scenario fixtures: NOT RUN (runner not built).
- Replay / live-game validation: NOT RUN.
- Baseline tests pin behaviour as received; they do not certify coaching correctness.
