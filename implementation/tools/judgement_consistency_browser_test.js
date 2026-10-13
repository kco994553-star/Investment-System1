'use strict';
const {displayOnlyOff}=require('./display_only_off.js');
// D-19 judgement consistency on S03 (portfolio) and S17 (daily reports) at 390 and 1440 (JUDGEMENT_CONSISTENCY_AUDIT.md).
// A. End to end (390): the app's own runner path on synthetic, intercepted inputs (same harness as the runner test) computes
//    the shadow ledger on 투자 일일보고서; S03 then shows exactly the same main + auxiliary chips per company as S17 and as
//    the exported template text.
// B. Synthetic coverage (390, 1440): a synthetic engine-shaped day with all 7 levels, auxiliary level/signal combinations
//    and every displayed code family (judgement, auxiliary, order, EXEC_*, ledger, runner, signals, V history) rendered
//    through the app's own modules on S17 (both reports) and S03. Checks: one source (chip text/tone = VirtualTrading),
//    exactly one main chip, auxiliaries in priority order never repeating the main, same text on S03 / S17 / template,
//    every code labelled (an unknown code only through the tested verbatim fallback), buy/sell verbs only in virtual
//    ledger wording, the fixed disclaimer on S17 (both reports) and the S03 card, chips wrap and are never cut, no
//    horizontal page scroll. Every request is intercepted; anything unexpected is aborted and counted.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const TOKEN = ['memory', 'only', 'synthetic', 'judgement', 'credential'].join('-');
const SCOPE = 'email openid https://www.googleapis.com/auth/drive.file';
const V = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'd'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const UNKNOWN = 'UPSTREAM_TEAPOT'; // a Worker-style code with no label: must be shown verbatim through the fallback

function weekdays(from, to) { const out = []; for (let d = new Date(from + 'T00:00:00Z'); d <= new Date(to + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1)) if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); return out; }
const SESSIONS = weekdays('2026-10-19', '2026-10-30');
function record(date) {
  const companies = {};
  IDS.forEach((id, i) => { companies[id] = { state: 'LIVE', Q: { score: 50 + i, coverage: i % 5 === 0 ? 'PARTIAL' : 'READY', missing_factor_count: 0 }, G: { score: 60 - i / 2, coverage: 'READY', missing_factor_count: 0 } }; });
  return { date, version: V, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: { portfolio_id: 'TARGET', version: 'v0', root_sha256: H, total_units: 10000, weights_units: { ...UNITS } },
    qg_as_of: date + 'T22:10:00+00:00', qg_screen_state: 'LIVE', companies, source_sha256: { 'sec-qg-factors.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' };
}
function forwardLedger(days) {
  return { schema_version: 1, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status: 'ACTIVE', as_of: days.at(-1) + 'T22:31:00+00:00', strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true,
    target: { portfolio_id: 'TARGET', version: 'v0' }, versions: { [V]: days.map(record), [VV]: [] }, version_status: { [V]: { state: 'ACTIVE', v_included: false, reason_codes: [] }, [VV]: { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] } } };
}
function history(symbol, range) {
  const meta = symbol.endsWith('.KS') ? ['KRW', 'Asia/Seoul'] : symbol.endsWith('.T') ? ['JPY', 'Asia/Tokyo'] : symbol.endsWith('=X') ? ['KRW', 'Europe/London'] : ['USD', 'America/New_York'];
  const base = symbol === 'KRW=X' ? 1400 : symbol === 'JPYKRW=X' ? 9.3 : 100 + symbol.length;
  const bars = weekdays('2026-09-01', '2026-10-30').map((d, i) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null,
    close: Math.round(base * (1 + (i % 7) / 100) * 10000) / 10000, adjusted_close: null, volume: null, session_status: 'COMPLETE' }));
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: meta[0], exchange: 'SYNTHETIC', timezone: meta[1], interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: '2026-10-30T22:00:00Z', bars };
}

async function open(browser, { now, width }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR', permissions: ['clipboard-read', 'clipboard-write'] });await displayOnlyOff(context);
  const traffic = { unexpected: [], errors: 0 };
  await context.addInitScript(({ token, scope }) => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: 'ko-KR', source_language: 'all' }));
    localStorage.setItem('investment.web.v1.unified-sheet-source', 'synthetic_existing_sheet_fixture');
    localStorage.setItem('investment.web.v1.private-history-origin', 'https://private-investment-history.kco994553.workers.dev');
    window.google = { accounts: { oauth2: { initTokenClient(config) { return { requestAccessToken() { config.callback({ access_token: token, expires_in: 3600, scope, token_type: 'Bearer' }); } }; }, revoke(_t, done) { done({}); } } } };
  }, { token: TOKEN, scope: SCOPE });
  await routeEmptyPublicScreens(context);
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === new URL(BASE).origin) {
      if (url.pathname.endsWith('/app-config.js')) {
        await route.fulfill({ contentType: 'application/javascript', body: 'window.InvestmentAppConfig=Object.freeze(' + JSON.stringify({ googleSheetsClientId: 'synthetic-public.apps.googleusercontent.com', privateHistoryEnabled: true, privateHistoryWorkerOrigin: WORKER, virtualTradingRequestSpacingMs: 0 }) + ');' });
        return;
      }
      if (url.pathname.endsWith('/forward-validation-ledger.json')) { await route.fulfill({ contentType: 'application/json', body: JSON.stringify(forwardLedger(SESSIONS)) }); return; }
      return route.fallback();
    }
    if (url.origin === WORKER) {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization', 'access-control-allow-methods': 'GET' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      await route.fulfill({ status: 200, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body: JSON.stringify(history(url.searchParams.get('symbol'), url.searchParams.get('range'))) });
      return;
    }
    if (url.origin === 'https://sheets.googleapis.com') {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      if (request.method() === 'GET' && url.searchParams.get('fields') === 'sheets(properties(title))') { await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ sheets: [{ properties: { title: 'Quotes' } }, { properties: { title: 'VirtualMeta' } }] }) }); return; }
      // The user's own target (decision 2026-10-11: the shadow ledger never falls back to TARGET v0): one synthetic
      // USER_TARGET row in VirtualMeta (the TARGET v0 units as %, read only).
      if (request.method() === 'GET' && decodeURIComponent(url.pathname).includes("/values/'VirtualMeta'!A1:")) {
        const meta = [['recorded_at', 'ledger_id', 'kind', 'event', 'start_date', 'end_date', 'config_version', 'engine_version', 'last_recorded_session', 'inputs_sha256', 'payload'],
          ['2026-10-12T00:00:00Z', '', 'TARGET', 'USER_TARGET', '', '', '', '', '', '', JSON.stringify({ target_weights: Object.fromEntries(IDS.map((id) => [id, UNITS[id] / 100])) })]];
        await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ range: 'VirtualMeta', majorDimension: 'ROWS', values: meta }) }); return;
      }
      if (request.method() === 'GET' && decodeURIComponent(url.pathname).includes("/values/'VirtualMeta'!A")) { await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ range: 'VirtualMeta', majorDimension: 'ROWS' }) }); return; }
    }
    traffic.unexpected.push(url.origin);
    await route.abort();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', (e) => { traffic.errors++; console.log('pageerror ' + String(e.message).slice(0, 200)); });
  await page.clock.install({ time: new Date(now) });
  await page.goto(BASE + '#home');
  await page.locator('[data-report-link="mock"]').waitFor();
  return { context, page, traffic };
}
async function login(page) {
  await page.evaluate((token) => {
    const real = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId); real.setEnabled(true); real.login();
    // Same client as the runner test after the Worker benchmark/FX allowlist change: same token, origin and request shape.
    const session = { ...real, async fetchHistory(origin, symbol, range, options = {}) {
      const r = await fetch(origin + '/history?symbol=' + encodeURIComponent(symbol) + '&range=' + encodeURIComponent(range), { method: 'GET', headers: { Authorization: 'Bearer ' + token }, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error', signal: options.signal });
      const body = await r.json(); if (!r.ok) throw new Error(body && body.error ? body.error.code : 'YAHOO_UNAVAILABLE'); return body; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
  }, TOKEN);
}
const go = (page, hash) => page.evaluate((h) => { location.hash = h; }, hash);

/* ---------- shared page checks ---------- */
// Per company: [chip texts] from a container whose rows carry the company id.
async function chipsBy(page, rowSelector, idAttr) {
  return page.evaluate(({ rowSelector, idAttr }) => {
    const out = {};
    for (const row of document.querySelectorAll(rowSelector)) out[row.getAttribute(idAttr)] = [...row.querySelectorAll('[data-chip]')].map((c) => c.textContent);
    return out;
  }, { rowSelector, idAttr });
}
// Template ③ rows → {name: judgement text}.
function templateJudgements(text) {
  const part = text.slice(text.indexOf('## ③'), text.indexOf('## ④')), out = {};
  for (const line of part.split('\n')) { const cells = line.split(' | '); if (line.startsWith('| ') && cells.length >= 7 && !line.startsWith('| 기업') && !line.startsWith('|---')) out[cells[0].slice(2)] = cells[5]; }
  return out;
}
// Visible text rule: 매수/매도 only as "가상 매수/매도" (or the negation "매수·매도 지시 아님").
function verbOffenders(text) {
  const bad = [];
  for (const m of text.matchAll(/매수|매도/g)) {
    const before = text.slice(Math.max(0, m.index - 3), m.index), around = text.slice(Math.max(0, m.index - 3), m.index + 12);
    if (before.endsWith('가상 ') || before.endsWith('가상')) continue;
    if (/^매수·매도 지시 아님/.test(text.slice(m.index)) || /매수·매도 지시 아님/.test(text.slice(Math.max(0, m.index - 3), m.index + 10))) continue;
    bad.push(around);
  }
  return bad;
}
async function layout(page, label) {
  const r = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth, chips = [...document.querySelectorAll('#content [data-chip]')];
    const cut = chips.filter((c) => c.scrollWidth > c.clientWidth + 1 || getComputedStyle(c).whiteSpace !== 'nowrap' || getComputedStyle(c).textOverflow === 'ellipsis').map((c) => c.textContent);
    // A chip outside the viewport must sit inside a horizontally scrollable table wrapper (scrolls, never clipped).
    const off = chips.filter((c) => { const b = c.getBoundingClientRect(); return (b.right > vw + 1 || b.left < -1) && !c.closest('.table-scroll'); }).map((c) => c.textContent);
    const nowrap = [...document.querySelectorAll('#content .vt-judgement')].filter((n) => getComputedStyle(n).flexWrap !== 'wrap').length;
    return { scroll: document.documentElement.scrollWidth <= innerWidth + 1, cut, off, nowrap, chips: chips.length };
  });
  assert.ok(r.scroll, 'horizontal page scroll ' + label);
  assert.deepEqual(r.cut, [], 'truncated chips ' + label);
  assert.deepEqual(r.off, [], 'chips outside the viewport ' + label);
  assert.equal(r.nowrap, 0, 'chip rows wrap ' + label);
  return r.chips;
}

/* ---------- B: synthetic day covering every level, auxiliary combination and code family ---------- */
function syntheticJudgements(VT) {
  const J = (main, aux_levels, reason_codes, aux = []) => ({ main, symbol: VT.SYMBOLS[main], aux_levels, aux, reason_codes, held: true, target_weight: 5, actual_weight: 5 });
  return {
    c01_block: J('BLOCK', [], ['DATA_PRICE_MISSING', 'DATA_SNAPSHOT_MISSING', 'USER_EXCLUDE']),
    c02_block_fx: J('BLOCK', [], ['DATA_FX_MISSING', 'COVERAGE_BLOCKED']),
    c03_risk_full: J('RISK_RECHECK', ['ADDITIONAL_REVIEW'], ['QG_DECLINE', 'COVERAGE_WORSENED', 'RECHECK_ABNORMAL_DROP', 'USER_CONFIRMED_STRUCTURAL'], ['INCREASE_CANDIDATE', 'OVERWEIGHT', 'EARNINGS_WINDOW']),
    c04_risk_hold: J('RISK_RECHECK', [], ['USER_HOLD', 'RECHECK_BASIS_NOT_AVAILABLE'], ['OVERWEIGHT']),
    c05_reduce: J('REDUCE_REVIEW', ['ADDITIONAL_REVIEW'], ['OVERWEIGHT_GAP', 'V_DETERIORATED', 'USER_CONFIRMED_TEMPORARY'], ['TYPE_CHANGED']),
    c06_increase: J('INCREASE_REVIEW', ['ADDITIONAL_REVIEW'], ['UNDERWEIGHT_GAP', 'V_IMPROVED'], ['COVERAGE_PARTIAL', 'SECTOR_SP500_SUBSTITUTE']),
    c07_additional: J('ADDITIONAL_REVIEW', [], ['BAND_INSIDE'], ['EARNINGS_WINDOW', 'TYPE_CHANGED', 'V_COMPOSITION_CHANGED']),
    c08_holding: J('HOLDING_CONTEXT', [], ['BAND_INSIDE']),
    c09_observe: J('OBSERVE', [], []),
    c10_unknown: J('INCREASE_REVIEW', [], ['UNDERWEIGHT_GAP', UNKNOWN]),
  };
}
async function renderSynthetic(page, { kind, tab }) {
  return page.evaluate(({ kind, tab, unknown }) => {
    const VT = VirtualTrading, R = DailyReport, js = window.__syntheticJudgements;
    const day = { date: '2026-10-30', deposit: 1, cash: 1, positions_value: 1, total_value: 2, stale_valuation: [], judgements: js, orders: [],
      executed: [{ date: '2026-10-30', company: 'c06_increase', side: 'BUY', amount: 1, quantity: 1, price: 1, fx: 1, fee: 0, realized_pnl: null, reason_codes: ['UNDERWEIGHT_GAP', 'V_IMPROVED', 'LIMIT_EXHAUSTED'], user_flag: null },
        { date: '2026-10-30', company: 'c05_reduce', side: 'SELL', amount: 1, quantity: 1, price: 1, fx: 1, fee: 0, realized_pnl: 0, reason_codes: ['OVERWEIGHT_GAP', 'V_DETERIORATED'], user_flag: null }],
      cancelled: VT.CODES.execution.map((code, i) => ({ company: 'c0' + (i + 1) + '_x', side: i % 2 ? 'SELL' : 'BUY', amount: 1, reason_codes: ['UNDERWEIGHT_GAP'], decided_on: '2026-10-29', cancel_reason: code })) };
    const ledger = { state: 'OK', reason_codes: [], days: [day], trades: day.executed, summary: { total_value: 2, simple_return: 0, initial_value: 1, deposits: 1, cash: 1, realized_pnl: 0, unrealized_pnl: 0, twr: 0 } };
    const basis = { c03_risk_full: { requested: 'SMH', benchmark: 'SP500', fallback: true, state: 'NOT_AVAILABLE', reason: 'HISTORY_INSUFFICIENT', aligned: 100, needed: 273, v_slope: 'BASIS_NOT_AVAILABLE' },
      c04_risk_hold: { requested: 'XLK', benchmark: 'XLK', fallback: false, state: 'NOT_AVAILABLE', reason: 'PRICE_NOT_ALIGNED', aligned: 0, needed: 273, v_slope: 'BASIS_NOT_AVAILABLE' },
      c05_reduce: { requested: 'XLI', benchmark: 'XLI', fallback: false, state: 'NOT_AVAILABLE', reason: 'DISTRIBUTION_DEGENERATE', aligned: 273, needed: 273, v_slope: 'BASIS_NOT_AVAILABLE' },
      c06_increase: { requested: 'XLV', benchmark: 'SP500', fallback: true, state: 'NOT_AVAILABLE', reason: 'SECTOR_BASIS_NOT_AVAILABLE', aligned: 0, needed: 273, v_slope: 'BASIS_NOT_AVAILABLE' },
      c07_additional: { requested: 'SP500', benchmark: 'SP500', fallback: false, state: 'NORMAL', reason: null, aligned: 273, needed: 273, v_slope: 'V_HISTORY_SHORT' } };
    const runnerCodes = [...VirtualTradingRunner.CODES, unknown];
    const runner = { state: 'NOT_AVAILABLE', reason_codes: runnerCodes, sources: runnerCodes.map((code, i) => ({ symbol: 'SYM' + i, state: 'NOT_AVAILABLE', code })), progress: '' };
    const signals = { basis, v_progress: { state: 'COLLECTING', first: '2026-10-20', last: '2026-10-30', recorded: 9, elapsed: 8, needed: 20 }, capture: { state: 'NOT_RECORDED', reason: 'V_STORE_INVALID', date: '2026-10-30', added: [] } };
    const names = Object.fromEntries(Object.keys(js).map((c) => [c, c.toUpperCase()]));
    const model = R.buildModel({ kind, tab, reportDate: '2026-10-31', baseDates: { NYSE: '2026-10-30' }, ledger, names, config: VT.defaultConfig(), runner, signals });
    document.querySelector('#daily-report').innerHTML = R.screenHtml(model, { hidden: true, locale: 'ko-KR' });
    // Ledger-level stop codes: the not-started summary of the same screen module.
    const stopped = R.buildModel({ kind, tab, reportDate: '2026-10-31', ledger: { state: 'NOT_AVAILABLE', reason_codes: [...VT.CODES.ledger, ...VirtualLedgerSheets.CODES.slice(0, 3)], days: [], trades: [], summary: null }, config: VT.defaultConfig() });
    const holder = document.createElement('div'); holder.setAttribute('data-synthetic-stopped', ''); holder.innerHTML = R.screenHtml(stopped, { hidden: true }).match(/<p class="badge NOT_AVAILABLE" data-report-not-started>[^]*?<\/p>/)[0];
    document.querySelector('#daily-report').append(holder);
    return { template: R.renderTemplate(model, { hidden: true, guide: false }), names, stoppedCodes: stopped.ledger_reasons, runnerCodes };
  }, { kind, tab, unknown: UNKNOWN });
}
async function checkS17(page, VTinfo, { kind, label }) {
  const out = await renderSynthetic(page, { kind, tab: kind === 'REAL' ? 'REAL' : 'SET_A' });
  const js = VTinfo.judgements;
  // 1. one source: every chip's text and tone come from VirtualTrading
  const chips = await page.evaluate(() => [...document.querySelectorAll('#daily-report [data-chip]')].map((c) => ({ kind: c.getAttribute('data-chip'), level: c.getAttribute('data-level'), tone: c.getAttribute('data-tone'), text: c.textContent, bg: getComputedStyle(c).backgroundColor })));
  for (const c of chips) {
    assert.equal(c.tone, VTinfo.tones[c.level], 'tone ' + c.level);
    if (c.kind === 'main') assert.equal(c.text, VTinfo.labels[c.level]);
    if (c.kind === 'aux') assert.equal(c.text, '+' + VTinfo.labels[c.level]);
  }
  const toneBg = {};
  for (const c of chips) { if (toneBg[c.tone]) assert.equal(c.bg, toneBg[c.tone], 'one colour per tone'); toneBg[c.tone] = c.bg; }
  assert.equal(new Set(Object.values(toneBg)).size, Object.keys(toneBg).length, 'tones have distinct colours');
  // 2. one main per company, auxiliaries by priority without the main, same text as the template and as VirtualTrading
  const s17 = await chipsBy(page, '#daily-report [data-judgement-cell]', 'data-judgement-cell');
  assert.deepEqual(Object.keys(s17).sort(), Object.keys(js).sort());
  const tpl = templateJudgements(out.template);
  for (const [cid, list] of Object.entries(s17)) {
    assert.equal(list.join(' '), VTinfo.text[cid], 'S17 ' + cid);
    assert.equal(tpl[out.names[cid]], VTinfo.text[cid], 'template ' + cid);
  }
  const mains = await page.evaluate(() => [...document.querySelectorAll('#daily-report [data-judgement]')].map((n) => n.querySelectorAll('[data-chip="main"]').length));
  assert.ok(mains.length === Object.keys(js).length && mains.every((n) => n === 1), 'exactly one main chip per company');
  const levels = await page.evaluate(() => [...document.querySelectorAll('#daily-report [data-judgement]')].map((n) => [...n.querySelectorAll('[data-chip]')].map((c) => c.getAttribute('data-level'))));
  for (const l of levels) {
    assert.equal(new Set(l).size, l.length, 'no level twice');
    const rest = l.slice(1).map((x) => VTinfo.levels.indexOf(x));
    assert.deepEqual(rest, [...rest].sort((a, b) => a - b), 'auxiliary chips by priority');
  }
  for (const level of VTinfo.levels) assert.ok(levels.some((l) => l[0] === level), 'main level shown: ' + level);
  for (const sig of ['OVERWEIGHT', 'INCREASE_CANDIDATE']) assert.equal(await page.locator('#daily-report [data-signal="' + sig + '"]').count() > 0, true, sig);
  // 3. every code labelled; the unknown code only through the verbatim fallback
  const reasons = await page.evaluate(() => [...document.querySelectorAll('#daily-report [data-reason-code]')].map((n) => ({ code: n.getAttribute('data-reason-code'), text: n.textContent, unlabeled: n.hasAttribute('data-unlabeled') })));
  const shownCodes = new Set(reasons.map((r) => r.code));
  for (const r of reasons) {
    if (r.code === UNKNOWN) { assert.ok(r.unlabeled && r.text === UNKNOWN, 'verbatim fallback'); continue; }
    assert.ok(!r.unlabeled && r.text === VTinfo.codeText[r.code], 'labelled ' + r.code + ' → ' + r.text);
  }
  for (const c of [...VTinfo.families.judgement, ...VTinfo.families.aux, ...VTinfo.families.order, ...VTinfo.families.execution]) assert.ok(shownCodes.has(c), 'shown: ' + c);
  const runnerText = await page.locator('#daily-report [data-runner-summary]').textContent();
  for (const c of out.runnerCodes) assert.ok(runnerText.includes(VTinfo.codeTextAll[c]), 'runner code ' + c);
  for (const c of out.runnerCodes.filter((x) => x !== UNKNOWN)) assert.ok((await page.locator('#daily-report [data-source-code="' + c + '"]').textContent()).includes(VTinfo.codeTextAll[c]), 'source code ' + c);
  const stoppedText = await page.locator('[data-synthetic-stopped]').textContent();
  for (const c of out.stoppedCodes) assert.ok(stoppedText.includes(VTinfo.codeTextAll[c]), 'ledger code ' + c);
  for (const [cid, code] of [['c03_risk_full', 'HISTORY_INSUFFICIENT'], ['c04_risk_hold', 'PRICE_NOT_ALIGNED'], ['c05_reduce', 'DISTRIBUTION_DEGENERATE'], ['c06_increase', 'SECTOR_BASIS_NOT_AVAILABLE']]) {
    const t = await page.locator('[data-basis="' + cid + '"]').textContent();
    assert.ok(t.includes(code) && t.includes(VTinfo.codeLabel[code]) && t.includes(VTinfo.codeLabel.BASIS_NOT_AVAILABLE), 'basis ' + cid + ' ' + t);
  }
  assert.ok((await page.locator('[data-basis="c07_additional"]').textContent()).includes(VTinfo.codeLabel.V_HISTORY_SHORT));
  assert.ok((await page.locator('[data-v-capture]').textContent()).includes(VTinfo.codeTextAll.V_STORE_INVALID));
  const legend = await page.locator('[data-cancel-legend]').textContent();
  for (const c of VTinfo.families.execution) assert.ok(legend.includes(c + ': ' + VTinfo.codeLabel[c]), 'legend ' + c);
  const dictionary = out.template.slice(out.template.indexOf('## 사유 코드 사전'));
  for (const c of shownCodes) assert.ok(dictionary.includes('- ' + c + ': ' + (c === UNKNOWN ? '라벨 없음 · 코드 그대로' : VTinfo.codeLabel[c])), 'dictionary ' + c);
  // 4. verbs only in virtual-ledger wording; fixed disclaimer in the header, ③ and ⑩ (and on the ledger sheet card)
  const visible = await page.locator('#content').innerText();
  assert.deepEqual(verbOffenders(visible), [], 'buy/sell verbs outside virtual wording (' + label + ')');
  const data = out.template.slice(out.template.indexOf('[일일보고서 템플릿]'));
  assert.deepEqual(verbOffenders(data), [], 'template verbs');
  for (const where of ['[data-report-badges]', '[data-report-section="3"] h2', '[data-report-section="10"] h2']) assert.equal((await page.locator(where + ' [data-vt-disclaimer]').textContent()).trim(), VTinfo.disclaimer, where);
  await page.locator('[data-ledger-sheets] [data-vt-disclaimer]').waitFor();
  assert.equal((await page.locator('[data-ledger-sheets] [data-vt-disclaimer]').textContent()).trim(), VTinfo.disclaimer);
  assert.ok(data.includes('판단: ' + VTinfo.disclaimer) && data.includes('(' + VTinfo.disclaimer + ')'));
  // 5. layout
  assert.equal(await layout(page, label), Object.values(VTinfo.text).reduce((a, t) => a + t.split(' +').length, 0), 'chip count');
  return s17;
}
async function vocabulary(page) {
  return page.evaluate(() => {
    const VT = VirtualTrading, js = window.__syntheticJudgements, all = [...Object.keys(VT.CODE_LABELS), ...VirtualTradingRunner.CODES, 'UPSTREAM_TEAPOT'];
    return { levels: [...VT.LEVELS], tones: { ...VT.TONES }, disclaimer: VT.DISCLAIMER.ko, families: VT.CODES,
      labels: Object.fromEntries(VT.LEVELS.map((l) => [l, VT.label(l, 'ko-KR')])),
      text: Object.fromEntries(Object.entries(js).map(([c, j]) => [c, VT.judgementText(j, 'ko-KR')])),
      codeText: Object.fromEntries(Object.keys(VT.CODE_LABELS).map((c) => [c, VT.codeText(c, 'ko-KR')])),
      codeTextAll: Object.fromEntries(all.map((c) => [c, VT.codeText(c, 'ko-KR')])),
      codeLabel: Object.fromEntries(Object.keys(VT.CODE_LABELS).map((c) => [c, VT.codeLabel(c, 'ko-KR')])), judgements: js };
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + String(e.message).slice(0, 400)); } };
  try {
    await check('A. app runner: S03 shows the same shadow-ledger chips as S17 and the exported template (390)', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', width: 390 });
      try {
        await go(page, 'portfolio');
        await page.locator('[data-portfolio-card="virtual"] [data-virtual-state="NOT_AVAILABLE"]').waitFor();
        assert.equal((await page.locator('[data-portfolio-card="virtual"] [data-vt-disclaimer]').textContent()).trim(), '가상 · 실제 추천 아님 · 주문 기능 없음');
        await login(page);
        await page.evaluate(() => {
          const snapshot = { effective_at: '2026-10-20T01:00:00Z', themes: [{ holdings: [
            { security_reference: { scheme: 'ISIN', value: 'US67066G1040' }, quantity: '4000', average_cost: '100', currency: 'USD' },
            { security_reference: { code: '042700', exchange: 'KRX', scheme: 'EXCHANGE_CODE' }, quantity: '30', average_cost: '70000', currency: 'KRW' }] }] };
          // The runner reads holdings through effectiveHoldings (stored ACTUAL or the RAM Holdings tab, #204); stub both.
          window.DeviceActual = { ...DeviceActual, readHoldings: async () => snapshot, effectiveHoldings: async () => ({ snapshot, source: 'ACTUAL', as_of: snapshot.effective_at }) };
        });
        await go(page, 'report/real');
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        const s17 = await chipsBy(page, '#daily-report [data-judgement-cell]', 'data-judgement-cell');
        assert.equal(Object.keys(s17).length, 19);
        const s17Text = Object.fromEntries(Object.entries(s17).map(([c, l]) => [c, l.join(' ')]));
        const names = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('#daily-report [data-judgement-cell]')].map((td) => [td.getAttribute('data-judgement-cell'), td.parentElement.firstElementChild.textContent])));
        const s17Order = await page.evaluate(() => [...document.querySelectorAll('#daily-report [data-judgement-cell]')].map((td) => td.getAttribute('data-judgement-cell')));
        await page.locator('[data-include-guide]').uncheck();
        await page.locator('[data-export-template]').click();
        await page.waitForFunction(() => /복사|표시/.test(document.querySelector('[data-report-status]')?.textContent || ''));
        const text = await page.evaluate(async () => { try { return await navigator.clipboard.readText(); } catch (_) { return document.querySelector('[data-export-fallback]')?.value || ''; } });
        const tpl = templateJudgements(text);
        for (const [cid, t] of Object.entries(s17Text)) assert.equal(tpl[names[cid]], t, 'template ' + cid);
        assert.ok(new Set(Object.values(s17Text).map((t) => t.split(' ')[0])).size >= 2, 'more than one main level in the synthetic run');
        await go(page, 'portfolio');
        await page.locator('[data-portfolio-card="virtual"] [data-virtual-list]').waitFor();
        const s03 = await chipsBy(page, '[data-virtual-company]', 'data-virtual-company');
        assert.deepEqual(Object.fromEntries(Object.entries(s03).map(([c, l]) => [c, l.join(' ')])), s17Text, 'S03 = S17 per company');
        assert.deepEqual(await page.evaluate(() => [...document.querySelectorAll('[data-virtual-company]')].map((n) => n.getAttribute('data-virtual-company'))), s17Order, 'same order');
        const s03Reasons = await page.evaluate(() => [...document.querySelectorAll('[data-portfolio-card="virtual"] [data-reason-code]')].filter((n) => n.hasAttribute('data-unlabeled')).length);
        assert.equal(s03Reasons, 0, 'every S03 reason labelled');
        assert.equal((await page.locator('[data-portfolio-card="virtual"] [data-vt-disclaimer]').textContent()).trim(), '가상 · 실제 추천 아님 · 주문 기능 없음');
        assert.deepEqual(verbOffenders(await page.locator('#content').innerText()), []);
        await layout(page, 'S03 runner 390');
        assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    for (const width of [390, 1440]) {
      await check('B. synthetic 7 levels, auxiliary combinations and every code family on S17 (both reports) and S03 (' + width + ')', async () => {
        const { context, page, traffic } = await open(browser, { now: '2026-10-15T03:00:00Z', width });
        try {
          await page.evaluate((judgements) => { window.__syntheticJudgements = judgements; }, syntheticJudgements(await page.evaluate(() => ({ SYMBOLS: { ...VirtualTrading.SYMBOLS } }))));
          const VTinfo = await vocabulary(page);
          for (const [hash, kind] of [['report/mock', 'MOCK'], ['report/real', 'REAL']]) {
            await go(page, hash);
            await page.locator('[data-report-inputs][data-runner-state="NOT_STARTED"]').waitFor();
            await page.locator('[data-ledger-sheets]').waitFor();
            await checkS17(page, VTinfo, { kind, label: kind + ' ' + width });
          }
          // S03 through the app's own route with the same judgements as the last shadow-ledger result of this page.
          await page.evaluate((js) => { virtualShadow = { date: '2026-10-30', judgements: js, names: Object.fromEntries(Object.keys(js).map((c) => [c, c.toUpperCase()])) }; }, VTinfo.judgements);
          await go(page, 'portfolio');
          await page.locator('[data-portfolio-card="virtual"] [data-virtual-list]').waitFor();
          const s03 = await chipsBy(page, '[data-virtual-company]', 'data-virtual-company');
          for (const [cid, list] of Object.entries(s03)) assert.equal(list.join(' '), VTinfo.text[cid], 'S03 ' + cid);
          assert.deepEqual(Object.keys(s03).sort(), Object.keys(VTinfo.judgements).sort());
          const order = await page.evaluate(() => [...document.querySelectorAll('[data-virtual-company]')].map((n) => n.querySelector('[data-chip="main"]').getAttribute('data-level')));
          const ranks = order.map((l) => VTinfo.levels.indexOf(l));
          assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b), 'S03 rows by main priority');
          const reasons = await page.evaluate(() => [...document.querySelectorAll('[data-portfolio-card="virtual"] [data-reason-code]')].map((n) => ({ code: n.getAttribute('data-reason-code'), text: n.textContent, unlabeled: n.hasAttribute('data-unlabeled') })));
          for (const r of reasons) assert.ok(r.code === UNKNOWN ? r.unlabeled && r.text === UNKNOWN : !r.unlabeled && r.text === VTinfo.codeText[r.code], 'S03 reason ' + r.code);
          const tones = await page.evaluate(() => [...document.querySelectorAll('[data-portfolio-card="virtual"] [data-chip]')].map((c) => [c.getAttribute('data-level'), c.getAttribute('data-tone')]));
          for (const [level, tone] of tones) assert.equal(tone, VTinfo.tones[level]);
          assert.equal((await page.locator('[data-portfolio-card="virtual"] h2 [data-vt-disclaimer]').textContent()).trim(), VTinfo.disclaimer);
          assert.deepEqual(verbOffenders(await page.locator('#content').innerText()), [], 'S03 verbs');
          assert.equal(await layout(page, 'S03 ' + width), Object.values(VTinfo.text).reduce((a, t) => a + t.split(' +').length, 0), 'S03 chip count');
          // English chips come from the same table.
          const en = await page.evaluate((js) => { const h = document.createElement('div'); h.innerHTML = PortfolioScreen.virtualCard('en-US', { date: '2026-10-30', judgements: js, names: {} }); return { chips: [...h.querySelectorAll('[data-chip="main"]')].map((c) => c.textContent), disclaimer: h.querySelector('[data-vt-disclaimer]').textContent, levels: VirtualTrading.LEVELS.map((l) => VirtualTrading.label(l, 'en-US')) }; }, VTinfo.judgements);
          assert.ok(en.chips.every((t) => en.levels.includes(t)) && en.disclaimer === 'Virtual · not a recommendation · no order function');
          assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0);
        } finally { await context.close(); }
      });
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  process.exitCode = fail ? 1 : 0;
})();
