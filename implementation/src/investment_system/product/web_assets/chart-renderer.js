/* Chart renderer adapter (technical chart design §4.4, P1-8).
   A renderer only draws display values it is given. It never calls the network, storage,
   QGV, TARGET, playbook or any pattern engine, and it makes no judgement.
   Implementations: Lightweight Charts 5.2.1 (self-hosted, attributionLogo off) and the
   existing SVG chart (TechnicalChart) as the fallback path (decision Q6). */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ChartRenderer = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const LWC_VERSION = '5.2.1';
  const LWC_FILE = 'lightweight-charts-' + LWC_VERSION + '.standalone.js';
  // Subresource integrity of the vendored, unmodified npm file (sha256 e21cc5ca… is pinned by the Pages guard).
  const LWC_INTEGRITY = 'sha384-KkYqTZlM13Zya6fVUF3IGCBOQ1ehFeJVVgxaVvD/0MebineF9EI8Jkd3NnWNChqN';
  const DATE = /^\d{4}-\d{2}-\d{2}$/;
  const STATUSES = new Set(['COMPLETE', 'IN_PROGRESS', 'UNKNOWN', 'PROVISIONAL']);
  const PANES = Object.freeze(['price', 'rsi', 'macd', 'atr']);
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const positive = x => finite(x) && x > 0;

  /* ---------- input contract (pure) ---------- */

  // View bar: {time,start,end:'YYYY-MM-DD', open,high,low,close (number|null), volume (number|null), status}.
  // start/end are the first and last session the bar covers (equal to time for a daily bar).
  function normalizeBars(bars) {
    if (!Array.isArray(bars) || bars.length > 1500) throw new Error('RENDER_INPUT_INVALID');
    let previous = '';
    return Object.freeze(bars.map(bar => {
      if (!bar || typeof bar !== 'object' || !DATE.test(bar.time) || bar.time <= previous || !STATUSES.has(bar.status)) throw new Error('RENDER_INPUT_INVALID');
      previous = bar.time;
      const start = DATE.test(bar.start) ? bar.start : bar.time, end = DATE.test(bar.end) ? bar.end : bar.time;
      if (start > end) throw new Error('RENDER_INPUT_INVALID');
      const ohlc = [bar.open, bar.high, bar.low, bar.close];
      const valid = ohlc.every(positive) && bar.low <= Math.min(bar.open, bar.close) && bar.high >= Math.max(bar.open, bar.close);
      return Object.freeze({
        time: bar.time, start, end,
        open: valid ? bar.open : null, high: valid ? bar.high : null, low: valid ? bar.low : null, close: valid ? bar.close : null,
        volume: finite(bar.volume) && bar.volume >= 0 ? bar.volume : null,
        status: bar.status, complete: bar.status === 'COMPLETE', ohlc: valid
      });
    }));
  }

  function normalizeLines(lines, length) {
    if (!Array.isArray(lines)) return Object.freeze([]);
    return Object.freeze(lines.filter(line => line && typeof line.id === 'string' && PANES.includes(line.pane) && Array.isArray(line.values) && line.values.length === length)
      .map(line => Object.freeze({id: line.id, pane: line.pane, type: line.type === 'histogram' ? 'histogram' : 'line', values: Object.freeze(line.values.map(v => finite(v) ? v : null)), tone: line.tone || 0})));
  }

  // Overlay objects (design §4.4): display geometry only, each with its origin. AUTO = official detection,
  // USER_SETTINGS = user-settings exploration (drawn dashed). The renderer draws; it never judges.
  // USER = user-written notes and scenarios (purple pen, dashed): never official detection.
  const OVERLAY_SOURCES = new Set(['AUTO', 'USER_SETTINGS', 'USER']), OVERLAY_TONES = new Set(['zone', 'box', 'double', 'invalidation', 'user']);
  const EMPHASIS = new Set(['normal', 'selected', 'dim']);
  function normalizeOverlays(list, bars) {
    if (!Array.isArray(list)) return Object.freeze([]);
    const times = new Set(bars.map(bar => bar.time)), out = [];
    for (const o of list) {
      if (!o || typeof o.id !== 'string' || !OVERLAY_SOURCES.has(o.source) || !OVERLAY_TONES.has(o.tone)) continue;
      const emphasis = EMPHASIS.has(o.emphasis) ? o.emphasis : 'normal';
      if (o.kind === 'line' && times.has(o.from) && times.has(o.to) && o.from < o.to && positive(o.price)) out.push(Object.freeze({id: o.id, kind: 'line', source: o.source, tone: o.tone, emphasis, from: o.from, to: o.to, price: o.price}));
      else if (o.kind === 'segment' && times.has(o.from) && times.has(o.to) && o.from < o.to && positive(o.fromPrice) && positive(o.toPrice)) out.push(Object.freeze({id: o.id, kind: 'segment', source: o.source, tone: o.tone, emphasis, from: o.from, to: o.to, fromPrice: o.fromPrice, toPrice: o.toPrice}));
      else if (o.kind === 'marker' && times.has(o.time) && typeof o.label === 'string' && o.label.length <= 12) out.push(Object.freeze({id: o.id, kind: 'marker', source: o.source, tone: o.tone, emphasis, time: o.time, label: o.label, position: o.position === 'belowBar' ? 'belowBar' : 'aboveBar'}));
    }
    return Object.freeze(out);
  }

  /* ---------- range and measurement helpers (pure) ---------- */

  function clampRange(range, length) {
    if (!length) return null;
    const from = Math.max(0, Math.min(length - 1, Math.round(range.from))), to = Math.max(0, Math.min(length - 1, Math.round(range.to)));
    return from <= to ? {from, to} : {from: to, to: from};
  }

  // Keeps the visible date span when switching daily <-> weekly (§11.3): daily -> the weeks that
  // contain the dates; weekly -> the first and last session of those weeks.
  function mapRange(source, target, range) {
    const span = clampRange(range, source.length);
    if (!span || !target.length) return null;
    const fromDate = source[span.from].start, toDate = source[span.to].end;
    let from = target.findIndex(bar => bar.end >= fromDate);
    if (from < 0) from = target.length - 1;
    let to = -1;
    for (let i = target.length - 1; i >= 0; i--) if (target[i].start <= toDate) { to = i; break; }
    if (to < 0) to = 0;
    return from <= to ? {from, to} : {from: to, to: from};
  }

  function calendarDays(a, b) { return Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / 86400000); }

  // Display-only measurement between two chart points. Not a signal, not stored.
  function measure(bars, a, b) {
    if (!a || !b || !bars[a.index] || !bars[b.index] || !positive(a.price) || !positive(b.price)) return null;
    const [first, second] = a.index <= b.index ? [a, b] : [b, a];
    const diff = second.price - first.price;
    return Object.freeze({
      from: Object.freeze({index: first.index, time: bars[first.index].time, price: first.price}),
      to: Object.freeze({index: second.index, time: bars[second.index].time, price: second.price}),
      diff, percent: diff / first.price * 100, bars: second.index - first.index,
      days: calendarDays(bars[first.index].start, bars[second.index].end)
    });
  }

  /* ---------- colours (read from the page theme; no network) ---------- */

  function colors(doc) {
    const style = doc.defaultView.getComputedStyle(doc.documentElement), read = (name, fallback) => (style.getPropertyValue(name) || '').trim() || fallback;
    return {
      panel: read('--chart-panel', '#ffffff'), ink: read('--chart-ink', '#161616'), muted: read('--chart-muted', '#4a4a4a'), line: read('--line', '#d4d2ca'),
      up: read('--up', '#d7322a'), down: read('--down', '#2457c5'), pen: read('--pen', '#7a4cc2'), font: read('--font-sans', 'system-ui, sans-serif'),
      tones: [read('--m-qgv', '#2457c5'), read('--m-macro', '#e98a12'), read('--m-portfolio', '#138a8a'), read('--m-prompts', '#c2416b'), read('--m-lab', '#5b6472'), read('--m-technical', '#1f8a4c')]
    };
  }
  function alpha(color, a) {
    const hex = /^#([0-9a-f]{6})$/i.exec(color);
    if (!hex) return color;
    const n = parseInt(hex[1], 16);
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  /* ---------- Lightweight Charts loader (same origin only) ---------- */

  let loading = null;
  function loadLibrary(view) {
    if (view.LightweightCharts && typeof view.LightweightCharts.createChart === 'function') return Promise.resolve(view.LightweightCharts);
    if (loading) return loading;
    loading = new Promise((resolve, reject) => {
      const doc = view.document, script = doc.createElement('script');
      script.src = LWC_FILE; script.integrity = LWC_INTEGRITY; script.crossOrigin = 'anonymous'; script.async = true;
      script.dataset.chartRendererVendor = LWC_VERSION;
      script.addEventListener('load', () => {
        const lib = view.LightweightCharts;
        if (lib && typeof lib.createChart === 'function' && typeof lib.version === 'function' && lib.version() === LWC_VERSION) resolve(lib);
        else { loading = null; reject(new Error('RENDERER_UNAVAILABLE')); }
      });
      script.addEventListener('error', () => { loading = null; script.remove(); reject(new Error('RENDERER_UNAVAILABLE')); });
      doc.head.append(script);
    });
    return loading;
  }

  /* ---------- LWC renderer ---------- */

  const LWC_CAPABILITIES = Object.freeze({zoom: true, pan: true, crosshair: true, volume: true, measure: true, keyboard: true, indicatorPanes: true, overlays: true});
  const SVG_CAPABILITIES = Object.freeze({zoom: false, pan: false, crosshair: false, volume: false, measure: false, keyboard: false, indicatorPanes: false, overlays: false});

  function createLwc(host, lib, options = {}) {
    const doc = host.ownerDocument, c = colors(doc), provisionalLabel = options.provisionalLabel || 'PROVISIONAL';
    const chart = lib.createChart(host, {
      autoSize: true,
      layout: {attributionLogo: false, background: {type: lib.ColorType.Solid, color: c.panel}, textColor: c.ink, fontFamily: c.font, panes: {separatorColor: c.line, enableResize: false}},
      grid: {vertLines: {color: alpha(c.line, 0.5)}, horzLines: {color: alpha(c.line, 0.5)}},
      rightPriceScale: {borderColor: c.line}, timeScale: {borderColor: c.line, timeVisible: false, rightOffset: 2},
      crosshair: {mode: lib.CrosshairMode.Normal},
      localization: {locale: options.locale || 'ko-KR'},
      trackingMode: {exitMode: lib.TrackingModeExitMode.OnNextTap},
      kineticScroll: {touch: true, mouse: false},
      handleScroll: true, handleScale: true
    });
    const candles = chart.addSeries(lib.CandlestickSeries, {upColor: c.up, downColor: c.down, borderUpColor: c.up, borderDownColor: c.down, wickUpColor: c.up, wickDownColor: c.down, borderVisible: true, priceLineVisible: false}, 0);
    const volume = chart.addSeries(lib.HistogramSeries, {priceFormat: {type: 'volume'}, priceLineVisible: false, lastValueVisible: false, color: alpha(c.muted, 0.5)}, 1);
    const markers = lib.createSeriesMarkers(candles, []);
    let bars = [], extra = [], measureSeries = null, overlaySeries = [], provisionalMarkers = [], overlayMarkers = [], disposed = false;
    const applyMarkers = () => markers.setMarkers([...provisionalMarkers, ...overlayMarkers].sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0)));
    function clearOverlays() { for (const series of overlaySeries) chart.removeSeries(series); overlaySeries = []; overlayMarkers = []; }
    const listeners = {crosshair: options.onCrosshair, range: options.onRange};
    const byTime = new Map();
    const indexOf = time => typeof time === 'string' ? byTime.get(time) : undefined;
    const paneFor = pane => pane === 'price' ? 0 : 2 + ['rsi', 'macd', 'atr'].filter(p => extra.some(s => s.pane === p)).indexOf(pane);

    chart.subscribeCrosshairMove(param => {
      if (disposed || typeof listeners.crosshair !== 'function') return;
      const index = indexOf(param.time);
      listeners.crosshair(index === undefined || !param.point ? null : {index, source: 'pointer'});
    });
    // LWC applies setVisibleLogicalRange on its next animation frame, and getVisibleLogicalRange returns the
    // old range until then. The renderer keeps the requested range as the visible one until that frame has
    // run, so callers never read a stale or intermediate range (timeframe switch, keyboard, settings).
    const view = doc.defaultView;
    let pending = null, frame = 0;
    const currentLogical = () => pending || chart.timeScale().getVisibleLogicalRange();
    const emitRange = () => { if (!disposed && typeof listeners.range === 'function') { const span = visible(); if (span) listeners.range(span); } };
    // Later layout changes (price-axis width measured at first paint, autosize after a pane-height change)
    // shift the applied range. A requested range holds until the user moves the chart: a range change with
    // no user input since the request is re-applied (bounded), and settle() re-checks a few frames.
    function settle(target, tries) {
      // Registered after LWC's own frame request, so it runs once the range has been applied.
      frame = view.requestAnimationFrame(() => {
        frame = 0;
        if (disposed || pending !== target) return;
        const applied = chart.timeScale().getVisibleLogicalRange();
        if (applied && tries > 0 && (Math.abs(applied.from - target.from) > 0.01 || Math.abs(applied.to - target.to) > 0.01)) {
          chart.timeScale().setVisibleLogicalRange(target); settle(target, tries - 1); return;
        }
        pending = null; emitRange();
      });
    }
    let lastRequest = null;
    const userMoved = () => { if (lastRequest) lastRequest.user = true; };
    for (const type of ['pointerdown', 'wheel', 'touchstart']) host.addEventListener(type, userMoved, {capture: true, passive: true});
    function request(logical) {
      const target = {from: logical.from, to: logical.to};
      lastRequest = {target, user: false, reapplied: 0};
      pending = target;
      chart.timeScale().setVisibleLogicalRange(target);
      if (frame) view.cancelAnimationFrame(frame);
      settle(target, 3);
    }
    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (!range || disposed) return;
      const last = lastRequest;
      if (last && !last.user && pending === null && last.reapplied < 5 && (Math.abs(range.from - last.target.from) > 0.01 || Math.abs(range.to - last.target.to) > 0.01)) {
        last.reapplied++; pending = last.target; chart.timeScale().setVisibleLogicalRange(last.target);
        if (frame) view.cancelAnimationFrame(frame);
        settle(last.target, 3);
      }
      emitRange();
    });

    function setData(model) {
      bars = normalizeBars(model.bars);
      pending = null; lastRequest = null;
      const lines = normalizeLines(model.lines, bars.length);
      byTime.clear(); bars.forEach((bar, i) => byTime.set(bar.time, i));
      for (const item of extra) chart.removeSeries(item.series);
      extra = [];
      if (measureSeries) { chart.removeSeries(measureSeries); measureSeries = null; }
      clearOverlays();
      candles.setData(bars.map(bar => !bar.ohlc ? {time: bar.time} : bar.complete
        ? {time: bar.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close}
        : {time: bar.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close, color: 'rgba(0,0,0,0)', borderColor: c.muted, wickColor: c.muted}));
      volume.setData(bars.map(bar => bar.volume === null ? {time: bar.time}
        : {time: bar.time, value: bar.volume, color: !bar.complete ? alpha(c.muted, 0.25) : bar.ohlc && bar.close < bar.open ? alpha(c.down, 0.45) : alpha(c.up, 0.45)}));
      provisionalMarkers = bars.filter(bar => !bar.complete).map(bar => ({time: bar.time, position: 'aboveBar', shape: 'square', color: c.muted, text: provisionalLabel, size: 0.5}));
      applyMarkers();
      // Declare panes in fixed order so pane indices are stable.
      for (const pane of PANES) for (const line of lines.filter(l => l.pane === pane)) extra.push({pane, line});
      for (const item of extra) {
        const color = item.line.type === 'histogram' ? alpha(c.muted, 0.6) : c.tones[item.line.tone % c.tones.length];
        item.series = chart.addSeries(item.line.type === 'histogram' ? lib.HistogramSeries : lib.LineSeries,
          item.line.type === 'histogram' ? {color, priceLineVisible: false, lastValueVisible: false} : {color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false},
          paneFor(item.pane));
        item.series.setData(item.line.values.map((v, i) => v === null ? {time: bars[i].time} : {time: bars[i].time, value: v}));
      }
      const panes = chart.panes();
      if (panes[0]) panes[0].setStretchFactor(4);
      for (let i = 1; i < panes.length; i++) panes[i].setStretchFactor(i === 1 ? 1 : 1.4);
      return panes.length;
    }

    // Bar i spans logical [i - 0.5, i + 0.5]; a bar counts as visible when its centre is inside the range.
    function visible() {
      const range = currentLogical();
      if (!range || !bars.length) return null;
      let from = Math.ceil(range.from - 1e-6), to = Math.floor(range.to + 1e-6);
      if (from > to) from = to = Math.round((range.from + range.to) / 2);
      return clampRange({from, to}, bars.length);
    }
    function setVisible(range) { const span = clampRange(range, bars.length); if (span) request({from: span.from - 0.5, to: span.to + 0.5}); }
    function zoom(factor) {
      const range = currentLogical(); if (!range) return;
      const center = (range.from + range.to) / 2, half = Math.max(2, (range.to - range.from) / 2 * factor);
      request({from: center - half, to: center + half});
    }
    function scroll(delta) { const range = currentLogical(); if (range) request({from: range.from + delta, to: range.to + delta}); }
    function showCrosshair(index) {
      const bar = bars[index]; if (!bar) return;
      if (bar.ohlc) chart.setCrosshairPosition(bar.close, bar.time, candles); else chart.clearCrosshairPosition();
    }
    function setMeasure(result) {
      if (measureSeries) { chart.removeSeries(measureSeries); measureSeries = null; }
      if (!result) return;
      measureSeries = chart.addSeries(lib.LineSeries, {color: c.pen, lineWidth: 2, lineStyle: lib.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, pointMarkersVisible: true}, 0);
      measureSeries.setData(result.from.time === result.to.time ? [{time: result.from.time, value: result.from.price}] : [{time: result.from.time, value: result.from.price}, {time: result.to.time, value: result.to.price}]);
    }
    // Chart point under a viewport position (price pane only). LWC drops a quick second click, so
    // callers use their own pointer events and ask here; nothing is read back from the library otherwise.
    function pointAt(clientX, clientY) {
      const rect = host.getBoundingClientRect(), x = clientX - rect.left, y = clientY - rect.top, pane = chart.panes()[0];
      if (!bars.length || x < 0 || y < 0 || x > rect.width || !pane || y > pane.getHeight()) return null;
      const logical = chart.timeScale().coordinateToLogical(x), price = candles.coordinateToPrice(y);
      if (logical === null || !positive(price)) return null;
      const index = Math.round(logical);
      return index >= 0 && index < bars.length ? {index, price} : null;
    }
    // Pattern objects: solid lines for official detection, dashed for user-settings exploration, dotted invalidation levels.
    function setOverlays(list) {
      clearOverlays();
      const toneColor = {zone: c.tones[1], box: c.tones[2], double: c.tones[3], invalidation: c.muted, user: c.pen};
      for (const o of normalizeOverlays(list, bars)) {
        const color = o.emphasis === 'dim' ? alpha(toneColor[o.tone], 0.3) : toneColor[o.tone];
        if (o.kind === 'marker') { overlayMarkers.push({time: o.time, position: o.position, shape: o.position === 'belowBar' ? 'arrowUp' : 'arrowDown', color, text: o.label}); continue; }
        const style = o.tone === 'invalidation' ? lib.LineStyle.Dotted : o.source === 'USER' ? lib.LineStyle.LargeDashed : o.source === 'USER_SETTINGS' ? lib.LineStyle.Dashed : lib.LineStyle.Solid;
        const series = chart.addSeries(lib.LineSeries, {color, lineWidth: o.emphasis === 'selected' ? 3 : o.source === 'USER' ? 2 : 1, lineStyle: style, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, pointMarkersVisible: o.kind === 'segment'}, 0);
        series.setData(o.kind === 'segment' ? [{time: o.from, value: o.fromPrice}, {time: o.to, value: o.toPrice}] : [{time: o.from, value: o.price}, {time: o.to, value: o.price}]);
        overlaySeries.push(series);
      }
      applyMarkers();
      return overlaySeries.length + overlayMarkers.length;
    }
    function destroy() { if (disposed) return; disposed = true; if (frame) view.cancelAnimationFrame(frame); frame = 0; pending = null; lastRequest = null; host.removeEventListener('pointerdown', userMoved, {capture: true}); host.removeEventListener('wheel', userMoved, {capture: true}); host.removeEventListener('touchstart', userMoved, {capture: true}); chart.remove(); host.replaceChildren(); }
    return Object.freeze({kind: 'lwc', capabilities: LWC_CAPABILITIES, setData, getVisibleRange: visible, setVisibleRange: setVisible, zoom, scroll,
      fit: () => { if (bars.length) request({from: -0.5, to: bars.length - 0.5}); }, showCrosshair, clearCrosshair: () => chart.clearCrosshairPosition(), setMeasure, setOverlays, pointAt, destroy});
  }

  /* ---------- SVG fallback (existing TechnicalChart, unchanged) ---------- */

  function createSvg(host, options = {}) {
    const view = host.ownerDocument.defaultView;
    let bars = [];
    function setData(model) {
      bars = normalizeBars(model.bars);
      const lines = normalizeLines(model.lines, bars.length).filter(line => line.pane === 'price' && line.type === 'line');
      host.replaceChildren();
      if (!view.TechnicalChart) throw new Error('RENDERER_UNAVAILABLE');
      view.TechnicalChart.render(host, {
        bars: bars.map(bar => ({session_date: bar.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close, session_status: bar.complete ? 'COMPLETE' : bar.status})),
        indicators: {indicators: lines.map(line => ({indicator_id: line.id, values: line.values}))},
        selected: new Set(lines.map(line => line.id)), locale: options.locale
      });
      return 1;
    }
    const all = () => bars.length ? {from: 0, to: bars.length - 1} : null;
    const none = () => {};
    return Object.freeze({kind: 'svg', capabilities: SVG_CAPABILITIES, setData, getVisibleRange: all, setVisibleRange: none, zoom: none, scroll: none, fit: none,
      showCrosshair: none, clearCrosshair: none, setMeasure: none, setOverlays: () => 0, pointAt: () => null, destroy: () => host.replaceChildren()});
  }

  // kind 'lwc' resolves to the LWC renderer or rejects with RENDERER_UNAVAILABLE; callers fall back to 'svg'.
  async function create(host, kind, options = {}) {
    if (kind === 'svg') return createSvg(host, options);
    const lib = await loadLibrary(host.ownerDocument.defaultView);
    if (!host.isConnected) throw new Error('RENDERER_DETACHED');
    return createLwc(host, lib, options);
  }

  return Object.freeze({LWC_VERSION, LWC_FILE, LWC_INTEGRITY, LWC_CAPABILITIES, SVG_CAPABILITIES, normalizeBars, normalizeLines, normalizeOverlays, clampRange, mapRange, measure, calendarDays, create, loadLibrary});
});
