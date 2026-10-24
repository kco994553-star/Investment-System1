'use strict';
// New frontend P1 · reuse (plan A) and shell plumbing.
//  - web_app/index.html is the only reuse list: P0 base, the 57 old engines/readers (old page's relative order, each once),
//    the P1 layer (action → data → prices → store → qgv → engines), the eight lane placeholders, the P0 screens, boot.js last;
//    every tag a deferred file, the CSP byte-identical to the old page.
//  - A name present in web_app wins and is never reused (screen-detail.js); every other script is an old web_assets file.
//    tools/build_web_app.py applies the same rule, keeps the reused files byte-identical, removes every other old frontend
//    file, and fails on a reference found in neither folder, a duplicate, an inline script or a non-local name.
//  - Old modules that start themselves at load or are old screens are not loaded; load-time bindings come before their users.
//  - Screen registry: a placeholder never replaces a real screen, two real screens for one route fail (SCREEN_DUPLICATE),
//    detail screens register by name; screen-menus.js registers all eight menus as placeholders (a lane screen loaded first
//    stays); h() refuses a style string (the CSP would drop it).
//  - Source rules for every web_app script (no console output, no HTML strings, no style attribute strings, NA never filled
//    with 0, storage / network / Google session / engine rows / score and price views / V source words only in their P1 owner
//    files, no old path that bypasses the price view, no order feature), checked to catch their examples, and the Pages
//    guard's secret patterns.
// Wording rules for the fixed code list are left to tools/spec_direction_guard.py and not repeated here.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');

const P0_BASE = ['core.js', 'shell.js', 'parts.js'];
// Design 1.3 (57 files), in the old page's order.
const REUSED = [
  'locale.js', 'entity-search.js', 'price-time.js', 'device-market.js', 'device-actual.js', 'profile-defaults.js', 'type-config-defaults.js',
  'device-profiles.js', 'engine-preview.js', 'dcf-parameters-defaults.js', 'device-valuation.js', 'playbook-config-defaults.js', 'playbook-engine.js',
  'qgv-v2.js', 'scoring-default.js', 'qgv2-inputs.js', 'qgv-scores.js', 'private-subset.js', 'share-class-groups.js', 'sec-universe-shares.js',
  'sec-qgv2.js', 'private-subset-view.js', 'target-v1-config-defaults.js', 'target-v1-builder.js', 'playbook-screen.js', 'target-v1-screen.js',
  'device-backup.js', 'watchlist.js', 'app-config.js', 'google-sheet-core.js', 'google-sheet-quotes.js', 'technical-chart.js', 'google-sheet-setup.js',
  'private-trades.js', 'holdings-capture.js', 'worker-quote-fallback.js', 'forward-validation.js', 'private-history.js', 'sec-reported.js',
  'manager-styles-v0.js', 'thirteenf-quarter.js', 'macro-lights.js', 'macro-evidence.js', 'public-screens.js', 'sec-disclosures.js', 'news-signals.js',
  'classification-screens.js', 'dart-disclosures.js', 'virtual-trading.js', 'virtual-trading-runner.js', 'virtual-trading-signals.js',
  'virtual-trading-v-history.js', 'virtual-ledger-sheets.js', 'price-store.js', 'report-benchmarks.js', 'virtual-trading-compare.js', 'data-refresh.js',
];
const P1 = ['action.js', 'data.js', 'prices.js', 'store.js', 'qgv.js', 'engines.js'];
const LANES = ['qgv', 'technical', 'macro', 'news', 'portfolio', 'prompts', 'tree', 'lab'].map((id) => 'screen-' + id + '.js');
const P0_SCREENS = ['screen-search.js', 'screen-menus.js', 'screen-detail.js', 'boot.js'];
// P0 names that also exist in web_assets: web_app wins, so they are never reused.
const SHARED = ['index.html', 'screen-detail.js'];
// Old files deliberately not loaded, with the reason.
const NOT_LOADED = {
  'daily-report.js': 'wires document listeners at load; the report model is decided in P2-6',
  'table-sort.js': 'starts itself on DOMContentLoaded',
  'sec-universe-qg.js': 'unused by the app', 'sec-m3-adapter.js': 'unused by the app',
  'app.js': 'old app boot (autoLoad, attach)', 'home-screen.js': 'old screen', 'company-screen.js': 'old screen', 'universe-company.js': 'old screen',
  'stat-radar.js': 'old screen; reads the real window (P2-2)', 'leaderboard-screen.js': 'old screen (P2-2)', 'v-coverage.js': 'old screen',
  'portfolio-screen.js': 'old screen', 'ops-status.js': 'old screen', 'screen-detail.js': 'old screen (web_app has its own)',
  'macro-cycle-ring.js': 'P2-4', 'chart-workbench.js': 'P2-3', 'pwa.js': 'P3 decision', 'theme-boot.js': 'old theme',
};
// Bindings an old module takes when its factory runs (the rest are read at call time).
const EAGER = [
  ['profile-defaults.js', 'engine-preview.js'], ['profile-defaults.js', 'device-profiles.js'], ['private-subset.js', 'share-class-groups.js'],
  ['private-subset.js', 'sec-universe-shares.js'], ['share-class-groups.js', 'sec-universe-shares.js'], ['device-market.js', 'google-sheet-core.js'],
  ['device-profiles.js', 'device-backup.js'], ['playbook-screen.js', 'device-backup.js'], ['playbook-engine.js', 'playbook-screen.js'],
  ['playbook-config-defaults.js', 'playbook-screen.js'], ['playbook-engine.js', 'target-v1-builder.js'], ['playbook-config-defaults.js', 'target-v1-builder.js'],
  ['target-v1-config-defaults.js', 'target-v1-builder.js'], ['technical-chart.js', 'report-benchmarks.js'],
];
// Modules that silently change behaviour without a companion (e.g. cyclical V basis without the playbook engine).
const COMPANIONS = {
  'qgv-scores.js': ['playbook-config-defaults.js', 'playbook-engine.js', 'qgv-v2.js', 'qgv2-inputs.js', 'sec-qgv2.js', 'scoring-default.js', 'price-time.js'],
  'qgv2-inputs.js': ['sec-qgv2.js'], 'public-screens.js': ['macro-lights.js', 'thirteenf-quarter.js', 'manager-styles-v0.js'],
  'google-sheet-quotes.js': ['app-config.js', 'google-sheet-core.js'], 'price-store.js': ['virtual-trading-runner.js', 'virtual-ledger-sheets.js'],
};
const FRONTEND_SUFFIXES = ['.html', '.css', '.js', '.woff2', '.txt', '.png', '.svg'];
const isFile = (p) => fs.existsSync(p) && fs.statSync(p).isFile();
const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const files = (dir) => fs.readdirSync(dir).filter((n) => isFile(path.join(dir, n)));
const tags = (html) => [...String(html).replace(/<!--[\s\S]*?-->/g, '').matchAll(/<script\b([^>]*)>/gi)].map((m) => m[1]);
const csp = (html) => (/<meta http-equiv="Content-Security-Policy" content="([^"]*)"/.exec(html) || [])[1];
const py = (code, args = []) => execFileSync('python3', ['-c', code, ...args], { encoding: 'utf8' });

test('index.html loads P0 base, reused old modules, the P1 layer, lane placeholders, P0 screens, boot.js last', () => {
  assert.equal(REUSED.length, 57);
  assert.deepEqual(R.scripts(), [...P0_BASE, ...REUSED, ...P1, ...LANES, ...P0_SCREENS]);
});

test('web_app wins on a shared name; every other script is an old web_assets file; the reuse list is the design list', () => {
  assert.deepEqual(R.reused(), REUSED);
  for (const name of REUSED) { assert.ok(!isFile(R.newPath(name)), name + ' must not exist in web_app'); assert.ok(isFile(R.oldPath(name)), name); }
  for (const name of R.scripts().filter((n) => !REUSED.includes(n))) assert.ok(isFile(R.newPath(name)), name);
  assert.deepEqual(files(R.NEW).filter((n) => isFile(R.oldPath(n))).sort(), [...SHARED].sort(), 'no new file shadows an old one');
  for (const name of SHARED) assert.ok(!REUSED.includes(name));
});

test('reused modules keep the old page relative order and each loads once', () => {
  const set = new Set(REUSED);
  assert.deepEqual(R.oldScripts().filter((n) => set.has(n)), REUSED);
  const all = R.scripts();
  assert.equal(new Set(all).size, all.length, 'no script loads twice (the old page loaded the playbook pair twice)');
});

test('load-time bindings come before their users and companions are present', () => {
  const at = new Map(R.scripts().map((n, i) => [n, i]));
  for (const [dep, user] of EAGER) { assert.ok(at.has(dep) && at.has(user), dep + ' / ' + user); assert.ok(at.get(dep) < at.get(user), dep + ' before ' + user); }
  for (const [user, deps] of Object.entries(COMPANIONS)) for (const dep of deps) assert.ok(at.has(dep), user + ' needs ' + dep);
  const lastOld = Math.max(...REUSED.map((n) => at.get(n)));
  for (const name of [...P1, ...LANES, ...P0_SCREENS]) assert.ok(at.get(name) > lastOld, name + ' after every reused module');
  assert.ok(at.get('core.js') < at.get('action.js') && at.get('parts.js') < at.get(LANES[0]), 'IS2 and parts exist before the layer and the screens');
});

test('old modules that start themselves or are old screens are not loaded', () => {
  const loaded = new Set(R.reused());
  for (const [name, why] of Object.entries(NOT_LOADED)) {
    assert.ok(isFile(R.oldPath(name)), name + ' still exists in web_assets (keep this list meaningful)');
    assert.ok(!loaded.has(name), name + ': ' + why);
  }
});

test('every tag is a deferred file, every web_app script is loaded, the CSP is the old page CSP', () => {
  const html = R.newIndex();
  for (const t of tags(html)) { assert.match(t, /\bsrc="[^"]+"/, 'no inline script: ' + t); assert.match(t, /\bdefer\b/, 'defer keeps order: ' + t); assert.doesNotMatch(t, /\basync\b|type="module"/, t); }
  assert.deepEqual(files(R.NEW).filter((n) => n.endsWith('.js')).sort(), R.scripts().filter((n) => isFile(R.newPath(n))).sort());
  assert.ok(csp(html), 'CSP meta present');
  assert.equal(csp(html), csp(R.oldIndex()));
});

test('build keeps the reused old files byte-identical, removes every other old frontend file, copies web_app', () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-reuse-'));
  fs.rmSync(out, { recursive: true });
  try {
    execFileSync('python3', [path.join(R.ROOT, 'implementation/tools/build_web_app.py'), '--out', out], { stdio: ['ignore', 'ignore', 'inherit'] });
    for (const name of REUSED) { assert.ok(isFile(path.join(out, name)), name); assert.equal(sha(path.join(out, name)), sha(R.oldPath(name)), name + ' byte-identical'); }
    for (const name of files(R.NEW)) assert.equal(sha(path.join(out, name)), sha(R.newPath(name)), name + ' from web_app');
    const stray = files(R.OLD).filter((n) => (FRONTEND_SUFFIXES.includes(path.extname(n)) || n === 'manifest.json') && !REUSED.includes(n) && !isFile(R.newPath(n)) && isFile(path.join(out, n)));
    assert.deepEqual(stray, [], 'unreferenced old frontend files are not in the build');
    for (const name of ['research.html', 'network.html', 'manifest.json']) assert.ok(!isFile(path.join(out, name)), name);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('build rule (python) equals the helper and fails on missing, duplicate, inline and non-local references', () => {
  const tools = path.join(R.ROOT, 'implementation/tools');
  const rule = (newDir, oldDir) => JSON.parse(py(`import json,sys\nsys.path.insert(0,sys.argv[1])\nimport build_web_app as b\nfrom pathlib import Path\n`
    + `try:\n    print(json.dumps({'ok': b.reused_old_files(*[Path(a) for a in sys.argv[2:]])}))\nexcept ValueError as e:\n    print(json.dumps({'error': str(e)}))`,
  [tools, ...(newDir ? [newDir, oldDir] : [])]));
  assert.deepEqual(rule(), { ok: REUSED });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-rule-')), W = path.join(dir, 'w'), O = path.join(dir, 'o');
  try {
    fs.mkdirSync(W); fs.mkdirSync(O);
    for (const [d, n] of [[W, 'a.js'], [W, 'app.css'], [O, 'a.js'], [O, 'b.js'], [O, 'old.css']]) fs.writeFileSync(path.join(d, n), '//\n');
    const page = (body) => { fs.writeFileSync(path.join(W, 'index.html'), '<link rel="icon" href="data:,"><link rel="stylesheet" href="app.css">' + body); return rule(W, O); };
    assert.deepEqual(page('<script defer src="a.js"></script><!-- <script src="gone.js"></script> --><script defer src="b.js"></script>'), { ok: ['b.js'] }, 'web_app wins on a.js');
    assert.match(page('<script src="c.js"></script>').error, /neither/);
    assert.match(page('<script src="b.js"></script><script src="b.js"></script>').error, /twice/);
    assert.match(page('<script>void 0</script>').error, /inline/);
    for (const bad of ['../b.js', 'https://x.example/b.js', 'sub/b.js', 'b.js?v=1']) assert.match(page(`<script src="${bad}"></script>`).error, /not a local file name/, bad);
    assert.match(page('<link rel="stylesheet" href="old.css">').error, /links a file/);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('P1 layer files are UMD modules exporting create()', () => {
  for (const name of P1) assert.equal(typeof R.requireNew(name).create, 'function', name);
});

test('screen registry: placeholders, SCREEN_DUPLICATE, detail screens', () => {
  delete require.cache[require.resolve(R.newPath('core.js'))];
  const core = R.requireNew('core.js'), a = () => 'a', b = () => 'b', p = () => 'p';
  core.register('qgv', a);
  core.register('qgv', p, { placeholder: true });
  assert.equal(core.screen('qgv'), a, 'a placeholder never replaces a real screen');
  assert.equal(core.isPlaceholder('qgv'), false);
  assert.throws(() => core.register('qgv', b), /SCREEN_DUPLICATE/);
  core.register('macro', p, { placeholder: true });
  assert.equal(core.isPlaceholder('macro'), true);
  core.register('macro', b);
  assert.equal(core.screen('macro'), b, 'a real screen replaces a placeholder');
  assert.throws(() => core.register('macro', a), /SCREEN_DUPLICATE/);
  assert.throws(() => core.register('news', 'x'), /SCREEN_INVALID/);
  core.registerDetail('settings', a);
  assert.equal(core.detail('settings'), a);
  assert.equal(core.detail('playbook'), null);
  assert.throws(() => core.registerDetail('settings', b), /SCREEN_DUPLICATE/);
  assert.throws(() => core.registerDetail('nowhere', a), /DETAIL_UNKNOWN/);
  assert.equal(core.screen('lab'), null);
});

// Code only: comments may name what a file must not do. Block comments keep their line breaks; a line comment starts a line or
// follows whitespace / punctuation (so the '//' of a URL inside a string stays).
const code = (text) => text.replace(/\/\*[\s\S]*?\*\//g, (c) => c.replace(/[^\n]/g, ' ')).split('\n').map((l) => l.replace(/(^|[\s;,(){}])\/\/.*$/, '$1'));
// [rule, pattern, files allowed to match]
const RULES = [
  ['console output', /\bconsole\./, []],
  ['HTML strings', /\binnerHTML\b|\bouterHTML\b|insertAdjacentHTML|document\.write/, []],
  ['eval', /\beval\(|\bnew Function\b/, []],
  ['NA filled with 0', /(\?\?|\|\|)\s*0(?!\d)/, []],
  ['style property writes (CSSOM helper only)', /\.style\./, ['core.js']],
  ['style attribute strings (the CSP drops them)', /\bstyle\s*:\s*['"`]|setAttribute\(\s*['"`]style\b|\[['"`]style['"`]\]\s*=/, []],
  ['device storage outside the P1 layer', /\b(localStorage|sessionStorage|indexedDB)\b/, P1],
  ['V source words outside qgv.js (screens use row.source_label / qgv.V_SOURCES)', /임시 V|공식 V|DEVICE_TEMPORARY|OFFICIAL_CENTRAL|중앙 V 미게시|기기 시세로 계산/, ['qgv.js']],
  ['hard-coded calc version', /qgv2-calc\//, []],
  ['network outside data.js and prices.js', /\bfetch\(/, ['data.js', 'prices.js']],
  ['price fetch outside prices.js and engines.js', /\bfetch\s*:\s*true\b/, ['prices.js', 'engines.js']],
  ['Google session outside prices.js', /\bsessionFor\(/, ['prices.js']],
  ['engine rows / score view outside qgv.js and engines.js', /\b(?:forEngines|engineInputs)\(|\bscoreView\b/, ['qgv.js', 'engines.js']],
  ['the price view outside prices.js and engines.js', /\bpriceView\b/, ['prices.js', 'engines.js']],
  ['old paths that bypass the price view', /\bautoLoad\b|\blatestPublished\b|\bStatRadar\b|\bDataRefresh\.attach\b|\b(PrivateSubsetView|TargetV1Screen|PriceStore|VirtualLedgerSheets)\.mount\w*\(/, []],
  ['order features', /placeOrder|submitOrder|sendOrder|주문하기|매수 주문|매도 주문/, []],
];
test('source rules for every web_app script (code, not comments)', () => {
  const scripts = files(R.NEW).filter((n) => n.endsWith('.js'));
  assert.ok(scripts.length >= P0_BASE.length + P1.length + LANES.length + P0_SCREENS.length);
  for (const name of scripts) {
    const lines = code(fs.readFileSync(R.newPath(name), 'utf8'));
    for (const [rule, re, allowed] of RULES) {
      if (allowed.includes(name)) continue;
      const hits = lines.map((l, i) => (re.test(l) ? i + 1 : 0)).filter(Boolean);
      assert.deepEqual(hits, [], name + ': ' + rule + ' (lines)');
    }
  }
  assert.doesNotMatch(R.newIndex(), RULES.find((r) => r[0] === 'order features')[1]);
});

test('source rules catch what they name (V source words, style attribute strings)', () => {
  const rule = (name) => RULES.find((r) => r[0].startsWith(name))[1];
  for (const line of ["label.textContent='공식 V'", "row.source==='DEVICE_TEMPORARY'", "note.textContent='기기 시세로 계산 · 중앙 V 미게시'", "x.textContent='임시 V'", "if(id==='OFFICIAL_CENTRAL')"])
    assert.match(line, rule('V source words'), line);
  assert.doesNotMatch("chip.textContent=row.source_label", rule('V source words'));
  for (const line of ["h('p',{style:'color:red'})", 'h("p",{style: "width:4px"})', "el.setAttribute('style','x')", "el['style']='x'"]) assert.match(line, rule('style attribute strings'), line);
  assert.doesNotMatch("h('i',{style:{width:'40%'}})", rule('style attribute strings'));
});

test('screen-menus.js registers every menu as a placeholder: a lane screen registered first is kept; h() refuses a style string', () => {
  delete require.cache[require.resolve(R.newPath('core.js'))];
  const core = R.requireNew('core.js'), lane = () => 'lane';
  core.register('macro', lane);// a P2 lane file loads before screen-menus.js (index.html order)
  const parts = { head: () => null, section: () => null, pending: () => null };
  vm.runInNewContext(fs.readFileSync(R.newPath('screen-menus.js'), 'utf8'), { window: { IS2: { ...core, parts } }, Object });
  const ids = core.MENU.filter((m) => m.id !== 'search').map((m) => m.id);
  assert.equal(ids.length, 8);
  for (const id of ids) {
    assert.equal(typeof core.screen(id), 'function', id);
    if (id === 'macro') { assert.equal(core.screen(id), lane, 'the lane screen stays'); assert.equal(core.isPlaceholder(id), false); }
    else assert.equal(core.isPlaceholder(id), true, id + ' is a placeholder (a lane may replace it)');
  }
  const doc = { createElement: () => ({ style: { setProperty() {} }, setAttribute() {}, addEventListener() {}, dataset: {}, appendChild() {} }), createTextNode: () => ({}) };
  const saved = globalThis.document; globalThis.document = doc;
  try {
    assert.throws(() => core.h('p', { style: 'color:red' }), /STYLE_INVALID/);
    assert.doesNotThrow(() => core.h('p', { style: { color: 'red' } }));
  } finally { globalThis.document = saved; }
});

test('web_app text files pass the Pages guard secret patterns', () => {
  const out = py(`import json,sys\nsys.path.insert(0,sys.argv[1])\nimport pages_artifact_guard as g\nfrom pathlib import Path\n`
    + `print(json.dumps({p.name: sum(len(x.findall(p.read_text(encoding='utf-8'))) for x in g.SECRET_PATTERNS) for p in sorted(Path(sys.argv[2]).iterdir()) if p.suffix in ('.js','.html','.css','.txt')}))`,
  [path.join(R.ROOT, 'implementation/tools'), R.NEW]);
  const counts = JSON.parse(out);
  assert.ok(Object.keys(counts).length > 0);
  assert.deepEqual(Object.entries(counts).filter(([, n]) => n > 0), []);
});
