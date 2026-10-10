// Render-time research guard (G3) E2E on the public Pages build (PAGES_COCKPIT_URL). Test vectors only; no grant.
//   node web_research_guard_browser_test.js [--evidence <dir>]
//
// Current contract (GSQ-010 public price boundary): the public build serves an all-NOT_AVAILABLE data.json and app.js never
// renders producer sections from it, so the hand-built schema-1 fixture of tools/build_web_research_guard_fixture.py can no
// longer be built or served (its build entry points are withheld). The fixture's pure in-memory vectors are still real
// schema-1 bundles, so this test (1) proves that a data.json carrying them is never rendered by the public build and
// (2) runs them through the app's own render-time guard, guardSections(), assigned to the page model in browser memory
// only (never served, never persisted), asserting the original G3 behaviour route by route.
"use strict";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const LIVE_OR_FROZEN = ".badge.LIVE, .badge.FROZEN_SNAPSHOT";
const REASON = {
  "ko-KR": "게시 승인이 없는 연구·잠정 결과라 표시하지 않습니다.",
  "en-US": "Withheld: research or provisional output without publication approval.",
};
const VALIDATION_REASON = {
  "ko-KR": "생산자 검증(validation)이 PASS가 아니라 표시하지 않습니다.",
  "en-US": "Withheld: producer validation is not PASS.",
};
const NOT_PROVIDED = { "ko-KR": "미제공", "en-US": "Not provided" };
// Home's Attention card; the fixture gives every section the same as_of, so the universe snapshot sentence is checked there only.
const ATTENTION = 'main section.card:has(.chips a[href="#companies"])';
const FIXTURE_MODULE = path.join(__dirname, "build_web_research_guard_fixture.py");

// The fixture's literal vectors, computed in memory by its own pure functions (the withheld build entry points are not used).
function loadFixture() {
  const code = ["import importlib.util,json,sys", "from pathlib import Path",
    "sys.path.insert(0,sys.argv[1])",
    "spec=importlib.util.spec_from_file_location('web_research_guard_fixture',sys.argv[2])",
    "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)",
    "print(json.dumps({'bundle':m.fixture_bundle(),'manifest':m.manifest(),'variants':m.validation_variants()},ensure_ascii=False))"].join("\n");
  const run = spawnSync("python3", ["-I", "-c", code, path.resolve(__dirname, "../src"), FIXTURE_MODULE], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  assert.equal(run.status, 0, "fixture vectors could not be computed");
  return JSON.parse(run.stdout);
}

async function main() {
  const args = process.argv.slice(2);
  const option = (name) => { const i = args.indexOf(name); return i >= 0 && args[i + 1] ? args[i + 1] : null; };
  const evidence = path.resolve(option("--evidence") || process.env.WEB_RESEARCH_GUARD_EVIDENCE_DIR || process.env.PAGES_COCKPIT_EVIDENCE_DIR || path.join(os.tmpdir(), "web-research-guard-evidence"));
  fs.mkdirSync(evidence, { recursive: true });
  const base = new URL(process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:9003/Investment-System1/");
  base.hash = "";
  if (!base.pathname.endsWith("/")) base.pathname += "/";
  const { bundle, manifest, variants } = loadFixture();
  assert.equal(manifest.kind, "WEB_RESEARCH_GUARD_FIXTURE_V1");
  const launch = { headless: true };
  if (process.env.WEB_TEST_CHROMIUM_PATH) launch.executablePath = process.env.WEB_TEST_CHROMIUM_PATH;
  const checks = [], errors = [], traffic = { external: 0, unsafe: 0, failed_responses: 0 };
  let browser;
  async function check(name, fn) { await fn(); checks.push(name); console.log("PASS " + name); }

  async function openPage(served = null) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.route("**/*", async (route) => {
      const request = route.request(), url = new URL(request.url());
      if (request.method() !== "GET" || request.postData()) { traffic.unsafe++; await route.abort(); return; }
      if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) { traffic.external++; await route.abort(); return; }
      if (served && url.pathname === new URL("data.json", base).pathname) {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(served) });
        return;
      }
      await route.continue();
    });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    // The optional SEC sidecar is absent from a build without collection; any other failure stays an error.
    page.on("response", (response) => {
      if (response.status() >= 400 && !(response.status() === 404 && response.url() === new URL("sec-public-inputs.json", base).href)) traffic.failed_responses++;
    });
    page.go = async (hash) => {
      await page.goto(new URL("#" + hash, base).href);
      await page.reload();
      await page.waitForFunction(() => typeof window.investmentSearch === "function" && !!document.querySelector("main h1"));
    };
    // Run a bundle through the shipped render-time guard and re-render the current route (browser memory only).
    page.apply = async (data) => {
      await page.evaluate((data) => { D = guardSections(data); render(); }, data);
    };
    page.view = async (hash, data) => { await page.go(hash); await page.apply(data); };
    page.setLocale = async (locale) => {
      await page.go("settings");
      await page.locator("#display-locale").selectOption(locale);
      assert.equal(await page.locator("html").getAttribute("lang"), locale);
    };
    return page;
  }

  try {
    browser = await chromium.launch(launch);
    const routes = ["home", "companies", "portfolio", "leaderboard", "news", "research", "settings",
      "company/" + encodeURIComponent(manifest.company), "entity/" + encodeURIComponent("MACRO:CPIAUCSL"),
      "qgv", "watchlist", "technical", "macro", "validation"];

    await check("public data.json is all NOT_AVAILABLE; a data.json carrying the research sections is never rendered", async () => {
      const probe = await openPage();
      await probe.go("home");
      const served = await probe.evaluate(() => fetch("data.json").then((r) => r.json()));
      assert.deepEqual(served.companies, []);
      for (const name of Object.keys(manifest.withheld).concat(Object.keys(manifest.rendered))) assert.equal(served[name].state, "NOT_AVAILABLE", name);
      await probe.context().close();
      // The same fixture bundle (valid LIVE, FROZEN, DEMO and research-marked sections) offered as the served data.json.
      for (const locale of ["ko-KR", "en-US"]) {
        const page = await openPage(bundle);
        await page.setLocale(locale);
        for (const hash of routes) {
          await page.go(hash);
          const html = await page.evaluate(() => document.documentElement.outerHTML);
          for (const text of [...manifest.withheld_probes, ...manifest.validation_probes, "44.44", "TEST DEMO / NOT ACTUAL"]) assert.ok(!html.includes(text), `${locale} ${hash} rendered ${text} from data.json`);
          assert.equal(await page.locator(".badge.LIVE, .badge.FROZEN_SNAPSHOT, .badge.DEMO").count(), 0, `${locale} ${hash}: served data.json produced a data-state badge`);
        }
        await page.context().close();
      }
    });
    for (const locale of ["ko-KR", "en-US"]) {
      const page = await openPage();
      await page.setLocale(locale);
      await check(`${locale}: withheld sections show NOT_AVAILABLE + reason and no value on every route`, async () => {
        for (const hash of routes) {
          await page.view(hash, bundle);
          const html = await page.evaluate(() => document.documentElement.outerHTML);
          for (const probe of manifest.withheld_probes) assert.ok(!html.includes(probe), `${locale} ${hash} leaked ${probe}`);
          assert.equal(await page.locator(".badge.FROZEN_SNAPSHOT").count(), 0, `${hash}: no FROZEN badge`);
          for (const badge of await page.locator(".badge.LIVE").all()) {
            assert.equal(await badge.evaluate((e) => !!e.closest(".card, #news-pane, #network-pane")?.querySelector("[data-withheld]")), false, `${hash}: LIVE badge on withheld unit`);
          }
          for (const note of await page.locator("[data-withheld]").all()) {
            assert.equal((await note.textContent()).trim(), REASON[locale]);
            const unit = note.locator("xpath=ancestor::*[contains(concat(' ',normalize-space(@class),' '),' card ') or @id='news-pane' or @id='network-pane'][1]");
            assert.equal(await unit.locator(".badge.NOT_AVAILABLE").count(), 1, `${hash}: withheld unit shows NOT_AVAILABLE`);
            assert.equal(await unit.locator(LIVE_OR_FROZEN).count(), 0);
            assert.ok(Object.keys(manifest.withheld).includes(await note.getAttribute("data-withheld")));
          }
        }
      });
      await check(`${locale}: each research-marked section is withheld where it is shown`, async () => {
        const expect = { home: ["changes", "news", "qgv", "technical"], portfolio: ["qgv", "technical"], technical: ["technical"],
          leaderboard: ["leaderboard"], news: ["news"], ["company/" + manifest.company]: ["news", "qgv", "technical"] };
        for (const [hash, names] of Object.entries(expect)) {
          await page.view(hash, bundle);
          const seen = await page.locator("[data-withheld]").evaluateAll((l) => [...new Set(l.map((e) => e.dataset.withheld))].sort());
          assert.deepEqual(seen, names, hash);
          for (const name of names) {
            assert.ok((await page.locator("main").textContent()).includes(manifest.withheld[name]), `${hash} marker ${name}`);
          }
        }
        await page.view("leaderboard", bundle);
        // The directory above the provided block lists price-free identities; the withheld block itself offers no ranking rows.
        assert.equal(await page.locator('main section.card:has([data-withheld="leaderboard"]) a[href^="#company/"]').count(), 0, "no withheld ranking rows");
        await page.view("news", bundle);
        assert.equal(await page.locator("#news-list [data-source-original], #news-list h3").count(), 0, "no withheld news rows");
      });
      await check(`${locale}: valid LIVE, legacy FROZEN universe, DEMO and NOT_AVAILABLE still render`, async () => {
        await page.view("home", bundle);
        const macro = page.locator(".home-grid section.card", { has: page.locator(".badge.LIVE") });
        assert.equal(await macro.count(), 1);
        assert.equal((await macro.locator(".badge.LIVE").innerText()).trim(), "LIVE");
        assert.ok((await macro.innerText()).includes("TEST_REGIME_VALID"));
        assert.equal(await page.locator(".banner").count(), 1, "DEMO banner");
        const hero = page.locator("section.hero");
        assert.equal((await hero.locator(".badge.DEMO").innerText()).trim(), "DEMO");
        assert.ok((await hero.innerText()).includes("TEST DEMO / NOT ACTUAL"));
        const main = await page.locator("main").textContent();
        // NOT_AVAILABLE relationships keep the producer's reason text (the GSQ-010 reason has no English translation yet).
        assert.ok(main.includes(bundle.relationships.reason), "NOT_AVAILABLE relationships reason");
        assert.ok((await page.locator(ATTENTION).innerText()).includes(bundle.universe.as_of), "legacy FROZEN universe as_of in Attention");
        await page.view("portfolio", bundle);
        assert.ok((await page.locator("main").textContent()).includes("44.44%"));
        await page.view("entity/" + encodeURIComponent("MACRO:CPIAUCSL"), bundle);
        assert.ok((await page.locator("main").textContent()).includes("33.33"));
        await page.view("company/" + manifest.company, bundle);
        const detail = await page.locator("main").textContent();
        assert.ok(detail.includes("TEST_EXPOSURE_VALID") && detail.includes("44.44%"));
        await page.view("companies", bundle);
        assert.ok((await page.locator("main p.meta").first().innerText()).includes("FROZEN_SNAPSHOT / DEMO"));
      });
      await page.view("home", bundle);
      await page.screenshot({ path: path.join(evidence, `guard-home-${locale}-390.png`), fullPage: true });
      await page.context().close();
    }
    await check("research-marked FROZEN universe is withheld in the companies legend", async () => {
      const variant = JSON.parse(JSON.stringify(bundle));
      // Producer validation PASS as the assembler persists it, so only the research half of the rule applies.
      variant.universe.producer = { producer_id: "test.web_research_guard", producer_version: "TEST_VECTOR_V1",
        methodology: { id: "TEST_VECTOR", version: "TEST_VECTOR_V1", status: "RESEARCH" },
        validation: { status: "PASS", checks: ["TEST_VECTOR_SHAPE_ONLY"] } };
      const vpage = await openPage();
      await vpage.setLocale("ko-KR");
      await vpage.view("companies", variant);
      const legend = await vpage.locator("main p.meta").first().innerText();
      assert.ok(legend.startsWith("NOT_AVAILABLE") && legend.includes(REASON["ko-KR"]) && !legend.includes("FROZEN"), legend);
      await vpage.view("home", variant);
      assert.ok(!(await vpage.locator(ATTENTION).innerText()).includes(bundle.universe.as_of), "no withheld universe as_of");
      await vpage.context().close();
    });
    await check("LIVE/FROZEN sections whose producer validation is not PASS are withheld (contract.py L194-199)", async () => {
      assert.deepEqual(Object.keys(variants).sort(), Object.keys(manifest.validation_withheld).sort());
      for (const [file, expect] of Object.entries(manifest.validation_withheld)) {
        const variant = variants[file];
        assert.equal(variant[expect.section].state, expect.state, file);
        const vpage = await openPage();
        for (const locale of ["ko-KR", "en-US"]) {
          await vpage.setLocale(locale);
          const marker = "producer.validation.status: " + (expect.status ?? NOT_PROVIDED[locale]);
          for (const hash of routes) {
            await vpage.view(hash, variant);
            const html = await vpage.evaluate(() => document.documentElement.outerHTML);
            if (expect.section === "macro") {
              for (const probe of manifest.validation_probes) assert.ok(!html.includes(probe), `${file} ${locale} ${hash} leaked ${probe}`);
              assert.equal(await vpage.locator(".badge.LIVE").count(), 0, `${file} ${hash}: no LIVE badge`);
            }
            for (const note of await vpage.locator(`[data-withheld="${expect.section}"]`).all()) {
              assert.equal((await note.textContent()).trim(), VALIDATION_REASON[locale]);
              assert.equal((await note.locator("xpath=following-sibling::div[1]").textContent()).trim(), marker);
              const unit = note.locator("xpath=ancestor::*[contains(concat(' ',normalize-space(@class),' '),' card ') or @id='news-pane' or @id='network-pane'][1]");
              assert.equal(await unit.locator(".badge.NOT_AVAILABLE").count(), 1, `${file} ${hash}: withheld unit shows NOT_AVAILABLE`);
              assert.equal(await unit.locator(LIVE_OR_FROZEN).count(), 0);
            }
          }
          if (expect.section === "macro") {
            for (const hash of ["home", "portfolio", "company/" + manifest.company]) {
              await vpage.view(hash, variant);
              assert.equal(await vpage.locator('[data-withheld="macro"]').count(), 1, `${file} ${hash}: macro withheld`);
            }
            await vpage.view("home", variant);
            const seen = await vpage.locator("[data-withheld]").evaluateAll((l) => [...new Set(l.map((e) => e.dataset.withheld))].sort());
            assert.deepEqual(seen, ["changes", "macro", "news", "qgv", "technical"], `${file}: research sections stay withheld`);
          } else {
            await vpage.view("companies", variant);
            const legend = await vpage.locator("main p.meta").first().innerText();
            assert.ok(legend.startsWith("NOT_AVAILABLE") && legend.includes(VALIDATION_REASON[locale]) && !legend.includes("FROZEN"), legend);
            await vpage.view("home", variant);
            assert.ok(!(await vpage.locator(ATTENTION).innerText()).includes(bundle.universe.as_of), "no withheld universe as_of");
          }
        }
        await vpage.context().close();
      }
    });
    await check("no page errors, external calls, unsafe requests or failed responses", async () => {
      assert.deepEqual(errors, []);
      assert.deepEqual(traffic, { external: 0, unsafe: 0, failed_responses: 0 });
    });
    const result = { kind: "WEB_RESEARCH_GUARD_BROWSER_VALIDATION_V2", mode: "public-build-in-memory-fixture", passed: true, checks, errors, traffic,
      runtime: { node: process.version, chromium: browser.version() },
      research_display: "NONE", frozen_grant: "NONE", live_grant: "NONE", real_data_validation: "NOT_RUN" };
    fs.writeFileSync(path.join(evidence, "browser-validation-public.json"), JSON.stringify(result, null, 2) + "\n");
    process.stdout.write(JSON.stringify({ mode: result.mode, passed: true, checks: checks.length }) + "\n");
  } finally {
    if (browser) await browser.close();
  }
}
main().catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
