"""Adversarial Main handoff checks; invented data and an independent cash oracle.

The Fraction oracle does not call the production ledger, selector or calendar.
Full-universe ranking uses the existing scorer; this is not an independent
implementation of QGV's fifteen factor formulas or evidence of market returns.
"""
import copy
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from investment_system.research.qgv_backtest import annual, preparation, runner
from investment_system.research.qgv_backtest.cache import PreparationCache
from investment_system.research.qgv_backtest.extensions import selected_cells
from investment_system.research.qgv_backtest.ledger import Ledger, LedgerError
from test_qgv_backtest_annual import multi_year_bundle
from test_qgv_backtest_reuse_runner import large_bundle
from test_qgv_backtest_runner import spec


def reference_transition(cash, holdings, selected, slots, closes, opens, bps):
    """No events/interest/suspension: exact rational sell-then-buy reference."""
    rate = Fraction(bps, 10000)
    nav = cash + sum(quantity * closes[sid] for sid, quantity in holdings.items())
    targets = {sid: nav / slots / closes[sid] for sid in selected}
    orders = {sid: targets.get(sid, 0) - holdings.get(sid, 0)
              for sid in set(targets) | set(holdings)}
    orders = {sid: quantity for sid, quantity in orders.items() if quantity}
    positions = dict(holdings)
    fills = {}
    for sid, quantity in orders.items():
        if quantity < 0:
            cash += -quantity * opens[sid] * (1 - rate)
            positions[sid] += quantity
            fills[sid] = quantity
    buys = {sid: quantity for sid, quantity in orders.items() if quantity > 0}
    debit = sum(quantity * opens[sid] * (1 + rate) for sid, quantity in buys.items())
    scale = min(Fraction(1), cash / debit) if debit else Fraction(0)
    for sid, quantity in buys.items():
        quantity *= scale
        cash -= quantity * opens[sid] * (1 + rate)
        positions[sid] = positions.get(sid, 0) + quantity
        fills[sid] = quantity
    return orders, fills, cash, {sid: q for sid, q in positions.items() if q}


def close_mapping(actual, expected):
    assert set(actual) == set(expected)
    for key, want in expected.items():
        assert float(actual[key]) == pytest.approx(float(want), abs=1e-10, rel=1e-12)


@pytest.mark.parametrize('bps', [0, 10, 30])
def test_exits_new_entries_continuing_deltas_and_both_side_costs_match_rational_oracle(bps):
    # Catches incumbent-only/reweight-only selection, unsold exits, using the
    # next open to size orders, or omitting either the buy or sell cost.
    ledger = Ledger(1000, cost_bps=bps)
    cash, positions = Fraction(1000), {}
    cases = [
        (date(2016, 2, 12), date(2016, 2, 16), ('A', 'B'),
         {'A': 10, 'B': 20}, {'A': 11, 'B': 19}),
        (date(2017, 2, 17), date(2017, 2, 21), ('B', 'C'),
         {'A': 12, 'B': 8, 'C': 20}, {'A': 11, 'B': 9, 'C': 22}),
    ]
    for signal, execution, names, closes, opens in cases:
        expected_orders, expected_fills, cash, positions = reference_transition(
            cash, positions, names, 2, closes, opens, bps)
        orders = ledger.rebalance(signal, names, 2, closes)
        close_mapping(orders, expected_orders)
        fills = ledger.execute_open(execution, opens)
        close_mapping({fill.security_id: fill.quantity for fill in fills}, expected_fills)
        close_mapping(ledger.holdings, positions)
        assert float(ledger.cash) == pytest.approx(float(cash), abs=1e-10)
        for fill in fills:
            assert float(fill.fee) == pytest.approx(float(fill.gross) * bps / 10000, abs=1e-10)
    assert 'A' not in ledger.holdings
    assert set(ledger.holdings) == {'B', 'C'}
    assert any(fill.quantity < 0 for fill in fills)
    assert any(fill.quantity > 0 for fill in fills)
    assert float(ledger.nav(execution, opens).nav) == pytest.approx(
        float(cash + sum(q * opens[sid] for sid, q in positions.items())), abs=1e-10)


def test_signal_and_open_retries_do_not_duplicate_orders_or_fills():
    ledger = Ledger(1000)
    signal, execution = date(2016, 2, 12), date(2016, 2, 16)
    expected = ledger.rebalance(signal, ['A'], 1, {'A': 10})
    assert ledger.rebalance(signal, ['A'], 1, {'A': 10}) == expected
    with pytest.raises(LedgerError, match='OPEN_MUST_FOLLOW_SIGNAL'):
        ledger.execute_open(signal, {'A': 10})
    fills = ledger.execute_open(execution, {'A': 11})
    snapshot = (ledger.cash, dict(ledger.holdings), len(ledger.fills))
    assert ledger.execute_open(execution, {'A': 11}) == fills
    assert (ledger.cash, dict(ledger.holdings), len(ledger.fills)) == snapshot
    with pytest.raises(LedgerError, match='CONFLICTING_DECISION_RETRY'):
        ledger.rebalance(signal, ['B'], 1, {'B': 10})
    with pytest.raises(LedgerError, match='CONFLICTING_OPEN_RETRY'):
        ledger.execute_open(execution, {'A': 12})


@pytest.mark.parametrize('attack', ['future_facts', 'after_close_availability', 'future_closes'])
def test_future_input_mutations_cannot_change_signal_selection_or_locked_quantities(attack):
    data = large_bundle()
    changed = copy.deepcopy(data)
    if attack == 'future_closes':
        for row in changed['prices']:
            if row['date'] > '2016-02-12':
                row['close'] *= 1000
    else:
        for facts in changed['companyfacts_by_cik'].values():
            for tags in facts['facts'].values():
                for info in tags.values():
                    for records in info['units'].values():
                        row = copy.deepcopy(records[-1])
                        row.update(filed='2016-02-16' if attack == 'future_facts' else '2016-02-11',
                                   val=row['val'] * 100000, accn='SYNTHETIC-FUTURE')
                        if attack == 'after_close_availability':
                            row['known_at'] = '2016-02-12T22:00:00Z'
                        records.append(row)
    extension = annual.annual_extension()
    cells = selected_cells(extension, 'primary', ['DEC-SPX-W0-Y-D1'])
    before, after = [runner.replay_bundle(spec(), payload, 'TARGET_QGV_V2', cells=cells,
                                        extension=extension) for payload in (data, changed)]
    assert before['runs'][0]['status'] == after['runs'][0]['status'] == 'COMPLETE'
    assert before['runs'][0]['decisions'] == after['runs'][0]['decisions']


def test_holiday_signal_price_cutoff_and_actual_open_are_separate_instants():
    # The hand calendar explicitly excludes Feb15 (and Feb13/14); no historical
    # calendar completeness claim follows from this synthetic schedule test.
    data = large_bundle()
    calendar = runner._calendar(data)
    from investment_system.research.qgv_backtest.calendar_adapter import rebalance_schedule
    schedule = rebalance_schedule(calendar, date(2016, 2, 16), date(2016, 2, 20), 'ANNUAL_FEBRUARY')
    assert [(r.nominal_day, r.signal_day, r.execution_day) for r in schedule] == [
        (date(2016, 2, 15), date(2016, 2, 12), date(2016, 2, 16))]
    assert schedule[0].decision_at.isoformat() == '2016-02-12T21:00:00+00:00'
    assert schedule[0].execute_at.isoformat() == '2016-02-16T14:30:00+00:00'
    extension = annual.annual_extension()
    run = runner.replay_bundle(spec(), data, 'TARGET_QGV_V2', extension=extension,
                              cells=selected_cells(extension, 'primary', ['DEC-SPX-W0-Y-D1']))['runs'][0]
    assert run['fills'][0]['session'] == '2016-02-16'
    assert len(run['decisions']) == 1
    assert all(calendar.is_session(date.fromisoformat(fill['session'])) for fill in run['fills'])


@pytest.fixture(scope='module')
def annual_transition():
    data = multi_year_bundle()
    # Two annual decisions and five quarterly decisions; full 12-offset replays
    # are already exercised by the original annual synthetic tests.
    end = '2017-02-22'
    data['coverage_end'] = data['universe_coverage']['end'] = end
    for field, key in [('sessions', 'day'), ('prices', 'date'), ('benchmark', 'date'), ('rates', 'public_date')]:
        data[field] = [row for row in data[field] if row[key] <= end]
    research_spec = spec()
    research_spec['period']['data_feasibility_ladder'][0]['end'] = end
    extension = annual.annual_extension()
    cache = PreparationCache()
    cells = selected_cells(extension, 'sensitivity', ['DEC-SPX-W0-Y-D1', 'DEC-SPX-W0-Q-D1'])
    cells = [cell for cell in cells if cell['cost_bps'] in (0, 30)]
    result = runner.replay_bundle(research_spec, data, 'TARGET_QGV_V2', cells=cells,
                                  extension=extension, preparation_cache=cache)
    assert all(run['status'] == 'COMPLETE' for run in result['runs'])
    return data, research_spec, extension, cells, cache, result


def test_each_annual_selection_matches_independent_whole_population_ranking_and_liquidates_exits(annual_transition):
    data, research_spec, extension, cells, cache, result = annual_transition
    calendar = runner._calendar(data)
    run = next(r for r in result['runs'] if r['cell']['id'] == 'DEC-SPX-W0-Y-D1' and r['cell']['cost_bps'] == 0)
    assert len(run['decisions']) == 2
    for decision in run['decisions']:
        payload, scores = preparation.prepare(data, 'U-SPX-HIST', date.fromisoformat(decision['signal_day']),
                                              calendar, PreparationCache(), {}, dict(pit_calls=0, score_calls=0))
        candidates = [sid for sid in payload['identities'] if
                      isinstance(scores['scores']['W0'][sid].get('total'), (int, float)) and
                      all(isinstance(scores['scores']['W0'][sid]['axes'][a].get('score'), (int, float)) for a in ('Q', 'G', 'V'))]
        ordered = sorted(candidates, key=lambda sid: (-scores['scores']['W0'][sid]['total'],
                                                    int(payload['identities'][sid]['cik']), sid))
        assert len(ordered) == 110
        assert decision['selected'] == ordered[:11]
    second = run['decisions'][1]
    assert second['entries'] and second['exits']
    assert set(second['entries']).isdisjoint(run['decisions'][0]['selected'])
    end_positions = run['exposure'][-1]['holdings']
    assert set(second['exits']).isdisjoint(end_positions)
    assert all(Decimal(second['quantities'][sid]) < 0 for sid in second['exits'])
    assert all(Decimal(second['quantities'][sid]) > 0 for sid in second['entries'])


def test_shared_preparation_cache_cannot_reuse_cost_specific_nav_or_mix_cadences(annual_transition):
    data, research_spec, extension, cells, cache, cold = annual_transition
    warm = runner.replay_bundle(research_spec, data, 'TARGET_QGV_V2', cells=cells,
                                extension=extension, preparation_cache=cache)
    assert warm['preparation_stats']['pit_calls'] == warm['preparation_stats']['score_calls'] == 0
    assert warm['runs'] == cold['runs']
    for suffix, count, role in [('Y', 2, 'PRIMARY_ANNUAL_RESELECTION'), ('Q', 5, 'CADENCE_SENSITIVITY')]:
        pair = [r for r in cold['runs'] if r['cell']['id'] == f'DEC-SPX-W0-{suffix}-D1']
        assert len(pair) == 2
        assert all(len(r['decisions']) == count and r['cell']['analysis_role'] == role for r in pair)
        assert pair[0]['decisions'][0]['selected'] == pair[1]['decisions'][0]['selected']
        assert pair[0]['nav'][-1]['nav'] != pair[1]['nav'][-1]['nav']
        for run in pair:
            keys = [(f['session'], f['security_id']) for f in run['fills']]
            assert len(keys) == len(set(keys))
    assert len({r['cell']['strategy_id'] for r in cold['runs']}) == 2


def test_late_known_incumbent_close_cannot_fund_new_annual_orders(annual_transition):
    data, research_spec, extension, cells, cache, baseline = annual_transition
    run = next(r for r in baseline['runs'] if r['cell']['id'] == 'DEC-SPX-W0-Y-D1' and r['cell']['cost_bps'] == 0)
    second = run['decisions'][1]
    incumbent = second['exits'][0]
    changed = copy.deepcopy(data)
    # Capitalization is optional for SPX. Removing it exposes the accounting
    # boundary independently of the all-market capitalization-price gate.
    changed['capitalization'] = []
    for row in changed['prices']:
        if row['security_id'] == incumbent and row['date'] == second['signal_day']:
            row.update(close=1000000, known_at=second['signal_day'] + 'T22:00:00Z')
    single = [c for c in cells if c['id'] == 'DEC-SPX-W0-Y-D1' and c['cost_bps'] == 0]
    attacked = runner.replay_bundle(research_spec, changed, 'TARGET_QGV_V2', cells=single,
                                   extension=extension)['runs'][0]
    assert attacked['status'] == 'INCOMPLETE_NAV'
    assert 'INCOMPLETE_SIGNAL_NAV' in attacked['blockers']
    assert len(attacked['decisions']) == 1
    assert all(f['session'] < second['execution_day'] for f in attacked['fills'])
