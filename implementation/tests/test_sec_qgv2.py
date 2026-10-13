"""QGV v2 Q·G: SEC factor math, percentile publication, `sec-qgv2.json` validators and daily wiring (synthetic data only)."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import urllib.error

import pytest

from investment_system.qgv import v2_factors as vf
from investment_system.qgv import v2_scoring as vs
from investment_system.universe import sec_qgv2 as q
from investment_system.universe import sec_universe_shares as shares
from investment_system.universe import sec_universe_qg as qg

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 13, 22, 30, tzinfo=timezone.utc)
CUTOFF = NOW.date()


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_qgv2_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REF = load_tool('sec_qgv2_reference')


# ---------------- hand-checkable company ----------------
def fact(facts, concept, unit, value, end, *, start=None, form='10-K', filed=None, accn='0000000001-26-000001', taxonomy='us-gaap'):
    row = {'end': end, 'val': value, 'accn': accn, 'form': form, 'filed': filed or (str(int(end[:4]) + 1) + '-02-15'), 'fp': 'FY', 'fy': 2025}
    if start is not None:
        row['start'] = start
    facts.setdefault(taxonomy, {}).setdefault(concept, {'units': {}})['units'].setdefault(unit, []).append(row)


def simple_company(*, years=range(2019, 2026), extra=None, omit=()):
    """Revenue +10%/yr (146.41 in 2025), EBIT 20%, pretax = EBIT, tax 25%, NI = 75% of EBIT, equity 100, debt 50, cash 30."""
    facts = {}
    for year in years:
        k = 2025 - year
        rev = 146.41 / 1.1 ** k
        span = dict(start=f'{year}-01-01', end=f'{year}-12-31')
        for concept, unit, value in (('Revenues', 'USD', rev), ('OperatingIncomeLoss', 'USD', 0.2 * rev),
                                     ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'USD', 0.2 * rev),
                                     ('IncomeTaxExpenseBenefit', 'USD', 0.05 * rev), ('NetIncomeLoss', 'USD', 0.15 * rev),
                                     ('NetCashProvidedByUsedInOperatingActivities', 'USD', 0.18 * rev),
                                     ('PaymentsToAcquirePropertyPlantAndEquipment', 'USD', 0.03 * rev),
                                     ('DepreciationDepletionAndAmortization', 'USD', 0.05 * rev), ('InterestExpense', 'USD', 2.0),
                                     ('GrossProfit', 'USD', 0.5 * rev), ('EarningsPerShareDiluted', 'USD/shares', 0.15 * rev / 10),
                                     ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 10.0)):
            if concept not in omit:
                fact(facts, concept, unit, value, span['end'], start=span['start'])
        for concept, value in (('Assets', 200.0), ('StockholdersEquity', 100.0), ('LongTermDebtNoncurrent', 40.0),
                               ('LongTermDebtCurrent', 10.0), ('CashAndCashEquivalentsAtCarryingValue', 30.0)):
            if concept not in omit:
                fact(facts, concept, 'USD', value, f'{year}-12-31')
    for args in extra or ():
        fact(facts, *args[0], **args[1])
    return {'cik': 1, 'facts': facts}


def compute(payload, sic='3674', cutoff=CUTOFF):
    return vf.compute(payload, sic=sic, cutoff=cutoff)


def test_general_metrics_match_hand_computation():
    profile, fy_end, currency, m, v = compute(simple_company())
    assert (profile, fy_end, currency) == ('GENERAL', '2025-12-31', 'USD')
    ic = 100 + 50 - 30  # equity + (noncurrent + current debt) - cash
    close = lambda a, b: math.isclose(a, b, rel_tol=1e-5)
    assert close(m['roic'], 0.2 * 146.41 * 0.75 / ic)
    assert close(m['gross_profit_to_assets'], 0.5 * 146.41 / 200)
    assert close(m['accruals_to_assets'], (0.15 - 0.18) * 146.41 / 200)
    assert close(m['fcf_to_net_income'], (0.18 - 0.03) / 0.15)
    assert close(m['net_debt_to_ebitda'], (50 - 30) / (0.25 * 146.41))
    assert close(m['interest_coverage'], 0.2 * 146.41 / 2)
    assert close(m['revenue_cagr_3y'], 0.1) and close(m['eps_cagr_3y'], 0.1) and close(m['fcf_per_share_cagr_3y'], 0.1)
    assert m['dilution_3y'] == 0.0  # constant share count: a real 0, not a fill
    assert m['incremental_roic_3y'] is None and m['incremental_roic_5y'] is None  # invested capital did not grow -> NA
    assert m['revenue_positive_growth_share'] == 1.0 and m['revenue_growth_volatility'] < 1e-6
    assert m['moat_return_years'] == 5 and close(m['moat_proxy'], m['moat_return_mean_5y'] - m['moat_return_std_5y'])
    assert close(m['revenue_ttm_growth'], 0.1) and abs(m['revenue_acceleration']) < 1e-5  # no 10-Q after FY0: TTM = FY
    for key in ('roe', 'roa', 'equity_to_assets', 'book_value_per_share_cagr_3y'):
        assert m[key] is None  # FINANCIAL-only metrics stay NA for GENERAL issuers
    assert v['ebit'] == {'fy_value': 0.2 * 146.41, 'fy_end': '2025-12-31', 'ttm_value': 0.2 * 146.41, 'ttm_end': '2025-12-31'}
    assert v['total_debt'] == {'value': 50.0, 'period_end': '2025-12-31'} and v['cash_and_equivalents'] == {'value': 30.0, 'period_end': '2025-12-31'}
    assert v['diluted_shares'] == {'value': 10.0, 'period_end': '2025-12-31'}
    assert [h['fiscal_year_end'] for h in v['ebit_per_share_history']] == [f'{y}-12-31' for y in range(2021, 2026)]


def test_ttm_uses_fy_plus_ytd_minus_prior_ytd_and_incremental_capital_rule():
    extra = []
    for year, value in ((2026, 80.0), (2025, 70.0), (2024, 60.0)):
        extra.append((('Revenues', 'USD', value, f'{year}-06-30'), {'start': f'{year}-01-01', 'form': '10-Q', 'filed': f'{year}-08-01'}))
    _, _, _, m, v = compute(simple_company(extra=extra))
    ttm = 146.41 + 80 - 70
    ttm_ago = 146.41 / 1.1 + 70 - 60
    assert math.isclose(m['revenue_ttm_growth'], ttm / ttm_ago - 1, rel_tol=1e-5)
    assert math.isclose(m['revenue_acceleration'], m['revenue_ttm_growth'] - m['revenue_cagr_3y'], abs_tol=2e-6)
    assert v['ebit']['ttm_end'] == '2025-12-31'  # no EBIT 10-Q facts -> TTM equals FY for EBIT


def test_revision_cutoff_and_ambiguity_rules():
    # Later 10-K/A restates FY2025 revenue: latest filed wins. A fact filed after the cutoff is ignored.
    extra = [(('Revenues', 'USD', 150.0, '2025-12-31'), {'start': '2025-01-01', 'form': '10-K/A', 'filed': '2026-05-01'}),
             (('Revenues', 'USD', 999.0, '2025-12-31'), {'start': '2025-01-01', 'form': '10-K/A', 'filed': '2026-12-01'})]
    _, _, _, m, _ = compute(simple_company(extra=extra))
    assert math.isclose(m['revenue_cagr_3y'], (150 / 110) ** (1 / 3) - 1, rel_tol=1e-5)
    # Same filed date, different values -> the period is dropped (FY0 falls back to the next concept or NA).
    clash = [(('Revenues', 'USD', 151.0, '2025-12-31'), {'start': '2025-01-01', 'form': '10-K', 'filed': '2026-02-15'})]
    _, _, _, m, _ = compute(simple_company(extra=clash))
    assert m['revenue_cagr_3y'] is None and m['revenue_acceleration'] is None


def test_missing_or_meaningless_inputs_are_none_never_zero():
    _, _, _, m, v = compute(simple_company(omit=('InterestExpense', 'DepreciationDepletionAndAmortization', 'LongTermDebtNoncurrent',
                                                  'LongTermDebtCurrent', 'GrossProfit')))
    assert m['interest_coverage'] is None and m['net_debt_to_ebitda'] is None and m['gross_profit_to_assets'] is None
    assert m['roic'] is None  # invested capital needs a reported debt line
    assert v['total_debt'] is None
    # Negative earnings: FCF/NI and EPS CAGR are not meaningful.
    loss = simple_company()
    for row in loss['facts']['us-gaap']['NetIncomeLoss']['units']['USD']:
        row['val'] = -abs(row['val'])
    for row in loss['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']:
        row['val'] = -abs(row['val'])
    _, _, _, m, _ = compute(loss)
    assert m['fcf_to_net_income'] is None and m['eps_cagr_3y'] is None
    # No annual facts at all -> no fiscal year, nothing published.
    assert compute({'cik': 1, 'facts': {}})[1] is None
    assert compute(b'not json')[1] is None and compute({'cik': 1, 'facts': {'us-gaap': []}})[1] is None


def test_financial_profile_uses_roe_capital_ratio_nim_and_skips_earnings_quality():
    extra = [(('InterestIncomeExpenseNet', 'USD', 30.0, f'{y}-12-31'), {'start': f'{y}-01-01'}) for y in range(2019, 2026)]
    profile, _, _, m, _ = compute(simple_company(extra=extra), sic='6021')
    assert profile == 'FINANCIAL'
    assert math.isclose(m['roe'], 0.15 * 146.41 / 100, rel_tol=1e-5) and math.isclose(m['equity_to_assets'], 0.5)
    assert math.isclose(m['net_interest_income_to_assets'], 30 / 200) and math.isclose(m['roa'], 0.15 * 146.41 / 200, rel_tol=1e-5)
    assert m['roic'] is None and m['accruals_to_assets'] is None and m['fcf_to_net_income'] is None
    assert vs.SUBMETRICS['FINANCIAL']['q_earnings_quality'] == ()
    assert vf.profile_for_sic('6499') == 'FINANCIAL' and vf.profile_for_sic('6500') == 'GENERAL' and vf.profile_for_sic(None) == 'GENERAL'


def test_ifrs_filer_and_52_53_week_years():
    facts = {}
    for year, end in ((2022, '2022-12-25'), (2023, '2023-12-31'), (2024, '2024-12-29'), (2025, '2025-12-28')):
        start = {2022: '2021-12-27', 2023: '2022-12-26', 2024: '2024-01-01', 2025: '2024-12-30'}[year]
        fact(facts, 'Revenue', 'EUR', 100.0 * 1.2 ** (year - 2022), end, start=start, form='20-F', taxonomy='ifrs-full')
        fact(facts, 'ProfitLoss', 'EUR', 10.0, end, start=start, form='20-F', taxonomy='ifrs-full')
    profile, fy_end, currency, m, v = compute({'cik': 1, 'facts': facts})
    assert (fy_end, currency, v['taxonomy']) == ('2025-12-28', 'EUR', 'ifrs-full')
    assert math.isclose(m['revenue_cagr_3y'], 0.2, rel_tol=1e-5)


# ---------------- percentile publication ----------------
def test_percentile_formula_ties_and_direction():
    assert vs.percentile(0, 1, 9) == 0 and vs.percentile(8, 1, 9) == 100 and vs.percentile(4, 1, 9) == 50
    assert vs.percentile(0, 9, 9) == 50  # all tied -> average rank
    rows = {f'X:{n}': {'cik': str(n).zfill(10), 'state': 'LIVE', 'profile': 'GENERAL', 'industry_group': 'g',
                       'metrics': {'revenue_cagr_3y': float(n % 5), 'revenue_growth_volatility': float(n)}} for n in range(1, 11)}
    scores, summary = vs.score_rows(rows)
    assert summary == {'cross_section_size': 10, 'cross_section_by_profile': {'GENERAL': 10, 'FINANCIAL': 0}}
    top, low = scores[('universe', 'X:4')], scores[('universe', 'X:5')]
    assert top['factors']['g_revenue_growth'] == 100 * (8 + 0.5) / 9  # value 4 (twice) above 8 others
    assert low['factors']['g_revenue_growth'] == 100 * 0.5 / 9  # value 0 (twice) is the lowest
    assert scores[('universe', 'X:1')]['factors']['g_consistency'] == 100  # lowest volatility is best
    axis = top['axes']['G']
    # only 2 of 5 G factors (weights 25 + 15 = 40 < 50) -> axis NA with the fixed reason; factors_available still published
    assert axis['score'] is None and axis['reason_codes'] == ['AXIS_COVERAGE_BELOW_50'] and axis['factors_available'] == '2/5'
    assert axis['available_weight'] == 40 and axis['peer_basis'] == 'UNIVERSE' and axis['peer_count'] == 10


def _row(n, profile='GENERAL', group='g', state='LIVE', **metrics):
    return {'cik': str(n).zfill(10), 'state': state, 'profile': profile, 'industry_group': group, 'metrics': metrics}


def test_peer_groups_fallback_financial_isolation_and_target_replacement():
    universe = {f'A:{n}': _row(n, group='big', roic=n / 100, revenue_cagr_3y=n / 50) for n in range(1, 9)}
    universe.update({f'B:{n}': _row(n, group='small', roic=n / 10) for n in range(20, 23)})
    universe.update({f'F:{n}': _row(n, profile='FINANCIAL', group='finance_real_estate', roe=n / 100) for n in range(40, 47)})
    universe['N:1'] = _row(99, state='NOT_AVAILABLE', roic=9.0)  # not in the cross-section
    target = {'t': _row(5, group='big', roic=0.5, revenue_cagr_3y=0.5)}  # same CIK as A:5, fresher values
    scores, summary = vs.score_rows(universe, target)
    assert summary['cross_section_size'] == 18 and summary['cross_section_by_profile'] == {'GENERAL': 11, 'FINANCIAL': 7}
    a1 = scores[('universe', 'A:1')]['axes']['Q']
    assert a1['peer_basis'] == 'INDUSTRY_GROUP' and a1['peer_count'] == 8
    b = scores[('universe', 'B:20')]['axes']['Q']
    assert b['peer_basis'] == 'UNIVERSE_FALLBACK' and b['peer_count'] == 11  # group of 3 < 8
    fin = scores[('universe', 'F:40')]['axes']
    assert fin['Q']['reason_codes'] == ['PEERS_BELOW_MINIMUM'] and fin['Q']['peer_count'] == 7 and fin['Q']['peer_basis'] == 'FINANCIAL_PROFILE'
    t = scores[('target', 't')]
    # TARGET replaces its own issuer point: still 8 peers in the group, and 0.5 is the top ROIC there.
    assert t['axes']['Q']['peer_count'] == 8 and t['factors']['q_profitability'] == 100
    assert scores[('universe', 'A:8')]['factors']['q_profitability'] == 100  # the universe row itself is unchanged by TARGET
    assert scores[('universe', 'N:1')]['axes']['Q']['reason_codes'] == ['ROW_NOT_AVAILABLE']


def test_weights_are_the_candidate_defaults_and_v1_is_unchanged():
    assert vs.Q_WEIGHTS_V2 == {'q_profitability': 25, 'q_moat_proxy': 20, 'q_earnings_quality': 20, 'q_financial_safety': 20, 'q_capital_allocation': 15}
    assert vs.G_WEIGHTS_V2 == {'g_revenue_growth': 25, 'g_per_share_growth': 25, 'g_growth_efficiency': 20, 'g_consistency': 15, 'g_recent_acceleration': 15}
    from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS
    assert Q_WEIGHTS['competitive_advantage'] == 0.20 and G_WEIGHTS['next_3_5y_growth'] == 0.25 and len(Q_WEIGHTS) == 7
    assert set(vs.FACTOR_IDS).isdisjoint(Q_WEIGHTS) and set(vs.FACTOR_IDS).isdisjoint(G_WEIGHTS)
    for profile in vs.SUBMETRICS.values():
        assert set(profile) == set(vs.FACTOR_IDS)
        for specs in profile.values():
            assert all(metric in vf.METRIC_KEYS and direction in (1, -1) for metric, direction in specs)


# ---------------- public file ----------------
def payload():
    return REF.base()


def test_publication_scores_universe_and_target_with_coverage_and_no_price():
    p = payload()
    assert p['cross_section_size'] == 27 and p['cross_section_by_profile'] == {'GENERAL': 18, 'FINANCIAL': 9}
    rows = [p['records'][c] for c in REF._codes()]
    assert all(r['state'] == 'LIVE' and r['axes']['Q']['score'] is not None and r['axes']['G']['score'] is not None for r in rows)
    semis = p['records'][REF._codes()[0]]
    assert semis['industry_group'] == 'manufacturing_industrial_tech' and semis['axes']['Q']['peer_basis'] == 'INDUSTRY_GROUP'
    software = p['records'][REF._codes()[11]]
    assert software['axes']['Q']['peer_basis'] == 'UNIVERSE_FALLBACK' and software['axes']['G']['peer_basis'] == 'UNIVERSE'
    fin = p['records'][REF._codes()[20]]
    assert fin['profile'] == 'FINANCIAL' and fin['axes']['Q']['factors_available'] == '4/5' and fin['factors']['q_earnings_quality'] is None
    assert p['target']['hanmi']['reason_codes'] == ['NON_SEC_ISSUER'] and p['target']['tokyo_electron']['state'] == 'NOT_AVAILABLE'
    assert p['target']['nvda']['state'] == 'LIVE' and p['target']['nvda']['axes']['Q']['peer_count'] == 14
    assert p['target']['asml']['reason_codes'] == ['NOT_COLLECTED']
    empty = p['records']['NYSE:MMM'] if 'NYSE:MMM' not in REF._codes() else p['records'][shares.universe_codes()[100]]
    assert empty['metrics'] == {} and all(v is None for v in empty['factors'].values())
    text = q.encode(p).decode().lower()
    assert '987654321' not in text and 'stockprice' not in text and '"price"' not in text and 'market_cap' not in text and '"rank' not in text
    v = p['target']['nvda']['v_inputs_v2']
    assert set(v) == set(vf.V_KEYS) and v['ebit']['ttm_end'] == '2026-06-30' and v['fcf']['fy_end'] == '2025-12-31'
    assert len(v['ebit_per_share_history']) == 5 and v['diluted_shares']['value'] > 0


def test_merge_carries_rows_never_erases_and_ages_them():
    p = payload()
    code = REF._codes()[0]
    later = NOW + timedelta(days=3)
    nodata = q.build_row(cik=p['records'][code]['cik'], companyfacts_body=b'{"cik":1000,"facts":{}}',
                         submissions_body=b'{"cik":1000,"sic":"3674"}', acquired_at=later)
    assert nodata['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS'] and nodata['sic'] == '3674'
    kept = q.merge(p, {code: nodata}, as_of=later, shard_index=4)
    assert kept['records'][code]['metrics'] == p['records'][code]['metrics'] and kept['records'][code]['acquired_at'] == p['records'][code]['acquired_at']
    stale = q.merge(kept, {}, as_of=NOW + timedelta(days=15), shard_index=5)
    row = stale['records'][code]
    assert row['state'] == 'STALE' and row['reason_codes'] == ['STALE_INPUT'] and row['axes']['Q']['score'] is not None
    assert stale['cross_section_size'] == 27  # STALE rows stay in the cross-section
    assert stale['target']['nvda']['state'] == 'STALE'  # TARGET rows age by the same window when not refreshed
    bad = json.loads(json.dumps(p['records'][code]))
    bad['metrics']['roic'] = float('inf')
    downgraded = q.merge(None, {code: bad}, as_of=NOW, shard_index=0)
    assert downgraded['records'][code]['reason_codes'] == ['INVALID_INPUT'] and downgraded['records'][code]['state'] == 'NOT_AVAILABLE'
    unresolved = q.merge(None, {}, as_of=NOW, shard_index=0, unresolved={'BATS:CBOE'})
    assert unresolved['records']['BATS:CBOE']['reason_codes'] == ['CIK_UNRESOLVED'] and unresolved['state'] == 'NOT_AVAILABLE'


def test_issuer_codes_share_one_row_and_one_cross_section_point():
    facts, subs = REF.synthetic_sec('0001652044', seed=3)
    rows = q.build_issuer_records(codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'), cik='0001652044', companyfacts_body=facts,
                                  submissions_body=subs, acquired_at=NOW)
    p = q.merge(payload(), rows, as_of=NOW, shard_index=1)
    live = [r for r in p['records'].values() if r['state'] != 'NOT_AVAILABLE']
    assert p['records']['NASDAQ:GOOGL'] == p['records']['NASDAQ:GOOG']
    assert sum(1 for r in live if r['cik'] == '0001652044') == 2 and p['cross_section_size'] == len({r['cik'] for r in live}) == len(live) - 1


def test_build_row_rejects_cik_mismatch_and_untrusted_bytes():
    facts, subs = REF.synthetic_sec('0000001000')
    assert q.build_row(cik='0000001001', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)['reason_codes'] == ['INVALID_INPUT']
    for bad in (b'{"cik":1000,"a":NaN}', b'{"cik":1000,"cik":2}', b'\xff', b'[]'):
        r = q.build_row(cik='0000001000', companyfacts_body=bad, submissions_body=subs, acquired_at=NOW)
        assert r['state'] == 'NOT_AVAILABLE' and r['reason_codes'] == ['INVALID_INPUT']
    assert q.build_row(cik='1', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)['cik'] is None
    assert q.build_row(cik='0000001000', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW.replace(tzinfo=None))['acquired_at'] is None


def test_size_at_504_issuers_stays_below_the_public_file_limit():
    from investment_system.universe.sec_universe_shares import universe_codes
    updates = {}
    for n, code in enumerate(universe_codes()):
        cik = str(5000 + n).zfill(10)
        facts, subs = REF.synthetic_sec(cik, sic=['3674', '7372', '2834', '6021', '4911', '5411'][n % 6], seed=n,
                                        growth=0.01 * (n % 13), financial=n % 6 == 3, revenue0=391035000000.0 + n * 7919)
        updates.update(q.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=facts, submissions_body=subs, acquired_at=NOW))
    full = q.merge(None, updates, as_of=NOW, shard_index=1, target_updates=REF.synthetic_target_updates())
    body = q.encode(full)
    assert full['cross_section_size'] == 504 and len(body) < 1.8 * 1024 * 1024 < q.MAX_BYTES
    assert len(q.encode(q.merge(None, {}, as_of=NOW, shard_index=None))) < 700 * 1024


# ---------------- validators (Python; JS parity through the shared vectors) ----------------
def test_vectors_fixture_is_regenerated_from_the_python_validator():
    fixture = json.loads((ROOT / 'tests/fixtures/sec_qgv2_vectors_v1.json').read_text())
    assert fixture == json.loads(json.dumps(REF.build()))
    assert fixture['synthetic'] is True and len(fixture['cases']) >= 40
    assert [c['id'] for c in fixture['cases'] if c['valid']] == ['base_valid', 'null_shard_and_registry_valid']


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_js_validator_reaches_the_python_verdict_and_recomputes_scores():
    result = subprocess.run(['node', str(ROOT / 'tools/sec_qgv2_node_test.js')], text=True, capture_output=True, timeout=180)
    assert result.returncode == 0 and 'fail=0' in result.stdout


@pytest.mark.parametrize('path,value', [
    (('price',), 1), (('records', 'NYSE:MMM', 'factors', 'q_profitability'), 50.0), (('target', 'nvda', 'axes', 'Q', 'score'), 1.0),
    (('method', 'weights', 'G', 'g_consistency'), 16), (('cross_section_size',), 1), (('standard_status',), 'CALIBRATED'),
])
def test_validator_is_strict(path, value):
    p = payload()
    target = p
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        q.require_qgv2(p)


def test_json_parser_rejects_nonfinite_duplicates_and_oversize():
    for body in (b'{"a":NaN}', b'{"a":1,"a":2}', b'\xff', b'x' * (q.MAX_BYTES + 1)):
        with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
            q.parse_json(body)
    assert q.require_qgv2(q.parse_json(q.encode(payload())))['state'] == 'LIVE'


def test_pages_guard_allows_valid_file_and_rejects_tampered_or_priced_values(tmp_path):
    build = load_tool('build_pages_cockpit')
    guard = load_tool('pages_artifact_guard')
    site = tmp_path / 'site'
    build.build_public_cockpit(site)
    assert not (site / q.FILENAME).exists() and (site / 'sec-qgv2.js').exists()  # offline builds do not publish the data file
    (site / q.FILENAME).write_bytes(q.encode(payload()))
    assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    tampered = payload()
    tampered['target']['nvda']['factors']['g_revenue_growth'] = 0
    (site / q.FILENAME).write_text(json.dumps(tampered))
    receipt = guard.scan_artifact(site)
    assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('qgv2_boundary') == 1
    priced = payload()
    priced['target']['nvda']['v_inputs_v2']['price'] = 1
    (site / q.FILENAME).write_text(json.dumps(priced))
    violations = guard.scan_artifact(site)['violations']
    assert violations.get('sensitive_json_fields') == 1 and violations.get('qgv2_boundary') == 1


# ---------------- daily wiring: shard tool + TARGET stage (mocked transports only) ----------------
from tests.test_sec_universe_qg import UA, client_kwargs, day_for, pages, ticker_body, transport_for  # noqa: E402


def staged_target(folder, when):
    rows = REF.synthetic_target_updates(acquired_at=when - timedelta(minutes=30))
    (folder / q.FILENAME).write_bytes(q.encode(q.merge(None, {}, as_of=when - timedelta(minutes=20), shard_index=None, target_updates=rows)))


def test_shard_tool_one_fetch_feeds_v2_and_carries_the_staged_target(tmp_path, capsys):
    from investment_system.providers.sec_universe_collection import daily_partition, universe_registry
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    staged_target(tmp_path, when)
    calls = []
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for(calls), when), open_previous=pages({}))
    out = capsys.readouterr().out
    shard = [i.cik for i in daily_partition(universe_registry(ticker_body()), shard_count=7, shard_index=when.date().toordinal() % 7)]
    assert code == 0 and len(calls) == len(set(calls)) == 1 + 3 * len(shard)  # no extra SEC request for v2
    p = q.require_qgv2(json.loads((tmp_path / q.FILENAME).read_text()))
    assert p['records']['NYSE:BRK.B']['state'] == 'LIVE' and p['records']['NYSE:BRK.B']['metrics']['revenue_cagr_3y'] is not None
    assert p['target']['nvda']['state'] == 'LIVE' and p['target']['amd']['acquired_at'] == '2026-' + p['target']['amd']['acquired_at'][5:]
    assert p['last_shard_index'] == when.date().toordinal() % 7 and p['registry_sha256'] == sha256(ticker_body()).hexdigest()
    lines = [l for l in out.splitlines() if l.startswith('SEC_QGV2')]
    assert 'SEC_QGV2 PREVIOUS_RESTORED staged_target=3' in lines and any(l.startswith(f'SEC_QGV2 shard={when.date().toordinal() % 7}/7 ') for l in lines)
    for secret in (UA, 'tester@', '0000000002', 'sec.gov', 'BRK', 'nvda', 'revenue'):
        assert secret not in out
    assert (tmp_path / qg.FILENAME).exists() and (tmp_path / shares.FILENAME).exists()


def test_shard_tool_v2_failures_never_change_the_other_files(tmp_path, monkeypatch, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    base_dir, broken = tmp_path / 'a', tmp_path / 'b'
    base_dir.mkdir()
    broken.mkdir()
    tool.run(base_dir, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when, client_kwargs=client_kwargs(transport_for([]), when), open_previous=pages({}))
    def boom(*_, **__):
        raise RuntimeError('synthetic')
    monkeypatch.setattr(tool.qgv2, 'build_issuer_records', boom)
    monkeypatch.setattr(tool.qgv2, 'merge', boom)
    assert tool.run(broken, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when, client_kwargs=client_kwargs(transport_for([]), when),
                    open_previous=pages({})) == 0
    assert 'SEC_QGV2 OUTPUT_FAILED previous_kept' in capsys.readouterr().out
    for name in (shares.FILENAME, qg.FILENAME):
        assert (broken / name).read_bytes() == (base_dir / name).read_bytes()
    assert not (broken / q.FILENAME).exists()


def test_shard_tool_previous_handling(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    previous = q.encode(payload())
    # preserve-only restores the previous copy (ages rows) and keeps its scores
    keep = tmp_path / 'keep'
    keep.mkdir()
    assert tool.run(keep, live=False, preserve_only=True, now=lambda: NOW + timedelta(hours=1), open_previous=pages({q.FILENAME: previous})) == 0
    assert 'SEC_QGV2 PREVIOUS_RESTORED' in capsys.readouterr().out
    restored = q.require_qgv2(json.loads((keep / q.FILENAME).read_text()))
    assert restored['records'][REF._codes()[0]]['axes'] == json.loads(previous)['records'][REF._codes()[0]]['axes']
    # an invalid previous copy is discarded; nothing to write in preserve-only
    other = tmp_path / 'other'
    other.mkdir()
    assert tool.run(other, live=False, preserve_only=True, open_previous=pages({q.FILENAME: b'{"price":1}'})) == 0
    out = capsys.readouterr().out
    assert 'SEC_QGV2 PREVIOUS_DISCARDED' in out and 'SEC_QGV2 PREVIOUS_NOT_AVAILABLE' in out and not (other / q.FILENAME).exists()
    # a network failure on the previous v2 copy writes nothing and exits 1 (same rule as the other two files)
    net = tmp_path / 'net'
    net.mkdir()
    assert tool.run(net, live=True, environ={'SEC_USER_AGENT': UA}, open_previous=pages({q.FILENAME: urllib.error.URLError('x')})) == 1
    assert 'SEC_QGV2 PREVIOUS_FETCH_FAILED' in capsys.readouterr().out and not list(net.iterdir())
    # an invalid staged TARGET file is discarded, never published as is
    bad = tmp_path / 'bad'
    bad.mkdir()
    (bad / q.FILENAME).write_text('{"price":1}')
    assert tool.run(bad, live=False, preserve_only=True, open_previous=pages({q.FILENAME: previous}), now=lambda: NOW) == 0
    assert 'SEC_QGV2 STAGED_TARGET_DISCARDED' in capsys.readouterr().out
    assert q.require_qgv2(json.loads((bad / q.FILENAME).read_text()))['target']['nvda']['state'] == 'LIVE'


def test_target_stage_writes_valid_file_from_pipeline_bytes(tmp_path, capsys):
    pipeline = load_tool('public_screens_pipeline')
    root = tmp_path / 'raw'
    root.mkdir()
    site = tmp_path / 'site'
    site.mkdir()
    manifest = {'sec': []}
    for n, company_id in enumerate(('nvda', 'msft')):
        facts, subs = REF.synthetic_sec(q.target_cik(company_id), seed=n)
        (root / f'{company_id}-f.json').write_bytes(facts)
        (root / f'{company_id}-s.json').write_bytes(subs)
        manifest['sec'].append({'company_id': company_id, 'companyfacts': f'{company_id}-f.json', 'submissions': f'{company_id}-s.json',
                                'acquired_at': NOW.isoformat(), 'synthetic': False})
    staged = pipeline.stage_qgv2_target(site, manifest, root, now=NOW + timedelta(minutes=5))
    assert 'SEC_QGV2_TARGET staged companies=2 with_data=2' in capsys.readouterr().out
    p = q.require_qgv2(json.loads((site / q.FILENAME).read_text()))
    assert p == staged and p['target']['nvda']['state'] == 'LIVE' and p['target']['nvda']['metrics']
    # no Universe peers yet: TARGET axes are NA with a fixed reason, never 0
    assert p['target']['nvda']['axes']['Q']['reason_codes'] == ['PEERS_BELOW_MINIMUM'] and p['target']['nvda']['axes']['Q']['score'] is None
    assert p['records']['NYSE:MMM']['reason_codes'] == ['NOT_COLLECTED'] and p['target']['hanmi']['reason_codes'] == ['NON_SEC_ISSUER']
    assert pipeline.stage_qgv2_target(tmp_path / 'missing', manifest, root) is None
    assert 'SEC_QGV2_TARGET STAGE_FAILED' in capsys.readouterr().out


def test_workflows_manifests_and_offline_fixture_are_wired():
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    target_step = daily.index('python implementation/tools/public_screens_pipeline.py --live')
    shard_step = daily.index('python implementation/tools/sec_universe_shares.py --live --out "$RUNNER_TEMP/public-cockpit"')
    assert target_step < shard_step < daily.index('actions/upload-pages-artifact')  # TARGET stage first, shard publish second
    pages_yml = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    assert 'python implementation/tools/sec_universe_shares.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"' in pages_yml
    assert 'sec_qgv2_node_test.js' in (ROOT / 'tools/ci_node_tests.txt').read_text().split()
    assert "'sec-qgv2.json'" in (ROOT / 'tools/empty_public_screens.js').read_text()
    assert '<script src="sec-qgv2.js"></script>' in (ROOT / 'src/investment_system/product/web_assets/index.html').read_text()
    guard = (ROOT / 'tools/pages_artifact_guard.py').read_text()
    assert guard.count('\nALLOWED_NAMES') == 1 and 'QGV2_FILENAME' in guard.split('\nALLOWED_NAMES', 1)[1].split('\n', 1)[0]
