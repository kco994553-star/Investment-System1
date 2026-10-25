const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
  });
  try {
    const page = await browser.newPage({
        viewport: { width: 390, height: 844 },
      }),
      errors = [],
      requests = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => {
      if (r.url().startsWith("http") && r.resourceType() !== "document")
        requests.push(r.url());
    });
    await page.goto(
      process.env.STUDIO_PREVIEW ||
        "http://127.0.0.1:8766/Investment-Studio.html",
    );
    await page
      .getByRole("heading", { name: "오늘의 투자 현황", exact: true })
      .waitFor();
    await page.context().setOffline(true);
    await page.getByRole("button", { name: "전체 메뉴 열기" }).click();
    await page.locator('#mobile-all-menu a[href="#portfolio"]').click();
    await page.locator('main[data-route="portfolio"]').waitFor();
    assert.equal(await page.locator("#mobile-all-menu").isVisible(), false);
    await page.getByRole("button", { name: "전체 메뉴 열기" }).click();
    await page.locator('#mobile-all-menu a[href="#technical"]').click();
    await page.locator('main[data-route="technical"]').waitFor();
    await page.locator("#global-search").fill("인텔");
    await page.locator("#global-search").press("Enter");
    await page.getByRole("dialog").waitFor();
    assert.ok(
      (await page.getByRole("dialog").textContent()).includes("예시 입력 없음"),
    );
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "전체 메뉴 열기" }).click();
    await page.locator('#mobile-all-menu a[href="#validation"]').click();
    assert.ok(
      (await page.locator("main").textContent()).includes(
        "Python 대조 JS 계산",
      ),
    );
    assert.ok(
      !(await page.locator("main").textContent()).includes(
        "기존 PIT 엔진 호출",
      ),
    );
    await page.locator('#mobile-nav a[href="#settings"]').click();
    assert.equal(await page.locator("details").getAttribute("open"), null);
    await page.locator("#profile-select").selectOption("value");
    await page
      .getByText("QGV v2 가치 중심 프로필을 적용했습니다.", { exact: true })
      .waitFor();
    await page.locator('#mobile-nav a[href="#simulation"]').click();
    await page.locator("#cash").fill("100");
    await page
      .getByRole("button", { name: "시뮬레이션 실행", exact: true })
      .click();
    await page.waitForFunction(() =>
      document
        .querySelector('[data-result="ending"]')
        ?.textContent.includes("1.18"),
    );
    assert.ok(
      (await page.locator("#simulation-result").textContent()).includes("0.0%"),
    );
    assert.equal(
      requests.length,
      0,
      "standalone preview must work without network",
    );
    assert.equal(errors.length, 0, errors.join("\n"));
    console.log(
      "PASS standalone HTML: offline, mobile full navigation, keyboard search, missing V, collapsed raw data, profile change, all-cash simulation",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
