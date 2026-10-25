'use strict';
// New frontend P2-1 · menu 0 홈 · 기업검색 (feature 1.1.1–1.1.4; draft boards Main / MMain) in a real browser, at 1440 and 390.
// Builds the development site (tools/web_app_test_site.js), serves the live-only score inputs and a filing list as synthetic
// fixtures, and checks the built page in Chromium:
//  - Home: hero, the search box in the first paint; before IS2.ready typing works and the list says 불러오는 중 (a layer file is
//    held back); then the company index: "nv" and a Korean name from the reviewed names file give ARIA combobox / listbox options
//    (at most 8, no price, cap, score or rank); the input element is never rebuilt and keys are ignored while composing.
//  - Selection: ArrowDown + Enter (implicit submission clicks the default button) and a pointer click navigate to the company page
//    and save the recent search with that real click; a synthetic el.click() / dispatchEvent navigates but saves nothing (the store
//    refuses it); a submit without an active option goes to #/company/<query> and saves nothing. Back home the recent chip shows the
//    company title; 최근 지우기 (a real click) clears it.
//  - Favorites: empty prefs show the developer default (TARGET 19, labelled 개발자 기본값 · 추천 아님, 8 chips then +N 더 보기); the
//    ★ toggle on the company page writes prefs only with a real click (disabled before IS2.ready); home then shows the favorite and
//    no default; unstarring brings the default back.
//  - Company page: h1[data-result-code] as given; title, ticker, Universe code and membership; QGV card numbers are exactly the
//    layer's row (Q · G · V · total · rank) or NA with the reasonText, V label = row.source_label; macro, news (fixture filings),
//    portfolio (device store not opened) from the layer; no digit in a pending block and none of the draft's example numbers; the
//    technical card asks for nothing. Unknown id: the fixed sentence, no values. IS2.selection keeps the company on #/qgv.
//  - Investor story: the module's checked text, labelled translation / summary, the English excerpt, person and a source link
//    (target _blank, rel noopener noreferrer).
//  - Boundaries: every request same-origin, data requests only names in IS2.data.FILES; nothing written to localStorage /
//    sessionStorage / IndexedDB without a real click; no console error (but the intended 404 of an unpublished live-only file), no
//    CSP violation, no [style], no horizontal overflow at 390.
// Synthetic data only (fixtures); no price is requested or shown.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const SEC = require('./sec_disclosures_fixture.js');

// The sec-qgv2.json fixture rows were collected 2026-10-13 (14-day window): a fixed clock keeps them LIVE.
const NOW = '2026-10-14T03:00:00.000Z';
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-universe-shares.json', 'forward-validation-ledger.json'];
const RECENT_KEY = 'investment.web.v1.recent-search', PERSONAL_KEY = 'investment.web.v1.personal';
// Draft example values and words (the draft's numbers are examples and must never show).
const DRAFT = /예시|EXA\b|상승 깃발|회복 후반|상승 초입|보유 비중 6%|모델 적합 비중 8%|23 \/ 498|QGV 72\b/;
let phase = 'START';

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'sec-disclosures.json': { json: SEC.payload(Date.parse(NOW)) } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const pageFiles = new Set([...R.scripts(), ...fs.readdirSync(R.NEW)]);
  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      const phone = width < 720, context = await browser.newContext({ viewport: { width, height } });
      await context.clock.setFixedTime(new Date(NOW));
      await context.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const tag = (p) => { phase = width + ' ' + p; };
      const ready = () => page.evaluate(() => window.IS2.ready.then(() => window.IS2.loadState()));
      const store = () => site.storage(page);
      const common = async () => {
        assert.equal(await page.locator('[style]').count(), 0, phase + ': no style attribute');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow');
        for (const t of await page.locator('[data-pending]').allTextContents()) assert.doesNotMatch(t, /\d/, phase + ': pending block has no number: ' + t);
        assert.doesNotMatch(await page.locator('main').innerText(), DRAFT, phase + ': no draft example value');
      };
      const go = async (hash, selector) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator(selector).first().waitFor(); };
      const options = () => page.locator('#q-list [role=option]');
      const typed = async (text) => { await page.locator('[data-search-input]').fill(text); await page.waitForFunction(() => { const l = document.querySelector('#q-list'); return l && !l.hidden && !l.querySelector('[data-search-state=loading]'); }); };

      // ---------------------------------------------------------------- before IS2.ready (engines.js held back)
      tag('before ready');
      let release; const gate = new Promise((r) => { release = r; });
      await page.route('**/engines.js', async (route) => { await gate; await route.continue(); });
      await page.goto(s.base + '#/'); await page.locator('main[data-route=search]').waitFor();
      assert.match(await page.locator('.hero-title').textContent(), /어떤 기업을 볼까요\?/);
      assert.equal(await page.locator('.hero-underline').count(), 1, 'the red hand underline');
      const marked = await page.evaluate(() => { const i = document.querySelector('[data-search-input]'); i.__mark = 1; return [i.id, i.getAttribute('role'), i.getAttribute('aria-controls'), i.getAttribute('aria-expanded')]; });
      assert.deepEqual(marked, ['q', 'combobox', 'q-list', 'false']);
      assert.ok(['WAITING', 'LOADING'].includes(await page.evaluate(() => window.IS2.loadState())), 'the layer is not there yet');
      await page.locator('[data-search-input]').fill('nv');
      assert.equal(await page.locator('#q-list [data-search-state=loading]').textContent(), '불러오는 중', 'typing works before the layer; the list says 불러오는 중');
      assert.equal(await page.locator('[data-search-input]').getAttribute('aria-expanded'), 'true');
      assert.equal(await page.locator('[data-quote] [data-pending]').count(), 1, 'the story waits for the layer');
      await common();
      // The ★ toggle is off before IS2.ready.
      await page.evaluate(() => { location.hash = '#/company/nvda'; }); await page.locator('[data-result-code="nvda"]').waitFor();
      assert.equal(await page.locator('[data-favorite]').isDisabled(), true, '★ is off before IS2.ready');
      assert.equal(await page.locator('[data-card]').count(), 5);
      await common();
      release();
      assert.equal(await ready(), 'READY');
      await page.locator('[data-favorite]:not([disabled])').waitFor();
      assert.deepEqual([(await store()).local, (await store()).session, (await store()).idb], [0, 0, 0], 'nothing stored by opening');

      // ---------------------------------------------------------------- search (after ready)
      tag('search');
      await go('#/', 'main[data-route=search] [data-search-input]');
      await page.locator('[data-home-chips] [data-favorites]').waitFor();
      await page.evaluate(() => { document.querySelector('[data-search-input]').__mark = 1; });
      await typed('nv');
      const nv = await page.evaluate(() => [...document.querySelectorAll('#q-list [role=option]')].map((o) => ({ id: o.id, key: o.dataset.entityKey, sel: o.getAttribute('aria-selected'), text: o.textContent })));
      assert.ok(nv.length >= 1 && nv.length <= 8, 'at most 8 options: ' + nv.length);
      assert.ok(nv.some((o) => o.key === 'COMPANY:nvda'), 'nv finds NVIDIA');
      assert.ok(nv.every((o) => o.sel === 'false' && /^q-opt-\d+$/.test(o.id) && /^COMPANY:/.test(o.key)), 'options are role=option, not selected yet, companies only');
      for (const o of nv) assert.doesNotMatch(o.text, /\d+\.\d|순위|시총|점수|\$/, 'no score, rank, cap or price in an option: ' + o.text);
      assert.equal(await page.locator('#q-list').getAttribute('role'), 'listbox');
      // EntitySearch order: an exact or prefix match before a substring match.
      const order = await page.evaluate(async () => { await window.IS2.ready; const ES = window.EntitySearch; return [...document.querySelectorAll('#q-list [role=option]')].map((o) => o.dataset.entityKey); });
      assert.equal(order[0], 'COMPANY:nvda', 'the ticker-prefix match comes first');
      // Korean name (reviewed names table) and IME safety: the same input element, no key handling while composing.
      await typed('퀄컴');
      assert.deepEqual(await options().evaluateAll((n) => n.map((o) => o.dataset.entityKey)), ['COMPANY:qcom']);
      assert.match(await options().first().textContent(), /^퀄컴 · QCOM/);
      assert.match(await options().first().textContent(), /NASDAQ:QCOM/); assert.match(await options().first().textContent(), /TARGET · Universe504 둘 다/);
      const ime = await page.evaluate(() => { const i = document.querySelector('[data-search-input]'); i.dispatchEvent(new CompositionEvent('compositionstart'));
        i.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, isComposing: true })); const during = i.getAttribute('aria-activedescendant');
        i.dispatchEvent(new CompositionEvent('compositionend')); return { mark: i.__mark, during }; });
      assert.deepEqual(ime, { mark: 1, during: null }, 'the input is never rebuilt; ArrowDown while composing does nothing');
      // A Universe-only company: its code and membership.
      await typed('NYSE:FIX');
      assert.match(await options().first().textContent(), /NYSE:FIX/); assert.match(await options().first().textContent(), /Universe504/);
      await typed('zzzzqqq'); assert.equal(await page.locator('#q-list [data-search-state=empty]').textContent(), '일치하는 기업이 없습니다');
      await page.keyboard.press('Escape'); assert.equal(await page.locator('#q-list').isHidden(), true, 'Escape closes the list');
      assert.equal((await store()).local, 0, 'typing stores nothing');
      await common();

      // ---------------------------------------------------------------- selection: synthetic first (navigation yes, recent no)
      tag('synthetic');
      await typed('amd');
      await page.evaluate(() => document.querySelector('#q-list [role=option]').click());
      await page.locator('[data-result-code="amd"]').waitFor();
      assert.equal((await store()).local, 0, 'a synthetic el.click() navigates but saves nothing');
      await go('#/', 'main[data-route=search] [data-search-input]');
      await typed('msft'); await page.locator('[data-search-input]').press('ArrowDown');
      assert.equal(await page.locator('[data-search-input]').getAttribute('aria-activedescendant'), 'q-opt-0');
      await page.evaluate(() => document.querySelector('[data-search-form] button[type=submit]').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })));
      await page.locator('[data-result-code="msft"]').waitFor();
      assert.equal((await store()).local, 0, 'a dispatched click navigates but saves nothing');
      // Submit without an active option: the P0 path, nothing saved.
      await go('#/', 'main[data-route=search] [data-search-input]');
      await page.locator('[data-search-input]').fill('NYSE:FIX'); await page.locator('[data-search-form] button[type=submit]').click();
      await page.locator('[data-result-code="NYSE:FIX"]').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/company/NYSE%3AFIX');
      assert.equal((await store()).local, 0, 'a submit without a chosen option saves nothing');

      // ---------------------------------------------------------------- real selection: keyboard, then pointer
      tag('real selection');
      await go('#/', 'main[data-route=search] [data-search-input]');
      await typed('nvd'); await page.locator('[data-search-input]').press('ArrowDown');
      assert.equal(await options().first().getAttribute('aria-selected'), 'true');
      await page.locator('[data-search-input]').press('Enter');
      await page.locator('[data-result-code="nvda"]').waitFor();
      assert.deepEqual(JSON.parse((await store()).localItems[RECENT_KEY]), ['COMPANY:nvda'], 'ArrowDown + Enter (the default button\'s click) saves the recent search');
      await go('#/', 'main[data-route=search] [data-search-input]');
      await typed('퀄컴'); await options().first().click();
      await page.locator('[data-result-code="qcom"]').waitFor();
      assert.deepEqual(JSON.parse((await store()).localItems[RECENT_KEY]), ['COMPANY:qcom', 'COMPANY:nvda'], 'a pointer click saves it first');
      assert.deepEqual(Object.keys((await store()).localItems), [RECENT_KEY], 'only the recent key, no query text');
      await go('#/', 'main[data-route=search] [data-recent]');
      assert.deepEqual(await page.locator('[data-recent] [data-chip]').evaluateAll((n) => n.map((a) => [a.dataset.chip, a.textContent, a.getAttribute('href')])),
        [['qcom', '퀄컴 · QCOM', '#/company/qcom'], ['nvda', 'NVIDIA · NVDA', '#/company/nvda']], 'recent chips show titles, newest first');
      await common();

      // ---------------------------------------------------------------- favorites: developer default, ★ toggle
      tag('favorites');
      const def = page.locator('[data-favorites=DEFAULT]');
      assert.equal(await def.locator('[data-default-label]').textContent(), '기본 목록 · 개발자 기본값 · 추천 아님');
      const targets = await page.evaluate(async () => { await window.IS2.ready; const c = await window.IS2.data.static('actual-catalog.json'); return window.DeviceWatchlist.identities(c).map((x) => x.company_id); });
      assert.equal(targets.length, 19);
      assert.deepEqual(await def.locator(':scope > [data-chip]').evaluateAll((n) => n.map((a) => a.dataset.chip)), targets.slice(0, 8), 'the first 8 of the TARGET 19, in DeviceWatchlist order');
      assert.equal(await def.locator('[data-default-more]').textContent(), '+11 더 보기');
      await def.locator('[data-default-more]').click();
      assert.equal(await def.locator('[data-chip]:visible').count(), 19, '+N 더 보기 shows the rest (RAM only)');
      assert.equal(await def.locator('[data-default-more]').getAttribute('aria-expanded'), 'true');
      assert.equal((await store()).localItems[PERSONAL_KEY], undefined, 'the default list is never written');
      await go('#/company/amd', '[data-favorite]:not([disabled])');
      assert.equal(await page.locator('[data-favorite]').getAttribute('aria-pressed'), 'false');
      await page.evaluate(() => document.querySelector('[data-favorite]').click());
      assert.equal((await store()).localItems[PERSONAL_KEY], undefined, 'a synthetic click on ★ writes nothing');
      await page.locator('[data-favorite]').click();
      assert.equal(await page.locator('[data-favorite]').getAttribute('aria-pressed'), 'true');
      assert.deepEqual(JSON.parse((await store()).localItems[PERSONAL_KEY]), { version: 1, interests: ['amd'], groups: [] }, 'a real click on ★ writes prefs');
      await go('#/', 'main[data-route=search] [data-favorites=MINE]');
      assert.deepEqual(await page.locator('[data-favorites=MINE] [data-chip]').evaluateAll((n) => n.map((a) => a.textContent)), ['★ AMD · AMD']);
      assert.equal(await page.locator('[data-favorites=DEFAULT]').count(), 0, 'the first favorite replaces the developer default');
      await common();
      // Unstar (a group holding the id keeps the validator happy: the id leaves the group too).
      await page.evaluate(() => 0);
      await go('#/company/amd', '[data-favorite][aria-pressed=true]:not([disabled])');
      await page.locator('[data-favorite]').click();
      assert.deepEqual(JSON.parse((await store()).localItems[PERSONAL_KEY]), { version: 1, interests: [], groups: [] });
      await go('#/', 'main[data-route=search] [data-favorites=DEFAULT]');
      // 최근 지우기: a real click clears the recent searches.
      await page.locator('[data-recent-clear]').click();
      assert.equal((await store()).localItems[RECENT_KEY], undefined, '최근 지우기 cleared the list');
      assert.equal(await page.locator('[data-recent]').count(), 0);

      // ---------------------------------------------------------------- company page values
      tag('company');
      await go('#/company/nvda', '[data-card=qgv] [data-qgv]');
      const facts = await page.locator('[data-result-facts] .facts-line').textContent();
      assert.match(facts, /^NVDA · NASDAQ:NVDA · TARGET · Universe504 둘 다/);
      assert.equal(await page.locator('.result-name').textContent(), 'NVIDIA · NVDA');
      assert.equal(await page.locator('.result-name').getAttribute('data-result-code'), 'nvda');
      await page.waitForFunction(() => document.querySelectorAll('[data-card] [data-pending]').length === 0);
      const want = await page.evaluate(async () => {
        const Q = window.IS2.qgv, pg = await Q.page(), r = Q.row(pg, 'nvda'), f = (v) => (typeof v === 'number' && Number.isFinite(v) ? new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v) : null);
        return { q: f(r.score.q), g: f(r.score.g), v: f(r.score.v), total: f(r.score.total), rank: r.rank.official, of: r.rank.of, label: Q.rankLabel(pg), source: r.source_label,
          why: { v: r.score.v === null ? Q.reasonText(r.na_reason.v) : null, rank: r.rank.official === null ? Q.reasonText(r.na_reason.rank) : null } };
      });
      const qgv = await page.evaluate(() => { const c = document.querySelector('[data-card=qgv]'), val = (a) => c.querySelector('[data-axis=' + a + '] .qval').textContent;
        return { q: val('Q'), g: val('G'), v: val('V'), text: c.querySelector('.card-body').innerText, fills: [...c.querySelectorAll('.qbar-fill')].map((x) => Number(x.getAttribute('width'))) }; });
      assert.equal(qgv.q, want.q ?? 'NA'); assert.equal(qgv.g, want.g ?? 'NA'); assert.equal(qgv.v, want.v ?? 'NA');
      assert.ok(want.q && want.g, 'the fixture scores Q and G for nvda');
      assert.equal(want.v, null, 'no device price: V is NA'); assert.ok(qgv.text.includes('V NA · ' + want.why.v), 'V shows its reason');
      assert.ok(qgv.text.includes('V 출처: ' + want.source), 'the V label is row.source_label');
      if (want.total) assert.ok(qgv.text.includes('QGV 종합 ' + want.total)); else assert.match(qgv.text, /QGV 종합 NA/);
      if (want.rank === null) assert.ok(qgv.text.includes('순위 NA · ' + want.why.rank)); else assert.ok(qgv.text.includes('순위 ' + want.rank + ' / ' + want.of + ' · ' + want.label));
      const allowed = new Set([want.q, want.g, want.v, want.total, String(want.rank), String(want.of)].filter((x) => x && x !== 'null'));
      for (const n of qgv.text.match(/\d+(?:\.\d+)?/g) || []) assert.ok(allowed.has(n), 'every number in the QGV card is the layer\'s: ' + n);
      assert.equal(qgv.fills.length, 2, 'two filled bars (Q, G); V is a dashed empty track');
      assert.equal(await page.locator('[data-card=technical]').innerText().then((t) => /가격 이력은 기술적 분석 화면에서 \[불러오기\]를 눌러야 계산합니다/.test(t)), true);
      const news = await page.locator('[data-card=news] [data-news-item]').allTextContents();
      assert.ok(news.length >= 1 && news.length <= 5, 'the fixture filings for nvda');
      for (const n of news) assert.match(n, /^\[공시 · SEC\] 8-K(\/A)? · .+ · \d{4}-\d{2}-\d{2}$/);
      assert.match(await page.locator('[data-card=portfolio]').innerText(), /이 기기 저장소가 아직 없습니다/);
      assert.match(await page.locator('[data-card=portfolio]').innerText(), /비중은 포트폴리오 화면에서/);
      assert.ok((await page.locator('[data-card=macro] .card-body').innerText()).length > 0);
      assert.deepEqual(await page.locator('[data-card]').evaluateAll((n) => n.map((x) => x.dataset.card)), ['qgv', 'technical', 'macro', 'news', 'portfolio']);
      assert.deepEqual(await page.locator('[data-card]').evaluateAll((n) => n.map((x) => (x.matches('a') ? x.getAttribute('href') : x.querySelector('a.more').getAttribute('href')))),
        ['#/qgv', '#/technical', '#/macro', '#/news', '#/portfolio'], 'each card leads to its menu');
      await common();
      // A company without filings in the fixture.
      await go('#/company/NYSE:FIX', '[data-card=news] [data-na]');
      assert.equal(await page.locator('[data-card=news] [data-na]').textContent(), '공개 파일에 이 기업 소식이 없습니다');
      assert.match(await page.locator('[data-card=portfolio]').innerText(), /TARGET 밖 기업이라/);
      assert.match(await page.locator('[data-result-facts] .facts-line').textContent(), /^FIX · NYSE:FIX · Universe504/);
      // Selection kept across menus (RAM).
      await go('#/qgv', 'main[data-route=qgv]');
      assert.deepEqual(await page.evaluate(() => window.IS2.selection.get()), { id: 'NYSE:FIX' }, 'the selected company stays on #/qgv');
      // Unknown id.
      await go('#/company/NO_SUCH_CO_X', '[data-not-found]');
      assert.equal(await page.locator('[data-not-found]').textContent(), '이 이름의 기업을 찾지 못했습니다');
      assert.equal(await page.locator('[data-qgv]').count(), 0, 'no values for an unknown id');
      assert.equal(await page.locator('[data-card] [data-na="NOT_FOUND"]').count(), 4);
      assert.equal(await page.locator('main [data-search-input]').count(), 1, 'the search box stays');
      assert.deepEqual(await page.evaluate(() => window.IS2.selection.get()), { id: 'NYSE:FIX' }, 'an unknown id does not replace the selection');
      await common();

      // ---------------------------------------------------------------- investor story
      tag('quote');
      await go('#/', '[data-quote][data-quote-id]');
      const q = await page.evaluate(() => { const el = document.querySelector('[data-quote]'), Q = window.HomeQuotes.byId(el.dataset.quoteId), a = el.querySelector('[data-quote-link]');
        return { type: el.dataset.quoteType, want: Q.type, ko: el.querySelector('.quote-ko').textContent, wantKo: Q.ko, en: el.querySelector('.quote-en').textContent, wantEn: Q.headline_en, who: el.querySelector('.quote-who').textContent,
          speaker: Q.speaker.ko, kind: el.querySelector('.quote-kind').textContent, src: el.querySelector('.quote-src').textContent, source: Q.source, href: a.getAttribute('href'), url: Q.url, rel: a.getAttribute('rel'), target: a.getAttribute('target') }; });
      assert.equal(q.type, q.want); assert.equal(q.ko, q.wantKo); assert.ok(q.en.endsWith(q.wantEn)); assert.ok(q.who.includes(q.speaker)); assert.ok(q.src.includes(q.source));
      assert.deepEqual([q.href, q.rel, q.target], [q.url, 'noopener noreferrer', '_blank']);
      assert.match(q.kind, q.type === 'STORY' ? /일화 요약 · 직접 인용 아님 · 우리말 요약/ : /직접 인용 · 우리말 번역/);

      // ---------------------------------------------------------------- phone and boundaries
      tag('boundaries');
      if (phone) {
        assert.equal(await page.locator('.tabbar').isVisible(), true);
        await typed('a'); await common();
        assert.ok(await page.locator('#q-list').evaluate((l) => { const b = l.getBoundingClientRect(); return b.left >= 0 && b.right <= window.innerWidth + 1; }), 'the list fits the 390 screen');
        await page.keyboard.press('Escape');
        await go('#/company/nvda', '[data-card=qgv] [data-qgv]'); await common();
        await page.screenshot({ path: require('node:path').join(require('node:os').tmpdir(), 'web-app-home-390.png'), fullPage: true });
      }
      assert.equal(await page.evaluate(() => window.__csp), 0, 'no CSP violation');
      assert.deepEqual(seen.outside, [], 'no request leaves the origin');
      const data = seen.requests.map((u) => decodeURIComponent(new URL(u).pathname.slice(1))).filter((n) => n && !pageFiles.has(n));
      const FILES = await page.evaluate(() => window.IS2.data.FILES);
      assert.deepEqual([...new Set(data.filter((n) => !FILES.includes(n)))], [], 'every data request is a public file in IS2.data.FILES');
      assert.ok(!data.includes('sec-universe-shares.json'), 'search needs no share counts (static files only)');
      assert.deepEqual(seen.errors, [], 'no console error but the intended 404s');
      assert.equal(await page.evaluate(() => window.IS2.action.blocked()), 0, 'no layer call tried a private request or a write outside a click');
      const st = await store(); assert.deepEqual([st.session, st.idb], [0, 0], 'no sessionStorage / IndexedDB');
      await context.close();
    }
    console.log('web app home: search, recent, favorites, company cards, story and boundaries ok at 1440 and 390');
  } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
