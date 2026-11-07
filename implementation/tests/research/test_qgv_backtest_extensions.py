"""Independent, hand-counted decile and matched-selection expectations."""
import copy
import importlib

import pytest


def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.extensions')
    except ModuleNotFoundError:
        pytest.fail('extension registry and selection interface missing')


def population(n):
    identities = {f'S{i:03}': dict(cik=str(i + 1), security_id=f'S{i:03}', issuer_id=f'I{i:03}') for i in range(n)}
    scores = {sid: dict(total=100 - i / 10, axes={a: dict(score=50) for a in ('Q', 'G', 'V')}) for i, sid in enumerate(identities)}
    return identities, scores


def test_default_registry_preserves_40_60_and_activates_only_20_12():
    module = api()
    extension = module.default_extension()
    module.validate_extension(extension)
    cells = module.registered_cells(extension)
    assert len([c for c in cells if c['kind'] == 'QGV_DECILE']) == 40
    assert len([c for c in cells if c['kind'] == 'FACTOR_PAIR']) == 60
    active = module.selected_cells(extension, 'primary')
    assert len([c for c in active if c['kind'] == 'QGV_DECILE']) == 20
    assert len([c for c in active if c['kind'] == 'FACTOR_PAIR']) == 12
    assert {c['factor_id'] for c in active if c['kind'] == 'FACTOR_PAIR'} == {'F03', 'F04', 'F06', 'F07', 'F10', 'F14'}
    assert all(c['cost_bps'] == 10 and c['rebalance'] == 'QUARTERLY' for c in active)


@pytest.mark.parametrize('n,first,last', [(100,10,10),(101,11,10),(109,11,10),(500,50,50)])
def test_decile_boundaries_cover_every_issuer_once(n, first, last):
    module = api()
    identities, scores = population(n)
    plans = [module.selection_plan(identities, scores, group='U-BOOK200', signal_day='2020-02-14', decile=d) for d in range(1,11)]
    assert len(plans[0].selected) == first
    assert len(plans[-1].selected) == last
    assert len({r['security_id'] for p in plans for r in p.selected}) == n
    assert plans[0].selected[0]['security_id'] == 'S000'
    assert plans[-1].selected[-1]['security_id'] == f'S{n-1:03}'
    assert all(p.slots == len(p.selected) for p in plans)


def test_missing_scores_are_not_the_worst_decile_and_failed_date_blocks():
    module = api()
    identities, scores = population(100)
    scores['S000']['total'] = None
    with pytest.raises(ValueError, match='NO_DECILE_COVERAGE'):
        module.selection_plan(identities, scores, group='U-BOOK200', signal_day='2020-02-14', decile=10)


def test_ties_and_economic_issuer_dedup_are_input_order_independent():
    module = api()
    identities, scores = population(101)
    identities['S100']['issuer_id'] = identities['S000']['issuer_id']
    for row in scores.values():
        row['total'] = 50
    a = module.selection_plan(identities, scores, group='U-BOOK200', signal_day='2020-02-14', decile=1)
    b = module.selection_plan(dict(reversed(list(identities.items()))), dict(reversed(list(scores.items()))), group='U-BOOK200', signal_day='2020-02-14', decile=1)
    assert a == b
    assert a.eligible_count == 100
    assert a.boundary_tie is True
    assert [r['security_id'] for r in a.selected] == [f'S{i:03}' for i in range(10)]


def test_matched_pair_intersects_before_both_selections_without_rescoring():
    module = api()
    identities, scores = population(110)
    values = {sid: float(i+1) for i,sid in enumerate(identities) if i >= 10}
    original = copy.deepcopy(scores)
    factor, qgv = module.matched_plans(identities, scores, values, factor_id='F03', group='U-SPX-HIST', signal_day='2020-02-14')
    assert factor.eligible_count == qgv.eligible_count == 100
    assert factor.slots == qgv.slots == 10
    assert factor.selected[0]['security_id'] == qgv.selected[0]['security_id'] == 'S010'
    assert scores == original
    high, qgv = module.matched_plans(identities, scores, values, factor_id='F14', group='U-SPX-HIST', signal_day='2020-02-14')
    assert high.selected[0]['security_id'] == 'S109'
    assert qgv.selected[0]['security_id'] == 'S010'


def test_explicit_experiment_selection_never_silently_falls_back():
    module = api()
    ext = module.default_extension()
    first = module.selected_cells(ext, 'primary')[0]['id']
    assert len(module.selected_cells(ext, 'primary', [first])) == 1
    with pytest.raises(ValueError, match='UNKNOWN_EXPERIMENT'):
        module.selected_cells(ext, 'primary', ['typo'])
    changed = copy.deepcopy(ext)
    changed['active_factors'] = ['F03']
    with pytest.raises(ValueError, match='ACTIVE_FACTOR_SET'):
        module.validate_extension(changed)
