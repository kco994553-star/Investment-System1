import copy
import hashlib
import importlib.util
import json
from pathlib import Path

from investment_system.ingestion.raw_store import RawDatasetStore

spec = importlib.util.spec_from_file_location("ca_unit", Path(__file__).parents[1] / "tools" / "ca_unit_policy.py")
unit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(unit)


def fixture(tmp_path):
    store = RawDatasetStore(tmp_path)
    body = b'Issuer Z common stock split two-for-one effective June 10, 2024.'
    store.put('primary:z', body, 'https://issuer.example/split', 'PRIMARY', 'text/html', 'test')
    event = {'event_id': 'z-split', 'cik': '0000000001', 'symbols': ['ZZZ'], 'security_scope': ['ZZZ'],
             'provider_event_date': '2024-06-10', 'unit_effective_at': '2024-06-10',
             'kind': 'SPLIT', 'share_factor': 2, 'security_basis': 'Issuer Z common stock',
             'documents': [{'artifact_id': 'primary:z', 'url': 'https://issuer.example/split',
                            'sha256': hashlib.sha256(body).hexdigest(), 'published_at': '2024-05-20',
                            'quotes': [body.decode()]}]}
    policy = {'policy_version': 'CA-UNIT-v1.0', 'approved': True, 'events': [event]}
    candidate = {'company_id': 'z', 'ticker': 'ZZZ', 'cik': '0000000001', 'shares': 100,
                 'shares_available_at': '2024-05-15', 'price': 20, 'gate_mcap': 2000,
                 'price_observed_at': '2024-06-28T20:00:00+00:00',
                 'security_components': [{'symbol': 'ZZZ', 'shares': 100, 'price': 20, 'measurement_date': '2024-05-10'}]}
    return store, policy, candidate


def test_primary_event_applies_without_vendor_event_and_is_idempotent(tmp_path):
    store, policy, c = fixture(tmp_path)
    overrides = {}
    report = unit.reconcile(store, [c], overrides, policy, unit.dt('2024-06-30'))
    assert report['passed'] and overrides['z']['mcap'] == 4000
    normalized = overrides['z']['unit_candidate']
    assert normalized['ca_unit']['original_shares'] == 100
    unit.reconcile(store, [normalized], overrides, policy, unit.dt('2024-06-30'))
    assert overrides['z']['mcap'] == 4000
    assert c['shares'] == 100


def test_future_missing_or_tampered_primary_evidence_blocks(tmp_path):
    store, policy, c = fixture(tmp_path)
    for field, value in [('published_at', '2024-07-01'), ('artifact_id', 'absent'), ('sha256', 'wrong'), ('quotes', ['invented'])]:
        p = copy.deepcopy(policy); p['events'][0]['documents'][0][field] = value
        overrides = {}
        assert not unit.reconcile(store, [c], overrides, p, unit.dt('2024-06-30'))['passed']
        assert not overrides


def test_vendor_event_does_not_authorize_shares_even_for_raw_close(tmp_path):
    store, _, c = fixture(tmp_path)
    body = json.dumps({'chart': {'result': [{'events': {'splits': {'1': {'date': int(unit.dt('2024-06-10').timestamp()), 'numerator': 99, 'denominator': 1}}}}]}}).encode()
    store.put('yahoo_events:ZZZ:5y', body, 'url', 'YAHOO_EVENTS', 'application/json', 'test')
    store.put('yahoo_chart:ZZZ:5y', b'{}', 'url', 'TIINGO_DAILY_RAW', 'application/json', 'test')
    overrides = {}
    r = unit.reconcile(store, [c], overrides, None, unit.dt('2024-06-30'))
    assert not r['passed'] and not overrides


def test_spinoff_preserves_parent_and_successor_uses_actual_count(tmp_path):
    store, policy, c = fixture(tmp_path)
    event = policy['events'][0]
    event.update(kind='SPINOFF_PARENT_UNCHANGED', share_factor=1)
    overrides = {}; r = unit.reconcile(store, [c], overrides, policy, unit.dt('2024-06-30'))
    assert r['passed'] and overrides['z']['mcap'] == 2000
    event.update(kind='SUCCESSOR_ACTUAL_SHARES', actual_shares=77, actual_measurement_date='2024-06-10', issuer_transition='old canceled, successor issued')
    overrides = {}; r = unit.reconcile(store, [c], overrides, policy, unit.dt('2024-06-30'))
    assert r['passed'] and overrides['z']['mcap'] == 1540


def test_multiclass_and_measurement_ambiguity_fail_transactionally(tmp_path):
    store, policy, c = fixture(tmp_path)
    c['security_components'].append({'member': 'OtherClass', 'symbol': None, 'shares': 50, 'price': None, 'measurement_date': '2024-05-10'})
    overrides = {}
    assert not unit.reconcile(store, [c], overrides, policy, unit.dt('2024-06-30'))['passed']
    assert not overrides
    policy['events'][0]['security_scope'].append('OtherClass')
    r = unit.reconcile(store, [c], overrides, policy, unit.dt('2024-06-30'))
    assert r['passed'] and overrides['z']['classes'][1]['shares'] == 100
    c['security_components'][0]['measurement_date'] = '2024-06-11'
    assert not unit.reconcile(store, [c], {}, policy, unit.dt('2024-06-30'))['passed']


def test_result_fields_never_change_policy_application(tmp_path):
    store, policy, c = fixture(tmp_path)
    for rank in (1, 500, 501, 10000):
        c.update(rank=rank, cutoff=rank * 1000, forward_return=rank / 100)
        overrides = {}
        assert unit.reconcile(store, [c], overrides, policy, unit.dt('2024-06-30'))['passed']
        assert overrides['z']['mcap'] == 4000


def test_post_event_publication_does_not_prove_adjusted_units(tmp_path):
    store, policy, c = fixture(tmp_path)
    c['shares_available_at'] = '2024-06-12'
    assert not unit.reconcile(store, [c], {}, policy, unit.dt('2024-06-30'))['passed']

    spin = copy.deepcopy(policy)
    spin['events'][0].update(kind='SPINOFF_PARENT_UNCHANGED', share_factor=1)
    overrides = {}
    assert unit.reconcile(store, [c], overrides, spin, unit.dt('2024-06-30'))['passed']
    assert overrides['z']['mcap'] == 2000
    body = json.dumps({'chart': {'result': [{'events': {'splits': {'1': {'date': int(unit.dt('2024-06-10').timestamp()), 'numerator': 2, 'denominator': 1}}}}]}}).encode()
    store.put('yahoo_events:ZZZ:5y', body, 'url', 'YAHOO_EVENTS', 'application/json', 'test')
    assert not unit.reconcile(store, [c], {}, policy, unit.dt('2024-06-30'))['passed']


def test_quote_from_before_action_cannot_be_mixed_with_new_share_units(tmp_path):
    store, policy, c = fixture(tmp_path)
    c['price_observed_at'] = '2024-06-07T20:00:00+00:00'
    assert not unit.reconcile(store, [c], {}, policy, unit.dt('2024-06-30'))['passed']
