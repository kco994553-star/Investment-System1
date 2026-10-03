// Existing Web + withheld producer/P01 contract fixture. No grant or engine execution.
"use strict";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const crypto = require("node:crypto");

async function main() {
  const args = process.argv.slice(2);
  function argument(name) {
    const index = args.indexOf(name);
    assert.ok(index >= 0 && args[index + 1], `required ${name}`);
    return path.resolve(args[index + 1]);
  }
  const root = argument("--dir"), evidence = argument("--evidence");
  assert.ok(evidence !== root && !evidence.startsWith(root + path.sep), "evidence stays outside served folder");
  const manifest = JSON.parse(fs.readFileSync(path.join(evidence, "fixture-manifest.json"), "utf8"));
  const originalData = fs.readFileSync(path.join(root, "data.json"));
  const originalEntities = fs.readFileSync(path.join(root, "entities.json"));
  const expected = JSON.parse(originalData);
  const digest = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
  const checks = [], errors = [];
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
    const target = path.resolve(root, "." + (pathname.endsWith("/") ? pathname + "index.html" : pathname));
    if (!target.startsWith(root + path.sep) || !fs.existsSync(target)) {
      response.writeHead(404); response.end("Not found"); return;
    }
    const mime = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript", ".css": "text/css" };
    response.writeHead(200, { "Content-Type": mime[path.extname(target)] || "application/octet-stream" });
    response.end(fs.readFileSync(target));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const url = `http://127.0.0.1:${server.address().port}`;
  const launch = { headless: true };
  if (process.env.WEB_TEST_CHROMIUM_PATH) launch.executablePath = process.env.WEB_TEST_CHROMIUM_PATH;
  let browser;
  async function check(name, fn) { await fn(); checks.push(name); }
  try {
    browser = await chromium.launch(launch);
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    async function route(hash) {
      await page.goto(url + "/#" + hash);
      await page.locator("main h1").waitFor();
    }
    await check("producer PASS, PARTIAL and BLOCKED remain NOT_AVAILABLE with grants NONE", async () => {
      await route("home");
      const actual = await page.evaluate(() => fetch("data.json").then(response => response.json()));
      assert.deepEqual(actual, expected);
      const envelope = actual.publication_envelope;
      assert.deepEqual(envelope.grants, { research_display: "NONE", frozen: "NONE", live: "NONE" });
      assert.equal(envelope.display_research_active, false);
      assert.deepEqual(new Set(envelope.decisions.map(row => row.data_completeness)), new Set(["PARTIAL", "BLOCKED"]));
      for (const row of envelope.decisions) {
        assert.equal(row.publication_mode, "NOT_AVAILABLE");
        assert.equal(row.official, false); assert.equal(row.live, false); assert.equal(row.track_c_validated, false);
      }
      assert.ok(envelope.decisions.some(row => row.not_authority.includes("PRODUCER_VALIDATION_IS_NOT_A_GRANT")));
    });
    await check("original provenance, as_of, freshness and methodology survive Web build and fetch", async () => {
      const actual = await page.evaluate(() => fetch("data.json").then(response => response.json()));
      for (const name of ["qgv", "technical", "macro", "leaderboard"]) {
        assert.equal(actual[name].state, "NOT_AVAILABLE"); assert.equal(actual[name].data, null);
        assert.equal(actual[name].producer.as_of, manifest.producer_as_of);
        assert.equal(actual[name].producer.freshness, "NOT_APPLICABLE");
        assert.equal(actual[name].producer.methodology.version, "TEST_VECTOR_V1");
        assert.deepEqual(actual[name].producer, expected[name].producer);
      }
      assert.equal(actual.universe.state, "FROZEN_SNAPSHOT");
      assert.ok(actual.universe.producer.source_inputs.every(input => /^[a-f0-9]{64}$/.test(input.sha256)));
    });
    await check("ko/en and mobile/desktop routes disclose absence without leaking withheld values", async () => {
      for (const locale of ["ko-KR", "en-US"]) {
        await route("settings");
        await page.locator("#display-locale").selectOption(locale);
        for (const width of [360, 390, 1280]) {
          await page.setViewportSize({ width, height: 844 });
          for (const hash of ["home", "companies", "portfolio", "leaderboard", "news", "research", "company/" + encodeURIComponent(expected.companies[0].company_id)]) {
            await route(hash);
            assert.equal(await page.locator("html").getAttribute("lang"), locale);
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${locale} ${width} ${hash}`);
            const visible = await page.locator("main").innerText();
            for (const token of manifest.withheld_tokens) assert.ok(!visible.includes(token), `withheld ${token}`);
            assert.equal(await page.locator(".banner").count(), 0);
          }
        }
        await route("leaderboard");
        assert.ok((await page.locator("main").innerText()).includes("NOT_AVAILABLE"));
        assert.equal(await page.locator('main a[href^="#company/"]').count(), 0, "no withheld ranking rows");
      }
    });
    await check("loading is visible while contract fetch is pending", async () => {
      const loading = await context.newPage();
      loading.on("pageerror", error => errors.push(error.message));
      let continueFetch;
      const blocked = new Promise(resolve => { continueFetch = resolve; });
      await loading.route("**/data.json", async route => { await blocked; await route.continue(); });
      await loading.goto(url + "/", { waitUntil: "domcontentloaded" });
      assert.equal(await loading.locator("main [role=status]").count(), 1);
      assert.equal(await loading.locator("nav a[aria-current=page]").count(), 0);
      continueFetch();
      await loading.locator("nav a[aria-current=page]").waitFor();
      await loading.close();
    });
    await check("HTTP and malformed JSON fail visibly and retry restores the original bundle", async () => {
      for (const kind of ["http", "json"]) {
        const failing = await context.newPage();
        failing.on("pageerror", error => errors.push(error.message));
        await failing.route("**/data.json", route => route.fulfill(kind === "http"
          ? { status: 503, body: "test outage" }
          : { status: 200, contentType: "application/json", body: "{broken" }));
        await failing.goto(url + "/");
        await failing.locator("#retry").waitFor();
        assert.equal(await failing.locator("main .metric").count(), 0, "no missing-to-zero rendering");
        await failing.unroute("**/data.json");
        await failing.locator("#retry").click();
        await failing.locator("nav a[aria-current=page]").waitFor();
        assert.deepEqual(await failing.evaluate(() => fetch("data.json").then(response => response.json())), expected);
        await failing.close();
      }
    });
    await check("bundle and search catalog bytes stay unchanged after all interactions", async () => {
      assert.equal(digest(fs.readFileSync(path.join(root, "data.json"))), digest(originalData));
      assert.equal(digest(fs.readFileSync(path.join(root, "entities.json"))), digest(originalEntities));
      assert.equal(digest(originalData), manifest.data_json_sha256);
      assert.equal(digest(originalEntities), manifest.entities_json_sha256);
      assert.deepEqual(errors, []);
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await route("home");
    await page.screenshot({ path: path.join(evidence, "withheld-home-en-390.png"), fullPage: true });
    const result = { kind: "PRODUCER_CONTRACT_WEB_BROWSER_VALIDATION_V1", passed: true, checks, errors,
      runtime: { node: process.version, chromium: browser.version() },
      fixture_data_sha256: manifest.data_json_sha256, Actions: "NOT_RUN", real_data_validation: "NOT_RUN",
      research_display: "NONE", frozen_grant: "NONE", live_grant: "NONE" };
    fs.writeFileSync(path.join(evidence, "browser-validation.json"), JSON.stringify(result, null, 2) + "\n");
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
