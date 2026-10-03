// Render-time research guard (G3) E2E on the existing static Web. Test vectors only; no grant.
//   fixture mode: node web_research_guard_browser_test.js --dir <build_web_research_guard_fixture --out> --evidence <dir>
//                 [--baseline-app <pre-guard app.js>]   (adds a per-card "unchanged" comparison and records the G3 leak)
//   legacy mode:  node web_research_guard_browser_test.js --mode legacy --dir <existing Web build> --evidence <dir>
//                 --baseline-app <pre-guard app.js>     (bundles without research markers render byte-identically)
"use strict";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");

const LIVE_OR_FROZEN = ".badge.LIVE, .badge.FROZEN_SNAPSHOT";
const REASON = {
  "ko-KR": "게시 승인이 없는 연구·잠정 결과라 표시하지 않습니다.",
  "en-US": "Withheld: research or provisional output without publication approval.",
};
const NOT_CONNECTED = { "ko-KR": "운영 Snapshot이 연결되지 않았습니다.", "en-US": "Operating snapshots are not connected." };

async function main() {
  const args = process.argv.slice(2);
  const option = (name, required = true) => {
    const i = args.indexOf(name);
    if (i < 0 || !args[i + 1]) { assert.ok(!required, `required ${name}`); return null; }
    return args[i + 1];
  };
  const mode = option("--mode", false) || "fixture";
  assert.ok(["fixture", "legacy"].includes(mode), "mode is fixture or legacy");
  const root = path.resolve(option("--dir")), evidence = path.resolve(option("--evidence"));
  const baselineApp = option("--baseline-app", false) && path.resolve(option("--baseline-app"));
  assert.ok(evidence !== root && !evidence.startsWith(root + path.sep), "evidence stays outside the served folder");
  if (mode === "legacy") assert.ok(baselineApp, "legacy mode compares against --baseline-app");
  fs.mkdirSync(evidence, { recursive: true });
  const manifest = mode === "fixture" ? JSON.parse(fs.readFileSync(path.join(evidence, "fixture-manifest.json"), "utf8")) : null;
  const original = fs.readFileSync(path.join(root, "data.json"));
  const bundle = JSON.parse(original);

  // /x -> served folder; /baseline/x -> same folder, except app.js comes from --baseline-app.
  const server = http.createServer((request, response) => {
    let pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
    const baseline = pathname.startsWith("/baseline/");
    if (baseline) pathname = pathname.slice("/baseline".length);
    let target = path.resolve(root, "." + (pathname.endsWith("/") ? pathname + "index.html" : pathname));
    if (baseline && baselineApp && target === path.join(root, "app.js")) target = baselineApp;
    else if (!target.startsWith(root + path.sep) || !fs.existsSync(target)) { response.writeHead(404); response.end("Not found"); return; }
    const mime = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript", ".css": "text/css" };
    response.writeHead(200, { "Content-Type": mime[path.extname(target)] || "application/octet-stream", "Cache-Control": "no-store" });
    response.end(fs.readFileSync(target));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const url = `http://127.0.0.1:${server.address().port}`;
  const launch = { headless: true };
  if (process.env.WEB_TEST_CHROMIUM_PATH) launch.executablePath = process.env.WEB_TEST_CHROMIUM_PATH;
  const checks = [], errors = [], observed = {};
  let browser;
  async function check(name, fn) { await fn(); checks.push(name); console.log("PASS " + name); }

  async function openPage(prefix) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push(`${prefix || "/"} ${e.message}`));
    page.go = async (hash) => {
      await page.goto(url + (prefix || "/") + "#" + hash);
      await page.reload();
      await page.waitForFunction(() => typeof window.investmentSearch === "function" && !!document.querySelector("main h1"));
    };
    page.setLocale = async (locale) => {
      await page.go("settings");
      await page.locator("#display-locale").selectOption(locale);
      assert.equal(await page.locator("html").getAttribute("lang"), locale);
    };
    return page;
  }
  // Comparable rendering units: cards and news/network panes. Withheld units are reported, not compared.
  const units = (page) => page.evaluate(() => {
    const main = document.querySelector("main").cloneNode(true);
    const list = [...main.querySelectorAll("section.card, #news-pane, #network-pane")]
      .filter((e) => !e.parentElement.closest("section.card, #news-pane, #network-pane"));
    const out = list.map((e) => ({ withheld: !!e.querySelector("[data-withheld]"), html: e.outerHTML }));
    list.forEach((e) => e.remove());
    return { units: out, rest: main.innerHTML };
  });
  // Search result rows; a company row reads the QGV section, so withheld fixtures may exclude them.
  const searchRows = async (page, query, companies = true) => {
    await page.locator("#global-search").fill(query);
    return page.locator("#global-results li").evaluateAll((rows, all) => rows
      .filter((e) => all || !(e.dataset.entityId || "").startsWith("COMPANY:")).map((e) => e.outerHTML).join(""), companies);
  };

  try {
    browser = await chromium.launch(launch);
    const routes = ["home", "companies", "portfolio", "leaderboard", "news", "research", "settings",
      "company/" + encodeURIComponent(manifest ? manifest.company : bundle.companies[0].company_id),
      "entity/" + encodeURIComponent("MACRO:CPIAUCSL")];

    if (mode === "fixture") {
      const page = await openPage("/");
      await check("served data.json still carries the hand-built research sections unchanged", async () => {
        await page.go("home");
        const served = await page.evaluate(() => fetch("data.json").then((r) => r.json()));
        assert.deepEqual(served, bundle);
        assert.equal(served.qgv.state, "LIVE");
        assert.equal(served.qgv.producer.methodology.status, "PROVISIONAL_RESEARCH");
        assert.equal(served.qgv.data[manifest.company].Q_score, 11.11);
        assert.equal(served.technical.state, "FROZEN_SNAPSHOT");
      });
      for (const locale of ["ko-KR", "en-US"]) {
        await page.setLocale(locale);
        await check(`${locale}: withheld sections show NOT_AVAILABLE + reason and no value on every route`, async () => {
          for (const hash of routes) {
            await page.go(hash);
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
          const expect = { home: ["changes", "news", "qgv", "technical"], portfolio: ["qgv", "technical"],
            leaderboard: ["leaderboard"], news: ["news"], ["company/" + manifest.company]: ["news", "qgv", "technical"] };
          for (const [hash, names] of Object.entries(expect)) {
            await page.go(hash);
            const seen = await page.locator("[data-withheld]").evaluateAll((l) => [...new Set(l.map((e) => e.dataset.withheld))].sort());
            assert.deepEqual(seen, names, hash);
            for (const name of names) {
              assert.ok((await page.locator("main").textContent()).includes(manifest.withheld[name]), `${hash} marker ${name}`);
            }
          }
          await page.go("leaderboard");
          assert.equal(await page.locator('main a[href^="#company/"]').count(), 0, "no withheld ranking rows");
          await page.go("news");
          assert.equal(await page.locator("#news-list [data-source-original], #news-list h3").count(), 0, "no withheld news rows");
        });
        await check(`${locale}: valid LIVE, legacy FROZEN universe, DEMO and NOT_AVAILABLE still render`, async () => {
          await page.go("home");
          const macro = page.locator("section.card", { has: page.locator(".badge.LIVE") });
          assert.equal(await macro.count(), 1);
          assert.equal((await macro.locator(".badge.LIVE").innerText()).trim(), "LIVE");
          assert.ok((await macro.innerText()).includes("TEST_REGIME_VALID"));
          assert.equal(await page.locator(".banner").count(), 1, "DEMO banner");
          const hero = page.locator("section.hero");
          assert.equal((await hero.locator(".badge.DEMO").innerText()).trim(), "DEMO");
          assert.ok((await hero.innerText()).includes("TEST DEMO / NOT ACTUAL"));
          const main = await page.locator("main").textContent();
          assert.ok(main.includes(NOT_CONNECTED[locale]), "NOT_AVAILABLE relationships reason");
          assert.ok(main.includes(bundle.universe.as_of), "legacy FROZEN universe as_of in Attention");
          await page.go("portfolio");
          assert.ok((await page.locator("main").textContent()).includes("44.44%"));
          await page.go("entity/" + encodeURIComponent("MACRO:CPIAUCSL"));
          assert.ok((await page.locator("main").textContent()).includes("33.33"));
          await page.go("company/" + manifest.company);
          const detail = await page.locator("main").textContent();
          assert.ok(detail.includes("TEST_EXPOSURE_VALID") && detail.includes("44.44%"));
          await page.go("companies");
          assert.ok((await page.locator("main p.meta").first().innerText()).includes("FROZEN_SNAPSHOT / DEMO"));
          const row = await searchRows(page, "NVDA");
          assert.ok(row.includes("FROZEN_SNAPSHOT"), "legacy universe state in search row");
        });
        await page.go("home");
        await page.screenshot({ path: path.join(evidence, `guard-home-${locale}-390.png`), fullPage: true });
      }
      await check("research-marked FROZEN universe is withheld in the companies legend and search rows", async () => {
        const variant = JSON.parse(original);
        variant.universe.producer = { producer_id: "test.web_research_guard", producer_version: "TEST_VECTOR_V1",
          methodology: { id: "TEST_VECTOR", version: "TEST_VECTOR_V1", status: "RESEARCH" } };
        const vpage = await openPage("/");
        await vpage.route("**/data.json", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(variant) }));
        await vpage.setLocale("ko-KR");
        await vpage.go("companies");
        const legend = await vpage.locator("main p.meta").first().innerText();
        assert.ok(legend.startsWith("NOT_AVAILABLE") && legend.includes(REASON["ko-KR"]) && !legend.includes("FROZEN"), legend);
        const row = await searchRows(vpage, "NVDA");
        assert.ok(!row.includes("FROZEN_SNAPSHOT") && row.includes("NOT_AVAILABLE"), row);
        await vpage.go("home");
        assert.ok(!(await vpage.locator("main").textContent()).includes(bundle.universe.as_of), "no withheld universe as_of");
        await vpage.context().close();
      });
      await page.context().close();
    }

    if (baselineApp) {
      const guarded = await openPage("/"), baseline = await openPage("/baseline/");
      const leaks = {};
      await check(`${mode}: sections without research markers render exactly as with the pre-guard app.js`, async () => {
        for (const locale of ["ko-KR", "en-US"]) {
          await guarded.setLocale(locale); await baseline.setLocale(locale);
          for (const hash of routes) {
            await guarded.go(hash); await baseline.go(hash);
            const g = await units(guarded), b = await units(baseline);
            assert.equal(g.rest, b.rest, `${locale} ${hash}: page outside cards`);
            assert.equal(g.units.length, b.units.length, `${locale} ${hash}: unit count`);
            g.units.forEach((u, i) => { if (!u.withheld) assert.equal(u.html, b.units[i].html, `${locale} ${hash}: unit ${i}`); });
            if (mode === "legacy") assert.equal(g.units.some((u) => u.withheld), false, `${hash}: legacy bundle has nothing to withhold`);
            const html = await baseline.evaluate(() => document.documentElement.outerHTML);
            const leaked = (manifest ? manifest.withheld_probes : []).filter((p) => html.includes(p));
            if (leaked.length) leaks[`${locale} ${hash}`] = leaked;
          }
          for (const query of ["NVDA", "CPI", "반도체"]) {
            const all = mode === "legacy";
            assert.equal(await searchRows(guarded, query, all), await searchRows(baseline, query, all), `${locale} search ${query}`);
          }
        }
      });
      if (mode === "fixture") {
        await check("pre-guard app.js reproduces the G3 leak on the same bundle (defect evidence)", async () => {
          assert.ok(Object.keys(leaks).length > 0, "baseline shows research values");
          await baseline.setLocale("ko-KR");
          await baseline.go("home");
          assert.ok(await baseline.locator("section.card .badge.LIVE").count() > 1, "baseline shows research sections as LIVE");
          await baseline.screenshot({ path: path.join(evidence, "pre-guard-home-ko-KR-390.png"), fullPage: true });
        });
        observed.pre_guard_leaks = leaks;
      }
      await guarded.context().close(); await baseline.context().close();
    }
    await check("data.json bytes unchanged and no page errors", async () => {
      assert.ok(fs.readFileSync(path.join(root, "data.json")).equals(original));
      assert.deepEqual(errors, []);
    });
    const result = { kind: "WEB_RESEARCH_GUARD_BROWSER_VALIDATION_V1", mode, passed: true, checks, errors,
      baseline_compared: !!baselineApp, runtime: { node: process.version, chromium: browser.version() }, observed,
      research_display: "NONE", frozen_grant: "NONE", live_grant: "NONE", real_data_validation: "NOT_RUN" };
    fs.writeFileSync(path.join(evidence, `browser-validation-${mode}.json`), JSON.stringify(result, null, 2) + "\n");
    process.stdout.write(JSON.stringify({ mode, passed: true, checks: checks.length, baseline_compared: !!baselineApp }) + "\n");
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}
main().catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
