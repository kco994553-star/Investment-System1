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


def checked_bytes(spec):
    path=Path(spec['path']);body=path.read_bytes()
    if hashlib.sha256(body).hexdigest()!=spec['sha256']:raise ValueError('INPUT_HASH_MISMATCH')
    return body


def _components(payload,record,reference):
    acquired=record['acquired_at'];cutoff=date.fromisoformat(acquired[:10])
    taxonomy,currency=vf._taxonomy_and_currency(payload,cutoff)
    if taxonomy is None or not record.get('fiscal_year_end'):return {},{}
    facts=vf._Facts(payload,taxonomy,currency,cutoff)
    c=vf._Company(facts,date.fromisoformat(record['fiscal_year_end']),sic=record.get('sic'),profile=record.get('profile') or 'GENERAL')
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
    return fields,reasons


def held_observations(payload, record, reference, *, as_of, valuation_date):
    """One verified issuer through the existing SEC period and factor engines.

    Shared by the original operating snapshot and held expanded issuer sample.
    No annual/TTM alias, price reconstruction, representative-security inference.
    """
    fields,reasons=_components(payload,record,reference)
    ctx=dict(as_of=as_of,valuation_date=valuation_date,issuer_id=record['cik'],security_id=None,
             accounting_template='GENERAL')
    allowed={'roa_ttm','roa_improvement_3y'} if record.get('profile')=='FINANCIAL' else {
        'operating_margin_ttm','accruals_assets_ttm','debt_assets','roa_ttm','cfo_assets_ttm',
        'interest_coverage_ttm','gross_profit_assets_ttm','net_debt_assets','revenue_cagr_3y',
        'revenue_cagr_5y','revenue_growth_1y','operating_income_cagr_3y',
        'revenue_growth_consistency_3y','roa_improvement_3y'}
    return {v:calculate_factor(v,fields,ctx) for v in sorted(allowed)},reasons


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
            row['observations'],row['input_diagnostics']=held_observations(source[0],record,source[1],as_of=as_of,valuation_date=valuation)
        else:row['input_diagnostics']={'source':'EXACT_SOURCE_HASH_NOT_IN_HELD_ARCHIVES'}
        rows.append(row)
    snapshot=dict(schema_version='sector-qgv-input/1',snapshot_id='held-sec-'+snapshot_hash[:16],
        universe_id='Universe504',universe_version='sec-universe-shares/v0@'+sec['registry_sha256'],
        mapping_version=MAPPING,input_version='held-sec-sector-adapter/1',as_of=as_of,valuation_date=valuation,
        members=sorted(sec['records']),rows=rows)
    audit['mapping_confirmed']=sum(bool(r['mapping']) for r in rows)
    audit['price_inputs_connected']=0
    audit['scope']='Held operating code rows; not whole-market or historical PIT coverage'
    audit['source_availability_basis']='Acquisition proves available by that timestamp, not initial SEC release time'
    return snapshot,audit
