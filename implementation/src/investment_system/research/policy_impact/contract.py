"""policy-impact/1: strict evidence/revision contract, no transport or scoring."""
import datetime as dt
import math
from urllib.parse import urlsplit

SCHEMA='policy-impact/1'
WATCH_AVAILABILITY={'PUBLIC_REFERENCE','UNAVAILABLE','UNKNOWN'}
FIELDS={
'sources': 'source_id source_revision_id kind publisher url title document_id published first_seen_at acquired_at revision_acquired_at verification_status evidence_locator content_sha256 data_kind',
'policies': 'policy_id revision_id supersedes_revision_id policy_type title issuer jurisdiction target_regions scope_description lifecycle_status published effective_from effective_to evidence_refs recorded_at change_recorded_at reviewed_at review_status next_review_on identity_basis subsidy_stage parent_policy_id data_kind',
'exposures': 'exposure_id exposure_revision_id company_id policy_id policy_revision_id exposure_type evidence_status policy_applicability description period evidence_refs recorded_at reviewed_at review_status ratio reason_codes data_kind',
'hypotheses': 'hypothesis_id hypothesis_revision_id policy_id policy_revision_id company_ids exposure_refs claim steps conditions counter_conditions watch_items created_at recorded_at reviewed_at review_status data_kind',
}
TOP='schema_version bundle_id generated_at data_kind policy_as_of score_effect gate_effect scope sources policies exposures hypotheses refresh reason_codes historical_pit_eligible freshness review_records'.split()
KEYS={'sources':('source_id','source_revision_id'),'policies':('policy_id','revision_id'),
      'exposures':('exposure_id','exposure_revision_id'),'hypotheses':('hypothesis_id','hypothesis_revision_id')}
ENUMS={
 'kind':{'OFFICIAL_RULE','OFFICIAL_RELEASE','COMPANY_FILING','NEWS_REFERENCE'},
 'policy_type':{'TARIFF','EXPORT_CONTROL','INDUSTRIAL_SUBSIDY'},
 'lifecycle_status':{'STATEMENT','PROPOSED','ADOPTED','EFFECTIVE','SUSPENDED','WITHDRAWN','EXPIRED','UNKNOWN'},
 'review_status':{'UNREVIEWED','REVIEWED','REVIEW_REQUIRED'},
 'verification_status':{'VERIFIED','SOURCE_UNVERIFIED','CONFLICTING_EVIDENCE'},
 'exposure_type':{'REVENUE_REGION','PRODUCTION_SITE','PROCUREMENT','CONTROLLED_PRODUCT','SUBSIDY_PROJECT'},
 'evidence_status':{'DOCUMENTED','CANDIDATE','UNKNOWN'},
 'policy_applicability':{'DOCUMENTED','UNCONFIRMED','OUTSIDE_SCOPE'},
 'subsidy_stage':{'PRELIMINARY_TERMS','FINAL_AWARD','DISBURSEMENT_CONFIRMED','UNKNOWN'},
}

class Invalid(ValueError):
    def __init__(self,code,path):self.code=code;self.path=path;super().__init__(code+':'+path)

def need(ok,code,path):
    if not ok:raise Invalid(code,path)

def shape(value,fields,path):
    need(isinstance(value,dict) and set(value)==set(fields),'FIELDS',path)

def time(value,path):
    try:
        need(isinstance(value,str),'TIME',path)
        result=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        need(result.tzinfo is not None and result.utcoffset()==dt.timedelta(0),'UTC_REQUIRED',path)
        return result
    except (TypeError,ValueError):raise Invalid('TIME',path) from None

def date(value,path):
    try:
        need(isinstance(value,str) and len(value)==10,'DATE',path)
        return dt.date.fromisoformat(value)
    except (TypeError,ValueError):raise Invalid('DATE',path) from None

def temporal(value,path):
    shape(value,['value','precision','timezone'],path)
    need(value['timezone'] is None or isinstance(value['timezone'],str),'TIMEZONE_TYPE',path)
    p=value['precision'];v=value['value']
    if p=='UNKNOWN':need(v is None and value['timezone'] is None,'PRECISION',path)
    elif p=='DATE':date(v,path);need(value['timezone'] is None,'DATE_TIMEZONE',path)
    elif p=='DATETIME':
        try:need(dt.datetime.fromisoformat(v.replace('Z','+00:00')).tzinfo is not None,'OFFSET_REQUIRED',path)
        except (ValueError,TypeError,AttributeError):raise Invalid('TIME',path) from None
    else:raise Invalid('PRECISION',path)

def url(value,path):
    try:
        parsed=urlsplit(value)
        need(parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password,'UNSAFE_URL',path)
    except (ValueError,TypeError):raise Invalid('UNSAFE_URL',path) from None

def validate(bundle,companies,public_macro_ids=()):
    shape(bundle,TOP,'$')
    need(bundle['schema_version']==SCHEMA,'VERSION','$.schema_version')
    need(bundle['score_effect']==bundle['gate_effect']=='NONE','FORBIDDEN_EFFECT','$')
    need(bundle['historical_pit_eligible'] is False,'PIT_UNPROVEN','$')
    need(bundle['data_kind'] in ('SYNTHETIC','REAL_REVIEWED'),'DATA_KIND','$')
    need(isinstance(bundle['bundle_id'],str) and bool(bundle['bundle_id']),'TEXT','bundle_id')
    time(bundle['generated_at'],'$.generated_at');time(bundle['policy_as_of'],'$.policy_as_of')
    shape(bundle['scope'],['policy_types','jurisdictions','source_scope','coverage_kind'],'$.scope')
    need(bundle['scope']['coverage_kind']=='CURATED_SAMPLE','COVERAGE','$')
    need(set(bundle['scope']['policy_types'])<=ENUMS['policy_type'],'TYPE','$.scope')
    indexes={}
    for group,fields in FIELDS.items():
        need(isinstance(bundle[group],list),'ARRAY',group);index={}
        for i,row in enumerate(bundle[group]):
            path=f'$.{group}[{i}]';shape(row,fields.split(),path)
            need(row['data_kind']==bundle['data_kind'],'MIXED_KIND',path)
            key=tuple(row[x] for x in KEYS[group])
            need(all(isinstance(v,str) and v.strip() for v in key),'ID',path)
            need(key not in index,'DUPLICATE_REVISION',path);index[key]=row
            for k,allowed in ENUMS.items():
                if k in row and row[k] is not None:need(row[k] in allowed,'ENUM',path+'.'+k)
            for k in ('recorded_at','change_recorded_at','created_at','acquired_at','revision_acquired_at'):
                if k in row:time(row[k],path+'.'+k)
            if 'reviewed_at' in row and row['reviewed_at'] is not None:time(row['reviewed_at'],path+'.reviewed_at')
            for k in ('document_id','supersedes_revision_id','parent_policy_id','subsidy_stage'):
                if k in row:need(row[k] is None or isinstance(row[k],str),'TEXT',path+'.'+k)
            if 'published' in row:temporal(row['published'],path+'.published')
        indexes[group]=index
    def refs(refs,path):
        need(isinstance(refs,list) and bool(refs),'EVIDENCE_REQUIRED',path)
        for ref in refs:
            shape(ref,['source_id','source_revision_id','locator','claim'],path)
            need((ref['source_id'],ref['source_revision_id']) in indexes['sources'],'SOURCE_REF',path)
            need(isinstance(ref['locator'],str) and bool(ref['locator']) and isinstance(ref['claim'],str) and bool(ref['claim']),'EVIDENCE_LOCATION',path)
    # Strict nested primitives prevent private objects being smuggled into text arrays.
    def texts(values,path):
        need(isinstance(values,list) and all(isinstance(v,str) for v in values),'TEXT_ARRAY',path)
    for field in ('policy_types','jurisdictions','source_scope'):texts(bundle['scope'][field],'scope.'+field)
    texts(bundle['reason_codes'],'reason_codes');texts(bundle['freshness']['reason_codes'],'freshness.reason_codes')
    for group,rows in indexes.items():
        for row in rows.values():
            for field in ('title','issuer','jurisdiction','scope_description','description','claim','publisher','url','content_sha256','evidence_locator'):
                if field in row:need(isinstance(row[field],str) and bool(row[field]),'TEXT',group+'.'+field)
            for field in ('target_regions','company_ids','conditions','counter_conditions','reason_codes'):
                if field in row:texts(row[field],group+'.'+field)
    for key,s in indexes['sources'].items():
        url(s['url'],'sources.url');need(isinstance(s['content_sha256'],str) and len(s['content_sha256'])==64 and all(c in '0123456789abcdef' for c in s['content_sha256']),'SOURCE_HASH','sources.content_sha256')
        need(time(s['acquired_at'],'sources')<=time(s['revision_acquired_at'],'sources'),'SOURCE_TIME_ORDER','sources')
        if s['first_seen_at'] is not None:time(s['first_seen_at'],'sources.first_seen_at')
        need(bool(s['evidence_locator']),'EVIDENCE_LOCATION','sources')
    for key,p in indexes['policies'].items():
        refs(p['evidence_refs'],'policies.evidence_refs')
        shape(p['identity_basis'],['method','issuer','document_id','relation_evidence_refs'],'policies.identity_basis')
        b=p['identity_basis'];need(b['method'] in ('ISSUER_DOCUMENT_VERIFIED_RELATION','ISSUER_OFFICIAL_URL') and b['issuer']==p['issuer'] and (bool(b['document_id']) or b['method']=='ISSUER_OFFICIAL_URL'),'UNSTABLE_POLICY_ID','policies.identity_basis')
        need(any(indexes['sources'][(r['source_id'],r['source_revision_id'])]['kind'] in ('OFFICIAL_RULE','OFFICIAL_RELEASE') and indexes['sources'][(r['source_id'],r['source_revision_id'])]['document_id']==b['document_id'] and indexes['sources'][(r['source_id'],r['source_revision_id'])]['publisher']==p['issuer'] for r in p['evidence_refs']),'IDENTITY_EVIDENCE','policies')
        old=p['supersedes_revision_id']
        if old is not None:
            need((p['policy_id'],old) in indexes['policies'],'REVISION_REF','policies')
            refs(b['relation_evidence_refs'],'policies.revision_relation')
        if b['relation_evidence_refs']:refs(b['relation_evidence_refs'],'policies.relation_refs')
        if p['parent_policy_id'] is not None:need(any(k[0]==p['parent_policy_id'] for k in indexes['policies']),'PARENT_REF','policies')
        for k in ('effective_from','effective_to'):temporal(p[k],'policies.'+k)
        if p['next_review_on'] is not None:date(p['next_review_on'],'policies.next_review_on')
        need((p['policy_type']=='INDUSTRIAL_SUBSIDY')==(p['subsidy_stage'] is not None),'SUBSIDY_STAGE','policies')
    for key,e in indexes['exposures'].items():
        need(e['company_id'] in companies,'COMPANY_REF','exposures.company_id')
        need((e['policy_id'],e['policy_revision_id']) in indexes['policies'],'POLICY_REF','exposures')
        refs(e['evidence_refs'],'exposures.evidence_refs')
        shape(e['period'],['start','end'],'exposures.period')
        for v in e['period'].values():
            if v is not None:date(v,'exposures.period')
        r=e['ratio']
        if r is None:need(bool(e['reason_codes']),'NULL_REASON','exposures.ratio')
        else:
            shape(r,['value','unit','denominator_description','period','scope'],'exposures.ratio')
            need(type(r['value']) in (int,float) and math.isfinite(r['value']) and r['unit']=='fraction' and 0<=r['value']<=1,'RATIO','exposures.ratio')
            need(r['period']==e['period'] and isinstance(r['scope'],str) and bool(r['scope']) and isinstance(r['denominator_description'],str) and bool(r['denominator_description']),'RATIO_SCOPE','exposures.ratio')
    for key,h in indexes['hypotheses'].items():
        need((h['policy_id'],h['policy_revision_id']) in indexes['policies'],'POLICY_REF','hypotheses')
        need(bool(h['company_ids']) and set(h['company_ids'])<=set(companies),'COMPANY_REF','hypotheses')
        need(bool(h['conditions']) and bool(h['counter_conditions']) and bool(h['steps']),'CONDITIONS_REQUIRED','hypotheses')
        for r in h['exposure_refs']:
            shape(r,['exposure_id','exposure_revision_id'],'hypotheses.exposure_refs')
            e=indexes['exposures'].get((r['exposure_id'],r['exposure_revision_id']))
            need(e is not None and e['company_id'] in h['company_ids'] and e['policy_id']==h['policy_id'] and e['policy_revision_id']==h['policy_revision_id'],'EXPOSURE_REF','hypotheses')
        for step in h['steps']:
            shape(step,['text','epistemic_status','evidence_refs'],'hypotheses.steps')
            need(isinstance(step['text'],str),'TEXT','hypotheses.steps')
            need(step['epistemic_status'] in ('SUPPORTED_FACT','HYPOTHESIS','UNKNOWN'),'EPISTEMIC','hypotheses.steps')
            if step['evidence_refs']:refs(step['evidence_refs'],'hypotheses.steps')
            if step['epistemic_status']=='SUPPORTED_FACT':need(bool(step['evidence_refs']),'EVIDENCE_REQUIRED','hypotheses.steps')
        for w in h['watch_items']:
            shape(w,['kind','reference_id','rationale','availability'],'hypotheses.watch_items')
            need(all(isinstance(v,str) for v in w.values()),'TEXT','hypotheses.watch_items')
            need(w['availability'] in WATCH_AVAILABILITY,'WATCH_AVAILABILITY','hypotheses.watch_items.availability')
            need(w['kind'] in ('MACRO_SERIES','COMPANY_DISCLOSURE','POLICY_UPDATE'),'WATCH_KIND','hypotheses')
            if w['kind']=='MACRO_SERIES':need(w['reference_id'] in public_macro_ids or w['availability']=='UNAVAILABLE','PRIVATE_MACRO_REF','hypotheses')
    # Revision and parent links must be acyclic (all other dependencies are typed).
    def walk(key,stack):
        need(key not in stack,'DEPENDENCY_CYCLE','policies')
        p=indexes['policies'][key]
        if p['supersedes_revision_id']:walk((key[0],p['supersedes_revision_id']),stack|{key})
        if p['parent_policy_id']:
            for other in indexes['policies']:
                if other[0]==p['parent_policy_id']:walk(other,stack|{key})
    for key in indexes['policies']:walk(key,set())
    for pid in {key[0] for key in indexes['policies']}:
        rows=[p for (k,_),p in indexes['policies'].items() if k==pid]
        need(len({(p['issuer'],p['policy_type'],p['jurisdiction']) for p in rows})==1,'POLICY_IDENTITY_MUTATION','policies')
        need(sum(p['supersedes_revision_id'] is None for p in rows)==1,'REVISION_CHAIN','policies')
        parents=[p['supersedes_revision_id'] for p in rows if p['supersedes_revision_id'] is not None]
        need(len(parents)==len(set(parents)),'REVISION_FORK','policies')
        for p in rows:
            if p['supersedes_revision_id']:
                old=indexes['policies'][pid,p['supersedes_revision_id']]
                need(time(p['change_recorded_at'],'policies')>time(old['change_recorded_at'],'policies'),'REVISION_TIME','policies')
    for r in bundle['review_records']:
        shape(r,['group','id','revision_id','reviewed_at','recorded_at','reviewer','author','method','evidence_refs'],'review_records')
        need(r['group'] in ('policies','exposures','hypotheses') and (r['id'],r['revision_id']) in indexes[r['group']],'REVIEW_REF','review_records')
        need(r['reviewer']!=r['author'] and r['method'] in ('AI_INDEPENDENT_SOURCE_CHECK','HUMAN_SOURCE_CHECK'),'INDEPENDENT_REVIEW','review_records')
        need(all(isinstance(r[k],str) for k in ('group','id','revision_id','reviewer','author','method')),'TEXT','review_records')
        time(r['recorded_at'],'review_records');time(r['reviewed_at'],'review_records');refs(r['evidence_refs'],'review_records')
    shape(bundle['freshness'],['last_source_check_at','last_reviewed_at','review_due','reason_codes'],'freshness')
    for k in ('last_source_check_at','last_reviewed_at'):
        if bundle['freshness'][k] is not None:time(bundle['freshness'][k],'freshness')
    need(bundle['freshness']['review_due'] is None or type(bundle['freshness']['review_due']) is bool,'BOOLEAN','freshness.review_due')
    def refresh(r):
        shape(r,['mode','result','last_attempt_at','last_success_at','last_manual_review_at','retained_bundle_id','retained_policy_as_of','sources','incomplete_ranges'],'refresh')
        need(r['mode'] in ('MANUAL_REVIEW','AUTOMATED'),'REFRESH_MODE','refresh')
        if r['mode']=='MANUAL_REVIEW':need(r['result'] is None and r['last_attempt_at'] is None and r['last_success_at'] is None,'MANUAL_NOT_AUTO','refresh')
        else:need(r['result'] in ('UPDATED','NO_NEW_ITEMS','PARTIAL_FAILED','FAILED','NOT_RUN','INCOMPLETE'),'REFRESH_RESULT','refresh')
        for k in ('last_attempt_at','last_success_at','last_manual_review_at','retained_policy_as_of'):
            if r[k] is not None:time(r[k],'refresh.'+k)
        need(r['retained_bundle_id'] is None or isinstance(r['retained_bundle_id'],str),'TEXT','refresh.retained_bundle_id')
        texts(r['incomplete_ranges'],'refresh.incomplete_ranges')
        if r['result']=='INCOMPLETE':need(bool(r['incomplete_ranges']),'INCOMPLETE_RANGE','refresh')
        for source in r['sources']:refresh(source)
    refresh(bundle['refresh'])
    return indexes
