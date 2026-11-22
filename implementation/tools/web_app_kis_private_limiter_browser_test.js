'use strict';
// The 2-1 KIS panel of #/technical against the real private Worker code (implementation/worker/src/index.js: createHandler and
// its HistoryRateLimiter with the deployed limit, REQUESTS_PER_MINUTE 12, one owner request at a time, 5 s apart, real clock),
// on the published Pages artifact (app.html) at phone width. Owner check 2026-11-17: the panel showed RATE_LIMITED because a
// second tap during the ~15 s of three spaced reads started overlapping reads. Checked here:
//  A. read-token check, then 비공개 펼치기 at once: the one stock-route read (owner 2026-11-20 switch) shown, the Worker refuses none.
//  B. a second tap during the read does nothing (the button is disabled and says 불러오는 중…): still one read, none refused.
//  C. the read-token check pressed while the panel reads waits its turn: the panel and the check both finish, none refused.
// Google, GitHub and the token check upstream are stand-ins inside the Worker's own fetch; every payload is the synthetic fixture
// tools/web_app_kis_private_fixture.js (no company, no KIS value).
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { execFileSync } = require('node:child_process');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_kis_private_fixture.js');

const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
const FIXTURES = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } };
const TOKEN = ['memory', 'only', 'synthetic', 'kis', 'limiter', 'session'].join('-');
const WORKER = 'https://private-investment-history.kco994553.workers.dev', ORIGIN = 'https://kco994553-star.github.io';
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const GIS_STUB = 'window.google={accounts:{oauth2:{initTokenClient:function(cfg){return{requestAccessToken:function(){cfg.callback({access_token:'
  + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,d){if(d)d({});}}}};';
const OWNER = ['owner', 'example.test'].join('@'), CLIENT_ID = 'synthetic-client-id';
const READS = ['/kis/stock?symbol=NVDA'];   // owner 2026-11-20 switch: one read of the stock route per click
let phase = 'START';

(async () => {
  let s = null, browser = null;
  const W = await import(pathToFileURL(path.join(R.ROOT, 'implementation/worker/src/index.js')).href);
  // A Durable Object storage stand-in with the one-at-a-time transaction the platform gives.
  class Storage { value; queue = Promise.resolve();
    async get() { return structuredClone(this.value); } async put(k, v) { this.value = structuredClone(v); }
    async transaction(cb) { const r = this.queue.then(() => cb(this)); this.queue = r.catch(() => {}); return r; } }
  const toml = fs.readFileSync(path.join(R.ROOT, 'implementation/worker/wrangler.toml'), 'utf8');
  const perMinute = /REQUESTS_PER_MINUTE\s*=\s*"(\d+)"/.exec(toml)[1];
  const env = { ALLOWED_EMAIL: OWNER, GOOGLE_CLIENT_ID: CLIENT_ID, PRIVATE_REPO_READ_TOKEN: ['github', 'pat', '11SYNTHETICONLY'].join('_'),
    PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER', REQUESTS_PER_MINUTE: perMinute };
  const limiter = new W.HistoryRateLimiter({ storage: new Storage() }, env);
  env.HISTORY_RATE_LIMITER = { idFromName: (n) => n, get: () => ({ fetch: (i, init) => limiter.fetch(i instanceof Request ? i : new Request(i, init)) }) };
  const f = X.codex556('available', { symbol: 'NVDA' });
  const files = { chart: f.chart, technical: f.technical, measures: f.measures };
  // The stock route's upstream: the index on the data branch, the asset API's one 302 to the release asset host, the gzip view.
  const { bars, raw_bars: rawBars, schema: chartSchema, ...chartHeader } = f.chart;
  const view = { schema: X.K('stock-view/1'), publication_scope: 'OWNER_PRIVATE_ONLY', symbol: 'NVDA', evaluation_day: f.technical.evaluation_day,
    fields: ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', ...Array.from({ length: 10 }, (_, i) => 'I' + i)],
    rows: bars.map((b) => [b.date, b.open, b.high, b.low, b.close, b.volume, ...Array(11).fill(null)]),
    chart: { ...chartHeader, schema: X.K('chart-metadata/1') }, indicators: {}, coverage: {}, latest: { technical: f.technical, measures: f.measures },
    additional_requests_for_toggle: 0, additional_requests_for_retained_period: 0 };
  const viewJson = Buffer.from(JSON.stringify(view), 'utf8'), viewGz = zlib.gzipSync(viewJson), hex = (b) => crypto.createHash('sha256').update(b).digest('hex');
  const stockIndex = { schema: X.K('stock-asset-index/1'), publication_scope: 'OWNER_PRIVATE_ONLY', evaluation_day: f.technical.evaluation_day,
    release_tag: 'kis-view-' + f.technical.evaluation_day + '-' + 'b'.repeat(12), generation_sha256: 'c'.repeat(64),
    stocks: { NVDA: { symbol: 'NVDA', asset_id: 7, name: hex(viewGz) + '.json.gz', bytes: viewGz.length, sha256: hex(viewGz), json_bytes: viewJson.length, json_sha256: hex(viewJson) } },
    qgv: { asset_id: 9, name: 'd'.repeat(64) + '.json.gz', bytes: 10, sha256: 'd'.repeat(64), json_bytes: 20, json_sha256: 'e'.repeat(64) } };
  const statusFile = { schema: ['private', 'area-status/1'].join('-'), publication_scope: 'OWNER_PRIVATE_ONLY', run_at: '2026-11-05T03:00:00Z',
    worker_read_token: { state: 'NO_EXPIRY', code: null, expires_on: null, days_left: null, verification: 'NOT_CHECKED' } };
  const upstream = async (input) => {
    const url = new URL(String(input));
    if (url.origin === 'https://oauth2.googleapis.com') return new Response(JSON.stringify({ aud: CLIENT_ID, email: OWNER, email_verified: true, expires_in: '3600' }), { status: 200 });
    await new Promise((r) => setTimeout(r, 300));                // a GitHub read is not instant
    if (url.origin === 'https://release-assets.githubusercontent.com') return new Response(viewGz, { status: 200 });
    if (/^\/repos\/[^/]+\/[^/]+\/releases\/assets\/7$/.test(url.pathname)) return new Response(null, { status: 302, headers: { Location: 'https://release-assets.githubusercontent.com/synthetic/7?sig=x' } });
    // No bundle root yet (Worker reader-first, 2026-11-22): its probe is a 404 and the single index is read as before.
    if (/\/contents\/views\/kis-stock-packs\.json$/.test(url.pathname)) return new Response('{}', { status: 404 });
    if (/\/contents\/views\/[a-z-]+\.json$/.test(url.pathname)) return new Response(JSON.stringify(stockIndex), { status: 200 });
    const m = /^\/repos\/[^/]+\/[^/]+\/contents\/([a-z]+)\//.exec(url.pathname);
    if (m && m[1] === 'status') return new Response(JSON.stringify(statusFile), { status: 200 });
    if (m && files[m[1]]) return new Response(JSON.stringify(files[m[1]]), { status: 200 });
    return new Response('{}', { status: 404 });
  };
  const handler = W.createHandler({ fetch: upstream });
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-kis-limiter-'));
  fs.rmSync(out, { recursive: true });
  execFileSync('python3', [path.join(R.ROOT, 'implementation/tools/build_pages_cockpit.py'), '--out', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  try {
    s = await site.start({ out, fixtures: FIXTURES });
    browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: [] });
    const log = [], unexpected = [], gzipped = [];
    await ctx.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url());
      if (url.origin === s.origin) { await route.continue(); return; }
      if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '' }); return; }
      if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (url.origin === WORKER) {
        const res = await handler(new Request(url.href, { method: req.method(), headers: { ...req.headers(), origin: ORIGIN } }), env);
        let body = Buffer.from(await res.arrayBuffer()); const headers = {};
        res.headers.forEach((v, k) => { headers[k] = v; });
        // Light read (owner 2026-11-21): the Worker passes the pinned gzip bytes through with Content-Encoding: gzip, unread.
        // A browser's network layer inflates them; Playwright's fulfill does not, so the stand-in transport does it here,
        // after checking the bytes are exactly the pinned asset.
        if (headers['content-encoding'] === 'gzip') {
          assert.ok(url.pathname === '/kis/stock' && body.equals(viewGz), 'only the stock route answers gzip, and with the pinned bytes unchanged');
          gzipped.push(url.pathname + url.search);
          body = zlib.gunzipSync(body); delete headers['content-encoding'];
        }
        headers['access-control-allow-origin'] = s.origin;           // the test site stands in for the Pages origin
        log.push({ at: Date.now(), path: url.pathname + url.search, status: res.status });
        await route.fulfill({ status: res.status, headers, body }); return;
      }
      unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    const panel = '[data-private-panel=tech-kis-chart]', btn = page.locator('[data-private-expand=technical]');
    const note = () => page.locator('[data-private-note=technical]').textContent();
    const shown = () => page.locator(panel + '[data-private-state=READY] [data-private-layer=technical]').waitFor({ timeout: 60000 });
    const refused = () => log.filter((l) => l.status === 429).length;
    function spaced(entries) { for (let i = 1; i < entries.length; i++) assert.ok(entries[i].at - entries[i - 1].at >= 5000, phase + ': requests at least 5 s apart'); }
    function threeShown(slice) {
      assert.deepEqual(slice.map((l) => [l.path, l.status]), READS.map((p) => [p, 200]), phase + ': the three reads, each answered');
    }
    async function everythingShown() {
      assert.equal(await page.locator('svg[data-private-chart=NVDA] [data-private-close-line]').count(), 1, phase + ': the chart (close line)');
      assert.match(await page.locator('[data-private-layer=technical]').textContent(), /^KIS · 비공개 · 가격 기준일 2026-10-23/, phase + ': the analysis label and basis day');
      assert.equal(await page.locator('[data-private-measures=READY]').count(), 1, phase + ': the indicators (technical measures)');
      assert.equal(await btn.textContent(), '비공개 접기');
      assert.equal(await btn.isDisabled(), false);
    }

    phase = 'sign in';
    await page.goto(s.base + 'app.html#/technical/NASDAQ%3ANVDA'); await page.locator('main[data-route=technical]').waitFor();
    await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 }); await btn.waitFor();
    await btn.click(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=technical]').textContent), null, { timeout: 20000 });
    await btn.click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=technical]').textContent));
    assert.equal(log.length, 0, phase + ': signing in reads nothing');

    phase = 'A token check, then expand at once';
    await page.locator('[data-private-status-area=technical] summary').click();
    await page.locator('[data-private-token-check=technical]').click();
    await page.waitForFunction(() => document.querySelector('[data-private-token-status=technical]').dataset.privateTokenState === 'NO_EXPIRY');
    await btn.click(); await shown();
    assert.deepEqual(log.map((l) => [l.path, l.status]), [['/kis/status', 200], ...READS.map((p) => [p, 200])], phase + ': status, then the three reads');
    assert.equal(refused(), 0, phase + ': the Worker refused nothing'); spaced(log);
    await everythingShown();
    assert.equal(await note(), '', phase + ': no error line');

    phase = 'B a second tap while reading';
    await btn.click(); await page.locator(panel + ' [data-private-closed]').waitFor();
    let mark = log.length;
    await btn.click();
    await page.waitForFunction(() => { const b = document.querySelector('[data-private-expand=technical]'); return b.disabled && b.getAttribute('aria-busy') === 'true'; });
    assert.equal(await btn.textContent(), '불러오는 중…', phase + ': the button says it is reading');
    await page.waitForTimeout(1500);
    await btn.click({ force: true }); await btn.click({ force: true });         // taps on the disabled button
    await shown();
    threeShown(log.slice(mark)); assert.equal(refused(), 0, phase + ': the Worker refused nothing'); spaced(log);
    await everythingShown();

    phase = 'C token check while the panel reads';
    await btn.click(); await page.locator(panel + ' [data-private-closed]').waitFor();
    mark = log.length;
    await btn.click(); await page.waitForTimeout(800);
    await page.locator('[data-private-status-area=technical]').evaluate((d) => { d.open = true; });
    await page.locator('[data-private-token-check=technical]').click();
    await shown();
    await page.waitForFunction(() => document.querySelector('[data-private-token-status=technical]').dataset.privateTokenState === 'NO_EXPIRY', null, { timeout: 30000 });
    assert.deepEqual(log.slice(mark).map((l) => [l.path, l.status]), [...READS.map((p) => [p, 200]), ['/kis/status', 200]], phase + ': the check waits behind the three reads');
    assert.equal(refused(), 0, phase + ': the Worker refused nothing'); spaced(log);
    await everythingShown();

    phase = 'boundaries';
    assert.deepEqual(unexpected, [], phase + ': no other outside request');
    assert.deepEqual(gzipped, log.filter((l) => l.path === READS[0] && l.status === 200).map((l) => l.path), phase + ': every answered stock read was the pinned gzip bytes, passed through');
    assert.ok(gzipped.length >= 1, phase + ': at least one pass-through read');
    const st = await site.storage(page);
    assert.ok(!Object.keys(st.localItems).some((k) => /kis|token|private-layer/i.test(k)), phase + ': no private key on the device');
    assert.deepEqual(site.leaks([...Object.values(st.localItems), page.url(), ...seen.errors], [TOKEN, ...X.MEASURE_RAW]), [], phase + ': no token or private value in storage, the address or the console');
    console.log('web_app_kis_private_limiter_browser_test: PASS (real Worker limiter, app.html 390: token check then expand, second tap while reading, check while reading; ' + log.length + ' admitted reads, 0 refused, ' + gzipped.length + ' gzip pass-through)');
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.message ? e.message.split('\n')[0] : e)); process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    if (s && typeof s.close === 'function') await s.close();
    fs.rmSync(out, { recursive: true, force: true });
  }
})();
