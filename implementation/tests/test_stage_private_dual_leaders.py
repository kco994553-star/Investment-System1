"""stage_private_dual_leaders.py (owner 2026-11-11): Codex's synthetic factor leaders companion (docs/research/sector_qgv/
dual-factor-leaders-synthetic, whose manifest pins Codex's synthetic delivery manifest dual-synthetic/delivery-manifest.json) staged
byte for byte under classification/dual/<scope>/leaders/ only beside that very delivery; every refusal keeps the existing copy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_dual_leaders as tool  # noqa: E402

SYN = ROOT / 'docs' / 'research' / 'sector_qgv'
DELIVERY = ('summary.json', 'index.json', 'detail-000.json')
LEADERS = ('factor-leaders-manifest.json', 'factor-leaders.json', 'factor-leaders-000.json')


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _setup(tmp_path, edit=None, manifest_edit=None):
    data = tmp_path / 'data'
    staged = data / 'classification' / 'dual' / 'operating504'
    staged.mkdir(parents=True)
    for name in DELIVERY:
        shutil.copyfile(SYN / 'dual-synthetic' / name, staged / name)
    shutil.copyfile(SYN / 'dual-synthetic' / 'delivery-manifest.json', staged / 'manifest.json')
    leaders = tmp_path / 'leaders'
    leaders.mkdir()
    docs = {n: (SYN / 'dual-factor-leaders-synthetic' / n).read_bytes() for n in LEADERS}
    if edit:
        parsed = {n: json.loads(docs[n]) for n in LEADERS[1:]}
        edit(parsed)
        for n in LEADERS[1:]:
            docs[n] = (json.dumps(parsed[n], indent=2) + '\n').encode()
        m = json.loads(docs[LEADERS[0]])
        m['files'] = [{'path': n, 'size': len(docs[n]), 'sha256': _sha(docs[n])} for n in sorted(LEADERS[1:])]
        docs[LEADERS[0]] = (json.dumps(m, indent=2) + '\n').encode()
    if manifest_edit:
        m = json.loads(docs[LEADERS[0]])
        manifest_edit(m)
        docs[LEADERS[0]] = (json.dumps(m, indent=2) + '\n').encode()
    for n, b in docs.items():
        (leaders / n).write_bytes(b)
    return leaders, data, _sha(docs[LEADERS[0]])


def test_codex_synthetic_companion_is_staged_beside_its_delivery(tmp_path, capsys):
    leaders, data, pin = _setup(tmp_path)
    assert pin == _sha((SYN / 'dual-factor-leaders-synthetic' / LEADERS[0]).read_bytes()), 'unedited Codex bytes'
    assert tool.main(['--leaders', str(leaders), '--scope', 'operating504', '--manifest-sha256', pin, '--data-dir', str(data)]) == 0
    out = data / 'classification' / 'dual' / 'operating504' / 'leaders'
    assert sorted(p.name for p in out.iterdir()) == sorted(LEADERS)
    for n in LEADERS:
        assert (out / n).read_bytes() == (leaders / n).read_bytes()
    line = capsys.readouterr().out
    assert line.startswith('STAGE_PRIVATE_DUAL_LEADERS scope=operating504 manifest sha256=' + pin) and ' groups=153 shards=1 files=3 ' in line


@pytest.mark.parametrize('kind, code', [
    ('pin', 'MANIFEST_PIN_MISMATCH'),
    ('scope', 'MANIFEST_SCHEMA'),
    ('other_delivery', 'SOURCE_DELIVERY_MISMATCH'),
    ('no_delivery', 'DELIVERY_NOT_STAGED'),
    ('extra_file', 'FILE_SET_MISMATCH'),
    ('changed_file', 'FILE_MISMATCH:factor-leaders.json'),
    ('recalculated', 'NOT_PROJECTION'),
    ('whole_market', 'NOT_PROJECTION'),
    ('board', 'BOARD_MISMATCH:U1'),
    ('raw', 'RAW_VALUE_PRESENT:factor-leaders-000.json'),
    ('shard_schema', 'SHARD_SCHEMA:factor-leaders-000.json'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    edit = manifest_edit = None
    if kind == 'recalculated':
        def edit(x):
            x['factor-leaders.json']['rank_recalculated'] = True
    elif kind == 'whole_market':
        def edit(x):
            x['factor-leaders.json']['whole_market_denominator'] = 8004
    elif kind == 'board':
        def edit(x):
            x['factor-leaders.json']['boards']['U1']['result_hash'] = 'a' * 64
    elif kind == 'raw':
        def edit(x):
            x['factor-leaders-000.json']['groups'][0]['leaders'][0]['raw_value'] = 0.1
    elif kind == 'shard_schema':
        def edit(x):
            x['factor-leaders-000.json']['schema_version'] = 'qgv-dual-detail/1'
    elif kind == 'other_delivery':
        def manifest_edit(m):
            m['source_delivery_manifest_sha256'] = 'b' * 64
    leaders, data, pin = _setup(tmp_path, edit, manifest_edit)
    target = data / 'classification' / 'dual' / 'operating504' / 'leaders'
    target.mkdir()
    (target / 'kept.json').write_text('{}')
    scope = 'operating504'
    if kind == 'pin':
        pin = 'c' * 64
    elif kind == 'scope':
        scope = 'held1057'
        (data / 'classification' / 'dual' / 'held1057').mkdir()
        for n in ('manifest.json', 'summary.json'):
            shutil.copyfile(data / 'classification' / 'dual' / 'operating504' / n, data / 'classification' / 'dual' / 'held1057' / n)
    elif kind == 'no_delivery':
        (data / 'classification' / 'dual' / 'operating504' / 'manifest.json').unlink()
    elif kind == 'extra_file':
        (leaders / 'factor-leaders-001.json').write_text('{}')
    elif kind == 'changed_file':
        (leaders / 'factor-leaders.json').write_bytes((leaders / 'factor-leaders.json').read_bytes() + b' ')
    with pytest.raises(tool.StageError) as error:
        tool.stage(leaders, scope, pin, data)
    assert str(error.value) == code
    assert sorted(p.name for p in target.iterdir()) == ['kept.json']


def test_public_data_dir_is_refused(tmp_path):
    leaders, data, pin = _setup(tmp_path)
    with pytest.raises(tool.StageError, match='^DATA_DIR_INSIDE_PUBLIC_REPOSITORY$'):
        tool.stage(leaders, 'operating504', pin, ROOT)
