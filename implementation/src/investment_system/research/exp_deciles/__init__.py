"""EXP-STOCK-INDICATOR-DECILES-v1 research engine (Main). RESEARCH ONLY, NOT OPERATIONS.

Settings: implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md sections 1-3 (owner 2026-11-01, fixed rules).

Selection inputs:
- settings   frozen constants and settings_sha256(), including the version and content hash of every scoring config
             (type_config/1, dcf parameters, playbook, SIC industry groups)
- schedule   annual S/T (third Monday of February), filing cutoff, usable_from, frozen schedule_v1.json
- pit        6th-session SEC cutoff applied to qgv.v2_factors.compute, per-row PIT record; a row without an as-filed SIC
             keeps SIC_AS_FILED_NOT_AVAILABLE and is scored as calc 23.1 does (GENERAL, industry NA)
- universe   security-type scope (common classes, ADR/ADS, REIT; owner 2026-10-30), issuer class-sum market cap (ADR:
             ordinary shares / ADR ratio x ADS price) from share counts usable at S on a confirmed split basis,
             representative security, U-A (entry/stay, UNKNOWN units and their class IDs carried to the next S,
             terminations only when effective at S) and U-B membership
- scoring    calc 23.1 scoring of the U-A population at S for the four fixed presets ('default' is an alias)
- selection  top/bottom k = floor(N x 0.10) from one total order, N < 10 not run

Ledger side:
- ledger     T-open fills only, equal-weight restore, 10 bp per side, reserved corporate-action cash, LOSS / CARRY,
             settlement entitlement fixed at the effective date (spin-offs inside a deferred-delivery window included),
             per-security conflicts (owner-first same-day order, circular chains recorded), ADR depositary fees,
             terminal valuation at the next reselection T open
- metrics    measured from the first selected rebalance's T (unfilled years are cash), CAGR, daily MDD / volatility
             only with daily price coverage (else null, DAILY_PRICES_NOT_SUPPLIED), endpoint metrics null on a stale
             terminal mark, calendar years from fresh boundaries with partial years marked, monthly metrics on month-end
             NAV (IR against the group equal weight, Sharpe / Sortino with a verified risk-free series), turnover, cost
             attribution, month-end NAV with the base-100 reported index, rolling 12/36/60/120-month windows, trailing
             1/3/5/10-year returns on complete reselection cycles, before/after-cost comparison
- benchmarks group equal-weight cell, external series bound to the SPY total-return ETF auxiliary slot (no S&P 500 index
             total return is ever claimed), previous-close fallbacks only from the immediately preceding session

Run and handoff:
- runner     pure orchestration: selection stage of one signal year (records -> universe -> pit -> scoring -> selection,
             selection_inputs/1) and ledger stage over consecutive years (strategy x group x side portfolios plus the
             group equal-weight benchmark, LOSS / CARRY at 0 and 10 bp, metrics, optional external TR; ledger_outputs/1)
- handoff    input manifest parsing and sha256 verification, run_id, run block and output manifest with the settings
             body and a reproduction command, output manifest verification
- synthetic  the invented bundle of the CLI `synthetic` command and the tests

Pure functions: no network, no data-provider call, no price stored. The only files read are the frozen schedule
(schedule.load_frozen) and the canonical scoring configs the qgv loaders read. implementation/tools/
exp_stock_indicator_deciles.py is the only IO layer (reads the hashed bundle, writes private 0600 outputs outside the
checkout). Codex's #417/#430 originals (research/qgv_backtest) are not imported; the ported pieces say so in their module
docstrings.
"""
