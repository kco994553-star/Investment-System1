"""IEX HIST adapter (providers/iex_hist.py) and month-end store reader (providers/iex_monthend.py). SYNTHETIC numbers only.

The C parser (tools/iex_tops/iex_last_trade.c) is compiled into a temp dir and fed a synthetic gzip pcap built here (IEX-TP
v1 TOPS 1.6 Trade Report / Trading Status messages in Ethernet/IPv4/UDP frames); `download` is `cat` of that file, so nothing
touches the network. Every price below is made up.
"""
import base64
import datetime as dt
import gzip
import hashlib
import json
import pickle
import re
import shutil
import struct
import subprocess

import pytest

from investment_system.providers import iex_hist as ih
from investment_system.providers import iex_monthend as im
from investment_system.qgv import v2_factors as vf
from investment_system.universe.sec_universe_shares import shard_day

ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]
CANARY_E4 = 4242_4242   # $4242.4242: a made-up price that must never show up in any text output
DAY = '20261022'


@pytest.fixture(scope='module')
def parser(tmp_path_factory):
    if not shutil.which('cc'):
        pytest.skip('no C compiler')
    out = tmp_path_factory.mktemp('parser') / 'iex_last_trade'
    subprocess.run(['cc', '-O2', '-o', str(out), str(ROOT / 'tools/iex_tops/iex_last_trade.c')], check=True)
    return str(out)


def _sym(s):
    return s.encode('ascii').ljust(8, b' ')


def trade(sym, ts, px_e4, flags=0, size=100):
    return struct.pack('<BBq8sIqq', 0x54, flags, ts, _sym(sym), size, px_e4, 1)


def status_msg(sym, ts, status=b'T'):
    return struct.pack('<Bcq8s4s', 0x48, status, ts, _sym(sym), b'    ')


def frame(messages):
    payload = b''.join(struct.pack('<H', len(m)) + m for m in messages)
    tp = struct.pack('<BBHIIHHqqq', 1, 0, 0x8003, 1, 1, len(payload), len(messages), 0, 0, 0) + payload
    udp = struct.pack('>HHHH', 1, 2, 8 + len(tp), 0) + tp
    ip = bytes([0x45, 0]) + struct.pack('>H', 20 + len(udp)) + bytes(5) + bytes([17]) + bytes(10) + udp
    return bytes(12) + b'\x08\x00' + ip


def pcap(frames):
    out = struct.pack('<IHHiIII', 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for f in frames:
        out += struct.pack('<IIII', 0, 0, len(f), len(f)) + f
    return out


def synthetic_day(tmp_path, day=DAY):
    t0, t1 = ih.session_ns(day)
    m = 60 * 10**9
    frames = [frame([status_msg('AAA', t0 - m), trade('AAA', t0 + m, 1000000)]),              # $100 round lot
              frame([trade('AAA', t0 + 2 * m, CANARY_E4)]),                                    # later round lot: last wins
              frame([trade('AAA', t0 + 3 * m, 999999, flags=0x20)]),                           # odd lot: never the price
              frame([trade('BBB', t0 + m, 555555, flags=0x20)]),                               # odd lot only
              frame([trade('CCC', t1 + m, 777777, flags=0x40), trade('CCC', t0 - m, 777777)]),  # extended / pre-open only
              frame([trade('SKYD', t0 + 5 * m, 123400)]),
              frame([trade('PSKY', t0 + 5 * m, 999900)]),                                     # never used after the alias date
              frame([trade('WBD', t0 + 5 * m, 888800)])]                                      # reused ticker: never filled
    body = gzip.compress(pcap(frames), mtime=0)
    path = tmp_path / 'tops.pcap.gz'
    path.write_bytes(body)
    return path, body


def test_symbol_alias_table_is_dated_and_fail_closed():
    assert ih.iex_symbol('NASDAQ:PSKY', '2026-10-05') == 'PSKY'
    assert ih.iex_symbol('NASDAQ:PSKY', '20261006') == 'SKYD'       # confirmed switch date (probe run 39944426209)
    assert ih.iex_symbol('NASDAQ:WBD', '2026-10-05') == 'WBD'
    assert ih.iex_symbol('NASDAQ:WBD', '2026-10-06') is None        # not on IEX: NO price, never another company's
    assert ih.iex_symbol('NYSE:BRK.B', DAY) == 'BRK.B'
    assert all(len(e) == 3 and e[2] for v in ih.SYMBOL_ALIASES.values() for e in v)   # every entry names its evidence
    assert ih.MONTHEND_BASIS_CUTS['NASDAQ:PSKY'][1] == 'MERGER_PRE_BASIS_UNCONFIRMED'


def _index(link='https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20261022%2Ftops.pcap.gz?generation=1&alt=media'):
    return {'20261021': [{'feed': 'TOPS', 'version': '1.6', 'link': link.replace('20261022', '20261021'), 'size': '10'}],
            '20261022': [{'feed': 'TOPS', 'version': '1.6', 'link': link, 'size': '20'},
                         {'feed': 'DEEP', 'version': '1.0', 'link': link, 'size': '30'}],
            '20261023': [{'feed': 'TOPS', 'version': '1.6', 'link': link, 'size': '40'}],
            '20261020': [{'feed': 'TOPS', 'version': '1.6', 'link': 'http://evil.example/x', 'size': '5'}]}


def test_select_day_latest_tops_file_on_or_before_the_basis_date():
    day, entry = ih.select_day(_index(), dt.date(2026, 10, 22))
    assert (day, entry['size']) == ('20261022', 20)
    assert ih.select_day(_index(), dt.date(2026, 10, 25))[0] == '20261023'
    with pytest.raises(ih.IexHistError, match='NO_FILE_FOR_BASIS'):
        ih.select_day(_index(), dt.date(2026, 10, 20))    # the only file then is not an allowed https link


def test_gcs_metadata_md5_and_size_check():
    _, entry = ih.select_day(_index(), dt.date(2026, 10, 22))
    md5 = hashlib.md5(b'x').digest()
    seen = []

    def fetch(url):
        seen.append(url)
        return {'size': '20', 'md5Hash': base64.b64encode(md5).decode()}
    assert ih.file_checks(entry, fetch) == (20, md5.hex())
    assert '/storage/v1/b/iex/o/' in seen[0] and 'alt=' not in seen[0] and '/download/' not in seen[0]
    with pytest.raises(ih.IexHistError, match='SIZE_MISMATCH'):
        ih.file_checks(entry, lambda url: {'size': '21', 'md5Hash': base64.b64encode(md5).decode()})
    with pytest.raises(ih.IexHistError, match='SOURCE_URL_INVALID'):
        ih.fetch_json('https://example.com/hist')


def _stream(path, body, parser, tmp_path, symbols, **over):
    kw = dict(day=DAY, size=len(body), md5=hashlib.md5(body).hexdigest(), parser=parser, workdir=tmp_path / 'w',
              download=lambda link: ['cat', str(path)])
    kw.update(over)
    return ih.stream_day('https://www.googleapis.com/x', symbols, **kw)


def test_stream_last_sale_eligible_rule_with_the_real_parser(parser, tmp_path):
    path, body = synthetic_day(tmp_path)
    rows = _stream(path, body, parser, tmp_path, ['AAA', 'BBB', 'CCC', 'DDD'])
    assert rows == {'AAA': ('ROUND', CANARY_E4), 'BBB': ('ODD_ONLY', 555555), 'CCC': ('NO_TRADE', None), 'DDD': ('NO_TRADE', None)}
    assert not list((tmp_path / 'w').iterdir())        # the ticker list is removed; nothing else was written


@pytest.mark.parametrize('over,code', [({'size': 1}, 'SIZE_MISMATCH'), ({'md5': '0' * 32}, 'MD5_MISMATCH')])
def test_stream_size_and_md5_checks(parser, tmp_path, over, code):
    path, body = synthetic_day(tmp_path)
    with pytest.raises(ih.IexHistError, match=code) as e:
        _stream(path, body, parser, tmp_path, ['AAA'], **over)
    assert e.value.__suppress_context__ or e.value.__cause__ is None
    assert str(CANARY_E4) not in str(e.value) and '4242' not in str(e.value)


def test_stream_rejects_a_broken_gzip(parser, tmp_path):
    path, body = synthetic_day(tmp_path)
    bad = body[:len(body) // 2]
    path.write_bytes(bad)
    with pytest.raises(ih.IexHistError, match='GZIP_FAILED'):
        _stream(path, bad, parser, tmp_path, ['AAA'])


def test_fetch_day_statuses_ram_only_and_no_price_in_any_text(parser, tmp_path, capsys):
    path, body = synthetic_day(tmp_path)
    md5 = base64.b64encode(hashlib.md5(body).digest()).decode()

    def fetch(url):
        if url == ih.HIST_URL:
            return {DAY: [{'feed': 'TOPS', 'version': '1.6', 'size': str(len(body)),
                           'link': 'https://www.googleapis.com/download/storage/v1/b/iex/o/t?alt=media'}]}
        return {'size': str(len(body)), 'md5Hash': md5}

    def stream(link, symbols, **kw):
        return ih.stream_day(link, symbols, download=lambda _: ['cat', str(path)], **kw)
    keys = {'NYSE:AAA': 'NYSE:AAA', 'NYSE:BBB': 'NYSE:BBB', 'NYSE:CCC': 'NYSE:CCC', 'NASDAQ:PSKY': 'NASDAQ:PSKY',
            'NASDAQ:WBD': 'NASDAQ:WBD', 'TARGET:x': None}
    day = ih.fetch_day(keys, dt.date(2026, 10, 22), parser=parser, workdir=tmp_path / 'w', fetch=fetch, stream=stream)
    assert day.day == '2026-10-22'
    assert day.status == {'NYSE:AAA': 'SUPPLIED', 'NYSE:BBB': 'ODD_LOT_ONLY', 'NYSE:CCC': 'NO_IEX_TRADE', 'NASDAQ:PSKY': 'SUPPLIED',
                          'NASDAQ:WBD': 'NO_IEX_TRADE', 'TARGET:x': 'PRICE_SYMBOL_UNMAPPED'}
    assert day.quotes == {'NYSE:AAA': {'price': CANARY_E4 / 10000, 'currency': 'USD'}, 'NASDAQ:PSKY': {'price': 12.34, 'currency': 'USD'}}
    text = repr(day) + str(day) + json.dumps(day.counts()) + capsys.readouterr().out
    assert '4242' not in text and '12.34' not in text
    with pytest.raises(TypeError):
        pickle.dumps(day)


# ---- month-end store -------------------------------------------------------------------------------------------------
MONTHS = {'2023-12': {'date': '20231229', 'codes': {'NYSE:AAA': 'AAA'}, 'symbols': {'AAA': {'status': 'ROUND', 'price_e4': 500000}, 'BBB': {'status': 'ODD_ONLY', 'price_e4': 1}}},
          '2024-12': {'date': '20241231', 'codes': {'NYSE:AAA': 'AAA', 'NASDAQ:PSKY': 'PARA'}, 'symbols': {'AAA': {'status': 'ROUND', 'price_e4': 400000}, 'PARA': {'status': 'ROUND', 'price_e4': 100000}}},
          '2025-12': {'date': '20251231', 'codes': {'NYSE:AAA': 'AAA', 'NASDAQ:PSKY': 'PSKY'}, 'symbols': {'AAA': {'status': 'ROUND', 'price_e4': 300000}, 'PSKY': {'status': 'ROUND', 'price_e4': 150000}}}}


def test_month_closes_raw_divided_by_share_basis_factor_and_left_out_reasons():
    # items in the production shape (#393 V-PRICE-BASIS, sec_qgv2._share_basis_entry): a factor, or null + its reason
    hist = [{'fiscal_year_end': '2023-12-31', 'value': 1.0, 'share_basis_factor': 4.0},
            {'fiscal_year_end': '2024-12-31', 'value': 1.0, 'share_basis_factor': None, 'share_basis_factor_reason': vf.SPLIT_TIMING_UNCONFIRMED},
            {'fiscal_year_end': '2025-12-31', 'value': 1.0, 'share_basis_factor': 1.0}]
    closes, left = im.month_closes('NYSE:AAA', hist, MONTHS)
    assert closes == {'2023-12': 50.0 / 4.0, '2025-12': 30.0}
    assert left == [('2024-12', vf.SPLIT_TIMING_UNCONFIRMED)]
    hist[1]['share_basis_factor_reason'] = vf.SHARE_BASIS_UNCONFIRMED
    assert im.month_closes('NYSE:AAA', hist, MONTHS)[1] == [('2024-12', vf.SHARE_BASIS_UNCONFIRMED)]
    # no factor (a pre-2026-10-23.1 row), a zero / bool factor, or a reason outside SHARE_BASIS_REASONS -> the fixed reason;
    # never 1.0
    closes, left = im.month_closes('NYSE:AAA', [{'fiscal_year_end': '2023-12-31', 'value': 1.0},
                                                {'fiscal_year_end': '2024-12-31', 'value': 1.0, 'share_basis_factor': True},
                                                {'fiscal_year_end': '2025-12-31', 'value': 1.0, 'share_basis_factor': 0, 'share_basis_factor_reason': 'SPLIT_RATIO_UNVERIFIED'}], MONTHS)
    assert closes == {} and left == [('2023-12', im.FK_MISSING), ('2024-12', im.FK_MISSING), ('2025-12', im.FK_MISSING)]
    assert im.public_v4_reason(left) == im.FK_MISSING


def test_one_parser_copy_and_one_symbol_alias_table():
    """Plan PR-A: ONE C parser (tools/iex_tops/iex_last_trade.c) and ONE dated alias table (providers/iex_hist.SYMBOL_ALIASES).
    The U8 / probe branches carried a byte-identical copy under tools/iex_hist/ and their own table; they must reuse these."""
    skip = {'.git', 'node_modules', '__pycache__', '.pytest_cache'}
    files = [f for f in ROOT.rglob('*') if f.is_file() and not skip & set(f.relative_to(ROOT).parts)]
    assert sorted(f.relative_to(ROOT).as_posix() for f in files if f.suffix == '.c') == ['tools/iex_tops/iex_last_trade.c']
    defines = sorted(f.relative_to(ROOT).as_posix() for f in files if f.suffix == '.py' and f.name != 'test_iex_hist.py'
                     and re.search(r'^\s*SYMBOL_ALIASES\s*[:=]', f.read_text(encoding='utf-8', errors='replace'), re.M))
    assert defines == ['src/investment_system/providers/iex_hist.py']
    assert im.SYMBOL_ALIASES is ih.SYMBOL_ALIASES and im.MONTHEND_BASIS_CUTS is ih.MONTHEND_BASIS_CUTS


# ---- basis day: weekends, market holidays, T+1, half days (owner decision D3) ----------------------------------------------
TRADING_DAYS = ('20261120', '20261123', '20261124', '20261125', '20261127', '20261130')   # 11-26 Thanksgiving: no file


def _hist_index(days=TRADING_DAYS):
    link = 'https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F{d}%2Ftops.pcap.gz?generation=1&alt=media'
    return {d: [{'feed': 'TOPS', 'version': '1.6', 'link': link.format(d=d), 'size': '100'}] for d in days}


@pytest.mark.parametrize('start,requested,basis', [
    # Thanksgiving (no session, no file): a run started after 00:00 UTC on 11-27 belongs to NY day 11-26 -> Wednesday 11-25
    ('2026-11-27T00:37:00+00:00', '2026-11-26', '20261125'),
    # Saturday scheduled run (22:17 UTC): no Saturday file -> Friday
    ('2026-11-21T22:17:00+00:00', '2026-11-21', '20261120'),
    # Monday ~00:37 UTC start = NY Sunday -> Friday
    ('2026-11-23T00:37:00+00:00', '2026-11-22', '20261120'),
    # the day after the half day (11-27, 13:00 close): its file is a normal TOPS day
    ('2026-11-28T22:17:00+00:00', '2026-11-28', '20261127'),
])
def test_basis_is_the_latest_tops_day_on_or_before_the_runs_new_york_day(start, requested, basis):
    day = shard_day(dt.datetime.fromisoformat(start))
    assert day.isoformat() == requested
    assert ih.select_day(_hist_index(), day)[0] == basis


def test_t_plus_one_file_not_yet_generated_uses_the_previous_trading_day():
    # Tuesday 11-24 00:37 UTC = NY Monday 11-23; Monday's file is generated 04:24-10:22 UTC on 11-24, so it is not in the index yet
    index = _hist_index(TRADING_DAYS[:1])
    day = shard_day(dt.datetime(2026, 11, 24, 0, 37, tzinfo=dt.timezone.utc))
    assert day == dt.date(2026, 11, 23) and ih.select_day(index, day)[0] == '20261120'
    # never a later file than the run's day, even if the index already lists one
    assert ih.select_day(_hist_index(), dt.date(2026, 11, 24))[0] == '20261124'


def test_holiday_run_publishes_requested_and_actual_basis_dates(tmp_path):
    md5 = base64.b64encode(hashlib.md5(b'x').digest()).decode()

    def fetch(url):
        return _hist_index() if url == ih.HIST_URL else {'size': '100', 'md5Hash': md5}

    def stream(link, symbols, **kw):
        assert kw['day'] == '20261125' and '20261125' in link
        return {s: ('ROUND', 1234500) for s in symbols}
    requested = shard_day(dt.datetime(2026, 11, 27, 0, 37, tzinfo=dt.timezone.utc))
    day = ih.fetch_day({'NYSE:AAA': 'NYSE:AAA'}, requested, parser='p', workdir=tmp_path, fetch=fetch, stream=stream)
    assert (day.basis_date, day.day) == ('2026-11-26', '2026-11-25')      # published as requested_basis_date / basis_date
    assert day.status == {'NYSE:AAA': 'SUPPLIED'} and '123.45' not in repr(day)


def test_half_day_last_eligible_trade_is_before_the_early_close(parser, tmp_path):
    """2026-11-27 closes at 13:00 New York. Trades after the close are extended-hours flagged (0x40): never the price."""
    day = '20261127'
    t0, t1 = ih.session_ns(day)
    m = 60 * 10**9
    close = t0 + 210 * m                                   # 13:00 New York
    frames = [frame([trade('AAA', close - m, 1000000)]),                     # 12:59 regular: the price
              frame([trade('AAA', close + 30 * m, CANARY_E4, flags=0x40)]),   # 13:30 extended hours: ignored
              frame([trade('BBB', close + 30 * m, 555555, flags=0x40)]),      # only after the close -> no trade
              frame([trade('CCC', close - 2 * m, 777700, flags=0x20)])]       # odd lot only
    body = gzip.compress(pcap(frames), mtime=0)
    path = tmp_path / 'half.pcap.gz'
    path.write_bytes(body)
    rows = _stream(path, body, parser, tmp_path, ['AAA', 'BBB', 'CCC'], day=day)
    assert rows == {'AAA': ('ROUND', 1000000), 'BBB': ('NO_TRADE', None), 'CCC': ('ODD_ONLY', 777700)}


def test_month_closes_psky_merger_cut_and_symbol_check():
    hist = [{'fiscal_year_end': f'{y}-12-31', 'value': 1.0, 'share_basis_factor': 1.0} for y in (2023, 2024, 2025)]
    closes, left = im.month_closes('NASDAQ:PSKY', hist, MONTHS)
    assert closes == {'2025-12': 15.0}
    assert left == [('2023-12', 'MERGER_PRE_BASIS_UNCONFIRMED'), ('2024-12', 'MERGER_PRE_BASIS_UNCONFIRMED')]
    assert im.public_v4_reason(left + [('2026-12', im.FK_MISSING)]) == 'MERGER_PRE_BASIS_UNCONFIRMED'
    # store symbol disagrees with the alias table -> left out (fail closed)
    months = json.loads(json.dumps(MONTHS))
    months['2025-12']['codes']['NYSE:AAA'] = 'ZZZ'
    closes, left = im.month_closes('NYSE:AAA', hist, months)
    assert '2025-12' not in closes and ('2025-12', im.SYMBOL_MISMATCH) in left
    assert im.public_v4_reason([('2025-12', im.SYMBOL_MISMATCH), ('2024-12', im.MONTH_PRICE_MISSING)]) is None


def _release_call(bodies, *, corrupt=None):
    assets, data = {}, {}
    for i, body in enumerate(bodies):
        tag = im.tag_for('20261023', i)
        blob = gzip.compress(json.dumps(body).encode(), mtime=0)
        name = tag + '.json.gz'
        sha = f'{hashlib.sha256(blob).hexdigest()}  {name}\n'.encode()
        if corrupt == i:
            sha = b'0' * 64 + b'\n'
        assets[tag] = [{'name': name, 'id': 10 * i + 1}, {'name': name + '.sha256', 'id': 10 * i + 2}]
        data[10 * i + 1], data[10 * i + 2] = blob, sha
    calls = []

    def call(method, url, headers=None, auth=True):
        calls.append((url, auth))
        if '/releases/tags/' in url:
            tag = url.rsplit('/', 1)[1]
            return (200, {}, json.dumps({'assets': assets[tag]}).encode()) if tag in assets else (404, {}, b'')
        aid = int(url.rsplit('/', 1)[1])
        return 302, {'Location': f'https://objects.example/{aid}'}, b'' if auth else None
    def follow(method, url, headers=None, auth=True):
        if url.startswith('https://objects.example/'):
            assert auth is False      # the token never goes to the redirect host
            return 200, {}, data[int(url.rsplit('/', 1)[1])]
        return call(method, url, headers=headers, auth=auth)
    return follow, calls


def test_read_store_merges_shards_and_checks_sha256():
    bodies = [{'schema': im.SCHEMA, 'months': {'2023-12': MONTHS['2023-12']}}, {'schema': im.SCHEMA, 'months': {'2024-12': MONTHS['2024-12']}}]
    call, _ = _release_call(bodies)
    assert set(im.read_store('20261023', 2, call)) == {'2023-12', '2024-12'}
    call, _ = _release_call(bodies, corrupt=1)
    with pytest.raises(im.MonthEndError, match='SHA256_MISMATCH'):
        im.read_store('20261023', 2, call)
    call, _ = _release_call([bodies[0], bodies[0]])
    with pytest.raises(im.MonthEndError, match='SHARD_INVALID'):       # one month in two shards
        im.read_store('20261023', 2, call)
    call, _ = _release_call(bodies)
    with pytest.raises(im.MonthEndError, match='RELEASE_NOT_FOUND'):
        im.read_store('20261023', 3, call)


# ---- stream failures: first broken stage, whole-pipeline retry, curl limits (rehearsal run 40156760950, 2026-10-25) ---------
def test_curl_command_has_no_retry_and_fails_fast_on_a_stall():
    """A curl --retry after a mid-transfer failure restarts the file from byte 0 into the same stdout pipe (the gzip stream is
    then corrupt): no curl retry. A slow connect or a stalled transfer fails fast instead of eating the step's 12 minutes."""
    cmd = ih.curl_command('https://www.googleapis.com/x')
    assert not any(a.startswith('--retry') for a in cmd)
    assert cmd[cmd.index('--connect-timeout') + 1] == '30'
    assert (cmd[cmd.index('--speed-limit') + 1], cmd[cmd.index('--speed-time') + 1]) == ('1048576', '60')
    assert {'-sS', '--fail'} <= set(cmd) and cmd[-3:] == ['-o', '-', 'https://www.googleapis.com/x']


@pytest.mark.parametrize('codes,broken,stage', [
    ((0, 0, 0), False, None),
    ((0, 0, 3), False, 'PARSER_FAILED'),            # parser fault with clean input
    ((-9, -13, 1), True, 'PARSER_FAILED'),          # parser crash -> gzip SIGPIPE -> our write breaks -> we kill curl
    ((0, -13, 1), False, 'PARSER_FAILED'),
    ((18, 1, 0), False, 'DOWNLOAD_FAILED'),         # curl partial transfer: gzip sees a cut stream, the parser a cut pcap
    ((7, 1, 3), False, 'DOWNLOAD_FAILED'),          # curl connect failure: no bytes, the parser exits 3 (no header)
    ((28, 0, 0), False, 'DOWNLOAD_FAILED'),
    ((0, 1, 0), False, 'GZIP_FAILED'),              # bad gzip data, full download
    ((-9, 1, 3), True, 'GZIP_FAILED'),              # bad gzip quits early -> broken pipe -> we kill curl
    ((-9, 0, 0), True, 'GZIP_FAILED'),
])
def test_failed_stage_names_the_first_broken_stage(codes, broken, stage):
    assert ih.failed_stage(codes, broken) == stage


def _program(path, body):
    import stat
    import sys
    path.write_text(f'#!{sys.executable}\nimport os, sys\n{body}\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def _writer(tmp_path, name, data_path, upto, code):
    """A fake download: writes the first `upto` bytes of a file to stdout, then exits with `code` (curl 18 = partial file)."""
    return [_program(tmp_path / name, f'data = open({str(data_path)!r}, "rb").read()[:{upto}]\n'
                                      f'sys.stdout.buffer.write(data); sys.stdout.flush(); sys.exit({code})')]


def test_stream_curl_failure_mid_stream_is_download_failed_not_gzip(parser, tmp_path):
    path, body = synthetic_day(tmp_path)
    for upto, code in ((len(body) // 2, 18), (0, 7)):        # cut mid-stream; connect failure (no byte: the parser exits 3)
        with pytest.raises(ih.IexHistError, match='^DOWNLOAD_FAILED$'):
            _stream(path, body, parser, tmp_path, ['AAA'], download=lambda link: _writer(tmp_path, 'dl', path, upto, code))


def test_stream_parser_crash_is_parser_failed(tmp_path):
    big = gzip.compress(bytes(range(256)) * 16384, mtime=0, compresslevel=0)   # ~4 MB of synthetic bytes: the pipe breaks
    path = tmp_path / 'big.gz'
    path.write_bytes(big)
    crash = _program(tmp_path / 'crash', 'sys.exit(1)')
    with pytest.raises(ih.IexHistError, match='^PARSER_FAILED$'):
        _stream(path, big, crash, tmp_path, ['AAA'])
    small, sbody = synthetic_day(tmp_path)                 # clean input, the parser reads it all and then fails
    late = _program(tmp_path / 'late', 'sys.stdin.buffer.read()\nsys.exit(4)')
    with pytest.raises(ih.IexHistError, match='^PARSER_FAILED$'):
        _stream(small, sbody, late, tmp_path, ['AAA'])


def test_stream_truly_bad_gzip_with_a_good_download_is_gzip_failed(parser, tmp_path):
    path = tmp_path / 'notgz.bin'
    bad = b'not a gzip stream ' * 4096
    path.write_bytes(bad)
    with pytest.raises(ih.IexHistError, match='^GZIP_FAILED$'):
        _stream(path, bad, parser, tmp_path, ['AAA'])


def test_stream_popen_failure_is_stream_failed(tmp_path):
    def popen(*a, **k):
        raise OSError('synthetic')
    with pytest.raises(ih.IexHistError, match='^STREAM_FAILED$'):
        ih.stream_day('https://www.googleapis.com/x', ['AAA'], day=DAY, size=1, md5='0' * 32, parser='p', workdir=tmp_path / 'w',
                      popen=popen)


def _fetch_for(body):
    md5 = base64.b64encode(hashlib.md5(body).digest()).decode()

    def fetch(url):
        if url == ih.HIST_URL:
            return {DAY: [{'feed': 'TOPS', 'version': '1.6', 'size': str(len(body)),
                           'link': 'https://www.googleapis.com/download/storage/v1/b/iex/o/t?alt=media'}]}
        return {'size': str(len(body)), 'md5Hash': md5}
    return fetch


def test_fetch_day_retries_a_download_failure_once_with_fresh_processes(parser, tmp_path):
    """First attempt: curl cuts the transfer (exit 18) -> DOWNLOAD_FAILED; the whole pipeline runs again from scratch (fresh md5 and
    size count) after the wait and succeeds: 2 attempts, the same rows as one clean attempt."""
    path, body = synthetic_day(tmp_path)
    calls, waits = [], []

    def stream(link, symbols, **kw):
        calls.append(1)
        cut = len(calls) == 1
        return ih.stream_day(link, symbols, download=lambda _: (_writer(tmp_path, 'dl', path, len(body) // 3, 18) if cut
                                                                 else ['cat', str(path)]), **kw)
    keys = {'NYSE:AAA': 'NYSE:AAA', 'NYSE:BBB': 'NYSE:BBB'}
    day = ih.fetch_day(keys, dt.date(2026, 10, 22), parser=parser, workdir=tmp_path / 'w', fetch=_fetch_for(body), stream=stream,
                       sleep=waits.append, monotonic=lambda: 0.0)
    assert (len(calls), waits, day.attempts) == (2, [ih.RETRY_WAIT_S], 2)
    assert day.status == {'NYSE:AAA': 'SUPPLIED', 'NYSE:BBB': 'ODD_LOT_ONLY'}
    assert 'attempts' not in repr(day) and '4242' not in repr(day)
    one = ih.fetch_day(keys, dt.date(2026, 10, 22), parser=parser, workdir=tmp_path / 'w', fetch=_fetch_for(body),
                       stream=lambda link, symbols, **kw: ih.stream_day(link, symbols, download=lambda _: ['cat', str(path)], **kw),
                       sleep=waits.append)
    assert one.attempts == 1 and one.quotes == day.quotes


def _scripted(codes):
    calls = []

    def stream(link, symbols, **kw):
        calls.append(kw['md5'])
        code = codes[len(calls) - 1]
        if code:
            raise ih.IexHistError(code)
        return {s: ('NO_TRADE', None) for s in symbols}
    return stream, calls


def _fetch_day_with(stream, tmp_path, **kw):
    return ih.fetch_day({'NYSE:AAA': 'NYSE:AAA'}, dt.date(2026, 10, 22), parser='p', workdir=tmp_path, fetch=_fetch_for(b'x'),
                        stream=stream, **kw)


@pytest.mark.parametrize('first', ['DOWNLOAD_FAILED', 'GZIP_FAILED', 'SIZE_MISMATCH', 'MD5_MISMATCH', 'STREAM_FAILED'])
def test_transfer_shaped_failures_are_retried_once(tmp_path, first):
    stream, calls = _scripted([first, None])
    waits = []
    day = _fetch_day_with(stream, tmp_path, sleep=waits.append, monotonic=lambda: 0.0)
    assert (len(calls), waits, day.attempts, day.status) == (2, [15], 2, {'NYSE:AAA': 'NO_IEX_TRADE'})
    stream, calls = _scripted([first, first, None])
    with pytest.raises(ih.IexHistError, match=f'^{first}$') as e:            # two attempts at most
        _fetch_day_with(stream, tmp_path, sleep=waits.append, monotonic=lambda: 0.0)
    assert (len(calls), e.value.attempts) == (2, 2)
    assert e.value.__cause__ is None and e.value.__context__ is None


@pytest.mark.parametrize('code', ['PARSER_FAILED', 'PARSER_OUTPUT_INVALID', 'PARSER_SYMBOLS_MISMATCH', 'SYMBOLS_INVALID'])
def test_parser_and_input_failures_are_not_retried(tmp_path, code):
    stream, calls = _scripted([code, None])
    waits = []
    with pytest.raises(ih.IexHistError, match=f'^{code}$') as e:
        _fetch_day_with(stream, tmp_path, sleep=waits.append, monotonic=lambda: 0.0)
    assert (len(calls), waits, e.value.attempts) == (1, [], 1)


def test_no_second_attempt_after_a_slow_first_one(tmp_path):
    """Time budget (`timeout -k 30s 12m`): a first attempt that ended after RETRY_START_LIMIT_S is not followed by a second full
    one (it would not finish inside the step); its own code is reported."""
    stream, calls = _scripted(['DOWNLOAD_FAILED', None])
    ticks = iter([0.0, ih.RETRY_START_LIMIT_S + 1.0])
    waits = []
    with pytest.raises(ih.IexHistError, match='^DOWNLOAD_FAILED$') as e:
        _fetch_day_with(stream, tmp_path, sleep=waits.append, monotonic=lambda: next(ticks))
    assert (len(calls), waits, e.value.attempts) == (1, [], 1)
    # the budget arithmetic in the module comment: two full attempts at the measured rate fit with room for the rest of the step
    size, rate = 13_079_032_608, 11.84e9 / (3.2 * 60)
    two = 2 * size / rate + ih.RETRY_WAIT_S
    assert size / rate < ih.RETRY_START_LIMIT_S and two < 8 * 60 < 12 * 60
    assert ih.RETRY_START_LIMIT_S + ih.RETRY_WAIT_S + size / rate < 9 * 60


def test_no_stream_no_attempt(tmp_path):
    day = ih.fetch_day({'TARGET:x': None}, dt.date(2026, 10, 22), parser='p', workdir=tmp_path, fetch=_fetch_for(b'x'),
                       stream=lambda *a, **k: pytest.fail('no symbol needs a download'))
    assert day.attempts == 0 and day.status == {'TARGET:x': 'PRICE_SYMBOL_UNMAPPED'}
