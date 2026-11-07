"""One-time Alpaca SIP small-sample measurement (tools/measure_once/alpaca_sample_once.py): offline checks with fakes only
(no network, no key, no token).

- the fixed sample (40 securities, 10 categories, consistent legs, the leg end convention, UNVERIFIED entries named) and the
  plan (67 series);
- the checkpoint days (T, S, 37 month-ends) against the repository's NYSE rule calendar (research.pit_filings);
- the exact Alpaca URL allow-list, refused redirects, key headers, pause, retries (waits capped by the clock), 401 / 403 /
  429 / request-cap stops;
- pagination by next_page_token (joined pages, loop / no-progress / cap refused), page parsing (null bars, NA never 0);
- evaluation helpers: presence codes (public) and value-comparison codes (private: vs_raw, legs_vs_raw, overlap, OK / BAD),
  event day differences, ticker lineage codes (reused symbols never read as CURRENT_SYMBOL_ONLY);
- the public-line allow-table: every printed line matches LINE_SPECS; synthetic prices with distinctive integer parts never
  appear in any int or str form; no value-comparison code is printed (they go only to the private manifest);
- asof mapping vs fallback: a dated series that returns its plain series unchanged is told apart privately (SAME_AS_RAW) and,
  where presence can show it, publicly (Peabody old / new equity, Under Armour class C);
- end to end on a fake Alpaca and a fake GitHub; counts per category; the raw archive and its sha256 manifest go only to the
  create-only release alpaca-sample-v1-<run_id>; privacy re-checked before creating; bounded storage retries inside a time
  budget; after creation only the created release id and own asset id are reachable;
- missing keys / token / runner / run id and failed preflights stop before any Alpaca request;
- the workflow's shape (offline test in its own job, the Secret job `needs:` it, no pip there, `python -I -S`).
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
GH_REPO = 'https://api.github.com/repos/kco994553-star/investment-system1-raw'
GH_UP = 'https://uploads.github.com/repos/kco994553-star/investment-system1-raw/releases/'
PRIVATE_CODES = {'SAME_BARS', 'DIFFERENT_BARS', 'PARTLY_SAME', 'NO_OVERLAP', 'SAME_AS_RAW', 'DIFFERS', 'SAME_ON_COMMON_DAYS',
                 'NO_RAW_BARS', 'NO_ASOF_BARS', 'OK', 'BAD'}


# ---- sample and plan -----------------------------------------------------------------------------------------------------
def test_sample_shape_and_plan_counts():
    assert len(SECURITIES) == 40 and len(PLAN) == 67
    by_category = Counter(info['category'] for info in SECURITIES.values())
    assert set(by_category) == set(m.CATEGORIES) and all(n >= 1 for n in by_category.values())
    assert by_category == {'CONTROL_LARGE': 2, 'ETF_AUX': 1, 'DELISTED_ACQUIRED': 7, 'DELISTED_OTHER': 4, 'TICKER_CHANGE': 5,
                           'MULTI_CLASS': 6, 'ADR': 3, 'REIT': 3, 'SMALL_CAP': 4, 'IPO_IN_WINDOW': 5}
    assert Counter(s['mode'] for s in PLAN) == {'RAW': 47, 'ASOF_PIT': 11, 'ASOF_CURRENT': 9}
    assert sorted(sid for sid, info in SECURITIES.items() if info['check'] == 'UNVERIFIED') == ['MC03', 'MC06', 'SC04']
    for sid, info in SECURITIES.items():
        if info['category'] == 'TICKER_CHANGE':
            assert len({leg[0] for leg in info['legs']}) == 2
    raw_symbols = [s['symbol'] for s in PLAN if s['mode'] == 'RAW']
    assert {'GOOGL', 'GOOG', 'BRK.A', 'BRK.B', 'UA', 'UAA', 'UA.C', 'TFCFA'} <= set(raw_symbols) and len(set(raw_symbols)) == 47
    shared = next(s for s in PLAN if s['id'] == 'RAW:UA')
    assert shared['sids'] == ['MC05', 'MC06']
    # corrected facts: last sessions on the event day (DOW, TWX), 21CF's last session as TFCFA, SHPG halted from 2019-01-07
    assert SECURITIES['DA03']['legs'] == (('DOW', None, date(2017, 9, 1)),)
    assert SECURITIES['DA05']['legs'] == (('TWX', None, date(2018, 6, 15)),)
    assert SECURITIES['DA07']['legs'] == (('FOXA', None, date(2019, 3, 19)), ('TFCFA', date(2019, 3, 19), date(2019, 3, 20)))
    assert SECURITIES['AD03']['legs'] == (('SHPG', None, date(2019, 1, 7)),)
    # Peabody: each dated request expects only the equity listed on its asof date
    btu = {s['id']: s['legs'] for s in PLAN if s['symbol'] == 'BTU' and s['mode'] != 'RAW'}
    assert btu == {'ASOF20160216:BTU': (0,), 'ASOF20180220:BTU': (1,), 'ASOF20261030:BTU': (1,)}


def test_leg_ends_are_the_first_day_no_longer_traded():
    """Convention: `end` is the first day the security no longer traded under the symbol, so it is a day the market was
    open (the last bar is the session before it); a leg start is a session too."""
    for sid, info in SECURITIES.items():
        for _, first, end in info['legs']:
            for day in (first, end):
                if day is not None and m.WINDOW_START < day <= m.WINDOW_END:
                    assert pit_filings.is_session(day), (sid, day)


def test_sample_carries_no_price_and_each_note_names_its_event():
    for sid, category, legs, note, check in m.SAMPLE:
        assert not re.search(r'[0-9]\.[0-9]', note) and '$' not in note, sid
        for _, first, end in legs:
            for day in (first, end):
                assert day is None or day in note, (sid, day)
        if check == 'WEB_CHECKED':
            assert re.search(r'\((?:ICE|SEC|Cboe|company|Nasdaq|Prologis|GlobeNewswire|Alpaca|OCC)', note), sid
        if check == 'UNVERIFIED':
            assert 'UNVERIFIED' in note, sid
    notes = {entry[0]: entry[3] for entry in m.SAMPLE}
    assert 'UA.C at Alpaca is UNVERIFIED' in notes['MC06'] and 'BRK.A' in notes['MC03']
    assert '2019-03-18' in notes['DA07'] and '2019-01-04' in notes['AD03'] and '2019-02-07' in notes['DA06']


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


@pytest.mark.parametrize('mapped, code', [
    ((('DO02', 'BTU', '2016-02-16', 'LINEAGE', (2,)),), 'mapped_legs'),
    ((('DO02', 'BTU', '2016-02-16', 'LINEAGE', ()),), 'mapped_legs'),
    ((('DA07', 'FOXA', m.CURRENT_ASOF, 'OTHER_ISSUER', (0,)),), 'mapped_legs'),
    ((('TC01', 'PCLN', '2018-02-20', 'LINEAGE', (1,)),), 'mapped_symbol'),
    ((('TC01', 'PCLN', '2018-02-20', 'GUESS', None),), 'mapped'),
])
def test_inconsistent_mapped_requests_are_refused(mapped, code):
    with pytest.raises(ValueError, match=code):
        m.load_sample(m.SAMPLE, m.OTHER_ISSUER_LEGS, mapped)


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
    months = {'monthend_2016w': ['2016-%02d' % i for i in range(2, 13)] + ['2017-01'],
              'monthend_2017w': ['2017-%02d' % i for i in range(2, 13)] + ['2018-01'],
              'monthend': ['2018-%02d' % i for i in range(2, 13)] + ['2019-01', '2019-02']}
    for group, days in m.MONTH_END_GROUPS:
        assert [d.strftime('%Y-%m') for d in days] == months[group], group
        for day in days:   # the last NYSE session of its month
            nxt = day + timedelta(days=1)
            while not pit_filings.is_session(nxt):
                nxt += timedelta(days=1)
            assert pit_filings.is_session(day) and nxt.month != day.month, day
    assert len(m.checkpoints()) == 8 + 37 and len({cp for cp, *_ in m.checkpoints()}) == 45
    assert SESSIONS[0] == m.FIRST_SESSION and SESSIONS[-1] == m.LAST_SESSION
    assert dict(m.T_DAYS)[2018] == date(2018, 2, 20) and dict(m.S_DAYS)[2019] == date(2019, 2, 15)


# ---- routes and client ---------------------------------------------------------------------------------------------------
ALLOWED = {(s['symbol'], s['asof']) for s in PLAN}


@pytest.mark.parametrize('symbol, asof, token', [('AAPL', '-', None), ('BRK.A', '-', None), ('UA.C', '-', None),
                                                 ('TFCFA', '-', None), ('PCLN', '2018-02-20', None),
                                                 ('META', m.CURRENT_ASOF, None),
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
    BASE.replace('adjustment=raw', 'adjustment=dividend'),
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


def test_backoff_waits_never_run_past_the_collection_clock():
    # start 0, loop-top check 0, then the wait is computed with 1 s left: it shrinks to 1 s
    client, sleeps, _ = make_client([http_error(429, {'Retry-After': '60'}), FakeResponse(b'x')],
                                    clock=Clock(0.0, 0.0, m.WALL_CLOCK_S - 1.0))
    assert client.get(BASE) == b'x' and sleeps == [0.6, 1.0, 0.6]
    client, sleeps, _ = make_client([http_error(503), FakeResponse(b'x')], clock=Clock(0.0, 0.0, m.WALL_CLOCK_S + 5.0))
    with pytest.raises(m.Stop) as stop:
        client.get(BASE)
    assert stop.value.reason == 'WALL_CLOCK' and sleeps == [0.6]
    assert m.WALL_CLOCK_S + m.TIMEOUT_S * 2 + m.PREFLIGHT_BUDGET_S + m.STORAGE_BUDGET_S < 20 * 60   # the step limit


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
VOLUME, TRADES = 1234567, 4321


def bar(day, value=101.25):
    return {'t': day.isoformat() + 'T05:00:00Z', 'o': value, 'h': value + 1, 'l': value - 1, 'c': value + 0.5,
            'v': VOLUME, 'n': TRADES, 'vw': value + 0.25}


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
    assert m.fetch_series(client, series)['status'] == 'INVALID_PAGINATION'
    client, _, _ = make_client([FakeResponse(page('AAPL', [], 'tok1'))])
    assert m.fetch_series(client, series)['status'] == 'INVALID_PAGINATION'
    client, _, _ = make_client([FakeResponse(page('AAPL', [bar(days[i])], f'tok{i}')) for i in range(m.MAX_PAGES)])
    assert m.fetch_series(client, series)['status'] == 'INVALID_PAGE_CAP'
    client, _, _ = make_client([FakeResponse(page('AAPL', [bar(days[1]), bar(days[0])]))])
    assert m.fetch_series(client, series)['status'] == 'INVALID_ORDER'
    client, _, _ = make_client([FakeResponse(b'not json')])
    assert m.fetch_series(client, series)['status'] == 'INVALID_JSON'
    client, _, _ = make_client([http_error(404)])
    result = m.fetch_series(client, series)
    assert result == {'status': 'ERR_HTTP404', 'bars': {}, 'pages': [], 'echo': '-'}
    client, _, _ = make_client([FakeResponse(page('AAPL', None))])
    assert m.fetch_series(client, series)['status'] == 'NO_DATA'


# ---- evaluation helpers --------------------------------------------------------------------------------------------------
D = date


def res(bars, status='DATA'):
    return {'status': status, 'bars': bars, 'pages': [], 'echo': 'SAME'}


def test_presence_codes_and_value_codes():
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
    # presence: a bar with an invalid value is still a bar (validity is private)
    invalid = res({D(2016, 1, 4): (None, None, None, None)})
    assert m.presence_state(invalid, spans, D(2016, 1, 4)) == 'BAR' and m.value_state(invalid, spans, D(2016, 1, 4), 0) == 'BAD'
    assert m.presence_state(invalid, spans, D(2016, 1, 5)) == 'MISS' and m.presence_state(invalid, [], D(2016, 1, 4)) == 'UNEXP'
    assert m.presence_state(res({}, 'ERR_HTTP404'), spans, D(2016, 1, 4)) == 'ERR'
    assert m.monthend_state(['BAR', 'BAR', '-']) == 'FULL' and m.monthend_state(['BAR', 'MISS']) == 'PARTIAL'
    assert m.monthend_state(['MISS', 'BAD']) == 'NONE' and m.monthend_state(['-', 'UNEXP']) == 'NA+UNEXP'
    assert m.monthend_state(['BAR', 'ERR']) == 'ERR' and m.monthend_state(['OK', 'BAD']) == 'PARTIAL'
    assert m.days_vs({1, 2}, {1, 2}) == 'SAME_DAYS' and m.days_vs({1}, {1, 2}) == 'FEWER_DAYS'
    assert m.days_vs({1, 2, 3}, {1, 2}) == 'MORE_DAYS' and m.days_vs({1, 3}, {1, 2}) == 'OTHER_DAYS'
    a = {D(2016, 1, 4): (1.0, 2.0, 0.5, 1.5), D(2016, 1, 5): (1.0, 2.0, 0.5, 1.5)}
    b = {d: (9.0, 9.0, 9.0, 9.0) for d in a}
    assert m.class_days(res(a), res(b)) == 'SAME_DAYS' and m.class_days(res(a), res({})) == 'ONE_EMPTY'
    assert m.common_days(res(a), res(b)) == 'SOME' and m.common_days(res(a), res({})) == 'NONE'
    assert m.common_days(res(a), res({}, 'NOT_RUN')) == 'ERR'
    # private value codes
    assert m.overlap(a, dict(a)) == 'SAME_BARS' and m.overlap(a, {}) == 'NO_OVERLAP'
    assert m.overlap(a, b) == 'DIFFERENT_BARS'
    assert m.overlap(a, {D(2016, 1, 4): a[D(2016, 1, 4)], D(2016, 1, 5): (9.0,) * 4}) == 'PARTLY_SAME'
    assert m.vs_raw(res(dict(a)), res(a)) == 'SAME_AS_RAW' and m.vs_raw(res(b), res(a)) == 'DIFFERS'
    assert m.vs_raw(res({}), res({})) == 'BOTH_EMPTY' and m.vs_raw(res(a, 'ERR_HTTP422'), res(a)) == 'ERR'
    span = [(D(2016, 1, 5), D(2016, 2, 1))]
    assert m.leg_vs_raw(res(a), res(a), span) == 'SAME_BARS' and m.leg_vs_raw(res(b), res(a), span) == 'DIFFERENT_BARS'
    assert m.leg_vs_raw(res(a), res(a), []) == '-' and m.leg_vs_raw(res(a), res({}), span) == 'NO_RAW_BARS'
    assert m.leg_vs_raw(res(a), res({D(2016, 1, 5): a[D(2016, 1, 5)], D(2016, 1, 6): (1.0,) * 4}),
                        span) == 'SAME_ON_COMMON_DAYS'


def ideal_bars(spans, salt=0):
    return {d: (100.0 + salt + i / 100, 101.0 + salt, 99.0 + salt, 100.5 + salt + i / 100)
            for i, d in enumerate(SESSIONS) if m.inside(d, spans)}


def raw_ideal():
    """{symbol: result} where every RAW series has exactly its symbol-level bars (last bar = the session before `end`)."""
    out = {}
    for n, s in enumerate(p for p in PLAN if p['mode'] == 'RAW'):
        out[s['symbol']] = res(ideal_bars(m.series_spans(s, SECURITIES, BY_SYMBOL), n))
    return out


def test_events_day_differences():
    raw = raw_ideal()
    got = {(sid, sym, kind): diff for sid, info in SECURITIES.items() for sym, kind, _, diff in m.events(sid, info, raw, BY_SYMBOL)}
    assert got[('DA01', 'EMC', 'END')] == -1                     # merger closed 2016-09-07 (Wed): last bar 09-06
    assert got[('DA02', 'WFM', 'END')] == -3                     # closed Monday 2017-08-28: last bar Friday
    assert got[('DA03', 'DOW', 'END')] == -1                     # last session 2017-08-31 (after-close merger), end 09-01
    assert got[('DA05', 'TWX', 'END')] == -1                     # last session 2018-06-14, end 06-15
    assert got[('AD03', 'SHPG', 'END')] == -3                    # halted from Monday 2019-01-07: last bar Friday 01-04
    assert got[('IP05', 'LYFT', 'START')] == 0 and got[('IP01', 'TWLO', 'START')] == 0
    assert got[('TC01', 'PCLN', 'RENAME_OUT')] == -1 and got[('TC01', 'BKNG', 'RENAME_IN')] == 0
    assert got[('DO02', 'BTU', 'END')] == -1 and got[('DO02', 'BTU', 'RELIST')] == 0
    assert got[('MC05', 'UA', 'RENAME_OUT')] == -1 and got[('MC06', 'UA', 'RENAME_IN')] == 0   # UA swaps classes 2016-12-07
    # 21CF: last FOXA bar 2019-03-18 (Fox Corp uses FOXA from 03-19), one TFCFA session 03-19, gone 03-20
    assert got[('DA07', 'FOXA', 'RENAME_OUT')] == -1 and got[('DA07', 'TFCFA', 'RENAME_IN')] == 0
    assert got[('DA07', 'TFCFA', 'END')] == -1
    assert ('TC05', 'FB', 'RENAME_OUT') not in got               # the rename lies after the window
    assert all(isinstance(v, int) for v in got.values())
    raw['EMC'] = res({})
    raw['WFM'] = res({}, 'ERR_HTTP404')
    got = {(sid, sym, kind): diff for sid, info in SECURITIES.items() for sym, kind, _, diff in m.events(sid, info, raw, BY_SYMBOL)}
    assert got[('DA01', 'EMC', 'END')] is None and got[('DA02', 'WFM', 'END')] == 'ERR'


def test_lineage_codes():
    raw = raw_ideal()
    info = SECURITIES['TC01']
    assert m.lineage_code('TC01', info, raw, BY_SYMBOL) == 'PIT_SYMBOLS'
    assert m.lineage_code('TC05', SECURITIES['TC05'], raw, BY_SYMBOL) == 'PIT_SYMBOLS'   # FB only; META none before 2022
    assert m.lineage_code('DA07', SECURITIES['DA07'], raw, BY_SYMBOL) == 'PIT_SYMBOLS'
    assert m.lineage_code('MC06', SECURITIES['MC06'], raw, BY_SYMBOL) == 'PIT_SYMBOLS'
    full = res(ideal_bars([(m.WINDOW_START, m.WINDOW_AFTER)]))
    backfilled = dict(raw, PCLN=res({}, 'NO_DATA'), BKNG=full)
    assert m.lineage_code('TC01', info, backfilled, BY_SYMBOL) == 'CURRENT_SYMBOL_ONLY'
    current = dict(raw, FB=res({}, 'NO_DATA'), META=full)
    assert m.lineage_code('TC05', SECURITIES['TC05'], current, BY_SYMBOL) == 'CURRENT_SYMBOL_ONLY'
    assert m.lineage_code('TC01', info, dict(raw, BKNG=full), BY_SYMBOL) == 'OVERLAPPING_SYMBOLS'
    assert m.lineage_code('TC01', info, dict(raw, BKNG=res({}, 'NO_DATA')), BY_SYMBOL) == 'MISSING_SYMBOL'
    assert m.lineage_code('TC01', info, dict(raw, BKNG=res({}, 'ERR_HTTP422')), BY_SYMBOL) == 'ERR'
    # UA.C unknown at Alpaca: the UA bars before 2016-12-07 are class A (MC05, the expected reuse), not class C history
    # backfilled under UA, so MC06 reads MISSING_SYMBOL, never CURRENT_SYMBOL_ONLY
    no_c = dict(raw, **{'UA.C': res({}, 'NO_DATA')})
    assert m.lineage_code('MC06', SECURITIES['MC06'], no_c, BY_SYMBOL) == 'MISSING_SYMBOL'
    # ... but class C history really filed under UA (bars before 2016-12-07 beyond MC05's use) would still read so
    # 21CF: FOXA empty, TFCFA carrying 21CF's whole history
    foxa = dict(raw, FOXA=res({}, 'NO_DATA'), TFCFA=res(ideal_bars([(m.WINDOW_START, date(2019, 3, 20))])))
    assert m.lineage_code('DA07', SECURITIES['DA07'], foxa, BY_SYMBOL) == 'CURRENT_SYMBOL_ONLY'


# ---- the public-line allow-table -------------------------------------------------------------------------------------------
def test_allow_table_refuses_anything_outside_it():
    good = 'ALPSAMPLE_CHECKPOINT cp=T2018 day=2018-02-20 field=open expected=37 bar=36 missing=1 error=0 unexpected=0'
    assert m.checked_line(good) == good
    for bad in [
        'ALPSAMPLE_CHECKPOINT cp=T2018 px_sum=4595 day=2018-02-20 field=open expected=37 bar=36 missing=1 error=0 unexpected=0',
        good + ' close=150',                                                        # an extra key
        good.replace('bar=36', 'bar=7391'),                                         # an integer beyond the bound
        good.replace('bar=36', 'bar=36.5'),                                         # a decimal
        good.replace('day=2018-02-20', 'day=2018-02-21'),                           # a date outside the fixed set
        good.replace('field=open', 'field=high'),                                   # a code outside the list
        good.replace('expected=37 bar=36', 'bar=36 expected=37'),                   # key order
        'ALPSAMPLE_PRICE close=150', 'ALPSAMPLE_CLASSES pair=GOOGL+GOOG overlap=SAME_BARS',
        'ALPSAMPLE_STORAGE status=STORED release=kis-raw-1 files=69 roundtrip=SHA256_MATCH retries=0',
        'ALPSAMPLE_EVENT sid=DA01 cat=DELISTED_ACQUIRED sym=EMC event=END event_day=2016-09-07 bar_vs_event_days=7391',
        'ALPSAMPLE_SERIES id=RAW:TSLA', 'ALPSAMPLE_STOP reason=a b', 'ALPSAMPLE_STOP', None,
    ]:
        with pytest.raises(ValueError):
            m.checked_line(bad)
    assert set(m.LINE_SPECS) == {'ALPSAMPLE_PLAN', 'ALPSAMPLE_PLAN_CATEGORY', 'ALPSAMPLE_STOP', 'ALPSAMPLE_START',
                                 'ALPSAMPLE_SERIES', 'ALPSAMPLE_EVENT', 'ALPSAMPLE_LINEAGE', 'ALPSAMPLE_CLASSES',
                                 'ALPSAMPLE_CATEGORY', 'ALPSAMPLE_CHECKPOINT', 'ALPSAMPLE_REQUESTS', 'ALPSAMPLE_STORAGE'}
    # no value-comparison code is a permitted public value anywhere in the table
    def values(matcher):
        if matcher[0] == 'enum':
            return set(matcher[1])
        if matcher[0] in ('list', 'either'):
            inner = [matcher[1]] if matcher[0] == 'list' else matcher[1]
            return set().union(*(values(x) for x in inner))
        return set()
    allowed = set().union(*(values(mt) for specs in m.LINE_SPECS.values() for spec in specs for _, mt in spec))
    assert not allowed & PRIVATE_CODES


# ---- fake services for the end-to-end runs --------------------------------------------------------------------------------
def price(symbol, i):
    """Synthetic o/h/l/c with distinctive integer parts 7391..7398, one series per symbol."""
    s = sum(map(ord, symbol))
    base = 7391 + s % 4
    frac = ((s * 7 + i) % 89 + 10) / 100
    return round(base + frac, 2), round(base + 4 + frac, 2), round(base + frac - 0.05, 2), round(base + 2 + frac, 2)


def priced_bar(day, values):
    o, h, l, c = values
    return {'t': day.isoformat() + 'T05:00:00Z', 'o': o, 'h': h, 'l': l, 'c': c, 'v': VOLUME, 'n': TRADES,
            'vw': round(o + 0.01, 2)}


def alpaca_service(variant=None, served=None):
    """URL -> response. RAW: the symbol's own uses, priced by that symbol. Mapped (ideal = follows the issuer): each expected
    leg carries the bars of that leg's symbol, so a mapped series equals the plain series of each leg's symbol inside the
    leg. A variant may return spans (bars of the requested symbol on those spans), 'AS_RAW' (answer the plain symbol: the
    documented fallback when no mapping is found) or an exception."""
    by_key = {(s['symbol'], s['asof']): s for s in PLAN}
    index = {d: i for i, d in enumerate(SESSIONS)}

    def serve(url):
        parts = urllib.parse.urlsplit(url)
        symbol = parts.path.split('/')[3]
        query = dict(urllib.parse.parse_qsl(parts.query))
        series = by_key[(symbol, query['asof'])]
        legs = m.expected_legs(series, SECURITIES, BY_SYMBOL)
        if variant:
            changed = variant(series, m.clip((f, e) for _, f, e in legs))
            if isinstance(changed, BaseException):
                raise changed
            if changed == 'AS_RAW':
                legs = [(symbol, f, e) for f, e, _ in BY_SYMBOL[symbol]]
            elif changed is not None:
                legs = [(symbol, a, b) for a, b in changed]
        bars = []
        for d in SESSIONS:
            owner = next((sym for sym, f, e in legs if m.inside(d, m.clip([(f, e)]))), None)
            if owner is not None:
                values = price(owner, index[d])
                if served is not None:
                    served.update(values)
                bars.append(priced_bar(d, values))
        half = len(bars) // 2
        if series['id'] == 'RAW:SPY':                      # one series answers in two pages
            if 'page_token' not in query:
                return FakeResponse(page(symbol, bars[:half], 'synthetic-page-2'))
            return FakeResponse(page(symbol, bars[half:]))
        return FakeResponse(page(symbol, bars or None))
    return serve


class FakeGithub:
    """Fake GitHub. `fail` maps a route label to how many leading answers are 503 (or 'net' for a connection error);
    `create_then_fail` creates the release but answers 502 to the create call."""

    def __init__(self, private=True, tag_exists=False, fail_upload=False, corrupt=False, fail=None, create_then_fail=False,
                 existing_assets=()):
        self.private, self.tag_exists, self.fail_upload, self.corrupt = private, tag_exists, fail_upload, corrupt
        self.fail, self.create_then_fail, self.existing_assets = dict(fail or {}), create_then_fail, list(existing_assets)
        self.calls, self.assets = [], {}

    def _failing(self, label):
        left = self.fail.get(label)
        kind, n = left if isinstance(left, tuple) else ('503', left or 0)
        if n <= 0:
            return None
        self.fail[label] = (kind, n - 1)
        if kind == 'net':
            raise TimeoutError('synthetic')
        return 503, {}, b'{}'

    def __call__(self, method, url, *, data=None, headers=None, auth=True, opener=None):
        self.calls.append((method, url, auth))
        assert opener is not None and auth is (not url.startswith('https://objects.'))
        if (method, url) == ('GET', GH_REPO):
            return self._failing('repo') or (200, {}, json.dumps({'private': self.private}).encode())
        if (method, url) == ('GET', GH_REPO + '/releases/tags/' + TAG):
            failed = self._failing('tag')
            if failed:
                return failed
            if self.tag_exists:
                return 200, {}, json.dumps({'id': 77, 'tag_name': TAG, 'draft': False,
                                            'assets': self.existing_assets}).encode()
            return 404, {}, b'{}'
        if (method, url) == ('POST', GH_REPO + '/releases'):
            payload = json.loads(data)
            assert payload['tag_name'] == payload['name'] == TAG and payload['draft'] is False
            failed = self._failing('create')
            if failed:
                return failed
            self.tag_exists = True
            if self.create_then_fail:
                self.create_then_fail = False
                return 502, {}, b'{}'
            return 201, {}, json.dumps({'id': 77, 'tag_name': TAG}).encode()
        if method == 'POST' and url.startswith(GH_UP + '77/assets?name='):
            failed = self._failing('upload')
            if failed:
                return failed
            if self.fail_upload:
                return 422, {}, b'{}'
            name = urllib.parse.unquote(url.split('name=', 1)[1])
            assert name not in self.assets
            self.assets[name] = data
            return 201, {}, json.dumps({'id': 900 + len(self.assets), 'name': name}).encode()
        if (method, url) == ('GET', GH_REPO + '/releases/assets/901'):
            return self._failing('download') or (302, {'Location': 'https://objects.githubusercontent.com/synthetic-signed'}, b'')
        if (method, url) == ('GET', 'https://objects.githubusercontent.com/synthetic-signed'):
            body = self.assets[TAG + '.zip']
            return 200, {}, (body + b'x' if self.corrupt else body)
        raise AssertionError('unexpected GitHub route')


def run_main(environ=ENV, variant=None, github=None, argv=(), served=None, clock=None):
    lines, github = [], github or FakeGithub()
    opener = FakeOpener(alpaca_service(variant, served))
    sleeps = []
    code = m.main(list(argv), environ=dict(environ), opener=opener, github_call=github, sleep=sleeps.append,
                  clock=clock or Clock(0.0), out=lines.append, now=datetime(2026, 11, 2, tzinfo=timezone.utc))
    return code, lines, opener, github


def fields(line):
    return dict(word.split('=', 1) for word in line.split(' ')[1:])


def assert_public(lines, served=()):
    """Every line passes the allow-table, no value-comparison code, no served price in any int or str form."""
    text = '\n'.join(lines)
    for line in lines:
        assert m.checked_line(line) == line
        assert not any(v in PRIVATE_CODES for word in line.split(' ')[1:] for v in re.split(r'[,+]', word.split('=', 1)[1]))
    assert not re.search(r'[0-9]\.[0-9]', text)
    assert str(VOLUME) not in text and str(TRADES) not in text
    for secret in (KEY, SECRET, TOKEN, 'synthetic-page-2', 'objects.githubusercontent', 'alpaca.markets', 'https:'):
        assert secret not in text
    numbers = set(re.findall(r'[0-9]+', text))
    for value in served:
        assert str(value) not in text and f'{value:.2f}' not in text and str(int(value)) not in numbers
    for whole in range(7391, 7399):
        assert str(whole) not in text


def run_ideal():
    served = set()
    code, lines, opener, github = run_main(served=served)
    return code, lines, opener, github, served


def test_end_to_end_ideal_data():
    code, lines, opener, github, served = run_ideal()
    assert code == 0 and len(served) > 500
    assert_public(lines, served)
    assert len(opener.calls) == 68 and all(c[1:] == (KEY, SECRET) for c in opener.calls)   # 67 series, SPY in two pages
    kinds = Counter(line.split(' ', 1)[0] for line in lines)
    assert kinds['ALPSAMPLE_START'] == 1 and kinds['ALPSAMPLE_SERIES'] == 67 and kinds['ALPSAMPLE_CATEGORY'] == 10
    assert kinds['ALPSAMPLE_CHECKPOINT'] == 45 and kinds['ALPSAMPLE_CLASSES'] == 3 and kinds['ALPSAMPLE_STORAGE'] == 1
    assert lines[-1] == f'ALPSAMPLE_STORAGE status=STORED release={TAG} files=69 roundtrip=SHA256_MATCH retries=0'
    series = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert all(s['status'] == 'DATA' or s['fit'] == 'NONE_EXPECTED' for s in series.values())
    assert series['RAW:AAPL'] == {'id': 'RAW:AAPL', 'sid': 'CL01', 'cat': 'CONTROL_LARGE', 'mode': 'RAW', 'expect': 'SYMBOL',
                                  'status': 'DATA', 'fit': 'MATCH', 'first': 'AT_START', 'last': 'AT_END', 'gaps': 'NONE',
                                  't_bar': 'BAR,BAR,BAR,BAR', 's_bar': 'BAR,BAR,BAR,BAR', 'monthend': 'FULL',
                                  'monthend_2016w': 'FULL', 'monthend_2017w': 'FULL', 'days_vs_raw': '-', 'echo': 'SAME'}
    assert series['RAW:EMC']['t_bar'] == 'BAR,-,-,-' and series['RAW:EMC']['monthend'] == 'NA'
    assert series['RAW:EMC']['monthend_2016w'] == 'FULL'             # 2016-02..08 expected; later ones lie after the merger
    assert series['RAW:LYFT']['first'] == 'LATER' and series['RAW:LYFT']['t_bar'] == '-,-,-,-'
    assert series['RAW:META']['status'] == 'NO_DATA' and series['RAW:META']['fit'] == 'NONE_EXPECTED'
    assert series['ASOF20180220:PCLN']['fit'] == 'MATCH' and series['ASOF20261030:DOW']['fit'] == 'NONE_EXPECTED'
    # issuer-following answers differ in their DAYS from the plain series wherever presence can show it
    assert series['ASOF20180220:PCLN']['days_vs_raw'] == 'MORE_DAYS'      # PCLN + BKNG days vs PCLN alone
    assert series['ASOF20160216:BTU']['days_vs_raw'] == 'FEWER_DAYS'      # old Peabody only
    assert series['ASOF20180220:UA']['days_vs_raw'] == 'FEWER_DAYS'       # class C: UA.C from 2016-04-08, then UA
    assert series['ASOF20160216:UA']['days_vs_raw'] == 'SAME_DAYS'        # class A: same days as plain UA (values: private)
    cats = {fields(l)['cat']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CATEGORY ')}
    assert cats['CONTROL_LARGE'] == {'cat': 'CONTROL_LARGE', 'securities': '2', 'symbols': '2', 'symbols_with_data': '2',
                                     'symbols_no_data': '0', 'symbols_error': '0', 't_bar': '8/8', 't_unexpected': '0',
                                     's_bar': '8/8', 's_unexpected': '0', 'monthend': '26/26', 'monthend_unexpected': '0',
                                     'monthend_2016w': '24/24', 'monthend_2016w_unexpected': '0',
                                     'monthend_2017w': '24/24', 'monthend_2017w_unexpected': '0',
                                     'complete': '2', 'gapless': '2/2'}
    assert cats['DELISTED_ACQUIRED']['t_bar'] == '18/18'   # EMC 1, WFM 2, DOW 2, MON 3, TWX 3, DNB 3 (gone before T2019), FOXA 4
    assert cats['DELISTED_ACQUIRED']['symbols'] == '8'     # TFCFA too
    assert cats['TICKER_CHANGE']['symbols_no_data'] == '1'  # META: nothing under it before 2022
    assert all(c['complete'] == c['securities'] and c['t_unexpected'] == c['s_unexpected'] == '0' for c in cats.values())
    checkpoint = {fields(l)['cp']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CHECKPOINT ')}
    assert checkpoint['T2018']['field'] == 'open' and checkpoint['ME201902']['field'] == 'close'
    assert checkpoint['T2016']['expected'] == checkpoint['T2016']['bar'] == '34'   # 40 minus five IPOs and class C (UA.C)
    assert checkpoint['ME201602']['day'] == '2016-02-29' and checkpoint['ME201712']['day'] == '2017-12-29'
    for cp, day, _, _ in m.checkpoints():
        assert checkpoint[cp]['day'] == day.isoformat() and pit_filings.is_session(day)
    lineage = {fields(l)['sid']: fields(l) for l in lines if l.startswith('ALPSAMPLE_LINEAGE ')}
    assert set(lineage) == {'TC01', 'TC02', 'TC03', 'TC04', 'TC05', 'MC05', 'MC06', 'DA03', 'DA07', 'DO02'}
    assert lineage['TC01'] == {'sid': 'TC01', 'cat': 'TICKER_CHANGE', 'raw': 'PIT_SYMBOLS', 'asof_pit': 'MATCH',
                               'asof_current': 'MATCH', 'common_days': 'NONE'}
    assert lineage['DO02']['asof_pit'] == 'MATCH,MATCH' and lineage['DO02']['asof_current'] == 'MATCH'
    assert lineage['DA03']['raw'] == 'SINGLE_LEG' and lineage['DA07']['raw'] == 'PIT_SYMBOLS'
    assert lineage['DA07']['asof_pit'] == 'MATCH'          # the dated FOXA series follows 21CF to its TFCFA session
    classes = [fields(l) for l in lines if l.startswith('ALPSAMPLE_CLASSES ')]
    assert [c['days'] for c in classes] == ['SAME_DAYS', 'SAME_DAYS', 'OTHER_DAYS']
    events = [fields(l) for l in lines if l.startswith('ALPSAMPLE_EVENT ')]
    assert {e['bar_vs_event_days'] for e in events} <= {'0', '-1', '-2', '-3', '-4'}
    requests = fields(next(l for l in lines if l.startswith('ALPSAMPLE_REQUESTS ')))
    assert requests['total'] == '68' and requests['pages'] == '68' and requests['stopped'] == 'NONE'


def manifest_of(github):
    with zipfile.ZipFile(io.BytesIO(github.assets[TAG + '.zip'])) as z:
        return json.loads(z.read('manifest.json')), z


def private_of(github, kind):
    manifest, _ = manifest_of(github)
    return {line.split(' ')[1].split('=', 1)[1]: fields(line) for line in manifest['private_lines']
            if line.startswith(kind + ' ')}


def test_raw_archive_goes_only_to_the_new_private_release():
    code, lines, _, github, _ = run_ideal()
    assert code == 0
    methods = [(c[0], c[1].split('?')[0]) for c in github.calls]
    # privacy and tag absence before any Alpaca request, and both again right before creating
    assert methods == [('GET', GH_REPO), ('GET', GH_REPO + '/releases/tags/' + TAG),
                       ('GET', GH_REPO), ('GET', GH_REPO + '/releases/tags/' + TAG), ('POST', GH_REPO + '/releases'),
                       ('POST', GH_UP + '77/assets'), ('POST', GH_UP + '77/assets'),
                       ('GET', GH_REPO + '/releases/assets/901'), ('GET', 'https://objects.githubusercontent.com/synthetic-signed')]
    assert set(github.assets) == {TAG + '.zip', TAG + '.zip.sha256'}
    archive = github.assets[TAG + '.zip']
    assert github.assets[TAG + '.zip.sha256'] == f'{hashlib.sha256(archive).hexdigest()}  {TAG}.zip\n'.encode()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        manifest = json.loads(z.read('manifest.json'))
        assert manifest['schema'] == 'alpaca-sample-v1-manifest/2' and manifest['run_id'] == RUN_ID
        assert manifest['code_sha'] == 'a' * 40 and manifest['stopped'] == 'NONE' and len(manifest['sample']) == 40
        assert manifest['source']['feed'] == 'sip' and 'non-commercial' in manifest['source']['terms']
        files = [p for e in manifest['series'] for p in e['pages']]
        assert len(files) == 68 and len(z.namelist()) == 69
        for entry in files:
            assert hashlib.sha256(z.read(entry['file'])).hexdigest() == entry['sha256']
        text = z.read('manifest.json').decode()
        assert KEY not in text and SECRET not in text and TOKEN not in text
        assert manifest['summary_lines'] == [l for l in lines if not l.startswith(('ALPSAMPLE_START', 'ALPSAMPLE_REQUESTS',
                                                                                   'ALPSAMPLE_STORAGE'))]
        private = manifest['private_lines']
        assert Counter(l.split(' ', 1)[0] for l in private) == {
            'ALPSAMPLE_PRIVATE_SERIES': 67, 'ALPSAMPLE_PRIVATE_ASOF': 20, 'ALPSAMPLE_PRIVATE_LINEAGE': 10,
            'ALPSAMPLE_PRIVATE_CLASSES': 3, 'ALPSAMPLE_PRIVATE_CHECKPOINT': 45}
        assert not set(private) & set(lines)
    classes = private_of(github, 'ALPSAMPLE_PRIVATE_CLASSES')
    assert {k: v['overlap'] for k, v in classes.items()} == {'GOOGL+GOOG': 'DIFFERENT_BARS', 'BRK.A+BRK.B': 'DIFFERENT_BARS',
                                                             'UAA+UA': 'DIFFERENT_BARS'}
    checkpoint = private_of(github, 'ALPSAMPLE_PRIVATE_CHECKPOINT')
    assert checkpoint['T2016'] == {'cp': 'T2016', 'ok': '34', 'bad': '0'}
    assert run_main()[0] == 0      # deterministic archive bytes for the same responses
    assert run_main()[3].assets[TAG + '.zip'] == archive


def test_mapping_followed_or_skipped():
    """Alpaca answers the plain symbol when it finds no mapping (asof doc). The private codes always tell the two apart; the
    public presence codes do wherever the days differ (Peabody, Under Armour class C, ticker changes), never by values."""
    _, ideal_lines, _, ideal_gh, _ = run_ideal()
    skipped = {'ASOF20160216:UA', 'ASOF20261030:UAA', 'ASOF20180220:UA', 'ASOF20160216:BTU', 'ASOF20180220:BTU',
               'ASOF20180220:PCLN'}
    served = set()
    code, lines, _, github = run_main(variant=lambda s, spans: 'AS_RAW' if s['id'] in skipped else None, served=served)
    assert code == 0
    assert_public(lines, served)
    ideal_asof, asof = private_of(ideal_gh, 'ALPSAMPLE_PRIVATE_ASOF'), private_of(github, 'ALPSAMPLE_PRIVATE_ASOF')
    # Under Armour class A: following = class A then UAA; skipped = plain UA (class A, then class C after the swap)
    assert ideal_asof['ASOF20160216:UA']['vs_raw'] == 'DIFFERS'
    assert ideal_asof['ASOF20160216:UA']['legs_vs_raw'] == 'SAME_BARS,SAME_BARS'
    assert asof['ASOF20160216:UA']['vs_raw'] == 'SAME_AS_RAW'                     # mapping not shown
    assert asof['ASOF20160216:UA']['legs_vs_raw'] == 'SAME_BARS,DIFFERENT_BARS'   # post-swap bars are class C, not UAA
    assert ideal_asof['ASOF20261030:UAA']['legs_vs_raw'] == 'SAME_BARS,SAME_BARS'
    assert asof['ASOF20261030:UAA']['legs_vs_raw'] == 'NO_ASOF_BARS,SAME_BARS'
    # Under Armour class C before the swap: following = UA.C bars; skipped = plain UA (class A)
    assert ideal_asof['ASOF20180220:UA']['legs_vs_raw'] == 'SAME_BARS,SAME_BARS'
    assert asof['ASOF20180220:UA']['legs_vs_raw'] == 'DIFFERENT_BARS,SAME_BARS'
    # Peabody: following keeps old and new equity apart; skipped returns both under BTU
    assert ideal_asof['ASOF20160216:BTU']['vs_raw'] == 'DIFFERS' and asof['ASOF20160216:BTU']['vs_raw'] == 'SAME_AS_RAW'
    public = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    ideal_public = {fields(l)['id']: fields(l) for l in ideal_lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert public['ASOF20160216:BTU']['fit'] == 'MATCH+OUTSIDE' and public['ASOF20160216:BTU']['days_vs_raw'] == 'SAME_DAYS'
    assert public['ASOF20180220:BTU']['fit'] == 'MATCH+OUTSIDE' and ideal_public['ASOF20180220:BTU']['fit'] == 'MATCH'
    assert public['ASOF20180220:UA']['days_vs_raw'] == 'SAME_DAYS' and public['ASOF20180220:UA']['fit'] == 'MATCH+OUTSIDE'
    assert public['ASOF20180220:PCLN']['days_vs_raw'] == 'SAME_DAYS' and public['ASOF20180220:PCLN']['fit'] == 'PARTIAL'
    # the class-A swap shows only privately: its public line is the same either way
    assert public['ASOF20160216:UA'] == ideal_public['ASOF20160216:UA']
    lineage = {fields(l)['sid']: fields(l) for l in lines if l.startswith('ALPSAMPLE_LINEAGE ')}
    assert lineage['DO02']['asof_pit'] == 'MATCH+OUTSIDE,MATCH+OUTSIDE'


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
        if series['id'] == 'RAW:LCUT':                     # a hole in the 2016 holding months
            return [(m.WINDOW_START, date(2016, 7, 1)), (date(2016, 8, 1), m.WINDOW_AFTER)]
        if series['id'] == 'RAW:UA.C':                     # the dotted form unknown at Alpaca
            return []
        if series['id'] == 'RAW:BRK.A':
            return urllib.error.HTTPError(BASE, 422, 'synthetic', {}, io.BytesIO(b'{}'))
        return None
    served = set()
    code, lines, _, _ = run_main(variant=variant, served=served)
    assert code == 0
    assert_public(lines, served)
    series = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert series['RAW:BKNG']['fit'] == 'MATCH+OUTSIDE' and series['RAW:PCLN']['status'] == 'NO_DATA'
    assert series['RAW:BRK.A']['status'] == 'ERR_HTTP422' and series['RAW:BRK.A']['t_bar'] == 'ERR,ERR,ERR,ERR'
    assert series['RAW:KIRK']['gaps'] == 'SOME' and series['RAW:KIRK']['monthend'] == 'PARTIAL'
    assert series['RAW:LCUT']['monthend_2016w'] == 'PARTIAL' and series['RAW:LCUT']['monthend'] == 'FULL'
    lineage = {fields(l)['sid']: fields(l) for l in lines if l.startswith('ALPSAMPLE_LINEAGE ')}
    assert lineage['TC01']['raw'] == 'CURRENT_SYMBOL_ONLY' and lineage['DA07']['asof_pit'] == 'MATCH+OUTSIDE'
    assert lineage['TC01']['common_days'] == 'NONE'
    assert lineage['MC06']['raw'] == 'MISSING_SYMBOL'      # never CURRENT_SYMBOL_ONLY for the reused UA
    events = {(fields(l)['sid'], fields(l)['event']): fields(l) for l in lines if l.startswith('ALPSAMPLE_EVENT ')}
    assert events[('DO03', 'END')]['bar_vs_event_days'] == '-33' and events[('DO03', 'END')]['event_day'] == '2018-10-24'
    assert events[('TC01', 'RENAME_OUT')]['bar_vs_event_days'] == 'NONE'
    cats = {fields(l)['cat']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CATEGORY ')}
    assert cats['TICKER_CHANGE']['t_bar'] == '17/20' and cats['TICKER_CHANGE']['complete'] == '4'   # PCLN: T2016..T2018
    assert cats['MULTI_CLASS']['symbols_error'] == '1' and cats['SMALL_CAP']['gapless'] == '2/4'
    assert cats['DELISTED_OTHER']['monthend'] == '33/34'   # BTU 13, SHLD 8, WIN 13; SHLD 2018-09-28 missing (ended 09-21)
    assert cats['SMALL_CAP']['monthend_2016w'] == '47/48'  # KIRK, LCUT, BGFV, RT 12 each; LCUT 2016-07 missing
    checkpoint = {fields(l)['cp']: fields(l) for l in lines if l.startswith('ALPSAMPLE_CHECKPOINT ')}
    assert checkpoint['T2017']['error'] == '1' and checkpoint['ME201805']['missing'] == '1'
    assert checkpoint['ME201607']['missing'] == '3' and checkpoint['ME201609']['missing'] == '2'   # LCUT, MC06, TC01


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
                           (FakeGithub(tag_exists=True), 'RELEASE_TAG_EXISTS'),
                           (FakeGithub(fail={'repo': 3}), 'HTTP5XX'),
                           (FakeGithub(fail={'tag': ('net', 3)}), 'NETWORK')]:
        code, lines, opener, github = run_main(github=github)
        assert (code, lines, opener.calls) == (2, [f'ALPSAMPLE_STOP reason={reason}'], [])
        assert all(c[0] == 'GET' for c in github.calls)


def test_auth_rejection_stops_and_storage_failures_exit_3():
    def variant(series, spans):
        if series['id'] == 'RAW:WFM':
            return urllib.error.HTTPError(BASE, 401, 'synthetic', {}, io.BytesIO(b'{}'))
        return None
    code, lines, opener, github = run_main(variant=variant)
    assert code == 3
    assert_public(lines)
    requests = fields(next(l for l in lines if l.startswith('ALPSAMPLE_REQUESTS ')))
    assert requests['stopped'] == 'AUTH_REJECTED' and requests['http401'] == '1' and requests['series_done'] == '4'
    series = {fields(l)['id']: fields(l) for l in lines if l.startswith('ALPSAMPLE_SERIES ')}
    assert series['RAW:MON']['status'] == 'NOT_RUN' and series['RAW:EMC']['status'] == 'DATA'
    assert lines[-1].startswith('ALPSAMPLE_STORAGE status=STORED ')             # partial raw pages are still kept privately
    for github, code_ in [(FakeGithub(fail_upload=True), 'ASSET_UPLOAD_FAILED'), (FakeGithub(corrupt=True), 'ROUNDTRIP_MISMATCH'),
                          (FakeGithub(fail={'upload': 5}), 'HTTP5XX')]:
        code, lines, _, _ = run_main(github=github)
        assert code == 3 and re.fullmatch(f'ALPSAMPLE_STORAGE status=FAILED code={code_} retries=[0-9]+', lines[-1]), lines[-1]
        assert_public(lines)


def test_storage_retries_transient_errors_inside_its_budget():
    # one 503 on every non-creating call and on the create (nothing created): stored, with the retries counted
    github = FakeGithub(fail={'repo': 1, 'tag': 1, 'create': 1, 'upload': 1, 'download': ('net', 1)})
    code, lines, _, github = run_main(github=github)
    assert code == 0 and lines[-1] == f'ALPSAMPLE_STORAGE status=STORED release={TAG} files=69 roundtrip=SHA256_MATCH retries=5'
    # preflight: repo and tag retried once each; store: create 503 -> tag re-checked (404) -> create again; one upload and one
    # download retried
    assert [c[0] + ' ' + c[1].split('?')[0].rsplit('/', 1)[-1] for c in github.calls].count('POST releases') == 2
    # the create reached GitHub but its answer was lost: the empty release with this run's tag is taken over, never a second
    github = FakeGithub(create_then_fail=True)
    code, lines, _, github = run_main(github=github)
    assert code == 0 and lines[-1].startswith('ALPSAMPLE_STORAGE status=STORED ')
    assert [c[0] for c in github.calls if c[1] == GH_REPO + '/releases'] == ['POST']
    # ... but a release that already holds an asset is never written to
    store = m.RawStore(TAG, FakeGithub(tag_exists=False, create_then_fail=True, existing_assets=[{'id': 1}]),
                       sleep=lambda s: None, clock=Clock(0.0))
    with pytest.raises(m.StorageError, match='RELEASE_TAG_EXISTS'):
        store.store(b'zip')
    # the time budget: no call starts once it is spent, and waits are capped by what is left
    sleeps = []
    store = m.RawStore(TAG, FakeGithub(fail={'repo': 5}), sleep=sleeps.append,
                       clock=Clock(0.0, 0.0, m.STORAGE_BUDGET_S - 2.0, m.STORAGE_BUDGET_S - 2.0, m.STORAGE_BUDGET_S + 1.0))
    with pytest.raises(m.StorageError, match='TIME_BUDGET'):
        store.store(b'zip')
    assert sleeps == [2.0]
    assert m.GH_TIMEOUT_S <= 60 and m.STORAGE_RETRY_WAITS_S == (5.0, 15.0)


def test_budget_opener_caps_the_socket_timeout():
    seen = []

    class Inner:
        def open(self, request, timeout=None):
            seen.append(timeout)
            return 'response'
    left = [500.0]
    opener = m._BudgetOpener(lambda: left[0])
    opener._opener = Inner()
    assert opener.open('req', timeout=600) == 'response' and seen == [m.GH_TIMEOUT_S]
    left[0] = 12.0
    opener.open('req', timeout=600)
    left[0] = -3.0
    opener.open('req', timeout=600)
    assert seen == [m.GH_TIMEOUT_S, 12.0, 1.0]


def test_release_name_and_routes_are_fixed():
    assert m.release_tag('123') == 'alpaca-sample-v1-123'
    for bad in ('', '12a', '1' * 21, '../1', ' 1', None):
        with pytest.raises(m.StorageError):
            m.release_tag(bad)
    for bad in ('alpaca-sample-v1-', 'alpaca-sample-v2-1', 'kis-1', 'alpaca-sample-v1-1x', None):
        with pytest.raises(m.StorageError):
            m.RawStore(bad, FakeGithub())
    store = m.RawStore(TAG, FakeGithub())
    up = GH_UP + '77/assets?name='
    assert store.allowed('GET', GH_REPO) and store.allowed('POST', GH_REPO + '/releases')
    assert store.allowed('GET', GH_REPO + '/releases/tags/' + TAG)
    refused = [('GET', GH_REPO + '/releases'), ('GET', GH_REPO + '/releases/latest'),
               ('GET', GH_REPO + '/releases/tags/alpaca-sample-v1-1'), ('GET', GH_REPO + '/releases/tags/kis-raw-1'),
               ('DELETE', GH_REPO + '/releases/77'), ('PATCH', GH_REPO + '/releases/77'), ('POST', up + 'other.zip'),
               ('POST', up + TAG + '.zip&x=1'), ('DELETE', GH_REPO + '/releases/assets/901'), ('PUT', GH_REPO),
               ('GET', 'https://api.github.com/repos/kco994553-star/Investment-System1'),
               ('GET', GH_REPO + '/contents/x'), ('POST', GH_REPO + '/git/refs')]
    # before the create: no upload and no asset download at all
    for method, url in refused + [('POST', up + TAG + '.zip'), ('POST', up + TAG + '.zip.sha256'),
                                  ('GET', GH_REPO + '/releases/assets/901')]:
        assert not store.allowed(method, url), (method, url)
        with pytest.raises(m.StorageError, match='ROUTE_NOT_ALLOWED'):
            store.http(method, url)
    # after the create: only the created release id and this run's own asset id; no second create
    store = m.RawStore(TAG, FakeGithub())
    store._release_id, store._asset_ids = 77, {901}
    assert store.allowed('POST', up + TAG + '.zip') and store.allowed('POST', up + TAG + '.zip.sha256')
    assert store.allowed('GET', GH_REPO + '/releases/assets/901')
    for method, url in refused + [('POST', GH_UP + '78/assets?name=' + TAG + '.zip'), ('POST', GH_REPO + '/releases'),
                                  ('GET', GH_REPO + '/releases/assets/902'), ('GET', GH_REPO + '/releases/assets/1')]:
        assert not store.allowed(method, url), (method, url)
    github = FakeGithub(tag_exists=True)    # create-only: an existing tag is never reused or written to
    with pytest.raises(m.StorageError, match='RELEASE_TAG_EXISTS'):
        m.RawStore(TAG, github).store(b'zip')
    assert [c[0] for c in github.calls] == ['GET', 'GET']


def test_plan_mode_and_script_without_environment(tmp_path):
    code, lines, opener, github = run_main(argv=['--plan'])
    assert code == 0 and opener.calls == [] and github.calls == []
    assert lines[0] == ('ALPSAMPLE_PLAN securities=40 symbols=47 series=67 raw=47 asof_pit=11 asof_current=9 '
                        'pages_expected=67 max_requests=150 pace_ms=600')
    assert len(lines) == 11 and run_main(argv=['--other'])[1] == ['ALPSAMPLE_STOP reason=USAGE']
    unverified = {fields(l)['cat']: fields(l)['unverified'] for l in lines[1:]}
    assert unverified == {'CONTROL_LARGE': '0', 'ETF_AUX': '0', 'DELISTED_ACQUIRED': '0', 'DELISTED_OTHER': '0',
                          'TICKER_CHANGE': '0', 'MULTI_CLASS': '2', 'ADR': '0', 'REIT': '0', 'SMALL_CAP': '1',
                          'IPO_IN_WINDOW': '0'}
    env = {k: v for k, v in os.environ.items() if k not in ENV and k.lower() not in
           ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9')   # a request could not leave anyway
    for flags in ([], ['-I', '-S']):   # the workflow runs the tool with -I -S (stdlib only)
        run = subprocess.run([sys.executable, *flags, str(TOOL)], cwd=tmp_path, env=env, capture_output=True, text=True,
                             timeout=60)
        assert (run.returncode, run.stdout, run.stderr) == (2, 'ALPSAMPLE_STOP reason=RUNNER_REQUIRED\n', '')
        run = subprocess.run([sys.executable, *flags, str(TOOL), '--plan'], cwd=tmp_path, env=env, capture_output=True,
                             text=True, timeout=60)
        assert run.returncode == 0 and run.stdout.startswith('ALPSAMPLE_PLAN securities=40 ') and run.stderr == ''
    assert list(tmp_path.iterdir()) == []


# ---- static: workflow, plan document, files -------------------------------------------------------------------------------
def _jobs(text):
    body = text.split('\njobs:\n', 1)[1]
    names = re.findall(r'(?m)^  ([a-z_-]+):\n', body)
    parts = re.split(r'(?m)^  [a-z_-]+:\n', body)[1:]
    return dict(zip(names, parts))


def test_workflow_runs_once_with_the_secrets_in_a_job_that_never_ran_pip():
    text = WORKFLOW.read_text()
    assert 'on:\n  push:\n    branches: [claude/alpaca-sample-once-run]\npermissions:\n  contents: read\n' in text
    for forbidden in ('workflow_dispatch', 'schedule:', 'pull_request', 'actions/upload', 'actions/cache', 'actions/download',
                      'GITHUB_STEP_SUMMARY', 'GITHUB_ENV', 'GITHUB_PATH', 'git push', 'git commit', 'always()', ': write',
                      'id-token', 'RAW_REPO_READ', 'claude/alpaca-sample-once]', 'KIS', 'kis', 'continue-on-error'):
        assert forbidden not in text, forbidden
    assert text.count('permissions:') == 1 and 'concurrency:\n  group: alpaca-sample-once-' in text
    jobs = _jobs(text)
    assert list(jobs) == ['offline', 'measure']
    for job in jobs.values():
        assert "if: github.ref == 'refs/heads/claude/alpaca-sample-once-run'" in job
        assert job.count('actions/checkout@') == job.count('persist-credentials: false') == 1
    offline, measure = jobs['offline'], jobs['measure']
    assert 'needs: offline' in measure and 'needs:' not in offline
    assert int(re.search(r'\n    timeout-minutes: (\d+)\n', '\n' + measure)[1]) <= 25
    # the offline test: its own job, no Secret, quiet failure output
    assert 'secrets.' not in offline and 'pip install pytest==9.1.1' in offline
    command = next(line for line in offline.splitlines() if 'python -m pytest' in line)
    assert command.strip() == ('PYTHONPATH=src python -m pytest -q --tb=no -rN -p no:warnings -p no:cacheprovider '
                               'tests/test_alpaca_sample_once.py')
    # the Secret job: no pip, no other run step, the stdlib-only tool under -I -S
    assert 'pip' not in measure and 'pytest' not in measure
    steps = measure.split('\n    steps:\n', 1)[1].split('\n      - ')
    holders = [s for s in steps if 'secrets.' in s]
    assert text.count('secrets.') == 3 and len(holders) == 1 and sum('run:' in s for s in steps) == 1
    for name in ('APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'RAW_REPO_TOKEN'):
        assert f'{name}: ${{{{ secrets.{name} }}}}' in holders[0]
    assert holders[0].rstrip().endswith('python -I -S implementation/tools/measure_once/alpaca_sample_once.py')
    assert 'umask 077' in holders[0]
    step_limit = int(re.search(r'timeout-minutes: (\d+)', holders[0])[1])
    assert step_limit <= 20 and (m.PREFLIGHT_BUDGET_S + m.WALL_CLOCK_S + 2 * m.TIMEOUT_S + m.STORAGE_BUDGET_S) < step_limit * 60
    daily = (REPO / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    pins = re.findall(r'uses: (\S+)', text)
    assert pins and all(re.fullmatch(r'actions/[a-z-]+@[0-9a-f]{40}', p) and f'uses: {p}' in daily for p in pins)
    assert text.count('actions/checkout@') == text.count('persist-credentials: false') == 2


def test_plan_document_names_the_sample_and_the_limits():
    text = PLAN_DOC.read_text(encoding='utf-8')
    for needle in ('alpaca-sample-v1-', 'IEX', '비상업', '67', '40', 'claude/alpaca-sample-once-run', 'UNVERIFIED', 'GO',
                   'NO_DATA', 'SAME_AS_RAW', 'private_lines', '분배금', '-rN', 'python -I -S', 'needs:'):
        assert needle in text, needle
    for sid, info in SECURITIES.items():
        for symbol, _, _ in info['legs']:
            assert symbol in text, symbol
    for kind in m.LINE_SPECS:
        if kind not in ('ALPSAMPLE_PLAN', 'ALPSAMPLE_PLAN_CATEGORY'):
            assert kind in text, kind
    assert not re.search(r'[0-9]\.[0-9]{2}', text)        # no price-like number


def test_no_address_shaped_literal_in_the_new_files():
    spec = importlib.util.spec_from_file_location('autonomy_gate_a_guard_for_alpaca', ROOT / 'tools/autonomy_gate_a_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    for path in (TOOL, Path(__file__), WORKFLOW, PLAN_DOC):
        assert guard.email_patterns(path.read_bytes()) == Counter(), path.name
