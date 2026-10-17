// S04/S05 기업: QGV v2 result, factor breakdown, the three classification axes, next filing window, disclosures/news.
// Public data only; V needs prices and stays NOT_AVAILABLE. Raw records live in 설정 > 원자료 보기.
import { esc, pct, score } from '../format.js';
import { head, card, chip, stat, bar } from '../ui.js';
import { basisBadges, feed, feedList, nextEarnings, rowStateChip } from './common.js';

const AXIS_NAME = { Q: 'Q · 질', G: 'G · 성장', V: 'V · 가치' };
const TYPE_NAME = { growth: '성장', quality: '우량', cyclical: '경기민감', defensive: '경기방어', value: '가치', dividend: '배당', leader: '주도', theme: '테마' };

export function company(ctx, key) {
  const { state, g, M } = ctx;
  const r = state.list.find((x) => x.key === key);
  if (!r) return head({ eyebrow: 'QGV · 기업', title: '기업을 찾을 수 없습니다' }) + '<p><a href="#/qgv">← 리더보드</a></p>';
  const p = r.primary;
  const weights = g.QgvV2 ? g.QgvV2.WEIGHTS : null;
  const factors = M.factorRows(p, weights);
  const next = r.isTarget ? nextEarnings(r.next) : null;

  const scoreCard = card('QGV v2', `<div class="stats" data-company-scores>
      ${stat('QGV', score(r.total), r.total === null && r.state !== 'NOT_AVAILABLE' ? '반영 비중 부족' : '', 'data-score="total"')}
      ${stat('Q · 질', score(r.q), '', 'data-score="Q"')}
      ${stat('G · 성장', score(r.g), '', 'data-score="G"')}
      ${stat('V · 가치', null, '가격 필요', 'data-score="V"')}
    </div>
    <div class="badges">${rowStateChip(r)}${r.rank !== null && r.rank !== undefined ? chip('정렬 순위 ' + r.rank + ' · 공식 순위 아님', 'outline') : ''}${r.flags.map((f) => chip(f, 'warn')).join('')}</div>
    ${r.reason ? `<p class="small" data-company-reason>${esc(r.reason)}</p>` : ''}
    ${p && (r.state === 'READY' || r.state === 'PARTIAL') ? `<p class="note">산출 요인 ${esc(String(p.factors_available))}/${esc(String(p.factors_total))}${p.profile && g.QgvScores ? ' · ' + esc(profileText(g, p.profile)) : ''}${p.v_excluded ? ' · 가치 함정 관문: V 제외' : ''}</p>` : ''}`, 'data-card="qgv"');

  const factorCard = card('요인', ['Q', 'G', 'V'].map((axis) => `<h3>${esc(AXIS_NAME[axis])}</h3>${factors.filter((f) => f.axis === axis).map((f) => `<div class="factor" data-factor="${esc(f.id)}"${f.code ? ` data-reason-code="${esc(f.code)}"` : ''}>
      <span class="name">${esc(f.label)}<small>비중 ${esc(String(f.weight))}%</small></span><span class="score">${f.score === null ? '<span class="na">—</span>' : esc(score(f.score))}</span>
      ${f.score === null ? '' : bar(f.score)}${f.reason ? `<span class="why">${esc(f.reason)}</span>` : ''}</div>`).join('')}`).join('')
    + '<p class="note">점수는 504종목 안 백분위(0~100)입니다. 결측은 0으로 채우지 않습니다. V 요인은 가격이 있어야 계산됩니다.</p>', 'data-card="factors"');

  return '<a class="back" href="#/qgv">← 리더보드</a>'
    + head({ flow: '1', eyebrow: 'QGV · 기업', title: r.ticker, lede: [r.name, r.target ? `TARGET · ${r.target.theme} · 목표 ${pct(r.target.weight)}` : null].filter(Boolean).join(' · ') })
    + basisBadges(ctx)
    + (r.isTarget ? `<p class="small" data-next-earnings>${next ? '다음 실적 ' + esc(next) : '다음 실적 확인 불가'}</p>` : '')
    + `<div class="grid wide-left"><div>${scoreCard}${factorCard}</div><div>`
    + classificationCard(ctx, r)
    + (r.isTarget ? card('공시·뉴스 (90일)', feedList(feed(ctx, { companyIds: [r.key], limit: 12, sinceDays: 90 }), '최근 90일 공시·뉴스가 없습니다.'), 'data-card="company-feed"') : '')
    + card('', '<p class="small">원자료(개발자용)는 <a href="#/settings">설정 → 원자료 보기</a>에 있습니다.</p>')
    + '</div></div>';
}

function profileText(g, profile) {
  const p = g.QgvScores.presets()[profile.preset];
  const name = p ? String(p.name).replace(/\s*\(.*\)$/, '') : profile.preset;
  return name + ' · 관문 ' + (profile.gate ? '켬' : '끔');
}

// 산업 (SEC SIC 업종군) / 전략 테마 / 투자 유형: three separate axes, none fills in for another.
function classificationCard(ctx, r) {
  const { state, g } = ctx, d = state.data;
  const cls = g.ClassificationScreens ? d.screens[g.ClassificationScreens.FILE] : null;
  const rec = cls && r.id && cls.data && cls.data.companies ? cls.data.companies[r.id] : null;
  const cfg = cls && cls.data ? cls.data : null;
  const named = (list, id) => { const x = (list || []).find((y) => y.id === id); return x ? x.name : id; };
  let industry;
  if (rec && rec.industry && rec.industry.state !== 'NOT_AVAILABLE' && rec.industry.group) {
    industry = `${chip(named(cfg.industry_config.groups, rec.industry.group), 'ok')}${rec.industry.subgroup ? ' ' + chip(named(cfg.industry_config.subgroups, rec.industry.subgroup), 'outline') : ''} <span class="small">SIC ${esc(rec.industry.sic || '—')}</span>`;
  } else if (r.industryGroup) {
    industry = `${chip(cfg ? named(cfg.industry_config.groups, r.industryGroup) : r.industryGroup, 'ok')} <span class="small">SIC ${esc(r.sic || '—')}</span>`;
  } else {
    industry = '<span class="na">—</span> <span class="small">업종 자료 없음</span>';
  }
  let themes;
  if (rec && rec.themes && rec.themes.memberships) {
    const on = Object.entries(rec.themes.memberships).filter(([, m]) => m && m.member === true).map(([id]) => named(cfg.theme_config.themes, id));
    themes = on.length ? on.map((t) => chip(t, 'watch')).join(' ') : '<span class="small">해당 테마 없음</span>';
  } else {
    themes = `<span class="na">—</span> <span class="small">${r.isTarget ? '테마 자료 없음' : 'TARGET 기업만 분류'}</span>`;
  }
  const p = r.primary;
  let types;
  if (p && Array.isArray(p.selected_types) && p.selected_types.length) types = p.selected_types.map((t) => chip(TYPE_NAME[t] || t, 'ok')).join(' ');
  else if (r.isTarget && p && p.type_reason) types = '<span class="small">해당 유형 없음 또는 자료 없음</span>';
  else types = `<span class="na">—</span> <span class="small">${r.isTarget ? '유형 자료 없음' : 'TARGET 기업만 계산'}</span>`;
  return card('분류 3축', `<dl class="kv axis-list" data-classification>
      <dt>산업</dt><dd data-axis="industry">${industry}</dd>
      <dt>전략 테마</dt><dd data-axis="theme">${themes}</dd>
      <dt>투자 유형</dt><dd data-axis="type">${types}</dd>
    </dl><p class="note">산업·전략 테마·투자 유형은 서로 다른 축이며 서로 대신 채우지 않습니다. 분류 v0 · 보정 전.</p>`, 'data-card="classification"');
}
