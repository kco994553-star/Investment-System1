"""One-time Alpaca SIP small-sample measurement (tools/measure_once/alpaca_sample_once.py): offline checks with fakes only
(no network, no key, no token).

- the fixed sample (40 securities, 10 categories, consistent legs, UNVERIFIED entries named) and the plan (66 series);
- the checkpoint days against the repository's NYSE rule calendar (research.pit_filings) and the settings doc rule;
- the exact Alpaca URL allow-list, refused redirects, key headers, pause, retries, 401 / 403 / 429 / request-cap stops;
- pagination by next_page_token (joined pages, loop / no-progress / cap refused), page parsing (null bars, NA never 0);
- evaluation helpers (fit, gaps, overlap, month-end state, event day differences, ticker lineage codes);
- end to end on a fake Alpaca and a fake GitHub: fixed lines only, never a price, volume, key or token, no decimal number;
  counts per category; the raw archive and its sha256 manifest go only to the create-only release alpaca-sample-v1-<run_id>;
- missing keys / token / runner / run id and failed preflights stop before any Alpaca request;
- the workflow's shape (push to the run branch only, Secrets in one step, pinned actions, no sinks).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
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

from investment_system.research import pit_filings

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TOOL = ROOT / 'tools/measure_once/alpaca_sample_once.py'
WORKFLOW = REPO / '.github/workflows/alpaca-sample-once.yml'
PLAN_DOC = ROOT / 'docs/lab/ALPACA_SAMPLE_PLAN_20261101.md'

_spec = importlib.util.spec_from_file_location('alpaca_sample_once', TOOL)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

AT = chr(64)   # no address-shaped literal in this file (repository email guard)
KEY = 'SYNTHETIC' + 'KEYID' + '0123'
SECRET = 'SYNTHETIC' + 'SECRET' + '456789'
TOKEN = 'synthetic-raw-token'
RUN_ID = '424242'
TAG = 'alpaca-sample-v1-' + RUN_ID
ENV = {'GITHUB_ACTIONS': 'true', 'APCA_API_KEY_ID': KEY, 'APCA_API_SECRET_KEY': SECRET, 'RAW_REPO_TOKEN': TOKEN,
       'GITHUB_RUN_ID': RUN_ID, 'GITHUB_SHA': 'a' * 40}
SECURITIES, BY_SYMBOL = m.load_sample()
PLAN = m.plan(SECURITIES)
SESSIONS = [m.WINDOW_START + timedelta(days=i) for i in range((m.WINDOW_END - m.WINDOW_START).days + 1)]
SESSIONS = [d for d in SESSIONS if pit_filings.is_session(d)]


# ---- sample and plan -----------------------------------------------------------------------------------------------------
def test_sample_shape_and_plan_counts():
    assert len(SECURITIES) == 40 and len(PLAN) == 66
    by_category = Counter(info['category'] for info in SECURITIES.values())
    assert set(by_category) == set(m.CATEGORIES) and all(n >= 1 for n in by_category.values())
    assert by_category == {'CONTROL_LARGE': 2, 'ETF_AUX': 1, 'DELISTED_ACQUIRED': 7, 'DELISTED_OTHER': 4, 'TICKER_CHANGE': 5,
                           'MULTI_CLASS': 6, 'ADR': 3, 'REIT': 3, 'SMALL_CAP_NEAR_THRESHOLD': 4, 'IPO_IN_WINDOW': 5}
    assert Counter(s['mode'] for s in PLAN) == {'RAW': 46, 'ASOF_PIT': 11, 'ASOF_CURRENT': 9}
    assert sorted(sid for sid, info in SECURITIES.items() if info['check'] == 'UNVERIFIED') == [
        'DA06', 'DA07', 'MC03', 'MC04', 'MC06', 'SC01', 'SC02', 'SC03', 'SC04']
    # every TICKER_CHANGE entry requests both symbols; every multi-class issuer each class
    for sid, info in SECURITIES.items():
        if info['category'] == 'TICKER_CHANGE':
            assert len({leg[0] for leg in info['legs']}) == 2
    raw_symbols = [s['symbol'] for s in PLAN if s['mode'] == 'RAW']
    assert {'GOOGL', 'GOOG', 'BRK.A', 'BRK.B', 'UA', 'UAA', 'UA.C'} <= set(raw_symbols) and len(set(raw_symbols)) == 46
    shared = next(s for s in PLAN if s['id'] == 'RAW:UA')
    assert shared['sids'] == ['MC05', 'MC06']


def test_sample_carries_no_price_and_each_note_names_its_event():
    for sid, category, legs, note, check in m.SAMPLE:
        assert not re.search(r'[0-9]\.[0-9]', note) and '$' not in note, sid
        for _, first, end in legs:
            for day in (first, end):
                assert day is None or day in note or category == 'IPO_IN_WINDOW' and day in note, (sid, day)
        if check == 'WEB_CHECKED':
            assert re.search(r'\((?:ICE|SEC|Cboe|company|Nasdaq|Prologis|GlobeNewswire|Alpaca)', note), sid


@pytest.mark.parametrize('broken, code', [
    ((('XX01', 'CONTROL_LARGE', (('AAA', None, None),), 'n', 'RECALL'),) * 2, 'sample_entry'),             # duplicate sid
    ((('XX01', 'NOT_A_CATEGORY', (('AAA', None, None),), 'n', 'RECALL'),), 'sample_entry'),
    ((('XX01', 'ADR', (('AAA', None, None),), 'n', 'MAYBE'),), 'sample_entry'),
    ((('XX01', 'ADR', (('aaa', None, None),), 'n', 'RECALL'),), 'sample_leg'),
    ((('XX01', 'ADR', (('AAA', '2018-01-02', '2017-01-02'),), 'n', 'RECALL'),), 'sample_leg'),
    ((('XX01', 'ADR', (('AAA', None, '2018-01-02'), ('BBB', '2017-01-02', None)), 'n', 'RECALL'),), 'sample_leg_order'),
    ((('XX01', 'ADR', (('AAA', '2020-01-02', None),), 'n', 'RECALL'),), 'sample_outside_window'),
    ((('XX01', 'ADR', (('AAA', None, None),), 'n', 'RECALL'), ('XX02', 'ADR', (('AAA', None, None),), 'n', 'RECALL')),
     'symbol_overlap'),
])
def test_inconsistent_samples_are_refused(broken, code):
    with pytest.raises(ValueError, match=code):
        m.load_sample(broken, (), ())


def test_checkpoints_follow_the_rule_calendar():
    def third_monday(year):
        first = date(year, 2, 1)
        return first + timedelta(days=(0 - first.weekday()) % 7 + 14)
    for year, t in m.T_DAYS:
        expected_t = third_monday(year)
        while not pit_filings.is_session(expected_t):
            expected_t += timedelta(days=1)
        expected_s = expected_t - timedelta(days=1)
        while not pit_filings.is_session(expected_s):
            expected_s -= timedelta(days=1)
        assert t == expected_t and dict(m.S_DAYS)[year] == expected_s
    for day in m.MONTH_ENDS:
        nxt = day + timedelta(days=1)
        while not pit_filings.is_session(nxt):
            nxt += timedelta(days=1)
        assert pit_filings.is_session(day) and nxt.month != day.month
    assert [d.strftime('%Y-%m') for d in m.MONTH_ENDS] == ['2018-%02d' % i for i in range(2, 13)] + ['2019-01', '2019-02']
    assert SESSIONS[0] == m.FIRST_SESSION and SESSIONS[-1] == m.LAST_SESSION
    # the settings doc table (section 2) for the years it lists
    assert dict(m.T_DAYS)[2018] == date(2018, 2, 20) and dict(m.S_DAYS)[2019] == date(2019, 2, 15)


# ---- routes and client ---------------------------------------------------------------------------------------------------
ALLOWED = {(s['symbol'], s['asof']) for s in PLAN}


@pytest.mark.parametrize('symbol, asof, token', [('AAPL', '-', None), ('BRK.A', '-', None), ('UA.C', '-', None),
                                                 ('PCLN', '2018-02-20', None), ('META', m.CURRENT_ASOF, None),
                                                 ('AAPL', '-', 'QUFQTHxEfDIwMTYtMDEtMDRUMDU6MDA6MDBa=='),
                                                 ('AAPL', '-', 'a+b/c_d-e')])
def test_allow_list_accepts_planned_requests(symbol, asof, token):
    url = m.build_url(symbol, asof, token)
    assert m.checked_alpaca_url(url, ALLOWED) == url
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert query == {'timeframe': '1Day', 'start': '2016-01-01T00:00:00-05:00', 'end': '2019-03-31T23:59:59-04:00',
                     'adjustment': 'raw', 'feed': 'sip', 'limit': '10000', 'sort': 'asc', 'asof': asof,
                     **({'page_token': token} if token else {})}


BASE = m.build_url('AAPL', '-')


@pytest.mark.parametrize('url', [
    BASE.replace('https://', 'http://'),
    BASE.replace('data.alpaca.markets', 'paper-api.alpaca.markets'),
    BASE.replace('data.alpaca.markets', 'api.alpaca.markets'),
    BASE.replace('data.alpaca.markets', 'data.alpaca.markets.example.org'),
    BASE.replace('data.alpaca.markets', 'data.alpaca.markets:8443'),
    BASE.replace('https://', 'https://user' + AT),
    BASE.replace('/v2/stocks/AAPL/bars', '/v2/stocks/TSLA/bars'),           # not planned
    BASE.replace('/v2/stocks/AAPL/bars', '/v2/stocks/bars'),                # multi-symbol route
    BASE.replace('/v2/stocks/AAPL/bars', '/v2/stocks/AAPL/trades'),
    BASE.replace('/v2/', '/v1beta1/'),
    BASE.replace('feed=sip', 'feed=iex'),
    BASE.replace('adjustment=raw', 'adjustment=all'),
    BASE.replace('timeframe=1Day', 'timeframe=1Min'),
    BASE.replace('limit=10000', 'limit=9999'),
    BASE.replace('asof=-', 'asof=2018-02-20'),                              # planned symbol, unplanned asof
    BASE.replace('start=2016', 'start=2015'),
    BASE + '&extra=1', BASE + '&asof=-', BASE + '#x', BASE + '&page_token=a%20b',
    m.build_url('AAPL', '-') .replace('&sort=asc', ''),
    BASE + '\r\nHost: example.org', '', None, 'file:///etc/passwd',
    'https://api.github.com/repos/kco994553-star/investment-system1-raw',
])
def test_allow_list_refuses_everything_else(url):
    with pytest.raises(ValueError):
        m.checked_alpaca_url(url, ALLOWED)
    client, sleeps, opener = make_client([])
    with pytest.raises(ValueError):
        client.get(url)
    assert opener.calls == [] and client.counts['total'] == 0 and sleeps == []


def test_redirects_are_refused():
    assert any(isinstance(h, m._RejectRedirects) for h in m.build_opener().handlers)
    with pytest.raises(m.FetchError) as exc:
        m._RejectRedirects().redirect_request(urllib.request.Request(BASE), None, 302, 'Found', {}, 'https://example.org/x')
    assert exc.value.code == 'REDIRECT_REJECTED'


class FakeResponse:
    def __init__(self, body, headers=None):
        self._body, self.headers, self.status = io.BytesIO(body), dict(headers or {}), 200

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_error(code, headers=None):
    return urllib.error.HTTPError(BASE, code, 'synthetic', headers or {}, io.BytesIO(b'{"message":"synthetic"}'))


class FakeOpener:
    """Serves a script of responses / exceptions in order, or a function of the URL."""

    def __init__(self, script):
        self.script, self.calls = script, []

    def open(self, request, timeout=None):
        self.calls.append((request.full_url, request.get_header('Apca-api-key-id'), request.get_header('Apca-api-secret-key')))
        item = self.script(request.full_url) if callable(self.script) else self.script.pop(0)
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


def make_client(script, clock=None):
    sleeps, opener = [], FakeOpener(script)
    client = m.AlpacaClient(KEY, SECRET, ALLOWED, opener=opener, sleep=sleeps.append, clock=clock or Clock(0.0))
    return client, sleeps, opener


def test_headers_pause_and_body():
    client, sleeps, opener = make_client([FakeResponse(b'{"ok":1}')])
    assert client.get(BASE) == b'{"ok":1}'
    assert opener.calls == [(BASE, KEY, SECRET)] and sleeps == [m.SLEEP_S] and client.counts['total'] == 1
    assert 60 / m.SLEEP_S <= 100 < 200   # well under Alpaca's free limit of 200 requests per minute


def test_retries_and_stops():
    client, sleeps, _ = make_client([http_error(503), http_error(502), FakeResponse(b'x')])
    assert client.get(BASE) == b'x' and sleeps == [0.6, 2.0, 0.6, 6.0, 0.6] and client.counts['retries'] == 2
    client, _, _ = make_client([http_error(500)] * 3)
    with pytest.raises(m.FetchError) as exc:
        client.get(BASE)
    assert exc.value.code == 'HTTP500' and client.counts['total'] == 3
    client, sleeps, _ = make_client([http_error(429, {'Retry-After': '45'}), FakeResponse(b'x')])
    assert client.get(BASE) == b'x' and sleeps == [0.6, 45.0, 0.6]
    client, sleeps, _ = make_client([http_error(429, {'Retry-After': '9000'}), http_error(429), http_error(429),
                                     http_error(429)])
    with pytest.raises(m.FetchError) as exc:
        client.get(BASE)
    assert exc.value.code == 'HTTP429' and sleeps == [0.6, 60.0, 0.6, 30.0, 0.6, 60.0, 0.6]
    client, _, _ = make_client([TimeoutError('slow'), urllib.error.URLError('down'), FakeResponse(b'x')])
    assert client.get(BASE) == b'x' and client.counts['network'] == 2
    for status in (401, 403):
        client, _, opener = make_client([http_error(status)] * 3)
        with pytest.raises(m.Stop) as stop:
            client.get(BASE)
        assert stop.value.reason == 'AUTH_REJECTED' and len(opener.calls) == 1
    for status in (400, 404, 422):
        client, _, opener = make_client([http_error(status)] * 3)
        with pytest.raises(m.FetchError) as exc:
            client.get(BASE)
        assert exc.value.code == f'HTTP{status}' and len(opener.calls) == 1


def test_request_cap_wall_clock_and_429_budget():
    client, _, _ = make_client(lambda url: FakeResponse(b'x'))
    client.counts['total'] = m.MAX_REQUESTS
    with pytest.raises(m.Stop) as stop:
        client.get(BASE)
    assert stop.value.reason == 'REQUEST_CAP'
    client, _, _ = make_client(lambda url: FakeResponse(b'x'), clock=Clock(0.0, m.WALL_CLOCK_S + 1))
    with pytest.raises(m.Stop) as stop:
        client.get(BASE)
    assert stop.value.reason == 'WALL_CLOCK'
    client, _, _ = make_client(lambda url: http_error(429))
    client.counts['http429'] = m.STOP_AFTER_429 - 1
    with pytest.raises(m.Stop) as stop:
        client.get(BASE)
    assert stop.value.reason == 'HTTP429_REPEATED'


def test_size_cap_and_encoding():
    client, _, _ = make_client([FakeResponse(b'y' * (m.PAGE_CAP + 1))])
    with pytest.raises(m.FetchError) as exc:
        client.get(BASE)
    assert exc.value.code == 'SIZE_CAP'
    client, _, _ = make_client([FakeResponse(b'x', {'Content-Encoding': 'gzip'})])
    with pytest.raises(m.FetchError) as exc:
        client.get(BASE)
    assert exc.value.code == 'ENCODING_NOT_SUPPORTED'


def test_missing_or_invalid_keys():
    assert not m.valid_key('') and not m.valid_key('short') and not m.valid_key('has space inside') \
        and not m.valid_key(KEY + '\n') and m.valid_key(KEY) and m.valid_key(SECRET)


# ---- page parsing and pagination -----------------------------------------------------------------------------------------
def bar(day, value=101.25):
    return {'t': day.isoformat() + 'T05:00:00Z', 'o': value, 'h': value + 1, 'l': value - 1, 'c': value + 0.5,
            'v': 1234567, 'n': 4321, 'vw': value + 0.25}


def page(symbol, bars, token=None):
    return json.dumps({'bars': bars, 'symbol': symbol, 'next_page_token': token}).encode()


def test_parse_page():
    rows, token, echo = m.parse_page(page('AAPL', [bar(date(2016, 1, 4)), bar(date(2016, 1, 5), 99)]), 'AAPL')
    assert rows == [(date(2016, 1, 4), (101.25, 102.25, 100.25, 101.75)), (date(2016, 1, 5), (99.0, 100.0, 98.0, 99.5))]
    assert token is None and echo == 'SAME'
    assert m.parse_page(b'{"bars":null,"symbol":"AAPL","next_page_token":null}', 'AAPL') == ([], None, 'SAME')
    nulls = dict(bar(date(2016, 1, 4)), o=None, c=0, h=float('nan'), l=True)
    assert m.parse_page(page('AAPL', [nulls]), 'AAPL')[0] == [(date(2016, 1, 4), (None, None, None, None))]   # NA, not 0
    assert m.parse_page(page('BKNG', []), 'PCLN', mapped=True)[2] == 'OTHER'
    for body, code in [(b'not json', 'JSON'), (b'[]', 'SCHEMA'), (page('MSFT', []), 'SYMBOL_MISMATCH'),
                       (b'{"bars":{},"symbol":"AAPL"}', 'SCHEMA'), (page('AAPL', [], 'bad token!'), 'PAGE_TOKEN'),
                       (page('AAPL', [{'o': 1}]), 'BAR_SCHEMA'), (page('AAPL', [dict(bar(date(2016, 1, 4)), t='x')]), 'BAR_TIME'),
                       (page('AAPL', [dict(bar(date(2016, 1, 4)), t='2016-01-04T05:00:00')]), 'BAR_TIME'),
                       (page('AAPL', [bar(date(2019, 4, 1))]), 'OUT_OF_WINDOW')]:
        with pytest.raises(ValueError, match=code):
            m.parse_page(body, 'AAPL')


def test_pagination_joins_pages_and_refuses_loops():
    series = {'symbol': 'AAPL', 'asof': '-'}
    days = SESSIONS[:6]
    client, _, opener = make_client([FakeResponse(page('AAPL', [bar(d) for d in days[:3]], 'tok1')),
                                     FakeResponse(page('AAPL', [bar(d) for d in days[3:]], None))])
    result = m.fetch_series(client, series)
    assert result['status'] == 'DATA' and sorted(result['bars']) == days and len(result['pages']) == 2
    assert 'page_token=tok1' in opener.calls[1][0] and 'page_token' not in opener.calls[0][0]
    client, _, _ = make_client([FakeResponse(page('AAPL', [bar(days[0])], 'tok1')),
                                FakeResponse(page('AAPL', [bar(days[1])], 'tok1'))])
    assert m.fetch_series(client, series)['status'] == 'BAD_PAGINATION'
    client, _, _ = make_client([FakeResponse(page('AAPL', [], 'tok1'))])
    assert m.fetch_series(client, series)['status'] == 'BAD_PAGINATION'
    client, _, _ = make_client([FakeResponse(page('AAPL', [bar(days[i])], f'tok{i}')) for i in range(m.MAX_PAGES)])
    assert m.fetch_series(client, series)['status'] == 'BAD_PAGE_CAP'
    client, _, _ = make_client([FakeResponse(page('AAPL', [bar(days[1]), bar(days[0])]))])
    assert m.fetch_series(client, series)['status'] == 'BAD_ORDER'
    client, _, _ = make_client([http_error(404)])
    result = m.fetch_series(client, series)
    assert result == {'status': 'ERR_HTTP404', 'bars': {}, 'pages': [], 'echo': '-'}
    client, _, _ = make_client([FakeResponse(page('AAPL', None))])
    assert m.fetch_series(client, series)['status'] == 'NO_DATA'


# ---- evaluation helpers --------------------------------------------------------------------------------------------------
D = date


def test_fit_gaps_overlap_monthend():
    spans = [(D(2016, 1, 1), D(2017, 1, 1))]
    days = {D(2016, 1, 4), D(2016, 6, 1), D(2016, 12, 30)}
    assert m.fit(days, spans) == 'MATCH'
    assert m.fit(days | {D(2017, 1, 3)}, spans) == 'MATCH'                     # within the boundary tolerance
    assert m.fit(days | {D(2017, 2, 1)}, spans) == 'MATCH+OUTSIDE'
    assert m.fit(days, spans + [(D(2018, 1, 1), D(2018, 2, 1))]) == 'PARTIAL'
    assert m.fit(set(), spans) == 'NO_DATA' and m.fit(set(), []) == 'NONE_EXPECTED' and m.fit(days, []) == 'OUTSIDE_ONLY'
    ref = {D(2016, 1, 4), D(2016, 1, 5), D(2016, 1, 6)}
    assert m.gaps({D(2016, 1, 4), D(2016, 1, 6)}, spans, ref) == 'SOME'
    assert m.gaps(ref, spans, ref) == 'NONE' and m.gaps(ref, spans, set()) == 'NA' and m.gaps(set(), spans, ref) == 'NA'
    a = {D(2016, 1, 4): (1.0, 2.0, 0.5, 1.5), D(2016, 1, 5): (1.0, 2.0, 0.5, 1.5)}
    assert m.overlap(a, dict(a)) == 'SAME_BARS' and m.overlap(a, {}) == 'NO_OVERLAP'
    assert m.overlap(a, {d: (9.0, 9.0, 9.0, 9.0) for d in a}) == 'DIFFERENT_BARS'
    assert m.overlap(a, {D(2016, 1, 4): a[D(2016, 1, 4)], D(2016, 1, 5): (9.0,) * 4}) == 'PARTLY_SAME'
    assert m.monthend_state(['OK', 'OK', '-']) == 'FULL' and m.monthend_state(['OK', 'MISS']) == 'PARTIAL'
    assert m.monthend_state(['MISS', 'BAD']) == 'NONE' and m.monthend_state(['-', 'UNEXP']) == 'NA+UNEXP'
    assert m.monthend_state(['OK', 'ERR']) == 'ERR'


def ideal_bars(spans, salt=0):
    return {d: (100.0 + salt + i / 100, 101.0 + salt, 99.0 + salt, 100.5 + salt + i / 100)
            for i, d in enumerate(SESSIONS) if m.inside(d, spans)}


def raw_ideal():
    """{symbol: result} where every RAW series has exactly its symbol-level bars (last trading day = day before the event)."""
    out = {}
    for n, s in enumerate(p for p in PLAN if p['mode'] == 'RAW'):
        out[s['symbol']] = {'status': 'DATA', 'bars': ideal_bars(m.series_spans(s, SECURITIES, BY_SYMBOL), n), 'pages': [],
                            'echo': 'SAME'}
    return out


def test_events_day_differences():
    raw = raw_ideal()
    got = {(sid, sym, kind): diff for sid, info in SECURITIES.items() for sym, kind, _, diff in m.events(sid, info, raw, BY_SYMBOL)}
    assert got[('DA01', 'EMC', 'END')] == -1                     # merger closed 2016-09-07 (Wed): last bar 09-06
    assert got[('DA02', 'WFM', 'END')] == -3                     # closed Monday 2017-08-28: last bar Friday
    assert got[('IP05', 'LYFT', 'START')] == 0 and got[('IP01', 'TWLO', 'START')] == 0
    assert got[('TC01', 'PCLN', 'RENAME_OUT')] == -1 and got[('TC01', 'BKNG', 'RENAME_IN')] == 0
    assert got[('DO02', 'BTU', 'END')] == -1 and got[('DO02', 'BTU', 'RELIST')] == 0
    assert got[('MC05', 'UA', 'RENAME_OUT')] == -1 and got[('MC06', 'UA', 'RENAME_IN')] == 0   # UA swaps classes 2016-12-07
    assert got[('DA07', 'FOXA', 'END')] == -1                    # last bar before the reusing issuer's first day
    assert ('TC05', 'FB', 'RENAME_OUT') not in got               # the rename lies after the window
    assert all(isinstance(v, int) for v in got.values())
    raw['EMC'] = {'status': 'DATA', 'bars': {}, 'pages': [], 'echo': 'SAME'}
    raw['WFM'] = {'status': 'ERR_HTTP404', 'bars': {}, 'pages': [], 'echo': '-'}
    got = {(sid, sym, kind): diff for sid, info in SECURITIES.items() for sym, kind, _, diff in m.events(sid, info, raw, BY_SYMBOL)}
    assert got[('DA01', 'EMC', 'END')] is None and got[('DA02', 'WFM', 'END')] == 'ERR'


def test_lineage_codes():
    raw = raw_ideal()
    info = SECURITIES['TC01']
    assert m.lineage_code(info, raw, BY_SYMBOL) == 'PIT_SYMBOLS'
    assert m.lineage_code(SECURITIES['TC05'], raw, BY_SYMBOL) == 'PIT_SYMBOLS'   # FB only; META none before 2022
    backfilled = dict(raw, PCLN={'status': 'NO_DATA', 'bars': {}, 'pages': [], 'echo': 'SAME'},
                      BKNG={'status': 'DATA', 'bars': ideal_bars([(m.WINDOW_START, m.WINDOW_AFTER)]), 'pages': [], 'echo': 'SAME'})
    assert m.lineage_code(info, backfilled, BY_SYMBOL) == 'CURRENT_SYMBOL_ONLY'
    current = dict(raw, FB={'status': 'NO_DATA', 'bars': {}, 'pages': [], 'echo': 'SAME'},
                   META={'status': 'DATA', 'bars': ideal_bars([(m.WINDOW_START, m.WINDOW_AFTER)]), 'pages': [], 'echo': 'SAME'})
    assert m.lineage_code(SECURITIES['TC05'], current, BY_SYMBOL) == 'CURRENT_SYMBOL_ONLY'
    both = dict(raw, BKNG=backfilled['BKNG'])
    assert m.lineage_code(info, both, BY_SYMBOL) == 'OVERLAPPING_SYMBOLS'
    missing = dict(raw, BKNG={'status': 'NO_DATA', 'bars': {}, 'pages': [], 'echo': 'SAME'})
    assert m.lineage_code(info, missing, BY_SYMBOL) == 'MISSING_SYMBOL'
    assert m.lineage_code(info, dict(raw, BKNG={'status': 'ERR_HTTP422', 'bars': {}, 'pages': [], 'echo': '-'}),
                          BY_SYMBOL) == 'ERR'


# ---- fake services for the end-to-end runs --------------------------------------------------------------------------------
def alpaca_service(variant=None):
    """URL -> response: every series answers its expected bars (RAW: symbol-level legs; mapped: lineage / other issuer)."""
    by_key = {(s['symbol'], s['asof']): s for s in PLAN}

    def serve(url):
        parts = urllib.parse.urlsplit(url)
        symbol = parts.path.split('/')[3]
        query = dict(urllib.parse.parse_qsl(parts.query))
        series = by_key[(symbol, query['asof'])]
        spans = m.series_spans(series, SECURITIES, BY_SYMBOL)
        if variant:
            changed = variant(series, spans)
            if isinstance(changed, BaseException):
                raise changed
            spans = changed
        salt = sum(map(ord, symbol)) % 97            # each symbol its own synthetic values
        bars = [bar(d, 100 + salt + i / 100) for i, d in enumerate(SESSIONS) if m.inside(d, spans)]
        half = len(bars) // 2
        if series['id'] == 'RAW:SPY':                      # one series answers in two pages
            if 'page_token' not in query:
                return FakeResponse(page(symbol, bars[:half], 'synthetic-page-2'))
            return FakeResponse(page(symbol, bars[half:]))
        return FakeResponse(page(symbol, bars or None))
    return serve


class FakeGithub:
    def __init__(self, private=True, tag_exists=False, fail_upload=False, corrupt=False):
        self.private, self.tag_exists, self.fail_upload, self.corrupt = private, tag_exists, fail_upload, corrupt
        self.calls, self.assets = [], {}

    def __call__(self, method, url, *, data=None, headers=None, auth=True, opener=None):
        self.calls.append((method, url, auth))
        repo = 'https://api.github.com/repos/kco994553-star/investment-system1-raw'
        if (method, url) == ('GET', repo):
            return 200, {}, json.dumps({'private': self.private}).encode()
        if (method, url) == ('GET', repo + '/releases/tags/' + TAG):
            return (200, {}, b'{"id": 5}') if self.tag_exists else (404, {}, b'{}')
        if (method, url) == ('POST', repo + '/releases'):
            payload = json.loads(data)
            assert payload['tag_name'] == payload['name'] == TAG and payload['draft'] is False
            self.tag_exists = True
            return 201, {}, json.dumps({'id': 77, 'tag_name': TAG}).encode()
        if method == 'POST' and url.startswith('https://uploads.github.com/repos/kco994553-star/investment-system1-raw/releases/77/assets?name='):
            if self.fail_upload:
                return 500, {}, b'{}'
            name = urllib.parse.unquote(url.split('name=', 1)[1])
            self.assets[name] = data
            return 201, {}, json.dumps({'id': 900 + len(self.assets), 'name': name}).encode()
        if (method, url) == ('GET', repo + '/releases/assets/901'):
            return 302, {'Location': 'https://objects.githubusercontent.com/synthetic-signed'}, b''
        if (method, url) == ('GET', 'https://objects.githubusercontent.com/synthetic-signed'):
            assert auth is False
            body = self.assets[TAG + '.zip']
            return 200, {}, (body + b'x' if self.corrupt else body)
        raise AssertionError('unexpected GitHub route')


def run_main(environ=ENV, variant=None, github=None, argv=()):
    lines, github = [], github or FakeGithub()
    opener = FakeOpener(alpaca_service(variant))
    code = m.main(list(argv), environ=dict(environ), opener=opener, github_call=github, sleep=lambda s: None,
                  clock=Clock(0.0), out=lines.append, now=datetime(2026, 11, 2, tzinfo=timezone.utc))
    return code, lines, opener, github


def fields(line):
    return dict(word.split('=', 1) for word in line.split(' ')[1:])


def assert_value_free(lines):
    text = '\n'.join(lines)
    assert not re.search(r'[0-9]\.[0-9]', text)                  # no decimal number anywhere (prices are synthetic x.yz)
    assert '1234567' not in text and '4321' not in text           # no volume / trade count
    for secret in (KEY, SECRET, TOKEN, 'synthetic-page-2', 'objects.githubusercontent', 'alpaca.markets', 'https:'):
        assert secret not in text
    for line in lines:
        assert re.fullmatch(r'ALPSAMPLE_[A-Z_]+( [a-z][a-z0-9_]*=[A-Za-z0-9_.:+/,=-]+)+', line), line


def test_end_to_end_ideal_data():
    code, lines, opener, github = run_main()
    assert code == 0
    assert_value_free(lines)
    assert len(opener.calls) == 67 and all(c[1:] == (KEY, SECRET) for c in opener.calls)   # 66 series, SPY in two pages
    kinds = Counter(line.split(' ', 1)[0] for line in lines)
    assert kinds['ALPSAMPLE_START'] == 1 and kinds['ALPSAMPLE_SERIES'] == 66 and kinds['ALPSAMPLE_CATEGORY'] == 10
    assert kinds['ALPSAMPLE_CHECKPOINT'] == 21 and kinds['ALPSAMPLE_CLASSES'] == 3 and kinds['ALPSAMPLE_STORAGE'] == 1
    assert lines[-1] == f'ALPSAMPLE_STORAGE status=STORED release={TAG} files=68 roundtrip=SHA256_MATCH'
    series = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert all(s['status'] == 'DATA' or s['fit'] == 'NONE_EXPECTED' for s in series.values())
    assert series['RAW:AAPL'] == {'id': 'RAW:AAPL', 'sid': 'CL01', 'cat': 'CONTROL_LARGE', 'mode': 'RAW', 'expect': 'SYMBOL',
                                  'status': 'DATA', 'fit': 'MATCH', 'first': 'AT_START', 'last': 'AT_END', 'gaps': 'NONE',
                                  't_open': 'OK,OK,OK,OK', 's_close': 'OK,OK,OK,OK', 'monthend': 'FULL', 'echo': 'SAME'}
    assert series['RAW:EMC']['t_open'] == 'OK,-,-,-' and series['RAW:EMC']['monthend'] == 'NA'
    assert series['RAW:LYFT']['first'] == 'LATER' and series['RAW:LYFT']['t_open'] == '-,-,-,-'
    assert series['RAW:META']['status'] == 'NO_DATA' and series['RAW:META']['fit'] == 'NONE_EXPECTED'
    assert series['ASOF20180220:PCLN']['fit'] == 'MATCH' and series['ASOF20261030:DOW']['fit'] == 'NONE_EXPECTED'
    cats = {fields(l)['cat']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CATEGORY ')}
    assert cats['CONTROL_LARGE'] == {'cat': 'CONTROL_LARGE', 'securities': '2', 'symbols': '2', 'symbols_with_data': '2',
                                     'symbols_no_data': '0', 'symbols_error': '0', 't_open': '8/8', 't_unexpected': '0',
                                     's_close': '8/8', 's_unexpected': '0', 'monthend': '26/26', 'monthend_unexpected': '0',
                                     'complete': '2', 'gapless': '2/2'}
    assert cats['DELISTED_ACQUIRED']['t_open'] == '18/18'   # EMC 1, WFM 2, DOW 2, MON 3, TWX 3, DNB 3 (gone before T2019), FOXA 4
    assert cats['TICKER_CHANGE']['symbols_no_data'] == '1'  # META: nothing under it before 2022
    assert all(c['complete'] == c['securities'] and c['t_unexpected'] == c['s_unexpected'] == '0' for c in cats.values())
    checkpoint = {fields(l)['cp']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CHECKPOINT ')}
    assert checkpoint['T2018']['field'] == 'open' and checkpoint['ME201902']['field'] == 'close'
    assert checkpoint['T2016']['expected'] == checkpoint['T2016']['ok'] == '34'   # 40 minus five IPOs and class C (UA.C)
    lineage = {fields(l)['sid']: fields(l) for l in lines if l.startswith('ALPSAMPLE_LINEAGE ')}
    assert set(lineage) == {'TC01', 'TC02', 'TC03', 'TC04', 'TC05', 'MC05', 'MC06', 'DA03', 'DA07', 'DO02'}
    assert lineage['TC01'] == {'sid': 'TC01', 'cat': 'TICKER_CHANGE', 'raw': 'PIT_SYMBOLS', 'asof_pit': 'MATCH',
                               'asof_current': 'MATCH', 'overlap': 'NO_OVERLAP'}
    assert lineage['DO02']['asof_pit'] == 'MATCH,MATCH' and lineage['DA03']['raw'] == 'SINGLE_LEG'
    classes = [fields(l) for l in lines if l.startswith('ALPSAMPLE_CLASSES ')]
    assert [c['overlap'] for c in classes] == ['DIFFERENT_BARS', 'DIFFERENT_BARS', 'DIFFERENT_BARS']
    events = [fields(l) for l in lines if l.startswith('ALPSAMPLE_EVENT ')]
    assert {e['bar_vs_event_days'] for e in events} <= {'0', '-1', '-2', '-3', '-4'}
    requests = fields(next(l for l in lines if l.startswith('ALPSAMPLE_REQUESTS ')))
    assert requests['total'] == '67' and requests['pages'] == '67' and requests['stopped'] == 'NONE'


def test_raw_archive_goes_only_to_the_new_private_release():
    code, lines, _, github = run_main()
    assert code == 0
    methods = [(c[0], c[1].split('?')[0]) for c in github.calls]
    repo = 'https://api.github.com/repos/kco994553-star/investment-system1-raw'
    assert methods == [('GET', repo), ('GET', repo + '/releases/tags/' + TAG), ('GET', repo + '/releases/tags/' + TAG),
                       ('POST', repo + '/releases'),
                       ('POST', 'https://uploads.github.com/repos/kco994553-star/investment-system1-raw/releases/77/assets'),
                       ('POST', 'https://uploads.github.com/repos/kco994553-star/investment-system1-raw/releases/77/assets'),
                       ('GET', repo + '/releases/assets/901'), ('GET', 'https://objects.githubusercontent.com/synthetic-signed')]
    assert set(github.assets) == {TAG + '.zip', TAG + '.zip.sha256'}
    archive = github.assets[TAG + '.zip']
    assert github.assets[TAG + '.zip.sha256'] == f'{hashlib.sha256(archive).hexdigest()}  {TAG}.zip\n'.encode()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        manifest = json.loads(z.read('manifest.json'))
        assert manifest['schema'] == 'alpaca-sample-v1-manifest/1' and manifest['run_id'] == RUN_ID
        assert manifest['code_sha'] == 'a' * 40 and manifest['stopped'] == 'NONE' and len(manifest['sample']) == 40
        assert manifest['source']['feed'] == 'sip' and 'non-commercial' in manifest['source']['terms']
        files = [p for e in manifest['series'] for p in e['pages']]
        assert len(files) == 67 and len(z.namelist()) == 68
        for entry in files:
            assert hashlib.sha256(z.read(entry['file'])).hexdigest() == entry['sha256']
        text = z.read('manifest.json').decode()
        assert KEY not in text and SECRET not in text and TOKEN not in text
        assert manifest['summary_lines'] == [l for l in lines if not l.startswith(('ALPSAMPLE_START', 'ALPSAMPLE_REQUESTS',
                                                                                   'ALPSAMPLE_STORAGE'))]
    assert run_main()[0] == 0      # deterministic archive bytes for the same responses
    assert run_main()[3].assets[TAG + '.zip'] == archive


def test_hard_case_variants_are_reported_by_category():
    def variant(series, spans):
        if series['id'] == 'RAW:BKNG':                     # current symbol carries the old symbol's history
            return [(m.WINDOW_START, m.WINDOW_AFTER)]
        if series['id'] == 'RAW:PCLN':
            return []
        if series['id'] == 'RAW:SHLD':                     # history stops a month early
            return [(m.WINDOW_START, date(2018, 9, 24))]
        if series['id'] == 'ASOF20180220:FOXA':            # the mapping merges the reusing issuer
            return [(m.WINDOW_START, m.WINDOW_AFTER)]
        if series['id'] == 'RAW:KIRK':                     # a hole of one month
            return [(m.WINDOW_START, date(2018, 5, 1)), (date(2018, 6, 1), m.WINDOW_AFTER)]
        if series['id'] == 'RAW:BRK.A':
            return urllib.error.HTTPError(BASE, 422, 'synthetic', {}, io.BytesIO(b'{}'))
        return spans
    code, lines, _, _ = run_main(variant=variant)
    assert code == 0
    assert_value_free(lines)
    series = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert series['RAW:BKNG']['fit'] == 'MATCH+OUTSIDE' and series['RAW:PCLN']['status'] == 'NO_DATA'
    assert series['RAW:BRK.A']['status'] == 'ERR_HTTP422' and series['RAW:BRK.A']['t_open'] == 'ERR,ERR,ERR,ERR'
    assert series['RAW:KIRK']['gaps'] == 'SOME' and series['RAW:KIRK']['monthend'] == 'PARTIAL'
    lineage = {fields(l)['sid']: fields(l) for l in lines if l.startswith('ALPSAMPLE_LINEAGE ')}
    assert lineage['TC01']['raw'] == 'CURRENT_SYMBOL_ONLY' and lineage['DA07']['asof_pit'] == 'MATCH+OUTSIDE'
    events = {(fields(l)['sid'], fields(l)['event']): fields(l) for l in lines if l.startswith('ALPSAMPLE_EVENT ')}
    assert events[('DO03', 'END')]['bar_vs_event_days'] == '-33' and events[('DO03', 'END')]['event_day'] == '2018-10-24'
    assert events[('TC01', 'RENAME_OUT')]['bar_vs_event_days'] == 'NONE'
    cats = {fields(l)['cat']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CATEGORY ')}
    assert cats['TICKER_CHANGE']['t_open'] == '17/20' and cats['TICKER_CHANGE']['complete'] == '4'   # PCLN: T2016..T2018
    assert cats['MULTI_CLASS']['symbols_error'] == '1' and cats['SMALL_CAP_NEAR_THRESHOLD']['gapless'] == '3/4'
    assert cats['DELISTED_OTHER']['monthend'] == '33/34'   # BTU 13, SHLD 8, WIN 13; SHLD 2018-09-28 missing (ended 09-21)
    checkpoint = {fields(l)['cp']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CHECKPOINT ')}
    assert checkpoint['T2017']['error'] == '1' and checkpoint['ME201805']['missing'] == '1'


def test_stops_before_any_alpaca_request():
    cases = [({k: v for k, v in ENV.items() if k != 'GITHUB_ACTIONS'}, 'RUNNER_REQUIRED'),
             (dict(ENV, APCA_API_KEY_ID=''), 'ALPACA_KEYS_MISSING'),
             ({k: v for k, v in ENV.items() if k != 'APCA_API_SECRET_KEY'}, 'ALPACA_KEYS_MISSING'),
             (dict(ENV, APCA_API_KEY_ID='short'), 'ALPACA_KEYS_INVALID'),
             (dict(ENV, APCA_API_SECRET_KEY=SECRET + '\r\nX: 1'), 'ALPACA_KEYS_INVALID'),
             (dict(ENV, RAW_REPO_TOKEN=' '), 'RAW_REPO_TOKEN_MISSING'),
             (dict(ENV, GITHUB_RUN_ID='12a'), 'RUN_ID_INVALID'),
             ({k: v for k, v in ENV.items() if k != 'GITHUB_RUN_ID'}, 'RUN_ID_INVALID')]
    for environ, reason in cases:
        code, lines, opener, github = run_main(environ)
        assert (code, lines, opener.calls) == (2, [f'ALPSAMPLE_STOP reason={reason}'], []), reason
        assert github.calls == []
    for github, reason in [(FakeGithub(private=False), 'PRIVATE_STORAGE_PREFLIGHT_FAILED'),
                           (FakeGithub(tag_exists=True), 'RELEASE_TAG_EXISTS')]:
        code, lines, opener, github = run_main(github=github)
        assert (code, lines, opener.calls) == (2, [f'ALPSAMPLE_STOP reason={reason}'], [])
        assert all(c[0] == 'GET' for c in github.calls)


def test_auth_rejection_stops_and_storage_failures_exit_3():
    def variant(series, spans):
        if series['id'] == 'RAW:WFM':
            return urllib.error.HTTPError(BASE, 401, 'synthetic', {}, io.BytesIO(b'{}'))
        return spans
    code, lines, opener, github = run_main(variant=variant)
    assert code == 3
    assert_value_free(lines)
    requests = fields(next(l for l in lines if l.startswith('ALPSAMPLE_REQUESTS ')))
    assert requests['stopped'] == 'AUTH_REJECTED' and requests['http401'] == '1' and requests['series_done'] == '4'
    series = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert series['RAW:MON']['status'] == 'NOT_RUN' and series['RAW:EMC']['status'] == 'DATA'
    assert lines[-1].startswith('ALPSAMPLE_STORAGE status=STORED ')             # partial raw pages are still kept privately
    for github, code_ in [(FakeGithub(fail_upload=True), 'ASSET_UPLOAD_FAILED'), (FakeGithub(corrupt=True), 'ROUNDTRIP_MISMATCH')]:
        code, lines, _, _ = run_main(github=github)
        assert code == 3 and lines[-1] == f'ALPSAMPLE_STORAGE status=FAILED code={code_}'


def test_release_name_and_routes_are_fixed():
    assert m.release_tag('123') == 'alpaca-sample-v1-123'
    for bad in ('', '12a', '1' * 21, '../1', ' 1', None):
        with pytest.raises(m.StorageError):
            m.release_tag(bad)
    for bad in ('alpaca-sample-v1-', 'alpaca-sample-v2-1', 'kis-1', 'alpaca-sample-v1-1x', None):
        with pytest.raises(m.StorageError):
            m.RawStore(bad, FakeGithub())
    store = m.RawStore(TAG, FakeGithub())
    repo = 'https://api.github.com/repos/kco994553-star/investment-system1-raw'
    up = 'https://uploads.github.com/repos/kco994553-star/investment-system1-raw/releases/77/assets?name='
    assert store.allowed('GET', repo) and store.allowed('POST', repo + '/releases')
    assert store.allowed('GET', repo + '/releases/tags/' + TAG) and store.allowed('POST', up + TAG + '.zip')
    assert store.allowed('POST', up + TAG + '.zip.sha256') and store.allowed('GET', repo + '/releases/assets/901')
    for method, url in [('GET', repo + '/releases'), ('GET', repo + '/releases/latest'),
                        ('GET', repo + '/releases/tags/alpaca-sample-v1-1'), ('GET', repo + '/releases/tags/kis-raw-1'),
                        ('DELETE', repo + '/releases/77'), ('PATCH', repo + '/releases/77'), ('POST', up + 'other.zip'),
                        ('POST', up + TAG + '.zip&x=1'), ('DELETE', repo + '/releases/assets/901'), ('PUT', repo),
                        ('GET', 'https://api.github.com/repos/kco994553-star/Investment-System1'),
                        ('GET', repo + '/contents/x'), ('POST', repo + '/git/refs')]:
        assert not store.allowed(method, url), (method, url)
        with pytest.raises(m.StorageError, match='ROUTE_NOT_ALLOWED'):
            store.http(method, url)
    github = FakeGithub(tag_exists=True)    # create-only: an existing tag is never reused or written to
    with pytest.raises(m.StorageError, match='RELEASE_TAG_EXISTS'):
        m.RawStore(TAG, github).store(b'zip')
    assert [c[0] for c in github.calls] == ['GET']


def test_plan_mode_and_script_without_environment(tmp_path):
    code, lines, opener, github = run_main(argv=['--plan'])
    assert code == 0 and opener.calls == [] and github.calls == []
    assert lines[0] == ('ALPSAMPLE_PLAN securities=40 symbols=46 series=66 raw=46 asof_pit=11 asof_current=9 '
                        'pages_expected=66 max_requests=150 pace_ms=600')
    assert len(lines) == 11 and run_main(argv=['--other'])[1] == ['ALPSAMPLE_STOP reason=USAGE']
    env = {k: v for k, v in os.environ.items() if k not in ENV and k.lower() not in
           ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9')   # a request could not leave anyway
    run = subprocess.run([sys.executable, str(TOOL)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert (run.returncode, run.stdout, run.stderr) == (2, 'ALPSAMPLE_STOP reason=RUNNER_REQUIRED\n', '')
    run = subprocess.run([sys.executable, str(TOOL), '--plan'], cwd=tmp_path, env=env, capture_output=True, text=True,
                         timeout=60)
    assert run.returncode == 0 and run.stdout.startswith('ALPSAMPLE_PLAN securities=40 ') and run.stderr == ''
    assert list(tmp_path.iterdir()) == []


# ---- static: workflow, plan document, files -------------------------------------------------------------------------------
def test_workflow_runs_once_on_the_run_branch_push_with_the_secrets_in_one_step():
    text = WORKFLOW.read_text()
    assert 'on:\n  push:\n    branches: [claude/alpaca-sample-once-run]\npermissions:\n  contents: read\n' in text
    for forbidden in ('workflow_dispatch', 'schedule:', 'pull_request', 'actions/upload', 'actions/cache', 'actions/download',
                      'GITHUB_STEP_SUMMARY', 'git push', 'git commit', 'always()', ': write', 'id-token', 'RAW_REPO_READ',
                      'claude/alpaca-sample-once]', 'KIS', 'kis'):
        assert forbidden not in text, forbidden
    assert text.count('permissions:') == 1 and 'concurrency:\n  group: alpaca-sample-once-' in text
    assert "if: github.ref == 'refs/heads/claude/alpaca-sample-once-run'" in text
    jobs = re.findall(r'\n  ([a-z_-]+):\n', '\n' + text.split('\njobs:\n', 1)[1])
    assert jobs == ['measure'] and int(re.search(r'\n    timeout-minutes: (\d+)\n', text)[1]) <= 20
    steps = text.split('\n    steps:\n', 1)[1].split('\n      - ')
    holders = [s for s in steps if 'secrets.' in s]
    assert text.count('secrets.') == 3 and len(holders) == 1
    for name in ('APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'RAW_REPO_TOKEN'):
        assert f'{name}: ${{{{ secrets.{name} }}}}' in holders[0]
    assert holders[0].rstrip().endswith('python implementation/tools/measure_once/alpaca_sample_once.py')
    assert 'umask 077' in holders[0] and int(re.search(r'timeout-minutes: (\d+)', holders[0])[1]) <= 15
    offline = next(s for s in steps if 'pytest' in s)
    assert 'tests/test_alpaca_sample_once.py' in offline and '--tb=no' in offline and 'secrets.' not in offline
    assert steps.index(offline) < steps.index(holders[0])
    daily = (REPO / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    pins = re.findall(r'uses: (\S+)', text)
    assert pins and all(re.fullmatch(r'actions/[a-z-]+@[0-9a-f]{40}', p) and f'uses: {p}' in daily for p in pins)
    assert text.count('actions/checkout@') == text.count('persist-credentials: false') == 1


def test_plan_document_names_the_sample_and_the_limits():
    text = PLAN_DOC.read_text(encoding='utf-8')
    for needle in ('alpaca-sample-v1-', 'IEX', '비상업', '66', '40', 'claude/alpaca-sample-once-run', 'UNVERIFIED'):
        assert needle in text, needle
    for sid, info in SECURITIES.items():
        for symbol, _, _ in info['legs']:
            assert symbol in text, symbol
    assert not re.search(r'[0-9]\.[0-9]{2}', text)        # no price-like number


def test_no_address_shaped_literal_in_the_new_files():
    spec = importlib.util.spec_from_file_location('autonomy_gate_a_guard_for_alpaca', ROOT / 'tools/autonomy_gate_a_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    for path in (TOOL, Path(__file__), WORKFLOW, PLAN_DOC):
        assert guard.email_patterns(path.read_bytes()) == Counter(), path.name
