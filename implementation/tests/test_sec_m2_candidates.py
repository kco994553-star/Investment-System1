"""Synthetic vectors exercise the candidate public boundary, never actual inputs."""
from copy import deepcopy
from importlib import import_module
import json
import pytest
from investment_system.product.web_mvp import build
from investment_system.public_price_boundary import public_bundle
from tests.test_sec_m2_qg import retain, analyze, METRICS


def api():
    try:
        return import_module('investment_system.product.sec_m2_candidates')
    except ModuleNotFoundError:
        pytest.fail('Candidate projection API is absent')


@pytest.fixture
def candidate(tmp_path):
    root = tmp_path / 'store'
    return analyze(root, [retain(root, c) for c in ('asml', 'nvda', 'stry')])


def test_default_build_is_unavailable_without_candidates(tmp_path):
    build(tmp_path / 'site')
    path = tmp_path / 'site/sec-m2-candidates.json'
    assert path.exists(), 'Default candidate sidecar is absent'
    assert json.loads(path.read_text()) == api().unavailable_candidates()
    assert json.loads((path.parent / 'data.json').read_text()) == public_bundle()


def test_native_projection_is_verbatim_and_does_not_mutate(candidate, tmp_path):
    before = deepcopy(candidate)
    result = api().project_candidates(candidate)
    assert candidate == before
    assert result['display_state'] == 'RESEARCH_CANDIDATE'
    assert result['input_kind'] == 'SYNTHETIC'
    assert result['companies']['stry']['ticker'] == 'SYK'
    for cid, row in result['companies'].items():
        native = candidate['candidate_data']['qgv']['data'][cid]
        assert (row['Q_score'], row['G_score'], row['V_score'], row['V_status']) == (native['Q_score'], native['G_score'], None, 'NOT_AVAILABLE')
        assert 'total_score' not in row and 'rank' not in row
    build(tmp_path / 'site', sec_m2_candidate=candidate)
    assert json.loads((tmp_path / 'site/data.json').read_text()) == public_bundle()
    assert json.loads((tmp_path / 'site/sec-m2-candidates.json').read_text()) == result
    api().require_public_candidates(result)


def test_zero_and_missing_native_scores_stay_distinct(candidate, tmp_path):
    candidate['candidate_data']['qgv']['data']['nvda']['Q_score'] = 0
    for row in candidate['candidate_data']['leaderboard']['data']['rows']:
        if row['company_id'] == 'nvda':
            row['Q_score'] = 0
    assert api().project_candidates(candidate)['companies']['nvda']['Q_score'] == 0
    root = tmp_path / 'partial'
    native = analyze(root, [retain(root, metrics={})])
    row = api().project_candidates(native)['companies']['nvda']
    assert row['status'] == 'NOT_AVAILABLE'
    assert row['Q_score'] is None and row['G_score'] is None


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(prices_used=True),
    lambda c: c.update(publication_approved=True),
    lambda c: c.update(synthetic_inputs=False),
    lambda c: c.update(as_of='2025-03-01'),
    lambda c: c.update(evaluated_at='2020-01-01T00:00:00Z'),
    lambda c: c.update(candidate_id='private-path-canary'),
    lambda c: c['publication'].update(grant='APPROVED'),
    lambda c: c['companies']['stry'].update(ticker='STRY'),
    lambda c: c['companies']['asml'].update(company_id='unknown'),
    lambda c: c['candidate_data']['qgv']['data']['asml'].update(Q_score=float('nan')),
    lambda c: c['candidate_data']['qgv']['data']['asml'].update(G_score=101),
    lambda c: c['candidate_data']['qgv']['data']['asml'].update(V_score=0),
    lambda c: c['candidate_data']['qgv']['data']['asml'].update(synthetic=False),
    lambda c: c['candidate_data']['leaderboard']['data']['rows'][0].update(Q_score=1),
    lambda c: c['companies']['asml'].update(Q_score=1),
])
def test_contradictions_reject_before_output_without_values(candidate, tmp_path, mutation):
    mutation(candidate)
    with pytest.raises(ValueError, match=r'^M2_CANDIDATE_INVALID$'):
        build(tmp_path / 'site', sec_m2_candidate=candidate)
    assert not (tmp_path / 'site').exists()


def test_untrusted_raw_pools_and_strings_never_projected(candidate, tmp_path):
    marker = 'INVENTED_PRIVATE_CANARY'
    candidate['notes'] = marker
    candidate['companies']['asml']['source']['selected_input_facts'] = {'price': marker, 'path': marker}
    candidate['companies']['asml']['normalized_financial_fields'] = {'money': marker}
    candidate['candidate_data']['qgv']['data']['asml']['factor_breakdown'] = {'anything': marker}
    build(tmp_path / 'site', sec_m2_candidate=candidate)
    assert all(marker not in p.read_text() for p in (tmp_path / 'site').iterdir())


def test_unavailable_source_and_incomplete_native_shapes(tmp_path):
    for name, kwargs in [('quarterly', {'form':'10-Q'}), ('partial', {'metrics':{'Revenues': METRICS['Revenues']}})]:
        root = tmp_path / name
        native = analyze(root, [retain(root, **kwargs)])
        row = api().project_candidates(native)['companies']['nvda']
        assert row['status'] == 'NOT_AVAILABLE'
        assert row['Q_score'] is None and row['G_score'] is None
    root = tmp_path / 'bad-replay'
    native = analyze(root, [retain(root)])
    row = native['companies']['nvda']
    row.update(status='NOT_AVAILABLE', reason_codes=['ORIGINAL_REPLAY_MISMATCH'])
    for key in ('source', 'snapshot_id', 'coverage'):
        row.pop(key, None)
    native['candidate_data']['qgv']['data'] = {}
    native['candidate_data']['qgv']['adapter_synthetic'] = False
    native['candidate_data']['leaderboard']['data']['rows'] = []
    native.update(n_calculated=0, n_unavailable=1)
    native['failures'] = [deepcopy(row)]
    assert api().project_candidates(native)['companies']['nvda']['source'] is None


def test_explicit_loader_rejects_duplicate_nonfinite_bad_input(tmp_path):
    for body in ['{"contract":1,"contract":2}', '{"score":NaN}', '{', '[]']:
        path = tmp_path / 'input.json'
        path.write_text(body)
        with pytest.raises(ValueError, match=r'^M2_CANDIDATE_INVALID$'):
            api().load_candidates(path)


def test_all_registry_identities_and_observed_unverified_flags(tmp_path):
    from investment_system.markets.us import US_LISTINGS
    root = tmp_path / 'all'
    native = analyze(root, [retain(root, c) for c in US_LISTINGS], synthetic=False)
    result = api().project_candidates(native)
    assert set(result['companies']) == set(US_LISTINGS)
    assert result['input_kind'] == 'OBSERVED_UNVERIFIED' and result['synthetic_inputs'] is False
    assert result['publication_approved'] is False


@pytest.mark.parametrize('mutate', [
    lambda c: c.update(extra='INVENTED_CANARY'),
    lambda c: c.update(prices_used=True),
    lambda c: c.update(publication_grant='APPROVED'),
    lambda c: c.update(as_of='2025-01-01'),
    lambda c: c['companies']['asml'].update(price=0),
    lambda c: c['companies']['asml'].update(V_score=0),
    lambda c: c['companies']['asml'].update(Q_score=float('nan')),
    lambda c: c['companies']['asml'].update(ticker='wrong'),
    lambda c: c['companies']['asml'].update(source={'path':'INVENTED_CANARY'}),
])
def test_repinned_hostile_sidecars_fail_directory_and_tar(candidate, tmp_path, mutate):
    import hashlib
    import importlib.util
    from pathlib import Path
    import tarfile
    path = Path(__file__).parents[1] / 'tools/pages_artifact_guard.py'
    spec = importlib.util.spec_from_file_location('m2_guard', path)
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    site = tmp_path / 'site'; build(site, sec_m2_candidate=candidate)
    value = api().project_candidates(candidate)
    mutate(value)
    (site / 'sec-m2-candidates.json').write_text(json.dumps(value))
    for file in site.iterdir():
        data = file.read_bytes()
        if file.suffix == '.json':
            data = json.dumps(json.loads(data), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        guard.APPROVED_SHA256[file.name] = hashlib.sha256(data).hexdigest()
    directory = guard.scan_artifact(site)
    assert directory['pages_artifact_guard'] == 'FAIL'
    assert directory['violations'].get('m2_candidate_boundary', 0) or directory['violations'].get('invalid_format', 0)
    archive = tmp_path / 'site.tar'
    with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as handle:
        for file in sorted(site.iterdir()):
            info = handle.gettarinfo(str(file), arcname='./' + file.name)
            info.uid = info.gid = 0; info.uname = info.gname = ''
            with file.open('rb') as body: handle.addfile(info, body)
    assert guard.validate_pages_tar(archive) == directory


@pytest.mark.parametrize('mutate', [
    lambda c: c['candidate_data']['leaderboard']['data']['rows'][0].update(ticker='wrong'),
    lambda c: c['candidate_data']['leaderboard']['data']['rows'][0].update(qgv_snapshot_id='sec_m2_qgv_'+'e'*64),
    lambda c: c['companies']['asml'].update(publication_eligible=True),
    lambda c: c['candidate_data']['qgv'].update(prices_used=True),
    lambda c: c['candidate_data']['qgv']['data']['asml'].update(standard_status='PRODUCTION'),
])
def test_additional_identity_and_provenance_contradictions(candidate, mutate):
    mutate(candidate)
    with pytest.raises(ValueError, match=r'^M2_CANDIDATE_INVALID$'):
        api().project_candidates(candidate)


def test_unavailable_schema_requires_integer_version():
    result=api().unavailable_candidates();result['version']=True
    with pytest.raises(ValueError, match=r'^M2_CANDIDATE_INVALID$'):
        api().require_public_candidates(result)


@pytest.mark.parametrize('mutate', [
    lambda c: c['candidate_data']['qgv'].update(adapter_synthetic=False),
    lambda c: c['candidate_data']['leaderboard'].update(adapter_synthetic=True),
    lambda c: c['companies']['asml']['source'].update(real_data_verified=True),
    lambda c: c['candidate_data']['leaderboard']['data']['rows'][0].update(calibration='VALIDATED'),
    lambda c: c['candidate_data']['leaderboard']['data']['rows'][0].update(freshness='LIVE'),
    lambda c: c['companies']['asml']['factors']['fundamental_value']['observation'].update(score_0_100=0),
    lambda c: c['candidate_data']['qgv']['data']['asml'].update(v_candidates={'bad':None}),
])
def test_native_known_metadata_contradictions_fail(candidate, mutate):
    mutate(candidate)
    with pytest.raises(ValueError, match=r'^M2_CANDIDATE_INVALID$'):
        api().project_candidates(candidate)


def test_explicit_private_input_cli_projects_and_masks_bad_paths(candidate, tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    tool = Path(__file__).parents[1] / 'tools/build_pages_cockpit.py'
    private = tmp_path / 'private.json'; private.write_text(json.dumps(candidate))
    out = tmp_path / 'site'
    run = subprocess.run([sys.executable, str(tool), '--out', str(out), '--sec-m2-candidate', str(private)], capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads((out / 'sec-m2-candidates.json').read_text()) == api().project_candidates(candidate)
    assert not (out / 'private.json').exists()
    bad = subprocess.run([sys.executable, str(tool), '--out', str(tmp_path / 'bad'), '--sec-m2-candidate', str(tmp_path / 'INVENTED_PATH')], capture_output=True, text=True)
    assert bad.returncode == 1
    assert bad.stdout == '' and bad.stderr.strip() == 'Pages public build failed'
    assert not (tmp_path / 'bad').exists()
