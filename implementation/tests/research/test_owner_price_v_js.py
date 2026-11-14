"""Synthetic owner-price wire tests; no network or real KIS/Sheet inputs.

Runtime execution requires Python + Node. Static review alone is not parity proof.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

import pytest

from test_personal_sheet_v_js import packet, row_projection, assert_numeric_contract

pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
IMPL = Path(__file__).resolve().parents[2]
ADAPTER = IMPL / 'src/investment_system/research/personal_sheet_v.js'
NODE = r"""
const fs = require('node:fs'), path = require('node:path');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
(async () => {
  try {
    let adapter, aliasesSame = null;
    if (request.browser) {
      const vm = require('node:vm');
      const scope = vm.createContext({
        QgvV2: require(path.join(path.dirname(process.argv[1]), '../product/web_assets/qgv-v2.js')),
        crypto: require('node:crypto').webcrypto, TextEncoder,
      });
      vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), scope);
      adapter = scope.OwnerPriceV;
      aliasesSame = adapter === scope.PersonalSheetV;
    } else adapter = require(process.argv[1]);
    const result = await adapter.calculate(request.text, request.pins);
    process.stdout.write(JSON.stringify({result, aliases_same: aliasesSame}));
  } catch (error) {
    process.stdout.write(JSON.stringify({error: error.code || error.message}));
  }
})();
"""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def call(p, *, text=None, pins=None, browser=False):
    text = encode(p) if text is None else text
    if pins is None:
        pins = dict(expected_payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
            expected_evaluation=deepcopy(p['evaluation_original']),
            expected_reference=deepcopy(p['reference_original']),
            expected_configuration_hash=p['configuration_hash'])
    run = subprocess.run(['node', '-e', NODE, str(ADAPTER)],
        input=encode(dict(text=text, pins=pins, browser=browser)),
        text=True, capture_output=True, check=False)
    assert run.returncode == 0, 'OWNER_V_NODE_EXECUTION_FAILED'
    return json.loads(run.stdout)


def owner_packet(provider='KIS'):
    p = packet(10)
    kis = provider == 'KIS'
    mode = 'EXPLICIT_EOD_ASOF' if kis else 'CURRENT'
    p.update(schema_version='owner-price-v-packet/1',
        namespace='OWNER_PRIVATE_KIS_V' if kis else 'PERSONAL_SHEET_V')
    p['context'] = dict(context_id='synthetic-owner-session', evaluation_day='2026-11-14',
        evaluated_at='2026-11-14T20:00:00Z', input_cutoff='2026-11-14T20:00:00Z',
        provider=provider, price_definition='KIS_DAILY_CLOSE' if kis else 'GOOGLEFINANCE_CURRENT',
        evaluation_mode=mode)
    p['availability_context'] = dict(evaluation_mode=mode, historical_pit_proven=False,
        reconstruction='ACTUAL_INPUT_CUTOFF_NOT_HISTORICAL_SYSTEM_HOLDINGS',
        official_top500_eligible=False, research_coverage_claim=False)
    return p


@pytest.mark.parametrize('provider', ['KIS', 'GOOGLEFINANCE'])
def test_owner_wire_preserves_scope_and_safe_row_disclosures(provider):
    p = owner_packet(provider)
    entry = p['evaluation'][0]
    entry.update(capitalization_basis='기간 가중평균 희석주식수 · 실제 종류별 시총 아님',
        price_metadata=dict(provider=provider, price_timestamp=None, time_status='DATE_ONLY',
            price_basis_date='2026-11-14', source_refs=['SYNTHETIC_OWNER_RECEIPT']),
        provenance=dict(source_refs=['SYNTHETIC_OWNER_BASIS'], source_kind='SYNTHETIC'))
    out = call(p)
    assert 'result' in out, out
    result = out['result']
    assert result['schema_version'] == 'owner-price-v-js-result/1'
    assert result['namespace'] == p['namespace']
    assert result['storage'] == 'EPHEMERAL_ONLY'
    assert not result['official'] and not result['research_coverage_claim'] and not result['filter_recalculates']
    assert result['availability_context'] == p['availability_context']
    assert len(result['rows']) == 10
    row = result['rows'][0]
    for key in ('capitalization_basis', 'price_metadata', 'provenance'):
        assert row[key] == entry[key]
    assert row['raw']['central::ebit_yield'] == pytest.approx(200 / 1030)
    assert row['roles']['v_earnings_yield']['decile'] == 1
    assert all('quote' not in r and 'company' not in r for r in result['rows'])


@pytest.mark.parametrize('change,error', [
    (('schema_version', 'personal-sheet-v-packet/1'), 'PERSONAL_PACKET_SCHEMA'),
    (('namespace', 'QGV_OFFICIAL'), 'OWNER_PACKET_SCOPE'),
    (('context.provider', 'GOOGLEFINANCE'), 'OWNER_PACKET_PROVIDER'),
    (('context.price_definition', 'GOOGLEFINANCE_CURRENT'), 'OWNER_PACKET_PROVIDER'),
    (('context.evaluation_mode', 'CURRENT'), 'OWNER_PACKET_PROVIDER'),
    (('availability_context.historical_pit_proven', True), 'OWNER_AVAILABILITY_CONTEXT'),
    (('availability_context.official_top500_eligible', True), 'OWNER_AVAILABILITY_CONTEXT'),
    (('availability_context.research_coverage_claim', True), 'OWNER_AVAILABILITY_CONTEXT'),
])
def test_owner_schema_namespace_provider_mode_and_claims_cannot_be_crossed(change,error):
    p = owner_packet()
    key, value = change
    if '.' in key:
        parent, child = key.split('.')
        p[parent][child] = value
    else:
        p[key] = value
    assert call(p) == dict(error=error)


def test_owner_context_requires_its_explicit_mode_without_tightening_legacy_context():
    p = owner_packet()
    del p['context']['evaluation_mode']
    assert call(p) == dict(error='OWNER_PACKET_CONTEXT')


def test_kis_cannot_be_relabelled_as_the_legacy_personal_wire():
    p = owner_packet()
    p.update(schema_version='personal-sheet-v-packet/1', namespace='PERSONAL_SHEET_V')
    assert call(p) == dict(error='PERSONAL_PACKET_PROVIDER')


@pytest.mark.parametrize('field', ['capitalization_basis', 'price_metadata', 'provenance'])
def test_owner_metadata_does_not_return_nested_quoted_price_values(field):
    p = owner_packet()
    p['evaluation'][0][field] = dict(source_refs=['SYNTHETIC'], nested=dict(price=10))
    assert call(p) == dict(error='OWNER_METADATA_PRICE_FIELD')


@pytest.mark.parametrize('provider', ['KIS', 'GOOGLEFINANCE'])
def test_browser_owner_alias_is_the_existing_personal_api_object(provider):
    out = call(owner_packet(provider), browser=True)
    assert 'result' in out, out
    assert out['aliases_same'] is True
    assert out['result']['schema_version'] == 'owner-price-v-js-result/1'


@pytest.mark.parametrize('n,model', [(7,'U1-555'),(8,'U1-555'),(10,'U1-555'),(23,'U1-555'),(10,'S1-555')])
def test_real_kis_owner_preparer_packet_matches_python_core_and_existing_js(n,model):
    from investment_system.research.personal_sheet_v import owner_result
    fixtures = runpy.run_path(str(IMPL / 'tools/owner_price_v_fixture.py'))
    prepared = fixtures['prepared'](fixtures['fixture'](n,model))
    wanted = owner_result(prepared)
    p = prepared['packet']
    pins = dict(expected_payload_sha256=prepared['payload_sha256'],
        expected_evaluation=p['evaluation_original'], expected_reference=p['reference_original'],
        expected_configuration_hash=p['configuration_hash'])
    response = call(p, text=prepared['packet_text'], pins=pins)
    assert 'result' in response, response
    actual = response['result']
    assert actual['namespace'] == 'OWNER_PRIVATE_KIS_V'
    assert actual['availability_context'] == p['availability_context']
    assert len(actual['rows']) == n
    assert_numeric_contract([row_projection(r) for r in actual['rows']],
                            [row_projection(r) for r in wanted['rows']])
    for observed, expected in zip(actual['rows'], wanted['rows']):
        assert observed['capitalization_basis'] == expected['capitalization_basis']
        assert observed['price_metadata'] == expected['price_metadata']
        if 'provenance' in expected:
            assert observed['provenance'] == expected['provenance']


def test_real_google_owner_wire_uses_personal_namespace_with_common_packet():
    from test_personal_sheet_v import fixture
    from investment_system.research.personal_sheet_v import prepare_owner, owner_result
    from investment_system.research.qgv_555 import identity
    req,e,ref,financial,prices = fixture(10)
    req.update(schema_version='owner-price-v-request/1', namespace='PERSONAL_SHEET_V')
    req['context']['evaluation_mode'] = 'CURRENT'
    prepared = prepare_owner(req,e,ref,financial,prices=prices,
        expected_evaluation=identity(e), expected_reference=identity(ref))
    wanted = owner_result(prepared)
    p = prepared['packet']
    pins = dict(expected_payload_sha256=prepared['payload_sha256'],
        expected_evaluation=p['evaluation_original'], expected_reference=p['reference_original'],
        expected_configuration_hash=p['configuration_hash'])
    response = call(p, text=prepared['packet_text'], pins=pins)
    assert 'result' in response, response
    actual = response['result']
    assert actual['namespace'] == 'PERSONAL_SHEET_V'
    assert_numeric_contract([row_projection(r) for r in actual['rows']],
                            [row_projection(r) for r in wanted['rows']])
