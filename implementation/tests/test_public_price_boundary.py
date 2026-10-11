"""GSQ-010 offline public route regression; all hostile values are invented canaries."""
import importlib.util
import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from investment_system.product import web_mvp

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('offline boundary tests prohibit network access')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def tool(name):
    spec = importlib.util.spec_from_file_location('boundary_' + name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_public_bundle_never_reads_legacy_data():
    with patch.object(Path, 'read_bytes', side_effect=AssertionError('legacy read')), patch.object(Path, 'read_text', side_effect=AssertionError('legacy read')):
        bundle = web_mvp.repository_bundle()
    assert bundle['companies'] == []
    assert bundle['universe']['state'] == 'NOT_AVAILABLE'
    assert bundle['universe']['data'] is None


@pytest.mark.parametrize('field', ['price', 'market_cap_rank', 'rank', 'V_score', 'period_return', 'renamed'])
def test_public_build_rejects_unreviewed_nested_data_before_writing(tmp_path, field):
    bundle = web_mvp.repository_bundle()
    bundle['extra'] = {'nested': [{field: 'INVENTED_VALUE_CANARY'}]}
    out = tmp_path / 'site'
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY') as caught:
        web_mvp.build(out, bundle)
    assert 'INVENTED_VALUE_CANARY' not in str(caught.value)
    assert not out.exists()


def test_mixed_demo_fails_before_reading_or_writing(tmp_path):
    with patch.object(Path, 'read_text', side_effect=AssertionError('legacy read')):
        with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
            web_mvp.demo_bundle({})
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        web_mvp.build(tmp_path / 'site', demo=True)
    assert not (tmp_path / 'site').exists()


BLOCKED = {
    'fetch_stooq_prices': ['run', 'main'],
    'fetch_tiingo_prices': ['run', '_finish', 'main'],
    'fetch_krx_data': ['run', '_get'],
    'fetch_ishares_reference': ['main'],
    'fetch_nport_reference': ['main'],
    'live_smoke': ['main'],
    'nport_cross_check': ['fetch_series_nport', 'main'],
    'nport_reported_prices': ['investigate', 'main'],
    'official_pipeline': ['load_official', 'main'],
    'run_top500_gate_chain': ['main'],
    'audit_mcap_store': ['main'],
    'prepare_ca_unit_evidence': ['prepare'],
    'import_bulk_real_data': ['import_stooq'],
    'export_web_bundle': ['main'],
    'build_web_mvp_demo': ['main'],
    'build_web_research_guard_fixture': ['build_fixture', 'main'],
    'build_web_state_presentation_fixture': ['build_fixture', 'main'],
}


@pytest.mark.parametrize('name,function', [(n, f) for n, fs in BLOCKED.items() for f in fs])
def test_audited_entrypoints_fail_before_any_dependency(name, function, monkeypatch):
    fn = getattr(tool(name), function)
    args = [None for p in inspect.signature(fn).parameters.values()
            if p.default is inspect.Parameter.empty]
    for method in ('read_text', 'read_bytes', 'write_text', 'write_bytes', 'mkdir'):
        monkeypatch.setattr(Path, method, lambda *a, **kw: (_ for _ in ()).throw(AssertionError('dependency reached')))
    import socket
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('network reached')))
    with pytest.raises(ValueError, match='^PUBLIC_PRICE_BOUNDARY: route withheld under GSQ-010$'):
        fn(*args)


def test_shared_fetch_rejects_price_or_unknown_source_before_cache_or_http():
    fn = tool('fetch_real_data')._fetch_one
    for kind in ('YAHOO_CHART', 'YAHOO_SPLIT_EVENTS', 'NPORT', 'ISHARES_FUND_HOLDINGS', 'UNKNOWN'):
        with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
            fn(None, 'synthetic-id', 'https://invalid.example', kind, '', [], False)


def test_real_collector_rejects_price_plan_before_store_creation(tmp_path, monkeypatch):
    module = tool('fetch_real_data')
    def forbidden_http(*args, **kwargs):
        raise AssertionError('HTTP must not be reached')
    monkeypatch.setattr(module, 'urlopen', forbidden_http)
    fn = module.run
    for symbols, plan in [(['SYNTHETIC'], None), ([], {'anything': 'unreviewed'})]:
        out = tmp_path / 'store'
        with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
            fn(out, [], symbols, '5y', 0, True, plan=plan)
        assert not out.exists()


def test_financial_only_empty_collection_remains_available(tmp_path):
    result = tool('fetch_real_data').run(tmp_path / 'financial', [], [], '5y', 0, True)
    assert result['n_requested'] == 0


def test_identity_parser_remains_available():
    date, rows = tool('fetch_ishares_reference').parse_holdings(b'Fund Holdings as of,"Dec 31, 2024"\nTicker,Name,Asset Class,ISIN,CUSIP\nEXAMPLE,Example,Equity,XX0000000001,000000000\n')
    assert isinstance(rows, list)


def test_original_27_plus_ishares_routes_are_accounted_for():
    audit = (ROOT / 'docs/public_price_boundary/AUDIT.md').read_text()
    routes = [line.split('`')[1] for line in audit.splitlines()
              if line.startswith('| `') and '공개 출력 경로' in line and '| 정리 필요 |' in line]
    assert len(set(routes)) == 27
    from investment_system.public_price_boundary import AUDITED_ROUTES
    assert set(AUDITED_ROUTES) == set(routes) | {'implementation/tools/fetch_ishares_reference.py'}


@pytest.mark.parametrize('name', ['c21-real-data', 'cockpit-pages', 'web-mvp-validation', 'web-research-guard', 'web-state-presentation'])
def test_affected_workflows_have_no_publication_sinks(name):
    source = (ROOT.parent / '.github/workflows' / (name + '.yml')).read_text()
    for forbidden in ['actions/cache', 'git push', 'git commit', 'always()']:
        assert forbidden not in source
    assert 'test_public_price_boundary.py' in source
    if name != 'cockpit-pages':
        assert 'actions/upload' not in source and 'actions/deploy-pages' not in source
    else:
        assert source.count('actions/upload') == 1
        assert source.count('actions/deploy-pages') == 1
        assert 'actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda462b719fa' in source
        assert 'actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e' in source
        condition = "github.event_name == 'workflow_dispatch' && github.ref_name == 'claude/investment-system-top500-validation-alrugm'"
        assert source.count(condition) == 2
        assert "path: ${{ runner.temp }}/public-cockpit" in source
        assert "needs: build" in source
        assert source.index('pages_artifact_guard.py') < source.index('actions/upload')
        assert source.index('ci_browser_tests.txt') < source.index('actions/upload')
        assert 'private_history_browser_test.js' in (ROOT / 'tools/ci_browser_tests.txt').read_text().split()



@pytest.mark.parametrize('field', ['rank', 'market_cap_rank', 'total_score', 'V_score', 'period_return', 'renamed'])
def test_semantic_guard_rejects_nested_values_even_if_hash_is_repinned(tmp_path, field):
    import hashlib
    from collections import Counter
    guard = tool('pages_artifact_guard')
    bundle = web_mvp.repository_bundle()
    bundle['universe']['data'] = {'nested': [{field: 'SYNTHETIC_CANARY'}]}
    payload = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    guard.APPROVED_SHA256['data.json'] = hashlib.sha256(payload).hexdigest()
    violations = Counter()
    guard._check_payload('data.json', payload, violations)
    assert violations['public_price_boundary'] > 0


def test_atomic_export_cannot_bypass_public_policy(tmp_path):
    from investment_system.producers.assembler import write_bundle_atomic
    bundle = web_mvp.repository_bundle()
    bundle['universe']['data'] = {'nested': [{'price': 987654321}]}
    out = tmp_path / 'bundle.json'
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        write_bundle_atomic(bundle, out)
    assert not out.exists()
    assert not out.with_name('bundle.json.sha256').exists()


def test_default_registry_withholds_frozen_without_reading_legacy_files():
    from datetime import datetime, timezone
    from investment_system.producers.registry import default_registry, ProduceRequest
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with patch.object(Path, 'read_text', side_effect=AssertionError('legacy read')), patch.object(Path, 'read_bytes', side_effect=AssertionError('legacy read')):
        snapshots = default_registry().run(ProduceRequest(now, now))
    assert all(s['data_state'] == 'NOT_AVAILABLE' and s['data'] is None for s in snapshots.values())


def test_financial_label_cannot_authorize_a_price_endpoint():
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        tool('fetch_real_data')._fetch_one(None, 'x', 'https://query1.finance.yahoo.com/chart/EXAMPLE', 'SEC_COMPANYFACTS', '', [])


@pytest.mark.parametrize('function', ['_get', '_get_with_retry'])
def test_direct_shared_network_helpers_reject_price_endpoints(function, monkeypatch):
    module = tool('fetch_real_data')
    calls = []
    monkeypatch.setattr(module, 'urlopen', lambda *a, **kw: calls.append(1))
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        getattr(module, function)('https://query1.finance.yahoo.com/chart/EXAMPLE', '')
    assert calls == []


@pytest.mark.parametrize('name', ['entities.json', 'actual-catalog.json'])
def test_catalog_semantic_guard_rejects_repinned_nested_value(name):
    import hashlib
    from collections import Counter
    from investment_system.product.entity_catalog import entity_catalog
    from investment_system.product.device_actual_catalog import public_actual_catalog
    guard = tool('pages_artifact_guard')
    catalog = entity_catalog(web_mvp.repository_bundle()) if name == 'entities.json' else public_actual_catalog()
    catalog['renamed'] = {'nested': ['INVENTED_PRICE_CANARY']}
    payload = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    guard.APPROVED_SHA256[name] = hashlib.sha256(payload).hexdigest()
    violations = Counter()
    guard._check_payload(name, payload, violations)
    assert violations['public_price_boundary'] > 0


def test_bulk_financial_import_projects_admitted_facts_and_drops_price_fields(tmp_path):
    import zipfile
    from investment_system.ingestion.raw_store import RawDatasetStore
    archive = tmp_path / 'input.zip'
    payload = {'cik': 1, 'renamed': {'price': 987654321}, 'facts': {'us-gaap': {
        'Revenues': {'units': {'USD': [{'val': 321, 'filed': '2025-01-01', 'price': 987654321}]}},
        'PriceRenamed': {'units': {'USD': [{'val': 987654321}]}}}}}
    with zipfile.ZipFile(archive, 'w') as handle:
        handle.writestr('CIK0000000001.json', json.dumps(payload))
        handle.writestr('CIK0000000002.json', json.dumps({'price': 987654321}))
    store = RawDatasetStore(tmp_path / 'store')
    result = tool('import_bulk_real_data').import_sec(store, archive, False)
    assert result['imported'] == 1 and result['bad'] == 1
    persisted = store.get_bytes('companyfacts:0000000001')
    assert b'987654321' not in persisted
    assert json.loads(persisted)['facts']['us-gaap']['Revenues']['units']['USD'][0]['val'] == 321


@pytest.mark.parametrize('name,function', [('audit_mcap_store','audit'), ('audit_mcap_store','audit_many'), ('audit_mcap_store','ranked_top500'), ('audit_mcap_store','row_detail'), ('run_top500_gate_chain','run_chain')])
def test_importable_disk_report_blocks_before_read(name, function):
    fn = getattr(tool(name), function)
    args = [None for p in inspect.signature(fn).parameters.values() if p.default is inspect.Parameter.empty]
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        fn(*args)


def test_financial_endpoint_cannot_be_stored_under_price_identity():
    module = tool('fetch_real_data')
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        module._fetch_one(None, 'yahoo_chart:EXAMPLE:5y', module.SEC_TICKERS_URL, 'SEC_TICKERS', '', [])


def test_unprojected_sec_archive_is_not_assumed_price_free():
    module = tool('fetch_real_data')
    with pytest.raises(ValueError, match='PUBLIC_PRICE_BOUNDARY'):
        module._fetch_one(None, 'xbrl_instance:0000000001:0000000001-25-000001',
            'https://www.sec.gov/Archives/edgar/data/1/000000000125000001/q_htm.xml', 'SEC_XBRL_INSTANCE', '', [])


@pytest.mark.parametrize('name', ['entities.json', 'actual-catalog.json'])
def test_repinned_catalog_is_rejected_equally_by_directory_and_tar(tmp_path, name):
    import hashlib
    import tarfile
    site = web_mvp.build(tmp_path / 'site')
    guard = tool('pages_artifact_guard')
    path = site / name
    value = json.loads(path.read_text())
    value['renamed'] = {'nested': ['INVENTED_VALUE_CANARY']}
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    path.write_bytes(raw)
    guard.APPROVED_SHA256[name] = hashlib.sha256(raw).hexdigest()
    directory = guard.scan_artifact(site)
    archive = tmp_path / 'site.tar'
    with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as handle:
        for entry in sorted(site.iterdir()):
            info = handle.gettarinfo(str(entry), arcname='./' + entry.name)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            with entry.open('rb') as content:
                handle.addfile(info, content)
    assert directory == guard.validate_pages_tar(archive)
    assert directory['violations']['public_price_boundary'] > 0
    assert 'INVENTED_VALUE_CANARY' not in json.dumps(directory)
