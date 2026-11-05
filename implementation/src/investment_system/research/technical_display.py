"""Offline display diagnostics over retained normalized bars, reusing approved kernels.

No provider requests, operational gate changes, pattern claims or rankings. Raw
arithmetic and evidence-qualified values are separate, as in technical-measures/1.
"""
from datetime import date
import math
import re
from types import SimpleNamespace

from investment_system.technical import research_display as display, patterns
from .exp_deciles import technical_measures as tm

SCHEMA = 'technical-offline-display/1'
PRICE_IDS = ('SMA_5','SMA_20','SMA_60','SMA_120','EMA_20','RSI_14',
             'MACD_12_26','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9',
             'BOLL_MIDDLE_20','BOLL_UPPER_20_2','BOLL_LOWER_20_2','ATR_14')
_INITIALIZATION = {
    'EMA_20': (20, 'FIRST_20_CLOSE_SMA_THEN_EMA'),
    'RSI_14': (15, 'FIRST_14_CHANGES_MEAN_THEN_WILDER'),
    'MACD_12_26': (26, 'FULL_INPUT_SMA_SEEDED_EMA_12_MINUS_26'),
    'MACD_SIGNAL_9': (34, 'FIRST_9_VALID_MACD_MEAN_THEN_EMA'),
    'MACD_HISTOGRAM_12_26_9': (34, 'MACD_MINUS_SIGNAL'),
    'ATR_14': (15, 'FIRST_14_TRUE_RANGES_MEAN_THEN_WILDER_RESET_AFTER_OHLC_GAP'),
}


def describe_readiness(result):
    """Project existing measures for readers, without recomputing or relaxing gates.

    Minimum sessions describe GSQ-015's first value, not a replacement seed window.
    Observation date is never treated as source availability or freshness evidence.
    """
    evidence = result['evidence']
    metrics = {}
    for name, metric in result['metrics'].items():
        reasons = metric['null_reasons']
        if name.startswith('SMA_'):
            minimum, method = int(name.split('_')[1]), 'ROLLING_CLOSE_MEAN'
        elif name.startswith('BOLL_'):
            minimum = 20
            method = 'ROLLING_CLOSE_MEAN' if name == 'BOLL_MIDDLE_20' else 'ROLLING_20_CLOSE_POPULATION_STDDEV'
        else:
            minimum, method = _INITIALIZATION[name]
        raw_missing = metric['raw_value'] is None
        invalid = [reason for reason in reasons if reason in (
            'PRICE_WINDOW_INCOMPLETE', 'RAW_PRICE_BASIS_REQUIRED', 'CLOSE_INVALID')]
        warmup_unverifiable = invalid or any(reason in reasons for reason in (
            'OHLC_MISSING', 'OHLC_BASIS_UNCONFIRMED', 'CALCULATION_ERROR'))
        warmup = ('NOT_EVALUATED' if warmup_unverifiable else 'INSUFFICIENT' if 'WARMUP' in reasons
                  or metric['observation_days'] < minimum else 'READY')
        metrics[name] = dict(
            state='VALUE' if metric['value'] is not None else 'DIAGNOSTIC' if not raw_missing else 'NOT_COMPUTED',
            initialization=dict(method=method, policy='GSQ015_FULL_RETAINED_HISTORY' if name in _INITIALIZATION else 'GSQ015_ROLLING_WINDOW',
                                input_start=result['input_start']),
            warmup=dict(minimum_sessions=minimum, observed_sessions=metric['observation_days'], state=warmup),
            continuity=dict(state='INCOMPLETE' if 'PRICE_WINDOW_INCOMPLETE' in reasons else
                            'INVALID' if invalid else 'COMPLETE', reasons=invalid),
            adjustment=dict(price_basis=result['price_basis'],
                            state='UNCONFIRMED' if 'ACTION_BASIS_UNCONFIRMED' in reasons else 'DOCUMENTED_NO_SPLIT',
                            required_start=metric['window_start'], required_end=metric['window_end'],
                            evidence_start=evidence.get('no_split_start'), evidence_end=evidence.get('no_split_end')),
            identity=dict(state=evidence.get('identity_status', 'UNKNOWN'),
                          reference_present=bool(evidence.get('identity_reference')),
                          fixed_security_id_state='PRESENT_NOT_RANKED' if evidence.get('security_id') else 'MISSING_RANKING_BLOCKED'),
            block_reasons=list(reasons))
    return dict(schema='technical-display-readiness/1', as_of=result['signal_day'],
                value_scope='PRIVATE_RESEARCH_DOCUMENT_RECONSTRUCTION',
                availability_status='NOT_VERIFIED', source_available_at=None,
                availability_reason='HISTORICAL_SOURCE_AVAILABILITY_NOT_VERIFIED',
                stale_status='UNKNOWN', stale_reason='UPDATE_SCHEDULE_NOT_CONNECTED', metrics=metrics)


def _number(value, *, zero=False):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) and (n >= 0 if zero else n > 0) else None
    except (ValueError, TypeError, OverflowError):
        return None


def measure_display(rows, *, signal_day, series_id, symbol, evidence, source_kind=None, include_sma240=False):
    """Use all retained sessions through S, with no gap skipping or basis repair."""
    if source_kind != 'NORMALIZED_PROVIDER_DAILY_BARS':
        raise ValueError('DAILY_BAR_SOURCE_REQUIRED')
    end = date.fromisoformat(signal_day)
    if not tm.schedule.is_session(end):
        raise ValueError('SIGNAL_DAY_NOT_A_SESSION')
    if not isinstance(symbol, str) or not symbol:
        raise ValueError('SYMBOL_REQUIRED')
    if type(include_sma240) is not bool:
        raise ValueError('INVALID_DISPLAY_CONFIG')
    dates = [r['date'] for r in rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError('UNSORTED_OR_DUPLICATE_SESSION')
    eligible = [r for r in rows if date.fromisoformat(r['date']) <= end]
    for row in eligible:
        if row.get('returned_symbol') != symbol or row.get('requested_symbol', symbol) != symbol:
            raise ValueError('SYMBOL_MISMATCH')
        if row.get('price_basis') != 'RAW' or row.get('asof', '-') != '-':
            raise ValueError('RAW_DIRECT_SYMBOL_BASIS_REQUIRED')
        actual, problem = tm.session_date(row.get('source_timestamp'))
        if problem or actual != date.fromisoformat(row['date']) or not tm.schedule.is_session(actual):
            raise ValueError(problem or 'SESSION_DATE_MISMATCH')
        if not isinstance(row.get('source_sha256'), str) or not re.fullmatch('[0-9a-f]{64}', row['source_sha256']):
            raise ValueError('SOURCE_HASH_REQUIRED')
    start = eligible[0]['date'] if eligible else signal_day
    expected = tm.sessions(date.fromisoformat(start), end)
    close_reasons = []
    if [r['date'] for r in eligible] != expected or not eligible:
        close_reasons.append('PRICE_WINDOW_INCOMPLETE')
    if any(r.get('price_basis') != 'RAW' for r in eligible):
        close_reasons.append('RAW_PRICE_BASIS_REQUIRED')
    prices = [_number(r.get('close')) for r in eligible]
    irrelevant = ('VOLUME_','TRADE_COUNT_','VWAP_','OPEN_','HIGH_','LOW_')
    if any(p is None or any(not q.startswith(irrelevant) for q in r.get('quality_reasons', []))
           for p,r in zip(prices,eligible)):
        close_reasons.append('CLOSE_INVALID')
    def economic_for(window_start):
        reasons = tm._economic_reasons(evidence, window_start, signal_day)
        if not evidence.get('currency') or not evidence.get('currency_reference'):
            reasons.append('CURRENCY_UNCONFIRMED')
        return reasons
    ids = PRICE_IDS + (('SMA_240',) if include_sma240 else ())
    metrics = {}

    def add(name, values, reasons):
        raw = values[-1] if values else None
        missing = list(close_reasons)
        if reasons and reasons[-1]:
            missing.append(reasons[-1])
        n = int(name.split('_')[1]) if name.startswith('SMA_') else 20 if name.startswith('BOLL_') else None
        window = eligible[-n:] if n else eligible
        window_start = window[0]['date'] if window else start
        missing.extend(economic_for(window_start))
        metrics[name] = dict(raw_value=raw, value=None if missing else raw,
            unit='PERCENT' if name == 'RSI_14' else 'SOURCE_CURRENCY_PER_SHARE',
            null_reasons=list(dict.fromkeys(missing)), observation_days=sum(_number(r.get('close')) is not None for r in window),
            expected_days=n if n else len(expected), window_start=window_start, window_end=signal_day)
    if close_reasons:
        for name in ids:
            add(name, [], [])
    else:
        for n in (5,20,60,120)+((240,) if include_sma240 else ()):
            add('SMA_'+str(n), *display._sma(prices,n))
        add('EMA_20',*display._ema(prices,20));add('RSI_14',*display._rsi(prices))
        fast,fr=display._ema(prices,12);slow,sr=display._ema(prices,26)
        line=[display._finite(lambda:a-b) if a is not None and b is not None else None for a,b in zip(fast,slow)]
        lr=[None if v is not None else 'CALCULATION_ERROR' if a is not None and b is not None else 'WARMUP' for v,a,b in zip(line,fast,slow)]
        signal,signal_reasons=display._ema(line,9)
        hist=[display._finite(lambda:a-b) if a is not None and b is not None else None for a,b in zip(line,signal)]
        hr=[None if v is not None else 'CALCULATION_ERROR' if a is not None and b is not None else 'WARMUP' for v,a,b in zip(hist,line,signal)]
        add('MACD_12_26',line,lr);add('MACD_SIGNAL_9',signal,signal_reasons);add('MACD_HISTOGRAM_12_26_9',hist,hr)
        middle,mr,upper,lower,br=display._bollinger(prices)
        add('BOLL_MIDDLE_20',middle,mr);add('BOLL_UPPER_20_2',upper,br);add('BOLL_LOWER_20_2',lower,br)
        bars=[]
        for r,p in zip(eligible,prices):
            o,h,l=(_number(r.get(k)) for k in ('open','high','low'))
            valid=all(x is not None for x in (o,h,l)) and l<=min(o,p)<=max(o,p)<=h
            bars.append(SimpleNamespace(close=p, high=h if valid else None,low=l if valid else None))
        add('ATR_14',*display._atr(bars,'RAW_CLOSE'))
    volumes=[_number(r.get('volume'),zero=True) for r in eligible]
    v=volumes[-1] if volumes else None
    volume_missing=[] if v is not None else ['VOLUME_MISSING']
    last_session = eligible[-1]['date'] if eligible else None
    if last_session != signal_day:
        v = None
        volume_missing.append('SIGNAL_SESSION_MISSING')
    volume_economic=economic_for(signal_day)
    note_start=eligible[-21]['date'] if len(eligible)>=21 else start
    note_economic=economic_for(note_start)
    volume_note={'raw_state':'NOT_AVAILABLE','state':None,'reason':'INSUFFICIENT_BARS','window_start':note_start,'window_end':signal_day}
    if eligible and [r['date'] for r in eligible]==expected:
        note=patterns._volume_note({'rules':patterns.load_rules(),'timeframe':'D',
                                    'bars':[{'volume':v} for v in volumes]},0,len(volumes)-1)
        volume_note.update(raw_state=note['state'],reason=note['reason_code'])
        if not note_economic and note['state'] != 'NOT_AVAILABLE':volume_note['state']=note['state']
    volume_note['null_reasons']=list(note_economic)+([volume_note['reason']] if volume_note['reason'] else [])
    result = dict(schema=SCHEMA,result_kind='RAW_SERIES_DIAGNOSTIC',series_id=series_id,symbol=symbol,
        signal_day=signal_day,source_kind=source_kind,input_start=start,history_count=len(eligible),excluded_future_rows=len(rows)-len(eligible),
        price_basis='RAW',pit_status='NOT_VERIFIED',publication_status='RESEARCH_PRIVATE_ONLY',
        evidence=dict(evidence),rank=None,metrics=metrics,volume_note=volume_note,
        volume_latest=dict(raw_value=v,value=None if volume_economic or volume_missing else v,unit='SHARES',
                           last_observed_session=last_session,
                           null_reasons=volume_missing+volume_economic),
        pattern_status='EXISTING_RULES_ONLY_NO_NEW_PATTERN_OR_SUCCESS_DEFINITION')
    result['readiness'] = describe_readiness(result)
    return result
