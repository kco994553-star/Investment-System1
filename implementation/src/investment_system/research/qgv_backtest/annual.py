"""BookAnnual-v1 overlay; legacy quarterly contracts remain immutable."""
from __future__ import annotations

from datetime import date

from .calendar_adapter import RebalanceDate, day

ANNUAL_SPEC_ID='qgv-reuse-bookannual/2026-10-27.1'


def annual_extension():
    from .extensions import default_extension
    spec=default_extension()
    spec.update(spec_id=ANNUAL_SPEC_ID,primary_rebalance='ANNUAL_FEBRUARY',
        reselection_mode='FULL_UNIVERSE_RESELECTION',book_exactness='BOOK_EXACT_UNCONFIRMED',
        annual_source=dict(spec_id='qgv-book-annual-reselection/2026-10-27.1',
            pr=418,sha='ef745b96621b06802c7055eb64da76f64f2800db',decile_spec='qgv-decile/2026-10-27.4',
            factor_spec='qgv-book-top-deciles/2026-10-27.2'),
        bt01_version='BT-01/BookAnnual-v1',
        additional_fixed_structures=['W1-N15-Y','W2-N15-Y'],
        formation_robustness=dict(months=list(range(1,13)),each_cohort_frequency_months=12,
            day_rule='FIRST_VERIFIED_SESSION_RESEARCH_ASSUMPTION',
            structural_count_multiplier=1,aggregate='INDIVIDUAL_RESULTS_AND_DESCRIPTIVE_RANGE_NOT_BOOK_EXACT'))
    return spec


def fixed_annual_registry():
    return [dict(id=f'W{i}-N15-Y',kind='FIXED_N',variant=f'W{i}',n=15,group='U-SPX-HIST',
        rebalance='ANNUAL_FEBRUARY',phase='P1',analysis_role='PRIMARY_ANNUAL_RESELECTION',
        research_version='BT-01/BookAnnual-v1',registration='NEW' if i in (1,2) else 'REUSED',
        book_exactness='BOOK_EXACT_UNCONFIRMED') for i in range(4)]


def formation_schedule(calendar,start,end,month):
    if type(month) is not int or not 1<=month<=12:
        raise ValueError('FORMATION_MONTH_INVALID')
    start,end=day(start),day(end)
    calendar._check(start)
    calendar._check(end)
    if start>end:
        raise ValueError('SCHEDULE_RANGE_INVALID')
    rows=[]
    for year in range(start.year,end.year+1):
        nominal=date(year,month,1)
        if nominal<calendar.coverage_start or nominal>end:
            continue
        execution=calendar.on_or_after(nominal)
        if execution.day.month!=month or execution.day.year!=year:
            raise ValueError('FORMATION_MONTH_CALENDAR_COVERAGE')
        if start<=execution.day<=end:
            signal=calendar.previous_session(execution.day)
            rows.append(RebalanceDate(nominal,signal.day,execution.day,signal.close_at,execution.open_at))
    return tuple(rows)


def with_formation_months(cells,months):
    if not months or any(type(m) is not int or not 1<=m<=12 for m in months):
        raise ValueError('FORMATION_MONTH_INVALID')
    if any(c['rebalance']!='ANNUAL_FEBRUARY' for c in cells):
        raise ValueError('FORMATION_REQUIRES_ANNUAL_STRATEGY')
    return [dict(cell,formation_month=month,analysis_role='START_MONTH_ROBUSTNESS',
                 schedule_mode=f'ANNUAL_OFFSET_{month:02}',book_exactness='BOOK_EXACT_UNCONFIRMED')
            for cell in cells for month in sorted(set(months))]


def summarize_offsets(detailed):
    groups={}
    for run in detailed.get('runs',[]):
        cell=run['cell']
        if cell.get('formation_month') is None:
            continue
        key=(cell.get('cohort_id'),cell.get('group'),cell.get('role'),cell.get('panel'),cell.get('cost_bps'))
        groups.setdefault(key,[]).append(run)
    rows=[]
    for key,runs in groups.items():
        individuals=[dict(month=r['cell']['formation_month'],status=r['status'],start=r.get('period_start'),
            metrics=r.get('metrics'),membership_changes=[dict(signal=d['signal_day'],entry_count=d['entry_count'],
                exit_count=d['exit_count'],continuing_count=d['continuing_count']) for d in r.get('decisions',[])]) for r in runs]
        complete=len(runs)==12 and {r['cell']['formation_month'] for r in runs}==set(range(1,13)) and all(r['status']=='COMPLETE' for r in runs)
        cagrs=[r.get('metrics',{}).get('cagr',{}).get('value') for r in runs if r.get('metrics')]
        cagrs=[v for v in cagrs if isinstance(v,(int,float))]
        same_period=len({r.get('period_start') for r in runs})==1
        rows.append(dict(cohort_id=key[0],group=key[1],role=key[2],panel=key[3],cost_bps=key[4],
            status='TWELVE_OFFSETS_RECORDED' if complete else 'PARTIAL_OFFSETS',individuals=individuals,
            book_exactness='BOOK_EXACT_UNCONFIRMED',structural_strategy_count=1,
            comparison_status='SAME_PERIOD' if same_period else 'DIFFERENT_FORMATION_WINDOWS',
            descriptive_individual_cagr_range=[min(cagrs),max(cagrs)] if cagrs else None,
            aggregate_portfolio_cagr=None,aggregate_reason='NO_BOOK_EXACT_COMBINATION_ASSUMED'))
    return rows
