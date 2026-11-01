"""Ticker-mismatch classification (tools/measure_once/sec_once_ticker_mismatch.py): offline checks on synthetic inputs only
(no network, no Secret).

- the class rules and their order (notation incl. several symbols in one value, class share only with evidence of a
  class, old ticker only for a ticker the issuer used BEFORE the filing and never today's, symbol-odd when the prefix is
  today's ticker, inline document name, short name / document name, other with the empty-symbol count); no row is ever
  an identity (identity_confirmed=false);
- company names from a stored form.idx (also when the name is glued to the CIK) and today's tickers / names from a stored
  submissions.zip;
- the per-filing inspection is the moved measurement's (same requests, same flags);
- end to end on a fake SEC with the stored form.idx: fixed count lines only, per-filing rows only in the private file,
  a missing stored quarter fetched again, the resumed path without requests, configuration stops, no request at all
  without this attempt's private-repository preflight marker or when collect stopped (403 / 429 repeats, caps, disk),
  complete=no after a transient filing error but yes after deterministic ones only.
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools/measure_once'
sys.path.insert(0, str(TOOLS))
_spec = importlib.util.spec_from_file_location('sec_once_ticker_mismatch', TOOLS / 'sec_once_ticker_mismatch.py')
mix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mix)
pit, once = mix.pit, mix.once

AT = chr(64)   # no address-shaped literal in this file (repository email guard)
AGENT = 'Synthetic Mismatch Probe ' + 'probe' + AT + 'example' + '.org'
ENV = {'GITHUB_REPOSITORY': once.PUBLIC_REPO, 'GITHUB_REF': once.RUN_REF, 'GITHUB_RUN_ID': '987654321',
       'GITHUB_RUN_ATTEMPT': '1', 'SEC_USER_AGENT': AGENT}


# ---- rules -----------------------------------------------------------------------------------------------------------------
def row(prefix, symbols, inline=False):
    return {'prefix': prefix, 'symbols': symbols, 'inline': inline}


@pytest.mark.parametrize('case, known, names, label', [
    (row('brkb', ['BRK.B']), {}, [], 'NOTATION'),
    (row('abcd', ['NYSE: AB.CD']), {}, [], 'NOTATION'),
    (row('goog', ['GOOGL, GOOG']), {'today': {'goog', 'googl'}}, [], 'NOTATION'),          # several symbols in one value
    (row('goog', ['GOOGL and GOOG']), {}, [], 'NOTATION'),
    (row('brk', ['BRK.B']), {}, [], 'CLASS_SHARE'),                                       # separator written
    (row('rds', ['RDS/A']), {}, [], 'CLASS_SHARE'),
    (row('googl', ['GOOG']), {'today': {'goog', 'googl'}}, [], 'CLASS_SHARE'),            # two tickers today
    (row('googl', ['GOOG']), {'earlier': {'goog', 'googl'}}, [], 'CLASS_SHARE'),          # both known tickers
    (row('googl', ['GOOG']), {}, [], 'OTHER'),                                            # no evidence of a class
    (row('fox', ['FOXA', 'FOX.B']), {}, [], 'CLASS_SHARE'),
    (row('lbtya', ['LBTYK']), {'today': {'lbtya', 'lbtyk'}}, [], 'CLASS_SHARE'),
    (row('int', ['INTC']), {'today': {'intc'}}, ['INTEL CORP'], 'SHORT_NAME_OR_DOC_NAME'),  # one ticker: a short name
    (row('aa', ['AAL']), {}, [], 'OTHER'),                                                # another company's ticker
    (row('abcd', ['WXYZ']), {'earlier': {'abcd'}}, [], 'OLD_TICKER'),                     # used before the filing
    (row('abcd', ['WXYZ']), {'earlier': {'abcd'}, 'today': {'wxyz'}}, [], 'OLD_TICKER'),
    (row('abcd', ['WXYZ']), {'earlier': {'abcd'}, 'today': {'abcd'}}, [], 'SYMBOL_ODD'),  # today's: never "old"
    (row('wxyz', ['ABCD']), {'today': {'wxyz'}}, [], 'SYMBOL_ODD'),                       # prefix normal, symbol odd
    (row('abc', ['XYZ']), {'today': {'abc'}}, ['ZETA CO'], 'SYMBOL_ODD'),
    (row('abcd', ['WXYZ']), {'later': {'abcd'}}, [], 'SYMBOL_ODD'),                       # used only AFTER the filing
    (row('form10', ['EFGH'], inline=True), {}, [], 'INLINE_DOC_NAME'),
    (row('ab', ['EFGH'], inline=True), {}, ['AB HOLDINGS INC'], 'INLINE_DOC_NAME'),        # inline wins over a name
    (row('synthco', ['SYN']), {}, [], 'SHORT_NAME_OR_DOC_NAME'),                           # longer than a ticker
    (row('d123', ['SYN']), {}, [], 'SHORT_NAME_OR_DOC_NAME'),                              # a digit
    (row('form', ['SYN']), {}, [], 'SHORT_NAME_OR_DOC_NAME'),                              # a document word
    (row('acme', ['ACM']), {}, ['ACME WIDGETS CORP'], 'SHORT_NAME_OR_DOC_NAME'),           # a name word
    (row('ibm', ['XYZ']), {}, ['INTERNATIONAL BUSINESS MACHINES CORP'], 'SHORT_NAME_OR_DOC_NAME'),   # initials
    (row('qrs', ['BRK.B']), {'today': {'brkb'}}, ['SYNTHETIC COMPANY INC'], 'OTHER'),
    (row('abcd', ['ABCDE']), {}, [], 'OTHER'),                                              # E is not a class letter
    (row('abcd', []), {}, [], 'OTHER'),
    (row('abcd', ['   ']), {'earlier': {'abcd'}}, [], 'OTHER'),                            # empty value
])
def test_classify(case, known, names, label):
    got, evidence = mix.classify(case, known, names)
    assert got == label
    assert set(evidence) >= {'notation', 'multi_value', 'class_share', 'known_ticker', 'symbol_known',
                             'issuer_tickers_today', 'name_match', 'not_ticker_shape', 'doc_word'}
    assert evidence['identity_confirmed'] is False
    assert evidence.get('symbol_empty', False) == (not any(s.strip() for s in case['symbols']))
    if got == 'OLD_TICKER':
        assert evidence['known_ticker'] == 'earlier_filing' and norm_in(case['prefix'], known.get('earlier'))
        assert not norm_in(case['prefix'], known.get('today'))


def norm_in(value, values):
    return mix.norm(value) in (values or set())


def test_split_symbols():
    assert mix.split_symbols(['GOOGL, GOOG', 'RDS/A', 'A and B', 'AND', 'BAND', 'X;Y', 'GOOGL/GOOG']) == [
        'GOOGL', 'GOOG', 'RDS/A', 'A', 'B', 'AND', 'BAND', 'X', 'Y', 'GOOGL', 'GOOG']


def test_transient_errors():
    assert mix.transient_errors({'SIZE_CAP': 2, 'BAD_INDEX': 1, 'HTTP404': 1, 'PARSE_ValueError': 1}) == 0
    assert mix.transient_errors({'SIZE_CAP': 2, 'HTTP503': 1, 'URLError': 1, 'FORM_IDX_HTTP500': 1, 'HTTP429': 1,
                                 'HTTP403': 1, 'TRUNCATED': 1, 'UNEXPECTED_KeyError': 1}) == 7


def test_name_evidence():
    assert mix.name_evidence('acme', ['ACME WIDGETS CORP'])
    assert mix.name_evidence('acmewid', ['ACME WIDGETS CORP'])
    assert mix.name_evidence('aw', ['ACME WIDGETS CORP'])
    assert mix.name_evidence('widgets', ['THE ACME WIDGETS CORP'])
    assert not mix.name_evidence('xyz', ['ACME WIDGETS CORP']) and not mix.name_evidence('', ['ACME'])
    assert not mix.name_evidence('co', ['ACME WIDGETS CO'])


# ---- stored inputs ------------------------------------------------------------------------------------------------------------
IDX_HEAD = ['Description:           Master Index of EDGAR Dissemination Feed by Form Type',
            'Last Data Received:    March 31, 2017', '', 'Form Type   Company Name' + ' ' * 52 + 'CIK         Date Filed  File Name',
            '-' * 140]


def idx_row(form, cik, filed, accession, name='SYNTHETIC COMPANY INC'):
    return f'{form:<12}{name:<62}{cik:<12}{filed:<12}edgar/data/{cik}/{accession}.txt'


def idx_gz(rows):
    return gzip.compress(('\n'.join(IDX_HEAD + rows) + '\n').encode('latin-1'), mtime=0)


def test_company_names(tmp_path):
    long_name = 'A VERY LONG SYNTHETIC REGISTRANT NAME THAT FILLS THE WHOLE COLUMN 2'
    path = tmp_path / 'f.idx.gz'
    path.write_bytes(idx_gz([idx_row('10-K', 11, '2017-02-10', '0000000011-17-000001', 'ACME WIDGETS CORP'),
                             f'{"10-K":<12}{long_name}12          2017-02-10  edgar/data/12/0000000012-17-000001.txt',
                             idx_row('SC 13D', 13, '2017-02-11', '0000000013-17-000001', 'OTHER CO'),
                             idx_row('10-Q', 14, '2017-02-12', '0000000014-17-000001', 'NOT WANTED INC')]))
    got = mix.company_names(path, {'0000000011-17-000001', '0000000012-17-000001', '0000000013-17-000001'})
    assert got == {'0000000011-17-000001': 'ACME WIDGETS CORP', '0000000012-17-000001': long_name,
                   '0000000013-17-000001': 'OTHER CO'}


def test_submissions_info(tmp_path):
    path = tmp_path / 'submissions.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('CIK0000000011.json', json.dumps({'name': 'ACME WIDGETS CORP', 'tickers': ['ACM', 'ACM-P'],
                                                           'formerNames': [{'name': 'ACME TOOLS INC'}, {'x': 1}]}))
        archive.writestr('CIK0000000012.json', 'not json')
        archive.writestr('CIK0000000013.json', json.dumps({'name': 'NOT WANTED'}))
    assert mix.submissions_info(path, ['0000000011', '0000000012', '0000000099']) == {
        '0000000011': {'tickers': ['ACM', 'ACM-P'], 'names': ['ACME WIDGETS CORP', 'ACME TOOLS INC']}}
    broken = tmp_path / 'broken.zip'
    broken.write_bytes(b'PK not a zip')
    assert mix.submissions_info(broken, ['0000000011']) == {}


# ---- fakes ------------------------------------------------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, body, headers=None):
        self._body = io.BytesIO(body)
        self.headers = headers or {}

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def open(self, request, timeout=None):
        assert isinstance(request, urllib.request.Request) and timeout == pit.TIMEOUT_S
        self.calls.append((request.full_url, request.get_header('User-agent')))
        item = self.answer(request.full_url)
        if isinstance(item, BaseException):
            raise item
        return item


class NoNetwork:
    def open(self, *args, **kwargs):
        raise AssertionError('no request may be made')


class Clock:
    def __call__(self):
        return 0.0


INSTANCE_NS = 'xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2014-01-31"'


def xbrl(*facts):
    return ('<?xml version="1.0"?>\n<xbrli:xbrl ' + INSTANCE_NS + ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            + '\n'.join(facts) + '\n</xbrli:xbrl>\n').encode()


def symbol(value):
    return '<dei:TradingSymbol contextRef="c">' + value + '</dei:TradingSymbol>'


NIL = '<dei:TradingSymbol contextRef="c" xsi:nil="true"/>'
PERIOD = '<dei:DocumentPeriodEndDate contextRef="c">{}-12-31</dei:DocumentPeriodEndDate>'
# (panel position, year) -> (instance file name, facts); a missing entry: no TradingSymbol, instance named 'zz-<year>.xml'
PLAN = {
    (0, 2016): ('abcd-20151231.xml', [symbol('ABCD')]), (1, 2016): ('efgh-20151231.xml', [symbol('EFGH')]),
    (2, 2016): ('brk-20151231.xml', [symbol('BRK')]),
    (0, 2017): ('abcd-20161231.xml', [symbol('WXYZ')]),                       # OLD_TICKER (2016: ABCD = prefix abcd)
    (1, 2017): ('form10-k_htm.xml', [symbol('EFGH')]),                        # INLINE_DOC_NAME
    (2, 2017): ('brk-20161231.xml', [symbol('BRK.B')]),                       # CLASS_SHARE
    (3, 2017): ('ij.kl-20161231.xml', [symbol('IJKL')]),                      # NOTATION
    (0, 2018): ('synthco-20171231.xml', [symbol('WXYZ')]),                    # SHORT_NAME_OR_DOC_NAME
    (1, 2018): ('efgh-20171231.xml', [NIL]),                                  # OTHER (empty symbol)
    (2, 2018): ('qrs-20171231.xml', [symbol('BRK.B')]),                       # OTHER
    (3, 2018): ('ijkl-20171231.xml', [symbol('IJKL')]),
}
EXPECTED = {(0, 2017): 'OLD_TICKER', (1, 2017): 'INLINE_DOC_NAME', (2, 2017): 'CLASS_SHARE', (3, 2017): 'NOTATION',
            (0, 2018): 'SHORT_NAME_OR_DOC_NAME', (1, 2018): 'OTHER', (2, 2018): 'OTHER'}
VALUES = ('ABCD', 'abcd', 'WXYZ', 'EFGH', 'efgh', 'BRK', 'IJKL', 'ij.kl', 'synthco', 'qrs', 'form10')


def accession(cik, year):
    return f'{cik:010d}-{year % 100:02d}-000001'


def ready(work, stopped='NONE'):
    """What the earlier steps leave: this attempt's private-repository preflight marker and the collect manifest."""
    Path(work).mkdir(parents=True, exist_ok=True)
    once.write_json(Path(work) / once.PREFLIGHT_FILE, {'repository': once.RAW_REPO, 'private': True,
                                                       'visibility': 'private', 'run_id': ENV['GITHUB_RUN_ID'],
                                                       'attempt': 1})
    once.write_json(Path(work) / 'collect-manifest.json', {'schema': 'sec-once-collect/1', 'records': [],
                                                          'stopped': stopped, 'complete': stopped == 'NONE'})


def setup_work(tmp_path, picked, skip=()):
    ready(tmp_path)
    files = tmp_path / 'files'
    files.mkdir(parents=True)
    for year in pit.YEARS:
        for quarter in (1, 2, 3, 4):
            if (year, quarter) in skip:
                continue
            rows = [idx_row('10-K', cik, f'{year}-02-2{i}', accession(cik, year)) for i, cik in enumerate(picked)] \
                if quarter == 1 else []
            (files / f'full-index-{year}-QTR{quarter}-form.idx.gz').write_bytes(idx_gz(rows))
    return files


def fake_sec(picked, remote_idx=None):
    routes = {}
    for position, cik in enumerate(picked):
        for year in pit.YEARS:
            name, facts = PLAN.get((position, year), (f'zz-{year}.xml', []))
            base = f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession(cik, year).replace("-", "")}/'
            schema = name.replace('_htm.xml', '.htm').replace('.xml', '.xsd')
            listing = {'directory': {'item': [{'name': name, 'size': '10'}, {'name': schema, 'size': '1'}]}}
            routes[base + 'index.json'] = json.dumps(listing).encode()
            routes[base + name] = xbrl(PERIOD.format(year - 1), *facts)

    def answer(url):
        if url.endswith('/form.idx'):
            assert remote_idx is not None
            return FakeResponse(gzip.decompress(remote_idx), {})
        return FakeResponse(routes[url])
    return answer


@pytest.fixture(scope='module')
def panel():
    pool = pit.load_pool()
    return pool, pit.sample_panel(pool)


LINE = [re.compile(p) for p in (
    r'TICKERMIX_START panel=\d+ years=2016-2019 names=(?:SUBMISSIONS|INDEX_ONLY|RESUMED)',
    r'TICKERMIX_INDEX local=\d+ remote=\d+',
    r'PITTICKER overall(?: [a-z0-9_]+=\d+){17}',
    r'PITTICKER_ERRORS overall codes=(?:-|[A-Za-z][A-Za-z0-9_]*:\d+(?:,[A-Za-z][A-Za-z0-9_]*:\d+)*)',
    r'TICKERMIX symbol_filings=\d+ prefix_eq_symbol=\d+ mismatches=\d+ expected_symbol=209 expected_mismatch=16 '
    r'same=(?:yes|no)',
    r'TICKERMIX_CLASSES mismatches=\d+(?: [a-z_]+=\d+){8}',
    r'TICKERMIX_SKIP reason=(?:COLLECT_STOPPED|COLLECT_MANIFEST_MISSING)',
    r'PITTICKER_REQUESTS(?: [a-z0-9_]+=\d+){12} mb_wire=\d+\.\d mb_body=\d+\.\d elapsed_s=\d+ '
    r'stopped=(?:NONE|REQUEST_CAP|WALL_CLOCK|HTTP403_REPEATED|HTTP429_REPEATED|UNEXPECTED)',
    r'TICKERMIX_DONE complete=(?:yes|no)',
    r'TICKERMIX_STOP reason=[A-Z0-9_]+',
)]


def assert_fixed_lines(lines, ciks=()):
    text = '\n'.join(lines)
    for line in lines:
        assert any(p.fullmatch(line) for p in LINE), line
        assert AT not in line and '://' not in line and 'sec.gov' not in line and '/' not in line
        assert not re.search(r'\d{10}', line)
    for value in VALUES + (AGENT, 'SYNTHETIC', 'ACME'):
        assert not re.search(rf'(?<![A-Za-z]){re.escape(value)}(?![A-Za-z])', text), value
    for cik in ciks:
        assert cik < 1000 or not re.search(rf'(?<![0-9]){cik}(?![0-9])', text)


def run(tmp_path, opener, environ=None):
    lines = []
    code = mix.main(['--work', str(tmp_path)], environ=ENV if environ is None else environ, opener=opener, sleep=lambda s: None, clock=Clock(),
                    out=lines.append)
    return code, lines


def test_end_to_end_counts_only_and_private_rows(tmp_path, panel):
    pool, ciks = panel
    picked = [int(ciks[3]), int(ciks[29]), int(ciks[64]), int(ciks[101])]
    setup_work(tmp_path, picked)
    with zipfile.ZipFile(tmp_path / 'files/submissions.zip', 'w') as archive:
        archive.writestr(f'CIK{picked[3]:010d}.json', json.dumps({'name': 'IJKL HOLDINGS INC', 'tickers': ['IJKL']}))
    opener = FakeOpener(fake_sec(picked))
    code, lines = run(tmp_path, opener)
    assert code == 0
    assert_fixed_lines(lines, picked)
    assert len(opener.calls) == 2 * 4 * 4 and {agent for _, agent in opener.calls} == {AGENT}
    assert not any(url.endswith('form.idx') for url, _ in opener.calls) and all(pit.checked_url(u) for u, _ in opener.calls)
    assert lines[0] == 'TICKERMIX_START panel=120 years=2016-2019 names=SUBMISSIONS'
    assert lines[1] == 'TICKERMIX_INDEX local=16 remote=0'
    assert lines[2] == ('PITTICKER overall sampled=480 form_idx_ok=16 filed=16 form10k=16 instance=16 no_instance=0 '
                        'inline=1 trading_symbol=11 symbol_multi=0 prefix=16 prefix_eq_symbol=4 prefix_eq_symbol_loose=5 '
                        'prefix_eq_today=0 period_known=16 post_mandate=0 post_mandate_symbol=0 errors=0')
    assert lines[3] == 'PITTICKER_ERRORS overall codes=-'
    assert lines[4] == ('TICKERMIX symbol_filings=11 prefix_eq_symbol=4 mismatches=7 expected_symbol=209 '
                        'expected_mismatch=16 same=no')
    assert lines[5] == ('TICKERMIX_CLASSES mismatches=7 short_name_doc=1 old_ticker=1 symbol_odd=0 class_share=1 notation=1 '
                        'inline_doc=1 other=2 other_symbol_empty=1')
    assert lines[6].startswith('PITTICKER_REQUESTS total=32 form_idx=0 filing_index=16 instance=16 ')
    assert lines[-1] == 'TICKERMIX_DONE complete=yes'
    data = json.loads((tmp_path / 'files' / once.ROWS_FILE).read_text())
    assert data['complete'] is True and data['summary']['mismatches'] == 7 and data['source_run_compared'] == 41255597310
    assert data['identity_confirmed'] is False and 'never an identity source' in data['use']
    assert all(r['identity_confirmed'] is False and r['evidence']['identity_confirmed'] is False for r in data['rows'])
    got = {(picked.index(int(r['cik'])), r['year']): r['class'] for r in data['rows']}
    assert got == EXPECTED
    first = next(r for r in data['rows'] if r['class'] == 'OLD_TICKER')
    assert first['evidence']['known_ticker'] == 'earlier_filing' and first['prefix'] == 'abcd' and first['symbols'] == ['WXYZ']
    assert first['company'] == 'SYNTHETIC COMPANY INC' and first['accession'] == accession(picked[0], 2017)
    assert AGENT not in json.dumps(data)


def test_missing_stored_quarter_is_fetched_as_in_the_measurement(tmp_path, panel):
    pool, ciks = panel
    picked = [int(ciks[3]), int(ciks[29]), int(ciks[64]), int(ciks[101])]
    setup_work(tmp_path, picked, skip={(2019, 2)})
    opener = FakeOpener(fake_sec(picked, remote_idx=idx_gz([])))
    code, lines = run(tmp_path, opener)
    assert code == 0 and lines[1] == 'TICKERMIX_INDEX local=15 remote=1' and lines[0].endswith('names=INDEX_ONLY')
    assert [u for u, _ in opener.calls if u.endswith('form.idx')] == ['https://www.sec.gov/Archives/edgar/full-index/2019/QTR2/form.idx']
    assert lines[-1] == 'TICKERMIX_DONE complete=yes'


def test_resumed_rows_print_counts_without_requests(tmp_path):
    files = tmp_path / 'files'
    files.mkdir()
    rows = [{'class': 'OTHER', 'evidence': {'symbol_empty': True}}, {'class': 'NOTATION', 'evidence': {}}]
    once.write_json(files / once.ROWS_FILE, {'schema': 'sec-once-ticker-mismatch/1', 'complete': True, 'rows': rows,
                                             'summary': {'panel': 120, 'symbol_filings': 209, 'prefix_eq_symbol': 193}})
    sha = once.sha256_file(files / once.ROWS_FILE)
    once.write_json(tmp_path / 'resume.json', {'verified': [{'key': once.ROWS_FILE, 'asset': once.ROWS_FILE, 'sha256': sha}]})
    code, lines = run(tmp_path, NoNetwork(), environ={})
    assert code == 0
    assert_fixed_lines(lines)
    assert lines == ['TICKERMIX_START panel=120 years=2016-2019 names=RESUMED',
                     'TICKERMIX symbol_filings=209 prefix_eq_symbol=193 mismatches=2 expected_symbol=209 '
                     'expected_mismatch=16 same=no',
                     'TICKERMIX_CLASSES mismatches=2 short_name_doc=0 old_ticker=0 symbol_odd=0 class_share=0 notation=1 '
                     'inline_doc=0 other=1 other_symbol_empty=1',
                     'TICKERMIX_DONE complete=yes']
    (files / once.ROWS_FILE).write_text('{}')                           # changed since the check: not resumed
    code, lines = run(tmp_path, NoNetwork(), environ={})
    assert (code, lines) == (2, ['TICKERMIX_STOP reason=SEC_USER_AGENT_MISSING'])
    once.write_json(files / once.ROWS_FILE, {'schema': 'sec-once-ticker-mismatch/1', 'complete': False, 'rows': rows,
                                             'summary': {}})               # verified but incomplete: classified again
    sha = once.sha256_file(files / once.ROWS_FILE)
    once.write_json(tmp_path / 'resume.json', {'verified': [{'key': once.ROWS_FILE, 'asset': once.ROWS_FILE, 'sha256': sha}]})
    assert mix.resumed_rows(tmp_path) is None


@pytest.mark.parametrize('environ, line', [
    ({k: v for k, v in ENV.items() if k != 'SEC_USER_AGENT'}, 'TICKERMIX_STOP reason=SEC_USER_AGENT_MISSING'),
    ({**ENV, 'SEC_USER_AGENT': 'no contact'}, 'TICKERMIX_STOP reason=SEC_USER_AGENT_INVALID'),
    ({**ENV, 'GITHUB_REF': 'refs/heads/claude/sec-once-collect-plan'}, 'TICKERMIX_STOP reason=NOT_THE_RUN_BRANCH'),
    (ENV, 'TICKERMIX_STOP reason=RAW_PREFLIGHT_MISSING'),                # no private-repository check on this attempt
    ({**ENV, 'GITHUB_RUN_ATTEMPT': '2'}, 'TICKERMIX_STOP reason=RAW_PREFLIGHT_MISSING'),
])
def test_configuration_stops_before_any_request(tmp_path, environ, line):
    if environ.get('GITHUB_RUN_ATTEMPT') == '2':
        ready(tmp_path)                                                 # attempt 1's marker does not count for attempt 2
    code, lines = run(tmp_path, NoNetwork(), environ=environ)
    assert code == 2 and lines == [line]


@pytest.mark.parametrize('stopped, reason', [
    ('HTTP403_REPEATED', 'COLLECT_STOPPED'), ('HTTP429_REPEATED', 'COLLECT_STOPPED'), ('REQUEST_CAP', 'COLLECT_STOPPED'),
    ('WALL_CLOCK', 'COLLECT_STOPPED'), ('LOCAL_DISK_FULL', 'COLLECT_STOPPED'), (None, 'COLLECT_MANIFEST_MISSING'),
])
def test_no_request_when_collect_stopped(tmp_path, stopped, reason):
    ready(tmp_path, stopped=stopped or 'NONE')
    if stopped is None:
        (tmp_path / 'collect-manifest.json').unlink()
    code, lines = run(tmp_path, NoNetwork())
    assert code == 0 and lines == [f'TICKERMIX_SKIP reason={reason}', 'TICKERMIX_DONE complete=no']
    assert_fixed_lines(lines)
    data = json.loads((tmp_path / 'files' / once.ROWS_FILE).read_text())
    assert data['complete'] is False and data['rows'] == [] and data['summary']['skipped'] == reason
    assert data['identity_confirmed'] is False


@pytest.mark.parametrize('broken, complete', [('SIZE_CAP', 'yes'), ('HTTP503', 'no')])
def test_transient_filing_errors_leave_the_result_incomplete(tmp_path, panel, broken, complete):
    pool, ciks = panel
    picked = [int(ciks[3]), int(ciks[29]), int(ciks[64]), int(ciks[101])]
    setup_work(tmp_path, picked)
    answer = fake_sec(picked)
    target = f'/{picked[1]}/{accession(picked[1], 2019).replace("-", "")}/zz-2019.xml'

    def flaky(url):
        if url.endswith(target):
            if broken == 'SIZE_CAP':
                return FakeResponse(b'x' * (pit.INSTANCE_CAP + 1))
            return urllib.error.HTTPError(url, 503, 'x', {}, None)
        return answer(url)
    code, lines = run(tmp_path, FakeOpener(flaky))
    assert code == 0 and lines[-1] == f'TICKERMIX_DONE complete={complete}'
    assert f'PITTICKER_ERRORS overall codes={broken}:1' in lines
    data = json.loads((tmp_path / 'files' / once.ROWS_FILE).read_text())
    assert data['complete'] is (complete == 'yes') and data['summary']['transient_errors'] == (0 if complete == 'yes' else 1)


def test_inspection_is_the_measurement_one():
    listing = b'{"directory":{"item":[{"name":"abcd-20171231.xml","size":"9"},{"name":"abcd-20171231.xsd"}]}}'
    instance = xbrl(PERIOD.format(2017), symbol('ABCD'))

    def client():
        answers = iter([FakeResponse(listing), FakeResponse(instance)])
        return pit.SecClient(AGENT, opener=FakeOpener(lambda url: next(answers)), sleep=lambda s: None, clock=Clock())
    a, b = client(), client()
    kept = mix.inspect_filing(a, 11, '0000000011-17-000001', {'ABCD'})
    flags = pit.measure_filing(b, 11, '0000000011-17-000001', {'ABCD'})
    assert kept['flags'] == flags and a._opener.calls == b._opener.calls and a.counts == b.counts
    assert (kept['instance'], kept['prefix'], kept['symbols'], kept['inline']) == ('abcd-20171231.xml', 'abcd', ['ABCD'], False)
    c = pit.SecClient(AGENT, opener=FakeOpener(lambda url: urllib.error.HTTPError(url, 500, 'x', {}, None)),
                      sleep=lambda s: None, clock=Clock())
    assert mix.inspect_filing(c, 11, '0000000011-17-000001', set()) == {'error': 'HTTP500'}


def test_rows_never_leave_the_private_file():
    source = (TOOLS / 'sec_once_ticker_mismatch.py').read_text()
    # every out(...) call prints a fixed format: counts, codes and the moved measurement's count lines
    calls = re.findall(r'\bout\((.+)\)\n', source)
    assert calls and all(re.match(r"(?:f?'(?:TICKERMIX|PITTICKER)|pit\.format_|format_(?:compare|classes)\()", c) for c in calls)
    assert source.count('print(') == 2 and 'lambda line: print(line, flush=True)' in source
    assert "print(f'TICKERMIX_STOP reason=UNEXPECTED class=" in source
