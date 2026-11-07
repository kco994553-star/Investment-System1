"""Offline shared normalization -> adapter, invented responses only."""
import hashlib,json
from datetime import date
from decimal import Decimal
import pytest
from investment_system.research.exp_deciles.adapters import alpaca_bars as ab, bundle

def norm(bars):
    from investment_system.research.exp_deciles.adapters.alpaca_normalization import normalize_pages
    body=json.dumps(dict(symbol='TEST',bars=bars,next_page_token=None)).encode()
    return normalize_pages([dict(body=body,sha256=hashlib.sha256(body).hexdigest(),request_page_token=None,
        acquired_at='2026-11-01T00:00:00Z')],request=dict(symbol='TEST',asof=None,feed='sip',adjustment='raw',
        timeframe='1Day',start='2018-02-01',end='2018-03-01'))

def test_raw_reader_keeps_empty_response_separate_from_missing_directory(tmp_path):
    (tmp_path/'page-00.json').write_text('{"symbol":"TEST","bars":null,"next_page_token":null}')
    got=ab.read_series(tmp_path,expected_symbol='TEST')
    assert got['normalization_status']=='EMPTY_RESPONSE'
    assert got['identity_status']=='UNVERIFIED'
    assert got['pages'][0]['sha256']==hashlib.sha256((tmp_path/'page-00.json').read_bytes()).hexdigest()
    assert ab.price_rows(got,'UNKNOWN-ID',start='2018-02-16',end='2018-02-20')==[]
    assert ab.read_series(tmp_path/'missing')['normalization_status']=='NOT_COLLECTED'

def test_normalized_input_retains_provenance_and_identity_through_bundle():
    n=norm([dict(t='2018-02-16T05:00:00Z',o=10,h=12,l=9,c=11,v=123,n=4,vw=10.25)])
    got=ab.from_normalized(n,expected_symbol='TEST')
    assert got['bars'][date(2018,2,16)]['close']==Decimal('11')
    assert got['normalization']==n
    assert got['identity_status']=='UNVERIFIED' and n['rows'][0]['security_id'] is None
    b=bundle.build(year=2018,securities=[dict(security_id='UNVERIFIED-ID',alpaca_symbol='TEST')],
        normalized_by_security={'UNVERIFIED-ID':n},s_price_source=bundle.S_PRICE_ALPACA)
    provenance=json.loads(dict(b['files'])['adapter_provenance.json'])
    assert provenance['alpaca']['UNVERIFIED-ID']['identity_status']=='UNVERIFIED'
    assert provenance['alpaca']['UNVERIFIED-ID']['normalization_status']=='FETCHED'

def test_normalized_input_still_refuses_bad_session_and_missing_open():
    n=norm([dict(t='2018-02-20T00:00:00Z',o=10,c=11)])
    assert ab.from_normalized(n)['reason']=='BAR_TIME_NOT_NY_MIDNIGHT'
    n=norm([dict(t='2018-02-16T05:00:00Z',c=11)])
    got=ab.from_normalized(n)
    assert got['bars'][date(2018,2,16)]['open'] is None
    assert ab.coverage(got,signal_day='2018-02-16',execution_day='2018-02-20',end='2019-02-19')['t_open']=='T_OPEN_BAR_MISSING'


def test_empty_echo_mismatch_is_not_hidden_by_empty_rows(tmp_path):
    (tmp_path/'page-00.json').write_text('{"symbol":"OTHER","bars":null,"next_page_token":null}')
    assert ab.read_series(tmp_path,expected_symbol='TEST')['reason']=='SYMBOL_MISMATCH'


def test_inconsistent_ohlc_not_projected_as_valid_prices():
    n=norm([dict(t='2018-02-16T05:00:00Z',o=10,h=9,l=8,c=11,v=123)])
    got=ab.from_normalized(n)
    assert got['status']=='REFUSED' and got['normalization_status']=='QUALITY_FAILED'
    assert got['reason']=='OHLC_INCONSISTENT'
