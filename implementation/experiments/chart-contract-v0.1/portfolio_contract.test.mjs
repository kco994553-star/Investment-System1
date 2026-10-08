import test from 'node:test';
import assert from 'node:assert/strict';
import {aggregatePortfolio, renderPortfolioInput} from './portfolio_contract.mjs';
import {fictionalPortfolioFixture as fixture} from './portfolio_fixture.mjs';

test('industry buckets partition portfolio including cash and unknown', () => {
  const out = aggregatePortfolio(fixture());
  assert.deepEqual(out.industry.buckets, [
    {kind: 'INDUSTRY', label: 'Fictional equipment', units: 55},
    {kind: 'INDUSTRY', label: 'Fictional services', units: 25},
    {kind: 'UNKNOWN', label: 'Unknown industry', units: 10},
    {kind: 'CASH', label: 'Cash', units: 10},
  ]);
  assert.equal(out.industry.buckets.reduce((n, b) => n + b.units, 0), out.total_units);
});
test('type exposure remains on portfolio denominator despite membership sum above 100%', () => {
  const out = aggregatePortfolio(fixture());
  assert.deepEqual(out.types.exposures, [
    {type: 'Growth', member_units: 65, non_member_units: 15, unknown_units: 10, cash_units: 10},
    {type: 'Quality', member_units: 40, non_member_units: 40, unknown_units: 10, cash_units: 10},
  ]);
  assert.equal(out.types.denominator_units, 100);
  assert.equal(out.types.exposures.reduce((n, b) => n + b.member_units, 0), 105);
});
test('overlap exact membership sets separate no-types, unknown and cash', () => {
  const out = aggregatePortfolio(fixture());
  assert.deepEqual(out.overlap.buckets, [
    {kind: 'MEMBERSHIP', types: ['Growth', 'Quality'], units: 40},
    {kind: 'MEMBERSHIP', types: ['Growth'], units: 25},
    {kind: 'NO_TYPES', types: [], units: 15},
    {kind: 'UNKNOWN', types: [], units: 10},
    {kind: 'CASH', types: [], units: 10},
  ]);
  assert.equal(out.overlap.buckets.reduce((n, b) => n + b.units, 0), 100);
});
test('snapshot is not mutated and output cannot mutate input provenance or labels', () => {
  const f = fixture(), before = structuredClone(f), out = aggregatePortfolio(f);
  assert.deepEqual(f, before);
  assert.equal(Object.isFrozen(out.holdings[0].types), true);
  assert.throws(() => { out.holdings[0].types.push('Value'); }, TypeError);
  f.holdings[0].types.push('Untrusted');
  assert.deepEqual(out.holdings[0].types, ['Growth', 'Quality']);
});
test('reordering holdings and type memberships leaves chart aggregates unchanged', () => {
  const f = fixture(), expected = aggregatePortfolio(f);
  f.holdings.reverse(); f.holdings.forEach(h => h.types?.reverse()); f.type_catalog.reverse();
  const out = aggregatePortfolio(f);
  for (const key of ['industry', 'types', 'overlap']) assert.deepEqual(out[key], expected[key]);
});
test('reference preserves explicit target basis without inventing actual holdings or PIT', () => {
  const f = fixture(); f.data_kind = 'USER_SPEC_REFERENCE'; f.holdings.forEach(h => { h.types = null; });
  const out = renderPortfolioInput(f);
  assert.equal(out.data_state, 'REFERENCE'); assert.equal(out.weight_basis, 'TARGET');
  assert.equal(out.publication_grant, null); assert.equal(out.pit_status, 'NOT_VERIFIED');
  assert.equal(out.types.exposures[0].unknown_units, 90);
  assert.equal(out.holdings.every(h => h.security_id === null), true);
  f.weight_basis = 'ACTUAL'; assert.throws(() => aggregatePortfolio(f), /TARGET only/);
});
test('observed data is aggregated but withheld from renderer', () => {
  const f = fixture(); f.data_kind = 'OBSERVED_DATA'; f.weight_basis = 'ACTUAL';
  assert.equal(aggregatePortfolio(f).data_state, 'NOT_AVAILABLE');
  assert.throws(() => renderPortfolioInput(f), /withheld/);
});
test('missing basis, provenance, versions and explicit availability fail', () => {
  for (const key of ['weight_basis', 'source', 'snapshot_id', 'portfolio_version', 'qgv_version', 'data_kind', 'classification']) {
    const f = fixture(); delete f[key]; assert.throws(() => aggregatePortfolio(f));
  }
  for (const key of ['source', 'version', 'available_at']) {
    const f = fixture(); delete f.classification[key]; assert.throws(() => aggregatePortfolio(f));
  }
});
test('classification future availability rejected; supplied historical time preserved without PIT upgrade', () => {
  const f = fixture(); f.classification.available_at = '2026-10-01T00:00:00Z';
  assert.throws(() => aggregatePortfolio(f), /unavailable/);
  f.classification.available_at = '2026-09-29T00:00:00Z';
  const out = aggregatePortfolio(f);
  assert.equal(out.classification.available_at, f.classification.available_at);
  assert.equal(out.pit_status, 'NOT_VERIFIED');
});
test('invalid date, naive time and missing as_of rejected', () => {
  for (const as_of of ['2026-02-30T00:00:00Z', '2026-09-30', '2026-09-30T12:00:00', undefined]) {
    const f = fixture(); f.as_of = as_of; assert.throws(() => aggregatePortfolio(f));
  }
});
test('weights need exact conservation with no hidden tolerance', () => {
  const f = fixture(); f.holdings[0].weight_units -= 1;
  assert.throws(() => aggregatePortfolio(f), /exactly/);
  f.holdings[0].weight_units += 2;
  assert.throws(() => aggregatePortfolio(f), /exactly/);
});
test('fractional, negative, string, nonfinite and unsafe units rejected', () => {
  for (const units of [-1, 0.1, '40', NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    const f = fixture(); f.holdings[0].weight_units = units;
    assert.throws(() => aggregatePortfolio(f), /safe integer/);
  }
});
test('safe operands whose combined sum overflows are rejected', () => {
  const f = fixture(); f.total_units = Number.MAX_SAFE_INTEGER;
  f.holdings[0].weight_units = Number.MAX_SAFE_INTEGER;
  assert.throws(() => aggregatePortfolio(f), /overflow/);
});
test('empty portfolio can represent all cash but zero total is invalid', () => {
  const f = fixture(); f.holdings = []; f.cash_units = 100;
  const out = aggregatePortfolio(f);
  assert.equal(out.types.exposures[0].cash_units, 100);
  assert.equal(out.overlap.buckets.find(b => b.kind === 'CASH').units, 100);
  f.total_units = 0; f.cash_units = 0; assert.throws(() => aggregatePortfolio(f), /positive/);
});
test('duplicate identities rejected while unresolved securities remain explicit', () => {
  const f = fixture(); f.holdings[1].holding_id = f.holdings[0].holding_id;
  assert.throws(() => aggregatePortfolio(f), /duplicate holding_id/);
  const g = fixture(); g.holdings[0].security_id = g.holdings[1].security_id = 'supplied-security';
  assert.throws(() => aggregatePortfolio(g), /duplicate security_id/);
  const h = fixture(); delete h.holdings[0].security_id;
  assert.throws(() => aggregatePortfolio(h), /security_id/);
});
test('missing classification differs from explicit null and explicit empty types', () => {
  for (const key of ['industry', 'types']) {
    const f = fixture(); delete f.holdings[0][key]; assert.throws(() => aggregatePortfolio(f));
  }
  const f = fixture(); f.holdings[0].types = [];
  assert.equal(aggregatePortfolio(f).overlap.buckets.find(b => b.kind === 'NO_TYPES').units, 55);
  f.holdings[0].types = null;
  assert.equal(aggregatePortfolio(f).overlap.buckets.find(b => b.kind === 'UNKNOWN').units, 50);
});
test('unknown or repeated types rejected, including repeated catalog entries', () => {
  for (const types of [['Growth', 'Growth'], ['InferredValue']]) {
    const f = fixture(); f.holdings[0].types = types; assert.throws(() => aggregatePortfolio(f));
  }
  const f = fixture(); f.type_catalog.push('Growth'); assert.throws(() => aggregatePortfolio(f), /duplicate catalog/);
});
test('prototype-like industry/type labels remain ordinary data without key collision', () => {
  const f = fixture(); f.type_catalog.push('__proto__');
  f.holdings[0].industry = '__proto__'; f.holdings[0].types = ['__proto__'];
  const out = aggregatePortfolio(f);
  assert.equal(out.industry.buckets.find(b => b.label === '__proto__').units, 40);
  assert.equal(out.types.exposures.find(b => b.type === '__proto__').member_units, 40);
  assert.equal({}.polluted, undefined);
});
test('equivalent exact membership sets merge while industry unknown stays separate from label', () => {
  const f = fixture(); f.holdings[1].types = ['Quality', 'Growth'];
  f.holdings[1].industry = 'Unknown industry';
  const out = aggregatePortfolio(f);
  assert.equal(out.overlap.buckets.find(b => b.kind === 'MEMBERSHIP').units, 65);
  assert.equal(out.industry.buckets.find(b => b.kind === 'UNKNOWN').units, 10);
  assert.equal(out.industry.buckets.find(b => b.kind === 'INDUSTRY' && b.label === 'Unknown industry').units, 25);
});
