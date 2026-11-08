"""Test helper: small INVENTED source files in the documented formats of the adapters' raw inputs (no real data).

Every CIK (9000001..), accession, ticker-like symbol (XQA, XQB1, ...), name, share count and price is invented. Nothing is
downloaded; every file is written under the caller's tmp_path. Prices are 4-decimal sentinels ending in 7.

Signal year 2018: S 2018-02-16, T 2018-02-20, filing cutoff 2018-02-08, next reselection T 2019-02-19.

Issuers (companyfacts.zip members):
  A 9000001  single class, cover count 50,000,000 as of 2018-01-20 in the 10-K filed 2018-02-01 (usable at S); an older
             10-Q count; a later 10-Q filed 2018-04-30 (after the cutoff: never used, never in the bundle)
  B 9000002  two securities in the caller's map (classes XQB1 / XQB2) -> shares UNKNOWN MULTI_CLASS_SECURITIES_AT_S
  C 9000003  only cover count filed 2018-02-09 (one day after the cutoff) -> COVER_SHARES_NOT_USABLE_AT_S
  D 9000004  two different counts in one filing -> COVER_SHARES_AMBIGUOUS_IN_FILING
  E 9000005  not in companyfacts.zip -> COMPANYFACTS_NOT_IN_ARCHIVE
  F 9000006  companyfacts without any dei cover count -> COVER_SHARES_NOT_IN_COMPANYFACTS
  G 9000007  single class in companyfacts but two tickers in today's submissions.zip -> MULTI_TICKER_IN_SUBMISSIONS
  H 9000008  carried previous U-A unit, no security at S: Form 25-NSE filed 2018-01-10 (usable), a 15-12B filed
             2018-02-14 (after the cutoff), and a 25-NSE/A amendment
FSDS sub.txt: SIC 3571 for A (filed 2018-02-01), 7372 for C (filed 2017-11-01), A's later 10-Q filed after the cutoff with
another SIC (never used), a row of E without SIC.
Alpaca SIP pages: XQA (two pages: bars on 2018-02-15, S, T, 2018-02-28 / page 2: 2019-02-19), XQG (no bar on T: a missing
T open), XQD (UTC-midnight stamps), XQC (a Saturday bar).
"""
from __future__ import annotations

import gzip
import json
import zipfile
from pathlib import Path

S, T, NEXT_T = '2018-02-16', '2018-02-20', '2019-02-19'
CIK = {k: 9000000 + i for i, k in enumerate('ABCDEFGH', 1)}


def accn(key, yy, n):
    return f'{CIK[key]:010d}-{yy}-{n}'


def cik10(key):
    return str(CIK[key]).zfill(10)


def _cover(val, end, filed, accn, form='10-K'):
    return {'end': end, 'val': val, 'accn': accn, 'fy': 2017, 'fp': 'FY', 'form': form, 'filed': filed,
            'frame': 'CY2017Q4I'}


def _revenue(filed, accn):
    return {'start': '2017-01-01', 'end': '2017-12-31', 'val': 1000.0, 'accn': accn, 'fy': 2017, 'fp': 'FY',
            'form': '10-K', 'filed': filed, 'frame': 'CY2017'}


def companyfacts(key):
    main = accn(key, '18', '000001')
    cover, revenue = [], [_revenue('2018-02-01', main)]
    if key == 'A':
        cover = [_cover(48000000, '2017-10-25', '2017-11-01', accn(key, '17', '000009'), '10-Q'),
                 _cover(50000000, '2018-01-20', '2018-02-01', main),
                 _cover(51000000, '2018-04-25', '2018-04-30', accn(key, '18', '000002'), '10-Q')]
        revenue.append(_revenue('2018-04-30', accn(key, '18', '000002')))
    elif key in ('B', 'G'):
        cover = [_cover(70000000, '2018-01-20', '2018-02-01', main)]
    elif key == 'C':
        cover = [_cover(30000000, '2018-02-05', '2018-02-09', main)]
        revenue = [_revenue('2018-02-09', main)]
    elif key == 'D':
        cover = [_cover(20000000, '2018-01-20', '2018-02-01', main), _cover(5000000, '2018-01-20', '2018-02-01', main)]
    facts = {'us-gaap': {'Revenues': {'label': 'Revenues', 'units': {'USD': revenue}}}}
    if cover:
        facts['dei'] = {'EntityCommonStockSharesOutstanding': {'label': 'cover', 'units': {'shares': cover}}}
    return {'cik': CIK[key], 'entityName': f'INVENTED ISSUER {key}', 'facts': facts}


def _zip(path, members):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in members:
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
            archive.writestr(info, data)
    return path


def write_companyfacts_zip(root, *, mismatch=False):
    members = [(f'CIK{cik10(k)}.json', json.dumps(companyfacts(k)).encode()) for k in 'ABCDFGH']
    if mismatch:
        wrong = dict(companyfacts('A'), cik=CIK['B'])
        members[0] = (f'CIK{cik10("A")}.json', json.dumps(wrong).encode())
    return _zip(Path(root) / 'companyfacts.zip', members)


def write_submissions_zip(root):
    members = []
    for k in 'ABCDFG':
        tickers = ['XQG', 'XQGW'] if k == 'G' else [f'XQ{k}']
        members.append((f'CIK{cik10(k)}.json', json.dumps({'cik': cik10(k), 'tickers': tickers}).encode()))
    return _zip(Path(root) / 'submissions.zip', members)


FORM_IDX_HEADER = (b'Description:           Master Index of EDGAR Dissemination Feed by Form Type\n'
                   b'Last Data Received:    March 31, 2018\n'
                   b'Comments:              invented header line\n'
                   b'Anonymous FTP:         ftp://ftp.sec.gov/edgar/\n \n \n \n'
                   b'Form Type   Company Name                                                  CIK         Date Filed  '
                   b'File Name\n' + b'-' * 141 + b'\n')


def _idx_row(form, name, cik, filed, accn):
    return (f'{form:<12}{name:<62}{cik:<12}{filed:<12}edgar/data/{cik}/{accn}.txt\n').encode('ascii')


def write_form_idx(root, *, gz=True):
    rows = [
        _idx_row('10-K', 'INVENTED ISSUER A', CIK['A'], '2018-02-01', accn('A', '18', '000001')),
        _idx_row('15-12B', 'INVENTED ISSUER H', CIK['H'], '2018-02-14', accn('H', '18', '000003')),
        _idx_row('25-NSE', 'INVENTED EXCHANGE FOR ISSUER H', CIK['H'], '2018-01-10', accn('H', '18', '000002')),
        _idx_row('25-NSE/A', 'INVENTED EXCHANGE FOR ISSUER H', CIK['H'], '2018-01-12', accn('H', '18', '000004')),
        _idx_row('25', 'INVENTED UNRELATED ISSUER', 9999999, '2018-01-11', '0009999999-18-000001'),
    ]
    data = FORM_IDX_HEADER + b''.join(rows)
    if gz:
        path = Path(root) / 'full-index-2018-QTR1-form.idx.gz'
        path.write_bytes(gzip.compress(data, mtime=0))
    else:
        path = Path(root) / 'form.idx'
        path.write_bytes(data)
    return path


SUB_HEADER = ['adsh', 'cik', 'name', 'sic', 'countryba', 'form', 'period', 'fy', 'fp', 'filed', 'accepted', 'prevrpt',
              'detail', 'instance', 'nciks', 'aciks']


def write_fsds(root, name='fsds-2018q1.zip'):
    def row(key, accn, sic, form, filed):
        return [accn, str(CIK[key]), f'INVENTED ISSUER {key}', sic, 'US', form, '20171231', '2017', 'FY', filed,
                f'{filed[:4]}-{filed[4:6]}-{filed[6:]} 16:01:00.0', '0', '0', 'inv-20171231.xml', '1', '']
    lines = [SUB_HEADER,
             row('A', accn('A', '18', '000001'), '3571', '10-K', '20180201'),
             row('A', accn('A', '18', '000002'), '6798', '10-Q', '20180430'),
             row('C', accn('C', '17', '000001'), '7372', '10-Q', '20171101'),
             row('E', accn('E', '18', '000001'), '', '10-K', '20180201')]
    text = '\n'.join('\t'.join(r) for r in lines) + '\n'
    return _zip(Path(root) / name, [('sub.txt', text.encode()), ('num.txt', b'adsh\ttag\n')])


def _bar(t, o, c):
    bar = {'t': t, 'h': c, 'l': o, 'v': 1000, 'n': 10, 'vw': c}
    if o is not None:
        bar['o'] = o
    if c is not None:
        bar['c'] = c
    return bar


def write_series(root, name, symbol, pages):
    """raw/<name>/page-NN.json with the given lists of bars; every page but the last carries a token."""
    folder = Path(root) / 'raw' / name
    folder.mkdir(parents=True)
    for n, bars in enumerate(pages):
        token = f'TOKEN{n}' if n < len(pages) - 1 else None
        body = {'bars': bars, 'symbol': symbol, 'next_page_token': token}
        (folder / f'page-{n:02d}.json').write_text(json.dumps(body), encoding='ascii')
    return folder


def write_alpaca(root):
    series = {}
    series['XQA'] = write_series(root, 'RAW_XQA', 'XQA', [
        [_bar('2018-02-15T05:00:00Z', 10.1007, 10.2007), _bar('2018-02-16T05:00:00Z', 10.3007, 10.4007),
         _bar('2018-02-20T05:00:00Z', 10.5007, 10.6007), _bar('2018-02-28T05:00:00Z', None, 10.8007)],
        [_bar('2019-02-19T05:00:00Z', 11.1007, 11.2007)]])
    series['XQG'] = write_series(root, 'RAW_XQG', 'XQG', [
        [_bar('2018-02-16T05:00:00Z', 20.1007, 20.2007), _bar('2018-02-21T05:00:00Z', 20.3007, 20.4007)]])
    series['XQD'] = write_series(root, 'RAW_XQD', 'XQD', [
        [_bar('2018-02-16T00:00:00Z', 5.1007, 5.2007), _bar('2018-02-20T00:00:00Z', 5.3007, 5.4007)]])
    series['XQC'] = write_series(root, 'RAW_XQC', 'XQC', [
        [_bar('2018-02-16T05:00:00Z', 7.1007, 7.2007), _bar('2018-02-17T05:00:00Z', 7.3007, 7.4007)]])
    return series


def iex_rows():
    """iex_hist.parse_rows shape: {IEX symbol: (parser status, price_e4 or None)} for S."""
    return {'XQA': ('ROUND', 104107), 'XQB1': ('ODD_ONLY', 300007), 'XQB2': ('NO_TRADE', None),
            'XQC': ('ROUND', 72007), 'XQD': ('ROUND', 52007), 'XQF': ('ROUND', 90007), 'XQG': ('ROUND', 202007)}


def security_map(series):
    return [
        {'security_id': 'SEC-A', 'cik': CIK['A'], 'iex_symbol': 'XQA', 'alpaca_series': str(series['XQA']),
         'alpaca_symbol': 'XQA'},
        {'security_id': 'SEC-B1', 'cik': CIK['B'], 'iex_symbol': 'XQB1'},
        {'security_id': 'SEC-B2', 'cik': CIK['B'], 'iex_symbol': 'XQB2'},
        {'security_id': 'SEC-C', 'cik': CIK['C'], 'iex_symbol': 'XQC', 'alpaca_series': str(series['XQC'])},
        {'security_id': 'SEC-D', 'cik': CIK['D'], 'iex_symbol': 'XQD', 'alpaca_series': str(series['XQD'])},
        {'security_id': 'SEC-E', 'cik': CIK['E'], 'iex_symbol': 'XQE'},
        {'security_id': 'SEC-F', 'cik': CIK['F'], 'iex_symbol': 'XQF'},
        {'security_id': 'SEC-G', 'cik': CIK['G'], 'iex_symbol': 'XQG', 'alpaca_series': str(series['XQG'])},
        {'security_id': 'SEC-NOCIK', 'cik': None, 'iex_symbol': None},
    ]


def write_all(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    return {'companyfacts_zip': write_companyfacts_zip(root), 'submissions_zip': write_submissions_zip(root),
            'form_idx': [write_form_idx(root)], 'fsds': [write_fsds(root)], 'series': write_alpaca(root)}


def file_bytes(files):
    return {name: data for name, data in files}


def read_json(files, name):
    return json.loads(file_bytes(files)[name])
