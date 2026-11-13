"""stage_private_dual_bins.py (owner 2026-11-12): Codex's synthetic all-bin routing (docs/research/sector_qgv/dual-bin-synthetic, each
case's bin-manifest pinned in cases.json) staged byte for byte under classification/dual/<scope>/bins/ only beside the very
distribution it routes (its source manifest pin); every refusal keeps the existing copy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_dual_bins as tool  # noqa: E402

BD = ROOT / 'docs' / 'research' / 'sector_qgv' / 'dual-bin-synthetic'
CASES = {c['output']: c for c in json.loads((BD / 'cases.json').read_text())['cases']}


def _dump(x) -> bytes:
    return (json.dumps(x, indent=2, ensure_ascii=False) + '\n').encode()


def _setup(tmp_path, case='all_ten-stored', edit=None):
    c = CASES[case]
    data = tmp_path / 'data'
    dist = data / 'classification' / 'dual' / 'operating504' / 'distribution'
    shutil.copytree((BD / c['source']).resolve(), dist)
    src = tmp_path / 'bins'
    shutil.copytree(BD / c['output'], src)
    if edit:
        docs = {p.name: json.loads(p.read_bytes()) for p in src.iterdir() if p.name != tool.MANIFEST}
        m = json.loads((src / tool.MANIFEST).read_bytes())
        edit(docs, m)
        for name, x in docs.items():
            (src / name).write_bytes(_dump(x))
        m['files'] = [{'path': n, 'size': (src / n).stat().st_size, 'sha256': hashlib.sha256((src / n).read_bytes()).hexdigest()} for n in sorted(docs)]
        (src / tool.MANIFEST).write_bytes(_dump(m))
    return src, data, hashlib.sha256((src / tool.MANIFEST).read_bytes()).hexdigest()


@pytest.mark.parametrize('case', sorted(CASES))
def test_codex_routing_is_staged_beside_its_distribution(tmp_path, capsys, case):
    src, data, pin = _setup(tmp_path, case)
    assert pin == CASES[case]['manifest_sha256'], 'unedited Codex bytes'
    assert tool.main(['--bins', str(src), '--scope', 'operating504', '--manifest-sha256', pin, '--data-dir', str(data)]) == 0
    out = data / 'classification' / 'dual' / 'operating504' / 'bins'
    assert sorted(p.name for p in out.iterdir()) == sorted(p.name for p in src.iterdir())
    for p in src.iterdir():
        assert (out / p.name).read_bytes() == p.read_bytes()
    assert capsys.readouterr().out.startswith('STAGE_PRIVATE_DUAL_BINS scope=operating504 manifest sha256=' + pin)


@pytest.mark.parametrize('kind, code', [
    ('pin', 'MANIFEST_PIN_MISMATCH'),
    ('scope', 'MANIFEST_SCHEMA'),
    ('other_distribution', 'SOURCE_DISTRIBUTION_MISMATCH'),
    ('other_boards', 'SOURCE_DISTRIBUTION_MISMATCH'),
    ('no_distribution', 'DISTRIBUTION_NOT_STAGED'),
    ('extra_file', 'FILE_SET_MISMATCH'),
    ('changed_file', 'FILE_MISMATCH:bin-index.json'),
    ('recalculated', 'NOT_PROJECTION'),
    ('routes', 'ROUTES_INVALID'),
    ('part_group', 'PART_GROUP_MISMATCH:bins-000.json'),
    ('member_file', 'MEMBER_FILE_MISMATCH:bins-000.json'),
    ('member_file_duplicate', 'MEMBER_FILE_MISMATCH:bins-000.json'),
    ('member_file_missing', 'MEMBER_FILE_MISMATCH:bins-000.json'),
    ('raw', 'RAW_VALUE_PRESENT:bins-000.json'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    edit = None
    if kind == 'scope':
        def edit(d, m):
            m['scope'] = 'held1057'
    elif kind == 'other_distribution':
        def edit(d, m):
            m['source_manifest_sha256'] = 'a' * 64
    elif kind == 'other_boards':
        def edit(d, m):
            d[tool.INDEX]['boards']['U1']['result_hash'] = 'b' * 64
    elif kind == 'recalculated':
        def edit(d, m):
            d[tool.INDEX]['new_score_calculations'] = 1
    elif kind == 'routes':
        def edit(d, m):
            d[tool.INDEX]['groups'] = []
    elif kind == 'part_group':
        def edit(d, m):
            d['bins-000.json']['groups'] = []
    elif kind == 'member_file':
        def edit(d, m):
            d['bins-000.json']['groups'][0]['bins'][0]['member_files'][0]['sha256'] = 'c' * 64
    elif kind == 'member_file_duplicate':
        def edit(d, m):
            b = next(x for x in d['bins-000.json']['groups'][0]['bins'] if x['member_files'])
            b['member_files'].append(dict(b['member_files'][0]))
    elif kind == 'member_file_missing':
        def edit(d, m):
            next(x for x in d['bins-000.json']['groups'][0]['bins'] if x['member_files'])['member_files'] = []
    elif kind == 'raw':
        def edit(d, m):
            d['bins-000.json']['groups'][0]['raw_value'] = 0.1
    src, data, pin = _setup(tmp_path, edit=edit)
    target = data / 'classification' / 'dual' / 'operating504' / 'bins'
    target.mkdir()
    (target / 'kept.json').write_text('{}')
    if kind == 'pin':
        pin = 'c' * 64
    elif kind == 'no_distribution':
        (data / 'classification' / 'dual' / 'operating504' / 'distribution' / 'distribution-manifest.json').unlink()
    elif kind == 'extra_file':
        (src / 'bins-001.json').write_text('{}')
    elif kind == 'changed_file':
        (src / tool.INDEX).write_bytes((src / tool.INDEX).read_bytes() + b' ')
    with pytest.raises(tool.StageError) as error:
        tool.stage(src, 'operating504', pin, data)
    assert str(error.value) == code
    assert sorted(p.name for p in target.iterdir()) == ['kept.json']


def test_public_data_dir_is_refused(tmp_path):
    src, data, pin = _setup(tmp_path)
    with pytest.raises(tool.StageError, match='^DATA_DIR_INSIDE_PUBLIC_REPOSITORY$'):
        tool.stage(src, 'operating504', pin, ROOT)
