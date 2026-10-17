// S09 매크로: macro lights v1 (PLAYBOOK_V1 13-5, uncalibrated) from macro-screen.json through MacroLights.merge.
// Three lights are public; market and credit need device prices and stay NOT_AVAILABLE on this page.
import { esc, shortDate, isNum } from '../format.js';
import { head, card, chip } from '../ui.js';
import { macroChip } from './today.js';

const pctv = (v, d = 2) => (isNum(v) ? v.toFixed(d) + '%' : '—');
const pp = (v, d = 2) => (isNum(v) ? (v > 0 ? '+' : '') + v.toFixed(d) + '%p' : '—');

function rule(id, cfg) {
  const c = cfg && cfg.lights ? cfg.lights[id] : null;
  if (!c) return '';
  if (id === 'employment') return `켜짐 기준: 실업률 3개월 평균이 12개월 최저보다 ${c.gap_pp_gte}%p 이상 높음`;
  if (id === 'inflation') return `켜짐 기준: CPI 전년비 ${(c.yoy_gt * 100).toFixed(0)}% 초과`;
  if (id === 'curve') return `켜짐 기준: 10년−3개월 금리차 0 미만이 ${c.min_run_days}거래일 이상`;
  if (id === 'market') return `켜짐 기준: S&P 500(SPY) 고점 대비 ${(c.drawdown_lte * 100).toFixed(0)}% 이하 또는 변동성 상위 ${(c.rv_top_share * 100).toFixed(0)}%`;
  if (id === 'credit') return `켜짐 기준: HYG/IEF 비율 ${c.window_sessions}거래일 변화 ${(c.change_lte * 100).toFixed(0)}% 이하`;
  return '';
}

function detail(id, l) {
  if (!l || l.state === 'NOT_AVAILABLE' || l.lit === null || l.lit === undefined) return null;
  if (id === 'employment') return `실업률 3개월 평균 ${pctv(l.avg3)} · 12개월 최저 ${pctv(l.low12)} · 차이 ${pp(l.gap)} · ${l.period || ''}`;
  if (id === 'inflation') return `CPI 전년비 ${isNum(l.yoy) ? (l.yoy * 100).toFixed(1) + '%' : '—'} · ${l.period || ''}`;
  if (id === 'curve') return `10년 ${pctv(l.ten_year)} − 3개월 ${pctv(l.three_month)} = ${pp(l.spread)} · 역전 ${isNum(l.run_days) ? l.run_days : '—'}거래일 · ${l.date || ''}`;
  return null;
}

const MISSING = { DEVICE_NOT_LOADED: '기기 가격 필요 (기존 코크핏 매크로 화면에서 계산)', SOURCE_NOT_COLLECTED: '아직 수집 안 됨', NO_DATA: '자료 없음', SCHEMA_MISMATCH: '자료 형식 오류' };

export function macroScreen(ctx) {
  const { state, M, g } = ctx, m = state.macro, cfg = g.MacroLights ? g.MacroLights.CONFIG : null;
  const screen = state.data.screens['macro-screen.json'];
  const engine = screen && screen.data && screen.data.growth_inflation_v0 ? screen.data.growth_inflation_v0.engine : null;
  const ids = ['employment', 'inflation', 'curve', 'market', 'credit'];
  const lights = ids.map((id) => {
    const l = m && m.lights ? m.lights[id] : null;
    const lit = l ? l.lit : null;
    const d = detail(id, l);
    return `<div class="light" data-light="${id}" data-lit="${lit === true ? 'on' : lit === false ? 'off' : 'na'}">
      <span class="dot ${lit === true ? 'on' : lit === false ? 'off' : ''}" aria-hidden="true"></span>
      <span class="name">${esc(M.LIGHT_NAME[id])}</span>
      <span>${lit === true ? chip('켜짐', 'risk') : lit === false ? chip('꺼짐', 'ok') : chip('자료 없음', 'na')}</span>
      <span class="detail">${esc(d || MISSING[l && l.reason] || '자료 없음')}</span>
      <span class="detail">${esc(rule(id, cfg))}</span>
      ${l && l.source ? `<span class="detail small">출처 ${esc(l.source)}</span>` : ''}
    </div>`;
  }).join('');
  return head({ flow: '3', eyebrow: 'MACRO', title: '매크로', lede: '경고등 v1 · 보정 전 · 시장 국면 참고이며 주문·매매 지시가 아닙니다.' })
    + card('상태', `<div class="row" data-macro-state>${macroChip(m, M)}<span class="small">${m && m.available_count ? `켜짐 ${m.lit_count} / 확인 가능 ${m.available_count} / 전체 5` : '공개 경고등 자료가 없습니다.'}</span></div>
      ${m && m.as_of ? `<p class="note">기준 ${esc(shortDate(m.as_of) || '')}</p>` : ''}
      ${m && m.low_confidence && m.available_count ? '<p class="small">확인 가능한 경고등이 3개 미만이라 판정 신뢰도가 낮습니다.</p>' : ''}`, 'data-card="macro-state"')
    + card('경고등 5개', `<div class="lights">${lights}</div>`, 'data-card="lights"')
    + card('판정 규칙 (잠정·보정 전)', `<ul class="list small">
        <li>경고: 켜진 경고등 ${cfg ? cfg.state.warning_lit_count : 2}개, 또는 물가 ${cfg ? (cfg.state.warning_inflation_gt * 100).toFixed(0) : 5}% 초과이면서 성장 0 미만</li>
        <li>비상: 켜진 경고등 ${cfg ? cfg.state.crisis_lit_count : 3}개 이상, 주식시장·신용 동시 켜짐, 또는 물가 ${cfg ? (cfg.state.crisis_inflation_gt * 100).toFixed(0) : 8}% 초과</li>
        <li>확인 가능한 경고등이 ${cfg ? cfg.state.low_confidence_available_lt : 3}개 미만이면 신뢰도 낮음</li></ul>`, 'data-card="macro-rules"')
    + (engine ? card('기존 매크로 엔진', `<dl class="kv"><dt>엔진</dt><dd>v${esc(String(engine.version || '').replace(/^v/, ''))}</dd><dt>상태</dt><dd>${esc(engine.state === 'NOT_AVAILABLE' ? '자료 없음' : ({ NORMAL: '정상', WARNING: '경고', EMERGENCY: '비상' }[engine.state] || '확인 불가'))}</dd></dl>`, 'data-card="macro-engine"') : '');
}
