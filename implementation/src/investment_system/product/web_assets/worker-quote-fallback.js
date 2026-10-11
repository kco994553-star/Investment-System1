/* Sheet quote missing (#N/A, empty) → latest COMPLETE Worker daily close, held only in this window's RAM.
   Source label WORKER_CLOSE ("Worker 종가 · 일봉 · 정보용"); as_of is the session date. Never stored, exported or logged.
   Requests are made only from a user's click (sheet quote import, or the fill button). */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.WorkerQuoteFallback = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SOURCE = 'WORKER_CLOSE', TIME_STATUS = 'SESSION_CLOSE', RANGE = '1mo', ORIGIN_KEY = 'investment.web.v1.private-history-origin';
  const DECIMAL = /^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/;
  const STOP = new Set(['AUTH_REQUIRED', 'AUTH_FORBIDDEN', 'ORIGIN_FORBIDDEN', 'CONFIG_UNAVAILABLE', 'RATE_LIMITED', 'RATE_LIMIT_UNAVAILABLE', 'CANCELED']);
  const CODE = /^[A-Z][A-Z0-9_]{2,40}$/;
  const LABEL = {ko: 'Worker 종가 · 일봉 · 정보용', en: 'Worker close · Daily bar · For information only'};
  const stores = new WeakMap();
  function fail(code) { throw new Error(code); }
  function plain(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
  function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (plain(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
    return JSON.stringify(value);
  }
  function label(locale) { return locale === 'en-US' ? LABEL.en : LABEL.ko; }
  // Catalog ticker or Holdings symbol → Worker symbol (KRX .KS, TSE .T, US as is).
  function workerSymbol(symbol) {
    if (typeof symbol !== 'string') return null;
    if (/^\d{6}$/.test(symbol)) return symbol + '.KS';
    if (/^\d{4}$/.test(symbol)) return symbol + '.T';
    return /^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol) ? symbol : null;
  }
  function sessionDate(timestamp, timeZone) {
    const parts = new Intl.DateTimeFormat('en-CA', {timeZone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date(timestamp * 1000));
    const get = type => parts.find(part => part.type === type).value; return get('year') + '-' + get('month') + '-' + get('day');
  }
  function priceText(value) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0 || value >= 1e15) return null;
    const text = String(Number(value.toFixed(6))); return DECIMAL.test(text) && Number(text) > 0 ? text : null;
  }
  // Pure: the latest bar with session_status COMPLETE and a close. Throws a reason code otherwise.
  function latestComplete(payload, expected) {
    if (!plain(payload) || payload.schema !== 'private-history/1' || payload.symbol !== expected.symbol || payload.interval !== '1d'
      || payload.basis !== 'RAW_CLOSE' || typeof payload.currency !== 'string' || !/^[A-Z]{3}$/.test(payload.currency)
      || (expected.currency && payload.currency !== expected.currency) || typeof payload.timezone !== 'string' || !/^[A-Za-z0-9_+\-/]{1,64}$/.test(payload.timezone)
      || typeof payload.read_at !== 'string' || !Number.isFinite(Date.parse(payload.read_at)) || !Array.isArray(payload.bars) || payload.bars.length > 1500) fail('WORKER_FORMAT_CHANGED');
    let previous = 0, found = null;
    for (const bar of payload.bars) {
      if (!plain(bar) || !Number.isSafeInteger(bar.timestamp) || bar.timestamp <= previous || !['COMPLETE', 'IN_PROGRESS', 'UNKNOWN'].includes(bar.session_status)
        || (bar.close !== null && (typeof bar.close !== 'number' || !Number.isFinite(bar.close) || bar.close <= 0))) fail('WORKER_FORMAT_CHANGED');
      previous = bar.timestamp;
      if (bar.session_status === 'COMPLETE' && bar.close !== null) found = bar;
    }
    if (!found) fail('NO_COMPLETE_SESSION');
    let day;
    try { day = typeof found.session_date === 'string' ? found.session_date : sessionDate(found.timestamp, payload.timezone); } catch (_) { fail('WORKER_FORMAT_CHANGED'); }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || new Date(day + 'T00:00:00Z').toISOString().slice(0, 10) !== day) fail('WORKER_FORMAT_CHANGED');
    const price = priceText(found.close); if (price === null) fail('WORKER_FORMAT_CHANGED');
    return {price, currency: payload.currency, session_date: day};
  }
  function storedOrigin(view) { try { return view.localStorage.getItem(ORIGIN_KEY) || ''; } catch (_) { return null; } }
  function readiness(view, config, session) {
    if (!config || config.privateHistoryEnabled !== true) return 'OFF';
    const origin = storedOrigin(view);
    if (origin === null) return 'REQUEST_INVALID';
    let approved = '';
    try { approved = view.GoogleSheetQuotes.historyOrigin(config.privateHistoryWorkerOrigin); } catch (_) { return 'ORIGIN_UNAPPROVED'; }
    if (!origin || origin.replace(/\/$/, '') !== approved) return 'ORIGIN_UNAPPROVED';
    if (!session || !session.state().connected) return 'AUTH_REQUIRED';
    return 'READY';
  }
  function sessionOf(view, config) {
    try { return config && config.googleSheetsClientId && view.GoogleSheetQuotes ? view.GoogleSheetQuotes.sessionFor(view, config.googleSheetsClientId) : null; } catch (_) { return null; }
  }
  function notify(view) { try { if (view.document && view.Event) view.document.dispatchEvent(new view.Event('device-actual-changed')); } catch (_) { /* RAM only */ } }
  function storeFor(view, session) {
    let state = stores.get(view);
    if (state && session && state.session !== session) { reset(view); state = null; }
    if (!state) {
      state = {session: session || null, revision: session ? session.revision() : null, entries: new Map(), unsubscribe: null};
      if (session) state.unsubscribe = session.subscribe(() => {
        const current = stores.get(view);
        if (current === state && (!session.state().connected || session.revision() !== state.revision)) { reset(view); notify(view); }
      });
      stores.set(view, state);
      if (view.addEventListener && !state.pagehide) { state.pagehide = () => reset(view); view.addEventListener('pagehide', state.pagehide, {once: true}); }
    }
    return state;
  }
  function reset(view) {
    const state = stores.get(view); if (!state) return;
    stores.delete(view); state.entries.clear(); if (state.unsubscribe) state.unsubscribe();
  }
  // One Worker read for one symbol. Resolves to {state:'AVAILABLE', price, currency, session_date} or {state:'NOT_AVAILABLE', reason}.
  async function readClose(view, {symbol, currency = null, config, session, signal} = {}) {
    const ready = readiness(view, config, session);
    if (ready !== 'READY') return {state: 'NOT_AVAILABLE', reason: ready};
    const target = workerSymbol(symbol);
    if (!target) return {state: 'NOT_AVAILABLE', reason: 'REQUEST_INVALID'};
    try {
      const origin = view.GoogleSheetQuotes.historyOrigin(config.privateHistoryWorkerOrigin);
      const payload = await session.fetchHistory(origin, target, RANGE, {approvedOrigin: origin, signal: signal || undefined});
      return {state: 'AVAILABLE', ...latestComplete(payload, {symbol: target, currency})};
    } catch (error) {
      const code = error && typeof error.message === 'string' && CODE.test(error.message) ? error.message : 'HISTORY_UNAVAILABLE';
      return {state: 'NOT_AVAILABLE', reason: code};
    }
  }
  function instrumentFor(catalog, ticker) { return catalog && Array.isArray(catalog.instruments) ? catalog.instruments.find(item => item.ticker === ticker) || null : null; }
  // Fill RAM closes for catalog tickers (sequential; a stop code ends the remaining reads with the same code).
  async function fill(view, {catalog, tickers, config, session = sessionOf(view, config), now = Date.now(), signal = null} = {}) {
    const list = [...new Set((tickers || []).filter(ticker => instrumentFor(catalog, ticker)))];
    if (!list.length) return {filled: 0, failed: 0};
    const state = storeFor(view, session), failedAt = new Date(now).toISOString(), revision = session ? session.revision() : null;
    let stop = null, filled = 0, failed = 0;
    for (const ticker of list) {
      const instrument = instrumentFor(catalog, ticker);
      const result = stop ? {state: 'NOT_AVAILABLE', reason: stop}
        : await readClose(view, {symbol: ticker, currency: instrument.currency, config, session, signal});
      if (stores.get(view) !== state || (session && session.revision() !== revision)) return {filled, failed, canceled: true};
      if (result.state === 'AVAILABLE') {
        const asOf = result.session_date + 'T00:00:00Z', available = new Date(Math.max(Date.parse(asOf), Date.now())).toISOString();
        state.entries.set(ticker, {state: 'AVAILABLE', ticker, session_date: result.session_date, sheet_failed_at: failedAt,
          quote: {security_reference: JSON.parse(JSON.stringify(instrument.security_reference)), price: result.price, currency: instrument.currency,
            as_of: asOf, available_at: available, source: SOURCE, time_status: TIME_STATUS}});
        filled++;
      } else {
        state.entries.set(ticker, {state: 'NOT_AVAILABLE', ticker, reason: result.reason, sheet_failed_at: failedAt});
        if (STOP.has(result.reason)) stop = result.reason;
        failed++;
      }
    }
    notify(view); return {filled, failed};
  }
  function tickerFromCode(code) { const match = /^(?:NASDAQ|NYSE|TYO|KRX):([A-Z0-9.]+)$/.exec(code || ''); return match ? match[1] : null; }
  // Called after a sheet quote import (the user's click): failed TARGET codes get a Worker close, working ones drop theirs.
  async function afterImport(view, {catalog, result, config = view.InvestmentAppConfig, session = sessionOf(view, config), now = Date.now()} = {}) {
    if (!result || !Array.isArray(result.failures) || !Array.isArray(result.successes)) return null;
    const existing = stores.get(view);
    if (existing) for (const row of result.successes) { const ticker = tickerFromCode(row.code); if (ticker) existing.entries.delete(ticker); }
    const tickers = result.failures.map(row => tickerFromCode(row.code)).filter(ticker => instrumentFor(catalog, ticker));
    if (!tickers.length) { if (existing) notify(view); return {filled: 0, failed: 0, tickers: []}; }
    const summary = await fill(view, {catalog, tickers, config, session, now});
    return {...summary, tickers};
  }
  function status(view, ticker) {
    const state = stores.get(view), entry = state ? state.entries.get(ticker) : null;
    if (!entry) return null;
    return entry.state === 'AVAILABLE' ? {state: 'AVAILABLE', source: SOURCE, session_date: entry.session_date} : {state: 'NOT_AVAILABLE', reason: entry.reason};
  }
  // RAM overlay rule: a Worker close replaces a sheet quote only where the sheet had none, or where the stored
  // GOOGLEFINANCE value predates the import in which the sheet returned #N/A. MANUAL/API values always win.
  function quotesFor(view, market) {
    const state = stores.get(view); if (!state) return [];
    const stored = new Map((market && Array.isArray(market.quotes) ? market.quotes : []).map(quote => [canonical(quote.security_reference), quote]));
    const result = [];
    for (const entry of state.entries.values()) {
      if (entry.state !== 'AVAILABLE') continue;
      const previous = stored.get(canonical(entry.quote.security_reference));
      if (!previous || (previous.source === 'GOOGLEFINANCE' && Date.parse(previous.available_at) <= Date.parse(entry.sheet_failed_at))) result.push(JSON.parse(JSON.stringify(entry.quote)));
    }
    return result;
  }
  function overlay(view, catalog, market, now) {
    const quotes = quotesFor(view, market);
    if (!quotes.length || !view.DeviceMarket) return market || null;
    return view.DeviceMarket.withRamQuotes(market || null, catalog, quotes, now);
  }
  function has(view) { const state = stores.get(view); return !!state && state.entries.size > 0; }
  // Explicit fill button for the actual-holdings screen.
  function mountControl(host, {catalog, locale = 'ko-KR', config, tickers}) {
    const doc = host.ownerDocument, view = doc.defaultView, english = locale === 'en-US';
    const make = (tag, text, attrs = {}) => { const node = doc.createElement(tag); if (text) node.textContent = text; for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v); return node; };
    const root = make('div', '', {class: 'worker-quote-fallback', 'data-worker-fallback': ''});
    const button = make('button', english ? 'Fill missing sheet quotes with Worker closes' : 'Worker 종가로 빈 시세 채우기', {type: 'button', 'data-worker-fallback-action': 'fill'});
    const status = make('p', '', {role: 'status', 'data-worker-fallback-status': ''});
    root.append(make('p', english ? 'Where the Google Sheet quote is missing or #N/A (e.g. Tokyo Electron), the latest COMPLETE daily close from your Worker is used, labelled ' + label(locale) + '. RAM only; nothing is stored.'
      : 'Google 시트 시세가 비었거나 #N/A인 종목(예: Tokyo Electron)은 Worker의 최근 완결 일봉 종가를 "' + label(locale) + '"로 표시해 씁니다. RAM 전용이며 저장하지 않습니다.', {class: 'small'}), button, status);
    host.replaceChildren(root);
    button.addEventListener('click', async () => {
      if (button.disabled) return; button.disabled = true; status.textContent = english ? 'Working…' : '처리 중…';
      try {
        const session = sessionOf(view, config), ready = readiness(view, config, session);
        if (ready !== 'READY') { status.textContent = 'NOT_AVAILABLE · ' + ready; status.dataset.code = ready; return; }
        const list = typeof tickers === 'function' ? await tickers() : tickers || [];
        if (!list.length) { status.textContent = english ? 'No missing or failed sheet quotes.' : '비었거나 실패한 시트 시세가 없습니다.'; status.dataset.code = 'NOTHING_TO_FILL'; return; }
        const summary = await fill(view, {catalog, tickers: list, config, session});
        status.dataset.code = summary.failed ? 'PARTIAL' : 'FILLED';
        status.textContent = (english ? 'Worker closes ' : 'Worker 종가 ') + summary.filled + ' / NOT_AVAILABLE ' + summary.failed;
      } catch (_) { status.textContent = 'NOT_AVAILABLE · HISTORY_UNAVAILABLE'; status.dataset.code = 'HISTORY_UNAVAILABLE'; }
      finally { button.disabled = false; }
    });
  }
  return Object.freeze({SOURCE, TIME_STATUS, RANGE, label, workerSymbol, latestComplete, readiness, readClose, fill, afterImport, status, quotesFor, overlay, has, reset, mountControl});
});
