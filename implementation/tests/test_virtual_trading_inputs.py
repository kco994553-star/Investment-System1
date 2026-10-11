"""Virtual trading runner v1: Python reference of the device ledger-input assembly. SYNTHETIC inputs only."""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import virtual_trading as vt  # noqa: E402
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402
import virtual_trading_inputs_reference as ref  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/virtual_trading_inputs_v1.json'
RUNNER = ROOT / 'src/investment_system/product/web_assets/virtual-trading-runner.js'


def vectors():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))['vectors']


def vector(name):
    return next(v for v in vectors() if v['name'] == name)


def test_vectors_are_current_and_synthetic():
    out = subprocess.run([sys.executable, str(ROOT / 'tools/virtual_trading_inputs_reference.py'), '--check'],
                         capture_output=True, text=True).stdout.strip()
    assert out == 'VIRTUAL_TRADING_INPUTS_REFERENCE_OK'
    data = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert data['synthetic'] is True and data['note'].startswith('SYNTHETIC')


def test_python_assembly_reproduces_vectors():
    for v in vectors():
        assert vi.assemble(**copy.deepcopy(v['inputs'])) == v['expected'], v['name']


def test_js_assembly_equals_python():
    script = ('const R=require(process.argv[1]),fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));'
              'process.stdout.write(JSON.stringify(d.vectors.map(v=>[R.assemble(v.inputs),R.requiredSymbols(v.inputs)])))')
    out = json.loads(subprocess.run(['node', '-e', script, str(RUNNER), str(FIXTURE)], capture_output=True, text=True, check=True).stdout)
    for v, (assembled, symbols) in zip(vectors(), out):
        assert assembled == v['expected'], v['name']
        assert symbols == v['required_symbols'], v['name']


def test_engine_on_assembled_inputs_matches_vectors():
    cfg = vt.load_config()
    for v in vectors():
        for kind, expected in (v['expected_engine'] or {}).items():
            result = vt.run_ledger(cfg | {'start_date': v['inputs']['config']['start_date']}, v['expected']['ledgers'][kind]['input'])
            assert ref.project(result) == expected, (v['name'], kind)


def test_config_is_untouched_and_no_backfill_before_start():
    assert vt.load_config()['start_date'] == '2026-10-19'
    out = vector('full_synthetic')['expected']
    for kind in ('SET_A', 'SHADOW'):
        assert min(out['ledgers'][kind]['input']['sessions']) >= '2026-10-19'
    result = vt.run_ledger(vt.load_config(), out['ledgers']['SET_A']['input'])
    assert result['days'][0]['date'] == '2026-10-19'


def test_missing_values_stay_absent_never_zero():
    v = vector('full_synthetic')
    out = v['expected']['ledgers']['SET_A']['input']
    assert '2026-10-30' not in out['fx']['USD']
    for series in [out['fx']['USD'], out['fx']['JPY'], out['benchmarks']['SP500']] + [c['closes'] for c in out['companies'].values()]:
        assert all(x > 0 for x in series.values())
    nvda = out['companies']['nvda']['closes']
    assert '2026-10-30' not in nvda and '2026-10-29' in nvda  # IN_PROGRESS out, UNKNOWN past date in
    assert '2026-10-22' not in nvda  # null close is not filled
    amd = out['companies']['amd']['closes']
    assert '2026-10-30' not in amd and '2026-10-19' not in amd  # UNKNOWN on read day; duplicated local date dropped
    result = vt.run_ledger(vt.load_config(), out)
    assert ('asml', 'EXEC_FX_MISSING') in {(c['company'], c['cancel_reason']) for c in result['days'][-1]['cancelled']}


def test_rejected_symbols_degrade_with_codes():
    v = vector('spy_rejected')['expected']
    assert v['state'] == 'NOT_AVAILABLE' and v['reason_codes'] == ['SESSIONS_NOT_AVAILABLE']
    assert v['sources']['SPY'] == {'state': 'NOT_AVAILABLE', 'code': 'REQUEST_INVALID', 'sessions': 0}
    assert v['sources']['ASML']['state'] == 'NOT_REQUESTED'
    fx = vector('fx_rejected')['expected']
    assert fx['sources']['KRW=X']['code'] == 'REQUEST_INVALID' and fx['sources']['JPYKRW=X']['code'] == 'HISTORY_UNAVAILABLE'
    assert fx['ledgers']['SET_A']['input']['fx'] == {}
    assert fx['ledgers']['SHADOW'] == {'state': 'NOT_AVAILABLE', 'reason_codes': ['INITIAL_COST_FX_MISSING'], 'input': None}
    bad = vector('format_currency_missing')['expected']['sources']
    assert bad['MSFT']['code'] == 'CURRENCY_MISMATCH' and bad['GOOGL']['code'] == 'HISTORY_FORMAT_INVALID'
    assert bad['AMZN']['code'] == 'HISTORY_FORMAT_INVALID' and bad['RTX']['state'] == 'NOT_REQUESTED'


def test_snapshot_coverage_follows_engine_vocabulary():
    row = lambda state, q, g: {'state': state, 'Q': {'score': 1, 'coverage': q}, 'G': {'score': 1, 'coverage': g}}
    assert vi.coverage(row('LIVE', 'READY', 'READY')) == 'READY'
    assert vi.coverage(row('LIVE', 'PARTIAL', 'READY')) == 'PARTIAL'
    assert vi.coverage(row('STALE', 'READY', 'READY')) == 'PARTIAL'
    assert vi.coverage(row('LIVE', 'READY', 'BLOCKED')) == 'BLOCKED'
    assert vi.coverage(row('NOT_AVAILABLE', 'BLOCKED', 'BLOCKED')) == 'BLOCKED'
    snaps = vector('full_synthetic')['expected']['ledgers']['SET_A']['input']['snapshots']
    assert '2026-10-21' not in snaps  # NOT_AVAILABLE record: no snapshot, engine reports DATA_SNAPSHOT_MISSING
    assert all(set(r) == {'q', 'g', 'coverage'} for rows in snaps.values() for r in rows.values())


def test_set_b_and_shadow_rules():
    assert vector('full_synthetic')['expected']['ledgers']['SET_B']['reason_codes'] == ['SET_B_NOT_DEFINED']
    assert vector('set_b_invalid_before_start')['expected']['ledgers']['SET_B']['reason_codes'] == ['SET_B_INVALID']
    late = vector('set_b_and_late_shadow')['expected']['ledgers']['SHADOW']['input']
    assert late['sessions'] == [] and late['id'] == 'shadow-2026-11-02'
    assert vector('format_currency_missing')['expected']['ledgers']['SHADOW']['reason_codes'] == ['NO_ACTUAL']


def test_v_scores_are_only_stored_device_values():
    out = vector('full_synthetic')['expected']['ledgers']['SET_A']['input']['v_scores']
    assert out == {'2026-10-20': {'nvda': 55.5}, '2026-10-22': {'googl': 0, 'nvda': 61.0}}
    assert vi.v_scores_from_store(None) == {} and vi.v_scores_from_store({'2026-10-20': {}}) == {}
