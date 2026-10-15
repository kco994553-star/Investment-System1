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
  interest. Operating-lease liabilities stay outside debt, as before. Everything else keeps the previous rule (NA when the
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
  absent means no substitute). The app (`qgv-scores.js`) turns it into the flag `EBIT_ESTIMATED`, shown as
  **"추정(대체 계산)"** ("Estimate (substitute calculation)") next to the v2 scores wherever they are displayed (company screen
  summary and overview through `flagText`, judgement rows and the daily report through the flags list). The TARGET filing-window
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
  Applies to `dilution_3y`, `eps_cagr_3y`, `fcf_per_share_cagr_3y`, `book_value_per_share_cagr_3y` and both per-share
  histories. The histories are on the basis of the latest share count (`v_inputs_v2.diluted_shares`, possibly a 10-Q after FY0),
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

Top level: `schema_version 1`, `kind SEC_QGV2`, `as_of`, `standard QGV_V2`, `standard_status PROVISIONAL_DEFAULT_UNCALIBRATED`,
`decision_ref GSQ-022`, `method` (weights, min_peers 8, axis_coverage_min_percent 50, percentile rule, SIC config,
financial SIC range, cross-section rule, earnings-surprise omission), `config_version/config_status` (shared `sec-universe-shares/v0`,
14-day stale window, 7 shards), `freshness_basis`, `stale_after_seconds`, `shard_count`, `last_shard_index`, `registry_sha256`,
`code_count 504`, `cross_section_size`, `cross_section_by_profile`, `state`, `reason_codes`, `records` (504 Universe codes) and
`target` (19 TARGET ids; `hanmi` and `tokyo_electron` are `NON_SEC_ISSUER`).

Row: `cik`, `acquired_at`, `source_sha256{companyfacts,submissions}`, `state` (LIVE/STALE/NOT_AVAILABLE), `reason_codes`, `sic`,
`industry_group`, `profile`, `fiscal_year_end`, `currency`, `metrics` (sparse; 6 significant digits), `factors` (10 ids → 0–100 | null),
`axes{Q,G}{score, factors_available, available_weight, peer_basis, peer_count, submetric_fallbacks, reason_codes}`, `v_inputs_v2`.
SEC-only descriptors in `metrics` (never ranked; `v2_factors.EXTRA_METRIC_PROFILES`, not in the DART reference key set):
`ebit_estimated_years` (GENERAL, integer 1–6, rule EBIT), `roic_avg_3y` (GENERAL, finite) and `operating_margin_std_5y_pp`
(GENERAL and FINANCIAL, ≥ 0), rule APPQ. Both validators accept them only for those profiles and range-check them.

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
- The debt definition excludes operating leases. Debt-free issuers follow rule NODEBT (section 1); its concept list is a fixed v0 list.
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
