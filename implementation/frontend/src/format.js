// Formatting and escaping. Missing is never 0: every formatter returns null for a missing input and the
// caller renders the NOT_AVAILABLE marker ('—' or a reason) instead.

export const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ESC[c]);

export function score(v, digits = 1) {
  return isNum(v) ? v.toFixed(digits) : null;
}

export function pct(ratio, digits = 1) {
  return isNum(ratio) ? (ratio * 100).toFixed(digits) + '%' : null;
}

// Short local date/time: '10. 17. 07:48' this year, '2025. 10. 17. 07:48' otherwise. Invalid -> null.
export function shortTime(iso, now = new Date()) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return null;
  const d = new Date(t);
  return new Intl.DateTimeFormat('ko-KR', {
    ...(d.getFullYear() !== now.getFullYear() ? { year: 'numeric' } : {}),
    month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(d);
}

export function shortDate(iso, now = new Date()) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return null;
  const d = new Date(t);
  return new Intl.DateTimeFormat('ko-KR', {
    ...(d.getFullYear() !== now.getFullYear() ? { year: 'numeric' } : {}),
    month: 'numeric', day: 'numeric',
  }).format(d);
}

// '3시간 전', '2일 전'; future or invalid -> null.
export function ago(iso, now = new Date()) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return null;
  const s = Math.floor((now.getTime() - t) / 1000);
  if (s < 0) return null;
  if (s < 3600) return Math.max(1, Math.floor(s / 60)) + '분 전';
  if (s < 86400) return Math.floor(s / 3600) + '시간 전';
  return Math.floor(s / 86400) + '일 전';
}

// Only http(s) links are rendered; anything else is dropped.
export function safeUrl(u) {
  try {
    const url = new URL(String(u));
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch (_) {
    return null;
  }
}

// 'tokyo_electron' -> 'Tokyo Electron', 'nvda' -> 'NVDA'.
export function idName(id) {
  const s = String(id ?? '');
  return s.includes('_') ? s.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') : s.toUpperCase();
}
