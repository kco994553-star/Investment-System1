"""Only synthetic SEC observations; no live collection or credential lookup."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from investment_system.markets.us import US_LISTINGS

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from public_sec_inputs import build_public_inputs, collect_public_inputs, require_public_inputs
from pages_artifact_guard import scan_artifact, validate_pages_tar
from investment_system.product.web_mvp import build, repository_bundle


def raw(company):
    cik = US_LISTINGS[company]['cik']
    fact = {'end': '2025-12-31', 'val': 100, 'accn': '0000000001-26-000001', 'fy': 2025,
            'fp': 'FY', 'form': '10-K', 'filed': '2026-02-01'}
    return ({'cik': int(cik), 'facts': {'dei': {'EntityCommonStockSharesOutstanding':
            {'label': 'discarded', 'units': {'shares': [fact]}}},
            'us-gaap': {'Price': {'units': {'USD': [{'val': 987654321}]}}}},
            'private_value': 'never publish'}, {'cik': cik, 'filings': {'recent': {
            'accessionNumber': ['0000000001-26-000001'], 'form': ['10-K'],
            'filingDate': ['2026-02-01'], 'reportDate': ['2025-12-31'],
            'acceptanceDateTime': ['2026-02-01T12:00:00Z']}}})


def observations():
    return [(company, *(json.dumps(x).encode() for x in raw(company)), '2026-02-02T12:00:00Z')
            for company in sorted(US_LISTINGS)]


def test_projection_is_reported_shares_and_filing_metadata_only():
    result = build_public_inputs(observations())
    require_public_inputs(result)
    text = json.dumps(result)
    assert '987654321' not in text and 'never publish' not in text and 'label' not in text
    assert len(result['companies']) == 17
    assert result['companies'][0]['reported_shares'][0]['val'] == 100
    assert result['scope'] == 'US_TARGET17_REPORTED_SEC_ONLY'


@pytest.mark.parametrize('mutation', ['price', 'derived', 'extra', 'issuer', 'url', 'negative', 'bool', 'date', 'missing', 'duplicate', 'unit', 'accession'])
def test_public_contract_rejects_contamination_and_incomplete_identity(mutation):
    p = build_public_inputs(observations()); row = p['companies'][0]
    if mutation == 'price': row['price'] = 100
    elif mutation == 'derived': row['Q_score'] = 10
    elif mutation == 'extra': p['user_agent'] = 'private'
    elif mutation == 'issuer': row['cik'] = '0000000000'
    elif mutation == 'url': row['sources']['companyfacts']['url'] = 'https://other.test/data'
    elif mutation == 'negative': row['reported_shares'][0]['val'] = -1
    elif mutation == 'bool': row['reported_shares'][0]['val'] = True
    elif mutation == 'date': row['reported_shares'][0]['filed'] = '2026-02-30'
    elif mutation == 'missing': p['companies'].pop()
    elif mutation == 'duplicate': p['companies'][1] = copy.deepcopy(row)
    elif mutation == 'unit': row['reported_shares'][0]['unit'] = 'USD'
    elif mutation == 'accession': row['filings'][0]['accession'] = 'private'
    with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'): require_public_inputs(p)


def test_raw_issuer_duplicate_keys_and_nonfinite_inputs_fail_without_payload_output():
    for mode in ['issuer', 'duplicate', 'nonfinite']:
        rows = observations()
        if mode == 'issuer':
            value = json.loads(rows[0][1]); value['cik'] = 0; bad = json.dumps(value).encode()
        elif mode == 'duplicate': bad = b'{"cik":1,"cik":2}'
        else: bad = b'{"cik":NaN}'
        rows[0] = (rows[0][0], bad, *rows[0][2:])
        with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'): build_public_inputs(rows)


def test_collector_reuses_codex2_client_and_does_not_publish_after_failure(tmp_path, capsys):
    from datetime import datetime, timezone
    class Client:
        def __init__(self, user_agent): assert user_agent == 'synthetic setting'
        def collect(self, company, cik):
            assert cik == US_LISTINGS[company]['cik']
            return *(json.dumps(x).encode() for x in raw(company)), datetime(2026, 2, 2, 12, tzinfo=timezone.utc)
    out = tmp_path / 'sec-public-inputs.json'
    collect_public_inputs(out, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Client)
    assert out.is_file(); before = out.read_bytes()
    class Failing(Client):
        def collect(self, company, cik): raise OSError('private provider message')
    with pytest.raises(ValueError, match='SEC_COLLECTION_FAILED'):
        collect_public_inputs(out, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Failing)
    assert out.read_bytes() == before and capsys.readouterr().out == ''


def test_optional_public_sec_file_is_semantically_guarded_in_directory_and_tar(tmp_path):
    import io, tarfile
    site = tmp_path / 'site'; build(site, bundle=repository_bundle())
    path = site / 'sec-public-inputs.json'; path.write_text(json.dumps(build_public_inputs(observations())))
    assert scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    archive = tmp_path / 'artifact.tar'
    with tarfile.open(archive, 'w', format=tarfile.GNU_FORMAT) as tar:
        for file in sorted(site.iterdir()):
            payload = file.read_bytes(); info = tarfile.TarInfo('./' + file.name); info.size = len(payload); info.mode = 0o644
            tar.addfile(info, io.BytesIO(payload))
    assert validate_pages_tar(archive)['pages_artifact_guard'] == 'PASS'
    p = json.loads(path.read_text()); p['companies'][0]['price'] = 1; path.write_text(json.dumps(p))
    assert scan_artifact(site)['pages_artifact_guard'] == 'FAIL'


def test_daily_workflow_is_default_branch_only_and_checks_exact_public_directory():
    source = (TOOLS.parents[1] / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    assert "cron: '17 22 * * *'" in source
    assert "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)" in source
    assert 'SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}' in source
    assert "needs.dependency.outputs.ready == 'true'" in source
    assert 'providers/sec_collection.py' in source
    assert 'needs: dependency' in source
    for forbidden in ['actions/cache', 'upload-artifact@', 'git push', 'git commit', 'always()', 'TIINGO', 'CLOUDFLARE', 'GOOGLE']:
        assert forbidden not in source
    assert 'pages_artifact_guard.py' in source and 'test_public_sec_inputs.py' in source
    assert source.index('pages_artifact_guard.py') < source.index('actions/upload-pages-artifact')
    assert source.index('private_trades_browser_test.js') < source.index('actions/upload-pages-artifact')
    assert 'path: ${{ runner.temp }}/public-cockpit' in source and 'needs: build' in source


def test_missing_secret_stops_before_factory_or_requests(tmp_path):
    def forbidden(_setting):
        raise AssertionError('factory must not run without the named Secret')
    for value in (None, '', '   '):
        with pytest.raises(ValueError, match='SEC_USER_AGENT_MISSING'):
            collect_public_inputs(tmp_path / 'inputs.json', environ={'SEC_USER_AGENT': value}, client_factory=forbidden)
    assert not (tmp_path / 'inputs.json').exists()
