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
from investment_system.producers.errors import MissingFieldError, ResearchStatusError, ValidationStatusError
from investment_system.product.web_mvp import STATES, validate_bundle

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


def test_fixture_publication_is_withheld_before_output(tmp_path):
    import pytest
    out, evidence = tmp_path / 'web', tmp_path / 'evidence'
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        fixture.build_fixture(out, evidence)
    assert not out.exists() and not evidence.exists()


def _function_body(name: str) -> str:
    m = re.search(r'\nfunction ' + name + r'\([^)]*\) \{\n(.*?)\n\}\n', APP, re.S)
    assert m, name
    return m.group(1)


def test_guard_is_applied_on_load_and_mirrors_both_halves_of_the_contract_rule():
    """Fails when the app.js guard is reverted or bypassed. Checks call sites and rule terms, not app.js bytes."""
    # Every assignment of the in-page view D goes through guardSections (data.json is never used as is).
    assigned = re.findall(r'(?<![\w$.])D\s*=(?!=)\s*([^;]*)', APP)
    assert assigned and all(a.startswith('guardSections(') for a in assigned), assigned
    assert 'D=guardSections(safeData)' in APP
    guard = _function_body('guardSections')
    for term in ('SECTION_NAMES', 'PUBLISHED_STATES.includes(s.state)', 'validationMarker(s)', 'researchMarker(s)',
                 'state:"NOT_AVAILABLE"', 'data:null'):
        assert term in guard, term
    # contract.py L197-202: validation status first, then methodology/research status.
    assert guard.index('validationMarker(s)') < guard.index('researchMarker(s)')
    validation = _function_body('validationMarker')
    assert 'producer?.validation?.status==="PASS"' in validation and '"producer" in s' in validation
    research = _function_body('researchMarker')
    assert 'producer?.methodology?.status' in research and 'RESEARCH_STATUSES.includes(' in research
    assert tuple(_js_list('VALIDATION_STATUSES')) == contract.VALIDATION_STATUSES


def test_validation_withheld_reason_is_localized():
    m = re.search(r'const VALIDATION_WITHHELD_REASON="([^"]+)";', APP)
    assert m
    locale = (ASSETS / 'locale.js').read_text(encoding='utf-8')
    assert f'"{m.group(1)}":{{"ko-KR":"{m.group(1)}","en-US":"Withheld: producer validation is not PASS."}}' in locale


@pytest.mark.parametrize('validation, accepted', [
    ({'status': 'PASS', 'checks': []}, True), ({'status': 'FAIL'}, False), ({'status': 'NOT_RUN'}, False),
    ({'status': 'pass'}, False), ({}, False), (None, False), ('PASS', False), ([], False)])
def test_published_validation_rule_is_status_pass_on_an_object(validation, accepted):
    """contract.py L194-199 for LIVE/FROZEN_SNAPSHOT reduces to `validation is an object and status == "PASS"`,
    which is what app.js checks at <section>.producer.validation.status (no case folding, no other value)."""
    for state in contract.PUBLISHED_STATES:
        snap = _snapshot('macro', state, 'VALIDATED')
        snap['validation'] = validation
        if accepted:
            validate_snapshot(snap)
        else:
            with pytest.raises(ValidationStatusError):
                validate_snapshot(snap)
        del snap['validation']
        with pytest.raises(MissingFieldError):
            validate_snapshot(snap)


def test_validation_variants_are_exactly_what_the_producer_contract_rejects():
    variants, expected = fixture.validation_variants(), fixture.manifest()['validation_withheld']
    assert set(variants) == set(expected) and len(expected) == 3
    sections = set()
    for file, bundle in variants.items():
        validate_bundle(bundle)  # the schema-1 validator accepts it: this is the gap the guard closes
        e = expected[file]
        section = bundle[e['section']]
        assert section['state'] == e['state'] in contract.PUBLISHED_STATES
        producer = section['producer']
        # Same section built as a producer snapshot: rejected for validation only, accepted once validation is PASS.
        snap = _snapshot(e['section'], section['state'], producer['methodology']['status'])
        if 'validation' in producer:
            snap['validation'] = producer['validation']
            assert e['status'] == producer['validation']['status'] in contract.VALIDATION_STATUSES
            with pytest.raises(ValidationStatusError):
                validate_snapshot(snap)
        else:
            del snap['validation']
            assert e['status'] is None
            with pytest.raises(MissingFieldError):
                validate_snapshot(snap)
        snap['validation'] = {'status': 'PASS', 'checks': []}
        validate_snapshot(snap)
        # Every other section of the variant is unchanged from the base fixture.
        base = fixture.fixture_bundle()
        assert {k: v for k, v in bundle.items() if k != e['section']} == {k: v for k, v in base.items() if k != e['section']}
        sections.add((e['section'], e['state'], e['status']))
    assert {s[1] for s in sections} == set(contract.PUBLISHED_STATES)
    assert {s[2] for s in sections} == {'FAIL', 'NOT_RUN', None}
