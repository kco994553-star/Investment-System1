"""Properties of the existing technical pipeline, using synthetic inputs only."""
from copy import deepcopy
from decimal import Decimal
import pytest
hypothesis = pytest.importorskip('hypothesis', reason='Install tests/research/dependencies/technical-properties.txt to run properties')
from hypothesis import given, settings, strategies as st
from investment_system.research.exp_deciles.technical_leaderboard import build_board, filter_board
from investment_system.research.private_technical_board import board_reader_payload
from test_private_technical_board import board_input

SET = settings(max_examples=40, deadline=None, derandomize=True, database=None)
IDS = ('momentum_3m','momentum_6m','momentum_12m','volatility_6m','dollar_volume_6m')

def inputs(values):
    rows=[dict(signal_day='2017-01-06', security_id=f'SYNTHETIC:{i:03}', series_id=f'REQUEST:{i}',
               metrics={m:dict(value=v, null_reasons=[] if v is not None else ['METRIC_NOT_AVAILABLE']) for m in IDS}) for i,v in enumerate(values)]
    group=dict(signal_day='2017-01-06',group_id='SYNTHETIC:PROPERTY',membership_status='CONFIRMED',
               membership_source='AUTHOR_CREATED',member_security_ids=[r['security_id'] for r in rows])
    return rows,group

@SET
@given(st.lists(st.one_of(st.none(),st.integers(-3,3).map(str)),min_size=0,max_size=40),st.data())
def test_permutation_nulls_ties_tails_and_filter_invariants(values,data):
    rows,group=inputs(values); a=build_board(rows,group=group)
    shuffled=list(data.draw(st.permutations(rows))); g=deepcopy(group);g['member_security_ids'].reverse()
    assert build_board(shuffled,group=g)==a
    valid=sum(v is not None for v in values);m=a['metrics']['momentum_3m']
    assert m['n_valid']==valid and m['n_members']==len(values)
    assert sorted(r['rank'] for r in m['rows'] if r['rank'] is not None)==list(range(1,valid+1))
    for left,right in zip(m['rows'],m['rows'][1:]):
        if left['value'] is not None and right['value'] is not None:
            assert Decimal(left['value'])>=Decimal(right['value'])
            if Decimal(left['value'])==Decimal(right['value']):assert left['security_id']<right['security_id']
    assert sum(r['decile']==10 for r in m['rows'])==(valid//10 if valid>=10 else 0)
    assert sum(r['decile']==1 for r in m['rows'])==(valid//10 if valid>=10 else 0)
    before=deepcopy(a);keep=filter_board(a,[dict(metric='volatility_6m',condition='exclude_D10')])
    assert a==before
    assert all(r['value'] is not None and r['decile'] in range(1,10) for r in m['rows'] if r['security_id'] in keep)

@SET
@given(st.sampled_from(['NaN','Infinity','-Infinity',None]))
def test_nonfinite_is_missing_not_zero(value):
    rows,group=inputs([value,'0']);m=build_board(rows,group=group)['metrics']['momentum_3m']
    assert m['n_valid']==1
    assert next(r for r in m['rows'] if r['series_id']=='REQUEST:0')['value'] is None

@SET
@given(st.lists(st.integers(-10,10).map(str),min_size=2,max_size=20))
def test_duplicate_security_ids_are_refused(values):
    rows,g=inputs(values);rows[-1]['security_id']=rows[0]['security_id']
    with pytest.raises(ValueError,match='DUPLICATE_SECURITY_ID'):build_board(rows,group=g)

@settings(max_examples=12, deadline=None, derandomize=True, database=None)
@given(st.sampled_from(['2017-02-30','2017-13-01','2017-1-6','not-a-date','20170106']))
def test_reader_rejects_same_invalid_date_in_outer_and_inner_result(day):
    from investment_system.research.private_technical_board import build_contract_board
    series,links,group=board_input(1);result=build_contract_board(series,group=group,security_links=links)
    result['signal_day']=result['board']['signal_day']=day
    with pytest.raises(ValueError):board_reader_payload(result)


@settings(max_examples=12, deadline=None, derandomize=True, database=None)
@given(st.integers(1,20),st.booleans())
def test_provider_normalization_price_scale_preserves_price_momentum(scale,reverse):
    import hashlib,json
    from test_private_technical_board import contract
    from investment_system.research.kis_price_bridge import normalize_page
    from investment_system.research.private_technical_board import measure_contract
    c=contract(short=True)
    rows=[dict(xymd=r['date'].replace('-',''),open=str(Decimal(r['open'])*scale),
               high=str(Decimal(r['high'])*scale),low=str(Decimal(r['low'])*scale),
               clos=str(Decimal(r['close'])*scale),tvol=str(r['volume']),tamt='999999') for r in c['raw_bars']]
    if reverse: rows.reverse()
    body=json.dumps(dict(rt_cd='0',output1={'rsym':'DNASSYN'},output2=rows)).encode()
    normalized=normalize_page(body,receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),http_status=200,fetched_at='2017-01-07T05:00:00Z'),
        request=dict(SYMB='SYN',EXCD='NAS',MODP='0',GUBN='0',BYMD='20170106'),
        evidence={**c['identity'], 'currency':'USD','currency_reference':'SYNTHETIC','confirmed_ranges':c['confirmed_ranges'],'held_ranges':[],'splits':[]})
    original=measure_contract(c,evaluation_day='2017-01-06',series_id='REQUEST:SCALE')
    measured=measure_contract(normalized,evaluation_day='2017-01-06',series_id='REQUEST:SCALE')
    assert measured['metrics']['momentum_3m']['value']==original['metrics']['momentum_3m']['value']
    assert measured['metrics']['momentum_6m']['value'] is None


