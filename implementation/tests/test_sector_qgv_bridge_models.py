"""Research model requests on the development engine route (owner 2026-11-11 「QGV 후속 연결」 §1, Codex #437 6792797898 반례).

A request with `model` is answered by Codex #529 research.dual_qgv, never by the sector default engine: the candidate is named
explicitly (INTEGRATED → U1 / U2, SECTOR → S1), unknown or missing names are refused, the answer names the same model and
model_id, preview is run_board on two inputs, save / replay are save_board / replay_board on the retained original inputs, and a
request without `model` keeps the sector default answer byte for byte."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import sector_qgv_engine_bridge as bridge  # noqa: E402
from investment_system.research import dual_qgv  # noqa: E402

U1, U2, S1 = 'unified-roa-core/0.1.0', 'unified-sales-core/0.1.0', 'sector-reduced-core/0.1.0'


def ask(b, **fields):
    return bridge.answer(b, json.dumps({'schema_version': bridge.REQUEST, 'request_id': 'T-1', **fields}))


@pytest.fixture()
def b():
    return bridge.Bridge(env={})


def test_codex_counterexample_is_no_longer_the_sector_answer(b):
    # 6792797898: op=context, model=INTEGRATED returned the sector default context unchanged.
    a = ask(b, op='context', model='INTEGRATED')
    assert a['ok'] is False and a['code'] == 'MODEL_ID_REQUIRED'
    legacy = ask(b, op='context')
    assert legacy['ok'] is True and legacy['versions']['model_version'] == 'sector-qgv-default/0.1.0' and 'model' not in legacy


@pytest.mark.parametrize('fields, code', [
    ({'model': 'INTEGRATED'}, 'MODEL_ID_REQUIRED'),
    ({'model': 'SECTOR'}, 'MODEL_ID_REQUIRED'),
    ({'model': 'INTEGRATED', 'model_id': S1}, 'MODEL_ID_UNKNOWN'),
    ({'model': 'SECTOR', 'model_id': U1}, 'MODEL_ID_UNKNOWN'),
    ({'model': 'OFFICIAL', 'model_id': U1}, 'MODEL_UNKNOWN'),
    ({'model_id': U1}, 'MODEL_UNKNOWN'),
    ({'model': 'INTEGRATED', 'model_id': 'unified-roa-core/0.2.0'}, 'MODEL_ID_UNKNOWN'),
])
def test_unknown_or_unnamed_models_are_refused_never_replaced(b, fields, code):
    for op in ('context', 'view', 'preview'):
        a = ask(b, op=op, **fields)
        assert a['ok'] is False and a['code'] == code, (op, fields)


def test_ops_the_research_route_does_not_have_are_refused(b):
    for op in ('comparisons', 'comparison'):
        assert ask(b, op=op, model='SECTOR', model_id=S1)['code'] == 'MODEL_OP_UNSUPPORTED'


@pytest.mark.parametrize('model, model_id, key', [('INTEGRATED', U1, 'U1'), ('INTEGRATED', U2, 'U2'), ('SECTOR', S1, 'S1')])
def test_context_names_the_requested_candidate_from_codex(b, model, model_id, key):
    a = ask(b, op='context', model=model, model_id=model_id)
    cfg = dual_qgv.candidate_configs()[key]
    assert a['ok'] and a['model'] == model and a['model_id'] == model_id and a['candidate'] == key
    assert a['versions']['model_id'] == model_id and a['config'] == json.loads(json.dumps(cfg)) and a['config_hash'] == dual_qgv.digest(cfg)
    assert a['evidence'] == json.loads(json.dumps(dual_qgv.evidence_catalog()))


def test_a_config_other_than_the_candidate_is_refused(b):
    cfg = json.loads(json.dumps(dual_qgv.candidate_configs()['U1']))
    cfg['uniform_preset']['axis_weights']['Q'] = 2
    assert ask(b, op='preview', model='INTEGRATED', model_id=U1, input_id='DUAL_BOTH_VALID', config=cfg)['code'] == 'CONFIG_NOT_CANDIDATE'


def test_view_common_preset_and_sector_scope(b):
    u = ask(b, op='view', model='INTEGRATED', model_id=U2)
    assert u['ok'] and u['kind'] == 'COMMON' and u['preset']['axes']['G'] == json.loads(json.dumps(dual_qgv.candidate_configs()['U2']['uniform_preset']['axes']['G']))
    s = ask(b, op='view', model='SECTOR', model_id=S1, sector_id='FINANCIALS', accounting_template='BANK')
    assert s['ok'] and s['kind'] == 'SECTOR' and s['sector_id'] == 'FINANCIALS'
    assert ask(b, op='view', model='SECTOR', model_id=S1)['code'] == 'MAPPING_UNRESOLVED'


@pytest.mark.parametrize('model, model_id, key', [('INTEGRATED', U1, 'U1'), ('INTEGRATED', U2, 'U2'), ('SECTOR', S1, 'S1')])
def test_preview_is_run_board_on_two_inputs_and_equals_codex_synthetic_delivery(b, model, model_id, key):
    a = ask(b, op='preview', model=model, model_id=model_id, input_id='DUAL_BOTH_VALID')
    assert a['ok'] and a['kind'] == 'SYNTHETIC_RECALCULATION' and a['board']['model_id'] == model_id
    delivered = json.loads((ROOT / 'docs/research/sector_qgv/dual-synthetic/summary.json').read_text())['boards'][key]
    # The retained synthetic board was made at #529's code. The recalculation binds the same configuration and both input identities,
    # and every row's axes, total, rank and status are the retained ones; its code binding is the current code's, and the result hash
    # moves exactly with it (#534 changed dual_qgv.py for config/2; an exact old replay is at its original commit, QGV_333.md).
    bd = a['board']
    for k in ('model_hash', 'evaluation', 'reference', 'engine_version', 'adapter_version'):
        assert bd['bindings'][k] == delivered['bindings'][k], k
    assert (bd['result_hash'] == delivered['result_hash']) == (bd['bindings']['code_hash'] == delivered['bindings']['code_hash'])
    index = {r['company_id']: r['boards'][key] for r in json.loads((ROOT / 'docs/research/sector_qgv/dual-synthetic/index.json').read_text())['rows']}
    assert len(bd['rows']) == len(index)
    for r in bd['rows']:
        for k in ('axes', 'total', 'rank', 'rank_n', 'ranking_scope', 'status', 'gate_status'):
            assert r[k] == index[r['company_id']][k], r['company_id'] + '.' + k
    ev, ref = a['board']['evaluation_population'], a['board']['reference_population']
    assert ev['code_rows'] == 3 and ref['issuers'] == 20 and ev['id'] != ref['id'], 'two populations, never one input'


def test_q_g_only_keeps_q_g_and_has_no_total_or_rank(b):
    a = ask(b, op='preview', model='SECTOR', model_id=S1, input_id='DUAL_QG_ONLY')
    rows = a['board']['rows']
    assert a['ok'] and all(r['axes']['Q'] is not None and r['axes']['G'] is not None for r in rows)
    assert all(r['axes']['V'] is None and r['total'] is None and r['rank'] is None for r in rows), 'no total from Q+G, no total rank'
    assert ask(b, op='preview', model='SECTOR', model_id=S1, input_id='NORMAL')['code'] == 'INPUT_UNKNOWN', 'no sector input under a research model'


def test_save_and_exact_replay_use_the_retained_original_inputs(b):
    p = ask(b, op='preview', model='INTEGRATED', model_id=U1, input_id='DUAL_BOTH_VALID')
    h = p['board']['result_hash']
    s = ask(b, op='save', model='INTEGRATED', model_id=U1, result_hash=h)
    assert s['ok'] and s['saved']['schema_version'] == 'qgv-dual-saved/1' and s['saved']['result_hash'] == h
    r = ask(b, op='replay', model='INTEGRATED', model_id=U1, saved=s['saved'])
    assert r['ok'] and r['kind'] == 'EXACT_REPLAY' and r['board']['result_hash'] == h and r['retained_result_hash'] == h
    # another candidate's name, a sector record, an unknown result and a save under another model are refused
    assert ask(b, op='replay', model='INTEGRATED', model_id=U2, saved=s['saved'])['code'] == 'MODEL_RESPONSE_MISMATCH'
    assert ask(b, op='replay', model='INTEGRATED', model_id=U1, saved={'schema_version': 'sector-qgv-saved/1'})['code'] == 'SAVED_SCHEMA_MISMATCH'
    assert ask(b, op='save', model='INTEGRATED', model_id=U2, result_hash=h)['code'] == 'MODEL_RESPONSE_MISMATCH'
    assert ask(b, op='save', model='INTEGRATED', model_id=U1, result_hash='0' * 64)['code'] == 'PREVIEW_NOT_FOUND'
    assert r['input_source'] == 'RETAINED_IN_PROCESS'
    # owner 2026-11-13 「재시작 후 저장·복원」: a fresh process (restart / memory dropped) reads the pinned inputs again from their
    # fixed manifest and replays exactly on the pair the saved bindings name; the Q/G-only input is never taken for it.
    f = ask(bridge.Bridge(env={}), op='replay', model='INTEGRATED', model_id=U1, saved=s['saved'])
    assert f['ok'] and f['kind'] == 'EXACT_REPLAY' and f['input_source'] == 'PINNED_INPUT_REREAD' and f['input_id'] == 'DUAL_BOTH_VALID'
    assert f['board']['result_hash'] == h and f['retained_result_hash'] == h
    q = ask(b, op='preview', model='SECTOR', model_id=S1, input_id='DUAL_QG_ONLY')
    sq = ask(b, op='save', model='SECTOR', model_id=S1, result_hash=q['board']['result_hash'])['saved']
    fq = ask(bridge.Bridge(env={}), op='replay', model='SECTOR', model_id=S1, saved=sq)
    assert fq['ok'] and fq['input_id'] == 'DUAL_QG_ONLY' and fq['board']['result_hash'] == q['board']['result_hash']
    # a record whose original input is not pinned here: kept by the caller, never "exact" on the latest input
    lost = json.loads(json.dumps(s['saved'])); lost['bindings']['evaluation']['input_hash'] = 'e' * 64
    assert ask(bridge.Bridge(env={}), op='replay', model='INTEGRATED', model_id=U1, saved=lost)['code'] == 'RETAINED_INPUT_NOT_FOUND'


def test_a_changed_saved_record_is_refused_by_codex_replay(b):
    p = ask(b, op='preview', model='INTEGRATED', model_id=U1, input_id='DUAL_BOTH_VALID')
    s = ask(b, op='save', model='INTEGRATED', model_id=U1, result_hash=p['board']['result_hash'])['saved']
    s['bindings']['code_hash'] = 'f' * 64
    a = ask(b, op='replay', model='INTEGRATED', model_id=U1, saved=s)
    assert a['ok'] is False and a['code'] == 'DUAL_REPLAY_INPUT_MISMATCH'


def test_sector_default_requests_are_unchanged(b):
    a = ask(b, op='view', sector_id='INFORMATION_TECHNOLOGY', accounting_template='GENERAL', config=bridge.engine.default_config())
    assert a['ok'] and 'model' not in a and 'model_id' not in a
