#!/usr/bin/env python3
"""One-shot preservation of the IEX HIST TOPS 1.6 original of exactly 2026-11-02 (owner directive 2026-11-05, plan "안 A").

Run ONLY by .github/workflows/iex-20261102-preserve-once.yml (a push of the branch run/iex-20261102-once after the owner's
approval). Design and request budget: docs/expanded_universe/IEX_20261102_PRESERVE_ONCE_20261105.md.

What one live run does, and nothing more:
  0. ENV         free disk on the work dir >= 25 GB (DISK_PRECHECK_FAILED), parser binary present, python / cc versions,
                 RAW_REPO_TOKEN present (never printed).
  1. PRIVATE     read the private handoff `connected-final.json` at a pinned commit of the private raw repository and its
                 directory manifest (manifest SHA-256 pinned below; file SHA-256 and size from that manifest); take the rows
                 at ROW_INDEXES and map each `code` to its IEX symbol with providers.iex_hist.iex_symbol(code, '2026-11-02').
                 The 11 codes are never written into this public repository.
  2. RELEASE     the private release RELEASE_TAG must be new or hold only earlier FAILED manifests.
  3. SOURCE      at most THREE source GETs, free, no retry, no Range / resume, no other date:
                   (a) the hist index (providers.iex_hist.HIST_URL), body capped at 8 MiB; its TOPS 1.6 entry must be dated
                       exactly 20261102 (no fallback day);
                   (b) the object metadata of that link (size, md5), body capped at 1 MiB; size = index size <= 20e9 bytes;
                   (c) the body, streamed ONCE by curl (no --retry, no -C / -r, no -L).
  4. STREAM      one pass over the body: whole-file SHA-256 + MD5 + byte count; lossless chunks of exactly CHUNK_BYTES
                 (last one smaller, at most MAX_CHUNKS); the same bytes go to `gzip -dc | iex_last_trade <symbols-file>
                 <start_ns> <end_ns>` (the existing symbols-file mode of tools/iex_tops/iex_last_trade.c).
                 Every closed chunk is handed to a background uploader thread (upload -> download back -> SHA-256 check ->
                 delete the local copy). The reading loop never waits for an upload: the disk precheck (>= 25 GB for a body
                 of <= 20 GB) holds every chunk on disk even if no upload finished, so curl's low-speed limit (1 MiB/s over
                 60 s) can only trip on a real source stall, never on our own upload.
  5. CHECKS      size = metadata size, md5 = metadata md5, curl / gzip / parser exit 0 (stage named by
                 providers.iex_hist.failed_stage), every chunk uploaded and verified.
  6. REASSEMBLY  download every chunk back in order into one SHA-256 + byte count; must equal the whole-file values.
  7. OUTPUT      upload the derived file (11 rows, private only) and then manifest.json (state COMPLETE) last.
Any failure: stop at once (no further source request), kill the pipeline, delete local partial files, DELETE every asset
this run uploaded (chunks, derived), and upload a small `manifest-FAILED-<utc>.json` (state FAILED, failed_stage, the chunk
assets uploaded and whether each was deleted), so no partial original remains looking complete.

Logs: fixed codes, counts, sizes and hashes only. Never a price, a symbol, a code, a URL or a token.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(TOOLS))

from investment_system import public_price_boundary as boundary  # noqa: E402
from investment_system.providers import iex_hist as ih  # noqa: E402
import raw_store_release as rsr  # noqa: E402

# ---- the one run --------------------------------------------------------------------------------------------------------
DAY = '20261102'
BASIS_DATE = '2026-11-02'
RUN_BRANCH = 'run/iex-20261102-once'
RAW_REPO = 'kco994553-star/investment-system1-raw'
RELEASE_TAG = 'current-iex-20261102'
INPUT_COMMIT = 'fc88bf410b7896dbfe7898a58fd4cf07ca18d451'
INPUT_DIR = 'handoffs/financial-v-connection-20261105'
INPUT_FILE = 'connected-final.json'
INPUT_MANIFEST = 'manifest.json'
INPUT_MANIFEST_SHA256 = 'd7b5c0715496857644f1971b236141b296caf80207f56fce40d0c204a22fbb2a'
ROW_INDEXES = (12, 13, 17, 25, 29, 30, 34, 38, 51, 64, 67)

# ---- caps and sizes -----------------------------------------------------------------------------------------------------
SOURCE_GET_BUDGET = 3
INDEX_CAP = 8 * 1024 * 1024
METADATA_CAP = 1024 * 1024
BODY_CAP = 20_000_000_000
CHUNK_BYTES = 1_000_000_000            # < 2 GiB, GitHub's per-asset limit
MAX_CHUNKS = 20
MIN_FREE_BYTES = 25_000_000_000
RUNTIME_MARGIN = 1_000_000_000         # free disk left over when a new chunk file is opened
PRIVATE_INPUT_CAP = 8 * 1024 * 1024
READ_BLOCK = 1 << 22                   # 4 MiB: the only body buffer held by the reading loop
NET_BLOCK = 1 << 20
PARSER_OUT_CAP = 1 << 20
DEADLINE_S = 7500                      # the tool's own limit (workflow step 140 min, job 150 min): cleanup still runs
CURL_MAX_TIME_S = 3600
SOURCE_TIMEOUT_S = 120
HTTP_TIMEOUT_S = 600

SCHEMA = 'iex-day-preserve-once/1'
DERIVED_SCHEMA = 'iex-day-financial11-last-trade/1'
SOURCE_LABEL = 'IEX_HIST TOPS 1.6 last regular-session trade'
CHUNK_PREFIX = f'iex-tops16-{DAY}.pcap.gz.part-'
DERIVED_NAME = f'iex-{DAY}-financial11-last-trade.json'
MANIFEST_NAME = 'manifest.json'
FAILED_PREFIX = 'manifest-FAILED-'
STATES = ('PRICE', 'NO_TRADE', 'NOT_IN_FILE', 'PRICE_INVALID')
_HEX = re.compile(r'[0-9a-f]+')
_CODE = re.compile(r'[A-Z][A-Z0-9]*:[A-Z0-9][A-Z0-9.\-]{0,9}')


_LIVE = False                          # set by main() in live mode only (signal handling)


class PreserveError(RuntimeError):
    """Fixed code only (the failed stage). Never a URL, a token, a symbol, a price or a response body."""


def _fail(code: str):
    raise PreserveError(code) from None


def _log(event: str, **fields) -> None:
    """One log line: a fixed event code and int / bool / hex / fixed-code values only."""
    parts = [f'IEX_PRESERVE {event}']
    for key, value in fields.items():
        if isinstance(value, bool) or isinstance(value, int) or value is None:
            parts.append(f'{key}={value}')
        elif isinstance(value, str) and (re.fullmatch(r'[0-9a-f]{32,64}', value) or re.fullmatch(r'[A-Z][A-Z0-9_]*', value)):
            parts.append(f'{key}={value}')
        else:
            parts.append(f'{key}=REDACTED')
    print(' '.join(parts), flush=True)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def _ns_utc(ns: int) -> str:
    secs, frac = divmod(ns, 10**9)
    return dt.datetime.fromtimestamp(secs, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + f'.{frac:09d}Z'


def price_text(price_e4: int) -> str:
    """TOPS price (int, 1e-4 USD) as an exact decimal string, USD per share."""
    return f'{price_e4 // 10000}.{price_e4 % 10000:04d}'


class Counts:
    """Request counter, thread safe (the uploader thread counts too). Source GETs are counted apart from private requests."""
    KEYS = ('source_get', 'private_read', 'release_lookup', 'release_create', 'upload', 'download', 'delete')

    def __init__(self):
        self._lock = threading.Lock()
        self.n = dict.fromkeys(self.KEYS, 0)

    def add(self, key: str, k: int = 1) -> None:
        with self._lock:
            self.n[key] += k

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.n)


# ---- 1. private input ---------------------------------------------------------------------------------------------------
def select_codes(manifest_bytes: bytes, file_bytes: bytes, *, expected_manifest_sha: str = INPUT_MANIFEST_SHA256,
                 indexes=ROW_INDEXES, file_name: str = INPUT_FILE) -> tuple[list, dict]:
    """([code, ...] in ROW_INDEXES order, receipt). The directory manifest must hash to the pinned SHA-256; the input file must
    match its manifest entry (SHA-256 and size); every selected row's `code` must be 'EXCH:TICKER' and the codes distinct."""
    if _sha256(manifest_bytes) != expected_manifest_sha:
        _fail('PRIVATE_INPUT_MANIFEST_SHA_MISMATCH')
    try:
        manifest = json.loads(manifest_bytes)
        entries = [f for f in manifest['files'] if isinstance(f, dict) and f.get('path') == file_name]
        sha, size = entries[0]['sha256'], entries[0]['bytes']
    except Exception:  # noqa: BLE001
        _fail('PRIVATE_INPUT_MANIFEST_INVALID')
    if len(entries) != 1 or not (isinstance(sha, str) and re.fullmatch(r'[0-9a-f]{64}', sha)) or type(size) is not int:
        _fail('PRIVATE_INPUT_MANIFEST_INVALID')
    if len(file_bytes) != size or _sha256(file_bytes) != sha:
        _fail('PRIVATE_INPUT_SHA_MISMATCH')
    try:
        rows = json.loads(file_bytes)['rows']
        codes = [rows[i]['code'] for i in indexes]
    except Exception:  # noqa: BLE001
        _fail('PRIVATE_INPUT_INVALID')
    if not all(isinstance(c, str) and _CODE.fullmatch(c) for c in codes) or len(set(codes)) != len(codes):
        _fail('PRIVATE_INPUT_INVALID')
    blob = hashlib.sha1(b'blob %d\0' % len(file_bytes) + file_bytes).hexdigest()
    receipt = {'repository': 'PRIVATE_RAW', 'commit': INPUT_COMMIT, 'path': f'{INPUT_DIR}/{file_name}',
               'manifest_sha256': _sha256(manifest_bytes), 'file_sha256': sha, 'file_bytes': size, 'git_blob_sha1': blob,
               'row_indexes': list(indexes)}
    return codes, receipt


def map_symbols(codes, day: str = BASIS_DATE) -> dict:
    """{code: IEX symbol or None} with providers.iex_hist.iex_symbol (the one dated alias table)."""
    return {code: ih.iex_symbol(code, day) for code in codes}


def symbols_file_bytes(symbol_of: dict) -> bytes:
    wanted = sorted({s for s in symbol_of.values() if ih.valid_symbol(s)})
    return ('\n'.join(wanted) + '\n').encode('ascii') if wanted else b''


# ---- 3. source requests ---------------------------------------------------------------------------------------------------
def _urllib_get(url: str, cap: int) -> bytes:
    """One GET, no retry, no Range; at most cap + 1 bytes are read. Any non-200 or transport error -> fixed code."""
    req = urllib.request.Request(url, method='GET', headers={'Accept': 'application/json', 'Accept-Encoding': 'identity'})
    try:
        with urllib.request.urlopen(req, timeout=SOURCE_TIMEOUT_S) as r:
            if r.status != 200:
                _fail('SOURCE_HTTP_STATUS')
            return r.read(cap + 1)
    except PreserveError:
        raise
    except urllib.error.HTTPError:
        _fail('SOURCE_HTTP_STATUS')
    except Exception:  # noqa: BLE001 - the message may carry a URL
        _fail('SOURCE_UNAVAILABLE')


def curl_body_command(link: str, max_time: int = CURL_MAX_TIME_S) -> list:
    """The body GET: once, https only, no --retry, no -C / -r (Range / resume), no -L. Low-speed limit as providers.iex_hist."""
    return ['curl', '-sS', '--fail', '--proto', '=https', '--connect-timeout', str(ih.CURL_CONNECT_TIMEOUT_S),
            '--speed-limit', str(ih.CURL_SPEED_LIMIT_BPS), '--speed-time', str(ih.CURL_SPEED_TIME_S),
            '--max-time', str(max(1, int(max_time))), '-o', '-', link]


class SourceClient:
    """The ONLY way to the price source: at most SOURCE_GET_BUDGET requests, each kind once, exact approved URL shapes
    (public_price_boundary.PRICE_SOURCE_URL_PATTERNS) checked before any network access."""

    def __init__(self, counts: Counts, *, get=_urllib_get, body_command=curl_body_command, budget: int = SOURCE_GET_BUDGET):
        self.counts, self._get, self._body_command, self.budget = counts, get, body_command, budget
        self.used: list = []

    def _spend(self, kind: str, url: str, kinds) -> None:
        if boundary.price_source_kind(url) not in kinds:
            _fail('SOURCE_URL_INVALID')
        if kind in self.used:
            _fail('SOURCE_REQUEST_REPEATED')
        if len(self.used) >= self.budget:
            _fail('SOURCE_BUDGET_EXCEEDED')
        self.used.append(kind)
        self.counts.add('source_get')

    def get_json(self, kind: str, url: str, cap: int, kinds):
        self._spend(kind, url, kinds)
        body = self._get(url, cap)
        if len(body) > cap:
            _fail(f'{kind}_TOO_LARGE')
        try:
            return json.loads(body)
        except ValueError:
            _fail(f'{kind}_INVALID')

    def index(self):
        return self.get_json('INDEX', ih.HIST_URL, INDEX_CAP, ('IEX_HIST_INDEX',))

    def metadata_url(self, url: str):
        return self.get_json('METADATA', url, METADATA_CAP, ('IEX_HIST_OBJECT',))

    def metadata(self, link: str):
        return self.metadata_url(ih.gcs_metadata_url(link))

    def body_command(self, link: str, max_time: int) -> list:
        self._spend('BODY', link, ('IEX_HIST_OBJECT', 'IEX_HIST_BUCKET'))
        return self._body_command(link, max_time)


def select_exact_day(index, day: str = DAY) -> dict:
    """The TOPS 1.6 entry of exactly `day` (an NYSE session day), size as int in (0, BODY_CAP]. No other day, ever."""
    if not isinstance(index, dict):
        _fail('INDEX_INVALID')
    feeds = index.get(day)
    matches = [f for f in feeds if isinstance(f, dict) and (f.get('feed'), f.get('version')) == ih.FEED] \
        if isinstance(feeds, list) else []
    if not matches:
        _fail('NO_FILE_FOR_EXACT_DAY')
    if len(matches) != 1:
        _fail('INDEX_AMBIGUOUS')
    if not ih.session_file_day(day) or ih.tops_files({day: matches}).get(day) is not matches[0]:
        _fail('INDEX_LINK_INVALID')
    try:
        size = int(matches[0]['size'])
    except (KeyError, TypeError, ValueError):
        _fail('INDEX_INVALID')
    if size <= 0:
        _fail('INDEX_INVALID')
    if size > BODY_CAP:
        _fail('BODY_CAP_EXCEEDED')
    return dict(matches[0], size=size)


def object_checks(entry: dict, source: SourceClient) -> tuple:
    """(size, md5 hex) of the object metadata (providers.iex_hist.file_checks: size must equal the index size)."""
    try:
        size, md5 = ih.file_checks(entry, source.metadata_url)
    except ih.IexHistError as e:
        _fail('METADATA_SIZE_MISMATCH' if str(e) == 'SIZE_MISMATCH' else 'METADATA_INVALID')
    if size > BODY_CAP:
        _fail('BODY_CAP_EXCEEDED')
    return size, md5


# ---- private store ----------------------------------------------------------------------------------------------------------
def http_stream(method: str, url: str, *, body=None, length=None, headers=None, auth=True, sink=None, cap=PRIVATE_INPUT_CAP):
    """raw_store_release.http in the same style (Accept, API version, Bearer RAW_REPO_TOKEN, no redirect followed), with a
    streamed request body (`body`: an iterable of bytes, `length`: Content-Length) and a streamed 200 response (`sink(block)`).
    Returns (status, headers, data): data = the response body (<= cap bytes) without a sink, else the byte count."""
    headers = dict(headers or {})
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Accept', headers.pop('Accept', 'application/vnd.github+json'))
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    if length is not None:
        req.add_header('Content-Length', str(length))
    for k, v in headers.items():
        req.add_header(k, v)
    if auth:
        req.add_header('Authorization', 'Bearer ' + rsr._token())
    opener = urllib.request.build_opener(rsr._NoRedirect)
    try:
        with opener.open(req, timeout=HTTP_TIMEOUT_S) as r:
            if sink is None or r.status != 200:
                return r.status, dict(r.headers), r.read(cap + 1)
            n = 0
            for block in iter(lambda: r.read(NET_BLOCK), b''):
                sink(block)
                n += len(block)
            return r.status, dict(r.headers), n
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), (e.read(cap + 1) if e.fp else b'')


def _file_blocks(path: Path, digest) -> 'iter':
    with path.open('rb') as f:
        for block in iter(lambda: f.read(NET_BLOCK), b''):
            digest.update(block)
            yield block


class ReleaseStore:
    """The private release RELEASE_TAG of RAW_REPO, through raw_store_release (release_for_tag, the token, its http style)."""

    def __init__(self, counts: Counts, *, repo: str = RAW_REPO, tag: str = RELEASE_TAG, transport=http_stream):
        self.counts, self.repo, self.tag, self._t = counts, repo, tag, transport
        self.release_id = None

    def _call(self, method, url, *, data=None, headers=None, auth=True):   # raw_store_release.http signature
        return self._t(method, url, body=data, length=None if data is None else len(data), headers=headers, auth=auth)

    def read_input(self, path: str, ref: str) -> bytes:
        self.counts.add('private_read')
        url = f'{rsr.API}/repos/{self.repo}/contents/{urllib.parse.quote(path)}?ref={ref}'
        status, _, data = self._t('GET', url, headers={'Accept': 'application/vnd.github.raw+json'})
        if status != 200 or len(data) > PRIVATE_INPUT_CAP:
            _fail('PRIVATE_INPUT_READ_FAILED')
        return data

    def prepare(self) -> list:
        """The release, created when missing. Refused when it holds anything but earlier FAILED manifests."""
        self.counts.add('release_lookup')
        try:
            release = rsr.release_for_tag(self.repo, self.tag, create=False, call=self._call)
        except rsr.ReleaseError as e:
            if 'http=404' not in str(e):
                _fail('RELEASE_LOOKUP_FAILED')
            self.counts.add('release_create')
            payload = json.dumps({'tag_name': self.tag, 'name': self.tag, 'draft': False, 'prerelease': False,
                                  'body': 'IEX HIST TOPS 1.6 original of one day (private, chunked). See manifest.json.'}).encode()
            status, _, body = self._call('POST', f'{rsr.API}/repos/{self.repo}/releases', data=payload,
                                         headers={'Content-Type': 'application/json'})
            if status != 201:
                _fail('RELEASE_CREATE_FAILED')
            release = json.loads(body)
        except Exception:  # noqa: BLE001
            _fail('RELEASE_LOOKUP_FAILED')
        self.release_id = release['id']
        names = [a.get('name', '') for a in release.get('assets', [])]
        if any(not (n.startswith(FAILED_PREFIX) and n.endswith('.json')) for n in names):
            _fail('RELEASE_NOT_EMPTY')
        return names

    def _upload(self, name: str, body, length: int, ctype: str) -> dict:
        self.counts.add('upload')
        url = f'{rsr.UPLOADS}/repos/{self.repo}/releases/{self.release_id}/assets?name={urllib.parse.quote(name)}'
        status, _, resp = self._t('POST', url, body=body, length=length, headers={'Content-Type': ctype})
        if status != 201:
            _fail('ASSET_UPLOAD_FAILED')
        asset = json.loads(resp)
        if asset.get('name') != name or asset.get('size') != length:
            _fail('ASSET_UPLOAD_FAILED')
        return {'id': asset['id'], 'name': name, 'size': length}

    def upload_file(self, path: Path, name: str) -> tuple:
        """(asset, SHA-256 of the bytes sent): streamed from disk in NET_BLOCK pieces, hashed on the way."""
        digest = hashlib.sha256()
        asset = self._upload(name, _file_blocks(path, digest), path.stat().st_size, 'application/octet-stream')
        return asset, digest.hexdigest()

    def list_assets(self) -> list:
        self.counts.add('release_lookup')
        status, _, body = self._t('GET', f'{rsr.API}/repos/{self.repo}/releases/{self.release_id}/assets?per_page=100')
        if status != 200:
            _fail('RELEASE_LOOKUP_FAILED')
        return [{'id': a['id'], 'name': a['name'], 'size': a.get('size')} for a in json.loads(body)]

    def upload_bytes(self, name: str, data: bytes) -> dict:
        return self._upload(name, data, len(data), 'application/json')

    def stream_asset(self, asset: dict, sink) -> int:
        """The asset's bytes into sink(block): the API answers with a redirect, followed WITHOUT the token."""
        self.counts.add('download')
        status, headers, n = self._t('GET', f'{rsr.API}/repos/{self.repo}/releases/assets/{asset["id"]}',
                                     headers={'Accept': 'application/octet-stream'}, sink=sink)
        if status in (301, 302, 303, 307, 308):
            location = headers.get('Location') or headers.get('location')
            if not location or urllib.parse.urlsplit(location).scheme != 'https':
                _fail('ASSET_REDIRECT_INVALID')
            self.counts.add('download')
            status, _, n = self._t('GET', location, headers={'Accept': 'application/octet-stream'}, auth=False, sink=sink)
        if status != 200:
            _fail('ASSET_DOWNLOAD_FAILED')
        return n

    def delete_asset(self, asset: dict) -> bool:
        self.counts.add('delete')
        status, _, _ = self._t('DELETE', f'{rsr.API}/repos/{self.repo}/releases/assets/{asset["id"]}')
        return status == 204


class FakeStore:
    """A release store on a local directory (dry run and tests). Same interface and the same request counting."""

    def __init__(self, counts: Counts, root: Path, inputs: dict, *, existing=()):
        self.counts, self.root, self.inputs = counts, Path(root), inputs
        self.root.mkdir(parents=True, exist_ok=True)
        self.assets: dict = {}
        self.release_id = None
        self._next = 1
        for name in existing:
            self._put(name, b'{}')

    def _put(self, name: str, data: bytes) -> dict:
        if name in {a['name'] for a in self.assets.values()}:
            _fail('ASSET_UPLOAD_FAILED')
        asset = {'id': self._next, 'name': name, 'size': len(data)}
        self._next += 1
        (self.root / str(asset['id'])).write_bytes(data)
        self.assets[asset['id']] = asset
        return dict(asset)

    def read_input(self, path: str, ref: str) -> bytes:
        self.counts.add('private_read')
        if ref != INPUT_COMMIT or path not in self.inputs:
            _fail('PRIVATE_INPUT_READ_FAILED')
        return self.inputs[path]

    def prepare(self) -> list:
        self.counts.add('release_lookup')
        if self.release_id is None:
            self.counts.add('release_create')
            self.release_id = 1
        names = [a['name'] for a in self.assets.values()]
        if any(not (n.startswith(FAILED_PREFIX) and n.endswith('.json')) for n in names):
            _fail('RELEASE_NOT_EMPTY')
        return names

    def upload_file(self, path: Path, name: str) -> tuple:
        self.counts.add('upload')
        if name in {a['name'] for a in self.assets.values()}:
            _fail('ASSET_UPLOAD_FAILED')
        digest, size = hashlib.sha256(), 0
        dest = self.root / f'.{self._next}.tmp'
        with dest.open('wb') as out:
            for block in _file_blocks(path, digest):
                out.write(block)
                size += len(block)
        asset = {'id': self._next, 'name': name, 'size': size}
        self._next += 1
        dest.rename(self.root / str(asset['id']))
        self.assets[asset['id']] = asset
        return dict(asset), digest.hexdigest()

    def list_assets(self) -> list:
        self.counts.add('release_lookup')
        return [dict(a) for a in self.assets.values()]

    def upload_bytes(self, name: str, data: bytes) -> dict:
        self.counts.add('upload')
        return self._put(name, data)

    def stream_asset(self, asset: dict, sink) -> int:
        self.counts.add('download', 2)          # the API request and its redirect, as the real store
        path = self.root / str(asset['id'])
        if asset['id'] not in self.assets or not path.exists():
            _fail('ASSET_DOWNLOAD_FAILED')
        n = 0
        with path.open('rb') as f:
            for block in iter(lambda: f.read(NET_BLOCK), b''):
                sink(block)
                n += len(block)
        return n

    def delete_asset(self, asset: dict) -> bool:
        self.counts.add('delete')
        if self.assets.pop(asset['id'], None) is None:
            return False
        (self.root / str(asset['id'])).unlink(missing_ok=True)
        return True

    def get(self, name: str) -> bytes:
        asset = next(a for a in self.assets.values() if a['name'] == name)
        return (self.root / str(asset['id'])).read_bytes()


def verify_asset(store, asset: dict, size: int, sha256: str) -> None:
    digest = hashlib.sha256()
    n = store.stream_asset(asset, digest.update)
    if n != size or digest.hexdigest() != sha256:
        _fail('CHUNK_VERIFY_FAILED')


# ---- 4. chunk uploader (background) --------------------------------------------------------------------------------------
class ChunkUploader:
    """Uploads closed chunk files in order on its own thread: upload (streamed from disk) -> download back -> SHA-256 and size
    check -> delete the local copy. The reading loop only enqueues (never waits), so the body download is never paused by an
    upload. The first failure is kept in `error` (a fixed code); later chunks are then only deleted locally."""

    def __init__(self, store, *, deadline: float, monotonic=time.monotonic):
        self.store, self.deadline, self._monotonic = store, deadline, monotonic
        self.error = None
        self.uploaded: list = []      # every asset this run created (verified or not): the cleanup list
        self.verified: list = []      # {name, size, sha256, id} in chunk order
        self._q: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, path: Path, name: str, size: int, sha256: str) -> None:
        self._q.put((path, name, size, sha256))

    def _run(self) -> None:
        for path, name, size, sha256 in iter(self._q.get, None):
            try:
                if self.error is None:
                    if self._monotonic() > self.deadline:
                        raise PreserveError('DEADLINE_EXCEEDED')
                    asset, sent = self.store.upload_file(path, name)
                    self.uploaded.append(asset)
                    if sent != sha256:
                        raise PreserveError('LOCAL_CHUNK_SHA_MISMATCH')
                    verify_asset(self.store, asset, size, sha256)
                    self.verified.append({'name': name, 'size': size, 'sha256': sha256, 'id': asset['id']})
            except PreserveError as e:
                self.error = self.error or str(e)
            except Exception:  # noqa: BLE001
                self.error = self.error or 'CHUNK_UPLOAD_FAILED'
            finally:
                path.unlink(missing_ok=True)

    def close(self, timeout=None) -> None:
        self._q.put(None)
        self._thread.join(timeout)


# ---- 4-5. one streaming pass -------------------------------------------------------------------------------------------
def _drain(stream, out: list, cap: int) -> None:
    kept, total = [], 0
    for block in iter(lambda: stream.read(65536), b''):
        if total < cap:
            kept.append(block[:cap - total])
        total += len(block)
    out.append((b''.join(kept), total))


def stream_once(command: list, *, size: int, md5: str, parser: str, symfile: Path, t0: int, t1: int, workdir: Path,
                uploader: ChunkUploader, chunk_bytes: int = CHUNK_BYTES, max_chunks: int = MAX_CHUNKS,
                deadline: float, disk_free=lambda p: shutil.disk_usage(p).free, runtime_margin: int = RUNTIME_MARGIN,
                popen=subprocess.Popen, monotonic=time.monotonic) -> dict:
    """body | (sha256 + md5 + count + chunk files) | gzip -dc | parser, in one pass. Returns the stream result; PreserveError
    (failed stage) on any check failure, with every child killed and reaped and the open chunk file removed."""
    whole_sha, whole_md5 = hashlib.sha256(), hashlib.md5()
    got, chunks, cur, cur_sha, cur_len, cur_path = 0, [], None, None, 0, None
    procs, broken, abort, codes = [], False, None, None
    out, err = [], []
    readers = []
    start = monotonic()

    def close_chunk():
        nonlocal cur, cur_path, cur_len, cur_sha
        cur.close()
        name = f'{CHUNK_PREFIX}{len(chunks) + 1:03d}'
        chunks.append({'name': name, 'size': cur_len, 'sha256': cur_sha.hexdigest()})
        uploader.submit(cur_path, name, cur_len, cur_sha.hexdigest())
        cur, cur_path, cur_len, cur_sha = None, None, 0, None

    try:
        p1 = popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p1)
        p2 = popen(['gzip', '-dc'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p2)
        p3 = popen([parser, str(symfile), str(t0), str(t1)], stdin=p2.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procs.append(p3)
        p2.stdout.close()
        readers = [threading.Thread(target=_drain, args=(p3.stdout, out, PARSER_OUT_CAP), daemon=True),
                   threading.Thread(target=_drain, args=(p3.stderr, err, 4096), daemon=True)]
        for r in readers:
            r.start()
        try:
            while True:
                block = p1.stdout.read(READ_BLOCK)
                if not block:
                    break
                got += len(block)
                if got > size:
                    abort = 'SIZE_MISMATCH'            # more bytes than the metadata size: never stored
                    break
                if uploader.error:
                    abort = uploader.error
                    break
                if monotonic() > deadline:
                    abort = 'DEADLINE_EXCEEDED'
                    break
                whole_sha.update(block)
                whole_md5.update(block)
                view = memoryview(block)
                while view:
                    if cur is None:
                        if len(chunks) >= max_chunks:
                            abort = 'CHUNK_LIMIT_EXCEEDED'
                            break
                        if disk_free(workdir) < min(chunk_bytes, size - (got - len(view))) + runtime_margin:
                            abort = 'DISK_RUNTIME_LOW'
                            break
                        cur_path = workdir / f'{CHUNK_PREFIX}{len(chunks) + 1:03d}'
                        cur, cur_sha, cur_len = cur_path.open('wb'), hashlib.sha256(), 0
                    take = view[:chunk_bytes - cur_len]
                    cur.write(take)
                    cur_sha.update(take)
                    cur_len += len(take)
                    view = view[len(take):]
                    if cur_len == chunk_bytes:
                        close_chunk()
                if abort:
                    break
                p2.stdin.write(block)
        except BrokenPipeError:
            broken = True
        finally:
            try:
                p2.stdin.close()
            except BrokenPipeError:
                broken = True
        if broken or abort:
            p1.kill()
        if abort:
            p2.kill()
            p3.kill()
        codes = (p1.wait(), p2.wait(), p3.wait())
        for r in readers:
            r.join()
    except PreserveError:
        raise
    except Exception:  # noqa: BLE001
        abort = 'STREAM_FAILED'
        codes = None
    finally:
        if abort or codes is None:
            for p in procs:
                p.kill()
            for p in procs:
                try:
                    p.wait(timeout=ih.REAP_TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    pass
        for p in procs:
            for pipe in (p.stdin, p.stdout, p.stderr):
                try:
                    if pipe is not None:
                        pipe.close()
                except OSError:
                    pass
        if cur is not None and (abort or codes is None):
            cur.close()
            cur_path.unlink(missing_ok=True)
            cur = None
    flow_s = round(monotonic() - start, 3)
    if abort:
        _fail(abort)
    stage = ih.failed_stage(codes, broken, size_ok=got == size, md5_ok=whole_md5.hexdigest() == md5)
    if stage:
        if cur is not None:
            cur.close()
            cur_path.unlink(missing_ok=True)
        _fail(stage)
    if cur is not None:
        close_chunk()
    if sum(c['size'] for c in chunks) != got:
        _fail('CHUNK_SUM_MISMATCH')
    try:
        text = out[0][0].decode('ascii') if out[0][1] <= PARSER_OUT_CAP else None
    except (IndexError, UnicodeDecodeError):
        text = None
    if text is None:
        _fail('PARSER_OUTPUT_INVALID')
    stats = parse_stats(err[0][0].decode('ascii', 'replace') if err else '')
    return {'bytes': got, 'sha256': whole_sha.hexdigest(), 'md5': whole_md5.hexdigest(), 'chunks': chunks,
            'parser_text': text, 'parser_stats': stats, 'exit_codes': list(codes), 'flow_s': flow_s}


def parse_stats(text: str) -> dict:
    """The parser's '#STATS k=v ...' stderr line (counts only)."""
    line = next((l for l in text.splitlines() if l.startswith('#STATS ')), '')
    out = {}
    for part in line.split()[1:]:
        k, _, v = part.partition('=')
        if re.fullmatch(r'[a-z_]+', k) and re.fullmatch(r'[0-9]+', v):
            out[k] = int(v)
    return out


# ---- 6. reassembly -------------------------------------------------------------------------------------------------------
def reassembly_check(store, verified: list, *, sha256: str, size: int) -> None:
    digest, n = hashlib.sha256(), 0
    for c in verified:
        n += store.stream_asset({'id': c['id'], 'name': c['name']}, digest.update)
    if n != size or digest.hexdigest() != sha256:
        _fail('REASSEMBLY_MISMATCH')


# ---- 7. derived rows -----------------------------------------------------------------------------------------------------
def parser_rows(text: str, symbols) -> dict:
    """Parser stdout -> {SYM: (status, price_e4, ts_ns, dir_seen, trading_status, all_trades)} for exactly `symbols`."""
    rows = {}
    for line in text.splitlines():
        cols = line.split('\t')
        if len(cols) != 8 or cols[1] not in ih.PARSER_STATUSES or cols[0] in rows:
            _fail('PARSER_OUTPUT_INVALID')
        try:
            px, ts, all_trades = int(cols[2]), int(cols[3]), int(cols[7])
        except ValueError:
            _fail('PARSER_OUTPUT_INVALID')
        rows[cols[0]] = (cols[1], px, ts, cols[5], cols[6], all_trades)
    if set(rows) != set(symbols):
        _fail('PARSER_SYMBOLS_MISMATCH')
    return rows


def derive_rows(codes, symbol_of: dict, rows: dict, *, t0: int, t1: int, parser_sha: str) -> list:
    """One row per code. A missing or invalid price gets a reason; never another day's or another symbol's price."""
    out = []
    for i, code in zip(ROW_INDEXES if len(codes) == len(ROW_INDEXES) else range(len(codes)), codes):
        sym = symbol_of[code]
        row = {'row_index': i, 'code': code, 'iex_symbol': sym, 'state': None, 'reason': None, 'price': None,
               'last_trade_ns': None, 'last_trade_utc': None, 'basis_date': BASIS_DATE, 'source': SOURCE_LABEL,
               'parser_source_sha256': parser_sha}
        if sym is None:
            row.update(state='NOT_IN_FILE', reason='IEX_SYMBOL_NONE_FROM_ALIAS_DATE')
        elif not ih.valid_symbol(sym):
            row.update(state='PRICE_INVALID', reason='IEX_SYMBOL_INVALID')
        else:
            status, px, ts, dir_seen, trading, all_trades = rows[sym]
            if status == 'ROUND':
                if not 0 < px < ih.MAX_PRICE_E4:
                    row.update(state='PRICE_INVALID', reason='PRICE_OUT_OF_RANGE')
                elif not t0 <= ts < t1:
                    row.update(state='PRICE_INVALID', reason='TIMESTAMP_OUTSIDE_SESSION')
                else:
                    row.update(state='PRICE', price=price_text(px), last_trade_ns=ts, last_trade_utc=_ns_utc(ts))
            elif status == 'ODD_ONLY':
                row.update(state='NO_TRADE', reason='ODD_LOT_ONLY')
            elif dir_seen == '0' and trading == '-' and all_trades == 0:
                row.update(state='NOT_IN_FILE', reason='SYMBOL_NOT_IN_FILE')
            else:
                row.update(state='NO_TRADE', reason='NO_REGULAR_SESSION_ROUND_LOT_TRADE')
        out.append(row)
    return out


def state_counts(rows) -> dict:
    return {s: sum(1 for r in rows if r['state'] == s) for s in STATES}


# ---- the run --------------------------------------------------------------------------------------------------------------
def _versions(parser: str) -> dict:
    def first_line(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.splitlines()[0][:120]
        except Exception:  # noqa: BLE001
            return None
    return {'python': platform.python_version(), 'compiler': first_line(['cc', '--version']),
            'compile_command': 'cc -O2 -o iex_last_trade implementation/tools/iex_tops/iex_last_trade.c'}


def _git_commit() -> str | None:
    sha = os.environ.get('GITHUB_SHA', '')
    if re.fullmatch(r'[0-9a-f]{40}', sha):
        return sha
    try:
        sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return None
    return sha if re.fullmatch(r'[0-9a-f]{40}', sha) else None


def _file_sha(path: Path) -> str | None:
    try:
        return rsr.file_sha(path)
    except OSError:
        return None


def run(*, store, source: SourceClient, counts: Counts, parser: str, workdir: Path, token_present: bool = True,
        chunk_bytes: int = CHUNK_BYTES, max_chunks: int = MAX_CHUNKS, min_free: int = MIN_FREE_BYTES,
        runtime_margin: int = RUNTIME_MARGIN, disk_free=lambda p: shutil.disk_usage(p).free,
        expected_manifest_sha: str = INPUT_MANIFEST_SHA256, deadline_s: float = DEADLINE_S,
        monotonic=time.monotonic, now=time.time, popen=subprocess.Popen, versions=None) -> dict:
    """The whole pipeline. Returns the manifest written (state COMPLETE or FAILED); never raises a PreserveError."""
    t_start, m_start = now(), monotonic()
    deadline = m_start + deadline_s
    timings: dict = {}
    parser_src = ROOT / 'tools/iex_tops/iex_last_trade.c'
    man = {'schema_version': SCHEMA, 'state': None, 'failed_stage': None, 'day': BASIS_DATE, 'release_tag': RELEASE_TAG,
           'parser': {'source_path': 'implementation/tools/iex_tops/iex_last_trade.c', 'source_sha256': _file_sha(parser_src),
                      'binary_sha256': _file_sha(Path(parser)), 'git_commit': _git_commit(), 'mode': 'SYMBOLS_FILE'},
           'environment': versions if versions is not None else _versions(parser),
           'limits': {'source_get_budget': SOURCE_GET_BUDGET, 'index_cap_bytes': INDEX_CAP, 'metadata_cap_bytes': METADATA_CAP,
                      'body_cap_bytes': BODY_CAP, 'chunk_bytes': chunk_bytes, 'max_chunks': max_chunks,
                      'min_free_bytes': min_free}}
    uploader = None
    outputs: list = []                 # derived / manifest assets this run uploaded (cleanup on failure)
    symfile = workdir / f'iex-symbols-{DAY}.txt'
    stage = 'ENV'
    prepared = False                   # this run saw the release empty (but for FAILED manifests): every asset named
    mark = monotonic()                 # like ours after that is this run's own

    def done(name):
        nonlocal mark
        timings[name] = round(monotonic() - mark, 3)
        mark = monotonic()

    try:
        # 0. environment, before any request
        workdir.mkdir(parents=True, exist_ok=True)
        if not token_present:
            _fail('RAW_REPO_TOKEN_MISSING')
        if not (Path(parser).is_file() and os.access(parser, os.X_OK)) or man['parser']['source_sha256'] is None:
            _fail('PARSER_MISSING')
        free = disk_free(workdir)
        man['environment']['free_bytes_at_start'] = free
        _log('ENV', free_bytes=free, min_free_bytes=min_free)
        if free < min_free:
            _fail('DISK_PRECHECK_FAILED')
        done('env_s')
        # 1. private input
        stage = 'PRIVATE_INPUT'
        manifest_bytes = store.read_input(f'{INPUT_DIR}/{INPUT_MANIFEST}', INPUT_COMMIT)
        file_bytes = store.read_input(f'{INPUT_DIR}/{INPUT_FILE}', INPUT_COMMIT)
        codes, receipt = select_codes(manifest_bytes, file_bytes, expected_manifest_sha=expected_manifest_sha)
        del manifest_bytes, file_bytes
        symbol_of = map_symbols(codes)
        sym_bytes = symbols_file_bytes(symbol_of)
        man['input'] = receipt
        man['symbols_filter'] = {'sha256': _sha256(sym_bytes), 'count': sym_bytes.count(b'\n'), 'codes': len(codes)}
        _log('PRIVATE_INPUT_OK', codes=len(codes), symbols=man['symbols_filter']['count'], file_sha256=receipt['file_sha256'])
        done('private_input_s')
        # 2. release
        stage = 'RELEASE_PREPARE'
        earlier = store.prepare()
        prepared = True
        man['earlier_failed_manifests'] = len(earlier)
        done('release_prepare_s')
        # 3. source (a) index, (b) metadata
        stage = 'SOURCE_INDEX'
        entry = select_exact_day(source.index())
        _log('INDEX_OK', index_size=entry['size'])
        done('source_index_s')
        stage = 'SOURCE_METADATA'
        size, md5 = object_checks(entry, source)
        n_chunks = -(-size // chunk_bytes)
        if n_chunks > max_chunks:
            _fail('CHUNK_LIMIT_EXCEEDED')
        man['source'] = {'index_url': ih.HIST_URL, 'link': entry['link'], 'metadata_url': ih.gcs_metadata_url(entry['link']),
                         'feed': 'TOPS', 'version': '1.6', 'index_day': DAY, 'index_size': entry['size'],
                         'metadata_size': size, 'metadata_md5': md5, 'expected_chunks': n_chunks}
        _log('METADATA_OK', size=size, md5=md5, expected_chunks=n_chunks)
        done('source_metadata_s')
        # 4-5. one streaming pass (source GET (c)) with the background uploader
        stage = 'STREAM'
        symfile.write_bytes(sym_bytes)
        t0, t1 = ih.session_ns(DAY)
        man['session_window_ns'] = [t0, t1]
        uploader = ChunkUploader(store, deadline=deadline, monotonic=monotonic)
        command = source.body_command(entry['link'], min(CURL_MAX_TIME_S, max(1, int(deadline - monotonic()))))
        result = stream_once(command, size=size, md5=md5, parser=parser, symfile=symfile, t0=t0, t1=t1, workdir=workdir,
                             uploader=uploader, chunk_bytes=chunk_bytes, max_chunks=max_chunks, deadline=deadline,
                             disk_free=disk_free, runtime_margin=runtime_margin, popen=popen, monotonic=monotonic)
        symfile.unlink(missing_ok=True)
        man['received'] = {'bytes': result['bytes'], 'md5': result['md5'], 'sha256': result['sha256'],
                           'exit_codes': result['exit_codes'], 'flow_s': result['flow_s']}
        man['parser_stats'] = result['parser_stats']
        _log('STREAM_OK', bytes=result['bytes'], sha256=result['sha256'], md5=result['md5'], chunks=len(result['chunks']))
        done('stream_s')
        stage = 'CHUNK_UPLOAD'
        uploader.close(timeout=max(1, deadline - monotonic()))
        if uploader.error:
            _fail(uploader.error)
        if [c['name'] for c in uploader.verified] != [c['name'] for c in result['chunks']] or \
                any(v['sha256'] != c['sha256'] or v['size'] != c['size'] for v, c in zip(uploader.verified, result['chunks'])):
            _fail('CHUNK_VERIFY_FAILED')
        _log('CHUNKS_VERIFIED', chunks=len(uploader.verified))
        done('chunk_upload_wait_s')
        # 6. reassembly
        stage = 'REASSEMBLY'
        reassembly_check(store, uploader.verified, sha256=result['sha256'], size=result['bytes'])
        _log('REASSEMBLY_OK', bytes=result['bytes'], sha256=result['sha256'])
        done('reassembly_s')
        # 7. derived rows, then manifest.json last
        stage = 'DERIVE'
        wanted = sorted({s for s in symbol_of.values() if ih.valid_symbol(s)})
        rows = derive_rows(codes, symbol_of, parser_rows(result['parser_text'], wanted), t0=t0, t1=t1,
                           parser_sha=man['parser']['source_sha256'])
        del result['parser_text']
        derived = {'schema_version': DERIVED_SCHEMA, 'basis_date': BASIS_DATE, 'source': SOURCE_LABEL,
                   'basis_kind': ih.BASIS_KIND, 'currency': ih.CURRENCY, 'unit': 'USD per share',
                   'adjustment_basis': ih.ADJUSTMENT_BASIS, 'attribution': ih.ATTRIBUTION,
                   'original': {'release_tag': RELEASE_TAG, 'sha256': man['received']['sha256'], 'md5': man['received']['md5'],
                                'bytes': man['received']['bytes']},
                   'input': {k: receipt[k] for k in ('commit', 'path', 'file_sha256', 'row_indexes')},
                   'session_window_ns': [t0, t1], 'parser_source_sha256': man['parser']['source_sha256'],
                   'parser_git_commit': man['parser']['git_commit'], 'rows': rows}
        derived_bytes = json.dumps(derived, ensure_ascii=True, indent=1).encode()
        counts_by_state = state_counts(rows)
        stage = 'OUTPUT_UPLOAD'
        outputs.append(store.upload_bytes(DERIVED_NAME, derived_bytes))
        man['derived'] = {'name': DERIVED_NAME, 'sha256': _sha256(derived_bytes), 'bytes': len(derived_bytes),
                          'rows': len(rows), 'states': counts_by_state}
        man['chunks'] = [{'name': c['name'], 'size': c['size'], 'sha256': c['sha256']} for c in uploader.verified]
        man['completeness'] = {'size_match': True, 'md5_match': True, 'gzip_exit_0': True, 'parser_exit_0': True,
                               'curl_exit_0': True, 'all_chunks_verified': True, 'reassembly_match': True,
                               'derived_rows': len(rows), 'derived_rows_expected': len(ROW_INDEXES)}
        man['state'] = 'COMPLETE'
        timings['total_s'] = round(monotonic() - m_start, 3)
        man['timings'] = dict(timings, started_at=_utc(t_start), finished_at=_utc(now()))
        man['requests'] = dict(counts.snapshot(), upload=counts.snapshot()['upload'] + 1)   # + this manifest upload
        outputs.append(store.upload_bytes(MANIFEST_NAME, json.dumps(man, ensure_ascii=True, indent=1).encode()))
        _log('COMPLETE', chunks=len(man['chunks']), bytes=man['received']['bytes'], sha256=man['received']['sha256'],
             **{s.lower(): n for s, n in counts_by_state.items()})
        _log('REQUESTS', **counts.snapshot())
        return man
    except BaseException as e:  # noqa: BLE001 - every failure, a signal included, ends in the cleanup below
        code = str(e) if isinstance(e, PreserveError) else ('CANCELLED' if isinstance(e, KeyboardInterrupt) else 'UNEXPECTED_ERROR')
        failed = _failure(code, stage, man, store=store, uploader=uploader, outputs=outputs, workdir=workdir, symfile=symfile,
                          counts=counts, timings=timings, t_start=t_start, now=now, monotonic=monotonic, m_start=m_start,
                          token_present=token_present, prepared=prepared)
        return failed


def _ours(name: str) -> bool:
    return name.startswith(CHUNK_PREFIX) or name in (DERIVED_NAME, MANIFEST_NAME)


def _failure(code, stage, man, *, store, uploader, outputs, workdir, symfile, counts, timings, t_start, now, monotonic,
             m_start, token_present, prepared) -> dict:
    """Stop, delete local partial files, delete every asset this run uploaded, upload a small FAILED manifest. An upload
    whose answer was lost may still have created its asset, so after this run's own empty-release check (`prepared`) the
    release is listed once and every asset named like ours is deleted too; before that check nothing is listed or deleted
    (a refused, non-empty release is never touched)."""
    if _LIVE:                          # a second cancel signal must not cut the cleanup short
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    _log('FAILED', failed_stage=code if re.fullmatch(r'[A-Z][A-Z0-9_]*', code) else 'UNEXPECTED_ERROR', stage=stage)
    if uploader is not None:
        uploader.error = uploader.error or 'ABORTED'
        uploader.close(timeout=HTTP_TIMEOUT_S)
    symfile.unlink(missing_ok=True)
    for p in workdir.glob(f'{CHUNK_PREFIX}*'):
        p.unlink(missing_ok=True)
    uploaded = (list(uploader.uploaded) if uploader is not None else []) + list(outputs)
    if prepared:
        try:
            uploaded += [a for a in store.list_assets() if _ours(a['name'])]
        except BaseException:  # noqa: BLE001
            pass
    seen, cleanup = set(), []
    for a in uploaded:
        if a and a['id'] not in seen:
            seen.add(a['id'])
            try:
                deleted = bool(store.delete_asset(a))
            except Exception:  # noqa: BLE001
                deleted = False
            cleanup.append({'name': a['name'], 'size': a.get('size'), 'deleted': deleted})
    failed = {'schema_version': SCHEMA, 'state': 'FAILED', 'failed_stage': code, 'stage': stage, 'day': BASIS_DATE,
              'release_tag': RELEASE_TAG, 'uploaded_assets': cleanup,
              'all_partial_assets_deleted': all(c['deleted'] for c in cleanup),
              'source': {k: v for k, v in (man.get('source') or {}).items() if k in ('index_size', 'metadata_size', 'metadata_md5')},
              'parser': man.get('parser'), 'timings': dict(timings, total_s=round(monotonic() - m_start, 3),
                                                           started_at=_utc(t_start), finished_at=_utc(now()))}
    _log('CLEANUP', uploaded_assets=len(cleanup), deleted=sum(c['deleted'] for c in cleanup))
    if token_present and stage != 'RELEASE_PREPARE':     # a release this run refused (not empty) is never written to
        try:
            if not prepared:
                store.prepare()
            failed['requests'] = dict(counts.snapshot(), upload=counts.snapshot()['upload'] + 1)
            name = FAILED_PREFIX + dt.datetime.fromtimestamp(now(), dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json'
            store.upload_bytes(name, json.dumps(failed, ensure_ascii=True, indent=1).encode())
            failed['failed_manifest_uploaded'] = True
        except BaseException:  # noqa: BLE001 - the private repository is not reachable: the log line is all that is left
            failed['failed_manifest_uploaded'] = False
    else:
        failed['failed_manifest_uploaded'] = False
    failed.setdefault('requests', counts.snapshot())
    _log('FAILED_MANIFEST', uploaded=failed['failed_manifest_uploaded'])
    _log('REQUESTS', **counts.snapshot())
    return failed


# ---- dry run (no network) -------------------------------------------------------------------------------------------------
class DryRunSource:
    """SourceClient's request functions on local files: the index JSON as given, the metadata computed from the body file."""

    def __init__(self, index_path: Path, body_path: Path):
        self.index_path, self.body_path = Path(index_path), Path(body_path)

    def get(self, url: str, cap: int) -> bytes:
        if url == ih.HIST_URL:
            return self.index_path.read_bytes()[:cap + 1]
        body = self.body_path.read_bytes()
        meta = {'size': str(len(body)), 'md5Hash': base64.b64encode(hashlib.md5(body).digest()).decode()}
        return json.dumps(meta).encode()[:cap + 1]

    def body_command(self, link: str, max_time: int) -> list:
        return ['cat', str(self.body_path)]


def _require_live_route() -> None:
    """Live mode only as this file's own entry point, inside the one-shot workflow run of RUN_BRANCH."""
    main = sys.modules.get('__main__')
    entry = getattr(main, '__file__', None)
    if not isinstance(entry, str) or Path(entry).resolve() != Path(__file__).resolve():
        _fail('LIVE_ROUTE_NOT_ALLOWED')
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REF') != f'refs/heads/{RUN_BRANCH}':
        _fail('LIVE_ROUTE_NOT_ALLOWED')


def _on_signal(signum, frame):  # noqa: ARG001 - a cancelled job still deletes its partial assets
    raise KeyboardInterrupt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--live', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    ap.add_argument('--parser', required=True)
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--index', help='dry run: a local hist index JSON')
    ap.add_argument('--body', help='dry run: a local TOPS pcap.gz')
    ap.add_argument('--inputs-dir', help='dry run: a directory holding manifest.json and connected-final.json')
    ap.add_argument('--expected-manifest-sha', help='dry run: SHA-256 of that manifest.json')
    ap.add_argument('--store-dir', help='dry run: the fake release store directory')
    ap.add_argument('--chunk-bytes', type=int, default=CHUNK_BYTES, help='dry run only')
    ap.add_argument('--min-free-bytes', type=int, default=MIN_FREE_BYTES, help='dry run only')
    a = ap.parse_args(argv)
    counts = Counts()
    workdir = Path(a.workdir)
    if a.live:
        try:
            _require_live_route()
        except PreserveError as e:
            _log('REFUSED', code=str(e))
            return 2
        if a.chunk_bytes != CHUNK_BYTES or a.min_free_bytes != MIN_FREE_BYTES or a.index or a.body or a.inputs_dir:
            _log('REFUSED', code='LIVE_ARGUMENTS_INVALID')
            return 2
        global _LIVE
        _LIVE = True
        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
        man = run(store=ReleaseStore(counts), source=SourceClient(counts), counts=counts, parser=a.parser, workdir=workdir,
                  token_present=bool(os.environ.get('RAW_REPO_TOKEN')))
    else:
        if not all((a.index, a.body, a.inputs_dir, a.expected_manifest_sha, a.store_dir)):
            ap.error('--dry-run needs --index --body --inputs-dir --expected-manifest-sha --store-dir')
        inputs_dir = Path(a.inputs_dir)
        inputs = {f'{INPUT_DIR}/{n}': (inputs_dir / n).read_bytes() for n in (INPUT_MANIFEST, INPUT_FILE)}
        dry = DryRunSource(Path(a.index), Path(a.body))
        man = run(store=FakeStore(counts, Path(a.store_dir), inputs), counts=counts, parser=a.parser, workdir=workdir,
                  source=SourceClient(counts, get=dry.get, body_command=dry.body_command), chunk_bytes=a.chunk_bytes,
                  min_free=a.min_free_bytes, runtime_margin=0, expected_manifest_sha=a.expected_manifest_sha)
    return 0 if man['state'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
