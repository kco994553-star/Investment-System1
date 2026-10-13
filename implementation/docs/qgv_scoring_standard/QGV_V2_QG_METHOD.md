# QGV v2 Q·G — SEC metric definitions, percentile rules and public file `sec-qgv2.json`

Status: **PROVISIONAL default · UNCALIBRATED** (user decision 2026-10-13; decision record **GSQ-022 pending approval**).
Spec: [QGV_V2_CANDIDATE.md](QGV_V2_CANDIDATE.md). v1 ([QGV_SCORING_STANDARD_v1.md](QGV_SCORING_STANDARD_v1.md),
`qgv/factors.py`, `qgv/raw_map.py`) is unchanged and keeps running beside v2.
Weights are the candidate defaults exactly. They were not tuned on past returns, and no Holdout data was used.

Code: `qgv/v2_factors.py` (SEC raw metrics), `qgv/v2_scoring.py` (percentiles, axes), `universe/sec_qgv2.py`
(rows, merge, publication, strict validator), `product/web_assets/sec-qgv2.js` (JS validator + reader, JS==Python
vectors `tests/fixtures/sec_qgv2_vectors_v1.json`, `tools/sec_qgv2_reference.py`, `tools/sec_qgv2_node_test.js`).

## 1. SEC inputs and period rules

All inputs come from one SEC companyfacts payload. Only facts filed on or before the acquisition date are used. Prices are never used.

- **Taxonomy and currency:** the taxonomy (`us-gaap` or `ifrs-full`) whose latest annual net-income/revenue fact is the most recent
  (`us-gaap` on a tie). Currency = the unit of
  the latest annual net-income/revenue fact (USD preferred on a tie). All amounts of a company use that one currency, and nothing is converted.
- **Annual flow:** a duration of 350–380 days from a 10-K, 10-K/A, 10-KT, 20-F or 40-F (and their amendments). FY0 = the latest
  annual end of net income, revenue, operating cash flow or EBIT. Year k = the annual fact ending within ±10 days of FY0 end minus k years,
  which absorbs 52/53-week years.
- **Instant (balance sheet):** the value at that year end (±10 days) from any 10-K/10-Q/20-F/40-F.
- **YTD:** a duration of 80–300 days from a 10-Q or 10-Q/A.
- **TTM:** FY0 + YTD(latest 10-Q of the new fiscal year) − YTD(same span one year earlier). TTM a year earlier uses FY−1 and the
  YTD two years earlier. FY0 and both YTD facts must come from **one concept**. Without such a later 10-Q, TTM = FY0 (period end = FY0 end).
- **Revisions:** for the same concept/unit/period, the latest `filed` wins. If two facts have the same `filed` date and different
  values, that period is dropped as ambiguous and never averaged.
- **Concept lists:** for each period the first concept in the list with a usable fact wins.

| Line | us-gaap (priority order) | ifrs-full |
|---|---|---|
| revenue | Revenues, RevenueFromContractWithCustomerExcludingAssessedTax, …IncludingAssessedTax, SalesRevenueNet, SalesRevenueGoodsNet, RevenuesNetOfInterestExpense | Revenue, RevenueFromContractsWithCustomers |
| gross profit | GrossProfit, else revenue − (CostOfRevenue, CostOfGoodsAndServicesSold, CostOfGoodsSold) | GrossProfit / CostOfSales |
| EBIT | OperatingIncomeLoss | ProfitLossFromOperatingActivities |
| pretax / tax | IncomeLossFromContinuingOperationsBeforeIncomeTaxes…(2 concepts) / IncomeTaxExpenseBenefit | ProfitLossBeforeTax / IncomeTaxExpenseContinuingOperations |
| net income | NetIncomeLoss, ProfitLoss | ProfitLossAttributableToOwnersOfParent, ProfitLoss |
| OCF / capex | NetCashProvidedByUsedInOperatingActivities(…ContinuingOperations) / PaymentsToAcquirePropertyPlantAndEquipment, PaymentsToAcquireProductiveAssets | CashFlowsFromUsedInOperatingActivities / PurchaseOfPropertyPlantAndEquipment(…ClassifiedAsInvestingActivities) |
| D&A | DepreciationDepletionAndAmortization, DepreciationAmortizationAndAccretionNet, DepreciationAndAmortization | DepreciationAndAmortisationExpense, AdjustmentsFor… |
| interest expense | InterestExpense, InterestExpenseNonoperating, InterestExpenseDebt, InterestAndDebtExpense | FinanceCosts, InterestExpense |
| net interest income | InterestIncomeExpenseNet | InterestIncomeExpenseNet, NetInterestIncomeExpense |
| diluted EPS / shares | EarningsPerShareDiluted, …BasicAndDiluted / WeightedAverageNumberOfDilutedSharesOutstanding, …ShareOutstandingBasicAndDiluted | DilutedEarningsLossPerShare / AdjustedWeightedAverageShares |
| assets / equity | Assets / StockholdersEquity, …IncludingPortionAttributableToNoncontrollingInterest | Assets / EquityAttributableToOwnersOfParent, Equity |
| cash | CashAndCashEquivalentsAtCarryingValue, CashCashEquivalentsRestrictedCash…, Cash | CashAndCashEquivalents |
| total debt | LongTermDebt (incl. current maturities), else LongTermDebtNoncurrent or LongTermDebtAndCapitalLeaseObligations (+ LongTermDebtCurrent / …CapitalLeaseObligationsCurrent when reported); plus ShortTermBorrowings, else CommercialPaper. If the noncurrent path has no current-maturities line but `DebtCurrent` is reported, debt = noncurrent + DebtCurrent (no separate short-term add, to avoid double counting). If none of these lines is reported, debt is NA. | Borrowings, else NoncurrentPortionOfNoncurrentBorrowings/NoncurrentBorrowings (+ CurrentPortionOfNoncurrentBorrowings); plus ShorttermBorrowings/CurrentBorrowings |

Derived lines: tax rate = income tax ÷ pretax income, clamped to 0–50%, when pretax > 0. Otherwise the default 21% applies
(DEFAULT_TAX_RATE, uncalibrated). NOPAT = EBIT × (1 − tax rate). Invested capital (IC) = equity + total debt − cash (must be > 0).
"Average" = (opening + closing) / 2 when both balances exist, else the closing balance. FCF = OCF − capex.

## 2. Factors and raw metrics (GENERAL profile)

A factor score is the mean of the percentiles of the sub-metrics that are available. ↑ = higher is better, ↓ = lower is better.

| Factor (weight) | Sub-metric (published key) | Definition | Dir. | NA when |
|---|---|---|---|---|
| `q_profitability` (25) | `roic` | NOPAT₀ / average IC | ↑ | IC ≤ 0 or any input missing |
| | `gross_profit_to_assets` | gross profit₀ / assets₀ | ↑ | assets ≤ 0 |
| `q_moat_proxy` (20) | `moat_proxy` | ROIC over FY0..FY−4 (≥ 3 years): mean μ, population std σ; μ × max(0, 1 − σ/μ) when μ > 0, else μ. Also published: `moat_return_mean_5y`, `moat_return_std_5y`, `moat_return_years` | ↑ | < 3 ROIC years |
| `q_earnings_quality` (20) | `accruals_to_assets` | (NI₀ − OCF₀) / average assets | ↓ | missing |
| | `fcf_to_net_income` | FCF₀ / NI₀ | ↑ | NI₀ ≤ 0 |
| `q_financial_safety` (20) | `net_debt_to_ebitda` | (debt₀ − cash₀) / (EBIT₀ + D&A₀) | ↓ | EBITDA ≤ 0 or debt not reported |
| | `interest_coverage` | EBIT₀ / interest expense₀ | ↑ | interest ≤ 0 or missing |
| `q_capital_allocation` (15) | `dilution_3y` | (diluted shares₀ / diluted shares₋₃)^(1/3) − 1 | ↓ | missing |
| | `incremental_roic_5y` | (NOPAT₀ − NOPAT₋₅) / (IC₀ − IC₋₅) | ↑ | IC did not grow |
| `g_revenue_growth` (25) | `revenue_cagr_3y` | (rev₀ / rev₋₃)^(1/3) − 1 | ↑ | either ≤ 0 |
| `g_per_share_growth` (25) | `eps_cagr_3y` | diluted EPS 3-year CAGR | ↑ | either ≤ 0 |
| | `fcf_per_share_cagr_3y` | (FCF / diluted shares) 3-year CAGR | ↑ | either ≤ 0 |
| `g_growth_efficiency` (20) | `incremental_roic_3y` | (NOPAT₀ − NOPAT₋₃) / (IC₀ − IC₋₃) | ↑ | IC did not grow |
| `g_consistency` (15) | `revenue_positive_growth_share` | share of positive revenue YoY over FY−5→FY0 (≥ 3 YoY values) | ↑ | < 3 values |
| | `revenue_growth_volatility` | population std of those YoY values | ↓ | < 3 values |
| `g_recent_acceleration` (15) | `revenue_acceleration` | TTM revenue YoY (`revenue_ttm_growth`) − `revenue_cagr_3y` | ↑ | either missing |

Two G/Q factors use incremental ROIC over different windows: capital allocation uses 5 years and growth efficiency uses 3 years.
Earnings surprise is **omitted** because there is no free consensus source (`method.earnings_surprise = OMITTED_NO_FREE_SOURCE`).

## 3. FINANCIAL profile

The repository's existing FINANCIAL inputs (CET1 and NIM in `raw_map`) are not available from companyfacts, so this minimal
SEC-derivable set is defined instead. The profile is decided by SEC SIC **6000–6499**: banks, credit, brokers and insurance. Real estate
and holding offices (6500–6799) stay GENERAL inside the `finance_real_estate` group. A missing SIC means GENERAL.

| Factor | FINANCIAL sub-metrics |
|---|---|
| `q_profitability` | `roe` = NI₀ / average equity ↑, `roa` = NI₀ / average assets ↑, `net_interest_income_to_assets` = net interest income₀ / average assets ↑ (NIM proxy) |
| `q_moat_proxy` | the same formula on ROE (FY0..FY−4) |
| `q_earnings_quality` | not defined for financials, always NA (OCF mixes funding flows); the axis renormalizes over the other 80 points |
| `q_financial_safety` | `equity_to_assets` ↑ (capital-ratio proxy; CET1 is not in companyfacts) |
| `q_capital_allocation` | `dilution_3y` ↓, `incremental_roe_5y` = ΔNI / Δequity over 5 years ↑ |
| `g_per_share_growth` | `eps_cagr_3y` ↑, `book_value_per_share_cagr_3y` (equity / diluted shares) ↑ |
| `g_growth_efficiency` | `incremental_roe_3y` ↑ |
| revenue, consistency, acceleration | same as GENERAL |

FINANCIAL rows are ranked **only among FINANCIAL rows**, for both Q and G. If there are fewer than 8 of them, the axis is NA with `PEERS_BELOW_MINIMUM`.

## 4. Percentile and peer rules

- **Cross-section:** Universe504 rows in LIVE or STALE state at publication time, **one point per CIK** (GOOG and GOOGL count once).
  It accumulates over the 7-day rotation and is recomputed every time the file is written. Published as `cross_section_size` and `cross_section_by_profile`.
- **Own point replaced:** each row is ranked with its own issuer's point replaced by its own values. For a TARGET row (fresher than its
  Universe row) this means "ranked as if it were that issuer's point today". ASML and other non-Universe TARGET issuers are added as an extra point.
- **Peers:** GENERAL Q factors use the same SIC industry group (`sic_industry_groups/v0`) when the group has **≥ 8** issuers
  (`INDUSTRY_GROUP`). Otherwise they use the whole GENERAL universe (`UNIVERSE_FALLBACK`). GENERAL G factors use the whole GENERAL universe (`UNIVERSE`).
  FINANCIAL rows use `FINANCIAL_PROFILE`. `peer_count` per axis counts issuers in that set, the row itself included.
- **Percentile:** 100 · (less + (equal − 1)/2) / (n − 1) over the peer values that exist (average rank for ties, 0–100). Lower-is-better
  metrics are negated first. A sub-metric needs **n ≥ 8** values, else it is NA.
- **Axis:** weighted mean of the available factor scores, with weights renormalized over the available factors. If less than 50% of the
  axis weight is available, the axis is NA with `AXIS_COVERAGE_BELOW_50`. `factors_available` ("n/5") and `available_weight` are always
  published. Missing values are **never 0**: an absent metric key, a `null` factor or a `null` score means NOT_AVAILABLE.
- **Choice of N = 8:** a fixed, uncalibrated minimum. With 8 points the percentile step is 14.3, coarse but not degenerate.

## 5. Public file `sec-qgv2.json`

Top level: `schema_version 1`, `kind SEC_QGV2`, `as_of`, `standard QGV_V2`, `standard_status PROVISIONAL_DEFAULT_UNCALIBRATED`,
`decision_ref GSQ-022_PENDING_APPROVAL`, `method` (weights, min_peers 8, axis_coverage_min_percent 50, percentile rule, SIC config,
financial SIC range, cross-section rule, earnings-surprise omission), `config_version/config_status` (shared `sec-universe-shares/v0`,
14-day stale window, 7 shards), `freshness_basis`, `stale_after_seconds`, `shard_count`, `last_shard_index`, `registry_sha256`,
`code_count 504`, `cross_section_size`, `cross_section_by_profile`, `state`, `reason_codes`, `records` (504 Universe codes) and
`target` (19 TARGET ids; `hanmi` and `tokyo_electron` are `NON_SEC_ISSUER`).

Row: `cik`, `acquired_at`, `source_sha256{companyfacts,submissions}`, `state` (LIVE/STALE/NOT_AVAILABLE), `reason_codes`, `sic`,
`industry_group`, `profile`, `fiscal_year_end`, `currency`, `metrics` (sparse; 6 significant digits), `factors` (10 ids → 0–100 | null),
`axes{Q,G}{score, factors_available, available_weight, peer_basis, peer_count, reason_codes}`, `v_inputs_v2`.

`v_inputs_v2` holds the price-free inputs the device needs to compute V in RAM. Amounts are exact SEC values in the row currency.
- `ebit`, `fcf`: `{fy_value, fy_end, ttm_value, ttm_end}`. FCF = OCF − capex for the same period.
- `total_debt`, `cash_and_equivalents`: `{value, period_end}`, each at its own latest balance-sheet date (they can differ). Debt uses the same rule as section 1.
- `diluted_shares`: `{value, period_end}`, the latest weighted-average diluted share count (quarter or year).
- `ebit_per_share_history`, `fcf_per_share_history`: up to 5 fiscal years `{fiscal_year_end, value}`, oldest first. These feed the own-history multiple percentile.
- `revenue_cagr_3y`, `eps_cagr_3y`, `fcf_per_share_cagr_3y`, `revenue_ttm_growth`: realized growth for the expectation check.
- Also: `currency`, `taxonomy`, `fiscal_year_end`.

Size: about 0.6 MB with every row empty, and about 1.3–1.5 MB with all 504 rows populated (synthetic test). The public limit is 2 MiB.
Validators: Python `require_qgv2` (Pages guard `qgv2_boundary`) and JS `SecQgv2.validate`. Both recompute **every** factor and axis score
and every peer count from the published metrics, and reject any mismatch, price/rank key or zero-fill.

## 6. Daily operation (no new SEC request, no workflow change)

1. `public_screens_pipeline.py --live` (TARGET step): after the six screen files, it computes TARGET rows from the same TARGET SEC
   bytes and stages `sec-qgv2.json` with Universe rows `NOT_COLLECTED`. TARGET axes are `PEERS_BELOW_MINIMUM` at this point.
   Log: `SEC_QGV2_TARGET staged companies=… with_data=…` or `SEC_QGV2_TARGET STAGE_FAILED`.
2. `sec_universe_shares.py --live` (shard step): reads the staged TARGET rows, fetches the previous Pages copy (404 → fresh,
   invalid → discarded, network failure → nothing written, exit 1, same as the other two files), restores it, then merges today's
   shard rows from the bytes it already fetched. It recomputes all percentiles and writes the file. A v2 failure prints
   `SEC_QGV2 OUTPUT_FAILED previous_kept` and never changes the shares or Q·G v1 files.
   Log: `SEC_QGV2 shard=i/7 codes=… with_data=… live=… stale=… not_available=… cross_section=… q_scored=… g_scored=… target_live=… target_q_scored=… target_g_scored=…`.
3. `cockpit-pages` (UI deploy): `sec_universe_shares.py --preserve-only` restores the previous copy. Offline builds do not publish
   the file (404, `empty_public_screens.js` ABSENT).

## 7. Open questions (for GSQ-022)

- N = 8 minimum peers, the 21% fallback tax rate and the moat formula μ·max(0, 1 − σ/μ) are uncalibrated defaults.
- FINANCIAL uses SIC 6000–6499. Whether REITs (6798) or payment networks (7389) should move needs a decision.
- The debt definition excludes operating leases. Debt-free issuers with no debt concept get NA ROIC and net-debt/EBITDA rather than 0.
- No earnings-surprise sub-metric. Add one only if a free source is approved.
- The first week after launch has a partial cross-section (about 72 issuers per day). Peer bases fall back to the universe until each group reaches 8.
