"""One-shot IEX 2026-11-02 preservation (tools/iex_day_preserve_once.py). SYNTHETIC data only, no network.

The real C parser is compiled (fixture from test_iex_hist) and fed a synthetic TOPS 1.6 pcap.gz built with test_iex_hist's
builders; the body "download" is `cat` of that file, the release store is a local directory (FakeStore), and the private
input (connected-final.json + its manifest) is made up here with invented tickers. Every price below is made up.
In-process runs inject a spy for public_price_boundary.require_price_source (pytest is not an approved route); the dry-run
subprocess test uses the real boundary function, which passes because the tool is the second ACTIONS_PRICE_ROUTES entry.
"""
import base64
from datetime import datetime
import gzip
import hashlib
import importlib.util
import io
import json
import re
import struct
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

import pytest

from investment_system import public_price_boundary as boundary
from investment_system.providers import iex_hist as ih
from tests.test_iex_hist import frame, parser, pcap, status_msg, trade  # noqa: F401 - `parser` is a fixture

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TOOL = ROOT / 'tools' / 'iex_day_preserve_once.py'
_SPEC = importlib.util.spec_from_file_location('iex_day_preserve_once', TOOL)
pre = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pre)

DAY = pre.DAY
RID = pre.DRY_RUN_ID
LINK = 'https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20261102%2Fsynthetic.pcap.gz?generation=1&alt=media'
CANARY_E4 = 7373_7373                       # $7373.7373: must never appear in any log line
# Invented codes / CIKs at the 11 ROW_INDEXES positions (none is a real candidate). PSKY / WBD exercise the alias table.
CODES = {12: 'NYSE:QZPA', 13: 'NASDAQ:PSKY', 17: 'NYSE:QZPB', 25: 'NYSE:QZPC', 29: 'NYSE:QZPD', 30: 'NASDAQ:WBD',
         34: 'NYSE:QZPE', 38: 'NYSE:QZPF', 51: 'NYSE:QZP.G', 64: 'NYSE:QZPH', 67: 'NYSE:QZPI'}
CIK = {i: f'{9900000000 + i:010d}' for i in range(68)}
FORBIDDEN_IN_LOGS = ('QZP', 'SKYD', 'PSKY', 'WBD', '7373', '9900000', 'Authorization', 'token', 'Bearer', '{', 'message',
                     'documentation_url', '<html', 'http://', 'https://', 'googleapis', 'Traceback')


def directory(sym, ts):
    """Security Directory message (0x44): only its type and symbol matter to the parser."""
    return struct.pack('<BBq8s', 0x44, 0, ts, sym.encode('ascii').ljust(8, b' ')) + bytes(13)


def synthetic_body():
    t0, t1 = ih.session_ns(DAY)
    m = 60 * 10**9
    frames = [frame([directory(s, t0 - 9 * m) for s in ('QZPA', 'SKYD', 'QZPB', 'QZPC', 'QZPE', 'QZPF', 'QZP.G', 'QZPH', 'QZPI')]),
              frame([trade('QZPA', t0 + m, 1000000), trade('QZPA', t0 + 2 * m, CANARY_E4)]),   # last round lot wins
              frame([trade('QZPA', t0 + 3 * m, 999999, flags=0x20)]),                          # odd lot: never the price
              frame([trade('SKYD', t0 + 4 * m, 123400), trade('PSKY', t0 + 4 * m, 999900)]),
              frame([trade('QZPB', t0 + m, 555555, flags=0x20)]),                              # odd lot only
              frame([status_msg('QZPC', t0 - m)]),                                             # listed, no trade
              frame([trade('QZPE', t1 + m, 777777, flags=0x40), trade('QZPE', t0 - m, 777777)]),   # outside the session
              frame([trade('QZPF', t0 + m, ih.MAX_PRICE_E4)]),                                 # not a price
              frame([trade('QZP.G', t1 - 1, 4200)]),                                           # last ns of the session
              frame([trade('QZPH', t0 + m, 0)]),                                               # zero: not a price
              frame([trade('QZPI', t0 + 5 * m, 101)]),
              frame([trade('WBD', t0 + 5 * m, 888800)])]                                       # never used (alias None)
    return gzip.compress(pcap(frames * 20), mtime=0)


def private_inputs(codes=CODES, ciks=CIK):
    rows = [{'code': codes.get(i, f'NYSE:QZF{i:02d}'), 'cik': ciks[i]} for i in range(68)]
    connected = json.dumps({'schema_version': 'synthetic', 'rows': rows}).encode()
    manifest = json.dumps({'files': [{'path': 'README.md', 'sha256': '0' * 64, 'bytes': 1},
                                     {'path': 'connected-final.json', 'sha256': hashlib.sha256(connected).hexdigest(),
                                      'bytes': len(connected)}]}).encode()
    return {f'{pre.INPUT_DIR}/manifest.json': manifest, f'{pre.INPUT_DIR}/connected-final.json': connected}, \
        hashlib.sha256(manifest).hexdigest()


def index_for(size, link=LINK):
    return {'20261030': [{'feed': 'TOPS', 'version': '1.6', 'link': link.replace('20261102', '20261030'), 'size': '5'}],
            DAY: [{'feed': 'TOPS', 'version': '1.6', 'protocol': 'IEXTP1', 'link': link, 'size': str(size)},
                  {'feed': 'DEEP', 'version': '1.0', 'link': link, 'size': '99'}],
            '20261103': [{'feed': 'TOPS', 'version': '1.6', 'link': link.replace('20261102', '20261103'), 'size': '7'}]}


class Source:
    """Fake source functions; every request and every boundary check is appended to one event list, in order."""

    def __init__(self, body_path, index, meta, get=None):
        self.body_path, self.index, self.meta, self.events, self._get = body_path, index, meta, [], get

    def require(self, kind, url):
        assert boundary.price_source_kind(url) == kind
        self.events.append(('require', kind, url))

    def get(self, url, cap):
        self.events.append(('request', url))
        if self._get:
            return self._get(url, cap)
        return json.dumps(self.index if url == ih.HIST_URL else self.meta).encode()

    def body_command(self, link, max_time):
        self.events.append(('request', link))
        return ['cat', str(self.body_path)]

    @property
    def urls(self):
        return [e[1] for e in self.events if e[0] == 'request']


def assert_every_request_was_required(events):
    for i, e in enumerate(events):
        if e[0] == 'request':
            assert i > 0 and events[i - 1][0] == 'require' and events[i - 1][2] == e[1], events


def meta_of(body, size=None, md5=None):
    return {'size': str(len(body) if size is None else size),
            'md5Hash': base64.b64encode(md5 or hashlib.md5(body).digest()).decode()}


def make(tmp_path, *, body=None, served=None, index=None, meta=None, codes=CODES, store_cls=None, existing=None, sha=None,
         get=None):
    body = synthetic_body() if body is None else body
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / 'served.pcap.gz'
    path.write_bytes(body if served is None else served)
    inputs, manifest_sha = private_inputs(codes)
    counts = pre.Counts()
    store = (store_cls or pre.FakeStore)(counts, tmp_path / 'store', inputs, existing=existing)
    src = Source(path, index_for(len(body)) if index is None else index, meta_of(body) if meta is None else meta, get=get)
    source = pre.SourceClient(counts, get=src.get, body_command=src.body_command, require=src.require)
    kw = dict(store=store, source=source, counts=counts, workdir=tmp_path / 'work', run_id=RID,
              chunk_bytes=max(1, len(body) // 3), reserve=0, disk_free=lambda p: 10**12, expected_manifest_sha=sha or manifest_sha,
              versions={})
    return kw, store, src, counts, body


RUN_KEYS = ('chunk_bytes', 'max_chunks', 'disk_free', 'min_free', 'token_present', 'reserve', 'fs_id', 'run_id', 'popen')


def run(parser, tmp_path, **over):
    run_kw = {k: over.pop(k) for k in RUN_KEYS if k in over}
    kw, store, src, counts, body = make(tmp_path, **over)
    kw.update(run_kw)
    man = pre.run(parser=parser, **kw)
    assert_every_request_was_required(src.events)
    return man, store, src, counts, body


def local_files(tmp_path):
    work = tmp_path / 'work'
    return sorted(p.relative_to(work).as_posix() for p in work.rglob('*') if p.is_file()) if work.exists() else []


def names(store):
    return sorted(a['name'] for a in store.assets.values())


def symfile_bytes():
    return len(pre.symbols_file_bytes(pre.map_symbols(CODES.values())))


# ---- exact date, caps, budget, boundary ------------------------------------------------------------------------------------
def test_exact_date_only_never_another_day():
    entry = pre.select_exact_day(index_for(1234))
    assert entry['size'] == 1234 and entry['link'] == LINK
    no_day = {k: v for k, v in index_for(1).items() if k != DAY}
    with pytest.raises(pre.PreserveError, match='^NO_FILE_FOR_EXACT_DAY$'):
        pre.select_exact_day(no_day)               # 10-30 and 11-03 exist: neither is taken
    two = index_for(1)
    two[DAY].append(dict(two[DAY][0]))
    with pytest.raises(pre.PreserveError, match='^INDEX_AMBIGUOUS$'):
        pre.select_exact_day(two)
    with pytest.raises(pre.PreserveError, match='^INDEX_LINK_INVALID$'):
        pre.select_exact_day(index_for(1, link='https://example.com/x.pcap.gz'))
    with pytest.raises(pre.PreserveError, match='^INDEX_LINK_INVALID$'):
        pre.select_exact_day({'20261031': index_for(1)[DAY]}, '20261031')     # a Saturday file is never a session day
    for size, code in ((0, 'INDEX_INVALID'), ('x', 'INDEX_INVALID'), (pre.BODY_CAP + 1, 'BODY_CAP_EXCEEDED')):
        bad = index_for(1)
        bad[DAY][0]['size'] = size
        with pytest.raises(pre.PreserveError, match=f'^{code}$'):
            pre.select_exact_day(bad)
    assert pre.select_exact_day(index_for(pre.BODY_CAP))['size'] == 20_000_000_000


def _client(get, **kw):
    return pre.SourceClient(pre.Counts(), get=get, require=lambda kind, url: None, **kw)


def test_caps_on_index_and_metadata_bodies():
    assert (pre.INDEX_CAP, pre.METADATA_CAP, pre.BODY_CAP) == (8 * 1024 * 1024, 1024 * 1024, 20_000_000_000)
    seen = []

    def get(url, cap):
        seen.append(cap)
        return b' ' * (cap + 1)
    for call, code in ((lambda s: s.index(), 'INDEX_TOO_LARGE'), (lambda s: s.metadata(LINK), 'METADATA_TOO_LARGE')):
        with pytest.raises(pre.PreserveError, match=f'^{code}$'):
            call(_client(get))
    assert seen == [pre.INDEX_CAP, pre.METADATA_CAP]


def test_metadata_size_must_equal_index_and_stay_under_the_cap():
    entry = pre.select_exact_day(index_for(100))
    assert pre.object_checks(entry, _client(lambda url, cap: json.dumps(meta_of(b'x', size=100)).encode())) == \
        (100, hashlib.md5(b'x').hexdigest())
    with pytest.raises(pre.PreserveError, match='^METADATA_SIZE_MISMATCH$'):
        pre.object_checks(entry, _client(lambda url, cap: json.dumps(meta_of(b'x', size=101)).encode()))
    with pytest.raises(pre.PreserveError, match='^METADATA_INVALID$'):
        pre.object_checks(entry, _client(lambda url, cap: b'{"size": "100"}'))
    with pytest.raises(pre.PreserveError, match='^BODY_CAP_EXCEEDED$'):
        pre.object_checks(dict(entry, size=pre.BODY_CAP + 1),
                          _client(lambda url, cap: json.dumps(meta_of(b'x', size=pre.BODY_CAP + 1)).encode()))


def test_source_budget_three_gets_each_kind_once_exact_urls_each_one_required():
    counts, events = pre.Counts(), []
    src = pre.SourceClient(counts, get=lambda url, cap: events.append(('request', url)) or b'{}',
                           body_command=lambda link, t: events.append(('request', link)) or ['true'],
                           require=lambda kind, url: events.append(('require', kind, url)))
    with pytest.raises(pre.PreserveError, match='^SOURCE_URL_INVALID$'):
        src.body_command('https://example.com/x', 1)
    assert counts.snapshot()['source_get'] == 0 and events == []
    src.index()
    with pytest.raises(pre.PreserveError, match='^SOURCE_REQUEST_REPEATED$'):
        src.index()
    src.metadata(LINK)
    bucket = 'https://storage.googleapis.com/iex/data/feeds/20261102/x.pcap.gz'
    src.body_command(bucket, 5)
    assert counts.snapshot()['source_get'] == 3 and src.used == ['INDEX', 'METADATA', 'BODY']
    assert [e[1] for e in events if e[0] == 'require'] == ['IEX_HIST_INDEX', 'IEX_HIST_OBJECT', 'IEX_HIST_BUCKET']
    assert_every_request_was_required(events)
    small = _client(lambda url, cap: b'{}', budget=1)
    small.index()
    with pytest.raises(pre.PreserveError, match='^SOURCE_BUDGET_EXCEEDED$'):
        small.metadata(LINK)
    curl = pre.curl_body_command(LINK, 99)
    assert curl[:2] == ['curl', '-sS'] and curl[-1] == LINK and '--max-time' in curl and '--fail' in curl
    assert not {'--retry', '-C', '--continue-at', '-r', '--range', '-L', '--location', '-v', '--verbose'} & set(curl)


def test_the_boundary_refusal_stops_every_source_request(parser, tmp_path):
    """Without an injected spy the tool asks the real public_price_boundary.require_price_source: pytest is not an approved
    route, so the first source request is refused (SOURCE_ROUTE_NOT_ALLOWED) and nothing is sent."""
    sent = []
    client = pre.SourceClient(pre.Counts(), get=lambda url, cap: sent.append(url), body_command=lambda l, t: sent.append(l))
    for call in (lambda: client.index(), lambda: client.metadata(LINK), lambda: client.body_command(LINK, 1)):
        with pytest.raises(pre.PreserveError, match='^SOURCE_ROUTE_NOT_ALLOWED$'):
            call()
    assert sent == [] and client.counts.snapshot()['source_get'] == 0
    kw, store, src, counts, _ = make(tmp_path)
    kw['source'] = pre.SourceClient(counts, get=src.get, body_command=src.body_command)       # the real boundary
    man = pre.run(parser=parser, **kw)
    assert man['failed_stage'] == 'SOURCE_ROUTE_NOT_ALLOWED' and src.events == [] and counts.snapshot()['source_get'] == 0
    assert boundary.ACTIONS_PRICE_ROUTES[1] == 'implementation/tools/iex_day_preserve_once.py'
    assert names(store) == [pre.manifest_name(RID)] and json.loads(store.get(pre.manifest_name(RID)))['state'] == 'FAILED'


# ---- private input ---------------------------------------------------------------------------------------------------------
def test_private_input_hashes_and_row_layout():
    inputs, sha = private_inputs()
    manifest, connected = inputs[f'{pre.INPUT_DIR}/manifest.json'], inputs[f'{pre.INPUT_DIR}/connected-final.json']
    codes, receipt = pre.select_codes(manifest, connected, expected_manifest_sha=sha)
    assert codes == [CODES[i] for i in pre.ROW_INDEXES]
    assert receipt['file_sha256'] == hashlib.sha256(connected).hexdigest() and receipt['commit'] == pre.INPUT_COMMIT
    assert receipt['git_blob_sha1'] == hashlib.sha1(b'blob %d\0' % len(connected) + connected).hexdigest()
    with pytest.raises(pre.PreserveError, match='^PRIVATE_INPUT_MANIFEST_SHA_MISMATCH$'):
        pre.select_codes(manifest, connected)      # the pinned real manifest hash: a synthetic manifest never matches it
    with pytest.raises(pre.PreserveError, match='^PRIVATE_INPUT_SHA_MISMATCH$'):
        pre.select_codes(manifest, connected.replace(b'QZPA', b'QZPZ'), expected_manifest_sha=sha)
    for bad in ({12: 'QZPA'}, {12: 'NYSE:qzpa'}, {12: 'NYSE:QZPB'}):      # no exchange, lower case, duplicate code
        inputs, sha = private_inputs({**CODES, **bad})
        with pytest.raises(pre.PreserveError, match='^PRIVATE_INPUT_INVALID$'):
            pre.select_codes(*inputs.values(), expected_manifest_sha=sha)
    assert pre.INPUT_MANIFEST_SHA256 == 'd7b5c0715496857644f1971b236141b296caf80207f56fce40d0c204a22fbb2a'
    assert pre.ROW_INDEXES == (12, 13, 17, 25, 29, 30, 34, 38, 51, 64, 67)


def test_symbols_mapped_with_the_repository_alias_table():
    symbol_of = pre.map_symbols(CODES.values())
    assert symbol_of['NASDAQ:PSKY'] == 'SKYD' and symbol_of['NASDAQ:WBD'] is None and symbol_of['NYSE:QZP.G'] == 'QZP.G'
    assert symbol_of == {c: ih.iex_symbol(c, '2026-11-02') for c in CODES.values()}
    listed = pre.symbols_file_bytes(symbol_of).decode().split()
    assert listed == sorted(listed) and 'WBD' not in listed and 'PSKY' not in listed and len(listed) == 10


# ---- the whole run --------------------------------------------------------------------------------------------------------
EXPECT = {'NYSE:QZPA': ('PRICE', 'REGULAR_SESSION_ROUND_LOT_LAST_TRADE', '7373.7373'),
          'NASDAQ:PSKY': ('PRICE', 'REGULAR_SESSION_ROUND_LOT_LAST_TRADE', '12.3400'),
          'NYSE:QZPB': ('NO_TRADE', 'ODD_LOT_ONLY', None),
          'NYSE:QZPC': ('NO_TRADE', 'NO_REGULAR_SESSION_ROUND_LOT_TRADE', None),
          'NYSE:QZPD': ('NOT_IN_FILE', 'SYMBOL_NOT_IN_FILE', None),
          'NASDAQ:WBD': ('NOT_IN_FILE', 'IEX_SYMBOL_NONE_FROM_ALIAS_DATE', None),
          'NYSE:QZPE': ('NO_TRADE', 'NO_REGULAR_SESSION_ROUND_LOT_TRADE', None),
          'NYSE:QZPF': ('PRICE_INVALID', 'PRICE_OUT_OF_RANGE', None),
          'NYSE:QZP.G': ('PRICE', 'REGULAR_SESSION_ROUND_LOT_LAST_TRADE', '0.4200'),
          'NYSE:QZPH': ('PRICE_INVALID', 'PRICE_OUT_OF_RANGE', None),
          'NYSE:QZPI': ('PRICE', 'REGULAR_SESSION_ROUND_LOT_LAST_TRADE', '0.0101')}


def test_complete_run(parser, tmp_path, capfd):
    man, store, src, counts, body = run(parser, tmp_path)
    assert man['state'] == 'COMPLETE', man.get('failed_stage')
    stored = json.loads(store.get(pre.manifest_name(RID)))
    assert stored['state'] == 'COMPLETE' and stored['run_id'] == RID and stored['release']['created_by_this_run'] is True
    assert stored['received']['sha256'] == hashlib.sha256(body).hexdigest()
    assert stored['received']['md5'] == hashlib.md5(body).hexdigest() and stored['received']['bytes'] == len(body)
    assert stored['source']['index_size'] == stored['source']['metadata_size'] == len(body)
    assert stored['parser']['source_sha256'] == hashlib.sha256((ROOT / 'tools/iex_tops/iex_last_trade.c').read_bytes()).hexdigest()
    assert stored['session_window_ns'] == list(ih.session_ns(DAY)) and stored['parser_stats']['packets'] == 12 * 20
    assert dict(stored['reassembly'], verified_at_utc=None) == {
        'mode': 'STREAMING_NO_FILE', 'bytes': len(body), 'chunks': len(stored['chunks']), 'sha256_match': True,
        'md5_match': True, 'gzip_test_ok': True, 'verified_at_utc': None}
    chunks = stored['chunks']
    n = len(chunks)
    assert b''.join(store.get(c['name']) for c in chunks) == body                              # lossless
    assert [c['name'] for c in chunks] == [f'iex-tops-20261102-{RID}.part-{i:02d}-of-{n:02d}' for i in range(1, n + 1)]
    assert all(c['sha256'] == hashlib.sha256(store.get(c['name'])).hexdigest() for c in chunks)
    assert local_files(tmp_path) == []                                                         # every local copy deleted
    assert names(store) == sorted([c['name'] for c in chunks] + [pre.derived_name(RID), pre.manifest_name(RID)])
    assert 0 < stored['disk']['peak_bytes'] <= len(body) + symfile_bytes()
    raw = store.get(pre.derived_name(RID))
    derived = json.loads(raw)
    assert stored['derived'] == {'name': pre.derived_name(RID), 'schema_version': 'iex-day-financial11-last-trade/1',
                                 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'rows': 11,
                                 'states': derived['states'], 'generated_at_utc': derived['generated_at_utc']}
    assert derived['manifest'] == pre.manifest_name(RID) and derived['original']['sha256'] == stored['received']['sha256']
    assert {r['code']: (r['state'], r['reason'], r['price']) for r in derived['rows']} == EXPECT
    assert derived['states'] == {'PRICE': 4, 'NO_TRADE': 3, 'NOT_IN_FILE': 2, 'PRICE_INVALID': 2}
    text = json.dumps(derived).lower()
    assert 'close' not in text and 'ohlcv' not in text
    assert counts.snapshot() == {'source_get': 3, 'private_read': 2, 'release_lookup': 1, 'release_create': 1,
                                 'upload': n + 2, 'download': 4 * n, 'delete': 0}
    assert stored['requests'] == counts.snapshot()
    assert src.urls == [ih.HIST_URL, ih.gcs_metadata_url(LINK), LINK]
    assert [e[1] for e in src.events if e[0] == 'require'] == ['IEX_HIST_INDEX', 'IEX_HIST_OBJECT', 'IEX_HIST_OBJECT']
    out, err = capfd.readouterr()
    assert err == ''
    assert_clean_logs(out)


@pytest.mark.parametrize('div,extra', [(3, 0), (3, 1), (1, 0), (7, 5)])
def test_chunk_boundaries(parser, tmp_path, div, extra):
    body = synthetic_body()
    size = len(body) // div + extra if div > 1 else len(body)
    man, store, *_ = run(parser, tmp_path, chunk_bytes=size)
    assert man['state'] == 'COMPLETE'
    sizes = [c['size'] for c in man['chunks']]
    assert len(sizes) == -(-len(body) // size) == man['source']['expected_chunks']
    assert all(s == size for s in sizes[:-1]) and 0 < sizes[-1] <= size and sum(sizes) == len(body)


def test_exact_multiple_has_no_empty_last_chunk_and_wide_numbering(parser, tmp_path):
    body = synthetic_body()
    k = next(k for k in range(2, len(body) + 1) if len(body) % k == 0)
    man, *_ = run(parser, tmp_path, chunk_bytes=len(body) // k, max_chunks=len(body))
    assert man['state'] == 'COMPLETE' and [c['size'] for c in man['chunks']] == [len(body) // k] * k
    man2, *_ = run(parser, tmp_path / 'b', chunk_bytes=len(body))
    assert [c['name'] for c in man2['chunks']] == [f'iex-tops-20261102-{RID}.part-01-of-01']
    assert pre.chunk_name(RID, 7, 120) == f'iex-tops-20261102-{RID}.part-007-of-120'


def test_chunk_limit(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, chunk_bytes=len(body) // 5, max_chunks=3)
    assert man['state'] == 'FAILED' and man['failed_stage'] == 'CHUNK_LIMIT_EXCEEDED'
    assert counts.snapshot()['source_get'] == 2          # refused from the metadata size, before the body GET


def test_many_chunks_upload_in_the_background(parser, tmp_path):
    man, store, src, counts, body = run(parser, tmp_path, chunk_bytes=64, max_chunks=10**6)
    n = -(-len(body) // 64)
    assert man['state'] == 'COMPLETE' and len(man['chunks']) == n and counts.snapshot()['download'] == 4 * n
    assert local_files(tmp_path) == []


# ---- F: source-native derived file and its separately named times -------------------------------------------------------
def test_derived_rows_and_times(parser, tmp_path):
    clock = iter(range(1_793_000_000, 1_793_000_100))                  # one distinct synthetic second per now() call
    kw, store, src, counts, body = make(tmp_path)
    man = pre.run(parser=parser, now=lambda: float(next(clock)), **kw)
    assert man['state'] == 'COMPLETE'
    derived = json.loads(store.get(pre.derived_name(RID)))
    t0, t1 = ih.session_ns(DAY)
    assert (derived['schema_version'], derived['basis_date'], derived['unit'], derived['currency']) == \
        ('iex-day-financial11-last-trade/1', '2026-11-02', 'USD/share', 'USD')
    assert (derived['basis_kind'], derived['adjustment_basis']) == (ih.BASIS_KIND, ih.ADJUSTMENT_BASIS)
    assert [r['row_index'] for r in derived['rows']] == list(pre.ROW_INDEXES)
    for r in derived['rows']:
        assert r['state'] in pre.STATES and r['reason'] and r['basis_date'] == '2026-11-02'
        assert r['source'] == pre.SOURCE_LABEL and r['parser_source_sha256'] == man['parser']['source_sha256']
        if r['state'] == 'PRICE':
            assert re.fullmatch(r'[0-9]+\.[0-9]{4}', r['price']) and t0 <= r['last_trade_ns'] < t1
            assert r['last_trade_utc'] == pre.ns_utc(r['last_trade_ns'])
        else:
            assert r['price'] is r['last_trade_ns'] is r['last_trade_utc'] is None
    rows = {r['code']: r for r in derived['rows']}
    assert rows['NYSE:QZPA']['last_trade_ns'] == t0 + 120 * 10**9
    assert rows['NYSE:QZPA']['last_trade_utc'] == '2026-11-02T14:32:00.000000000Z'
    assert rows['NYSE:QZP.G']['last_trade_utc'] == '2026-11-02T20:59:59.999999999Z'      # all nine digits, no rounding
    assert rows['NASDAQ:PSKY']['iex_symbol'] == 'SKYD' and rows['NASDAQ:WBD']['iex_symbol'] is None
    assert 'close' not in json.dumps(derived).lower() and 'ohlcv' not in json.dumps(derived).lower()
    # Times: each kept apart, in the order the stages happen; acquisition = the verified receipt, not the job's end.
    order = [man['received']['started_at_utc'], man['received']['completed_at_utc'], man['chunks_preserved_at_utc'],
             man['reassembly']['verified_at_utc'], derived['generated_at_utc'], man['written_at_utc']]
    assert order == sorted(order) and len(set(order)) == len(order)
    assert derived['acquired_at_utc'] == man['received']['completed_at_utc'] != man['written_at_utc']
    assert all(t.endswith('Z') and datetime.fromisoformat(t.replace('Z', '+00:00')).utcoffset().total_seconds() == 0
               for t in order)
    stored = json.loads(store.get(pre.manifest_name(RID)))
    assert stored['received']['completed_at_utc'] == derived['acquired_at_utc'] and 'finished_at' not in stored['timings']


def test_price_text_is_exact():
    assert pre.price_text(1000000) == '100.0000' and pre.price_text(101) == '0.0101' and pre.price_text(12345678) == '1234.5678'
    assert pre.price_text(CANARY_E4) == '7373.7373' and pre.price_text(ih.MAX_PRICE_E4 - 1) == '9999999.9999'


# ---- B: disk ----------------------------------------------------------------------------------------------------------------
class StallStore(pre.FakeStore):
    """No upload starts before every chunk of the body is on disk (all chunks pending at once)."""

    def upload_file(self, path, name):
        deadline = time.monotonic() + 20
        total = int(name.rsplit('-of-', 1)[1])
        while len(list(path.parent.glob('*.part-*'))) + len(self.assets) < total and time.monotonic() < deadline:
            time.sleep(0.01)
        return super().upload_file(path, name)


def test_peak_disk_with_every_upload_stalled(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, store_cls=StallStore, chunk_bytes=len(body) // 4)
    assert man['state'] == 'COMPLETE' and len(man['chunks']) >= 4
    assert man['disk']['peak_bytes'] == len(body) + symfile_bytes()        # the whole body pending at once
    assert man['disk']['peak_bytes'] <= len(body) + pre.CHUNK_BYTES       # the budget S + 1e9
    assert man['disk']['budget_peak_bytes'] == len(body) + len(body) // 4


def test_disk_prechecks_at_the_boundaries(parser, tmp_path):
    assert pre.MIN_FREE_BEFORE_SOURCE == pre.BODY_CAP + pre.CHUNK_BYTES + pre.DISK_RESERVE == 22_000_000_000
    for free, ok in ((22_000_000_000 - 1, False), (22_000_000_000, True)):
        man, store, src, counts, _ = run(parser, tmp_path / f'a{ok}', disk_free=lambda p, f=free: f,
                                         min_free=pre.MIN_FREE_BEFORE_SOURCE)
        assert (man['state'] == 'COMPLETE') is ok
        if not ok:
            assert man['failed_stage'] == 'DISK_PRECHECK_FAILED' and man['stage'] == 'ENV'
            assert counts.snapshot()['source_get'] == 0
    body = synthetic_body()
    chunk = len(body) // 3
    need = len(body) + chunk + pre.DISK_RESERVE                 # after metadata: S + CHUNK + RESERVE
    for free_after, ok in ((need - 1, False), (need, True)):
        frees = iter([22_000_000_000, free_after] + [10**12] * 50)
        man, store, src, counts, _ = run(parser, tmp_path / f'b{ok}', disk_free=lambda p: next(frees), chunk_bytes=chunk,
                                         reserve=pre.DISK_RESERVE, min_free=pre.MIN_FREE_BEFORE_SOURCE)
        if ok:
            assert man['state'] == 'COMPLETE' and man['disk']['required_after_metadata'] == need
        else:
            assert man['failed_stage'] == 'DISK_PRECHECK_FAILED' and man['stage'] == 'SOURCE_METADATA'
            assert counts.snapshot()['source_get'] == 2                     # never the body GET


def test_free_space_is_measured_on_the_chunk_filesystem(parser, tmp_path):
    seen = []
    man, store, src, counts, _ = run(parser, tmp_path, disk_free=lambda p: seen.append(Path(p)) or 10**12)
    assert man['state'] == 'COMPLETE' and set(seen) == {tmp_path / 'work' / 'chunks'}
    man, store, src, counts, _ = run(parser, tmp_path / 'x', fs_id=lambda p: 1 if Path(p).name == 'chunks' else 2)
    assert man['failed_stage'] == 'DISK_PATH_MISMATCH' and counts.snapshot()['source_get'] == 0


def test_runtime_disk_check(parser, tmp_path):
    frees = iter([10**12, 10**12] + [0] * 100)
    man, store, src, counts, _ = run(parser, tmp_path, disk_free=lambda p: next(frees))
    assert_failed_clean(man, store, tmp_path, counts, 'DISK_RUNTIME_LOW')


# ---- D: existing release, names, cleanup ------------------------------------------------------------------------------------
OTHER = {'manifest-r11a1.json': json.dumps({'state': 'FAILED'}).encode(), 'notes-from-elsewhere.txt': b'other run'}


def assert_failed_clean(man, store, tmp_path, counts, stage, existing=None):
    assert man['state'] == 'FAILED' and man['failed_stage'] == stage, man['failed_stage']
    assert local_files(tmp_path) == []
    assert names(store) == sorted([pre.manifest_name(RID)] + list(existing or {}))     # pre-existing assets untouched
    for name, data in (existing or {}).items():
        assert store.get(name) == data
    failed = json.loads(store.get(pre.manifest_name(RID)))
    assert failed['state'] == 'FAILED' and failed['failed_stage'] == stage and failed['all_partial_assets_deleted'] is True
    assert all(a['deleted'] and pre.is_ours(a['name'], RID) for a in failed['uploaded_assets'])
    assert counts.snapshot()['source_get'] <= 3 and counts.snapshot()['delete'] == len(failed['uploaded_assets'])
    return failed


@pytest.mark.parametrize('existing,code', [
    ({'manifest-r5a1.json': json.dumps({'state': 'COMPLETE'}).encode()}, 'RELEASE_HAS_COMPLETE'),
    ({'manifest.json': json.dumps({'state': 'COMPLETE'}).encode(), **OTHER}, 'RELEASE_HAS_COMPLETE'),
    ({pre.chunk_name(RID, 1, 3): b'x', **OTHER}, 'NAME_COLLISION'),
    ({pre.manifest_name(RID): json.dumps({'state': 'FAILED'}).encode()}, 'NAME_COLLISION'),
    ({'manifest-r7a2.json': b'not json'}, 'RELEASE_MANIFEST_UNREADABLE'),
])
def test_release_refusals_touch_nothing_and_spend_no_source_request(parser, tmp_path, existing, code):
    man, store, src, counts, _ = run(parser, tmp_path, existing=existing)
    assert man['failed_stage'] == code and man['stage'] == 'RELEASE_PREPARE'
    assert counts.snapshot()['source_get'] == 0 and src.events == []
    assert counts.snapshot()['upload'] == counts.snapshot()['delete'] == 0 and man['failed_manifest_uploaded'] is False
    assert {n: store.get(n) for n in names(store)} == existing


def test_earlier_failed_manifests_and_other_assets_are_left_alone(parser, tmp_path):
    man, store, *_ = run(parser, tmp_path, existing=OTHER)
    assert man['state'] == 'COMPLETE' and man['release'] == {'existing_assets': 2, 'existing_failed_manifests': 1,
                                                              'created_by_this_run': False}
    assert all(store.get(n) == d for n, d in OTHER.items())


class CorruptVerifyStore(pre.FakeStore):
    """The first chunk download (its verification) returns one flipped byte."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seen = []

    def flip(self, asset):
        return not self.seen

    def stream_asset(self, asset, sink):
        if not pre.is_ours(asset['name'], RID):
            return super().stream_asset(asset, sink)
        flip = self.flip(asset)
        self.seen.append(asset['id'])
        return super().stream_asset(asset, (lambda b: sink(bytes([b[0] ^ 1]) + b[1:])) if flip else sink)


class CorruptReassemblyStore(CorruptVerifyStore):
    """The second download of a chunk (the reassembly pass) returns one flipped byte; every verification passed."""
    def flip(self, asset):
        return asset['id'] in self.seen


class FailUploadStore(pre.FakeStore):
    def upload_file(self, path, name):
        if name.startswith(pre.chunk_prefix(RID) + '02'):
            self.counts.add('upload')
            pre._fail('ASSET_UPLOAD_FAILED', http=502)
        return super().upload_file(path, name)


class LostAnswerStore(pre.FakeStore):
    """The asset is created but the answer is lost: the cleanup finds it by this run's unique name and deletes it."""
    def upload_file(self, path, name):
        out = super().upload_file(path, name)
        if name.startswith(pre.chunk_prefix(RID) + '02'):
            pre._fail('PRIVATE_TRANSPORT_FAILED')
        return out


class CancelStore(pre.FakeStore):
    def upload_bytes(self, name, data):
        if name == pre.derived_name(RID):
            raise KeyboardInterrupt
        return super().upload_bytes(name, data)


class ManifestUploadLost(pre.FakeStore):
    """The COMPLETE manifest is stored but its answer is lost: it is deleted, then the FAILED manifest takes its name."""
    def upload_bytes(self, name, data):
        out = super().upload_bytes(name, data)
        if name == pre.manifest_name(RID) and json.loads(data)['state'] == 'COMPLETE':
            pre._fail('PRIVATE_TRANSPORT_FAILED')
        return out


class BrokenStore(pre.FakeStore):
    """An unexpected exception (with a price, a symbol, a URL and a token in its text) in the main thread's reassembly."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seen = set()

    def stream_asset(self, asset, sink):
        if asset['id'] in self.seen:
            raise ValueError('synthetic 12.34 QZPA https://example.invalid/?token=x')
        self.seen.add(asset['id'])
        return super().stream_asset(asset, sink)


@pytest.mark.parametrize('store_cls,stage', [(CorruptVerifyStore, 'CHUNK_VERIFY_FAILED'),
                                             (CorruptReassemblyStore, 'REASSEMBLY_MISMATCH'),
                                             (FailUploadStore, 'ASSET_UPLOAD_FAILED'),
                                             (LostAnswerStore, 'PRIVATE_TRANSPORT_FAILED'),
                                             (CancelStore, 'CANCELLED'),
                                             (ManifestUploadLost, 'PRIVATE_TRANSPORT_FAILED')])
def test_store_failures_delete_only_this_runs_assets(parser, tmp_path, store_cls, stage, capfd):
    man, store, src, counts, body = run(parser, tmp_path, store_cls=store_cls, existing=OTHER)
    failed = assert_failed_clean(man, store, tmp_path, counts, stage, existing=OTHER)
    assert failed['uploaded_assets'] and counts.snapshot()['source_get'] == 3
    if store_cls in (LostAnswerStore, ManifestUploadLost):
        assert any(a['known_from'] == 'LISTED_LOST_ANSWER' for a in failed['uploaded_assets'])
    if store_cls is FailUploadStore:
        assert failed['http_status'] == 502
    assert_clean_logs(''.join(capfd.readouterr()))


def test_reassembly_gzip_test(parser, tmp_path):
    """`gzip -t` of the streamed chunks is part of the reassembly verification (a stand-in that fails it)."""
    real = subprocess.Popen

    def popen(cmd, **kw):
        return real(['sh', '-c', 'cat > /dev/null; exit 1'], **kw) if cmd == ['gzip', '-t'] else real(cmd, **kw)
    man, store, src, counts, _ = run(parser, tmp_path, popen=popen)
    failed = assert_failed_clean(man, store, tmp_path, counts, 'REASSEMBLY_GZIP_TEST_FAILED')
    assert failed['exit_code'] == 1


# ---- stream failures ----------------------------------------------------------------------------------------------------------
def test_md5_mismatch(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, meta=meta_of(body, md5=hashlib.md5(b'other').digest()))
    failed = assert_failed_clean(man, store, tmp_path, counts, 'MD5_MISMATCH')
    assert len(failed['uploaded_assets']) >= 1 and counts.snapshot()['source_get'] == 3


@pytest.mark.parametrize('served', ['half', 'longer'])
def test_cut_or_longer_stream(parser, tmp_path, served):
    body = synthetic_body()
    data = body[:len(body) // 2] if served == 'half' else body + b'\0' * 10
    man, store, src, counts, _ = run(parser, tmp_path, body=body, served=data)
    assert_failed_clean(man, store, tmp_path, counts, 'SIZE_MISMATCH')


def test_gzip_faults(parser, tmp_path):
    raw = b'not a gzip stream at all ' * 40
    man, store, src, counts, _ = run(parser, tmp_path / 'a', body=raw)
    failed = assert_failed_clean(man, store, tmp_path / 'a', counts, 'GZIP_FAILED')
    assert failed['source']['metadata_size'] == len(raw)
    man, store, src, counts, _ = run(parser, tmp_path / 'b', body=synthetic_body()[:-12])
    assert man['failed_stage'] in ('GZIP_FAILED', 'PARSER_FAILED')
    assert_failed_clean(man, store, tmp_path / 'b', counts, man['failed_stage'])


def test_upload_error_stops_the_reading_loop(parser, tmp_path):
    body = synthetic_body() * 50
    path = tmp_path / 'b.gz'
    path.write_bytes(body)
    chunks = tmp_path / 'work' / 'chunks'
    chunks.mkdir(parents=True)
    symfile = tmp_path / 'work' / 's.txt'
    symfile.write_text('QZPA\n')
    disk = pre.DiskUse()
    uploader = pre.ChunkUploader(pre.FakeStore(pre.Counts(), tmp_path / 'store', {}), deadline=float('inf'), disk=disk)
    uploader.error, uploader.error_http = 'ASSET_UPLOAD_FAILED', 503
    t0, t1 = ih.session_ns(DAY)
    with pytest.raises(pre.PreserveError, match='^ASSET_UPLOAD_FAILED$') as caught:
        pre.stream_once(['cat', str(path)], size=len(body), md5=hashlib.md5(body).hexdigest(), parser=parser, symfile=symfile,
                        t0=t0, t1=t1, chunk_dir=chunks, uploader=uploader, run_id=RID, disk=disk, chunk_bytes=64,
                        max_chunks=10**6, deadline=float('inf'), disk_free=lambda p: 10**12, reserve=0)
    uploader.close()
    assert caught.value.http == 503 and list(chunks.iterdir()) == []


@pytest.mark.parametrize('over,stage,source_gets', [
    (dict(sha='0' * 64), 'PRIVATE_INPUT_MANIFEST_SHA_MISMATCH', 0),
    (dict(index={'20261030': index_for(5)['20261030']}), 'NO_FILE_FOR_EXACT_DAY', 1),
    (dict(meta={'size': '1', 'md5Hash': 'AAAA'}), 'METADATA_SIZE_MISMATCH', 2),
    (dict(run_id='r1a'), 'RUN_ID_INVALID', 0),
])
def test_early_failures_stop_before_further_source_requests(parser, tmp_path, over, stage, source_gets):
    man, store, src, counts, _ = run(parser, tmp_path, **over)
    assert man['state'] == 'FAILED' and man['failed_stage'] == stage
    assert counts.snapshot()['source_get'] == source_gets == len(src.urls)
    assert counts.snapshot()['download'] == 0 and local_files(tmp_path) == []


def test_missing_token_makes_no_request(parser, tmp_path):
    man, store, src, counts, _ = run(parser, tmp_path, token_present=False)
    assert man['failed_stage'] == 'RAW_REPO_TOKEN_MISSING' and set(counts.snapshot().values()) == {0}


# ---- E: logs ---------------------------------------------------------------------------------------------------------------
DECIMAL = re.compile(r'(?<![0-9a-f])[0-9]+\.[0-9]+')


def assert_clean_logs(text):
    assert text
    for line in text.splitlines():
        assert line.startswith('IEX_PRESERVE '), line
    for marker in FORBIDDEN_IN_LOGS:
        assert marker not in text, marker
    assert not DECIMAL.search(text), DECIMAL.search(text)


def leaky_urlopen(*a, **kw):
    raise urllib.error.HTTPError('https://example.invalid/x?token=secret', 403, 'Forbidden 12.34', {'X': 'y'},
                                 io.BytesIO(b'{"message": "token QZPA 12.34", "documentation_url": "x"}'))


def leaky_transport(method, url, **kw):
    return 403, {}, b'{"message": "Bad credentials token 12.34 QZPA", "documentation_url": "https://x"}'


def raising_transport(method, url, **kw):
    raise urllib.error.URLError('https://example.invalid/?token=abc 12.34')


INJECTIONS = {
    'ENV_DISK': dict(disk_free=lambda p: 1, min_free=pre.MIN_FREE_BEFORE_SOURCE),
    'PRIVATE_INPUT': dict(sha='1' * 64),
    'RELEASE': dict(existing={'manifest-r5a1.json': json.dumps({'state': 'COMPLETE'}).encode()}),
    'INDEX_HTTP': 'urlopen',
    'INDEX_SHAPE': dict(index={'x': 1}),
    'METADATA': dict(meta={'size': '1', 'md5Hash': 'AAAA'}),
    'STREAM_MD5': 'md5',
    'STREAM_GZIP': dict(body=b'not gzip ' * 50),
    'CHUNK_UPLOAD': dict(store_cls=FailUploadStore),
    'CHUNK_VERIFY': dict(store_cls=CorruptVerifyStore),
    'REASSEMBLY': dict(store_cls=CorruptReassemblyStore),
    'UNEXPECTED': dict(store_cls=BrokenStore),
    'OUTPUT': dict(store_cls=ManifestUploadLost),
    'CANCEL': dict(store_cls=CancelStore),
}


@pytest.mark.parametrize('name', list(INJECTIONS) + ['PRIVATE_HTTP', 'PRIVATE_TRANSPORT', 'COMPLETE'])
def test_no_price_symbol_token_or_body_in_any_log(parser, tmp_path, capfd, monkeypatch, name):
    over = INJECTIONS.get(name, {})
    if over == 'urlopen':
        monkeypatch.setattr(pre.urllib.request, 'urlopen', leaky_urlopen)
        over = dict(get=pre._urllib_get)
    elif over == 'md5':
        over = dict(meta=meta_of(synthetic_body(), md5=hashlib.md5(b'x').digest()))
    if name in ('PRIVATE_HTTP', 'PRIVATE_TRANSPORT'):
        kw, store, src, counts, _ = make(tmp_path)
        kw['store'] = pre.ReleaseStore(counts, transport=leaky_transport if name == 'PRIVATE_HTTP' else raising_transport)
        man = pre.run(parser=parser, **kw)
        assert man['failed_stage'] == ('PRIVATE_INPUT_READ_FAILED' if name == 'PRIVATE_HTTP' else 'PRIVATE_TRANSPORT_FAILED')
        assert man['http_status'] == (403 if name == 'PRIVATE_HTTP' else None)
    else:
        man, *_ = run(parser, tmp_path, **over)
        assert (man['state'] == 'COMPLETE') == (name == 'COMPLETE')
    out, err = capfd.readouterr()
    assert err == ''
    assert_clean_logs(out)
    if name == 'INDEX_HTTP':
        assert man['failed_stage'] == 'SOURCE_HTTP_STATUS' and 'http=403' in out
    if name == 'UNEXPECTED':
        assert man['failed_stage'] == 'UNEXPECTED_ERROR' and 'error_class=ValueError' in out


def test_log_redacts_anything_but_codes_counts_and_hashes(capsys):
    pre._log('X', n=3, sha='a' * 64, code='SIZE_MISMATCH', url='https://example.com/?token=abc', price='12.34',
             error_class='ValueError', other_class='a b')
    out = capsys.readouterr().out
    assert out == (f'IEX_PRESERVE X n=3 sha={"a" * 64} code=SIZE_MISMATCH url=REDACTED price=REDACTED '
                   'error_class=ValueError other_class=REDACTED\n')


# ---- the real release store against a fake transport ----------------------------------------------------------------------
class Transport:
    def __init__(self, release_status=404, assets=()):
        self.calls, self.release_status, self.blobs, self.assets = [], release_status, {}, list(assets)

    def __call__(self, method, url, *, body=None, length=None, headers=None, auth=True, sink=None, cap=None):
        sent = b''.join(body) if body is not None and not isinstance(body, bytes) else body
        self.calls.append((method, url, auth, length))
        if method == 'GET' and '/releases/tags/' in url:
            return self.release_status, {}, (json.dumps({'id': 9, 'assets': []}).encode() if self.release_status == 200 else b'')
        if method == 'GET' and '/releases/9/assets?' in url:
            return 200, {}, json.dumps(self.assets).encode()
        if method == 'POST' and url.endswith('/releases'):
            return 201, {}, json.dumps({'id': 9, 'assets': []}).encode()
        if method == 'POST' and '/releases/9/assets?name=' in url:
            name = url.rsplit('=', 1)[1]
            self.blobs[name] = sent
            return 201, {}, json.dumps({'id': 100 + len(self.blobs), 'name': name, 'size': len(sent)}).encode()
        if method == 'GET' and '/releases/assets/' in url:
            return 302, {'Location': 'https://objects.example/signed'}, b''
        if method == 'GET' and url == 'https://objects.example/signed':
            data = next(iter(self.blobs.values()))
            sink(data)
            return 200, {}, len(data)
        if method == 'GET' and '/contents/' in url:
            return 200, {}, b'{"ok": 1}'
        if method == 'DELETE':
            return 204, {}, b''
        return 500, {}, b''


def test_release_store_requests(tmp_path):
    counts, t = pre.Counts(), Transport()
    store = pre.ReleaseStore(counts, transport=t)
    assert store.read_input(f'{pre.INPUT_DIR}/connected-final.json', pre.INPUT_COMMIT) == b'{"ok": 1}'
    assert t.calls[0][1] == (f'https://api.github.com/repos/{pre.RAW_REPO}/contents/{pre.INPUT_DIR}/connected-final.json'
                             f'?ref={pre.INPUT_COMMIT}')
    assert pre.prepare_release(store, RID) == {'existing_assets': 0, 'existing_failed_manifests': 0, 'created_by_this_run': True}
    chunk = tmp_path / 'c'
    chunk.write_bytes(b'synthetic chunk bytes')
    asset, sent = store.upload_file(chunk, pre.chunk_name(RID, 1, 1))
    assert sent == hashlib.sha256(b'synthetic chunk bytes').hexdigest() and asset['size'] == 21
    upload = t.calls[-1]
    assert upload[0] == 'POST' and upload[1].startswith(f'https://uploads.github.com/repos/{pre.RAW_REPO}/releases/9/assets?name=')
    assert upload[3] == 21
    pre.verify_asset(store, asset, 21, sent)
    api, redirect = t.calls[-2], t.calls[-1]
    assert api[1].endswith(f'/releases/assets/{asset["id"]}') and api[2] is True
    assert redirect[1] == 'https://objects.example/signed' and redirect[2] is False        # the token never follows a redirect
    assert store.delete_asset(asset) is True
    assert t.calls[-1][:2] == ('DELETE', f'https://api.github.com/repos/{pre.RAW_REPO}/releases/assets/{asset["id"]}')
    assert [c for c in t.calls if c[0] == 'DELETE' and '/releases/assets/' not in c[1]] == []    # never the release itself
    assert counts.snapshot() == {'source_get': 0, 'private_read': 1, 'release_lookup': 1, 'release_create': 1, 'upload': 1,
                                 'download': 2, 'delete': 1}


def test_release_store_checks_an_existing_release():
    other = [{'id': 1, 'name': 'notes.txt', 'size': 3}]
    store = pre.ReleaseStore(pre.Counts(), transport=Transport(release_status=200, assets=other))
    assert pre.prepare_release(store, RID)['created_by_this_run'] is False
    collide = [{'id': 1, 'name': pre.chunk_name(RID, 1, 2), 'size': 3}]
    with pytest.raises(pre.PreserveError, match='^NAME_COLLISION$'):
        pre.prepare_release(pre.ReleaseStore(pre.Counts(), transport=Transport(release_status=200, assets=collide)), RID)
    with pytest.raises(pre.PreserveError, match='^RELEASE_LOOKUP_FAILED$') as caught:
        pre.ReleaseStore(pre.Counts(), transport=Transport(release_status=403)).lookup()
    assert caught.value.http == 403


# ---- CLI --------------------------------------------------------------------------------------------------------------------
def test_dry_run_subprocess_passes_the_real_route_check(parser, tmp_path):
    """A fresh interpreter whose entry script is the tool: the real require_price_source passes (ACTIONS_PRICE_ROUTES entry
    2) and the whole pipeline runs on local files."""
    body = synthetic_body()
    (tmp_path / 'body.pcap.gz').write_bytes(body)
    (tmp_path / 'index.json').write_text(json.dumps(index_for(len(body))))
    inputs, sha = private_inputs()
    (tmp_path / 'in').mkdir()
    for path, data in inputs.items():
        (tmp_path / 'in' / path.rsplit('/', 1)[1]).write_bytes(data)
    proc = subprocess.run([sys.executable, str(TOOL), '--dry-run', '--parser', parser, '--workdir', str(tmp_path / 'work'),
                           '--index', str(tmp_path / 'index.json'), '--body', str(tmp_path / 'body.pcap.gz'),
                           '--inputs-dir', str(tmp_path / 'in'), '--expected-manifest-sha', sha,
                           '--store-dir', str(tmp_path / 'store'), '--chunk-bytes', str(len(body) // 4), '--min-free-bytes', '0'],
                          cwd=REPO, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0 and proc.stderr == '', proc.stdout
    assert 'IEX_PRESERVE COMPLETE' in proc.stdout and 'source_get=3' in proc.stdout
    assert_clean_logs(proc.stdout)


def test_live_mode_refused_outside_the_one_shot_workflow(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/' + pre.RUN_BRANCH)
    assert pre.main(['--live', '--parser', 'x', '--workdir', str(tmp_path)]) == 2      # pytest is not this tool's entry point
    assert 'LIVE_ROUTE_NOT_ALLOWED' in capsys.readouterr().out
    assert pre.live_run_id({'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '2'}) == 'r123a2'
    assert pre.live_run_id({'GITHUB_RUN_ID': '12x', 'GITHUB_RUN_ATTEMPT': '1'}) is None


def test_parser_rows_strict():
    with pytest.raises(pre.PreserveError, match='^PARSER_SYMBOLS_MISMATCH$'):
        pre.parser_rows('AAA\tNO_TRADE\t0\t0\t0\t0\t-\t0\n', ['AAA', 'BBB'])
    with pytest.raises(pre.PreserveError, match='^PARSER_OUTPUT_INVALID$'):
        pre.parser_rows('AAA\tROUND\t1\t2\t3\n', ['AAA'])
    t0, t1 = ih.session_ns(DAY)
    rows = pre.parser_rows(f'AAA\tROUND\t100\t{t1}\t1\t1\tT\t1\n', ['AAA'])
    out = pre.derive_rows(['NYSE:AAA'], {'NYSE:AAA': 'AAA'}, rows, t0=t0, t1=t1, parser_sha='0' * 64)
    assert (out[0]['state'], out[0]['reason'], out[0]['price']) == ('PRICE_INVALID', 'TIMESTAMP_OUTSIDE_SESSION', None)
    out = pre.derive_rows(['NYSE:A A'], {'NYSE:A A': 'A A'}, {}, t0=t0, t1=t1, parser_sha='0' * 64)
    assert (out[0]['state'], out[0]['reason']) == ('PRICE_INVALID', 'IEX_SYMBOL_INVALID')


# ---- workflow (static) ----------------------------------------------------------------------------------------------------
WORKFLOW = REPO / '.github/workflows/iex-20261102-preserve-once.yml'


def test_workflow_is_one_shot_push_of_the_run_branch_only():
    text = WORKFLOW.read_text()
    body = '\n'.join(l for l in text.splitlines() if not l.lstrip().startswith('#'))
    head = text.split('\nname:', 1)[0]
    for phrase in ('one-shot', 'owner', '3 source GETs', '20,000,000,000', 'delete the branch'):
        assert phrase.lower() in head.lower(), phrase
    on = body.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
    assert on == "  push:\n    branches: ['run/iex-20261102-once']"
    for trigger in ('pull_request', 'schedule', 'workflow_dispatch', 'workflow_run', 'repository_dispatch', 'tags:'):
        assert trigger not in body
    assert '\npermissions:\n  contents: read\n' in body and body.count('permissions:') == 1
    assert body.count('runs-on: ubuntu-24.04') == 1 and 'timeout-minutes: 150' in body
    for forbidden in ('always()', 'actions/cache', 'git push', 'git commit', 'actions/upload', 'GITHUB_STEP_SUMMARY',
                      'continue-on-error', 'pull_request_target', 'set -x', 'curl '):
        assert forbidden not in body, forbidden
    uses = re.findall(r'uses: (\S+)', body)
    assert uses == ['actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
                    'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065']
    assert 'persist-credentials: false' in body
    steps = ('\n' + body.split('\n    steps:\n', 1)[1]).split('\n      - ')[1:]
    holders = [s for s in steps if 'RAW_REPO_TOKEN' in s]
    assert len(holders) == 1 and body.count('secrets.') == 1
    assert 'RAW_REPO_TOKEN: ${{ secrets.RAW_REPO_TOKEN }}' in holders[0]
    assert holders[0].rstrip().endswith('python implementation/tools/iex_day_preserve_once.py --live --parser "$RUNNER_TEMP/iex_last_trade" '
                                        '--workdir "$RUNNER_TEMP/iex-preserve"')
    build = next(s for s in steps if 'cc -O2' in s)
    assert 'cc -O2 -o "$RUNNER_TEMP/iex_last_trade" implementation/tools/iex_tops/iex_last_trade.c' in build
    assert steps.index(build) < steps.index(holders[0])
    assert 'dotnet' in body and 'android' in body
    assert not re.search(r'iextrading\.com|iexapis\.com|storage\.googleapis\.com|/b/iex/o/', text)
