"""One-off private IEX day store (owner approval 2026-11-14, QGV 555 V): iex_day_private_once.private_day on synthetic fakes only.
The requested day is exact (another index day is refused), the request is split into shards, the stdout line carries counts
only, and the one payload goes to the upload callable and is removed from disk afterwards."""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import iex_day_private_once as pub  # noqa: E402

LINK = 'https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20261104%2FTOPS.pcap.gz?alt=media'
MD5 = '0' * 32


def fetch(url):
    if url == pub.iex_hist.HIST_URL:
        return {'20261104': [{'feed': 'TOPS', 'version': '1.6', 'protocol': 'IEXTP1', 'link': LINK, 'size': '1000'}]}
    return {'size': '1000', 'md5Hash': base64.b64encode(bytes.fromhex(MD5)).decode()}


def stream(link, symbols, **kw):
    return {s: (('ROUND', 1234567) if i % 2 == 0 else ('NO_TRADE', None)) for i, s in enumerate(sorted(symbols))}


def request(tmp, day='2026-11-04', codes=('NYSE:AAA', 'NASDAQ:BBB', 'HELD:CCC', 'NYSE:DDD')):
    p = tmp / 'request.json'
    p.write_text(json.dumps({'schema_version': 'iex-day-request/1', 'day': day, 'codes': list(codes)}))
    return p


def test_shard_payload_and_counts_only(tmp_path):
    seen = {}

    def upload(out_dir, *, tag, token):
        seen['tag'], seen['token'] = tag, token
        seen['payload'] = json.loads((Path(out_dir) / 'iex-day.json').read_text())
        return 'RAW_UPLOADED bytes=1 sha256=' + 'a' * 64

    line = pub.private_day(day='2026-11-04', request=request(tmp_path), shard=1, shards=2, parser='x', workdir=tmp_path / 'w',
                           token='t', deadline=None, fetch=fetch, stream=stream, store=upload)
    assert line.startswith('IEX_DAY status=OK day=2026-11-04 tag=iex-day-20261104-shard1 codes=2 symbols=2')
    assert '1234567' not in line and '123.4567' not in line
    p = seen['payload']
    assert p['schema_version'] == 'iex-day/1' and p['day'] == '2026-11-04' and p['shard'] == 1 and p['shards'] == 2
    assert set(p['codes']) == set(sorted(['NYSE:AAA', 'NASDAQ:BBB', 'HELD:CCC', 'NYSE:DDD'])[1::2])
    assert p['adjustment_basis'] == 'AS_TRADED' and p['file'] == {'size': 1000, 'md5': MD5}
    assert not (tmp_path / 'w' / 'iex-day-20261104-shard1' / 'iex-day.json').exists()


def test_other_day_and_missing_token_are_refused(tmp_path):
    never = lambda *a, **k: (_ for _ in ()).throw(AssertionError('no upload'))  # noqa: E731
    other = pub.private_day(day='2026-11-05', request=request(tmp_path, day='2026-11-05'), shard=0, shards=1, parser='x',
                            workdir=tmp_path, token='t', deadline=None, fetch=fetch, stream=stream, store=never)
    assert other == 'IEX_DAY status=REFUSED reason=NOT_REQUESTED_DAY'
    assert pub.private_day(day='2026-11-04', request=request(tmp_path), shard=0, shards=1, parser='x', workdir=tmp_path,
                           token=None, deadline=None, fetch=fetch, stream=stream, store=never) == 'IEX_DAY status=NOT_RUN reason=TOKEN_MISSING'
    assert pub.private_day(day='2026-11-04', request=request(tmp_path, day='2026-11-03'), shard=0, shards=1, parser='x',
                           workdir=tmp_path, token='t', deadline=None, fetch=fetch, stream=stream,
                           store=never) == 'IEX_DAY status=REFUSED reason=REQUEST_INVALID'
