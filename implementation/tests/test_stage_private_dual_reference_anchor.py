"""stage_private_dual_reference_anchor.py (owner 2026-11-12): an independent reference anchor (qgv-dual-reference-anchor/1, the shape
of Codex's private operating-reference-anchor.json; test-made over Codex's synthetic dual delivery, whose set has no anchor) staged
byte for byte only when every staged board's reference binding and candidate population are its expected identity and the staged
#528 view has the SHA it names; every refusal keeps the existing copy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_dual_reference_anchor as tool  # noqa: E402

SYN = ROOT / 'docs' / 'research' / 'sector_qgv' / 'dual-synthetic'


def _dump(x) -> bytes:
    return (json.dumps(x, indent=2, ensure_ascii=False) + '\n').encode()


def _setup(tmp_path, edit=None, summary_edit=None):
    data = tmp_path / 'data'
    staged = data / 'classification' / 'dual' / 'operating504'
    staged.mkdir(parents=True)
    shutil.copyfile(SYN / 'delivery-manifest.json', staged / 'manifest.json')
    summary = json.loads((SYN / 'summary.json').read_bytes())
    if summary_edit:
        summary_edit(summary)
    (staged / 'summary.json').write_bytes(_dump(summary))
    expected = json.loads((SYN / 'summary.json').read_bytes())['boards']['U1']['bindings']['reference']
    view = {'schema_version': 'sector-qgv-reference-view/1', 'reference_population': {'input_hash': expected['input_hash']}}
    (data / 'classification' / 'expanded').mkdir(parents=True)
    (data / 'classification' / 'expanded' / 'reference-view.json').write_bytes(_dump(view))
    x = {'schema_version': 'qgv-dual-reference-anchor/1', 'scope': 'operating504', 'expected_reference': expected,
         'source_snapshot_sha256': 'a' * 64, 'source_reference_view_sha256': hashlib.sha256(_dump(view)).hexdigest(),
         'source_reference_view_path': 'accepted/reference-view.json', 'source_reference_view_input_hash_field': 'reference_population.input_hash',
         'source_reference_view_members_not_interchangeable': True, 'source_original_catalog_binding': {'id': 'SYN-CATALOG'},
         'matches_all_dual_boards': True, 'eligible_members_are_not_candidate_members': True, 'old_selected_reference_rows': 3,
         'candidate_rows': expected['code_rows'], 'generation_rule': 'synthetic', 'new_score_calculations': 0}
    if edit:
        edit(x)
    anchor = tmp_path / 'operating-reference-anchor.json'
    anchor.write_bytes(_dump(x))
    return anchor, data, hashlib.sha256(anchor.read_bytes()).hexdigest()


def test_anchor_is_staged_beside_its_delivery(tmp_path, capsys):
    anchor, data, pin = _setup(tmp_path)
    assert tool.main(['--anchor', str(anchor), '--anchor-sha256', pin, '--data-dir', str(data)]) == 0
    out = data / 'classification' / 'dual' / 'operating504' / 'reference-anchor.json'
    assert out.read_bytes() == anchor.read_bytes()
    assert capsys.readouterr().out.startswith('STAGE_PRIVATE_DUAL_REFERENCE_ANCHOR scope=operating504 anchor sha256=' + pin)


@pytest.mark.parametrize('kind, code', [
    ('pin', 'ANCHOR_PIN_MISMATCH'),
    ('scope', 'ANCHOR_SCHEMA'),
    ('new_score', 'ANCHOR_SCHEMA'),
    ('rows', 'ANCHOR_SCHEMA'),
    ('input', 'ANCHOR_MISMATCH:U1'),
    ('members', 'ANCHOR_MISMATCH:U1'),
    ('board_moved', 'ANCHOR_MISMATCH:S1'),
    ('view', 'REFERENCE_VIEW_MISMATCH'),
    ('no_view', 'REFERENCE_VIEW_NOT_STAGED'),
    ('no_delivery', 'DELIVERY_NOT_STAGED'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    edit = summary_edit = None
    if kind == 'scope':
        def edit(x):
            x['scope'] = 'held1057'
    elif kind == 'new_score':
        def edit(x):
            x['new_score_calculations'] = 1
    elif kind == 'rows':
        def edit(x):
            x['candidate_rows'] += 1
    elif kind == 'input':
        def edit(x):
            x['expected_reference']['input_hash'] = 'f' * 64
    elif kind == 'members':
        def edit(x):
            x['expected_reference']['members_hash'] = 'f' * 64
    elif kind == 'board_moved':
        def summary_edit(s):
            s['boards']['S1']['bindings']['reference']['input_hash'] = 'e' * 64
    elif kind == 'view':
        def edit(x):
            x['source_reference_view_sha256'] = 'b' * 64
    anchor, data, pin = _setup(tmp_path, edit, summary_edit)
    target = data / 'classification' / 'dual' / 'operating504' / 'reference-anchor.json'
    target.write_text('{"kept":true}')
    if kind == 'pin':
        pin = 'c' * 64
    elif kind == 'no_view':
        (data / 'classification' / 'expanded' / 'reference-view.json').unlink()
    elif kind == 'no_delivery':
        (data / 'classification' / 'dual' / 'operating504' / 'summary.json').unlink()
    with pytest.raises(tool.StageError) as error:
        tool.stage(anchor, pin, data)
    assert str(error.value) == code
    assert target.read_text() == '{"kept":true}'


def test_public_data_dir_is_refused(tmp_path):
    anchor, data, pin = _setup(tmp_path)
    with pytest.raises(tool.StageError, match='^DATA_DIR_INSIDE_PUBLIC_REPOSITORY$'):
        tool.stage(anchor, pin, ROOT)
