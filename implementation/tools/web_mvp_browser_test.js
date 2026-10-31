const {displayOnlyOff}=require('./display_only_off.js');
// Integration tests for the mobile UI on the public Pages build (PAGES_COCKPIT_URL). No personal account data.
//
// Current contract (GSQ-010 public price boundary + IA update): the public build ships no producer rows (no QGV scores,
// leaderboard, news, relationship page), company identities are the price-free device directory, and group management
// lives on the watchlist screen. The old demo-fixture checks (a 90.79 QGV score, the Track D network page) can no longer
// be built or served, so the equivalent checks assert the fail-closed behaviour instead.
const { chromium } = require("playwright");
const { routeEmptyPublicScreens } = require("./empty_public_screens.js");
const fs = require("fs");
const os = require("node:os");
const path = require("node:path");
const assert = require("node:assert/strict");
const base = new URL(process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:9003/Investment-System1/");
base.hash = "";
if (!base.pathname.endsWith("/")) base.pathname += "/";
(async () => {
  const out = path.resolve(process.env.WEB_MVP_EVIDENCE_DIR || process.env.PAGES_COCKPIT_EVIDENCE_DIR || path.join(os.tmpdir(), "web-mvp-evidence"));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.WEB_TEST_CHROMIUM_PATH ? { executablePath: process.env.WEB_TEST_CHROMIUM_PATH } : {}) });
  const traffic = { external: 0, unsafe: 0, failed_responses: 0 };
  const guard = async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (request.method() !== "GET" || request.postData()) { traffic.unsafe++; await route.abort(); return; }
    if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) { traffic.external++; await route.abort(); return; }
    await route.continue();
  };
  // The optional SEC sidecar is absent from a build without collection; any other failure stays an error.
  const responses = (page) => page.on("response", (response) => {
    if (response.status() >= 400 && !(response.status() === 404 && ["sec-public-inputs.json", "forward-validation-ledger.json", "sec-qgv2.json", "qgv-official.json"].some(name => response.url() === new URL(name, base).href))) traffic.failed_responses++;
  });
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    permissions: ["clipboard-read", "clipboard-write"],
  });await displayOnlyOff(ctx);
  await ctx.route("**/*", guard);
  await routeEmptyPublicScreens(ctx);
  const page = await ctx.newPage();
  responses(page);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const checks = [];
  async function check(name, fn) {
    await fn();
    checks.push(name);
    console.log("PASS " + name);
  }
  async function route(hash, target = page) {
    await target.goto(new URL("#" + hash, base).href);
    await target.waitForFunction((hash) => location.hash === "#" + hash && !!document.querySelector("main h1"), hash);
  }
  async function group() {
    // Group management is the details panel of the watchlist screen.
    await page.locator("summary", { hasText: /Groups/ }).click();
  }
  try {
    await check("default fail-closed missing data", async () => {
      await page.goto(base.href);
      // Home is the search start (2026-10-17); the fail-closed dashboard cards moved to #brief unchanged.
      await page.getByRole("heading", { name: "어떤 기업을 살펴볼까요?" }).waitFor();
      await page.goto(new URL("#brief", base).href);
      await page.getByRole("heading", { name: "오늘의 투자 화면" }).waitFor();
      assert.equal(await page.locator(".banner").count(), 0);
      assert.ok(
        (await page.locator("main").innerText()).includes("NOT_AVAILABLE"),
      );
    });
    await check("routes 360/390/1280 without overflow", async () => {
      for (const width of [360, 390, 1280]) {
        await page.setViewportSize({ width, height: 844 });
        for (const hash of [
          "home",
          "brief",
          "companies",
          "portfolio",
          "leaderboard",
          "news",
          "research",
          "qgv",
          "watchlist",
          "technical",
          "macro",
          "validation",
          "settings",
        ]) {
          await route(hash);
          assert.equal(
            await page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
            true,
            hash + " " + width,
          );
        }
      }
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await check("companies to company and fail-closed QGV", async () => {
      await route("companies");
      await page.locator('a[href="#company/nvda"]').click();
      await page.getByRole("heading", { name: "NVIDIA · NVDA", exact: true }).waitFor(); // KR-NAMES title "<name> · <ticker>"
      const text = await page.locator("main").innerText();
      // No producer score is invented: the original QGV view is unavailable, never a number.
      assert.ok(text.includes("NOT_AVAILABLE"));
      assert.ok(!text.includes("90.79"));
      // The raw Q·G / type cards moved to Settings > 원자료 보기(개발자용) for the last viewed company (owner decision 2026-10-14).
      assert.equal(await page.locator('main [data-screen-company]').count(), 0);
      await route("settings");
      await page.locator('[data-raw-data] > summary').click();
      assert.equal(await page.locator('main [data-raw-data] [data-screen-company="nvda"] dd').evaluateAll((nodes) => nodes.length > 0 && nodes.every((node) => node.textContent.trim() === "NOT_AVAILABLE")), true);
      await route("company/nvda");
    });
    await check("interest persistence and group membership", async () => {
      await page.locator('[data-star="nvda"]').click();
      await page.reload();
      await page.locator('[data-star="nvda"][aria-pressed=true]').waitFor();
      await route("watchlist");
      await group();
      await page.locator("#group-name").fill("반도체");
      await page.getByRole("button", { name: "그룹 만들기" }).click();
      await group();
      await page.locator('[data-member="nvda"]').check();
      await page.reload();
      await group();
      assert.equal(
        await page.locator('[data-member="nvda"]').isChecked(),
        true,
      );
      await route("companies");
      await page.locator("#search").fill("nvda");
      assert.equal(await page.locator("#company-list li").count(), 1);
    });
    await check(
      "news-network switch stays fail-closed without a relationship page",
      async () => {
        await route("news");
        assert.equal(await page.locator("#news-pane").isVisible(), true);
        assert.ok((await page.locator("#news-pane").innerText()).includes("NOT_AVAILABLE"));
        assert.equal(await page.locator("#news-list>li.empty").count(), 1);
        await page.locator("#show-network").click();
        assert.equal(await page.locator("#network-pane").isVisible(), true);
        assert.equal(await page.locator("#news-pane").isVisible(), false);
        assert.ok((await page.locator("#network-pane").innerText()).includes("NOT_AVAILABLE"));
        // Track D's relationship page is withheld (GSQ-010): no frame, no zoom/pan/focus controls.
        assert.equal(await page.locator("#network-frame").count(), 0);
        await page.locator("#show-news").click();
        assert.equal(await page.locator("#news-pane").isVisible(), true);
      },
    );
    await check("research canonical select fill preview copy", async () => {
      await route("research");
      const f = page.frameLocator("#research-frame");
      await f
        .getByText("Filters(필터) · Starter · Bundle", { exact: true })
        .click();
      await f.locator("#f-starter").check();
      await f.locator("#list li").first().click();
      const fields = await f.locator("[data-v]").all();
      for (const field of fields) {
        const name = await field.getAttribute("data-v");
        const tag = await field.evaluate((e) => e.tagName);
        await (tag === "SELECT"
          ? field.selectOption("STANDALONE")
          : field.fill(
              name === "as_of"
                ? "2024-12-31"
                : name === "prior_cutoff"
                  ? "2024-09-30"
                  : name === "candidate_count"
                    ? "5"
                    : "테스트 문맥",
            ));
      }
      await f.locator("#copy:not([disabled])").waitFor();
      const preview = await f.locator("#pv").innerText();
      await f.locator("#copy").click();
      await f.locator("#copied").getByText("Copied").waitFor();
      assert.equal(
        await page.evaluate(() => navigator.clipboard.readText()),
        preview,
      );
      await f.locator("#f-starter").uncheck();
      await f.locator("#f-bundle").selectOption({ index: 1 });
      assert.ok((await f.locator("#list li").count()) > 0);
    });
    // Directive §10: per-browser favorites and personal copies. The official catalog text, preview and copy never change.
    await check("research favorites and personal copies stay on this browser", async () => {
      await route("research");
      await page.reload();
      const f = page.frameLocator("#research-frame");
      const frozen = await f.locator("#plv1-data").textContent();
      const note = f.locator("[data-prompt-storage-note]");
      assert.ok((await note.locator("summary").innerText()).includes("이 브라우저 기준"));
      await note.locator("summary").click();
      assert.ok((await note.innerText()).includes("다른 브라우저"));
      assert.ok((await f.locator("[data-prompt-missing-domains]").innerText()).includes("뉴스·포트폴리오·백테스트"));
      assert.equal(await f.locator("[data-prompt-domain]").count(), 6, "five existing catalog domains + all");
      await f.locator('[data-prompt-domain="TECHNICAL"]').click();
      assert.equal(await f.locator("#f-domain").inputValue(), "TECHNICAL");
      assert.equal(await f.locator('[data-prompt-domain="TECHNICAL"]').getAttribute("aria-pressed"), "true");
      const id = "plv1.tech.001";
      await f.locator('#list [data-id="' + id + '"]').click();
      await f.locator("[data-prompt-personal]").waitFor();
      const official = await f.locator("#pv").innerText();
      assert.ok((await f.locator("[data-prompt-official-label]").innerText()).includes("공식 원문"));
      await f.locator("#pl-fav").click();
      assert.equal(await f.locator("#pl-fav").getAttribute("aria-pressed"), "true");
      await f.locator("#pl-view").selectOption("fav");
      assert.equal(await f.locator("#list li:not([hidden])").count(), 1);
      assert.ok((await f.locator('#list [data-id="' + id + '"] [data-prompt-fav-mark]').count()) === 1);
      await f.locator("[data-prompt-personal-make]").click();
      const body = f.locator("[data-prompt-personal-body]");
      const officialBody = JSON.parse(frozen).prompts.find((p) => p.prompt_id === id).body;
      assert.equal(await body.inputValue(), officialBody, "a personal copy starts from the official text");
      await body.fill(officialBody + "\n\n[개인 메모] 내 관점");
      assert.ok((await f.locator("[data-prompt-personal-meta]").innerText()).includes("공식 원문과 다름"));
      await f.locator("[data-prompt-personal-save]").click();
      await f.locator("#pl-status").getByText("저장했습니다").waitFor();
      for (const field of await f.locator("[data-v]").all()) {
        const name = await field.getAttribute("data-v"), tag = await field.evaluate((e) => e.tagName);
        await (tag === "SELECT" ? field.selectOption("STANDALONE") : field.fill(name === "as_of" ? "2024-12-31" : "테스트 문맥"));
      }
      await f.locator("[data-prompt-personal-copy]").click();
      await f.locator("#pl-status").getByText("개인 수정본(공식 원문 아님)").waitFor();
      const personalCopy = await page.evaluate(() => navigator.clipboard.readText());
      assert.ok(personalCopy.includes("[개인 메모] 내 관점") && personalCopy.includes("테스트 문맥") && !personalCopy.includes("{{"));
      await f.locator("#copy").click();
      await f.locator("#copied").getByText("Copied").waitFor();
      const officialCopy = await page.evaluate(() => navigator.clipboard.readText());
      assert.equal(officialCopy, await f.locator("#pv").innerText(), "official copy is the official preview");
      assert.ok(!officialCopy.includes("[개인 메모]"));
      assert.equal(await f.locator("#plv1-data").textContent(), frozen, "embedded Frozen catalog unchanged");
      assert.ok(official.length > 0);
      // Persisted for this browser profile only.
      await page.reload();
      await f.locator('#list [data-id="' + id + '"]').click();
      await f.locator("[data-prompt-personal-body]").waitFor();
      assert.equal(await f.locator("#pl-fav").getAttribute("aria-pressed"), "true");
      assert.ok((await f.locator("[data-prompt-personal-body]").inputValue()).includes("[개인 메모] 내 관점"));
      assert.ok((await f.locator('#list [data-id="' + id + '"] [data-prompt-mine-mark]').innerText()).includes("개인 수정본"));
      const other = await browser.newContext({ viewport: { width: 1280, height: 900 } });await displayOnlyOff(other);
      await other.route("**/*", guard);await routeEmptyPublicScreens(other);
      const otherPage = await other.newPage();
      await route("research", otherPage);
      const g = otherPage.frameLocator("#research-frame");
      await g.locator('#list [data-id="' + id + '"]').click();
      await g.locator("[data-prompt-personal-make]").waitFor();
      assert.equal(await g.locator("#pl-fav").getAttribute("aria-pressed"), "false", "another browser profile shares nothing");
      assert.ok(await otherPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await other.close();
      // Blocked storage: the click reports the failure and nothing changes.
      await f.locator("html").evaluate(() => { window.__plSetItem = Storage.prototype.setItem; Storage.prototype.setItem = () => { throw new Error("blocked"); }; });
      await f.locator("#pl-fav").click();
      await f.locator("#pl-status").getByText("저장하지 못했습니다").waitFor();
      assert.equal(await f.locator("#pl-fav").getAttribute("aria-pressed"), "true");
      await f.locator("html").evaluate(() => { Storage.prototype.setItem = window.__plSetItem; });
      page.once("dialog", (d) => d.accept());
      await f.locator("[data-prompt-personal-delete]").click();
      await f.locator("[data-prompt-personal-make]").waitFor();
      assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem("investment.web.v1.prompt-personal-copies")))["plv1.tech.001"], undefined);
      await f.locator("#pl-fav").click();
      assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("investment.web.v1.prompt-favorites"))), []);
      await f.locator("#pl-view").selectOption("all");
    });
    await check("group rename delete and preferences backup", async () => {
      await route("watchlist");
      await group();
      await page.locator("[data-rename-input]").fill("AI");
      await page.locator("[data-rename]").click();
      await group();
      assert.ok((await page.locator("#groups").innerText()).includes("AI"));
      // The backup is the unified, price-free device backup; it is only ever a local Blob download.
      const downloadPromise = page.waitForEvent("download");
      await page.locator("#export").click();
      const download = await downloadPromise;
      assert.equal(download.suggestedFilename(), "investment-personal.json");
      const backup = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
      assert.equal(backup.schema, "investment-device-backup/4");
      assert.deepEqual(backup.investor_stars, []);
      assert.deepEqual(backup.preferences.interests, ["nvda"]);
      assert.deepEqual(backup.preferences.groups.map((g) => g.name), ["AI"]);
      assert.ok(!JSON.stringify(backup).includes("market_data"));
      await page.locator("[data-delete]").click();
      await page.reload();
      await group();
      assert.equal(await page.locator("[data-delete]").count(), 0);
      assert.equal(
        await page.locator('[data-star="nvda"]').getAttribute("aria-pressed"),
        "true",
      );
    });
    await check("back navigation and deep link", async () => {
      await route("companies");
      await page.locator("#search").fill("nvda");
      await page.locator("#company-list a").click();
      await page.goBack();
      await page.locator("#search").waitFor();
      await route("company/nvda");
      await page.getByRole("heading", { name: "NVIDIA · NVDA", exact: true }).waitFor(); // KR-NAMES title "<name> · <ticker>"
    });
    await check("no page errors, external calls or failed responses", async () => {
      assert.deepEqual(errors, []);
      assert.deepEqual(traffic, { external: 0, unsafe: 0, failed_responses: 0 });
    });
    // Screenshots only from a fresh context: no interests, groups or other device records are present.
    const fresh = await browser.newContext({ viewport: { width: 390, height: 844 } });await displayOnlyOff(fresh);
    await fresh.route("**/*", guard);
    await routeEmptyPublicScreens(fresh);
    const shot = await fresh.newPage();
    responses(shot);
    for (const name of ["home", "portfolio", "company/nvda", "news", "research"]) {
      await route(name, shot);
      await shot.screenshot({
        path: out + "/" + name.replace("/", "-") + "-mobile.png",
        fullPage: true,
      });
    }
    await fresh.close();
    assert.deepEqual(traffic, { external: 0, unsafe: 0, failed_responses: 0 });
    fs.writeFileSync(
      out + "/browser.json",
      JSON.stringify({ passed: true, checks, errors, traffic }, null, 2),
    );
  } catch (e) {
    fs.writeFileSync(
      out + "/browser.json",
      JSON.stringify(
        { passed: false, checks, errors, traffic, error: String(e), stack: e.stack },
        null,
        2,
      ),
    );
    console.error("FAIL " + String(e).split("\n")[0]);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
