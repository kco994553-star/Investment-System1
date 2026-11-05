"""Author-created display fixtures; no provider, prices or production collection."""
import json
from pathlib import Path
from .exp_deciles.technical_leaderboard import build_board, filter_board
from .private_technical_board import board_reader_payload

METRICS=('momentum_3m','momentum_6m','momentum_12m','volatility_6m','dollar_volume_6m')

def fixtures():
    cases={};expectations={}
    for name in ('normal','empty','partial_missing','stale','unknown_group'):
        values=[] if name=='empty' else ['-5','-5','0','0','1','1','2','2','3','3']
        rows=[]
        for i,v in enumerate(values,1):
            metrics={m:dict(value=str(int(v)+5) if m=='volatility_6m' else str((int(v)+5)*100) if m=='dollar_volume_6m' else v,raw_value=v,unit='USD_PER_TRADING_DAY' if m=='dollar_volume_6m' else 'PERCENT_PER_DAY' if m=='volatility_6m' else 'PERCENT',null_reasons=[]) for m in METRICS}
            for metric in metrics.values(): metric['raw_value']=metric['value']
            if name=='partial_missing' and i==1:
                metrics['volatility_6m'].update(value=None,raw_value='999',null_reasons=['METRIC_NOT_AVAILABLE'])
            rows.append(dict(signal_day='2017-01-06',security_id=f'SYNTHETIC:{i:03}',series_id=f'REQUEST:{i}',metrics=metrics))
        unknown=name=='unknown_group'
        group=dict(signal_day='2017-01-06',group_id='SYNTHETIC:SCREEN',membership_status='UNKNOWN' if unknown else 'CONFIRMED',
                   membership_source=None if unknown else 'AUTHOR_CREATED',member_security_ids=None if unknown else [r['security_id'] for r in rows])
        board=build_board(rows,group=group)
        result=dict(schema='kis-technical-board/1',publication_scope='OWNER_PRIVATE_ONLY',evidence_kind='SYNTHETIC',signal_day=group['signal_day'],board=board)
        cases[name]=board_reader_payload(result)
        conditions=[dict(metric='volatility_6m',condition='exclude_D10')]
        expected=[] if name in ('empty','partial_missing','unknown_group') else [f'SYNTHETIC:{i:03}' for i in range(1,11) if i!=9]
        assert filter_board(board,conditions)==expected
        expectations[name]=dict(file=name+'.json',transport_state='OK',freshness='STALE' if name=='stale' else 'NORMAL',
            evaluation_day='2017-01-06',query_day='2017-01-09' if name=='stale' else '2017-01-06',
            company_display_name='합성기업_아주긴한글기업명_화면줄바꿈과접근성검사용_가나다라마바사아자차카타파하',
            expected_order=[] if name=='empty' else ['SYNTHETIC:'+f'{i:03}' for i in (range(1,11) if unknown else (9,10,7,8,5,6,3,4,1,2))],
            filter=conditions,expected_selected_ids=expected,filter_semantics='UNDECIDABLE' if name in ('unknown_group','partial_missing') else 'CONFIRMED_EMPTY' if name=='empty' else 'CALCULATED',expected_filter_counts={'PASS':0,'FAIL':0,'UNKNOWN':10} if name in ('unknown_group','partial_missing') else {'PASS':0,'FAIL':0,'UNKNOWN':0} if name=='empty' else {'PASS':9,'FAIL':1,'UNKNOWN':0},valid_volatility_n=None if unknown else 0 if name=='empty' else 9 if name=='partial_missing' else 10,
            null_meaning='UNKNOWN_GROUP_NOT_ZERO' if unknown else 'MISSING_VALUE_NOT_ZERO' if name=='partial_missing' else 'EMPTY_CONFIRMED_GROUP' if name=='empty' else None)
    cases['failed']=None
    expectations['failed']=dict(file='failed.json',transport_state='ERROR',error='SYNTHETIC_UPSTREAM_FAILURE',expected_selected_ids=None,null_meaning='NO_PAYLOAD_NOT_EMPTY_POPULATION')
    return cases,dict(schema='technical-screen-fixture-expectations/1',data_kind='SYNTHETIC',cases=expectations,
        units=dict(momentum='PERCENT',volatility='PERCENT_PER_DAY_NON_ANNUALISED',dollar_volume='USD_PER_TRADING_DAY'),
        invariants='Filters retain original metric N/ranks/percentiles; no post-filter reranking. Transport/name/freshness metadata is harness-only, outside the strict board contract.')

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    cases,expectations=fixtures()
    for name,data in {**cases,'expectations':expectations}.items():
        (a.output_dir/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
