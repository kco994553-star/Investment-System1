'use strict';
// TARGET v1 finalize rehearsal (owner request 2026-10-23, B-3). Not registered in CI; run by hand against a local build:
//   PAGES_COCKPIT_URL=http://127.0.0.1:<port>/ [CHROMIUM_EXECUTABLE_PATH=...] node implementation/tools/target_v1_finalize_rehearsal_browser_test.js
// SYNTHETIC ONLY: a made-up 504-company universe ('RZnnn' tickers, made-up CIKs, metrics, factor scores and V inputs) and made-up
// device prices / month-end closes passed in RAM to the shipped QgvScores.compute (the same engine the phone runs). Nothing is a
// real price; nothing is stored or published except the device TARGET state the screen itself keeps in this test browser's
// localStorage. Missing values stay NA (never 0). Every request outside the local origin is aborted and counted.
// What it walks (phone width 390 first, then the main path at 1280):
//  P  phone navigation: bottom tab 포트폴리오 → playbook link → TARGET v1 builder (empty public screens: NA, build disabled).
//  A  full path: synthetic 504 scores + device prices + month-ends → draft (button) → 30 candidates → 15 cards → answers →
//     finalize saves TARGET v1 with the #386 number-check record (qgv2-calc/2026-10-17.1) on the window date 2026-11-10.
//  B  each finalize condition broken one at a time on the same answered draft (blocker list and status line checked):
//     number check not passed / other calc_version, file unreadable / legacy / mixed / stale row, Q or G coverage below 90%
//     (and the 454/504 boundary passing), normal NA rows vs NA rows without a reason, financial-safety re-check (FAIL and NA),
//     cards pending, a 반대 without a reason, name shortfall.
//  V  device prices without month-end closes → every V lacks V4 → draft allowed and marked 'V4 빠짐 · 확정 불가', finalize blocked
//     with V_FACTORS_V3_V4_MISSING only; no device prices → V NA → every name excluded (AXIS_COVERAGE_LOW) → build/finalize blocked.
//  S  schedule: before the window (risk-code checks only), after 11-15 unfinalized → 확정 연기 text; round 1 (11-16) lists names
//     only when finalized on or before it.
//  L  label audit: whether the screen says where V comes from (central qgv-official vs device '임시 V').
// No buy/sell wording; no horizontal page scroll.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8870/';
const SHOT = process.env.TV1_REHEARSAL_SHOT_DIR || null;

// In-page synthetic generator (init script). Ticker 'RZnnn', CIK '99' + 8 digits: made up, not real issuers.
const GEN = `window.__reh=(()=>{
 const N=504,CALC='qgv2-calc/2026-10-17.1';
 // SAFE: SICs the shipped PlaybookEngine.classifyTypesV0 does not mark cyclical; CYCLICAL: ones it does (semis 3674, equipment 3559, ...).
 const SAFE=['7372','3612','3812','3823','2834','5812','4911','2080','3571','4813','3841'],CYCLICAL=['3674','3559','1311','5331','2621','3711','4512'],ALL=[...SAFE,...CYCLICAL];
 const GROUPS=['services_software_health','manufacturing_industrial_tech','consumer_trade','energy_materials'];
 const QF=['q_profitability','q_moat_proxy','q_earnings_quality','q_financial_safety','q_capital_allocation'],GF=['g_revenue_growth','g_per_share_growth','g_growth_efficiency','g_consistency','g_recent_acceleration'];
 const code=i=>(i%2?'NYSE:':'NASDAQ:')+'RZ'+String(i).padStart(3,'0'),codes=Array.from({length:N},(_,i)=>code(i));
 const r1=v=>Math.round(v*10)/10;
 function record(i,{calc,acquired,cyclical}){const SICS=cyclical?ALL:SAFE;
  const q=Math.max(5,r1(93-i*0.16-(i%9))),g=Math.max(5,r1(89-i*0.15-(i%7))),factors={};
  QF.forEach((k,j)=>{factors[k]=Math.min(100,r1(q+j*1.5-3));});GF.forEach((k,j)=>{factors[k]=Math.min(100,r1(g-j*1.2+2));});
  // Financial safety: every 23rd name fails (net debt/EBITDA 3.5), every 31st has no interest coverage (NA → excluded).
  const metrics={roic:0.08+(i%11)*0.02,moat_return_mean_5y:0.07+(i%9)*0.02,fcf_to_net_income:0.7+(i%6)*0.1,net_debt_to_ebitda:i%23===5?3.5:0.4+(i%5)*0.3,revenue_cagr_3y:0.02+(i%8)*0.015};
  if(i%31!==7)metrics.interest_coverage=5+(i%6)*2;
  const ebit=60+(i%37)*7,shares=100+(i%29)*4,ocf=45+(i%31)*5,capex=6+(i%5);
  const r={cik:'99'+String(10000000+i).slice(1),acquired_at:acquired,state:'LIVE',reason_codes:[],sic:SICS[i%SICS.length],industry_group:GROUPS[i%GROUPS.length],
   profile:'GENERAL',fiscal_year_end:'2025-12-31',currency:'USD',metrics,factors,
   axes:{Q:{score:q,factors_available:'5/5',available_weight:100},G:{score:g,factors_available:'5/5',available_weight:100}},
   v_inputs_v2:{currency:'USD',taxonomy:'us-gaap',fiscal_year_end:'2025-12-31',
    ebit:{fy_value:ebit,fy_end:'2025-12-31',ttm_value:null,ttm_end:null},fcf:{fy_value:ocf-capex,fy_end:'2025-12-31',ttm_value:null,ttm_end:null},
    total_debt:{value:50+(i%13)*5,period_end:'2026-06-30'},cash_and_equivalents:{value:20+(i%7)*3,period_end:'2026-06-30'},diluted_shares:{value:shares,period_end:'2026-06-30'},
    revenue:{fy_value:(60+(i%37)*7)*6,fy_end:'2025-12-31',ttm_value:null,ttm_end:null},operating_margin_history:[2021,2022,2023,2024,2025].map((y,j)=>({fiscal_year_end:y+'-12-31',value:0.14+0.01*j})),
    ebit_per_share_history:[2021,2022,2023,2024,2025].map((y,j)=>({fiscal_year_end:y+'-12-31',value:Math.round(ebit/shares*(0.72+0.06*j)*1e4)/1e4})),
    fcf_per_share_history:[],revenue_cagr_3y:0.02+(i%8)*0.015,eps_cagr_3y:0.05,fcf_per_share_cagr_3y:0.04,revenue_ttm_growth:0.05}};
  if(calc)r.calc_version=calc;return r;}
 // A normal NA row as the collector writes it: no values, an NA reason, no calc_version.
 const naRow=i=>({cik:'99'+String(10000000+i).slice(1),state:'NOT_AVAILABLE',reason_codes:['NOT_COLLECTED'],acquired_at:null,fiscal_year_end:null,factors:{},axes:{},metrics:{},v_inputs_v2:{}});
 /* Raw published sec-qgv2.json shape. naTail: the last n codes become normal NA rows; qNullTail / gNullTail: the last n codes lose
    only their Q / G axis score; naNoReason: n NA rows without a reason code; patch: {code: fields}. */
 function payload({calc=CALC,asOf='2026-11-09T21:00:00Z',acquired='2026-11-09T20:00:00Z',legacy=false,naTail=0,qNullTail=0,gNullTail=0,naNoReason=0,cyclical=false,patch={}}={}){
  const out={schema_version:1,kind:'SEC_QGV2',as_of:asOf,shard_count:7,records:{},target:{}};if(!legacy)out.calc_version=calc;
  for(let i=0;i<N;i++){let r=record(i,{calc:legacy?null:calc,acquired,cyclical});
   if(i>=N-naTail)r=naRow(i);if(i>=N-naTail-naNoReason&&i<N-naTail){r=naRow(i);r.reason_codes=[];}
   if(i>=N-qNullTail)r.axes.Q={score:null};if(i>=N-gNullTail)r.axes.G={score:null};out.records[code(i)]=r;}
  for(const[c,f]of Object.entries(patch))Object.assign(out.records[c],f);return out;}
 /* Synthetic device quotes in RAM: a made-up USD price per code (priced: how many codes, from the top), month-end closes for the
    fiscal year-end months when monthEnds (V4 own history needs >= 3). */
 function quotes(p,{priced=N,monthEnds=true}={}){const out={};let n=0;
  for(const[c,r]of Object.entries(p.records)){if(r.state!=='LIVE'||n>=priced)continue;n++;const i=Number(c.slice(-3)),price=30+((i*37)%170)+0.25,q={price,currency:'USD'};
   if(monthEnds)q.month_closes=Object.fromEntries([2021,2022,2023,2024,2025].map((y,j)=>[y+'-12',Math.round(price*(0.8+0.05*j+((i+j)%3)*0.02)*100)/100]));out[c]=q;}
  return out;}
 function compute(p,q){const inputs=Qgv2Inputs.fromInputs(Qgv2Inputs.light(p)),identities=codes.map(c=>({company_id:c,ticker:c.slice(c.indexOf(':')+1)}));
  return{inputs,computed:QgvScores.compute({identities,publicScreens:{[Qgv2Inputs.FILE]:inputs},v2Inputs:inputs,quotes:q})};}
 return{N,CALC,codes,code,payload,quotes,compute};})();`;

const blockers = (page) => page.locator('[data-tv1-blocker]').evaluateAll((n) => n.map((x) => x.dataset.tv1Blocker));
const status = (page) => page.locator('[data-tv1-status]').textContent();
const log = [];
function note(step, what) { log.push(step + ' | ' + what); }

/* Mount the shipped TARGET v1 screen with synthetic scores computed in the page. spec: {date, priced, monthEnds, cfg ('386' |
   'canonical'), reset, pub (published spec for the provider, null = unreadable)}. The provider re-reads window.__pub at each click. */
async function mount(page, spec) {
  return page.evaluate(async (s) => {
    const R = window.__reh, catalog = await (await fetch('actual-catalog.json')).json();
    const own = { cyclical: !!s.cyclical, asOf: s.asOf, acquired: s.acquired }, page0 = R.payload(own), { inputs, computed } = R.compute(page0, R.quotes(page0, { priced: s.priced ?? R.N, monthEnds: s.monthEnds !== false }));
    window.__pub = { spec: s.pub === undefined ? {} : s.pub, base: own, reads: 0 };
    const base = TargetV1ConfigDefaults, cfg = s.cfg === 'canonical' ? { ...base, number_check: { ...base.number_check, result: { calc_version: null, passed: false, date: null, companies: 0 } } }
      : s.cfg === 'other' ? { ...base, number_check: { ...base.number_check, result: { ...base.number_check.result, calc_version: 'qgv2-calc/2026-10-10.1' } } } : base;
    if (s.reset) TargetV1Screen.writeState(PlaybookScreen, localStorage, TargetV1Builder.emptyState());
    window.__ctx = { computed, inputs: { ...inputs, as_of: page0.as_of } };
    await TargetV1Screen.mount(document.querySelector('[data-target-v1-builder]'), {
      playbook: PlaybookScreen, config: cfg, catalog, storage: localStorage, date: s.date, computed, universeCodes: R.codes,
      screens: { 'sec-qgv2.json': window.__ctx.inputs },
      publishedProvider: async () => { window.__pub.reads++; return window.__pub.spec === null ? null : R.payload({ ...window.__pub.base, ...window.__pub.spec }); } });
    const rows = Object.values(computed.rows), v = rows.filter((r) => Number.isFinite(r.v2?.v));
    return { state: computed.v2_state, priced: computed.priced_codes, rows: rows.length, withV: v.length,
      v5: v.filter((r) => ['v_earnings_yield', 'v_fcf_yield', 'v_vs_industry', 'v_vs_own_history', 'v_expectation_check'].every((k) => Number.isFinite(r.v2.factors?.[k]?.score))).length };
  }, spec);
}
async function answerAll(page) {
  for (;;) {
    const pending = await page.locator('[data-tv1-card]').evaluateAll((n) => n.filter((x) => x.querySelector('[data-tv1-card-state]').textContent === '응답 대기').map((x) => x.dataset.tv1Card));
    if (!pending.length) return;
    await page.locator('[data-tv1-card="' + pending[0] + '"] [data-tv1-answer=AGREE]').click();
    await page.waitForFunction((s) => document.querySelector('[data-tv1-card="' + s + '"] [data-tv1-card-state]')?.textContent !== '응답 대기', pending[0]);
  }
}
// One finalize click against the published spec; returns {blockers, status, saved versions}.
async function tryFinalize(page, pub) {
  await page.evaluate((p) => { window.__pub.spec = p; }, pub);
  const reads = await page.evaluate(() => window.__pub.reads);
  await page.locator('[data-tv1-finalize]').click();
  await page.waitForFunction((n) => window.__pub.reads > n && !/다시 읽는 중/.test(document.querySelector('[data-tv1-status]').textContent), reads);
  return { blockers: await blockers(page), status: await status(page), versions: await page.evaluate(() => TargetV1Screen.readState(PlaybookScreen, localStorage).versions.length) };
}
async function buildDraftByButton(page) {
  await page.locator('[data-tv1-build]').click();
  await page.waitForFunction(() => /초안 만듦/.test(document.querySelector('[data-tv1-status]').textContent));
  return status(page);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });let phase = 'start';
  try {
    for (const width of [390, 1280]) {
      const phone = width === 390, tag = (s) => width + ' ' + s;
      const context = await browser.newContext({ viewport: { width, height: phone ? 844 : 900 }, serviceWorkers: 'block' }), unexpected = [];
      await routeEmptyPublicScreens(context);
      await context.route('**/*', (route) => { const url = new URL(route.request().url());if (url.origin === new URL(BASE).origin) return route.fallback();unexpected.push(url.origin);return route.abort(); });
      await context.addInitScript({ content: GEN });
      const page = await context.newPage(), errors = [];page.on('pageerror', (e) => errors.push(e.message));

      // ---------- P: phone navigation to the builder (empty public screens) ----------
      phase = tag('P navigation');await page.goto(BASE);await page.locator('#primary-nav [data-nav-tab="portfolio"]').waitFor();
      const tabText = (await page.locator('#primary-nav [data-nav-tab="portfolio"]').innerText()).replace(/\s+/g, ' ').trim();
      await page.locator('#primary-nav [data-nav-tab="portfolio"]').click();
      const link = page.locator('a[href="#playbook"]', { hasText: 'TARGET v1' }).first();await link.waitFor();
      const linkText = (await link.textContent()).trim();await link.click();
      await page.locator('[data-tv1-builder]').waitFor();
      assert.equal(await page.locator('[data-tv1-build]').isDisabled(), true);
      const readiness = await page.locator('[data-tv1-readiness]').textContent(), coverage = await page.locator('[data-tv1-coverage]').textContent();
      assert.match(readiness, /^NA · QGV v2 총점에는 V가 필요/);assert.match(coverage, /Q 0\/504, G 0\/504/);
      note(tag('P'), 'tab "' + tabText + '" → link "' + linkText + '" → #playbook · readiness "' + readiness + '" · coverage "' + coverage + '" · build disabled');
      const vText = await page.locator('[data-target-v1-builder]').textContent();
      note(tag('L'), 'V source label on builder: 임시 V=' + /임시 V/.test(vText) + ' · qgv-official=' + /qgv-official|중앙 V|공식 V/.test(vText));

      // ---------- A: full path, all conditions met (window date 2026-11-10, #386 number check) ----------
      phase = tag('A compute');const a = await mount(page, { date: '2026-11-10', reset: true });
      assert.equal(a.state, 'READY');assert.equal(a.rows, 504);assert.ok(a.withV >= 400, JSON.stringify(a));
      note(tag('A'), 'synthetic compute: rows ' + a.rows + ' · priced ' + a.priced + ' · V ' + a.withV + ' · V 5/5 ' + a.v5);
      assert.equal(await page.locator('[data-tv1-build]').isDisabled(), false);
      assert.match(await page.locator('[data-tv1-readiness]').textContent(), /^QGV v2 계산됨 · 기기 가격 504종목/);
      phase = tag('A draft');const built = await buildDraftByButton(page);
      assert.match(built, /^초안 만듦 · 통과 \d+ · 후보 30 · 입력 기준 qgv2-calc\/2026-10-17\.1$/);note(tag('A'), 'build → "' + built + '"');
      assert.equal(await page.locator('[data-tv1-candidates] tbody tr').count(), 30);assert.equal(await page.locator('[data-tv1-card]').count(), 15);
      assert.equal(await page.locator('[data-tv1-candidates] [data-tv1-v-incomplete]').count(), 0);
      assert.match(await page.locator('[data-tv1-limits]').textContent(), /16절 한도 통과/);
      const sel0 = await page.locator('[data-tv1-selection] h2').textContent();note(tag('A'), 'selection "' + sel0 + '"');
      assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(), true, 'cards pending → finalize disabled');
      // B: cards pending (button disabled) and a 반대 without a reason (refused, nothing changes).
      phase = tag('B disagree reason');const first = await page.locator('[data-tv1-card]').first().getAttribute('data-tv1-card');
      await page.locator('[data-tv1-card="' + first + '"] [data-tv1-answer=DISAGREE]').click();
      assert.equal(await status(page), '반대 이유를 한 줄로 적어 주세요.');assert.equal(await page.locator('[data-tv1-card="' + first + '"]').count(), 1);
      await page.locator('[data-tv1-card="' + first + '"] [data-tv1-reason]').fill('합성 · 리허설 반대');await page.locator('[data-tv1-card="' + first + '"] [data-tv1-answer=DISAGREE]').click();
      await page.waitForFunction((s) => !document.querySelector('[data-tv1-card="' + s + '"]'), first);
      note(tag('B'), '반대 without reason refused; with reason → "' + await status(page) + '"');
      await answerAll(page);assert.equal(await page.locator('[data-tv1-finalize]').isDisabled(), false);
      if (SHOT && phone) await page.locator('[data-tv1-confirm]').screenshot({ path: SHOT + '/rehearsal-confirm-390.png' });

      // ---------- B: break one condition at a time (same answered draft) ----------
      const cases = [
        ['number check not passed (canonical db66d312 state)', { cfg: 'canonical' }, {}, ['NUMBER_CHECK_NOT_PASSED']],
        ['number check of another calc_version', { cfg: 'other' }, {}, ['NUMBER_CHECK_CALC_VERSION_MISMATCH']],
        ['published file unreadable', {}, null, ['SEC_QGV2_NOT_AVAILABLE', 'NUMBER_CHECK_CALC_VERSION_MISMATCH']],
        ['legacy file without calc_version', {}, { legacy: true }, ['CALC_VERSION_MISSING', 'DRAFT_BASIS_CHANGED', 'NUMBER_CHECK_CALC_VERSION_MISMATCH']],
        ['one valued row of another calc_version', {}, { patch: { 'NASDAQ:RZ400': { calc_version: 'qgv2-calc/2026-11-01.1' } } }, ['CALC_VERSION_MIXED']],
        ['one valued row acquired 8 days before', {}, { patch: { 'NASDAQ:RZ400': { acquired_at: '2026-11-02T00:00:00Z' } } }, ['ROW_DATA_STALE']],
        ['Q coverage 453/504 (Q score dropped on 51 rows)', {}, { qNullTail: 51 }, ['Q_COVERAGE_LOW']],
        ['G coverage 453/504', {}, { gNullTail: 51 }, ['G_COVERAGE_LOW']],
        ['51 normal NA rows (Q and G 453/504)', {}, { naTail: 51 }, ['Q_COVERAGE_LOW', 'G_COVERAGE_LOW']],
        ['3 NA rows without a reason code', {}, { naNoReason: 3 }, ['CALC_VERSION_MIXED']],
        ['new calc_version file, other as_of (page scores older)', {}, { calc: 'qgv2-calc/2026-11-05.1', asOf: '2026-11-10T21:00:00Z' }, ['DRAFT_BASIS_CHANGED', 'NUMBER_CHECK_CALC_VERSION_MISMATCH']],
      ];
      const selected = await page.evaluate(() => TargetV1Builder.currentSelection(TargetV1Screen.readState(PlaybookScreen, localStorage)).rows.map((r) => r.code));
      cases.push(['selected name fails financial safety on the latest file', {}, { patch: { [selected[0]]: { metrics: { net_debt_to_ebitda: 4, interest_coverage: 9 } } } }, ['FINANCIAL_SAFETY_RECHECK_FAILED']]);
      cases.push(['selected name financial safety NA on the latest file', {}, { patch: { [selected[1]]: { metrics: { net_debt_to_ebitda: 1 } } } }, ['FINANCIAL_SAFETY_RECHECK_FAILED']]);
      for (const [label, m, pub, want] of (phone ? cases : cases.slice(0, 2))) {
        phase = tag('B ' + label);await mount(page, { date: '2026-11-10', ...m, pub });
        const r = await tryFinalize(page, pub);assert.deepEqual(r.blockers, want, label + ' · ' + r.status);assert.equal(r.versions, 0, label);
        note(tag('B'), label + ' → [' + r.blockers.join(', ') + '] · "' + r.status + '"');
      }
      if (phone) {
        // Boundary: 50 normal NA rows → Q·G 454/504 (≥ 90%) passes the coverage check; the result here is a real save, so it runs last.
        phase = tag('B new calc_version same as_of');await mount(page, { date: '2026-11-10', pub: {} });
        const regen = await tryFinalize(page, { calc: 'qgv2-calc/2026-11-05.1' });
        note(tag('B'), 'new calc_version, same as_of → [' + regen.blockers.join(', ') + '] · "' + regen.status + '"');
        assert.equal(regen.versions, 0);assert.match(regen.status, /^입력 기준이 바뀌어 초안을 다시 만들었습니다/);
        // Put the draft back on the page's file basis (regenerating restores it; answers kept for the same names).
        await mount(page, { date: '2026-11-10', pub: {} });const back = await tryFinalize(page, {});
        assert.match(back.status, /^입력 기준이 바뀌어 초안을 다시 만들었습니다 · 응답 유지 15 · 새로 확인할 종목 0/);note(tag('B'), 'back to page basis → "' + back.status + '"');
      }

      // ---------- S: schedule texts before finalize ----------
      phase = tag('S schedule');await mount(page, { date: '2026-11-16', pub: {} });
      const late = await page.locator('[data-tv1-confirm] [data-tv1-schedule]').textContent();assert.match(late, /목표 주까지 조건 미충족 · 확정 연기 · 11월 회차는 위험 코드 점검만/);
      assert.match(await page.locator('[data-tv1-risk-only]').textContent(), /^TARGET v1 미확정 · 회차별 종목 목록·예상 금액 없음/);
      note(tag('S'), '2026-11-16 unfinalized → "' + late + '" · round 1 risk-code checks only');

      // ---------- A: finalize succeeds (50 normal NA rows: 454/504 boundary) ----------
      phase = tag('A finalize');await mount(page, { date: '2026-11-10', pub: { naTail: 50 } });
      const ok = await tryFinalize(page, { naTail: 50 });
      assert.deepEqual(ok.blockers, []);assert.equal(ok.versions, 1, ok.status);assert.match(ok.status, /^TARGET v1 저장 · calc_version qgv2-calc\/2026-10-17\.1 · R-C\(규칙 지수\) 2026-11-10 시작 · 원본 v0 유지$/);
      const check = await page.locator('[data-tv1-finalize-check]').textContent();assert.match(check, /^확정 검사 통과.*Q 454\/504 · G 454\/504 · 정상 NA 행 50 · 계산 버전 다른 행 0 · 7일 넘은 행 0/);
      const saved = await page.evaluate(() => TargetV1Screen.readState(PlaybookScreen, localStorage).versions[0]);
      assert.deepEqual(saved.number_check, { calc_version: 'qgv2-calc/2026-10-17.1', passed: true, date: '2026-10-23', companies: 10 });
      assert.equal(saved.rows.length, 15);assert.ok(!('v_basis' in saved), 'version records no V source today');
      note(tag('A'), 'finalize → "' + ok.status + '" · check "' + check.slice(0, 160) + '" · saved keys ' + Object.keys(saved).join(','));
      assert.match(await page.locator('[data-tv1-rebalance] h2').textContent(), /1회차 2026-11-16 주/);assert.ok(await page.locator('[data-tv1-rebalance] tbody tr').count() >= 15);
      note(tag('S'), 'finalized 2026-11-10 → round 1 (2026-11-16) lists names: ' + await page.locator('[data-tv1-rebalance] tbody tr').count() + ' rows · schedule "' + await page.locator('[data-tv1-confirm] [data-tv1-schedule]').textContent() + '"');
      if (SHOT && phone) await page.locator('[data-tv1-confirm]').screenshot({ path: SHOT + '/rehearsal-finalized-390.png' });

      // ---------- V: prices without month-ends (V4 missing everywhere) and no prices ----------
      phase = tag('V no month-ends');const v = await mount(page, { date: '2026-11-10', reset: true, monthEnds: false, pub: {} });
      note(tag('V'), 'no month-ends compute: V ' + v.withV + ' · V 5/5 ' + v.v5);assert.equal(v.v5, 0);
      await buildDraftByButton(page);const vCell = await page.locator('[data-tv1-candidates] tbody tr').first().locator('[data-tv1-v-cell]').textContent();
      assert.equal(vCell, '4/5 V4 빠짐 · 확정 불가');assert.equal(await page.locator('[data-tv1-candidates] [data-tv1-v-incomplete]').count(), 30);
      await answerAll(page);const vr = await tryFinalize(page, {});
      assert.deepEqual(vr.blockers, ['V_FACTORS_V3_V4_MISSING']);assert.equal(vr.versions, 0);
      note(tag('V'), 'draft allowed, every candidate "' + vCell + '" → [' + vr.blockers.join(', ') + '] · "' + vr.status + '"');
      if (SHOT && phone) await page.locator('[data-tv1-confirm]').screenshot({ path: SHOT + '/rehearsal-v4-blocked-390.png' });
      phase = tag('V no prices');const np = await mount(page, { date: '2026-11-10', reset: true, priced: 0, pub: {} });
      note(tag('V'), 'no device prices: V ' + np.withV + ' · readiness "' + await page.locator('[data-tv1-readiness]').textContent() + '" · build disabled ' + await page.locator('[data-tv1-build]').isDisabled());
      if (!(await page.locator('[data-tv1-build]').isDisabled())) {
        await page.locator('[data-tv1-build]').click();await page.waitForFunction(() => document.querySelector('[data-tv1-status]').textContent.length > 0);
        note(tag('V'), 'no device prices → build "' + await status(page) + '" · cards ' + await page.locator('[data-tv1-card]').count() + ' · shortfall "' + ((await page.locator('[data-tv1-shortfall]').count()) ? await page.locator('[data-tv1-shortfall]').textContent() : 'none') + '" · finalize disabled ' + ((await page.locator('[data-tv1-finalize]').count()) ? await page.locator('[data-tv1-finalize]').isDisabled() : 'NA'));
      }
      phase = tag('V partial prices');await mount(page, { date: '2026-11-10', reset: true, priced: 60, pub: {} });await buildDraftByButton(page);
      note(tag('V'), '60 priced codes → "' + await status(page) + '" · cards ' + await page.locator('[data-tv1-card]').count() + ' · shortfall "' + ((await page.locator('[data-tv1-shortfall]').count()) ? await page.locator('[data-tv1-shortfall]').textContent() : 'none') + '" · finalize disabled ' + await page.locator('[data-tv1-finalize]').isDisabled());

      // ---------- C: cyclical names (semis etc.) in the universe: month-ends present, V4 still missing by rule ----------
      if (phone) {
        phase = tag('C cyclical');const cy = await mount(page, { date: '2026-11-10', reset: true, cyclical: true, pub: {} });
        await buildDraftByButton(page);
        const marked = await page.locator('[data-tv1-candidates] [data-tv1-v-incomplete]').count(), markedCards = await page.locator('[data-tv1-card] [data-tv1-v-marker]').count();
        const sample = await page.locator('[data-tv1-candidates] [data-tv1-v-incomplete] [data-tv1-v-cell]').first().textContent().catch(() => 'none');
        note(tag('C'), 'cyclical SICs included: compute V ' + cy.withV + ' · V 5/5 ' + cy.v5 + ' · candidates marked ' + marked + '/30 ("' + sample + '") · selected cards marked ' + markedCards + '/15');
        await answerAll(page);const cr = await tryFinalize(page, {});
        note(tag('C'), 'finalize with cyclical names selected → [' + cr.blockers.join(', ') + ']');
        if (markedCards) assert.deepEqual(cr.blockers, ['V_FACTORS_V3_V4_MISSING']);
        // The only path the rules leave: 반대 (with a reason) on each marked name; the next-ranked name takes its place.
        let rejected = 0;
        for (;;) {
          const m = await page.locator('[data-tv1-card]:has([data-tv1-v-marker])').first().getAttribute('data-tv1-card').catch(() => null);if (!m) break;
          await page.locator('[data-tv1-card="' + m + '"] [data-tv1-reason]').fill('합성 · V4 없음(경기민감 정규화)');await page.locator('[data-tv1-card="' + m + '"] [data-tv1-answer=DISAGREE]').click();
          await page.waitForFunction((s) => !document.querySelector('[data-tv1-card="' + s + '"]'), m);rejected++;if (rejected > 40) break;
        }
        await answerAll(page);const shortC = (await page.locator('[data-tv1-shortfall]').count()) ? await page.locator('[data-tv1-shortfall]').textContent() : 'none';
        const after = await page.locator('[data-tv1-finalize]').isDisabled() ? { blockers: ['(button disabled)'], status: '', versions: 0 } : await tryFinalize(page, {});
        note(tag('C'), '반대 on ' + rejected + ' marked names → shortfall "' + shortC + '" → [' + after.blockers.join(', ') + '] · "' + after.status + '" · versions ' + after.versions);
      }

      // ---------- S2: late finalize (2026-11-16, after the 11-15 deadline): what round 1 (2026-11-16) shows ----------
      // Recorded, not asserted: the owner rule says a missed window means round 1 is risk-code checks only; the code lists names
      // whenever the version date <= the round date (TargetV1Builder.roundMode). See the rehearsal doc, finding F1.
      if (phone) {
        phase = tag('S2 late finalize');await mount(page, { date: '2026-11-16', reset: true, acquired: '2026-11-15T20:00:00Z', asOf: '2026-11-15T21:00:00Z', pub: {} });
        await buildDraftByButton(page);await answerAll(page);const lf = await tryFinalize(page, {});
        const r1 = (await page.locator('[data-tv1-risk-only]').count()) ? 'risk-code checks only' : 'per-name list (' + await page.locator('[data-tv1-rebalance] tbody tr').count() + ' rows)';
        note(tag('S2'), 'finalize on 2026-11-16 → versions ' + lf.versions + ' · schedule "' + await page.locator('[data-tv1-confirm] [data-tv1-schedule]').textContent() + '" · round 1 (2026-11-16): ' + r1);
      }

      phase = tag('layout');const text = await page.locator('[data-target-v1-builder]').textContent();
      assert.ok(!/매수|매도|사세요|파세요|\bbuy\b|\bsell\b/i.test(text), 'buy/sell wording');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'horizontal overflow');
      assert.ok(!(await page.evaluate(() => JSON.stringify(localStorage))).match(/"(price|close|month_closes)"/), 'no price in device storage');
      assert.deepEqual(errors, []);assert.deepEqual(unexpected, []);
      console.log('PASS TARGET v1 finalize rehearsal ' + width);
      await context.close();
    }
    console.log(log.join('\n'));
  } catch (e) { console.log(log.join('\n'));console.log('FAIL ' + phase + ' ' + e.message);process.exitCode = 1; } finally { await browser.close(); }
})();
