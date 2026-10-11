"use strict";
// IA behavior on the public build. Every capture requires fresh empty device storage.
// No login, Google call, quotation, holdings or populated form is used by this test.
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const base = new URL(process.env.APP_NAV_IA_URL || process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:9003/Investment-System1/");
base.hash = "";
if (!base.pathname.endsWith("/")) base.pathname += "/";
const evidence = path.resolve(process.env.APP_NAV_IA_EVIDENCE_DIR || "/tmp/app-nav-ia-evidence");
const tabs = ["home", "qgv", "technical", "macro", "validation"];
const groups = ["investments", "companies", "market", "performance"];
// Official Macro v0.1.4 Candidate §15, also retained by IA v1 §3/S09.
const macroAxes = ["Growth", "Inflation", "Liquidity", "Monetary Policy", "Credit", "Labor", "Fiscal", "FX"];
const macroStates = ["Level", "Direction", "Momentum", "Surprise", "Stress", "Confidence"];
const labels = { "ko-KR": ["오늘", "QGV", "기술", "매크로", "검증"], "en-US": ["Today", "QGV", "Technical", "Macro", "Validation"] };
const checks = [], screenshots = [];
let browser, current = "browser launch", operation = "browser launch";
const traffic = { external: 0, unsafe: 0, failed_responses: 0, page_errors: 0, csp_violations: 0, console_csp_warnings: 0 };
function verify(value, name) { if (!value) { const e = new Error(name); e.safeReason = name; throw e; } checks.push(current + ": " + name); }
async function emptyDevice(page) {
  return page.evaluate(async () => {
    if (!(await indexedDB.databases()).some(db => db.name === "investment-device-actual-v1")) return true;
    const db = await new Promise((resolve, reject) => { const request = indexedDB.open("investment-device-actual-v1", 1); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(Error("storage")); });
    try { return await new Promise((resolve, reject) => {
      if (!db.objectStoreNames.contains("snapshots")) { resolve(true); return; }
      const tx = db.transaction("snapshots", "readonly"), store = tx.objectStore("snapshots"); let empty = true;
      for (const key of ["actual", "market", "api-settings", "google-sheet-settings", "market-import-history"]) { const r = store.getKey(key); r.onsuccess = () => { if (r.result !== undefined) empty = false; }; }
      tx.oncomplete = () => resolve(empty); tx.onerror = tx.onabort = () => reject(Error("storage"));
    }); } finally { db.close(); }
  });
}
async function active(page, expected) {
  const selected = await page.locator('#primary-nav [data-nav-tab][aria-current="page"]').evaluateAll(nodes => nodes.map(node => node.dataset.navTab));
  verify(JSON.stringify(selected) === JSON.stringify(expected ? [expected] : []), "one current primary destination (or none in settings)");
  verify(await page.locator('#primary-nav [data-nav-group][aria-current="page"]').count() === 0, "subgroups never duplicate current-page semantics");
}
async function go(page, hash) {
  operation = "page.goto #" + hash;
  // A same-document hash change can detach the research iframe while it is loading.
  // Wait for the destination's rendered state instead of iframe-dependent networkidle.
  await page.goto(new URL("#" + hash, base).href, { waitUntil: "domcontentloaded" });
  operation = "wait for rendered destination #" + hash;
  const route = hash.split("/")[0], parent = ["companies", "portfolio", "actual", "leaderboard", "news", "company", "entity"].includes(route) ? "qgv" : route === "research" ? "validation" : route === "settings" ? null : route;
  const selector = {home: ".hero", qgv: '[data-hub="qgv"]', technical: '[data-ia-screen="technical"]', macro: '[data-ia-screen="macro"]', validation: '[data-hub="validation"]', companies: "#search", portfolio: "#device-actual-summary", actual: "#device-actual-root", news: "#news-pane", research: "#research-frame", settings: "#display-locale"}[route];
  const ticker = page.__iaCompanyTickers?.[decodeURIComponent(hash.slice(route.length + 1))] || null;
  await page.waitForFunction(({hash, parent, selector, route, ticker}) => {
    if (location.hash !== "#" + hash || !document.querySelector("main h1, main h2, main iframe")) return false;
    if (selector && !document.querySelector("main " + selector)) return false;
    // Identity-only companies (public build) open as COMPANY RESEARCH; producer-backed ones as COMPANY DETAIL. The title is the ticker either way.
    if (route === "company" && !["COMPANY DETAIL", "COMPANY RESEARCH"].includes(document.querySelector("main .eyebrow")?.textContent.trim())) return false;
    if (route === "company" && ticker && document.querySelector("main h1")?.textContent.trim() !== ticker) return false;
    if (route === "entity" && document.querySelector("main .eyebrow")?.textContent.trim() !== decodeURIComponent(hash.slice("entity/".length)).split(":")[0]) return false;
    if (route === "leaderboard" && document.querySelector("main .eyebrow")?.textContent.trim() !== "LEADERBOARD") return false;
    if (route === "news" && ticker && !document.querySelector("main p.muted")?.textContent.includes(ticker)) return false;
    if (route === "qgv" && hash.includes("/")) {
      const group = document.querySelector("#qgv-" + hash.split("/")[1]);
      if (!group?.contains(document.activeElement)) return false;
    }
    if (!document.querySelector("#primary-nav")) return true;
    const active = document.querySelector('#primary-nav [data-nav-tab][aria-current="page"]');
    return parent ? active?.dataset.navTab === parent : !active && ["설정", "Settings"].includes(document.querySelector("main h1")?.textContent.trim());
  }, {hash, parent, selector, route, ticker});
  verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "route has no horizontal overflow");
}
async function capture(page, hash, locale, width) {
  verify(await emptyDevice(page), "capture requires empty device storage");
  verify(await page.locator('input[data-field], [data-sheet-id], [data-sheet-paste], [data-api-key]').evaluateAll(nodes => nodes.every(node => !node.value)), "capture contains no populated private controls");
  const name = "ia-" + hash + "-" + locale + "-" + width + ".png";
  await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForFunction(() => scrollY === 0);
  await page.mouse.move(0, 0);
  await page.screenshot({ path: path.join(evidence, name), fullPage: false }); screenshots.push(name);
}
async function unavailableNewScreen(page, selector) {
  const root = page.locator(selector); await root.waitFor();
  verify(await root.locator("svg, canvas").count() === 0, "unavailable screen renders no invented chart");
  verify(await root.locator("dd, [data-value], .metric").evaluateAll(nodes => nodes.every(node => !/^\s*[+-]?(?:\d|\.\d)/.test(node.textContent))), "unavailable screen exposes no invented numeric value");
  verify((await root.textContent()).includes("NOT_AVAILABLE"), "unavailable screen states NOT_AVAILABLE");
}
(async () => {
  fs.mkdirSync(evidence, { recursive: true });
  try {
    browser = await chromium.launch({ headless: true, ...(process.env.WEB_TEST_CHROMIUM_PATH ? { executablePath: process.env.WEB_TEST_CHROMIUM_PATH } : {}) });
    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      current = width + "px " + locale;
      const context = await browser.newContext({ viewport: { width, height: 844 } });
      await context.exposeBinding("__reportIaCspViolation", () => { traffic.csp_violations++; });
      await context.addInitScript(locale => {
        localStorage.setItem("investment.web.v1.settings", JSON.stringify({ version: 1, display_locale: locale, source_language: "all" }));
        document.addEventListener("securitypolicyviolation", () => { window.__reportIaCspViolation(); });
      }, locale);
      await context.route("**/*", async route => {
        const request = route.request(), url = new URL(request.url());
        if (request.method() !== "GET" || request.postData()) { traffic.unsafe++; await route.abort(); return; }
        if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) { traffic.external++; await route.abort(); return; }
        await route.continue();
      });
      const page = await context.newPage();
      page.on("pageerror", () => { traffic.page_errors++; });
      page.on("console", message => { if (/Content Security Policy|violates.*(?:directive|policy)/i.test(message.text())) traffic.console_csp_warnings++; });
      // The optional SEC sidecar is absent from a build without collection; any other failure stays an error.
      page.on("response", response => { if (response.status() >= 400 && !(response.status() === 404 && response.url() === new URL("sec-public-inputs.json", base).href)) traffic.failed_responses++; });
      try {
        await go(page, "home");
        verify(await page.locator("#primary-nav").count() === 1, "primary navigation exists");
        const primary = page.locator("#primary-nav [data-nav-tab]");
        verify(JSON.stringify(await primary.evaluateAll(nodes => nodes.map(node => node.dataset.navTab))) === JSON.stringify(tabs), "five destinations follow the IA order");
        verify(JSON.stringify(await primary.evaluateAll(nodes => nodes.map(node => node.getAttribute("href")))) === JSON.stringify(tabs.map(tab => "#" + tab)), "five primary links use stable hashes");
        verify(await primary.evaluateAll(nodes => nodes.every(node => node.getBoundingClientRect().height >= 44)), "primary targets are touch-sized");
        // Labels must be meaningful in the selected locale, without rejecting optional subtitles.
        verify(await primary.evaluateAll((nodes, expected) => nodes.every((node, index) => node.textContent.includes(expected[index])), labels[locale]), "primary destination labels follow the display language");
        const subgroups = page.locator("#primary-nav [data-nav-group]");
        verify(JSON.stringify(await subgroups.evaluateAll(nodes => nodes.map(node => node.dataset.navGroup))) === JSON.stringify(groups), "QGV exposes four purpose groups");
        verify(JSON.stringify(await subgroups.evaluateAll(nodes => nodes.map(node => node.getAttribute("href")))) === JSON.stringify(groups.map(group => "#qgv/" + group)), "QGV groups use stable deep links");
        verify(await page.locator(".nav-subgroups").isVisible() === (width >= 1024), "QGV subgroups appear only in desktop navigation");
        verify(await page.locator("#primary-nav").evaluate((nav, desktop) => {
          const box = nav.getBoundingClientRect(), main = document.querySelector("main").getBoundingClientRect();
          return desktop ? box.left < main.left && box.right <= main.left + 1 && box.height > 300 : Math.abs(box.bottom - innerHeight) <= 2 && box.width <= innerWidth;
        }, width >= 1024), "mobile bottom bar or desktop left sidebar occupies its expected area");
        await active(page, "home");
        await page.evaluate(() => { window.__iaSpaSentinel = true; });
        for (const tab of tabs) {
          await page.locator('#primary-nav [data-nav-tab="' + tab + '"]').click();
          await page.waitForFunction(tab => location.hash === "#" + tab && document.querySelector('#primary-nav [data-nav-tab="' + tab + '"]')?.getAttribute("aria-current") === "page", tab);
          await active(page, tab);
          verify(await page.evaluate(() => window.__iaSpaSentinel === true), "primary link click navigates without reloading the document");
        }
        const original = await page.evaluate(() => fetch("data.json").then(response => response.text()));
        // The public build ships no producer company rows; companies are the price-free identities listed by the QGV company directory.
        await go(page, "companies");
        const listed = await page.locator("#company-list a[href^='#company/']").evaluateAll(nodes => {
          const node = nodes.find(item => /^[A-Z]{1,5}$/.test(item.querySelector(".ticker")?.textContent.trim() || ""));
          return node ? { id: decodeURIComponent(node.getAttribute("href").slice("#company/".length)), ticker: node.querySelector(".ticker").textContent.trim() } : null;
        });
        verify(listed !== null, "company directory lists price-free identities");
        page.__iaCompanyTickers = { [listed.id]: listed.ticker };
        const routes = await page.evaluate(async company => {
          const { entities } = await (await fetch("entities.json")).json();
          const other = entities.find(entity => entity.entity_type !== "COMPANY");
          return ["company/" + encodeURIComponent(company), "entity/" + encodeURIComponent(other.entity_type + ":" + other.canonical_id)];
        }, listed.id);
        await go(page, "qgv"); await active(page, "qgv");
        verify(await page.locator('[data-hub="qgv"] .hub-group').count() === 4, "QGV hub preserves all four groups");
        const destinations = ["#portfolio", "#profiles", "#model", "#actual", "#leaderboard", "#watchlist", "#companies", "#types", "#news", "#thirteenf", "#validation"];
        verify(JSON.stringify(await page.locator('[data-hub="qgv"] a.hub-card').evaluateAll(nodes => nodes.map(node => node.getAttribute("href")))) === JSON.stringify(destinations), "QGV available cards link to existing destinations");
        verify(await page.locator('[data-hub="qgv"] [data-feature-status]').evaluateAll(nodes => nodes.every(node => ["사용 가능", "부분", "준비 중", "설계만"].includes(node.dataset.featureStatus))), "QGV cards use explicit availability states");
        verify(await page.locator('[data-hub="qgv"] [data-feature-status="준비 중"], [data-hub="qgv"] [data-feature-status="설계만"]').evaluateAll(nodes => nodes.every(node => !node.closest("a") && node.closest(".hub-card")?.textContent.includes("NOT_AVAILABLE"))), "pending QGV features have no false navigation target");
        for (const href of destinations) {
          await go(page, "qgv"); await page.evaluate(() => { window.__iaSpaSentinel = true; });
          await page.locator('[data-hub="qgv"] a[href="' + href + '"]').click();
          await page.waitForFunction(href => location.hash === href && !document.querySelector('[data-hub="qgv"]'), href);
          await active(page, href === "#validation" ? "validation" : "qgv");
          verify(await page.evaluate(() => window.__iaSpaSentinel === true), "QGV card click opens its destination without a document reload");
        }
        for (const group of groups) {
          await go(page, "qgv/" + group); await active(page, "qgv");
          verify(await page.locator('[data-hub="qgv"] .hub-group').count() === 4, "group deep link retains the complete hub");
          verify(await page.evaluate(group => document.querySelector("#qgv-" + group)?.contains(document.activeElement), group), "group deep link focuses its section");
          verify(await page.evaluate(group => { const node = document.activeElement, section = document.querySelector("#qgv-" + group), box = node.getBoundingClientRect(); return section?.contains(node) && box.top >= -1 && box.bottom <= innerHeight + 1; }, group), "group deep link scrolls the requested heading into view");
        }
        await go(page, "qgv"); await capture(page, "qgv", locale, width);
        for (const hash of ["companies", "portfolio", "actual", "leaderboard", "news", "news/" + routes[0].slice("company/".length), ...routes]) {
          await go(page, hash); await active(page, "qgv");
          verify(await page.locator('main > .parent-row > .parent-link[href="#qgv"]').count() === 1, "legacy QGV destination offers a parent link");
          verify(await page.locator('main > .parent-row > .parent-link[href="#qgv"]').evaluate(node => { const box = node.getBoundingClientRect(); return box.width >= 44 && box.height >= 44; }), "legacy parent navigation meets minimum target size");
          verify(page.url().endsWith("#" + hash), "legacy deep-link hash is preserved");
        }
        await page.locator('main > .parent-row > .parent-link[href="#qgv"]').click(); await page.locator('[data-hub="qgv"]').waitFor(); await active(page, "qgv");
        await page.goBack(); await page.waitForFunction(() => !!document.querySelector('main > .parent-row > .parent-link[href="#qgv"]')); await active(page, "qgv");
        await go(page, "technical"); await active(page, "technical"); await unavailableNewScreen(page, '[data-ia-screen="technical"]');
        verify(JSON.stringify(await page.locator('[data-ia-screen="technical"] [data-tech-status]').evaluateAll(nodes => nodes.map(node => node.dataset.techStatus))) === JSON.stringify(["chart", "engine", "execution", "record"]), "technical chart, engine, execution and record availability stay separate");
        verify(await page.locator('[data-ia-screen="technical"] [data-tech-status="engine"], [data-ia-screen="technical"] [data-tech-status="execution"], [data-ia-screen="technical"] [data-tech-status="record"]').evaluateAll(nodes => nodes.length === 3 && nodes.every(node => node.textContent.includes("NOT_AVAILABLE"))), "technical engine, execution and record cards preserve missing-data status");
        await capture(page, "technical", locale, width);
        await go(page, "macro"); await active(page, "macro"); await unavailableNewScreen(page, '[data-ia-screen="macro"]');
        verify(await page.locator("[data-macro-axis]").count() === 8, "macro preserves eight independent axes");
        verify(JSON.stringify(await page.locator("[data-macro-axis]").evaluateAll(nodes => nodes.map(node => node.dataset.macroAxis))) === JSON.stringify(macroAxes), "macro axes preserve their official identities and order");
        verify(await page.locator("[data-macro-axis]").evaluateAll((nodes, expected) => nodes.every(node => JSON.stringify([...node.querySelectorAll("[data-macro-state]")].map(state => state.dataset.macroState)) === JSON.stringify(expected)), macroStates), "macro states preserve their official identities and order");
        verify(await page.locator("[data-macro-axis]").evaluateAll(nodes => nodes.every(node => node.querySelectorAll("[data-macro-state]").length === 6 && [...node.querySelectorAll("[data-macro-state]")].every(state => state.textContent.includes("NOT_AVAILABLE")))), "every macro axis preserves six unavailable states");
        await capture(page, "macro", locale, width);
        await go(page, "validation"); await active(page, "validation"); await unavailableNewScreen(page, '[data-hub="validation"]');
        verify(await page.locator('[data-hub="validation"] a[href="#research"]').count() === 1, "validation keeps existing research reachable");
        verify(await page.locator('[data-hub="validation"] .card').filter({ hasText: "NOT_AVAILABLE" }).count() === 5, "five S10 validation areas (paper, backtest, forward, track record, trials) remain unavailable");
        await capture(page, "validation", locale, width);
        await page.locator('[data-hub="validation"] a[href="#research"]').click(); await page.locator("#research-frame").waitFor(); await active(page, "validation");
        verify(await page.locator('main > .parent-row > .parent-link[href="#validation"]').count() === 1, "existing research offers its validation parent");
        verify(await page.locator('main > .parent-row > .parent-link[href="#validation"]').evaluate(node => { const box = node.getBoundingClientRect(); return box.width >= 44 && box.height >= 44; }), "research parent navigation meets minimum target size");
        await go(page, "settings"); await active(page, null);
        await page.locator("[data-sheet-enabled]").waitFor();
        verify(!await page.locator("[data-sheet-enabled]").isChecked(), "Google integration remains OFF");
        const otherLocale = locale === "ko-KR" ? "en-US" : "ko-KR";
        await page.locator("#display-locale").selectOption(otherLocale); await active(page, null);
        verify(await page.locator("html").getAttribute("lang") === otherLocale, "settings changes display language without selecting a primary tab");
        await page.locator("#display-locale").selectOption(locale);
        await go(page, "qgv"); await page.reload(); await page.locator('[data-hub="qgv"]').waitFor(); await active(page, "qgv");
        verify(await page.locator("html").getAttribute("lang") === locale, "language survives deep-link reload");
        verify(await page.evaluate(() => fetch("data.json").then(response => response.text())) === original, "navigation and language changes preserve the served read model");
      } finally { await context.close(); }
    }
    current = "all viewports and languages";
    verify(Object.values(traffic).every(count => count === 0), "no external calls, unsafe requests, failed responses, runtime errors or CSP violations");
    fs.writeFileSync(path.join(evidence, "app-nav-ia-browser.json"), JSON.stringify({ passed: true, checks, screenshots, screenshot_state: "DEVICE_EMPTY", traffic, payload_files_written: 0 }, null, 2) + "\n");
    console.log("PASS IA navigation: " + checks.length + " checks; " + screenshots.length + " empty screenshots; no external calls");
  } catch (error) {
    const reason = error.safeReason || "browser interaction failed (details omitted)";
    fs.writeFileSync(path.join(evidence, "app-nav-ia-browser.json"), JSON.stringify({ passed: false, failed_check: current + ": " + reason, failure_kind: error.name, operation, checks, screenshots, traffic, payload_files_written: 0 }, null, 2) + "\n");
    console.error("FAIL IA navigation: " + current + ": " + reason + " (" + error.name + ", " + operation + ")"); process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
})();
