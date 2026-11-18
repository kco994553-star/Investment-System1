"""Annual reselection is new membership, not reweighting the old names."""
import copy
from datetime import date, timedelta
import importlib

import pytest

from investment_system.research.qgv_backtest.extensions import default_extension, registered_cells, selected_cells
from investment_system.research.qgv_backtest import runner
from test_qgv_backtest_reuse_runner import large_bundle
from test_qgv_backtest_runner import spec, frozen_spec


def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.annual')
    except ModuleNotFoundError:
        pytest.fail('BookAnnual-v1 versioned overlay missing')


def multi_year_bundle():
    data=large_bundle()
    # Extend the existing hand table with complete synthetic weekday sessions;
    # these are explicitly not a verified historical exchange holiday table.
    rows=[r for r in data['prices'] if r['date']=='2016-02-19']
    d=date(2016,2,22)
    while d<=date(2018,12,31):
        if d.weekday()<5:
            day=str(d)
            data['sessions'].append(dict(day=day,open_at=f'{day}T09:30:00-05:00',close_at=f'{day}T16:00:00-05:00'))
            data['benchmark'].append(dict(date=day,total_return_index=102,open_total_return_index=102,currency='USD'))
            data['rates'].append(dict(public_date=day,annual_yield=0))
            for original in rows:
                row=copy.deepcopy(original)
                row.update(date=day)
                # A post-2017 price change changes the whole-universe QGV V
                # ordering; the original incumbent list must not be frozen.
                if d>=date(2017,1,1):
                    row['open']=row['close']=200-float(original['close'])
                row['basis_alignment'].update(signal_day=day,verified_through=day)
                data['prices'].append(row)
        d+=timedelta(days=1)
    data['coverage_end']='2018-12-31'
    data['universe_coverage']['end']='2018-12-31'
    return data


def long_spec():
    s=spec()
    s['period']['data_feasibility_ladder'][0]['end']='2018-12-31'
    return s


def test_annual_overlay_preserves_legacy_30_40_60_and_adds_exactly_two_fixed_structures():
    module=api()
    legacy=default_extension()
    old=copy.deepcopy(legacy)
    annual=module.annual_extension()
    cells=registered_cells(annual)
    assert len(cells)==100
    assert legacy==old
    assert len(frozen_spec()['strategies'])==30
    active=selected_cells(annual,'primary')
    assert sum(c['kind']=='QGV_DECILE' for c in active)==20
    assert sum(c['kind']=='FACTOR_PAIR' for c in active)==12
    assert all(c['rebalance']=='ANNUAL_FEBRUARY' for c in active)
    fixed=module.fixed_annual_registry()
    assert {c['id'] for c in fixed}=={'W0-N15-Y','W1-N15-Y','W2-N15-Y','W3-N15-Y'}
    assert {c['id'] for c in fixed if c['registration']=='NEW'}=={'W1-N15-Y','W2-N15-Y'}
    assert len({r['id'] for r in frozen_spec()['strategies']}|{r['id'] for r in fixed})==32
    assert annual['spec_id']!=legacy['spec_id']


def test_all_twelve_formation_months_reselect_only_in_their_own_month_once_per_year():
    module=api()
    data=multi_year_bundle()
    cal=runner._calendar(data)
    for month in range(1,13):
        schedule=module.formation_schedule(cal,date(2016,2,16),date(2018,12,31),month)
        assert schedule
        assert all(r.execution_day.month==month for r in schedule)
        assert len({r.execution_day.year for r in schedule})==len(schedule)
        assert all(b.execution_day.year-a.execution_day.year==1 for a,b in zip(schedule,schedule[1:]))
        assert all(cal.previous_session(r.execution_day).day==r.signal_day for r in schedule)
        assert all(not any(s.day.month==month and s.day.year==r.execution_day.year and s.day<r.execution_day for s in cal.sessions)
                   for r in schedule)


def test_annual_and_quarterly_start_identically_but_annual_does_not_trade_on_interim_rank_changes():
    module=api()
    ext=module.annual_extension()
    cells=selected_cells(ext,'primary',['DEC-SPX-W0-Y-D1','DEC-SPX-W0-Q-D1'])
    result=runner.replay_bundle(long_spec(),multi_year_bundle(),'TARGET_QGV_V2',cells=cells,extension=ext)
    assert all(r['status']=='COMPLETE' for r in result['runs'])
    yearly=next(r for r in result['runs'] if r['cell']['rebalance']=='ANNUAL_FEBRUARY')
    quarterly=next(r for r in result['runs'] if r['cell']['rebalance']=='QUARTERLY')
    assert yearly['decisions'][0]['selected']==quarterly['decisions'][0]['selected']
    assert len(yearly['decisions'])==3
    assert len(quarterly['decisions'])==12
    assert all(date.fromisoformat(d['signal_day']).month==2 for d in yearly['decisions'])
    assert yearly['cell']['analysis_role']=='PRIMARY_ANNUAL_RESELECTION'
    assert quarterly['cell']['analysis_role']=='CADENCE_SENSITIVITY'
    assert yearly['decisions'][1]['entry_count']>0
    assert yearly['decisions'][1]['exit_count']>0
    assert all(d['entry_count']+d['continuing_count']==len(d['selected']) for d in yearly['decisions'])
    assert yearly['decisions'][1]['selection_mode']=='FULL_UNIVERSE_RESELECTION'


def test_twelve_month_dimension_does_not_create_12x_structural_ids_or_monthly_trading():
    module=api()
    ext=module.annual_extension()
    cells=module.with_formation_months(selected_cells(ext,'primary',['DEC-SPX-W0-Y-D1']),[1,2,3,4,5,6,7,8,9,10,11,12])
    assert len(cells)==12
    assert len({c['id'] for c in cells})==1
    assert all(c['book_exactness']=='BOOK_EXACT_UNCONFIRMED' for c in cells)
    # Full ledger replay of two offsets is enough to detect a dispatcher which
    # accidentally replaces the formation month with monthly full turnover.
    result=runner.replay_bundle(long_spec(),multi_year_bundle(),'TARGET_QGV_V2',cells=[c for c in cells if c['formation_month'] in (3,9)],extension=ext)
    assert len(result['runs'])==2
    assert {r['cell']['formation_month'] for r in result['runs']}=={3,9}
    for run in result['runs']:
        month=run['cell']['formation_month']
        assert len(run['decisions'])==3
        assert all(date.fromisoformat(d['execution_day']).month==month for d in run['decisions'])
        assert run['period_start']==run['decisions'][0]['execution_day']
    assert len({r['cell']['strategy_id'] for r in result['runs']})==2


def test_fixed_annual_four_variants_use_same_engine_and_new_contract():
    module=api()
    ext=module.annual_extension()
    cells=selected_cells(ext,'primary',['W0-N15-Y','W1-N15-Y','W2-N15-Y','W3-N15-Y'])
    assert len(cells)==8  # COMMON and PRACTICAL remain separate.
    result=runner.replay_bundle(spec(),large_bundle(),'TARGET_QGV_V2',cells=cells,extension=ext)
    assert all(r['status']=='COMPLETE' for r in result['runs'])
    assert {r['cell']['variant'] for r in result['runs']}=={'W0','W1','W2','W3'}
    assert all(r['coverage'][0]['slots']==15 for r in result['runs'])
    assert result['preparation_stats']['score_calls']==1
    assert all(r['cell']['research_version']=='BT-01/BookAnnual-v1' for r in result['runs'])


def test_annual_tables_are_first_and_show_membership_changes_and_12_month_dimension():
    from investment_system.research.qgv_backtest.research_tables import build_tables
    ext=api().annual_extension()
    cells=selected_cells(ext,'primary',['DEC-SPX-W0-Q-D1','DEC-SPX-W0-Y-D1'])
    detailed=runner.replay_bundle(spec(),large_bundle(),'TARGET_QGV_V2',cells=cells,extension=ext)
    report=build_tables(detailed,spec())
    rows=report['tables']['TABLE-A']['rows']
    assert rows[0]['analysis_role']=='PRIMARY_ANNUAL_RESELECTION'
    assert rows[0]['reselection_frequency']=='ANNUAL_FEBRUARY'
    assert rows[0]['book_exactness']=='BOOK_EXACT_UNCONFIRMED'
    assert rows[0]['entry_exit_count'][0]['entry_count']==11
    assert report['primary_reselection']=='ANNUAL_FEBRUARY'
    assert report['inference']['primary_reselection']=='ANNUAL_FEBRUARY'


def test_all_twelve_offset_ledgers_have_individual_metrics_and_no_invented_combined_cagr():
    from investment_system.research.qgv_backtest.research_tables import build_tables
    module=api()
    ext=module.annual_extension()
    cells=module.with_formation_months(selected_cells(ext,'primary',['DEC-SPX-W0-Y-D1']),list(range(1,13)))
    detailed=runner.replay_bundle(long_spec(),multi_year_bundle(),'TARGET_QGV_V2',cells=cells,extension=ext)
    assert len(detailed['runs'])==12
    assert all(r['status']=='COMPLETE' for r in detailed['runs'])
    for run in detailed['runs']:
        executions=[date.fromisoformat(d['execution_day']) for d in run['decisions']]
        assert all(d.month==run['cell']['formation_month'] for d in executions)
        assert len({d.year for d in executions})==len(executions)
        assert run['metrics']['cagr']['value'] is not None
        assert run['metrics']['max_drawdown']['value'] is not None
        assert run['fills']
    summary=module.summarize_offsets(detailed)
    assert len(summary)==1
    assert summary[0]['status']=='TWELVE_OFFSETS_RECORDED'
    assert summary[0]['structural_strategy_count']==1
    assert summary[0]['aggregate_portfolio_cagr'] is None
    assert len(summary[0]['individuals'])==12
    report=build_tables(detailed,long_spec())
    assert len(report['formation_robustness'][0]['individuals'])==12
    assert len(report['tables']['TABLE-P']['rows'])==12
