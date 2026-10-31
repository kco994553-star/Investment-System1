'use strict';
// Synthetic public files for the new frontend's 3. 매크로 screen tests (web_app_macro_browser_test.js). Not market data, not
// real statistics: every value is made up and only has to pass the old readers' own validation (PublicScreens.validate with
// MacroLights.requirePublicBlock, MacroEvidence.validate, SecQgv2, ClassificationScreens).
//  - macroScreen(): the NOT_AVAILABLE macro-screen.json of an offline build (tools/fixtures/empty_public_screens.json) with three
//    public lights (employment and curve lit, inflation not: 경고, 3 of 5 lights have data; the same lights as the home test) and
//    one raw axis (Labor, published 4.6 % -> 0.046) LIVE; every other axis, the 8×6 cells and the observations stay empty.
//  - evidence(): the synthetic multi-run macro-evidence.json (tests/fixtures/macro_evidence/browser_payload.json, written by
//    tests/macro_evidence_fixture.py): 13 indicators, 14 realtime events, E14 held for unverified terms.
//  - emptyEvidence() / emptyScreen() / classification(): the offline build's NOT_AVAILABLE files, served explicitly so a deploy
//    build that carries live data does not change the test.
//  - qgv(): the strict sec-qgv2.json fixture (tools/qgv_v2_fixture.js). A valid file without any industry_group would need every
//    row (and the target rows' scores) recomputed, so the test reaches that state by stubbing the layer's read result instead.
const fs = require('node:fs');
const path = require('node:path');
const { EMPTY } = require('./empty_public_screens.js');
const F = require('./qgv_v2_fixture.js');

const A = 'a'.repeat(64), B = 'b'.repeat(64), AT = '2026-01-01T00:00:00+00:00';
function macroScreen() {
  const p = structuredClone(EMPTY['macro-screen.json']);
  p.state = 'LIVE'; p.sources = [{ agency: 'BLS', sha256: A, acquired_at: AT }, { agency: 'TREASURY', sha256: B, acquired_at: AT }];
  const L = p.data.macro_lights_v1.lights;
  Object.assign(L.employment, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2025-12', inputs: [{ sha256: A, acquired_at: AT }], values: { period: '2025-12', avg3: 4.6, low12: 4.0, low12_count: 12, gap: 0.6 } });
  Object.assign(L.inflation, { state: 'LIVE', lit: false, reason: 'NOT_LIT', as_of: '2025-12', inputs: [{ sha256: A, acquired_at: AT }], values: { period: '2025-12', base_period: '2024-12', yoy: 0.03 } });
  Object.assign(L.curve, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2025-12-31', inputs: [{ sha256: B, acquired_at: AT }], values: { date: '2025-12-31', ten_year: 4.2, three_month: 4.5, spread: -0.3, run_days: 25 } });
  Object.assign(p.data.raw_axes_v0.axes.Labor, { state: 'LIVE', value: '0.046', period: '2025-12', published_value: '4.6', acquired_at: AT, source_sha256: A, reason_codes: [] });
  return p;
}
const emptyScreen = () => structuredClone(EMPTY['macro-screen.json']);
const evidence = () => JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/macro_evidence/browser_payload.json'), 'utf8'));
const emptyEvidence = () => structuredClone(EMPTY['macro-evidence.json']);
const classification = () => structuredClone(EMPTY['company-classification.json']);
const qgv = () => F.strictPayload();
// The industry groups the fixture's sec-qgv2.json rows carry, in the classification config order, with their names.
function groups(p = qgv()) {
  const cfg = classification().data.industry_config.groups, have = new Set(Object.values(p.records).map((r) => r && r.industry_group).filter((g) => typeof g === 'string' && g));
  return cfg.filter((g) => have.has(g.id)).map((g) => ({ id: g.id, name: g.name }));
}
module.exports = Object.freeze({ macroScreen, emptyScreen, evidence, emptyEvidence, classification, qgv, groups });
