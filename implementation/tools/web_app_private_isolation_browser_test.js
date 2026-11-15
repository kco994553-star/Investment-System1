'use strict';
// The public screens do not depend on the owner-private KIS panels (owner 2026-11-15, DC-52). Builds the real Pages artifact
// (tools/build_pages_cockpit.py), and serves it as published plus synthetic variants made in temporary copies only:
//  - published: app.html as deployed. The owner-private files are not published (tools/web_app_preview.py OWNER_PRIVATE), so
//    IS2.kisPrivate / IS2.privateExpand do not exist, nothing goes to the Worker or a /kis path, private panels are 준비 중.
//  - owner files added: the two owner-private files and the source loader.js copied in (what an approved publication would
//    serve). A public visitor (not signed in) sees only 로그인 필요 in the private cells and sends nothing to the Worker on any
//    screen; after a sign-in, a Worker answer of 403 / 500 / invalid JSON / a schema mismatch leaves the private cell in its short
//    login or error state and the public screen as it was.
//  - script failures: kis-private.js throws on load, private-expand-live.js throws on load, private-expand-live.js is missing.
//    The loader still finishes (IS2.loadState() READY; the file is named in IS2.loadSkipped()), the private cells stay 준비 중,
//    and the public screens are the same as published.
// "The same" is per screen: the shell and menus, the public sections ([data-section]) of #/, #/qgv, #/technical, #/macro and
// #/news in order, the leaderboard rows, and the technical screen's public verdicts. No page error but an injected one; synthetic
// values only.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const site = require('./web_app_test_site');
const { ROOT } = require('./web_app_reuse');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_kis_private_fixture.js');

const WEB_APP = path.join(ROOT, 'implementation/src/investment_system/product/web_app');
const OWNER_PRIVATE = ['kis-private.js', 'private-expand-live.js'];
const NOW = '2026-10-31T06:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
const FIXTURES = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } };
const ROUTES = ['#/', '#/qgv', '#/technical/NASDAQ%3ANVDA', '#/macro', '#/news'];
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const TOKEN = ['memory', 'only', 'synthetic', 'isolation', 'session'].join('-');
const GIS_STUB = 'window.google={accounts:{oauth2:{initTokenClient:function(cfg){return{requestAccessToken:function(){cfg.callback({access_token:'
  + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};}}}};';
const THROW = (name) => "throw new Error('SYNTHETIC_" + name.replace(/\W/g, '_').toUpperCase() + "_FAILURE');\n";

function buildPages() {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-isolation-'));
  fs.rmSync(out, { recursive: true });
  execFileSync('python3', [path.join(ROOT, 'implementation/tools/build_pages_cockpit.py'), '--out', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  return out;
}
// A temporary copy of the Pages build with the owner-private files: 'real' (the source file), 'throw' (a synthetic script that
// throws on load) or 'missing' (not there). Any of them present also brings the source loader.js, which lists both files.
function variant(out, files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-isolation-variant-'));
  fs.cpSync(out, dir, { recursive: true });
  fs.copyFileSync(path.join(WEB_APP, 'loader.js'), path.join(dir, 'loader.js'));
  for (const name of OWNER_PRIVATE) {
    if (files[name] === 'real') fs.copyFileSync(path.join(WEB_APP, name), path.join(dir, name));
    else if (files[name] === 'throw') fs.writeFileSync(path.join(dir, name), THROW(name));
  }
  return dir;
}

let phase = 'START';
(async () => {
  const out = buildPages();
  for (const name of OWNER_PRIVATE) assert.ok(!fs.existsSync(path.join(out, name)), name + ' is not published');
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const dirs = [];
  let checks = 0;
  // One visit: every route in order; returns each route's public signature and private cells, and what left the origin.
  async function visit(dir, { injected = null, missing = [], data = null } = {}) {
    const server = await site.start({ out: dir, fixtures: FIXTURES });
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    const page = await ctx.newPage(), seen = { outside: [], worker: [], errors: [], pageErrors: [], missing: new Set() };
    await ctx.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url());
      if (url.origin === server.origin) { await route.continue(); return; }
      seen.outside.push(req.method() + ' ' + url.origin + url.pathname);
      if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
      if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (url.origin === WORKER && data) {
        seen.worker.push(url.pathname);
        const a = data(url.pathname);
        await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: a.raw !== undefined ? a.raw : JSON.stringify(a.body) }); return;
      }
      await route.abort();
    });
    page.on('response', (r) => { if (r.status() === 404 && new URL(r.url()).origin === server.origin) seen.missing.add(decodeURIComponent(new URL(r.url()).pathname.slice(1))); });
    page.on('console', (m) => { if (m.type() === 'error' && !/status of (403|404|500)/.test(m.text())) seen.errors.push(m.text()); });
    page.on('pageerror', (e) => seen.pageErrors.push(String(e && e.message || e)));
    await page.goto(server.base + 'app.html#/');
    await page.locator('main[data-route]').waitFor();
    await page.evaluate(() => window.IS2.ready);
    const head = await page.evaluate(() => ({ state: window.IS2.loadState(), skipped: typeof window.IS2.loadSkipped === 'function' ? [...window.IS2.loadSkipped()] : null,
      reader: !!window.IS2.kisPrivate, expand: !!window.IS2.privateExpand, menus: document.querySelectorAll('nav a[href^="#/"]').length }));
    const screens = {};
    for (const route of ROUTES) {
      await page.evaluate((h) => { location.hash = h; }, route);
      await page.waitForFunction((h) => document.querySelector('main[data-route]') && location.hash === h, route);
      if (route === '#/qgv') await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
      if (route.startsWith('#/technical')) await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 });
      await page.waitForTimeout(200);
      screens[route] = await page.evaluate(() => ({
        route: document.querySelector('main[data-route]').dataset.route, kids: document.querySelector('main[data-route]').children.length,
        sections: [...document.querySelectorAll('main [data-section]')].map((x) => x.dataset.section),
        rows: [...document.querySelectorAll('[data-lb-table] tbody tr[data-row]')].map((tr) => tr.dataset.row + ' ' + ((tr.querySelector('td[data-cell=rank]') || {}).textContent || '')),
        verdicts: [...document.querySelectorAll('[data-indicator] [data-verdict]')].map((x) => x.dataset.verdict + ' ' + (x.dataset.na || '')),
        privates: [...document.querySelectorAll('[data-private-panel]')].map((p) => [p.dataset.privatePanel, p.dataset.privateState, p.querySelector('[data-private-status]').textContent, p.querySelector('.private-body').textContent]),
      }));
    }
    const result = { head, screens, seen, page, ctx, server };
    const pageErrors = seen.pageErrors.filter((e) => !(injected && e.includes(injected)));
    assert.deepEqual(pageErrors, [], phase + ': no page error but the injected one');
    if (injected) assert.ok(seen.pageErrors.some((e) => e.includes(injected)), phase + ': the injected failure happened');
    assert.deepEqual(seen.errors, [], phase + ': no console error');
    for (const name of seen.missing) assert.ok(/^[a-z0-9-]+\.json$/.test(name) || missing.includes(name), phase + ': only live-only data or the removed file is missing: ' + name);
    return result;
  }
  const close = async (v) => { await v.ctx.close(); await v.server.close(); };
  // The public part of every screen equals the published one; the private cells are listed apart.
  function samePublic(v, base) {
    assert.equal(v.head.state, 'READY', phase + ': the loader finishes');
    assert.equal(v.head.menus, base.head.menus, phase + ': the shell and menus draw');
    for (const route of ROUTES) {
      const a = v.screens[route], b = base.screens[route];
      assert.deepEqual([a.route, a.kids, a.sections, a.rows, a.verdicts], [b.route, b.kids, b.sections, b.rows, b.verdicts], phase + ' ' + route + ': the public screen is the same as published');
      assert.ok(a.kids > 0, phase + ' ' + route + ': public screen drawn');
    }
    checks += ROUTES.length + 2;
  }
  const privates = (v) => ROUTES.flatMap((r) => v.screens[r].privates);
  try {
    phase = 'published';
    const base = await visit(out);
    assert.deepEqual([base.head.state, base.head.reader, base.head.expand], ['READY', false, false], phase + ': no owner-private code on the published preview');
    assert.deepEqual(base.head.skipped, [], phase + ': nothing skipped');
    assert.ok(base.head.menus > 0, phase + ': the shell and menus draw');
    assert.deepEqual(base.seen.outside, [], phase + ': no request leaves the origin (no Worker, no /kis, no sign-in script)');
    for (const [id, st, words, bodyText] of privates(base)) assert.ok(['NOT_READY', 'LOGIN_REQUIRED'].includes(st) && /준비 중|로그인 필요/.test(words) && bodyText === '', phase + ': ' + id);
    assert.ok(ROUTES.every((r) => base.screens[r].kids > 0 && (r === '#/' || base.screens[r].sections.length > 0)) && base.screens['#/qgv'].rows.length > 0 && base.screens['#/technical/NASDAQ%3ANVDA'].verdicts.length > 0, phase + ': public content renders ' + JSON.stringify(ROUTES.map((r) => [r, base.screens[r].sections.length, base.screens[r].rows.length, base.screens[r].verdicts.length])));
    checks += 5;
    await close(base);

    phase = 'owner files added, public visitor';
    dirs.push(variant(out, { 'kis-private.js': 'real', 'private-expand-live.js': 'real' }));
    const owner = await visit(dirs[dirs.length - 1]);
    samePublic(owner, base);
    assert.deepEqual([owner.head.reader, owner.head.expand, owner.head.skipped], [true, true, []]);
    const kis = privates(owner).filter(([id]) => id === 'tech-kis-chart' || id === 'qgv-kis');
    assert.deepEqual(kis.map(([id, st, words, b]) => [id, st, words, b]), [['qgv-kis', 'LOGIN_REQUIRED', '로그인 필요', ''], ['tech-kis-chart', 'LOGIN_REQUIRED', '로그인 필요', '']], phase + ': only 로그인 필요 in the KIS cells');
    assert.deepEqual(owner.seen.outside, [], phase + ': a public visitor sends nothing to the Worker or Google on any screen');
    checks += 3;
    await close(owner);

    // Data failures after a sign-in: the private cell takes its short state, the public screen stays.
    // A transport or auth failure stops the click at its first read; a file of the wrong schema is refused after the click's reads.
    const ALL = ['/kis/analysis', '/kis/chart', '/kis/technical'];
    for (const [label, answer, st, reads] of [
      ['403', { status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } }, 'LOGIN_REQUIRED', ALL.slice(0, 1)],
      ['500', { status: 500, body: { error: { code: 'UPSTREAM_UNAVAILABLE' } } }, 'ERROR', ALL.slice(0, 1)],
      ['invalid JSON', { status: 200, raw: '{"schema": ' }, 'ERROR', ALL.slice(0, 1)],
      ['schema mismatch', { status: 200, body: { ...X.analysis(), schema: X.K('bars/9/analysis') } }, 'ERROR', ALL],
    ]) {
      phase = 'data ' + label;
      const v = await visit(dirs[0], { data: () => answer });
      const page = v.page, expand = () => page.locator('[data-private-expand=technical]').click();
      await page.evaluate(() => { location.hash = '#/technical/NASDAQ%3ANVDA'; });
      await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 });
      await expand(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=technical]').textContent), null, { timeout: 20000 });
      await expand(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=technical]').textContent));
      await expand();
      await page.locator('[data-private-panel=tech-kis-chart][data-private-state=' + st + ']').waitFor({ timeout: 30000 });
      await page.waitForFunction(() => document.querySelector('[data-private-note=technical]').textContent.length > 0);
      const after = await page.evaluate(() => ({ sections: [...document.querySelectorAll('main [data-section]')].map((x) => x.dataset.section),
        verdicts: [...document.querySelectorAll('[data-indicator] [data-verdict]')].map((x) => x.dataset.verdict + ' ' + (x.dataset.na || '')),
        layer: document.querySelectorAll('[data-private-layer]').length, note: document.querySelector('[data-private-note=technical]').textContent }));
      const b = base.screens['#/technical/NASDAQ%3ANVDA'];
      assert.deepEqual([after.sections, after.verdicts], [b.sections, b.verdicts], phase + ': the public technical screen is unchanged');
      assert.equal(after.layer, 0, phase + ': nothing of a failed read is shown');
      assert.ok(after.note.length <= 40, phase + ': one short line: ' + after.note);
      assert.deepEqual(v.seen.worker, reads, phase + ': the reads of the one click');
      // The other public screens still work after the failure.
      await page.evaluate(() => { location.hash = '#/qgv'; });
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
      const rows = await page.locator('[data-lb-table] tbody tr[data-row]').evaluateAll((n) => n.map((tr) => tr.dataset.row + ' ' + ((tr.querySelector('td[data-cell=rank]') || {}).textContent || '')));
      assert.deepEqual(rows, base.screens['#/qgv'].rows, phase + ': the leaderboard is unchanged');
      assert.deepEqual(v.seen.pageErrors, [], phase + ': no page error');
      checks += 5;
      await close(v);
    }

    for (const [label, files, injected, missing, skipped] of [
      ['reader throws', { 'kis-private.js': 'throw', 'private-expand-live.js': 'real' }, 'SYNTHETIC_KIS_PRIVATE_JS_FAILURE', [], ['kis-private.js']],
      ['panel script throws', { 'kis-private.js': 'real', 'private-expand-live.js': 'throw' }, 'SYNTHETIC_PRIVATE_EXPAND_LIVE_JS_FAILURE', [], ['private-expand-live.js']],
      ['panel script missing', { 'kis-private.js': 'real', 'private-expand-live.js': 'missing' }, null, ['private-expand-live.js'], ['private-expand-live.js']],
      ['both missing', { 'kis-private.js': 'missing', 'private-expand-live.js': 'missing' }, null, OWNER_PRIVATE, OWNER_PRIVATE],
    ]) {
      phase = 'script ' + label;
      dirs.push(variant(out, files));
      const v = await visit(dirs[dirs.length - 1], { injected, missing });
      samePublic(v, base);
      assert.deepEqual(v.head.skipped, skipped, phase + ': the failed owner-private file is named, the layer still loads');
      for (const [id, st, words, bodyText] of privates(v)) assert.ok(st === 'NOT_READY' && words === '비공개 기능 준비 중' && bodyText === '', phase + ': ' + id + ' stays 준비 중');
      assert.deepEqual(v.seen.outside, [], phase + ': nothing leaves the origin');
      checks += 3;
      await close(v);
    }
    console.log('web_app_private_isolation_browser_test: ' + checks + ' checks passed (published, owner files with a public visitor, data 403 / 500 / invalid JSON / schema mismatch, reader throws, panel script throws, panel script missing, both missing)');
  } catch (e) {
    console.error('web_app_private_isolation_browser_test failed at ' + phase + ':', e && e.stack || e);
    process.exitCode = 1;
  } finally {
    await browser.close();
    for (const d of [...dirs, out]) fs.rmSync(d, { recursive: true, force: true });
  }
})();
