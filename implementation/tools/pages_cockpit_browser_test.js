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
let requestProblems = 0, responseProblems = 0, pageErrors = 0;
function verify(value, label) { if (!value) throw new Error(label); }
async function emptyDevice(page) {
  return page.evaluate(() => new Promise((resolve, reject) => {
    const request = indexedDB.open("investment-device-actual-v1");
    request.onerror = () => reject(new Error("storage verification failed"));
    request.onsuccess = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("snapshots")) { db.close(); resolve(true); return; }
      const tx = db.transaction("snapshots", "readonly");
      const get = tx.objectStore("snapshots").get("actual");
      let empty = false;
      get.onsuccess = () => { empty = get.result === undefined || get.result === null; };
      tx.oncomplete = () => { db.close(); resolve(empty); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error("storage verification failed")); };
    };
  }));
}
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      const context = await browser.newContext({ viewport: { width, height: 844 } });
      const page = await context.newPage();
      const label = String(width) + "px " + locale;
      page.on("pageerror", () => { pageErrors += 1; });
      context.on("request", request => {
        const url = new URL(request.url());
        if (!["http:", "https:"].includes(url.protocol)) return;
        if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname) ||
            request.method() !== "GET" || request.postData() !== null) requestProblems += 1;
      });
      context.on("response", response => { if (response.status() >= 400) responseProblems += 1; });
      await page.goto(new URL("#settings", base).href);
      await page.locator("#display-locale").selectOption(locale);
      verify(await page.locator("html").getAttribute("lang") === locale, "locale failed");
      for (const route of ["home", "companies", "portfolio", "leaderboard", "news", "research", "settings", "actual"]) {
        await page.goto(new URL("#" + route, base).href);
        await page.waitForFunction(() => document.querySelector("main h1, main h2, main iframe"));
        verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "horizontal overflow");
      }
      await page.locator("[data-security-index]").last().waitFor();
      verify(await page.locator("[data-security-index]").count() === 19, "catalog coverage failed");
      verify(await emptyDevice(page), "screenshot requires empty device");
      verify(await page.locator('[data-field="quantity"]').evaluateAll(nodes => nodes.every(n => n.value === "")), "quantity must be empty");
      verify(await page.locator('[data-field="average_cost"]').evaluateAll(nodes => nodes.every(n => n.value === "")), "cost must be empty");
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
      checks.push(label + ": subpath routes, empty ACTUAL, refresh and screenshot");
      checks.push(label + ": relative resources and no PWA cache/scope");
      await context.close();
    }
    verify(requestProblems === 0, "resource path or unexpected request failed");
    verify(responseProblems === 0, "resource response failed");
    verify(pageErrors === 0, "page runtime failed");
    checks.push("all resources stay under the Pages project path");
    checks.push("no failed resources or unhandled runtime errors");
    const result = { passed: true, path: base.pathname, checks, screenshots: captures,
      screenshot_state: "ACTUAL_EMPTY", request_problems: requestProblems,
      response_problems: responseProblems, page_errors: pageErrors,
      pwa_manifest_count: 0, service_worker_count: 0 };
    fs.writeFileSync(path.join(out, "pages-browser.json"), JSON.stringify(result, null, 2) + "\n");
    for (const check of checks) console.log("PASS " + check);
  } catch (_) {
    fs.writeFileSync(path.join(out, "pages-browser.json"), JSON.stringify({ passed: false, checks }) + "\n");
    console.error("Pages browser validation failed");
    process.exitCode = 1;
  } finally { await browser.close(); }
})();
