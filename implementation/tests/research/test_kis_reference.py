from copy import deepcopy
import importlib,runpy,json
from pathlib import Path
import pytest
from investment_system.research._private_artifacts import digest


def sample():
 return runpy.run_path(str(Path(__file__).parents[2]/'tools/kis_contract_fixture.py'))['fixtures']()['synthetic-raw.json']

def api():return importlib.import_module('investment_system.research.private_kis_reference')

def test_reference_does_not_upgrade_adopted_values():
 c=sample();c['identity']['identity_status']='UNKNOWN';c['confirmed_ranges']=[]
 from investment_system.research.technical_handoff import prepare_technical
 from investment_system.research.private_kis_preprocess import project_technical
 h=prepare_technical(c,evaluation_day='2026-10-23',series_id='SYN')
 files=project_technical(c,h,expected_contract_hash=digest(c),expected_handoff_hash=digest(h))
 result=api().reference_files(files,c,'2026-10-23')
 a=json.loads(result['technical/S/SYN.json']);m=a['metrics']['SMA_5']
 assert m['value'] is None and m['reference_value']==11
 assert m['validation_tier']=='UNVERIFIED_REFERENCE' and a['adopted_count']==0
 assert json.loads(result['chart/S/SYN.json'])['display']['official'] is False
 assert files!=result

@pytest.mark.parametrize('ratio',['0.5','2','0.3333333333','3'])
def test_integer_like_raw_jump_is_hold_not_confirmed_split(ratio):
 c=sample();from decimal import Decimal
 for rows in (c['raw_bars'],c['bars']):
  for r in rows[2:]:
   for f in ('open','high','low','close'):r[f]=str(Decimal(r[f])*Decimal(ratio))
 d=api().split_candidates(c,'2026-10-23')
 assert d and d[0]['confirmed'] is False
 assert api().split_candidates(c,'2026-10-20')==[]

def test_modp1_not_reference_input():
 c=sample();c['source_query']['MODP']='1'
 with pytest.raises(ValueError,match='RAW_DAILY'):api().split_candidates(c,'2026-10-23')

def test_no_split_candidate_from_small_change():
 assert api().split_candidates(sample(),'2026-10-23')==[]

def test_verified_split_does_not_infer_another_event():
 c=sample();c['splits']=[dict(date='2026-10-21',ratio='2',status='CONFIRMED',evidence='SYN')]
 c['raw_bars'][2]['close']='5.5';c['raw_bars'][2]['low']='4'
 c['bars']=deepcopy(c['raw_bars'])
 assert not any(r['date']=='2026-10-21' for r in api().split_candidates(c,'2026-10-23'))


def test_official_adapter_reuses_exact_engine_and_rejects_pins():
 from investment_system.qgv import qgv_official as common
 from investment_system.universe.sec_universe_shares import universe_codes
 from investment_system.universe.sec_qgv2 import empty_record
 from datetime import datetime
 payload=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_text())['base']
 payload['records']={c:payload['records'].get(c) or empty_record() for c in universe_codes()}
 args=dict(day='2026-10-23',calculated_at='2026-10-24T04:00:00Z',expected_payload_hash=digest(payload),expected_links_hash=digest({}),expected_contract_hashes={})
 result=api().official_reference(payload,{}, {},**args)
 ctx=common.prepare(payload,datetime.fromisoformat('2026-10-24T04:00:00+00:00'))
 expected={k:common.projection(v) for k,v in common.score(ctx,{}).items()}
 assert result['rows']==api().mask_incomplete_totals(dict(rows=expected,population=sorted(payload['records']),coverage={}))['rows'] and result['coverage']['V']==0
 assert result['rank'] is None and result['official_publication_replaced'] is False
 args['expected_payload_hash']='0'*64
 with pytest.raises(ValueError,match='SOURCE_PIN_MISMATCH'):api().official_reference(payload,{}, {},**args)


def test_partial_total_is_never_delivered_as_total():
 packet={'rows':{'partial':{'axes':{'Q':{'score':50},'G':{'score':50},'V':{'score':None}},'total':50,'total_reason':None},'full':{'axes':{a:{'score':50} for a in ['Q','G','V']},'total':50,'total_reason':None}},'population':['partial','full'],'coverage':{'engine_total_computed':2}}
 before=deepcopy(packet);r=api().mask_incomplete_totals(packet)
 assert packet==before
 assert r['rows']['partial']['total'] is None
 assert r['rows']['partial']['total_reason']=='THREE_AXES_REQUIRED'
 assert r['rows']['full']['total']==50
 assert r['coverage']['total']==1 and r['diagnostics']['suppressed_partial_totals']==1

 assert api().mask_incomplete_totals(r)==r
