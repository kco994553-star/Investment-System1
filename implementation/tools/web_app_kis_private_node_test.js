'use strict';
// Owner-private layer reader and client (web_app/kis-private.js; owner 2026-11-05, DC-44; Codex #480 contract). Synthetic only.
//  - Readers (kis-bars/1, analysis, kis-technical-measures/1, qgv) refuse a file that breaks its contract; adopted values only (raw diagnostics are a count); 미산출 never 0; no rank
//    on the private QGV and the official publication / TARGET untouched; public vs private basis day words.
//  - Price basis (Codex #498): RAW 원주가 / SPLIT_ADJUSTED 확인된 분할 반영 for the chart, the analysis (result_kind, price /
//    chart / diagnostic basis, evidence adjustment_*, readiness adjustment.state) and the measures (basis, settings_version);
//    a file whose own basis fields disagree and an unknown enum are refused; a result of another basis than the chart's is
//    BASIS_MISMATCH; counts read 채택값 N개 (이 기업·이 평가일), never companies or coverage; the fixed adjusted line.
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
    assert.equal(v.summary, '진단값(원시 계산) 2개 · 채택값 0개 (이 기업·이 평가일) · 미산출 3개');
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
    assert.equal(v.summary, '진단값(원시 계산) 2개 · 채택값 1개 (이 기업·이 평가일) · 미산출 4개');
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
    assert.equal(d.summary, '진단값(원시 계산) 2개 · 채택값 0개 (이 기업·이 평가일) · 미산출 5개');
    assert.ok(!JSON.stringify(d).includes('12.4242'), 'a diagnostic 3m is not shown as a value');
  });
  await ok('price basis (#498): adjusted bars / analysis / measures pass; RAW and adjusted words, evaluation day, settings version, evidence', () => {
    const b = KP.validateBars(X.bars({ basis: 'SPLIT_ADJUSTED' })); assert.equal(b.ok, true, JSON.stringify(b));
    const bm = KP.barsMeta(b.value); assert.deepEqual([bm.basis, bm.basisCode, bm.note], ['확인된 분할 반영', 'SPLIT_ADJUSTED', KP.ADJUSTED_NOTE]);
    assert.deepEqual([KP.barsMeta(KP.validateBars(X.bars()).value).basis, KP.barsMeta(KP.validateBars(X.bars()).value).note], ['원주가', null]);
    assert.equal(KP.ADJUSTED_NOTE, '실제 분할 사건 검증 미완료 · 분할 없는 구간의 조정 경로 확인');
    const a = KP.validateAnalysis(X.analysis({ adopted: true, basis: 'SPLIT_ADJUSTED' })); assert.equal(a.ok, true, JSON.stringify(a));
    const av = KP.analysisView(a.value);
    assert.deepEqual([av.basis, av.basisText, av.chartBasisText, av.resultKind, av.evaluation_day, av.signal_day, av.note],
      ['SPLIT_ADJUSTED', '확인된 분할 반영', '확인된 분할 반영', 'SPLIT_ADJUSTED_SERIES_DIAGNOSTIC', '2026-10-30', '2026-10-30', KP.ADJUSTED_NOTE]);
    assert.equal(av.evidence, '분할 반영 증거 구간 2026-10-26 ~ 2026-10-30 · 확인된 분할만 반영 · 근거 기록 있음');
    assert.equal(av.adjustment, '지표별 분할 상태 · 확인된 분할만 반영 지표 1개 · 분할 기준 미확인 지표 2개');
    assert.equal(av.summary, '진단값(원시 계산) 2개 · 채택값 1개 (이 기업·이 평가일) · 미산출 2개');
    const rv = KP.analysisView(KP.validateAnalysis(X.analysis()).value);
    assert.deepEqual([rv.basisText, rv.resultKind, rv.note, rv.evidence], ['원주가', 'RAW_SERIES_DIAGNOSTIC', null, '분할 없음 증거 구간 2026-10-26 ~ 2026-10-30 · 근거 기록 있음']);
    assert.equal(rv.adjustment, '지표별 분할 상태 · 분할 없음 확인 지표 1개 · 분할 기준 미확인 지표 2개');
    const m = KP.validateMeasures(X.measures({ basis: 'SPLIT_ADJUSTED' })); assert.equal(m.ok, true, JSON.stringify(m));
    const mv = KP.measuresView(m.value);
    assert.deepEqual([mv.basisText, mv.settings_version, mv.evaluation_day, mv.signal_day, mv.note], ['확인된 분할 반영', 'technical-leaderboard/split-adjusted-2026-11-05.1', '2026-10-30', '2026-10-30', KP.ADJUSTED_NOTE]);
    assert.equal(mv.evidence, '분할 반영 증거 구간 2026-04-30 ~ 2026-10-30 · 확인된 분할만 반영 · 근거 기록 있음');
    const mr = KP.measuresView(KP.validateMeasures(X.measures()).value);
    assert.deepEqual([mr.basisText, mr.settings_version, mr.note], ['원주가', 'technical-leaderboard/2026-11-03.1', null]);
    // Coverage missing on an adjusted result: allowed, the values are held, and the words say so.
    const nc = X.analysis({ basis: 'SPLIT_ADJUSTED' }); delete nc.evidence.adjustment_start; delete nc.evidence.adjustment_end; delete nc.evidence.adjustment_reference;
    assert.equal(KP.analysisView(KP.validateAnalysis(nc).value).evidence, '분할 반영 증거 구간 없음 · 값 미채택');
    // A file of the #480 era (before #498): no evidence price_basis, no readiness, still read.
    const old = X.measures(); delete old.evidence.price_basis; delete old.evidence.no_split_start; delete old.evidence.no_split_end; delete old.evidence.no_split_reference;
    assert.equal(KP.validateMeasures(old).ok, true);
    const oa = X.analysis({ chart: 'SPLIT_ADJUSTED' }); delete oa.readiness; delete oa.evidence;
    assert.equal(KP.validateAnalysis(oa).ok, true);
  });
  await ok('price basis: a file whose own basis fields disagree, or an unknown basis / kind / state / method / settings version, is refused', () => {
    const cases = [
      [KP.validateBars, () => X.bars(), (x) => { x.basis = 'ADJUSTED'; }, 'ENUM', '$.basis'],
      [KP.validateBars, () => X.bars({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.dividend_adjustment = 'CASH'; }, 'ENUM', '$.dividend_adjustment'],
      [KP.validateAnalysis, () => X.analysis(), (x) => { delete x.diagnostic_basis; }, 'KEY_MISSING', '$.diagnostic_basis'],
      [KP.validateAnalysis, () => X.analysis(), (x) => { x.chart_basis = 'MODP1'; }, 'ENUM', '$.chart_basis'],
      [KP.validateAnalysis, () => X.analysis(), (x) => { x.result_kind = 'ADJUSTED_SERIES_DIAGNOSTIC'; }, 'ENUM', '$.result_kind'],
      [KP.validateAnalysis, () => X.analysis(), (x) => { x.result_kind = 'SPLIT_ADJUSTED_SERIES_DIAGNOSTIC'; }, 'BASIS_CONFLICT', '$.result_kind'],
      [KP.validateAnalysis, () => X.analysis({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.price_basis = 'RAW'; }, 'BASIS_CONFLICT', '$.price_basis'],
      [KP.validateAnalysis, () => X.analysis({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.evidence.adjustment_method = 'PROVIDER_MODP1'; }, 'ENUM', '$.evidence.adjustment_method'],
      [KP.validateAnalysis, () => X.analysis({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.evidence.price_basis = 'RAW'; }, 'BASIS_CONFLICT', '$.evidence.price_basis'],
      [KP.validateAnalysis, () => X.analysis({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.evidence.adjustment_end = '2026-10-01'; x.evidence.adjustment_start = '2026-10-02'; }, 'DATE_ORDER', '$.evidence.adjustment_start'],
      [KP.validateAnalysis, () => X.analysis(), (x) => { x.evidence.adjustment_method = 'CONFIRMED_SPLITS_ONLY'; }, 'BASIS_CONFLICT', '$.evidence.adjustment_method'],
      [KP.validateAnalysis, () => X.analysis({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.readiness.metrics.SMA_20.adjustment.state = 'PROVIDER_ADJUSTED'; }, 'ENUM', '$.readiness.metrics.SMA_20.adjustment.state'],
      [KP.validateAnalysis, () => X.analysis(), (x) => { x.readiness.metrics.SMA_20.adjustment.state = 'CONFIRMED_SPLITS_ONLY'; }, 'BASIS_CONFLICT', '$.readiness.metrics.SMA_20.adjustment.state'],
      [KP.validateAnalysis, () => X.analysis({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.readiness.metrics.RSI_14.adjustment.price_basis = 'RAW'; }, 'BASIS_CONFLICT', '$.readiness.metrics.RSI_14.adjustment.price_basis'],
      [KP.validateMeasures, () => X.measures(), (x) => { x.diagnostic_basis = 'ADJUSTED'; }, 'ENUM', '$.diagnostic_basis'],
      [KP.validateMeasures, () => X.measures(), (x) => { delete x.settings_version; }, 'KEY_MISSING', '$.settings_version'],
      [KP.validateMeasures, () => X.measures(), (x) => { x.settings_version = 'technical-leaderboard/2026-11-09.1'; }, 'SETTINGS_VERSION', '$.settings_version'],
      [KP.validateMeasures, () => X.measures({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.settings_version = X.SETTINGS.RAW; }, 'SETTINGS_BASIS_MISMATCH', '$.settings_version'],
      [KP.validateMeasures, () => X.measures(), (x) => { x.settings_version = X.SETTINGS.SPLIT_ADJUSTED; }, 'SETTINGS_BASIS_MISMATCH', '$.settings_version'],
      [KP.validateMeasures, () => X.measures({ basis: 'SPLIT_ADJUSTED' }), (x) => { x.evidence.price_basis = 'RAW'; }, 'BASIS_CONFLICT', '$.evidence.price_basis'],
    ];
    for (const [f, make, change, code, at] of cases) { const v = make(); change(v); assert.deepEqual(f(v), { ok: false, code, path: at }, code + ' ' + at); }
  });
  await ok('chart / indicator basis agreement: another basis than the chart file is BASIS_MISMATCH with words, never silent', () => {
    const A = (o) => KP.validateAnalysis(X.analysis(o)).value, M = (o) => KP.validateMeasures(X.measures(o)).value;
    assert.deepEqual(KP.basisAgreement('RAW', A()), { code: 'BASIS_MATCH', same: true, text: '차트·지표 가격 기준 같음 · 원주가' });
    assert.equal(KP.basisAgreement('SPLIT_ADJUSTED', A({ basis: 'SPLIT_ADJUSTED' })).code, 'BASIS_MATCH');
    const g = KP.basisAgreement('RAW', A({ basis: 'SPLIT_ADJUSTED' }));
    assert.deepEqual([g.code, g.same], ['BASIS_MISMATCH', false]);
    assert.equal(g.text, '가격 기준 불일치 · 지표를 이 차트에 붙이지 않음 · 차트 파일 원주가 · 지표 확인된 분할 반영');
    // #480-era adjusted file: chart SPLIT_ADJUSTED but indicators RAW → not on an adjusted chart.
    assert.equal(KP.basisAgreement('SPLIT_ADJUSTED', A({ chart: 'SPLIT_ADJUSTED' })).text, '가격 기준 불일치 · 지표를 이 차트에 붙이지 않음 · 차트 파일 확인된 분할 반영 · 지표 원주가 · 결과의 차트 기준 확인된 분할 반영');
    assert.equal(KP.basisAgreement('SPLIT_ADJUSTED', M()).code, 'BASIS_MISMATCH');
    assert.equal(KP.basisAgreement('RAW', M({ basis: 'SPLIT_ADJUSTED' })).code, 'BASIS_MISMATCH');
    assert.equal(KP.basisAgreement('SPLIT_ADJUSTED', M({ basis: 'SPLIT_ADJUSTED' })).code, 'BASIS_MATCH');
  });
  await ok('wording: counts are this company on this evaluation day, never companies or coverage; the retired reason still has words', () => {
    const views = [KP.analysisView(KP.validateAnalysis(X.analysis({ adopted: true, basis: 'SPLIT_ADJUSTED' })).value), KP.measuresView(KP.validateMeasures(X.measures({ basis: 'SPLIT_ADJUSTED' })).value)];
    for (const v of views) {
      assert.match(v.summary, /채택값 \d+개 \(이 기업·이 평가일\)/);
      assert.doesNotMatch(JSON.stringify(v), /종목|coverage|커버리지|기업 수|시장/i, 'never a number of companies or market coverage');
    }
    assert.match(KP.reasonText('SPLIT_ADJUSTED_DISPLAY_ADAPTER_PENDING'), /이전 판/);
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
  await ok('client: the eight routes — technical takes a symbol, classification a part, macro and news take no query', async () => {
    assert.deepEqual(Object.keys(KP.ROUTE).sort(), ['analysis', 'chart', 'classification', 'macro', 'news', 'qgv', 'status', 'technical']);
    assert.deepEqual([...KP.CLASSIFICATION_PARTS], ['view', 'technical', 'macro', 'qgv_links', 'dictionary']);
    const h = harness({ answers: [{ status: 200, body: X.measures() }, { status: 200, body: { schema_version: 'macro-current-query/1' } }, { status: 200, body: { kind: 'NEWS_SIGNALS', schema_version: 2 } }] });
    await h.c.connect();
    await h.c.get('technical', 'NVDA'); await h.c.get('macro', 'NVDA'); await h.c.get('news', null);
    assert.deepEqual(h.sent.map((x) => x.url), [ORIGIN + KP.ROUTE.technical + '?symbol=NVDA', ORIGIN + KP.ROUTE.macro, ORIGIN + KP.ROUTE.news]);
    for (const x of h.sent) { assert.deepEqual(x.init.headers, { Authorization: 'Bearer synthetic-token' }); assert.equal(x.init.redirect, 'error'); assert.equal(x.init.credentials, 'omit'); }
    // classification (owner 2026-11-08): ?part= one of the five parts only, the same request rules; a bad part never leaves the page.
    const c = harness({ answers: KP.CLASSIFICATION_PARTS.map(() => ({ status: 200, body: { schema_version: 'synthetic' } })) });
    await c.c.connect();
    for (const part of KP.CLASSIFICATION_PARTS) await c.c.get('classification', part);
    assert.deepEqual(c.sent.map((x) => x.url), KP.CLASSIFICATION_PARTS.map((p) => ORIGIN + KP.ROUTE.classification + '?part=' + p));
    for (const x of c.sent) { assert.deepEqual(x.init.headers, { Authorization: 'Bearer synthetic-token' }); assert.equal(x.init.redirect, 'error'); assert.equal(x.init.cache, 'no-store'); }
    for (const bad of [null, '', 'store', 'View', '../view', 'view&x=1']) await assert.rejects(c.c.get('classification', bad), /REQUEST_INVALID/, String(bad));
    assert.equal(c.sent.length, KP.CLASSIFICATION_PARTS.length);
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
