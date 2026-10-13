"""Virtual trading signals v1: Python reference for D-5 basis labels, V history inputs and the rehearsal window."""
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
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402
from investment_system.qgv import virtual_trading_signals as vs  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/virtual_trading_signals_v1.json'
ASSETS = ROOT / 'src/investment_system/product/web_assets'


def data():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def vector(name):
    return next(v for v in data()['vectors'] if v['name'] == name)


def assembled_for(v):
    cfg = vt.load_config()
    run_cfg = vs.rehearsal_config(v['inputs']['histories'], cfg) if v['rehearsal'] else cfg
    out = vi.assemble(**(copy.deepcopy(v['inputs']) | {'config': {'start_date': run_cfg['start_date']}}))
    if v['rehearsal']:
        out, _ = vs.apply_rehearsal_snapshots(out, data()['qg_rows'], 'REHEARSAL')
    return out, run_cfg


def test_vectors_are_current_and_synthetic():
    out = subprocess.run([sys.executable, str(ROOT / 'tools/virtual_trading_signals_reference.py'), '--check'],
                         capture_output=True, text=True).stdout.strip()
    assert out == 'VIRTUAL_TRADING_SIGNALS_REFERENCE_OK'
    d = data()
    assert d['synthetic'] is True and d['note'].startswith('SYNTHETIC')


def test_d5_activation_with_realistic_length_inputs():
    v = vector('recording_d5_v_slope')
    out, cfg = assembled_for(v)
    L = out['ledgers']['SET_A']['input']
    basis = vs.basis_rows(L, cfg)
    assert basis['msft'] | {} == {'requested': 'XLK', 'benchmark': 'XLK', 'fallback': False, 'state': 'ABNORMAL', 'reason': None,
                                  'aligned': 326, 'needed': 273, 'v_slope': 'READY'}
    assert (basis['googl']['aligned'], basis['googl']['state']) == (273, 'NORMAL')
    assert (basis['nvda']['aligned'], basis['nvda']['reason'], basis['nvda']['v_slope']) == (272, 'HISTORY_INSUFFICIENT', 'BASIS_NOT_AVAILABLE')
    assert (basis['amzn']['requested'], basis['amzn']['benchmark'], basis['amzn']['fallback']) == ('XLY', 'SP500', True)
    last = vt.run_ledger(cfg, L)['days'][-1]['judgements']
    assert last['msft']['main'] == 'RISK_RECHECK' and 'RECHECK_ABNORMAL_DROP' in last['msft']['reason_codes']
    assert 'RECHECK_BASIS_NOT_AVAILABLE' in last['nvda']['reason_codes']
    assert 'V_IMPROVED' in last['googl']['reason_codes']
    # Ledger sessions start on 2026-10-19 (no backfill), the closes behind D-5 reach back the full 2y history.
    assert L['sessions'][0] == '2026-10-19' and min(L['companies']['msft']['closes']) < '2026-01-01'


def test_rehearsal_window_changes_only_start_date():
    v = vector('rehearsal_window_qg_fill')
    out, cfg = assembled_for(v)
    base = vt.load_config()
    assert {k: x for k, x in cfg.items() if k != 'start_date'} == {k: x for k, x in base.items() if k != 'start_date'}
    assert base['start_date'] == '2026-10-19'
    L = out['ledgers']['SET_A']['input']
    assert len(L['sessions']) == vs.REHEARSAL_WINDOW and L['sessions'][0] == cfg['start_date']
    assert L['initial'] == {'cash': 0, 'positions': {}}
    assert set(L['snapshots']) == set(L['sessions'])  # every unrecorded window session got today's public Q·G
    assert vs.rehearsal_start({'SPY': {'error': 'REQUEST_INVALID'}}) is None
    assert vs.rehearsal_snapshot({'nvda': {'q': 70, 'g': None, 'partial': True}, 'zzz': {'q': 1, 'g': 1}}) == {
        'nvda': {'q': 70, 'g': None, 'coverage': 'BLOCKED'}}


def test_recorded_snapshots_are_kept_in_rehearsal():
    assembled = {'state': 'READY', 'ledgers': {'SET_A': {'state': 'READY', 'reason_codes': [], 'input': {
        'sessions': ['2026-10-19', '2026-10-20'], 'snapshots': {'2026-10-19': {'msft': {'q': 1, 'g': 2, 'coverage': 'READY'}}}}}}}
    out, filled = vs.apply_rehearsal_snapshots(assembled, {'msft': {'q': 9, 'g': 9, 'partial': False}}, 'REHEARSAL')
    assert filled == ['2026-10-20']
    assert out['ledgers']['SET_A']['input']['snapshots']['2026-10-19']['msft']['q'] == 1


def test_v_scores_are_numbers_only_and_absent_when_missing():
    v = vector('recording_d5_v_slope')['expected']
    assert v['capture_date'] == '2026-11-30'
    assert all(isinstance(x, float) and 0 <= x <= 100 and round(x, 2) == x for x in v['v_scores'].values())
    assert 'asml' not in v['v_scores']  # no ASML close in the histories → no V, never 0
    assert vector('rehearsal_without_spy')['expected']['v_scores'] == {}
    assert vs.round2(13.4345) == 13.43 and vs.round2(0.125) == 0.13


def test_v_progress():
    assert vs.v_progress([], {}, 20)['state'] == 'NOT_RECORDED'
    p = vs.v_progress(['2026-10-19', '2026-10-20'], {'2026-10-19': {'msft': 1.0}}, 20)
    assert (p['state'], p['elapsed'], p['recorded']) == ('COLLECTING', 1, 1)
    assert vector('recording_d5_v_slope')['expected']['signals']['v_progress']['state'] == 'READY'


def test_js_equality_runs_in_node():
    out = subprocess.run(['node', '--test', str(ROOT / 'tools/virtual_trading_signals_node_test.js')], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]


def test_v_store_is_not_in_device_backup_and_assets_store_no_price():
    assert 'virtual-trading-v-scores' not in (ASSETS / 'device-backup.js').read_text(encoding='utf-8')
    src = (ASSETS / 'virtual-trading-v-history.js').read_text(encoding='utf-8')
    assert src.count('setItem(') == 2  # Separate, already-authorized v1/v2 private V-score stores.
    assert 'JSON.stringify({schema:SCHEMA,scores:m.scores,composition:m.composition})' in src
    assert 'JSON.stringify({schema:V2_SCHEMA,records})' in src


def test_rehearsal_fill_is_refused_outside_rehearsal_mode():
    """Decision 2026-10-11: today's public Q·G may fill missing days in a rehearsal only; recording never fills."""
    assembled = {'state': 'READY', 'ledgers': {'SET_A': {'state': 'READY', 'reason_codes': [], 'input': {
        'sessions': ['2026-10-19', '2026-10-20'], 'snapshots': {}}}}}
    for mode in ('RECORDING', None, 'rehearsal'):
        with pytest.raises(vs.RehearsalOnlyError, match='REHEARSAL_ONLY'):
            vs.apply_rehearsal_snapshots(assembled, {'msft': {'q': 9, 'g': 9, 'partial': False}}, mode)
    assert assembled['ledgers']['SET_A']['input']['snapshots'] == {}


def test_core_v_factor_missing_makes_v_na_never_zero():
    cases = {c['name']: c for c in data()['v_axis']}
    assert data()['core_v_factors'] == vs.core_v_factors() and len(vs.core_v_factors()) == 7
    for c in cases.values():
        assert vs.v_axis_detail(c['view']) == c['expected']
    # PLAYBOOK_V1 §13-1: >= 50 V weight present and an anchor factor -> renormalized partial V; otherwise NA.
    assert cases['core_factor_missing']['expected']['state'] == 'OK' and cases['core_factor_missing']['expected']['weight_percent'] == 90
    assert vs.v_axis(cases['anchors_missing']['view']) is None and vs.v_axis(cases['below_half_weight']['view']) is None
    assert cases['anchors_missing']['expected']['reason'] == 'V_CORE_FACTOR_MISSING'
    assert vs.V1_V_RULE['min_weight_percent'] == 50.0 and vs.V1_V_RULE['anchor_any'] == ('fundamental_value', 'reverse_dcf')
    assert cases['all_factors']['expected']['composition'] == '+'.join(vs.core_v_factors())


def test_v_slope_needs_equal_composition():
    v = vector('recording_v_composition_unknown')['expected']
    assert v['signals']['basis']['googl']['v_slope'] == 'V_COMPOSITION_CHANGED'
    assert 'V_IMPROVED' not in v['engine']['last']['googl']['reason_codes']
    assert 'V_COMPOSITION_CHANGED' in v['engine']['last']['googl']['aux']
    assert vector('recording_d5_v_slope')['expected']['signals']['basis']['googl']['v_slope'] == 'READY'
