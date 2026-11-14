"""KIS daily-bar collector, key-free halves (kis_collector.py; owner 2026-11-14 DC-52). Synthetic pages only: every body here is
made up in this file (prices 1.00 to 9.99, symbols of the real Universe list), never a KIS response."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from investment_system.private_area import kis_collector as C

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'src/investment_system/private_area/kis_collector.py'
UNIVERSE = ROOT / 'src/investment_system/universe/universe_codes_v1.json'
CODES = json.loads(UNIVERSE.read_text(encoding='utf-8'))


def page(symb, excd, days, *, modp='0', bymd='', rt='0', rsym=None, fetched='2026-11-15T03:40:00Z', row=None):
    rows = [dict({'xymd': d, 'open': '1.10', 'high': '1.30', 'low': '1.00', 'clos': '1.20', 'tvol': '100', 'tamt': '120'}, **(row or {}))
            for d in days]
    body = json.dumps({'rt_cd': rt, 'msg_cd': 'MCA00000', 'output1': {'rsym': rsym or 'D' + excd + symb}, 'output2': rows}).encode()
    meta = {'id': None, 'request': {'SYMB': symb, 'EXCD': excd, 'MODP': modp, 'GUBN': '0', 'BYMD': bymd},
            'http_status': 200, 'fetched_at': fetched, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    return body, meta


def drop(folder, n, body, meta, ident):
    meta = dict(meta, id=ident)
    (folder / ('%05d.body' % n)).write_bytes(body)
    (folder / ('%05d.json' % n)).write_text(json.dumps(meta), encoding='utf-8')


def test_targets_are_the_504_codes_and_the_15_etfs():
    t = C.targets(CODES)
    assert len(t) == 519 and sum(x['kind'] == 'ETF' for x in t) == 15
    by = {x['id']: x for x in t}
    assert by['NYSE:BRK.B']['symb'] == 'BRK/B' and by['NYSE:BF.B']['symb'] == 'BF/B'
    assert by['NASDAQ:AAPL']['candidates'] == ['NAS', 'NYS', 'AMS'] and by['BATS:CBOE']['candidates'][0] == 'AMS'
    assert {x['symb'] for x in t if x['kind'] == 'ETF'} == {'SPY', 'HYG', 'IEF', 'SMH', 'XLK', 'XLV', 'XLE', 'XLB', 'XLP', 'XLY',
                                                         'XLC', 'XLU', 'XLRE', 'XLF', 'XLI'}
    with pytest.raises(C.CollectError, match='UNIVERSE_LIST'):
        C.targets(CODES[:-1])
    with pytest.raises(C.CollectError, match='UNIVERSE_CODE'):
        C.targets(CODES[:-1] + ['OTC:ABCD'])


def test_first_run_plans_the_latest_page_and_no_older_page(tmp_path):
    p = C.plan(CODES, tmp_path, latest=True, older_pages=0, modp1=True)
    assert len(p['items']) == 519 and all(i['latest'] and i['older_from'] is None and i['modp1'] for i in p['items'])
    assert p['max_calls'] == 519 * 3 + 519 and p['max_calls'] <= C.MAX_CALLS
    # Older pages with nothing held: nothing to chain from, so nothing is planned.
    assert C.plan(CODES, tmp_path, latest=False, older_pages=2, modp1=False)['items'] == []
    for bad in (-1, C.MAX_OLDER_PAGES + 1, True):
        with pytest.raises(C.CollectError, match='PAGES'):
            C.plan(CODES, tmp_path, latest=True, older_pages=bad, modp1=False)
    with pytest.raises(C.CollectError, match='PAGES'):
        C.plan(CODES, tmp_path, latest=False, older_pages=0, modp1=False)


def test_store_files_pages_byte_for_byte_and_the_next_plan_chains_older(tmp_path):
    pages, data = tmp_path / 'pages', tmp_path / 'data'
    pages.mkdir()
    body, meta = page('AAPL', 'NAS', ['20261113', '20261112'])
    drop(pages, 1, body, meta, 'NASDAQ:AAPL')
    probe_body, probe_meta = page('BRK/B', 'NYS', [])
    drop(pages, 2, probe_body, dict(probe_meta, candidate_probe=True), 'NYSE:BRK.B')
    b3, m3 = page('BRK/B', 'AMS', ['20261113'])
    drop(pages, 3, b3, m3, 'NYSE:BRK.B')
    b4, m4 = page('AAPL', 'NAS', ['20261113', '20261112'], modp='1')
    drop(pages, 4, b4, m4, 'NASDAQ:AAPL')
    status = C.store(pages, data, CODES, run_at='2026-11-15T03:45:00Z')
    c = status['counts']
    assert (c['pages'], c['filed'], c['empty_candidates'], c['refused']) == (4, 3, 1, {})
    held = data / 'kis/dailyprice/AAPL/MODP0/20261112_20261113.json'
    assert held.read_bytes() == body
    receipt = json.loads(held.with_name('20261112_20261113.receipt.json').read_text())
    assert receipt == {'sha256': meta['sha256'], 'bytes': len(body), 'http_status': 200, 'fetched_at': meta['fetched_at'],
                       'request': meta['request'], 'rows': 2}
    assert (data / 'kis/dailyprice/BRK_B/MODP0/20261113_20261113.json').read_bytes() == b3
    assert (data / 'kis/dailyprice/AAPL/MODP1/20261112_20261113.json').read_bytes() == b4
    assert json.loads((data / 'kis/symbols.json').read_text())['NYSE:BRK.B'] == {'symb': 'BRK/B', 'excd': 'AMS'}
    cov = json.loads((data / 'kis/coverage.json').read_text())
    assert cov == {'NASDAQ:AAPL': {'earliest': '20261112', 'latest': '20261113'},
                   'NYSE:BRK.B': {'earliest': '20261113', 'latest': '20261113'}}   # MODP1 never moves the raw range
    assert status['symbols_held'] == 2 and status['newest_session'] == '20261113' and len(status['symbols_missing']) == 517
    assert status['publication_scope'] == 'OWNER_PRIVATE_ONLY'
    nxt = {i['id']: i for i in C.plan(CODES, data, latest=False, older_pages=2, modp1=False)['items']}
    assert set(nxt) == {'NASDAQ:AAPL', 'NYSE:BRK.B'}
    assert nxt['NASDAQ:AAPL']['older_from'] == '20261111' and nxt['NASDAQ:AAPL']['candidates'] == ['NAS']
    assert nxt['NYSE:BRK.B']['candidates'] == ['AMS']


def test_an_empty_older_page_is_the_end_of_history_not_a_failure(tmp_path):
    pages, data = tmp_path / 'pages', tmp_path / 'data'
    pages.mkdir()
    body, meta = page('AAPL', 'NAS', [], bymd='20160101')
    drop(pages, 1, body, dict(meta, older_page=True), 'NASDAQ:AAPL')
    status = C.store(pages, data, CODES, run_at='2026-11-15T03:45:00Z')
    assert status['counts']['history_end'] == 1 and status['counts']['refused'] == {} and status['counts']['filed'] == 0


def test_a_held_page_is_never_overwritten_and_a_different_body_is_a_revision(tmp_path):
    pages, data = tmp_path / 'pages', tmp_path / 'data'
    pages.mkdir()
    body, meta = page('AAPL', 'NAS', ['20261113'])
    drop(pages, 1, body, meta, 'NASDAQ:AAPL')
    C.store(pages, data, CODES, run_at='2026-11-15T03:45:00Z')
    status = C.store(pages, data, CODES, run_at='2026-11-16T03:45:00Z')
    assert status['counts']['same_as_held'] == 1 and status['counts']['filed'] == 0
    for f in pages.iterdir():
        f.unlink()
    b2, m2 = page('AAPL', 'NAS', ['20261113'], fetched='2026-11-16T03:40:00Z', row={'clos': '1.25'})
    drop(pages, 1, b2, m2, 'NASDAQ:AAPL')
    status = C.store(pages, data, CODES, run_at='2026-11-16T03:45:00Z')
    assert status['counts']['revisions'] == 1
    folder = data / 'kis/dailyprice/AAPL/MODP0'
    assert (folder / '20261113_20261113.json').read_bytes() == body
    assert (folder / '20261113_20261113.rev-20261116T034000Z.json').read_bytes() == b2


@pytest.mark.parametrize('case,reason', [
    ('mismatch', 'BODY_MISMATCH'), ('http', 'HTTP_STATUS'), ('rt', 'RESULT_CODE'), ('empty', 'NO_ROWS'),
    ('rsym', 'SYMBOL_MISMATCH'), ('bad', 'BAD_ROW'), ('future', 'FUTURE_ROW'), ('dup', 'DUPLICATE_ROW'),
    ('meta', 'META'), ('notjson', 'NOT_JSON'), ('large', 'TOO_LARGE')])
def test_a_bad_page_is_refused_with_a_code_and_never_filed(tmp_path, case, reason):
    days = ['20261113', '20261113'] if case == 'dup' else ['20261113']
    body, meta = page('AAPL', 'NAS', [] if case == 'empty' else days, rt='1' if case == 'rt' else '0',
                      rsym='DNASMSFT' if case == 'rsym' else None, bymd='20261112' if case == 'future' else '',
                      row={'clos': '-1'} if case == 'bad' else None)
    if case == 'mismatch':
        meta['sha256'] = '0' * 64
    if case == 'http':
        meta['http_status'] = 500
    if case == 'meta':
        meta['request'] = dict(meta['request'], MODP='2')
    if case == 'notjson':
        body = b'\xff'
        meta.update(bytes=1, sha256=hashlib.sha256(body).hexdigest())
    if case == 'large':
        body = b' ' * (C.MAX_PAGE_BYTES + 1)
        meta.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    with pytest.raises(C.CollectError, match=reason):
        C.check_page(body, meta)
    pages, data = tmp_path / 'pages', tmp_path / 'data'
    pages.mkdir()
    drop(pages, 1, body, meta, 'NASDAQ:AAPL')
    status = C.store(pages, data, CODES, run_at='2026-11-15T03:45:00Z')
    assert status['counts']['refused'] == {reason: 1} and not (data / 'kis/dailyprice').exists()


def test_a_page_for_a_symbol_outside_the_targets_is_refused(tmp_path):
    pages, data = tmp_path / 'pages', tmp_path / 'data'
    pages.mkdir()
    body, meta = page('ZZZZ', 'NAS', ['20261113'])
    drop(pages, 1, body, meta, 'NASDAQ:ZZZZ')
    assert C.store(pages, data, CODES, run_at='2026-11-15T03:45:00Z')['counts']['refused'] == {'META': 1}


def test_cli_prints_fixed_lines_only_and_refuses_outside_the_private_repository(tmp_path):
    pages, data = tmp_path / 'pages', tmp_path / 'data'
    pages.mkdir()
    body, meta = page('AAPL', 'NAS', ['20261113'], row={'clos': '7.77'})
    drop(pages, 1, body, meta, 'NASDAQ:AAPL')
    env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': C.PRIVATE_REPOSITORY, 'PATH': '/usr/bin:/bin'}
    out = subprocess.run([sys.executable, '-I', str(MODULE), 'store', '--universe', str(UNIVERSE), '--data', str(data),
                          '--pages', str(pages)], capture_output=True, text=True, env=env, check=True).stdout
    assert out.startswith('KIS_COLLECT store pages=1 filed=1 ') and '7.77' not in out and 'AAPL' not in out
    out = subprocess.run([sys.executable, '-I', str(MODULE), 'plan', '--universe', str(UNIVERSE), '--data', str(data),
                          '--out', str(tmp_path / 'plan.json'), '--latest', 'yes', '--older-pages', '0'],
                         capture_output=True, text=True, env=env, check=True).stdout
    assert out == 'KIS_COLLECT plan items=519 max_calls=%d\n' % (1 + 518 * 3)
    other = dict(env, GITHUB_REPOSITORY='someone/else')
    run = subprocess.run([sys.executable, '-I', str(MODULE), 'plan', '--universe', str(UNIVERSE), '--data', str(data),
                          '--out', str(tmp_path / 'p2.json'), '--latest', 'yes', '--older-pages', '0'],
                         capture_output=True, text=True, env=other)
    assert run.returncode == 2 and run.stdout == 'KIS_COLLECT stop=wrong_repository\n' and not (tmp_path / 'p2.json').exists()


def test_module_is_standard_library_only_with_no_network_secret_or_host():
    tree = ast.parse(MODULE.read_text(encoding='utf-8'))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or '').split('.')[0])
    assert imported == {'__future__', 'argparse', 'datetime', 'hashlib', 'json', 'os', 're', 'sys', 'pathlib'}
    text = MODULE.read_text(encoding='utf-8')
    for word in ('urllib', 'http.client', 'socket', 'KIS_APP', 'koreainvestment', 'oauth2', 'environ.get(\'KIS'):
        assert word not in text, word
    for word in ('order', 'balance', 'account'):
        assert not [line for line in text.splitlines() if word in line.casefold() and not line.lstrip().startswith(('#', '-'))
                    and 'route' not in line], word
