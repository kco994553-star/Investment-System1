'use strict';
// Display-only filters: existing classification rules, synthetic inputs, no provider calls.
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const W=path.join(__dirname,'../src/investment_system/product/web_assets'),F=require('./qgv_v2_fixture.js');
for(const [name,file] of [['TypeConfigDefaults','type-config-defaults.js'],['CompanyScreen','company-screen.js'],['UniverseCompany','universe-company.js']])globalThis[name]=require(path.join(W,file));
const L=require(path.join(W,'leaderboard-screen.js')),P=require(path.join(W,'portfolio-screen.js')),QI=require(path.join(W,'qgv2-inputs.js')),QS=require(path.join(W,'qgv-scores.js'));
const deepFreeze=o=>{if(o&&typeof o==='object'&&!Object.isFrozen(o)){Object.values(o).forEach(deepFreeze);Object.freeze(o);}return o;};
const ids=[{company_id:'nvda',ticker:'NVDA'},{company_id:'amd',ticker:'AMD'},{company_id:'hanmi',ticker:'042700'}];
function screens(){return {'company-classification.json':{data:{industry_config:{groups:[{id:'manufacturing_industrial_tech',name:'제조·산업·기술',name_en:'Manufacturing / industrial / technology'}]},companies:{nvda:{industry:{state:'LIVE',group:'manufacturing_industrial_tech'},themes:{memberships:{finance_real_estate:{member:true}}}},amd:{industry:{state:'NOT_AVAILABLE',group:null}}}}},
 'company-types-pricefree.json':{data:{companies:{nvda:{state:'LIVE',memberships:{growth:.8,quality:.35,cyclical:null,defensive:null}},amd:{state:'LIVE',memberships:{growth:.1,quality:.1,cyclical:null,defensive:null}}}}}};}
test('2.1.3 no longer tells users the approved SIC/type filters are unconnected',()=>{
 for(const locale of ['ko-KR','en-US'])assert.doesNotMatch(L.filterNoteHtml(locale),/미연결|아직 연결되지|not connected/i);
});
test('portfolio links to the existing official N sets without claiming TARGET is finalized',()=>{
 for(const locale of ['ko-KR','en-US']){const html=P.shell(locale);assert.doesNotMatch(html,/생성기 없음|생성기가 아직|no generator|no selector/i);
  assert.match(html,/N10[\s\S]*N15[\s\S]*N20/);assert.match(html,/href="#leaderboard"/);assert.match(html,locale==='en-US'?/TARGET.*not finalized/:/TARGET 확정 결과는 (?:아닙니다|아니며)/);}
});
test('industry and type filters intersect, without theme substitution; missing differs from no selected type',()=>{
 assert.equal(typeof L.filterClassifications,'function','approved display filter API must exist');const s=deepFreeze(screens()),rows=deepFreeze(structuredClone(ids));
 const run=filters=>L.filterClassifications(rows,{publicScreens:s,filters}).map(x=>x.company_id);
 assert.deepEqual(run({industry:'manufacturing_industrial_tech',type:'growth'}),['nvda']);
 assert.deepEqual(run({industry:'finance_real_estate'}),[],'theme membership must not act as an industry');
 assert.deepEqual(run({industry:'NOT_AVAILABLE'}),['amd','hanmi']);
 assert.deepEqual(run({type:'NOT_AVAILABLE'}),['hanmi']);assert.deepEqual(run({type:'NO_SELECTED_TYPE'}),['amd']);
 assert.deepEqual(run({type:'quality'}),['nvda'],'reuse official mixing, including overlap');
 assert.deepEqual(run({industry:'removed_group'}),[],'disappearing selection must not silently broaden to all');
 assert.equal(L.filterClassifications(rows,{publicScreens:s,filters:{}})[0],rows[0],'same identity objects');
});
test('all classification filter combinations leave Universe504, official scores/ranks and model eligibility unchanged',()=>{
 assert.equal(typeof L.filterClassifications,'function','approved display filter API must exist');
 const payload=F.strictPayload(),SQ=require(path.join(W,'sec-qgv2.js')),inputs=QI.fromInputs(SQ.toInputs(payload,{now:'2026-10-13T12:00:00Z'})),targets=Object.entries(F.TICKERS).map(([company_id,code])=>({company_id,ticker:code.split(':')[1]}));
 const U=QS.universeIdentities(inputs,targets),quotes=Object.fromEntries(F.strictUniverseValues().slice(1).map(([code,,price])=>[code,{price,currency:'USD',state:'READY'}]));
 const S=QS.compute({identities:U.identities,v2Inputs:inputs,quotes,official:U}),M=QS.officialModel({identities:U.identities,v2Inputs:inputs,quotes,official:U,computed:S});
 assert.equal(U.codes,504);assert.ok(S.official.ranked>0,'nonempty synthetic official ranking');assert.ok(M.sets.N20.selected.length>0,'nonempty candidate set');
 const before=JSON.stringify({inputs,U,S,M}),pub=deepFreeze({...screens(),'sec-qgv2.json':inputs});deepFreeze(U);deepFreeze(S);deepFreeze(M);
 for(const industry of ['', 'manufacturing_industrial_tech','finance_real_estate','NOT_AVAILABLE','removed_group'])for(const type of ['', 'growth','quality','NOT_AVAILABLE','NO_SELECTED_TYPE']){
  const shown=L.filterClassifications(U.identities,{publicScreens:pub,filters:{industry,type}});
  assert.ok(shown.every(r=>U.identities.includes(r)));assert.equal(JSON.stringify({inputs,U,S,M}),before);
  const again=QS.officialModel({identities:U.identities,v2Inputs:inputs,quotes,official:U,computed:S});assert.deepEqual(again,M,'same official eligibility, exclusions, N sets and weights');
 }
});
test('Universe filters reuse published groups and existing type selection, including missing/withdrawn data',()=>{
 assert.equal(typeof L.filterClassifications,'function');const inputs=QI.fromInputs(QI.light(F.payload()));
 inputs.records['NASDAQ:SYNS1'].metrics={revenue_cagr_3y:.3,roic:.3};
 inputs.records['NASDAQ:SYNS2'].metrics={revenue_cagr_3y:0,roic:0};
 inputs.records['NYSE:SYNI1'].state='WITHDRAWN';inputs.records['NYSE:SYNI1'].identity_withdrawn=true;
 const rows=['NASDAQ:SYNS1','NASDAQ:SYNS2','NYSE:SYNI1'].map(company_id=>({company_id,ticker:company_id.split(':')[1]})),pub={'sec-qgv2.json':inputs};
 assert.deepEqual(L.filterClassifications(rows,{publicScreens:pub,filters:{type:'growth'}}).map(x=>x.company_id),['NASDAQ:SYNS1']);
 assert.deepEqual(L.filterClassifications(rows,{publicScreens:pub,filters:{type:'NOT_AVAILABLE'}}).map(x=>x.company_id),['NYSE:SYNI1']);
 assert.deepEqual(L.filterClassifications(rows,{publicScreens:pub,filters:{industry:'NOT_AVAILABLE'}}).map(x=>x.company_id),['NYSE:SYNI1']);
});
