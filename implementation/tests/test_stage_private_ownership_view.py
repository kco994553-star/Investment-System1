"""stage_private_ownership_view.py (owner 2026-11-13): Codex #531 relationship views staged byte for byte under classification/ownership/
with Main's index (company-ownership-delivery/1) for the authenticated delivery; refresh receipts bound to their view's bytes and
times; every refusal keeps the existing copy. Views are Codex's consumer cases (consumer-synthetic.json) written as test-made
handoffs (the producer's canonical bytes and a handoff manifest naming them)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import stage_private_ownership_view as tool  # noqa: E402

CX = {c['case_id']: c for c in json.loads((ROOT / 'docs' / 'research' / 'company_ownership' / 'consumer-synthetic.json').read_text())['cases']}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _handoff(tmp_path, name, view, *, listed=True, raw=None):
    d = tmp_path / name
    d.mkdir()
    data = raw if raw is not None else tool.canonical(view)
    (d / 'view.json').write_bytes(data)
    files = [{'path': 'view.json', 'bytes': len(data), 'sha256': _sha(data)}] if listed else []
    m = (json.dumps({'path': 'handoffs/' + name, 'files': files, 'new_external_requests': 0}, indent=2) + '\n').encode()
    (d / 'handoff-manifest.json').write_bytes(m)
    return d, _sha(m)


def _receipt(tmp_path, name, r):
    p = tmp_path / name
    p.write_bytes((json.dumps(r, indent=2) + '\n').encode())
    return p, _sha(p.read_bytes())


def test_codex_views_and_receipt_are_staged_with_the_index(tmp_path, capsys):
    a = CX['refresh_failed']
    h1 = _handoff(tmp_path, 'a', a['expected_view'])
    b = json.loads(json.dumps(CX['incoming_holder']['expected_view']))
    h2 = _handoff(tmp_path, 'b', b)
    r = _receipt(tmp_path, 'receipt.json', a['refresh'])
    data = tmp_path / 'data'
    assert tool.main(['--handoff', str(h1[0]), '--handoff-manifest-sha256', h1[1], '--handoff', str(h2[0]), '--handoff-manifest-sha256', h2[1],
                      '--receipt', str(r[0]), '--receipt-sha256', r[1], '--data-dir', str(data), '--synthetic']) == 0
    out = data / 'classification' / 'ownership'
    idx = json.loads((out / 'ownership-index.json').read_bytes())
    assert idx['schema_version'] == 'company-ownership-delivery/1' and idx['data_kind'] == 'SYNTHETIC' and idx['new_external_requests'] == 0
    assert [v['entity_id'] for v in idx['views']] == ['SYN-A', 'SYN-B']
    a_bytes = (h1[0] / 'view.json').read_bytes()
    assert (out / 'views' / 'SYN-A.json').read_bytes() == a_bytes, 'byte for byte'
    assert _sha(a_bytes) == a['expected_view_sha256'], 'the producer\'s canonical view bytes'
    assert idx['views'][0]['view'] == {'size': len(a_bytes), 'sha256': _sha(a_bytes)} and idx['views'][0]['company_ids'] == ['SYN:A', 'SYN:A2']
    assert idx['views'][0]['receipt'] == {'size': r[0].stat().st_size, 'sha256': r[1]} and idx['views'][1]['receipt'] is None
    assert (out / 'receipts' / 'SYN-A.json').read_bytes() == r[0].read_bytes()
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()) == ['ownership-index.json', 'receipts/SYN-A.json', 'views/SYN-A.json', 'views/SYN-B.json']
    assert capsys.readouterr().out.startswith('STAGE_PRIVATE_OWNERSHIP_VIEW kind=SYNTHETIC views=2 receipts=1 ')


@pytest.mark.parametrize('kind, code', [
    ('pin', 'MANIFEST_PIN_MISMATCH'),
    ('unlisted', 'VIEW_NOT_LISTED'),
    ('not_canonical', 'VIEW_NOT_CANONICAL'),
    ('schema', 'VIEW_SCHEMA'),
    ('real_publication', 'VIEW_PUBLICATION'),
    ('centre', 'VIEW_CENTRE'),
    ('no_company', 'VIEW_COMPANY_IDS'),
    ('same_centre', 'DUPLICATE_CENTRE:SYN-A'),
    ('receipt_pin', 'RECEIPT_PIN_MISMATCH'),
    ('receipt_other_view', 'RECEIPT_VIEW_MISMATCH'),
    ('receipt_time', 'RECEIPT_TIME'),
    ('receipt_date_only', 'RECEIPT_TIME:attempted_at'),
    ('receipt_no_zone', 'RECEIPT_TIME:attempted_at'),
    ('receipt_dataset', 'RECEIPT_DATASET_MISMATCH'),
    ('receipt_changed_time', 'RECEIPT_VIEW_MISMATCH'),
    ('receipt_extra_key', 'RECEIPT_SCHEMA'),
    ('receipt_outcome', 'RECEIPT_SCHEMA'),
    ('two_receipts', 'DUPLICATE_RECEIPT:SYN-A'),
])
def test_refusals_keep_the_existing_copy(tmp_path, kind, code):
    a = CX['refresh_failed']
    view = json.loads(json.dumps(a['expected_view']))
    receipt = json.loads(json.dumps(a['refresh']))
    synthetic, handoffs, receipts = True, [], []
    if kind == 'schema':
        view['schema_version'] = 'company-ownership-view/2'
    elif kind == 'real_publication':
        synthetic = False
    elif kind == 'centre':
        view['entity_context']['entity_id'] = 'syn-a'
    elif kind == 'no_company':
        for e in view['entities']:
            if e['entity_id'] == 'SYN-A':
                e['company_ids'] = []
    if kind == 'not_canonical':
        h = _handoff(tmp_path, 'a', view, raw=(json.dumps(view, indent=1) + '\n').encode())
    else:
        h = _handoff(tmp_path, 'a', view, listed=kind != 'unlisted')
    handoffs.append((h[0], 'c' * 64 if kind == 'pin' else h[1]))
    if kind == 'same_centre':
        handoffs.append(_handoff(tmp_path, 'b', CX['reviewed_scope']['expected_view']))
    if kind.startswith('receipt') or kind == 'two_receipts':
        if kind == 'receipt_other_view':
            receipt['retained_view_sha256'] = 'd' * 64
        elif kind == 'receipt_time':
            receipt['attempt']['attempted_at'] = '2000-01-01T00:00:00Z'
        elif kind == 'receipt_date_only':
            receipt['attempt']['attempted_at'] = '2026-01-06'
        elif kind == 'receipt_no_zone':
            receipt['attempt']['attempted_at'] = '2026-01-06T12:00:00'
        elif kind == 'receipt_dataset':
            receipt['retained_dataset_sha256'] = '0' * 64
        elif kind == 'receipt_changed_time':
            receipt['unchanged_generated_at'] = '2026-01-06T00:00:00Z'
        elif kind == 'receipt_extra_key':
            receipt['note'] = 'x'
        elif kind == 'receipt_outcome':
            receipt['attempt']['outcome'] = 'TIMEOUT'
        p, pin = _receipt(tmp_path, 'r.json', receipt)
        receipts.append((p, 'e' * 64 if kind == 'receipt_pin' else pin))
    if kind == 'two_receipts':
        p, pin = _receipt(tmp_path, 'r.json', receipt)
        receipts = [(p, pin)]
        p2, pin2 = _receipt(tmp_path, 'r2.json', receipt)
        receipts.append((p2, pin2))
    data = tmp_path / 'data'
    target = data / 'classification' / 'ownership'
    target.mkdir(parents=True)
    (target / 'kept.json').write_text('{}')
    with pytest.raises(tool.StageError) as error:
        tool.stage(handoffs, receipts, data, synthetic)
    assert str(error.value) == code
    assert sorted(p.name for p in target.iterdir()) == ['kept.json']


def test_public_data_dir_is_refused(tmp_path):
    h = _handoff(tmp_path, 'a', CX['reviewed_scope']['expected_view'])
    with pytest.raises(tool.StageError, match='^DATA_DIR_INSIDE_PUBLIC_REPOSITORY$'):
        tool.stage([h], [], ROOT, True)
