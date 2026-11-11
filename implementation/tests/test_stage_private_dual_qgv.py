"""stage_private_dual_qgv.py (owner 2026-11-11): Codex #529's synthetic dual delivery (docs/research/sector_qgv/dual-synthetic, pinned
in its manifest.json) staged byte for byte under classification/dual/<scope>/ only when pinned, complete and tied to the staged
coverage scope; every refusal keeps the existing copy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_dual_qgv as tool  # noqa: E402

SYN = ROOT / 'docs' / 'research' / 'sector_qgv' / 'dual-synthetic'
FILES = ('summary.json', 'index.json', 'detail-000.json')


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _setup(tmp_path, scope='operating504', edit=None, coverage_edit=None):
    pins = {f['path']: f['sha256'] for f in json.loads((SYN / 'manifest.json').read_text())['files']}
    docs = {name: (SYN / name).read_bytes() for name in FILES}
    assert all(_sha(docs[n]) == pins[n] for n in FILES), 'Codex synthetic pins'
    if edit:
        parsed = {n: json.loads(docs[n]) for n in FILES}
        edit(parsed)
        docs = {n: (json.dumps(parsed[n], indent=2) + '\n').encode() for n in FILES}
    delivery = tmp_path / 'delivery'
    delivery.mkdir()
    for n, b in docs.items():
        (delivery / n).write_bytes(b)
    manifest = {'schema_version': 'qgv-dual-delivery-manifest/1', 'data_kind': 'SYNTHETIC', 'scope': scope,
                'files': [{'path': n, 'size': len(docs[n]), 'sha256': _sha(docs[n])} for n in FILES]}
    (delivery / 'manifest.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode())
    summary = json.loads(docs['summary.json'])['boards']['U1']
    ev, ref = summary['evaluation_population'], summary['reference_population']
    scopes = {}
    for key, inp in (('operating', ev['input_hash']), ('held_financial_subsample', ref['input_hash'])):
        scopes[key] = {'context': {'valuation_date': ev['valuation_date'], 'result_identity': {'input_hash': inp},
                                   'population': {'id': ev['id'], 'version': ev['version'], 'members_hash': ev['members_hash'], 'denominator': ev['code_rows']}}}
    if coverage_edit:
        coverage_edit(scopes)
    data = tmp_path / 'data'
    (data / 'classification' / 'expanded').mkdir(parents=True)
    (data / 'classification' / 'expanded' / 'coverage.json').write_text(json.dumps({'scopes': scopes}))
    return delivery, data, _sha((delivery / 'manifest.json').read_bytes())


@pytest.mark.parametrize('scope', ['operating504', 'held1057'])
def test_stages_every_file_byte_for_byte(tmp_path, capsys, scope):
    delivery, data, pin = _setup(tmp_path, scope)
    assert tool.main(['--delivery', str(delivery), '--scope', scope, '--manifest-sha256', pin, '--data-dir', str(data)]) == 0
    out = data / 'classification' / 'dual' / scope
    assert sorted(p.name for p in out.iterdir()) == sorted(FILES + ('manifest.json',))
    for p in delivery.iterdir():
        assert (out / p.name).read_bytes() == p.read_bytes()
    line = capsys.readouterr().out
    assert line.startswith('STAGE_PRIVATE_DUAL_QGV scope=' + scope + ' manifest sha256=' + pin) and 'models=U1,U2,S1 code_rows=3 issuers=3 details=1 files=4' in line
    assert line.rstrip().endswith('input_check=' + ('EVALUATION_INPUT_MATCHED' if scope == 'operating504' else 'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED'))


def _board(name, f):
    def edit(x):
        for k, b in x['summary.json']['boards'].items():
            f(b, k)
    return edit


@pytest.mark.parametrize('kind, code', [
    ('pin', 'MANIFEST_PIN_MISMATCH'),
    ('scope', 'MANIFEST_SCHEMA'),
    ('extra_file', 'FILE_SET_MISMATCH'),
    ('changed_file', 'FILE_MISMATCH:summary.json'),
    ('adopted', 'SUMMARY_SCHEMA'),
    ('model', 'SUMMARY_SCHEMA'),
    ('raw', 'RAW_VALUE_PRESENT:detail-000.json'),
    ('population', 'POPULATION_MISMATCH'),
    ('date', 'DATE_MISMATCH'),
    ('input', 'INPUT_MISMATCH:U1'),
    ('no_coverage', 'COVERAGE_NOT_STAGED'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    edit = None
    if kind == 'adopted':
        edit = _board('adopted', lambda b, k: b.update(operating_adoption='ADOPTED') if k == 'S1' else None)
    elif kind == 'model':
        edit = _board('model', lambda b, k: b.update(model_id='unified-roa-core/0.1.0') if k == 'U2' else None)
    elif kind == 'raw':
        def edit(x):
            next(iter(x['detail-000.json']['rows'][0]['boards']['U1']['factors'].values()))['raw_value'] = 0.1
    cov = None
    if kind == 'population':
        def cov(s):
            s['operating']['context']['population']['members_hash'] = 'a' * 64
    elif kind == 'date':
        def cov(s):
            s['operating']['context']['valuation_date'] = '2026-11-04'
    elif kind == 'input':
        def cov(s):
            s['operating']['context']['result_identity']['input_hash'] = 'b' * 64
    delivery, data, pin = _setup(tmp_path, edit=edit, coverage_edit=cov)
    old = data / 'classification' / 'dual' / 'operating504'
    old.mkdir(parents=True)
    (old / 'kept.json').write_text('{}')
    scope = 'operating504'
    if kind == 'pin':
        pin = 'c' * 64
    elif kind == 'scope':
        scope = 'held1057'
    elif kind == 'extra_file':
        (delivery / 'coverage.json').write_text('{}')
    elif kind == 'changed_file':
        (delivery / 'summary.json').write_bytes((delivery / 'summary.json').read_bytes() + b' ')
    elif kind == 'no_coverage':
        (data / 'classification' / 'expanded' / 'coverage.json').unlink()
    with pytest.raises(tool.StageError) as error:
        tool.stage(delivery, scope, pin, data)
    assert str(error.value) == code
    assert (old / 'kept.json').read_text() == '{}' and sorted(p.name for p in old.iterdir()) == ['kept.json']


def test_held_scope_is_tied_by_the_reference_input_not_the_evaluation_projection(tmp_path):
    def cov(s):
        s['held_financial_subsample']['context']['result_identity']['input_hash'] = s['operating']['context']['result_identity']['input_hash']
    delivery, data, pin = _setup(tmp_path, 'held1057', coverage_edit=cov)
    with pytest.raises(tool.StageError, match='^INPUT_MISMATCH:U1$'):
        tool.stage(delivery, 'held1057', pin, data)


def test_public_data_dir_and_unknown_scope_are_refused(tmp_path):
    delivery, data, pin = _setup(tmp_path)
    with pytest.raises(tool.StageError, match='^DATA_DIR_INSIDE_PUBLIC_REPOSITORY$'):
        tool.stage(delivery, 'operating504', pin, ROOT)
    with pytest.raises(tool.StageError, match='^SCOPE_UNKNOWN$'):
        tool.check(delivery, 'market', pin, data)
