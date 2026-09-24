# Product / UI Architecture mapping

Status: PROVISIONAL overlay on Architecture v1.0. Existing engines not rewritten.

## Layers

| Layer | Examples | User menu? |
|---|---|---|
| Backend infrastructure | providers, SEC, Yahoo, PIT, raw_map, pipeline, adapters | No |
| Application engines | qgv.analysis/simulation/portfolio/leaderboard/track_record, technical.engine, macro.engine, integration.engine | No (consumed by pages) |
| Product workspaces | Home, QGV, Technical, Macro, Integrated, Strategy Lab | Yes |
| UI pages | 17 pages under web/app | Yes |

## Page → Engine

See `contracts/product.py` NAV_PAGES.

## Data links

- SecurityContext shares company_id / ticker / as_of between QGV and Technical.
- Macro remains market-level; only Macro Snapshot is referenced.
- Final decision: QGV + Technical + Macro + Portfolio/Risk → Integration → target weight / execution.

## Validation vs Track Record

- Backtest = replay with PIT-available data only.
- Track Record = immutable prediction at as_of + later outcome.
- Existing QGV TrackRecordStore kept; ScopedTrackStore generalizes scope.

## Strategy Profile

- Styles: Defensive / Balanced / Aggressive / Custom mix.
- Configurable: cash_buffer, risk_multiplier, lookback, signal threshold, macro sensitivity, deadband.
- Frozen: Q/G weights, V production off, Macro v0.1.1, Q7 label (C-03).
- Profile values = PROVISIONAL.

## Conflicts checked

- C-01: profile does not select Macro v0.1.4.
- C-03: Q7 label not user-editable.
- C-08: TEL not added to US search workspace.
- C-16: UI overlay does not claim Drive recovery.

## Frontend IA 2026-09-23

Target navigation: Home / QGV Hub / Technical Workspace / Macro Dashboard / Strategy.
QGV keeps five module pages. Technical and Macro collapse to one screen each.
See `Investment-System1 · Frontend Information Architecture 2026-09-23.md`.
HTML prototype not rewritten in that session.
