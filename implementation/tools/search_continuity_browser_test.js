'use strict';
// G3/G8: tab-only list return state; home news follows only a successfully applied public generation.
// Price-free synthetic public fixtures; all traffic stays GET/same-origin. No private settings or providers.
const { chromium } = require('playwright'), assert = require('node:assert/strict');
const { routeEmptyPublicScreens } = require('./empty_public_screens.js');
const { displayOnlyOff } = require('./display_only_off.js');
const secFx = require('./sec_disclosures_fixture.js'), newsFx = require('./news_signals_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const NOW = Date.parse('2026-10-21T12:00:00Z'), sec = secFx.payload(NOW);
const NEWS = [newsFx.payload(NOW, sec), newsFx.payload(NOW + 3600000, sec, { without: ['nvda'] })];
let assertions = 0;
function eq(a, b, why) { assert.deepEqual(a, b, why); assertions++; }
function ok(a, why) { assert.ok(a, why); assertions++; }
async function setup(browser, width) {
  const context = await browser.newContext({ viewport: { width, height: 800 }, serviceWorkers: 'block' });
  await context.clock.setFixedTime(new Date(NOW));
  await displayOnlyOff(context); await routeEmptyPublicScreens(context);
  const state = { day: 0, fail: false, gate: null }, traffic = { unsafe: 0, outside: 0 }, errors = [];
  await context.route('**/sec-disclosures.json*', r => r.fulfill({ json: sec }));
  await context.route('**/news-signals.json*', async r => {
    if (state.gate) await state.gate;
    return state.fail ? r.fulfill({ status: 503, body: 'synthetic failure' }) : r.fulfill({ json: NEWS[state.day] });
  });
  await context.addInitScript(width => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: width === 390 ? 'ko-KR' : 'en-US', source_language: 'all' }));
    if (!localStorage.getItem('investment.web.v1.personal')) localStorage.setItem('investment.web.v1.personal', JSON.stringify({
      version: 1, interests: ['amd', 'nvda', 'msft', 'asml', 'avgo', 'hanmi', 'klac', 'lrcx', 'qcom'],
      groups: [{ id: 'synthetic-group', name: 'Synthetic group', members: ['amd', 'nvda', 'asml', 'avgo', 'hanmi', 'klac'] }]
    }));
  }, width);
  const page = await context.newPage(); page.setDefaultTimeout(12000);
  page.on('pageerror', e => errors.push(String(e)));
  await page.route('**/*', r => {
    if (r.request().method() !== 'GET') { traffic.unsafe++; return r.abort(); }
    if (new URL(r.request().url()).origin !== ORIGIN) { traffic.outside++; return r.abort(); }
    return r.fallback();
  });
  async function finish() { eq(errors, [], 'no page errors'); eq(traffic, { unsafe: 0, outside: 0 }, 'GET/same-origin only'); await context.close(); }
  return { context, page, state, finish };
}
async function ready(page, route) {
  await page.goto(BASE + '#' + route);
  await page.waitForFunction(() => document.getElementById('data-refresh')?.dataset.refreshState !== 'LOADING' && typeof window.investmentSearch === 'function');
  await page.evaluate(() => companyNamesPromise);
}
const rows = (page, route) => page.locator(route === 'companies' ? '#company-list > li' : '#watchlist-company-list > li');
const fields = (page, route) => page.evaluate(route => route === 'companies'
  ? ['search', 'only-interest', 'group-filter', 'company-sort'].map(id => { const n = document.getElementById(id); return n.type === 'checkbox' ? n.checked : n.value; })
  : ['watch-group', 'watch-sort'].map(id => document.getElementById(id).value), route);
async function directory(page, route) {
  await ready(page, route);
  if (route === 'companies') {
    await page.fill('#search', 'a'); await page.check('#only-interest');
    await page.selectOption('#group-filter', 'synthetic-group'); await page.selectOption('#company-sort', 'name');
  } else {
    await page.selectOption('#watch-group', 'synthetic-group'); await page.selectOption('#watch-sort', 'favorites');
  }
  const beforeFields = await fields(page, route), beforeRows = await rows(page, route).allTextContents();
  const link = (route === 'companies' ? '#company-list' : '#watchlist-company-list') + ' a[href="#company/amd"]';
  for (const back of ['origin', 'history']) {
    // Keep a focused field/caret on the first return and the actual activated link on browser Back.
    await page.evaluate(([route, link, back]) => {
      const n = document.querySelector(back === 'history' ? link : route === 'companies' ? '#search' : '#watch-sort');
      n.focus({ preventScroll: true }); if (n.id === 'search') n.setSelectionRange(1, 1);
      scrollTo(0, 250);
    }, [route, link, back]);
    await page.waitForTimeout(100);
    const before = await page.evaluate(() => ({ y: scrollY, id: document.activeElement.id, href: document.activeElement.getAttribute('href'), caret: document.activeElement.selectionStart }));
    ok(before.y > 0, route + ' scrolled before detail');
    await page.evaluate(s => document.querySelector(s).click(), link);
    await page.locator('[data-origin-link="' + route + '"]').waitFor();
    if (back === 'origin') await page.locator('[data-origin-link="' + route + '"]').click(); else await page.goBack();
    await rows(page, route).first().waitFor(); await page.waitForTimeout(250);
    eq(await fields(page, route), beforeFields, route + ' filters/query/sort restored via ' + back);
    eq(await rows(page, route).allTextContents(), beforeRows, route + ' filtered ordering restored');
    const after = await page.evaluate(() => ({ y: scrollY, id: document.activeElement.id, href: document.activeElement.getAttribute('href'), caret: document.activeElement.selectionStart }));
    ok(Math.abs(after.y - before.y) <= 2, route + ' scroll restored: ' + before.y + ' -> ' + after.y);
    eq({ ...after, y: 0 }, { ...before, y: 0 }, route + ' focus/caret restored');
  }
  const other = route === 'companies' ? 'watchlist' : 'companies';
  await page.evaluate(r => { location.hash = r; }, other); await rows(page, other).first().waitFor();
  // This programmatic hash change has no pointer/keyboard event to cancel DataRefresh's 50 ms settle loop. Give it the exit
  // tick before navigating again; a real navigation click cancels it immediately.
  await page.waitForTimeout(100);
  eq(await fields(page, other), other === 'companies' ? ['', false, '', 'ticker'] : ['', 'added'], 'each list has independent controls');
  await page.evaluate(r => { location.hash = r; }, route); await rows(page, route).first().waitFor();
  eq(await fields(page, route), beforeFields, 'returning to the list keeps its own controls');
  eq(await page.evaluate(() => scrollY), 0, 'unrelated navigation keeps the normal top-of-page behavior');
  await page.reload(); await rows(page, route).first().waitFor();
  eq(await fields(page, route), route === 'companies' ? ['', false, '', 'ticker'] : ['', 'added'], 'reload starts a new RAM view');
}
async function pagination(page) {
  await ready(page, 'companies');
  // The production identity catalog is deliberately fixed at 19. Extend only this tab's identity-only directory to exercise
  // the existing 30/60 row boundary; no catalog validator or market inputs are changed, and the detail remains real AMD.
  await page.evaluate(() => { identityCompanies = identityCompanies.concat(Array.from({ length: 55 }, (_, i) => ({
    company_id: 'synthetic_' + i, ticker: 'ZZ' + String(i).padStart(2, '0'), name: 'Synthetic identity ' + i, identity_only: true
  }))); paintCompanies(); });
  eq(await rows(page, 'companies').count(), 30, 'first page');
  await page.locator('#more-companies').click(); eq(await rows(page, 'companies').count(), 60, 'expanded page');
  await page.evaluate(() => document.querySelector('#company-list a[href="#company/amd"]').click());
  await page.locator('[data-origin-link="companies"]').click(); await rows(page, 'companies').first().waitFor();
  eq(await rows(page, 'companies').count(), 60, 'expanded count survives detail');
  await page.fill('#search', 'ZZ'); eq(await rows(page, 'companies').count(), 30, 'changing a query resets pagination');
}
async function membership(page, route) {
  await ready(page, route);
  await page.selectOption(route === 'companies' ? '#group-filter' : '#watch-group', 'synthetic-group');
  await page.evaluate(() => { for (const d of document.querySelectorAll('#content details')) d.open = true; });
  await page.locator((route === 'companies' ? '#company-list' : '#watchlist-company-list') + ' a[href="#company/amd"]').click();
  await page.locator('[data-origin-link="' + route + '"]').waitFor();
  await page.evaluate(() => document.querySelector('[data-group="synthetic-group"][data-member="amd"]').click());
  await page.locator('[data-origin-link="' + route + '"]').click(); await rows(page, route).first().waitFor();
  eq(await page.locator('[data-group="synthetic-group"][data-member="amd"]').isChecked(), false, 'group setting changed in detail stays current');
  eq(await rows(page, route).locator('a[href="#company/amd"]').count(), 0, 'filtered rows use the changed group');
}
const feedKeys = page => page.locator('#home-personal [data-timeline] > li').evaluateAll(ns => ns.map(n => n.dataset.news || n.dataset.disclosure));
async function home(page, state) {
  await ready(page, 'home'); await page.locator('[data-home-personal-feed]:not([aria-busy])').waitFor();
  await page.fill('#global-search', 'NVDA'); await page.locator('[data-search-filter="company"]').click();
  await page.locator('#global-search').press('ArrowDown');
  await page.locator('#home-result[data-result-company="nvda"]').waitFor();
  await page.evaluate(() => {
    const n = document.getElementById('global-search'); n.focus(); n.setSelectionRange(1, 3);
    window.__continuity = { input: n, home: document.querySelector('[data-home]'), result: document.getElementById('home-result'),
      selected: document.querySelector('#global-results [aria-selected="true"]')?.dataset.entityId };
  });
  const oldKeys = await feedKeys(page); ok(oldKeys.length > 0, 'initial personal news present');
  const searchState = () => page.evaluate(() => {
    const s = window.__continuity, n = document.getElementById('global-search');
    return { sameInput: n === s.input, sameHome: document.querySelector('[data-home]') === s.home, sameResult: document.getElementById('home-result') === s.result,
      query: n.value, caret: [n.selectionStart, n.selectionEnd], focused: document.activeElement === n,
      filter: document.querySelector('[data-search-filter][aria-pressed="true"]')?.dataset.searchFilter,
      selected: document.querySelector('#global-results [aria-selected="true"]')?.dataset.entityId, result: s.result.dataset.resultCompany };
  });
  const beforeSearch = await searchState();
  for (const fail of [true, false]) {
    state.day = 1; state.fail = fail; let release; state.gate = new Promise(resolve => { release = resolve; });
    await page.evaluate(() => { window.__continuity.feed = document.querySelector('[data-home-personal-feed]'); });
    await page.evaluate(() => document.querySelector('[data-refresh-button]').click());
    await page.waitForFunction(() => document.getElementById('data-refresh').dataset.refreshState === 'LOADING');
    eq(await feedKeys(page), oldKeys, 'old personal news stays while refresh is pending');
    ok(await page.evaluate(() => document.querySelector('[data-home-personal-feed]') === window.__continuity.feed), 'pending refresh keeps the feed DOM');
    release(); state.gate = null;
    await page.waitForFunction(() => document.getElementById('data-refresh').dataset.refreshState !== 'LOADING');
    await page.locator('[data-home-personal-feed]:not([aria-busy])').waitFor({ state: 'attached' });
    const status = await page.locator('#data-refresh').getAttribute('data-refresh-state');
    if (fail) { eq(status, 'FAILED', 'failed atomic generation'); eq(await feedKeys(page), oldKeys, 'failed refresh keeps old news');
      ok(await page.evaluate(() => document.querySelector('[data-home-personal-feed]') === window.__continuity.feed), 'failed refresh keeps the feed DOM'); }
    else { eq(status, 'APPLIED', 'successful generation applied'); ok(JSON.stringify(await feedKeys(page)) !== JSON.stringify(oldKeys), 'successful refresh replaces personal news'); }
    eq(await searchState(), beforeSearch, 'active input/result/selection survive ' + (fail ? 'failure' : 'success'));
  }
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  try {
    for (const width of [390, 1280]) for (const scenario of ['companies', 'watchlist', 'pagination', 'home', 'companies-membership', 'watchlist-membership']) {
      if (process.env.SEARCH_CONTINUITY_ONLY && !process.env.SEARCH_CONTINUITY_ONLY.split(',').includes(scenario)) continue;
      const t = await setup(browser, width);
      try {
        if (scenario.endsWith('-membership')) await membership(t.page, scenario.split('-')[0]);
        else if (scenario === 'home') await home(t.page, t.state);
        else if (scenario === 'pagination') await pagination(t.page);
        else await directory(t.page, scenario);
        await t.finish(); pass++; console.log('PASS search continuity ' + scenario + ' ' + width);
      } catch (e) { fail++; console.log('FAIL search continuity ' + scenario + ' ' + width + ': ' + e.message.split('\n')[0]); await t.context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail + ' assertions=' + assertions); if (fail) process.exitCode = 1;
})();
