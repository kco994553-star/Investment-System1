"""Additive held-source review; all identities/documents here are synthetic."""
from copy import deepcopy
import hashlib
import pytest

from investment_system.research.sector_qgv_classification import extend_held_classification
from investment_system.research.common_classification.records import from_sector_snapshot, resolve, append_review

VERSION = 'held-sec-book-correspondence/0.3.0'
AT = '2026-11-04T02:00:00Z'


def fixture(sic='6200', description='Security & Commodity Brokers, Dealers, Exchanges & Services', profile='FINANCIAL'):
    e = {'issuer_id':'0000000001','sic':sic,'sic_description':description,
         'source_sha256':'a'*64,'archive_sha256':'b'*64,'member':'synthetic/submissions.json',
         'source_url':'https://example.invalid/source','source_kind':'SEC_SUBMISSIONS',
         'acquired_at':'2026-11-03T00:00:00Z'}
    s = {'as_of':AT,'valuation_date':'2026-11-04','snapshot_id':'synthetic',
         'mapping_version':'book-sector-map/1','classification_rule_version':'old/1',
         'universe_id':'SYNTHETIC','universe_version':'1','members':['ROW:A'],
         'rows':[{'company_id':'ROW:A','issuer_id':e['issuer_id'],'source_sic':sic,'source_profile':profile,
                  'sector_id':None,'accounting_template':None,'mapping':None,
                  'official_classification':{'system':'SEC_SIC','code':sic,'source_sha256':'a'*64,
                     'source_url':e['source_url'],'observed_at':e['acquired_at']},
                  'reasons':['EXACT_SIC_CORRESPONDENCE_NOT_REVIEWED'],
                  'observations':{'kept':{'value':None}},'gate':{'kept':True}}]}
    return s, {'ROW:A':e}


def test_sector_survives_unknown_accounting_and_old_version_replays():
    s,e=fixture(); original=deepcopy(s)
    old,_=extend_held_classification(s,e)
    after,a=extend_held_classification(s,e,rule_version=VERSION)
    assert old['rows'][0]['sector_id'] is None and s==original
    r=after['rows'][0]
    assert r['sector_id']=='FINANCIALS' and r['accounting_template'] is None and r['mapping'] is None
    assert r['observations']==s['rows'][0]['observations'] and r['gate']==s['rows'][0]['gate']
    store=from_sector_snapshot(after,e,source_sha256='c'*64,recorded_at='2026-11-08T00:00:00Z',data_kind='SYNTHETIC')
    v=resolve(store,valuation_date='2026-11-04',knowledge_as_of='2026-11-08T01:00:00Z')
    assert v['coverage']['sector_confirmed']==1 and v['coverage']['accounting_confirmed']==0
    assert a['new_sector']==1 and a['new_accounting']==0


@pytest.mark.parametrize('change', ['description','future','issuer','hash'])
def test_partial_mapping_never_bypasses_source_validation(change):
    s,e=fixture(); x=e['ROW:A']
    if change=='description':x['sic_description']='Unreviewed activity'
    if change=='future':x['acquired_at']='2026-11-05T00:00:00Z'
    if change=='issuer':x['issuer_id']='0000000002'
    if change=='hash':x['source_sha256']='bad'
    after,_=extend_held_classification(s,e,rule_version=VERSION)
    assert after['rows'][0]['sector_id'] is None


def review(tmp_path, sector='INFORMATION_TECHNOLOGY', accounting='GENERAL', industry='software'):
    s,e=fixture('7374','Services-Computer Processing & Data Preparation','GENERAL')
    text='Synthetic enterprise software business; no bank or insurer business.'
    body=('<xbrl xmlns:x="urn:synthetic"><context id="C"><entity><identifier>0000000001</identifier></entity>'
          '<period><startDate>2026-01-01</startDate><endDate>2026-09-30</endDate></period></context>'
          '<x:DescriptionOfBusinessTextBlock contextRef="C">'+text+'</x:DescriptionOfBusinessTextBlock></xbrl>').encode()
    p=tmp_path/'synthetic.xml';p.write_bytes(body)
    doc={'path':str(p),'sha256':hashlib.sha256(body).hexdigest(),'archive_sha256':'b'*64,
         'member':'synthetic/filing.xml','source_url':'https://example.invalid/filing',
         'acquired_at':e['ROW:A']['acquired_at']}
    citation={'document':0,'tag':'{urn:synthetic}DescriptionOfBusinessTextBlock','context_id':'C',
              'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
              'period_start':'2026-01-01','period_end':'2026-09-30'}
    claims={k:{'id':v,'rationale':'Synthetic verified business review','citations':[0]}
            for k,v in [('sector',sector),('accounting',accounting),('industry',industry)] if v}
    r={'company_id':'ROW:A','issuer_id':'0000000001','valuation_date':'2026-11-04',
       'submissions_sha256':'a'*64,'documents':[doc],'citations':[citation],
       'claims':claims,'sector_unresolved_reason':'REIT_BOOK_SECTOR_POLICY_UNRESOLVED'}
    return s,e,r


def test_business_review_and_reit_accounting_are_independent(tmp_path):
    s,e,r=review(tmp_path,sector=None,accounting='EQUITY_REIT',industry=None)
    after,a=extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])
    assert after['rows'][0]['sector_id'] is None
    assert after['rows'][0]['accounting_template']=='EQUITY_REIT'
    store=from_sector_snapshot(after,e,source_sha256='d'*64,recorded_at='2026-11-08T00:00:00Z',data_kind='SYNTHETIC')
    v=resolve(store,valuation_date='2026-11-04',knowledge_as_of='2026-11-08T01:00:00Z')
    assert v['coverage']['sector_confirmed']==0 and v['coverage']['accounting_confirmed']==1


@pytest.mark.parametrize('change', ['body','context_issuer','future_period','future_acquisition','citation','wrong_parent','missing_citation','wrong_day'])
def test_review_citations_fail_closed(tmp_path, change):
    s,e,r=review(tmp_path)
    if change=='body':r['documents'][0]['sha256']='0'*64
    if change=='context_issuer':r['issuer_id']='0000000002'
    if change=='future_period':r['citations'][0]['period_end']='2027-01-01'
    if change=='future_acquisition':r['documents'][0]['acquired_at']='2026-11-05T00:00:00Z'
    if change=='citation':r['citations'][0]['text_sha256']='0'*64
    if change=='wrong_parent':r['claims']['industry']['id']='medical_devices'
    if change=='missing_citation':r['claims']['sector']['citations']=[]
    if change=='wrong_day':r['valuation_date']='2026-11-02'
    with pytest.raises(ValueError):extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])


def test_append_keeps_old_records_sources_cutoff_and_input_members(tmp_path):
    s,e,r=review(tmp_path); before=from_sector_snapshot(s,e,source_sha256='c'*64,recorded_at='2026-11-07T00:00:00Z',data_kind='SYNTHETIC')
    original=deepcopy(before)
    after,a=extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])
    new=from_sector_snapshot(after,e,source_sha256='d'*64,recorded_at='2026-11-08T00:00:00Z',data_kind='SYNTHETIC')
    merged=append_review(before,new,company_ids=[x['company_id'] for x in a['changes']])
    assert before==original and merged['members']==before['members']
    assert merged['records'][:len(before['records'])]==before['records']
    assert merged['sources'][:len(before['sources'])]==before['sources']
    args=dict(valuation_date='2026-11-04',knowledge_as_of='2026-11-07T01:00:00Z')
    assert resolve(merged,**args)['classification_hash']==resolve(before,**args)['classification_hash']
    v=resolve(merged,valuation_date='2026-11-04',knowledge_as_of='2026-11-08T01:00:00Z')
    assert v['coverage']['industry_confirmed']==1 and v['coverage']['sector_confirmed']==1
    assert merged['records'][-1]['supersedes']==before['records'][0]['record_id']


def test_relocation_does_not_change_mapping_identity_and_unknown_is_not_general(tmp_path):
    s,e,r=review(tmp_path)
    first,_=extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])
    p=tmp_path/'relocated.xml';p.write_bytes((tmp_path/'synthetic.xml').read_bytes())
    r['documents'][0]['path']=str(p)
    second,_=extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])
    assert first==second
    s['rows'][0]['source_profile']=None
    with pytest.raises(ValueError,match='ACCOUNTING_PROFILE_CONFLICT'):
        extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])


def test_old_confirmed_rows_and_duplicate_reviews_are_not_silently_overwritten(tmp_path):
    s,e,r=review(tmp_path)
    with pytest.raises(ValueError,match='MEMBERS_INVALID'):
        extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r,r])
    s['rows'][0]['mapping']={'existing':True}
    with pytest.raises(ValueError,match='REPLACEMENT_NOT_SUPPORTED'):
        extend_held_classification(s,e,rule_version=VERSION,business_reviews=[r])
