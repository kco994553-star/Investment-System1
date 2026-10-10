"""GSQ-010 public output policy. No runtime switch or environment bypass.

A matching legacy hash or a synthetic label is not publication permission.
This initial contract withholds all legacy sections; a reviewed price-free
contract can extend it independently of collectors and private device state.
"""

MESSAGE = "PUBLIC_PRICE_BOUNDARY: route withheld under GSQ-010"
SECTIONS = ('universe', 'qgv', 'technical', 'macro', 'portfolio', 'leaderboard',
            'news', 'relationships', 'changes')
REASON = '공개 가격 경계에 따라 제공되지 않습니다. (GSQ-010)'


class PublicPriceBoundaryError(ValueError):
    """Value-free rejection before acquisition, persistence, or publication."""


def block_public_route():
    raise PublicPriceBoundaryError(MESSAGE)


def public_bundle():
    return {'schema_version': 1, 'companies': [], **{
        name: {'state': 'NOT_AVAILABLE', 'as_of': None, 'source': None,
               'reason': REASON, 'data': None} for name in SECTIONS}}


def require_public_bundle(bundle):
    # Exact structural allowlist rejects nested extras and renamed values too.
    # Never accept caller-provided provenance/synthetic flags as proof.
    if bundle != public_bundle():
        block_public_route()


FINANCIAL_SOURCE_KINDS = frozenset({
    'SEC_COMPANYFACTS', 'SEC_SUBMISSIONS', 'SEC_SUBMISSIONS_PAGE',
    'SEC_TICKERS', 'SEC_CIK_LOOKUP',
})


FINANCIAL_URL_PATTERNS = {
    'SEC_COMPANYFACTS': r'https://data\.sec\.gov/api/xbrl/companyfacts/CIK[0-9]{10}\.json',
    'SEC_SUBMISSIONS': r'https://data\.sec\.gov/submissions/CIK[0-9]{10}\.json',
    'SEC_SUBMISSIONS_PAGE': r'https://data\.sec\.gov/submissions/CIK[0-9]{10}-submissions-[0-9]+\.json',
    'SEC_TICKERS': r'https://www\.sec\.gov/files/company_tickers\.json',
    'SEC_CIK_LOOKUP': r'https://www\.sec\.gov/Archives/edgar/cik-lookup-data\.txt',
}


def require_financial_source(source_kind, url):
    import re
    if source_kind not in FINANCIAL_URL_PATTERNS or not re.fullmatch(FINANCIAL_URL_PATTERNS[source_kind], url):
        block_public_route()


def require_financial_artifact(source_kind, url, artifact_id):
    require_financial_source(source_kind, url)
    basename = url.rsplit('/', 1)[-1]
    expected = {
        'SEC_TICKERS': 'sec_tickers', 'SEC_CIK_LOOKUP': 'sec_cik_lookup',
        'SEC_COMPANYFACTS': 'companyfacts:' + basename.removeprefix('CIK').removesuffix('.json'),
        'SEC_SUBMISSIONS': 'submissions:' + basename.removeprefix('CIK').removesuffix('.json'),
        'SEC_SUBMISSIONS_PAGE': 'submissions_page:' + basename,
    }[source_kind]
    if artifact_id != expected:
        block_public_route()


def require_financial_url(url):
    import re
    if not any(re.fullmatch(pattern, url) for pattern in FINANCIAL_URL_PATTERNS.values()):
        block_public_route()


AUDITED_ROUTES = (
    '.github/workflows/c21-real-data.yml',
    '.github/workflows/cockpit-pages.yml',
    '.github/workflows/web-mvp-validation.yml',
    '.github/workflows/web-research-guard.yml',
    '.github/workflows/web-state-presentation.yml',
    'implementation/src/investment_system/product/web_assets/app.js',
    'implementation/src/investment_system/product/web_mvp.py',
    'implementation/tools/audit_mcap_store.py',
    'implementation/tools/build_pages_cockpit.py',
    'implementation/tools/build_web_mvp_demo.py',
    'implementation/tools/build_web_research_guard_fixture.py',
    'implementation/tools/build_web_state_presentation_fixture.py',
    'implementation/tools/export_web_bundle.py',
    'implementation/tools/fetch_cover_xbrl.py',
    'implementation/tools/fetch_ishares_reference.py',
    'implementation/tools/fetch_krx_data.py',
    'implementation/tools/fetch_nport_reference.py',
    'implementation/tools/fetch_real_data.py',
    'implementation/tools/fetch_stooq_prices.py',
    'implementation/tools/fetch_tiingo_prices.py',
    'implementation/tools/import_bulk_real_data.py',
    'implementation/tools/live_smoke.py',
    'implementation/tools/nport_cross_check.py',
    'implementation/tools/nport_reported_prices.py',
    'implementation/tools/official_pipeline.py',
    'implementation/tools/pages_artifact_guard.py',
    'implementation/tools/prepare_ca_unit_evidence.py',
    'implementation/tools/run_top500_gate_chain.py',
)


def require_public_catalog(name, value):
    from .product.entity_catalog import entity_catalog
    from .product.device_actual_catalog import public_actual_catalog
    expected = entity_catalog(public_bundle()) if name == 'entities.json' else public_actual_catalog()
    if value != expected:
        block_public_route()


# Facts admitted by the existing SEC financial/share-count consumers. Market
# float, market-price, option fair-value and unknown extension concepts are absent.
FINANCIAL_CONCEPTS = frozenset({
    'Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenue',
    'RevenueFromContractWithCustomerIncludingAssessedTax', 'SalesRevenueNet',
    'NetIncomeLoss', 'ProfitLoss', 'OperatingIncomeLoss', 'OperatingProfitLoss',
    'CashAndCashEquivalentsAtCarryingValue', 'CashAndCashEquivalents',
    'LongTermDebt', 'LongTermDebtNoncurrent', 'LongTermDebtCurrent', 'ShortTermBorrowings',
    'StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'Equity', 'EquityAttributableToOwnersOfParent', 'Assets', 'Liabilities',
    'CommonStockSharesOutstanding', 'EntityCommonStockSharesOutstanding',
    'WeightedAverageNumberOfDilutedSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic',
    'FreeCashFlow', 'NetCashProvidedByUsedInOperatingActivities',
    'CashFlowsFromUsedInOperatingActivities', 'PaymentsToAcquirePropertyPlantAndEquipment',
    'PurchaseOfPropertyPlantAndEquipment', 'EarningsPerShareDiluted', 'EarningsPerShareBasic',
    'BasicEarningsLossPerShare', 'DilutedEarningsLossPerShare',
})


def project_companyfacts(payload):
    """Keep typed financial facts, never raw response fragments or arbitrary labels."""
    import math
    import re
    if not isinstance(payload, dict) or not isinstance(payload.get('facts'), dict):
        block_public_route()
    result = {'facts': {}}
    for taxonomy in ('us-gaap', 'ifrs-full', 'dei'):
        concepts = payload['facts'].get(taxonomy, {})
        if not isinstance(concepts, dict):
            block_public_route()
        clean = {}
        for concept, item in concepts.items():
            if concept not in FINANCIAL_CONCEPTS:
                continue
            if not isinstance(item, dict) or not isinstance(item.get('units'), dict):
                block_public_route()
            units = {}
            for unit, rows in item['units'].items():
                if unit not in {'USD', 'EUR', 'KRW', 'JPY', 'shares', 'Shares', 'USD/shares', 'EUR/shares', 'USD-per-shares', 'pure'}:
                    continue
                if not isinstance(rows, list):
                    block_public_route()
                projected = []
                for row in rows:
                    if (not isinstance(row, dict) or type(row.get('val')) not in (int, float)
                            or not math.isfinite(row['val'])):
                        block_public_route()
                    fact = {'val': row['val']}
                    for key in ('filed', 'start', 'end'):
                        if key in row:
                            if not isinstance(row[key], str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row[key]):
                                block_public_route()
                            fact[key] = row[key]
                    if row.get('form') in {'10-K', '10-Q', '10-K/A', '10-Q/A', '20-F', '20-F/A', '40-F', '40-F/A', '6-K', '8-K'}:
                        fact['form'] = row['form']
                    if type(row.get('fy')) is int and 1900 <= row['fy'] <= 2200:
                        fact['fy'] = row['fy']
                    if row.get('fp') in {'FY', 'Q1', 'Q2', 'Q3', 'Q4'}:
                        fact['fp'] = row['fp']
                    if isinstance(row.get('accn'), str) and re.fullmatch(r'[0-9]{10}-[0-9]{2}-[0-9]{6}', row['accn']):
                        fact['accn'] = row['accn']
                    if isinstance(row.get('frame'), str) and re.fullmatch(r'CY[0-9]{4}(?:Q[1-4])?I?', row['frame']):
                        fact['frame'] = row['frame']
                    projected.append(fact)
                units[unit] = projected
            clean[concept] = {'units': units}
        if clean:
            result['facts'][taxonomy] = clean
    return result
