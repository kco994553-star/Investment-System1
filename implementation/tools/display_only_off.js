'use strict';
// Browser tests that assert "no external request" for other features turn the two display-only external features
// (TradingView widgets, company logos) off through their own device switches before any page script runs.
// tradingview_widgets_browser_test.js and company_logos_browser_test.js cover them ON, against stubs.
const KEYS = { 'investment.web.v1.tradingview-widgets': 'off', 'investment.web.v1.logo-display': 'off' };
async function displayOnlyOff(target) {
  await target.addInitScript((keys) => {
    try { for (const [key, value] of Object.entries(keys)) if (localStorage.getItem(key) === null) localStorage.setItem(key, value); } catch (_) {}
  }, KEYS);
}
module.exports = { KEYS, displayOnlyOff };
