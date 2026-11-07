import importlib
from datetime import date

import pytest

from investment_system.research.qgv_backtest.metrics import MonthlyReturn, paired_monthly_bootstrap


def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.research_tables')
    except ModuleNotFoundError:
        pytest.fail('source-aware 22-table renderer missing')


def months(n, value=.01):
    starts = [date(2000+i//12,1+i%12,1) for i in range(n+1)]
    return [MonthlyReturn(a,b,value) for a,b in zip(starts,starts[1:])]


def test_unknown_and_blocked_cells_cannot_carry_a_performance_number():
    module = api()
    with pytest.raises(ValueError,match='UNVERIFIED_NUMERIC'):
        module.result_cell(.1,'NOT_VERIFIED','unknown',{})
    assert module.result_cell(None,'BLOCKED_ON_DATA','input audit',{},reason='MISSING_PIT')['value'] is None
    with pytest.raises(ValueError,match='SOURCE_TYPE'):
        module.result_cell(.1,'invented','x',{})


def test_comparability_requires_same_verified_conditions_not_just_same_cagr():
    module = api()
    conditions = dict(universe='U-SPX-HIST',start='2000-01-01',end='2025-12-31',weighting='EW',
        rebalance='QUARTERLY',cost_bps=10,frequency='DAILY',currency='USD',dividends='CASH_REINVEST_AT_REBALANCE',
        execution='SIGNAL_CLOSE_TO_NEXT_OPEN',candidate_basis='PAIR_F03',cash='TBILL')
    a = module.result_cell(.1,'MATCHED_HEAD_TO_HEAD','private-run',conditions)
    b = module.result_cell(.2,'MATCHED_HEAD_TO_HEAD','private-run',dict(conditions,cost_bps=0))
    assert module.compare_cells(a,b)['status'] == 'NOT_COMPARABLE'
    assert 'cost_bps' in module.compare_cells(a,b)['differences']
    assert module.compare_cells(a,a)['status'] == 'MATCHED_CONDITIONS'
    book = module.result_cell(.1,'BOOK_REPORTED','author excerpt',conditions)
    assert module.compare_cells(a,book)['status'] == 'NOT_COMPARABLE'


def test_empty_data_renders_all_22_tables_without_synthetic_performance():
    module = api()
    report = module.build_tables(dict(status='BLOCKED_ON_DATA',runs=[],period_id='TARGET_QGV_V2'))
    assert set(report['tables']) == {f'TABLE-{chr(c)}' for c in range(ord('A'),ord('V')+1)}
    assert report['real_data_executed'] is False
    assert all(table['rows'] and all(cell['value'] is None for row in table['rows'] for cell in row['metrics'].values()) for table in report['tables'].values())
    text = module.render_tables_markdown(report)
    assert text.count('## TABLE-') == 22
    assert 'NA' in text and '0.00%' not in text


def test_rolling_windows_are_complete_paired_and_not_independent_trials():
    module = api()
    result = module.rolling_statistics(months(24,.01),months(24,0),years=1)
    assert result['windows'] == 13
    assert result['base_rate'] == 1
    assert result['overlapping_not_independent'] is True
    broken = months(24,.01)
    broken[5] = MonthlyReturn(broken[5].start,broken[5].end,None)
    assert module.rolling_statistics(broken,months(24,0),years=1)['status'] == 'INCOMPLETE_MONTHLY_RETURNS'
    assert module.rolling_statistics(months(24),months(24),years=5)['worst'] is None


def test_new_inference_family_is_20_without_changing_old_three_weight_tests():
    series = {'W0':months(60,0),'candidate':months(60,.01)}
    original = paired_monthly_bootstrap(series,replications=20)
    try:
        extended = paired_monthly_bootstrap(series,replications=20,family_size=20)
    except TypeError:
        pytest.fail('separate multiplicity family missing')
    assert original['lower_tail_alpha'] == .05/3
    assert extended['lower_tail_alpha'] == .05/20
    assert extended['comparisons']['candidate']['observed_difference'].value > 0


def test_monotonicity_uses_ten_paired_return_series_and_missing_month_stays_missing():
    module = api()
    curves = {d:months(60,(11-d)/1000) for d in range(1,11)}
    result = module.decile_monotonicity(curves,replications=20)
    assert result['mean_spearman'] == -1
    assert result['lower_tail_alpha'] == .05/20
    curves[10] = months(59)
    assert module.decile_monotonicity(curves,replications=20)['status'] == 'MONTHLY_ALIGNMENT_MISMATCH'


def test_table_r_pairs_each_formation_month_with_its_own_qgv_execution():
    from dataclasses import asdict
    from investment_system.research.qgv_backtest.annual import annual_extension
    runs=[]
    for month in (3,9):
        for role,value in (('FACTOR',.02),('MATCHED_QGV',.01)):
            boundaries=[date(2010+(month-1+i)//12,1+(month-1+i)%12,1) for i in range(25)]
            monthly=[dict(start=str(a),end=str(b),value=value,full_month=True) for a,b in zip(boundaries,boundaries[1:])]
            nav=[dict(session=str(d),nav=str(100000*(1+value)**i)) for i,d in enumerate(boundaries)]
            cell=dict(strategy_id=f'FAC-SPX-F03-Y-{role}-M{month:02}',cohort_id='FAC-SPX-F03-Y',factor_id='F03',
                group='U-SPX-HIST',kind='FACTOR_PAIR',variant='W0',panel='PANEL_FULL_QGV',cost_bps=10,
                rebalance='ANNUAL_FEBRUARY',schedule_mode=f'ANNUAL_OFFSET_{month:02}',formation_month=month,
                role=role,source_type='MATCHED_HEAD_TO_HEAD',analysis_role='START_MONTH_ROBUSTNESS')
            runs.append(dict(cell=cell,status='COMPLETE',monthly=monthly,nav=nav,metrics={},
                period_start=str(boundaries[0]),period_end=str(boundaries[-1]),decisions=[],coverage=[],blockers=[]))
    report=api().build_tables(dict(status='REPLAY_COMPLETE',synthetic=True,runs=runs,extension_spec=annual_extension()))
    rows=[r for r in report['tables']['TABLE-R']['rows'] if r['id'].endswith(':1Y')]
    assert [r['metrics']['factor_beats_matched_qgv']['value'] for r in rows]==[1,1]
    assert len({r['id'] for r in report['tables']['TABLE-R']['rows']})==10
    assert {r['formation_month'] for r in rows}=={3,9}
