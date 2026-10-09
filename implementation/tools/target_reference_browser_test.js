"use strict";
// Public reference only: fresh contexts, no portfolio fixtures or device storage.
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

const PAGE_URL = new URL(process.env.TARGET_REFERENCE_URL || "http://127.0.0.1:8990/Investment-System1/target.html");
const SOURCE_URL = "https://raw.githubusercontent.com/kco994553-star/Investment-System1/refs/heads/claude/investment-system-top500-validation-alrugm/implementation/docs/portfolio_target_owner/TARGET_v0.yaml";
const METADATA_URL = new URL("target-reference.json", PAGE_URL).href;
const OUTPUT = path.resolve(process.env.TARGET_REFERENCE_EVIDENCE_DIR || "/tmp/target-reference-browser-evidence");
const checks = [], screenshots = [];
let pageErrors = 0, unexpectedRequests = 0, nonReadOnlyRequests = 0;
function verify(value, label) { if (!value) throw new Error(label); }

(async () => {
  fs.mkdirSync(OUTPUT, { recursive: true });
  let current = "browser launch";
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    async function open(width = 390, locale = "ko-KR") {
      const context = await browser.newContext({ viewport: { width, height: 844 }, locale });
      await context.addInitScript(() => {
        window.__referenceStorageCalls = 0;
        window.__referenceFetches = [];
        for (const key of ["localStorage", "sessionStorage", "indexedDB"]) {
          Object.defineProperty(window, key, { configurable: true, get() {
            window.__referenceStorageCalls += 1;
            throw new Error("Device storage is forbidden on the public reference route");
          } });
        }
        const original = window.fetch.bind(window);
        window.fetch = (url, options) => {
          window.__referenceFetches.push({ url: String(url), cache: options?.cache,
            credentials: options?.credentials, referrerPolicy: options?.referrerPolicy,
            redirect: options?.redirect, method: options?.method || "GET", body: options?.body != null });
          return original(url, options);
        };
      });
      context.on("request", (request) => {
        const url = new URL(request.url());
        const sameProject = url.origin === PAGE_URL.origin && url.pathname.startsWith(new URL(".", PAGE_URL).pathname);
        if (!sameProject && request.url() !== SOURCE_URL) unexpectedRequests += 1;
        if (request.method() !== "GET" || request.postData() !== null) nonReadOnlyRequests += 1;
      });
      const page = await context.newPage();
      page.on("pageerror", () => { pageErrors += 1; });
      await page.goto(PAGE_URL.href, { waitUntil: "domcontentloaded" });
      return { page, context };
    }

    async function state(page, value) {
      await page.waitForFunction(expected => document.querySelector("[data-target-status]")?.dataset.state === expected &&
        (expected !== "NOT_AVAILABLE" || /cannot be verified|확인할 수 없습니다/.test(document.querySelector("[data-target-reason]")?.textContent || "")),
        value, { timeout: 18000 });
    }

    async function empty(page) {
      verify(await page.locator("[data-target-unit]").count() === 0, "numeric target rows were not cleared");
      verify(await page.locator("meter").count() === 0, "target bars were not cleared");
      verify(await page.locator("[data-target-output]").textContent() === "", "stale reference output remains");
    }

    async function revalidate(page, event = "pageshow") {
      await page.evaluate(event => {
        if (event === "visible") {
          Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
          document.dispatchEvent(new Event("visibilitychange"));
        } else window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
      }, event);
    }

    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      current = `${width}px ${locale}: genuine canonical root`;
      const { page, context } = await open(width, locale);
      await state(page, "REFERENCE_VALIDATED");
      verify(await page.locator("[data-target-holding]").count() === 19, "reviewed 19 holding coverage failed");
      verify(await page.locator("meter").count() === 4, "reviewed theme coverage failed");
      verify(await page.locator("html").getAttribute("lang") === (locale.startsWith("en") ? "en" : "ko"), "initial language failed");
      verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "horizontal overflow");
      verify(await page.evaluate(() => window.__referenceStorageCalls === 0), "route accessed device storage");
      verify(await page.evaluate(() => window.__referenceFetches.length >= 2 && window.__referenceFetches.every(r =>
        r.cache === "no-store" && r.credentials === "omit" && r.referrerPolicy === "no-referrer" &&
        r.redirect === "error" && r.method === "GET" && !r.body)), "fetch privacy options failed");
      const disclaimer = await page.locator("[data-target-disclaimer]").textContent();
      verify(disclaimer === (locale.startsWith("en") ? "Not investment advice / Reference only" : "투자 권유 아님 / 참고용"), "disclaimer failed");
      const file = `public-target-${width}-${locale}.png`;
      await page.screenshot({ path: path.join(OUTPUT, file), fullPage: false });
      screenshots.push(file);
      await page.locator("#target-language").selectOption(locale.startsWith("en") ? "ko" : "en");
      verify(await page.locator("[data-target-holding]").count() === 19, "language change lost valid reference");
      const before = await page.evaluate(() => window.__referenceFetches.length);
      await revalidate(page, "visible");
      await state(page, "REFERENCE_VALIDATED");
      verify(await page.evaluate(before => window.__referenceFetches.length >= before + 2, before), "visible event did not revalidate source");
      checks.push(current + ": ko/en, no storage, public-only screenshot and visible revalidation");
      await context.close();
    }

    for (const kind of ["hash-mismatch", "missing", "timeout"]) {
      current = kind + ": clear previously verified weights";
      const { page, context } = await open();
      await state(page, "REFERENCE_VALIDATED");
      await context.route(SOURCE_URL, async route => {
        if (kind === "timeout") return; // AbortController must end the in-flight request.
        await route.fulfill({ status: kind === "missing" ? 404 : 200,
          contentType: "text/plain", body: kind === "missing" ? "missing" : "changed root bytes" });
      });
      await revalidate(page);
      await state(page, kind === "hash-mismatch" ? "INVALIDATED" : "NOT_AVAILABLE");
      await empty(page);
      await page.locator("#target-language").selectOption("en");
      await empty(page);
      verify(await page.evaluate(() => window.__referenceStorageCalls === 0), "failure path accessed device storage");
      checks.push(current + ": pageshow invalidates, language cannot resurrect numbers");
      await context.close();
    }

    current = "metadata tampering: declared lineage is insufficient";
    {
      const { page, context } = await open();
      await state(page, "REFERENCE_VALIDATED");
      await context.route(METADATA_URL, async route => {
        const response = await route.fetch();
        const metadata = await response.json();
        metadata.catalog.instruments[0].target_units += 1;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(metadata) });
      });
      await revalidate(page);
      await state(page, "INVALIDATED");
      await empty(page);
      checks.push(current + ": pinned metadata bytes reject modified weights");
      await context.close();
    }

    current = "query cannot control source URL";
    {
      const { page, context } = await open();
      const queried = new URL(PAGE_URL);
      queried.search = "?source=https%3A%2F%2Finvalid.example%2Froot.yaml";
      await page.goto(queried.href, { waitUntil: "domcontentloaded" });
      await state(page, "REFERENCE_VALIDATED");
      verify(await page.evaluate(source => window.__referenceFetches.every(r =>
        r.url === source || r.url.endsWith("/target-reference.json")), SOURCE_URL), "query changed a fetch target");
      checks.push(current);
      await context.close();
    }

    verify(unexpectedRequests === 0, "unexpected network destination");
    verify(nonReadOnlyRequests === 0, "non-read-only network request");
    verify(pageErrors === 0, "unhandled runtime error");
    const result = { passed: true, path: PAGE_URL.pathname, checks, screenshots,
      screenshot_state: "PUBLIC_REFERENCE_ONLY_NO_DEVICE_DATA", unexpected_requests: unexpectedRequests,
      non_read_only_requests: nonReadOnlyRequests, page_errors: pageErrors };
    fs.writeFileSync(path.join(OUTPUT, "target-reference-browser.json"), JSON.stringify(result, null, 2) + "\n");
    checks.forEach(check => console.log("PASS " + check));
  } catch (_) {
    fs.writeFileSync(path.join(OUTPUT, "target-reference-browser.json"), JSON.stringify({ passed: false, failed_check: current, checks }, null, 2) + "\n");
    console.error("TARGET reference browser validation failed: " + current);
    process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
})();
