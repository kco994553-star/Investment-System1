"""Held SEC snapshot -> research observations, using the existing SEC facts engine.

No fetching, no new EPS reconstruction, price reconstruction or classification engine.
The book-sector/accounting mapping is an evidence-bearing input; SIC ETF mappings
are not silently repurposed. Archive paths and hashes are supplied by the job.
"""
from __future__ import annotations
import hashlib
import json
import tarfile
from datetime import date, timedelta
from pathlib import Path
from investment_system.qgv import v2_factors as vf
from .sector_qgv import calculate_factor
from .sector_qgv_registry import CATALOG, MAPPING
from .financial_v import _balance_observations

ADAPTER_VERSION = 'held-sec-sector-adapter/2'


def _common_components(payload, record, reference, facts, company, fields, reasons, put):
    """Explicit common-holder concepts; reuse existing fiscal and balance parsers."""
    cutoff=facts.cutoff;currency=facts.currency
    tax=payload.get('facts',{}).get('us-gaap',{})
    if facts.taxonomy!='us-gaap':
        reasons['common_inputs']={'cause':'TRANSFORM_NOT_CONNECTED','detail':'IFRS_COMMON_ATTRIBUTION_NOT_MAPPED'}
        return
    tag='NetIncomeLossAvailableToCommonStockholdersBasic'
    table,source=facts._table(tax.get(tag),currency,False)
    facts.items['net_income_common']=[table];facts.sources['net_income_common']=[source]
    facts.concepts['net_income_common']=(tag,)
    hit=company.ttm('net_income_common');latest=facts.latest_duration('net_income_common')
    if hit and not (latest and latest[1]>hit[1]):
        put('net_income_common',hit[0],'TTM',hit[1],start=vf._shift_years(hit[1],1)+timedelta(days=1))
        fields['net_income_common'].update(equity_basis='COMMON_EXCLUDING_PREFERRED_NCI',
            filing_evidence=[{'concept':tag,'start':str(k[0]),'end':str(k[1]),'accession':v[0],
                              'filed':str(v[1])} for k,v in source.items()
                             if vf._shift_years(hit[1],2)<=k[1]<=hit[1]])
    else:reasons['net_income_common']={'cause':'VALIDATION_FAILED' if tag in tax else 'VALUE_ABSENT_IN_EXAMINED_SOURCE',
                                      'detail':'EXACT_COMMON_INCOME_TTM_REQUIRED_NO_NET_INCOME_SUBSTITUTE'}
    specs={'direct':(('CommonStockholdersEquity',),currency),
           'parent':(('StockholdersEquity',),currency),
           'preferred':(('PreferredStockSharesOutstanding',),'shares'),
           'shares':(('CommonStockSharesOutstanding',),'shares')}
    history_days=max(0,(cutoff-company.end(3)).days)
    observed={k:_balance_observations(payload,tags,unit,cutoff,history_days=history_days)
              for k,(tags,unit) in specs.items()}
    def common_at(end):
        keys=set(observed['direct'][0])|set(observed['parent'][0])
        # Conflict rows passed date/unit/form checks but were removed by the
        # balance parser. Retain their filing anchors when choosing the latest
        # observation so an older accepted value cannot hide a newer conflict.
        for kind in ('direct','parent'):
            for rejected in observed[kind][1]:
                key=rejected.get('balance_key')
                if key:keys.add((date.fromisoformat(key[0]),date.fromisoformat(key[1]),key[2]))
        keys=[k for k in keys if k[0]==end]
        # Invalid newer direct observations must not fall back to an older filing.
        if not keys:return None,None,None
        filed=max(k[1] for k in keys);keys=[k for k in keys if k[1]==filed]
        if len(keys)!=1:return None,None,None
        key=keys[0];common=observed['direct'][0].get(key)
        if any(x.get('balance_key')==[str(v) for v in key] for x in observed['direct'][1]):
            return None,key,None
        if common is None and observed['preferred'][0].get(key,{}).get('value')==0:
            common=observed['parent'][0].get(key)
        return common,key,observed['shares'][0].get(key)
    end=max(facts.instant_ends('total_assets'),default=None)
    for field,at in [('common_equity_end',end),('common_equity_begin',vf._shift_years(end,1) if end else None)]:
        common,key,_=common_at(at)
        if common:
            put(field,common['value'],'INSTANT',at)
            fields[field].update(equity_basis='COMMON_EXCLUDING_PREFERRED_NCI',
                source_detail={'accession':key[2],'filed':str(key[1]),'json_pointers':common['json_pointers'],
                  'preferred_zero_evidence':observed['preferred'][0].get(key) if key not in observed['direct'][0] else None})
        else:reasons[field]={'cause':'VALIDATION_FAILED' if observed['direct'][2] else 'VALUE_ABSENT_IN_EXAMINED_SOURCE',
                            'detail':'EXACT_PERIOD_COMMON_ATTRIBUTION_REQUIRED','period_end':str(at) if at else None,
                            'rejected':{k:v[1] for k,v in observed.items() if v[1]}}
    # Raw per-share fiscal components are retained, but no class, ADR or split
    # continuity is inferred from issuer-level XBRL. The kernel rejects missing basis.
    for k in range(4):
        at=company.end(k);common,key,shares=common_at(at)
        if common and shares and shares['value']>0:
            field='common_bps_fy'+(str(k) if k else '')
            put(field,common['value']/shares['value'],'FY' if k==0 else 'FY_MINUS_'+str(k),at,unit=currency+'/share')
            fields[field]['source_detail']={'accession':key[2],'filed':str(key[1]),
                'common_equity':common,'instant_common_shares':shares}
        else:
            field='common_bps_fy'+(str(k) if k else '')
            reasons[field]={'cause':'VALUE_ABSENT_IN_EXAMINED_SOURCE' if not observed['direct'][2] else 'VALIDATION_FAILED',
                'detail':'EXACT_ANNUAL_COMMON_EQUITY_AND_SAME_FILING_INSTANT_SHARES_REQUIRED',
                'period_end':str(at)}
    reasons['common_bps_cagr_3y']='COMMON_SHARE_BASIS_UNCONFIRMED; annual class/ADR/split continuity required'


def checked_bytes(spec):
    path=Path(spec['path']);body=path.read_bytes()
    if hashlib.sha256(body).hexdigest()!=spec['sha256']:raise ValueError('INPUT_HASH_MISMATCH')
    return body


def _components(payload,record,reference):
    acquired=record['acquired_at'];cutoff=date.fromisoformat(acquired[:10])
    taxonomy,currency=vf._taxonomy_and_currency(payload,cutoff)
    if taxonomy is None or not record.get('fiscal_year_end'):return {},{}
    facts=vf._Facts(payload,taxonomy,currency,cutoff)
    c=vf._Company(facts,date.fromisoformat(record['fiscal_year_end']),sic=record.get('sic'),profile=record.get('profile'))
    fields={};reasons={}
    source_state=record.get('state')
    source_status='STALE' if source_state=='STALE' or 'STALE_INPUT' in record.get('reason_codes',[]) else ('SOURCE_NOT_AVAILABLE' if source_state=='NOT_AVAILABLE' else 'VALID')
    if source_status!='VALID':reasons['source_status']=source_status
    def put(key,value,kind,end,unit=None,start=None):
        if value is None or end is None:return
        fields[key]=dict(value=value,period_kind=kind,period_start=start.isoformat() if start else None,
            period_end=end.isoformat(),unit=unit or currency,currency=currency,issuer_id=record['cik'],
            security_id=None,share_basis=None,corporate_action_basis=None,scope='CONSOLIDATED',
            available_at=acquired,retrieved_at=acquired,availability_basis='OBSERVED_BY_ACQUISITION_NOT_FIRST_RELEASE',
            provenance=[reference],status=source_status)
    # Same-concept FY + current YTD - comparable YTD from the existing engine.
    # Reject its annual fallback when a later duration exists but cannot be completed.
    for field,item in [('revenue','revenue'),('net_income','net_income'),('cfo','operating_cash_flow'),
                       ('ebit','ebit'),('da','depreciation_amortization'),('capex','capital_expenditure'),
                       ('interest_expense','interest_expense'),('gross_profit','gross_profit')]:
        try:hit=c.ttm(item)
        except (KeyError,TypeError,ValueError):hit=None
        latest=facts.latest_duration(item) if item in facts.items else None
        if hit is not None and latest is not None and latest[1]>hit[1]:
            reasons[field]='LATEST_TTM_INCOMPLETE_NO_ANNUAL_FALLBACK';continue
        if hit:
            start=vf._shift_years(hit[1],1)+timedelta(days=1)
            put(field,hit[0],'TTM',hit[1],start=start)
            # Q01 uses reported operating income, not the operating engine's EBIT substitute.
            if field=='ebit' and not c.ebit_estimated(0):put('operating_income',hit[0],'TTM',hit[1],start=start)
    asset_ends=facts.instant_ends('total_assets')
    end=max(asset_ends,default=None)
    if end:
        put('assets_end',facts.instant('total_assets',end,tolerance=0),'INSTANT',end)
        begin=vf._shift_years(end,1)
        put('assets_begin',facts.instant('total_assets',begin,tolerance=7),'INSTANT',begin)
        put('debt',c.debt_at(end,tolerance=0),'INSTANT',end)
        put('cash',facts.instant('cash_and_equivalents',end,tolerance=0),'INSTANT',end)
    # Annual-series history is explicit; every year required by each growth variant.
    for field,item in [('revenue','revenue'),('operating_income','ebit')]:
        for k in range(6):
            hit=facts.annual(item,c.end(k))
            if hit:put(field+'_fy'+(str(k) if k else ''),hit[0],'FY' if k==0 else 'FY_MINUS_'+str(k),hit[2],start=hit[1])
    for k in (0,3):
        ni=facts.annual('net_income',c.end(k));ocf=facts.annual('operating_cash_flow',c.end(k))
        for name,hit in [('roa',ni),('cfo_assets',ocf)]:
            if not hit:continue
            a=facts.instant('total_assets',hit[2],tolerance=7)
            b=facts.instant('total_assets',hit[1]-timedelta(days=1),tolerance=7)
            if a is not None and b is not None and a>0 and b>0:
                put(name+'_fy'+(str(k) if k else ''),hit[0]/((a+b)/2),'FY' if k==0 else 'FY_MINUS_'+str(k),hit[2],unit='decimal',start=hit[1])
    reasons['eps_ttm_diluted']='VERIFIED_TTM_EPS_COMPOSITION_NOT_CONNECTED; generic monetary-flow YTD arithmetic not used for EPS'
    _common_components(payload,record,reference,facts,c,fields,reasons,put)
    return fields,reasons


def held_observations(payload, record, reference, *, as_of, valuation_date, accounting_template=None, include_components=False):
    """One verified issuer through the existing SEC period and factor engines.

    Shared by the original operating snapshot and held expanded issuer sample.
    No annual/TTM alias, price reconstruction, representative-security inference.
    """
    fields,reasons=_components(payload,record,reference)
    ctx=dict(as_of=as_of,valuation_date=valuation_date,issuer_id=record['cik'],security_id=None,
             accounting_template=accounting_template,
             raw_only_accounting_unconfirmed=accounting_template is None)
    if accounting_template is None:reasons['accounting_template']='UNCONFIRMED_RAW_ONLY'
    allowed={
        'operating_margin_ttm','accruals_assets_ttm','debt_assets','roa_ttm','cfo_assets_ttm',
        'interest_coverage_ttm','gross_profit_assets_ttm','net_debt_assets','revenue_cagr_3y',
        'revenue_cagr_5y','revenue_growth_1y','operating_income_cagr_3y',
        'revenue_growth_consistency_3y','roa_improvement_3y',
        'roe_common_ttm','common_equity_assets','common_bps_cagr_3y','cfo_assets_improvement_3y'}
    result={v:calculate_factor(v,fields,ctx) for v in sorted(allowed)}
    return (result,reasons,fields) if include_components else (result,reasons)


def build_held_snapshot(sec,archive_specs,*,snapshot_hash,mapping_rows=None,as_of=None):
    if sec.get('calc_version')!='qgv2-calc/2026-10-23.1':raise ValueError('HELD_INPUT_VERSION_MISMATCH')
    mapping_rows=mapping_rows or {};as_of=as_of or sec['as_of']
    # Evaluation date is the source snapshot date. The separate official baseline
    # has 2026-11-02 prices: it is not claimed to be this date's price input.
    valuation=as_of[:10];wanted={r.get('source_sha256',{}).get('companyfacts') for r in sec['records'].values()}
    sources={};audit={'requested_rows':len(sec['records']),'source_hash_connected':0,'raw_input_failures':{},'archives':[]}
    for spec in archive_specs:
        checked_bytes(spec)  # New transformation verifies the exact inputs it consumes.
        with tarfile.open(spec['path']) as archive:
            tag=spec['release'];manifest=json.load(archive.extractfile(tag+'/manifest.json'))
            audit['archives'].append({'release':tag,'sha256':spec['sha256']})
            for comp in manifest['companies']:
                expected=comp.get('sha256',{}).get('companyfacts.json')
                if expected not in wanted or expected in sources:continue
                member=tag+'/'+comp['cik']+'/companyfacts.json';body=archive.extractfile(member).read()
                if hashlib.sha256(body).hexdigest()!=expected:raise ValueError('MEMBER_HASH_MISMATCH')
                payload=json.loads(body)
                if str(payload['cik']).zfill(10)!=comp['cik']:raise ValueError('ISSUER_ID_MISMATCH')
                sources[expected]=(payload,tag+'/'+comp['cik']+'/companyfacts.json#sha256='+expected)
    rows=[]
    for code,record in sorted(sec['records'].items()):
        mapping=mapping_rows.get(code,{})
        row=dict(company_id=code,issuer_id=record.get('cik'),security_id=mapping.get('security_id'),
                 sector_id=mapping.get('sector_id'),accounting_template=mapping.get('accounting_template'),
                 mapping=mapping.get('mapping'),observations={},gate=None,
                 source_profile=record.get('profile'),source_sic=record.get('sic'))
        source=sources.get(record.get('source_sha256',{}).get('companyfacts'))
        if source:
            if str(source[0]['cik']).zfill(10)!=record['cik']:raise ValueError('RECORD_ISSUER_MISMATCH')
            audit['source_hash_connected']+=1
            if record.get('state')=='NOT_AVAILABLE' or record.get('calc_version')!='qgv2-calc/2026-10-23.1':
                reason='SOURCE_NOT_AVAILABLE' if record.get('state')=='NOT_AVAILABLE' else 'HELD_ROW_VERSION_MISMATCH'
                row['input_diagnostics']={'source':reason}
                audit['raw_input_failures'][reason]=audit['raw_input_failures'].get(reason,0)+1
                rows.append(row)
                continue
            if sec.get('state')=='STALE':record=dict(record,state='STALE')
            row['observations'],row['input_diagnostics']=held_observations(source[0],record,source[1],as_of=as_of,valuation_date=valuation,accounting_template=row['accounting_template'])
        else:row['input_diagnostics']={'source':'EXACT_SOURCE_HASH_NOT_IN_HELD_ARCHIVES'}
        rows.append(row)
    snapshot=dict(schema_version='sector-qgv-input/1',snapshot_id='held-sec-'+snapshot_hash[:16],
        universe_id='Universe504',universe_version='sec-universe-shares/v0@'+sec['registry_sha256'],
        mapping_version=MAPPING,input_version=ADAPTER_VERSION,as_of=as_of,valuation_date=valuation,
        members=sorted(sec['records']),rows=rows)
    audit['mapping_confirmed']=sum(bool(r['mapping']) for r in rows)
    audit['price_inputs_connected']=0
    audit['scope']='Held operating code rows; not whole-market or historical PIT coverage'
    audit['source_availability_basis']='Acquisition proves available by that timestamp, not initial SEC release time'
    return snapshot,audit
