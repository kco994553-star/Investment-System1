'use strict';
// Example_* tabs (decision 2026-10-11): any tab whose name starts with "Example_" (e.g. Example_SetA_Trades) is ignored by
// the app: never read, never written, excluded from title listings and validation, never mistaken for Trades / Holdings /
// Virtual* / Quotes / Universe. Implemented centrally in GoogleSheetQuotes (title listings, values ranges, write allowlist)
// and checked here on an in-memory SYNTHETIC session. No real sheet, token or value is used.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const ASSETS = path.join(__dirname, '../src/investment_system/product/web_assets');
const Q = require(path.join(ASSETS, 'google-sheet-quotes.js'));
const S = require(path.join(ASSETS, 'virtual-ledger-sheets.js'));
const Setup = require(path.join(ASSETS, 'google-sheet-setup.js'));

const ID = ['synthetic', 'example', 'tabs', 'fixture'].join('_');
const TOKEN = ['memory', 'only', 'synthetic', 'example'].join('-');
const SCOPE = 'https://www.googleapis.com/auth/drive.file email';
const TABS = [
  { title: 'Quotes', sheetId: 0 }, { title: 'Trades', sheetId: 1 }, { title: 'Example_SetA_Trades', sheetId: 5000 },
  { title: 'Example_Trades', sheetId: 5001 }, { title: 'Example_VirtualA', sheetId: 5002 }, { title: 'Example_Holdings', sheetId: 5003 },
  { title: 'VirtualMeta', sheetId: 7 }];

function harness(tabs = TABS) {
  const requests = [];
  let callbacks;
  const oauth = { initTokenClient(config) { callbacks = config; return { requestAccessToken() {} }; }, revoke(_t, done) { done({}); } };
  const json = (body) => new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
  const view = { setTimeout: () => 1, clearTimeout() {}, AbortController, google: { accounts: { oauth2: oauth } },
    async fetch(url, options = {}) {
      const u = new URL(url), method = options.method || 'GET';
      requests.push([method, decodeURIComponent(u.pathname), u.searchParams.get('fields')]);
      if (u.searchParams.get('fields') === 'sheets(properties(title))') return json({ sheets: tabs.map((t) => ({ properties: { title: t.title } })) });
      if (u.searchParams.get('fields') === 'sheets(properties(title,sheetId))') return json({ sheets: tabs.map((t) => ({ properties: t })) });
      if (method === 'POST') return json({ replies: [] });
      return json({ range: 'x', values: [['header']] });
    } };
  const session = Q.createSession(view, { clientId: 'public-client-id', now: () => 1000 });
  session.setEnabled(true);
  return { session, requests, connect: async () => { await session.prepare(); session.login(); callbacks.callback({ access_token: TOKEN, expires_in: 3600, scope: SCOPE }); } };
}

test('title helpers: only names starting with Example_ are ignored; the range sheet name is parsed (quoted or bare)', () => {
  for (const t of ['Example_SetA_Trades', 'Example_', 'Example_Holdings']) assert.equal(Q.isIgnoredTab(t), true, t);
  for (const t of ['Trades', 'example_Trades', 'My Example_Trades', 'Examples', 'VirtualA', '', null]) assert.equal(Q.isIgnoredTab(t), false, String(t));
  assert.equal(Q.rangeSheet("'Example_SetA_Trades'!A1:D10"), 'Example_SetA_Trades');
  assert.equal(Q.rangeSheet("'It''s'!A1"), "It's");
  assert.equal(Q.rangeSheet('Quotes!A1:C22'), 'Quotes');
  assert.equal(Q.rangeSheet('Example_X'), 'Example_X');
  assert.throws(() => Q.sheetsURL(ID, "'Example_SetA_Trades'!A1:D1025"), /INVALID/);
  assert.throws(() => Q.sheetsURL(ID, 'Example_Trades!A1:D10'), /INVALID/);
  assert.match(Q.sheetsURL(ID, "'Trades'!A1:D1025"), /Trades/);
});

test('listings exclude Example_* tabs; reads and writes of an Example_* tab are refused before any request', async () => {
  const h = harness();
  await h.connect();
  assert.deepEqual(await h.session.sheetTitles(ID), ['Quotes', 'Trades', 'VirtualMeta']);
  assert.deepEqual((await h.session.sheetTabs(ID)).map((t) => t.title), ['Quotes', 'Trades', 'VirtualMeta']);
  const before = h.requests.length;
  await assert.rejects(h.session.fetchValues(ID, "'Example_SetA_Trades'!A1:D1025"), /INVALID/);
  await assert.rejects(h.session.fetchValues(ID, 'Example_Holdings!A1:G10', { maxBytes: 65536 }), /INVALID/);
  await assert.rejects(h.session.appendRows(ID, "'Example_VirtualA'!A1", [['x']]), /INVALID/);
  await assert.rejects(h.session.addTabs(ID, ['Example_VirtualA']), /INVALID/);
  assert.equal(h.requests.length, before, 'no request reached the sheet for an Example_* tab');
  // The write allowlist covers the new ledger tabs VirtualC / VirtualD (same drive.file session, no new scope).
  await h.session.addTabs(ID, ['VirtualC', 'VirtualD']);
  await h.session.appendRows(ID, "'VirtualC'!A1", [['ledger_id']]);
  await h.session.appendRows(ID, "'VirtualD'!A1", [['ledger_id']]);
  assert.ok(h.requests.slice(before).every(([method, p]) => method === 'POST' && !p.includes('Example_')));
});

test('a new Holdings tab id never collides with a hidden Example_* tab id', async () => {
  const h = harness();
  await h.connect();
  const out = await h.session.addHoldingsTab(ID);
  assert.equal(out.created, true);
  assert.ok(!TABS.some((t) => t.sheetId === out.sheetId), 'sheetId ' + out.sheetId + ' is free');
  assert.equal(out.sheetId, 5004);
});

test('ledger sheets and sheet setup never mistake Example_* tabs for Trades / Virtual* tabs', async () => {
  // A session whose listing still shows Example_* titles (defence in depth): the ledger loader drops them itself.
  const reads = [];
  const session = { async sheetTitles() { return ['Example_VirtualA', 'Example_VirtualMeta', 'VirtualFlags']; },
    async fetchValues(id, range) { reads.push(range); return { range, values: [['created_at', 'date', 'company', 'kind']] }; } };
  const sheet = await S.load(session, ID);
  assert.equal(sheet.state, 'READY');
  assert.deepEqual(reads.map((r) => Q.rangeSheet(r)), ['VirtualFlags']);
  assert.equal(sheet.tabs.VirtualA, false);
  // Sheet setup check: an Example_Trades tab does not satisfy the Trades tab check.
  const h = harness([{ title: 'Quotes', sheetId: 0 }, { title: 'Example_Trades', sheetId: 9 }, { title: 'Universe', sheetId: 2 }]);
  await h.connect();
  const result = await Setup.verify(h.session, ID);
  const trades = result.tabs.find((t) => t.tab === 'Trades');
  assert.deepEqual([trades.present, result.ready], [false, false]);
  assert.ok(h.requests.every(([, p]) => !p.includes('Example_')));
});
