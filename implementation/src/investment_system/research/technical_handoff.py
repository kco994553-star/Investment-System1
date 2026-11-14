"""Small private handoff over existing KIS normalization and technical kernels.

No collection, price repair, new indicator formula, group ranking or QGV scoring.
Chart indicators may show a stale observation; measures stay pinned to signal S.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json

from ..technical import chart_bars, patterns
from .kis_price_bridge import analyze, price_rows, validate_contract, _covers, _stamp
from .private_technical_board import measure_contract
from .exp_deciles.technical_measures import sessions, _identity
from .sector_qgv import digest
from .dual_qgv_delivery import MAX_BYTES
from .technical_display import _INITIALIZATION


def _pattern_result(c, rows, day, missing):
    reasons = []
    start = rows[0]['date'] if rows else day
    if missing or not rows: reasons.append('PRICE_WINDOW_INCOMPLETE')
    if not rows or rows[-1]['date'] != day: reasons.append('SIGNAL_SESSION_MISSING')
    identity = c['identity']
    if not _identity(identity): reasons.append('IDENTITY_UNCONFIRMED')
    if not ((identity.get('identity_start') or '9999') <= start <= day <=
            (identity.get('identity_end') or '0000')): reasons.append('IDENTITY_RANGE_UNCONFIRMED')
    if not c.get('currency_reference'): reasons.append('CURRENCY_UNCONFIRMED')
    covered = next((r for r in c['confirmed_ranges'] if _covers(r, start, day)), None)
    if covered is None: reasons.append('ACTION_BASIS_UNCONFIRMED')
    if any(start <= r['to'] and r['from'] <= day for r in c['held_ranges']):
        reasons.append('HELD_RANGE_IN_WINDOW')
    if any(any(r.get(k) is None for k in ('open', 'high', 'low', 'close')) for r in rows):
        reasons.append('OHLC_MISSING')
    used_splits = [s['date'] for s in c['splits'] if start <= s['date'] <= day]
    rules = patterns.load_rules()
    out = dict(state='NOT_JUDGEABLE' if reasons else 'CALCULATED_RESEARCH',
               basis='RAW_CLOSE', reasons=list(dict.fromkeys(reasons)),
               rule_version=rules['rule_version'], params_sha256=rules['params_sha256'],
               rules_scope='RESEARCH_DEFAULT_NOT_INVESTMENT_SIGNAL',
               volume_scope='WITHHELD_SCOPE_UNCONFIRMED', applied_splits=used_splits,
               success_probability=None, result=None,
               initialization=dict(minimum_sessions=_INITIALIZATION['ATR_14'][0],
                                   latest_segment_state='NOT_EVALUATED', segments=[]))
    if reasons: return out
    # Actual retained RAW OHLC, never SPLIT_ADJUSTED relabelled as RAW_CLOSE.
    # KIS volume scope is unconfirmed: withhold volume confirmation, not prices.
    history = dict(schema=chart_bars.SOURCE_SCHEMA, symbol=c['symbol'], provider=c['source'],
        interval='1d', basis='RAW_CLOSE', timezone=c['timezone'], currency=c['currency'],
        exchange=c['exchange'], read_at=c['collected_at'], delay_status='UNKNOWN',
        bars=[dict(timestamp=int(_stamp(r['date']).timestamp()), session_date=r['date'],
                   session_status='COMPLETE', adjusted_close=None, volume=None,
                   **{k: float(r[k]) for k in ('open', 'high', 'low', 'close')}) for r in rows])
    actions = dict(status='AVAILABLE', covered_from=covered['from'], covered_to=covered['to'],
                   splits=used_splits)
    out['result'] = patterns.run(chart_bars.normalize(history), rules, actions)
    minimum = out['initialization']['minimum_sessions']
    out['initialization']['segments'] = [dict(start_day=rows[a]['date'], end_day=rows[b]['date'],
        observed_sessions=b-a+1, atr_seed_state='READY' if b-a+1 >= minimum else 'INSUFFICIENT')
        for a, b in out['result']['segments']]
    if out['initialization']['segments']:
        out['initialization']['latest_segment_state'] = out['initialization']['segments'][-1]['atr_seed_state']
    return out


def prepare_technical(c, *, evaluation_day, series_id):
    """kis-bars/1 -> existing components/measures plus explicit Main-ready reasons.

    Call on newly received inputs. Previously stored outputs need no recomputation.
    Results and chart prices are owner-private RAM values; this function never writes.
    """
    if c.get('schema') != 'kis-bars/1': raise ValueError('KIS_DAILY_CONTRACT_REQUIRED')
    validate_contract(c)
    components = analyze(c, evaluation_day=evaluation_day)
    measures = measure_contract(c, evaluation_day=evaluation_day, series_id=series_id)
    raw = [r for r in c['raw_bars'] if r['date'] <= evaluation_day]
    expected = sessions(date.fromisoformat(raw[0]['date'] if raw else evaluation_day),
                        date.fromisoformat(evaluation_day))
    actual = {r['date'] for r in raw}
    missing = [d for d in expected if d not in actual]
    availability = []
    for kind, result in [('CHART_COMPONENT', components), ('COMPANY_MEASURE', measures)]:
        for name, metric in result['metrics'].items():
            value = metric['value']; diagnostic = metric['raw_value']
            readiness = components['readiness']['metrics'].get(name, {}) if kind == 'CHART_COMPONENT' else {}
            availability.append(dict(metric_id=name, kind=kind, unit=metric['unit'], value=value,
                state='VALUE' if value is not None else 'DIAGNOSTIC' if diagnostic is not None else 'NOT_COMPUTED',
                reasons=deepcopy(metric['null_reasons']), raw_available=diagnostic is not None,
                observation_day=result['data_asof'], signal_day=evaluation_day,
                stale_status=result['status'], initialization=deepcopy(readiness.get('initialization')),
                warmup=deepcopy(readiness.get('warmup')),
                rank=None, decile=None, group_status='NOT_REQUESTED'))
    result = dict(schema='kis-technical-handoff/1', publication_scope='OWNER_PRIVATE_ONLY',
        data_kind='SYNTHETIC' if c.get('fixture_kind') == 'SYNTHETIC_NOT_A_COMPANY' else 'RETAINED_INPUT',
        context=dict(series_id=series_id, signal_day=evaluation_day,
            chart_observation_day=components['data_asof'], measure_observation_day=measures['data_asof'],
            collected_at=c['collected_at'], historical_available_at=c.get('historical_available_at'),
            update_state=c.get('update_state', 'RETAINED_ARCHIVE'),
            last_success_at=c.get('last_success_at', c['collected_at']),
            pit_status='NOT_VERIFIED', timestamp_basis=c['timestamp_basis'],
            excluded_future_rows=len(c['raw_bars']) - len(raw)),
        provenance=dict(contract_hash=digest(c), source_sha256=c['source_sha256'],
            source_query=deepcopy(c['source_query']), source=c['source'],
            identity=deepcopy(c['identity']), currency_reference=c['currency_reference']),
        sessions=dict(calendar=c['calendar'], timezone=c['timezone'],
            checked_from=raw[0]['date'] if raw else None, checked_to=evaluation_day,
            expected_count=len(expected), retained_count=len(raw), missing=missing,
            rejected_rows=deepcopy(c['rejected_rows']), gap_fill='NONE',
            scope='FIRST_RETAINED_SESSION_THROUGH_SIGNAL_NOT_ALL_REQUESTED_HISTORY'),
        chart=dict(basis=c['basis'], currency=c['currency'], dividend_adjustment=c['dividend_adjustment'],
            volume_basis=c['volume_basis'], amount_basis=c['amount_basis'],
            bars=deepcopy(price_rows(c, evaluation_day))),
        components=components, measures=measures,
        patterns=_pattern_result(c, raw, evaluation_day, missing), availability=availability,
        group=dict(state='NOT_REQUESTED', reason='DATED_GROUP_AND_FIXED_SECURITY_LINK_REQUIRED',
                   rank=None, decile=None, qgv_join_status='NOT_REQUESTED'),
        coverage_claim=None)
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True,
                         separators=(',', ':')).encode()
    result['result_sha256'] = hashlib.sha256(encoded).hexdigest()
    final_bytes = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True,
                             separators=(',', ':')).encode()
    if len(final_bytes) + 1 > MAX_BYTES: raise ValueError('TECHNICAL_HANDOFF_TOO_LARGE')
    return result
