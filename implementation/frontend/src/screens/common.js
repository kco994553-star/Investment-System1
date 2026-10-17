// Shared pieces of the screens: the disclosure/news feed, company labels and the data-basis badges.
import { esc, shortTime, ago, safeUrl, score, idName } from '../format.js';
import { chip, na, companyLink } from '../ui.js';

// One chronological feed (newest first) from the cockpit's own merge (NewsSignals.timeline): SEC 8-K/6-K, DART and news.
export function feed(ctx, { companyIds = null, limit = 8, sinceDays = null } = {}) {
  const { g, state } = ctx, d = state.data;
  if (!g.NewsSignals || typeof g.NewsSignals.timeline !== 'function') return [];
  let rows = [];
  try {
    rows = g.NewsSignals.timeline({ sec: d.disclosures, dart: d.dart, news: d.news }, { companyIds, dartApi: g.DartDisclosures || null });
  } catch (_) {
    rows = [];
  }
  const now = Date.now();
  const out = [];
  for (const r of rows) {
    const t = Date.parse(r.time);
    if (sinceDays !== null && (!Number.isFinite(t) || now - t > sinceDays * 86400000)) continue;
    out.push(feedItem(g, r));
    if (out.length >= limit) break;
  }
  return out;
}

function feedItem(g, r) {
  const e = r.event || null, i = r.item || null;
  let kind, title, link, tone;
  if (r.channel === 'DISCLOSURE' && r.source === 'SEC' && e) {
    const label = g.SecDisclosures ? g.SecDisclosures.classLabel(e.classification, false, e.items || []) : e.classification;
    kind = '공시 · ' + e.form;
    title = (e.exhibit_99_1 && e.exhibit_99_1.state === 'AVAILABLE' && e.exhibit_99_1.title) ? e.exhibit_99_1.title : label;
    link = e.link;
    tone = e.classification === 'RESULTS' ? 'watch' : 'outline';
  } else if (r.source === 'DART' && e) {
    kind = '공시 · DART';
    title = e.title || e.report_type || '공시';
    link = e.link;
    tone = 'outline';
  } else {
    kind = '뉴스 · ' + (r.source || '');
    title = i ? i.title : '';
    link = i ? i.link : null;
    tone = 'outline';
  }
  return { kind, title, link: safeUrl(link), time: r.time, company: r.company_id, tone, repeats: (r.repeats || []).length };
}

export function feedList(items, empty = '최근 공시·뉴스가 없습니다.') {
  if (!items.length) return `<p class="empty">${esc(empty)}</p>`;
  return `<ul class="list" data-feed>${items.map((x) => `<li data-feed-item>
    <span class="row">${chip(x.kind, x.tone)}<a class="company-chip" href="#/company/${encodeURIComponent(x.company)}">${esc(idName(x.company))}</a><span class="small">${esc(ago(x.time) || shortTime(x.time) || '')}</span></span>
    ${x.link ? `<a class="title" href="${esc(x.link)}" target="_blank" rel="noopener noreferrer">${esc(x.title)}</a>` : `<span class="title">${esc(x.title)}</span>`}
    ${x.repeats ? `<span class="meta">같은 소식 ${x.repeats}건 더</span>` : ''}</li>`).join('')}</ul>`;
}

// Score cell: the number, or '—' with the reason folded (never 0, never v1).
export function scoreCell(v) {
  const s = score(v);
  return s === null ? na() : `<span class="num">${esc(s)}</span>`;
}

export function rowStateChip(r) {
  if (r.state === 'READY') return chip('점수 있음', 'ok');
  if (r.state === 'PARTIAL') return chip('일부만', 'warn');
  if (r.state === 'MISMATCH') return chip('계산 버전 다름', 'na');
  return chip('자료 없음', 'na');
}

export function companyCell(r) {
  return `${companyLink({ key: r.key, ticker: r.ticker, id: r.id })}${r.name && r.name !== r.ticker ? ` <span class="small">${esc(r.name)}</span>` : ''}${r.isTarget ? ' ' + chip('TARGET', 'watch') : ''}${r.reference ? ' ' + chip('참고 순위', 'warn') : ''}`;
}

// Next estimated filing window, never a confirmed date: '10/20경 (확정 아님) · D-3' or '제출 구간 진행 중'.
export function nextEarnings(next) {
  if (!next) return null;
  if (next.status !== 'ESTIMATED' || !next.window) return null;
  const w = next.window;
  return w.start.replace('-', '/') + '경 (확정 아님) · ' + (w.days_until_start === 0 ? '제출 구간 진행 중' : 'D-' + w.days_until_start);
}

export function basisBadges(ctx) {
  const { state } = ctx, cov = state.cov;
  const asOf = shortTime(cov.asOf);
  return `<div class="badges" data-basis>
    ${chip('QGV v2 · 잠정', 'outline')}
    ${asOf ? chip('기준 ' + asOf, 'outline', `data-as-of="${esc(cov.asOf)}"`) : chip('QGV 자료 없음', 'na')}
    ${chip('시세 없음 · 공개 자료는 가격 미포함', 'na')}
  </div>`;
}
