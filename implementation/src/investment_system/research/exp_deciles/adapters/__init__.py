"""Offline input adapters of EXP-STOCK-INDICATOR-DECILES-v1: already-approved raw sources -> engine input records.

RESEARCH ONLY. Every adapter is pure in the sense of the engine package: paths (or RAM objects) in, records out. No network
access of any kind, no file is written, nothing is printed (callers may print `bundle.count_lines`, which carries counts
only). Outputs are deterministic (sorted keys and rows; exact Decimals).

Settings doc (implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md sections 1-3, 5, 10.8) rules applied everywhere:
- a missing or unusable input is UNKNOWN with a fixed reason code; it is never turned into an exclusion and never filled
  with 0 (or with another day's, symbol's or source's value);
- a SEC issuer list or one day's IEX symbol list is never a historical population: the candidates are the caller's
  security map, and the bundle manifest says it is not a complete historical population;
- the IEX last regular-session trade is only an approximation of the S signal price (label
  IEX_LAST_REGULAR_TRADE_APPROX) and is never a T open; the Alpaca SIP daily-bar open is the consolidated open candidate
  for T; open and close are kept separate;
- the SPY total-return slot is an ETF auxiliary comparison only (no adapter here builds it).

Modules
  common      reason-code helpers, exact numbers, file sha256
  sec_bulk    SEC one-time collection assets (PR #460 plan: companyfacts.zip, submissions.zip,
              full-index-<y>-QTR<n>-form.idx.gz, fsds-<y>q<n>.zip with sub.txt) -> PIT companyfacts per CIK, as-filed SIC
              filing rows, single-class cover share counts, Form 25 / 15 termination evidence
  iex_signal  per-day IEX last-trade result held in RAM (providers/iex_hist.py shapes) -> S quote records
  alpaca_bars Alpaca SIP raw daily-bar pages (raw/<series>/page-NN.json) -> ledger price rows and coverage
  bundle      one S: records + terminations, quotes, companyfacts, filings, prices, the input manifest and a provenance
              document (source name, file sha256 and reason codes per item) with candidate / input-present / UNKNOWN counts
"""
