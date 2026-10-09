/* Synthetic credentials stay in memory; failures never print request payloads. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const filename = require('node:path').join(__dirname, '../src/investment_system/product/web_assets/google-sheet-quotes.js');
const api = fs.existsSync(filename) ? require(filename) : {};
const SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly';
const ID = ['synthetic', 'spreadsheet', 'fixture'].join('_');
function runtime() {
  let now = 1000000, callbacks, pendingResolve;
  const calls = { scripts: 0, popup: 0, revoke: 0, fetch: 0, config: null, request: null };
  const token = ['memory', 'only', 'synthetic', 'credential'].join('-');
  const view = { setTimeout: () => 1, clearTimeout() {}, AbortController, document: { createElement: () => ({}), head: { append(script) { calls.scripts++; view.google = { accounts: { oauth2: oauth } }; queueMicrotask(() => script.onload()); } } },
    fetch: async (url, options) => { calls.fetch++; calls.request = { url, options }; return { ok: true, status: 200, json: async () => ({ values: [['code', 'price', 'tradetime']] }) }; } };
  const oauth = { initTokenClient(config) { calls.config = config; callbacks = config; return { requestAccessToken() { calls.popup++; } }; }, revoke(value, done) { calls.revoke++; assert.ok(value === token, 'revoke uses only current memory token'); done({}); } };
  const session = () => api.createSession(view, { clientId: 'public-client-id', now: () => now });
  return { view, calls, token, oauth, session, advance: value => { now += value; }, respond: (value = {}) => callbacks.callback({ access_token: token, expires_in: 3600, scope: SCOPE, ...value }), delayedFetch() { view.fetch = (url, options) => { calls.fetch++; calls.request = { url, options }; return new Promise(resolve => { pendingResolve = resolve; }); }; }, resolveFetch: () => pendingResolve({ ok: true, status: 200, json: async () => ({ values: [] }) }) };
}
test('auth exports exist without starting a network request', () => {
  for (const name of ['mount', 'extractSpreadsheetId', 'sheetsURL', 'createSession']) assert.equal(typeof api[name], 'function', name + ' is available');
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
test('OFF and preparation make no popup or Sheets request; login uses only readonly scope', async () => {
  const r = runtime(), session = r.session();
  assert.ok(!session.state().connected && !session.state().enabled);
  assert.throws(() => session.login(), { message: 'OFF' });
  assert.ok(r.calls.scripts === 0 && r.calls.fetch === 0 && r.calls.popup === 0);
  session.setEnabled(true); await session.prepare();
  assert.ok(r.calls.scripts === 1 && r.calls.popup === 0 && r.calls.fetch === 0);
  session.login(); assert.ok(r.calls.popup === 1 && r.calls.config.scope === SCOPE && r.calls.config.include_granted_scopes === false);
  r.respond(); assert.ok(session.state().connected && r.calls.fetch === 0);
  const json = await session.fetchValues(ID, 'Quotes!A1:C22');
  assert.ok(Array.isArray(json.values) && r.calls.fetch === 1);
  assert.ok(r.calls.request.options.headers.Authorization === 'Bearer ' + r.token, 'authorization exists only in the direct request');
  assert.ok(r.calls.request.options.credentials === 'omit' && r.calls.request.options.cache === 'no-store' && r.calls.request.options.referrerPolicy === 'no-referrer');
  assert.ok(!JSON.stringify(session.state()).includes(r.token), 'public state never exposes a token');
});
test('expiry clears token before a request and 401 requires another button login', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare(); session.login(); r.respond(); r.advance(3600001);
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
  session.setEnabled(true); session.login(); r.respond(); r.delayedFetch();
  const read = session.fetchValues(ID, 'Quotes!A1:C22'); session.setEnabled(false); r.resolveFetch();
  await assert.rejects(read, { message: 'CANCELED' }); assert.ok(!session.state().connected);
});
test('token scope escalation and malformed token responses are rejected', async () => {
  const r = runtime(), session = r.session(); session.setEnabled(true); await session.prepare();
  for (const value of [{ scope: SCOPE + ' https://www.googleapis.com/auth/drive' }, { access_token: '' }, { expires_in: 0 }, { token_type: 'Other' }]) { session.login(); r.respond(value); assert.ok(!session.state().connected); }
});
