"""Offline current-expansion evidence pipeline; no publication or supplier calls.

An observed SEC ticker row is a discovery row, never a listing interval or security ID.
Current nominal rules are separate from the historical real-dollar C2 experiment.
The common official engine is called only after the entire supplied selection population
is established. Uncollected financial rows remain in that population and denominator.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, date, timezone
import math
import re
from types import SimpleNamespace

from ..universe import sec_qgv2 as sec
from ..qgv import v2_factors as vf, v2_scoring as vs, qgv2_inputs as qi, qgv_official as official
from ..qgv.type_config import load_official_type_config

VERSION = 'U-US-EXPANDED-CURRENT/1'
POLICY = {'version':'current-nominal-20261031/1', 'entry_market_cap_usd':250_000_000,
          'retain_market_cap_usd':200_000_000, 'entry_price_usd':5, 'retain_price_usd':3,
          'adv_gate':'DEFERRED', 'rebalance':'MONTH_END', 'representatives':'ONE_PER_ISSUER',
          'official_universe_replaced':False}
INCLUDED = {'COMMON','COMMON_CLASS','ADR','FOREIGN_COMMON','REIT','LP','BDC'}
EXCLUDED = {'ETF','ETN','CLOSED_END_FUND','PREFERRED','WARRANT','RIGHT','UNIT'}
EXCHANGES = {'NYSE','NASDAQ','NYSE_AMERICAN','BATS'}


def _number(v):
    return type(v) in (int,float) and math.isfinite(v)


def _cik(v):
    return str(v).zfill(10) if type(v) in (str,int) and re.fullmatch(r'[0-9]{1,10}',str(v)) and int(v)>0 else None


def _day(v):
    try:return date.fromisoformat(v)
    except (ValueError,TypeError):return None


def _eligible(row, e, basis_date):
    reasons=[];excluded=[]
    if not row['cik'] or e.get('cik')!=row['cik'] or e.get('ticker')!=row['ticker'] or not e.get('source_ref'):
        return 'UNKNOWN',['ISSUER_LINK_UNCONFIRMED'],None
    start,end=_day(e.get('valid_from')),_day(e.get('valid_to'))
    if not start or start>_day(basis_date) or (e.get('valid_to') is not None and (not end or end<_day(basis_date))):
        reasons.append('IDENTITY_DATE_UNCONFIRMED')
    if e.get('basis_date')!=basis_date:reasons.append('EVIDENCE_DATE_MISMATCH')
    for k,reason in [('security_id','SECURITY_ID_UNCONFIRMED'),('issuer_id','ISSUER_ID_UNCONFIRMED')]:
        if not isinstance(e.get(k),str) or not e[k].strip():reasons.append(reason)
    kind=e.get('security_type')
    if kind in EXCLUDED:excluded.append('EXCLUDED_SECURITY_TYPE')
    elif kind not in INCLUDED:reasons.append('SECURITY_TYPE_UNCONFIRMED')
    exchange=e.get('exchange')
    if exchange and exchange not in EXCHANGES:excluded.append('EXCLUDED_EXCHANGE')
    elif not exchange:reasons.append('EXCHANGE_UNCONFIRMED')
    for field,unknown,rejected in [('listed','LISTING_STATUS_UNCONFIRMED','NOT_LISTED'),
                                   ('iex_tradable','IEX_MEMBERSHIP_UNCONFIRMED','NOT_IEX_TRADABLE'),
                                   ('representative','REPRESENTATIVE_UNCONFIRMED','NON_REPRESENTATIVE')]:
        if e.get(field) is False:excluded.append(rejected)
        elif e.get(field) is not True:reasons.append(unknown)
    if e.get('shell_or_spac') is True:excluded.append('SHELL_OR_SPAC')
    elif e.get('shell_or_spac') is not False:reasons.append('SHELL_STATUS_UNCONFIRMED')
    retained=e.get('previous_member') is True
    if retained and not (e.get('previous_membership_ref') and _day(e.get('previous_membership_date'))
                         and e['previous_membership_date']<basis_date):
        reasons.append('PREVIOUS_MEMBERSHIP_UNCONFIRMED')
    cap=e.get('issuer_market_cap_usd')
    if not _number(cap) or cap<=0 or e.get('market_cap_basis')!='ALL_CLASSES':reasons.append('ISSUER_MARKET_CAP_UNCONFIRMED')
    elif cap<POLICY['retain_market_cap_usd' if retained else 'entry_market_cap_usd']:excluded.append('BELOW_MARKET_CAP')
    if e.get('price_date')!=basis_date:reasons.append('PRICE_DATE_MISMATCH')
    if not e.get('security_id') or e.get('quote_security_id')!=e.get('security_id'):reasons.append('PRICE_IDENTITY_MISMATCH')
    p=e.get('price')
    if not _number(p) or p<=0 or e.get('price_currency')!='USD' or e.get('price_basis')!='RAW' or not e.get('price_source_ref'):
        reasons.append('PRICE_BASIS_UNCONFIRMED')
    elif p<POLICY['retain_price_usd' if retained else 'entry_price_usd']:excluded.append('BELOW_PRICE')
    # Exclusion itself needs valid evidence. An old/other-security price cannot
    # remove a candidate and silently change the cross-section denominator.
    identity_ok=not any(r in reasons for r in ('IDENTITY_DATE_UNCONFIRMED','EVIDENCE_DATE_MISMATCH','SECURITY_ID_UNCONFIRMED','ISSUER_ID_UNCONFIRMED'))
    if not identity_ok:
        excluded=[]
    elif any(r in reasons for r in ('PRICE_DATE_MISMATCH','PRICE_IDENTITY_MISMATCH','PRICE_BASIS_UNCONFIRMED','PREVIOUS_MEMBERSHIP_UNCONFIRMED')):
        excluded=[r for r in excluded if r!='BELOW_PRICE']
    if 'PREVIOUS_MEMBERSHIP_UNCONFIRMED' in reasons:
        excluded=[r for r in excluded if r!='BELOW_MARKET_CAP']
    # A confirmed type/listing exclusion needs no irrelevant financial/price input.
    status='EXCLUDED' if excluded else 'UNKNOWN' if reasons else 'ELIGIBLE'
    return status,excluded+reasons,e.get('security_id') if identity_ok else None


def _common_scores(rows, financials, evidence, basis_date):
    records={};lookup={}
    for r in rows:
        if r['eligibility']!='ELIGIBLE':continue
        e=evidence[r['observation_id']];code=e['exchange']+':'+r['ticker']
        if code in records:raise ValueError('DUPLICATE_LISTING_CODE')
        records[code]=deepcopy(financials.get(r['cik']) or sec.empty_record(cik=r['cik']))
        lookup[code]=r
    scores,_=vs.score_rows(records,calc_version=vf.CALC_VERSION)
    volatility=vs.volatility_rank_rows(records,calc_version=vf.CALC_VERSION)
    for code,r in records.items():
        r.update(scores[('universe',code)])
        if volatility[('universe',code)] is not None:r['metrics']['revenue_volatility_5y_rank_pct']=volatility[('universe',code)]
    payload={'records':records,'target':{},'as_of':basis_date+'T23:59:59Z','calc_version':vf.CALC_VERSION}
    inputs=qi.from_inputs(payload);ids=qi.page_identities(inputs);types=load_official_type_config().to_dict()
    companies,_=qi.engine_inputs(inputs,identities=ids,type_config=types)
    ctx={'payload':payload,'inputs':inputs,'companies':companies,'blocked':qi.blocked_codes(inputs,ids),
         'type_config':types,'keys':{c:c for c in records}}
    quotes={c:{'price':evidence[r['observation_id']]['price'],'currency':'USD'} for c,r in lookup.items()}
    day=SimpleNamespace(day=basis_date,quotes=quotes,status={c:'SUPPLIED' for c in quotes})
    months={} # no fabricated V4 history; missing months retain the official reason
    status=official.price_status(ctx,day,months)
    priced,left=official.engine_quotes(ctx,day,status,months)
    results=official.score(ctx,priced)
    projected={c:official.public_row(c,inputs['records'][c],results.get(c),status[c],left.get(c)) for c in records}
    official.assign_ranks(projected)
    for c,r in lookup.items():
        r.update(score=projected[c],rank=projected[c]['rank'],price_status=status[c],calculation_attempted=True)
    return projected


def evaluate(candidates, *, financials, evidence, source, basis_date):
    if not _day(basis_date):raise ValueError('INVALID_BASIS_DATE')
    rows=[]
    for i,c in enumerate(candidates):
        cik=_cik(c.get('cik_str'));oid=str(i)
        r={'observation_id':oid,'ticker':c.get('ticker'),'name':c.get('title'),'cik':cik,'security_id':None,
           'searchable':bool(c.get('ticker')),'score':None,'rank':None,'calculation_attempted':False}
        r['eligibility'],r['reasons'],r['security_id']=_eligible(r,evidence.get(oid,{}),basis_date)
        f=financials.get(cik) or {};r['financial_available']=f.get('state') in ('LIVE','STALE')
        r['financial_reasons']=f.get('reason_codes') or ([] if r['financial_available'] else ['FINANCIAL_NOT_HELD'])
        r['financial_acquired_at']=f.get('acquired_at');r['raw_metrics']=f.get('metrics') or {}
        rows.append(r)
    population_reasons=[]
    if not (source.get('scope')=='IEX_TRADABLE' and source.get('complete') is True and source.get('source_ref')
            and source.get('basis_date')==basis_date):population_reasons.append('COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED')
    if any(r['eligibility']=='UNKNOWN' for r in rows):population_reasons.append('ELIGIBILITY_UNRESOLVED')
    eligible=[r for r in rows if r['eligibility']=='ELIGIBLE']
    ids=[r['security_id'] for r in eligible]
    if len(ids)!=len(set(ids)):population_reasons.append('DUPLICATE_SECURITY_ID')
    issuers=[r['cik'] for r in eligible]
    if len(issuers)!=len(set(issuers)):population_reasons.append('MULTIPLE_ISSUER_REPRESENTATIVES')
    for r in eligible:
        f=financials.get(r['cik'])
        if f and (f.get('cik')!=r['cik'] or (f.get('acquired_at') or '')[:10]>basis_date):
            population_reasons.append('FINANCIAL_IDENTITY_OR_TIME_MISMATCH');break
    projected=_common_scores(rows,financials,evidence,basis_date) if not population_reasons else None
    coverage={'denominator':len(eligible) if not population_reasons else None,
              'Q':None,'G':None,'V':None,'simultaneous':None,'ranked':None,'preset_actual_total':None,'factors':None}
    if projected is not None:
        coverage.update({a:sum(_number(r['axes'][a]['score']) for r in projected.values()) for a in ('Q','G','V')})
        coverage.update(simultaneous=sum(all(_number(r['axes'][a]['score']) for a in ('Q','G','V')) for r in projected.values()),
                        ranked=sum(r['rank'] is not None for r in projected.values()),
                        preset_actual_total=sum(_number(r['total']) for r in projected.values()),
                        factors={k:sum(_number(r['factors'][k]['score']) for r in projected.values()) for k in official.qgv_v2.FACTORS})
    state=Counter(r['eligibility'] for r in rows)
    return {'schema_version':'current-expansion-research/1','visibility':'PRIVATE_RESEARCH','universe_version':VERSION,
            'calc_version':vf.CALC_VERSION,'policy':POLICY.copy(),'basis_date':basis_date,'source':source,
            'full_market_denominator':len(rows) if 'COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED' not in population_reasons else None,
            'population_reasons':population_reasons,'counts':{'candidate_rows':len(rows),'unique_tickers':len({r['ticker'] for r in rows if r['ticker']}),
                'unique_issuers':len({r['cik'] for r in rows if r['cik']}),'financial_rows':sum(r['financial_available'] for r in rows),
                'fixed_security_ids':len({r['security_id'] for r in rows if r['security_id']}),'eligible':state['ELIGIBLE'],
                'excluded':state['EXCLUDED'],'unknown':state['UNKNOWN'],'scored':len(projected or {})},
            'coverage':coverage,'rows':rows}


def read_held_archive(path, *, basis_date):
    """Verify only used member receipts; normalize original SEC bytes with the official calculator.

    Never creates a security ID, uses an observed timestamp as a listing start, or
    downloads absent files. The original approved archive remains the raw source.
    """
    import hashlib
    import json
    import zipfile
    if not _day(basis_date):raise ValueError('INVALID_BASIS_DATE')
    receipts=[]
    with zipfile.ZipFile(path) as z:
        names=z.namelist();members=set(names)
        if len(names)!=len(members):raise ValueError('DUPLICATE_ARCHIVE_MEMBER')
        def read(key):
            name='data/raw/blobs/'+key;receipt_name='data/raw/manifests/'+key+'.json'
            body=z.read(name);receipt=json.loads(z.read(receipt_name))
            if hashlib.sha256(body).hexdigest()!=receipt['sha256'] or len(body)!=receipt['bytes']:
                raise ValueError('HELD_MEMBER_HASH_MISMATCH')
            acquired=datetime.fromisoformat(receipt['fetched_at'].replace('Z','+00:00'))
            if acquired.utcoffset() is None or acquired.astimezone(timezone.utc).date()>_day(basis_date):
                raise ValueError('HELD_MEMBER_AFTER_BASIS')
            receipts.append({'member':name,'receipt_member':receipt_name,**receipt})
            return body,acquired
        body,observed=read('sec_tickers');catalog=json.loads(body)
        candidates=[catalog[k] for k in sorted(catalog,key=int)]
        financials={};missing=[]
        for cik in sorted({_cik(c.get('cik_str')) for c in candidates}-{None}):
            keys=['companyfacts__'+cik,'submissions__'+cik]
            if any('data/raw/blobs/'+k not in members or 'data/raw/manifests/'+k+'.json' not in members for k in keys):
                missing.append(cik);continue
            facts,ft=read(keys[0]);subs,st=read(keys[1])
            financials[cik]=sec.build_row(cik=cik,companyfacts_body=facts,submissions_body=subs,acquired_at=max(ft,st))
        source={'source_ref':receipts[0]['source_url'],'scope':'SEC_TICKER_OBSERVATIONS','complete':False,
                'observed_at':observed.isoformat(),'basis_date':observed.date().isoformat(),
                'age_days_at_evaluation':(_day(basis_date)-observed.date()).days,
                'full_current_iex_membership':'UNCONFIRMED','security_validity':'NOT_ESTABLISHED_BY_OBSERVATION',
                'original_member':receipts[0]['member'],'sha256':receipts[0]['sha256']}
    return {'candidates':candidates,'financials':financials,'source':source,'receipts':receipts,'missing_issuer_inputs':missing}
