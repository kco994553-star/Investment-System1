#!/usr/bin/env python3
"""Reconcile Main's producer handoffs stage by stage (owner 2026-11-13 「3/3/3 화면 연결 우선, 전달·재현 병렬 작업 추가」 §2).

For each entry of the registry (implementation/docs/frontend_v2/HANDOFF_REGISTRY.json) this checks the files themselves, never a
comment's wording, and reports six stages apart:

  DELIVERED        the producer's handoff exists: a public manifest in this checkout, or the raw commit:path in the local raw clone
  RECEIPT_CHECKED  that manifest's bytes have the pinned SHA-256 (and, for a public manifest, every file it lists matches)
  READER_VERIFIED  Main's reader supports it as written: model ids and configuration hashes equal the contract's canonical configs,
                   the slots / EPS reader exist (node reads web_app/dual-qgv.js)
  STAGED           every staged private file in --data-dir has its pinned SHA-256
  SCREEN_CONNECTED the private Worker accepts every route the screen reads for it (worker/src/index.js kisClassificationPart)
  REAL_ENV         confirmed only when the registry records a deployed, checked environment; otherwise NOT_CONFIRMED with its reason

Each stage is OK, FAILED (with what differs), NOT_CHECKED (an input was not given, e.g. no --raw-repo) or NOT_APPLICABLE. The
registry's open items are listed as MISSING lines so nothing already delivered is asked for again and nothing missing is assumed.
A contract that exists is not accepted until its stages check. Read only: nothing is fetched, written or staged.

  python implementation/tools/handoff_status.py [--registry …] [--raw-repo <raw clone>] [--data-dir <private data checkout>] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / 'implementation' / 'docs' / 'frontend_v2' / 'HANDOFF_REGISTRY.json'
WEB = REPO / 'implementation' / 'src' / 'investment_system' / 'product' / 'web_app'
WORKER = REPO / 'implementation' / 'worker' / 'src' / 'index.js'
STAGES = ('DELIVERED', 'RECEIPT_CHECKED', 'READER_VERIFIED', 'STAGED', 'SCREEN_CONNECTED', 'REAL_ENV')
WORD = {'DELIVERED': '전달됨', 'RECEIPT_CHECKED': '수령 확인', 'READER_VERIFIED': '판독 검증', 'STAGED': '배치됨', 'SCREEN_CONNECTED': '화면 연결', 'REAL_ENV': '실환경 확인'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(v) -> str:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def node(script: str, *args) -> dict:
    out = subprocess.run(['node', '-e', script, *args], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError('NODE_FAILED')
    return json.loads(out.stdout)


READER = r"""const D=require(process.argv[1]);const m={};for(const[k,v]of Object.entries(D.MODELS))m[k]={model_id:v.model_id,configuration_hash:v.configuration_hash||null,gen:v.gen};
process.stdout.write(JSON.stringify({models:m,slots:Object.keys(D.SLOTS||{}),eps:typeof D.checkEps==='function'}));"""
ROUTES = r"""import(process.argv[1]).then((w)=>{const out={};for(const q of JSON.parse(process.argv[2])){try{out[q]=String(w.kisClassificationPart(new URL('https://w/kis/classification'+q)));}catch(e){out[q]=null;}}
process.stdout.write(JSON.stringify(out));});"""


def raw_bytes(raw_repo: Path, commit: str, path: str):
    out = subprocess.run(['git', '-C', str(raw_repo), 'show', commit + ':' + path], capture_output=True, timeout=60)
    return out.stdout if out.returncode == 0 else None


def check_entry(e: dict, raw_repo, data_dir, reader, routes) -> dict:
    st = {s: ('NOT_APPLICABLE', '') for s in STAGES}
    # delivered / receipt
    if e.get('public'):
        p = REPO / e['public']['manifest']
        if not p.is_file():
            st['DELIVERED'] = ('FAILED', 'public manifest absent: ' + e['public']['manifest'])
        else:
            st['DELIVERED'] = ('OK', 'public ' + e['public']['manifest'])
            b = p.read_bytes()
            bad = [] if sha(b) == e['public']['sha256'] else ['manifest ' + sha(b)[:12]]
            for f in json.loads(b).get('files', []):
                fp = p.parent / f['path']
                if not fp.is_file() or fp.stat().st_size != f['size'] or sha(fp.read_bytes()) != f['sha256']:
                    bad.append(f['path'])
            st['RECEIPT_CHECKED'] = ('FAILED', 'differs: ' + ', '.join(bad)) if bad else ('OK', 'manifest ' + e['public']['sha256'][:12] + '… and every listed file')
    if e.get('raw'):
        r = e['raw']
        if raw_repo is None:
            st['DELIVERED'] = st['RECEIPT_CHECKED'] = ('NOT_CHECKED', 'no --raw-repo')
        else:
            b = raw_bytes(raw_repo, r['commit'], r['path'])
            if b is None:
                st['DELIVERED'] = ('FAILED', 'raw ' + r['commit'][:8] + ':' + r['path'] + ' not in the local clone (fetch the ref)')
                st['RECEIPT_CHECKED'] = ('NOT_CHECKED', 'not delivered locally')
            else:
                st['DELIVERED'] = ('OK', 'raw ' + r['commit'][:8] + ':' + r['path'])
                st['RECEIPT_CHECKED'] = ('OK', r['sha256'][:12] + '…') if sha(b) == r['sha256'] else ('FAILED', 'sha256 ' + sha(b)[:12] + '… ≠ pin ' + r['sha256'][:12] + '…')
    # reader
    rd = e.get('reader') or {}
    if rd:
        bad = []
        if rd.get('contract'):
            contract = json.loads((REPO / rd['contract']).read_text(encoding='utf-8'))
            for k in rd.get('models', []):
                c, m = contract['candidates'].get(k), reader['models'].get(k)
                if not c or not m:
                    bad.append(k + ' not registered')
                elif m['model_id'] != c['model_id'] or m['configuration_hash'] != sha(canonical(c).encode()):
                    bad.append(k + ' id/configuration differs')
        for s in rd.get('slots', []):
            if s not in reader['slots']:
                bad.append('slot ' + s + ' absent')
        if rd.get('eps') and not reader['eps']:
            bad.append('EPS reader absent')
        st['READER_VERIFIED'] = ('FAILED', '; '.join(bad)) if bad else ('OK', ', '.join(rd.get('models', []) + rd.get('slots', []) + (['EPS'] if rd.get('eps') else [])))
    # staged
    if e.get('staged'):
        if data_dir is None:
            st['STAGED'] = ('NOT_CHECKED', 'no --data-dir')
        else:
            bad = []
            for f in e['staged']:
                p = data_dir / f['path']
                if not p.is_file():
                    bad.append(f['path'] + ' absent')
                elif sha(p.read_bytes()) != f['sha256']:
                    bad.append(f['path'] + ' ' + sha(p.read_bytes())[:12] + '…')
            st['STAGED'] = ('FAILED', '; '.join(bad)) if bad else ('OK', str(len(e['staged'])) + ' files at their pins')
    # screen
    if e.get('screen_parts'):
        bad = [q for q in e['screen_parts'] if routes.get(q) is None]
        st['SCREEN_CONNECTED'] = ('FAILED', 'Worker refuses ' + ', '.join(bad)) if bad else ('OK', str(len(e['screen_parts'])) + ' routes accepted (code, not deployment)')
    # real environment
    re_ = e.get('real_env')
    if re_ is not None:
        st['REAL_ENV'] = ('OK', re_.get('evidence', '')) if re_.get('confirmed') else ('NOT_CONFIRMED', re_.get('reason', ''))
    return {'id': e['id'], 'title': e['title'], 'comments': e.get('comments', []), 'producer': e.get('producer'), 'stages': st, 'missing': e.get('missing', [])}


def run(registry: Path, raw_repo, data_dir) -> list:
    reg = json.loads(registry.read_text(encoding='utf-8'))
    if reg.get('schema_version') != 'main-handoff-registry/1':
        raise SystemExit('REGISTRY_SCHEMA')
    reader = node(READER, str(WEB / 'dual-qgv.js'))
    parts = sorted({q for e in reg['entries'] for q in e.get('screen_parts', [])})
    routes = node(ROUTES, str(WORKER), json.dumps(parts)) if parts else {}
    return [check_entry(e, raw_repo, data_dir, reader, routes) for e in reg['entries']]


def markdown(rows: list) -> str:
    out = ['| 인계 | ' + ' | '.join(WORD[s] for s in STAGES) + ' |', '|---|' + '---|' * len(STAGES)]
    for r in rows:
        out.append('| ' + r['id'] + ' | ' + ' | '.join(r['stages'][s][0] for s in STAGES) + ' |')
    for r in rows:
        out.append('')
        out.append('- ' + r['id'] + ' — ' + r['title'] + ' · comments ' + (', '.join(map(str, r['comments'])) or '—') + ' · producer ' + str((r['producer'] or {}).get('sha')))
        for s in STAGES:
            state, why = r['stages'][s]
            if state not in ('NOT_APPLICABLE',):
                out.append('  - ' + WORD[s] + ': ' + state + (' · ' + why if why else ''))
        for m in r['missing']:
            out.append('  - MISSING: ' + m)
    return '\n'.join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--registry', type=Path, default=REGISTRY)
    ap.add_argument('--raw-repo', type=Path)
    ap.add_argument('--data-dir', type=Path)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rows = run(a.registry, a.raw_repo, a.data_dir)
    print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else markdown(rows))
    return 1 if any(r['stages'][s][0] == 'FAILED' for r in rows for s in STAGES) else 0


if __name__ == '__main__':
    sys.exit(main())
