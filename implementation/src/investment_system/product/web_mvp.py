"""Read-only static cockpit. No engine execution; producers own snapshot semantics."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Path(__file__).with_name('web_assets')
STATES = {'LIVE', 'FROZEN_SNAPSHOT', 'DEMO', 'NOT_AVAILABLE'}
SECTIONS = ('qgv', 'technical', 'macro', 'portfolio', 'leaderboard', 'news', 'relationships', 'changes')


def unavailable(reason):
    return {'state': 'NOT_AVAILABLE', 'as_of': None, 'source': None, 'reason': reason, 'data': None}


def envelope(data, state, as_of, source):
    return {'state': state, 'as_of': as_of, 'source': source, 'data': deepcopy(data)}


def validate_bundle(bundle):
    """Validate presentation envelope, not investment logic. Fail closed on false provenance."""
    b = deepcopy(bundle)
    if b.get('schema_version') != 1:
        raise ValueError('unsupported web bundle schema')
    ids = [c['company_id'] for c in b['companies']]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError('company IDs must be unique and nonempty')
    def synthetic(v):
        if isinstance(v, dict):
            return v.get('synthetic') is True or v.get('synthetic_qgv') is True or v.get('kind') == 'SYNTHETIC' or any(synthetic(x) for x in v.values())
        return isinstance(v, list) and any(synthetic(x) for x in v)
    for name in ('universe', *SECTIONS):
        s = b[name]
        if s['state'] not in STATES:
            raise ValueError('unknown data state')
        if s['state'] == 'NOT_AVAILABLE':
            if s.get('data') is not None:
                raise ValueError('unavailable must not contain data')
            continue
        if not s.get('as_of') or not s.get('source'):
            raise ValueError('source and as_of required')
        if synthetic(s['data']) and s['state'] != 'DEMO':
            raise ValueError('synthetic data must be DEMO')
        if s['state'] == 'LIVE':
            for field in ('as_of', 'expires_at'):
                dt = datetime.fromisoformat(s[field].replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    raise ValueError('LIVE timestamps require timezone')
    # Referential integrity only. No ticker-based identity guessing.
    for name in ('qgv', 'technical'):
        if b[name]['data'] is not None and not set(b[name]['data']).issubset(ids):
            raise ValueError('unknown company snapshot identity')
    for name, key in (('portfolio', 'holdings'), ('leaderboard', 'rows')):
        if b[name]['data'] is not None:
            for row in b[name]['data'].get(key, []):
                if row['company_id'] not in ids:
                    raise ValueError('unknown row identity')
    return b


def repository_bundle(root=ROOT):
    folder = root / 'reports/gate_evidence'
    manifest = json.loads((folder / 'track_a_freeze_readiness_2026-09-27.json').read_text())
    name = 'official_snapshot_2024-12-31.json'
    raw = (folder / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['evidence_sha256'][name]:
        raise ValueError('frozen Universe hash mismatch')
    u = json.loads(raw)
    if u['universe_id'] != manifest['per_date'][-1]['universe_id']:
        raise ValueError('frozen Universe identity mismatch')
    b = {'schema_version': 1, 'companies': [dict(company_id=r['company_id'], ticker=r['ticker'], name=r['ticker'],
         market_cap_rank=r['rank'], rank_is_lower_bound=r['rank_is_lower_bound']) for r in u['members']],
         'universe': envelope(u, 'FROZEN_SNAPSHOT', u['as_of'], 'Track A / '+name)}
    for s in SECTIONS:
        b[s] = unavailable('운영 Snapshot이 연결되지 않았습니다.')
    return validate_bundle(b)


def demo_bundle(b):
    b = deepcopy(b)
    report = json.loads((ROOT / 'reports/official_v11_book_snapshots.json').read_text())
    known = {c['company_id'] for c in b['companies']}
    for s in report['snapshots']:
        if s['company_id'] not in known:
            b['companies'].append({'company_id': s['company_id'], 'ticker': s['company_id'], 'name': s['company_id']})
    b['qgv'] = envelope({s['company_id']: s for s in report['snapshots']}, 'DEMO', report['as_of'], 'official_v11_book_snapshots.json / SYNTHETIC')
    mixed = json.loads((ROOT / 'reports/us_session_mixed_2026-09-23.json').read_text())
    b['portfolio'] = envelope({'holdings': mixed['holdings'], 'role': 'SYNTHETIC MODEL / NOT ACTUAL'}, 'DEMO', mixed['as_of_session'], 'us_session_mixed_2026-09-23.json')
    return validate_bundle(b)


def compose(html, css='', js=''):
    # Presentation-only additions. Never edit Frozen source renderer or content.
    return html.replace('</head>', '<style>'+css+'</style></head>').replace('</body>', '<script>'+js+'</script></body>')


def build(out, bundle=None, demo=False, rig_page=None):
    from ..prompt_library.ui import render_html
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    b = validate_bundle(bundle) if bundle else repository_bundle()
    if demo:
        b = demo_bundle(b)
    if b['relationships']['data'] is not None and not rig_page and not demo:
        raise ValueError('relationships require the reviewed Track D rendered page')
    for f in ASSETS.iterdir():
        if f.suffix in ('.html', '.css', '.js') and not f.name.startswith(('research-', 'network-')):
            shutil.copyfile(f, out / f.name)
    (out / 'data.json').write_text(json.dumps(b, ensure_ascii=False), encoding='utf-8')
    research = compose(render_html(), (ASSETS/'research-style.css').read_text(), (ASSETS/'research-bridge.js').read_text())
    (out / 'research.html').write_text(research, encoding='utf-8')
    if rig_page and not demo:
        page = Path(rig_page).read_text(encoding='utf-8')
        (out/'network.html').write_text(compose(page, (ASSETS/'network-style.css').read_text(), (ASSETS/'network-bridge.js').read_text()), encoding='utf-8')
    elif not demo:
        (out/'network.html').unlink(missing_ok=True)
    (out/'data.json').write_text(json.dumps(validate_bundle(b), ensure_ascii=False), encoding='utf-8')
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True)
    p.add_argument('--input', help='Producer-reviewed read-only JSON bundle (schema 1)')
    p.add_argument('--demo', action='store_true')
    p.add_argument('--rig-page', help='Trusted operator-produced Track D HTML, never arbitrary uploaded HTML')
    a = p.parse_args()
    b = json.loads(Path(a.input).read_text()) if a.input else None
    print(build(a.out, b, a.demo, a.rig_page))

if __name__ == '__main__': main()
