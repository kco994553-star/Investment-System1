'use strict';
// New frontend P2-8 · menu n 구조 트리 (feature 8 · 8.1.1–8.1.4; boards SystemTree · m/MTree · add/TreeCommon; screen-tree.js skeleton
// + screen-tree-live.js) in a real browser at 1440×1000 and 390×844. Builds the development site (tools/web_app_test_site.js); no
// fixture is needed: the screen reads nothing.
//  - First paint (split, the tree is 9 KB gzip): with the P1 layer held back (data.js not answered) the skeleton shows the head and
//    section n-1 with a role=status 불러오는 중 line and no tree item, and no file is read; after the release the whole tree.
//  - Content: main[data-route=tree], one section n-1 (the shell test's contract), the head; top-level nodes = IS2.MENU in its order
//    (number · name · route) plus 세부 화면; under them every numbered line of docs/SPEC/FUNCTION_HIERARCHY_v1.0.md (levels 2–4,
//    parsed here, same order, same names; 4.5 = 나비효과 by DC-17) under its own parent, each area's meta = its spec number and
//    name; the detail screens = IS2.DETAILS with routes #/detail/<id>; aria-level / setsize / posinset / expanded / owns
//    consistent; every href parses (IS2.parse) to the route it belongs to (2.4 QGV 상세 → 기업 검색).
//  - Status: each screen node's data-node-status and chip equal the registry at render time (IS2.screen / isPlaceholder,
//    IS2.detail): 화면 있음 / 준비 중; no other node has a status; the counts line equals the chips; registering a detail screen
//    (and a menu screen where one is still a placeholder) flips that node to 화면 있음 on the next render. The unfinished models
//    carry the owner's words (공식 국면 미산출 · 준비 중); 8.1.3's classes and steps are 준비 중 with what is missing (the
//    FUNCTION_STATUS public copy). Table 1-3 (8.1): 내 정보 = 이 기기에만 · 공개 안 함 (never 비공개); one static line for the private
//    layer; the public file count = IS2.data.FILES.length (a constant, no read); as_of examples 준비 중 with what is missing; no
//    private panel; no 로그인 / 계정 words but the private-layer line.
//  - Keyboard: Tab reaches every control of main with a focus ring, the tree is one tab stop (one treeitem tabindex 0); ↓ ↑ → ←
//    Home End * as in the WAI-ARIA tree pattern; Enter follows the link; open nodes survive a route change (RAM).
//  - Pointer: the caret opens and closes without leaving the page; a label click navigates; 세부 화면 (no route) toggles;
//    모두 펼치기 / 모두 접기.
//  - Phone: no horizontal overflow with every node open, each treeitem inside the viewport, 44 px tap targets.
//  - States: partial (the registry throws for one menu: 상태 확인 불가 there, the rest stays; a feature area missing from
//    IS2.MENU), empty (IS2.MENU = []), error (IS2.MENU unreadable: role=alert card, 다시 그리기 by keyboard redraws), the P1
//    layer failing (data.js 404: tree whole, the file count 확인 불가, shell notice shown), the tree's own file missing
//    (screen-tree-live.js 404: the screen's error card, no tree item, shell notice).
//  - Boundaries everywhere: zero requests leave the origin (route level and page level), zero CSP violations, no console error but
//    the provoked ones, no [style], nothing stored; the public files read by #/tree are exactly none (fresh load and route
//    change); no board example value and no percentage on the page.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');

// The spec's numbered lines (the body after the header's ---), as the screen must show them.
const SPEC = fs.readFileSync(path.join(R.ROOT, 'docs/SPEC/FUNCTION_HIERARCHY_v1.0.md'), 'utf8');
const BODY = SPEC.slice(SPEC.indexOf('\n---\n') + 5).split('\n');
const AREAS = [], FEATS = [];
for (const line of BODY) {
  let m = line.match(/^(\d)\. (.+)$/); if (m) { AREAS.push([m[1], m[2].trim()]); continue; }
  m = line.match(/^(\d+(?:\.\d+)+) (.+)$/); if (m) FEATS.push([m[1], m[2].trim()]);
}
assert.equal(AREAS.length, 9, 'spec areas 1-9'); assert.ok(FEATS.length > 100, 'spec features parsed');
const NAME = (no, name) => (no === '4.5' ? '나비효과' : name);// DC-17 (CHAIN-NAME): 4.5 = 나비효과; the spec text is left as written
const AREA_MENU = { 1: 'search', 2: 'qgv', 3: 'technical', 4: 'macro', 5: 'news', 6: 'portfolio', 7: 'prompts', 8: 'tree', 9: 'lab' };
const TREE_READS = [];// #/tree reads no public file
// Live-only files other routes read in this offline build (their 404 is the NOT_PUBLISHED state; the tree never asks them).
const LIVE_ONLY = ['sec-qgv2.json', 'sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json'];
// Board example values and words that must never show (SystemTree / MTree / TreeCommon).
const EXAMPLES = ['23위', '498', '수치 미정', '8축', '비교군 3', '상승 추세', '0.81', '메모 3개', '회복 후반', '확인 4', '77건', '10/19', '7회', 'QGV 72', '431', '504',
  '10/24', '2026-10-24', '상승 초입', '예시기업', '예시 값은'];
let phase = 'START';

(async () => {
  const s = await site.start();
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  let FILES = null;
  async function context(width) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const out = [], hold = { gate: null };
    await ctx.route('**/*', async (route) => {
      const u = new URL(route.request().url());
      if (u.origin !== s.origin) { out.push(u.href); await route.abort(); return; }
      if (hold.gate && u.pathname === '/data.js') await hold.gate;
      await route.continue();
    });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: [...LIVE_ONLY, 'data.js'] });
    return { ctx, page, seen, out, hold };
  }
  const dataReads = (from) => s.requests.slice(from).map((r) => r.name).filter((n) => n.endsWith('.json') || (FILES && FILES.includes(n))).sort();
  const settle = (page, ms = 200) => page.evaluate((t) => new Promise((r) => setTimeout(r, t)), ms);
  const rerender = async (page) => { await page.evaluate(() => window.dispatchEvent(new HashChangeEvent('hashchange'))); await page.locator('main[data-route=tree] [data-tree-state]:not([data-tree-state=loading])').waitFor(); };
  const active = (page) => page.evaluate(() => { const e = document.activeElement; return e && e.dataset ? e.dataset.treeNode || null : null; });
  const key = async (page, k, want) => { await page.keyboard.press(k); assert.equal(await active(page), want, phase + ': ' + k + ' → ' + want); };
  const expanded = (page, k) => page.locator('[data-tree-node="' + k + '"]').getAttribute('aria-expanded');
  const visible = (page) => page.evaluate(() => [...document.querySelectorAll('[role=treeitem]')].filter((a) => a.getClientRects().length).length);
  const statuses = (page) => page.locator('[data-node-status]').evaluateAll((n) => n.map((x) => [x.dataset.treeNode, x.dataset.nodeStatus]));
  // The registry's answer for every screen node (what the screen must show).
  const registry = (page) => page.evaluate(() => {
    const I = window.IS2, sc = (id) => (I.screen(id) && !I.isPlaceholder(id) ? 'ready' : 'pending'), out = [];
    for (const m of I.MENU) { out.push(['m:' + m.id, sc(m.id)]); if (m.id === 'qgv') out.push(['f:2.4', sc('company')]); }
    for (const d of I.DETAILS) out.push(['d:' + d.id, I.detail(d.id) ? 'ready' : 'pending']);
    return out;
  });
  async function boundaries(page, seen, out, label, { errors = [] } = {}) {
    assert.equal(await page.locator('[style]').count(), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(out, [], label + ': no request leaves the origin (route level)');
    assert.deepEqual(seen.outside, [], label + ': no request leaves the origin (page level)');
    assert.deepEqual(seen.errors.filter((e) => !errors.some((x) => x.test(e))), [], label + ': no console or page error');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    const text = await page.locator('main').innerText();
    for (const x of EXAMPLES) assert.ok(!text.includes(x), label + ': no board example value: ' + x);
    assert.ok(!text.includes('%'), label + ': no percentage');
    const st = await site.storage(page);
    assert.deepEqual([st.local, st.session, st.idb], [0, 0, 0], label + ': nothing stored on the device');
  }
  // Every focusable control of main is reached by Tab (the tree: its one tab stop), each with a focus ring.
  async function tabbing(page, label) {
    const n = await page.evaluate(() => {
      const els = [...document.querySelectorAll('main button, main a[href], main [tabindex]')].filter((e) => !e.disabled && e.tabIndex >= 0 && e.getClientRects().length && e.id !== 'main');
      els.forEach((e, i) => { e.dataset.k = String(i); });
      document.getElementById('main').focus();
      return els.length;
    });
    const got = new Set(); let ring = 0;
    for (let i = 0; i < n + 40; i++) {
      await page.keyboard.press('Tab');
      const a = await page.evaluate(() => { const e = document.activeElement, cs = getComputedStyle(e); return { k: e.dataset ? e.dataset.k : undefined, inMain: !!e.closest('main'), ring: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2 }; });
      if (!a.inMain) { if (got.size) break; continue; }
      if (a.k !== undefined) got.add(a.k); if (a.ring) ring++;
    }
    assert.equal(got.size, n, label + ': every control is reached by Tab (' + got.size + '/' + n + ')');
    assert.ok(ring >= got.size, label + ': each focused control shows a focus ring');
    assert.equal(await page.evaluate(() => [...document.querySelectorAll('main button')].filter((b) => !(b.getAttribute('aria-label') || b.textContent.trim())).length), 0, label + ': every button has a name');
    await page.evaluate(() => document.querySelectorAll('[data-k]').forEach((e) => { delete e.dataset.k; }));
  }

  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = (p) => { phase = width + ' ' + p; };
      const { ctx, page, seen, out, hold } = await context(width);
      // ---------------------------------------------------------------- first paint with the layer held back
      tag('held layer');
      let release; hold.gate = new Promise((r) => { release = r; });
      const at = s.requests.length;
      await page.goto(s.base + '#/tree', { waitUntil: 'domcontentloaded' });
      await page.locator('[data-tree-slot] [data-state=loading]').waitFor();
      assert.notEqual(await page.evaluate(() => window.IS2.loadState()), 'READY', phase + ': the layer is still held');
      assert.equal(await page.locator('[data-tree-slot] [data-state=loading]').getAttribute('role'), 'status');
      assert.equal(await page.locator('main h1').innerText(), 'n. 투자시스템 한 장 지도');
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['n-1'], phase + ': the skeleton section');
      assert.deepEqual([await page.locator('[data-tree-state]').getAttribute('data-tree-state'), await page.locator('[role=treeitem]').count()], ['loading', 0], phase + ': no tree before the layer');
      const MENU = await page.evaluate(() => window.IS2.MENU.map((m) => ({ id: m.id, no: m.no, ko: m.ko, href: window.IS2.href(m.id) })));
      const DETAILS = await page.evaluate(() => window.IS2.DETAILS.map((d) => ({ id: d.id, ko: d.ko })));
      const TOTAL = MENU.length + FEATS.length + 1 + DETAILS.length;
      const DEFAULT_VISIBLE = MENU.length + 1 + FEATS.filter(([no]) => no.split('.').length === 2).length + DETAILS.length;
      hold.gate = null; release();
      await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-tree]').waitFor();
      if (!FILES) FILES = await page.evaluate(() => [...window.IS2.data.FILES]);
      assert.equal(await page.locator('[role=treeitem]').count(), TOTAL, phase + ': the whole tree after the layer');
      assert.equal(await visible(page), DEFAULT_VISIBLE, phase + ': menus and 세부 화면 open, features closed');
      assert.equal(await page.locator('[data-tree-slot] [data-state=loading]').count(), 0, phase + ': the loading line is gone');
      const early = await statuses(page);
      assert.deepEqual(early, await registry(page), phase + ': statuses from the registry');
      await settle(page);
      tag('reads');
      assert.deepEqual(dataReads(at), TREE_READS, phase + ': a fresh open of #/tree reads no public file');

      // ---------------------------------------------------------------- content
      tag('content');
      assert.equal(await page.locator('main').getAttribute('data-route'), 'tree');
      assert.equal(await page.locator('main h1').innerText(), 'n. 투자시스템 한 장 지도');
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['n-1'], phase + ': one section (shell contract)');
      assert.equal(await page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'ready');
      const tree = page.locator('[role=tree]');
      assert.equal(await tree.count(), 1); assert.ok(await tree.getAttribute('aria-label'), phase + ': the tree is named');
      const nodes = await page.evaluate(() => [...document.querySelectorAll('[role=treeitem]')].map((a) => {
        const g = a.parentElement.closest('[role=group]'), owns = a.getAttribute('aria-owns');
        return { k: a.dataset.treeNode, level: Number(a.getAttribute('aria-level')), size: Number(a.getAttribute('aria-setsize')), pos: Number(a.getAttribute('aria-posinset')),
          exp: a.getAttribute('aria-expanded'), href: a.getAttribute('href'), parent: g ? g.previousElementSibling.dataset.treeNode : null, text: a.textContent,
          ownsOk: owns ? document.getElementById(owns) === a.nextElementSibling : !a.nextElementSibling, route: a.getAttribute('href') ? window.IS2.parse(a.getAttribute('href')) : null,
          tabindex: a.tabIndex, tag: a.tagName };
      }));
      const top = nodes.filter((n) => n.level === 1);
      assert.deepEqual(top.map((n) => n.k), [...MENU.map((m) => 'm:' + m.id), 'g:details'], phase + ': top level = IS2.MENU order + 세부 화면');
      for (const m of MENU) {
        const n = top.find((x) => x.k === 'm:' + m.id), area = AREAS.find(([no]) => AREA_MENU[no] === m.id);
        assert.ok(n.text.startsWith(m.no + '. ' + m.ko), phase + ': menu label ' + m.id);
        assert.ok(n.text.includes('기능 ' + area[0] + ' · ' + area[1]), phase + ': area meta ' + m.id);
        assert.equal(n.href, m.href, phase + ': menu route ' + m.id);
      }
      const feats = nodes.filter((n) => n.k.startsWith('f:'));
      assert.deepEqual(feats.map((n) => n.k.slice(2)), FEATS.map(([no]) => no), phase + ': every spec number, in spec order');
      for (const [no, name] of FEATS) {
        const n = feats.find((x) => x.k === 'f:' + no), parts = no.split('.'), parent = parts.length === 2 ? 'm:' + AREA_MENU[parts[0]] : 'f:' + parts.slice(0, -1).join('.');
        assert.ok(n.text.startsWith(no + ' ' + NAME(no, name)), phase + ': spec name ' + no + ' (' + n.text + ')');
        assert.equal(n.level, parts.length, phase + ': aria-level ' + no);
        assert.equal(n.parent, parent, phase + ': parent of ' + no);
        const want = no === '2.4' ? 'search' : AREA_MENU[parts[0]];
        assert.equal(n.route.id, want, phase + ': route of ' + no);
      }
      const det = nodes.filter((n) => n.k.startsWith('d:'));
      assert.deepEqual(det.map((n) => n.k.slice(2)), DETAILS.map((d) => d.id), phase + ': detail screens = IS2.DETAILS');
      for (const d of DETAILS) { const n = det.find((x) => x.k === 'd:' + d.id); assert.ok(n.text.startsWith(d.ko)); assert.deepEqual([n.route.id, n.route.params], ['detail', [d.id]]); assert.equal(n.parent, 'g:details'); }
      const grp = top.find((n) => n.k === 'g:details'); assert.equal(grp.href, null, phase + ': 세부 화면 has no route of its own'); assert.equal(grp.tag, 'DIV');
      for (const n of nodes) {
        const sibs = nodes.filter((x) => x.parent === n.parent && x.level === n.level);
        assert.equal(n.size, sibs.length, phase + ': setsize ' + n.k); assert.equal(n.pos, sibs.indexOf(n) + 1, phase + ': posinset ' + n.k);
        const kids = nodes.some((x) => x.parent === n.k);
        assert.equal(n.exp !== null, kids, phase + ': aria-expanded only on parents ' + n.k); assert.ok(n.ownsOk, phase + ': aria-owns names the group ' + n.k);
      }
      assert.equal(nodes.filter((n) => n.tabindex === 0).length, 1, phase + ': one tab stop in the tree');
      assert.equal(await page.locator('[role=treeitem][aria-current=page]').getAttribute('data-tree-node'), 'm:tree');
      // ---- statuses and the unfinished models
      tag('status');
      const reg = await registry(page);
      assert.deepEqual(await statuses(page), reg, phase + ': status = registry for every screen node, nothing else has one');
      for (const [k, st] of reg) assert.equal(await page.locator('[data-tree-node="' + k + '"] [data-status-chip]').innerText(), st === 'ready' ? '화면 있음' : '준비 중', phase + ': chip ' + k);
      assert.deepEqual(Object.fromEntries(reg.filter(([k]) => ['m:tree', 'm:search'].includes(k))), { 'm:search': 'ready', 'm:tree': 'ready' });
      const ready = reg.filter(([, st]) => st === 'ready').length;
      assert.equal(await page.locator('[data-tree-summary]').innerText(), '메뉴 · 기업 상세 · 세부 화면 기준: 화면 있음 ' + ready + ' · 준비 중 ' + (reg.length - ready));
      for (const [no, words] of [['4.1.1', '공식 국면 미산출'], ['4.2.1', '준비 중'], ['4.3.2', '준비 중'], ['4.5', '준비 중']])
        assert.match(await page.locator('[data-tree-node="f:' + no + '"] [data-prep]').innerText(), new RegExp(words), phase + ': ' + no + ' says ' + words);
      assert.match(await page.locator('[data-prep="8.1.3"]').innerText(), /준비 중[\s\S]*기능별 구현 분류[\s\S]*기능 상태 공개 자료/);
      assert.equal(await page.locator('[data-flow-step]').count(), 6, phase + ': 8.1.1 six steps');
      assert.deepEqual(await page.locator('[data-tree-block]').evaluateAll((n) => n.map((x) => x.dataset.treeBlock)), ['sources', '8.1.2', '8.1.1', '8.1.3', '8.1.4']);
      // ---- table 1-3 (8.1): personal data on this device only, the private layer as one static line, the public file count
      tag('two layers');
      const src = await page.locator('[data-tree-block=sources]').evaluate((e) => e.textContent);
      assert.ok(src.includes('보유 · 설정 · 노트 = 이 기기에만 · 공개 안 함') && src.includes('내 정보(이 기기에만 · 공개 안 함)'), phase + ': 내 정보 = 이 기기에만 · 공개 안 함');
      assert.match(await page.locator('[data-flow-step="① 자료"]').innerText(), /내 정보 = 이 기기에만 · 공개 안 함/);
      const all = await page.locator('main').evaluate((e) => e.textContent);
      assert.doesNotMatch(all, /내 정보[^·]{0,12}\(?비공개|노트 \(비공개\)|내 정보 = 비공개/, phase + ': device data is never called 비공개');
      assert.equal(await page.locator('[data-private-layer]').innerText(), '비공개 층: 로그인한 오너에게만 덧붙는 KIS 일봉·Lab 결과 (지금은 비공개 기능 준비 중)');
      assert.doesNotMatch(all.replace('비공개 층: 로그인한 오너에게만 덧붙는 KIS 일봉·Lab 결과 (지금은 비공개 기능 준비 중)', ''), /로그인|계정/, phase + ': no login / account words but the private-layer line');
      assert.equal(await page.locator('[data-private-panel]').count(), 0, phase + ': no private panel on the tree');
      assert.equal(await page.locator('[data-file-count]').getAttribute('data-file-count'), String(FILES.length));
      assert.equal(await page.locator('[data-file-count]').innerText(), '공개 파일 수 · ' + FILES.length + '개 (고정 목록 · 파일을 읽지 않고 셈)', phase + ': the fixed FILES count');
      assert.match(await page.locator('[data-prep="8.1.4"]').innerText(), /^공개 파일 기준 시각\(as_of\) 예시 · 준비 중 · 없는 것: 공개 파일을 읽는 연결/);
      assert.match(await page.locator('[data-prep="8.1.3"]').innerText(), /FUNCTION_STATUS 공개본/);
      await boundaries(page, seen, out, phase);

      // ---------------------------------------------------------------- keyboard
      tag('keyboard');
      await tabbing(page, phase);
      await page.locator('[data-tree-all=close]').focus();
      await page.keyboard.press('Tab');
      assert.equal(await active(page), 'm:search', phase + ': Tab after the buttons lands on the tree');
      const ring = await page.evaluate(() => { const cs = getComputedStyle(document.activeElement); return cs.outlineStyle === 'solid' && parseFloat(cs.outlineWidth) >= 2; });
      assert.ok(ring, phase + ': the focused node shows a focus ring');
      await key(page, 'ArrowDown', 'f:1.1'); await key(page, 'ArrowDown', 'm:qgv'); await key(page, 'ArrowUp', 'f:1.1');
      await key(page, 'ArrowDown', 'm:qgv'); await key(page, 'ArrowRight', 'f:2.1');
      await key(page, 'ArrowRight', 'f:2.1'); assert.equal(await expanded(page, 'f:2.1'), 'true', phase + ': → opens a closed node');
      await key(page, 'ArrowRight', 'f:2.1.1'); await key(page, 'ArrowRight', 'f:2.1.1');// a leaf: nothing
      await key(page, 'ArrowLeft', 'f:2.1'); await key(page, 'ArrowLeft', 'f:2.1'); assert.equal(await expanded(page, 'f:2.1'), 'false', phase + ': ← closes an open node');
      await key(page, 'ArrowLeft', 'm:qgv'); await key(page, 'ArrowLeft', 'm:qgv'); assert.equal(await expanded(page, 'm:qgv'), 'false');
      await key(page, 'ArrowDown', 'm:technical');// the closed menu's children are skipped
      await key(page, 'ArrowUp', 'm:qgv'); await key(page, 'ArrowRight', 'm:qgv'); assert.equal(await expanded(page, 'm:qgv'), 'true');
      await key(page, 'End', 'd:' + DETAILS[DETAILS.length - 1].id); await key(page, 'Home', 'm:search');
      await key(page, 'ArrowLeft', 'm:search'); await key(page, 'ArrowLeft', 'm:search');// closes, then nothing above a top node
      assert.equal(await expanded(page, 'm:search'), 'false'); await key(page, 'ArrowRight', 'm:search');
      await key(page, 'ArrowRight', 'f:1.1'); await key(page, 'ArrowDown', 'm:qgv'); await key(page, 'ArrowRight', 'f:2.1');
      await key(page, '*', 'f:2.1');
      for (const no of ['2.1', '2.2', '2.3', '2.4', '2.5']) assert.equal(await expanded(page, 'f:' + no), 'true', phase + ': * opens sibling ' + no);
      await key(page, 'ArrowDown', 'f:2.1.1');
      // Enter follows the link; the open nodes are kept in RAM across the route change.
      await page.keyboard.press('Enter');
      await page.locator('main[data-route=qgv]').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/qgv', phase + ': Enter follows the node link');
      await page.evaluate(() => { location.hash = '#/tree'; }); await page.locator('main[data-route=tree] [data-tree]').waitFor();
      for (const no of ['2.1', '2.2', '2.3', '2.4', '2.5']) assert.equal(await expanded(page, 'f:' + no), 'true', phase + ': open nodes kept after a route change ' + no);
      assert.equal(await expanded(page, 'm:search'), 'true');
      await boundaries(page, seen, out, phase, { errors: [/status of 404/] });

      // ---------------------------------------------------------------- pointer and the two buttons
      tag('pointer');
      await page.locator('[data-tree-node="f:3.1"]').scrollIntoViewIfNeeded();
      const before = await page.evaluate(() => location.hash);
      await page.locator('[data-tree-node="f:3.1"] [data-tree-toggle]').click();
      assert.equal(await expanded(page, 'f:3.1'), 'true', phase + ': the caret opens'); assert.equal(await page.evaluate(() => location.hash), before, phase + ': the caret does not navigate');
      await page.locator('[data-tree-node="f:3.1"] [data-tree-toggle]').click(); assert.equal(await expanded(page, 'f:3.1'), 'false', phase + ': the caret closes');
      await page.locator('[data-tree-node="g:details"]').click(); assert.equal(await expanded(page, 'g:details'), 'false', phase + ': 세부 화면 toggles');
      await page.locator('[data-tree-node="g:details"]').click(); assert.equal(await expanded(page, 'g:details'), 'true');
      await page.locator('[data-tree-all=open]').click();
      assert.equal(await visible(page), TOTAL, phase + ': 모두 펼치기 shows every node');
      tag('phone layout');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow with every node open');
      const boxes = await page.evaluate(() => [...document.querySelectorAll('[role=treeitem], main button, main [data-tree-block] a.lk')].filter((e) => e.getClientRects().length)
        .map((e) => { const r = e.getBoundingClientRect(); return { k: e.dataset.treeNode || e.textContent.trim(), right: r.right, left: r.left, h: r.height }; }));
      const W = await page.evaluate(() => window.innerWidth);
      assert.deepEqual(boxes.filter((b) => b.left < 0 || b.right > W + 0.5).map((b) => b.k), [], phase + ': every node and control inside the viewport');
      assert.deepEqual(boxes.filter((b) => b.h < 44).map((b) => b.k), [], phase + ': 44 px tap targets');
      if (phone) assert.equal(await page.locator('[data-tree-block=sources] .m-only').isVisible(), true, phase + ': the one-line 재료 box on the phone');
      else assert.equal(await page.locator('[data-tree-block=sources] .pc-only').isVisible(), true, phase + ': the six 재료 boxes on the PC');
      await page.locator('[data-tree-all=close]').click();
      assert.equal(await visible(page), MENU.length + 1, phase + ': 모두 접기 leaves the top level');
      assert.equal(await page.evaluate(() => { const a = [...document.querySelectorAll('[role=treeitem]')].find((x) => x.tabIndex === 0); return a && a.getClientRects().length > 0; }), true, phase + ': the tab stop stays on a shown node');
      await page.locator('[data-tree-node="m:technical"] [data-tree-toggle]').click();
      await page.locator('[data-tree-node="f:3.1"] > span').click();
      await page.locator('main[data-route=technical]').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/technical', phase + ': a label click follows the link');

      // ---------------------------------------------------------------- route change into #/tree reads nothing
      tag('route change');
      await settle(page);
      const at2 = s.requests.length;
      await page.evaluate(() => { location.hash = '#/tree'; }); await page.locator('main[data-route=tree] [data-tree]').waitFor(); await settle(page);
      assert.deepEqual(dataReads(at2), TREE_READS, phase + ': a route change into #/tree reads no public file');

      // ---------------------------------------------------------------- states
      tag('partial: one status unknown');
      await page.evaluate(() => { const I = window.IS2; window.__isP = I.isPlaceholder; I.isPlaceholder = (id) => { if (id === 'macro') throw Error('synthetic'); return window.__isP(id); }; });
      await rerender(page);
      assert.equal(await page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'partial');
      assert.equal(await page.locator('[data-tree-node="m:macro"]').getAttribute('data-node-status'), 'unknown');
      assert.equal(await page.locator('[data-tree-node="m:macro"] [data-status-chip]').innerText(), '상태 확인 불가');
      assert.equal(await page.locator('[data-tree-node="m:macro"] .chip.err').count(), 1);
      assert.match(await page.locator('[data-tree-partial=status]').innerText(), /일부 화면의 상태를 확인하지 못했습니다/);
      assert.match(await page.locator('[data-tree-summary]').innerText(), / · 상태 확인 불가 1$/);
      assert.deepEqual((await statuses(page)).filter(([k]) => k !== 'm:macro'), reg.filter(([k]) => k !== 'm:macro'), phase + ': the other statuses stay');
      assert.equal(await page.locator('[role=treeitem]').count(), TOTAL, phase + ': the tree stays whole');
      assert.equal(await page.locator('[data-tree-node="m:macro"]').getAttribute('href'), '#/macro', phase + ': the link stays');
      await boundaries(page, seen, out, phase, { errors: [/status of 404/] });
      await page.evaluate(() => { window.IS2.isPlaceholder = window.__isP; });
      tag('partial: area missing from MENU');
      await page.evaluate(() => { window.__menu = window.IS2.MENU; window.IS2.MENU = window.__menu.filter((m) => m.id !== 'lab'); });
      await rerender(page);
      assert.equal(await page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'partial');
      assert.equal(await page.locator('[data-tree-node="m:lab"]').count(), 0);
      assert.match(await page.locator('[data-tree-partial=menu]').innerText(), /메뉴 목록에 없는 기능 영역은 빼고 그렸습니다 · 기능 9$/);
      await boundaries(page, seen, out, phase, { errors: [/status of 404/] });
      tag('empty');
      await page.evaluate(() => { window.IS2.MENU = []; });
      await rerender(page);
      assert.equal(await page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'empty');
      assert.equal(await page.locator('[data-tree-card=empty] [data-mascot=plain]').count(), 1);
      assert.match(await page.locator('[data-tree-card=empty]').innerText(), /보여 줄 메뉴가 없습니다/);
      assert.equal(await page.locator('[role=treeitem]').count(), 0);
      await boundaries(page, seen, out, phase, { errors: [/status of 404/] });
      tag('error');
      await page.evaluate(() => { window.IS2.MENU = null; });
      await rerender(page);
      assert.equal(await page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'error');
      const err = page.locator('[data-tree-card=error]');
      assert.equal(await err.getAttribute('role'), 'alert');
      assert.equal(await err.locator('[data-mascot=alarm]').count(), 1);
      assert.match(await err.innerText(), /구조 트리를 그리지 못했습니다[\s\S]*메뉴 목록을 읽지 못했습니다/);
      assert.equal(await page.locator('[role=treeitem]').count(), 0);
      await tabbing(page, phase);
      await boundaries(page, seen, out, phase, { errors: [/status of 404/] });
      await page.evaluate(() => { window.IS2.MENU = window.__menu; });
      await page.locator('[data-tree-redraw]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-tree-state=ready] [data-tree]').waitFor();
      assert.equal(await page.locator('[role=treeitem]').count(), TOTAL, phase + ': 다시 그리기 draws the whole tree again');
      tag('registry change');
      const flip = await page.evaluate(() => {
        const I = window.IS2, d = I.DETAILS.find((x) => !I.detail(x.id)), m = I.MENU.find((x) => I.isPlaceholder(x.id));
        if (d) I.registerDetail(d.id, () => I.h('div', { class: 'screen' }, d.ko));
        if (m) I.register(m.id, () => I.h('div', { class: 'screen' }, m.ko));
        return { d: d ? d.id : null, m: m ? m.id : null };
      });
      assert.ok(flip.d, phase + ': a detail screen is still unregistered in this build');
      await rerender(page);
      assert.equal(await page.locator('[data-tree-node="d:' + flip.d + '"]').getAttribute('data-node-status'), 'ready', phase + ': a registered detail screen shows 화면 있음');
      if (flip.m) assert.equal(await page.locator('[data-tree-node="m:' + flip.m + '"]').getAttribute('data-node-status'), 'ready', phase + ': a real menu screen replacing its placeholder shows 화면 있음');
      assert.deepEqual(await statuses(page), await registry(page), phase + ': statuses follow the registry');
      await boundaries(page, seen, out, phase, { errors: [/status of 404/] });
      await ctx.close();

      // ---------------------------------------------------------------- the P1 layer failing
      tag('layer failure');
      s.fixture('data.js', { status: 404, body: '' });
      const f = await context(width);
      const at3 = s.requests.length;
      await f.page.goto(s.base + '#/tree'); await f.page.locator('[data-tree]').waitFor();
      await f.page.evaluate(() => window.IS2.ready.then(() => 'READY', () => 'FAILED'));
      await f.page.locator('[data-load-failed]').waitFor();
      assert.equal(await f.page.locator('[role=treeitem]').count(), TOTAL, phase + ': the tree stays whole when the layer fails');
      assert.deepEqual(await statuses(f.page), early, phase + ': the same statuses');
      assert.equal(await f.page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'ready');
      assert.deepEqual([await f.page.locator('[data-file-count]').getAttribute('data-file-count'), await f.page.locator('[data-file-count]').innerText()], ['NA', '공개 파일 수 · 확인 불가 (층을 불러오지 못함)'], phase + ': no count without the layer');
      await settle(f.page);
      assert.deepEqual(dataReads(at3), TREE_READS, phase + ': still no public file read');
      await boundaries(f.page, f.seen, f.out, phase, { errors: [/status of 404/] });
      s.fixture('data.js', null);
      await f.ctx.close();
      // ---------------------------------------------------------------- the tree's own file missing
      tag('logic file missing');
      s.fixture('screen-tree-live.js', { status: 404, body: '' });
      const g = await context(width);
      const at4 = s.requests.length;
      await g.page.goto(s.base + '#/tree'); await g.page.locator('[data-tree-card=error]').waitFor();
      assert.equal(await g.page.evaluate(() => window.IS2.ready.then(() => 'READY', (e) => e.message)), 'LOADER_FAILED screen-tree-live.js');
      assert.equal(await g.page.locator('[data-tree-state]').getAttribute('data-tree-state'), 'error');
      assert.equal(await g.page.locator('[data-tree-card=error]').getAttribute('role'), 'alert');
      assert.equal(await g.page.locator('[data-tree-card=error] [data-mascot=alarm]').count(), 1);
      assert.match(await g.page.locator('[data-tree-card=error]').innerText(), /구조 트리를 그리지 못했습니다[\s\S]*화면 파일을 불러오지 못했습니다/);
      assert.equal(await g.page.locator('[role=treeitem]').count(), 0);
      await g.page.locator('[data-load-failed]').waitFor();
      await settle(g.page);
      assert.deepEqual(dataReads(at4), TREE_READS, phase + ': no public file read');
      await boundaries(g.page, g.seen, g.out, phase, { errors: [/status of 404/] });
      s.fixture('screen-tree-live.js', null);
      await g.ctx.close();
    }
    console.log('web app tree: spec structure (' + FEATS.length + ' feature nodes), registry statuses, keyboard, pointer, states, phone layout and boundaries ok at 1440 and 390');
  } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
