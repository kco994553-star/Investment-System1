"""QGV 555 on the development engine route (owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49).

qgv555_context returns Main's SYNTHETIC proposal files exactly as written (the generator's output is checked byte for byte against
the generator), and qgv555_preview is refused with ENGINE_CONTRACT_PENDING for both 555 models: no 555 calculation exists, so no
answer of the reduced, 3/3/3 or sector default engine is ever given under a 555 name. Other requests are unchanged."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import sector_qgv_engine_bridge as bridge  # noqa: E402


def ask(b, **fields):
    return bridge.answer(b, json.dumps({'schema_version': bridge.REQUEST, 'request_id': 'T-555', **fields}))


@pytest.fixture()
def b():
    return bridge.Bridge(env={})


def test_context_serves_the_synthetic_files_as_written(b):
    out = ask(b, op='qgv555_context')
    assert out['ok'] is True and out['op'] == 'qgv555_context' and out['data_kind'] == 'SYNTHETIC'
    for key, name in bridge.QGV555_FILES.items():
        assert out[key] == json.loads((bridge.QGV555_FIXTURES / name).read_text('utf-8'))
    assert out['catalog']['schema_version'] == 'qgv-555-catalog/1'
    assert all(len(out['catalog']['roles'][a]) == 5 for a in 'QGV')
    assert out['population']['unit'] == 'ISSUER' and out['population']['n'] == 500


@pytest.mark.parametrize('model_id', bridge.QGV555_MODELS)
def test_preview_is_refused_until_the_engine_contract_exists(b, model_id):
    out = ask(b, op='qgv555_preview', model_id=model_id)
    assert out == {'schema_version': bridge.RESPONSE, 'op': 'qgv555_preview', 'request_id': 'T-555', 'ok': False,
                   'code': 'ENGINE_CONTRACT_PENDING'}


@pytest.mark.parametrize('model_id', [None, 'unified-333-eps/0.1.0', 'unified-roa-core/0.1.0', 'sector-qgv-default/0.1.0'])
def test_preview_of_another_model_is_refused_not_answered(b, model_id):
    out = ask(b, op='qgv555_preview', **({} if model_id is None else {'model_id': model_id}))
    assert out['ok'] is False and out['code'] == 'MODEL_UNKNOWN'


def test_the_synthetic_files_are_the_generators_output(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'make_qgv555_synthetic.py'), '--out', str(tmp_path)], check=True)
    for name in bridge.QGV555_FILES.values():
        assert (tmp_path / name).read_bytes() == (bridge.QGV555_FIXTURES / name).read_bytes()


def test_sector_default_requests_are_unchanged(b):
    out = ask(b, op='context')
    assert out['ok'] is True and 'default_config' in out
