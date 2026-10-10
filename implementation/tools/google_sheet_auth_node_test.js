/* Synthetic credentials stay in memory; failures never print request payloads. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const filename = require('node:path').join(__dirname, '../src/investment_system/product/web_assets/google-sheet-quotes.js');
const api = fs.existsSync(filename) ? require(filename) : {};
const READONLY_SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly';
const EMAIL_SCOPE = 'email', EMAIL_ALIAS = 'https://www.googleapis.com/auth/userinfo.email';
const SCOPE = READONLY_SCOPE + ' ' + EMAIL_SCOPE;
const STYLE = 'https://accounts.google.com/gsi/style', STYLE_ID = 'googleidentityservice_button_styles';
const ID = ['synthetic', 'spreadsheet', 'fixture'].join('_');
const WORKER_ORIGIN = 'https://private-fixture.owner-fixture.workers.dev';
const HISTORY_PAYLOAD = { schema: 'private-history/1', bars: [] };
function runtime() {
  let now = 1000000, callbacks, pendingResolve, styleFailure = false, delayedStyles = false, resolveStyle;
  const nodes = new Map();
  const calls = { styles: 0, scripts: 0, popup: 0, revoke: 0, fetch: 0, config: null, request: null, order: [] };
  const token = ['memory', 'only', 'synthetic', 'credential'].join('-');
  const view = { setTimeout: () => 1, clearTimeout() {}, AbortController, document: {
    getElementById: id => nodes.get(id) || null,
    createElement: tag => ({ tagName: tag.toUpperCase(), dataset: {}, remove() { if (nodes.get(this.id) === this) nodes.delete(this.id); } }),
    head: { append(node) {
      if (node.id) nodes.set(node.id, node);
      if (node.tagName === 'LINK') {
        calls.styles++; calls.order.push('css-request');
        assert.ok(node.rel === 'stylesheet' && node.href === STYLE && node.id === STYLE_ID, 'only the official external stylesheet can replace the SDK style marker');
        const complete = () => { if (styleFailure) node.onerror(); else { node.sheet = {}; calls.order.push('css-loaded'); node.onload(); } };
        if (delayedStyles) resolveStyle = complete; else queueMicrotask(complete);
      } else {
        calls.scripts++; calls.order.push('sdk-request'); view.google = { accounts: { oauth2: oauth } }; queueMicrotask(() => node.onload());
      }
    } } },
    fetch: async (url, options) => { calls.fetch++; calls.request = { url, options }; return { ok: true, status: 200, json: async () => ({ values: [['code', 'price', 'tradetime']] }) }; } };
  const oauth = { initTokenClient(config) { calls.config = config; callbacks = config; return { requestAccessToken(options) { calls.popup++; calls.prompt = options.prompt; } }; }, revoke(value, done) { calls.revoke++; assert.ok(value === token, 'revoke uses only current memory token'); done({}); } };
  const session = () => api.createSession(view, { clientId: 'public-client-id', now: () => now });
  return { view, calls, token, oauth, session, advance: value => { now += value; }, failStyles: value => { styleFailure = value; }, delayStyles: () => { delayedStyles = true; }, resolveStyles: () => resolveStyle(),
    popupError: type => callbacks.error_callback({type,private_message:'never shown'}), respond: (value = {}) => callbacks.callback({ access_token: token, expires_in: 3600, scope: SCOPE, ...value }), delayedFetch() { view.fetch = (url, options) => { calls.fetch++; calls.request = { url, options }; return new Promise(resolve => { pendingResolve = resolve; }); }; }, resolveFetch: () => pendingResolve({ ok: true, status: 200, json: async () => ({ values: [] }) }) };
}
test('auth exports exist without starting a network request', () => {
  for (const name of ['mount', 'extractSpreadsheetId', 'sheetsURL', 'createSession', 'sessionFor', 'historyOrigin']) assert.equal(typeof api[name], 'function', name + ' is available');
});
test('spreadsheet IDs accept a strict Google URL and reject unrelated origins', () => {
  assert.ok(api.extractSpreadsheetId(ID) === ID);
  assert.ok(api.extractSpreadsheetId('https://docs.google.com/spreadsheets/d/' + ID + '/edit#gid=0') === ID);
  for (const account of [0, 2]) assert.ok(api.extractSpreadsheetId('https://docs.google.com/spreadsheets/u/' + account + '/d/' + ID + '/edit?gid=0') === ID);
  for (const bad of ['https://example.org/spreadsheets/d/' + ID, 'https://docs.google.com.evil.invalid/spreadsheets/d/' + ID, 'http://docs.google.com/spreadsheets/d/' + ID, 'https://secret@docs.google.com/spreadsheets/d/' + ID, 'https://docs.google.com/spreadsheets/d/' + ID + '/unknown', ID + '?secret', 'short']) assert.throws(() => api.extractSpreadsheetId(bad), { message: 'INVALID' });
});
test('Sheets endpoint encodes range and fixes render modes', () => {
  const url = new URL(api.sheetsURL(ID, 'Quotes!A1:C22'));
  assert.ok(url.origin === 'https://sheets.googleapis.com');
  assert.ok(decodeURIComponent(url.pathname).endsWith('/values/Quotes!A1:C22'));
  assert.ok(url.searchParams.get('valueRenderOption') === 'UNFORMATTED_VALUE');
  assert.ok(url.searchParams.get('dateTimeRenderOption') === 'SERIAL_NUMBER');
});
test('OFF and preparation make no popup or Sheets request; login requests exactly readonly and email scopes', async () => {
  const r = runtime(), session = r.session();
  assert.ok(!session.state().connected && !session.state().enabled);
  assert.throws(() => session.login(), { message: 'OFF' });
  assert.ok(r.calls.styles === 0 && r.calls.scripts === 0 && r.calls.fetch === 0 && r.calls.popup === 0);
  session.setEnabled(true); await session.prepare();
  assert.ok(r.calls.scripts === 1 && r.calls.popup === 0 && r.calls.fetch === 0);
  session.login(); assert.ok(r.calls.popup === 1 && r.calls.config.include_granted_scopes === false);
  assert.equal(r.calls.prompt, 'consent', 'email identity is requested through explicit renewed consent');
  assert.deepEqual(new Set(r.calls.config.scope.trim().split(/\s+/)), new Set([READONLY_SCOPE, EMAIL_SCOPE]), 'login asks for exactly readonly Sheets and email identity scopes');
  r.respond(); assert.ok(session.state().connected && r.calls.fetch === 0);
  const json = await session.fetchValues(ID, 'Quotes!A1:C22');
  assert.ok(Array.isArray(json.values) && r.calls.fetch === 1);
  assert.ok(r.calls.request.options.headers.Authorization === 'Bearer ' + r.token, 'authorization exists only in the direct request');
  assert.ok(r.calls.request.options.credentials === 'omit' && r.calls.request.options.cache === 'no-store' && r.calls.request.options.referrerPolicy === 'no-referrer');
  assert.ok(!JSON.stringify(session.state()).includes(r.token), 'public state never exposes a token');
});
test('explicit preparation loads the official stylesheet before the SDK and reuses it', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true);
  assert.ok(r.calls.styles === 0 && r.calls.scripts === 0, 'enabling alone loads neither styles nor SDK');
  await session.prepare();
  assert.deepEqual(r.calls.order, ['css-request', 'css-loaded', 'sdk-request'], 'SDK runs only after external CSS has loaded');
  const marker = r.view.document.getElementById(STYLE_ID);
  assert.ok(marker?.tagName === 'LINK' && marker.sheet, 'a loaded external stylesheet supplies the official SDK marker');
  await session.prepare();
  assert.ok(r.calls.styles === 1 && r.calls.scripts === 1 && r.calls.popup === 0 && r.calls.fetch === 0, 'repeat preparation does not add requests or open login');
});
test('failed stylesheet load prevents SDK and popup until a successful explicit retry', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); r.failStyles(true);
  await assert.rejects(session.prepare(), { message: 'AUTH_FAILED' });
  assert.ok(r.calls.styles === 1 && r.calls.scripts === 0 && r.calls.popup === 0 && r.calls.fetch === 0, 'CSS failure cannot reach the SDK or OAuth');
  assert.ok(!session.state().ready && !session.state().connected && !session.state().preparing, 'failed preparation stays disconnected and can retry');
  assert.throws(() => session.login(), { message: 'NOT_READY' });
  r.failStyles(false); await session.prepare();
  assert.ok(r.calls.styles === 2 && r.calls.scripts === 1, 'retry reloads CSS and then loads SDK once');
  session.login(); r.respond(); assert.ok(session.state().connected && r.calls.popup === 1);
});
test('concurrent preparation shares one pending stylesheet and one SDK load', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); r.delayStyles();
  const first = session.prepare(), second = session.prepare();
  // Allow a sequential stylesheet helper to start while retaining its pending load.
  await Promise.resolve();
  assert.ok(r.calls.styles === 1 && r.calls.scripts === 0 && session.state().preparing, 'concurrent clicks cannot load the SDK early or duplicate CSS');
  r.resolveStyles(); await Promise.all([first, second]);
  assert.deepEqual(r.calls.order, ['css-request', 'css-loaded', 'sdk-request']);
  assert.ok(r.calls.popup === 0 && r.calls.fetch === 0);
});
test('disabling while CSS is pending prevents a late SDK request', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); r.delayStyles();
  const preparation = session.prepare(); await Promise.resolve();
  assert.ok(r.calls.styles === 1 && r.calls.scripts === 0, 'only CSS has started');
  session.setEnabled(false); r.resolveStyles();
  await assert.rejects(preparation, { message: 'CANCELED' });
  assert.ok(r.calls.scripts === 0 && r.calls.popup === 0 && !session.state().ready, 'OFF rejects the late preparation without loading the SDK');
});
test('expiry clears token before a request and 401 requires another button login', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare(); session.login(); r.respond();
  assert.ok(session.state().connected, 'a valid grant connects before expiry'); r.advance(3600001);
  await assert.rejects(session.fetchValues(ID, 'Quotes!A1:C22'), { message: 'AUTH_REQUIRED' });
  assert.ok(!session.state().connected && r.calls.fetch === 0);
  session.login(); r.respond(); r.view.fetch = async () => ({ ok: false, status: 401 });
  await assert.rejects(session.fetchValues(ID, 'Quotes!A1:C22'), { message: 'AUTH_REQUIRED' });
  assert.ok(!session.state().connected);
});
test('disconnect clears memory even when revoke throws, and rejects late auth callbacks', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare(); session.login(); r.respond();
  r.oauth.revoke = () => { r.calls.revoke++; throw new Error('synthetic'); };
  await session.disconnect(); assert.ok(!session.state().connected && r.calls.revoke === 1);
  session.login(); await session.disconnect(); r.respond();
  assert.ok(!session.state().connected, 'late token response cannot reconnect');
});
test('disabling invalidates pending auth and a pending read before it can be applied', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare(); session.login(); session.setEnabled(false); r.respond(); assert.ok(!session.state().connected);
  session.setEnabled(true); session.login(); r.respond(); assert.ok(session.state().connected, 'a valid grant connects before a delayed read'); r.delayedFetch();
  const read = session.fetchValues(ID, 'Quotes!A1:C22'); session.setEnabled(false); r.resolveFetch();
  await assert.rejects(read, { message: 'CANCELED' }); assert.ok(!session.state().connected);
});
test('token scope escalation, missing identity scope and malformed responses are rejected', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare();
  for (const value of [{ scope: SCOPE + ' https://www.googleapis.com/auth/drive' }, { scope: READONLY_SCOPE }, { scope: EMAIL_SCOPE }, { scope: '' }, { scope: undefined }, { scope: 42 }, { scope: SCOPE + ' https://www.googleapis.com/auth/spreadsheets' }, { access_token: '' }, { expires_in: 0 }, { token_type: 'Other' }]) { session.login(); r.respond(value); assert.ok(!session.state().connected && session.state().error === 'AUTH_FAILED', 'invalid grants leave the session disconnected with a fixed error'); }
});
test('token scopes are a set that accepts either email spelling in any order', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare();
  for (const scope of [SCOPE, EMAIL_SCOPE + ' ' + READONLY_SCOPE, READONLY_SCOPE + ' ' + EMAIL_ALIAS, EMAIL_ALIAS + ' ' + READONLY_SCOPE, '  ' + EMAIL_SCOPE + '\t' + READONLY_SCOPE + '  ', SCOPE + ' ' + EMAIL_SCOPE, SCOPE + ' ' + EMAIL_ALIAS]) {
    session.login(); r.respond({ scope }); assert.ok(session.state().connected && !session.state().error, 'the exact semantic scope set is accepted independently of ordering or whitespace');
  }
});
async function connectedRuntime() {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare(); session.login(); r.respond();
  assert.ok(session.state().connected, 'valid readonly and email grants connect');
  return { ...r, active: session };
}
function historyRead(session, options = {}) { return session.fetchHistory(WORKER_ORIGIN, 'NVDA', '1y', { approvedOrigin: WORKER_ORIGIN, ...options }); }
function historyResponse(r, response = {}) {
  r.view.fetch = async (url, options) => {
    r.calls.fetch++; r.calls.request = { url, options };
    return { ok: true, status: 200, json: async () => HISTORY_PAYLOAD, ...response };
  };
}
test('sessionFor shares a frozen memory session across consumers without exposing a token', async () => {
  const r = runtime(), shared = api.sessionFor(r.view, 'public-client-id');
  assert.ok(shared === api.sessionFor(r.view, 'public-client-id'), 'the same browser and public client share the session');
  assert.ok(Object.isFrozen(shared), 'consumers cannot replace the session API');
  assert.ok(shared !== api.sessionFor(runtime().view, 'public-client-id'), 'browser memory is isolated');
  shared.setEnabled(true); await shared.prepare(); shared.login(); r.respond();
  assert.ok(shared.state().connected && r.calls.fetch === 0, 'sharing memory never initiates a data read');
  assert.ok(!Object.keys(shared).some(key => /token|credential/i.test(key)), 'the API has no token getter');
  assert.ok(!JSON.stringify(shared.state()).includes(r.token), 'state contains no token');
  const replacement = api.sessionFor(r.view, 'replacement-public-client-id');
  assert.ok(replacement !== shared && !shared.state().connected, 'changing the client clears the old session synchronously');
  assert.ok(replacement === api.sessionFor(r.view, 'replacement-public-client-id') && !replacement.state().connected, 'the replacement begins disconnected and is shared');
});
test('historyOrigin accepts only strict HTTPS workers.dev root URLs', () => {
  assert.equal(api.historyOrigin(WORKER_ORIGIN), WORKER_ORIGIN);
  assert.equal(api.historyOrigin(WORKER_ORIGIN + '/'), WORKER_ORIGIN);
  for (const origin of [undefined, '', ' ' + WORKER_ORIGIN, WORKER_ORIGIN + ' ', WORKER_ORIGIN.toUpperCase(), WORKER_ORIGIN.replace('https:', 'http:'), WORKER_ORIGIN + ':443', WORKER_ORIGIN + ':8443', 'https://workers.dev', 'https://fixture.workers.dev', 'https://fixture.owner.workers.dev.evil.invalid', 'https://fixture.owner.workers.dev.', 'https://fixture.owner.workers.dev@evil.invalid', 'https://secret@fixture.owner.workers.dev', WORKER_ORIGIN + '/history', WORKER_ORIGIN + '/%2e/', WORKER_ORIGIN + '?x=1', WORKER_ORIGIN + '#x']) {
    assert.throws(() => api.historyOrigin(origin), { message: 'REQUEST_INVALID' }, 'invalid origin inputs use one fixed error');
  }
});
test('history requires a saved exact positive origin approval before any bearer request', async () => {
  const r = await connectedRuntime();
  assert.equal(typeof r.active.fetchHistory, 'function', 'the private history transport is available');
  for (const options of [{}, { approvedOrigin: false }, { approvedOrigin: true }, { approvedOrigin: '' }, { approvedOrigin: 'https://other.owner-fixture.workers.dev' }, { approvedOrigin: WORKER_ORIGIN + '/' }]) {
    await assert.rejects(r.active.fetchHistory(WORKER_ORIGIN, 'NVDA', '1y', options), { message: 'REQUEST_INVALID' });
  }
  for (const origin of ['https://evil.invalid', 'http://private-fixture.owner-fixture.workers.dev', WORKER_ORIGIN + '/history', WORKER_ORIGIN + '?x=1', 'https://secret@private-fixture.owner-fixture.workers.dev', WORKER_ORIGIN + ':443']) {
    await assert.rejects(r.active.fetchHistory(origin, 'NVDA', '1y', { approvedOrigin: origin }), { message: 'REQUEST_INVALID' });
  }
  assert.ok(r.calls.fetch === 0 && r.active.state().connected, 'invalid approval or origin cannot send the token or invalidate login');
});
test('history fixes the exact Worker query and omits cookies, cache and redirects', async () => {
  const r = await connectedRuntime(); historyResponse(r);
  assert.ok(await r.active.fetchHistory(WORKER_ORIGIN + '/', 'NVDA', '1y', { approvedOrigin: WORKER_ORIGIN }) === HISTORY_PAYLOAD, 'the transport returns the JSON for downstream history validation');
  const url = new URL(r.calls.request.url), options = r.calls.request.options;
  assert.ok(url.origin === WORKER_ORIGIN && url.pathname === '/history' && !url.username && !url.password && !url.hash, 'bearer credentials target only the saved Worker history endpoint');
  assert.ok(url.searchParams.size === 2 && url.searchParams.get('symbol') === 'NVDA' && url.searchParams.get('range') === '1y', 'the request contains only the two parameters accepted by the Worker');
  assert.ok(options.method === 'GET' && !options.body, 'history reads are GET requests without a body');
  assert.ok(Object.keys(options.headers).length === 1 && options.headers.Authorization === 'Bearer ' + r.token, 'only the private request gets the current memory token');
  assert.ok(options.credentials === 'omit' && options.cache === 'no-store' && options.redirect === 'error' && options.referrerPolicy === 'no-referrer', 'cookies, caching, redirects and referrers are disabled');
  assert.ok(options.signal instanceof AbortSignal && !JSON.stringify(r.active.state()).includes(r.token), 'the request can be canceled without exposing credentials');
});
test('history rejects symbols and ranges outside the narrow chart contract without a request', async () => {
  const r = await connectedRuntime();
  for (const [symbol, range] of [['AAPL', '1y'], ['NVDA?secret', '1y'], [' NVDA', '1y'], ['NVDA', 'max'], ['NVDA', '1y&interval=1m'], ['', '1y'], ['NVDA', '']]) {
    await assert.rejects(r.active.fetchHistory(WORKER_ORIGIN, symbol, range, { approvedOrigin: WORKER_ORIGIN }), { message: 'REQUEST_INVALID' });
  }
  assert.ok(r.calls.fetch === 0, 'invalid chart inputs make no request');
});
test('history is unavailable while OFF, disconnected or expired without refreshing login', async () => {
  const r = runtime(), session = r.session();
  await assert.rejects(historyRead(session), { message: 'AUTH_REQUIRED' });
  session.setEnabled(true); await session.prepare();
  await assert.rejects(historyRead(session), { message: 'AUTH_REQUIRED' });
  session.login(); r.respond(); r.advance(3600001);
  await assert.rejects(historyRead(session), { message: 'AUTH_REQUIRED' });
  assert.ok(!session.state().connected && r.calls.fetch === 0 && r.calls.popup === 1, 'expiry deletes memory credentials without another popup or request');
});
test('history propagates only recognized fixed Worker errors without response details', async () => {
  const r = await connectedRuntime();
  for (const code of ['CONFIG_UNAVAILABLE', 'AUTH_UNAVAILABLE', 'REQUEST_INVALID', 'ORIGIN_FORBIDDEN', 'RATE_LIMITED', 'RATE_LIMIT_UNAVAILABLE', 'YAHOO_BLOCKED', 'YAHOO_UNAVAILABLE', 'YAHOO_TIMEOUT', 'YAHOO_FORMAT_CHANGED', 'YAHOO_TOO_LARGE', 'HISTORY_UNAVAILABLE']) {
    historyResponse(r, { ok: false, status: 503, json: async () => ({ error: { code, message: 'synthetic-private-detail', token: r.token } }) });
    await assert.rejects(historyRead(r.active), { message: code }, 'only the allowlisted code leaves transport');
    assert.ok(r.active.state().connected, 'provider and budget errors preserve login');
  }
  for (const payload of [{ error: { code: 'SYNTHETIC_PRIVATE_UNKNOWN', message: 'synthetic-private-detail' } }, { message: 'synthetic-private-detail' }, null]) {
    historyResponse(r, { ok: false, status: 500, json: async () => payload });
    await assert.rejects(historyRead(r.active), { message: 'YAHOO_UNAVAILABLE' }, 'unrecognized error payloads collapse to a fixed error');
  }
});
test('history unauthorized or forbidden responses clear the shared memory session', async () => {
  const r = await connectedRuntime(); let notices = 0; const unsubscribe = r.active.subscribe(() => { notices++; });
  for (const [status, code] of [[401, 'AUTH_REQUIRED'], [403, 'AUTH_FORBIDDEN']]) {
    if (!r.active.state().connected) { r.active.login(); r.respond(); }
    const before = notices;
    historyResponse(r, { ok: false, status, json: async () => ({ error: { code } }) });
    await assert.rejects(historyRead(r.active), { message: code });
    assert.ok(!r.active.state().connected && notices > before, 'failed owner authorization clears credentials and notifies chart consumers');
    const count = r.calls.fetch; await assert.rejects(historyRead(r.active), { message: 'AUTH_REQUIRED' });
    assert.ok(r.calls.fetch === count, 'authorization failure cannot silently retry');
  }
  unsubscribe();
});
test('history network, malformed JSON and malformed transport values use fixed unavailable errors', async () => {
  const r = await connectedRuntime();
  r.view.fetch = async () => { throw new Error('synthetic-private-detail'); };
  await assert.rejects(historyRead(r.active), { message: 'YAHOO_UNAVAILABLE' });
  historyResponse(r, { json: async () => { throw new Error('synthetic-private-detail'); } });
  await assert.rejects(historyRead(r.active), { message: 'YAHOO_UNAVAILABLE' });
  for (const payload of [null, [], 'synthetic-private-detail']) {
    historyResponse(r, { json: async () => payload }); await assert.rejects(historyRead(r.active), { message: 'YAHOO_UNAVAILABLE' });
  }
  assert.ok(r.active.state().connected, 'unavailable transport does not remove owner login');
});
test('history respects caller cancellation before and during requests', async () => {
  const r = await connectedRuntime(), canceled = new AbortController(); canceled.abort();
  await assert.rejects(historyRead(r.active, { signal: canceled.signal }), { message: 'CANCELED' });
  assert.ok(r.calls.fetch === 0 && r.active.state().connected, 'an already canceled chart request sends nothing');
  const cancel = new AbortController(); r.delayedFetch();
  const read = historyRead(r.active, { signal: cancel.signal });
  cancel.abort(); assert.ok(r.calls.request.options.signal.aborted, 'caller cancellation reaches the network signal');
  r.resolveFetch(); await assert.rejects(read, { message: 'CANCELED' });
  assert.ok(r.active.state().connected, 'canceling one chart does not remove the login');
});
test('history rejects late results after logout, OFF, a replacement login or expiry', async () => {
  for (const invalidate of [r => r.active.disconnect(), r => r.active.setEnabled(false), r => { r.active.login(); r.respond(); }, r => { r.advance(3600001); r.active.state(); }]) {
    const r = await connectedRuntime(); r.delayedFetch();
    const read = historyRead(r.active); await invalidate(r);
    assert.ok(r.calls.request.options.signal.aborted, 'invalidating login aborts the in-flight history request'); r.resolveFetch();
    await assert.rejects(read, { message: 'CANCELED' }, 'stale history is never returned to a chart');
  }
});
test('history cancellation during JSON parsing rejects a late payload', async () => {
  const r = await connectedRuntime(), cancel = new AbortController(); let finish;
  historyResponse(r, { json: () => new Promise(resolve => { finish = resolve; }) });
  const read = historyRead(r.active, { signal: cancel.signal }); await Promise.resolve();
  cancel.abort(); finish(HISTORY_PAYLOAD);
  await assert.rejects(read, { message: 'CANCELED' });
});
test('bounded readonly Sheets reads reject oversized advertised and streamed bodies', async () => {
  const r=await connectedRuntime();let options;
  r.view.fetch=async(url,o)=>{options=o;return new Response(JSON.stringify({values:[['date','symbol','B/S','quantity']]}));};
  const value=await r.active.fetchValues(ID,"'Trades'!A1:D1025",{maxBytes:1024});assert.equal(value.values.length,1);assert.equal(options.redirect,'error');assert.equal(options.cache,'no-store');assert.equal(options.credentials,'omit');assert.equal(options.referrerPolicy,'no-referrer');
  r.view.fetch=async()=>new Response('{}',{headers:{'content-length':'2048'}});await assert.rejects(r.active.fetchValues(ID,"'Trades'!A1:D1025",{maxBytes:1024}),{message:'SOURCE_TOO_LARGE'});
  r.view.fetch=async()=>new Response(JSON.stringify({values:[['x'.repeat(2048)]]}));await assert.rejects(r.active.fetchValues(ID,"'Trades'!A1:D1025",{maxBytes:1024}),{message:'SOURCE_TOO_LARGE'});
});
test('bounded Sheets reads honor caller abort and disconnect cancels concurrent reads', async () => {
 const r=await connectedRuntime(),first=new AbortController();first.abort();await assert.rejects(r.active.fetchValues(ID,"'Trades'!A1:D1025",{signal:first.signal,maxBytes:1024}),{message:'CANCELED'});
 const pending=[];r.view.fetch=async(url,options)=>new Promise((resolve,reject)=>{pending.push(options.signal);options.signal.addEventListener('abort',()=>reject(Error('ABORT')),{once:true});});
 const a=r.active.fetchValues(ID,"'Trades'!A1:D1025",{maxBytes:1024}),b=r.active.fetchValues(ID,"'Universe'!A1:C1025",{maxBytes:1024});
 r.active.setEnabled(false);const settled=await Promise.allSettled([a,b]);assert.ok(pending.every(s=>s.aborted));assert.ok(settled.every(s=>s.status==='rejected'&&s.reason.message==='CANCELED'));
});

test('identity expansion accepts required grants plus openid/profile and duplicate email aliases', async () => {
 const r=runtime(),session=r.session();session.setEnabled(true);await session.prepare();
 for(const scope of [SCOPE+' openid',SCOPE+' profile',SCOPE+' openid https://www.googleapis.com/auth/userinfo.profile','email openid '+EMAIL_ALIAS+' '+READONLY_SCOPE+' profile']){session.login();r.respond({scope});assert.ok(session.state().connected,'Google identity expansion must connect');}
});
test('popup errors expose fixed codes, never arbitrary provider text, and ignore stale callbacks', async () => {
 const r=runtime(),session=r.session();session.setEnabled(true);await session.prepare();
 for(const [type,code] of [['popup_failed_to_open','AUTH_POPUP_FAILED_TO_OPEN'],['popup_closed','AUTH_POPUP_CLOSED'],['unknown','AUTH_POPUP_UNKNOWN'],['untrusted private text','AUTH_POPUP_UNKNOWN']]){session.login();r.popupError(type);assert.equal(session.state().error,code);assert.equal(session.state().connected,false);assert.equal(session.state().pending,false);}
 session.login();session.setEnabled(false);r.popupError('popup_closed');assert.equal(session.state().error,'');
});
