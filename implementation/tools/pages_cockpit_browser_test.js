"use strict";
// Screenshots always use fresh empty ACTUAL storage. Holdings are never captured.
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const base = new URL(process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:8990/Investment-System1/");
base.hash = "";
if (!base.pathname.endsWith("/")) base.pathname += "/";
const out = path.resolve(process.env.PAGES_COCKPIT_EVIDENCE_DIR || "/tmp/pages-browser-evidence");
const checks = [], captures = [];
const notices = {
  "ko-KR": "개인 참고용입니다. 투자 권유나 자문이 아닙니다.",
  "en-US": "For personal reference only. Not investment advice."
};
const keyGuidance = {
  "ko-KR": { link: "Alpha Vantage 공식 무료 API 키 발급 (새 탭)", text: "본인의 무료 키는 이 기기에만 저장되고 백업에서 제외됩니다. 검증 전까지 API는 꺼져 있습니다. 키 없이도 가격·환율을 수동 입력할 수 있습니다." },
  "en-US": { link: "Alpha Vantage official free API key issuance (new tab)", text: "Your own free key stays on this device and is excluded from backups. API remains OFF pending validation. You can manually enter prices and FX without a key." }
};
let requestProblems = 0, responseProblems = 0, pageErrors = 0, networkDataEvents = 0;
function verify(value, label) { if (!value) { const error = new Error(label); error.safeReason = label; throw error; } }
async function personalNotices(page, locale) {
  verify(await page.locator("[data-personal-reference]").count() === 2, "both personal notices are required");
  for (const position of ["top", "bottom"]) {
    const notice = page.locator('[data-personal-reference="' + position + '"]');
    verify(await notice.textContent() === notices[locale], "personal notice locale or exact text failed");
    await notice.scrollIntoViewIfNeeded();
    verify(await notice.isVisible(), "personal notice is hidden");
    verify(await notice.evaluate(node => {
      const box = node.getBoundingClientRect(), nav = document.querySelector("nav").getBoundingClientRect();
      const style = getComputedStyle(node);
      const left = Math.max(0, box.left), right = Math.min(innerWidth, box.right);
      const x = (left + right) / 2, y = (box.top + box.bottom) / 2;
      const range = document.createRange(); range.selectNodeContents(node);
      const textVisible = [...range.getClientRects()].every(rect =>
        rect.top >= 0 && rect.bottom <= innerHeight && rect.left >= 0 && rect.right <= innerWidth &&
        (rect.right <= nav.left || rect.left >= nav.right || rect.bottom <= nav.top || rect.top >= nav.bottom));
      return box.top >= 0 && box.bottom <= innerHeight && box.width > 0 && textVisible &&
        parseFloat(style.fontSize) >= 12 && style.visibility === "visible" &&
        node.contains(document.elementFromPoint(x, y));
    }), "personal notice is obscured or unreadable");
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}
async function settingsGuidance(page, locale) {
  const root = page.locator("[data-device-api-settings]");
  await root.locator("[data-api-status]").waitFor();
  const link = root.locator("[data-api-key-issuance]");
  verify(await link.textContent() === keyGuidance[locale].link, "official key link locale failed");
  verify(await root.locator("[data-api-guidance]").textContent() === keyGuidance[locale].text, "key guidance locale failed");
  verify(await link.evaluate(node => node.getAttribute("href") === "https://www.alphavantage.co/support/#api-key" &&
    node.target === "_blank" && node.rel === "noopener noreferrer" &&
    node.referrerPolicy === "no-referrer" && !node.hasAttribute("ping")), "official key link privacy failed");
  await link.scrollIntoViewIfNeeded();
  verify(await link.isVisible() && await root.locator("[data-api-guidance]").isVisible(), "key guidance is hidden");
  verify(await root.locator("[data-api-service]").inputValue() === "NOT_SELECTED" &&
    await root.locator("[data-api-service]").isDisabled() &&
    await root.locator("[data-api-refresh]").isDisabled(), "API must stay unselected and OFF");
  verify(await root.locator("[data-api-key]").inputValue() === "" &&
    await root.locator("[data-api-status]").getAttribute("data-stored") === "no", "keyless settings must remain empty");
}
async function emptyDevice(page) {
  return page.evaluate(() => new Promise((resolve, reject) => {
    const request = indexedDB.open("investment-device-actual-v1");
    request.onerror = () => reject(new Error("storage verification failed"));
    request.onsuccess = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("snapshots")) { db.close(); resolve(true); return; }
      const tx = db.transaction("snapshots", "readonly");
      const store = tx.objectStore("snapshots");
      let empty = true;
      for (const key of ["actual", "market", "api-settings"]) {
        const get = store.getKey(key);
        get.onsuccess = () => { if (get.result !== undefined) empty = false; };
      }
      tx.oncomplete = () => { db.close(); resolve(empty); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error("storage verification failed")); };
    };
  }));
}
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const launch = { headless: true };
  if (process.env.WEB_TEST_CHROMIUM_PATH) launch.executablePath = process.env.WEB_TEST_CHROMIUM_PATH;
  const browser = await chromium.launch(launch);
  try {
    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      const context = await browser.newContext({ viewport: { width, height: 844 } });
      const page = await context.newPage();
      const label = String(width) + "px " + locale;
      page.on("pageerror", () => { pageErrors += 1; });
      context.on("request", request => {
        const url = new URL(request.url());
        if (!["http:", "https:"].includes(url.protocol)) return;
        if (request.method() !== "GET" || request.postData() !== null) networkDataEvents += 1;
        if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname) ||
            request.method() !== "GET" || request.postData() !== null) requestProblems += 1;
      });
      context.on("response", response => {
        // The optional SEC sidecar is absent from a build without collection. Other failures remain errors.
        const missingSec = response.status() === 404 && response.url() === new URL("sec-public-inputs.json", base).href;
        if (response.status() >= 400 && !missingSec) responseProblems += 1;
      });
      await page.goto(new URL("#settings", base).href);
      await page.locator("#display-locale").selectOption(locale === "ko-KR" ? "en-US" : "ko-KR");
      await personalNotices(page, locale === "ko-KR" ? "en-US" : "ko-KR");
      await page.locator("#display-locale").selectOption(locale);
      verify(await page.locator("html").getAttribute("lang") === locale, "locale failed");
      const detailRoutes = await page.evaluate(async () => {
        const response = await fetch(new URL("entities.json", location.href));
        const { entities } = await response.json();
        const company = entities.find(entity => entity.entity_type === "COMPANY");
        const other = entities.find(entity => entity.entity_type !== "COMPANY");
        const bundle = await (await fetch(new URL("data.json", location.href))).json();
        if (company || bundle.companies.length || bundle.universe.data !== null)
          throw new Error("public membership must be withheld under GSQ-010");
        return other ? ["entity/" + encodeURIComponent(other.entity_type + ":" + other.canonical_id)] : [];
      });
      verify(detailRoutes.length === 1, "price-free entity route coverage unavailable");
      for (const route of ["home", "companies", "portfolio", "leaderboard", "news", "research", ...detailRoutes, "settings", "actual"]) {
        await page.goto(new URL("#" + route, base).href);
        await page.waitForFunction(() => document.querySelector("main h1, main h2, main iframe"));
        verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "horizontal overflow");
        await personalNotices(page, locale);
        if (route === "settings") await settingsGuidance(page, locale);
      }
      await page.locator("[data-security-index]").last().waitFor();
      verify(await page.locator("[data-security-index]").count() === 19, "catalog coverage failed");
      verify(await emptyDevice(page), "screenshot requires empty device");
      verify(await page.locator('[data-field="quantity"]').evaluateAll(nodes => nodes.every(n => n.value === "")), "quantity must be empty");
      verify(await page.locator('[data-field="average_cost"]').evaluateAll(nodes => nodes.every(n => n.value === "")), "cost must be empty");
      for (const [field, count] of [["quantity", 19], ["average_cost", 19], ["price", 19], ["price_as_of", 19], ["rate", 2], ["fx_as_of", 2]]) {
        const controls = page.locator('[data-field="' + field + '"]');
        verify(await controls.count() === count && await controls.evaluateAll(nodes => nodes.every(node => !node.disabled && !node.readOnly)), "keyless manual controls unavailable");
      }
      verify(await page.locator('[data-field="price"], [data-field="rate"]').evaluateAll(nodes => nodes.every(node => node.value === "")), "manual values must be empty");
      verify(await page.locator('[data-action="save"]').isEnabled(), "keyless manual save unavailable");
      const pwa = await page.evaluate(async () => ({
        manifests: document.querySelectorAll('link[rel="manifest"]').length,
        workers: navigator.serviceWorker ? (await navigator.serviceWorker.getRegistrations()).length : 0
      }));
      verify(pwa.manifests === 0 && pwa.workers === 0, "unexpected PWA cache or scope");
      const filename = "actual-empty-" + width + "-" + locale + ".png";
      await page.screenshot({ path: path.join(out, filename), fullPage: false });
      captures.push(filename);
      await page.reload();
      await page.locator("[data-security-index]").last().waitFor();
      verify(await emptyDevice(page), "refresh must preserve empty storage");
      await personalNotices(page, locale);
      checks.push(label + ": subpath routes, exact visible notices, locale switch, empty ACTUAL, refresh and screenshot");
      checks.push(label + ": official key guidance, API OFF, keyless manual controls, relative resources and no PWA cache/scope");
      await context.close();
    }
    verify(requestProblems === 0, "resource path or unexpected request failed");
    verify(responseProblems === 0, "resource response failed");
    verify(pageErrors === 0, "page runtime failed");
    verify(networkDataEvents === 0, "unexpected network data event");
    checks.push("all resources stay under the Pages project path");
    checks.push("no failed resources or unhandled runtime errors");
    const result = { passed: true, path: base.pathname, checks, screenshots: captures,
      screenshot_state: "ACTUAL_EMPTY", request_problems: requestProblems,
      response_problems: responseProblems, page_errors: pageErrors,
      network_data_events: networkDataEvents,
      pwa_manifest_count: 0, service_worker_count: 0 };
    fs.writeFileSync(path.join(out, "pages-browser.json"), JSON.stringify(result, null, 2) + "\n");
    for (const check of checks) console.log("PASS " + check);
  } catch (error) {
    const reason = error.safeReason || "browser operation failed";
    fs.writeFileSync(path.join(out, "pages-browser.json"), JSON.stringify({ passed: false, checks, failed_check: reason }) + "\n");
    console.error("Pages browser validation failed: " + reason);
    process.exitCode = 1;
  } finally { await browser.close(); }
})();
