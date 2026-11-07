"""Federal Register metadata replay adapter. Plans only; never performs HTTP.

Shares the existing news request budget/Retry-After rules and policy failure
projection. Policy candidates have their own document ledger because the news
ledger requires corporate issuer IDs and news-source enums.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urlencode
from investment_system.providers.dart_collection import CallBudget
from investment_system.providers.news_feeds import retry_after_seconds,MAX_BODY_BYTES
from .build import collection_outcome,retain_good

VERSION='policy-fr-replay/1'
ENDPOINT='https://www.federalregister.gov/api/v1/documents.json'
DEFAULTS={'max_requests':12,'max_pages':20,'per_page':100,'overlap_days':7,'window_days':7,'max_body_bytes':MAX_BODY_BYTES,'cooldown_seconds':600}


def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def instant(x):
    t=datetime.fromisoformat(x.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('FR_TIMEZONE_REQUIRED')
    return t

def config(c):
    if set(c)!=set(DEFAULTS) or any(type(v)!=int or v<1 for v in c.values()):raise ValueError('FR_CONFIG_INVALID')
    if c['max_requests']>40 or c['max_pages']>20 or c['per_page']>100 or c['window_days']>31 or c['overlap_days']>31 or c['max_body_bytes']>MAX_BODY_BYTES or c['cooldown_seconds']>86400:raise ValueError('FR_LIMIT_EXCEEDED')


def initial(start,*,data_kind='SYNTHETIC'):
    date.fromisoformat(start)
    if data_kind not in ('SYNTHETIC','RETAINED_API'):raise ValueError('FR_KIND_INVALID')
    return {'schema_version':VERSION,'data_kind':data_kind,'scope_start':start,'completed_through':None,
            'reconcile_from':start,'split_ranges':[],'tracked_after':None,'ranges':{},'documents':{},'candidates':{},'last_attempt_at':None,
            'last_success_at':None,'result':'NOT_RUN','retry_at':None,'attempts':[]}


def url(start,end,page,per_page):
    return ENDPOINT+'?'+urlencode({'conditions[publication_date][gte]':start,'conditions[publication_date][lte]':end,
                                  'order':'oldest','per_page':per_page,'page':page})


def plan(state,through,now,settings=None):
    c=settings or DEFAULTS;config(c);end=date.fromisoformat(through);at=instant(now);start=date.fromisoformat(state['scope_start'])
    if end>at.astimezone(timezone.utc).date() or end<start:raise ValueError('FR_SCOPE_INVALID')
    if state.get('retry_at') and at<instant(state['retry_at']):return {'requests':[],'reason':'RETRY_AFTER_PENDING','next_retry_at':state['retry_at'],'limits':c}
    active=[x for x in state['ranges'].values() if not x['complete']]+state.get('split_ranges',[])
    def pending_overlap(a,b):return any(a<=x['end'] and b>=x['start'] for x in active)
    windows=[]
    for item in state['ranges'].values():
        if not item['complete']:windows.append((item['start'],item['end'],item['next_page'],'RESUME'))
    windows.extend((x['start'],x['end'],1,'SPLIT_RETRY') for x in state.get('split_ranges',[]) if not x.get('blocked'))
    frontier=date.fromisoformat(state['completed_through']) if state['completed_through'] else start-timedelta(days=1)
    inc=max(start,frontier+timedelta(days=1));last=min(end,inc+timedelta(days=c['window_days']-1))
    if inc<=end and not pending_overlap(str(inc),str(last)):windows.append((str(inc),str(last),1,'INCREMENTAL'))
    if frontier>=start:
        a,b=str(max(start,frontier-timedelta(days=c['overlap_days']-1))),str(min(frontier,end))
        if not pending_overlap(a,b):windows.append((a,b,1,'OVERLAP'))
    # A bounded historical sweep revisits older dates; no finite overlap guarantees
    # arbitrary-late backfills. Only the configured scope is claimed scanned.
    sweep=date.fromisoformat(state['reconcile_from'])
    if sweep<=min(frontier,end):
        a,b=str(sweep),str(min(frontier,end,sweep+timedelta(days=c['window_days']-1)))
        if not pending_overlap(a,b):windows.append((a,b,1,'RECONCILE'))
    requests=[];seen=set()
    for a,b,page,kind in windows:
        if (a,b) in seen:continue
        seen.add((a,b));requests.append({'range_id':a+'/'+b,'start':a,'end':b,'page':page,'kind':kind,'url':url(a,b,page,c['per_page'])})
    # Tracked document refresh catches modifications older than the overlap.
    docs=sorted(state['documents']);last=state.get('tracked_after')
    docs=[d for d in docs if not last or d>last]+[d for d in docs if last and d<=last]
    for doc in docs:
        number=doc.removeprefix('FR:');requests.append({'document_number':number,'kind':'TRACKED_DOCUMENT',
            'url':'https://www.federalregister.gov/api/v1/documents/'+number+'.json'})
    return {'requests':requests[:c['max_requests']],'limits':dict(c),'through':through,'scope_start':state['scope_start'],
            'checkpoint_meaning':'COMPLETED_PUBLICATION_DATE_INTERVALS_NOT_POLICY_PIT_OR_ALL_REVISIONS',
            'blocked_ranges':[x for x in state.get('split_ranges',[]) if x.get('blocked')],
            'automatic_publication':False}


def normalize(raw):
    if not isinstance(raw,dict):raise ValueError('FR_DOCUMENT_INVALID')
    number=raw.get('document_number');published=raw.get('publication_date');agencies=raw.get('agencies')
    if not isinstance(number,str) or not re.fullmatch(r'(?:\d{4}-\d{4,6}|[A-Z]\d-\d+)',number):raise ValueError('FR_DOCUMENT_NUMBER_INVALID')
    date.fromisoformat(published)
    if not isinstance(agencies,list) or not agencies:raise ValueError('FR_AGENCY_MISSING')
    names=[]
    for a in agencies:
        if not isinstance(a,dict) or not isinstance(a.get('name'),str) or not a['name']:raise ValueError('FR_AGENCY_MISSING')
        names.append(a['name'])
    title=raw.get('title');link=raw.get('html_url')
    if not isinstance(title,str) or not title or len(title)>4096 or not isinstance(link,str) or not link.startswith('https://www.federalregister.gov/documents/'):raise ValueError('FR_TEXT_OR_URL_INVALID')
    out={'document_id':'FR:'+number,'document_number':number,'agencies':sorted(set(names)),
         'title':title,'url':link,'published':{'value':published,'precision':'DATE','timezone':None}}
    for field in ('type','abstract','effective_on'):
        value=raw.get(field)
        if value is not None and (not isinstance(value,str) or len(value)>20000):raise ValueError('FR_METADATA_INVALID')
        if field=='effective_on' and value is not None:date.fromisoformat(value)
        out[field]=value
    # effective_on is received metadata, never inferred lifecycle or scope.
    return out


def _record(state,row,acquired,response_hash):
    key=row['document_id'];h=digest(row);old=state['documents'].get(key)
    if old and instant(acquired)<instant(old['last_seen_at']):return 'OLDER_RESPONSE'
    candidate_id=key+':'+h
    if old and h in old['versions']:
        previous=old['head_hash'];old['last_seen_at']=acquired;old['head_hash']=h
        if previous==h:return 'DUPLICATE'
        # A -> B -> A is a new observation of changed content, not a new
        # policy amendment or a duplicate. Immutable source versions remain.
        event={'from':previous,'to':h,'acquired_at':acquired,'response_sha256':response_hash}
        old.setdefault('changes',[]).append(event)
        candidate=state['candidates'][candidate_id]
        candidate.setdefault('reappearance_events',[]).append(copy.deepcopy(event))
        candidate['status']='UNREVIEWED'
        return 'CONTENT_CHANGED'
    change='CONTENT_CHANGED' if old else 'NEW_DOCUMENT'
    entry=copy.deepcopy(row)|{'content_sha256':h,'response_sha256':response_hash,'acquired_at':acquired,
        'first_seen_at':acquired,'status':'UNREVIEWED','policy_id':None,'policy_revision_id':None,
        'policy_relation':'NOT_ESTABLISHED','lifecycle_status':'UNKNOWN','company_applicability':'UNKNOWN',
        'hypothesis':None,'automatic_publication':False,'previous_content_sha256':old['head_hash'] if old else None,'change':change}
    if old is None:old={'versions':{},'head_hash':None,'last_seen_at':acquired};state['documents'][key]=old
    old.setdefault('changes',[]).append({'from':old['head_hash'],'to':h,'acquired_at':acquired,'response_sha256':response_hash})
    old['versions'][h]=entry;old['head_hash']=h;old['last_seen_at']=acquired
    state['candidates'][candidate_id]=copy.deepcopy(entry)
    return change


def _advance(state):
    frontier=date.fromisoformat(state['completed_through']) if state['completed_through'] else date.fromisoformat(state['scope_start'])-timedelta(days=1)
    for x in sorted(state['ranges'].values(),key=lambda r:r['start']):
        if x['complete'] and date.fromisoformat(x['start'])<=frontier+timedelta(days=1):frontier=max(frontier,date.fromisoformat(x['end']))
    if frontier>=date.fromisoformat(state['scope_start']):state['completed_through']=str(frontier)


def replay(state,responses,*,through,now,settings=None,last_good=None):
    c=settings or DEFAULTS;config(c);s=copy.deepcopy(state);budget=CallBudget(c['max_requests']);at=instant(now)
    if s.get('schema_version')!=VERSION:raise ValueError('FR_STATE_VERSION')
    results=[];changes={'NEW_DOCUMENT':0,'CONTENT_CHANGED':0,'DUPLICATE':0,'OLDER_RESPONSE':0}
    if s.get('retry_at') and at<instant(s['retry_at']):
        return {'state':s,'attempts':[],'changes':changes,'next_plan':plan(s,through,now,c),'retained_good':last_good,'actual_http_requests':0}
    for response in responses:
        if budget.used>=c['max_requests']:results.append({'result':'INCOMPLETE','reason':'REQUEST_BUDGET','checkpoint_advance':False});break
        budget.spend();req=response['request'];acquired=response['acquired_at']
        if instant(acquired)>at:raise ValueError('FR_ACQUISITION_AFTER_REPLAY')
        supplied=response.get('body');body=json.dumps(supplied,sort_keys=True,ensure_ascii=False).encode() if not isinstance(supplied,str) else supplied.encode()
        if s['data_kind']=='RETAINED_API' and not isinstance(supplied,str):raise ValueError('FR_ORIGINAL_RESPONSE_TEXT_REQUIRED')
        try:payload=json.loads(supplied) if isinstance(supplied,str) else supplied
        except ValueError:payload=None
        if response.get('data_kind')!=s['data_kind']:raise ValueError('FR_DATA_KIND_MISMATCH')
        outcome=collection_outcome(http_status=response['status'],parsed=isinstance(payload,dict),complete=False)
        if response['status']==429:
            seconds=retry_after_seconds(response.get('retry_after'),instant(acquired));seconds=c['cooldown_seconds'] if seconds is None else seconds
            try:s['retry_at']=(instant(acquired)+timedelta(seconds=seconds)).isoformat()
            except OverflowError:s['retry_at']=datetime.max.replace(tzinfo=timezone.utc).isoformat()
        if response['status']!=200 or not isinstance(payload,dict) or len(body)>c['max_body_bytes']:
            outcome.update(result='FAILED',reason='BODY_TOO_LARGE' if len(body)>c['max_body_bytes'] else 'HTTP_429' if response['status']==429 else 'HTTP_OR_PARSE_FAILURE')
            results.append(outcome);break
        try:
            if req.get('kind')=='TRACKED_DOCUMENT':
                expected='https://www.federalregister.gov/api/v1/documents/'+req['document_number']+'.json'
                rows=[normalize(payload)];complete=True;range_item=None
                if rows[0]['document_number']!=req['document_number']:raise ValueError('FR_TRACKED_DOCUMENT_MISMATCH')
            else:
                start,end=req['start'],req['end'];page=req['page'];expected=url(start,end,page,c['per_page'])
                if not state['scope_start']<=start<=end<=through or type(page)!=int or not 1<=page<=c['max_pages']:raise ValueError('FR_RANGE_INVALID')
                if date.fromisoformat(end)>instant(acquired).astimezone(timezone.utc).date():raise ValueError('FR_RESPONSE_PREDATES_INTERVAL')
                count,total=payload.get('count'),payload.get('total_pages')
                if type(count)!=int or type(total)!=int or count<0 or total<0 or total>c['max_pages'] or count>2000 or not isinstance(payload.get('results'),list):raise ValueError('FR_PAGE_LIMIT_OR_METADATA')
                required_pages=max(1,(count+c['per_page']-1)//c['per_page'])
                if max(1,total)!=required_pages:raise ValueError('FR_PAGE_COUNT_INCONSISTENT')
                rows=[normalize(r) for r in payload['results']]
                if any(not start<=r['published']['value']<=end for r in rows) or len(rows)!=min(c['per_page'],max(0,count-(page-1)*c['per_page'])):raise ValueError('FR_TRUNCATED_PAGE')
                rid=start+'/'+end;prior=s['ranges'].get(rid)
                # Page1 begins a new scan; duplicate page1 can be safely replayed.
                if page==1:range_item={'start':start,'end':end,'count':count,'total_pages':total,'pages':{},'next_page':1,'complete':False}
                else:
                    if prior and (prior['count']!=count or prior['total_pages']!=total):
                        s['ranges'][rid]=dict(prior,pages={},next_page=1,complete=False)
                        raise ValueError('FR_CHANGED_PAGINATION_RESTART')
                    if not prior or prior['complete'] or prior['next_page']!=page:raise ValueError('FR_INCOMPLETE_OR_CHANGED_PAGINATION')
                    range_item=copy.deepcopy(prior)
                range_item['pages'][str(page)]=[r['document_id'] for r in rows]
                ids=[v for values in range_item['pages'].values() for v in values]
                if len(set(ids))!=len(ids):
                    # Page drift/duplication cannot be repaired by requesting
                    # total_pages+1. Restart this interval from page 1.
                    range_item.update(pages={},next_page=1,complete=False)
                    s['ranges'][rid]=range_item
                    raise ValueError('FR_DUPLICATE_PAGE_DOCUMENTS_RESTART')
                complete=len(range_item['pages'])==required_pages and len(ids)==count and len(set(ids))==count
                range_item.update(complete=complete,next_page=page+1)
            if req.get('url')!=expected:raise ValueError('FR_REQUEST_URL_MISMATCH')
            if any(date.fromisoformat(row['published']['value'])>instant(acquired).astimezone(timezone.utc).date() for row in rows):raise ValueError('FR_DOCUMENT_AFTER_ACQUISITION')
            for row in rows:changes[_record(s,row,acquired,hashlib.sha256(body).hexdigest())]+=1
            if range_item:
                s['ranges'][req['start']+'/'+req['end']]=range_item
                if complete:s['split_ranges']=[x for x in s.get('split_ranges',[]) if (x['start'],x['end'])!=(req['start'],req['end'])]
                if complete and req.get('kind')=='RECONCILE':
                    nxt=date.fromisoformat(req['end'])+timedelta(days=1)
                    s['reconcile_from']=s['scope_start'] if str(nxt)>through else str(nxt)
                _advance(s)
            outcome=collection_outcome(http_status=200,parsed=True,complete=complete,new_items=sum(changes[k] for k in ('NEW_DOCUMENT','CONTENT_CHANGED')),
                                       incomplete_ranges=[] if complete else [req])
            if req.get('kind')=='TRACKED_DOCUMENT':s['tracked_after']='FR:'+req['document_number']
            if complete and (s['last_success_at'] is None or instant(acquired)>instant(s['last_success_at'])):s['last_success_at']=acquired
        except (ValueError,TypeError,KeyError) as error:
            if str(error)=='FR_PAGE_LIMIT_OR_METADATA' and req.get('start') and isinstance(payload,dict) and (isinstance(payload.get('count'),int) and payload['count']>2000 or isinstance(payload.get('total_pages'),int) and payload['total_pages']>c['max_pages']):
                a,b=date.fromisoformat(req['start']),date.fromisoformat(req['end']);mid=a+(b-a)//2
                splits=[{'start':str(a),'end':str(mid)},{'start':str(mid+timedelta(days=1)),'end':str(b)}] if a<b else [{'start':str(a),'end':str(b),'blocked':True,'reason':'ONE_DAY_SCOPE_REFINEMENT_REQUIRED'}]
                s['ranges'].pop(req['start']+'/'+req['end'],None)
                s['split_ranges']=[x for x in s.get('split_ranges',[]) if (x['start'],x['end'])!=(req['start'],req['end'])]+splits
            outcome={'result':'INCOMPLETE','reason':str(error) if isinstance(error,ValueError) and str(error).startswith('FR_') else 'FR_PARSE_FAILURE','checkpoint_advance':False}
        results.append(outcome)
    s['last_attempt_at']=now
    failure=next((r for r in results if r['result']=='FAILED' or r['result']=='INCOMPLETE' and r.get('reason')!='PAGE_OR_REQUEST_LIMIT'),None)
    if failure is None and (any(not r['complete'] for r in s['ranges'].values()) or s.get('split_ranges')):failure={'result':'INCOMPLETE','reason':'PAGES_PENDING'}
    s['result']=failure['result'] if failure else 'UPDATED' if changes['NEW_DOCUMENT'] or changes['CONTENT_CHANGED'] else 'NO_NEW_ITEMS' if results else 'NOT_RUN'
    s['attempts'].append({'at':now,'result':s['result'],'response_count':budget.used,'changes':changes})
    retained=retain_good(last_good,{'result':s['result'],'at':now,'incomplete_ranges':[r for r in s['ranges'].values() if not r['complete']]}) if last_good and failure else copy.deepcopy(last_good)
    return {'state':s,'attempts':results,'changes':changes,'next_plan':plan(s,through,now,c),'retained_good':retained,
            'actual_http_requests':0,'compatibility':'SYNTHETIC_ONLY' if s['data_kind']=='SYNTHETIC' else 'RETAINED_RESPONSE_REPLAY_NOT_LIVE_API'}
