'use strict';
// Owner-private layer reader and client (web_app/kis-private.js; owner 2026-11-05 DC-44, 2026-11-15 DC-53; Codex #480 contract). Synthetic only.
//  - Read token status (DC-53): NO_EXPIRY reads 만료일 없음 with null dates; dated, expiring, rejected and mismatch words apart; a malformed status is refused.
//  - Readers (kis-bars/1, analysis, kis-technical-measures/1, qgv) refuse a file that breaks its contract; adopted values only (raw diagnostics are a count); 미산출 never 0; no rank
//    on the private QGV and the official publication / TARGET untouched; public vs private basis day words.
//  - Price basis (Codex #498): RAW 원주가 / SPLIT_ADJUSTED 확인된 분할 반영 for the chart, the analysis (result_kind, price /
//    chart / diagnostic basis, evidence adjustment_*, readiness adjustment.state) and the measures (basis, settings_version);
//    a file whose own basis fields disagree and an unknown enum are refused; a result of another basis than the chart's is
//    BASIS_MISMATCH; counts read 채택값 N개 (이 기업·이 평가일), never companies or coverage; the fixed adjusted line.
//  - Client: token scope exactly openid email (include_granted_scopes false), memory only, dropped on expiry and on a server
//    403; requests carry only the Bearer header, credentials omit, no-store, no referrer; nothing without a token. An answer that
//    never came or a 5xx without the Worker's code is marked unreachable (the layer's one retry, owner 2026-11-28); nothing else.
const assert = require('node:assert/strict');
const KP = require('../src/investment_system/product/web_app/kis-private.js');
const X = require('./web_app_kis_private_fixture.js');

let n = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };

(async () => {
  await ok('read token: explicit no-expiry, dated warning and blocked failures have separate words', () => {
    const record = (state, code = null, expires_on = null, days_left = null) => ({ schema: X.K('status/1'), state, code, expires_on, days_left });
    for (const [raw, words, blocked] of [
      [record('NO_EXPIRY'), /만료일 없음/, false],
      [record('OK', null, '2027-02-13', 30), /2027-02-13/, false],
      [record('EXPIRING', null, '2027-02-13', 14), /14일 뒤.*2027-02-13.*만료/, false],
      [record('EXPIRED', 'TOKEN_EXPIRED', '2027-02-13', 0), /토큰 만료/, true],
      [record('EXPIRED', 'TOKEN_EXPIRED', '2027-02-13', 2), /토큰 만료/, true],
      [record('UNSET', 'TOKEN_DATE_INVALID'), /만료 설정 오류/, true],
      [record('REJECTED', 'TOKEN_REJECTED'), /토큰 거부/, true],
      [record('ERROR', 'TOKEN_EXPIRY_MISMATCH'), /만료 설정.*일치하지 않/, true],
    ]) {
      const r = KP.validateTokenStatus(raw); assert.equal(r.ok, true);
      const v = KP.tokenStatusView(r.value); assert.match(v.text, words); assert.equal(v.blocked, blocked);
      if (raw.state !== 'NO_EXPIRY') assert.doesNotMatch(v.text, /만료일 없음/);
    }
    for (const raw of [
      record('OK'), record('NO_EXPIRY', null, '2027-02-13'), record('NO_EXPIRY', null, null, 0),
      record('EXPIRING', null, '2027-02-30', 14), record('EXPIRING', null, '2027-02-13', 15),
      record('NO_EXPIRY', 'TOKEN_REJECTED'), record('UNKNOWN'), record('REJECTED', 'ARBITRARY_SECRET'),
      record('EXPIRED', 'TOKEN_EXPIRED', '2027-02-13', 3),
    ]) assert.equal(KP.validateTokenStatus(raw).ok, false, 'malformed status is refused');
  });
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
    assert.equal(v.row.total, '총점 미산출 · 세 축 필요');
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

  await ok('class shares BRK/B and BF/B: read, matched to the request symbol and the Universe code; other slashes refused', () => {
    for (const [sym, req, code] of [['BRK/B', 'BRK-B', 'NYSE:BRK.B'], ['BF/B', 'BF-B', 'NYSE:BF.B']]) {
      assert.equal(KP.validateBars(X.bars({ symbol: sym })).ok, true, sym);
      assert.equal(KP.validateMeasures(X.measures({ symbol: sym })).ok, true, sym);
      assert.deepEqual([KP.requestSymbol(sym), KP.universeCode(sym)], [req, code]);
    }
    assert.deepEqual([KP.requestSymbol('NVDA'), KP.universeCode('NVDA')], ['NVDA', null]);
    for (const sym of ['BRK_B', 'ABC/B', 'BRK/A', 'brk/b', 'BRK.B']) assert.equal(KP.validateBars(X.bars({ symbol: sym })).code, 'SYMBOL', sym);
  });
  await ok('the 15 approved ETFs read like a company symbol', () => {
    assert.deepEqual([...KP.ETFS], ['SPY', 'HYG', 'IEF', 'SMH', 'XLK', 'XLV', 'XLE', 'XLB', 'XLP', 'XLY', 'XLC', 'XLU', 'XLRE', 'XLF', 'XLI']);
    for (const sym of KP.ETFS) { assert.equal(KP.validateBars(X.bars({ symbol: sym })).ok, true, sym); assert.equal(KP.validateMeasures(X.measures({ symbol: sym })).ok, true, sym); }
  });
  await ok('display tiers come only from Codex #556 fields: 검증됨 = tier VERIFIED with the adopted value, 검증 전(참고) = reference_value', () => {
    assert.deepEqual({ ...KP.VERIFICATION }, { VERIFIED: '검증됨', REFERENCE: '검증 전(참고)' });
    assert.equal(KP.verification, undefined, 'no Main-derived verification is left');
    const tiers = (kase) => { const f = X.codex556(kase); return [KP.analysisTiers(KP.validateAnalysis(f.technical).value), KP.measuresTiers(KP.validateMeasures(f.measures).value), KP.displayOf(KP.validateBars(f.chart).value)]; };
    let [a, m, c] = tiers('available');
    assert.deepEqual([a.display.state, c.state, c.tag], ['AVAILABLE', 'AVAILABLE', '검증 전(참고)']);
    assert.deepEqual(a.rows.filter((r) => r.value !== null).map((r) => [r.id, r.kind, r.value, r.tag]), [['SMA_5', 'VERIFIED', '11', '검증됨']], 'the adopted value with 검증됨');
    assert.ok(a.rows.filter((r) => r.value === null).every((r) => r.kind === 'HELD' && /^미산출 · /.test(r.text) && r.tag === null), 'held: one-line reason, no tag');
    assert.ok(m.rows.every((r) => r.kind === 'HELD'), 'measures without a raw value are held');
    [a] = tiers('reference');
    const sma = a.rows.find((r) => r.id === 'SMA_5'), file = KP.validateAnalysis(X.codex556('reference').technical).value;
    assert.deepEqual([sma.kind, sma.value, sma.tag], ['REFERENCE', '11', '검증 전(참고)'], 'the reference_value with 검증 전(참고)');
    assert.equal(file.metrics.SMA_5.value, null, 'never promoted into the adopted value');
    assert.deepEqual(KP.analysisView(file).adopted, [], 'the adopted list stays empty');
    [a, m, c] = tiers('withheld');
    assert.deepEqual([a.display.state, c.state, a.display.line], ['WITHHELD', 'WITHHELD', '보류 · 분할 같은 원주가 급변 · 검토 필요'], 'one line naming the hold reason');
    assert.ok(a.withheld > 0 && a.rows.every((r) => r.kind === 'VERIFIED'), 'WITHHELD: no reference row, only verified adopted values');
    assert.deepEqual([m.rows.length, m.withheld], [0, 5]);
    assert.ok(!JSON.stringify([a.rows, m.rows]).includes('"REFERENCE"'));
  });
  await ok('absent or unknown display / tier fields fail closed: no value, no 검증됨, one 검증 표시 없음 line', () => {
    // The #493-shaped synthetic files carry no display: nothing of their values is shown.
    for (const t of [KP.analysisTiers(KP.validateAnalysis(X.analysis({ adopted: true })).value), KP.measuresTiers(KP.validateMeasures(X.measures()).value)]) {
      assert.equal(t.display.state, 'UNKNOWN'); assert.ok(t.rows.every((r) => r.kind === 'HELD' && r.value === null && r.text === '검증 표시 없음'));
    }
    const base = X.codex556('available');
    const variants = [
      (f) => { f.technical.display.validation_tier = 'VERIFIED'; }, (f) => { f.technical.display.official = true; }, (f) => { f.technical.display.state = 'SHOWN'; },
      (f) => { f.technical.display.label = '검증됨'; }, (f) => { delete f.technical.display.hold_reasons; }, (f) => { delete f.technical.display; },
    ];
    for (const change of variants) {
      const f = JSON.parse(JSON.stringify(base)); change(f);
      const t = KP.analysisTiers(KP.validateAnalysis(f.technical).value);
      assert.equal(t.display.state, 'UNKNOWN'); assert.ok(!t.rows.some((r) => r.tag === '검증됨' || r.value !== null), String(change));
    }
    // A metric tier that does not match its values, or an unknown tier, is held (never 검증됨, never a value).
    for (const change of [(m) => { m.validation_tier = 'CONFIRMED'; }, (m) => { delete m.validation_tier; }, (m) => { m.validation_tier = 'UNVERIFIED_REFERENCE'; }]) {
      const f = JSON.parse(JSON.stringify(base)); change(f.technical.metrics.SMA_5);
      const r = KP.analysisTiers(KP.validateAnalysis(f.technical).value).rows.find((x) => x.id === 'SMA_5');
      assert.deepEqual([r.kind, r.value, r.tag], ['HELD', null, null], String(change));
    }
    const f = JSON.parse(JSON.stringify(X.codex556('reference'))); f.technical.metrics.SMA_5.validation_tier = 'VERIFIED';
    assert.equal(KP.analysisTiers(KP.validateAnalysis(f.technical).value).rows.find((x) => x.id === 'SMA_5').kind, 'HELD', 'VERIFIED without an adopted value is held');
    assert.equal(KP.displayOf(KP.validateQgv(X.qgv()).value, { stateful: false }).state, 'UNKNOWN', 'a qgv file without display');
  });
  await ok('KIS V (stage 1): Codex #556 official_reference output is read as given; calc_version, basis day, source, tag; rank null', () => {
    assert.ok(KP.QGV_FIELDS.includes('calc_version') && KP.QGV_FIELDS.includes('price_basis_date'));
    const r = KP.validateQgv(X.codexQgv()); assert.equal(r.ok, true, JSON.stringify(r));
    assert.equal(r.value.rank, null);
    const v = KP.qgvView(r.value, 'NASDAQ:AAPL');
    assert.deepEqual([v.calc_version, v.price_basis_date, v.source, v.display.state, v.display.tag], [X.C556.qgv.calc_version, '2026-10-23', 'KIS', 'AVAILABLE', '검증 전(참고)']);
    const row = r.value.rows['NASDAQ:AAPL'];
    assert.deepEqual(v.row.axes.slice(0, 2), ['Q ' + Math.round(row.axes.Q.score * 10) / 10, 'G ' + Math.round(row.axes.G.score * 10) / 10], 'the file\'s scores, only rounded for display');
    assert.equal(v.row.total, row.axes.V.score === null ? '총점 미산출 · 세 축 필요' : 'QGV ' + Math.round(row.total * 10) / 10, 'no total without V');
    assert.match(v.rank, /^비공개 순위 없음 · 비공개 참고 결과라 순위 없음$/);
    assert.equal(KP.qgvView(r.value, 'NASDAQ:NVDA').row.price, 'KIS 가격 반영', 'the code fed from the synthetic contract');
    assert.match(v.stages, /^가격 반영 \d+ · V 원시값 \d+ · V 요소 \d+$/);
    assert.ok(v.bases.includes('WEIGHTED_AVERAGE_DILUTED_PROXY_NOT_ACTUAL_OUTSTANDING'));
    for (const [change, code] of [[(q) => { q.rank = 1; }, 'RANK_NOT_ALLOWED'], [(q) => { q.calc_version = ''; }, 'TYPE'], [(q) => { q.source = 5; }, 'TYPE'], [(q) => { delete q.calc_version; }, 'KEY_MISSING']]) {
      const q = X.codexQgv(); change(q); assert.equal(KP.validateQgv(q).code, code);
    }
    assert.equal(KP.qgvView(KP.validateQgv({ ...X.qgv(), source: 'KIS retained dailyprice MODP0' }).value, null).source, 'KIS retained dailyprice MODP0');
  });
  await ok('Codex #556 total policy (2abdd286): partial totals masked by the producer, counts as given, contradictions refused', () => {
    const q = X.codexQgv(), r = KP.validateQgv(q); assert.equal(r.ok, true, JSON.stringify(r));
    assert.equal(q.total_policy, KP.TOTAL_POLICY);
    assert.ok(Object.values(q.rows).every((x) => x.verification === 'UNVERIFIED_REFERENCE' && x.total === null && x.total_reason === 'THREE_AXES_REQUIRED'));
    const v = KP.qgvView(r.value, 'NASDAQ:AAPL');
    assert.equal(v.row.total, '총점 미산출 · 세 축 필요', 'no total, one short reason');
    assert.equal(v.coverage.at(-1), '총점 ' + q.coverage.total + ' / ' + q.coverage.codes, 'coverage.total as given');
    assert.equal(v.diagnostics, '엔진 총점 ' + q.diagnostics.original_engine_total_count + ' · 부분 총점 미표시 ' + q.diagnostics.suppressed_partial_totals, 'diagnostics as given, never recomputed');
    assert.equal(Object.hasOwn(q.coverage, 'engine_total_computed'), false);
    // A complete row (all three axes) keeps its total under the policy.
    const full = X.codexQgv(); const row = full.rows['NASDAQ:AAPL']; row.axes.V.score = 42.42; row.total = 50.55; delete row.total_reason;
    assert.equal(KP.qgvView(KP.validateQgv(full).value, 'NASDAQ:AAPL').row.total, 'QGV 50.6');
    for (const [change, code, path] of [
      [(x) => { x.rows['NASDAQ:AAPL'].total = 12.5; }, 'TOTAL_POLICY_VIOLATION', '$.rows.NASDAQ:AAPL.total'],
      [(x) => { delete x.rows['NASDAQ:AAPL'].total_reason; }, 'TOTAL_POLICY_VIOLATION', '$.rows.NASDAQ:AAPL.total'],
      [(x) => { delete x.rows['NASDAQ:AAPL'].verification; }, 'KEY_MISSING', '$.rows.NASDAQ:AAPL.verification'],
      [(x) => { x.rows['NASDAQ:AAPL'].verification = 'VERIFIED'; }, 'ENUM', '$.rows.NASDAQ:AAPL.verification'],
      [(x) => { x.total_policy = 'ANY'; }, 'ENUM', '$.total_policy'],
      [(x) => { x.coverage.engine_total_computed = 3; }, 'COUNT_CONFLICT', '$.coverage.engine_total_computed'],
      [(x) => { delete x.coverage.total; }, 'COUNT_INVALID', '$.coverage.total'],
      [(x) => { x.coverage.total = x.coverage.codes + 1; }, 'COUNT_INVALID', '$.coverage.total'],
      [(x) => { delete x.diagnostics; }, 'TYPE', '$.diagnostics'],
      [(x) => { x.diagnostics.suppressed_partial_totals = -1; }, 'COUNT_INVALID', '$.diagnostics.suppressed_partial_totals'],
    ]) { const x = X.codexQgv(); change(x); assert.deepEqual(KP.validateQgv(x), { ok: false, code, path }, code + ' ' + path); }
    // The earlier shape (no policy): a partial total is never shown, and a THREE_AXES_REQUIRED row with a total is refused.
    const old = X.qgv(); old.rows['NASDAQ:NVDA'].axes.V.score = null;
    assert.equal(KP.qgvView(KP.validateQgv(old).value, 'NASDAQ:NVDA').row.total, '총점 미산출 · 세 축 필요');
    const qOld = X.qgv(); qOld.rows['NASDAQ:NVDA'].axes.Q.score = null; qOld.rows['NASDAQ:NVDA'].axes.V.score = 40;
    assert.equal(KP.qgvView(KP.validateQgv(qOld).value, 'NASDAQ:NVDA').row.total, '총점 미산출 · 세 축 필요', 'any missing axis, not V only');
    const bad = X.qgv(); bad.rows['NASDAQ:NVDA'].total_reason = 'THREE_AXES_REQUIRED';
    assert.equal(KP.validateQgv(bad).code, 'TOTAL_POLICY_VIOLATION');
  });
  await ok('the Codex #556 synthetic payloads pass every reader unchanged (chart, technical, measures; three cases)', () => {
    for (const kase of ['available', 'reference', 'withheld']) {
      const f = X.codex556(kase);
      for (const [fn, raw] of [[KP.validateBars, f.chart], [KP.validateAnalysis, f.technical], [KP.validateMeasures, f.measures]]) { const r = fn(raw); assert.equal(r.ok, true, kase + ' ' + JSON.stringify(r)); }
    }
    assert.equal(X.C556.generated_by.commit, '2abdd286d83400fd2686a4f49eeb7d495f704689');
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
    const h = harness({ answers: [{ status: 200, body: { synthetic: true } }] });
    await assert.rejects(h.c.get('stock', 'NVDA'), /AUTH_REQUIRED/); assert.equal(h.sent.length, 0);
    await h.c.connect();
    assert.equal(h.tokenRequests[0].scope, 'openid email'); assert.equal(h.tokenRequests[0].include_granted_scopes, false);
    const body = await h.c.get('stock', 'NVDA');
    assert.equal(body.synthetic, true);
    const [s] = h.sent;
    assert.equal(s.url, ORIGIN + KP.ROUTE.stock + '?symbol=NVDA');
    assert.deepEqual(s.init.headers, { Authorization: 'Bearer synthetic-token' });
    assert.equal(s.init.credentials, 'omit'); assert.equal(s.init.cache, 'no-store'); assert.equal(s.init.referrerPolicy, 'no-referrer');
    await assert.rejects(h.c.get('stock', '../x'), /REQUEST_INVALID/); await assert.rejects(h.c.get('orders', null), /ROUTE_UNKNOWN/);
  });
  await ok('client: the two routes the panels read — stock takes a symbol (and ?part=qgv), status takes no query; the four older routes and macro / news / classification are unknown', async () => {
    assert.deepEqual(Object.keys(KP.ROUTE).sort(), ['status', 'stock']);
    const h = harness({ answers: [{ status: 200, body: X.qgv() }, { status: 200, body: { schema: X.K('status/1') } }, { status: 200, body: { synthetic: true } }] });
    await h.c.connect();
    await h.c.get('stockQgv', null); await h.c.get('status', null); await h.c.get('stock', 'BRK-B');
    assert.deepEqual(h.sent.map((x) => x.url), [ORIGIN + KP.ROUTE.stock + '?part=qgv', ORIGIN + KP.ROUTE.status, ORIGIN + KP.ROUTE.stock + '?symbol=BRK-B']);
    for (const x of h.sent) { assert.deepEqual(x.init.headers, { Authorization: 'Bearer synthetic-token' }); assert.equal(x.init.redirect, 'error'); assert.equal(x.init.credentials, 'omit'); }
    for (const route of ['chart', 'analysis', 'technical', 'qgv', 'macro', 'news', 'classification']) await assert.rejects(h.c.get(route, null), /ROUTE_UNKNOWN/, route);
    await assert.rejects(h.c.get('stock', null), /REQUEST_INVALID/, 'stock needs a symbol');
    await assert.rejects(h.c.get('stock', 'BRK/B'), /REQUEST_INVALID/, 'stock takes the request symbol, not the KIS file symbol');
    assert.equal(h.sent.length, 3);
  });
  await ok('client: KIS V reads the qgv part of the stock route (no symbol); a symbol on the part is refused', async () => {
    assert.deepEqual(KP.PARTS, { stockQgv: { route: 'stock', query: '?part=qgv' } });
    const h = harness({ answers: [{ status: 200, body: X.qgv() }] });
    await h.c.connect();
    await h.c.get('stockQgv', null);
    assert.deepEqual(h.sent.map((x) => x.url), [ORIGIN + KP.ROUTE.stock + '?part=qgv']);
    await assert.rejects(h.c.get('stockQgv', 'NVDA'), /REQUEST_INVALID/, 'the part takes no symbol');
    assert.equal(h.sent.length, 1);
  });
  await ok('stockParts: the one-file view is only assembled into the three parts the panel reads; the readers then check them', async () => {
    const c = X.bars({ symbol: 'NVDA' }), a = X.analysis({ adopted: true }), m = X.measures({ symbol: 'NVDA' });
    const { bars, raw_bars: rawBars, schema, ...header } = c;
    const fields = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', ...Array.from({ length: 10 }, (_, i) => 'I' + i)];
    const view = () => ({ schema: X.K('stock-view/1'), publication_scope: 'OWNER_PRIVATE_ONLY', symbol: 'NVDA', evaluation_day: a.evaluation_day, fields: [...fields],
      rows: bars.map((b) => [b.date, b.open, b.high, b.low, b.close, b.volume, null, ...Array(10).fill(1.5)]), chart: { ...header, schema: X.K('chart-metadata/1') },
      latest: { technical: a, measures: m }, additional_requests_for_toggle: 0, additional_requests_for_retained_period: 0 });
    const r = KP.stockParts(view());
    assert.equal(r.ok, true);
    assert.equal(r.value.chart.schema, KP.SCHEMA.BARS);
    assert.deepEqual(r.value.chart.bars.map((b) => [b.date, b.close]), bars.map((b) => [b.date, b.close]), 'the six columns as given, no value changed');
    assert.deepEqual(r.value.chart.raw_bars, r.value.chart.bars, 'a RAW view: the RAW rows themselves');
    assert.equal(KP.validateBars(r.value.chart).ok, true, 'the assembled chart passes the unchanged chart reader');
    assert.deepEqual([KP.validateAnalysis(r.value.analysis).ok, KP.validateMeasures(r.value.measures).ok], [true, true]);
    const noMeasures = view(); delete noMeasures.latest.measures;
    assert.equal(KP.stockParts(noMeasures).value.measures, null, 'no measures object: that part alone is 자료 없음');
    // The producer's SPLIT_ADJUSTED view (#593, kis_stock_journal.py): raw_fields date..amount and raw_rows in those 7 columns.
    const RAW_FIELDS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount'];
    const withRaw = (v) => { v.raw_fields = [...RAW_FIELDS]; v.raw_rows = v.rows.map((x) => x.slice(0, 6).concat(['1'])); return v; };
    const split = KP.stockParts(withRaw(view()));
    assert.equal(split.ok, true, 'a 7-column RAW series named by raw_fields');
    assert.equal(split.value.chart.raw_bars.length, bars.length, 'a separate RAW series is carried');
    assert.deepEqual(split.value.chart.raw_bars.map((b) => [b.date, b.close]), bars.map((b) => [b.date, b.close]), 'its six columns as given');
    for (const [label, change, code] of [
      ['fields out of order', (v) => { v.fields = ['open', 'date', ...v.fields.slice(2)]; }, 'STOCK_FIELDS'],
      ['short row', (v) => { v.rows[0] = v.rows[0].slice(0, 5); }, 'TYPE'],
      ['another symbol in the header', (v) => { v.chart.symbol = 'AMD'; }, 'SYMBOL'],
      ['scope', (v) => { v.publication_scope = 'PUBLIC'; }, 'SCOPE'],
      ['no latest', (v) => { delete v.latest; }, 'KEY_MISSING'],
      ['another schema', (v) => { v.schema = X.K('stock-view/2'); }, 'SCHEMA_VERSION'],
      ['a request symbol, not the file symbol', (v) => { v.symbol = 'NVDA/X'; v.chart.symbol = 'NVDA/X'; }, 'SYMBOL'],
      ['not a day', (v) => { v.evaluation_day = '2026-1-05'; }, 'DATE'],
      ['a toggle request counted', (v) => { v.additional_requests_for_toggle = 1; }, 'STOCK_REQUESTS'],
      ['a retained-period request counted', (v) => { v.additional_requests_for_retained_period = 2; }, 'STOCK_REQUESTS'],
      ['16 fields', (v) => { v.fields = v.fields.slice(0, 16); }, 'STOCK_FIELDS'],
      ['a field not a string', (v) => { v.fields[9] = 9; }, 'STOCK_FIELDS'],
      ['a long row', (v) => { v.rows[1] = [...v.rows[1], 0]; }, 'TYPE'],
      ['a short RAW row', (v) => { withRaw(v); v.raw_rows[0].pop(); }, 'TYPE'],
      ['a long RAW row', (v) => { withRaw(v); v.raw_rows[1].push('2'); }, 'TYPE'],
      ['raw_rows without raw_fields', (v) => { withRaw(v); delete v.raw_fields; }, 'KEY_MISSING'],
      ['raw_fields without raw_rows', (v) => { withRaw(v); delete v.raw_rows; }, 'KEY_MISSING'],
      ['raw_fields out of order', (v) => { withRaw(v); v.raw_fields = ['open', 'date', ...RAW_FIELDS.slice(2)]; }, 'STOCK_FIELDS'],
      ['raw_fields too short', (v) => { withRaw(v); v.raw_fields = RAW_FIELDS.slice(0, 5); v.raw_rows = v.raw_rows.map((x) => x.slice(0, 5)); }, 'STOCK_FIELDS'],
      ['raw_fields not strings', (v) => { withRaw(v); v.raw_fields[6] = 6; }, 'STOCK_FIELDS'],
      ['raw_rows not a list', (v) => { withRaw(v); v.raw_rows = {}; }, 'TYPE'],
      ['rows not a list', (v) => { v.rows = {}; }, 'TYPE'],
    ]) { const v = view(); change(v); const x = KP.stockParts(v); assert.deepEqual([x.ok, x.code], [false, code], label); }
  });
  await ok('client: a wider scope is refused; a server 403 drops the token; expiry drops it; disconnect drops it', async () => {
    let h = harness({ scope: 'openid email https://www.googleapis.com/auth/drive.file' });
    await assert.rejects(h.c.connect(), /LOGIN_REFUSED/); assert.equal(h.c.state().connected, false);
    h = harness({ answers: [{ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } }] }); await h.c.connect();
    await assert.rejects(h.c.get('status', null), /AUTH_FORBIDDEN/); assert.equal(h.c.state().connected, false, 'server refusal drops the token');
    h = harness({ expires: 60 }); await h.c.connect(); assert.equal(h.c.state().connected, true);
    h.clock.now += 61_000; assert.equal(h.c.state().connected, false, 'expired token dropped');
    await assert.rejects(h.c.get('status', null), /AUTH_REQUIRED/); assert.equal(h.sent.length, 0);
    h = harness(); await h.c.connect(); h.c.disconnect(); assert.equal(h.c.state().connected, false);
    h = harness({ answers: [{ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } }] }); await h.c.connect();
    await assert.rejects(h.c.get('stock', 'NVDA'), /KIS_SERIES_NOT_FOUND/); assert.equal(h.c.state().connected, true, 'a missing file keeps the session');
  });
  await ok('client: only an answer that never came or a 5xx without the Worker\'s code is marked unreachable (one retry in the layer); coded errors and 401 / 403 / 404 / 429 never are', async () => {
    // A client whose send fails (reject), is aborted, or answers raw text.
    const one = async ({ status = 503, raw = '', reject = false, abort = false } = {}) => {
      const controller = new AbortController(), scope = 'openid https://www.googleapis.com/auth/userinfo.email';
      const google = { accounts: { oauth2: { initTokenClient: (cfg) => ({ requestAccessToken: () => cfg.callback({ access_token: 'synthetic-token', expires_in: '3600', scope }) }) } } };
      const send = async () => { if (abort) { controller.abort(); throw new TypeError('aborted'); } if (reject) throw new TypeError('Failed to fetch');
        return { status, ok: false, json: async () => JSON.parse(raw) }; };
      const c = KP.createClient({ win: { google }, clientId: 'synthetic-client', origin: ORIGIN, send, now: () => 1_000_000 });
      await c.connect();
      return c.get('stock', 'NVDA', controller.signal).then(() => null, (e) => e);
    };
    const mark = (e) => [e.message, e.unreachable === true];
    assert.deepEqual(mark(await one({ reject: true })), ['UPSTREAM_UNAVAILABLE', true], 'a failed request (network, CORS, the runtime stop)');
    assert.deepEqual(mark(await one({ status: 503, raw: '<html>error 1102</html>' })), ['UPSTREAM_UNAVAILABLE', true], 'a non-JSON 5xx');
    assert.deepEqual(mark(await one({ status: 502, raw: '{"error":{"code":"x"}}' })), ['UPSTREAM_UNAVAILABLE', true], 'a 5xx whose code is not a fixed code');
    assert.deepEqual(mark(await one({ abort: true })), ['CANCELED', false], 'an abort is a cancel');
    const coded = async (status, body) => { const h = harness({ answers: [{ status, body }] }); await h.c.connect(); return h.c.get('stock', 'NVDA').then(() => null, (e) => e); };
    for (const [status, body, message] of [[503, { error: { code: 'UPSTREAM_UNAVAILABLE' } }, 'UPSTREAM_UNAVAILABLE'], [502, { error: { code: 'KIS_STOCK_PIN' } }, 'KIS_STOCK_PIN'],
      [401, null, 'AUTH_FORBIDDEN'], [403, { error: { code: 'AUTH_FORBIDDEN' } }, 'AUTH_FORBIDDEN'], [404, { error: { code: 'KIS_SERIES_NOT_FOUND' } }, 'KIS_SERIES_NOT_FOUND'],
      [404, null, 'UPSTREAM_UNAVAILABLE'], [429, { error: { code: 'RATE_LIMITED' } }, 'RATE_LIMITED'], [429, null, 'UPSTREAM_UNAVAILABLE']]) {
      assert.deepEqual(mark(await coded(status, body)), [message, false], status + ' ' + JSON.stringify(body));
    }
  });
  console.log(JSON.stringify({ passed: true, checks: n }));
})().catch((e) => { console.error(e); process.exitCode = 1; });
