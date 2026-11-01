"""adapters/alpaca_bars.py: Alpaca SIP raw daily-bar pages -> ledger price rows. Invented pages in tmp_path only."""
from datetime import date
from decimal import Decimal

import pytest

import exp_deciles_adapter_fixtures as fx
from investment_system.research.exp_deciles import ledger
from investment_system.research.exp_deciles.adapters import alpaca_bars as ab
from investment_system.research.exp_deciles.adapters.common import AdapterError


@pytest.fixture()
def series(tmp_path):
    return fx.write_alpaca(tmp_path)


def test_session_date_is_the_new_york_date_of_new_york_midnight():
    assert ab.session_date('2018-02-20T05:00:00Z') == (date(2018, 2, 20), None)          # EST
    assert ab.session_date('2018-07-02T04:00:00Z') == (date(2018, 7, 2), None)           # EDT
    assert ab.session_date('2018-02-20T00:00:00-05:00') == (date(2018, 2, 20), None)
    # UTC midnight is 19:00 New York of the day before: refused, never shifted onto a session
    assert ab.session_date('2018-02-21T00:00:00Z') == (None, 'BAR_TIME_NOT_NY_MIDNIGHT')
    assert ab.session_date('2018-02-19T05:00:00Z') == (None, 'NON_SESSION_DATE')         # Presidents' Day
    assert ab.session_date('2018-02-17T05:00:00Z') == (None, 'NON_SESSION_DATE')         # Saturday
    assert ab.session_date('2018-02-20T05:00:00') == (None, 'BAR_TIME_INVALID')           # no zone
    assert ab.session_date('2030-01-02T05:00:00Z') == (None, 'OUTSIDE_RULE_CALENDAR')


def test_read_series_pages_open_close_separate(series):
    out = ab.read_series(series['XQA'], expected_symbol='XQA')
    assert out['status'] == 'OK' and out['symbol'] == 'XQA' and [p['file'] for p in out['pages']] == [
        'page-00.json', 'page-01.json']
    assert out['bars'][date(2018, 2, 20)] == {'open': Decimal('10.5007'), 'close': Decimal('10.6007')}
    assert out['bars'][date(2018, 2, 28)] == {'open': None, 'close': Decimal('10.8007')}   # no 'o': never the close
    assert out['counts'] == {'bars': 5, 'close_invalid': 0, 'open_invalid': 1}


def test_refused_series(series, tmp_path):
    assert ab.read_series(series['XQD'])['reason'] == 'BAR_TIME_NOT_NY_MIDNIGHT'
    assert ab.read_series(series['XQC'])['reason'] == 'NON_SESSION_DATE'
    assert ab.read_series(series['XQA'], expected_symbol='XQZ')['reason'] == 'SYMBOL_MISMATCH'
    assert ab.read_series(tmp_path / 'nothing')['reason'] == 'PAGES_MISSING'
    bar = {'t': '2018-02-16T05:00:00Z', 'o': 1, 'c': 1}
    cut = fx.write_series(tmp_path, 'CUT', 'XQX', [[bar], [dict(bar, t='2018-02-20T05:00:00Z')]])
    (cut / 'page-01.json').unlink()
    assert ab.read_series(cut)['reason'] == 'PAGINATION_INCOMPLETE'          # page 00 promises another page
    early = fx.write_series(tmp_path, 'EARLY', 'XQX', [[bar], [dict(bar, t='2018-02-20T05:00:00Z')]])
    (early / 'page-00.json').write_text('{"bars": [], "symbol": "XQX", "next_page_token": null}')
    assert ab.read_series(early)['reason'] == 'PAGINATION_INCONSISTENT'      # a page after the last one
    gap = fx.write_series(tmp_path, 'GAP', 'XQX', [[bar], [dict(bar, t='2018-02-20T05:00:00Z')]])
    (gap / 'page-01.json').rename(gap / 'page-02.json')
    assert ab.read_series(gap)['reason'] == 'PAGE_SEQUENCE_GAP'
    dup = fx.write_series(tmp_path, 'DUP', 'XQX', [[bar, bar]])
    assert ab.read_series(dup)['reason'] == 'BAR_ORDER_INVALID'
    nan = fx.write_series(tmp_path, 'NAN', 'XQX', [[bar]])
    (nan / 'page-00.json').write_text('{"bars": [{"t": "2018-02-16T05:00:00Z", "o": NaN}], "symbol": "XQX"}')
    assert ab.read_series(nan)['reason'] == 'PAGE_NOT_JSON'
    empty = fx.write_series(tmp_path, 'EMPTY', 'XQX', [None])
    assert ab.read_series(empty)['status'] == 'OK' and ab.read_series(empty)['bars'] == {}


def test_price_rows_are_engine_rows_with_source_and_no_fill(series):
    xqa = ab.read_series(series['XQA'])
    rows = ab.price_rows(xqa, 'SEC-A', start=fx.S, end=fx.NEXT_T)
    assert [r['date'] for r in rows] == ['2018-02-16', '2018-02-20', '2018-02-28', '2019-02-19']   # 02-15 is before S
    assert rows[2]['open'] is None and rows[2]['close'] == Decimal('10.8007')
    assert all(r['source'] == 'ALPACA_SIP_DAILY_BAR_RAW' and r['price_basis'] == 'RAW' and r['currency'] == 'USD'
               for r in rows)
    index = ledger.index_price_rows([dict(r, date=date.fromisoformat(r['date'])) for r in rows])
    assert index[date(2018, 2, 20)]['SEC-A'].open == Decimal('10.5007')
    # a missing T bar gives no row at all: no open is taken from the S close or the next day
    xqg = ab.read_series(series['XQG'])
    rows = ab.price_rows(xqg, 'SEC-G', start=fx.S, end=fx.NEXT_T)
    assert [r['date'] for r in rows] == ['2018-02-16', '2018-02-21']
    assert ab.price_rows(ab.read_series(series['XQD']), 'SEC-D', start=fx.S, end=fx.NEXT_T) == []
    with pytest.raises(AdapterError, match='SECURITY_ID_INVALID'):
        ab.price_rows(xqa, '', start=fx.S, end=fx.NEXT_T)


def test_coverage_codes(series):
    cov = ab.coverage(ab.read_series(series['XQG']), signal_day=fx.S, execution_day=fx.T, end=fx.NEXT_T)
    assert (cov['s_close'], cov['t_open'], cov['next_t_open']) == ('SUPPLIED', 'T_OPEN_BAR_MISSING',
                                                                  'NEXT_T_OPEN_BAR_MISSING')
    assert cov['holding_sessions'] == 251 and cov['holding_bars'] == 1
    assert set(cov['month_ends']) == {f'{y}-{m:02d}' for y, m in [(2018, m) for m in range(2, 13)] + [(2019, 1)]}
    cov = ab.coverage(ab.read_series(series['XQA']), signal_day=fx.S, execution_day=fx.T, end=fx.NEXT_T)
    assert (cov['s_close'], cov['t_open'], cov['next_t_open'], cov['month_ends']['2018-02']) == (
        'SUPPLIED', 'SUPPLIED', 'SUPPLIED', 'SUPPLIED')
    assert cov['month_ends']['2018-03'] == 'MONTH_END_BAR_MISSING'
    refused = ab.coverage(ab.read_series(series['XQD']), signal_day=fx.S, execution_day=fx.T, end=fx.NEXT_T)
    assert refused['t_open'] == 'SERIES_REFUSED'
    assert ab.coverage(None, signal_day=fx.S, execution_day=fx.T, end=fx.NEXT_T)['t_open'] == 'SERIES_NOT_SUPPLIED'


def test_span_clips_a_reused_symbol(series):
    xqa = ab.read_series(series['XQA'])
    rows = ab.price_rows(xqa, 'SEC-A', start=fx.S, end=fx.NEXT_T, span=(None, '2018-03-01'))
    assert [r['date'] for r in rows] == ['2018-02-16', '2018-02-20', '2018-02-28']
    cov = ab.coverage(xqa, signal_day=fx.S, execution_day=fx.T, end=fx.NEXT_T, span=(None, '2018-03-01'))
    assert cov['next_t_open'] == 'NEXT_T_OPEN_BAR_MISSING' and cov['bars_outside_span'] == 1
