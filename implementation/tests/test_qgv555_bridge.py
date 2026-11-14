"""QGV 555 on the development engine route (owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49).

The route calls Codex #537 research.qgv_555 / top500_selection unchanged on synthetic inputs: qgv555_context is Codex's catalog,
recipes and default configurations; qgv555_preview is run() of the edited and the before configuration on the same fixture pair
(both answers as Codex returns them, model id checked); the preview carries the after result's replay record; qgv555_replay is
Codex replay(); qgv555_population is select_top500() on a synthetic job, projected to its public fields (no price, market cap or
evidence). Other requests are unchanged."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import sector_qgv_engine_bridge as bridge  # noqa: E402
from investment_system.research import qgv_555  # noqa: E402

U1, S1 = 'unified-555/0.1.0', 'sector-555/0.1.0'


def ask(b, **fields):
    return bridge.answer(b, json.dumps({'schema_version': bridge.REQUEST, 'request_id': 'T-555', **fields}))


@pytest.fixture()
def b():
    return bridge.Bridge(env={})


def test_context_is_codex_contract(b):
    out = ask(b, op='qgv555_context')
    assert out['ok'] is True and out['data_kind'] == 'SYNTHETIC'
    assert out['catalog'] == json.loads(json.dumps(qgv_555.catalog()))
    assert out['configs'] == {k: qgv_555.configuration(k) for k in ('U1-555', 'S1-555')}
    assert out['recipes'] == json.loads(json.dumps(qgv_555.accounting_recipes()))


def test_preview_is_codex_run_of_both_configs_on_the_same_input(b):
    base = qgv_555.configuration('U1-555')
    edited = copy.deepcopy(base)
    edited['axis_weights']['V'] = 66
    out = ask(b, op='qgv555_preview', model_id=U1, config=edited, before_config=base, input_id='SYNTHETIC_21')
    assert out['ok'] is True and out['model_id'] == U1
    e, ref = qgv_555.fixture()
    for key, c in (('before', base), ('after', edited)):
        mine = qgv_555.run(c, e, ref, calculated_at=out[key]['calculated_at'])
        assert out[key]['result_hash'] == mine['result_hash']
    assert out['before']['evaluation'] == out['after']['evaluation']
    assert out['preview_id'] == out['after']['result_hash']


@pytest.mark.parametrize('model_id', [None, 'unified-333-eps/0.1.0', 'unified-roa-core/0.1.0', 'sector-qgv-default/0.1.0'])
def test_other_models_are_refused(b, model_id):
    base = qgv_555.configuration('U1-555')
    out = ask(b, op='qgv555_preview', config=base, before_config=base, input_id='SYNTHETIC_21', **({} if model_id is None else {'model_id': model_id}))
    assert out['ok'] is False and out['code'] == 'MODEL_UNKNOWN'


def test_config_of_another_model_is_refused(b):
    out = ask(b, op='qgv555_preview', model_id=S1, config=qgv_555.configuration('U1-555'),
              before_config=qgv_555.configuration('S1-555'), input_id='SYNTHETIC_21')
    assert out['ok'] is False and out['code'] == 'MODEL_RESPONSE_MISMATCH'


def test_engine_refusal_is_passed_as_a_code(b):
    c = qgv_555.configuration('U1-555')
    c['roles']['v_earnings_yield']['metrics']['EV_EBIT_TTM'] = 1
    out = ask(b, op='qgv555_preview', model_id=U1, config=c, before_config=qgv_555.configuration('U1-555'), input_id='SYNTHETIC_21')
    assert out['ok'] is False and out['code'] == 'DUPLICATE_CANONICAL_METRIC'


def test_save_and_replay_reproduce_the_shown_preview(b):
    c = qgv_555.configuration('S1-555')
    c['scoped_role_overrides'] = {'ENERGY|GENERAL': {'q_profitability': dict(c['roles']['q_profitability'], weight=40)}}
    p = ask(b, op='qgv555_preview', model_id=S1, config=c, before_config=qgv_555.configuration('S1-555'), input_id='SYNTHETIC_21')
    assert p['ok'] is True
    saved = p['saved']
    assert saved['schema_version'] == 'qgv-555-saved/1' and saved['result_hash'] == p['after']['result_hash']
    assert set(saved) == {'schema_version', *bridge.QGV555_SAVED_KEYS} and 'rows' not in saved
    assert saved == {'schema_version': 'qgv-555-saved/1', **{k: p['after'][k] for k in bridge.QGV555_SAVED_KEYS}}
    r = ask(b, op='qgv555_replay', saved=saved)
    assert r['ok'] is True and r['reproduced'] is True and r['result_hash'] == p['after']['result_hash']
    assert ask(b, op='qgv555_replay', saved={**saved, 'rows': []})['code'] == 'SAVED_INVALID'


def test_population_is_public_view_only(b):
    for kind, status in (('SYNTHETIC_COMPLETE', 'VALIDATED_RESEARCH_CANDIDATE'), ('SYNTHETIC_ROSTER_UNPROVEN', 'UNCONFIRMED_CANDIDATE')):
        out = ask(b, op='qgv555_population', input_id=kind)
        sel = out['selection']
        assert out['ok'] is True and sel['status'] == status and sel['official'] is False and sel['replace_official'] is False
        text = json.dumps(out)
        for word in ('market_cap', 'price', 'shares', 'evidence'):
            assert word not in text
        assert [m['selection_rank'] for m in sel['members']] == list(range(1, len(sel['members']) + 1))
    assert ask(b, op='qgv555_population', input_id='REAL')['code'] == 'INPUT_UNKNOWN'


def test_sector_default_requests_are_unchanged(b):
    out = ask(b, op='context')
    assert out['ok'] is True and 'default_config' in out
