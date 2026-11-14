'use strict';
// QGV 555 · 시총 Top500 · 사용자 설정 (web_app/qgv-555.js; owner 2026-11-14, DC-49) against Codex #537 research.qgv_555 /
// top500_selection through Main's development engine route (tools/sector_qgv_engine_bridge.py as the real child process;
// SYNTHETIC inputs only): the context reads as the 15 official roles (5 per axis); the editor writes qgv-555-config/1 the engine
// accepts (a second metric splits the role, the role weight unchanged; alias / axis / accounting / preparing refusals; S1 edits
// only its SECTOR|TEMPLATE; restore = own candidate and version); a preview is the engine's before / after on the same input
// (population effect none, coverage stages, deciles D1–D10 counted from the engine's own decile, detail, family exposure); late,
// other-model and other-config answers are refused; the saved record replays to the same result hash; the Top500 selection's
// public view (no price, market cap or evidence) reads 「확정 아님」 without roster evidence; every population × model pair.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Q = require('../src/investment_system/product/web_app/qgv-555.js');
const E = require('./web_app_sector_qgv_engine.js');

const REQ = 'sector-qgv-engine-request/1';
let n = 0, seq = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };
const throws = (fn, code) => assert.throws(fn, (e) => String(e.message).split(':')[0] === code, code);
const copy = (v) => JSON.parse(JSON.stringify(v));

(async () => {
  const eng = E.start({ env: {} });
  try {
    const ask = (op, fields = {}) => eng.call({ schema_version: REQ, op, request_id: 'N-' + (++seq), ...fields });
    const raw = await ask('qgv555_context'); assert.equal(raw.ok, true, JSON.stringify(raw).slice(0, 200));
    const ctx = Q.checkContext(raw);
    const preview = async (config, before) => { const req = { schema_version: REQ, op: 'qgv555_preview', request_id: 'N-' + (++seq), model_id: config.model_id, config, before_config: before || ctx.configs[config.candidate], input_id: 'SYNTHETIC_21' };
      const res = await eng.call(req); return { req, res }; };

    await ok('context: Codex catalog / configs read as five roles per axis = the official 15; recipes GENERAL complete, others preparing', async () => {
      for (const a of Q.AXES) assert.equal(ctx.roles[a].length, 5);
      assert.deepEqual(ctx.roles.Q, ['q_profitability', 'q_moat_proxy', 'q_earnings_quality', 'q_financial_safety', 'q_capital_allocation']);
      assert.equal(ctx.configs['U1-555'].model_id, 'unified-555/0.1.0'); assert.equal(ctx.configs['S1-555'].model_id, 'sector-555/0.1.0');
      assert.match(Q.recipeLine(ctx, 'FINANCIALS|BANK'), /은행 · 555 정의 준비 중 .* 일반기업 식으로 대체하지 않음/);
      const bad = copy(raw); delete bad.configs['U1-555'].roles.v_fcf_yield; throws(() => Q.checkContext(bad), 'ROLES_NOT_FIFTEEN');
      for (const id of Object.values(Q.MODELS).map((m) => m.model_id).filter(Boolean)) assert.doesNotMatch(id, /333|reduced|roa-core|sales-core/);
    });

    await ok('editor: a second metric splits the role budget, role weight unchanged; the engine accepts it and returns both metrics', async () => {
      const c = Q.start(ctx, 'U1-555');
      const d = Q.addMetric(ctx, c, 'COMMON', 'q_moat_proxy', 'roic');
      assert.equal(d.roles.q_moat_proxy.weight, c.roles.q_moat_proxy.weight);
      assert.deepEqual(d.roles.q_moat_proxy.metrics, { moat_proxy: 1, roic: 1 });
      const { res } = await preview(d); assert.equal(res.ok, true, res.code);
      assert.deepEqual(res.after.rows[0].roles.q_moat_proxy.metrics.map((m) => m.metric), ['moat_proxy', 'roic']);
      assert.ok(Object.isFrozen(d)); assert.notEqual(c, d);
    });

    await ok('editor refusals: alias in the same role, other axis, accounting not applicable, preparing recipe, last metric', async () => {
      const c = Q.start(ctx, 'U1-555');
      throws(() => Q.addMetric(ctx, c, 'COMMON', 'q_profitability', 'roic'), 'ALIAS_DUPLICATE');
      const alias = Object.values(ctx.catalog).find((e) => e.aliases.length);
      if (alias) { const role = Object.entries(c.roles).find(([, r]) => Object.keys(r.metrics).includes(alias.canonical_id)); if (role) throws(() => Q.addMetric(ctx, c, 'COMMON', role[0], alias.aliases[0]), 'ALIAS_DUPLICATE'); }
      throws(() => Q.addMetric(ctx, c, 'COMMON', 'q_profitability', 'revenue_cagr_3y'), 'AXIS_MISMATCH');
      const bankOnly = Object.values(ctx.catalog).find((e) => e.axis === 'Q' && !e.accounting_scope.includes('GENERAL'));
      if (bankOnly) throws(() => Q.addMetric(ctx, c, 'COMMON', 'q_profitability', bankOnly.canonical_id), 'ACCOUNTING_NOT_APPLICABLE');
      const s = Q.start(ctx, 'S1-555'); throws(() => Q.addMetric(ctx, s, 'FINANCIALS|BANK', 'q_profitability', 'sector::roe_common_ttm'), 'ACCOUNTING_RECIPE_PREPARING');
      throws(() => Q.removeMetric(c, 'COMMON', 'q_moat_proxy', 'moat_proxy'), 'ROLE_LAST_METRIC');
      const k = Q.card(ctx, 'revenue_cagr_3y', c, 'COMMON', 'q_profitability', null); assert.equal(k.selectable, false); assert.equal(k.why, 'AXIS_MISMATCH');
    });

    await ok('exclude a role: active count Q4/G5/V5; the engine runs it and the coverage says 15 roles complete for nobody', async () => {
      const c = Q.excludeRole(Q.start(ctx, 'U1-555'), 'COMMON', 'q_capital_allocation');
      assert.equal(Q.activeCount(c, 'COMMON').text, 'Q4/G5/V5');
      const { res } = await preview(c); assert.equal(res.ok, true, res.code);
      assert.deepEqual(res.after.rows[0].active_roles, { Q: 4, G: 5, V: 5 });
      assert.equal(res.after.coverage.all15, 0);
      assert.equal(res.before.coverage.all15, res.before.coverage.denominator);
    });

    await ok('S1: a role edit goes to its own SECTOR|TEMPLATE override, the sector axis to its sector only; nothing reaches another scope', async () => {
      const s = Q.start(ctx, 'S1-555'), it = 'INFORMATION_TECHNOLOGY|GENERAL', en = 'ENERGY|GENERAL';
      const d = Q.setAxis(Q.setRole(s, it, 'q_profitability', 40), ctx, it, 'Q', 50);
      assert.equal(Q.rolesOf(d, it).q_profitability.weight, 40); assert.equal(Q.rolesOf(d, en).q_profitability.weight, s.roles.q_profitability.weight);
      assert.equal(d.roles.q_profitability.weight, s.roles.q_profitability.weight);
      assert.equal(Q.axisOf(d, ctx, it).Q, 50); assert.deepEqual(Q.axisOf(d, ctx, en), Q.axisOf(s, ctx, en));
      assert.deepEqual(Object.keys(d.scoped_role_overrides), [it]);
      const { res } = await preview(d); assert.equal(res.ok, true, res.code);
      assert.deepEqual(Q.restoreScope(d, it).scoped_role_overrides, {});
    });

    await ok('restore = the setting\'s own candidate and version; another version is never substituted', async () => {
      const c = Q.setAxis(Q.start(ctx, 'U1-555'), ctx, 'COMMON', 'Q', 60);
      assert.deepEqual(Q.restore(ctx, c), Q.start(ctx, 'U1-555'));
      throws(() => Q.restore(ctx, { ...c, version: '0.0.9' }), 'BASE_VERSION_MISSING');
    });

    await ok('preview: same input → population effect none; before / after rows, versions, coverage stages, deciles from the engine', async () => {
      const c = Q.setAxis(Q.start(ctx, 'U1-555'), ctx, 'COMMON', 'V', 66);
      const { req, res } = await preview(c);
      assert.equal(Q.previewAnswer(req, res, req).state, 'SHOWN');
      const C = Q.compare(res); assert.equal(C.population, 'SAME'); assert.equal(C.rows.length, 21);
      assert.notEqual(C.versions.config_before, C.versions.config_after);
      const st = Q.stages(C.coverage.after); assert.ok(st.find((s) => s.key === 'eligible_total')); assert.equal(st.find((s) => s.key === 'denominator').value, 21);
      const D = Q.deciles(res.after, 'q_profitability'); assert.equal(D.bands.length, 10); assert.equal(D.bands.reduce((t, x) => t + x, 0) + D.other, 21);
      const d = Q.detail(res.after, res.after.rows[0].company_id); assert.equal(d.axes.length, 3); assert.equal(d.axes[0].roles.length, 5);
      assert.ok(d.axes[0].roles[0].metrics[0].lineage, 'lineage from the engine');
      const fam = Q.families(ctx, c, 'COMMON', res.after.rows[0]); assert.ok(fam.length > 0 && fam.every((f) => f.nominal !== null));
      assert.equal(res.after.rows[0].total !== null, true);
    });

    await ok('late, other-model and other-config answers are never shown; an engine refusal is a refusal', async () => {
      const c = Q.start(ctx, 'U1-555'), { req, res } = await preview(c);
      assert.equal(Q.previewAnswer(req, res, { ...req }).state, 'LATE_ANSWER');
      assert.equal(Q.previewAnswer(req, { ...res, request_id: 'other' }, req).state, 'LATE_ANSWER');
      assert.equal(Q.previewAnswer(req, { ...res, model_id: 'sector-555/0.1.0' }, req).state, 'MODEL_MISMATCH');
      assert.equal(Q.previewAnswer({ ...req, config: Q.setAxis(c, ctx, 'COMMON', 'Q', 1) }, res, null).state, 'LATE_ANSWER');
      const r2 = { ...req, config: Q.setAxis(c, ctx, 'COMMON', 'Q', 1) }; assert.equal(Q.previewAnswer(r2, res, r2).state, 'CONFIG_MISMATCH');
      const dup = copy(c); dup.roles.q_profitability.metrics.EV_EBIT_TTM = 1; dup.roles.q_profitability.metrics.ebit_yield = 1;
      const bad = await preview(dup); assert.equal(bad.res.ok, false); assert.equal(Q.previewAnswer(bad.req, bad.res, bad.req).state, 'REFUSED');
      const other = await eng.call({ schema_version: REQ, op: 'qgv555_preview', request_id: 'N-x', model_id: 'unified-333-eps/0.1.0', config: c, before_config: c, input_id: 'SYNTHETIC_21' });
      assert.equal(other.ok, false); assert.equal(other.code, 'MODEL_UNKNOWN');
    });

    await ok('save and replay: the engine\'s record of the shown preview replays to the same result hash (Codex replay)', async () => {
      const c = Q.setRole(Q.start(ctx, 'U1-555'), 'COMMON', 'g_consistency', 5);
      const { res } = await preview(c); const sv = { saved: res.saved };
      assert.equal(Q.validateSaved(sv.saved).ok, true); assert.equal(sv.saved.result_hash, res.after.result_hash);
      assert.deepEqual(Q.savedFrom(res.after), sv.saved);
      const rp = await ask('qgv555_replay', { saved: sv.saved }); assert.equal(rp.ok, true); assert.equal(rp.reproduced, true);
      const t = copy(sv.saved); t.configuration.axis_weights.Q = 1; const rp2 = await ask('qgv555_replay', { saved: t });
      assert.ok(rp2.ok === false || rp2.reproduced === false, 'a changed record is not reproduced');
      assert.equal(Q.validateSaved({ ...sv.saved, rows: [] }).ok, false);
    });

    await ok('Top500 selection: public view only (no price, market cap or evidence); unproven roster = 확정 아님 with the reason', async () => {
      const a = await ask('qgv555_population', { input_id: 'SYNTHETIC_COMPLETE' }), b = await ask('qgv555_population', { input_id: 'SYNTHETIC_ROSTER_UNPROVEN' });
      assert.doesNotMatch(JSON.stringify([a, b]), /market_cap|price|shares|evidence/);
      const sa = Q.checkSelection(a.selection), sb = Q.checkSelection(b.selection);
      const va = Q.populationView('top500', sa, 'SYNTHETIC'), vb = Q.populationView('top500', sb, 'SYNTHETIC');
      assert.match(va.lines[0], /검증된 연구 후보 .* 공식 모집단 교체 아님/); assert.match(vb.lines[0], /자료가 있는 기업 중 상위 500\(전체시장 Top500 확정 아님\)/);
      assert.match(vb.lines[1], /후보 명부 완전성 근거 없음/); assert.match(va.lines.join('\n'), /QGV 순위가 아님/);
      assert.match(vb.lines.join('\n'), /분모 확정 전/);
      throws(() => Q.checkSelection({ ...a.selection, market_cap_usd: '1' }), 'SELECTION_KEY');
      const g = copy(a.selection); g.members[3].selection_rank = 9; throws(() => Q.checkSelection(g), 'RANK_GAP');
      const dup = copy(a.selection); dup.members[1].issuer_id = dup.members[0].issuer_id; throws(() => Q.checkSelection(dup), 'ISSUER_DUPLICATE');
      assert.equal(Q.populationView('top500', null).state, 'NOT_DELIVERED');
    });

    await ok('board state: every population × model pair says what it is; only 기존504 × 기존 공식 is SHOWN', async () => {
      for (const p of Object.keys(Q.POPULATIONS)) for (const m of Object.keys(Q.MODELS)) {
        const s = Q.boardState(p, m, { officialLoaded: true });
        assert.equal(s.state === 'SHOWN', p === 'universe504' && m === 'OFFICIAL', p + ' ' + m);
      }
      assert.match(Q.boardState('top500', 'U1-555').text, /실제 Top500 미선정 · 다른 모형 결과를 이 이름으로 보이지 않음/);
      assert.match(Q.boardState('top500', 'OFFICIAL').text, /기존504에서만/);
    });

    await ok('pure module: no window / fetch / storage / percentile computing in the source', async () => {
      const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app', 'qgv-555.js'), 'utf8');
      for (const bad of ['localStorage', 'sessionStorage', 'indexedDB', 'fetch(', 'XMLHttpRequest', 'document.', 'percentile(', 'Math.random']) assert.ok(!src.includes(bad), bad);
    });
  } finally { await eng.close(); }
  console.log('PASS ' + n + ' qgv555');
})().catch((e) => { console.error(e); process.exit(1); });
