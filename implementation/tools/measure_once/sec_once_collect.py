"""SEC ONE-TIME COLLECTION (owner decision 2026-11-01: "SEC 1회용 수집: 조건부 승인 ... PR을 먼저 올리고, 승인 뒤 실행한다").
Plan: implementation/docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md. Not part of any pipeline. It runs once from
.github/workflows/sec-once-collect.yml on the push to claude/sec-once-collect-run, which is made only after the owner
approves the plan PR. The workflow starts it with `python -I -S` on a runner where pip installed nothing.

What it fetches (public SEC files only, fixed list; no prices, no KIS, nothing published):
- bulk companyfacts.zip and submissions.zip (www.sec.gov/Archives/edgar/daily-index/...);
- EDGAR full-index form.idx and company.idx of every quarter 2014 QTR1 .. 2026 QTR4 (the last one as of the run day);
- Financial Statement Data Sets 2014q1 .. 2026q3 (www.sec.gov/files/dera/data/financial-statement-data-sets/...).
Where it goes: ONE new release of the private raw repository, tag and name `sec-once-v1-<GITHUB_RUN_ID>` (fixed in code).

Subcommands; each runs in its own workflow step and a step holds at most one Secret:
  plan          no network, no Secret: the fixed file list, planned request counts, free-disk check.
  resume-check  RAW_REPO_TOKEN only. EVERY attempt first reads the raw repository's own metadata (GET /repos/<raw repo>)
                and stops unless it answers 200 with the exact full name, private true and visibility private; only then
                it writes the preflight marker raw-preflight.json (run id + attempt) that `collect` and the classifier
                require before any SEC request. Attempt 1 then reads nothing else. A re-run attempt of the SAME run (same
                run id) reads that run's own release (the one tag above, nothing else) and downloads, per file, the newest
                asset whose sha256 sidecar matches into the work directory, so `collect` does not ask SEC for it again and
                `upload` does not upload it again.
  collect       SEC_USER_AGENT only. Refuses to start without this attempt's preflight marker. Streams each planned file
                to disk (sha256, byte count, Content-Length / gzip end and zip CRC checks, retries with backoff for
                network faults only; a local disk error stops the run at once), writes collect-manifest.json (private),
                prints fixed count lines.
  upload        RAW_REPO_TOKEN only. Checks again that the raw repository is private, then creates the release
                (create-only: attempt 1 never reads it; a re-run reads only its own tag), uploads each file with a
                `.sha256` sidecar (a file over 2,000,000,000 bytes is split into 1,900,000,000-byte parts plus a
                `.parts.json` index; a name already taken by ANY asset of an earlier attempt, parts included, gets the
                a<attempt>- prefix), downloads every data asset of this attempt back to check its sha256, then uploads
                sec-once-manifest-a<attempt>.json (complete only when collection, classification, upload and the
                read-back are all complete) last and reads it back too.
  done          no network: exits 1 unless collection, classification and upload are all complete (so the run shows
                red and "Re-run failed jobs" resumes it).

Code restrictions on the private repository (the token is repository-wide, so the limits are in code, not in the token):
only the endpoints in ReleaseClient.check (read the raw repository's metadata, create one release, upload assets to it,
read that one release by its own tag on re-run attempts, download that release's own assets); never PATCH, PUT or DELETE;
never list releases; never a KIS or any other release; asset names from one allow-list.

SEC fair access: the User-Agent comes only from env SEC_USER_AGENT and is never printed; exact URL allow-list on
www.sec.gov, redirects refused; a fixed 0.15 s sleep before every request (at most 6.7 requests per second, one request at
a time); 429, 5xx, network errors and truncated bodies retried at most twice with backoff; caps on requests, wall clock
and sizes; five 403s in a row or ten 429s stop the run.
Output: fixed lines only (codes, counts, MB, seconds). Never a URL, User-Agent, token, ticker, CIK, company name or
exception text (class names and fixed codes only):
  SECONCE_PLAN bulk=2 index_files=104 index_years=2014-2026 fsds_files=51 fsds_quarters=2014q1-2026q3
      sec_requests_planned=157 max_requests=<n> wall_clock_s=<s> pace_s=0.15
  SECONCE_DISK free_gb=<GiB> need_gb=<GiB> ok=yes|no
  SECONCE_PREFLIGHT raw_repo=private
  SECONCE_RESUME attempt=<n> release=NOT_READ|ABSENT|PRESENT assets=<n> verified=<n> unverified=<n>
      (older copies of a file are not read once a newer copy verified)
  SECONCE_FILES kind=bulk|index|fsds planned=<n> ok=<n> resumed=<n> failed=<n> optional_missing=<n> mb=<MB>
      (optional: only the newest FSDS quarter, 2026q3; its 404 is not a failure)
  SECONCE_ZIP name=companyfacts|submissions entries=<n>|NA overflow_pages=<n>|NA check=<CODE>
  SECONCE_ZIP name=fsds files=<n> ok=<n> bad=<n>
  SECONCE_INDEX year=<y> quarters=<n> rows=<n> f10k f10q f8k f25 f25nse f8a12b f1512b f1512g f1515d (key=<count>)
  SECONCE_ERRORS codes=<CODE:n,...>|-
  SECONCE_REQUESTS total bulk index fsds retries redownloads http403 http429 http5xx (key=<count>) mb_wire=<MB>
      mb_body=<MB> elapsed_s=<s> stopped=NONE|<reason> complete=yes|no
  SECONCE_RELEASE created=yes|no assets_uploaded=<n> assets_present=<n> assets_failed=<n> mb=<MB> manifest=OK|FAILED
  SECONCE_VERIFY assets=<n> ok=<n> bad=<n>
  SECONCE_DONE complete=yes|no collect=yes|no classify=yes|no upload=yes|no
  SECONCE_STOP reason=<code>   (configuration stop before any request, e.g. RAW_REPO_NOT_PRIVATE, RAW_PREFLIGHT_MISSING)
Exit: 0 ran to the end (complete or partial: the files say which); 2 configuration stop; 1 unexpected or upload failure
(`done`: 1 when not complete).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import errno  # noqa: E402
import gzip  # noqa: E402
import hashlib  # noqa: E402
import http.client  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import time  # noqa: E402
import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402
import zipfile  # noqa: E402
import zlib  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fv3_pit_ticker_measure as pit  # noqa: E402  (User-Agent rule, Stop / FetchError, form.idx reading)
import raw_store_release  # noqa: E402  (the approved GitHub transport: no redirects, token from RAW_REPO_TOKEN only)

# ---- the run ---------------------------------------------------------------------------------------------------------
PUBLIC_REPO = 'kco994553-star/Investment-System1'
RUN_BRANCH = 'claude/sec-once-collect-run'
RUN_REF = 'refs/heads/' + RUN_BRANCH
RAW_REPO = 'kco994553-star/investment-system1-raw'
TAG_PREFIX = 'sec-once-v1-'
_TAG = re.compile(r'sec-once-v1-[1-9][0-9]{0,19}')
_RUN_ID = re.compile(r'[1-9][0-9]{0,19}')

# ---- the plan (fixed; changing it needs a new owner approval) ----------------------------------------------------------
INDEX_YEARS = tuple(range(2014, 2027))       # 2014 QTR1 .. 2026 QTR4 (the last quarter as of the run day)
INDEX_FILES = ('form', 'company')
FSDS_FIRST, FSDS_LAST = (2014, 1), (2026, 3)
BULK = (('companyfacts.zip', 'https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip'),
        ('submissions.zip', 'https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip'))
ALLOWED_SEC_URLS = tuple(re.compile(p) for p in (
    r'https://www\.sec\.gov/Archives/edgar/daily-index/xbrl/companyfacts\.zip',
    r'https://www\.sec\.gov/Archives/edgar/daily-index/bulkdata/submissions\.zip',
    r'https://www\.sec\.gov/Archives/edgar/full-index/20[0-9]{2}/QTR[1-4]/(?:form|company)\.idx',
    r'https://www\.sec\.gov/files/dera/data/financial-statement-data-sets/20[0-9]{2}q[1-4]\.zip',
))

SLEEP_S = 0.15                 # fixed sleep before every request (also before each retry): <= 6.7 requests per second
MAX_RETRIES = 2
BACKOFF_S = (5.0, 20.0)
RETRY_AFTER_MAX_S = 60.0
TIMEOUT_S = 60                 # per socket operation
MAX_REQUESTS = 500             # every HTTP attempt counts (157 planned + retries + zip re-downloads)
WALL_CLOCK_S = 60 * 60
STOP_AFTER_403 = 5
STOP_AFTER_429 = 10
CHUNK = 1024 * 1024
CAPS = {'bulk': 4 * 1024 ** 3, 'index': 512 * 1024 ** 2, 'fsds': 1024 ** 3}   # body bytes per file
NEED_FREE_GB = 11              # GiB: about 8.1 GB (7.5 GiB) kept on the runner at the peak (plan section 4) + ~3.5 GiB
SPLIT_LIMIT = 2_000_000_000    # GitHub: each release asset must be under 2 GiB (2,147,483,648 bytes)
PART_BYTES = 1_900_000_000
ROWS_FILE = 'ticker-mismatch-rows.json'
PREFLIGHT_FILE = 'raw-preflight.json'
STOP_REASONS = ('NONE', 'REQUEST_CAP', 'WALL_CLOCK', 'HTTP403_REPEATED', 'HTTP429_REPEATED', 'LOCAL_DISK_FULL', 'LOCAL_IO',
                'UNEXPECTED')
INDEX_FORMS = (('f10k', b'10-K'), ('f10q', b'10-Q'), ('f8k', b'8-K'), ('f25', b'25'), ('f25nse', b'25-NSE'),
               ('f8a12b', b'8-A12B'), ('f1512b', b'15-12B'), ('f1512g', b'15-12G'), ('f1515d', b'15-15D'))
REQUEST_FIELDS = ('total', 'bulk', 'index', 'fsds', 'retries', 'redownloads', 'http403', 'http429', 'http5xx')
KINDS = ('bulk', 'index', 'fsds')

_DATA_ASSET = (r'(?:(?:companyfacts|submissions)\.zip|fsds-20[0-9]{2}q[1-4]\.zip'
               r'|full-index-20[0-9]{2}-QTR[1-4]-(?:form|company)\.idx\.gz|ticker-mismatch-rows\.json)'
               r'(?:\.part[0-9]{2}|\.parts\.json)?')
ASSET_NAME = re.compile(rf'(?:a[0-9]{{1,3}}-)?(?:{_DATA_ASSET})(?:\.sha256)?|sec-once-manifest-a[0-9]{{1,3}}\.json(?:\.sha256)?')
_HEX64 = re.compile(r'[0-9a-f]{64}')


class ConfigStop(Exception):
    """Configuration stop before any request: one fixed SECONCE_STOP line, exit 2."""


class LocalStop(pit.Stop):
    """A local disk fault (no space, I/O error) while writing a download: the run stops at once; SEC is not asked again."""

    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason if reason in STOP_REASONS else 'UNEXPECTED'


def _local_stop(exc):
    return LocalStop('LOCAL_DISK_FULL' if getattr(exc, 'errno', None) == errno.ENOSPC else 'LOCAL_IO')


# ---- plan --------------------------------------------------------------------------------------------------------------
def fsds_quarters():
    year, quarter, out = FSDS_FIRST[0], FSDS_FIRST[1], []
    while (year, quarter) <= FSDS_LAST:
        out.append((year, quarter))
        year, quarter = (year, quarter + 1) if quarter < 4 else (year + 1, 1)
    return out


def plan_items():
    """The fixed file list: dicts with key (local / asset file name), kind, url and store ('raw' or 'gzip')."""
    items = [{'key': name, 'kind': 'bulk', 'url': url, 'store': 'raw'} for name, url in BULK]
    for year in INDEX_YEARS:
        for quarter in (1, 2, 3, 4):
            for name in INDEX_FILES:
                items.append({'key': f'full-index-{year}-QTR{quarter}-{name}.idx.gz', 'kind': 'index', 'store': 'gzip',
                              'url': f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/{name}.idx'})
    for year, quarter in fsds_quarters():
        items.append({'key': f'fsds-{year}q{quarter}.zip', 'kind': 'fsds', 'store': 'raw',
                      'url': f'https://www.sec.gov/files/dera/data/financial-statement-data-sets/{year}q{quarter}.zip'})
    items[-1]['optional'] = True      # the newest quarter may not be published on the run day: a 404 is recorded, not a failure
    for item in items:
        checked_sec_url(item['url'])
        if not ASSET_NAME.fullmatch(item['key']):
            raise ValueError('ASSET_NAME_NOT_ALLOWED')
    return items


def checked_sec_url(url):
    """Exact allow-list: https on www.sec.gov, one of four path shapes, no query, no userinfo or port."""
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
        raise ValueError('URL_NOT_ALLOWED')
    parts = urllib.parse.urlsplit(url)
    if parts.netloc != 'www.sec.gov' or parts.query or parts.fragment or not any(p.fullmatch(url) for p in ALLOWED_SEC_URLS):
        raise ValueError('URL_NOT_ALLOWED')
    return url


def plan_lines(free_bytes):
    items = plan_items()
    count = Counter(item['kind'] for item in items)
    free_gb = int(free_bytes // 1024 ** 3) if isinstance(free_bytes, int) and free_bytes >= 0 else 0
    first, last = fsds_quarters()[0], fsds_quarters()[-1]
    return [f'SECONCE_PLAN bulk={count["bulk"]} index_files={count["index"]} index_years={INDEX_YEARS[0]}-{INDEX_YEARS[-1]} '
            f'fsds_files={count["fsds"]} fsds_quarters={first[0]}q{first[1]}-{last[0]}q{last[1]} '
            f'sec_requests_planned={len(items)} max_requests={MAX_REQUESTS} wall_clock_s={WALL_CLOCK_S} pace_s={SLEEP_S}',
            f'SECONCE_DISK free_gb={free_gb} need_gb={NEED_FREE_GB} ok={"yes" if free_gb >= NEED_FREE_GB else "no"}']


# ---- helpers -----------------------------------------------------------------------------------------------------------
def code_token(value):
    return value if isinstance(value, str) and pit._CODE_TOKEN.fullmatch(value) else 'OTHER'


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b''):
            digest.update(chunk)
    return digest.hexdigest()


def source_digest(path, store):
    """(bytes, sha256) of the SEC body: the file itself, or the decompressed bytes of a stored .gz."""
    digest, size = hashlib.sha256(), 0
    opener = gzip.open if store == 'gzip' else open
    with opener(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b''):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def sidecar_text(sha, name):
    return f'{sha}  {name}\n'


def parse_sidecar(body, name):
    """The sha256 of a `<sha>  <name>` sidecar, or None."""
    try:
        text = body.decode('ascii')
    except (UnicodeDecodeError, AttributeError):
        return None
    match = re.fullmatch(r'([0-9a-f]{64})  (\S+)\n', text)
    return match.group(1) if match and match.group(2) == name else None


def base_name(asset):
    """Asset name without the a<attempt>- prefix used when an earlier attempt left an unverified asset of that name."""
    return re.sub(r'^a[0-9]{1,3}-', '', asset)


def run_context(environ, *, need_run_id=True):
    """(run_id, attempt) of the approved run; anything else is a configuration stop (no request is made)."""
    if environ.get('GITHUB_REPOSITORY') != PUBLIC_REPO or environ.get('GITHUB_REF') != RUN_REF:
        raise ConfigStop('NOT_THE_RUN_BRANCH')
    run_id = environ.get('GITHUB_RUN_ID') or ''
    if need_run_id and not _RUN_ID.fullmatch(run_id):
        raise ConfigStop('RUN_ID_INVALID')
    attempt = environ.get('GITHUB_RUN_ATTEMPT') or '1'
    if not re.fullmatch(r'[1-9][0-9]{0,2}', attempt):
        raise ConfigStop('RUN_ATTEMPT_INVALID')
    return run_id, int(attempt)


def release_tag(run_id):
    tag = TAG_PREFIX + str(run_id)
    if not _TAG.fullmatch(tag):
        raise ConfigStop('TAG_INVALID')
    return tag


def require_preflight(work, environ):
    """This attempt's raw-repository preflight marker (written by resume-check after the private check), or a stop."""
    run_id, attempt = run_context(environ)
    data = read_json(Path(work) / PREFLIGHT_FILE)
    if not (isinstance(data, dict) and data.get('repository') == RAW_REPO and data.get('private') is True
            and data.get('visibility') == 'private' and data.get('run_id') == run_id and data.get('attempt') == attempt):
        raise ConfigStop('RAW_PREFLIGHT_MISSING')
    return run_id, attempt


def write_json(path, payload):
    tmp = Path(str(path) + '.tmp')
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def files_dir(work):
    path = Path(work) / 'files'
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---- SEC download --------------------------------------------------------------------------------------------------------
class Truncated(Exception):
    """Body shorter than Content-Length, or a gzip stream without its end: retried like a network error."""


class Downloader:
    """One request at a time, a fixed sleep before each, bounded retries; streams each file to disk while hashing."""

    def __init__(self, user_agent, *, opener=None, sleep=time.sleep, clock=time.monotonic):
        self._agent = user_agent
        self._opener = opener if opener is not None else pit.build_opener()
        self._sleep, self._clock = sleep, clock
        self._start = clock()
        self._refused_in_a_row = 0
        self.counts = Counter()

    def elapsed(self):
        return self._clock() - self._start

    def _deadline(self):
        if self.elapsed() >= WALL_CLOCK_S:
            raise pit.Stop('WALL_CLOCK')

    def download(self, item, dest):
        """Fetch one plan item into `dest` (written as dest.part, renamed at the end). Returns the file record."""
        url = checked_sec_url(item['url'])
        kind = item['kind']
        for attempt in range(MAX_RETRIES + 1):
            if self.counts['total'] >= MAX_REQUESTS:
                raise pit.Stop('REQUEST_CAP')
            self._deadline()
            self._sleep(SLEEP_S)
            self.counts['total'] += 1
            self.counts[kind] += 1
            wait = None
            try:
                encoding = 'gzip' if item['store'] == 'gzip' else 'identity'
                request = urllib.request.Request(url, headers={'User-Agent': self._agent, 'Accept-Encoding': encoding})
                with self._opener.open(request, timeout=TIMEOUT_S) as response:
                    self._refused_in_a_row = 0
                    record = self._stream(response, item, dest)
                record['last_modified'] = _header(response, 'Last-Modified')
                return record
            except urllib.error.HTTPError as exc:
                status = exc.code if type(exc.code) is int else 0
                retry_after = exc.headers.get('Retry-After') if exc.headers is not None else None
                exc.close()
                self._refused_in_a_row = self._refused_in_a_row + 1 if status == 403 else 0
                if status == 403:
                    self.counts['http403'] += 1
                elif status == 429:
                    self.counts['http429'] += 1
                elif 500 <= status <= 599:
                    self.counts['http5xx'] += 1
                if self._refused_in_a_row >= STOP_AFTER_403:
                    raise pit.Stop('HTTP403_REPEATED') from None
                if self.counts['http429'] >= STOP_AFTER_429:
                    raise pit.Stop('HTTP429_REPEATED') from None
                if not (status == 429 or 500 <= status <= 599) or attempt == MAX_RETRIES:
                    raise pit.FetchError(f'HTTP{status}' if 100 <= status <= 599 else 'HTTP_OTHER') from None
                wait = BACKOFF_S[attempt]
                if status == 429 and isinstance(retry_after, str) and retry_after.strip().isdigit():
                    wait = max(wait, min(float(retry_after.strip()), RETRY_AFTER_MAX_S))
            except Truncated:
                if attempt == MAX_RETRIES:
                    raise pit.FetchError('TRUNCATED') from None
                wait = BACKOFF_S[attempt]
            except pit.FetchError:
                raise
            except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
                # network faults only: every local write is wrapped in _stream and raises LocalStop (never retried)
                if attempt == MAX_RETRIES:
                    raise pit.FetchError(type(exc).__name__) from None
                wait = BACKOFF_S[attempt]
            finally:
                try:
                    Path(str(dest) + '.part').unlink(missing_ok=True)
                except OSError:
                    pass
            self.counts['retries'] += 1
            self._sleep(wait)
        raise pit.FetchError('RETRIES_EXHAUSTED')  # not reached

    def _stream(self, response, item, dest):
        encoding = (_header(response, 'Content-Encoding') or 'identity').strip().lower()
        if encoding not in ('identity', 'gzip', 'x-gzip') or (encoding != 'identity' and item['store'] != 'gzip'):
            raise pit.FetchError('ENCODING_NOT_SUPPORTED')
        length = _header(response, 'Content-Length')
        length = int(length) if isinstance(length, str) and length.strip().isdigit() else None
        cap = CAPS[item['kind']]
        if length is not None and length > cap:
            raise pit.FetchError('SIZE_CAP')
        inflate = zlib.decompressobj(31) if encoding != 'identity' else None
        part = Path(str(dest) + '.part')
        digest, wire, body = hashlib.sha256(), 0, 0
        raw = sink = None
        finished = False
        try:
            try:      # local file: any OSError here is a disk fault, not a network one
                raw = open(part, 'wb')
                sink = (gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=6)
                        if item['store'] == 'gzip' else raw)
            except OSError as exc:
                raise _local_stop(exc) from None
            while True:
                self._deadline()
                chunk = response.read(CHUNK)          # network: an OSError here is retried by download()
                if not chunk:
                    break
                wire += len(chunk)
                self.counts['wire_bytes'] += len(chunk)
                if wire > cap:
                    raise pit.FetchError('SIZE_CAP')
                for piece in ((chunk,) if inflate is None else _inflate(inflate, chunk)):
                    body += len(piece)
                    self.counts['body_bytes'] += len(piece)
                    if body > cap:
                        raise pit.FetchError('SIZE_CAP')
                    digest.update(piece)
                    _write_local(sink, piece)
            if inflate is not None:
                try:
                    tail = inflate.flush()
                except zlib.error:
                    raise pit.FetchError('BAD_GZIP') from None
                if tail:
                    body += len(tail)
                    self.counts['body_bytes'] += len(tail)
                    digest.update(tail)
                    _write_local(sink, tail)
                if not inflate.eof:
                    raise Truncated()
            try:
                if sink is not raw:
                    sink.close()
                raw.close()
            except OSError as exc:
                raise _local_stop(exc) from None
            finished = True
        finally:
            if not finished:
                for handle in (sink, raw):
                    try:
                        if handle is not None:
                            handle.close()
                    except (OSError, ValueError):
                        pass
        if length is not None and wire != length:
            raise Truncated()
        try:
            os.replace(part, dest)
            stored_bytes = dest.stat().st_size
            stored_sha = sha256_file(dest) if item['store'] == 'gzip' else digest.hexdigest()
        except OSError as exc:
            raise _local_stop(exc) from None
        return {'key': item['key'], 'kind': item['kind'], 'source_url': item['url'], 'store': item['store'],
                'source_bytes': body, 'source_sha256': digest.hexdigest(), 'stored_bytes': stored_bytes,
                'stored_sha256': stored_sha, 'wire_bytes': wire, 'fetched_at': utc_now(), 'resumed': False}


def _write_local(sink, data):
    try:
        sink.write(data)
    except OSError as exc:
        raise _local_stop(exc) from None


def _header(response, name):
    headers = getattr(response, 'headers', None)
    value = headers.get(name) if headers is not None else None
    return value if isinstance(value, str) else None


def _inflate(inflate, raw):
    data = raw
    try:
        while data:
            piece = inflate.decompress(data, 4 * CHUNK)
            data = inflate.unconsumed_tail
            if piece:
                yield piece
    except zlib.error:
        raise pit.FetchError('BAD_GZIP') from None


# ---- checks on the files ---------------------------------------------------------------------------------------------------
def zip_check(path):
    """(code, entries, overflow_pages): central directory readable and every member's CRC correct."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            bad = archive.testzip()
    except (zipfile.BadZipFile, OSError, EOFError, zlib.error, NotImplementedError, RuntimeError):
        return 'BAD_ZIP', None, None
    overflow = sum(1 for n in names if re.fullmatch(r'CIK[0-9]{10}-submissions-[0-9]{3}\.json', n))
    return ('CRC_FAILED' if bad is not None else 'OK'), len(names), overflow


def index_form_counts(path):
    """{field: count} of one stored form.idx(.gz): data rows and the delisting / registration / report form types."""
    wanted = dict((form, key) for key, form in INDEX_FORMS)
    counts, header_done = Counter(), False
    with gzip.open(path, 'rb') as handle:
        for line in pit.iter_lines(iter(lambda: handle.read(CHUNK), b'')):
            if not header_done:
                header_done = line.startswith(b'-----')
                continue
            parts = line.rsplit(None, 2)
            if len(parts) != 3 or not pit._IDX_PATH.fullmatch(parts[2]) or not pit._IDX_DAY.fullmatch(parts[1]):
                continue
            counts['rows'] += 1
            form = parts[0].split(b'  ', 1)[0].strip()
            if form in wanted:
                counts[wanted[form]] += 1
    if not header_done:
        raise ValueError('BAD_FORM_IDX')
    return counts


# ---- collect -------------------------------------------------------------------------------------------------------------
def verified_resume(work):
    """{file key: (sha256, asset name)} the resume check verified in this run's own release (empty on attempt 1)."""
    data = read_json(Path(work) / 'resume.json')
    rows = data.get('verified') if isinstance(data, dict) else None
    out = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and all(isinstance(row.get(k), str) for k in ('key', 'sha256', 'asset')) \
                and ASSET_NAME.fullmatch(row['key']) and ASSET_NAME.fullmatch(row['asset']) and _HEX64.fullmatch(row['sha256']):
            out[row['key']] = (row['sha256'], row['asset'])
    return out


def collect(work, environ, *, opener=None, sleep=time.sleep, clock=time.monotonic, out=print):
    agent = environ.get('SEC_USER_AGENT') or ''
    if not agent.strip():
        raise ConfigStop('SEC_USER_AGENT_MISSING')
    if not pit.valid_user_agent(agent):
        raise ConfigStop('SEC_USER_AGENT_INVALID')
    require_preflight(work, environ)        # the raw repository was found private on THIS attempt, before any SEC request
    folder = files_dir(work)
    resumed = verified_resume(work)
    downloader = Downloader(agent, opener=opener, sleep=sleep, clock=clock)
    records, failed, optional_missing, errors, stopped = [], {}, {}, Counter(), 'NONE'
    files = Counter()
    zips = {}
    items = plan_items()
    try:
        for item in items:
            dest = folder / item['key']
            if item['key'] in resumed and dest.is_file() and sha256_file(dest) == resumed[item['key']][0]:
                size, sha = source_digest(dest, item['store'])
                record = {'key': item['key'], 'kind': item['kind'], 'source_url': item['url'], 'store': item['store'],
                          'source_bytes': size, 'source_sha256': sha, 'stored_bytes': dest.stat().st_size,
                          'stored_sha256': resumed[item['key']][0], 'wire_bytes': 0, 'fetched_at': None,
                          'last_modified': None, 'resumed': True}
                if item['key'].endswith('.zip'):
                    code, entries, overflow = zip_check(dest)
                    record.update(zip_check=code, zip_entries=entries,
                                  zip_detail=[entries, overflow if item['key'] == 'submissions.zip' else None])
                records.append(record)
                files[item['kind'], 'resumed'] += 1
                files[item['kind'], 'mb'] += dest.stat().st_size
            else:
                try:
                    record = downloader.download(item, dest)
                    if item['key'].endswith('.zip'):
                        record = _checked_zip(downloader, item, dest, record)
                except pit.FetchError as exc:
                    try:
                        dest.unlink(missing_ok=True)
                    except OSError as error:
                        raise _local_stop(error) from None
                    if item.get('optional') and exc.code == 'HTTP404':
                        optional_missing[item['key']] = 'HTTP404'
                        files[item['kind'], 'optional_missing'] += 1
                        continue
                    failed[item['key']] = code_token(exc.code)
                    errors[item['kind'].upper() + '_' + code_token(exc.code)] += 1
                    files[item['kind'], 'failed'] += 1
                    continue
                records.append(record)
                files[item['kind'], 'ok'] += 1
                files[item['kind'], 'mb'] += record['stored_bytes']
            if item['key'].endswith('.zip'):
                zips[item['key']] = records[-1]['zip_check']
                zips[item['key'] + ':detail'] = records[-1]['zip_detail']
    except pit.Stop as stop:
        stopped = stop.reason
    complete = stopped == 'NONE' and not failed and len(records) + len(optional_missing) == len(items)
    manifest = {'schema': 'sec-once-collect/1', 'plan': plan_summary(), 'records': records, 'failed': failed,
                'optional_missing': optional_missing, 'stopped': stopped, 'complete': complete, 'finished_at': utc_now()}
    write_json(Path(work) / 'collect-manifest.json', manifest)
    planned = Counter(item['kind'] for item in items)
    for kind in KINDS:
        out(f'SECONCE_FILES kind={kind} planned={planned[kind]} ok={files[kind, "ok"]} resumed={files[kind, "resumed"]} '
            f'failed={files[kind, "failed"]} optional_missing={files[kind, "optional_missing"]} '
            f'mb={files[kind, "mb"] / 1e6:.1f}')
    for key, label in (('companyfacts.zip', 'companyfacts'), ('submissions.zip', 'submissions')):
        detail = zips.get(key + ':detail') or [None, None]
        entries = 'NA' if detail[0] is None else int(detail[0])
        overflow = 'NA' if detail[1] is None else int(detail[1])
        out(f'SECONCE_ZIP name={label} entries={entries} overflow_pages={overflow} check={zips.get(key, "MISSING")}')
    fsds = [code for key, code in zips.items() if key.startswith('fsds-') and not key.endswith(':detail')]
    out(f'SECONCE_ZIP name=fsds files={len(fsds)} ok={fsds.count("OK")} bad={len(fsds) - fsds.count("OK")}')
    for line in index_lines(folder, errors):
        out(line)
    out(format_errors(errors))
    out(format_requests(downloader.counts, downloader.elapsed(), stopped, complete))
    return 0


def _checked_zip(downloader, item, dest, record):
    """Zip CRC check; one fresh download when it fails (a bulk zip can be rebuilt while it is read)."""
    code, entries, overflow = zip_check(dest)
    if code != 'OK':
        downloader.counts['redownloads'] += 1
        dest.unlink(missing_ok=True)
        record = downloader.download(item, dest)
        code, entries, overflow = zip_check(dest)
        if code != 'OK':
            raise pit.FetchError(code)
    record['zip_check'] = code
    record['zip_entries'] = entries
    record['zip_detail'] = [entries, overflow if item['key'] == 'submissions.zip' else None]
    return record


def index_lines(folder, errors):
    lines = []
    for year in INDEX_YEARS:
        counts, quarters = Counter(), 0
        for quarter in (1, 2, 3, 4):
            path = folder / f'full-index-{year}-QTR{quarter}-form.idx.gz'
            if not path.is_file():
                continue
            try:
                counts.update(index_form_counts(path))
                quarters += 1
            except (OSError, ValueError, EOFError, zlib.error):
                errors['INDEX_PARSE'] += 1
        if quarters:
            lines.append(f'SECONCE_INDEX year={year} quarters={quarters} rows={counts["rows"]} '
                         + ' '.join(f'{key}={counts[key]}' for key, _ in INDEX_FORMS))
    return lines


def plan_summary():
    first, last = fsds_quarters()[0], fsds_quarters()[-1]
    return {'index_years': [INDEX_YEARS[0], INDEX_YEARS[-1]], 'index_files': list(INDEX_FILES),
            'fsds_quarters': [f'{first[0]}q{first[1]}', f'{last[0]}q{last[1]}'], 'bulk': [name for name, _ in BULK],
            'files_planned': len(plan_items())}


def format_errors(errors):
    merged = Counter()
    for code, n in errors.items():
        merged[code_token(code)] += int(n)
    return 'SECONCE_ERRORS codes=' + (','.join(f'{c}:{merged[c]}' for c in sorted(merged) if merged[c]) or '-')


def format_requests(counts, elapsed_s, stopped, complete):
    stopped = stopped if stopped in STOP_REASONS else 'UNEXPECTED'
    parts = [f'{k}={int(counts.get(k, 0))}' for k in REQUEST_FIELDS]
    parts += [f'mb_wire={counts.get("wire_bytes", 0) / 1e6:.1f}', f'mb_body={counts.get("body_bytes", 0) / 1e6:.1f}',
              f'elapsed_s={int(elapsed_s)}', f'stopped={stopped}', f'complete={"yes" if complete else "no"}']
    return 'SECONCE_REQUESTS ' + ' '.join(parts)


# ---- the private release (create-only, name fixed in code) ------------------------------------------------------------
class ReleaseRefused(Exception):
    """A GitHub call outside the allow-list or an unexpected answer; `code` is a fixed token."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code_token(code)


class _RangeReader:
    """File-like view of bytes [start, start + length) of a file, so a part is streamed, never held in memory."""

    def __init__(self, path, start, length):
        self._handle = open(path, 'rb')
        self._handle.seek(start)
        self._left = length

    def read(self, size=-1):
        if self._left <= 0:
            return b''
        size = self._left if size is None or size < 0 else min(size, self._left)
        data = self._handle.read(size)
        self._left -= len(data)
        return data

    def close(self):
        self._handle.close()


class ReleaseClient:
    """The only GitHub calls this tool makes. Every call goes through `check` first."""

    def __init__(self, tag, *, call=None, open_url=None):
        if not _TAG.fullmatch(tag):
            raise ReleaseRefused('TAG_INVALID')
        self.tag = tag
        self._call = call or raw_store_release.http
        self._open = open_url or urllib.request.build_opener(raw_store_release._NoRedirect()).open
        self.release_id = None
        self.asset_ids = set()

    def check(self, method, url):
        api, uploads, repo = raw_store_release.API, raw_store_release.UPLOADS, RAW_REPO
        if method == 'GET' and url in (f'{api}/repos/{repo}', f'{api}/repos/{repo}/releases/tags/{self.tag}'):
            return
        if method == 'POST' and url == f'{api}/repos/{repo}/releases' and self.release_id is None:
            return
        if self.release_id is not None:
            prefix = f'{uploads}/repos/{repo}/releases/{self.release_id}/assets?name='
            if method == 'POST' and url.startswith(prefix) and ASSET_NAME.fullmatch(urllib.parse.unquote(url[len(prefix):])) \
                    and urllib.parse.quote(urllib.parse.unquote(url[len(prefix):])) == url[len(prefix):]:
                return
            match = re.fullmatch(rf'{re.escape(api)}/repos/{re.escape(repo)}/releases/assets/([1-9][0-9]{{0,19}})', url)
            if method == 'GET' and match and int(match.group(1)) in self.asset_ids:
                return
        raise ReleaseRefused('GITHUB_CALL_NOT_ALLOWED')

    def _json(self, method, url, **kwargs):
        self.check(method, url)
        status, _, body = self._call(method, url, **kwargs)
        try:
            payload = json.loads(body) if body else None
        except ValueError:
            payload = None
        return status, payload

    def _adopt(self, release):
        if not isinstance(release, dict) or release.get('tag_name') != self.tag or type(release.get('id')) is not int \
                or release['id'] <= 0:
            raise ReleaseRefused('RELEASE_INVALID')
        self.release_id = release['id']
        assets = {}
        for asset in release.get('assets') or []:
            if isinstance(asset, dict) and isinstance(asset.get('name'), str) and ASSET_NAME.fullmatch(asset['name']) \
                    and type(asset.get('id')) is int and asset['id'] > 0:
                assets[asset['name']] = asset
                self.asset_ids.add(asset['id'])
        return assets

    def check_private(self):
        """The raw repository's own metadata must say: this exact repository, private. Anything else stops the run
        (ConfigStop) before any SEC request (resume-check) and before the release is created (upload)."""
        try:
            status, payload = self._json('GET', f'{raw_store_release.API}/repos/{RAW_REPO}')
        except (OSError, urllib.error.URLError, http.client.HTTPException):
            raise ConfigStop('RAW_REPO_UNREACHABLE') from None
        if status != 200:
            raise ConfigStop(f'RAW_REPO_HTTP{int(status)}' if type(status) is int and 100 <= status <= 599
                             else 'RAW_REPO_UNREACHABLE')
        if not isinstance(payload, dict) or payload.get('full_name') != RAW_REPO:
            raise ConfigStop('RAW_REPO_MISMATCH')
        if payload.get('private') is not True or payload.get('visibility') != 'private':
            raise ConfigStop('RAW_REPO_NOT_PRIVATE')
        return True

    def read_own(self):
        """This run's own release by its tag: (assets by name) or None when it does not exist."""
        status, payload = self._json('GET', f'{raw_store_release.API}/repos/{RAW_REPO}/releases/tags/{self.tag}')
        if status == 404:
            return None
        if status != 200:
            raise ReleaseRefused(f'RELEASE_READ_HTTP{int(status)}' if type(status) is int else 'RELEASE_READ_FAILED')
        return self._adopt(payload)

    def create(self):
        body = json.dumps({'tag_name': self.tag, 'name': self.tag, 'draft': False, 'prerelease': False,
                           'make_latest': 'false',
                           'body': 'SEC one-time collection (private; public SEC files and derived counts, no prices). '
                                   'See sec-once-manifest-a<attempt>.json. Plan: '
                                   'implementation/docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md.'}).encode()
        status, payload = self._json('POST', f'{raw_store_release.API}/repos/{RAW_REPO}/releases', data=body,
                                     headers={'Content-Type': 'application/json'})
        if status == 422:
            raise ReleaseRefused('RELEASE_EXISTS')
        if status != 201:
            raise ReleaseRefused(f'RELEASE_CREATE_HTTP{int(status)}' if type(status) is int else 'RELEASE_CREATE_FAILED')
        return self._adopt(payload)

    def upload(self, name, source, size, content_type):
        """Upload one asset from a file path, a (path, start, length) range or bytes. Returns the asset record."""
        url = f'{raw_store_release.UPLOADS}/repos/{RAW_REPO}/releases/{self.release_id}/assets?name={urllib.parse.quote(name)}'
        self.check('POST', url)
        if isinstance(source, bytes):
            data, handle = source, None
        elif isinstance(source, tuple):
            handle = data = _RangeReader(*source)
        else:
            handle = data = open(source, 'rb')
        try:
            status, _, body = self._call('POST', url, data=data,
                                         headers={'Content-Type': content_type, 'Content-Length': str(size)})
        finally:
            if handle is not None:
                handle.close()
        try:
            asset = json.loads(body) if status == 201 else None
        except ValueError:
            asset = None
        if not isinstance(asset, dict) or asset.get('name') != name or asset.get('size') != size \
                or asset.get('state', 'uploaded') != 'uploaded' or type(asset.get('id')) is not int:
            raise ReleaseRefused(f'UPLOAD_HTTP{int(status)}' if type(status) is int and status != 201 else 'UPLOAD_INVALID')
        self.asset_ids.add(asset['id'])
        return asset

    def stream(self, asset_id, sink):
        """Download one asset of this release, handing its bytes to `sink`; returns (bytes, sha256)."""
        url = f'{raw_store_release.API}/repos/{RAW_REPO}/releases/assets/{int(asset_id)}'
        self.check('GET', url)
        request = urllib.request.Request(url, headers={'Accept': 'application/octet-stream',
                                                       'Authorization': 'Bearer ' + raw_store_release._token(),
                                                       'X-GitHub-Api-Version': '2022-11-28'})
        try:
            response = self._open(request, timeout=600)
        except urllib.error.HTTPError as exc:
            location = exc.headers.get('Location') if exc.headers is not None and exc.code in (301, 302, 303, 307, 308) \
                else None
            exc.close()
            if not isinstance(location, str):
                raise ReleaseRefused(f'ASSET_HTTP{int(exc.code)}' if type(exc.code) is int else 'ASSET_FAILED') from None
            parts = urllib.parse.urlsplit(location)
            if parts.scheme != 'https' or not (parts.hostname or '').endswith('.githubusercontent.com') or parts.username:
                raise ReleaseRefused('ASSET_REDIRECT_INVALID') from None
            response = self._open(urllib.request.Request(location, headers={'Accept': 'application/octet-stream'}),
                                  timeout=600)
        digest, size = hashlib.sha256(), 0
        with response:
            for chunk in iter(lambda: response.read(CHUNK), b''):
                digest.update(chunk)
                size += len(chunk)
                sink(chunk)
        return size, digest.hexdigest()


def _token_present(environ):
    return bool(environ.get('RAW_REPO_TOKEN'))


def _attempt_of(name):
    """The attempt that uploaded an asset: the number of its a<n>- prefix, 1 for a plain name."""
    match = re.match(r'a([0-9]{1,3})-', name)
    return int(match.group(1)) if match else 1


def resume_check(work, environ, *, call=None, open_url=None, out=print):
    run_id, attempt = run_context(environ)
    tag = release_tag(run_id)
    Path(work, PREFLIGHT_FILE).unlink(missing_ok=True)
    if not _token_present(environ):
        raise ConfigStop('RAW_REPO_TOKEN_MISSING')
    client = ReleaseClient(tag, call=call, open_url=open_url)
    client.check_private()                  # every attempt, before anything else and before any SEC request
    write_json(Path(work) / PREFLIGHT_FILE, {'repository': RAW_REPO, 'private': True, 'visibility': 'private',
                                             'run_id': run_id, 'attempt': attempt, 'checked_at': utc_now()})
    out('SECONCE_PREFLIGHT raw_repo=private')
    resume = {'attempt': attempt, 'tag': tag, 'release': 'NOT_READ', 'verified': [], 'unverified': []}
    if attempt == 1:
        write_json(Path(work) / 'resume.json', resume)
        out('SECONCE_RESUME attempt=1 release=NOT_READ assets=0 verified=0 unverified=0')
        return 0
    folder = files_dir(work)
    assets = client.read_own()
    resume['release'] = 'ABSENT' if assets is None else 'PRESENT'
    data_assets = {} if assets is None else {n: a for n, a in assets.items() if not n.endswith('.sha256')
                                             and not n.startswith('sec-once-manifest-')
                                             and not re.fullmatch(r'.*\.part[0-9]{2}', n)}
    by_target = {}
    for name in data_assets:
        key = base_name(name)
        target = key[:-len('.parts.json')] if key.endswith('.parts.json') else key
        by_target.setdefault(target, []).append(name)
    for target in sorted(by_target):
        # newest attempt first (numeric: a10- after a2-); older copies are not read once a newer one verified
        for name in sorted(by_target[target], key=lambda n: (-_attempt_of(n), n)):
            try:
                if name.endswith('.parts.json'):
                    ok, sha = _resume_parts(client, assets, name, folder)
                else:
                    ok, sha = _resume_one(client, assets, name, folder / target)
            except (ReleaseRefused, OSError, ValueError, KeyError, TypeError, urllib.error.URLError,
                    http.client.HTTPException):
                ok, sha = False, None
            if ok:
                resume['verified'].append({'key': target, 'asset': name, 'sha256': sha})
                break
            resume['unverified'].append(name)
    write_json(Path(work) / 'resume.json', resume)
    out(f'SECONCE_RESUME attempt={attempt} release={resume["release"]} assets={len(data_assets)} '
        f'verified={len(resume["verified"])} unverified={len(resume["unverified"])}')
    return 0


def _sidecar(client, assets, name):
    side = assets.get(name + '.sha256')
    if side is None:
        return None
    chunks = []
    client.stream(side['id'], chunks.append)
    return parse_sidecar(b''.join(chunks), name)


def _resume_one(client, assets, name, dest):
    """Download one data asset to dest when its sidecar matches; (verified, sha256)."""
    expected = _sidecar(client, assets, name)
    if expected is None:
        return False, None
    tmp = Path(str(dest) + '.part')
    with open(tmp, 'wb') as handle:
        size, sha = client.stream(assets[name]['id'], handle.write)
    if sha != expected or size != assets[name].get('size'):
        tmp.unlink(missing_ok=True)
        return False, None
    os.replace(tmp, dest)
    return True, sha


def _resume_parts(client, assets, name, folder):
    """Verify index/part sizes and hashes before atomically accepting a reconstructed file."""
    expected = _sidecar(client, assets, name)
    if expected is None:
        return False, None
    chunks = []
    size, sha = client.stream(assets[name]['id'], chunks.append)
    body = b''.join(chunks)
    if size != len(body) or size != assets[name].get('size') or sha != expected or hashlib.sha256(body).hexdigest() != expected:
        return False, None
    index = json.loads(body)
    key = base_name(name)[:-len('.parts.json')]
    if (not isinstance(index, dict) or index.get('file') != key
            or type(index.get('bytes')) is not int or index['bytes'] <= 0
            or not isinstance(index.get('sha256'), str) or not _HEX64.fullmatch(index['sha256'])
            or not isinstance(index.get('parts'), list) or not index['parts']):
        return False, None
    prefix = name[:-len('.parts.json')]
    for number, part in enumerate(index['parts'], 1):
        if (not isinstance(part, dict) or part.get('name') != f'{prefix}.part{number:02d}'
                or not ASSET_NAME.fullmatch(part['name']) or part['name'] not in assets
                or type(part.get('bytes')) is not int or part['bytes'] <= 0
                or part['bytes'] != assets[part['name']].get('size')
                or not isinstance(part.get('sha256'), str) or not _HEX64.fullmatch(part['sha256'])):
            return False, None
    if sum(p['bytes'] for p in index['parts']) != index['bytes']:
        return False, None
    dest = folder / key
    tmp = Path(str(dest) + '.part')
    digest, total = hashlib.sha256(), 0
    try:
        with open(tmp, 'wb') as handle:
            for part in index['parts']:
                part_name = part['name']
                if _sidecar(client, assets, part_name) != part['sha256']:
                    return False, None

                def write(chunk):
                    handle.write(chunk)
                    digest.update(chunk)
                size, sha = client.stream(assets[part_name]['id'], write)
                if size != part['bytes'] or sha != part['sha256']:
                    return False, None
                total += size
        if total != index['bytes'] or tmp.stat().st_size != total or digest.hexdigest() != index['sha256']:
            return False, None
        os.replace(tmp, dest)
        return True, index['sha256']
    finally:
        tmp.unlink(missing_ok=True)


def upload(work, environ, *, call=None, open_url=None, out=print, verify_back=True):
    run_id, attempt = run_context(environ)
    tag = release_tag(run_id)
    if not _token_present(environ):
        raise ConfigStop('RAW_REPO_TOKEN_MISSING')
    collected = read_json(Path(work) / 'collect-manifest.json')
    if not isinstance(collected, dict) or not isinstance(collected.get('records'), list):
        raise ConfigStop('COLLECT_MANIFEST_MISSING')
    folder = files_dir(work)
    resumed = verified_resume(work)
    client = ReleaseClient(tag, call=call, open_url=open_url)
    client.check_private()                  # again, right before the release is created or read
    created, uploaded, present, failed, mb = False, [], 0, Counter(), 0
    manifest_ok, verify = False, Counter()
    try:
        existing = client.read_own() if attempt > 1 else None
        if existing is None:
            existing = client.create()
            created = True
        entries = []
        files = [(r, folder / r['key']) for r in collected['records'] if isinstance(r, dict) and ASSET_NAME.fullmatch(r['key'])]
        rows = folder / ROWS_FILE
        if rows.is_file():
            files.append(({'key': ROWS_FILE, 'kind': 'derived', 'store': 'raw', 'stored_bytes': rows.stat().st_size,
                           'stored_sha256': sha256_file(rows)}, rows))
        for record, path in files:
            entry = dict(record)
            try:
                if not path.is_file() or path.stat().st_size != record['stored_bytes'] or \
                        sha256_file(path) != record['stored_sha256']:
                    raise ReleaseRefused('LOCAL_FILE_CHANGED')
                if record['key'] in resumed and resumed[record['key']][0] == record['stored_sha256']:
                    entry['assets'] = [{'name': resumed[record['key']][1], 'bytes': record['stored_bytes'],
                                        'sha256': record['stored_sha256'], 'status': 'PRESENT_VERIFIED'}]
                    present += 1
                else:
                    entry['assets'] = _upload_file(client, existing, record['key'], path, attempt, uploaded)
                    mb += record['stored_bytes']
            except (ReleaseRefused, OSError, urllib.error.URLError, http.client.HTTPException) as exc:
                code = exc.code if isinstance(exc, ReleaseRefused) else type(exc).__name__
                entry['upload_failed'] = code_token(code)
                failed[code_token(code)] += 1
            entries.append(entry)
        if verify_back:                     # every data asset of this attempt is read back BEFORE the manifest is written
            _verify(client, uploaded, verify)
        rows_data = read_json(rows) if rows.is_file() else None
        rows_complete = isinstance(rows_data, dict) and rows_data.get('complete') is True
        manifest = {'schema': 'sec-once-manifest/1', 'release': tag, 'repository': RAW_REPO,
                    'run': {'run_id': run_id, 'attempt': attempt, 'commit': environ.get('GITHUB_SHA'),
                            'workflow': '.github/workflows/sec-once-collect.yml', 'public_repository': PUBLIC_REPO},
                    'plan': collected.get('plan'), 'collect_complete': bool(collected.get('complete')),
                    'collect_stopped': collected.get('stopped'), 'collect_failed': collected.get('failed'),
                    'collect_optional_missing': collected.get('optional_missing'),
                    'files': entries, 'upload_failed': sum(failed.values()),
                    'classification_complete': rows_complete,
                    'verify': {'checked': bool(verify_back), 'ok': verify['ok'], 'bad': verify['bad']},
                    'complete': (bool(collected.get('complete')) and rows_complete and not failed and bool(verify_back)
                                 and verify['bad'] == 0),
                    'complete_rule': 'collection complete, classification complete, every upload done and read back '
                                     'with a matching sha256; the run is finished only when the highest-attempt '
                                     'manifest says complete and the run log ends with SECONCE_DONE complete=yes',
                    'rights': 'SEC EDGAR public data (sec.gov privacy and dissemination statement); kept private together '
                              'with derived research results; no prices, no KIS data',
                    'reuse': 'owner, Main and Codex; EXP-STOCK-INDICATOR-DECILES-v1 and forward validation v3 point-in-time '
                             'inputs; anything else needs a new owner decision',
                    'written_at': utc_now()}
        body = (json.dumps(manifest, indent=1, sort_keys=True) + '\n').encode()
        name = f'sec-once-manifest-a{attempt}.json'
        if name in existing or name + '.sha256' in existing:
            raise ReleaseRefused('MANIFEST_EXISTS')
        sha = hashlib.sha256(body).hexdigest()
        last = [dict(client.upload(name, body, len(body), 'application/json'), _sha256=sha)]
        side = sidecar_text(sha, name).encode()
        last.append(dict(client.upload(name + '.sha256', side, len(side), 'text/plain'),
                         _sha256=hashlib.sha256(side).hexdigest()))
        uploaded.extend(last)
        manifest_ok = True
        mb += len(body)
        if verify_back:
            _verify(client, last, verify)
    except ReleaseRefused as exc:
        failed[exc.code] += 1
    except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
        failed[code_token(type(exc).__name__)] += 1
    data_uploaded = sum(1 for a in uploaded if not a['name'].endswith('.sha256'))
    status = {'created': created, 'uploaded': data_uploaded, 'present': present, 'failed': dict(failed),
              'manifest': manifest_ok, 'verify_ok': verify['ok'], 'verify_bad': verify['bad'],
              'complete': manifest_ok and not failed and verify['bad'] == 0}
    write_json(Path(work) / 'upload-status.json', status)
    out(f'SECONCE_RELEASE created={"yes" if created else "no"} assets_uploaded={data_uploaded} assets_present={present} '
        f'assets_failed={sum(failed.values())} mb={mb / 1e6:.1f} manifest={"OK" if manifest_ok else "FAILED"}')
    out(f'SECONCE_VERIFY assets={verify["ok"] + verify["bad"]} ok={verify["ok"]} bad={verify["bad"]}')
    out(format_errors(failed))
    return 0 if status['complete'] else 1


def _verify(client, assets, verify):
    """Download each asset back and count it ok when its size and sha256 match what was uploaded."""
    for asset in assets:
        try:
            size, sha = client.stream(asset['id'], lambda chunk: None)
            verify['ok' if size == asset['size'] and sha == asset.get('_sha256') else 'bad'] += 1
        except (ReleaseRefused, OSError, urllib.error.URLError, http.client.HTTPException, KeyError):
            verify['bad'] += 1


def name_taken(name, existing):
    """True when the release already has `name` or any asset an upload under `name` would create (its .sha256
    sidecar, its .partNN parts and their sidecars, its .parts.json index): GitHub refuses a duplicate asset name and
    this tool never deletes one."""
    return any(asset == name or asset.startswith(name + '.') for asset in existing)


def _upload_file(client, existing, key, path, attempt, uploaded):
    """Upload one local file (split when needed) with sha256 sidecars; returns the manifest asset entries."""
    size = path.stat().st_size
    sha = sha256_file(path)
    name = key if not name_taken(key, existing) else f'a{attempt}-{key}'
    if name_taken(name, existing):
        raise ReleaseRefused('ASSET_EXISTS')
    content = 'application/zip' if key.endswith('.zip') else 'application/gzip' if key.endswith('.gz') \
        else 'application/json'
    entries = []
    if size <= SPLIT_LIMIT:
        uploaded.append(dict(client.upload(name, path, size, content), _sha256=sha))
        side = sidecar_text(sha, name).encode()
        uploaded.append(dict(client.upload(name + '.sha256', side, len(side), 'text/plain'),
                             _sha256=hashlib.sha256(side).hexdigest()))
        return [{'name': name, 'bytes': size, 'sha256': sha, 'status': 'UPLOADED'}]
    parts = []
    for number, start in enumerate(range(0, size, PART_BYTES), 1):
        length = min(PART_BYTES, size - start)
        part_name = f'{name}.part{number:02d}'
        digest = hashlib.sha256()
        reader = _RangeReader(path, start, length)
        try:
            for chunk in iter(lambda: reader.read(CHUNK), b''):
                digest.update(chunk)
        finally:
            reader.close()
        part_sha = digest.hexdigest()
        uploaded.append(dict(client.upload(part_name, (path, start, length), length, 'application/octet-stream'),
                             _sha256=part_sha))
        side = sidecar_text(part_sha, part_name).encode()
        uploaded.append(dict(client.upload(part_name + '.sha256', side, len(side), 'text/plain'),
                             _sha256=hashlib.sha256(side).hexdigest()))
        parts.append({'name': part_name, 'bytes': length, 'sha256': part_sha})
    index = (json.dumps({'file': key, 'bytes': size, 'sha256': sha, 'parts': parts,
                         'join': 'cat the parts in order, then check sha256'}, indent=1, sort_keys=True) + '\n').encode()
    index_name = name + '.parts.json'
    index_sha = hashlib.sha256(index).hexdigest()
    uploaded.append(dict(client.upload(index_name, index, len(index), 'application/json'), _sha256=index_sha))
    side = sidecar_text(index_sha, index_name).encode()
    uploaded.append(dict(client.upload(index_name + '.sha256', side, len(side), 'text/plain'),
                         _sha256=hashlib.sha256(side).hexdigest()))
    entries = [{'name': p['name'], 'bytes': p['bytes'], 'sha256': p['sha256'], 'status': 'UPLOADED'} for p in parts]
    entries.append({'name': index_name, 'bytes': len(index), 'sha256': index_sha, 'status': 'UPLOADED', 'whole_sha256': sha,
                    'whole_bytes': size})
    return entries


def done(work, out=print):
    collected = read_json(Path(work) / 'collect-manifest.json') or {}
    rows = read_json(files_dir(work) / ROWS_FILE) or {}
    status = read_json(Path(work) / 'upload-status.json') or {}
    flags = {'collect': collected.get('complete') is True, 'classify': rows.get('complete') is True,
             'upload': status.get('complete') is True}
    complete = all(flags.values())
    out(f'SECONCE_DONE complete={"yes" if complete else "no"} '
        + ' '.join(f'{k}={"yes" if v else "no"}' for k, v in flags.items()))
    return 0 if complete else 1


# ---- entry ---------------------------------------------------------------------------------------------------------------
def main(argv=None, *, environ=None, opener=None, call=None, open_url=None, sleep=time.sleep, clock=time.monotonic,
         disk_usage=shutil.disk_usage, out=None):
    environ = os.environ if environ is None else environ
    out = out if out is not None else (lambda line: print(line, flush=True))
    parser = argparse.ArgumentParser(description='SEC one-time collection (see the module docstring).')
    parser.add_argument('command', choices=('plan', 'resume-check', 'collect', 'upload', 'done'))
    parser.add_argument('--work', required=True)
    args = parser.parse_args(argv)
    work = Path(args.work)
    try:
        work.mkdir(parents=True, exist_ok=True)
        if args.command == 'plan':
            lines = plan_lines(disk_usage(work).free)
            for line in lines:
                out(line)
            return 0 if lines[-1].endswith('ok=yes') else 2
        if args.command == 'resume-check':
            return resume_check(work, environ, call=call, open_url=open_url, out=out)
        if args.command == 'collect':
            return collect(work, environ, opener=opener, sleep=sleep, clock=clock, out=out)
        if args.command == 'upload':
            return upload(work, environ, call=call, open_url=open_url, out=out)
        return done(work, out=out)
    except ConfigStop as stop:
        out(f'SECONCE_STOP reason={code_token(str(stop))}')
        return 2
    except ReleaseRefused as refused:
        out(f'SECONCE_STOP reason={refused.code}')
        return 1


if __name__ == '__main__':
    try:
        code = main()
    except (Exception, KeyboardInterrupt) as exc:
        name = type(exc).__name__
        print(f'SECONCE_STOP reason=UNEXPECTED class={name if pit._CODE_TOKEN.fullmatch(name) else "OTHER"}', flush=True)
        code = 1
    sys.exit(code)
