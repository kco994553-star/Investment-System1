import copy,hashlib,json
from pathlib import Path
import pytest
from investment_system.research.policy_impact import build,Invalid

ROOT=Path(__file__).parents[2]
def base():
 j=json.loads((ROOT/'docs/research/policy_impact/synthetic-job.json').read_text())
 return j

def test_watch_availability_unknown_does_not_grant_public_permission():
 j=base();w=j['bundle']['hypotheses'][0]['watch_items'][0];w['availability']='UNKNOWN'
 private=build(j['bundle'],j['company_ids'],j['as_of'],public_macro_ids=j['public_macro_ids'])
 public=build(j['bundle'],j['company_ids'],j['as_of'],public=True,public_macro_ids=j['public_macro_ids'])
 assert private['bundle']['hypotheses'][0]['watch_items'][0]['availability']=='UNKNOWN'
 assert not public['bundle']['hypotheses'][0]['watch_items']
 w['availability']='ALLOW_ALL'
 with pytest.raises(Invalid,match='WATCH_AVAILABILITY'):build(j['bundle'],j['company_ids'],j['as_of'],public_macro_ids=j['public_macro_ids'])

def test_pure_limits_remain_the_same_news_objects():
 from investment_system import request_limits
 from investment_system.providers import news_feeds
 assert news_feeds.retry_after_seconds is request_limits.retry_after_seconds
 assert news_feeds.MAX_BODY_BYTES==request_limits.MAX_BODY_BYTES

def nav_fixture():
 from investment_system.research.policy_impact.build import digest
 j=base();v=build(j['bundle'],j['company_ids'],j['as_of'],public=True,public_macro_ids=j['public_macro_ids']);p=v['bundle']['policies'][0];s=v['bundle']['sources'][0]
 item={'group_id':'existing-synthetic-news-group','company_id':'synthetic-company','title':'Synthetic article','link':'https://example.org/synthetic-news','published_at':None,'source_seen_at':'2026-11-06T00:00:00Z','acquired_at':'2026-11-06T01:00:00Z','publication_permission':'ALLOWED'}
 n={'schema_version':'policy-impact-navigation-input/1','data_kind':'SYNTHETIC','base_view_hash':digest(v),'titles':[], 'news_items':[item], 'links':[{'news_ref':{k:item[k] for k in ('group_id','company_id','link')},'news_revision_hash':digest(item),'policy_id':p['policy_id'],'policy_revision_id':p['revision_id'],'relation':'DISCOVERY_REFERENCE_ONLY','reviewed_at':'2026-11-06T03:00:00Z','recorded_at':'2026-11-06T03:00:00Z','reviewer':'reviewer','author':'author','reason':'Synthetic article-policy association checked; no applicability claim','publication_permission':'ALLOWED'}]}
 n['links'][0].update(reviewed_at='2026-11-07T22:00:00Z',recorded_at='2026-11-07T22:00:00Z')
 return v,n

def test_news_navigation_does_not_promote_news_to_policy_evidence():
 from investment_system.research.policy_impact.navigation import project
 v,n=nav_fixture();old=copy.deepcopy(v);out=project(v,n,'2026-11-07T23:00:00Z',public=True)
 assert len(out['news_links'])==1 and out['news_links'][0]['evidence_effect']=='NONE' and v==old
 n['links'][0]['publication_permission']='UNKNOWN'
 assert project(v,n,'2026-11-07T23:00:00Z',public=True)['news_links']==[]
 n['links'][0]['publication_permission']='BOGUS'
 with pytest.raises(Invalid,match='PERMISSION'):project(v,n,'2026-11-07T23:00:00Z',public=True)

@pytest.mark.parametrize('change',['future','changed_article','self_review','wrong_revision','preacquisition_review'])
def test_unreviewed_or_changed_news_association_is_not_public(change):
 from investment_system.research.policy_impact.navigation import project
 v,n=nav_fixture()
 if change=='future':n['links'][0]['recorded_at']='2099-01-01T00:00:00Z'
 if change=='changed_article':n['news_items'][0]['title']='Changed article'
 if change=='self_review':n['links'][0]['reviewer']='author'
 if change=='wrong_revision':n['links'][0]['policy_revision_id']='missing'
 if change=='preacquisition_review':n['links'][0]['reviewed_at']='2026-11-05T00:00:00Z'
 out=project(v,n,'2026-11-07T23:00:00Z',public=True)
 assert not out['news_links'] and out['reasons']

def test_official_title_receipt_requires_original_bytes_and_locator():
 from investment_system.research.policy_impact.navigation import title_receipt
 body=b'<html><h1>Official synthetic title</h1></html>';sha=hashlib.sha256(body).hexdigest()
 r=title_receipt(body,sha,0)
 assert r['official_title']=='Official synthetic title' and r['locator']=='h1[0]'
 with pytest.raises(Invalid,match='SOURCE_HASH'):title_receipt(body,'0'*64,0)

def test_public_reference_needs_separate_explicit_watch_permission():
 j=base();w=j['bundle']['hypotheses'][0]['watch_items'][0]
 v=build(j['bundle'],j['company_ids'],j['as_of'],public=True)
 assert v['schema_version']=='policy-impact-view/2' and not v['bundle']['hypotheses'][0]['watch_items']
 access={w['kind']+':'+w['reference_id']:'ALLOWED'}
 granted=build(j['bundle'],j['company_ids'],j['as_of'],public=True,watch_publication_permissions=access)
 assert len(granted['bundle']['hypotheses'][0]['watch_items'])==1
 with pytest.raises(Invalid,match='PUBLICATION_PERMISSION'):
  build(j['bundle'],j['company_ids'],j['as_of'],public=True,watch_publication_permissions={next(iter(access)):'MAYBE'})

def test_title_text_is_verified_at_projection_and_pit_review_uses_recording_time():
 from investment_system.research.policy_impact.navigation import project,title_receipt
 from investment_system.research.policy_impact.build import digest
 v,n=nav_fixture();policy=v['bundle']['policies'][0];ref=policy['evidence_refs'][0]
 source=next(s for s in v['bundle']['sources'] if s['source_id']==ref['source_id'])
 body=b'<h1>Synthetic official title</h1>';sha=hashlib.sha256(body).hexdigest();source['content_sha256']=sha;n['base_view_hash']=digest(v)
 t=dict(policy_id=policy['policy_id'],policy_revision_id=policy['revision_id'],source_id=source['source_id'],source_revision_id=source['source_revision_id'],**title_receipt(body,sha,0),explanation_title_ko='합성 설명 제목',explanation_origin='RESEARCH_SUMMARY',extracted_at='2026-11-07T22:00:00Z',publication_permission='ALLOWED')
 n['titles']=[t]
 assert len(project(v,n,'2026-11-07T23:00:00Z',public=True,title_sources={sha:body})['titles'])==1
 t['official_title']='fabricated'
 with pytest.raises(Invalid,match='TITLE_TEXT'):project(v,n,'2026-11-07T23:00:00Z',public=True,title_sources={sha:body})
 n['titles']=[]
 for review in v['bundle']['review_records']:
  if review['group']=='policies' and review['id']==policy['policy_id']:review['recorded_at']='2026-11-07T22:30:00Z'
 n['base_view_hash']=digest(v)
 out=project(v,n,'2026-11-07T23:00:00Z',public=True)
 assert not out['news_links'] and 'POLICY_REVIEW_NOT_AVAILABLE_AT_LINK_REVIEW' in out['reasons']

def test_private_view_cannot_supply_public_navigation_and_unknown_check_time_stays_null():
 from investment_system.research.policy_impact.navigation import project
 from investment_system.research.policy_impact.build import digest,reproject_view
 v,n=nav_fixture();v['schema_version']='policy-impact-view/1';n['base_view_hash']=digest(v)
 with pytest.raises(Invalid,match='PUBLIC_VIEW_REQUIRED'):project(v,n,'2026-11-07T23:00:00Z',public=True)
 v['schema_version']='policy-impact-view/2';v['bundle']['policy_as_of']=None;n['base_view_hash']=digest(v)
 assert len(project(v,n,'2026-11-07T23:00:00Z',public=True)['news_links'])==1
 assert reproject_view(v,'2026-11-07T22:00:00Z',public=True)['bundle']['policy_as_of'] is None
 v['bundle']['sources'][0]['verification_status']='SOURCE_UNVERIFIED';n['base_view_hash']=digest(v)
 # Even a wrongly labelled view cannot promote an unverified source through replay.
 assert not project(v,n,'2026-11-07T23:00:00Z',public=True)['news_links']
