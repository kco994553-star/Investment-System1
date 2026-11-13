"""handoff_status.py (owner 2026-11-13 「3/3/3 화면 연결 우선」 §2): six stages kept apart and each checked against the files; an input
that was not given is NOT_CHECKED (never OK), a differing hash is FAILED with what differs, the registry's open items are listed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import handoff_status as tool  # noqa: E402

REG = json.loads(tool.REGISTRY.read_text(encoding='utf-8'))


def _entry(i):
    return next(e for e in REG['entries'] if e['id'] == i)


def _reg(tmp_path, entries):
    p = tmp_path / 'reg.json'
    p.write_text(json.dumps({'schema_version': 'main-handoff-registry/1', 'entries': entries}))
    return p


def test_the_registry_checks_against_this_checkout_without_private_inputs(tmp_path):
    rows = {r['id']: r['stages'] for r in tool.run(tool.REGISTRY, None, None)}
    c = rows['qgv333-contract']
    assert [c[s][0] for s in tool.STAGES[:3]] == ['OK', 'OK', 'OK'], c
    r = rows['qgv333-results']
    assert r['DELIVERED'][0] == r['RECEIPT_CHECKED'][0] == 'NOT_CHECKED' and r['STAGED'][0] == 'NOT_CHECKED', 'no private input given: never OK'
    assert r['READER_VERIFIED'][0] == 'OK' and r['SCREEN_CONNECTED'][0] == 'OK' and r['REAL_ENV'][0] == 'NOT_CONFIRMED'
    assert rows['qgv333-eps']['READER_VERIFIED'][0] == 'OK' and rows['qgv333-eps']['SCREEN_CONNECTED'][0] == 'OK'


def test_differences_are_failed_with_what_differs(tmp_path):
    bad_public = json.loads(json.dumps(_entry('qgv333-contract')))
    bad_public['public']['sha256'] = '0' * 64
    bad_reader = json.loads(json.dumps(_entry('qgv333-contract')))
    bad_reader['id'] = 'reader'; bad_reader['reader']['models'] = ['U2-333', 'U9-333']
    staged = {'id': 'staged', 'title': 't', 'staged': [{'path': 'a.json', 'sha256': hashlib.sha256(b'{}').hexdigest()}, {'path': 'b.json', 'sha256': '1' * 64}],
              'screen_parts': ['?part=dual_eps_index', '?part=dual_eps_continuation'], 'real_env': {'confirmed': False, 'reason': 'not deployed'}, 'missing': ['x']}
    data = tmp_path / 'data'; data.mkdir(); (data / 'a.json').write_bytes(b'{}'); (data / 'b.json').write_bytes(b'[]')
    rows = {r['id']: r for r in tool.run(_reg(tmp_path, [bad_public, bad_reader, staged]), None, data)}
    assert rows['qgv333-contract']['stages']['RECEIPT_CHECKED'][0] == 'FAILED'
    assert rows['reader']['stages']['READER_VERIFIED'] == ('FAILED', 'U9-333 not registered')
    s = rows['staged']['stages']
    assert s['STAGED'][0] == 'FAILED' and 'b.json' in s['STAGED'][1] and 'a.json' not in s['STAGED'][1]
    assert s['SCREEN_CONNECTED'] == ('FAILED', 'Worker refuses ?part=dual_eps_continuation')
    assert s['REAL_ENV'] == ('NOT_CONFIRMED', 'not deployed') and rows['staged']['missing'] == ['x']
    assert tool.main(['--registry', str(_reg(tmp_path, [bad_public])), '--json']) == 1


def test_a_raw_handoff_is_checked_in_the_local_clone(tmp_path):
    raw = tmp_path / 'raw'
    subprocess.run(['git', 'init', '-q', str(raw)], check=True)
    (raw / 'h').mkdir(); (raw / 'h' / 'm.json').write_bytes(b'{"a":1}\n')
    env = ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
    subprocess.run(['git', '-C', str(raw), *env, 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(raw), *env, 'commit', '-qm', 'x'], check=True)
    head = subprocess.run(['git', '-C', str(raw), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    good = {'id': 'good', 'title': 't', 'raw': {'commit': head, 'path': 'h/m.json', 'sha256': hashlib.sha256(b'{"a":1}\n').hexdigest()}}
    pin = {'id': 'pin', 'title': 't', 'raw': {'commit': head, 'path': 'h/m.json', 'sha256': '2' * 64}}
    gone = {'id': 'gone', 'title': 't', 'raw': {'commit': head, 'path': 'h/none.json', 'sha256': '2' * 64}}
    rows = {r['id']: r['stages'] for r in tool.run(_reg(tmp_path, [good, pin, gone]), raw, None)}
    assert rows['good']['DELIVERED'][0] == rows['good']['RECEIPT_CHECKED'][0] == 'OK'
    assert rows['pin']['DELIVERED'][0] == 'OK' and rows['pin']['RECEIPT_CHECKED'][0] == 'FAILED'
    assert rows['gone']['DELIVERED'][0] == 'FAILED' and rows['gone']['RECEIPT_CHECKED'][0] == 'NOT_CHECKED'
