"""ChartBars reference (technical/chart_bars.py): fixture == Python reference, W1 weekly rule, missing vs real-zero volume,
price-basis continuity without re-adjustment, merge revisions. Synthetic bars only."""
import importlib.util
import json
from pathlib import Path

import pytest

from investment_system.technical import chart_bars as CB

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/chart_bars_reference_v1.json'


def _reference():
    spec = importlib.util.spec_from_file_location('pattern_reference', ROOT / 'tools/pattern_reference.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _reference()


def _case(case_id):
    return next(c for c in R.chart_cases() if c['id'] == case_id)


def test_fixture_matches_python_reference():
    assert json.loads(FIXTURE.read_text(encoding='utf-8')) == json.loads(json.dumps(R.build_chart(), ensure_ascii=False))
    assert all(c['synthetic'] for c in R.chart_cases())


def test_missing_values_stay_none_and_real_zero_volume_stays_zero():
    s = R.run_chart_case(_case('normalize_codes'))
    b = s['bars']
    assert (b[2]['volume'], b[2]['volume_state'], b[2]['codes']) == (0, 'REPORTED', [])
    assert (b[3]['volume'], b[3]['volume_state'], b[3]['codes']) == (None, 'MISSING', ['VOLUME_MISSING'])
    assert (b[4]['close'], b[4]['ohlc']) == (None, 'MISSING')
    assert b[5]['ohlc'] == 'MISSING' and 'OHLC_INCONSISTENT' in b[5]['codes'] and b[5]['open'] == 30.0
    assert b[6]['codes'] == ['NON_COMPLETE_IN_HISTORY', 'PROVISIONAL_SESSION']
    assert b[11]['state'] == 'PROVISIONAL' and b[11]['codes'] == ['PROVISIONAL_SESSION']
    assert s['quality']['counts']['DELAY_UNKNOWN'] == 1 and 'PROVIDER_FALLBACK' not in s['quality']['codes']


def test_session_dates_use_exchange_timezone_or_provider_label():
    seoul = R.run_chart_case(_case('normalize_seoul_session_date'))
    assert [b['session_date'] for b in seoul['bars']] == ['2030-01-08', '2030-01-09', '2030-01-10']
    tiingo = R.run_chart_case(_case('normalize_fallback_session_label'))
    assert [b['session_date'] for b in tiingo['bars']] == ['2030-01-07', '2030-01-08', '2030-01-09', '2030-01-10']
    assert 'PROVIDER_FALLBACK' in tiingo['quality']['codes'] and tiingo['bars'][-1]['state'] == 'PROVISIONAL'
    dup = R.run_chart_case(_case('normalize_duplicate_session_date'))
    assert [b['ohlc'] for b in dup['bars']] == ['MISSING', 'MISSING', 'PRESENT']


def test_weekly_w1_completion_and_no_partial_sums():
    w = {b['week_start']: b for b in R.run_chart_case(_case('weekly_w1_holiday_missing'))['bars']}
    assert (w['2030-01-07']['state'], w['2030-01-07']['known_at']) == ('COMPLETE', '2030-01-11')
    assert (w['2030-01-14']['known_at'], w['2030-01-14']['session_count']) == ('2030-01-21', 4)  # Friday holiday
    assert w['2030-01-07']['open'] == 50 and w['2030-01-07']['high'] == 52 and w['2030-01-07']['volume'] == 500
    assert w['2030-01-28']['high'] is None and 'OHLC_MISSING_IN_WEEK' in w['2030-01-28']['codes']
    assert w['2030-02-04']['volume'] is None and w['2030-02-04']['close'] == 51
    assert w['2030-02-11']['volume'] == 300 and w['2030-02-11']['state'] == 'PROVISIONAL'
    tail = R.run_chart_case(_case('weekly_tail_not_closed'))['bars'][-1]
    assert (tail['state'], tail['known_at'], tail['codes']) == ('PROVISIONAL', None, ['WEEK_NOT_CLOSED'])
    friday = R.run_chart_case(_case('weekly_friday_in_progress'))['bars'][-1]
    assert friday['state'] == 'PROVISIONAL' and 'PROVISIONAL_DAILY_IN_WEEK' in friday['codes']
    inside = R.run_chart_case(_case('weekly_provisional_inside'))['bars']
    assert inside[1]['state'] == 'PROVISIONAL' and inside[2]['state'] == 'COMPLETE'


def test_weekly_known_at_never_precedes_its_last_session():
    for cid in ('weekly_w1_holiday_missing', 'weekly_provisional_inside', 'weekly_split_straddles_week'):
        for bar in R.run_chart_case(_case(cid))['bars']:
            assert bar['known_at'] is None or bar['known_at'] >= bar['last_session']


@pytest.mark.parametrize('cid,state,codes', [
    ('continuity_not_provided', 'NOT_JUDGEABLE', ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']),
    ('continuity_not_provided_explicit', 'NOT_JUDGEABLE', ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']),
    ('continuity_lookup_failed', 'NOT_JUDGEABLE', ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_LOOKUP_FAILED']),
    ('continuity_invalid_kind', 'NOT_JUDGEABLE', ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_INVALID']),
    ('continuity_no_events', 'CONFIRMED', []),
    ('continuity_dividend_only_window', 'CONFIRMED', []),
    ('continuity_split_in_window', 'NOT_JUDGEABLE', ['CORPORATE_ACTION_IN_WINDOW']),
    ('continuity_starts_on_split', 'CONFIRMED', []),
    ('continuity_coverage_gap', 'NOT_JUDGEABLE', ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_COVERAGE_GAP']),
])
def test_continuity(cid, state, codes):
    assert R.run_chart_case(_case(cid)) == {'state': state, 'reason_codes': codes}


def test_split_marks_straddling_week_na_and_never_reprices():
    c = _case('weekly_split_straddles_week')
    daily = CB.normalize(c['input']['history'])
    before = json.dumps(daily, sort_keys=True)
    split, plain = CB.weekly(daily, c['input']['actions']), CB.weekly(daily, None)
    assert json.dumps(daily, sort_keys=True) == before
    for a, b in zip(split['bars'], plain['bars']):
        if 'CORPORATE_ACTION_IN_BAR' in a['codes']:
            assert a['close'] is None and a['volume'] is None
        else:
            assert all(a[k] == b[k] for k in ('open', 'high', 'low', 'close', 'volume'))
    assert ['CORPORATE_ACTION_IN_BAR' in b['codes'] for b in split['bars']] == [False, True, False]


def test_merge_records_revision_without_overwriting():
    r = R.run_chart_case(_case('merge_revision'))
    assert r['revised'] == ['2030-01-10']
    held = {b['session_date']: b for b in r['series']['bars']}
    assert held['2030-01-10']['close'] == 10 and 'PRICE_REVISED' in held['2030-01-10']['codes']
    assert held['2030-01-14']['volume'] == 101 and held['2030-01-14']['state'] == 'COMPLETE'
    assert 'PROVIDER_MIXED' in r['series']['quality']['codes'] and len(held) == 8


def test_session_set_mismatch_counts_only():
    assert R.run_chart_case(_case('session_set_mismatch')) == {'state': 'MISMATCH', 'reason_codes': ['SESSION_SET_MISMATCH'], 'missing_in_bars': 0, 'missing_in_store': 1}


@pytest.mark.parametrize('mutate', [
    lambda h: h.update(schema='private-history/2'),
    lambda h: h.update(interval='1wk'),
    lambda h: h.update(basis='PROVIDER_ADJUSTED_CLOSE'),
    lambda h: h['bars'][1].update(timestamp=h['bars'][0]['timestamp']),
    lambda h: h['bars'][0].update(volume=-1),
    lambda h: h['bars'][0].update(close=0),
    lambda h: h['bars'][0].update(session_status='DONE'),
    lambda h: h['bars'][0].update(session_date='2030-02-30'),
])
def test_invalid_input_fails_with_fixed_code(mutate):
    h = json.loads(json.dumps(_case('normalize_codes')['input']['history']))
    mutate(h)
    with pytest.raises(CB.ChartBarsError, match='^CHART_BARS_INPUT_INVALID$'):
        CB.normalize(h)
