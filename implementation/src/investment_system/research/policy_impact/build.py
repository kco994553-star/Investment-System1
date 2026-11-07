"""Append-only reviewed inputs -> as-of display, with no collection or scores."""
import copy
import hashlib
import json
from zoneinfo import ZoneInfo
from .contract import FIELDS,KEYS,Invalid,need,time,date,validate

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def append_only(previous,current):
    for group in FIELDS:
        now={tuple(r[k] for k in KEYS[group]):r for r in current[group]}
        for old in previous[group]:
            need(now.get(tuple(old[k] for k in KEYS[group]))==old,'HISTORY_MUTATION',group)
    for r in previous['review_records']:need(r in current['review_records'],'REVIEW_HISTORY_MUTATION','review_records')

def build(bundle,companies,as_of,*,public=False,public_macro_ids=(),previous=None,query_timezone='UTC'):
    index=validate(bundle,companies,public_macro_ids)
    if previous is not None:validate(previous,companies,public_macro_ids);append_only(previous,bundle)
    at=time(as_of,'as_of');memo={};reviews=[]
    def source_times(refs):return [available('sources',(r['source_id'],r['source_revision_id'])) for r in refs]
    def available(group,key):
        if (group,key) in memo:return memo[group,key]
        r=index[group][key];times=[]
        for k in ('recorded_at','created_at','change_recorded_at','reviewed_at','acquired_at','revision_acquired_at'):
            if r.get(k) is not None:times.append(time(r[k],k))
        if r.get('first_seen_at'):times.append(time(r['first_seen_at'],'first_seen_at'))
        times+=source_times(r.get('evidence_refs',[]))
        if group=='policies':times+=source_times(r['identity_basis']['relation_evidence_refs'])
        if group in ('exposures','hypotheses'):times.append(available('policies',(r['policy_id'],r['policy_revision_id'])))
        if group=='hypotheses':
            for e in r['exposure_refs']:times.append(available('exposures',(e['exposure_id'],e['exposure_revision_id'])))
            for step in r['steps']:times+=source_times(step['evidence_refs'])
        result=max(times);memo[group,key]=result;return result
    for review in bundle['review_records']:
        if public and any(index['sources'][(r['source_id'],r['source_revision_id'])]['verification_status']!='VERIFIED' for r in review['evidence_refs']):continue
        if max([time(review['reviewed_at'],'reviewed_at'),time(review['recorded_at'],'recorded_at'),*source_times(review['evidence_refs'])])<=at:reviews.append(review)
    out={k:copy.deepcopy(v) for k,v in bundle.items() if k not in FIELDS}
    out['policy_as_of']=bundle['policy_as_of'] if time(bundle['policy_as_of'],'policy_as_of')<=at else None;out['review_records']=copy.deepcopy(reviews)
    if out['policy_as_of'] is None:out['freshness']['reason_codes'].append('POLICY_CHECK_NOT_AVAILABLE_AT_QUERY')
    for group in FIELDS:
        rows=[]
        for key,original in index[group].items():
            if available(group,key)>at:continue
            row=copy.deepcopy(original)
            if group!='sources':
                rs=[r for r in reviews if r['group']==group and (r['id'],r['revision_id'])==key]
                # A declared review requires its independent, timestamped source check.
                if rs:
                    row['reviewed_at']=max((r['reviewed_at'] for r in rs),key=lambda v:time(v,'reviewed_at'))
                    if row['review_status']=='UNREVIEWED':row['review_status']='REVIEWED'
                elif row['review_status']!='UNREVIEWED':continue
            rows.append(row)
        out[group]=rows
    # Public output is a fixed-field projection of validated data, never raw input.
    if public:
        for group in ('policies','exposures','hypotheses'):
            out[group]=[r for r in out[group] if r['review_status']!='UNREVIEWED' and not (group=='exposures' and r['evidence_status']=='CANDIDATE')]
        out['sources']=[s for s in out['sources'] if s['verification_status']=='VERIFIED']
    # Dependency closure prevents dangling references after time/public filtering.
    while True:
        before=sum(len(out[g]) for g in FIELDS)
        ids={g:{tuple(r[k] for k in KEYS[g]) for r in out[g]} for g in FIELDS}
        def refs_ok(refs):return all((r['source_id'],r['source_revision_id']) in ids['sources'] for r in refs)
        policy_ids={k[0] for k in ids['policies']}
        out['policies']=[p for p in out['policies'] if refs_ok(p['evidence_refs']) and refs_ok(p['identity_basis']['relation_evidence_refs']) and (not p['parent_policy_id'] or p['parent_policy_id'] in policy_ids) and (not p['supersedes_revision_id'] or (p['policy_id'],p['supersedes_revision_id']) in ids['policies'])]
        out['exposures']=[e for e in out['exposures'] if (e['policy_id'],e['policy_revision_id']) in ids['policies'] and refs_ok(e['evidence_refs'])]
        out['hypotheses']=[h for h in out['hypotheses'] if (h['policy_id'],h['policy_revision_id']) in ids['policies'] and all((r['exposure_id'],r['exposure_revision_id']) in ids['exposures'] for r in h['exposure_refs']) and all(refs_ok(s['evidence_refs']) for s in h['steps'])]
        if sum(len(out[g]) for g in FIELDS)==before:break
    # Select latest recorded revision; history remains in the input ledger.
    all_policies=out['policies'];latest={}
    for p in all_policies:
        pid=p['policy_id'];old=latest.get(pid)
        if old is None or (time(p['change_recorded_at'],'change_recorded_at'),p['revision_id'])>(time(old['change_recorded_at'],'change_recorded_at'),old['revision_id']):latest[pid]=p
    for group in ('exposures','hypotheses'):
        for r in out[group]:
            if latest[r['policy_id']]['revision_id']!=r['policy_revision_id']:r['review_status']='REVIEW_REQUIRED'
    # Preserve referenced old revisions in the displayed bundle, with separate current IDs.
    out['policies']=sorted(all_policies,key=lambda r:(-time(r['change_recorded_at'],'change_recorded_at').timestamp(),r['policy_id'],r['revision_id']))
    for group in ('exposures','hypotheses'):
        out[group].sort(key=lambda r:tuple(r[k] for k in KEYS[group]))
    out['freshness']['review_due']=None if not latest or any(p['next_review_on'] is None for p in latest.values()) else any(at.astimezone(ZoneInfo(query_timezone)).date()>date(p['next_review_on'],'next_review_on') for p in latest.values())
    # reviewed_at denotes latest retained content review, never collection success.
    shown={(g,tuple(r[k] for k in KEYS[g])) for g in ('policies','exposures','hypotheses') for r in out[g]}
    out['review_records']=[r for r in out['review_records'] if (r['group'],(r['id'],r['revision_id'])) in shown]
    out['freshness']['last_reviewed_at']=max((r['reviewed_at'] for r in out['review_records']),key=lambda v:time(v,'reviewed_at'),default=None)
    checked=out['freshness']['last_source_check_at']
    if checked is not None and time(checked,'last_source_check_at')>at:
        out['freshness']['last_source_check_at']=None
        out['freshness']['reason_codes'].append('SOURCE_CHECK_HISTORY_UNAVAILABLE_AT_QUERY')
    def trim_refresh(r):
        future=any(r.get(k) is not None and time(r[k],k)>at for k in ('last_attempt_at','last_success_at','last_manual_review_at','retained_policy_as_of'))
        if future:
            r.update(result='NOT_RUN' if r['mode']=='AUTOMATED' else None,last_attempt_at=None,last_success_at=None,last_manual_review_at=None,retained_bundle_id=None,retained_policy_as_of=None,incomplete_ranges=[])
            out['freshness']['reason_codes'].append('REFRESH_HISTORY_UNAVAILABLE_AT_QUERY')
        for source in r['sources']:trim_refresh(source)
    trim_refresh(out['refresh'])
    return {'query_timezone':query_timezone,'schema_version':'policy-impact-view/1','bundle':out,'current_policy_revisions':{k:p['revision_id'] for k,p in latest.items()},'as_of':as_of,'historical_pit_eligible':False}

def collection_outcome(*,http_status,parsed,complete,truncated=False,new_items=0,incomplete_ranges=()):
    if http_status!=200 or not parsed:return {'result':'FAILED','reason':'SOURCE_FAILURE','checkpoint_advance':False}
    if not complete or truncated:return {'result':'INCOMPLETE','reason':'PAGE_OR_REQUEST_LIMIT','checkpoint_advance':False,'incomplete_ranges':list(incomplete_ranges)}
    return {'result':'UPDATED' if new_items else 'NO_NEW_ITEMS','reason':None,'checkpoint_advance':True}

def retain_good(previous,attempt):
    need(attempt['result'] in ('FAILED','PARTIAL_FAILED','INCOMPLETE'),'NOT_FAILURE','attempt')
    result=copy.deepcopy(previous)
    result['refresh'].update(mode='AUTOMATED',result=attempt['result'],last_attempt_at=attempt['at'],retained_bundle_id=previous['bundle_id'],retained_policy_as_of=previous['policy_as_of'],incomplete_ranges=attempt.get('incomplete_ranges',[]))
    return result

def from_discovery_fact(fact,source,exposure):
    """Reuse #503 SOURCE_EXTRACT receipts/period/region; never parse a second time."""
    need(fact.get('origin')=='SOURCE_EXTRACT' and fact.get('source_assertion') is True,'NOT_SOURCE_EXTRACT','fact')
    need(fact['company_id']==exposure['company_id'],'COMPANY_REF','fact')
    s=copy.deepcopy(source);e=copy.deepcopy(exposure)
    s.update(url=fact['source_url'],content_sha256=fact['sha256'],document_id=fact['document_id'],acquired_at=fact['acquired_at'],revision_acquired_at=fact['acquired_at'],evidence_locator=json.dumps(fact['locator'],sort_keys=True))
    e.update(period=copy.deepcopy(fact['period']),ratio=None,reason_codes=['RATIO_NOT_ESTABLISHED'])
    return s,e

def from_news_reference(article,source):
    """#483 metadata -> reference only. First discovery is never publication."""
    s=copy.deepcopy(source);s.update(kind='NEWS_REFERENCE',url=article['link'],title=article['title'],first_seen_at=article.get('source_seen_at'))
    s['published']={'value':None,'precision':'UNKNOWN','timezone':None}
    s['verification_status']='SOURCE_UNVERIFIED'
    return s
