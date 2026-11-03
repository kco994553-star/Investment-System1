# 계층 3 기술적 분석 리더보드 연구 설정·Main 인계

Owner instruction: 2026-11-03. Research base #467 `745b143a61ef4f2eaa450497ccb603ab9c149bb0`;
shared normalization originated in #461 `6d6fd7faad7415b2b0c2dbfc1a4361d73c688c6f`.
This is a research calculation/proposed handoff, not an application contract change or a strategy performance result.
Main owns screen/reader integration. No actual company price, metric, source hash or result is included here.

## Scope and chosen implementation

Reuse `exp_deciles/adapters/alpaca_normalization.py`, `liquidity.summarize`, the canonical NYSE schedule,
and `selection.select` for the approved extreme-decile order. Add research-only measurement and board modules.
Replacing the common technical screen/engine would cross Main's ownership and is unnecessary.
The owner delegated fixing the six-month formula and middle-bin allocation before comparisons; the choices below
are project settings chosen for this task, not a claim about a book's exact strategy.

## Settings frozen before results

- Signal S is a completed NYSE session. The held-sample run fixes S=2018-02-16 and its original request-series inventory
  before measuring. U-A and U-B are separate dated membership snapshots; unknown membership is never an empty group.
- Subtract calendar months with end-of-month clipping. Momentum anchor is the last NYSE session on/before S−3/6/12 months.
  Price momentum = `(P[S]−P[anchor])/P[anchor] × 100`, no skipped month. Require every expected close in [anchor,S].
- Volatility: daily simple returns `(P[t]−P[previous session])/P[previous session]` for sessions in `(S−6 calendar months,S]`.
  Include the previous-session close needed by the first return. Require every expected return and both closes, at least 2 returns.
  Sample standard deviation `sqrt(sum((r−mean(r))²)/(n−1)) × 100`; **ddof=1, not annualized**, unit percent per day.
- Prices are raw. Economic price metrics require dated identity and confirmed no-split evidence covering the entire requested window.
  Where that evidence is missing, preserve raw-series arithmetic separately; do not call it an adjusted security return.
  Split-affected series need a separately validated common-engine adjustment before adoption; no inferred ratio adjustment is added here.
  Cash dividends are excluded (price return, no reinvestment); dividend-related price moves remain in returns.
- Six-month dollar volume uses `(S−6 calendar months,S]`, one VWAP×volume per expected session. Both must be from the same original
  raw bar and an explicitly evidenced matching trade scope; confirmed USD is also required. Provider-rounded VWAP remains an approximation.
  The primary mean requires 100% coverage. Observed-day means and close×volume proxies have separate diagnostic fields and never fill it.
- Arithmetic: Decimal precision 50 for price returns/volatility and ordering; preserve unrounded decimal strings.
  Existing liquidity arithmetic is reused at its original precision 28. Display rounding is downstream only.

## Groups, ranks and independent predicates

- A group fixes `group_id`, `signal_day`, complete `member_security_ids`, and `membership_source` before ranking.
  Fixed security IDs are required; neither tickers nor issuer CIKs are promoted to security IDs. Metric eligibility is independent.
- Each metric's N counts the group's finite, adopted values. Rank 1 is the **largest measured value**, ties by fixed security ID ascending.
  High volatility is D10, without a desirability sign flip. QGV is joined by fixed ID + S, never blended into these five measures.
- For N≥10, reuse `k=floor(N×0.10)` and the one total order: first k=D10, last k=D1. Set R=N−2k, q=R//8, r=R%8.
  D9..D2 each get q names; the first r bins in that descending bin order get one extra name. Ties may cross a bin boundary by fixed ID.
  Example N=23: counts D10..D1 are **2,3,3,3,2,2,2,2,2,2**. N<10 retains ordinal ranks/median but all deciles/top-bottom flags are null.
- Median is the central unrounded value, or arithmetic mean of the central pair. `gt_zero`, `ge_median`, `gt_median`, `top_decile`
  are independent. Screen “중앙값 이상” is `>=`; a book strategy's “중앙값 초과” is `>`. Neither implies return >0.
- Filters only select rows from the frozen board; never rebuild N/median/ranks/deciles after filtering.
  `exclude_D10` passes only a present decile in D1..D9. Missing volatility, unknown groups and N<10 do not pass this condition.
- If U-A/U-B membership is unavailable, N/rank/median/decile and relative predicates are null with `GROUP_MEMBERSHIP_UNCONFIRMED`.
  Raw measurements and absolute predicates can still be computed independently. A request-series sample is not U-A/U-B or a security universe.

## Proposed fields for Main

The additive research schema is `technical-leaderboard/1`; it is not a new field inserted into `lab-backtest-v1`.
Main can adapt it in a separately versioned application contract. Actual rows remain private.

| Field | Type / unit / meaning |
|---|---|
| `signal_day`, `settings_version`, `settings_sha256` | date; pinned research settings and hash |
| `series_id`, `symbol`, `security_id`, `identity_status` | original request identity, display symbol, nullable fixed ID, evidence level |
| `metrics.momentum_3m/6m/12m.value` | decimal string or null, percent |
| `metrics.volatility_6m.value` | decimal string or null, percent per day; sample stdev, nonannualized |
| `metrics.dollar_volume_6m.value` | decimal string or null, USD/trading day; complete matched-scope mean |
| each metric: `raw_value`, `null_reasons` | separate raw arithmetic; reasons preventing primary adoption |
| each metric: `window_start`, `window_end`, `anchor_day` | calendar boundary; effective anchor if needed |
| each metric: `observed_days`, `expected_days`, `observation_unit` | close count, return count or trading-day count; never conflate them |
| volatility: `observed_price_days`, `expected_price_days` | prices needed for the consecutive daily returns |
| volume: `mean_observed`, `close_volume_proxy`, `trade_scope_status` | separate diagnostics, never primary fallbacks |
| `group_id`, `membership_status`, `membership_source`, `population_hash` | dated original comparison group and identity |
| board `metrics.<id>.n_valid`, `.n_members`, `.median`, `.k` | per-metric eligible N, original member count, median, extreme-bin size |
| board `metrics.<id>.rows[].rank`, `.decile`, `.null_reasons` | descending ordinal, D1..D10 integer or null, missing reason |
| row `conditions` | nullable booleans `gt_zero`, `ge_median`, `gt_median`, `top_decile`, `bottom_decile`, `exclude_D10` |
| `qgv_join_key` | `[signal_day, security_id]`; null without fixed ID. QGV values/scores remain independent |

Public synthetic examples will accompany the implementation: N=23 with middle-bin remainder, tied negative returns,
N=9, unknown membership, and missing volatility during D10 exclusion. They use `SYNTHETIC:*` IDs and generated prices only.

## Validation and privacy

Tests cover time boundaries, missing prior close/no gap bridging, constant and known returns, split/currency/scope gates,
independent metric N, exact ties, N=9/10/11/23, unknown membership, and filtering without reranking.
The real held-sample run separately compares prior AMD momentum and complete liquidity coverage, and validates new volatility
with an independent sample-stdev calculation. Inventory counts distinguish requested series, documented identities, fixed IDs,
raw arithmetic validity and adopted metric validity. No new provider collection, execution-branch push, merge or deployment.
