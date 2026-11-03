'use strict';
// Feature 3.5 기술 조건 필터 test fixture (tools/web_app_tech_filter_node_test.js, tools/web_app_tech_filter_browser_test.js).
// SYNTHETIC VALUES ONLY, in the proposed tech-screen-v0 shape (web_app/tech-screen.js); nothing here is written to a public file.
// payload(companies) builds two evaluation days over the given [{id, ticker}] (the leaderboard's own rows in the browser test):
//  - 2026-09-30 "market down": every 6-month momentum is negative, so D10 of 6개월 모멘텀 is still a negative return.
//    U_A = every company, U_B = every second one, U_SMALL = six companies (n_valid 6 < 10: values and a median, no deciles,
//    reason GROUP_TOO_SMALL). One U_B company in the 6-month momentum D10 has no volatility (SOURCE_MISSING), so the condition
//    "변동성 D10 제외" is 판정 불가 for it; another one in that D10 is itself in the volatility D10 (fails that condition).
//    "6개월 모멘텀 0% 초과" in U_B passes nobody (calculation fine, zero matches).
//  - 2026-10-30: the same groups with positive momentum (a second day to pick).
// Deciles are computed here per group over valid values (ascending value, D10 = top tenth); medians are the groups' medians.
const DAYS = ['2026-09-30', '2026-10-30'];
const H40 = 'd'.repeat(40);
function decile(rank, n) { return Math.min(10, Math.floor((rank * 10) / n) + 1); }
// value(i, k) for company index i on day k; null with a reason when the company has no value.
function series(list) {
  const n = list.length;
  return {
    // Scaled by the company count so the down day stays negative and 0.95 stays the largest volatility for any list size.
    mom_3m: (i, k) => (k === 0 ? -0.30 + (0.25 * i) / n : 0.02 + (0.30 * i) / n),
    mom_6m: (i, k) => (k === 0 ? -0.45 + (0.40 * i) / n : 0.05 + (0.40 * i) / n),
    mom_12m: (i, k) => (i === 3 ? null : k === 0 ? -0.35 + (0.30 * i) / n : 0.11 + (0.50 * i) / n),
    vol_6m: (i) => 0.18 + (0.30 * ((i * 7) % n)) / n,
    adv_6m: (i) => 98765432.1 + 13579246.8 * ((i * 5) % n),
  };
}
function payload(companies, { status = 'SYNTHETIC' } = {}) {
  // The given order is kept: momentum rises with the index, so a caller puts the companies it wants in the top deciles last.
  const list = [...companies];
  if (new Set(list.map((c) => c.id)).size !== list.length) throw new Error('FIXTURE_DUPLICATE');
  if (list.length < 40) throw new Error('FIXTURE_TOO_FEW ' + list.length);
  const fn = series(list), METRICS = ['mom_3m', 'mom_6m', 'mom_12m', 'vol_6m', 'adv_6m'];
  const groups = [
    { id: 'U_A', label: 'U-A (합성)', ids: list.map((c) => c.id) },
    { id: 'U_B', label: 'U-B (합성)', ids: list.filter((_, i) => i % 2 === 0).map((c) => c.id) },
    { id: 'U_SMALL', label: '소표본 시험 그룹 (합성)', ids: list.slice(0, 6).map((c) => c.id) },
  ];
  const ub = groups[1].ids, top = (k) => ub.map((id) => list.findIndex((c) => c.id === id)).sort((a, b) => fn.mom_6m(b, k) - fn.mom_6m(a, k));
  const evaluations = DAYS.map((as_of, k) => {
    const raw = list.map((c, i) => Object.fromEntries(METRICS.map((m) => [m, fn[m](i, k)])));
    // 6-month momentum D10 of U_B (top tenth): the first has no volatility; the second gets the group's largest volatility.
    const order = top(k), nb = ub.length, d10 = order.slice(0, Math.max(2, Math.ceil(nb / 10)));
    raw[d10[0]].vol_6m = null;
    raw[d10[1]].vol_6m = 0.95;
    const stats = {}, deciles = {};
    for (const g of groups) {
      stats[g.id] = {};
      for (const m of METRICS) {
        const vals = g.ids.map((id) => { const i = list.findIndex((c) => c.id === id); return { id, v: raw[i][m] }; }).filter((x) => x.v !== null).sort((a, b) => a.v - b.v);
        const n = vals.length, small = n < 10, median = n ? (n % 2 ? vals[(n - 1) / 2].v : (vals[n / 2 - 1].v + vals[n / 2].v) / 2) : null;
        stats[g.id][m] = { n_valid: n, median, deciles: !small, reason: small ? 'GROUP_TOO_SMALL' : null };
        vals.forEach((x, r) => { (deciles[x.id] = deciles[x.id] || {}); (deciles[x.id][m] = deciles[x.id][m] || {}); deciles[x.id][m][g.id] = small ? null : decile(r, n); });
      }
    }
    const rows = list.map((c, i) => {
      const gs = groups.filter((g) => g.ids.includes(c.id)).map((g) => g.id);
      const metrics = {};
      for (const m of METRICS) {
        const v = raw[i][m], dec = {};
        for (const g of gs) dec[g] = v === null ? null : deciles[c.id][m][g];
        const expected = m === 'mom_3m' ? 63 : m === 'mom_12m' ? 252 : 126;
        metrics[m] = { value: v, obs_days: v === null ? null : expected - (i % 3), expected_days: expected, reason: v === null ? (m === 'vol_6m' ? 'SOURCE_MISSING' : 'PRICE_HISTORY_SHORT') : null, decile: dec };
      }
      return { company_id: c.id, ticker: c.ticker, groups: gs, metrics };
    });
    return { as_of, groups: groups.map((g) => ({ id: g.id, label: g.label, members: g.ids.length })), stats, rows };
  });
  return { schema_version: 'tech-screen-v0', generated_at: '2026-11-03T09:00:00Z', source_commit: H40, data_status: status, evaluations };
}
// The U_B 6-month momentum D10 companies of day k (ids), the one without volatility and the one in the volatility D10.
function cases(p, k = 0) {
  const ev = p.evaluations[k], ub = ev.rows.filter((r) => r.groups.includes('U_B'));
  const d10 = ub.filter((r) => r.metrics.mom_6m.decile.U_B === 10);
  return { d10: d10.map((r) => r.company_id), noVol: d10.filter((r) => r.metrics.vol_6m.value === null).map((r) => r.company_id),
    volTop: d10.filter((r) => r.metrics.vol_6m.decile.U_B === 10).map((r) => r.company_id), small: ev.rows.filter((r) => r.groups.includes('U_SMALL')).map((r) => r.company_id) };
}
module.exports = { DAYS, payload, cases };
