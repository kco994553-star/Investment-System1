"""Pure private-report assembly: no filesystem writes, data fetches or publishing."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from html import escape
import math

from . import metrics as m


METRICS = ('cagr', 'cumulative_return', 'max_drawdown', 'sharpe', 'sortino',
           'information_ratio', 'annualized_volatility')


def _encode(value):
    if is_dataclass(value):
        return _encode(asdict(value))
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def _na(reason):
    return {'value': None, 'reason': reason}


def _metric(value, reason='MISSING_METRIC'):
    if isinstance(value, m.Metric):
        return _encode(value)
    if isinstance(value, dict):
        if value.get('value') is None:
            return _na(value.get('reason') or reason)
        value = value['value']
    if value is None or isinstance(value, bool):
        return _na(reason)
    try:
        numeric = float(value)
    except (ValueError, TypeError):
        return _na('INVALID_METRIC')
    return {'value': numeric, 'reason': None} if math.isfinite(numeric) else _na('INVALID_METRIC')


def _monthly(rows):
    return [item if isinstance(item, m.MonthlyReturn) else m.MonthlyReturn(
        date.fromisoformat(item['start']), date.fromisoformat(item['end']),
        float(item['value']) if item.get('value') is not None else None, item.get('full_month', True))
        for item in rows]


def _points(run):
    return [m.NavPoint(date.fromisoformat(item['session']),
                       float(item['nav']) if item.get('nav') is not None else None)
            for item in run.get('nav', [])]


def _key(run):
    cell = run['cell']
    return (cell.get('period_id'), cell['strategy_id'], cell['panel'], cell['cost_bps'],
            cell.get('execution_delay', 0))


def _benchmark_label(detailed, period_id):
    """Keep the validated runner identity; infer only registered period types."""
    supplied = detailed.get('benchmark_label')
    if supplied and detailed.get('period_id') == period_id:
        return supplied
    if period_id == 'TARGET_QGV_V2':
        return 'SP500_TR_INDEX'
    if period_id in ('SECONDARY_DIAGNOSTIC_NOT_TARGET', 'DATA_LIMITED_DIAGNOSTIC_NOT_TARGET'):
        return 'SPY_TR'
    return 'BENCHMARK'


def _difference(candidate, baseline, metric):
    if candidate is None or baseline is None:
        return _na('MISSING_STRATEGY_RUN')
    a, b = candidate['metrics'].get(metric, _na('MISSING_METRIC')), baseline['metrics'].get(metric, _na('MISSING_METRIC'))
    if a['value'] is None or b['value'] is None:
        return _na(a.get('reason') or b.get('reason') or 'MISSING_METRIC')
    return _metric(a['value'] - b['value'])


def _run_summary(spec, run):
    points = _points(run)
    declared = next((period for period in spec.get('period', {}).get('data_feasibility_ladder', [])
                     if period['label'] == run['cell'].get('period_id')), None)
    actual_points = ([point for point in points if point.date >= date.fromisoformat(declared['start'])]
                     if declared else points)
    incomplete = not points or any(point.nav is None for point in points)
    supplied = run.get('metrics') or {}
    summary = dict(cell=dict(run['cell']), status=run.get('status', 'NOT_RUN'),
                   blockers=list(run.get('blockers', [])), metrics={name: _metric(supplied.get(name)) for name in METRICS})
    if incomplete:
        summary['status'] = 'INCOMPLETE_NAV'
        for name in ('cagr', 'cumulative_return', 'max_drawdown', 'annualized_volatility'):
            summary['metrics'][name] = _na('INCOMPLETE_NAV')
    if run.get('monthly'):
        try:
            risk = m.monthly_risk_metrics(_monthly(run['monthly']),
                risk_free_monthly=_monthly(run['risk_free']) if run.get('risk_free') else None,
                benchmark_monthly=_monthly(run['benchmark']) if run.get('benchmark') else None)
            summary['metrics'].update({name: _encode(risk[name]) for name in
                                       ('sharpe', 'sortino', 'information_ratio')})
        except (ValueError, TypeError, KeyError):
            summary['metrics'].update({name: _na('INVALID_MONTHLY_INPUT') for name in
                                       ('sharpe', 'sortino', 'information_ratio')})
    else:
        summary['metrics'].update({name: _na('MISSING_MONTHLY_RETURNS') for name in
                                   ('sharpe', 'sortino', 'information_ratio')})
    try:
        daily = m.performance_metrics(points)
        summary['annual_returns'] = supplied.get('annual_returns', daily['annual_returns'])
        summary['worst_year'] = supplied.get('worst_year', daily['worst_year'])
    except ValueError:
        summary['annual_returns'], summary['worst_year'] = {}, None
        summary['blockers'].append('INVALID_NAV')
    trades = []
    for fill in run.get('fills', []):
        quantity = float(fill.get('quantity', 0))
        trades.append(dict(date=date.fromisoformat(fill['session']),
                           side=fill.get('side', 'BUY' if quantity >= 0 else 'SELL'),
                           notional=abs(float(fill['gross']))))
    try:
        summary['annual_turnover'] = _encode(m.annual_turnover(trades, actual_points))
    except (ValueError, TypeError, KeyError):
        summary['annual_turnover'] = {}
        summary['blockers'].append('INVALID_TURNOVER_INPUT')
    fees = sum(float(fill.get('fee', 0)) for fill in run.get('fills', []))
    summary['booked_costs'] = fees
    summary['fixed_trade_cost_attribution'] = {
        'method': 'BOOKED_COST_ONLY_NO_INTEREST_REPLAY',
        'same_executed_quantities': True,
        'independent_zero_bps_run_is_separate': True,
        'multipliers': [{'multiplier': factor,
                         'cost_total': fees * factor,
                         'cost_subtracted_final_nav': (points[-1].nav + fees * (1 - factor)
                                                        if points and not incomplete else None)}
                        for factor in spec.get('costs', {}).get('locked_trade_cost_attribution_multipliers', [1, 2, 3])]}
    summary['regime_summaries'] = []
    for window in spec.get('period', {}).get('regime_windows', []):
        start, end = date.fromisoformat(window['start']), date.fromisoformat(window['end'])
        inside = [point for point in points if start <= point.date <= end]
        previous = [point for point in points if point.date < start]
        if inside and previous:
            inside.insert(0, previous[-1])
        entry = dict(label=window['label'], requested_start=window['start'], requested_end=window['end'],
                     observed_start=str(inside[0].date) if inside else None,
                     observed_end=str(inside[-1].date) if inside else None,
                     coverage_status='OBSERVED_SUBWINDOW', metrics={})
        if not inside:
            entry.update(coverage_status='NOT_RUN', metrics={name: _na('NO_NAV_IN_WINDOW') for name in METRICS})
        else:
            entry['metrics'] = _encode(m.performance_metrics(inside))
            # This is deliberately conservative without a session-calendar
            # object: do not infer complete coverage from weekday assumptions.
            if inside[0].date <= start and inside[-1].date == end:
                entry['coverage_status'] = 'BOUNDARIES_OBSERVED'
        summary['regime_summaries'].append(entry)
    summary['coverage'] = run.get('coverage', [])
    summary['exposure'] = run.get('exposure', [])
    summary['unfilled_count'] = len(run.get('unfilled', []))
    return summary


def build_report(spec, detailed):
    """Assemble JSON-ready evidence, retaining every unexecuted registry row.

    Only COMMON/N15/quarterly/10bps, zero-delay W1/W2/W3 versus W0 receive
    candidate labels. Missing RF, incomplete runs or <60 complete months keep
    decisions unavailable. This function does not claim OOS or operational
    adoption. Callers alone control verified private artifact storage.
    """
    raw = [dict(run, cell=dict(run['cell'], period_id=run['cell'].get('period_id', detailed.get('period_id'))))
           for run in detailed.get('runs', [])]
    summaries = [_run_summary(spec, run) for run in raw]
    periods = spec.get('period', {}).get('data_feasibility_ladder', [])
    report = dict(spec_id=spec.get('spec_id'), status='REPORT_PARTIAL',
                  period_id=detailed.get('period_id'), oos_status=detailed.get('oos_status', 'OOS_NOT_ESTABLISHED'),
                  benchmark_label=_benchmark_label(detailed, detailed.get('period_id')),
                  private_only=True, blockers=list(detailed.get('blockers', [])), runs=summaries,
                  strategy_period_status=[], primary_comparisons=[], diagnostic_effects=[],
                  frequency_deltas=[], selection_overlap=[])
    index = {}
    raw_index = {}
    duplicates = set()
    for run, summary in zip(raw, summaries):
        key = _key(run)
        if key in index:
            duplicates.add(key)
        index[key], raw_index[key] = summary, run
    if duplicates:
        report['blockers'].append('DUPLICATE_RUN_CELL')
        for key in duplicates:
            index.pop(key, None)
            raw_index.pop(key, None)
    expected_cells = 2 * len(spec.get('costs', {}).get('sensitivity_one_way_bps', [10]))
    for period in periods:
        for strategy in spec['strategies']:
            matching = [summary for key, summary in index.items()
                        if key[0] == period['label'] and key[1] == strategy['id'] and key[4] == 0]
            completed = sum(row['status'] == 'COMPLETE' for row in matching)
            status = ('NOT_RUN' if not matching else 'COMPLETE' if completed == expected_cells else
                      'INCOMPLETE' if any(row['status'] != 'COMPLETE' for row in matching) else 'PARTIAL_CELLS')
            report['strategy_period_status'].append(dict(period_id=period['label'], strategy_id=strategy['id'],
                status=status, completed_cells=completed, expected_cells=expected_cells))
    active_periods = list(dict.fromkeys([run['cell'].get('period_id', detailed.get('period_id')) for run in raw]))
    if not active_periods:
        active_periods = [detailed.get('period_id')]
    for period_id in active_periods:
        benchmark_label = _benchmark_label(detailed, period_id)
        key_for = lambda strategy: (period_id, strategy, 'COMMON', 10, 0)
        baseline = raw_index.get(key_for('W0-N15-Q'))
        selected = {f'W{i}': raw_index.get(key_for(f'W{i}-N15-Q')) for i in range(4)}
        bootstrap, failure = None, None
        try:
            series = {name: _monthly(run['monthly']) for name, run in selected.items()
                      if run and run.get('monthly')}
            if baseline and baseline.get('benchmark'):
                series[benchmark_label] = _monthly(baseline['benchmark'])
            if baseline and baseline.get('risk_free'):
                series['RF'] = _monthly(baseline['risk_free'])
            if 'W0' in series:
                bootstrap = m.paired_monthly_bootstrap(series)
        except (ValueError, TypeError, KeyError):
            failure = 'MONTHLY_ALIGNMENT_OR_INPUT_INVALID'
        for candidate in ('W1', 'W2', 'W3'):
            row = dict(period_id=period_id, candidate=candidate, baseline='W0',
                       panel='COMMON', n=15, cost_bps=10, rebalance='QUARTERLY',
                       benchmark_label=benchmark_label,
                       missing_inputs=[], approximate_inference=True)
            candidate_run = selected[candidate]
            if baseline is None or candidate_run is None:
                reason = 'MISSING_STRATEGY_RUN'
            elif not baseline.get('monthly') or not candidate_run.get('monthly'):
                reason = 'MISSING_MONTHLY_RETURNS'
            else:
                reason = failure
            comparison = bootstrap and bootstrap['comparisons'].get(candidate)
            if reason or comparison is None:
                row.update(observed_difference=_na(reason or 'MISSING_MONTHLY_RETURNS'),
                           lower_bound=_na(reason or 'MISSING_MONTHLY_RETURNS'))
            else:
                row.update(_encode(comparison))
                row['bootstrap'] = {key: value for key, value in bootstrap.items() if key != 'comparisons'}
            a, b = index.get(key_for(f'{candidate}-N15-Q')), index.get(key_for('W0-N15-Q'))
            # Drawdown values are negative: baseline - candidate is worsening
            # of the positive loss magnitude. Baseline - candidate Sharpe is
            # the observed deterioration.
            worsening = _difference(b, a, 'max_drawdown')
            deterioration = _difference(b, a, 'sharpe')
            row.update(mdd_worsening=worsening, sharpe_deterioration=deterioration)
            if candidate_run is not None and baseline is not None:
                if not candidate_run.get('risk_free') or not baseline.get('risk_free'):
                    row['missing_inputs'].append('MISSING_RISK_FREE')
                if not candidate_run.get('benchmark') or not baseline.get('benchmark'):
                    row['missing_inputs'].append('MISSING_BENCHMARK')
                if a['status'] != 'COMPLETE' or b['status'] != 'COMPLETE':
                    row['missing_inputs'].append('INCOMPLETE_STRATEGY_RUN')
            bound = row['lower_bound']['value'] if not row['missing_inputs'] else None
            row['decision'] = m.primary_decision(row['observed_difference']['value'], bound,
                worsening['value'], deterioration['value'], panel='COMMON', n=15, rebalance='QUARTERLY', cost_bps=10)
            report['primary_comparisons'].append(row)

    groups = sorted({(key[0], key[2], key[3]) for key in index}, key=str)
    effects = [('D0', 'W0'), ('D2', 'W2'), ('W2', 'W0'), ('D2', 'D0'), ('W1', 'D0'), ('W3', 'D2')]
    for period_id, panel, cost in groups:
        lookup = lambda strategy: index.get((period_id, strategy, panel, cost, 0))
        for candidate, baseline in effects:
            a, b = lookup(f'{candidate}-N15-Q'), lookup(f'{baseline}-N15-Q')
            report['diagnostic_effects'].append(dict(period_id=period_id, panel=panel, cost_bps=cost,
                comparison=f'{candidate}-{baseline}', cagr_difference=_difference(a, b, 'cagr'),
                max_drawdown_difference=_difference(a, b, 'max_drawdown'), sharpe_difference=_difference(a, b, 'sharpe')))
        for n in (25, 50):
            for variant in ('W0', 'W1', 'W2', 'W3'):
                a, b = lookup(f'{variant}-N{n}-Q'), lookup(f'{variant}-N{n}-Y')
                report['frequency_deltas'].append(dict(period_id=period_id, panel=panel, cost_bps=cost,
                    variant=variant, n=n, orientation='QUARTERLY_MINUS_ANNUAL',
                    cagr_difference=_difference(a, b, 'cagr'), max_drawdown_difference=_difference(a, b, 'max_drawdown'),
                    sharpe_difference=_difference(a, b, 'sharpe')))
        baseline_run = raw_index.get((period_id, 'W0-N15-Q', panel, cost, 0))
        if baseline_run:
            before = {row['signal_day']: row['selected'] for row in baseline_run.get('decisions', [])}
            for variant in ('W1', 'W2', 'W3', 'D0', 'D2'):
                candidate_run = raw_index.get((period_id, f'{variant}-N15-Q', panel, cost, 0))
                after = {row['signal_day']: row['selected'] for row in candidate_run.get('decisions', [])} if candidate_run else {}
                for signal in sorted(set(before) | set(after)):
                    change = m.selection_changes(before[signal], after[signal]) if signal in before and signal in after else dict(jaccard=None, reason='MISSING_SELECTION')
                    report['selection_overlap'].append(dict(period_id=period_id, panel=panel, cost_bps=cost,
                        comparison=f'{variant}-W0', signal_day=signal, **change))
    if (report['strategy_period_status'] and not report['blockers']
            and all(row['status'] == 'COMPLETE' for row in report['strategy_period_status'])
            and all(row['decision']['status'] == 'OK' for row in report['primary_comparisons'])):
        report['status'] = 'REPORT_COMPLETE'
    return _encode(report)


def render_markdown(report):
    """Compact local report table; NA retains its reason."""
    def display(metric, percent=False):
        if metric.get('value') is None:
            return f"NA ({metric.get('reason', 'MISSING_METRIC')})"
        return f"{metric['value'] * 100:.2f}%" if percent else f"{metric['value']:.3f}"
    rows = ['Private QGV research report', '', f"Status: {report['status']}", '',
            '| Strategy | Period | Panel | Cost bps | CAGR | MDD | Sharpe | Sortino |',
            '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for run in report['runs']:
        cell, metrics = run['cell'], run['metrics']
        label = str(cell['strategy_id']).replace('|', '\\|').replace('\n', ' ')
        rows.append(f"| {label} | {cell.get('period_id', '')} | {cell['panel']} | {cell['cost_bps']} | "
                    f"{display(metrics['cagr'], True)} | {display(metrics['max_drawdown'], True)} | "
                    f"{display(metrics['sharpe'])} | {display(metrics['sortino'])} |")
    return '\n'.join(rows) + '\n'


def render_svg(detailed):
    """Self-contained private NAV/drawdown SVG; missing NAV breaks each path."""
    runs = list(detailed.get('runs', []))
    preferred = [run for run in runs if run['cell'].get('panel') == 'COMMON'
                 and run['cell'].get('cost_bps') == 10 and not run['cell'].get('execution_delay')
                 and run['cell'].get('strategy_id') in {f'W{i}-N15-Q' for i in range(4)}]
    chosen = preferred or runs[:4]
    reference = next((run for run in chosen if run.get('benchmark_nav')), None)
    if reference:
        chosen = chosen + [dict(cell=dict(strategy_id=detailed.get('benchmark_label') or 'BENCHMARK'), nav=reference['benchmark_nav'],
                                status=reference.get('status', 'UNKNOWN'))]
    valid = [(point.date, point.nav) for run in chosen for point in _points(run) if point.nav is not None]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650" viewBox="0 0 1000 650">',
             '<rect width="1000" height="650" fill="white"/>',
             '<text x="60" y="25" font-family="sans-serif" font-size="18">Private research NAV and drawdown</text>']
    if not valid:
        return ''.join(parts + ['<text x="60" y="60">NA: NO_COMPLETE_NAV</text></svg>'])
    first, last = min(item[0] for item in valid), max(item[0] for item in valid)
    lo, hi = min(item[1] for item in valid), max(item[1] for item in valid)
    width = max(1, (last - first).days)
    span = hi - lo or max(abs(hi) * .01, 1)
    x = lambda day: 60 + (day - first).days / width * 880
    y = lambda value: 290 - (value - lo) / span * 220
    parts.extend(['<path d="M60 60V290H940 M60 360V580H940" fill="none" stroke="#555"/>',
                  '<text x="10" y="70">NAV</text><text x="5" y="375">DD%</text>'])
    colors = ('#2459aa', '#c44e35', '#168064', '#804eaa', '#555555')
    for order, run in enumerate(chosen):
        color = colors[order % len(colors)]
        label = escape(str(run['cell']['strategy_id']))
        status = escape(str(run.get('status', 'UNKNOWN')))
        parts.append(f'<text x="{60 + order * 175}" y="{45}" fill="{color}" font-size="10">{label} ({status})</text>')
        peak, nav_segment, dd_segment = None, [], []
        segments = []
        for point in _points(run):
            if point.nav is None:
                if nav_segment:
                    segments.append((nav_segment, dd_segment))
                nav_segment, dd_segment = [], []
                continue
            peak = point.nav if peak is None else max(peak, point.nav)
            dd = point.nav / peak - 1 if peak else 0
            nav_segment.append(f'{x(point.date):.2f},{y(point.nav):.2f}')
            dd_segment.append(f'{x(point.date):.2f},{360 - dd * 220:.2f}')
        if nav_segment:
            segments.append((nav_segment, dd_segment))
        for nav_segment, dd_segment in segments:
            for segment in (nav_segment, dd_segment):
                parts.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2"/>')
    parts.append(f'<text x="60" y="620" font-size="12">{first.isoformat()} to {last.isoformat()}; gaps indicate missing NAV. Drawdown scale: 0 to -100%.</text>')
    return ''.join(parts + ['</svg>'])
