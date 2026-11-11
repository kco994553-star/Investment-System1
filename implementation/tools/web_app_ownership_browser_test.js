'use strict';
// 5.1.1 기업 중심 관계 · 5.1.2 연결 근거 · company page 관계 lines (IS2.ownershipView + IS2.ownershipScreen) in a real browser at 1440,
// 390 and 200 % zoom (1440 / 2 = 720 CSS px at device scale 2). Codex #531's synthetic company-ownership-view/1 cases, with the centre
// entity's code row mapped to NASDAQ:NVDA so the test site's company list has it (test-made mapping; the counterparties stay
// SYN-B / SYN-C, which are not in the list). Checks:
//  - no checked view → the 5.1 centre keeps 「관계 자료 미연결」 (REL_SOURCE) and the company page adds nothing;
//  - a view that the reader refuses never reaches RAM; a checked view in RAM draws the block: the five lists apart (모회사 / 자회사 /
//    보유 지분 / 주주 / 13F), the state line, the dates and 「전체 관계 수 미상」; counterparties outside the company list have no
//    link and say 「기업 페이지 없음」; share capital is its own line with basis, class and date; 5.1.2 shows the relationship id
//    and evidence ids;
//  - keyboard: Tab reaches each list's summary, Enter opens it; the unresolved-name case shows the name with 「목록에 없는 대상」
//    and no row; not collected / not found in scope keep their own words;
//  - the company page (4. 이 기업 소식) shows the compact block under the news rows (the view stays in RAM across a route change,
//    gone after a reload); nothing stored; no horizontal overflow.
// Synthetic only.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const site = require('./web_app_test_site');
const X = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'research', 'company_ownership', 'synthetic.json'), 'utf8'));
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'macro-evidence.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json',
  'sec-disclosures.json', 'news-signals.json', 'dart-disclosures.json'];
const CODE = 'NASDAQ:NVDA';
function caseView(id) {
  const v = JSON.parse(JSON.stringify(X.cases.find((c) => c.case_id === id).expected_view));
  const e = v.entities.find((x) => x.entity_id === v.entity_context.entity_id); e.company_ids = [CODE];
  return v;
}
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: {} });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.innerText);
  const put = (page, v) => page.evaluate((x) => { const r = window.IS2.ownershipView.validate(x); if (r.ok) window.IS2.ownershipView.ram.put(r.value); return r.ok ? 'OK' : r.code; }, v);
  const noOverflow = (page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  try {
    for (const [label, opts] of [['1440', { viewport: { width: 1440, height: 1000 } }], ['390', { viewport: { width: 390, height: 844 } }],
      ['200%', { viewport: { width: 720, height: 500 }, deviceScaleFactor: 2 }]]) {
      const ctx = await browser.newContext(opts), page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      phase = label + ' no view';
      await page.goto(s.origin + '/#/news/nvda');
      await page.locator('[data-center-code="' + CODE + '"]').waitFor({ timeout: 30000 });
      assert.equal(await page.locator('[data-news-center] [data-na=REL_SOURCE]').count(), 1, label + ': 관계 자료 미연결 without a view');
      assert.equal(await page.locator('[data-own-block]').count(), 0);
      const store0 = await page.evaluate(() => Object.keys(localStorage).sort());
      phase = label + ' refused';
      const bad = caseView('explicit_path_duplicate_cycle'); bad.relationship_denominator = 12;
      assert.equal(await put(page, bad), 'COVERAGE_CLAIMED');
      assert.equal(await page.locator('[data-own-block]').count(), 0, label + ': a refused view never draws');
      phase = label + ' view';
      assert.equal(await put(page, caseView('explicit_path_duplicate_cycle')), 'OK');
      await page.locator('[data-own-block="SYN-A"]').waitFor({ timeout: 10000 });
      assert.equal(await page.locator('[data-news-center] [data-na=REL_SOURCE]').count(), 0, label + ': the block replaces 관계 자료 미연결');
      assert.deepEqual(await page.locator('[data-own-list]').evaluateAll((e) => e.map((x) => x.dataset.ownList)), ['parents', 'subsidiaries', 'holdings', 'holders', 'discretion']);
      assert.match(await text(page, '[data-own-state]'), /확인된 3개 · 전체 목록 미확인/);
      assert.match(await text(page, '[data-own-block]'), /전체 관계 수 미상 · 커버리지 계산 안 함/);
      assert.match(await text(page, '[data-own-block]'), /과거 시점 재현\(PIT\) 아님/);
      // Keyboard: the 보유 지분 summary by Tab, Enter opens it.
      await page.locator('[data-own-list=holdings] > summary').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('[data-own-list=holdings]').evaluate((e) => e.open), true, label + ': Enter opens the list');
      const hold = page.locator('[data-own-list=holdings] [data-own-rel]').first();
      assert.match(await hold.innerText(), /합성 자회사 · 기업 목록에 없음 · 기업 페이지 없음/);
      assert.equal(await hold.locator('a').count(), 0, label + ': no page for a company outside the list');
      assert.match(await hold.locator('[data-own-obs=share]').innerText(), /^지분율 .*%/);
      assert.match(await hold.locator('[data-own-evidence]').innerText(), /^연결 근거 · 관계 ID ownership_[0-9a-f]+ · 근거 e1/);
      await page.locator('[data-own-list=parents] > summary').click();
      assert.equal(await page.locator('[data-own-list=parents] [data-own-relative=INCOMING]').count(), 1, label + ': the parent is an incoming fact');
      assert.match(await page.locator('[data-own-empty=holders]').textContent(), /^전달된 관계 없음 · 없다는 확인이 아님$/);
      assert.ok(await noOverflow(page), label + ': no horizontal overflow');
      phase = label + ' other states';
      for (const [id, word] of [['not_collected', /관계 자료 없음 · 수집 전/], ['not_found_in_reviewed_scope', /검토한 범위에서 찾지 못함/]]) {
        await page.evaluate(() => window.IS2.ownershipView.ram.clear()); assert.equal(await put(page, caseView(id)), 'OK');
        await page.locator('[data-own-state="' + X.cases.find((c) => c.case_id === id).expected_view.collection_state + '"]').waitFor();
        assert.match(await text(page, '[data-own-state]'), word, id);
      }
      await page.evaluate(() => window.IS2.ownershipView.ram.clear()); assert.equal(await put(page, caseView('unresolved_unlisted_name')), 'OK');
      await page.locator('[data-own-unresolved]').waitFor();
      assert.match(await text(page, '[data-own-unresolved]'), /Unresolved same-name unlisted company · 목록에 없는 대상 · 기업 페이지 없음/);
      assert.equal(await page.locator('[data-own-rel]').count(), 0, label + ': an unresolved name makes no row');
      phase = label + ' company page';
      await page.evaluate(() => window.IS2.ownershipView.ram.clear()); assert.equal(await put(page, caseView('direct_ownership_and_parent')), 'OK');
      await page.goto(s.origin + '/#/company/nvda');
      await page.locator('[data-own-slot="' + CODE + '"]').waitFor({ state: 'attached', timeout: 30000 });
      await page.locator('[data-own-slot] [data-own-block][data-own-compact=true]').waitFor({ timeout: 10000 });
      assert.equal(await page.locator('[data-own-slot] [data-own-evidence]').count(), 0, label + ': compact lines leave the evidence to 5.1.2');
      assert.ok(await noOverflow(page), label + ': company page, no horizontal overflow');
      assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).sort()), store0, label + ': nothing stored');
      await page.reload(); await page.locator('[data-own-slot="' + CODE + '"]').waitFor({ state: 'attached', timeout: 30000 });
      assert.equal(await page.locator('[data-own-slot] [data-own-block]').count(), 0, label + ': after a reload no view is left (RAM only)');
      assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
      assert.deepEqual(seen.errors, [], label + ': no console or page error');
      await ctx.close(); pass++;
      console.log('PASS ' + label);
    }
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (error) {
    console.log('FAIL at ' + phase + ': ' + (error && error.stack || error));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
