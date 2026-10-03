"""Independent current-policy observation, not an admission implementation.

Only existing validators are called. The expected table is for the active Primary
Web worker's eventual handoff; this writes no repository/product/source files.
"""
from copy import deepcopy
import json
from pathlib import Path

from investment_system.product.web_mvp import validate_bundle
from investment_system.producers.contract import make_snapshot, validate_snapshot, PUBLISHED_STATES, RESEARCH_STATUSES
from investment_system.producers.errors import ResearchStatusError

ROOT=Path(__file__).resolve().parent
base=json.loads((ROOT/'test-vector.schema1.json').read_text())
assert set(PUBLISHED_STATES)=={'LIVE','FROZEN_SNAPSHOT'}
assert RESEARCH_STATUSES=={'IDEA','RESEARCH','PROVISIONAL','PROVISIONAL_INITIAL_PRIOR','PROVISIONAL_RESEARCH'}
rows=[]
for state in PUBLISHED_STATES:
 for status in sorted(RESEARCH_STATUSES):
  m={'id':'G3_TEST_VECTOR_ONLY','version':'TEST_ONLY','status':status}
  snap=make_snapshot(producer_id='G3_TEST_VECTOR_ONLY',producer_version='TEST_ONLY',section='qgv',
   data_state=state,as_of=base['qgv']['as_of'],generated_at='2026-10-03T00:01:00Z',
   expires_at=base['qgv']['expires_at'] if state=='LIVE' else None,
   methodology=m,synthetic=False,
   provenance={'source':'G3 test vector only','inputs':[{'artifact_id':'G3_TEST_VECTOR_ONLY','sha256':'0'*64}]},
   validation={'status':'PASS','checks':['TEST_VECTOR_ONLY']},data=deepcopy(base['qgv']['data']),scope_kind='ENTITY_MAP')
  try:validate_snapshot(snap)
  except ResearchStatusError:producer='REJECTED_ResearchStatusError'
  else:raise AssertionError('existing approved rule must reject')
  for location in ('section.methodology','section.producer.methodology'):
   b=deepcopy(base);b['qgv']['state']=state
   if location=='section.methodology':b['qgv']['methodology']=m
   else:
    del b['qgv']['methodology'];b['qgv']['producer']={'methodology':m}
   before=deepcopy(b)
   validate_bundle(b)
   assert b==before
   rows.append({'state':state,'methodology_status':status,'metadata_location':location,
                'actual_existing_producer':producer,'actual_Frozen_web':'ACCEPTED',
                'expected_NEW_integration_admission':'REJECT_WITHOUT_REWRITE_OR_ARTIFACTS',
                'raw_input_unchanged':True})
receipt={'source_head':'675d0d298fbaab5b8473ed048a561ef84e2f3e78','scope':'READ_ONLY_TEST_VECTOR_ORACLE',
 'observed_existing_producer_negative_combinations':10,'observed_Frozen_schema1_bypass_shapes':20,
 'cases':rows,'real_data_provider_calls':0,'grants_issued':0,'new_UI_implementation':False,
 'active_Primary_Web_batch':'wf5; independent observer only'}
(ROOT/'READONLY_POLICY_ORACLE.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'producer_negative_combinations':10,'schema1_bypass_shapes':20,'all_original_inputs_unchanged':True}))
