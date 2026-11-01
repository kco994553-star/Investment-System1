"""SEC one-time collection (tools/measure_once/sec_once_collect.py; plan docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md):
offline checks on synthetic, in-memory inputs only (no network, no Secret).

- the fixed plan: 2 bulk zips, 104 full-index files (2014-2026), 51 FSDS quarters (2014q1-2026q3), 157 requests;
- the exact SEC URL allow-list (www.sec.gov only, four path shapes) and the run-branch lock;
- the downloader: User-Agent and encodings, pacing, retries with backoff, truncation, size caps, 403 / 429 / request /
  wall-clock stops, a local disk fault stops at once (never retried as a network error), deterministic gzip storage,
  zip CRC check with one fresh download;
- collect end to end on a fake SEC: fixed count lines only, the private manifest, partial runs, the resume skip, and no
  request at all without this attempt's private-repository preflight marker;
- the private release: the raw repository must answer private on every attempt (resume-check, before any SEC request)
  and again before the release is created; the GitHub call allow-list (create-only, own tag only, no PATCH / PUT /
  DELETE, no listing), attempt 1 reads no release, uploads with sha256 sidecars, the 2 GiB split, read-back before the
  manifest, the manifest last, re-run attempts that skip verified assets (newest attempt first) and rename every name an
  upload would collide with (a fake GitHub that refuses duplicate names with 422, an interrupted split re-run);
- the workflow's shape (push to the run branch only, offline tests in their own job, `python -I -S` in the Secret job,
  one Secret per step, upload still runs after a classifier failure, pinned actions, no sinks).
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TOOL = ROOT / 'tools/measure_once/sec_once_collect.py'
WORKFLOW = REPO / '.github/workflows/sec-once-collect.yml'
sys.path.insert(0, str(TOOL.parent))
_spec = importlib.util.spec_from_file_location('sec_once_collect', TOOL)
once = importlib.util.module_from_spec(_spec)
sys.modules['sec_once_collect'] = once
_spec.loader.exec_module(once)
pit = once.pit

AT = chr(64)   # no address-shaped literal in this file (repository email guard)
AGENT = 'Synthetic Collect Probe ' + 'probe' + AT + 'example' + '.org'
TOKEN = 'synthetic-raw-repo-credential-' + 'x' * 12
RUN_ID = '987654321'
ENV = {'GITHUB_REPOSITORY': once.PUBLIC_REPO, 'GITHUB_REF': once.RUN_REF, 'GITHUB_RUN_ID': RUN_ID,
       'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'f' * 40}
TAG = 'sec-once-v1-' + RUN_ID
API = 'https://api.github.com/repos/kco994553-star/investment-system1-raw'
UPL = 'https://uploads.github.com/repos/kco994553-star/investment-system1-raw'


# ---- plan and allow-list ---------------------------------------------------------------------------------------------
def test_plan_is_fixed():
    items = once.plan_items()
    kinds = Counter(item['kind'] for item in items)
    assert kinds == {'bulk': 2, 'index': 104, 'fsds': 51} and len(items) == 157
    assert len({item['key'] for item in items}) == len({item['url'] for item in items}) == 157
    assert [i['key'] for i in items[:4]] == ['companyfacts.zip', 'submissions.zip', 'full-index-2014-QTR1-form.idx.gz',
                                            'full-index-2014-QTR1-company.idx.gz']
    assert items[105]['key'] == 'full-index-2026-QTR4-company.idx.gz'
    assert items[106]['url'] == 'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2014q1.zip'
    assert items[-1]['url'] == 'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q3.zip'
    assert all(once.ASSET_NAME.fullmatch(i['key']) and once.checked_sec_url(i['url']) for i in items)
    assert [i['key'] for i in items if i.get('optional')] == ['fsds-2026q3.zip']
    assert {i['store'] for i in items if i['kind'] == 'index'} == {'gzip'}
    assert {i['store'] for i in items if i['kind'] != 'index'} == {'raw'}


def test_plan_lines_and_disk_check():
    lines = once.plan_lines(20 * 1024 ** 3)
    assert lines == ['SECONCE_PLAN bulk=2 index_files=104 index_years=2014-2026 fsds_files=51 fsds_quarters=2014q1-2026q3 '
                     'sec_requests_planned=157 max_requests=500 wall_clock_s=3600 pace_s=0.15',
                     'SECONCE_DISK free_gb=20 need_gb=11 ok=yes']
    assert once.plan_lines(11 * 1024 ** 3)[1] == 'SECONCE_DISK free_gb=11 need_gb=11 ok=yes'
    assert once.plan_lines(11 * 1024 ** 3 - 1)[1] == 'SECONCE_DISK free_gb=10 need_gb=11 ok=no'


def test_plan_command_stops_on_little_disk(tmp_path):
    class Usage:
        free = 3 * 1024 ** 3
    out = []
    assert once.main(['plan', '--work', str(tmp_path)], disk_usage=lambda p: Usage(), out=out.append, environ={}) == 2
    assert out[-1] == 'SECONCE_DISK free_gb=3 need_gb=11 ok=no'


@pytest.mark.parametrize('url', [
    'https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip',
    'https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip',
    'https://www.sec.gov/Archives/edgar/full-index/2014/QTR1/form.idx',
    'https://www.sec.gov/Archives/edgar/full-index/2026/QTR4/company.idx',
    'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2021q2.zip',
])
def test_allow_list_accepts_the_planned_shapes(url):
    assert once.checked_sec_url(url) == url


@pytest.mark.parametrize('url', [
    'http://www.sec.gov/Archives/edgar/full-index/2014/QTR1/form.idx',
    'https://sec.gov/Archives/edgar/full-index/2014/QTR1/form.idx',
    'https://data.sec.gov/api/xbrl/companyfacts/CIK0000000011.json',
    'https://efts.sec.gov/LATEST/search-index?q=x',
    'https://www.sec.gov:443/Archives/edgar/full-index/2014/QTR1/form.idx',
    'https://user' + AT + 'www.sec.gov/Archives/edgar/full-index/2014/QTR1/form.idx',
    'https://www.sec.gov/Archives/edgar/full-index/2014/QTR1/form.idx?x=1',
    'https://www.sec.gov/Archives/edgar/full-index/2014/QTR5/form.idx',
    'https://www.sec.gov/Archives/edgar/full-index/1999/QTR1/form.idx',
    'https://www.sec.gov/Archives/edgar/full-index/2014/QTR1/master.idx',
    'https://www.sec.gov/Archives/edgar/full-index/2014/QTR1/../form.idx',
    'https://www.sec.gov/Archives/edgar/data/11/000000001117000001/index.json',
    'https://www.sec.gov/files/dera/data/financial-statement-and-notes-data-sets/2021q2_notes.zip',
    'https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip#x',
    'https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip\n',
    'https://api.github.com/repos/kco994553-star/investment-system1-raw/releases',
    None,
])
def test_allow_list_refuses_everything_else(url):
    with pytest.raises(ValueError):
        once.checked_sec_url(url)


@pytest.mark.parametrize('change, code', [
    ({'GITHUB_REF': 'refs/heads/claude/sec-once-collect-plan'}, 'NOT_THE_RUN_BRANCH'),
    ({'GITHUB_REF': 'refs/heads/main'}, 'NOT_THE_RUN_BRANCH'),
    ({'GITHUB_REF': 'refs/pull/1/merge'}, 'NOT_THE_RUN_BRANCH'),
    ({'GITHUB_REPOSITORY': 'someone/fork'}, 'NOT_THE_RUN_BRANCH'),
    ({'GITHUB_RUN_ID': ''}, 'RUN_ID_INVALID'),
    ({'GITHUB_RUN_ID': '12a'}, 'RUN_ID_INVALID'),
    ({'GITHUB_RUN_ID': '0'}, 'RUN_ID_INVALID'),
    ({'GITHUB_RUN_ATTEMPT': 'x'}, 'RUN_ATTEMPT_INVALID'),
])
def test_run_context_lock(change, code):
    with pytest.raises(once.ConfigStop) as stop:
        once.run_context({**ENV, **change})
    assert str(stop.value) == code
    assert once.run_context(ENV) == (RUN_ID, 1)
    assert once.release_tag(RUN_ID) == TAG


# ---- fakes -------------------------------------------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, body, headers=None, length=True):
        self._body = io.BytesIO(body)
        self.headers = dict(headers or {})
        if length and 'Content-Length' not in self.headers and 'Content-Encoding' not in self.headers:
            self.headers['Content-Length'] = str(len(body))
        self.status = 200

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_error(url, status, headers=None):
    return urllib.error.HTTPError(url, status, 'synthetic', headers or {}, None)


class FakeOpener:
    """Answers with the next scripted item (FakeResponse, exception, callable(url)); `default` once the script is used up."""

    def __init__(self, script=(), default=None):
        self.script, self.default, self.calls = list(script), default, []

    def open(self, request, timeout=None):
        assert isinstance(request, urllib.request.Request) and timeout == once.TIMEOUT_S
        self.calls.append((request.full_url, request.get_header('User-agent'), request.get_header('Accept-encoding')))
        item = self.script.pop(0) if self.script else self.default
        if callable(item) and not isinstance(item, BaseException):
            item = item(request.full_url)
        if isinstance(item, BaseException):
            raise item
        return item


class Clock:
    def __init__(self, *times):
        self.times, self.last = list(times), 0.0

    def __call__(self):
        if self.times:
            self.last = self.times.pop(0)
        return self.last


def zip_bytes(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


IDX_HEAD = ['Description:           Master Index of EDGAR Dissemination Feed by Form Type',
            'Last Data Received:    March 31, 2017', '', 'Form Type   Company Name' + ' ' * 52 + 'CIK         Date Filed  File Name',
            '-' * 140]


def idx_row(form, cik, filed, accession, name='SYNTHETIC COMPANY INC'):
    return f'{form:<12}{name:<62}{cik:<12}{filed:<12}edgar/data/{cik}/{accession}.txt'


def idx_text(year):
    rows = [idx_row('10-K', 11, f'{year}-02-20', f'0000000011-{year % 100:02d}-000001'),
            idx_row('10-Q', 12, f'{year}-03-01', f'0000000012-{year % 100:02d}-000002'),
            idx_row('15-12B', 13, f'{year}-03-02', f'0000000013-{year % 100:02d}-000003'),
            idx_row('25-NSE', 13, f'{year}-03-02', f'0000000013-{year % 100:02d}-000004'),
            idx_row('8-A12B', 14, f'{year}-03-03', f'0000000014-{year % 100:02d}-000005'),
            idx_row('8-K', 11, f'{year}-03-04', f'0000000011-{year % 100:02d}-000006')]
    return ('\n'.join(IDX_HEAD + rows) + '\n').encode('latin-1')


COMPANYFACTS = zip_bytes({'CIK0000000011.json': b'{"cik": 11, "facts": {}}', 'CIK0000000012.json': b'{"cik": 12}'})
SUBMISSIONS = zip_bytes({'CIK0000000011.json': b'{"cik": "11"}', 'CIK0000000011-submissions-001.json': b'{}',
                         'CIK0000000012.json': b'{"cik": "12"}'})
FSDS = zip_bytes({'sub.txt': b'adsh\tcik\tsic\n', 'num.txt': b'adsh\ttag\tvalue\n'})


def fake_sec(url):
    """A fake SEC for every planned URL (zips as identity with Content-Length, .idx gzip-encoded)."""
    if url.endswith('companyfacts.zip'):
        return FakeResponse(COMPANYFACTS)
    if url.endswith('submissions.zip'):
        return FakeResponse(SUBMISSIONS)
    if url.endswith('.idx'):
        year = int(re.search(r'/full-index/(\d{4})/', url).group(1))
        return FakeResponse(gzip.compress(idx_text(year)), {'Content-Encoding': 'gzip'})
    if 'financial-statement-data-sets' in url:
        return FakeResponse(FSDS)
    raise AssertionError('unplanned URL')


def downloader(script=(), default=None, clock=None):
    sleeps = []
    d = once.Downloader(AGENT, opener=FakeOpener(script, default), sleep=sleeps.append, clock=clock or Clock(0.0))
    return d, sleeps


ITEM_ZIP = {'key': 'fsds-2017q1.zip', 'kind': 'fsds', 'store': 'raw',
            'url': 'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2017q1.zip'}
ITEM_IDX = {'key': 'full-index-2017-QTR1-form.idx.gz', 'kind': 'index', 'store': 'gzip',
            'url': 'https://www.sec.gov/Archives/edgar/full-index/2017/QTR1/form.idx'}


# ---- downloader -----------------------------------------------------------------------------------------------------------
def test_download_zip_headers_pacing_and_record(tmp_path):
    d, sleeps = downloader([FakeResponse(FSDS, {'Last-Modified': 'Tue, 01 Jan 2019 00:00:00 GMT'})])
    record = d.download(ITEM_ZIP, tmp_path / ITEM_ZIP['key'])
    assert d._opener.calls == [(ITEM_ZIP['url'], AGENT, 'identity')] and sleeps == [once.SLEEP_S]
    assert (tmp_path / ITEM_ZIP['key']).read_bytes() == FSDS
    assert record['source_sha256'] == record['stored_sha256'] == hashlib.sha256(FSDS).hexdigest()
    assert record['source_bytes'] == record['stored_bytes'] == record['wire_bytes'] == len(FSDS)
    assert record['last_modified'] == 'Tue, 01 Jan 2019 00:00:00 GMT' and record['resumed'] is False
    assert not list(tmp_path.glob('*.part'))


def test_download_index_is_gunzipped_hashed_and_stored_deterministically(tmp_path):
    body = idx_text(2017)
    d, _ = downloader([FakeResponse(gzip.compress(body, mtime=1), {'Content-Encoding': 'gzip'}),
                       FakeResponse(gzip.compress(body, mtime=2), {'Content-Encoding': 'gzip'}),
                       FakeResponse(body)])                                   # a server that ignores Accept-Encoding
    first = d.download(ITEM_IDX, tmp_path / 'a.gz')
    second = d.download(ITEM_IDX, tmp_path / 'b.gz')
    third = d.download(ITEM_IDX, tmp_path / 'c.gz')
    assert d._opener.calls[0][2] == 'gzip'
    assert first['source_sha256'] == second['source_sha256'] == third['source_sha256'] == hashlib.sha256(body).hexdigest()
    assert first['stored_sha256'] == second['stored_sha256'] == third['stored_sha256']     # mtime 0, no file name
    assert gzip.decompress((tmp_path / 'a.gz').read_bytes()) == body and first['source_bytes'] == len(body)


def test_download_retries_429_5xx_network_and_truncation_with_backoff(tmp_path):
    d, sleeps = downloader([http_error('x', 429, {'Retry-After': '45'}), http_error('x', 503),
                            FakeResponse(FSDS)])
    d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert sleeps == [0.15, 45.0, 0.15, 20.0, 0.15] and d.counts['retries'] == 2 and d.counts['total'] == 3
    d, sleeps = downloader([FakeResponse(FSDS[:-5], {'Content-Length': str(len(FSDS))}), urllib.error.URLError('x'),
                            FakeResponse(FSDS)])
    d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert d.counts['retries'] == 2 and (tmp_path / 'f.zip').read_bytes() == FSDS
    truncated = gzip.compress(idx_text(2017))[:-12]
    d, _ = downloader([FakeResponse(truncated, {'Content-Encoding': 'gzip'})] * 3)
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_IDX, tmp_path / 'i.gz')
    assert exc.value.code == 'TRUNCATED' and d.counts['total'] == 3 and not (tmp_path / 'i.gz').exists()
    assert not list(tmp_path.glob('*.part'))
    d, _ = downloader([http_error('x', 500)] * 3)
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_ZIP, tmp_path / 'g.zip')
    assert exc.value.code == 'HTTP500' and d.counts['http5xx'] == 3


@pytest.mark.parametrize('status', [400, 401, 403, 404, 410])
def test_other_statuses_are_not_retried(tmp_path, status):
    d, _ = downloader([http_error('x', status)])
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert exc.value.code == f'HTTP{status}' and d.counts['total'] == 1


def test_size_caps_and_encodings(tmp_path, monkeypatch):
    monkeypatch.setitem(once.CAPS, 'fsds', 100)
    d, _ = downloader([FakeResponse(b'x' * 101)])
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert exc.value.code == 'SIZE_CAP' and d.counts['total'] == 1
    d, _ = downloader([FakeResponse(b'x' * 50, {'Content-Length': '101'})])
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert exc.value.code == 'SIZE_CAP'
    monkeypatch.setitem(once.CAPS, 'index', 1024 * 1024)
    bomb = gzip.compress(b'\0' * (8 * 1024 * 1024))
    d, _ = downloader([FakeResponse(bomb, {'Content-Encoding': 'gzip'})])
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_IDX, tmp_path / 'i.gz')
    assert exc.value.code == 'SIZE_CAP' and d.counts['body_bytes'] <= 6 * 1024 * 1024
    d, _ = downloader([FakeResponse(gzip.compress(FSDS), {'Content-Encoding': 'gzip'})])     # zips must come as they are
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert exc.value.code == 'ENCODING_NOT_SUPPORTED'
    d, _ = downloader([FakeResponse(b'not gzip', {'Content-Encoding': 'gzip'})])
    with pytest.raises(pit.FetchError) as exc:
        d.download(ITEM_IDX, tmp_path / 'i.gz')
    assert exc.value.code == 'BAD_GZIP'
    assert not list(tmp_path.iterdir())


def test_stops(tmp_path):
    d, _ = downloader()
    d.counts['total'] = once.MAX_REQUESTS
    with pytest.raises(pit.Stop) as stop:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert stop.value.reason == 'REQUEST_CAP' and d._opener.calls == []
    d, _ = downloader(clock=Clock(0.0, float(once.WALL_CLOCK_S)))
    with pytest.raises(pit.Stop) as stop:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert stop.value.reason == 'WALL_CLOCK' and d._opener.calls == []
    d, _ = downloader([http_error('x', 403)] * once.STOP_AFTER_403)
    for _ in range(once.STOP_AFTER_403 - 1):
        with pytest.raises(pit.FetchError):
            d.download(ITEM_ZIP, tmp_path / 'f.zip')
    with pytest.raises(pit.Stop) as stop:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert stop.value.reason == 'HTTP403_REPEATED'
    d, _ = downloader([http_error('x', 429)] * once.STOP_AFTER_429)
    with pytest.raises(pit.Stop) as stop:
        for _ in range(once.STOP_AFTER_429):
            try:
                d.download(ITEM_ZIP, tmp_path / 'f.zip')
            except pit.FetchError:
                pass
    assert stop.value.reason == 'HTTP429_REPEATED' and d.counts['total'] == once.STOP_AFTER_429


def test_default_opener_refuses_redirects():
    d = once.Downloader(AGENT, sleep=lambda s: None, clock=Clock(0.0))
    assert any(isinstance(h, pit._RejectRedirects) for h in d._opener.handlers)


def test_zip_check(tmp_path):
    good = tmp_path / 'g.zip'
    good.write_bytes(SUBMISSIONS)
    assert once.zip_check(good) == ('OK', 3, 1)
    cut = tmp_path / 'c.zip'
    cut.write_bytes(SUBMISSIONS[:-30])
    assert once.zip_check(cut) == ('BAD_ZIP', None, None)
    stored = io.BytesIO()
    with zipfile.ZipFile(stored, 'w', zipfile.ZIP_STORED) as archive:
        archive.writestr('a.json', b'{"value": 12345}')
    data = bytearray(stored.getvalue())
    data[data.index(b'12345')] = ord('9')
    bad = tmp_path / 'b.zip'
    bad.write_bytes(bytes(data))
    assert once.zip_check(bad)[0] == 'CRC_FAILED'


def test_index_form_counts(tmp_path):
    path = tmp_path / 'f.idx.gz'
    path.write_bytes(gzip.compress(idx_text(2018) + b'garbage line\n'))
    assert once.index_form_counts(path) == Counter(rows=6, f10k=1, f10q=1, f1512b=1, f25nse=1, f8a12b=1, f8k=1)
    path.write_bytes(gzip.compress(b'no header\n'))
    with pytest.raises(ValueError):
        once.index_form_counts(path)


# ---- collect end to end ----------------------------------------------------------------------------------------------------
LINE = [re.compile(p) for p in (
    r'SECONCE_FILES kind=(?:bulk|index|fsds) planned=\d+ ok=\d+ resumed=\d+ failed=\d+ optional_missing=\d+ mb=\d+\.\d',
    r'SECONCE_ZIP name=(?:companyfacts|submissions) entries=(?:\d+|NA) overflow_pages=(?:\d+|NA) check=[A-Z_]+',
    r'SECONCE_ZIP name=fsds files=\d+ ok=\d+ bad=\d+',
    r'SECONCE_INDEX year=20\d\d quarters=[1-4] rows=\d+(?: f[a-z0-9]+=\d+){9}',
    r'SECONCE_ERRORS codes=(?:-|[A-Za-z][A-Za-z0-9_]*:\d+(?:,[A-Za-z][A-Za-z0-9_]*:\d+)*)',
    r'SECONCE_REQUESTS(?: [a-z0-9]+=\d+){9} mb_wire=\d+\.\d mb_body=\d+\.\d elapsed_s=\d+ '
    r'stopped=(?:NONE|REQUEST_CAP|WALL_CLOCK|HTTP403_REPEATED|HTTP429_REPEATED|LOCAL_DISK_FULL|LOCAL_IO|UNEXPECTED) '
    r'complete=(?:yes|no)',
    r'SECONCE_PREFLIGHT raw_repo=private',
    r'SECONCE_RESUME attempt=\d+ release=(?:NOT_READ|ABSENT|PRESENT) assets=\d+ verified=\d+ unverified=\d+',
    r'SECONCE_RELEASE created=(?:yes|no) assets_uploaded=\d+ assets_present=\d+ assets_failed=\d+ mb=\d+\.\d '
    r'manifest=(?:OK|FAILED)',
    r'SECONCE_VERIFY assets=\d+ ok=\d+ bad=\d+',
    r'SECONCE_DONE complete=(?:yes|no) collect=(?:yes|no) classify=(?:yes|no) upload=(?:yes|no)',
    r'SECONCE_STOP reason=[A-Z0-9_]+',
)]


def assert_fixed_lines(lines):
    for line in lines:
        assert any(p.fullmatch(line) for p in LINE), line
        assert AT not in line and '://' not in line and 'sec.gov' not in line and '/' not in line
        assert TOKEN not in line and AGENT not in line and not re.search(r'\d{10}', line)


def write_preflight(work, environ=None):
    """The marker resume-check writes after the raw repository answered private (tests that do not run resume-check)."""
    run_id, attempt = once.run_context(environ or ENV)
    Path(work).mkdir(parents=True, exist_ok=True)
    once.write_json(Path(work) / once.PREFLIGHT_FILE, {'repository': once.RAW_REPO, 'private': True,
                                                       'visibility': 'private', 'run_id': run_id, 'attempt': attempt})


def run_collect(tmp_path, opener, env=None, clock=None, preflight=True):
    lines = []
    environ = env or {**ENV, 'SEC_USER_AGENT': AGENT}
    if preflight and not (Path(tmp_path) / once.PREFLIGHT_FILE).is_file():
        try:
            write_preflight(tmp_path, environ)
        except once.ConfigStop:
            pass
    code = once.main(['collect', '--work', str(tmp_path)], environ=environ,
                     opener=opener, sleep=lambda s: None, clock=clock or Clock(0.0), out=lines.append)
    return code, lines


def test_collect_end_to_end_counts_only(tmp_path):
    opener = FakeOpener(default=fake_sec)
    code, lines = run_collect(tmp_path, opener)
    assert code == 0 and len(opener.calls) == 157
    assert {agent for _, agent, _ in opener.calls} == {AGENT}
    assert [url for url, _, _ in opener.calls] == [item['url'] for item in once.plan_items()]
    assert_fixed_lines(lines)
    assert lines[:3] == ['SECONCE_FILES kind=bulk planned=2 ok=2 resumed=0 failed=0 optional_missing=0 mb=0.0',
                         'SECONCE_FILES kind=index planned=104 ok=104 resumed=0 failed=0 optional_missing=0 mb=0.0',
                         'SECONCE_FILES kind=fsds planned=51 ok=51 resumed=0 failed=0 optional_missing=0 mb=0.0']
    assert lines[3:6] == ['SECONCE_ZIP name=companyfacts entries=2 overflow_pages=NA check=OK',
                          'SECONCE_ZIP name=submissions entries=3 overflow_pages=1 check=OK',
                          'SECONCE_ZIP name=fsds files=51 ok=51 bad=0']
    index = [line for line in lines if line.startswith('SECONCE_INDEX ')]
    assert len(index) == 13 and index[0] == ('SECONCE_INDEX year=2014 quarters=4 rows=24 f10k=4 f10q=4 f8k=4 f25=0 '
                                             'f25nse=4 f8a12b=4 f1512b=4 f1512g=0 f1515d=0')
    assert lines[-2] == 'SECONCE_ERRORS codes=-'
    assert lines[-1].startswith('SECONCE_REQUESTS total=157 bulk=2 index=104 fsds=51 retries=0 redownloads=0 http403=0 ')
    assert lines[-1].endswith(' stopped=NONE complete=yes')
    manifest = json.loads((tmp_path / 'collect-manifest.json').read_text())
    assert manifest['complete'] is True and manifest['failed'] == {} and len(manifest['records']) == 157
    assert manifest['plan'] == {'index_years': [2014, 2026], 'index_files': ['form', 'company'],
                                'fsds_quarters': ['2014q1', '2026q3'], 'bulk': ['companyfacts.zip', 'submissions.zip'],
                                'files_planned': 157}
    for record in manifest['records']:
        path = tmp_path / 'files' / record['key']
        assert once.sha256_file(path) == record['stored_sha256'] and path.stat().st_size == record['stored_bytes']
        assert once.source_digest(path, record['store']) == (record['source_bytes'], record['source_sha256'])
    assert AGENT not in (tmp_path / 'collect-manifest.json').read_text()


def test_collect_partial_run_keeps_going_and_says_so(tmp_path):
    def answer(url):
        if url.endswith('2019q2.zip'):
            return http_error(url, 404)
        if url.endswith('companyfacts.zip'):
            return FakeResponse(COMPANYFACTS[:-40])            # a broken zip twice: re-downloaded once, then failed
        return fake_sec(url)
    opener = FakeOpener(default=answer)
    code, lines = run_collect(tmp_path, opener)
    assert code == 0 and len(opener.calls) == 158
    assert_fixed_lines(lines)
    assert lines[0] == 'SECONCE_FILES kind=bulk planned=2 ok=1 resumed=0 failed=1 optional_missing=0 mb=0.0'
    assert lines[2] == 'SECONCE_FILES kind=fsds planned=51 ok=50 resumed=0 failed=1 optional_missing=0 mb=0.0'
    assert lines[3] == 'SECONCE_ZIP name=companyfacts entries=NA overflow_pages=NA check=MISSING'
    assert 'SECONCE_ERRORS codes=BULK_BAD_ZIP:1,FSDS_HTTP404:1' in lines
    assert lines[-1].endswith(' stopped=NONE complete=no') and ' redownloads=1 ' in lines[-1]
    manifest = json.loads((tmp_path / 'collect-manifest.json').read_text())
    assert manifest['failed'] == {'companyfacts.zip': 'BAD_ZIP', 'fsds-2019q2.zip': 'HTTP404'}
    assert not (tmp_path / 'files/companyfacts.zip').exists()


def test_newest_fsds_quarter_not_yet_published_is_not_a_failure(tmp_path):
    def answer(url):
        return http_error(url, 404) if url.endswith(('2026q3.zip', '2026q2.zip')) else fake_sec(url)
    code, lines = run_collect(tmp_path, FakeOpener(default=answer))
    assert code == 0
    assert lines[2] == 'SECONCE_FILES kind=fsds planned=51 ok=49 resumed=0 failed=1 optional_missing=1 mb=0.0'
    assert 'SECONCE_ERRORS codes=FSDS_HTTP404:1' in lines and lines[-1].endswith(' complete=no')
    code, lines = run_collect(tmp_path / 'b', FakeOpener(default=lambda url: http_error(url, 404) if url.endswith('2026q3.zip')
                                                         else fake_sec(url)))
    assert lines[2] == 'SECONCE_FILES kind=fsds planned=51 ok=50 resumed=0 failed=0 optional_missing=1 mb=0.0'
    assert 'SECONCE_ERRORS codes=-' in lines and lines[-1].endswith(' complete=yes')
    manifest = json.loads((tmp_path / 'b/collect-manifest.json').read_text())
    assert manifest['optional_missing'] == {'fsds-2026q3.zip': 'HTTP404'} and manifest['complete'] is True


def test_collect_stop_keeps_what_it_has(tmp_path):
    opener = FakeOpener([fake_sec] * 3 + [http_error('x', 403)] * once.STOP_AFTER_403)
    code, lines = run_collect(tmp_path, opener)
    assert code == 0 and len(opener.calls) == 3 + once.STOP_AFTER_403
    assert_fixed_lines(lines)
    assert lines[-1].endswith(' stopped=HTTP403_REPEATED complete=no')
    manifest = json.loads((tmp_path / 'collect-manifest.json').read_text())
    assert len(manifest['records']) == 3 and manifest['stopped'] == 'HTTP403_REPEATED'


def test_collect_skips_files_the_resume_check_verified(tmp_path):
    files = tmp_path / 'files'
    files.mkdir()
    (files / 'submissions.zip').write_bytes(SUBMISSIONS)
    (files / 'fsds-2014q1.zip').write_bytes(b'changed since')            # listed but altered: fetched again
    once.write_json(tmp_path / 'resume.json', {'verified': [
        {'key': 'submissions.zip', 'asset': 'submissions.zip', 'sha256': hashlib.sha256(SUBMISSIONS).hexdigest()},
        {'key': 'fsds-2014q1.zip', 'asset': 'fsds-2014q1.zip', 'sha256': hashlib.sha256(FSDS).hexdigest()}]})
    opener = FakeOpener(default=fake_sec)
    code, lines = run_collect(tmp_path, opener)
    assert code == 0 and len(opener.calls) == 156
    assert not any(url.endswith('submissions.zip') for url, _, _ in opener.calls)
    assert lines[0] == 'SECONCE_FILES kind=bulk planned=2 ok=1 resumed=1 failed=0 optional_missing=0 mb=0.0'
    assert 'SECONCE_ZIP name=submissions entries=3 overflow_pages=1 check=OK' in lines
    record = next(r for r in json.loads((tmp_path / 'collect-manifest.json').read_text())['records']
                  if r['key'] == 'submissions.zip')
    assert record['resumed'] is True and record['source_sha256'] == hashlib.sha256(SUBMISSIONS).hexdigest()


class NoNetwork:
    calls = []

    def open(self, *args, **kwargs):
        raise AssertionError('no request may be made')


@pytest.mark.parametrize('env, line', [
    ({**ENV}, 'SECONCE_STOP reason=SEC_USER_AGENT_MISSING'),
    ({**ENV, 'SEC_USER_AGENT': '  '}, 'SECONCE_STOP reason=SEC_USER_AGENT_MISSING'),
    ({**ENV, 'SEC_USER_AGENT': 'no contact here'}, 'SECONCE_STOP reason=SEC_USER_AGENT_INVALID'),
    ({**ENV, 'SEC_USER_AGENT': AGENT + '\r\nX: 1'}, 'SECONCE_STOP reason=SEC_USER_AGENT_INVALID'),
    ({**ENV, 'SEC_USER_AGENT': AGENT, 'GITHUB_REF': 'refs/heads/main'}, 'SECONCE_STOP reason=NOT_THE_RUN_BRANCH'),
])
def test_collect_configuration_stops_before_any_request(tmp_path, env, line):
    code, lines = run_collect(tmp_path, NoNetwork(), env=env)
    assert code == 2 and lines == [line]


@pytest.mark.parametrize('marker, line', [
    (None, 'SECONCE_STOP reason=RAW_PREFLIGHT_MISSING'),
    ({'repository': once.RAW_REPO, 'private': True, 'visibility': 'private', 'run_id': RUN_ID, 'attempt': 2},
     'SECONCE_STOP reason=RAW_PREFLIGHT_MISSING'),                      # an earlier / other attempt's marker
    ({'repository': once.RAW_REPO, 'private': False, 'visibility': 'public', 'run_id': RUN_ID, 'attempt': 1},
     'SECONCE_STOP reason=RAW_PREFLIGHT_MISSING'),
    ({'repository': 'kco994553-star/other', 'private': True, 'visibility': 'private', 'run_id': RUN_ID, 'attempt': 1},
     'SECONCE_STOP reason=RAW_PREFLIGHT_MISSING'),
])
def test_collect_refuses_to_start_without_this_attempts_private_preflight(tmp_path, marker, line):
    if marker is not None:
        once.write_json(tmp_path / once.PREFLIGHT_FILE, marker)
    code, lines = run_collect(tmp_path, NoNetwork(), preflight=False)
    assert code == 2 and lines == [line]


class DiskFull(io.BytesIO):
    """A local file whose writes fail with ENOSPC after `room` bytes."""

    def __init__(self, room):
        super().__init__()
        self.room = room

    def write(self, data):
        if self.tell() + len(data) > self.room:
            raise OSError(once.errno.ENOSPC, 'synthetic: no space left')
        return super().write(data)


@pytest.mark.parametrize('error, reason', [(once.errno.ENOSPC, 'LOCAL_DISK_FULL'), (once.errno.EIO, 'LOCAL_IO')])
def test_local_disk_fault_stops_at_once_and_is_never_retried(tmp_path, monkeypatch, error, reason):
    real_open = open

    def fake_open(path, mode='r', *args, **kwargs):
        if str(path).endswith('.part') and 'w' in mode:
            if error == once.errno.ENOSPC:
                return DiskFull(10)
            raise OSError(error, 'synthetic I/O error')
        return real_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(once, 'open', fake_open, raising=False)
    d, sleeps = downloader([FakeResponse(FSDS)] * 3)
    with pytest.raises(pit.Stop) as stop:
        d.download(ITEM_ZIP, tmp_path / 'f.zip')
    assert stop.value.reason == reason and d.counts['total'] == 1 and d.counts['retries'] == 0
    assert sleeps == [once.SLEEP_S]                                     # no backoff wait, no second request
    opener = FakeOpener(default=fake_sec)
    code, lines = run_collect(tmp_path / 'w', opener)
    assert code == 0 and len(opener.calls) == 1
    assert_fixed_lines(lines)
    assert lines[-1].endswith(f' stopped={reason} complete=no')
    assert json.loads((tmp_path / 'w/collect-manifest.json').read_text())['stopped'] == reason


def test_script_without_user_agent_prints_one_fixed_line(tmp_path):
    """Started like the workflow starts it (python -I -S: no site-packages, no .pth hooks, no PYTHONPATH)."""
    env = {k: v for k, v in os.environ.items() if k not in ('SEC_USER_AGENT', 'RAW_REPO_TOKEN') and k.lower() not in
           ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', **ENV)
    isolated = [sys.executable, '-I', '-S']
    run = subprocess.run(isolated + [str(TOOL), 'collect', '--work', str(tmp_path / 'w')], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=60)
    assert (run.returncode, run.stdout, run.stderr) == (2, 'SECONCE_STOP reason=SEC_USER_AGENT_MISSING\n', '')
    for command in ('upload', 'resume-check'):
        run = subprocess.run(isolated + [str(TOOL), command, '--work', str(tmp_path / 'w')], cwd=tmp_path, env=env,
                             capture_output=True, text=True, timeout=60)
        assert (run.returncode, run.stdout, run.stderr) == (2, 'SECONCE_STOP reason=RAW_REPO_TOKEN_MISSING\n', '')
    run = subprocess.run(isolated + [str(TOOL.parent / 'sec_once_ticker_mismatch.py'), '--work', str(tmp_path / 'w')],
                         cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert (run.returncode, run.stdout, run.stderr) == (2, 'TICKERMIX_STOP reason=SEC_USER_AGENT_MISSING\n', '')


# ---- the private release ---------------------------------------------------------------------------------------------------
PRIVATE_REPO = {'full_name': 'kco994553-star/investment-system1-raw', 'private': True, 'visibility': 'private'}


class FakeGitHub:
    """Fake api.github.com / uploads.github.com for the raw repository: `call` (raw_store_release.http signature) and
    `open_url` (streaming downloads). Records every request. Like GitHub, it refuses a duplicate asset name (422)."""

    def __init__(self, release=None, fail_upload=(), repo=None, repo_status=200):
        self.calls, self.assets, self.next_id, self.fail_upload = [], {}, 100, set(fail_upload)
        self.release = release
        self.repo, self.repo_status = dict(PRIVATE_REPO if repo is None else repo), repo_status
        if release is not None:
            for asset in release['assets']:
                self.assets[asset['id']] = asset

    def call(self, method, url, *, data=None, headers=None, auth=True, opener=None):
        assert os.environ.get('RAW_REPO_TOKEN') == TOKEN
        body = data if isinstance(data, bytes) or data is None else b''.join(iter(lambda: data.read(65536), b''))
        if headers is not None and 'Content-Length' in headers:
            assert int(headers['Content-Length']) == len(body)
        self.calls.append((method, url, None if body is None else len(body)))
        if method == 'GET' and url == API:
            if isinstance(self.repo_status, BaseException):
                raise self.repo_status
            return self.repo_status, {}, json.dumps(self.repo).encode()
        if method == 'GET' and url == f'{API}/releases/tags/{TAG}':
            if self.release is None:
                return 404, {}, b'{"message": "Not Found"}'
            return 200, {}, json.dumps({**self.release, 'assets': [{k: v for k, v in a.items() if k != '_body'}
                                                                   for a in self.release['assets']]}).encode()
        if method == 'POST' and url == f'{API}/releases':
            payload = json.loads(body)
            assert payload['tag_name'] == payload['name'] == TAG and payload['draft'] is False
            assert payload['make_latest'] == 'false'
            if self.release is not None:
                return 422, {}, b'{}'
            self.release = {'id': 77, 'tag_name': TAG, 'assets': []}
            return 201, {}, json.dumps(self.release).encode()
        match = re.fullmatch(re.escape(UPL) + r'/releases/77/assets\?name=(.+)', url)
        if method == 'POST' and match:
            name = urllib.parse.unquote(match.group(1))
            if name in self.fail_upload:
                return 500, {}, b''
            if any(a['name'] == name for a in self.release['assets']):
                return 422, {}, b'{"errors": [{"code": "already_exists"}]}'
            self.next_id += 1
            asset = {'id': self.next_id, 'name': name, 'size': len(body), 'state': 'uploaded', '_body': body}
            self.assets[asset['id']] = asset
            self.release['assets'].append(asset)
            return 201, {}, json.dumps({k: v for k, v in asset.items() if k != '_body'}).encode()
        raise AssertionError(('unexpected GitHub call', method, url))

    def open_url(self, request, timeout=None):
        url = request.full_url
        self.calls.append(('GET', url, None))
        match = re.fullmatch(re.escape(API) + r'/releases/assets/(\d+)', url)
        if match:
            assert request.get_header('Authorization') == 'Bearer ' + TOKEN
            raise urllib.error.HTTPError(url, 302, 'Found', {'Location': f'https://release-assets.githubusercontent.com/'
                                                                         f'x/{match.group(1)}?sig=1'}, None)
        match = re.fullmatch(r'https://release-assets\.githubusercontent\.com/x/(\d+)\?sig=1', url)
        assert match and request.get_header('Authorization') is None
        return FakeResponse(self.assets[int(match.group(1))]['_body'])


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv('RAW_REPO_TOKEN', TOKEN)


def env(attempt=1):
    return {**ENV, 'RAW_REPO_TOKEN': TOKEN, 'GITHUB_RUN_ATTEMPT': str(attempt)}


def test_release_client_allow_list():
    client = once.ReleaseClient(TAG, call=lambda *a, **k: None)
    client.check('GET', API)                                   # the raw repository's own metadata (private check)
    client.check('GET', f'{API}/releases/tags/{TAG}')
    client.check('POST', f'{API}/releases')
    for method, url in (('GET', f'{API}/releases'), ('GET', API + '/'), ('GET', 'https://api.github.com/repos/other/repo'),
                        ('PATCH', API), ('DELETE', API), ('POST', API), ('GET', f'{API}/releases/latest'),
                        ('GET', f'{API}/releases/tags/sec-once-v1-1'), ('GET', f'{API}/releases/tags/kis-us-daily-1'),
                        ('GET', f'{API}/releases/tags/{TAG}x'), ('PATCH', f'{API}/releases/77'),
                        ('DELETE', f'{API}/releases/77'), ('DELETE', f'{API}/releases/assets/5'),
                        ('PUT', f'{API}/releases/77'), ('POST', f'{UPL}/releases/77/assets?name=fsds-2014q1.zip'),
                        ('GET', f'{API}/releases/assets/5'), ('POST', 'https://api.github.com/repos/other/repo/releases'),
                        ('GET', f'https://api.github.com/repos/kco994553-star/investment-system1-raw/git/refs')):
        with pytest.raises(once.ReleaseRefused):
            client.check(method, url)
    client._adopt({'id': 77, 'tag_name': TAG, 'assets': [{'id': 5, 'name': 'fsds-2014q1.zip'},
                                                         {'id': 6, 'name': 'kis-anything.json'}]})
    client.check('POST', f'{UPL}/releases/77/assets?name=fsds-2014q1.zip')
    client.check('POST', f'{UPL}/releases/77/assets?name=a2-fsds-2014q1.zip.sha256')
    client.check('POST', f'{UPL}/releases/77/assets?name=sec-once-manifest-a1.json')
    client.check('GET', f'{API}/releases/assets/5')
    for method, url in (('POST', f'{API}/releases'), ('GET', f'{API}/releases/assets/6'),
                        ('POST', f'{UPL}/releases/78/assets?name=fsds-2014q1.zip'),
                        ('POST', f'{UPL}/releases/77/assets?name=prices.csv'),
                        ('POST', f'{UPL}/releases/77/assets?name=fsds-2014q1.zip%2F..'),
                        ('POST', f'{UPL}/releases/77/assets?name=..%2Fx.zip'),
                        ('DELETE', f'{API}/releases/assets/5'), ('PATCH', f'{API}/releases/assets/5')):
        with pytest.raises(once.ReleaseRefused):
            client.check(method, url)
    with pytest.raises(once.ReleaseRefused):
        client._adopt({'id': 78, 'tag_name': 'kis-us-daily-1', 'assets': []})
    for tag in ('sec-once-v1-', 'sec-once-v1-0', 'exp-deciles-v1-1', 'kis-1', 'sec-once-v1-1/../x'):
        with pytest.raises(once.ReleaseRefused):
            once.ReleaseClient(tag)


def collected(tmp_path):
    code, _ = run_collect(tmp_path, FakeOpener(default=fake_sec))
    assert code == 0
    once.write_json(tmp_path / 'files' / once.ROWS_FILE, {'schema': 'sec-once-ticker-mismatch/1', 'complete': True,
                                                         'rows': [], 'summary': {}})


def run_upload(tmp_path, gh, attempt=1):
    lines = []
    code = once.main(['upload', '--work', str(tmp_path)], environ=env(attempt), call=gh.call, open_url=gh.open_url,
                     out=lines.append)
    return code, lines


def test_upload_attempt_one_creates_without_reading_and_verifies_back(tmp_path, token):
    collected(tmp_path)
    gh = FakeGitHub()
    code, lines = run_upload(tmp_path, gh)
    assert code == 0
    assert_fixed_lines(lines)
    assert lines[0].startswith('SECONCE_RELEASE created=yes assets_uploaded=159 assets_present=0 assets_failed=0 ')
    assert lines[0].endswith(' manifest=OK') and lines[1] == 'SECONCE_VERIFY assets=318 ok=318 bad=0'
    assert lines[2] == 'SECONCE_ERRORS codes=-'
    methods = Counter((m, re.sub(r'/(?:assets|releases|x)/\d+', lambda g: g.group(0).rsplit('/', 1)[0] + '/N',
                                 u.split('?')[0])) for m, u, _ in gh.calls)
    assert ('GET', f'{API}/releases/tags/{TAG}') not in [(m, u) for m, u, _ in gh.calls]      # attempt 1 reads no release
    assert set(methods) == {('GET', API), ('POST', f'{API}/releases'), ('POST', f'{UPL}/releases/N/assets'),
                            ('GET', f'{API}/releases/assets/N'), ('GET', 'https://release-assets.githubusercontent.com/x/N')}
    assert methods[('POST', f'{API}/releases')] == 1 and methods[('GET', API)] == 1
    assert gh.calls[0][:2] == ('GET', API) and gh.calls[1][:2] == ('POST', f'{API}/releases')   # private check first
    names = [a['name'] for a in gh.release['assets']]
    assert len(names) == 318 and names[-2:] == ['sec-once-manifest-a1.json', 'sec-once-manifest-a1.json.sha256']
    assert all(once.ASSET_NAME.fullmatch(n) for n in names)
    by_name = {a['name']: a['_body'] for a in gh.release['assets']}
    for name in names:
        if not name.endswith('.sha256'):
            assert by_name[name + '.sha256'] == f'{hashlib.sha256(by_name[name]).hexdigest()}  {name}\n'.encode()
    assert by_name['companyfacts.zip'] == COMPANYFACTS
    manifest = json.loads(by_name['sec-once-manifest-a1.json'])
    assert manifest['complete'] is True and manifest['release'] == TAG and manifest['run']['run_id'] == RUN_ID
    # the data assets were read back BEFORE the manifest was written; the manifest and its sidecar after it
    assert manifest['verify'] == {'checked': True, 'ok': 316, 'bad': 0} and manifest['classification_complete'] is True
    assert len(manifest['files']) == 158 and all(f['assets'][0]['status'] == 'UPLOADED' for f in manifest['files'])
    assert TOKEN not in json.dumps(manifest) and AGENT not in json.dumps(manifest)
    assert json.loads((tmp_path / 'upload-status.json').read_text())['complete'] is True
    done = []
    assert once.main(['done', '--work', str(tmp_path)], out=done.append, environ={}) == 0
    assert done == ['SECONCE_DONE complete=yes collect=yes classify=yes upload=yes']


def test_upload_failure_is_recorded_and_fails_the_step(tmp_path, token):
    collected(tmp_path)
    gh = FakeGitHub(fail_upload={'fsds-2015q3.zip'})
    code, lines = run_upload(tmp_path, gh)
    assert code == 1
    assert_fixed_lines(lines)
    assert ' assets_failed=1 ' in lines[0] and lines[0].endswith('manifest=OK') and lines[2] == 'SECONCE_ERRORS codes=UPLOAD_HTTP500:1'
    manifest = json.loads(next(a['_body'] for a in gh.release['assets'] if a['name'] == 'sec-once-manifest-a1.json'))
    assert manifest['complete'] is False and manifest['upload_failed'] == 1
    done = []
    assert once.main(['done', '--work', str(tmp_path)], out=done.append, environ={}) == 1
    assert done == ['SECONCE_DONE complete=no collect=yes classify=yes upload=no']


def test_rerun_attempt_resumes_from_its_own_release(tmp_path, token):
    first = tmp_path / 'first'
    collected(first)
    gh = FakeGitHub(fail_upload={'fsds-2015q3.zip', 'submissions.zip.sha256'})
    assert run_upload(first, gh)[0] == 1
    # a fresh runner (attempt 2): the resume check reads only this run's tag and downloads the verified assets
    second = tmp_path / 'second'
    lines = []
    assert once.main(['resume-check', '--work', str(second)], environ=env(2), call=gh.call, open_url=gh.open_url,
                     out=lines.append) == 0
    assert_fixed_lines(lines)
    # attempt 1 left 157 data assets (156 SEC files + the rows file; fsds-2015q3 failed); submissions.zip has no sidecar
    assert lines == ['SECONCE_PREFLIGHT raw_repo=private',
                     'SECONCE_RESUME attempt=2 release=PRESENT assets=157 verified=156 unverified=1']
    gets = [u for m, u, _ in gh.calls if m == 'GET' and '/releases/tags/' in u]
    assert gets == [f'{API}/releases/tags/{TAG}']
    before = len(gh.calls)
    opener = FakeOpener(default=fake_sec)
    code, collect_lines = run_collect(second, opener, env={**env(2), 'SEC_USER_AGENT': AGENT})
    assert code == 0 and sorted(u.rsplit('/', 1)[1] for u, _, _ in opener.calls) == ['2015q3.zip', 'submissions.zip']
    assert collect_lines[0] == 'SECONCE_FILES kind=bulk planned=2 ok=1 resumed=1 failed=0 optional_missing=0 mb=0.0'
    gh.fail_upload = set()
    code, up = run_upload(second, gh, attempt=2)
    assert code == 0, up
    assert up[0].startswith('SECONCE_RELEASE created=no assets_uploaded=3 assets_present=156 assets_failed=0 ')
    new = [a['name'] for a in gh.release['assets']][-6:]
    assert new == ['a2-submissions.zip', 'a2-submissions.zip.sha256', 'fsds-2015q3.zip', 'fsds-2015q3.zip.sha256',
                   'sec-once-manifest-a2.json', 'sec-once-manifest-a2.json.sha256']
    manifest = json.loads(gh.release['assets'][-2]['_body'])
    assert manifest['complete'] is True and manifest['run']['attempt'] == 2
    statuses = Counter(f['assets'][0]['status'] for f in manifest['files'])
    assert statuses == {'PRESENT_VERIFIED': 156, 'UPLOADED': 2}
    assert not any(m in ('PATCH', 'PUT', 'DELETE') for m, _, _ in gh.calls)
    assert sum(1 for m, u, _ in gh.calls[before:] if m == 'POST' and u == f'{API}/releases') == 0


def test_resume_check_attempt_one_checks_privacy_and_reads_no_release(tmp_path, token):
    gh = FakeGitHub()
    lines = []
    assert once.main(['resume-check', '--work', str(tmp_path)], environ=env(1), call=gh.call, open_url=gh.open_url,
                     out=lines.append) == 0
    assert lines == ['SECONCE_PREFLIGHT raw_repo=private',
                     'SECONCE_RESUME attempt=1 release=NOT_READ assets=0 verified=0 unverified=0']
    assert gh.calls == [('GET', API, None)]                    # exactly one call: the repository metadata
    marker = json.loads((tmp_path / once.PREFLIGHT_FILE).read_text())
    assert marker['private'] is True and marker['run_id'] == RUN_ID and marker['attempt'] == 1
    assert once.require_preflight(tmp_path, env(1)) == (RUN_ID, 1)
    with pytest.raises(once.ConfigStop):
        once.require_preflight(tmp_path, env(2))               # a later attempt must check again
    gh.calls.clear()
    lines = []
    assert once.main(['resume-check', '--work', str(tmp_path)], environ=env(2), call=gh.call, open_url=gh.open_url,
                     out=lines.append) == 0
    assert lines == ['SECONCE_PREFLIGHT raw_repo=private',
                     'SECONCE_RESUME attempt=2 release=ABSENT assets=0 verified=0 unverified=0']
    assert gh.calls == [('GET', API, None), ('GET', f'{API}/releases/tags/{TAG}', None)]


@pytest.mark.parametrize('repo, status, reason', [
    ({**PRIVATE_REPO, 'private': False, 'visibility': 'public'}, 200, 'RAW_REPO_NOT_PRIVATE'),
    ({**PRIVATE_REPO, 'private': True, 'visibility': 'internal'}, 200, 'RAW_REPO_NOT_PRIVATE'),
    ({**PRIVATE_REPO, 'private': True, 'visibility': None}, 200, 'RAW_REPO_NOT_PRIVATE'),
    ({k: v for k, v in PRIVATE_REPO.items() if k != 'visibility'}, 200, 'RAW_REPO_NOT_PRIVATE'),
    ({**PRIVATE_REPO, 'private': 'true'}, 200, 'RAW_REPO_NOT_PRIVATE'),
    ({**PRIVATE_REPO, 'full_name': 'kco994553-star/Investment-System1'}, 200, 'RAW_REPO_MISMATCH'),
    (PRIVATE_REPO, 401, 'RAW_REPO_HTTP401'),
    (PRIVATE_REPO, 403, 'RAW_REPO_HTTP403'),
    (PRIVATE_REPO, 404, 'RAW_REPO_HTTP404'),
    (PRIVATE_REPO, 301, 'RAW_REPO_HTTP301'),
    (PRIVATE_REPO, urllib.error.URLError('synthetic'), 'RAW_REPO_UNREACHABLE'),
])
def test_resume_check_stops_unless_the_raw_repository_is_private(tmp_path, token, repo, status, reason):
    for attempt in (1, 2):
        gh = FakeGitHub(repo=repo, repo_status=status)
        lines = []
        assert once.main(['resume-check', '--work', str(tmp_path)], environ=env(attempt), call=gh.call,
                         open_url=gh.open_url, out=lines.append) == 2
        assert lines == [f'SECONCE_STOP reason={reason}'] and gh.calls == [('GET', API, None)]
        assert not (tmp_path / once.PREFLIGHT_FILE).exists() and not (tmp_path / 'resume.json').exists()
    # and so no SEC request is possible
    code, lines = run_collect(tmp_path, NoNetwork(), env={**env(2), 'SEC_USER_AGENT': AGENT}, preflight=False)
    assert code == 2 and lines == ['SECONCE_STOP reason=RAW_PREFLIGHT_MISSING']


def test_stale_marker_is_removed_before_the_check(tmp_path, token):
    write_preflight(tmp_path, env(1))
    gh = FakeGitHub(repo={**PRIVATE_REPO, 'private': False, 'visibility': 'public'})
    assert once.main(['resume-check', '--work', str(tmp_path)], environ=env(1), call=gh.call, open_url=gh.open_url,
                     out=[].append) == 2
    assert not (tmp_path / once.PREFLIGHT_FILE).exists()


def test_upload_checks_privacy_again_before_creating_the_release(tmp_path, token):
    collected(tmp_path)
    gh = FakeGitHub(repo={**PRIVATE_REPO, 'private': False, 'visibility': 'public'})
    code, lines = run_upload(tmp_path, gh)
    assert code == 2 and lines == ['SECONCE_STOP reason=RAW_REPO_NOT_PRIVATE']
    assert gh.calls == [('GET', API, None)] and gh.release is None


def test_missing_token_stops_before_any_call(tmp_path, monkeypatch):
    monkeypatch.delenv('RAW_REPO_TOKEN', raising=False)
    gh = FakeGitHub()
    for command, attempt in (('upload', 1), ('resume-check', 1), ('resume-check', 2)):
        lines = []
        environ = {k: v for k, v in env(attempt).items() if k != 'RAW_REPO_TOKEN'}
        assert once.main([command, '--work', str(tmp_path)], environ=environ, call=gh.call, open_url=gh.open_url,
                         out=lines.append) == 2
        assert lines == ['SECONCE_STOP reason=RAW_REPO_TOKEN_MISSING'] and gh.calls == []


def test_large_files_are_split_and_joined_again(tmp_path, token, monkeypatch):
    collected(tmp_path)
    assert len(COMPANYFACTS) > 200
    monkeypatch.setattr(once, 'SPLIT_LIMIT', 200)
    monkeypatch.setattr(once, 'PART_BYTES', 100)
    gh = FakeGitHub()
    code, lines = run_upload(tmp_path, gh)
    assert code == 0 and lines[1].endswith(' bad=0')
    by_name = {a['name']: a['_body'] for a in gh.release['assets']}
    big = [n for n in by_name if n.endswith('.parts.json')]
    assert big and all(by_name[n + '.sha256'] for n in big)
    index = json.loads(by_name['companyfacts.zip.parts.json'])
    joined = b''.join(by_name[p['name']] for p in index['parts'])
    assert joined == COMPANYFACTS and index['sha256'] == hashlib.sha256(COMPANYFACTS).hexdigest()
    assert all(len(by_name[p['name']]) <= 100 for p in index['parts']) and 'companyfacts.zip' not in by_name
    assert len(index['parts']) == -(-len(COMPANYFACTS) // 100)
    # a re-run attempt joins the parts back from the release
    second = tmp_path / 'second'
    lines = []
    assert once.main(['resume-check', '--work', str(second)], environ=env(2), call=gh.call, open_url=gh.open_url,
                     out=lines.append) == 0
    assert (second / 'files/companyfacts.zip').read_bytes() == COMPANYFACTS
    resume = json.loads((second / 'resume.json').read_text())
    assert {'key': 'companyfacts.zip', 'asset': 'companyfacts.zip.parts.json',
            'sha256': hashlib.sha256(COMPANYFACTS).hexdigest()} in resume['verified']


def test_interrupted_split_upload_is_resumed_under_new_names(tmp_path, token, monkeypatch):
    """Attempt 1 breaks after companyfacts.zip.part01: its part01 (+ sidecar) stay, DELETE is not allowed. Attempt 2 must
    not upload any name that already exists (GitHub answers 422), so the whole split goes under a2-."""
    monkeypatch.setattr(once, 'SPLIT_LIMIT', 200)
    monkeypatch.setattr(once, 'PART_BYTES', 100)
    first = tmp_path / 'first'
    collected(first)
    gh = FakeGitHub(fail_upload={'companyfacts.zip.part02'})
    code, lines = run_upload(first, gh)
    assert code == 1 and 'SECONCE_ERRORS codes=UPLOAD_HTTP500:1' in lines
    names = {a['name'] for a in gh.release['assets']}
    assert {'companyfacts.zip.part01', 'companyfacts.zip.part01.sha256'} <= names
    assert 'companyfacts.zip.parts.json' not in names and 'companyfacts.zip' not in names
    gh.fail_upload = set()
    for attempt in (2, 3):                    # attempt 3 re-runs after a complete attempt 2: nothing left to upload
        work = tmp_path / f'a{attempt}'
        lines = []
        assert once.main(['resume-check', '--work', str(work)], environ=env(attempt), call=gh.call, open_url=gh.open_url,
                         out=lines.append) == 0
        code, collect_lines = run_collect(work, FakeOpener(default=fake_sec), env={**env(attempt), 'SEC_USER_AGENT': AGENT})
        assert code == 0
        code, up = run_upload(work, gh, attempt=attempt)
        assert code == 0, up
        assert 'SECONCE_ERRORS codes=-' in up
    by_name = {a['name']: a['_body'] for a in gh.release['assets']}
    assert len(by_name) == len(gh.release['assets'])                  # no duplicate name was ever accepted
    index = json.loads(by_name['a2-companyfacts.zip.parts.json'])
    assert [p['name'] for p in index['parts']][:2] == ['a2-companyfacts.zip.part01', 'a2-companyfacts.zip.part02']
    assert b''.join(by_name[p['name']] for p in index['parts']) == COMPANYFACTS
    assert not any(n.startswith('a3-') for n in by_name)              # attempt 3 resumed everything from attempt 2
    manifest = json.loads(by_name['sec-once-manifest-a3.json'])
    assert manifest['complete'] is True
    assert Counter(f['assets'][0]['status'] for f in manifest['files']) == {'PRESENT_VERIFIED': 158}


def test_name_taken_covers_every_name_an_upload_creates():
    existing = {'companyfacts.zip.part01': {}, 'companyfacts.zip.part01.sha256': {}, 'fsds-2014q1.zip.sha256': {},
                'a2-submissions.zip.parts.json': {}}
    assert once.name_taken('companyfacts.zip', existing) and once.name_taken('fsds-2014q1.zip', existing)
    assert once.name_taken('a2-submissions.zip', existing) and not once.name_taken('submissions.zip', existing)
    assert not once.name_taken('fsds-2014q2.zip', existing) and not once.name_taken('companyfacts.zi', existing)


def test_resume_prefers_the_newest_attempt_of_a_file(tmp_path, token):
    """Attempt 1 stored an incomplete rows file, attempt 2 a complete one (as a2-...), attempt 10 none. The resume check of
    a later attempt must keep a2- (newest verified copy), not let the plain name overwrite it, and order a10 after a2."""
    def asset(id_, name, body):
        return {'id': id_, 'name': name, 'size': len(body), 'state': 'uploaded', '_body': body}

    def pair(id_, name, body):
        side = once.sidecar_text(hashlib.sha256(body).hexdigest(), name).encode()
        return [asset(id_, name, body), asset(id_ + 1, name + '.sha256', side)]
    old = (json.dumps({'schema': 'sec-once-ticker-mismatch/1', 'complete': False, 'rows': []}) + '\n').encode()
    new = (json.dumps({'schema': 'sec-once-ticker-mismatch/1', 'complete': True, 'rows': []}) + '\n').encode()
    a10 = b'attempt ten copy'
    release = {'id': 77, 'tag_name': TAG, 'assets': pair(1, 'ticker-mismatch-rows.json', old)
               + pair(3, 'a2-ticker-mismatch-rows.json', new)
               + pair(5, 'fsds-2014q1.zip', FSDS) + pair(7, 'a10-fsds-2014q1.zip', a10)
               + [asset(9, 'a2-fsds-2014q1.zip', b'no sidecar')]}
    gh = FakeGitHub(release=release)
    lines = []
    assert once.main(['resume-check', '--work', str(tmp_path)], environ=env(11), call=gh.call, open_url=gh.open_url,
                     out=lines.append) == 0
    assert lines[-1] == 'SECONCE_RESUME attempt=11 release=PRESENT assets=5 verified=2 unverified=0'
    assert (tmp_path / 'files' / once.ROWS_FILE).read_bytes() == new
    assert (tmp_path / 'files/fsds-2014q1.zip').read_bytes() == a10
    verified = {r['key']: r['asset'] for r in json.loads((tmp_path / 'resume.json').read_text())['verified']}
    assert verified == {once.ROWS_FILE: 'a2-ticker-mismatch-rows.json', 'fsds-2014q1.zip': 'a10-fsds-2014q1.zip'}
    read = [u for m, u, _ in gh.calls if u.startswith(f'{API}/releases/assets/')]
    assert f'{API}/releases/assets/1' not in read and f'{API}/releases/assets/5' not in read   # older copies not read


def test_manifest_is_not_complete_when_the_classification_is_not(tmp_path, token):
    collected(tmp_path)
    once.write_json(tmp_path / 'files' / once.ROWS_FILE, {'schema': 'sec-once-ticker-mismatch/1', 'complete': False,
                                                         'rows': [], 'summary': {}})
    gh = FakeGitHub()
    code, lines = run_upload(tmp_path, gh)
    assert code == 0 and lines[1] == 'SECONCE_VERIFY assets=318 ok=318 bad=0'      # the upload itself is fine
    manifest = json.loads(next(a['_body'] for a in gh.release['assets'] if a['name'] == 'sec-once-manifest-a1.json'))
    assert manifest['complete'] is False and manifest['classification_complete'] is False
    assert manifest['collect_complete'] is True
    done = []
    assert once.main(['done', '--work', str(tmp_path)], out=done.append, environ={}) == 1
    assert done == ['SECONCE_DONE complete=no collect=yes classify=no upload=yes']


def test_redirect_to_another_host_is_refused(tmp_path, token):
    gh = FakeGitHub()
    client = once.ReleaseClient(TAG, call=gh.call, open_url=lambda request, timeout=None: (_ for _ in ()).throw(
        urllib.error.HTTPError(request.full_url, 302, 'Found', {'Location': 'https://example.org/x'}, None)))
    client._adopt({'id': 77, 'tag_name': TAG, 'assets': [{'id': 5, 'name': 'fsds-2014q1.zip'}]})
    with pytest.raises(once.ReleaseRefused) as refused:
        client.stream(5, lambda chunk: None)
    assert refused.value.code == 'ASSET_REDIRECT_INVALID'


def test_done_without_files_is_not_complete(tmp_path):
    lines = []
    assert once.main(['done', '--work', str(tmp_path)], out=lines.append, environ={}) == 1
    assert lines == ['SECONCE_DONE complete=no collect=no classify=no upload=no']


# ---- static: workflow and files ---------------------------------------------------------------------------------------------
GUARD = ("    if: github.event_name == 'push' && github.ref == 'refs/heads/claude/sec-once-collect-run' && "
         "github.repository == 'kco994553-star/Investment-System1'\n")


def jobs_of(text):
    """{job name: job text} of the workflow."""
    body = text.split('\njobs:\n', 1)[1]
    parts = re.split(r'\n?^  ([a-z_-]+):\n', body, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def steps_of(job):
    """Step texts of one job, without the comment lines that introduce the next step."""
    return [re.sub(r'(?:\n *#[^\n]*)+\s*$', '', step) for step in job.split('\n    steps:\n', 1)[1].split('\n      - ')]


def test_workflow_runs_only_on_the_run_branch_push_with_one_secret_per_step():
    text = WORKFLOW.read_text()
    assert 'on:\n  push:\n    branches: [claude/sec-once-collect-run]\npermissions:\n  contents: read\n' in text
    for forbidden in ('workflow_dispatch', 'schedule:', 'pull_request', 'workflow_run', 'repository_dispatch',
                      'actions/upload', 'actions/cache', 'actions/download', 'GITHUB_STEP_SUMMARY', 'git push',
                      'git commit', 'always()', 'RAW_REPO_READ_TOKEN', ': write', 'id-token', 'continue-on-error',
                      'tags:', 'branches-ignore', 'secrets.KIS', 'secrets.kis', 'secrets.GITHUB_TOKEN', 'github.token',
                      'secrets: inherit', 'toJSON(secrets'):
        assert forbidden not in text, forbidden
    assert text.count('permissions:') == 1 and 'concurrency:\n  group: sec-once-collect\n  cancel-in-progress: false\n' in text
    jobs = jobs_of(text)
    assert list(jobs) == ['offline-tests', 'collect']
    # both jobs check event, branch and repository; collect runs only after the offline tests passed
    assert all(job.startswith(GUARD) or job.startswith('    needs: offline-tests\n' + GUARD) for job in jobs.values())
    assert jobs['collect'].startswith('    needs: offline-tests\n' + GUARD) and 'needs:' not in jobs['offline-tests']
    assert text.count(GUARD) == 2
    for job in jobs.values():
        assert '    runs-on: ubuntu-24.04\n' in job
        assert job.count('actions/checkout@') == job.count('persist-credentials: false') == 1
    assert int(re.search(r'\n    timeout-minutes: (\d+)\n', jobs['offline-tests'])[1]) <= 30
    job_minutes = int(re.search(r'\n    timeout-minutes: (\d+)\n', jobs['collect'])[1])
    assert job_minutes <= 180
    # offline tests: pytest on a runner of their own, no Secret; a failure names the test only (no assertion text,
    # no exception message, no warning text reaches the public log)
    tests_job = jobs['offline-tests']
    assert 'secrets' not in tests_job and 'python -m pip install pytest==9.1.1\n' in tests_job
    assert len(re.findall(r'^ +(?:run: )?python -m pip ', tests_job, re.M)) == 1
    pytest_line = next(line for line in tests_job.splitlines() if 'python -m pytest' in line)
    for flag in (' -v ', ' --tb=no ', ' -rN ', ' -p no:warnings ', ' -p no:cacheprovider '):
        assert flag in pytest_line, flag
    assert ' -q ' not in pytest_line and '-r ' not in pytest_line.replace('-rN', '')
    for name in ('tests/test_sec_once_collect.py', 'tests/test_sec_once_ticker_mismatch.py', 'tests/test_fv3_pit_ticker_measure.py'):
        assert name in pytest_line
    # the Secret job: no pip, every tool started with python -I -S (no site-packages, no .pth hooks, no PYTHONPATH)
    collect_job = jobs['collect']
    assert 'pip' not in collect_job and 'pytest' not in collect_job and 'PYTHONPATH' not in collect_job
    runs = re.findall(r'\n        run: (.+)', collect_job)
    assert len(runs) == 6 and all(r.startswith('python -I -S implementation/tools/measure_once/') for r in runs)
    code_lines = [line for line in collect_job.splitlines() if not line.strip().startswith('#')]
    assert not any(re.search(r'\bpython(?!-version:)(?!3? -I -S )', line.replace('setup-python', ''))
                   for line in code_lines)
    steps = steps_of(collect_job)
    holders = [s for s in steps if 'secrets.' in s]
    assert text.count('secrets.') == 4 and len(holders) == 4
    assert text.count('secrets.SEC_USER_AGENT') == 2 and text.count('secrets.RAW_REPO_TOKEN') == 2
    for step in holders:
        assert ('SEC_USER_AGENT' in step) != ('RAW_REPO_TOKEN' in step)      # never both in one step
        assert step.count('secrets.') == 1
        assert re.search(r'\n        timeout-minutes: \d+\n', step)
    step_minutes = sum(int(m) for m in re.findall(r'\n        timeout-minutes: (\d+)\n', collect_job))
    assert step_minutes + 5 <= job_minutes
    tool = 'python -I -S implementation/tools/measure_once/sec_once_collect.py'
    work = '--work "$RUNNER_TEMP/sec-once"'
    sec = [s for s in holders if 'SEC_USER_AGENT' in s]
    raw = [s for s in holders if 'RAW_REPO_TOKEN' in s]
    assert sec[0].rstrip().endswith(f'run: {tool} collect {work}') and '\n        id: collect\n' in sec[0]
    assert sec[1].rstrip().endswith(f'run: python -I -S implementation/tools/measure_once/sec_once_ticker_mismatch.py {work}')
    assert raw[0].rstrip().endswith(f'run: {tool} resume-check {work}')
    assert raw[1].rstrip().endswith(f'run: {tool} upload {work}')
    plan = next(s for s in steps if f'{tool} plan {work}' in s)
    done = next(s for s in steps if f'{tool} done {work}' in s)
    order = [steps.index(s) for s in (plan, raw[0], sec[0], sec[1], raw[1], done)]
    assert order == sorted(order) and steps.index(done) == len(steps) - 1
    assert 'secrets' not in plan and 'secrets' not in done
    # a classifier failure must not discard the collection: upload (and done) run whenever collect succeeded
    keep = "        if: ${{ !cancelled() && steps.collect.outcome == 'success' }}\n"
    assert keep in raw[1] and keep in done and collect_job.count('        if: ') == 2
    for step in (plan, raw[0], sec[0], sec[1]):
        assert '        if: ' not in step
    daily = (REPO / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    pins = re.findall(r'uses: (\S+)', text)
    assert len(pins) == 4 and all(re.fullmatch(r'actions/[a-z-]+@[0-9a-f]{40}', p) and f'uses: {p}' in daily for p in pins)


def test_no_address_shaped_literal_in_the_new_files():
    spec = importlib.util.spec_from_file_location('autonomy_gate_a_guard_for_sec_once', ROOT / 'tools/autonomy_gate_a_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    for path in (TOOL, ROOT / 'tools/measure_once/sec_once_ticker_mismatch.py', Path(__file__),
                 ROOT / 'tests/test_sec_once_ticker_mismatch.py', WORKFLOW,
                 ROOT / 'docs/lab/SEC_ONCE_COLLECTION_PLAN_20261101.md'):
        assert guard.email_patterns(path.read_bytes()) == Counter(), path.name
