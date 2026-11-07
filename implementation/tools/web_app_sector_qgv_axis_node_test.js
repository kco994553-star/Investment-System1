'use strict';
// Q/G 부분 비교 reader (web_app/sector-qgv-axis.js; owner 2026-11-07 「#505 실자료 부분 비교 계약 추가 인수」) on engine output only:
// Codex's synthetic D1 comparison (SHA-256 pinned as handed over on #437), Main's synthetic I1 comparison (Codex compare_axes,
// tools/sector_qgv_axis_main_variants.py) and the comparison the development bridge attaches to a real engine preview.
// Q / G are read apart and kept even when the total has no common value; D1 and I1 are never mixed; nothing is ranked or rescored.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const A = require('../src/investment_system/product/web_app/sector-qgv-axis.js');
const eng = require('./web_app_sector_qgv_engine');

const ROOT = path.join(__dirname, '..');
const D1F = path.join(ROOT, 'docs/research/sector_qgv/partial-synthetic-comparison.json');
const I1F = path.join(ROOT, 'tests/fixtures/sector_qgv_axis_i1_synthetic.json');
const read = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const edit = (base, fn) => { const c = JSON.parse(JSON.stringify(base)); fn(c); return c; };
let n = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };
const refused = (base, fn, code) => { const r = A.validate(edit(base, fn)); assert.equal(r.ok, false, code); assert.equal(r.code, code, JSON.stringify(r)); };

(async () => {
  await ok('Codex synthetic D1: pinned bytes; Q changed on all 20, G unchanged, V / total null; Q / G shown although the total common is 0', () => {
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(D1F)).digest('hex'), '18f3d0eff9d58bbb7127d3fbad2902a507b7f218f9c1c83e5c5a26b3c5a5d903');
    const r = A.validate(read(D1F)); assert.equal(r.ok, true, JSON.stringify(r));
    const v = A.view(r.value);
    assert.equal(v.treatment, 'SAME_INPUT_CONFIGURATION'); assert.deepEqual(v.identity_diff, ['config_hash', 'cache_key'], 'settings only');
    assert.deepEqual([v.axes.Q.COMMON_VALID, v.axes.Q.changed_common, v.axes.G.COMMON_VALID, v.axes.G.changed_common], [20, 20, 20, 0]);
    assert.deepEqual(v.vt, { V: { before: 0, after: 0 }, total: { before: 0, after: 0 }, total_common: 0 });
    assert.equal(A.filter(v, { axis: 'Q', show: 'CHANGED' }).length, 20, 'Q rows stay with no common total');
    assert.equal(A.filter(v, { axis: 'G', show: 'CHANGED' }).length, 0);
    assert.equal(A.filter(v).length, 20, 'the whole denominator');
    assert.ok(v.rows.every((x) => x.axes.Q.change_reason === 'FACTOR_ALLOCATION_CHANGED' && x.axes.G.change_reason === 'UNCHANGED'));
  });
  await ok('Main synthetic I1 (Codex compare_axes, input_treatment): same settings, input / snapshot versions differ, gained rows, reclassified row, peer rescoring', () => {
    const r = A.validate(read(I1F)); assert.equal(r.ok, true, JSON.stringify(r));
    const v = A.view(r.value);
    assert.equal(v.treatment, 'INPUT_CLASSIFICATION');
    assert.ok(!v.identity_diff.includes('config_hash') && v.identity_diff.includes('input_version') && v.identity_diff.includes('snapshot_id'));
    assert.equal(v.reclassified, 1); assert.equal(A.filter(v, { show: 'RECLASSIFIED' }).length, 1);
    assert.equal(A.filter(v, { axis: 'Q', show: 'GAINED' }).length, 20);
    assert.ok(A.TREATMENT_NOTE.INPUT_CLASSIFICATION.includes('기업 실적이 좋아지거나 나빠졌다는 뜻이 아님'));
    assert.ok(A.REASON_TEXT.PEER_RESCORING.includes('실적 변화 아님'));
  });
  await ok('the development bridge attaches Codex compare_axes to a real engine preview; the reader accepts it and its ids match the preview', async () => {
    const e = eng.start();
    try {
      const ctx = await e.call({ schema_version: 'sector-qgv-engine-request/1', op: 'context', request_id: 'c1' });
      const c = ctx.default_config, edited = JSON.parse(JSON.stringify(c));
      const view = await e.call({ schema_version: 'sector-qgv-engine-request/1', op: 'view', request_id: 'v1', config: c, sector_id: 'INFORMATION_TECHNOLOGY', accounting_template: 'GENERAL' });
      const p = JSON.parse(JSON.stringify(view.preset)); p.axis_weights = { Q: 3400, G: 3300, V: 3300 };
      edited.scoped_overrides = { 'INFORMATION_TECHNOLOGY|GENERAL': p };
      const res = await e.call({ schema_version: 'sector-qgv-engine-request/1', op: 'preview', request_id: 'p1', config: edited, before_config: c, input_id: 'NORMAL' });
      assert.equal(res.ok, true, res.code);
      const r = A.validate(res.axis); assert.equal(r.ok, true, JSON.stringify(r));
      assert.equal(r.value.comparison_id, 'p1'); assert.equal(r.value.before_identity.config_hash, res.before.config_hash); assert.equal(r.value.after_identity.config_hash, res.after.config_hash);
      assert.equal(r.value.denominator, res.after.result_rows.length);
      const files = await e.call({ schema_version: 'sector-qgv-engine-request/1', op: 'comparisons', request_id: 'l1' });
      assert.deepEqual(files.comparisons.map((x) => [x.name, x.data_kind]), [['PARTIAL_SYNTHETIC', 'SYNTHETIC'], ['MAIN_SYNTHETIC_I1', 'SYNTHETIC']], 'no private file without the process setting');
    } finally { await e.close(); }
  });
  await ok('refusals: D1 / I1 never mixed, counts equal the rows, null always with a reason, no rank / performance, exact keys', () => {
    const d1 = read(D1F), i1 = read(I1F);
    refused(d1, (c) => { c.after_identity.input_hash = 'x'; }, 'TREATMENT_MIXED');
    refused(d1, (c) => { c.rows[0].axes.Q.change_reason = 'PEER_RESCORING'; }, 'TREATMENT_MIXED');
    refused(d1, (c) => { c.rows[0].after_context = ['FINANCIALS', 'BANK']; }, 'TREATMENT_MIXED');
    refused(i1, (c) => { c.after_identity.config_hash = 'f'.repeat(64); }, 'TREATMENT_MIXED');
    refused(i1, (c) => { c.rows[0].axes.Q.change_reason = 'FACTOR_ALLOCATION_CHANGED'; }, 'TREATMENT_MIXED');
    refused(d1, (c) => { c.axes.Q.changed_common = 19; }, 'SUMMARY_MISMATCH');
    refused(d1, (c) => { c.rank = 1; }, 'RANK_NOT_NULL');
    refused(d1, (c) => { c.performance = { return: 0.1 }; }, 'PERFORMANCE_NOT_NULL');
    refused(d1, (c) => { c.rows[0].axes.Q.delta = null; }, 'DELTA_MISMATCH');
    refused(d1, (c) => { c.rows[0].axes.Q.common_valid = false; }, 'COMMON_MISMATCH');
    refused(d1, (c) => { c.rows[0].axes.Q.transition = 'GAINED'; }, 'TRANSITION_MISMATCH');
    refused(d1, (c) => { c.rows[0].axes.Q.before_reasons = ['MISSING_INPUT']; }, 'NULL_WITHOUT_REASON');
    refused(d1, (c) => { c.rows[0].axes.Q.after = 0; c.rows[0].axes.Q.before = null; }, 'COMMON_MISMATCH');
    refused(d1, (c) => { c.rows[0].rank = 1; }, 'KEY_UNKNOWN');
    refused(d1, (c) => { c.rows.pop(); }, 'DENOMINATOR');
    refused(d1, (c) => { c.rows[1].company_id = c.rows[0].company_id; }, 'DUPLICATE');
    refused(d1, (c) => { c.schema_version = 'sector-qgv-axis-comparison/2'; }, 'SCHEMA_VERSION');
    refused(d1, (c) => { c.rows[0].total.after = 'high'; }, 'NUMBER');
    assert.equal(A.validate(null).ok, false);
  });
  await ok('the reader and its screen make no rank, total, market rank or score of their own', () => {
    for (const f of ['sector-qgv-axis.js', 'screen-sector-qgv-axis-live.js']) {
      const src = fs.readFileSync(path.join(ROOT, 'src/investment_system/product/web_app', f), 'utf8');
      for (const bad of [/\.sort\(/, /\brank\s*[:=](?!=)\s*(?!null)/, /fetch\(|localStorage|sessionStorage|Date\.now\(/, /innerHTML/]) assert.ok(!bad.test(src), f + ' ' + bad);
    }
  });
  console.log('ok ' + n + ' checks');
})().catch((e) => { console.error(e); process.exitCode = 1; });
