"""qgv-official/1 JS reader parity (web_assets/qgv-official.js, PR-D, owner decision D8 (b)).

The vectors (tests/fixtures/qgv_official_vectors_v1.json) are regenerated from the Python validator by
tests/build_qgv_official_vectors.py; tools/qgv_official_node_test.js replays them through the JS reader. Synthetic only.
"""
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from investment_system.qgv import qgv_official as qo
from tests import build_qgv_official_vectors as REF

ROOT = Path(__file__).resolve().parents[1]
WA = ROOT / 'src/investment_system/product/web_assets'
FIXTURE = ROOT / 'tests/fixtures/qgv_official_vectors_v1.json'


@pytest.fixture(scope='module')
def vectors():
    return json.loads(FIXTURE.read_text())


def test_fixture_is_regenerated_from_the_python_validator():
    assert FIXTURE.read_text() == REF.render()


def test_fixture_is_synthetic_and_pins_the_valid_and_divergent_ids(vectors):
    assert vectors['synthetic'] is True and vectors['schema'] == 'qgv-official-vectors/1'
    text = FIXTURE.read_text()
    assert '4321.09' not in text                                                  # the publisher tests' price canary
    assert not re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}', text)    # nothing e-mail shaped
    base = qo.parse(vectors['base_text'].encode())
    assert base['times']['verified_at'] and len(base['rows']) == base['population']['row_count'] < 60
    assert len(vectors['base_text']) == vectors['base_canonical_length'] >= vectors['base_estimate_length']
    for key in ('python_sha256', 'js_sha256', 'publisher_sha256'):                # fixed synthetic hex, not source bytes
        assert base['engine'][key] == REF.hexof({'python_sha256': 'engine-python', 'js_sha256': 'engine-js', 'publisher_sha256': 'publisher'}[key])
    assert len(vectors['cases']) >= 120 and len(vectors['bodies']) >= 20
    assert [c['id'] for c in vectors['cases'] if c['valid']] == [
        'base_valid', 'cik_all_zero_valid', 'fiscal_year_end_calendar_free_valid', 'acquired_at_calendar_free_valid', 'clock_fraction_valid',
        'acquired_text_order_valid', 'acquired_both_null_valid', 'raw_price_code_in_flags_valid', 'raw_price_code_in_basis_valid',
        'raw_price_code_in_type_reason_valid', 'verified_at_null', 'verified_at_other_clock_valid', 'cross_section_flip_recounted_valid',
        'target_rank_row_valid_as_published', 'target_for_two_share_classes_valid', 'target_live_unplaced_valid',
        'target_calc_mismatch_valid', 'tie_dot_symbols_valid', 'stop_reason_skips_recompute_valid',
        'calc_mismatch_skips_recompute_valid', 'calc_version_later_day_valid', 'calc_version_same_day_n2_valid',
        'calc_version_leap_day_valid', 'last_trade_session_close_only_valid', 'last_trade_every_v_row_valid', 'last_trade_one_v_row_valid',
        'last_trade_early_close_valid', 'last_trade_winter_early_close_valid', 'last_trade_winter_regular_close_valid',
        'size_cap_at_canonical_length_valid']
    assert [(c['id'], c['js_stricter']) for c in vectors['cases'] if 'js_stricter' in c] == [('verified_at_null', 'OFFICIAL_INVALID')]
    assert [(b['id'], b['divergence']) for b in vectors['bodies'] if 'divergence' in b] == [('months_float_spelling', 'INT_FLOAT_SPELLING')]
    codes = {c['code'] for c in vectors['cases'] + vectors['bodies']}
    assert codes == {None, 'OFFICIAL_INVALID', 'OFFICIAL_FORBIDDEN_KEY', 'OFFICIAL_TOO_LARGE'}


def test_every_case_replays_in_python_from_its_ops(vectors):
    base = json.loads(vectors['base_text'])
    for case in vectors['cases']:
        assert REF.verdict(REF.apply(base, case['ops']), case.get('max_bytes')) == (case['valid'], case['code']), case['id']
    for body in vectors['bodies']:
        raw = REF.make_body(vectors['base_text'].encode(), body)
        assert REF.body_verdict(raw, body.get('max_bytes')) == (body['valid'], body['code']), body['id']


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_js_reader_reaches_every_python_verdict():
    result = subprocess.run(['node', str(ROOT / 'tools/qgv_official_node_test.js')], text=True, capture_output=True, timeout=300)
    assert result.returncode == 0 and 'fail=0' in result.stdout, result.stdout[-2000:]


def test_node_test_is_in_the_ci_manifest():
    names = [line.split('#', 1)[0].strip() for line in (ROOT / 'tools/ci_node_tests.txt').read_text().splitlines()]
    assert names.count('qgv_official_node_test.js') == 1


def test_index_loads_the_reader_once_after_its_dependencies_and_before_the_target_builder():
    html = (WA / 'index.html').read_text()
    scripts = re.findall(r'<script src="([^"]+)"></script>', html)
    assert scripts.count('qgv-official.js') == 1
    at = scripts.index('qgv-official.js')
    assert scripts.index('sec-qgv2.js') == at - 1 and scripts.index('target-v1-builder.js') > at
    for dep in ('qgv-v2.js', 'type-config-defaults.js', 'dcf-parameters-defaults.js'):
        assert scripts.index(dep) < at, dep
    assert 'forward-validation.js' in scripts                                       # bound lazily (use rule calendar)


def test_reader_and_index_are_pinned_in_the_pages_guard():
    spec = importlib.util.spec_from_file_location('qgv_vectors_guard', ROOT / 'tools/pages_artifact_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    for name in ('qgv-official.js', 'index.html'):
        assert guard.APPROVED_SHA256[name] == hashlib.sha256((WA / name).read_bytes()).hexdigest(), name
    assert (ROOT / 'tools/pages_artifact_guard.py').read_text().count('"qgv-official.js"') == 1
