"""One-time FV3-PIT-TICKER measurement (tools/measure_once/fv3_pit_ticker_measure.py): offline checks on synthetic,
in-memory inputs only (no network, no Secret).

- dei:TradingSymbol detection in XBRL instances and inline XBRL (case-insensitive tags, own dei prefix, nil, absent);
- instance-name prefix, instance choice, form.idx parsing (early stop, out-of-order rows), filing choice;
- client: route allow-list, refused redirects, retries, size caps, request / wall-clock / 403 / 429 stops;
- end to end on a fake SEC: counts only, never a ticker, CIK, URL or the User-Agent;
- missing / invalid User-Agent: one fixed STOP line, exit 2, no request.
Moved unchanged from branch claude/fv3-pit-ticker-measure (commit ead5ffdd) together with the tool. That branch's push-only
workflow is not carried over: the workflow that now runs this tool's functions is .github/workflows/sec-once-collect.yml,
whose shape is pinned in tests/test_sec_once_collect.py.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import gzip
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TOOL = ROOT / 'tools/measure_once/fv3_pit_ticker_measure.py'

_spec = importlib.util.spec_from_file_location('fv3_pit_ticker_measure', TOOL)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

AT = chr(64)   # no address-shaped literal in this file (repository email guard)
AGENT = 'Synthetic Measure Probe ' + 'probe' + AT + 'example' + '.org'
INSTANCE_NS = 'xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'


# ---- dei:TradingSymbol detection ---------------------------------------------------------------------------------------
def xbrl(*facts, dei='xmlns:dei="http://xbrl.sec.gov/dei/2014-01-31"'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<xbrli:xbrl ' + INSTANCE_NS + ' ' + dei + '>\n'
            + '\n'.join(facts) + '\n</xbrli:xbrl>\n').encode()


def test_xbrl_trading_symbol_and_period():
    facts = m.scan_instance(xbrl('<dei:DocumentType contextRef="FD2017">10-K</dei:DocumentType>',
                                 '<dei:DocumentPeriodEndDate contextRef="FD2017">2017-12-31</dei:DocumentPeriodEndDate>',
                                 '<dei:TradingSymbol contextRef="FD2017" id="f1">abcd</dei:TradingSymbol>'))
    assert facts == {'present': True, 'symbols': ['abcd'], 'period': date(2017, 12, 31)}


@pytest.mark.parametrize('fact, dei, present, symbols', [
    ('<DEI:TRADINGSYMBOL contextRef="c">ABCD</DEI:TRADINGSYMBOL>', 'xmlns:dei="http://xbrl.sec.gov/dei/2014-01-31"', True, ['ABCD']),
    ('<dei:tradingSymbol\n   contextRef="c">\n  ABCD \n</dei:tradingSymbol>', '', True, ['ABCD']),
    # the instance declares its own prefix for the dei namespace
    ('<d0:TradingSymbol contextRef="c">ABCD</d0:TradingSymbol>', 'xmlns:d0="http://xbrl.sec.gov/dei/2018-01-31"', True, ['ABCD']),
    ('<dei:TradingSymbol contextRef="c" xsi:nil="true"/>', '', True, []),                     # present, no value
    ('<dei:TradingSymbol contextRef="c"></dei:TradingSymbol>', '', True, []),
    ('<dei:TradingSymbolX contextRef="c">ABCD</dei:TradingSymbolX>', '', False, []),          # another element
    ('<abc:TradingSymbol contextRef="c">ABCD</abc:TradingSymbol>', 'xmlns:abc="http://example.org/abc/2017"', False, []),
    ('<dei:EntityRegistrantName contextRef="c">TradingSymbol Corp</dei:EntityRegistrantName>', '', False, []),
])
def test_xbrl_tag_detection_variants(fact, dei, present, symbols):
    facts = m.scan_instance(xbrl(fact, dei=dei))
    assert (facts['present'], facts['symbols']) == (present, symbols)


INLINE = ('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
          'xmlns:dei="http://xbrl.sec.gov/dei/2019-01-31"><body><table><tr>'
          '<td><ix:nonNumeric name="dei:TradingSymbol" contextRef="c1" id="f1"><span style="font-weight:bold">EFGH'
          '</span></ix:nonNumeric></td>'
          '<td><ix:nonNumeric contextRef="c2" name="dei:TradingSymbol" id="f2">EFGH.B</ix:nonNumeric></td></tr></table>'
          '<p><ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c1" format="ixt:datemonthdayyearen">'
          'September&#160;28, 2019</ix:nonNumeric></p></body></html>')


def test_inline_trading_symbols_and_period():
    facts = m.scan_instance(INLINE.encode())
    assert facts == {'present': True, 'symbols': ['EFGH', 'EFGH.B'], 'period': date(2019, 9, 28)}


@pytest.mark.parametrize('doc, present, symbols', [
    ("<IX:NONNUMERIC CONTEXTREF='c' NAME='DEI:TRADINGSYMBOL'>ijkl</IX:NONNUMERIC>", True, ['ijkl']),
    ('<ix:nonnumeric name="dei:tradingsymbol" contextref="c">&amp;X</ix:nonnumeric>', True, ['&X']),
    ('<ix:nonNumeric name="dei:TradingSymbol" contextRef="c" xsi:nil="true"/>', True, []),
    ('<ix:nonNumeric name="dei:SecurityExchangeName" contextRef="c">NYSE</ix:nonNumeric>', False, []),
    ('<ix:nonNumeric name="abc:TradingSymbol" contextRef="c">ABCD</ix:nonNumeric>', False, []),
    ('<p>Trading Symbol: ABCD (dei:TradingSymbol)</p>', False, []),
])
def test_inline_tag_detection_variants(doc, present, symbols):
    facts = m.scan_instance(('<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body>' + doc + '</body></html>').encode())
    assert (facts['present'], facts['symbols']) == (present, symbols)


@pytest.mark.parametrize('text, day', [
    ('2019-06-15', date(2019, 6, 15)), ('September 28, 2019', date(2019, 9, 28)), ('Dec. 31, 2017', date(2017, 12, 31)),
    ('28 September 2019', date(2019, 9, 28)), ('09/28/2019', date(2019, 9, 28)), ('June 30,2019', date(2019, 6, 30)),
    ('FY2019', None), ('September 2019', None), ('2019-02-30', None), ('', None),
])
def test_period_end_dates(text, day):
    assert m.parse_day(text) == day


def test_evaluate_flags():
    facts = m.scan_instance(INLINE.encode())
    flags = m.evaluate('efgh-20190928_htm.xml', True, facts, {'EFGH.B'})
    assert flags == {'instance': 1, 'inline': 1, 'trading_symbol': 1, 'symbol_multi': 1, 'prefix': 1, 'period_known': 1,
                     'post_mandate': 1, 'post_mandate_symbol': 1, 'prefix_eq_symbol': 1, 'prefix_eq_symbol_loose': 1,
                     'prefix_eq_today': 0}
    loose = m.evaluate('efghb-20190928_htm.xml', True, facts, {'EFGH.B'})
    assert (loose['prefix_eq_symbol'], loose['prefix_eq_symbol_loose'], loose['prefix_eq_today']) == (0, 1, 1)
    before = m.evaluate('form10-k.xml', False, {'present': False, 'symbols': [], 'period': date(2019, 6, 14)}, {'FORM'})
    assert before == {'instance': 1, 'inline': 0, 'trading_symbol': 0, 'symbol_multi': 0, 'prefix': 1, 'period_known': 1,
                      'post_mandate': 0, 'post_mandate_symbol': 0, 'prefix_eq_symbol': 0, 'prefix_eq_symbol_loose': 0,
                      'prefix_eq_today': 0}
    none = m.evaluate('instance.xml', False, {'present': True, 'symbols': ['ABCD'], 'period': None}, set())
    assert none['prefix'] == 0 and 'prefix_eq_symbol' not in none and none['period_known'] == 0


# ---- prefix, instance choice, form.idx ---------------------------------------------------------------------------------
@pytest.mark.parametrize('name, prefix', [
    ('abcd-20171231.xml', 'abcd'), ('abcd-20190928_htm.xml', 'abcd'), ('form10-k_htm.xml', 'form10'),
    ('d123456d10k_htm.xml', 'd123456d10k'), ('ab_cd-2017.xml', 'ab'), ('instance.xml', None), ('-x.xml', None),
    ('_x.xml', None), ('', None),
])
def test_name_prefix(name, prefix):
    assert m.name_prefix(name) == prefix


def test_pick_instance():
    traditional = {'abcd-20171231.xml': 900, 'abcd-20171231.xsd': 50, 'abcd-20171231_cal.xml': 10, 'abcd-20171231_def.xml': 10,
                   'abcd-20171231_lab.xml': 10, 'abcd-20171231_pre.xml': 10, 'FilingSummary.xml': 5, 'R1.htm': 1,
                   'R2.xml': 1, 'Financial_Report.xlsx': 3, '0000000001-17-000001-index.htm': 1}
    assert m.pick_instance(traditional) == ('abcd-20171231.xml', False)
    inline = {'abcd-20190928.htm': 5000, 'abcd-20190928_htm.xml': 700, 'abcd-20190928.xsd': 50, 'abcd-20190928_lab.xml': 9}
    assert m.pick_instance(inline) == ('abcd-20190928_htm.xml', True)
    inline_doc_only = {'abcd-20190928.htm': 5000, 'abcd-20190928.xsd': 50, 'abcd-20190928_pre.xml': 9, 'ex21.htm': 3}
    assert m.pick_instance(inline_doc_only) == ('abcd-20190928.htm', True)
    two = {'x-1.xml': 10, 'y-1.xml': 20}
    assert m.pick_instance(two) == ('y-1.xml', False)
    assert m.pick_instance({'doc10k.htm': 1, 'FilingSummary.xml': 1, 'primary_doc.xml': 1}) == (None, False)


def idx_row(form, cik, filed, accession, name='SYNTHETIC COMPANY INC'):
    return f'{form:<12}{name:<62}{cik:<12}{filed:<12}edgar/data/{cik}/{accession}.txt'


IDX_HEAD = ['Description:           Daily Index of EDGAR Dissemination Feed by Form Type',
            'Last Data Received:    March 31, 2017', '', 'Form Type   Company Name' + ' ' * 52 + 'CIK         Date Filed  File Name',
            '-' * 140]


def idx_text(rows):
    return ('\n'.join(IDX_HEAD + rows) + '\n').encode('latin-1')


def chunked(data, size=37):
    return (data[i:i + size] for i in range(0, len(data), size))


def test_form_idx_rows_stop_after_the_10_block():
    rows = [idx_row('1-A', 9, '2017-01-03', '0000000009-17-000001'),
            idx_row('10-D', 8, '2017-01-03', '0000000008-17-000001'),
            idx_row('10-K', 11, '2017-02-20', '0000000011-17-000002'),
            idx_row('10-K', 11, '2017-02-10', '0000000011-17-000001'),
            idx_row('10-K/A', 12, '2017-02-11', '0000000012-17-000001'),
            idx_row('10-Q', 12, '2017-03-01', '0000000012-17-000002'),
            idx_row('10-Q', 13, '2017-03-02', '0000000013-17-000001'),
            idx_row('11-K', 11, '2017-03-03', '0000000011-17-000003'),
            idx_row('13F-HR', 7, '2017-03-03', '0000000007-17-000001'),
            idx_row('4', 6, '2017-03-03', '0000000006-17-000001'),
            idx_row('8-K', 11, '2017-03-04', '0000000011-17-000004')]
    got, early, unsorted, parsed, bad = m.form_idx_rows(chunked(idx_text(rows)), {11: 0, 12: 1})
    assert (early, unsorted, parsed, bad) == (True, False, 10, 0)
    assert got == [(11, '10-K', '2017-02-20', '0000000011-17-000002'), (11, '10-K', '2017-02-10', '0000000011-17-000001'),
                   (12, '10-Q', '2017-03-01', '0000000012-17-000002')]
    assert m.pick_filings(got + [(12, '10-Q', '2017-01-30', '0000000012-17-000000')]) == {
        11: ('10-K', '0000000011-17-000001'), 12: ('10-Q', '0000000012-17-000000')}


def test_form_idx_rows_out_of_order_reads_everything():
    rows = [idx_row('10-K', 11, '2017-02-10', '0000000011-17-000001'),
            idx_row('10-D', 8, '2017-01-03', '0000000008-17-000001'),       # out of order: no early stop any more
            idx_row('8-K', 11, '2017-03-04', '0000000011-17-000004'),
            idx_row('10-Q', 11, '2017-03-05', '0000000011-17-000005')]
    got, early, unsorted, parsed, bad = m.form_idx_rows(chunked(idx_text(rows)), {11: 0})
    assert (early, unsorted, parsed, bad) == (False, True, 4, 0) and [g[1] for g in got] == ['10-K', '10-Q']


def test_form_idx_rows_take_the_cik_from_the_file_name():
    long_name = 'A VERY LONG SYNTHETIC REGISTRANT NAME THAT FILLS THE WHOLE COLUMN 2'
    rows = [f'{"10-K":<12}{long_name}11          2017-02-10  edgar/data/11/0000000011-17-000001.txt',   # glued to the CIK
            f'{"10-Q":<12}{"SYNTHETIC CO":<62}{12:<12}20170301    edgar/data/12/0000000012-17-000002.txt',   # YYYYMMDD
            f'{"10-Q":<12}{"SYNTHETIC CO":<62}{13:<12}2017-03-01  edgar/data/13/not-an-accession.txt',         # bad row
            '',
            idx_row('8-K', 11, '2017-03-04', '0000000011-17-000004')]
    got, early, unsorted, parsed, bad = m.form_idx_rows(chunked(idx_text(rows)), {11: 0, 12: 1, 13: 2})
    assert got == [(11, '10-K', '2017-02-10', '0000000011-17-000001'), (12, '10-Q', '2017-03-01', '0000000012-17-000002')]
    assert (early, unsorted, parsed, bad) == (True, False, 3, 1)


def test_form_idx_without_header_is_refused():
    with pytest.raises(m.FetchError) as exc:
        m.form_idx_rows(iter([b'no header here\n']), {1: 0})
    assert exc.value.code == 'BAD_FORM_IDX'


def test_directory_names():
    body = b'{"directory":{"item":[{"name":"abcd-20171231.xml","size":"123"},{"name":"../x","size":"1"},' \
           b'{"name":"a/b.xml"},{"name":"R1.htm","size":""}],"name":"/Archives/edgar/data/1/000000000117000001"}}'
    assert m.directory_names_json(chunked(body)) == {'abcd-20171231.xml': 123, 'R1.htm': 0}
    with pytest.raises(m.FetchError):
        m.directory_names_json(iter([b'<html>not json</html>']))
    page = (b'<a href="/Archives/edgar/data/11/000000001117000001/abcd-20171231.xml">x</a>'
            b'<a href="/ix?doc=/Archives/edgar/data/11/000000001117000001/abcd-20171231.htm">y</a>'
            b'<a href="https://example.org/elsewhere.xml">z</a>')
    assert m.directory_names_html(iter([page])) == {'abcd-20171231.xml': 0, 'abcd-20171231.htm': 0}


# ---- output format -----------------------------------------------------------------------------------------------------
LINE = {
    'start': re.compile(r'PITTICKER_START pool=\d+ panel=\d+ years=2016-2019 per_year=120 max_requests=2500 wall_clock_s=1200'),
    'counts': re.compile(r'PITTICKER (?:year=20\d\d|overall)(?: [a-z0-9_]+=\d+){17}'),
    'errors': re.compile(r'PITTICKER_ERRORS (?:year=20\d\d|overall) codes=(?:-|[A-Za-z][A-Za-z0-9_]*:\d+(?:,[A-Za-z][A-Za-z0-9_]*:\d+)*)'),
    'requests': re.compile(r'PITTICKER_REQUESTS(?: [a-z0-9_]+=\d+){12} mb_wire=\d+\.\d mb_body=\d+\.\d elapsed_s=\d+ '
                           r'stopped=(?:NONE|REQUEST_CAP|WALL_CLOCK|HTTP403_REPEATED|HTTP429_REPEATED|UNEXPECTED)'),
}


def assert_fixed_lines(lines):
    for line in lines:
        assert any(p.fullmatch(line) for p in LINE.values()), line
        assert AT not in line and '://' not in line and 'sec.gov' not in line and '/' not in line
        assert not re.search(r'\d{10}', line)


def test_summary_lines_are_fixed_and_carry_no_values():
    counts = Counter({'sampled': 120, 'filed': 118, 'instance': 112, 'trading_symbol': 34, 'prefix': 101,
                      'prefix_eq_symbol': 30, 'errors': 2, 'not_a_field': 7})
    assert m.format_counts('year=2017', counts) == (
        'PITTICKER year=2017 sampled=120 form_idx_ok=0 filed=118 form10k=0 instance=112 no_instance=0 inline=0 '
        'trading_symbol=34 symbol_multi=0 prefix=101 prefix_eq_symbol=30 prefix_eq_symbol_loose=0 prefix_eq_today=0 '
        'period_known=0 post_mandate=0 post_mandate_symbol=0 errors=2')
    errors = Counter({'HTTP404': 1, 'TimeoutError': 2, 'https://www.sec.gov/Archives/edgar/data/1/x': 1, 'ABCD 0000000011': 1,
                      'probe' + AT + 'example.org': 1})
    assert m.format_errors('overall', errors) == 'PITTICKER_ERRORS overall codes=HTTP404:1,OTHER:3,TimeoutError:2'
    assert m.format_errors('year=2016', Counter()) == 'PITTICKER_ERRORS year=2016 codes=-'
    requests = m.format_requests(Counter(total=987, form_idx=16, wire_bytes=12_345_678, body_bytes=99_000_000), 512.7, 'odd')
    assert requests == ('PITTICKER_REQUESTS total=987 form_idx=16 filing_index=0 instance=0 retries=0 http403=0 http429=0 '
                        'http5xx=0 idx_early_stop=0 idx_unsorted=0 idx_rows=0 idx_bad_rows=0 mb_wire=12.3 mb_body=99.0 '
                        'elapsed_s=512 stopped=UNEXPECTED')
    assert_fixed_lines([m.format_counts('overall', counts), m.format_errors('overall', errors), requests])
    for bad in ('cik=0000000011', 'year=2017 x', 'https://www.sec.gov/'):
        with pytest.raises(ValueError):
            m.format_counts(bad, counts)
    assert m.FetchError('https://www.sec.gov/x').code == 'OTHER' and m.Stop('weird').reason == 'UNEXPECTED'


# ---- client: fake transport --------------------------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, body, headers=None):
        self._body = io.BytesIO(body)
        self.headers = headers or {}
        self.closed = False

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True
        return False


def http_error(url, status, headers=None):
    return urllib.error.HTTPError(url, status, 'synthetic', headers or {}, None)


class FakeOpener:
    """Answers each call with the next item of `script` (a FakeResponse, an exception to raise, or a callable(url))."""

    def __init__(self, script=()):
        self.script = list(script)
        self.calls = []

    def open(self, request, timeout=None):
        assert isinstance(request, urllib.request.Request) and timeout == m.TIMEOUT_S
        self.calls.append((request.full_url, request.get_header('User-agent'), request.get_header('Accept-encoding')))
        item = self.script.pop(0)
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


URL = 'https://www.sec.gov/Archives/edgar/data/11/000000001117000001/index.json'


def client(script=(), clock=None):
    sleeps = []
    c = m.SecClient(AGENT, opener=FakeOpener(script), sleep=sleeps.append, clock=clock or Clock(0.0))
    return c, sleeps


@pytest.mark.parametrize('url', [
    'https://www.sec.gov/Archives/edgar/full-index/2016/QTR1/form.idx',
    'https://www.sec.gov/Archives/edgar/data/11/000000001117000001/index.json',
    'https://www.sec.gov/Archives/edgar/data/11/000000001117000001/abcd-20170930.xml',
])
def test_allow_list_accepts_the_three_routes(url):
    assert m.checked_url(url) == url


@pytest.mark.parametrize('url', [
    'http://www.sec.gov/Archives/edgar/full-index/2016/QTR1/form.idx',          # not https
    'https://sec.gov/Archives/edgar/full-index/2016/QTR1/form.idx',             # other host
    'https://data.sec.gov/submissions/CIK0000000011.json',
    'https://www.sec.gov.example.org/Archives/edgar/full-index/2016/QTR1/form.idx',
    'https://www.sec.gov' + AT + 'example.org/Archives/edgar/x',                  # userinfo trick
    'https://user' + AT + 'www.sec.gov/Archives/edgar/x',
    'https://www.sec.gov:8443/Archives/edgar/x',                                  # port
    'https://WWW.SEC.GOV/Archives/edgar/x',
    'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany',               # outside the archive
    'https://www.sec.gov/Archives/edgar/../../files/company_tickers.json',
    'https://www.sec.gov/Archives/edgar/x?y=1',
    'https://www.sec.gov/Archives/edgar/x#f',
    'https://www.sec.gov/Archives/edgar/a b',
    'https://www.sec.gov/Archives/edgar/x\r\nHost: example.org',
    'file:///etc/passwd', '', None,
])
def test_allow_list_refuses_everything_else(url):
    with pytest.raises(ValueError):
        m.checked_url(url)
    c, sleeps = client()
    with pytest.raises(ValueError):
        c.fetch(url, kind='instance', cap=10, consume=m.read_all)
    assert c._opener.calls == [] and c.counts['total'] == 0 and sleeps == []


def test_redirects_are_refused():
    assert any(isinstance(h, m._RejectRedirects) for h in m.build_opener().handlers)
    request = urllib.request.Request(URL)
    for target in ('https://www.sec.gov/Archives/edgar/data/11/other.json', 'https://example.org/x'):
        with pytest.raises(m.FetchError) as exc:
            m._RejectRedirects().redirect_request(request, None, 302, 'Found', {}, target)
        assert exc.value.code == 'REDIRECT_REJECTED'


def test_headers_sleep_and_gzip():
    body = b'x' * 200_000
    c, sleeps = client([FakeResponse(gzip.compress(body), {'Content-Encoding': 'gzip'})])
    assert c.fetch(URL, kind='filing_index', cap=1_000_000, consume=m.read_all) == body
    assert c._opener.calls == [(URL, AGENT, 'gzip')] and sleeps == [m.SLEEP_S]
    assert c.counts['total'] == c.counts['filing_index'] == 1 and c.counts['body_bytes'] == len(body)
    assert m.SLEEP_S >= 0.125   # at most 8 requests per second


def test_retries_429_5xx_and_network_errors_at_most_twice():
    c, sleeps = client([http_error(URL, 503), http_error(URL, 502), FakeResponse(b'ok')])
    assert c.fetch(URL, kind='instance', cap=10, consume=m.read_all) == b'ok'
    assert sleeps == [0.15, 2.0, 0.15, 6.0, 0.15] and (c.counts['total'], c.counts['retries'], c.counts['http5xx']) == (3, 2, 2)

    c, sleeps = client([http_error(URL, 500)] * 3)
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    assert exc.value.code == 'HTTP500' and c.counts['total'] == 3 and c.counts['retries'] == 2

    c, sleeps = client([http_error(URL, 429, {'Retry-After': '9'}), FakeResponse(b'ok')])
    assert c.fetch(URL, kind='instance', cap=10, consume=m.read_all) == b'ok' and sleeps == [0.15, 9.0, 0.15]

    c, sleeps = client([http_error(URL, 429, {'Retry-After': '900'}), TimeoutError('slow'), FakeResponse(b'ok')])
    assert c.fetch(URL, kind='instance', cap=10, consume=m.read_all) == b'ok' and sleeps == [0.15, 30.0, 0.15, 6.0, 0.15]

    c, sleeps = client([urllib.error.URLError('down')] * 3)
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    assert exc.value.code == 'URLError' and c.counts['total'] == 3


@pytest.mark.parametrize('status', [400, 403, 404, 410])
def test_other_statuses_are_not_retried(status):
    c, _ = client([http_error(URL, status)])
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    assert exc.value.code == f'HTTP{status}' and c.counts['total'] == 1 and c.counts['retries'] == 0


def test_size_caps_and_encodings():
    c, _ = client([FakeResponse(b'y' * 101)])
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=100, consume=m.read_all)
    assert exc.value.code == 'SIZE_CAP' and c.counts['total'] == 1     # never retried
    bomb = gzip.compress(b'\0' * (8 * 1024 * 1024))
    assert len(bomb) < 64 * 1024
    c, _ = client([FakeResponse(bomb, {'Content-Encoding': 'gzip'})])
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=1024 * 1024, consume=m.read_all)
    assert exc.value.code == 'SIZE_CAP' and c.counts['body_bytes'] <= 2 * 1024 * 1024
    c, _ = client([FakeResponse(b'x', {'Content-Encoding': 'br'})])
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=100, consume=m.read_all)
    assert exc.value.code == 'ENCODING_NOT_SUPPORTED'
    c, _ = client([FakeResponse(b'not gzip at all', {'Content-Encoding': 'gzip'})])
    with pytest.raises(m.FetchError) as exc:
        c.fetch(URL, kind='instance', cap=100, consume=m.read_all)
    assert exc.value.code == 'BAD_GZIP'


def test_deflate_body_is_read():
    body = b'z' * 100_000
    c, _ = client([FakeResponse(zlib.compress(body), {'Content-Encoding': 'deflate'})])
    assert c.fetch(URL, kind='instance', cap=200_000, consume=m.read_all) == body


def test_one_odd_filing_is_an_error_not_a_stop(monkeypatch):
    listing = FakeResponse(b'{"directory":{"item":[{"name":"abcd-20171231.xml","size":"9"},{"name":"abcd-20171231.xsd"}]}}')
    instance = FakeResponse(xbrl('<dei:TradingSymbol contextRef="c">ABCD</dei:TradingSymbol>'))
    c, _ = client([listing, instance])
    assert m.measure_filing(c, 11, '0000000011-17-000001', {'ABCD'})['prefix_eq_today'] == 1
    assert c._opener.calls[0][0] == URL
    assert c._opener.calls[1][0] == 'https://www.sec.gov/Archives/edgar/data/11/000000001117000001/abcd-20171231.xml'
    # index.json answered with something that is not a listing -> the -index.htm page
    page = b'<a href="/Archives/edgar/data/11/000000001117000001/abcd-20171231.xml">i</a>'
    c, _ = client([FakeResponse(b'<html>an error page served as 200</html>'), FakeResponse(page),
                   FakeResponse(instance._body.getvalue())])
    assert m.measure_filing(c, 11, '0000000011-17-000001', set())['trading_symbol'] == 1
    assert c._opener.calls[1][0].endswith('/11/000000001117000001/0000000011-17-000001-index.htm')

    def broken(body):
        raise RuntimeError('synthetic')
    monkeypatch.setattr(m, 'scan_instance', broken)
    c, _ = client([FakeResponse(listing._body.getvalue()), FakeResponse(instance._body.getvalue())])
    assert m.measure_filing(c, 11, '0000000011-17-000001', set()) == {'error': 'PARSE_RuntimeError'}
    c, _ = client([ValueError('synthetic')])
    assert m.measure_filing(c, 11, '0000000011-17-000001', set()) == {'error': 'UNEXPECTED_ValueError'}
    c, _ = client([FakeResponse(b'{"directory":{"item":[{"name":"doc10k.htm"}]}}')])
    assert m.measure_filing(c, 11, '0000000011-17-000001', set()) == {'no_instance': 1}
    c, _ = client([http_error(URL, 500)] * 3)
    assert m.measure_filing(c, 11, '0000000011-17-000001', set()) == {'error': 'HTTP500'}      # no fallback for 5xx
    c, _ = client()
    c.counts['total'] = m.MAX_REQUESTS
    with pytest.raises(m.Stop):
        m.measure_filing(c, 11, '0000000011-17-000001', set())


def test_run_stops():
    c, _ = client()
    c.counts['total'] = m.MAX_REQUESTS
    with pytest.raises(m.Stop) as stop:
        c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    assert stop.value.reason == 'REQUEST_CAP' and c._opener.calls == []
    c, _ = client(clock=Clock(0.0, float(m.WALL_CLOCK_S)))
    with pytest.raises(m.Stop) as stop:
        c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    assert stop.value.reason == 'WALL_CLOCK' and c._opener.calls == []
    c, _ = client([http_error(URL, 403)] * m.STOP_AFTER_403)
    for _ in range(m.STOP_AFTER_403 - 1):
        with pytest.raises(m.FetchError):
            c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    with pytest.raises(m.Stop) as stop:
        c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
    assert stop.value.reason == 'HTTP403_REPEATED'
    c, _ = client([http_error(URL, 403)] * 4 + [FakeResponse(b'ok')] + [http_error(URL, 403)] * 4)   # not in a row
    for _ in range(9):
        try:
            c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
        except m.FetchError:
            pass
    assert c.counts['http403'] == 8 and c._opener.script == []
    c, _ = client([http_error(URL, 429)] * m.STOP_AFTER_429)
    with pytest.raises(m.Stop) as stop:
        for _ in range(m.STOP_AFTER_429):
            try:
                c.fetch(URL, kind='instance', cap=10, consume=m.read_all)
            except m.FetchError:
                pass
    assert stop.value.reason == 'HTTP429_REPEATED' and c.counts['total'] == m.STOP_AFTER_429


# ---- end to end on a fake SEC ------------------------------------------------------------------------------------------
def fake_sec(pool, picked):
    """A fake SEC for three panel CIKs: a (10-K, XBRL instance with TradingSymbol), b (10-K, inline XBRL with two
    symbols, gzip), c (10-Q only, index.json 404 -> -index.htm, no TradingSymbol, prefix = today's ticker)."""
    a, b, c = picked
    today_c = m._alnum(sorted(pool[f'{c:010d}'])[0])
    rows = [idx_row('1-A', 9, '2016-01-04', '0000000009-16-000001'),
            idx_row('10-D', 8, '2016-01-04', '0000000008-16-000001'),
            idx_row('10-K', a, '2016-02-20', f'{a:010d}-16-000001'),
            idx_row('10-K', b, '2016-02-21', f'{b:010d}-16-000002'),
            idx_row('10-K', b, '2016-03-21', f'{b:010d}-16-000003'),
            idx_row('10-K/A', c, '2016-02-22', f'{c:010d}-16-000004'),
            idx_row('10-Q', a, '2016-01-20', f'{a:010d}-16-000005'),
            idx_row('10-Q', c, '2016-03-01', f'{c:010d}-16-000006'),
            idx_row('13F-HR', 7, '2016-03-03', '0000000007-16-000001'),
            idx_row('4', 6, '2016-03-03', '0000000006-16-000001'),
            idx_row('10-K', c, '2016-03-04', f'{c:010d}-16-000007')]      # after the stop: never read
    form_idx = idx_text(rows)
    a_xml = xbrl('<dei:DocumentPeriodEndDate contextRef="c">2015-12-31</dei:DocumentPeriodEndDate>',
                 '<dei:TradingSymbol contextRef="c">ABCD</dei:TradingSymbol>')
    b_xml = xbrl('<dei:DocumentPeriodEndDate contextRef="c">2019-09-28</dei:DocumentPeriodEndDate>',
                 '<dei:TradingSymbol contextRef="c1">EFGH</dei:TradingSymbol>',
                 '<dei:TradingSymbol contextRef="c2">EFGH.B</dei:TradingSymbol>', dei='xmlns:dei="http://xbrl.sec.gov/dei/2019-01-31"')
    c_xml = xbrl('<dei:DocumentPeriodEndDate contextRef="c">2016-01-31</dei:DocumentPeriodEndDate>')
    base = 'https://www.sec.gov/Archives/edgar/data/'

    def listing(*names):
        return ('{"directory":{"item":[' + ','.join('{"name":"%s","size":"%d"}' % (n, 10 + i) for i, n in enumerate(names))
                + ']}}').encode()

    routes = {
        f'{base}{a}/{a:010d}16000001/index.json': FakeResponse(listing('abcd-20151231.xml', 'abcd-20151231.xsd',
                                                                        'abcd-20151231_lab.xml', 'FilingSummary.xml')),
        f'{base}{a}/{a:010d}16000001/abcd-20151231.xml': FakeResponse(a_xml),
        f'{base}{b}/{b:010d}16000002/index.json': FakeResponse(listing('efgh-20190928.htm', 'efgh-20190928_htm.xml',
                                                                        'efgh-20190928.xsd')),
        f'{base}{b}/{b:010d}16000002/efgh-20190928_htm.xml': FakeResponse(gzip.compress(b_xml), {'Content-Encoding': 'gzip'}),
        f'{base}{c}/{c:010d}16000006/index.json': http_error('x', 404),
        f'{base}{c}/{c:010d}16000006/{c:010d}-16-000006-index.htm': FakeResponse(
            f'<a href="/Archives/edgar/data/{c}/{c:010d}16000006/{today_c}-20160131.xml">i</a>'
            f'<a href="/Archives/edgar/data/{c}/{c:010d}16000006/{today_c}-20160131.xsd">s</a>'.encode()),
        f'{base}{c}/{c:010d}16000006/{today_c}-20160131.xml': FakeResponse(c_xml),
    }

    def answer(url):
        if url.endswith('/form.idx'):
            assert re.fullmatch(r'https://www\.sec\.gov/Archives/edgar/full-index/201[6-9]/QTR[1-4]/form\.idx', url)
            return FakeResponse(form_idx)
        item = routes[url]
        return FakeResponse(item._body.getvalue(), item.headers) if isinstance(item, FakeResponse) else item

    return answer


def test_end_to_end_counts_only():
    pool = m.load_pool()
    panel = m.sample_panel(pool)
    assert len(pool) >= 400 and len(panel) == m.PER_YEAR == 120
    assert panel == sorted(panel, key=lambda cik: hashlib.sha256(cik.encode()).hexdigest())
    picked = [int(panel[5]), int(panel[17]), int(panel[42])]
    answer = fake_sec(pool, picked)
    per_year = 4 + 2 + 2 + 3
    opener = FakeOpener([answer] * (per_year * 4))
    lines = []
    code = m.main(environ={'SEC_USER_AGENT': AGENT}, opener=opener, sleep=lambda s: None, clock=Clock(0.0), out=lines.append)
    assert code == 0 and opener.script == []
    assert {agent for _, agent, _ in opener.calls} == {AGENT} and all(m.checked_url(url) for url, _, _ in opener.calls)
    assert len(lines) == 1 + 2 * 4 + 3
    assert_fixed_lines(lines)
    year = ('sampled=120 form_idx_ok=4 filed=3 form10k=2 instance=3 no_instance=0 inline=1 trading_symbol=2 symbol_multi=1 '
            'prefix=3 prefix_eq_symbol=2 prefix_eq_symbol_loose=2 prefix_eq_today=1 period_known=3 post_mandate=1 '
            'post_mandate_symbol=1 errors=0')
    for i, y in enumerate(m.YEARS):
        assert lines[1 + 2 * i] == f'PITTICKER year={y} ' + year
        assert lines[2 + 2 * i] == f'PITTICKER_ERRORS year={y} codes=-'
    assert lines[-3] == ('PITTICKER overall sampled=480 form_idx_ok=16 filed=12 form10k=8 instance=12 no_instance=0 inline=4 '
                         'trading_symbol=8 symbol_multi=4 prefix=12 prefix_eq_symbol=8 prefix_eq_symbol_loose=8 '
                         'prefix_eq_today=4 period_known=12 post_mandate=4 post_mandate_symbol=4 errors=0')
    assert lines[-2] == 'PITTICKER_ERRORS overall codes=-'
    assert lines[-1].startswith('PITTICKER_REQUESTS total=44 form_idx=16 filing_index=16 instance=12 retries=0 http403=0 '
                                'http429=0 http5xx=0 idx_early_stop=16 idx_unsorted=0 idx_rows=160 idx_bad_rows=0 ')
    assert lines[-1].endswith(' elapsed_s=0 stopped=NONE')
    text = '\n'.join(lines)
    assert AGENT not in text and 'ABCD' not in text and 'EFGH' not in text
    for cik in picked:
        assert f'{cik:010d}' not in text
        assert cik < 1000 or not re.search(rf'(?<![0-9]){cik}(?![0-9])', text)


def test_end_to_end_stop_keeps_the_counts():
    pool = m.load_pool()
    opener = FakeOpener([http_error('x', 403)] * m.STOP_AFTER_403)
    lines = []
    code = m.main(environ={'SEC_USER_AGENT': AGENT}, opener=opener, sleep=lambda s: None, clock=Clock(0.0), out=lines.append)
    # 2016: four quarters refused (403, not retried); the fifth 403 (2017 QTR1) stops the run inside 2017, whose partial
    # line is still printed; nothing after it is requested
    assert code == 3 and len(lines) == 1 + 2 * 2 + 3 and opener.script == []
    assert_fixed_lines(lines)
    empty = ('sampled=120 form_idx_ok=0 filed=0 form10k=0 instance=0 no_instance=0 inline=0 trading_symbol=0 symbol_multi=0 '
             'prefix=0 prefix_eq_symbol=0 prefix_eq_symbol_loose=0 prefix_eq_today=0 period_known=0 post_mandate=0 '
             'post_mandate_symbol=0 errors=0')
    assert lines[1:5] == ['PITTICKER year=2016 ' + empty, 'PITTICKER_ERRORS year=2016 codes=FORM_IDX_HTTP403:4',
                          'PITTICKER year=2017 ' + empty, 'PITTICKER_ERRORS year=2017 codes=-']
    assert lines[-2] == 'PITTICKER_ERRORS overall codes=FORM_IDX_HTTP403:4'
    assert lines[-1].startswith('PITTICKER_REQUESTS total=5 form_idx=5 ') and lines[-1].endswith(' stopped=HTTP403_REPEATED')
    assert len(pool) >= 400


# ---- User-Agent ----------------------------------------------------------------------------------------------------------
class NoNetwork:
    def open(self, *args, **kwargs):
        raise AssertionError('no request may be made')


@pytest.mark.parametrize('environ, line', [
    ({}, m.STOP_MISSING), ({'SEC_USER_AGENT': ''}, m.STOP_MISSING), ({'SEC_USER_AGENT': '   '}, m.STOP_MISSING),
    ({'SEC_USER_AGENT': 'Synthetic Probe without contact'}, m.STOP_INVALID),
    ({'SEC_USER_AGENT': 'probe' + AT + 'example.org'}, m.STOP_INVALID),                      # contact only
    ({'SEC_USER_AGENT': 'Synthetic Probe probe' + AT + 'example.invalid'}, m.STOP_INVALID),  # placeholder
    ({'SEC_USER_AGENT': AGENT + '\r\nX-Injected: 1'}, m.STOP_INVALID),
    ({'SEC_USER_AGENT': AGENT + 'é'}, m.STOP_INVALID),
])
def test_user_agent_missing_or_invalid_stops_before_any_request(environ, line):
    lines = []
    assert m.main(environ=environ, opener=NoNetwork(), sleep=None, clock=None, out=lines.append) == 2
    assert lines == [line]
    assert line in ('PITTICKER_STOP reason=SEC_USER_AGENT_MISSING', 'PITTICKER_STOP reason=SEC_USER_AGENT_INVALID')


def test_script_without_user_agent_prints_one_fixed_line(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != 'SEC_USER_AGENT' and k.lower() not in
           ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9')   # a request could not leave anyway
    run = subprocess.run([sys.executable, str(TOOL)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert (run.returncode, run.stdout, run.stderr) == (2, 'PITTICKER_STOP reason=SEC_USER_AGENT_MISSING\n', '')
    assert list(tmp_path.iterdir()) == []


# ---- static: files ------------------------------------------------------------------------------------------------------
def test_no_address_shaped_literal_in_the_new_files():
    spec = importlib.util.spec_from_file_location('autonomy_gate_a_guard_for_fv3', ROOT / 'tools/autonomy_gate_a_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    for path in (TOOL, Path(__file__)):
        assert guard.email_patterns(path.read_bytes()) == Counter(), path.name
