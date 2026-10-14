'use strict';
// 13F manager style config (device copy) + style filter + verification binding, synthetic data only.
const assert=require('node:assert/strict'),test=require('node:test'),{spawnSync}=require('node:child_process'),path=require('node:path'),fs=require('node:fs');
const root=path.resolve(__dirname,'..'),api=require('../src/investment_system/product/web_assets/public-screens.js'),copy=require('../src/investment_system/product/web_assets/manager-styles-v0.js');
const script="import json,tempfile;from pathlib import Path;from tests.test_sec_13f_managers import tool,config,client,site,NOW\nwith tempfile.TemporaryDirectory() as d:print(json.dumps(tool().build(Path(d),config=config(),fetch=client(site()).fetch,now=lambda:NOW)[0]))";
const run=spawnSync('python3',['-c',script],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')+path.delimiter+root},encoding:'utf8'});
assert.equal(run.status,0,run.stderr);const generated=JSON.parse(run.stdout);
test('device copy equals the versioned Python config and is frozen',()=>{assert.deepEqual(JSON.parse(JSON.stringify(copy)),JSON.parse(fs.readFileSync(path.join(root,'src/investment_system/config/manager_styles_v0.json'),'utf8')));
 assert.equal(copy.config_version,'manager_styles/v0');assert.equal(copy.label_ko,'일반적 평가 기반 v0 분류');assert.ok(Object.isFrozen(copy.managers[0].styles));assert.equal(api.managerStyles(),copy);assert.equal(copy.managers.length,10);});
test('style filter matches any selected style, empty selection keeps all',()=>{const config={styles:copy.styles,managers:[{...copy.managers[0],id:'a',styles:['value','activist']},{...copy.managers[1],id:'b',styles:['quant']},{...copy.managers[2],id:'c',styles:['macro','growth_tech']}]};
 const rows=api.managerRows(config,{data:{reports:[],role:'REPORTED_QUANTITY_CHANGE_NOT_TRADES'}}),ids=sel=>api.filterManagerRows(rows,sel).map(r=>r.manager.id);
 assert.deepEqual(ids([]),['a','b','c']);assert.deepEqual(ids(['activist']),['a']);assert.deepEqual(ids(['quant','growth_tech']),['b','c']);assert.deepEqual(ids(['event']),[]);assert.deepEqual(ids(undefined),['a','b','c']);
 const real=api.managerRows(copy,null);assert.deepEqual(api.filterManagerRows(real,['growth_tech']).map(r=>r.manager.display_name),['Coatue Management','Tiger Global']);
 assert.deepEqual(api.filterManagerRows(real,['value','quant']).map(r=>r.manager.id),['berkshire_hathaway','baupost_group','renaissance_technologies']);});
test('JS validator accepts the Python 13F step output and binds names only to verified CIKs',()=>{assert.equal(api.validate('sec-13f-changes.json',structuredClone(generated)).state,'LIVE');
 const config={styles:copy.styles,managers:[{...copy.managers[0],id:'synthetic_value',candidate_cik:'0000000123'},{...copy.managers[1],id:'synthetic_other',candidate_cik:'0000000456'},{...copy.managers[2],id:'synthetic_unset',candidate_cik:null},{...copy.managers[3],id:'not_run',candidate_cik:'0000000789'}]};
 const rows=api.managerRows(config,generated);assert.deepEqual(rows.map(r=>[r.verified,r.reason,r.report&&r.report.changes.length]),[[true,null,1],[false,'NAME_MISMATCH',null],[false,'CIK_NOT_CONFIGURED',null],[false,'VERIFICATION_NOT_RUN',null]]);
 const edited={...config,managers:[{...config.managers[0],candidate_cik:'0000000999'}]};assert.deepEqual(api.managerRows(edited,generated).map(r=>[r.verified,r.reason,r.report]),[[false,'VERIFICATION_NOT_RUN',null]]);
 for(const mutate of [p=>{p.data.managers[0].state='NOT_AVAILABLE';p.data.managers[0].reason_code='NAME_MISMATCH';p.data.managers[0].matched_name=null;p.data.managers[0].verified_at=null;p.data.managers[0].latest_13f_accession=null;},p=>{p.data.managers[1].matched_name='x';},p=>{p.data.managers[0].latest_13f_accession='1';},p=>{p.data.managers[2].cik='0000000001';},p=>{p.data.managers[0].capture_reason='OTHER';},p=>{p.data.extra=1;},p=>{p.data.managers.push(structuredClone(p.data.managers[0]));}]){const p=structuredClone(generated);mutate(p);assert.throws(()=>api.validate('sec-13f-changes.json',p));}
 const legacy=structuredClone(generated);delete legacy.data.managers;assert.equal(api.validate('sec-13f-changes.json',legacy).state,'LIVE');});
test('limitation text covers delay, US-listed long positions and quant/macro reference in both languages',()=>{for(const t of ['분기 종료 후 최대 45일','미국 상장 주식(13F 대상 증권)','매수 포지션만','퀀트·매크로 기관','참고용'])assert.ok(api.LIMITS.ko.includes(t),t);
 for(const t of ['45 days after quarter end','long positions in US-listed equities (13F securities)','Quant and macro managers are reference only'])assert.ok(api.LIMITS.en.includes(t),t);});
test('13F complete snapshots and informational E4 match Python, no missing-data exits',()=>{
 const Q=require('../src/investment_system/product/web_assets/thirteenf-quarter.js');
 const code="import json;from tests.test_thirteenf_enrichment import evidence_payload;from investment_system.product import thirteenf_quarter as q;from investment_system.product.device_actual_catalog import public_actual_catalog;p,c=evidence_payload();cat=public_actual_catalog();print(json.dumps(dict(payload=p,config=c,catalog=cat,expected=q.playbook_evidence(p,cat,c))))";
 const result=spawnSync('python3',['-c',code],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')+path.delimiter+root},encoding:'utf8'});assert.equal(result.status,0,result.stderr);
 const data=JSON.parse(result.stdout);assert.deepEqual(Q.playbookEvidence(data.payload,data.catalog,data.config),data.expected);
 assert.equal(data.expected.nvda.full_exit_count,3);assert.equal(data.expected.nvda.structural_event,true);
 const mutations=[p=>p.data.reports[2].state='STALE',p=>p.data.reports[2].current_quarter='2026-03-31',p=>p.data.managers[2].state='NOT_AVAILABLE',p=>delete p.data.reports[2].details,p=>p.data.reports[2].changes=[],p=>p.data.reports[2].changes[0].cusip='594918104',p=>{p.data.reports[2].manager_cik='0000000011';p.data.managers[2].cik='0000000011';},p=>p.data.reports[2].details.current.reported_holdings=structuredClone(p.data.reports[2].details.previous.reported_holdings),p=>p.data.reports[2].manager_cik=p.data.reports[1].manager_cik];
 for(const mutate of mutations){const p=structuredClone(data.payload);mutate(p);assert.equal(Q.playbookEvidence(p,data.catalog,data.config).nvda.structural_event,false);}
 const p=structuredClone(data.payload);p.data.reports.forEach(r=>delete r.details);assert.equal(Q.playbookEvidence(p,data.catalog,data.config).nvda.tracked_holding_count,null);
});
test('13F details reject arbitrary prices and units in both public consumers',()=>{
 const p=structuredClone(generated),report=p.data.reports[0],hold=report.details.current.reported_holdings[0];
 assert.equal(hold.reported_value,2000);assert.equal(hold.reported_value_basis,'USD_DOLLARS');
 for(const mutate of [r=>r.details.scope='PRIVATE',r=>r.details.current.filing_date='2026-03-30',r=>r.details.current.reported_holdings[0].price=1,r=>r.details.current.reported_holdings[0].reported_value_basis='CURRENT_USD',r=>r.details.current.reported_holdings[0].issuer_names=['invalid'+'@'+'host.test']]){const other=structuredClone(p);mutate(other.data.reports[0]);assert.throws(()=>api.validate('sec-13f-changes.json',other));}
});
