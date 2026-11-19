'use strict';
// node --require <this> <browser test>: moves "now" by TEST_CLOCK_SHIFT_DAYS days, in Node and in every page.
// Used only by .github/workflows/browser-date-shift.yml (owner 2026-11-16: catch tests that expect "today" before the
// day comes). Without TEST_CLOCK_SHIFT_DAYS, or with 0, it changes nothing.
// Pages get Playwright's own clock (install at now+shift, then resume), so a test that pins its clock
// (clock.install / setFixedTime / setSystemTime) still wins exactly as it does without this file.
const days = Number(process.env.TEST_CLOCK_SHIFT_DAYS || '0');
if (!Number.isFinite(days) || days === 0) return;
const OFFSET = Math.round(days * 86400000);
// Node side.
(() => {
  const O = Date, off = OFFSET;
  function D(...a) { if (!new.target) return new O(O.now() + off).toString(); return a.length ? new O(...a) : new O(O.now() + off); }
  D.prototype = O.prototype; D.now = () => O.now() + off; D.parse = O.parse; D.UTC = O.UTC; Object.setPrototypeOf(D, O);
  globalThis.Date = D;
})();
const pw = require('playwright');
function wrapContext(c) {
  const clock = c.clock, install = clock.install.bind(clock);
  const ready = install({ time: new Date(Date.now()) }).then(() => clock.resume());
  // A test's own install becomes "jump to that time and run from there" on the already installed clock.
  clock.install = async (opts = {}) => { await ready; if (opts.time !== undefined) await clock.setSystemTime(opts.time); };
  return ready.then(() => c);
}
for (const type of [pw.chromium, pw.firefox, pw.webkit]) {
  if (!type) continue;
  const launch = type.launch.bind(type);
  type.launch = async (...args) => {
    const browser = await launch(...args);
    const newContext = browser.newContext.bind(browser);
    browser.newContext = async (...a) => wrapContext(await newContext(...a));
    browser.newPage = async (...a) => { const c = await browser.newContext(...a); const p = await c.newPage(); const close = p.close.bind(p); p.close = async (...x) => { await close(...x); await c.close(); }; return p; };
    return browser;
  };
  if (type.launchPersistentContext) {
    const lpc = type.launchPersistentContext.bind(type);
    type.launchPersistentContext = async (...a) => wrapContext(await lpc(...a));
  }
}
process.stderr.write('CLOCK_SHIFT_DAYS ' + days + '\n');
