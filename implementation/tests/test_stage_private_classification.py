"""stage_private_classification: byte-for-byte staging of the held classification bundle, checked against the manifest.

Synthetic files only (made up here, no company)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import stage_private_classification as stage_tool  # noqa: E402

HASH = 'a' * 64


POLICY = {'version': 'common-sector-boundaries/2026-11-08.1', 'source': 'owner:2026-11-08:common-classification-boundaries',
          'approved_date': '2026-11-08', 'recorded_at': '2026-11-08T08:05:49Z'}


def _bundle(tmp_path, *, view_extra=None, version=1, name='held'):
    src = tmp_path / name
    (src / 'result').mkdir(parents=True)
    files = []
    for part, (rel, schema) in stage_tool.PARTS.items():
        value = {'schema_version': schema, 'note': 'SYNTHETIC'}
        if part != 'dictionary':
            value.update(classification_hash=HASH, valuation_date='2026-11-02')
        if part == 'view':
            value.update(dictionary_version='common-industry-dictionary/%d' % version, mapping_version='common-classification-map/%d' % version)
            if version == 2:
                value['boundary_policy'] = dict(POLICY)
        if part == 'dictionary':
            value['version'] = 'common-industry-dictionary/%d' % version
            if version == 2:
                value['policy'] = {k: POLICY[k] for k in ('version', 'source', 'approved_date')}
        if part == 'view' and view_extra:
            value.update(view_extra)
        # the writer's own spacing; the copy must keep it
        data = json.dumps(value, indent=1, sort_keys=True).encode('utf-8')
        (src / rel).write_bytes(data)
        files.append({'path': rel, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = src / 'handoff-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 'held-classification-private-handoff/1', 'files': files}), encoding='utf-8')
    data_dir = tmp_path / 'data'
    data_dir.mkdir(exist_ok=True)
    return src, manifest, data_dir


def test_stages_every_part_byte_for_byte(tmp_path, capsys):
    src, manifest, data_dir = _bundle(tmp_path)
    assert stage_tool.main(['--source', str(src), '--manifest', str(manifest), '--data-dir', str(data_dir)]) == 0
    for part, (rel, _) in stage_tool.PARTS.items():
        assert (data_dir / 'classification' / (part + '.json')).read_bytes() == (src / rel).read_bytes()
    out = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in out] == ['part=' + p for p in stage_tool.PARTS]
    assert all('SYNTHETIC' not in line for line in out), 'no file content in the output'


@pytest.mark.parametrize('fault, code', [
    ('size', 'MANIFEST_MISMATCH:technical'), ('missing', 'FILE_MISSING:macro'), ('schema', 'SCHEMA_MISMATCH:qgv_links'),
    ('other_records', 'PART_OTHER_RECORDS:technical'), ('not_in_manifest', 'MANIFEST_PART_MISSING:dictionary'),
])
def test_refuses_and_writes_nothing(tmp_path, capsys, fault, code):
    src, manifest, data_dir = _bundle(tmp_path)
    m = json.loads(manifest.read_text())
    if fault == 'size':
        (src / 'result/technical.json').write_bytes(b'{"schema_version": "common-classification-technical/1"}  ')
    elif fault == 'missing':
        (src / 'result/macro.json').unlink()
    elif fault == 'schema':
        p = src / 'result/qgv-classification-links.json'
        data = json.dumps({'schema_version': 'common-classification-view/1', 'classification_hash': HASH, 'valuation_date': '2026-11-02'}).encode()
        p.write_bytes(data)
        for f in m['files']:
            if f['path'].endswith('qgv-classification-links.json'):
                f.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
    elif fault == 'other_records':
        p = src / 'result/technical.json'
        data = json.dumps({'schema_version': 'common-classification-technical/1', 'classification_hash': 'b' * 64, 'valuation_date': '2026-11-02'}).encode()
        p.write_bytes(data)
        for f in m['files']:
            if f['path'].endswith('technical.json'):
                f.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
    elif fault == 'not_in_manifest':
        m['files'] = [f for f in m['files'] if not f['path'].endswith('dictionary.json')]
    manifest.write_text(json.dumps(m))
    assert stage_tool.main(['--source', str(src), '--manifest', str(manifest), '--data-dir', str(data_dir)]) == 1
    assert capsys.readouterr().out.strip() == 'STAGE_PRIVATE_CLASSIFICATION refused=' + code
    assert not (data_dir / 'classification').exists(), 'nothing written before every check passed'


def test_refuses_a_data_dir_inside_the_public_repository(tmp_path, capsys):
    src, manifest, _ = _bundle(tmp_path)
    inside = stage_tool.REPO_ROOT / 'implementation'
    assert stage_tool.main(['--source', str(src), '--manifest', str(manifest), '--data-dir', str(inside)]) == 1
    assert 'DATA_DIR_INSIDE_PUBLIC_REPOSITORY' in capsys.readouterr().out
    assert not (inside / 'classification').exists()


def test_a_policy_version_pair_stages_and_replaces_the_previous_set_whole(tmp_path, capsys):
    src, manifest, data_dir = _bundle(tmp_path)
    assert stage_tool.main(['--source', str(src), '--manifest', str(manifest), '--data-dir', str(data_dir)]) == 0
    src2, manifest2, _ = _bundle(tmp_path, version=2, name='held2')
    assert stage_tool.main(['--source', str(src2), '--manifest', str(manifest2), '--data-dir', str(data_dir)]) == 0
    for part, (rel, _) in stage_tool.PARTS.items():
        assert (data_dir / 'classification' / (part + '.json')).read_bytes() == (src2 / rel).read_bytes()
    assert sorted(p.name for p in data_dir.iterdir()) == ['classification'], 'no staging or previous copy left'


@pytest.mark.parametrize('edit, code', [
    (lambda v, d: v.update(mapping_version='common-classification-map/1'), 'VERSION_PAIR_INVALID'),
    (lambda v, d: v.update(dictionary_version='common-industry-dictionary/3', mapping_version='common-classification-map/3'), 'VERSION_PAIR_INVALID'),
    (lambda v, d: v.pop('boundary_policy'), 'POLICY_VERSION_MISMATCH'),
    (lambda v, d: d.update(version='common-industry-dictionary/1'), 'PART_OTHER_VERSION:dictionary'),
    (lambda v, d: d['policy'].update(version='common-sector-boundaries/2026-11-09.1'), 'POLICY_VERSION_MISMATCH'),
])
def test_a_broken_new_set_keeps_the_existing_connection(tmp_path, capsys, edit, code):
    src, manifest, data_dir = _bundle(tmp_path)
    assert stage_tool.main(['--source', str(src), '--manifest', str(manifest), '--data-dir', str(data_dir)]) == 0
    before = {p.name: p.read_bytes() for p in (data_dir / 'classification').iterdir()}
    capsys.readouterr()
    src2, _, _ = _bundle(tmp_path, version=2, name='held2')
    v, d = (json.loads((src2 / stage_tool.PARTS[k][0]).read_text()) for k in ('view', 'dictionary'))
    edit(v, d)
    files = []
    for k, value in (('view', v), ('dictionary', d)):
        (src2 / stage_tool.PARTS[k][0]).write_bytes(json.dumps(value).encode())
    for part, (rel, _) in stage_tool.PARTS.items():
        data = (src2 / rel).read_bytes()
        files.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (src2 / 'm.json').write_text(json.dumps({'files': files}))
    assert stage_tool.main(['--source', str(src2), '--manifest', str(src2 / 'm.json'), '--data-dir', str(data_dir)]) == 1
    assert capsys.readouterr().out.strip() == 'STAGE_PRIVATE_CLASSIFICATION refused=' + code
    assert {p.name: p.read_bytes() for p in (data_dir / 'classification').iterdir()} == before, 'the existing connection is untouched'
    assert sorted(p.name for p in data_dir.iterdir()) == ['classification']


def _expanded(tmp_path, view_bytes, *, cite=None, name='expanded'):
    """A synthetic expanded summary carrying calculation_counts that cites the staged view (Codex #523 shape, trimmed)."""
    src = tmp_path / name
    (src / 'final').mkdir(parents=True)
    view = json.loads(view_bytes)
    value = {'schema_version': 'held-expanded-classification-summary/1', 'valuation_date': view['valuation_date'],
             'calculation_counts': {'valuation_date': view['valuation_date'], 'scopes': {'operating': {
                 'valuation_date': view['valuation_date'], 'population': {'denominator': len(view.get('rows') or [])},
                 'classification': {'classification_hash': view['classification_hash']},
                 'sources': {'view': {'ref': 'synthetic://view', 'sha256': cite or hashlib.sha256(view_bytes).hexdigest()}}}}}}
    data = json.dumps(value).encode()
    (src / 'final/summary.json').write_bytes(data)
    (src / 'm.json').write_text(json.dumps({'files': [{'path': 'final/summary.json', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}))
    return src, src / 'm.json'


def test_a_counts_summary_must_cite_the_staged_view_bytes(tmp_path, capsys):
    src, manifest, data_dir = _bundle(tmp_path)
    view_bytes = (src / stage_tool.PARTS['view'][0]).read_bytes()
    exp, exp_m = _expanded(tmp_path, view_bytes)
    args = ['--source', str(src), '--manifest', str(manifest), '--data-dir', str(data_dir), '--expanded-source', str(exp), '--expanded-manifest', str(exp_m)]
    assert stage_tool.main(args) == 0
    before = {p.name: p.read_bytes() for p in (data_dir / 'classification').iterdir()}
    capsys.readouterr()
    bad, bad_m = _expanded(tmp_path, view_bytes, cite='e' * 64, name='expanded-bad')
    args = ['--source', str(src), '--manifest', str(manifest), '--data-dir', str(data_dir), '--expanded-source', str(bad), '--expanded-manifest', str(bad_m)]
    assert stage_tool.main(args) == 1
    assert capsys.readouterr().out.strip() == 'STAGE_PRIVATE_CLASSIFICATION refused=COUNTS_VIEW_MISMATCH:expanded_summary'
    assert {p.name: p.read_bytes() for p in (data_dir / 'classification').iterdir()} == before, 'the existing good set stays'
    assert sorted(p.name for p in data_dir.iterdir()) == ['classification']
