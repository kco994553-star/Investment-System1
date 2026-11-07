"""Retained non-price V inputs and a resume adapter to the existing sector engine.

No requests, quote parser, EPS reconstruction, market-cap or EV calculator.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import tarfile
from collections import Counter
from datetime import date,timedelta,timezone
from .sector_qgv import default_config,preset,calculate_factor,preview_qgv,digest,timestamp,day,finite,VALID
from .sector_qgv_registry import CATALOG
from .sector_qgv_held import checked_bytes
from investment_system.qgv import v2_factors as vf

VERSION='sector-qgv-v-resume/1'
MARKET={'price','issuer_mcap','enterprise_value'}
FLOWS={'revenue':'revenue','cfo':'operating_cash_flow','capex':'capital_expenditure','ebit':'ebit','da':'depreciation_amortization'}


def selected(row):
    if not row.get('mapping'):return []
    p=preset(default_config(),row['sector_id'],row['accounting_template'])
    return sorted(v for role in p['axes']['V'].values() for v,w in role['factors'].items() if role['weight'] and w)


def component(record,field,value,kind,end,reference,*,start=None,unit=None):
    currency=record['currency'];at=record['acquired_at']
    return {'value':value,'period_kind':kind,'period_start':start,'period_end':end,
            'unit':unit or currency,'currency':currency,'issuer_id':record['cik'],
            'security_id':None,'share_basis':None,'corporate_action_basis':None,'scope':'CONSOLIDATED',
            'available_at':at,'retrieved_at':at,'availability_basis':'OBSERVED_BY_ACQUISITION_NOT_FIRST_RELEASE',
            'provenance':[reference],'status':'VALID','field':field}


def extract_nonprice(record,payload,variants,reference,cached_financial=None):
    needed={x['field'] for v in variants for x in CATALOG[v]['inputs']} - MARKET
    fields={};diagnostics={};cutoff=day(record['acquired_at'][:10])
    taxonomy,currency=vf._taxonomy_and_currency(payload,cutoff)
    if record.get('state')!='LIVE':return {},{'source':'SOURCE_NOT_LIVE'}
    if taxonomy is None or currency!=record.get('currency') or not record.get('fiscal_year_end'):
        return {},{'source':'CURRENCY_OR_FISCAL_ANCHOR_UNAVAILABLE'}
    facts=vf._Facts(payload,taxonomy,currency,cutoff)
    company=vf._Company(facts,day(record['fiscal_year_end']),sic=record['sic'],profile=record['profile'])
    for field in sorted(needed & FLOWS.keys()):
        item=FLOWS[field];stored=record.get('v_inputs_v2',{}).get(field) or {}
        if field in ('revenue','ebit') and stored.get('ttm_value') is not None and stored.get('ttm_end'):
            hit=(stored['ttm_value'],day(stored['ttm_end']),None);method='REUSED_CALC23_1_TTM'
        else:
            try:hit=company.ttm(item)
            except (KeyError,TypeError,ValueError):hit=None
            method='EXISTING_CALC23_1_TTM_EXTRACT'
        latest=facts.latest_duration(item)
        if hit is None or latest and latest[1]>hit[1]:
            diagnostics[field]='LATEST_TTM_INCOMPLETE_NO_ANNUAL_FALLBACK';continue
        end=hit[1];start=vf._shift_years(end,1)+timedelta(days=1)
        fields[field]=component(record,field,hit[0],'TTM',str(end),reference,start=str(start))
        fields[field]['extraction_method']=method
        # Retain exact eligible concept period/filed/accession inventory; calculator
        # remains responsible for selecting the same-concept TTM recipe.
        fields[field]['filing_evidence']=[{'concept':concept,'start':str(k[0]) if k[0] else None,'end':str(k[1]),
            'accession':filing[0],'filed':str(filing[1])}
            for concept,src in zip(facts.concepts[item],facts.sources[item]) for k,filing in src.items()
            if k[0] and vf._shift_years(end,2)<=k[1]<=end]
    if 'eps_ttm_diluted' in needed:diagnostics['eps_ttm_diluted']='VERIFIED_TTM_DILUTED_EPS_COMPOSITION_MISSING_NO_FY_OR_NI_SUBSTITUTE'
    if 'common_dps_ttm' in needed:diagnostics['common_dps_ttm']='CLASS_MATCHED_TTM_DPS_NOT_CONNECTED_NO_ZERO_FILL'
    if 'nareit_ffo' in needed:diagnostics['nareit_ffo']='NAREIT_FFO_RECONCILIATION_NOT_CONNECTED'
    if 'common_bps' in needed:
        old=(cached_financial or {}).get('inputs',{}).get('book_yield')
        if old and old['source'].get('companyfacts_sha256')==record['source_sha256']['companyfacts'] and day(old['filed'])<=cutoff and day(old['period_end'])==max(facts.instant_ends('total_assets'),default=None):
            x=component(record,'common_bps',old['value'],'INSTANT',old['period_end'],reference,unit=old['unit'])
            x.update(share_basis=old['share_basis'],source_detail=copy.deepcopy(old['source']),
                     extraction_method='REUSED_499_COMMON_BOOK_INPUT',source_evaluation_date='2026-11-02')
            # Fiscal numerator may be reused; Nov2 price/adoption does not travel.
            fields['common_bps']=x
        else:diagnostics['common_bps']='COMMON_EQUITY_AND_POINT_IN_TIME_CLASS_SHARES_NOT_CONNECTED'
    capital={k:copy.deepcopy(record.get('v_inputs_v2',{}).get(k)) for k in ('total_debt','cash_and_equivalents')}
    capital.update(preferred=None,noncontrolling_interest=None,actual_evaluation_date_class_shares=None,
                   diluted_shares_not_used=copy.deepcopy(record.get('v_inputs_v2',{}).get('diluted_shares')))
    return fields,{'missing':diagnostics,'capital_diagnostics':capital}


def input_issues(field,x,spec,pack,issuer):
    if not isinstance(x,dict) or x.get('value') is None:return ['MISSING:'+field]
    out=[]
    if not finite(x['value']) or x.get('status') not in VALID:out.append('INVALID:'+field)
    if x.get('issuer_id')!=issuer or x.get('scope')!='CONSOLIDATED':out.append('ISSUER_SCOPE:'+field)
    if x.get('unit')!=spec['unit'].replace('currency',x.get('currency') or '?'):out.append('UNIT:'+field)
    try:
        if timestamp(x['available_at'])>timestamp(pack['as_of']) or timestamp(x['retrieved_at'])>timestamp(pack['as_of']):out.append('FUTURE:'+field)
        if x['period_kind']!=spec['period'] or day(x['period_end'])>day(pack['valuation_date']):out.append('PERIOD:'+field)
        if spec['period']=='TTM' and not 350<=(day(x['period_end'])-day(x['period_start'])).days<=380:out.append('PERIOD:'+field)
    except (KeyError,TypeError,ValueError):out.append('TIME_EVIDENCE:'+field)
    if not x.get('provenance'):out.append('SOURCE:'+field)
    return sorted(set(out))


def readiness(pack):
    rows=[];counts=Counter();by_variant={};groups=Counter((r.get('sector_id'),r.get('accounting_template')) for r in pack['snapshot']['rows'] if r.get('mapping'))
    for row in pack['rows']:
        for v in row['selected_variants']:
            specs=CATALOG[v]['inputs'];missing=[]
            for spec in specs:
                if spec['field'] not in MARKET:missing+=input_issues(spec['field'],row['inputs'].get(spec['field']),spec,pack,row['issuer_id'])
            present=[row['inputs'][s['field']] for s in specs if s['field'] not in MARKET and s['field'] in row['inputs']]
            if len({x['period_end'] for x in present if x['period_kind']=='TTM'})>1:missing.append('TTM_PERIOD_ALIGNMENT')
            if len({x['currency'] for x in present})>1:missing.append('CURRENCY_ALIGNMENT')
            if v=='fcf_mcap' and row['inputs'].get('capex',{}).get('value',0)<0:missing.append('NEGATIVE_CAPEX_DOMAIN')
            basis=[]
            if not row.get('security_id'):basis.append('SECURITY_ID_AND_DATED_IDENTITY')
            basis.append('DATED_SPLIT_ADR_SHARE_BASIS_EVIDENCE')
            market=[s['field'] for s in specs if s['field'] in MARKET]
            if any(f in market for f in ('issuer_mcap','enterprise_value')):basis+=['ALL_CLASS_ACTUAL_SHARES_ON_EVALUATION','ALL_CLASS_QUOTE_AND_CURRENCY_BASIS']
            if 'enterprise_value' in market:
                capital=row['diagnostics'].get('capital_diagnostics',{})
                basis+=['EV_'+k.upper() for k in ('total_debt','cash_and_equivalents','preferred','noncontrolling_interest') if capital.get(k) is None or isinstance(capital[k],dict) and capital[k].get('value') is None]
                basis.append('EV_COMPONENT_PERIOD_AND_DEFINITION_RECONCILIATION')
            # These are preparation gaps, not raw ratios calculated with fake prices.
            rec={'company_id':row['company_id'],'variant_id':v,'numerator_ready':not missing,
                 'price_only_ready':not missing and not basis,'nonprice_missing':missing+basis,
                 'price_inputs_pending':market,'mapped_group_upper_bound':groups[(row['sector_id'],row['accounting_template'])],
                 'peer_sample_status':'STRUCTURAL_PEER_SHORTFALL' if groups[(row['sector_id'],row['accounting_template'])]<20 else 'FACTOR_VALID_N_PENDING_PRICE',
                 'raw_value':None,'factor_score':None}
            rows.append(rec);counts['selected_variant_rows']+=1;counts['numerator_ready']+=not missing
            counts['price_only_ready']+=rec['price_only_ready'];counts['additional_nonprice_gaps']+=bool(missing+basis)
            counts['structural_peer_shortfall']+=rec['peer_sample_status']=='STRUCTURAL_PEER_SHORTFALL'
            by_variant.setdefault(v,Counter()).update({'selected':1,'numerator_ready':not missing,'price_only_ready':rec['price_only_ready']})
    return {'schema_version':'sector-qgv-v-readiness/1','valuation_date':pack['valuation_date'],'denominator':len(pack['snapshot']['members']),
            'mapped_companies':sum(bool(r['selected_variants']) for r in pack['rows']),'rows':rows,'counts':dict(counts),
            'by_variant':{k:dict(v) for k,v in by_variant.items()},'real_raw_calculated':0,'V_scored':0,'total_scored':0}


def prepare(snapshot,sec,archive_specs,cached_financial):
    if sec['as_of']!=snapshot['as_of'] or sorted(sec['records'])!=sorted(snapshot['members']):raise ValueError('V_SOURCE_SNAPSHOT_MISMATCH')
    cached={r['code']:r for r in cached_financial.get('rows',[])}
    if cached_financial and timestamp(cached_financial['input_vintage'])>timestamp(snapshot['as_of']):raise ValueError('FINANCIAL_CACHE_FUTURE')
    wanted={sec['records'][r['company_id']]['source_sha256'].get('companyfacts') for r in snapshot['rows'] if selected(r)};sources={}
    for spec in archive_specs:
        checked_bytes(spec)
        with tarfile.open(spec['path']) as tar:
            tag=spec['release'];manifest=json.load(tar.extractfile(tag+'/manifest.json'))
            for c in manifest['companies']:
                sha=c['sha256'].get('companyfacts.json')
                if sha not in wanted or sha in sources:continue
                member=tag+'/'+c['cik']+'/companyfacts.json';body=tar.extractfile(member).read()
                if hashlib.sha256(body).hexdigest()!=sha:raise ValueError('V_SOURCE_HASH_MISMATCH')
                payload=json.loads(body)
                if str(payload.get('cik')).zfill(10)!=c['cik']:raise ValueError('V_SOURCE_ISSUER_MISMATCH')
                sources[sha]=(payload,member+'#sha256='+sha)
    rows=[]
    for row in snapshot['rows']:
        vs=selected(row);record=sec['records'][row['company_id']];src=sources.get(record['source_sha256'].get('companyfacts'))
        fields,diag={},{'source':'SOURCE_OR_MAPPING_UNAVAILABLE'}
        if vs and src:
            fields,diag=extract_nonprice(record,src[0],vs,src[1],cached.get(row['company_id']))
        rows.append({k:copy.deepcopy(row.get(k)) for k in ('company_id','issuer_id','security_id','sector_id','accounting_template')}|{'selected_variants':vs,'inputs':fields,'diagnostics':diag})
    pack={'schema_version':VERSION,'valuation_date':snapshot['valuation_date'],'as_of':snapshot['as_of'],
          'snapshot':copy.deepcopy(snapshot),'rows':rows,'market_inputs':None,'data_kind':'PRIVATE',
          'original_qg_recomputed':0,'source_snapshot_hash':digest(sec)}
    return pack,readiness(pack)


def resume(pack,market,request_id):
    if pack.get('schema_version')!=VERSION or market.get('schema_version')!='sector-qgv-v-market-input/1':raise ValueError('V_RESUME_SCHEMA_MISMATCH')
    if market.get('valuation_date')!=pack['valuation_date'] or timestamp(market.get('as_of'))<timestamp(pack['as_of']) or market.get('resume_hash')!=digest(pack):raise ValueError('V_MARKET_CONTEXT_MISMATCH')
    s=copy.deepcopy(pack['snapshot']);s['source_financial_as_of']=pack['as_of'];s['as_of']=market['as_of'];by_code={r['company_id']:r for r in pack['rows']};known=set(s['members'])
    if set(market['records'])-known:raise ValueError('V_MARKET_OUTSIDE_UNIVERSE')
    def timed(proof):
        if not proof.get('evidence_refs'):raise ValueError('V_EVIDENCE_MISSING')
        for key in ('available_at','retrieved_at'):
            try:t=timestamp(proof[key])
            except (KeyError,TypeError,ValueError,AttributeError):raise ValueError('V_EVIDENCE_TIME_MISSING') from None
            if t>timestamp(s['as_of']) or key=='available_at' and t.astimezone(timezone.utc).date()>day(s['valuation_date']):raise ValueError('V_FUTURE_CAPITAL_EVIDENCE')
    for row in s['rows']:
        prepared=by_code[row['company_id']];delivery=market['records'].get(row['company_id'])
        if not delivery:continue
        basis=delivery['basis'];fields=copy.deepcopy(prepared['inputs'])
        if (basis.get('issuer_id')!=row['issuer_id'] or not basis.get('security_id') or not basis.get('evidence_refs')
            or not basis['valid_from']<=s['valuation_date']<basis['valid_to']):raise ValueError('V_MARKET_IDENTITY_UNCONFIRMED')
        timed(basis)
        row['security_id']=basis['security_id']
        for field,proof in delivery.get('field_basis',{}).items():
            if field not in fields or not proof.get('source_share_basis') or fields[field].get('share_basis')!=proof.get('source_share_basis') or proof.get('target_share_basis')!=proof.get('source_share_basis') or not proof.get('evidence_refs'):raise ValueError('V_NUMERATOR_BASIS_MISMATCH')
            timed(proof)
            fields[field].update(security_id=basis['security_id'],share_basis=proof['target_share_basis'],corporate_action_basis=proof['corporate_action_basis'])
            fields[field]['provenance']+=proof['evidence_refs']
        for field,x in delivery['inputs'].items():
            if field not in MARKET:raise ValueError('V_MARKET_CANNOT_REPLACE_FINANCIAL_INPUT')
            if x.get('security_id')!=basis['security_id']:raise ValueError('V_MARKET_SECURITY_MISMATCH')
            if field in ('issuer_mcap','enterprise_value'):
                cap=delivery.get('capital_evidence',{})
                classes=cap.get('classes',[])
                if cap.get('all_common_classes_confirmed') is not True or not classes or len({c.get('security_id') for c in classes})!=len(classes):raise ValueError('V_ALL_CLASS_CAPITAL_UNCONFIRMED')
                if basis['security_id'] not in {c.get('security_id') for c in classes}:raise ValueError('V_TARGET_CLASS_MISSING')
                checked_cap=[]
                for c in classes:
                    timed(c)
                    if not c.get('security_id') or not finite(c.get('actual_shares')) or c['actual_shares']<=0 or c.get('unit')!='shares' or c.get('date')!=s['valuation_date'] or not c.get('evidence_refs') or not c.get('corporate_action_basis'):raise ValueError('V_ACTUAL_CLASS_SHARES_UNCONFIRMED')
                    quote=c.get('quote',{})
                    timed(quote)
                    if quote.get('security_id')!=c['security_id'] or quote.get('date')!=s['valuation_date'] or quote.get('currency')!=x.get('currency') or quote.get('unit')!=x.get('currency')+'/share' or quote.get('share_basis')!=c.get('share_basis') or not c.get('share_basis') or quote.get('corporate_action_basis')!=c['corporate_action_basis'] or not finite(quote.get('value')) or quote['value']<=0:raise ValueError('V_CLASS_QUOTE_BASIS_MISMATCH')
                    checked_cap.append(c['actual_shares']*quote['value'])
                # Validation of the supplied capital result against its primitive
                # observations; this does not generate a quote/market-cap/EV input.
                expected=math.fsum(checked_cap)
                if field=='enterprise_value':
                    for key in ('debt','cash','preferred','nci'):
                        value=cap.get('components',{}).get(key)
                        if isinstance(value,dict):timed(value)
                        if not isinstance(value,dict) or not finite(value.get('value')) or value['value']<0 or not value.get('evidence_refs') or value.get('currency')!=x.get('currency') or value.get('unit')!=x.get('currency') or value.get('period_kind')!='INSTANT' or value.get('scope')!='CONSOLIDATED' or not value.get('period_end') or day(value['period_end'])>day(s['valuation_date']):raise ValueError('V_EV_COMPONENT_UNCONFIRMED')
                    components=cap['components']
                    if len({components[k]['period_end'] for k in ('debt','cash','preferred','nci')})!=1:raise ValueError('V_EV_PERIOD_MISMATCH')
                    expected+=math.fsum(components[k]['value'] for k in ('debt','preferred','nci'))-components['cash']['value']
                if not finite(x.get('value')) or not math.isclose(x['value'],expected,rel_tol=1e-12,abs_tol=1e-8):raise ValueError('V_CAPITAL_RECONCILIATION_MISMATCH')
            fields[field]=x
        for v in prepared['selected_variants']:
            ctx={'as_of':s['as_of'],'valuation_date':s['valuation_date'],'issuer_id':row['issuer_id'],'security_id':basis['security_id'],'accounting_template':row['accounting_template']}
            row['observations'][v]=calculate_factor(v,fields,ctx)
    s['snapshot_id']+='-V-'+digest(market)[:12];s['input_version']='held-sector-v-connected/1'
    return s,preview_qgv(default_config(),s,request_id)
