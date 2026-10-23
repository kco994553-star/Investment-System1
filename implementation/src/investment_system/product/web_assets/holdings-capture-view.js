/* "내 증권사 연결 방법" guide and the capture + personal AI flow (Holdings tab). Rows, prices and P&L stay in this window's RAM.
   Sheet writes: only creating the Holdings tab (header + plain-text cells) on the user's click; existing tabs are never modified. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HoldingsCaptureView = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const QUOTES_RANGE = "'Quotes'!A1:C1025", DECIMAL = /^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/;
  const US_PREFIXES = ['NASDAQ', 'NYSE', 'NYSEARCA', 'NYSEAMERICAN', 'BATS'];
  const REASONS = {
    COLUMN_COUNT: ['열 개수가 7개를 넘음', 'More than 7 columns'], AS_OF_MISSING: ['기준일 없음', 'as_of missing'], AS_OF_FORMAT: ['기준일 형식 아님(YYYY-MM-DD)', 'as_of is not YYYY-MM-DD'],
    AS_OF_MISMATCH: ['다른 기준일', 'Different as_of'], SYMBOL_MISSING: ['종목 없음', 'symbol missing'], SYMBOL_FORMAT: ['종목 형식 아님', 'symbol format'],
    QUANTITY_MISSING: ['수량 없음', 'quantity missing'], QUANTITY_FORMAT: ['수량 숫자 형식 아님', 'quantity number format'], QUANTITY_NOT_POSITIVE: ['수량 0', 'quantity is 0'],
    AVG_COST_FORMAT: ['평균단가 숫자 형식 아님', 'avg_cost number format'], COST_KRW_FORMAT: ['원화 매입금액 숫자 형식 아님', 'cost_krw number format'],
    CURRENCY_MISSING: ['통화 없음', 'currency missing'], CURRENCY_FORMAT: ['통화 형식 아님', 'currency format'], CURRENCY_MISMATCH: ['시장과 통화 불일치', 'currency does not match the market'],
    CASH_AVG_COST_PRESENT: ['현금 줄에 평균단가', 'avg_cost on a cash row'], NAME_FORMAT: ['종목명 형식', 'name format'], COST_RANGE: ['평균단가 계산 범위 초과', 'average cost out of range'],
    DUPLICATE_SYMBOL: ['같은 종목 여러 줄', 'duplicate symbol'], COST_NOT_AVAILABLE: ['평균단가 근거 없음 · ACTUAL 미반영', 'no cost basis · not in ACTUAL']
  };
  const states = new WeakMap();
  function words(locale, ko, en) { return locale === 'en-US' ? en : ko; }
  function make(doc, tag, text, attrs = {}) {
    const node = doc.createElement(tag); if (text !== undefined && text !== null) node.textContent = text;
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value)); return node;
  }
  function format(locale, value, digits = 6) { return new Intl.NumberFormat(locale, {maximumFractionDigits: digits}).format(value); }
  function reasonText(locale, code) { return code + (REASONS[code] ? ' · ' + REASONS[code][locale === 'en-US' ? 1 : 0] : ''); }
  function basisText(locale, basis) {
    return basis === 'COST_KRW_DIV_QTY' ? words(locale, 'cost_krw ÷ quantity', 'cost_krw ÷ quantity')
      : basis === 'AVG_COST_FIELD' ? words(locale, 'avg_cost (cost_krw 없음)', 'avg_cost (cost_krw empty)') : 'NOT_AVAILABLE';
  }
  function sessionOf(view, config) {
    try { return config && config.googleSheetsClientId && view.GoogleSheetQuotes ? view.GoogleSheetQuotes.sessionFor(view, config.googleSheetsClientId) : null; } catch (_) { return null; }
  }
  async function sheetId(view) {
    try { const unified = view.GoogleSheetSetup ? view.GoogleSheetSetup.source(view) : ''; if (unified) return unified; } catch (_) { /* fall through */ }
    try { const settings = await view.DeviceActual.sheetSettings(view); return settings.spreadsheet_id || ''; } catch (_) { return ''; }
  }
  function strictPrice(value) {
    const text = typeof value === 'number' ? (Number.isFinite(value) && value > 0 && !/e/i.test(String(value)) ? String(value) : '') : typeof value === 'string' ? value.trim() : '';
    return DECIMAL.test(text) && Number(text) > 0 ? text : null;
  }
  function codesFor(position) {
    if (position.market === 'KRX') return ['KRX:' + position.symbol];
    if (position.market === 'TSE') return ['TYO:' + position.symbol];
    return US_PREFIXES.map(prefix => prefix + ':' + position.symbol);
  }
  // Out-of-scope prices: a unique sheet Quotes row for the symbol, else the Worker when the symbol is on its allowlist.
  // fetch false (the automatic read on return to the app): no Worker request; such a symbol is PRICE_NOT_FETCHED until the
  // user presses 'Holdings 탭 읽기' (owner decision 2026-10-23: price requests only from a button).
  async function outsideQuotes(view, {positions, values, config, session, readAt, fetch = true}) {
    const result = {}, allow = new Set(view.GoogleSheetQuotes && view.GoogleSheetQuotes.HISTORY_SYMBOLS || []);
    for (const position of positions) {
      const codes = new Set(codesFor(position)), rows = (values || []).filter(row => Array.isArray(row) && typeof row[0] === 'string' && codes.has(row[0].trim()));
      const price = rows.length === 1 ? strictPrice(rows[0][1]) : null;
      // D10: the Quotes row has no parsed trade time here, so the price time is unconfirmed; readAt is only the read time.
      if (price !== null) { result[position.symbol] = {state: 'AVAILABLE', price, currency: position.currency, source: 'GOOGLEFINANCE', time_status: 'UNKNOWN', as_of: readAt, available_at: readAt}; continue; }
      const target = view.WorkerQuoteFallback ? view.WorkerQuoteFallback.workerSymbol(position.symbol) : null;
      if (!target || !allow.has(target)) { result[position.symbol] = {state: 'NOT_AVAILABLE', reason: 'QUOTE_NOT_AVAILABLE_OUT_OF_SCOPE'}; continue; }
      if (!fetch) { result[position.symbol] = {state: 'NOT_AVAILABLE', reason: 'PRICE_NOT_FETCHED'}; continue; }
      const close = await view.WorkerQuoteFallback.readClose(view, {symbol: position.symbol, currency: position.currency, config, session});
      result[position.symbol] = close.state === 'AVAILABLE'
        ? {state: 'AVAILABLE', price: close.price, currency: close.currency, source: 'WORKER_CLOSE', time_status: 'SESSION_CLOSE', as_of: close.session_date + 'T00:00:00Z', available_at: new Date().toISOString()}
        : {state: 'NOT_AVAILABLE', reason: close.reason};
    }
    return result;
  }
  async function readTab(state, {fetch = true} = {}) {
    const {view, config} = state, session = sessionOf(view, config);
    if (!session || !session.state().connected) return fail(state, 'AUTH_REQUIRED');
    const id = await sheetId(view); if (!id) return fail(state, 'SHEET_SOURCE_REQUIRED');
    const revision = session.revision(), current = () => live(state) && session.revision() === revision && session.state().connected;
    state.busy = true; paintButtons(state); say(state, words(state.locale, 'Holdings 탭을 읽는 중…', 'Reading the Holdings tab…'), 'READING');
    try {
      const payload = await session.fetchValues(id, view.HoldingsCapture.RANGE, {maxBytes: 1048576});
      if (!current()) return;
      const parsed = view.HoldingsCapture.parse(payload.values), readAt = new Date().toISOString();
      let outside = {};
      if (parsed.state === 'OK') {
        const catalog = state.catalog, split = view.HoldingsCapture.toActual(parsed, catalog);
        if (split.out_of_scope.length) {
          let quotes = [];
          try { quotes = (await session.fetchValues(id, QUOTES_RANGE, {maxBytes: 1048576})).values; } catch (_) { quotes = []; }
          if (!current()) return;
          outside = await outsideQuotes(view, {positions: split.out_of_scope, values: quotes, config, session, readAt, fetch});
          if (!current()) return;
        }
      }
      view.HoldingsCapture.set(view, {parsed, read_at: readAt, outside});
      watchSession(state, session);
      say(state, parsed.state === 'OK' ? words(state.locale, 'Holdings 탭을 읽었습니다. RAM 전용 · 저장하지 않음.', 'Read the Holdings tab. RAM only · not stored.') : 'HOLDINGS_' + parsed.state, parsed.state === 'OK' ? 'READ' : 'HOLDINGS_' + parsed.state);
    } catch (error) {
      if (!live(state)) return;
      const code = error && error.message === 'READ_FAILED' ? 'HOLDINGS_TAB_NOT_READ' : error && /^[A-Z_]{3,40}$/.test(error.message) ? error.message : 'HOLDINGS_TAB_NOT_READ';
      say(state, code + (code === 'HOLDINGS_TAB_NOT_READ' ? words(state.locale, ' · Holdings 탭이 없거나 읽을 수 없습니다. [시트 Holdings 탭 열기]를 먼저 누르세요.', ' · The Holdings tab is missing or unreadable. Press [Open sheet Holdings tab] first.') : ''), code);
    } finally { state.busy = false; if (live(state)) { paintButtons(state); preview(state); } }
  }
  function watchSession(state, session) {
    const view = state.view; if (state.unsubscribe) return;
    state.unsubscribe = session.subscribe(() => { if (!session.state().connected) { view.HoldingsCapture.clear(view); } });
  }
  async function openTab(state) {
    const {view, config} = state, session = sessionOf(view, config);
    if (!session || !session.state().connected) return fail(state, 'AUTH_REQUIRED');
    const id = await sheetId(view); if (!id) return fail(state, 'SHEET_SOURCE_REQUIRED');
    state.busy = true; paintButtons(state); say(state, words(state.locale, 'Holdings 탭 확인 중…', 'Checking the Holdings tab…'), 'PREPARING');
    try {
      const tab = await session.addHoldingsTab(id);
      if (!live(state)) return;
      state.awaiting = true;
      say(state, (tab.created ? words(state.locale, 'Holdings 탭을 만들었습니다(머리글·텍스트 서식). ', 'Created the Holdings tab (header, plain-text cells). ') : words(state.locale, 'Holdings 탭이 이미 있어 수정하지 않았습니다. ', 'The Holdings tab already exists and was not modified. '))
        + words(state.locale, '열린 시트 하단의 Holdings 탭 A1에 AI 답(머리글 포함)을 붙여넣고 이 앱으로 돌아오세요.', 'Paste the AI answer (with header) into cell A1 of the Holdings tab, then return to this app.'), tab.created ? 'TAB_CREATED' : 'TAB_EXISTS');
    } catch (error) {
      if (live(state)) say(state, error && /^[A-Z_]{3,40}$/.test(error.message) ? error.message : 'WRITE_FAILED', error && /^[A-Z_]{3,40}$/.test(error.message) ? error.message : 'WRITE_FAILED');
    } finally { state.busy = false; if (live(state)) paintButtons(state); }
  }
  function fail(state, code) {
    const hint = code === 'AUTH_REQUIRED' ? words(state.locale, ' · 설정 → Google 첫 설정에서 구글 로그인을 먼저 하세요.', ' · Sign in under Settings → Google first setup first.')
      : code === 'SHEET_SOURCE_REQUIRED' ? words(state.locale, ' · 설정 → Google 첫 설정에서 시트를 만들거나 연결하세요.', ' · Create or connect a sheet under Settings → Google first setup.') : '';
    say(state, code + hint, code);
  }
  function say(state, text, code) { if (!live(state)) return; state.status.textContent = text; state.status.dataset.code = code; }
  function live(state) { return state.host.isConnected && states.get(state.host) === state; }
  function paintButtons(state) { for (const button of [state.copy, state.open, state.read, state.clear]) button.disabled = state.busy; }
  async function copyPrompt(state) {
    const asOf = state.view.HoldingsCapture.seoulDate(), text = state.view.HoldingsCapture.prompt(asOf);
    state.asOf.textContent = words(state.locale, '기준일 ', 'As-of ') + asOf + ' (Asia/Seoul)';
    try { await state.view.navigator.clipboard.writeText(text); say(state, words(state.locale, '프롬프트를 복사했습니다(기준일 ', 'Prompt copied (as-of ') + asOf + words(state.locale, '). 본인 AI 새 대화에 캡처와 함께 붙여넣으세요.', '). Paste it with the screenshot into a new chat with your own AI.'), 'PROMPT_COPIED'); state.manual.hidden = true; }
    catch (_) { state.manualText.value = text; state.manual.hidden = false; say(state, words(state.locale, '자동 복사를 할 수 없어 아래 칸에 표시했습니다. 직접 복사하세요.', 'Automatic copy is unavailable; the prompt is shown below to copy by hand.'), 'PROMPT_SHOWN'); }
  }
  // Preview of the last read Holdings tab (RAM).
  function preview(state) {
    const {view, doc, locale} = state, entry = view.HoldingsCapture.get(view);
    state.preview.replaceChildren();
    if (!entry) { state.preview.append(make(doc, 'p', words(locale, 'Holdings 탭을 아직 읽지 않았습니다.', 'The Holdings tab has not been read yet.'), {class: 'small', 'data-capture-preview-empty': ''})); return; }
    const parsed = entry.parsed, box = make(doc, 'div', null, {'data-capture-preview': parsed.state});
    box.append(make(doc, 'h4', words(locale, '미리보기 · Holdings 탭 · RAM 전용', 'Preview · Holdings tab · RAM only')));
    if (parsed.state !== 'OK') {
      box.append(make(doc, 'p', 'HOLDINGS_' + parsed.state + ' · ' + (parsed.state === 'HEADER_MISMATCH' ? words(locale, '첫 행은 정확히 ', 'The first row must be exactly ') + view.HoldingsCapture.HEADER.join(', ') + words(locale, ' 이어야 합니다. 아무 줄도 읽지 않았습니다.', '. No rows were read.') : words(locale, '읽을 줄이 없습니다.', 'No rows to read.')), {role: 'status'}));
      state.preview.append(box); return;
    }
    let split = null; try { split = view.HoldingsCapture.toActual(parsed, state.catalog); } catch (_) { split = null; }
    box.append(make(doc, 'p', 'as_of ' + (parsed.as_of || 'NOT_AVAILABLE') + ' · ' + words(locale, '종목 ', 'Positions ') + parsed.positions.length + ' · ' + words(locale, '현금 ', 'Cash ') + parsed.cash.length + ' · ' + words(locale, '확인 필요 ', 'Needs review ') + (split ? split.review.length : parsed.review.length) + ' · ' + words(locale, '읽은 시각 ', 'read at ') + entry.read_at, {'data-capture-counts': ''}));
    if (parsed.positions.length) {
      const wrap = make(doc, 'div', null, {class: 'table-wrap'}), table = make(doc, 'table', null, {'data-capture-positions': ''}), head = make(doc, 'tr');
      for (const label of [words(locale, '행', 'Row'), 'symbol', 'name', 'quantity', words(locale, '평균단가', 'Average cost'), words(locale, '근거', 'Basis'), words(locale, '범위', 'Scope')]) head.append(make(doc, 'th', label, {scope: 'col'}));
      const thead = make(doc, 'thead'), body = make(doc, 'tbody'); thead.append(head);
      const inScope = new Set(split ? split.in_scope.map(item => item.row) : []);
      for (const position of parsed.positions) {
        const tr = make(doc, 'tr', null, {'data-capture-row': position.row});
        const scope = inScope.has(position.row) ? words(locale, '분석 대상 19', 'Analysis 19') : split && split.out_of_scope.some(item => item.row === position.row) ? words(locale, '분석 범위 밖', 'Outside analysis scope') : words(locale, '확인 필요', 'Needs review');
        for (const value of [String(position.row), position.symbol, position.name || '—', position.quantity, position.average_cost === null ? 'NOT_AVAILABLE' : position.average_cost + ' ' + position.average_cost_currency, basisText(locale, position.cost_basis), scope]) tr.append(make(doc, 'td', value));
        body.append(tr);
      }
      table.append(thead, body); wrap.append(table); box.append(wrap);
    }
    for (const cash of parsed.cash) box.append(make(doc, 'p', words(locale, '현금 ', 'Cash ') + cash.symbol + ' · ' + cash.amount + ' ' + cash.currency + (cash.cost_krw !== null ? ' · KRW ' + cash.cost_krw : ''), {'data-capture-cash': cash.symbol}));
    const review = split ? split.review : parsed.review;
    if (review.length) {
      const list = make(doc, 'ul', null, {'data-capture-review': ''});
      for (const item of review) list.append(make(doc, 'li', words(locale, '확인 필요 · ', 'Needs review · ') + words(locale, '행 ', 'row ') + item.row + ' · ' + item.reason_codes.map(code => reasonText(locale, code)).join(' / '), {'data-review-row': item.row}));
      box.append(make(doc, 'p', words(locale, '아래 줄은 읽지 않았습니다. 시트에서 고친 뒤 다시 읽으세요. 빈 숫자는 0으로 채우지 않습니다.', 'These rows were not read. Fix them in the sheet and read again. Missing numbers are never filled with 0.'), {class: 'small'}), list);
    }
    state.preview.append(box);
  }
  function mountGuide(host, {catalog, locale = 'ko-KR', config = {}} = {}) {
    const doc = host.ownerDocument, view = doc.defaultView, old = states.get(host);
    if (old) old.dispose();
    const state = {host, doc, view, catalog, locale, config, busy: false, awaiting: false, unsubscribe: null};
    states.set(host, state);
    const root = make(doc, 'section', null, {class: 'card broker-guide', 'data-broker-guide': ''});
    root.append(make(doc, 'h3', words(locale, '내 증권사 연결 방법', 'How to connect my brokerage')),
      make(doc, 'p', words(locale, '증권사 계정·비밀번호는 이 앱에 넣지 않습니다. 아래 방법 중 하나로 보유를 이 기기에서만 다룹니다.', 'Brokerage credentials never enter this app. Use one of the methods below; holdings stay on this device.')));
    const methods = make(doc, 'ol', null, {'data-broker-methods': ''});
    methods.append(make(doc, 'li', words(locale, '직접 입력 · 아래 입력 칸에 수량·평균 매입가를 넣고 이 기기에 저장', 'Manual entry · enter quantity and average cost below and save on this device')),
      make(doc, 'li', words(locale, 'JSON 가져오기 · 이 앱에서 내보낸 백업 파일', 'Import JSON · a backup exported from this app')));
    const capture = make(doc, 'li', null, {'data-broker-method': 'capture-ai'});
    capture.append(make(doc, 'strong', words(locale, '캡처 + 개인 AI', 'Screenshot + personal AI')),
      make(doc, 'p', words(locale, '① 증권사 앱 잔고 화면을 캡처합니다. ② [프롬프트 복사] 후 본인 AI 새 대화에 캡처와 함께 붙여넣습니다. ③ [시트 Holdings 탭 열기]로 연결된 시트를 열고 AI 답을 Holdings 탭 A1에 붙여넣습니다. ④ 앱으로 돌아오면 미리보기가 나옵니다. 읽은 보유는 RAM에만 있고 저장·전송하지 않습니다.',
        '1 Capture the balance screen in your brokerage app. 2 Press [Copy prompt] and paste it with the screenshot into a new chat with your own AI. 3 Press [Open sheet Holdings tab] and paste the AI answer into cell A1 of the Holdings tab. 4 Back in the app, a preview appears. Read holdings stay in RAM only; nothing is stored or sent.'), {class: 'small'}));
    state.asOf = make(doc, 'p', words(locale, '기준일 ', 'As-of ') + view.HoldingsCapture.seoulDate() + ' (Asia/Seoul) · ' + view.HoldingsCapture.PROMPT_VERSION, {'data-capture-as-of': ''});
    const actions = make(doc, 'div', null, {class: 'actual-actions'});
    state.copy = make(doc, 'button', words(locale, '프롬프트 복사', 'Copy prompt'), {type: 'button', 'data-capture-action': 'copy'});
    state.open = make(doc, 'button', words(locale, '시트 Holdings 탭 열기', 'Open sheet Holdings tab'), {type: 'button', 'data-capture-action': 'open'});
    state.read = make(doc, 'button', words(locale, 'Holdings 탭 다시 읽기', 'Read Holdings tab again'), {type: 'button', 'data-capture-action': 'read'});
    state.clear = make(doc, 'button', words(locale, '읽은 Holdings 지우기 (RAM)', 'Clear read Holdings (RAM)'), {type: 'button', 'data-capture-action': 'clear'});
    actions.append(state.copy, state.open, state.read, state.clear);
    state.manual = make(doc, 'div', null, {'data-capture-manual': ''}); state.manual.hidden = true;
    const manualLabel = make(doc, 'label', words(locale, '프롬프트 (직접 복사)', 'Prompt (copy by hand)'));
    state.manualText = make(doc, 'textarea', null, {rows: '8', readonly: '', 'data-capture-prompt': ''}); manualLabel.append(state.manualText); state.manual.append(manualLabel);
    state.status = make(doc, 'p', '', {role: 'status', 'aria-live': 'polite', 'data-capture-status': ''});
    state.preview = make(doc, 'div', null, {'data-capture-preview-host': ''});
    capture.append(state.asOf, actions, state.manual, state.status, state.preview); methods.append(capture); root.append(methods);
    host.replaceChildren(root);
    state.copy.addEventListener('click', () => { void copyPrompt(state); });
    state.open.addEventListener('click', () => {
      if (state.busy) return;
      const session = sessionOf(view, config);
      if (!session || !session.state().connected) { fail(state, 'AUTH_REQUIRED'); return; }
      // Open synchronously with the click (pop-up rules); the Holdings tab check/creation follows.
      openWindow(state); void openTab(state);
    });
    state.read.addEventListener('click', () => { void readTab(state); });
    state.clear.addEventListener('click', () => { view.HoldingsCapture.clear(view); say(state, words(locale, 'RAM의 Holdings를 지웠습니다.', 'Cleared Holdings from RAM.'), 'CLEARED'); preview(state); });
    const back = () => { if (!live(state)) { state.dispose(); return; } if (doc.visibilityState === 'visible' && state.awaiting && !state.busy) { state.awaiting = false; void readTab(state, {fetch: false}); } };
    const changed = () => { if (!live(state)) { state.dispose(); return; } preview(state); };
    doc.addEventListener('visibilitychange', back); view.addEventListener('focus', back); doc.addEventListener('device-actual-changed', changed);
    state.dispose = () => { doc.removeEventListener('visibilitychange', back); view.removeEventListener('focus', back); doc.removeEventListener('device-actual-changed', changed); if (state.unsubscribe) state.unsubscribe(); if (states.get(host) === state) states.delete(host); };
    preview(state);
  }
  function openWindow(state) {
    // The connected sheet ID comes from device settings; the URL is opened, never logged or stored here.
    let id = '';
    try { id = state.view.GoogleSheetSetup ? state.view.GoogleSheetSetup.source(state.view) : ''; } catch (_) { id = ''; }
    if (!id || !/^[A-Za-z0-9_-]{20,100}$/.test(id)) return;
    try { state.view.open('https://docs.google.com/spreadsheets/d/' + encodeURIComponent(id) + '/edit', '_blank', 'noopener,noreferrer'); } catch (_) { /* The tab can still be opened by hand. */ }
  }
  // Summary extras for DeviceActual: holdings source note, outside-scope rows (quantity, value, P&L only), cash and review rows.
  function extras(doc, {locale = 'ko-KR', effective, market}) {
    const box = make(doc, 'section', null, {class: 'capture-extras', 'data-capture-extras': ''}), entry = effective.entry, split = effective.capture;
    if (!entry) return box;
    if (entry.parsed.state !== 'OK') { box.append(make(doc, 'p', 'Holdings · HOLDINGS_' + entry.parsed.state + ' · ' + words(locale, '기기 ACTUAL만 사용', 'device ACTUAL only'), {'data-capture-state': entry.parsed.state})); return box; }
    if (effective.capture_state === 'AS_OF_FUTURE') box.append(make(doc, 'p', 'Holdings · AS_OF_FUTURE · ' + words(locale, '기준일이 읽은 시각보다 뒤여서 쓰지 않습니다.', 'as_of is after the read time; not used.'), {'data-capture-state': 'AS_OF_FUTURE'}));
    else if (effective.source === 'DEVICE_ACTUAL' && split && split.as_of) box.append(make(doc, 'p', words(locale, 'Holdings 탭(as_of ' + split.as_of + ')보다 기기 ACTUAL이 최근이어서 기기 ACTUAL을 씁니다.', 'Device ACTUAL is newer than the Holdings tab (as_of ' + split.as_of + '), so device ACTUAL is used.'), {'data-capture-state': 'OLDER'}));
    if (!split) return box;
    const rates = new Map((market && Array.isArray(market.fx) ? market.fx : []).map(rate => [rate.currency, Number(rate.rate)]));
    if (split.out_of_scope.length) {
      box.append(make(doc, 'h4', words(locale, '분석 범위 밖 · 수량·평가액·손익만', 'Outside analysis scope · quantity, value and P&L only')));
      const list = make(doc, 'div', null, {class: 'actual-value-list', 'data-outside-scope': ''});
      for (const position of split.out_of_scope) {
        const quote = entry.outside && entry.outside[position.symbol] || {state: 'NOT_AVAILABLE', reason: 'QUOTE_NOT_AVAILABLE_OUT_OF_SCOPE'};
        const quantity = Number(position.quantity), price = quote.state === 'AVAILABLE' ? Number(quote.price) : null;
        const native = price === null ? null : quantity * price, rate = position.currency === 'KRW' ? 1 : rates.has(position.currency) ? rates.get(position.currency) : null;
        const krw = native !== null && rate !== null && Number.isFinite(native * rate) ? native * rate : null;
        let pnl = 'NOT_AVAILABLE';
        if (position.cost_basis === 'COST_KRW_DIV_QTY' && krw !== null) pnl = format(locale, krw - Number(position.cost_krw), 0) + ' KRW · cost_krw';
        else if (position.cost_basis === 'AVG_COST_FIELD' && price !== null) pnl = format(locale, (price - Number(position.avg_cost)) * quantity, 2) + ' ' + position.currency + ' · avg_cost';
        const card = make(doc, 'div', null, {class: 'actual-value-row', 'data-outside-symbol': position.symbol});
        card.append(make(doc, 'strong', position.symbol + (position.name ? ' · ' + position.name : '') + ' · ' + words(locale, '분석 범위 밖', 'Outside analysis scope')));
        const dl = make(doc, 'dl');
        const workerLabel = doc.defaultView && doc.defaultView.WorkerQuoteFallback ? doc.defaultView.WorkerQuoteFallback.label(locale) : 'WORKER_CLOSE';
        const PT = doc.defaultView && doc.defaultView.PriceTime, DM = doc.defaultView && doc.defaultView.DeviceMarket;
        const time = quote.state !== 'AVAILABLE' ? '' : PT ? (d => locale === 'en-US' ? d.label_en : d.label_ko)(PT.describe(quote, {staleness: DM ? DM.staleness : undefined})) : String(quote.as_of);
        const source = quote.state === 'AVAILABLE' ? (quote.source === 'WORKER_CLOSE' ? workerLabel : words(locale, 'GOOGLEFINANCE · 최대 20분 지연 · 정보용', 'GOOGLEFINANCE · Up to 20 minutes delayed · For information only')) + ' · ' + time : 'NOT_AVAILABLE · ' + quote.reason;
        for (const [label, value] of [[words(locale, '수량', 'Quantity'), position.quantity], [words(locale, '가격 출처', 'Price source'), source],
          [words(locale, '원통화 평가액', 'Native value'), native === null ? 'NOT_AVAILABLE' : format(locale, native, 2) + ' ' + position.currency],
          [words(locale, '원화 평가액', 'KRW value'), krw === null ? 'NOT_AVAILABLE' + (native !== null ? ' · FX_NOT_AVAILABLE' : '') : format(locale, krw, 0) + ' KRW'],
          [words(locale, '손익', 'P&L'), pnl], ['QGV', 'NOT_AVAILABLE · OUT_OF_SCOPE']]) dl.append(make(doc, 'dt', label), make(doc, 'dd', value));
        card.append(dl); list.append(card);
      }
      box.append(list);
    }
    if (split.cash.length) {
      box.append(make(doc, 'h4', words(locale, '현금 · 보유 종목 아님', 'Cash · not a position')));
      for (const cash of split.cash) box.append(make(doc, 'p', cash.symbol + ' · ' + format(locale, Number(cash.amount), 2) + ' ' + cash.currency + (cash.cost_krw !== null ? ' · ' + format(locale, Number(cash.cost_krw), 0) + ' KRW' : ''), {'data-cash-row': cash.symbol}));
    }
    if (split.review.length) {
      const list = make(doc, 'ul', null, {'data-capture-summary-review': ''});
      for (const item of split.review) list.append(make(doc, 'li', words(locale, '확인 필요 · 행 ', 'Needs review · row ') + item.row + ' · ' + item.reason_codes.map(code => reasonText(locale, code)).join(' / ')));
      box.append(make(doc, 'h4', words(locale, '확인 필요 · 읽지 않음', 'Needs review · not read')), list);
    }
    return box;
  }
  return Object.freeze({mountGuide, extras, outsideQuotes, codesFor});
});
