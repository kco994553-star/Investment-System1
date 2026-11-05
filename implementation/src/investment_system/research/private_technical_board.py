"""Retained price contracts -> shared five measures -> a frozen, evidenced board.

No collection, synthetic identity assignment, alternative formulas or reranking.
Company diagnostics do not require a complete comparison population.
"""
from copy import deepcopy
from datetime import date, timedelta

from .kis_price_bridge import validate_contract, _covers, _day, _stamp, _status, FIELDS
from .exp_deciles import schedule, technical_measures as measures
from .exp_deciles.technical_leaderboard import build_board, filter_board

SECURITY_IDENTIFIER_TYPES = frozenset(('PERMNO', 'FIGI', 'ISIN', 'CUSIP', 'EXCHANGE_SECURITY_ID',
                                       'PROVIDER_SECURITY_ID', 'SYNTHETIC_FIXED_SECURITY_ID'))


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
    bars = [r for r in c['raw_bars'] if r['date'] <= evaluation_day]
    normalized = [dict(date=r['date'], **{f:r.get(f) for f in FIELDS[:5]},
                       vwap=r.get('vwap'), trade_count=r.get('trade_count'),
                       requested_symbol=c['symbol'], returned_symbol=c['symbol'], price_basis='RAW', asof='-',
                       source_timestamp=_stamp(r['date']).isoformat(), source_sha256=r['source_sha256'],
                       quality_reasons=[]) for r in bars]
    result = measures.measure(normalized, signal_day=evaluation_day, symbol=c['symbol'],
                              series_id=series_id, evidence=evidence)
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
            if c['basis'] != 'RAW':reasons.append('SPLIT_ADJUSTED_DISPLAY_ADAPTER_PENDING')
            if any(start < s['date'] <= end for s in c['splits']):reasons.append('CORPORATE_ACTION_IN_RAW_WINDOW')
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
                  source=c['source'], chart_basis=c['basis'], diagnostic_basis='RAW',
                  collected_at=c['collected_at'], historical_available_at=None, pit_status='NOT_VERIFIED',
                  publication_scope='OWNER_PRIVATE_ONLY', rank_count=0,
                  raw_count=sum(m['raw_value'] is not None for m in result['metrics'].values()),
                  adopted_count=sum(m['value'] is not None for m in result['metrics'].values()))
    if c.get('update_state') in ('FAILED', 'PARTIAL'):result['status']='STALE'
    return result


def build_contract_board(series, *, group, security_links=(), conditions=()):
    """A supplied fixed-ID link and dated membership are separate prerequisites.

    Links are evidence inputs, not IDs generated from a ticker or issuer CIK. A
    missing link preserves company measures and leaves that group member unscored.
    """
    series = list(series)
    synthetic = [s['contract'].get('fixture_kind') == 'SYNTHETIC_NOT_A_COMPANY' for s in series]
    if any(synthetic) and not all(synthetic):raise ValueError('MIXED_SYNTHETIC_AND_RETAINED_INPUT')
    ids = [s['series_id'] for s in series]
    if len(set(ids)) != len(ids):raise ValueError('DUPLICATE_REQUEST_SERIES')
    links = {}
    for link in security_links:
        sid = link.get('security_id')
        kind = link.get('identifier_type')
        if (not isinstance(sid, str) or not sid.strip() or not isinstance(kind, str) or kind not in SECURITY_IDENTIFIER_TYPES
                or not isinstance(link.get('reference'), str) or not link['reference'].strip()):
            raise ValueError('FIXED_SECURITY_LINK_EVIDENCE_REQUIRED')
        if kind == 'SYNTHETIC_FIXED_SECURITY_ID' and not all(synthetic):
            raise ValueError('SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT')
        if _day(link['valid_from']) > _day(link['valid_to']):raise ValueError('INVALID_SECURITY_LINK_RANGE')
        if link['series_id'] in links or link['series_id'] not in ids:raise ValueError('INVALID_SECURITY_LINK_SERIES')
        links[link['series_id']] = link
    measurements, linkage = [], []
    for item in series:
        c, series_id = item['contract'], item['series_id']
        m = measure_contract(c, evaluation_day=group['signal_day'], series_id=series_id)
        link = links.get(series_id)
        reason = 'FIXED_SECURITY_LINK_MISSING'
        if link:
            sid = link['security_id']
            if sid in (c['symbol'], c.get('issuer_id')):raise ValueError('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID')
            if c.get('security_id') not in (None, sid):raise ValueError('SECURITY_LINK_CONFLICT')
            if not link['valid_from'] <= group['signal_day'] <= link['valid_to']:
                reason = 'SECURITY_LINK_OUTSIDE_SIGNAL_DAY'
            elif not measures._identity(c['identity']):
                reason = 'IDENTITY_UNCONFIRMED'
            elif not (c['identity'].get('identity_start') or '9999') <= group['signal_day'] <= (c['identity'].get('identity_end') or '0000'):
                reason = 'IDENTITY_RANGE_UNCONFIRMED'
            else:
                m['security_id'] = sid
                m['qgv_join_key'] = [group['signal_day'], sid]
                reason = None
        linkage.append(dict(series_id=series_id, security_id=m['security_id'], reason=reason))
        measurements.append(m)
    board = build_board(measurements, group=group)
    selected = filter_board(board, conditions)
    return dict(schema='kis-technical-board/1', result_kind='DATED_GROUP_BOARD',
                signal_day=group['signal_day'], publication_scope='OWNER_PRIVATE_ONLY',
                pit_status='NOT_VERIFIED',
                evidence_kind='SYNTHETIC' if series and all(synthetic) else 'RETAINED_INPUT',
                measurements=measurements, linkage=linkage, board=board,
                selection=dict(conditions=deepcopy(list(conditions)), security_ids=selected, rank_origin='ORIGINAL_GROUP',
                               status='CALCULATED' if group.get('membership_status') == 'CONFIRMED' else 'NOT_COMPUTED',
                               reason=None if group.get('membership_status') == 'CONFIRMED' else 'GROUP_MEMBERSHIP_UNCONFIRMED'),
                requested_series_count=len(series),
                fixed_security_id_count=sum(m['security_id'] is not None for m in measurements),
                ranked_security_count=len({r['security_id'] for metric in board['metrics'].values()
                                           for r in metric['rows'] if r['rank'] is not None}))
