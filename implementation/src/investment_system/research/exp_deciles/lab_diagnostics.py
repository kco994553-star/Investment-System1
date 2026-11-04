"""Private adapter from preserved one-company metric evidence to Main's Lab v2.

The metric was already computed: this adapter never recalculates it or promotes
it to a score, selection or performance. Main's contract permits aggregate counts
only; the original ratio and company identity remain in the private evidence.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

METRICS = ('cagr', 'total_return', 'max_drawdown', 'volatility', 'sharpe', 'benchmark_cagr', 'excess_cagr')


def single_company(result, *, source_commit, generated_at):
    try:
        if result['result_kind'] != 'SINGLE_COMPANY_METRIC':
            raise ValueError()
        day = result['signal_day']
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError()
        for sha in (result['code_reference'], source_commit):
            if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha):
                raise ValueError()
        if not isinstance(result['ev_sales'], (str, int, float)) or isinstance(result['ev_sales'], bool):
            raise ValueError()
        if not Decimal(str(result['ev_sales'])).is_finite():
            raise ValueError()
        if datetime.fromisoformat(generated_at.replace('Z', '+00:00')).tzinfo is None:
            raise ValueError()
    except (KeyError, ValueError, TypeError, InvalidOperation):
        raise ValueError('SINGLE_COMPANY_EVIDENCE_INVALID') from None
    population_id = 'preserved-single-company-sample'
    run = {
        'id': 'preserved-single-company-metric', 'name': 'Preserved one-company metric',
        'description': 'Previously calculated EV/sales; aggregate calculation status only.',
        'run_type': 'PILOT', 'data_status': 'REAL', 'validation_status': 'NOT_VALIDATED', 'qgv_version': 'v2',
        'universe': {'definition': 'One preserved company observation, not a market universe.',
                     'point_in_time': False, 'survivorship_note': 'Historical population and fixed security identity remain unverified.'},
        'period': None, 'rebalance': None, 'benchmark': None, 'costs': None,
        'metrics': dict.fromkeys(METRICS), 'null_reasons': dict.fromkeys(METRICS, 'NOT_A_STRATEGY_BACKTEST'),
        'equity_curve': [], 'limitations': ['Not strategy performance.', 'C2/U-A/U-B denominators unknown.',
                                          'Metric value and identity remain only in private source evidence.'],
        'result_kind': 'SINGLE_COMPANY_METRIC', 'computation_status': 'COMPUTED', 'not_computed_reason': None,
        'as_of': day, 'sample': {'unit': 'company', 'n_requested': 1, 'n_used': 1, 'selection': 'Previously preserved one-company calculation.'},
        'population': {'id': population_id, 'scope': 'SAMPLE', 'as_of': day, 'completeness': 'COMPLETE', 'n_total': 1, 'null_reason': None},
        'diagnostics': [{'name': 'raw_metric_company_count', 'value': 1, 'unit': 'count', 'null_reason': None,
                         'n_valid': 1, 'n_total': 1, 'population_ref': population_id}],
    }
    return {'schema_version': 'lab-backtest-v2', 'generated_at': generated_at, 'source_commit': source_commit, 'runs': [run]}
