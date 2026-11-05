'use strict';
// Owner-private layer reader and client (web_app/kis-private.js; owner 2026-11-05, DC-44; Codex #480 contract). Synthetic only.
//  - Readers (kis-bars/1, analysis, kis-technical-measures/1, qgv) refuse a file that breaks its contract; adopted values only (raw diagnostics are a count); 미산출 never 0; no rank
//    on the private QGV and the official publication / TARGET untouched; public vs private basis day words.
//  - Client: token scope exactly openid email (include_granted_scopes false), memory only, dropped on expiry and on a server
//    403; requests carry only the Bearer header, credentials omit, no-store, no referrer; nothing without a token.
const assert = require('node:assert/strict');
const KP = require('../src/investment_system/product/web_app/kis-private.js');
const X = require('./web_app_kis_private_fixture.js');

let n = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };

(async () => {
  await ok('bars / analysis / qgv synthetic payloads pass and freeze', () => {
    for (const [f, v] of [[KP.validateBars, X.bars()], [KP.validateAnalysis, X.analysis()], [KP.validateQgv, X.qgv()]]) {
      const r = f(v); assert.equal(r.ok, true, JSON.stringify(r)); assert.ok(Object.isFrozen(r.value));
    }
  });
  await ok('readers refuse wrong schema, a rank, a touched publication, a value with a reason, wrong counts', () => {
    const cases = [
      [KP.validateBars, (x) => { x.schema = X.K('bars/2'); }, 'SCHEMA_VERSION'],
      [KP.validateBars, (x) => { x.publication_scope = 'PUBLIC'; }, 'SCOPE'],
      [KP.validateBars, (x) => { x.bars[0].close = 101.5; }, 'DECIMAL_INVALID'],
      [KP.validateBars, (x) => { x.price_basis_date = '2026-10-29'; }, 'BASIS_DATE_MISMATCH'],
      [KP.validateAnalysis, (x) => { x.metrics.SMA_20.value = '1'; }, 'VALUE_WITH_REASON'],
      [KP.validateAnalysis, (x) => { x.raw_count = 3; }, 'COUNT_MISMATCH'],
      [KP.validateQgv, (x) => { x.rank = 1; }, 'RANK_NOT_ALLOWED'],
      [KP.validateQgv, (x) => { x.TARGET_modified = true; }, 'OFFICIAL_TOUCHED'],
      [KP.validateQgv, (x) => { x.coverage.Q = 3; }, 'COUNT_INVALID'],
    ];
    for (const [f, change, code] of cases) {
      const v = f === KP.validateBars ? X.bars() : f === KP.validateAnalysis ? X.analysis() : X.qgv(); change(v);
      const r = f(v); assert.equal(r.ok, false, code); assert.equal(r.code, code);
    }
  });
  await ok('analysis view: adopted values only, raw diagnostics as a count, held indicators as 미산출 with reasons', () => {
    const v = KP.analysisView(KP.validateAnalysis(X.analysis()).value);
    assert.equal(v.summary, '진단값(원시 계산) 2개 · 채택값 0개 · 미산출 3개');
    assert.deepEqual(v.adopted, []);
    assert.doesNotMatch(JSON.stringify(v), /101\.25|55\.5/, 'no raw_value shown as a value');
    assert.ok(v.held.every((x) => x.text.startsWith('미산출 · ')));
    assert.match(v.held.find((x) => x.id === 'RSI_14').text, /이력 부족/);
    const a = KP.analysisView(KP.validateAnalysis(X.analysis({ adopted: true })).value);
    assert.deepEqual(a.adopted, [{ id: 'SMA_20', value: '101.25' }]);
    assert.equal(KP.analysisView(KP.validateAnalysis(X.analysis({ status: 'STALE' })).value).statusText, '갱신 지연');
  });
  await ok('qgv view: Q/G computed, V 미산출 (never 0), no total without V, no rank, official unchanged', () => {
    const v = KP.qgvView(KP.validateQgv(X.qgv()).value, 'NASDAQ:NVDA');
    assert.deepEqual(v.coverage, ['Q 산출 2 / 2', 'G 산출 2 / 2', 'V 산출 0 / 2', 'Q·G·V 모두 0 / 2']);
    assert.deepEqual(v.row.axes, ['Q 70.3', 'G 60.5', 'V 미산출 · 사유 코드 V_INPUTS_NOT_AVAILABLE']);
    assert.equal(v.row.total, 'QGV 총점 미산출 · V 미산출');
    assert.match(v.rank, /비공개 순위 없음 · 같은 모집단·입력 비교가 확인되지 않아 순위 없음/);
    assert.equal(v.official, '공개 공식 순위·TARGET은 이 결과로 바뀌지 않음');
    assert.equal(KP.qgvView(KP.validateQgv(X.qgv()).value, 'NYSE:NONE').row, null);
  });
  await ok('measures (five #469 measures, one company): the synthetic file passes and freezes', () => {
    for (const adopted of [true, false]) { const r = KP.validateMeasures(X.measures({ adopted })); assert.equal(r.ok, true, JSON.stringify(r)); assert.ok(Object.isFrozen(r.value.metrics.momentum_3m)); }
  });
  await ok('measures reader refuses the whole file at the first fault: schema, scope, a rank, states, units, counts, windows', () => {
    const cases = [
      [(x) => { x.schema = X.K('technical-measures/2'); }, 'SCHEMA_VERSION', '$.schema'],
      [(x) => { x.publication_scope = 'PUBLIC'; }, 'SCOPE', '$.publication_scope'],
      [(x) => { x.result_kind = 'DATED_GROUP_BOARD'; }, 'ENUM', '$.result_kind'],
      [(x) => { delete x.metrics.volatility_6m; }, 'KEY_MISSING', '$.metrics.volatility_6m'],
      [(x) => { x.metrics.sma_120 = x.metrics.momentum_6m; }, 'METRIC_UNKNOWN', '$.metrics.sma_120'],
      [(x) => { x.rank_count = 1; }, 'RANK_NOT_ALLOWED', '$.rank_count'],
      [(x) => { x.rank = 3; }, 'RANK_NOT_ALLOWED', '$.rank'],
      [(x) => { x.metrics.momentum_3m.rank = 1; }, 'RANK_NOT_ALLOWED', '$.metrics.momentum_3m.rank'],
      [(x) => { x.metrics.momentum_6m.value = x.metrics.momentum_6m.raw_value; }, 'STATE_MISMATCH', '$.metrics.momentum_6m.state'],
      [(x) => { x.metrics.momentum_6m.state = 'VALUE'; }, 'STATE_MISMATCH', '$.metrics.momentum_6m.state'],
      [(x) => { x.metrics.momentum_12m.null_reasons = []; }, 'STATE_MISMATCH', '$.metrics.momentum_12m.state'],
      [(x) => { x.metrics.momentum_12m.raw_value = '0'; }, 'STATE_MISMATCH', '$.metrics.momentum_12m.state'],
      [(x) => { x.metrics.momentum_3m.null_reasons = ['IDENTITY_RANGE_UNCONFIRMED']; }, 'STATE_MISMATCH', '$.metrics.momentum_3m.state'],
      [(x) => { x.metrics.momentum_3m.value = 'NaN'; }, 'VALUE_INVALID', '$.metrics.momentum_3m.value'],
      [(x) => { x.metrics.volatility_6m.unit = 'PERCENT'; }, 'UNIT_MISMATCH', '$.metrics.volatility_6m.unit'],
      [(x) => { x.metrics.momentum_3m.state = 'ADOPTED'; }, 'ENUM', '$.metrics.momentum_3m.state'],
      [(x) => { x.metrics.momentum_3m.observed_days = 65; }, 'COUNT_INVALID', '$.metrics.momentum_3m.observed_days'],
      [(x) => { x.metrics.momentum_3m.window_start = '2026-11-30'; }, 'DATE_ORDER', '$.metrics.momentum_3m.window_start'],
      [(x) => { x.raw_count = 5; }, 'COUNT_MISMATCH', '$.raw_count'],
      [(x) => { x.adopted_count = 0; }, 'COUNT_MISMATCH', '$.adopted_count'],
      [(x) => { x.data_asof = '2026-11-02'; }, 'DATE', '$.data_asof'],
      [(x) => { x.symbol = 'nvda'; }, 'SYMBOL', '$.symbol'],
    ];
    for (const [change, code, at] of cases) {
      const v = X.measures(); change(v);
      assert.deepEqual(KP.validateMeasures(v), { ok: false, code, path: at }, code + ' ' + at);
    }
    assert.equal(KP.validateMeasures(null).ok, false);
  });
  await ok('measures view: 채택값 only when adopted, 진단값 as a count, 미산출 with reasons, windows, no rank, null never 0', () => {
    const v = KP.measuresView(KP.validateMeasures(X.measures()).value);
    assert.equal(v.summary, '진단값(원시 계산) 2개 · 채택값 1개 · 미산출 4개');
    assert.deepEqual(v.rows.map((r) => [r.id, r.kind, r.value]), [['momentum_3m', 'VALUE', '12.4242 %'], ['momentum_6m', 'DIAGNOSTIC', null], ['momentum_12m', 'NOT_COMPUTED', null],
      ['volatility_6m', 'NOT_COMPUTED', null], ['dollar_volume_6m', 'NOT_COMPUTED', null]]);
    assert.equal(v.rows[1].text, '미산출 · 증권 신원 기간 미확인 · 진단값만 있음 (값 미표시)');
    assert.equal(v.rows[4].text, '미산출 · 거래량 창이 모자라거나 맞지 않음 · 거래 범위 미확인');
    assert.equal(v.rows[0].window, '관측 창 2026-07-30 ~ 2026-10-30 · 64 / 64 종가');
    assert.equal(v.rows[3].window, '관측 창 2026-05-01 ~ 2026-10-30 · 100 / 126 일간 수익률');
    assert.match(v.rank, /^그룹 순위 미산출 · 한 기업 측정만 있음/);
    assert.deepEqual([v.signal_day, v.data_asof, v.collected_at, v.statusText], ['2026-10-30', '2026-10-30', '2026-10-31T04:00:00Z', '평가일 기준 정상 · 현재 시세 최신 아님']);
    const text = JSON.stringify(v);
    for (const raw of X.MEASURE_RAW) assert.ok(!text.includes(raw), 'raw ' + raw + ' never in the view');
    assert.doesNotMatch(text, /"value":"0|· 0 %/, 'a null is never 0');
    const d = KP.measuresView(KP.validateMeasures(X.measures({ adopted: false })).value);
    assert.equal(d.summary, '진단값(원시 계산) 2개 · 채택값 0개 · 미산출 5개');
    assert.ok(!JSON.stringify(d).includes('12.4242'), 'a diagnostic 3m is not shown as a value');
  });
  await ok('basis day words: same, different (직접 비교 제한), missing', () => {
    assert.equal(KP.basisCompare('2026-10-30', '2026-10-30').same, true);
    assert.match(KP.basisCompare('2026-10-29', '2026-10-30').text, /기준일이 달라 직접 비교 제한/);
    assert.match(KP.basisCompare(null, '2026-10-30').text, /공개 기준일 없음 · 비공개 기준일 2026-10-30 · 직접 비교 제한/);
  });

  // ---- client
  const ORIGIN = 'https://private-worker.example';
  function harness({ scope = 'openid https://www.googleapis.com/auth/userinfo.email', expires = 3600, answers = [] } = {}) {
    const clock = { now: 1_000_000 }, sent = [], tokenRequests = [];
    const google = { accounts: { oauth2: { initTokenClient: (cfg) => { tokenRequests.push(cfg); return { requestAccessToken: () => cfg.callback({ access_token: 'synthetic-token', expires_in: String(expires), scope }) }; } } } };
    const queue = [...answers];
    const send = async (url, init) => { sent.push({ url, init }); const a = queue.shift() || { status: 200, body: {} }; return { status: a.status, ok: a.status >= 200 && a.status < 300, json: async () => a.body }; };
    const c = KP.createClient({ win: { google }, clientId: 'synthetic-client', origin: ORIGIN, send, now: () => clock.now });
    return { c, clock, sent, tokenRequests };
  }
  await ok('client: nothing without a token; scope exactly openid email; Bearer only, omit, no-store, no referrer', async () => {
    const h = harness({ answers: [{ status: 200, body: X.analysis() }] });
    await assert.rejects(h.c.get('analysis', 'NVDA'), /AUTH_REQUIRED/); assert.equal(h.sent.length, 0);
    await h.c.connect();
    assert.equal(h.tokenRequests[0].scope, 'openid email'); assert.equal(h.tokenRequests[0].include_granted_scopes, false);
    const body = await h.c.get('analysis', 'NVDA');
    assert.equal(body.status, 'NORMAL');
    const [s] = h.sent;
    assert.equal(s.url, ORIGIN + KP.ROUTE.analysis + '?symbol=NVDA');
    assert.deepEqual(s.init.headers, { Authorization: 'Bearer synthetic-token' });
    assert.equal(s.init.credentials, 'omit'); assert.equal(s.init.cache, 'no-store'); assert.equal(s.init.referrerPolicy, 'no-referrer');
    await assert.rejects(h.c.get('analysis', '../x'), /REQUEST_INVALID/); await assert.rejects(h.c.get('orders', null), /ROUTE_UNKNOWN/);
    await assert.rejects(h.c.get('technical', null), /REQUEST_INVALID/, 'technical needs a symbol');
  });
  await ok('client: the seven routes — technical takes a symbol, macro and news take no query', async () => {
    assert.deepEqual(Object.keys(KP.ROUTE).sort(), ['analysis', 'chart', 'macro', 'news', 'qgv', 'status', 'technical']);
    const h = harness({ answers: [{ status: 200, body: X.measures() }, { status: 200, body: { schema_version: 'macro-current-query/1' } }, { status: 200, body: { kind: 'NEWS_SIGNALS', schema_version: 2 } }] });
    await h.c.connect();
    await h.c.get('technical', 'NVDA'); await h.c.get('macro', 'NVDA'); await h.c.get('news', null);
    assert.deepEqual(h.sent.map((x) => x.url), [ORIGIN + KP.ROUTE.technical + '?symbol=NVDA', ORIGIN + KP.ROUTE.macro, ORIGIN + KP.ROUTE.news]);
    for (const x of h.sent) { assert.deepEqual(x.init.headers, { Authorization: 'Bearer synthetic-token' }); assert.equal(x.init.redirect, 'error'); assert.equal(x.init.credentials, 'omit'); }
  });
  await ok('client: a wider scope is refused; a server 403 drops the token; expiry drops it; disconnect drops it', async () => {
    let h = harness({ scope: 'openid email https://www.googleapis.com/auth/drive.file' });
    await assert.rejects(h.c.connect(), /LOGIN_REFUSED/); assert.equal(h.c.state().connected, false);
    h = harness({ answers: [{ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } }] }); await h.c.connect();
    await assert.rejects(h.c.get('qgv', null), /AUTH_FORBIDDEN/); assert.equal(h.c.state().connected, false, 'server refusal drops the token');
    h = harness({ expires: 60 }); await h.c.connect(); assert.equal(h.c.state().connected, true);
    h.clock.now += 61_000; assert.equal(h.c.state().connected, false, 'expired token dropped');
    await assert.rejects(h.c.get('qgv', null), /AUTH_REQUIRED/); assert.equal(h.sent.length, 0);
    h = harness(); await h.c.connect(); h.c.disconnect(); assert.equal(h.c.state().connected, false);
    h = harness({ answers: [{ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } }] }); await h.c.connect();
    await assert.rejects(h.c.get('chart', 'NVDA'), /KIS_SERIES_NOT_FOUND/); assert.equal(h.c.state().connected, true, 'a missing file keeps the session');
  });
  console.log(JSON.stringify({ passed: true, checks: n }));
})().catch((e) => { console.error(e); process.exitCode = 1; });
