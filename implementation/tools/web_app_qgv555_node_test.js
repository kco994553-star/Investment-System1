'use strict';
// QGV 555 · 시총 Top500 · 사용자 설정 (web_app/qgv-555.js; owner 2026-11-14, DC-49) against Codex #537 a22ce2a4 research.qgv_555 /
// qgv_555_preview / top500_selection through Main's development engine route (tools/sector_qgv_engine_bridge.py as the real child process;
// SYNTHETIC inputs only): the context reads as the 15 official roles (5 per axis); the editor writes qgv-555-config/1 the engine
// accepts (a second metric splits the role, the role weight unchanged; alias / axis / accounting / preparing refusals; S1 edits
// only its SECTOR|TEMPLATE; restore = own candidate and version); a preview is the engine's before / after on the same input
// (population effect none, coverage stages, deciles D1–D10 counted from the engine's own decile, detail, family exposure); late,
// other-model and other-config answers are refused; the saved record replays to the same result hash; the Top500 selection's
// public view (no price, market cap or evidence) reads 「확정 아님」 without roster evidence; every population × model pair.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const Q = require('../src/investment_system/product/web_app/qgv-555.js');
const sha256 = async (b) => crypto.createHash('sha256').update(Buffer.from(b)).digest('hex');
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
      const det = await ask('qgv555_detail', { preview_id: res.preview_id, company_id: res.page.rows[0].company_id });
      assert.deepEqual(det.row.roles.q_moat_proxy.metrics.map((m) => m.metric), ['moat_proxy', 'roic']);
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
      const unassigned = Object.values(ctx.catalog).find((e) => e.axis === 'Q' && !e.roles.length && ctx.selectable.GENERAL.q_profitability.includes(e.canonical_id));
      assert.ok(unassigned, 'a metric without a default role is still selectable (Codex selectable_metrics)');
      assert.equal(Q.blocked(ctx, c, 'COMMON', 'q_profitability', unassigned.canonical_id), null);
    });

    await ok('exclude a role: active count Q4/G5/V5; the engine runs it and the coverage says 15 roles complete for nobody', async () => {
      const c = Q.excludeRole(Q.start(ctx, 'U1-555'), 'COMMON', 'q_capital_allocation');
      assert.equal(Q.activeCount(c, 'COMMON').text, 'Q4/G5/V5');
      const { res } = await preview(c); assert.equal(res.ok, true, res.code);
      assert.deepEqual(res.page.rows[0].after.active_roles, { Q: 4, G: 5, V: 5 });
      assert.equal(res.page.after_coverage.all15, 0);
      assert.equal(res.page.before_coverage.all15, res.page.before_coverage.denominator);
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

    await ok('preview: Codex preview() page — settings effect only, 20 + 1 rows, stages, role deciles, detail with three weights, family exposure', async () => {
      const c = Q.setAxis(Q.start(ctx, 'U1-555'), ctx, 'COMMON', 'V', 66);
      const { req, res } = await preview(c);
      assert.equal(Q.previewAnswer(req, res, req).state, 'SHOWN');
      const C = Q.compare(res.page); assert.equal(C.population, 'NOT_EVALUATED'); assert.equal(C.scope, 'SETTINGS_ONLY_FIXED_INPUT_AND_POPULATIONS');
      assert.equal(C.rows.length, 20); assert.equal(C.row_count, 21); assert.equal(res.page.next_offset, 20);
      assert.notEqual(C.versions.before, C.versions.after);
      const p2 = await ask('qgv555_page', { preview_id: res.preview_id, offset: 20 });
      assert.equal(Q.pageAnswer(res.page, p2).state, 'SHOWN'); assert.equal(p2.page.rows.length, 1); assert.equal(p2.page.next_offset, null);
      assert.equal(Q.pageAnswer({ source_preview_hash: 'x' }, p2).state, 'LATE_ANSWER');
      const st = Q.stages(C.coverage.after); assert.ok(st.find((x) => x.key === 'eligible_total')); assert.equal(st.find((x) => x.key === 'denominator').value, 21);
      const role = await ask('qgv555_role', { preview_id: res.preview_id, role: 'q_profitability' });
      assert.equal(role.after_result_hash, res.page.after_result_hash);
      const D = Q.deciles(role); assert.equal(D.bands.length, 10); assert.equal(D.bands.reduce((t, x) => t + x, 0) + D.other, 21);
      const det = await ask('qgv555_detail', { preview_id: res.preview_id, company_id: C.rows[0].company_id });
      const d = Q.detail(det.row, res.page.rows[0]); assert.equal(d.axes.length, 3); assert.equal(d.axes[0].roles.length, 5);
      const w = d.axes[0].roles[0].metrics[0].w; assert.ok(w && 'missing_redistributed_before_gate' in w && 'after_gate' in w, 'three weights from the engine');
      const fam = Q.families(ctx, c, 'COMMON', res.page.rows[0]); assert.ok(fam.length > 0 && fam.every((f) => f.nominal !== null));
      assert.equal((await ask('qgv555_detail', { preview_id: 'f'.repeat(64), company_id: 'SYN:000' })).code, 'PREVIEW_NOT_KEPT');
    });

    await ok('late, other-model and other-config answers are never shown; an engine refusal is a refusal', async () => {
      const c = Q.start(ctx, 'U1-555'), { req, res } = await preview(c);
      assert.equal(Q.previewAnswer(req, res, { ...req }).state, 'LATE_ANSWER');
      assert.equal(Q.previewAnswer(req, { ...res, request_id: 'other' }, req).state, 'LATE_ANSWER');
      assert.equal(Q.previewAnswer(req, { ...res, model_id: 'sector-555/0.1.0' }, req).state, 'MODEL_MISMATCH');
      assert.equal(Q.previewAnswer({ ...req, config: Q.setAxis(c, ctx, 'COMMON', 'Q', 1) }, res, null).state, 'LATE_ANSWER');
      const r2 = { ...req, config: Q.setAxis(c, ctx, 'COMMON', 'Q', 1) }; assert.equal(Q.previewAnswer(r2, { ...res, page: { ...res.page, request_id: r2.request_id } }, r2).state, 'CONFIG_MISMATCH');
      const dup = copy(c); dup.roles.q_profitability.metrics.EV_EBIT_TTM = 1; dup.roles.q_profitability.metrics.ebit_yield = 1;
      const bad = await preview(dup); assert.equal(bad.res.ok, false); assert.equal(Q.previewAnswer(bad.req, bad.res, bad.req).state, 'REFUSED');
      const other = await eng.call({ schema_version: REQ, op: 'qgv555_preview', request_id: 'N-x', model_id: 'unified-333-eps/0.1.0', config: c, before_config: c, input_id: 'SYNTHETIC_21' });
      assert.equal(other.ok, false); assert.equal(other.code, 'MODEL_UNKNOWN');
    });

    await ok('save and replay: the engine\'s record of the shown preview replays to the same result hash (Codex replay)', async () => {
      const c = Q.setRole(Q.start(ctx, 'U1-555'), 'COMMON', 'g_consistency', 5);
      const { res } = await preview(c); const sv = { saved: res.saved };
      assert.equal(Q.validateSaved(sv.saved).ok, true); assert.equal(sv.saved.result_hash, res.page.after_result_hash);
      const rp = await ask('qgv555_replay', { saved: sv.saved }); assert.equal(rp.ok, true); assert.equal(rp.reproduced, true);
      const t = copy(sv.saved); t.configuration.axis_weights.Q = 1; const rp2 = await ask('qgv555_replay', { saved: t });
      assert.ok(rp2.ok === false || rp2.reproduced === false, 'a changed record is not reproduced');
      assert.equal(Q.validateSaved({ ...sv.saved, rows: [] }).ok, false);
    });

    await ok('Top500 view: Codex top500_view() allowlist (no price, market cap or evidence); unproven roster = 확정 아님 with the reason', async () => {
      const a = await ask('qgv555_population', { input_id: 'SYNTHETIC_COMPLETE' }), b = await ask('qgv555_population', { input_id: 'SYNTHETIC_ROSTER_UNPROVEN' });
      assert.doesNotMatch(JSON.stringify([a, b]), /market_cap|price|shares|evidence/);
      const sa = Q.checkView(a.view), sb = Q.checkView(b.view);
      const va = Q.populationView('top500', sa, 'SYNTHETIC'), vb = Q.populationView('top500', sb, 'SYNTHETIC');
      assert.match(va.lines[0], /검증된 연구 후보 .* 공식 모집단 교체 아님/); assert.match(vb.lines[0], /자료가 있는 기업 중 상위 500\(전체시장 Top500 확정 아님\)/);
      assert.match(vb.lines[1], /후보 명부 완전성 근거 없음/); assert.match(va.lines.join('\n'), /QGV 순위가 아님/);
      assert.match(vb.lines.join('\n'), /분모 확정 전/); assert.match(va.lines.join('\n'), /공개 게시 권한 아님/);
      throws(() => Q.checkView({ ...a.view, market_cap_usd: '1' }), 'VIEW_KEY');
      const g = copy(a.view); g.members[3].selection_rank = g.members[2].selection_rank; throws(() => Q.checkView(g), 'RANK_INVALID');
      const dup = copy(a.view); dup.members[1].issuer_id = dup.members[0].issuer_id; throws(() => Q.checkView(dup), 'ISSUER_DUPLICATE');
      throws(() => Q.checkView({ ...a.view, public_publication_authorized: true }), 'VIEW_STATE');
      assert.equal(Q.populationView('top500', null).state, 'NOT_DELIVERED');
    });

    await ok('preview checks (§1, §6): the route\'s independent anchors, page continuity, saved record against the inputs', async () => {
      assert.ok(ctx.anchors.evaluation.input_hash && ctx.anchors.reference.input_hash);
      const c = Q.setAxis(Q.start(ctx, 'U1-555'), ctx, 'COMMON', 'G', 40);
      const { req, res } = await preview(c);
      assert.equal(Q.previewAnswer(req, res, req, ctx.anchors).state, 'SHOWN');
      const otherE = { ...ctx.anchors, evaluation: { ...ctx.anchors.evaluation, input_hash: 'f'.repeat(64) } };
      const otherR = { ...ctx.anchors, reference: { ...ctx.anchors.reference, members_hash: 'e'.repeat(64) } };
      assert.equal(Q.previewAnswer(req, res, req, otherE).state, 'INPUT_MISMATCH');
      assert.equal(Q.previewAnswer(req, res, req, otherR).state, 'INPUT_MISMATCH');
      const p2 = await ask('qgv555_page', { preview_id: res.preview_id, offset: 20 });
      assert.equal(Q.pageAnswer(res.page, p2, 20).state, 'SHOWN');
      assert.equal(Q.pageAnswer(res.page, p2, 19).state, 'PAGE_GAP', 'a page that does not start where the shown rows end');
      assert.equal(Q.pageAnswer(res.page, { ...p2, page: { ...p2.page, rows: [...p2.page.rows, ...p2.page.rows] } }, 20).state, 'PAGE_GAP', 'rows past the row count');
      assert.equal(Q.pageAnswer(res.page, { ...p2, page: { ...p2.page, row_count: 99 } }, 20).state, 'PAGE_GAP');
      assert.equal(Q.savedMatches(res.saved, ctx.anchors), true);
      assert.equal(Q.savedMatches(res.saved, otherE), false, 'a record of other inputs is not this input\'s record');
      assert.equal(res.before_source, 'RECOMPUTED');
      assert.equal(Q.previewAnswer(req, { ...res, before_source: 'SAVED_REPLAYED' }, req, ctx.anchors).code, 'BEFORE_SOURCE');
    });

    await ok('saved before (Codex #437 6871203367): the saved record is replayed and used only when its hash is the saved one', async () => {
      const c = Q.setAxis(Q.start(ctx, 'U1-555'), ctx, 'COMMON', 'V', 50);
      const first = (await preview(c)).res; assert.equal(first.ok, true, first.code);
      const sv = first.saved, d = Q.setAxis(c, ctx, 'COMMON', 'Q', 50);
      const req = { schema_version: REQ, op: 'qgv555_preview', request_id: 'N-' + (++seq), model_id: d.model_id, config: d, before_config: sv.configuration, input_id: 'SYNTHETIC_21', saved_before: sv };
      const res = await eng.call(req);
      assert.equal(res.ok, true, res.code); assert.equal(res.before_source, 'SAVED_REPLAYED');
      assert.equal(res.before_result_hash, sv.result_hash); assert.equal(res.page.before_result_hash, sv.result_hash);
      assert.equal(Q.previewAnswer(req, res, req, ctx.anchors).state, 'SHOWN');
      assert.equal(Q.previewAnswer(req, { ...res, before_source: 'RECOMPUTED' }, req, ctx.anchors).code, 'BEFORE_SOURCE');
      const forged = await eng.call({ ...req, request_id: 'N-' + (++seq), saved_before: { ...sv, result_hash: 'a'.repeat(64) } });
      assert.equal(forged.ok, false); assert.equal(forged.code, 'SAVED_NOT_REPRODUCED', 'a hash the replay does not give is never the before side');
      const other = await eng.call({ ...req, request_id: 'N-' + (++seq), before_config: ctx.configs['U1-555'] });
      assert.equal(other.ok, false); assert.equal(other.code, 'SAVED_ENGINE_OR_CONFIGURATION_MISMATCH');
      const bad = await eng.call({ ...req, request_id: 'N-' + (++seq), saved_before: { ...sv, rows: [] } });
      assert.equal(bad.code, 'SAVED_INVALID', 'a full result in the compact slot is refused');
    });

    await ok('roles=[] metric (§2): selectable, explicitly assigned to the chosen role; computable, accounting fit, no duplicate, role budget kept', async () => {
      const c = Q.start(ctx, 'U1-555');
      const m = Object.values(ctx.catalog).find((e) => e.axis === 'Q' && !e.roles.length && ctx.selectable.GENERAL.q_financial_safety.includes(e.canonical_id));
      assert.ok(m, 'an unassigned Q metric fits q_financial_safety');
      const k = Q.card(ctx, m.canonical_id, c, 'COMMON', 'q_financial_safety', null);
      assert.equal(k.selectable, true); assert.match(k.assignment, /기본 역할 없음 · 이 역할\(재무 안전성\)에 명시 배정/);
      const d = Q.addMetric(ctx, c, 'COMMON', 'q_financial_safety', m.canonical_id);
      assert.equal(d.roles.q_financial_safety.weight, c.roles.q_financial_safety.weight);
      assert.equal(Object.keys(d.roles.q_financial_safety.metrics).length, 3);
      throws(() => Q.addMetric(ctx, d, 'COMMON', 'q_financial_safety', m.canonical_id), 'ALIAS_DUPLICATE');
      throws(() => Q.addMetric(ctx, d, 'COMMON', 'g_revenue_growth', m.canonical_id), 'AXIS_MISMATCH');
      const { res } = await preview(d); assert.equal(res.ok, true, res.code);
      const det = await ask('qgv555_detail', { preview_id: res.preview_id, company_id: res.page.rows[0].company_id });
      assert.ok(det.row.roles.q_financial_safety.metrics.some((x) => x.metric === m.canonical_id), 'the engine computed it in the assigned role');
      const raw2 = copy(raw); raw2.catalog[m.canonical_id].implementation_status = 'PREPARING';
      throws(() => Q.addMetric(ctx2(raw2), Q.start(ctx2(raw2), 'U1-555'), 'COMMON', 'q_financial_safety', m.canonical_id), 'NOT_IMPLEMENTED');
      function ctx2(r) { return Q.checkContext(r); }
    });

    await ok('stored r2 reader (§3): staged synthetic delivery read whole; independent anchors, member bytes, model results; refusals', async () => {
      const dir = execFileSync('python3', [path.join(__dirname, 'qgv555_private_fixture.py'), '--out', fs.mkdtempSync(path.join(os.tmpdir(), 'q555-'))], { encoding: 'utf8' }).trim();
      const rd = (n) => { const bytes = fs.readFileSync(path.join(dir, n)); return { bytes: new Uint8Array(bytes), body: JSON.parse(bytes) }; };
      const stage = rd('stage.json').body, manifest = rd('manifest.json'), index = rd('index.json');
      const st = await Q.checkStored({ stage, manifest, index }, { scope: 'operating504', sha256 });
      assert.equal(st.scope, 'operating504');
      const b = Q.storedBoard(st, 'U1-555'); assert.match(b.lines[0], /보관 결과 .* 이 화면에서 재계산 아님/); assert.match(b.lines[2], /원입력에서 따로 계산한 기준과 같음/);
      const name = b.files[0].replace(/\.json$/, ''), det = await Q.checkStoredFile(st, name, rd(b.files[0]), sha256);
      const rows = Q.storedRows(det); assert.ok(rows.length > 0 && 'partial' in rows[0] && 'complete' in rows[0] && 'active' in rows[0]);
      const groups = Q.storedGroups(st, []); const D = Q.storedDeciles(groups, 'U1-555', 'q_profitability'); assert.equal(D.bands.length, 10); assert.ok(D.valid > 0);
      const bad = async (over, code) => { await assert.rejects(Q.checkStored({ stage, manifest, index, ...over }, { scope: 'operating504', sha256 }), (e) => String(e.message).split(':')[0] === code, code); };
      await bad({ stage: { ...stage, scope: 'held1057' } }, 'STAGE');
      await bad({ stage: { ...stage, manifest_sha256: 'f'.repeat(64) } }, 'MANIFEST_HASH');
      await bad({ stage: { ...stage, index_sha256: 'f'.repeat(64) } }, 'INDEX_HASH');
      await bad({ stage: { ...stage, expected_evaluation: { ...stage.expected_evaluation, input_hash: 'f'.repeat(64) } } }, 'EVALUATION_ANCHOR');
      await bad({ stage: { ...stage, expected_references: { ...stage.expected_references, 'S1-555': { ...stage.expected_references['S1-555'], input_hash: 'e'.repeat(64) } } } }, 'REFERENCE_ANCHOR');
      const tampered = rd(b.files[0]); tampered.bytes[10] ^= 1;
      await assert.rejects(Q.checkStoredFile(st, name, tampered, sha256), (e) => e.message === 'MEMBER_HASH');
      const s1 = Q.storedBoard(st, 'S1-555').files[0];
      await assert.rejects(Q.checkStoredFile({ ...st, files: { ...st.files, [name + '.json']: st.files[s1] } }, name, rd(s1), sha256), (e) => e.message === 'DETAIL_RESULT', 'an S1 detail under a U1 name');
      await assert.rejects(Q.checkStoredFile(st, 'U1-555-result', rd(b.files[0]), sha256), (e) => e.message === 'NOT_IN_MANIFEST');
      // SHARDED layout (the real r2 shape): the groups move to one group-index file; the count and duplicates are checked.
      const enc = (o) => new TextEncoder().encode(JSON.stringify(o));
      const part = { schema_version: 'qgv-555-groups-part/1', evaluation_input_hash: index.body.evaluation.input_hash, rows: index.body.groups };
      const idx2 = { ...index.body, groups: [], groups_layout: 'SHARDED', groups_count: index.body.groups.length, group_files: ['group-index-0000.json'] };
      const ib = enc(idx2), pb = enc(part);
      const man2 = { ...manifest.body, files: manifest.body.files.filter((f) => f.path !== 'index.json').concat([{ path: 'index.json', size: ib.length, sha256: await sha256(ib) }, { path: 'group-index-0000.json', size: pb.length, sha256: await sha256(pb) }]) };
      const mb = enc(man2), st2 = await Q.checkStored({ stage: { ...stage, manifest_sha256: await sha256(mb), index_sha256: await sha256(ib) }, manifest: { bytes: mb, body: man2 }, index: { bytes: ib, body: idx2 } }, { scope: 'operating504', sha256 });
      const gp = await Q.checkStoredFile(st2, 'group-index-0000', { bytes: pb, body: part }, sha256);
      assert.equal(Q.storedGroups(st2, [gp]).length, index.body.groups.length);
      throws(() => Q.storedGroups({ ...st2, index: { ...st2.index, groups_count: 1 } }, [gp]), 'GROUP_MEMBERS');
      throws(() => Q.storedGroups(st2, []), 'GROUP_FILES');
    });

    await ok('board state: every population × model pair says what it is; only 기존504 × 기존 공식 is SHOWN', async () => {
      for (const p of Object.keys(Q.POPULATIONS)) for (const m of Object.keys(Q.MODELS)) {
        const s = Q.boardState(p, m, { officialLoaded: true });
        assert.equal(s.state === 'SHOWN', p === 'universe504' && m === 'OFFICIAL', p + ' ' + m);
      }
      assert.match(Q.boardState('top500', 'U1-555').text, /실제 Top500 미선정 · 다른 모집단 결과를 이 이름으로 보이지 않음/);
      assert.equal(Q.boardState('universe504', 'U1-555').state, 'STORED_AVAILABLE'); assert.match(Q.boardState('expanded', 'S1-555').text, /보유 1057발행사 .* 이 화면에서 재계산 아님/);
      assert.match(Q.boardState('top500', 'OFFICIAL').text, /기존504에서만/);
    });

    await ok('pure module: no window / fetch / storage / percentile computing in the source', async () => {
      const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app', 'qgv-555.js'), 'utf8');
      for (const bad of ['localStorage', 'sessionStorage', 'indexedDB', 'fetch(', 'XMLHttpRequest', 'document.', 'percentile(', 'Math.random']) assert.ok(!src.includes(bad), bad);
    });
  } finally { await eng.close(); }
  console.log('PASS ' + n + ' qgv555');
})().catch((e) => { console.error(e); process.exit(1); });
