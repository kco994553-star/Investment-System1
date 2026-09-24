import importlib.util, json
from datetime import datetime, timezone
from pathlib import Path
from investment_system.ingestion.raw_store import RawDatasetStore
UTC=timezone.utc

def load_tool():
 p=Path(__file__).parents[1]/'tools'/'audit_mcap_store.py'; s=importlib.util.spec_from_file_location('audit_mcap_store',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_audit_is_memory_bounded_and_never_claims_completeness(tmp_path):
 m=load_tool(); store=RawDatasetStore(tmp_path/'raw'); t='2024-12-31'
 cf={'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'filed':'2024-12-01','val':100}]}}}}}
 store.put('companyfacts:0000000001',json.dumps(cf).encode(),'u','SEC','application/json','t',200)
 chart={'chart':{'result':[{'timestamp':[int(datetime(2024,12,30,tzinfo=UTC).timestamp())],'indicators':{'quote':[{'close':[12.0]}]}}],'error':None}}
 store.put('yahoo_chart:AAA:5y',json.dumps(chart).encode(),'u','YAHOO','application/json','t',200)
 r=m.audit(store,{'a':{'cik':'1','yahoo':'AAA'},'b':{'cik':'2','yahoo':'BBB'}},datetime(2024,12,31,tzinfo=UTC))
 assert r['rankable']==1 and r['missing_companyfacts']==1
 assert r['candidate_pool_complete'] is False and r['justified_official_top500'] is False

def test_multi_date_audit_reuses_each_issuer_load_once(tmp_path, monkeypatch):
 m=load_tool(); store=RawDatasetStore(tmp_path/'raw')
 cf={'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'filed':'2024-01-01','val':100},{'filed':'2025-01-01','val':120}]}}}}}
 store.put('companyfacts:0000000001',json.dumps(cf).encode(),'u','SEC','application/json','t',200)
 chart={'chart':{'result':[{'timestamp':[int(datetime(2024,6,1,tzinfo=UTC).timestamp()),int(datetime(2025,6,1,tzinfo=UTC).timestamp())],'indicators':{'quote':[{'close':[10.0,20.0]}]}}],'error':None}}
 store.put('yahoo_chart:AAA:5y',json.dumps(chart).encode(),'u','YAHOO','application/json','t',200)
 calls={'cf':0,'px':0}; ocf=m.load_companyfacts; opx=m.load_price_bars
 def cf(*a,**k): calls['cf']+=1; return ocf(*a,**k)
 def px(*a,**k): calls['px']+=1; return opx(*a,**k)
 monkeypatch.setattr(m,'load_companyfacts',cf); monkeypatch.setattr(m,'load_price_bars',px)
 rs=m.audit_many(store,{'a':{'cik':'1','yahoo':'AAA'}},[datetime(2024,12,31,tzinfo=UTC),datetime(2025,12,31,tzinfo=UTC)])
 assert calls=={'cf':1,'px':1}
 assert [r['rankable'] for r in rs]==[1,1]
 assert all(r['candidate_pool_complete'] is False for r in rs)


def test_top500_heap_is_bounded_and_cutoff_is_exact():
 m=load_tool(); h=[]
 for i in range(1000): m._top500_push(h,float(i),f'c{i}',None)
 assert len(h)==500
 assert h[0][0]==500.0

def test_ingestion_resume_plan_only_lists_absent_artifacts(tmp_path):
 m=load_tool(); store=RawDatasetStore(tmp_path/'raw')
 store.put('companyfacts:0000000001',b'{}','u','SEC','application/json','t',200)
 store.put('yahoo_chart:AAA:5y',b'{}','u','YAHOO','application/json','t',200)
 listings={'a':{'cik':'1','yahoo':'AAA'},'b':{'cik':'2','yahoo':'BBB'},'c':{'cik':'','yahoo':'CCC'}}
 p=m.build_ingestion_plan(store,listings,'5y')
 assert p['ciks']==['0000000002']
 assert p['symbols']==['BBB','CCC']
 assert p['unresolved_identifiers']==['c']
 assert p['candidate_pool_complete'] is False

def test_pit_gap_plan_distinguishes_absent_from_present_but_unusable(tmp_path):
 m=load_tool(); store=RawDatasetStore(tmp_path/'raw')
 # A has both artifacts but its first price is after as_of: refetching the same
 # present artifact blindly is not equivalent to an absent-price case.
 cf_a={'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'filed':'2024-01-01','val':100}]}}}}}
 store.put('companyfacts:0000000001',json.dumps(cf_a).encode(),'u','SEC','application/json','t',200)
 late={'chart':{'result':[{'timestamp':[int(datetime(2025,1,2,tzinfo=UTC).timestamp())],'indicators':{'quote':[{'close':[10.0]}]}}],'error':None}}
 store.put('yahoo_chart:AAA:5y',json.dumps(late).encode(),'u','YAHOO','application/json','t',200)
 # B has present companyfacts but no usable shares at the date and no price artifact.
 cf_b={'facts':{}}
 store.put('companyfacts:0000000002',json.dumps(cf_b).encode(),'u','SEC','application/json','t',200)
 listings={'a':{'cik':'1','yahoo':'AAA'},'b':{'cik':'2','yahoo':'BBB'},'c':{'cik':'3','yahoo':'CCC'}}
 p=m.build_pit_gap_plan(store,listings,[datetime(2024,12,31,tzinfo=UTC)])
 d=p['dates']['2024-12-31T00:00:00+00:00']
 assert d['no_pit_price_in_present_artifact']==['a']
 assert d['missing_shares_in_present_companyfacts']==['b']
 assert d['absent_companyfacts']==['c']
 assert p['candidate_pool_complete'] is False

def test_official_promotion_gate_never_passes_on_rank_count_alone():
 m=load_tool()
 audit={'as_of':'2024-12-31T00:00:00+00:00','listings':600,'rankable':600}
 g=m.build_official_promotion_gate(audit)
 assert g['passed'] is False
 assert 'ELIGIBILITY_COMPLETENESS_NOT_ATTESTED' in g['reasons']
 assert g['justified_official_top500'] is False


def test_official_promotion_gate_requires_dated_complete_evidence_and_full_rankability():
 m=load_tool(); a='2024-12-31T00:00:00+00:00'
 ev={'as_of':a,'source':'dated-us-listing-snapshot','source_vintage':'2025-01-02','eligibility_complete':True}
 incomplete=m.build_official_promotion_gate({'as_of':a,'listings':601,'rankable':600},ev)
 assert incomplete['passed'] is False
 assert incomplete['reasons']==['ELIGIBLE_LISTINGS_NOT_FULLY_RANKABLE']
 complete=m.build_official_promotion_gate({'as_of':a,'listings':600,'rankable':600},ev)
 assert complete['passed'] is True
 assert complete['candidate_pool_complete'] is True
 assert complete['justified_official_top500'] is True

def test_cli_gate_writes_fail_closed_result(tmp_path, monkeypatch):
 m=load_tool(); store=RawDatasetStore(tmp_path/'raw')
 listings=tmp_path/'listings.json'; listings.write_text(json.dumps({}),encoding='utf-8')
 ev=tmp_path/'eligibility.json'; ev.write_text(json.dumps({'as_of':'2024-12-31T00:00:00+00:00','source':'x','source_vintage':'v','eligibility_complete':True}),encoding='utf-8')
 out=tmp_path/'gate.json'
 monkeypatch.setattr('sys.argv',['audit_mcap_store.py','--store',str(tmp_path/'raw'),'--listings',str(listings),'--as-of','2024-12-31T00:00:00+00:00','--eligibility-evidence',str(ev),'--gate-out',str(out)])
 m.main()
 g=json.loads(out.read_text(encoding='utf-8'))
 assert g['passed'] is False
 assert 'FEWER_THAN_500_RANKABLE' in g['reasons']
 assert g['justified_official_top500'] is False
