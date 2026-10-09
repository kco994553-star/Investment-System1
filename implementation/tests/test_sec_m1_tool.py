"""Bounded manual SEC input execution with synthetic transport only."""

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from tests.test_sec_m1_receipts import AT, payloads


def tool():
    path = Path(__file__).resolve().parents[1] / 'tools' / 'sec_m1_inputs.py'
    spec = importlib.util.spec_from_file_location('sec_m1_inputs_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_scope_is_validated_before_loader_or_storage(tmp_path):
    m = tool()

    def forbidden(*args):
        raise AssertionError('scope violation caused a request')

    for companies in ([], ['aapl'], ['hanmi'], ['nvda'] * 18):
        with pytest.raises(ValueError, match='US17'):
            m.run_batch(tmp_path / 'absent', companies, forbidden)
    assert not (tmp_path / 'absent').exists()


def test_transport_and_schema_failures_are_isolated(tmp_path):
    m = tool()

    def loader(company, cik):
        if company == 'nvda':
            return *payloads(), AT
        if company == 'asml':
            raise HTTPError('https://data.sec.gov/submissions/x', 429, 'simulated exhausted retries', None, None)
        return b'not json', b'not json', AT

    result = m.run_batch(tmp_path, ['asml', 'nvda', 'amd'], loader, as_of=AT)
    assert result['n_ready'] == 1 and result['n_failed'] == 2
    assert [r['status'] for r in result['results']] == ['ERROR_HTTPError', 'READY', 'ERROR_JSONDecodeError']
    assert result['results'][1]['receipt_id']


def test_failed_retry_keeps_last_verified_input(tmp_path):
    m = tool()
    ready = m.run_batch(tmp_path, ['nvda'], lambda *args: (*payloads(), AT), as_of=AT)

    def timeout(*args):
        raise TimeoutError('simulated')

    failed = m.run_batch(tmp_path, ['nvda'], timeout, as_of=AT)
    assert failed['results'][0]['previous_ready_receipt_id'] == ready['results'][0]['receipt_id']
    assert failed['results'][0]['status'] == 'ERROR_TimeoutError'


def test_live_loader_only_requests_two_sec_urls_and_never_prices(tmp_path, monkeypatch):
    m = tool()
    facts, subs = payloads()
    urls = []

    def fetch(url, ua):
        urls.append(url)
        assert ua == 'M1 Research owner@example.com'
        if '/companyfacts/' in url:
            return facts, 200, 'application/json'
        assert '/submissions/CIK' in url
        return subs, 200, 'application/json'

    monkeypatch.setattr(m, '_fetch', fetch)
    monkeypatch.setattr(m.time, 'sleep', lambda delay: None)
    loader = m.make_live_loader('M1 Research owner@example.com')
    result = m.run_batch(tmp_path, ['nvda'], loader)
    assert result['n_ready'] == 1
    assert urls == ['https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json',
                    'https://data.sec.gov/submissions/CIK0001045810.json']
    assert all(url.startswith('https://data.sec.gov/') for url in urls)


def test_offline_cli_never_calls_transport(tmp_path, monkeypatch, capsys):
    m = tool()
    source = tmp_path / 'imports'
    source.mkdir()
    facts, subs = payloads()
    (source / 'nvda.companyfacts.json').write_bytes(facts)
    (source / 'nvda.submissions.json').write_bytes(subs)

    def forbidden(*args):
        raise AssertionError('offline CLI attempted networking')

    monkeypatch.setattr(m, '_fetch', forbidden)
    code = m.main(['--companies', 'nvda', '--store', str(tmp_path / 'store'),
                   '--input-dir', str(source), '--acquired-at', AT.isoformat(), '--as-of', AT.isoformat()])
    result = json.loads(capsys.readouterr().out)
    assert code == 0 and result['n_ready'] == 1
    assert set(result['results'][0]) == {'company_id', 'status', 'receipt_id', 'previous_ready_receipt_id'}


def test_live_mode_requires_descriptive_contact_and_refuses_wrong_cik(monkeypatch):
    m = tool()
    for ua in ('', 'research', 'research contact@example.invalid'):
        with pytest.raises(ValueError):
            m.make_live_loader(ua)
    loader = m.make_live_loader('M1 Research owner@example.com')
    monkeypatch.setattr(m, '_fetch', lambda *args: pytest.fail('invalid issuer triggered request'))
    with pytest.raises(ValueError, match='US17'):
        loader('nvda', '0000320193')


def test_corrupt_previous_receipt_does_not_stop_other_issuers(tmp_path):
    m = tool()
    ready = m.run_batch(tmp_path, ['nvda'], lambda *args: (*payloads(), AT), as_of=AT)
    rid = ready['results'][0]['receipt_id']
    (tmp_path / 'm1' / 'receipts' / (rid + '.json')).write_text('[]')
    pointer = tmp_path / 'm1' / 'latest' / 'nvda.json'
    original_pointer = pointer.read_bytes()
    calls = []

    def loader(company, cik):
        calls.append(company)
        facts, subs = map(json.loads, payloads())
        facts['cik'], subs['cik'] = int(cik), cik
        return json.dumps(facts).encode(), json.dumps(subs).encode(), AT

    result = m.run_batch(tmp_path, ['nvda', 'amd'], loader, as_of=AT)
    assert calls == ['nvda', 'amd']
    assert result['n_ready'] == 1 and result['n_failed'] == 1
    assert result['results'][0]['status'] == 'ERROR_ValueError'
    assert pointer.read_bytes() == original_pointer
