'use strict';
// Synthetic daily bars for the new frontend's 2. 기술적 분석 screen tests (web_app_technical_browser_test.js,
// web_app_technical_node_test.js). Not market data: every close is a made-up number ending in the sentinel decimals .0718293,
// so a test can prove that no bar value leaves [data-ram-price] text (screen), storage, requests or the console. The payload
// has the Worker's private-history/1 shape (PrivateHistory.validateHistory accepts it); only the device-chart path of the
// screen sees it, and only after a real click in the test.
const DAY = 86400000;
const SENTINEL = '.0718293';
const RANGE_DAYS = Object.freeze({ '1mo': 31, '3mo': 92, '6mo': 183, '1y': 366, '2y': 731, '5y': 1827 });

function weekdays(from, to) {
  const out = [];
  for (let t = Date.parse(from + 'T00:00:00Z'); t <= Date.parse(to + 'T00:00:00Z'); t += DAY) { const d = new Date(t); if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); }
  return out;
}
// A smooth made-up wave between about 180 and 240 with the sentinel decimals; a whole number part keeps the decimals exact in String().
const closeAt = (i) => 210 + Math.round(24 * Math.sin(i / 17) + 6 * Math.sin(i / 5)) + Number(SENTINEL);
// One Worker answer for symbol / range read at readAt (ISO). The last bar is IN_PROGRESS (as the Worker marks the read day).
function history(symbol, range, readAt) {
  const end = readAt.slice(0, 10), start = new Date(Date.parse(end + 'T00:00:00Z') - RANGE_DAYS[range] * DAY).toISOString().slice(0, 10);
  const days = weekdays(start, end);
  const bars = days.map((d, i) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null, close: closeAt(i), adjusted_close: null, volume: null,
    session_status: i === days.length - 1 ? 'IN_PROGRESS' : 'COMPLETE' }));
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: 'USD', exchange: 'SYNTHETIC', timezone: 'America/New_York', interval: '1d',
    basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: readAt, bars };
}
module.exports = Object.freeze({ SENTINEL, RANGE_DAYS, history, closeAt, weekdays });
