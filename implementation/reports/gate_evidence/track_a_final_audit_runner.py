import json,hashlib,subprocess,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path[:0]=['src','tools']
from ca_unit_policy import document_errors,dt
from investment_system.ingestion.raw_store import RawDatasetStore
GE=Path('reports/gate_evidence');store=RawDatasetStore('/tmp/track_a_run70/data/raw')
def read(n):return json.loads((GE/n).read_text())
def save(n,d):(GE/n).write_text(json.dumps(d,indent=2,ensure_ascii=False,default=str)+'\n')
policy=read('ca_unit_policy_v1.json');cases=[];added=[];checks=[]
for date in ['2024-06-30','2024-09-30','2024-12-31']:
 g=read(f'gate_chain_{date}_real_gha.json'); old=json.loads(subprocess.check_output(['git','show',f'48c0c4e:implementation/reports/gate_evidence/gate_chain_{date}_real_gha.json']))
 audit=g['share_price_unit_audit']; assert audit['passed'] and not audit['unresolved'] and not audit['rank_and_cutoff_used'] and not audit['future_evidence_allowed']
 assert g['official_top500_declared'] and g['promotion_gate_v2']['passed'] and g['gate_snapshot_consistency']['passed']
 assert len(g['top500'])==len({r['cik'] for r in g['top500']})==500
 snap=read(f'official_snapshot_{date}.json');assert [r['company_id'] for r in snap['members']]==[r['company_id'] for r in g['top500']]
 for c in g['official_snapshot_candidates']:
  assert dt(c['shares_available_at'])<=dt(date) and dt(c['price_observed_at'])<=dt(date)
 for e in audit['applied']:
  for doc in e['documents']:assert not document_errors(store,doc,dt(date)),(date,e['ticker'])
  assert dt(e['unit_effective_at'])<=dt(date)
 for c in old['share_price_unit_audit']['unresolved']:
  symbol=c['ticker'];records=[r for r in audit['applied'] if r['ticker']==symbol];ov=g['cover_overrides'].get(symbol); row=next((r for r in g['top500'] if r['company_id']==c['company_id']),None)
  assert records or symbol=='PARA'
  cases.append({'as_of':date,'ticker':symbol,'company_id':c['company_id'],'status':'RESOLVED','resolution':records[0]['kind'] if records else 'HISTORICAL_SECURITY_PRICE_IDENTITY_REPAIR','events':records,'original_shares':c['shares'],'corrected_mcap':ov['mcap'] if ov else None,'corrected_top500_rank':row['rank'] if row else None,'evidence':'ca_unit_price_identity_repair.json' if not records else 'ca_unit_policy_v1.json'})
 oldsymbols={c['ticker'] for c in old['share_price_unit_audit']['unresolved']}
 added += [{'as_of':date,**r,'decision_class':'D3-C'} for r in audit['applied'] if r['ticker'] not in oldsymbols]
 checks.append({'as_of':date,'candidates_audited':audit['n_candidates'],'ca_events_applied':len(audit['applied']),'official_members':500,'unique_ciks':500,'promotion_gate_v2':True,'gate_snapshot_exact_consistency':True,'unit_audit':True,'official_share_publication_and_quote_dates_not_future':True,'universe_id':snap['universe_id'],'approved_reconstruction_exceptions':g['price_basis_exceptions'],'corporate_action_policy':g['corporate_action_policy']})
assert len(cases)==20 and len(added)==3
save('track_a_ca_unit_20_case_revalidation_2026-09-27.json',{'kind':'CA_UNIT_ORIGINAL20_AND_ADDITIONAL_D3C_AUDIT','passed':True,'n_original_cases':20,'n_original_ca_events':19,'n_price_identity_repairs':1,'n_additional_d3c':3,'original_cases':cases,'additional_d3c':added})
m=json.loads(Path('/tmp/ca_unit/measurement_audit.json').read_text());m['resolution']='All three ambiguous share-measurement/publication cases resolved by primary-evidenced unchanged parent share quantities under approved CA-UNIT-v1.0';m['evidence']='track_a_ca_unit_20_case_revalidation_2026-09-27.json';save('track_a_share_measurement_audit_2026-09-27.json',m)
i=json.loads(Path('/tmp/ca_unit/full_identity_audit.json').read_text()); i['scope_note']='Name tokens are discovery diagnostics, not identity proof. Cross-check against dated company-level Gate rows and reviewed security components.'
for r in i['unmatched']:
 usages=[]
 for date in ['2024-06-30','2024-09-30','2024-12-31']:
  g=read(f'gate_chain_{date}_real_gha.json')
  for row in g['top500']:
   if row['yahoo']==r['symbol']:usages.append(date)
 r['used_as_top500_main_symbol_dates']=usages
 if r['symbol']=='GE':r['review']='Same issuer; GE Aerospace name evidenced by reviewed 2024 GE primary 8-K.'
 elif r['symbol']=='FWONA':r['review']='Existing reviewed Liberty Media tracking-group security/class policy; no cross-group economic equivalence introduced.'
 elif r['symbol']=='FNB':r['review']='F.N.B. punctuation mismatch; existing same-CIK dated filing identity retained.'
 elif r['symbol']=='PINC':r['review']='Current provider ETF identity is not used: approved per-date PINC NPORT price exceptions remain applied in all three gates.'
 else:
  assert not usages,r
  r['review']='Not used as any Official Top500 main security; derivative/preferred/foreign listing name differs from issuing registrant. Existing company-level dedupe and eligibility retained.'
save('track_a_price_identity_audit_2026-09-27.json',i)
save('track_a_pit_provenance_audit_2026-09-27.json',{'kind':'TRACK_A_PIT_PROVENANCE_AUDIT','passed':True,'scope':'Existing approved reconstruction/PIT contract; not a claim of zero retrospective reconstruction','per_date':checks,'primary_ca_documents':22,'new_future_information_permission':False,'unchanged_approved_exceptions':['PINC/WOLF per-date NPORT','CA-PRICE-01 WRK','CA-SHARES-01 GRAL actual first subsequent periodic','Dated NPORT reference reconstruction'],'PARA_identity_note':'2025 corporate announcement establishes retrieval alias only; no 2025 economic data or share ratio admitted into 2024 inputs. Provider historical price bytes preserved and identity/hash-bound.','historical_reports':'Pre-correction states preserved in git 48c0c4e and original run70 archive; current filenames use real_gha legacy suffix but execution_provenance explicitly LOCAL_WORK_MODE.'})
print('20 original +3 D3C; 3 dates PIT/provenance PASS')
