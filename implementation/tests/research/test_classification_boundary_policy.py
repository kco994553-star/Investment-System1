"""Owner-approved research boundaries; synthetic evidence, no operating rules changed."""
from copy import deepcopy
import pytest
from test_classification_held_review import fixture
from investment_system.research.sector_qgv_classification import extend_held_classification
from investment_system.research.common_classification.catalog import dictionary
from investment_system.research.common_classification.records import from_sector_snapshot,resolve,upgrade_policy_store,append_review
from investment_system.research.common_classification.qgv import project_qgv

V='held-sec-book-correspondence/0.5.0'
DICT='common-industry-dictionary/2'
AT='2026-11-08T09:00:00Z'

@pytest.mark.parametrize('sic,description,profile,sector,accounting',[
 ('6798','Real Estate Investment Trusts','GENERAL','FINANCIALS',None),
 ('6324','Hospital & Medical Service Plans','FINANCIAL','HEALTH_CARE',None),
 ('4833','Television Broadcasting Stations','GENERAL','CONSUMER_DISCRETIONARY','GENERAL'),
 ('4832','Radio Broadcasting Stations','GENERAL','CONSUMER_DISCRETIONARY','GENERAL'),
 ('2711','Newspapers: Publishing or  Publishing & Printing','GENERAL','CONSUMER_DISCRETIONARY','GENERAL'),
 ('5065','Wholesale-Electronic Parts & Equipment, NEC','GENERAL','INFORMATION_TECHNOLOGY','GENERAL'),
])
def test_explicit_activity_policy_does_not_invent_accounting(sic,description,profile,sector,accounting):
 s,e=fixture(sic,description,profile);before=deepcopy(s)
 out,a=extend_held_classification(s,e,rule_version=V)
 assert out['rows'][0]['sector_id']==sector and out['rows'][0]['accounting_template']==accounting
 assert out['rows'][0]['gate']==s['rows'][0]['gate'] and out['rows'][0]['observations']==s['rows'][0]['observations']
 assert s==before
 old,_=extend_held_classification(s,e,rule_version='held-sec-book-correspondence/0.4.0')
 assert old['rows'][0]['sector_id'] is None

@pytest.mark.parametrize('sic',['6512','6531','6282','4841','4899','5912','7374'])
def test_policy_does_not_blanket_assign_real_estate_cable_platform_or_mixed_health(sic):
 s,e=fixture(sic,'Unreviewed primary business','GENERAL')
 out,_=extend_held_classification(s,e,rule_version=V)
 assert out['rows'][0]['sector_id'] is None


def test_existing_company_exception_not_overridden_by_generic_media_or_electronics_rule():
 for sic,desc in [('2711','Newspapers: Publishing or  Publishing & Printing'),('5065','Wholesale-Electronic Parts & Equipment, NEC')]:
  s,e=fixture(sic,desc,'GENERAL');s['rows'][0]['reasons']=['COMPANY_MIX_PRIMARY_ACTIVITY_NOT_CONFIRMED']
  out,_=extend_held_classification(s,e,rule_version=V)
  assert out['rows'][0]['sector_id'] is None


def test_reit_accounting_evidence_survives_sector_policy_and_versioned_history():
 s,e=fixture('6798','Real Estate Investment Trusts','GENERAL');r=s['rows'][0]
 r['accounting_template']='EQUITY_REIT';r['component_mappings']={'accounting':{'classification_rule_version':'held-review/old','evidence_refs':['retained-reit-accounting-proof']}}
 old=from_sector_snapshot(s,e,source_sha256='c'*64,recorded_at='2026-11-07T00:00:00Z',data_kind='SYNTHETIC')
 out,_=extend_held_classification(s,e,rule_version=V)
 assert out['rows'][0]['accounting_template']=='EQUITY_REIT'
 imported=from_sector_snapshot(out,e,source_sha256='d'*64,recorded_at=AT,data_kind='SYNTHETIC',dictionary_version=DICT)
 upgraded=upgrade_policy_store(old,recorded_at=AT)
 combined=append_review(upgraded,imported,company_ids=s['members'])
 view=resolve(combined,valuation_date=s['valuation_date'],knowledge_as_of=AT)
 assert view['dictionary_version']==DICT and view['mapping_version']=='common-classification-map/2'
 assert view['boundary_policy']==combined['boundary_policy']
 assert view['rows'][0]['accounting']['evidence_refs']==['retained-reit-accounting-proof']
 assert view['rows'][0]['sector']['id']=='FINANCIALS' and len(combined['records'])==2
 assert resolve(old,valuation_date=s['valuation_date'],knowledge_as_of=AT)['rows'][0]['sector']['id'] is None
 assert resolve(combined,valuation_date='2026-11-03',knowledge_as_of=AT)['coverage']['sector_confirmed']==0
 with pytest.raises(ValueError,match='POLICY_NOT_AVAILABLE'):
  resolve(combined,valuation_date=s['valuation_date'],knowledge_as_of='2026-11-07T23:00:00Z')
 assert dictionary()['exceptions']['REIT']=='UPPER_SECTOR_AND_ACCOUNTING_NOT_RESOLVED'
 assert dictionary(DICT)['policy']['book_direct_claim'] is False
 projected=project_qgv(s,view)
 assert projected['rows'][0]['component_mappings']['accounting']['evidence_refs']==['retained-reit-accounting-proof']

@pytest.mark.parametrize('change',['issuer','date','description','hash'])
def test_new_policy_retains_source_boundary(change):
 s,e=fixture('6798','Real Estate Investment Trusts','GENERAL');x=e['ROW:A']
 if change=='issuer':x['issuer_id']='OTHER'
 if change=='date':x['acquired_at']='2026-11-05T00:00:00Z'
 if change=='description':x['sic_description']='Real estate developer'
 if change=='hash':x['source_sha256']='bad'
 out,_=extend_held_classification(s,e,rule_version=V)
 assert out['rows'][0]['sector_id'] is None


def test_policy_view_remains_usable_by_common_technical_and_macro_producers():
 from investment_system.research.common_classification.technical_macro import technical_groups,macro_projection
 s,e=fixture('6798','Real Estate Investment Trusts','GENERAL')
 out,_=extend_held_classification(s,e,rule_version=V)
 store=from_sector_snapshot(out,e,source_sha256='e'*64,recorded_at=AT,data_kind='SYNTHETIC',dictionary_version=DICT)
 view=resolve(store,valuation_date=s['valuation_date'],knowledge_as_of=AT)
 technical=technical_groups(view,[],[],price_basis='RAW')
 assert technical['rows'][0]['reasons']
 macro_projection(view,[])
 view['mapping_version']='common-classification-map/1'
 with pytest.raises(ValueError,match='VERSION_MISMATCH'):technical_groups(view,[],[],price_basis='RAW')


def test_public_boundary_fixture_expected_components_and_unchanged_gate():
 import json
 from pathlib import Path
 pack=json.loads((Path(__file__).parents[1]/'fixtures/common_classification/boundary-policy-v2.json').read_text())
 for case in pack['cases']:
  out,_=extend_held_classification(case['snapshot'],case['evidence'],rule_version=pack['rule_version'])
  row=out['rows'][0]
  for key in ('sector_id','accounting_template'):assert row[key]==case['expected'][key],case['case_id']
  assert row['observations']==case['snapshot']['rows'][0]['observations']
  assert row['gate']==case['snapshot']['rows'][0]['gate']
