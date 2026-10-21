"""Pattern signals (technical/patterns.py run) and the official history (technical/pattern_history.py): fixture == Python
reference for every TA_PREP §6 case (B1-B13, D1-D7, P4-P7), PIT on full runs, history append-only rules. Synthetic only."""
import importlib.util
import json
from pathlib import Path

import pytest

from investment_system.technical import chart_bars as CB
from investment_system.technical import pattern_history as H
from investment_system.technical import patterns as P
from investment_system.technical import pit_checks as PIT

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/pattern_signals_reference_v1.json'


def _reference():
    spec = importlib.util.spec_from_file_location('pattern_reference', ROOT / 'tools/pattern_reference.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _reference()
RULES = P.load_rules()
SCEN = {cid: (raw, tf, actions) for cid, raw, tf, actions in R.scenarios()}


def _run(cid):
    raw, tf, actions = SCEN[cid]
    return R.run_raw(raw, tf, actions)


def _events(result, pattern):
    return [(t['event'], t['known_index']) for t in result['transitions'] if t.get('pattern') == pattern]


def test_fixture_matches_python_reference():
    assert json.loads(FIXTURE.read_text(encoding='utf-8')) == json.loads(json.dumps(R.build_signals(), ensure_ascii=False))


@pytest.mark.parametrize('cid,expected', [
    ('B1_box_breakout_confirmed', [('FORMED', 42), ('CONFIRMED', 44), ('OBSERVATION_ENDED', 49)]),
    ('B2_close_equal_to_level_is_not_confirmed', [('FORMED', 42)]),
    ('B3_provisional_bar_only', [('FORMED', 42)]),
    ('B4_failed_within_fail_window', [('FORMED', 42), ('CONFIRMED', 44), ('FAILED', 45)]),
    ('B5_return_after_fail_window', [('FORMED', 42), ('CONFIRMED', 44), ('OBSERVATION_ENDED', 49)]),
    ('B6_breakdown_first_invalidates_breakout', [('FORMED', 42), ('INVALIDATED', 44)]),
    ('B12b_missing_bar_while_formed', [('FORMED', 42), ('NOT_JUDGEABLE', 43)]),
    ('B13_split_crosses_live_window', [('FORMED', 42), ('NOT_JUDGEABLE', 45)]),
])
def test_box_breakout_cases(cid, expected):
    assert _events(_run(cid), 'BOX_BREAKOUT_UP') == expected


def test_b2_boundary_is_exactly_the_level():
    raw = SCEN['B2_close_equal_to_level_is_not_confirmed'][0]
    formed = next(t for t in _run('B2_close_equal_to_level_is_not_confirmed')['transitions'] if t.get('pattern') == 'BOX_BREAKOUT_UP')
    assert raw[44]['close'] == formed['detail']['confirm_level']


def test_b6_breakdown_and_b7_expiry():
    assert _events(_run('B6_breakdown_first_invalidates_breakout'), 'BOX_BREAKDOWN')[:2] == [('FORMED', 42), ('CONFIRMED', 44)]
    first = _events(_run('B7_expired_at_box_max_bars'), 'BOX_BREAKOUT_UP')[:2]
    assert first == [('FORMED', 42), ('EXPIRED', 24 + RULES['params']['BOX_MAX_BARS']['D'])]


@pytest.mark.parametrize('cid', ['B8_1_length_below_min', 'B8_2_one_upper_touch', 'B8_3_one_lower_touch', 'B8_4_close_outside_box', 'B8_5_too_shallow', 'B8_5b_too_deep'])
def test_b8_each_condition_alone_blocks_the_box(cid):
    out = _run(cid)
    assert sum(t['object_kind'] == 'PIVOT' and t['event'] == 'PIVOT_CONFIRMED' for t in out['transitions']) >= 4
    assert not [t for t in out['transitions'] if t.get('pattern') in ('BOX_BREAKOUT_UP', 'BOX_BREAKDOWN', 'BOX')]


def test_b8_length_at_minimum_forms():
    assert _events(_run('B8_1b_length_at_min_forms'), 'BOX_BREAKOUT_UP') == [('FORMED', 36)]


def test_b9_levels_stay_at_formation_atr():
    raw, _, actions = SCEN['B9_levels_fixed_when_atr_changes']
    out = _run('B9_levels_fixed_when_atr_changes')
    formed = next(t for t in out['transitions'] if t.get('pattern') == 'BOX_BREAKOUT_UP' and t['event'] == 'FORMED')
    ctx = P.prepare(CB.normalize(R.history(raw)), RULES, actions)
    assert ctx['atr'][46] > 2 * formed['detail']['atr'] and raw[46]['close'] < formed['detail']['upper'] + 0.25 * ctx['atr'][46]
    assert _events(out, 'BOX_BREAKOUT_UP')[:2] == [('FORMED', 42), ('CONFIRMED', 46)]


def test_b10_gap_and_b11_volume_reference_only():
    gap = next(t for t in _run('B10_gap_breakout')['transitions'] if t.get('pattern') == 'BOX_BREAKOUT_UP' and t['event'] == 'CONFIRMED')
    assert gap['detail']['gap'] is True
    vol = next(t for t in _run('B11_confirm_bar_volume_missing')['transitions'] if t.get('pattern') == 'BOX_BREAKOUT_UP' and t['event'] == 'CONFIRMED')
    assert vol['detail']['volume'] == {'state': 'NOT_AVAILABLE', 'reason_code': 'VOLUME_MISSING'}


def test_b12_b13_not_judgeable_reasons():
    box = [t for t in _run('B12_missing_bar_in_box_window')['transitions'] if t.get('pattern') == 'BOX']
    assert [(t['event'], t['detail']['reason_codes']) for t in box] == [('NOT_JUDGEABLE', ['MISSING_BARS_IN_WINDOW'])]
    split = [t for t in _run('B13_split_crosses_live_window')['transitions'] if t['known_index'] == 45 and t['object_kind'] != 'PIVOT']
    assert len(split) >= 2 and all(t['judgement']['reason_codes'] == ['CORPORATE_ACTION_IN_WINDOW'] for t in split)
    for cid, sub in (('B13b_split_lookup_failed', 'CORPORATE_ACTION_LOOKUP_FAILED'), ('B13c_no_split_events', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED')):
        assert {tuple(t['judgement']['reason_codes']) for t in _run(cid)['transitions']} == {('PRICE_BASIS_CONTINUITY_UNCONFIRMED', sub)}


@pytest.mark.parametrize('cid,expected', [
    ('D1_double_bottom_confirmed', [('FORMED', 37), ('CONFIRMED', 39), ('OBSERVATION_ENDED', 44)]),
    ('D2_double_bottom_failed', [('FORMED', 37), ('CONFIRMED', 39), ('FAILED', 40)]),
    ('D3_double_bottom_invalidated', [('FORMED', 37), ('INVALIDATED', 39)]),
    ('D4_double_bottom_expired', [('FORMED', 37), ('EXPIRED', 48)]),
    ('D5_neckline_passed_before_known', []),
    ('D7_separation_min_minus_one', []),
    ('D7b_separation_max_plus_one', []),
])
def test_double_bottom_cases(cid, expected):
    assert _events(_run(cid), 'DOUBLE_BOTTOM') == expected


def test_d6_nearest_p1_and_d7_max_boundary():
    formed = [t for t in _run('D6_nearest_p1_only')['transitions'] if t.get('pattern') == 'DOUBLE_BOTTOM' and t['event'] == 'FORMED']
    assert [(t['detail']['p1_at'], t['detail']['p2_at']) for t in formed] == [('2030-02-08', '2030-02-22'), ('2030-02-22', '2030-03-08')]
    assert next(t for t in _run('D7c_separation_max_forms')['transitions'] if t.get('pattern') == 'DOUBLE_BOTTOM')['detail']['separation_bars'] == 120


def test_mirrored_cases_swap_patterns():
    swap = {'BOX_BREAKOUT_UP': 'BOX_BREAKDOWN', 'BOX_BREAKDOWN': 'BOX_BREAKOUT_UP', 'DOUBLE_BOTTOM': 'DOUBLE_TOP', 'DOUBLE_TOP': 'DOUBLE_BOTTOM'}
    for a, b in (('B1_mirror_breakdown', 'B1_box_breakout_confirmed'), ('D1_mirror_double_top', 'D1_double_bottom_confirmed')):
        left = sorted((t['pattern'], t['event'], t['known_index']) for t in _run(a)['transitions'] if t.get('pattern') in swap)
        right = sorted((swap[t['pattern']], t['event'], t['known_index']) for t in _run(b)['transitions'] if t.get('pattern') in swap)
        assert left == right


def test_zone_is_not_broken_by_moving_away():
    out = _run('B13c_no_split_events')
    zones = [t for t in out['transitions'] if t['object_kind'] == 'ZONE']
    resistance = [t for t in zones if t['detail'].get('close_side') == 'BELOW']
    assert resistance and all(t['event'] == 'ACTIVE' for t in resistance)
    broken = [t for t in zones if t['event'] == 'BROKEN']
    assert broken and broken[0]['detail']['direction'] == 'UP' and broken[0]['known_index'] == 44


def test_preview_is_display_only():
    raw = SCEN['B3_provisional_bar_only'][0]
    s = CB.normalize(R.history(raw))
    out = P.run(s, RULES, R.ALL_SPLIT_FREE)
    assert {p['note_ko'] for p in P.preview(s, out)} == {'잠정 봉 기준 조건 충족 · 확정 아님'}
    assert out['transitions'] == P.run(CB.normalize(R.history(raw[:-1])), RULES, R.ALL_SPLIT_FREE)['transitions']


def _full_run(timeframe, actions):
    def run(raw):
        if not raw:
            return []
        s = CB.normalize(R.history(raw))
        return P.run(s if timeframe == 'D' else CB.weekly(s, actions), RULES, actions)['transitions']
    return run


def _cut(raw):
    return CB.normalize(R.history(raw))['bars'][-1]['session_date'] if raw else None


@pytest.mark.parametrize('cid', ['B4_failed_within_fail_window', 'B12_missing_bar_in_box_window', 'B13_split_crosses_live_window', 'D6_nearest_p1_only', 'random_walk_3'])
def test_prefix_invariance_full_run(cid):
    raw, tf, actions = SCEN[cid]
    assert PIT.prefix_violations(_full_run(tf, actions), raw, _cut) == []
    assert PIT.pivot_lag_violations(_full_run(tf, actions)(raw), 3) == []


def test_future_mutation_full_run():
    raw, tf, actions = SCEN['random_walk_3']
    for t in (60, 140):
        assert PIT.future_mutation_violations(_full_run(tf, actions), raw, t, lambda i, b: {**b, 'open': 1, 'high': 9999, 'low': 0.5, 'close': 9000 if i % 2 else 1}, _cut) == []


def test_history_log_p4_p5():
    case = next(c for c in R.signal_cases() if c['id'] == 'P4_P5_history')
    out = R.history_steps(case['input'])
    log = {row[0]: row[1:] for row in out['log'] if row[0] != 'prefix'}
    assert log['repeat'][0]['added'] == 0 and log['repeat'][0]['conflicts'] == 0
    assert log['user_settings'] == ['HISTORY_USER_SETTINGS_REFUSED'] and log['version_mixed'] == ['HISTORY_VERSION_MIXED']
    assert log['prefix_order_equals_full_once'] == [True]
    assert log['no_split_events'][0]['added'] == 0 and log['no_split_events'][1] == 0
    assert log['revised_dates'] == [['2030-03-08']]
    revisions = [r for r in out['records'] if r['event'] == 'DATA_REVISION']
    assert revisions and {r['detail']['note_ko'] for r in revisions} == {'자료 수정 후 재계산 결과 다름'}
    original = [r for r in out['records'] if r['event'] == 'CONFIRMED' and r['pattern'] == 'BOX_BREAKOUT_UP']
    assert [r['known_index'] for r in original] == [44]   # the earlier record is kept as it was
    assert [r['seq'] for r in out['records']] == list(range(1, len(out['records']) + 1))


def test_history_refuses_back_dated_and_keeps_records_immutable():
    raw = SCEN['B1_box_breakout_confirmed'][0]
    full = R.run_raw(raw, 'D', R.ALL_SPLIT_FREE)
    hist = H.PatternHistory(full['symbol'], 'D', full['rule_version'], full['params_sha256'])
    hist.append(full, 'T1')
    changed = R.run_raw([dict(b) for b in raw[:44]] + [{**raw[44], 'close': 110.8, 'high': 111.3}] + raw[45:], 'D', R.ALL_SPLIT_FREE)
    counts = hist.append(changed, 'T2')
    assert counts['added'] == 0 and counts['late'] + counts['conflicts'] > 0
    snapshot = hist.records()
    snapshot[0]['event'] = 'EDITED'
    assert hist.records()[0]['event'] != 'EDITED'
    book = H.PatternHistoryBook()
    book.append(full, 'T1')
    book.history_for({**full, 'params_sha256': 'f' * 64})
    assert len(book.keys()) == 2
    with pytest.raises(H.PatternHistoryError, match='HISTORY_USER_SETTINGS_REFUSED'):
        book.append(R.run_raw(raw, 'D', R.ALL_SPLIT_FREE, R.rules_with(BREAK_BUFFER_ATR=0)), 'T3')


def test_back_dated_new_object_is_withheld_entirely():
    raw = SCEN['B1_box_breakout_confirmed'][0]
    full = R.run_raw(raw, 'D', R.ALL_SPLIT_FREE)
    hist = H.PatternHistory(full['symbol'], 'D', full['rule_version'], full['params_sha256'])
    hist.append({**full, 'transitions': [t for t in full['transitions'] if t.get('pattern') != 'BOX_BREAKOUT_UP']}, 'T1')
    counts = hist.append(full, 'T2')
    assert counts['late'] == 3 and counts['added'] == 0
    assert not [r for r in hist.records() if r.get('pattern') == 'BOX_BREAKOUT_UP']
