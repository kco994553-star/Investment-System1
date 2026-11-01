"""Top / bottom k = floor(N x 0.10) from one total order; N < 10 not run; ties by security ID. Hand-made scores."""
from decimal import Decimal
import random

import pytest

from investment_system.research.exp_deciles import selection, settings


def ids(n, prefix='S'):
    return [f'{prefix}{i:03}' for i in range(n)]


def test_k_is_floor_of_n_times_one_tenth_in_exact_arithmetic():
    assert [selection.decile_k(n) for n in (0, 9, 10, 19, 20, 29, 30, 99, 100, 101, 1234)] == \
        [0, 0, 1, 1, 2, 2, 3, 9, 10, 10, 123]
    assert all(selection.decile_k(n) == n // 10 for n in range(0, 5001))


def test_n_below_ten_is_not_run_and_ten_runs_with_k_one():
    members = ids(10)
    scores = {sid: float(i) for i, sid in enumerate(members)}
    scores['S009'] = None                                                     # 9 eligible
    out = selection.select(scores, members)
    assert out['status'] == 'NOT_RUN' and out['reason'] == 'ELIGIBLE_BELOW_MIN_N'
    assert (out['N'], out['k'], out['top'], out['bottom'], out['ranks']) == (9, None, (), (), {})
    assert out['not_eligible'] == {'S009': 'NO_SCORE'}
    scores['S009'] = 9.0
    run = selection.select(scores, members)
    assert (run['status'], run['N'], run['k']) == ('RUN', 10, 1)
    assert [t['security_id'] for t in run['top']] == ['S009'] and [b['security_id'] for b in run['bottom']] == ['S000']


def test_one_order_score_descending_ties_by_security_id_ascending():
    members = ['D', 'B', 'A', 'C', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']
    scores = dict.fromkeys(members, 50.0)
    scores.update(D=90.0, B=90.0, A=10.0, C=10.0)
    out = selection.select(scores, members)
    assert out['N'] == 20 and out['k'] == 2
    assert out['order'][:2] == ('B', 'D') and out['order'][-2:] == ('A', 'C')
    assert [t['security_id'] for t in out['top']] == ['B', 'D']
    assert [b['security_id'] for b in out['bottom']] == ['A', 'C']
    assert out['order'][2:6] == ('E', 'F', 'G', 'H')                         # the tied middle in ID order
    assert out['ranks']['B'] == 1 and out['ranks']['C'] == 20
    assert [t['rank'] for t in out['bottom']] == [19, 20]


def test_boundary_ties_are_cut_by_security_id_not_dropped_or_shared():
    members = ids(10)
    scores = dict.fromkeys(members, 1.0)
    out = selection.select(scores, members)
    assert [t['security_id'] for t in out['top']] == ['S000']
    assert [b['security_id'] for b in out['bottom']] == ['S009']


def test_top_and_bottom_never_overlap_and_are_the_ends_of_one_order():
    rng = random.Random(20261101)
    for n in range(10, 120):
        members = ids(n)
        scores = {sid: rng.choice([rng.random(), 0.5, 0.25]) for sid in members}
        out = selection.select(scores, list(reversed(members)))
        top, bottom = [t['security_id'] for t in out['top']], [b['security_id'] for b in out['bottom']]
        assert len(top) == len(bottom) == n // 10 and not set(top) & set(bottom)
        assert tuple(top) == out['order'][:n // 10] and tuple(bottom) == out['order'][n - n // 10:]
        expected = sorted(members, key=lambda s: (-scores[s], s))
        assert list(out['order']) == expected
        assert min(t['score'] for t in out['top']) >= max(b['score'] for b in out['bottom'])


def test_members_without_scores_are_not_counted_and_carry_reasons():
    members = ids(12) + ['OUTSIDE']
    scores = {sid: float(i) for i, sid in enumerate(ids(12))}
    scores['S000'] = None
    scores['S001'] = float('nan')
    out = selection.select(scores, members, na_reasons={'S000': 'AXIS_WEIGHT_INSUFFICIENT'})
    assert out['N'] == 10 and out['members'] == 13
    assert out['not_eligible'] == {'OUTSIDE': 'NOT_IN_SCORING_POPULATION', 'S000': 'AXIS_WEIGHT_INSUFFICIENT',
                                   'S001': 'SCORE_NOT_FINITE'}
    with pytest.raises(ValueError, match='DUPLICATE_GROUP_MEMBER'):
        selection.select(scores, ['S002', 'S002'])


def test_decimal_scores_are_ordered_exactly():
    members = ids(10)
    scores = {sid: Decimal(i) / Decimal(3) for i, sid in enumerate(members)}
    out = selection.select(scores, members)
    assert out['top'][0] == {'security_id': 'S009', 'rank': 1, 'score': Decimal(9) / Decimal(3)}


def score_result(n=20):
    """A hand-made scoring.score_population-shaped result: Q rises with i, G falls, V None for even i."""
    secs = {}
    for i, sid in enumerate(ids(n)):
        totals = {p: float(i) + k for k, p in enumerate(settings.PRESET_IDS)}
        totals['default'] = totals['balanced']
        secs[sid] = {'axes': {'Q': float(i), 'G': float(n - i), 'V': None if i % 2 == 0 else float(i)},
                     'axis_reasons': {'Q': [], 'G': [], 'V': ['AXIS_WEIGHT_INSUFFICIENT'] if i % 2 == 0 else []},
                     'totals': totals, 'total_reasons': dict.fromkeys(totals)}
    return {'securities': secs}


def test_select_all_strategies_groups_and_alias():
    result = score_result()
    groups = {'U_A': ids(20), 'U_B': ids(20)[5:] + ['NOT_SCORED']}
    out = selection.select_all(result, groups)
    assert set(out) == set(settings.STRATEGY_IDS) | {'QGV_DEFAULT'}
    assert out['QGV_DEFAULT'] is out['QGV_BALANCED']
    q = out['AXIS_Q']['U_A']
    assert (q['N'], q['k'], q['top'][0]['security_id'], q['bottom'][-1]['security_id']) == (20, 2, 'S019', 'S000')
    g = out['AXIS_G']['U_A']
    assert [t['security_id'] for t in g['top']] == ['S000', 'S001']           # G falls with i: higher is better
    v = out['AXIS_V']['U_A']
    assert v['N'] == 10 and v['k'] == 1 and v['not_eligible']['S000'] == 'AXIS_WEIGHT_INSUFFICIENT'
    ub = out['AXIS_V']['U_B']                                                 # odd i in 5..19: 8 names
    assert ub['status'] == 'NOT_RUN' and ub['N'] == 8 and ub['not_eligible']['NOT_SCORED'] == 'NOT_IN_SCORING_POPULATION'
    assert out['QGV_VALUE']['U_B']['N'] == 15 and out['QGV_VALUE']['U_B']['k'] == 1
    with pytest.raises(ValueError, match='GROUP_INVALID'):
        selection.select_all(result, {'U_C': ids(3)})


def test_chain_universe_scoring_selection_on_synthetic_records():
    from decimal import Decimal as D

    from investment_system.qgv import v2_factors, v2_scoring
    from investment_system.research.exp_deciles import scoring, universe

    records = []
    for i in range(14):   # cap = 0.1bn x (1 + 20i): S000 below U-A entry; S000..S004 below U-B
        records.append({'security_id': f'S{i:03}', 'cik': str(i + 1), 'listed': True, 'security_type': 'COMMON',
                        'shares_outstanding': D('100000000'), 'price': D(1 + 20 * i), 'price_label': 'PROXY_LAST_TRADE'})
    uni = universe.build_universes(records, signal_day='2018-02-16')
    assert uni['U_A']['counts']['eligible'] == 13 and uni['U_B']['counts']['eligible'] == 9
    rows, quotes = {}, {}
    for n, sid in enumerate(uni['U_A']['member_securities']):
        metrics = {m: d * n for spec in v2_scoring.SUBMETRICS['GENERAL'].values() for m, d in spec}
        rows[sid] = {'security_id': sid, 'cik': uni['securities'][sid]['cik'], 'state': 'LIVE', 'profile': 'GENERAL',
                     'sic': '3571', 'industry_group': 'synthetic', 'fiscal_year_end': '2017-12-31', 'currency': 'USD',
                     'metrics': metrics, 'calc_version': v2_factors.CALC_VERSION, 'reason_codes': [],
                     'v_inputs_v2': v2_factors.empty_v_inputs()}
        quotes[sid] = {'price': D('10'), 'currency': 'USD'}
    scores = scoring.score_population(rows, quotes, population=uni['U_A']['member_securities'])
    assert scores['summary']['percentile_population_size'] == 13              # U-A only
    groups = {g: uni[g]['member_securities'] for g in settings.GROUPS}
    out = selection.select_all(scores, groups)
    qa, qb = out['AXIS_Q']['U_A'], out['AXIS_Q']['U_B']
    assert (qa['N'], qa['k'], qa['top'][0]['security_id'], qa['bottom'][0]['security_id']) == (13, 1, 'S013', 'S001')
    assert qb['status'] == 'NOT_RUN' and qb['N'] == 9                        # U-B scores come from the U-A pool
    assert qb['not_eligible'] == {}
    assert out['AXIS_V']['U_A']['status'] == 'NOT_RUN' and out['AXIS_V']['U_A']['N'] == 0
    assert out['QGV_BALANCED']['U_A']['N'] == 13                             # Q and G carry the total without V
