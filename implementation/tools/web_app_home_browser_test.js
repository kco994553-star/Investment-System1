'use strict';
// New frontend P2-1 · menu 0 홈 · 기업검색 (feature 1.1.1–1.1.4; draft boards Main / MMain) in a real browser, at 1440 and 390.
// Builds the development site (tools/web_app_test_site.js), serves the live-only score inputs and a filing list as synthetic
// fixtures, and checks the built page in Chromium:
//  - Home: hero, the search box in the first paint; before IS2.ready typing works and the list says 불러오는 중 (a layer file is
//    held back), Escape keeps the text, leaving the box hides the list; the hand-over on the same render (typed text becomes
//    options on the same input, focus kept, one repaint per keystroke) and a route left before IS2.ready is not filled; then the
//    shared company search (search-part-live.js, DC-23): "nv" and an English name give ARIA combobox / listbox options (at most
//    8, Universe504 only, no price, cap, score or rank); Korean text gives the fixed hint, a TARGET-only company is not found,
//    WBD says 상장 종료; the input has the phone search keyboard attributes; the input element is never rebuilt, keys are ignored
//    while composing and the list follows an open composition.
//  - Selection: ArrowDown + Enter (implicit submission clicks the default button) and a pointer click navigate to the company page
//    and save the recent search with that real click; a synthetic el.click() / dispatchEvent navigates but saves nothing (the store
//    refuses it); a submit without an active option goes to the single exact match (NVDA -> nvda), else stays with the no-match
//    line in the list (nv: options, no navigation), and saves nothing; an unknown id typed in the address shows the not-found
//    sentence. Back home the recent chip shows the company title; 최근 지우기 (a real click)
//    clears it and the focus stays in the chip block.
//  - Favorites: empty prefs show the developer default (TARGET 19, labelled 개발자 기본값 · 추천 아님, 8 chips then +N 더 보기); the
//    ★ toggle (accessible name 즐겨찾기, state in aria-pressed) on the company page writes prefs only with a real click (disabled
//    before IS2.ready); home then shows the favorite and no default; unstarring also takes the id out of a group that holds it;
//    with no favorite left the default comes back; unreadable stored favorites still show the default (DC-22).
//  - Company page: h1[data-result-code] as given; title, ticker, Universe code and membership; QGV card numbers are exactly the
//    layer's row (Q · G · V · total · rank) or NA with the reasonText, V label = row.source_label; macro equal to
//    IS2.engines.macro.current() (a synthetic lights file at 1440: label and counts; the built file at 390: NO_LIGHTS), news lines
//    exactly the fixture's newest filings for the company, portfolio (device store not opened) from the layer; tap targets 44 px; no digit in a pending block and none of the draft's example numbers; the
//    technical card asks for nothing. Unknown id: the fixed sentence, no values. IS2.selection keeps the company on #/qgv.
//  - Investor story: the module's checked text, labelled translation / summary (a STORY and a DIRECT item are both shown, by a
//    stubbed Math.random), the English excerpt, person and a source link (target _blank, rel noopener noreferrer).
//  - Boundaries: every request same-origin, data requests only names in IS2.data.FILES; nothing written to localStorage /
//    sessionStorage / IndexedDB without a real click; no console error (but the intended 404 of an unpublished live-only file), no
//    CSP violation, no [style], no horizontal overflow at 390.
//  - Hover only highlights: the 검색 click submits the typed text, not the hovered option.
//  - Two more contexts: a device store seeded by the test (portfolio card held yes / no) and screen-search-live.js answering 404
//    (LOADER_FAILED: the company header's fixed sentence, ★ off, the shell notice, every facade refuses, no uncaught error).
// Synthetic data only (fixtures); no price is requested or shown.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const SEC = require('./sec_disclosures_fixture.js');
const { EMPTY } = require('./empty_public_screens.js');

// The sec-qgv2.json fixture rows were collected 2026-10-13 (14-day window): a fixed clock keeps them LIVE.
const NOW = '2026-10-14T03:00:00.000Z';
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-universe-shares.json', 'forward-validation-ledger.json'];
const RECENT_KEY = 'investment.web.v1.recent-search', PERSONAL_KEY = 'investment.web.v1.personal';
// Draft example values and words (the draft's numbers are examples and must never show).
const DRAFT = /예시|EXA\b|상승 깃발|회복 후반|상승 초입|보유 비중 6%|모델 적합 비중 8%|23 \/ 498|QGV 72\b/;
let phase = 'START';
// A synthetic macro-screen.json with three public lights (employment and curve lit, inflation not): 경고, 2 of 3 (the
// macro_lights_browser_test fixture). Not market data.
function macroScreen() {
  const A = 'a'.repeat(64), B = 'b'.repeat(64), AT = '2026-01-01T00:00:00+00:00', p = structuredClone(EMPTY['macro-screen.json']);
  p.state = 'LIVE'; p.sources = [{ agency: 'BLS', sha256: A, acquired_at: AT }, { agency: 'TREASURY', sha256: B, acquired_at: AT }];
  const L = p.data.macro_lights_v1.lights;
  Object.assign(L.employment, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2025-12', inputs: [{ sha256: A, acquired_at: AT }], values: { period: '2025-12', avg3: 4.6, low12: 4.0, low12_count: 12, gap: 0.6 } });
  Object.assign(L.inflation, { state: 'LIVE', lit: false, reason: 'NOT_LIT', as_of: '2025-12', inputs: [{ sha256: A, acquired_at: AT }], values: { period: '2025-12', base_period: '2024-12', yoy: 0.03 } });
  Object.assign(L.curve, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2025-12-31', inputs: [{ sha256: B, acquired_at: AT }], values: { date: '2025-12-31', ten_year: 4.2, three_month: 4.5, spread: -0.3, run_days: 25 } });
  return p;
}

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'sec-disclosures.json': { json: SEC.payload(Date.parse(NOW)) } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const pageFiles = new Set([...R.scripts(), ...fs.readdirSync(R.NEW)]);
  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      const phone = width < 720, context = await browser.newContext({ viewport: { width, height } });
      s.fixture('macro-screen.json', phone ? null : { json: macroScreen() });
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
      // domcontentloaded: when loader.js inserts LOAD_ORDER before the window load event, the held file holds 'load' as well.
      await page.goto(s.base + '#/', { waitUntil: 'domcontentloaded' }); await page.locator('main[data-route=search]').waitFor();
      assert.match(await page.locator('.hero-title').textContent(), /어떤 기업을 볼까요\?/);
      assert.equal(await page.locator('.hero-underline').count(), 1, 'the red hand underline');
      const marked = await page.evaluate(() => { const i = document.querySelector('[data-search-input]'); i.__mark = 1; return [i.id, i.getAttribute('role'), i.getAttribute('aria-controls'), i.getAttribute('aria-expanded')]; });
      assert.deepEqual(marked, ['q', 'combobox', 'q-list', 'false']);
      assert.ok(['WAITING', 'LOADING'].includes(await page.evaluate(() => window.IS2.loadState())), 'the layer is not there yet');
      const input = page.locator('[data-search-input]'), list = page.locator('#q-list');
      await input.fill('nv');
      assert.equal(await page.locator('#q-list [data-search-state=loading]').textContent(), '불러오는 중', 'typing works before the layer; the list says 불러오는 중');
      assert.equal(await input.getAttribute('aria-expanded'), 'true');
      assert.equal(await page.locator('[data-quote] [data-pending]').count(), 1, 'the story waits for the layer');
      await common();
      // The box before the layer behaves as after it: leaving it hides the list, focusing it again reopens it, Escape closes the list
      // and keeps the text (no native clear of type=search).
      await page.locator('.hero-title').click(); await list.waitFor({ state: 'hidden' });
      assert.equal(await input.getAttribute('aria-expanded'), 'false', 'leaving the box hides the list');
      await input.focus(); await page.locator('#q-list [data-search-state=loading]').waitFor();
      await input.press('Escape');
      assert.deepEqual([await input.inputValue(), await list.isHidden(), await input.getAttribute('aria-expanded')], ['nv', true, 'false'], 'Escape closes the list and keeps the text');
      await input.press('d');
      // A route left before IS2.ready is never filled: keep its list to look at after the layer arrives.
      await page.evaluate(() => { window.__oldList = document.querySelector('#q-list'); });
      await go('#/qgv', 'main[data-route=qgv]');
      // The ★ toggle is off before IS2.ready.
      await go('#/company/nvda', '[data-result-code="nvda"]');
      assert.equal(await page.locator('[data-favorite]').isDisabled(), true, '★ is off before IS2.ready');
      assert.equal(await page.locator('[data-card]').count(), 5);
      await common();
      // Hand-over on the same render: text typed before IS2.ready becomes options on the same input element when the logic file
      // arrives, the focus stays, and the skeleton's listener is gone (one more keystroke repaints the list once).
      await go('#/', 'main[data-route=search] [data-search-input]');
      await page.evaluate(() => { document.querySelector('[data-search-input]').__mark = 2; });
      await input.fill('nvd'); await page.locator('#q-list [data-search-state=loading]').waitFor();
      release();
      assert.equal(await ready(), 'READY');
      await options().first().waitFor();
      const handed = await page.evaluate(() => { const i = document.querySelector('[data-search-input]'), l = document.querySelector('#q-list');
        return { mark: i.__mark, focus: document.activeElement === i, value: i.value, expanded: i.getAttribute('aria-expanded'), loading: !!l.querySelector('[data-search-state=loading]'),
          first: l.querySelector('[role=option]').dataset.entityKey, old: [window.__oldList.isConnected, window.__oldList.textContent], selection: window.IS2.selection.get() }; });
      assert.deepEqual(handed, { mark: 2, focus: true, value: 'nvd', expanded: 'true', loading: false, first: 'COMPANY:nvda', old: [false, '불러오는 중'], selection: null },
        'same input, focus kept, options for the typed text; the routes left before IS2.ready were not filled');
      await page.evaluate(() => { window.__records = 0; new MutationObserver((m) => { window.__records += m.length; }).observe(document.querySelector('#q-list'), { childList: true }); });
      await input.press('a');
      await page.waitForFunction(() => window.__records > 0);
      assert.equal(await page.evaluate(() => window.__records), 1, 'one input handler: one repaint per keystroke');
      assert.deepEqual(await options().evaluateAll((n) => n.map((o) => o.dataset.entityKey)).then((k) => k.slice(0, 1)), ['COMPANY:nvda']);
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
      // English name (reviewed names table); Korean text gets the hint (DC-23: ticker + English name only); IME safety: the same
      // input element, no key handling while composing.
      await typed('qualcomm');
      assert.deepEqual(await options().evaluateAll((n) => n.map((o) => o.dataset.entityKey)), ['COMPANY:qcom']);
      assert.match(await options().first().textContent(), /^QCOM · QUALCOMM INC\/DE/);
      assert.match(await options().first().textContent(), /NASDAQ:QCOM · Universe504/);
      await typed('퀄컴');
      assert.equal(await page.locator('#q-list [data-search-state=hangul]').textContent(), '티커나 영문 회사명으로 찾아 주세요');
      assert.equal(await options().count(), 0, 'no Korean-name search');
      await typed('hanmi'); assert.equal(await page.locator('#q-list [data-search-state=empty]').count(), 1, 'a TARGET company outside Universe504 is not found');
      await typed('wbd');
      assert.match(await options().first().textContent(), /^WBD · Warner Bros\. Discovery, Inc\./);
      assert.equal(await options().first().locator('[data-listing-ended]').textContent(), ' · 상장 종료 2026-10-06 · 점수 없음', 'a listing-ended code says so');
      assert.deepEqual(await page.locator('[data-search-input]').evaluate((i) => ['inputmode', 'enterkeyhint', 'autocorrect', 'autocapitalize', 'placeholder'].map((a) => i.getAttribute(a))),
        ['search', 'search', 'off', 'characters', '티커 · 영문 회사명'], 'the phone keyboard shows a search key');
      const ime = await page.evaluate(() => { const i = document.querySelector('[data-search-input]'); i.dispatchEvent(new CompositionEvent('compositionstart'));
        i.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, isComposing: true })); const during = i.getAttribute('aria-activedescendant');
        i.dispatchEvent(new CompositionEvent('compositionend')); return { mark: i.__mark, during }; });
      assert.deepEqual(ime, { mark: 1, during: null }, 'the input is never rebuilt; ArrowDown while composing does nothing');
      const composing = await page.evaluate(() => { const i = document.querySelector('[data-search-input]'), l = document.querySelector('#q-list'); i.dispatchEvent(new CompositionEvent('compositionstart'));
        i.value = 'nvd'; i.dispatchEvent(new InputEvent('input', { bubbles: true, isComposing: true, inputType: 'insertCompositionText', data: 'nvd' }));
        const r = { open: !l.hidden, first: (l.querySelector('[role=option]') || {}).dataset?.entityKey || null, mark: i.__mark }; i.dispatchEvent(new CompositionEvent('compositionend')); return r; });
      assert.deepEqual(composing, { open: true, first: 'COMPANY:nvda', mark: 1 }, 'the list follows an open composition (Android keyboards, Korean syllables)');
      // A Universe-only company: its code and membership.
      await typed('NYSE:FIX');
      assert.match(await options().first().textContent(), /NYSE:FIX/); assert.match(await options().first().textContent(), /Universe504/);
      await typed('zzzzqqq'); assert.equal(await page.locator('#q-list [data-search-state=empty]').textContent(), '일치하는 기업이 없습니다 · Universe504 안에서만 찾습니다');
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
      // The single exact match (a ticker in another case), and a query without one (DC-23: it stays, the list shows the options).
      for (const [text, hash] of [['NVDA', '#/company/nvda'], ['nv', '#/']]) {
        await go('#/', 'main[data-route=search] [data-search-input]');
        await typed(text);
        if (text === 'nv') { // hover only highlights: the 검색 click still submits the typed text
          await options().last().hover(); assert.equal(await options().last().getAttribute('aria-selected'), 'true', 'hover highlights');
        }
        await page.locator('[data-search-form] button[type=submit]').click();
        await page.waitForFunction((x) => location.hash === x, hash);
        if (text === 'nv') { await options().first().waitFor(); assert.equal(await page.locator('[data-search-input]').inputValue(), 'nv', 'no match: the text and the options stay'); }
        else await page.locator('[data-result-code="nvda"] ~ [data-result-facts] .facts-line').waitFor();
        assert.equal((await store()).local, 0, text + ': a submit without a chosen option saves nothing');
      }
      await go('#/company/nv', '[data-not-found]');
      assert.equal(await page.locator('[data-not-found]').textContent(), '이 이름의 기업을 찾지 못했습니다', 'an unknown id in the address');
      assert.equal(await page.locator('[data-result-facts] svg.mascot[data-mascot=plain][aria-hidden=true]').count(), 1, 'the state character (DC-25)');
      await go('#/company/NASDAQ%3AWBD', '[data-listing-ended]');
      assert.equal(await page.locator('[data-result-facts] [data-listing-ended]').textContent(), '상장 종료 2026-10-06 · 점수 없음', 'the company page of a listing-ended code');

      // ---------------------------------------------------------------- real selection: keyboard, then pointer
      tag('real selection');
      await go('#/', 'main[data-route=search] [data-search-input]');
      await typed('nvd'); await page.locator('[data-search-input]').press('ArrowDown');
      assert.equal(await options().first().getAttribute('aria-selected'), 'true');
      await page.locator('[data-search-input]').press('Enter');
      await page.locator('[data-result-code="nvda"]').waitFor();
      assert.deepEqual(JSON.parse((await store()).localItems[RECENT_KEY]), ['COMPANY:nvda'], 'ArrowDown + Enter (the default button\'s click) saves the recent search');
      await go('#/', 'main[data-route=search] [data-search-input]');
      await typed('qualcomm'); await options().first().click();
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
      const starName = () => page.getByRole('button', { name: '즐겨찾기', exact: true });
      assert.equal(await starName().count(), 1, 'the ★ toggle is named 즐겨찾기');
      await page.locator('[data-favorite]').click();
      assert.equal(await page.locator('[data-favorite]').getAttribute('aria-pressed'), 'true');
      assert.equal(await starName().getAttribute('aria-pressed'), 'true', 'the same name when pressed; aria-pressed carries the state');
      assert.deepEqual(JSON.parse((await store()).localItems[PERSONAL_KEY]), { version: 1, interests: ['amd'], groups: [] }, 'a real click on ★ writes prefs');
      await go('#/', 'main[data-route=search] [data-favorites=MINE]');
      assert.deepEqual(await page.locator('[data-favorites=MINE] [data-chip]').evaluateAll((n) => n.map((a) => a.textContent)), ['★ AMD · AMD']);
      assert.equal(await page.locator('[data-favorites=DEFAULT]').count(), 0, 'the first favorite replaces the developer default');
      await common();
      // Unstar with a group that holds the id (as the old watchlist screen saves them): the id leaves the group too, so the
      // validator takes it.
      await page.evaluate((k) => localStorage.setItem(k, JSON.stringify({ version: 1, interests: ['amd', 'nvda'], groups: [{ id: 'g1', name: '반도체', members: ['amd', 'nvda'] }] })), PERSONAL_KEY);
      await go('#/company/amd', '[data-favorite][aria-pressed=true]:not([disabled])');
      await page.locator('[data-favorite]').click();
      assert.deepEqual(JSON.parse((await store()).localItems[PERSONAL_KEY]), { version: 1, interests: ['nvda'], groups: [{ id: 'g1', name: '반도체', members: ['nvda'] }] });
      assert.equal(await page.locator('[data-favorite]').getAttribute('aria-pressed'), 'false');
      assert.equal(await page.locator('[data-favorite-why]').textContent(), '', 'saved without a reason line');
      await go('#/', 'main[data-route=search] [data-favorites=MINE]');
      assert.deepEqual(await page.locator('[data-favorites=MINE] [data-chip]').evaluateAll((n) => n.map((a) => a.textContent)), ['★ NVIDIA · NVDA']);
      await go('#/company/nvda', '[data-favorite][aria-pressed=true]:not([disabled])');
      await page.locator('[data-favorite]').click();
      assert.deepEqual(JSON.parse((await store()).localItems[PERSONAL_KEY]), { version: 1, interests: [], groups: [{ id: 'g1', name: '반도체', members: [] }] });
      await go('#/', 'main[data-route=search] [data-favorites=DEFAULT]');
      // 최근 지우기: a real click clears the recent searches.
      await page.locator('[data-recent-clear]').click();
      assert.equal((await store()).localItems[RECENT_KEY], undefined, '최근 지우기 cleared the list');
      assert.equal(await page.locator('[data-recent]').count(), 0);
      assert.equal(await page.locator('[data-recent-cleared]').textContent(), '최근 검색을 지웠습니다');
      assert.equal(await page.evaluate(() => document.activeElement && 'homeChips' in document.activeElement.dataset), true, 'the focus stays in the chip block');
      const small = async (sel) => page.evaluate((x) => [...document.querySelectorAll(x)].filter((e) => e.getClientRects().length).map((e) => [e.textContent, e.getBoundingClientRect().height]).filter(([, h]) => h < 44 - 0.5), sel);
      assert.deepEqual(await small('main .chip-row .chip, main .linkish, main [data-quote-link]'), [], 'home tap targets are 44 px tall');
      // DC-22: unreadable stored favorites hide the favorites, never the public default list (the stored text stays as it was).
      const kept = (await store()).localItems[PERSONAL_KEY], broken = '{"version":1,"interests":"broken"}';
      await page.evaluate(([k, v]) => localStorage.setItem(k, v), [PERSONAL_KEY, broken]);
      await go('#/qgv', 'main[data-route=qgv]'); await go('#/', 'main[data-route=search] [data-favorites=INVALID]');
      assert.ok(await page.locator('[data-favorites=DEFAULT] > [data-chip]').count() > 0, 'the developer default (public TARGET list) still shows');
      assert.equal((await store()).localItems[PERSONAL_KEY], broken, 'nothing rewritten');
      await page.evaluate(([k, v]) => localStorage.setItem(k, v), [PERSONAL_KEY, kept]);

      // ---------------------------------------------------------------- company page values
      tag('company');
      await go('#/company/nvda', '[data-card=qgv] [data-qgv]');
      const facts = await page.locator('[data-result-facts] .facts-line').textContent();
      assert.match(facts, /^NASDAQ:NVDA · Universe504(?! 밖)/, 'the ticker once: in the title; membership names Universe504 only (no TARGET v0, DC-24)');
      assert.equal(await page.locator('.result-name').textContent(), 'NVIDIA · NVDA');
      assert.equal(await page.locator('.result-name').getAttribute('data-result-code'), 'nvda');
      await page.waitForFunction(() => document.querySelectorAll('[data-card] [data-pending]').length === 0);
      const want = await page.evaluate(async () => {
        const Q = window.IS2.qgv, pg = await Q.page(), r = Q.row(pg, 'nvda'), f = (v) => (typeof v === 'number' && Number.isFinite(v) ? new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v) : null);
        return { q: f(r.score.q), g: f(r.score.g), v: f(r.score.v), total: f(r.score.total), rank: r.rank.official, of: r.rank.of, label: Q.rankLabel(pg), source: r.source_label,
          why: { v: r.score.v === null ? Q.reasonText(r.na_reason.v) : null, rank: r.rank.official === null ? Q.reasonText(r.na_reason.rank) : null } };
      });
      const qgv = await page.evaluate(() => { const c = document.querySelector('[data-card=qgv]'), val = (a) => c.querySelector('[data-axis=' + a + '] .qval').textContent;
        const basis = c.querySelector('[data-qgv-basis]'), body = c.querySelector('.card-body').cloneNode(true); body.querySelector('[data-qgv-basis]').remove();
        return { q: val('Q'), g: val('G'), v: val('V'), text: body.textContent, basis: basis.textContent, fills: [...c.querySelectorAll('.qbar-fill')].map((x) => Number(x.getAttribute('width'))) }; });
      // DC-22: the score file's refresh time (its as_of, UTC) and calc_version under the card.
      const stamp = await page.evaluate(async () => { const pg = await window.IS2.qgv.page(), F = new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' });
        return '점수 갱신 ' + F.format(Date.parse(pg.as_of)) + ' UTC · 계산 버전 ' + pg.calc_version; });
      assert.equal(qgv.basis, stamp, 'the QGV card names the score refresh time and the calc_version');
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
      const fixtureNews = SEC.payload(Date.parse(NOW)).events.filter((e) => e.company_id === 'nvda').sort((a, b) => (a.accepted_at < b.accepted_at ? 1 : a.accepted_at > b.accepted_at ? -1 : 0)).slice(0, 5);
      const wantNews = await page.evaluate((evs) => evs.map((e) => '[공시 · SEC] ' + e.form + ' · ' + window.SecDisclosures.classLabel(e.classification, false, e.items) + ' · ' + e.accepted_at.slice(0, 10)), fixtureNews);
      assert.ok(wantNews.length >= 1);
      assert.deepEqual(news, wantNews, 'the fixture\'s newest filings for nvda, newest first, kind · form · class · date');
      assert.match(await page.locator('[data-card=portfolio]').innerText(), /이 기기 저장소가 아직 없습니다/);
      assert.match(await page.locator('[data-card=portfolio]').innerText(), /비중은 포트폴리오 화면에서/);
      const mac = await page.evaluate(async () => { const I = window.IS2, c = await I.engines.macro.current(), st = I.data.state('macro-screen.json'), b = document.querySelector('[data-card=macro] .card-body');
        return { c, asOf: st.as_of, state: st.state, text: b.innerText, na: [...b.querySelectorAll('[data-na]')].map((x) => x.dataset.na) }; });
      assert.ok(!mac.na.includes('MACRO_FAILED'), 'the macro card read the layer');
      if (phone) { assert.ok(mac.c && mac.c.state === null, 'the built file has no public lights'); assert.deepEqual(mac.na, ['NO_LIGHTS']); }
      else {
        assert.deepEqual(mac.c && [mac.c.state, mac.c.lit_count, mac.c.available_count], ['WARNING', 2, 3], 'the synthetic lights file');
        assert.ok(mac.text.includes('경고등 판정: 경고 · 켜진 경고등 2 / 확인 3'), mac.text); assert.deepEqual(mac.na, []);
      }
      if (mac.asOf) assert.ok(mac.text.includes('공개 자료 기준 ' + String(mac.asOf).slice(0, 10)), 'the public file date');
      assert.deepEqual(await small('[data-favorite], [data-card] a.more'), [], 'company page tap targets are 44 px tall');
      assert.deepEqual(await page.locator('[data-card]').evaluateAll((n) => n.map((x) => x.dataset.card)), ['qgv', 'technical', 'macro', 'news', 'portfolio']);
      assert.deepEqual(await page.locator('[data-card]').evaluateAll((n) => n.map((x) => (x.matches('a') ? x.getAttribute('href') : x.querySelector('a.more').getAttribute('href')))),
        ['#/qgv', '#/technical', '#/macro', '#/news', '#/portfolio'], 'each card leads to its menu');
      await common();
      // A company without filings in the fixture.
      await go('#/company/NYSE:FIX', '[data-card=news] [data-na]');
      assert.equal(await page.locator('[data-card=news] [data-na]').textContent(), '공개 파일에 이 기업 소식이 없습니다');
      assert.match(await page.locator('[data-card=portfolio]').innerText(), /TARGET 밖 기업이라/);
      assert.match(await page.locator('[data-result-facts] .facts-line').textContent(), /^NYSE:FIX · Universe504/);
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
      const kinds = [];
      for (const type of ['STORY', 'DIRECT']) {
      // HomeQuotes.pick(previous, Math.random): a stubbed Math.random picks an item of this type from the pool without the shown one.
      const prev = await page.locator('[data-quote]').getAttribute('data-quote-id');
      await go('#/qgv', 'main[data-route=qgv]');
      await page.evaluate(({ type, prev }) => { const pool = window.HomeQuotes.QUOTES.filter((x) => x.id !== prev), i = pool.findIndex((x) => x.type === type); window.__random = Math.random; Math.random = () => (i + 0.5) / pool.length; }, { type, prev });
      await go('#/', '[data-quote][data-quote-id]');
      await page.evaluate(() => { Math.random = window.__random; });
      const q = await page.evaluate(() => { const el = document.querySelector('[data-quote]'), Q = window.HomeQuotes.byId(el.dataset.quoteId), a = el.querySelector('[data-quote-link]');
        return { type: el.dataset.quoteType, want: Q.type, ko: el.querySelector('.quote-ko').textContent, wantKo: Q.ko, en: el.querySelector('.quote-en').textContent, wantEn: Q.headline_en, who: el.querySelector('.quote-who').textContent,
          speaker: Q.speaker.ko, kind: el.querySelector('.quote-kind').textContent, src: el.querySelector('.quote-src').textContent, source: Q.source, href: a.getAttribute('href'), url: Q.url, rel: a.getAttribute('rel'), target: a.getAttribute('target') }; });
      assert.equal(q.type, q.want); assert.equal(q.ko, q.wantKo); assert.ok(q.en.endsWith(q.wantEn)); assert.ok(q.who.includes(q.speaker)); assert.ok(q.src.includes(q.source));
      assert.deepEqual([q.href, q.rel, q.target], [q.url, 'noopener noreferrer', '_blank']);
      assert.equal(q.type, type);
      assert.equal(q.kind, q.type === 'STORY' ? '일화 요약 · 직접 인용 아님 · 우리말 정리(자체 작성)' : '직접 인용 · 우리말 번역(자체 번역)');
      kinds.push(q.type);
      }
      assert.deepEqual(kinds, ['STORY', 'DIRECT'], 'both labels shown');

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
    // ---------------------------------------------------------------- portfolio card with a device store: held yes / no
    phase = 'holdings';
    {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
      await context.clock.setFixedTime(new Date(NOW));
      const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      await page.goto(s.base + '#/'); await page.evaluate(() => window.IS2.ready);
      // Seeded by the test straight into the device database (DeviceActual's schema): nvda quantity 10, amd recorded with quantity 0,
      // qcom absent. Synthetic rows, no price.
      await page.evaluate(async () => {
        const c = await window.IS2.data.static('actual-catalog.json'), ref = (t) => c.instruments.find((i) => i.ticker === t).security_reference;
        const snap = window.DeviceActual.makeSnapshot(c, [{ security_reference: ref('NVDA'), quantity: '10', average_cost: '100', currency: 'USD' }, { security_reference: ref('AMD'), quantity: '0', average_cost: '0', currency: 'USD' }]);
        await new Promise((resolve, reject) => { const r = indexedDB.open('investment-device-actual-v1', 1); r.onerror = () => reject(r.error);
          r.onupgradeneeded = () => r.result.createObjectStore('snapshots');
          r.onsuccess = () => { const tx = r.result.transaction('snapshots', 'readwrite'); tx.objectStore('snapshots').put(snap, 'actual'); tx.oncomplete = () => { r.result.close(); resolve(); }; tx.onerror = () => reject(tx.error); }; });
      });
      const held = [];
      for (const id of ['nvda', 'amd', 'qcom']) {
        await page.evaluate((h) => { location.hash = h; }, '#/company/' + id); await page.locator('[data-result-code="' + id + '"] ~ [data-result-facts] .facts-line').waitFor();
        const p = page.locator('[data-card=portfolio] [data-held]'); await p.waitFor();
        held.push([id, await p.getAttribute('data-held'), await p.textContent()]);
      }
      assert.deepEqual(held, [['nvda', 'true', '이 기기 보유 기록 있음'], ['amd', 'false', '이 기기 보유 기록 없음'], ['qcom', 'false', '이 기기 보유 기록 없음']],
        'the TARGET instrument by ticker, canonical security_reference and quantity > 0');
      assert.deepEqual(seen.errors, [], 'holdings: no console error but the intended 404s');
      await context.close();
    }

    // ---------------------------------------------------------------- the logic file fails: LOADER_FAILED for every menu
    phase = 'loader failed';
    {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const page = await context.newPage(), errors = [];
      page.on('pageerror', (e) => errors.push(String(e)));
      await page.route('**/screen-search-live.js', (route) => route.fulfill({ status: 404, contentType: 'text/plain', body: 'gone' }));
      await page.goto(s.base + '#/company/nvda', { waitUntil: 'domcontentloaded' });
      await page.locator('[data-result-facts] [data-na=INDEX_FAILED]').waitFor();
      const failed = await page.evaluate(() => ({ state: window.IS2.loadState(), facts: document.querySelector('[data-result-facts]').textContent, code: document.querySelector('[data-result-code]').dataset.resultCode,
        star: document.querySelector('[data-favorite]').disabled, alert: (document.querySelector('[role=alert]') || {}).textContent || '', prefs: window.IS2.store.prefs().reason }));
      assert.equal(failed.state, 'FAILED'); assert.equal(failed.facts, '기업 목록을 불러오지 못했습니다', 'the fixed sentence, as before the split');
      assert.equal(failed.code, 'nvda'); assert.equal(failed.star, true, '★ stays off'); assert.match(failed.alert, /일부 파일을 불러오지 못했습니다/, 'the shell notice');
      assert.equal(failed.prefs, 'LOADER_FAILED', 'a missing screen logic file fails the layer for every menu (P1_DATA_LAYER.md 1.1)');
      assert.deepEqual(errors, [], 'no uncaught error or unhandled rejection');
      await context.close();
    }
    console.log('web app home: search, recent, favorites, company cards, story and boundaries ok at 1440 and 390; held yes / no; LOADER_FAILED');
  } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
