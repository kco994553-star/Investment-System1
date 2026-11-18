"""Source-aware TABLE-A--V views over one replay; never run a backtest here."""
from __future__ import annotations

from datetime import date
import json
import math
import random
from statistics import fmean, median

from .extensions import ACTIVE_FACTORS, GROUPS, finite
from . import metrics as m
from .reporting import _encode, _monthly, _run_summary

SOURCE_TYPES = frozenset(('BOOK_REPORTED','EXTERNAL_RESEARCH','EXTERNAL_FACTOR_SERIES',
    'QGV_REPRODUCED','MATCHED_HEAD_TO_HEAD','NOT_VERIFIED','BLOCKED_ON_DATA'))
CONDITIONS = ('universe','start','end','weighting','rebalance','cost_bps','frequency','currency',
              'dividends','execution','candidate_basis','cash')
TITLES = ('전략 수익·위험 요약','전체 10분위 성과 기울기','연도별 수익률','기간·시장 국면',
    '최악·중앙·최선 롤링 수익률','실증성·자료 적합성','단일 팩터와 복합점수','모집단별 결과',
    '시총 분위별 성과','규모 × QGV','Base Rate','최악의 경우·하방 위험','상승·하락 민감도',
    '업종 기여·편향','시총 문턱·거래 가능성','비용·주기 강건성','팩터 BEST10 대 QGV BEST10',
    '팩터·QGV 롤링 승률','복합전략 산식 상태','전체시장 대 역사 S&P500','팩터 시대별 차이','자료 충족·검증 단계')


def result_cell(value, source_type, source_ref, conditions, *, reason=None, verification_status='SOURCE_VERIFIED'):
    if source_type not in SOURCE_TYPES:
        raise ValueError('SOURCE_TYPE_INVALID')
    if value is not None and (source_type in ('NOT_VERIFIED','BLOCKED_ON_DATA') or not finite(value)):
        raise ValueError('UNVERIFIED_NUMERIC_RESULT')
    if value is not None and not source_ref:
        raise ValueError('RESULT_SOURCE_REQUIRED')
    return dict(value=value,source_type=source_type,source_ref=source_ref,conditions=dict(conditions),
                reason=reason if value is None else None,verification_status=verification_status)


def compare_cells(a,b):
    differences = [k for k in CONDITIONS if a['conditions'].get(k) != b['conditions'].get(k)
                   or a['conditions'].get(k) is None or b['conditions'].get(k) is None]
    if a['source_type'] != b['source_type']:
        differences.append('source_type')
    if a['verification_status'] != b['verification_status']:
        differences.append('verification_status')
    for key in ('reselection_frequency','formation_month','formation_day_rule'):
        if (key in a['conditions'] or key in b['conditions']) and a['conditions'].get(key)!=b['conditions'].get(key):
            differences.append(key)
    return dict(status='NOT_COMPARABLE' if differences else 'MATCHED_CONDITIONS',differences=differences)


def rolling_statistics(series, benchmark=None, *, years):
    series = _monthly(series)
    m._monthly_validate(series)
    count = years*12
    output = dict(years=years,windows=0,worst=None,median=None,best=None,base_rate=None,
                  overlapping_not_independent=True,status='INSUFFICIENT_MONTHS')
    if benchmark is not None:
        benchmark = _monthly(benchmark)
        if [(r.start,r.end,r.full_month) for r in benchmark] != [(r.start,r.end,r.full_month) for r in series]:
            return dict(output,status='MONTHLY_ALIGNMENT_MISMATCH')
    if any(r.value is None for r in series) or (benchmark is not None and any(r.value is None for r in benchmark)):
        return dict(output,status='INCOMPLETE_MONTHLY_RETURNS')
    gains, wins = [], []
    for i in range(len(series)-count+1):
        window = series[i:i+count]
        if not all(r.full_month for r in window):
            continue
        duration = (window[-1].end-window[0].start).days
        gain = math.prod(1+r.value for r in window)**(365.25/duration)-1
        gains.append(gain)
        if benchmark is not None:
            other = math.prod(1+r.value for r in benchmark[i:i+count])**(365.25/duration)-1
            wins.append(gain > other)
    if gains:
        output.update(windows=len(gains),worst=min(gains),median=median(gains),best=max(gains),
                      base_rate=fmean(wins) if wins else None,status='OK')
    return output


def _ranks(values):
    ordered = sorted(range(len(values)),key=lambda i:values[i])
    ranks, cursor = [0.0]*len(values),0
    while cursor < len(ordered):
        end = cursor+1
        while end < len(ordered) and values[ordered[cursor]] == values[ordered[end]]:
            end += 1
        for i in ordered[cursor:end]:
            ranks[i] = (cursor+1+end)/2
        cursor = end
    return ranks


def decile_monotonicity(curves, *, replications=10000, seed=20261026):
    output = dict(status='MISSING_DECILE_SERIES',mean_spearman=None,negative_mean_lower_bound=None,
                  lower_tail_alpha=.05/20,approximate_inference=True,full_months=0)
    if set(curves) != set(range(1,11)):
        return output
    series = {d:_monthly(rows) for d,rows in curves.items()}
    grid = [(r.start,r.end,r.full_month) for r in series[1]]
    if any([(r.start,r.end,r.full_month) for r in rows] != grid for rows in series.values()):
        return dict(output,status='MONTHLY_ALIGNMENT_MISMATCH')
    if any(r.value is None for rows in series.values() for r in rows):
        return dict(output,status='INCOMPLETE_MONTHLY_RETURNS')
    for rows in series.values():
        m._monthly_validate(rows)
    correlations = []
    for i,row in enumerate(series[1]):
        if not row.full_month:
            continue
        y = _ranks([series[d][i].value for d in range(1,11)])
        dy = [value-fmean(y) for value in y]
        dx = [d-5.5 for d in range(1,11)]
        denominator = math.sqrt(sum(v*v for v in dx)*sum(v*v for v in dy))
        if denominator == 0:
            return dict(output,status='ZERO_CROSS_SECTION_VARIANCE')
        correlations.append(sum(a*b for a,b in zip(dx,dy))/denominator)
    output.update(full_months=len(correlations),mean_spearman=fmean(correlations) if correlations else None)
    if len(correlations)<60:
        return dict(output,status='INSUFFICIENT_MONTHS')
    rng, samples, n = random.Random(seed),[],len(correlations)
    for _ in range(replications):
        indices=[]
        while len(indices)<n:
            start=rng.randrange(n)
            indices.extend((start+k)%n for k in range(min(12,n-len(indices))))
        samples.append(-fmean(correlations[i] for i in indices))
    return dict(output,status='OK',negative_mean_lower_bound=m._quantile(samples,.05/20),
                caution='APPROXIMATE_FEW_BLOCKS_AT_60_MONTHS',block_months=12,replications=replications,seed=seed)


def extension_inference(detailed):
    """Always report all twenty claims, including missing/failed comparisons."""
    primary=detailed.get('extension_spec',{}).get('primary_rebalance','QUARTERLY')
    runs = [r for r in detailed.get('runs',[]) if r['cell'].get('cost_bps')==10 and r['cell'].get('rebalance')==primary
            and r['cell'].get('formation_month') is None]
    def find(group, **criteria):
        return next((r for r in runs if r['cell'].get('group')==group and all(r['cell'].get(k)==v for k,v in criteria.items())),None)
    result=[]
    def contrast(label,candidate,baseline,baseline_monthly=None):
        item=dict(id=label,status='MISSING_STRATEGY_RUN',estimate=None,lower_bound=None)
        if candidate and (baseline or baseline_monthly is not None):
            if candidate.get('status')!='COMPLETE' or (baseline and baseline.get('status')!='COMPLETE'):
                item['status']='INCOMPLETE_REPLAY'
            else:
                try:
                    bootstrap=m.paired_monthly_bootstrap({'candidate':_monthly(candidate['monthly']),
                        'baseline':_monthly(baseline['monthly'] if baseline else baseline_monthly)},baseline='baseline',family_size=20)
                    comparison=bootstrap['comparisons']['candidate']
                    item.update(status=bootstrap['status'],estimate=_encode(comparison['observed_difference']),
                                lower_bound=_encode(comparison['lower_bound']))
                except ValueError:
                    item['status']='MONTHLY_ALIGNMENT_MISMATCH'
        result.append(item)
    for group in GROUPS:
        best=find(group,kind='QGV_DECILE',decile=1)
        contrast(f'H1:{group}:D10',best,find(group,kind='QGV_DECILE',decile=10))
        contrast(f'H1:{group}:EW',best,find(group,kind='ELIGIBLE_EW'))
        contrast(f'H1:{group}:MARKET',best,None,best.get('benchmark') if best else None)
        curves={d:r['monthly'] for d in range(1,11) if (r:=find(group,kind='QGV_DECILE',decile=d)) and r.get('status')=='COMPLETE'}
        result.append(dict(id=f'H2:{group}',**decile_monotonicity(curves)))
        for factor in ACTIVE_FACTORS:
            contrast(f'H3:{group}:{factor}',find(group,factor_id=factor,role='MATCHED_QGV'),find(group,factor_id=factor,role='FACTOR'))
    weight_claims=[]
    if primary=='ANNUAL_FEBRUARY':
        baseline=next((r for r in runs if r['cell'].get('variant')=='W0' and r['cell'].get('kind')=='FIXED_N' and r['cell'].get('panel')=='COMMON'),None)
        for variant in ('W1','W2','W3'):
            candidate=next((r for r in runs if r['cell'].get('variant')==variant and r['cell'].get('kind')=='FIXED_N' and r['cell'].get('panel')=='COMMON'),None)
            claim=dict(id=f'BT01-BookAnnual-v1:{variant}-W0',status='MISSING_STRATEGY_RUN')
            if baseline and candidate and baseline['status']==candidate['status']=='COMPLETE':
                bootstrap=m.paired_monthly_bootstrap({'W0':_monthly(baseline['monthly']),variant:_monthly(candidate['monthly'])})
                claim.update(status=bootstrap['status'],comparison=_encode(bootstrap['comparisons'][variant]))
            weight_claims.append(claim)
    return dict(family_size=20,lower_tail_alpha=.05/20,claims=result,oos_status='OOS_NOT_ESTABLISHED',
                primary_reselection=primary,bt01_annual_separate_family=dict(family_size=3,claims=weight_claims),
                economic_adoption_decision='NOT_AUTOMATIC',synthetic=detailed.get('synthetic',False))


def build_tables(detailed, base_spec=None):
    base_spec=base_spec or {}
    source=detailed.get('provenance',{}).get('run_id','SYNTHETIC_OR_UNEXECUTED')
    synthetic=detailed.get('synthetic') is True
    tables={f'TABLE-{chr(65+i)}':dict(title=title,rows=[],status='BLOCKED_ON_DATA') for i,title in enumerate(TITLES)}
    def order(run):
        role=run['cell'].get('analysis_role')
        return (0 if role=='PRIMARY_ANNUAL_RESELECTION' else 2 if role=='START_MONTH_ROBUSTNESS' else 1,
                run['cell'].get('group',''),run['cell'].get('formation_month',0),run['cell']['strategy_id'])
    for run in sorted(detailed.get('runs',[]),key=order):
        cell=run['cell']
        if not cell.get('group'):
            continue
        conditions=dict(universe=cell['group'],start=run.get('period_start',detailed.get('period',{}).get('start')),end=run.get('period_end',detailed.get('period',{}).get('end')),
            weighting='EW_AT_SIGNAL_CLOSE',rebalance=cell.get('rebalance'),cost_bps=cell['cost_bps'],frequency='DAILY',currency='USD',
            dividends='CASH_REINVEST_AT_REBALANCE',execution='SIGNAL_CLOSE_TO_NEXT_OPEN',
            candidate_basis=cell.get('cohort_id') if cell.get('kind')=='FACTOR_PAIR' else cell['panel'],cash='TBILL',
            reselection_frequency=cell.get('rebalance'),formation_month=cell.get('formation_month',2 if cell.get('rebalance')=='ANNUAL_FEBRUARY' else None),
            formation_day_rule='FIRST_VERIFIED_SESSION' if cell.get('formation_month') is not None else 'THIRD_MONDAY_HOLIDAY_SHIFT')
        verified='SYNTHETIC_ONLY' if synthetic else ('VERIFIED_REAL_RESULTS' if run.get('status')=='COMPLETE' else run.get('status','NOT_RUN'))
        provenance=cell.get('source_type','QGV_REPRODUCED')
        def metric(value,reason=None):
            if isinstance(value,dict):
                reason=value.get('reason',reason)
                value=value.get('value')
            if run.get('status')!='COMPLETE':
                value,reason=None,run.get('status','NOT_RUN')
            return result_cell(value,provenance,source,conditions,reason=reason or 'NOT_COMPUTED',verification_status=verified)
        summary=_run_summary(base_spec,run)
        extra=dict(booked_trading_costs=summary.get('booked_costs'),booked_instrument_fees=summary.get('booked_instrument_fees'),
                   mdd_recovery_sessions=(run.get('metrics') or {}).get('max_drawdown_recovery_sessions'))
        summary['metrics'].update({key:dict(value=value,reason='UNRECOVERED_OR_NOT_COMPUTED' if value is None else None) for key,value in extra.items()})
        changes=[dict(signal=d['signal_day'],execution=d['execution_day'],entry_count=d.get('entry_count'),exit_count=d.get('exit_count'),
                      continuing_count=d.get('continuing_count')) for d in run.get('decisions',[])]
        row=dict(id=cell['strategy_id'],group=cell['group'],cell=dict(cell),metrics={k:metric(v) for k,v in summary['metrics'].items()},
                 comparison_status='WITHIN_RECORDED_CONDITIONS',execution_status=run.get('status'),
                 analysis_role=cell.get('analysis_role'),reselection_frequency=cell.get('rebalance'),formation_month=conditions['formation_month'],
                 formation_day_rule=conditions['formation_day_rule'],book_exactness=cell.get('book_exactness','BOOK_EXACT_UNCONFIRMED'),
                 entry_exit_count=changes,annual_turnover=summary.get('annual_turnover',{}))
        for table in ('TABLE-A','TABLE-B' if cell.get('kind')=='QGV_DECILE' else 'TABLE-G','TABLE-H','TABLE-P','TABLE-T'):
            tables[table]['rows'].append(row)
        for year,value in summary.get('annual_returns',{}).items():
            tables['TABLE-C']['rows'].append(dict(id=f"{cell['strategy_id']}:{year}",metrics={'annual_return':metric(value)}))
        for regime in summary.get('regime_summaries',[]):
            tables['TABLE-D']['rows'].append(dict(id=f"{cell['strategy_id']}:{regime['label']}",metrics={k:metric(v) for k,v in regime['metrics'].items() if isinstance(v,dict) and 'value' in v}))
        if run.get('monthly'):
            for years in (1,3,5,7,10):
                rolling=rolling_statistics(run['monthly'],run.get('benchmark'),years=years)
                rolling_row=dict(id=f"{cell['strategy_id']}:{years}Y",metrics={k:metric(rolling[k],rolling['status']) for k in ('worst','median','best','base_rate')},
                                 windows=rolling['windows'],overlapping_not_independent=True)
                for table in ('TABLE-E','TABLE-K','TABLE-L'):
                    tables[table]['rows'].append(rolling_row)
        tables['TABLE-N']['rows'].append(dict(id=cell['strategy_id'],metrics={'max_drawdown':metric(summary['metrics']['max_drawdown'])},
            concentration=run.get('attribution',{}).get('concentration'),attribution=run.get('attribution'),exposure=run.get('exposure')))
        for table in ('TABLE-F','TABLE-O','TABLE-V'):
            tables[table]['rows'].append(dict(id=cell['strategy_id'],metrics={'eligible_issuers':metric(run['coverage'][0]['eligible_count']) if run.get('coverage') else metric(None)},
                coverage=run.get('coverage',[]),blockers=run.get('blockers',[])))
        if cell.get('kind')=='FACTOR_PAIR':
            for table in ('TABLE-Q','TABLE-U'):
                tables[table]['rows'].append(row)
    # Paired rolling wins use each factor's own matched QGV comparator, not
    # the unfiltered P1 QGV portfolio.
    for run in detailed.get('runs',[]):
        c=run['cell']
        if c.get('role')!='FACTOR' or run.get('status')!='COMPLETE':
            continue
        def execution_key(candidate):
            cc=candidate['cell']
            return tuple(cc.get(key) for key in ('cohort_id','group','panel','cost_bps','rebalance','schedule_mode',
                'formation_month','variant','execution_delay'))+(candidate.get('period_start'),candidate.get('period_end'),cc.get('period_id'))
        other=next((r for r in detailed['runs'] if r['cell'].get('role')=='MATCHED_QGV'
                    and execution_key(r)==execution_key(run) and r.get('status')=='COMPLETE'),None)
        if other:
            for years in (1,3,5,7,10):
                rolling=rolling_statistics(run['monthly'],other['monthly'],years=years)
                tables['TABLE-R']['rows'].append(dict(id=f"{c['strategy_id']}:{years}Y",formation_month=c.get('formation_month'),
                    reselection_frequency=c['rebalance'],schedule_mode=c.get('schedule_mode'),period_start=run.get('period_start'),period_end=run.get('period_end'),metrics={
                    'factor_beats_matched_qgv':result_cell(rolling['base_rate'],'MATCHED_HEAD_TO_HEAD',source,
                    dict(universe=c['group'],years=years,cost_bps=c['cost_bps'],panel=c['panel'],
                         rebalance=c['rebalance'],formation_month=c.get('formation_month'),schedule_mode=c.get('schedule_mode'),
                         start=run.get('period_start'),end=run.get('period_end'),candidate_basis=c.get('cohort_id')),reason=rolling['status'],
                    verification_status='SYNTHETIC_ONLY' if synthetic else 'VERIFIED_REAL_RESULTS')},windows=rolling['windows'],overlapping_not_independent=True))
    for table_id,table in tables.items():
        if not table['rows']:
            reason=('SIZE_PORTFOLIOS_NOT_EXECUTED' if table_id in ('TABLE-I','TABLE-J') else
                    'RISK_DECOMPOSITION_NOT_COMPUTED' if table_id=='TABLE-M' else
                    'BLOCKED_ON_FORMULA' if table_id=='TABLE-S' else 'BLOCKED_ON_DATA')
            table['rows']=[dict(id='NOT_EXECUTED',metrics={'result':result_cell(None,'BLOCKED_ON_DATA' if reason=='BLOCKED_ON_DATA' else 'NOT_VERIFIED',source,{},reason=reason)})]
        else:
            table['status']='SYNTHETIC_ONLY' if synthetic else ('PARTIAL' if any(r.get('execution_status') not in (None,'COMPLETE') for r in table['rows']) else 'RECORDED')
    from .annual import summarize_offsets
    return dict(schema='qgv-source-tables/1',status='REPORT_PARTIAL',tables=tables,
                inference=extension_inference(detailed),real_data_executed=detailed.get('real_data_executed',False),
                primary_reselection=detailed.get('extension_spec',{}).get('primary_rebalance','QUARTERLY'),
                formation_robustness=summarize_offsets(detailed),book_exactness='BOOK_EXACT_UNCONFIRMED',
                synthetic=synthetic,oos_status='OOS_NOT_ESTABLISHED',
                notes=['External evidence cannot fill QGV result cells.','Missing views remain NA with a reason.'])


def render_tables_markdown(report):
    lines=['# QGV TABLE-A~V','',f"상태: {report['status']} / OOS_NOT_ESTABLISHED",'',
           f"주검정 재선정: {report.get('primary_reselection')} / BOOK_EXACT_UNCONFIRMED",'']
    for key,table in report['tables'].items():
        lines.extend([f"## {key} — {table['title']}",'','| 항목 | 지표 | 값 | 출처 유형 | 검증 상태·사유 |','|---|---|---:|---|---|'])
        for row in table['rows']:
            for name,cell in row['metrics'].items():
                value='NA' if cell['value'] is None else str(cell['value'])
                clean=lambda x:str(x).replace('|','\\|').replace('\n',' ')
                lines.append('| '+' | '.join(clean(x) for x in (row['id'],name,value,cell['source_type'],cell['reason'] or cell['verification_status']))+' |')
        lines.append('')
    return '\n'.join(lines)
