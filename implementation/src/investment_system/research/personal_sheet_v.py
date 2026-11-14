"""Current personal price adapter; no network, ledger writes or official publication.

prepare_personal returns sensitive calculation inputs in RAM. personal_result and
its page/group projections contain no quoted prices. Only synthetic fixtures may
be saved by the accompanying CLI. Formulae and scoring remain existing kernels.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from ..qgv import qgv2_inputs, qgv_v2
from ..qgv.dcf_parameters import load_default_dcf_parameters
from . import qgv_555 as engine
from .qgv_555_central_v import reported_raw, _history
from .sector_qgv import digest, timestamp
from .dual_qgv import json_bytes, _rank_factors
from .sector_qgv_registry import CATALOG
from .dual_qgv_delivery import MAX_BYTES

SCHEMA='personal-sheet-v-request/1'
NAMESPACE='PERSONAL_SHEET_V'
VERSION='personal-sheet-price/1'
KEYS=tuple('central::'+k for k in ('ebit_yield','fcf_yield','own_history','gap'))
SOURCES={'GOOGLEFINANCE':'GOOGLEFINANCE_CURRENT','IEX_HIST':'IEX_LAST_REGULAR_SESSION_TRADE'}
NY=ZoneInfo('America/New_York')


def _need(ok, reason):
    if not ok:raise ValueError(reason)


def _finite(v):return type(v) in (int,float) and math.isfinite(v)
def _refs(v):return isinstance(v,list) and bool(v) and all(isinstance(x,str) and x for x in v)


def _stamp(v, reason):
    try:return timestamp(v)
    except (ValueError,TypeError,AttributeError):raise ValueError(reason) from None


def _day(v):
    try:return isinstance(v,str) and date.fromisoformat(v).isoformat()==v
    except ValueError:return False


def _proof(p, cutoff):
    if not isinstance(p,dict) or p.get('status')!='VERIFIED' or not _refs(p.get('source_refs')):return False
    try:return timestamp(p['available_at'])<=cutoff
    except (KeyError,ValueError,TypeError,AttributeError):return False


def _basis(row, wrapped, quote, context, normalized):
    """No kind/ADR conversion or corporate-action multiplier is invented here."""
    b=wrapped.get('basis_evidence') or (quote or {}).get('basis_evidence') or {}
    cutoff=timestamp(context['input_cutoff']);day=context['evaluation_day']
    m=b.get('mapping') or {};s=b.get('share_basis') or {};a=b.get('corporate_actions') or {}
    if (not _proof(m,cutoff) or not m.get('record_id') or
        m.get('company_id')!=row['company_id'] or m.get('issuer_id')!=row.get('issuer_id') or
        not m.get('share_class_id') or not m.get('provider_symbol') or
        (quote and quote.get('provider_symbol')!=m['provider_symbol']) or
        (row.get('security_id') and m.get('security_id')!=row['security_id'])):
        return 'IDENTITY_UNCONFIRMED'
    observed=(quote or {}).get('trade_day');earliest=min(day,observed) if _day(observed) else day
    if (not _day(m.get('valid_from')) or m['valid_from']>earliest or
        m.get('valid_to') is not None and (not _day(m['valid_to']) or day>=m['valid_to'])):
        return 'IDENTITY_PERIOD_UNCONFIRMED'
    if (not _proof(s,cutoff) or s.get('definition')!='WEIGHTED_AVERAGE_DILUTED' or
        s.get('share_class_id')!=m['share_class_id']):return 'SHARE_BASIS_UNCONFIRMED'
    source=wrapped['record'].get('v_inputs_v2') or {};sp=(source.get('diluted_shares') or {}).get('period_end')
    if not _day(sp) or s.get('period_end')!=sp or sp>earliest:return 'SHARE_PERIOD_UNCONFIRMED'
    if (not _proof(a,cutoff) or not _day(a.get('from_day')) or a['from_day']>sp or
        not _day(a.get('through_day')) or a['through_day']<day or
        a.get('basis') not in ('NO_ACTIONS_DOCUMENTED','ALREADY_NORMALIZED')):
        return 'CORPORATE_ACTION_BASIS_UNCONFIRMED'
    if m.get('security_type')=='ADR':
        adr=b.get('adr') or {}
        if (not _proof(adr,cutoff) or not _finite(adr.get('underlying_per_receipt')) or
            adr['underlying_per_receipt']<=0 or s.get('unit')!='ADR_RECEIPTS' or
            adr.get('normalized_share_unit')!='ADR_RECEIPTS' or
            not _day(adr.get('valid_from')) or adr['valid_from']>earliest or
            adr.get('valid_to') is not None and (not _day(adr['valid_to']) or day>=adr['valid_to'])):return 'ADR_RATIO_UNCONFIRMED'
    elif m.get('security_type')!='COMMON_STOCK' or s.get('unit')!='COMMON_SHARES':
        return 'SHARE_CLASS_BASIS_UNCONFIRMED'
    return None


def _quote(q, row, context):
    m=dict(status='MISSING',price_timestamp=None,trade_day=None,received_at=None,price_age_at_evaluation_seconds=None,
        query_started_at=None,currency=None,source_refs=[],
        time_status='UNCONFIRMED',actual_delay_seconds=None,freshness='UNDETERMINED',
        provider=context['provider'],price_definition=context['price_definition'],
        adjustment_status='UNKNOWN',provider_delay_notice='UP_TO_20_MINUTES' if context['provider']=='GOOGLEFINANCE' else None,
        reasons=[],price_available=False,qualified=False,exact_eod=False)
    if q is None:m['reasons']=['MISSING'];return None,m
    for k in ('status','price_timestamp','trade_day','received_at','time_status','adjustment_status'):
        if k in q:m[k]=q[k]
    for k in ('currency','query_started_at','source_refs','provider','price_definition'):
        m[k]=deepcopy(q.get(k))
    if q.get('provider')!=context['provider'] or q.get('price_definition')!=context['price_definition']:
        m['reasons']=['PRICE_DEFINITION_MISMATCH'];return None,m
    if q.get('company_id')!=row['company_id'] or q.get('issuer_id')!=row.get('issuer_id'):
        m['reasons']=['IDENTITY_UNCONFIRMED'];return None,m
    if q.get('status') not in ('AVAILABLE','MISSING','READ_FAILED','INVALID','NO_TRADE'):
        m['reasons']=['PRICE_STATUS_INVALID'];return None,m
    try:
        received=_stamp(q.get('received_at'),'PRICE_RECEIPT_TIME')
        started=_stamp(q.get('query_started_at'),'PRICE_QUERY_TIME')
        _need(started<=received<=timestamp(context['input_cutoff']),'PRICE_AFTER_CUTOFF')
    except ValueError as ex:m['reasons']=[str(ex)];return None,m
    if q['status']!='AVAILABLE':m['reasons']=[q['status']];return None,m
    if not _finite(q.get('price')) or q['price']<=0:m['reasons']=['INVALID_PRICE'];return None,m
    if not _refs(q.get('source_refs')):m['reasons']=['PRICE_SOURCE_UNCONFIRMED'];return None,m
    m['price_available']=True
    if not _day(q.get('trade_day')):m['reasons']=['PRICE_DAY_UNCONFIRMED'];return None,m
    if q['trade_day']>context['evaluation_day']:m['reasons']=['FUTURE_PRICE_DAY'];return None,m
    if q.get('time_status')=='CONFIRMED':
        try:
            t=_stamp(q.get('price_timestamp'),'PRICE_TIME_INVALID')
            _need(t<=received and t.astimezone(NY).date().isoformat()==q['trade_day'],'PRICE_TIME_INVALID')
        except ValueError as ex:m['reasons']=[str(ex)];return None,m
        m['actual_delay_seconds']=(received-t).total_seconds()
        m['price_age_at_evaluation_seconds']=(timestamp(context['evaluated_at'])-t).total_seconds()
        m['delay_definition']='RECEIPT_MINUS_PRICE_TIME_NOT_PROVIDER_FEED_LATENCY'
        if context['provider']=='GOOGLEFINANCE':m['freshness']='DELAYED' if m['price_age_at_evaluation_seconds']>1200 else 'WITHIN_PROVIDER_NOTICE'
    elif q.get('time_status') in ('UNCONFIRMED','DATE_ONLY'):
        if q.get('price_timestamp') is not None:m['reasons']=['UNCONFIRMED_TIME_HAS_TIMESTAMP'];return None,m
    else:m['reasons']=['PRICE_TIME_STATUS_INVALID'];return None,m
    if q.get('adjustment_status')!='AS_TRADED':m['reasons']=['PRICE_ADJUSTMENT_UNCONFIRMED'];return None,m
    if not isinstance(q.get('currency'),str) or len(q['currency'])!=3:
        m['reasons']=['CURRENCY_BASIS_UNCONFIRMED'];return None,m
    return dict(price=q['price'],currency=q['currency']),m


def _entry(row, snapshot, wrapped, q, context, c, params):
    r=engine.financial_peer_context(c,engine.calculation_row(c,row),snapshot)
    supported,support_reason=engine._row_support(c,r)
    if not row.get('issuer_id'):supported=False;support_reason='ISSUER_ID_UNCONFIRMED'
    class_ok=c['candidate']!='S1-555' or engine.classification_peer_verified(c,r,snapshot)
    if not class_ok:supported=False;support_reason='CLASSIFICATION_PERIOD_UNCONFIRMED'
    roles=deepcopy(c['financial_roles'] if engine._financial_enabled(c,r) else c['roles'])
    if c['candidate']=='S1-555' and not engine._financial_enabled(c,r):
        roles.update(c.get('scoped_role_overrides',{}).get(str(r.get('sector_id'))+'|'+str(r.get('accounting_template')),{}))
    quote,meta=_quote(q,row,context);reasons={};normalized=None;periods={};source_reason=None;nonprice={k:False for k in KEYS};period_failures={}
    profile=(wrapped or {}).get('record',{}).get('profile')
    if not row.get('issuer_id'):source_reason='ISSUER_ID_UNCONFIRMED'
    elif not wrapped:source_reason='RETAINED_FINANCIAL_NOT_LINKED'
    else:
        record=wrapped['record'];owner=row.get('owner_source_context') or {}
        _need(record.get('calc_version')=='qgv2-calc/2026-10-23.1' and digest(record)==owner.get('record_hash') and
            record.get('cik')==row.get('issuer_id') and _refs(wrapped.get('source_refs')) and
            all(owner.get(k)==record.get(k) for k in ('acquired_at','fiscal_year_end','currency','calc_version')),'PERSONAL_FINANCIAL_ANCHOR')
        _need(owner.get('profile') is None or owner['profile']==record.get('profile'),'PERSONAL_FINANCIAL_PROFILE')
        _need(_stamp(record.get('acquired_at'),'FINANCIAL_AVAILABLE_TIME')<=timestamp(context['input_cutoff']),'FINANCIAL_AFTER_CUTOFF')
        normalized,periods=qgv2_inputs._v_inputs(record.get('v_inputs_v2'))
        if normalized:
            def period_ok(key):
                p=periods.get(key);p=p.split(' ')[-1] if isinstance(p,str) else None
                return _day(p) and p<=context['evaluation_day']
            if not period_ok('total_debt') or not period_ok('cash_and_equivalents'):
                period_failures.update({k:'EV_COMPONENT_PERIOD_UNCONFIRMED' for k in KEYS[:2]})
            if not period_ok('ebit'):period_failures.update({'central::ebit_yield':'EBIT_PERIOD_UNCONFIRMED','central::own_history':'EBIT_PERIOD_UNCONFIRMED'})
            if not period_ok('fcf'):period_failures.update({'central::fcf_yield':'FCF_PERIOD_UNCONFIRMED','central::gap':'FCF_PERIOD_UNCONFIRMED'})
            source_reason=_basis(row,wrapped,q,context,normalized)
            if source_reason:meta['reasons'].append(source_reason)
            if quote and (quote['currency']!=record.get('currency') or quote['currency']!=normalized.get('currency')):
                meta['reasons'].append('CURRENCY_BASIS_UNCONFIRMED');quote=None
            if not source_reason and profile!='FINANCIAL':
                shares=qgv_v2.positive(normalized.get('diluted_shares'))
                ev=all(_finite(normalized.get(k)) and normalized[k]>=0 for k in ('total_debt','cash'))
                nonprice.update({'central::ebit_yield':shares and ev and _finite(normalized.get('ebit')),
                    'central::fcf_yield':shares and ev and _finite(normalized.get('fcf')),
                    'central::own_history':False,  # Whole historical share basis is checked separately below.
                    'central::gap':shares and qgv_v2.positive(normalized.get('fcf')) and _finite(normalized.get('revenue_cagr_3y'))})
                for k in period_failures:nonprice[k]=False
            if source_reason:quote=None
        else:source_reason='V_INPUTS_NOT_AVAILABLE'
        if profile=='FINANCIAL':source_reason='FINANCIAL_PROFILE_V_NOT_DEFINED';quote=None
    if source_reason:
        reasons={k:source_reason for k in KEYS};quote=None
        if source_reason not in meta['reasons']:meta['reasons'].append(source_reason)
    if quote is None:
        reasons={k:reasons.get(k) or (meta['reasons'][0] if meta['reasons'] else 'PRICE_NOT_QUALIFIED') for k in KEYS}
    else:
        try:history,why=_history(q,context['evaluation_day'])
        except ValueError as ex:history=None;why=str(ex)
        if history is not None:
            h=q.get('history_basis_evidence') or {};b=wrapped.get('basis_evidence') or q.get('basis_evidence') or {};m=b.get('mapping') or {}
            used=[x['period_end'] for x in normalized.get('ebit_per_share_history',[]) if
                _finite(x.get('value')) and qgv_v2.month_close(history,x.get('period_end')) is not None]
            valid=(_proof(h,timestamp(context['input_cutoff'])) and bool(h.get('share_class_id')) and h.get('share_class_id')==m.get('share_class_id') and
                h.get('share_basis')=='WEIGHTED_AVERAGE_DILUTED' and h.get('currency')==normalized.get('currency') and
                h.get('basis')=='ALREADY_COMMON_SHARE_BASIS' and _day(h.get('from_day')) and
                (not used or h['from_day']<=min(used)) and _day(h.get('through_day')) and
                h['through_day']>=context['evaluation_day'])
            if not valid:history=None;why='HISTORY_PRICE_SHARE_BASIS_UNVERIFIED'
            else:nonprice['central::own_history']=len(used)>=qgv_v2.MIN_HISTORY and qgv_v2.positive(normalized.get('diluted_shares')) and _finite(normalized.get('ebit'))
        if history is not None:quote['month_closes']=history
        else:reasons['central::own_history']=why
        meta['qualified']=True
    raw={k:None for k in KEYS}
    if wrapped and quote is not None:
        _,_,values=reported_raw(wrapped['record'],quote,params)
        for key in KEYS:
            name=key.split('::')[1];raw[key]=values[name]
            if raw[key] is not None:reasons.pop(key,None)
            else:reasons.setdefault(key,values['reasons'].get(name,'RAW_MISSING'))
    for k,why in period_failures.items():raw[k]=None;reasons[k]=why
    weights=c['axis_weights'] if c['candidate']=='U1-555' else c.get('sector_axis_overrides',{}).get(r.get('sector_id'),dict(zip('QGV',engine.SECTORS.get(r.get('sector_id'),(34,33,33)))))
    basis=(wrapped or {}).get('basis_evidence') or (q or {}).get('basis_evidence') or {}
    allowed=('status','record_id','company_id','issuer_id','security_id','share_class_id','provider_symbol','currency','share_basis',
        'security_type','valid_from','valid_to','available_at','source_refs','definition','period_end','unit',
        'from_day','through_day','basis','underlying_per_receipt','normalized_share_unit')
    provenance=dict(financial=dict(record_hash=(row.get('owner_source_context') or {}).get('record_hash'),
        companyfacts_sha256=(row.get('owner_source_context') or {}).get('companyfacts_sha256'),
        source_refs=deepcopy((wrapped or {}).get('source_refs',[])),
        **{k:(wrapped or {}).get('record',{}).get(k) for k in ('acquired_at','currency','fiscal_year_end','calc_version')}),
        basis={k:{f:deepcopy(v[f]) for f in allowed if f in v} for k,v in basis.items() if k in ('mapping','share_basis','corporate_actions','adr') and isinstance(v,dict)})
    h=(q or {}).get('history_basis_evidence') or {}
    provenance['history']={f:deepcopy(h[f]) for f in allowed if f in h}
    provenance['history_source_refs']=deepcopy((q or {}).get('history_source_refs',[]))
    return dict(company_id=row['company_id'],issuer_id=row.get('issuer_id'),industry_group=r.get('industry_group'),
        sector_id=r.get('sector_id'),accounting_template=r.get('accounting_template'),supported=supported,
        support_reason=support_reason,reference_included=bool(r.get('issuer_id')) and
            (r.get('accounting_template')=='GENERAL' or engine._financial_enabled(c,r)) and class_ok,
        ranking_scope='COMMON' if c['candidate']=='U1-555' else 'SECTOR|'+str(r.get('sector_id'))+'|'+str(r.get('accounting_template')),
        company=dict(profile=profile,v_inputs=normalized),quote=quote,raw=raw,raw_reasons=reasons,price_metadata=meta,
        financial_periods=periods,provenance=provenance,nonprice=nonprice,axis_weights=weights,
        roles={k:v for k,v in roles.items() if k.startswith('v_')})


def prepare_personal(request,evaluation,reference,financial_records,prices,*,expected_evaluation,expected_reference):
    _need(request.get('schema_version')==SCHEMA,'PERSONAL_REQUEST_SCHEMA')
    _need(engine.identity(evaluation)==expected_evaluation,'PERSONAL_EVALUATION_ANCHOR')
    _need(engine.identity(reference)==expected_reference,'PERSONAL_REFERENCE_ANCHOR')
    c=deepcopy(request['configuration']);engine.validate_configuration(c)
    _need(c['version'] in ('0.2.0','0.3.0','0.4.0','0.5.0'),'PERSONAL_MODEL_VARIANT_UNSUPPORTED')
    context=deepcopy(request['context'])
    _need(set(context)=={'context_id','evaluation_day','evaluated_at','input_cutoff','provider','price_definition'},'PERSONAL_CONTEXT_FIELDS')
    _need(isinstance(context['context_id'],str) and context['context_id'] and _day(context['evaluation_day']),'PERSONAL_CONTEXT')
    now=_stamp(context['evaluated_at'],'PERSONAL_EVALUATION_TIME');cutoff=_stamp(context['input_cutoff'],'PERSONAL_INPUT_CUTOFF')
    _need(cutoff<=now and now.astimezone(NY).date().isoformat()==context['evaluation_day'],'CURRENT_EVALUATION_CONTEXT')
    _need(context['provider'] in SOURCES and SOURCES[context['provider']]==context['price_definition'],'PERSONAL_PRICE_DEFINITION')
    for s in (evaluation,reference):
        _need(s['evaluation_day']==context['evaluation_day'] and timestamp(s['input_cutoff'])==cutoff,'CURRENT_EVALUATION_CONTEXT')
        for row in s['rows']:
            _need(isinstance(row.get('company_id'),str) and bool(row['company_id']),'PERSONAL_COMPANY_ID')
            _need(row.get('issuer_id') is None or isinstance(row['issuer_id'],str) and bool(row['issuer_id']),'PERSONAL_ISSUER_ID')
    known={r['company_id'] for s in (evaluation,reference) for r in s['rows']};quotes={}
    for q in prices:
        cid=q.get('company_id');_need(cid in known,'PERSONAL_PRICE_OUTSIDE_ROSTER');_need(cid not in quotes,'DUPLICATE_PRICE')
        quotes[cid]=q
    try:price_hash=digest(prices)
    except (ValueError,TypeError):raise ValueError('NON_FINITE_OR_INVALID_PRICE_PAYLOAD') from None
    params=load_default_dcf_parameters();ctx=dict(namespace=NAMESPACE,adapter_version=VERSION,context_id=context['context_id'],
        price_snapshot_hash=price_hash,original_evaluation=deepcopy(expected_evaluation),original_reference=deepcopy(expected_reference))
    ev,ref=deepcopy(evaluation),deepcopy(reference);entries={}
    for label,s in (('evaluation',ev),('reference',ref)):
        s['personal_sheet_context']=deepcopy(ctx);entries[label]=[]
        for row in s['rows']:
            entry=_entry(row,s,financial_records.get(row['company_id']),quotes.get(row['company_id']),context,c,params)
            entries[label].append(entry)
            row.update(personal_reference_included=entry['reference_included'],personal_support_reason=entry['support_reason'])
            # Every price-dependent old V observation is removed, including custom variants.
            for key,spec in engine.catalog().items():
                if spec['axis']=='V':
                    row.setdefault('metrics',{}).pop(key,None);row.setdefault('metric_evidence',{}).pop(key,None)
            for key,value in entry['raw'].items():
                if value is None:continue
                row['metrics'][key]=value
                row['metric_evidence'][key]=dict(status='VERIFIED',variant=key.split('::')[1]+'/central-wad-reported-1',
                    source_refs=['PERSONAL_CURRENT_BASIS_VALIDATED'],available_at=context['input_cutoff'],
                    valuation_day=context['evaluation_day'],share_basis='WEIGHTED_AVERAGE_DILUTED',
                    security_and_actions='VERIFIED',scope=NAMESPACE,adapter_version=VERSION)
    peers={}
    for entry in entries['reference']:
        if not entry['reference_included']:continue
        signature={k:entry[k] for k in ('industry_group','sector_id','accounting_template','ranking_scope','raw')}
        issuer=entry['issuer_id']
        _need(issuer not in peers or peers[issuer]==signature,'PERSONAL_ISSUER_POINT_CONFLICT')
        peers[issuer]=signature
    core=engine.run(c,ev,ref,calculated_at=context['evaluated_at'],calculation_scope=NAMESPACE)
    lookup={r['company_id']:r for r in core['rows']}
    for entry in entries['evaluation']:entry['base_axes']={a:lookup[entry['company_id']]['axes'][a]['score'] for a in 'QG'};entry['gate_status']=lookup[entry['company_id']]['gate_status']
    for entry in entries['reference']:entry.update(base_axes=dict(Q=None,G=None),gate_status='UNKNOWN')
    packet=dict(schema_version='personal-sheet-v-packet/1',namespace=NAMESPACE,context=context,configuration=c,
        configuration_hash=digest(c),evaluation_original=expected_evaluation,reference_original=expected_reference,
        evaluation_effective=engine.identity(ev),reference_effective=engine.identity(ref),
        evaluation=entries['evaluation'],reference=entries['reference'],parameters=params)
    sources=[Path(__file__),Path(engine.__file__),Path(qgv2_inputs.__file__),
        Path(__file__).with_name('qgv_555_central_v.py'),Path(__file__).with_suffix('.js'),
        Path(__file__).parent.parent/'product/web_assets/qgv-v2.js']
    packet['engine_source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    payload=json_bytes(packet).decode();pin=hashlib.sha256(payload.encode()).hexdigest()
    return dict(configuration=c,evaluation=ev,reference=ref,core_result=core,packet=packet,packet_text=payload,
        payload_sha256=pin,price_snapshot_hash=price_hash)


def _rank_metrics(rows):
    slot=next(iter(CATALOG));keys=sorted({k for r in rows for k in r['metrics']})
    for key in keys:
        bridge=[dict(company_id=r['company_id'],ranking_scope=r['ranking_scope'],factors={s:dict(score=r['metrics'].get(key,{}).get('score') if s==slot else None) for s in CATALOG}) for r in rows]
        _rank_factors(bridge)
        for row,b in zip(rows,bridge):
            if key in row['metrics']:row['metrics'][key].update({k:b['factors'][slot][k] for k in ('rank','rank_n','decile','decile_status')})


def personal_result(prepared):
    core=prepared['core_result'];packet=prepared['packet'];_need(core.get('namespace')==NAMESPACE,'PERSONAL_RESULT_SCOPE')
    _need(core['result_hash']==digest({k:v for k,v in core.items() if k!='result_hash'}),'PERSONAL_CORE_HASH')
    rows=[];raw_entries={e['company_id']:e for e in packet['evaluation']}
    fields=('metric','raw','score','reason','reference_n','reference_scope','weight')
    for row in core['rows']:
        entry=raw_entries[row['company_id']];roles={};metrics={}
        for name,role in row['roles'].items():
            if not name.startswith('v_'):continue
            items=[]
            for x in role['metrics']:
                m={k:deepcopy(x.get(k)) for k in fields}
                if x['raw'] is None and row['status']=='READY' and x['weight']>0:
                    m['reason']=entry['raw_reasons'].get(x['metric'],x['reason']) if x['metric'] in KEYS else 'PERSONAL_VARIANT_NOT_CONNECTED'
                items.append(m);metrics[name+'|'+x['metric']]=deepcopy(m)
            roles[name]=dict(score=role['score'],metrics=items,**{k:role[k] for k in ('rank','rank_n','decile','decile_status')})
        rows.append(dict(company_id=row['company_id'],issuer_id=row['issuer_id'],ranking_scope=row['ranking_scope'],
            raw=deepcopy(entry['raw']),metrics=metrics,roles=roles,
            axes={a:row['axes'][a]['score'] for a in 'QGV'},gate_status=row['gate_status'],total=row['total'],
            partial_total=row['partial_total'],rank=row['rank'],rank_n=row['rank_n'],
            price_metadata=deepcopy(entry['price_metadata']),financial_periods=deepcopy(entry['financial_periods']),
            provenance=deepcopy(entry['provenance'])))
    _rank_metrics(rows)
    for row in rows:
        for key,item in row['metrics'].items():
            role,metric=key.split('|',1)
            for x in row['roles'][role]['metrics']:
                if x['metric']==metric:x.update({k:item[k] for k in ('rank','rank_n','decile','decile_status')})
    def count(pred):return len({r['issuer_id'] for r in rows if r.get('issuer_id') and pred(r)})
    groups=[]
    for kind in ('roles','metrics'):
        for key in sorted({k for r in rows for k in r[kind]}):
            scopes=defaultdict(list)
            for r in rows:
                if key in r[kind]:scopes[r['ranking_scope']].append(r)
            for scope,rr in sorted(scopes.items()):
                valid=[r for r in rr if r[kind][key]['score'] is not None];bins=Counter(r[kind][key]['decile'] for r in valid)
                gid=digest([prepared['payload_sha256'],core['model_id'],kind,key,scope])
                groups.append(dict(group_id='personal:'+gid,kind=kind,key=key,ranking_scope=scope,minimum_decile_n=10,
                    evaluation_valid_n=len(valid),original_code_rows=len(rr),unit='CODE_ROW',
                    bins=[dict(decile=d,count=bins[d],top_percent_from=(10-d)*10,top_percent_to=(11-d)*10) for d in range(10,0,-1)]))
    variants={k:dict(nonprice_complete=len({e['issuer_id'] for e in packet['evaluation'] if e['issuer_id'] and e['nonprice'][k]}),
        minimum_reference_n=0 if k=='central::own_history' else packet['configuration']['minimum'],
        minimum_history_values=qgv_v2.MIN_HISTORY if k=='central::own_history' else None,
        raw=count(lambda r:r['raw'][k] is not None),score=count(lambda r:any(m['metric']==k and m['score'] is not None for m in r['metrics'].values()))) for k in KEYS}
    counts=dict(price_available=count(lambda r:r['price_metadata']['price_available']),
        price_qualified=count(lambda r:r['price_metadata']['qualified']),
        nonprice_any=len({e['issuer_id'] for e in packet['evaluation'] if e['issuer_id'] and any(e['nonprice'].values())}),
        nonprice_all=len({e['issuer_id'] for e in packet['evaluation'] if e['issuer_id'] and all(e['nonprice'].values())}),
        raw_any=count(lambda r:any(v is not None for v in r['raw'].values())),
        raw_all=count(lambda r:all(v is not None for v in r['raw'].values())),
        role_any=count(lambda r:any(v['score'] is not None for v in r['roles'].values())),
        V_axis=count(lambda r:r['axes']['V'] is not None),
        personal_partial_total=count(lambda r:r['total'] is not None and r['partial_total']),
        personal_eligible_total=count(lambda r:r['total'] is not None and not r['partial_total']))
    out=dict(schema_version='personal-sheet-v-result/1',namespace=NAMESPACE,storage='EPHEMERAL_ONLY',
        model_id=core['model_id'],configuration_hash=packet['configuration_hash'],context=packet['context'],
        engine_source_sha256=deepcopy(packet['engine_source_sha256']),
        evaluation=packet['evaluation_original'],reference=packet['reference_original'],
        evaluation_effective=packet['evaluation_effective'],reference_effective=packet['reference_effective'],
        calculation_input_sha256=prepared['payload_sha256'],price_snapshot_hash=prepared['price_snapshot_hash'],
        formula_version='qgv2-calc/2026-10-23.1/REPORTED_WAD_RAW;555_SCORING',denominator=dict(code_rows=len(rows),issuers=len({r['issuer_id'] for r in rows if r['issuer_id']})),
        counts=counts,counts_unit='UNIQUE_ISSUER',variants=variants,rows=rows,groups=groups,official=False,filter_recalculates=False,
        comparison_scope='PERSONAL_SESSION_NOT_OFFICIAL_RANK',research_coverage_claim=False,
        rank_policy='STORED_DUAL_ORDINAL_SCORE_DESC_CODE_ASC',tie_policy='EXISTING_FIXED_COUNT_BINS_WITH_REPORTED_TIE_SPLITS')
    out['result_hash']=digest(out);return out


def _checked(result):_need(result.get('namespace')==NAMESPACE and result.get('result_hash')==digest({k:v for k,v in result.items() if k!='result_hash'}),'PERSONAL_RESULT_HASH')


def personal_page(result,*,offset=0,limit=20,company_ids=None):
    _checked(result);_need(type(offset) is int and offset>=0 and type(limit) is int and 1<=limit<=50,'PERSONAL_PAGE_RANGE')
    rows=result['rows'] if company_ids is None else [r for r in result['rows'] if r['company_id'] in company_ids]
    out={k:deepcopy(v) for k,v in result.items() if k not in ('rows','groups','result_hash')}
    out.update(schema_version='personal-sheet-v-page/1',source_result_hash=result['result_hash'],rows=deepcopy(rows[offset:offset+limit]),
        offset=offset,filtered_rows=len(rows),next_offset=offset+limit if offset+limit<len(rows) else None)
    _need(len(json_bytes(out))<=MAX_BYTES,'PERSONAL_PAGE_SIZE');return out


def personal_group_page(result,group_id,*,decile=None,offset=0,limit=50):
    _checked(result);_need(type(offset) is int and offset>=0 and type(limit) is int and 1<=limit<=50,'PERSONAL_PAGE_RANGE')
    groups=[g for g in result['groups'] if g['group_id']==group_id];_need(len(groups)==1,'PERSONAL_GROUP_ID')
    g=groups[0];_need(decile is None or type(decile) is int and 1<=decile<=10,'PERSONAL_DECILE')
    rows=[r for r in result['rows'] if r['ranking_scope']==g['ranking_scope'] and g['key'] in r[g['kind']] and
        (decile is None or r[g['kind']][g['key']]['decile']==decile)]
    rows.sort(key=lambda r:(r[g['kind']][g['key']]['rank'] is None,r[g['kind']][g['key']]['rank'] or 0,r['company_id']))
    out=dict(schema_version='personal-sheet-v-group-page/1',namespace=NAMESPACE,group=deepcopy(g),
        denominator=deepcopy(result['denominator']),source_result_hash=result['result_hash'],filter_recalculates=False,
        decile=decile,rows=[dict(company_id=r['company_id'],issuer_id=r['issuer_id'],**r[g['kind']][g['key']]) for r in rows[offset:offset+limit]],
        next_offset=offset+limit if offset+limit<len(rows) else None)
    _need(len(json_bytes(out))<=MAX_BYTES,'PERSONAL_PAGE_SIZE');return out
