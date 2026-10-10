/* ACTUAL stays on this browser's device. No network or telemetry is used here. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DeviceActual = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'device-actual-holdings/1';
  const DB_NAME = 'investment-device-actual-v1', STORE = 'snapshots', KEY = 'actual', MARKET_KEY = 'market', API_RECORD_KEY = 'api-settings';
  const SHEET_SETTINGS_KEY = 'google-sheet-settings', IMPORT_HISTORY_KEY = 'market-import-history';
  const MAX_FILE_BYTES = 131072, CURRENCIES = Object.freeze(['USD', 'JPY', 'KRW']);
  const MISSING_RECORD = Object.freeze({ missingRecord: true });
  const DECIMAL = /^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/;
  const hosts = new WeakMap();
  const UI = {
    title: ['내 실제 보유 · ACTUAL', 'My actual holdings · ACTUAL'],
    device: ['이 기기에만 저장됨', 'Stored only on this device'],
    privacy: ['보유 정보는 이 브라우저의 IndexedDB에만 저장됩니다. 서버로 전송되지 않습니다.', 'Holdings are stored only in this browser’s IndexedDB. They are never sent to a server.'],
    backup: ['JSON 내보내기 파일은 기기에 남을 수 있습니다. 기기 삭제는 내보낸 파일을 삭제하지 않습니다.', 'An exported JSON file may remain on your device. Deleting browser holdings does not delete exported files.'],
    entry: ['수량·평균 매입가·통화를 입력하세요. 두 보유 숫자 칸을 비우면 해당 종목을 제외합니다. 가격과 환율은 보유 없이도 저장할 수 있습니다.', 'Enter quantity, average cost and currency. Leave both holdings number fields blank to exclude an instrument. Prices and FX can also be saved without holdings.'],
    quote: ['시장가격·환율과 기준 시점을 직접 입력하세요. 입력 시점의 기본값은 현재이며 수정할 수 있습니다. 7일 이상 지난 값은 STALE로 표시하고 계산에 유지합니다. 가격 또는 필요한 환율이 없으면 총 평가액·비중·TARGET 차이는 NOT_AVAILABLE입니다.', 'Enter market prices, FX and their as-of timestamps. Timestamps default to now and can be edited. Values at least 7 days old are marked STALE and remain in calculations. Without any held price or required FX, the total, weights and TARGET deltas are NOT_AVAILABLE.'],
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
    readFailed: ['기기 저장소를 열 수 없습니다. ACTUAL · NOT_AVAILABLE', 'Cannot open device storage. ACTUAL · NOT_AVAILABLE'],
    price: ['수동 시장가격', 'Manual market price'], priceTime: ['가격 기준 시점 · ISO 8601', 'Price as-of · ISO 8601'], source: ['가격 출처', 'Price source'],
    manual: ['수동', 'Manual'], none: ['없음', 'None'], fxTitle: ['수동 환율 · KRW 기준', 'Manual FX · KRW base'], fxTime: ['환율 기준 시점 · ISO 8601', 'FX as-of · ISO 8601'], fxRate: ['1 단위당 KRW', 'KRW per 1 unit'],
    native: ['원통화 시장 평가액', 'Native market value'], provenance: ['가격 출처·기준 시점', 'Price source and as-of'], fxProvenance: ['환율 출처·기준 시점', 'FX source and as-of'], stale: ['STALE · 7일 이상 지난 입력', 'STALE · Input at least 7 days old'],
    apiTitle: ['기기 API 키 설정', 'Device API key settings'], apiPrivacy: ['브라우저 직접 호출이 승인된 API 키만 입력하세요. 앱 시크릿이나 액세스 토큰은 입력하지 마세요. 키는 이 브라우저의 IndexedDB에만 저장되며 JSON 백업에 포함되지 않습니다.', 'Enter only an API key approved for direct browser calls. Do not enter an app secret or access token. The key is stored only in this browser’s IndexedDB and is excluded from JSON backups.'],
    apiKeyIssuance: ['Alpha Vantage 공식 무료 API 키 발급 (새 탭)', 'Alpha Vantage official free API key issuance (new tab)'],
    apiGuidance: ['본인의 무료 키는 이 기기에만 저장되고 백업에서 제외됩니다. 검증 전까지 API는 꺼져 있습니다. 키 없이도 가격·환율을 수동 입력할 수 있습니다.', 'Your own free key stays on this device and is excluded from backups. API remains OFF pending validation. You can manually enter prices and FX without a key.'],
    apiPending: ['서비스 선택 대기 · API 사용 안 함. 시세 갱신과 자동 호출은 비활성 상태입니다.', 'Service selection pending · API disabled. Quote refresh and automatic calls are disabled.'], apiService: ['API 서비스', 'API service'], apiKey: ['API 키', 'API key'], apiSave: ['API 키를 이 기기에 저장', 'Save API key on this device'], apiDelete: ['기기 API 키 삭제', 'Delete device API key'], apiRefresh: ['시세 새로고침', 'Refresh quotes'],
    apiYes: ['저장된 API 키: 있음', 'Stored API key: Yes'], apiNo: ['저장된 API 키: 없음', 'Stored API key: No'], apiSaved: ['API 키를 이 기기에 저장했습니다. API 호출은 비활성 상태입니다.', 'API key saved on this device. API calls remain disabled.'], apiRemoved: ['기기 API 키를 삭제했습니다.', 'Device API key deleted.'], apiInvalid: ['API 키 형식이 유효하지 않습니다. 저장된 키는 변경하지 않았습니다.', 'The API key format is invalid. The stored key was not changed.'], apiStorage: ['API 키 저장소를 사용할 수 없습니다. 저장된 키는 변경하지 않았습니다.', 'API key storage is unavailable. The stored key was not changed.']
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
  async function readStored(view, requestedKeys = [KEY, MARKET_KEY]) {
    const db = await openDatabase(view);
    return new Promise((resolve, reject) => {
      const values = {}; let tx;
      try {
        tx = db.transaction(STORE, 'readonly'); const store = tx.objectStore(STORE);
        for (const key of requestedKeys) {
          const request = store.get(key); request.onsuccess = () => { values[key] = request.result; };
          const presence = store.getKey(key); presence.onsuccess = () => { if (presence.result === undefined) values[key] = MISSING_RECORD; };
        }
      } catch (_) { db.close(); reject(new Error('STORAGE')); return; }
      tx.oncomplete = () => { db.close(); resolve(values); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error('STORAGE')); };
    });
  }
  function storedEqual(left, right, forward = new Map(), reverse = new Map()) {
    if (Object.is(left, right)) return true;
    if (left === MISSING_RECORD || right === MISSING_RECORD || left === null || right === null || typeof left !== 'object' || typeof right !== 'object') return false;
    if (forward.has(left) || reverse.has(right)) return forward.get(left) === right && reverse.get(right) === left;
    const tag = Object.prototype.toString.call(left);
    if (tag !== Object.prototype.toString.call(right) || Object.getPrototypeOf(left) !== Object.getPrototypeOf(right)) return false;
    forward.set(left, right); reverse.set(right, left);
    const equal = (a, b) => storedEqual(a, b, forward, reverse);
    if (tag === '[object Date]') return Object.is(left.getTime(), right.getTime());
    if (tag === '[object RegExp]') return left.source === right.source && left.flags === right.flags && left.lastIndex === right.lastIndex;
    if (tag === '[object Map]') {
      if (left.size !== right.size) return false;
      const other = right.entries();
      for (const [key, value] of left) { const next = other.next().value; if (!equal(key, next[0]) || !equal(value, next[1])) return false; }
      return true;
    }
    if (tag === '[object Set]') {
      if (left.size !== right.size) return false;
      const other = right.values();
      for (const value of left) if (!equal(value, other.next().value)) return false;
      return true;
    }
    if (tag === '[object ArrayBuffer]') {
      // Resizable buffers and their views carry hidden length-tracking state.
      // Preserve these corrupt records instead of comparing only current bytes.
      if (left.resizable || right.resizable) return false;
      if (left.byteLength !== right.byteLength) return false;
      const a = new Uint8Array(left), b = new Uint8Array(right);
      return a.every((value, i) => value === b[i]);
    }
    if (ArrayBuffer.isView(left)) return left.byteOffset === right.byteOffset && left.byteLength === right.byteLength && equal(left.buffer, right.buffer);
    if (['[object Boolean]', '[object Number]', '[object String]', '[object BigInt]'].includes(tag)) return Object.is(left.valueOf(), right.valueOf());
    // Opaque structured clones (for example Blob/File) cannot be compared by
    // metadata alone. Preserve them rather than guessing that cleanup is safe.
    if (!['[object Object]', '[object Array]', '[object Error]'].includes(tag)) return false;
    const a = Object.getOwnPropertyNames(left).sort(), b = Object.getOwnPropertyNames(right).sort();
    return a.length === b.length && a.every((key, i) => key === b[i] && equal(left[key], right[key]));
  }
  function storedValues(values) { return Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value === null ? MISSING_RECORD : value])); }
  async function commitStored(view, values, expected, isCurrent) {
    const db = await openDatabase(view);
    return new Promise((resolve, reject) => {
      let tx, conflict = false;
      try {
        tx = db.transaction(STORE, 'readwrite'); const store = tx.objectStore(STORE), entries = Object.entries(values);
        const write = () => {
          if (isCurrent && !isCurrent()) fail('CANCELLED');
          for (const [key, value] of entries) { if (value === null) store.delete(key); else store.put(value, key); }
        };
        const current = {}; let pending = entries.length;
        for (const [key] of entries) {
          const request = store.get(key); request.onsuccess = () => { current[key] = request.result; };
          const presence = store.getKey(key);
          presence.onsuccess = () => {
            if (presence.result === undefined) current[key] = MISSING_RECORD;
            if (--pending) return;
            try {
              if (entries.some(([key]) => !storedEqual(current[key], expected[key]))) { conflict = true; tx.abort(); return; }
              write();
            } catch (_) { try { tx.abort(); } catch (_) {} }
          };
        }
      } catch (_) { if (tx) { try { tx.abort(); } catch (_) {} } db.close(); reject(new Error('STORAGE')); return; }
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error(conflict ? 'CONFLICT' : 'STORAGE')); };
    });
  }
  function t(state, key) { return UI[key][state.locale === 'en-US' ? 1 : 0]; }
  function el(state, tag, text, attributes = {}) {
    const element = state.host.ownerDocument.createElement(tag); if (text !== undefined) element.textContent = text;
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value)); return element;
  }
  function marketApi(state) { const api = state.view.DeviceMarket; if (!api) fail('STORAGE'); return api; }
  function notice(state, key) { state.notice.textContent = t(state, key); state.notice.dataset.notice = key; }
  function errorNotice(state, error) { notice(state, error.message === 'INCOMPATIBLE' ? 'incompatible' : error.message === 'VERSION' ? 'version' : ['STORAGE', 'CONFLICT'].includes(error.message) ? 'storage' : 'invalid'); }
  function number(state, value) { return new Intl.NumberFormat(state.locale, { maximumFractionDigits: 8 }).format(value); }
  function percentage(state, value) { return value === null ? 'NOT_AVAILABLE' : new Intl.NumberFormat(state.locale, { style: 'percent', maximumFractionDigits: 2 }).format(value); }
  function points(state, value) { return value === null ? 'NOT_AVAILABLE' : new Intl.NumberFormat(state.locale, { maximumFractionDigits: 2, signDisplay: 'always' }).format(value * 100) + ' %p'; }
  function source(state, value) {
    if (value === 'GOOGLEFINANCE') return state.locale === 'en-US'
      ? 'GOOGLEFINANCE · Up to 20 minutes delayed · For information only'
      : 'GOOGLEFINANCE · 최대 20분 지연 · 정보용';
    return value === 'API' ? 'API' : value === 'MANUAL' ? t(state, 'manual') : t(state, 'none');
  }
  function timeStatus(state, value) {
    if (value === 'UNKNOWN') return state.locale === 'en-US' ? ' · Time unknown · Import time' : ' · 시각 미확인 · 불러온 시각';
    if (value === 'FX_UNKNOWN') return state.locale === 'en-US' ? ' · FX time unknown · Import time' : ' · 환율 시각 미확인 · 불러온 시각';
    return '';
  }
  function provenance(state, record) {
    if (!record) return t(state, 'none') + ' · NOT_AVAILABLE';
    return source(state, record.source) + ' · ' + record.as_of + timeStatus(state, record.time_status) + ' · ' + marketApi(state).staleness(record.as_of);
  }
  function valuesFor(state) {
    if (state.snapshot) validate(state.snapshot, state.catalog);
    // External quote arrays remain available to legacy callers; production
    // mounts use the independent device market record instead.
    if (state.externalQuotes) return valuation(state.snapshot, state.catalog, state.quotes);
    return marketApi(state).valuation(state.snapshot, state.catalog, state.market);
  }
  function summaryContent(state) {
    const box = el(state, 'section', undefined, { 'data-actual-summary': '', class: 'actual-summary' });
    box.append(el(state, 'h3', t(state, 'summary')));
    box.append(el(state, 'p', state.snapshot ? t(state, 'existing') : t(state, 'unavailable'), { 'data-actual-status': '', role: 'status' }));
    const values = valuesFor(state);
    box.append(el(state, 'p', t(state, values.reason === 'FX_NOT_AVAILABLE' ? 'fx' : values.reason === 'QUOTED' ? 'available' : values.reason === 'NO_POSITIONS' ? 'zero' : values.reason === 'CALCULATION_ERROR' ? 'calculation' : 'missing')));
    if (values.stale) box.append(el(state, 'p', t(state, 'stale'), { class: 'actual-stale', 'data-market-stale': '' }));
    box.append(el(state, 'p', t(state, 'total') + ': ' + (values.total === null ? 'NOT_AVAILABLE' : number(state, values.total) + ' ' + values.currency), { class: 'actual-total', 'data-market-total': '' }));
    if (values.rows.length) {
      const list = el(state, 'div', undefined, { class: 'actual-value-list' });
      for (const row of values.rows) {
        const instrument = state.catalog.instruments.find(candidate => canonical(candidate.security_reference) === canonical(row.security_reference));
        const card = el(state, 'div', undefined, { class: 'actual-value-row' }); card.append(el(state, 'strong', instrument.label + (instrument.ticker ? ' · ' + instrument.ticker : '')));
        const marketCurrency = state.externalQuotes ? row.currency : values.currency;
        const fields = [[t(state, 'quantity'), row.quantity], [t(state, 'average'), row.average_cost + ' ' + row.currency], [t(state, 'market') + ' · ' + marketCurrency, row.market_value === null ? 'NOT_AVAILABLE' : number(state, row.market_value) + ' ' + marketCurrency], [t(state, 'target'), percentage(state, row.target_units / state.catalog.total_units)], [t(state, 'weight'), percentage(state, row.weight)], [t(state, 'delta') + ' (%p)', points(state, row.delta)]];
        if (!state.externalQuotes) {
          fields.push([t(state, 'native'), row.market_value_native === null ? 'NOT_AVAILABLE' : number(state, row.market_value_native) + ' ' + row.market_currency_native]);
          fields.push([t(state, 'provenance'), source(state, row.quote_source) + ' · ' + (row.quote_as_of || 'NOT_AVAILABLE') + timeStatus(state, row.quote_time_status) + ' · ' + row.quote_status]);
          if (instrument.currency !== 'KRW') fields.push([t(state, 'fxProvenance'), source(state, row.fx_source) + ' · ' + (row.fx_as_of || 'NOT_AVAILABLE') + timeStatus(state, row.fx_time_status) + ' · ' + row.fx_status]);
        }
        const details = el(state, 'dl'); for (const [label, value] of fields) details.append(el(state, 'dt', label), el(state, 'dd', value)); card.append(details); list.append(card);
      }
      box.append(list);
    }
    return box;
  }
  function repaintSummary(state) {
    const old = state.root.querySelector('[data-actual-summary]'); if (old) old.replaceWith(summaryContent(state));
    if (state.exportButton) state.exportButton.disabled = !state.snapshot || state.busy;
    updateSources(state);
  }
  function updateSources(state) {
    const quotes = new Map(state.market ? state.market.quotes.map(quote => [canonical(quote.security_reference), quote]) : []);
    for (const row of state.formRows) row.source.textContent = t(state, 'source') + ': ' + provenance(state, quotes.get(canonical(row.instrument.security_reference)));
    for (const row of state.fxRows) row.source.textContent = provenance(state, state.market ? state.market.fx.find(fx => fx.currency === row.currency) : null);
  }
  function populate(state) {
    const saved = new Map(state.snapshot ? state.snapshot.themes.flatMap(theme => theme.holdings).map(row => [canonical(row.security_reference), row]) : []);
    const quotes = new Map(state.market ? state.market.quotes.map(quote => [canonical(quote.security_reference), quote]) : []), timestamp = new Date().toISOString();
    for (const row of state.formRows) {
      const value = saved.get(canonical(row.instrument.security_reference)), quote = quotes.get(canonical(row.instrument.security_reference));
      row.quantity.value = value ? value.quantity : ''; row.average_cost.value = value ? value.average_cost : ''; row.currency.value = value ? value.currency : row.instrument.currency;
      row.price.value = quote ? quote.price : ''; row.price_as_of.value = quote ? quote.as_of : timestamp;
    }
    for (const row of state.fxRows) {
      const fx = state.market ? state.market.fx.find(fx => fx.currency === row.currency) : null;
      row.rate.value = fx ? fx.rate : ''; row.fx_as_of.value = fx ? fx.as_of : timestamp;
    }
    updateSources(state);
  }
  function setBusy(state, busy) {
    state.busy = busy; for (const control of state.root.querySelectorAll('button, input, select')) control.disabled = busy;
    if (!busy && state.storageProblem) { if (state.saveButton) state.saveButton.disabled = true; if (state.importInput) state.importInput.disabled = true; }
    if (state.exportButton) state.exportButton.disabled = busy || !state.snapshot;
    for (const control of state.root.querySelectorAll('[data-api-service], [data-api-refresh]')) control.disabled = true;
  }
  function announce(state) { state.host.ownerDocument.dispatchEvent(new state.view.Event('device-actual-changed')); }
  async function save(state) {
    if (state.busy || state.storageProblem) return;
    setBusy(state, true);
    try {
      const rows = [], quotes = [], fx = [], timestamp = new Date().toISOString();
      for (const row of state.formRows) {
        const quantity = row.quantity.value.trim(), average_cost = row.average_cost.value.trim();
        if (quantity || average_cost) rows.push({ security_reference: clone(row.instrument.security_reference), quantity, average_cost, currency: row.currency.value });
        const price = row.price.value.trim(), as_of = row.price_as_of.value.trim();
        if (!price) continue;
        const previous = state.market ? state.market.quotes.find(quote => canonical(quote.security_reference) === canonical(row.instrument.security_reference)) : null;
        const unchanged = previous && previous.price === price && previous.as_of === as_of;
        quotes.push(unchanged ? clone(previous) : { security_reference: clone(row.instrument.security_reference), price, currency: row.instrument.currency, as_of, available_at: timestamp, source: 'MANUAL' });
      }
      for (const row of state.fxRows) {
        const rate = row.rate.value.trim(), as_of = row.fx_as_of.value.trim(); if (!rate) continue;
        const previous = state.market ? state.market.fx.find(fx => fx.currency === row.currency) : null, unchanged = previous && previous.rate === rate && previous.as_of === as_of;
        fx.push(unchanged ? clone(previous) : { currency: row.currency, rate, as_of, available_at: timestamp, source: 'MANUAL' });
      }
      const next = makeSnapshot(state.catalog, rows, state.snapshot), market = marketApi(state).makeMarket(state.catalog, quotes, fx, state.market);
      const raw = { [KEY]: next, [MARKET_KEY]: market };
      await commitStored(state.view, raw, state.raw);
      state.snapshot = next; state.market = market; state.raw = storedValues(raw); repaintSummary(state); notice(state, 'saved'); announce(state);
    } catch (error) { errorNotice(state, error); } finally { setBusy(state, false); }
  }
  async function importFile(state, file) {
    if (!file || state.busy || state.storageProblem) return;
    setBusy(state, true);
    try {
      if (file.size > MAX_FILE_BYTES) { notice(state, 'tooLarge'); return; }
      const text = await file.text();
      if (new state.view.TextEncoder().encode(text).byteLength > MAX_FILE_BYTES) { notice(state, 'tooLarge'); return; }
      const payload = JSON.parse(text);
      if (state.view.DeviceBackup?.accepts ? state.view.DeviceBackup.accepts(payload) : payload.schema === state.view.DeviceBackup?.SCHEMA) {
        if (!state.view.confirm(t(state, 'overwrite'))) return;
        await state.view.DeviceBackup.restore(state.view, state.catalog, payload);
        state.view.document.dispatchEvent(new state.view.Event('device-backup-restored')); return;
      }
      const imported = marketApi(state).importBackup(payload, state.catalog);
      const sourceSnapshot = validate(imported.snapshot, state.catalog);
      if ((state.raw[KEY] !== MISSING_RECORD || state.raw[MARKET_KEY] !== MISSING_RECORD) && !state.view.confirm(t(state, 'overwrite'))) { notice(state, 'canceled'); return; }
      const next = prepareImport(sourceSnapshot, state.catalog, state.snapshot);
      let market = null;
      if (payload.schema !== SCHEMA) {
        market = marketApi(state).validateMarket(imported.market, state.catalog);
        if (state.market) market.version = Math.max(market.version, state.market.version + 1);
        market.available_at = new Date().toISOString();
        market = marketApi(state).validateMarket(market, state.catalog, state.market ? { minimumVersion: state.market.version } : {});
      }
      const raw = { [KEY]: next, [MARKET_KEY]: market };
      await commitStored(state.view, raw, state.raw);
      state.snapshot = next; state.market = market; state.raw = storedValues(raw); populate(state); repaintSummary(state); notice(state, 'imported'); announce(state);
    } catch (error) { errorNotice(state, error); } finally { state.importInput.value = ''; setBusy(state, false); }
  }
  async function exportFile(state) {
    if (!state.snapshot || state.busy) return;
    try {
      const payload = await state.view.DeviceBackup.read(state.view, state.catalog);
      const blob = new state.view.Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = state.view.URL.createObjectURL(blob), anchor = el(state, 'a', undefined, { href: url, download: 'device-actual-holdings.json' });
      state.root.append(anchor); anchor.click(); anchor.remove(); state.view.setTimeout(() => state.view.URL.revokeObjectURL(url), 1000); notice(state, 'exported');
    } catch (error) { errorNotice(state, error); }
  }
  async function remove(state) {
    if (state.busy) return;
    if (!state.view.confirm(t(state, 'removeConfirm'))) { notice(state, 'canceled'); return; }
    setBusy(state, true);
    try {
      const history = await readStored(state.view, [IMPORT_HISTORY_KEY]);
      const raw = { [KEY]: null, [MARKET_KEY]: null, [IMPORT_HISTORY_KEY]: null };
      await commitStored(state.view, raw, {...state.raw, ...history});
      state.raw = storedValues(raw); state.snapshot = null; state.market = null; state.storageProblem = false; populate(state); repaintSummary(state); notice(state, 'removed'); announce(state);
    } catch (error) { errorNotice(state, error); } finally { setBusy(state, false); }
  }
  async function initialState(host, options) {
    if (!host || !host.ownerDocument || !options) fail('INVALID'); catalogIndex(options.catalog);
    const state = { host, view: host.ownerDocument.defaultView, catalog: clone(options.catalog), locale: options.locale === 'en-US' ? 'en-US' : 'ko-KR', quotes: options.quotes || [], externalQuotes: Object.prototype.hasOwnProperty.call(options, 'quotes'), snapshot: null, market: null, raw: { [KEY]: MISSING_RECORD, [MARKET_KEY]: MISSING_RECORD }, storageProblem: false, busy: false, formRows: [], fxRows: [] };
    try {
      state.raw = await readStored(state.view);
      if (state.raw[KEY] !== MISSING_RECORD) state.snapshot = validate(state.raw[KEY], state.catalog);
      if (state.raw[MARKET_KEY] !== MISSING_RECORD) state.market = marketApi(state).validateMarket(state.raw[MARKET_KEY], state.catalog);
    } catch (error) { state.snapshot = null; state.market = null; state.storageProblem = true; state.initialError = state.raw[KEY] !== MISSING_RECORD || state.raw[MARKET_KEY] !== MISSING_RECORD ? 'corrupt' : 'readFailed'; }
    hosts.set(host, state); return state;
  }
  function inputLabel(state, row, field, text, attributes = {}) {
    const label = el(state, 'label', text), control = el(state, 'input', undefined, { type: 'text', autocomplete: 'off', 'data-field': field, 'aria-label': text, ...attributes });
    label.append(control); row.append(label); return control;
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
      controls.quantity = inputLabel(state, row, 'quantity', t(state, 'quantity'), { inputmode: 'decimal', maxlength: '28' });
      controls.average_cost = inputLabel(state, row, 'average_cost', t(state, 'average'), { inputmode: 'decimal', maxlength: '28' });
      const currencyLabel = el(state, 'label', t(state, 'currency')); controls.currency = el(state, 'select', undefined, { 'data-field': 'currency', 'aria-label': t(state, 'currency') });
      for (const currency of CURRENCIES) controls.currency.append(el(state, 'option', currency, { value: currency })); currencyLabel.append(controls.currency); row.append(currencyLabel);
      controls.price = inputLabel(state, row, 'price', t(state, 'price') + ' · ' + instrument.currency, { inputmode: 'decimal', maxlength: '28' });
      controls.price_as_of = inputLabel(state, row, 'price_as_of', t(state, 'priceTime'), { maxlength: '35', placeholder: 'YYYY-MM-DDTHH:mm:ss.sssZ' });
      controls.source = el(state, 'p', '', { class: 'actual-quote-source', 'data-quote-source': '' }); row.append(controls.source);
      state.formRows.push(controls); form.append(row);
    });
    const fxBox = el(state, 'fieldset', undefined, { class: 'actual-fx-box' }); fxBox.append(el(state, 'legend', t(state, 'fxTitle')));
    for (const currency of ['USD', 'JPY']) {
      const row = el(state, 'div', undefined, { class: 'actual-fx-row', 'data-fx-currency': currency }), controls = { currency };
      controls.rate = inputLabel(state, row, 'rate', currency + '/KRW · ' + t(state, 'fxRate'), { inputmode: 'decimal', maxlength: '28' });
      controls.fx_as_of = inputLabel(state, row, 'fx_as_of', t(state, 'fxTime'), { maxlength: '35', placeholder: 'YYYY-MM-DDTHH:mm:ss.sssZ' });
      controls.source = el(state, 'p', '', { class: 'actual-quote-source', 'data-fx-source': currency }); row.append(controls.source); fxBox.append(row); state.fxRows.push(controls);
    }
    form.append(fxBox); state.saveButton = el(state, 'button', t(state, 'save'), { type: 'submit', 'data-action': 'save' }); form.append(state.saveButton);
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
      try {
        const raw = await readStored(state.view), snapshot = raw[KEY] === MISSING_RECORD ? null : validate(raw[KEY], state.catalog), market = raw[MARKET_KEY] === MISSING_RECORD ? null : marketApi(state).validateMarket(raw[MARKET_KEY], state.catalog);
        state.snapshot = snapshot; state.market = market; state.raw = raw; repaintSummary(state);
      } catch (_) { state.snapshot = null; state.market = null; repaintSummary(state); }
    };
    host.ownerDocument.addEventListener('device-actual-changed', update);
    return { state: state.snapshot ? 'ACTUAL' : 'NOT_AVAILABLE' };
  }
  function validateSettings(value) {
    keys(value, ['schema', 'service', 'enabled', 'api_key']);
    if (value.schema !== 'device-api-settings/1' || value.service !== 'NOT_SELECTED' || value.enabled !== false || typeof value.api_key !== 'string' || !/^[\x21-\x7e]{1,512}$/.test(value.api_key)) fail('INVALID');
    return clone(value);
  }
  async function settings(host, options) {
    if (!host || !host.ownerDocument || !options) fail('INVALID'); catalogIndex(options.catalog);
    const state = { host, view: host.ownerDocument.defaultView, locale: options.locale === 'en-US' ? 'en-US' : 'ko-KR', raw: { [API_RECORD_KEY]: MISSING_RECORD }, busy: false, storageProblem: false };
    let stored = false;
    try { state.raw = await readStored(state.view, [API_RECORD_KEY]); if (state.raw[API_RECORD_KEY] !== MISSING_RECORD) { validateSettings(state.raw[API_RECORD_KEY]); stored = true; } }
    catch (_) { state.storageProblem = true; }
    const root = el(state, 'section', undefined, { class: 'device-actual actual-api-settings', 'data-device-api-settings': '' }); state.root = root;
    root.append(el(state, 'h2', t(state, 'apiTitle')), el(state, 'p', t(state, 'apiPrivacy')), el(state, 'p', t(state, 'apiPending')));
    const issuance = el(state, 'p');
    issuance.append(el(state, 'a', t(state, 'apiKeyIssuance'), { href: 'https://www.alphavantage.co/support/#api-key', target: '_blank', rel: 'noopener noreferrer', referrerpolicy: 'no-referrer', 'data-api-key-issuance': '' }));
    root.append(issuance, el(state, 'p', t(state, 'apiGuidance'), { 'data-api-guidance': '' }));
    const serviceLabel = el(state, 'label', t(state, 'apiService')), service = el(state, 'select', undefined, { 'data-api-service': '', disabled: '' }); service.append(el(state, 'option', t(state, 'apiPending'), { value: 'NOT_SELECTED' })); serviceLabel.append(service); root.append(serviceLabel);
    const form = el(state, 'form', undefined, { class: 'actual-api-form' }), label = el(state, 'label', t(state, 'apiKey'));
    state.keyInput = el(state, 'input', undefined, { type: 'password', autocomplete: 'new-password', maxlength: '512', 'data-api-key': '', 'aria-label': t(state, 'apiKey'), spellcheck: 'false' }); label.append(state.keyInput); form.append(label);
    state.saveButton = el(state, 'button', t(state, 'apiSave'), { type: 'submit', 'data-api-action': 'save' }); form.append(state.saveButton); root.append(form);
    const actions = el(state, 'div', undefined, { class: 'actual-actions' }), removeButton = el(state, 'button', t(state, 'apiDelete'), { type: 'button', 'data-api-action': 'delete' }), refresh = el(state, 'button', t(state, 'apiRefresh'), { type: 'button', 'data-api-refresh': '', disabled: '' }); actions.append(removeButton, refresh); root.append(actions);
    const status = el(state, 'p', '', { 'data-api-status': '', role: 'status' }); root.append(status);
    const setStatus = value => { status.textContent = t(state, value ? 'apiYes' : 'apiNo'); status.dataset.stored = value ? 'yes' : 'no'; };
    state.notice = el(state, 'p', '', { 'data-api-notice': '', role: 'status', 'aria-live': 'polite' }); root.append(state.notice); setStatus(stored);
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (state.busy || state.storageProblem) return; setBusy(state, true);
      try {
        const value = validateSettings({ schema: 'device-api-settings/1', service: 'NOT_SELECTED', enabled: false, api_key: state.keyInput.value });
        const raw = { [API_RECORD_KEY]: value }; await commitStored(state.view, raw, state.raw); state.raw = storedValues(raw); state.keyInput.value = ''; setStatus(true); notice(state, 'apiSaved');
      } catch (error) { notice(state, ['STORAGE', 'CONFLICT'].includes(error.message) ? 'apiStorage' : 'apiInvalid'); }
      finally { state.keyInput.value = ''; setBusy(state, false); }
    });
    removeButton.addEventListener('click', async () => {
      if (state.busy) return; setBusy(state, true);
      try { const raw = { [API_RECORD_KEY]: null }; await commitStored(state.view, raw, state.raw); state.raw = storedValues(raw); state.storageProblem = false; state.keyInput.value = ''; setStatus(false); notice(state, 'apiRemoved'); }
      catch (_) { notice(state, 'apiStorage'); } finally { setBusy(state, false); }
    });
    host.replaceChildren(root); setBusy(state, false); if (state.storageProblem) notice(state, 'apiStorage');
    return { service: 'NOT_SELECTED', enabled: false, keyStored: stored };
  }
  function validateSheetSettings(value) {
    keys(value, ['schema', 'enabled', 'spreadsheet_id', 'range']);
    if (value.schema !== 'device-google-sheet-settings/1' || typeof value.enabled !== 'boolean'
      || typeof value.spreadsheet_id !== 'string' || (value.spreadsheet_id !== '' && !/^[A-Za-z0-9_-]{20,100}$/.test(value.spreadsheet_id))
      || typeof value.range !== 'string' || value.range.length < 1 || value.range.length > 160
      || /[\x00-\x1f\x7f]/.test(value.range) || /https?:|ya29\./i.test(value.range)) fail('INVALID');
    return clone(value);
  }
  async function sheetSettings(view, value) {
    const raw = await readStored(view, [SHEET_SETTINGS_KEY]);
    const previous = raw[SHEET_SETTINGS_KEY] === MISSING_RECORD
      ? {schema:'device-google-sheet-settings/1',enabled:false,spreadsheet_id:'',range:'Quotes!A1:C22'}
      : validateSheetSettings(raw[SHEET_SETTINGS_KEY]);
    if (value === undefined) return previous;
    const next = validateSheetSettings(value);
    await commitStored(view, {[SHEET_SETTINGS_KEY]:next}, raw);
    return next;
  }
  function approvedImportNames(catalog) {
    catalogIndex(catalog);
    return new Set([...catalog.instruments.map(row => row.label), 'USD/KRW', 'JPY/KRW']);
  }
  function validateImportHistory(value, catalog, marketApi) {
    keys(value, ['schema', 'entries']);
    if (value.schema !== 'device-market-import-history/1' || !Array.isArray(value.entries) || value.entries.length > 1000) fail('INVALID');
    const names = approvedImportNames(catalog);
    let previous = 0;
    for (const entry of value.entries) {
      keys(entry, ['at', 'method', 'success_count', 'failure_names', 'warning_count', 'quotes', 'fx']);
      const at = clock(entry.at);
      if (at < previous || at > Date.now() || !['google-sheet','paste'].includes(entry.method)
        || !Number.isSafeInteger(entry.success_count) || entry.success_count < 0 || entry.success_count > 21
        || !Number.isSafeInteger(entry.warning_count) || entry.warning_count < 0 || entry.warning_count > 1000
        || !Array.isArray(entry.failure_names) || entry.failure_names.length > 21
        || new Set(entry.failure_names).size !== entry.failure_names.length || entry.failure_names.some(name => !names.has(name))) fail('INVALID');
      const checked = marketApi.makeMarket(catalog, entry.quotes, entry.fx, null, at);
      if (checked.quotes.length + checked.fx.length !== entry.success_count
        || [...checked.quotes, ...checked.fx].some(row => row.source !== 'GOOGLEFINANCE')) fail('INVALID');
      previous = at;
    }
    return clone(value);
  }
  async function readMarketImportHistory(view, catalog) {
    const raw = await readStored(view, [IMPORT_HISTORY_KEY]);
    const history = raw[IMPORT_HISTORY_KEY] === MISSING_RECORD ? {entries:[]}
      : validateImportHistory(raw[IMPORT_HISTORY_KEY], catalog, view.DeviceMarket);
    return history.entries.map(({at,method,success_count,failure_names,warning_count}) => ({at,method,success_count,failure_names,warning_count}));
  }
  async function applyMarketImport(view, catalog, result, options = {}) {
    const active = () => !options.isCurrent || options.isCurrent();
    if (!active()) fail('CANCELLED');
    if (!plain(result) || !Array.isArray(result.quotes) || !Array.isArray(result.fx)
      || !Array.isArray(result.successes) || !Array.isArray(result.failures) || !Array.isArray(result.warnings)
      || result.successes.length + result.failures.length > 21 || result.warnings.length > 1000
      || !['google-sheet','paste'].includes(options.method)) fail('INVALID');
    const api = view.DeviceMarket;
    if (!api || !view.GoogleSheetCore) fail('STORAGE');
    const names = approvedImportNames(catalog);
    if ([...result.successes,...result.failures].some(row => !plain(row) || !names.has(row.name))
      || new Set([...result.successes,...result.failures].map(row => row.name)).size !== result.successes.length + result.failures.length
      || result.failures.some(row => row.state !== 'NOT_AVAILABLE')) fail('INVALID');
    const now = options.now === undefined ? Date.now() : nowMillis(options.now), at = new Date(now).toISOString();
    const fresh = api.makeMarket(catalog, result.quotes, result.fx, null, now);
    if (fresh.quotes.length + fresh.fx.length !== result.successes.length
      || [...fresh.quotes,...fresh.fx].some(row => row.source !== 'GOOGLEFINANCE')) fail('INVALID');
    const raw = await readStored(view, [MARKET_KEY, IMPORT_HISTORY_KEY]);
    if (!active()) fail('CANCELLED');
    const previous = raw[MARKET_KEY] === MISSING_RECORD ? null : api.validateMarket(raw[MARKET_KEY], catalog, {now});
    const history = raw[IMPORT_HISTORY_KEY] === MISSING_RECORD ? {schema:'device-market-import-history/1',entries:[]}
      : validateImportHistory(raw[IMPORT_HISTORY_KEY], catalog, api);
    history.entries.push({at,method:options.method,success_count:result.successes.length,
      failure_names:result.failures.map(row => row.name),warning_count:result.warnings.length,quotes:fresh.quotes,fx:fresh.fx});
    validateImportHistory(history, catalog, api);
    const values = {[IMPORT_HISTORY_KEY]:history};
    if (result.successes.length) values[MARKET_KEY] = view.GoogleSheetCore.apply(catalog, previous, result, now);
    await commitStored(view, values, raw, active);
    if (view.document) view.document.dispatchEvent(new view.Event('device-actual-changed'));
    return result;
  }
  async function readHoldings(view, catalog) {
    const raw = await readStored(view, [KEY]);
    return raw[KEY] === MISSING_RECORD ? null : validate(raw[KEY], catalog);
  }
  async function restoreHoldings(view, catalog, snapshot) {
    if (snapshot !== null) validate(snapshot, catalog);
    const raw = await readStored(view, [KEY]);
    const previous = raw[KEY] === MISSING_RECORD ? null : validate(raw[KEY], catalog);
    const next = snapshot === null ? null : prepareImport(snapshot, catalog, previous);
    await commitStored(view, {[KEY]:next}, raw);
    if (view.document) view.document.dispatchEvent(new view.Event('device-actual-changed'));
    return next;
  }
  return Object.freeze({ mount, summary, settings, validate, makeSnapshot, prepareImport, valuation,
    sheetSettings, applyMarketImport, readMarketImportHistory, readHoldings, restoreHoldings });
});
