'use strict';
// New frontend · 4. 뉴스 (feature 5.1–5.3, route #/news[/<company>], screen-news.js skeleton + screen-news-live.js) in a real browser
// at 1440 and 390. Builds the development site (tools/web_app_test_site.js) and serves synthetic public lists
// (tools/web_app_news_fixture.js: SEC 8-K, news-signals and DART files that pass the old readers' validation), then checks in Chromium:
//  - Loading (split first paint): with a layer file held back the skeleton's three section slots say 불러오는 중, nothing else is
//    drawn and nothing is read; after the release the blocks, the 준비 중 parts and the one private panel are drawn.
//  - Reads: a fresh open of #/news reads exactly the page-open core set (IS2.data.CORE without dart-financials.json), the three
//    lists (IS2.data.LIST_FILES) and the company list's two static files (the NEWS_READS of web_app_data_layer_browser_test.js);
//    a route change (another centre) reads nothing new.
//  - 5.2 list: the rows and their order equal the pure timeline (screen-news-live.js, itself equal to NewsSignals.timeline by
//    web_app_news_node_test.js) over the newest 30; 8-K rows carry the IR release under them, a news event folds its repeat;
//    external links open in a new tab with noopener noreferrer; filters by keyboard (channel, class, new / repeat, order, range,
//    reset) narrow the rows and keep the focus on the control; 5.2.5 counts; 5.2.7 collection state (per file, per news source,
//    DART STALE, GDELT attribution, no score effect); 5.2.2 · 5.2.3 · 5.2.4 · 5.2.6 as 준비 중 with no number; the 5.2.4 private
//    panel (news-event-reaction) NOT_READY, nothing in it.
//  - 5.1: no centre → 가운데 기업 없음 and 관계 자료 미연결 (REL_SOURCE); the shared company search picks NVDA (keys) and opens
//    #/news/nvda (range = 가운데 기업); a code route (#/news/NASDAQ:NVDA) resolves the same company; an unknown one says so; ★ 관심
//    기업 is written only by a real click (a script click stores nothing), kept in this device's interests (the home's key) and
//    across a reload, feeds 5.1.4, the 관심 기업 range and the importance order; 가운데 기업 비우기.
//  - 5.3: the tree nodes, the jump to 4.2, the public counts and newest examples, relations NA.
//  - Partial failure: news-signals.json 404 (SEC + DART rows stay, its words, tree NA), sec-disclosures.json HTTP 500 (the IR
//    release stands alone as a repeat), the GDELT 429 run (일부 갱신 실패, the failed source's words). Empty: the offline
//    NOT_AVAILABLE files and all three lists missing. Error: data.js 404 (LOADER_FAILED) and screen-news-live.js 404.
//  - Boundaries everywhere: same-origin requests only (no external call), no console error but the intended ones, no CSP violation,
//    no [style], no horizontal overflow at 390 (details open too), every control reachable by Tab with a visible focus ring,
//    named buttons, no price-shaped text, nothing stored but the ★ click's interests.
// Synthetic data only.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const site = require('./web_app_test_site');
const R = require('./web_app_reuse');
const X = require('./web_app_news_fixture.js');
const M = require(R.newPath('screen-news-live.js'));

const NOW = new Date(X.NOW).toISOString();
// Files the offline build does not publish (answered 404 by the server when no fixture is set).
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'macro-evidence.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json'];
const LISTS = ['sec-disclosures.json', 'news-signals.json', 'dart-disclosures.json'];
const P = { sec: X.sec(), news: X.news(), dart: X.dart() };
const FULL = { 'sec-disclosures.json': { json: P.sec }, 'news-signals.json': { json: P.news }, 'dart-disclosures.json': { json: P.dart } };
const PERSONAL = 'investment.web.v1.personal';// the home's 즐겨찾기 / interests key (IS2.store.KEYS.PERSONAL)
const NO_PRICE = /\d+(\.\d+)?\s?%|USD|\$\s?\d/;
const rowId = (r) => (r.channel === 'NEWS' ? r.item.group_id : r.source === 'DART' ? r.event.rcept_no : r.event.accession);
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
  const reads = (from) => s.requests.slice(from).map((r) => r.name).filter((n) => n.endsWith('.json')).sort();
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => (e instanceof HTMLElement ? e.innerText : e.textContent));
  const count = (page, sel) => page.locator(sel).count();
  const drawn = (page) => page.locator('[data-news-facts] [data-tree-fact], [data-news-slot] [data-state=error]').first().waitFor();
  const rows = (page) => page.locator('[data-timeline] > li[data-row]').evaluateAll((n) => n.map((x) => x.dataset.row));
  const rowCompanies = (page) => page.locator('[data-timeline] > li[data-row] [data-row-company]').evaluateAll((n) => n.map((x) => x.dataset.rowCompany));
  let CORE = null, NEWS_READS = null;
  async function open(page, hash = '#/news', opts = {}) {
    const at = s.requests.length;
    await page.goto(s.base + hash, opts); await page.locator('main[data-route=news]').waitFor();
    return at;
  }
  async function boundaries(page, seen, label, { errors = [], stored = [] } = {}) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
    assert.deepEqual(seen.errors.filter((e) => !errors.some((x) => x.test(e))), [], label + ': no console or page error');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    const price = (await page.locator('main').innerText()).match(NO_PRICE);
    assert.equal(price && price[0], null, label + ': no price-shaped text');
    const st = await site.storage(page);
    assert.deepEqual([Object.keys(st.localItems).sort(), st.session, st.idb], [[...stored].sort(), 0, 0], label + ': nothing stored on the device but the keys a click wrote');
  }
  // The one private panel (table 1-3: 5.2.4 only): NOT_READY, the shared words, in 4.2; nothing else in it.
  async function panel(page, label) {
    const got = await page.locator('[data-private-panel]').evaluateAll((n) => n.map((x) => [x.dataset.privatePanel, x.dataset.privateState, x.querySelector('[data-private-status]').textContent,
      x.querySelector('.card-title').textContent, x.closest('[data-section]').dataset.section, x.querySelectorAll('[data-mascot]').length, x.querySelector('.private-body').textContent]));
    assert.deepEqual(got, [['news-event-reaction', 'NOT_READY', '비공개 기능 준비 중', '비공개 사건 전후 반응 · 통합 거래량 배수 (KIS 일봉 · 분봉)', '4-2', 0, '']], label + ': one private panel, NOT_READY');
  }
  // Every focusable control of main is reached by Tab, with a visible focus ring; every button is named. The one exception is the
  // shared company search's input (parts.searchBox: its bordered box and caret, app.css `.search-box input{outline:none}`, Main's
  // shared style, the same on the home): it is still reached by Tab, and counted as shown by its box.
  async function keyboard(page, label) {
    const n = await page.evaluate(() => {
      const els = [...document.querySelectorAll('main button, main select, main input, main summary, main a[href], main [tabindex]')]
        .filter((e) => !e.disabled && e.tabIndex >= 0 && e.getClientRects().length && !e.closest('details:not([open]) > :not(summary)'));
      els.forEach((e, i) => { e.dataset.k = String(i); });
      document.getElementById('main').focus();
      return els.length;
    });
    const got = new Set(); let ring = 0;
    for (let i = 0; i < n + 40; i++) {
      await page.keyboard.press('Tab');
      const a = await page.evaluate(() => { const e = document.activeElement, cs = getComputedStyle(e); return { k: e.dataset ? e.dataset.k : undefined, inMain: !!e.closest('main'), ring: (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || e.matches('.search-box input') }; });
      if (!a.inMain) { if (got.size) break; continue; }
      if (a.k !== undefined) got.add(a.k); if (a.ring) ring++;
    }
    assert.equal(got.size, n, label + ': every control is reached by Tab (' + got.size + '/' + n + ')');
    assert.ok(ring >= got.size, label + ': each focused control shows a focus ring');
    const unnamed = await page.evaluate(() => [...document.querySelectorAll('main button, main select')].filter((b) => !(b.getAttribute('aria-label') || b.textContent.trim())).length);
    assert.equal(unnamed, 0, label + ': every button and select has a name');
    await page.evaluate(() => document.querySelectorAll('[data-k]').forEach((e) => { delete e.dataset.k; }));
  }
  const focused = (page) => page.evaluate(() => document.activeElement && document.activeElement.dataset ? Object.assign({}, document.activeElement.dataset) : {});
  async function choose(page, name, value) {
    await page.locator('[data-news-filter="' + name + '"]').focus(); await page.locator('[data-news-filter="' + name + '"]').selectOption(value);
    assert.equal((await focused(page)).newsFilter, name, phase + ': the focus stays on the ' + name + ' control after the repaint');
  }
  try {
    // ================================================================ full data, PC
    {
      const width = 1440, tag = (p) => { phase = width + ' ' + p; };
      set(FULL);
      const { ctx, page, seen } = await context(width);
      // ---- loading: a layer file held back
      tag('loading');
      let release; const gate = new Promise((r) => { release = r; });
      await page.route('**/engines.js', async (route) => { await gate; await route.continue(); });
      const at = await open(page, '#/news', { waitUntil: 'domcontentloaded' });
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['4-1', '4-2', '4-3'], phase + ': the skeleton draws the three sections');
      assert.equal(await count(page, '[data-news-slot] [data-state=loading][role=status]'), 3, phase + ': three section slots say 불러오는 중');
      assert.equal(await page.locator('main h1').innerText(), '4. 뉴스');
      assert.deepEqual([await count(page, '[data-block]'), await count(page, '[data-prep]'), await count(page, '[data-private-panel]')], [0, 0, 0], phase + ': nothing but the skeleton before the layer');
      assert.deepEqual(reads(at), [], phase + ': nothing is read before the layer');
      release();
      await drawn(page); await page.locator('[data-timeline]').waitFor();
      assert.equal(await count(page, '[data-news-slot] [data-state=loading]'), 0, phase + ': the slots are filled');
      await panel(page, phase);
      CORE = await page.evaluate(() => window.IS2.data.CORE);
      NEWS_READS = [...CORE.filter((n) => n !== 'dart-financials.json'), ...LISTS, 'universe-codes.json', 'company-names-ko.json'].sort();
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      tag('reads');
      assert.deepEqual(reads(at), NEWS_READS, phase + ': a fresh open reads exactly the core set, the three lists and the company list');
      assert.equal(await count(page, '[data-state=loading]'), 0, phase + ': no block is left loading');
      assert.deepEqual(await page.locator('[data-news-band] [data-file]').evaluateAll((n) => n.map((x) => [x.dataset.file, x.dataset.fileState])), LISTS.map((f) => [f, 'OK']));
      assert.match(await text(page, '[data-news-band]'), /SEC 8-K · 기준 2026-10-14 02:30 UTC[\s\S]*뉴스·신호 · 기준 2026-10-14 02:30 UTC[\s\S]*DART · 기준 2026-10-11 00:30 UTC/);
      // ---- 5.2.1 list (no centre on a fresh page: every company)
      tag('list');
      const all = M.timeline(P), top = all.slice(0, M.LIMIT);
      assert.deepEqual(await rows(page), top.map(rowId), phase + ': the newest rows in timeline order');
      assert.equal(await text(page, '[data-news-filter-count]'), '표시 ' + top.length + '건 · 최신 30행 안에서 거름');
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'ALL');
      const msft8k = P.sec.events.find((e) => e.company_id === 'msft');
      assert.equal(await page.locator('li[data-row="' + msft8k.accession + '"] [data-related-ir]').getAttribute('data-related-ir'), '1', phase + ': the IR release sits under its 8-K');
      const nvdaGroup = top.find((r) => r.channel === 'NEWS' && r.repeats.length);
      assert.equal(await page.locator('li[data-row="' + nvdaGroup.item.group_id + '"] [data-news-repeats]').getAttribute('data-news-repeats'), '1', phase + ': the repeat report is folded');
      assert.match(await text(page, 'li[data-row="' + nvdaGroup.item.group_id + '"]'), /^뉴스·신호\s*새 소식\s*실적 \(Earnings\)\s*기타 기업\s*NVDA · GDELT · 2026-10-12 21:00 UTC · news\.example\.com/);
      const amended = P.sec.events.find((e) => e.occurrence === 'REPEAT');
      assert.match(await text(page, 'li[data-row="' + amended.accession + '"]'), /공시·확정\s*정정·반복\s*실적 \(Results\)[\s\S]*NVDA · SEC 8-K\/A[\s\S]*EX-99\.1 없음 · NO_EXHIBIT_99_1[\s\S]*2\.02 영업 실적 및 재무 상태/);
      assert.match(await text(page, 'li[data-row="' + P.dart.events[0].rcept_no + '"]'), /공시·확정\s*새 공시\s*기타 공시 \(Other disclosure\)[\s\S]*042700 · DART · 2026-10-02 KST/);
      const links = await page.locator('main a[target=_blank]').evaluateAll((n) => n.map((a) => [a.getAttribute('rel'), new URL(a.href).protocol]));
      assert.ok(links.length > 20 && links.every(([rel, p]) => rel === 'noopener noreferrer' && p === 'https:'), phase + ': outside links open a new tab, noopener noreferrer, https');
      await page.locator('li[data-row="' + msft8k.accession + '"] [data-evidence] > summary').click();
      assert.match(await text(page, 'li[data-row="' + msft8k.accession + '"] [data-evidence]'), /구분\s*공시·확정 · 회사가 SEC에 제출한 원문[\s\S]*중복 처리\s*새 공시 · 묶음 시작[\s\S]*점수 영향\s*없음/);
      // ---- filters by keyboard (focus kept), counts and categories
      tag('filters');
      const cats = M.categories(all);
      assert.deepEqual(await page.locator('[data-news-filter=category] option').evaluateAll((n) => n.map((o) => o.value)), ['ALL', ...cats]);
      assert.deepEqual(await page.locator('[data-news-filter=category] option').allTextContents(), ['전체', ...cats.map(M.categoryLabel)]);
      await choose(page, 'channel', 'NEWS');
      assert.deepEqual(await rows(page), M.filterRows(top, { ...M.FILTER_DEFAULT, channel: 'NEWS' }).map(rowId));
      assert.deepEqual([...new Set(await page.locator('[data-timeline] > li[data-row]').evaluateAll((n) => n.map((x) => x.dataset.channel)))], ['NEWS']);
      await choose(page, 'channel', 'ALL'); await choose(page, 'category', 'RESULTS');
      assert.deepEqual(await rows(page), M.filterRows(top, { ...M.FILTER_DEFAULT, category: 'RESULTS' }).map(rowId), phase + ': 실적 merges news EARNINGS with SEC / DART RESULTS');
      await choose(page, 'occurrence', 'REPEAT');
      assert.deepEqual(await rows(page), M.filterRows(top, { ...M.FILTER_DEFAULT, category: 'RESULTS', occurrence: 'REPEAT' }).map(rowId));
      await choose(page, 'category', 'SEC:OFFICERS_DIRECTORS');
      assert.equal(await count(page, '[data-news-filter-empty]'), 1, phase + ': nothing matches');
      assert.equal(await text(page, '[data-news-filter-count]'), '표시 0건 · 최신 30행 안에서 거름');
      await page.locator('[data-news-filter-reset]').focus(); await page.keyboard.press('Enter');
      assert.equal((await focused(page)).newsFilterReset, '', phase + ': the focus stays on 조건 초기화');
      assert.deepEqual(await rows(page), top.map(rowId), phase + ': reset gives every row back');
      assert.deepEqual(await page.locator('[data-occurrence-count]').evaluateAll((n) => n.map((x) => [x.dataset.occurrenceCount, x.textContent])),
        Object.entries(M.counts(top)).map(([k, v]) => [k, v + '건']), phase + ': 5.2.5 counts of the rows in view');
      // ---- 5.2.7 collection state
      tag('status');
      assert.deepEqual(await page.locator('[data-list-state]').evaluateAll((n) => n.map((x) => [x.dataset.listState, x.dataset.listValue])), [['sec', 'LIVE'], ['news', 'LIVE'], ['dart', 'LIVE']]);
      assert.deepEqual(await page.locator('[data-news-refresh]').evaluateAll((n) => n.map((x) => [x.dataset.newsRefresh, x.dataset.newsRefreshResult, x.textContent])),
        M.refreshStatus(P.news).map((r) => [r.source, r.result, M.refreshText(r)]), phase + ': per source refresh words');
      assert.equal(await text(page, '[data-news-refresh=GDELT]'), 'GDELT · 새 뉴스 반영 · 확인 2026-10-14 02:30 UTC');
      assert.equal(await count(page, '[data-news-refresh-badge]'), 0, phase + ': no failure badge for a successful run');
      assert.equal(await text(page, '[data-list-stale=dart]'), 'STALE · DART · 수집 갱신 시각 경과', phase + ': the DART file is overdue at this clock');
      assert.equal(await count(page, '[data-list-stale=sec], [data-list-stale=news]'), 0);
      assert.equal(await text(page, '[data-sec-companies]'), 'SEC 8-K 수집 기업 17곳 · 수집됨 4 · 오래됨 0 · 수집 전 13');
      assert.equal(await page.locator('[data-gdelt-attribution]').getAttribute('href'), 'https://www.gdeltproject.org/');
      assert.equal(await text(page, '[data-score-effect=NONE]'), '점수에 반영하지 않음 · 제목·링크·시각·기업·분류만 표시');
      // ---- 5.2.2 · 5.2.3 · 5.2.4 · 5.2.6: not built
      tag('not computed');
      for (const b of ['5.2.2', '5.2.3', '5.2.4', '5.2.6']) assert.equal(await count(page, '[data-block="' + b + '"] [data-prep]'), 1, phase + ': ' + b + ' 준비 중');
      assert.deepEqual(await page.locator('[data-news-five] [data-na]').allTextContents(), ['미산출', '미산출', '미산출', '미산출', '미산출']);
      assert.match(await text(page, '[data-block="5.2.6"]'), /컨센서스 자료 미연결/);
      assert.match(await text(page, '[data-block="5.2.2"]'), /IA-14/);
      // ---- 5.1: no centre yet
      tag('5.1');
      assert.equal(await count(page, '[data-news-center] [data-na=NO_CENTER]'), 1);
      assert.equal(await count(page, '[data-news-center] [data-na=REL_SOURCE]'), 1, phase + ': 관계 자료 미연결 (REL-SOURCE)');
      assert.equal(await count(page, '[data-news-sketch] [aria-hidden], svg[data-news-sketch][aria-hidden=true]'), 1, phase + ': the sketch is decoration');
      assert.equal(await page.locator('[data-interest-count]').getAttribute('data-interest-count'), '0');
      for (const b of ['5.1.2', '5.1.3']) assert.equal(await count(page, '[data-block="' + b + '"] [data-prep]'), 1);
      // ---- 5.3 tree
      tag('tree');
      assert.deepEqual(await page.locator('[data-tree-node]').evaluateAll((n) => n.map((x) => [x.dataset.treeNode, x.dataset.treeState])),
        [['input', 'ok'], ['class', 'ok'], ['5.1', 'na'], ['5.2', 'ok'], ['5.2.2', 'na'], ['5.2.6', 'na'], ['mine', 'ok']]);
      assert.deepEqual(await page.locator('[data-tree-fact]').evaluateAll((n) => n.map((x) => [x.dataset.treeFact, x.dataset.exampleCount])), [['sec', '5'], ['news', '7'], ['dart', '9'], ['rel', 'NA']]);
      assert.match(await text(page, '[data-tree-fact=sec]'), /^5건 · 파일 기준 2026-10-14 02:30 UTC\s*최신: GOOGL · 8-K · 7\.01,8\.01,9\.01 · 2026-10-12 03:00 UTC$/);
      assert.match(await text(page, '[data-tree-fact=dart]'), /최신: 042700 · 기타 공시 \(Other disclosure\) · 2026-10-02 KST/);
      await page.locator('[data-tree-jump="4-2"]').first().focus(); await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => document.activeElement.id), 's-4-2', phase + ': the jump moves the focus to 4.2');
      // ---- keyboard and boundaries on the full page (details open)
      tag('keyboard');
      await keyboard(page, phase);
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      await boundaries(page, seen, phase + ' (details open)');
      // ---- 5.1 the shared company search picks the centre (keys); a route change reads nothing
      tag('search');
      const at2 = s.requests.length;
      await page.locator('#news-center').focus(); await page.keyboard.type('NVDA');
      await page.locator('#news-center-list [role=option]').first().waitFor();
      await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
      await page.waitForFunction(() => location.hash === '#/news/nvda'); await page.locator('[data-center-code="NASDAQ:NVDA"]').waitFor(); await page.locator('[data-timeline]').waitFor();
      assert.match(await text(page, '[data-center-code]'), /^NVDA · /);
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'CENTER', phase + ': a centre narrows the list to it');
      assert.deepEqual(await rows(page), M.timeline(P, { companyIds: ['nvda'] }).map(rowId));
      assert.deepEqual([...new Set(await rowCompanies(page))], ['nvda']);
      assert.match(await text(page, '[data-news-center] [data-sketch-caption]'), /가운데 원 = NVDA · 점선 = 관계 자료 미연결/);
      assert.equal(await page.evaluate(() => window.IS2.selection.get().id), 'nvda', phase + ': the centre is the selected company (RAM)');
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.deepEqual(reads(at2), [], phase + ': a route change reads nothing new');
      assert.deepEqual(await page.locator('[data-news-refresh]').evaluateAll((n) => n.map((x) => x.textContent)), M.refreshStatus(P.news, { companyIds: ['nvda'] }).map(M.refreshText), phase + ': collection state for the companies in view');
      // ---- ★ 관심 기업: a script click stores nothing; a real click does
      tag('star');
      await page.evaluate(() => document.querySelector('[data-news-star]').click());
      assert.match(await text(page, '[data-news-star-why]'), /^저장하지 않음 · 버튼을 직접 눌러야 저장합니다$/);
      assert.equal(await page.evaluate((k) => localStorage.getItem(k), PERSONAL), null, phase + ': nothing stored without a real click');
      await page.locator('[data-news-star]').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('[data-news-star]').getAttribute('aria-pressed'), 'true');
      assert.equal(await text(page, '[data-news-star-why]'), '관심 기업으로 저장했습니다 · 이 기기');
      assert.deepEqual(await page.evaluate((k) => JSON.parse(localStorage.getItem(k)), PERSONAL), { version: 1, interests: ['nvda'], groups: [] }, phase + ': the home\'s interests key and shape');
      assert.deepEqual(await page.locator('[data-interest]').evaluateAll((n) => n.map((x) => [x.dataset.interest, x.getAttribute('href')])), [['nvda', '#/news/nvda']]);
      assert.deepEqual([...new Set(await page.locator('[data-timeline] [data-importance]').evaluateAll((n) => n.map((x) => x.dataset.importance)))], ['INTEREST'], phase + ': the rows say 관심');
      // ---- 관심 기업 range, importance order, clearing the centre
      tag('range');
      await choose(page, 'scope', 'INTEREST');
      assert.deepEqual(await rows(page), M.timeline(P, { companyIds: ['nvda'] }).map(rowId));
      await page.locator('[data-center-clear]').focus(); await page.keyboard.press('Enter');
      await page.waitForFunction(() => location.hash === '#/news'); await page.locator('[data-news-center] [data-na=NO_CENTER]').waitFor(); await page.locator('[data-timeline]').waitFor();
      assert.equal(await page.evaluate(() => window.IS2.selection.get()), null);
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'INTEREST', phase + ': the chosen range is kept in this tab');
      assert.equal(await page.locator('[data-news-filter=scope] option[value=CENTER]').evaluate((o) => o.disabled), true, phase + ': no centre, no centre range');
      await choose(page, 'scope', 'ALL'); await choose(page, 'order', 'IMPORTANCE');
      const imp = M.filterRows(top, { ...M.FILTER_DEFAULT, order: 'IMPORTANCE' }, { held: [], interests: ['nvda'] });
      assert.deepEqual(await rows(page), imp.map(rowId), phase + ': interest rows first, time order inside a tier');
      assert.equal((await rowCompanies(page))[0], 'nvda');
      await choose(page, 'order', 'TIME');
      await boundaries(page, seen, phase, { stored: [PERSONAL] });
      // ---- reload: the ★ stays (this device), the filters start again, the same reads once
      tag('reload');
      const at3 = await open(page, '#/news/nvda'); await page.reload(); await page.locator('[data-center-code]').waitFor(); await page.locator('[data-timeline]').waitFor();
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.equal(await page.locator('[data-news-star]').getAttribute('aria-pressed'), 'true', phase + ': the ★ survives a reload');
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'CENTER', phase + ': the range starts from the centre again (memory only)');
      assert.deepEqual(reads(at3).filter((n, i, a) => a.indexOf(n) === i), NEWS_READS, phase + ': a reload reads the same set');
      await panel(page, phase);
      await boundaries(page, seen, phase, { stored: [PERSONAL] });
      await ctx.close(); pass++;
    }
    // ================================================================ full data, phone (code route, unknown company)
    {
      phase = '390 full';
      set(FULL);
      const { ctx, page, seen } = await context(390);
      const at = await open(page, '#/news/NASDAQ:NVDA'); await drawn(page); await page.locator('[data-timeline]').waitFor(); await page.locator('[data-center-code]').waitFor();
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.deepEqual(reads(at), NEWS_READS, phase + ': the same reads');
      assert.equal(await page.locator('[data-center-code]').getAttribute('data-center-code'), 'NASDAQ:NVDA', phase + ': a code route resolves through IS2.companies');
      assert.deepEqual(await rows(page), M.timeline(P, { companyIds: ['nvda'] }).map(rowId));
      await panel(page, phase);
      await keyboard(page, phase);
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      await boundaries(page, seen, phase + ' (details open)');
      await choose(page, 'scope', 'ALL');
      assert.equal((await rows(page)).length, M.LIMIT > M.timeline(P).length ? M.timeline(P).length : M.LIMIT);
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': every row open, no horizontal overflow');
      await open(page, '#/news/NOPE.X'); await page.locator('[data-news-center] [data-na=CENTER_NOT_FOUND]').waitFor(); await page.locator('[data-timeline]').waitFor();
      assert.equal(await text(page, '[data-news-center] [data-na=CENTER_NOT_FOUND] p'), '이 이름의 기업을 Universe504 목록에서 찾지 못했습니다 · NOPE.X');
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'ALL', phase + ': an unknown centre shows every company');
      await boundaries(page, seen, phase + ' unknown centre');
      // Without a route company the selected company (IS2.selection, RAM) is the centre; 비우기 clears it in place.
      await page.evaluate(() => window.IS2.selection.set('amd'));
      await open(page, '#/news'); await page.locator('[data-center-code="NASDAQ:AMD"]').waitFor(); await page.locator('[data-timeline]').waitFor();
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'ALL', phase + ': the range chosen in this tab stays');
      await choose(page, 'scope', 'CENTER');
      assert.deepEqual(await rows(page), M.timeline(P, { companyIds: ['amd'] }).map(rowId));
      await page.locator('[data-center-clear]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-news-center] [data-na=NO_CENTER]').waitFor();
      assert.deepEqual([await page.evaluate(() => [location.hash, window.IS2.selection.get(), document.activeElement.id])], [['#/news', null, 'news-center']], phase + ': cleared in place, the focus on the search');
      assert.equal(await page.locator('[data-news-filter=scope]').inputValue(), 'ALL', phase + ': no centre, every company');
      await boundaries(page, seen, phase + ' selected company');
      await ctx.close(); pass++;
    }
    // ================================================================ partial failure: one file missing / failed, a failed refresh run
    {
      phase = 'partial 1440 (news-signals.json 404)';
      set({ ...FULL, 'news-signals.json': { status: 404, body: 'not found' } });
      const { ctx, page, seen } = await context(1440, { allow404: [...UNPUBLISHED, 'news-signals.json'] });
      await open(page); await drawn(page); await page.locator('[data-timeline]').waitFor();
      assert.deepEqual(await rows(page), M.timeline({ sec: P.sec, dart: P.dart }).slice(0, M.LIMIT).map(rowId), phase + ': the SEC and DART rows stay');
      assert.equal(await text(page, '[data-news-list] [data-file-missing=news]'), '뉴스·신호 파일이 아직 게시되지 않았습니다 · 아직 게시되지 않음(HTTP 404)');
      assert.equal(await page.locator('[data-news-band] [data-file="news-signals.json"]').getAttribute('data-file-state'), 'NOT_PUBLISHED');
      assert.deepEqual(await page.locator('[data-tree-fact]').evaluateAll((n) => n.map((x) => [x.dataset.treeFact, x.dataset.exampleCount])), [['sec', '5'], ['news', 'NA'], ['dart', '9'], ['rel', 'NA']]);
      assert.equal(await count(page, '[data-news-refresh], [data-news-attribution]'), 0, phase + ': no refresh line from a missing file');
      assert.equal(await count(page, '[data-news-status] [data-file-missing=news]'), 1);
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    {
      phase = 'partial 390 (sec-disclosures.json 500)';
      set({ ...FULL, 'sec-disclosures.json': { status: 500, body: 'x' } });
      const { ctx, page, seen } = await context(390);
      await open(page); await drawn(page); await page.locator('[data-timeline]').waitFor();
      assert.deepEqual(await rows(page), M.timeline({ news: P.news, dart: P.dart }).slice(0, M.LIMIT).map(rowId));
      assert.match(await text(page, '[data-news-list] [data-file-missing=sec]'), /^SEC 8-K 파일을 읽지 못했습니다 · 읽기 실패\(HTTP 500\)$/);
      assert.equal(await page.locator('[data-news-band] [data-file="sec-disclosures.json"]').getAttribute('data-file-state'), 'FAILED');
      assert.equal(await count(page, '[data-occurrence-label=RELATED_TO_8K]'), 1, phase + ': the IR release whose 8-K is not listed stands alone as a repeat');
      await boundaries(page, seen, phase, { errors: [/status of 500/] });
      await ctx.close(); pass++;
    }
    {
      phase = 'partial 1440 (GDELT 429 run)';
      const failedRun = X.news(X.NOW, { scenario: 'GDELT_429' });
      set({ ...FULL, 'news-signals.json': { json: failedRun } });
      const { ctx, page, seen } = await context(1440);
      await open(page); await drawn(page); await page.locator('[data-timeline]').waitFor();
      assert.equal(await page.locator('[data-news-refresh-badge]').getAttribute('data-news-refresh-badge'), 'PARTIAL_FAILED');
      assert.equal(await text(page, '[data-news-refresh-badge]'), '일부 갱신 실패');
      const st = M.refreshStatus(failedRun);
      assert.deepEqual(await page.locator('[data-news-refresh]').evaluateAll((n) => n.map((x) => [x.dataset.newsRefreshResult, x.className, x.textContent])), st.map((r) => [r.result, 'err', M.refreshText(r)]));
      assert.match(await text(page, '[data-news-refresh=GDELT]'), /이전 자료 유지 · 마지막 성공 .* · 최근 갱신 실패\(GDELT HTTP_429/);
      assert.deepEqual(await rows(page), M.timeline({ ...P, news: failedRun }).slice(0, M.LIMIT).map(rowId), phase + ': carried items stay listed');
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    // ================================================================ empty: the offline NOT_AVAILABLE files; every list missing
    {
      phase = 'empty 390';
      const E = X.empty();
      set({ 'sec-disclosures.json': { json: E.sec }, 'news-signals.json': { json: E.news }, 'dart-disclosures.json': { json: E.dart } });
      const { ctx, page, seen } = await context(390);
      await open(page); await drawn(page); await page.locator('[data-news-list] [data-na=NO_ROWS]').waitFor();
      assert.equal(await text(page, '[data-news-list] [data-na=NO_ROWS] p'), '표시할 공시·뉴스가 없습니다');
      assert.equal(await count(page, '[data-news-list] [data-na=NO_ROWS] [data-mascot=plain]'), 1);
      assert.deepEqual(await page.locator('[data-occurrence-count]').allTextContents(), ['0건', '0건', '0건']);
      assert.deepEqual(await page.locator('[data-list-state]').evaluateAll((n) => n.map((x) => x.dataset.listValue)), ['NOT_AVAILABLE', 'NOT_AVAILABLE', 'NOT_AVAILABLE']);
      assert.equal(await text(page, '[data-dart-reason]'), 'DART · NOT_AVAILABLE · NOT_COLLECTED');
      assert.deepEqual(await page.locator('[data-news-refresh]').allTextContents(), ['GDELT · 이 파일은 수집 없이 만들어짐', '회사 IR · 이 파일은 수집 없이 만들어짐']);
      assert.equal(await count(page, '[data-list-stale]'), 0, phase + ': a NOT_AVAILABLE file is never STALE');
      assert.deepEqual(await page.locator('[data-tree-fact]').evaluateAll((n) => n.map((x) => x.dataset.exampleCount)), ['0', '0', '0', 'NA']);
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    {
      phase = 'empty 1440 (every list 404)';
      set(Object.fromEntries(LISTS.map((n) => [n, { status: 404, body: 'not found' }])));
      const { ctx, page, seen } = await context(1440, { allow404: [...UNPUBLISHED, ...LISTS] });
      await open(page); await drawn(page); await page.locator('[data-news-list] [data-na=LISTS_FAILED]').waitFor();
      assert.match(await text(page, '[data-news-list] [data-na=LISTS_FAILED]'), /공시·뉴스 파일을 하나도 읽지 못했습니다 · SEC 8-K 아직 게시되지 않음\(HTTP 404\)/);
      assert.equal(await count(page, '[data-news-list] [data-mascot=alarm]'), 1);
      assert.deepEqual(await page.locator('[data-news-band] [data-file]').evaluateAll((n) => n.map((x) => x.dataset.fileState)), ['NOT_PUBLISHED', 'NOT_PUBLISHED', 'NOT_PUBLISHED']);
      assert.equal(await count(page, '[data-news-center] [data-na=NO_CENTER]'), 1, phase + ': 5.1 does not depend on the lists');
      await panel(page, phase);
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    // ================================================================ error: the layer did not load (LOADER_FAILED); the live file 404
    {
      phase = 'error 390';
      set(FULL);
      const { ctx, page, seen } = await context(390, { allow404: [...UNPUBLISHED, 'data.js'] });
      await page.route('**/data.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      const at = await open(page); await drawn(page);
      assert.equal(await count(page, '[data-news-slot] [data-state=error][data-na=LOADER_FAILED]'), 3, phase + ': every section slot shows the failure');
      assert.equal(await count(page, '[data-news-slot] [data-mascot=alarm]'), 3);
      assert.match(await text(page, '[data-news-slot="4-2"] [data-state=error]'), /층을 불러오지 못해 공시·뉴스를 그리지 못했습니다/);
      assert.equal(await page.locator('[data-news-band] [data-file-state]').getAttribute('data-file-state'), 'LOADER_FAILED');
      assert.deepEqual([await count(page, '[data-state=loading]'), await count(page, '[data-block]'), await count(page, '[data-private-panel]')], [0, 0, 0]);
      await page.locator('[data-load-failed]').waitFor();
      assert.deepEqual(reads(at), [], phase + ': nothing is read');
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    {
      phase = 'error 1440 (screen-news-live.js 404)';
      set(FULL);
      const { ctx, page, seen } = await context(1440, { allow404: [...UNPUBLISHED, 'screen-news-live.js'] });
      await page.route('**/screen-news-live.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      await open(page); await drawn(page);
      assert.equal(await page.evaluate(() => window.IS2.ready.then(() => 'READY', (e) => e.message)), 'LOADER_FAILED screen-news-live.js');
      assert.equal(await count(page, '[data-news-slot] [data-state=error][data-na=LOADER_FAILED]'), 3, phase + ': the screen\'s error state');
      await page.locator('[data-load-failed]').waitFor();
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    console.log('web_app_news_browser_test: PASS (' + pass + ' contexts: full 1440, full 390, partial ×3, empty ×2, error, live-file error)');
  } catch (e) {
    console.error('web_app_news_browser_test: FAIL at ' + phase);
    throw e;
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
