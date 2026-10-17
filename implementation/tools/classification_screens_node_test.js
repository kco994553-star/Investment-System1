'use strict';
// SIC industry group v0 / theme v0: JS validator parity with the Python fixture, shared concentration vectors
// (Python reference qgv.theme_membership) and the S04/S03 presentation helpers. Synthetic data only.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'..'),api=require(path.join(root,'src/investment_system/product/web_assets/classification-screens.js'));
const fixtures=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/company_classification_v0_payloads.json'),'utf8'));
const vectors=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/theme_concentration_v0_vectors.json'),'utf8'));
const config=JSON.parse(fs.readFileSync(path.join(root,'src/investment_system/qgv/theme_config_v0.json'),'utf8'));
const clone=v=>JSON.parse(JSON.stringify(v));

test('threshold is the v0 config default',()=>{assert.equal(api.THRESHOLD,config.concentration_warning.single_theme_max_share);assert.equal(vectors.threshold,api.THRESHOLD);});

test('shared concentration vectors match the Python reference',()=>{
 for(const c of vectors.cases){const got=api.themeConcentration({rows:c.rows,memberships:c.memberships,themeIds:c.theme_ids,threshold:vectors.threshold});
  assert.deepEqual(got.warnings,c.expected.warnings,c.name);assert.equal(got.themes.length,c.expected.themes.length);
  got.themes.forEach((t,i)=>{const e=c.expected.themes[i];assert.equal(t.id,e.id);assert.equal(t.status,e.status,c.name+' '+t.id);assert.ok(Math.abs(t.exposure-e.exposure)<1e-12);assert.ok(Math.abs(t.unknown-e.unknown)<1e-12);});}
 for(const c of vectors.status_cases)assert.equal(api.concentrationStatus(c.exposure,c.unknown,vectors.threshold),c.status);
});

test('validator accepts the Python-generated payloads and rejects the same mutations',()=>{
 assert.equal(api.validate(clone(fixtures.live)).state,'LIVE');assert.equal(api.validate(clone(fixtures.offline)).state,'NOT_AVAILABLE');
 const mutations=[q=>{q.data.etfs.SMH.weight=0.05;},q=>{q.data.companies.nvda.themes.memberships.ai.evidence=[];},q=>{q.data.companies.amd.themes.memberships.ai.member=false;},
  q=>{q.data.companies.nvda.themes.memberships.ai.etfs=['SOXX'];},q=>{q.data.companies.nvda.industry.group='utilities_x';},q=>{q.data.companies.gev.industry.sic='0000';},
  q=>{q.data.companies.nvda.themes.item1='text';},q=>{q.state='STALE';},q=>{q.sources.push({agency:'SEC_13F',sha256:'a'.repeat(64),acquired_at:q.as_of});},
  q=>{q.data.theme_config.themes[0].etfs=['AIQ','AIQ'];},q=>{q.data.companies.nvda.themes.memberships.ai.member=0;},q=>{delete q.data.companies.rok;}];
 mutations.forEach((m,i)=>{const q=clone(fixtures.live);m(q);assert.throws(()=>api.validate(q),/PUBLIC_CLASSIFICATION_INVALID/,'mutation '+i);});
});

test('S04 chips: group, SIC, evidence kinds, weak-evidence flag and v0 marker; NOT_AVAILABLE otherwise',()=>{
 const p=fixtures.live;
 const nvdaIndustry=api.industryChip(p,'nvda','ko-KR');assert.match(nvdaIndustry,/data-industry-chip="manufacturing_industrial_tech"/);assert.match(nvdaIndustry,/반도체/);assert.match(nvdaIndustry,/SIC 3674/);assert.match(nvdaIndustry,/v0 기본값 · 보정 전 · 나중에 수정 가능/);
 assert.match(api.industryChip(p,'gev','ko-KR'),/NOT_AVAILABLE[\s\S]*SIC 없음/);assert.match(api.industryChip(p,'hanmi','en-US'),/Not an SEC registrant/);
 const nvdaTheme=api.themeChip(p,'nvda','ko-KR');assert.match(nvdaTheme,/data-theme-chip="semiconductors"/);assert.match(nvdaTheme,/ETF SOXX·SMH \+ 10-K 키워드/);assert.doesNotMatch(nvdaTheme,/data-theme-chip="cybersecurity"/);
 const msft=api.themeChip(p,'msft','ko-KR');assert.match(msft,/data-weak-evidence="consumer_brands"/);assert.match(msft,/근거 약함/);
 assert.match(api.themeChip(p,'amd','ko-KR'),/NOT_AVAILABLE/);assert.match(api.themeChip(fixtures.offline,'nvda','ko-KR'),/NOT_AVAILABLE/);assert.match(api.themeChip(null,'nvda','ko-KR'),/NOT_AVAILABLE/);
 const en=api.themeChip(p,'nvda','en-US')+api.industryChip(p,'nvda','en-US');assert.doesNotMatch(en,/[가-힣]/);assert.match(en,/v0 default · uncalibrated · editable later/);
});

test('S03 industry composition and concentration warning run on RAM weights only',()=>{
 const p=fixtures.live,idByTicker=new Map([['NVDA','nvda'],['MSFT','msft'],['042700','hanmi']]);
 const ram={state:'AVAILABLE',rows:[{ticker:'NVDA',weight:0.5},{ticker:'MSFT',weight:0.3},{ticker:'042700',weight:0.2}],themes:[{theme_id:'ai_semi',weight:0.5},{theme_id:'big_tech',weight:0.3},{theme_id:'semi_equipment',weight:0.2}]};
 const comp=api.industryComposition({rows:ram.rows,payload:p,idByTicker});assert.deepEqual(comp.groups.map(g=>g[0]),['manufacturing_industrial_tech','services_software_health']);assert.ok(Math.abs(comp.unknown-0.2)<1e-12);
 const card=api.industryCard({locale:'ko-KR',ram,payload:p,idByTicker});assert.match(card,/data-industry="nodata"/);assert.match(card,/50\.0%/);
 const catalog={themes:[{theme_id:'semi_equipment',label:'반도체 장비',label_en:'Semiconductor equipment'},{theme_id:'ai_semi',label:'AI·반도체',label_en:'AI and semiconductors'},{theme_id:'big_tech',label:'Big Tech',label_en:'Big Tech'}]};
 const html=api.concentrationBlock({locale:'ko-KR',ram,payload:p,catalog,idByTicker});
 // NVDA 0.5 is in semiconductors and AI; hanmi (0.2) has no exact identifier -> unknown, not 0.
 assert.match(html,/data-concentration-warning="semiconductors"[^>]*>쏠림 경고 · 반도체 50\.0% &gt; 40% · v0 기본값/);
 assert.match(html,/data-concentration-scope="target"[\s\S]*data-concentration-warning="ai_semi"/);
 assert.doesNotMatch(html,/data-concentration-warning="big_tech"/);assert.match(html,/data-concentration-indeterminate="cybersecurity"|data-concentration-indeterminate/);
 const empty=api.concentrationBlock({locale:'ko-KR',ram:{state:'NOT_AVAILABLE',reason:'NO_ACTUAL',rows:[],themes:[]},payload:p,catalog,idByTicker});
 assert.match(empty,/NOT_AVAILABLE/);assert.doesNotMatch(empty,/data-concentration-warning/);
});
