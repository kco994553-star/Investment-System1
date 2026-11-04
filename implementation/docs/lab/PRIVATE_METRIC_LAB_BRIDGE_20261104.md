# Preserved metric to Lab v2

The #454 → #464 → #465 → #467 chain already contains the approved engine, adapters and CPI-2025 configuration. Its `select`/`ledger` CLI defaults to `cpi-2025-v1`; the preserved standalone #454 nominal path is not the current approved entry point. No branch is merged by this work.

The actual gap is export of an already verified one-company result to Main's `lab-backtest-v2` reader (#471), not a new score or backtest. Run:

```
python implementation/tools/exp_stock_indicator_deciles.py lab-metric \
  --result <preserved-private-metric.json> --expected-sha256 <verified-source-digest> \
  --out <new-private-directory>
```

The input is the preserved `SINGLE_COMPANY_METRIC` evidence format: signal_day, full calculation code_reference and finite EV/sales value. Its digest must match the previously preserved evidence. The CLI requires a clean code tree and writes 0600 files outside Git, refusing overwrite. `lab-evidence.json` distinguishes the original calculation SHA from this export SHA and marks `recalculated=false`.

`lab-backtest-v2.json` contains one computed company-count diagnostic. The ratio and identity stay in the source evidence because Main's existing v2 diagnostic contract accepts only counts/fractions. No period, costs, selection, ledger, return, curve or PIT-population claim is invented. The settings hash in evidence records context, not application of market-cap rules to a raw metric.

Main integration: existing v2 fields only; no contract or screen changes requested. Private authenticated serving remains Main's #436 responsibility. No public endpoint or publish permission is added.
