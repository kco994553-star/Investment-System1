"""QGV 555 on the development engine route (owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49).

The route calls Codex #537 a22ce2a4 research.qgv_555 / qgv_555_preview / top500_selection unchanged on synthetic inputs (the
server resolves them): qgv555_context is Codex's catalog, recipes, default configurations and selectable_metrics(); qgv555_preview
is preview() of the before / after configuration, answered with its first preview_page() and the after result's replay record
(the whole preview stays on the route); qgv555_page / qgv555_detail / qgv555_role read that kept preview; qgv555_replay is Codex
replay(); qgv555_population is top500_view(select_top500()) on a synthetic job (no price, market cap or evidence). Other
requests are unchanged."""
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
from investment_system.research import qgv_555, qgv_555_preview  # noqa: E402

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
    assert out['selectable']['GENERAL']['q_profitability'] == qgv_555_preview.selectable_metrics('q_profitability', 'GENERAL')
    assert out['selectable']['BANK']['q_profitability'] == qgv_555_preview.selectable_metrics('q_profitability', 'BANK')


def test_preview_is_codex_preview_page_of_both_configs_on_the_same_input(b):
    base = qgv_555.configuration('U1-555')
    edited = copy.deepcopy(base)
    edited['axis_weights']['V'] = 66
    out = ask(b, op='qgv555_preview', model_id=U1, config=edited, before_config=base, input_id='SYNTHETIC_21')
    assert out['ok'] is True and out['model_id'] == U1
    page = out['page']
    assert page['schema_version'] == 'qgv-555-preview-page/1' and page['request_id'] == 'T-555'
    assert page['population_effect'] == 'NOT_EVALUATED' and page['row_count'] == 21 and len(page['rows']) == 20 and page['next_offset'] == 20
    e, ref = qgv_555.fixture()
    mine = qgv_555.run(edited, e, ref, calculated_at=page['after_calculated_at'])
    assert page['after_result_hash'] == mine['result_hash'] == out['saved']['result_hash']
    assert page['evaluation'] == qgv_555.identity(e) and page['reference'] == qgv_555.identity(ref)
    assert 'after_result' not in out and 'after_result' not in page and 'rows' not in out['saved']
    more = ask(b, op='qgv555_page', preview_id=out['preview_id'], offset=20)['page']
    assert more['source_preview_hash'] == page['source_preview_hash'] and len(more['rows']) == 1 and more['next_offset'] is None
    row = ask(b, op='qgv555_detail', preview_id=out['preview_id'], company_id=page['rows'][0]['company_id'])
    assert row['after_result_hash'] == page['after_result_hash'] and row['row']['company_id'] == page['rows'][0]['company_id']
    role = ask(b, op='qgv555_role', preview_id=out['preview_id'], role='q_profitability')
    assert role['n'] == 21 and set(role['rows'][0]) == {'company_id', 'decile', 'decile_status', 'rank', 'rank_n'}
    assert ask(b, op='qgv555_page', preview_id='0' * 64, offset=0)['code'] == 'PREVIEW_NOT_KEPT'
    assert ask(b, op='qgv555_role', preview_id=out['preview_id'], role='x_role')['code'] == 'ROLE_UNKNOWN'


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
    other = qgv_555.configuration('U1-555')
    other['axis_weights']['Q'] = 50
    s1 = ask(b, op='qgv555_preview', model_id=U1, config=other, before_config=qgv_555.configuration('S1-555'), input_id='SYNTHETIC_21')
    assert s1['ok'] is False and s1['code'] == 'MODEL_RESPONSE_MISMATCH'


def test_save_and_replay_reproduce_the_shown_preview(b):
    c = qgv_555.configuration('S1-555')
    c['scoped_role_overrides'] = {'ENERGY|GENERAL': {'q_profitability': dict(c['roles']['q_profitability'], weight=40)}}
    p = ask(b, op='qgv555_preview', model_id=S1, config=c, before_config=qgv_555.configuration('S1-555'), input_id='SYNTHETIC_21')
    assert p['ok'] is True
    saved = p['saved']
    assert saved['schema_version'] == 'qgv-555-saved/1' and saved['result_hash'] == p['page']['after_result_hash']
    assert set(saved) == {'schema_version', *bridge.QGV555_SAVED_KEYS} and 'rows' not in saved
    assert saved['configuration'] == c
    r = ask(b, op='qgv555_replay', saved=saved)
    assert r['ok'] is True and r['reproduced'] is True and r['result_hash'] == p['page']['after_result_hash']
    assert ask(b, op='qgv555_replay', saved={**saved, 'rows': []})['code'] == 'SAVED_INVALID'


def test_population_is_codex_top500_view(b):
    for kind, status in (('SYNTHETIC_COMPLETE', 'VALIDATED_RESEARCH_CANDIDATE'), ('SYNTHETIC_ROSTER_UNPROVEN', 'UNCONFIRMED_CANDIDATE')):
        out = ask(b, op='qgv555_population', input_id=kind)
        view = out['view']
        assert out['ok'] is True and view['schema_version'] == 'top500-view/1' and view['status'] == status
        assert view == qgv_555_preview.top500_view(bridge.select_top500(bridge._top500_job(kind)))
        assert view['official'] is False and view['public_publication_authorized'] is False
        text = json.dumps(out)
        for word in ('market_cap', 'price', 'shares', 'evidence'):
            assert word not in text
    assert ask(b, op='qgv555_population', input_id='REAL')['code'] == 'INPUT_UNKNOWN'


def test_sector_default_requests_are_unchanged(b):
    out = ask(b, op='context')
    assert out['ok'] is True and 'default_config' in out
