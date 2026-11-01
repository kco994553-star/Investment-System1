"""Offline raw response -> private candidates. Synthetic only; no HTTP or credentials."""
from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('alpaca_offline_under_test', ROOT/'tools/measure_once/alpaca_sample_once.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REQ = dict(symbol='TEST', asof='-', feed='sip', timeframe='1Day', adjustment='raw',
           start='2018-01-01', end='2018-12-31')


def page(day='2018-02-20', token=None, requested=None, **fields):
    bar = dict(t=day+'T05:00:00Z', o=10, h=12, l=9, c=11, v=123456789012345678,
               n=24, vw=10.25)
    bar.update(fields)
    body = json.dumps(dict(symbol='TEST', bars=[bar], next_page_token=token)).encode()
    return dict(body=body, sha256=hashlib.sha256(body).hexdigest(), request_page_token=requested,
                acquired_at='2026-11-01T00:00:00Z')


def test_preserves_ohlcv_and_optional_fields_with_raw_provenance_but_no_execution_claim():
    raw = page()
    out = m.normalize_pages([raw], request=REQ)
    row = out['rows'][0]
    assert (row['open'], row['close'], row['volume'], row['trade_count'], row['vwap']) == (
        '10', '11', '123456789012345678', 24, '10.25')
    assert row['date'] == '2018-02-20' and row['source_timestamp'] == '2018-02-20T05:00:00Z'
    assert row['source_sha256'] == raw['sha256'] and row['source_row'] == 0
    assert row['security_id'] is None and row['currency'] is None
    assert row['available_at'] is None and row['acquired_at'] == raw['acquired_at']
    assert out['execution_open_status'] == 'UNVERIFIED_SESSION_OPEN'
    assert out['corporate_actions_status'] == 'NOT_IN_BARS'
    assert out['status'] == 'FETCHED' and out['pages_complete'] is True


def test_missing_fields_stay_null_and_invalid_ohlc_is_not_usable():
    out = m.normalize_pages([page(v=None, n=None, vw=None, l=13)], request=REQ)
    row = out['rows'][0]
    assert row['volume'] is None and row['trade_count'] is None and row['vwap'] is None
    assert row['null_reasons']['volume'] == 'MISSING'
    assert 'OHLC_INCONSISTENT' in row['quality_reasons']
    assert out['status'] == 'QUALITY_FAILED'


def test_empty_is_not_delisting_and_incomplete_pages_are_not_complete():
    raw = page(token='next')
    out = m.normalize_pages([raw], request=REQ)
    assert out['status'] == 'INCOMPLETE' and out['pages_complete'] is False
    body = b'{"symbol":"TEST","bars":null,"next_page_token":null}'
    empty = dict(raw,body=body,sha256=hashlib.sha256(body).hexdigest())
    out = m.normalize_pages([empty], request=REQ)
    assert out['status'] == 'EMPTY_RESPONSE' and out['rows'] == []
    assert out['listing_status'] == 'UNKNOWN'


@pytest.mark.parametrize('kind,code', [('hash','RAW_HASH_MISMATCH'),('chain','PAGE_CHAIN'),
                                      ('duplicate','ORDER'),('after_end','PAGE_CHAIN')])
def test_refuses_wrong_hash_pagination_or_duplicates(kind,code):
    pages = [page(token='next'),page('2018-02-21',requested='next')]
    if kind=='hash': pages[0]['sha256']='0'*64
    if kind=='chain': pages[1]['request_page_token']='wrong'
    if kind=='duplicate': pages[1]=page(requested='next')
    if kind=='after_end': pages=[page(),page('2018-02-21',requested='next')]
    with pytest.raises(ValueError,match='^'+code+'$'):m.normalize_pages(pages,request=REQ)


def test_replay_deterministic_exact_decimal_and_dst_session_date():
    body=b'{"symbol":"TEST","bars":[{"t":"2018-07-02T04:00:00Z","o":10.1234567890123456789,"h":12,"l":9,"c":11,"v":0}],"next_page_token":null}'
    raw=dict(body=body,sha256=hashlib.sha256(body).hexdigest(),request_page_token=None,acquired_at='2026-11-01T00:00:00Z')
    first=m.normalize_pages([raw],request=REQ)
    assert first['rows'][0]['open']=='10.1234567890123456789'
    assert first['rows'][0]['date']=='2018-07-02' and first['rows'][0]['volume']=='0'
    assert json.dumps(first,sort_keys=True)==json.dumps(m.normalize_pages([raw],request=REQ),sort_keys=True)


def test_raw_request_refuses_echo_change_but_mapping_does_not_prove_identity():
    raw=page();raw['body']=raw['body'].replace(b'"TEST"',b'"OTHER"');raw['sha256']=hashlib.sha256(raw['body']).hexdigest()
    with pytest.raises(ValueError,match='SYMBOL_MISMATCH'):m.normalize_pages([raw],request=REQ)
    out=m.normalize_pages([raw],request=dict(REQ,asof='2018-02-20'))
    assert out['rows'][0]['returned_symbol']=='OTHER' and out['rows'][0]['security_id'] is None
    assert out['identity_status']=='UNVERIFIED'


@pytest.mark.parametrize('field,value', [('feed','iex'),('adjustment','split'),('timeframe','1Min')])
def test_no_silent_feed_or_adjustment_relabel(field,value):
    with pytest.raises(ValueError,match='REQUEST_BASIS'):m.normalize_pages([page()],request=dict(REQ,**{field:value}))


def test_no_pages_is_not_collected_and_unrecorded_asof_stays_unrecorded():
    out = m.normalize_pages([], request=dict(REQ, asof=None))
    assert out['status'] == 'NOT_COLLECTED' and not out['pages_complete']
    assert out['request']['asof'] is None and out['identity_status'] == 'UNVERIFIED'


@pytest.mark.parametrize('receipt', [None, '2018-02-20T00:00:00', 'not-a-time'])
def test_receipt_timestamp_requires_actual_timezone_bearing_metadata(receipt):
    raw = page(); raw['acquired_at'] = receipt
    with pytest.raises(ValueError, match='^ACQUIRED_AT$'):
        m.normalize_pages([raw], request=REQ)


def test_repeated_next_token_is_not_a_completed_page_chain():
    pages = [page(token='same'), page('2018-02-21', token='same', requested='same')]
    with pytest.raises(ValueError, match='^PAGE_CHAIN$'):
        m.normalize_pages(pages, request=REQ)


def test_invalid_numeric_values_are_null_not_zero():
    out = m.normalize_pages([page(o=True, v=-1, n=1.5)], request=REQ)
    row = out['rows'][0]
    assert all(row[k] is None for k in ('open', 'volume', 'trade_count'))
    assert all(row['null_reasons'][k] == 'INVALID_NUMBER' for k in ('open', 'volume', 'trade_count'))
    assert out['status'] == 'QUALITY_FAILED'
