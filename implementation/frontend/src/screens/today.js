// S01 오늘: system flow, what to look at, TARGET v0 and the data basis. Results only; no orders.
import { esc, pct, shortTime, shortDate } from '../format.js';
import { head, card, chip, stat } from '../ui.js';
import { feed, feedList, scoreCell, companyCell, nextEarnings, basisBadges } from './common.js';

export function macroChip(m, M) {
  if (!m || m.available_count === 0) return chip('확인 불가', 'na');
  const [label, tone] = M.MACRO_STATE[m.state] || ['확인 불가', 'na'];
  return chip(label + (m.low_confidence ? ' · 신뢰도 낮음' : ''), tone);
}

export function ledgerChip(ledger) {
  if (!ledger || ledger.state !== 'LOADED') return chip('확인 불가', 'na');
  return ledger.ledger.status === 'ACTIVE' ? chip('기록 중', 'ok') : chip('시작 전', 'na');
}

export function today(ctx) {
  const { state, M } = ctx, cov = state.cov, m = state.macro, d = state.data;
  const targets = state.list.filter((r) => r.isTarget);
  const scoredTargets = targets.filter((r) => r.state === 'READY' || r.state === 'PARTIAL').length;
  const ledger = d.ledger && d.ledger.state === 'LOADED' ? d.ledger.ledger : null;

  const flow = [
    ['1', 'QGV', '#/qgv', cov.both > 0 ? chip('사용 가능', 'ok') : chip('자료 없음', 'na'),
      cov.codes ? `미국 ${cov.codes}종목 중 Q ${cov.q} · G ${cov.g} 산출 · TARGET ${targets.length}개 중 ${scoredTargets}개 점수` : '공개 QGV v2 자료가 아직 없습니다.'],
    ['2', '기술적 분석', '#/technical', chip('준비 중', 'na'), '차트는 착수 조건과 별도 승인 뒤에 엽니다. 공개 자료에는 가격이 없습니다.'],
    ['3', '매크로', '#/macro', macroChip(m, M), m && m.available_count ? `경고등 ${m.lit_count}/${m.available_count}개 켜짐 · 주식시장·신용 2개는 기기 가격 필요` : '공개 경고등 자료가 없습니다.'],
    ['4', '검증·연구', '#/validation', ledgerChip(d.ledger), ledger ? `전진검증 시작일 ${ledger.start_date} · 기록 ${countRecords(ledger)}건` : '전진검증 원장을 읽지 못했습니다.'],
  ];

  const attention = [];
  if (m && m.available_count) {
    for (const [id, l] of Object.entries(m.lights || {})) if (l && l.lit === true) attention.push(`<li>${chip('경고등 켜짐', 'risk')} <b>${esc(M.LIGHT_NAME[id] || id)}</b></li>`);
  }
  for (const r of M.upcoming(targets, 14).slice(0, 6)) {
    attention.push(`<li data-upcoming="${esc(r.key)}">${chip(r.next.window.days_until_start === 0 ? '제출 구간' : 'D-' + r.next.window.days_until_start, 'watch')} ${companyCell(r)} <span class="small">다음 실적 ${esc(nextEarnings(r.next))}</span></li>`);
  }
  const recent = feed(ctx, { limit: 6, sinceDays: 7 });

  const targetRows = targets.slice().sort((a, b) => (b.target ? b.target.weight : 0) - (a.target ? a.target.weight : 0));
  const asOf = shortTime(cov.asOf);
  return head({ eyebrow: 'TODAY', title: '오늘', lede: asOf ? `공개 자료 기준 ${asOf} · 매일 미국 장 마감 뒤 갱신` : '공개 QGV 자료가 아직 없습니다.' })
    + basisBadges(ctx)
    + `<div class="stats spaced" data-today-stats>
        ${stat('Q 산출', cov.codes ? `${cov.q}` : null, cov.codes ? `/${cov.codes} 종목` : '')}
        ${stat('G 산출', cov.codes ? `${cov.g}` : null, cov.codes ? `/${cov.codes} 종목` : '')}
        ${stat('매크로 경고등', m && m.available_count ? `${m.lit_count}/${m.available_count}` : null, '켜짐/확인 가능')}
        ${stat('전진검증', ledger ? (ledger.status === 'ACTIVE' ? '기록 중' : '시작 전') : null, ledger ? '시작 ' + ledger.start_date : '')}
      </div>`
    + card('시스템 흐름', `<ol class="flow-list" data-system-flow>${flow.map(([n, t, href, c, desc]) => `<li><a class="flow-item" href="${href}"><span class="flow-badge">${n}</span><span class="body"><span class="title">${esc(t)} ${c}</span><span class="desc">${esc(desc)}</span></span></a></li>`).join('')}</ol>`)
    + `<div class="grid two">`
    + card('주의할 것', attention.length ? `<ul class="list" data-attention>${attention.join('')}</ul>` : '<p class="empty" data-attention-empty>2주 안 예상 실적·켜진 경고등이 없습니다.</p>', 'data-card="attention"')
    + card('최근 7일 공시·뉴스', feedList(recent, '최근 7일 공시·뉴스가 없습니다.') + '<p class="note">정보 제공용입니다. 점수에 반영하지 않습니다.</p>', 'data-card="recent"')
    + `</div>`
    + card(`TARGET ${d.catalog ? d.catalog.target_root_version : ''} · ${targets.length}종목`, targetRows.length ? `<div class="table-wrap"><table data-target-table><thead><tr><th>기업</th><th>테마</th><th class="num">목표</th><th class="num">QGV</th><th class="num">Q</th><th class="num">G</th></tr></thead><tbody>
        ${targetRows.map((r) => `<tr data-target-row="${esc(r.key)}"><td>${companyCell(r)}</td><td class="small">${esc(r.target ? r.target.theme : '')}</td><td class="num">${esc(r.target ? pct(r.target.weight) : '—')}</td><td class="num">${scoreCell(r.total)}</td><td class="num">${scoreCell(r.q)}</td><td class="num">${scoreCell(r.g)}</td></tr>`).join('')}
      </tbody></table></div><p class="note">목표 비중(TARGET)입니다. 실제 보유(ACTUAL)는 기기 전용이라 이 화면에 없습니다. QGV는 가격 없이 Q·G로만 계산돼 V가 빠져 있습니다.</p>` : '<p class="empty">TARGET 카탈로그를 읽지 못했습니다.</p>', 'data-card="target"')
    + card('데이터 기준', `<dl class="kv" data-data-basis>
        <dt>QGV v2 기준 시각</dt><dd>${esc(shortTime(cov.asOf) || '—')}</dd>
        <dt>계산 규칙 버전</dt><dd>${esc(cov.calcVersion ? cov.calcVersion.replace('qgv2-calc/', '') : '—')}</dd>
        <dt>계산 버전이 달라 제외</dt><dd>${esc(cov.codes ? cov.mismatch + '종목' : '—')}</dd>
        <dt>아직 자료 없음</dt><dd>${esc(cov.codes ? cov.missing + '종목' : '—')}</dd>
        <dt>목표 비중 버전</dt><dd>${esc(d.catalog ? 'TARGET ' + d.catalog.target_root_version : '—')}</dd>
        <dt>매크로 기준</dt><dd>${esc(m && m.as_of ? shortDate(m.as_of) || '—' : '—')}</dd>
      </dl>`);
}

function countRecords(ledger) {
  return Object.values(ledger.versions || {}).reduce((n, list) => n + (Array.isArray(list) ? list.length : 0), 0);
}
