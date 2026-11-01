"""Runner: selection stage of two signal years (hysteresis carried via the previous U-A) and the ledger stage (LOSS /
CARRY x 0 / 10 bp, group equal-weight benchmark, cash years). Synthetic bundle only (exp_deciles_synthetic)."""
import copy
from datetime import date
from decimal import Decimal, localcontext
import json

import pytest

import exp_deciles_synthetic as syn
from investment_system.research.exp_deciles import benchmarks, handoff, ledger, runner, settings

END = '2019-03-29'


def select(year, previous=None, **kw):
    """previous: runner.u_a_state of the previous selection (members and UNKNOWN units) or None."""
    facts = kw.pop('companyfacts', syn.companyfacts_by_cik())
    state = {} if previous is None else {'previous_u_a': previous['members'],
                                         'previous_u_a_unknown': previous['unknown'],
                                         'previous_u_a_securities': previous['securities']}
    kw.setdefault('terminations', syn.terminations(year))
    return runner.selection_stage(syn.records(year), year=year, companyfacts=facts, filing_rows=syn.filing_rows(),
                                  quotes=syn.quotes(year), **state, **kw)


@pytest.fixture(scope='module')
def years():
    s18 = select(2018)
    s19 = select(2019, runner.u_a_state(s18))
    return s18, s19


@pytest.fixture(scope='module')
def outputs(years):
    return runner.ledger_stage(list(years), prices=syn.price_rows(), events=syn.event_rows(), end=END,
                               tr_series=syn.tr_series())


def cik(i):
    return syn.cik(i).zfill(10)


# ---- selection stage ----------------------------------------------------------------------------------------------
def test_selection_stage_first_year_counts_statuses_scores_and_selections(years):
    s18, _ = years
    assert s18['schema'] == runner.SELECTION_SCHEMA and s18['stage'] == 'select'
    assert s18['settings_sha256'] == settings.settings_sha256() and s18['experiment_id'] == settings.EXPERIMENT_ID
    assert s18['signal']['S'] == '2018-02-16' and s18['signal']['T'] == '2018-02-20'
    assert s18['signal']['filing_cutoff'] == '2018-02-08' and s18['first_build'] is True and s18['flags'] == []
    counts = s18['counts']
    assert counts['U_A'] == {'candidate': 36, 'eligible': 30, 'excluded': 2, 'unknown': 4,
                             'excluded_by_reason': {'BELOW_U_A_ENTRY_THRESHOLD': 1, 'NO_LISTED_ELIGIBLE_SECURITY': 1},
                             'unknown_by_reason': {'ADR_RATIO_UNCONFIRMED': 1, 'SECURITY_TYPE_NOT_CANONICAL': 1,
                                                   'SHARES_NOT_USABLE_AT_S': 1, 'SHARE_PRICE_BASIS_UNCONFIRMED': 1}}
    assert counts['U_B']['eligible'] == 13 and counts['U_B']['excluded_by_reason'] == {
        'BELOW_U_B_THRESHOLD': 18, 'NO_LISTED_ELIGIBLE_SECURITY': 1}
    for group in settings.GROUPS:
        c = counts[group]
        assert c['candidate'] == c['eligible'] + c['excluded'] + c['unknown']
    assert counts['securities']['excluded_by_reason'] == {'NOT_ELIGIBLE_SECURITY_TYPE': 1}
    # every security's universe status and reasons
    secs = s18['universe']['securities']
    assert set(secs) == {syn.sid(i) for i in range(1, syn.N_ISSUERS + 1)}
    assert secs['XQ028']['reasons'] == ['NOT_ELIGIBLE_SECURITY_TYPE'] and secs['XQ025']['security_type'] == 'REIT'
    issuers = s18['universe']['issuers']
    assert issuers[cik(27)]['U_A']['reasons'] == ['ADR_RATIO_UNCONFIRMED']
    # ADR issuer cap = 600,000,000 / 2 x 30.2207 (exact Decimal, as text)
    assert Decimal(issuers[cik(26)]['market_cap_usd']) == Decimal('9066210000')
    # review F2: share counts usable at S and on a confirmed split basis, with provenance
    assert issuers[cik(35)]['U_A']['status'] == 'ELIGIBLE'
    assert issuers[cik(35)]['share_provenance'][0]['shares_filed'] == '2018-02-08'
    assert issuers[cik(36)]['U_A']['reasons'] == ['SHARES_NOT_USABLE_AT_S']
    assert issuers[cik(34)]['U_A']['reasons'] == ['SHARE_PRICE_BASIS_UNCONFIRMED']
    members = s18['universe']['U_A']['member_securities']
    assert len(members) == 30 and {'XQ026', 'XQ025', 'XQ015', 'XQ021'} <= set(members)
    assert not {'XQ033', 'XQ034', 'XQ036', 'XQ027'} & set(members)
    assert s18['universe']['U_A']['unknown'] == [cik(i) for i in (27, 29, 34, 36)]
    # PIT rows and scores exist for exactly the U-A population, at this S; the PIT boundary filings
    assert set(s18['pit']['rows']) == set(members) == set(s18['scores']['securities'])
    assert all(row['pit']['signal_day'] == '2018-02-16' for row in s18['pit']['rows'].values())
    assert s18['pit']['rows']['XQ023']['pit']['latest_filing_used']['filed'] == '2018-02-08'
    late = s18['pit']['rows']['XQ024']['pit']
    assert late['latest_filing_used']['filed'] == '2017-02-01' and late['rejected']['NOT_USABLE_AT_SIGNAL_DAY'] > 0
    assert s18['quote_basis'] == {'XQ026': 'ADR_PER_ORDINARY_SHARE'}
    g = s18['scores']['securities']['XQ026']
    assert set(g) >= {'axes', 'totals', 'factors', 'value_trap_gate', 'flags', 'axis_reasons', 'total_reasons'}
    # every scored member has Q, G, V and all four totals; every strategy cell runs in both groups
    assert counts['scoring']['axes_available'] == {'Q': 30, 'G': 30, 'V': 30}
    assert counts['scoring']['totals_available'] == {p: 30 for p in ('balanced', 'quality', 'growth', 'value')}
    for strategy in settings.STRATEGY_IDS:
        assert {g: (c['status'], c['N'], c['k']) for g, c in counts['strategies'][strategy].items()} == {
            'U_A': ('RUN', 30, 3), 'U_B': ('RUN', 13, 1)}
    sel = s18['selections']['AXIS_G']['U_A']
    assert len(sel['top']) == len(sel['bottom']) == 3 and sel['top'][0]['rank'] == 1 and sel['bottom'][-1]['rank'] == 30
    assert sel['top'][0]['score'] >= sel['bottom'][0]['score'] and len(sel['ranks']) == 30
    # QGV_DEFAULT is an alias, not a second selection
    assert 'QGV_DEFAULT' not in s18['selections'] and s18['strategy_aliases'] == {'QGV_DEFAULT': 'QGV_BALANCED'}
    assert set(s18['selections']) == set(settings.STRATEGY_IDS)


def test_exact_score_tie_is_ordered_by_security_id(years):
    for sel in years:
        scores = sel['scores']['securities']
        assert scores['XQ014']['axes'] == scores['XQ030']['axes'] and scores['XQ014']['totals'] == scores['XQ030']['totals']
        for strategy in settings.STRATEGY_IDS:
            run = sel['selections'][strategy]['U_A']
            order = list(run['order'])
            first, second = order.index('XQ014'), order.index('XQ030')
            assert first < second, strategy                      # equal scores: the lower security ID first
            assert run['ranks']['XQ030'] - run['ranks']['XQ014'] == second - first


def test_selection_stage_second_year_carries_hysteresis_through_previous_u_a(years):
    s18, s19 = years
    assert s19['first_build'] is False and s19['previous_u_a'] == s18['universe']['U_A']['members']
    assert s19['previous_u_a_unknown'] == s18['universe']['U_A']['unknown'] == runner.u_a_state(s18)['unknown']
    issuers = s19['universe']['issuers']
    assert issuers[cik(31)]['U_A'] == {'status': 'ELIGIBLE', 'reasons': [], 'basis': 'STAY'}       # 220m >= 200m stay
    assert issuers[cik(32)]['U_A'] == {'status': 'EXCLUDED', 'reasons': ['BELOW_U_A_STAY_THRESHOLD'], 'basis': 'STAY'}
    assert issuers[cik(33)]['U_A'] == {'status': 'EXCLUDED', 'reasons': ['BELOW_U_A_ENTRY_THRESHOLD'], 'basis': 'ENTRY'}
    # review F3: an UNKNOWN year is carried; a member without a record is an UNKNOWN candidate unless evidenced
    assert issuers[cik(34)]['U_A'] == {'status': 'UNKNOWN', 'reasons': ['PREVIOUS_U_A_STATUS_UNKNOWN'],
                                       'basis': 'PREVIOUS_STATUS_UNKNOWN'}
    assert issuers[cik(36)]['U_A'] == {'status': 'ELIGIBLE', 'reasons': [], 'basis': 'ENTRY'}
    assert issuers[cik(15)]['U_A'] == {'status': 'UNKNOWN', 'reasons': ['NOT_IN_RECORDS_AT_S'], 'basis': None}
    assert cik(21) not in issuers and s19['universe']['U_A']['terminated'][0]['cik'] == cik(21)
    assert s19['counts']['u_a_transitions'] == {
        'entered': 1, 'stayed': 27, 'left': 3,
        'left_by_reason': {'BELOW_U_A_STAY_THRESHOLD': 1, 'NOT_IN_RECORDS_AT_S': 1, 'TERMINATION_EVIDENCED': 1},
        'unknown_to_next_s': 4, 'terminated': 1}
    assert s19['counts']['U_A']['eligible'] == 28 and s19['counts']['U_A']['candidate'] == 35
    # U-B has no hysteresis: issuer 1 falls below 10bn (still U-A), the ADR rises above it
    ub = s19['universe']['U_B']['members']
    assert cik(1) not in ub and cik(26) in ub and cik(1) in s19['universe']['U_A']['members'] and len(ub) == 13
    # the split issuer's 2019 record is on the post-split basis: 200,000,000 x 115.3337
    assert Decimal(issuers[cik(13)]['market_cap_usd']) == Decimal('23066740000')
    # A first build in a later year is flagged; with the previous U-A the same records give another U-A.
    fresh = select(2019)
    assert fresh['flags'] == ['FIRST_BUILD_NOT_FIRST_BUNDLE_SIGNAL_DAY'] and fresh['first_build'] is True
    assert fresh['universe']['issuers'][cik(31)]['U_A']['reasons'] == ['BELOW_U_A_ENTRY_THRESHOLD']


def test_selection_inputs_are_json_ready_and_round_trip(years):
    s18, _ = years
    body = handoff.canonical_bytes(s18)
    assert json.loads(body) == s18
    assert handoff.canonical_bytes(json.loads(body)) == body


def test_companyfacts_are_loaded_lazily_for_u_a_members_only():
    calls = []
    facts = syn.companyfacts_by_cik()

    def load(cik_text):
        calls.append(cik_text)
        return facts.get(str(int(cik_text)))

    out = select(2018, companyfacts=load)
    assert sorted(calls) == sorted(out['universe']['U_A']['members'])
    assert cik(33) not in calls and cik(27) not in calls and cik(28) not in calls
    assert out['scores'] == select(2018)['scores']


def test_adr_quote_is_converted_to_per_ordinary_share_or_withheld():
    uni = {'issuers': {cik(16): {'classes': [{'security_id': 'A', 'security_type': 'ADR', 'adr_ratio': Decimal('4')}]}},
           'U_A': {'member_securities': ['A', 'B', 'C']},
           'securities': {'A': {'security_type': 'ADR'}, 'B': {'security_type': 'ADR'}, 'C': {'security_type': 'COMMON'}}}
    quotes = {'A': {'price': '20.0', 'currency': 'USD', 'month_closes': {'2017-12': '18.0'}},
              'B': {'price': Decimal('9'), 'currency': 'USD'}, 'C': {'price': '7.5', 'currency': 'USD'},
              'OUTSIDE': {'price': '1', 'currency': 'USD'}}
    out, basis = runner.scoring_quotes(quotes, uni)
    assert out['A']['price'] == Decimal('5') and out['A']['month_closes'] == {'2017-12': Decimal('4.5')}
    assert out['B']['withheld_reason'] == 'ADR_RATIO_UNCONFIRMED' and out['C']['price'] == Decimal('7.5')
    assert basis == {'A': 'ADR_PER_ORDINARY_SHARE', 'B': 'ADR_RATIO_UNCONFIRMED'} and 'OUTSIDE' not in out


def test_selection_stage_refuses_a_year_outside_the_frozen_schedule():
    with pytest.raises(runner.RunnerError, match='YEAR_NOT_IN_FROZEN_SCHEDULE'):
        runner.selection_stage([], year=2016)


# ---- ledger stage -------------------------------------------------------------------------------------------------
def test_ledger_stage_runs_every_strategy_side_and_group_benchmark(years, outputs):
    assert outputs['schema'] == runner.LEDGER_SCHEMA and outputs['selection_years'] == [2018, 2019]
    assert outputs['end'] == END and outputs['end_rule'] == 'SUPPLIED' and outputs['start'] == '2018-02-16'
    assert outputs['end_valuation'] == 'CLOSE' and outputs['flags'] == []
    expected = {f'{s}/{g}/{side}' for s in settings.STRATEGY_IDS for g in settings.GROUPS for side in ('TOP', 'BOTTOM')}
    expected |= {'GROUP_EQUAL_WEIGHT/U_A', 'GROUP_EQUAL_WEIGHT/U_B'}
    assert set(outputs['portfolios']) == expected and not any('QGV_DEFAULT' in pid for pid in expected)
    counts = outputs['counts']
    assert (counts['portfolios'], counts['portfolios_run'], counts['portfolios_all_cash']) == (30, 30, 0)
    assert counts['ledger_runs'] == 120 and counts['ledger_runs_by_status'] == {'COMPLETE': 120}
    assert counts['daily_coverage'] == {'DAILY_COVERAGE_COMPLETE': 30} and counts['settlement_conflicts'] == 0
    assert outputs['scenarios'] == ['LOSS', 'CARRY'] and outputs['cost_bps_levels'] == ['0', '10']
    top = outputs['portfolios']['AXIS_G/U_A/TOP']
    assert top['status'] == 'RUN' and top['cash_years'] == [] and [y['holding'] for y in top['years']] == ['SELECTED'] * 2
    for scenario in ('LOSS', 'CARRY'):
        free, paid = top['runs'][scenario]['0'], top['runs'][scenario]['10']
        assert free['cost_bps'] == '0' and Decimal(free['total_costs']) == 0
        assert paid['cost_bps'] == '10' and Decimal(paid['total_costs']) > 0
        with localcontext() as ctx:
            ctx.prec = 120
            assert Decimal(paid['total_costs']) == Decimal(paid['total_gross_traded']) * Decimal('0.001')
        assert [r['execution_status'] for r in paid['rebalances']] == ['EXECUTED', 'EXECUTED']
        comparison = top['metrics'][scenario]
        assert comparison['before_cost_bps'] == 0.0 and comparison['after_cost_bps'] == 10.0
        assert comparison['after_cost_total_fees'] > 0
        assert comparison['after_minus_before']['final_nav']['value'] < 0
        assert comparison['after_cost']['performance']['cagr']['value'] is not None
    # no termination among this portfolio's names: the two scenarios agree day by day
    assert [d['nav'] for d in top['runs']['LOSS']['10']['daily']] == [d['nav'] for d in top['runs']['CARRY']['10']['daily']]
    # U-B strategies run too (13 names, k = 1)
    ub = outputs['portfolios']['AXIS_G/U_B/TOP']
    assert ub['status'] == 'RUN' and [y['k'] for y in ub['years']] == [1, 1]
    assert runner.portfolio_alias(outputs, 'QGV_DEFAULT/U_A/TOP') is outputs['portfolios']['QGV_BALANCED/U_A/TOP']
    # a cell NOT_RUN in every year is ALL_CASH: recorded, no ledger
    s18, s19 = (copy.deepcopy(x) for x in years)
    for sel in (s18, s19):
        sel['selections']['AXIS_G']['U_B'] = dict(sel['selections']['AXIS_G']['U_B'], status='NOT_RUN',
                                                  reason='ELIGIBLE_BELOW_MIN_N', k=None, top=[], bottom=[], order=[],
                                                  ranks={})
    cash = runner.ledger_stage([s18, s19], prices=syn.price_rows(end=date(2019, 3, 1)), end='2019-03-01')
    assert cash['portfolios']['AXIS_G/U_B/TOP']['status'] == 'ALL_CASH'
    assert cash['portfolios']['AXIS_G/U_B/TOP']['cash_years'] == [2018, 2019]


def test_group_equal_weight_benchmark_holds_every_group_member_and_matches_the_ledger(years, outputs):
    s18, s19 = years
    ew = outputs['portfolios']['GROUP_EQUAL_WEIGHT/U_A']
    assert ew['kind'] == 'GROUP_EQUAL_WEIGHT' and ew['side'] is None
    assert [y['selected'] for y in ew['years']] == [s18['universe']['U_A']['member_securities'],
                                                    s19['universe']['U_A']['member_securities']]
    assert [y['N'] for y in ew['years']] == [30, 28]
    sessions = runner.calendar_sessions('2018-02-16', END)
    schedule_rows = [(date(2018, 2, 16), date(2018, 2, 20)), (date(2019, 2, 15), date(2019, 2, 19))]
    eligible = {date(2018, 2, 16): ew['years'][0]['selected'], date(2019, 2, 15): ew['years'][1]['selected']}
    direct = benchmarks.group_equal_weight_benchmark(sessions, schedule_rows, eligible, runner.price_rows(syn.price_rows()),
                                                     runner.ledger_events(syn.event_rows()), group='U_A',
                                                     daily_positions=False)
    for scenario in ('LOSS', 'CARRY'):
        mine = ew['runs'][scenario]['10']
        assert mine['daily'][-1]['nav'] == str(direct['runs'][scenario]['daily'][-1]['nav'])
        assert mine['total_costs'] == str(direct['runs'][scenario]['total_costs'])
    assert outputs['portfolios']['GROUP_EQUAL_WEIGHT/U_B']['years'][1]['N'] == 13


def test_external_total_return_series_is_the_spy_etf_and_a_french_label_is_refused(years, outputs):
    external = outputs['benchmarks']['external_total_return']
    assert external['status'] == 'COMPLETE'
    result = external['result']
    assert (result['benchmark_id'], result['name'], result['is_etf']) == ('ETF_TR:SPY', 'SPY total return (ETF)', True)
    assert result['is_sp500_index'] is False and result['claim'] == 'OTHER_TR'
    assert result['entry_date'] == '2018-02-20' and external['metrics']['performance']['cagr']['value']
    french = {'label': 'Fama-French market', 'claim': 'SP500_TR', 'source': 'Kenneth French library',
              'rows': syn.tr_rows(end=date(2018, 3, 2))}
    out = runner.ledger_stage([years[0]], prices=syn.price_rows(end=date(2018, 3, 2)), end='2018-03-02',
                              tr_series=french)
    assert out['benchmarks']['external_total_return'] == {'status': 'REFUSED', 'reason': 'FRENCH_MARKET_NOT_SP500',
                                                         'label': 'Fama-French market', 'result': None, 'metrics': None}
    assert out['counts']['portfolios_run'] == 30


# ---- the corporate-action and fill cases of the synthetic bundle -------------------------------------------------
def test_synthetic_delisting_without_terms_splits_loss_and_carry_in_a_strategy_portfolio(outputs):
    bottom = outputs['portfolios']['AXIS_G/U_A/BOTTOM']
    assert 'XQ015' in bottom['years'][0]['selected']
    loss = {d['date']: Decimal(d['nav']) for d in bottom['runs']['LOSS']['0']['daily']}
    carry = {d['date']: Decimal(d['nav']) for d in bottom['runs']['CARRY']['0']['daily']}
    assert loss['2018-09-28'] == carry['2018-09-28'] and loss['2018-10-01'] < carry['2018-10-01']
    day = next(d for d in bottom['runs']['LOSS']['0']['daily'] if d['date'] == '2018-10-01')
    assert 'LOSS_SCENARIO:XQ015' in day['flags'] and 'TERMINATION_UNCONFIRMED:DELIST-XQ015-1:LOSS' in day['events']
    carried = next(d for d in bottom['runs']['CARRY']['0']['daily'] if d['date'] == '2019-02-19')
    assert 'CARRY_SCENARIO:XQ015' in carried['flags']          # never sold at the 2019 reselection


def test_synthetic_confirmed_cash_merger_and_its_form_25_in_a_strategy_portfolio(outputs):
    top = outputs['portfolios']['QGV_BALANCED/U_A/TOP']
    assert 'XQ021' in top['years'][0]['selected']
    run = top['runs']['LOSS']['0']
    effective = next(d for d in run['daily'] if d['date'] == '2018-07-02')
    assert 'SETTLEMENT_APPLIED:MERGER-XQ021-1' in effective['events'] and Decimal(effective['receivables']) > 0
    paid = next(d for d in run['daily'] if d['date'] == '2018-07-05')
    assert 'CASH_RECEIVED:SETTLEMENT_CASH:MERGER-XQ021-1' in paid['events'] and Decimal(paid['reserved_cash']) > 0
    form25 = next(d for d in run['daily'] if d['date'] == '2018-07-12')
    assert 'TERMINATION_SUPPORTING_EVIDENCE:FORM25-XQ021-1' in form25['events'] and run['conflicts'] == []
    assert [d['nav'] for d in run['daily']] == [d['nav'] for d in top['runs']['CARRY']['0']['daily']]


def test_synthetic_selected_name_without_t_open_is_unfilled_and_its_slot_stays_cash(outputs):
    top = outputs['portfolios']['AXIS_G/U_A/TOP']
    first = top['runs']['LOSS']['0']['rebalances'][0]
    assert 'XQ009' in first['selected']
    assert [u['security_id'] for u in first['unfilled'] if u['reason'] == 'UNAVAILABLE_OPEN'] == ['XQ009']
    assert all(f['security_id'] != 'XQ009' for f in top['runs']['LOSS']['0']['fills'] if f['session'] < '2019-02-19')
    assert Decimal(first['slot_cash_held_back']) > 0
    day = next(d for d in top['runs']['LOSS']['0']['daily'] if d['date'] == '2018-03-01')
    assert Decimal(day['cash']) >= Decimal(first['slot_cash_held_back'])


def test_synthetic_split_dividend_and_adr_depositary_fee_in_the_group_benchmark(outputs):
    ew = outputs['portfolios']['GROUP_EQUAL_WEIGHT/U_A']['runs']['LOSS']['0']
    assert [(f['event_id'], f['kind'], f['security_id']) for f in ew['instrument_fees']] == [
        ('DIV-XQ026-1', 'DEPOSITARY_FEE', 'XQ026')]
    assert Decimal(ew['total_instrument_fees']) > 0
    by_day = {d['date']: d for d in ew['daily']}
    assert 'SPLIT:SPLIT-XQ013-1' in by_day['2018-09-04']['events']
    assert 'DIVIDEND_EX:DIV-XQ012-1' in by_day['2018-06-01']['events']
    assert by_day['2018-06-15']['events'].count('CASH_RECEIVED:DIVIDEND:DIV-XQ012-1') == 1


def test_a_strategy_not_run_in_a_year_holds_cash_that_year(years):
    s18, s19 = years
    s19 = copy.deepcopy(s19)
    s19['selections']['AXIS_G']['U_A'] = dict(s19['selections']['AXIS_G']['U_A'], status='NOT_RUN',
                                              reason='ELIGIBLE_BELOW_MIN_N', k=None, top=[], bottom=[], order=[],
                                              ranks={})
    out = runner.ledger_stage([s18, s19], prices=syn.price_rows(), events=syn.event_rows(), end=END)
    top = out['portfolios']['AXIS_G/U_A/TOP']
    assert top['status'] == 'RUN' and top['cash_years'] == [2019]
    assert top['years'][1] == {'year': 2019, 'S': '2019-02-15', 'T': '2019-02-19', 'status': 'NOT_RUN',
                               'reason': 'ELIGIBLE_BELOW_MIN_N', 'N': s19['selections']['AXIS_G']['U_A']['N'], 'k': None,
                               'holding': 'CASH', 'selected': []}
    run = top['runs']['LOSS']['10']
    after = [d for d in run['daily'] if d['date'] >= '2019-02-19']
    # NAV is the cash (the snapshot sums at precision 50, the cash book is exact)
    assert after and all(Decimal(d['market_value']) == 0 and abs(Decimal(d['nav']) - Decimal(d['cash'])) < Decimal('1e-40')
                         for d in after)
    assert run['rebalances'][1]['selected'] == [] and run['rebalances'][1]['execution_status'] == 'EXECUTED'
    assert all(f['quantity'].startswith('-') for f in run['rebalances'][1]['fills'])   # sold, nothing bought
    before = [d for d in run['daily'] if '2018-02-20' <= d['date'] < '2019-02-19']
    assert all(Decimal(d['market_value']) > 0 for d in before)


def test_unconfirmed_delisting_splits_loss_and_carry(years):
    s18, s19 = years
    held = s18['selections']['AXIS_G']['U_A']['top'][0]['security_id']
    events = syn.event_rows() + [{'type': 'SETTLEMENT', 'event_id': 'DELIST-1', 'effective_date': '2018-10-01',
                                  'security_id': held, 'kind': 'DELISTING', 'available_at': '2018-10-01',
                                  'evidence': 'synthetic notice'}]
    out = runner.ledger_stage([s18, s19], prices=syn.price_rows(), events=events, end=END)
    top = out['portfolios']['AXIS_G/U_A/TOP']
    loss = {d['date']: Decimal(d['nav']) for d in top['runs']['LOSS']['0']['daily']}
    carry = {d['date']: Decimal(d['nav']) for d in top['runs']['CARRY']['0']['daily']}
    assert loss['2018-09-28'] == carry['2018-09-28']
    assert loss['2018-10-01'] < carry['2018-10-01']
    assert any(f'LOSS_SCENARIO:{held}' in d['flags'] for d in top['runs']['LOSS']['0']['daily'])


def test_ledger_stage_refuses_inconsistent_selections(years):
    s18, s19 = years
    prices = syn.price_rows(end=date(2018, 3, 2))
    forged = dict(s18, settings_sha256='0' * 64)
    with pytest.raises(runner.RunnerError, match='SETTINGS_SHA256_MISMATCH'):
        runner.ledger_stage([forged], prices=prices, end='2018-03-02')
    broken = dict(s19, previous_u_a=s19['previous_u_a'][1:])
    with pytest.raises(runner.RunnerError, match='HYSTERESIS_CHAIN_BROKEN'):
        runner.ledger_stage([s18, broken], prices=prices, end='2018-03-02')
    lost_unknown = dict(s19, previous_u_a_unknown=[])           # review F3: the UNKNOWN set is part of the chain
    with pytest.raises(runner.RunnerError, match='HYSTERESIS_CHAIN_BROKEN'):
        runner.ledger_stage([s18, lost_unknown], prices=prices, end='2018-03-02')
    lost_classes = dict(s19, previous_u_a_securities={})        # review U1: the carried class IDs too
    with pytest.raises(runner.RunnerError, match='HYSTERESIS_CHAIN_BROKEN'):
        runner.ledger_stage([s18, lost_classes], prices=prices, end='2018-03-02')
    with pytest.raises(runner.RunnerError, match='SELECTION_YEAR_DUPLICATE'):
        runner.ledger_stage([s18, s18], prices=prices, end='2018-03-02')
    gap = dict(s19, year=2020, signal={'S': '2020-02-14', 'T': '2020-02-18'})
    with pytest.raises(runner.RunnerError, match='SELECTION_YEARS_NOT_CONSECUTIVE'):
        runner.ledger_stage([s18, gap], prices=prices, end='2018-03-02')
    with pytest.raises(runner.RunnerError, match='SELECTION_SIGNAL_DAY_MISMATCH'):
        runner.ledger_stage([dict(s18, signal=dict(s18['signal'], S='2018-02-15'))], prices=prices, end='2018-03-02')


def test_selection_files_and_in_memory_results_give_the_same_ledger(years):
    s18, _ = years
    prices = syn.price_rows(end=date(2018, 4, 30))
    a = runner.ledger_stage([s18], prices=prices, end='2018-04-30')
    b = runner.ledger_stage([json.loads(handoff.canonical_bytes(s18))], prices=prices, end='2018-04-30')
    assert handoff.canonical_bytes(a) == handoff.canonical_bytes(b)


def test_default_end_and_event_rows():
    rows = runner.price_rows([{'date': '2026-03-02', 'security_id': 'X'}, {'date': '2026-03-03', 'security_id': 'X'}])
    assert runner.default_end(2019, rows) == (date(2020, 2, 18), 'NEXT_RESELECTION_T_OPEN', 'OPEN')
    assert runner.default_end(2026, rows) == (date(2026, 3, 3), 'LAST_PRICE_DATE', 'CLOSE')
    events = runner.ledger_events(syn.event_rows())
    assert events[0] == ledger.Dividend('DIV-XQ012-1', date(2018, 6, 1), 'XQ012', Decimal('0.2517'), date(2018, 6, 15))
    assert events[1] == ledger.Dividend('DIV-XQ026-1', date(2018, 8, 1), 'XQ026', Decimal('0.4007'), date(2018, 8, 15),
                                        Decimal('0.0207'))
    assert events[2] == ledger.Split('SPLIT-XQ013-1', date(2018, 9, 4), 'XQ013', Decimal('2'))
    with pytest.raises(runner.RunnerError, match='EVENT_FIELDS_INVALID'):
        runner.ledger_events([{'type': 'SPLIT', 'event_id': 'S', 'effective_date': '2018-01-02', 'security_id': 'X'}])
    with pytest.raises(runner.RunnerError, match='EVENT_AMOUNT_INVALID'):
        runner.ledger_events([{'type': 'SPLIT', 'event_id': 'S', 'effective_date': '2018-01-02', 'security_id': 'X',
                               'ratio': 2.5}])


def test_dividend_rows_carry_an_optional_depositary_fee():
    rows = [{'type': 'DIVIDEND', 'event_id': 'D1', 'effective_date': '2018-06-01', 'security_id': 'X',
             'cash_per_share': '0.4007', 'pay_date': '2018-06-15', 'depositary_fee_per_share': '0.0207'}]
    assert runner.ledger_events(rows)[0] == ledger.Dividend('D1', date(2018, 6, 1), 'X', Decimal('0.4007'),
                                                            date(2018, 6, 15), Decimal('0.0207'))
    with pytest.raises(runner.RunnerError, match='EVENT_AMOUNT_INVALID'):
        runner.ledger_events([dict(rows[0], depositary_fee_per_share=0.02)])



# ---- review F4: the first bundle is held to the next reselection T open ------------------------------------------
def test_default_end_values_every_portfolio_and_the_external_tr_at_the_next_t_open(years):
    s18, _ = years
    assert runner.default_end(2018, []) == (date(2019, 2, 19), 'NEXT_RESELECTION_T_OPEN', 'OPEN')
    tr = {'label': 'SPY total return', 'claim': 'OTHER_TR', 'is_etf': True, 'source': 'synthetic', 'rows': syn.tr_rows()}
    out = runner.ledger_stage([s18], prices=syn.price_rows(), events=syn.event_rows(), tr_series=tr)
    assert (out['end'], out['end_rule'], out['end_valuation']) == ('2019-02-19', 'NEXT_RESELECTION_T_OPEN', 'OPEN')
    for pid in ('GROUP_EQUAL_WEIGHT/U_A', 'AXIS_G/U_A/TOP'):
        for scenario in ('LOSS', 'CARRY'):
            run = out['portfolios'][pid]['runs'][scenario]['10']
            last, before = run['daily'][-1], run['daily'][-2]
            assert (last['date'], last['valuation'], run['end_valuation']) == ('2019-02-19', 'OPEN', 'OPEN')
            assert before['date'] == '2019-02-15' and before['valuation'] == 'CLOSE'
            assert last['fills'] == [] and last['costs'] == '0'            # no trade at the terminal open
    external = out['benchmarks']['external_total_return']['result']
    assert external['daily'][-1]['date'] == '2019-02-19' and external['daily'][-1]['valuation'] == 'OPEN'
    assert external['end_valuation'] == 'OPEN' and 'END_AT_PREVIOUS_CLOSE' not in external['flags']
    no_open = dict(tr, rows=[dict(r, open_total_return_index=None) if r['date'] == '2019-02-19' else r
                             for r in syn.tr_rows()])
    out = runner.ledger_stage([s18], prices=syn.price_rows(), tr_series=no_open)
    external = out['benchmarks']['external_total_return']['result']
    assert external['daily'][-1]['valuation'] == 'PREVIOUS_CLOSE' and 'END_AT_PREVIOUS_CLOSE' in external['flags']
    assert external['daily'][-1]['level'] == external['daily'][-2]['level']


def test_one_name_held_flat_to_the_next_s_close_measures_the_move_to_the_next_t_open():
    """Review d1: flat 100 through the 2019-02-15 close, 110 at the 2019-02-19 open -> +10%, not 0%."""
    end, rule, valuation = runner.default_end(2018, [])
    sessions = runner.calendar_sessions('2018-02-16', end)
    rows = [dict(date=day, security_id='SYN_A', open=Decimal(110 if day == end else 100),
                 close=Decimal(110 if day == end else 100), price_basis='RAW') for day in sessions]
    result = ledger.run_ledger(sessions, [ledger.Rebalance(date(2018, 2, 16), date(2018, 2, 20), ('SYN_A',))], rows,
                               scenario='LOSS', cost_bps=0, end=end, end_valuation=valuation)
    assert result['daily'][-1]['date'] == date(2019, 2, 19) and result['daily'][-1]['nav'] == Decimal('1100000')
    assert result['daily'][-2]['nav'] == Decimal('1000000')


# ---- review F9: an end past the next reselection is refused when that year's selection is absent ------------------
def test_end_past_the_next_reselection_without_its_selection_is_refused(years):
    s18, s19 = years
    with pytest.raises(runner.RunnerError, match='END_PAST_NEXT_RESELECTION'):
        runner.ledger_stage([s18], prices=syn.price_rows(), events=syn.event_rows(), end=END)
    at_t = runner.ledger_stage([s18], prices=syn.price_rows(), end='2019-02-19')
    assert (at_t['end_rule'], at_t['end_valuation']) == ('SUPPLIED', 'OPEN')
    before = runner.ledger_stage([s18], prices=syn.price_rows(), end='2019-02-15')
    assert (before['end_rule'], before['end_valuation']) == ('SUPPLIED', 'CLOSE')
    both = runner.ledger_stage([s18, s19], prices=syn.price_rows(), end=END)       # 2019 selection supplied
    assert [len(p['runs']['LOSS']['10']['rebalances']) for p in both['portfolios'].values() if p['runs']][0] == 2


# ---- review F6: an ADR float quote is divided too, never passed per ADS ----------------------------------------------
def test_adr_float_quote_is_divided_through_decimal_text_or_withheld():
    """Review d4: a float price 30.0 stayed 30.0 per ADS while the basis said ADR_PER_ORDINARY_SHARE."""
    uni = {'issuers': {cik(16): {'classes': [{'security_id': 'A', 'security_type': 'ADR', 'adr_ratio': Decimal('2')}]}},
           'U_A': {'member_securities': ['A']}, 'securities': {'A': {'security_type': 'ADR'}}}
    for price in ('30', 30.0, Decimal('30'), 30):
        out, basis = runner.scoring_quotes({'A': {'price': price, 'currency': 'USD', 'month_closes': {'2018-01': price}}},
                                           uni)
        assert out['A']['price'] == Decimal('15') and isinstance(out['A']['price'], Decimal)
        assert out['A']['month_closes'] == {'2018-01': Decimal('15')} and basis == {'A': 'ADR_PER_ORDINARY_SHARE'}
    out, basis = runner.scoring_quotes({'A': {'price': 30.1, 'currency': 'USD'}}, uni)
    assert out['A']['price'] == Decimal('15.05')                       # Decimal(str(30.1)) / 2, no binary noise
    out, basis = runner.scoring_quotes({'A': {'price': 'n/a', 'currency': 'USD',
                                              'month_closes': {'2018-01': 'x', '2018-02': 40.0}}}, uni)
    assert out['A']['withheld_reason'] == 'ADR_QUOTE_PRICE_INVALID' and basis == {'A': 'ADR_QUOTE_PRICE_INVALID'}


# ---- owner 11/01 decision 7: daily metrics only when daily prices cover the holding period -------------------------
def test_portfolio_daily_coverage_and_monthly_metrics_without_daily_prices(years):
    s18, _ = years
    sessions = runner.calendar_sessions('2018-02-16', '2019-02-19')
    month_ends = {day for day, nxt in zip(sessions, sessions[1:]) if nxt.month != day.month}
    keep = {date(2018, 2, 16), date(2018, 2, 20), date(2019, 2, 19)} | month_ends
    full = runner.ledger_stage([s18], prices=syn.price_rows(), events=syn.event_rows())
    sparse = runner.ledger_stage([s18], prices=[r for r in syn.price_rows() if r['date'] in keep],
                                 events=syn.event_rows())
    # A U-B cell whose only (k = 1) pick has no T open holds cash all year: NO_FILL, not a coverage gap.
    no_fill = full['counts']['daily_coverage'].get('NO_FILL', 0)
    assert full['counts']['daily_coverage'] == {'DAILY_COVERAGE_COMPLETE': 30 - no_fill, **({'NO_FILL': no_fill}
                                                                                            if no_fill else {})}
    assert sparse['counts']['daily_coverage'] == {'DAILY_PRICES_NOT_SUPPLIED': 30 - no_fill,
                                                  **({'NO_FILL': no_fill} if no_fill else {})}
    ew_full = full['portfolios']['GROUP_EQUAL_WEIGHT/U_A']['metrics']['LOSS']['after_cost']
    ew = sparse['portfolios']['GROUP_EQUAL_WEIGHT/U_A']['metrics']['LOSS']['after_cost']
    assert ew['performance']['max_drawdown'] == {'value': None, 'reason': 'DAILY_PRICES_NOT_SUPPLIED'}
    assert ew['performance']['annualized_volatility']['reason'] == 'DAILY_PRICES_NOT_SUPPLIED'
    assert ew['monthly']['basis'] == 'MONTHLY' and ew['monthly']['max_drawdown']['value'] is not None
    assert ew['final']['valuation'] == 'OPEN' and ew['final']['nav_index'] is not None
    assert [r['nav_index'] for r in ew['month_end_nav']] == [r['nav_index'] for r in ew_full['month_end_nav']]


def test_selection_stage_requires_the_carried_class_ids_with_a_previous_u_a(years):
    """Review U1: the previous U-A state is members + UNKNOWN units + their class IDs; selection_inputs records it."""
    s18, s19 = years
    state = runner.u_a_state(s18)
    assert s19['previous_u_a_securities'] == state['securities'] == s18['universe']['U_A']['unit_securities']
    assert set(state['securities']) == set(state['members']) | set(state['unknown'])
    with pytest.raises(runner.RunnerError, match='PREVIOUS_U_A_SECURITIES_REQUIRED'):
        runner.selection_stage(syn.records(2019), year=2019, previous_u_a=state['members'],
                               previous_u_a_unknown=state['unknown'])


def test_ledger_output_keeps_every_selection_flag_by_year(years):
    """Review U3: the ledger stage dropped the selections' flags (its own flags list was always [])."""
    s18, _ = years
    flagged = dict(s18, flags=['SOME_SELECTION_FLAG'])
    out = runner.ledger_stage([flagged], prices=syn.price_rows(end=date(2018, 3, 2)), end='2018-03-02')
    assert out['selection_flags'] == {'2018': ['SOME_SELECTION_FLAG']}
