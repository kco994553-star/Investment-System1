'use strict';
(() => {
  const sample = window.COMPANY_SAMPLE || {};
  const $ = id => document.getElementById(id);
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const add = (parent, tag, text, cls) => { const node = make(tag, text, cls); parent.append(node); return node; };
  const available = value => value && value.status === 'AVAILABLE';
  const percentFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });
  const percent = value => value === null || value === undefined || !Number.isFinite(Number(value)) ? 'Unavailable' : percentFormat.format(Number(value)) + '%';
  const reasons = value => (value && Array.isArray(value.reason_codes) && value.reason_codes.length) ? value.reason_codes.join(' · ') : 'No validated projection supplied';
  const kindResult = kind => sample[kind === 'ANNUAL' ? 'annual' : 'quarterly'];
  const localURL = (file, params) => file + '?' + new URLSearchParams(params).toString();
  const currency = available(sample.price_position) ? (((sample.price_position.evidence || {}).bindings || {}).currency || '') : '';
  const price = value => value === null || value === undefined ? 'Unavailable' : (currency === 'USD' ? '$' : currency + ' ') + String(value);

  function renderPrices(target) {
    target.replaceChildren();
    const projection = sample.price_position;
    if (!available(projection)) {
      const card = add(target, 'div', undefined, 'card');
      add(card, 'p', 'Unavailable', 'unavailable');
      add(card, 'p', reasons(projection), 'note');
      return;
    }
    const values = projection.values || {};
    for (const [field, label, formatter] of [
      ['current_price', 'Current price', price],
      ['historical_ath', 'Historical ATH', price],
      ['percent_from_ath', 'Position from ATH', percent],
      ['high_52w', '52-week high', price],
      ['percent_from_high_52w', 'Position from 52-week high', percent],
    ]) {
      const card = add(target, 'div', undefined, 'card');
      add(card, 'div', label, 'metric-label');
      add(card, 'p', formatter(values[field]), 'metric-value');
      add(card, 'p', 'Synthetic · same declared price basis', 'metric-meta');
    }
  }

  function renderChart(target, projection, kind) {
    target.replaceChildren();
    if (!available(projection) || !Array.isArray(projection.bars) || !projection.bars.length) return;
    const bars = projection.bars;
    const values = bars.map(bar => Number(bar.return_percent));
    if (values.some(value => !Number.isFinite(value))) {
      add(target, 'p', 'Unavailable: invalid chart projection', 'unavailable');
      return;
    }
    // Geometry only. Returns, direction and denominator come from the adapter.
    const ns = 'http://www.w3.org/2000/svg';
    const svgNode = (tag, attrs, text) => {
      const node = document.createElementNS(ns, tag);
      for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, String(value));
      if (text !== undefined) node.textContent = text;
      return node;
    };
    const width = Math.max(520, bars.length * 110 + 48);
    const height = 245, baseline = 110, maxMagnitude = Math.max(1, ...values.map(Math.abs));
    const slot = (width - 50) / bars.length;
    const svg = svgNode('svg', { viewBox: `0 0 ${width} ${height}`, role: 'group', 'aria-label': `${kind} return bars with 0% baseline; each bar opens period detail` });
    svg.append(svgNode('line', { x1: 30, x2: width - 10, y1: baseline, y2: baseline, class: 'baseline' }));
    svg.append(svgNode('text', { x: 0, y: baseline + 4, class: 'axis-label' }, '0%'));
    bars.forEach((bar, index) => {
      const value = values[index], center = 30 + slot * (index + .5);
      const barHeight = Math.abs(value) / maxMagnitude * 74;
      const y = value >= 0 ? baseline - barHeight : baseline;
      const link = svgNode('a', {
        href: localURL('detail.html', { kind, period: bar.period_id }),
        tabindex: '0', role: 'link',
        class: (bar.direction || '') + (bar.historical_denominator ? '' : ' partial'),
        'aria-label': `${bar.label}: ${percent(bar.return_percent)}; ${bar.direction}; ${bar.historical_denominator ? 'completed full period' : bar.display_kind + ', excluded from denominator'}. Open detail`,
      });
      link.append(svgNode('rect', { x: center - slot / 2 + 4, y: 14, width: slot - 8, height: 223, class: 'focus-area' }));
      link.append(svgNode('title', {}, `${bar.label} · ${bar.direction} · ${percent(bar.return_percent)}`));
      link.append(svgNode('rect', { x: center - 20, y: barHeight ? y : baseline - 1, width: 40, height: Math.max(2, barHeight), class: 'bar' }));
      link.append(svgNode('text', { x: center, y: value >= 0 ? y - 9 : y + barHeight + 18, 'text-anchor': 'middle' }, percent(bar.return_percent)));
      link.append(svgNode('text', { x: center, y: 213, 'text-anchor': 'middle' }, bar.label));
      link.append(svgNode('text', { x: center, y: 230, 'text-anchor': 'middle', class: 'axis-label' }, bar.historical_denominator ? 'Full period' : bar.display_kind + ' · excluded'));
      svg.append(link);
    });
    target.append(svg);
    const legend = add(target, 'div', undefined, 'chart-legend');
    for (const [cls, text] of [['positive', 'Positive'], ['negative', 'Negative'], ['flat', 'Flat'], ['partial', 'Partial period · excluded']]) add(legend, 'span', text, cls);
  }

  function renderSummary(target, projection) {
    target.replaceChildren();
    target.dataset.status = projection && projection.status || 'NOT_AVAILABLE';
    if (!available(projection)) {
      add(target, 'span', 'Unavailable', 'unavailable');
      add(target, 'span', ' · ' + reasons(projection), 'note');
      return;
    }
    add(target, 'strong', `${projection.positive_count} / ${projection.completed_count}`);
    add(target, 'span', ` completed full periods were positive (${percent(projection.positive_rate_percent)}).`);
  }

  function table(parent, rows) {
    const wrap = add(parent, 'div', undefined, 'table-wrap');
    const node = add(wrap, 'table');
    for (const [name, value] of rows) {
      const tr = add(node, 'tr');
      const th = add(tr, 'th', name); th.scope = 'row';
      add(tr, 'td', value === undefined || value === null ? 'Unavailable' : String(value));
    }
    return node;
  }

  function overview() {
    const company = sample.company || {};
    $('company-name').textContent = company.name || 'Company unavailable';
    $('company-subtitle').textContent = `${company.symbol || 'Unavailable'} · Synthetic example · Company Analysis`;
    const stamp = $('data-stamp');
    const bindings = available(sample.price_position) ? ((sample.price_position.evidence || {}).bindings || {}) : {};
    const current = available(sample.price_position) ? ((((sample.price_position.evidence || {}).operands || {}).current) || {}) : {};
    for (const text of [`Decision time: ${sample.decision_time || 'Unavailable'}`, `Security: ${company.security_ref || 'Unavailable'}`, `Snapshot: ${current.effective_at || 'Unavailable'}`, `Available at: ${current.available_at || 'Unavailable'}`, `Basis: ${bindings.price_basis || 'Unavailable'}`, `Actions receipt: ${bindings.corporate_action_receipt || 'Unavailable'}`, 'Projection: company-price-context-v1']) add(stamp, 'span', text);
    renderPrices($('price-position'));
    for (const [key, kind] of [['quarterly', 'QUARTERLY'], ['annual', 'ANNUAL']]) {
      renderSummary($(key + '-summary'), sample[key]);
      renderChart($(key + '-chart'), sample[key], kind);
    }
  }

  function detail() {
    const params = new URLSearchParams(location.search);
    const view = params.get('view');
    const content = $('detail-content');
    $('detail-subtitle').textContent = `${(sample.company || {}).name || 'Company unavailable'} · synthetic example only`;
    if (view === 'full-chart') {
      $('detail-title').textContent = 'Full Technical Chart';
      const card = add(content, 'div', undefined, 'card');
      add(card, 'h2', 'Not assembled in this offline preview');
      add(card, 'p', 'The existing full Technical Chart is not connected to this sidecar. No production Chart route or runtime API is attached.');
      add(card, 'p', 'Period bars and evidence are available through the local overview and detail pages.', 'note');
      return;
    }
    if (view === 'thesis') {
      $('detail-title').textContent = 'Q / G / V thesis recheck';
      for (const [id, title, text] of [
        ['quality', 'Q · Quality', 'Business resilience, financial quality and competitive evidence are unavailable.'],
        ['growth', 'G · Growth', 'Growth drivers and source-backed forward evidence are unavailable.'],
        ['valuation', 'V · Valuation', 'Existing valuation inputs and approved profile evidence are unavailable.'],
        ['news-events', 'News / Event', 'Existing source/time-stamped news and event records are unavailable.'],
        ['vmr', 'VMR / Scenario', 'Current VMR and scenario authority are unavailable.'],
      ]) {
        const card = add(content, 'section', undefined, 'card detail-card'); card.id = id;
        add(card, 'h2', title); add(card, 'p', 'Unavailable', 'unavailable'); add(card, 'p', text);
      }
      add(content, 'p', 'Historical price context does not change QGV raw scores, create economic credit or produce a buy/sell instruction.', 'note');
      return;
    }
    if (view === 'price' || !params.has('kind')) {
      $('detail-title').textContent = 'Historical price position';
      const prices = add(content, 'div', undefined, 'grid'); renderPrices(prices);
      const inputs = (sample.source_inputs || {}).price_position || {};
      table(content, [['Decision time', sample.decision_time], ['Price basis', (inputs.current || {}).price_basis], ['Corporate-action receipt', (inputs.current || {}).corporate_action_receipt], ['Lifetime coverage', (inputs.ath || {}).coverage_ref], ['52-week window contract', (inputs.high_52w || {}).window_contract_ref], ['52-week start', (inputs.high_52w || {}).window_start], ['52-week end', (inputs.high_52w || {}).window_end]]);
      add(content, 'p', 'Same-basis supplied operands are validated by the adapter. General, company, type-peer, GICS-peer and Current VMR drawdown contexts remain separate and unavailable; numeric bands are inactive.', 'note');
      return;
    }
    const kind = params.get('kind') === 'ANNUAL' ? 'ANNUAL' : 'QUARTERLY';
    const projection = kindResult(kind);
    const selectedID = params.get('period');
    $('detail-title').textContent = kind === 'ANNUAL' ? 'Annual period detail' : 'Quarterly period detail';
    if (!available(projection)) { add(content, 'p', 'Unavailable · ' + reasons(projection), 'unavailable'); return; }
    const bars = projection.bars || [];
    const selected = selectedID ? bars.find(bar => bar.period_id === selectedID) : null;
    $('detail-evidence').href = localURL('evidence.html', { kind, ...(selectedID ? { period: selectedID } : {}) });
    if (selectedID && !selected) { add(content, 'p', 'Unavailable: requested period is not in the validated projection.', 'unavailable'); return; }
    if (!selected) {
      const summary = add(content, 'p', undefined, 'period-summary'); renderSummary(summary, projection);
      const chart = add(content, 'div', undefined, 'chart card'); renderChart(chart, projection, kind);
      const list = add(content, 'div', undefined, 'detail-links');
      for (const bar of bars) { const a = add(list, 'a', bar.label + ' · ' + percent(bar.return_percent)); a.href = localURL('detail.html', { kind, period: bar.period_id }); }
      return;
    }
    const input = ((sample.source_inputs || {})[kind === 'ANNUAL' ? 'annual' : 'quarterly'] || {});
    const row = (input.periods || []).find(period => period.period_id === selected.period_id) || {};
    const card = add(content, 'div', undefined, 'card');
    add(card, 'h2', selected.label);
    table(card, [['Return', percent(selected.return_percent)], ['Direction', selected.direction], ['Period kind', selected.display_kind], ['Historical denominator', selected.historical_denominator ? 'Included · completed full period' : 'Excluded · partial period'], ['Start', row.start_at], ['End', row.end_at], ['Available at', row.available_at], ['Calendar reference', input.calendar_ref], ['Source reference', selected.source_ref], ['Start / end prices', 'Unavailable'], ['High / low', 'Unavailable'], ['Maximum drawdown', 'Unavailable'], ['Existing events', 'Unavailable']]);
    add(content, 'p', 'Additional period facts require separately admitted evidence. No start/end price, intraperiod drawdown or event is inferred from the period return.', 'note');
  }

  function evidence() {
    const content = $('evidence-content');
    const provenance = sample.provenance || {};
    const stamp = add(content, 'section', undefined, 'card detail-card');
    add(stamp, 'h2', 'Projection boundary');
    table(stamp, [['Decision time', sample.decision_time], ['Input SHA-256', provenance.input_sha256], ['Adapter SHA-256', provenance.adapter_sha256], ['Contract SHA-256', provenance.contract_sha256], ['Field contract SHA-256', provenance.field_contract_sha256], ['QGV raw score input', 'false'], ['Source admission', 'false'], ['Runtime route attachment', 'Not implemented / not activated']]);
    const params = new URLSearchParams(location.search), kind = params.get('kind'), periodID = params.get('period');
    if (periodID && ['ANNUAL', 'QUARTERLY'].includes(kind)) {
      const inputs = (sample.source_inputs || {})[kind === 'ANNUAL' ? 'annual' : 'quarterly'] || {};
      const row = (inputs.periods || []).find(period => period.period_id === periodID);
      if (row) {
        const card = add(content, 'section', undefined, 'card detail-card');
        add(card, 'h2', 'Selected period evidence · ' + row.label);
        add(card, 'pre', JSON.stringify(row, null, 2));
      }
    }
    for (const [key, title] of [['price_position', 'Historical price operands'], ['quarterly', 'Quarterly calendar / roster / periods'], ['annual', 'Annual calendar / roster / periods']]) {
      const card = add(content, 'section', undefined, 'card detail-card');
      add(card, 'h2', title);
      const output = sample[key] || {};
      add(card, 'p', `${output.status || 'NOT_AVAILABLE'} · synthetic source refs only`, available(output) ? '' : 'unavailable');
      const projected = add(card, 'details'); add(projected, 'summary', 'Validated adapter projection'); add(projected, 'pre', JSON.stringify(output, null, 2));
      const input = add(card, 'details'); add(input, 'summary', 'Supplied input, coverage & time stamps'); add(input, 'pre', JSON.stringify((sample.source_inputs || {})[key] || {}, null, 2));
    }
  }

  if (document.body.dataset.page === 'overview') overview();
  if (document.body.dataset.page === 'detail') detail();
  if (document.body.dataset.page === 'evidence') evidence();
})();
