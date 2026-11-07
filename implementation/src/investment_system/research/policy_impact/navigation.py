"""Optional title/news navigation sidecar; never policy evidence or publication approval."""
import hashlib
import re
from html.parser import HTMLParser
from .build import digest,reproject_view
from .contract import need,shape,time,url

INPUT='policy-impact-navigation-input/1'
OUTPUT='policy-impact-navigation/1'
PERMISSIONS={'ALLOWED','PRIVATE_ONLY','UNKNOWN'}
NEWS_KEYS='group_id company_id title link published_at source_seen_at acquired_at publication_permission'.split()
LINK_KEYS='news_ref news_revision_hash policy_id policy_revision_id relation reviewed_at recorded_at reviewer author reason publication_permission'.split()
TITLE_KEYS='policy_id policy_revision_id source_id source_revision_id official_title explanation_title_ko explanation_origin locator source_sha256 extracted_at publication_permission'.split()


def title_receipt(body,expected_sha256,h1_index):
    need(isinstance(body,bytes) and hashlib.sha256(body).hexdigest()==expected_sha256,'SOURCE_HASH','title')
    class Titles(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.active=False;self.parts=[];self.rows=[]
        def handle_starttag(self,tag,attrs):
            if tag=='h1':self.active=True;self.parts=[]
        def handle_data(self,text):
            if self.active:self.parts.append(text)
        def handle_endtag(self,tag):
            if tag=='h1' and self.active:self.rows.append(' '.join(''.join(self.parts).split()));self.active=False
    p=Titles();p.feed(body.decode('utf-8'))
    need(type(h1_index)==int and 0<=h1_index<len(p.rows) and bool(p.rows[h1_index]),'TITLE_LOCATOR','title')
    return {'official_title':p.rows[h1_index],'locator':f'h1[{h1_index}]','source_sha256':expected_sha256}


def project(view,data,as_of,*,public=False,title_sources=None):
    shape(data,['schema_version','data_kind','base_view_hash','titles','news_items','links'],'navigation')
    need(data['schema_version']==INPUT and view.get('schema_version') in ('policy-impact-view/1','policy-impact-view/2'),'VERSION','navigation')
    if public:need(view['schema_version']=='policy-impact-view/2','PUBLIC_VIEW_REQUIRED','navigation')
    need(data['base_view_hash']==digest(view),'BASE_VIEW_HASH','navigation')
    need(data['data_kind']==view['bundle']['data_kind'],'MIXED_KIND','navigation')
    at=time(as_of,'navigation.as_of');need(time(view['as_of'],'view.as_of')<=at,'FUTURE_VIEW','navigation')
    sources={(s['source_id'],s['source_revision_id']):s for s in view['bundle']['sources']}
    policies={(p['policy_id'],p['revision_id']):p for p in view['bundle']['policies']}
    result={'schema_version':OUTPUT,'data_kind':data['data_kind'],'base_view_hash':digest(view),'as_of':as_of,
            'titles':[],'news_links':[],'reasons':[],'policy_evidence_effect':'NONE','automatic_publication':False}
    def permission(row):need(row['publication_permission'] in PERMISSIONS,'PERMISSION','navigation')
    def text(value):need(isinstance(value,str) and bool(value) and len(value)<=20000,'TEXT','navigation')
    for t in data['titles']:
        shape(t,TITLE_KEYS,'navigation.title');permission(t)
        for key in TITLE_KEYS:
            if key!='publication_permission':text(t[key])
        need(t['explanation_origin']=='RESEARCH_SUMMARY','EXPLANATION_ORIGIN','navigation.title')
        p=policies.get((t['policy_id'],t['policy_revision_id']));s=sources.get((t['source_id'],t['source_revision_id']))
        need(p is not None and s is not None and s['kind'] in ('OFFICIAL_RULE','OFFICIAL_RELEASE') and s['verification_status']=='VERIFIED','TITLE_SOURCE','navigation.title')
        need(t['source_sha256']==s['content_sha256'] and any((r['source_id'],r['source_revision_id'])==(t['source_id'],t['source_revision_id']) for r in p['evidence_refs']),'TITLE_SOURCE','navigation.title')
        body=(title_sources or {}).get(t['source_sha256']);m=re.fullmatch(r'h1\[(\d+)\]',t['locator'])
        need(body is not None and m is not None,'TITLE_ORIGINAL_REQUIRED','navigation.title')
        receipt=title_receipt(body,t['source_sha256'],int(m[1]))
        need(receipt['official_title']==t['official_title'],'TITLE_TEXT_MISMATCH','navigation.title')
        if max(time(t['extracted_at'],'title'),time(s['revision_acquired_at'],'source'))>at:
            result['reasons'].append('TITLE_NOT_AVAILABLE');continue
        if public and t['publication_permission']!='ALLOWED':
            result['reasons'].append('TITLE_PUBLICATION_NOT_ALLOWED');continue
        result['titles'].append(dict(t))
    articles={}
    for item in data['news_items']:
        shape(item,NEWS_KEYS,'navigation.news');permission(item)
        for k in ('group_id','company_id','title','link'):text(item[k])
        url(item['link'],'navigation.news.link')
        for k in ('published_at','source_seen_at','acquired_at'):
            if item[k] is not None:time(item[k],'news.'+k)
        need(item['acquired_at'] is not None,'TIME','news.acquired_at')
        key=tuple(item[k] for k in ('group_id','company_id','link'))
        need(key not in articles,'DUPLICATE_NEWS_REF','navigation');articles[key]=item
    seen=set()
    for link in data['links']:
        shape(link,LINK_KEYS,'navigation.link');permission(link);shape(link['news_ref'],['group_id','company_id','link'],'news_ref')
        for k in LINK_KEYS:
            if k!='news_ref':text(link[k])
        need(link['relation']=='DISCOVERY_REFERENCE_ONLY','NOT_POLICY_EVIDENCE','navigation.link')
        key=tuple(link['news_ref'][k] for k in ('group_id','company_id','link'));pkey=(link['policy_id'],link['policy_revision_id']);unique=(key,pkey)
        need(unique not in seen,'DUPLICATE_NEWS_LINK','navigation');seen.add(unique)
        item=articles.get(key);policy=policies.get(pkey);reasons=[]
        if item is None:reasons.append('NEWS_REFERENCE_MISSING')
        elif digest(item)!=link['news_revision_hash']:reasons.append('NEWS_CHANGED_REVIEW_REQUIRED')
        if policy is None:reasons.append('POLICY_REVISION_MISSING')
        elif policy['review_status']!='REVIEWED':reasons.append('POLICY_NOT_REVIEWED')
        if view['current_policy_revisions'].get(link['policy_id'])!=link['policy_revision_id']:reasons.append('POLICY_VERSION_REVIEW_REQUIRED')
        if link['reviewer']==link['author']:reasons.append('INDEPENDENT_LINK_REVIEW_REQUIRED')
        stamps=[time(link[k],k) for k in ('reviewed_at','recorded_at')]
        reviewed=time(link['reviewed_at'],'reviewed_at')
        if time(link['recorded_at'],'recorded_at')<reviewed or item and time(item['acquired_at'],'acquired_at')>reviewed:
            reasons.append('REVIEW_TIME_ORDER')
        if policy:
            then=reproject_view(view,link['reviewed_at'],public=public)
            if not any((p['policy_id'],p['revision_id'])==pkey and p['review_status']=='REVIEWED' for p in then['bundle']['policies']):
                reasons.append('POLICY_REVIEW_NOT_AVAILABLE_AT_LINK_REVIEW')
        if item:stamps+=[time(item[k],k) for k in ('published_at','source_seen_at','acquired_at') if item[k] is not None]
        if max(stamps)>at:reasons.append('LINK_NOT_AVAILABLE')
        if public and (link['publication_permission']!='ALLOWED' or not item or item['publication_permission']!='ALLOWED'):reasons.append('NEWS_PUBLICATION_NOT_ALLOWED')
        if reasons:result['reasons']+=reasons;continue
        result['news_links'].append({'news_ref':dict(link['news_ref']),'news_revision_hash':link['news_revision_hash'],
            'policy_id':link['policy_id'],'policy_revision_id':link['policy_revision_id'],'title':item['title'],
            'published_at':item['published_at'],'source_seen_at':item['source_seen_at'],'acquired_at':item['acquired_at'],
            'reviewed_at':link['reviewed_at'],'recorded_at':link['recorded_at'],'relation':link['relation'],
            'evidence_effect':'NONE','policy_application':'NOT_ASSESSED','reason':link['reason']})
    result['reasons']=sorted(set(result['reasons']));return result
