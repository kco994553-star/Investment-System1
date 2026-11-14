"""Synthetic KIS retained-close projection only; no source requests or real prices."""
from copy import deepcopy
from pathlib import Path
import json
import runpy
import pytest

from investment_system.research.kis_owner_price import prepare_kis_quotes
from investment_system.research.kis_price_bridge import _split_adjust
from investment_system.research.sector_qgv import digest

fixture=runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/owner_price_v_fixture.py'))['fixture']


def quotes(case):
    req,e,r,f,c,pins=case
    return prepare_kis_quotes(req['context'],e,r,f,c,expected_contract_hashes=pins)


def repin(case,cid):
    case[5][cid]=digest(case[4][cid])


def first(case):
    return case[1]['rows'][0]['company_id']


def test_exact_original_close_without_trade_timestamp_or_capitalization_invention():
    case=fixture();before=deepcopy(case);q=quotes(case)[0]
    assert case==before
    assert q['price']==10 and q['trade_day']=='2026-11-13'
    assert q['price_timestamp'] is None and q['time_status']=='DATE_ONLY'
    assert q['received_at']=='2026-11-14T04:00:00Z' and q['query_started_at'] is None
    assert q['provider']=='KIS' and q['price_definition']=='KIS_DAILY_CLOSE'
    assert q['adjustment_status']=='AS_TRADED' and 'qualification_reason' not in q
    metadata=q['price_source_metadata']
    assert not metadata['exchange_official_close_confirmed']
    assert 'price' not in metadata and '\"record\":' not in json.dumps(metadata) and '\"source_record\":' not in json.dumps(metadata)
    assert metadata['normalized_contract_hash']!=metadata['original_response_sha256']


def test_missing_contract_stays_outside_quotes_without_changing_evaluation_roster():
    case=fixture();cid=first(case);del case[4][cid];del case[5][cid]
    assert len(quotes(case))==22 and len(case[1]['rows'])==23


def test_missing_exact_day_never_uses_previous_close():
    case=fixture();cid=first(case);c=case[4][cid]
    for key in ('raw_bars','bars'):c[key][0]['date']='2026-11-12'
    c['price_basis_date']='2026-11-12';repin(case,cid)
    q=next(x for x in quotes(case) if x['company_id']==cid)
    assert q['status']=='MISSING' and q['price'] is None and q['trade_day'] is None
    assert q['qualification_reason']=='EXACT_TRADE_DAY_NOT_RETAINED'


@pytest.mark.parametrize('change,reason',[
    ('hash','KIS_CONTRACT_HASH_MISMATCH'),
    ('pins','KIS_CONTRACT_PIN_SET'),
    ('outside','KIS_CONTRACT_OUTSIDE_ROSTER'),
    ('modp','RAW_DAILY_SOURCE_REQUIRED'),
    ('exchange','KIS_SOURCE_IDENTITY_MISMATCH'),
])
def test_integrity_and_source_errors_are_not_empty_normal_results(change,reason):
    case=fixture();cid=first(case)
    if change=='hash':case[5][cid]='0'*64
    elif change=='pins':del case[5][cid]
    elif change=='outside':
        case[4]['SYN:OUTSIDE']=deepcopy(case[4][cid]);case[5]['SYN:OUTSIDE']=digest(case[4]['SYN:OUTSIDE'])
    elif change=='modp':case[4][cid]['source_query']['MODP']='1';repin(case,cid)
    elif change=='exchange':case[4][cid]['exchange']='NYSE';repin(case,cid)
    with pytest.raises(ValueError,match=reason):quotes(case)


@pytest.mark.parametrize('change,reason',[
    ('mapping','KIS_SECURITY_MAPPING_UNCONFIRMED'),
    ('identity','KIS_IDENTITY_PERIOD_UNCONFIRMED'),
    ('issuer','KIS_ISSUER_ID_CONFLICT'),
    ('security','KIS_SECURITY_ID_CONFLICT'),
    ('mapping_period','KIS_MAPPING_PERIOD_UNCONFIRMED'),
    ('action_range','KIS_ACTION_INTERVAL_UNCONFIRMED'),
    ('held','HELD_RANGE_IN_FINANCIAL_BASIS'),
])
def test_numeric_price_does_not_prove_nonprice_basis(change,reason):
    case=fixture();cid=first(case);c=case[4][cid];b=case[3][cid]['basis_evidence']
    if change=='mapping':b['mapping']['provider']='GOOGLEFINANCE'
    elif change=='identity':c['identity']['identity_status']='UNKNOWN'
    elif change=='issuer':c['issuer_id']='SYN:OTHER_ISSUER'
    elif change=='security':c['security_id']='SYN:OTHER_SECURITY'
    elif change=='mapping_period':b['mapping']['valid_to']='2026-11-13'
    elif change=='action_range':c['confirmed_ranges']=[]
    elif change=='held':c['held_ranges']=[dict(**{'from':'2026-10-15','to':'2026-10-16'},reason='SYNTHETIC_HOLD')]
    repin(case,cid);q=next(x for x in quotes(case) if x['company_id']==cid)
    assert q['status']=='AVAILABLE' and q['price']==10
    assert q['qualification_reason']==reason and q['nonprice_reason']==reason


def with_split(case):
    cid=first(case);c=case[4][cid]
    c['splits']=[dict(date='2026-10-15',ratio='2',status='CONFIRMED',evidence='SYNTHETIC_SPLIT')]
    case[3][cid]['basis_evidence']['corporate_actions']['basis']='ALREADY_NORMALIZED'
    repin(case,cid)
    return cid


def test_split_outside_price_window_still_requires_record_bound_share_unit_proof():
    case=fixture();cid=with_split(case)
    q=next(x for x in quotes(case) if x['company_id']==cid)
    assert q['qualification_reason']=='SHARE_NORMALIZATION_UNCONFIRMED'
    assert q['price']==10
    metadata=q['price_source_metadata']['split_evidence']
    assert metadata['events'][0]['state']=='OUTSIDE_RETAINED_PRICE_WINDOW'
    assert not metadata['independently_verified']


def test_already_normalized_record_is_not_adjusted_a_second_time():
    case=fixture();cid=with_split(case);wrapped=case[3][cid];before=deepcopy(wrapped['record'])
    wrapped['basis_evidence']['share_normalization']=dict(status='VERIFIED',mode='SOURCE_ALREADY_NORMALIZED',
        record_hash=digest(wrapped['record']),target_day='2026-11-13',share_unit_basis_day='2026-10-15',
        share_class_id='SYN_COMMON',available_at='2026-11-13T12:00:00Z',
        source_refs=['SYNTHETIC_NORMALIZATION_NOTE'],split_event_hashes=[digest(case[4][cid]['splits'][0])])
    q=next(x for x in quotes(case) if x['company_id']==cid)
    assert 'qualification_reason' not in q and q['price']==10
    assert wrapped['record']==before
    wrapped['basis_evidence']['share_normalization']['record_hash']='0'*64
    assert next(x for x in quotes(case) if x['company_id']==cid)['qualification_reason']=='SHARE_NORMALIZATION_UNCONFIRMED'


def test_source_record_conflict_outside_price_window_is_not_hidden_by_helper_window():
    case=fixture();cid=with_split(case)
    case[4][cid]['splits'][0]['source_record']=dict(ratio='3',effective_date='2026-10-15')
    repin(case,cid)
    assert next(x for x in quotes(case) if x['company_id']==cid)['qualification_reason']=='SPLIT_RATIO_CONFLICT'


def test_later_archive_split_does_not_change_earlier_original_close_or_receipt():
    case=fixture();cid=first(case);c=case[4][cid]
    later=deepcopy(c['raw_bars'][0]);later.update(date='2026-11-16',collected_at='2026-11-17T04:00:00Z')
    c['raw_bars'].append(later);c['collected_at']='2026-11-17T04:00:00Z';c['price_basis_date']='2026-11-16'
    c['splits']=[dict(date='2026-11-16',ratio='2',status='CONFIRMED',evidence='SYNTHETIC_FUTURE_SPLIT')]
    c['basis']='SPLIT_ADJUSTED';c['bars']=_split_adjust(c['raw_bars'],c['splits'])
    c['source_query']['BYMD']='20261116';repin(case,cid)
    case[0]['context'].update(input_cutoff='2026-11-17T04:02:00Z',evaluated_at='2026-11-17T04:02:00Z')
    q=next(x for x in quotes(case) if x['company_id']==cid)
    assert c['bars'][0]['close']=='5'
    assert q['price']==10 and q['received_at']=='2026-11-14T04:00:00Z'
    assert q['price_source_metadata']['split_evidence']['future_events_excluded']==1
    assert 'qualification_reason' not in q


def test_failed_update_preserves_old_row_capture_and_failure_metadata():
    case=fixture();cid=first(case);c=case[4][cid]
    c.update(update_state='FAILED',last_success_at=c['collected_at'],collected_at='2026-11-14T04:01:00Z')
    repin(case,cid);q=next(x for x in quotes(case) if x['company_id']==cid)
    assert q['received_at']=='2026-11-14T04:00:00Z'
    assert q['price_source_metadata']['update_state']=='FAILED'
    assert q['price_source_metadata']['last_success_at']=='2026-11-14T04:00:00Z'
