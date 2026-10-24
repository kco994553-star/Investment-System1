'use strict';
// New frontend P1 helper (not a test): builds the development site (tools/build_web_app.py) into a fresh temporary folder,
// serves it on 127.0.0.1 with a free port, and lets a browser test answer chosen files with fixtures (the live-only public
// files such as sec-qgv2.json are absent from the offline build). Also the shared boundary checks every P1/P2 browser test
// needs: requests that leave the origin, console errors (with an explicit list of intended 404s), device storage, and
// assertRamOnly — a synthetic sentinel price may appear only as text inside a [data-ram-price] element, never in an attribute.
// Fixtures carry synthetic values only; nothing here reads real prices.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { execFileSync } = require('node:child_process');
const { ROOT } = require('./web_app_reuse');

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2',
  '.txt': 'text/plain', '.png': 'image/png', '.svg': 'image/svg+xml' };

// Builds into a new empty temporary folder (the build refuses a non-empty one) and returns its path.
function build() {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-p1-'));
  fs.rmSync(out, { recursive: true });
  execFileSync('python3', [path.join(ROOT, 'implementation/tools/build_web_app.py'), '--out', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  return out;
}

// fixture: {status=200, json} | {status=200, body, type} | (req, url) => one of those. A fixture answers before the built file.
function answer(res, f) {
  const status = f.status || 200, body = 'json' in f ? JSON.stringify(f.json) : f.body === undefined ? '' : f.body;
  res.writeHead(status, { 'content-type': f.type || ('json' in f ? 'application/json' : 'text/plain') });
  res.end(body);
}

// start({fixtures, out}) -> {base, origin, out, requests, fixture(name, f|null), close()}
async function start({ fixtures = {}, out = null } = {}) {
  const dir = out || build(), owned = !out, table = new Map(Object.entries(fixtures)), requests = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://x'), name = decodeURIComponent(url.pathname.slice(1)) || 'index.html';
    requests.push({ method: req.method, name, search: url.search });
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); res.end(); return; }
    if (table.has(name)) { const f = table.get(name); answer(res, typeof f === 'function' ? f(req, url) : f); return; }
    const file = path.join(dir, name);
    if (!file.startsWith(dir + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(res);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + server.address().port + '/';
  return {
    base, origin: new URL(base).origin, out: dir, requests,
    fixture(name, f) { if (f === null) table.delete(name); else table.set(name, f); },
    async close() { await new Promise((r) => server.close(r)); if (owned) fs.rmSync(dir, { recursive: true, force: true }); },
  };
}

// Collects, for one page: every request URL, the ones leaving the origin, and console/page errors. An intended 404 of a
// listed same-origin file name (e.g. a live-only file the test leaves unpublished) is not an error.
function watch(page, origin, { allow404 = [] } = {}) {
  const seen = { requests: [], outside: [], errors: [] }, allowed = new Set(allow404);
  page.on('request', (r) => { seen.requests.push(r.url()); if (new URL(r.url()).origin !== origin) seen.outside.push(r.url()); });
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const at = m.location() && m.location().url ? new URL(m.location().url, origin) : null;
    if (at && at.origin === origin && /status of 404/.test(m.text()) && allowed.has(decodeURIComponent(at.pathname.slice(1)))) return;
    seen.errors.push(m.text());
  });
  page.on('pageerror', (e) => seen.errors.push(String(e)));
  return seen;
}

// Device storage counts and contents (contents so a test can look for sentinels in them).
async function storage(page) {
  return page.evaluate(async () => {
    const dump = (s) => { const o = {}; for (let i = 0; i < s.length; i++) { const k = s.key(i); o[k] = s.getItem(k); } return o; };
    const dbs = indexedDB.databases ? (await indexedDB.databases()).map((d) => d.name) : null;
    return { local: localStorage.length, session: sessionStorage.length, idb: dbs ? dbs.length : 0, idbNames: dbs, localItems: dump(localStorage), sessionItems: dump(sessionStorage) };
  });
}

// Which sentinels (by index) occur in any of the given strings.
function leaks(strings, sentinels) {
  const all = strings.map((s) => (typeof s === 'string' ? s : JSON.stringify(s))).join('\n');
  return sentinels.map(String).map((s, i) => (all.includes(s) ? i : -1)).filter((i) => i >= 0);
}

// RAM-only display rule for P2 screens: a sentinel price may show only as text under a [data-ram-price] element; never in an
// attribute, a form value or the title. Reports sentinel indexes, not values.
async function assertRamOnly(page, sentinels, label = '') {
  const bad = await page.evaluate((list) => {
    const out = [], hit = (t) => list.findIndex((s) => String(t).includes(s));
    const walk = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const i = hit(n.nodeValue);
      if (i >= 0 && !(n.parentElement && n.parentElement.closest('[data-ram-price]'))) out.push({ where: 'text', sentinel: i, in: n.parentElement ? n.parentElement.tagName : null });
    }
    for (const el of document.querySelectorAll('*')) {
      for (const a of el.attributes) { const i = hit(a.value); if (i >= 0) out.push({ where: 'attribute', sentinel: i, name: a.name, in: el.tagName }); }
      if ('value' in el && typeof el.value === 'string') { const i = hit(el.value); if (i >= 0) out.push({ where: 'value', sentinel: i, in: el.tagName }); }
    }
    const t = hit(document.title); if (t >= 0) out.push({ where: 'title', sentinel: t });
    return out;
  }, sentinels.map(String));
  assert.deepEqual(bad, [], (label ? label + ': ' : '') + 'sentinel price outside [data-ram-price] text');
}

module.exports = Object.freeze({ TYPES, build, start, watch, storage, leaks, assertRamOnly });
