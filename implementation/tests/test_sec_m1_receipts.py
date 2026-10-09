"""Synthetic SEC custody, cutoff and interrupted-publication tests; no network."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_system.ingestion.raw_store import RawDatasetStore

AT = datetime(2026, 10, 9, 10, tzinfo=timezone.utc)


def payloads(value=100, amended=False):
    accn = '0001045810-26-000002' if amended else '0001045810-26-000001'
    form = '10-K/A' if amended else '10-K'
    facts = {'cik': 1045810, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
        {'start': '2025-01-01', 'end': '2025-12-31', 'val': value,
         'filed': '2026-10-08', 'form': form, 'fy': 2025, 'fp': 'FY', 'accn': accn}
    ]}}}}}
    subs = {'cik': '0001045810', 'filings': {'recent': {
        'form': [form], 'filingDate': ['2026-10-08'], 'accessionNumber': [accn],
        'acceptanceDateTime': ['2026-10-08T20:00:00Z']}}}
    return json.dumps(facts).encode(), json.dumps(subs).encode()


def api():
    from investment_system.ingestion import sec_m1
    return sec_m1


def test_rerun_and_replay_bind_the_same_immutable_bytes(tmp_path):
    m = api()
    facts, subs = payloads()
    first = m.retain_input(tmp_path, 'nvda', facts, subs, AT, AT)
    again = m.retain_input(tmp_path, 'nvda', facts, subs, AT, AT)
    assert first == again
    assert first['input']['raw_fundamentals']['revenue'] == 100
    assert m.load_latest(tmp_path, 'nvda') == first
    early = m.replay_receipt(tmp_path, first['receipt_id'], AT.replace(hour=9))
    assert early['status'] == 'NOT_AVAILABLE'
    assert m.replay_receipt(tmp_path, first['receipt_id'], AT) == first['input']
    store = RawDatasetStore(tmp_path)
    assert store.get_bytes(first['inputs']['companyfacts']['artifact_id']) == facts


def test_same_accession_payload_revision_keeps_original_receipt(tmp_path):
    m = api()
    old = m.retain_input(tmp_path, 'nvda', *payloads(100), AT, AT)
    later = AT.replace(hour=11)
    new = m.retain_input(tmp_path, 'nvda', *payloads(90), later, later)
    assert old['receipt_id'] != new['receipt_id']
    assert new['revision_parent_receipt_id'] == old['receipt_id']
    assert new['change_kind'] == 'PAYLOAD_REVISION'
    assert new['changes'] and all(not c['formal_amendment'] for c in new['changes'])
    assert all(c['parent_accession'] is None for c in new['changes'])
    assert m.load_receipt(tmp_path, old['receipt_id'])['input']['raw_fundamentals']['revenue'] == 100
    assert m.load_latest(tmp_path, 'nvda')['input']['raw_fundamentals']['revenue'] == 90


def test_unavailable_refresh_preserves_previous_ready_pointer(tmp_path):
    m = api()
    old = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    future = AT.replace(hour=12)
    unavailable = m.retain_input(tmp_path, 'nvda', *payloads(90), future, AT)
    assert unavailable['input']['status'] == 'NOT_AVAILABLE'
    assert m.load_latest(tmp_path, 'nvda') == old


def test_older_ready_cutoff_does_not_replace_newer_pointer(tmp_path):
    m = api()
    later = AT.replace(hour=12)
    new = m.retain_input(tmp_path, 'nvda', *payloads(90), later, later)
    old = m.retain_input(tmp_path, 'nvda', *payloads(100), AT, AT.replace(hour=13))
    assert old['input']['status'] == 'READY'
    assert old['revision_parent_receipt_id'] is None
    assert m.load_latest(tmp_path, 'nvda') == new


def test_quarterly_receipt_replay_preserves_form_filter(tmp_path):
    m = api()
    facts, subs = map(json.loads, payloads())
    row = facts['facts']['us-gaap']['Revenues']['units']['USD'][0]
    row.update(start='2026-04-01', end='2026-06-30', form='10-Q', fy=2026, fp='Q2')
    subs['filings']['recent']['form'] = ['10-Q']
    receipt = m.retain_input(tmp_path, 'nvda', json.dumps(facts).encode(), json.dumps(subs).encode(),
                             AT, AT, form_filter='10-Q')
    assert receipt['input']['status'] == 'READY'
    assert m.replay_receipt(tmp_path, receipt['receipt_id'], AT) == receipt['input']


def test_raw_and_manifest_tampering_are_rejected(tmp_path):
    m = api()
    receipt = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    artifact = receipt['inputs']['companyfacts']['artifact_id']
    blob = tmp_path / 'blobs' / artifact.replace(':', '__')
    original = blob.read_bytes()
    blob.write_bytes(original + b' ')
    with pytest.raises(ValueError, match='integrity'):
        m.load_receipt(tmp_path, receipt['receipt_id'])
    blob.write_bytes(original)
    manifest = tmp_path / 'manifests' / (artifact.replace(':', '__') + '.json')
    data = json.loads(manifest.read_text())
    data['sha256'] = '0' * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='integrity'):
        m.load_latest(tmp_path, 'nvda')


def test_receipt_tampering_and_missing_blob_are_rejected(tmp_path):
    m = api()
    receipt = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    path = tmp_path / 'm1' / 'receipts' / (receipt['receipt_id'] + '.json')
    original = path.read_bytes()
    changed = json.loads(original)
    changed['input']['raw_fundamentals']['revenue'] = 999
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='integrity'):
        m.load_receipt(tmp_path, receipt['receipt_id'])
    path.write_bytes(original)
    artifact = receipt['inputs']['submissions']['artifact_id']
    (tmp_path / 'blobs' / artifact.replace(':', '__')).unlink()
    with pytest.raises(ValueError, match='integrity'):
        m.load_latest(tmp_path, 'nvda')


def test_interrupted_second_snapshot_keeps_previous_input(tmp_path, monkeypatch):
    m = api()
    old = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    put = RawDatasetStore.put
    calls = []

    def interrupted(self, *args, **kwargs):
        calls.append(args[0])
        if len(calls) == 2:
            raise OSError('simulated interrupted snapshot')
        return put(self, *args, **kwargs)

    monkeypatch.setattr(RawDatasetStore, 'put', interrupted)
    later = AT.replace(hour=12)
    with pytest.raises(OSError):
        m.retain_input(tmp_path, 'nvda', *payloads(90, True), later, later)
    assert len(calls) == 2
    assert m.load_latest(tmp_path, 'nvda') == old


def test_interrupted_pointer_publication_keeps_previous_input(tmp_path, monkeypatch):
    m = api()
    old = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    replace = m.os.replace

    def interrupted(src, dest):
        path = Path(dest)
        if path.parent.name == 'latest' and path.name == 'nvda.json':
            raise OSError('simulated interrupted pointer')
        return replace(src, dest)

    monkeypatch.setattr(m.os, 'replace', interrupted)
    later = AT.replace(hour=12)
    with pytest.raises(OSError):
        m.retain_input(tmp_path, 'nvda', *payloads(90), later, later)
    assert m.load_latest(tmp_path, 'nvda') == old


def test_outside_target_rejected_before_any_storage(tmp_path):
    with pytest.raises(ValueError, match='US17'):
        api().retain_input(tmp_path / 'absent', 'aapl', *payloads(), AT, AT)
    assert not (tmp_path / 'absent').exists()


def test_valid_json_with_wrong_receipt_shape_fails_closed(tmp_path):
    m = api()
    receipt = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    path = tmp_path / 'm1' / 'receipts' / (receipt['receipt_id'] + '.json')
    for value in ([], None, 1):
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError, match='integrity'):
            m.load_latest(tmp_path, 'nvda')


@pytest.mark.parametrize('field,value', [
    ('artifact_id', None), ('artifact_id', '../outside'),
    ('sha256', None), ('bytes', True), ('bytes', -1),
])
def test_malformed_snapshot_binding_rejected_before_store_lookup(tmp_path, monkeypatch, field, value):
    m = api()
    receipt = m.retain_input(tmp_path, 'nvda', *payloads(), AT, AT)
    receipt['inputs']['companyfacts'][field] = value
    receipt['receipt_id'] = m._digest({k: receipt[k] for k in m.CORE})
    receipt.pop('receipt_sha256')
    receipt['receipt_sha256'] = m._digest(receipt)
    path = tmp_path / 'm1' / 'receipts' / (receipt['receipt_id'] + '.json')
    path.write_text(json.dumps(receipt))

    def unexpected_lookup(*args):
        raise AssertionError('malformed binding reached blob lookup')

    monkeypatch.setattr(RawDatasetStore, 'get_bytes', unexpected_lookup)
    with pytest.raises(ValueError, match='integrity'):
        m.load_receipt(tmp_path, receipt['receipt_id'])
