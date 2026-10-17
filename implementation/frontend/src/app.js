// Investment System frontend v2 (read-only). Routes: #/ (오늘), #/qgv (리더보드), #/qgv/target, #/qgv/market,
// #/company/<key>, #/technical, #/macro, #/validation, #/settings. Public price-free data only; no storage, no orders.
import { loadAll } from './data.js';
import * as M from './model.js';
import { esc } from './format.js';
import { today } from './screens/today.js';
import { qgv, bindQgv } from './screens/qgv.js';
import { company } from './screens/company.js';
import { macroScreen } from './screens/macro.js';
import { technical } from './screens/technical.js';
import { validation } from './screens/validation.js';
import { settings, bindSettings } from './screens/settings.js';

const g = globalThis;
const main = document.getElementById('content');
const state = { data: null, scores: null, list: [], cov: null, macro: null, preset: null, gate: null, ui: { scope: 'all', query: '', sort: 'total', page: 0, onlyScored: false } };

// Scores come only from the cockpit engine (QgvScores.compute; no device quotes on this page, so V stays NOT_AVAILABLE).
function score() {
  const d = state.data;
  const inputs = d.screens[g.Qgv2Inputs ? g.Qgv2Inputs.FILE : 'sec-qgv2.json'] || null;
  const identities = M.identitiesFor(inputs, d.identities);
  let referenceRows = {};
  try {
    const row = d.screens['dart-financials.json'] && inputs && g.DartDisclosures ? g.DartDisclosures.qgv2Reference(d.screens['dart-financials.json'], inputs.records) : null;
    if (row) referenceRows = { hanmi: row };
  } catch (_) {
    referenceRows = {};
  }
  let S = null;
  try {
    S = g.QgvScores ? g.QgvScores.compute({ identities, publicScreens: d.screens, quotes: {}, preset: state.preset || undefined, gate: state.gate, referenceRows }) : null;
  } catch (_) {
    S = null;
  }
  state.scores = S;
  state.inputs = inputs;
  state.list = M.rows(S, identities, { QS: g.QgvScores, inputs, targets: M.targetInfo(d.catalog), windows: d.screens['sec-filing-windows.json'] || null, PS: g.PublicScreens });
  state.cov = M.coverage(inputs);
  state.macro = M.macro(g.MacroLights, d.screens);
}

function route() {
  const raw = decodeURIComponent((location.hash || '#/').replace(/^#\/?/, ''));
  const [head, ...rest] = raw.split('/');
  return { head: head || 'today', rest };
}

const TAB = { today: 'today', qgv: 'qgv', company: 'qgv', technical: 'technical', macro: 'macro', validation: 'validation', settings: 'settings' };

function render() {
  const { head, rest } = route();
  const tab = TAB[head] || 'today';
  for (const a of document.querySelectorAll('[data-tab]')) {
    if (a.dataset.tab === tab) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  }
  if (!state.data) return;
  const ctx = { state, g, M };
  let html;
  switch (head) {
    case 'qgv': html = qgv(ctx, rest[0] || 'find'); break;
    case 'company': html = company(ctx, rest.join('/')); break;
    case 'technical': html = technical(ctx); break;
    case 'macro': html = macroScreen(ctx); break;
    case 'validation': html = validation(ctx); break;
    case 'settings': html = settings(ctx); break;
    default: html = today(ctx);
  }
  main.innerHTML = html;
  for (const el of main.querySelectorAll('[data-w]')) el.style.width = el.dataset.w + '%';
  if (head === 'qgv') bindQgv(main, ctx, () => { score(); render(); }, render);
  if (head === 'settings') bindSettings(main, ctx);
  const title = main.querySelector('h1');
  document.title = (title ? title.textContent + ' · ' : '') + '투자 시스템';
}

let lastHead = null;
window.addEventListener('hashchange', () => {
  const { head } = route();
  render();
  if (head !== lastHead) { window.scrollTo(0, 0); main.focus({ preventScroll: true }); }
  lastHead = head;
});

(async function boot() {
  try {
    state.data = await loadAll(g);
    score();
    lastHead = route().head;
    render();
  } catch (e) {
    main.innerHTML = `<p class="state-screen error-line" role="alert">공개 자료를 불러오지 못했습니다. ${esc(e && e.message ? e.message : '')}</p>`;
  }
})();
