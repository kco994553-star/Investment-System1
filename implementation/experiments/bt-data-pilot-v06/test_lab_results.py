"""Synthetic boundary fixtures only; these are never Lab production results."""
from copy import deepcopy
from datetime import date
import importlib
import math

import pytest


def module():
    try:
        return importlib.import_module('lab_results')
    except ModuleNotFoundError:
        pytest.fail('private Lab contract adapter is not implemented')


def payload():
    return {'schema_version': 'lab-backtest-v1', 'generated_at': '2026-10-31T00:00:00Z',
            'source_commit': 'a' * 40, 'runs': [{
        'id': 'TEST-ONLY', 'name': 'Synthetic contract fixture', 'description': 'test only',
        'run_type': 'PILOT', 'data_status': 'SYNTHETIC', 'validation_status': 'NOT_VALIDATED',
        'qgv_version': 'v2', 'universe': {'definition': 'synthetic', 'point_in_time': False,
                                      'survivorship_note': 'not market data'},
        'period': {'start': '2020-01-31', 'end': '2020-03-31'}, 'rebalance': 'annual',
        'benchmark': {'name': 'nominal cash diagnostic', 'total_return': False},
        'costs': {'fee_bps': 10, 'slippage_bps': 0},
        'metrics': {'cagr': None, 'total_return': -.1, 'max_drawdown': -.25,
                    'volatility': None, 'sharpe': None, 'benchmark_cagr': 0, 'excess_cagr': None},
        'null_reasons': {'cagr': 'test', 'volatility': 'test', 'sharpe': 'MISSING_RISK_FREE',
                         'excess_cagr': 'test'},
        'equity_curve': [{'date': '2020-01', 'strategy': 100, 'benchmark': 100},
                         {'date': '2020-03', 'strategy': 90, 'benchmark': 100}],
        'limitations': ['synthetic test only']} ]}


def test_empty_result_and_valid_fixture():
    doc=payload(); module().validate(doc)
    doc['runs']=[]; module().validate(doc)


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(source_commit='short'),
    lambda d: d.update(generated_at='2026-10-31T00:00:00'),
    lambda d: d['runs'][0]['metrics'].update(max_drawdown=.25),
    lambda d: d['runs'][0]['metrics'].update(total_return=0),
    lambda d: d['runs'][0]['metrics'].update(volatility=float('nan')),
    lambda d: d['runs'][0]['metrics'].update(sharpe=True),
    lambda d: d['runs'][0]['null_reasons'].pop('sharpe'),
    lambda d: d['runs'][0]['equity_curve'][0].update(strategy=99),
    lambda d: d['runs'][0]['equity_curve'].append(d['runs'][0]['equity_curve'][0]),
    lambda d: d['runs'][0].update(prices=[10]),
    lambda d: d['runs'][0]['costs'].update(fee_bps=-1),
    lambda d: d['runs'][0]['universe'].update(point_in_time='false'),
    lambda d: d['runs'].append(deepcopy(d['runs'][0])),
    lambda d: d['runs'][0]['equity_curve'][1].update(date='2020-04'),
    lambda d: d['runs'][0]['metrics'].update(cagr=.1, excess_cagr=.2),
])
def test_contract_rejects_invalid_or_private_fields(mutation):
    doc=payload();mutation(doc)
    with pytest.raises(ValueError):module().validate(doc)


def test_daily_metrics_not_monthly_decimated_metrics_and_missing_day_blocks(reviewed_metrics):
    # Intermediate 80 is omitted from display curve, but must set daily MDD=-.2.
    snapshots=[{'session':d,'nav':n,'status':'COMPLETE'} for d,n in
               [('2020-01-31',100),('2020-02-03',80),('2020-02-04',110)]]
    expected=[date(2020,1,31),date(2020,2,3),date(2020,2,4)]
    result=module().summarize(snapshots, expected, reviewed_metrics)
    assert result['metrics']['total_return']==pytest.approx(.1)
    assert result['metrics']['max_drawdown']==pytest.approx(-.2)
    assert result['metrics']['volatility']==pytest.approx(.575/math.sqrt(2)*math.sqrt(252))
    assert result['metrics']['sharpe'] is None
    assert result['null_reasons']['sharpe']=='MISSING_RISK_FREE'
    assert [r['date']for r in result['equity_curve']]==['2020-01','2020-02']
    assert [r['strategy']for r in result['equity_curve']]==pytest.approx([100,110])
    assert [r['benchmark']for r in result['equity_curve']]==[100,100]
    with pytest.raises(ValueError):module().summarize(snapshots[::2],expected,reviewed_metrics)


@pytest.fixture
def reviewed_metrics():
    # Optional external preserved engine; production CLI requires it explicitly.
    import os, pathlib, sys
    path=pathlib.Path(os.environ.get('BT_PILOT_REVIEWED_SRC','/workspace/Investment-System1/implementation/src'))
    if not (path/'investment_system/research/qgv_backtest/metrics.py').exists():
        pytest.skip('preserved #417 engine dependency is not installed')
    from audit_v_ledger import bootstrap
    bootstrap(path)
    return importlib.import_module('investment_system.research.qgv_backtest.metrics')


def test_duplicate_json_keys_rejected():
    with pytest.raises(ValueError):module().loads('{"runs": [], "runs": []}')


def test_mixed_old_archive_does_not_relabel_another_company_as_abt():
    import export_lab_pilot
    select=getattr(export_lab_pilot,'abt_request',None)
    assert select is not None,'reuse must select company before normalizing old multi-company archives'
    meta={'request':{'symbol':'AAPL'},'arguments':{'feed':'sip','adjustment':'raw',
          'start':'2016-03-28T00:00:00-04:00','end':'2016-04-01T23:59:59-04:00'}}
    assert select(meta,'2016-02-12','2017-02-21') is None
    meta['request']['symbol']='ABT'
    selected=select(meta,'2016-02-12','2017-02-21')
    assert selected['symbol']=='ABT'
    assert selected['days']==['2016-03-28','2016-03-29','2016-03-30','2016-03-31','2016-04-01']
