"""Read-only static cockpit. No engine execution; producers own snapshot semantics."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime
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
    from .device_actual_catalog import reject_private_holdings
    reject_private_holdings(bundle)
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
        s = b.get(name)
        if not isinstance(s, dict) or 'state' not in s:
            raise ValueError(f'missing or malformed section: {name}')
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
                if not isinstance(s.get(field), str):
                    raise ValueError(f'LIVE requires {field}')
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
    from ..public_price_boundary import public_bundle
    return public_bundle()


def demo_bundle(b):
    from ..public_price_boundary import block_public_route
    block_public_route()


def compose(html, css='', js=''):
    # Presentation-only additions. Never edit Frozen source renderer or content.
    return html.replace('</head>', '<style>'+css+'</style></head>').replace('</body>', '<script src="locale.js"></script><script>'+js+'</script></body>')


def build(out, bundle=None, demo=False, rig_page=None):
    from ..prompt_library.ui import render_html
    from .entity_catalog import entity_catalog
    from .device_actual_catalog import public_actual_catalog
    out = Path(out)
    from ..public_price_boundary import require_public_bundle, block_public_route
    if demo or rig_page:
        block_public_route()
    b = repository_bundle() if bundle is None else bundle
    from .device_actual_catalog import reject_private_holdings
    reject_private_holdings(b)
    require_public_bundle(b)
    b = validate_bundle(b)
    if demo:
        b = demo_bundle(b)
    if b['relationships']['data'] is not None and not rig_page and not demo:
        raise ValueError('relationships require the reviewed Track D rendered page')
    device_catalog = public_actual_catalog()
    out.mkdir(parents=True, exist_ok=True)
    for f in ASSETS.iterdir():
        if f.suffix in ('.html', '.css', '.js') and not f.name.startswith(('research-', 'network-')):
            shutil.copyfile(f, out / f.name)
    (out / 'data.json').write_text(json.dumps(b, ensure_ascii=False), encoding='utf-8')
    (out / 'entities.json').write_text(json.dumps(entity_catalog(b), ensure_ascii=False), encoding='utf-8')
    (out / 'actual-catalog.json').write_text(json.dumps(device_catalog, ensure_ascii=False), encoding='utf-8')
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
