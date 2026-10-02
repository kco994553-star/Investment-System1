# US_EQUITY_TRADING_SESSION_V1 — status

Approved contract, implemented beside the Technical model.
`technical/real_model_v1.py`, `technical/engine.py`, `technical/pit_market.py`,
and `providers/yahoo_chart.py` are not modified.

**Session / Technical implementation baseline / INTEGRATION WAIT.**
Draft only. Not merged. Not a research-display grant, Frozen grant, Live grant, or Track C change.

| State | Verdict |
|---|---|
| Session binder | Implemented for an explicit vintage and one listing interval |
| Close-availability guard | Implemented as a lower bound. Provider publication time is not claimed |
| REAL_TECHNICAL_RESEARCH_PRODUCER_READY | NO. No exchange-issued vintage has been replayed end to end |
| OFFICIAL_TECHNICAL_PRODUCER_READY | NO. Track C is unchanged |

M1 and M2 formulas, M3, the placeholder engine, QGV, Macro, Track C, Web publication,
and Portfolio are not part of this change.

The inner research record still reports `exchange_calendar: UNBOUND` because that
string is produced by the untouched model. The binding envelope carries `calendar_id`.

Do not derive `session_index` from a calendar-day rule.
Do not treat fixture vintages as the NYSE or Nasdaq calendar.

## PR #18

| Check | Result |
|---|---|
| URL | https://github.com/kco994553-star/Investment-System1/pull/18 |
| State | OPEN, draft |
| Base | `feature/technical-real-model-v1` `ce587040e7beb31b66a423eab6ca89767f2a2cf8` |
| Head at this evidence commit | this commit. It is not the code SHA below |
| Merge-base with base | `ce587040e7beb31b66a423eab6ca89767f2a2cf8` |
| Diff vs base before this docs commit | session package only: `sessions/`, `docs/us_equity_session/`, `tests/test_us_equity_session_v1.py`, `.github/workflows/us-equity-session.yml` |
| Mergeability at code SHA | MERGEABLE, mergeStateStatus CLEAN |
| Merged | NO |

## Code SHA and Actions

Code SHA is the implementation commit. This evidence commit does not change it.

| Identity | SHA |
|---|---|
| Code commit | `1d9bc11a23a967f350cf6782468efff6aeb17a66` |
| `implementation/src/investment_system/sessions` tree at the code commit | `5d26bcb5931345dd8eac4649cb3424dfb6809166` |
| `implementation/src/investment_system/technical` tree | `ddf49c251328a8b3f637bc923e7f021e822181fa` (same blob as base `ce587040`) |

Actions below completed with conclusion `success` on code SHA `1d9bc11a23a967f350cf6782468efff6aeb17a66`. No other SHA is claimed.

| Workflow | Event | Run | Job | Conclusion |
|---|---|---|---|---|
| us-equity-session | push | [36980569432](https://github.com/kco994553-star/Investment-System1/actions/runs/36980569432) | 110753918406 offline | success |
| us-equity-session | pull_request #18 | [36997605461](https://github.com/kco994553-star/Investment-System1/actions/runs/36997605461) | 110807810864 offline | success |
| technical-real-model | pull_request #18 | [36997605404](https://github.com/kco994553-star/Investment-System1/actions/runs/36997605404) | 110807810836 offline | success |
| technical-real-producer | pull_request #18 | [36997605344](https://github.com/kco994553-star/Investment-System1/actions/runs/36997605344) | 110807810381 offline | success |

`c21-real-data` is `workflow_dispatch` only and did not run. A later docs commit is not covered by the rows above until its own run completes on that later SHA.
