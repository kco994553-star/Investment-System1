'use strict';
// 3.1.2 고른 기업의 지표 (owner 2026-11-05; screen-tech-display-live.js in the 기술적 분석 screen, route #/technical/<company>) in a
// real browser at 1440×1000 and 390×844.
//  - Real source (IS2.techDisplay.source → NONE): the block says so, draws no number; with no company it asks for one; the block
//    sits in 2-1 after 3.1.2 and before 3.1.3; the verdict band (지표 판정 보류 · NO_APPROVED_PRICE_SERIES) and the 3.1.2 table
//    stay on hold; the group ranks (1.1.8) are not drawn here, only pointed to.
//  - The SYNTHETIC fixture (Codex's own tool on synthetic bars, pinned) put in place of source(), one case at a time relabelled to
//    the chosen company's ticker (NVDA): 합성 개발 검증; 13 component cards; VALUE → 채택값 with the value as [data-ram-price] text
//    (a real 0 shows 0); DIAGNOSTIC → 진단값만 있음 with no number at all (raw_value nowhere in the page, text or attribute);
//    NOT_COMPUTED → 미산출 with its reasons; warm-up / adjustment / continuity words; 순위 없음 with its reason while the indicators
//    still show; availability NOT_VERIFIED; freshness UNKNOWN · 갱신 일정 미연결.
//  - Another company (AMD) is not in the file: NOT_IN_FILE, no number. An invalid file is refused whole (ERROR with its code).
//  - Boundaries: values only as [data-ram-price] text (assertRamOnly), no data request, no storage, no request outside the origin,
//    no console error, CSP 0, no [style], no horizontal overflow at 390. TECH_DISPLAY_SHOTS=<dir> saves screenshots.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const site = require('./web_app_test_site');
const X = require('./web_app_tech_display_fixture.js');

const NOW = '2026-10-14T21:00:00.000Z';
const SHOTS = process.env.TECH_DISPLAY_SHOTS || null;
const B = '[data-tech-display]';
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(X.sha(), X.SHA256, 'fixture unchanged');
  const P = X.display();
  const s = await site.start({});
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const tag = String(width);
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin);
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const count = (sel) => page.locator(sel).count();
      const go = async (hash) => {
        await page.evaluate(() => { location.hash = '#/prompts'; }); await page.locator('main[data-route=prompts]').waitFor();
        await page.evaluate((h) => { location.hash = h; }, hash); await page.locator('main[data-route=technical]').waitFor();
        await page.locator('[data-block="3.4"]').waitFor(); };
      const swap = (src) => page.evaluate((x) => { const I = window.IS2; I.__realDisplay = I.__realDisplay || I.techDisplay;
        I.techDisplay = Object.freeze({ ...I.__realDisplay, source: () => Promise.resolve(x) }); }, src);
      const show = async (symbol) => { await swap(X.source(X.relabel(P, { [symbol]: 'NVDA' }))); await go('#/technical/nvda');
        await page.locator(B + ' [data-tech-display-state=FOUND]').waitFor(); };
      const card = (id) => B + ' [data-display-metric=' + id + ']';
      const kinds = () => page.$$eval(B + ' [data-display-metric]', (n) => n.map((x) => x.dataset.displayMetric + ':' + x.dataset.displayKind));

      await page.goto(s.base + '#/technical'); await page.evaluate(() => window.IS2.ready); await page.locator('[data-block="3.4"]').waitFor();

      // ---------------- no company, then the real source NONE (the company list is read once for the route parameter)
      phase = tag + ' none';
      await page.locator(B + ' [data-tech-display-state=NO_COMPANY]').waitFor();
      await go('#/technical/nvda');
      await page.locator(B + ' [data-tech-display-state=NONE]').waitFor();
      const at = s.requests.length;
      const none = await text(B);
      assert.ok(none.includes('기업별 지표 자료가 아직 없습니다') && none.includes('비공개 연구 결과라 공개 화면에 연결하지 않음') && none.includes('SMA 120') && none.includes('ATR 14'), none);
      assert.ok(none.includes('그룹별 순위·필터는 1. QGV의 1.1.8 기술 조건 필터에서 따로 봅니다'), 'group pointer');
      assert.equal(await page.locator(B + ' [data-display-group] a').getAttribute('href'), '#/qgv');
      assert.equal(await count('[data-ram-price]'), 0, 'no number drawn');
      const order = await page.$$eval('[data-tech-slot="2-1"] > *', (n) => n.map((x) => x.dataset.block || (x.hasAttribute('data-tech-display') ? 'DISPLAY' : x.dataset.privatePanel || x.dataset.verdictHold || '?')));
      assert.deepEqual(order, ['NO_APPROVED_PRICE_SERIES', '3.1.1', '3.1.2', 'DISPLAY', '3.1.3', '3.1.4', 'tech-kis-chart'], 'block after 3.1.2');
      assert.ok((await text('[data-verdict-hold]')).startsWith('지표 판정 보류 · 승인·검증된 차트용 가격 계열이 아직 없습니다 (NO_APPROVED_PRICE_SERIES)'));
      assert.equal(await count('[data-indicator] [data-verdict=HOLD]'), 6, '3.1.2 table stays on hold');
      ok(tag + ' no company / real source NONE: words, no number, placed after 3.1.2; verdicts stay on hold');

      // ---------------- VALUE: every component adopted
      phase = tag + ' value';
      await show('SYN_VALUE');
      assert.ok((await text(B + ' [data-tech-display-data=SYNTHETIC]')).startsWith('합성 개발 검증 · technical-offline-display/1 · 평가일 2017-12-28'));
      assert.equal(await page.locator(B + ' [data-display-counts]').getAttribute('data-display-counts'), '13/0/0');
      assert.equal(await count(B + ' [data-display-kind=VALUE]'), 13);
      const want = { SMA_20: '240.5', SMA_60: '220.5', SMA_120: '190.5', RSI_14: '100', MACD_12_26: '7', MACD_HISTOGRAM_12_26_9: '0', ATR_14: '2' };
      for (const [id, v] of Object.entries(want)) assert.equal(await page.locator(card(id) + ' [data-display-value] [data-ram-price]').textContent(), v, id);
      const sma = await text(card('SMA_20'));
      for (const w of ['SMA 20', '채택값', '주당 · 원 통화 USD', '관측 20 / 20세션', '초기 봉 충족 · 최소 20 · 관측 20', '최근 N봉 창', '세션 연속', '의존 구간 무분할 문서 확인']) assert.ok(sma.includes(w), 'SMA_20 card has ' + w);
      assert.ok((await text(card('EMA_20'))).includes('전체 보유 이력으로 시작값 (시작 2017-01-03)'));
      const rank = await text(B + ' [data-display-rank]');
      assert.equal(rank, '순위 없음 · 고정 증권 ID 없음 · 순위를 매기지 않음 · 지표는 순위 없이도 표시');
      assert.equal(await page.locator(B + ' [data-display-availability]').getAttribute('data-display-availability'), 'NOT_VERIFIED');
      assert.equal(await text(B + ' [data-display-stale=UNKNOWN][data-na=UPDATE_SCHEDULE_NOT_CONNECTED]'), '최신 여부 알 수 없음 · 갱신 일정 미연결');
      assert.ok((await text(B + ' [data-display-facts]')).includes('보유 일봉 250봉 · 2017-01-03 ~ 2017-12-28'));
      assert.ok((await text('[data-verdict-hold]')).startsWith('지표 판정 보류'), 'the verdict band is unchanged');
      assert.equal(await count('[data-indicator] [data-verdict=HOLD]'), 6);
      await site.assertRamOnly(page, ['240.5', '220.5', '190.5'], tag);
      if (SHOTS) await page.locator(B).screenshot({ path: path.join(SHOTS, 'td-' + tag + '-value.png') });
      ok(tag + ' VALUE: 13 adopted values as RAM text (a real 0 is 0), 순위 없음 with reason, availability / freshness words');

      // ---------------- DIAGNOSTIC: no number at all
      phase = tag + ' diagnostic';
      await show('SYN_IDENTITY');
      assert.equal(await page.locator(B + ' [data-display-counts]').getAttribute('data-display-counts'), '0/13/0');
      assert.equal(await count(B + ' [data-ram-price]'), 0, 'a diagnostic draws no number');
      for (const id of ['SMA_20', 'RSI_14', 'ATR_14']) {
        const t = await text(card(id));
        assert.ok(t.includes('진단값만 있음') && t.includes('진단값 1개 있음') && t.includes('증권 신원 미확인'), t);
      }
      const html = await page.content();
      assert.ok(!html.includes('240.8125') && !html.includes('190.8125'), 'raw_value nowhere in the page');
      assert.ok((await text(B + ' [data-display-facts]')).includes('신원 미확인'));
      assert.ok((await text(B + ' [data-display-counts]')).startsWith('채택값 0 · 진단값만 있음 13 · 미산출 0 · 진단값은 개수만'));
      ok(tag + ' DIAGNOSTIC: 진단값만 있음 counted, no number, raw_value nowhere');

      phase = tag + ' split';
      await show('SYN_SPLIT120');
      assert.equal(await page.locator(B + ' [data-display-counts]').getAttribute('data-display-counts'), '7/6/0');
      assert.deepEqual(await kinds(), ['SMA_5:VALUE', 'SMA_20:VALUE', 'SMA_60:VALUE', 'SMA_120:VALUE', 'EMA_20:DIAGNOSTIC', 'RSI_14:DIAGNOSTIC', 'MACD_12_26:DIAGNOSTIC',
        'MACD_SIGNAL_9:DIAGNOSTIC', 'MACD_HISTOGRAM_12_26_9:DIAGNOSTIC', 'BOLL_MIDDLE_20:VALUE', 'BOLL_UPPER_20_2:VALUE', 'BOLL_LOWER_20_2:VALUE', 'ATR_14:DIAGNOSTIC']);
      assert.equal(await count(card('EMA_20') + ' [data-ram-price]'), 0);
      assert.ok((await text(card('EMA_20'))).includes('무분할 근거가 의존 구간을 덮지 못함'));
      assert.equal(await page.locator(card('EMA_20') + ' [data-adjustment]').getAttribute('data-adjustment'), 'UNCONFIRMED');
      assert.equal(await page.locator(card('SMA_120') + ' [data-ram-price]').textContent(), '190.5');
      ok(tag + ' split evidence for the last 120 bars: rolling adopted, recursive 진단값만 있음 (adjustment UNCONFIRMED)');

      // ---------------- NOT_COMPUTED
      phase = tag + ' not computed';
      await show('SYN_FLAT35');
      assert.ok((await text(card('SMA_120'))).includes('미산출 · 초기 봉 부족'));
      assert.equal(await page.locator(card('SMA_120') + ' [data-warmup]').getAttribute('data-warmup'), 'INSUFFICIENT');
      assert.ok((await text(card('RSI_14'))).includes('미산출 · 가격 변화 0 · 정의 불가'));
      assert.equal(await page.locator(card('RSI_14') + ' [data-warmup]').getAttribute('data-warmup'), 'READY');
      assert.equal(await page.locator(card('MACD_12_26') + ' [data-ram-price]').textContent(), '0', 'flat MACD is a real 0');
      assert.equal(await count(card('SMA_120') + ' [data-ram-price]'), 0, 'a null is never 0');
      await show('SYN_NOHIGH');
      assert.ok((await text(card('ATR_14'))).includes('미산출 · 고가·저가 결손'));
      assert.equal(await page.locator(card('ATR_14') + ' [data-warmup]').getAttribute('data-warmup'), 'NOT_EVALUATED');
      assert.equal(await count(B + ' [data-display-kind=VALUE]'), 12);
      await show('SYN_EMPTY');
      assert.equal(await page.locator(B + ' [data-display-counts]').getAttribute('data-display-counts'), '0/0/13');
      assert.equal(await count(B + ' [data-ram-price]'), 0);
      assert.ok((await text(card('SMA_5'))).includes('미산출 · 보유 일봉에 빠진 거래일'));
      assert.ok((await text(card('SMA_5'))).includes('세션 결손'));
      if (SHOTS) await page.locator(B).screenshot({ path: path.join(SHOTS, 'td-' + tag + '-empty.png') });
      ok(tag + ' NOT_COMPUTED: 미산출 with reasons, warm-up INSUFFICIENT / READY / NOT_EVALUATED, empty series');

      // ---------------- another company: not in the file
      phase = tag + ' not in file';
      await swap(X.source(X.relabel(P, { SYN_VALUE: 'NVDA' }))); await go('#/technical/amd');
      await page.locator(B + ' [data-tech-display-state=NOT_IN_FILE]').waitFor();
      assert.ok((await text(B)).includes('이 파일에 AMD 계열이 없습니다'));
      assert.equal(await count('[data-ram-price]'), 0);
      ok(tag + ' a company not in the file: NOT_IN_FILE, no number');

      // ---------------- invalid file refused whole
      phase = tag + ' invalid';
      const bad = X.relabel(P, { SYN_VALUE: 'NVDA' }); bad.series[0].metrics.SMA_20.value = 1;
      await swap(X.source(bad)); await go('#/technical/nvda');
      await page.locator(B + ' [data-tech-display-state=ERROR][data-na=VALUE_NOT_RAW]').waitFor();
      assert.ok((await text(B)).includes('지표 파일이 계약과 달라 파일 전체를 쓰지 않습니다'));
      assert.equal(await count('[data-ram-price]'), 0);
      assert.equal(await count('[data-block="3.1.3"]'), 1, 'the rest of the screen stays');
      ok(tag + ' invalid file refused whole');

      // ---------------- layout and boundaries
      phase = tag + ' boundaries';
      await show('SYN_SPLIT120');
      assert.equal(await count('[style]'), 0, 'no style attribute');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'no horizontal overflow');
      if (width < 720) {
        const cols = await page.$$eval(B + ' [data-display-metric]', (n) => new Set(n.map((x) => Math.round(x.getBoundingClientRect().left))).size);
        assert.equal(cols, 1, 'one column on a phone');
      }
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      assert.deepEqual(s.requests.slice(at).map((r) => r.name).filter((n) => n.endsWith('.json')), [], 'no data request after the company list');
      const st = await site.storage(page); assert.deepEqual([st.local, st.session], [0, 0]);
      assert.equal(await page.evaluate(() => window.__csp), 0);
      ok(tag + ' boundaries: no request, no storage, no console error, CSP 0, no overflow');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
