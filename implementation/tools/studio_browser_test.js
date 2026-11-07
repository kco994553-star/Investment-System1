/* Local synthetic studio: real browser -> HTTP -> canonical engines -> rendered results. */
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const base = process.env.STUDIO_URL || "http://127.0.0.1:8765";
const out = process.env.STUDIO_EVIDENCE || "/tmp/investment-studio-evidence";
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
  });
  const errors = [];
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1050 },
    });
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(base);
    await page
      .getByRole("heading", { name: "오늘의 투자 현황", exact: true })
      .waitFor();
    await page.locator('[data-chart="wealth"] svg').waitFor();
    assert.ok(
      await page
        .locator(".spark svg")
        .first()
        .evaluate(
          (e) =>
            e.getBoundingClientRect().height <= 30 &&
            e.getBoundingClientRect().width <= 74,
        ),
      "compact sparklines",
    );
    assert.ok(
      (await page.locator("#demo-banner").textContent()).includes(
        "예시 데이터",
      ),
    );
    await page.screenshot({ path: out + "/overview-1440.png", fullPage: true });
    for (const route of [
      "portfolio",
      "leaderboard",
      "simulation",
      "technical",
      "macro",
      "intelligence",
      "validation",
      "settings",
    ]) {
      if (route === "settings")
        await page.locator(".sidebar .settings-nav").click();
      else await page.locator(`#desktop-nav a[href="#${route}"]`).click();
      await page.waitForFunction(
        (r) => document.querySelector("main")?.dataset.route === r,
        route,
      );
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
        route,
      );
      assert.ok(
        (await page.locator("main").textContent()).trim().length > 100,
        route,
      );
    }
    await page.locator('#desktop-nav a[href="#leaderboard"]').click();
    await page.locator("#company-filter").fill("없는기업");
    await page.getByText("검색 결과가 없습니다.", { exact: true }).waitFor();
    await page.locator("#company-filter").fill("NVDA");
    await page.locator('[data-company="nvda"]').first().click();
    await page.getByRole("dialog").waitFor();
    assert.ok(
      (await page.getByRole("dialog").textContent()).includes("엔비디아"),
    );
    await page.getByRole("button", { name: "관심 기업에 추가" }).click();
    await page.keyboard.press("Escape");
    assert.equal(await page.getByRole("dialog").count(), 0);
    await page.locator('#desktop-nav a[href="#home"]').click();
    await page.route("**/api/simulate", async (route) => {
      const response = await route.fetch();
      await new Promise((resolve) => setTimeout(resolve, 600));
      await route.fulfill({ response });
    });
    await page.locator('[data-period="12"]').click();
    await page.locator('#desktop-nav a[href="#simulation"]').click();
    await page.waitForFunction(() =>
      document
        .querySelector("#simulation-result h2")
        ?.textContent.includes("12개월"),
    );
    assert.equal(
      await page.locator("#months").inputValue(),
      "12",
      "late home result keeps simulation form in sync",
    );
    await page.locator('#desktop-nav a[href="#home"]').click();
    await page.locator('[data-period="60"]').click();
    await page.locator('#desktop-nav a[href="#simulation"]').click();
    await page.locator("#capital").fill("300000000");
    await page.waitForFunction(() =>
      document
        .querySelector("#simulation-result h2")
        ?.textContent.includes("60개월"),
    );
    assert.equal(await page.locator("#months").inputValue(), "60");
    assert.equal(
      await page.locator("#capital").inputValue(),
      "300000000",
      "newer deliberate draft survives a late response",
    );
    assert.ok(
      (await page.locator("#simulation-error").textContent()).includes(
        "수정한 입력",
      ),
    );
    await page.unroute("**/api/simulate");
    const old = await page.locator('[data-result="ending"]').textContent();
    await page.locator("#capital").fill("200000000");
    await page.locator("#monthly").fill("1000000");
    await page.locator("#scenario").selectOption("recession");
    await page
      .getByRole("button", { name: "시뮬레이션 실행", exact: true })
      .click();
    await page.waitForFunction(
      (v) =>
        document.querySelector('[data-result="ending"]')?.textContent !== v,
      old,
    );
    assert.ok(
      (await page.locator("#simulation-result").textContent()).includes(
        "경기 침체",
      ),
    );
    await page.screenshot({
      path: out + "/simulation-1440.png",
      fullPage: true,
    });
    const download = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "CSV 내보내기", exact: true })
      .click();
    assert.equal(
      (await download).suggestedFilename(),
      "investment-studio-DEMO.csv",
    );
    await page.locator("#capital").fill("-1");
    await page
      .getByRole("button", { name: "시뮬레이션 실행", exact: true })
      .click();
    assert.equal(
      await page.locator("#capital").evaluate((e) => e.validity.valid),
      false,
    );
    // Real error state, followed by retry.
    await page.route("**/api/studio*", (r) =>
      r.fulfill({ status: 503, body: "{}", contentType: "application/json" }),
    );
    await page.reload();
    await page.getByRole("button", { name: "다시 불러오기" }).waitFor();
    await page.unroute("**/api/studio*");
    await page.getByRole("button", { name: "다시 불러오기" }).click();
    await page.locator('main[data-route="simulation"]').waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    for (const route of [
      "home",
      "portfolio",
      "leaderboard",
      "simulation",
      "technical",
      "macro",
      "intelligence",
      "validation",
      "settings",
    ]) {
      await page.evaluate((r) => (location.hash = r), route);
      await page.waitForFunction(
        (r) => document.querySelector("main")?.dataset.route === r,
        route,
      );
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
        false,
        "mobile " + route,
      );
      if (route === "home" || route === "simulation")
        await page.screenshot({
          path: out + "/" + route + "-390.png",
          fullPage: true,
        });
    }
    assert.equal(errors.length, 0, errors.join("\n"));
    await page.close();
    console.log(
      "PASS studio: 9 routes × desktop/mobile, search, company dialog, watchlist, simulation/API, invalid input, CSV, failure/retry, no console errors",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
