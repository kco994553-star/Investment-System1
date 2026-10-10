"""Public price-free screen sidecars from explicitly retained government inputs.

No network/credentials/scheduling, Holdout, private preferences or public prices.
LIVE denotes acquisition freshness only, not model/PIT/calibration approval.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, DecimalException
import hashlib
import json
import math
from pathlib import Path
import re

from ..markets.us import US_LISTINGS
from ..qgv.portfolio import OFFICIAL_V11_TARGETS
from ..qgv.factors import Q_WEIGHTS, G_WEIGHTS
from ..qgv.raw_map import map_raw
from ..qgv.sec_m2 import _mapping_view, _current_ambiguity
from ..providers.sec_m1 import build_input
from ..providers.sec_filing_timing import build_filing_timing_pattern
from ..macro.primary_contract import AXES, DIMENSIONS, SOURCE_REGISTRY, ENDPOINTS, LEVEL_REQUIRED, SourceReceipt
from ..macro.government_screen import build_government_macro_screen
from ..providers.macro_primary import parse_bls, parse_bea_nipa, parse_treasury_yields
from ..providers.sec_13f import FilingMetadata, parse_information_table, compare_quarters

FILENAMES = {'macro-screen.json':'MACRO', 'sec-13f-changes.json':'SEC_13F',
    'sec-filing-windows.json':'SEC_FILING_WINDOWS', 'sec-qg-factors.json':'SEC_QG_FACTORS',
    'company-types-pricefree.json':'COMPANY_TYPES_PRICEFREE'}
STATES = ('LIVE','STALE','NOT_AVAILABLE')
AGENCIES = ('SEC_COMPANYFACTS','SEC_SUBMISSIONS','SEC_13F','BLS','BEA','TREASURY','FED_H41','FED_H8','FED_H10','TREASURY_MTS')
REASONS = ('NO_ELIGIBLE_INPUT','SOURCE_NOT_AVAILABLE','SYNTHETIC_INPUT_NOT_PUBLIC','SOURCE_AFTER_AS_OF',
    'STALE_INPUT','UPSTREAM_NOT_AVAILABLE','TYPE_ENGINE_PENDING_MERGE','CRITERIA_UNDEFINED','PUBLIC_FX_EXCLUDED','UNAPPROVED_ENGINE_INPUT_MAPPING')
PRICEFREE_TYPES = ('growth','quality','cyclical','defensive')
FACTORS = set(Q_WEIGHTS)|set(G_WEIGHTS)


def _need(condition,code='PUBLIC_SCREEN_INVALID'):
    if not condition: raise ValueError(code)


def clock(value):
    _need(isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',value) is not None)
    d=datetime.fromisoformat(value.replace('Z','+00:00'));_need(d.utcoffset() is not None)
    return d.astimezone(timezone.utc)


def _finite(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False


def _score(value,max_=100):
    _need(value is None or _finite(value) and 0<=value<=max_)


def _keys(value,expected):
    _need(isinstance(value,dict) and set(value)==set(expected))


def _day(value):
    _need(isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value) is not None)
    return date.fromisoformat(value)


def _hash(value):_need(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None)


def _company_rows(data):
    _keys(data,('companies','method_status','availability_basis'))
    _need(data['method_status']=='PROVISIONAL_UNCALIBRATED' and data['availability_basis']=='OBSERVED_CAPTURE_ONLY')
    rows=data['companies'];_need(isinstance(rows,dict) and set(rows)==set(OFFICIAL_V11_TARGETS));return rows


def _aggregate(states):
    return 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'


def _source_refs(row, sources, agencies, cut, ttl, state):
    refs=row['source_hashes'];_need(isinstance(refs,dict) and set(refs)<=set(agencies))
    for key,sha in refs.items():_hash(sha);_need((agencies[key],sha) in sources)
    if state!='NOT_AVAILABLE':
        _need(set(refs)==set(agencies))
        # Filing/current-report freshness is acquisition freshness, not the age of its historical comparison.
        acquired=sources[(agencies[next(reversed(agencies))],refs[next(reversed(agencies))])]
        _need(state==_fresh(acquired,cut,timedelta(seconds=ttl)))


def _public_unit(unit):
    fixed=('index 1982-84=100','thousands','percent','Percent','Billions','Currency','Millions of USD')
    return unit if unit in fixed or isinstance(unit,str) and re.fullmatch(r'(?:Billions of chained [12]\d{3} dollars|Billions of Chained \([12]\d{3}\) Dollars)',unit) else None


def _require(name,payload):
    _need(name in FILENAMES)
    _keys(payload,('schema_version','kind','as_of','state','sources','reason_codes','freshness_basis','stale_after_seconds','data'))
    _need(type(payload['schema_version']) is int and payload['schema_version']==1 and payload['kind']==FILENAMES[name])
    cut=clock(payload['as_of']);_need(payload['state'] in STATES and payload['freshness_basis']=='SOURCE_ACQUISITION')
    _need(_finite(payload['stale_after_seconds']) and payload['stale_after_seconds']>0)
    _need(isinstance(payload['reason_codes'],list) and all(r in REASONS for r in payload['reason_codes']))
    _need(isinstance(payload['sources'],list) and len(payload['sources'])<=10000)
    allowed=('SEC_COMPANYFACTS','SEC_SUBMISSIONS') if name in ('sec-qg-factors.json','company-types-pricefree.json','sec-filing-windows.json') else ('SEC_13F',) if name=='sec-13f-changes.json' else tuple(p for p in AGENCIES if not p.startswith('SEC_'))
    sources={}
    for s in payload['sources']:
        _keys(s,('agency','sha256','acquired_at'));_need(s['agency'] in allowed);_hash(s['sha256']);_need(clock(s['acquired_at'])<=cut)
        key=(s['agency'],s['sha256']);acquired=clock(s['acquired_at'])
        if key in sources:_need(sources[key]==acquired)
        sources[key]=acquired
    states=[]
    data=payload['data']
    if name in ('sec-qg-factors.json','company-types-pricefree.json'):
        rows=_company_rows(data)
        for row in rows.values():
            _keys(row,('state','factors','source_hashes') if name=='sec-qg-factors.json' else ('state','memberships','config_version','source_hashes'))
            _need(row['state'] in STATES);states.append(row['state'])
            _source_refs(row,sources,{'companyfacts':'SEC_COMPANYFACTS','submissions':'SEC_SUBMISSIONS'},cut,payload['stale_after_seconds'],row['state'])
            if name=='sec-qg-factors.json':
                _need(isinstance(row['factors'],dict) and set(row['factors'])==FACTORS)
                _need(row['state']==_aggregate([f['state'] for f in row['factors'].values()]))
                for f in row['factors'].values():
                    _keys(f,('score','state'));_score(f['score']);_need(f['state'] in STATES and (f['state']=='NOT_AVAILABLE')==(f['score'] is None));_need(f['state'] in ('NOT_AVAILABLE',row['state']))
            else:
                _need(row['config_version'] in (None,'type_config/1'))
                _need(isinstance(row['memberships'],dict) and set(row['memberships'])==set(PRICEFREE_TYPES))
                for v in row['memberships'].values():_score(v,1)
                _need((row['state']=='NOT_AVAILABLE')==all(v is None for v in row['memberships'].values()))
    elif name=='sec-filing-windows.json':
        _keys(data,('companies',));_need(isinstance(data['companies'],dict) and set(data['companies'])==set(OFFICIAL_V11_TARGETS))
        for row in data['companies'].values():
            _keys(row,('state','role','confirmed_earnings_date','groups','source_hashes'))
            _need(row['state'] in STATES and row['role']=='ESTIMATED_PATTERN_NOT_CONFIRMED' and row['confirmed_earnings_date'] is None and isinstance(row['groups'],list))
            states.append(row['state']);_need((row['state']=='NOT_AVAILABLE')==(not row['groups']))
            _source_refs(row,sources,{'companyfacts':'SEC_COMPANYFACTS','submissions':'SEC_SUBMISSIONS'},cut,payload['stale_after_seconds'],row['state'])
            for group in row['groups']:
                _keys(group,('form','report_month_day','observation_count','observed_filing_windows'))
                _need(group['form'] in ('10-K','10-Q') and isinstance(group['report_month_day'],str) and re.fullmatch(r'\d{2}-\d{2}',group['report_month_day']) is not None)
                date.fromisoformat('2000-'+group['report_month_day'])
                _need(type(group['observation_count']) is int and group['observation_count']>0 and isinstance(group['observed_filing_windows'],list))
                for w in group['observed_filing_windows']:
                    _keys(w,('month','day_min','day_max','count'))
                    _need(all(type(v) is int for v in w.values()) and 1<=w['month']<=12 and 1<=w['day_min']<=w['day_max']<=31 and w['count']>0)
    elif name=='macro-screen.json':
        _keys(data,('axes','dimensions','cells','observations','regime','pit_status'))
        _need(data['axes']==list(AXES) and data['dimensions']==list(DIMENSIONS) and data['regime'] is None and data['pit_status'] in ('OBSERVED_BOUND_ONLY','NOT_VERIFIED'))
        _need(isinstance(data['cells'],list) and len(data['cells'])==48)
        _need([(c['axis'],c['dimension']) for c in data['cells']]==[(a,d) for a in AXES for d in DIMENSIONS])
        for c in data['cells']:
            _keys(c,('axis','dimension','state'));_need(c['state'] in ('RAW_EVIDENCE','NOT_AVAILABLE'))
        _need(isinstance(data['observations'],list) and len(data['observations'])<=10000)
        for o in data['observations']:
            _keys(o,('provider','axis','source_id','observation_period','value','unit','unit_scale','binding_sha256','available_at','source_response_sha256'))
            _need(o['provider'] in AGENCIES and o['axis'] in AXES and o['axis']!='FX')
            if o['provider'] in ('BLS','BEA','TREASURY'):_need(o['source_id'] in SOURCE_REGISTRY and SOURCE_REGISTRY[o['source_id']].provider==o['provider'] and SOURCE_REGISTRY[o['source_id']].axis==o['axis'])
            else:_need(o['provider'] in ('FED_H41','FED_H8','TREASURY_MTS') and o['source_id']==o['provider']+'_SUPPLIED_BINDING' and o['axis']=={'FED_H41':'Liquidity','FED_H8':'Credit','TREASURY_MTS':'Fiscal'}[o['provider']])
            _need(isinstance(o['observation_period'],str) and re.fullmatch(r'\d{4}(?:Q[1-4]|-\d{2}(?:-\d{2})?)',o['observation_period']) is not None)
            period=o['observation_period']
            if 'Q' in period:date(int(period[:4]),1,1)
            else:_day(period+'-01' if len(period)==7 else period)
            _need(isinstance(o['value'],str) and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?',o['value']) is not None and Decimal(o['value']).is_finite())
            _need(_public_unit(o['unit']) is not None);_hash(o['binding_sha256'])
            scale=o['unit_scale'];_keys(scale,('kind','value'))
            _need(scale['kind'] in ('POWER_OF_TEN','MULTIPLIER','UNSPECIFIED'))
            if scale['kind']=='POWER_OF_TEN':_need(type(scale['value']) is int and -30<=scale['value']<=30)
            elif scale['kind']=='MULTIPLIER':_need(isinstance(scale['value'],str) and len(scale['value'])<=80 and Decimal(scale['value']).is_finite() and Decimal(scale['value'])>0)
            else:_need(scale['value'] is None)
            _need((o['provider'],o['source_response_sha256']) in sources)
            _need(clock(o['available_at'])==sources[(o['provider'],o['source_response_sha256'])])
            states.append(_fresh(clock(o['available_at']),cut,timedelta(seconds=payload['stale_after_seconds'])))
            _need(clock(o['available_at'])<=cut);_hash(o['source_response_sha256'])
        present={o['source_id'] for o in data['observations']}
        for c in data['cells']:
            required=LEVEL_REQUIRED.get(c['axis'])
            eligible=bool(set(required)<=present) if required else any(o['axis']==c['axis'] for o in data['observations'])
            expected='RAW_EVIDENCE' if c['dimension']=='Level' and eligible else 'NOT_AVAILABLE'
            _need(c['state']==expected)
        _need(data['pit_status']==('OBSERVED_BOUND_ONLY' if data['observations'] else 'NOT_VERIFIED'))
    else:
        _keys(data,('reports','role'));_need(data['role']=='REPORTED_QUANTITY_CHANGE_NOT_TRADES' and isinstance(data['reports'],list))
        for r in data['reports']:
            _keys(r,('manager_cik','previous_quarter','current_quarter','state','changes','source_hashes'))
            _need(isinstance(r['manager_cik'],str) and re.fullmatch(r'\d{10}',r['manager_cik']) is not None and int(r['manager_cik'])>0 and r['state'] in STATES)
            old,new=_day(r['previous_quarter']),_day(r['current_quarter']);_need(old<new and new<=cut.date())
            states.append(r['state']);_source_refs(r,sources,{'previous':'SEC_13F','current':'SEC_13F'},cut,payload['stale_after_seconds'],r['state'])
            _need(isinstance(r['changes'],list) and (r['state']!='NOT_AVAILABLE' or not r['changes']))
            for c in r['changes']:
                _keys(c,('cusip','security_key','unit','kind','reported_before','reported_after','reported_delta'))
                _need(isinstance(c['cusip'],str) and re.fullmatch(r'[0-9A-Z*@#]{9}',c['cusip']) is not None);_hash(c['security_key'])
                _need(c['unit'] in ('SH','PRN') and c['kind'] in ('NEW','ADD','REDUCE','EXIT'))
                _need(type(c['reported_before']) is int and c['reported_before']>=0 and type(c['reported_after']) is int and c['reported_after']>=0 and type(c['reported_delta']) is int and c['reported_delta']==c['reported_after']-c['reported_before'])
                before,after=c['reported_before'],c['reported_after']
                expected='NEW' if before==0 and after>0 else 'EXIT' if before>0 and after==0 else 'ADD' if after>before>0 else 'REDUCE' if before>after>0 else None
                _need(c['kind']==expected)
    _need(payload['state']==_aggregate(states))
    return payload


def require_public_screen(name,payload):
    try:return _require(name,payload)
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError,AttributeError,DecimalException):raise ValueError('PUBLIC_SCREEN_INVALID') from None


def _pairs(items):
    d={}
    for k,v in items:
        _need(k not in d,'PUBLIC_SCREENS_INPUT_INVALID');d[k]=v
    return d


def parse_json(body):
    def invalid(_):raise ValueError('PUBLIC_SCREENS_INPUT_INVALID')
    return json.loads(body,object_pairs_hook=_pairs,parse_constant=invalid)


def _read(root,name):
    _need(isinstance(name,str),'PUBLIC_SCREENS_INPUT_INVALID')
    p=Path(name);_need(not p.is_absolute() and '..' not in p.parts,'PUBLIC_SCREENS_INPUT_INVALID')
    root=Path(root).resolve();target=root/p
    _need(target.resolve().is_relative_to(root) and target.is_file() and not target.is_symlink(),'PUBLIC_SCREENS_INPUT_INVALID')
    _need(target.stat().st_size<=32*1024*1024,'PUBLIC_SCREENS_INPUT_INVALID')
    return target.read_bytes()


def _fresh(acquired,as_of,stale_after):return 'STALE' if as_of-acquired>stale_after else 'LIVE'


def _source(agency,body,acquired):return {'agency':agency,'sha256':hashlib.sha256(body).hexdigest(),'acquired_at':acquired.isoformat()}


def _envelope(name,as_of,stale_after,data,sources,states=(),reasons=()):
    state='LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    return {'schema_version':1,'kind':FILENAMES[name],'as_of':as_of.isoformat(),'state':state,'sources':sources,
        'freshness_basis':'SOURCE_ACQUISITION','stale_after_seconds':stale_after.total_seconds(),
        'reason_codes':list(dict.fromkeys(reasons or (() if state=='LIVE' else ('STALE_INPUT',) if state=='STALE' else ('NO_ELIGIBLE_INPUT',)))), 'data':data}


def _growth(m1):
    """Conservative same-tag/unit 4 exact annual periods; no fiscal guessing."""
    raw=m1['raw_fundamentals'];by={}
    for row in m1['selected_input_facts']:
        if (row['taxonomy'],row['concept']) not in (('us-gaap','Revenues'),('us-gaap','RevenueFromContractWithCustomerExcludingAssessedTax'),('ifrs-full','Revenue')) or row['unit']!=raw['reporting_currency']:continue
        end=date.fromisoformat(row['end'])
        try:expected=(end.replace(year=end.year-1)+timedelta(days=1)).isoformat()
        except ValueError:continue
        if row['start']!=expected:continue
        by.setdefault((row['taxonomy'],row['concept'],row['unit']),{})[row['end']]=row['value']
    values=[]
    for periods in by.values():
        end=max(periods);d=date.fromisoformat(end)
        try:years=[d.replace(year=d.year-n).isoformat() for n in range(4)]
        except ValueError:continue
        if all(y in periods for y in years) and periods[end]==raw['revenue'] and periods[years[-1]]>0 and periods[end]>0:
            values.append((periods[end]/periods[years[-1]])**(1/3)-1)
    return values[0] if values and all(math.isclose(v,values[0],rel_tol=1e-12,abs_tol=1e-12) for v in values) else None


def generate_screen_bundle(*,manifest,input_root,as_of,stale_after):
    try:return _generate(manifest,input_root,as_of,stale_after)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):raise ValueError('PUBLIC_SCREENS_INPUT_INVALID') from None


def _generate(manifest,root,as_of,stale_after):
    _need(isinstance(as_of,datetime) and as_of.utcoffset() is not None and isinstance(stale_after,timedelta) and stale_after.total_seconds()>0,'PUBLIC_SCREENS_INPUT_INVALID')
    as_of=as_of.astimezone(timezone.utc)
    _keys(manifest,('schema_version','sec','macro','thirteen_f'));_need(type(manifest['schema_version']) is int and manifest['schema_version']==1)
    _need(all(isinstance(manifest[k],list) for k in ('sec','macro','thirteen_f')) and len(manifest['sec'])<=17 and len(manifest['macro'])<=64 and len(manifest['thirteen_f'])<=20)
    qg={cid:{'state':'NOT_AVAILABLE','source_hashes':{},'factors':{fid:{'score':None,'state':'NOT_AVAILABLE'} for fid in sorted(FACTORS)}} for cid in OFFICIAL_V11_TARGETS}
    types={cid:{'state':'NOT_AVAILABLE','source_hashes':{},'memberships':dict.fromkeys(PRICEFREE_TYPES),'config_version':None} for cid in OFFICIAL_V11_TARGETS}
    windows={cid:{'state':'NOT_AVAILABLE','role':'ESTIMATED_PATTERN_NOT_CONFIRMED','confirmed_earnings_date':None,'source_hashes':{},'groups':[]} for cid in OFFICIAL_V11_TARGETS}
    sec_sources=[];type_reasons=[];seen=set()
    try:
        from ..qgv.company_types import calculate_company_types
        from ..qgv.type_config import load_official_type_config
        config=load_official_type_config()
    except ImportError:config=None;type_reasons.append('TYPE_ENGINE_PENDING_MERGE')
    for entry in manifest['sec']:
        _keys(entry,('company_id','companyfacts','submissions','acquired_at','synthetic'))
        cid=entry['company_id'];_need(cid in US_LISTINGS and cid not in seen and type(entry['synthetic']) is bool);seen.add(cid)
        acquired=clock(entry['acquired_at'])
        if entry['synthetic'] or acquired>as_of:continue
        fb=_read(root,entry['companyfacts']);sb=_read(root,entry['submissions']);facts=parse_json(fb);sub=parse_json(sb)
        m1=build_input(cid,facts,sub,acquired,as_of)
        # Only correctly identified government source payloads reach projection.
        _need(str(facts.get('cik')).zfill(10)==US_LISTINGS[cid]['cik'] and str(sub.get('cik')).zfill(10)==US_LISTINGS[cid]['cik'])
        sec_sources.extend((_source('SEC_COMPANYFACTS',fb,acquired),_source('SEC_SUBMISSIONS',sb,acquired)))
        refs={'companyfacts':hashlib.sha256(fb).hexdigest(),'submissions':hashlib.sha256(sb).hexdigest()}
        for rows in (qg,types,windows):rows[cid]['source_hashes']=dict(refs)
        state=_fresh(acquired,as_of,stale_after)
        timing=build_filing_timing_pattern(cid,sub,acquired,as_of)
        if timing['groups']:
            windows[cid].update(state=state,groups=timing['groups'])
        if m1['status']=='READY' and not _current_ambiguity(m1):
            raw=_mapping_view(cid,m1['raw_fundamentals'],False);obs=map_raw(raw)
            for fid in FACTORS:
                score=obs[fid].score_0_100
                if score is not None:qg[cid]['factors'][fid]={'score':score,'state':state};qg[cid]['state']=state
            if config is not None:
                metrics={'revenue_cagr_3y':_growth(m1),'roic':None if raw.net_income is None or raw.invested_capital in (None,0) else raw.net_income/raw.invested_capital}
                calc=calculate_company_types(metrics=metrics,original_qgv={'Q':None,'G':None,'V':None},config=config)
                members={t:calc['memberships'][t]['membership'] for t in PRICEFREE_TYPES}
                types[cid].update(config_version=calc['config_version'],memberships=members,state=state if any(v is not None for v in members.values()) else 'NOT_AVAILABLE')
    primary=[];remaining=[];macro_sources=[];bindings={}
    for entry in manifest['macro']:
        _need(isinstance(entry,dict) and set(entry)<=set(('provider','file','acquired_at','synthetic','series_ids','table','binding','source_url')) and set(('provider','file','acquired_at','synthetic'))<=set(entry))
        provider=entry['provider'];acquired=clock(entry['acquired_at']);_need(type(entry['synthetic']) is bool)
        if entry['synthetic'] or acquired>as_of:continue
        body=_read(root,entry['file']);sha=hashlib.sha256(body).hexdigest()
        if provider in ENDPOINTS:
            receipt=SourceReceipt(provider,ENDPOINTS[provider],sha,acquired,False,'CLEARED_SCOPE')
            result=parse_bls(body,receipt,expected_series_ids=tuple(entry.get('series_ids',()))) if provider=='BLS' else parse_bea_nipa(body,receipt,expected_table=entry.get('table')) if provider=='BEA' else parse_treasury_yields(body,receipt)
            primary.append(result)
        else:
            from ..providers.macro_remaining import GovernmentReceipt,RemainingSeriesBinding,parse_fed_sdmx,parse_treasury_mts
            _need(provider in ('FED_H41','FED_H8','FED_H10','TREASURY_MTS'))
            binding=dict(entry['binding']);binding['field_filters']=tuple(tuple(p) for p in binding.get('field_filters',()))
            if 'unit_multiplier' in binding and binding['unit_multiplier'] is not None:binding['unit_multiplier']=Decimal(str(binding['unit_multiplier']))
            receipt=GovernmentReceipt(provider,entry['source_url'],sha,acquired,False,'CLEARED_SCOPE')
            result=(parse_treasury_mts if provider=='TREASURY_MTS' else parse_fed_sdmx)(body,receipt,RemainingSeriesBinding(**binding));remaining.append(result)
        binding_payload=entry.get('binding',{'provider':provider,'series_ids':entry.get('series_ids',[]),'table':entry.get('table')})
        binding_sha=hashlib.sha256(json.dumps(binding_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        for observation in result.observations:
            key=(provider,sha,observation.observation_id)
            if key in bindings:_need(bindings[key]==binding_sha)
            bindings[key]=binding_sha
        macro_sources.append(_source(provider,body,acquired))
    screen=build_government_macro_screen(tuple(primary),as_of,tuple(remaining));observations=[]
    for o in screen['observations']:
        if o['axis']=='FX' or _public_unit(o['unit']) is None:continue
        provider=o['provider'];observations.append({'provider':provider,'axis':o['axis'],'source_id':o['source_id'] if provider in ENDPOINTS else provider+'_SUPPLIED_BINDING','observation_period':o['observation_period'],'value':o['value'],'unit':o['unit'],'unit_scale':{'kind':'POWER_OF_TEN' if provider in ENDPOINTS and o.get('unit_multiplier') is not None else 'MULTIPLIER' if o.get('unit_multiplier') is not None else 'UNSPECIFIED','value':o.get('unit_multiplier')},'binding_sha256':bindings[(provider,o['source_response_sha256'],o['observation_id'])],'available_at':o['available_at'],'source_response_sha256':o['source_response_sha256']})
    cells=[{'axis':c['axis'],'dimension':c['dimension'],'state':c['state'] if c['axis']!='FX' else 'NOT_AVAILABLE'} for c in screen['cells']]
    for cell in cells:
        relevant=[o for o in observations if o['axis']==cell['axis']]
        if not relevant or cell['axis'] in LEVEL_REQUIRED and not set(LEVEL_REQUIRED[cell['axis']])<=set(o['source_id'] for o in relevant):cell['state']='NOT_AVAILABLE'
    macro={'axes':list(AXES),'dimensions':list(DIMENSIONS),'cells':cells,'observations':observations,'regime':None,'pit_status':'OBSERVED_BOUND_ONLY' if observations else 'NOT_VERIFIED'}
    reports=[];report_sources=[]
    for pair in manifest['thirteen_f']:
        _keys(pair,('previous','current','synthetic'));_need(type(pair['synthetic']) is bool)
        if pair['synthetic']:continue
        captures=[];refs={}
        for key in ('previous','current'):
            item=pair[key];_keys(item,('file','metadata'));md=dict(item['metadata'])
            for k in ('quarter_end','filing_date'):md[k]=_day(md[k])
            md['acquired_at']=clock(md['acquired_at']);body=_read(root,item['file'])
            md['source_response_sha256']=hashlib.sha256(body).hexdigest();metadata=FilingMetadata(**md)
            result=parse_information_table(body,metadata,selected_manager_ciks=(metadata.manager_cik,),as_of=as_of)
            captures.append(result)
            if md['acquired_at']<=as_of:
                report_sources.append(_source('SEC_13F',body,md['acquired_at']));refs[key]=hashlib.sha256(body).hexdigest()
        prev,current=captures;comparison=compare_quarters(prev,current)
        changes=[];state='NOT_AVAILABLE'
        if comparison.status=='AVAILABLE':
            state=_fresh(current.metadata.acquired_at,as_of,stale_after)
            for c in comparison.changes:
                from dataclasses import asdict
                identity=json.dumps(asdict(c.key),sort_keys=True,separators=(',',':')).encode()
                changes.append({'cusip':c.key.cusip,'security_key':hashlib.sha256(identity).hexdigest(),'unit':c.key.quantity_type,'kind':c.kind,'reported_before':c.previous_quantity,'reported_after':c.current_quantity,'reported_delta':c.delta_quantity})
        reports.append({'manager_cik':pair['current']['metadata']['manager_cik'].zfill(10),'previous_quarter':pair['previous']['metadata']['quarter_end'],'current_quarter':pair['current']['metadata']['quarter_end'],'state':state,'changes':changes,'source_hashes':refs})
    financial=lambda companies:{'companies':companies,'method_status':'PROVISIONAL_UNCALIBRATED','availability_basis':'OBSERVED_CAPTURE_ONLY'}
    outputs={
        'sec-qg-factors.json':_envelope('sec-qg-factors.json',as_of,stale_after,financial(qg),sec_sources,[r['state'] for r in qg.values()]),
        'company-types-pricefree.json':_envelope('company-types-pricefree.json',as_of,stale_after,financial(types),sec_sources,[r['state'] for r in types.values()],type_reasons),
        'sec-filing-windows.json':_envelope('sec-filing-windows.json',as_of,stale_after,{'companies':windows},sec_sources,[r['state'] for r in windows.values()]),
        'macro-screen.json':_envelope('macro-screen.json',as_of,stale_after,macro,macro_sources,[_fresh(clock(o['available_at']),as_of,stale_after) for o in observations],('UNAPPROVED_ENGINE_INPUT_MAPPING','PUBLIC_FX_EXCLUDED')),
        'sec-13f-changes.json':_envelope('sec-13f-changes.json',as_of,stale_after,{'reports':reports,'role':'REPORTED_QUANTITY_CHANGE_NOT_TRADES'},report_sources,[r['state'] for r in reports]),
    }
    for name,payload in outputs.items():require_public_screen(name,payload)
    return outputs
