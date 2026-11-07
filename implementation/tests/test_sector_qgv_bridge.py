"""Main's development engine route of the sector QGV screen (tools/sector_qgv_engine_bridge.py, owner 2026-11-06).

The bridge must call Codex's common engine (#505) and add nothing: every answer equals the engine's own function on the same
arguments, the synthetic state inputs reproduce Codex's synthetic-states.json expectations, inputs are synthetic only, and
the answer of one request carries that request's id.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from investment_system.research import sector_qgv as engine

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'sector_qgv_engine_bridge.py'
FIX = ROOT / 'docs' / 'research' / 'sector_qgv'
spec = importlib.util.spec_from_file_location('sector_qgv_engine_bridge', TOOL)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def req(op, rid='t-1', **fields):
    return {'schema_version': bridge.REQUEST, 'op': op, 'request_id': rid, **fields}


def ask(b, r):
    return bridge.answer(b, json.dumps(r))


def test_context_is_the_engine_registry():
    out = ask(bridge.Bridge(), req('context'))
    assert out['ok'] and out['request_id'] == 't-1' and out['op'] == 'context'
    assert out['default_config'] == engine.default_config()
    assert out['versions'] == {'model_version': engine.MODEL, 'engine_version': engine.ENGINE,
                               'normalization_version': engine.NORMALIZATION, 'mapping_version': engine.MAPPING}
    assert [s['sector_id'] for s in out['sectors']] == list(engine.SECTORS)
    assert out['templates'] == list(engine.TEMPLATES)
    assert all(x['data_kind'] == 'SYNTHETIC' for x in out['inputs'])
    assert out['gate']['policy'] == 'official-q-percentile-required/1'


def test_view_equals_engine_preset_and_list_factors():
    c = engine.default_config()
    out = ask(bridge.Bridge(), req('view', config=c, sector_id='FINANCIALS', accounting_template='BANK'))
    assert out['ok'] and out['preset'] == engine.preset(c, 'FINANCIALS', 'BANK')
    assert out['factors'] == engine.list_factors(c, 'FINANCIALS', 'BANK')
    assert out['validation'] == engine.validate_config(c)
    # The published presets.json (Codex) is the same default: the screen has no second copy of it.
    presets = json.loads((FIX / 'presets.json').read_text())
    one = next(p for p in presets if p['sector_id'] == 'FINANCIALS' and p['accounting_template'] == 'BANK')
    assert out['default_preset'] == one


def test_view_reports_an_invalid_config_with_the_engine_code():
    c = engine.default_config()
    p = engine.preset(c, 'INFORMATION_TECHNOLOGY', 'GENERAL')
    p['axis_weights']['Q'] += 1
    c['scoped_overrides'] = {'INFORMATION_TECHNOLOGY|GENERAL': p}
    out = ask(bridge.Bridge(), req('view', config=c, sector_id='INFORMATION_TECHNOLOGY', accounting_template='GENERAL'))
    assert out['ok'] and out['validation'] == {'valid': False, 'code': 'WEIGHTS_MUST_SUM_10000'}
    assert out['preset'] == engine.preset(engine.default_config(), 'INFORMATION_TECHNOLOGY', 'GENERAL')


def test_preview_is_the_engine_preview_compare_and_save():
    c = engine.default_config()
    edited = copy.deepcopy(c)
    p = engine.preset(edited, 'INFORMATION_TECHNOLOGY', 'GENERAL')
    p['axis_weights'] = {'Q': 3400, 'G': 3300, 'V': 3300}
    edited['scoped_overrides'] = {'INFORMATION_TECHNOLOGY|GENERAL': p}
    out = ask(bridge.Bridge(), req('preview', 'p-1', config=edited, before_config=c, input_id='NORMAL'))
    snap = json.loads((FIX / 'synthetic-input.json').read_text())
    before = engine.preview_qgv(c, snap, 'p-1:before')
    after = engine.preview_qgv(edited, snap, 'p-1')
    assert out['ok'] and out['before'] == before and out['after'] == after
    assert out['comparison'] == engine.compare_previews(before, after, 'p-1')
    assert out['saved'] == engine.save_user_config(edited, after, request_id='p-1', expected_preview_id=after['preview_id'])
    assert out['data_kind'] == 'SYNTHETIC'
    # Codex's published synthetic preview is reproduced through the route (default config, request id synthetic-normal).
    again = ask(bridge.Bridge(), req('preview', 'synthetic-normal', config=c, before_config=c, input_id='NORMAL'))
    assert again['after'] == json.loads((FIX / 'synthetic-preview.json').read_text())


@pytest.mark.parametrize('state', [s for s in json.loads((FIX / 'synthetic-states.json').read_text()) if 'expected_total' in s or 'expected_error' in s],
                         ids=lambda s: s['case'])
def test_states_match_codex_synthetic_states(state):
    case = 'FAILED' if state['case'] == 'FAILED' else state['case']
    out = ask(bridge.Bridge(), req('preview', 's-1', config=engine.default_config(), before_config=engine.default_config(), input_id=case))
    if 'expected_error' in state:
        assert out == {'schema_version': bridge.RESPONSE, 'op': 'preview', 'request_id': 's-1', 'ok': False, 'code': state['expected_error']}
        return
    after = out['after']
    assert after['coverage']['total'] == state['expected_total']
    first = after['result_rows'][0] if after['result_rows'] else None
    assert (first['status'] if first else None) == state['expected_first_status']
    assert (next(iter(first['factors'].values()))['score_status'] if first else None) == state['expected_first_factor_status']


def test_three_gate_results_and_no_final_score_when_unknown():
    b = bridge.Bridge()
    rows = {k: ask(b, req('preview', 'g-' + k, config=engine.default_config(), before_config=engine.default_config(), input_id=k))['after']['result_rows'][0]
            for k in ('NORMAL', 'GATE_EXCLUDED', 'GATE_UNKNOWN')}
    assert rows['NORMAL']['gate_status'] == 'PASS' and rows['NORMAL']['total'] is not None
    ex = rows['GATE_EXCLUDED']
    assert ex['gate_status'] == 'VALUE_EXCLUDED' and ex['post_gate_axis_weights']['V'] == 0.0 and ex['total'] is not None
    un = rows['GATE_UNKNOWN']
    assert un['gate_status'] == 'UNKNOWN' and un['status'] == 'GATE_UNKNOWN' and un['total'] is None and un['rank'] is None


def test_save_needs_the_kept_preview_of_the_same_config():
    b = bridge.Bridge()
    c = engine.default_config()
    out = ask(b, req('preview', 'p-2', config=c, before_config=c, input_id='NORMAL'))
    pid = out['after']['preview_id']
    ok = ask(b, req('save', 's-2', config=c, preview_id=pid))
    assert ok['ok'] and ok['saved'] == out['saved']
    other = copy.deepcopy(c)
    p = engine.preset(other, 'ENERGY', 'GENERAL')
    p['axis_weights'] = {'Q': 3400, 'G': 3300, 'V': 3300}
    other['scoped_overrides'] = {'ENERGY|GENERAL': p}
    assert ask(b, req('save', 's-3', config=other, preview_id=pid))['code'] == 'PREVIEW_CONFIG_OR_REQUEST_MISMATCH'
    assert ask(b, req('save', 's-4', config=c, preview_id='0' * 64))['code'] == 'PREVIEW_NOT_FOUND'


def test_synthetic_only_and_fixed_codes():
    b = bridge.Bridge()
    assert ask(b, req('preview', config=engine.default_config(), before_config=engine.default_config(), input_id='/approved/private/job.json'))['code'] == 'INPUT_UNKNOWN'
    assert ask(b, req('preview', config=engine.default_config(), before_config=engine.default_config(), input_id='NORMAL', snapshot={'rows': []}))['ok']  # no such field: ignored
    assert ask(b, {'op': 'context', 'request_id': 'x'})['code'] == 'REQUEST_SCHEMA'
    assert ask(b, req('collect'))['code'] == 'OP_UNKNOWN'
    assert ask(b, req('context', 'bad id with spaces'))['code'] == 'REQUEST_ID_INVALID'
    assert bridge.answer(b, '{not json')['code'] == 'REQUEST_NOT_JSON'
    assert bridge.answer(b, 'x' * (bridge.MAX_REQUEST_BYTES + 1))['code'] == 'REQUEST_TOO_LARGE'
    assert ask(b, req('view', config=engine.default_config(), sector_id='SPACE', accounting_template='GENERAL'))['code'] == 'MAPPING_UNRESOLVED'


def test_stdio_one_answer_per_line_in_order_and_nothing_on_stderr():
    lines = [json.dumps(req('context', 'a-1')), '{bad', json.dumps(req('view', 'a-2', config=engine.default_config(),
             sector_id='UTILITIES', accounting_template='GENERAL'))]
    run = subprocess.run([sys.executable, str(TOOL)], input='\n'.join(lines) + '\n', capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and run.stderr == ''
    out = [json.loads(x) for x in run.stdout.splitlines()]
    assert [x['request_id'] for x in out] == ['a-1', None, 'a-2'] and [x['ok'] for x in out] == [True, False, True]
