'use strict';
// Feature 3.5 기술 조건 필터 test helpers (tools/web_app_tech_filter_node_test.js, tools/web_app_tech_filter_browser_test.js).
//  - CODEX: Codex's public synthetic fixture of technical-leaderboard/1, byte-for-byte the file of #469 f1ca390a
//    (implementation/tests/fixtures/technical_leaderboard_v1.json, sha256 pinned in CODEX_SHA256). The screen reads it unchanged.
//  - joined(companies): one more SYNTHETIC board in the same schema whose security ids are the leaderboard's own row ids, so the
//    leaderboard table filter (QGV order) can be shown. Ranks, deciles, medians and conditions follow Codex's rules
//    (TECHNICAL_LEADERBOARD_V1.md): rank 1 = largest value, ties by security id ascending; k = floor(N×0.10); first k D10, last k D1;
//    D9..D2 get (N−2k)//8 each, the first (N−2k)%8 bins one more; N < 10 no decile; median = middle value or mean of the middle pair.
//    Market-down day: every 6-month momentum is negative. Two companies have no volatility (METRIC_NOT_AVAILABLE).
// SYNTHETIC VALUES ONLY; nothing here is written to a public file.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { ROOT } = require('./web_app_reuse');

const CODEX_PATH = path.join(ROOT, 'implementation/tests/fixtures/technical_leaderboard_v1.json');
const CODEX_SHA256 = '4df008ec1a71b315e7ca618f4ccaec63abcdf3d12b454a897297d414b4d2a634';
const codexText = () => fs.readFileSync(CODEX_PATH, 'utf8');
const codex = () => JSON.parse(codexText());
const codexSha = () => crypto.createHash('sha256').update(fs.readFileSync(CODEX_PATH)).digest('hex');
const METRICS = ['momentum_3m', 'momentum_6m', 'momentum_12m', 'volatility_6m', 'dollar_volume_6m'];

// Values in hundredths (integers) so medians stay exact; written as decimal strings with two decimals.
const str = (c) => (c < 0 ? '-' : '') + String(Math.floor(Math.abs(c) / 100)) + '.' + String(Math.abs(c) % 100).padStart(2, '0');
function deciles(n) {
  if (n < 10) return null;
  const k = Math.floor(n / 10), rem = n - 2 * k, q = Math.floor(rem / 8), r = rem % 8, out = [];
  for (let i = 0; i < k; i++) out.push(10);
  for (let d = 9; d >= 2; d--) for (let i = 0; i < q + (9 - d < r ? 1 : 0); i++) out.push(d);
  for (let i = 0; i < k; i++) out.push(1);
  return out;
}
function metric(ids, values, reasonFor) {
  const valid = ids.map((id, i) => ({ id, c: values[i] })).filter((x) => x.c !== null);
  valid.sort((a, b) => b.c - a.c || (a.id < b.id ? -1 : 1));
  const n = valid.length, dec = deciles(n), sorted = valid.map((x) => x.c).sort((a, b) => a - b);
  const medC = n ? (n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2) : null;
  // medC is a whole or half hundredth: written exactly with three decimals (thousandths).
  const m3 = medC === null ? null : Math.round(medC * 10), median = m3 === null ? null : (m3 < 0 ? '-' : '') + String(Math.floor(Math.abs(m3) / 1000)) + '.' + String(Math.abs(m3) % 1000).padStart(3, '0');
  const place = new Map(valid.map((x, i) => [x.id, { rank: i + 1, decile: dec ? dec[i] : null }]));
  const rows = ids.map((id, i) => {
    const c = values[i];
    if (c === null) return { value: null, null_reasons: [reasonFor], security_id: id, series_id: 'SYNTHETIC:R-' + id, rank: null, decile: null,
      conditions: { gt_zero: null, ge_median: null, gt_median: null, top_decile: null, bottom_decile: null, exclude_D10: null } };
    const p = place.get(id), d = p.decile, half = medC;
    return { value: str(c), null_reasons: d === null ? ['N_BELOW_10'] : [], security_id: id, series_id: 'SYNTHETIC:R-' + id, rank: p.rank, decile: d,
      conditions: { gt_zero: c > 0, ge_median: c >= half, gt_median: c > half, top_decile: d === null ? null : d === 10, bottom_decile: d === null ? null : d === 1, exclude_D10: d === null ? null : d !== 10 } };
  });
  return { n_valid: n, n_members: ids.length, median, k: n >= 10 ? Math.floor(n / 10) : null, null_reason: null, rows };
}
// A confirmed board over the given ids (order kept: later ids get larger momentum, so callers put the rows they want at the top last).
function joined(ids, { signal_day = '2018-02-16', group_id = 'SYNTHETIC:LEADERBOARD' } = {}) {
  const n = ids.length, vals = {
    momentum_3m: ids.map((_, i) => -3000 + Math.round((2500 * i) / n)),
    momentum_6m: ids.map((_, i) => -4500 + Math.round((4000 * i) / n)),
    momentum_12m: ids.map((_, i) => -3500 + Math.round((3000 * i) / n)),
    volatility_6m: ids.map((_, i) => (i === n - 1 || i === n - 3 ? null : 80 + ((i * 7) % n))),
    dollar_volume_6m: ids.map((_, i) => 9876543 + 13579 * ((i * 5) % n)),
  };
  const metrics = Object.fromEntries(METRICS.map((m) => [m, metric(ids, vals[m], 'METRIC_NOT_AVAILABLE')]));
  return { schema: 'technical-leaderboard/1', signal_day, settings_version: 'technical-leaderboard/2026-11-03.1', settings_sha256: 'e'.repeat(64), group_id,
    membership_status: 'CONFIRMED', membership_source: 'SYNTHETIC:MEMBERSHIP', population_hash: 'f'.repeat(64), metrics };
}
module.exports = { CODEX_PATH, CODEX_SHA256, codex, codexText, codexSha, METRICS, deciles, joined };
