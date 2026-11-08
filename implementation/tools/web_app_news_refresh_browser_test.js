'use strict';
// Feature 5.2.7 원천별 갱신 기록 (owner 2026-11-05) on the existing 4. 뉴스 screen (#/news, screen-news-live.js + news-refresh.js) in a
// real browser at 1440 and 390. The public lists are served through the real layer (IS2.data.list, old readers' validation), with
// news-signals.json = the SYNTHETIC schema 2 file Codex's #483 merge wrote (tests/fixtures/news_signals_refresh_v2_synthetic.json):
//  - GDELT FAILED HTTP_429 + IR UPDATED: both source cards drawn; IR 갱신 with its counts and its rows in the 5.2.1 list (the new
//    IR releases), GDELT 실패 (HTTP_429) · 이전 자료 유지 with 이월 시작 and its carried rows still listed; the per-view line says
//    GDELT 이전 자료 유지 / IR 새 뉴스 반영; 수정 · 중복 미제공 (never 0); the overall line names the partial failure.
//  - Schema 1 copy → UNRECORDED, schema 2 without a run → NO_RUN, news-signals.json 404 → NONE: words, no source card, the SEC /
//    DART rows stay.
//  - source() replaced with a synthetic payload: 합성 개발 검증 shown; an injected payload that breaks the contract → INVALID with its
//    code and no number; the rest of the screen stays.
//  - 5.2.2 요약 · 5.2.3 영향 · 5.2.6 컨센서스 stay 미산출 with their reasons.
//  - Boundaries: requests only to the layer's public files on the same origin, no console error, no CSP violation, no [style], no
//    storage, no horizontal overflow at 390.
// Synthetic data only.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const site = require('./web_app_test_site');
const X = require('./web_app_news_fixture.js');

const FX = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/news_signals_refresh_v2_synthetic.json'), 'utf8'));
const NOW = new Date(X.NOW).toISOString();
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'macro-evidence.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json'];
const LISTS = ['sec-disclosures.json', 'news-signals.json', 'dart-disclosures.json'];
const MIXED = FX.cases.gdelt_429_ir_updated.payload;
const FULL = { 'sec-disclosures.json': { json: X.sec() }, 'news-signals.json': { json: MIXED }, 'dart-disclosures.json': { json: X.dart() } };
const B = '[data-news-source-refresh]';
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: FULL });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const set = (fx) => { for (const n of LISTS) s.fixture(n, Object.hasOwn(fx, n) ? fx[n] : null); };
  async function context(width, { allow404 = UNPUBLISHED } = {}) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404 });
    return { ctx, page, seen };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.textContent);
  const count = (page, sel) => page.locator(sel).count();
  async function open(page, hash = '#/news') {
    await page.goto(s.base + hash); await page.locator('main[data-route=news]').waitFor();
    await page.locator(B).first().waitFor();
  }
  async function boundaries(page, seen, label) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute ' + await page.evaluate(() => [...document.querySelectorAll('[style]')].map((e) => e.outerHTML.slice(0, 200)).join(' | ')));
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
    assert.deepEqual(seen.errors, [], label + ': no console or page error');
    const files = await page.evaluate(() => [...window.IS2.data.FILES]);
    const json = seen.requests.map((u) => new URL(u).pathname.slice(1)).filter((n) => n.endsWith('.json'));
    assert.deepEqual(json.filter((n) => !files.includes(n)), [], label + ': every data request is a public file of the layer');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    const st = await site.storage(page);
    assert.deepEqual([Object.keys(st.localItems), st.session, st.idb], [[], 0, 0], label + ': nothing stored');
  }
  const cellSel = (src, key) => B + ' td[data-refresh-source=' + src + '][data-source-cell=' + key + ']';
  const cell = (page, src, key) => text(page, cellSel(src, key));
  async function notComputed(page, label) {
    for (const [id, words] of [['5.2.2', '5줄 요약 미산출'], ['5.2.3', '모두 미산출'], ['5.2.6', '컨센서스 자료 미연결']]) {
      const t = await text(page, '[data-block="' + id + '"]');
      assert.ok(t.includes(words), label + ': ' + id + ' says ' + words);
      assert.ok(await count(page, '[data-block="' + id + '"] [data-prep]') >= 1, label + ': ' + id + ' is 준비 중 with its missing inputs');
    }
    assert.equal(await count(page, '[data-news-five=NOT_AVAILABLE] [data-na=NOT_COMPUTED]'), 5, label + ': five summary lines 미산출');
  }
  try {
    for (const width of [1440, 390]) {
      phase = width + ' GDELT 429 + IR UPDATED';
      set(FULL);
      const { ctx, page, seen } = await context(width);
      await open(page);
      await page.locator('[data-timeline]').waitFor();
      assert.equal(await page.locator(B).getAttribute('data-news-source-refresh'), 'RECORDED');
      assert.equal(await count(page, '[data-news-refresh-data]'), 0, phase + ': the layer path carries no synthetic mark of its own');
      assert.equal(await page.locator('[data-news-source-refresh-overall]').getAttribute('data-news-source-refresh-overall'), 'PARTIAL_FAILED');
      assert.match(await text(page, '[data-news-source-refresh-overall]'), /이번 실행 2026-10-14 02:30 UTC · 일부 원천·회사 실패 · 응답한 원천은 그대로 표시/);
      const cards = await page.locator(B + ' [data-news-source-row]').evaluateAll((n) => n.map((x) => [x.dataset.newsSourceRow, x.dataset.newsSourceResult]));
      assert.deepEqual(cards, [['GDELT', 'FAILED'], ['IR', 'UPDATED']], phase + ': both sources are drawn');
      const want = {
        GDELT: { last_success_at: '2026-10-13 00:58 UTC', last_attempt_at: '2026-10-14 02:30 UTC', last_result: '실패 (HTTP_429) · 이전 자료 유지', companies: '성공 0 · 실패 1 · 미실행 18', new_items: '0건', items_carried_from: '2026-10-13 00:58 UTC 수집분' },
        IR: { last_success_at: '2026-10-14 02:29 UTC', last_attempt_at: '2026-10-14 02:30 UTC', last_result: '갱신', companies: '성공 10 · 실패 0 · 미실행 0', new_items: '2건', items_carried_from: '이월 없음 · 모든 회사 응답' } };
      for (const [src, cells] of Object.entries(want)) for (const [k, v] of Object.entries(cells)) assert.equal(await cell(page, src, k), v, phase + ': ' + src + ' ' + k);
      for (const src of ['GDELT', 'IR']) for (const k of ['revisions', 'duplicates']) {
        assert.equal(await cell(page, src, k), '미제공 · 공개 파일에 없음', phase + ': ' + src + ' ' + k + ' 미제공, never 0');
        assert.equal(await page.locator(cellSel(src, k)).getAttribute('data-na'), 'NA');
      }
      // The failed source does not hide the one that answered: IR's new releases and GDELT's carried rows are both listed.
      const listed = await page.locator('[data-timeline] > li[data-row][data-channel=NEWS]').evaluateAll((n) => n.map((x) => x.dataset.source));
      const items = MIXED.items.filter((i) => i.relation === 'NONE');
      assert.equal(listed.filter((x) => x === 'IR').length, new Set(items.filter((i) => i.source === 'IR').map((i) => i.group_id)).size, phase + ': every IR event is listed');
      assert.equal(listed.filter((x) => x === 'GDELT').length, new Set(items.filter((i) => i.source === 'GDELT').map((i) => i.group_id)).size, phase + ': GDELT carried events stay listed');
      const links = await page.locator('[data-timeline] [data-news-link]').evaluateAll((n) => n.map((x) => x.getAttribute('href')));
      for (const l of ['https://news.microsoft.com/synthetic/surface', 'https://nvidianews.nvidia.com/synthetic/platform']) assert.ok(links.includes(l), phase + ': the new IR release ' + l + ' is shown');
      assert.ok((await text(page, '[data-timeline]')).includes('Microsoft announces quarterly dividend increase'), phase + ': the corrected title is the one shown');
      assert.match(await text(page, '[data-news-refresh=GDELT]'), /GDELT · 이전 자료 유지 · 마지막 성공 2026-10-13 00:58 UTC · 최근 갱신 실패\(GDELT HTTP_429, 2026-10-14 02:30 UTC\)$/);
      assert.match(await text(page, '[data-news-refresh=IR]'), /회사 IR · 새 뉴스 반영 · 확인 2026-10-14 02:30 UTC/);
      assert.equal(await page.locator('[data-news-refresh-badge]').getAttribute('data-news-refresh-badge'), 'PARTIAL_FAILED');
      await notComputed(page, phase);
      assert.match(await text(page, B + ' [data-news-source-row=GDELT]'), /GDELT실패/); assert.match(await text(page, B + ' [data-news-source-row=IR]'), /회사 IR갱신/);
      // The table fits its column (no inner horizontal scroll at 390 either).
      assert.ok(await page.locator(B + ' [data-news-source-table]').evaluate((e) => e.scrollWidth <= e.clientWidth + 1), phase + ': the table needs no horizontal scroll');
      await boundaries(page, seen, phase);
      await page.locator(B).scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(__dirname, 'web_app_news_refresh_' + width + '.png'), fullPage: false });
      await ctx.close(); pass++;
    }
    for (const [name, payload, kind, words] of [['schema 1 copy', X.newsV1(), 'UNRECORDED', '원천별 갱신 기록 없음 · 이전 형식 파일 (schema 1)'],
      ['schema 2 without a run', X.newsNoRun(), 'NO_RUN', '원천별 갱신 기록 없음 · 이 파일은 수집 없이 만들어짐 (refresh 없음)']]) {
      phase = '1440 ' + name;
      set({ ...FULL, 'news-signals.json': { json: payload } });
      const { ctx, page, seen } = await context(1440);
      await open(page);
      assert.equal(await page.locator(B).getAttribute('data-news-source-refresh'), kind);
      assert.equal(await text(page, B + ' [data-na=' + kind + ']'), words);
      assert.equal(await count(page, B + ' [data-news-source-row]'), 0, phase + ': no source card');
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    {
      phase = '390 news-signals.json 404';
      set({ ...FULL, 'news-signals.json': { status: 404, body: 'not found' } });
      const { ctx, page, seen } = await context(390, { allow404: [...UNPUBLISHED, 'news-signals.json'] });
      await open(page);
      assert.equal(await page.locator(B).getAttribute('data-news-source-refresh'), 'NONE');
      assert.ok((await text(page, B)).includes('뉴스 파일이 없어 원천별 갱신 기록을 보일 수 없습니다'));
      assert.equal(await count(page, B + ' [data-news-source-row]'), 0);
      await page.locator('[data-timeline]').waitFor();
      assert.ok(await count(page, '[data-timeline] > li[data-channel=DISCLOSURE]') > 0, phase + ': SEC / DART rows stay');
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    for (const width of [1440, 390]) {
      phase = width + ' source() replaced (synthetic, then invalid)';
      set(FULL);
      const { ctx, page, seen } = await context(width);
      await open(page);
      const inject = (p) => page.evaluate((x) => { const I = window.IS2, real = I.newsRefresh;
        I.newsRefresh = Object.freeze({ ...real, source: () => Object.freeze({ state: 'OK', payload: x, data_kind: 'SYNTHETIC', text: '' }) }); }, p);
      const repaint = async () => { await page.evaluate(() => { location.hash = '#/news/nvda'; }); await page.locator('[data-center-code]').waitFor(); await page.locator(B).first().waitFor(); };
      await inject(FX.cases.both_no_new_items.payload); await repaint();
      assert.equal(await text(page, '[data-news-refresh-data=SYNTHETIC]'), '합성 개발 검증 · 실제 수집 결과 아님');
      assert.ok(await page.locator('[data-news-refresh-data=SYNTHETIC]').isVisible(), phase + ': the synthetic mark is visible');
      assert.deepEqual(await page.locator(B + ' [data-news-source-row]').evaluateAll((n) => n.map((x) => x.dataset.newsSourceResult)), ['NO_NEW_ITEMS', 'NO_NEW_ITEMS']);
      assert.equal(await cell(page, 'GDELT', 'last_result'), '새 항목 없음');
      const bad = structuredClone(MIXED); bad.refresh.sources.IR.new_items = 0;
      await inject(bad); await page.evaluate(() => { location.hash = '#/news'; }); await page.locator('[data-news-search]').waitFor(); await page.locator(B).first().waitFor();
      await page.waitForFunction(() => document.querySelector('[data-news-source-refresh]').dataset.newsSourceRefresh === 'INVALID');
      assert.match(await text(page, B), /원천별 갱신 기록이 계약과 달라 이 칸을 쓰지 않습니다 · RESULT_MISMATCH \$\.refresh\.sources\.IR\.last_result/);
      assert.equal(await count(page, B + ' [data-news-source-row]'), 0, phase + ': a refused block draws no number');
      await page.locator('[data-timeline]').waitFor();
      await notComputed(page, phase);
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    console.log('web_app_news_refresh_browser_test: PASS (' + pass + ' contexts: 429+IR 1440/390, schema 1, no run, 404, injected 1440/390)');
  } catch (e) {
    console.error('web_app_news_refresh_browser_test: FAIL at ' + phase);
    throw e;
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
