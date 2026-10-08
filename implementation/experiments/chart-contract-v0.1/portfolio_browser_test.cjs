const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');

// Independent expectations from the user-owned TARGET v0 file, not the adapter.
const sourceSha256='a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b';
const declaredClock='2026-10-08T20:37:00+09:00',utcClock='2026-10-08T11:37:00Z';
const sourceGroups=[
 ['semi_equipment','반도체 장비',3000,[
  ['ASML Holding','ASML',900],['Lam Research','LRCX',600],['KLA Corporation','KLAC',550],
  ['Tokyo Electron','8035',500,'USER_DECIDED: TSE (Tokyo, 8035)'],
  ['한미반도체','042700',450,'USER_DECIDED: KRX (042700)']]],
 ['ai_semi','AI·반도체',2500,[
  ['NVIDIA','NVDA',800],['Advanced Micro Devices','AMD',500],['Broadcom','AVGO',500],
  ['Qualcomm','QCOM',400],['Intel','INTC',300]]],
 ['big_tech','Big Tech',2000,[
  ['Microsoft','MSFT',700],['Alphabet','GOOGL',700,'USER_DECIDED: Class A (GOOGL)'],['Amazon','AMZN',600]]],
 ['other_industrial','기타산업',2500,[
  ['RTX Corporation','RTX',600],['Stryker','SYK',550],['Eaton','ETN',500],
  ['Hubbell','HUBB',350],['GE Vernova','GEV',300],['Rockwell Automation','ROK',200]]],
];
const expectedRows=sourceGroups.flatMap(([theme_id,theme_label,,holdings],themeIndex)=>holdings.map(([label,ticker_hint,weight_units,listing='UNRESOLVED_BY_AGENT'],holdingIndex)=>({
 source_pointer:`/themes/${themeIndex}/holdings/${holdingIndex}`,label,ticker_hint,listing,weight_units,theme_id,theme_label,security_id:null,
})));

async function actualIsWithheld(page){
 await page.locator('#portfolio-actual').click();
 assert.equal(await page.evaluate(()=>__portfolioLab.mode),'actual');
 assert.equal(await page.evaluate(()=>__portfolioLab.doc),null,'ACTUAL must not acquire the current TARGET or fictional DEMO document');
 assert.equal(await page.locator('#portfolio-charts').getAttribute('data-state'),'NOT_AVAILABLE');
 assert.equal(await page.locator('#portfolio-charts').getAttribute('data-basis'),'ACTUAL');
 assert.match(await page.locator('#portfolio-state').innerText(),/ACTUAL.*NOT_AVAILABLE/);
 assert.match(await page.locator('#portfolio-meta').innerText(),/denominator.*NOT_AVAILABLE/);
 assert.equal(await page.locator('#portfolio-charts svg').count(),0);
 assert.equal(await page.locator('#portfolio-charts table').count(),0,'stale TARGET holdings must be cleared');
 for(const dimension of ['GICS','STRATEGY_THEME','INVESTMENT_TYPE','TYPE_OVERLAP']){
  const card=page.locator(`[data-dimension="${dimension}"]`);
  assert.equal(await card.getAttribute('data-availability'),'NOT_AVAILABLE');
  assert.match(await card.innerText(),/NOT_AVAILABLE/);
 }
}

const invalidSourceEnvelopes=['metadata absent','metadata empty','source rows reversed','source row missing','source row disagrees with holding','fake source hash','fabricated admitted mapping','changed ticker hint','changed USER listing','changed theme_id','conserved total with inconsistent Theme subtotals','fabricated known overlap'];
async function invalidSourceIsWithheld(page,original,name){
 try{
  await page.evaluate(({original,name})=>{
   const candidate=JSON.parse(JSON.stringify(original));
   if(name==='metadata absent')delete candidate.source_metadata;
   else if(name==='metadata empty')candidate.source_metadata={};
   else if(name==='source rows reversed')candidate.source_metadata.source_rows.reverse();
   else if(name==='source row missing')candidate.source_metadata.source_rows.pop();
   else if(name==='source row disagrees with holding')candidate.source_metadata.source_rows[0].label='Microsoft';
   else if(name==='fake source hash')candidate.source_metadata.source_sha256='0'.repeat(64);
   else if(name==='fabricated admitted mapping')candidate.source_metadata.mapping={admitted:19,unresolved:0,total:19};
   else if(name==='changed ticker hint')candidate.source_metadata.source_rows[0].ticker_hint='MSFT';
   else if(name==='changed USER listing')candidate.source_metadata.source_rows[3].listing='USER_DECIDED: ADR (TOELY)';
   else if(name==='changed theme_id')candidate.source_metadata.source_rows[0].theme_id='big_tech';
   else if(name==='conserved total with inconsistent Theme subtotals'){
    candidate.source_metadata.themes[0].target_units+=100;candidate.source_metadata.themes[1].target_units-=100;
    candidate.industry.buckets.find(b=>b.label==='반도체 장비').units+=100;
    candidate.industry.buckets.find(b=>b.label==='AI·반도체').units-=100;
   }
   else if(name==='fabricated known overlap')candidate.overlap.buckets=candidate.overlap.buckets.map(b=>b.kind==='UNKNOWN'?{kind:'MEMBERSHIP',types:['Growth'],units:10000}:b);
   PORTFOLIO_CHARTS.reference=candidate;__portfolioLab.render('reference');
  },{original,name});
  assert.equal(await page.locator('#portfolio-charts').getAttribute('data-state'),'BLOCKED',`${name}: invalid source metadata must be rejected before displaying an allocation`);
  assert.equal(await page.evaluate(()=>__portfolioLab.doc),null,`${name}: no invalid or previous TARGET document`);
  assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);
  assert.equal(await page.locator('#portfolio-charts svg').count(),0,`${name}: no partial or stale allocation chart`);
  assert.equal(await page.locator('#portfolio-charts table').count(),0,`${name}: no mismatched or stale source rows`);
  assert(!(await page.locator('#portfolio-charts').innerText()).includes('ASML Holding'),`${name}: previous holding label cleared`);
  assert(!(await page.locator('#portfolio-meta').innerText()).includes(sourceSha256),`${name}: previous source hash cleared`);
 }finally{
  await page.evaluate(original=>{PORTFOLIO_CHARTS.reference=JSON.parse(JSON.stringify(original));__portfolioLab.render('reference');},original);
 }
 assert.equal(await page.evaluate(()=>__portfolioLab.doc.source_metadata.source_sha256),sourceSha256,`${name}: valid original source can be restored`);
 assert.equal(await page.locator('#portfolio-charts').getAttribute('data-state'),'REFERENCE');
 assert.equal(await page.locator('#portfolio-charts table tbody tr').count(),19);
 assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),1);
}

async function unexpectedDemoSourceIsWithheld(page,original){
 try{
  await page.evaluate(original=>{
   const candidate=JSON.parse(JSON.stringify(original));candidate.source_metadata={};
   PORTFOLIO_CHARTS.demo=candidate;__portfolioLab.render('demo');
  },original);
  assert.equal(await page.locator('#portfolio-charts').getAttribute('data-state'),'BLOCKED','DEMO must reject an unexpected source_metadata envelope');
  assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
  assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);
  assert.equal(await page.locator('#portfolio-charts svg').count(),0);
  assert.equal(await page.locator('#portfolio-charts table').count(),0);
  assert(!(await page.locator('#portfolio-charts').innerText()).includes('Fictional A'),'previous fictional holdings cleared');
  assert(!(await page.locator('#portfolio-meta').innerText()).includes(sourceSha256));
 }finally{
  await page.evaluate(original=>{PORTFOLIO_CHARTS.demo=JSON.parse(JSON.stringify(original));__portfolioLab.render('demo');},original);
 }
 assert.equal(await page.evaluate(()=>__portfolioLab.doc.data_state),'DEMO','valid fictional fixture restored');
 assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),3);
 assert.equal(await page.locator('#portfolio-charts table tbody tr').count(),original.holdings.length);
}

const invalidModeSlots=['DEMO in reference slot','reference disguised as DEMO in reference slot','reference in DEMO slot'];
async function invalidModeSlotIsWithheld(page,reference,demo,name){
 try{
  await page.evaluate(({reference,demo,name})=>{
   const clone=value=>JSON.parse(JSON.stringify(value));
   PORTFOLIO_CHARTS.reference=clone(reference);PORTFOLIO_CHARTS.demo=clone(demo);
   let key='reference';
   if(name==='DEMO in reference slot')PORTFOLIO_CHARTS.reference=clone(demo);
   else if(name==='reference disguised as DEMO in reference slot'){
    const candidate=clone(reference);candidate.data_state='DEMO';candidate.data_kind='SYNTHETIC_FIXTURE';delete candidate.source_metadata;
    PORTFOLIO_CHARTS.reference=candidate;
   }else{PORTFOLIO_CHARTS.demo=clone(reference);key='demo';}
   __portfolioLab.render(key);
  },{reference,demo,name});
  assert.equal(await page.locator('#portfolio-charts').getAttribute('data-state'),'BLOCKED',`${name}: selected mode must match its permitted payload`);
  assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
  assert.equal(await page.locator('#portfolio-charts svg').count(),0);
  assert.equal(await page.locator('#portfolio-charts table').count(),0);
  assert.match(await page.locator('#portfolio-heading').innerText(),/BLOCKED/);
  assert.match(await page.locator('#portfolio-source-tag').innerText(),/BLOCKED/);
  assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);
  assert(!(await page.locator('#portfolio-charts').innerText()).includes('ASML Holding'));
  assert(!(await page.locator('#portfolio-charts').innerText()).includes('Fictional A'));
 }finally{
  await page.evaluate(({reference,demo})=>{
   PORTFOLIO_CHARTS.reference=JSON.parse(JSON.stringify(reference));PORTFOLIO_CHARTS.demo=JSON.parse(JSON.stringify(demo));
   __portfolioLab.render('reference');
  },{reference,demo});
 }
 assert.equal(await page.evaluate(()=>__portfolioLab.doc.data_state),'REFERENCE');
 assert.equal(await page.evaluate(()=>__portfolioLab.doc.holdings.length),19);
 assert.equal(await page.locator('#portfolio-charts table tbody tr').count(),19);
 assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),1);
 await page.locator('#portfolio-demo').click();
 assert.equal(await page.evaluate(()=>__portfolioLab.doc.data_state),'DEMO');
 assert.equal(await page.evaluate(()=>__portfolioLab.doc.holdings.length),4);
 assert.equal(await page.locator('#portfolio-charts table tbody tr').count(),4);
 assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),3);
}

(async()=>{
 let launch={headless:true,args:['--no-sandbox']};
 if(process.env.CHART_CHROMIUM_PATH)launch.executablePath=process.env.CHART_CHROMIUM_PATH;
 if(process.env.CHART_CHROMIUM_MODULE){const binary=(await import(process.env.CHART_CHROMIUM_MODULE)).default;launch.executablePath=await binary.executablePath();}
 const browser=await chromium.launch(launch);const results=[];fs.mkdirSync('browser-results',{recursive:true});
 try{
  for(const [width,locale] of [[360,'ko'],[390,'ko'],[390,'en'],[1280,'ko']]){
   const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   const url=new URL(process.env.CHART_DEMO_URL||'file://'+path.resolve(process.env.CHART_DEMO_FILE||'dist/index.html'));url.searchParams.set('lang',locale);
   await page.goto(url.href);
   await page.evaluate(async lang=>{document.documentElement.lang=lang;__portfolioLab.render('reference');await document.fonts.ready;},locale);
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   assert.equal(new URL(page.url()).searchParams.get('lang'),locale);
   const ref=await page.evaluate(()=>__portfolioLab.doc);
   assert.equal(ref.data_state,'REFERENCE');assert.equal(ref.weight_basis,'TARGET');assert.equal(ref.holdings.length,19);
   assert(ref.source_metadata,'default portfolio must come from the adopted user TARGET v0, not the historical reference fixture');
   const metadata=ref.source_metadata;
   assert.equal(metadata.source_sha256,sourceSha256);assert.equal(metadata.version,'v0');assert.equal(metadata.owner,'USER');
   assert.deepEqual(metadata.declared_clocks,{effective_at:declaredClock,available_at:declaredClock,adopted_at:declaredClock});
   for(const name of ['effective_at_utc','available_at_utc','adopted_at_utc'])assert.equal(metadata[name],utcClock);
   assert.deepEqual(metadata.mapping,{admitted:0,unresolved:19,total:19});
   assert.deepEqual(metadata.source_rows,expectedRows,'all original labels, hints, listing choices, units and Theme memberships must survive');
   assert.equal(ref.total_units,10000);assert.equal(ref.cash_units,0);
   assert.deepEqual(ref.holdings.map(h=>[h.holding_id,h.label,h.weight_units,h.industry,h.security_id,h.types]),
    expectedRows.map(r=>[r.source_pointer,r.label,r.weight_units,r.theme_label,null,null]));
   assert.deepEqual(ref.industry.buckets.filter(b=>b.kind==='INDUSTRY').map(b=>[b.label,b.units]).sort(),
    sourceGroups.map(([,label,units])=>[label,units]).sort());
   assert.deepEqual(ref.types.exposures,[]);assert.equal(ref.publication_grant,null);assert.equal(ref.pit_status,'NOT_VERIFIED');
   const state=await page.locator('#portfolio-state').innerText(),meta=await page.locator('#portfolio-meta').innerText();
   assert.match(state,/REFERENCE/);assert.match(state,/TARGET v0.*USER/);assert.doesNotMatch(state,/SAMPLE/);
   const heading=await page.locator('#portfolio > h2').innerText();assert.match(heading,/TARGET v0.*USER/);assert.doesNotMatch(heading,/SAMPLE/);
   assert(meta.includes(sourceSha256),'the displayed metadata must identify the exact user source bytes');
   assert(meta.includes(utcClock),'current source clocks must be visible');assert.match(meta,/0\s*\/\s*19/);
   assert.match(meta,/effective_at/);assert.match(meta,/available_at/);assert.match(meta,/adopted_at/);
   if(locale==='en')assert.doesNotMatch(meta,/미제공|효력|현금|미분류|관측|추출/,'English metadata must use the selected portfolio locale');
   for(const dimension of ['GICS','INVESTMENT_TYPE','TYPE_OVERLAP']){
    const card=page.locator(`[data-dimension="${dimension}"]`);
    assert.equal(await card.getAttribute('data-availability'),'NOT_AVAILABLE');assert.match(await card.innerText(),/NOT_AVAILABLE/);
    assert.equal(await card.locator('svg').count(),0);
   }
   assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),1,'only the supplied Strategy Theme allocation is renderable');
   await page.locator('#portfolio-charts details').first().locator('summary').click();
   const tableRows=page.locator('#portfolio-charts table tbody tr');assert.equal(await tableRows.count(),19);
   for(const [index,row]of expectedRows.entries()){
    const cells=await tableRows.nth(index).locator('td').allTextContents();
    assert.deepEqual(cells.slice(0,3),[row.label,`${row.weight_units/100}%`,row.theme_label]);
    assert((await tableRows.nth(index).innerText()).includes(row.ticker_hint));
    assert((await tableRows.nth(index).innerText()).includes(row.listing));
   }
   if(width===390)await page.locator('#portfolio').screenshot({path:`browser-results/portfolio-target-${width}-${locale}.png`});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await actualIsWithheld(page);
   if(width===390)await page.locator('#portfolio').screenshot({path:`browser-results/portfolio-actual-${width}-${locale}.png`});
   await page.locator('#portfolio-demo').click();const demo=await page.evaluate(()=>__portfolioLab.doc);
   assert.equal(demo.data_state,'DEMO');assert.equal(demo.types.exposures.reduce((n,e)=>n+e.member_units,0),105);
   assert(demo.types.exposures.every(e=>e.member_units+e.non_member_units+e.unknown_units+e.cash_units===100));
   assert.equal(demo.cash_units,10);assert.equal(demo.overlap.buckets.find(b=>b.kind==='UNKNOWN').units,10);
   assert.equal(demo.overlap.buckets.reduce((n,b)=>n+b.units,0),100);
   assert.match(await page.locator('#portfolio-charts').innerText(),/Growth 65% 하한\(최소\) \/ Quality 40% 하한\(최소\)/);
   assert.match(await page.locator('#portfolio-charts').innerText(),/\[Growth\] \+ \[Quality\]/);
   assert.match(await page.locator('#portfolio-state').innerText(),/가상 기업/);
   assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),3);
   await page.locator('#portfolio').screenshot({path:`browser-results/portfolio-${width}${locale==='en'?'-en':''}.png`});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await unexpectedDemoSourceIsWithheld(page,demo);assert.deepEqual(errors,[],'unexpected DEMO metadata must be withheld without a page error');
   for(const name of invalidModeSlots){
    await invalidModeSlotIsWithheld(page,ref,demo,name);assert.deepEqual(errors,[],`${name}: rejected mode substitution must not produce a page error`);
   }
   await actualIsWithheld(page);
   assert.equal(await page.locator('.inventory-row').count(),113);
   await page.locator('#inventory-search').fill('RSI');assert.equal(await page.locator('.inventory-row').count(),1);
   await page.locator('.inventory-row summary').click();assert.match(await page.locator('.inventory-row').innerText(),/L1 원본/);
   await page.locator('#inventory-search').fill('');await page.locator('#inventory-group').selectOption('K');assert.equal(await page.locator('.inventory-row').count(),8);
   await page.locator('#inventory-group').selectOption('');assert.equal(await page.locator('.inventory-row').count(),113);
   await page.locator('#portfolio-reference').click();assert.equal(await page.evaluate(()=>__portfolioLab.mode),'reference');
   assert.equal(await page.evaluate(()=>__portfolioLab.doc.source_metadata.source_sha256),sourceSha256);
   for(const name of invalidSourceEnvelopes){
    await invalidSourceIsWithheld(page,ref,name);
    assert.deepEqual(errors,[],`${name}: malformed metadata must be withheld without a page error`);
   }
   // A serialized observed-data payload cannot acquire display eligibility by a mode switch.
   await page.evaluate(()=>{PORTFOLIO_CHARTS.demo.data_state='NOT_AVAILABLE';__portfolioLab.render('demo');});
   assert.match(await page.locator('#portfolio-charts').innerText(),/BLOCKED/);assert.equal(await page.locator('#portfolio-charts svg').count(),0);assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
   await page.locator('#portfolio-reference').click();assert.equal(await page.evaluate(()=>__portfolioLab.doc.source_metadata.source_sha256),sourceSha256);
   await page.evaluate(()=>{PORTFOLIO_CHARTS.reference.data_state='NOT_AVAILABLE';__portfolioLab.render('reference');});
   assert.match(await page.locator('#portfolio-charts').innerText(),/BLOCKED/);assert.equal(await page.locator('#portfolio-charts svg').count(),0);assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
   assert.equal(await page.locator('#portfolio-charts table').count(),0);assert(!(await page.locator('#portfolio-charts').innerText()).includes('ASML Holding'));
   assert(!(await page.locator('#portfolio-meta').innerText()).includes(sourceSha256),'blocked source must clear previous displayed metadata');
   assert.deepEqual(errors,[]);results.push({width,locale,result:'PASS',source_sha256:sourceSha256,mapping:{admitted:0,unresolved:19},source_envelope_rejections:invalidSourceEnvelopes,mode_slot_rejections:invalidModeSlots,checks:['user-source-hash-and-declared-current-clocks','exact-19-label-unit-theme-and-listing-choices','visible-source-rows-and-zero-mapping','no-inferred-types-or-security','GICS-type-overlap-unavailable','ACTUAL-null-zero-SVG-after-TARGET-and-DEMO','fictional-105-percent','unknown-cash-denominator','exact-set-partition','three-SVGs','scope-labels','inventory-113-search-filter','reference-restores-TARGET-v0','invalid-source-envelope-blocked-and-original-restored','unexpected-DEMO-source-metadata-blocked-and-original-restored','mode-slot-payload-binding-and-both-original-slots-restored','observed-demo-blocked','blocked-clears-stale-TARGET','no-overflow','no-page-errors']});await page.close();
  }
  fs.writeFileSync('browser-results/portfolio-results.json',JSON.stringify({scope:'USER_TARGET_V0_REFERENCE_AND_FICTIONAL_PORTFOLIO_NO_ACTUAL',results},null,2));console.log(JSON.stringify(results));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
