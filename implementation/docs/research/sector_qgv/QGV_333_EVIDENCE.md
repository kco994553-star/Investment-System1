# Evidence and formula differences — fixed 3/3/3 research

Read 2026-11-13. This is an owner's fixed research configuration, not a Buffett
formula, an institution's portfolio, or evidence that nine equal weights are
optimal. No performance was used to choose factors. Current strict/20/gate and
common-ten-sector rules remain system policies. Full source bytes and receipts
are private; only citations and method comparisons are published here.

## Primary sources actually opened

| Source | Sections read | Direct claim and difference from this implementation |
|---|---|---|
| [MSCI Quality May 2022](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Quality_Indexes_Methodology_May2022.pdf) | construction; Appendix I pp10, Appendix II pp11 | ROE=TTM EPS/latest BPS; debt/equity; five-FY EPS-growth standard deviation. Our ROA uses average assets, common ROE uses average common equity, debt/assets uses assets. These are different variants. MSCI permits some missing-factor averaging; our strict policy does not. |
| [MSCI Value/Growth May 2023](https://app2.msci.com/eqb/methodology/meth_docs/MSCI_GIMIVGMethod_May2023.pdf) | §1.2.1, §2.3; appendix pp29–32 | Value uses B/P, forward E/P, dividend yield. Growth uses forward EPS, internal growth and five-year regression trends of EPS and sales/share (minimum four observations). Our E/P is historical verified diluted TTM, EPS CAGR is positive-endpoint three-year CAGR, sales is issuer revenue, persistence is count of three increases/3. No forecast mixing, regression or institution missing reweighting is imported. |
| [Buffett 1977](https://www.berkshirehathaway.com/letters/1977.html) | opening discussion of performance and equity capital | EPS growth alone can be financed by added equity; beginning-equity return matters. It does not prescribe ROA, this common-ROE denominator, EPS CAGR or 3/3/3. |
| [Buffett 1986](https://www.berkshirehathaway.com/letters/1986.html) | appendix, owner earnings discussion | Earnings plus noncash charges less maintenance investment and required working capital. Our reported CFO and CFO-capex are not owner earnings; maintenance capex is not estimated or filled. |
| [Buffett 1992](https://www.berkshirehathaway.com/letters/1992.html) | common-stock/value-growth discussion | Growth and value are linked through incremental returns; low multiples/high yield do not prove intrinsic value. Relative V is not a margin of safety. |
| [Buffett 2007](https://www.berkshirehathaway.com/letters/2007ltr.pdf) | Businesses — Great, Good and Gruesome, pp6–8 | Durable competitive advantage and capital needed for growth; moat/management/incremental returns remain separate evidence-backed diagnostics, zero automatic core contribution. |
| [S&P Quality](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-quality-indices.pdf) | unavailable | One official request returned HTTP403. Exact formula/financial exceptions NOT VERIFIED here; no retry or inferred endorsement. |

Prior What Works on Wall Street reading is reused from DUAL_QGV.md, not newly
claimed: chapters8/14/15/17/18/19/24/25; Drive1ZmzhcJONp4Wi2UDiMVLg5deBt7fiozaC,
original bytes SHA recorded there. Book cash-flow proxies, ranking treatment and
sector descriptions are not interchangeable with these system variants.

## Factor-level rationale, overlap and input burden

Exact inputs/units/periods/directions/accounting scope are exported from the
single CATALOG in `qgv-333-contract.json`; it is the computational authority.
The following is rationale, not a second formula registry. Actual selected-target
input/raw/score counts are in each private result coverage.selected_factors;
no aggregate input rate is presented as final-score coverage.

| Variants | Economic role / selection reason | Evidence relationship and overlap | Burden / limits / pending reason |
|---|---|---|---|
| roa_ttm, operating_margin_ttm | asset profitability / operating margin | profitability concept, not MSCI ROE; margin and ROA share earnings exposure | TTM flows, matched endpoints and consolidated scope; only CATALOG accounting scopes |
| accruals_assets_ttm | NI–CFO cash-conversion proxy, lower better | system proxy; exact S&P analogue unverified; overlaps CFO yields | NI/CFO same TTM, average assets; unsuitable capital-financial/equity-REIT scopes remain excluded |
| debt_assets | interest-bearing leverage, lower better | distinct from MSCI debt/equity and total liabilities | explicit debt, matched asset date; missing debt is not0 |
| roe_common_ttm, common_equity_assets | common-owner profitability / capital cushion | Buffett/quality conceptual, different denominators; correlation with B/P and ROA | common attribution, average positive common equity for ROE; never total-equity substitution |
| cfo_assets_ttm, interest_coverage_ttm | REIT cash productivity / interest service | system adaptation, not owner earnings or an institution recipe | CFO/average assets; EBIT/interest. Missing/zero interest cannot be silently scored as infinite |
| revenue_cagr_3y, revenue_growth_consistency_3y | growth extent / persistence contrast | not MSCI sales/share regression; correlated sales exposures in U1-333 explicitly accepted as controlled contrast | four comparable FY revenue observations; CAGR positive endpoints; equal year is not increase |
| roa_improvement_3y, cfo_assets_improvement_3y | three-year profitability/cash-productivity change | system adaptation; overlaps level profitability | verified FY ratios at t and t−3; no change of accounting denominator |
| eps_diluted_cagr_3y, common_bps_cagr_3y | per-share earnings / common-capital accumulation | MSCI uses different EPS trend; capital additions can affect book growth | four FY observations, matching diluted/common class, currency, corporate actions. Loss-to-profit not CAGR |
| ffo_per_share_growth | REIT per-share operating growth | proposed slot, no approved complete definition | PREPARING: horizon, diluted basis, restatement and Nareit reconciliation must be specified; G remains null |
| ep_ttm_diluted, common_bp | earnings and common-book price perspectives | MSCI value has forward E/P, not our TTM; B/P not intrinsic value | verified TTM diluted EPS or common BPS; same security/action basis and valuation-day price |
| cfo_mcap, fcf_mcap | operating cash / after-total-capex yield | distinct from Buffett owner earnings; correlated with earnings/accruals | issuer equity all matching classes, prices/shares; capex positive expenditure. No missing capital components0 |
| dividend_yield_ttm | realized common-owner distribution | MSCI value conceptual support; exact common TTM variant retained | TTM common DPS/class/action basis. Actual0 valid, absent data null. Financial third is this explicit research extension, not prior official default |
| ebitda_ev, sales_ev, sales_mcap | capital-structure earnings / sales valuation | system sector defaults; no primary-source optimality claim | issuer scope, all required EV components; EBITDA is EBIT+DA, not CFO; sales ignores margins |
| nareit_ffo_mcap | REIT sector-specific operating yield | retained approved catalog variant, not new general-company substitute | defined/reconciled Nareit TTM FFO and matching issuer equity; absence blocks V |

These factors are correlated by construction. Equal weights do not imply
independent risks. Sector/financial/REIT scope and missing inputs remain visible
in original denominators. Institution financial exceptions are not copied.
EPS/BPS/DPS absolute levels are components, never standalone valuation points.
No new financial-statements or market-price acquisition occurred in this work.
