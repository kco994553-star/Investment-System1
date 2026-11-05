"""Offline retained daily-price adapter. No authentication, network or public output.

Reuses the chart validator, GSQ-015 display kernels and existing ledger marking.
Provider MODP1 never substitutes for verified split-only adjustment. Raw diagnostics
are not official QGV, a performance series, or an authenticated UI acceptance test.
"""
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from investment_system.technical import chart_bars
from .technical_display import measure_display, describe_readiness
from .exp_deciles import schedule
from .pit_filings import session_close
from .exp_deciles.ledger import Ledger, PriceRow

SCHEMA = 'kis-bars/1'
EXCHANGES = {'NAS': 'NASDAQ', 'NYS': 'NYSE', 'AMS': 'NYSE_AMERICAN'}
FIELDS = ('open', 'high', 'low', 'close', 'volume', 'amount')


def _day(s):
    if not isinstance(s, str) or date.fromisoformat(s).isoformat() != s:
        raise ValueError('INVALID_SESSION_DATE')
    return s


def _ts(s):
    try:
        v = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if v.tzinfo is None: raise ValueError()
        return v
    except (ValueError, TypeError, AttributeError):
        raise ValueError('INVALID_CAPTURE_TIME') from None


def _decimal(v, *, zero=False, nullable=True):
    if v in (None, '') and nullable: return None
    if not isinstance(v, str) or len(v)>80: raise ValueError('INVALID_DECIMAL_STRING')
    try: n = Decimal(v)
    except InvalidOperation: raise ValueError('INVALID_DECIMAL_STRING') from None
    if not n.is_finite() or (n<0 if zero else n<=0) or abs(n.adjusted())>100:
        raise ValueError('INVALID_DECIMAL_VALUE')
    return n


def _str(n):
    return None if n is None else format(n, 'f')


def _covers(r, start, end):
    return r['from'] <= start <= end <= r['to'] and bool(r.get('evidence'))


def _stamp(day):
    # Calendar join key only. Not a provider observation/publication timestamp.
    return datetime.combine(date.fromisoformat(day), time(0), ZoneInfo('America/New_York'))


def _split_adjust(rows, splits):
    adjusted=deepcopy(rows)
    for split in splits:
        ratio=Decimal(split['ratio'])
        for row in adjusted:
            if row['date']<split['date']:
                with localcontext() as ctx:
                    ctx.prec=50
                    for field in ('open','high','low','close'):
                        if row.get(field) is not None:row[field]=_str(Decimal(row[field])/ratio)
                    if row.get('volume') is not None:row['volume']=_str(Decimal(row['volume'])*ratio)
    return adjusted


def price_rows(c, evaluation_day):
    """Rebase only confirmed splits through S, never a later archive event."""
    rows=[r for r in c['raw_bars'] if r['date']<=evaluation_day]
    return _split_adjust(rows,[s for s in c['splits'] if s['date']<=evaluation_day]) if c['basis']=='SPLIT_ADJUSTED' else rows


def basis_evidence(evidence, c):
    evidence['price_basis']=c['basis']
    if c['basis']=='SPLIT_ADJUSTED':
        for old,new in [('no_split_start','adjustment_start'),('no_split_end','adjustment_end'),('no_split_reference','adjustment_reference')]:
            if old in evidence:evidence[new]=evidence.pop(old)
        evidence['adjustment_method']='CONFIRMED_SPLITS_ONLY'
    return evidence


def normalize_page(body, *, receipt, request, evidence, basis='RAW'):
    if hashlib.sha256(body).hexdigest()!=receipt.get('sha256') or len(body)!=receipt.get('bytes'):
        raise ValueError('SOURCE_HASH_OR_SIZE_MISMATCH')
    if receipt.get('http_status')!=200: raise ValueError('SOURCE_HTTP_FAILURE')
    captured=receipt.get('fetched_at');_ts(captured)
    if request.get('MODP')!='0' or request.get('GUBN')!='0': raise ValueError('RAW_DAILY_SOURCE_REQUIRED')
    symbol=request.get('SYMB');exchange=request.get('EXCD')
    if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,15}',symbol) or exchange not in EXCHANGES:
        raise ValueError('INVALID_QUERY_IDENTITY')
    query=datetime.strptime(request['BYMD'],'%Y%m%d').date().isoformat()
    data=json.loads(body)
    if data.get('rt_cd')!='0' or not isinstance(data.get('output2'),list): raise ValueError('SOURCE_RESPONSE_FAILURE')
    if data.get('output2') and data.get('output1',{}).get('rsym')!='D'+exchange+symbol:
        raise ValueError('RETURNED_SYMBOL_MISMATCH')
    if basis not in ('RAW','SPLIT_ADJUSTED'): raise ValueError('UNSUPPORTED_PRICE_BASIS')
    currency=evidence.get('currency')
    if currency!='USD' or not evidence.get('currency_reference'): raise ValueError('CURRENCY_EVIDENCE_REQUIRED')
    raw, rejected, seen=[],[],set()
    for record in data['output2']:
        day=datetime.strptime(record['xymd'],'%Y%m%d').date().isoformat()
        if day in seen or day>query: raise ValueError('DUPLICATE_OR_FUTURE_SESSION')
        seen.add(day)
        if not schedule.is_session(date.fromisoformat(day)):
            rejected.append({'date':day,'reason':'REFERENCE_CALENDAR_CLOSED'});continue
        close=session_close(date.fromisoformat(day)).close_at
        if close is None or close>_ts(captured): raise ValueError('INCOMPLETE_SESSION_AT_CAPTURE')
        try:
            values={k:_decimal(record.get(v),zero=k in ('volume','amount')) for k,v in zip(FIELDS,('open','high','low','clos','tvol','tamt'))}
            o,h,l,c=(values[k] for k in ('open','high','low','close'))
            if all(v is not None for v in (o,h,l,c)) and not l<=min(o,c)<=max(o,c)<=h:
                raise ValueError('OHLC_INCONSISTENT')
        except ValueError as error:
            rejected.append({'date':day,'reason':str(error)});continue
        raw.append({'date':day,**{k:_str(v) for k,v in values.items()},'corrected':None,'source_sha256':receipt['sha256'],'collected_at':captured})
    raw.sort(key=lambda r:r['date']);bars=deepcopy(raw)
    splits=deepcopy(evidence.get('splits',[]))
    if len({s['date'] for s in splits})!=len(splits): raise ValueError('DUPLICATE_SPLIT')
    for s in splits:
        _day(s['date']);ratio=_decimal(s['ratio'],nullable=False)
        if not s.get('evidence') or s.get('status')!='CONFIRMED': raise ValueError('SPLIT_EVIDENCE_REQUIRED')
        if not raw or s['date']>raw[-1]['date']: raise ValueError('SPLIT_AFTER_BASIS_DATE')
    if basis=='SPLIT_ADJUSTED':bars=_split_adjust(raw,splits)
    result={'schema':SCHEMA,'symbol':symbol,'security_id':evidence.get('security_id'),
            'issuer_id':evidence.get('issuer_id'),'exchange':EXCHANGES[exchange],'currency':currency,
            'source':'KIS retained dailyprice MODP0','price_basis_date':raw[-1]['date'] if raw else None,
            'collected_at':captured,'corrected_at':None,'historical_available_at':None,
            'calendar':'NYSE','timezone':'America/New_York','basis':basis,'dividend_adjustment':'NONE',
            'session_scope':evidence.get('session_scope','PROVIDER_UNCONFIRMED'),
            'price_scope_status':evidence.get('price_scope_status','UNCONFIRMED'),
            'volume_basis':'PROVIDER_REPORTED_UNCONFIRMED','amount_basis':'PROVIDER_REPORTED_UNCONFIRMED',
            'vwap':None,'trade_count':None,'source_sha256':receipt['sha256'],'source_query':{k:request[k] for k in ('SYMB','EXCD','MODP','GUBN','BYMD')},
            'identity':{k:evidence.get(k) for k in ('identity_status','identity_reference','identity_start','identity_end')},
            'currency_reference':evidence['currency_reference'],'splits':splits,
            'confirmed_ranges':deepcopy(evidence.get('confirmed_ranges',[])),
            'held_ranges':deepcopy(evidence.get('held_ranges',[])),
            'raw_bars':raw,'bars':bars,'rejected_rows':rejected,'suspensions':[],
            'timestamp_basis':'SESSION_DATE_ONLY_NO_PROVIDER_INTRADAY_TIME','publication_scope':'OWNER_PRIVATE_ONLY'}
    validate_contract(result)
    # Existing chart validator is the OHLCV reader; timestamp is a documented join key.
    chart_bars.normalize({'schema':chart_bars.SOURCE_SCHEMA,'symbol':symbol,'provider':result['source'],
        'interval':'1d','basis':'RAW_CLOSE','timezone':result['timezone'],'currency':currency,
        'exchange':result['exchange'],'read_at':captured,'delay_status':'UNKNOWN',
        'bars':[{'timestamp':int(_stamp(r['date']).timestamp()),'session_date':r['date'],
                 'session_status':'COMPLETE','adjusted_close':None,
                 **{k:None if r[k] is None else float(r[k]) for k in FIELDS[:5]}} for r in raw]})
    return result


def validate_contract(c):
    if c.get('schema') not in (SCHEMA,'retained-daily-price/1') or c.get('basis') not in ('RAW','SPLIT_ADJUSTED') or c.get('currency')!='USD':
        raise ValueError('INVALID_DAILY_CONTRACT')
    _ts(c['collected_at'])
    for key in ('raw_bars','bars'):
        days=[_day(r['date']) for r in c[key]]
        if days!=sorted(set(days)) or any(not schedule.is_session(date.fromisoformat(d)) for d in days):
            raise ValueError('INVALID_SESSION_SET')
        for row in c[key]:
            if not re.fullmatch('[0-9a-f]{64}',row.get('source_sha256','')):raise ValueError('ROW_SOURCE_HASH_REQUIRED')
            if _ts(row['collected_at'])>_ts(c['collected_at']):raise ValueError('ROW_CAPTURE_AFTER_HEADER')
            close=session_close(date.fromisoformat(row['date'])).close_at
            if close is None or close>_ts(row['collected_at']):raise ValueError('INCOMPLETE_SESSION_AT_CAPTURE')
            for f in FIELDS:_decimal(row.get(f),zero=f in ('volume','amount'))
            values=[_decimal(row.get(k)) for k in ('open','high','low','close')]
            o,h,l,cl=values
            if all(v is not None for v in values) and not l<=min(o,cl)<=max(o,cl)<=h:raise ValueError('OHLC_INCONSISTENT')
            if row.get('corrected') is not None and type(row['corrected']) is not bool:raise ValueError('INVALID_CORRECTION_STATUS')
    if [r['date'] for r in c['bars']]!=[r['date'] for r in c['raw_bars']]:raise ValueError('BASIS_SESSION_MISMATCH')
    if c['price_basis_date']!=(c['bars'][-1]['date'] if c['bars'] else None):raise ValueError('BASIS_DATE_MISMATCH')
    splits=c['splits']
    if len({s['date'] for s in splits})!=len(splits):raise ValueError('DUPLICATE_SPLIT')
    for split in splits:
        _decimal(split['ratio'],nullable=False)
        if not split.get('evidence') or split.get('status')!='CONFIRMED':raise ValueError('SPLIT_EVIDENCE_REQUIRED')
        if not c['price_basis_date'] or _day(split['date'])>c['price_basis_date']:raise ValueError('SPLIT_AFTER_BASIS_DATE')
    if c['basis']=='SPLIT_ADJUSTED' and c.get('dividend_adjustment')!='NONE':
        raise ValueError('SPLIT_ONLY_ADJUSTMENT_REQUIRED')
    if c['basis']=='SPLIT_ADJUSTED' and c['bars']!=_split_adjust(c['raw_bars'],splits):
        raise ValueError('ADJUSTED_ROWS_DO_NOT_MATCH_CONFIRMED_SPLITS')
    for r in c['confirmed_ranges']+c['held_ranges']:
        if _day(r['from'])>_day(r['to']):raise ValueError('INVALID_EVIDENCE_RANGE')


def _status(c, evaluation_day):
    _day(evaluation_day)
    return 'MISSING' if not c['price_basis_date'] else 'STALE' if c['price_basis_date']<evaluation_day else 'NORMAL'


def analyze(c, *, evaluation_day):
    validate_contract(c);_day(evaluation_day)
    rows=price_rows(c,evaluation_day)
    end=rows[-1]['date'] if rows else evaluation_day
    if not schedule.is_session(date.fromisoformat(end)):end=schedule.previous_session(date.fromisoformat(end)).isoformat()
    evidence={**c['identity'],'security_id':c['security_id'],'currency':c['currency'],'currency_reference':c['currency_reference']}
    # Pass the widest evidenced interval ending at this observation to the shared
    # kernel. It checks each rolling/recursive window separately; requiring the
    # full retained seed here incorrectly suppresses already-proven short windows.
    ranges=sorted((r for r in c['confirmed_ranges'] if rows and _covers(r,end,end)),key=lambda r:r['from'])
    if ranges:evidence.update(no_split_start=ranges[0]['from'],no_split_end=ranges[0]['to'],no_split_reference=ranges[0]['evidence'])
    basis_evidence(evidence,c)
    normalized=[{'date':r['date'],**{f:r[f] for f in FIELDS[:5]},'returned_symbol':c['symbol'],'requested_symbol':c['symbol'],
                 'price_basis':c['basis'],'asof':'-','source_timestamp':_stamp(r['date']).isoformat(),
                 'source_sha256':r['source_sha256'],'quality_reasons':[]} for r in rows]
    result=measure_display(normalized,signal_day=end,series_id=c['symbol'],symbol=c['symbol'],evidence=evidence,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    for metric in result['metrics'].values():
        a,b=metric['window_start'],metric['window_end'];reasons=metric['null_reasons']
        if not (c['identity'].get('identity_start','9999') or '9999')<=a<=b<=(c['identity'].get('identity_end','0000') or '0000'):reasons.append('IDENTITY_RANGE_UNCONFIRMED')
        if any(a<=r['to'] and r['from']<=b for r in c['held_ranges']):reasons.append('HELD_RANGE_IN_WINDOW')
        if c['basis']=='RAW' and any(a<s['date']<=b for s in c['splits']):reasons.append('CORPORATE_ACTION_IN_RAW_WINDOW')
        if not any(_covers(r,a,b) for r in c['confirmed_ranges']):reasons.append('ACTION_BASIS_UNCONFIRMED')
        metric['null_reasons']=list(dict.fromkeys(reasons))
        if reasons:metric['value']=None
    for obj in (result['volume_latest'], result['volume_note']):
        obj['null_reasons'].append('VOLUME_SCOPE_UNCONFIRMED')
    result['volume_latest']['value']=None
    result['volume_note']['state']=None
    result.update(schema=SCHEMA+'/analysis',status=_status({'price_basis_date':end if rows else None},evaluation_day),data_asof=end if rows else None,
                  evaluation_day=evaluation_day,collected_at=c['collected_at'],corrected_at=c['corrected_at'],
                  historical_available_at=None,diagnostic_basis=c['basis'],chart_basis=c['basis'],
                  raw_count=sum(m['raw_value'] is not None for m in result['metrics'].values()),
                  adopted_count=sum(m['value'] is not None for m in result['metrics'].values()),
                  QGV_coverage_change=None,QGV_reason='OFFICIAL_MODEL_UNCHANGED_NOT_RECALCULATED')
    if c.get('update_state') in ('FAILED','PARTIAL'):result['status']='STALE'
    result['update_state']=c.get('update_state','RETAINED_ARCHIVE')
    result['last_success_at']=c.get('last_success_at',c['collected_at'])
    result['readiness']=describe_readiness(result)
    result['readiness'].update(availability_status='RETAINED_CAPTURE',source_available_at=c['collected_at'],stale_status=result['status'])
    return result


def value_positions(contracts, positions, *, evaluation_day, cash, currency):
    """Value user-supplied same-day quantities through the existing ledger; no orders."""
    def blocked(reason):return {'state':'NOT_COMPUTED','snapshot':None,'reason':reason,'orders_created':0}
    if not positions:return blocked('HOLDINGS_NOT_PROVIDED')
    for c in contracts:validate_contract(c)
    by_id={c['security_id']:c for c in contracts if c['security_id']}
    if len(by_id)!=sum(bool(c['security_id']) for c in contracts):return blocked('DUPLICATE_SECURITY')
    if len({p['security_id'] for p in positions})!=len(positions):return blocked('DUPLICATE_POSITION')
    ledger=Ledger(scenario='LOSS',initial_cash=Decimal(1));ledger.cash=_decimal(cash,zero=True,nullable=False)
    ledger.begin_session(date.fromisoformat(evaluation_day));marks={}
    for p in positions:
        c=by_id.get(p['security_id'])
        if c is None:return blocked('FIXED_SECURITY_LINK_REQUIRED')
        if p['currency']!=currency or c['currency']!=currency:return blocked('CURRENCY_MISMATCH')
        if p['quantity_basis_date']!=evaluation_day:return blocked('QUANTITY_DATE_MISMATCH')
        identity=c['identity']
        if identity.get('identity_status')!='CONFIRMED' or not identity.get('identity_reference') or not (identity.get('identity_start') or '9999')<=evaluation_day<=(identity.get('identity_end') or '0000'):return blocked('IDENTITY_UNCONFIRMED')
        if any(r['from']<=evaluation_day<=r['to'] for r in c['held_ranges']):return blocked('HELD_RANGE')
        r=next((r for r in c['raw_bars'] if r['date']==evaluation_day),None)
        if not r or r['close'] is None:return blocked('SAME_DAY_RAW_CLOSE_REQUIRED')
        ledger.holdings[p['security_id']]=_decimal(p['quantity'],zero=True,nullable=False)
        marks[p['security_id']]=PriceRow(None,Decimal(r['close']))
    ledger.observe(marks)
    return {'state':'CALCULATED','snapshot':ledger.snapshot(),'reason':None,'orders_created':len(ledger.fills),
            'result_kind':'SUPPLIED_HOLDINGS_MARK_ONLY','currency':currency,'evaluation_day':evaluation_day}


def compare(left, right, *, start, end):
    if left['symbol']!=right['symbol'] or left['currency']!=right['currency']:raise ValueError('COMPARISON_IDENTITY_OR_CURRENCY_MISMATCH')
    start=_day(start);end=_day(end)
    if start>end:raise ValueError('COMPARISON_WINDOW_INVALID')
    # Shared helper uses the approved NYSE calendar, including exceptional closures.
    from .exp_deciles.technical_measures import sessions
    expected=sessions(date.fromisoformat(start),date.fromisoformat(end))
    def one(c):
        cropped=deepcopy(c)
        for k in ('bars','raw_bars'):cropped[k]=[r for r in c[k] if start<=r['date']<=end]
        cropped['price_basis_date']=cropped['bars'][-1]['date'] if cropped['bars'] else None
        r=analyze(cropped,evaluation_day=end)
        return {'expected_sessions':len(expected),'valid_close_sessions':sum(x['close'] is not None for x in cropped['raw_bars']),
                'latest_session':r['data_asof'],'raw_indicators':r['raw_count'],'adopted_indicators':r['adopted_count'],
                'collected_at':c['collected_at'],'status':r['status']}
    return {'same_security_confirmed':bool(left.get('security_id') and left['security_id']==right.get('security_id')),
            'ticker_match_only':not bool(left.get('security_id') and left['security_id']==right.get('security_id')),
            'start':start,'end':end,'left':one(left),'right':one(right),'QGV_coverage_change':None}


def merge_update(previous, incoming, *, evaluation_day, failure=None):
    validate_contract(previous)
    if incoming is None:
        kept=deepcopy(previous);kept['update_state']='FAILED';kept['last_success_at']=previous.get('last_success_at',previous['collected_at'])
        return {'data':kept,'status':'STALE','failure':failure or 'NO_INCOMING_DATA','revised_dates':[],'update_state':'FAILED'}
    validate_contract(incoming)
    for k in ('symbol','security_id','currency','exchange','basis','splits','confirmed_ranges','held_ranges','identity','source','session_scope','price_scope_status'):
        if previous[k]!=incoming[k]:raise ValueError('UPDATE_METADATA_REVIEW_REQUIRED')
    if _ts(incoming['collected_at'])<=_ts(previous['collected_at']):raise ValueError('OLDER_OR_DUPLICATE_CAPTURE')
    merged=deepcopy(incoming);revised=set()
    for key in ('bars','raw_bars'):
        old={r['date']:r for r in previous[key]};new={r['date']:r for r in incoming[key]}
        revised.update(d for d in new if d in old and any(new[d].get(f)!=old[d].get(f) for f in (*FIELDS,'corrected')));old.update(new);merged[key]=[old[d] for d in sorted(old)]
    merged['price_basis_date']=merged['bars'][-1]['date'] if merged['bars'] else None
    merged['lineage']={'previous_source_sha256':previous['source_sha256'],'incoming_source_sha256':incoming['source_sha256'],'prior_collected_at':previous['collected_at']}
    from .exp_deciles.technical_measures import sessions
    query=incoming.get('source_query',{}).get('BYMD',evaluation_day.replace('-',''))
    requested_end=min(datetime.strptime(query,'%Y%m%d').date().isoformat(),evaluation_day)
    present={r['date'] for r in incoming['bars']}
    expected=sessions(date.fromisoformat(incoming['bars'][0]['date'] if incoming['bars'] else requested_end),date.fromisoformat(requested_end))
    missing=sorted(set(expected)-present)
    failed=bool(incoming.get('rejected_rows')) or not incoming['bars'] or bool(missing)
    merged['missing_requested_sessions']=missing
    merged['update_state']='PARTIAL' if failed and incoming['bars'] else 'FAILED' if failed else 'UPDATED'
    merged['last_success_at']=previous.get('last_success_at',previous['collected_at']) if failed else incoming['collected_at']
    return {'data':merged,'status':'STALE' if failed else _status(merged,evaluation_day),
            'failure':('REJECTED_INCOMING_ROWS' if incoming.get('rejected_rows') else 'REQUESTED_SESSION_MISSING') if failed else None,'revised_dates':sorted(revised),'update_state':merged['update_state']}


def retained_baseline(rows, *, symbol, source, currency_reference, evidence=None):
    """Bridge already normalized provider rows for a same-window offline comparison."""
    e=evidence or {};rows=sorted(rows,key=lambda r:r['date'])
    if not rows:raise ValueError('BASELINE_ROWS_REQUIRED')
    if any(r.get('price_basis')!='RAW' or r.get('returned_symbol')!=symbol or r.get('asof')!='-' for r in rows):
        raise ValueError('BASELINE_IDENTITY_OR_BASIS')
    if any(r.get('quality_reasons') for r in rows):raise ValueError('BASELINE_ROW_QUALITY')
    bars=[{'date':r['date'],**{f:None if r.get(f) is None else str(r[f]) for f in FIELDS[:5]},
           'vwap':r.get('vwap'),'trade_count':r.get('trade_count'),
           'amount':None,'corrected':None,'source_sha256':r['source_sha256'],'collected_at':r['acquired_at']} for r in rows]
    result={'schema':'retained-daily-price/1','symbol':symbol,'source':source,'currency':'USD','exchange':e.get('exchange','NASDAQ'),
            'security_id':e.get('security_id'),'issuer_id':e.get('issuer_id'),'basis':'RAW',
            'price_basis_date':rows[-1]['date'],'collected_at':max(r['acquired_at'] for r in rows),
            'corrected_at':None,'historical_available_at':None,'calendar':'NYSE','timezone':'America/New_York',
            'source_sha256':rows[0]['source_sha256'],'source_pages':sorted({r['source_sha256'] for r in rows}),
            'identity':{k:e.get(k) for k in ('identity_status','identity_reference','identity_start','identity_end')},
            'currency_reference':currency_reference,'price_scope_status':'PROVIDER_REPORTED','session_scope':'PROVIDER_DAILY',
            'splits':e.get('splits',[]),'confirmed_ranges':e.get('confirmed_ranges',[]),'held_ranges':e.get('held_ranges',[]),
            'raw_bars':deepcopy(bars),'bars':bars}
    validate_contract(result);return result
