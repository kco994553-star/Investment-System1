'use strict';
/* Owner instruction 2026-10-19: '개인 프리셋 결과의 ‘공식’ 표시를 수정한다. 공식 가중치 사용 여부, 개인 설정 여부, 기기 가격 사용 여부,
   중앙 게시 결과 여부를 구분한다. 문구를 고치기 위해 계산 결과를 바꾸지 않는다.' (D11: a personal result says 개인.)
   On the real user path at 390 and 1280, with the strictly valid SYNTHETIC sec-qgv2.json and the SYNTHETIC central V publication
   (qgv_official_fixture.js; DC-31: the screens show only the central V, no device price), for three S06 settings: the official default (balanced, gate on), a personal preset (growth) and the gate off (balanced):
   1. S06, the company detail, the Universe company page, the playbook candidates, the V panel and the radar carry the
      provenance attributes (data-qgv-weights / -setting / -prices / -source) and words from QgvScores.provenance: the rank is
      called 공식 only on the official default profile, else '개인 프리셋 순위 (Universe 기준)'.
   2. N10/N15/N20 keep saying 공식 가중치 (official default profile) and say that the S06 order may differ under a personal preset.
   3. Values are unchanged: the official values are the publication's (QgvScores.officialPage); a personal setting equals a direct
      QgvScores.compute({publication, weights: officialWeights(preset), gate}) recompute; the official values after a round trip
      through the personal settings are the same as before. */
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const SETTINGS = [
  { key: 'official', preset: 'balanced', gate: true, weights: 'OFFICIAL', setting: 'NONE', source: 'CENTRAL', id: 'qgv-v2/balanced/gate-on', text: '공식 가중치 · 가격 없음 · 중앙 게시(qgv-official.json)', rank: 'Universe 공식 QGV 순위' },
  { key: 'growth', preset: 'growth', gate: true, weights: 'PERSONAL', setting: 'PRESET', source: 'DEVICE_COMPUTED', id: 'qgv-v2/growth/gate-on', text: '개인 프리셋(성장 친화) · 가격 없음 · 기기 계산', rank: '개인 프리셋 순위 (Universe 기준)' },
  { key: 'gate-off', preset: 'balanced', gate: false, weights: 'PERSONAL', setting: 'GATE_OFF', source: 'DEVICE_COMPUTED', id: 'qgv-v2/balanced/gate-off', text: '개인 프리셋(균형 · 관문 끔) · 가격 없음 · 기기 계산', rank: '개인 프리셋 순위 (Universe 기준)' }];
const attrs = (page, sel) => page.evaluate((s) => { const n = document.querySelectorAll(s);return n.length === 1 ? Object.fromEntries([...n[0].attributes].filter((a) => a.name.startsWith('data-')).map((a) => [a.name, a.value])) : { __count: n.length }; }, sel);
const prov = (a) => [a['data-qgv-weights'], a['data-qgv-setting'], a['data-qgv-prices'], a['data-qgv-source'], a['data-qgv-profile']];
// The value reference: the official page result itself (official default), else a direct personal recompute from the published
// factor scores with the preset's official weights and the gate, on the identities of the shared result.
const engine = (page, s) => page.evaluate(async ({ preset, gate }) => {
  const inputs = publicScreens[Qgv2Inputs.FILE], P = leaderPage, off = preset === QgvV2.DEFAULT_PRESET && gate === QgvV2.GATE_DEFAULT, id = QgvV2.VERSION + '/' + preset + '/gate-' + (gate ? 'on' : 'off');
  const S = off ? P.computed : QgvScores.compute({ identities: P.identities, v2Inputs: inputs, quotes: {}, official: P.official, gate, weights: QgvV2.officialWeights(preset), typeWeights: true, publication: QgvScores.pagePublication().publication });
  const one = (r) => off ? { rank: r.rank, d: r.primary } : { rank: r.personal_rank, d: r.personal };
  return { profile: id, same: leaderScores().profile.id === id, rows: Object.fromEntries(Object.entries(S.rows).map(([k, r]) => [k, { ticker: r.ticker, uc: r.universe_code ?? null, rank: one(r).rank, total: one(r).d.total, v: one(r).d.v }])), by_code: { ...S.official.by_code }, tin: S.official.target_in_universe.map((x) => x.company_id) };
}, { preset: s.preset, gate: s.gate });
const tableRows = (page) => page.locator('[data-leaderboard-table] tbody tr[data-leaderboard-row]').evaluateAll((rs) => rs.map((r) => [r.dataset.leaderboardRow, r.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank ?? null, r.querySelector('[data-leaderboard-total]')?.dataset.leaderboardTotal ?? null]));
const modelRows = (page) => page.locator('[data-model-portfolio] [data-model-row]').evaluateAll((rs) => rs.map((r) => [r.dataset.modelRow, r.dataset.modelRank, r.dataset.modelIn]));
async function settle(page) { await page.waitForFunction(() => typeof leaderPage === 'object' && leaderPage && leaderPage.source === 'PUBLICATION' && leaderPage.inputs_match === true); }
async function setProfile(page, s) {
  await page.evaluate(() => { location.hash = 'leaderboard'; });await page.locator('[data-leaderboard-table]').waitFor();
  await page.locator('[data-qgv2-preset="' + s.preset + '"]').click();await page.locator('[data-qgv2-preset="' + s.preset + '"][aria-pressed="true"]').waitFor();
  const box = page.locator('[data-qgv2-gate]');if ((await box.isChecked()) !== s.gate) { if (s.gate) await box.check();else await box.uncheck(); }
  await page.waitForFunction((x) => (qgv2Profile.preset ?? QgvV2.DEFAULT_PRESET) === x.preset && (qgv2Profile.gate ?? QgvV2.GATE_DEFAULT) === x.gate, s);await settle(page);
  await page.waitForFunction((id) => document.querySelector('[data-qgv-provenance="S06"]')?.dataset.qgvProfile === id, s.id);
}
const show = (v) => (Math.round(v * 10) / 10).toFixed(1);

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const day1 = F.strictPayload();
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(day1) }));
      await O.routeOfficial(context);
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'OPEN';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();await settle(page);await page.locator('[data-leaderboard-rank]').first().waitFor();
        let model0 = null, official0 = null, shownOfficial0 = null;
        for (const s of [...SETTINGS, SETTINGS[0]]) {
          const round = official0 !== null && s.key === 'official';
          phase = 'S06 ' + s.key;await setProfile(page, s);const E = await engine(page, s), R = E.rows, personal = s.weights === 'PERSONAL';
          assert.equal(E.same, true, 'S06 shows the ' + s.id + ' result');assert.equal(E.profile, s.id);
          // 3. Values: every S06 rank and total = the engine's for this setting.
          const shown = await tableRows(page);
          for (const [id, rank, total] of shown) { assert.equal(rank, Number.isInteger(R[id].rank) ? String(R[id].rank) : null, s.key + ' ' + id + ' rank');assert.equal(total, Number.isFinite(R[id].total) ? show(R[id].total) : 'NOT_AVAILABLE', s.key + ' ' + id + ' total'); }
          if (personal) assert.ok(Object.keys(R).some((id) => R[id].total !== official0[id].total), s.key + ' really is another result (labels follow it)');
          if (s.key === 'official') { if (round) assert.deepEqual(shown, shownOfficial0, 'official S06 values after the personal round trip = before');else shownOfficial0 = shown; }
          // 1. S06 labels and attributes.
          const b = await attrs(page, '[data-qgv-provenance="S06"]');assert.deepEqual(prov(b), [s.weights, s.setting, 'NONE', s.source, s.id]);
          assert.equal(await page.locator('[data-qgv-provenance="S06"]').textContent(), s.text);
          assert.match(await page.locator('[data-leaderboard-population]').textContent(), personal ? / · 개인 프리셋 평가$/ : / · 공식 평가$/);
          const sc = await attrs(page, '[data-leaderboard-rank-scope]'), scText = await page.locator('[data-leaderboard-rank-scope]').textContent();
          assert.deepEqual(prov(sc), [s.weights, s.setting, 'NONE', s.source, s.id]);
          if (personal) { assert.ok(scText.includes('순위는 개인 프리셋 순위(Universe 기준 · 공식 QGV 순위 아님)로, '), scText);assert.ok(!scText.includes('Universe 공식 QGV 순위'), 'no 공식 rank under ' + s.key); }
          else assert.ok(scText.includes('순위는 Universe 공식 QGV 순위로, '), scText);
          const ranked = Object.values(R).filter((r) => Number.isInteger(r.rank)).length;
          assert.match(await page.locator('[data-leaderboard-counts]').textContent(), new RegExp((personal ? '개인 프리셋 순위 ' : '공식 순위 ') + ranked + '개'));
          assert.equal(await page.locator('[data-leaderboard-explore-option="ranked"]').textContent(), (personal ? '개인 프리셋 순위 ' : '공식 QGV 순위 ') + ranked);
          await page.locator('[data-leaderboard-explore-option="ranked"]').click();await page.locator('[data-leaderboard-explore="ranked"]').waitFor();
          assert.equal(await page.locator('[data-leaderboard-list-title="RANKED"]').textContent(), personal ? '개인 프리셋 순위 (Universe 기준 · V 산출 기업)' : '공식 QGV 순위 (V 산출 기업)');
          assert.equal((await attrs(page, '[data-leaderboard-list-title="RANKED"]'))['data-qgv-weights'], s.weights);
          await page.locator('[data-leaderboard-explore-option="all"]').click();await page.locator('[data-leaderboard-explore="all"]').waitFor();
          // 2. N10/N15/N20: always the official default profile and the same selection.
          phase = 'N ' + s.key;if ((await page.locator('[data-model-portfolio]').getAttribute('open')) === null) await page.locator('[data-model-portfolio] > summary').click();
          const m = await modelRows(page);if (model0 === null) model0 = m;assert.deepEqual(m, model0, 'N sets unchanged by ' + s.key);assert.ok(m.length > 0);
          const mp = await attrs(page, '[data-model-provenance]');assert.deepEqual(prov(mp), ['OFFICIAL', 'NONE', 'NONE', 'CENTRAL', 'qgv-v2/balanced/gate-on']);
          assert.equal(mp['data-model-provenance'], personal ? 'S06_PERSONAL' : 'S06_OFFICIAL');
          assert.equal(await page.locator('[data-model-provenance]').textContent(), '공식 가중치 · 가격 없음 · 중앙 게시(qgv-official.json)' + (personal ? ' · 위 S06 순서는 개인 프리셋 순위라 이 공식 순서와 다를 수 있습니다' : ''));
          // V panel: the publication's coverage, whatever the S06 setting (DC-31).
          assert.equal(await page.locator('[data-v-coverage="READY"] [data-central-basis]').getAttribute('data-central-basis'), O.PUB.publication_id);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide horizontal scroll (S06)');
          if (process.env.LABELS_SHOTS) await page.locator('[data-leaderboard-screen]').screenshot({ path: process.env.LABELS_SHOTS + '/s06-' + width + '-' + s.key + '.png' });
          // Company detail of a ranked TARGET in the Universe.
          phase = 'COMPANY ' + s.key;const tgt = E.tin.find((id) => Number.isInteger(R[id].rank)), uni = Object.keys(R).find((id) => Number.isInteger(R[id].rank) && !E.tin.includes(id) && R[id].uc === id);
          await page.evaluate((id) => { location.hash = 'company/' + id; }, tgt);await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').waitFor();
          await page.waitForFunction((id) => document.querySelector('[data-qgv-rank-scope]')?.dataset.qgvProfile === id, s.id);
          assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').textContent(), String(R[tgt].rank), tgt + ' rank = engine');
          const cr = await attrs(page, '[data-qgv-rank-scope]');assert.deepEqual(prov(cr), [s.weights, s.setting, 'NONE', s.source, s.id]);
          const crText = await page.locator('[data-qgv-rank-scope]').textContent();assert.ok(crText.startsWith(s.rank + ' · '), crText);assert.ok(crText.endsWith(s.text), crText);if (personal) assert.ok(!crText.includes('공식 QGV 순위'), crText);
          assert.deepEqual(prov(await attrs(page, '[data-company-card="qgv"] [data-qgv-provenance="COMPANY"]')), [s.weights, s.setting, 'NONE', s.source, s.id]);
          assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv-provenance="COMPANY"]').textContent(), 'QGV 계산 근거: ' + s.text);
          // The radar: Q·G as published (sec-qgv2.json), V as published in the central publication, whatever the preset.
          await page.locator('[data-sr-provenance="V"]').first().waitFor();
          assert.deepEqual(prov(await attrs(page, '[data-company-card="radar"] [data-sr-provenance="QG"]')).slice(0, 4), ['OFFICIAL', undefined, 'NONE', 'PUBLISHED']);
          assert.equal(await page.locator('[data-company-card="radar"] [data-sr-provenance="QG"]').textContent(), 'Q·G: 공식 가중치 · 가격 없음 · 중앙 게시(sec-qgv2.json)');
          assert.deepEqual(prov(await attrs(page, '[data-company-card="radar"] [data-sr-provenance="V"]')).slice(0, 4), ['OFFICIAL', undefined, 'NONE', 'CENTRAL']);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide horizontal scroll (company)');
          if (width === 390 && process.env.LABELS_SHOTS) await page.locator('[data-company-card="qgv"]').screenshot({ path: process.env.LABELS_SHOTS + '/company-' + s.key + '.png' });
          // Universe company page of a ranked Universe code.
          phase = 'UNIVERSE ' + s.key;await page.evaluate((c) => { location.hash = 'company/' + encodeURIComponent(c); }, uni);
          await page.waitForFunction((id) => document.querySelector('[data-uc-provenance]')?.dataset.qgvProfile === id, s.id);
          assert.ok(Math.abs(Number(await page.locator('[data-uc-total]').getAttribute('data-uc-total')) - R[uni].total) <= 1e-9, uni + ' total = engine');
          assert.deepEqual(prov(await attrs(page, '[data-uc-provenance]')), [s.weights, s.setting, 'NONE', s.source, s.id]);
          { const t = await page.locator('[data-uc-provenance]').textContent();assert.ok(t.startsWith(s.text + ' · ' + s.rank + ' ' + R[uni].rank + ' · 반영 축 '), t);if (personal) assert.ok(!t.includes('공식 QGV 순위'), t); }
          assert.deepEqual(prov(await attrs(page, '[data-uc-axis="Q"]')).slice(0, 4), ['OFFICIAL', 'NONE', 'NONE', 'PUBLISHED']);
          assert.deepEqual(prov(await attrs(page, '[data-uc-axis="V"]')).slice(0, 4), ['OFFICIAL', 'NONE', 'NONE', 'CENTRAL']);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide horizontal scroll (Universe page)');
          // Playbook candidates: the order of the shared result, labelled by its profile.
          phase = 'CANDIDATES ' + s.key;await page.evaluate(() => { location.hash = 'playbook'; });const writer = page.locator('[data-target-v1]');
          await page.waitForFunction((id) => document.querySelector('[data-target-ranking] > p')?.dataset.qgvProfile === id, s.id);
          const cp = await attrs(page, '[data-target-ranking] > p');assert.deepEqual(prov(cp), [s.weights, s.setting, 'NONE', s.source, s.id]);assert.equal(cp['data-target-rank-label'], s.weights);
          const cpText = await writer.locator('[data-target-ranking] > p').textContent();
          assert.ok(cpText.includes(personal ? ' · 개인 프리셋 순위(Universe 기준 · V 포함) 순 · 공식 QGV 순위 아님 · ' : ' · 공식 QGV 순위(V 포함) 순 · '), cpText);assert.ok(cpText.endsWith(' · ' + s.text), cpText);
          const cand = await writer.locator('[data-target-ranking] [data-target-rank-row]').evaluateAll((rs) => rs.map((r) => [r.dataset.targetRankRow, r.cells[1].textContent, r.cells[2].textContent]));
          const byTicker = Object.fromEntries(Object.entries(R).map(([id, r]) => [r.ticker, id])), order = Object.keys(R).filter((id) => Number.isInteger(R[id].rank) && R[id].uc).sort((a, b) => R[a].rank - R[b].rank);
          assert.deepEqual(cand.filter((c) => c[1] !== '—').map((c) => c[0]), order.slice(0, 30).map((id) => R[id].ticker), s.key + ' candidates = the engine order');
          for (const [t, rank, total] of cand.filter((c) => c[1] !== '—')) { assert.equal(rank, String(R[byTicker[t]].rank));assert.equal(total, R[byTicker[t]].total.toFixed(1)); }
          if (s.key === 'official' && !round) official0 = R;
          if (round) assert.deepEqual(R, official0, 'official engine values after the round trip = before');
        }
        assert.deepEqual(external, []);assert.equal(errors, 0);
        pass++;console.log('PASS official/personal labels ' + width + ' (official · growth · gate off; synthetic fixture + synthetic central publication)');
      } catch (e) { fail++;console.log('FAIL official/personal labels ' + width + ' ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
