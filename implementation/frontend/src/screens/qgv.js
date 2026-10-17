// QGV: 종목 찾기 (S06 leaderboard), TARGET (S03 target side only) and 공시·뉴스 (S07 news side). QGV v2 only.
import { esc, pct } from '../format.js';
import { head, card, chip, subnav, bar } from '../ui.js';
import { scoreCell, companyCell, nextEarnings, basisBadges, feed, feedList } from './common.js';

const PAGE = 50;
const SORTS = [['total', 'QGV 높은 순'], ['q', 'Q 높은 순'], ['g', 'G 높은 순'], ['ticker', '티커 순']];

function nav(current) {
  return subnav([['#/qgv', '종목 찾기', 'find'], ['#/qgv/target', 'TARGET 구성', 'target'], ['#/qgv/market', '공시·뉴스', 'market']], current);
}

export function qgv(ctx, sub) {
  if (sub === 'target') return targetView(ctx);
  if (sub === 'market') return marketView(ctx);
  return findView(ctx);
}

function findView(ctx) {
  const { state, g } = ctx, S = state.scores, ui = state.ui;
  const presets = g.QgvScores ? g.QgvScores.presets() : {};
  const profile = S ? S.profile : null;
  return head({ flow: '1', eyebrow: 'QGV · 종목 찾기', title: '리더보드', lede: '미국 상위 504종목과 TARGET 19종목 · QGV v2(잠정) · 순서는 이 화면의 정렬이며 공식 순위가 아닙니다.' })
    + nav('find') + basisBadges(ctx)
    + `<section class="card" data-leaderboard>
      <div class="toolbar">
        <div class="seg" role="group" aria-label="QGV 프로필" data-presets>${Object.entries(presets).map(([id, p]) => `<button type="button" data-preset="${esc(id)}" aria-pressed="${profile && profile.preset === id}">${esc(p.name.replace(/\s*\(.*\)$/, ''))}</button>`).join('')}</div>
        <label class="toggle"><input type="checkbox" data-gate${!profile || profile.gate ? ' checked' : ''}> 가치 함정 관문</label>
      </div>
      <div class="toolbar">
        <label class="visually-hidden" for="lb-search">티커·이름 검색</label>
        <input class="search" id="lb-search" type="search" maxlength="40" autocomplete="off" placeholder="티커·이름 검색 (예: NVDA)" value="${esc(ui.query)}" data-search>
        <label class="visually-hidden" for="lb-scope">범위</label>
        <select class="select" id="lb-scope" data-scope><option value="all"${ui.scope === 'all' ? ' selected' : ''}>전체</option><option value="target"${ui.scope === 'target' ? ' selected' : ''}>TARGET 19</option></select>
        <label class="visually-hidden" for="lb-sort">정렬</label>
        <select class="select" id="lb-sort" data-sort>${SORTS.map(([id, label]) => `<option value="${id}"${ui.sort === id ? ' selected' : ''}>${esc(label)}</option>`).join('')}</select>
        <label class="toggle"><input type="checkbox" data-only-scored${ui.onlyScored ? ' checked' : ''}> 점수 있는 종목만</label>
      </div>
      <div id="lb-table">${tableHtml(ctx)}</div>
      <p class="note">— = 값 없음(0이 아님). 공개 자료에는 가격이 없어 V(가치)는 계산하지 않고, QGV는 Q·G만으로 계산합니다(엔진 규칙: 반영 비중 50% 이상일 때만 합계). 계산 규칙 버전이 다른 행은 순위에서 뺍니다.</p>
    </section>`;
}

export function tableHtml(ctx) {
  const { state, M } = ctx, ui = state.ui;
  const rows = M.view(state.list, { scope: ui.scope, query: ui.query, sort: ui.sort, dir: -1, onlyScored: ui.onlyScored });
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  ui.page = Math.min(ui.page, pages - 1);
  const shown = rows.slice(ui.page * PAGE, ui.page * PAGE + PAGE);
  const ready = rows.filter((r) => r.state === 'READY').length;
  if (!state.list.length) return '<p class="empty">공개 QGV v2 자료가 아직 없습니다.</p>';
  return `<p class="small" data-count>${rows.length}개 · QGV 점수 있음 ${ready}개</p>
    <div class="table-wrap"><table data-leaderboard-table><thead><tr><th class="num">#</th><th>기업</th><th class="num">QGV</th><th class="num">Q</th><th class="num">G</th><th>다음 실적</th></tr></thead><tbody>
    ${shown.map((r, i) => `<tr data-row="${esc(r.key)}" data-state="${r.state}"><td class="num">${esc(String(ui.page * PAGE + i + 1))}</td><td>${companyCell(r)}</td>
      <td class="num">${r.state === 'READY' || r.state === 'PARTIAL' ? scoreCell(r.total) + (r.flags.length ? `<div>${r.flags.map((f) => chip(f, 'warn')).join(' ')}</div>` : '') : `<span class="na">—</span> <details class="why"><summary>사유</summary><span data-reason>${esc(r.reason || '')}</span></details>`}</td>
      <td class="num">${scoreCell(r.q)}</td><td class="num">${scoreCell(r.g)}</td><td class="small">${esc(r.isTarget ? nextEarnings(r.next) || '—' : '—')}</td></tr>`).join('')}
    </tbody></table></div>
    ${pages > 1 ? `<div class="pager"><button type="button" data-page="-1"${ui.page === 0 ? ' disabled' : ''}>이전</button><span>${ui.page + 1} / ${pages}</span><button type="button" data-page="1"${ui.page >= pages - 1 ? ' disabled' : ''}>다음</button></div>` : ''}`;
}

export function bindQgv(root, ctx, rescore, rerender) {
  const { state } = ctx, ui = state.ui, table = root.querySelector('#lb-table');
  const refresh = () => {
    if (!table) return;
    table.innerHTML = tableHtml(ctx);
    bindPager();
  };
  function bindPager() {
    for (const b of root.querySelectorAll('[data-page]')) b.addEventListener('click', () => { ui.page += Number(b.dataset.page); refresh(); table.scrollIntoView({ block: 'start' }); });
  }
  for (const b of root.querySelectorAll('[data-preset]')) b.addEventListener('click', () => { state.preset = b.dataset.preset; rescore(); });
  const gate = root.querySelector('[data-gate]');
  if (gate) gate.addEventListener('change', () => { state.gate = gate.checked; rescore(); });
  const search = root.querySelector('[data-search]');
  let timer = null;
  if (search) search.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => { ui.query = search.value; ui.page = 0; refresh(); }, 120); });
  const scope = root.querySelector('[data-scope]');
  if (scope) scope.addEventListener('change', () => { ui.scope = scope.value; ui.page = 0; refresh(); });
  const sort = root.querySelector('[data-sort]');
  if (sort) sort.addEventListener('change', () => { ui.sort = sort.value; ui.page = 0; refresh(); });
  const only = root.querySelector('[data-only-scored]');
  if (only) only.addEventListener('change', () => { ui.onlyScored = only.checked; ui.page = 0; refresh(); });
  bindPager();
  void rerender;
}

function targetView(ctx) {
  const { state, M } = ctx, d = state.data, themes = M.themeTargets(d.catalog);
  const byTicker = Object.fromEntries(state.list.filter((r) => r.isTarget).map((r) => [r.ticker, r]));
  const body = themes.length ? themes.map((t) => `<section class="card" data-theme="${esc(t.id)}"><h2>${esc(t.label)} <span class="small">목표 ${esc(pct(t.weight))}</span></h2>${bar(t.weight * 100)}
      <ul class="list spaced">${t.members.map((m) => { const r = byTicker[m.ticker]; return `<li class="row">${r ? companyCell(r) : esc(m.ticker)} <span class="small">${esc(m.label)}</span> <span class="spacer"></span><span class="small">목표 ${esc(pct(m.weight))} · QGV ${r ? scoreCell(r.total) : '—'}</span></li>`; }).join('')}</ul></section>`).join('')
    : '<p class="empty">TARGET 카탈로그를 읽지 못했습니다.</p>';
  return head({ flow: '1', eyebrow: 'QGV · 내 투자', title: 'TARGET 구성', lede: `목표 비중 ${d.catalog ? d.catalog.target_root_version : ''} · 실제 보유(ACTUAL)와 다른 축입니다.` })
    + nav('target')
    + `<div class="grid two">${body}</div>`
    + card('실제 보유 (ACTUAL)', '<p class="small">보유·평가액은 이 기기에만 저장되는 개인 자료라 이 화면에서 읽지 않습니다. 목표로 실제를 대신 채우지 않습니다.</p><p><a href="../#portfolio">기존 코크핏의 포트폴리오 화면 열기 →</a></p>', 'data-card="actual"');
}

function marketView(ctx) {
  const items = feed(ctx, { limit: 40, sinceDays: 30 });
  return head({ flow: '1', eyebrow: 'QGV · 시장 정보', title: '공시·뉴스', lede: 'TARGET 기업의 최근 30일 SEC·DART 공시와 뉴스 · 정보 제공용, 점수에 반영하지 않음' })
    + nav('market')
    + card('최근 30일', feedList(items, '최근 30일 공시·뉴스가 없습니다.'), 'data-card="market-feed"');
}
