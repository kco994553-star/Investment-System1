'use strict';
// New frontend · feature 7 프롬프트 라이브러리 (web_app/screen-prompts-live.js, the part after the first paint; screen-prompts.js is its
// skeleton): the pure parts, against the old prompt library.
//  - pack(): equal to the Frozen catalog PLV1_CONTENT_V1.0 as the old research page embedded it (prompt_library/ui.py
//    catalog_payload; bodies verbatim; the field guide in Korean, one entry per variable); library() accepts it (70 prompts, 6
//    Starter, 10 Bundle) and refuses a broken copy as a whole (PROMPT_PACK_INVALID).
//  - check() = ui.py plvCheck (the old page's browser checker, run here from ui.JS) on every prompt: empty, filled, optional blank,
//    braces, bad / future dates, prior_cutoff, mode, positive integer, unknown and whitespace values; reasonKey covers every reason.
//  - filter() = the old list() rule (domain / role / scope / Starter / Bundle order / keyword over id, code, title, purpose,
//    keywords, aliases, tags), plus the old page's two views (research-bridge.js pl-view): copies (saved or being edited) and
//    ★ favorites.
//  - findPrivate (e-mail, phone, secret words, sheet links and long ids, amounts, account-like numbers, holding words; dates and
//    plain analysis text pass), resolveCompany / importState / fillCompany (research-bridge.js and app.js rules), todayKST.
// `node web_app_prompts_node_test.js --print` prints pack() for screen-prompts-live.js from the Python catalog (regeneration).
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const R = require('./web_app_reuse');

const PY_ENV = { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') };
const py = (code) => execFileSync('python3', ['-c', code], { env: PY_ENV, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
// The projection screen-prompts-live.js embeds: catalog_payload with the Korean field guide once per variable.
const PROJECT = `
import json
from investment_system.prompt_library.ui import catalog_payload, JS
from investment_system.prompt_library.catalog import load_catalog
p = catalog_payload(load_catalog())
guides = {}
for x in p['prompts']:
    for v in x['variables']:
        g = {k: v['guide'][k]['ko-KR'] for k in ('label', 'description', 'placeholder', 'source')}
        assert guides.setdefault(v['name'], g) == g
meta = {k: p[k] for k in ('content_version', 'schema_version', 'sha256', 'freeze_time', 'not_provided', 'starters', 'bundles')}
meta['guides'] = guides
keys = ('prompt_id', 'prompt_code', 'title', 'purpose', 'domain', 'role', 'category', 'subcategory', 'tags', 'keywords', 'aliases', 'scopes', 'system_overlap', 'body')
prompts = [dict({k: x[k] for k in keys}, variables=[{k: v[k] for k in ('name', 'required', 'kind', 'owner')} for v in x['variables']]) for x in p['prompts']]
print(json.dumps({'pack': {'meta': meta, 'prompts': prompts}, 'payload': p, 'js': JS}, ensure_ascii=False))
`;
const PY = JSON.parse(py(PROJECT));

if (process.argv.includes('--print')) {
  const d = PY.pack;
  process.stdout.write(['function pack(){return{meta:' + JSON.stringify(d.meta) + ',prompts:[', ...d.prompts.map((p) => JSON.stringify(p) + ','), ']};}'].join('\n') + '\n');
  process.exit(0);
}

const M = require(R.newPath('screen-prompts-live.js'));
const LIB = M.library();
const NOW = '2026-10-14T03:00:00Z';
// The old page's browser checker, run from the generated page script (ui.py JS) as the page ran it.
function oldChecker() {
  const ctx = { document: { getElementById: () => ({ textContent: JSON.stringify(PY.payload) }) }, module: { exports: {} } };
  vm.runInNewContext(PY.js, ctx, { filename: 'ui.py JS' });
  return ctx.module.exports.plvCheck;
}
const plain = (x) => JSON.parse(JSON.stringify(x));
const pick = (r) => ({ text: r.text, missing: [...r.missing], invalid: [...r.invalid], unknown: [...r.unknown], ready: r.ready });

test('pack() is the Frozen catalog as the old page embedded it; library() accepts it', () => {
  assert.deepStrictEqual(plain(M.pack()), PY.pack, 'screen-prompts-live.js pack() = catalog_payload (regenerate with --print)');
  assert.equal(LIB.ok, true);
  assert.equal(LIB.prompts.length, 70);
  assert.equal(LIB.meta.content_version, 'PLV1_CONTENT_V1.0');
  assert.equal(LIB.meta.sha256, 'f0a6ed9005e22b8fa534d51135cc3e734aa9577150438a35d65823a4c283e68e');
  assert.deepEqual([...LIB.starters], PY.payload.starters);
  assert.deepEqual(LIB.bundles.map((b) => [b.number, b.name, [...b.prompt_ids]]), PY.payload.bundles.map((b) => [b.number, b.name, b.prompt_ids]));
  for (const p of PY.payload.prompts) assert.equal(LIB.byId.get(p.prompt_id).body, p.body, p.prompt_id + ' body verbatim');
  assert.ok(Object.isFrozen(LIB.prompts[0]) && Object.isFrozen(LIB.prompts[0].variables[0]), 'deep-frozen');
  assert.equal(M.library(), LIB, 'parsed once');
});

test('library() refuses a broken pack as a whole', () => {
  const broken = [
    (d) => { d.prompts[0].domain = 'NEWS'; },
    (d) => { d.prompts[1].role = 'ANY'; },
    (d) => { d.prompts[2].body += ' {{undeclared}}'; },
    (d) => { delete d.meta.guides[d.prompts[0].variables[0].name]; },
    (d) => { d.prompts[3].prompt_id = d.prompts[4].prompt_id; },
    (d) => { d.meta.bundles[0].prompt_ids.push('plv1.none.999'); },
    (d) => { d.meta.starters.push('plv1.none.999'); },
    (d) => { d.prompts[5].variables[0].kind = 'NUMBER'; },
    (d) => { d.prompts[6].variables[0].owner = 'PORTFOLIO'; },
    (d) => { d.prompts[7].tags = 'tag'; },
    (d) => { d.prompts = []; },
    (d) => { delete d.meta.content_version; },
  ];
  for (const [i, edit] of broken.entries()) {
    const d = structuredClone(PY.pack); edit(d);
    assert.deepEqual({ ...M.library(() => d) }, { ok: false, code: 'PROMPT_PACK_INVALID' }, 'case ' + i);
  }
  assert.deepEqual({ ...M.library(() => { throw Error('x'); }) }, { ok: false, code: 'PROMPT_PACK_INVALID' });
  assert.equal(M.library(() => structuredClone(PY.pack)).ok, true, 'an intact copy passes');
});

test('check() = the old plvCheck on every prompt', () => {
  const old = oldChecker();
  const good = (v) => (v.kind === 'DATE' ? (v.name === 'prior_cutoff' ? '2026-09-01' : '2026-10-01') : v.kind === 'INPUT_MODE' ? 'STANDALONE'
    : v.kind === 'POSITIVE_INT' ? '5' : 'value of ' + v.name + '\nsecond line');
  let n = 0;
  for (const p of LIB.prompts) {
    const all = Object.fromEntries(p.variables.map((v) => [v.name, good(v)]));
    const text = p.variables.find((v) => v.kind === 'TEXT');
    const cases = [{}, all, { ...all, nope: '1' }, Object.fromEntries(p.variables.map((v) => [v.name, '   ']))];
    for (const v of p.variables) {
      cases.push({ ...all, [v.name]: '' }, { ...all, [v.name]: '  ' + good(v) + '  ' }, { ...all, [v.name]: 'a {{x}} b' }, { ...all, [v.name]: 'b }} a' });
      if (v.kind === 'DATE') cases.push(...['yesterday', '2026-10-01T10:00', '2026-10-01T10:00:00+09:00', '2026-10-01T00:00:00Z', '2099-01-01', '2026-13-01', '2026-10-14', '2026-10-15'].map((x) => ({ ...all, [v.name]: x })));
      if (v.kind === 'INPUT_MODE') cases.push(...['BOTH', 'system_context', 'SYSTEM_CONTEXT'].map((x) => ({ ...all, [v.name]: x })));
      if (v.kind === 'POSITIVE_INT') cases.push(...['0', '-3', '2.5', '007', '12'].map((x) => ({ ...all, [v.name]: x })));
    }
    if (p.variables.some((v) => v.name === 'prior_cutoff')) cases.push({ ...all, prior_cutoff: '2026-10-01' }, { ...all, prior_cutoff: '2026-10-02' }, { ...all, as_of: 'bad', prior_cutoff: '2026-09-01' });
    if (text) cases.push({ ...all, [text.name]: '$& $1 {{' });
    for (const c of cases) {
      assert.deepStrictEqual(pick(M.check(p, c, { nowIso: NOW, notProvided: LIB.meta.not_provided })), plain(old(p.prompt_id ? PY.payload.prompts.find((x) => x.prompt_id === p.prompt_id) : p, c, NOW)), p.prompt_id + ' ' + JSON.stringify(c).slice(0, 120));
      n++;
    }
  }
  assert.ok(n > 2000, 'cases: ' + n);
  // The one optional variable becomes NOT_PROVIDED; a ready result has no placeholder left.
  const fund = LIB.byId.get('plv1.fund.030');
  const r = M.check(fund, { company: 'A', ticker: 'B', as_of: '2026-10-01' }, { nowIso: NOW });
  assert.equal(r.ready, true);
  assert.match(r.text, /`NOT_PROVIDED`/);
  assert.doesNotMatch(r.text, /\{\{/);
});

test('reasonKey maps every reason check() gives to its field words', () => {
  const reasons = ['as_of: placeholder braces are not allowed in values', 'as_of: not an ISO date (YYYY-MM-DD) or offset-aware ISO datetime',
    'as_of: information cutoff lies in the future', 'prior_cutoff: must be strictly before as_of', 'candidate_count: not a positive integer',
    'input_mode: not in SYSTEM_CONTEXT/STANDALONE', 'x: anything else'];
  assert.deepEqual(reasons.map(M.reasonKey), ['braces', 'date', 'future', 'prior', 'positive', 'mode', 'invalid']);
  for (const k of ['braces', 'date', 'future', 'prior', 'positive', 'mode', 'invalid', 'missing']) assert.ok(M.WORDS[k], k);
});

test('filter() = the old list() rule', () => {
  const ids = (list) => list.map((p) => p.prompt_id);
  const all = PY.payload.prompts;
  assert.deepEqual(ids(M.filter(LIB, {})), all.map((p) => p.prompt_id), 'catalog order, no ranking');
  for (const [d] of M.DOMAINS) assert.deepEqual(ids(M.filter(LIB, { domain: d })), all.filter((p) => p.domain === d).map((p) => p.prompt_id), d);
  for (const [r] of M.ROLES) assert.deepEqual(ids(M.filter(LIB, { role: r })), all.filter((p) => p.role === r).map((p) => p.prompt_id), r);
  for (const [s] of M.SCOPES) assert.deepEqual(ids(M.filter(LIB, { scope: s })), all.filter((p) => p.scopes.includes(s)).map((p) => p.prompt_id), s);
  assert.deepEqual(ids(M.filter(LIB, { starter: true })), all.filter((p) => PY.payload.starters.includes(p.prompt_id)).map((p) => p.prompt_id));
  for (const b of PY.payload.bundles) assert.deepEqual(ids(M.filter(LIB, { bundle: String(b.number) })), b.prompt_ids, 'Bundle ' + b.number + ' keeps its own order');
  const hay = (p) => [p.prompt_id, p.prompt_code, p.title, p.purpose, ...p.keywords, ...p.aliases, ...p.tags].join('\n').toLowerCase();
  for (const kw of ['margin', 'MARGIN delta', '  경쟁  ', 'plv1.fund.030', 'xyz-nothing']) {
    const words = kw.trim().toLowerCase().split(/\s+/).filter(Boolean);
    assert.deepEqual(ids(M.filter(LIB, { kw })), all.filter((p) => words.every((w) => hay(p).includes(w))).map((p) => p.prompt_id), kw);
  }
  assert.deepEqual(ids(M.filter(LIB, { domain: 'MACRO', role: 'BLIND-SPOT', scope: 'MARKET' })), all.filter((p) => p.domain === 'MACRO' && p.role === 'BLIND-SPOT' && p.scopes.includes('MARKET')).map((p) => p.prompt_id));
  assert.deepEqual(ids(M.filter(LIB, { mine: true, drafts: {} })), []);
  assert.deepEqual(ids(M.filter(LIB, { mine: true, drafts: { 'plv1.fund.030': 'x' } })), ['plv1.fund.030']);
  // ★ view (research-bridge.js 즐겨찾기만): catalog order kept, unknown ids never listed, combined with the other filters.
  assert.deepEqual(ids(M.filter(LIB, { fav: true, favs: [] })), []);
  assert.deepEqual(ids(M.filter(LIB, { fav: true })), [], 'no favorites list: nothing');
  assert.deepEqual(ids(M.filter(LIB, { fav: true, favs: ['plv1.macro.001', 'plv1.fund.030', 'plv1.none.999'] })), all.filter((p) => ['plv1.fund.030', 'plv1.macro.001'].includes(p.prompt_id)).map((p) => p.prompt_id));
  assert.deepEqual(ids(M.filter(LIB, { fav: true, favs: ['plv1.macro.001', 'plv1.fund.030'], domain: 'MACRO' })), ['plv1.macro.001']);
  assert.deepEqual(ids(M.filter(LIB, { fav: false, favs: ['plv1.fund.030'] })), all.map((p) => p.prompt_id), 'fav off: every prompt');
});

test('findPrivate: private-looking text asks for a look; dates, names and analysis text pass', () => {
  const kinds = (t) => M.findPrivate([{ label: 'L', text: t }]).map((f) => f.kind);
  for (const [t, k] of [['me' + '@' + 'example.com', 'EMAIL'], ['010-1234-5678', 'PHONE'], ['+82 10 1234 5678', 'PHONE'], ['my api key is x', 'SECRET'], ['password: hunter2', 'SECRET'],
    ['비밀번호 1234', 'SECRET'], ['https://docs.google.com/spreadsheets/d/abc', 'SHEET'], ['1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-xyz', 'SHEET'], ['$1,200', 'MONEY'],
    ['3,000만 원', 'MONEY'], ['500달러', 'MONEY'], ['USD 300', 'MONEY'], ['123-456789-0123', 'ACCOUNT'], ['내 보유 종목', 'HOLDING'], ['평단 52', 'HOLDING'], ['잔고 확인', 'HOLDING']])
    assert.ok(kinds(t).includes(k), t + ' -> ' + k + ' (got ' + kinds(t) + ')');
  for (const t of ['2026-10-14', '2026-10-01T10:00:00+09:00', 'Synthetic Fixture Corp', 'SYN', 'NYSE:SYN', '미국 대형 기술주 · 최근 1년', 'STANDALONE', '5', '', '   ',
    'Q2 실적 이후 Margin 변화와 경쟁 구도를 본다'])
    assert.deepEqual(kinds(t), [], JSON.stringify(t));
  const found = M.findPrivate([{ label: '회사', text: 'a' + '@' + 'b.co' }, { label: '메모', text: '평단 10' }, { label: '빈 칸', text: '' }]);
  assert.deepEqual(found.map((f) => [f.label, f.kind]), [['회사', 'EMAIL'], ['메모', 'HOLDING']]);
  assert.ok(found.every((f) => typeof f.what === 'string' && f.what));
});

test('selected company: resolve from the public names table, import states, fill as one pair', () => {
  const recs = { 'NYSE:SYN': { ticker: 'SYN', en_name: 'Synthetic Fixture Corp' }, 'NYSE:NONAME': { ticker: 'NONAME', en_name: null }, 'NYSE:ODD': { ticker: 'OTHER', en_name: 'Odd' },
    target_co: { ticker: 'TGT', en_name: 'Target Co' }, 'NYSE:LONG': { ticker: 'LONG', en_name: 'two\nlines' } };
  const names = { get: (id) => recs[id] || null };
  assert.deepEqual({ ...M.resolveCompany('NYSE:SYN', names) }, { id: 'NYSE:SYN', ticker: 'SYN', name: 'Synthetic Fixture Corp' });
  assert.deepEqual({ ...M.resolveCompany('target_co', names) }, { id: 'target_co', ticker: 'TGT', name: 'Target Co' });
  assert.deepEqual({ ...M.resolveCompany('NYSE:NONAME', names) }, { id: 'NYSE:NONAME', ticker: 'NONAME', name: null });
  assert.equal(M.resolveCompany('NYSE:LONG', names).name, null, 'a name with a line break is not used');
  for (const id of ['NYSE:ODD', 'NYSE:NONE', 'bad id', '', null]) assert.equal(M.resolveCompany(id, names), null, String(id));
  assert.equal(M.resolveCompany('NYSE:SYN', null), null);
  const fund = LIB.byId.get('plv1.fund.030'), macro = LIB.byId.get('plv1.macro.001');
  const syn = M.resolveCompany('NYSE:SYN', names), noname = M.resolveCompany('NYSE:NONAME', names);
  assert.equal(M.importState(macro, syn, {}, 'READY'), 'NOT_APPLICABLE');
  assert.deepEqual(['NONE', 'LOADING', 'FAILED'].map((ph) => M.importState(fund, syn, {}, ph)), ['MISSING', 'LOADING', 'FAILED']);
  assert.equal(M.importState(fund, null, {}, 'READY'), 'UNRESOLVED');
  assert.equal(M.importState(fund, syn, { company: 'x' }, 'READY'), 'INPUT_RETAINED');
  assert.equal(M.importState(fund, syn, { ticker: ' ' }, 'READY'), 'INPUT_RETAINED', 'any typed character keeps the input (the old rule)');
  assert.equal(M.importState(fund, noname, {}, 'READY'), 'NAME_UNAVAILABLE');
  assert.equal(M.importState(fund, syn, { as_of: '2026-10-01' }, 'READY'), 'AVAILABLE');
  assert.deepEqual(M.fillCompany(fund, syn), { company: 'Synthetic Fixture Corp', ticker: 'SYN' });
  const seed = LIB.prompts.find((p) => p.variables.some((v) => v.name === 'seed_company'));
  if (seed) assert.deepEqual(Object.keys(M.fillCompany(seed, syn)).sort(), seed.variables.map((v) => v.name).filter((n) => ['company', 'ticker', 'seed_company', 'seed_ticker'].includes(n)).sort());
  for (const k of Object.keys(M.IMPORT_TEXT)) assert.ok(M.IMPORT_TEXT[k], k);
});

test('todayKST: the date in Seoul (the old 오늘 날짜 button)', () => {
  assert.equal(M.todayKST(new Date('2026-10-14T03:00:00Z')), '2026-10-14');
  assert.equal(M.todayKST(new Date('2026-10-14T15:30:00Z')), '2026-10-15');
});
