'use strict';
// 공통 사전 판독기 (owner 2026-11-22: reader moved alone from #526 7b4a805b; no screen connection). Synthetic only.
//  - web_app/common-taxonomy.js is Codex's current_taxonomy() as is: equal to Codex's public fixture taxonomy.json (pinned SHA-256);
//    TELECOMMUNICATIONS = 통신서비스; names and definitions only, no classification effect.
// The assertions are the common-taxonomy.js part of #526's web_app_industry_macro_node_test.js 'one dictionary' case, unchanged; the
// screen lines of that case (classification.js / sector-qgv.js) and industry-macro.js stay in the research Drafts.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const R = require('./web_app_reuse');
const T = R.requireNew('common-taxonomy.js');
const FIX = path.join(__dirname, '..', 'tests', 'fixtures');

test('one dictionary: the embedded current taxonomy is Codex\'s, names come from it', () => {
  const raw = fs.readFileSync(path.join(FIX, 'macro_industry_evidence', 'taxonomy.json'));
  assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), '0804c7c54ebc34064129de45a08fafcb782286a22869aa99cfbd2cf889cf712d', 'Codex fixture pinned (#437 6721800433)');
  assert.deepEqual(JSON.parse(JSON.stringify(T.DATA)), JSON.parse(raw.toString('utf8')));
  assert.equal(T.NAME, '투자시스템 공통 10섹터'); assert.equal(T.VERSION, 'investment-system-common-10-sector/1');
  assert.equal(T.sectorName('TELECOMMUNICATIONS'), '통신서비스');
  assert.equal(T.DATA.sectors.length, 10); assert.equal(T.DATA.classification_effect, 'NONE_DISPLAY_DEFINITION_ONLY');
  assert.ok(Object.isFrozen(T.DATA) && Object.isFrozen(T.DATA.sectors[0]));
  assert.equal(T.sectorName('NOT_A_SECTOR'), 'NOT_A_SECTOR', 'an unknown id is shown as the id');
});
