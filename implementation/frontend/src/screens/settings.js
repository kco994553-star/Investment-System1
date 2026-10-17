// S11 설정: data sources, what this page does not do, and the raw public record of one company (collapsed by default,
// developer use). Nothing is stored: the chosen company lives only in memory.
import { esc, shortTime } from '../format.js';
import { head, card, chip } from '../ui.js';

let rawKey = null;

function sources(ctx) {
  const { state, g } = ctx, d = state.data, s = d.screens;
  const env = (p) => (p ? { state: p.state || 'LIVE', as_of: p.as_of || null } : null);
  return [
    ['QGV v2 (Q·G)', 'sec-qgv2.json', state.inputs ? { state: 'LIVE', as_of: state.inputs.as_of } : null],
    ['매크로 경고등', 'macro-screen.json', env(s['macro-screen.json'])],
    ['실적 예상 시기', 'sec-filing-windows.json', env(s['sec-filing-windows.json'])],
    ['투자 유형', 'company-types-pricefree.json', env(s['company-types-pricefree.json'])],
    ['산업·테마 분류', 'company-classification.json', env(g.ClassificationScreens ? s[g.ClassificationScreens.FILE] : null)],
    ['SEC 공시', 'sec-disclosures.json', env(d.disclosures)],
    ['뉴스', 'news-signals.json', env(d.news)],
    ['DART 공시', 'dart-disclosures.json', env(d.dart)],
    ['전진검증 원장', 'forward-validation-ledger.json', d.ledger && d.ledger.state === 'LOADED' ? { state: d.ledger.ledger.status, as_of: d.ledger.ledger.as_of } : null],
    ['TARGET 카탈로그', 'actual-catalog.json', d.catalog ? { state: 'LIVE', as_of: null } : null],
  ];
}

const STATE = { LIVE: ['실데이터', 'ok'], STALE: ['오래됨', 'warn'], NOT_AVAILABLE: ['자료 없음', 'na'], NOT_STARTED: ['시작 전', 'na'], ACTIVE: ['기록 중', 'ok'] };

export function settings(ctx) {
  const { state } = ctx;
  const list = state.list;
  if (!rawKey || !list.some((r) => r.key === rawKey)) rawKey = (list.find((r) => r.isTarget) || list[0] || {}).key || null;
  return head({ eyebrow: 'SETTINGS', title: '설정', lede: '읽기 전용 · 이 화면은 아무것도 저장하거나 전송하지 않습니다.' })
    + card('데이터 출처', `<div class="table-wrap"><table data-sources><thead><tr><th>자료</th><th>상태</th><th>기준 시각</th></tr></thead><tbody>
      ${sources(ctx).map(([label, file, x]) => { const [t, tone] = x ? STATE[x.state] || ['확인 불가', 'na'] : ['읽지 못함', 'na']; return `<tr data-source="${esc(file)}"><td>${esc(label)}</td><td>${chip(t, tone)}</td><td class="small">${esc(x && x.as_of ? shortTime(x.as_of) || '—' : '—')}</td></tr>`; }).join('')}
      </tbody></table></div><p class="note">공개 자료는 GitHub Actions가 매일 만들고, 각 파일은 기존 코크핏과 같은 검증기로 읽습니다. 검증에 실패한 파일은 '읽지 못함'으로 보입니다.</p>`, 'data-card="sources"')
    + card('이 화면의 범위', `<ul class="list small">
        <li>공개 자료만 읽습니다. 가격·보유·계좌·시트 설정은 읽지 않습니다.</li>
        <li>점수는 기존 엔진(QGV v2)을 그대로 씁니다. 새 계산 방법을 만들지 않습니다.</li>
        <li>가격이 없어 V(가치)는 계산하지 않습니다. 결측은 0으로 채우지 않습니다.</li>
        <li>매수·매도·주문 기능이 없습니다.</li></ul>
        <p class="row"><a href="../">기존 코크핏 열기 →</a></p>`, 'data-card="scope"')
    + `<details class="raw card" data-raw><summary>원자료 보기 (개발자용)</summary>
        <p class="small">공개 sec-qgv2.json의 해당 기업 행(읽기 도구가 정리한 형태)입니다. 화면에는 결과만 보입니다.</p>
        <label for="raw-company" class="small">기업</label>
        <select class="select" id="raw-company" data-raw-company>${list.map((r) => `<option value="${esc(r.key)}"${r.key === rawKey ? ' selected' : ''}>${esc(r.ticker + (r.name && r.name !== r.ticker ? ' · ' + r.name : ''))}</option>`).join('')}</select>
        <pre class="raw" data-raw-json>${esc(rawJson(ctx, rawKey))}</pre>
      </details>`;
}

function rawJson(ctx, key) {
  const { state } = ctx, r = state.list.find((x) => x.key === key);
  if (!r || !state.inputs || !r.code || !state.inputs.records[r.code]) return '자료 없음';
  return JSON.stringify(state.inputs.records[r.code], (k, v) => (typeof v === 'number' ? Math.round(v * 1000) / 1000 : v), 2);
}

export function bindSettings(root, ctx) {
  const select = root.querySelector('[data-raw-company]'), pre = root.querySelector('[data-raw-json]');
  if (select && pre) select.addEventListener('change', () => { rawKey = select.value; pre.textContent = rawJson(ctx, rawKey); });
}
