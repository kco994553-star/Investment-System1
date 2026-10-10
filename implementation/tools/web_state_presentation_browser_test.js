// Production-shaped state presentation E2E on the public Pages build (PAGES_COCKPIT_URL). Test vectors only; no grant.
//   node web_state_presentation_browser_test.js [--evidence <dir>]
// U1 freshness badges, U2 persisted withheld/unavailable metadata, U3 ko/en strings, U4 render-error
// fallback; every check runs in ko-KR and en-US at a 390px viewport (plus a 360/1280 overflow pass).
//
// Current contract (GSQ-010 public price boundary): the public build serves an all-NOT_AVAILABLE data.json and app.js never
// renders producer sections from it, so the fixture folder of tools/build_web_state_presentation_fixture.py (and the demo
// build) can no longer be built or served: their build entry points are withheld. The fixture's pure in-memory functions
// (fixture_bundle / variants / manifest, the producer path make_snapshot -> assemble_bundle with an explicit clock) are still
// real schema-1 bundles, so they are run through the app's own render-time presentation (guardSections() + render())
// assigned to the page model in browser memory only: never served, never persisted, nothing built.
"use strict";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const TEXT = {
  "ko-KR": {
    FRESH: "FRESH · 만료 전", STALE: "STALE · 만료 후, 최신 아님", NOT_USABLE: "NOT_USABLE · 사용 기한 경과, 표시 보류",
    notUsableReason: "사용 기한(usable_until)이 지난 데이터라 표시하지 않습니다.",
    meta: { reason_code: "사유 코드", as_of: "생산자 데이터 시점", methodology: "방법론", freshness: "신선도", counts: "커버리지 집계" },
    notConnected: "운영 Snapshot이 연결되지 않았습니다.", noSnapshot: "이 기업의 Snapshot 미제공",
    loading: "데이터를 불러오는 중…", unavailable: "데이터를 열 수 없습니다.", retry: "다시 시도", home: "오늘의 투자 화면",
    holdings: "종목 보유", newsRel: "News / Relationships(뉴스·관계)",
    contexts: ["QGV context(QGV 맥락)", "Technical context(기술적 분석 맥락)", "Macro context(거시 맥락)"],
    researchSub: "프롬프트 → 맥락·변수 → 미리보기 → 복사", promptLibrary: "Prompt Library(프롬프트 라이브러리)",
    interest: "관심기업",
    actualWeight: "실제 비중", modelWeight: "모델 비중", snapshotWeight: "Snapshot에 포함 · 비중", portfolioStatus: "Portfolio status(보유 상태)",
    returnLabel: "수익률", missingValue: "미제공",
  },
  "en-US": {
    FRESH: "FRESH · Before expiry", STALE: "STALE · Past expiry, not current", NOT_USABLE: "NOT_USABLE · Past usable-until, withheld",
    notUsableReason: "Withheld: past the producer-declared usable_until.",
    meta: { reason_code: "Reason code", as_of: "Producer as-of", methodology: "Methodology", freshness: "Freshness", counts: "Coverage counts" },
    notConnected: "Operating snapshots are not connected.", noSnapshot: "No snapshot provided for this company",
    loading: "Loading data…", unavailable: "Cannot open data.", retry: "Retry", home: "Today's investment view",
    holdings: "holdings", newsRel: "News / Relationships",
    contexts: ["QGV context", "Technical context", "Macro context"],
    researchSub: "Prompt → Context / Variables → Preview → Copy", promptLibrary: "Prompt Library",
    interest: "Interests",
    actualWeight: "Actual weight", modelWeight: "Model weight", snapshotWeight: "Included in snapshot · Weight", portfolioStatus: "Portfolio status",
    returnLabel: "Return", missingValue: "Not provided",
  },
};
const SETTINGS_KEY = "investment.web.v1.settings";
const FIXTURE_MODULE = path.join(__dirname, "build_web_state_presentation_fixture.py");

// The fixture's literal vectors, computed in memory by its own pure functions (the withheld build entry points are not used).
function loadFixture() {
  const code = ["import importlib.util,json,sys", "sys.path.insert(0,sys.argv[1])",
    "spec=importlib.util.spec_from_file_location('web_state_fixture',sys.argv[2])",
    "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)",
    "b=m.fixture_bundle()",
    "print(json.dumps({'bundle':b,'manifest':m.manifest(b),'variants':m.variants(b)},ensure_ascii=False))"].join("\n");
  const run = spawnSync("python3", ["-I", "-c", code, path.resolve(__dirname, "../src"), FIXTURE_MODULE], { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
  assert.equal(run.status, 0, "fixture vectors could not be computed");
  return JSON.parse(run.stdout);
}

async function main() {
  const args = process.argv.slice(2);
  const option = (name) => { const i = args.indexOf(name); return i >= 0 && args[i + 1] ? args[i + 1] : null; };
  const evidence = path.resolve(option("--evidence") || process.env.WEB_STATE_PRESENTATION_EVIDENCE_DIR || process.env.PAGES_COCKPIT_EVIDENCE_DIR || path.join(os.tmpdir(), "web-state-presentation-evidence"));
  fs.mkdirSync(evidence, { recursive: true });
  const base = new URL(process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:9003/Investment-System1/");
  base.hash = "";
  if (!base.pathname.endsWith("/")) base.pathname += "/";
  const { bundle, manifest, variants } = loadFixture();
  assert.equal(manifest.kind, "WEB_STATE_PRESENTATION_FIXTURE_V1");
  assert.deepEqual(Object.keys(variants).sort(), [...manifest.variants].sort());
  const variant = (name) => variants[name];
  const company = manifest.company;
  // The unchanged production-shaped bundle plus a DEMO portfolio snapshot (the old demo build supplied it).
  const withPortfolio = (holding) => {
    const supplied = JSON.parse(JSON.stringify(bundle));
    supplied.portfolio = { state: "DEMO", as_of: manifest.as_of, source: "TEST VECTOR / demo portfolio",
      data: { role: "TEST DEMO / NOT ACTUAL", holdings: [holding] } };
    return supplied;
  };

  const launch = { headless: true };
  if (process.env.WEB_TEST_CHROMIUM_PATH) launch.executablePath = process.env.WEB_TEST_CHROMIUM_PATH;
  const checks = [], errors = [], observed = {}, traffic = { external: 0, unsafe: 0, failed_responses: 0 };
  let browser;
  async function check(name, fn) { await fn(); checks.push(name); console.log("PASS " + name); }

  // One context per page; the persisted display-locale setting is written before any page script runs.
  async function openPage(locale, { clock = manifest.browser_clock, width = 390, timezoneId = null } = {}) {
    const context = await browser.newContext({ viewport: { width, height: 844 }, ...(timezoneId ? { timezoneId } : {}) });
    await context.addInitScript(([key, value]) => { try { localStorage.setItem(key, value); } catch (e) { /* storage blocked */ } },
      [SETTINGS_KEY, JSON.stringify({ version: 1, display_locale: locale, source_language: "all" })]);
    await context.route("**/*", async (route) => {
      const request = route.request(), target = new URL(request.url());
      if (request.method() !== "GET" || request.postData()) { traffic.unsafe++; await route.abort(); return; }
      if (target.origin !== base.origin || !target.pathname.startsWith(base.pathname)) { traffic.external++; await route.abort(); return; }
      await route.continue();
    });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(`${locale} ${e.message}`));
    // The optional SEC sidecar is absent from a build without collection; any other failure stays an error.
    page.on("response", (response) => {
      if (response.status() >= 400 && !(response.status() === 404 && response.url() === new URL("sec-public-inputs.json", base).href)) traffic.failed_responses++;
    });
    if (clock) await page.clock.setFixedTime(new Date(clock));
    page.go = async (hash) => {
      await page.goto(new URL("#" + hash, base).href);
      await page.reload();
      await page.waitForFunction(() => typeof window.investmentSearch === "function" && !!document.querySelector("main h1"));
      assert.equal(await page.locator("html").getAttribute("lang"), locale);
    };
    // Run a bundle through the shipped render-time guard and re-render the current route (browser memory only).
    page.apply = async (data) => { await page.evaluate((data) => { D = guardSections(data); render(); }, data); };
    // First call loads the app; later calls navigate by hash inside the loaded document (the model is re-assigned each time).
    page.view = async (hash, data) => {
      if (!page.loaded) { await page.go(hash); page.loaded = true; await page.apply(data); return; }
      await page.evaluate(([hash, data]) => { D = guardSections(data); location.hash = "#" + hash; render(); }, [hash, data]);
      await page.waitForFunction((hash) => location.hash === "#" + hash && !!document.querySelector("main h1"), hash);
    };
    return page;
  }
  const html = (page) => page.evaluate(() => document.documentElement.outerHTML);
  const texts = (locator) => locator.evaluateAll((l) => l.map((e) => e.textContent.trim()));
  const metaOf = (page, name) => page.locator(`[data-producer-meta="${name}"] > [data-meta]`)
    .evaluateAll((l) => Object.fromEntries(l.map((e) => [e.dataset.meta, e.textContent])));
  const metaLine = (L, entries) => Object.fromEntries(Object.entries(entries).map(([k, v]) => [k, `${L.meta[k]}: ${v}`]));
  const unitOf = (locator) => locator.locator("xpath=ancestor::*[contains(concat(' ',normalize-space(@class),' '),' card ') or @id='news-pane' or @id='network-pane'][1]");
  const routes = ["home", "companies", "portfolio", "leaderboard", "news", "research", "settings",
    "company/" + encodeURIComponent(company), "entity/" + encodeURIComponent("MACRO:CPIAUCSL"),
    "qgv", "watchlist", "technical", "macro", "validation"];

  try {
    browser = await chromium.launch(launch);
    await check("public data.json is all NOT_AVAILABLE and stays unchanged by in-memory presentation", async () => {
      const probe = await openPage("ko-KR");
      await probe.go("home");
      const before = await probe.evaluate(() => fetch("data.json", { cache: "no-store" }).then((r) => r.text()));
      assert.ok(Object.keys(manifest.persisted).every((name) => JSON.parse(before)[name].state === "NOT_AVAILABLE"));
      await probe.apply(bundle);
      assert.equal(await probe.evaluate(() => fetch("data.json", { cache: "no-store" }).then((r) => r.text())), before);
      await probe.context().close();
    });
    for (const locale of ["ko-KR", "en-US"]) {
      const L = TEXT[locale];
      const page = await openPage(locale);

      await check(`${locale}: PPA-F08 missing or unusable ACTUAL never falls back to TARGET; finite ACTUAL is unchanged`, async () => {
        const cases = [
          { name: "omitted", expected: "NOT_AVAILABLE" },
          { name: "null", actual: null, expected: "NOT_AVAILABLE" },
          { name: "unavailable code", actual: "NOT_AVAILABLE", expected: "NOT_AVAILABLE" },
          { name: "numeric string", actual: "0.1234", expected: "NOT_AVAILABLE" },
          { name: "zero", actual: 0, expected: "0%" },
          { name: "nonzero", actual: 0.1234, expected: "12.34%" },
        ];
        const holdingCompany = bundle.companies[0];
        assert.ok(holdingCompany, "fixture company exists");
        for (const test of cases) {
          const holding = { company_id: holdingCompany.company_id, ticker: holdingCompany.ticker,
            target_weight: 0.3456, return: null };
          if (Object.hasOwn(test, "actual")) holding.actual_weight = test.actual;
          const supplied = withPortfolio(holding);
          assert.equal(supplied.portfolio.state, "DEMO", "test vectors remain DEMO");
          const p = await openPage(locale);
          try {
            await p.view("company/" + encodeURIComponent(holding.company_id), supplied);
            const status = p.locator("main section.card").filter({ has: p.getByRole("heading", { name: L.portfolioStatus, exact: true }) });
            assert.equal((await status.locator("p").first().innerText()).trim(), `${L.snapshotWeight} ${test.expected}`,
              `${locale} company ${test.name}: missing ACTUAL must not display TARGET 34.56%`);
            const companyTarget = status.locator('[data-weight-kind="TARGET"]');
            assert.equal(await companyTarget.count(), 1, "TARGET has its own company presentation element");
            assert.equal((await companyTarget.innerText()).trim(), `TARGET · ${L.modelWeight} 34.56%`,
              "persisted TARGET is explicitly labelled independently of the ACTUAL snapshot weight");
            assert.deepEqual(await p.evaluate(() => D), supplied, "company rendering preserves the supplied bundle");
            const holdingEvidence = JSON.parse(await status.locator("pre").textContent());
            assert.deepEqual(holdingEvidence, holding, "ACTUAL and TARGET stay separate and unchanged in Evidence");
            if (test.name === "omitted") await p.screenshot({ path: path.join(evidence, `ppa-f08-company-${locale}-390.png`), fullPage: true });
            await p.view("portfolio", supplied);
            const weight = p.locator(`main a[href="#company/${encodeURIComponent(holding.company_id)}"] .muted`);
            assert.equal((await weight.innerText()).trim(), `${L.actualWeight} ${test.expected} · ${L.returnLabel} ${L.missingValue}`,
              `${locale} portfolio ${test.name}: ACTUAL stays explicitly labelled`);
            const portfolioTarget = p.locator(`main a[href="#company/${encodeURIComponent(holding.company_id)}"] [data-weight-kind="TARGET"]`);
            assert.equal(await portfolioTarget.count(), 1, "TARGET has its own portfolio presentation element");
            assert.equal((await portfolioTarget.innerText()).trim(), `TARGET · ${L.modelWeight} 34.56%`,
              "persisted TARGET is explicitly labelled independently of the ACTUAL holding weight");
            assert.deepEqual(await p.evaluate(() => D), supplied, "portfolio rendering preserves the supplied bundle");
            assert.equal(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${locale} ${test.name}: 390px has no overflow`);
            if (test.name === "omitted") await p.screenshot({ path: path.join(evidence, `ppa-f08-portfolio-${locale}-390.png`), fullPage: true });
          } finally {
            await p.context().close();
          }
        }
      });

      await check(`${locale}: U1 LIVE, FRESH and STALE are separate labelled badges; STALE has its own style rule`, async () => {
        await page.view("home", bundle);
        // The state line of each section: LIVE is followed by its own freshness badge (other LIVE chips are navigation summaries).
        const stateBadges = page.locator(".state > .badge.LIVE");
        assert.equal(await stateBadges.count(), 3, "macro, changes and technical state lines");
        for (const badge of await stateBadges.all()) {
          assert.equal((await badge.textContent()).trim(), "LIVE", "LIVE badge carries no freshness suffix");
          const next = badge.locator("xpath=following-sibling::span[1]");
          assert.equal(await next.evaluate((e) => e.classList.contains("freshness")), true, "LIVE is followed by its freshness badge");
        }
        assert.deepEqual(await texts(page.locator(".badge.freshness.FRESH")), [L.FRESH], "macro FRESH (persisted)");
        // changes: persisted FRESH but expired at the view clock; technical: persisted STALE (inside More details).
        assert.deepEqual(await texts(page.locator(".badge.freshness.STALE")), [L.STALE, L.STALE]);
        assert.equal(await page.locator(".badge.LIVE .badge, .badge.LIVE:has-text('STALE')").count(), 0);
        const style = await page.evaluate(() => {
          const bg = (sel) => getComputedStyle(document.querySelector(sel)).backgroundColor;
          const rules = [...document.styleSheets].flatMap((s) => [...s.cssRules].map((r) => r.selectorText || ""));
          return { live: bg(".badge.LIVE"), fresh: bg(".badge.freshness.FRESH"), stale: bg(".badge.freshness.STALE"),
            notAvailable: bg(".badge.NOT_AVAILABLE"), staleRule: rules.includes(".badge.freshness.STALE"), liveRule: rules.includes(".badge.LIVE") };
        });
        assert.ok(style.staleRule && style.liveRule, "own style rules");
        assert.equal(new Set([style.live, style.fresh, style.stale, style.notAvailable]).size, 4, JSON.stringify(style));
        observed.badge_colors = style;
        await page.view("company/" + company, bundle);
        const technical = unitOf(page.locator(".badge.freshness.STALE")).first();
        assert.equal((await technical.locator(".badge.LIVE").innerText()).trim(), "LIVE");
        assert.ok((await technical.innerText()).includes("TEST_REGIME_STALE"), "STALE values stay visible, labelled STALE");
        assert.deepEqual(await texts(page.locator(".badge.freshness.FRESH")), [L.FRESH], "company detail macro");
      });

      await check(`${locale}: U1 the existing view-time rule decides FRESH vs STALE before/after expires_at; nothing else is derived`, async () => {
        const before = await openPage(locale, { clock: "2026-01-02T12:00:00Z" });
        await before.view("home", bundle);
        const changes = unitOf(before.locator(".badge.freshness").first());
        // Before changes.expires_at both changes and macro are FRESH; technical stays STALE (persisted).
        assert.deepEqual(await texts(before.locator(".badge.freshness.FRESH")), [L.FRESH, L.FRESH]);
        assert.deepEqual(await texts(before.locator(".badge.freshness.STALE")), [L.STALE]);
        assert.ok((await changes.innerText()).includes("TEST_CHANGES_VIEW_STALE"));
        await before.context().close();
      });

      await check(`${locale}: U1 an expires_at this browser cannot parse is never FRESH (fail closed as STALE)`, async () => {
        const card = (p, text) => p.locator("section.card", { hasText: text });
        const BEFORE = "2026-01-02T12:00:00Z";  // before changes.expires_at (2026-01-03T00:00:00Z)
        // (b) a valid future expires_at stays FRESH and (c) a valid past one is STALE (both clocks).
        for (const [clock, changes] of [[manifest.browser_clock, L.STALE], [BEFORE, L.FRESH]]) {
          const p = await openPage(locale, { clock });
          await p.view("home", bundle);
          assert.deepEqual(await texts(card(p, "TEST_CHANGES_VIEW_STALE").locator(".badge.freshness")), [changes], `changes at ${clock}`);
          assert.deepEqual(await texts(card(p, "TEST_REGIME_FRESH").locator(".badge.freshness")), [L.FRESH], `macro at ${clock}`);
          await p.context().close();
        }
        // (a) the same instant in ISO forms the producer contract accepts and Date.parse rejects, persisted FRESH:
        // STALE with the existing STALE badge at either clock, never FRESH; the values stay visible, labelled STALE.
        for (const [file, form] of Object.entries(manifest.unparsable_expiry)) {
          const served = variant(file);
          assert.equal(served.changes.expires_at, form);
          assert.equal(served.changes.producer.freshness, "FRESH");
          assert.equal(served.producer_manifest.sections.changes.freshness, "FRESH");
          for (const clock of [manifest.browser_clock, BEFORE]) {
            const p = await openPage(locale, { clock });
            await p.view("home", served);
            assert.equal(await p.evaluate((v) => Number.isNaN(Date.parse(v)), form), true, `precondition: Date.parse rejects ${form}`);
            const changes = card(p, "TEST_CHANGES_VIEW_STALE");
            assert.equal(await changes.count(), 1);
            assert.equal((await changes.locator(".badge.LIVE").innerText()).trim(), "LIVE");
            assert.deepEqual(await texts(changes.locator(".badge.freshness")), [L.STALE], `${form} at ${clock}`);
            assert.deepEqual(await texts(p.locator(".badge.freshness.FRESH")), [L.FRESH], `${form} at ${clock}: only macro is FRESH`);
            await p.context().close();
          }
        }
      });

      // One page per time zone; each case swaps the in-memory bundle and the fixed clock, then re-renders home.
      async function zonePage(timezoneId) {
        const p = await openPage(locale, { clock: null, timezoneId });
        await p.go("home");
        p.serve = async (data, clock) => {
          await p.clock.setFixedTime(new Date(clock));
          await p.apply(data);
          assert.equal(await p.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone), timezoneId);
          assert.equal(await p.evaluate(() => Date.now()), Date.parse(clock));
        };
        return p;
      }
      const changesCard = (p) => p.locator("section.card", { hasText: "TEST_CHANGES_VIEW_STALE" });

      await check(`${locale}: U1 an expires_at outside the strict ISO form ('(' / U+0000 separators) is never FRESH after its Python-parsed expiry, in every time zone`, async () => {
        const later = {};
        for (const timezoneId of manifest.timezones) {
          const p = await zonePage(timezoneId);
          for (const [file, info] of Object.entries(manifest.misparsed_expiry)) {
            const served = variant(file);
            assert.equal(served.changes.expires_at, info.form);
            assert.equal(served.changes.producer.freshness, "FRESH");
            assert.equal(served.producer_manifest.sections.changes.freshness, "FRESH");
            // Every clock is after the expiry contract.parse_ts reads (python_expires_at): never FRESH there.
            for (const clock of [...info.after_expiry_clocks, manifest.browser_clock]) {
              assert.ok(Date.parse(clock) > Date.parse(info.python_expires_at));
              await p.serve(served, clock);
              const changes = changesCard(p);
              assert.equal(await changes.count(), 1);
              assert.equal((await changes.locator(".badge.LIVE").innerText()).trim(), "LIVE");
              const where = `${JSON.stringify(info.form)} ${timezoneId} ${clock}`;
              assert.deepEqual(await texts(changes.locator(".badge.freshness")), [L.STALE], where);
              assert.equal(await changes.locator(".badge.freshness.FRESH").count(), 0, where);
              assert.deepEqual(await texts(p.locator(".badge.freshness.FRESH")), [L.FRESH], `${where}: only macro is FRESH`);
            }
            // How this browser's Date.parse alone reads the form in this zone, relative to the Python instant.
            const delta = (await p.evaluate((v) => Date.parse(v), info.form)) - Date.parse(info.python_expires_at);
            later[file] = Math.max(later[file] ?? -Infinity, delta);
          }
          await p.context().close();
        }
        // Precondition: in at least one zone Date.parse alone reads each form as a later instant than Python
        // (the bypass these variants pin); the strict-form gate is what keeps them STALE.
        for (const [file, delta] of Object.entries(later)) assert.ok(delta > 0, `${file}: Date.parse is never later than Python`);
        observed.misparsed_expiry_date_parse_minus_python_ms = later;
      });

      await check(`${locale}: U1 strict-form expires_at (Z, +-hh:mm, with and without fractional seconds) is FRESH before expiry and STALE after it, in every time zone`, async () => {
        for (const timezoneId of manifest.timezones) {
          const p = await zonePage(timezoneId);
          for (const [file, info] of Object.entries(manifest.strict_expiry)) {
            const served = variant(file);
            assert.equal(served.changes.expires_at, info.form);
            assert.equal(served.changes.producer.freshness, "FRESH");
            assert.equal(await p.evaluate((v) => Date.parse(v), info.form), Date.parse(info.python_expires_at), `${info.form} ${timezoneId}`);
            for (const [clock, expected] of [[info.fresh_clock, L.FRESH], [info.stale_clock, L.STALE]]) {
              await p.serve(served, clock);
              assert.deepEqual(await texts(changesCard(p).locator(".badge.freshness")), [expected], `${info.form} ${timezoneId} ${clock}`);
            }
          }
          await p.context().close();
        }
      });

      await check(`${locale}: U1 NOT_USABLE carried by the bundle is shown as withheld`, async () => {
        await page.view("leaderboard", bundle);
        assert.deepEqual(await texts(page.locator(".badge.NOT_AVAILABLE")), ["NOT_AVAILABLE"]);
        assert.deepEqual(await texts(page.locator(".badge.freshness.NOT_USABLE")), [L.NOT_USABLE]);
        assert.equal(await page.locator(".badge.LIVE").count(), 0);
        // The directory above the provided block lists price-free identities; the withheld block itself offers no ranking rows.
        assert.equal(await page.locator('main section.card:has([data-producer-meta="leaderboard"]) a[href^="#company/"]').count(), 0, "no withheld ranking rows");
        const variantPage = await openPage(locale);
        await variantPage.view("home", variant("variant-not-usable.json"));
        const notes = variantPage.locator("[data-withheld]");
        assert.deepEqual((await notes.evaluateAll((l) => l.map((e) => e.dataset.withheld))).sort(), ["changes", "news"]);
        for (const note of await notes.all()) {
          assert.equal((await note.textContent()).trim(), L.notUsableReason);
          const unit = unitOf(note);
          assert.equal(await unit.locator(".badge.NOT_AVAILABLE").count(), 1);
          assert.deepEqual(await texts(unit.locator(".badge.freshness")), [L.NOT_USABLE]);
          assert.equal(await unit.locator(".badge.LIVE, [data-producer-meta]").count(), 0);
        }
        const main = await variantPage.locator("main").textContent();
        assert.ok(main.includes("producer.freshness: NOT_USABLE") && main.includes("producer_manifest.sections.changes.freshness: NOT_USABLE"));
        for (const hash of routes) {
          await variantPage.view(hash, variant("variant-not-usable.json"));
          const h = await html(variantPage);
          for (const probe of manifest.withheld_probes) assert.ok(!h.includes(probe), `${hash} leaked ${probe}`);
        }
        await variantPage.view("news", variant("variant-not-usable.json"));
        assert.equal(await variantPage.locator("#news-list h3").count(), 0, "no withheld news rows");
        await variantPage.context().close();
      });

      await check(`${locale}: U2 withheld/unavailable sections show persisted reason_code, as_of, methodology, freshness, counts`, async () => {
        await page.view("company/" + company, bundle);
        assert.deepEqual(await metaOf(page, "qgv"), metaLine(L, { reason_code: "RESEARCH_DISPLAY_GRANT_NONE", as_of: manifest.as_of,
          methodology: "TEST_QGV / TEST_VECTOR_V1", freshness: "NOT_APPLICABLE", counts: "COMPLETE=3, NONE=1, PARTIAL=1" }));
        const main = await page.locator("main").innerText();
        assert.ok(main.includes(L.noSnapshot), "empty-state wording unchanged");
        await page.view("leaderboard", bundle);
        assert.deepEqual(await metaOf(page, "leaderboard"), metaLine(L, { reason_code: "EXPIRED_NOT_USABLE", as_of: "2025-12-30T00:00:00+00:00",
          methodology: "TEST_VECTOR / TEST_VECTOR_V1", freshness: "NOT_USABLE", counts: "expected_count=1, ranked_count=1" }));
        await page.view("home", bundle);
        const names = await page.locator("[data-producer-meta]").evaluateAll((l) => l.map((e) => e.dataset.producerMeta).sort());
        assert.deepEqual(names, ["news", "portfolio", "qgv", "relationships"], "only NOT_AVAILABLE sections; LIVE/FROZEN carry none");
        // Absent fields add nothing: the default registry persists no as_of and no counts for portfolio.
        assert.deepEqual(await metaOf(page, "portfolio"), metaLine(L, { reason_code: "PORTFOLIO_NO_ACTUAL_HOLDINGS",
          methodology: "NONE / NONE", freshness: "NOT_APPLICABLE" }));
        assert.ok((await page.locator("main").textContent()).includes(L.notConnected), "NOT_AVAILABLE reason wording unchanged");
        // Display only: every section that is not withheld is exactly the supplied section (nothing merged in).
        const view = await page.evaluate(() => Object.fromEntries(SECTION_NAMES.map((n) => [n, D[n]])));
        for (const [name, section] of Object.entries(view)) assert.deepEqual(section, bundle[name], name);
      });

      await check(`${locale}: U2 sparse bundle shows only what is persisted (no fabricated metadata)`, async () => {
        const sparse = await openPage(locale);
        for (const hash of ["home", "leaderboard", "company/" + company]) {
          await sparse.view(hash, variant("variant-sparse-metadata.json"));
          const names = await sparse.locator("[data-producer-meta]").evaluateAll((l) => l.map((e) => e.dataset.producerMeta));
          assert.deepEqual(names, hash === "leaderboard" ? [] : ["portfolio"], hash);
          assert.equal(await sparse.locator(".badge.freshness.NOT_USABLE").count(), 0, `${hash}: no persisted NOT_USABLE`);
        }
        await sparse.view("home", variant("variant-sparse-metadata.json"));
        assert.deepEqual(await metaOf(sparse, "portfolio"), metaLine(L, { reason_code: "ONLY_REASON_CODE_PERSISTED" }));
        await sparse.context().close();
      });

      await check(`${locale}: U2 only code-shaped reason_code and token-shaped methodology id/version are displayed`, async () => {
        const served = variant("variant-free-text-metadata.json");
        const p = await openPage(locale);
        for (const hash of routes) {
          await p.view(hash, served);
          const h = await html(p);
          for (const probe of manifest.free_text_probes) assert.ok(!h.includes(probe), `${hash} displayed ${probe}`);
        }
        // Free-text, multi-line, 65-character and lower-case values are omitted; nothing is truncated or rewritten.
        await p.view("company/" + company, served);
        assert.deepEqual(await metaOf(p, "qgv"), metaLine(L, { as_of: manifest.as_of, freshness: "NOT_APPLICABLE",
          counts: "COMPLETE=3, NONE=1, PARTIAL=1" }));
        await p.view("home", served);
        assert.deepEqual(await metaOf(p, "portfolio"), metaLine(L, { methodology: "NONE / NONE", freshness: "NOT_APPLICABLE" }));
        // 64-character code and token (the shape limits) are still displayed as persisted.
        assert.deepEqual(await metaOf(p, "relationships"), metaLine(L, {
          methodology: "NONE / " + manifest.edge["relationships.methodology.version"], freshness: "NOT_APPLICABLE" }));
        assert.deepEqual(await metaOf(p, "news"), metaLine(L, { reason_code: manifest.edge["news.reason_code"],
          methodology: "NONE / NONE", freshness: "NOT_APPLICABLE" }));
        await p.context().close();
      });

      await check(`${locale}: U2 a count is displayed only under a code/token-shaped key; free-text keys are omitted`, async () => {
        const served = variant("variant-free-text-count-keys.json");
        const p = await openPage(locale);
        for (const hash of routes) {
          await p.view(hash, served);
          assert.ok(!(await html(p)).includes(manifest.count_key_probe), `${hash} displayed a free-text count key`);
        }
        // Free-text, multi-line, 65-character, underscore-led, dashed and markup keys are omitted, never truncated;
        // 64-character and lower-case keys (inside the shape) are still displayed as persisted.
        const edgeCode = "EDGE_COUNT_KEY_" + "9".repeat(49), edgeCount = "edge_" + "9".repeat(53) + "_count";
        assert.equal(edgeCode.length, 64);
        assert.equal(edgeCount.length, 64);
        await p.view("company/" + company, served);
        assert.deepEqual(await metaOf(p, "qgv"), metaLine(L, { reason_code: "RESEARCH_DISPLAY_GRANT_NONE", as_of: manifest.as_of,
          methodology: "TEST_QGV / TEST_VECTOR_V1", freshness: "NOT_APPLICABLE",
          counts: `COMPLETE=3, NONE=1, PARTIAL=1, ${edgeCode}=6, lower_case_key=8, ${edgeCount}=10` }));
        await p.view("leaderboard", served);
        assert.deepEqual(await metaOf(p, "leaderboard"), metaLine(L, { reason_code: "EXPIRED_NOT_USABLE", as_of: "2025-12-30T00:00:00+00:00",
          methodology: "TEST_VECTOR / TEST_VECTOR_V1", freshness: "NOT_USABLE", counts: "expected_count=1, ranked_count=1" }));
        await p.context().close();
      });

      await check(`${locale}: U3 loading text and remaining UI strings follow the display locale`, async () => {
        const loading = await openPage(locale);
        let release;
        const blocked = new Promise((resolve) => { release = resolve; });
        await loading.route("**/data.json", async (r) => { await blocked; await r.continue(); });
        await loading.goto(base.href, { waitUntil: "domcontentloaded" });
        await loading.waitForFunction((t) => document.querySelector("main [role=status]")?.textContent === t, L.loading);
        release();
        await loading.locator("nav a[aria-current=page]").waitFor();
        await loading.context().close();
        await page.view("portfolio", bundle);
        const h2 = await texts(page.locator("main h2"));
        for (const heading of L.contexts) assert.ok(h2.includes(heading), heading);
        await page.view("company/" + company, bundle);
        assert.ok((await texts(page.locator("main h2"))).includes(L.newsRel));
        await page.go("research");
        assert.equal((await page.locator("main p.muted").innerText()).trim(), L.researchSub);
        assert.equal(await page.locator("#research-frame").getAttribute("title"), L.promptLibrary);
        await page.go("companies");
        await page.locator("#import").setInputFiles({ name: "broken.json", mimeType: "application/json", buffer: Buffer.from("{broken") });
        // The import failure notice is localized text plus the fixed code BACKUP_IMPORT_FAILED.
        await page.waitForFunction((expected) => document.querySelector("#notice").textContent.trim() === expected, locale === "en-US" ? "Import failed · BACKUP_IMPORT_FAILED" : "가져오기 실패 · BACKUP_IMPORT_FAILED");
      });

      await check(`${locale}: U3 demo holdings count, news/network labels and interest toggle label are localized`, async () => {
        const demo = await openPage(locale);
        const supplied = withPortfolio({ company_id: company, ticker: "NVDA", target_weight: 0.3456, actual_weight: 0.1234, return: null });
        await demo.view("home", supplied);
        assert.match((await demo.locator("main .metric").innerText()).trim(), new RegExp(`^\\d+ ${L.holdings}$`));
        // Track D's relationship page is not in the public build: the network pane is a NOT_AVAILABLE notice, never a frame.
        await demo.view("news", supplied);
        await demo.locator("#show-network").click();
        assert.equal(await demo.locator("#network-frame").count(), 0);
        assert.ok((await demo.locator("#network-pane").innerText()).includes("NOT_AVAILABLE"));
        await demo.view("company/" + company, supplied);
        const toggle = demo.locator(`button[data-star="${company}"]`);
        assert.ok((await toggle.getAttribute("aria-label")).endsWith(" " + L.interest), "interest toggle label follows the display locale");
        assert.equal((await toggle.textContent()).trim(), "☆");
        await toggle.click();
        assert.equal(await demo.locator(`button[data-star="${company}"][aria-pressed=true]`).count(), 1);
        assert.equal((await demo.locator(`button[data-star="${company}"]`).textContent()).trim(), "★");
        await demo.context().close();
      });

      await check(`${locale}: U4 a render error after hashchange shows the DATA UNAVAILABLE fallback, then recovers`, async () => {
        const broken = await openPage(locale);
        await broken.view("home", variant("variant-render-error.json"));
        assert.equal((await broken.locator("main h1").innerText()).trim(), L.home);
        const before = errors.length;
        await broken.evaluate(() => { location.hash = "#news"; });
        await broken.waitForFunction((t) => document.querySelector("main h1")?.textContent === t, L.unavailable);
        assert.equal((await broken.locator("main .eyebrow").innerText()).trim(), "DATA UNAVAILABLE");
        assert.equal((await broken.locator("#retry").innerText()).trim(), L.retry);
        await broken.evaluate(() => { location.hash = "#home"; });
        await broken.waitForFunction((t) => document.querySelector("main h1")?.textContent === t, L.home);
        assert.equal(errors.length, before, "no uncaught exception");
        await broken.context().close();
      });

      await check(`${locale}: 390px routes have no horizontal overflow with the state bundle applied`, async () => {
        for (const width of [360, 390, 1280]) {
          const sized = await openPage(locale, { width });
          for (const hash of routes) {
            await sized.view(hash, bundle);
            assert.equal(await sized.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${width} ${hash}`);
          }
          await sized.context().close();
        }
      });
      for (const hash of ["home", "leaderboard", "company/" + company]) {
        await page.view(hash, bundle);
        await page.screenshot({ path: path.join(evidence, `state-${hash.replace(/\W+/g, "-")}-${locale}-390.png`), fullPage: true });
      }
      await page.context().close();
    }
    await check("no page errors, external calls, unsafe requests or failed responses", async () => {
      assert.deepEqual(errors, []);
      assert.deepEqual(traffic, { external: 0, unsafe: 0, failed_responses: 0 });
    });
    const result = { kind: "WEB_STATE_PRESENTATION_BROWSER_VALIDATION_V2", mode: "public-build-in-memory-fixture", passed: true, checks, errors, traffic, observed,
      viewport: "390x844 (+360/1280 overflow)", browser_clock: manifest.browser_clock,
      runtime: { node: process.version, chromium: browser.version() },
      research_display: "NONE", frozen_grant: "NONE", live_grant: "NONE", real_data_validation: "NOT_RUN" };
    fs.writeFileSync(path.join(evidence, "browser-validation.json"), JSON.stringify(result, null, 2) + "\n");
    process.stdout.write(JSON.stringify({ passed: true, checks: checks.length }) + "\n");
  } finally {
    if (browser) await browser.close();
  }
}
main().catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
