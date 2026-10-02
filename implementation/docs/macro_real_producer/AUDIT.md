# Macro REAL Producer — audit

Recorded: 2026-10-01. Base inspected after `git fetch`: canonical `claude/investment-system-top500-validation-alrugm` @ `b8e39a2`. This branch is cut from Producer Infrastructure PR #9 `feature/producer-infrastructure-v1` @ `6fe9eee` and does not merge canonical or any other agent branch.

Labels: `IMPLEMENTED` (code on the base does this), `DESIGNED_NOT_IMPLEMENTED` (a design record exists; this change does not invent the missing rule), `POLICY_BLOCKED` (publishing or promoting it would cross an existing freeze).

| Item | Where inspected | Label |
|---|---|---|
| Confirmed Macro v0.1.1 engine: NORMAL / WARNING / EMERGENCY and NEUTRAL / EXPANSION / STAGFLATION_RISK / INFLATION_SHOCK from growth and inflation thresholds | `macro/engine.py`, `versions.py` `MACRO_CONFIRMED=v0.1.1` | IMPLEMENTED |
| v0.1.4 candidate factors, scenario engine, transmission, stress, portfolio context, probability distribution | `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` §§14–22; engine stores `candidate_not_applied` and does not apply it | DESIGNED_NOT_IMPLEMENTED |
| Regime rules, weights, thresholds | Engine thresholds only. v1.2 OM/TM/MM/RM and strategy `macro_warning_sensitivity` are provisional / unresolved (Track C `UNRESOLVED`) | IMPLEMENTED for v0.1.1 thresholds. POLICY_BLOCKED for anything else |
| FRED public CSV ingestion | `providers/fred_csv.py`. Vintage label `CURRENT_REVISED_NOT_ALFRED` | IMPLEMENTED as a fetch tool. POLICY_BLOCKED as a decision input |
| ALFRED `realtime_end` vintage fetch and row filter (`date` and `available_at` ≤ as_of) | `providers/fred_alfred.py`, `tests/test_alfred_vintage_pit.py` | IMPLEMENTED. Not REAL-DATA VERIFIED (`real_data_verified` stays false) |
| YoY indicator transform and pillar map growth/inflation/rates/liquidity/risk → INDPRO/CPIAUCSL/DGS10/WALCL/BAMLH0A0HYM2 | `fred_csv.py` comment: "Mapping is PROVISIONAL." | IMPLEMENTED as existing tooling. POLICY_BLOCKED for LIVE/FROZEN publication |
| Synthetic flag | `MacroEngine.evaluate(..., synthetic=True)` default; `live_macro` may still label an empty pack synthetic | IMPLEMENTED. Synthetic → LIVE is rejected by this producer |
| Industry / company exposure coefficients | Design §§18–21. No approved coefficient, weight, or formula in code. Web reads `data.exposures[company_id]` and shows 미제공 when absent | DESIGNED_NOT_IMPLEMENTED and POLICY_BLOCKED |
| PIT fields observation_period, release_at, available_at, vintage_at, ingested_at | Design §23. ALFRED code keeps observation date and realtime available_at. release_at / vintage_at / ingested_at were not a stored contract | DESIGNED_NOT_IMPLEMENTED on the base. This producer preserves them when the caller supplies them and does not invent the missing timestamps |
| `live_macro` CSV fallback | `validation/historical.py` | IMPLEMENTED on the base. Not used here. POLICY_BLOCKED for this producer (revised history must not rewrite a past decision) |
| Web macro shape | `product/web_assets/app.js` reads `data.state`, `data.regime`, `data.exposures[id]`. Producer `WEB_READS` also lists `indicators` | IMPLEMENTED as a reader. `state`/`regime` names match `MacroSnapshot`. `environment.indicators` → `indicators` is a rename PR #9 refused. POLICY_BLOCKED |
| Producer Infrastructure macro section | PR #9 registry: `MACRO_SHAPE_INCOMPATIBLE`. `adapters.macro_section` raises `IncompatibleShapeError` | IMPLEMENTED. Left unchanged |
| Track C macro boundary | `feature/track-c-evl` only: `MacroEngine.evaluate_stamped` requires exactly growth and inflation `StampedValue`s, then calls `evaluate`. Not on this base | DESIGNED_NOT_IMPLEMENTED on this branch (their method). This change does not edit `engine.py`, so their method remains the Track C addition |
| QGV / Technical / Portfolio / Leaderboard calculations | Untouched files. Fingerprint below | IMPLEMENTED and unchanged |

No new indicator, regime rule, weight, threshold, exposure coefficient, or scoring formula is introduced. The research path calls `collect_indicators_alfred` and `MacroEngine.evaluate` as they already exist.

## Unresolved scope frozen with this baseline

These stay unresolved. This implementation does not define them.

| Unresolved item | Why it stays open |
|---|---|
| v0.1.4 scenario / transmission / stress | Candidate record only. Engine keeps `candidate_not_applied` and does not build those objects |
| Company / industry exposure | Design describes exposure ≠ sensitivity and forbids freezing an unvalidated impact formula. No coefficient was approved |
| Web `indicators` mapping | PR #9 refuses to rename `environment.indicators` to `data.indicators`. That refusal is unchanged |
| `CURRENT_REVISED_NOT_ALFRED` | CSV tooling exists and is labeled revised history, not ALFRED. This producer rejects that vintage kind and does not call the CSV fallback |

