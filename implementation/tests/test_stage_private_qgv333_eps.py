"""stage_private_qgv333_eps.py (owner 2026-11-13 「3/3/3 화면 연결 우선」): the producer's three EPS follow-up files staged byte for byte
under classification/dual-333/eps/ with Main's qgv-333-eps-delivery/1 index, only when pinned and consistent; every refusal keeps
the existing copy. The handoff here is test-made (the shape of Codex #534's qgv-333-eps handoff, made-up counts)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_qgv333_eps as tool  # noqa: E402

DAY, AS_OF = '2026-11-04', '2026-11-04T02:29:35Z'


def _docs():
    diag = {k: {'valuation_date': DAY, 'as_of': AS_OF, 'denominator_issuers': 3, 'full_four_year_components': 3, 'adopted_raw': 0} for k in ('operating', 'held')}
    comp = {s: {m: {'stages': {}} for m in ('U2-333', 'U1-333', 'S1-333')} for s in ('operating504', 'held1057')}
    cont = {'schema_version': 'qgv-333-eps-continuation/1', 'valuation_date': DAY, 'retained_as_of': AS_OF, 'new_external_data_requests': 0}
    return {'diagnostic-summary.json': diag, 'run-comparison.json': comp, 'continuation-inputs.json': cont}


def _handoff(tmp_path, edit=None, manifest_edit=None):
    d = tmp_path / 'h'
    d.mkdir()
    docs = _docs()
    if edit:
        edit(docs)
    files = []
    for name, doc in docs.items():
        b = (json.dumps(doc) + '\n').encode()
        (d / name).write_bytes(b)
        files.append({'path': name, 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    m = {'schema_version': 'qgv-333-eps-handoff/1', 'visibility': 'PRIVATE_RESEARCH', 'path': 'handoffs/test', 'producer_sha': '1' * 40,
         'execution_sha': '2' * 40, 'files': files}
    if manifest_edit:
        manifest_edit(m)
    raw = (json.dumps(m, indent=2) + '\n').encode()
    (d / 'handoff-manifest.json').write_bytes(raw)
    data = tmp_path / 'data'
    (data / 'classification').mkdir(parents=True)
    return d, hashlib.sha256(raw).hexdigest(), data


def test_stages_the_three_files_byte_for_byte_with_the_index(tmp_path, capsys):
    h, pin, data = _handoff(tmp_path)
    assert tool.main(['--handoff', str(h), '--handoff-manifest-sha256', pin, '--data-dir', str(data)]) == 0
    out = data / 'classification' / 'dual-333' / 'eps'
    assert sorted(p.name for p in out.iterdir()) == ['continuation-inputs.json', 'diagnostic-summary.json', 'eps-index.json', 'run-comparison.json']
    for n in ('continuation-inputs.json', 'diagnostic-summary.json', 'run-comparison.json'):
        assert (out / n).read_bytes() == (h / n).read_bytes(), 'byte for byte'
    idx = json.loads((out / 'eps-index.json').read_text())
    assert idx['schema_version'] == 'qgv-333-eps-delivery/1' and idx['result_delivery'] is None and idx['new_external_requests'] == 0
    assert idx['source'] == {'handoff_path': 'handoffs/test', 'handoff_manifest_sha256': pin, 'producer_sha': '1' * 40, 'execution_sha': '2' * 40}
    assert idx['files']['comparison']['sha256'] == hashlib.sha256((h / 'run-comparison.json').read_bytes()).hexdigest()
    assert (idx['valuation_date'], idx['input_as_of']) == (DAY, AS_OF)
    assert capsys.readouterr().out.rstrip().endswith('result_delivery=none')


@pytest.mark.parametrize('kind, code', [
    ('pin', 'MANIFEST_PIN_MISMATCH'),
    ('schema', 'MANIFEST_SCHEMA'),
    ('unlisted', 'FILE_NOT_LISTED:run-comparison.json'),
    ('changed', 'FILE_MISMATCH:continuation-inputs.json'),
    ('scope', 'DIAGNOSTIC_SCHEMA'),
    ('model', 'COMPARISON_SCHEMA'),
    ('continuation', 'CONTINUATION_SCHEMA'),
    ('date', 'DATE_MISMATCH'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    edits = {'scope': lambda d: d['diagnostic-summary.json'].update(catalog={}),
             'model': lambda d: d['run-comparison.json']['held1057'].pop('S1-333'),
             'continuation': lambda d: d['continuation-inputs.json'].update(schema_version='x'),
             'date': lambda d: d['diagnostic-summary.json']['held'].update(as_of='2026-11-05T00:00:00Z')}
    medits = {'schema': lambda m: m.update(visibility='PUBLIC'), 'unlisted': lambda m: m.update(files=[f for f in m['files'] if f['path'] != 'run-comparison.json'])}
    h, pin, data = _handoff(tmp_path, edits.get(kind), medits.get(kind))
    if kind == 'changed':
        (h / 'continuation-inputs.json').write_bytes(b'{}\n')
    target = data / 'classification' / 'dual-333' / 'eps'
    target.mkdir(parents=True)
    (target / 'kept.json').write_text('{}')
    with pytest.raises(tool.StageError) as error:
        tool.stage(h, 'c' * 64 if kind == 'pin' else pin, data)
    assert str(error.value) == code
    assert sorted(p.name for p in target.iterdir()) == ['kept.json']


def test_public_data_dir_is_refused(tmp_path):
    h, pin, _ = _handoff(tmp_path)
    with pytest.raises(tool.StageError, match='^DATA_DIR_INSIDE_PUBLIC_REPOSITORY$'):
        tool.stage(h, pin, ROOT)
