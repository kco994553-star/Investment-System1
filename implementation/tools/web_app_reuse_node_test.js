'use strict';
// New frontend P1 · reuse (plan A), the first-paint loader (P2-1a) and shell plumbing.
//  - What the page loads (owner 2026-10-24, first paint): index.html only the first screen (P0 base, loader.js, the eight lane
//    placeholders, the P0 screens, boot.js last; web_app files only, every tag a deferred file, the CSP byte-identical to the old
//    page), then loader.js LOAD_ORDER after the first paint: the 59 old engines/readers (old page's relative order, each once)
//    and the P1 layer (action → data → prices → store → qgv → engines). LOAD_ORDER is the one load list: the loader's runtime
//    list, tools/web_app_reuse.js and tools/build_web_app.py read the same literal.
//  - A name present in web_app wins and is never reused (screen-detail.js); every other script is an old web_assets file.
//    tools/build_web_app.py applies the same rule, keeps the reused files byte-identical, removes every other old frontend
//    file, and fails on a reference found in neither folder, a duplicate, an inline script, a non-local name, an old module in
//    index.html, a LOAD_ORDER that is not one literal of plain quoted names, or a loader index.html does not load.
//  - LOAD_ORDER names: the build (LOAD_NAME, and loader.js must define NAME as the build's exact line) and the helper (the
//    loader's own NAME) refuse exactly the names, and a name twice, that the loader refuses at runtime (LOADER_NAME_INVALID),
//    run through all three on one table.
//  - Loader (fake window): nothing is inserted before the shell's first paint and an idle moment (at once in a hidden page);
//    then every listed file as a same-origin <script src> with async=false, in order; IS2.ready resolves when all ran and the
//    layer installed itself, else rejects with LOADER_FAILED <first failed file in list order> (missing, threw while it ran,
//    or installed nothing), and the facades are put back. Facades before ready: 's'/'v' → IS2.NOT_READY, 'a' throws
//    LAYER_NOT_READY, 'p' waits for ready, 'sub' attaches when ready (not after its signal aborted); after ready a kept facade
//    forwards; after a failure they refuse. The facade API is the real layer's API (kinds checked against the functions).
//  - The screen files touch no layer namespace while they load (they draw before the layer); the fonts never hold the first
//    screen (font-display swap / optional, no preload).
//  - Old modules that start themselves at load or are old screens are not loaded; load-time bindings come before their users.
//    chart-workbench.js and macro-cycle-ring.js are loaded for their backup /5 validators (owner 2026-10-24: reuse, never rewrite)
//    because loading them is side-effect free: run as a browser script against a recording global, each only defines its own
//    global (no DOM, request, storage, timer or listener).
//  - The V history is never recorded (owner 2026-10-24, D9): no web_app script and no reused module calls its capture / record.
//  - Screen registry: a placeholder never replaces a real screen, two real screens for one route fail (SCREEN_DUPLICATE),
//    detail screens register by name; screen-menus.js registers all eight menus as placeholders (a lane screen loaded first
//    stays); h() refuses a style string (the CSP would drop it) and a script tag in any case or namespace (TAG_INVALID).
//  - Source rules for every web_app script (no console output, no HTML strings, no style attribute strings, NA never filled
//    with 0, storage / network / Google session / engine rows / score and price views / V source words only in their P1 owner
//    files, no old path that bypasses the price view, no order feature, no script element outside loader.js: a 'script' tag
//    in createElement / createElementNS / h() only there, a computed tag or an indirect createElement(NS) only in core.js h(),
//    no HTML parsing), checked to catch their examples, and the Pages guard's secret patterns.
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
// Design 1.3 (57 files) plus the two backup /5 validator modules (owner 2026-10-24), in the old page's order.
const REUSED = [
  'locale.js', 'entity-search.js', 'price-time.js', 'device-market.js', 'device-actual.js', 'profile-defaults.js', 'type-config-defaults.js',
  'device-profiles.js', 'engine-preview.js', 'dcf-parameters-defaults.js', 'device-valuation.js', 'playbook-config-defaults.js', 'playbook-engine.js',
  'qgv-v2.js', 'scoring-default.js', 'qgv2-inputs.js', 'qgv-scores.js', 'private-subset.js', 'share-class-groups.js', 'sec-universe-shares.js',
  'sec-qgv2.js', 'private-subset-view.js', 'target-v1-config-defaults.js', 'target-v1-builder.js', 'playbook-screen.js', 'target-v1-screen.js',
  'device-backup.js', 'watchlist.js', 'app-config.js', 'google-sheet-core.js', 'google-sheet-quotes.js', 'technical-chart.js', 'chart-workbench.js', 'google-sheet-setup.js',
  'private-trades.js', 'holdings-capture.js', 'worker-quote-fallback.js', 'forward-validation.js', 'private-history.js', 'sec-reported.js',
  'manager-styles-v0.js', 'thirteenf-quarter.js', 'macro-lights.js', 'macro-cycle-ring.js', 'macro-evidence.js', 'public-screens.js', 'sec-disclosures.js', 'news-signals.js',
  'classification-screens.js', 'dart-disclosures.js', 'virtual-trading.js', 'virtual-trading-runner.js', 'virtual-trading-signals.js',
  'virtual-trading-v-history.js', 'virtual-ledger-sheets.js', 'price-store.js', 'report-benchmarks.js', 'virtual-trading-compare.js', 'data-refresh.js',
];
const P1 = ['action.js', 'data.js', 'prices.js', 'store.js', 'qgv.js', 'engines.js'];
const LANES = ['qgv', 'technical', 'macro', 'news', 'portfolio', 'prompts', 'tree', 'lab'].map((id) => 'screen-' + id + '.js');
const P0_SCREENS = ['screen-search.js', 'screen-menus.js', 'screen-detail.js', 'boot.js'];
const LOADER = 'loader.js';
// index.html: the first screen only.
const FIRST = [...P0_BASE, LOADER, ...LANES, ...P0_SCREENS];
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
  'pwa.js': 'P3 decision', 'theme-boot.js': 'old theme',
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
const py = (code, args = [], input = '') => execFileSync('python3', ['-c', code, ...args], { encoding: 'utf8', input });

test('index.html loads the first screen only; loader.js LOAD_ORDER loads the reused old modules, then the P1 layer', () => {
  assert.equal(REUSED.length, 59);
  assert.deepEqual(R.firstPaint(), FIRST);
  assert.deepEqual(R.loadOrder(), [...REUSED, ...P1]);
  delete require.cache[require.resolve(R.newPath(LOADER))];
  assert.deepEqual([...R.requireNew(LOADER).LOAD_ORDER], R.loadOrder(), 'the loader runs the list the build and the helper read');
  assert.deepEqual(R.scripts(), [...FIRST, ...REUSED, ...P1], 'the page load order: index.html, then LOAD_ORDER');
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
  const lastOld = Math.max(...REUSED.map((n) => at.get(n))), firstLoaded = Math.min(...R.loadOrder().map((n) => at.get(n)));
  for (const name of P1) assert.ok(at.get(name) > lastOld, name + ' after every reused module');
  for (const name of FIRST) assert.ok(at.get(name) < firstLoaded, name + ' is on the first screen, before every LOAD_ORDER file');
  assert.ok(at.get('core.js') < at.get('action.js') && at.get('parts.js') < at.get(LANES[0]), 'IS2 and parts exist before the layer and the screens');
  for (const name of [...LANES, ...P0_SCREENS]) assert.ok(at.get(LOADER) < at.get(name), 'the loader facades exist before ' + name);
  assert.equal(R.firstPaint().at(-1), 'boot.js', 'boot.js starts the page last');
});

test('old modules that start themselves or are old screens are not loaded', () => {
  const loaded = new Set(R.reused());
  for (const [name, why] of Object.entries(NOT_LOADED)) {
    assert.ok(isFile(R.oldPath(name)), name + ' still exists in web_assets (keep this list meaningful)');
    assert.ok(!loaded.has(name), name + ': ' + why);
  }
});

/* Runs an old module as a browser classic script (no `module`) against a global that records every name it reads or writes. A
   side-effect free module reads only `module` / `window` to pick its export path and writes only its own global. */
function loadRecorded(name) {
  const base = { Object, Array, Map, Set, WeakMap, WeakSet, JSON, Math, Number, String, Boolean, Symbol, Error, TypeError, RangeError, RegExp, Date, Promise, Intl, Reflect, Proxy, parseInt, parseFloat, isFinite, isNaN, Infinity, NaN, undefined };
  const own = {}, seen = new Set();
  const g = new Proxy(own, {
    get(t, k) { if (k === 'globalThis' || k === 'window') { seen.add('get ' + k); return g; } if (typeof k === 'string' && !(k in base)) seen.add('get ' + k); return k in t ? t[k] : base[k]; },
    set(t, k, v) { seen.add('set ' + String(k)); t[k] = v; return true; },
    has(t, k) { if (typeof k === 'string' && !(k in base) && k !== 'globalThis' && k !== 'window') seen.add('has ' + k); return k in t || k in base || k === 'globalThis' || k === 'window'; },
  });
  vm.runInContext(fs.readFileSync(R.oldPath(name), 'utf8'), vm.createContext(g), { filename: name });
  return { seen: [...seen].filter((x) => x !== 'get globalThis' && x !== 'get window' && x !== 'get module'), own: Object.keys(own) };
}
test('the backup /5 validator modules load without side effects and expose what DeviceBackup looks up', () => {
  for (const [name, global] of [['chart-workbench.js', 'ChartWorkbench'], ['macro-cycle-ring.js', 'MacroCycleRing']]) {
    const r = loadRecorded(name);
    assert.deepEqual(r, { seen: ['set ' + global], own: [global] }, name + ': no DOM, request, storage, timer or listener at load');
  }
  // The recorder itself catches a module that touches the page at load.
  assert.deepEqual(loadRecorded('table-sort.js').seen.filter((x) => /document|addEventListener/.test(x)).length > 0, true, 'table-sort.js starts itself and is caught');
  const CW = R.requireOld('chart-workbench.js'); require(R.oldPath('macro-cycle-ring.js')); const MC = globalThis.MacroCycleRing;
  for (const [m, keys] of [[CW, ['parseUserExport', 'createDeviceUserStore', 'mergeUserItems', 'USER_SCHEMA', 'USER_KEY']], [MC, ['parseUserExport', 'readUserStore', 'importUserHistory', 'USER_SCHEMA', 'USER_KEY']]])
    for (const k of keys) assert.ok(m[k] !== undefined, k);
});

test('the V history is never recorded: no web_app script or reused module calls its capture / record', () => {
  const RECORD = /\b(?:VHistory|VirtualTradingVHistory)\s*(?:\?\.|\.)\s*(?:capture|captureV2|record|recordV2)\b/;
  assert.match('const c=await VHistory.capture(window,result)', RECORD); assert.match('VirtualTradingVHistory.recordV2(s)', RECORD); assert.match('VHistory?.captureV2(w)', RECORD);
  assert.doesNotMatch('VirtualTradingVHistory.readV2(storage)', RECORD);
  for (const name of files(R.NEW).filter((n) => n.endsWith('.js'))) assert.doesNotMatch(code(fs.readFileSync(R.newPath(name), 'utf8')).join('\n'), RECORD, name);
  for (const name of R.reused()) assert.doesNotMatch(code(fs.readFileSync(R.oldPath(name), 'utf8')).join('\n'), RECORD, name);
  assert.match(fs.readFileSync(R.oldPath('app.js'), 'utf8'), RECORD, 'the old app (not loaded) is where it was recorded');
});

test('every tag is a deferred file, every web_app script is loaded, the CSP is the old page CSP', () => {
  const html = R.newIndex();
  for (const t of tags(html)) { assert.match(t, /\bsrc="[^"]+"/, 'no inline script: ' + t); assert.match(t, /\bdefer\b/, 'defer keeps order: ' + t); assert.doesNotMatch(t, /\basync\b|type="module"/, t); }
  for (const name of R.firstPaint()) assert.ok(isFile(R.newPath(name)), 'index.html loads web_app files only: ' + name);
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

// build_web_app.parse_load_order over several loader texts in one python run: [{ok: names} | {error}].
const parse = (texts) => JSON.parse(py(`import json,sys\nsys.path.insert(0,sys.argv[1])\nimport build_web_app as b\nout=[]\n`
  + `for t in json.loads(sys.stdin.read()):\n    try:\n        out.append({'ok': b.parse_load_order(t)})\n    except ValueError as e:\n        out.append({'error': str(e)})\nprint(json.dumps(out))`,
[path.join(R.ROOT, 'implementation/tools')], JSON.stringify(texts)));
const NAME_LINE = 'const NAME=' + String(R.requireNew(LOADER).NAME) + ';';
test('build rule (python) equals the helper and fails on missing, duplicate, inline and non-local references', () => {
  const tools = path.join(R.ROOT, 'implementation/tools');
  const rule = (newDir, oldDir) => JSON.parse(py(`import json,sys\nsys.path.insert(0,sys.argv[1])\nimport build_web_app as b\nfrom pathlib import Path\n`
    + `try:\n    print(json.dumps({'ok': b.reused_old_files(*[Path(a) for a in sys.argv[2:]])}))\nexcept ValueError as e:\n    print(json.dumps({'error': str(e)}))`,
  [tools, ...(newDir ? [newDir, oldDir] : [])]));
  const order = (newDir) => JSON.parse(py(`import json,sys\nsys.path.insert(0,sys.argv[1])\nimport build_web_app as b\nfrom pathlib import Path\n`
    + `try:\n    print(json.dumps({'ok': b.load_order(*[Path(a) for a in sys.argv[2:]])}))\nexcept ValueError as e:\n    print(json.dumps({'error': str(e)}))`,
  [tools, ...(newDir ? [newDir] : [])]));
  assert.deepEqual(rule(), { ok: REUSED });
  assert.deepEqual(order(), { ok: R.loadOrder() }, 'python and the helper read the same LOAD_ORDER');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-rule-')), W = path.join(dir, 'w'), O = path.join(dir, 'o');
  const helper = (text) => { try { return { ok: R.loadOrderOf(text) }; } catch (e) { return { error: e.message }; } };
  try {
    fs.mkdirSync(W); fs.mkdirSync(O);
    for (const [d, n] of [[W, 'a.js'], [W, 'c.js'], [W, 'app.css'], [O, 'a.js'], [O, 'b.js'], [O, 'old.css']]) fs.writeFileSync(path.join(d, n), '//\n');
    const BASE = '<link rel="icon" href="data:,"><link rel="stylesheet" href="app.css"><script defer src="a.js"></script><!-- <script src="gone.js"></script> --><script defer src="loader.js"></script>';
    const page = (list, body = BASE) => {
      if (list === null) fs.rmSync(path.join(W, 'loader.js'), { force: true }); else fs.writeFileSync(path.join(W, 'loader.js'), typeof list === 'string' ? list : `const X=1;\nconst LOAD_ORDER=Object.freeze([\n ${list.map((n) => `'${n}'`).join(',')},\n]);\n${NAME_LINE}\n`);
      fs.writeFileSync(path.join(W, 'index.html'), body); return rule(W, O);
    };
    assert.deepEqual(page(['b.js', 'c.js']), { ok: ['b.js'] }, 'web_app wins on a.js and c.js; b.js is reused from web_assets');
    assert.match(page(['gone.js']).error, /neither/);
    assert.match(page(['a.js']).error, /twice/, 'a name in index.html and LOAD_ORDER');
    assert.match(page(['b.js', 'b.js']).error, /twice/);
    assert.match(page(['b.js'], BASE + '<script defer src="b.js"></script>').error, /index\.html loads a script that is not in web_app: b\.js/, 'an old module before the first paint');
    assert.match(page(['b.js'], BASE.replace('<script defer src="loader.js"></script>', '')).error, /does not load loader\.js/);
    assert.deepEqual(page(null, BASE.replace('<script defer src="loader.js"></script>', '')), { ok: [] }, 'no loader: the first screen only');
    assert.match(page(['b.js'], BASE + '<script>void 0</script>').error, /inline/);
    assert.match(page(['b.js'], BASE + '<link rel="stylesheet" href="old.css">').error, /links a file/);
    for (const bad of ['../b.js', 'https://x.example/b.js', 'sub/b.js', 'b.js?v=1', 'Bad_name.js', 'old.css']) assert.match(page([bad]).error, /LOAD_ORDER lists a name the loader refuses at runtime \(LOADER_NAME_INVALID/, bad);
    // The build reads the loader's own name rule line; a loader whose rule differs (or is missing, or defined twice) fails.
    const plain = "const LOAD_ORDER=Object.freeze(['b.js']);\n";
    assert.deepEqual(page(plain + NAME_LINE), { ok: ['b.js'] });
    for (const text of [plain, plain + NAME_LINE.replace('[a-z0-9-]*', '[a-z0-9_-]*'), plain + NAME_LINE + '\n' + NAME_LINE]) assert.match(page(text).error, /must define its name rule once, exactly as the build does/, text);
    const LITERALS = {
      plain: ["const LOAD_ORDER=Object.freeze(['b.js','c.js']);", { ok: ['b.js', 'c.js'] }],
      trailing: ["const LOAD_ORDER=Object.freeze([\n 'b.js',\n 'c.js',\n]);", { ok: ['b.js', 'c.js'] }],
      expression: ["const LOAD_ORDER=Object.freeze(['b.js',x]);", /plain quoted name|LOAD_ORDER_INVALID/],
      doubleQuoted: ['const LOAD_ORDER=Object.freeze(["b.js"]);', /plain quoted name|LOAD_ORDER_INVALID/],
      hole: ["const LOAD_ORDER=Object.freeze(['b.js',,'c.js']);", /plain quoted name|LOAD_ORDER_INVALID/],
      comment: ["const LOAD_ORDER=Object.freeze(['b.js', // x\n 'c.js']);", /plain quoted name|LOAD_ORDER_INVALID/],
      missing: ["const ORDER=Object.freeze(['b.js']);", /exactly one|LOAD_ORDER_MISSING/],
      twice: ["const LOAD_ORDER=Object.freeze(['b.js']);\nconst LOAD_ORDER=Object.freeze(['c.js']);", /exactly one|LOAD_ORDER_MISSING/],
      badName: ["const LOAD_ORDER=Object.freeze(['b.js','Bad_name.js']);", /LOADER_NAME_INVALID/],
      duplicate: ["const LOAD_ORDER=Object.freeze(['b.js','b.js']);", /LOADER_NAME_INVALID/],
      empty: ['const LOAD_ORDER=Object.freeze([]);', { ok: [] }],
    };
    const names = Object.keys(LITERALS), pys = parse(names.map((n) => LITERALS[n][0]));
    names.forEach((name, i) => {
      const [text, want] = LITERALS[name], py1 = pys[i], js1 = helper(text);
      if (want instanceof RegExp) { assert.match(py1.error || '', want, 'python ' + name); assert.match(js1.error || '', want, 'helper ' + name); }
      else { assert.deepEqual(py1, want, 'python ' + name); assert.deepEqual(js1, want, 'helper ' + name); }
    });
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('LOAD_ORDER names: the build and the helper refuse exactly what the loader refuses at runtime (LOADER_NAME_INVALID)', () => {
  const L = R.requireNew(LOADER), tools = path.join(R.ROOT, 'implementation/tools');
  assert.deepEqual(JSON.parse(py(`import json,sys\nsys.path.insert(0,sys.argv[1])\nimport build_web_app as b\nprint(json.dumps([b.LOAD_NAME.pattern, b.LOAD_NAME.flags & 0x1ff]))`, [tools])),
    [L.NAME.source, 32], 'python LOAD_NAME is the loader\'s NAME (re.UNICODE only, as a str pattern always has; no other flag)');
  assert.equal(L.NAME.flags, '', 'the loader\'s NAME has no flag');
  assert.deepEqual([R.LOAD_NAME.source, R.LOAD_NAME.flags], [L.NAME.source, L.NAME.flags], 'the helper uses the loader\'s NAME');
  const OK = ['a.js', 'b.js', 'a-b.js', 'a.b.js', '0.js', 'x1-2.min.js', 'data-refresh.js'];
  const BAD = ['Bad_name.js', 'B.js', 'b.JS', 'b c.js', 'b_c.js', '-b.js', '.b.js', 'b..js', 'b.js.', 'b.css', 'b', '.js', '', 'sub/b.js', '../b.js', 'b.js?v=1',
    'b.js#x', 'https://x.example/b.js', 'b.js\n', '\u00e9.js', 'b.js ', ' b.js', "b'.js"];
  const lists = [...[...OK, ...BAD].map((n) => [n]), ['b.js', 'b.js'], ['a.js', 'b.js'], []];
  const text = (list) => 'const LOAD_ORDER=Object.freeze([' + list.map((n) => "'" + n + "'").join(',') + ']);';
  const pys = parse(lists.map(text));
  lists.forEach((list, i) => {
    const want = list.length === 0 || (list.every((n) => OK.includes(n)) && new Set(list).size === list.length);
    let loader = true; try { L.create(fakePage(), { list }); } catch (e) { assert.equal(e.message, 'LOADER_NAME_INVALID'); loader = false; }
    let helper = true; try { assert.deepEqual(R.loadOrderOf(text(list)), list); } catch (e) { assert.match(e.message, /^(?:LOADER_NAME_INVALID|LOAD_ORDER_INVALID)/); helper = false; }
    if (pys[i].ok) assert.deepEqual(pys[i].ok, list);
    assert.deepEqual({ loader, build: !pys[i].error, helper }, { loader: want, build: want, helper: want }, JSON.stringify(list) + ' ' + (pys[i].error || ''));
  });
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
  ['HTML strings', /\binnerHTML\b|\bouterHTML\b|insertAdjacentHTML|document\.write|createContextualFragment|\bDOMParser\b|\b(?:set|parse)HTMLUnsafe\b|\bsrcdoc\b/, []],
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
  // DeviceActual's own screen runs on the real window (host.ownerDocument.defaultView) and saves, imports and deletes the holdings
  // together with the stopped quote record; its quote import writes that record (DC-18). Holdings writes go through the store.
  ['old writers of the stopped device quote record', /\bDeviceActual\.(?:mount\w*|applyMarketImport)\(/, []],
  ['order features', /placeOrder|submitOrder|sendOrder|주문하기|매수 주문|매도 주문/, []],
  // The loader inserts the listed scripts; nothing else in web_app makes a script element (GIS comes through the old modules):
  // a 'script' tag (any case, either namespace) given to createElement / createElementNS / h() only in loader.js; an element
  // made from a computed tag, or createElement(NS) held or called indirectly, only in core.js h(), which refuses 'script' and
  // 'svg:script' (TAG_INVALID); HTML parsing that could make one is refused with the HTML strings above.
  // (Known limit of a regex rule: bracket access with a built name, document['create'+'Element'](...), is not matched; h() and
  // the computed-tag rule are the runtime and static backstops.)
  ['script elements outside loader.js', /\bcreateElement(?:NS)?\s*\([^)]*['"`](?:svg:)?(?:[^'"`:]*:)*script['"`]|\bh\(\s*['"`](?:svg:)?(?:[^'"`:]*:)*script['"`]/i, [LOADER]],
  ['elements from a computed tag outside core.js h()', /\bcreateElement\s*\(\s*(?!(['"])[A-Za-z0-9-]+\1\s*\))|\bcreateElementNS\s*\(\s*[^,()]*,\s*(?!(['"])[A-Za-z0-9-]+\2\s*\))|\bcreateElement(?:NS)?\b(?!\s*\()/, ['core.js']],
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

test('source rules catch what they name (V source words, style attribute strings, script elements, HTML parsing)', () => {
  const rule = (name) => RULES.find((r) => r[0].startsWith(name))[1];
  for (const line of ["label.textContent='공식 V'", "row.source==='DEVICE_TEMPORARY'", "note.textContent='기기 시세로 계산 · 중앙 V 미게시'", "x.textContent='임시 V'", "if(id==='OFFICIAL_CENTRAL')"])
    assert.match(line, rule('V source words'), line);
  assert.doesNotMatch("chip.textContent=row.source_label", rule('V source words'));
  for (const line of ["h('p',{style:'color:red'})", 'h("p",{style: "width:4px"})', "el.setAttribute('style','x')", "el['style']='x'"]) assert.match(line, rule('style attribute strings'), line);
  assert.doesNotMatch("h('i',{style:{width:'40%'}})", rule('style attribute strings'));
  // Script elements: only loader.js makes one; a computed tag only in core.js h() (which refuses 'script').
  const script = rule('script elements'), computed = rule('elements from a computed tag');
  for (const line of ["const s=document.createElement('script')", 'doc.createElement("SCRIPT")', 'doc.createElement( `script` )', "document.createElementNS('http://www.w3.org/2000/svg','script')",
    'document.createElementNS(SVG, "script")', "document.createElementNS('http://www.w3.org/1999/xhtml','Script')", "h('script',{src:'x.js'})", 'h("svg:script",null)', "IS2.h( 'SCRIPT' )", 'h(`script`)', "h('svg:x:script',{href:'p.js'})", "h('svg:xlink:script')", "document.createElementNS(SVG,'x:script')"])
    assert.match(line, script, line);
  for (const line of ['document.createElement(tag)', 'document.createElement(name.trim())', "document.createElement('scr'+'ipt')", 'doc.createElement(`scr${x}`)', 'document.createElementNS(SVG,tag)',
    "document.createElementNS(SVG, kind+'')", 'const make=document.createElement', "document['createElement']('script')", "document.createElement.call(document,'script')", 'const {createElementNS}=document'])
    assert.match(line, computed, line);
  for (const line of ["document.createElementNS('http://www.w3.org/2000/svg','circle')", "doc.createElement('button')", "h('p',null,'script')", "h('svg:path',{d})", "h('script-note')", "x.textContent='script'"]) {
    assert.doesNotMatch(line, script, line); assert.doesNotMatch(line, computed, line);
  }
  for (const line of ["r.createContextualFragment('<b>')", 'new DOMParser()', 'el.setHTMLUnsafe(x)', "f.srcdoc='x'"]) assert.match(line, rule('HTML strings'), line);
});

test('screen-menus.js registers every menu as a placeholder: a lane screen registered first is kept; h() refuses a style string and a script tag', () => {
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
  const mk = () => ({ style: { setProperty() {} }, setAttribute() {}, addEventListener() {}, dataset: {}, appendChild() {} });
  const doc = { createElement: mk, createTextNode: () => ({}) };
  const saved = globalThis.document; globalThis.document = doc;
  try {
    assert.throws(() => core.h('p', { style: 'color:red' }), /STYLE_INVALID/);
    assert.doesNotThrow(() => core.h('p', { style: { color: 'red' } }));
    // Script elements come from loader.js only: h() refuses the tag in any case and in the SVG namespace, before making anything.
    const made = []; doc.createElement = (t) => { made.push(t); return mk(); }; doc.createElementNS = (ns, t) => { made.push(ns + ' ' + t); return mk(); };
    for (const tag of ['script', 'SCRIPT', 'Script', 'svg:script', 'svg:SCRIPT', ' script ', null, 7, 'svg:x:script', 'svg:svg:script', 'svg:xlink:script', 'svg:x:SCRIPT', 'x:script', 'svg:', 'svg:x:path']) assert.throws(() => core.h(tag, { src: 'x.js' }), /^Error: TAG_INVALID$/, String(tag));
    assert.deepEqual(made, [], 'nothing was made for a refused tag');
    assert.doesNotThrow(() => core.h('p', { title: 'script' })); assert.doesNotThrow(() => core.h('svg:path', { d: 'M0 0' }));
    assert.deepEqual(made, ['p', 'http://www.w3.org/2000/svg path']);
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

// ---------------------------------------------------------------- loader (P2-1a)
const freshLoader = () => { delete require.cache[require.resolve(R.newPath(LOADER))]; return R.requireNew(LOADER); };
// The views and results the layer hands only to old modules and engines.js (source rules): no facade member.
const INTERNAL = { prices: ['priceView', 'storeFacade'], store: ['storage'], qgv: ['scoreView', 'forEngines', 'engineInputs'] };
// Arguments for the non-async members that return a promise (each is called once on the real layer).
const SAMPLE = { 'data.static': ['entities.json'] };
test('the loader facade API is the real layer API: every member, each kind matching the function', async () => {
  const win = R.nodeWindow(); R.loadOld(win);
  const fresh = (n) => { delete require.cache[require.resolve(R.newPath(n))]; return R.requireNew(n); };
  const action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action }), prices = fresh('prices.js').create({ win, action, data });
  const store = fresh('store.js').create({ win, action, data }), qgv = fresh('qgv.js').create({ win, data, prices, action });
  const engines = fresh('engines.js').create({ win, action, data, prices, store, qgv }), real = { data, prices, store, qgv, engines };
  const L = freshLoader();
  assert.deepEqual(Object.keys(L.API), Object.keys(L.NAMESPACES));
  const firstParam = (fn) => { const src = String(fn); const m = /^(?:async\s+)?(?:function\b[^(]*|[A-Za-z_$][\w$]*\s*)?\(\s*([A-Za-z_$][\w$]*)/.exec(src) || /^(?:async\s+)?([A-Za-z_$][\w$]*)\s*=>/.exec(src); return m ? m[1] : null; };
  const thenable = (v) => !!v && typeof v.then === 'function';
  const checks = [];
  const walk = (spec, obj, where, internal = []) => {
    const keys = Object.keys(obj).filter((k) => !internal.includes(k));
    assert.deepEqual(Object.keys(spec).sort(), keys.sort(), where + ': facade members = layer members (less the internal views)');
    for (const [k, kind] of Object.entries(spec)) {
      const v = obj[k], at = where + '.' + k;
      if (kind && typeof kind === 'object') { assert.ok(v && typeof v === 'object', at + ' is a group'); walk(kind, v, at); continue; }
      if (kind === 'v') { assert.notEqual(typeof v, 'function', at + ' is a value'); continue; }
      assert.equal(typeof v, 'function', at + ' is a function');
      const isAsync = v.constructor.name === 'AsyncFunction', p0 = firstParam(v);
      if (k === 'subscribe') { assert.equal(kind, 'sub', at); continue; }
      assert.equal(p0 === 'event', kind === 'a', at + ': an action takes the event first (' + p0 + ')');
      if (isAsync) assert.equal(kind, 'p', at + ' is async');
      if (kind === 'p' && !isAsync) checks.push([at, () => v.apply(obj, SAMPLE[at] || []), true]);
      if (kind === 's') checks.push([at, () => v.apply(obj, []), false]);
    }
  };
  for (const [ns, spec] of Object.entries(L.API)) walk(spec, real[ns], ns, INTERNAL[ns] || []);
  for (const [ns, list] of Object.entries(INTERNAL)) for (const k of list) assert.ok(k in real[ns], ns + '.' + k + ' exists (internal)');
  // A promise member gives a promise; a getter never does (called on the real layer; a throw is fine for a getter).
  for (const [at, call, promise] of checks) {
    let v; try { v = call(); } catch (e) { assert.ok(!promise, at + ' threw instead of giving a promise: ' + e.message); continue; }
    if (thenable(v)) v.then(() => {}, () => {});
    assert.equal(thenable(v), promise, at + (promise ? ' gives a promise' : ' is synchronous'));
  }
});

// A fake page for the loader: script elements are recorded (src resolved like a browser's), the test runs them by firing 'load'
// / 'error', animation frames and idle callbacks run on the next turn, marks are recorded.
function fakePage({ hidden = false } = {}) {
  const win = new EventTarget(), body = { scripts: [], appendChild(el) { this.scripts.push(el); return el; } }, marks = [];
  const make = () => { const el = new EventTarget(); let src = ''; Object.defineProperty(el, 'src', { get: () => (src ? new URL(src, win.location.href).href : ''), set: (v) => { src = String(v); } }); el.async = true; return el; };
  Object.assign(win, { IS2: {}, location: { href: 'https://site.test/app/', origin: 'https://site.test' }, document: { visibilityState: hidden ? 'hidden' : 'visible', body, createElement: (t) => { assert.equal(t, 'script'); return make(); } },
    performance: { mark: (n) => marks.push(n) }, requestAnimationFrame: (f) => setImmediate(f), requestIdleCallback: (f) => setImmediate(f), setTimeout: (f, ms) => setTimeout(f, ms), marks, body });
  return win;
}
const tick = () => new Promise((r) => setImmediate(r));
async function settle(n = 6) { for (let i = 0; i < n; i++) await tick(); }
// Runs the inserted scripts: install(name) may set namespaces on IS2; outcome(name) → 'load' | 'error' | 'throw'.
function run(win, install = () => {}, outcome = () => 'load') {
  for (const el of win.body.scripts) {
    const name = new URL(el.src).pathname.split('/').pop(), o = outcome(name);
    if (o === 'error') { el.dispatchEvent(new Event('error')); continue; }
    install(name);// a file that throws may have installed its global before it threw
    if (o === 'throw') { const e = new Event('error'); e.filename = el.src; win.dispatchEvent(e); }
    el.dispatchEvent(new Event('load'));
  }
}
// A stand-in layer: records the calls the facades forward.
function standIn(calls) {
  const subs = [];
  return {
    data: { FILES: ['x.json'], ready: async () => 'ready-value', get: (n) => 'got ' + n, refresh: (e) => { calls.push(['refresh', e]); return 'refreshed'; }, subscribe: (fn, o) => { subs.push(fn); return () => { subs.splice(subs.indexOf(fn), 1); }; } },
    prices: { status: () => ({ google: { connected: false } }) }, store: { savePrefs: (e, v) => { calls.push(['savePrefs', e, v]); return { version: 1 }; }, marketQuotes: { count: async () => 0 } },
    qgv: { page: async () => 'page' }, engines: { target: { state: () => 'state' } }, emit: () => subs.forEach((f) => f('x')), subs };
}
const installAll = (win, layer) => (name) => { const ns = Object.entries(freshLoader().NAMESPACES).find(([, f]) => f === name); if (name === 'action.js') win.IS2.action = { run() {} }; if (ns) win.IS2[ns[0]] = layer[ns[0]]; };

test('loader: names are plain same-origin script names; install puts facades, ready, load and the markers on IS2', () => {
  const L = freshLoader();
  for (const bad of [['../x.js'], ['x.js?v=1'], ['https://x.example/x.js'], ['X.js'], ['x.css'], ['sub/x.js'], ['a.js', 'a.js'], [''], 'a.js'])
    assert.throws(() => L.create(fakePage(), { list: bad }), /LOADER_NAME_INVALID/, JSON.stringify(bad));
  for (const n of L.LOAD_ORDER) assert.match(n, /^[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.js$/);
  const win = fakePage(), I = L.create(win).install();
  assert.equal(I, win.IS2);
  for (const ns of Object.keys(L.NAMESPACES)) assert.ok(I[ns] && typeof I[ns] === 'object', ns + ' facade');
  assert.equal(I.loadState(), 'WAITING'); assert.equal(typeof I.load, 'function'); assert.ok(I.ready instanceof Promise);
  assert.deepEqual([I.NOT_READY, I.LOAD_FAILED], [{ state: 'NOT_READY', reason: 'LAYER_NOT_READY' }, { state: 'NOT_READY', reason: 'LOADER_FAILED' }]);
  assert.ok(Object.isFrozen(I.NOT_READY) && Object.isFrozen(I.data) && Object.isFrozen(I.store.backup));
  const kept = { data: { real: true } }; const w2 = fakePage(); w2.IS2 = { ...kept }; L.create(w2).install();
  assert.equal(w2.IS2.data, kept.data, 'a namespace already there is not replaced');
});

test('loader: facades before ready, nothing inserted before the first paint, async=false in list order, ready, forwarding', async () => {
  const L = freshLoader(), win = fakePage(), list = ['a.js', 'action.js', 'data.js', 'prices.js', 'store.js', 'qgv.js', 'engines.js'];
  const loader = L.create(win, { list }), I = loader.install(), F = { ...I }, calls = [], layer = standIn(calls), ev = { type: 'click' };
  // Before ready.
  assert.equal(I.data.FILES, I.NOT_READY); assert.equal(I.prices.status(), I.NOT_READY); assert.equal(I.store.prefs(), I.NOT_READY); assert.equal(I.engines.target.state(), I.NOT_READY);
  assert.throws(() => I.store.savePrefs(ev, {}), /^Error: LAYER_NOT_READY$/); assert.throws(() => I.data.refresh(ev), /LAYER_NOT_READY/);
  const early = [I.data.ready(), I.qgv.page(), I.store.marketQuotes.count()], order = [];
  early.forEach((p, i) => p.then((v) => order.push(i + ':' + v)));
  let got = 0; I.data.subscribe(() => { got++; }); const ac = new AbortController(); I.data.subscribe(() => { got += 100; }, { signal: ac.signal }); ac.abort();
  assert.throws(() => I.data.subscribe('x'), /SUBSCRIBER_INVALID/);
  // Nothing before the shell's first paint.
  let paint; win.IS2.firstPaint = new Promise((r) => { paint = r; });
  assert.equal(I.load(), I.ready); assert.equal(I.load(), I.ready, 'load() once');
  await settle(); assert.equal(win.body.scripts.length, 0, 'nothing inserted before the first paint'); assert.equal(I.loadState(), 'WAITING');
  paint(); await settle();
  assert.equal(I.loadState(), 'LOADING');
  assert.deepEqual(win.body.scripts.map((s) => s.src), list.map((n) => 'https://site.test/app/' + n), 'every listed file, same origin, in order');
  assert.ok(win.body.scripts.every((s) => s.async === false), 'async=false keeps the order');
  assert.deepEqual(order, [], 'promise members still wait');
  run(win, installAll(win, layer)); await I.ready; await settle();
  assert.equal(I.loadState(), 'READY'); assert.deepEqual(win.marks, ['is2-ready']);
  assert.deepEqual(order.sort(), ['0:ready-value', '1:page', '2:0'], 'promise members called before ready ran on the layer');
  layer.emit(); assert.equal(got, 1, 'the subscription made before ready is attached; the aborted one is not');
  // The layer replaced the facades on IS2; a facade a screen kept forwards.
  assert.equal(I.data, layer.data);
  assert.deepEqual([F.data.FILES, F.data.get('n'), F.prices.status().google.connected, F.engines.target.state()], [['x.json'], 'got n', false, 'state']);
  assert.deepEqual(F.store.savePrefs(ev, { v: 1 }), { version: 1 }); assert.deepEqual(calls, [['savePrefs', ev, { v: 1 }]], 'an action forwards its event as is (same tick)');
  assert.equal(await F.qgv.page(), 'page');
  const off = F.data.subscribe(() => { got += 10; }); layer.emit(); off(); layer.emit(); assert.equal(got, 1 + 1 + 10 + 1, 'subscribe after ready is the layer\'s own');
});

test('loader: failures reject IS2.ready with LOADER_FAILED <first file in list order> and put the refusing facades back', async () => {
  const L = freshLoader(), list = ['a.js', 'b.js', 'action.js', 'data.js', 'prices.js', 'store.js', 'qgv.js', 'engines.js'];
  const cases = [
    ['missing file', (n) => (n === 'b.js' || n === 'qgv.js' ? 'error' : 'load'), () => true, 'b.js'],
    ['an old module threw while it ran', (n) => (n === 'b.js' ? 'throw' : 'load'), () => true, 'b.js'],
    ['a layer file threw after installing', (n) => (n === 'prices.js' ? 'throw' : 'load'), () => true, 'prices.js'],
    ['installed nothing', () => 'load', (n) => n !== 'store.js', 'store.js'],
    ['no action gate', () => 'load', (n) => n !== 'action.js', 'action.js'],
  ];
  for (const [label, outcome, installs, file] of cases) {
    const win = fakePage(), I = L.create(win, { list }).install(), F = { ...I }, layer = standIn([]);
    win.IS2.firstPaint = Promise.resolve();
    const early = I.qgv.page().then(() => 'OK', (e) => e.message);
    I.load(); await settle();
    const put = installAll(win, layer); run(win, (n) => { if (installs(n)) put(n); }, outcome);
    const message = await I.ready.then(() => 'OK', (e) => e.message);
    assert.equal(message, 'LOADER_FAILED ' + file, label);
    assert.equal(await I.ready.catch((e) => e.file), file);
    assert.equal(await early, 'LOADER_FAILED ' + file, label + ': a promise member called before rejects too');
    assert.equal(I.loadState(), 'FAILED'); assert.deepEqual(win.marks, ['is2-load-failed']);
    for (const ns of Object.keys(L.NAMESPACES)) assert.equal(win.IS2[ns], F[ns], label + ': the facade is back on IS2 (' + ns + ')');
    assert.equal(I.data.FILES, I.LOAD_FAILED); assert.equal(I.prices.status(), I.LOAD_FAILED);
    assert.throws(() => I.store.savePrefs({}, {}), new RegExp('^Error: LOADER_FAILED ' + file.replace('.', '\\.') + '$'));
    assert.equal(await I.data.ready().then(() => 'OK', (e) => e.message), 'LOADER_FAILED ' + file);
    let got = 0; I.data.subscribe(() => { got++; }); layer.emit(); assert.equal(got, 0, label + ': a subscription keeps nothing');
  }
});

test('loader: a hidden page loads at once (it paints nothing); the screen files touch no layer namespace while they load', async () => {
  const L = freshLoader(), win = fakePage({ hidden: true }), I = L.create(win, { list: ['a.js'] }).install();
  win.IS2.firstPaint = new Promise(() => {});
  I.load(); await settle();
  assert.equal(win.body.scripts.length, 1, 'no wait for a paint that never comes');
  delete require.cache[require.resolve(R.newPath('core.js'))];
  const core = R.requireNew('core.js'), touched = [];
  const parts = { head: () => null, section: () => null, card: () => null, pending: () => null, more: () => null };
  const IS2 = new Proxy({ ...core, parts }, { get(t, k) { if (['data', 'qgv', 'prices', 'store', 'engines', 'action', 'ready'].includes(k)) touched.push(k); return t[k]; } });
  for (const name of [...LANES, 'screen-search.js', 'screen-menus.js', 'screen-detail.js']) vm.runInNewContext(fs.readFileSync(R.newPath(name), 'utf8'), { window: { IS2 }, Object }, { filename: name });
  assert.deepEqual(touched, [], 'screens read the layer at render time only (through the facades before IS2.ready)');
});

test('the first screen never waits for the fonts: every @font-face swaps (or is optional), nothing is preloaded', () => {
  const css = fs.readFileSync(R.newPath('app.css'), 'utf8'), faces = [...css.matchAll(/@font-face\s*\{([^}]*)\}/g)].map((m) => m[1]);
  assert.equal(faces.length, 3);
  for (const f of faces) assert.match(f, /font-display:\s*(?:swap|optional)\s*;/, f.slice(0, 60));
  assert.doesNotMatch(R.newIndex(), /rel="(?:preload|modulepreload|prefetch|preconnect)"/, 'no preload: the fonts and the layer come after the first paint');
});
