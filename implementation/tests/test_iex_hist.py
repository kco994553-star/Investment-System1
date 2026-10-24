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
import shutil
import struct
import subprocess

import pytest

from investment_system.providers import iex_hist as ih
from investment_system.providers import iex_monthend as im

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
    hist = [{'fiscal_year_end': '2023-12-31', 'value': 1.0, 'share_basis_factor': 4.0, 'share_basis_factor_reason': None},
            {'fiscal_year_end': '2024-12-31', 'value': 1.0, 'share_basis_factor': None, 'share_basis_factor_reason': 'SPLIT_RATIO_UNVERIFIED'},
            {'fiscal_year_end': '2025-12-31', 'value': 1.0, 'share_basis_factor': 1}]
    closes, left = im.month_closes('NYSE:AAA', hist, MONTHS)
    assert closes == {'2023-12': 50.0 / 4.0, '2025-12': 30.0}
    assert left == [('2024-12', 'SPLIT_RATIO_UNVERIFIED')]
    # missing field / non-code reason -> the fixed reason; never 1.0
    closes, left = im.month_closes('NYSE:AAA', [{'fiscal_year_end': '2023-12-31', 'value': 1.0},
                                                {'fiscal_year_end': '2025-12-31', 'value': 1.0, 'share_basis_factor': 0, 'share_basis_factor_reason': 'bad text'}], MONTHS)
    assert closes == {} and left == [('2023-12', im.FK_MISSING), ('2025-12', im.FK_MISSING)]
    assert im.public_v4_reason(left) == im.FK_MISSING


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
