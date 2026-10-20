"""Pattern rules + swing pivots (technical/patterns.py): fixture == Python reference, config copy == JSON, parameter hash,
PIT prefix invariance / future mutation / pivot lag (§13.2), provisional tail, continuity judgement. Synthetic only."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from investment_system.technical import chart_bars as CB
from investment_system.technical import patterns as P
from investment_system.technical import pit_checks as PIT

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/pattern_engine_reference_v1.json'
WEB = ROOT / 'src/investment_system/product/web_assets'


def _reference():
    spec = importlib.util.spec_from_file_location('pattern_reference', ROOT / 'tools/pattern_reference.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _reference()
RULES = P.load_rules()


def _case(case_id):
    return next(c for c in R.engine_cases() if c['id'] == case_id)


def test_fixture_matches_python_reference():
    assert json.loads(FIXTURE.read_text(encoding='utf-8')) == json.loads(json.dumps(R.build_engine(), ensure_ascii=False))


def test_rules_are_research_defaults_with_canonical_hash():
    assert (RULES['schema'], RULES['rule_version'], RULES['status']) == ('pattern-rules/1', 'pattern-rules/1', 'RESEARCH_DEFAULT')
    assert RULES['label_ko'] == '연구 기본값 · 투자 유용성 미검증'
    assert RULES['params_sha256'] == P.params_sha256(RULES['params'])
    assert P.params_sha256({'a': 1.0, 'b': [0.5]}) == P.params_sha256({'b': [0.5], 'a': 1})
    broken = copy.deepcopy(RULES)
    broken['params']['PIVOT_K']['D'] = 4
    with pytest.raises(P.PatternRulesError):
        P.check_rules(broken)
    assert P.run_mode(RULES) == 'OFFICIAL' and P.run_mode(R.rules_with(SWING_MIN_ATR=2)) == 'USER_SETTINGS'


def test_device_config_copy_is_generated_from_json():
    assert (WEB / 'pattern-config-defaults.js').read_text(encoding='utf-8') == R.config_js()
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(WEB / 'pattern-config-defaults.js')], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == RULES


def test_atr_port_matches_research_indicators_shape():
    bars = [{'high': 101.0, 'low': 99.0, 'close': 100.0} for _ in range(20)]
    atr = P.atr14(bars)
    assert atr[:14] == [None] * 14 and atr[14] == 2 and atr[19] == 2
    bars[16] = {'high': None, 'low': None, 'close': None}
    atr = P.atr14(bars)
    assert atr[16:] == [None] * 4   # a missing bar restarts the warm-up, never bridges


def _daily(raw):
    return CB.normalize(R.history(raw))


def _run(timeframe='D', actions=R.ALL_SPLIT_FREE, rules=RULES):
    def run(raw):
        if not raw:
            return []
        s = _daily(raw)
        return P.run_pivots(s if timeframe == 'D' else CB.weekly(s, actions), rules, actions)['transitions']
    return run


def _cut(raw):
    return _daily(raw)['bars'][-1]['session_date'] if raw else None


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_prefix_invariance_and_pivot_lag_on_random_walks(seed):
    raw = R.random_walk(seed, 180)
    assert PIT.prefix_violations(_run(), raw, _cut) == []
    assert PIT.pivot_lag_violations(_run()(raw), 3) == []


def test_prefix_invariance_weekly_from_daily_prefixes():
    raw = R.zigzag(260, legs=(24, -18, 30, -27, 21, -12, 36, -30), steps=15)
    transitions = _run('W')(raw)
    assert transitions and PIT.prefix_violations(_run('W'), raw, _cut, start=30) == []
    assert PIT.pivot_lag_violations(transitions, 2) == []


def test_prefix_invariance_with_missing_bars_and_split_segments():
    raw = R.random_walk(11, 160)
    for n in (40, 41, 90):
        raw[n] = {**raw[n], 'open': None, 'high': None, 'low': None, 'close': None}
    split = {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2031-12-31', 'events': [{'kind': 'SPLIT', 'effective_date': raw[120]['day']}]}
    assert PIT.prefix_violations(_run(actions=split), raw, _cut) == []


@pytest.mark.parametrize('t', [25, 60, 130])
def test_future_mutation_never_changes_known_transitions(t):
    raw = R.random_walk(5, 170)
    extreme = lambda i, b: {**b, 'open': 1, 'high': 9999, 'low': 0.5, 'close': 9000 if i % 2 else 1, 'volume': 0}
    missing = lambda i, b: {**b, 'open': None, 'high': None, 'low': None, 'close': None, 'volume': None}
    assert PIT.future_mutation_violations(_run(), raw, t, extreme, _cut) == []
    assert PIT.future_mutation_violations(_run(), raw, t, missing, _cut) == []


def test_pit_helpers_detect_a_lookahead_leak():
    raw = R.random_walk(5, 120)

    def leaky(raw_bars):  # dates every pivot one bar early: must be caught
        return [{**x, 'known_at': _daily(raw_bars)['bars'][x['known_index'] - 1]['session_date']} for x in _run()(raw_bars)]
    assert PIT.prefix_violations(leaky, raw, _cut)


def test_provisional_tail_never_changes_transitions():
    raw = R.random_walk(9, 150)
    tail = {**raw[-1], 'session_status': 'IN_PROGRESS', 'high': 9999, 'low': 0.5}
    assert _run()(raw[:-1] + [tail]) == _run()(raw[:-1])


def test_without_events_every_pivot_is_not_judgeable():
    out = R.run_engine_case(_case('pivots_zigzag_not_provided'))
    assert out['transitions'] and all(t['judgement'] == {'state': 'NOT_JUDGEABLE', 'reason_codes': ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']} for t in out['transitions'])
    failed = P.run_pivots(_daily(R.zigzag(120)), RULES, {'status': 'LOOKUP_FAILED'})
    assert {tuple(t['judgement']['reason_codes']) for t in failed['transitions']} == {('PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_LOOKUP_FAILED')}


def test_split_bounds_windows_and_restarts_atr():
    out = R.run_engine_case(_case('pivots_split_segments'))
    (s0, e0), (s1, e1) = out['segments']
    assert s1 == e0 + 1
    for t in out['transitions']:
        assert t['known_index'] <= e0 or t['anchor_index'] - 3 >= s1
        assert t['judgement']['state'] == 'CONFIRMED'
    assert min(t['anchor_index'] for t in out['transitions'] if t['anchor_index'] >= s1) - s1 >= 14


def test_tie_rule_supersede_and_alternation():
    tie = R.run_engine_case(_case('pivots_tie_and_alternation'))['transitions']
    assert [(t['event'], t['detail']['pivot'], t['anchor_index'], t['known_index']) for t in tie] == [
        ('PIVOT_CONFIRMED', 'HIGH', 20, 23), ('PIVOT_CONFIRMED', 'LOW', 26, 29), ('PIVOT_CONFIRMED', 'HIGH', 31, 34)]
    sup = R.run_engine_case(_case('pivots_superseded'))['transitions']
    assert [(t['event'], t['anchor_index'], t['known_index']) for t in sup] == [
        ('PIVOT_CONFIRMED', 20, 23), ('SUPERSEDED', 20, 34), ('PIVOT_CONFIRMED', 31, 34), ('PIVOT_CONFIRMED', 35, 38)]
    assert sup[1]['superseded_by'] == sup[2]['object_id']


def test_missing_bar_window_is_not_judged():
    out = R.run_engine_case(_case('pivots_missing_bar_in_window'))
    assert out['skipped']['MISSING_BARS_IN_WINDOW'] == 7
    assert all(not (t['anchor_index'] - 3 <= 24 <= t['known_index']) for t in out['transitions'])


def test_structure_is_a_description_not_a_regime():
    assert P.structure([]) == {'state': 'NOT_AVAILABLE', 'reason_code': 'INSUFFICIENT_PIVOTS', 'label_ko': None}
    up = [{'pivot': 'LOW', 'price': 1}, {'pivot': 'HIGH', 'price': 3}, {'pivot': 'LOW', 'price': 2}, {'pivot': 'HIGH', 'price': 4}]
    assert P.structure(up)['label_ko'] == '고점·저점 상승'


def test_outputs_carry_no_probability_or_score_fields():
    text = json.dumps([json.loads(c['expected_json']) for c in json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']], ensure_ascii=False).lower()
    for word in ('probability', 'win_rate', 'score', 'confidence', '확률', '승률', '%'):
        assert word not in text
