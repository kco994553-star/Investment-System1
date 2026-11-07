"""Synthetic prices/IDs only. Expectations are hand-derived, not copied from the implementation."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
import importlib
import math
from zoneinfo import ZoneInfo

import pytest

from investment_system.research.exp_deciles import schedule

S = '2018-02-16'
IDS = ('momentum_3m', 'momentum_6m', 'momentum_12m', 'volatility_6m', 'dollar_volume_6m')


def evidence():
    return dict(identity_status='DOCUMENT_RECONSTRUCTED', identity_reference='SYNTHETIC:identity',
                security_id='SYNTHETIC:SEC1', currency='USD', currency_reference='SYNTHETIC:currency',
                no_split_start='2017-01-01', no_split_end=S, no_split_reference='SYNTHETIC:actions',
                trade_scope_status='CONFIRMED_MATCH', trade_scope_reference='SYNTHETIC:matching-trades')


def bars():
    rows, day = [], date(2017, 2, 16)
    while day <= date(2018, 2, 16):
        if schedule.is_session(day):
            timestamp = datetime.combine(day, time(), ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()
            rows.append(dict(date=day.isoformat(), source_timestamp=timestamp,
                             returned_symbol='TEST', requested_symbol='TEST', asof='-', price_basis='RAW',
                             close='100', vwap='10.25', volume='100', quality_reasons=[], source_sha256='a'*64))
        day += timedelta(days=1)
    return rows


def measure(rows=None, ev=None):
    mod = importlib.import_module('investment_system.research.exp_deciles.technical_measures')
    return mod.measure(bars() if rows is None else rows, signal_day=S, symbol='TEST',
                       series_id='SYNTHETIC:REQUEST1', evidence=evidence() if ev is None else ev)


def test_sample_stdev_full_consecutive_returns_not_annualized():
    rows = bars()
    for r in rows:
        if r['date'] == '2017-08-17':
            r['close'] = '110'
        elif r['date'] >= '2017-08-18':
            r['close'] = '99'
    m = measure(rows)['metrics']
    vol = m['volatility_6m']
    # +10%, -10%, then 125 zeros: sum=0; sum squares=200 percentage-points squared.
    assert float(vol['value']) == pytest.approx(math.sqrt(200/126), abs=1e-13)
    assert (vol['observed_days'], vol['expected_days']) == (127, 127)
    assert (vol['observed_price_days'], vol['expected_price_days']) == (128, 128)
    assert vol['anchor_day'] == '2017-08-16'
    assert Decimal(m['momentum_6m']['value']) == -1
    assert Decimal(m['momentum_3m']['value']) == 0
    assert Decimal(m['dollar_volume_6m']['value']) == Decimal('1025')


def test_constant_price_zero_is_valid_and_boundary_prices_do_not_change_volume():
    out = measure()
    assert Decimal(out['metrics']['volatility_6m']['value']) == 0
    assert out['metrics']['momentum_12m']['gt_zero'] is False
    assert out['metrics']['dollar_volume_6m']['observed_days'] == 127
    assert out['qgv_join_key'] == [S, 'SYNTHETIC:SEC1']


def test_missing_anchor_and_interior_price_do_not_bridge_or_forward_fill():
    rows = [r for r in bars() if r['date'] != '2017-08-16']
    m = measure(rows)['metrics']
    assert m['volatility_6m']['value'] is None
    assert m['volatility_6m']['observed_days'] == 126
    assert m['momentum_6m']['value'] is None
    assert m['dollar_volume_6m']['value'] is not None  # boundary excluded from volume
    rows = [r for r in bars() if r['date'] != '2018-01-10']
    m = measure(rows)['metrics']
    assert m['volatility_6m']['observed_days'] == 125  # missing date breaks two adjacent returns
    assert m['volatility_6m']['value'] is None
    assert m['dollar_volume_6m']['value'] is None
    assert Decimal(m['dollar_volume_6m']['mean_observed']) == 1025


def test_action_evidence_is_window_specific_and_raw_is_separate():
    ev = evidence(); ev['no_split_start'] = '2017-08-16'
    m = measure(ev=ev)['metrics']
    assert m['momentum_6m']['value'] is not None
    assert m['momentum_12m']['value'] is None
    assert m['momentum_12m']['raw_value'] is not None
    assert 'ACTION_BASIS_UNCONFIRMED' in m['momentum_12m']['null_reasons']
    ev['identity_status'] = 'UNKNOWN'; ev['security_id'] = None
    out = measure(ev=ev)
    assert out['qgv_join_key'] is None
    assert out['metrics']['volatility_6m']['value'] is None
    assert out['metrics']['volatility_6m']['raw_value'] is not None


@pytest.mark.parametrize('field,value,reason', [
    ('currency', None, 'USD_UNCONFIRMED'),
    ('trade_scope_status', 'SAME_BAR_ONLY', 'TRADE_SCOPE_UNCONFIRMED'),
    ('trade_scope_reference', None, 'TRADE_SCOPE_UNCONFIRMED'),
])
def test_volume_needs_currency_and_trade_scope_evidence(field, value, reason):
    ev = evidence(); ev[field] = value
    m = measure(ev=ev)['metrics']['dollar_volume_6m']
    assert m['value'] is None and reason in m['null_reasons']
    assert Decimal(m['raw_value']) == 1025
    assert Decimal(m['close_volume_proxy']['mean_complete']) == 10000


def test_vwap_missing_never_uses_close_proxy_and_zero_volume_is_observed():
    rows = bars(); rows[-1]['vwap'] = None
    m = measure(rows)['metrics']['dollar_volume_6m']
    assert m['value'] is None and m['observed_days'] == 126
    assert Decimal(m['close_volume_proxy']['mean_complete']) == 10000
    for r in rows:
        r['vwap'], r['volume'] = '10', '0'
    assert Decimal(measure(rows)['metrics']['dollar_volume_6m']['value']) == 0


def test_duplicate_conflict_and_future_data_boundaries():
    rows = bars()
    assert measure(rows + [deepcopy(rows[-1])])['metrics'] == measure(rows)['metrics']
    conflict = dict(rows[-1], close='101')
    with pytest.raises(ValueError, match='CONFLICTING_DAY'):
        measure(rows + [conflict])
    future = dict(conflict, date='2018-02-20', source_timestamp='2018-02-20T05:00:00Z')
    assert measure(rows + [future])['metrics'] == measure(rows)['metrics']


def test_decimal_context_does_not_change_measurements():
    with localcontext() as c:
        c.prec = 9
        low = measure()
    with localcontext() as c:
        c.prec = 70
        high = measure()
    assert low == high


def records(n):
    return [dict(signal_day=S, series_id=f'SYNTHETIC:R{i:03}', security_id=f'SYNTHETIC:S{i:03}',
                 metrics={key: dict(value=str(i), null_reasons=[]) for key in IDS}) for i in range(n)]


def board(rows, *, unknown=False):
    mod = importlib.import_module('investment_system.research.exp_deciles.technical_leaderboard')
    group = dict(group_id='SYNTHETIC:GROUP', signal_day=S, membership_status='UNKNOWN' if unknown else 'CONFIRMED',
                 member_security_ids=None if unknown else [r['security_id'] for r in rows],
                 membership_source='SYNTHETIC:MEMBERSHIP')
    return mod.build_board(rows, group=group)


@pytest.mark.parametrize('n,counts', [(10,[1]*10), (11,[1,2,1,1,1,1,1,1,1,1]), (23,[2,3,3,3,2,2,2,2,2,2])])
def test_extreme_tails_and_middle_remainder_allocation(n, counts):
    got = board(records(n))['metrics']['volatility_6m']
    assert [sum(r['decile'] == d for r in got['rows']) for d in range(10,0,-1)] == counts
    assert got['rows'][0]['security_id'] == f'SYNTHETIC:S{n-1:03}'
    assert got['rows'][0]['rank'] == 1 and got['rows'][0]['decile'] == 10
    assert got['rows'][-1]['decile'] == 1


def test_nine_has_ranks_median_but_no_deciles():
    got = board(records(9))['metrics']['momentum_3m']
    assert got['n_valid'] == 9 and Decimal(got['median']) == 4
    assert [r['rank'] for r in got['rows']] == list(range(1,10))
    assert all(r['decile'] is None and r['conditions']['top_decile'] is None for r in got['rows'])


def test_negative_equal_values_keep_four_independent_momentum_conditions():
    rows = records(10)
    for r in rows: r['metrics']['momentum_3m']['value'] = '-5'
    got = board(list(reversed(rows)))['metrics']['momentum_3m']['rows']
    assert got[0]['security_id'] == 'SYNTHETIC:S000'
    assert got[0]['conditions'] == dict(gt_zero=False, ge_median=True, gt_median=False,
                                       top_decile=True, bottom_decile=False, exclude_D10=False)
    assert got[-1]['conditions']['bottom_decile'] is True


def test_unrounded_order_not_display_rounding():
    rows = records(10)
    rows[0]['metrics']['momentum_3m']['value'] = '9.000000000000000001'
    got = board(rows)['metrics']['momentum_3m']['rows']
    assert got[0]['security_id'] == 'SYNTHETIC:S000'


def test_missing_metric_does_not_change_other_metrics_n():
    rows = records(11); rows[0]['metrics']['volatility_6m']['value'] = None
    got = board(rows)
    assert got['metrics']['momentum_3m']['n_valid'] == 11
    assert got['metrics']['volatility_6m']['n_valid'] == 10


def test_unknown_group_preserves_absolute_only_without_invented_n():
    got = board(records(2), unknown=True)['metrics']['momentum_3m']
    assert got['n_valid'] is None and got['n_members'] is None and got['median'] is None
    assert all(r['rank'] is None and r['decile'] is None for r in got['rows'])
    assert any(r['conditions']['gt_zero'] is True for r in got['rows'])
    assert all(r['conditions']['ge_median'] is None for r in got['rows'])


def test_duplicate_security_and_mixed_dates_are_rejected():
    rows = records(10); rows[1]['security_id'] = rows[0]['security_id']
    with pytest.raises(ValueError, match='DUPLICATE'):
        board(rows)
    rows = records(10); rows[1]['signal_day'] = '2018-02-15'
    with pytest.raises(ValueError, match='SIGNAL_DAY_MISMATCH'):
        board(rows)


def test_filter_keeps_original_ranks_and_missing_volatility_does_not_pass():
    mod = importlib.import_module('investment_system.research.exp_deciles.technical_leaderboard')
    rows = records(12); rows[0]['metrics']['volatility_6m']['value'] = None
    got = board(rows); original = deepcopy(got)
    kept = mod.filter_board(got, [{'metric':'volatility_6m','condition':'exclude_D10'},
                                 {'metric':'momentum_3m','condition':'ge_median'}])
    assert kept == ['SYNTHETIC:S006','SYNTHETIC:S007','SYNTHETIC:S008','SYNTHETIC:S009','SYNTHETIC:S010']
    assert got == original
    assert 'SYNTHETIC:S000' not in mod.filter_board(got, [{'metric':'volatility_6m','condition':'exclude_D10'}])
    assert mod.filter_board(board(records(9)), [{'metric':'volatility_6m','condition':'exclude_D10'}]) == []


def test_board_keeps_observation_units_and_rejects_mixed_settings():
    row = measure()
    got = board([row])
    metric = got['metrics']['volatility_6m']['rows'][0]
    assert metric['unit'] == 'PERCENT_PER_DAY'
    assert metric['observed_days'] == 127 and metric['expected_price_days'] == 128
    assert got['settings_sha256'] == row['settings_sha256']
    row['settings_version'] = 'OTHER_FORMULA'
    with pytest.raises(ValueError, match='SETTINGS_MISMATCH'):
        board([row])


def test_non_session_calendar_boundary_uses_prior_session_close():
    mod = importlib.import_module('investment_system.research.exp_deciles.technical_measures')
    got = mod.measure(bars(), signal_day='2017-11-27', symbol='TEST', series_id='SYNTHETIC:R', evidence=evidence())
    # Sunday/Saturday calendar boundaries use preceding Friday closes, never the next Monday.
    assert got['metrics']['momentum_3m']['anchor_day'] == '2017-08-25'
    assert got['metrics']['volatility_6m']['anchor_day'] == '2017-05-26'
    assert got['metrics']['momentum_12m']['value'] is None
    assert got['metrics']['momentum_6m']['value'] is not None
    from datetime import date
    assert mod.boundary(date(2020, 5, 31), 3) == date(2020, 2, 29)


def test_missing_volume_quality_does_not_poison_close_only_metrics():
    rows = bars()
    rows[-1].update(volume=None, quality_reasons=['VOLUME_MISSING'])
    metrics = measure(rows)['metrics']
    assert all(Decimal(metrics[k]['value']) == 0 for k in IDS[:4])
    assert metrics['dollar_volume_6m']['value'] is None
    rows[-1]['quality_reasons'] = ['OHLC_INCONSISTENT']
    assert measure(rows)['metrics']['volatility_6m']['value'] is None


def test_unmeasured_group_member_is_retained_without_reducing_original_n():
    mod = importlib.import_module('investment_system.research.exp_deciles.technical_leaderboard')
    rows = records(10)
    group = dict(group_id='SYNTHETIC:G', signal_day=S, membership_status='CONFIRMED',
                 member_security_ids=[r['security_id'] for r in rows]+['SYNTHETIC:MISSING'], membership_source='SYNTHETIC:S')
    m = mod.build_board(rows, group=group)['metrics']['momentum_3m']
    assert m['n_members'] == 11 and m['n_valid'] == 10
    missing = next(r for r in m['rows'] if r['security_id'] == 'SYNTHETIC:MISSING')
    assert missing['rank'] is None and missing['conditions']['exclude_D10'] is None
    empty = board([])['metrics']['momentum_3m']
    assert empty['n_valid'] == 0 and empty['median'] is None and empty['rows'] == []


@pytest.mark.parametrize('n,k', [(19,1), (20,2)])
def test_tail_size_changes_only_at_floor_boundary(n,k):
    m = board(records(n))['metrics']['momentum_3m']
    assert m['k'] == k
    assert sum(r['conditions']['top_decile'] for r in m['rows']) == k
    assert sum(r['conditions']['bottom_decile'] for r in m['rows']) == k
