"""Render-time research guard (G3): app.js mirrors the producer contract; nothing else changes.

The browser behaviour is tested by tools/web_research_guard_browser_test.js on the fixture
built by tools/build_web_research_guard_fixture.py. These tests pin the mirror and the
presentation-only boundary without a browser.
"""
import importlib.util
import json
import re
from pathlib import Path

import pytest

from investment_system.producers import contract
from investment_system.producers.contract import make_snapshot, validate_snapshot
from investment_system.producers.errors import ResearchStatusError
from investment_system.product.web_mvp import STATES

IMPL = Path(__file__).resolve().parents[1]
ASSETS = IMPL / 'src/investment_system/product/web_assets'
APP = (ASSETS / 'app.js').read_text(encoding='utf-8')
_spec = importlib.util.spec_from_file_location('web_research_guard_fixture', IMPL / 'tools/build_web_research_guard_fixture.py')
fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixture)


def _js_list(name: str) -> list[str]:
    m = re.search(r'const ' + name + r'=Object\.freeze\(\[([^\]]*)\]\);', APP)
    assert m, name
    return json.loads('[' + m.group(1) + ']')


def test_app_guard_constants_mirror_producer_contract_exactly():
    assert _js_list('RESEARCH_STATUSES') == sorted(contract.RESEARCH_STATUSES)
    assert tuple(_js_list('PUBLISHED_STATES')) == contract.PUBLISHED_STATES
    assert tuple(_js_list('SECTION_NAMES')) == contract.SECTION_NAMES
    # The guard adds no data state; it only reuses NOT_AVAILABLE.
    assert set(contract.PUBLISHED_STATES) | {'NOT_AVAILABLE'} <= STATES
    assert 'DISPLAY_RESEARCH' not in APP


def test_withheld_reason_is_localized():
    m = re.search(r'const WITHHELD_REASON="([^"]+)";', APP)
    assert m
    locale = (ASSETS / 'locale.js').read_text(encoding='utf-8')
    assert f'"{m.group(1)}":{{"ko-KR":"{m.group(1)}","en-US":"Withheld: ' in locale


def _snapshot(section: str, state: str, status: str) -> dict:
    data = {'test_vector': True}
    return make_snapshot(producer_id='test.web_research_guard', producer_version='TEST_VECTOR_V1', section=section,
                         data_state=state, as_of=fixture.AS_OF, generated_at=fixture.AS_OF,
                         expires_at=fixture.EXPIRES if state == 'LIVE' else None,
                         methodology={'id': 'TEST_VECTOR', 'version': 'TEST_VECTOR_V1', 'status': status},
                         synthetic=False, provenance={'source': 'test', 'inputs': [{'artifact_id': 'test', 'sha256': '0' * 64}]},
                         validation={'status': 'PASS', 'checks': []}, data=data)


def test_fixture_methodology_markers_are_exactly_what_the_producer_contract_rejects():
    bundle, withheld = fixture.fixture_bundle(), fixture.manifest()['withheld']
    for name in contract.SECTION_NAMES:
        status = bundle[name].get('producer', {}).get('methodology', {}).get('status')
        if status is None:
            continue
        snap = _snapshot(name, bundle[name]['state'], status)
        if name in withheld:
            assert withheld[name] == f'producer.methodology.status: {status}'
            with pytest.raises(ResearchStatusError):
                validate_snapshot(snap)
        else:
            validate_snapshot(snap)
    # The research_state marker uses the same constant set, never a new status value.
    assert withheld['leaderboard'].split(': ')[1] in contract.RESEARCH_STATUSES
    # All five existing research statuses are exercised (universe RESEARCH runs in the browser test).
    used = {v.split(': ')[1] for v in withheld.values()} | {'RESEARCH'}
    assert used == set(contract.RESEARCH_STATUSES)


def test_fixture_build_is_presentation_only(tmp_path):
    out, evidence = tmp_path / 'web', tmp_path / 'evidence'
    m = fixture.build_fixture(out, evidence)
    served = json.loads((out / 'data.json').read_text(encoding='utf-8'))
    assert served == fixture.fixture_bundle()
    assert served['qgv']['state'] == 'LIVE' and served['qgv']['data']['nvda']['Q_score'] == 11.11
    assert (out / 'app.js').read_bytes() == (ASSETS / 'app.js').read_bytes()
    assert json.loads((evidence / 'fixture-manifest.json').read_text(encoding='utf-8')) == json.loads(json.dumps(m))
    assert m['research_display'] == m['frozen_grant'] == m['live_grant'] == 'NONE'
