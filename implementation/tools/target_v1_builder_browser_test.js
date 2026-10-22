'use strict';
// TARGET v1 builder screen (owner decision 2026-10-14) at 390 and 1280: empty public screens → builder disabled (NA, no 0-fill);
// a synthetic device draft → 30-candidate table, 15 cards, 동의 / 반대(reason required, automatic replacement, limits re-check) /
// 모름(미확인), judgement records in the playbook store, final save blocked by number_check_passed, then (config override) TARGET v1
// saved + set C start, the rebalance-week view (1/3 per round, amounts hidden), the A/B/C/S&P 500 comparison and the round-3
// review suggestion. Every request is intercepted: public screens are the empty fixtures, the Worker is stubbed, anything else
// is aborted and counted. No horizontal page scroll; no buy/sell verbs on the builder.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {routeEmptyPublicScreens}=require('./empty_public_screens');
const BASE=process.env.PAGES_COCKPIT_URL||'http://127.0.0.1:8990/';
const WORKER='https://private-investment-history.kco994553.workers.dev';

// Synthetic v2 accessor rows + public records → a draft through the shipped builder (runs in the page).
function seed({date}){
 const B=window.TargetV1Builder,S=window.TargetV1Screen,SICS=['7372','3674','3559','3612','3812','3823','2834','5812','4911','1311','2080','6798'];
 const F={q_profitability:90,q_moat_proxy:80,q_earnings_quality:70,q_financial_safety:60,q_capital_allocation:50,g_revenue_growth:85,g_per_share_growth:40,g_growth_efficiency:30,g_consistency:20,g_recent_acceleration:10};
 const M={roic:0.25,moat_return_mean_5y:0.2,fcf_to_net_income:1.1,net_debt_to_ebitda:1,interest_coverage:12,revenue_cagr_3y:0.12};
 const computed={v2_state:'READY',profile:{id:'qgv-v2/balanced/gate-on'},v2_as_of:date,rows:{}},inputs={records:{}},codes=[];
 for(let i=0;i<45;i++){const symbol=i===3?'NVDA':'SYN'+String(i).padStart(2,'0'),code='NASDAQ:'+symbol,ax=s=>({score:s,weight_available:1});codes.push(code);
  computed.rows['c'+i]={ticker:symbol,code,v2:{total:90-i*0.5,q:70,g:65,v:55,axes:{Q:ax(70),G:ax(65),V:ax(55)},factors:Object.fromEntries(Object.entries(F).map(([k,v])=>[k,{score:v}])),factors_available:i%7===0?11:15,factors_total:15,q_industry_percentile:60,value_trap_gate:i===44,selected_types:['quality']}};
  inputs.records[code]={cik:'C'+i,sic:i===3?'3674':SICS[i%SICS.length],industry_group:'grp'+(i%SICS.length),metrics:M,qg_axes:{Q:{score:70},G:{score:65}}};}
 const draft=B.buildDraft({computed,inputs,universeCodes:codes,existing:['NVDA'],date});
 const state={...B.emptyState(),draft,set_b:[{date,rows:draft.pool.slice(0,15).map(r=>({symbol:r.symbol,pct:100/15,subgroup:r.subgroup})),cash_pct:0,limits_ok:true}]};
 S.writeState(window.PlaybookScreen,localStorage,state);return draft.pool.length;
}
(async()=>{
 const browser=await chromium.launch({headless:true});let phase='start';
 try{for(const width of [390,1280]){
  phase=width+' setup';const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),unexpected=[];
  await routeEmptyPublicScreens(context);
  await context.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin===new URL(BASE).origin)return route.fallback();if(url.origin===WORKER)return route.fulfill({status:503,contentType:'application/json',body:'{"error":"UNAVAILABLE"}'});unexpected.push(url.origin);return route.abort();});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE+'#playbook');await page.locator('[data-tv1-builder]').waitFor();
  phase=width+' empty';assert.equal(await page.locator('[data-tv1-build]').isDisabled(),true);assert.match(await page.locator('[data-tv1-readiness]').textContent(),/^NA · QGV v2 총점에는 V가 필요/);
  assert.match(await page.locator('[data-tv1-coverage]').textContent(),/초안 · 커버리지 편향 가능 \(Q 0\/504, G 0\/504\)/);assert.equal(await page.locator('[data-tv1-card]').count(),0);
  phase=width+' draft';const pool=await page.evaluate(seed,{date:'2026-10-14'});assert.ok(pool>=30);
  await page.goto(BASE+'#home');await page.goto(BASE+'#playbook');await page.locator('[data-tv1-candidates]').waitFor();
  assert.equal(await page.locator('[data-tv1-candidates] tbody tr').count(),30);assert.match(await page.locator('[data-tv1-candidate=NVDA]').textContent(),/반도체.*예$/);
  assert.equal(await page.locator('[data-tv1-card]').count(),15);assert.match(await page.locator('[data-tv1-limits]').textContent(),/16절 한도 통과/);
  const cards=await page.locator('[data-tv1-card]').evaluateAll(n=>n.map(x=>x.dataset.tv1Card));
  const card=s=>page.locator('[data-tv1-card="'+s+'"]');
  assert.equal(await card(cards[0]).locator('h4 + ol li').first().count(),1);assert.equal(await card(cards[0]).locator('ol').nth(1).locator('li').count(),3);
  assert.match(await card(cards[0]).locator('ol').nth(1).textContent(),/ROIC가 17\.5% 아래로 내려가면/);
  phase=width+' answers';await card(cards[0]).locator('[data-tv1-answer=AGREE]').click();await page.waitForFunction(s=>document.querySelector('[data-tv1-status]').textContent.includes('동의 · '+s),cards[0]);
  await card(cards[1]).locator('[data-tv1-answer=DISAGREE]').click();assert.match(await page.locator('[data-tv1-status]').textContent(),/반대 이유를 한 줄로/);assert.equal(await card(cards[1]).count(),1);
  await card(cards[1]).locator('[data-tv1-reason]').fill('합성 · 사업 이해 부족');await card(cards[1]).locator('[data-tv1-answer=DISAGREE]').click();
  await page.waitForFunction(s=>!document.querySelector('[data-tv1-card="'+s+'"]'),cards[1]);assert.equal(await page.locator('[data-tv1-card]').count(),15);
  assert.match(await page.locator('[data-tv1-status]').textContent(),new RegExp('반대 · '+cards[1]+' 제외 → \\S+ 추가 · 16절 한도 통과'));assert.match(await page.locator('[data-tv1-rejected]').textContent(),new RegExp(cards[1]));
  await card(cards[2]).locator('[data-tv1-answer=UNKNOWN]').click();await page.waitForFunction(s=>/모름 · 미확인/.test(document.querySelector('[data-tv1-card="'+s+'"] [data-tv1-card-state]').textContent),cards[2]);
  for(;;){const pending=await page.locator('[data-tv1-card]').evaluateAll(n=>n.filter(x=>x.querySelector('[data-tv1-card-state]').textContent==='응답 대기').map(x=>x.dataset.tv1Card));if(!pending.length)break;await card(pending[0]).locator('[data-tv1-answer=AGREE]').click();await page.waitForFunction(s=>document.querySelector('[data-tv1-card="'+s+'"] [data-tv1-card-state]').textContent!=='응답 대기',pending[0]);}
  phase=width+' number check';assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(),false);assert.match(await page.locator('[data-tv1-number-check]').textContent(),/숫자 검증\(10-K 대조\) 통과 전/);
  await page.locator('[data-tv1-finalize]').click();assert.match(await page.locator('[data-tv1-status]').textContent(),/숫자 검증\(10-K 대조\) 통과 전에는 TARGET v1을 확정 저장할 수 없습니다/);
  const store=await page.evaluate(()=>{const v=PlaybookScreen.read(localStorage);return{records:v.records.filter(r=>r.primary_code==='TV1').map(r=>r.verdict),versions:v.target_v1.versions.length};});
  assert.equal(store.versions,0);assert.equal(store.records.length,16);assert.equal(store.records.filter(v=>v==='TV1_DISAGREE').length,1);assert.equal(store.records.filter(v=>v==='TV1_UNKNOWN').length,1);
  await page.goto(BASE+'#home');await page.goto(BASE+'#playbook');await page.locator('[data-tv1-confirm]').waitFor();assert.match(await page.locator('[data-playbook-scoring]').textContent(),/TARGET v1 반대/);
  phase=width+' finalize';await page.evaluate(async c=>{const catalog=await(await fetch('actual-catalog.json')).json(),rows=catalog.instruments.map((r,i)=>({ticker:r.ticker,weight:r.target_units/catalog.total_units+(i%2?0.001:-0.001)}));
   await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,config:{...TargetV1ConfigDefaults,number_check_passed:true},catalog,storage:localStorage,date:'2026-10-14',ram:{state:'AVAILABLE',total:100000000,rows}});},null);
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>/TARGET v1 저장 · 세트 C 2026-10-14 시작/.test(document.querySelector('[data-tv1-status]').textContent));
  assert.match(await page.locator('[data-tv1-set-c]').textContent(),/시작 2026-10-14 · v1/);assert.match(await page.locator('[data-tv1-version]').textContent(),/v1 · 2026-10-14/);
  phase=width+' rebalance';const reb=page.locator('[data-tv1-rebalance]');assert.match(await reb.locator('h2').textContent(),/1회차 2026-11-16 주/);
  assert.ok(await reb.locator('tbody tr').count()>=15);const first=await reb.locator('tbody tr').first().locator('td').allTextContents();assert.equal(first.length,6);assert.match(first[3],/^[+−]?\d+\.\d\d%p$/);assert.equal(first[5],'●●●만원');
  const nvda=await reb.locator('[data-tv1-rebalance-row=NVDA] td').allTextContents();assert.match(nvda[1],/%$/);
  await reb.locator('[data-tv1-round="3"]').click();assert.match(await page.locator('[data-tv1-rebalance] h2').textContent(),/3회차 2027-05-17 주/);
  phase=width+' compare';await page.evaluate(async()=>{const catalog=await(await fetch('actual-catalog.json')).json();
   // Synthetic closes (RAM, in the page): S&P 500 and the other A names up, B and C names down.
   const provider=async(symbols,from)=>{const out={},days=[];for(let d=new Date(from+'T00:00:00Z');d<=new Date('2027-04-01T00:00:00Z');d.setUTCDate(d.getUTCDate()+1))if(d.getUTCDay()%6)days.push(d.toISOString().slice(0,10));
    const st=TargetV1Screen.readState(PlaybookScreen,localStorage),down=new Set([...(st.versions.at(-1)?.rows||[]).map(r=>r.symbol),...st.set_b.flatMap(x=>x.rows.map(r=>r.symbol))]);
    for(const sym of symbols){const slope=sym==='SPY'?0.001:down.has(sym)?-0.001:0.002;out[sym]=Object.fromEntries(days.map((d,i)=>[d,100*(1+slope*i)]));}return out;};
   await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,catalog,storage:localStorage,date:'2027-04-01',closesProvider:provider});});
  await page.locator('[data-tv1-load-compare]').click();await page.waitForFunction(()=>document.querySelectorAll('[data-tv1-compare-row] td')[1]?.textContent!=='NA');
  const cmp=await page.locator('[data-tv1-compare-row]').evaluateAll(n=>n.map(x=>x.querySelectorAll('td')[1].textContent));assert.equal(cmp.length,4);assert.ok(cmp.every(v=>/^[+−]\d/.test(v)),cmp.join(','));
  assert.match(await page.locator('[data-tv1-review]').textContent(),/^제안 · 세트 B와 세트 C가 모두 세트 A와 S&P 500보다 낮습니다/);
  phase=width+' layout';const text=await page.locator('[data-target-v1-builder]').textContent();assert.ok(!/매수|매도|사세요|파세요|\bbuy\b|\bsell\b/i.test(text),'buy/sell wording');
  await page.locator('[data-tv1-raw] summary').click();assert.match(await page.locator('[data-tv1-raw]').textContent(),/무효화 지표/);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow');
  await page.screenshot({path:(process.env.TV1_SHOT_DIR||'/tmp')+'/target-v1-builder-'+width+'.png',fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);
  console.log('PASS TARGET v1 builder empty NA, cards agree/disagree(replace)/unknown, records, number-check gate, finalize, rebalance week, compare and review rule '+width);
  await context.close();}}
 catch(e){console.log('FAIL '+phase+' '+e.message);process.exitCode=1;}finally{await browser.close();}
})();
