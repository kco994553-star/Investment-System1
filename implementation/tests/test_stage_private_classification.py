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


def _bundle(tmp_path, *, view_extra=None):
    src = tmp_path / 'held'
    (src / 'result').mkdir(parents=True)
    files = []
    for part, (rel, schema) in stage_tool.PARTS.items():
        value = {'schema_version': schema, 'note': 'SYNTHETIC'}
        if part != 'dictionary':
            value.update(classification_hash=HASH, valuation_date='2026-11-02')
        if part == 'view' and view_extra:
            value.update(view_extra)
        # the writer's own spacing; the copy must keep it
        data = json.dumps(value, indent=1, sort_keys=True).encode('utf-8')
        (src / rel).write_bytes(data)
        files.append({'path': rel, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = tmp_path / 'handoff-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 'held-classification-private-handoff/1', 'files': files}), encoding='utf-8')
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
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
