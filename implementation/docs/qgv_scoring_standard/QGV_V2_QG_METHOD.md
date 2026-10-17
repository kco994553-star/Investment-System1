# QGV v2 Q·G — SEC metric definitions, percentile rules and public file `sec-qgv2.json`

Status: **PROVISIONAL default · UNCALIBRATED** (user decision 2026-10-13; decision record **GSQ-022 approved 2026-10-13**).
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
| revenue | Revenues, RevenueFromContractWithCustomerExcludingAssessedTax, …IncludingAssessedTax, SalesRevenueNet, SalesRevenueGoodsNet, RevenuesNetOfInterestExpense, RegulatedAndUnregulatedOperatingRevenue (utilities, last) | Revenue, RevenueFromContractsWithCustomers |
| gross profit | GrossProfit, else revenue − (CostOfRevenue, CostOfGoodsAndServicesSold, CostOfGoodsSold) | GrossProfit / CostOfSales |
| EBIT | OperatingIncomeLoss, else rule **EBIT** (GENERAL) | ProfitLossFromOperatingActivities, else rule **EBIT** (GENERAL) |
| pretax / tax | IncomeLossFromContinuingOperationsBeforeIncomeTaxes…(2 concepts), else fallback **F1** / IncomeTaxExpenseBenefit | ProfitLossBeforeTax / IncomeTaxExpenseContinuingOperations |
| net income | NetIncomeLoss, ProfitLoss | ProfitLossAttributableToOwnersOfParent, ProfitLoss |
| OCF / capex | NetCashProvidedByUsedInOperatingActivities(…ContinuingOperations) / PaymentsToAcquirePropertyPlantAndEquipment, PaymentsToAcquireProductiveAssets, else fallback **F3** | CashFlowsFromUsedInOperatingActivities / PurchaseOfPropertyPlantAndEquipment(…ClassifiedAsInvestingActivities) |
| D&A | DepreciationDepletionAndAmortization, DepreciationAmortizationAndAccretionNet, DepreciationAndAmortization, then rule **F2** | DepreciationAndAmortisationExpense, AdjustmentsFor… |
| interest expense | InterestExpense, InterestExpenseNonoperating, InterestExpenseDebt, InterestAndDebtExpense | FinanceCosts, InterestExpense |
| net interest income | InterestIncomeExpenseNet | InterestIncomeExpenseNet, NetInterestIncomeExpense |
| diluted EPS / shares | EarningsPerShareDiluted, …BasicAndDiluted / WeightedAverageNumberOfDilutedSharesOutstanding, …ShareOutstandingBasicAndDiluted | DilutedEarningsLossPerShare / AdjustedWeightedAverageShares |
| assets / equity | Assets / StockholdersEquity, …IncludingPortionAttributableToNoncontrollingInterest | Assets / EquityAttributableToOwnersOfParent, Equity |
| cash | CashAndCashEquivalentsAtCarryingValue, CashCashEquivalentsRestrictedCash…, Cash | CashAndCashEquivalents |
| total debt | LongTermDebt (incl. current maturities), else LongTermDebtNoncurrent or LongTermDebtAndCapitalLeaseObligations (+ LongTermDebtCurrent / …CapitalLeaseObligationsCurrent when reported); plus ShortTermBorrowings, else CommercialPaper. If the noncurrent path has no current-maturities line but `DebtCurrent` is reported, debt = noncurrent + DebtCurrent (no separate short-term add, to avoid double counting). If none of these lines is reported, debt is NA unless rule **NODEBT** applies. | Borrowings, else NoncurrentPortionOfNoncurrentBorrowings/NoncurrentBorrowings (+ CurrentPortionOfNoncurrentBorrowings); plus ShorttermBorrowings/CurrentBorrowings |

**Fallback lines (us-gaap only; added 2026-10-14 after the 10-K number check
[QGV_V2_NUMBER_CHECK_20261014.md](QGV_V2_NUMBER_CHECK_20261014.md) §7 items 2, 3, 5).** They apply per fiscal year, read the
same annual facts as above (PIT, revision and ±10-day rules), and need every component they name: a missing component is never
taken as 0, so the line stays NA. ifrs-full has no fallback lines. Code: `_Company.annual_hit` in `qgv/v2_factors.py`.

- **F1 pretax income (DECK):** when neither pretax concept is reported for the year, pretax =
  `IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic` + `…Foreign`, both for the same span. A domestic-only filer
  keeps NA (default 21% tax rate). A reported total always wins.
- **F2 D&A = `Depreciation` + `AmortizationOfIntangibleAssets`** (same span, both ≥ 0) in exactly two cases:
  (a) no D&A concept of the list is reported for the year (EME: 67.4 + 119.1); or
  (b) the D&A concept the list selected equals `Depreciation` within 0.5% **and** the intangible amortization is larger than
  that total, so the total cannot contain it (FIX: `DepreciationAndAmortization` 62.4 = `Depreciation` 62.379, amortization
  79.6 → D&A 142.0). Otherwise the selected total is kept: when the amortization is smaller than a total equal to `Depreciation`
  (BBY 831 vs 14), the total may already include it, so nothing is added (no double count). One component alone is not D&A.
- **F3 capex fallback:** when neither capex concept is reported for the year, one of `PaymentsToAcquireOtherProductiveAssets`
  (INCY), `PaymentsToAcquireMachineryAndEquipment` (RL FY2026), `PaymentsForCapitalImprovements` (GLW, SNA, IT),
  `PaymentsToAcquireOtherPropertyPlantAndEquipment` (LLY, WEC, ADP) — **only if exactly one of these four is reported for the
  year and none of the partial capex lines is**: oil-and-gas property (`PaymentsToAcquireOilAndGasProperty`,
  `…OilAndGasPropertyAndEquipment`, `PaymentsToExploreAndDevelopOilAndGasProperties`), real estate (`PaymentsToAcquireRealEstate`,
  `…CommercialRealEstate`, `…ResidentialRealEstate`, `…OtherRealEstate`, `PaymentsToDevelopRealEstateAssets`,
  `PaymentsForTenantImprovements`, `PaymentsToAcquireBuildings`, `PaymentsToAcquireLand`), `PaymentsForConstructionInProcess`,
  `PaymentsToAcquireTimberlands`, `PaymentsToAcquireFurnitureAndFixtures`, `PaymentsForProceedsFromProductiveAssets` (net of
  disposals). Two or more such lines mean each is a part of capex (LNT utility + other, EOG, HST, REITs), so capex stays NA.
  TTM still uses one concept: the fallback concept's own 10-Q YTD facts (RL tags its 10-Qs with another concept, so its TTM FCF
  stays NA while FY FCF resolves). Capitalized software is added by rule **SW** below.

**Rules from the owner decisions of 2026-10-15** (Q-247 approved; code in `qgv/v2_factors.py`, tests in
`tests/test_sec_qgv2.py`). Like F1–F3 they apply per fiscal year, read only SEC facts filed on or before the cutoff, and never
take a missing component as 0. They apply to SEC companyfacts only; the DART adapter (`product/dart_qgv2.py`) is unchanged.

- **SW capitalized software in capex (Q-SW = include).** Capex = the physical capex line of the year (the priority list, else
  F3) + capitalized software of **the same span**: `PaymentsForSoftware` alone when reported (it is the total), else
  `PaymentsToAcquireSoftware` + `PaymentsToDevelopSoftware` (each one that is reported, each ≥ 0). No double count:
  (a) nothing is added to `PaymentsToAcquireProductiveAssets`, whose us-gaap definition already includes software and other
  intangibles; (b) by definition `PaymentsToAcquirePropertyPlantAndEquipment` is physical assets and the software elements are
  intangible assets, so they are separate lines; but when the issuer also reports `PaymentsToAcquireProductiveAssets` for the
  span and that total is smaller than PP&E + software (0.5% tolerance), the software is taken to be inside the PP&E line and is
  not added. Software alone (no physical capex line) is not capex: NA. TTM capex = TTM of the physical line + TTM of each
  software line, only when all of them end on the same date; otherwise TTM capex is NA and FY is kept (MA: FCF −4.2%).
  **Known limitation (owner decision Q-0415-MISC, 2026-10-15):** the double-count guard can only be confirmed when the issuer
  also reports a `PaymentsToAcquireProductiveAssets` total for the span. Without that total, nothing in companyfacts shows
  whether an issuer's PP&E line already contains software, so the rule relies on the us-gaap element definitions (physical vs
  intangible) and cannot fully rule out a double count.
  Test: `test_capex_includes_capitalized_software_without_double_count`.
- **MAA REIT capital improvements (Q-MAA = exclude for SIC 6798).** For an issuer with SEC SIC **6798** (REIT),
  `PaymentsForCapitalImprovements` is never the F3 fallback line and counts as a partial capex line: when it is reported, F3
  capex is NA (MAA tags real-estate development as `PaymentsToAcquireInProcessResearchAndDevelopment`, so capital improvements
  alone were a partial capex: FCF 717.9 instead of about 446). Other issuers keep F3 as before (GLW, SNA, IT); a REIT's
  reported PP&E capex and its other single fallback lines are unchanged. Test: `test_reit_capital_improvements_are_never_the_capex_fallback`.
- **RSG issuer exception (Q-RSG = issuer exception).** `ISSUER_CONCEPT_EXCEPTIONS` in `v2_factors.py` is an explicit,
  CIK-keyed list (us-gaap only). For a listed issuer the named line reads **only** the listed concepts, so its years never mix
  two revenue bases; a year without them is NA. One entry: RSG (CIK 0001060391) revenue =
  `RevenueFromContractWithCustomerExcludingAssessedTax` (income statement 16,591), because its `Revenues` is the segment-note
  total before intercompany eliminations (19,027). Gross profit (revenue − cost) and operating margin follow. This is not a
  blanket "income-statement revenue first" rule: for most of the 19 issuers whose `Revenues` exceeds `RevenueFromContract…`
  by more than 5% (REITs such as AMT, CCI, ESS, UDR) `Revenues` is the right total. A new entry needs an owner decision.
  Test: `test_rsg_issuer_exception_uses_income_statement_revenue_only_for_the_listed_cik`.
- **NODEBT debt-free issuers (Q-NODEBT = conditional).** Applies at a fiscal-year-end balance sheet (FY0..FY−5, and for
  `v_inputs_v2.total_debt` at FY0) only when none of the debt lines above gives a value. us-gaap only. Debt is **0** when all hold:
  (a) a balance sheet exists at that date (total assets or equity); (b) no debt line and no other borrowing concept has a
  non-zero value at that date — `ConvertibleDebt(…Noncurrent/Current)`, `ConvertibleNotesPayable(…Current)`,
  `ConvertibleLongTermNotesPayable`, `ConvertibleSubordinatedDebt(…Noncurrent)`, `SeniorNotes(…Current/Noncurrent)`,
  `SeniorLongTermNotes`, `SeniorSubordinatedNotes`, `SubordinatedDebt`, `SubordinatedLongTermDebt`, `NotesPayable(…Current)`,
  `LongTermNotesPayable(…Current)`, `NotesAndLoansPayable(…Current)`, `LoansPayable(…Current)`, `LongTermLoansPayable`,
  `ShortTermBankLoansAndNotesPayable`, `BankOverdrafts`, `LineOfCredit`, `LongTermLineOfCredit(…Noncurrent)`,
  `LinesOfCreditCurrent`, `SecuredDebt(…Current)`, `SecuredLongTermDebt`, `UnsecuredDebt(…Current)`, `UnsecuredLongTermDebt`,
  `OtherLongTermDebt(…Noncurrent/Current)`, `OtherShortTermBorrowings`, `OtherBorrowings`, `DebtInstrumentCarryingAmount`,
  `DebtInstrumentFaceAmount`, `LongTermDebtFairValue`, `DebtLongtermAndShorttermCombinedAmount`, `DebtAndCapitalLeaseObligations`,
  `LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities` (a reported 0 is a reported zero, not a debt); (c) every
  interest-expense concept of that fiscal year (`InterestExpense`, `…Nonoperating`, `…Debt`, `InterestAndDebtExpense`, `…Other`,
  `…Borrowings`, `…LongTermDebt`, `…ShortTermBorrowings`, `…DebtExcludingAmortization`, `…RelatedParty`) is 0 or unreported.
  **Finance-lease liabilities only:** when (a) and (b) hold and `FinanceLeaseLiability` (or `CapitalLeaseObligations`) is
  reported, debt = that lease liability; without a total, `…Noncurrent` + `…Current` (both needed; one part alone is NA).
  Interest expense is then allowed only up to `FinanceLeaseInterestExpense` of the year (0.5% tolerance): it is the lease's
  interest. **결정(Q-0415-MISC, 2026-10-15): 운용리스는 부채에서 제외한다** (operating-lease liabilities are not debt; only
  finance-lease liabilities can stand in for debt here). **Decision Q-NODEBT-INT (2026-10-15): no materiality threshold.** Any
  non-zero interest expense not explained by the finance-lease interest keeps debt NA (EME 12.0M, INCY 2.4M and DECK 2.5M stay
  NA in the c21 recompute). Everything else keeps the previous rule (NA when the
  components are missing): an issuer that reports debt under another concept (DXCM-type convertible notes) or under its own
  extension tags, which companyfacts does not carry, with interest expense (ORCL, F, GM) is never treated as debt-free.
  MNST-type: a debt line reported at FY−1 but gone at FY0 gives FY0 debt 0 and `total_debt` at FY0, not the stale FY−1 amount.
  Test: `test_debt_is_zero_only_without_any_debt_concept_and_without_interest_expense`.
- **EBIT substitute (Q-EBIT = substitute approved).** For a fiscal year without reported operating income (`OperatingIncomeLoss`
  / `ProfitLossFromOperatingActivities`), EBIT = pretax income (incl. F1) + interest expense (the interest-expense line above),
  both for the same span and interest ≥ 0; a missing part leaves EBIT NA (never pretax + 0). A reported operating income always
  wins, so a filer with operating income for only some years mixes the two per year (ROK-type). TTM = TTM pretax + TTM interest
  when both end on the same date, else TTM EBIT is NA and FY stays. SEC **GENERAL** profile only: for banks and insurers
  (FINANCIAL) interest expense is an operating cost, so no substitute (the DART adapter always has operating income). Every value
  built from EBIT (NOPAT, ROIC, moat, incremental ROIC, interest coverage, net debt/EBITDA, `v_inputs_v2.ebit`,
  `ebit_per_share_history`, `operating_margin_history`) uses it. **Estimate flag:** the row publishes
  `metrics.ebit_estimated_years` = the number of fiscal years FY0..FY−5 whose EBIT is the substitute (integer 1–6, only when ≥ 1;
  absent means no substitute) and `metrics.ebit_estimated_fiscal_years` = **which** years: the calendar year of each substituted
  fiscal-year end, ascending, unique, same length as the count and never after the row's fiscal year (FY ending 2026-03-31 →
  2026). Both validators check the pair. The app (`qgv-scores.js`) turns it into the flag `EBIT_ESTIMATED`, shown as
  **"추정(대체 계산): FY2023·FY2024"** ("Estimate (substitute calculation): FY2023, FY2024") next to the v2 scores on the
  company screen (summary and overview, `flagsHtml`) and the leaderboard (both pass the display row to `flagText`); judgement
  rows and the daily report carry the flag code. The flag covers every EBIT-derived value of the row, because ROIC, moat,
  incremental ROIC, margins and EV/EBIT all mix the listed years. **Decision Q-EBIT-SCOPE (2026-10-15): keep this scope.**
  Each year uses the issuer's reported operating income first; only years without it are substituted and listed; FINANCIAL
  issuers are excluded. The TARGET filing-window
  TTM lineage (`public_engine_screens.qgv2_ttm_periods`) uses the same rule and profile. Tests:
  `test_ebit_substitute_is_pretax_plus_interest_and_is_flagged_as_an_estimate`, `tools/qgv_scores_node_test.js`
  ("EBIT substitute rows … carry the EBIT_ESTIMATED flag").
- **SPLIT stock-split adjustment (Q-SPLIT = add adjustment).** The latest 10-K restates FY0..FY−2 to the post-split basis, but
  FY−3 and older come from earlier filings and may be pre-split (KLAC, NFLX, ORLY, NOW, IBKR, FAST, TPL, AMCR reverse; WRB unit
  change). Every per-share input is restated to one basis, using SEC facts only (`_Company.share_factor`):
  1. **Basis** = the filing (accession + filed date) of the FY0 diluted share count (else of FY0 diluted EPS).
  2. **Filings are linked** when both report the diluted share count of the same period (same concept, same span; 10-K annual
     spans, 10-Q year-to-date/quarter spans). The link ratio is later ÷ earlier value. Within ±5% it is an ordinary revision
     (factor 1). Otherwise it must match a reported split ratio (`StockholdersEquityNoteStockSplitConversionRatio1` or
     `…Ratio`, unit pure, filed ≤ cutoff), or its reciprocal, within ±3%; the factor is then that exact ratio (a reverse split
     tagged 0.2 or 5 both work: the direction comes from the restated counts). A link matching no ratio fact is unconfirmed.
  3. A year's share count is multiplied, and its diluted EPS divided, by the product of the confirmed links from its filing to
     the basis. If the basis is reachable only through an unconfirmed link (WRB-type 1,000× change), the factor is **not
     established → NA**. If the filings share no period at all, the factor is 1 unless a split-ratio fact was filed between
     them (then NA).
  4. **Discontinuity guard:** an adjusted share count more than 3× (or less than ⅓) of FY0's is NA, and so is that year's EPS.
     **Decision Q-SPLIT-GUARD (2026-10-15): kept as a conservative protection rule, not a validated threshold.** The factor 3 was
     not calibrated; it can also make genuine spin-off, merger or IPO share changes NA for older years (c21 recompute: CEG, EXE,
     WBD, COIN, CVNA, HOOD, DASH).
  Applies to `dilution_3y`, `eps_cagr_3y`, `fcf_per_share_cagr_3y`, `book_value_per_share_cagr_3y` and both per-share
  histories. The histories are on the basis of the latest share count (`v_inputs_v2.diluted_shares`, possibly a 10-Q after FY0; FY0 basis when it is NA),
  i.e. FY0 basis × the FY0→latest factor; when that factor is not established (a split filed after FY0 that no shared period
  confirms) both histories are empty (NA) until the next 10-K. The FY0-basis Q/G ratios are unaffected by that case. Never a
  guessed ratio, never 0. Tests: `test_per_share_histories_are_split_adjusted_only_when_sec_facts_establish_the_ratio`,
  `test_split_after_fy0_blocks_per_share_history_until_the_basis_is_established`.
- **APPQ public quality inputs (Q-APPQ = add public fields).** Each row's `metrics` carries two price-free descriptors for the
  PLAYBOOK §6-2 / §17 #19 quality rule (3-year average ROIC ≥ 15% and 5-year operating-margin std < 3%p and net debt/EBITDA
  < 1.5): `roic_avg_3y` = mean of `roic` FY0, FY−1, FY−2 (all three needed; GENERAL only, since FINANCIAL has no ROIC) and
  `operating_margin_std_5y_pp` = population std of EBIT/revenue over FY0..FY−4 × 100 (all five needed, revenue > 0; GENERAL and
  FINANCIAL). Both follow every rule above (EBIT substitute, debt-free, RSG), are never ranked, never 0-filled (a constant
  margin is a real 0.0 spread) and are absent when not computable. The app's quality judgement reads them
  (`playbook-screen.js` `playbookTypeFacts`: `metrics.roic_avg_3y`, `metrics.operating_margin_std_5y_pp`,
  `metrics.net_debt_to_ebitda`), so it is no longer always NA. Tests:
  `test_quality_inputs_roic_avg_3y_and_operating_margin_std_are_published_pricefree`, `tools/playbook_screen_node_test.js`
  ("quality (#19) reads the published sec-qgv2 fields").
- **NDSN (Q-NDSN = keep).** No change: a D&A total equal to the intangible amortization only stays as reported (F2 does not
  replace it).

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
  metrics are negated first. A sub-metric needs **n ≥ 8** values. On an `INDUSTRY_GROUP` axis, a sub-metric with fewer than 8 group
  values is ranked in the whole GENERAL universe instead, and the axis counts these in `submetric_fallbacks`. Otherwise the sub-metric is NA.
- **Axis:** weighted mean of the available factor scores, with weights renormalized over the available factors. If less than 50% of the
  axis weight is available, the axis is NA with `AXIS_COVERAGE_BELOW_50`. `factors_available` ("n/5") and `available_weight` are always
  published. Missing values are **never 0**: an absent metric key, a `null` factor or a `null` score means NOT_AVAILABLE.
- **Choice of N = 8:** a fixed, uncalibrated minimum. With 8 points the percentile step is 14.3, coarse but not degenerate.

## 5. Public file `sec-qgv2.json`

Top level: `schema_version 1`, `calc_version`, `kind SEC_QGV2`, `as_of`, `standard QGV_V2`, `standard_status PROVISIONAL_DEFAULT_UNCALIBRATED`,
`decision_ref GSQ-022`, `method` (weights, min_peers 8, axis_coverage_min_percent 50, percentile rule, SIC config,
financial SIC range, cross-section rule, earnings-surprise omission), `config_version/config_status` (shared `sec-universe-shares/v0`,
14-day stale window, 7 shards), `freshness_basis`, `stale_after_seconds`, `shard_count`, `last_shard_index`, `registry_sha256`,
`code_count 504`, `cross_section_size`, `cross_section_by_profile`, `state`, `reason_codes`, `records` (504 Universe codes) and
`target` (19 TARGET ids; `hanmi` and `tokyo_electron` are `NON_SEC_ISSUER`).

Row (plus `calc_version`, see below): `cik`, `acquired_at`, `source_sha256{companyfacts,submissions}`, `state` (LIVE/STALE/NOT_AVAILABLE), `reason_codes`, `sic`,
`industry_group`, `profile`, `fiscal_year_end`, `currency`, `metrics` (sparse; 6 significant digits), `factors` (10 ids → 0–100 | null),
`axes{Q,G}{score, factors_available, available_weight, peer_basis, peer_count, submetric_fallbacks, reason_codes}`, `v_inputs_v2`.
SEC-only descriptors in `metrics` (never ranked; `v2_factors.EXTRA_METRIC_PROFILES`, not in the DART reference key set):
`ebit_estimated_years` (GENERAL, integer 1–6) and `ebit_estimated_fiscal_years` (GENERAL, ascending integer years, same length), rule EBIT, `roic_avg_3y` (GENERAL, finite) and `operating_margin_std_5y_pp`
(GENERAL and FINANCIAL, ≥ 0), rule APPQ. Both validators accept them only for those profiles and range-check them.

**Calculation-rule version `calc_version` (owner supplement 2026-10-15).** `v2_factors.CALC_VERSION` (now
`qgv2-calc/2026-10-17.1` = `2026-10-15.1` (F1–F3 + rules SW, MAA, RSG, NODEBT, EBIT, SPLIT, APPQ) + V-STALE-BS,
V-STALE-SHARES and V-SHARES-SCALE on `v_inputs_v2` only, Q·G unchanged; format `qgv2-calc/<date>.<n>`) is bumped whenever a factor rule in section 1–3 or a published
`v_inputs_v2` rule changes. The file declares it at the top level (`calc_version`) and every row with data
carries the version it was computed with (`calc_version`; `null` for rows without data and for legacy rows). **Versions are
never mixed in one percentile:** the publisher (`v2_scoring.score_rows` / `volatility_rank_rows` with `calc_version`), both
validators (Python `require_qgv2`, JS `SecQgv2.validate`, which recompute with the same rule) and the device
(`qgv2-inputs.js` → `qgv-scores.js`) rank only rows whose version equals the file's. A row of another version, or a row
without one in a versioned file (a legacy row kept from an older copy), keeps its values but gets NA factors and axes with
reason `CALC_VERSION_MISMATCH`, no playbook volatility rank, and on the device it leaves the cross-section and every V/total
percentile population and is shown as NA with the flag "계산 규칙 버전이 달라 순위에서 제외" ("Excluded from ranking: different
calculation-rule version"). A file written before this field (no `calc_version` anywhere) still loads and validates as one
legacy population, scored exactly as before. The DART reference ranks only against the file's version. **Transition:** the first
shard publish after a version bump keeps the other six shards' rows (merge never erases data) but they are outside the
population until their shard is collected again, so for up to 7 days the cross-section holds only re-collected issuers (axes
`PEERS_BELOW_MINIMUM` until each peer set reaches 8). Tests: `test_calc_version_rows_of_another_version_never_share_a_percentile`,
vectors `calc_version_*` (`sec_qgv2_node_test.js`), `qgv_scores_node_test.js` ("calc_version: …").

**Rows without source data (normal NA).** A row whose source data is missing keeps its own reason code (`NOT_COLLECTED`,
`CIK_UNRESOLVED`, `NO_ANNUAL_SEC_FINANCIALS`, `INVALID_INPUT`, TARGET `NON_SEC_ISSUER`), `calc_version` `null`, empty metrics
and axes `ROW_NOT_AVAILABLE`. It is outside every ranking population but stays one of the 504 codes (`code_count`). It is never
`CALC_VERSION_MISMATCH`: that reason is only for rows **with values** computed under another (or no) version; a row without
data cannot carry a `calc_version` (both validators). On the device such a row shows `total_reason` `SOURCE_NOT_AVAILABLE` with
its source reasons ("QGV v2 산출 불가 · 원자료 없음 (CIK 미해결)"). Tests:
`test_normal_na_rows_keep_an_explicit_source_reason_and_are_never_calc_version_mismatch`, `qgv_scores_node_test.js` ("normal-NA rows …").

**TARGET identity withdrawal (owner instruction 2026-10-17 item 3, TARGET NA schema /4 extended to the `target` section).** When
the daily TARGET collection hits an identity conflict (`sec-public-inputs.json` row `WITHDRAWN`: `SEC_CIK_MISMATCH` /
`SEC_ISSUER_NOT_ALLOWED`), the TARGET step stages a withdrawal row and the shard merge publishes it instead of the kept row:
reason `IDENTITY_CONFLICT_WITHDRAWN`, the issuer's TARGET CIK, no `acquired_at`, values or scores, and two extra keys only on
this row: `detected_at` (when the conflict was seen; never an acquisition time) and `withdrawn_acquired_at` (the `acquired_at`
of the row whose use it stops; `null` without one). The previous row is never carried or used again. Both validators accept
the two keys only on such a TARGET row. The pre-deploy freshness guard passes it only when `withdrawn_acquired_at` names the
live observation exactly (else `WITHDRAWAL_MISMATCH` / `OLDER`); a newer collection after the detection replaces it. No
calculation rule changes (`calc_version` unchanged). On the device (`qgv2-inputs.js`) the withdrawn issuer is used nowhere:
its TARGET record and every Universe code with the same CIK (other share classes) get state `WITHDRAWN`, no factors, axes,
V inputs or metrics, leave every ranking population and candidate list, and show "QGV v2 산출 불가 · 원자료 없음 (식별 충돌로
사용 중지)"; the TARGET row is never replaced by the Universe code of the same ticker. Published Q·G percentiles of other
issuers still count the same-CIK Universe rows as peers (a Universe-section change, outside this rule). Tests:
`test_target_withdrawal_e2e.py`, vectors `target_withdrawn_*` (`sec_qgv2_node_test.js`), `qgv_scores_node_test.js`
("identity-conflict withdrawal: …").

**Universe identity withdrawal (owner decision UNI-WITHDRAWN (a), 2026-10-17; `records` of this file, `sec-universe-shares.json`
and `sec-universe-qg.json`).** When a Universe code meets an identity conflict without a collection of this run (a ticker claimed by
several CIKs, an SEC response naming another CIK, another CIK without its own collection record) and a file's kept row of the code
has a collection record, that file publishes a withdrawal row instead: state NOT_AVAILABLE, reason `IDENTITY_CONFLICT_WITHDRAWN`
only, no CIK, `acquired_at`, sources, metrics or scores, plus three keys found on no other row: `detected_at` (the publishing run's
time when the conflict was first seen; never an acquisition or freshness time), `withdrawn_acquired_at` and `withdrawn_cik` (the
`acquired_at` and CIK of THAT file's kept row; each file names its own observation, nothing is copied from TARGET or another file).
Without a kept collection record the code stays `CIK_UNRESOLVED` (or this run's NA row) and no time is made up. The withdrawal is
kept unchanged (first detection, same named row) while the conflict lasts and through fetch failures, unresolved symbols,
identification failures and preserve-only rebuilds; only a new collection of the code with confirmed identity, collected at or
after the detection, replaces it (a new holder of the ticker starts from its own row, never the withdrawn issuer's history).
Withdrawal rows are not new collections, not LIVE/STALE, outside the cross-section, every percentile and the Q·G coverage counts
(`withdrawn=` on the daily summary lines and the published coverage line), and stay in the 504-code denominator. Validators
(Python and JS, vectors `universe_withdrawn_*` / `withdrawn_*`) accept the keys only on such a row; the freshness guard passes it
only when it names the live row exactly (`withdrawn_acquired_at`, `withdrawn_cik`, detection not before it), else
`WITHDRAWAL_MISMATCH` / `OLDER`, and refuses an artifact that brings the stopped row back (`OLDER`). The three files move to
`schema_version` 2 (the row contract gains a reason code and keys; readers accept 1 and 2, withdrawals only in 2; a reader of 1
only rejects a version-2 file as a whole, a safety block, not backward compatibility). No calculation change (`calc_version`
unchanged). Detection time differs from TARGET: a TARGET withdrawal takes the latest detection, a Universe withdrawal keeps the
first one; re-checks are counted in the run log line `SEC_UNIVERSE_WITHDRAWALS` only. Plain fetch failures, unresolved symbols,
identification failures of the same CIK and collections without data are never withdrawals (#278 / #287 rules); a file whose
live row does not identify one observation exactly (CIK, acquired_at, both source hashes) withdraws nothing. Contract details:
`docs/daily_data_pipeline/SEC_COLLECTION_DIAGNOSTICS.md`. On the device the row is stopped like a TARGET withdrawal (`Qgv2Inputs`
`identity_withdrawn`, "식별 충돌로 사용 중지"): no score, rank or candidate place, no M3 identity or market cap from the shares row,
and the candidate list never scores the code with another row of the same ticker. UNI-TARGET: a TARGET row (fixed CIK) keeps its
Q·G, but when its device price symbol (ticker) is the symbol of a withdrawn Universe code no price is read and its V, total, rank
and candidate place are NOT_AVAILABLE (`PRICE_IDENTITY_CONFLICT`); a TARGET of another symbol is unchanged. Tests:
`test_universe_withdrawal_e2e.py`.

`v_inputs_v2` holds the price-free inputs the device needs to compute V in RAM. Amounts are exact SEC values in the row currency.
- `ebit`, `fcf`: `{fy_value, fy_end, ttm_value, ttm_end}`. FCF = OCF − capex for the same period.
- `total_debt`, `cash_and_equivalents`: `{value, period_end}`, each at its own latest balance-sheet date (they can differ). Debt uses the same rule as section 1.
  **V-STALE-BS (calc_version `2026-10-17.1`, 2026-10-17 number check):** a debt or cash value dated before the FY0 balance sheet
  (FY0 end − 10 days, the instant tolerance) is `null` (NA), never the last value reported years earlier. Debt is 0 only from an
  FY0 line or the NODEBT rule; when NODEBT is NA (Q-NODEBT-INT) `total_debt` is NA. The device then shows `ebit_yield` and
  `fcf_yield` as NA with reason `DEBT_CASH_NOT_AVAILABLE` (missing never becomes 0). 10/17 raw: 23 issuers' debt (13 GENERAL:
  DXCM, INCY, PANW, SMCI, VRSN, VRTX, DE, DECK, DLR, EME, EXR, F, ORCL; 10 FINANCIAL, where V is not defined) and 1 issuer's cash
  (PCAR) became NA; Q·G metrics, factors and axes are identical. Test: `test_v_inputs_stale_balance_sheet_values_are_na`.
- `diluted_shares`: `{value, period_end}`, the latest weighted-average diluted share count (quarter or year).
  **V-STALE-SHARES (calc_version `2026-10-17.1`, owner decision 2026-10-17, same version as V-STALE-BS):** the count is the
  latest-ending positive fact over **all** allowed diluted-share concepts (us-gaap `WeightedAverageNumberOfDilutedSharesOutstanding`,
  `WeightedAverageNumberOfShareOutstandingBasicAndDiluted`; ifrs-full `AdjustedWeightedAverageShares`), annual spans from annual
  forms and YTD/quarter spans from 10-Q forms, filed by the cutoff (at the same period end the earlier-listed concept, then the
  shortest span). Before, the first concept with any fact was read, so its last value could be years old while another allowed
  concept was current. Freshness is the count's **period end**, not its filing date: an end before FY0 end − 10 days (the
  V-STALE-BS tolerance) is `null` (NA). Basic shares, shares outstanding (cover or balance sheet) and any other concept are never
  substituted. The per-share histories use the filing of the published count (none → FY0 basis). The device (`qgv2-inputs.js` →
  `qgv-v2.js`, unchanged; it reads no other share value) then shows `ebit_yield`, `fcf_yield`, industry, own-history and
  expectation-check V as NA with reason `SHARES_NOT_AVAILABLE` and the DCF reference range NA. Shared selection
  (`_Facts.latest_duration`) is unchanged; the new `_Facts.latest_duration_any_concept` is read only here. 10/17 raw: 7 issuers'
  count became NA (BKR 2021-06-30, REG 2020-12-31, TTWO 2024-03-31, HSY 2015-10-04, LYB 2019-03-31, SJM 2023-01-31, ERIE
  2021-06-30; no allowed concept has a current value); no issuer switched concept; Q·G metrics, factors and axes and the
  per-share histories are identical. Test: `test_v_inputs_diluted_shares_newest_allowed_concept_by_period_end_else_na`.
  **V-SHARES-SCALE (calc_version `2026-10-17.1`, owner decision 2026-10-17 on the MCD/WAT unit errors, same version):** a
  current count is checked against the dei cover share count (`EntityCommonStockSharesOutstanding`) reported in the **same
  filing** (same accession, filed by the cutoff). Ratio count / cover outside `SHARES_SCALE_BAND` = 0.1..10 (inclusive) →
  `diluted_shares` is `null` with reason `SHARES_SCALE_UNCONFIRMED`. The count is never multiplied or divided by 1,000 /
  1,000,000 and never replaced by the cover, the basic weighted count or the balance-sheet count. The per-share histories
  are `[]` (same reason) when their FY0-basis count, restated to the filing of the latest count (rule SPLIT factor), is
  outside the band of that filing's cover. No same-filing cover value, or several distinct ones (class-dimensioned covers are
  not in companyfacts) → no reference: the count is kept unchecked, never blocked for it. A stale count (V-STALE-SHARES) is
  not checked. Why the cover and not the basic count: the scale slip sits in the EPS table, so the basic count of the same
  table repeats it (MCD 709.1, WAT 98,204,000,000), while the cover is tagged separately. Band (UNCALIBRATED): 10/17 raw, 442
  issuers with a current count and one same-filing cover: every correctly tagged count within 0.83–1.16 of it, the FY0-basis
  counts of the histories within 0.58–1.20 (low end: mergers closed after FY0 — OMC, FITB, HBAN, WAT, DVN); the errors are
  10⁶× (MCD), 10³× (WAT) and 1/23 (BKNG histories). One order of magnitude each way is far outside every normal difference and
  far inside the smallest unit error. The reason code is not a published field (the `v_inputs_v2` key set is pinned by the
  hash-pinned JS validator); `v2_factors.compute(..., diagnostics={})` returns it with value, filing, concept, cover and ratio.
  The device (unchanged; it reads only `v_inputs_v2.diluted_shares`) shows the per-share and EV-based V as NA with
  `SHARES_NOT_AVAILABLE` and the DCF reference range NA; with histories `[]` the own-history V is `HISTORY_TOO_SHORT`.
  Evidence (10/17 raw; sec.gov HTML not reachable from the build environment, so the XBRL instance of the same filing and
  companyfacts are the evidence): **MCD** 10-Q 0000063908-26-000073, `WeightedAverageNumberOfDilutedSharesOutstanding`
  2026-04-01..2026-06-30 = 711.1 shares, `decimals="1"` (the displayed "711.1" in millions tagged without scale) vs cover
  707,641,531 (`decimals="INF"`) and net income 2,362,000,000 / diluted EPS 3.32 = 711.4 million; every MCD filing since the
  FY2023 10-K (11 filings) tags the weighted counts in millions, earlier ones in shares. **WAT** 10-Q 0001193125-26-344691,
  2026-04-05..2026-07-04 = 98,204,000,000 shares, `decimals="-6"` vs cover 98,248,111, balance-sheet
  `CommonStockSharesOutstanding` 98,225,000 (`decimals="-3"`) and −136,000,000 / −1.39 = 97.8 million; the 2026 Q1 and Q2
  10-Qs tag the counts (and the restated 2025 comparatives) 1,000× too high, the 10-Ks are correct. Both are filer XBRL
  scale errors; the selected concept, period and filing are right, so no selection fix applies and the count is NA.
  10/17 raw: `diluted_shares` → NA for MCD and WAT only; per-share histories → `[]` for MCD and BKNG (25-for-1 split after
  FY0, no split-ratio fact: the FY0-basis histories were 1/23 of the published post-split count); 43 issuers without a
  same-filing cover are unchecked (41 of them have net income / diluted EPS of the same period: ratios 0.23–1.09, IBKR lowest
  with its class-A-only EPS; ABNB and CVNA have no such pair). Q·G metrics,
  factors and axes are identical. Test: `test_v_inputs_diluted_shares_scale_unconfirmed_is_na_never_rescaled`.
- `ebit_per_share_history`, `fcf_per_share_history`: up to 5 fiscal years `{fiscal_year_end, value}`, oldest first. These feed the own-history multiple percentile. `[]` when their FY0-basis count fails V-SHARES-SCALE.
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
- The debt definition excludes operating leases (decision: 운용리스는 부채에서 제외한다). Debt-free issuers follow rule NODEBT
  (section 1; no materiality threshold); its concept list is a fixed v0 list.
- No earnings-surprise sub-metric. Add one only if a free source is approved.
- Fallback lines F1–F3 (section 1): a D&A total equal to the intangible amortization only (NDSN, not covered by F2) is kept as
  reported (owner decision Q-NDSN 2026-10-15: no change).
- The first week after launch has a partial cross-section (about 72 issuers per day). Peer bases fall back to the universe until each group reaches 8.


## 8. 2026-10-13 approved normalized-earnings inputs

`v_inputs_v2.revenue` uses the same FY/TTM flow structure and SEC period rules as EBIT.
`operating_margin_history` contains at most five ascending annual fiscal-period ends and reported EBIT/revenue ratios,
with missing years omitted and no zero replacement. The older input shape remains readable. These are price-free
fields for the approved cyclical definition (latest revenue × five-year mean operating margin); the device leaves
normalized EBIT unavailable unless all five years exist. Public-field publication is pending this PR's approval.
