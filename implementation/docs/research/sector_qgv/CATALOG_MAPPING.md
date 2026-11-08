# Candidate design ID → explicit variants → operating correspondence

Latest implementation §5 controls defaults and G06. These are **design IDs**, not the existing composite-factor IDs. No old score is renamed as a raw observation.

| Design ID | Variants | Calculator | Operating correspondence / distinction |
|---|---|---|---|
| G01 | revenue_growth_1y | IMPLEMENTED | revenue_ttm_growth has different period; annual YoY is separate. |
| G02 | revenue_cagr_3y | IMPLEMENTED | Shared annual SEC extraction reused; this candidate additionally requires all four annual observations. |
| G03 | revenue_cagr_5y | IMPLEMENTED | Shared annual SEC extraction; six annual observations required. |
| G04 | operating_income_cagr_3y | IMPLEMENTED | Reported operating income, not EBIT-per-share growth. |
| G05 | eps_diluted_cagr_3y | IMPLEMENTED | Existing split-aware annual EPS source can be supplied only with verified identity/basis; no current-shares replacement. |
| G06 | roa_improvement_3y | IMPLEMENTED | Latest override: annual ROA_t minus ROA_t-3; not QMJ or margin change. |
| G07 | revenue_growth_consistency_3y | IMPLEMENTED | Existing positive-growth share uses a different history; this variant uses three changes. |
| G08 | cfo_per_share_growth | PENDING_DEFINITION | Horizon/share basis pending. |
| G09 | fcf_per_share_growth | PENDING_DEFINITION | Existing fcf_per_share_cagr_3y is not automatically this undefined-horizon candidate. |
| G10 | tangible_bps_growth | PENDING_DEFINITION | Existing financial book-value growth is not necessarily tangible/common capital. |
| G11 | ffo_per_share_growth | PENDING_DEFINITION | Requires same Nareit FFO/share definition and specified horizon. |
| G12 | consensus_growth | PENDING_DEFINITION | No dated consensus aggregation/horizon defined. |
| G13 | common_bps_cagr_3y | IMPLEMENTED | New common BPS 3-year CAGR; not tangible G10. |
| G14 | cfo_assets_improvement_3y | IMPLEMENTED | New annual CFO/mean-assets delta, t-4 assets required. |
| Q01 | operating_margin_ttm | IMPLEMENTED | v_inputs_v2.operating_margin_history is FY, not TTM; reported operating income only here. |
| Q02 | roa_ttm | IMPLEMENTED | Financial metrics ROA is annual; new variant is TTM / begin-end mean assets. |
| Q03 | gross_profit_assets_ttm | IMPLEMENTED | metrics.gross_profit_to_assets uses FY / end assets; not the mean-assets TTM variant. |
| Q04 | cfo_assets_ttm | IMPLEMENTED | Reuse SEC operating_cash_flow and total_assets; no alias to q_earnings_quality score. |
| Q05 | accruals_assets_ttm | IMPLEMENTED | metrics.accruals_to_assets is FY; use same components with explicit TTM period. |
| Q06 | debt_assets | IMPLEMENTED | Reuse _Company.debt_at and SEC asset inputs; not total liabilities. |
| Q07 | net_debt_assets | IMPLEMENTED | Reuse debt/cash/asset inputs; signed net cash remains valid. |
| Q08 | interest_coverage_ttm | IMPLEMENTED | metrics.interest_coverage is FY; TTM EBIT/interest is separate. |
| Q09 | roe_common_ttm | IMPLEMENTED | Existing generic ROE does not prove common-equity attribution; separate variant. |
| Q10 | roic_explicit | PENDING_DEFINITION | Operating ROIC has its own tax/capital defaults; no automatic adoption. |
| Q11 | profit_stability_5y | PENDING_DEFINITION | operating_margin_std_5y_pp is not an approved candidate stability/loss-guard policy. |
| Q12 | noa_growth | PENDING_DEFINITION | No exact approved NOA decomposition connected. |
| Q13 | depreciation_capex | PENDING_DEFINITION | D&A is not automatically depreciation; direction/industry policy pending. |
| Q14 | common_equity_assets | IMPLEMENTED | New common-equity/total-assets ratio; not CET1. |
| V01 | ep_ttm_diluted, ep_fy_diluted, net_income_mcap | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V02 | cfo_mcap | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V03 | sales_mcap | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V04 | sales_ev | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V05 | ebitda_ev | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V06 | fcf_mcap | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V07 | fcff_ev | PENDING_DEFINITION | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V08 | common_bp | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V09 | tangible_common_bp | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V10 | dividend_yield_ttm | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V11 | net_share_reduction | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V12 | shareholder_yield | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V13 | nareit_ffo_mcap | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V14 | affo_mcap | PENDING_DEFINITION | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| V15 | ep_fy1, ep_ntm | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| ebit_ev | ebit_ev | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| fcf_ev | fcf_ev | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| ni_da_mcap | ni_da_mcap | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| peg_forecast | peg_forecast | PENDING_DEFINITION | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
| peg_historical | peg_historical | IMPLEMENTED | Existing qgv_v2 composite V factor names are not identical formulas. Reuse evidence-bearing price/financial inputs; match the exact numerator, denominator, period and share scope listed in catalog.json. |
