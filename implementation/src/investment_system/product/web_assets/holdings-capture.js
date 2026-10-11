/* Holdings tab (capture + personal AI) parser, prompt v1 and the RAM-only parsed result. No network, no storage.
   Python reference: investment_system/product/holdings_capture.py (vectors: tests/fixtures/holdings_capture_reference_v1.json). */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HoldingsCapture = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'holdings-capture/1', TAB = 'Holdings', RANGE = "'Holdings'!A1:H1025", MAX_ROWS = 1000;
  const HEADER = Object.freeze(['as_of', 'symbol', 'quantity', 'avg_cost', 'currency', 'cost_krw', 'name']);
  const PROMPT_VERSION = '잔고 캡처 변환 프롬프트 v1', AS_OF_TOKEN = '{{AS_OF}}';
  // Verbatim copy of implementation/docs/virtual_trading/HOLDINGS_CAPTURE_PROMPT_V1.md (fenced block); tests keep them equal.
  const PROMPT_TEMPLATE = [
    '[잔고 캡처 변환 프롬프트 v1]',
    '',
    '첨부한 증권사 잔고 화면 캡처를 아래 형식의 표로 바꿔 주세요.',
    '',
    '형식',
    '- 첫 줄은 머리글이며 정확히 다음 7개 열입니다. 열 사이는 탭 문자로 구분합니다.',
    'as_of\tsymbol\tquantity\tavg_cost\tcurrency\tcost_krw\tname',
    '- 그다음 줄부터 보유 종목 하나당 한 줄입니다. 위 7개 열만 쓰고 다른 열, 합계 줄, 빈 줄은 넣지 않습니다.',
    '',
    '열 규칙',
    '- as_of: 기준일입니다. 모든 줄에 ' + AS_OF_TOKEN + ' 값을 그대로 씁니다.',
    '- symbol: 티커만 씁니다. 미국 주식은 미국 티커(예: NVDA), 한국 주식은 KRX 6자리 종목코드(예: 005930, 앞자리 0 유지), 일본 주식은 도쿄증권거래소 4자리 코드(예: 8035).',
    '- quantity: 보유 수량입니다.',
    '- avg_cost: 화면에 표시된 평균 매입단가(종목 통화 기준)입니다.',
    '- currency: 종목 통화의 ISO 코드입니다(USD, KRW, JPY 등).',
    '- cost_krw: 화면에 표시된 원화 매입금액 합계입니다.',
    '- name: 화면에 보이는 종목명을 그대로 씁니다.',
    '- 예수금·현금은 symbol을 CASH_통화코드(예: CASH_KRW, CASH_USD)로 쓰고, quantity에 그 통화의 금액, currency에 같은 통화 코드를 씁니다. avg_cost는 비워 둡니다. 원화 환산액이 화면에 있으면 cost_krw에 씁니다.',
    '',
    '숫자 규칙',
    '- 천 단위 쉼표, 통화 기호, 단위(주, 원, %), +와 - 기호를 넣지 않습니다. 소수점은 마침표(.)만 씁니다.',
    '',
    '모르면 빈칸',
    '- 화면에서 확실히 읽을 수 없는 값은 빈칸으로 둡니다. 추측하거나 계산해서 채우지 않고, 0으로 채우지 않습니다.',
    '',
    '출력',
    '- 머리글을 포함한 표만 출력합니다. 앞뒤 설명, 인사, 주석, 코드 블록 표시를 붙이지 않습니다.'
  ].join('\n');
  const DECIMAL = /^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/;
  const US = /^[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z0-9]{1,3})?$/, KRX = /^\d{6}$/, TSE = /^\d{4}$/, CASH = /^CASH_([A-Z]{3})$/, CCY = /^[A-Z]{3}$/;
  const AVG_SCALE = 6n, AVG_DIGITS = 6;
  const store = new WeakMap();

  function fail(code) { throw new Error(code); }
  function seoulDate(now) {
    const value = now === undefined ? new Date() : new Date(now);
    if (!Number.isFinite(value.getTime())) fail('INVALID');
    return new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'}).format(value);
  }
  function validDay(text) {
    if (typeof text !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
    const time = Date.parse(text + 'T00:00:00Z');
    return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === text && text >= '1970-01-01';
  }
  function prompt(asOf) { if (!validDay(asOf)) fail('INVALID'); return PROMPT_TEMPLATE.split(AS_OF_TOKEN).join(asOf); }
  // Same whitespace set as the Python reference (str.strip(' \t\r\n\u00a0\u3000')).
  function trim(text) { return text.replace(/^[ \t\r\n\u00a0\u3000]+|[ \t\r\n\u00a0\u3000]+$/g, ''); }
  function blank(value) { return value === null || value === undefined || (typeof value === 'string' && trim(value) === ''); }
  // Sheet numbers are read UNFORMATTED. Exponent forms (JS: >= 1e21 or < 1e-6) are rejected, never expanded.
  function numberText(value) {
    if (typeof value === 'number') {
      if (!Number.isFinite(value) || value < 0 || (value !== 0 && (value < 1e-6 || value >= 1e21))) return null;
      const text = String(value); return /e/i.test(text) ? null : text;
    }
    return typeof value === 'string' ? trim(value) : null;
  }
  function decimal(value) { const text = numberText(value); return text !== null && DECIMAL.test(text) ? text : null; }
  function day(value) {
    if (typeof value === 'number') {
      if (!Number.isInteger(value) || value < 1 || value > 2958465) return null;
      return new Date(Date.UTC(1899, 11, 30) + value * 86400000).toISOString().slice(0, 10);
    }
    if (typeof value !== 'string') return null;
    const text = trim(value); return validDay(text) ? text : null;
  }
  function parts(text) { const [whole, fraction = ''] = text.split('.'); return [BigInt(whole + fraction), BigInt(fraction.length)]; }
  // Exact decimal cost_krw / quantity, rounded half-up to 6 decimals (same integer arithmetic as the Python reference).
  function divide(numerator, denominator) {
    const [n, ns] = parts(numerator), [d, ds] = parts(denominator);
    if (d === 0n) return null;
    const top = n * 10n ** (ds + AVG_SCALE), bottom = d * 10n ** ns;
    let quotient = top / bottom; if ((top % bottom) * 2n >= bottom) quotient += 1n;
    const digits = quotient.toString().padStart(AVG_DIGITS + 1, '0');
    let text = digits.slice(0, -AVG_DIGITS) + '.' + digits.slice(-AVG_DIGITS);
    text = text.replace(/0+$/, '').replace(/\.$/, '');
    return DECIMAL.test(text) ? text : null;
  }
  function symbolOf(raw, currency) {
    if (typeof raw === 'number') {
      if (!Number.isInteger(raw) || raw < 0) return null;
      if (currency === 'KRW' && raw <= 999999) return String(raw).padStart(6, '0');
      if (currency === 'JPY' && raw >= 1000 && raw <= 9999) return String(raw);
      return null;
    }
    if (typeof raw !== 'string') return null;
    const text = trim(raw);
    return CASH.test(text) || KRX.test(text) || TSE.test(text) || US.test(text) ? text : null;
  }
  function marketOf(symbol) { return CASH.test(symbol) ? 'CASH' : KRX.test(symbol) ? 'KRX' : TSE.test(symbol) ? 'TSE' : 'US'; }
  function expectedCurrency(symbol, market) { return market === 'CASH' ? CASH.exec(symbol)[1] : market === 'KRX' ? 'KRW' : market === 'TSE' ? 'JPY' : 'USD'; }
  function headerMatches(row) {
    if (!Array.isArray(row)) return false;
    const cells = row.slice(); while (cells.length && blank(cells[cells.length - 1])) cells.pop();
    return cells.length === HEADER.length && cells.every((cell, i) => typeof cell === 'string' && trim(cell).toLowerCase() === HEADER[i]);
  }
  function parse(values) {
    const result = {schema: SCHEMA, state: 'EMPTY', as_of: null, positions: [], cash: [], review: []};
    if (!Array.isArray(values) || !values.length) return result;
    if (!headerMatches(values[0])) return {...result, state: 'HEADER_MISMATCH'};
    let end = values.length;
    while (end > 1 && (!Array.isArray(values[end - 1]) || values[end - 1].every(blank))) end--;
    if (end - 1 > MAX_ROWS) return {...result, state: 'ROW_LIMIT'};
    const checked = [];
    for (let index = 1; index < end; index++) {
      const row = values[index], number = index + 1;
      if (!Array.isArray(row)) { result.review.push({row: number, symbol: null, reason_codes: ['COLUMN_COUNT']}); continue; }
      if (row.every(blank)) continue;
      if (row.slice(HEADER.length).some(cell => !blank(cell))) { result.review.push({row: number, symbol: null, reason_codes: ['COLUMN_COUNT']}); continue; }
      const cell = i => row[i] === undefined ? null : row[i], reasons = [];
      const asOfRaw = cell(0), symbolRaw = cell(1), quantityRaw = cell(2), avgRaw = cell(3), currencyRaw = cell(4), costRaw = cell(5), nameRaw = cell(6);
      const asOf = blank(asOfRaw) ? null : day(asOfRaw);
      if (blank(asOfRaw)) reasons.push('AS_OF_MISSING'); else if (asOf === null) reasons.push('AS_OF_FORMAT');
      const currency = blank(currencyRaw) ? null : typeof currencyRaw === 'string' && CCY.test(trim(currencyRaw)) ? trim(currencyRaw) : null;
      if (blank(currencyRaw)) reasons.push('CURRENCY_MISSING'); else if (currency === null) reasons.push('CURRENCY_FORMAT');
      const symbol = blank(symbolRaw) ? null : symbolOf(symbolRaw, currency);
      if (blank(symbolRaw)) reasons.push('SYMBOL_MISSING'); else if (symbol === null) reasons.push('SYMBOL_FORMAT');
      const market = symbol === null ? null : marketOf(symbol);
      const quantity = blank(quantityRaw) ? null : decimal(quantityRaw);
      if (blank(quantityRaw)) reasons.push('QUANTITY_MISSING'); else if (quantity === null) reasons.push('QUANTITY_FORMAT');
      else if (market !== 'CASH' && Number(quantity) <= 0) reasons.push('QUANTITY_NOT_POSITIVE');
      const avg = blank(avgRaw) ? null : decimal(avgRaw);
      if (!blank(avgRaw) && avg === null) reasons.push('AVG_COST_FORMAT');
      if (market === 'CASH' && !blank(avgRaw)) reasons.push('CASH_AVG_COST_PRESENT');
      const cost = blank(costRaw) ? null : decimal(costRaw);
      if (!blank(costRaw) && cost === null) reasons.push('COST_KRW_FORMAT');
      if (symbol !== null && currency !== null && expectedCurrency(symbol, market) !== currency) reasons.push('CURRENCY_MISMATCH');
      const name = blank(nameRaw) ? null : typeof nameRaw === 'string' ? trim(nameRaw) : null;
      if (!blank(nameRaw) && (name === null || [...name].length > 100 || /[\x00-\x1f\x7f]/.test(name))) reasons.push('NAME_FORMAT');
      let average = null, averageCurrency = null, basis = 'NOT_AVAILABLE';
      if (!reasons.length && market !== 'CASH') {
        if (cost !== null) { average = divide(cost, quantity); averageCurrency = 'KRW'; basis = 'COST_KRW_DIV_QTY'; if (average === null) reasons.push('COST_RANGE'); }
        else if (avg !== null) { average = avg; averageCurrency = currency; basis = 'AVG_COST_FIELD'; }
      }
      if (reasons.length) { result.review.push({row: number, symbol, reason_codes: reasons}); continue; }
      checked.push(market === 'CASH'
        ? {kind: 'cash', as_of: asOf, value: {row: number, symbol, currency, amount: quantity, cost_krw: cost, name}}
        : {kind: 'position', as_of: asOf, value: {row: number, symbol, market, quantity, currency, avg_cost: avg, cost_krw: cost,
          average_cost: average, average_cost_currency: averageCurrency, cost_basis: basis, name}});
    }
    // One tab is one snapshot: rows dated before the newest as_of are not read; then duplicate symbols are not read.
    const newest = checked.reduce((latest, item) => item.as_of > latest ? item.as_of : latest, '');
    const dated = [];
    for (const item of checked) {
      if (item.as_of !== newest) result.review.push({row: item.value.row, symbol: item.value.symbol, reason_codes: ['AS_OF_MISMATCH']});
      else dated.push(item);
    }
    const counts = new Map(); for (const item of dated) counts.set(item.value.symbol, (counts.get(item.value.symbol) || 0) + 1);
    for (const item of dated) {
      if (counts.get(item.value.symbol) > 1) result.review.push({row: item.value.row, symbol: item.value.symbol, reason_codes: ['DUPLICATE_SYMBOL']});
      else (item.kind === 'cash' ? result.cash : result.positions).push(item.value);
    }
    result.review.sort((a, b) => a.row - b.row);
    result.state = checked.length || result.review.length ? 'OK' : 'EMPTY';
    result.as_of = result.positions.length || result.cash.length ? newest : null;
    return result;
  }
  // Split parsed rows into the 19-instrument ACTUAL rows and everything outside the analysis scope (pure).
  function toActual(parsed, catalog) {
    if (!parsed || parsed.schema !== SCHEMA || parsed.state !== 'OK' || !catalog || !Array.isArray(catalog.instruments)) fail('INVALID');
    const byTicker = new Map(catalog.instruments.map(instrument => [instrument.ticker, instrument]));
    const rows = [], inScope = [], outOfScope = [], review = parsed.review.map(item => ({...item, reason_codes: item.reason_codes.slice()}));
    for (const position of parsed.positions) {
      const instrument = byTicker.get(position.symbol);
      if (!instrument) { outOfScope.push({...position}); continue; }
      if (position.currency !== instrument.currency) { review.push({row: position.row, symbol: position.symbol, reason_codes: ['CURRENCY_MISMATCH']}); continue; }
      if (position.average_cost === null) { review.push({row: position.row, symbol: position.symbol, reason_codes: ['COST_NOT_AVAILABLE']}); continue; }
      rows.push({security_reference: JSON.parse(JSON.stringify(instrument.security_reference)), quantity: position.quantity, average_cost: position.average_cost, currency: position.average_cost_currency});
      inScope.push({...position, ticker: instrument.ticker});
    }
    review.sort((a, b) => a.row - b.row);
    return {as_of: parsed.as_of, rows, in_scope: inScope, out_of_scope: outOfScope, cash: parsed.cash.map(item => ({...item})), review};
  }
  // RAM-only holder of the last read Holdings tab for this window. Cleared on sign-out, reload or page hide.
  function set(view, entry) {
    if (!view || !entry || !entry.parsed || typeof entry.read_at !== 'string') fail('INVALID');
    store.set(view, Object.freeze({...entry})); notify(view);
  }
  function get(view) { return view ? store.get(view) || null : null; }
  function clear(view) { if (view && store.has(view)) { store.delete(view); notify(view); } }
  function notify(view) { try { if (view.document && view.Event) view.document.dispatchEvent(new view.Event('device-actual-changed')); } catch (_) { /* RAM state only */ } }
  return Object.freeze({SCHEMA, TAB, RANGE, HEADER, PROMPT_VERSION, AS_OF_TOKEN, PROMPT_TEMPLATE, MAX_ROWS,
    seoulDate, prompt, parse, toActual, divide, set, get, clear});
});
