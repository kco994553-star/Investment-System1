# US_EQUITY_TRADING_SESSION_V1 — status

Approved contract, implemented beside the Technical model.
`technical/real_model_v1.py`, `technical/engine.py`, `technical/pit_market.py`,
and `providers/yahoo_chart.py` are not modified.

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
