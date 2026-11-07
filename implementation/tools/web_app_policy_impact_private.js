'use strict';
// 4.5 정책·지정학 on Codex's PRIVATE real output (owner 2026-11-07; #509 REAL_REVIEWED handoff), development only.
//   [POLICY_IMPACT_PRIVATE_NAV=<abs path>] optional: Codex's private policy-impact-navigation/1 for that view (#509 c2ae92a0 handoff,
//   same file rules); then the official / Korean titles are checked too.
//   POLICY_IMPACT_PRIVATE_VIEW=<abs path> node implementation/tools/web_app_policy_impact_private.js serve
//       → a 127.0.0.1 site serving that file as policy-impact.json (Ctrl-C stops)
//   POLICY_IMPACT_PRIVATE_VIEW=<abs path> node implementation/tools/web_app_policy_impact_private.js check
//       → the screen checks on the real file in a headless browser; prints PASS lines and counts only.
// The file must be a policy-impact-view/1 with data_kind REAL_REVIEWED, accepted whole by the reader, outside every Git checkout,
// owner-only (mode 600), at most 8 MiB. Nothing is copied, published, stored or screenshotted; stdout carries no title, URL, company
// or text from the file. Not in CI (the public site has no such file; its absence is 자료 없음, never a stand-in). The company
// registry is the test site's synthetic one (qgv_v2_fixture.js), which carries the same existing company id.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const P = require('../src/investment_system/product/web_app/policy-impact.js');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');

const FILE = 'policy-impact.json', NAV_FILE = 'policy-impact-navigation.json';
const fail = (code) => { console.error('PRIVATE_VIEW_REFUSED ' + code); process.exit(2); };
function readFileRules(file) {
  if (!file || !path.isAbsolute(file)) fail('PATH_NOT_ABSOLUTE');
  let st; try { st = fs.lstatSync(file); } catch (_) { fail('NOT_FOUND'); }
  if (!st.isFile()) fail('NOT_A_FILE');
  if ((st.mode & 0o077) !== 0) fail('NOT_OWNER_ONLY');
  if (st.size > 8 * 1024 * 1024) fail('TOO_LARGE');
  for (let d = path.dirname(fs.realpathSync(file)); ; d = path.dirname(d)) { if (fs.existsSync(path.join(d, '.git'))) fail('INSIDE_GIT_CHECKOUT'); if (path.dirname(d) === d) break; }
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (_) { fail('NOT_JSON'); }
}
async function readNav(file, json) {
  if (!file) return null;
  const n = readFileRules(file), r = await P.validateNavigation(n, json);
  if (!r.ok) fail('NAV ' + r.code + ' ' + r.path);
  if (n.data_kind !== 'REAL_REVIEWED') fail('NAV_NOT_REAL_REVIEWED');
  return n;
}
function readPrivate(file) {
  const json = readFileRules(file);
  const r = P.validate(json); if (!r.ok) fail(r.code + ' ' + r.path);
  if (r.value.bundle.data_kind !== 'REAL_REVIEWED') fail('NOT_REAL_REVIEWED');
  return json;
}

async function check(json, nav) {
  const { chromium } = require('playwright');
  const v = P.view(P.validate(json).value), nix = P.navIndex(nav);
  const fixtures = { 'sec-qgv2.json': { json: F.strictPayload() }, [FILE]: { json } }; if (nav) fixtures[NAV_FILE] = { json: nav };
  const s = await site.start({ fixtures });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const B = '[data-policy-body]';
  let pass = 0; const ok = (name) => { pass++; console.log('PASS ' + name); };
  try {
    for (const width of [1440, 390, 320]) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: ['sec-public-inputs.json', 'sec-universe-shares.json', 'forward-validation-ledger.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence.json', 'dart-financials.json', 'company-classification.json', 'news-signals.json', 'sec-disclosures.json', 'dart-disclosures.json', ...(nav ? [] : [NAV_FILE])] });
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      await page.goto(s.base + '#/macro'); await page.evaluate(() => window.IS2.ready);
      await page.locator(B + ' [data-k=pol-open]').click(); await page.locator(B + ' [data-pol-card]').first().waitFor();
      const ids = await page.$$eval(B + ' [data-pol-card]', (n) => n.map((x) => x.dataset.polCard));
      assert.deepEqual(ids, v.order.map((p) => p.policy_id), 'engine order');
      assert.ok((await text(B + ' [data-pol-band]')).includes('실자료 · 검토 기록 있음'));
      for (const id of ids) assert.equal(await page.locator(B + ' [data-pol-card="' + id + '"] [data-pol-historical]').innerText(), '역사 사례 · 현재 상태 미확인');
      ok(width + ' list: ' + ids.length + ' policies, engine order, 실자료, every one 역사 사례 · 현재 상태 미확인');
      for (const p of v.order) {
        await page.evaluate((h) => { location.hash = h; }, '#/macro/policy/' + encodeURIComponent(p.policy_id)); await page.locator(B + ' [data-pol-detail]').waitFor();
        await page.$$eval(B + ' details', (n) => n.forEach((d) => { d.open = true; }));
        const all = await text(B);
        assert.ok(!/영향 없음(?!이라는 뜻이 아님)/.test(all), 'never 영향 없음'); assert.ok(!/\b(null|undefined|NaN)\b/.test(all));
        assert.ok(all.includes('AI 독립 원문 대조 · 사람 검토 아님'), 'review method shown');
        const t = P.titleState(p.current, nix);
        if (t.state === 'OFFICIAL') {
          assert.equal(await page.locator(B + ' .pol-detail-title').innerText(), t.official, 'official title from the sidecar');
          assert.equal(await page.locator(B + ' [data-pol-title-state=OFFICIAL]').count(), 1); assert.ok((await text(B + ' [data-pol-title-ko]')).includes('공식 제목 아님'));
        } else if (p.current.title === p.policy_id) assert.equal(await page.locator(B + ' [data-pol-title-state=ID_ONLY]').count(), 1, 'id-only title said so');
        assert.ok((await text(B + ' [data-pol-identifier]')).includes(p.policy_id), 'identifier shown apart');
        const links = await page.$$eval(B + ' a[data-pol-external]', (n) => n.map((a) => [a.protocol, a.target, a.rel]));
        assert.ok(links.length >= 1 && links.every(([pr, t, r]) => pr === 'https:' && t === '_blank' && r === 'noopener noreferrer'), 'source document links');
        const wide = await page.$$eval('[data-section="3-5"] *', (els) => els.filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > window.innerWidth + 1 && !e.closest('.scroll'); }).length);
        assert.equal(wide, 0, width + ': nothing in 3.5 past the viewport');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth) <= 0, width + ': detail page overflow');
        if (!p.exposures.length) assert.ok((await text(B + ' [data-pol-no-exposure]')).includes('연결 근거 미확인 (영향 없음이라는 뜻이 아님)'));
        if (p.current.policy_type === 'INDUSTRIAL_SUBSIDY') {
          assert.ok((await text(B + ' [data-pol-subsidy]')).includes('실제 지급 아님')); assert.ok(!all.includes('지급 확인'), 'a final award is not a disbursement');
          assert.equal(await page.locator(B + ' [data-pol-hypothesis]').count(), p.hypotheses.length);
        }
        ok(width + ' detail ' + p.current.policy_type + ' (title ' + t.state + '): exposures ' + p.exposures.length + ', hypotheses ' + p.hypotheses.length + ', source links ' + links.length + (p.exposures.length ? '' : ', 연결 근거 미확인 (not 영향 없음)'));
      }
      const withCompany = v.order.find((p) => p.exposures.length);
      if (withCompany) {
        await page.evaluate((h) => { location.hash = h; }, '#/macro/policy/' + encodeURIComponent(withCompany.policy_id)); await page.locator(B + ' [data-pol-detail]').waitFor();
        await page.locator(B + ' [data-pol-group=LINKED] a[data-pol-company]').first().click(); await page.locator('main[data-route=company]').waitFor();
        const card = '[data-pol-company-card]'; await page.locator(card + ' summary').click(); await page.locator(card + ' [data-pol-company-summary]').waitFor();
        assert.equal(await page.locator(card + ' [data-pol-company-summary]').getAttribute('data-pol-company-summary'), '1');
        await page.goBack(); await page.locator(B + ' [data-pol-detail]').waitFor();
        ok(width + ' exposure → existing company detail → 관련 정책 1건 → 뒤로');
      }
      const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert.ok(over <= 0, width + ': page overflow ' + over + ' px');
      assert.deepEqual(seen.outside, [], 'no request left the origin'); assert.deepEqual(seen.errors, []);
      ok(width + ' boundaries: origin only, no console error, page overflow ' + over + ' px');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass, data_kind: 'REAL_REVIEWED', policies: v.order.length, official_titles: nix.titles.size, reviewed_news_links: nix.count }));
  } finally { await browser.close(); await s.close(); }
}

(async () => {
  const mode = process.argv[2], json = readPrivate(process.env.POLICY_IMPACT_PRIVATE_VIEW), nav = await readNav(process.env.POLICY_IMPACT_PRIVATE_NAV, json);
  if (mode === 'check') { await check(json, nav); return; }
  if (mode !== 'serve') fail('MODE');
  const fixtures = { 'sec-qgv2.json': { json: F.strictPayload() }, [FILE]: { json } }; if (nav) fixtures[NAV_FILE] = { json: nav };
  const s = await site.start({ fixtures });
  console.log('policy-impact private development site: ' + s.base + '#/macro (REAL_REVIEWED, this machine only)');
  const stop = async () => { await s.close(); process.exit(0); };
  process.on('SIGINT', stop); process.on('SIGTERM', stop);
})().catch((e) => { console.error('PRIVATE_CHECK_FAILED ' + (e && e.message ? e.message.split('\n')[0] : 'error')); process.exitCode = 1; });
