"""Pure, offline split-evidence checks shared by KIS technical and V adapters.

Metadata agreement preserves the existing declared-reference adoption policy; it
is not an independent read or verification of an original corporate-action filing.
No price adjustment, source request, clock read or ledger write occurs here.
"""
from copy import deepcopy

from .kis_price_bridge import validate_contract, _covers, _decimal, _day
from .sector_qgv import digest


def assess_splits(c, evaluation_day):
    """Explain declared references without upgrading them to original-source reads.

    Optional source_record fields are compared with the event/series, never used
    to manufacture a missing identity. Full-range coverage is explanatory: each
    existing metric keeps its own dependency window gate.
    """
    day = _day(evaluation_day)
    if c.get('schema') != 'kis-bars/1': raise ValueError('KIS_DAILY_CONTRACT_REQUIRED')
    query = c.get('source_query') or {}
    if query.get('MODP') != '0' or query.get('GUBN') != '0':
        raise ValueError('RAW_DAILY_SOURCE_REQUIRED')
    if query.get('SYMB') != c.get('symbol'):
        raise ValueError('KIS_SOURCE_IDENTITY_MISMATCH')
    if any(r.get('price_basis', 'RAW') not in ('RAW', 'RAW_CLOSE') for r in c['raw_bars']):
        raise ValueError('RAW_INPUT_ALREADY_ADJUSTED')
    validate_contract(c)
    raw = [r for r in c['raw_bars'] if r['date'] <= day]
    start = raw[0]['date'] if raw else day
    covered = next((r for r in c['confirmed_ranges'] if _covers(r, start, day)), None)
    full_reasons = [] if covered else ['ACTION_BASIS_UNCONFIRMED']
    if any(start <= r['to'] and r['from'] <= day for r in c['held_ranges']):
        full_reasons.append('HELD_RANGE_IN_WINDOW')
    events, confirmed, future, blocking = [], [], [], []
    for event in c['splits']:
        relevant = bool(raw) and start < event['date'] <= day
        record = event.get('source_record')
        reasons = []; compared = []; unconfirmed = []
        if record is None:
            record_state = 'NOT_PROVIDED'
        elif not isinstance(record, dict):
            record_state = 'INVALID'; reasons.append('SPLIT_SOURCE_RECORD_INVALID')
        else:
            if 'ratio' in record:
                compared.append('ratio')
                try:
                    same_ratio = _decimal(record['ratio'], nullable=False) == _decimal(event['ratio'], nullable=False)
                except ValueError:
                    same_ratio = False
                if not same_ratio: reasons.append('SPLIT_RATIO_CONFLICT')
            if 'effective_date' in record:
                compared.append('effective_date')
                if record['effective_date'] != event['date']: reasons.append('SPLIT_EFFECTIVE_DATE_CONFLICT')
            for key in ('symbol', 'issuer_id', 'security_id'):
                if key not in record: continue
                if c.get(key) is None:
                    unconfirmed.append(key)
                else:
                    compared.append(key)
                    if record[key] != c[key]: reasons.append('SPLIT_SUBJECT_MISMATCH')
            record_state = ('CONFLICT' if reasons else 'PARTIAL_IDENTITY_UNCONFIRMED' if unconfirmed else
                            'SUPPLIED_FIELDS_MATCH' if compared else 'NO_COMPARABLE_FIELDS')
        reasons = list(dict.fromkeys(reasons))
        state = ('EXCLUDED_FUTURE_EVENT' if event['date'] > day else
                 'CONFLICT' if reasons and relevant else 'OUTSIDE_RETAINED_PRICE_WINDOW' if not relevant else
                 'DECLARED_CONFIRMED_WITH_REFERENCE')
        if relevant: blocking.extend(reasons)
        original = dict(date=event['date'], ratio=event['ratio'], evidence=deepcopy(event['evidence']),
            record=deepcopy(event), record_hash=digest(event),
            source_record=deepcopy(record), source_record_hash=digest(record) if isinstance(record, dict) else None,
            independently_verified=False, adoption_basis='EXISTING_CALLER_DECLARATION_WITH_REFERENCE')
        if event['date'] > day:
            future.append(dict(**original, state='EXCLUDED_FUTURE_EVENT', reasons=reasons))
        elif not reasons:
            confirmed.append(original)
        events.append(dict(effective_date=event['date'], ratio=event['ratio'],
            ratio_definition='NEW_SHARES_PER_OLD_SHARE', declared_status=event['status'],
            evidence_reference=deepcopy(event['evidence']), state=state, reasons=reasons,
            relevant_to_prices=relevant, adjustment_applied=relevant and c['basis'] == 'SPLIT_ADJUSTED' and not reasons,
            source_record_state=record_state, compared_fields=compared, unconfirmed_fields=unconfirmed,
            source_record_reference={k: deepcopy(record[k]) for k in
                ('source_sha256', 'document_location', 'reviewed_at') if isinstance(record, dict) and k in record}))
    blocking = list(dict.fromkeys(blocking))
    return dict(policy_version='kis-split-evidence/1',
        state='WITHHELD_CONFLICT' if blocking else 'EXISTING_DECLARED_EVIDENCE_POLICY',
        source_document_verification='NOT_PERFORMED', independently_verified=False,
        empty_event_list_is_no_split_evidence=False,
        adjustment_method='CONFIRMED_SPLITS_ONLY' if c['basis'] == 'SPLIT_ADJUSTED' else 'NONE_RAW',
        duplicate_adjustment_policy='ORIGINAL_MODP0_REQUIRED_EXISTING_EXACT_BAR_VALIDATION',
        full_retained_interval=dict(start_day=raw[0]['date'] if raw else None, end_day=day,
            state='COVERED_BY_DECLARED_REFERENCE' if covered and not full_reasons else 'UNCONFIRMED',
            reasons=full_reasons, evidence_reference=covered['evidence'] if covered else None,
            adoption_policy='EACH_EXISTING_METRIC_DEPENDENCY_WINDOW'),
        raw_window_split_dates=[e['effective_date'] for e in events if e['relevant_to_prices']],
        events=events, confirmed_events=confirmed, excluded_future_events=future,
        block_reasons=blocking)
