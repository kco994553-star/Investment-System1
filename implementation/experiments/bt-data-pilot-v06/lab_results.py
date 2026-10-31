"""Private candidate for user-specified lab-backtest-v1; never a public exporter.

The shared product validator and publication policy remain Main-owned. This
module checks structure, arithmetic and unit conventions, not factual PIT or
review evidence. A valid document is not permission to publish it.
"""
from datetime import date, datetime
import json
import math
import re

METRICS = {'cagr','total_return','max_drawdown','volatility','sharpe',
           'benchmark_cagr','excess_cagr'}
RUN_KEYS = {'id','name','description','run_type','data_status','validation_status',
            'qgv_version','universe','period','rebalance','benchmark','costs',
            'metrics','null_reasons','equity_curve','limitations'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected):
    require(isinstance(value,dict) and set(value)==set(expected), 'contract keys mismatch')


def number(value):
    return type(value) in (int,float) and math.isfinite(value)


def text(value):
    return isinstance(value,str) and bool(value.strip())


def loads(body):
    def pairs(items):
        result={}
        for k,v in items:
            require(k not in result,'duplicate JSON key');result[k]=v
        return result
    return json.loads(body,object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def validate(doc):
    keys(doc,{'schema_version','generated_at','source_commit','runs'})
    require(doc['schema_version']=='lab-backtest-v1','unsupported schema')
    require(isinstance(doc['generated_at'],str),'timestamp must be string')
    require(datetime.fromisoformat(doc['generated_at'].replace('Z','+00:00')).tzinfo is not None,
            'timezone required')
    require(isinstance(doc['source_commit'],str) and
            re.fullmatch('[0-9a-f]{40}',doc['source_commit']), 'full source commit required')
    require(isinstance(doc['runs'],list),'runs must be list')
    ids=set()
    for run in doc['runs']:
        keys(run,RUN_KEYS)
        for key in ('id','name','description','rebalance'):require(text(run[key]),'empty text')
        require(run['id'] not in ids,'duplicate run ID');ids.add(run['id'])
        for key,allowed in [('run_type',{'PILOT','FORMAL'}),('data_status',{'REAL','SYNTHETIC','MIXED'}),
                            ('validation_status',{'NOT_VALIDATED','PIT_VERIFIED','REVIEWED'})]:
            require(run[key] in allowed,'invalid status')
        require(run['qgv_version']=='v2','QGV version changed')
        keys(run['universe'],{'definition','point_in_time','survivorship_note'})
        require(type(run['universe']['point_in_time']) is bool,'PIT flag must be boolean')
        require(all(text(run['universe'][k])for k in ('definition','survivorship_note')),'universe missing')
        keys(run['period'],{'start','end'})
        start,end=(date.fromisoformat(run['period'][k])for k in ('start','end'))
        require(start<=end,'period reversed')
        keys(run['benchmark'],{'name','total_return'})
        require(text(run['benchmark']['name']) and type(run['benchmark']['total_return']) is bool,
                'benchmark missing')
        keys(run['costs'],{'fee_bps','slippage_bps'})
        require(all(number(x) and x>=0 for x in run['costs'].values()),'invalid costs')
        keys(run['metrics'],METRICS);m=run['metrics'];reasons=run['null_reasons']
        require(isinstance(reasons,dict) and set(reasons)=={k for k,v in m.items()if v is None},
                'null reasons must exactly cover missing metrics')
        require(all(text(v) for v in reasons.values()),'empty null reason')
        require(all(v is None or number(v)for v in m.values()),'nonfinite or nonnumeric metric')
        require(m['max_drawdown'] is None or -1<=m['max_drawdown']<=0,'MDD must be negative fraction')
        require(m['volatility'] is None or m['volatility']>=0,'negative volatility')
        for k in ('cagr','total_return','benchmark_cagr'):
            require(m[k] is None or m[k]>=-1,'return below total loss')
        if m['excess_cagr'] is not None:
            require(m['cagr'] is not None and m['benchmark_cagr'] is not None and
                    math.isclose(m['excess_cagr'],m['cagr']-m['benchmark_cagr'],abs_tol=1e-12),
                    'excess CAGR mismatch')
        curve=run['equity_curve'];require(isinstance(curve,list),'curve must be list')
        previous=None
        for i,row in enumerate(curve):
            keys(row,{'date','strategy','benchmark'})
            require(isinstance(row['date'],str) and re.fullmatch(r'\d{4}-\d{2}',row['date']),
                    'curve date must be YYYY-MM')
            date.fromisoformat(row['date']+'-01')
            require(start.isoformat()[:7]<=row['date']<=end.isoformat()[:7],'curve outside period')
            require(previous is None or previous<row['date'],'curve duplicate or reversed')
            previous=row['date']
            require(all(number(row[k]) and row[k]>=0 for k in ('strategy','benchmark')),'invalid curve value')
            if i==0:require(row['strategy']==row['benchmark']==100,'curve must start at 100')
        if m['total_return'] is not None:
            require(bool(curve),'return needs curve')
            require(curve[0]['date']==start.isoformat()[:7] and curve[-1]['date']==end.isoformat()[:7],
                    'curve endpoints do not match period')
            require(math.isclose(curve[-1]['strategy']/100-1,m['total_return'],abs_tol=1e-12),
                    'final return mismatch')
        require(isinstance(run['limitations'],list) and all(text(x)for x in run['limitations']),
                'limitations must be text list')


def summarize(snapshots, expected_sessions, metrics_module):
    """Use the preserved #417 engine; daily risk metrics precede chart sampling."""
    require(bool(snapshots),'no ledger result')
    require(all(s['status']=='COMPLETE' and s['nav'] is not None for s in snapshots),'incomplete NAV')
    points=[metrics_module.NavPoint(date.fromisoformat(s['session']),float(s['nav']))for s in snapshots]
    require([p.date for p in points]==list(expected_sessions),'missing or duplicate session')
    require(points[0].nav>0,'invalid initial NAV')
    raw=metrics_module.performance_metrics(points,expected_sessions=expected_sessions)
    mapping={'cagr':'cagr','total_return':'cumulative_return','max_drawdown':'max_drawdown',
             'volatility':'annualized_volatility','sharpe':'sharpe'}
    values={k:raw[v].value for k,v in mapping.items()}
    reasons={k:raw[v].reason for k,v in mapping.items()if raw[v].value is None}
    values['benchmark_cagr']=0.0  # Explicit nominal cash diagnostic, not a market observation.
    values['excess_cagr']=values['cagr']
    if values['excess_cagr'] is None:reasons['excess_cagr']=reasons['cagr']
    first=points[0];monthly={}
    for p in points:
        if p.date.isoformat()[:7]!=first.date.isoformat()[:7]:monthly[p.date.isoformat()[:7]]=p.nav
    curve=[{'date':first.date.isoformat()[:7],'strategy':100.0,'benchmark':100.0}]
    curve.extend({'date':d,'strategy':v/first.nav*100,'benchmark':100.0}for d,v in monthly.items())
    return {'metrics':values,'null_reasons':reasons,'equity_curve':curve}
