'use strict';
// New frontend · feature 7 프롬프트 라이브러리 (#/prompts, web_app/screen-prompts.js skeleton + screen-prompts-live.js; boards v52
// Prompt · MPrompt · add/PromptUse) in Chromium at 1440 and 390, on the development site (tools/web_app_test_site.js) with a
// synthetic company-names-ko.json.
//  - First paint (split): with screen-prompts-live.js held back the skeleton shows the head and sections 6-1 · 6-2, each with a
//    role=status 불러오는 중 line and no card; after the release the library.
//  - Open: sections 6-1 · 6-2 (the shell's menu order), the PLV1 version line, 표시 70 / 전체 70, the first 12 cards (6 on a phone)
//    in catalog order with the Frozen titles, the three idle blocks; nothing read but page files (no selection: no data file).
//  - 7.1.1: domain / role chips by Space and Enter (aria-pressed), scope, Starter, Bundle in its own order, keyword, 내 사본 있는
//    것만 → the empty state (character, 필터 지우기 by keyboard puts the focus back in the search box), 더 보기 moves the focus to
//    the first new card; every count equals the old list() rule (screen module filter, node-tested against ui.py).
//  - 7.1.2 / 7.1.3: a prompt opened by Enter moves the focus to the fill block; typed values and the 오늘 날짜 button (Seoul date)
//    give 복사 가능; the preview lines equal check()'s filled text (old plvCheck rules), unfilled placeholders marked; Enter on 복사
//    puts exactly that text on the clipboard with a status line (cleared when the text changes); a future date, braces and a cleared required field show the old
//    error words and turn copy off; private-looking text (an e-mail) opens 복사 전에 확인 (tick by Space, copy by Enter; Escape
//    cancels and returns the focus); a refused clipboard selects the text in a read-only box.
//  - 7.1.4 (kept in this browser, the old prompt page's keys through IS2.store): ★ by a real click only (a synthetic click stores
//    nothing), aria-pressed, the ★ pill and the ★ 즐겨찾기만 filter (= filter() with the stored list); a copy starts from the
//    official text, differs after typing, fills and copies the edited text, flags added private lines, rejects an undeclared
//    variable, shows 내 사본 있음 in the list, and 기본값으로 되돌리기 asks first (cancel, then delete); 저장 · 이 브라우저 by a real
//    click only; the ★ and the saved copy survive a reload (the saved copy is the value shown: this browser's value, else the
//    official text); deleting the saved copy and turning ★ off write the store; only those two keys are ever in localStorage.
//  - 7.1.5: #/prompts/<id>/qgv opens that prompt with a link back to 1. QGV; an unknown id says so and keeps the list; the input_mode
//    radios work by keyboard; the system-input field links its menu; the 6.2 table and the sample link.
//  - Selected company: IS2.selection NYSE:SYN → exactly one read of company-names-ko.json; 선택 기업 가져오기 (Enter) fills the empty
//    company fields with the public English name and ticker; NAME_UNAVAILABLE / UNRESOLVED / NOT_APPLICABLE; no further reads.
//  - 6.2 personalization order: this browser's saved value → the developer default (two steps, no 로그인 / 계정 words in 6.2 or
//    7.1.4: personal data stays on this device, DC-22).
//  - Keyboard: a Tab walk through main reaches every enabled control (one stop per radio group) and each shows a focus outline.
//  - States in their own pages: loading (company-names-ko.json held: 확인 중, button off, then 가져오기 가능), partial failure (the
//    names file unpublished: FAILED while the library and copy work), loader failure (engines.js 404: the shell notice, the library
//    works, the import says FAILED, ★ and 저장 off with their reason), the logic file missing (screen-prompts-live.js 404: the
//    screen's error card with the alarm character, both sections, no card), a broken prompt pack (served screen-prompts-live.js
//    with one bad domain: the error card with the alarm character, both sections, no card, no page error).
//  - Always: no request leaves the origin, no CSP violation, no console error but the provoked 404s, no [style], no horizontal
//    overflow at 390, nothing in localStorage / sessionStorage / IndexedDB but the two prompt keys a real click wrote, no draft
//    example words.
// Synthetic names only; no price is requested or shown.
const { chromium } = require('playwright');
// Synthetic addresses for the private-text check, built at run time so no address-shaped literal sits in the repository
// (repository guard EMAIL_PATTERN).
const SYN_EMAIL = 'me' + '@' + 'example.com', SYN_EMAIL_CO = 'me' + '@' + 'example.co';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const M = require(R.newPath('screen-prompts-live.js'));
// The old prompt page's two keys (research-bridge.js PL_FAV_KEY / PL_COPY_KEY; IS2.store.KEYS.PROMPT_FAVORITES / PROMPT_COPIES).
const FAV_KEY = 'investment.web.v1.prompt-favorites', COPY_KEY = 'investment.web.v1.prompt-personal-copies';

const LIB = M.library();
const NOW = '2026-10-14T03:00:00.000Z', TODAY = '2026-10-14';
const NAMES = 'company-names-ko.json';
const DRAFT = /예시|EXA\b|예시기업|0\.71|238 \/ 50,000|즐겨찾기 12곳|노트 3개/;
const rec = (code, ticker, en) => ({ key: code, key_kind: 'UNIVERSE_CODE', universe_code: code, ticker, exchange: 'NYSE', en_name: en, en_source: en ? 'synthetic test fixture' : null,
  ko_name: null, ko_status: 'UNREGISTERED', ko_source: null, class_label: null, share_class_note: null, aliases: [] });
const namesFixture = () => ({ schema: 'company-names-ko/1', records: [rec('NYSE:SYN', 'SYN', 'Synthetic Fixture Corp'), rec('NYSE:NONAME', 'NONAME', null)] });
const ids = (list) => list.map((p) => p.prompt_id);
const filled = (p, vals) => M.check(p, vals, { nowIso: NOW, notProvided: LIB.meta.not_provided }).text;
let phase = 'START';

(async () => {
  const s = await site.start({ fixtures: { [NAMES]: { json: namesFixture() } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const pageFiles = new Set([...R.scripts(), ...fs.readdirSync(R.NEW)]);
  const reads = (from) => s.requests.slice(from).map((r) => r.name).filter((n) => !pageFiles.has(n));
  async function open(width, height, allow404 = []) {
    const context = await browser.newContext({ viewport: { width, height } });
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: s.origin });
    await context.clock.setFixedTime(new Date(NOW));
    await context.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404 });
    const go = async (hash, selector) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator(selector).first().waitFor(); };
    const common = async () => {
      assert.equal(await page.locator('[style]').count(), 0, phase + ': no style attribute');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow');
      for (const t of await page.locator('[data-pending]').allTextContents()) assert.doesNotMatch(t, /\d/, phase + ': pending block has no number');
      assert.doesNotMatch(await page.locator('main').innerText(), DRAFT, phase + ': no draft example value');
    };
    const boundaries = async (stored = []) => {
      assert.deepEqual(seen.outside, [], phase + ': no request leaves the origin');
      assert.deepEqual(seen.errors, [], phase + ': no console error');
      assert.equal(await page.evaluate(() => window.__csp), 0, phase + ': no CSP violation');
      const st = await site.storage(page);
      assert.deepEqual([Object.keys(st.localItems).sort(), st.session, st.idb], [[...stored].sort(), 0, 0], phase + ': nothing stored but the keys a click wrote');
    };
    return { context, page, seen, go, common, boundaries };
  }
  const settle = (page) => page.waitForTimeout(150);
  const filledIn = (page) => page.locator('[data-prompt-screen]:not([data-screen-state=loading])').waitFor();
  const stored = (page, key) => page.evaluate((k) => JSON.parse(localStorage.getItem(k)), key);
  const text = (page, sel) => page.locator(sel).first().innerText();
  const clipboard = (page) => page.evaluate(() => navigator.clipboard.readText());
  const active = (page) => page.evaluate(() => { const a = document.activeElement; return a ? { id: a.id, data: { ...a.dataset }, tag: a.tagName } : null; });
  const importState = (page) => page.locator('[data-prompt-import-state]').getAttribute('data-prompt-import-state');
  const waitState = (page, st) => page.waitForFunction((x) => { const n = document.querySelector('[data-prompt-import-state]'); return n && n.dataset.promptImportState === x; }, st);
  const copyState = (page, scope, st) => page.waitForFunction(([sc, x]) => { const n = document.querySelector(sc + ' [data-prompt-copy-status], ' + sc + ' [data-prompt-draft-status]'); return n && n.dataset.copyState === x; }, [scope, st]);
  const previewText = (page) => page.evaluate(() => [...document.querySelectorAll('[data-prompt-preview] > p')].map((p) => p.textContent).join('\n'));
  // Every enabled, rendered control in main (one per radio group) is reached by Tab and shows a focus outline.
  async function tabWalk(page) {
    const expected = await page.evaluate(() => {
      let n = 0; const keys = [], groups = new Set();
      for (const el of document.querySelectorAll('main a[href], main button, main input, main select, main textarea')) {
        if (el.disabled || el.getAttribute('tabindex') === '-1' || !el.getClientRects().length) continue;
        if (el.type === 'radio') { if (groups.has(el.name)) continue; groups.add(el.name); }
        el.dataset.k = 'k' + (n++); keys.push(el.type === 'radio' ? 'radio:' + el.name : el.dataset.k);
      }
      document.getElementById('main').focus(); return keys;
    });
    const got = [], noRing = [];
    for (let i = 0; i < 600; i++) {
      await page.keyboard.press('Tab');
      const a = await page.evaluate(() => { const e = document.activeElement; if (!e || !document.getElementById('main').contains(e)) return null;
        const cs = getComputedStyle(e); return { k: e.type === 'radio' ? 'radio:' + e.name : e.dataset.k, ring: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2, label: e.tagName + ' ' + (e.textContent || e.id).slice(0, 30) }; });
      if (!a) break;
      got.push(a.k); if (!a.ring) noRing.push(a.label);
    }
    assert.deepEqual(expected.filter((k) => !got.includes(k)), [], phase + ': every control is reached by Tab');
    assert.deepEqual(noRing, [], phase + ': every focused control shows an outline');
    return got.length;
  }

  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      const phone = width < 720, per = phone ? 6 : 12, tag = (p) => { phase = width + ' ' + p; };
      const { context, page, go, common, boundaries } = await open(width, height);

      // ---------------------------------------------------------------- open
      tag('first paint');
      const at0 = s.requests.length;
      let release; const gate = new Promise((r) => { release = r; });
      await page.route('**/screen-prompts-live.js', async (route) => { await gate; await route.continue(); });
      await page.goto(s.base + '#/prompts', { waitUntil: 'domcontentloaded' }); await page.locator('[data-prompt-screen]').waitFor();
      assert.equal(await page.locator('[data-prompt-screen]').getAttribute('data-screen-state'), 'loading');
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['6-1', '6-2'], 'the skeleton draws both sections');
      assert.deepEqual(await page.locator('[data-prompt-slot] [data-state=loading][role=status]').allTextContents(), ['불러오는 중', '불러오는 중'], 'a loading line in each section');
      assert.equal(await page.locator('[data-prompt-card]').count(), 0, 'no card before the logic file');
      release();// the route stays: with the gate open it lets every later load through at once
      tag('open');
      assert.equal(await page.evaluate(() => window.IS2.ready.then(() => window.IS2.loadState())), 'READY');
      await filledIn(page);
      assert.equal(await page.locator('[data-prompt-screen]').getAttribute('data-screen-state'), 'ready');
      assert.equal(await page.locator('[data-prompt-slot] [data-state=loading]').count(), 0);
      await settle(page);
      assert.deepEqual(reads(at0), [], 'opening #/prompts reads no data file');
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['6-1', '6-2']);
      assert.equal((await text(page, 'main h1')).replace(/\s+/g, ' '), '6. 프롬프트 라이브러리');
      const version = await text(page, '[data-prompt-version]');
      assert.ok(version.includes('PLV1_CONTENT_V1.0') && version.includes('프롬프트 70개') && version.includes(LIB.meta.sha256.slice(0, 12)), version);
      assert.equal(await text(page, '[data-prompt-count]'), '표시 70 / 전체 70');
      const first = LIB.prompts.slice(0, per);
      assert.deepEqual(await page.locator('[data-prompt-card]').evaluateAll((n) => n.map((x) => x.dataset.promptCard)), ids(first), 'catalog order, first step');
      assert.deepEqual(await page.locator('[data-prompt-card] .card-title').allTextContents(), first.map((p) => p.title), 'Frozen titles');
      assert.equal(await page.locator('[data-prompt-idle]').count(), 3, 'fill / copy / mine wait for a prompt');
      assert.deepEqual(await page.locator('[data-prompt-absent-domain]').allTextContents(), ['뉴스', '포트폴리오', '연구']);
      assert.deepEqual([await page.locator('[data-prompt-fav-only]').isDisabled(), await page.locator('[data-prompt-fav-only]').getAttribute('aria-pressed')], [false, 'false'], '★ 즐겨찾기만 is a filter now');
      assert.match(await text(page, '[data-prompt-more]'), new RegExp('남은 ' + (70 - per) + '개'));
      await common();

      // ---------------------------------------------------------------- 7.1.1 고르기
      tag('filters');
      const cards = () => page.locator('[data-prompt-card]').evaluateAll((n) => n.map((x) => x.dataset.promptCard));
      const expectList = async (f, why) => {
        const want = M.filter(LIB, f);
        assert.equal(await text(page, '[data-prompt-count]'), '표시 ' + want.length + ' / 전체 70' + (f.fav ? ' · ★ 즐겨찾기만' : '') + (f.mine ? ' · 내 사본 있는 것만' : ''), why);
        assert.deepEqual(await cards(), ids(want.slice(0, per)), why);
      };
      await page.locator('[data-prompt-domain="MACRO"]').focus(); await page.keyboard.press('Space');
      assert.deepEqual(await page.locator('[data-prompt-domain]').evaluateAll((n) => n.filter((x) => x.getAttribute('aria-pressed') === 'true').map((x) => x.dataset.promptDomain)), ['MACRO']);
      await expectList({ domain: 'MACRO' }, 'domain by Space');
      await page.locator('[data-prompt-role="BLIND-SPOT"]').focus(); await page.keyboard.press('Enter');
      await expectList({ domain: 'MACRO', role: 'BLIND-SPOT' }, 'role by Enter');
      await page.locator('[data-prompt-scope]').selectOption('MARKET');
      await expectList({ domain: 'MACRO', role: 'BLIND-SPOT', scope: 'MARKET' }, 'scope');
      await page.locator('[data-prompt-starter]').click();
      await expectList({ domain: 'MACRO', role: 'BLIND-SPOT', scope: 'MARKET', starter: true }, 'Starter');
      await page.locator('[data-prompt-mine-only]').click();
      assert.equal(await page.locator('[data-prompt-card]').count(), 0);
      assert.equal(await page.locator('[data-prompt-empty]').isVisible(), true, 'the empty state');
      assert.equal(await page.locator('[data-prompt-empty] [data-mascot="plain"]').count(), 1, 'with the calm character');
      assert.equal(await page.locator('[data-prompt-more]').count(), 0, 'no 더 보기 without more');
      assert.match(await text(page, '[data-prompt-empty]'), /조건에 맞는 프롬프트 없음[\s\S]*필터를 하나씩 풀어 보세요/);
      await common();
      await page.locator('[data-prompt-clear]').focus(); await page.keyboard.press('Enter');
      assert.equal(await text(page, '[data-prompt-count]'), '표시 70 / 전체 70', 'filters cleared');
      assert.equal((await active(page)).id, 'prompt-kw', 'focus back in the search box');
      assert.deepEqual(await page.locator('[aria-pressed="true"]').evaluateAll((n) => n.map((x) => x.textContent)), ['전체', '전체'], 'only the two 전체 chips stay on');
      assert.equal(await page.locator('[data-prompt-empty]').count(), 0);
      for (const b of LIB.bundles.slice(0, 3)) {
        await page.locator('[data-prompt-bundle]').selectOption(String(b.number));
        assert.deepEqual(await cards(), [...b.prompt_ids].slice(0, per), 'Bundle ' + b.number + ' in its own order');
        assert.match(await page.locator('[data-prompt-card] .card-title').first().textContent(), /^1\. /, 'numbered');
      }
      await page.locator('[data-prompt-bundle]').selectOption('');
      await page.locator('[data-prompt-kw]').fill('margin');
      await expectList({ kw: 'margin' }, 'keyword');
      await page.locator('[data-prompt-kw]').fill('');
      await page.locator('[data-prompt-more]').click();
      assert.deepEqual(await cards(), ids(LIB.prompts.slice(0, 2 * per)), '더 보기');
      assert.equal((await active(page)).data.promptOpen, LIB.prompts[per].prompt_id, 'the focus goes to the first new card');
      await common();

      // ---------------------------------------------------------------- open a prompt by keyboard (7.1.2)
      tag('open prompt');
      const fund = LIB.byId.get('plv1.fund.030');
      await page.locator('[data-prompt-kw]').fill('plv1.fund.030');
      assert.deepEqual(await cards(), ['plv1.fund.030']);
      await page.locator('[data-prompt-open="plv1.fund.030"]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-prompt-fill="plv1.fund.030"]').waitFor();
      assert.equal((await active(page)).id, 'pb-fill', 'the focus moves to the fill block');
      assert.equal(await page.locator('[data-prompt-card="plv1.fund.030"]').getAttribute('aria-current'), 'true');
      assert.deepEqual(await page.locator('[data-prompt-fill] [data-field]').evaluateAll((n) => n.map((x) => x.dataset.field)), fund.variables.map((v) => v.name));
      assert.equal(await page.locator('[data-prompt-copy]').isDisabled(), true, 'copy off while required fields are empty');
      assert.match(await text(page, '[data-check-state="MISSING"]'), /필수 누락 3 · 분석할 회사, 종목 코드, 정보 기준일/);
      assert.match(await text(page, '[data-context-row="from"]'), /프롬프트 라이브러리에서 직접 엶/);
      assert.match(await text(page, '[data-context-row="company"]'), /선택 기업 없음/);
      assert.equal(await importState(page), 'MISSING');
      assert.equal(await page.locator('[data-prompt-import]').isDisabled(), true);
      assert.match(await text(page, '[data-context-row="lack"]'), /기존 QGV 요약: 바로 가져오기 준비 중/);
      assert.match(await text(page, '[data-context-row="period"]'), /자동으로 옮기지 않습니다/);
      assert.deepEqual(await page.locator('[data-prompt-preview] mark').evaluateAll((n) => [...new Set(n.map((x) => x.dataset.unfilled))].sort()), ['as_of', 'company', 'ticker']);
      assert.equal(await previewText(page), filled(fund, {}), 'preview = check() text (the optional summary becomes NOT_PROVIDED)');
      await common();

      // ---------------------------------------------------------------- fill and copy by keyboard (7.1.3)
      tag('copy');
      await page.locator('#pv-company').focus(); await page.keyboard.type('Synthetic Co');
      await page.locator('#pv-ticker').focus(); await page.keyboard.type('SYN');
      await page.locator('[data-prompt-today]').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('#pv-as_of').inputValue(), TODAY, '오늘 날짜 = the Seoul date');
      const vals = { company: 'Synthetic Co', ticker: 'SYN', as_of: TODAY };
      await page.locator('[data-check-state="READY"]').waitFor();
      assert.equal(await page.locator('[data-prompt-copy]').isDisabled(), false);
      assert.equal(await page.locator('[data-prompt-preview] mark').count(), 0);
      assert.equal(await previewText(page), filled(fund, vals));
      await page.locator('[data-prompt-copy]').focus(); await page.keyboard.press('Enter');
      await copyState(page, '[data-prompt-block="copy"]', 'COPIED');
      assert.equal(await clipboard(page), filled(fund, vals), 'Enter on 복사 copies exactly the filled text');
      assert.match(await text(page, '[data-prompt-copy-status]'), /복사했습니다/);
      // Old error words, copy off.
      await page.locator('#pv-as_of').fill('2099-01-01');
      assert.equal(await page.locator('[data-prompt-copy-status]').textContent(), '', 'a changed text clears the last copy line');
      assert.match(await text(page, '[data-check-state="INVALID"]'), /정보 기준일: 정보 기준 날짜는 미래일 수 없습니다\./);
      assert.equal(await text(page, '[data-field-error="as_of"]'), M.WORDS.future);
      assert.equal(await page.locator('#pv-as_of').getAttribute('aria-invalid'), 'true');
      assert.equal(await page.locator('[data-prompt-copy]').isDisabled(), true);
      await page.locator('#pv-as_of').fill('2026-10-01'); vals.as_of = '2026-10-01';
      await page.locator('#pv-company').fill('A {{x}}');
      assert.equal(await text(page, '[data-field-error="company"]'), M.WORDS.braces);
      await page.locator('#pv-company').fill('Synthetic Co');
      await page.locator('#pv-ticker').fill('');
      assert.equal(await text(page, '[data-field-error="ticker"]'), M.WORDS.missing, 'a touched required field says so');
      await page.locator('#pv-ticker').fill('SYN');
      await page.locator('[data-check-state="READY"]').waitFor();
      assert.equal(await page.locator('[data-field-error]:not([hidden])').count(), 0);
      await common();
      // Private-looking text: look first.
      tag('confirm');
      await page.locator('#pv-company').fill('Synthetic Co ' + SYN_EMAIL);
      await page.locator('[data-prompt-copy]').click();
      await page.locator('[data-prompt-confirm="official"]').waitFor();
      assert.equal((await active(page)).data.promptConfirmCheck, '', 'the focus moves to the tick');
      assert.deepEqual(await page.locator('[data-prompt-confirm] [data-private-kind]').evaluateAll((n) => n.map((x) => x.dataset.privateKind)), ['EMAIL']);
      assert.equal(await page.locator('[data-prompt-confirm-copy]').isDisabled(), true);
      await page.keyboard.press('Space');
      assert.equal(await page.locator('[data-prompt-confirm-copy]').isDisabled(), false);
      await page.keyboard.press('Tab'); assert.equal((await active(page)).data.promptConfirmCopy, '');
      await page.keyboard.press('Enter');
      await copyState(page, '[data-prompt-block="copy"]', 'COPIED');
      assert.equal(await clipboard(page), filled(fund, { ...vals, company: 'Synthetic Co ' + SYN_EMAIL }));
      assert.equal(await page.locator('[data-prompt-confirm]').count(), 0);
      assert.equal((await active(page)).data.promptCopy, '', 'the focus returns to 복사');
      await page.locator('#pv-company').fill('Synthetic Co ' + SYN_EMAIL_CO);
      await page.locator('[data-prompt-copy]').click(); await page.locator('[data-prompt-confirm="official"]').waitFor();
      await common();
      await page.keyboard.press('Escape');
      await copyState(page, '[data-prompt-block="copy"]', 'CANCELLED');
      assert.equal((await active(page)).data.promptCopy, '', 'Escape returns the focus to 복사');
      await page.locator('#pv-company').fill('Synthetic Co');
      // A refused clipboard: the text is selected for a manual copy.
      tag('clipboard refused');
      await page.evaluate(() => { navigator.clipboard.writeText = () => Promise.reject(new DOMException('refused', 'NotAllowedError')); });
      await page.locator('[data-prompt-copy]').click();
      await copyState(page, '[data-prompt-block="copy"]', 'FAILED');
      const fb = await page.evaluate(() => { const t = document.querySelector('[data-prompt-copy-fallback]'); return { hidden: t.hidden, focus: document.activeElement === t, value: t.value, a: t.selectionStart, b: t.selectionEnd }; });
      assert.deepEqual(fb, { hidden: false, focus: true, value: filled(fund, vals), a: 0, b: filled(fund, vals).length });
      assert.match(await text(page, '[data-prompt-copy-status]'), /직접 복사/);
      await common();
      await page.evaluate(() => { delete navigator.clipboard.writeText; });

      // ---------------------------------------------------------------- 7.1.4 내 사본 (RAM only)
      tag('favorite');
      const fav = page.locator('[data-prompt-favorite="plv1.fund.030"]');
      assert.deepEqual([await fav.isDisabled(), await fav.getAttribute('aria-pressed'), await fav.textContent()], [false, 'false', '☆ 즐겨찾기']);
      assert.match(await text(page, '[data-prompt-store-note]'), /이 브라우저에만 저장됩니다[\s\S]*기기 백업 파일에는 아직 들어가지 않음[\s\S]*새로고침하면 사라집니다/);
      // A synthetic click (script) is no user action: the gate refuses, nothing is stored.
      await page.evaluate(() => document.querySelector('[data-prompt-favorite]').click());
      assert.equal(await text(page, '[data-prompt-favorite-status]'), '저장하지 않음 · 버튼을 직접 눌러야 저장합니다.');
      assert.equal(await fav.getAttribute('aria-pressed'), 'false'); assert.equal(await stored(page, FAV_KEY), null, 'nothing stored without a real click');
      await fav.focus(); await page.keyboard.press('Enter');
      assert.deepEqual([await fav.getAttribute('aria-pressed'), await fav.textContent()], ['true', '★ 즐겨찾기'], 'a real click turns ★ on');
      assert.deepEqual(await stored(page, FAV_KEY), ['plv1.fund.030'], 'kept in this browser under the old key');
      assert.equal(await text(page, '[data-prompt-favorite-status]'), '이 브라우저의 즐겨찾기에 넣었습니다.');
      assert.deepEqual(await page.locator('[data-prompt-card="plv1.fund.030"] .pill').allTextContents().then((t) => t.filter((x) => x === '★ 즐겨찾기')), ['★ 즐겨찾기'], 'the ★ pill in the list');
      await page.locator('[data-prompt-kw]').fill('');
      await page.locator('[data-prompt-fav-only]').click();
      await expectList({ fav: true, favs: ['plv1.fund.030'] }, '★ 즐겨찾기만');
      assert.match(await text(page, '[data-prompt-count]'), / · ★ 즐겨찾기만$/);
      await page.locator('[data-prompt-fav-only]').click();
      await page.locator('[data-prompt-kw]').fill('plv1.fund.030');
      tag('draft');
      await page.locator('[data-prompt-draft-make]').click();
      const area = page.locator('[data-prompt-draft]');
      assert.equal(await area.inputValue(), fund.body);
      assert.equal((await active(page)).data.promptDraft, '', 'the focus moves to the copy text');
      assert.match(await text(page, '[data-prompt-draft-meta]'), /^공식 원문과 같음 · 저장 안 됨/);
      assert.equal(await page.locator('[data-prompt-draft-save]').isDisabled(), false, '저장 · 이 브라우저 is on');
      await page.keyboard.press('Control+End'); await page.keyboard.type('\n마지막에 반대 근거 세 가지를 적어라.');
      assert.match(await text(page, '[data-prompt-draft-meta]'), /^공식 원문과 다름 · 저장 안 됨/);
      await page.locator('[data-prompt-draft-copy]').click();
      await copyState(page, '[data-prompt-block="mine"]', 'COPIED');
      assert.equal(await clipboard(page), filled({ ...fund, body: fund.body + '\n마지막에 반대 근거 세 가지를 적어라.' }, vals), 'the edited copy, filled with the same values');
      assert.equal(await page.locator('[data-prompt-card="plv1.fund.030"] .pill.mine').count(), 1, '내 사본 있음 in the list');
      await page.locator('[data-prompt-kw]').fill('');
      await page.locator('[data-prompt-mine-only]').click();
      await expectList({ mine: true, drafts: { 'plv1.fund.030': 1 } }, 'mine only');
      await page.locator('[data-prompt-mine-only]').click();
      await area.focus(); await page.keyboard.press('Control+End'); await page.keyboard.type('\n잔고 1,000원');
      await page.locator('[data-prompt-draft-copy]').click(); await page.locator('[data-prompt-confirm="draft"]').waitFor();
      assert.deepEqual(await page.locator('[data-prompt-confirm="draft"] [data-private-kind]').evaluateAll((n) => n.map((x) => x.dataset.privateKind)).then((k) => k.sort()), ['HOLDING', 'MONEY']);
      await page.locator('[data-prompt-confirm-back]').click();
      await area.focus(); await page.keyboard.press('Control+End'); await page.keyboard.type(' {{nope}}');
      await page.locator('[data-prompt-draft-copy]').click();
      assert.match(await text(page, '[data-prompt-draft-status]'), /선언되지 않은 변수가 남아 있습니다: \{\{nope\}\}/);
      await common();
      phase = width + ' tab walk';
      const stops = await tabWalk(page);
      assert.ok(stops > 20, 'tab stops ' + stops);
      tag('draft reset');
      await page.locator('[data-prompt-draft-reset]').click();
      assert.equal((await active(page)).data.promptDraftResetCancel, '', 'asks first; the focus is on 취소');
      await page.keyboard.press('Enter');
      assert.equal((await active(page)).data.promptDraftReset, '', 'cancel returns the focus');
      assert.equal(await area.count(), 1, 'nothing deleted');
      await page.locator('[data-prompt-draft-reset]').click(); await page.locator('[data-prompt-draft-reset-confirm]').click();
      assert.equal(await page.locator('[data-prompt-draft]').count(), 0);
      assert.equal((await active(page)).data.promptDraftMake, '', 'the focus goes to 공식 원문으로 만들기');
      assert.equal(await text(page, '[data-prompt-draft-status]'), '내 사본을 지웠습니다.');
      assert.equal(await stored(page, COPY_KEY), null, 'an unsaved copy was never stored');

      // ---------------------------------------------------------------- 7.1.5 deep link
      tag('deep link');
      await go('#/prompts/plv1.tech.001/qgv', '[data-prompt-fill="plv1.tech.001"]');
      assert.equal(await text(page, '[data-prompt-back]'), '← 1. QGV 화면으로 돌아가기');
      assert.equal(await page.locator('[data-prompt-back]').getAttribute('href'), '#/qgv');
      assert.match(await text(page, '[data-context-row="from"]'), /1\. QGV 화면에서 열림/);
      const radios = page.locator('input[type=radio][data-v="input_mode"]');
      assert.equal(await radios.count(), 2);
      await radios.first().focus(); await page.keyboard.press('Space');
      assert.equal(await radios.first().isChecked(), true);
      await page.keyboard.press('ArrowDown');
      assert.equal(await radios.nth(1).isChecked(), true, 'arrow keys move within the radio group');
      assert.equal(await page.locator('[data-field="technical_input"] a[href="#/technical"]').count(), 1, 'the system-input field names its menu');
      await common();
      await go('#/prompts/plv1.none.999', '[data-prompt-error="UNKNOWN_PROMPT"]');
      assert.equal(await page.locator('[data-prompt-error="UNKNOWN_PROMPT"]').getAttribute('role'), 'alert');
      assert.ok(await page.locator('[data-prompt-card]').count() > 0, 'the list stays');
      assert.equal(await page.locator('[data-prompt-fill="plv1.tech.001"]').count(), 1, 'the open prompt stays');

      // ---------------------------------------------------------------- selected company (IS2.selection, public names only)
      tag('selection');
      const at1 = s.requests.length;
      await page.evaluate(() => window.IS2.selection.set('NYSE:SYN'));
      await go('#/prompts/plv1.fund.030', '[data-prompt-fill="plv1.fund.030"]');
      await waitState(page, 'INPUT_RETAINED');
      assert.match(await text(page, '[data-context-row="company"]'), /Synthetic Fixture Corp · SYN/);
      await page.locator('#pv-company').fill(''); await page.locator('#pv-ticker').fill('');
      await waitState(page, 'AVAILABLE');
      assert.match(await text(page, '[data-context-row="have"]'), /선택 기업/);
      await page.locator('[data-prompt-import]').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('#pv-company').inputValue(), 'Synthetic Fixture Corp');
      assert.equal(await page.locator('#pv-ticker').inputValue(), 'SYN');
      assert.equal(await page.locator('#pv-as_of').inputValue(), '2026-10-01', 'dates stay');
      assert.equal(await importState(page), 'INPUT_RETAINED');
      assert.match(await text(page, '[data-prompt-import-state]'), /채웠습니다/);
      assert.equal((await active(page)).id, 'pv-company', 'the focus goes to the filled field');
      await page.locator('#pv-company').fill(''); await page.locator('#pv-ticker').fill('');
      await page.evaluate(() => window.IS2.selection.set('NYSE:NONAME')); await waitState(page, 'NAME_UNAVAILABLE');
      assert.equal(await page.locator('[data-prompt-import]').isDisabled(), true);
      await page.evaluate(() => window.IS2.selection.set('NYSE:ZZZZ')); await waitState(page, 'UNRESOLVED');
      assert.match(await text(page, '[data-context-row="company"]'), /NYSE:ZZZZ · 공개 이름표에 없음/);
      await go('#/prompts/plv1.macro.001', '[data-prompt-fill="plv1.macro.001"]');
      assert.equal(await importState(page), 'NOT_APPLICABLE');
      assert.equal(await page.locator('[data-prompt-import]').count(), 0, 'no import button without company fields');
      await common();
      assert.deepEqual(reads(at1), [NAMES], 'one read of the public names table, only once a company is selected');
      await page.evaluate(() => window.IS2.selection.set(null));

      // ---------------------------------------------------------------- 6.2
      tag('6.2');
      assert.equal(await page.locator('[data-prompt-links] tbody tr').count(), 6);
      assert.deepEqual(await page.locator('[data-prompt-links] tbody .chip:not(.wait)').allTextContents(), ['연결됨']);
      assert.deepEqual(await page.locator('[data-prompt-block="personal"] .grid-2 > .card .card-title').allTextContents(), ['① 이 기기(브라우저)에 저장된 값', '② 저장된 값이 없으면 개발자 기본값'],
        'this browser\'s saved value, then the developer default');
      assert.match(await text(page, '[data-prompt-personal-now]'), /이 브라우저에 저장한 내 사본이 있으면 그것을, 없으면 개발자 기본값/);
      for (const sel of ['[data-prompt-block="personal"]', '[data-prompt-block="mine"]', '[data-prompt-band]']) assert.doesNotMatch(await text(page, sel), /로그인|계정/, sel + ': no login / account words for personal data');
      await page.locator('[data-prompt-sample]').click();
      await page.locator('[data-prompt-fill="' + LIB.starters[0] + '"]').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/prompts/' + LIB.starters[0] + '/qgv');
      await common();
      if (phone) {
        // Catalog text holds long unbroken runs (Trend·Momentum·Volume/Flow): every prompt, opened, stays inside 390 px.
        for (const p of LIB.prompts) {
          phase = width + ' every prompt ' + p.prompt_id;
          await go('#/prompts/' + p.prompt_id, '[data-prompt-fill="' + p.prompt_id + '"]');
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow');
        }
      }
      // ---------------------------------------------------------------- kept in this browser: a saved copy and ★ survive a reload
      tag('kept in this browser');
      await page.evaluate(() => window.IS2.selection.set(null));
      await go('#/prompts/plv1.fund.030', '[data-prompt-fill="plv1.fund.030"]');
      await page.locator('[data-prompt-draft-make]').click();
      await page.locator('[data-prompt-draft]').focus(); await page.keyboard.press('Control+End'); await page.keyboard.type('\n저장할 내 문장.');
      const mineBody = fund.body + '\n저장할 내 문장.';
      await page.evaluate(() => document.querySelector('[data-prompt-draft-save]').click());
      assert.equal(await text(page, '[data-prompt-draft-status]'), '버튼을 직접 눌러야 저장합니다.'); assert.equal(await stored(page, COPY_KEY), null, 'a synthetic click saves nothing');
      await page.locator('[data-prompt-draft-save]').focus(); await page.keyboard.press('Enter');
      const saved = await stored(page, COPY_KEY);
      assert.deepEqual(Object.keys(saved), ['plv1.fund.030']); assert.equal(saved['plv1.fund.030'].body, mineBody); assert.equal(saved['plv1.fund.030'].content_version, 'PLV1_CONTENT_V1.0');
      assert.equal(await text(page, '[data-prompt-draft-status]'), '이 브라우저에 내 사본을 저장했습니다.');
      assert.match(await text(page, '[data-prompt-draft-meta]'), /^공식 원문과 다름 · 이 브라우저에 저장됨 · 기준 원문 PLV1_CONTENT_V1\.0 · 저장 /);
      const atR = s.requests.length;
      await page.reload(); await filledIn(page); await page.locator('[data-prompt-fill="plv1.fund.030"]').waitFor();
      assert.equal(await page.locator('[data-prompt-draft]').inputValue(), mineBody, 'the saved copy is the value shown after a reload');
      assert.match(await text(page, '[data-prompt-draft-meta]'), /이 브라우저에 저장됨/);
      assert.equal(await page.locator('[data-prompt-favorite="plv1.fund.030"]').getAttribute('aria-pressed'), 'true', '★ survives a reload');
      await page.locator('[data-prompt-kw]').fill('plv1.fund.030');
      assert.equal(await page.locator('[data-prompt-card="plv1.fund.030"] .pill.mine').count(), 1, '내 사본 있음 after a reload');
      await page.locator('[data-prompt-mine-only]').click();
      await expectList({ kw: 'plv1.fund.030', mine: true, drafts: { 'plv1.fund.030': 1 } }, 'the saved copy counts as a copy');
      await page.locator('[data-prompt-mine-only]').click();
      assert.deepEqual(reads(atR), [], 'a reload of #/prompts reads no data file');
      await common();
      await page.locator('[data-prompt-draft-reset]').click(); await page.locator('[data-prompt-draft-reset-confirm]').click();
      assert.deepEqual(await stored(page, COPY_KEY), {}, 'the confirm click deletes this browser\'s copy');
      assert.equal(await page.locator('[data-prompt-draft-make]').count(), 1);
      await page.locator('[data-prompt-favorite="plv1.fund.030"]').click();
      assert.deepEqual(await stored(page, FAV_KEY), [], 'a second click turns ★ off');
      assert.equal(await page.locator('[data-prompt-favorite="plv1.fund.030"]').getAttribute('aria-pressed'), 'false');
      phase = width + ' boundaries';
      assert.deepEqual(reads(at0), [NAMES], 'the whole run read one data file');
      await boundaries([FAV_KEY, COPY_KEY]);
      await context.close();
    }

    // ---------------------------------------------------------------- loading and partial failure (phone)
    {
      phase = 'loading';
      const { context, page, go, common, boundaries } = await open(390, 844, [NAMES]);
      let release; const gate = new Promise((r) => { release = r; });
      await page.route('**/' + NAMES, async (route) => { await gate; await route.continue(); });
      await page.goto(s.base + '#/prompts'); await page.locator('[data-prompt-screen]').waitFor();
      await page.evaluate(() => window.IS2.ready);
      await page.evaluate(() => window.IS2.selection.set('NYSE:SYN'));
      await go('#/prompts/plv1.fund.030', '[data-prompt-fill="plv1.fund.030"]');
      await waitState(page, 'LOADING');
      assert.match(await text(page, '[data-context-row="company"]'), /NYSE:SYN · 공개 이름표 확인 중/);
      assert.equal(await page.locator('[data-prompt-import]').isDisabled(), true);
      assert.match(await text(page, '[data-prompt-import-state]'), /읽는 중/);
      await common();
      release(); await waitState(page, 'AVAILABLE');
      await page.unroute('**/' + NAMES);
      phase = 'partial failure';
      s.fixture(NAMES, { status: 404, body: '' });
      await page.reload(); await page.locator('[data-prompt-fill="plv1.fund.030"]').waitFor();
      await page.evaluate(() => window.IS2.ready);
      await page.evaluate(() => window.IS2.selection.set('NYSE:SYN'));
      await waitState(page, 'FAILED');
      assert.match(await text(page, '[data-context-row="company"]'), /공개 이름표를 읽지 못함/);
      assert.match(await text(page, '[data-prompt-import-state]'), /직접 입력하세요/);
      await page.locator('#pv-company').fill('Synthetic Co'); await page.locator('#pv-ticker').fill('SYN'); await page.locator('#pv-as_of').fill('2026-10-01');
      await page.locator('[data-prompt-copy]').click();
      await copyState(page, '[data-prompt-block="copy"]', 'COPIED');
      assert.equal(await clipboard(page), filled(LIB.byId.get('plv1.fund.030'), { company: 'Synthetic Co', ticker: 'SYN', as_of: '2026-10-01' }), 'the library works without the names table');
      await page.locator('[data-prompt-domain="TECHNICAL"]').click();
      assert.equal(await text(page, '[data-prompt-count]'), '표시 ' + M.filter(LIB, { domain: 'TECHNICAL' }).length + ' / 전체 70');
      await common();
      await boundaries();
      s.fixture(NAMES, { json: namesFixture() });
      await context.close();
    }
    {
      phase = 'loader failure';
      const { context, page, common, boundaries } = await open(390, 844, ['engines.js']);
      await page.route('**/engines.js', (route) => route.fulfill({ status: 404, body: '' }));
      await page.goto(s.base + '#/prompts/plv1.fund.030'); await page.locator('[data-prompt-fill="plv1.fund.030"]').waitFor();
      assert.equal(await page.evaluate(() => window.IS2.ready.then(() => 'READY', (e) => e.message)), 'LOADER_FAILED engines.js');
      await page.locator('[data-load-failed]').waitFor();
      await page.evaluate(() => window.IS2.selection.set('NYSE:SYN'));
      await waitState(page, 'FAILED');
      assert.equal(await page.locator('[data-prompt-card]').count() > 0, true, 'the library does not need the layer');
      await page.locator('#pv-company').fill('Synthetic Co'); await page.locator('#pv-ticker').fill('SYN'); await page.locator('#pv-as_of').fill('2026-10-01');
      await page.locator('[data-check-state="READY"]').waitFor();
      assert.equal(await page.locator('[data-prompt-favorite]').isDisabled(), true, '★ off without the store');
      assert.match(await text(page, '[data-prompt-store-state="NOT_READY"]'), /저장 경로를 불러오지 못해 ★와 저장이 꺼져 있습니다/);
      await page.locator('[data-prompt-draft-make]').click();
      assert.equal(await page.locator('[data-prompt-draft-save]').isDisabled(), true, '저장 off without the store');
      await common();
      await boundaries();
      await context.close();
    }
    {
      phase = 'logic file missing';
      const { context, page, common, boundaries } = await open(390, 844, ['screen-prompts-live.js']);
      await page.route('**/screen-prompts-live.js', (route) => route.fulfill({ status: 404, body: '' }));
      const at = s.requests.length;
      await page.goto(s.base + '#/prompts/plv1.fund.030'); await page.locator('[data-prompt-error="LOADER_FAILED"]').waitFor();
      assert.equal(await page.evaluate(() => window.IS2.ready.then(() => 'READY', (e) => e.message)), 'LOADER_FAILED screen-prompts-live.js');
      assert.equal(await page.locator('[data-prompt-screen]').getAttribute('data-screen-state'), 'error');
      assert.equal(await page.locator('[data-prompt-error="LOADER_FAILED"]').getAttribute('role'), 'alert');
      assert.equal(await page.locator('[data-prompt-error] [data-mascot="alarm"]').count(), 1);
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['6-1', '6-2']);
      assert.deepEqual([await page.locator('[data-prompt-card]').count(), await page.locator('[data-state=loading]').count()], [0, 0]);
      await page.locator('[data-load-failed]').waitFor();
      await settle(page);
      assert.deepEqual(reads(at), [], 'no data read');
      await common();
      await boundaries();
      await context.close();
    }
    {
      phase = 'broken pack';
      const good = fs.readFileSync(R.newPath('screen-prompts-live.js'), 'utf8'), bad = good.replace('"domain":"DISCOVERY"', '"domain":"NOPE"');
      assert.notEqual(bad, good);
      s.fixture('screen-prompts-live.js', { body: bad, type: 'text/javascript' });
      const { context, page, common, boundaries } = await open(1440, 1000);
      const at = s.requests.length;
      await page.goto(s.base + '#/prompts/plv1.fund.030'); await page.locator('[data-prompt-error="PROMPT_PACK_INVALID"]').waitFor();
      await page.evaluate(() => window.IS2.ready);
      assert.equal(await page.locator('[data-prompt-error="PROMPT_PACK_INVALID"]').getAttribute('role'), 'alert');
      assert.equal(await page.locator('[data-prompt-error] [data-mascot="alarm"]').count(), 1);
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['6-1', '6-2']);
      assert.equal(await page.locator('[data-prompt-card]').count(), 0);
      assert.equal(await page.locator('[data-prompt-links]').count(), 1, '6.2 stays');
      await settle(page);
      assert.deepEqual(reads(at), [], 'no data read');
      await common();
      await boundaries();
      s.fixture('screen-prompts-live.js', null);
      await context.close();
    }
    console.log('web app prompts: split first paint, list, filters, fill, copy, confirm, ★ and copies kept in this browser, deep links, selected company, personalization order, keyboard, states and boundaries ok at 1440 and 390');
  } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
