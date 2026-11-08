"""Small, hand-counted held issuer projection fixtures; no private observations."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from test_classification_counts import inputs, pin, rewrite
from investment_system.research.sector_qgv import config_hash, default_config, digest


def job_fixture(root):
    job = inputs(root)
    job['schema_version'] = 'held-issuer-delivery-job/1'
    job['mode'] = 'issuer-delivery'
    crosswalk = []
    for issuer, tickers in [('A', ['SYN_A', 'SYN_A.B']), ('B', ['SYN_B']), ('C', ['SYN_C'])]:
        for ticker in tickers:
            crosswalk.append({'issuer_id': issuer, 'analysis_row_id': 'ISSUER:' + issuer,
                              'observed_ticker': ticker, 'security_id': None, 'representative': None,
                              'kind': 'CATALOG_OBSERVATION_NOT_LISTING_PROOF'})
    job['crosswalk'] = pin(root, 'crosswalk.json', crosswalk)
    for scope in ['operating', 'expanded']:
        def view(v):
            v['sources'] = [{'source_id': 'SYN_SOURCE', 'sha256': 'a' * 64,
                             'url': 'https://example.invalid/filing', 'locator': 'Business',
                             'acquired_at': '2026-11-03T00:00:00Z'}]
            for n, row in enumerate(v['rows']):
                known = n == 0
                for k, val in [('sector', 'INFORMATION_TECHNOLOGY'), ('accounting', 'GENERAL'), ('industry', 'computers')]:
                    row[k] = {'id': val if known else None, 'status': 'CONFIRMED' if known else 'UNKNOWN',
                              'reasons': [] if known else ['SYNTHETIC_MISSING'], 'evidence_refs': ['SYN_SOURCE'] if known else []}
                row.update(source_refs=['SYN_SOURCE'], record_id='REC:' + row['company_id'],
                           source_sic={'system': 'SEC_SIC', 'code': '3571'},
                           applicability={'kind': 'EVALUATION_DATE_ONLY', 'valuation_date': v['valuation_date']})
        rewrite(job, root, scope, 'view', view)
        def preview(p):
            p['config_hash'] = config_hash(default_config())
            versions = {k: p[k] for k in ('model_version', 'engine_version', 'normalization_version', 'mapping_version', 'input_version', 'snapshot_id', 'universe_id', 'universe_version')}
            p['cache_key'] = digest(dict(config_hash=p['config_hash'], input_hash=p['input_hash'], **versions))
            p['preview_id'] = digest({'cache': p['cache_key'], 'request_id': p['request_id']})
            for r in p['result_rows']:
                r.update(rank=None, gate_status='UNKNOWN', pre_gate_total=None,
                         selected_variants=['operating_margin_ttm', 'revenue_cagr_3y', 'cfo_mcap'])
                r['factors'] = {
                    'operating_margin_ttm': {'raw_value': 0, 'raw_status': 'VALID_ZERO', 'score': r['axes']['Q'],
                        'score_status': 'VALID' if r['axes']['Q'] is not None else 'PEER_SAMPLE_SMALL', 'valid_n': 20,
                        'raw_components_available': True, 'verified_external_available': False},
                    'revenue_cagr_3y': {'raw_value': .1, 'raw_status': 'VALID', 'score': r['axes']['G'],
                        'score_status': 'VALID' if r['axes']['G'] is not None else 'PEER_SAMPLE_SMALL', 'valid_n': 20,
                        'raw_components_available': True, 'verified_external_available': False},
                    'cfo_mcap': {'raw_value': None, 'raw_status': 'MISSING_INPUT', 'score': None,
                        'score_status': 'MISSING_INPUT', 'valid_n': 0,
                        'raw_components_available': False, 'verified_external_available': False}}
        rewrite(job, root, scope, 'preview', preview)
        job[scope]['expected']['config_hash'] = config_hash(default_config())
    return job


def project(job, **kw):
    from investment_system.research.held_issuer_delivery import project_delivery
    return project_delivery(job, **kw)


def decode(files, name):
    return json.loads(files[name])


def test_index_detail_preserve_issuer_rows_unknowns_zero_and_original_score_population(tmp_path):
    from investment_system.research.held_issuer_delivery import verify_delivery
    job = job_fixture(tmp_path)
    before = deepcopy(job)
    files = project(job)
    manifest = verify_delivery(files)
    index = decode(files, manifest['indexes'][0])['rows']
    assert [r['issuer_id'] for r in index] == ['A', 'B']
    a = decode(files, index[0]['detail']['path'])
    b = decode(files, index[1]['detail']['path'])
    assert a['analysis_row_id'] == 'ISSUER:A' and a['operating_code_rows'] == ['ROW:A', 'ROW:A.B']
    assert a['calculation']['axes']['Q'] == 0
    assert a['official_q_gate_input']['status'] == 'CONNECTED'
    assert a['calculation']['gate_status'] == 'UNKNOWN'
    assert a['calculation']['total'] is None and a['security_prices_technical']['status'] == 'NOT_CONNECTED'
    assert b['classification']['sector']['status'] == 'UNKNOWN'
    assert a['context']['scoring_population']['denominator'] == 3
    assert manifest['context']['population']['denominator'] == 2
    assert len(a['catalog_observations']) == 2
    assert all(r['security_id'] is None for r in a['catalog_observations'])
    assert 'raw_value' not in json.dumps(a) and job == before
    coverage = decode(files, 'coverage.json')
    assert coverage['scopes']['held_financial_subsample']['code_rows']['Q']['valid'] == 1
    assert coverage['scopes']['operating']['issuers']['G']['valid'] == 1
    assert coverage['scopes']['operating']['code_rows']['G']['valid'] == 2
    assert coverage['scopes']['held_financial_subsample']['code_rows']['all_default_raw']['valid'] == 0
    assert coverage['scopes']['held_financial_subsample']['issuers']['target']['goal_percent'] == 95
    assert coverage['full_market']['denominator'] is None


def repack_manifest(files):
    import hashlib
    m = decode(files, 'manifest.json')
    for entry in m['files']:
        if entry['path'] in files:
            b = files[entry['path']]
            entry.update(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
    files['manifest.json'] = json.dumps(m).encode()


@pytest.mark.parametrize('fault', ['hash', 'detail_missing', 'duplicate_index', 'wrong_issuer', 'context', 'extra_file', 'unreferenced_index', 'index_name', 'index_status'])
def test_delivery_corruption_or_scope_mix_rejected(tmp_path, fault):
    from investment_system.research.held_issuer_delivery import verify_delivery
    files = project(job_fixture(tmp_path))
    m = decode(files, 'manifest.json');ip = m['indexes'][0];idx = decode(files, ip);dp = idx['rows'][0]['detail']['path']
    if fault == 'hash':
        files[dp] += b' '
    elif fault == 'detail_missing':
        del files[dp]
    elif fault == 'duplicate_index':
        idx['rows'].append(deepcopy(idx['rows'][0]));files[ip] = json.dumps(idx).encode();repack_manifest(files)
    elif fault in ('wrong_issuer', 'context'):
        d = decode(files, dp)
        if fault == 'wrong_issuer':d['issuer_id'] = 'OTHER'
        else:d['context_hash'] = 'f' * 64
        files[dp] = json.dumps(d).encode();repack_manifest(files)
    elif fault == 'unreferenced_index':
        m['indexes'] = [];files['manifest.json'] = json.dumps(m).encode()
    elif fault in ('index_name', 'index_status'):
        idx['rows'][0]['observed_names' if fault == 'index_name' else 'calculation_status'] = ['WRONG'] if fault == 'index_name' else 'WRONG'
        files[ip] = json.dumps(idx).encode();repack_manifest(files)
    else:
        files['unexpected.json'] = b'{}'
    with pytest.raises(ValueError):verify_delivery(files)


def test_missing_source_evidence_and_unsupported_population_fail_closed(tmp_path):
    job = job_fixture(tmp_path)
    rewrite(job, tmp_path, 'expanded', 'view', lambda v: v.update(sources=[]))
    with pytest.raises(ValueError, match='EVIDENCE_REFERENCE_MISSING'):project(job)
    job = job_fixture(tmp_path)
    rewrite(job, tmp_path, None, 'crosswalk', lambda v: v[0].update(analysis_row_id='OTHER'))
    with pytest.raises(ValueError, match='CROSSWALK_ID_MISMATCH'):project(job)


def test_byte_bound_splits_index_without_dropping_details(tmp_path):
    from investment_system.research.held_issuer_delivery import verify_delivery
    job = job_fixture(tmp_path)
    original = project(job)
    # The index splitter has its own tighter request budget; the per-file hard
    # bound still covers every JSON, including details and manifest.
    files = project(job, index_bytes=1300)
    m = verify_delivery(files)
    assert len(m['indexes']) == 2
    assert m['context']['population'] == decode(original, 'manifest.json')['context']['population']
    assert all(len(b) <= 2 * 1024 * 1024 for b in files.values())


def test_cli_uses_projection_and_writes_verified_private_files(tmp_path, monkeypatch):
    import investment_system.research.sector_qgv as engine
    monkeypatch.setattr(engine, 'preview_qgv', lambda *a, **k: pytest.fail('scoring repeated'))
    spec = importlib.util.spec_from_file_location('delivery_cli', Path(__file__).parents[2] / 'tools/held_issuer_delivery.py')
    cli = importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    job = job_fixture(tmp_path);out = tmp_path / 'out'
    result = cli.run(job, out, synthetic=True)
    assert result['issuers'] == 2 and result['new_calculations'] == 0
    assert (out / 'manifest.json').exists()
    with pytest.raises(ValueError, match='OUTPUT_ALREADY_EXISTS'):cli.run(job, out, synthetic=True)
