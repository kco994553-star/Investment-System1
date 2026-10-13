"""S17 ⑪⑫⑬ report benchmarks: Python reference vs shared SYNTHETIC vectors, and JS == Python."""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.qgv import report_benchmarks as rb  # noqa: E402
from investment_system.qgv import virtual_trading as vt  # noqa: E402
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/report_benchmarks_v1.json'
ASSET = ROOT / 'src/investment_system/product/web_assets/report-benchmarks.js'


def data():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def _close(a, b, where):
    if isinstance(b, float) or (isinstance(b, int) and not isinstance(b, bool) and isinstance(a, float)):
        assert abs(a - b) <= 1e-12 * max(1, abs(b)), where
    elif isinstance(b, list):
        assert isinstance(a, list) and len(a) == len(b), where
        for i, (x, y) in enumerate(zip(a, b)):
            _close(x, y, f'{where}[{i}]')
    elif isinstance(b, dict):
        assert set(a) == set(b), where
        for k in b:
            _close(a[k], b[k], f'{where}.{k}')
    else:
        assert a == b, where


def test_vectors_are_current_and_synthetic():
    out = subprocess.run([sys.executable, str(ROOT / 'tools/report_benchmarks_reference.py'), '--check'], capture_output=True, text=True).stdout.strip()
    assert out == 'REPORT_BENCHMARKS_REFERENCE_OK'
    d = data()
    assert d['synthetic'] is True and d['note'].startswith('SYNTHETIC')


def test_python_reproduces_vectors():
    d = data()
    for v in d['build_vectors']:
        assert json.loads(json.dumps(rb.build(**copy.deepcopy(v['inputs'])))) == v['expected'], v['name']
    for v in d['track_vectors']:
        assert json.loads(json.dumps(rb.track_record(**copy.deepcopy(v['inputs'])))) == v['expected'], v['name']


def test_js_equals_python():
    script = ('const RB=require(process.argv[1]),fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));'
              'process.stdout.write(JSON.stringify([d.build_vectors.map(v=>RB.build(v.inputs)),d.track_vectors.map(v=>RB.trackRecord(v.inputs))]))')
    built, tracked = json.loads(subprocess.run(['node', '-e', script, str(ASSET), str(FIXTURE)], capture_output=True, text=True, check=True).stdout)
    d = data()
    for v, out in zip(d['build_vectors'], built):
        _close(out, v['expected'], v['name'])
    for v, out in zip(d['track_vectors'], tracked):
        _close(out, v['expected'], v['name'])


def test_gaps_are_never_filled():
    v = next(x for x in data()['build_vectors'] if x['name'] == 'usd_since_start')
    out = rb.build(**copy.deepcopy(v['inputs']))
    dash = out['dashboard']
    xlk = next(s for s in dash['series'] if s['key'] == 'XLK')
    i = dash['sessions'].index('2026-11-02')
    assert xlk['points'][i] is None and xlk['gap_codes'][i] == 'CLOSE_MISSING'
    set_a = next(s for s in dash['series'] if s['key'] == 'SET_A')
    j = dash['sessions'].index('2026-11-04')
    assert set_a['points'][j] is None and set_a['gap_codes'][j] == 'VALUE_MISSING'
    # USD basis: the missing KRW=X day is a ledger gap too (no previous rate).
    k = dash['sessions'].index('2026-11-11')
    assert set_a['points'][k] is None and set_a['gap_codes'][k] == 'FX_MISSING'


def test_missing_base_or_last_value_is_not_available():
    v = next(x for x in data()['build_vectors'] if x['name'] == 'last_values_missing')
    out = rb.build(**copy.deepcopy(v['inputs']))
    by = {s['key']: s for s in out['dashboard']['series']}
    assert by['SET_A']['state'] == 'NOT_AVAILABLE' and by['SET_A']['reason'] == 'LAST_VALUE_MISSING' and by['SET_A']['return'] is None
    assert by['XLK']['reason'] == 'LAST_CLOSE_MISSING'
    assert by['XLP']['reason'] == 'BASE_CLOSE_MISSING' and by['XLP']['points'] == []
    assert by['VUG']['reason'] == 'REQUEST_INVALID'


def test_ledger_index_equals_engine_twr_without_gaps():
    vec = json.loads((ROOT / 'tests/fixtures/virtual_trading_inputs_v1.json').read_text(encoding='utf-8'))['vectors']
    v = next(x for x in vec if x['name'] == 'full_synthetic')
    inp = v['expected']['ledgers']['SET_A']['input']
    res = vt.run_ledger(vt.load_config() | {'start_date': v['inputs']['config']['start_date']}, copy.deepcopy(inp))
    days = [{'date': d['date'], 'total_value': d['total_value'], 'deposit': d['deposit']} for d in res['days']]
    assert all(d['total_value'] is not None for d in days)
    out = rb.build(indices={'SPY': inp['benchmarks']['SP500']}, ledgers=[{'key': 'SET_A', 'state': 'OK', 'reason_codes': [], 'days': days}],
                   period='SINCE_START', basis='KRW')
    row = out['periods'][-1]
    assert abs(row['target']['return'] - res['summary']['twr']) < 1e-12


def test_track_record_minimum_and_expected_dates():
    cfg = vt.load_config()
    assert cfg['hit_windows'] == [5, 20, 63] and cfg['hit_min_samples'] == 30
    out = rb.track_record(hits=None, ledger_reasons=['BEFORE_START_DATE'], start_date=cfg['start_date'], windows=cfg['hit_windows'],
                          min_samples=cfg['hit_min_samples'])
    assert [(w['window'], w['expected_first'], w['expected_estimated']) for w in out['windows']] == [
        (5, '2026-10-27', True), (20, '2026-11-17', True), (63, '2027-01-21', True)]
    v = next(x for x in data()['track_vectors'] if x['name'] == 'enough_samples')
    rows = {w['window']: w for w in rb.track_record(**copy.deepcopy(v['inputs']))['windows']}
    assert rows[5]['state'] == 'OK' and rows[5]['hit_rate'] is not None
    assert rows[63]['state'] == 'INSUFFICIENT_SAMPLE' and rows[63]['hit_rate'] is None and 0 < rows[63]['samples'] < 30


def test_runner_requests_dashboard_etfs_and_passes_indices():
    vec = json.loads((ROOT / 'tests/fixtures/virtual_trading_inputs_v1.json').read_text(encoding='utf-8'))['vectors']
    for v in vec:
        symbols = v['required_symbols']
        if symbols:
            for etf in vi.DASHBOARD_ETFS:
                assert symbols.count(etf) == 1, (v['name'], etf)
        assert 'indices' in v['expected']
        assert set(v['expected']['indices']) <= {'SPY', 'KRW=X', *vi.DASHBOARD_ETFS}
