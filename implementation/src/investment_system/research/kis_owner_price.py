"""Pure KIS retained-close projection into the shared owner-price V contract.

No network, price adjustment, formula, clock read or persistence. Independent
contract pins are supplied by Main after verifying the original receipt/manifest.
Canonical contract digests do not replace original response-byte verification.
"""
from copy import deepcopy
from decimal import Decimal
import math

from .kis_price_bridge import validate_contract, EXCHANGES, _covers, _day, _ts
from .kis_split_evidence import assess_splits
from .sector_qgv import digest


def _need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _refs(v):
    return isinstance(v,list) and bool(v) and all(isinstance(x,str) and x for x in v)


def _proof(p, cutoff):
    if not isinstance(p,dict) or p.get('status')!='VERIFIED' or not _refs(p.get('source_refs')):
        return False
    try:
        return _ts(p.get('available_at'))<=cutoff
    except ValueError:
        return False


def _valid_day(value):
    try:
        _day(value)
        return True
    except (ValueError,TypeError):
        return False


def _identity_reason(c, row, wrapped, day, cutoff):
    b=(wrapped or {}).get('basis_evidence') or {}
    m=b.get('mapping') or {}
    identity=c.get('identity') or {}
    exchange=(c.get('source_query') or {}).get('EXCD')
    if (not _proof(m,cutoff) or not m.get('record_id') or
        m.get('company_id')!=row['company_id'] or m.get('issuer_id')!=row.get('issuer_id') or
        m.get('provider')!='KIS' or m.get('provider_symbol')!=c['symbol'] or
        m.get('exchange')!=c['exchange'] or
        m.get('provider_exchange_code',exchange)!=exchange or not m.get('share_class_id')):
        return 'KIS_SECURITY_MAPPING_UNCONFIRMED'
    for security_id in (row.get('security_id'),c.get('security_id')):
        if security_id and m.get('security_id')!=security_id:
            return 'KIS_SECURITY_ID_CONFLICT'
    if c.get('issuer_id') and c['issuer_id']!=row.get('issuer_id'):
        return 'KIS_ISSUER_ID_CONFLICT'
    if (identity.get('identity_status') not in ('CONFIRMED','DOCUMENT_RECONSTRUCTED') or
        not identity.get('identity_reference') or
        not _valid_day(identity.get('identity_start')) or not _valid_day(identity.get('identity_end')) or
        not identity['identity_start']<=day<=identity['identity_end']):
        return 'KIS_IDENTITY_PERIOD_UNCONFIRMED'
    if (not _valid_day(m.get('valid_from')) or m['valid_from']>day or
        m.get('valid_to') is not None and (not _valid_day(m['valid_to']) or day>=m['valid_to'])):
        return 'KIS_MAPPING_PERIOD_UNCONFIRMED'
    return None


def _action_reason(c, wrapped, day, cutoff, assessment):
    b=(wrapped or {}).get('basis_evidence') or {}
    actions=b.get('corporate_actions') or {}
    shares=(((wrapped or {}).get('record') or {}).get('v_inputs_v2') or {}).get('diluted_shares') or {}
    period=shares.get('period_end');start=actions.get('from_day')
    if (not _valid_day(period) or not _valid_day(start) or start>period or period>day or
        not _proof(actions,cutoff) or not _valid_day(actions.get('through_day')) or actions['through_day']<day):
        return 'CORPORATE_ACTION_BASIS_UNCONFIRMED'
    if not any(_covers(r,start,day) for r in c['confirmed_ranges']):
        return 'KIS_ACTION_INTERVAL_UNCONFIRMED'
    if any(start<=r['to'] and r['from']<=day for r in c['held_ranges']):
        return 'HELD_RANGE_IN_FINANCIAL_BASIS'
    # assess_splits.block_reasons covers the retained PRICE window only. A split
    # outside that window can still invalidate the older financial share unit.
    used=[e for e in assessment['events'] if start<e['effective_date']<=day]
    conflicts=[reason for e in used for reason in e['reasons']]
    if conflicts:
        return conflicts[0]
    if not used:
        return None
    proof=b.get('share_normalization') or {}
    mapping=b.get('mapping') or {}
    expected={e['record_hash'] for e in assessment['confirmed_events'] if start<e['date']<=day}
    actual=proof.get('split_event_hashes')
    unit_day=proof.get('share_unit_basis_day')
    if (not _proof(proof,cutoff) or proof.get('mode')!='SOURCE_ALREADY_NORMALIZED' or
        proof.get('record_hash')!=digest(wrapped['record']) or proof.get('target_day')!=day or
        proof.get('share_class_id')!=mapping.get('share_class_id') or
        not _valid_day(unit_day) or not max(e['effective_date'] for e in used)<=unit_day<=day or
        not isinstance(actual,list) or not all(isinstance(x,str) and len(x)==64 for x in actual) or
        len(actual)!=len(set(actual)) or set(actual)!=expected or
        actions.get('basis')!='ALREADY_NORMALIZED'):
        return 'SHARE_NORMALIZATION_UNCONFIRMED'
    return None


def _source_summary(c, raw, assessment, pin):
    return dict(normalized_contract_hash=pin,
        original_response_sha256=raw.get('source_sha256') if raw else None,
        source_query=deepcopy(c.get('source_query')),
        source_exchange=c['exchange'],currency_reference=c.get('currency_reference'),
        source_input_basis=c['basis'],selected_price_basis='EXACT_DAY_ORIGINAL_MODP0_CLOSE',
        source_session_scope=c.get('session_scope','PROVIDER_UNCONFIRMED'),
        source_price_scope_status=c.get('price_scope_status','UNCONFIRMED'),
        exchange_official_close_confirmed=False,
        update_state=c.get('update_state','RETAINED_ARCHIVE'),
        header_collected_at=c['collected_at'],
        last_success_at=c.get('last_success_at',c['collected_at']),
        row_collected_at=raw.get('collected_at') if raw else None,
        split_evidence=dict(policy_version=assessment['policy_version'],
            source_document_verification=assessment['source_document_verification'],
            independently_verified=False,
            events=[dict(effective_date=e['effective_date'],ratio=e['ratio'],
                ratio_definition=e['ratio_definition'],state=e['state'],reasons=deepcopy(e['reasons']),
                source_record_state=e['source_record_state']) for e in assessment['events']],
            confirmed_event_hashes=[e['record_hash'] for e in assessment['confirmed_events']],
            future_events_excluded=len(assessment['excluded_future_events'])))


def prepare_kis_quotes(context,evaluation,reference,financial_records,contracts,*,expected_contract_hashes):
    """Return common quote rows, preserving original capture clocks and full roster.

    Missing contracts produce no quote (the common engine keeps the roster row).
    Malformed or hash-mismatched contracts fail explicitly. Nonprice uncertainty
    is a row qualification reason and never a zero price or invented identity.
    """
    _need(context.get('provider')=='KIS' and context.get('price_definition')=='KIS_DAILY_CLOSE' and
        context.get('evaluation_mode')=='EXPLICIT_EOD_ASOF','KIS_PRICE_PROFILE')
    day=_day(context['evaluation_day']);cutoff=_ts(context['input_cutoff'])
    _need(isinstance(contracts,dict) and isinstance(expected_contract_hashes,dict),'KIS_CONTRACT_MAP')
    known={}
    for snapshot in (evaluation,reference):
        for row in snapshot['rows']:
            cid=row['company_id']
            if cid in known:
                _need(all(known[cid].get(k)==row.get(k) for k in ('issuer_id','security_id')),'KIS_ROSTER_IDENTITY_CONFLICT')
            known[cid]=row
    _need(set(contracts)<=set(known),'KIS_CONTRACT_OUTSIDE_ROSTER')
    _need(set(expected_contract_hashes)==set(contracts),'KIS_CONTRACT_PIN_SET')
    quotes=[]
    for cid,c in sorted(contracts.items()):
        pin=expected_contract_hashes[cid]
        _need(isinstance(c,dict) and c.get('schema')=='kis-bars/1','KIS_DAILY_CONTRACT_REQUIRED')
        _need(isinstance(pin,str) and len(pin)==64 and digest(c)==pin,'KIS_CONTRACT_HASH_MISMATCH')
        validate_contract(c)
        query=c.get('source_query') or {}
        _need(query.get('MODP')=='0' and query.get('GUBN')=='0','RAW_DAILY_SOURCE_REQUIRED')
        _need(query.get('SYMB')==c.get('symbol') and EXCHANGES.get(query.get('EXCD'))==c.get('exchange'),
            'KIS_SOURCE_IDENTITY_MISMATCH')
        _need(c.get('currency')=='USD' and bool(c.get('currency_reference')),'CURRENCY_EVIDENCE_REQUIRED')
        _need(_ts(c['collected_at'])<=cutoff,'KIS_SOURCE_AFTER_CUTOFF')
        assessment=assess_splits(c,day)
        bars=[r for r in c['raw_bars'] if r['date']==day]
        _need(len(bars)<=1,'DUPLICATE_KIS_PRICE_DAY')
        raw=bars[0] if bars else None
        q=dict(company_id=cid,issuer_id=known[cid].get('issuer_id'),provider_symbol=c['symbol'],
            provider='KIS',price_definition='KIS_DAILY_CLOSE',adjustment_status='AS_TRADED',
            currency=c['currency'],status='MISSING',price=None,trade_day=None,
            requested_trade_day=day,price_timestamp=None,time_status='DATE_ONLY',
            query_started_at=raw.get('query_started_at') if raw else None,
            received_at=raw['collected_at'] if raw else c['collected_at'],
            source_refs=['KIS_NORMALIZED_CONTRACT:'+pin]+
                (['KIS_RESPONSE_SHA256:'+raw['source_sha256']] if raw else []),
            price_source_metadata=_source_summary(c,raw,assessment,pin))
        if raw and raw.get('close') is not None:
            value=float(Decimal(raw['close']))
            _need(math.isfinite(value) and value>0,'INVALID_KIS_PRICE')
            q.update(status='AVAILABLE',price=value,trade_day=day)
        else:
            q['qualification_reason']='EXACT_TRADE_DAY_NOT_RETAINED' if raw is None else 'CLOSE_NOT_AVAILABLE'
        if raw:
            _need(_ts(raw['collected_at'])<=cutoff,'KIS_PRICE_AFTER_CUTOFF')
            reason=_identity_reason(c,known[cid],financial_records.get(cid),day,cutoff)
            if not reason:
                reason=_action_reason(c,financial_records.get(cid),day,cutoff,assessment)
            if reason:
                q['qualification_reason']=reason
                q['nonprice_reason']=reason
        quotes.append(q)
    return quotes
