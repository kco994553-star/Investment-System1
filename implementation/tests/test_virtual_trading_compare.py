"""Set comparison metrics (decision 2026-10-11): Python reference on the shared SYNTHETIC vectors and JS parity."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import report_benchmarks as rb  # noqa: E402
from investment_system.qgv import virtual_trading_compare as vc  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/virtual_trading_compare_v1.json'
MODULE = ROOT / 'src/investment_system/product/web_assets/virtual-trading-compare.js'


def data():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_vectors_are_current_and_synthetic():
    out = subprocess.run([sys.executable, str(ROOT / 'tools/virtual_trading_compare_reference.py'), '--check'], capture_output=True, text=True).stdout.strip()
    assert out == 'VIRTUAL_TRADING_COMPARE_REFERENCE_OK'
    d = data()
    assert d['synthetic'] is True and d['note'].startswith('SYNTHETIC') and d['min'] == vc.MIN


def test_python_reproduces_vectors_and_js_equals_python():
    d = data()
    for v in d['vectors']:
        got = vc.metrics(days=v['days'], indices=v['indices'], basis=v['basis'], types=v['types'], hits=v['hits'], summary=v['summary'])
        assert json.loads(json.dumps(got)) == v['expected'], v['name']
    script = ("const C=require(process.argv[1]),d=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));"
              "process.stdout.write(JSON.stringify(d.vectors.map(v=>C.metrics({days:v.days,indices:v.indices,basis:v.basis,types:v.types,hits:v.hits,summary:v.summary}))))")
    js = json.loads(subprocess.run(['node', '-e', script, str(MODULE), str(FIXTURE)], capture_output=True, text=True, check=True).stdout)
    assert js == [v['expected'] for v in d['vectors']]


def test_minimum_samples_give_na_never_zero_and_returns_reuse_report_benchmarks():
    assert vc.MIN == {'capture_days': 20, 'max_drawdown': 20, 'volatility': 20}
    d = {v['name']: v for v in data()['vectors']}
    short = d['short_set_below_minimums']['expected']
    for k in ('volatility', 'max_drawdown', 'upside_capture', 'downside_capture'):
        assert short[k]['state'] == 'NOT_AVAILABLE' and short[k]['value'] is None and short[k]['reason'] == 'INSUFFICIENT_SAMPLE', k
        assert 0 <= short[k]['samples'] < 20
    v = d['gaps_in_spy_and_fx']
    days = [{'date': x['date'], 'total_value': x['total_value'], 'deposit': x['deposit']} for x in vc.compare_days(v['days'])]
    row = next(p for p in rb.build(indices=v['indices'], ledgers=[{'key': 'X', 'state': 'OK', 'reason_codes': [], 'days': days}], period='SINCE_START')['periods']
               if p['period'] == 'SINCE_START')
    assert v['expected']['period_return']['value'] == row['target']['return']
    assert v['expected']['excess_return']['value'] == row['excess']
    assert d['no_fx_series']['expected']['excess_return']['reason'] == 'FX_NOT_AVAILABLE'
    assert all(x['value'] is None for x in d['not_started']['expected'].values())


def test_fixture_has_no_holding_shaped_objects():
    sys.path.insert(0, str(ROOT / 'tools'))
    from autonomy_gate_a_guard import contains_device_actual
    assert not contains_device_actual(FIXTURE.read_bytes(), 'implementation/tests/fixtures/virtual_trading_compare_v1.json')
