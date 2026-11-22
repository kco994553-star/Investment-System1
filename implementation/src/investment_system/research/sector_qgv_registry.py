"""Owner §4–5 sector-QGV registry. Research defaults, not official calc23.1.

Semantic variant IDs are stable; historical dictionary IDs are asserted only where
specified in the supplied design. No inferred Q13/G12/V15 numbering.
"""
from __future__ import annotations

MODEL = 'sector-qgv-default/0.1.0'
ENGINE = 'sector-qgv-engine/0.1.0'
NORMALIZATION = 'sector-midrank-strict20/1'
MAPPING = 'book-sector-map/1'
SOURCE = 'owner:Sector_QGV_Custom_Factors_Implementation_20261106.md'
SECTORS = {
    'CONSUMER_DISCRETIONARY': (30,25,45), 'CONSUMER_STAPLES': (35,15,50),
    'ENERGY': (35,15,50), 'FINANCIALS': (40,15,45), 'HEALTH_CARE': (35,25,40),
    'INDUSTRIALS': (35,20,45), 'INFORMATION_TECHNOLOGY': (30,25,45),
    'MATERIALS': (35,15,50), 'TELECOMMUNICATIONS': (40,15,45), 'UTILITIES': (40,10,50),
}
TEMPLATES = ('GENERAL','BANK','INSURANCE','BROKER','MORTGAGE_REIT','ASSET_MANAGER','EQUITY_REIT')
FINANCIAL = ('BANK','INSURANCE','BROKER','MORTGAGE_REIT')
GENERAL = ('GENERAL','ASSET_MANAGER')
CATALOG = {}


def add(variant, axis, role, name, inputs, formula, *, period='TTM', direction='HIGHER',
        scopes=TEMPLATES, aliases=(), legacy=None, unit='decimal', status='IMPLEMENTED', note=''):
    CATALOG[variant] = dict(factor_id=legacy or variant, variant_id=variant, axis=axis, role=role,
        display_name=name, aliases=list(aliases), formula_version='1', formula=formula,
        inputs=[dict(field=f,period=p,unit=u) for f,p,u in inputs], unit=unit, direction=direction,
        period=period, scope=list(scopes), domain_rules=note or 'All named inputs required; positive denominator; signed numerator preserved.',
        overlap_group=variant, evidence_refs=[SOURCE], calculator_status=status)


def flow(f): return (f,'TTM','currency')
def stock(f): return (f,'INSTANT','currency')
def per_share(f,p='TTM'): return (f,p,'currency/share')
PRICE = ('price','PRICE','currency/share')
MCAP = ('issuer_mcap','PRICE','currency')
EV = ('enterprise_value','PRICE','currency')
add('operating_margin_ttm','Q','profitability','영업이익률', [flow('operating_income'),flow('revenue')],'ratio',scopes=GENERAL,legacy='Q01')
add('accruals_assets_ttm','Q','accounting_quality','발생액/평균자산',[flow('net_income'),flow('cfo'),stock('assets_begin'),stock('assets_end')],'difference_average',direction='LOWER',scopes=GENERAL,legacy='Q05')
add('debt_assets','Q','financial_capacity','차입금/자산',[stock('debt'),stock('assets_end')],'ratio',period='LATEST_QUARTER',direction='LOWER',scopes=GENERAL+('EQUITY_REIT',),legacy='Q06')
add('roa_ttm','Q','profitability','ROA',[flow('net_income'),stock('assets_begin'),stock('assets_end')],'ratio_average',scopes=FINANCIAL+GENERAL)
add('roe_common_ttm','Q','profitability','보통주 ROE',[flow('net_income_common'),stock('common_equity_begin'),stock('common_equity_end')],'ratio_average',scopes=FINANCIAL)
add('common_equity_assets','Q','financial_capacity','보통주자본/자산',[stock('common_equity_end'),stock('assets_end')],'ratio',period='LATEST_QUARTER',scopes=FINANCIAL,legacy='Q14')
add('cfo_assets_ttm','Q','profitability','CFO/평균자산',[flow('cfo'),stock('assets_begin'),stock('assets_end')],'ratio_average',scopes=GENERAL+('EQUITY_REIT',))
add('interest_coverage_ttm','Q','interest_capacity','이자보상배율',[flow('operating_income'),flow('interest_expense')],'ratio',unit='multiple',scopes=GENERAL+('EQUITY_REIT',))
add('revenue_cagr_3y','G','growth','매출 3년 CAGR',[('revenue_fy','FY','currency'),('revenue_fy3','FY_MINUS_3','currency')],'cagr3',period='FY_3Y',scopes=GENERAL+('EQUITY_REIT',),legacy='G02')
add('roa_improvement_3y','G','profitability_change','3년 ROA 개선',[('roa_fy','FY','decimal'),('roa_fy3','FY_MINUS_3','decimal')],'difference',period='FY_3Y',legacy='G06',note='ROA FY net income / mean(begin,end assets); t−3 requires t−4 assets. Signed difference.')
add('common_bps_cagr_3y','G','growth','보통주 BPS 3년 CAGR',[per_share('common_bps_fy','FY'),per_share('common_bps_fy3','FY_MINUS_3')],'cagr3',period='FY_3Y',scopes=FINANCIAL,legacy='G13')
add('cfo_assets_improvement_3y','G','profitability_change','CFO/자산 3년 개선',[('cfo_assets_fy','FY','decimal'),('cfo_assets_fy3','FY_MINUS_3','decimal')],'difference',period='FY_3Y',scopes=('EQUITY_REIT',),legacy='G14')
add('ep_ttm_diluted','V','earnings','PER / E/P (TTM 희석)',[per_share('eps_ttm_diluted'),PRICE],'ratio',aliases=('PER_TTM_DILUTED','EP_TTM_DILUTED'),note='Explicit verified TTM diluted EPS; no NI/current-shares or undefined FY/YTD EPS arithmetic. Negative and zero E/P valid; PER display only for positive EPS.')
add('ep_fy_diluted','V','earnings','연간 PER / E/P',[per_share('eps_fy_diluted','FY'),PRICE],'ratio',period='FY',aliases=('PER_FY_DILUTED',))
add('ep_fy1','V','earnings','예상 PER FY1',[per_share('eps_fy1','FY1'),PRICE],'ratio',period='FY1',aliases=('PER_FY1',))
add('ep_ntm','V','earnings','예상 PER NTM',[per_share('eps_ntm','NTM'),PRICE],'ratio',period='NTM',aliases=('PER_NTM',))
add('net_income_mcap','V','earnings','순이익/현재 시총',[flow('net_income_common'),MCAP],'ratio')
add('common_bp','V','book_value','PBR / 보통주 B/P',[per_share('common_bps','INSTANT'),PRICE],'ratio',period='LATEST_QUARTER',aliases=('PBR_COMMON',),note='Common-equity attributable scope and current class shares, not total equity. Negative and zero valid with capital impairment label.')
add('tangible_common_bp','V','book_value','P/TBV',[per_share('tangible_common_bps','INSTANT'),PRICE],'ratio',period='LATEST_QUARTER',aliases=('PTBV_COMMON',))
add('sales_mcap','V','sales_value','PSR / 매출수익률',[flow('revenue'),MCAP],'ratio',aliases=('PSR_TTM',))
add('cfo_mcap','V','operating_cash','PCR / CFO 수익률',[flow('cfo'),MCAP],'ratio',aliases=('PCR_CFO_TTM',))
add('ni_da_mcap','V','operating_cash','PCR (NI+D&A)',[flow('net_income'),flow('da'),MCAP],'sum_ratio',aliases=('PCR_NI_DA_TTM',))
add('ebitda_ev','V','enterprise_value','EV/EBITDA',[flow('ebit'),flow('da'),EV],'sum_ratio',aliases=('EV_EBITDA_TTM',),note='Unadjusted EBIT + D&A; excludes company adjusted EBITDA; same period. EV strictly positive.')
add('ebit_ev','V','enterprise_value','EV/EBIT',[flow('ebit'),EV],'ratio',aliases=('EV_EBIT_TTM',))
add('sales_ev','V','enterprise_value','EV/Sales',[flow('revenue'),EV],'ratio',aliases=('EV_SALES_TTM',))
add('fcf_mcap','V','investment_cash','P/FCF (CFO−CAPEX)',[flow('cfo'),flow('capex'),MCAP],'difference_ratio',aliases=('P_FCF_CFO_CAPEX_TTM',),note='CFO minus positive cash CAPEX outflow; not labelled FCFE.')
add('fcf_ev','V','investment_cash','EV/FCF (CFO−CAPEX)',[flow('cfo'),flow('capex'),EV],'difference_ratio',aliases=('EV_FCF_CFO_CAPEX_TTM',))
add('fcff_ev','V','investment_cash','EV/FCFF',[flow('fcff'),EV],'ratio',aliases=('EV_FCFF_TTM',),status='PENDING_DEFINITION',note='FCFF tax/interest/reinvestment recipe not supplied; cannot execute until separately versioned.')
add('dividend_yield_ttm','V','distribution','배당수익률',[per_share('common_dps_ttm'),PRICE],'ratio',aliases=('DIVIDEND_YIELD_TTM',),note='Confirmed no common dividend is explicit 0; missing is null.')
add('net_share_reduction','V','distribution','순주식수 감소율',[('adjusted_shares_now','INSTANT','shares'),('adjusted_shares_year_ago','YEAR_AGO','shares')],'one_minus_ratio',period='ONE_YEAR')
add('shareholder_yield','V','distribution','주주환원수익률',[('dividend_yield','TTM','decimal'),('net_share_reduction','ONE_YEAR','decimal')],'sum',period='TTM')
add('peg_historical','V','earnings','PEG (과거 3년)',[per_share('eps_ttm_diluted'),PRICE,('eps_growth_3y','FY_3Y','decimal')],'peg',unit='multiple',direction='LOWER',note='price/EPS/(decimal growth*100); EPS and growth strictly positive.')
add('peg_forecast','V','earnings','예상 PEG',[per_share('eps_fy1','FY1'),PRICE,('eps_forecast_growth','FORECAST','decimal')],'peg',period='FY1',unit='multiple',direction='LOWER',status='PENDING_DEFINITION',note='Forecast growth horizon and consensus vintage recipe pending.')
add('nareit_ffo_mcap','V','reit_earnings','P/FFO (Nareit)',[flow('nareit_ffo'),MCAP],'ratio',scopes=('EQUITY_REIT',),aliases=('P_FFO_NAREIT_TTM',))
add('affo_mcap','V','reit_earnings','P/AFFO',[flow('affo'),MCAP],'ratio',scopes=('EQUITY_REIT',),status='PENDING_DEFINITION',note='Company AFFO reconciliation not standardized; explicit recipe approval required.')

ALIASES = {alias:key for key,item in CATALOG.items() for alias in item['aliases']}


def canonical(variant):
    key = ALIASES.get(variant,variant)
    if key not in CATALOG: raise ValueError('UNKNOWN_VARIANT')
    return key

# Design IDs from the separately supplied candidate catalog, not operating IDs.
DESIGN_IDS = {
 'operating_margin_ttm':'Q01','roa_ttm':'Q02','cfo_assets_ttm':'Q04','accruals_assets_ttm':'Q05',
 'debt_assets':'Q06','interest_coverage_ttm':'Q08','roe_common_ttm':'Q09',
 'revenue_cagr_3y':'G02','roa_improvement_3y':'G06',
 'ep_ttm_diluted':'V01','ep_fy_diluted':'V01','net_income_mcap':'V01',
 'cfo_mcap':'V02','sales_mcap':'V03','sales_ev':'V04','ebitda_ev':'V05','fcf_mcap':'V06',
 'fcff_ev':'V07','common_bp':'V08','tangible_common_bp':'V09','dividend_yield_ttm':'V10',
 'net_share_reduction':'V11','shareholder_yield':'V12','nareit_ffo_mcap':'V13',
 'affo_mcap':'V14','ep_fy1':'V15','ep_ntm':'V15',
}
for v, design_id in DESIGN_IDS.items(): CATALOG[v]['factor_id']=design_id
CATALOG['interest_coverage_ttm']['inputs'][0]=dict(field='ebit',period='TTM',unit='currency')
add('gross_profit_assets_ttm','Q','profitability','매출총이익/평균자산',[flow('gross_profit'),stock('assets_begin'),stock('assets_end')],'ratio_average',scopes=GENERAL,legacy='Q03')
add('net_debt_assets','Q','financial_capacity','순차입금/자산',[stock('debt'),stock('cash'),stock('assets_end')],'difference_ratio',period='LATEST_QUARTER',direction='LOWER',scopes=GENERAL,legacy='Q07')
add('roic_explicit','Q','profitability','ROIC',[flow('nopat'),stock('invested_capital_begin'),stock('invested_capital_end')],'ratio_average',scopes=GENERAL,legacy='Q10',status='PENDING_DEFINITION',note='Tax, leases and non-operating assets recipe unresolved; do not alias operating ROIC silently.')
add('profit_stability_5y','Q','stability','이익 안정성 (5년)',[],'pending',period='FY_5Y',direction='LOWER',legacy='Q11',status='PENDING_DEFINITION',note='ROA vs margin, standard deviation convention and loss guard require a defined variant.')
add('noa_growth','Q','accounting_quality','순영업자산 증가율',[],'pending',period='FY',legacy='Q12',status='PENDING_DEFINITION',note='NOA decomposition and scoring direction unresolved.')
add('depreciation_capex','Q','accounting_quality','감가상각/CAPEX',[flow('depreciation'),flow('capex')],'ratio',legacy='Q13',status='PENDING_DEFINITION',note='Period can be TTM, but direction/industry policy unresolved; no automatic high/low scoring.')

def annual_series(field,years,unit='currency'):
    return [(field+'_fy'+(str(k) if k else ''),'FY_MINUS_'+str(k) if k else 'FY',unit) for k in range(years+1)]
# G02/G03/G04/G05 require every annual observation, not only endpoint availability.
CATALOG['revenue_cagr_3y']['inputs']=[dict(field=f,period=p,unit=u) for f,p,u in annual_series('revenue',3)]
CATALOG['common_bps_cagr_3y']['inputs']=[dict(field=f,period=p,unit=u) for f,p,u in annual_series('common_bps',3,'currency/share')]
add('revenue_growth_1y','G','growth','매출 1년 증가율',annual_series('revenue',1),'growth1',period='FY_1Y',scopes=GENERAL+('EQUITY_REIT',),legacy='G01')
add('revenue_cagr_5y','G','growth','매출 5년 CAGR',annual_series('revenue',5),'cagr5',period='FY_5Y',scopes=GENERAL+('EQUITY_REIT',),legacy='G03')
add('operating_income_cagr_3y','G','growth','영업이익 3년 CAGR',annual_series('operating_income',3),'cagr3',period='FY_3Y',scopes=GENERAL,legacy='G04')
add('eps_diluted_cagr_3y','G','growth','희석 EPS 3년 CAGR',annual_series('eps_diluted',3,'currency/share'),'cagr3',period='FY_3Y',legacy='G05')
add('revenue_growth_consistency_3y','G','growth','매출 성장 지속성',annual_series('revenue',3),'positive_growth_share',period='FY_3Y',scopes=GENERAL+('EQUITY_REIT',),legacy='G07')
for variant,design_id,name,scope,note in [
 ('cfo_per_share_growth','G08','CFO/주 성장',GENERAL,'Growth horizon and shares denominator unspecified.'),
 ('fcf_per_share_growth','G09','FCF/주 성장',GENERAL,'Growth horizon, cash CAPEX and shares definition unspecified.'),
 ('tangible_bps_growth','G10','유형장부가/주 성장',FINANCIAL,'Growth horizon and common intangible reconciliation unspecified.'),
 ('ffo_per_share_growth','G11','FFO/주 성장',('EQUITY_REIT',),'Growth horizon and dilution basis unspecified.'),
 ('consensus_growth','G12','컨센서스 성장',TEMPLATES,'Consensus forecast horizon and aggregation/vintage unspecified.')]:
    add(variant,'G','growth',name,[],'pending',period='UNRESOLVED',scopes=scope,legacy=design_id,status='PENDING_DEFINITION',note=note)
# Preserve authoritative source distinction and overlap warnings; recommendations are not book performance claims.
for f in CATALOG.values():
    f['evidence_refs'].append('owner:Sector_QGV_Factor_Catalog_20261106.md')
    f['duplicate_policy']='SAME_VARIANT_ALIAS_REJECTED; related variants share a fixed role budget'
    f['substitution_policy']='NONE; choose a new versioned configuration, never per-company fallback'
    f['source_definition']='Explicit field/period/scope contract; retained source reference required'
ALIASES = {alias:key for key,item in CATALOG.items() for alias in item['aliases']}

# The v0 V role contract is earnings / cash / other value (implementation §5).
for variant,factor in CATALOG.items():
    if factor['axis']=='V':
        factor['role']=('earnings' if factor['role'] in ('earnings','reit_earnings') else
                        'cash' if factor['role']=='operating_cash' else 'other_value')
