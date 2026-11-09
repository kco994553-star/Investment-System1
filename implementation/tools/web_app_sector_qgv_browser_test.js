'use strict';
// Sector QGV (feature 2.2) on #/qgv section 1.2 in a real browser at 1440×1000 and 390×844, with the development engine route:
// the site answers POST sector-qgv-engine with Codex's common engine #505 (tools/sector_qgv_engine_bridge.py as a child process,
// SYNTHETIC inputs only). Owner 2026-11-06 「섹터 QGV 실제 연결」: 설정 변경 → 공통 엔진 실행 → 결과 판독 → 전후 미리보기 → 저장·복원.
//  - Nothing is sent when #/qgv opens; 「계산 엔진 연결」 asks for the context and the scope's factor list.
//  - Badges as words (기본값 · 초기 설정 / 추천 / 선택됨 / 계산 기능 준비 중 / 산식 적용 부적합), PER / PBR search, replace.
//  - A preview is an engine call: the rows and ranks shown are the engine's answer for that config (checked against a direct
//    engine call), before → after, the original denominator; save only for the shown, current preview; reload keeps it.
//  - Gate: 관문 통과 / V 총점 반영 제외 / 판정 불가 (no final score, no rank); a refused input keeps the last good result.
//  - Cancel, restore, a bank change that stays in banks, a late answer dropped, the published site without the route.
//  - Owner 2026-11-07: the flow is ① 10섹터 기본값 (base preset id / version of the scope) → ② 내 설정; 공격형·균형형·수비형 are
//    not offered; 기본값 복원 names and shows the base preset id / version; an old leaderboard weight tree (DeviceProfiles v2)
//    on the device is listed as 이전 설정 호환, still loads in 1.1.6 (today's data, not a past-result replay), never rewritten.
//  - Owner 2026-11-07: 2.2.7 「섹터 QGV 설정(요소·가중치)」 on the body; 원본 참조 / 내 설정; N<20 = 요소 점수 미산출; 「최신 입력에 설정 적용」
//    (a new result) vs 「과거 입력으로 결과 재현」 (the engine's replay); a record the route does not hold = 재현 입력 연결 전; bytes kept.
//  - Phone: no horizontal overflow, 44 px controls. Boundaries: no request leaves the origin, the engine route is POST only,
//    nothing stored but the one sector key, no console error, CSP 0. SQ_SHOTS=<dir> saves screenshots (deviceScaleFactor 2).
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const E = require('./web_app_sector_qgv_engine.js');
const CCX = require('./web_app_classification_fixture.js');
const S = require('../src/investment_system/product/web_app/sector-qgv.js');

const NOW = '2026-11-06T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json'];
const KEY = 'investment.web.v2.sector-qgv-user-config';
const LEGACY_KEY = 'investment.web.v1.profile-drafts-v2';
const DP = require('../src/investment_system/product/web_assets/device-profiles.js');
const LEGACY = JSON.stringify(DP.saveV2(DP.emptyV2(), { name: '공격형 v0.1', weights: DP.candidateFor('aggressive').weights }, new Date('2026-10-18T00:00:00Z')));
const BASE = 'sector-qgv-default/0.1.0';
const SHOTS = process.env.SQ_SHOTS || null;
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const eng = E.start();
  const fixtures = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } };
  const s = await site.start({ fixtures, posts: { [E.ROUTE]: eng.route } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = phone ? '390' : '1440';
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const posts = []; page.on('request', (r) => { if (r.url().endsWith('/' + E.ROUTE)) posts.push(r.method()); });
      const B = '[data-sq-body]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const tableRows = () => page.locator('[data-lb-table] tbody tr[data-row]').count();
      const factorIds = () => page.$$eval(B + ' [data-sq-factor]', (n) => n.map((x) => x.dataset.sqFactor));
      const ready = () => page.locator(B + ' [data-sq-role]').first().waitFor();
      const setAxis = async (a, value) => { await page.fill(B + ' [data-k=sq-axis-' + a + ']', value); await page.locator(B + ' [data-k=sq-axis-' + a + ']').press('Tab'); };
      const preview = async () => { const before = eng.calls.length; await page.locator(B + ' [data-k=sq-preview]').click();
        await page.waitForFunction((b) => { const p = document.querySelector(b + ' [data-sq-preview]'), m = document.querySelector(b + ' [data-sq-msg]'), btn = document.querySelector(b + ' [data-k=sq-preview]');
          return btn && btn.textContent !== '계산 중…' && (p || m); }, B); return eng.calls.slice(before); };
      const connect = async () => { await page.locator(B + ' [data-k=sq-connect]').click(); await ready(); };
      const ranks = () => page.$$eval(B + ' [data-sq-row]', (n) => Object.fromEntries(n.map((x) => [x.dataset.sqRow, x.querySelector('[data-sq-rank]').innerText.split('→').pop().trim()])));

      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      const boardRows = await tableRows();
      await page.locator(B + ' [data-sq-state=IDLE]').waitFor();
      assert.ok((await text(B)).includes('계산 엔진 연결 전')); assert.deepEqual(posts, [], 'nothing sent when the page opens');
      ok(tag + ' opening sends nothing; 계산 엔진 연결 전; official board ' + boardRows + ' rows');

      // ---------------- connect: context + factor list from the engine; badges, search, replace
      phase = tag + ' connect';
      const c0 = eng.calls.length; await connect();
      assert.deepEqual(eng.calls.slice(c0).map((c) => c.op), ['context', 'view']);
      const all = await text(B);
      assert.ok(!/\b(null|undefined|NaN)\b/.test(all), 'no null / undefined text');
      for (const w of ['모델 sector-qgv-default/0.1.0', '엔진 sector-qgv-engine/0.1.0', '계산 Codex 공통 엔진', '관문 official-q-percentile-required/1', '이 기기(이 브라우저)에만 저장', '기업 유형 태그는 점수에 영향 없음'])
        assert.ok(all.includes(w), w);
      const flow = B + ' [data-sq-flow]';
      assert.equal(await page.locator(flow).getAttribute('data-sq-flow'), 'SECTOR_DEFAULT'); assert.equal(await page.locator(flow).getAttribute('data-sq-base'), BASE + '@0.1.0');
      assert.equal(await text(flow + ' [data-sq-step=SECTOR_DEFAULT]'), '① 10섹터 기본값 · 정보기술·일반 · ' + BASE + ' v0.1.0');
      assert.equal(await text(flow + ' [data-sq-step=MY_SETTING]'), '② 내 설정 · 저장 전');
      assert.equal(await page.locator(flow + ' [data-sq-step=SECTOR_DEFAULT]').getAttribute('aria-current'), 'step');
      assert.doesNotMatch(all, /공격형|균형형|수비형|이전 설정 호환/, 'no old profile offered (none saved on this device)');
      assert.equal(await page.locator(B + ' [data-sq-legacy]').count(), 0);
      await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'cfo_mcap', 'sales_ev'], 'IT general V from the engine preset');
      const ep = B + ' [data-sq-factor=ep_ttm_diluted]';
      assert.deepEqual(await page.$$eval(ep + ' [data-sq-badge]', (n) => n.map((x) => x.dataset.sqBadge)), ['BASE', 'RECOMMENDED', 'SELECTED']);
      assert.ok((await text(ep)).includes('기본값 · 초기 설정') && (await text(ep)).includes('✓ 선택됨') && (await text(ep)).includes('추천'), 'badges are words');
      await page.fill('#sq-q', 'PER');
      assert.equal(await page.locator(B + ' [data-sq-cand=ep_ttm_diluted] button').isDisabled(), true, 'PER = the selected E/P');
      assert.ok((await text(B + ' [data-sq-cand=ep_fy1]')).includes('예상 PER'));
      await page.fill('#sq-q', 'FCFF');
      assert.ok((await text(B + ' [data-sq-cand=fcff_ev]')).includes('계산 기능 준비 중'));
      assert.equal(await page.locator(B + ' [data-sq-cand=fcff_ev] button').isDisabled(), true, 'pending: not selectable');
      await page.fill('#sq-q', 'PBR');
      assert.equal(await page.locator(B + ' [data-sq-cand=common_bp] button').isDisabled(), false, 'PBR selectable');
      await page.locator(B + ' [data-k=sq-tab-Q]').click(); await page.fill('#sq-q', '보통주 ROE');
      assert.ok((await text(B + ' [data-sq-cand=roe_common_ttm]')).includes('산식 적용 부적합'));
      await page.fill('#sq-q', ''); await page.locator(B + ' [data-k=sq-tab-V]').click();
      await page.selectOption(B + ' [data-k="sq-replace-sales_ev"]', 'common_bp');
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'cfo_mcap', 'common_bp']);
      assert.equal(await page.locator(flow).getAttribute('data-sq-flow'), 'MY_SETTING', 'an edit is the 내 설정 step');
      ok(tag + ' flow ① 10섹터 기본값 (' + BASE + ' v0.1.0) → ② 내 설정, no old profile offered; engine context and factor list; badges as words; PER / PBR search; pending and unfit not selectable; PBR replaces EV/Sales');

      // ---------------- preview = engine recalculation; save; reload
      phase = tag + ' preview';
      assert.equal(await page.locator(B + ' [data-k=sq-save]').isDisabled(), true, 'no save before a preview');
      let calls;
      if (phone) calls = await preview();
      else { const before = eng.calls.length; await page.locator(B + ' [data-k=sq-preview]').focus(); await page.keyboard.press('Enter'); await page.locator(B + ' [data-sq-preview]').waitFor(); calls = eng.calls.slice(before); }
      assert.deepEqual(calls.map((c) => [c.op, c.input_id, c.ok]), [['preview', 'NORMAL', true]], 'one engine preview call');
      const sum = await text(B + ' [data-sq-summary]');
      assert.match(sum, /미리보기 · 공통 엔진 재계산/);
      // 2.2.7 × 공통 분류 (owner 2026-11-08, Codex GROUP_JOIN.md): no record set → its own words, no row matched; Codex's CLI run
      // (main fixture bundle: qgv links of ANOTHER preview) → 미리보기 다름, never mixed into these rows. (Matching = node test.)
      await page.locator(B + ' [data-sq-cc=NONE]').waitFor();
      assert.ok((await text(B + ' [data-sq-cc]')).includes('공통 분류 · 공통 분류 기록 미연결 · 분류 대조 안 함'));
      await page.evaluate((p) => { const I = window.IS2; I.__realCC = I.__realCC || I.classification;
        I.classification = Object.freeze({ ...I.__realCC, source: () => Promise.resolve({ state: 'OK', code: null, payload: p }) }); return I.classification.load(); }, CCX.bundle());
      await page.locator(B + ' [data-k=sq-only]').click(); await page.locator(B + ' [data-sq-cc=PREVIEW_NOT_LINKED]').waitFor();
      const cc = await text(B + ' [data-sq-cc]');
      assert.ok(cc.includes('이 미리보기는 분류 연결 기록의 미리보기와 다름 · 분류 기록과 섞지 않음') && cc.includes('preview_id'), cc);
      assert.equal(await page.locator(B + ' [data-sq-cc-record]').count(), 0, 'no row matched to a record');
      await page.locator(B + ' [data-k=sq-only]').click();
      await page.evaluate(() => { const I = window.IS2; I.classification = I.__realCC; return I.classification.load(); });
      ok(tag + ' 2.2.7 preview × 공통 분류: 미연결 and 다른 미리보기 each in their own words, no row mixed');
      // The synthetic input has no common B/P observation: the engine leaves V and the total unscored (strict), never 0.
      assert.match(sum, /총점 산출 · 전 20 \/ 20 → 후 0 \/ 20 · 원래 모집단 전체 기준/); assert.match(sum, /V 0 \/ 20/); assert.match(sum, /필수 요소 결측 · 총점 미산출 20/);
      assert.ok((await text(B + ' [data-sq-factor=common_bp]')).includes('자료 일부 부족 0/20 · 선택 가능'), 'availability from the engine coverage');
      assert.ok((await text(B + ' [data-sq-row=company-000]')).includes('미산출 · PBR / 보통주 B/P 자료 없음'));
      assert.equal(await page.locator(B + ' [data-k=sq-save]').isDisabled(), false, 'an unscored result can still be saved: it is the engine\'s answer');
      await page.selectOption(B + ' [data-k="sq-replace-common_bp"]', 'ebitda_ev');
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'cfo_mcap', 'ebitda_ev']);
      assert.equal(await page.locator(B + ' [data-sq-stale]').count(), 1, 'the PBR preview is stale now');
      calls = await preview();
      assert.deepEqual(calls.map((c) => [c.op, c.input_id, c.ok]), [['preview', 'NORMAL', true]]);
      assert.match(await text(B + ' [data-sq-summary]'), /총점 산출 · 전 20 \/ 20 → 후 20 \/ 20 · 원래 모집단 전체 기준/);
      assert.equal(await page.locator(B + ' [data-sq-row]').count(), 20);
      const shown = await ranks();
      assert.ok(!/\b(null|undefined|NaN)\b/.test(await text(B)), 'no null / undefined text with a preview');
      assert.equal(await page.locator(B + ' [data-k=sq-save]').isDisabled(), false);
      await page.locator(B + ' [data-k=sq-save]').click();
      assert.ok((await text(B + ' [data-sq-msg]')).startsWith('이 기기에 저장함 · 엔진 저장 기록'));
      const stored = JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY));
      assert.equal(S.validateSaved(stored).ok, true); assert.equal(stored.preview_id, await page.locator(B + ' [data-sq-preview]').getAttribute('data-sq-preview'));
      assert.deepEqual(Object.keys(stored.config.scoped_overrides), ['INFORMATION_TECHNOLOGY|GENERAL']);
      // The ranks on the screen are the engine's for this config (a direct call with the stored config gives the same).
      const direct = await eng.call(S.request('preview', { config: stored.config, before_config: stored.config, input_id: 'NORMAL' }));
      assert.deepEqual(shown, Object.fromEntries(direct.after.result_rows.map((r) => [r.company_id, String(r.rank)])), 'screen ranks = engine ranks');
      assert.ok(Object.values(await page.$$eval(B + ' [data-sq-row] [data-sq-rank]', (n) => n.map((x) => x.innerText))).some((t) => { const [a, b] = t.split('→').map((x) => x.trim()); return a !== b; }), 'some rank moved before → after');
      assert.equal(await tableRows(), boardRows, 'official board unchanged');
      await page.reload(); await page.evaluate(() => window.IS2.ready); await page.locator(B + ' [data-sq-state=IDLE]').waitFor(); await connect();
      assert.ok((await text(B + ' [data-sq-saved=OK]')).includes(stored.preview_id.slice(0, 12)));
      assert.equal(await page.locator(flow).getAttribute('data-sq-flow'), 'MY_SETTING'); assert.equal(await text(flow + ' [data-sq-step=MY_SETTING]'), '② 내 설정 · 이 기기에 저장됨');
      await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'cfo_mcap', 'ebitda_ev'], 'saved on this device');
      ok(tag + ' preview is one engine call each (PBR: V 0 / 20 strict, never 0; EV/EBITDA: 20 / 20, ranks = engine), saved record of that preview, kept after reload');

      // ---------------- stale, invalid sum, cancel, restore
      phase = tag + ' cancel';
      await preview();
      await setAxis('Q', '31'); await page.locator(B + ' [data-sq-axis-sum="10100"]').waitFor();
      await page.locator(B + ' [data-sq-fault=SUM]').waitFor();
      assert.equal(await page.locator(B + ' [data-k=sq-preview]').isDisabled(), true, 'bad sum: no preview');
      assert.equal(await page.locator(B + ' [data-sq-stale]').count(), 1, 'the older preview is hidden as stale');
      assert.equal(await page.locator(B + ' [data-k=sq-save]').isDisabled(), true, 'no save of a stale preview');
      await page.locator(B + ' [data-k=sq-cancel]').click(); await ready();
      assert.equal(await page.inputValue(B + ' [data-k=sq-axis-Q]'), '30');
      await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'cfo_mcap', 'ebitda_ev'], 'cancel = last saved');
      await page.locator(B + ' [data-k=sq-restore]').click(); await ready(); await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'cfo_mcap', 'sales_ev'], 'restore = the engine default preset');
      assert.equal(await text(B + ' [data-sq-msg]'), '기본값 복원 · 10섹터 기본값 ' + BASE + ' v0.1.0 · 정보기술·일반 · 저장 전까지 기기 설정은 그대로', 'restore names the base preset id / version');
      assert.equal(await page.locator(flow).getAttribute('data-sq-flow'), 'SECTOR_DEFAULT'); assert.equal(await page.locator(flow).getAttribute('data-sq-base'), BASE + '@0.1.0');
      assert.equal(await page.locator(B + ' [data-k=sq-axis-Q]').inputValue(), '30', 'base axis weights back');
      assert.equal(JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY)).preview_id, stored.preview_id, 'not saved until the user saves');
      ok(tag + ' a changed config hides the stale preview and blocks save; bad sum blocks preview; cancel = saved; restore = base preset ' + BASE + ' v0.1.0');

      // ---------------- a bank change stays in banks
      phase = tag + ' bank';
      await page.selectOption('#sq-sector', 'FINANCIALS'); await ready(); await page.selectOption('#sq-template', 'BANK'); await ready();
      await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'common_bp']);
      await page.selectOption(B + ' [data-k="sq-replace-common_bp"]', 'tangible_common_bp');
      await preview();
      assert.ok((await text(B + ' [data-sq-preview]')).includes('이 섹터·회계모형의 행 없음'), 'the synthetic input has no banks: said, not 0');
      await page.locator(B + ' [data-k=sq-save]').click();
      const st2 = JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY));
      assert.deepEqual(Object.keys(st2.config.scoped_overrides), ['FINANCIALS|BANK']);
      assert.deepEqual(st2.config.scoped_overrides['FINANCIALS|BANK'].axes.V.other_value.factors, { tangible_common_bp: 10000 });
      await page.selectOption('#sq-template', 'INSURANCE'); await ready(); await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['ep_ttm_diluted', 'common_bp'], 'insurance keeps the engine default');
      ok(tag + ' bank override saved alone; insurance keeps the engine default');

      // ---------------- gate: pass / V excluded / unknown; a refused input keeps the last good result
      phase = tag + ' gate';
      await page.selectOption('#sq-sector', 'INFORMATION_TECHNOLOGY'); await ready(); await page.selectOption('#sq-template', 'GENERAL'); await ready();
      await page.selectOption('#sq-input', 'GATE_UNKNOWN'); await preview();
      const unk = B + ' [data-sq-row=company-000]';
      assert.equal(await page.locator(unk).getAttribute('data-sq-status'), 'GATE_UNKNOWN');
      assert.ok((await text(unk)).includes('관문 판정 불가 · 최종 점수·순위 없음'));
      assert.equal((await text(unk + ' [data-sq-rank]')).split('→').pop().trim(), '없음', 'no rank');
      assert.ok((await text(B + ' [data-sq-summary]')).includes('총점 산출 · 전 19 / 20 → 후 19 / 20'));
      await page.selectOption('#sq-input', 'GATE_EXCLUDED'); await preview();
      const ex = await text(B + ' [data-sq-row=company-000] [data-sq-gate]');
      assert.ok(ex.startsWith('관문: V 총점 반영 제외 · 남은 축 비례 재배분 · 기업 탈락·자료 미수집 아님 · 적용 Q ') && !/\bV\b/.test(ex.split(' · 적용 ')[1]), ex); // the applied weights name no V
      assert.equal(await page.locator(B + ' [data-sq-row=company-001] [data-sq-gate]').getAttribute('data-sq-gate'), 'PASS');
      await page.selectOption('#sq-input', 'FAILED'); await preview();
      assert.ok((await text(B + ' [data-sq-msg]')).includes('미리보기 거부 · 입력 거부 · 회사 ID 중복 · 이전 결과는 그대로'));
      await page.selectOption('#sq-input', 'GATE_EXCLUDED');
      assert.equal(await page.locator(B + ' [data-sq-preview]').count(), 1, 'the last good preview is still the shown one for its input');
      ok(tag + ' gate pass / V excluded / unknown without score or rank; a refused input keeps the last good preview');

      // ---------------- a late answer to an older request never wins
      phase = tag + ' order';
      await page.selectOption('#sq-input', 'NORMAL');
      const dropped = Number(await page.locator(B + ' [data-sq-dropped]').getAttribute('data-sq-dropped'));
      eng.hold(1); await page.locator(B + ' [data-k=sq-preview]').click();
      await page.waitForFunction(() => document.querySelector('[data-k=sq-preview]').textContent === '계산 중…');
      await setAxis('Q', '31'); await setAxis('G', '24'); await page.locator(B + ' [data-sq-axis-sum="10000"]').waitFor();
      eng.release();
      await page.waitForFunction((d) => Number(document.querySelector('[data-sq-dropped]').dataset.sqDropped) === d + 1, dropped);
      assert.equal(await page.locator(B + ' [data-sq-preview]').count(), 0, 'the answer to the older config is not shown');
      assert.equal(await page.locator(B + ' [data-k=sq-preview]').isDisabled(), false, 'a new preview can be asked');
      await preview(); assert.equal(await page.locator(B + ' [data-sq-preview]').count(), 1);
      ok(tag + ' request order: the answer to the older config is dropped');

      // ---------------- owner 2026-11-07: 2.2.7 label; 원본 참조 vs 내 설정; N<20; 최신 입력에 설정 적용 vs 과거 입력으로 결과 재현; no overwrite
      phase = tag + ' 2.2.7';
      assert.equal(await text(B + ' [data-sq-feature]'), '2.2.7 섹터 QGV 설정(요소·가중치)');
      const raw = await page.evaluate((k) => localStorage.getItem(k), KEY), rec = JSON.parse(raw);
      assert.equal(await text(B + ' [data-sq-origin]'), '원본 참조 · ' + BASE + ' v0.1.0 · 정보기술·일반 기본값 · 바꾸지 않음');
      assert.equal(await page.locator(B + ' [data-sq-mine]').getAttribute('data-sq-mine'), rec.canonical_config_hash);
      assert.equal(await text(B + ' [data-sq-mine]'), '내 설정 · 설정 ID device · sector-qgv-config/1 · 설정 해시 ' + rec.canonical_config_hash.slice(0, 12) + ' (설정 버전 필드 없음 · 해시로 식별) · 기준 ' + BASE + ' · 적용 범위 1곳: 금융·은행');
      await page.selectOption('#sq-input', 'PEER_SAMPLE_SMALL'); await preview();
      const small = B + ' [data-sq-preview] [data-sq-row=company-000]', N20 = '요소 점수 미산출 · 유효 비교 기업 N<20 (N=19)';
      assert.ok((await text(small)).includes(N20)); assert.ok(!(await text(small)).includes('필수 요소 결측'), 'not told as missing');
      assert.equal((await text(small + ' [data-sq-rank]')).split('→').pop().trim(), '없음', 'no rank');
      assert.ok((await text(B + ' [data-sq-reasons]')).includes(N20 + ' 19'));
      assert.doesNotMatch(await text(small), /\b0\.0\b/, 'never a 0 score');
      // 과거 입력으로 결과 재현: the replay op on the saved record (its original NORMAL input), engine-confirmed.
      let c1 = eng.calls.length; await page.locator(B + ' [data-k=sq-run-reproduce]').click(); await page.locator(B + ' [data-sq-run-state=REPRODUCED]').waitFor();
      assert.deepEqual(eng.calls.slice(c1).map((c) => [c.op, c.ok]), [['replay', true]]);
      const rp = await text(B + ' [data-sq-run-state=REPRODUCED]');
      assert.ok(rp.startsWith('과거 입력으로 결과 재현됨 · 엔진 확인') && rp.includes('원래 미리보기 ' + rec.preview_id.slice(0, 12)) && rp.includes('스냅숏 ' + rec.snapshot_id), rp);
      assert.equal(await page.locator(B + ' [data-sq-applied]').count(), 0);
      // 최신 입력에 설정 적용: the preview op on the input chosen now (PEER_SAMPLE_SMALL): a new result, said so.
      c1 = eng.calls.length; await page.locator(B + ' [data-k=sq-run-latest]').click(); await page.locator(B + ' [data-sq-run-state=APPLIED_LATEST]').waitFor();
      assert.deepEqual(eng.calls.slice(c1).map((c) => [c.op, c.input_id, c.ok]), [['preview', 'PEER_SAMPLE_SMALL', true]]);
      const lt = await text(B + ' [data-sq-run-label]');
      assert.ok(lt.startsWith('최신 입력에 설정 적용 · 새 결과 · 입력 합성 · 비교집단 19개') && lt.includes('과거 결과 재현 아님') && lt.includes('저장 기록은 그대로'), lt);
      assert.equal(await page.locator(B + ' [data-sq-run-state=REPRODUCED]').count(), 0, 'one run state at a time');
      assert.equal(await page.evaluate((k) => localStorage.getItem(k), KEY), raw, 'neither run writes the device record');
      // A record whose original preview / snapshot this route does not hold: 재현 입력 연결 전, nothing else computed;
      // loading it and 기본값 복원 leave its bytes as they were.
      const foreign = JSON.stringify({ ...rec, preview_id: 'a'.repeat(64) });
      await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, foreign]);
      await page.reload(); await page.evaluate(() => window.IS2.ready); await page.locator(B + ' [data-sq-state=IDLE]').waitFor(); await connect();
      c1 = eng.calls.length; await page.locator(B + ' [data-k=sq-run-reproduce]').click(); await page.locator(B + ' [data-sq-run-state=INPUT_MISSING]').waitFor();
      assert.deepEqual(eng.calls.slice(c1).map((c) => [c.op, c.code]), [['replay', 'RETAINED_INPUT_NOT_FOUND']], 'no latest-input run in its place');
      assert.ok((await text(B + ' [data-sq-run-state=INPUT_MISSING]')).startsWith('재현 입력(원래 preview·snapshot) 연결 전'));
      await page.locator(B + ' [data-k=sq-restore]').click(); await ready();
      assert.equal(await page.evaluate((k) => localStorage.getItem(k), KEY), foreign, 'load and restore never rewrite the stored record');
      await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, raw]);
      ok(tag + ' 2.2.7 섹터 QGV 설정(요소·가중치): 원본 참조 / 내 설정 identities; N<20 = 요소 점수 미산출 (N=19), no rank; reproduce = engine replay; apply-latest = new result; missing retained input = 연결 전; stored bytes unchanged');

      // ---------------- phone
      if (phone) {
        phase = tag + ' phone';
        assert.ok((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 0, 'no horizontal overflow');
        const small = await page.$$eval(B + ' select, ' + B + ' input[type=number], ' + B + ' .btn', (els) => els.filter((e) => e.offsetParent && e.getBoundingClientRect().height < 44).map((e) => e.dataset.k || e.tagName));
        assert.deepEqual(small, [], '44 px');
        ok(tag + ' phone: no overflow, 44 px controls');
      }
      if (SHOTS) await page.locator('[data-section="1-2"]').screenshot({ path: path.join(SHOTS, 'sq-' + tag + '.png') });

      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      assert.ok(posts.length > 0 && posts.every((m) => m === 'POST'), 'the engine route is POST only');
      assert.deepEqual(seen.requests.filter((u) => /sector/i.test(u) && !/\/(sector-qgv|sector-qgv-axis|screen-sector-qgv-axis-live|screen-sector-qgv-live)\.js$|\/sector-qgv-engine$/.test(new URL(u).pathname)), [], 'no sector data file request');
      const st = await site.storage(page);
      assert.deepEqual(Object.keys(st.localItems).filter((k) => !/recent-search/.test(k)), [KEY], 'only the sector key is written by this screen');
      assert.equal(await page.evaluate(() => window.__csp), 0);
      assert.deepEqual(eng.stderr, []);
      ok(tag + ' boundaries');
      await ctx.close();
    }

    // ---------------- an old leaderboard weight tree on the device: 이전 설정 호환, still loads in 1.1.6, never rewritten
    phase = 'legacy';
    {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(([k, v]) => { if (!sessionStorage.getItem('seeded')) { localStorage.setItem(k, v); sessionStorage.setItem('seeded', '1'); } }, [LEGACY_KEY, LEGACY]);
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED }), B = '[data-sq-body]';
      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      await page.locator(B + ' [data-k=sq-connect]').click(); await page.locator(B + ' [data-sq-role]').first().waitFor();
      assert.equal(await page.locator(B + ' [data-sq-flow]').getAttribute('data-sq-flow'), 'SECTOR_DEFAULT', 'the flow still starts at 10섹터 기본값');
      const lg = B + ' [data-sq-legacy="1"]';
      assert.equal(await page.locator(lg).count(), 1);
      await page.locator(lg + ' summary').click();
      const lt = await page.locator(lg).innerText();
      assert.ok(lt.startsWith('이전 설정 호환 · 이전 리더보드 가중치 1개') && lt.includes('새 섹터 모형의 기본 선택이 아님') && lt.includes('과거 결과 재현 아님') && lt.includes('공격형 v0.1 · v1 · 이전 설정 호환'), lt);
      assert.equal(await page.locator(B + ' [data-sq-flow] [data-sq-step]').count(), 2, 'two steps only: the old profile is not a step');
      // 1.1.6: the same saved tree still loads for the preview (past results), labelled 이전 설정 호환.
      await page.waitForFunction(() => { const b = document.querySelector('[data-k=mode-preview]'); return b && !b.disabled; });
      assert.ok((await page.locator('[data-legacy-profiles="1"]').innerText()).includes('지금 자료로 계산(과거 결과 재현 아님)'));
      assert.ok((await page.locator('[data-legacy-profiles="1"]').innerText()).startsWith('이전 설정 호환 · 옛 가중치 편집기(공격형·균형형·수비형·사용자 설정)에서 저장한 리더보드 가중치 1개 · 새 기본 선택이 아님'));
      assert.equal(await page.locator('[data-k=mode-preview]').innerText(), '이전 설정 결과(미리보기 · 호환)');
      await page.locator('[data-k=mode-preview]').click(); await page.locator('[data-list-lock=PREVIEW]').waitFor();
      assert.equal(await page.locator('[data-badges] [data-badge=weights] .hl').innerText(), '개인 가중치', 'the old tree computes as before');
      await page.locator('[data-k=mode-official]').click(); await page.locator('[data-list-lock=PREVIEW]').waitFor({ state: 'detached' });
      assert.equal(await page.evaluate((k) => localStorage.getItem(k), LEGACY_KEY), LEGACY, 'the old tree is never rewritten');
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      await ctx.close();
    }
    ok('legacy: an old weight tree is listed as 이전 설정 호환 (not a step of the flow), still loads in 1.1.6, stored value unchanged');

    // ---------------- the published site has no engine route
    phase = 'no route';
    const bare = await site.start({ fixtures, out: s.out });
    try {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } }); const page = await ctx.newPage(); const errs = [];
      page.on('pageerror', (e) => errs.push(String(e)));
      await page.goto(bare.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-sq-body] [data-k=sq-connect]').click();
      await page.locator('[data-sq-body] [data-sq-state=ERROR]').waitFor();
      assert.ok((await page.locator('[data-sq-body]').innerText()).includes('계산 실행 경로 연결 전'));
      assert.equal(await page.locator('[data-sq-body]').getAttribute('data-sq-code'), 'ENGINE_NOT_CONNECTED');
      assert.deepEqual(errs, []);
      await ctx.close();
    } finally { await bare.close(); }
    ok('published site: no engine route → 계산 실행 경로 연결 전, never a guessed result');
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); await eng.close(); }
})();
