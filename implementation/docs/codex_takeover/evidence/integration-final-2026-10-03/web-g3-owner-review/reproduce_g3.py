"""Exact existing source, isolated hand-built TEST VECTOR; no data providers."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from investment_system.product.web_mvp import SECTIONS, build, validate_bundle
from investment_system.producers.contract import make_snapshot, validate_snapshot, RESEARCH_STATUSES
from investment_system.producers.errors import ResearchStatusError

HERE=Path(__file__).resolve().parent
ROOT=Path('/workspace/gsup-v2-integration')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == '675d0d298fbaab5b8473ed048a561ef84e2f3e78'
cid='G3_SYNTHETIC_TEST_VECTOR_ONLY'
bundle={'schema_version':1,'companies':[{'company_id':cid,'ticker':'G3TEST','name':'G3 TEST VECTOR ONLY'}],
 'universe':{'state':'DEMO','as_of':'2026-10-03T00:00:00Z','source':'G3 isolated synthetic test vector',
             'data':{'synthetic':True,'members':[]}}}
for name in SECTIONS:
 bundle[name]={'state':'NOT_AVAILABLE','as_of':None,'source':None,'reason':'G3 isolated test vector has no producer data','data':None}
values={cid:{'Q_score':11.11,'G_score':22.22,'V_score':33.33,'total_score':44.44}}
method={'id':'G3_TEST_VECTOR_ONLY','version':'TEST_ONLY','status':'PROVISIONAL_RESEARCH'}
bundle['qgv']={'state':'LIVE','as_of':'2026-10-03T00:00:00Z','expires_at':'2099-01-01T00:00:00Z',
 'source':'G3 SYNTHETIC TEST VECTOR falsely labelled LIVE; NEVER PRODUCTION', 'data':values,'methodology':method}
# Deliberately omit payload synthetic markers on the bad qgv envelope to exercise
# the methodology guard rather than the separate already-working DEMO guard.
validated=validate_bundle(bundle)
(HERE/'test-vector.schema1.json').write_text(json.dumps(bundle,indent=2)+'\n')
build(HERE/'isolated-web',bundle=bundle)
snap=make_snapshot(producer_id='G3_TEST_VECTOR_ONLY',producer_version='TEST_ONLY',section='qgv',
 data_state='LIVE',as_of=bundle['qgv']['as_of'],generated_at='2026-10-03T00:01:00Z',
 expires_at=bundle['qgv']['expires_at'],methodology=method,synthetic=False,
 provenance={'source':'G3 test vector only','inputs':[{'artifact_id':'G3_TEST_VECTOR_ONLY','sha256':'0'*64}]},
 validation={'status':'PASS','checks':['TEST_VECTOR_ONLY']},data=values,scope_kind='ENTITY_MAP')
try:
 validate_snapshot(snap)
except ResearchStatusError as exc:
 producer={'status':'REJECTED','error_type':type(exc).__name__,'message':str(exc)}
else:
 raise AssertionError('existing producer research policy must reject')
paths=['implementation/src/investment_system/product/web_mvp.py','implementation/src/investment_system/product/web_assets/app.js']
receipt={'source_head':'675d0d298fbaab5b8473ed048a561ef84e2f3e78','scope':'HAND_BUILT_TEST_VECTOR_ONLY',
 'web_schema1_admission':'ACCEPTED','frozen_builder':'ACCEPTED','producer_admission':producer,
 'existing_research_statuses':sorted(RESEARCH_STATUSES),
 'source_sha256':{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
 'copied_app_js_identical':(ROOT/paths[1]).read_bytes()==(HERE/'isolated-web/app.js').read_bytes(),
 'real_data_provider_calls':0,'CAL_VERIFY_actual_access':'NOT_RUN','Holdout_actual_access':'NOT_RUN',
 'grants_issued':0,'source_changes':0}
(HERE/'reproduction-admission-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
