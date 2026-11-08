'use strict';
// 공통 분류 (DC-48, owner 2026-11-07) test helpers (tools/web_app_classification_node_test.js, web_app_classification_browser_test.js).
//  - MAIN: tests/fixtures/common_classification_main/main_fixture.json, the output of Codex's own functions on Codex's own cases
//    (tools/common_classification_main_fixture.py; pytest tests/test_common_classification_main_fixture.py checks it byte for byte),
//    SHA-256 pinned here. Nothing in it is written by Main.
//  - HANDOFF: Codex's handoff files (docs/research/common_classification, #516 9343b5e6) with the SHA-256 of its manifest.
//  - payload(...): the IS2.classification source payload a test puts in place of source() — parts of the fixture as they are.
// SYNTHETIC VALUES ONLY; nothing here is written to a public file.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { ROOT } = require('./web_app_reuse');

const MAIN_PATH = path.join(ROOT, 'implementation/tests/fixtures/common_classification_main/main_fixture.json');
const MAIN_SHA256 = '4e405f90864574eba4f0dba64e9d90e01cdaef3a20c7fce1d5e1a9e0ff280949';
const HANDOFF_DIR = path.join(ROOT, 'implementation/docs/research/common_classification');
const HANDOFF_SHA256 = { 'CONTRACT.md': '00bccc2c38ae03e037ff820d6010a251b87f35983dadf1986217d0a1989258ea',
  'fixtures.json': '526cbf85defddbc4b255ea8dc5194ccab034c5eb9b317ef94142b5338c26ebcf', 'dictionary.json': '9ae49c5f849535d325aaa64689da9fa61147347a9c8f8dafcf4055c0ef6d5776' };
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const main = () => JSON.parse(fs.readFileSync(MAIN_PATH, 'utf8'));
const mainSha = () => sha(MAIN_PATH);
const handoffSha = (name) => sha(path.join(HANDOFF_DIR, name));
const codexFixtures = () => JSON.parse(fs.readFileSync(path.join(HANDOFF_DIR, 'fixtures.json'), 'utf8'));
// The CLI run's four parts and the dictionary (the bundle that carries one record per company in every part).
const bundle = (M = main()) => ({ view: M.bundle.view, qgv_links: M.bundle.qgv_links, technical: M.bundle.technical, macro: M.bundle.macro, dictionary: M.dictionary });
// A technical case: its view, its technical projection and (normal only) its macro projection.
const technicalCase = (name, M = main()) => { const c = M.technical_cases[name]; return { view: c.view, technical: c.technical, macro: c.macro, dictionary: M.dictionary }; };
const recordCase = (name, M = main()) => { const c = M.record_cases[name]; return { view: c.view, macro: c.macro, dictionary: M.dictionary }; };
// The same Codex runs on the browser page's Universe504 codes (only the input company ids renamed; Codex computed the rest).
const universe = (M = main()) => M.universe;
const uBundle = (M = main()) => ({ ...M.universe.bundle, dictionary: M.dictionary });
const uTechnical = (M = main()) => { const t = M.universe.technical_normal; return { view: t.view, technical: t.technical, macro: t.macro, dictionary: M.dictionary }; };
const uRecord = (name, M = main()) => { const c = M.universe.record_cases[name]; return { view: c.view, macro: c.macro, dictionary: M.dictionary }; };
module.exports = { universe, uBundle, uTechnical, uRecord, MAIN_PATH, MAIN_SHA256, HANDOFF_DIR, HANDOFF_SHA256, sha, main, mainSha, handoffSha, codexFixtures, bundle, technicalCase, recordCase };
