'use strict';
// TARGET v1 builder screen (owner decision 2026-10-14) at 390 and 1280: empty public screens → builder disabled (NA, no 0-fill);
// a synthetic device draft → 30-candidate table, 15 cards, 동의 / 반대(reason required, automatic replacement, limits re-check) /
// 모름(미확인), judgement records in the playbook store, final save blocked until the number check of the same calc_version passed, then (config override) TARGET v1
// saved + R-C start, the rebalance-week view (1/3 per round, amounts hidden), the A / R-B / R-C (규칙 지수) / S&P 500 comparison,
// the round-3 review suggestion and the T-PRICE flow (TV1 names outside the 19 → confirm → the user's sheet → scored, else NA).
// 2026-10-15 supplement: before finalize the rebalance week is risk-code checks only (no list); finalize re-reads the published
// sec-qgv2.json at the click (404 / legacy without calc_version / number check of another calc_version all block, with every
// blocker listed) and succeeds only for the same calc_version; a name shortfall (< 15) is shown and blocks finalize.
// 2026-10-15 evening: a valued row acquired > 7 days ago blocks (all-shards run hint) whatever the file as_of; a selected name
// failing the financial-safety re-check blocks; a changed input basis regenerates the draft (same-symbol answers kept, the new
// name waits for its card). 2026-10-25 확정 차단 점검 (display only): one line above the 확정 button (today / tomorrow / kept rows)
// from the same published file the button reads (once at mount, then each click's file), the table only when a row blocks today or
// a kept row exists (KEPT row by row, ROTATION one line per shard), per-class action texts; the line agrees with the finalize check.
// Every request is intercepted: public screens are the empty fixtures, the Worker is stubbed, anything else
// is aborted and counted. No horizontal page scroll; no buy/sell verbs on the builder.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {routeEmptyPublicScreens}=require('./empty_public_screens');
const BASE=process.env.PAGES_COCKPIT_URL||'http://127.0.0.1:8990/';
const WORKER='https://private-investment-history.kco994553.workers.dev';

// Synthetic published sec-qgv2.json (raw shape) for the same 45 synthetic names + fillers to 504 (page init script).
const PAYLOAD=`window.__tv1Payload=(calc,{asOf='2026-10-13T21:00:00Z',acquired='2026-10-13T20:00:00Z',patch={}}={})=>{
 const M={roic:0.25,moat_return_mean_5y:0.2,fcf_to_net_income:1.1,net_debt_to_ebitda:1,interest_coverage:12,revenue_cagr_3y:0.12};
 const out={kind:'SEC_QGV2',as_of:asOf,shard_count:7,records:{}};if(calc)out.calc_version=calc;
 for(let i=0;i<504;i++){const code=i<45?'NASDAQ:'+(i===3?'NVDA':'SYN'+String(i).padStart(2,'0')):'NYSE:P'+i;
  out.records[code]={cik:'C'+i,state:'LIVE',reason_codes:[],acquired_at:acquired,axes:{Q:{score:50},G:{score:50}},metrics:{...M},...(calc?{calc_version:calc}:{})};}
 for(const[code,f]of Object.entries(patch))Object.assign(out.records[code],f);return out;};`;
// Synthetic v2 accessor rows + public records → a draft through the shipped builder (runs in the page); the draft records the
// input basis of the qgv2-calc/2026-10-17.1 payload.
// vMiss: {symbol: V factor id} whose synthetic score is null (2026-10-23 V count: a V without V3 / V4 blocks finalize).
async function seed({date,n=45,vMiss={}}){
 const B=window.TargetV1Builder,S=window.TargetV1Screen,SICS=['7372','3674','3559','3612','3812','3823','2834','5812','4911','1311','2080','6798'];
 const F={q_profitability:90,q_moat_proxy:80,q_earnings_quality:70,q_financial_safety:60,q_capital_allocation:50,g_revenue_growth:85,g_per_share_growth:40,g_growth_efficiency:30,g_consistency:20,g_recent_acceleration:10,
  v_earnings_yield:45,v_fcf_yield:44,v_vs_industry:43,v_vs_own_history:42,v_expectation_check:41};
 const M={roic:0.25,moat_return_mean_5y:0.2,fcf_to_net_income:1.1,net_debt_to_ebitda:1,interest_coverage:12,revenue_cagr_3y:0.12};
 const computed={v2_state:'READY',profile:{id:'qgv-v2/balanced/gate-on'},v2_as_of:date,rows:{}},inputs={records:{}},codes=[];
 for(let i=0;i<n;i++){const symbol=i===3?'NVDA':'SYN'+String(i).padStart(2,'0'),code='NASDAQ:'+symbol,ax=s=>({score:s,weight_available:1});codes.push(code);
  computed.rows['c'+i]={ticker:symbol,code,v2:{total:90-i*0.5,q:70,g:65,v:55,axes:{Q:ax(70),G:ax(65),V:ax(55)},factors:Object.fromEntries(Object.entries(F).map(([k,v])=>[k,{score:vMiss[symbol]===k?null:v}])),factors_available:i%7===0?11:15,factors_total:15,q_industry_percentile:60,value_trap_gate:i===44,selected_types:['quality']}};
  inputs.records[code]={cik:'C'+i,sic:i===3?'3674':SICS[i%SICS.length],industry_group:'grp'+(i%SICS.length),metrics:M,qg_axes:{Q:{score:70},G:{score:65}}};}
 const basis=await B.inputBasis(window.__tv1Payload('qgv2-calc/2026-10-17.1'));window.__seedData={computed,inputs,codes,basis};
 const draft=B.buildDraft({computed,inputs,universeCodes:codes,existing:['NVDA'],date,basis});
 const state={...B.emptyState(),draft,rule_b:[{date,rows:draft.pool.slice(0,15).map(r=>({symbol:r.symbol,pct:100/15,subgroup:r.subgroup})),cash_pct:0,limits_ok:true}]};
 S.writeState(window.PlaybookScreen,localStorage,state);return draft.pool.length;
}
(async()=>{
 const browser=await chromium.launch({headless:true});let phase='start';
 try{for(const width of [390,1280]){
  phase=width+' setup';const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),unexpected=[];
  await routeEmptyPublicScreens(context);
  await context.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin===new URL(BASE).origin)return route.fallback();if(url.origin===WORKER)return route.fulfill({status:503,contentType:'application/json',body:'{"error":"UNAVAILABLE"}'});unexpected.push(url.origin);return route.abort();});
  await context.addInitScript({content:PAYLOAD});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE+'#playbook');await page.locator('[data-tv1-builder]').waitFor();
  phase=width+' empty';assert.equal(await page.locator('[data-tv1-build]').isDisabled(),true);assert.match(await page.locator('[data-tv1-readiness]').textContent(),/^NA · QGV v2 총점에는 V가 필요/);
  assert.match(await page.locator('[data-tv1-coverage]').textContent(),/초안 · 커버리지 편향 가능 \(Q 0\/504, G 0\/504\)/);assert.equal(await page.locator('[data-tv1-card]').count(),0);
  phase=width+' draft';const pool=await page.evaluate(seed,{date:'2026-10-14'});assert.ok(pool>=30);
  // The shipped browser builder must recognize the actual production version, with the default gate still false.
  const versionCheck=await page.evaluate(()=>{
   const B=TargetV1Builder,pub=window.__tv1Payload('qgv2-calc/2026-10-17.1'),check=p=>B.publishedCheck(p,{date:'2026-10-14'});
   const current=check(pub);pub.records['NYSE:P200'].calc_version='qgv2-calc/2026-10-17.2';
   return{basis:window.__seedData.basis.calc_version,version:current.calc_version,reasons:current.reasons,
    invalid:check(window.__tv1Payload('other/2026-10-17.1')).reasons,mixed:check(pub).reasons,
    passed:TargetV1ConfigDefaults.number_check.result.passed,number:B.numberCheck(current.calc_version).reason};
  });
  assert.deepEqual(versionCheck,{basis:'qgv2-calc/2026-10-17.1',version:'qgv2-calc/2026-10-17.1',reasons:[],
   invalid:['CALC_VERSION_MISSING'],mixed:['CALC_VERSION_MIXED'],passed:true,number:null});
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
  phase=width+' risk only';assert.match(await page.locator('[data-tv1-risk-only]').textContent(),/^TARGET v1 미확정 · 회차별 종목 목록·예상 금액 없음 · 이번 회차는 위험 코드 점검만$/);
  assert.equal(await page.locator('[data-tv1-rebalance] table').count(),0);assert.equal(await page.locator('[data-tv1-risk-codes] li').count(),8);assert.match(await page.locator('[data-tv1-risk-codes]').textContent(),/R1 · 확신 보유 종목의 무효화 조건 발생/);
  assert.deepEqual(await page.locator('[data-tv1-round-row] td:last-child').allTextContents(),['위험 코드 점검만','위험 코드 점검만','위험 코드 점검만']);
  assert.match(await page.locator('[data-tv1-transition] [data-tv1-schedule]').textContent(),/확정 목표 2026년 11월 둘째 주\(11-09 ~ 11-15\) · 미확정 · 조건을 못 맞추면 확정을 미루고 11월 회차는 위험 코드 점검만/);
  phase=width+' number check';assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(),false);
  await page.waitForFunction(()=>!/읽는 중/.test(document.querySelector('[data-tv1-precheck-line]').textContent));
  assert.equal(await page.locator('[data-tv1-precheck-line]').textContent(),'확정 차단 점검: 확인 불가 · 최신 공개 sec-qgv2.json을 읽지 못함');assert.equal(await page.locator('[data-tv1-precheck-table]').count(),0);assert.match(await page.locator('[data-tv1-number-check]').textContent(),/^숫자 검증 통과 · 10개 기업 · calc_version qgv2-calc\/2026-10-17\.1 · 2026-10-23 · 앱 계산식 대조 통과\(시험 가격\) \/ 실기기 시세 경로 미검증 · /);
  // The published file is re-read at the click: absent on this build (404) → blocked with every reason listed.
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>document.querySelector('[data-tv1-finalize-check]'));
  assert.match(await page.locator('[data-tv1-status]').textContent(),/^확정 불가 · 최신 공개 sec-qgv2\.json을 읽지 못함$/);
  assert.deepEqual(await page.locator('[data-tv1-blocker]').evaluateAll(n=>n.map(x=>x.dataset.tv1Blocker)),['SEC_QGV2_NOT_AVAILABLE','NUMBER_CHECK_CALC_VERSION_MISMATCH']);
  const store=await page.evaluate(()=>{const v=PlaybookScreen.read(localStorage);return{records:v.records.filter(r=>r.primary_code==='TV1').map(r=>r.verdict),versions:v.target_v1.versions.length};});
  assert.equal(store.versions,0);assert.equal(store.records.length,16);assert.equal(store.records.filter(v=>v==='TV1_DISAGREE').length,1);assert.equal(store.records.filter(v=>v==='TV1_UNKNOWN').length,1);
  await page.goto(BASE+'#home');await page.goto(BASE+'#playbook');await page.locator('[data-tv1-confirm]').waitFor();assert.match(await page.locator('[data-playbook-scoring]').textContent(),/TARGET v1 반대/);
  phase=width+' finalize';await page.evaluate(async c=>{const catalog=await(await fetch('actual-catalog.json')).json(),rows=catalog.instruments.map((r,i)=>({ticker:r.ticker,weight:r.target_units/catalog.total_units+(i%2?0.001:-0.001)}));
   // Synthetic published payloads (raw shape), handed out per click so each finalize re-reads; a number check passed for qgv2-calc/2026-10-17.1.
   window.__pub={reads:0,calc:null,patch:{}};const cfg={...TargetV1ConfigDefaults,number_check:{...TargetV1ConfigDefaults.number_check,result:{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-14',companies:10}}};
   await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,config:cfg,catalog,storage:localStorage,date:'2026-10-14',ram:{state:'AVAILABLE',total:100000000,rows},
    publishedProvider:async()=>{window.__pub.reads++;return window.__tv1Payload(window.__pub.calc,{patch:window.__pub.patch});}});},null);
  assert.match(await page.locator('[data-tv1-number-check]').textContent(),/^숫자 검증 통과 · 10개 기업 · calc_version qgv2-calc\/2026-10-17\.1 · 2026-10-14/);
  // 확정 차단 점검 before any click: the mount read the same provider once; all rows fresh → line only, no table.
  await page.waitForFunction(()=>window.__pub.reads===1&&/오늘 차단/.test(document.querySelector('[data-tv1-precheck-line]').textContent));
  assert.equal(await page.locator('[data-tv1-precheck-line]').textContent(),'확정 차단 점검: 오늘 차단 0 · 내일 차단 0 · 보존 행 0');assert.equal(await page.locator('[data-tv1-precheck-table]').count(),0);
  assert.equal(await page.evaluate(()=>{const n=document.querySelector('[data-tv1-precheck]');return!!(n.compareDocumentPosition(document.querySelector('[data-tv1-finalize]'))&Node.DOCUMENT_POSITION_FOLLOWING);}),true,'the line is above the 확정 button');
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>document.querySelector('[data-tv1-finalize-check]'));
  assert.deepEqual(await page.locator('[data-tv1-blocker]').evaluateAll(n=>n.map(x=>x.dataset.tv1Blocker)),['CALC_VERSION_MISSING','DRAFT_BASIS_CHANGED','NUMBER_CHECK_CALC_VERSION_MISMATCH']);assert.match(await page.locator('[data-tv1-status]').textContent(),/calc_version 없음\(이전 형식 파일\)/);
  // Another calc_version on a valid file → the draft must be regenerated; without this page's scores of that file → reload hint.
  await page.evaluate(()=>{window.__pub.calc='qgv2-calc/2026-10-17.2';});await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>window.__pub.reads===3&&/페이지를 새로 고친 뒤 다시 확정하세요/.test(document.querySelector('[data-tv1-status]').textContent));
  assert.deepEqual(await page.locator('[data-tv1-blocker]').evaluateAll(n=>n.map(x=>x.dataset.tv1Blocker)),['DRAFT_BASIS_CHANGED','NUMBER_CHECK_CALC_VERSION_MISMATCH']);assert.equal(await page.evaluate(()=>TargetV1Screen.readState(PlaybookScreen,localStorage).versions.length),0);
  // One valued row acquired 8+ days ago blocks (row acquisition, not the file as_of). Its shard was collected later (2026-10-13), so it
  // is a kept row: the identity-action text, not the all-shards hint; the line counts the same row the finalize check counts.
  await page.evaluate(()=>{window.__pub.calc='qgv2-calc/2026-10-17.1';window.__pub.patch={'NYSE:P200':{acquired_at:'2026-10-05T00:00:00Z'}};});await page.locator('[data-tv1-finalize]').click();
  await page.waitForFunction(()=>window.__pub.reads===4&&document.querySelector('[data-tv1-blocker]')?.dataset.tv1Blocker==='ROW_DATA_STALE');
  assert.deepEqual(await page.locator('[data-tv1-blocker]').evaluateAll(n=>n.map(x=>x.dataset.tv1Blocker)),['ROW_DATA_STALE']);assert.deepEqual(await page.locator('[data-tv1-stale-action]').evaluateAll(n=>n.map(x=>x.dataset.tv1StaleAction)),['KEPT']);
  assert.match(await page.locator('[data-tv1-stale-action]').textContent(),/^보존 행 \(KEPT\) · .*기호·식별 조치 필요\(별칭, 사유 있는 NA 또는 CIK 고정\) · 전체 샤드\(all_shards\) 실행으로는 풀리지 않음$/);
  assert.match(await page.locator('[data-tv1-published]').textContent(),/7일 넘은 행 1 · 가장 오래된 수집 2026-10-05T00:00:00Z/);
  assert.equal(await page.locator('[data-tv1-precheck-line]').textContent(),'확정 차단 점검: 오늘 차단 1 · 내일 차단 1 · 보존 행 1');
  assert.deepEqual(await page.locator('[data-tv1-precheck-table] tbody tr').evaluateAll(n=>n.map(x=>[x.dataset.tv1PrecheckKind,...[...x.querySelectorAll('td')].map(t=>t.textContent)])),[['KEPT','NYSE:P200','2026-10-05 00:00','9','2026-10-11','보존 행 (KEPT)']]);
  assert.deepEqual(await page.locator('[data-tv1-precheck-action]').evaluateAll(n=>n.map(x=>x.dataset.tv1PrecheckAction)),['KEPT']);
  // A selected name whose latest metrics fail financial safety blocks.
  const victimCode=await page.evaluate(()=>'NASDAQ:'+TargetV1Builder.currentSelection(TargetV1Screen.readState(PlaybookScreen,localStorage)).rows[0].symbol);
  await page.evaluate(c=>{window.__pub.patch={[c]:{metrics:{net_debt_to_ebitda:5,interest_coverage:12}}};},victimCode);await page.locator('[data-tv1-finalize]').click();
  await page.waitForFunction(()=>window.__pub.reads===5&&document.querySelector('[data-tv1-blocker]')?.dataset.tv1Blocker==='FINANCIAL_SAFETY_RECHECK_FAILED');
  assert.equal(await page.locator('[data-tv1-precheck-line]').textContent(),'확정 차단 점검: 오늘 차단 0 · 내일 차단 0 · 보존 행 0','the click file replaced the line');assert.equal(await page.locator('[data-tv1-stale-action]').count(),0);
  assert.equal(await page.locator('[data-tv1-safety-recheck]').textContent(),'재무 안전 재검사 불통과 · '+victimCode.slice(7));
  // A normal NA row (no value, NA reason, no calc_version) does not block.
  await page.evaluate(()=>{window.__pub.patch={'NYSE:P300':{state:'NOT_AVAILABLE',reason_codes:['NOT_COLLECTED'],acquired_at:null,axes:{Q:{score:null},G:{score:null}},metrics:{},calc_version:undefined}};});await page.locator('[data-tv1-finalize]').click();
  await page.waitForFunction(()=>/TARGET v1 저장 · calc_version qgv2-calc\/2026-10-17\.1 · R-C\(규칙 지수\) 2026-10-14 시작/.test(document.querySelector('[data-tv1-status]').textContent));
  assert.equal(await page.evaluate(()=>window.__pub.reads),6);assert.match(await page.locator('[data-tv1-finalize-check]').textContent(),/^확정 검사 통과.*calc_version qgv2-calc\/2026-10-17\.1 · as_of 2026-10-13T21:00:00Z · Q 503\/504 · G 503\/504 · 정상 NA 행 1 · 계산 버전 다른 행 0 · 7일 넘은 행 0/);
  assert.deepEqual(await page.evaluate(()=>TargetV1Screen.readState(PlaybookScreen,localStorage).versions[0].number_check),{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-14',companies:10});
  assert.match(await page.locator('[data-tv1-rule-c]').textContent(),/^R-C · TARGET v1 \(규칙 지수\) · 시작 2026-10-14 · v1/);
  assert.match(await page.locator('[data-tv1-rule-b]').textContent(),/^R-B · v2 상위 15 균등 \(규칙 지수\) · 시작 2026-10-14/);assert.match(await page.locator('[data-tv1-sets]').textContent(),/사용자 세트 B\/C\/D\(VirtualMeta\)와 이름이 겹치지 않게/);assert.match(await page.locator('[data-tv1-version]').textContent(),/v1 · 2026-10-14/);
  phase=width+' rebalance';const reb=page.locator('[data-tv1-rebalance]');assert.match(await reb.locator('h2').textContent(),/1회차 2026-11-16 주/);
  assert.ok(await reb.locator('tbody tr').count()>=15);const first=await reb.locator('tbody tr').first().locator('td').allTextContents();assert.equal(first.length,6);assert.match(first[3],/^[+−]?\d+\.\d\d%p$/);assert.equal(first[5],'●●●만원');
  const nvda=await reb.locator('[data-tv1-rebalance-row=NVDA] td').allTextContents();assert.match(nvda[1],/%$/);
  await reb.locator('[data-tv1-round="3"]').click();assert.match(await page.locator('[data-tv1-rebalance] h2').textContent(),/3회차 2027-05-17 주/);
  phase=width+' compare';await page.evaluate(async()=>{const catalog=await(await fetch('actual-catalog.json')).json();
   // Synthetic closes (RAM, in the page): S&P 500 and the other A names up, B and C names down.
   const provider=async(symbols,from)=>{const out={},days=[];for(let d=new Date(from+'T00:00:00Z');d<=new Date('2027-04-01T00:00:00Z');d.setUTCDate(d.getUTCDate()+1))if(d.getUTCDay()%6)days.push(d.toISOString().slice(0,10));
    const st=TargetV1Screen.readState(PlaybookScreen,localStorage),down=new Set([...(st.versions.at(-1)?.rows||[]).map(r=>r.symbol),...st.rule_b.flatMap(x=>x.rows.map(r=>r.symbol))]);
    for(const sym of symbols){const slope=sym==='SPY'?0.001:down.has(sym)?-0.001:0.002;out[sym]=Object.fromEntries(days.map((d,i)=>[d,100*(1+slope*i)]));}return out;};
   await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,catalog,storage:localStorage,date:'2027-04-01',closesProvider:provider});});
  await page.locator('[data-tv1-load-compare]').click();await page.waitForFunction(()=>document.querySelectorAll('[data-tv1-compare-row] td')[1]?.textContent!=='NA');
  const cmp=await page.locator('[data-tv1-compare-row]').evaluateAll(n=>n.map(x=>x.querySelectorAll('td')[1].textContent));assert.equal(cmp.length,4);assert.ok(cmp.every(v=>/^[+−]\d/.test(v)),cmp.join(','));
  assert.match(await page.locator('[data-tv1-review]').textContent(),/^제안 · R-B와 R-C\(규칙 지수\)가 모두 세트 A와 S&P 500보다 낮습니다/);
  assert.deepEqual(await page.locator('[data-tv1-compare-row]').evaluateAll(n=>n.map(x=>x.dataset.tv1CompareRow)),['A','R-B','R-C','SP500']);
  assert.match(await page.locator('[data-tv1-compare-row="R-B"] td').first().textContent(),/^R-B · .*\(규칙 지수\)$/);assert.match(await page.locator('[data-tv1-compare-row="R-C"] td').first().textContent(),/^R-C · TARGET v1 \(규칙 지수\)$/);
  phase=width+' prices';
  // TV1 names outside the 19 are NA before; the add button asks first (cancel → nothing written), then the stubbed sheet sync runs
  // and the scoring table reads the RAM series. The page never reaches Google here (stubs; anything else is aborted and counted).
  const naBefore=await page.locator('[data-playbook-scoring] tbody tr').evaluateAll(n=>n.filter(x=>/TARGET v1/.test(x.textContent)&&!/^NVDA/.test(x.textContent)&&/NA · DEVICE_HISTORY_UNAVAILABLE/.test(x.textContent)).length);assert.ok(naBefore>=45,String(naBefore));
  await page.evaluate(async()=>{const catalog=await(await fetch('actual-catalog.json')).json();window.__tv1={confirms:[],syncs:[],accept:false};
   const days=[];for(let d=new Date('2026-09-01T00:00:00Z');d<=new Date('2027-04-01T00:00:00Z');d.setUTCDate(d.getUTCDate()+1))if(d.getUTCDay()%6)days.push(d.toISOString().slice(0,10));
   const provider=async symbols=>{const out={};for(const s of symbols)if(window.__tv1.syncs.flat().includes(s))out[s]=Object.fromEntries(days.map((d,i)=>[d,s==='SPY'?100+i*0.1:s==='SYN00'?NaN:50+i*0.2]).filter(([,v])=>Number.isFinite(v)));return out;};
   await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,catalog,storage:localStorage,date:'2027-04-01',
    priceStoreStatus:()=>({state:'READY',fetch:'READY'}),confirm:t=>{window.__tv1.confirms.push(t);return window.__tv1.accept;},
    priceSync:async symbols=>{window.__tv1.syncs.push(symbols);return{state:'READY',kind:'TV1',symbols:symbols.length,fetched:symbols.length-1,appended_rows:symbols.length*3,current:0,write_failed:0,failed:{WORKER_ALLOWLIST:1},not_allowed:1,results:{SYN01:{code:'WORKER_ALLOWLIST',fetched:false,appended:0}}};},
    scoringClosesProvider:provider});});
  const pending=await page.locator('[data-tv1-prices-pending]').textContent();assert.match(pending,/^가격 경로 없음 \d+종목 · SYN/);assert.ok(!/NVDA/.test(pending),'NVDA is one of the 19');
  await page.locator('[data-tv1-add-prices]').click();await page.waitForFunction(()=>/취소 · 시트를 바꾸지 않았습니다/.test(document.querySelector('[data-tv1-prices-status]').textContent));
  let probe=await page.evaluate(()=>({confirms:window.__tv1.confirms.length,syncs:window.__tv1.syncs.length,added:TargetV1Screen.priceSymbols(PlaybookScreen,localStorage).length,text:window.__tv1.confirms[0]}));
  assert.deepEqual([probe.confirms,probe.syncs,probe.added],[1,0,0]);assert.match(probe.text,/내 비공개 구글 시트의 Prices_D 탭에 덧붙입니다:\nSYN\d\d · /);assert.match(probe.text,/ · SPY( · |\n)/);
  await page.evaluate(()=>{window.__tv1.accept=true;});await page.locator('[data-tv1-add-prices]').click();
  await page.waitForFunction(()=>/채점 시계열 \d+종목\(RAM\)/.test(document.querySelector('[data-tv1-prices-status]').textContent));
  probe=await page.evaluate(()=>({syncs:window.__tv1.syncs,added:TargetV1Screen.priceSymbols(PlaybookScreen,localStorage),status:document.querySelector('[data-tv1-prices-status]').textContent,tracked:document.querySelector('[data-tv1-prices-tracked]').textContent,disabled:document.querySelector('[data-tv1-add-prices]').disabled}));
  assert.equal(probe.syncs.length,1);assert.deepEqual(probe.syncs[0].filter(x=>x!=='SYN01'),probe.added);assert.ok(probe.syncs[0].includes('SYN01')&&!probe.added.includes('SYN01'),'not-allowlisted names are not tracked');assert.ok(probe.added.includes('SPY')&&!probe.added.includes('NVDA'));
  assert.equal(probe.disabled,false);assert.match(await page.locator('[data-tv1-prices-pending]').textContent(),/^가격 경로 없음 1종목 · SYN01$/);
  assert.match(probe.status,/^내 시트 추가 · 종목 \d+ · 요청 \d+ · 덧붙인 행 \d+ · WORKER_ALLOWLIST 1 · 채점 시계열 \d+종목\(RAM\)$/);assert.match(probe.tracked,/^내 시트에서 읽는 종목 \d+ · SYN/);
  const scored=await page.locator('[data-playbook-scoring] tbody tr').evaluateAll(n=>n.map(x=>[...x.querySelectorAll('td')].map(t=>t.textContent)));
  const syn=scored.filter(r=>/^SYN(?!0[01])\d\d \d{4}-\d\d-\d\d · TARGET v1/.test(r[0])&&r[1]==='D+20');assert.ok(syn.length>=10,String(syn.length));assert.ok(syn.every(r=>/^\+\d+\.\d\d%$/.test(r[2])),JSON.stringify(syn[0]));
  // SYN00 has no closes in the sheet and SYN01 is outside the Worker allowlist → still NA (never 0).
  const syn00=scored.filter(r=>/^SYN0[01] /.test(r[0]));assert.ok(syn00.length>0&&syn00.every(r=>/^NA · /.test(r[2])&&r[3]==='NA'&&r[4]==='NA'),JSON.stringify(syn00[0]));
  assert.ok(!(await page.evaluate(()=>JSON.stringify(localStorage))).match(/"close"|50\.2|100\.1/),'no price in device storage');
  phase=width+' regenerate';await page.evaluate(seed,{date:'2026-10-14'});
  // All 15 answered; the page's scores are of the latest file (same as_of); a new SEC acquisition in one shard changes the basis and
  // SYN43 now ranks first → the draft is regenerated: 14 answers kept, SYN43 waits for its card.
  await page.evaluate(async()=>{const B=TargetV1Builder,S=TargetV1Screen,catalog=await(await fetch('actual-catalog.json')).json();let st=S.readState(PlaybookScreen,localStorage);
   for(const r of B.currentSelection(st).rows)st=B.answer(st,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});S.writeState(PlaybookScreen,localStorage,st);
   const d=window.__seedData;for(const r of Object.values(d.computed.rows))if(r.ticker==='SYN43')r.v2.total=99;
   const cfg={...TargetV1ConfigDefaults,number_check:{...TargetV1ConfigDefaults.number_check,result:{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-14',companies:10}}};
   await S.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,config:cfg,catalog,storage:localStorage,date:'2026-10-14',computed:d.computed,universeCodes:d.codes,
    screens:{'sec-qgv2.json':{...d.inputs,as_of:'2026-10-13T21:00:00Z'}},publishedProvider:async()=>window.__tv1Payload('qgv2-calc/2026-10-17.1',{patch:{'NYSE:P400':{acquired_at:'2026-10-14T03:00:00Z'}}})});});
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>/입력 기준이 바뀌어 초안을 다시 만들었습니다/.test(document.querySelector('[data-tv1-status]').textContent));
  assert.match(await page.locator('[data-tv1-status]').textContent(),/^입력 기준이 바뀌어 초안을 다시 만들었습니다 · 응답 유지 14 · 새로 확인할 종목 1 \(SYN43\) · 카드 확인 후 다시 확정하세요$/);
  assert.equal(await page.locator('[data-tv1-card="SYN43"] [data-tv1-card-state]').textContent(),'응답 대기');assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(),true);
  const regen=await page.evaluate(()=>{const st=TargetV1Screen.readState(PlaybookScreen,localStorage);return{shards:st.draft.basis.shards,seed:window.__seedData.basis.shards,answers:st.answers.length};});
  assert.notEqual(regen.shards,regen.seed);assert.match(regen.shards,/2026-10-14T03:00:00Z/);
  await page.locator('[data-tv1-card="SYN43"] [data-tv1-answer=AGREE]').click();await page.waitForFunction(()=>!document.querySelector('[data-tv1-finalize]').disabled);
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>/TARGET v1 저장 · calc_version qgv2-calc\/2026-10-17\.1/.test(document.querySelector('[data-tv1-status]').textContent));
  assert.ok((await page.evaluate(()=>TargetV1Screen.readState(PlaybookScreen,localStorage).versions.at(-1).rows.map(r=>r.symbol))).includes('SYN43'));
  phase=width+' v factor gate';
  // 2026-10-23: SYN00 (selected) has V without V4 → the draft is allowed and marked (candidate row, selection reason line, card);
  // finalize is blocked with that reason only; 반대 on SYN00 → the replacement has V1..V5 → finalize saves.
  await page.evaluate(seed,{date:'2026-10-14',vMiss:{SYN00:'v_vs_own_history'}});
  await page.evaluate(async()=>{const B=TargetV1Builder,S=TargetV1Screen,catalog=await(await fetch('actual-catalog.json')).json();let st=S.readState(PlaybookScreen,localStorage);
   for(const r of B.currentSelection(st).rows)st=B.answer(st,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});S.writeState(PlaybookScreen,localStorage,st);
   const cfg={...TargetV1ConfigDefaults,number_check:{...TargetV1ConfigDefaults.number_check,result:{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-14',companies:10}}};
   await S.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,config:cfg,catalog,storage:localStorage,date:'2026-10-14',publishedProvider:async()=>window.__tv1Payload('qgv2-calc/2026-10-17.1')});});
  assert.equal(await page.locator('[data-tv1-candidates] thead th').nth(6).textContent(),'V 요인');
  assert.equal(await page.locator('[data-tv1-candidates] thead th').nth(5).textContent(),'V(임시 V)');assert.match(await page.locator('[data-tv1-v-source]').textContent(),/^V 출처: 임시 V · 기기 시세로 계산 · 중앙 V 미게시/);
  const vRow=page.locator('[data-tv1-candidate=SYN00]');assert.equal(await vRow.getAttribute('data-tv1-v-count'),'4');assert.equal(await vRow.getAttribute('data-tv1-v-incomplete'),'');
  assert.equal(await vRow.locator('[data-tv1-v-cell]').textContent(),'4/5 V4 빠짐 · 확정 불가');assert.match(await vRow.textContent(),/예$|아니오$/);
  assert.equal(await page.locator('[data-tv1-candidate=SYN01] [data-tv1-v-cell]').textContent(),'5/5');assert.equal(await page.locator('[data-tv1-candidates] [data-tv1-v-incomplete]').count(),1);
  assert.match(await page.locator('[data-tv1-v-reason]').textContent(),/^V3\(업종 대비\)·V4\(자기 과거 대비\)가 빠진 V · SYN00 V 4\/5 · 초안은 그대로 쓸 수 있지만 .*확정할 수 없습니다\(2026-10-23 결정\)$/);
  assert.match(await page.locator('[data-tv1-v-reason-selected]').textContent(),/SYN00 V 4\/5/);
  assert.match(await page.locator('[data-tv1-card=SYN00] [data-tv1-v-marker]').textContent(),/^V4 빠짐 · 확정 불가$/);assert.match(await page.locator('[data-tv1-card=SYN00]').textContent(),/V 요인 4\/5 · 산출 요인/);
  assert.equal(await page.locator('[data-tv1-card] [data-tv1-v-marker]').count(),1);assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(),false);
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>document.querySelector('[data-tv1-finalize-check]'));
  assert.deepEqual(await page.locator('[data-tv1-blocker]').evaluateAll(n=>n.map(x=>x.dataset.tv1Blocker)),['V_FACTORS_V3_V4_MISSING']);
  assert.equal(await page.locator('[data-tv1-status]').textContent(),'확정 불가 · V3(업종 대비)·V4(자기 과거 대비)가 빠진 V로 계산된 선정 종목이 있어 확정할 수 없음(초안은 가능 · 2026-10-23 결정)');
  assert.equal(await page.locator('[data-tv1-v-recheck]').textContent(),'V3·V4 빠진 V · SYN00');assert.equal(await page.evaluate(()=>TargetV1Screen.readState(PlaybookScreen,localStorage).versions.length),0);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'v marker horizontal overflow');
  await page.locator('[data-tv1-card=SYN00] [data-tv1-reason]').fill('합성 · V4 없음');await page.locator('[data-tv1-card=SYN00] [data-tv1-answer=DISAGREE]').click();await page.waitForFunction(()=>!document.querySelector('[data-tv1-card=SYN00]'));
  for(;;){const pending=await page.locator('[data-tv1-card]').evaluateAll(n=>n.filter(x=>x.querySelector('[data-tv1-card-state]').textContent==='응답 대기').map(x=>x.dataset.tv1Card));if(!pending.length)break;await card(pending[0]).locator('[data-tv1-answer=AGREE]').click();await page.waitForFunction(s=>document.querySelector('[data-tv1-card="'+s+'"] [data-tv1-card-state]').textContent!=='응답 대기',pending[0]);}
  assert.equal(await page.locator('[data-tv1-v-reason-selected]').count(),0);assert.equal(await page.locator('[data-tv1-v-reason]').count(),1,'the draft table keeps the marker line');
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>/TARGET v1 저장 · calc_version qgv2-calc\/2026-10-17\.1/.test(document.querySelector('[data-tv1-status]').textContent));
  assert.ok(!(await page.evaluate(()=>TargetV1Screen.readState(PlaybookScreen,localStorage).versions.at(-1).rows.map(r=>r.symbol))).includes('SYN00'));
  phase=width+' precheck';
  // 확정 차단 점검 states on the same draft (finalize date varies; payload rows collected 2026-10-13T20:00Z unless patched):
  // tomorrow only → line only; whole shards old → one ROTATION line per shard; kept + rotation → both, and the finalize check agrees.
  const precheck=async(date,patch={})=>{await page.evaluate(async([date,patch])=>{const catalog=await(await fetch('actual-catalog.json')).json();window.__pre={reads:0};
    await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,catalog,storage:localStorage,date,publishedProvider:async()=>{window.__pre.reads++;return window.__tv1Payload('qgv2-calc/2026-10-17.1',{patch});}});},[date,patch]);
   await page.waitForFunction(()=>/오늘 차단/.test(document.querySelector('[data-tv1-precheck-line]').textContent));
   return page.evaluate(()=>({reads:window.__pre.reads,line:document.querySelector('[data-tv1-precheck-line]').textContent,head:[...document.querySelectorAll('[data-tv1-precheck-table] th')].map(x=>x.textContent),
    rows:[...document.querySelectorAll('[data-tv1-precheck-table] tbody tr')].map(x=>[x.dataset.tv1PrecheckKind,x.dataset.tv1PrecheckRow||'group '+x.dataset.tv1PrecheckGroup,...[...x.querySelectorAll('td')].map(t=>t.textContent)]),
    actions:[...document.querySelectorAll('[data-tv1-precheck-action]')].map(x=>[x.dataset.tv1PrecheckAction,x.textContent])}));};
  const shards=await page.evaluate(async()=>{const s=new Set();for(let i=0;i<504;i++){const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('C'+i));s.add(Number(BigInt('0x'+[...new Uint8Array(d)].map(b=>b.toString(16).padStart(2,'0')).join(''))%7n));}return s.size;});
  let pre=await precheck('2026-10-19');assert.deepEqual([pre.reads,pre.line,pre.rows.length,pre.actions.length],[1,'확정 차단 점검: 오늘 차단 0 · 내일 차단 504 · 보존 행 0',0,0]);
  pre=await precheck('2026-10-20');assert.equal(pre.line,'확정 차단 점검: 오늘 차단 504 · 내일 차단 504 · 보존 행 0');
  assert.deepEqual(pre.head,['코드','수집 시각(UTC)','나이(일)','마지막 확정 가능일(수집 UTC 날짜+6)','분류'],'no price and no score column');
  assert.equal(pre.rows.length,shards);assert.ok(pre.rows.every(r=>r[0]==='ROTATION'&&/^group \d$/.test(r[1])&&/^샤드 \d · \d+행$/.test(r[2])&&r[3]==='2026-10-13 20:00'&&r[4]==='7'&&r[5]==='2026-10-19'&&r[6]==='회전 대기 (ROTATION)'),JSON.stringify(pre.rows[0]));
  assert.equal(pre.rows.reduce((n,r)=>n+Number(/· (\d+)행/.exec(r[2])[1]),0),504);
  assert.deepEqual(pre.actions.map(a=>a[0]),['ROTATION']);assert.match(pre.actions[0][1],/^회전 대기 \(ROTATION\) · 샤드 전체가 오래됨 · 다음 정기 실행\(하루 1개 샤드 회전\) 뒤 해소, 또는 .*workflow_dispatch all_shards=true/);
  pre=await precheck('2026-10-20',{'NYSE:P200':{acquired_at:'2026-10-05T00:00:00Z'},'NYSE:P300':{state:'NOT_AVAILABLE',reason_codes:['NOT_COLLECTED'],acquired_at:'2026-09-01T00:00:00Z',axes:{Q:{score:null},G:{score:null}},metrics:{},calc_version:undefined}});
  assert.equal(pre.line,'확정 차단 점검: 오늘 차단 503 · 내일 차단 503 · 보존 행 1','the NA row is not counted');assert.deepEqual(pre.rows[0],['KEPT','NYSE:P200','NYSE:P200','2026-10-05 00:00','15','2026-10-11','보존 행 (KEPT)']);
  assert.equal(pre.rows.filter(r=>r[0]==='ROTATION').length,shards);assert.ok(!pre.rows.some(r=>r[1]==='NYSE:P300'));assert.deepEqual(pre.actions.map(a=>a[0]),['KEPT','ROTATION']);
  await page.locator('[data-tv1-finalize]').click();await page.waitForFunction(()=>window.__pre.reads===2&&document.querySelector('[data-tv1-finalize-check]'));
  assert.ok((await page.locator('[data-tv1-blocker]').evaluateAll(n=>n.map(x=>x.dataset.tv1Blocker))).includes('ROW_DATA_STALE'));
  assert.match(await page.locator('[data-tv1-published]').textContent(),/7일 넘은 행 503 · /);assert.equal(await page.locator('[data-tv1-precheck-line]').textContent(),'확정 차단 점검: 오늘 차단 503 · 내일 차단 503 · 보존 행 1');
  assert.deepEqual(await page.locator('[data-tv1-stale-action]').evaluateAll(n=>n.map(x=>x.dataset.tv1StaleAction)),['KEPT','ROTATION']);
  assert.ok(!/\$|가격|점수/.test(await page.locator('[data-tv1-precheck-table]').textContent()),'codes, times and days only');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'precheck table horizontal overflow');
  phase=width+' shortfall';const few=await page.evaluate(seed,{date:'2026-10-14',n:12});assert.equal(few,12);
  await page.evaluate(async()=>{const catalog=await(await fetch('actual-catalog.json')).json();await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'),{playbook:PlaybookScreen,catalog,storage:localStorage,date:'2026-10-14'});});
  assert.match(await page.locator('[data-tv1-shortfall]').textContent(),/^통과 종목 부족 3종목 · 조건 완화·제외 종목 복귀 없음 · 확정 불가 · 사유: /);assert.equal(await page.locator('[data-tv1-card]').count(),12);assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(),true);
  phase=width+' layout';const text=await page.locator('[data-target-v1-builder]').textContent();assert.ok(!/매수|매도|사세요|파세요|\bbuy\b|\bsell\b/i.test(text),'buy/sell wording');
  assert.equal(await page.locator('[data-tv1-raw]').count(),0,'TARGET raw inputs live in Settings only');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow');
  await page.screenshot({path:(process.env.TV1_SHOT_DIR||'/tmp')+'/target-v1-builder-'+width+'.png',fullPage:true});
  phase=width+' settings raw';const beforeRaw=await page.evaluate(()=>localStorage.getItem(PlaybookScreen.KEY));
  await page.goto(BASE+'#settings');await page.locator('[data-raw-data]').waitFor();
  assert.equal(await page.locator('[data-raw-data]').getAttribute('open'),null,'settings raw data collapsed by default');
  assert.equal(await page.locator('[data-raw-data] [data-tv1-raw]').count(),1);
  await page.locator('[data-raw-data] > summary').click();await page.locator('[data-tv1-raw] > summary').click();
  assert.match(await page.locator('[data-tv1-raw]').textContent(),/무효화 지표/);
  assert.equal(await page.evaluate(()=>localStorage.getItem(PlaybookScreen.KEY)),beforeRaw,'viewing raw data never changes TARGET records');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'settings raw horizontal overflow');
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);
  console.log('PASS TARGET v1 builder empty NA, cards agree/disagree(replace)/unknown, records, number-check gate, finalize, rebalance week, compare, review rule, TV1 sheet prices, risk-only rounds, finalize re-check (calc_version, row freshness, safety), 확정 차단 점검 (line, KEPT / ROTATION table), draft regeneration, V factor gate (2026-10-23) and shortfall '+width);
  await context.close();}}
 catch(e){console.log('FAIL '+phase+' '+e.message);process.exitCode=1;}finally{await browser.close();}
})();
