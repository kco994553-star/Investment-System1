"""Build tests/fixtures/price_store_v1.json: SYNTHETIC vectors for the price store (Prices_D / Prices_M tabs).

Every close below is an invented round number; no market data, no holdings. Each vector holds the expected output of the
Python reference (qgv/price_store.py); the device JS (web_assets/price-store.js) must reproduce it exactly.
Usage: python tools/price_store_reference.py [--check]
"""
from __future__ import annotations

import calendar
from datetime import date
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.qgv import price_store as ps  # noqa: E402

OUT = ROOT / 'tests/fixtures/price_store_v1.json'
NOTE = 'SYNTHETIC test vectors: invented round closes for the price store logic; no market data, no holdings.'
HEAD = list(ps.HEAD)
AT = '2026-10-13T00:00:00Z'


def err(fn):
    try:
        return fn()
    except ps.StoreError as e:
        return {'error': str(e)}


def bars(rows):
    """[(session_date, status, close)] → synthetic Worker bars (timestamps 13:30 UTC of each date)."""
    out = []
    for d, status, close in rows:
        y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:])
        out.append({'timestamp': calendar.timegm((y, m, dd, 13, 30, 0)), 'open': None, 'high': None, 'low': None, 'close': close,
                    'adjusted_close': None, 'volume': None, 'session_status': status})
    return out


def payload(symbol, rows, read_at='2026-10-09T21:00:00Z', provider='Yahoo Finance(비공식)', currency=None, tz=None):
    return {'schema': 'private-history/1', 'provider': provider, 'symbol': symbol, 'range': '1mo', 'currency': currency or ps.currency_for(symbol),
            'exchange': 'SYNTHETIC', 'timezone': tz or ps.timezone_for(symbol), 'interval': '1d', 'basis': 'RAW_CLOSE',
            'delay_status': 'UNKNOWN', 'read_at': read_at, 'bars': bars(rows)}


def tabs():
    good = [HEAD,
            ['SPY', '2026-10-01', '100.5', 'YAHOO', AT],
            ['SPY', '2026-10-02', '101.25'],
            ['', '', ''],
            [],
            ['SPY', '2026-02-30', '99'],
            ['spy', '2026-10-03', '99'],
            ['SPY', '2026-10-05', 101.75],
            ['SPY', '2026-10-06', '-3'],
            ['SPY', '2026-10-07', '0'],
            ['SPY', '2026-10-08', '1e+400'],
            ['SPY', '2026-10-08', '1.5e2'],
            ['XLK', '2026-10-08', '1.5e+2'],
            ['KRW=X', '2026-10-08', '1400.125'],
            ['042700.KS', '2026-10-08', '98000'],
            ['BRK-B', '2026-10-08'],
            ['SPY', '1899-12-29', '5'],
            ['SPY', '2026-10-09', '102', 'TIINGO', AT, 'extra']]
    cases = [('valid_mixed_daily', good, '1d'), ('valid_mixed_monthly', good, '1mo'), ('empty_tab', [], '1d'),
             ('header_only', [HEAD], '1mo'), ('header_mismatch', [['symbol', 'date', 'interval', 'close', 'source', 'fetched_at']], '1d'),
             ('header_renamed', [['symbol', 'date', 'Close', 'source', 'fetched_at'], ['SPY', '2026-10-01', '1']], '1d'),
             ('empty_header_with_rows', [[], ['SPY', '2026-10-01', '1']], '1d')]
    return [{'name': n, 'values': v, 'interval': i, 'expected': err(lambda v=v, i=i: ps.parse_tab(v, i))} for n, v, i in cases]


def indexes():
    rows = [['SPY', '2026-09-30', 100.0], ['SPY', '2026-09-29', 99.5], ['SPY', '2026-09-30', 100.25], ['XLK', '2026-08-31', 50.0],
            ['SPY', '2026-08-31', 98.0], ['XLK', '2026-08-28', 49.5]]
    return [{'name': i, 'rows': rows, 'interval': i, 'expected': ps.index_rows(rows, i)} for i in ('1d', '1mo')]


def histories():
    cases = [
        ('yahoo_complete_in_progress', 'SPY', payload('SPY', [('2026-10-07', 'COMPLETE', 100.5), ('2026-10-08', 'COMPLETE', None),
                                                               ('2026-10-09', 'IN_PROGRESS', 101.5)])),
        ('unknown_before_read_day', 'NVDA', payload('NVDA', [('2026-10-07', 'UNKNOWN', 120.0), ('2026-10-09', 'UNKNOWN', 121.0)],
                                                      read_at='2026-10-09T21:00:00Z')),
        ('tiingo_session_labels', 'XLK', {**payload('XLK', [('2026-10-07', 'COMPLETE', 50.25)], provider='Tiingo EOD'),
                                          'timestamp_kind': 'PROVIDER_SESSION_LABEL',
                                          'bars': [{'timestamp': 1791331200, 'session_date': '2026-10-07', 'close': 50.25, 'session_status': 'COMPLETE'},
                                                   {'timestamp': 1791417600, 'session_date': '2026-10-08', 'close': 50.5, 'session_status': 'UNKNOWN'}]}),
        ('fx_krw', 'KRW=X', payload('KRW=X', [('2026-10-07', 'COMPLETE', 1400.5), ('2026-10-08', 'COMPLETE', 1401.0)])),
        ('currency_mismatch', 'SPY', payload('SPY', [('2026-10-07', 'COMPLETE', 100.5)], currency='KRW')),
        ('worker_error', 'SPY', {'error': 'RATE_LIMITED'}),
        ('not_requested', 'SPY', None),
        ('format_invalid', 'SPY', {**payload('SPY', []), 'bars': [{'timestamp': 'x'}]}),
        ('no_final_close', 'SPY', payload('SPY', [('2026-10-09', 'IN_PROGRESS', 101.5)])),
    ]
    out = []
    for name, symbol, p in cases:
        closes, code = ps.closes_from_history(p, symbol)
        out.append({'name': name, 'symbol': symbol, 'payload': p, 'expected': [closes, code], 'source': ps.source_of(p)})
    return out


def month_end_vectors():
    daily = {'2026-07-30': 90.0, '2026-07-31': 91.0, '2026-08-28': 95.5, '2026-09-29': 99.0, '2026-09-30': 100.0, '2026-10-01': 100.5,
             '2026-10-02': 101.0}
    return [{'name': 'mid_month', 'closes': daily, 'as_of': '2026-10-13', 'expected': ps.month_ends(daily, '2026-10-13')},
            {'name': 'first_of_month', 'closes': daily, 'as_of': '2026-10-01', 'expected': ps.month_ends(daily, '2026-10-01')},
            {'name': 'month_not_complete', 'closes': daily, 'as_of': '2026-09-30', 'expected': ps.month_ends(daily, '2026-09-30')},
            {'name': 'empty', 'closes': {}, 'as_of': '2026-10-13', 'expected': {}}]


def due_vectors():
    cases = [('SPY', '2026-10-13', '09:30'), ('SPY', '2026-10-13', '16:00'), ('SPY', '2026-10-13', '15:59'), ('SPY', '2026-10-12', '08:00'),
             ('SPY', '2026-10-11', '18:00'), ('SPY', '2026-10-10', '18:00'), ('042700.KS', '2026-10-13', '15:30'),
             ('042700.KS', '2026-10-13', '15:29'), ('8035.T', '2026-10-13', '16:00'), ('KRW=X', '2026-10-13', '23:59'),
             ('JPYKRW=X', '2026-10-12', '12:00'), ('BRK-B', '2026-10-16', '16:05'), ('SPY', '2026-13-01', '10:00'), ('SPY', '2026-10-13', '9:30')]
    return [{'symbol': s, 'day': d, 'time': t, 'expected': err(lambda s=s, d=d, t=t: ps.due_date(s, d, t))} for s, d, t in cases]


def range_vectors():
    today = '2026-10-13'
    cases = [(None, '2026-10-12'), ('2026-10-12', '2026-10-12'), ('2026-10-13', '2026-10-12'), ('2026-10-09', '2026-10-12'),
             ('2026-09-13', '2026-10-12'), ('2026-09-12', '2026-10-12'), ('2026-07-14', '2026-10-12'), ('2026-04-13', '2026-10-12'),
             ('2025-10-13', '2026-10-12'), ('2025-10-12', '2026-10-12'), ('2024-10-13', '2026-10-12'), ('2021-10-13', '2026-10-12'),
             ('2019-01-02', '2026-10-12')]
    daily = [{'last': last, 'due': due, 'today': today, 'expected': ps.next_range(last, due, today)} for last, due in cases]
    daily.append({'last': '2026-02-27', 'due': '2026-03-30', 'today': '2026-03-31', 'expected': ps.next_range('2026-02-27', '2026-03-30', '2026-03-31')})
    daily.append({'last': '2024-02-29', 'due': '2026-02-27', 'today': '2026-02-28', 'expected': ps.next_range('2024-02-29', '2026-02-27', '2026-02-28')})
    months = [(None, '2026-10-13'), ('2026-09', '2026-10-13'), ('2026-10', '2026-10-13'), ('2026-08', '2026-10-13'), ('2026-08', '2026-10-01'),
              ('2026-06', '2026-10-13'), ('2025-12', '2026-10-13'), ('2024-01', '2026-10-13'), ('2021-01', '2026-10-13'), ('2025-11', '2026-01-05')]
    monthly = [{'last_month': m, 'today': t, 'due': ps.month_due(t), 'expected': ps.next_month_range(m, t)} for m, t in months]
    backs = [{'today': t, 'months': n, 'expected': ps._months_back(date.fromisoformat(t), n).isoformat()}
             for t, n in [('2026-03-31', 1), ('2026-05-31', 3), ('2024-02-29', 12), ('2026-10-13', 60), ('2026-01-15', 1), ('2026-12-31', 24)]]
    return {'daily': daily, 'monthly': monthly, 'months_back': backs}


def plan_vectors():
    stored = {'2026-10-01': 100.5, '2026-10-02': 101.0, '2026-10-06': 102.0}
    fetched = {'2026-10-01': 100.5, '2026-10-02': 101.125, '2026-10-05': 101.5, '2026-10-06': 102.0, '2026-10-07': 102.5, '2026-10-08': 103.0}
    m_stored = {'2026-07': 91.0, '2026-08': 95.5}
    m_fetched = {'2026-07': ['2026-07-31', 91.25], '2026-08': ['2026-08-28', 95.5], '2026-09': ['2026-09-30', 100.0]}
    return [{'name': 'daily_tail_gap_revised', 'stored': stored, 'fetched': fetched, 'interval': '1d', 'expected': ps.append_plan(stored, fetched, '1d')},
            {'name': 'daily_first', 'stored': {}, 'fetched': fetched, 'interval': '1d', 'expected': ps.append_plan({}, fetched, '1d')},
            {'name': 'daily_nothing_new', 'stored': fetched, 'fetched': fetched, 'interval': '1d', 'expected': ps.append_plan(fetched, fetched, '1d')},
            {'name': 'monthly_new_month_revised', 'stored': m_stored, 'fetched': m_fetched, 'interval': '1mo', 'expected': ps.append_plan(m_stored, m_fetched, '1mo')}]


def row_vectors():
    rows = [['2026-10-07', 102.5], ['2026-10-08', 0.1 + 0.2], ['2026-10-09', 1e21], ['2026-10-12', 1234.5678e10], ['2026-10-13', 98000.0]]
    return [{'symbol': 'SPY', 'rows': rows, 'source': 'YAHOO', 'fetched_at': AT, 'expected': ps.sheet_rows('SPY', rows, 'YAHOO', AT)}]


def merged_vectors():
    daily = {'2026-07-31': 91.0, '2026-08-28': 95.5, '2026-09-30': 100.0, '2026-10-02': 101.0}
    monthly = {'2021-10': 40.0, '2026-08': 95.75}
    return [{'name': 'monthly_first_then_daily', 'daily': daily, 'monthly': monthly, 'as_of': '2026-10-13', 'expected': ps.month_end_closes(daily, monthly, '2026-10-13')},
            {'name': 'daily_only', 'daily': daily, 'monthly': None, 'as_of': '2026-10-13', 'expected': ps.month_end_closes(daily, None, '2026-10-13')},
            {'name': 'nothing', 'daily': None, 'monthly': None, 'as_of': '2026-10-13', 'expected': {}}], [
            {'daily': daily, 'from': '2026-08-28', 'expected': ps.daily_closes(daily, '2026-08-28')},
            {'daily': daily, 'from': None, 'expected': ps.daily_closes(daily, None)},
            {'daily': None, 'from': '2026-01-01', 'expected': {}}]


def runner_vectors():
    closes = {'2024-10-11': 80.0, '2024-10-14': 80.5, '2025-06-02': 90.0, '2026-10-09': 100.0, '2026-10-12': 100.5}
    out = []
    for symbol, today in [('SPY', '2026-10-13'), ('KRW=X', '2026-10-13'), ('042700.KS', '2026-10-14')]:
        p = ps.runner_payload(closes, symbol, today, '2026-10-13T12:00:00Z')
        out.append({'symbol': symbol, 'today': today, 'closes': closes, 'read_at': '2026-10-13T12:00:00Z', 'expected': p,
                    'runner_closes': list(ps.closes_from_history(p, symbol))})
    return out


def chunk_vectors():
    rows = [['SPY', '2026-10-%02d' % d, str(100 + d), 'YAHOO', AT] for d in range(1, 10)]
    return [{'rows': rows, 'max_bytes': n, 'expected': ps.chunk_rows(rows, n)} for n in (1, 120, 200, 100000)]


def build():
    merged, daily = merged_vectors()
    return {
        'schema': 'price-store-vectors/1', 'synthetic': True, 'note': NOTE, 'head': HEAD, 'tabs_by_interval': ps.TABS,
        'tabs': tabs(), 'indexes': indexes(), 'histories': histories(), 'month_ends': month_end_vectors(), 'due': due_vectors(),
        'ranges': range_vectors(), 'plans': plan_vectors(), 'rows': row_vectors(), 'merged': merged, 'daily': daily,
        'runner': runner_vectors(), 'chunks': chunk_vectors(),
        'universe': [{'code': c, 'expected': ps.universe_symbol(c)} for c in
                     ['NYSE:BRK.B', 'NASDAQ:NVDA', 'BATS:CBOE', 'NYSE:BF.B', 'KRX:042700', 'TYO:8035', 'nyse:mmm', 'NYSE:', 42]],
    }


def text():
    return json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def main(argv):
    if '--check' in argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text():
            print('PRICE_STORE_REFERENCE_STALE')
            return 1
        print('PRICE_STORE_REFERENCE_OK')
        return 0
    OUT.write_text(text(), encoding='utf-8')
    print('PRICE_STORE_REFERENCE_WRITTEN')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
