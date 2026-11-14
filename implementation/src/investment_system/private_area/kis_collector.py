"""KIS daily-bar collector, the two key-free halves (owner 2026-11-14 evening, DC-52; design PRIVATE_AREA_KIS_DESIGN_20261031.md
§3.2, §4, §17.2). Runs only in the private repository's Actions, from a pinned commit of this public repository, as
``python -I kis_collector.py plan|store``: standard library only, no package import, no network, no Secret.

The private workflow has three steps around this file:
  1. ``plan`` (no Secret): which symbols and which pages to request, from the public Universe504 code list plus the 15
     approved ETFs (PRIV-ETF) and what the private ``data`` branch already holds. Writes one plan file.
  2. the keyed fetch (no repository code): the workflow's own inline script issues one token, requests the overseas daily
     period quote for each plan item through the route allow list (kis_routes.py), keeps each response body as received,
     revokes the token. It writes bodies and receipts to a scratch folder and prints fixed lines only.
  3. ``store`` (no Secret): checks every received page and files the accepted ones in the ``data`` branch, byte for byte,
     with a receipt (SHA-256, byte length, HTTP status, capture time, request), the shape Codex's normalize_page
     (research/kis_price_bridge.py) reads. It also writes the resolved exchange codes, the held date range per symbol and a
     run status with counts only.

Rules (owner 2026-10-31 and 2026-11-14):
- raw prices only (MODP 0) are the record; the adjusted series (MODP 1) is kept apart as a comparison for split candidates
  and never establishes a split; confirmed splits are applied later from evidence only;
- nothing here prints a price, a per-symbol value, a key, a token or a response body: counts, codes and dates only;
- a rejected page is never filed; a filed page is never overwritten (a different body for the same window is kept beside
  it as a revision, so a correction stays visible);
- no order, account or balance route exists anywhere (kis_routes.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

PRIVATE_REPOSITORY = 'kco994553-star/investment-system1-kis-private'
# PRIV-ETF (owner 2026-10-31): SPY, HYG, IEF and the 12 sector ETFs. Exchange code candidates in KIS order: AMS also covers
# NYSE Arca listings; the first candidate that returns rows is kept for later runs.
ETFS = (('SPY', 'ARCA'), ('HYG', 'ARCA'), ('IEF', 'NASDAQ'), ('SMH', 'NASDAQ'), ('XLK', 'ARCA'), ('XLV', 'ARCA'),
        ('XLE', 'ARCA'), ('XLB', 'ARCA'), ('XLP', 'ARCA'), ('XLY', 'ARCA'), ('XLC', 'ARCA'), ('XLU', 'ARCA'),
        ('XLRE', 'ARCA'), ('XLF', 'ARCA'), ('XLI', 'ARCA'))
CANDIDATES = {'NYSE': ('NYS', 'AMS', 'NAS'), 'NASDAQ': ('NAS', 'NYS', 'AMS'), 'BATS': ('AMS', 'NYS', 'NAS'),
              'ARCA': ('AMS', 'NYS', 'NAS')}
EXCD = frozenset({'NYS', 'NAS', 'AMS'})
UNIVERSE_SIZE = 504
CODE = re.compile(r'(NYSE|NASDAQ|BATS):([A-Z][A-Z0-9.]{0,15})')
SYMB = re.compile(r'[A-Z][A-Z0-9/]{0,15}')
DAY = re.compile(r'20[0-9]{6}')
MAX_OLDER_PAGES = 10              # older 100-session pages per symbol in one run
MAX_CALLS = 8000                  # per run, all symbols, all candidates (519 symbols x (3 + 10 + 1) is below it)
MAX_PAGE_BYTES = 262144           # one daily page is about 20 KB
ROOT = 'kis'                      # folder in the data branch
SCHEMA_PLAN, SCHEMA_STATUS = 'kis-collect-plan/1', 'kis-collect-status/1'
REASONS = ('BODY_MISMATCH', 'HTTP_STATUS', 'NOT_JSON', 'RESULT_CODE', 'NO_ROWS', 'SYMBOL_MISMATCH', 'BAD_ROW', 'FUTURE_ROW',
           'DUPLICATE_ROW', 'TOO_LARGE', 'META')


class CollectError(ValueError):
    """A fixed code only."""


def _day(text: str) -> dt.date:
    if not isinstance(text, str) or not DAY.fullmatch(text):
        raise CollectError('DAY')
    return dt.datetime.strptime(text, '%Y%m%d').date()


def key(symb: str) -> str:
    """The folder name of a symbol (KIS writes class shares with '/', e.g. BRK/B)."""
    if not SYMB.fullmatch(symb):
        raise CollectError('SYMBOL')
    return symb.replace('/', '_')


def targets(universe_codes: list) -> list[dict]:
    """The 504 Universe codes and the 15 approved ETFs, in a fixed sequence, each with its KIS symbol and exchange candidates."""
    if not isinstance(universe_codes, list) or len(universe_codes) != UNIVERSE_SIZE or len(set(universe_codes)) != UNIVERSE_SIZE:
        raise CollectError('UNIVERSE_LIST')
    out = []
    for code in universe_codes:
        match = CODE.fullmatch(code) if isinstance(code, str) else None
        if not match:
            raise CollectError('UNIVERSE_CODE')
        out.append({'id': code, 'kind': 'UNIVERSE504', 'symb': match.group(2).replace('.', '/'),
                    'candidates': list(CANDIDATES[match.group(1)])})
    for symbol, venue in ETFS:
        out.append({'id': 'ETF:' + symbol, 'kind': 'ETF', 'symb': symbol, 'candidates': list(CANDIDATES[venue])})
    if len({t['symb'] for t in out}) != len(out):
        raise CollectError('DUPLICATE_SYMBOL')
    return out


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def plan(universe_codes: list, data: Path, *, latest: bool, older_pages: int, modp1: bool) -> dict:
    """Requests for one run. ``latest`` asks the newest page (BYMD empty); ``older_pages`` chains that many pages before the
    oldest session already held (or, with no held page, before the newest page fetched in the same run)."""
    if type(older_pages) is not int or not 0 <= older_pages <= MAX_OLDER_PAGES or not (latest or older_pages):
        raise CollectError('PAGES')
    resolved = _read_json(data / ROOT / 'symbols.json', {})
    coverage = _read_json(data / ROOT / 'coverage.json', {})
    items, calls = [], 0
    for target in targets(universe_codes):
        excd = resolved.get(target['id'], {}).get('excd')
        candidates = [excd] if excd in EXCD else target['candidates']
        earliest = coverage.get(target['id'], {}).get('earliest')
        if earliest is not None:
            _day(earliest)
        if not latest and earliest is None:
            continue   # nothing held yet: an older page has nothing to chain from (the first run asks the latest page)
        older_from = None if earliest is None else (_day(earliest) - dt.timedelta(days=1)).strftime('%Y%m%d')
        item = {'id': target['id'], 'symb': target['symb'], 'candidates': candidates, 'latest': bool(latest),
                'older_pages': older_pages, 'older_from': older_from, 'modp1': bool(modp1 and latest)}
        items.append(item)
        calls += (len(candidates) if latest else 1) + older_pages + (1 if item['modp1'] else 0)
    if calls > MAX_CALLS:
        raise CollectError('TOO_MANY_CALLS')
    return {'schema': SCHEMA_PLAN, 'repository': PRIVATE_REPOSITORY, 'items': items, 'max_calls': calls,
            'pace_per_second': 5}


def _short(value) -> str:
    return value if isinstance(value, str) and 0 < len(value) <= 16 and value.replace('_', '').isalnum() else '-'


def check_page(body: bytes, meta: dict) -> dict:
    """One received page: the receipt matches the body and the body is a successful daily page for the requested symbol.
    Returns the held sessions' first and last day and the row count; raises CollectError(reason) otherwise."""
    request = meta.get('request') if isinstance(meta, dict) else None
    if not isinstance(request, dict) or set(request) != {'SYMB', 'EXCD', 'MODP', 'GUBN', 'BYMD'}:
        raise CollectError('META')
    if request['EXCD'] not in EXCD or request['MODP'] not in ('0', '1') or request['GUBN'] != '0' or not SYMB.fullmatch(request['SYMB']):
        raise CollectError('META')
    if request['BYMD']:
        _day(request['BYMD'])
    if len(body) > MAX_PAGE_BYTES:
        raise CollectError('TOO_LARGE')
    if meta.get('bytes') != len(body) or meta.get('sha256') != hashlib.sha256(body).hexdigest():
        raise CollectError('BODY_MISMATCH')
    if meta.get('http_status') != 200:
        raise CollectError('HTTP_STATUS')
    fetched = meta.get('fetched_at')
    if not isinstance(fetched, str) or not re.fullmatch(r'20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ', fetched):
        raise CollectError('META')
    try:
        data = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise CollectError('NOT_JSON') from None
    if not isinstance(data, dict) or data.get('rt_cd') != '0' or not isinstance(data.get('output2'), list):
        raise CollectError('RESULT_CODE')
    rows = [r for r in data['output2'] if isinstance(r, dict) and r.get('xymd')]
    if not rows:
        raise CollectError('NO_ROWS')
    head = data.get('output1') if isinstance(data.get('output1'), dict) else {}
    if head.get('rsym') != 'D' + request['EXCD'] + request['SYMB']:
        raise CollectError('SYMBOL_MISMATCH')
    limit = _day(request['BYMD']) if request['BYMD'] else _day(fetched[:10].replace('-', ''))
    days = []
    for row in rows:
        try:
            day = _day(row['xymd'])
            for field in ('open', 'high', 'low', 'clos', 'tvol'):
                if not isinstance(row.get(field), str) or not re.fullmatch(r'[0-9]+(\.[0-9]+)?', row[field]):
                    raise CollectError('BAD_ROW')
        except CollectError:
            raise CollectError('BAD_ROW') from None
        if day > limit:
            raise CollectError('FUTURE_ROW')
        days.append(day)
    if len(set(days)) != len(days):
        raise CollectError('DUPLICATE_ROW')
    return {'first': min(days).strftime('%Y%m%d'), 'last': max(days).strftime('%Y%m%d'), 'rows': len(days)}


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'xb') as handle:
        handle.write(payload)


def store(pages: Path, data: Path, universe_codes: list, *, run_at: str) -> dict:
    """Files every accepted page under data/kis/dailyprice/<symbol>/MODP<m>/<first>_<last>.json with its receipt and updates
    symbols.json (exchange code that returned rows), coverage.json (oldest and newest held raw session) and status.json."""
    by_symb = {t['symb']: t for t in targets(universe_codes)}
    root = data / ROOT
    resolved = _read_json(root / 'symbols.json', {})
    coverage = _read_json(root / 'coverage.json', {})
    counts = {'pages': 0, 'filed': 0, 'same_as_held': 0, 'revisions': 0, 'refused': {}, 'empty_candidates': 0, 'history_end': 0}
    for meta_path in sorted(pages.glob('*.json')):
        counts['pages'] += 1
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            body = meta_path.with_suffix('.body').read_bytes()
        except (OSError, ValueError):
            counts['refused']['META'] = counts['refused'].get('META', 0) + 1
            continue
        try:
            held = check_page(body, meta)
            target = by_symb.get(meta['request']['SYMB'])
            if target is None or meta.get('id') != target['id']:
                raise CollectError('META')
        except CollectError as error:
            reason = str(error)
            if reason == 'NO_ROWS' and meta.get('candidate_probe') is True:
                counts['empty_candidates'] += 1   # another exchange code is tried next; not a failure
                continue
            if reason == 'NO_ROWS' and meta.get('older_page') is True:
                counts['history_end'] += 1        # nothing older than the oldest held session; not a failure
                continue
            counts['refused'][reason] = counts['refused'].get(reason, 0) + 1
            continue
        request = meta['request']
        folder = root / 'dailyprice' / key(request['SYMB']) / ('MODP' + request['MODP'])
        name = held['first'] + '_' + held['last']
        receipt = {'sha256': meta['sha256'], 'bytes': meta['bytes'], 'http_status': 200, 'fetched_at': meta['fetched_at'],
                   'request': request, 'rows': held['rows']}
        target_path = folder / (name + '.json')
        if target_path.exists():
            if hashlib.sha256(target_path.read_bytes()).hexdigest() == meta['sha256']:
                counts['same_as_held'] += 1
                continue
            name += '.rev-' + meta['fetched_at'].replace('-', '').replace(':', '')
            target_path = folder / (name + '.json')
            counts['revisions'] += 1
        _write_new(target_path, body)
        _write_new(folder / (name + '.receipt.json'), (json.dumps(receipt, sort_keys=True, indent=1) + '\n').encode('utf-8'))
        counts['filed'] += 1
        resolved[target['id']] = {'symb': request['SYMB'], 'excd': request['EXCD']}
        if request['MODP'] == '0':
            have = coverage.setdefault(target['id'], {'earliest': held['first'], 'latest': held['last']})
            have['earliest'] = min(have['earliest'], held['first'])
            have['latest'] = max(have['latest'], held['last'])
    root.mkdir(parents=True, exist_ok=True)
    (root / 'symbols.json').write_text(json.dumps(resolved, sort_keys=True, indent=1) + '\n', encoding='utf-8')
    (root / 'coverage.json').write_text(json.dumps(coverage, sort_keys=True, indent=1) + '\n', encoding='utf-8')
    latest = sorted({c['latest'] for c in coverage.values()})
    status = {'schema': SCHEMA_STATUS, 'publication_scope': 'OWNER_PRIVATE_ONLY', 'run_at': run_at, 'counts': counts,
              'symbols_total': len(by_symb), 'symbols_held': len(coverage),
              'symbols_missing': sorted(t['id'] for t in by_symb.values() if t['id'] not in coverage),
              'newest_session': latest[-1] if latest else None,
              'symbols_at_newest_session': sum(1 for c in coverage.values() if latest and c['latest'] == latest[-1])}
    (root / 'status.json').write_text(json.dumps(status, sort_keys=True, indent=1) + '\n', encoding='utf-8')
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='kis_collector.py')
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--universe', type=Path, required=True)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--latest', choices=('yes', 'no'), required=True)
    p.add_argument('--older-pages', type=int, required=True)
    p.add_argument('--modp1', choices=('yes', 'no'), default='no')
    s = sub.add_parser('store')
    s.add_argument('--universe', type=Path, required=True)
    s.add_argument('--data', type=Path, required=True)
    s.add_argument('--pages', type=Path, required=True)
    args = parser.parse_args(argv)
    if os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_REPOSITORY') != PRIVATE_REPOSITORY:
        print('KIS_COLLECT stop=wrong_repository')
        return 2
    try:
        codes = json.loads(args.universe.read_text(encoding='utf-8'))
        if args.cmd == 'plan':
            result = plan(codes, args.data, latest=args.latest == 'yes', older_pages=args.older_pages, modp1=args.modp1 == 'yes')
            with open(args.out, 'x', encoding='utf-8') as handle:
                json.dump(result, handle, sort_keys=True)
            print('KIS_COLLECT plan items=%d max_calls=%d' % (len(result['items']), result['max_calls']))
            return 0
        run_at = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        status = store(args.pages, args.data, codes, run_at=run_at)
    except CollectError as error:
        print('KIS_COLLECT stop=%s' % error)
        return 1
    except (OSError, ValueError) as error:
        print('KIS_COLLECT stop=%s' % type(error).__name__)
        return 1
    c = status['counts']
    refused = ','.join('%s:%d' % (k, v) for k, v in sorted(c['refused'].items())) or '-'
    print('KIS_COLLECT store pages=%d filed=%d same=%d revisions=%d empty_candidates=%d history_end=%d refused=%s held=%d/%d newest=%s at_newest=%d'
          % (c['pages'], c['filed'], c['same_as_held'], c['revisions'], c['empty_candidates'], c['history_end'], refused, status['symbols_held'],
             status['symbols_total'], status['newest_session'] or '-', status['symbols_at_newest_session']))
    return 0 if not c['refused'] else 1


if __name__ == '__main__':
    sys.exit(main())
