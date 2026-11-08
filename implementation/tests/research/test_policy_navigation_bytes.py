"""Numeric view values must bind to their delivered bytes, without a second serializer."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.research.policy_impact import Invalid, build
from investment_system.research.policy_impact import navigation as nav

ROOT = Path(__file__).parents[2]
FIX = ROOT / 'docs/research/policy_impact'
ALGORITHM = 'SHA256_VIEW_UTF8_BYTES_V1'
NUMERIC_FIX = FIX / 'numeric-navigation-v2'


def numeric_case(value):
    job = json.loads((FIX / 'navigation-synthetic-job.json').read_text())
    bundle = copy.deepcopy(job['view']['bundle'])
    exposure = bundle['exposures'][0]
    exposure['ratio'] = {'value': value, 'unit': 'fraction', 'period': dict(exposure['period']),
                         'scope': 'Synthetic disclosed product scope',
                         'denominator_description': 'Synthetic annual revenue'}
    exposure['reason_codes'] = []
    companies = json.loads((FIX / 'synthetic-job.json').read_text())['company_ids']
    view = build(bundle, companies, job['view']['as_of'], public=True)
    data = copy.deepcopy(job['navigation'])
    originals = {spec['sha256']: (ROOT.parent / spec['path']).read_bytes() for spec in job['title_sources']}
    return view, data, originals, job['as_of']


def wire(data, body):
    data = copy.deepcopy(data)
    data.update(schema_version='policy-impact-navigation-input/2', hash_algorithm=ALGORITHM,
                base_view_hash=hashlib.sha256(body).hexdigest())
    return data


@pytest.mark.parametrize('value', [0, 1, 0.0, 1.0, 0.125, 0.1, 1e-7, 1e-12, 5e-324, -0.0])
def test_numeric_view_keeps_numbers_and_reviewed_title_news_join(value):
    view, data, originals, at = numeric_case(value)
    before = copy.deepcopy(view)
    body = (json.dumps(view, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
    out = nav.project_bytes(body, wire(data, body), at, public=True, title_sources=originals)
    assert out['schema_version'] == 'policy-impact-navigation/2'
    assert out['hash_algorithm'] == ALGORITHM
    assert out['base_view_hash'] == hashlib.sha256(body).hexdigest()
    assert len(out['titles']) == len(out['news_links']) == 1
    assert out['news_links'][0]['evidence_effect'] == 'NONE'
    assert view == before
    ratio = json.loads(body)['bundle']['exposures'][0]['ratio']['value']
    assert type(ratio) is type(value) and ratio == value


def test_wire_hash_rejects_numeric_edits_and_even_same_value_reserialization():
    view, data, originals, at = numeric_case(1e-7)
    body = (json.dumps(view, ensure_ascii=False, indent=2) + '\n').encode()
    config = wire(data, body)
    for changed in (body.replace(b'1e-07', b'2e-07'), body + b' ',
                    body.replace(b'1e-07', b'0.0000001')):
        with pytest.raises(Invalid, match='BASE_VIEW_HASH'):
            nav.project_bytes(changed, config, at, public=True, title_sources=originals)


@pytest.mark.parametrize('body', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                                 b'{"x":1e400}', b'\xff'])
def test_malformed_view_is_not_accepted_even_with_matching_bytes_hash(body):
    _, data, _, at = numeric_case(0)
    with pytest.raises(Invalid, match='VIEW_JSON'):
        nav.project_bytes(body, wire(data, body), at)


def test_hash_versions_are_explicit_and_legacy_navigation_is_unchanged():
    job = json.loads((FIX / 'navigation-synthetic-job.json').read_text())
    originals = {s['sha256']: (ROOT.parent / s['path']).read_bytes() for s in job['title_sources']}
    legacy = nav.project(job['view'], job['navigation'], job['as_of'], public=True, title_sources=originals)
    assert legacy == json.loads((FIX / 'navigation-synthetic-view.json').read_text())
    body = nav.encode_view(job['view'])
    with pytest.raises(Invalid, match='VERSION'):
        nav.project_bytes(body, job['navigation'], job['as_of'])
    config = wire(job['navigation'], body)
    with pytest.raises(Invalid, match='VERSION'):
        nav.project(job['view'], config, job['as_of'])
    config['hash_algorithm'] = 'UNKNOWN'
    with pytest.raises(Invalid, match='HASH_ALGORITHM'):
        nav.project_bytes(body, config, job['as_of'])


def test_byte_binding_keeps_existing_public_permission_gate():
    view, data, originals, at = numeric_case(0.125)
    body = nav.encode_view(view)
    data['titles'][0]['publication_permission'] = 'UNKNOWN'
    data['links'][0]['publication_permission'] = 'UNKNOWN'
    out = nav.project_bytes(body, wire(data, body), at, public=True, title_sources=originals)
    assert out['titles'] == out['news_links'] == []
    private = copy.deepcopy(view); private['schema_version'] = 'policy-impact-view/1'
    body = nav.encode_view(private)
    with pytest.raises(Invalid, match='PUBLIC_VIEW_REQUIRED'):
        nav.project_bytes(body, wire(data, body), at, public=True, title_sources=originals)


def test_existing_cli_reads_exact_view_file_and_keeps_old_output_on_bad_hash(tmp_path):
    view, data, originals, at = numeric_case(1e-12)
    body = (json.dumps(view, ensure_ascii=False, indent=2) + '\n').encode()
    source = tmp_path / 'view.json'; source.write_bytes(body)
    sha = next(iter(originals)); title = tmp_path / 'title.html'; title.write_bytes(originals[sha])
    config = {'mode': 'navigation', 'view_source': {'path': str(source), 'sha256': hashlib.sha256(body).hexdigest()},
              'navigation': wire(data, body), 'as_of': at, 'public': True,
              'title_sources': [{'path': str(title), 'sha256': sha}]}
    job = tmp_path / 'job.json'; output = tmp_path / 'navigation.json'
    def run():
        job.write_text(json.dumps(config))
        return subprocess.run([sys.executable, str(ROOT / 'tools/policy_impact.py'), '--job', str(job),
                               '--output', str(output)], capture_output=True, text=True)
    result = run()
    assert result.returncode == 0, result.stdout
    saved = output.read_bytes()
    assert json.loads(saved)['base_view_hash'] == hashlib.sha256(body).hexdigest()
    source.write_bytes(body + b' ')
    result = run()
    assert result.returncode == 2 and 'SOURCE_HASH' in result.stdout and output.read_bytes() == saved
    source.write_bytes(body); config['view'] = view
    result = run()
    assert result.returncode == 2 and 'VIEW_INPUT_AMBIGUOUS' in result.stdout and output.read_bytes() == saved


@pytest.mark.parametrize('case', json.loads((NUMERIC_FIX / 'manifest.json').read_bytes())['cases'],
                         ids=lambda case: case['case'])
def test_handoff_bytes_hashes_and_joins_remain_reproducible(case):
    view, data, originals, at = numeric_case(case['ratio_value'])
    body = (NUMERIC_FIX / case['view']).read_bytes()
    assert body == nav.encode_view(view)
    for field in ('view', 'navigation', 'job'):
        assert hashlib.sha256((NUMERIC_FIX / case[field]).read_bytes()).hexdigest() == case[field + '_sha256']
    job = json.loads((NUMERIC_FIX / case['job']).read_bytes())
    assert job['view_source'] == {'path': str((NUMERIC_FIX / case['view']).relative_to(ROOT.parent)),
                                   'sha256': case['view_sha256']}
    assert job['navigation'] == wire(data, body)
    result = nav.project_bytes(body, job['navigation'], at, public=True, title_sources=originals)
    assert nav.encode_view(result) == (NUMERIC_FIX / case['navigation']).read_bytes()
    assert len(result['titles']) == case['expected']['titles'] == 1
    assert len(result['news_links']) == case['expected']['news_links'] == 1
    assert result['base_view_hash'] == case['view_sha256']
