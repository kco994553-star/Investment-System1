'use strict';
// 공통 분류 · 비공개 전달 (owner 2026-11-08 「통합 결과 수령」 2항: the held common classification bundle through the existing
// owner-checked private Worker, DC-44 pattern) in a real browser at 1440 and 390. Google and the private Worker are stand-ins;
// every part is Main's synthetic fixture (Codex functions on Codex cases, tools/web_app_classification_fixture.js uBundle) — no
// company record of the held bundle is here. Checks:
//  - Public by default: the company page shows 공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결 and the panel waits
//    for a sign-in; nothing goes to the Worker; a synthetic click does nothing.
//  - One click after sign-in reads the five parts, /kis/classification?part=view · technical · macro · qgv_links · dictionary,
//    one after another 5 s apart, each with the Bearer header only; the panel shows 비공개 보관본 · 인증 경로 · 게시본 아님, the
//    evaluation date, the hash, the data kind and the counts; the company block repaints from the delivered bundle (sector, the
//    accounting line kept apart: 회계모형 미확인 · 섹터가 확인돼도 QGV 비교집단 완결 아님), with the delivery words.
//  - Two populations apart: 운영504 (Universe504, the screens' records) and the expanded held issuer sample (its own denominators
//    and counts, never added to the 504 counts, never a company page or a technical security id).
//  - The same RAM bundle serves the QGV leaderboard's 공통 분류 filter without another read; another company page shows the
//    panel open and reads nothing; 접기 drops the bundle (the page and the QGV filter are back to NONE).
//  - Version pairs (Codex #520 41f2a25b): /1 + /1 and /2 + /2 read (policy words), a mixed pair refused whole; the expanded block
//    shows the official Q gate linkage for the catalog scope only and says the row-level screen is not built.
//  - 404 for the view → 자료 없음 and the source stays NONE; a view that breaks the contract → refused whole (ERROR), NONE;
//    a 403 drops the token (sign in again) and the bundle.
//  - Boundaries: no token or record id in storage, the address or another request; no style attribute, no CSP violation, no
//    horizontal overflow at 390.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_classification_fixture.js');

const NOW = '2026-11-08T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence-status.json'];
const TOKEN = ['memory', 'only', 'synthetic', 'classification', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STUB = 'window.__gisCfg=[];window.google={accounts:{oauth2:{initTokenClient:function(cfg){window.__gisCfg.push({scope:cfg.scope,igs:cfg.include_granted_scopes});'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const PARTS = ['view', 'technical', 'macro', 'qgv_links', 'dictionary', 'expanded_summary'];
const PANEL = 'common-classification-private';
// The delivered bundle: the synthetic universe bundle, one fully confirmed company given an unknown accounting model (Codex #516
// 4cf2e037: independent states) so the accounting line is seen apart from the sector line.
const BUNDLE = (() => { const b = JSON.parse(JSON.stringify(X.uBundle())), r = b.view.rows.find((x) => x.company_id === 'NASDAQ:ADBE');
  r.accounting = { id: null, status: 'UNKNOWN', reasons: ['ACCOUNTING_TEMPLATE_UNCONFIRMED'], evidence_refs: [] };
  // The expanded held issuer sample's summary (Codex #520 shape, made-up counts with 7s so the page shows where they go).
  b.expanded_summary = { schema_version: 'held-expanded-classification-summary/1', valuation_date: b.view.valuation_date, catalog_observed_at: '2026-09-25T08:20:49Z', catalog_age_days: 38,
    population_kind: 'OBSERVED_CATALOG_ISSUERS_NOT_INVESTMENT_ELIGIBLE_UNIVERSE', rank_scope: 'HELD_ISSUER_FACTOR_PERCENTILES_ONLY', full_market_denominator: null, full_market_coverage: null,
    new_security_ids: 0, official_universe_changed: false,
    catalog: { issuers: 777, ticker_observations: 977, sector: 77, accounting: 76, industry: 17, raw: 57, factor_score: 47, Q: 37, G: 27, V: 0, joint: 0, total: 0 },
    held_financial_subsample: { issuers: 177, ticker_observations: 277, sector: 75, accounting: 74, industry: 15, raw: 57, factor_score: 47, Q: 37, G: 27, V: 0, joint: 0, total: 0 },
    official_gate_connected: 47 };
  // Codex #523 calculation_counts on the same test view and summary (made-up counts; the page must show these, not fixed numbers).
  b.expanded_summary.calculation_counts = X.syntheticCounts(b.view, b.expanded_summary, { opQ: 7, opG: 17, heldGate: 27, catGate: 47 });
  return b; })();
const RECORD_IDS = BUNDLE.view.rows.map((r) => r.record_id).filter(Boolean);
// The held issuer delivery (Codex #524 shape, synthetic) tied to this bundle's expanded summary as served (its bytes and held scope).
const SUMMARY_TEXT = JSON.stringify(BUNDLE.expanded_summary);
// The first issuer names one Universe504 company of the public list (its code row links the company page) and one unknown id.
const LINKED_CODE = BUNDLE.view.rows[0].company_id;
// Codex #527 comparison outputs (Codex's comparison() on Codex's synthetic input). The synthetic coverage's operating scope is set to
// name the peer_shift result (its input hash and row count) and to carry all three gate decisions: a synthetic pairing for the screen.
const REPAIR = JSON.parse(require('node:fs').readFileSync(require('node:path').join(R.ROOT, 'implementation/tests/fixtures/input_repair_comparison/outputs.json'), 'utf8'));
const repairCase = (id) => JSON.parse(JSON.stringify(REPAIR.cases.find((c) => c.id === id).output));
const DELIVERY = X.heldDelivery(SUMMARY_TEXT, BUNDLE.expanded_summary.calculation_counts.scopes.held_financial_subsample, { firstCodes: [LINKED_CODE, 'ROW:NOT-IN-LIST'],
  coverageEdit: (c) => { const o = c.scopes.operating, x = repairCase('peer_shift');
    o.gate_decisions = { PASS: 1, UNKNOWN: 0, VALUE_EXCLUDED: 1 };
    o.context = { ...(o.context || {}), valuation_date: x.valuation_date, population: { ...((o.context || {}).population || {}), denominator: x.denominator },
      result_identity: { ...((o.context || {}).result_identity || {}), input_hash: x.after_input_hash } }; } });
const EXF = { expanded_manifest: 'manifest.json', expanded_index: 'expanded-index.json', expanded_coverage: 'coverage.json' };
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(X.mainSha(), X.MAIN_SHA256, 'Main fixture (Codex output) unchanged');
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  async function context(width) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
    const w = { log: [], answers: {}, unexpected: [], all: [] };
    await ctx.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url()), hd = req.headers();
      w.all.push(req.method() + ' ' + req.url());
      if (url.origin === s.origin) { await route.continue(); return; }
      if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
      if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (url.origin === WORKER && url.pathname === '/kis/classification' && req.method() === 'GET') {
        // The real Worker admits one owner request at a time, at least 5 s apart; the stand-in refuses the same way.
        const at = Date.now(), early = w.lastAt !== undefined && at - w.lastAt < 5000;
        if (early) { w.refused = (w.refused || 0) + 1; await route.fulfill({ status: 429, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ error: { code: 'RATE_LIMITED' } }) }); return; }
        w.lastAt = at;
        w.log.push({ at, path: url.pathname + url.search, auth: hd.authorization || null, cookie: hd.cookie || null, referer: hd.referer || null });
        const part = url.searchParams.get('part'), shard = url.searchParams.get('shard'), key = part === 'expanded_detail' ? 'expanded_detail/' + shard : part;
        const file = EXF[part] || (part === 'expanded_detail' ? 'expanded-detail/' + shard + '.json' : null);
        const a = (w.answers[key] || (() => file ? (DELIVERY.files[file] === undefined ? { status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } } : { status: 200, text: DELIVERY.files[file] })
          : { status: 200, body: BUNDLE[part], text: part === 'expanded_summary' ? SUMMARY_TEXT : undefined }))();
        await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: a.text !== undefined ? a.text : JSON.stringify(a.body) }); return;
      }
      w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    return { ctx, page, seen, w };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.innerText);
  const count = (page, sel) => page.locator(sel).count();
  const state = (page) => page.locator('[data-private-panel="' + PANEL + '"]').getAttribute('data-private-state');
  const go = async (page, hash, sel) => { await page.evaluate((h) => { location.hash = h; }, hash); if (sel) await page.locator(sel).first().waitFor({ timeout: 20000 }); };
  const DONE = '[data-cc]:not([data-cc=LOADING]):not([data-cc=NOT_LOADED])';
  const company = async (page, code) => { await go(page, '#/search'); await go(page, '#/company/' + encodeURIComponent(code), DONE); await page.locator('[data-private-expand=classification]').waitFor(); };
  async function signIn(page) {
    const btn = page.locator('[data-private-expand=classification]');
    await btn.click(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=classification]').textContent), null, { timeout: 20000 });
    await btn.click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=classification]').textContent));
    assert.equal(await state(page), 'READY', phase + ': signed in, still folded');
  }
  async function read(page) { await page.locator('[data-private-expand=classification]').click(); }
  async function boundaries(page, seen, w, label) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(w.unexpected, [], label + ': no other outside request');
    assert.deepEqual(seen.errors.filter((e) => !/status of (403|404|429)/.test(e)), [], label + ': no console or page error but the stand-in refusals');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    for (const l of w.log) assert.deepEqual([l.auth, l.cookie, l.referer], ['Bearer ' + TOKEN, null, null], label + ': Bearer header only, no cookie, no referrer');
    const st = await site.storage(page);
    assert.equal(st.session, 0, label + ': nothing in session storage');
    assert.deepEqual(site.leaks([...Object.values(st.localItems), ...Object.keys(st.localItems), page.url(), await page.evaluate(() => JSON.stringify(history.state)), ...seen.errors, ...w.all.filter((u) => !u.includes(WORKER))],
      [TOKEN, ...RECORD_IDS]), [], label + ': no token or record id in storage, the address, the console or another request');
  }

  // The policy version pair (dictionary /2 + map /2, Codex #520 41f2a25b) on the same synthetic records.
  const POL = { version: 'common-sector-boundaries/2026-11-08.1', source: 'owner:2026-11-08:common-classification-boundaries', approved_date: '2026-11-08', recorded_at: '2026-11-08T08:05:49Z' };
  const v2view = { ...JSON.parse(JSON.stringify(BUNDLE.view)), dictionary_version: 'common-industry-dictionary/2', mapping_version: 'common-classification-map/2', boundary_policy: POL };
  const v2dict = { ...JSON.parse(JSON.stringify(BUNDLE.dictionary)), version: 'common-industry-dictionary/2', exceptions: { REIT: 'FINANCIALS_UPPER_SECTOR_ACCOUNTING_INDEPENDENT_NOT_ALL_REAL_ESTATE' },
    policy: { version: POL.version, approved_date: POL.approved_date, source: POL.source, book_direct_claim: false, automatic_company_assignment: false } };
  const POLICY_PANEL = /common-sector-boundaries\/2026-11-08\.1 · 시스템 대응 정책\(책의 직접 명시 아님\)/;
  const POLICY_LINE = /경계 정책판 · 시스템 대응 정책\(책의 직접 명시 아님\) · 회사별 분류는 근거 확인분만 · common-sector-boundaries\/2026-11-08\.1 · 승인 2026-11-08/;

  try {
    for (const width of [1440, 390]) {
      const tag = width < 720 ? '390' : '1440';
      phase = tag + ' public';
      const { ctx, page, seen, w } = await context(width);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-private-expand=classification]').waitFor();
      assert.equal(await page.locator('[data-cc]').first().getAttribute('data-cc'), 'NONE');
      assert.ok((await text(page, '.cc-block')).includes('공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결'), phase + ': NONE words before the delivery');
      assert.equal(await state(page), 'LOGIN_REQUIRED', phase + ': the panel waits for a sign-in');
      await page.evaluate(() => document.querySelector('[data-private-expand=classification]').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })));
      await page.waitForTimeout(200);
      assert.deepEqual([w.log.length, w.all.filter((u) => u.includes('accounts.google.com')).length], [0, 0], phase + ': a synthetic click sends nothing');
      ok(tag + ' public by default: NONE words, the panel waits, nothing sent');

      phase = tag + ' delivery';
      await signIn(page);
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');
      await read(page); await page.locator('[data-private-layer=classification]').waitFor({ timeout: 45000 });
      assert.deepEqual(w.log.map((l) => l.path), PARTS.map((p) => '/kis/classification?part=' + p), phase + ': exactly the six parts, in order');
      assert.equal(w.refused || 0, 0, phase + ': no read refused by the one-at-a-time limiter');
      assert.ok(w.log.slice(1).every((l, i) => l.at - w.log[i].at >= 5000), phase + ': one after another, 5 s apart');
      assert.match(await text(page, '[data-private-layer=classification]'), /^비공개 보관본 · 인증 경로 · 게시본 아님 · 같은 화면 같은 형식/);
      const dd = await page.locator('[data-private-meta=classification] dd').allTextContents();
      assert.deepEqual(dd.slice(0, 4), [BUNDLE.view.valuation_date, BUNDLE.view.dictionary_version + ' + ' + BUNDLE.view.mapping_version, BUNDLE.view.classification_hash.slice(0, 12), '합성 데이터 · 시험용'], phase + ': date, version pair, hash, data kind (no policy row on /1)');
      assert.equal(await count(page, '[data-cc-private-policy]'), 0, phase + ': a /1 bundle shows no boundary policy row');
      assert.equal(await page.locator('[data-cc-private-parts]').getAttribute('data-cc-private-parts'), PARTS.join(','));
      const n = (k) => BUNDLE.view.rows.filter((r) => r[k].status === 'CONFIRMED').length;
      assert.equal(await text(page, '[data-cc-count=rows]'), '기업 행 ' + BUNDLE.view.rows.length + '개(원래 분모 그대로)');
      assert.equal(await text(page, '[data-cc-count=sector]'), '섹터 확인 ' + n('sector') + '개');
      assert.equal(await text(page, '[data-cc-count=accounting]'), '회계모형 확인 ' + n('accounting') + '개 · 섹터와 따로 셈');
      assert.equal(await text(page, '[data-cc-count=peer]'), '섹터·회계모형 둘 다 확인 ' + (n('accounting')) + '개 · 나머지는 QGV 비교집단 완결 아님');
      // The company block repaints from the delivered bundle.
      await page.locator('.cc-block[data-cc=CONFIRMED], .cc-block[data-cc=SECTOR_ONLY]').waitFor();
      assert.equal(await count(page, '[data-cc-delivery=PRIVATE]'), 1, phase + ': delivery words in the company block');
      assert.equal(await page.locator('[data-cc-line=accounting]').getAttribute('data-cc-peer-complete'), 'YES');
      // Two populations apart.
      assert.equal(await count(page, '[data-cc-population=OPERATING_504]'), 1);
      assert.equal(await count(page, '[data-cc-population=EXPANDED_SAMPLE]'), 1);
      const ex = await text(page, '[data-cc-population=EXPANDED_SAMPLE]');
      assert.match(ex, /^확장 발행사 표본 · 별도 모집단 · 운영504와 합치지 않음/);
      assert.match(ex, /관측 카탈로그 전체 · 발행사 777 · 티커 관측 977 · 분류 단계: 섹터 77.* · 계산 단계: Q .*\(분류 수는 계산 완료 수가 아님\)/); assert.match(ex, /보유 재무 하위표본 · 발행사 177/);
      assert.match(ex, /전체시장 분모·커버리지 미산출 · 새 증권 ID 0/); assert.match(ex, /발행사 행 ID는 증권 ID가 아님/);
      assert.match(ex, /38일 전 · 평가일 상장 명부 아님/);
      const rowsN = BUNDLE.view.rows.length;
      assert.equal(await page.locator('[data-cc-calc=operating]').getAttribute('data-cc-calc-state'), 'OK');
      assert.match(await text(page, '[data-cc-calc=operating]'), new RegExp('Q 산출 7/' + rowsN + ' · G 산출 17/' + rowsN + ' · V 산출 \\S+ · 세 축 동시 \\S+ · 최종 총점 \\S+ · 평가일 ' + BUNDLE.view.valuation_date + ' · 원결과 집계\\(재계산 없음\\).* 위 분류 확인 수는 QGV 계산 완료율이 아님 · 95% 목표는 세 축 동시 \\+ 최종 총점 기준'), phase + ': the 504 Q / G counts from the delivered summary');
      assert.match(await text(page, '[data-cc-expanded-gate=catalog]'), /^공식 Q 관문 입력 연결 47\/777 · 관측 카탈로그 범위 · 관문 통과·새 섹터 Q 산출 아님 · 기존 Universe504 공식 Q 재생값\(확장 표본 Q 아님\)$/);
      assert.match(await text(page, '[data-cc-expanded-gate=held_financial_subsample]'), /^공식 Q 관문 입력 연결 27\/177 · 보유 재무 하위표본 범위 · 관문 통과·새 섹터 Q 산출 아님/);
      assert.equal(await count(page, '[data-cc-population=OPERATING_504] [data-cc-expanded-gate]'), 0, phase + ': the gate input lines stay in the expanded block');
      assert.equal(await count(page, '[data-cc-population=EXPANDED_SAMPLE] [data-held-browse] [data-held-open]'), 1, phase + ': the held issuer search waits for a click');
      assert.equal(await count(page, '[data-cc-expanded-rows]'), 0);
      // 7.1.2 화면 문맥 (queue item 8): the counts line links the prompt screen, which shows this bundle's date, population and
      // missing counts as a private display only — no field gets a value and the copied text never carries them.
      {
        const op = BUNDLE.expanded_summary.calculation_counts.scopes.operating, N = op.counts.Q.denominator;
        const gaps = [['Q', 'Q'], ['G', 'G'], ['V', 'V'], ['total', '총점']].filter(([k]) => op.counts[k].uncomputed > 0).map(([k, t]) => t + ' 미산출 ' + op.counts[k].uncomputed + '/' + N);
        assert.equal(await page.locator('[data-cc-prompt-context]').getAttribute('href'), '#/prompts/-/search');
        await page.locator('[data-cc-prompt-context]').click();
        await page.locator('[data-context-screen=PRIVATE]').waitFor({ timeout: 20000 });
        assert.equal(await count(page, '[data-prompt-error]'), 0, phase + ': "-" opens no prompt and no link error');
        assert.match(await text(page, '[data-context-screen] [data-context-row=screen]'), /^화면 문맥 · 공통 분류 보관 묶음 · 섹터 QGV 원결과 집계 \(재계산 없음\)비공개 결과 · 화면에만 보임$/);
        assert.equal(await text(page, '[data-context-screen] [data-context-row=asof]'), '평가일 · ' + op.valuation_date);
        assert.equal(await text(page, '[data-context-screen] [data-context-row=population]'), '모집단 · ' + op.population.id + ' · 코드 행 ' + N);
        assert.equal(await text(page, '[data-context-screen] [data-context-row=gaps]'), '자료 부족 · ' + gaps.join(' · '));
        assert.match(await text(page, '[data-context-not-copied]'), /칸 · 복사 글에 자동으로 넣지 않음/);
        await page.locator('[data-prompt-open]').first().click(); await page.locator('[data-prompt-fill]').waitFor();
        assert.equal(await page.locator('[data-prompt-context] [data-context-row=asof]').innerText(), '평가일 · ' + op.valuation_date, phase + ': the open prompt keeps the screen context');
        const vals = await page.evaluate(() => [...document.querySelectorAll('[data-prompt-fill] input, [data-prompt-fill] textarea, [data-prompt-fill] select')].map((e) => e.value));
        assert.ok(vals.every((v) => !v.includes(op.valuation_date) && !v.includes(op.population.id)), phase + ': no field takes the context ' + JSON.stringify(vals));
        const preview = await page.evaluate(() => document.querySelector('[data-prompt-block=copy]').textContent);
        assert.ok(!preview.includes(op.population.id) && !gaps.some((g) => preview.includes(g)), phase + ': the copy part carries no context');
        await page.goBack(); await page.locator('[data-cc-calc=operating]').waitFor({ timeout: 20000 });
      }
      assert.equal(await page.locator('[data-cc-private-version]').getAttribute('data-cc-private-version'), 'common-industry-dictionary/1');
      assert.equal(await text(page, '[data-cc-count=rows]'), '기업 행 ' + BUNDLE.view.rows.length + '개(원래 분모 그대로)', phase + ': the 504 count never takes the expanded issuers');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow with the panel open (long producer codes wrap)');
      ok(tag + ' one click reads six parts 5 s apart; panel words, date, hash, counts; 운영504 and the expanded sample apart; the company block repaints (PRIVATE)');

      // 확장 발행사 찾기 (owner 2026-11-09, Codex #524): index first (three reads 5 s apart), then one shard per chosen issuer.
      phase = tag + ' held browse';
      {
        const held = BUNDLE.expanded_summary.calculation_counts.scopes.held_financial_subsample, N = held.population.denominator;
        const logAt = w.log.length;
        if (tag === '390') {
          // A delivery that names another summary is refused whole; the button stays for another try.
          const m = JSON.parse(DELIVERY.files['manifest.json']); m.identity.summary.sha256 = 'f'.repeat(64);
          // re-sealed (identity_hash recomputed), so the refusal is the anchor itself, not a damaged manifest
          m.identity_hash = require('node:crypto').createHash('sha256').update(require('../src/investment_system/product/web_app/expanded-issuers.js').canonical(m.identity)).digest('hex');
          w.answers.expanded_manifest = () => ({ status: 200, text: JSON.stringify(m) });
          await page.locator('[data-held-open]').click();
          await page.locator('[data-held-state=ERROR]').waitFor({ timeout: 40000 });
          assert.match(await text(page, '[data-held-state]'), /확장 발행사 묶음을 쓰지 않음 · .*SUMMARY_MISMATCH/);
          assert.equal(await count(page, '[data-held-query]'), 0, phase + ': no search over a refused delivery');
          delete w.answers.expanded_manifest; await page.waitForTimeout(5200);
        }
        const reads0 = w.log.length;
        await page.locator('[data-held-open]').click();
        await page.locator('[data-held-state=READY]').waitFor({ timeout: 40000 });
        assert.deepEqual(w.log.slice(reads0).map((x) => x.path), ['/kis/classification?part=expanded_manifest', '/kis/classification?part=expanded_index', '/kis/classification?part=expanded_coverage']);
        assert.match(await text(page, '[data-held-state]'), new RegExp('^확장 발행사 ' + N + '개 · 평가일 ' + held.valuation_date + ' · 합성 자료 · 시험용 · 목록표·색인·커버리지 검증됨$'));
        assert.match(await text(page, '[data-held-meta]'), new RegExp('발행사 ' + N + '개 · 운영504와 합치지 않음'));
        // Two issuers in one shard (the second needs no read), one in another shard.
        const byShard = {}; for (const id of DELIVERY.ids) (byShard[DELIVERY.shardOf(id)] = byShard[DELIVERY.shardOf(id)] || []).push(id);
        const pair = Object.values(byShard).find((v) => v.length >= 2), [a1, a2] = pair, other = DELIVERY.ids.find((id) => ![a1, DELIVERY.ids[0]].map(DELIVERY.shardOf).includes(DELIVERY.shardOf(id)));
        const pick = async (id) => { await page.locator('[data-held-query]').fill(id); await page.locator('[data-held-result="' + id + '"] button').click(); };
        const r1 = w.log.length; await pick(a1);
        await page.locator('[data-held-detail="' + a1 + '"]').waitFor({ timeout: 20000 });
        assert.deepEqual(w.log.slice(r1).map((x) => x.path), ['/kis/classification?part=expanded_detail&shard=' + DELIVERY.shardOf(a1)], phase + ': one shard read, never the whole delivery');
        const d1 = await text(page, '[data-held-detail="' + a1 + '"]');
        const even = DELIVERY.ids.indexOf(a1) % 2 === 0;
        assert.match(d1, even ? /Q 0 · G 50 · V 미산출/ : /Q 미산출 · G 20 · V 미산출/, phase + ': 0 is a value, null is 미산출');
        assert.match(d1, /카탈로그 관측 티커 · 상장 증명·증권 ID 아님/); assert.match(d1, /총점 없음 · 0으로 채우지 않음/);
        assert.match(d1, /순위 없음 · 비교집단 = 보관 카탈로그 점수 모집단\(전체시장 아님\)/); assert.match(d1, /관문 통과·새 Q 점수 아님/);
        assert.match(d1, /가격·기술 연결 안 됨/);
        assert.equal(await page.locator('[data-held-detail="' + a1 + '"] [data-held-evidence]').count(), 1);
        await page.waitForTimeout(5200);
        // 검색 → 기업 상세: the first issuer's code rows (a Universe504 code links its page; an unknown id stays text).
        const first = DELIVERY.ids[0];
        await page.locator('[data-held-query]').fill(first); await page.locator('[data-held-result="' + first + '"] button').click();
        await page.locator('[data-held-detail="' + first + '"]').waitFor({ timeout: 20000 });
        const links = await page.locator('[data-held-detail="' + first + '"] [data-held-company]').evaluateAll((n) => n.map((x) => [x.dataset.heldCompany, x.getAttribute('href')]));
        assert.deepEqual(links.map((x) => x[0]), [LINKED_CODE], phase + ': only the listed code links');
        assert.equal(links[0][1], '#/company/' + encodeURIComponent(LINKED_CODE));
        assert.match(await text(page, '[data-held-detail="' + first + '"] [data-held-code-rows]'), /ROW:NOT-IN-LIST/);
        await page.waitForTimeout(5200);
        const r2 = w.log.length; await pick(a2);
        await page.locator('[data-held-detail="' + a2 + '"]').waitFor({ timeout: 20000 });
        assert.equal(w.log.length, r2, phase + ': a shard already read and checked is not read again');
        // A changed shard is that issuer's 연결 오류; the index and the search stay.
        const bad = DELIVERY.files['expanded-detail/' + DELIVERY.shardOf(other) + '.json'].replace('SYNTHETIC', 'SYNTHETIc');
        w.answers['expanded_detail/' + DELIVERY.shardOf(other)] = () => ({ status: 200, text: bad });
        await pick(other);
        await page.locator('[data-held-detail-error]').waitFor({ timeout: 20000 });
        assert.equal(await page.locator('[data-held-detail-error]').getAttribute('data-held-detail-error'), 'DELIVERY_HASH_MISMATCH');
        assert.equal(await count(page, '[data-held-result="' + other + '"]'), 1, phase + ': the search stays');
        delete w.answers['expanded_detail/' + DELIVERY.shardOf(other)];
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow with a detail open');
        // Coverage by stage (owner 2026-11-09): pipeline order, two units for 운영504, gate decisions apart, VALUE_EXCLUDED is not a loss.
        await page.locator('[data-held-coverage] > summary').click();
        const opStages = await page.locator('[data-held-scope=operating] [data-held-stages="issuers:axes"] [data-held-stage]').evaluateAll((n) => n.map((x) => x.dataset.heldStage));
        assert.deepEqual(opStages, ['sector', 'accounting', 'required_components_present', 'any_raw', 'all_default_raw', 'any_factor_scores', 'all_default_factor_scores', 'Q', 'G', 'V', 'joint'], phase + ': stages in order up to 세 축 동시');
        assert.deepEqual(await page.locator('[data-held-scope=operating] [data-held-stages="issuers:total"] [data-held-stage]').evaluateAll((n) => n.map((x) => x.dataset.heldStage)), ['pre_gate_total', 'total', 'all_axes_and_total']);
        assert.equal(await count(page, '[data-held-scope=operating] [data-held-stages="code_rows:axes"]'), 1, phase + ': code rows are their own unit');
        assert.deepEqual(await page.locator('[data-held-gate=operating] [data-held-gate-decision]').evaluateAll((n) => n.map((x) => x.dataset.heldGateDecision)), ['PASS', 'UNKNOWN', 'VALUE_EXCLUDED']);
        assert.match(await text(page, '[data-held-gate=operating] [data-held-gate-decision=VALUE_EXCLUDED]'), /^V 총점 반영 제외\(VALUE_EXCLUDED\) · 기업 탈락·자료 미수집 아님 1\/2$/);
        assert.match(await text(page, '[data-held-gate=operating] [data-held-gate-decision=UNKNOWN]'), /^관문 판정 불가\(UNKNOWN\) · 최종 총점·순위 없음 0\/2$/, phase + ': 0 stays 0');
        assert.ok(!/^관문/m.test((await page.locator('[data-held-causes=operating] li').allTextContents()).join('\n')), phase + ': the merged gate cause is not a loss cause');
        assert.match(await text(page, '[data-held-target=operating]'), /^95% 목표\(원래 모집단\) · 기준 Q·G·V 세 축 동시 \+ 최종 총점 · 운영504 고유 발행사/);
        assert.match(await text(page, '[data-held-coverage]'), /분류 확인 수나 원지표 수는 QGV 계산 완료율이 아님/);
        // 입력 연결 수정 전후 비교 (Codex #527): keyboard; a comparison for another result is refused and the bundle stays; then the
        // comparison for this result; nothing stored.
        const store0 = await page.evaluate(() => [Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]);
        w.answers.input_repair = () => ({ status: 200, body: repairCase('peer_minimum') });
        const q0 = w.log.length; await page.locator('[data-repair-open]').focus(); await page.keyboard.press('Enter');
        await page.locator('[data-repair-state=ERROR]').waitFor({ timeout: 20000 });
        assert.deepEqual(w.log.slice(q0).map((x) => x.path), ['/kis/classification?part=input_repair']);
        assert.match(await text(page, '[data-repair-state]'), /지금 받은 결과와 다른 결과의 비교입니다 · COMPARISON_RESULT_MISMATCH .* 위 묶음은 그대로$/);
        assert.equal(await count(page, '[data-held-query]'), 1, phase + ': the bundle and search stay');
        assert.equal(await count(page, '[data-repair-axis]'), 0);
        await page.waitForTimeout(5200);
        w.answers.input_repair = () => ({ status: 200, body: repairCase('peer_shift') });
        await page.locator('[data-repair-open]').focus(); await page.keyboard.press('Enter');
        await page.locator('[data-repair-state=READY]').waitFor({ timeout: 20000 });
        assert.match(await text(page, '[data-repair-state]'), /^입력 연결 수정 전후 비교 \(INPUT_CONNECTION_REPAIR\) · 평가일 .* · 분모 24 · 운영504 코드 행$/);
        assert.match(await text(page, '[data-repair-not]'), /요소·비중 변경 아님 · 분류 변경 아님 · 설정 변경 아님/);
        assert.equal(await text(page, '[data-repair-axis=Q]'), 'Q · 전 21 → 후 24 · 새로 산출 +3 · 산출 사라짐 0 · 기존 값 바뀜 20 / 24');
        assert.match(await text(page, '[data-repair-shift]'), /기업 실적 개선·전략 성과 아님$/);
        assert.deepEqual(await page.evaluate(() => [Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]), store0, phase + ': nothing stored');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow with coverage and comparison open');
        delete w.answers.input_repair;
        await page.waitForTimeout(5200);
        await page.waitForTimeout(5200);
        assert.ok(w.log.length > logAt);
      }
      ok(tag + ' held browse: index (3 reads) checked against the summary; search → one shard per issuer; a cached shard is not read again; a changed shard is that detail only');

      // 공통 산업 → 매크로 근거 (owner 2026-11-09, Codex #525): one click, one read; refused when made from another classification.
      phase = tag + ' industry macro';
      {
        const IM = JSON.parse(require('node:fs').readFileSync(require('node:path').join(R.ROOT, 'implementation/tests/fixtures/industry_macro_main/outputs.json'), 'utf8'));
        const base = IM.cases.find((c) => c.id === 'base').output;
        if (tag === '1440') {
          w.answers.industry_macro = () => ({ status: 200, body: base });
          await page.locator('[data-im-open]').click();
          await page.locator('[data-im-state=ERROR]').waitFor({ timeout: 20000 });
          assert.match(await text(page, '[data-im-state]'), /다른 분류로 만든 조회입니다 · CLASSIFICATION_CONTEXT_MISMATCH/);
          await page.waitForTimeout(5200);
        }
        const sel = await page.evaluate(() => { const x = window.IS2.selection.get(); return x && x.id; });
        const q = JSON.parse(JSON.stringify(base));
        q.classification_context = { valuation_date: BUNDLE.view.valuation_date, classification_hash: BUNDLE.view.classification_hash,
          dictionary_version: BUNDLE.view.dictionary_version, mapping_version: BUNDLE.view.mapping_version };
        q.companies[0].company_id = sel;
        w.answers.industry_macro = () => ({ status: 200, body: q });
        const r0 = w.log.length;
        await page.locator('[data-im-open]').click();
        await page.locator('[data-im-state=READY]').waitFor({ timeout: 20000 });
        assert.deepEqual(w.log.slice(r0).map((x) => x.path), ['/kis/classification?part=industry_macro']);
        assert.match(await text(page, '[data-im-state]'), /^기업 행 2 · 산업 연결 2 · 활성 대응 1 · 계열 1 · 합성 자료 · 시험용$/);
        assert.match(await text(page, '[data-im-not]'), /산업 연결·국면 판정 아님/);
        assert.match(await text(page, '[data-im-keeps]'), /기존 매크로 현재 조회는 그대로/);
        assert.equal(await page.locator('[data-im-company]').getAttribute('data-im-status'), 'LINKED');
        assert.match(await text(page, '[data-im-series]'), /SYN:SERIES · 0 hours/, phase + ': 0 stays 0');
        assert.match(await text(page, '[data-im-mappings]'), /복수 산업 대응\(비중 없음 · 나누거나 합치지 않음\)/);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow');
        delete w.answers.industry_macro;
        await page.waitForTimeout(5200);
      }
      ok(tag + ' industry macro: one read; another classification refused; summary, the selected company\'s link, series 0 kept, not a regime');

      phase = tag + ' same bundle';
      const before = w.log.length;
      await company(page, 'NASDAQ:ADBE');
      assert.equal(await page.locator('[data-private-expand=classification]').getAttribute('aria-expanded'), 'true', phase + ': another page shows the panel open');
      assert.equal(await page.locator('[data-cc-line=accounting]').getAttribute('data-cc-accounting'), 'UNKNOWN');
      assert.equal(await text(page, '[data-cc-line=accounting]'), '회계모형 회계모형 미확인 · 섹터가 확인돼도 QGV 비교집단 완결 아님', phase + ': the accounting line apart');
      assert.equal(await page.locator('[data-cc-line=accounting]').getAttribute('data-cc-peer-complete'), 'NO');
      assert.equal(await page.locator('[data-cc-line=sector]').evaluate((e) => /확인|정보기술|IT|섹터/.test(e.innerText)), true);
      await go(page, '#/macro', 'main[data-route=macro]'); await go(page, '#/qgv', 'main[data-route=qgv]');
      await page.locator('[data-cc-filter]:not([data-cc-filter=NONE])').first().waitFor({ timeout: 20000 });
      assert.equal(w.log.length, before, phase + ': the QGV filter and another company read the same RAM bundle, no new read');
      ok(tag + ' the same RAM bundle on another company (accounting line apart) and the QGV filter, no new read');

      phase = tag + ' fold';
      await company(page, 'NYSE:MMM');
      await page.locator('[data-private-expand=classification]').click();
      await page.locator('.cc-block[data-cc=NONE]').waitFor();
      assert.equal(await count(page, '[data-cc-delivery=PRIVATE]'), 0);
      await go(page, '#/macro', 'main[data-route=macro]'); await go(page, '#/qgv', 'main[data-route=qgv]');
      await page.locator('[data-cc-filter=NONE]').first().waitFor({ timeout: 20000 });
      await go(page, '#/prompts/-/search', 'main[data-route=prompts]'); await page.locator('[data-context-screen]').waitFor({ timeout: 20000 });
      assert.equal(await page.locator('[data-context-screen]').getAttribute('data-context-screen'), 'NONE', phase + ': a dropped bundle hands no context to the prompt screen');
      await boundaries(page, seen, w, phase);
      ok(tag + ' 접기 drops the bundle: company block and QGV filter back to NONE; boundaries');
      await ctx.close();
    }

    // ---------------- the /2 policy pair at 390 (mobile): panel rows, the company block's policy line, no overflow
    {
      phase = '390 policy pair';
      const { ctx, page, seen, w } = await context(390);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-private-expand=classification]').waitFor();
      await signIn(page);
      w.answers.view = () => ({ status: 200, body: v2view }); w.answers.dictionary = () => ({ status: 200, body: v2dict });
      await read(page); await page.locator('[data-private-layer=classification]').waitFor({ timeout: 45000 });
      await page.locator('[data-cc-delivery=PRIVATE]').waitFor();
      const dd = await page.locator('[data-private-meta=classification] dd').allTextContents();
      assert.deepEqual(dd.slice(0, 3), [v2view.valuation_date, 'common-industry-dictionary/2 + common-classification-map/2', POL.version + ' · 시스템 대응 정책(책의 직접 명시 아님)'], phase + ': date, version pair, policy');
      assert.match(await text(page, '[data-cc-policy]'), POLICY_LINE);
      assert.equal(await count(page, '[data-cc-line=accounting]'), 1, phase + ': the accounting line stays its own line');
      assert.match(await text(page, '[data-cc-calc=operating]'), /연결 오류\(COUNTS_VERSION_MISMATCH\) · 쓰지 않음/, phase + ': counts of the /1 view are set aside for a /2 view');
      assert.match(await text(page, '[data-cc-expanded-gate=held_financial_subsample]'), /연결 오류\(COUNTS_VERSION_MISMATCH\)/);
      await boundaries(page, seen, w, phase);
      ok('390: the /2 policy pair reads (version pair, policy rows, the company block policy line), no overflow; boundaries');
      await ctx.close();
    }

    // ---------------- refusals (1440)
    {
      phase = 'refusals';
      const { ctx, page, seen, w } = await context(1440);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-private-expand=classification]').waitFor();
      await signIn(page);
      w.answers.view = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await read(page); await page.locator('[data-private-panel="' + PANEL + '"][data-private-state=EMPTY]').waitFor({ timeout: 20000 });
      assert.match(await text(page, '[data-private-note=classification]'), /비공개 보관 분류 묶음이 아직 없습니다/);
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE', phase + ': a missing view leaves NONE');
      assert.equal(w.log.length, 1, phase + ': the required view missing stops the click');
      ok('404 view: 자료 없음, NONE kept, the click stops');
      const broken = JSON.parse(JSON.stringify(BUNDLE.view)); broken.rows[0].sector.status = 'MAYBE';
      w.answers.view = () => ({ status: 200, body: broken });
      await page.waitForTimeout(5300);
      await read(page); await page.locator('[data-private-panel="' + PANEL + '"][data-private-state=ERROR]').waitFor({ timeout: 45000 });
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE', phase + ': a refused bundle is never used');
      ok('a view that breaks the contract is refused whole (ERROR), NONE kept');
      // The policy version pair (dictionary /2 + map /2, Codex #520 41f2a25b): read, the policy line shown; a mixed pair refused whole.
      w.answers.view = () => ({ status: 200, body: v2view }); w.answers.dictionary = () => ({ status: 200, body: BUNDLE.dictionary });
      await page.waitForTimeout(5300);
      await read(page); await page.locator('[data-private-panel="' + PANEL + '"][data-private-state=ERROR]').waitFor({ timeout: 45000 });
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE', phase + ': a /2 view with a /1 dictionary is never used');
      ok('a mixed version pair (/2 view, /1 dictionary) is refused whole, NONE kept');
      w.answers.dictionary = () => ({ status: 200, body: v2dict }); await page.waitForTimeout(5300);
      await read(page); await page.locator('[data-private-layer=classification]').waitFor({ timeout: 45000 });
      await page.locator('[data-cc-delivery=PRIVATE]').waitFor();
      assert.equal(await page.locator('[data-cc-private-version]').getAttribute('data-cc-private-version'), 'common-industry-dictionary/2');
      assert.match(await text(page, '[data-cc-private-policy]'), POLICY_PANEL);
      assert.match(await text(page, '[data-cc-policy]'), POLICY_LINE);
      ok('the /2 + /2 policy pair reads: version and policy words in the panel and the company block');
      delete w.answers.view; delete w.answers.dictionary;
      w.answers.view = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await page.locator('[data-private-expand=classification]').click();          // 접기
      await page.locator('.cc-block[data-cc=NONE]').waitFor();
      await page.waitForTimeout(5300);
      await read(page);
      await page.waitForFunction(() => /다시 로그인하세요/.test(document.querySelector('[data-private-note=classification]').textContent), null, { timeout: 20000 });
      assert.equal(await state(page), 'LOGIN_REQUIRED', phase + ': a 403 drops the token');
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE');
      await boundaries(page, seen, w, phase);
      ok('403 drops the token; the source stays NONE; boundaries');
      await ctx.close();
    }
  } catch (e) { console.error('FAIL at ' + phase + ': ' + (e && e.stack || e)); process.exitCode = 1; }
  finally { await browser.close(); await s.close(); }
  if (!process.exitCode) console.log(JSON.stringify({ passed: true, checks: pass }));
})();
