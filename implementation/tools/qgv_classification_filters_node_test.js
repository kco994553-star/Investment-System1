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
// L3 (2.1.3): SIC 4-digit / 2-digit display filters and the SIC column read only the published SIC code (company-classification
// industry.sic for a TARGET id, sec-qgv2 `sic` for a Universe code). Missing SIC is never 0, a group, a theme or a neighbour's code.
function sicScreens(){const s=screens(),c=s['company-classification.json'].data.companies;
 c.nvda.industry={state:'LIVE',sic:'3674',group:'manufacturing_industrial_tech'};c.amd.industry={state:'NOT_AVAILABLE',sic:'3672',group:null,reason_code:'SIC_UNMATCHED'};
 c.msft={industry:{state:'LIVE',sic:'7372',group:'services_software_health'}};c.gev={industry:{state:'NOT_AVAILABLE',sic:null,group:null,reason_code:'SIC_NOT_AVAILABLE'}};
 c.hanmi={themes:{memberships:{manufacturing_industrial_tech:{member:true}}}};return s;}
const sicIds=[...ids,{company_id:'msft',ticker:'MSFT'},{company_id:'gev',ticker:'GEV'}];
test('SIC 4-digit and 2-digit filters use only published codes; missing SIC is never relabeled or matched by a code',()=>{
 assert.equal(typeof L.sicOf,'function','SIC reader API must exist');const s=deepFreeze(sicScreens()),rows=deepFreeze(structuredClone(sicIds));
 assert.deepEqual(rows.map(r=>L.sicOf(r,s)),['3674','3672',null,'7372',null],'published code or null; theme and group never fill it');
 assert.deepEqual(rows.map(r=>L.classificationOf(r,s).sic),['3674','3672',null,'7372',null]);
 const run=filters=>L.filterClassifications(rows,{publicScreens:s,filters}).map(x=>x.company_id);
 assert.deepEqual(run({sic4:'3674'}),['nvda']);assert.deepEqual(run({sic2:'36'}),['nvda','amd']);assert.deepEqual(run({sic2:'73'}),['msft']);
 assert.deepEqual(run({sic4:'NOT_AVAILABLE'}),['hanmi','gev']);assert.deepEqual(run({sic2:'NOT_AVAILABLE'}),['hanmi','gev']);
 for(const f of [{sic4:'3674'},{sic2:'36'},{sic2:'73'},{sic4:'0000'},{sic2:'00'}])for(const id of run(f))assert.ok(['nvda','amd','msft'].includes(id),'a missing-SIC row never matches a code filter');
 assert.deepEqual(run({sic4:'9999'}),[],'a code absent from the publication never broadens to all');assert.deepEqual(run({sic2:'36',sic4:'7372'}),[],'axes intersect');
 assert.deepEqual(run({sic2:'36',industry:'manufacturing_industrial_tech'}),['nvda'],'SIC code and industry group intersect; a group never stands in for a code');
 assert.deepEqual(run({sic2:'36',type:'growth'}),['nvda']);assert.equal(L.filterClassifications(rows,{publicScreens:s,filters:{sic2:'',sic4:''}})[1],rows[1],'same identity objects');
});
test('SIC filter controls and the SIC column: codes from the data only, no invented SIC names, missing counted apart',()=>{
 const s=deepFreeze(sicScreens()),html=L.classificationFiltersHtml(sicIds,{publicScreens:s,locale:'ko-KR'}),en=L.classificationFiltersHtml(sicIds,{publicScreens:s,locale:'en-US'});
 for(const h of [html,en]){assert.match(h,/id="leader-classification-sic4"/);assert.match(h,/id="leader-classification-sic2"/);
  const v=axis=>[...h.split('id="leader-classification-'+axis+'"')[1].split('</select>')[0].matchAll(/value="([^"]*)"/g)].map(m=>m[1]);
  assert.deepEqual(v('sic4'),['','3672','3674','7372','NOT_AVAILABLE']);assert.deepEqual(v('sic2'),['','36','73','NOT_AVAILABLE']);
  for(const axis of ['sic2','sic4'])assert.doesNotMatch(h.split('id="leader-classification-'+axis+'"')[1].split('</select>')[0],/반도체|소프트웨어|Semiconductor|Software/,'no SIC name label: no public file carries one');assert.match(h,/for="leader-classification-sic4"/);}
 assert.match(html,/SIC 자료 없음 2/);assert.match(en,/SIC missing 2/);
 assert.deepEqual(L.COLUMNS.find(c=>c[0]==='sic'),['sic','SIC','SIC',true],'SIC column: wide table; phone shows the code in the company cell');
 assert.ok(L.COLUMNS.findIndex(c=>c[0]==='sic')===L.COLUMNS.findIndex(c=>c[0]==='company')+1);
 for(const locale of ['ko-KR','en-US'])assert.match(L.filterNoteHtml(locale),locale==='en-US'?/SIC code[\s\S]*only the code/:/SIC 코드[\s\S]*코드만/);
});
test('Universe codes read the sec-qgv2 SIC; withdrawn identities have none',()=>{
 const inputs=QI.fromInputs(QI.light(F.payload()));inputs.records['NYSE:SYNI1'].state='WITHDRAWN';inputs.records['NYSE:SYNI1'].identity_withdrawn=true;inputs.records['NYSE:SYNI1'].sic='3600';
 const rows=['NASDAQ:SYNS1','NYSE:SYNF1','NYSE:SYNI1','NYSE:NOPE'].map(company_id=>({company_id,ticker:company_id.split(':')[1]})),pub={'sec-qgv2.json':inputs};
 assert.deepEqual(rows.map(r=>L.sicOf(r,pub)),['3674','6022',null,null]);
 assert.deepEqual(L.filterClassifications(rows,{publicScreens:pub,filters:{sic2:'60'}}).map(x=>x.company_id),['NYSE:SYNF1']);
 assert.deepEqual(L.filterClassifications(rows,{publicScreens:pub,filters:{sic4:'NOT_AVAILABLE'}}).map(x=>x.company_id),['NYSE:SYNI1','NYSE:NOPE']);
});
test('SIC filter combinations leave Universe504, official scores/ranks and model eligibility unchanged',()=>{
 const payload=F.strictPayload(),SQ=require(path.join(W,'sec-qgv2.js')),inputs=QI.fromInputs(SQ.toInputs(payload,{now:'2026-10-13T12:00:00Z'})),targets=Object.entries(F.TICKERS).map(([company_id,code])=>({company_id,ticker:code.split(':')[1]}));
 const U=QS.universeIdentities(inputs,targets),quotes=Object.fromEntries(F.strictUniverseValues().slice(1).map(([code,,price])=>[code,{price,currency:'USD',state:'READY'}]));
 const S=QS.compute({identities:U.identities,v2Inputs:inputs,quotes,official:U}),M=QS.officialModel({identities:U.identities,v2Inputs:inputs,quotes,official:U,computed:S});
 const before=JSON.stringify({inputs,U,S,M}),pub=deepFreeze({...sicScreens(),'sec-qgv2.json':inputs});deepFreeze(U);deepFreeze(S);deepFreeze(M);const ranks=Object.fromEntries(Object.entries(S.rows).map(([k,r])=>[k,r.rank]));
 let coded=0;for(const sic4 of ['','3674','6021','NOT_AVAILABLE','9999'])for(const sic2 of ['','36','60','NOT_AVAILABLE','99']){
  const shown=L.filterClassifications(U.identities,{publicScreens:pub,filters:{sic4,sic2}});if(sic4==='3674'&&!sic2)coded=shown.length;
  assert.ok(shown.every(r=>U.identities.includes(r)));assert.equal(JSON.stringify({inputs,U,S,M}),before);assert.deepEqual(Object.fromEntries(Object.entries(S.rows).map(([k,r])=>[k,r.rank])),ranks);
  if(sic4&&sic4!=='NOT_AVAILABLE'||sic2&&sic2!=='NOT_AVAILABLE')assert.ok(shown.every(r=>L.sicOf(r,pub)!==null),'missing SIC never under a code filter');
  assert.deepEqual(QS.officialModel({identities:U.identities,v2Inputs:inputs,quotes,official:U,computed:S}),M);}
 assert.ok(coded>0,'nonempty synthetic SIC selection');
});
