'use strict';
// QGV 555 · 시총 Top500 · 사용자 설정 (web_app/qgv-555.js; owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49) against
// the SYNTHETIC proposal files (docs/frontend_v2/qgv555-synthetic, written by tools/make_qgv555_synthetic.py): three populations
// apart, Top500 identity checks (issuer / security / rank / members hash / dates), its 「확정 아님」 wording without completeness
// evidence, five roles per axis, the editor (role budget split, alias duplicate, pending / not-fit with reason and alternatives,
// variant group, composite bounds, exclude → active count, restore = own base preset), no propagation between templates,
// nominal = setting product, input-family overlap shown without penalty, the board state of every population × model pair
// (no result under another name), and the preview: never a result while the 555 engine contract is pending, late / other-model refused.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Q = require('../src/investment_system/product/web_app/qgv-555.js');

const FIX = path.join(__dirname, '..', 'docs', 'frontend_v2', 'qgv555-synthetic');
const read = (f) => JSON.parse(fs.readFileSync(path.join(FIX, f), 'utf8'));
const CAT = read('catalog.json'), PRE = read('presets.json'), POP = read('population-top500.json');
const sha256 = async (bytes) => crypto.createHash('sha256').update(Buffer.from(bytes)).digest('hex');
const copy = (v) => JSON.parse(JSON.stringify(v));
let n = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };
const throws = (fn, code) => assert.throws(fn, (e) => e.message === code, code);

(async () => {
  const B = Q.checkBundle(CAT, PRE); assert.equal(B.ok, true, JSON.stringify(B)); const bundle = B.value, cat = bundle.catalog;
  const u1 = Q.presetFor(bundle, 'U1-555', 'COMMON'), bank = Q.presetFor(bundle, 'S1-555', 'FINANCIALS|BANK');

  await ok('three populations and four models stay separate identities; 555 ids differ from reduced and 333 ids', async () => {
    assert.deepEqual(Object.keys(Q.POPULATIONS), ['universe504', 'top500', 'expanded']);
    assert.deepEqual(Object.keys(Q.MODELS), ['OFFICIAL', 'U1-555', 'S1-555', 'MY']);
    const ids = Object.values(Q.MODELS).map((m) => m.model_id).filter(Boolean);
    for (const id of ids) { assert.match(id, /-555\//); assert.doesNotMatch(id, /333|reduced/); }
    assert.match(Q.POPULATIONS.universe504.text, /시총 순위로 고른 목록 아님/);
    assert.match(Q.POPULATIONS.expanded.text, /전체시장 아님/);
  });

  await ok('Top500 population: checked as written; without completeness evidence it is never called the Top500', async () => {
    const r = await Q.checkPopulation(POP, sha256); assert.equal(r.ok, true, JSON.stringify(r));
    const v = Q.populationView('top500', r.value); assert.equal(v.state, 'POOL_UNPROVEN');
    assert.match(v.lines[0], /자료가 있는 기업 중 상위 500\(전체시장 Top500 확정 아님\)/);
    assert.match(v.lines[1], /선정 기준일 2026-11-04 · 적용일 2026-11-05/);
    assert.match(v.lines.join('\n'), /QGV 순위가 아님/);
    assert.doesNotMatch(v.lines.join('\n'), /\$|USD|시가총액 [0-9]/);
    const full = copy(POP); full.candidate_pool_complete = true;
    const r2 = await Q.checkPopulation(full, sha256); assert.equal(Q.populationView('top500', r2.value).state, 'COMPLETE');
    assert.equal(Q.populationView('top500', null).state, 'NOT_DELIVERED');
  });

  await ok('Top500 refusals: duplicate issuer (share classes counted twice), duplicate security, rank gap, members hash, dates, unit, extra key', async () => {
    const cases = [
      ['ISSUER_DUPLICATE', (x) => { x.members[1].issuer_id = x.members[0].issuer_id; }],
      ['SECURITY_DUPLICATE', (x) => { x.members[1].representative_security_id = x.members[0].representative_security_id; }],
      ['RANK_GAP', (x) => { x.members[3].selection_rank = 5; }],
      ['MEMBERS_HASH_MISMATCH', (x) => { x.members[0].share_classes = 2; }],
      ['DATE_ORDER', (x) => { x.price_basis_date = '2026-11-06'; }],
      ['POPULATION_UNIT', (x) => { x.unit = 'SECURITY'; }],
      ['KEY_UNKNOWN', (x) => { x.price = 1; }],
      ['MEMBER_COUNT', (x) => { x.members.pop(); }],
    ];
    for (const [code, mut] of cases) { const x = copy(POP); mut(x); const r = await Q.checkPopulation(x, sha256); assert.equal(r.ok, false, code); assert.equal(r.code, code); }
  });

  await ok('catalog: exactly five roles per axis; a fourth role, an unknown role, an ambiguous alias are refused', async () => {
    for (const a of Q.AXES) assert.equal(cat.roles[a].length, 5);
    const c1 = copy(CAT); c1.roles.G.pop(); assert.equal(Q.checkBundle(c1, PRE).code, 'ROLES_NOT_FIVE');
    const c2 = copy(CAT); c2.factors[0].role_id = 'nope'; assert.equal(Q.checkBundle(c2, PRE).code, 'FACTOR_ROLE_UNKNOWN');
    const c3 = copy(CAT); c3.factors[1].aliases = [c3.factors[0].variant_id]; assert.equal(Q.checkBundle(c3, PRE).code, 'ALIAS_AMBIGUOUS');
    const p1 = copy(PRE); p1.presets[0].axis_weights.Q += 1; assert.equal(Q.checkBundle(CAT, p1).code, 'AXIS_SUM');
  });

  await ok('presets: U1 is COMMON, S1 one SECTOR|TEMPLATE each; editing one template never changes another (은행 → 보험·REIT never automatic)', async () => {
    assert.equal(u1.scope, 'COMMON'); assert.ok(bank);
    const s = Q.scopesOf(bundle, 'S1-555'); assert.ok(s.includes('FINANCIALS|INSURANCE') && s.includes('REAL_ESTATE|EQUITY_REIT'));
    const ins = Q.presetFor(bundle, 'S1-555', 'FINANCIALS|INSURANCE'), before = copy(ins);
    const edited = Q.setAxis(Q.setAxis(Q.start(bank), 'Q', 5000), 'G', 1700);
    assert.equal(edited.scope, 'FINANCIALS|BANK'); assert.deepEqual(ins, before, 'editing the bank setting leaves insurance as it was');
    assert.deepEqual(Q.presetFor(bundle, 'S1-555', 'FINANCIALS|INSURANCE'), before);
  });

  await ok('editor: a second factor in a role splits that role\'s budget, the role weight and other roles unchanged', async () => {
    const c = Q.start(u1), role = 'profitability', before = c.axes.Q[role].weight;
    const extra = cat.factors.find((f) => f.axis === 'Q' && f.role_id === role && Q.selectable(f, 'COMMON').ok && !(f.variant_id in c.axes.Q[role].factors));
    assert.ok(extra, 'synthetic catalog offers a second profitability factor');
    const d = Q.addFactor(c, cat, extra.variant_id);
    assert.equal(d.axes.Q[role].weight, before);
    assert.deepEqual(Object.values(d.axes.Q[role].factors), [5000, 5000]);
    assert.deepEqual(d.axes.Q.accounting_quality, c.axes.Q.accounting_quality);
    assert.deepEqual(Q.sums(d, cat).problems, []);
    const e = Q.removeFactor(d, 'Q', role, extra.variant_id); assert.deepEqual(e.axes.Q[role].factors, c.axes.Q[role].factors);
    assert.notEqual(c, d); assert.ok(Object.isFrozen(d));
  });

  await ok('editor refusals: alias double selection, pending definition, not fit (reason + alternatives), role mismatch', async () => {
    const c = Q.start(u1);
    const chosen = Object.keys(c.axes.Q.profitability.factors)[0];
    const alias = cat.factors.find((f) => f.variant_id !== chosen && f.alias_group === cat.factors.find((g) => g.variant_id === chosen).alias_group);
    if (alias) throws(() => Q.addFactor(c, cat, alias.variant_id), 'ALIAS_DUPLICATE');
    const twin = copy(CAT); const t = copy(twin.factors.find((f) => f.variant_id === chosen)); t.variant_id = chosen + '_twin'; t.aliases = []; twin.factors.push(t);
    throws(() => Q.addFactor(c, Q.checkBundle(twin, PRE).value.catalog, t.variant_id), 'ALIAS_DUPLICATE');
    const pend = cat.factors.find((f) => f.calculator_status === 'PENDING_DEFINITION'); assert.ok(pend);
    throws(() => Q.addFactor(c, cat, pend.variant_id), 'PENDING_DEFINITION');
    const b = Q.start(bank);
    const unfit = cat.factors.find((f) => f.calculator_status === 'IMPLEMENTED' && !f.scope.includes('BANK') && Q.alternatives(cat, f, 'FINANCIALS|BANK').length);
    assert.ok(unfit); throws(() => Q.addFactor(b, cat, unfit.variant_id), 'NOT_FIT');
    const k = Q.card(cat, unfit, b); assert.equal(k.selectable, false); assert.match(k.status, /부적합/); assert.ok(k.alternatives.length > 0);
    const other = cat.factors.find((f) => f.axis === 'Q' && f.role_id !== 'profitability' && Q.selectable(f, 'COMMON').ok);
    throws(() => Q.replaceFactor(c, cat, chosen, other.variant_id), 'FACTOR_ROLE_MISMATCH');
  });

  await ok('variants and composite: same variant group only; composite internal weight kept within its bounds', async () => {
    const vg = cat.factors.filter((f) => f.variant_group).reduce((m, f) => { (m[f.variant_group] = m[f.variant_group] || []).push(f); return m; }, {});
    const pair = Object.values(vg).find((fs2) => fs2.length > 1 && fs2.every((f) => Q.selectable(f, 'COMMON').ok));
    assert.ok(pair, 'synthetic catalog has a variant pair');
    let c = Q.start(u1); const [a, b] = pair;
    const sel = Object.keys(c.axes[a.axis][a.role_id].factors);
    if (!sel.includes(a.variant_id)) c = sel.length ? Q.replaceFactor(c, cat, sel[0], a.variant_id) : Q.addFactor(c, cat, a.variant_id);
    const d = Q.chooseVariant(c, cat, a.variant_id, b.variant_id);
    assert.ok(b.variant_id in d.axes[a.axis][a.role_id].factors && !(a.variant_id in d.axes[a.axis][a.role_id].factors));
    const notGroup = cat.factors.find((f) => f.axis === a.axis && f.role_id === a.role_id && f.variant_group !== a.variant_group && Q.selectable(f, 'COMMON').ok);
    if (notGroup) throws(() => Q.chooseVariant(c, cat, a.variant_id, notGroup.variant_id), 'VARIANT_GROUP_MISMATCH');
    const comp = cat.factors.find((f) => f.composite); let e = Q.start(u1);
    const cur = Object.keys(e.axes[comp.axis][comp.role_id].factors);
    e = cur.length ? Q.replaceFactor(e, cat, cur[0], comp.variant_id) : Q.addFactor(e, cat, comp.variant_id);
    const [p0] = comp.composite.components;
    const f = Q.setComposite(e, cat, comp.variant_id, p0.variant_id, p0.max_weight); assert.equal(f.composites[comp.variant_id][p0.variant_id], p0.max_weight);
    throws(() => Q.setComposite(e, cat, comp.variant_id, p0.variant_id, p0.max_weight + 1), 'COMPOSITE_BOUNDS');
    assert.ok(Q.card(cat, comp, e).composite.length === comp.composite.components.length);
  });

  await ok('exclude a role: active count drops (Q3/G4/V5 style), sums show the imbalance until the user rebalances', async () => {
    const c = Q.start(u1); const n0 = Q.activeCount(c);
    assert.match(n0.text, /^Q\d\/G\d\/V\d$/);
    const r = Object.keys(c.axes.V).find((k) => c.axes.V[k].weight > 0);
    const d = Q.excludeRole(c, 'V', r); assert.equal(Q.activeCount(d).V, n0.V - 1);
    assert.ok(Q.sums(d, cat).problems.some((p) => p.code === 'ROLE_SUM'));
    assert.deepEqual(d.axes.V[r].factors, c.axes.V[r].factors);
  });

  await ok('restore = the setting\'s own base preset id/version/scope; a newer preset of the same id does not replace it; no template propagation', async () => {
    const b = Q.start(bank); const edited = Q.setAxis(Q.setAxis(b, 'Q', 4400), 'G', 2300);
    const back = Q.restore(edited, bundle); assert.deepEqual(back, Q.start(bank));
    const newer = copy(PRE); const p2 = copy(bank); p2.version = '0.2.0'; p2.axis_weights = { Q: 5000, G: 2500, V: 2500 }; newer.presets.push(p2);
    const nb = Q.checkBundle(CAT, newer).value; assert.deepEqual(Q.restore(edited, nb).axis_weights, bank.axis_weights);
    assert.deepEqual(Q.start(Q.presetFor(bundle, 'S1-555', 'FINANCIALS|INSURANCE')).axis_weights, Q.presetFor(bundle, 'S1-555', 'FINANCIALS|INSURANCE').axis_weights);
    const gone = copy(PRE); gone.presets = gone.presets.filter((p) => p.scope !== 'FINANCIALS|BANK');
    throws(() => Q.restore(edited, Q.checkBundle(CAT, gone).value), 'BASE_PRESET_MISSING');
  });

  await ok('nominal = axis × role × share of the setting, exact; overlap by input family shown with summed exposure, never a penalty', async () => {
    const c = Q.start(u1); const w = Q.nominal(c);
    const total = w.reduce((t, x) => t + x.numerator, 0); assert.equal(total, w[0].denominator, 'the setting\'s nominal weights add up to the whole');
    const o = Q.overlap(c, cat); assert.ok(o.length > 0);
    for (const e of o) { assert.ok(e.factors.length > 1); assert.match(e.exposure, /%$/); }
    const card = Q.card(cat, cat.factors.find((f) => f.variant_id === o[0].factors[0]), c);
    assert.ok(card.overlap.length > 0); assert.match(card.weights, /설정값의 곱 · 실효 비중은 엔진 답/);
    assert.deepEqual(Q.nominal(c), w, 'overlap view does not change weights');
  });

  await ok('board state: every population × model pair says what it is; no result is shown under another model or population', async () => {
    for (const p of Object.keys(Q.POPULATIONS)) for (const m of Object.keys(Q.MODELS)) {
      const s = Q.boardState(p, m, { officialLoaded: true });
      if (p === 'universe504' && m === 'OFFICIAL') assert.equal(s.state, 'SHOWN'); else assert.notEqual(s.state, 'SHOWN', p + ' ' + m);
    }
    assert.match(Q.boardState('top500', 'OFFICIAL').text, /기존504에서만/);
    assert.match(Q.boardState('top500', 'U1-555').text, /모집단 계약 전/);
    assert.equal(Q.boardState('universe504', 'MY', { savedConfig: Q.start(u1) }).state, 'ENGINE_PENDING');
    assert.equal(Q.boardState('universe504', 'MY').state, 'NO_SAVED');
  });

  await ok('preview: the 555 engine contract is pending → no result; late answer and other-model answer refused', async () => {
    const req = { request_id: 'r1', model_id: 'unified-555/0.1.0' }, now = req;
    assert.equal(Q.previewAnswer(req, { request_id: 'r1', ok: false, code: 'ENGINE_CONTRACT_PENDING' }, now).state, 'ENGINE_CONTRACT_PENDING');
    assert.equal(Q.previewAnswer(req, { request_id: 'r0', ok: true, model_id: req.model_id }, now).state, 'LATE_ANSWER');
    assert.equal(Q.previewAnswer(req, { request_id: 'r1', ok: true, model_id: req.model_id }, { request_id: 'r2' }).state, 'LATE_ANSWER');
    assert.equal(Q.previewAnswer(req, { request_id: 'r1', ok: true, model_id: 'sector-555/0.1.0' }, now).state, 'MODEL_MISMATCH');
    assert.equal(Q.previewAnswer(req, null, now).state, 'ENGINE_NOT_CONNECTED');
    assert.match(Q.PREVIEW_STATE.ENGINE_CONTRACT_PENDING, /이전 결과를 이 설정 이름으로 보이지 않음/);
  });

  await ok('pure module: no window / fetch / storage / score computing words in the source', async () => {
    const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app', 'qgv-555.js'), 'utf8');
    for (const bad of ['localStorage', 'sessionStorage', 'indexedDB', 'fetch(', 'XMLHttpRequest', 'document.', 'percentile(', 'zscore']) assert.ok(!src.includes(bad), bad);
  });

  console.log('PASS ' + n + ' qgv555');
})().catch((e) => { console.error(e); process.exit(1); });
