'use strict';
// Runs every test of a manifest (the same file run_js_tests.sh reads), spread over N groups that run at the same time; each
// group runs its tests one after another. Tests named in the solo list run afterwards, alone (they assert time limits).
// No test is added, skipped or changed: the run fails unless every manifest entry ran exactly once and passed.
//   node run_js_tests_parallel.js <manifest> --groups N [--solo <list>] [--weights <file>]
// Output per test is printed in one piece when it ends, with the same lines run_js_tests.sh prints
// (RUN <name>, the test's own output, ::error ... CI_TEST_FAILED <name> exit=<code>), then MANIFEST_OK tests=<count>.
// After a failure no new test starts; tests already running finish.
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i < 0 ? d : args[i + 1]; };
const manifest = args[0], groups = Number(opt('--groups', '1'));
const TOOLS = path.join('implementation', 'tools');
function names(file) {
  return fs.readFileSync(file, 'utf8').split('\n').map((l) => l.split('#')[0].trim()).filter(Boolean);
}
function die(msg) { console.log(msg); process.exit(1); }
if (!manifest || !Number.isInteger(groups) || groups < 1 || groups > 4) die('USAGE run_js_tests_parallel.js <manifest> --groups 1..4');
const all = names(manifest);
if (!all.length) die('EMPTY_TEST_MANIFEST');
for (const n of all) if (n.includes('/') || n.startsWith('..')) die('INVALID_TEST_NAME ' + n);
if (new Set(all).size !== all.length) die('DUPLICATE_TEST_NAME');
const soloFile = opt('--solo', null), solo = soloFile ? names(soloFile) : [];
for (const n of solo) if (!all.includes(n)) die('STALE_SOLO_ENTRY ' + n);
const weight = new Map();
const weightFile = opt('--weights', null);
if (weightFile) for (const n of names(weightFile)) { const [k, v] = n.split(/\s+/); if (k && Number(v) > 0) weight.set(k, Number(v)); }
// Longest first onto the least loaded group (weights are seconds from a past run; they only decide the order).
const shared = all.filter((n) => !solo.includes(n));
const plan = Array.from({ length: groups }, () => ({ load: 0, tests: [] }));
for (const n of [...shared].sort((a, b) => (weight.get(b) || 30) - (weight.get(a) || 30) || all.indexOf(a) - all.indexOf(b))) {
  const g = plan.reduce((m, x) => (x.load < m.load ? x : m));
  g.tests.push(n); g.load += weight.get(n) || 30;
}
let failed = null, passed = 0;
const ran = new Set();
function runOne(name) {
  return new Promise((resolve) => {
    const started = Date.now(), chunks = [];
    const child = spawn(process.execPath, [path.join(TOOLS, name)], { stdio: ['ignore', 'pipe', 'pipe'], env: process.env });
    child.stdout.on('data', (c) => chunks.push(c)); child.stderr.on('data', (c) => chunks.push(c));
    child.on('close', (code, signal) => {
      ran.add(name);
      const status = code === null ? 1 : code;
      process.stdout.write('RUN ' + name + '\n' + Buffer.concat(chunks).toString());
      if (status === 0) { passed++; console.log('TEST_SECONDS ' + name + ' ' + Math.round((Date.now() - started) / 1000)); }
      else {
        console.log('::error file=implementation/tools/' + name + ',title=CI_TEST_FAILED::CI_TEST_FAILED ' + name + ' exit=' + status);
        if (!failed) failed = { name, status };
      }
      resolve();
    });
  });
}
async function runGroup(tests) { for (const n of tests) { if (failed) return; await runOne(n); } }
(async () => {
  console.log('PARALLEL_GROUPS ' + groups + ' ' + plan.map((g) => g.tests.length + 'tests/' + Math.round(g.load) + 's').join(' ') + ' solo=' + solo.length);
  await Promise.all(plan.map((g) => runGroup(g.tests)));
  for (const n of solo) { if (failed) break; await runOne(n); }
  if (failed) process.exit(failed.status || 1);
  if (ran.size !== all.length || passed !== all.length) die('MANIFEST_INCOMPLETE ran=' + ran.size + ' of ' + all.length);
  console.log('MANIFEST_OK tests=' + passed);
})();
