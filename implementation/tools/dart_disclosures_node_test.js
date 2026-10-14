'use strict';/* dart-disclosures.js must reach the same verdicts as Python product/dart_public on the shared synthetic vectors. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const reader=require('../src/investment_system/product/web_assets/dart-disclosures.js');
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/dart_public_vectors_v1.json'),'utf8'));
let pass=0,fail=0;async function test(name,f){try{await f();pass++;console.log('PASS '+name);}catch(e){fail++;console.log('FAIL '+name+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}}
const live=vectors.cases.find(c=>c.name==='live').payload;
(async()=>{
 await test('title rules match Python ('+vectors.titles.length+')',()=>{assert.equal(vectors.synthetic,true);for(const t of vectors.titles){assert.equal(reader.validTitle(t.title),t.valid,t.title);if(!t.valid)continue;assert.equal(reader.family(t.title),t.family);assert.equal(reader.amended(t.title),t.amended);
  for(const[k,v]of Object.entries(t.classes))assert.equal(reader.classify(t.title,k==='None'?null:k),v);}});
 await test('payload verdicts match Python ('+vectors.cases.length+')',()=>{assert.ok(vectors.cases.length>=30);for(const c of vectors.cases){let ok=true;try{reader.validate(JSON.parse(JSON.stringify(c.payload)));}catch(e){ok=false;assert.equal(e.message,'DART_PUBLIC_INVALID');}assert.equal(ok,c.valid,c.name);}});
 await test('timeline rows use the SEC 8-K row shape with source DART and KST day ordering',()=>{const rows=reader.timeline(live);assert.equal(rows.length,live.events.length);for(const r of rows){assert.deepEqual(Object.keys(r).sort(),['channel','company_id','event','source','time']);assert.equal(r.channel,'DISCLOSURE');assert.equal(r.source,'DART');assert.match(r.time,/^\d{4}-\d{2}-\d{2}T15:00:00\+00:00$/);}
  assert.equal(reader.timeline(live,{companyIds:['nvda']}).length,0);const results=live.events.filter(e=>e.classification==='RESULTS');assert.equal(results.length,1);assert.equal(reader.classLabel('RESULTS',false),'실적(잠정실적 공정공시) (Results (preliminary earnings))');});
 await test('records carry title, link, date and classification only (no body, filer or price)',()=>{const text=JSON.stringify(live);for(const word of ['SYNTHETIC FILER','flr_nm','body','price','summary'])assert.ok(!text.includes(word),word);for(const e of live.events)assert.ok(e.link.startsWith('https://dart.fss.or.kr/dsaf001/main.do?rcpNo='));});
 await test('loader: 404 or invalid file -> null, valid -> payload, no storage writes',async()=>{const view=(status,body)=>({fetch:async(name,opt)=>{assert.equal(name,'dart-disclosures.json');assert.equal(opt.cache,'no-store');assert.equal(opt.credentials,'omit');assert.equal(opt.redirect,'error');return{status,ok:status===200,text:async()=>body};}});
  assert.equal(await reader.load(view(404,'')),null);assert.equal(await reader.load(view(200,'{"price":1}')),null);assert.deepEqual(await reader.load(view(200,JSON.stringify(live))),live);});
 await test('DART v2 reference excludes target rows and enforces complete metric keys',()=>{const engine=require('../src/investment_system/product/web_assets/sec-qgv2.js');
  const metrics=Object.fromEntries(engine.METRIC_KEYS.map(k=>[k,0.1])),block={state:'LIVE',reference_only:true,comparison_label:'참고 순위',comparison_basis:'US_UNIVERSE_504_GENERAL',industry_basis:'NOT_ASSIGNED',currency:'KRW',reason_codes:[],metrics};
  const payload={companies:{hanmi:{state:'LIVE',qgv2:block}}},universe={};for(let i=1;i<=9;i++)universe['US'+i]={cik:String(i),state:'LIVE',profile:'GENERAL',industry_group:null,metrics:{...metrics}};
  universe.TARGET={cik:'999',state:'LIVE',profile:'GENERAL',industry_group:null,metrics:{...metrics},in_cross_section:false};
  const before=JSON.stringify(universe),result=reader.qgv2Reference(payload,universe,engine);assert.equal(result.cross_section_size,9);assert.equal(result.reference_only,true);assert.equal(result.axes.Q.available_weight,100);assert.equal(JSON.stringify(universe),before);
  delete block.metrics.roic;assert.throws(()=>reader.qgv2Reference(payload,universe,engine));
 });
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
