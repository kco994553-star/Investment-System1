"""Held-catalog issuer diagnostics, separate from market/security eligibility.

Uses the common classification and QGV engines. No network, issuer-to-security
identity substitution, new scoring rules, or change to the approved market gate.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import re
import zipfile

from .sector_qgv import digest, timestamp, day, preview_qgv
from .sector_qgv_registry import MAPPING
from .sector_qgv_held import checked_bytes, held_observations
from .sector_qgv_classification import link_classification, extend_held_classification
from .common_classification.records import from_sector_snapshot, resolve, validate, unknown
from .common_classification.qgv import project_qgv

VERSION='held-expanded-issuer-adapter/1'


def issuer_members(candidates):
    links=[]
    for r in candidates:
        cik=r.get('cik_str');ticker=r.get('ticker')
        if type(cik) not in (str,int) or not re.fullmatch(r'[0-9]{1,10}',str(cik)) or int(cik)<=0:
            raise ValueError('CATALOG_ISSUER_INVALID')
        if not isinstance(ticker,str) or not ticker or ticker.strip()!=ticker:raise ValueError('CATALOG_TICKER_INVALID')
        cik=str(cik).zfill(10)
        links.append({'analysis_row_id':'ISSUER:'+cik,'issuer_id':cik,'observed_ticker':ticker,
                      'security_id':None,'representative':None,'kind':'CATALOG_OBSERVATION_NOT_LISTING_PROOF'})
    links.sort(key=lambda r:(r['issuer_id'],r['observed_ticker']))
    return sorted({r['analysis_row_id'] for r in links}),links


def reuse_issuer_reviews(store,view,upstream_snapshot,financials,*,as_of):
    """Reuse the SAME evaluation's evidence-bearing issuer decision, not a ticker.

    Different source SIC/profile, conflicting class rows or future evidence are
    explicit conflicts. Sources retain their dates and upstream record IDs.
    """
    date=as_of[:10]
    if view['valuation_date']!=date or upstream_snapshot['valuation_date']!=date:
        raise ValueError('REVIEW_REUSE_VALUATION_MISMATCH')
    by_issuer=defaultdict(list);by_code={r['company_id']:r for r in upstream_snapshot['rows']}
    for r in view['rows']:
        if r.get('issuer_id'):by_issuer[r['issuer_id']].append(r)
    sources={s['source_id']:s for s in view['sources']};out=deepcopy(store)
    dest={s['source_id']:s for s in out['sources']};audit={'reused_issuers':0,'reasons':{},'rows':[]}
    for row in out['records']:
        candidates=by_issuer.get(row['issuer_id'],[])
        if not candidates:continue
        rec=financials.get(row['issuer_id'],{});reason=None
        signatures={digest({k:r[k] for k in ('sector','accounting','industry')}) for r in candidates}
        if len(signatures)!=1 or any(not r.get('record_id') for r in candidates):reason='UPSTREAM_ISSUER_REVIEW_AMBIGUOUS'
        for r in candidates:
            up=by_code.get(r['company_id'])
            if not up or up.get('issuer_id')!=row['issuer_id']:reason='UPSTREAM_ROW_ISSUER_MISMATCH';break
            if rec.get('sic') is not None and str(rec['sic']).zfill(4)!=str(up.get('source_sic')).zfill(4):reason='RETAINED_SIC_CHANGED';break
            if rec.get('profile') is not None and rec['profile']!=up.get('source_profile'):reason='RETAINED_ACCOUNTING_PROFILE_CHANGED';break
            for ref in r['source_refs']:
                source=sources.get(ref)
                if (not source or not source.get('acquired_at') or timestamp(source['acquired_at'])>timestamp(as_of)):
                    reason='UPSTREAM_SOURCE_UNAVAILABLE_AT_EVALUATION';break
                publication=source.get('published_at') or source.get('published_date')
                if publication and (day(publication)>day(date) if len(publication)==10 else timestamp(publication)>timestamp(as_of)):
                    reason='UPSTREAM_SOURCE_UNAVAILABLE_AT_EVALUATION';break
            if reason:break
        if reason:
            for k in ('sector','accounting','industry'):row[k]=unknown(reason)
            audit['reasons'][reason]=audit['reasons'].get(reason,0)+1
            audit['rows'].append({'issuer_id':row['issuer_id'],'status':'CONFLICT','reason':reason});continue
        source_row=sorted(candidates,key=lambda r:r['record_id'])[0]
        refs=[]
        for ref in source_row['source_refs']:
            source=deepcopy(sources[ref]);key=ref
            if key in dest and dest[key]!=source:key=ref+':metadata:'+digest(source)[:16];source['source_id']=key
            if key not in dest:out['sources'].append(source);dest[key]=source
            refs.append(key)
        row.update({k:deepcopy(source_row[k]) for k in ('sector','accounting','industry','source_sic','applicability','tags','rule_version')})
        row.update(source_refs=refs,upstream_record_ids=sorted(r['record_id'] for r in candidates),
                   upstream_company_ids=sorted(r['company_id'] for r in candidates),
                   upstream_classification_hash=view['classification_hash'],
                   upstream_reviewed_at=source_row.get('recorded_at'),
                   reuse_basis='SAME_ISSUER_EVALUATION_SIC_ACCOUNTING_PROFILE_NOT_SECURITY')
        row['record_id']='expanded-reuse:'+digest(row)[:32]
        audit['reused_issuers']+=1
        audit['rows'].append({'issuer_id':row['issuer_id'],'status':'REUSED','upstream_record_ids':row['upstream_record_ids']})
    return validate(out),audit


def _receipt_body(archive,receipt):
    body=archive.read(receipt['member'])
    if len(body)!=receipt['bytes'] or hashlib.sha256(body).hexdigest()!=receipt['sha256']:
        raise ValueError('ARCHIVE_MEMBER_HASH_MISMATCH')
    original=json.loads(archive.read(receipt['receipt_member']))
    for k in ('source_url','fetched_at','sha256','bytes','http_status'):
        if original.get(k)!=receipt.get(k):raise ValueError('ARCHIVE_RECEIPT_MISMATCH:'+k)
    if original['http_status']!=200:raise ValueError('ARCHIVE_SOURCE_NOT_SUCCESS')
    return json.loads(body)


def _normalize_sources(job,held,members,links,receipts):
    as_of=job['as_of']
    # One original retained archive, content pinned before any transformations.
    checked_bytes(job['archive'])
    rows=[];evidence={};audit={'financial_source_connected':0,'sector_raw_reconstructed':0,'calc23_raw_recomputed':0,'source_failures':{}}
    with zipfile.ZipFile(job['archive']['path']) as archive:
        catalog=_receipt_body(archive,receipts['sec_tickers'])
        if issuer_members(list(catalog.values()))!=(members,links):raise ValueError('CATALOG_CACHE_MISMATCH')
        for member in members:
            cik=member.split(':',1)[1];rec=held['financials'].get(cik)
            row=dict(company_id=member,issuer_id=cik,security_id=None,sector_id=None,accounting_template=None,
                     mapping=None,gate=None,observations={},source_sic=rec.get('sic') if rec else None,
                     source_profile=rec.get('profile') if rec else None)
            if rec:
                if rec.get('cik')!=cik or timestamp(rec['acquired_at'])>timestamp(as_of):raise ValueError('FINANCIAL_CONTEXT_MISMATCH')
                payloads={}
                for kind in ('companyfacts','submissions'):
                    receipt=receipts[kind+':'+cik]
                    if receipt['sha256']!=rec['source_sha256'][kind] or timestamp(receipt['fetched_at'])>timestamp(rec['acquired_at']):
                        raise ValueError('FINANCIAL_SOURCE_CACHE_MISMATCH')
                    payloads[kind]=_receipt_body(archive,receipt)
                    if str(payloads[kind].get('cik','')).zfill(10)!=cik:raise ValueError('SOURCE_ISSUER_MISMATCH')
                sub=payloads['submissions'];receipt=receipts['submissions:'+cik]
                evidence[member]={'issuer_id':cik,'sic':str(sub.get('sic','')).zfill(4),'sic_description':sub.get('sicDescription'),
                    'source_sha256':receipt['sha256'],'archive_sha256':job['archive']['sha256'],'member':receipt['member'],
                    'source_url':receipt['source_url'],'source_kind':'SEC_SUBMISSIONS','acquired_at':receipt['fetched_at']}
                audit['financial_source_connected']+=1
                if rec.get('state')=='NOT_AVAILABLE' or rec.get('calc_version')!='qgv2-calc/2026-10-23.1':
                    row['input_diagnostics']={'source':'SOURCE_NOT_AVAILABLE' if rec.get('state')=='NOT_AVAILABLE' else 'HELD_ROW_VERSION_MISMATCH'}
                else:
                    ref=receipts['companyfacts:'+cik]['member']+'#sha256='+rec['source_sha256']['companyfacts']
                    row['observations'],row['input_diagnostics']=held_observations(payloads['companyfacts'],rec,ref,as_of=as_of,valuation_date=as_of[:10])
                    audit['sector_raw_reconstructed']+=1
            else:row['input_diagnostics']={'source':'REQUIRED_COMPANYFACTS_SUBMISSIONS_PAIR_NOT_HELD'}
            rows.append(row)
    return rows,evidence,audit


def build(job):
    if job.get('schema_version')!='held-expanded-classification-job/1':raise ValueError('JOB_VERSION_INVALID')
    read=lambda k:json.loads(checked_bytes(job[k]))
    held=read('held');config=read('config');up_snapshot=read('upstream_snapshot');up_store=read('upstream_store')
    as_of=job['as_of'];recorded=job['recorded_at'];timestamp(as_of);timestamp(recorded)
    if timestamp(as_of)>timestamp(recorded):raise ValueError('REVIEW_PRECEDES_EVALUATION')
    members,links=issuer_members(held['candidates'])
    if held['source'].get('complete') is not False:raise ValueError('HELD_SCOPE_MUST_BE_EXPLICIT_PARTIAL')
    if timestamp(held['source']['observed_at'])>timestamp(as_of):raise ValueError('CATALOG_NOT_AVAILABLE')
    receipts={r['artifact_id']:r for r in held['receipts']}
    if len(receipts)!=len(held['receipts']):raise ValueError('DUPLICATE_RECEIPT')
    if 'retained_transform' in job:
        cache=job['retained_transform']; manifest=json.loads(checked_bytes(cache['manifest']))
        for key in ('held','archive'):
            if manifest['source_files'][key]['sha256']!=job[key]['sha256']:raise ValueError('TRANSFORM_SOURCE_MISMATCH')
        entries={r['path']:r for r in manifest['files']}
        for key,name in (('snapshot','snapshot.json'),('source_evidence','source-evidence.json')):
            if entries[name]['sha256']!=cache[key]['sha256']:raise ValueError('TRANSFORM_MANIFEST_MISMATCH')
        retained=json.loads(checked_bytes(cache['snapshot'])); evidence=json.loads(checked_bytes(cache['source_evidence']))
        if (retained['valuation_date']!=as_of[:10] or retained['members']!=members or
            {r['company_id'] for r in retained['rows']}!=set(members) or len(retained['rows'])!=len(members)):
            raise ValueError('TRANSFORM_POPULATION_OR_DATE_MISMATCH')
        rows=[]
        for old in retained['rows']:
            cik=old['company_id'].split(':',1)[1]; rec=held['financials'].get(cik,{})
            if (old['issuer_id']!=cik or old.get('source_sic')!=rec.get('sic') or old.get('source_profile')!=rec.get('profile') or
                any(o.get('source_available_at') and timestamp(o['source_available_at'])>timestamp(as_of) for o in old['observations'].values())):
                raise ValueError('TRANSFORM_ROW_CONTEXT_MISMATCH')
            rows.append({**{k:deepcopy(old[k]) for k in ('company_id','issuer_id','source_sic','source_profile','observations','input_diagnostics')},
                         'security_id':None,'sector_id':None,'accounting_template':None,'mapping':None,'gate':None})
        audit={'financial_source_connected':len(held['financials']),'sector_raw_reconstructed':0,
               'sector_raw_reused':sum(bool(r['observations']) for r in rows),'calc23_raw_recomputed':0,'source_failures':{}}
    else:
        rows,evidence,audit=_normalize_sources(job,held,members,links,receipts)
    snapshot={'schema_version':'sector-qgv-input/1','snapshot_id':'expanded-held-'+job['held']['sha256'][:16],
        'universe_id':'HELD_SEC_CATALOG_ISSUER_DIAGNOSTIC','universe_version':'1@'+held['source']['sha256'],
        'mapping_version':MAPPING,'input_version':VERSION,'as_of':as_of,'valuation_date':as_of[:10],
        'members':members,'rows':rows,'analysis_unit':'ISSUER_NOT_SECURITY','data_kind':job['data_kind']}
    classified,_=link_classification(snapshot,evidence)
    classified,_=extend_held_classification(classified,evidence)
    classified,_=extend_held_classification(classified,evidence,rule_version='held-sec-book-correspondence/0.3.0')
    # Invalid classification evidence is not promoted by passing it as an import source.
    import_evidence={r['company_id']:evidence[r['company_id']] for r in classified['rows'] if r.get('official_classification')}
    store=from_sector_snapshot(classified,import_evidence,source_sha256=digest(classified),recorded_at=recorded,data_kind=job['data_kind'])
    upstream=resolve(up_store,valuation_date=as_of[:10],knowledge_as_of=recorded)
    store,reuse=reuse_issuer_reviews(store,upstream,up_snapshot,held['financials'],as_of=as_of)
    view=resolve(store,valuation_date=as_of[:10],knowledge_as_of=recorded)
    projected=project_qgv(snapshot,view)
    preview=preview_qgv(config,projected,job['request_id'])
    financial_ids={c for c,r in held['financials'].items() if r.get('state')!='NOT_AVAILABLE'}
    def count_scope(issuers):
        selected=[r for r in preview['result_rows'] if r['issuer_id'] in issuers]
        cr=[r for r in view['rows'] if r['issuer_id'] in issuers]
        return {'issuers':len(issuers),'ticker_observations':sum(r['issuer_id'] in issuers for r in links),
            **{k:sum(r[k]['status']=='CONFIRMED' for r in cr) for k in ('sector','accounting','industry')},
            'raw':sum(any(f['raw_value'] is not None for f in r['factors'].values()) for r in selected),
            'factor_score':sum(any(f['score'] is not None for f in r['factors'].values()) for r in selected),
            **{a:sum(r['axes'][a] is not None for r in selected) for a in ('Q','G','V')},
            'joint':sum(all(x is not None for x in r['axes'].values()) for r in selected),'total':sum(r['total'] is not None for r in selected)}
    summary={'schema_version':'held-expanded-classification-summary/1','valuation_date':as_of[:10],
        'catalog_observed_at':held['source']['observed_at'],
        'catalog_age_days':(day(as_of[:10])-day(held['source']['observed_at'][:10])).days,
        'population_kind':'OBSERVED_CATALOG_ISSUERS_NOT_INVESTMENT_ELIGIBLE_UNIVERSE',
        'catalog':count_scope({r['issuer_id'] for r in links}),'held_financial_subsample':count_scope(financial_ids),
        'retained_financial_inputs':len(held['financials']),'retained_calc23_raw_issuers':len(financial_ids),
        'missing_financial_pairs':len(members)-len(held['financials']),
        'source_diagnostics':dict(Counter(r.get('input_diagnostics',{}).get('source','CONNECTED') for r in rows)),
        'classification_failures':view['unresolved_reasons'],'reuse':{k:v for k,v in reuse.items() if k!='rows'},
        'raw_observations':sum(c['raw_valid'] for c in preview['coverage']['factors'].values()),
        'full_market_denominator':None,'full_market_coverage':None,'rank_scope':'HELD_ISSUER_FACTOR_PERCENTILES_ONLY',
        'new_security_ids':0,'investment_eligibility_confirmed':0,'official_gate_connected':0,
        'performance':None,'historical_pit_certified':False,'official_universe_changed':False,'network_requests':0,'audit':audit}
    return {'snapshot.json':projected,'preview.json':preview,'classification-store.json':store,
            'classification-view.json':view,'source-evidence.json':evidence,'review-reuse.json':reuse,
            'catalog-crosswalk.json':links,'summary.json':summary,'config.json':config}
