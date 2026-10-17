// View model: turns the cockpit engines' results into rows for the screens. Pure functions (engines are passed in), so
// node tests can drive them with the same UMD modules the page loads. No methodology lives here: Q, G, V, total, rank,
// flags and NOT_AVAILABLE reasons all come from QgvScores (QGV v2 only; v1 is never shown).
import { isNum } from './format.js';

export const FACTOR_LABEL = {
  q_profitability: '수익성', q_moat_proxy: '해자 대리', q_earnings_quality: '이익의 질', q_financial_safety: '재무 안전',
  q_capital_allocation: '자본 배분 (경영진 대리)', g_revenue_growth: '매출 성장', g_per_share_growth: '주당 이익·FCF 성장',
  g_growth_efficiency: '성장 효율', g_consistency: '성장 일관성', g_recent_acceleration: '최근 가속',
  v_earnings_yield: '이익 수익률 (EBIT/EV)', v_fcf_yield: 'FCF 수익률 (FCF/EV)', v_vs_industry: '업종 대비',
  v_vs_own_history: '자기 과거 대비 (5년)', v_expectation_check: '기대 점검 (역DCF − 실현 성장)',
};

// Factor-level reasons in words; an unknown code reads '자료 부족' (the code stays in data-reason).
const REASON = {
  SEC_FACTOR_NOT_AVAILABLE: 'SEC 재무로 계산할 수 없음', NO_DEVICE_PRICE: '가격 필요 (공개 자료에는 가격 없음)',
  PRICE_HISTORY_NOT_AVAILABLE: '월말 가격 이력 필요', HISTORY_TOO_SHORT: '비교할 과거 기간이 짧음',
  NORMALIZED_HISTORY_NOT_AVAILABLE: '경기민감 기업이라 과거 비교 보류', NORMALIZED_EARNINGS_NOT_AVAILABLE: '정상화 이익 자료 부족',
  EBIT_NOT_AVAILABLE: '영업이익 자료 없음', FCF_NOT_AVAILABLE: '잉여현금흐름 자료 없음', SHARES_NOT_AVAILABLE: '주식 수 자료 없음',
  DEBT_CASH_NOT_AVAILABLE: '부채·현금 자료 없음', EV_NON_POSITIVE: '기업가치가 0 이하', CROSS_SECTION_TOO_SMALL: '비교할 종목 수 부족',
  REALIZED_GROWTH_NOT_AVAILABLE: '실현 성장률 자료 없음', FINANCIAL_PROFILE_V_NOT_DEFINED: '금융업 가치 계산 방식 미정',
  V_INPUTS_NOT_AVAILABLE: '가치 입력 자료 없음', CURRENCY_BASIS_UNCONFIRMED: '가격과 재무 통화가 다름',
};
export const reasonText = (code) => (code && Object.hasOwn(REASON, code) ? REASON[code] : '자료 부족');

const symbol = (t) => String(t || '').replaceAll('.', '-').toUpperCase();
export const symbolOfCode = (code) => symbol(String(code).slice(String(code).indexOf(':') + 1));

// TARGET identities (from the catalog) plus every Universe code that is not a TARGET ticker: one row per company.
export function identitiesFor(inputs, targets = []) {
  const taken = new Set(targets.map((t) => symbol(t.ticker)));
  const out = targets.map((t) => ({ company_id: t.company_id, ticker: t.ticker, name: t.name, target: true }));
  if (inputs && inputs.records) {
    for (const code of Object.keys(inputs.records)) {
      if (code.startsWith('TARGET:')) continue;
      const s = symbolOfCode(code);
      if (taken.has(s)) continue;
      taken.add(s);
      out.push({ company_id: code, ticker: s, name: null, target: false });
    }
  }
  return out;
}

// Targets from the public catalog: theme and target weight (TARGET v0, never ACTUAL).
export function targetInfo(catalog) {
  const out = {};
  if (!catalog || !Array.isArray(catalog.instruments)) return out;
  const total = catalog.total_units || 10000;
  const themes = Object.fromEntries((catalog.themes || []).map((t) => [t.theme_id, t]));
  for (const i of catalog.instruments) {
    out[symbol(i.ticker)] = { weight: i.target_units / total, theme: themes[i.theme_id] ? themes[i.theme_id].label : null, themeId: i.theme_id, label: i.label, currency: i.currency };
  }
  return out;
}

export function themeTargets(catalog) {
  if (!catalog || !Array.isArray(catalog.themes)) return [];
  const total = catalog.total_units || 10000;
  return catalog.themes.map((t) => ({
    id: t.theme_id, label: t.label, weight: t.target_units / total,
    members: (catalog.instruments || []).filter((i) => i.theme_id === t.theme_id).map((i) => ({ ticker: i.ticker, label: i.label, weight: i.target_units / total })),
  }));
}

// One display row per identity. state: READY (total), PARTIAL (Q or G but no total), MISMATCH (other calc_version),
// NOT_AVAILABLE. The reason text is QgvScores.naText (never a v1 fallback).
export function rows(S, identities, { QS, inputs = null, targets = {}, windows = null, PS = null, now = new Date() } = {}) {
  const list = [];
  for (const id of identities) {
    const r = S && S.rows ? S.rows[id.company_id] : null;
    const p = r ? r.primary : null;
    const src = inputs && r && r.code ? inputs.records[r.code] : null;
    const mismatch = !!(p && (p.flags || []).includes('CALC_VERSION_MISMATCH'));
    const hasQG = !!p && (isNum(p.q) || isNum(p.g));
    const state = mismatch ? 'MISMATCH' : p && isNum(p.total) ? 'READY' : hasQG ? 'PARTIAL' : 'NOT_AVAILABLE';
    const t = targets[symbol(id.ticker)] || null;
    let next = null;
    if (windows && PS && id.target) {
      const rec = windows.data && windows.data.companies ? windows.data.companies[id.company_id] : null;
      if (rec && rec.state !== 'NOT_AVAILABLE') {
        try {
          next = nextWindow(PS, rec, now);
        } catch (_) {
          next = null;
        }
      }
    }
    list.push({
      key: id.company_id, id: id.target ? id.company_id : null, ticker: id.ticker, name: id.name || (t && t.label) || null,
      isTarget: !!id.target, target: t, code: r ? r.code : null,
      q: p && !mismatch ? p.q : null, g: p && !mismatch ? p.g : null, v: p && !mismatch ? p.v : null,
      total: p && !mismatch ? p.total : null, rank: r ? r.rank : null, state,
      reason: state === 'READY' || state === 'PARTIAL' ? null : QS && p ? QS.naText(p, false) : 'QGV v2 산출 불가 · 공개 v2 자료 없음',
      // V needs prices and is never computed on this page: its flag would sit on every row.
      flags: QS && p && !mismatch ? QS.flagText((p.flags || []).filter((f) => f !== 'V_NOT_AVAILABLE'), false, p) : [],
      factorsAvailable: p ? p.factors_available : 0, factorsTotal: p ? p.factors_total : 15,
      reference: !!(p && p.reference_only), sic: src ? src.sic : null, industryGroup: src ? src.industry_group : null,
      next, primary: p,
    });
  }
  return list;
}

/* The next estimated filing window, as the cockpit's S04 line computes it (company-screen.js nextEarningsLine): the current
   window while it is estimated; after a confirmed release (8-K Item 2.02) the following window, searched from 45 days after
   the release. Returns {status:'ESTIMATED', window:{start, end, form, days_until_start}} or null. Never a confirmed date. */
export function nextWindow(PS, rec, now = new Date()) {
  const s = PS.earningsStatus(rec, now);
  if (s && s.status === 'ESTIMATED') return s;
  if (!s || s.status !== 'CONFIRMED') return null;
  const day = (d) => Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const after = new Date(Date.parse(s.date + 'T00:00:00Z') + 45 * 864e5), base = after > now ? after : now, n = PS.nextFilingWindow(rec, base);
  return n ? { status: 'ESTIMATED', window: { ...n, days_until_start: n.days_until_start + Math.round((day(base) - day(now)) / 864e5) }, after_confirmed: s.date } : null;
}

const cmp = (a, b, key, dir) => {
  const x = a[key], y = b[key];
  const mx = !isNum(x), my = !isNum(y);
  if (mx || my) return mx === my ? 0 : mx ? 1 : -1; // missing is always last
  return (x - y) * dir;
};

// Filter + sort for the leaderboard. sort: total | q | g (dir -1 high first) | ticker (A→Z). Missing values sort last.
export function view(list, { scope = 'all', query = '', sort = 'total', dir = -1, onlyScored = false } = {}) {
  const q = String(query || '').trim().toUpperCase();
  let out = list.filter((r) => (scope === 'target' ? r.isTarget : true));
  if (onlyScored) out = out.filter((r) => r.state === 'READY' || r.state === 'PARTIAL');
  if (q) out = out.filter((r) => r.ticker.toUpperCase().includes(q) || (r.name || '').toUpperCase().includes(q) || (r.id || '').toUpperCase().includes(q));
  const tick = (a, b) => (a.ticker < b.ticker ? -1 : a.ticker > b.ticker ? 1 : 0);
  return out.slice().sort((a, b) => (sort === 'ticker' ? tick(a, b) : cmp(a, b, sort, dir) || tick(a, b)));
}

// Coverage of the published Universe (504 codes, TARGET rows excluded): what the daily run actually scored.
export function coverage(inputs) {
  const out = { codes: 0, q: 0, g: 0, both: 0, mismatch: 0, missing: 0, calcVersion: inputs ? inputs.calc_version : null, asOf: inputs ? inputs.as_of : null };
  if (!inputs || !inputs.records) return out;
  for (const [code, r] of Object.entries(inputs.records)) {
    if (code.startsWith('TARGET:')) continue;
    out.codes += 1;
    if (r.calc_version_mismatch === true) { out.mismatch += 1; continue; }
    const q = r.qg_axes && isNum(r.qg_axes.Q && r.qg_axes.Q.score), g = r.qg_axes && isNum(r.qg_axes.G && r.qg_axes.G.score);
    if (q) out.q += 1;
    if (g) out.g += 1;
    if (q && g) out.both += 1;
    if (!q && !g) out.missing += 1;
  }
  return out;
}

// Factor rows of one company for the S05-style breakdown: weight, score or reason, grouped by axis.
export function factorRows(p, weights) {
  if (!weights) return [];
  const out = [];
  for (const axis of ['Q', 'G', 'V']) {
    for (const [f, w] of Object.entries(weights[axis] || {})) {
      const x = p && p.factors ? p.factors[f] : null;
      const ok = !!x && isNum(x.score);
      out.push({ axis, id: f, label: FACTOR_LABEL[f] || f, weight: w, score: ok ? x.score : null, reason: ok ? null : reasonText(x && x.reason), code: ok ? null : (x && x.reason) || null });
    }
  }
  return out;
}

// Upcoming estimated filing windows of TARGET rows within `days` (D-n from PublicScreens.earningsStatus).
export function upcoming(list, days = 14) {
  return list
    .filter((r) => r.next && r.next.status === 'ESTIMATED' && r.next.window && r.next.window.days_until_start <= days)
    .sort((a, b) => a.next.window.days_until_start - b.next.window.days_until_start);
}

// Macro: the merged 5-light state from MacroLights (public lights only on this page: market and credit need prices).
export function macro(ML, screens) {
  if (!ML || !screens || !screens['macro-screen.json']) return null;
  try {
    return ML.merge(screens);
  } catch (_) {
    return null;
  }
}

export const MACRO_STATE = { NORMAL: ['정상', 'ok'], WARNING: ['경고', 'warn'], CRISIS: ['비상', 'risk'] };
export const LIGHT_NAME = { employment: '고용', inflation: '물가', curve: '장단기 금리차', market: '주식시장', credit: '신용' };
