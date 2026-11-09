'use strict';
// Sector QGV screen side (web_app/sector-qgv.js) against Codex's common engine #505 through Main's engine route
// (tools/sector_qgv_engine_bridge.py, run here as the real child process; SYNTHETIC inputs only). Owner 2026-11-06 「섹터 QGV 실제
// 연결」: no second set of defaults, no score / gate / rank on the screen side, edits in the engine's own shape, a recalculation
// is an engine call, an answer of another request is refused. Owner 2026-11-07: the default flow is 10섹터 기본값 → 내 설정,
// 공격형·균형형·수비형 only as 이전 설정 호환, 기본값 복원 = the selected model's base preset id / version, no preset id rewritten.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const S = require('../src/investment_system/product/web_app/sector-qgv.js');
const E = require('./web_app_sector_qgv_engine.js');

const FIX = path.join(__dirname, '..', 'docs', 'research', 'sector_qgv');
const PRESETS = JSON.parse(fs.readFileSync(path.join(FIX, 'presets.json'), 'utf8'));
const W = path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app');
let n = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };
const copy = (v) => JSON.parse(JSON.stringify(v));

(async () => {
  const eng = E.start();
  try {
    const ask = async (op, fields, ctx = null) => { const req = S.request(op, fields), res = await eng.call(req), chk = S.check(op, req, res, ctx); return { req, res, chk }; };
    const { res: ctx, chk: c0 } = await ask('context');
    assert.equal(c0.ok, true, JSON.stringify(c0));
    const view = async (config, s, t) => { const r = await ask('view', { config, sector_id: s, accounting_template: t }, ctx); assert.equal(r.chk.ok, true, JSON.stringify(r.chk)); return r.res; };
    const IT = ['INFORMATION_TECHNOLOGY', 'GENERAL'];

    await ok('the defaults are the engine\'s: every scope\'s preset equals Codex presets.json, the screen file has none of its own', async () => {
      assert.equal(ctx.versions.model_version, 'sector-qgv-default/0.1.0'); assert.equal(ctx.default_config.gate_policy, 'official-q-percentile-required/1');
      assert.equal(PRESETS.length, ctx.sectors.length * ctx.templates.length);
      for (const p of PRESETS) { const v = await view(ctx.default_config, p.sector_id, p.accounting_template); assert.deepEqual(v.preset, p, p.sector_id + '|' + p.accounting_template); assert.deepEqual(v.default_preset, p); }
      const src = fs.readFileSync(path.join(W, 'sector-qgv.js'), 'utf8') + fs.readFileSync(path.join(W, 'screen-sector-qgv-live.js'), 'utf8');
      for (const id of ['ep_ttm_diluted', 'cfo_mcap', 'operating_margin_ttm', 'sector-qgv-default/0.1.0', 'GATE_PERCENTILE']) assert.doesNotMatch(src, new RegExp(id.replace(/[/.]/g, '\\$&')), 'no engine constant copied into the screen: ' + id);
      assert.doesNotMatch(src, /\bpercentile\(|midrank|\brank\s*=(?!=)|\.sort\([^)]*total/, 'no score, percentile or rank computed on the screen side');
      assert.doesNotMatch(src, /\bfetch\(|localStorage|sessionStorage|indexedDB/); assert.doesNotMatch(src, /\|\|\s*0\b|\?\?\s*0\b/);
    });

    await ok('factor list: design IDs and variants from the engine; badge facts told apart (기본값 · 추천 · 선택됨 · 준비 중 · 부적합 · 자료 일부 부족)', async () => {
      const v = await view(ctx.default_config, ...IT), by = new Map(v.factors.map((f) => [f.variant_id, f]));
      assert.equal(v.factors.length, 51); assert.equal(by.get('operating_margin_ttm').factor_id, 'Q01');
      const codes = (f, cov) => S.badges(f, cov).map((b) => b.code);
      assert.deepEqual(codes(by.get('ep_ttm_diluted')), ['BASE', 'RECOMMENDED', 'SELECTED']);
      assert.deepEqual(codes(by.get('fcff_ev')), ['PENDING']); assert.equal(S.selectable(by.get('fcff_ev')), 'PENDING');
      assert.deepEqual(codes(by.get('roe_common_ttm')), ['NOT_FIT'], 'a bank-only factor on a general template');
      const cov = { factors: { sales_mcap: { raw_valid: 18, denominator: 20 } } };
      assert.deepEqual(codes(by.get('sales_mcap'), cov), ['PARTIAL']); assert.equal(S.badges(by.get('sales_mcap'), cov)[0].text, '자료 일부 부족 18/20 · 선택 가능');
      assert.ok(['ep_ttm_diluted', 'ep_fy_diluted'].every((x) => S.search(v.factors, 'PER').some((f) => f.variant_id === x)), 'PER finds the E/P variants');
      assert.ok(S.search(v.factors, 'pbr').some((f) => f.variant_id === 'common_bp'));
      assert.ok(S.search(v.factors, 'PER_TTM_DILUTED').some((f) => f.variant_id === 'ep_ttm_diluted'), 'an alias finds its one canonical variant');
    });

    await ok('edits in the engine shape: a same-role addition splits that role\'s budget; remove / replace; pending and unfit refused', async () => {
      const v = await view(ctx.default_config, ...IT), by = new Map(v.factors.map((f) => [f.variant_id, f]));
      let p = S.addFactor(v.preset, by.get('ebitda_ev'));
      assert.deepEqual(p.axes.V.other_value, { weight: v.preset.axes.V.other_value.weight, factors: { sales_ev: 5000, ebitda_ev: 5000 } });
      assert.equal(S.sums(p).ok, true);
      p = S.addFactor(p, by.get('interest_coverage_ttm'));
      assert.deepEqual(p.axes.Q.interest_capacity, { weight: 0, factors: { interest_coverage_ttm: 10000 } }, 'a new role starts at 0: the user sets its budget');
      assert.throws(() => S.addFactor(p, by.get('ebitda_ev')), /DUPLICATE_VARIANT_ALIAS/);
      assert.throws(() => S.addFactor(p, by.get('fcff_ev')), /CALCULATOR_PENDING/);
      assert.throws(() => S.addFactor(p, by.get('roe_common_ttm')), /NOT_APPLICABLE/);
      p = S.removeFactor(p, 'V', 'other_value', 'ebitda_ev'); assert.deepEqual(p.axes.V.other_value.factors, { sales_ev: 10000 });
      p = S.replaceFactor(p, 'V', 'other_value', 'sales_ev', by.get('common_bp')); assert.deepEqual(p.axes.V.other_value.factors, { common_bp: 10000 });
      assert.throws(() => S.replaceFactor(p, 'V', 'earnings', 'ep_ttm_diluted', by.get('cfo_mcap')), /FACTOR_ROLE_MISMATCH/);
      p = S.removeFactor(p, 'Q', 'interest_capacity', 'interest_coverage_ttm'); assert.equal('interest_capacity' in p.axes.Q, false);
      p = S.removeFactor(p, 'G', 'profitability_change', 'roa_improvement_3y');
      assert.deepEqual(p.axes.G, { growth: { weight: 10000, factors: { revenue_cagr_3y: 10000 } } }, 'the removed role\'s budget goes to the others');
      assert.throws(() => S.removeFactor(p, 'G', 'growth', 'revenue_cagr_3y'), /LAST_FACTOR_OF_AXIS/);
      assert.equal(S.sums(S.setAxis(p, 'Q', 3001)).ok, false);
      const check = await view(S.withScope(ctx.default_config, p), ...IT); assert.equal(check.validation.valid, true, JSON.stringify(check.validation));
    });

    await ok('the engine is the validation authority: an alias twice, a pending factor with weight, bad sums are its codes', async () => {
      const v = await view(ctx.default_config, ...IT), bad = copy(v.preset);
      bad.axes.V.earnings.factors = { ep_ttm_diluted: 5000, PER_TTM_DILUTED: 5000 };
      assert.equal((await view(S.withScope(ctx.default_config, bad), ...IT)).validation.code, 'DUPLICATE_VARIANT_ALIAS');
      const pend = copy(v.preset); pend.axes.V.other_value.factors = { fcff_ev: 10000 };
      assert.equal((await view(S.withScope(ctx.default_config, pend), ...IT)).validation.code, 'CALCULATOR_PENDING:fcff_ev');
      assert.equal(S.errorText('CALCULATOR_PENDING:fcff_ev'), '계산 기능 준비 중인 요소에 비중이 있음 (fcff_ev)');
      assert.equal((await view(S.withScope(ctx.default_config, S.setAxis(v.preset, 'Q', 2999)), ...IT)).validation.code, 'WEIGHTS_MUST_SUM_10000');
    });

    await ok('scope: a bank edit stays in FINANCIALS|BANK (insurance, asset managers, REITs keep the engine default); 전체 적용 is an explicit copy that skips unfit scopes', async () => {
      const bank = await view(ctx.default_config, 'FINANCIALS', 'BANK');
      const cfg = S.withScope(ctx.default_config, S.setAxis(S.setAxis(bank.preset, 'Q', 5000), 'V', 3500));
      assert.deepEqual(Object.keys(cfg.scoped_overrides), ['FINANCIALS|BANK']);
      for (const t of ['INSURANCE', 'ASSET_MANAGER', 'EQUITY_REIT']) assert.deepEqual((await view(cfg, 'FINANCIALS', t)).preset, (await view(ctx.default_config, 'FINANCIALS', t)).preset, t);
      assert.equal((await view(cfg, 'FINANCIALS', 'BANK')).preset.axis_weights.Q, 5000);
      const it = await view(ctx.default_config, ...IT), scopes = ctx.sectors.flatMap((s) => ctx.templates.map((t) => ({ sector_id: s.sector_id, accounting_template: t })));
      const all = S.applyAll(ctx.default_config, it.preset, scopes, it.factors);
      assert.ok(all.skipped.includes('FINANCIALS|BANK') && all.skipped.includes('ENERGY|EQUITY_REIT'), 'operating margin / accruals do not apply to banks or REITs');
      assert.ok(all.applied.includes('ENERGY|GENERAL') && all.applied.includes('UTILITIES|ASSET_MANAGER'));
      assert.equal(all.applied.length + all.skipped.length, 70);
      assert.equal((await view(all.config, 'ENERGY', 'GENERAL')).validation.valid, true);
    });

    await ok('recalculation is an engine call: an edited config changes the engine\'s totals and ranks; comparison and save come from the engine', async () => {
      const it = await view(ctx.default_config, ...IT), cfg = S.withScope(ctx.default_config, { ...it.preset, axis_weights: { Q: 3400, G: 3300, V: 3300 } });
      const r = await ask('preview', { config: cfg, before_config: ctx.default_config, input_id: 'NORMAL' }, ctx);
      assert.equal(r.chk.ok, true, JSON.stringify(r.chk));
      assert.notEqual(r.res.after.config_hash, r.res.before.config_hash);
      assert.deepEqual(r.res.after.coverage.total, { valid: 20, denominator: 20 });
      assert.ok(r.res.comparison.rows.some((x) => x.delta !== 0), 'scores move'); assert.ok(r.res.comparison.rows.some((x) => x.before_common_rank !== x.after_common_rank), 'ranks move');
      assert.equal(S.validateSaved(r.res.saved).ok, true); assert.equal(r.res.saved.preview_id, r.res.after.preview_id);
      assert.deepEqual(eng.calls.filter((c) => c.op === 'preview').map((c) => c.input_id).slice(-1), ['NORMAL']);
    });

    await ok('gate: 관문 통과 / V 총점 반영 제외 / 판정 불가 are the engine\'s; 판정 불가 has no final score and no rank', async () => {
      const rows = {};
      for (const k of ['NORMAL', 'GATE_EXCLUDED', 'GATE_UNKNOWN']) { const r = await ask('preview', { config: ctx.default_config, before_config: ctx.default_config, input_id: k }, ctx); assert.equal(r.chk.ok, true); rows[k] = r.res.after.result_rows[0]; }
      assert.equal(S.text(S.GATE_TEXT, rows.NORMAL.gate_status), '관문 통과');
      assert.equal(S.text(S.GATE_TEXT, rows.GATE_EXCLUDED.gate_status), '관문: V 총점 반영 제외 · 남은 축 비례 재배분 · 기업 탈락·자료 미수집 아님'); assert.equal(rows.GATE_EXCLUDED.post_gate_axis_weights.V, 0);
      assert.equal(rows.GATE_UNKNOWN.total, null); assert.equal(rows.GATE_UNKNOWN.rank, null);
      assert.equal(S.text(S.STATUS_TEXT, rows.GATE_UNKNOWN.status), '관문 판정 불가 · 최종 점수·순위 없음');
    });

    await ok('states: partial, stale, mapping unknown, small peers, empty are the engine\'s statuses on the original denominator; a refused input is a code', async () => {
      const want = { PARTIAL: [0, 20, 'STRICT_INCOMPLETE'], STALE: [0, 20, 'STRICT_INCOMPLETE'], MAPPING_UNKNOWN: [0, 20, 'MAPPING_UNRESOLVED'], PEER_SAMPLE_SMALL: [0, 19, 'STRICT_INCOMPLETE'], EMPTY: [0, 0, null] };
      for (const [k, [valid, den, st]] of Object.entries(want)) {
        const r = await ask('preview', { config: ctx.default_config, before_config: ctx.default_config, input_id: k }, ctx); assert.equal(r.chk.ok, true, k);
        assert.deepEqual(r.res.after.coverage.total, { valid, denominator: den }, k); assert.equal(r.res.after.result_rows[0] ? r.res.after.result_rows[0].status : null, st, k);
      }
      const f = await ask('preview', { config: ctx.default_config, before_config: ctx.default_config, input_id: 'FAILED' }, ctx);
      assert.deepEqual(f.chk, { ok: false, code: 'DUPLICATE_COMPANY_ID' }); assert.equal(S.errorText('DUPLICATE_COMPANY_ID'), '입력 거부 · 회사 ID 중복');
    });

    await ok('answers of another request are refused: request id (both previews), op, engine versions, saved record, data kind', async () => {
      const r = await ask('preview', { config: ctx.default_config, before_config: ctx.default_config, input_id: 'NORMAL' }, ctx);
      const other = S.request('preview', { config: ctx.default_config, before_config: ctx.default_config, input_id: 'NORMAL' });
      assert.deepEqual(S.check('preview', other, r.res, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      assert.deepEqual(S.check('view', r.req, r.res, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      const moved = copy(r.res); moved.after.engine_version = 'sector-qgv-engine/9.9.9';
      assert.deepEqual(S.check('preview', r.req, moved, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      const cmp = copy(r.res); cmp.before.request_id = 'other:before'; assert.deepEqual(S.check('preview', r.req, cmp, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      const sv = copy(r.res); sv.saved.preview_id = '0'.repeat(64); assert.deepEqual(S.check('preview', r.req, sv, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      const kinds = copy(r.res); kinds.data_kind = 'PRIVATE'; assert.deepEqual(S.check('preview', r.req, kinds, ctx), { ok: false, code: 'ENGINE_ANSWER_INVALID' });
      assert.deepEqual(S.check('preview', r.req, { ...r.res, ok: false, code: 'ENGINE_FAILED' }, ctx), { ok: false, code: 'ENGINE_FAILED' });
    });

    await ok('saved record: the engine\'s save_user_config shape only; a changed config cannot reuse an old preview', async () => {
      const r = await ask('preview', { config: ctx.default_config, before_config: ctx.default_config, input_id: 'NORMAL' }, ctx), s = r.res.saved;
      assert.deepEqual(S.validateSaved(s), { ok: true });
      assert.equal(S.validateSaved({ ...s, extra: 1 }).code, 'SAVED_KEYS'); assert.equal(S.validateSaved({ ...s, preview_id: 'abc' }).code, 'SAVED_HASH');
      assert.equal(S.validateSaved({ ...s, config: { schema_version: 'x' } }).code, 'SAVED_CONFIG');
      const it = await view(ctx.default_config, ...IT), changed = S.withScope(ctx.default_config, S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400));
      const sv = await ask('save', { config: changed, preview_id: r.res.after.preview_id }, ctx);
      assert.deepEqual(sv.chk, { ok: false, code: 'PREVIEW_CONFIG_OR_REQUEST_MISMATCH' });
      assert.equal(S.errorText('PREVIEW_CONFIG_OR_REQUEST_MISMATCH'), '미리보기와 설정이 달라 저장 거부');
    });

    await ok('display preferences and owner scope do not change the engine\'s numbers (Lynch tags / names are presentation only)', async () => {
      const a = copy(ctx.default_config), b = { ...copy(ctx.default_config), owner_scope: 'PRIVATE', config_id: 'device', display_preferences: { lynch_tags: true, names: 'long' } };
      const ra = await ask('preview', { config: a, before_config: a, input_id: 'NORMAL' }, ctx), rb = await ask('preview', { config: b, before_config: b, input_id: 'NORMAL' }, ctx);
      assert.equal(ra.res.after.config_hash, rb.res.after.config_hash); assert.deepEqual(ra.res.after.result_rows, rb.res.after.result_rows);
    });

    // ---- owner 2026-11-07: default flow 10섹터 기본값 → 내 설정; 공격형·균형형·수비형 only as 이전 설정 호환; restore = base id / version.
    await ok('new default flow: 10섹터 기본값 → 내 설정; every scope starts from the engine\'s base preset id / version; the three old profiles are not a step', async () => {
      assert.deepEqual(S.FLOW, ['SECTOR_DEFAULT', 'MY_SETTING']); assert.deepEqual([S.FLOW_TEXT.SECTOR_DEFAULT, S.FLOW_TEXT.MY_SETTING, S.FLOW_TEXT.LEGACY], ['10섹터 기본값', '내 설정', '이전 설정 호환']);
      assert.equal(new Set(PRESETS.map((p) => p.sector_id)).size, 10, '10 sectors');
      for (const p of PRESETS) {
        const v = await view(ctx.default_config, p.sector_id, p.accounting_template);
        assert.deepEqual({ ...S.base(v, ctx.versions) }, { preset_id: p.preset_id, version: p.version, scope: p.sector_id + '|' + p.accounting_template });
        assert.equal(S.origin(ctx.default_config, p.sector_id, p.accounting_template), 'SECTOR_DEFAULT');
      }
      const it = await view(ctx.default_config, ...IT);
      assert.equal(S.origin(S.withScope(ctx.default_config, S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400)), ...IT), 'MY_SETTING');
      assert.equal(S.origin(S.withScope(ctx.default_config, it.preset), 'FINANCIALS', 'BANK'), 'SECTOR_DEFAULT', 'another scope stays on its default');
      assert.throws(() => S.base(it, { ...ctx.versions, model_version: 'sector-qgv-default/9.9.9' }), /BASE_PRESET_MISMATCH/, 'a base of another model is refused');
      assert.throws(() => S.base({ ...it, default_preset: { ...it.default_preset, version: '' } }, ctx.versions), /BASE_PRESET_MISMATCH/);
      const src = fs.readFileSync(path.join(W, 'sector-qgv.js'), 'utf8') + fs.readFileSync(path.join(W, 'screen-sector-qgv-live.js'), 'utf8');
      assert.doesNotMatch(src, /user-preset\/|aggressive|balanced|defensive|candidateFor|PRODUCT_PRESETS|saveWeights/, 'the old profiles are not offered or written by the sector screen');
    });

    await ok('restore = the selected model\'s base preset id / version: an edited scope comes back to the engine\'s default_preset, other scopes kept', async () => {
      const it = await view(ctx.default_config, ...IT), bank = await view(ctx.default_config, 'FINANCIALS', 'BANK');
      let cfg = S.withScope(ctx.default_config, S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400));
      cfg = S.withScope(cfg, S.setAxis(S.setAxis(bank.preset, 'Q', 5000), 'V', 3500));
      const edited = await view(cfg, ...IT); assert.notDeepEqual(edited.preset, edited.default_preset);
      const r = S.restore(cfg, edited, ctx.versions);
      assert.deepEqual({ ...r.base }, { preset_id: ctx.versions.model_version, version: edited.default_preset.version, scope: 'INFORMATION_TECHNOLOGY|GENERAL' });
      assert.deepEqual(Object.keys(r.config.scoped_overrides), ['FINANCIALS|BANK'], 'only this scope is restored');
      const back = await view(r.config, ...IT), want = PRESETS.find((p) => p.sector_id === IT[0] && p.accounting_template === IT[1]);
      assert.deepEqual(back.preset, back.default_preset); assert.deepEqual(back.preset, want, 'the base preset of presets.json');
      assert.ok(S.sameIdentity(back.preset, r.base));
      assert.equal((await view(r.config, 'FINANCIALS', 'BANK')).preset.axis_weights.Q, 5000, 'the bank edit is kept');
      assert.throws(() => S.restore(cfg, edited, { ...ctx.versions, model_version: 'other/1' }), /BASE_PRESET_MISMATCH/);
    });

    await ok('no preset id is rewritten: edits keep id / version / scope; after a saved user setting every base preset still equals presets.json; the old user-preset numbers are as they were', async () => {
      const it = await view(ctx.default_config, ...IT), by = new Map(it.factors.map((f) => [f.variant_id, f])), b = S.base(it, ctx.versions);
      let p = S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400); p = S.addFactor(p, by.get('ebitda_ev')); p = S.replaceFactor(p, 'V', 'other_value', 'sales_ev', by.get('common_bp'));
      assert.ok(S.sameIdentity(p, b), 'an edit changes weights only');
      for (const bad of [{ ...p, preset_id: 'sector-qgv-default/0.1.1' }, { ...p, version: '0.1.1' }, { ...p, sector_id: 'ENERGY' }]) assert.equal(S.sameIdentity(bad, b), false);
      assert.equal(S.withScope(ctx.default_config, p).base_preset_id, ctx.default_config.base_preset_id, 'the user setting names its base, it is not a new preset id');
      const cfg = S.withScope(ctx.default_config, p), pv = await ask('preview', { config: cfg, before_config: ctx.default_config, input_id: 'NORMAL' }, ctx);
      assert.equal(pv.chk.ok, true); const sv = await ask('save', { config: cfg, preview_id: pv.res.after.preview_id }, ctx); assert.equal(sv.chk.ok, true, JSON.stringify(sv.chk));
      for (const q of PRESETS) assert.deepEqual((await view(sv.res.saved.config, q.sector_id, q.accounting_template)).default_preset, q, 'base unchanged: ' + q.sector_id + '|' + q.accounting_template);
      assert.deepEqual(it.default_preset, PRESETS.find((q) => q.sector_id === IT[0] && q.accounting_template === IT[1]), 'the view answer was not changed by the edits');
      const V2 = require('../src/investment_system/product/web_assets/qgv-v2.js');
      assert.deepEqual(Object.fromEntries(Object.entries(V2.USER_PRESETS).map(([id, x]) => [id, [x.name, x.version, x.axis]])),
        { 'user-preset/aggressive@0.1': ['공격형', '0.1', { Q: 30, G: 50, V: 20 }], 'user-preset/balanced@0.1': ['균형형', '0.1', { Q: 40, G: 30, V: 30 }], 'user-preset/defensive@0.1': ['수비형', '0.1', { Q: 55, G: 15, V: 30 }] }, 'old ids keep their numbers');
    });

    await ok('legacy saved settings (old leaderboard weight trees) still load, read-only, labelled 이전 설정 호환', async () => {
      const P = require('../src/investment_system/product/web_assets/device-profiles.js');
      const doc = P.saveV2(P.emptyV2(), { name: '공격형 v0.1', weights: P.candidateFor('aggressive').weights }, new Date('2026-10-18T00:00:00Z'));
      const read = { state: 'OK', value: P.validateV2(JSON.parse(JSON.stringify(doc))) }, before = JSON.stringify(read);
      const lg = S.legacy(read);
      assert.equal(lg.state, 'OK'); assert.deepEqual(lg.profiles.map((x) => [x.name, x.version, x.label]), [['공격형 v0.1', 1, '이전 설정 호환']]);
      assert.equal(JSON.stringify(read), before, 'the stored trees are not changed');
      assert.deepEqual(S.legacy({ state: 'OK', value: P.emptyV2() }), { state: 'EMPTY', profiles: [] });
      assert.deepEqual(S.legacy({ state: 'INVALID', value: null }), { state: 'INVALID', profiles: [] });
      assert.deepEqual(S.legacy(null), { state: 'UNKNOWN', profiles: [] });
    });

    // ---- owner 2026-11-07: 2.2.7 섹터 QGV 설정(요소·가중치); 원본 참조 vs 내 설정; 최신 입력에 설정 적용 vs 과거 입력으로 결과 재현;
    // no auto-overwrite of a saved setting; fewer than 20 valid peers = 요소 점수 미산출 (its own state).
    const saveOf = async (cfg, input = 'NORMAL') => { const r = await ask('preview', { config: cfg, before_config: ctx.default_config, input_id: input }, ctx); assert.equal(r.chk.ok, true, JSON.stringify(r.chk)); assert.equal(S.validateSaved(r.res.saved).ok, true); return r.res; };

    await ok('2.2.7 is labelled 섹터 QGV 설정(요소·가중치) on the screen and in the docs', async () => {
      assert.deepEqual({ ...S.FEATURE }, { id: '2.2.7', name: '섹터 QGV 설정(요소·가중치)' });
      const live = fs.readFileSync(path.join(W, 'screen-sector-qgv-live.js'), 'utf8');
      assert.match(live, /sqFeature:S\.FEATURE\.id\}\},S\.FEATURE\.id,' ',S\.FEATURE\.name/); assert.equal((live.match(/feature\(\),/g) || []).length, 3, 'idle, loading and connected bodies');
      // the first-paint placeholder names the feature without its number (pending text carries no digit, web_app_qgv_browser_test)
      assert.match(fs.readFileSync(path.join(W, 'screen-qgv.js'), 'utf8'), /pending\('섹터 QGV 설정\(요소·가중치\) · 미리보기'\)/);
      const doc = fs.readFileSync(path.join(__dirname, '..', 'docs', 'frontend_v2', 'SECTOR_QGV_20261106.md'), 'utf8');
      const status = fs.readFileSync(path.join(__dirname, '..', '..', 'docs', 'SPEC', 'FUNCTION_STATUS.md'), 'utf8');
      for (const t of [doc, status]) { assert.match(t, /2\.2\.7 섹터 QGV 설정\(요소·가중치\)/); assert.doesNotMatch(t, /2\.2\.7 요소 사전/); }
    });

    await ok('원본 참조 (base preset id / version, never rewritten) vs 내 설정 (config id, schema, canonical hash, scopes); no invented version', async () => {
      const it = await view(ctx.default_config, ...IT), bank = await view(ctx.default_config, 'FINANCIALS', 'BANK');
      let cfg = S.withScope(ctx.default_config, S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400));
      cfg = S.withScope(cfg, S.setAxis(S.setAxis(bank.preset, 'Q', 5000), 'V', 3500));
      const res = await saveOf(cfg), id = S.identity(res.saved), b = S.base(it, ctx.versions);
      assert.equal(id.origin.base_preset_id, ctx.versions.model_version);
      assert.deepEqual(id.origin.presets.map((x) => ({ ...x })), [{ scope: 'FINANCIALS|BANK', preset_id: b.preset_id, version: b.version }, { scope: 'INFORMATION_TECHNOLOGY|GENERAL', preset_id: b.preset_id, version: b.version }], 'each override still names the base preset id / version');
      assert.deepEqual({ ...id.mine, scopes: [...id.mine.scopes] }, { config_id: 'device', schema_version: S.CONFIG, version: null, canonical_config_hash: res.saved.canonical_config_hash,
        preview_id: res.saved.preview_id, snapshot_id: res.saved.snapshot_id, scopes: ['FINANCIALS|BANK', 'INFORMATION_TECHNOLOGY|GENERAL'] });
      assert.equal(S.scopeText('FINANCIALS|BANK'), '금융·은행');
      const dflt = S.identity((await saveOf(ctx.default_config)).saved);
      assert.equal(dflt.mine.config_id, 'default'); assert.deepEqual([...dflt.mine.scopes], []); assert.notEqual(dflt.mine.canonical_config_hash, id.mine.canonical_config_hash, 'my setting has its own identity');
      assert.equal(dflt.origin.base_preset_id, id.origin.base_preset_id, 'the same original reference');
      for (const q of PRESETS.filter((x) => ['INFORMATION_TECHNOLOGY|GENERAL', 'FINANCIALS|BANK'].includes(x.sector_id + '|' + x.accounting_template)))
        assert.deepEqual((await view(res.saved.config, q.sector_id, q.accounting_template)).default_preset, q, 'the base preset is not rewritten');
      assert.equal(S.identity({ ...res.saved, config: { ...res.saved.config, config_version: '7' } }).mine.version, '7', 'a version is shown only if the record carries one');
    });

    await ok('최신 입력에 설정 적용 (preview: a new result) and 과거 입력으로 결과 재현 (replay: engine-confirmed identity) are distinct; refusals are codes', async () => {
      assert.deepEqual([...S.RUN], ['APPLY_LATEST', 'REPRODUCE']); assert.deepEqual({ ...S.RUN_TEXT }, { APPLY_LATEST: '최신 입력에 설정 적용', REPRODUCE: '과거 입력으로 결과 재현' });
      const it = await view(ctx.default_config, ...IT), cfg = S.withScope(ctx.default_config, S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400));
      const orig = await saveOf(cfg), saved = copy(orig.saved), bytes = JSON.stringify(saved);
      const rep = await ask('replay', { saved }, ctx);
      assert.deepEqual(rep.chk, { ok: true }); const st = S.replayState(rep.chk);
      assert.equal(st.state, 'REPRODUCED'); assert.match(st.text, /^과거 입력으로 결과 재현됨 · 엔진 확인/);
      assert.equal(rep.res.retained_preview_id, saved.preview_id); assert.notEqual(rep.res.preview.preview_id, saved.preview_id);
      assert.deepEqual(rep.res.preview.result_rows, orig.after.result_rows); assert.equal(rep.res.preview.input_hash, orig.after.input_hash);
      // apply to the latest input: the ordinary preview op on the input chosen now; a new preview, another input identity.
      const late = await ask('preview', { config: saved.config, before_config: ctx.default_config, input_id: 'GATE_EXCLUDED' }, ctx);
      assert.equal(late.chk.ok, true); assert.notEqual(late.res.after.preview_id, saved.preview_id); assert.notEqual(late.res.after.input_hash, orig.after.input_hash);
      assert.equal(late.res.after.config_hash, saved.canonical_config_hash, 'the same setting'); assert.notDeepEqual(late.res.after.result_rows, orig.after.result_rows, 'a new result');
      assert.equal(JSON.stringify(saved), bytes, 'neither run changes the saved record');
      // the replay answer must be this record's; a foreign answer is dropped.
      const other = S.request('replay', { saved });
      assert.deepEqual(S.check('replay', other, rep.res, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      const moved = copy(rep.res); moved.preview.config_hash = '0'.repeat(64); assert.deepEqual(S.check('replay', rep.req, moved, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      const same = copy(rep.res); same.preview.preview_id = saved.preview_id; assert.deepEqual(S.check('replay', rep.req, same, ctx), { ok: false, code: 'ANSWER_MISMATCH' });
      // refusals: the engine's code as text; a record the route does not hold = 재현 입력 연결 전; no replay route = 연결 전.
      const bad = await ask('replay', { saved: { ...saved, canonical_config_hash: 'f'.repeat(64) } }, ctx);
      assert.deepEqual(bad.chk, { ok: false, code: 'SAVED_PREVIEW_MISMATCH' });
      assert.deepEqual({ ...S.replayState(bad.chk) }, { state: 'REFUSED', code: 'SAVED_PREVIEW_MISMATCH', text: '재현 거부 · 저장 기록이 원래 미리보기와 다름 · 엔진 코드 SAVED_PREVIEW_MISMATCH' });
      const gone = await ask('replay', { saved: { ...saved, preview_id: 'a'.repeat(64) } }, ctx);
      const g = S.replayState(gone.chk); assert.equal(g.state, 'INPUT_MISSING'); assert.ok(g.text.startsWith('재현 입력(원래 preview·snapshot) 연결 전') && g.text.endsWith('(RETAINED_INPUT_NOT_FOUND)'));
      for (const code of ['OP_UNKNOWN', 'ENGINE_NOT_CONNECTED']) { const x = S.replayState({ ok: false, code }); assert.equal(x.state, 'NOT_CONNECTED'); assert.match(x.text, /^재현 입력\(원래 preview·snapshot\) 연결 전/); }
      assert.equal(S.replayState({ ok: false, code: 'REFERENCE_PREVIEW_IDENTITY_MISMATCH' }).text, '재현 거부 · 원래 입력·모형 식별자와 다름 · 엔진 코드 REFERENCE_PREVIEW_IDENTITY_MISMATCH');
      assert.notEqual(S.replayState(late.chk).state, undefined); assert.equal(S.replayState(late.chk).state, 'REPRODUCED', 'replayState is only ever given a replay answer: the screen keeps APPLY_LATEST apart');
      const live = fs.readFileSync(path.join(W, 'screen-sector-qgv-live.js'), 'utf8');
      assert.match(live, /kind==='REPRODUCE'\?'replay':'preview'/); assert.match(live, /sqRunState:'APPLIED_LATEST'/); assert.match(live, /sqRunState:'REPRODUCED'/);
    });

    await ok('no auto-overwrite: loading, a newer default and 기본값 복원 never change the stored record bytes', async () => {
      const it = await view(ctx.default_config, ...IT), cfg = S.withScope(ctx.default_config, S.setAxis(S.setAxis(it.preset, 'Q', 3100), 'V', 4400));
      const raw = JSON.stringify((await saveOf(cfg)).saved), read = Object.freeze({ state: 'OK', value: JSON.parse(raw) });
      const r = S.readSaved(read, ctx.versions); assert.equal(r.state, 'OK'); assert.equal(JSON.stringify(r.saved), raw, 'read as stored: no migration');
      const newer = S.readSaved(read, { ...ctx.versions, model_version: 'sector-qgv-default/0.2.0' });
      assert.equal(newer.state, 'BASE_DIFFERS'); assert.equal(JSON.stringify(newer.saved), raw, 'a newer engine default does not rewrite it');
      const edited = await view(r.saved.config, ...IT), back = S.restore(r.saved.config, edited, ctx.versions);
      assert.deepEqual(Object.keys(back.config.scoped_overrides), [], 'restore acts on the edited config of this scope');
      assert.equal(JSON.stringify(r.saved), raw); assert.equal(JSON.stringify(read.value), raw, 'the stored record is unchanged');
      assert.equal(S.validateSaved(JSON.parse(raw)).ok, true, 'an existing 6-key record keeps validating');
      assert.deepEqual(S.readSaved({ state: 'INVALID', value: null }, ctx.versions), { state: 'INVALID', saved: null }); assert.deepEqual(S.readSaved({ state: 'EMPTY', value: null }, ctx.versions), { state: 'EMPTY', saved: null });
      const live = fs.readFileSync(path.join(W, 'screen-sector-qgv-live.js'), 'utf8');
      assert.equal((live.match(/I\.store\.sectorQgv\.save\(/g) || []).length, 1, 'the one write is the 저장 click');
    });

    await ok('N<20: the engine\'s PEER_SAMPLE_SMALL is 요소 점수 미산출 · 유효 비교 기업 N<20 (N=19), apart from 관문 UNKNOWN, 결측 and 분류 미확인; no 0, no rank', async () => {
      const row = async (k) => (await saveOf(ctx.default_config, k)).after.result_rows[0];
      const small = await row('PEER_SAMPLE_SMALL');
      assert.equal(small.total, null); assert.equal(small.rank, null); assert.equal(small.axes.Q, null);
      assert.equal(small.factors.operating_margin_ttm.score, null); assert.equal(small.factors.operating_margin_ttm.score_status, 'PEER_SAMPLE_SMALL');
      const want = '요소 점수 미산출 · 유효 비교 기업 N<20 (N=19)';
      assert.deepEqual(S.rowState(small), { code: 'PEER_SAMPLE_SMALL', text: want }); assert.equal(S.factorText(small.factors.operating_margin_ttm), want);
      const others = { GATE_UNKNOWN: await row('GATE_UNKNOWN'), PARTIAL: await row('PARTIAL'), MAPPING_UNKNOWN: await row('MAPPING_UNKNOWN') };
      assert.deepEqual(Object.fromEntries(Object.entries(others).map(([k, r]) => [k, S.rowState(r).text])),
        { GATE_UNKNOWN: '관문 판정 불가 · 최종 점수·순위 없음', PARTIAL: '필수 요소 결측 · 총점 미산출', MAPPING_UNKNOWN: '섹터·회계모형 분류 미확정 · 점수 계산 안 함' });
      for (const r of Object.values(others)) assert.doesNotMatch(S.rowState(r).text, /N<20/);
      const mixed = copy(small); mixed.factors.debt_assets = { ...mixed.factors.debt_assets, score_status: 'MISSING_INPUT', valid_n: 0 };
      assert.deepEqual(S.rowState(mixed), { code: 'STRICT_INCOMPLETE', text: '필수 요소 결측 · 총점 미산출 · ' + want }, 'both told, neither hidden');
      const live = fs.readFileSync(path.join(W, 'screen-sector-qgv-live.js'), 'utf8');
      assert.match(live, /S\.rowState\(r\)/); assert.match(live, /S\.factorText\(/);
    });
  } finally { await eng.close(); }
  assert.deepEqual(eng.stderr, [], 'nothing on the bridge stderr');
  console.log('ok ' + n + ' checks');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
