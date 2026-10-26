"""Local-only orchestration for the frozen QGV research experiment.

The command-facing API returns status metadata. All security-level inputs,
scores, fills, NAVs and performance stay in the verified private destination.
No provider, network client, operational pipeline or public output is used.
"""
from __future__ import annotations

import csv
import calendar as civil_calendar
import hashlib
import io
import json
import os
from bisect import bisect_right
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .config import audit_inputs, execution_cells, period_for, validate_spec


STAGES = ('audit', 'smoke', 'primary', 'sensitivity', 'report')


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _number(value, *, positive=False, signed=False):
    try:
        result = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ValueError('INVALID_NUMERIC_INPUT') from exc
    if not result.is_finite() or (not signed and result < 0) or (positive and result <= 0):
        raise ValueError('INVALID_NUMERIC_INPUT')
    return result


def _selected_cells(spec, period_id, stage):
    cells = execution_cells(spec, period_id)
    primary = {r['id'] for r in spec['strategies'] if r['stage'] == 'primary'}
    if stage in ('smoke', 'primary'):
        return [c for c in cells if c['strategy_id'] in primary and c['cost_bps'] == 10]
    if stage in ('sensitivity', 'report'):
        extra = []
        for c in cells:
            if c['strategy_id'] in ('W0-N15-Q', 'W3-N15-Q'):
                extra.append(dict(c, execution_delay=1))
            if c['strategy_id'] == 'W0-N15-Q':
                extra.extend(dict(c, strategy_id=f'{variant}-N15-Q', diagnostic=True) for variant in ('D0', 'D2'))
        return cells + extra
    return []


def _calendar(bundle):
    from .calendar_adapter import Session, VerifiedSessionCalendar
    return VerifiedSessionCalendar(
        [Session(date.fromisoformat(r['day']), datetime.fromisoformat(r['open_at']),
                 datetime.fromisoformat(r['close_at'])) for r in bundle['sessions']],
        coverage_start=date.fromisoformat(bundle['coverage_start']),
        coverage_end=date.fromisoformat(bundle['coverage_end']),
        source=bundle['calendar_source'], verified=True)


def _semantic_audit(spec, bundle, period_id):
    """Check the payload contract separately from file/hash integrity."""
    blockers = []
    if not isinstance(bundle, dict):
        return ['MALFORMED_LOCAL_BUNDLE']
    required = ('sessions', 'coverage_start', 'coverage_end', 'calendar_source',
                'companyfacts_by_cik', 'filings', 'membership', 'prices', 'events', 'rates', 'benchmark', 'benchmark_id')
    for key in required:
        if key not in bundle:
            blockers.append(f'MISSING_BUNDLE_{key.upper()}')
    if blockers:
        return blockers
    try:
        p = period_for(spec, period_id)
        start, end = date.fromisoformat(p['start']), date.fromisoformat(p['end'])
        benchmark_id = 'SP500_TR_INDEX' if period_id == 'TARGET_QGV_V2' else 'SPY_TR'
        if bundle['benchmark_id'] != benchmark_id:
            blockers.append('BENCHMARK_IDENTITY_MISMATCH')
        cal = _calendar(bundle)
        if cal.coverage_start >= start or cal.coverage_end < end:
            blockers.append('CALENDAR_PERIOD_OR_SIGNAL_COVERAGE')
        if not bundle['companyfacts_by_cik'] or not bundle['filings'] or not bundle['membership']:
            blockers.append('EMPTY_PIT_UNIVERSE_INPUT')
        if not bundle['prices']:
            blockers.append('EMPTY_PRICES')
        keys = set()
        for row in bundle['prices']:
            key = (row['security_id'], row['date'])
            date.fromisoformat(row['date'])
            if key in keys:
                blockers.append('DUPLICATE_PRICE_KEY')
                break
            keys.add(key)
            if row.get('currency') != 'USD' or row.get('price_basis') != 'RAW' or row.get('shares_basis') != 'RAW':
                blockers.append('UNVERIFIED_PRICE_SHARE_BASIS')
                break
            for field in ('open', 'close'):
                if row.get(field) is not None:
                    _number(row[field], positive=True)
        for name in ('rates', 'benchmark'):
            if not bundle[name]:
                blockers.append(f'EMPTY_{name.upper()}')
        for row in bundle['membership']:
            date.fromisoformat(row['start'])
            if row.get('end'):
                date.fromisoformat(row['end'])
            if not row.get('security_id') or not str(row.get('cik', '')).isdigit():
                blockers.append('INVALID_PERMANENT_IDENTITY')
        benchmark_keys = set()
        for row in bundle['benchmark']:
            date.fromisoformat(row['date'])
            if row['date'] in benchmark_keys:
                blockers.append('DUPLICATE_BENCHMARK_DATE')
            benchmark_keys.add(row['date'])
            _number(row['total_return_index'], positive=True)
            if row.get('open_total_return_index') is not None:
                _number(row['open_total_return_index'], positive=True)
            if row.get('currency') != 'USD':
                blockers.append('BENCHMARK_CURRENCY_UNVERIFIED')
        for row in bundle['rates']:
            date.fromisoformat(row['public_date'])
            _number(row['annual_yield'], signed=True)
    except (KeyError, ValueError, TypeError):
        blockers.append('MALFORMED_LOCAL_BUNDLE')
    return sorted(set(blockers))


def _rate_at(bundle, cal, day):
    """A date-only publication becomes usable the following verified session."""
    days = [s.day for s in cal.sessions]
    current = days.index(day)
    eligible = []
    for row in bundle['rates']:
        published = date.fromisoformat(row['public_date'])
        effective = next((i for i, d in enumerate(days) if d > published), None)
        if effective is not None and effective <= current:
            eligible.append((published, effective, _number(row['annual_yield'], signed=True)))
    if not eligible:
        return None, 6
    published, effective, rate = max(eligible, key=lambda r: r[0])
    conflicts = {value for p, _, value in eligible if p == published}
    if len(conflicts) != 1:
        return None, 6
    return rate, current - effective


def _rate_curve(bundle, cal):
    days = [s.day for s in cal.sessions]
    releases = {}
    for row in bundle['rates']:
        published = date.fromisoformat(row['public_date'])
        releases.setdefault(published, set()).add(_number(row['annual_yield'], signed=True))
    timeline = sorted((published, bisect_right(days, published), rates)
                      for published, rates in releases.items())
    cursor, latest, curve = 0, None, {}
    for index, day in enumerate(days):
        while cursor < len(timeline) and timeline[cursor][1] <= index:
            latest = timeline[cursor]
            cursor += 1
        if latest is None or len(latest[2]) != 1:
            curve[day] = (None, 6)
        else:
            curve[day] = (next(iter(latest[2])), index - latest[1])
    return curve


def _event(row):
    from .ledger import Dividend, Settlement, Split
    kind = row['type']
    common = (row['event_id'], date.fromisoformat(row['effective_date']), row['security_id'])
    if kind == 'SPLIT':
        return Split(*common, _number(row['ratio'], positive=True))
    if kind == 'DIVIDEND':
        return Dividend(*common, _number(row['cash_per_share']), date.fromisoformat(row['pay_date']))
    if kind in ('CASH_MERGER', 'STOCK_MERGER', 'SPINOFF', 'DELISTING'):
        return Settlement(*common, kind,
                          date.fromisoformat(row['settlement_date']) if row.get('settlement_date') else None,
                          _number(row['cash_per_share']) if row.get('cash_per_share') is not None else None,
                          row.get('new_security_id'),
                          _number(row['stock_ratio'], positive=True) if row.get('stock_ratio') is not None else None)
    raise NotImplementedError('UNSUPPORTED_EVENT_TYPE')


def _monthly(points, cal, start, end, initial_value=None):
    from .metrics import MonthlyReturn
    # Calendar coverage beyond the period distinguishes an actual month end
    # from a truncated final observation. Never guess by weekdays.
    month_last = {}
    for session in cal.sessions:
        day = session.day
        month_end = date(day.year, day.month, civil_calendar.monthrange(day.year, day.month)[1])
        if cal.coverage_end >= month_end:
            month_last[(day.year, day.month)] = day
    values = {day: value for day, value in points}
    if initial_value is not None:
        values[start] = initial_value
    boundaries = [start] + sorted({d for d, _ in points if d > start and month_last.get((d.year, d.month)) == d})
    if boundaries[-1] != end:
        boundaries.append(end)
    result = []
    for a, b in zip(boundaries, boundaries[1:]):
        av, bv = values.get(a), values.get(b)
        full = month_last.get((a.year, a.month)) == a and month_last.get((b.year, b.month)) == b
        result.append(MonthlyReturn(a, b, float(bv / av - 1) if av and bv is not None else None, full_month=full))
    return result


def _references(bundle, cal, start, end, initial, cost_bps, rate_curve):
    """Same-period net SPY entry and a separately compounded verified cash path."""
    days = [s.day for s in cal.sessions if start <= s.day <= end]
    benchmark = {date.fromisoformat(row['date']): row for row in bundle['benchmark']}
    entry = benchmark.get(start, {}).get('open_total_return_index')
    entry = _number(entry, positive=True) if entry is not None else None
    rf_value, previous, risk_free = initial, None, []
    net_points, raw_points, blockers = [], [], []
    for day in days:
        if previous is not None:
            rate, stale = rate_curve[previous]
            if rate is None or stale > 5:
                rf_value = None
                blockers.append('RISK_FREE_REFERENCE_UNVERIFIED')
            elif rf_value is not None:
                rf_value *= 1 + rate * Decimal((day - previous).days) / 365
        risk_free.append((day, rf_value))
        close = benchmark.get(day, {}).get('total_return_index')
        if entry is None or close is None:
            raw_value = net_value = None
            blockers.append('BENCHMARK_ENTRY_OR_SESSION_UNVERIFIED')
        else:
            raw_value = initial * _number(close, positive=True) / entry
            net_value = raw_value / (1 + Decimal(str(cost_bps)) / 10000)
        net_points.append((day, net_value))
        raw_points.append((day, raw_value))
        previous = day
    return dict(benchmark=net_points, raw=raw_points, risk_free=risk_free, blockers=sorted(set(blockers)))


def _replay(spec, bundle, period_id, cells, *, smoke=False):
    from . import calendar_adapter as ca, pit_adapter as pit, scoring_adapter as scoring
    from .ledger import Ledger, LedgerError
    from .metrics import NavPoint, exposure_metrics, performance_metrics
    validate_spec(spec)
    cells = [dict(cell, period_id=period_id) for cell in cells]
    blockers = _semantic_audit(spec, bundle, period_id)
    result = dict(spec_id=spec['spec_id'], period_id=period_id, status='BLOCKED_ON_DATA',
                  oos_status='OOS_NOT_ESTABLISHED', blockers=blockers, runs=[],
                  benchmark_label='SP500_TR_INDEX' if period_id == 'TARGET_QGV_V2' else 'SPY_TR')
    if blockers:
        return result
    cal = _calendar(bundle)
    p = period_for(spec, period_id)
    start, end = date.fromisoformat(p['start']), date.fromisoformat(p['end'])
    strategies = {r['id']: r for r in spec['strategies']}
    strategies.update({f'{v}-N15-Q': dict(id=f'{v}-N15-Q', variant=v, n=15, rebalance='QUARTERLY') for v in ('D0', 'D2')})
    schedules = {mode: ca.rebalance_schedule(cal, start, end, rebalance=mode)
                 for mode in {strategies[c['strategy_id']]['rebalance'] for c in cells}}
    if not schedules or any(not rows for rows in schedules.values()):
        result['blockers'] = ['NO_VERIFIED_REBALANCE_IN_PERIOD']
        return result
    if smoke:
        # The first chronological rebalance is fixed before inspecting scores.
        end = min(rows[0].execution_day for rows in schedules.values())
        schedules = {mode: rows[:1] for mode, rows in schedules.items()}
    price_days = {}
    for row in bundle['prices']:
        price_days.setdefault(date.fromisoformat(row['date']), {})[row['security_id']] = row
    try:
        events = [_event(row) for row in bundle['events']]
    except NotImplementedError:
        result.update(status='BLOCKED_ON_IMPLEMENTATION', blockers=['UNSUPPORTED_EVENT_TYPE'])
        return result
    session_days = {s.day for s in cal.sessions}
    earliest_signal = min(rows[0].signal_day for rows in schedules.values())
    if any(earliest_signal <= e.effective_date <= end and e.effective_date not in session_days for e in events):
        result.update(status='BLOCKED_ON_IMPLEMENTATION', blockers=['NON_SESSION_CORPORATE_ACTION'])
        return result
    rate_curve = _rate_curve(bundle, cal)
    score_cache = {}
    for rows in schedules.values():
        for rebalance in rows:
            signal = rebalance.signal_day
            if signal in score_cache:
                continue
            rows_asof = pit.build_pit_rows(bundle['companyfacts_by_cik'], bundle['filings'], bundle['membership'],
                                         bundle['prices'], signal, cal)
            quotes = pit.quotes_as_of(bundle['prices'], signal, calendar=cal)
            scores = scoring.score_variants(rows_asof, quotes, include_diagnostics=True)
            score_cache[signal] = (rows_asof, scores)
    initial = _number(spec['portfolio']['initial_capital'], positive=True)
    reference_cache = {}
    for cell in cells:
        strategy = strategies[cell['strategy_id']]
        schedule = schedules[strategy['rebalance']]
        baseline = schedule[0].signal_day
        days = [s.day for s in cal.sessions if baseline <= s.day <= end]
        regular = {r.signal_day: r for r in schedule}
        ledger = Ledger(initial, cost_bps=cell['cost_bps'])
        run = dict(cell=cell, status='COMPLETE', blockers=[], decisions=[], nav=[], fills=[],
                   metrics=None, monthly=[], benchmark=[], risk_free=[], coverage=[], exposure=[])
        current_rows, current_scores = {}, {}
        ready_day = None
        failed_nav = False
        previous = baseline
        for day in days:
            if day > start:
                rate, stale = rate_curve[previous]
                try:
                    ledger.accrue_cash_interest(previous, day, rate, stale_sessions=stale)
                except LedgerError:
                    failed_nav = True
                    run['blockers'].append('CASH_RATE_UNVERIFIED')
            for event in events:
                if event.effective_date == day:
                    ledger.apply_event(event, day)
            ledger.settle_events(day)
            prices = price_days.get(day, {})
            opens = {sid: row.get('open') for sid, row in prices.items()}
            closes = {sid: row.get('close') for sid, row in prices.items()}
            if ready_day is not None and day >= ready_day and not failed_nav:
                ledger.execute_open(day, opens, suspended=[sid for sid, row in prices.items() if row.get('suspended') is True])
            snapshot = ledger.nav(day, closes)
            encoded = _jsonable(snapshot)
            if failed_nav:
                encoded.update(nav=None, status='INCOMPLETE_NAV', reasons=['CASH_RATE_UNVERIFIED'])
            run['nav'].append(encoded)
            if day in regular and not failed_nav:
                rows_asof, scores = score_cache[day]
                rebalance = regular[day]
                variant = strategy['variant']
                current_rows, current_scores = rows_asof, scores['scores'][variant]
                eligible = scores['panels'][cell['panel']][variant]
                selected = scoring.select_top(scores['scores'][variant], rows_asof, strategy['n'], eligible_ids=eligible)
                ids = [r['security_id'] for r in selected]
                try:
                    orders = ledger.rebalance(day, ids, strategy['n'], closes)
                except LedgerError:
                    run['blockers'].append('INCOMPLETE_SIGNAL_NAV')
                    run['status'] = 'INCOMPLETE_NAV'
                    break
                opportunity = next(i for i, s in enumerate(cal.sessions) if s.day == rebalance.execution_day)
                opportunity += cell.get('execution_delay', 0)
                if opportunity >= len(cal.sessions):
                    run['blockers'].append('EXECUTION_DELAY_CALENDAR_COVERAGE')
                    run['status'] = 'BLOCKED_ON_DATA'
                    break
                ready_day = cal.sessions[opportunity].day
                run['decisions'].append(dict(signal_day=str(day), execution_day=str(ready_day), selected=ids,
                                             quantities=_jsonable(orders), candidate_count=len(rows_asof),
                                             common_candidate_count=len(scores['common_ids']),
                                             selected_details=selected))
                run['coverage'].append(dict(signal_day=str(day), **_jsonable(scores['summary']),
                                             eligible_count=len(eligible), selected_count=len(ids),
                                             slots=strategy['n'], empty_slots=strategy['n'] - len(ids),
                                             flags={sid: row.get('flags', []) for sid, row in rows_asof.items()},
                                             score_flags={sid: row.get('flags', []) for sid, row in current_scores.items()}))
            weights = {}
            if snapshot.nav and not failed_nav:
                weights = {sid: float(quantity * _number(closes[sid], positive=True) / snapshot.nav)
                           for sid, quantity in ledger.holdings.items() if closes.get(sid) is not None}
            if encoded['nav'] is None:
                run['exposure'].append(dict(session=str(day), status='INCOMPLETE_NAV', metrics=None))
            else:
                exposure = exposure_metrics(weights, {sid: row.get('industry_group') or 'UNKNOWN'
                                                       for sid, row in current_rows.items()})
                exposure['cash_weight'] = float(ledger.cash / snapshot.nav) if snapshot.nav else None
                exposure['receivable_weight'] = float(snapshot.receivables / snapshot.nav) if snapshot.nav else None
                type_weights = {}
                for sid, weight in weights.items():
                    for label in current_scores.get(sid, {}).get('selected_types', []):
                        type_weights[label] = type_weights.get(label, 0) + weight
                exposure['type_overlap_weights'] = type_weights
                run['exposure'].append(dict(session=str(day), status='COMPLETE', metrics=exposure,
                                             holdings=_jsonable(ledger.holdings)))
            previous = day
        run['fills'] = _jsonable(ledger.fills)
        run['unfilled'] = _jsonable(ledger.unfilled)
        run['cancellations'] = _jsonable(ledger.cancellations)
        if any(r['nav'] is None for r in run['nav']):
            run['status'] = 'INCOMPLETE_NAV'
            run['blockers'].append('INCOMPLETE_CURRENT_NAV')
        points = [(date.fromisoformat(r['session']), Decimal(r['nav']) if r['nav'] is not None else None) for r in run['nav']]
        actual_points = [(d, value) for d, value in points if d >= start]
        monthly = _monthly(actual_points, cal, start, end, initial_value=initial)
        run['monthly'] = _jsonable(monthly)
        if cell['cost_bps'] not in reference_cache:
            reference_cache[cell['cost_bps']] = _references(bundle, cal, start, end, initial, cell['cost_bps'], rate_curve)
        references = reference_cache[cell['cost_bps']]
        benchmark_monthly = _monthly(references['benchmark'], cal, start, end, initial_value=initial)
        risk_free_monthly = _monthly(references['risk_free'], cal, start, end, initial_value=initial)
        run['benchmark'] = _jsonable(benchmark_monthly)
        run['risk_free'] = _jsonable(risk_free_monthly)
        run['benchmark_nav'] = [dict(session=str(d), nav=float(v) if v is not None else None,
                                     raw_reference_nav=float(raw) if raw is not None else None)
                                for (d, v), (_, raw) in zip(references['benchmark'], references['raw'])]
        run['risk_free_nav'] = [dict(session=str(d), nav=float(v) if v is not None else None)
                               for d, v in references['risk_free']]
        if references['blockers']:
            run['blockers'].extend(references['blockers'])
            if run['status'] == 'COMPLETE':
                run['status'] = 'INCOMPLETE_REFERENCE'
        expected = [d for d in days if d >= start]
        # Keep the pre-entry baseline in private audit data; performance API uses
        # the actual first-fill date and capital to include entry costs.
        actual = [NavPoint(d, float(v) if v is not None else None) for d, v in points if d >= start]
        run['metrics'] = _jsonable(performance_metrics(actual, expected_sessions=expected,
                                                       initial_capital=float(initial), started_at=start,
                                                       monthly_returns=monthly,
                                                       risk_free_monthly=risk_free_monthly,
                                                       benchmark_monthly=benchmark_monthly))
        result['runs'].append(run)
    result['blockers'] = sorted({reason for run in result['runs'] for reason in run['blockers']})
    if any(run['status'] != 'COMPLETE' for run in result['runs']):
        result['status'] = 'INCOMPLETE_REPLAY'
    else:
        result['status'] = 'SMOKE_COMPLETE' if smoke else 'REPLAY_COMPLETE'
    return result


def replay_bundle(spec, bundle, period_id, cells=None):
    """Replay an explicitly synthetic in-memory bundle; never a CLI bypass."""
    if bundle.get('synthetic') is not True:
        raise ValueError('PURE_REPLAY_SYNTHETIC_ONLY')
    return _replay(spec, bundle, period_id, cells if cells is not None else _selected_cells(spec, period_id, 'primary'))


def _contract(spec, manifest, stage, period_id):
    code = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        code.update(path.name.encode())
        code.update(path.read_bytes())
    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    contract = dict(stage=stage, period_id=period_id, config_sha256=spec_hash,
                    research_code_sha256=code.hexdigest(), source_sha=spec['source']['scoring_source_sha'],
                    manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest())
    contract['contract_sha256'] = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    contract['run_id'] = contract['contract_sha256'][:24]
    return contract


def _exclusive_write(path, payload):
    """Never follow a leaf symlink or overwrite an existing private artifact."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _private_read(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as handle:
        return handle.read()


def _safe_summary(result, detailed, stage, *, written=0, cached=False):
    status = detailed['status']
    if status in ('REPLAY_COMPLETE', 'SMOKE_COMPLETE', 'REPORT_COMPLETE'):
        status = {'smoke': 'SMOKE_PASS', 'primary': 'PRIMARY_DONE', 'sensitivity': 'SENSITIVITY_DONE',
                  'report': 'REPORT_DONE'}[stage]
    runs = detailed.get('runs', [])
    result.update(status=status, blockers=detailed.get('blockers', []),
                  completed_cells=sum(r['status'] == 'COMPLETE' for r in runs),
                  requested_cells=len(runs), private_artifacts_written=written, cached=cached)
    for row in result['strategies']:
        strategy_runs = [r for r in runs if r['cell']['strategy_id'] == row['id']]
        if strategy_runs:
            row['status'] = 'PRIVATE_REPLAY_RECORDED' if all(r['status'] == 'COMPLETE' for r in strategy_runs) else 'INCOMPLETE_PRIVATE_REPLAY'
    return result


def _csv_payload(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _report_artifacts(spec, detailed):
    from .reporting import build_report, render_markdown, render_svg
    report = build_report(spec, detailed)
    detailed['report'] = report
    detailed['status'] = report.get('status', 'REPORT_PARTIAL')
    detailed['blockers'] = sorted(set(detailed['blockers'] + report.get('blockers', [])))
    rows = []
    metric_rows = []
    for run in detailed['runs']:
        cell = run['cell']
        keys = dict(period_id=cell.get('period_id'), strategy_id=cell['strategy_id'], panel=cell['panel'],
                    cost_bps=cell['cost_bps'], execution_delay=cell.get('execution_delay', 0))
        rows.extend(dict(keys, **row) for row in run['nav'])
        for name, metric in (run.get('metrics') or {}).items():
            if isinstance(metric, dict) and 'value' in metric:
                metric_rows.append(dict(keys, metric=name, value=metric['value'], reason=metric.get('reason')))
    fields = ['period_id', 'strategy_id', 'panel', 'cost_bps', 'execution_delay']
    return {'report.json': (json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode(),
            'report.md': render_markdown(report).encode(), 'nav-drawdown.svg': render_svg(detailed).encode(),
            'daily-nav.csv': _csv_payload(rows, fields + ['session', 'nav', 'status', 'cash', 'receivables']),
            'comparisons.csv': _csv_payload(metric_rows, fields + ['metric', 'value', 'reason'])}


def run_stage(spec, stage, period_id, manifest=None, output=None):
    """Run an authorized local stage and return privacy-safe status metadata."""
    if stage not in STAGES:
        raise ValueError('UNKNOWN_STAGE')
    validate_spec(spec)
    period = period_for(spec, period_id)
    # Check explicit protected access scope BEFORE audit_inputs hashes any file.
    if manifest and manifest.get('protection_status') == 'AUTHORIZED_PROTECTED':
        scope = manifest.get('protected_scope', {})
        if not scope.get('receipt') or scope.get('start', '9999') > period['start'] or scope.get('end', '') < period['end']:
            result = audit_inputs(spec, None, period_id)
            result.update(status='BLOCKED_ON_PERMISSION', blockers=['PROTECTED_PERIOD_SCOPE_UNVERIFIED'], stage=stage)
            return result
    result = audit_inputs(spec, manifest, period_id)
    result['stage'] = stage
    if result['status'] != 'INPUT_INTEGRITY_PASS':
        return result
    descriptor = manifest.get('bundle', {})
    try:
        raw = Path(descriptor['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
            raise ValueError('BUNDLE_HASH_MISMATCH')
        bundle = json.loads(raw)
    except (KeyError, ValueError, OSError, TypeError):
        result.update(status='BLOCKED_ON_DATA', blockers=['BUNDLE_INTEGRITY_OR_FORMAT'])
        return result
    if not isinstance(bundle, dict) or bundle.get('source_hashes') != {name: row['sha256'] for name, row in manifest['resources'].items()}:
        result.update(status='BLOCKED_ON_DATA', blockers=['BUNDLE_SOURCE_HASH_MISMATCH'])
        return result
    blockers = _semantic_audit(spec, bundle, period_id)
    if blockers:
        result.update(status='BLOCKED_ON_DATA', blockers=blockers)
        return result
    result.update(status='SEMANTIC_INPUT_CONTRACT_PASS', blockers=[])
    if stage == 'audit':
        return result
    try:
        destination = Path(output).resolve() if output else None
        private_root = Path(manifest['private_output_root']).resolve()
        if destination is None or not destination.is_relative_to(private_root) or destination == private_root:
            raise ValueError('UNVERIFIED_PRIVATE_OUTPUT')
        public_checkout = Path(__file__).resolve().parents[5]
        if private_root.is_relative_to(public_checkout) or destination.is_relative_to(public_checkout):
            raise ValueError('PUBLIC_CHECKOUT_NOT_PRIVATE')
    except (KeyError, ValueError, OSError, TypeError):
        result.update(status='BLOCKED_ON_PERMISSION', blockers=['VERIFIED_PRIVATE_OUTPUT_REQUIRED'])
        return result
    contract = _contract(spec, manifest, stage, period_id)
    artifact = destination / f'{stage}-private.json'
    if artifact.exists() or artifact.is_symlink():
        try:
            cached = json.loads(_private_read(artifact))
            if cached.get('provenance', {}).get('contract_sha256') != contract['contract_sha256']:
                raise ValueError('PRIVATE_OUTPUT_COLLISION')
            for name, digest in cached.get('artifact_sha256', {}).items():
                if Path(name).name != name or hashlib.sha256(_private_read(destination / name)).hexdigest() != digest:
                    raise ValueError('PRIVATE_ARTIFACT_CHANGED')
            return _safe_summary(result, cached, stage, cached=True)
        except (ValueError, OSError, KeyError, TypeError):
            result.update(status='BLOCKED_ON_PERMISSION', blockers=['PRIVATE_OUTPUT_COLLISION_NEW_RUN_REQUIRED'])
            return result
    try:
        detailed = _replay(spec, bundle, period_id, _selected_cells(spec, period_id, stage), smoke=stage == 'smoke')
    except (ValueError, KeyError, TypeError, NotImplementedError):
        result.update(status='BLOCKED_ON_IMPLEMENTATION', blockers=['UNSUPPORTED_OR_INCOMPLETE_REPLAY_INPUT'])
        return result
    detailed['provenance'] = dict(contract, executed_at=datetime.now(timezone.utc).isoformat(),
                                   source_hashes=bundle['source_hashes'])
    artifacts = _report_artifacts(spec, detailed) if stage == 'report' else {}
    detailed['artifact_sha256'] = {name: hashlib.sha256(payload).hexdigest() for name, payload in artifacts.items()}
    try:
        destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.chmod(0o700)
        for name, payload in artifacts.items():
            _exclusive_write(destination / name, payload)
        _exclusive_write(artifact, (json.dumps(_jsonable(detailed), ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
    except OSError:
        result.update(status='BLOCKED_ON_PERMISSION', blockers=['PRIVATE_OUTPUT_COLLISION_OR_WRITE_FAILURE'])
        return result
    return _safe_summary(result, detailed, stage, written=1 + len(artifacts))
