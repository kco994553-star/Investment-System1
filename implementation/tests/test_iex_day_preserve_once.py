"""One-shot IEX 2026-11-02 preservation (tools/iex_day_preserve_once.py). SYNTHETIC data only, no network.

The real C parser is compiled (fixture from test_iex_hist) and fed a synthetic TOPS 1.6 pcap.gz built with test_iex_hist's
builders; the body "download" is `cat` of that file, the release store is a local directory (FakeStore), and the private
input (connected-final.json + its manifest) is made up here with invented tickers. Every price below is made up.
"""
import base64
import gzip
import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path

import pytest

from investment_system.providers import iex_hist as ih
from tests.test_iex_hist import frame, parser, pcap, status_msg, trade  # noqa: F401 - `parser` is a fixture

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
_SPEC = importlib.util.spec_from_file_location('iex_day_preserve_once', ROOT / 'tools' / 'iex_day_preserve_once.py')
pre = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pre)

DAY = pre.DAY
LINK = 'https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20261102%2Fsynthetic.pcap.gz?generation=1&alt=media'
CANARY_E4 = 7373_7373                       # $7373.7373: must never appear in any log line
CANARY_TEXT = pre.price_text(CANARY_E4)
# Invented codes at the 11 ROW_INDEXES positions (none is a real candidate). PSKY / WBD exercise the repository alias table.
CODES = {12: 'NYSE:QZPA', 13: 'NASDAQ:PSKY', 17: 'NYSE:QZPB', 25: 'NYSE:QZPC', 29: 'NYSE:QZPD', 30: 'NASDAQ:WBD',
         34: 'NYSE:QZPE', 38: 'NYSE:QZPF', 51: 'NYSE:QZP.G', 64: 'NYSE:QZPH', 67: 'NYSE:QZPI'}
SYMBOLS_IN_LOGS = ('QZP', 'SKYD', 'PSKY', 'WBD')


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


def private_inputs(codes=CODES):
    rows = [{'code': codes.get(i, f'NYSE:QZF{i:02d}'), 'cik': i} for i in range(68)]
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
    """Fake source functions: every URL asked is recorded; the body is `cat` of a local file."""

    def __init__(self, body_path, index, meta):
        self.body_path, self.index, self.meta, self.urls = body_path, index, meta, []

    def get(self, url, cap):
        self.urls.append(url)
        return json.dumps(self.index if url == ih.HIST_URL else self.meta).encode()

    def body_command(self, link, max_time):
        self.urls.append(link)
        assert '--retry' not in pre.curl_body_command(link) and '-C' not in pre.curl_body_command(link)
        return ['cat', str(self.body_path)]


def meta_of(body, size=None, md5=None):
    return {'size': str(len(body) if size is None else size),
            'md5Hash': base64.b64encode(md5 or hashlib.md5(body).digest()).decode()}


def make(tmp_path, *, body=None, served=None, index=None, meta=None, codes=CODES, store_cls=None, existing=(), sha=None):
    """(run kwargs, store, source, counts). `body` = the original, `served` = the bytes `cat` delivers (default: body)."""
    body = synthetic_body() if body is None else body
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / 'served.pcap.gz'
    path.write_bytes(body if served is None else served)
    inputs, manifest_sha = private_inputs(codes)
    counts = pre.Counts()
    store = (store_cls or pre.FakeStore)(counts, tmp_path / 'store', inputs, existing=existing)
    src = Source(path, index_for(len(body)) if index is None else index, meta_of(body) if meta is None else meta)
    source = pre.SourceClient(counts, get=src.get, body_command=src.body_command)
    kw = dict(store=store, source=source, counts=counts, workdir=tmp_path / 'work', chunk_bytes=max(1, len(body) // 3),
              runtime_margin=0, disk_free=lambda p: 10**12, expected_manifest_sha=sha or manifest_sha, versions={})
    return kw, store, src, counts, body


def run(parser, tmp_path, **over):
    run_kw = {k: over.pop(k) for k in ('chunk_bytes', 'max_chunks', 'disk_free', 'min_free', 'token_present') if k in over}
    kw, store, src, counts, body = make(tmp_path, **over)
    kw.update(run_kw)
    return pre.run(parser=parser, **kw), store, src, counts, body


def local_files(tmp_path):
    work = tmp_path / 'work'
    return sorted(p.name for p in work.iterdir()) if work.exists() else []


# ---- exact date, caps, budget ---------------------------------------------------------------------------------------------
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


def test_caps_on_index_and_metadata_bodies():
    assert (pre.INDEX_CAP, pre.METADATA_CAP, pre.BODY_CAP) == (8 * 1024 * 1024, 1024 * 1024, 20_000_000_000)
    seen = []

    def get(url, cap):
        seen.append(cap)
        return b' ' * (cap + 1)
    for call, code in ((lambda s: s.index(), 'INDEX_TOO_LARGE'), (lambda s: s.metadata(LINK), 'METADATA_TOO_LARGE')):
        with pytest.raises(pre.PreserveError, match=f'^{code}$'):
            call(pre.SourceClient(pre.Counts(), get=get))
    assert seen == [pre.INDEX_CAP, pre.METADATA_CAP]


def test_metadata_size_must_equal_index_and_stay_under_the_cap():
    entry = pre.select_exact_day(index_for(100))
    src = pre.SourceClient(pre.Counts(), get=lambda url, cap: json.dumps(meta_of(b'x', size=100)).encode())
    assert pre.object_checks(entry, src) == (100, hashlib.md5(b'x').hexdigest())
    src = pre.SourceClient(pre.Counts(), get=lambda url, cap: json.dumps(meta_of(b'x', size=101)).encode())
    with pytest.raises(pre.PreserveError, match='^METADATA_SIZE_MISMATCH$'):
        pre.object_checks(entry, src)
    src = pre.SourceClient(pre.Counts(), get=lambda url, cap: b'{"size": "100"}')
    with pytest.raises(pre.PreserveError, match='^METADATA_INVALID$'):
        pre.object_checks(entry, src)
    big = dict(entry, size=pre.BODY_CAP + 1)
    src = pre.SourceClient(pre.Counts(), get=lambda url, cap: json.dumps(meta_of(b'x', size=pre.BODY_CAP + 1)).encode())
    with pytest.raises(pre.PreserveError, match='^BODY_CAP_EXCEEDED$'):
        pre.object_checks(big, src)


def test_source_budget_three_gets_each_kind_once_exact_urls():
    counts = pre.Counts()
    asked = []
    src = pre.SourceClient(counts, get=lambda url, cap: asked.append(url) or b'{}', body_command=lambda link, t: ['true'])
    with pytest.raises(pre.PreserveError, match='^SOURCE_URL_INVALID$'):
        src.body_command('https://example.com/x', 1)
    assert counts.snapshot()['source_get'] == 0 and asked == []
    src.index()
    with pytest.raises(pre.PreserveError, match='^SOURCE_REQUEST_REPEATED$'):
        src.index()
    src.metadata(LINK)
    cmd = src.body_command(LINK, 5)
    assert counts.snapshot()['source_get'] == 3 and src.used == ['INDEX', 'METADATA', 'BODY']
    small = pre.SourceClient(pre.Counts(), get=lambda url, cap: b'{}', budget=1)
    small.index()
    with pytest.raises(pre.PreserveError, match='^SOURCE_BUDGET_EXCEEDED$'):
        small.metadata(LINK)
    assert asked[0] == ih.HIST_URL and '/storage/v1/b/iex/o/' in asked[1] and '/download/' not in asked[1]
    curl = pre.curl_body_command(LINK, 99)
    assert curl[-1] == LINK and '--max-time' in curl and '--fail' in curl
    assert not {'--retry', '-C', '--continue-at', '-r', '--range', '-L', '--location'} & set(curl)
    assert cmd == ['true']


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
def test_complete_run_chunks_reassembly_manifest_and_derived_rows(parser, tmp_path, capsys):
    man, store, src, counts, body = run(parser, tmp_path)
    assert man['state'] == 'COMPLETE', man.get('failed_stage')
    stored = json.loads(store.get('manifest.json'))
    assert stored['state'] == 'COMPLETE' and stored['received']['sha256'] == hashlib.sha256(body).hexdigest()
    assert stored['received']['md5'] == hashlib.md5(body).hexdigest() and stored['received']['bytes'] == len(body)
    assert stored['source']['index_size'] == stored['source']['metadata_size'] == len(body)
    assert stored['parser']['source_sha256'] == hashlib.sha256((ROOT / 'tools/iex_tops/iex_last_trade.c').read_bytes()).hexdigest()
    assert stored['session_window_ns'] == list(ih.session_ns(DAY)) and stored['parser_stats']['packets'] == 12 * 20
    assert all(stored['completeness'][k] is True for k in ('size_match', 'md5_match', 'gzip_exit_0', 'parser_exit_0',
                                                           'all_chunks_verified', 'reassembly_match'))
    chunks = stored['chunks']
    assert b''.join(store.get(c['name']) for c in chunks) == body                              # lossless
    assert [c['name'] for c in chunks] == [f'{pre.CHUNK_PREFIX}{i:03d}' for i in range(1, len(chunks) + 1)]
    assert all(c['sha256'] == hashlib.sha256(store.get(c['name'])).hexdigest() for c in chunks)
    assert local_files(tmp_path) == []                                                         # every local copy deleted
    assert sorted(a['name'] for a in store.assets.values()) == sorted([c['name'] for c in chunks] + [pre.DERIVED_NAME, 'manifest.json'])
    derived = json.loads(store.get(pre.DERIVED_NAME))
    assert stored['derived']['sha256'] == hashlib.sha256(store.get(pre.DERIVED_NAME)).hexdigest()
    rows = {r['code']: r for r in derived['rows']}
    t0, t1 = ih.session_ns(DAY)
    expect = {'NYSE:QZPA': ('PRICE', None, CANARY_TEXT), 'NASDAQ:PSKY': ('PRICE', None, '12.3400'),
              'NYSE:QZPB': ('NO_TRADE', 'ODD_LOT_ONLY', None),
              'NYSE:QZPC': ('NO_TRADE', 'NO_REGULAR_SESSION_ROUND_LOT_TRADE', None),
              'NYSE:QZPD': ('NOT_IN_FILE', 'SYMBOL_NOT_IN_FILE', None),
              'NASDAQ:WBD': ('NOT_IN_FILE', 'IEX_SYMBOL_NONE_FROM_ALIAS_DATE', None),
              'NYSE:QZPE': ('NO_TRADE', 'NO_REGULAR_SESSION_ROUND_LOT_TRADE', None),
              'NYSE:QZPF': ('PRICE_INVALID', 'PRICE_OUT_OF_RANGE', None), 'NYSE:QZP.G': ('PRICE', None, '0.4200'),
              'NYSE:QZPH': ('PRICE_INVALID', 'PRICE_OUT_OF_RANGE', None), 'NYSE:QZPI': ('PRICE', None, '0.0101')}
    assert {c: (r['state'], r['reason'], r['price']) for c, r in rows.items()} == expect
    assert [r['row_index'] for r in derived['rows']] == list(pre.ROW_INDEXES)
    assert rows['NASDAQ:PSKY']['iex_symbol'] == 'SKYD' and rows['NASDAQ:WBD']['iex_symbol'] is None
    assert rows['NYSE:QZPA']['last_trade_ns'] == t0 + 120 * 10**9 and rows['NYSE:QZP.G']['last_trade_ns'] == t1 - 1
    assert rows['NYSE:QZPA']['last_trade_utc'] == '2026-11-02T14:32:00.000000000Z'
    assert all(r['basis_date'] == '2026-11-02' and r['source'] == pre.SOURCE_LABEL and r['parser_source_sha256'] ==
               stored['parser']['source_sha256'] for r in derived['rows'])
    assert all(r['price'] is None and r['last_trade_ns'] is None for r in derived['rows'] if r['state'] != 'PRICE')
    text = json.dumps(derived).lower()
    assert 'close' not in text and 'ohlcv' not in text
    assert stored['derived']['states'] == {'PRICE': 4, 'NO_TRADE': 3, 'NOT_IN_FILE': 2, 'PRICE_INVALID': 2}
    # request budget: 3 source GETs; private requests counted apart
    n = len(chunks)
    assert counts.snapshot() == {'source_get': 3, 'private_read': 2, 'release_lookup': 1, 'release_create': 1,
                                 'upload': n + 2, 'download': 4 * n, 'delete': 0}
    assert stored['requests'] == counts.snapshot()
    assert src.urls == [ih.HIST_URL, ih.gcs_metadata_url(LINK), LINK]
    # logs: fixed codes, counts, sizes, hashes only
    out = capsys.readouterr().out
    assert out and all(line.startswith('IEX_PRESERVE ') for line in out.splitlines())
    for secret in SYMBOLS_IN_LOGS + (CANARY_TEXT, str(CANARY_E4), '12.34', 'http', 'googleapis', 'REDACTED'):
        assert secret not in out, secret


@pytest.mark.parametrize('div,extra', [(3, 0), (3, 1), (1, 0), (7, 5)])
def test_chunk_boundaries(parser, tmp_path, div, extra):
    body = synthetic_body()
    size = len(body) // div + extra if div > 1 else len(body)
    man, store, *_ = run(parser, tmp_path, chunk_bytes=size)
    assert man['state'] == 'COMPLETE'
    sizes = [c['size'] for c in man['chunks']]
    assert len(sizes) == -(-len(body) // size) == man['source']['expected_chunks']
    assert all(s == size for s in sizes[:-1]) and 0 < sizes[-1] <= size and sum(sizes) == len(body)


def test_exact_multiple_has_no_empty_last_chunk(parser, tmp_path):
    body = synthetic_body()
    k = next(k for k in range(2, len(body) + 1) if len(body) % k == 0)
    man, *_ = run(parser, tmp_path, chunk_bytes=len(body) // k, max_chunks=len(body))
    assert man['state'] == 'COMPLETE' and [c['size'] for c in man['chunks']] == [len(body) // k] * k
    man2, *_ = run(parser, tmp_path / 'b', chunk_bytes=len(body))
    assert [c['size'] for c in man2['chunks']] == [len(body)]


def test_chunk_limit(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, chunk_bytes=len(body) // 5, max_chunks=3)
    assert man['state'] == 'FAILED' and man['failed_stage'] == 'CHUNK_LIMIT_EXCEEDED'
    assert counts.snapshot()['source_get'] == 2          # refused from the metadata size, before the body GET


# ---- failures -------------------------------------------------------------------------------------------------------------
def _assert_failed_clean(man, store, tmp_path, counts, stage):
    assert man['state'] == 'FAILED' and man['failed_stage'] == stage, man['failed_stage']
    assert local_files(tmp_path) == []
    names = [a['name'] for a in store.assets.values()]
    assert len(names) == 1 and names[0].startswith(pre.FAILED_PREFIX)        # only the small FAILED manifest is left
    failed = json.loads(store.get(names[0]))
    assert failed['state'] == 'FAILED' and failed['failed_stage'] == stage and failed['all_partial_assets_deleted'] is True
    assert all(a['deleted'] for a in failed['uploaded_assets'])
    assert counts.snapshot()['source_get'] <= 3
    assert counts.snapshot()['delete'] == len(failed['uploaded_assets'])
    return failed


def test_md5_mismatch(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, meta=meta_of(body, md5=hashlib.md5(b'other').digest()))
    failed = _assert_failed_clean(man, store, tmp_path, counts, 'MD5_MISMATCH')
    assert len(failed['uploaded_assets']) >= 1 and counts.snapshot()['source_get'] == 3


def test_truncated_stream_is_a_size_mismatch(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, body=body, served=body[:len(body) // 2])
    _assert_failed_clean(man, store, tmp_path, counts, 'SIZE_MISMATCH')


def test_longer_stream_than_metadata_is_refused(parser, tmp_path):
    body = synthetic_body()
    man, store, src, counts, _ = run(parser, tmp_path, body=body, served=body + b'\0' * 10)
    _assert_failed_clean(man, store, tmp_path, counts, 'SIZE_MISMATCH')


def test_gzip_fault(parser, tmp_path):
    raw = b'not a gzip stream at all ' * 40
    man, store, src, counts, _ = run(parser, tmp_path, body=raw)
    failed = _assert_failed_clean(man, store, tmp_path, counts, 'GZIP_FAILED')
    assert failed['source']['metadata_size'] == len(raw)


def test_truncated_gzip_with_matching_metadata(parser, tmp_path):
    body = synthetic_body()[:-12]
    man, store, src, counts, _ = run(parser, tmp_path, body=body)
    assert man['failed_stage'] in ('GZIP_FAILED', 'PARSER_FAILED')
    _assert_failed_clean(man, store, tmp_path, counts, man['failed_stage'])


class CorruptVerifyStore(pre.FakeStore):
    """The first download of chunk 1 (its verification) returns one flipped byte."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seen = []

    def flip(self, asset):
        return not self.seen

    def stream_asset(self, asset, sink):
        flip = self.flip(asset)
        self.seen.append(asset['id'])
        return super().stream_asset(asset, (lambda b: sink(bytes([b[0] ^ 1]) + b[1:])) if flip else sink)


class CorruptReassemblyStore(CorruptVerifyStore):
    """The second download of a chunk (the reassembly pass) returns one flipped byte; every verification passed."""
    def flip(self, asset):
        return asset['id'] in self.seen


class FailUploadStore(pre.FakeStore):
    def upload_file(self, path, name):
        if name.endswith('002'):
            self.counts.add('upload')
            pre._fail('ASSET_UPLOAD_FAILED')
        return super().upload_file(path, name)


class LostAnswerStore(pre.FakeStore):
    """The asset is created but the answer is lost: the cleanup must still find and delete it."""
    def upload_file(self, path, name):
        super().upload_file(path, name)
        if name.endswith('002'):
            pre._fail('ASSET_UPLOAD_FAILED')
        return list(self.assets.values())[-1], hashlib.sha256(path.read_bytes()).hexdigest()


class CancelStore(pre.FakeStore):
    def upload_bytes(self, name, data):
        if name == pre.DERIVED_NAME:
            raise KeyboardInterrupt
        return super().upload_bytes(name, data)


class ManifestUploadFails(pre.FakeStore):
    def upload_bytes(self, name, data):
        if name == 'manifest.json':
            self.counts.add('upload')
            pre._fail('ASSET_UPLOAD_FAILED')
        return super().upload_bytes(name, data)


@pytest.mark.parametrize('store_cls,stage', [(CorruptVerifyStore, 'CHUNK_VERIFY_FAILED'),
                                             (CorruptReassemblyStore, 'REASSEMBLY_MISMATCH'),
                                             (FailUploadStore, 'ASSET_UPLOAD_FAILED'),
                                             (LostAnswerStore, 'ASSET_UPLOAD_FAILED'),
                                             (CancelStore, 'CANCELLED'),
                                             (ManifestUploadFails, 'ASSET_UPLOAD_FAILED')])
def test_store_failures_delete_every_partial_asset(parser, tmp_path, store_cls, stage, capsys):
    man, store, src, counts, body = run(parser, tmp_path, store_cls=store_cls)
    failed = _assert_failed_clean(man, store, tmp_path, counts, stage)
    assert failed['uploaded_assets'] and counts.snapshot()['source_get'] == 3
    out = capsys.readouterr().out
    assert 'IEX_PRESERVE FAILED' in out and all(s not in out for s in SYMBOLS_IN_LOGS + (CANARY_TEXT,))


def test_upload_error_stops_the_reading_loop(parser, tmp_path):
    """The reading loop checks the uploader before every block: an upload error kills the body download at once and
    removes the open chunk file."""
    body = synthetic_body() * 50
    path = tmp_path / 'b.gz'
    path.write_bytes(body)
    work = tmp_path / 'work'
    work.mkdir()
    symfile = work / 's.txt'
    symfile.write_text('QZPA\n')
    uploader = pre.ChunkUploader(pre.FakeStore(pre.Counts(), tmp_path / 'store', {}), deadline=float('inf'))
    uploader.error = 'ASSET_UPLOAD_FAILED'
    t0, t1 = ih.session_ns(DAY)
    with pytest.raises(pre.PreserveError, match='^ASSET_UPLOAD_FAILED$'):
        pre.stream_once(['cat', str(path)], size=len(body), md5=hashlib.md5(body).hexdigest(), parser=parser, symfile=symfile,
                        t0=t0, t1=t1, workdir=work, uploader=uploader, chunk_bytes=64, max_chunks=10**6,
                        deadline=float('inf'), disk_free=lambda p: 10**12, runtime_margin=0)
    uploader.close()
    assert sorted(p.name for p in work.iterdir()) == ['s.txt']


def test_many_chunks_upload_in_the_background(parser, tmp_path):
    man, store, src, counts, body = run(parser, tmp_path, chunk_bytes=64, max_chunks=10**6)
    n = -(-len(body) // 64)
    assert man['state'] == 'COMPLETE' and len(man['chunks']) == n and counts.snapshot()['download'] == 4 * n
    assert local_files(tmp_path) == []


@pytest.mark.parametrize('over,stage,source_gets', [
    (dict(disk_free=lambda p: pre.MIN_FREE_BYTES - 1, min_free=pre.MIN_FREE_BYTES), 'DISK_PRECHECK_FAILED', 0),
    (dict(sha='0' * 64), 'PRIVATE_INPUT_MANIFEST_SHA_MISMATCH', 0),
    (dict(index={'20261030': index_for(5)['20261030']}), 'NO_FILE_FOR_EXACT_DAY', 1),
    (dict(meta={'size': '1', 'md5Hash': 'AAAA'}), 'METADATA_SIZE_MISMATCH', 2),
    (dict(existing=['manifest.json']), 'RELEASE_NOT_EMPTY', 0),
])
def test_early_failures_stop_before_further_source_requests(parser, tmp_path, over, stage, source_gets):
    man, store, src, counts, _ = run(parser, tmp_path, **over)
    assert man['state'] == 'FAILED' and man['failed_stage'] == stage
    assert counts.snapshot()['source_get'] == source_gets == len(src.urls)
    assert counts.snapshot()['upload'] <= 1 and counts.snapshot()['download'] == 0 and local_files(tmp_path) == []
    if stage == 'RELEASE_NOT_EMPTY':
        assert [a['name'] for a in store.assets.values()] == ['manifest.json']     # someone else's asset: never touched
        assert counts.snapshot()['delete'] == 0 and man['failed_manifest_uploaded'] is False
    else:
        assert man['failed_manifest_uploaded'] is True


def test_runtime_disk_check(parser, tmp_path):
    free = iter([10**12] + [0] * 100)
    man, store, src, counts, _ = run(parser, tmp_path, disk_free=lambda p: next(free))
    _assert_failed_clean(man, store, tmp_path, counts, 'DISK_RUNTIME_LOW')


def test_missing_token_makes_no_request(parser, tmp_path):
    man, store, src, counts, _ = run(parser, tmp_path, token_present=False)
    assert man['failed_stage'] == 'RAW_REPO_TOKEN_MISSING' and set(counts.snapshot().values()) == {0}


def test_earlier_failed_manifest_allows_a_rerun(parser, tmp_path):
    man, store, *_ = run(parser, tmp_path, existing=[pre.FAILED_PREFIX + '20261106T000000Z.json'])
    assert man['state'] == 'COMPLETE' and man['earlier_failed_manifests'] == 1


def test_parser_rows_and_price_text():
    assert pre.price_text(1000000) == '100.0000' and pre.price_text(101) == '0.0101' and pre.price_text(12345678) == '1234.5678'
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


def test_log_redacts_anything_but_codes_counts_and_hashes(capsys):
    pre._log('X', n=3, sha='a' * 64, code='SIZE_MISMATCH', url='https://example.com/?token=abc', price='12.34')
    out = capsys.readouterr().out
    assert out == f'IEX_PRESERVE X n=3 sha={"a" * 64} code=SIZE_MISMATCH url=REDACTED price=REDACTED\n'


# ---- the real release store against a fake transport ----------------------------------------------------------------------
class Transport:
    def __init__(self, release_status=404):
        self.calls, self.release_status, self.blobs = [], release_status, {}

    def __call__(self, method, url, *, body=None, length=None, headers=None, auth=True, sink=None, cap=None):
        sent = b''.join(body) if body is not None and not isinstance(body, bytes) else body
        self.calls.append((method, url, auth, length))
        if method == 'GET' and '/releases/tags/' in url:
            return self.release_status, {}, (json.dumps({'id': 9, 'assets': []}).encode() if self.release_status == 200 else b'')
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
    assert store.prepare() == [] and store.release_id == 9
    chunk = tmp_path / 'c'
    chunk.write_bytes(b'synthetic chunk bytes')
    asset, sent = store.upload_file(chunk, pre.CHUNK_PREFIX + '001')
    assert sent == hashlib.sha256(b'synthetic chunk bytes').hexdigest() and asset['size'] == 21
    upload = t.calls[-1]
    assert upload[0] == 'POST' and upload[1].startswith(f'https://uploads.github.com/repos/{pre.RAW_REPO}/releases/9/assets?name=')
    assert upload[3] == 21
    pre.verify_asset(store, asset, 21, sent)
    api, redirect = t.calls[-2], t.calls[-1]
    assert api[1].endswith(f'/releases/assets/{asset["id"]}') and api[2] is True
    assert redirect[1] == 'https://objects.example/signed' and redirect[2] is False        # the token never follows a redirect
    assert store.delete_asset(asset) is True and t.calls[-1][:2] == ('DELETE', f'https://api.github.com/repos/{pre.RAW_REPO}/releases/assets/{asset["id"]}')
    assert counts.snapshot() == {'source_get': 0, 'private_read': 1, 'release_lookup': 1, 'release_create': 1, 'upload': 1,
                                 'download': 2, 'delete': 1}


def test_release_store_refuses_a_non_empty_release():
    class Full(Transport):
        def __call__(self, method, url, **kw):
            if '/releases/tags/' in url:
                return 200, {}, json.dumps({'id': 9, 'assets': [{'id': 1, 'name': pre.CHUNK_PREFIX + '001'}]}).encode()
            return super().__call__(method, url, **kw)
    with pytest.raises(pre.PreserveError, match='^RELEASE_NOT_EMPTY$'):
        pre.ReleaseStore(pre.Counts(), transport=Full()).prepare()
    with pytest.raises(pre.PreserveError, match='^RELEASE_LOOKUP_FAILED$'):
        pre.ReleaseStore(pre.Counts(), transport=Transport(release_status=403)).prepare()


# ---- CLI ------------------------------------------------------------------------------------------------------------------
def test_dry_run_end_to_end(parser, tmp_path, capsys):
    body = synthetic_body()
    (tmp_path / 'body.pcap.gz').write_bytes(body)
    (tmp_path / 'index.json').write_text(json.dumps(index_for(len(body))))
    inputs, sha = private_inputs()
    (tmp_path / 'in').mkdir()
    for path, data in inputs.items():
        (tmp_path / 'in' / path.rsplit('/', 1)[1]).write_bytes(data)
    rc = pre.main(['--dry-run', '--parser', parser, '--workdir', str(tmp_path / 'work'), '--index', str(tmp_path / 'index.json'),
                   '--body', str(tmp_path / 'body.pcap.gz'), '--inputs-dir', str(tmp_path / 'in'), '--expected-manifest-sha', sha,
                   '--store-dir', str(tmp_path / 'store'), '--chunk-bytes', str(len(body) // 4), '--min-free-bytes', '0'])
    out = capsys.readouterr().out
    assert rc == 0 and 'IEX_PRESERVE COMPLETE' in out and 'source_get=3' in out
    assert all(s not in out for s in SYMBOLS_IN_LOGS + (CANARY_TEXT,))


def test_live_mode_refused_outside_the_one_shot_workflow(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/' + pre.RUN_BRANCH)
    assert pre.main(['--live', '--parser', 'x', '--workdir', str(tmp_path)]) == 2      # pytest is not this tool's entry point
    assert 'LIVE_ROUTE_NOT_ALLOWED' in capsys.readouterr().out and not (tmp_path / 'x').exists()


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
                      'continue-on-error', 'pull_request_target', 'set -x'):
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
    assert 'dotnet' in body and 'android' in body                       # disk freed before the tool's own 25 GB check
    assert not re.search(r'iextrading\.com|iexapis\.com|storage\.googleapis\.com|/b/iex/o/', text)
