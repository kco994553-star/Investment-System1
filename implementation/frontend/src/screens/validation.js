// S10 검증·연구: the forward-validation ledger (public, price-free Q·G records of TARGET v0). Past records are never
// rewritten. Virtual trading and daily reports are device-only and stay in the existing cockpit.
import { esc, score } from '../format.js';
import { head, card, chip } from '../ui.js';

const EVAL = { PRIMARY: ['본 기록', 'ok'], PREPARATORY: ['준비 기록', 'warn'], LEGACY: ['이전 형식', 'na'], NOT_AVAILABLE: ['기록 없음', 'na'] };
const EVAL_REASON = {
  RECORD_NOT_AVAILABLE: '그날 기록 없음', Q_BELOW_454: 'Q 산출 454종목 미만', G_BELOW_454: 'G 산출 454종목 미만', CALC_VERSION_MISSING: '계산 버전 없음',
  CALC_VERSION_MIXED: '계산 버전 섞임', ROW_DATA_STALE: '오래된 행 포함', POPULATION_MISMATCH: '모집단 불일치', BASIS_NOT_COMPUTED: '기준 미계산',
};

export function validation(ctx) {
  const { state, g } = ctx, FV = g.ForwardValidation, res = state.data.ledger;
  const head0 = head({ flow: '4', eyebrow: 'VALIDATION', title: '검증·연구', lede: '전진검증: 매일 동결한 Q·G 기록과 이후 결과 · 과거 기록은 다시 쓰지 않음' });
  if (!res || res.state !== 'LOADED') {
    const why = res && res.reason === 'LEDGER_NOT_PUBLISHED' ? '원장 파일이 아직 게시되지 않았습니다.' : '원장을 읽지 못했습니다.';
    return head0 + card('전진검증 원장', `<div class="row">${chip('확인 불가', 'na')}</div><p class="small">${esc(why)}</p>`, 'data-card="ledger"') + links();
  }
  const L = res.ledger;
  const v2 = (L.versions && FV ? L.versions[FV.V2_VERSION] : null) || [];
  const v1 = (L.versions && FV ? L.versions[FV.VERSION] : null) || [];
  const rows = v2.slice().sort((a, b) => (a.date < b.date ? 1 : -1));
  const status = L.status === 'ACTIVE' ? chip('기록 중', 'ok') : chip('시작 전', 'na');
  const table = rows.length ? `<div class="table-wrap"><table data-ledger-table><thead><tr><th>날짜</th><th>구분</th><th class="num">Q 산출</th><th class="num">Q 가중평균</th><th class="num">G 산출</th><th class="num">G 가중평균</th></tr></thead><tbody>
      ${rows.map((r) => {
        const s = FV.qgSummary(r), ev = FV.rowEvaluation(r), [label, tone] = EVAL[ev.status] || EVAL.NOT_AVAILABLE;
        const why = ev.reasons.map((c) => EVAL_REASON[c] || '자료 부족').join(' · ');
        return `<tr data-ledger-day="${esc(r.date)}"><td>${esc(r.date)}</td><td>${chip(label, tone)}${why ? `<div class="small">${esc(why)}</div>` : ''}</td>
          <td class="num">${s.state === 'RECORDED' ? esc(s.Q.available + '/' + s.companies) : '—'}</td><td class="num">${s.state === 'RECORDED' ? esc(score(s.Q.weighted_mean) || '—') : '—'}</td>
          <td class="num">${s.state === 'RECORDED' ? esc(s.G.available + '/' + s.companies) : '—'}</td><td class="num">${s.state === 'RECORDED' ? esc(score(s.G.weighted_mean) || '—') : '—'}</td></tr>`;
      }).join('')}</tbody></table></div>`
    : `<p class="empty" data-ledger-empty>${L.status === 'NOT_STARTED' ? `시작일(${esc(L.start_date)}) 전이라 기록이 없습니다.` : '아직 기록된 미국 거래일이 없습니다.'}</p>`;
  return head0
    + card('전진검증 원장', `<div class="row">${status}${chip('보정 전', 'outline')}${chip('Holdout 미확정·사용 안 함', 'outline')}</div>
      <dl class="kv spaced" data-ledger-facts><dt>시작일</dt><dd>${esc(L.start_date)}</dd><dt>대상</dt><dd>TARGET ${esc(L.target ? L.target.version : 'v0')} · 19종목</dd>
      <dt>v2 기록</dt><dd>${v2.length}건</dd><dt>v1 비교 기록</dt><dd>${v1.length}건</dd><dt>V(가치)</dt><dd>가격 필요 · 기록하지 않음</dd></dl>`, 'data-card="ledger"')
    + card('일별 Q·G 기록 (v2)', table + '<p class="note">본 기록은 Q·G가 각각 454종목 이상 같은 계산 버전으로 산출된 날입니다. v1 행은 비교를 위해 원장에만 남고 화면 점수에는 쓰지 않습니다.</p>', 'data-card="ledger-days"')
    + links();
}

function links() {
  return card('기기 전용 기록', '<p class="small">가상매매 장부·일일보고서·백테스트는 이 기기의 가격과 보유가 필요해 기존 코크핏에 있습니다.</p><p class="row"><a href="../#validation">검증 화면 →</a><a href="../#report/mock">모의투자 일일보고서 →</a></p>', 'data-card="device-links"');
}
