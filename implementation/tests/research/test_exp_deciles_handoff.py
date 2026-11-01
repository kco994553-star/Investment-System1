"""Input / output manifests: hash refusal, run_id, generated_at, output verification. Synthetic bytes only."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json

import pytest

from investment_system.research.exp_deciles import handoff, ledger, metrics, settings


def resource(name, data, path=None):
    return {'name': name, 'path': path or name.replace(':', '_') + '.json', 'sha256': hashlib.sha256(data).hexdigest(),
            'source': 'synthetic', 'period': '2018', 'rights_note': 'synthetic test data'}


def manifest_bytes(resources, **override):
    body = {'schema': handoff.INPUT_MANIFEST_SCHEMA, 'experiment_id': settings.EXPERIMENT_ID, 'resources': resources}
    body.update(override)
    return json.dumps(body).encode()


def test_input_manifest_is_parsed_strictly_and_hashed():
    data = manifest_bytes([resource('records:2018', b'[]'), resource('companyfacts:320', b'{}'),
                           resource('filings', b'[]'), resource('tr_series', b'{}')])
    parsed = handoff.parse_input_manifest(data)
    assert parsed['sha256'] == hashlib.sha256(data).hexdigest()
    assert [r['name'] for r in handoff.resources_of(parsed, 'records', '2018')] == ['records:2018']
    assert handoff.resource_kind('companyfacts:320') == ('companyfacts', '320')
    refusals = {
        'MANIFEST_EXPERIMENT_MISMATCH': manifest_bytes([resource('filings', b'[]')], experiment_id='OTHER'),
        'MANIFEST_SCHEMA_INVALID': manifest_bytes([resource('filings', b'[]')], schema='x/1'),
        'MANIFEST_RESOURCE_NAME_INVALID': manifest_bytes([resource('records', b'[]')]),       # records need a year
        'MANIFEST_RESOURCE_DUPLICATE': manifest_bytes([resource('filings', b'[]'), resource('filings', b'[1]')]),
        'MANIFEST_SHA256_INVALID': manifest_bytes([dict(resource('filings', b'[]'), sha256='ABC')]),
        'MANIFEST_RIGHTS_NOTE_INVALID': manifest_bytes([dict(resource('filings', b'[]'), rights_note=' ')]),
        'MANIFEST_RESOURCE_KEYS_INVALID': manifest_bytes([dict(resource('filings', b'[]'), extra=1)]),
        'MANIFEST_NOT_JSON': b'{not json',
    }
    for code, raw in refusals.items():
        with pytest.raises(handoff.HandoffError, match=code):
            handoff.parse_input_manifest(raw)
    with pytest.raises(handoff.HandoffError, match='MANIFEST_RESOURCE_NAME_INVALID'):
        handoff.resource_kind('tr_series:extra')


def test_resource_bytes_with_another_hash_are_refused():
    item = resource('prices', b'[{"a": 1}]')
    handoff.verify_resource(item, b'[{"a": 1}]')
    with pytest.raises(handoff.HandoffError, match='MANIFEST_HASH_MISMATCH'):
        handoff.verify_resource(item, b'[{"a": 2}]')


def test_run_id_covers_identity_code_inputs_and_stage_but_not_the_clock():
    base = dict(experiment_id=settings.EXPERIMENT_ID, settings_sha256='a' * 64, code_sha='b' * 40,
                input_manifest_sha256='c' * 64, stage={'name': 'select', 'year': 2018, 'previous_u_a_sha256': None})
    rid = handoff.run_id(**base)
    assert len(rid) == 24 and int(rid, 16) >= 0
    body = handoff.canonical_bytes({k: base[k] for k in ('experiment_id', 'settings_sha256', 'code_sha',
                                                         'input_manifest_sha256', 'stage')})
    assert rid == hashlib.sha256(body).hexdigest()[:24]
    for key, value in (('code_sha', 'd' * 40), ('input_manifest_sha256', 'e' * 64), ('settings_sha256', 'f' * 64),
                       ('stage', {'name': 'select', 'year': 2019, 'previous_u_a_sha256': None})):
        assert handoff.run_id(**dict(base, **{key: value})) != rid
    with pytest.raises(handoff.HandoffError, match='STAGE_INVALID'):
        handoff.run_id(**dict(base, stage={'name': 'publish'}))


def test_code_sha_unknown_is_flagged_and_generated_at_is_utc_seconds():
    assert handoff.code_sha_record('0123456789abcdef0123456789abcdef01234567') == (
        '0123456789abcdef0123456789abcdef01234567', [])
    assert handoff.code_sha_record(None) == ('UNKNOWN', ['CODE_SHA_UNKNOWN'])
    assert handoff.code_sha_record('main') == ('UNKNOWN', ['CODE_SHA_UNKNOWN'])
    assert handoff.generated_at_text('2026-11-01T09:30:15.987+09:00') == '2026-11-01T00:30:15Z'
    assert handoff.generated_at_text(datetime(2026, 11, 1, 1, 2, 3, tzinfo=timezone(timedelta(hours=-5)))) == \
        '2026-11-01T06:02:03Z'
    for bad in ('2026-11-01T00:00:00', 'yesterday', datetime(2026, 11, 1)):
        with pytest.raises(handoff.HandoffError, match='GENERATED_AT_INVALID'):
            handoff.generated_at_text(bad)


def test_jsonable_and_canonical_bytes_are_deterministic():
    value = {'b': Decimal('1.50'), 'a': (date(2018, 2, 16), {3: 'x'}), 'm': metrics.Metric(None, 'NO_FILL'),
             'f': ledger.Fill(date(2018, 2, 20), 'X', Decimal('2'), Decimal('3'), Decimal('6'), Decimal('0'),
                              date(2018, 2, 16))}
    out = handoff.jsonable(value)
    assert out['b'] == '1.50' and out['a'] == ['2018-02-16', {'3': 'x'}]
    assert out['m'] == {'value': None, 'reason': 'NO_FILL'} and out['f']['session'] == '2018-02-20'
    assert handoff.canonical_bytes(value) == handoff.canonical_bytes(json.loads(handoff.canonical_bytes(value)))
    assert handoff.canonical_bytes(value).endswith(b'\n') and b' ' not in handoff.canonical_bytes({'k': [1, 2]})
    with pytest.raises(handoff.HandoffError, match='NON_FINITE_NUMBER'):
        handoff.canonical_bytes({'x': float('nan')})


def test_output_manifest_records_run_and_files_and_verification_finds_changes():
    inputs = handoff.parse_input_manifest(manifest_bytes([resource('filings', b'[]')]))
    run = handoff.run_metadata(input_manifest=inputs, code_sha=None, generated_at='2026-11-01T00:00:00Z',
                               stage={'name': 'select', 'year': 2018, 'previous_u_a_sha256': None},
                               extra_inputs=[{'role': 'previous_u_a', 'sha256': '0' * 64}], code_flags=['CODE_TREE_DIRTY'])
    assert run['code_sha'] == 'UNKNOWN' and run['code_sha_flags'] == ['CODE_SHA_UNKNOWN', 'CODE_TREE_DIRTY']
    assert run['settings_sha256'] == settings.settings_sha256() and run['generated_at'] == '2026-11-01T00:00:00Z'
    body = b'{"x":1}\n'
    out = handoff.build_output_manifest(run, inputs, {'selection_inputs.json': body})
    assert out['run_id'] == run['run_id'] and out['input_manifest_sha256'] == inputs['sha256']
    assert out['outputs'] == [{'file': 'selection_inputs.json', 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': 8}]
    assert out['inputs'] == inputs['resources'] and out['stage']['year'] == 2018
    ok = handoff.verify_output_manifest(out, {'selection_inputs.json': body})
    assert ok['ok'] and ok['run_id_ok'] and ok['counts'] == {'OK': 1}
    bad = handoff.verify_output_manifest(out, {'selection_inputs.json': b'{"x":2}\n', 'other.json': b''})
    assert not bad['ok'] and bad['counts'] == {'HASH_MISMATCH': 1, 'UNLISTED': 1}
    assert handoff.verify_output_manifest(out, {})['counts'] == {'MISSING': 1}
    forged = dict(out, stage=dict(out['stage'], year=2019))
    assert handoff.verify_output_manifest(forged, {'selection_inputs.json': body})['run_id_ok'] is False
    with pytest.raises(handoff.HandoffError, match='OUTPUT_NAME_INVALID'):
        handoff.build_output_manifest(run, inputs, {'../x.json': body})
