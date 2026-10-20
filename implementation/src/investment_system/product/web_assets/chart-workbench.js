/* Technical chart workbench (P1-8, P1-9 subset). Display only: no orders, no signals, no scores.
   Real prices arrive only at run time from PrivateHistory (private Worker, RAM only) through update().
   The built-in preview uses generated synthetic bars and is always labelled as such.
   Weekly bars come only from ChartBars (chart-bars.js, lane B1); this file never aggregates bars.
   Device storage holds display toggles only (no prices). Nothing here changes official detection. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ChartWorkbench = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SETTINGS_KEY = 'investment.web.v1.chart-display-settings';
  const SETTINGS_SCHEMA = 'chart-display-settings/1';
  const INDICATOR_GROUPS = Object.freeze({
    SMA: Object.freeze([['SMA_5', 'price', 0], ['SMA_20', 'price', 1], ['SMA_60', 'price', 2], ['SMA_120', 'price', 3], ['SMA_240', 'price', 4]]),
    EMA: Object.freeze([['EMA_20', 'price', 5]]),
    BOLL: Object.freeze([['BOLL_UPPER_20_2', 'price', 4], ['BOLL_MIDDLE_20', 'price', 4], ['BOLL_LOWER_20_2', 'price', 4]]),
    RSI: Object.freeze([['RSI_14', 'rsi', 0]]),
    MACD: Object.freeze([['MACD_12_26', 'macd', 0], ['MACD_SIGNAL_9', 'macd', 1], ['MACD_HISTOGRAM_12_26_9', 'macd', 0, 'histogram']]),
    ATR: Object.freeze([['ATR_14', 'atr', 2]])
  });
  const DEFAULT_SETTINGS = Object.freeze({schema: SETTINGS_SCHEMA, mode: 'long', renderer: 'lwc', indicators: Object.freeze({SMA: true, EMA: false, BOLL: false, RSI: false, MACD: false, ATR: false})});
  const SYNTHETIC_LABEL = Object.freeze(['합성 자료 · 미리보기 · 실데이터 검증 아님', 'Synthetic data · Preview · Not validated on real data']);
  const NOTICE_TEXT = 'TradingView Lightweight Charts™ Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/';
  const active = new Set();

  /* ---------- settings (display toggles only) ---------- */

  function readSettings(storage) {
    let parsed = null;
    try { const raw = storage && storage.getItem(SETTINGS_KEY); parsed = raw ? JSON.parse(raw) : null; } catch (_) { parsed = null; }
    const out = {schema: SETTINGS_SCHEMA, mode: DEFAULT_SETTINGS.mode, renderer: DEFAULT_SETTINGS.renderer, indicators: {...DEFAULT_SETTINGS.indicators}};
    if (parsed && parsed.schema === SETTINGS_SCHEMA) {
      if (['long', 'swing'].includes(parsed.mode)) out.mode = parsed.mode;
      if (['lwc', 'svg'].includes(parsed.renderer)) out.renderer = parsed.renderer;
      if (parsed.indicators && typeof parsed.indicators === 'object') for (const key of Object.keys(out.indicators)) if (typeof parsed.indicators[key] === 'boolean') out.indicators[key] = parsed.indicators[key];
    }
    return out;
  }
  function writeSettings(storage, settings) {
    try { storage.setItem(SETTINGS_KEY, JSON.stringify({schema: SETTINGS_SCHEMA, mode: settings.mode, renderer: settings.renderer, indicators: settings.indicators})); return true; } catch (_) { return false; }
  }

  /* ---------- bars: daily view and the ChartBars weekly boundary ---------- */

  function sessionDate(timestamp, timezone) {
    const parts = new Intl.DateTimeFormat('en-CA', {timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date(timestamp * 1000)), get = type => parts.find(x => x.type === type).value;
    return get('year') + '-' + get('month') + '-' + get('day');
  }
  // Same session-date rule as PrivateTrades.markers: provider session label, else the exchange-local date.
  function dailyView(raw, timezone) {
    return raw.map(bar => ({time: typeof bar.session_date === 'string' ? bar.session_date : sessionDate(bar.timestamp, timezone || 'UTC'),
      open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume, status: bar.session_status}));
  }

  /* Weekly boundary: lane B1 chart-bars.js (ChartBars, schema chart-bars/1, rule W1).
       ChartBars.normalize(private-history/1) -> daily series; ChartBars.weekly(series, actions) -> weekly series
       whose bars carry week_start, first_session, last_session, open..volume (null when missing) and state.
     This is the only place that reads ChartBars output. No aggregation happens in this file.
     Split events are not delivered yet (P1-W), so actions stay null (NOT_PROVIDED). */
  function historyOf(data) {
    return {schema: 'private-history/1', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', symbol: data.symbol || '', provider: data.provider || '',
      currency: data.currency || '', timezone: data.timezone || 'UTC', read_at: data.readAt || '', bars: data.bars};
  }
  function weeklyView(view, data) {
    const api = view.ChartBars;
    if (!api || typeof api.normalize !== 'function' || typeof api.weekly !== 'function') return {code: 'WEEKLY_BARS_MODULE_PENDING', bars: null};
    let result;
    try { result = api.weekly(api.normalize(historyOf(data)), null); } catch (_) { return {code: 'WEEKLY_BARS_FAILED', bars: null}; }
    const list = result && Array.isArray(result.bars) ? result.bars : null;
    if (!list || !list.length) return {code: 'WEEKLY_BARS_FAILED', bars: null};
    return {code: 'READY', bars: list.map(w => ({time: w.week_start, start: w.first_session, end: w.last_session, open: w.open, high: w.high, low: w.low, close: w.close, volume: w.volume, status: w.state === 'COMPLETE' ? 'COMPLETE' : 'PROVISIONAL'}))};
  }
  // Price-basis continuity of the shown window from ChartBars (display reason codes only).
  function continuityCodes(view, bars) {
    const api = view.ChartBars;
    if (!api || typeof api.continuity !== 'function' || !bars.length) return ['PRICE_BASIS_CONTINUITY_UNCONFIRMED'];
    try { const r = api.continuity(null, bars[0].start, bars[bars.length - 1].end); return r && Array.isArray(r.reason_codes) && r.reason_codes.length ? r.reason_codes : ['PRICE_BASIS_CONTINUITY_UNCONFIRMED']; }
    catch (_) { return ['PRICE_BASIS_CONTINUITY_UNCONFIRMED']; }
  }

  /* ---------- synthetic preview (generated, deterministic, never market data) ---------- */

  function syntheticHistory() {
    let seed = 20261020;
    const random = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
    const round = x => Math.round(x * 100) / 100, bars = [];
    let day = Date.UTC(2025, 0, 6), close = 100;
    while (bars.length < 320) {
      const weekday = new Date(day).getUTCDay();
      if (weekday >= 1 && weekday <= 5) {
        const open = close * (1 + (random() - 0.5) * 0.02);
        close = open * (1 + (random() - 0.5) * 0.035 + 0.004 * Math.sin(bars.length / 23));
        const high = Math.max(open, close) * (1 + random() * 0.012), low = Math.min(open, close) * (1 - random() * 0.012);
        bars.push({timestamp: day / 1000 + 52200, session_date: new Date(day).toISOString().slice(0, 10), open: round(open), high: round(high), low: round(low), close: round(close), adjusted_close: null, volume: Math.round(800000 + random() * 900000), session_status: 'COMPLETE'});
        const last = bars.at(-1); last.high = Math.max(last.high, last.open, last.close); last.low = Math.min(last.low, last.open, last.close);
      }
      day += 86400000;
    }
    bars[60].volume = null;
    Object.assign(bars[120], {open: null, high: null, low: null, close: null});
    bars.at(-1).session_status = 'IN_PROGRESS';
    return Object.freeze({symbol: 'SYNTH', provider: 'SYNTHETIC', timezone: 'UTC', currency: '', readAt: '', bars});
  }

  /* ---------- helpers ---------- */

  function words(state, ko, en) { return state.locale === 'en-US' ? en : ko; }
  function node(doc, tag, attrs = {}, text) {
    const el = doc.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) if (value !== undefined && value !== null) el.setAttribute(key, String(value));
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function fmt(state, value) { return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString(state.locale || 'ko-KR', {maximumSignificantDigits: 6}) : '—'; }
  function fmtVolume(state, value) { return typeof value === 'number' && Number.isFinite(value) ? Math.round(value).toLocaleString(state.locale || 'ko-KR') : words(state, '결측', 'missing'); }
  function signed(state, value, digits) { return (value > 0 ? '+' : '') + value.toLocaleString(state.locale || 'ko-KR', {maximumFractionDigits: digits}); }
  function statusWord(state, bar) { return bar.complete ? words(state, '확정', 'complete') : words(state, '잠정', 'provisional'); }

  function lines(state) {
    if (state.timeframe !== 'daily' || !state.data || !state.data.indicators || !Array.isArray(state.data.indicators.indicators)) return [];
    const byId = new Map(state.data.indicators.indicators.map(item => [item.indicator_id, item.values])), out = [];
    for (const [group, specs] of Object.entries(INDICATOR_GROUPS)) {
      if (!state.settings.indicators[group]) continue;
      for (const [id, pane, tone, type] of specs) if (byId.has(id)) out.push({id, pane, tone, type: type || 'line', values: byId.get(id)});
    }
    return out;
  }

  /* ---------- painting ---------- */

  function setAttr(state, name, value) { state.root.setAttribute(name, String(value)); }

  function paintRange(state) {
    const span = state.renderer && state.bars.length ? state.renderer.getVisibleRange() : null;
    const from = span ? state.bars[span.from].time : '', to = span ? state.bars[span.to].time : '';
    setAttr(state, 'data-visible-from', from); setAttr(state, 'data-visible-to', to);
    const frame = state.timeframe === 'weekly' ? words(state, '주봉', 'weekly') : words(state, '일봉', 'daily');
    state.chartBox.setAttribute('aria-label', [state.symbol || words(state, '자료 없음', 'No data'), frame, from && to ? words(state, '보이는 기간 ', 'visible ') + from + ' ~ ' + to : '', words(state, '선택 패턴 없음', 'no pattern selected')].filter(Boolean).join(' · '));
  }

  function readoutText(state, index) {
    const bar = state.bars[index];
    if (!bar) return '';
    const ohlc = bar.ohlc ? words(state, '시가 ', 'O ') + fmt(state, bar.open) + ' · ' + words(state, '고가 ', 'H ') + fmt(state, bar.high) + ' · ' + words(state, '저가 ', 'L ') + fmt(state, bar.low) + ' · ' + words(state, '종가 ', 'C ') + fmt(state, bar.close) : words(state, 'OHLC 결측', 'OHLC missing');
    const span = bar.start !== bar.end ? ' (' + bar.start + ' ~ ' + bar.end + ')' : '';
    return bar.time + span + ' · ' + ohlc + ' · ' + words(state, '거래량 ', 'Vol ') + fmtVolume(state, bar.volume) + ' · ' + statusWord(state, bar);
  }

  function paintReadout(state, index, source) {
    state.cursor = typeof index === 'number' ? index : null;
    const text = state.cursor === null ? words(state, '차트 위를 가리키거나 길게 누르면 봉 값이 여기에 고정 표시됩니다.', 'Point at the chart or long-press to pin bar values here.') : readoutText(state, state.cursor);
    state.readout.textContent = text;
    state.readout.dataset.tracking = source === 'touch' ? 'touch' : source === 'keyboard' ? 'keyboard' : source === 'pointer' ? 'pointer' : 'off';
    if (state.cursor !== null) state.readout.dataset.index = String(state.cursor); else delete state.readout.dataset.index;
    if (source === 'keyboard' && state.cursor !== null) state.live.textContent = text;
  }

  function paintMeasure(state) {
    const m = state.measure;
    setAttr(state, 'data-measure-state', !state.measuring ? 'off' : m ? 'done' : state.measureStart ? 'first-point' : 'armed');
    if (!state.measuring) { state.measureOut.textContent = words(state, '측정 꺼짐 · 측정은 두 점 사이 값만 보여 줍니다(신호 아님).', 'Measure off · Shows values between two points only (not a signal).'); return; }
    if (!m) { state.measureOut.textContent = state.measureStart ? words(state, '첫 점 ', 'First point ') + state.bars[state.measureStart.index].time + ' · ' + fmt(state, state.measureStart.price) + words(state, ' · 두 번째 점을 고르세요', ' · pick the second point') : words(state, '측정 켜짐 · 차트에서 두 점을 누르세요(키보드: M).', 'Measure on · Tap two points on the chart (keyboard: M).'); return; }
    state.measureOut.textContent = words(state, '측정 · ', 'Measure · ') + m.from.time + ' ' + fmt(state, m.from.price) + ' → ' + m.to.time + ' ' + fmt(state, m.to.price)
      + ' · ' + words(state, '가격 차 ', 'diff ') + signed(state, Number(m.diff.toPrecision(6)), 6) + ' · ' + signed(state, m.percent, 2) + '% · ' + m.bars + words(state, '봉', ' bars') + ' · ' + m.days + words(state, '일', ' days')
      + ' · ' + words(state, '측정 표시만 · 신호 아님', 'measurement only · not a signal');
  }

  function paintJudgement(state) {
    // Never a signal: without confirmed price-basis continuity the window is not judged (design §7.3, Q3).
    const reasons = state.source === 'device' ? continuityCodes(state.view, state.daily) : [];
    const code = !state.data ? 'NO_DATA' : state.source === 'synthetic' ? 'SYNTHETIC_PREVIEW' : reasons.includes('CORPORATE_ACTION_IN_WINDOW') ? 'CORPORATE_ACTION_IN_WINDOW' : 'PRICE_BASIS_CONTINUITY_UNCONFIRMED';
    state.judgement.dataset.code = code;
    state.judgement.dataset.reasons = reasons.join(' ');
    state.judgement.replaceChildren(node(state.doc, 'span', {class: 'badge NOT_AVAILABLE'}, words(state, '판정 불가', 'Not judged')), state.doc.createTextNode(' ' + (reasons.length ? reasons.join(' · ') : code) + ' · ' + (
      code === 'NO_DATA' ? words(state, '차트 자료가 없습니다.', 'No chart data.')
        : code === 'SYNTHETIC_PREVIEW' ? words(state, '합성 자료는 판정하지 않습니다.', 'Synthetic data is never judged.')
          : words(state, '가격 기준 연속성(분할 이벤트, P1-W)을 확인하지 못해 패턴을 판정하지 않습니다. 패턴 엔진 연결 전입니다.', 'Price-basis continuity (split events, P1-W) is unconfirmed, so no pattern is judged. The pattern engine is not connected.'))));
  }

  function paintSource(state) {
    const doc = state.doc;
    setAttr(state, 'data-source', state.source);
    state.sourceLine.replaceChildren();
    if (state.source === 'synthetic') state.sourceLine.append(node(doc, 'strong', {'data-synthetic-label': ''}, words(state, ...SYNTHETIC_LABEL)), doc.createTextNode(' · ' + words(state, '생성한 봉 · 시장 가격 아님', 'generated bars · not market prices')));
    else if (state.source === 'device') state.sourceLine.append(doc.createTextNode(words(state, '이 기기 RAM · 비공개 일봉 · 저장 안 함 · ', 'This device RAM · private daily bars · not saved · ') + [state.data.provider, state.data.symbol, state.data.readAt ? 'read_at ' + state.data.readAt : ''].filter(Boolean).join(' · ')));
    else state.sourceLine.textContent = words(state, '자료 없음 · 위의 가격 차트에서 "가격 불러오기"를 누르거나 합성 미리보기를 고르세요.', 'No data · Press “Load prices” in the price chart above, or pick the synthetic preview.');
  }

  function paintButtons(state) {
    for (const button of state.root.querySelectorAll('[data-cw-mode]')) button.setAttribute('aria-pressed', String(button.dataset.cwMode === state.settings.mode));
    for (const button of state.root.querySelectorAll('[data-cw-timeframe]')) button.setAttribute('aria-pressed', String(button.dataset.cwTimeframe === state.timeframe));
    for (const button of state.root.querySelectorAll('[data-cw-renderer]')) button.setAttribute('aria-pressed', String(button.dataset.cwRenderer === state.settings.renderer));
    const weekly = state.root.querySelector('[data-cw-timeframe="weekly"]');
    weekly.disabled = state.weeklyCode !== 'READY';
    state.weeklyStatus.dataset.code = state.weeklyCode;
    state.weeklyStatus.textContent = state.weeklyCode === 'READY' ? '' : words(state, '주봉 · ', 'Weekly · ') + state.weeklyCode + (state.weeklyCode === 'WEEKLY_BARS_MODULE_PENDING' ? words(state, ' · 주봉 모듈(chart-bars.js) 연결 전', ' · weekly module (chart-bars.js) not connected') : '');
    const caps = state.renderer ? state.renderer.capabilities : {measure: false, zoom: false};
    state.measureButton.disabled = !caps.measure || !state.bars.length;
    state.measureButton.setAttribute('aria-pressed', String(state.measuring));
    for (const button of state.root.querySelectorAll('[data-cw-zoom]')) button.disabled = !caps.zoom || !state.bars.length;
    state.limits.hidden = !(state.renderer && state.renderer.kind === 'svg');
    state.indicatorNote.textContent = state.timeframe === 'weekly' ? words(state, '주봉에서는 보조 지표를 그리지 않습니다(TA-G3 결정 대기).', 'No indicators on weekly bars (TA-G3 decision pending).') : state.renderer && state.renderer.kind === 'svg' ? words(state, 'SVG 대체 경로는 가격 위 선(SMA·EMA·볼린저)만 그립니다.', 'The SVG fallback draws price-pane lines only (SMA, EMA, Bollinger).') : '';
  }

  function paintMode(state) {
    const doc = state.doc, panel = state.modePanel;
    panel.replaceChildren();
    panel.dataset.mode = state.settings.mode;
    if (state.settings.mode === 'long') {
      panel.append(node(doc, 'h3', {}, words(state, '장기 보유 모드', 'Long-term mode')),
        node(doc, 'p', {}, words(state, '주봉 구조를 먼저 봅니다. QGV와 나란히 볼 뿐이며, 이 차트는 QGV·TARGET·플레이북을 바꾸지 않고 입력으로도 쓰이지 않습니다.', 'Weekly structure first. Shown beside QGV only; this chart never changes QGV, TARGET or the playbook and is not an input to them.')),
        node(doc, 'a', {href: state.qgvHref || '#leaderboard', 'data-cw-qgv-link': ''}, words(state, 'QGV 나란히 보기 →', 'View QGV alongside →')));
    } else {
      panel.append(node(doc, 'h3', {}, words(state, '스윙 모드', 'Swing mode')),
        node(doc, 'p', {'data-cw-swing-slot': ''}, words(state, '시나리오 그리기 자리 · 2단계(P2-2·P2-3)에서 연결합니다 · 주문 아님 · 가정 계산 · 지금은 아무것도 그리지 않습니다.', 'Scenario drawing slot · connected in phase 2 (P2-2, P2-3) · not an order · assumption only · nothing is drawn yet.')));
    }
  }

  function paintAll(state) { paintSource(state); paintJudgement(state); paintButtons(state); paintMode(state); paintMeasure(state); paintRange(state); setAttr(state, 'data-timeframe', state.timeframe); setAttr(state, 'data-renderer', state.renderer ? state.renderer.kind : 'none'); setAttr(state, 'data-mode', state.settings.mode); }

  /* ---------- rendering ---------- */

  function computeBars(state) {
    state.weeklyCode = 'WEEKLY_BARS_MODULE_PENDING';
    state.daily = []; state.weekly = null;
    if (!state.data) return;
    const R = state.view.ChartRenderer;
    state.daily = R.normalizeBars(dailyView(state.data.bars, state.data.timezone));
    const weekly = weeklyView(state.view, state.data);
    state.weeklyCode = weekly.code;
    if (weekly.bars) { try { state.weekly = R.normalizeBars(weekly.bars); } catch (_) { state.weekly = null; state.weeklyCode = 'WEEKLY_BARS_FAILED'; } }
  }

  async function createRenderer(state, want) {
    const R = state.view.ChartRenderer, callbacks = {
      locale: state.locale, provisionalLabel: words(state, '잠정', 'Prov.'),
      onCrosshair: hit => {
        if (state.disposed) return;
        if (!hit) { paintReadout(state, state.keyboardCursor, state.keyboardCursor !== null ? 'keyboard' : null); return; }
        paintReadout(state, hit.index, state.touching ? 'touch' : hit.index === state.keyboardCursor ? 'keyboard' : 'pointer');
      },
      onRange: () => { if (!state.disposed) paintRange(state); }
    };
    state.rendererCode = 'READY';
    try { return await R.create(state.chartBox, want, callbacks); }
    catch (error) {
      if (state.disposed) throw error;
      state.rendererCode = error && error.message === 'RENDERER_UNAVAILABLE' ? 'RENDERER_UNAVAILABLE' : 'RENDERER_FAILED';
      return R.create(state.chartBox, 'svg', callbacks);
    }
  }

  // One renderer at a time on the chart box: creations are serialised so a late one never wipes a newer one.
  async function ensureRenderer(state) {
    for (;;) {
      if (state.pending) { try { await state.pending; } catch (_) { /* handled by the creator */ } continue; }
      if (state.disposed) return null;
      const want = state.settings.renderer === 'svg' ? 'svg' : 'lwc';
      if (state.renderer && (state.renderer.kind === want || state.rendererCode !== 'READY')) return state.renderer;
      if (state.renderer) { state.renderer.destroy(); state.renderer = null; }
      state.pending = createRenderer(state, want);
      let renderer = null;
      try { renderer = await state.pending; } catch (_) { renderer = null; } finally { state.pending = null; }
      if (!renderer) return null;
      if (state.disposed) { renderer.destroy(); return null; }
      state.renderer = renderer;
      state.rendererStatus.dataset.code = state.rendererCode;
      state.rendererStatus.textContent = state.rendererCode === 'READY' ? '' : words(state, '렌더러 · ', 'Renderer · ') + state.rendererCode + words(state, ' · SVG 대체 경로로 표시', ' · shown with the SVG fallback');
      return renderer;
    }
  }

  async function render(state, {keepRange = null} = {}) {
    const generation = ++state.renderGeneration;
    if (!state.data && !state.renderer) { state.bars = []; setAttr(state, 'data-bar-count', 0); setAttr(state, 'data-provisional-count', 0); paintReadout(state, null, null); paintAll(state); return; }
    const renderer = await ensureRenderer(state);
    if (!renderer || state.disposed || generation !== state.renderGeneration) return;
    state.bars = state.timeframe === 'weekly' && state.weekly ? state.weekly : state.daily;
    if (state.timeframe === 'weekly' && !state.weekly) { state.timeframe = 'daily'; state.bars = state.daily; }
    state.measure = null; state.measureStart = null; state.keyboardCursor = null; renderer.setMeasure(null);
    state.chartBox.style.height = '';
    if (!state.bars.length) { renderer.setData({bars: [], lines: []}); state.chartBox.dataset.panes = '0'; }
    else {
      try {
        const panes = renderer.setData({bars: state.bars, lines: lines(state)});
        state.chartBox.dataset.panes = String(panes);
        state.chartBox.style.height = renderer.kind === 'lwc' ? (300 + Math.max(0, panes - 2) * 90) + 'px' : 'auto';
      } catch (error) { state.rendererStatus.dataset.code = 'RENDER_INPUT_INVALID'; state.rendererStatus.textContent = 'RENDER_INPUT_INVALID'; state.bars = []; }
      if (keepRange) renderer.setVisibleRange(keepRange);
      else if (state.bars.length) renderer.setVisibleRange({from: Math.max(0, state.bars.length - (state.timeframe === 'weekly' ? 104 : 120)), to: state.bars.length - 1});
    }
    setAttr(state, 'data-bar-count', state.bars.length);
    setAttr(state, 'data-provisional-count', state.bars.filter(bar => !bar.complete).length);
    paintReadout(state, null, null);
    paintAll(state);
  }

  function addMeasurePoint(state, hit) {
    if (!hit || !state.bars[hit.index]) return;
    if (!state.measureStart || state.measure) { state.measure = null; state.measureStart = hit; state.renderer.setMeasure(null); }
    else { state.measure = state.view.ChartRenderer.measure(state.bars, state.measureStart, hit); state.renderer.setMeasure(state.measure); }
    paintMeasure(state);
    if (state.measure) state.live.textContent = state.measureOut.textContent;
  }

  function moveCursor(state, index) {
    if (!state.bars.length) return;
    const next = Math.max(0, Math.min(state.bars.length - 1, index));
    state.keyboardCursor = next;
    const span = state.renderer.getVisibleRange();
    if (span && (next < span.from || next > span.to)) state.renderer.scroll(next < span.from ? next - span.from : next - span.to);
    state.renderer.showCrosshair(next);
    paintReadout(state, next, 'keyboard');
  }

  function onKey(state, event) {
    if (!state.renderer || !state.renderer.capabilities.keyboard || !state.bars.length) return;
    const current = state.keyboardCursor !== null ? state.keyboardCursor : state.cursor !== null ? state.cursor : (state.renderer.getVisibleRange() || {to: state.bars.length - 1}).to;
    const step = event.shiftKey ? 10 : 1;
    let handled = true;
    switch (event.key) {
      case 'ArrowLeft': moveCursor(state, current - (state.keyboardCursor === null ? 0 : step)); break;
      case 'ArrowRight': moveCursor(state, current + (state.keyboardCursor === null ? 0 : step)); break;
      case 'Home': state.renderer.setVisibleRange({from: 0, to: Math.min(state.bars.length - 1, 59)}); moveCursor(state, 0); break;
      case 'End': state.renderer.setVisibleRange({from: Math.max(0, state.bars.length - 60), to: state.bars.length - 1}); moveCursor(state, state.bars.length - 1); break;
      case '+': case '=': state.renderer.zoom(0.7); break;
      case '-': case '_': state.renderer.zoom(1.4); break;
      case 'Escape': state.keyboardCursor = null; state.renderer.clearCrosshair(); paintReadout(state, null, null); state.live.textContent = words(state, '십자선 지움', 'Crosshair cleared'); break;
      case 'm': case 'M':
        if (state.measuring && state.keyboardCursor !== null && state.bars[state.keyboardCursor].ohlc) addMeasurePoint(state, {index: state.keyboardCursor, price: state.bars[state.keyboardCursor].close});
        else handled = false;
        break;
      default: handled = false;
    }
    if (handled) event.preventDefault();
  }

  /* ---------- public API ---------- */

  function setData(state, data, source) {
    state.data = data; state.source = data ? source : 'none'; state.symbol = data ? data.symbol : '';
    state.measuring = false; computeBars(state);
    if (state.settings.mode === 'long' && state.weeklyCode === 'READY') state.timeframe = 'weekly'; else if (state.timeframe === 'weekly' && state.weeklyCode !== 'READY') state.timeframe = 'daily';
    return render(state);
  }

  function preview(state) {
    const data = syntheticHistory();
    return setData(state, {...data, indicators: state.view.ResearchIndicators ? state.view.ResearchIndicators.calculate(data.bars) : null}, 'synthetic');
  }

  function update(state, payload) {
    if (state.disposed) return Promise.resolve();
    if (!payload) { return state.source === 'device' ? setData(state, null, 'none') : Promise.resolve(); }
    if (!Array.isArray(payload.bars) || !payload.bars.length) return Promise.resolve();
    if (state.source === 'device' && state.data && state.data.symbol === payload.symbol && state.data.readAt === payload.readAt && state.data.bars === payload.bars) {
      state.data = {...state.data, indicators: payload.indicators};
      return state.timeframe === 'daily' ? render(state, {keepRange: state.renderer ? state.renderer.getVisibleRange() : null}) : Promise.resolve();
    }
    return setData(state, {symbol: payload.symbol || '', provider: payload.provider || '', timezone: payload.timezone || 'UTC', currency: payload.currency || '', readAt: payload.readAt || '', bars: payload.bars, indicators: payload.indicators || null}, 'device');
  }

  function dispose(state) {
    if (state.disposed) return;
    state.disposed = true;
    if (state.renderer) state.renderer.destroy();
    state.renderer = null; state.data = null; state.daily = []; state.weekly = null; state.bars = [];
    if (state.observer) state.observer.disconnect();
    state.view.removeEventListener('pagehide', state.pagehide);
    active.delete(state);
  }

  function build(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en);
    const root = node(doc, 'section', {class: 'card chart-workbench', 'data-chart-workbench': '', 'data-source': 'none', 'data-renderer': 'none', 'data-timeframe': 'daily', 'data-mode': state.settings.mode, 'data-bar-count': '0', 'data-provisional-count': '0', 'data-visible-from': '', 'data-visible-to': '', 'data-measure-state': 'off', 'aria-labelledby': state.id + '-title'});
    root.append(node(doc, 'h2', {id: state.id + '-title'}, w('기술 차트 · 미리보기', 'Technical chart · Preview')),
      node(doc, 'p', {class: 'small', 'data-cw-boundary': ''}, w('TradingView 위젯 아님 · 이 기기에서 그림 · 가격은 RAM에만 · 매매 기능 없음 · 판정·신호 없음', 'Not a TradingView widget · Drawn on this device · Prices stay in RAM · No trading features · No judgement or signal')));
    const toolbar = node(doc, 'div', {class: 'cw-toolbar', role: 'toolbar', 'aria-label': w('차트 도구', 'Chart tools')});
    const group = (label, items, attr) => { const g = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': label}); for (const [value, text] of items) g.append(node(doc, 'button', {type: 'button', [attr]: value, 'aria-pressed': 'false'}, text)); return g; };
    toolbar.append(group(w('모드', 'Mode'), [['long', w('장기', 'Long-term')], ['swing', w('스윙', 'Swing')]], 'data-cw-mode'),
      group(w('봉 주기', 'Interval'), [['daily', w('일봉', 'Daily')], ['weekly', w('주봉', 'Weekly')]], 'data-cw-timeframe'),
      group(w('그리기 방식', 'Renderer'), [['lwc', 'Lightweight Charts'], ['svg', w('SVG 대체', 'SVG fallback')]], 'data-cw-renderer'));
    const tools = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': w('보기', 'View')});
    state.measureButton = node(doc, 'button', {type: 'button', 'data-cw-measure': '', 'aria-pressed': 'false'}, w('측정', 'Measure'));
    tools.append(state.measureButton, node(doc, 'button', {type: 'button', 'data-cw-zoom': 'in', 'aria-label': w('확대', 'Zoom in')}, '+'), node(doc, 'button', {type: 'button', 'data-cw-zoom': 'out', 'aria-label': w('축소', 'Zoom out')}, '−'), node(doc, 'button', {type: 'button', 'data-cw-zoom': 'fit'}, w('전체', 'Fit')),
      node(doc, 'button', {type: 'button', 'data-cw-synthetic': ''}, w('합성 미리보기', 'Synthetic preview')));
    toolbar.append(tools);
    state.sourceLine = node(doc, 'p', {class: 'cw-source', 'data-cw-source': ''});
    state.judgement = node(doc, 'p', {class: 'cw-judgement', 'data-cw-judgement': ''});
    state.weeklyStatus = node(doc, 'p', {class: 'small', 'data-cw-weekly-status': ''});
    state.rendererStatus = node(doc, 'p', {class: 'small', 'data-cw-renderer-status': ''});
    state.readout = node(doc, 'div', {class: 'cw-readout', 'data-cw-readout': '', 'data-tracking': 'off'});
    state.chartBox = node(doc, 'div', {class: 'cw-chart', 'data-cw-chart': '', 'data-panes': '0', tabindex: '0', role: 'group', 'aria-describedby': state.id + '-help'});
    state.limits = node(doc, 'p', {class: 'cw-limits', 'data-cw-limits': '', hidden: ''}, w('SVG 대체 경로 · 기능 제한: 확대·이동·십자선·측정·거래량·보조 지표 창·키보드 이동이 없습니다. 아래 일별 가격 표를 함께 보세요.', 'SVG fallback · Limits: no zoom, pan, crosshair, measure, volume, indicator panes or keyboard movement. Use the daily price table as well.'));
    state.measureOut = node(doc, 'p', {class: 'cw-measure', 'data-cw-measure-out': ''});
    state.indicatorNote = node(doc, 'p', {class: 'small', 'data-cw-indicator-note': ''});
    const help = node(doc, 'p', {class: 'small', id: state.id + '-help'}, w('키보드(차트에 초점): ←/→ 한 봉 · Shift+←/→ 열 봉 · +/− 확대·축소 · Home/End 처음·끝 · Esc 십자선 지우기 · 측정 켜짐에서 M 점 찍기. 폰: 끌어서 이동, 두 손가락 확대, 길게 눌러 값 추적.', 'Keyboard (chart focused): ←/→ one bar · Shift+←/→ ten bars · +/− zoom · Home/End first/last · Esc clear crosshair · M marks a point while measuring. Phone: drag to pan, pinch to zoom, long-press to track values.'));
    state.live = node(doc, 'div', {class: 'sr-only', 'aria-live': 'polite', 'data-cw-live': ''});
    state.modePanel = node(doc, 'div', {class: 'cw-mode-panel', 'data-cw-mode-panel': ''});
    root.append(toolbar, state.sourceLine, state.judgement, state.weeklyStatus, state.rendererStatus, state.readout, state.chartBox, state.limits, state.measureOut, state.indicatorNote, help, state.live, state.modePanel, buildSettings(state), buildNotice(state));
    return root;
  }

  function buildSettings(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en);
    const details = node(doc, 'details', {class: 'cw-settings', 'data-cw-settings': ''});
    details.append(node(doc, 'summary', {}, w('지표·패턴 표시 설정 · 이 기기 저장', 'Indicator and pattern display settings · saved on this device')));
    const fieldset = node(doc, 'fieldset', {}), legend = node(doc, 'legend', {}, w('연구용 지표 (RESEARCH_DISPLAY_ONLY · 일봉)', 'Research indicators (RESEARCH_DISPLAY_ONLY · daily)'));
    fieldset.append(legend);
    const labels = {SMA: 'SMA 5·20·60·120', EMA: 'EMA 20', BOLL: w('볼린저 20/2', 'Bollinger 20/2'), RSI: 'RSI 14', MACD: 'MACD 12/26/9', ATR: 'ATR 14'};
    for (const key of Object.keys(INDICATOR_GROUPS)) {
      const label = node(doc, 'label', {class: 'cw-toggle'}), box = node(doc, 'input', {type: 'checkbox', 'data-cw-indicator': key});
      box.checked = state.settings.indicators[key];
      label.append(box, doc.createTextNode(' ' + labels[key]));
      fieldset.append(label);
    }
    const patterns = node(doc, 'fieldset', {'data-cw-pattern-shell': ''});
    patterns.append(node(doc, 'legend', {}, w('패턴 표시 (엔진 연결 전)', 'Pattern display (engine not connected)')));
    for (const [key, text] of [['ZONES', w('지지·저항 구간', 'Support/resistance zones')], ['BOX', w('박스 돌파·이탈', 'Box breakout/breakdown')], ['DOUBLE', w('이중 바닥·천장', 'Double bottom/top')]]) {
      const label = node(doc, 'label', {class: 'cw-toggle'}), box = node(doc, 'input', {type: 'checkbox', disabled: '', 'data-cw-pattern': key});
      label.append(box, doc.createTextNode(' ' + text));
      patterns.append(label);
    }
    details.append(fieldset, patterns, node(doc, 'p', {class: 'small'}, w('표시 설정은 이 기기 화면에만 적용됩니다. 공식 탐지·규칙 버전·QGV·TARGET에 영향을 주지 않으며, 가격은 저장하지 않습니다.', 'Display settings apply to this screen only. They never affect official detection, rule versions, QGV or TARGET, and no prices are saved.')),
      state.settingsStatus = node(doc, 'p', {class: 'small', role: 'status', 'data-cw-settings-status': ''}));
    return details;
  }

  function buildNotice(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en), p = node(doc, 'p', {class: 'small cw-notice', 'data-cw-notice': ''});
    const link = (href, text, extra = {}) => node(doc, 'a', {href, ...extra}, text);
    p.append(doc.createTextNode(w('차트 그리기: TradingView Lightweight Charts™ 5.2.1 (Apache-2.0, 이 사이트에 포함한 파일 · 로고 끔). ', 'Chart drawing: TradingView Lightweight Charts™ 5.2.1 (Apache-2.0, file hosted on this site · logo off). ')),
      node(doc, 'span', {'data-cw-notice-text': ''}, NOTICE_TEXT), doc.createTextNode(' · '),
      link('https://www.tradingview.com/', 'TradingView', {rel: 'noopener noreferrer', target: '_blank', 'data-cw-attribution-link': ''}), doc.createTextNode(' · '),
      link('lightweight-charts-5.2.1.LICENSE.txt', 'LICENSE'), doc.createTextNode(' · '), link('lightweight-charts-5.2.1.NOTICE.txt', 'NOTICE'), doc.createTextNode(' · '),
      link('third-party-notices.txt', w('제3자 고지', 'Third-party notices')));
    return p;
  }

  function wire(state) {
    const root = state.root;
    root.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button || !root.contains(button) || button.disabled) return;
      if (button.dataset.cwMode) {
        state.settings.mode = button.dataset.cwMode; persist(state);
        if (state.settings.mode === 'long' && state.weeklyCode === 'READY' && state.timeframe !== 'weekly') switchTimeframe(state, 'weekly'); else paintAll(state);
      } else if (button.dataset.cwTimeframe) switchTimeframe(state, button.dataset.cwTimeframe);
      else if (button.dataset.cwRenderer) { state.settings.renderer = button.dataset.cwRenderer; persist(state); void render(state); }
      else if (button.hasAttribute('data-cw-measure')) { state.measuring = !state.measuring; state.measure = null; state.measureStart = null; if (state.renderer) state.renderer.setMeasure(null); paintButtons(state); paintMeasure(state); }
      else if (button.dataset.cwZoom && state.renderer) { if (button.dataset.cwZoom === 'fit') state.renderer.fit(); else state.renderer.zoom(button.dataset.cwZoom === 'in' ? 0.7 : 1.4); }
      else if (button.hasAttribute('data-cw-synthetic')) void preview(state);
    });
    root.addEventListener('change', event => {
      const box = event.target;
      if (box.dataset && box.dataset.cwIndicator) { state.settings.indicators[box.dataset.cwIndicator] = box.checked; persist(state); if (state.bars.length) void render(state, {keepRange: state.renderer ? state.renderer.getVisibleRange() : null}); }
    });
    state.chartBox.addEventListener('keydown', event => onKey(state, event));
    // A tap or click (little movement, short press) marks a measure point while measuring.
    state.chartBox.addEventListener('pointerdown', event => { if (event.pointerType === 'touch') state.touching = true; state.press = {x: event.clientX, y: event.clientY, at: event.timeStamp}; });
    state.chartBox.addEventListener('pointerup', event => {
      const press = state.press; state.press = null;
      if (event.pointerType === 'touch') { state.touching = false; if (state.readout.dataset.tracking === 'touch') state.readout.dataset.tracking = 'touch-held'; }
      if (!state.measuring || !press || !state.renderer || Math.hypot(event.clientX - press.x, event.clientY - press.y) > 6 || event.timeStamp - press.at > 500) return;
      const hit = state.renderer.pointAt(event.clientX, event.clientY);
      if (hit) addMeasurePoint(state, hit);
    });
    state.chartBox.addEventListener('pointercancel', event => { state.press = null; if (event.pointerType === 'touch') state.touching = false; });
  }

  function persist(state) {
    const ok = writeSettings(state.storage, state.settings);
    state.settingsStatus.dataset.code = ok ? 'SAVED' : 'STORAGE_UNAVAILABLE';
    state.settingsStatus.textContent = ok ? words(state, '이 기기에 저장함(표시 설정만)', 'Saved on this device (display settings only)') : 'STORAGE_UNAVAILABLE';
  }

  function switchTimeframe(state, next) {
    if (next === state.timeframe || (next === 'weekly' && !state.weekly)) { paintAll(state); return; }
    const source = state.bars, span = state.renderer ? state.renderer.getVisibleRange() : null, target = next === 'weekly' ? state.weekly : state.daily;
    const keep = span && source.length ? state.view.ChartRenderer.mapRange(source, target, span) : null;
    state.timeframe = next;
    void render(state, {keepRange: keep});
  }

  let counter = 0;
  function mount(host, options = {}) {
    const doc = host.ownerDocument, view = doc.defaultView;
    let storage = null; try { storage = options.storage || view.localStorage; } catch (_) { storage = null; }
    const state = {doc, view, host, storage, locale: options.locale, qgvHref: options.qgvHref || null, id: 'cw' + (++counter), settings: readSettings(storage), data: null, source: 'none', symbol: '',
      daily: [], weekly: null, bars: [], timeframe: 'daily', weeklyCode: 'WEEKLY_BARS_MODULE_PENDING', renderer: null, rendererCode: 'READY', pending: null, renderGeneration: 0,
      cursor: null, keyboardCursor: null, press: null, measuring: false, measureStart: null, measure: null, touching: false, disposed: false};
    state.root = build(state);
    host.replaceChildren(state.root);
    wire(state);
    active.add(state);
    state.pagehide = () => dispose(state);
    view.addEventListener('pagehide', state.pagehide);
    if (view.MutationObserver) { state.observer = new view.MutationObserver(() => { if (!host.isConnected || !state.root.isConnected) dispose(state); }); state.observer.observe(doc.documentElement, {childList: true, subtree: true}); }
    paintAll(state); paintReadout(state, null, null);
    void render(state);
    return Object.freeze({update: payload => update(state, payload), clear: () => setData(state, null, 'none'), dispose: () => dispose(state), preview: () => preview(state)});
  }

  function disposeAll() { for (const state of [...active]) dispose(state); }

  return Object.freeze({SETTINGS_KEY, SETTINGS_SCHEMA, SYNTHETIC_LABEL, readSettings, writeSettings, dailyView, weeklyView, continuityCodes, syntheticHistory, mount, disposeAll});
});
