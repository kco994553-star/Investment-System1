"""Virtual trading rules v1 (PROVISIONAL): reference behaviour, vectors and boundaries. Synthetic inputs only."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import virtual_trading as vt  # noqa: E402
import virtual_trading_reference as ref  # noqa: E402


def test_config_is_provisional_and_not_started():
    c = vt.load_config()
    assert c['status'] == 'PROVISIONAL_UNCALIBRATED' and c['start_date'] is None
    assert c['buy_limit'] == 1000000 and c['sell_limit'] == 1000000
    assert c['abnormal_drop'] == {'window_sessions': 20, 'lookback_sessions': 252, 'k': 2}
    assert c['v_slope'] == {'lookback_sessions': 20, 'threshold': 10}
    assert c['sector_basis'] == 'SP500_SUBSTITUTE_D22_PENDING'
    assert all(v.split()[0].startswith('D-') for v in c['provenance'].values())


def test_vectors_are_current():
    assert subprocess.run([sys.executable, str(ROOT / 'tools/virtual_trading_reference.py'), '--check'],
                          capture_output=True, text=True).stdout.strip() == 'VIRTUAL_TRADING_REFERENCE_OK'


def test_device_copy_of_config_matches_json():
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1]).CONFIG))'
    out = subprocess.run(['node', '-e', script, str(ROOT / 'src/investment_system/product/web_assets/virtual-trading.js')],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == vt.load_config()


def test_no_start_date_records_nothing():
    r = vt.run_ledger(vt.load_config(), ref.base_ledger(n=30))
    assert r['state'] == 'NOT_STARTED' and r['trades'] == [] and r['days'] == []


def scenario(name):
    return next(s for s in ref.scenarios() if s['name'] == name)


def test_execution_is_next_session_and_limits_hold():
    s = scenario('set_a_deposit_buys')
    r = vt.run_ledger(s['config'], s['ledger'])
    days = r['days']
    assert days[0]['executed'] == [] and days[0]['orders']
    for prev, cur in zip(days, days[1:]):
        assert {(t['company'], t['decided_on']) for t in cur['executed']} <= {(o['company'], prev['date']) for o in prev['orders']}
        assert all(t['decided_on'] == prev['date'] for t in cur['executed'])
    for d in days:
        assert sum(o['amount'] for o in d['orders'] if o['side'] == 'BUY') <= 1000000
        assert sum(o['amount'] for o in d['orders'] if o['side'] == 'SELL') <= 1000000
        assert all(o['amount'] >= 10000 for o in d['orders'])
        assert len({o['company'] for o in d['orders']}) == len(d['orders'])


def test_rule_paths_in_shadow_scenario():
    s = scenario('shadow_rules')
    r = vt.run_ledger(s['config'], s['ledger'])
    d = s['ledger']['sessions']
    by = {x['date']: x for x in r['days']}
    j = lambda i, c: by[d[i]]['judgements'][c]  # noqa: E731
    assert j(280, 'aaa')['main'] == 'REDUCE_REVIEW' and 'OVERWEIGHT_GAP' in j(280, 'aaa')['reason_codes']
    assert j(284, 'bbb')['main'] == 'RISK_RECHECK' and 'QG_DECLINE' in j(284, 'bbb')['reason_codes']
    assert any(o['company'] == 'bbb' and o['side'] == 'SELL' for o in by[d[284]]['orders'])
    assert j(283, 'ccc')['main'] == 'BLOCK' and j(283, 'ccc')['reason_codes'] == ['DATA_PRICE_MISSING']
    assert j(286, 'ccc')['reason_codes'][:1] == ['USER_HOLD'] and 'INCREASE_CANDIDATE' in j(286, 'ccc')['aux']
    assert not any(o['company'] == 'ccc' for o in by[d[286]]['orders'])
    assert j(288, 'aaa')['main'] == 'RISK_RECHECK' and 'RECHECK_ABNORMAL_DROP' in j(288, 'aaa')['reason_codes']
    assert not any(o['company'] == 'aaa' for o in by[d[288]]['orders'])
    assert 'USER_CONFIRMED_TEMPORARY' in j(294, 'aaa')['reason_codes'] and j(294, 'aaa')['main'] == 'REDUCE_REVIEW'
    assert j(292, 'ddd')['main'] == 'BLOCK' and 'USER_EXCLUDE' in j(292, 'ddd')['reason_codes']
    assert j(287, 'bbb')['aux'][-1] == 'EARNINGS_WINDOW' and 'ADDITIONAL_REVIEW' in [j(287, 'bbb')['main']] + j(287, 'bbb')['aux_levels']
    assert 'COVERAGE_WORSENED' in j(289, 'bbb')['reason_codes']
    assert j(291, 'bbb')['main'] == 'BLOCK'
    assert {c['cancel_reason'] for x in r['days'] for c in x['cancelled']} >= {'EXEC_PRICE_MISSING', 'EXEC_FX_MISSING'}
    assert r['summary']['user_flagged_count'] > 0 and r['summary']['realized_pnl'] != 0


def test_short_history_disables_v_signal_and_recheck():
    s = scenario('short_history_no_v_signal')
    r = vt.run_ledger(s['config'], s['ledger'])
    for day in r['days']:
        for jj in day['judgements'].values():
            assert 'RECHECK_BASIS_NOT_AVAILABLE' in jj['reason_codes'] and 'V_IMPROVED' not in jj['reason_codes']


def test_average_cost_is_not_a_decision_input():
    s = scenario('shadow_rules')
    a = vt.run_ledger(s['config'], s['ledger'])
    L = copy.deepcopy(s['ledger'])
    for p in L['initial']['positions'].values():
        p['cost'] *= 3
    b = vt.run_ledger(s['config'], L)
    strip = lambda r: [{k: x[k] for k in ('judgements', 'orders')} for x in r['days']]  # noqa: E731
    assert strip(a) == strip(b)


def test_shadow_without_target_and_invalid_inputs():
    assert vt.run_ledger(scenario('shadow_without_target')['config'], scenario('shadow_without_target')['ledger'])['reason_codes'] == ['TARGET_NOT_AVAILABLE']
    assert vt.run_ledger(scenario('invalid_input')['config'], scenario('invalid_input')['ledger'])['reason_codes'] == ['INPUT_INVALID']
    bad = vt.load_config() | {'buy_limit': -1}
    with pytest.raises(vt.VirtualTradingInputError):
        vt.run_ledger(bad, ref.base_ledger(n=5))


def test_hits_need_thirty_samples():
    s = scenario('set_a_deposit_buys')
    r = vt.run_ledger(s['config'], s['ledger'])
    h = {x['window']: x for x in vt.evaluate_hits(s['config'], s['ledger'], r['trades'])}
    assert h[63]['state'] == 'INSUFFICIENT_SAMPLE' and h[63]['hit_rate'] is None
    assert h[5]['samples'] >= 30 and h[5]['hit_rate'] == h[5]['hits'] / h[5]['samples']
