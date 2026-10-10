/* Google credentials are held only by this module's memory closures. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GoogleSheetQuotes = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';
  const SCOPE = FILE_SCOPE + ' email';
  const HISTORY_SYMBOLS = new Set(['ASML','LRCX','KLAC','NVDA','AMD','AVGO','QCOM','INTC','MSFT','GOOGL','AMZN','RTX','SYK','ETN','HUBB','GEV','ROK','042700.KS','8035.T']);
  const HISTORY_RANGES = new Set(['1mo','3mo','6mo','1y','2y','5y']);
  const HISTORY_ERRORS = new Set(['CONFIG_UNAVAILABLE','AUTH_FORBIDDEN','AUTH_UNAVAILABLE','REQUEST_INVALID','ORIGIN_FORBIDDEN','RATE_LIMITED','RATE_LIMIT_UNAVAILABLE','YAHOO_BLOCKED','YAHOO_UNAVAILABLE','YAHOO_TIMEOUT','YAHOO_FORMAT_CHANGED','YAHOO_TOO_LARGE','TIINGO_UNAVAILABLE','TIINGO_TIMEOUT','TIINGO_FORMAT_CHANGED','TIINGO_TOO_LARGE','KRX_UNAVAILABLE','KRX_TIMEOUT','KRX_FORMAT_CHANGED','KRX_TOO_LARGE','KRX_RANGE_UNSUPPORTED','HISTORY_UNAVAILABLE']);
  const CLIENT_SCRIPT = 'https://accounts.google.com/gsi/client';
  const CLIENT_STYLE = 'https://accounts.google.com/gsi/style';
  // The current GIS token-client SDK skips its inline button styles when this
  // marker exists. Load Google's external CSS under a strict CSP. GIS buttons
  // and One Tap are outside this integration; recheck this marker on updates.
  const STYLE_ID = 'googleidentityservice_button_styles';
  const DEFAULT_RANGE = 'Quotes!A1:C22', sessions = new WeakMap(), hosts = new WeakMap();
  const TEXT = {
    title: ['구글 시트 시세 · 선택 기능', 'Google Sheet quotes · Optional'],
    detail: ['비공개 구글 시트를 이 기기에서 읽기 전용으로 읽습니다. 최대 20분 지연 · 정보용. 수동 입력은 계속 사용할 수 있습니다.', 'Read your private Google Sheet directly on this device with read-only access. Up to 20 minutes delayed · Informational. Manual entry remains available.'],
    enable: ['구글 시트 사용 · 기본 OFF', 'Use Google Sheets · OFF by default'],
    id: ['스프레드시트 ID 또는 구글 시트 URL', 'Spreadsheet ID or Google Sheet URL'], range: ['읽을 범위', 'Range to read'],
    privacy: ['ID·범위는 이 기기에만 저장되며 백업에서 제외됩니다. 로그인 토큰은 메모리에만 보관하며 약 1시간 후 다시 연결해야 합니다.', 'ID and range stay on this device and are excluded from backups. The sign-in token stays only in memory; reconnect after about one hour.'],
    save: ['시트 설정을 이 기기에 저장', 'Save Sheet settings on this device'], saved: ['시트 설정을 이 기기에 저장했습니다.', 'Sheet settings saved on this device.'],
    prepare: ['구글 로그인 준비', 'Prepare Google sign-in'], login: ['구글 로그인 · 읽기 전용', 'Google sign-in · Read-only'], fetch: ['구글 시트에서 불러오기', 'Load from Google Sheet'], disconnect: ['구글 연결 해제', 'Disconnect Google'],
    ready: ['로그인 준비가 끝났습니다. 로그인 버튼을 눌러 연결하세요.', 'Sign-in is ready. Press the sign-in button to connect.'], connected: ['구글 연결됨 · 읽기 전용 · 약 1시간', 'Google connected · Read-only · About one hour'], off: ['OFF · 구글 호출 없음', 'OFF · No Google requests'], disconnected: ['연결되지 않음 · 불러오기는 버튼을 누를 때만 실행됩니다.', 'Disconnected · Quotes load only when you press the button.'],
    pasteTitle: ['예비 입력 · 일괄 붙여넣기', 'Fallback · Bulk paste'], pasteHelp: ['시트의 A~C열(code, price, tradetime)을 복사해 붙여넣으세요. 탭 또는 쉼표 구분, 로그인 없이 사용할 수 있습니다.', 'Copy and paste Sheet columns A–C (code, price, tradetime). Tab or comma separated; no sign-in required.'], pasteLabel: ['시트에서 복사한 텍스트', 'Text copied from the Sheet'], paste: ['붙여넣은 시세를 이 기기에 저장', 'Save pasted quotes on this device'],
    success: ['성공', 'Success'], failure: ['실패', 'Failed'], warning: ['경고', 'Warning'], history: ['시세 불러오기 변경 이력', 'Quote import history'], emptyHistory: ['불러오기 이력이 없습니다.', 'No imports yet.'], methodGoogle: ['구글 시트', 'Google Sheet'], methodPaste: ['붙여넣기', 'Paste'], unknown: ['표에 없는 코드는 무시했습니다.', 'Unmapped codes were ignored.'], duplicate: ['중복 코드의 시세는 NOT_AVAILABLE입니다.', 'Quotes with duplicate codes are NOT_AVAILABLE.'],
    invalid: ['시트 ID·범위 또는 붙여넣기 형식을 확인하세요. 기존 시세는 유지됩니다.', 'Check the Sheet ID, range or pasted format. Existing quotes are preserved.'], storage: ['기기 저장을 완료하지 못했습니다. 기존 시세는 유지됩니다.', 'Device saving did not complete. Existing quotes are preserved.'], auth: ['로그인이 만료되었거나 연결되지 않았습니다. 구글 로그인 버튼을 다시 누르세요.', 'Sign-in expired or is disconnected. Press Google sign-in again.'], authFailed: ['구글 연결을 완료하지 못했습니다. 로그인 버튼으로 다시 시도하세요.', 'Google connection did not complete. Try the sign-in button again.'], readFailed: ['구글 시트를 읽지 못했습니다. 접근 권한·ID·범위를 확인하세요. 기존 시세는 유지됩니다.', 'Could not read the Google Sheet. Check access, ID and range. Existing quotes are preserved.'], removed: ['구글 연결을 해제하고 메모리 토큰을 삭제했습니다.', 'Google disconnected and the memory token was removed.'], canceled: ['불러오기를 취소했습니다. 기존 시세는 유지됩니다.', 'Import canceled. Existing quotes are preserved.'], busy: ['처리 중…', 'Working…']
  };
  function fail(code) { throw new Error(code); }
  function extractSpreadsheetId(input) {
    if (typeof input !== 'string') fail('INVALID');
    const value = input.trim();
    if (/^[A-Za-z0-9_-]{20,100}$/.test(value)) return value;
    let url; try { url = new URL(value); } catch (_) { fail('INVALID'); }
    if (url.protocol !== 'https:' || url.hostname !== 'docs.google.com' || url.port || url.username || url.password) fail('INVALID');
    const match = /^\/spreadsheets\/(?:u\/\d+\/)?d\/([A-Za-z0-9_-]{20,100})(?:\/(?:edit|view|preview|copy))?\/?$/.exec(url.pathname);
    if (!match) fail('INVALID'); return match[1];
  }
  function sheetsURL(id, range) {
    if (extractSpreadsheetId(id) !== id || typeof range !== 'string' || !range.trim() || range.length > 160 || /[\x00-\x1f\x7f]/.test(range)) fail('INVALID');
    return 'https://sheets.googleapis.com/v4/spreadsheets/' + encodeURIComponent(id) + '/values/' + encodeURIComponent(range) + '?valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=SERIAL_NUMBER';
  }
  function validScope(value) {
    if (typeof value !== 'string') return false;
    const aliases = {'https://www.googleapis.com/auth/userinfo.email':'email','https://www.googleapis.com/auth/userinfo.profile':'profile'};
    const scopes = new Set(value.trim().split(/\s+/).map(scope => Object.hasOwn(aliases,scope)?aliases[scope]:scope));
    const allowed = new Set([FILE_SCOPE,'email','openid','profile']);
    return scopes.has(FILE_SCOPE) && scopes.has('email') && [...scopes].every(scope=>allowed.has(scope));
  }
  function historyOrigin(value) {
    const label = '[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?';
    if (typeof value !== 'string' || !new RegExp('^https://' + label + '\\.' + label + '\\.workers\\.dev/?$').test(value)) fail('REQUEST_INVALID');
    return value.replace(/\/$/, '');
  }
  function sessionFor(view, clientId) {
    let shared = sessions.get(view);
    if (!shared || shared.clientId !== clientId) {
      if (shared) void shared.session.disconnect();
      shared = {clientId,session:createSession(view,{clientId})}; sessions.set(view,shared);
    }
    return shared.session;
  }
  function createSession(view, options) {
    const clientId = options.clientId, now = options.now || (() => Date.now()), listeners = new Set(), controllers = new Set();
    let enabled = false, token = '', expiresAt = 0, epoch = 0, pending = false, preparing = null, timer = null, controller = null, error = '';
    let pickerCancel = null;
    function oauth() { return view.google && view.google.accounts && view.google.accounts.oauth2; }
    function notify() { for (const listener of listeners) listener(); }
    function invalidate() {
      if(pickerCancel){const stop=pickerCancel;pickerCancel=null;stop();}
      token = ''; expiresAt = 0; pending = false; epoch++;
      if (timer !== null) { view.clearTimeout(timer); timer = null; }
      if (controller) { controller.abort(); controller = null; }
      for (const abort of controllers) abort.abort(); controllers.clear();
    }
    function expire() { if (token && expiresAt <= now()) { invalidate(); error = 'AUTH_REQUIRED'; notify(); } }
    function state() { expire(); return { enabled, ready: !!oauth(), connected: !!token, pending, preparing: !!preparing, error }; }
    function setEnabled(value) { enabled = value === true; error = ''; if (!enabled) invalidate(); notify(); }
    function prepare() {
      if (!enabled || !clientId) return Promise.reject(new Error('OFF'));
      if (oauth()) return Promise.resolve();
      if (preparing) return preparing;
      const attempt = epoch;
      preparing = new Promise((resolve, reject) => {
        function loadScript() {
          if (!enabled || attempt !== epoch) { reject(new Error('CANCELED')); return; }
          const script = view.document.createElement('script'); script.src = CLIENT_SCRIPT; script.async = true; script.referrerPolicy = 'no-referrer';
          script.onload = () => {
            if (!enabled || attempt !== epoch) reject(new Error('CANCELED'));
            else if (oauth()) resolve();
            else reject(new Error('AUTH_FAILED'));
          };
          script.onerror = () => { script.remove(); reject(new Error('AUTH_FAILED')); };
          view.document.head.append(script);
        }
        const existing = view.document.getElementById(STYLE_ID);
        if (existing) {
          if (existing.tagName === 'LINK' && existing.rel === 'stylesheet' && existing.href === CLIENT_STYLE && existing.dataset.googleSheetReady === 'true') loadScript();
          else reject(new Error('AUTH_FAILED'));
          return;
        }
        const style = view.document.createElement('link');
        style.id = STYLE_ID; style.rel = 'stylesheet'; style.href = CLIENT_STYLE; style.referrerPolicy = 'no-referrer';
        style.onload = () => { style.dataset.googleSheetReady = 'true'; loadScript(); };
        style.onerror = () => { style.remove(); reject(new Error('AUTH_FAILED')); };
        view.document.head.append(style);
      }).finally(() => { preparing = null; notify(); });
      notify(); return preparing;
    }
    function login() {
      if (!enabled || !clientId) fail('OFF');
      if (!oauth()) fail('NOT_READY');
      invalidate(); const attempt = epoch; pending = true; error = ''; notify();
      function rejected(code='AUTH_FAILED') { if (attempt !== epoch || !enabled) return; pending = false; error = code; notify(); }
      try {
        const client = oauth().initTokenClient({ client_id: clientId, scope: SCOPE, include_granted_scopes: false,
          callback(response) {
            if (attempt !== epoch || !enabled) return;
            if (!response || response.error || typeof response.access_token !== 'string' || !/^[A-Za-z0-9._~-]{1,4096}$/.test(response.access_token) || !Number.isFinite(Number(response.expires_in)) || Number(response.expires_in) <= 0 || (response.token_type && response.token_type !== 'Bearer') || !validScope(response.scope)) { rejected(); return; }
            token = response.access_token; expiresAt = now() + Math.min(Number(response.expires_in), 3600) * 1000; pending = false;
            timer = view.setTimeout(() => { expire(); }, Math.max(1, expiresAt - now())); notify();
          }, error_callback: response => {
            const codes={popup_failed_to_open:'AUTH_POPUP_FAILED_TO_OPEN',popup_closed:'AUTH_POPUP_CLOSED'};
            rejected(response&&Object.hasOwn(codes,response.type)?codes[response.type]:'AUTH_POPUP_UNKNOWN');
          } });
        // This call remains synchronous with the user's real button click.
        client.requestAccessToken({ prompt: 'consent' });
      } catch (_) { rejected(); }
    }
    async function disconnect() {
      const previous = token; invalidate(); error = ''; notify();
      if (previous && oauth()) { try { oauth().revoke(previous, () => {}); } catch (_) { /* Memory is cleared even if revocation fails. */ } }
    }
    async function sheetRequest(path,method='GET',body=null) {
      expire();if(!enabled||!token)fail('AUTH_REQUIRED');
      const attempt=epoch,abort=new view.AbortController();controllers.add(abort);
      const current=()=>enabled&&token&&epoch===attempt&&!abort.signal.aborted;
      try{
        const response=await view.fetch('https://sheets.googleapis.com/v4/spreadsheets'+path,{method,headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',redirect:'error',signal:abort.signal});
        if(!current())fail('CANCELED');
        if(response.status===401){invalidate();error='AUTH_REQUIRED';notify();fail('AUTH_REQUIRED');}
        if(response.status===403)fail('DRIVE_FILE_PERMISSION_REQUIRED');
        if(!response.ok)fail(method==='POST'?'SHEET_CREATE_FAILED':'READ_FAILED');
        const advertised=response.headers.get('content-length');if(advertised&&/^\d+$/.test(advertised)&&Number(advertised)>65536){await response.body?.cancel();fail('SOURCE_TOO_LARGE');}
        if(!response.body)fail('READ_FAILED');const reader=response.body.getReader(),chunks=[];let length=0;
        try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>65536||!current()){await reader.cancel();fail(length>65536?'SOURCE_TOO_LARGE':'CANCELED');}chunks.push(value);}}finally{reader.releaseLock();}
        const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
        const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));expire();if(!current())fail('CANCELED');return value;
      }catch(caught){if(!current()&&caught.message!=='AUTH_REQUIRED')fail('CANCELED');if(['AUTH_REQUIRED','CANCELED','DRIVE_FILE_PERMISSION_REQUIRED','SOURCE_TOO_LARGE','READ_FAILED','SHEET_CREATE_FAILED'].includes(caught.message))throw caught;fail(method==='POST'?'SHEET_CREATE_UNCERTAIN':'READ_FAILED');}
      finally{controllers.delete(abort);}
    }
    async function createSpreadsheet(body){
      if(!body||body.properties?.title!=='Investment Cockpit Data'||!Array.isArray(body.sheets)||JSON.stringify(body).length>1048576)fail('INVALID');
      const value=await sheetRequest('?fields=spreadsheetId','POST',body);return extractSpreadsheetId(value.spreadsheetId);
    }
    async function sheetTitles(id){
      if(extractSpreadsheetId(id)!==id)fail('INVALID');const value=await sheetRequest('/'+encodeURIComponent(id)+'?fields=sheets(properties(title))');
      if(!Array.isArray(value.sheets)||value.sheets.length>200)fail('READ_FAILED');
      const titles=value.sheets.map(s=>s?.properties?.title);if(titles.some(x=>typeof x!=='string'||x.length>100))fail('READ_FAILED');return titles;
    }
    function pickSpreadsheet(config){
      expire();if(!enabled||!token)fail('AUTH_REQUIRED');const api=view.google?.picker;
      if(!api||!config||typeof config.apiKey!=='string'||!/^AIza[A-Za-z0-9_-]{20,80}$/.test(config.apiKey)||!/^\d{1,20}$/.test(config.appId))fail('PICKER_CONFIG_INVALID');
      if(pickerCancel)fail('PICKER_BUSY');const attempt=epoch;
      return new Promise((resolve,reject)=>{let picker,settled=false;
        const finish=(code,id)=>{if(settled)return;settled=true;pickerCancel=null;try{picker?.setVisible(false);picker?.dispose?.();}catch(_){}if(code)reject(Error(code));else resolve(id);};
        pickerCancel=()=>finish('CANCELED');
        try{const selected=new api.DocsView(api.ViewId.SPREADSHEETS);selected.setMimeTypes('application/vnd.google-apps.spreadsheet');
          picker=new api.PickerBuilder().addView(selected).setOAuthToken(token).setDeveloperKey(config.apiKey).setAppId(config.appId).setOrigin(view.location.origin).setCallback(data=>{
            if(attempt!==epoch||!enabled||!token){finish('CANCELED');return;}
            const action=data&&data[api.Response.ACTION];if(action===api.Action.CANCEL){finish('PICKER_CANCELED');return;}if(action!==api.Action.PICKED)return;
            try{const docs=data[api.Response.DOCUMENTS];if(!Array.isArray(docs)||docs.length!==1||docs[0][api.Document.MIME_TYPE]!=='application/vnd.google-apps.spreadsheet')fail('INVALID');finish(null,extractSpreadsheetId(docs[0][api.Document.ID]));}catch(_){finish('PICKER_SELECTION_INVALID');}
          }).build();picker.setVisible(true);
        }catch(_){finish('PICKER_UNAVAILABLE');}
      });
    }
    async function fetchValues(id, range, options = {}) {
      expire(); if (!enabled || !token) fail('AUTH_REQUIRED');
      const url = sheetsURL(id, range), attempt = epoch, signal = options.signal;
      if (options.maxBytes !== undefined && (!Number.isSafeInteger(options.maxBytes) || options.maxBytes < 1024 || options.maxBytes > 1048576)) fail('INVALID');
      if (signal?.aborted) fail('CANCELED');
      controller = new view.AbortController(); const abort = controller;
      controllers.add(abort); const cancel = () => abort.abort(); if (signal) signal.addEventListener('abort', cancel, {once:true});
      const current = () => attempt === epoch && enabled && token && !abort.signal.aborted;
      try {
        const response = await view.fetch(url, { method: 'GET', headers: { Authorization: 'Bearer ' + token }, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect:'error', signal: abort.signal });
        if (!current()) fail('CANCELED');
        if (response.status === 401) { invalidate(); error = 'AUTH_REQUIRED'; notify(); fail('AUTH_REQUIRED'); }
        if (!response.ok) fail('READ_FAILED');
        let value;
        if (options.maxBytes !== undefined) {
          const size = response.headers?.get('content-length');
          if (size && /^\d+$/.test(size) && Number(size) > options.maxBytes) { await response.body?.cancel(); fail('SOURCE_TOO_LARGE'); }
          if (!response.body) fail('READ_FAILED');
          const reader=response.body.getReader(),chunks=[];let length=0;
          try { while(true) { const {done,value:chunk}=await reader.read(); if(done)break; length+=chunk.byteLength;if(length>options.maxBytes){await reader.cancel();fail('SOURCE_TOO_LARGE');}chunks.push(chunk);if(!current()){await reader.cancel();fail('CANCELED');} } } finally {reader.releaseLock();}
          const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
          value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
        } else value = await response.json();
        expire(); if (!current()) fail('CANCELED');
        if (!value || !Array.isArray(value.values)) fail('READ_FAILED'); return value;
      } catch (caught) {
        if (caught.message === 'AUTH_REQUIRED') throw caught;
        if (!current()) fail('CANCELED');
        if (['INVALID', 'READ_FAILED', 'SOURCE_TOO_LARGE', 'CANCELED'].includes(caught.message)) throw caught;
        fail('READ_FAILED');
      } finally { if (controller === abort) controller = null; controllers.delete(abort); if(signal)signal.removeEventListener('abort',cancel); }
    }
    async function fetchHistory(origin, symbol, range, options = {}) {
      const destination = historyOrigin(origin);
      if (!options.approvedOrigin || historyOrigin(options.approvedOrigin) !== options.approvedOrigin || destination !== options.approvedOrigin || !HISTORY_SYMBOLS.has(symbol) || !HISTORY_RANGES.has(range)) fail('REQUEST_INVALID');
      expire(); if (!enabled || !token) fail('AUTH_REQUIRED');
      const attempt = epoch, abort = new view.AbortController(), signal = options.signal;
      const cancel = () => abort.abort();
      if (signal) { if (signal.aborted) fail('CANCELED'); signal.addEventListener('abort',cancel,{once:true}); }
      controllers.add(abort);
      const current = () => attempt === epoch && enabled && !!token && !abort.signal.aborted;
      try {
        const response = await view.fetch(destination + '/history?symbol=' + encodeURIComponent(symbol) + '&range=' + encodeURIComponent(range), {
          method:'GET',headers:{Authorization:'Bearer ' + token},credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',redirect:'error',signal:abort.signal
        });
        expire(); if (!current()) fail('CANCELED');
        if (response.status === 401) { invalidate(); error='AUTH_REQUIRED'; notify(); fail('AUTH_REQUIRED'); }
        const payload = await response.json(); expire(); if (!current()) fail('CANCELED');
        if (!response.ok) {
          const code = payload && payload.error && HISTORY_ERRORS.has(payload.error.code) ? payload.error.code : 'YAHOO_UNAVAILABLE';
          if (code === 'AUTH_FORBIDDEN') { invalidate(); error='AUTH_REQUIRED'; notify(); }
          fail(code);
        }
        if (!payload || typeof payload !== 'object' || Array.isArray(payload)) fail('YAHOO_UNAVAILABLE');
        return payload;
      } catch (caught) {
        if (['AUTH_REQUIRED','AUTH_FORBIDDEN'].includes(caught.message)) throw caught;
        if (!current()) fail('CANCELED');
        if (HISTORY_ERRORS.has(caught.message)) throw caught;
        fail('YAHOO_UNAVAILABLE');
      } finally { controllers.delete(abort); if(signal)signal.removeEventListener('abort',cancel); }
    }
    if (view.addEventListener) view.addEventListener('pagehide', () => { invalidate(); error='AUTH_REQUIRED'; notify(); });
    return Object.freeze({ state, setEnabled, prepare, login, disconnect, fetchValues, fetchHistory, createSpreadsheet, sheetTitles, pickSpreadsheet, revision: () => epoch,
      subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); } });
  }
  function translate(state, key) { return TEXT[key][state.locale === 'en-US' ? 1 : 0]; }
  function element(state, tag, label, attributes = {}) {
    const node = state.doc.createElement(tag); if (label !== undefined) node.textContent = label;
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value); return node;
  }
  function notice(state, key) { state.notice.dataset.notice = key; state.notice.textContent = translate(state, key); }
  function live(state) { return hosts.get(state.host) === state && state.host.isConnected; }
  function renderStatus(state) {
    state.pasteButton.disabled = state.busy;
    if (!state.enable) return;
    const current = state.session.state();
    state.enable.checked = state.settings.enabled;
    state.googleControls.hidden = !state.settings.enabled;
    state.prepare.hidden = current.ready || current.connected;
    state.prepare.disabled = current.preparing || state.busy;
    state.login.hidden = !current.ready || current.connected;
    state.login.disabled = current.pending || state.busy;
    state.fetch.hidden = !current.connected; state.fetch.disabled = state.busy || !state.settings.spreadsheet_id;
    state.disconnect.hidden = !current.connected && !current.pending;
    state.status.textContent = translate(state, !state.settings.enabled ? 'off' : current.connected ? 'connected' : current.pending || current.preparing ? 'busy' : 'disconnected');
    state.saveButton.disabled = state.busy;
    if (current.error === 'AUTH_REQUIRED') notice(state, 'auth'); else if (current.error === 'AUTH_FAILED') notice(state, 'authFailed');
    else if(['AUTH_POPUP_FAILED_TO_OPEN','AUTH_POPUP_CLOSED','AUTH_POPUP_UNKNOWN'].includes(current.error)){
      notice(state,'authFailed');state.notice.textContent+=' · '+current.error;
    }
  }
  async function history(state) {
    try {
      const entries = await state.view.DeviceActual.readMarketImportHistory(state.view, state.catalog);
      if (!live(state)) return; state.history.replaceChildren();
      if (!entries.length) { state.history.append(element(state, 'p', translate(state, 'emptyHistory'))); return; }
      for (const entry of entries.slice(-10).reverse()) {
        const names = entry.failure_names.length ? ' (' + entry.failure_names.join(', ') + ')' : '';
        state.history.append(element(state, 'li', entry.at + ' · ' + translate(state, entry.method === 'paste' ? 'methodPaste' : 'methodGoogle') + ' · ' + translate(state, 'success') + ' ' + entry.success_count + ' / ' + translate(state, 'failure') + ' ' + entry.failure_names.length + names + ' · ' + translate(state, 'warning') + ' ' + entry.warning_count));
      }
    } catch (_) { if (live(state)) notice(state, 'storage'); }
  }
  async function saveSettings(state) {
    if (state.busy) return;
    state.busy = true; renderStatus(state);
    try {
      const rawId = state.id.value.trim();
      const value = { schema: 'device-google-sheet-settings/1', enabled: state.settings.enabled, spreadsheet_id: rawId ? extractSpreadsheetId(rawId) : '', range: state.range.value.trim() || DEFAULT_RANGE };
      await state.view.DeviceActual.sheetSettings(state.view, value);
      if (!live(state)) return;
      state.settings = value; state.id.value = value.spreadsheet_id; state.range.value = value.range; notice(state, 'saved');
    } catch (error) { if (live(state)) notice(state, error.message === 'INVALID' ? 'invalid' : 'storage'); }
    finally { state.busy = false; if (live(state)) renderStatus(state); }
  }
  async function setEnabled(state) {
    const value = state.enable.checked;
    // Cancel pending Google reads synchronously before asynchronous device storage.
    state.settings.enabled = value; state.session.setEnabled(value); renderStatus(state);
    try { await state.view.DeviceActual.sheetSettings(state.view, state.settings); }
    catch (_) { if (live(state)) { state.settings.enabled = false; state.session.setEnabled(false); notice(state, 'storage'); renderStatus(state); } }
  }
  async function importQuotes(state, method) {
    if (state.busy) return;
    state.busy = true; state.summary.textContent = ''; renderStatus(state);
    const revision = state.session.revision();
    const current = () => live(state) && (method === 'paste' || (state.settings.enabled && state.session.revision() === revision && state.session.state().connected));
    try {
      let now = new Date().toISOString(), result;
      if (method === 'paste') result = state.view.GoogleSheetCore.parsePaste(state.paste.value, state.catalog, { now });
      else {
        const payload = await state.session.fetchValues(state.settings.spreadsheet_id, state.settings.range);
        if (!current()) fail('CANCELED'); now = new Date().toISOString(); result = state.view.GoogleSheetCore.parseValues(payload.values, state.catalog, { now });
      }
      if (!current()) fail('CANCELED');
      await state.view.DeviceActual.applyMarketImport(state.view, state.catalog, result, { now, method, isCurrent: current });
      if (!current()) return;
      if (method === 'paste') state.paste.value = '';
      const failed = result.failures.map(row => row.name);
      state.summary.dataset.successCount = result.successes.length; state.summary.dataset.failureCount = result.failures.length;
      const warnings = [...new Set(result.warnings)].map(code => translate(state, code === 'DUPLICATE_CODE_NOT_AVAILABLE' ? 'duplicate' : 'unknown'));
      state.summary.textContent = translate(state, 'success') + ' ' + result.successes.length + ' / ' + translate(state, 'failure') + ' ' + result.failures.length + (failed.length ? ' (' + failed.join(', ') + ') · NOT_AVAILABLE' : '') + (warnings.length ? ' · ' + translate(state, 'warning') + ' ' + result.warnings.length + ': ' + warnings.join(' ') : '');
      state.notice.textContent = ''; state.notice.dataset.notice = 'imported'; await history(state);
    } catch (error) {
      if (live(state)) notice(state, error.message === 'AUTH_REQUIRED' ? 'auth' : ['CANCELED', 'CANCELLED'].includes(error.message) ? 'canceled' : error.message === 'READ_FAILED' ? 'readFailed' : ['INVALID', 'CATALOG', 'INPUT'].includes(error.message) ? 'invalid' : 'storage');
    } finally { state.busy = false; if (live(state)) renderStatus(state); }
  }
  async function mount(host, options) {
    const previous = hosts.get(host); if (previous && previous.unsubscribe) previous.unsubscribe();
    const doc = host.ownerDocument, view = doc.defaultView;
    const state = { host, doc, view, catalog: options.catalog, locale: options.locale === 'en-US' ? 'en-US' : 'ko-KR', busy: false };
    hosts.set(host, state);
    state.root = element(state, 'section', undefined, { class: 'google-sheet-quotes card', 'data-google-sheet-quotes': '' });
    state.root.append(element(state, 'h2', translate(state, 'title')), element(state, 'p', translate(state, 'detail')));
    state.notice = element(state, 'p', '', { 'data-sheet-notice': '', role: 'status', 'aria-live': 'polite' });
    host.replaceChildren(state.root);
    try { state.settings = await view.DeviceActual.sheetSettings(view); }
    catch (_) { state.settings = { schema: 'device-google-sheet-settings/1', enabled: false, spreadsheet_id: '', range: DEFAULT_RANGE }; state.storageFailed = true; }
    if (!live(state)) return;
    if (options.clientId) {
      state.session = sessionFor(view,options.clientId); state.session.setEnabled(state.settings.enabled);
      const toggle = element(state, 'label', undefined, { class: 'sheet-toggle' });
      state.enable = element(state, 'input', undefined, { type: 'checkbox', 'data-sheet-enabled': '' }); toggle.append(state.enable, element(state, 'span', translate(state, 'enable'))); state.root.append(toggle);
      state.googleControls = element(state, 'div', undefined, { 'data-sheet-google-controls': '' });
      const form = element(state, 'form', undefined, { class: 'sheet-settings-form' });
      const idLabel = element(state, 'label', translate(state, 'id')), rangeLabel = element(state, 'label', translate(state, 'range'));
      state.id = element(state, 'input', undefined, { type: 'text', 'data-sheet-id': '', autocomplete: 'off', spellcheck: 'false', maxlength: '512' }); state.id.value = state.settings.spreadsheet_id;
      state.range = element(state, 'input', undefined, { type: 'text', 'data-sheet-range': '', autocomplete: 'off', spellcheck: 'false', maxlength: '160' }); state.range.value = state.settings.range;
      idLabel.append(state.id); rangeLabel.append(state.range);
      state.saveButton = element(state, 'button', translate(state, 'save'), { type: 'submit', 'data-sheet-action': 'save' }); const advanced=element(state,'details',undefined,{'data-sheet-advanced':''});advanced.append(element(state,'summary',state.locale==='en-US'?'Advanced · individual sheet ID / range':'고급 · 개별 시트 ID / 범위'),idLabel,rangeLabel,state.saveButton);form.append(advanced); form.addEventListener('submit', event => { event.preventDefault(); void saveSettings(state); });
      const actions = element(state, 'div', undefined, { class: 'sheet-actions' });
      for (const action of ['prepare', 'login', 'fetch', 'disconnect']) { state[action] = element(state, 'button', translate(state, action), { type: 'button', 'data-sheet-action': action }); actions.append(state[action]); }
      state.status = element(state, 'p', '', { 'data-sheet-status': '', role: 'status' });
      state.googleControls.append(form, element(state, 'p', translate(state, 'privacy')), actions); state.root.append(state.googleControls, state.status);
      state.enable.addEventListener('change', () => { void setEnabled(state); });
      state.prepare.addEventListener('click', () => { void state.session.prepare().then(() => { if (live(state) && state.settings.enabled) notice(state, 'ready'); }).catch(() => { if (live(state)) notice(state, 'authFailed'); }); });
      state.login.addEventListener('click', () => { try { state.session.login(); } catch (_) { notice(state, 'authFailed'); } });
      state.fetch.addEventListener('click', () => { void importQuotes(state, 'google-sheet'); });
      state.disconnect.addEventListener('click', () => { void state.session.disconnect(); notice(state, 'removed'); });
    } else {
      const shared = sessions.get(view); if (shared) shared.session.setEnabled(false);
      state.session = { revision: () => 0 }; state.settings.enabled = false;
    }
    const pasteBox = element(state, 'section', undefined, { class: 'sheet-paste-box' }); pasteBox.append(element(state, 'h3', translate(state, 'pasteTitle')), element(state, 'p', translate(state, 'pasteHelp')));
    const pasteLabel = element(state, 'label', translate(state, 'pasteLabel')); state.paste = element(state, 'textarea', undefined, { 'data-sheet-paste': '', rows: '5', maxlength: '65536', autocomplete: 'off', spellcheck: 'false' }); pasteLabel.append(state.paste);
    state.pasteButton = element(state, 'button', translate(state, 'paste'), { type: 'button', 'data-sheet-action': 'paste' }); state.pasteButton.addEventListener('click', () => { void importQuotes(state, 'paste'); }); pasteBox.append(pasteLabel, state.pasteButton); state.root.append(pasteBox);
    state.summary = element(state, 'p', '', { 'data-sheet-summary': '', role: 'status', 'aria-live': 'polite' });
    state.history = element(state, 'ul', undefined, { 'data-sheet-history': '' }); state.root.append(state.notice, state.summary, element(state, 'h3', translate(state, 'history')), state.history);
    if (options.clientId) {
      state.unsubscribe = state.session.subscribe(() => { if (live(state)) renderStatus(state); else if (state.unsubscribe) state.unsubscribe(); });
      renderStatus(state);
    }
    if (state.storageFailed) notice(state, 'storage'); else await history(state);
  }
  return Object.freeze({ mount, extractSpreadsheetId, sheetsURL, createSession, sessionFor, historyOrigin });
});
