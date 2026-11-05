'use strict';
// 3.1.2 고른 기업의 지표 test helpers (tools/web_app_tech_display_node_test.js, tools/web_app_tech_display_browser_test.js).
//  - FIXTURE: implementation/tests/fixtures/technical_offline_display_synthetic.json (sha256 pinned in SHA256): the output of
//    Codex's own tools/technical_display_offline.py at #478 419add34, unchanged, run on SYNTHETIC bars by
//    tools/build_tech_display_fixture.py, wrapped as {data_kind: 'SYNTHETIC', description, symbols, display}.
//  - source(display): the IS2.techDisplay.source() answer a test puts in place of the real NONE.
//  - relabel(display, map): a copy whose SYN_* series symbols are a test company's ticker (in memory only, so the chosen company
//    finds its series); no value is touched.
// SYNTHETIC VALUES ONLY; nothing here is written to a public file.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { ROOT } = require('./web_app_reuse');

const PATH = path.join(ROOT, 'implementation/tests/fixtures/technical_offline_display_synthetic.json');
const SHA256 = '559e2eb968b522f12f8b45e8d267d0a5a1187e6b290acf9e1e5b80065758515d';
const text = () => fs.readFileSync(PATH, 'utf8');
const fixture = () => JSON.parse(text());
const display = () => fixture().display;
const sha = () => crypto.createHash('sha256').update(fs.readFileSync(PATH)).digest('hex');
const source = (payload) => ({ state: 'OK', code: null, payload, data_kind: 'SYNTHETIC', text: '' });
function relabel(payload, map) {
  const out = JSON.parse(JSON.stringify(payload));
  for (const s of out.series) if (Object.prototype.hasOwnProperty.call(map, s.symbol)) s.symbol = map[s.symbol];
  return out;
}
module.exports = { PATH, SHA256, text, fixture, display, sha, source, relabel };
