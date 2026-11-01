"""EXP-STOCK-INDICATOR-DECILES-v1 research engine (Main). RESEARCH ONLY, NOT OPERATIONS.

Settings: implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md sections 1-3 (owner 2026-11-01, fixed rules).

Selection inputs:
- settings   frozen constants and settings_sha256()
- schedule   annual S/T (third Monday of February), filing cutoff, usable_from, frozen schedule_v1.json
- pit        6th-session SEC cutoff applied to qgv.v2_factors.compute, per-row PIT record
- universe   security-type scope (common classes, ADR/ADS, REIT; owner 2026-10-30), issuer class-sum market cap (ADR:
             ordinary shares / ADR ratio x ADS price), representative security, U-A (entry/stay) and U-B membership
- scoring    calc 23.1 scoring of the U-A population at S for the four fixed presets ('default' is an alias)
- selection  top/bottom k = floor(N x 0.10) from one total order, N < 10 not run

Ledger side:
- ledger     T-open fills only, equal-weight restore, 10 bp per side, reserved corporate-action cash, LOSS / CARRY
- metrics    CAGR, MDD, volatility, turnover, cost attribution, month-end NAV, rolling 12/36/60/120-month windows,
             trailing 1/3/5/10-year returns (null with INSUFFICIENT_HISTORY), before/after-cost comparison
- benchmarks group equal-weight cell, external total-return index consumer (ETF labelled, French refused)

Run and handoff:
- runner     pure orchestration: selection stage of one signal year (records -> universe -> pit -> scoring -> selection,
             selection_inputs/1) and ledger stage over consecutive years (strategy x group x side portfolios plus the
             group equal-weight benchmark, LOSS / CARRY at 0 and 10 bp, metrics, optional external TR; ledger_outputs/1)
- handoff    input manifest parsing and sha256 verification, run_id, output manifest building and verification

Pure functions: no network, no data-provider call, no price stored. The only files read are the frozen schedule
(schedule.load_frozen) and the canonical scoring configs the qgv loaders read. implementation/tools/
exp_stock_indicator_deciles.py is the only IO layer (reads the hashed bundle, writes private 0600 outputs outside the
checkout). Codex's #417/#430 originals (research/qgv_backtest) are not imported; the ported pieces say so in their module
docstrings.
"""
