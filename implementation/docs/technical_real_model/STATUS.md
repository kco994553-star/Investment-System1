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
