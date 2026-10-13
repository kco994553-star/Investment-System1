'use strict';
// Signal playbook v1 engine: JS == Python reference vectors (synthetic), device config copy, doc-anchored code table.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const E = require(path.join(W, 'playbook-engine.js')), CFG = require(path.join(W, 'playbook-config-defaults.js'));
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/playbook_reference_v1.json'), 'utf8'));
const DOC = fs.readFileSync(path.join(__dirname, '../docs/playbook/PLAYBOOK_V1.md'), 'utf8');
function run(c) {
  const i = c.input;
  switch (c.operation) {
    case 'evaluate': return E.evaluate(CFG, i.situation, i.mode);
    case 'transition': return E.transition(CFG, i.from, i.choice, i.ctx);
    case 'criteria': return E.criteria(CFG, i.code, i.facts, i.ctx);
    case 'classify_types_v0': return E.classifyTypesV0(CFG, i.metrics);
    case 'sector_for': return E.sectorFor(CFG, i.symbol, i.etf);
    case 'e4_level': return E.e4Level(CFG, ...i.args);
    case 'portfolio_limits': return E.portfolioLimits(CFG, i.rows, i.cash_pct);
    default: throw new Error(c.operation);
  }
}
for (const c of vectors.cases) test('python reference vector ' + c.id, () => {
  assert.equal(c.synthetic, true); const before = JSON.stringify(c.input);
  assert.deepEqual(JSON.parse(JSON.stringify(run(c))), JSON.parse(c.expected_json)); assert.equal(JSON.stringify(c.input), before, 'input not mutated');
});
test('config copy is v0 · UNCALIBRATED and frozen', () => {
  assert.equal(CFG.config_version, 'playbook/v1'); assert.equal(CFG.status, 'v0'); assert.equal(CFG.calibration, 'UNCALIBRATED');
  assert.ok(Object.isFrozen(CFG.defaults.band_min_pp));
});
test('every §1 code row of the doc is in the config, in the same order, with the same reason codes', () => {
  const rows = [...DOC.matchAll(/^\|[^|]*\| ([XRTUEHW]\d) \| [^|]+ \| ([A-Z_/ ]+) \|$/gm)].map(m => [m[1], m[2].trim()]);
  assert.deepEqual(rows.map(r => r[0]), CFG.codes.map(c => c.code));
  for (const [code, reasons] of rows) {
    const cfg = CFG.codes.find(c => c.code === code), want = reasons.includes('/') && code === 'X1' ? ['PRICE_MISSING', 'FX_MISSING', 'SNAPSHOT_MISSING'] : reasons.split(' / ');
    assert.deepEqual(cfg.reason_codes, want, code);
  }
});
test('vectors cover every code, every §4 transition row and the five special rules', () => {
  const fired = new Set(), trans = new Set(), text = vectors.cases.map(c => c.expected_json).join('\n');
  for (const c of vectors.cases) {
    if (c.operation === 'evaluate') { const e = JSON.parse(c.expected_json); [e.primary, ...e.secondary].filter(Boolean).forEach(x => fired.add(x.code)); }
    if (c.operation === 'transition') trans.add(c.input.from + ':' + c.input.choice);
  }
  for (const c of CFG.codes) assert.ok(fired.has(c.code), 'code ' + c.code);
  for (const r of CFG.transitions) assert.ok(trans.has(r.from + ':' + r.choice), 'transition ' + r.from + ':' + r.choice);
  for (const id of ['CYCLICAL_PEAK_EARNINGS', 'VALUE_TRAP', 'THEME_CONCENTRATION', 'VALUE_TRAP_GATE', 'MACRO_CRISIS', 'MACRO_WARNING_CYCLICAL', 'FINANCIALS_QG_NOT_CONFIGURED']) assert.ok(text.includes('"' + id + '"'), id);
  assert.ok(text.includes('"점유율 하락 원인"')); assert.ok(text.includes('"DIVIDEND_CUT"'));
});
test('missing facts never fire a code and never count as zero', () => {
  const r = E.evaluate(CFG, {symbol: 'SYN', held: true, memberships: {}, data: {}, target_pct: null});
  assert.equal(r.primary, null); assert.ok(r.unknown.some(u => u.code === 'R2'));
  assert.equal(r.qg.qg_drop, null); assert.equal(r.v_change_20, null);
});
test('engine output never uses buy/sell verbs (§0-5)', () => {
  const text = JSON.stringify(CFG.codes.map(c => c.choices)) + JSON.stringify(CFG.conviction_choice);
  for (const w of ['매수', '매도', '주문']) assert.ok(!text.includes(w), w);
});

test('SIC invalid values fail unavailable and preserve ETF fallback',()=>{
 for(const sic of ['', 'NA',true,false,3559.9,Infinity,NaN,-1,10000,' 3559']){
  assert.equal(E.sicCandidate(CFG,sic),null);
  assert.deepEqual(E.sectorFor(CFG,'SYN','XLK',sic),{sector:'technology_hardware',source:'ETF_FALLBACK'});
 }
 assert.equal(E.sicCandidate(CFG,'3559'),'CYCLICAL');
});
