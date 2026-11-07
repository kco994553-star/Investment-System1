'use strict';
// Q/G 부분 비교 on Codex's PRIVATE retained comparisons (owner 2026-11-07 「#505 실자료 부분 비교 계약 추가 인수」), development only.
//   SECTOR_QGV_PRIVATE_COMPARISONS=<abs D1 file>:<abs I1 file> node implementation/tools/web_app_sector_qgv_private.js check
// starts the development engine route with those files (the bridge refuses any file inside a Git checkout, not owner-only, over
// 8 MiB or of another schema), opens #/qgv 1.2 in a headless browser on 127.0.0.1 and checks that the screen shows each file as
// the engine wrote it: Q / G counts equal to the file, all rows of the denominator, total common 0 not hiding Q / G, D1 named
// 요소·비중 변경 and I1 named 분류 보완·비교집단 확대 (not a company improvement), versions of both sides. stdout carries PASS lines
// and counts only (no company, value or path). Not in CI; nothing is copied, stored or screenshotted.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const E = require('./web_app_sector_qgv_engine.js');

(async () => {
  const files = (process.env.SECTOR_QGV_PRIVATE_COMPARISONS || '').split(':').filter(Boolean);
  if (files.length < 1) { console.error('PRIVATE_COMPARISONS_MISSING'); process.exit(2); }
  const want = Object.fromEntries(files.map((f) => { const c = JSON.parse(fs.readFileSync(f, 'utf8')); return [c.comparison_id, c]; }));
  const eng = E.start({ env: { SECTOR_QGV_PRIVATE_COMPARISONS: files.join(':') } });
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() } }, posts: { [E.ROUTE]: eng.route } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  let pass = 0; const ok = (m) => { pass++; console.log('PASS ' + m); };
  try {
    for (const width of [1440, 390]) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'company-classification.json'] });
      const B = '[data-sq-body]', text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator(B + ' [data-k=sq-connect]').click(); await page.locator(B + ' [data-sq-role]').first().waitFor();
      await page.locator(B + ' [data-k=sq-axis-list]').click(); await page.locator(B + ' [data-sq-axis-files=READY]').waitFor();
      const listed = await page.$$eval(B + ' [data-sq-axis-file-kind=PRIVATE]', (n) => n.map((x) => x.dataset.sqAxisFile));
      assert.deepEqual(listed.sort(), Object.keys(want).sort());
      for (const [id, c] of Object.entries(want)) {
        await page.locator(B + ' [data-k="sq-axis-open-' + id + '"]').click(); await page.locator(B + ' [data-sq-axis="' + id + '"]').waitFor();
        const X = B + ' [data-sq-axis="' + id + '"]';
        assert.equal(await page.locator(X + ' [data-sq-axis-data=PRIVATE]').count(), 1);
        for (const a of ['Q', 'G']) {
          const t = await text(X + ' [data-sq-axis-summary=' + a + ']'), s0 = c.axes[a];
          for (const [label, k] of [['전 산출 ', 'before_valid'], ['후 산출 ', 'after_valid'], ['공통 ', 'COMMON_VALID'], ['새로 산출 ', 'GAINED'], ['빠짐 ', 'LOST'], ['공통 중 바뀜 ', 'changed_common']])
            assert.ok(t.includes(label + s0[k]), a + ' ' + k);
          assert.ok(t.includes('/ 전체 ' + c.denominator));
        }
        assert.ok((await text(X + ' [data-sq-axis-vt]')).includes('총점이 없어도 Q/G 비교는 따로 보임'));
        assert.equal(await page.locator(X + ' [data-sq-axis-rank=NONE]').count(), 1);
        const cause = await text(X + ' [data-sq-axis-cause]'), note = await text(X + ' [data-sq-axis-note]');
        if (c.treatment === 'SAME_INPUT_CONFIGURATION') { assert.ok(cause.startsWith('요소·비중 변경')); assert.equal(await page.locator(X + ' [data-sq-identity=input_hash][data-sq-diff=no]').count(), 1); }
        else {
          assert.ok(cause.startsWith('분류 보완·비교집단 확대') && note.includes('기업 실적이 좋아지거나 나빠졌다는 뜻이 아님'));
          assert.equal(await page.locator(X + ' [data-sq-identity=config_hash][data-sq-diff=no]').count(), 1);
          await page.selectOption(X + ' [data-k=sq-axis-show]', 'RECLASSIFIED');
          const n = Number(await page.locator(X + ' [data-sq-axis-count]').getAttribute('data-sq-axis-count'));
          assert.equal(n, c.rows.filter((r) => r.before_context.join() !== r.after_context.join()).length);
          await page.selectOption(X + ' [data-k=sq-axis-show]', 'ALL');
        }
        assert.equal(Number(await page.locator(X + ' [data-sq-axis-count]').getAttribute('data-sq-axis-count')), c.denominator, 'all rows of the denominator');
        assert.equal(await page.locator(X + ' [data-sq-axis-row]').count(), Math.min(50, c.denominator), '50 rows at a time');
        assert.ok(!/\b(null|undefined|NaN)\b/.test(await text(X)));
        ok(width + ' ' + c.treatment + ': Q ' + c.axes.Q.before_valid + '→' + c.axes.Q.after_valid + ' (common ' + c.axes.Q.COMMON_VALID + ', changed ' + c.axes.Q.changed_common + ', gained ' + c.axes.Q.GAINED + ') · G ' +
          c.axes.G.before_valid + '→' + c.axes.G.after_valid + ' (changed ' + c.axes.G.changed_common + ', gained ' + c.axes.G.GAINED + ') · rows ' + c.denominator + ' · cause and versions shown');
      }
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      ok(width + ' boundaries: origin only, no console error');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass, data_kind: 'PRIVATE', comparisons: Object.keys(want).length }));
  } finally { await browser.close(); await s.close(); await eng.close(); }
})().catch((e) => { console.error('PRIVATE_CHECK_FAILED ' + (e && e.message ? e.message.split('\n')[0] : 'error')); process.exitCode = 1; });
