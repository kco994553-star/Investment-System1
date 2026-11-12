"""stage_private_dual_distribution.py (owner 2026-11-12): Codex's synthetic full factor distribution (docs/research/sector_qgv/
dual-distribution-synthetic, each case's manifest pinned in cases.json) staged byte for byte under classification/dual/<scope>/
distribution/ only beside a delivery with the same boards and companies; every refusal keeps the existing copy. The staged delivery
here is test-made from the case's own index (boards and companies), the only parts of a delivery the tool reads."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_dual_distribution as tool  # noqa: E402

SYN = ROOT / 'docs' / 'research' / 'sector_qgv' / 'dual-distribution-synthetic'
CASES = {c['case_id']: c for c in json.loads((SYN / 'cases.json').read_text())['cases']}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dump(x) -> bytes:
    return (json.dumps(x, indent=2, ensure_ascii=False) + '\n').encode()


def _setup(tmp_path, case='all_ten-stored', edit=None, delivery_edit=None):
    src = tmp_path / 'distribution'
    shutil.copytree(SYN / CASES[case]['output'], src)
    if edit:
        docs = {p.name: json.loads(p.read_bytes()) for p in src.iterdir() if p.name != tool.MANIFEST}
        m = json.loads((src / tool.MANIFEST).read_bytes())
        edit(docs, m)
        for name, x in docs.items():
            (src / name).write_bytes(_dump(x))
        m['files'] = [{'path': n, 'size': (src / n).stat().st_size, 'sha256': _sha((src / n).read_bytes())} for n in sorted(docs)]
        (src / tool.MANIFEST).write_bytes(_dump(m))
    index = json.loads((SYN / CASES[case]['output'] / tool.INDEX).read_bytes())
    boards = {k: {f: v for f, v in b.items() if f != 'source_result_sha256'} for k, b in index['boards'].items()}
    delivery = {'manifest.json': {'schema_version': 'qgv-dual-delivery-manifest/1', 'scope': 'operating504', 'data_kind': 'SYNTHETIC', 'files': []},
                'summary.json': {'schema_version': 'qgv-dual-delivery/1', 'boards': boards},
                'index.json': {'schema_version': 'qgv-dual-index/1', 'rows': [dict(c, boards={}) for c in index['companies']]}}
    if delivery_edit:
        delivery_edit(delivery)
    data = tmp_path / 'data'
    staged = data / 'classification' / 'dual' / 'operating504'
    staged.mkdir(parents=True)
    for name, x in delivery.items():
        (staged / name).write_bytes(_dump(x))
    return src, data, _sha((src / tool.MANIFEST).read_bytes())


def test_codex_synthetic_distribution_is_staged_beside_its_delivery(tmp_path, capsys):
    src, data, pin = _setup(tmp_path)
    assert pin == CASES['all_ten-stored']['manifest_sha256'], 'unedited Codex bytes'
    assert tool.main(['--distribution', str(src), '--scope', 'operating504', '--manifest-sha256', pin, '--data-dir', str(data)]) == 0
    out = data / 'classification' / 'dual' / 'operating504' / 'distribution'
    assert sorted(p.name for p in out.iterdir()) == sorted(p.name for p in src.iterdir())
    for p in src.iterdir():
        assert (out / p.name).read_bytes() == p.read_bytes()
    line = capsys.readouterr().out
    assert line.startswith('STAGE_PRIVATE_DUAL_DISTRIBUTION scope=operating504 manifest sha256=' + pin + ' policy=stored-evaluation-deciles/1')
    assert ' groups=1 companies=20 parts=1 files=3 ' in line


def test_two_sector_groups_stage_as_delivered(tmp_path):
    src, data, pin = _setup(tmp_path, 'sector_groups-stored')
    tool.stage(src, 'operating504', pin, data)
    assert (data / 'classification' / 'dual' / 'operating504' / 'distribution' / tool.INDEX).read_bytes() == (src / tool.INDEX).read_bytes()


@pytest.mark.parametrize('kind, code', [
    ('pin', 'MANIFEST_PIN_MISMATCH'),
    ('candidate', 'POLICY_NOT_CONFIRMED'),
    ('scope', 'MANIFEST_SCHEMA'),
    ('no_delivery', 'DELIVERY_NOT_STAGED'),
    ('other_result', 'BOARD_MISMATCH:U1'),
    ('other_date', 'BOARD_MISMATCH:U1'),
    ('source', 'SOURCE_RESULT_MISMATCH:U1'),
    ('companies', 'COMPANIES_MISMATCH'),
    ('extra_file', 'FILE_SET_MISMATCH'),
    ('changed_file', 'FILE_MISMATCH:distribution-index.json'),
    ('recalculated', 'NOT_PROJECTION'),
    ('filter', 'NOT_PROJECTION'),
    ('raw', 'RAW_VALUE_PRESENT:distribution-000.json'),
    ('part_schema', 'PART_SCHEMA:distribution-000.json'),
    ('part_group', 'PART_GROUP_MISMATCH:distribution-000.json'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    edit = delivery_edit = None
    case = 'all_ten-stored'
    if kind == 'candidate':
        case = 'all_ten-reference-candidate'
    elif kind == 'scope':
        def edit(docs, m):
            m['scope'] = 'held1057'
    elif kind == 'other_result':
        def delivery_edit(x):
            x['summary.json']['boards']['U1']['result_hash'] = 'a' * 64
    elif kind == 'other_date':
        def delivery_edit(x):
            x['summary.json']['boards']['U1']['evaluation_population']['valuation_date'] = '2026-11-05'
    elif kind == 'source':
        def edit(docs, m):
            m['source_results']['U1']['sha256'] = 'b' * 64
    elif kind == 'companies':
        def delivery_edit(x):
            x['index.json']['rows'].pop()
    elif kind == 'recalculated':
        def edit(docs, m):
            docs[tool.INDEX]['rank_recalculated'] = True
    elif kind == 'filter':
        def edit(docs, m):
            docs[tool.INDEX]['filter_changes_population'] = True
    elif kind == 'raw':
        def edit(docs, m):
            docs['distribution-000.json']['parts'][0]['rows'][0]['raw_value'] = 0.1
    elif kind == 'part_schema':
        def edit(docs, m):
            docs['distribution-000.json']['schema_version'] = 'qgv-dual-detail/1'
    elif kind == 'part_group':
        def edit(docs, m):
            docs['distribution-000.json']['parts'][0]['group_id'] = 'U1|COMMON|other'
    src, data, pin = _setup(tmp_path, case, edit, delivery_edit)
    target = data / 'classification' / 'dual' / 'operating504' / 'distribution'
    target.mkdir()
    (target / 'kept.json').write_text('{}')
    if kind == 'pin':
        pin = 'c' * 64
    elif kind == 'no_delivery':
        (data / 'classification' / 'dual' / 'operating504' / 'summary.json').unlink()
    elif kind == 'extra_file':
        (src / 'distribution-001.json').write_text('{}')
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
