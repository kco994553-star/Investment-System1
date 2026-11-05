'use strict';
// SYNTHETIC owner-private payloads for the 비공개 펼치기 tests (web_app/kis-private.js), shaped like Codex #480's writers
// (research/kis_price_bridge.py normalize_page / analyze, research/private_layer_qgv.py). Not a company, not a KIS value. The
// schema names are assembled at run time so no file carries a private schema literal (tests/test_private_boundary_static.py).
const K = (rest) => ['kis', rest].join('-');
const DAYS = ['2026-10-26', '2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30'];
const row = (d, i) => ({ date: d, open: String(100 + i), high: String(102 + i), low: String(99 + i), close: String(101 + i) + '.5', volume: '1000', amount: '101500',
  corrected: null, collected_at: '2026-10-31T04:00:00Z', source_sha256: 'a'.repeat(64) });
function bars({ symbol = 'NVDA', days = DAYS } = {}) {
  const raw = days.map(row);
  return { schema: K('bars/1'), symbol, security_id: 'SYNTHETIC-SECURITY-1', issuer_id: null, exchange: 'NASDAQ', currency: 'USD',
    source: 'KIS retained dailyprice MODP0', price_basis_date: days.length ? days[days.length - 1] : null, collected_at: '2026-10-31T04:00:00Z',
    corrected_at: null, historical_available_at: null, calendar: 'NYSE', timezone: 'America/New_York', basis: 'RAW', dividend_adjustment: 'NONE',
    session_scope: 'PROVIDER_UNCONFIRMED', price_scope_status: 'UNCONFIRMED', volume_basis: 'PROVIDER_REPORTED_UNCONFIRMED', amount_basis: 'PROVIDER_REPORTED_UNCONFIRMED',
    splits: [], confirmed_ranges: [{ from: days[0], to: days[days.length - 1], evidence: 'SYNTHETIC' }], held_ranges: [], raw_bars: raw, bars: raw.map((r) => ({ ...r })),
    rejected_rows: [], suspensions: [], timestamp_basis: 'SESSION_DATE_ONLY_NO_PROVIDER_INTRADAY_TIME', publication_scope: 'OWNER_PRIVATE_ONLY', fixture_kind: 'SYNTHETIC_NOT_A_COMPANY' };
}
// The current state of the real result as the owner described it (11/05): raw diagnostics exist, no indicator adopted.
function analysis({ adopted = false, status = 'NORMAL', evaluationDay = '2026-10-30' } = {}) {
  const metrics = {
    SMA_20: { raw_value: '101.25', value: adopted ? '101.25' : null, null_reasons: adopted ? [] : ['VOLUME_SCOPE_UNCONFIRMED'] },
    RSI_14: { raw_value: '55.5', value: null, null_reasons: ['INSUFFICIENT_HISTORY'] },
    MACD_12_26: { raw_value: null, value: null, null_reasons: ['INSUFFICIENT_HISTORY'] },
  };
  const raw = Object.values(metrics).filter((m) => m.raw_value !== null).length, ad = Object.values(metrics).filter((m) => m.value !== null).length;
  return { schema: K('bars/1/analysis'), status, data_asof: '2026-10-30', evaluation_day: evaluationDay, collected_at: '2026-10-31T04:00:00Z', corrected_at: null,
    historical_available_at: null, diagnostic_basis: 'RAW', chart_basis: 'RAW', metrics, raw_count: raw, adopted_count: ad,
    QGV_coverage_change: null, QGV_reason: 'OFFICIAL_MODEL_UNCHANGED_NOT_RECALCULATED' };
}
// Private QGV through the common engine: Q and G computed, V not (the owner's 11/05 description of the real result).
function qgv({ priceBasis = '2026-10-30', codes = ['NASDAQ:NVDA', 'NASDAQ:AAPL'] } = {}) {
  const rows = Object.fromEntries(codes.map((c, i) => [c, { axes: { Q: { score: 70.25 - i, reason: null }, G: { score: 60.5 - i, reason: null }, V: { score: null, reason: 'V_INPUTS_NOT_AVAILABLE' } },
    total: 64.4 - i, total_reason: null }]));
  return { schema: K('qgv/1'), layer: 'OWNER_PRIVATE', calculation_path: 'qgv_official.prepare/price_status/engine_quotes/score/projection', calc_version: 'SYNTHETIC-CALC',
    engine_version: 'SYNTHETIC', financial_input_as_of: '2026-10-29T22:30:00Z', price_basis_date: priceBasis, calculated_at: '2026-10-31T05:00:00Z', historical_pit_proven: false,
    price_status: Object.fromEntries(codes.map((c) => [c, 'SUPPLIED'])), population: codes, rows,
    coverage: { codes: codes.length, Q: codes.length, G: codes.length, V: 0, QGV: 0, engine_total_without_V: codes.length, engine_total_computed: codes.length },
    rank: null, rank_reason: 'PAIRED_COMPARISON_POPULATION_NOT_ESTABLISHED', official_publication_replaced: false, TARGET_modified: false };
}
// The five measures of one company on its signal day (kis-technical-measures/1, Codex's technical-measures mode, #480 follow-up),
// HAND-BUILT from the shape of the writer's output (keys, value types and state rules only; no number of a real file): 3m
// momentum adopted, 6m momentum a diagnostic only, 12m momentum / volatility / dollar volume not computed with their reasons.
// Every number below is made up and carries the digits 4242 so a test can show where it may appear.
function measures({ symbol = 'NVDA', signalDay = '2026-10-30', adopted = true } = {}) {
  const base = (unit, obs, extra = {}) => ({ value: null, raw_value: null, unit, null_reasons: [], gt_zero: null, raw_gt_zero: null, window_start: '2026-05-01',
    window_end: signalDay, anchor_day: '2026-04-30', observed_days: 100, expected_days: 126, observation_unit: obs, state: 'NOT_COMPUTED', ...extra });
  const metrics = {
    momentum_3m: base('PERCENT', 'CLOSES', adopted ? { value: '12.4242', raw_value: '12.4242', gt_zero: true, raw_gt_zero: true, window_start: '2026-07-30', anchor_day: '2026-07-29', observed_days: 64, expected_days: 64, state: 'VALUE' }
      : { raw_value: '12.4242', raw_gt_zero: true, null_reasons: ['IDENTITY_RANGE_UNCONFIRMED'], state: 'DIAGNOSTIC' }),
    momentum_6m: base('PERCENT', 'CLOSES', { raw_value: '20.4242', raw_gt_zero: true, null_reasons: ['IDENTITY_RANGE_UNCONFIRMED'], state: 'DIAGNOSTIC' }),
    momentum_12m: base('PERCENT', 'CLOSES', { null_reasons: ['PRICE_WINDOW_INCOMPLETE_OR_INVALID', 'ACTION_BASIS_UNCONFIRMED'] }),
    volatility_6m: base('PERCENT_PER_DAY', 'DAILY_RETURNS', { null_reasons: ['RETURN_WINDOW_INCOMPLETE_OR_INVALID'], observed_price_days: 101, expected_price_days: 127, ddof: 1, annualized: false }),
    dollar_volume_6m: base('USD_PER_TRADING_DAY', 'TRADING_DAYS', { null_reasons: ['VOLUME_WINDOW_INCOMPLETE_OR_INVALID', 'TRADE_SCOPE_UNCONFIRMED'], anchor_day: null, mean_observed: null,
      close_volume_proxy: { valid_days: 100, mean_observed: '4242000.5', mean_complete: null, invalid_dates: [], reason: 'INCOMPLETE_WINDOW' }, raw_unit: 'SOURCE_QUOTE_CURRENCY_PER_TRADING_DAY',
      trade_scope_status: 'UNCONFIRMED', approximation: 'PROVIDER_ROUNDED_AGGREGATE_NOT_EXACT_TRADE_SUM' }),
  };
  const ms = Object.values(metrics);
  return { schema: K('technical-measures/1'), signal_day: signalDay, series_id: 'SYNTHETIC:SERIES:1', symbol, security_id: null, identity_status: 'SYNTHETIC',
    evidence: { identity_status: 'SYNTHETIC', currency: 'USD', trade_scope_status: 'UNCONFIRMED' }, settings_version: 'technical-leaderboard/2026-11-03.1', settings_sha256: 'b'.repeat(64),
    qgv_join_key: null, metrics, result_kind: 'SINGLE_COMPANY_MEASURES', evaluation_day: signalDay, data_asof: signalDay, status: 'NORMAL', source: 'KIS retained dailyprice MODP0',
    chart_basis: 'RAW', diagnostic_basis: 'RAW', collected_at: '2026-10-31T04:00:00Z', historical_available_at: null, pit_status: 'NOT_VERIFIED', publication_scope: 'OWNER_PRIVATE_ONLY',
    rank_count: 0, raw_count: ms.filter((m) => m.raw_value !== null).length, adopted_count: ms.filter((m) => m.value !== null).length, fixture_kind: 'SYNTHETIC_NOT_A_COMPANY' };
}
// Raw-only numbers of measures(): never on a page (the adopted 12.4242 may be, inside [data-ram-price] only).
const MEASURE_RAW = ['20.4242', '4242000.5'];
module.exports = { K, DAYS, bars, analysis, qgv, measures, MEASURE_RAW };
