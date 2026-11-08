'use strict';
// New frontend · feature 8.1 구조 트리 (web_app/screen-tree-live.js): the stage words the tree shows for the added numbers
// (2.1.8 · 2.2.7 · 2.4.6 · 3.5 · 4.5.x.1) and for the common classification are FUNCTION_STATUS's own words.
//  - For every STAGES entry the status table (docs/SPEC/FUNCTION_STATUS.md) has exactly one row whose first cell starts with that
//    id, and each of the five values appears in that row's own 구현: / 검증: / 통합: / 배포: / 실환경: part (the text up to the
//    next stage name). A word that went stale in either place fails here instead of showing a wrong stage.
//  - The added numbers that have a status row all carry a stage, so a new row is not left without one on the tree.
//  - The tree's 9.1 note is the main-table 9.1 row's own words for the research scope block.
//  - No stage says 준비 중 · Draft any more (the old fixed notes are gone).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const R = require('./web_app_reuse');

const ROOT = path.resolve(__dirname, '..', '..');
const STATUS = fs.readFileSync(path.join(ROOT, 'docs', 'SPEC', 'FUNCTION_STATUS.md'), 'utf8');
const TREE = fs.readFileSync(R.newPath('screen-tree-live.js'), 'utf8');

// The stage table as it stands in the screen file (between its two marks), run on its own: the file hands only its filler to
// the skeleton (web_app_reuse_node_test.js), so the table is not exported.
function load() {
  const m = TREE.match(/\/\/ stage-table:begin\n([\s\S]*?)\/\/ stage-table:end\n/);
  assert.ok(m, 'the stage-table marks');
  const out = {};
  vm.runInNewContext(m[1] + '\nout.STAGES=STAGES;out.STAGE_NAMES=STAGE_NAMES;out.stageText=stageText;', { out, Object });
  return out;
}
const rowsOf = (id) => STATUS.split('\n').filter((l) => l.startsWith('| ' + id + ' ') || l.startsWith('| ' + id + '(') || l.startsWith('| ' + id + ' ·'));
// The part of a row after "<name>: " up to the next " · <other name>:" (or the cell end).
function part(row, name, names) {
  const cell = row.split(' | ')[1] || '';
  const at = cell.indexOf(name + ': ');
  if (at < 0) return null;
  let rest = cell.slice(at + name.length + 2), end = rest.length;
  for (const n of names) { const i = rest.indexOf(' · ' + n + ': '); if (i >= 0 && i < end) end = i; }
  return rest.slice(0, end);
}

test('every tree stage is the status row\'s own word, stage by stage', () => {
  const T = load();
  assert.deepEqual([...T.STAGE_NAMES], ['구현', '검증', '통합', '배포', '실환경']);
  const ids = Object.keys(T.STAGES);
  assert.ok(ids.length >= 10);
  const policy = ['4.5.1.1', '4.5.1.2', '4.5.2.1', '4.5.3.1', '4.5.4.1'];
  for (const id of ids) {
    // The five 4.5.x.1 numbers share one row (it starts with 4.5.1.1 and names the other four).
    const key = policy.includes(id) ? '4.5.1.1' : id;
    const rows = rowsOf(key);
    assert.equal(rows.length, 1, id + ': one status row');
    if (policy.includes(id)) assert.ok(rows[0].split(' | ')[0].includes(id), id + ': named in the shared 4.5 row');
    T.STAGE_NAMES.forEach((name, i) => {
      const got = part(rows[0], name, T.STAGE_NAMES);
      assert.ok(got !== null, id + ': the row has ' + name);
      assert.ok(got.includes(T.STAGES[id][i]), id + ' ' + name + ': "' + T.STAGES[id][i] + '" in "' + got + '"');
    });
    const shown = T.stageText(id);
    assert.ok(!/[`*]/.test(shown), id + ': markdown marks dropped on screen');
    assert.ok(!/준비 중 · Draft/.test(shown));
  }
  assert.equal(T.stageText('9.9.9'), null, 'no entry → no stage');
});

test('the added numbers with a status row all carry a stage; the old 준비 중 · Draft notes are gone', () => {
  const T = load();
  for (const id of ['2.1.8', '2.2.7', '2.4.6', '3.5', '4.5.1.1', '공통 분류']) assert.ok(T.STAGES[id], id);
  assert.ok(!/준비 중 · Draft #5(06|07|10|11)/.test(TREE));
  assert.ok(!/\b(DISC|POLICY)\)/.test(TREE));
});

test('the 9.1 note is the 9.1 row\'s own words for the research scope block', () => {
  const note = TREE.match(/L\('9\.1\.6','결과 보고'\)\],null,'([^']+)'\]/);
  assert.ok(note, '9.1 note');
  // 9.1 has a row in the main status table and one in the later layer table; the main table comes first.
  const rows = rowsOf('9.1');
  assert.ok(rows.length >= 1);
  assert.ok(rows[0].includes(note[1]), '9.1 row says ' + note[1]);
});
