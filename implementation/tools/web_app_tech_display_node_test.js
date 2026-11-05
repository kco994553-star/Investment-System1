'use strict';
// 3.1.2 고른 기업의 지표 (owner 2026-11-05): web_app/tech-display.js against Codex's technical-offline-display/1 +
// technical-display-readiness/1 (#478 419add34).
//  - The SYNTHETIC fixture (Codex's own tool on synthetic bars, sha256 pinned) is read unchanged: six series, one signal day.
//  - Kinds: VALUE → 채택값 with the adopted value (the contract example SMA20 240.5, RSI14 100, MACD 7, signal 7, histogram a real
//    0 shown as 0); DIAGNOSTIC → 진단값만 있음 with no value text at all (raw_value never shown); NOT_COMPUTED → 미산출 with its
//    reasons in words (WARMUP, ZERO_TOTAL_CHANGE, OHLC_MISSING, PRICE_WINDOW_INCOMPLETE); a null is never 0.
//  - Per series: 순위 없음 with the fixed-id reason, availability NOT_VERIFIED, stale UNKNOWN · UPDATE_SCHEDULE_NOT_CONNECTED, warm-up
//    READY / INSUFFICIENT / NOT_EVALUATED, adjustment UNCONFIRMED vs DOCUMENTED_NO_SPLIT.
//  - The validator refuses the whole file at its first fault; source() is NONE; find() by symbol (not in file, ambiguous).
const assert = require('node:assert/strict');
const D = require('../src/investment_system/product/web_app/tech-display.js');
const X = require('./web_app_tech_display_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const P = X.display(), V = D.validate(P);
const S = (sym) => D.find(V.value, sym).series;
const item = (sym, id) => D.view(S(sym)).items.find((x) => x.id === id);
const mut = (fn) => { const p = JSON.parse(JSON.stringify(P)); fn(p); return D.validate(p); };

ok('fixture: pinned, SYNTHETIC, read unchanged and deep-frozen', () => {
  assert.equal(X.sha(), X.SHA256);
  assert.equal(X.fixture().data_kind, 'SYNTHETIC');
  assert.equal(V.ok, true, JSON.stringify(V));
  assert.deepEqual(V.value.series.map((s) => s.symbol), X.fixture().symbols);
  assert.ok(Object.isFrozen(V.value.series[0].readiness.metrics.SMA_20.warmup));
  assert.deepEqual(Object.keys(V.value.series[0].metrics), D.COMPONENTS);
  assert.equal(D.COMPONENTS.length, 13);
});
ok('VALUE: 채택값 with the contract example values; a real 0 is a value', () => {
  const v = D.view(S('SYN_VALUE'));
  assert.deepEqual({ ...v.counts }, { VALUE: 13, DIAGNOSTIC: 0, NOT_COMPUTED: 0 });
  assert.equal(v.countsText, '채택값 13 · 진단값만 있음 0 · 미산출 0');
  const want = { SMA_20: '240.5', SMA_120: '190.5', EMA_20: '240.5', RSI_14: '100', MACD_12_26: '7', MACD_SIGNAL_9: '7', MACD_HISTOGRAM_12_26_9: '0', ATR_14: '2' };
  for (const [id, t] of Object.entries(want)) { const it = item('SYN_VALUE', id); assert.equal(it.kind, 'VALUE'); assert.equal(it.kindText, '채택값'); assert.equal(it.value, t, id); }
  assert.equal(item('SYN_VALUE', 'RSI_14').unit, '% (0~100)');
  assert.equal(item('SYN_VALUE', 'SMA_20').unit, '주당 · 원 통화 USD');
  assert.equal(item('SYN_VALUE', 'SMA_20').observed, '20 / 20세션');
  assert.equal(item('SYN_VALUE', 'EMA_20').observed, '250 / 250세션');
  assert.equal(item('SYN_VALUE', 'EMA_20').init, '전체 보유 이력으로 시작값 (시작 2017-01-03)');
  assert.equal(item('SYN_VALUE', 'SMA_20').window, S('SYN_VALUE').metrics.SMA_20.window_start + ' ~ 2017-12-28');
  assert.equal(D.num(0), '0'); assert.equal(D.num(-0), '0'); assert.equal(D.num(null), null); assert.equal(D.num(-1.23456), '−1.2346');
});
ok('DIAGNOSTIC: 진단값만 있음, no value text, the reason words (identity / split window)', () => {
  const v = D.view(S('SYN_IDENTITY'));
  assert.deepEqual({ ...v.counts }, { VALUE: 0, DIAGNOSTIC: 13, NOT_COMPUTED: 0 });
  for (const it of v.items) { assert.equal(it.kindText, '진단값만 있음'); assert.equal(it.value, null); assert.deepEqual(it.reasons.map((r) => r.code), ['IDENTITY_UNCONFIRMED']); }
  assert.ok(!JSON.stringify(v).includes('240.8125'), 'raw_value nowhere in the view');
  assert.equal(v.identity, '신원 미확인 · 근거 문서 있음');
  const split = D.view(S('SYN_SPLIT120'));
  assert.deepEqual({ ...split.counts }, { VALUE: 7, DIAGNOSTIC: 6, NOT_COMPUTED: 0 });
  assert.equal(item('SYN_SPLIT120', 'SMA_120').kind, 'VALUE');
  const ema = item('SYN_SPLIT120', 'EMA_20');
  assert.equal(ema.kind, 'DIAGNOSTIC'); assert.equal(ema.value, null); assert.equal(ema.adjustmentState, 'UNCONFIRMED'); assert.equal(ema.warmupState, 'READY');
  assert.equal(ema.reasons[0].text, '무분할 근거가 의존 구간을 덮지 못함');
  assert.ok(ema.adjustment.startsWith('의존 구간 무분할 근거 미확인 · 필요 2017-01-03 ~ 2017-12-28 · 근거 '), ema.adjustment);
});
ok('NOT_COMPUTED: 미산출 with reasons; warm-up INSUFFICIENT / READY / NOT_EVALUATED kept apart; never 0', () => {
  const sma120 = item('SYN_FLAT35', 'SMA_120'), rsi = item('SYN_FLAT35', 'RSI_14'), macd = item('SYN_FLAT35', 'MACD_12_26');
  assert.deepEqual([sma120.kind, sma120.value, sma120.warmupState, sma120.reasons[0].text], ['NOT_COMPUTED', null, 'INSUFFICIENT', '초기 봉 부족']);
  assert.deepEqual([rsi.kind, rsi.warmupState, rsi.reasons[0].code], ['NOT_COMPUTED', 'READY', 'ZERO_TOTAL_CHANGE']);
  assert.deepEqual([macd.kind, macd.value], ['VALUE', '0'], 'flat MACD is a real 0');
  const atr = item('SYN_NOHIGH', 'ATR_14');
  assert.deepEqual([atr.kind, atr.warmupState, atr.reasons[0].text], ['NOT_COMPUTED', 'NOT_EVALUATED', '고가·저가 결손']);
  const empty = D.view(S('SYN_EMPTY'));
  assert.deepEqual({ ...empty.counts }, { VALUE: 0, DIAGNOSTIC: 0, NOT_COMPUTED: 13 });
  for (const it of empty.items) { assert.equal(it.kindText, '미산출'); assert.equal(it.value, null); assert.equal(it.continuityState, 'INCOMPLETE'); assert.equal(it.warmupState, 'NOT_EVALUATED'); }
  assert.equal(empty.history, '보유 일봉 0봉 · 2017-12-28 ~ 2017-12-28');
});
ok('series words: 순위 없음 with reason, availability NOT_VERIFIED, stale UNKNOWN · UPDATE_SCHEDULE_NOT_CONNECTED', () => {
  const v = D.view(S('SYN_VALUE'));
  assert.equal(v.rank, '순위 없음 · 고정 증권 ID 없음 · 순위를 매기지 않음'); assert.equal(v.rankCode, 'MISSING_RANKING_BLOCKED');
  assert.equal(v.availabilityCode, 'NOT_VERIFIED'); assert.ok(v.availability.includes('가용 시각 미확인'));
  assert.deepEqual([v.staleCode, v.staleReason, v.stale], ['UNKNOWN', 'UPDATE_SCHEDULE_NOT_CONNECTED', '최신 여부 알 수 없음 · 갱신 일정 미연결']);
  assert.ok(v.basis.includes('PIT 미검증') && v.basis.includes('공식 운영 가격 아님'));
  assert.equal(v.history, '보유 일봉 250봉 · 2017-01-03 ~ 2017-12-28');
});
ok('find by symbol: found, not in file, ambiguous', () => {
  assert.equal(D.find(V.value, 'SYN_VALUE').state, 'FOUND');
  assert.equal(D.find(V.value, 'NVDA').state, 'NOT_IN_FILE');
  const two = D.validate(X.relabel(P, { SYN_VALUE: 'AAA', SYN_SPLIT120: 'AAA' }));
  assert.equal(two.ok, true); assert.deepEqual(D.find(two.value, 'AAA'), { state: 'AMBIGUOUS', count: 2 });
});
ok('status: SYNTHETIC says 합성 개발 검증', () => {
  assert.equal(D.status(X.source(P)), '합성 개발 검증');
  assert.equal(D.status({ state: 'OK' }), '자료 종류 표시 없음');
});
ok('validator refuses the whole file at its first fault', () => {
  const cases = [
    ['schema', (p) => { p.schema = 'technical-offline-display/2'; }, 'ENUM', '$.schema'],
    ['empty', (p) => { p.series = []; }, 'EMPTY', '$.series'],
    ['unknown top key', (p) => { p.extra = 1; }, 'KEY_UNKNOWN', '$.extra'],
    ['missing component', (p) => { delete p.series[0].metrics.ATR_14; }, 'KEY_MISSING', '$.series[0].metrics.ATR_14'],
    ['value without state', (p) => { p.series[2].metrics.SMA_20.value = p.series[2].metrics.SMA_20.raw_value; }, 'REASON_WITH_VALUE', '$.series[2].metrics.SMA_20.null_reasons'],
    ['value not raw', (p) => { p.series[0].metrics.SMA_20.value = 1; }, 'VALUE_NOT_RAW', '$.series[0].metrics.SMA_20.value'],
    ['state mismatch', (p) => { p.series[1].readiness.metrics.EMA_20.state = 'VALUE'; }, 'STATE_MISMATCH', '$.series[1].readiness.metrics.EMA_20.state'],
    ['null without reason', (p) => { const m = p.series[5].metrics.SMA_5; m.null_reasons = []; p.series[5].readiness.metrics.SMA_5.block_reasons = []; }, 'NULL_REASON_MISSING', '$.series[5].metrics.SMA_5.null_reasons'],
    ['block reasons differ', (p) => { p.series[1].readiness.metrics.EMA_20.block_reasons = ['IDENTITY_UNCONFIRMED']; }, 'BLOCK_REASONS_MISMATCH', '$.series[1].readiness.metrics.EMA_20.block_reasons'],
    ['warm-up minimum', (p) => { p.series[0].readiness.metrics.RSI_14.warmup.minimum_sessions = 14; }, 'ENUM', '$.series[0].readiness.metrics.RSI_14.warmup.minimum_sessions'],
    ['observed sessions', (p) => { p.series[0].readiness.metrics.RSI_14.warmup.observed_sessions = 249; }, 'OBSERVED_MISMATCH', '$.series[0].readiness.metrics.RSI_14.warmup.observed_sessions'],
    ['init method', (p) => { p.series[0].readiness.metrics.EMA_20.initialization.method = 'ROLLING_CLOSE_MEAN'; }, 'ENUM', '$.series[0].readiness.metrics.EMA_20.initialization.method'],
    ['state unknown', (p) => { p.series[1].readiness.metrics.EMA_20.state = 'RAW'; }, 'ENUM', '$.series[1].readiness.metrics.EMA_20.state'],
    ['unit', (p) => { p.series[0].metrics.RSI_14.unit = 'SOURCE_CURRENCY_PER_SHARE'; }, 'ENUM', '$.series[0].metrics.RSI_14.unit'],
    ['rank', (p) => { p.series[0].rank = 1; }, 'RANK_UNEXPECTED', '$.series[0].rank'],
    ['availability', (p) => { p.series[0].readiness.availability_status = 'VERIFIED'; }, 'ENUM', '$.series[0].readiness.availability_status'],
    ['stale', (p) => { p.series[0].readiness.stale_status = 'FRESH'; }, 'ENUM', '$.series[0].readiness.stale_status'],
    ['as_of', (p) => { p.series[0].readiness.as_of = '2017-12-27'; }, 'AS_OF_MISMATCH', '$.series[0].readiness.as_of'],
    ['signal day', (p) => { p.series[3].signal_day = '2017-12-27'; }, 'SIGNAL_DAY_MISMATCH', '$.series[3].signal_day'],
    ['duplicate series', (p) => { p.series[1].series_id = p.series[0].series_id; }, 'SERIES_DUPLICATE', '$.series[1].series_id'],
    ['identity per series', (p) => { p.series[0].readiness.metrics.ATR_14.identity.state = 'UNKNOWN'; }, 'IDENTITY_MISMATCH', '$.series[0].readiness.metrics.ATR_14.identity'],
    ['adjustment window', (p) => { p.series[0].readiness.metrics.SMA_5.adjustment.required_start = '2017-01-03'; }, 'WINDOW_MISMATCH', '$.series[0].readiness.metrics.SMA_5.adjustment.required_start'],
    ['string number', (p) => { p.series[0].metrics.SMA_5.value = '248'; }, 'TYPE', '$.series[0].metrics.SMA_5.value'],
    ['date', (p) => { p.series[0].metrics.SMA_5.window_start = '2017-02-30'; }, 'DATE_INVALID', '$.series[0].metrics.SMA_5.window_start'],
    ['source kind', (p) => { p.series[0].source_kind = 'IEX_LAST_TRADE'; }, 'ENUM', '$.series[0].source_kind'],
    ['publication', (p) => { p.series[0].publication_status = 'PUBLIC'; }, 'ENUM', '$.series[0].publication_status'],
  ];
  for (const [name, fn, code, path] of cases) assert.deepEqual(mut(fn), { ok: false, code, path }, name);
  assert.deepEqual(D.validate(null), { ok: false, code: 'TYPE', path: '$' });
  assert.equal(mut((p) => { p.series[0].metrics.SMA_240 = { ...p.series[0].metrics.SMA_20, expected_days: 240, observation_days: 240, window_start: '2017-01-09', raw_value: 1, value: 1 };
    p.series[0].readiness.metrics.SMA_240 = { ...p.series[0].readiness.metrics.SMA_20, warmup: { minimum_sessions: 240, observed_sessions: 240, state: 'READY' },
      adjustment: { ...p.series[0].readiness.metrics.SMA_20.adjustment, required_start: '2017-01-09' } }; }).ok, true, 'SMA_240 (default OFF) may appear');
});
// source() is NONE (private research output, no request).
D.source().then((s) => { assert.equal(s.state, 'NONE'); assert.equal(s.payload, null); n++; console.log('PASS source() is NONE');
  console.log(JSON.stringify({ passed: true, checks: n })); }).catch((e) => { console.error('FAIL ' + e.stack); process.exitCode = 1; });
