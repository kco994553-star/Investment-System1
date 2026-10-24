'use strict';
// New frontend P1 helper (not a test): the one place that knows where the old modules live and which of them the new
// frontend reuses. Plan A (tools/build_web_app.py): a script the page loads that has no file of that name in web_app is an old
// web_assets file kept byte-identical by the build. What the page loads (P2-1a): index.html's scripts (the first screen, web_app
// files only), then web_app/loader.js LOAD_ORDER after the first paint (the one load list, read here the way the build reads
// it). When the old modules move into web_app (P3), OLD below is the only line node tests need changed.
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PRODUCT = path.join(ROOT, 'implementation/src/investment_system/product');
const OLD = path.join(PRODUCT, 'web_assets');
const NEW = path.join(PRODUCT, 'web_app');

const isFile = (p) => fs.existsSync(p) && fs.statSync(p).isFile();
// <script src> values of a page in document order (comments skipped). Inline scripts are reported as '' so callers can fail.
function scriptsOf(html) {
  const text = String(html).replace(/<!--[\s\S]*?-->/g, '');
  return [...text.matchAll(/<script\b([^>]*)>/gi)].map((m) => { const src = /\bsrc="([^"]*)"/i.exec(m[1]); return src ? src[1] : ''; });
}
const newIndex = () => fs.readFileSync(path.join(NEW, 'index.html'), 'utf8');
const oldIndex = () => fs.readFileSync(path.join(OLD, 'index.html'), 'utf8');
// loader.js LOAD_ORDER, parsed as build_web_app.load_order parses it: exactly one literal of plain quoted names.
function loadOrderOf(text) {
  const found = [...String(text).matchAll(/const LOAD_ORDER=Object\.freeze\(\[([\s\S]*?)\]\);/g)];
  if (found.length !== 1) throw new Error('LOAD_ORDER_MISSING');
  const items = found[0][1].split(',').map((x) => x.trim());
  if (items.length && items[items.length - 1] === '') items.pop();
  return items.map((x) => { const m = /^'([^'\\]*)'$/.exec(x); if (!m) throw new Error('LOAD_ORDER_INVALID ' + x.slice(0, 40)); return m[1]; });
}
const loadOrder = () => loadOrderOf(fs.readFileSync(path.join(NEW, 'loader.js'), 'utf8'));
// The first screen's scripts (index.html), the page's whole load order (then LOAD_ORDER), and the old page's scripts in
// first-load order (the old page loads two playbook files twice).
const firstPaint = () => scriptsOf(newIndex());
const scripts = () => [...firstPaint(), ...loadOrder()];
const oldScripts = () => [...new Set(scriptsOf(oldIndex()))];
// Same rule as build_web_app.reused_old_files: web_app wins on a shared name, otherwise the file must be in web_assets.
function reused(list = scripts()) {
  return list.filter((src) => {
    if (isFile(path.join(NEW, src))) return false;
    if (!isFile(path.join(OLD, src))) throw new Error('REUSE_MISSING ' + src);
    return true;
  });
}
const oldPath = (name) => path.join(OLD, name);
const requireOld = (name) => require(oldPath(name));
const newPath = (name) => path.join(NEW, name);
const requireNew = (name) => require(newPath(name));

// Browser global of an old UMD module (root.X = api / factory, r.X = d), read from its own source. A global-only module
// (macro-cycle-ring.js: root.X = Object.freeze({...}) on window, else globalThis; no module.exports) sets it when required.
function globalName(name) {
  const text = fs.readFileSync(oldPath(name), 'utf8');
  const m = /\b(?:root|r|g|global)\.([A-Z][A-Za-z0-9]*)\s*=\s*(?:api|d|factory)\b/.exec(text) || /\broot\.([A-Z][A-Za-z0-9]*)\s*=\s*Object\.freeze\(/.exec(text);
  if (!m) throw new Error('NO_GLOBAL ' + name);
  return m[1];
}
/* Node tests of the P1 layer: fresh copies of old modules (module state such as QgvScores' memo, DataRefresh's generation or
   Qgv2Inputs.lastReason starts empty), set as globals on `win` and on globalThis (old modules read siblings through globalThis,
   which in the browser is the same window). app-config.js is browser-only (window.InvestmentAppConfig) and runs against `win`.
   Default list: every reused module, in load order. */
function loadOld(win, names = reused()) {
  for (const name of names) if (name !== 'app-config.js') delete require.cache[require.resolve(oldPath(name))];
  const out = {};
  for (const name of names) {
    if (name === 'app-config.js') { require('node:vm').runInNewContext(fs.readFileSync(oldPath(name), 'utf8'), { window: win, Object }); out.InvestmentAppConfig = win.InvestmentAppConfig; continue; }
    const exported = require(oldPath(name)), g = globalName(name), api = exported && Object.keys(exported).length ? exported : globalThis[g];
    if (!api) throw new Error('NO_EXPORT ' + name);
    win[g] = api; globalThis[g] = api; out[g] = api;
  }
  return out;
}
/* A browser-like window for node tests. Its own functions refuse any other `this`, as a browser window does ("Illegal invocation"),
   so a view that forgets to bind them fails here too. fetch answers from `files` ({name: {status, json} | {status, body} |
   {status, bytes}} or a function(name, init)) and records every request; timers are recorded, never run.
   Its Event follows the browser where the click gate reads it: isTrusted is an own accessor of each event and eventPhase a
   prototype accessor, both refusing an object that is not a real event of this window (a forged prototype, a Proxy).
   trusted(type, props) makes a real user gesture (isTrusted true, e.g. props {key: 'Enter'}) that is being dispatched until the
   current task ends (setImmediate), as a handler's event is; ended(e) ends that dispatch now (a kept event replayed later). */
function nodeWindow({ files = {}, origin = 'https://site.test' } = {}) {
  const events = new EventTarget(), doc = new EventTarget(), requests = [], timers = [];
  require('node:events').setMaxListeners(0, events, doc);// one window can serve many layer instances in a test
  Object.assign(doc, { visibilityState: 'visible', documentElement: { lang: 'ko' }, getElementById: () => null });
  const made = new WeakSet(), trustedSet = new WeakSet(), dispatching = new WeakSet();
  const brand = (e) => { if (!made.has(e)) throw new TypeError('Illegal invocation'); };
  function isTrusted() { brand(this); return trustedSet.has(this); }
  class WinEvent extends Event {
    constructor(type, init) { super(type, init); made.add(this); Object.defineProperty(this, 'isTrusted', { get: isTrusted, enumerable: true, configurable: false }); }
    get eventPhase() { brand(this); return dispatching.has(this) ? 2 : super.eventPhase; }
  }
  const win = { requests, timers, document: doc, location: { href: origin + '/app/', origin }, Response, Request, Headers, Event: WinEvent, CustomEvent, AbortController, URL, TextEncoder, TextDecoder,
    trusted: (type, props = {}) => {
      const e = Object.defineProperties(new WinEvent(type), Object.fromEntries(Object.entries(props).map(([k, value]) => [k, { value }])));
      trustedSet.add(e); dispatching.add(e); setImmediate(() => dispatching.delete(e)); return e;
    },
    ended: (e) => { dispatching.delete(e); return e; } };
  const own = (name, fn) => { win[name] = function (...a) { if (this !== win) throw new TypeError('Illegal invocation: ' + name); return fn(...a); }; };
  own('addEventListener', (...a) => events.addEventListener(...a));
  own('removeEventListener', (...a) => events.removeEventListener(...a));
  own('dispatchEvent', (e) => events.dispatchEvent(e));
  own('setInterval', (fn, ms) => timers.push({ fn, ms }));
  own('setTimeout', (fn, ms) => timers.push({ fn, ms }));
  own('clearInterval', () => {});
  own('clearTimeout', () => {});
  own('fetch', async (input, init = {}) => {
    const name = String(input), f = typeof files === 'function' ? files(name, init) : files[name];
    requests.push({ name, init: { ...init } });
    if (f instanceof Error) throw f;
    if (!f) return new Response('', { status: 404 });
    const status = f.status || 200, body = 'json' in f ? JSON.stringify(f.json) : 'bytes' in f ? f.bytes : f.body === undefined ? '' : f.body;
    return new Response([204, 205, 304].includes(status) ? null : body, { status, headers: { 'content-type': 'application/json' } });
  });
  return win;
}

module.exports = Object.freeze({ ROOT, OLD, NEW, scriptsOf, newIndex, oldIndex, loadOrderOf, loadOrder, firstPaint, scripts, oldScripts, reused, oldPath, requireOld, newPath, requireNew, globalName, loadOld, nodeWindow });
