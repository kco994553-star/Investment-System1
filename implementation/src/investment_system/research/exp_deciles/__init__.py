"""EXP-STOCK-INDICATOR-DECILES-v1 research engine (Main). RESEARCH ONLY, NOT OPERATIONS.

Settings: implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md sections 1-3 (owner 2026-11-01, fixed rules).
Modules in this part (selection inputs):

- settings   frozen constants and settings_sha256()
- schedule   annual S/T (third Monday of February), filing cutoff, usable_from, frozen schedule_v1.json
- pit        6th-session SEC cutoff applied to qgv.v2_factors.compute, per-row PIT record
- universe   issuer class-sum market cap, representative security, U-A (entry/stay) and U-B membership
- scoring    calc 23.1 scoring of the U-A population at S for the four fixed presets ('default' is an alias)
- selection  top/bottom k = floor(N x 0.10) from one total order, N < 10 not run

Pure functions: no network, no data-provider call, no price stored. The only file read in this part is the frozen
schedule (schedule.load_frozen) and the canonical scoring configs the qgv loaders read. Codex's #417/#430 originals
(research/qgv_backtest) are not imported; the ported pieces say so in their module docstrings.
"""
