"""Five research measures over retained normalized raw bars; no data collection or ranking.

Primary economic values and raw-series arithmetic are separate. Scope/identity/action
evidence is supplied by the caller and retained, never inferred from a ticker or price.
"""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re

from . import liquidity, schedule
from .adapters.alpaca_bars import session_date

SETTINGS_BYTES = Path(__file__).with_name('technical_leaderboard_v1.json').read_bytes()
SETTINGS = json.loads(SETTINGS_BYTES)
METRIC_IDS = ('momentum_3m', 'momentum_6m', 'momentum_12m', 'volatility_6m', 'dollar_volume_6m')


def settings_for_basis(basis):
    if basis=='RAW':return SETTINGS,SETTINGS_BYTES
    if basis!='SPLIT_ADJUSTED':raise ValueError('UNSUPPORTED_PRICE_BASIS')
    config={**SETTINGS,'settings_version':'technical-leaderboard/split-adjusted-2026-11-05.1',
            'split_policy':'CONFIRMED_SPLITS_ONLY_WITH_FULL_WINDOW_ACTION_COVERAGE'}
    return config,json.dumps(config,sort_keys=True,separators=(',',':')).encode()


def number(value):
    if value is None or isinstance(value, (bool, float)):
        return None
    try:
        n = Decimal(value)
        return n if n.is_finite() else None
    except (ValueError, TypeError, InvalidOperation):
        return None


def boundary(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    return date(year, month + 1, min(day.day, monthrange(year, month + 1)[1]))


def sessions(start, end):
    days = []
    while start <= end:
        if schedule.is_session(start):
            days.append(start.isoformat())
        start += timedelta(days=1)
    return days


def _identity(evidence):
    return (evidence.get('identity_status') in ('CONFIRMED', 'DOCUMENT_RECONSTRUCTED')
            and bool(evidence.get('identity_reference')))


def _economic_reasons(evidence, anchor, signal):
    reasons = []
    if not _identity(evidence):
        reasons.append('IDENTITY_UNCONFIRMED')
    prefix='adjustment_' if evidence.get('price_basis')=='SPLIT_ADJUSTED' else 'no_split_'
    if prefix=='adjustment_' and evidence.get('adjustment_method')!='CONFIRMED_SPLITS_ONLY':
        reasons.append('ACTION_BASIS_UNCONFIRMED')
    if not (evidence.get(prefix+'reference') and evidence.get(prefix+'start') and evidence.get(prefix+'end')
            and date.fromisoformat(evidence[prefix+'start']) <= date.fromisoformat(anchor)
            and date.fromisoformat(evidence[prefix+'end']) >= date.fromisoformat(signal)):
        reasons.append('ACTION_BASIS_UNCONFIRMED')
    return reasons


def _result(raw, reasons, *, unit, start, end, anchor, observed, expected, observation_unit):
    value = None if reasons or raw is None else str(raw)
    return dict(value=value, raw_value=None if raw is None else str(raw), unit=unit, null_reasons=reasons,
                gt_zero=None if value is None else Decimal(value) > 0,
                raw_gt_zero=None if raw is None else raw > 0,
                window_start=start, window_end=end, anchor_day=anchor,
                observed_days=observed, expected_days=expected, observation_unit=observation_unit)


def measure(rows, *, signal_day, symbol, series_id, evidence, liquidity_rows=None):
    """One original request series. Never merge aliases or infer a permanent security ID.

    Decimal strings, UTC daily-bar timestamps and source hashes follow the shared
    Alpaca normalizer. Reject conflicting duplicates; future bars never enter S.
    Evidence may document identity without a permanent ID: raw/economic values then
    remain useful, while the security-group ranking and QGV join stay unavailable.
    """
    if evidence.get('price_basis','RAW') not in ('RAW','SPLIT_ADJUSTED'):raise ValueError('UNSUPPORTED_PRICE_BASIS')
    if evidence.get('price_basis')=='SPLIT_ADJUSTED' and liquidity_rows is None:raise ValueError('RAW_LIQUIDITY_ROWS_REQUIRED')
    end = date.fromisoformat(signal_day)
    if not schedule.is_session(end):
        raise ValueError('SIGNAL_DAY_NOT_A_SESSION')
    anchors = {}
    for months in SETTINGS['momentum_months']:
        b = boundary(end, months)
        anchors[months] = b if schedule.is_session(b) else schedule.previous_session(b)
    def validate_source(row, day, basis):
        if row.get('returned_symbol') != symbol or row.get('requested_symbol', symbol) != symbol:
            raise ValueError('SYMBOL_MISMATCH')
        if row.get('price_basis') != basis or row.get('asof', '-') != '-':
            raise ValueError('RAW_DIRECT_SYMBOL_BASIS_REQUIRED')
        actual, problem = session_date(row.get('source_timestamp'))
        if problem or actual != day or not schedule.is_session(day):
            raise ValueError(problem or 'SESSION_DATE_MISMATCH')
        if not re.fullmatch('[0-9a-f]{64}', row.get('source_sha256', '')):
            raise ValueError('SOURCE_HASH_REQUIRED')

    by_day = {}
    for row in rows:
        day = date.fromisoformat(row['date'])
        if day < anchors[12] or day > end:
            continue
        validate_source(row,day,evidence.get('price_basis','RAW'))
        key = day.isoformat()
        fields = ('close', 'vwap', 'volume', 'quality_reasons')
        if key in by_day and any(by_day[key].get(k) != row.get(k) for k in fields):
            raise ValueError('CONFLICTING_DAY')
        by_day[key] = row
    prices = {day: number(r.get('close')) for day, r in by_day.items()}
    # A missing volume/open/high/low is not a missing close. Keep metrics independent;
    # still reject close defects, OHLC inconsistency and unknown whole-row quality failures.
    irrelevant_to_close = ('VOLUME_', 'TRADE_COUNT_', 'VWAP_', 'OPEN_', 'HIGH_', 'LOW_')
    prices = {day: p for day, p in prices.items()
              if p is not None and p > 0 and not any(
                  not q.startswith(irrelevant_to_close) for q in by_day[day].get('quality_reasons', []))}
    metrics = {}
    with localcontext() as ctx:
        ctx.prec = SETTINGS['price_decimal_precision']
        for months, anchor in anchors.items():
            wanted = sessions(anchor, end)
            observed = sum(d in prices for d in wanted)
            raw = None
            reasons = _economic_reasons(evidence, anchor.isoformat(), signal_day)
            if observed != len(wanted):
                reasons.insert(0, 'PRICE_WINDOW_INCOMPLETE_OR_INVALID')
            else:
                first, last = prices[wanted[0]], prices[wanted[-1]]
                raw = (last - first) / first * 100
            metrics[f'momentum_{months}m'] = _result(raw, reasons, unit='PERCENT',
                start=boundary(end, months).isoformat(), end=signal_day, anchor=anchor.isoformat(),
                observed=observed, expected=len(wanted), observation_unit='CLOSES')
        start, anchor = boundary(end, 6), anchors[6]
        days = sessions(start + timedelta(days=1), end)
        price_days = [anchor.isoformat()] + days
        returns = [(prices[d] - prices[p]) / prices[p]
                   for p, d in zip(price_days, days) if p in prices and d in prices]
        raw = None
        reasons = _economic_reasons(evidence, anchor.isoformat(), signal_day)
        if len(returns) != len(days):
            reasons.insert(0, 'RETURN_WINDOW_INCOMPLETE_OR_INVALID')
        elif len(returns) < SETTINGS['minimum_returns']:
            reasons.insert(0, 'INSUFFICIENT_RETURNS')
        else:
            mean = sum(returns) / len(returns)
            raw = (sum((r-mean)**2 for r in returns) / (len(returns)-SETTINGS['volatility_ddof'])).sqrt() * 100
        metrics['volatility_6m'] = _result(raw, reasons, unit='PERCENT_PER_DAY', start=start.isoformat(),
            end=signal_day, anchor=anchor.isoformat(), observed=len(returns), expected=len(days), observation_unit='DAILY_RETURNS')
        metrics['volatility_6m'].update(observed_price_days=sum(d in prices for d in price_days),
                                      expected_price_days=len(price_days), ddof=1, annualized=False)
    if liquidity_rows is not None:
        liquidity_days={}
        for row in liquidity_rows:
            day=date.fromisoformat(row['date'])
            if day<anchors[12] or day>end:continue
            validate_source(row,day,'RAW')
            key=day.isoformat()
            if key in liquidity_days and any(liquidity_days[key].get(k)!=row.get(k) for k in ('close','vwap','volume','quality_reasons')):
                raise ValueError('CONFLICTING_DAY')
            liquidity_days[key]=row
        liquidity_rows=list(liquidity_days.values())
    with localcontext() as ctx:
        ctx.prec = SETTINGS['liquidity_decimal_precision']
        liquid = liquidity.summarize(list(by_day.values()) if liquidity_rows is None else liquidity_rows, signal_day=signal_day, symbol=symbol)
    reasons = []
    if not _identity(evidence):
        reasons.append('IDENTITY_UNCONFIRMED')
    if evidence.get('currency') != 'USD' or not evidence.get('currency_reference'):
        reasons.append('USD_UNCONFIRMED')
    if evidence.get('trade_scope_status') != 'CONFIRMED_MATCH' or not evidence.get('trade_scope_reference'):
        reasons.append('TRADE_SCOPE_UNCONFIRMED')
    vol = liquid['vwap_volume']
    if vol['mean_complete'] is None:
        reasons.insert(0, 'VOLUME_WINDOW_INCOMPLETE_OR_INVALID')
    metrics['dollar_volume_6m'] = _result(number(vol['mean_complete']), reasons, unit='USD_PER_TRADING_DAY',
        start=liquid['window_start_exclusive'], end=signal_day, anchor=None,
        observed=vol['valid_days'], expected=liquid['expected_sessions'], observation_unit='TRADING_DAYS')
    metrics['dollar_volume_6m'].update(mean_observed=vol['mean_observed'], close_volume_proxy=liquid['close_volume_proxy'],
        raw_unit='SOURCE_QUOTE_CURRENCY_PER_TRADING_DAY', trade_scope_status=evidence.get('trade_scope_status', 'UNCONFIRMED'),
        approximation='PROVIDER_ROUNDED_AGGREGATE_NOT_EXACT_TRADE_SUM')
    config,config_bytes=settings_for_basis(evidence.get('price_basis','RAW'))
    sid = evidence.get('security_id')
    return dict(schema='technical-measures/1', signal_day=signal_day, series_id=series_id, symbol=symbol, security_id=sid,
                identity_status=evidence.get('identity_status', 'UNKNOWN'), evidence=dict(evidence),
                settings_version=config['settings_version'], settings_sha256=hashlib.sha256(config_bytes).hexdigest(),
                qgv_join_key=[signal_day, sid] if sid and _identity(evidence) else None, metrics=metrics)
