// Small HTML builders. Every dynamic value goes through esc(); screens return HTML strings.
import { esc, idName } from './format.js';

// Status chip. tone: ok | warn | watch | risk | na | outline (design canvas chip colors).
export const chip = (text, tone = 'na', attrs = '') => `<span class="chip ${tone}"${attrs ? ' ' + attrs : ''}>${esc(text)}</span>`;

// A missing value: '—' with an optional short reason. Never 0.
export const na = (reason = '') => `<span class="na" data-na>—</span>${reason ? ` <span class="small">${esc(reason)}</span>` : ''}`;

export const value = (text, reason = '') => (text === null || text === undefined ? na(reason) : esc(text));

export function head({ flow = null, eyebrow, title, lede = '' }) {
  return `<header class="page-head"><p class="eyebrow">${flow ? `<span class="flow-badge">${esc(flow)}</span>` : ''}${esc(eyebrow)}</p>`
    + `<h1>${esc(title)}</h1>${lede ? `<p class="lede">${esc(lede)}</p>` : ''}</header>`;
}

export function card(title, body, attrs = '') {
  return `<section class="card"${attrs ? ' ' + attrs : ''}>${title ? `<h2>${esc(title)}</h2>` : ''}${body}</section>`;
}

export function stat(label, text, sub = '', attrs = '') {
  const missing = text === null || text === undefined;
  return `<div class="stat"${attrs ? ' ' + attrs : ''}><span class="label">${esc(label)}</span>`
    + `<span class="value${missing ? ' na' : ''}">${missing ? '—' : esc(text)}</span>${sub ? `<span class="sub">${esc(sub)}</span>` : ''}</div>`;
}

// Monogram logo: no external images are loaded.
export function logo(ticker) {
  const t = String(ticker || '?');
  return `<span class="logo" aria-hidden="true">${esc(/^\d/.test(t) ? t.charAt(0) : t.charAt(0).toUpperCase())}</span>`;
}

export function companyLink(c) {
  const label = c.ticker || idName(c.id);
  return `<a class="company-chip" href="#/company/${encodeURIComponent(c.key)}">${logo(label)}<span>${esc(label)}</span></a>`;
}

export function bar(score) {
  const ok = typeof score === 'number' && Number.isFinite(score);
  // Width is applied by app.js (CSSOM) after render: the CSP has no 'unsafe-inline' for style attributes.
  return `<div class="bar${ok ? '' : ' is-empty'}" aria-hidden="true"><span data-w="${ok ? Math.max(0, Math.min(100, score)).toFixed(1) : 0}"></span></div>`;
}

export function subnav(items, current) {
  return `<nav class="subnav" aria-label="하위 메뉴">${items.map(([href, label, key]) => `<a href="${href}"${key === current ? ' aria-current="page"' : ''}>${esc(label)}</a>`).join('')}</nav>`;
}
