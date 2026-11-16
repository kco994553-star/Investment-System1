'use strict';
// Leaderboard table trial (development only, not shipped, not in CI): SYNTHETIC leaderboard rows in the page-row shape that
// web_app/screen-qgv-live.js helpers.sortRows reads (id, ticker, score.{total,q,g,v}, rank.{official,qg_reference_order},
// acquired_at) plus the display fields the trial page draws. Every value is made up by a seeded generator: ids are
// 'SYNTHETIC:S00001', tickers 'SYN00001', names '합성기업 00001', industries '합성 업종 A..E'. Nothing here is a real company,
// score or price. Ranks are assigned HERE, once, by the generator (it plays the engine): the table under test must show them
// unchanged under any sort or filter.
const GROUPS = Object.freeze([['synthetic_a', '합성 업종 A'], ['synthetic_b', '합성 업종 B'], ['synthetic_c', '합성 업종 C'], ['synthetic_d', '합성 업종 D'], ['synthetic_e', '합성 업종 E']]);
const TYPES = Object.freeze(['합성 유형 1', '합성 유형 2', '합성 유형 3']);
const pad = (n, w = 5) => String(n).padStart(w, '0');

// Mulberry32: a small deterministic generator (same seed, same rows on every run).
function prng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

function rows(n, seed = 504) {
  const rnd = prng(seed + n), one = () => Math.round((5 + rnd() * 90) * 10) / 10, na = (p) => rnd() < p;
  const out = [];
  for (let i = 1; i <= n; i++) {
    const q = na(0.08) ? null : one(), g = na(0.08) ? null : one(), v = na(0.12) ? null : one();
    const [industry, industry_label] = GROUPS[Math.floor(rnd() * GROUPS.length)];
    const total = q !== null && g !== null && v !== null ? Math.round(((q + g + v) / 3) * 10) / 10 : q !== null && g !== null ? Math.round(((q + g) / 2) * 10) / 10 : null;
    const day = 1 + Math.floor(rnd() * 28);
    out.push({
      id: 'SYNTHETIC:S' + pad(i), ticker: 'SYN' + pad(i), title: '합성기업 ' + pad(i), industry, industry_label,
      sic: '99' + pad(Math.floor(rnd() * 100), 2), types_text: TYPES[Math.floor(rnd() * TYPES.length)],
      acquired_at: '2026-10-' + pad(day, 2) + 'T00:00:00Z', score: { total, q, g, v },
      na_reason: { total: total === null ? '합성 NA · 축 부족' : null, q: q === null ? '합성 NA · Q 없음' : null, g: g === null ? '합성 NA · G 없음' : null, v: v === null ? '합성 NA · V 없음' : null, rank: null },
      rank: { official: null, qg_reference_order: null },
    });
  }
  // The "engine": rows with Q, G and V are ranked by total (ties by ticker); rows with Q and G only get a QG reference order.
  const byTotal = (a, b) => b.score.total - a.score.total || a.ticker.localeCompare(b.ticker);
  out.filter((r) => r.score.v !== null && r.score.total !== null).sort(byTotal).forEach((r, k) => { r.rank.official = k + 1; });
  out.filter((r) => r.score.v === null && r.score.total !== null).sort(byTotal).forEach((r, k) => { r.rank.qg_reference_order = k + 1; });
  for (const r of out) { r.rank_text = rankText(r); if (r.rank_text === '—') r.na_reason.rank = '합성 NA · 순위 없음'; }
  // Input order is shuffled so neither table gets a pre-sorted list for free.
  for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; }
  return out;
}
// The rank text exactly as screen-qgv-live.js rankCell draws it (official view): the rank, '참고 n', or '—'.
function rankText(r) { return Number.isInteger(r.rank.official) ? String(r.rank.official) : r.rank.qg_reference_order !== null ? '참고 ' + r.rank.qg_reference_order : '—'; }

module.exports = Object.freeze({ GROUPS, rows, rankText });
