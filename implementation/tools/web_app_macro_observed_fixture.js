'use strict';
// 매크로 관측 자료 (feature 4.1.3, Codex #477 macro-current-query/1) test helpers for web_app_macro_observed_node_test.js and
// web_app_macro_observed_browser_test.js.
//  - cases(): the SYNTHETIC current-query files in implementation/tests/fixtures/macro_current_query_v1_synthetic.json (sha256
//    pinned in SHA256), made by running Codex's own tools/macro_observed_timeline.py of #477 (efc8715f) with python3 -I in a temp
//    dir on made-up captures (the file's _synthetic header says how): main (curve 2025-11 revised and held, BLS LNS14000000 failed
//    after a success, CES3000000007 stale, G17 2025-12 known only by an upper bound, FOMC event series, Census key not
//    configured, DOL held for terms), late (the same cache read 200 days later: five stale) and never (no capture at all).
//  - SENTINEL: the made-up values all carry the digits 7319NN, so a test can show that no observed value reaches the page.
//  - mutate(name, fn): a deep copy of one case changed by fn (for the refusals).
// SYNTHETIC VALUES ONLY; nothing here is written to a public file.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { ROOT } = require('./web_app_reuse');

const FILE = path.join(ROOT, 'implementation/tests/fixtures/macro_current_query_v1_synthetic.json');
const SHA256 = 'b1c6e8e26fb93046c6fdee5c7bc515eedc5e8d6bd46c29c035977768ab764650';
const SENTINEL = /7319\d\d/;
const bundle = () => JSON.parse(fs.readFileSync(FILE, 'utf8'));
const sha = () => crypto.createHash('sha256').update(fs.readFileSync(FILE)).digest('hex');
const cases = () => bundle().cases;
function mutate(name, fn) { const p = structuredClone(cases()[name]); fn(p); return p; }
const IDS = { curve: 'TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN', labor: 'BLS:LNS14000000', hours: 'BLS:CES3000000007', ip: 'FED:G17:IP.B50001.S',
  gdp: 'BEA:NIPA:A191RL:Q', fomc: 'FED:FOMC:TARGET_RANGE', dol: 'DOL:ETA539:INITIAL_CLAIMS_SA', census: 'CENSUS:M3:NXA:NO:SA', temp: 'BLS:CES6056132001' };
module.exports = Object.freeze({ FILE, SHA256, SENTINEL, IDS, bundle, sha, cases, mutate });
