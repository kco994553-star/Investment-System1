/* ACTUAL stays on this browser's device. No network or telemetry is used here. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DeviceActual = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'device-actual-holdings/1';
  const DB_NAME = 'investment-device-actual-v1', STORE = 'snapshots', KEY = 'actual';
  const MAX_FILE_BYTES = 131072, CURRENCIES = Object.freeze(['USD', 'JPY', 'KRW']);
  const DECIMAL = /^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/;
  const hosts = new WeakMap();
  const UI = {
    title: ['내 실제 보유 · ACTUAL', 'My actual holdings · ACTUAL'],
    device: ['이 기기에만 저장됨', 'Stored only on this device'],
    privacy: ['보유 정보는 이 브라우저의 IndexedDB에만 저장됩니다. 서버로 전송되지 않습니다.', 'Holdings are stored only in this browser’s IndexedDB. They are never sent to a server.'],
    backup: ['JSON 내보내기 파일은 기기에 남을 수 있습니다. 기기 삭제는 내보낸 파일을 삭제하지 않습니다.', 'An exported JSON file may remain on your device. Deleting browser holdings does not delete exported files.'],
    entry: ['수량·평균 매입가·통화를 입력하세요. 두 숫자 칸을 비우면 해당 종목을 제외합니다.', 'Enter quantity, average cost and currency. Leave both number fields blank to exclude an instrument.'],
    quote: ['평가액은 제공된 시장가격으로만 계산됩니다. 평균 매입가는 시장가격이 아닙니다. 가격 또는 환율이 없으면 비중·TARGET 차이는 NOT_AVAILABLE입니다.', 'Market value uses supplied market prices only. Average cost is not a market price. Without prices or FX, weights and TARGET deltas are NOT_AVAILABLE.'],
    quantity: ['수량', 'Quantity'], average: ['평균 매입가', 'Average cost'], currency: ['통화', 'Currency'],
    save: ['이 기기에 저장', 'Save on this device'], export: ['JSON 내보내기', 'Export JSON'], import: ['JSON 가져오기', 'Import JSON'], delete: ['기기 보유 정보 삭제', 'Delete device holdings'],
    saved: ['이 기기에 저장했습니다.', 'Saved on this device.'], imported: ['가져온 보유 정보를 이 기기에 저장했습니다.', 'Imported holdings were saved on this device.'],
    removed: ['기기 보유 정보를 삭제했습니다. 내보낸 JSON 파일은 기기에 남을 수 있습니다.', 'Device holdings were deleted. Exported JSON files may remain on your device.'],
    exported: ['기기에서 JSON 파일을 내보냈습니다. 파일을 안전하게 보관하세요.', 'A JSON file was exported on this device. Keep the file safe.'],
    overwrite: ['이 기기에 저장된 보유 정보를 가져온 파일로 바꾸시겠습니까?', 'Replace holdings saved on this device with the imported file?'],
    removeConfirm: ['이 브라우저의 보유 정보를 영구 삭제하시겠습니까? 내보낸 파일은 삭제되지 않습니다.', 'Permanently delete holdings in this browser? Exported files will remain.'],
    canceled: ['취소했습니다. 저장된 보유 정보는 그대로입니다.', 'Canceled. Saved holdings are unchanged.'],
    unavailable: ['ACTUAL · NOT_AVAILABLE — 이 기기의 보유 정보가 없습니다.', 'ACTUAL · NOT_AVAILABLE — No holdings on this device.'],
    existing: ['ACTUAL · 이 기기에만 저장됨', 'ACTUAL · Stored only on this device'],
    invalid: ['입력 또는 JSON 형식이 유효하지 않습니다. 저장된 보유 정보는 그대로입니다.', 'The input or JSON format is invalid. Saved holdings are unchanged.'],
    incompatible: ['TARGET·식별자 버전이 일치하지 않습니다. 저장된 보유 정보는 그대로입니다.', 'TARGET or identity versions do not match. Saved holdings are unchanged.'],
    version: ['기기의 저장 버전을 갱신할 수 없습니다. 저장된 보유 정보는 그대로입니다.', 'Cannot advance the device revision. Saved holdings are unchanged.'],
    storage: ['이 기기에 저장할 수 없습니다. 저장 완료가 아닙니다. 기존 보유 정보는 변경하지 않았습니다.', 'Cannot save on this device. Saving did not complete. Existing holdings were not changed.'],
    corrupt: ['저장된 보유 정보를 읽을 수 없습니다. 원본을 보존했습니다. 삭제 후 다시 입력할 수 있습니다.', 'Saved holdings cannot be read. The original is preserved. You can delete it and enter holdings again.'],
    tooLarge: ['128 KB 이하 JSON 파일을 선택하세요.', 'Select a JSON file of 128 KB or less.'],
    total: ['총 시장 평가액', 'Total market value'], market: ['시장 평가액', 'Market value'], weight: ['ACTUAL 비중', 'ACTUAL weight'], delta: ['TARGET 대비 차이', 'Delta from TARGET'],
    missing: ['시장가격 미제공 · NOT_AVAILABLE', 'Market prices missing · NOT_AVAILABLE'], fx: ['환율 계약 미제공 · NOT_AVAILABLE', 'FX contract missing · NOT_AVAILABLE'],
    zero: ['양수 보유가 없음 · NOT_AVAILABLE', 'No positive holdings · NOT_AVAILABLE'], calculation: ['계산 범위 초과 · NOT_AVAILABLE', 'Calculation out of range · NOT_AVAILABLE'], available: ['제공된 시장가격 기준', 'Based on supplied market prices'],
    summary: ['내 실제 보유 요약', 'My actual holdings summary'], target: ['TARGET 비중', 'TARGET weight'],
    readFailed: ['기기 저장소를 열 수 없습니다. ACTUAL · NOT_AVAILABLE', 'Cannot open device storage. ACTUAL · NOT_AVAILABLE']
  };
  function fail(code) { throw new Error(code); }
  function plain(value) { return value !== null && typeof value === 'object' && !Array.isArray(value) && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null); }
  function keys(value, expected) {
    if (!plain(value) || Object.keys(value).length !== expected.length || expected.some(key => !Object.prototype.hasOwnProperty.call(value, key))) fail('INVALID');
  }
  function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (plain(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
    return JSON.stringify(value);
  }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function decimal(value) { if (typeof value !== 'string' || !DECIMAL.test(value) || !Number.isFinite(Number(value))) fail('INVALID'); return value; }
  function clock(value) {
    if (typeof value !== 'string') fail('INVALID');
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
    if (!m) fail('INVALID');
    const year = Number(m[1]), month = Number(m[2]), day = Number(m[3]);
    if (year < 1970 || month < 1 || month > 12 || day < 1 || day > new Date(Date.UTC(year, month, 0)).getUTCDate() || Number(m[4]) > 23 || Number(m[5]) > 59 || Number(m[6]) > 59) fail('INVALID');
    if (m[8] !== 'Z' && (Number(m[8].slice(1, 3)) > 23 || Number(m[8].slice(4)) > 59)) fail('INVALID');
    const result = Date.parse(value); if (!Number.isFinite(result)) fail('INVALID'); return result;
  }
  function nowMillis(now) { const result = now === undefined ? Date.now() : typeof now === 'number' ? now : clock(now); if (!Number.isFinite(result)) fail('INVALID'); return result; }
  function catalogIndex(catalog) {
    if (!plain(catalog) || catalog.schema !== 'DEVICE_ACTUAL_CATALOG/1' || !Array.isArray(catalog.themes) || !Array.isArray(catalog.instruments) || !catalog.themes.length || !catalog.instruments.length || catalog.instruments.length > 100 || catalog.total_units !== 10000) fail('CATALOG');
    for (const field of ['target_root_version', 'identity_map_version']) if (typeof catalog[field] !== 'string' || !catalog[field]) fail('CATALOG');
    for (const field of ['target_root_sha256', 'identity_map_sha256']) if (typeof catalog[field] !== 'string' || !/^[a-f0-9]{64}$/.test(catalog[field])) fail('CATALOG');
    const themes = new Map(), instruments = new Map();
    for (const theme of catalog.themes) {
      if (!plain(theme) || typeof theme.theme_id !== 'string' || !theme.theme_id || themes.has(theme.theme_id) || !Number.isSafeInteger(theme.target_units) || theme.target_units < 0) fail('CATALOG');
      themes.set(theme.theme_id, theme);
    }
    for (const instrument of catalog.instruments) {
      if (!plain(instrument) || !plain(instrument.security_reference) || !themes.has(instrument.theme_id) || !CURRENCIES.includes(instrument.currency) || !Number.isSafeInteger(instrument.target_units) || instrument.target_units < 0) fail('CATALOG');
      const id = canonical(instrument.security_reference); if (instruments.has(id)) fail('CATALOG'); instruments.set(id, instrument);
    }
    if (catalog.themes.reduce((sum, t) => sum + t.target_units, 0) !== catalog.total_units || catalog.instruments.reduce((sum, r) => sum + r.target_units, 0) !== catalog.total_units) fail('CATALOG');
    return { themes, instruments };
  }
  function validate(snapshot, catalog, options = {}) {
    const index = catalogIndex(catalog);
    keys(snapshot, ['schema', 'version', 'kind', 'ownership', 'owner', 'effective_at', 'available_at', 'target_root_version', 'target_root_sha256', 'identity_map_version', 'identity_map_sha256', 'themes']);
    if (snapshot.schema !== SCHEMA || snapshot.kind !== 'ACTUAL' || snapshot.ownership !== 'USER_DEVICE_ONLY' || !Number.isSafeInteger(snapshot.version) || snapshot.version < 1) fail('INVALID');
    if (options.minimumVersion !== undefined && snapshot.version <= options.minimumVersion) fail('VERSION');
    keys(snapshot.owner, ['role', 'storage']);
    if (snapshot.owner.role !== 'USER' || snapshot.owner.storage !== 'USER_DEVICE_ONLY') fail('INVALID');
    for (const field of ['target_root_version', 'target_root_sha256', 'identity_map_version', 'identity_map_sha256']) if (snapshot[field] !== catalog[field]) fail('INCOMPATIBLE');
    const effective = clock(snapshot.effective_at), available = clock(snapshot.available_at);
    if (effective > available || available > nowMillis(options.now)) fail('INVALID');
    if (!Array.isArray(snapshot.themes) || snapshot.themes.length !== index.themes.size) fail('INVALID');
    const seenThemes = new Set(), seenRows = new Set();
    for (const theme of snapshot.themes) {
      keys(theme, ['theme_id', 'holdings']);
      if (!index.themes.has(theme.theme_id) || seenThemes.has(theme.theme_id) || !Array.isArray(theme.holdings) || theme.holdings.length > index.instruments.size) fail('INVALID');
      seenThemes.add(theme.theme_id);
      for (const row of theme.holdings) {
        keys(row, ['security_reference', 'quantity', 'average_cost', 'currency']);
        if (!plain(row.security_reference)) fail('INVALID');
        const id = canonical(row.security_reference), instrument = index.instruments.get(id);
        if (!instrument || instrument.theme_id !== theme.theme_id || seenRows.has(id) || !CURRENCIES.includes(row.currency)) fail('INVALID');
        seenRows.add(id); decimal(row.quantity); decimal(row.average_cost);
      }
    }
    return clone(snapshot);
  }
  function makeSnapshot(catalog, rows, previous = null, now) {
    const index = catalogIndex(catalog); if (!Array.isArray(rows)) fail('INVALID');
    if (previous) validate(previous, catalog, { now });
    const timestamp = new Date(nowMillis(now)).toISOString();
    const snapshot = {
      schema: SCHEMA, version: previous ? previous.version + 1 : 1, kind: 'ACTUAL', ownership: 'USER_DEVICE_ONLY',
      owner: { role: 'USER', storage: 'USER_DEVICE_ONLY' }, effective_at: timestamp, available_at: timestamp,
      target_root_version: catalog.target_root_version, target_root_sha256: catalog.target_root_sha256,
      identity_map_version: catalog.identity_map_version, identity_map_sha256: catalog.identity_map_sha256,
      themes: catalog.themes.map(theme => ({ theme_id: theme.theme_id, holdings: [] }))
    };
    for (const row of rows) {
      if (!plain(row) || !plain(row.security_reference)) fail('INVALID');
      const instrument = index.instruments.get(canonical(row.security_reference)); if (!instrument) fail('INVALID');
      snapshot.themes.find(theme => theme.theme_id === instrument.theme_id).holdings.push(clone(row));
    }
    return validate(snapshot, catalog, { now });
  }
  function prepareImport(snapshot, catalog, previous = null, now) {
    const next = validate(snapshot, catalog, { now });
    if (previous) { validate(previous, catalog, { now }); next.version = Math.max(next.version, previous.version + 1); }
    next.available_at = new Date(nowMillis(now)).toISOString();
    return validate(next, catalog, { now, ...(previous ? { minimumVersion: previous.version } : {}) });
  }
  function valuation(snapshot, catalog, quotes = [], options = {}) {
    const index = catalogIndex(catalog);
    const empty = { state: 'NOT_AVAILABLE', reason: 'NO_ACTUAL', total: null, currency: null, rows: [], themes: [], currency_totals: {} };
    if (!snapshot) return empty;
    const valid = validate(snapshot, catalog, options), quoteMap = new Map(), seenQuotes = new Set(), ambiguous = new Set(), current = nowMillis(options.now);
    for (const quote of Array.isArray(quotes) ? quotes : []) {
      try {
        if (!plain(quote) || !plain(quote.security_reference)) fail('INVALID');
        const id = canonical(quote.security_reference); if (!index.instruments.has(id)) fail('INVALID');
        if (seenQuotes.has(id)) { ambiguous.add(id); quoteMap.delete(id); continue; }
        seenQuotes.add(id);
        keys(quote, ['security_reference', 'price', 'currency', 'as_of', 'available_at']);
        const price = typeof quote.price === 'number' ? quote.price : Number(decimal(quote.price));
        if (!Number.isFinite(price) || price <= 0 || quote.currency !== index.instruments.get(id).currency) fail('INVALID');
        if (clock(quote.as_of) > clock(quote.available_at) || clock(quote.available_at) > current) fail('INVALID');
        quoteMap.set(id, { ...quote, price });
      } catch (_) { /* Unusable quote remains unavailable. */ }
    }
    const rows = valid.themes.flatMap(theme => theme.holdings.map(row => {
      const id = canonical(row.security_reference), instrument = index.instruments.get(id), quote = quoteMap.get(id), quantity = Number(row.quantity);
      const marketValue = quote && quote.currency === row.currency && !ambiguous.has(id) ? quantity * quote.price : null;
      return { ...row, theme_id: theme.theme_id, target_units: instrument.target_units, market_value: Number.isFinite(marketValue) ? marketValue : null, weight: null, delta: null };
    }));
    const positive = rows.filter(row => Number(row.quantity) > 0), currencies = new Set(positive.map(row => row.currency));
    const complete = rows.every(row => row.market_value !== null), sameCurrency = currencies.size === 1;
    const total = complete && sameCurrency ? rows.reduce((sum, row) => sum + row.market_value, 0) : null;
    const available = total !== null && total > 0 && Number.isFinite(total);
    const currencyTotals = {};
    for (const currency of new Set(rows.map(row => row.currency))) {
      const group = rows.filter(row => row.currency === currency);
      const groupTotal = group.every(row => row.market_value !== null) ? group.reduce((sum, row) => sum + row.market_value, 0) : null;
      currencyTotals[currency] = Number.isFinite(groupTotal) ? groupTotal : null;
    }
    if (available) for (const row of rows) { row.weight = row.market_value / total; row.delta = row.weight - row.target_units / catalog.total_units; }
    const themes = catalog.themes.map(theme => {
      const group = rows.filter(row => row.theme_id === theme.theme_id);
      const marketValue = available ? group.reduce((sum, row) => sum + row.market_value, 0) : null;
      const weight = available ? marketValue / total : null;
      return { theme_id: theme.theme_id, market_value: marketValue, weight, delta: available ? weight - theme.target_units / catalog.total_units : null };
    });
    return { state: available ? 'AVAILABLE' : 'NOT_AVAILABLE', reason: available ? 'QUOTED' : !positive.length ? 'NO_POSITIONS' : !complete ? 'MISSING_QUOTES' : !sameCurrency ? 'FX_NOT_AVAILABLE' : !Number.isFinite(total) ? 'CALCULATION_ERROR' : 'NO_POSITIONS', total: total !== null && Number.isFinite(total) ? total : null, currency: sameCurrency ? [...currencies][0] : null, rows, themes, currency_totals: currencyTotals };
  }
  function openDatabase(view) {
    return new Promise((resolve, reject) => {
      let request;
      try { if (!view.indexedDB) fail('STORAGE'); request = view.indexedDB.open(DB_NAME, 1); } catch (_) { reject(new Error('STORAGE')); return; }
      let settled = false;
      request.onupgradeneeded = () => { if (!request.result.objectStoreNames.contains(STORE)) request.result.createObjectStore(STORE); };
      request.onerror = () => { settled = true; reject(new Error('STORAGE')); };
      request.onblocked = () => { settled = true; reject(new Error('STORAGE')); };
      request.onsuccess = () => { if (settled) request.result.close(); else { request.result.onversionchange = () => request.result.close(); resolve(request.result); } };
    });
  }
  async function readStored(view) {
    const db = await openDatabase(view);
    return new Promise((resolve, reject) => {
      let value, tx;
      try { tx = db.transaction(STORE, 'readonly'); const request = tx.objectStore(STORE).get(KEY); request.onsuccess = () => { value = request.result; }; } catch (_) { db.close(); reject(new Error('STORAGE')); return; }
      tx.oncomplete = () => { db.close(); resolve(value === undefined ? null : value); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error('STORAGE')); };
    });
  }
  async function commitStored(view, snapshot, expected) {
    const db = await openDatabase(view);
    return new Promise((resolve, reject) => {
      let tx, conflict = false;
      try {
        tx = db.transaction(STORE, 'readwrite'); const store = tx.objectStore(STORE);
        // Confirmed deletion also clears corrupt structured-clone records.
        if (snapshot === null) store.delete(KEY);
        else {
          const request = store.get(KEY);
          request.onsuccess = () => {
            try {
              if (canonical(request.result === undefined ? null : request.result) !== canonical(expected)) { conflict = true; tx.abort(); return; }
              store.put(snapshot, KEY);
            } catch (_) { tx.abort(); }
          };
        }
      } catch (_) { db.close(); reject(new Error('STORAGE')); return; }
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error(conflict ? 'CONFLICT' : 'STORAGE')); };
    });
  }
  function t(state, key) { return UI[key][state.locale === 'en-US' ? 1 : 0]; }
  function el(state, tag, text, attributes = {}) {
    const element = state.host.ownerDocument.createElement(tag); if (text !== undefined) element.textContent = text;
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value)); return element;
  }
  function notice(state, key) { state.notice.textContent = t(state, key); state.notice.dataset.notice = key; }
  function errorNotice(state, error) { notice(state, error.message === 'INCOMPATIBLE' ? 'incompatible' : error.message === 'VERSION' ? 'version' : ['STORAGE', 'CONFLICT'].includes(error.message) ? 'storage' : 'invalid'); }
  function number(state, value) { return new Intl.NumberFormat(state.locale, { maximumFractionDigits: 8 }).format(value); }
  function percentage(state, value, signed = false) { return value === null ? 'NOT_AVAILABLE' : new Intl.NumberFormat(state.locale, { style: 'percent', maximumFractionDigits: 2, ...(signed ? { signDisplay: 'always' } : {}) }).format(value); }
  function summaryContent(state) {
    const box = el(state, 'section', undefined, { 'data-actual-summary': '', class: 'actual-summary' });
    box.append(el(state, 'h3', t(state, 'summary')));
    const status = el(state, 'p', state.snapshot ? t(state, 'existing') : t(state, 'unavailable'), { 'data-actual-status': '', role: 'status' }); box.append(status);
    const values = valuation(state.snapshot, state.catalog, state.quotes);
    box.append(el(state, 'p', t(state, values.reason === 'FX_NOT_AVAILABLE' ? 'fx' : values.reason === 'QUOTED' ? 'available' : values.reason === 'NO_POSITIONS' ? 'zero' : values.reason === 'CALCULATION_ERROR' ? 'calculation' : 'missing')));
    box.append(el(state, 'p', t(state, 'total') + ': ' + (values.total === null ? 'NOT_AVAILABLE' : number(state, values.total) + ' ' + values.currency), { class: 'actual-total', 'data-market-total': '' }));
    if (values.reason === 'FX_NOT_AVAILABLE') for (const [currency, total] of Object.entries(values.currency_totals)) box.append(el(state, 'p', currency + ': ' + (total === null ? 'NOT_AVAILABLE' : number(state, total))));
    if (values.rows.length) {
      const list = el(state, 'div', undefined, { class: 'actual-value-list' });
      for (const row of values.rows) {
        const instrument = state.catalog.instruments.find(candidate => canonical(candidate.security_reference) === canonical(row.security_reference));
        const card = el(state, 'div', undefined, { class: 'actual-value-row' }); card.append(el(state, 'strong', instrument.label + (instrument.ticker ? ' · ' + instrument.ticker : '')));
        const fields = [[t(state, 'quantity'), row.quantity], [t(state, 'average'), row.average_cost + ' ' + row.currency], [t(state, 'market'), row.market_value === null ? 'NOT_AVAILABLE' : number(state, row.market_value) + ' ' + row.currency], [t(state, 'target'), percentage(state, row.target_units / state.catalog.total_units)], [t(state, 'weight'), percentage(state, row.weight)], [t(state, 'delta'), percentage(state, row.delta, true)]];
        const details = el(state, 'dl'); for (const [label, value] of fields) details.append(el(state, 'dt', label), el(state, 'dd', value)); card.append(details); list.append(card);
      }
      box.append(list);
    }
    return box;
  }
  function repaintSummary(state) {
    const old = state.root.querySelector('[data-actual-summary]'); if (old) old.replaceWith(summaryContent(state));
    if (state.exportButton) state.exportButton.disabled = !state.snapshot || state.busy;
  }
  function populate(state) {
    const saved = new Map(state.snapshot ? state.snapshot.themes.flatMap(theme => theme.holdings).map(row => [canonical(row.security_reference), row]) : []);
    for (const row of state.formRows) {
      const value = saved.get(canonical(row.instrument.security_reference)); row.quantity.value = value ? value.quantity : ''; row.average_cost.value = value ? value.average_cost : ''; row.currency.value = value ? value.currency : row.instrument.currency;
    }
  }
  function setBusy(state, busy) {
    state.busy = busy; for (const control of state.root.querySelectorAll('button, input, select')) control.disabled = busy;
    if (!busy && state.storageProblem) { state.saveButton.disabled = true; state.importInput.disabled = true; }
    if (state.exportButton) state.exportButton.disabled = busy || !state.snapshot;
  }
  function announce(state) { state.host.ownerDocument.dispatchEvent(new state.view.Event('device-actual-changed')); }
  async function save(state) {
    if (state.busy || state.storageProblem) return;
    setBusy(state, true);
    try {
      const rows = [];
      for (const row of state.formRows) {
        const quantity = row.quantity.value.trim(), average_cost = row.average_cost.value.trim();
        if (!quantity && !average_cost) continue;
        rows.push({ security_reference: clone(row.instrument.security_reference), quantity, average_cost, currency: row.currency.value });
      }
      const next = makeSnapshot(state.catalog, rows, state.snapshot);
      await commitStored(state.view, next, state.raw);
      state.snapshot = next; state.raw = next; repaintSummary(state); notice(state, 'saved'); announce(state);
    } catch (error) { errorNotice(state, error); } finally { setBusy(state, false); }
  }
  async function importFile(state, file) {
    if (!file || state.busy || state.storageProblem) return;
    setBusy(state, true);
    try {
      if (file.size > MAX_FILE_BYTES) { notice(state, 'tooLarge'); return; }
      const text = await file.text();
      if (new state.view.TextEncoder().encode(text).byteLength > MAX_FILE_BYTES) { notice(state, 'tooLarge'); return; }
      const source = validate(JSON.parse(text), state.catalog);
      if (state.raw !== null && !state.view.confirm(t(state, 'overwrite'))) { notice(state, 'canceled'); return; }
      const next = prepareImport(source, state.catalog, state.snapshot);
      await commitStored(state.view, next, state.raw);
      state.snapshot = next; state.raw = next; populate(state); repaintSummary(state); notice(state, 'imported'); announce(state);
    } catch (error) { errorNotice(state, error); } finally { state.importInput.value = ''; setBusy(state, false); }
  }
  function exportFile(state) {
    if (!state.snapshot || state.busy) return;
    try {
      const blob = new state.view.Blob([JSON.stringify(validate(state.snapshot, state.catalog), null, 2)], { type: 'application/json' });
      const url = state.view.URL.createObjectURL(blob), anchor = el(state, 'a', undefined, { href: url, download: 'device-actual-holdings.json' });
      state.root.append(anchor); anchor.click(); anchor.remove(); state.view.setTimeout(() => state.view.URL.revokeObjectURL(url), 1000); notice(state, 'exported');
    } catch (error) { errorNotice(state, error); }
  }
  async function remove(state) {
    if (state.busy) return;
    if (!state.view.confirm(t(state, 'removeConfirm'))) { notice(state, 'canceled'); return; }
    setBusy(state, true);
    try {
      await commitStored(state.view, null, state.raw);
      state.raw = null; state.snapshot = null; state.storageProblem = false; populate(state); repaintSummary(state); notice(state, 'removed'); announce(state);
    } catch (error) { errorNotice(state, error); } finally { setBusy(state, false); }
  }
  async function initialState(host, options) {
    if (!host || !host.ownerDocument || !options) fail('INVALID'); catalogIndex(options.catalog);
    const state = { host, view: host.ownerDocument.defaultView, catalog: clone(options.catalog), locale: options.locale === 'en-US' ? 'en-US' : 'ko-KR', quotes: options.quotes || [], snapshot: null, raw: null, storageProblem: false, busy: false, formRows: [] };
    try { state.raw = await readStored(state.view); if (state.raw !== null) state.snapshot = validate(state.raw, state.catalog); }
    catch (error) { state.storageProblem = true; state.initialError = state.raw !== null ? 'corrupt' : 'readFailed'; }
    hosts.set(host, state); return state;
  }
  async function mount(host, options) {
    const state = await initialState(host, options);
    const root = el(state, 'section', undefined, { class: 'device-actual' }); state.root = root;
    root.append(el(state, 'h2', t(state, 'title')), el(state, 'p', t(state, 'device'), { class: 'actual-device-badge' }), el(state, 'p', t(state, 'privacy')), el(state, 'p', t(state, 'entry')), el(state, 'p', t(state, 'quote')));
    const form = el(state, 'form', undefined, { class: 'actual-form' });
    state.catalog.instruments.forEach((instrument, i) => {
      const row = el(state, 'fieldset', undefined, { class: 'actual-input-row', 'data-security-index': i });
      row.append(el(state, 'legend', instrument.label + (instrument.ticker ? ' · ' + instrument.ticker : '')));
      const controls = { instrument };
      for (const [field, key] of [['quantity', 'quantity'], ['average_cost', 'average'], ['currency', 'currency']]) {
        const label = el(state, 'label', t(state, key)), id = 'actual-' + i + '-' + field;
        const control = field === 'currency' ? el(state, 'select', undefined, { 'data-field': field, 'aria-label': t(state, key) }) : el(state, 'input', undefined, { type: 'text', inputmode: 'decimal', maxlength: '28', autocomplete: 'off', 'data-field': field, 'aria-label': t(state, key) });
        control.id = id; label.setAttribute('for', id);
        if (field === 'currency') for (const currency of CURRENCIES) control.append(el(state, 'option', currency, { value: currency }));
        label.append(control); row.append(label); controls[field] = control;
      }
      state.formRows.push(controls); form.append(row);
    });
    state.saveButton = el(state, 'button', t(state, 'save'), { type: 'submit', 'data-action': 'save' }); form.append(state.saveButton);
    form.addEventListener('submit', event => { event.preventDefault(); void save(state); }); root.append(form);
    const actions = el(state, 'div', undefined, { class: 'actual-actions' });
    state.exportButton = el(state, 'button', t(state, 'export'), { type: 'button', 'data-action': 'export' }); state.exportButton.addEventListener('click', () => exportFile(state));
    const importLabel = el(state, 'label', t(state, 'import'), { class: 'actual-import-label' });
    state.importInput = el(state, 'input', undefined, { type: 'file', accept: '.json,application/json', 'data-action': 'import', 'aria-label': t(state, 'import') }); state.importInput.addEventListener('change', () => { void importFile(state, state.importInput.files[0]); }); importLabel.append(state.importInput);
    const deleteButton = el(state, 'button', t(state, 'delete'), { type: 'button', 'data-action': 'delete' }); deleteButton.addEventListener('click', () => { void remove(state); });
    actions.append(state.exportButton, importLabel, deleteButton); root.append(actions, el(state, 'p', t(state, 'backup'), { class: 'actual-backup-note' }));
    state.notice = el(state, 'p', '', { 'data-actual-notice': '', role: 'status', 'aria-live': 'polite' }); root.append(state.notice, summaryContent(state));
    host.replaceChildren(root); populate(state); setBusy(state, false); if (state.initialError) notice(state, state.initialError);
    return { state: state.snapshot ? 'ACTUAL' : 'NOT_AVAILABLE' };
  }
  async function summary(host, options) {
    const state = await initialState(host, options); state.root = el(state, 'section', undefined, { class: 'device-actual actual-compact' });
    state.root.append(el(state, 'p', t(state, 'device'), { class: 'actual-device-badge' }), summaryContent(state));
    if (state.initialError) state.root.append(el(state, 'p', t(state, state.initialError), { role: 'status' }));
    host.replaceChildren(state.root);
    const update = async () => {
      if (!host.isConnected || hosts.get(host) !== state) { host.ownerDocument.removeEventListener('device-actual-changed', update); return; }
      try { const raw = await readStored(state.view); state.snapshot = raw === null ? null : validate(raw, state.catalog); repaintSummary(state); } catch (_) { state.snapshot = null; repaintSummary(state); }
    };
    host.ownerDocument.addEventListener('device-actual-changed', update);
    return { state: state.snapshot ? 'ACTUAL' : 'NOT_AVAILABLE' };
  }
  return Object.freeze({ mount, summary, validate, makeSnapshot, prepareImport, valuation });
});
