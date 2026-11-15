"""Existing single-company measures, without the unmerged group/selection engine."""
from copy import deepcopy
from datetime import date, timedelta
from .kis_price_bridge import validate_contract, _covers, _day, _stamp, _status, FIELDS, price_rows, basis_evidence
from .exp_deciles import schedule, technical_measures as measures

def measure_contract(c, *, evaluation_day, series_id):
    """Measure exactly S, never substitute the last retained date for missing S."""
    validate_contract(c); _day(evaluation_day)
    if not schedule.is_session(date.fromisoformat(evaluation_day)):
        raise ValueError('SIGNAL_DAY_NOT_A_SESSION')
    if not isinstance(series_id, str) or not series_id.strip():
        raise ValueError('REQUEST_SERIES_ID_REQUIRED')
    evidence = {**c['identity'], 'security_id': None, 'currency': c['currency'],
                'currency_reference': c['currency_reference'], 'trade_scope_status': 'UNCONFIRMED',
                'trade_scope_reference': None}
    ranges = sorted((r for r in c['confirmed_ranges'] if _covers(r, evaluation_day, evaluation_day)),
                    key=lambda r:r['from'])
    if ranges:
        evidence.update(no_split_start=ranges[0]['from'], no_split_end=ranges[0]['to'],
                        no_split_reference=ranges[0]['evidence'])
    raw_bars = [r for r in c['raw_bars'] if r['date'] <= evaluation_day]
    bars = price_rows(c,evaluation_day)
    basis_evidence(evidence,c)
    normalized = [dict(date=r['date'], **{f:r.get(f) for f in FIELDS[:5]},
                       vwap=r.get('vwap'), trade_count=r.get('trade_count'),
                       requested_symbol=c['symbol'], returned_symbol=c['symbol'], price_basis=c['basis'], asof='-',
                       source_timestamp=_stamp(r['date']).isoformat(), source_sha256=r['source_sha256'],
                       quality_reasons=[]) for r in bars]
    result = measures.measure(normalized, signal_day=evaluation_day, symbol=c['symbol'],
                              series_id=series_id, evidence=evidence, liquidity_rows=[{**row,'source_timestamp':_stamp(row['date']).isoformat(),'price_basis':'RAW','requested_symbol':c['symbol'],'returned_symbol':c['symbol'],'asof':'-','quality_reasons':[]} for row in raw_bars])
    for name, metric in result['metrics'].items():
        start = metric.get('anchor_day') or (date.fromisoformat(metric['window_start']) + timedelta(days=1)).isoformat()
        end = evaluation_day
        reasons = metric['null_reasons']
        identity = c['identity']
        if not (identity.get('identity_start') or '9999') <= start <= end <= (identity.get('identity_end') or '0000'):
            reasons.append('IDENTITY_RANGE_UNCONFIRMED')
        if any(start <= r['to'] and r['from'] <= end for r in c['held_ranges']):
            reasons.append('HELD_RANGE_IN_WINDOW')
        if name != 'dollar_volume_6m':
            if c['basis']=='RAW' and any(start < s['date'] <= end for s in c['splits']):reasons.append('CORPORATE_ACTION_IN_RAW_WINDOW')
            if not any(_covers(r, start, end) for r in c['confirmed_ranges']):reasons.append('ACTION_BASIS_UNCONFIRMED')
        # Amount / volume does not manufacture VWAP. An unproven provider scope
        # cannot promote even a complete raw VWAP*volume diagnostic.
        metric['null_reasons'] = list(dict.fromkeys(reasons))
        if reasons:
            metric['value'] = None
            metric['gt_zero'] = None
        metric['state'] = 'VALUE' if metric['value'] is not None else 'DIAGNOSTIC' if metric['raw_value'] is not None else 'NOT_COMPUTED'
    observed = bars[-1]['date'] if bars else None
    result.update(schema='kis-technical-measures/1', result_kind='SINGLE_COMPANY_MEASURES',
                  evaluation_day=evaluation_day, data_asof=observed,
                  status=_status({'price_basis_date':observed}, evaluation_day),
                  source=c['source'], chart_basis=c['basis'], diagnostic_basis=c['basis'],
                  collected_at=c['collected_at'], historical_available_at=None, pit_status='NOT_VERIFIED',
                  publication_scope='OWNER_PRIVATE_ONLY', rank_count=0,
                  raw_count=sum(m['raw_value'] is not None for m in result['metrics'].values()),
                  adopted_count=sum(m['value'] is not None for m in result['metrics'].values()))
    if c.get('update_state') in ('FAILED', 'PARTIAL'):result['status']='STALE'
    return result
