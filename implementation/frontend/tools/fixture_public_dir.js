'use strict';
// Builds a local public-data directory for development and the browser test: the offline cockpit build (real, deterministic
// files: assets, actual-catalog.json, ...) plus SYNTHETIC daily files taken from the cockpit's own test fixtures. Synthetic
// values are test shapes, not market data. Usage: node fixture_public_dir.js OUT_DIR [--ledger active|not-started]
const fs = require('node:fs'), path = require('node:path'), { execFileSync } = require('node:child_process');
const IMPL = path.resolve(__dirname, '../..'), TOOLS = path.join(IMPL, 'tools');
const { EMPTY } = require(path.join(TOOLS, 'empty_public_screens.js'));
const QF = require(path.join(TOOLS, 'qgv_v2_fixture.js'));
const SD = require(path.join(TOOLS, 'sec_disclosures_fixture.js'));
const NF = require(path.join(TOOLS, 'news_signals_fixture.js'));

const A = 'a'.repeat(64), B = 'b'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };

function macroScreen(now) {
  const at = now.toISOString(), p = structuredClone(EMPTY['macro-screen.json']);
  p.state = 'LIVE'; p.as_of = at; p.sources = [{ agency: 'BLS', sha256: A, acquired_at: at }, { agency: 'TREASURY', sha256: B, acquired_at: at }];
  const L = p.data.macro_lights_v1.lights;
  Object.assign(L.employment, { state: 'LIVE', lit: false, reason: 'NOT_LIT', as_of: '2026-09', inputs: [{ sha256: A, acquired_at: at }], values: { period: '2026-09', avg3: 4.13, low12: 4.1, low12_count: 11, gap: 0.03 } });
  Object.assign(L.inflation, { state: 'LIVE', lit: false, reason: 'NOT_LIT', as_of: '2026-09', inputs: [{ sha256: A, acquired_at: at }], values: { period: '2026-09', base_period: '2025-09', yoy: 0.037 } });
  Object.assign(L.curve, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2026-10-16', inputs: [{ sha256: B, acquired_at: at }], values: { date: '2026-10-16', ten_year: 4.2, three_month: 4.5, spread: -0.3, run_days: 25 } });
  return p;
}

function types(now) {
  const at = now.toISOString(), p = structuredClone(EMPTY['company-types-pricefree.json']);
  p.state = 'LIVE'; p.as_of = at; p.sources = [{ agency: 'SEC_COMPANYFACTS', sha256: A, acquired_at: at }, { agency: 'SEC_SUBMISSIONS', sha256: B, acquired_at: at }];
  const live = (m) => ({ state: 'LIVE', config_version: 'type_config/1', source_hashes: { companyfacts: A, submissions: B }, memberships: m });
  p.data.companies.nvda = live({ growth: 0.8, quality: 0.35, cyclical: null, defensive: null });
  p.data.companies.msft = live({ growth: 0.2, quality: 0.6, cyclical: null, defensive: null });
  return p;
}

function v2Row(date, i0, basis) {
  const companies = {};
  IDS.forEach((id, i) => { companies[id] = (i + i0) % 4 ? { state: 'LIVE', Q: { score: 40 + i, coverage: 'PARTIAL', missing_factor_count: 1 }, G: { score: 60 - i, coverage: 'PARTIAL', missing_factor_count: 2 } } : { state: 'NOT_AVAILABLE', Q: { score: null, coverage: 'BLOCKED', missing_factor_count: 5 }, G: { score: null, coverage: 'BLOCKED', missing_factor_count: 5 } }; });
  return { date, version: 'forward_validation/v2', strategy: 'QGV_STANDARD_V2', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: { portfolio_id: 'TARGET', version: 'v0', root_sha256: A, total_units: 10000, weights_units: { ...UNITS } }, qg_as_of: date + 'T22:10:00+00:00', qg_screen_state: 'LIVE', companies, source_sha256: { 'sec-qgv2.json': A, 'actual-catalog.json': A }, created_at: date + 'T22:30:00+00:00', basis };
}

function ledger(kind) {
  const p = { schema_version: 2, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status: 'NOT_STARTED', as_of: '2026-10-16T22:48:00+00:00', strategy: 'QGV_STANDARD_V2', calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true, target: { portfolio_id: 'TARGET', version: 'v0' },
    versions: { 'forward_validation/v1': [], 'forward_validation/v1+dcf_v1_default': [], 'forward_validation/v2': [] },
    version_status: { 'forward_validation/v1': { state: 'NOT_STARTED', v_included: false, reason_codes: [] }, 'forward_validation/v1+dcf_v1_default': { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] }, 'forward_validation/v2': { state: 'NOT_STARTED', v_included: false, reason_codes: [] } } };
  if (kind !== 'active') return p;
  const calc = 'qgv2-calc/2026-10-17.1';
  const prep = { calc_version: null, q_scored: 300, g_scored: 290, population: { n: 310, id: '0123456789abcdef' }, acquired: ['2026-10-14', '2026-10-19'], evaluation: { eligible: false, status: 'PREPARATORY', reasons: ['Q_BELOW_454', 'G_BELOW_454', 'CALC_VERSION_MISSING'] }, segment: 'NONE' };
  const primary = (d) => ({ calc_version: calc, q_scored: 470, g_scored: 466, population: { n: 480, id: 'fedcba9876543210' }, acquired: ['2026-10-14', d], evaluation: { eligible: true, status: 'PRIMARY', reasons: [] }, segment: calc });
  p.status = 'ACTIVE'; p.as_of = '2026-10-21T22:31:00+00:00';
  p.versions['forward_validation/v2'] = [v2Row('2026-10-19', 0, prep), v2Row('2026-10-20', 1, primary('2026-10-20')), v2Row('2026-10-21', 2, primary('2026-10-21'))];
  p.version_status['forward_validation/v1'].state = 'ACTIVE';
  p.version_status['forward_validation/v2'].state = 'ACTIVE';
  return p;
}

function main() {
  const out = path.resolve(process.argv[2] || '');
  if (!process.argv[2]) throw Error('usage: node fixture_public_dir.js OUT_DIR [--ledger active|not-started]');
  const kind = process.argv.includes('--ledger') ? process.argv[process.argv.indexOf('--ledger') + 1] : 'not-started';
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  execFileSync('python3', [path.join(TOOLS, 'build_pages_cockpit.py'), '--out', out], { stdio: 'ignore' });
  const now = new Date();
  const files = {
    'sec-qgv2.json': QF.strictPayload(),
    'macro-screen.json': macroScreen(now),
    'company-types-pricefree.json': types(now),
    'sec-disclosures.json': SD.payload(now),
    'sec-filing-windows.json': SD.filingWindows(now),
    'news-signals.json': NF.payload(now),
    'company-classification.json': JSON.parse(fs.readFileSync(path.join(IMPL, 'tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live,
    'forward-validation-ledger.json': ledger(kind),
  };
  for (const [name, body] of Object.entries(files)) fs.writeFileSync(path.join(out, name), JSON.stringify(body));
  process.stdout.write('fixture public dir ' + out + ' (synthetic daily files, ledger ' + kind + ')\n');
}

if (require.main === module) main();
module.exports = { macroScreen, types, ledger };
