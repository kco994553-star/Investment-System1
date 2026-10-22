"use strict";
const {displayOnlyOff}=require('./display_only_off.js');
const { routeEmptyPublicScreens } = require("./empty_public_screens.js");
const QgvFixture = require("./qgv_v2_fixture.js");
// IA behavior on the public build. Every capture requires fresh empty device storage.
// No login, Google call, quotation, holdings or populated form is used by this test.
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const base = new URL(process.env.APP_NAV_IA_URL || process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:9003/Investment-System1/");
base.hash = "";
if (!base.pathname.endsWith("/")) base.pathname += "/";
const evidence = path.resolve(process.env.APP_NAV_IA_EVIDENCE_DIR || "/tmp/app-nav-ia-evidence");
// Owner IA (2026-10-18, PRODUCT_IA_DIRECTIVE_20261018): 0 홈 · 1 QGV · 2 기술적 분석 · 3 매크로 · 4 뉴스 · 5 포트폴리오 ·
// 6 프롬프트 라이브러리 · n 구조 트리 · n+1 Lab, plus 전체 메뉴.
// Phone: bottom tab bar 홈 · QGV · 포트폴리오 · 뉴스 · 전체 (in that visual order). PC: numbered header menu 0 · 1~6 · n · n+1 · 전체.
const tabs = ["home", "qgv", "technical", "macro", "news", "portfolio", "prompts", "system", "lab"];
const tabHref = { home: "#home", qgv: "#leaderboard", technical: "#technical", macro: "#macro", news: "#news", portfolio: "#portfolio", prompts: "#research", system: "#system", lab: "#validation" };
// phoneTabs is DOM order (the bar shows portfolio before news through CSS order; checked separately below).
const phoneTabs = ["home", "qgv", "news", "portfolio"], desktopTabs = tabs;
// Every route belongs to one menu (settings to none). 13F (#thirteenf, #lab-13f) is QGV 1.3 (ontology check IA-2).
const TAB_OF = { home: "home", companies: "qgv", leaderboard: "qgv", watchlist: "qgv", company: "qgv", analysis: "qgv", entity: "qgv", types: "qgv", qgv: "qgv", profiles: "qgv",
  portfolio: "portfolio", actual: "portfolio", model: "portfolio", playbook: "portfolio", brief: "portfolio", report: "portfolio",
  news: "news", thirteenf: "qgv", macro: "macro", technical: "technical", research: "prompts", system: "system", validation: "lab", "lab-13f": "qgv", settings: null };
// Entity pages follow their kind: MACRO → 매크로, others (industry, investor) → QGV. Structure trees (#tree/<menu>) follow their menu.
const ENTITY_TAB = { MACRO: "macro" };
const TREE_TABS = ["qgv", "technical", "macro", "news", "portfolio"];
const tabOf = hash => { const [r, id = ""] = hash.replace(/^#/, "").split("/"); if (r === "entity") return ENTITY_TAB[decodeURIComponent(id).split(":")[0]] || "qgv"; if (r === "tree") return TREE_TABS.includes(id) ? id : "qgv";
  const anchored = ["validation", "technical", "macro", "news"].find(screen => r.startsWith(screen + "-")); return TAB_OF[anchored || r]; };
// Every route of the new IA, including the numbered section anchors and the structure trees.
const IA_ROUTES = ["home", "leaderboard", "companies", "watchlist", "profiles", "types", "lab-13f", "thirteenf", "tree/qgv", "qgv",
  "technical", "technical-pattern", "technical-notes", "tree/technical", "macro", "macro-cycle", "macro-rotation", "macro-industry", "macro-mine", "macro-chain", "tree/macro",
  "news-network", "news", "tree/news", "portfolio", "model", "actual", "report/real", "report/mock", "playbook", "brief", "tree/portfolio", "research", "system",
  "validation", "validation-backtest", "validation-forward", "settings"];
const groups = ["investments", "companies", "market", "performance"];
// Official Macro v0.1.4 Candidate §15, also retained by IA v1 §3/S09.
const macroAxes = ["Growth", "Inflation", "Liquidity", "Monetary Policy", "Credit", "Labor", "Fiscal", "FX"];
const macroStates = ["Level", "Direction", "Momentum", "Surprise", "Stress", "Confidence"];
// Visible labels: short names on phones and PCs below 1360 px (full names in the 전체 메뉴 sheet and on wide PCs).
const labels = { "ko-KR": ["홈", "QGV", "기술적 분석", "매크로", "뉴스", "포트폴리오", "프롬프트", "구조 트리", "Lab"], "en-US": ["Home", "QGV", "Technical", "Macro", "News", "Portfolio", "Prompts", "Tree", "Lab"] };
const numbers = ["0", "1", "2", "3", "4", "5", "6", "n", "n+1"];
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
  verify(await page.locator("#more-menu").isHidden() && await page.locator("#more-menu a").count() === 0, "the closed 더보기 menu exposes no second set of current-page links");
}
async function go(page, hash) {
  operation = "page.goto #" + hash;
  // A same-document hash change can detach the research iframe while it is loading.
  // Wait for the destination's rendered state instead of iframe-dependent networkidle.
  await page.goto(new URL("#" + hash, base).href, { waitUntil: "domcontentloaded" });
  operation = "wait for rendered destination #" + hash;
  const route = hash.split("/")[0], parent = tabOf(hash);
  const selector = {home: "[data-home]", qgv: '[data-hub="qgv"]', system: '[data-tree="system"]', tree: "[data-tree]", "lab-13f": '[data-pending-page="lab-13f"]', technical: '[data-ia-screen="technical"]', macro: '[data-ia-screen="macro"]', validation: '[data-hub="validation"]', companies: "#search", portfolio: "#device-actual-summary", actual: "#device-actual-root", news: "#news-pane", research: "#research-frame", settings: "#display-locale"}[route];
  const ticker = page.__iaCompanyTickers?.[decodeURIComponent(hash.slice(route.length + 1))] || null;
  await page.waitForFunction(({hash, parent, selector, route, ticker}) => {
    if (location.hash !== "#" + hash || !document.querySelector("main h1, main h2, main iframe")) return false;
    if (selector && !document.querySelector("main " + selector)) return false;
    // Identity-only companies (public build) open as COMPANY RESEARCH; producer-backed ones as COMPANY DETAIL. The title ends with the
    // ticker either way ("<name> · <ticker>" once the KR-NAMES table is loaded, the ticker alone before).
    if (route === "company" && !["COMPANY DETAIL", "COMPANY RESEARCH"].includes(document.querySelector("main .eyebrow")?.textContent.trim())) return false;
    if (route === "company" && ticker && !((t) => t === ticker || t?.endsWith(" · " + ticker))(document.querySelector("main h1")?.textContent.trim())) return false;
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
  verify(await root.locator('svg:not([data-cycle-kind="concept"]), canvas').count() === 0, "unavailable screen renders no invented chart (only the cycle ring concept diagram)");
  verify(await root.locator("[data-cycle-interval], [data-cycle-point]").count() === 0, "concept ring carries no estimated interval or point without a model");
  verify(await root.locator("dd, [data-value], .metric").evaluateAll(nodes => nodes.every(node => !/^\s*[+-]?(?:\d|\.\d)/.test(node.textContent))), "unavailable screen exposes no invented numeric value");
  verify((await root.textContent()).includes("NOT_AVAILABLE"), "unavailable screen states NOT_AVAILABLE");
}
(async () => {
  fs.mkdirSync(evidence, { recursive: true });
  try {
    browser = await chromium.launch({ headless: true, ...(process.env.WEB_TEST_CHROMIUM_PATH ? { executablePath: process.env.WEB_TEST_CHROMIUM_PATH } : {}) });
    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      current = width + "px " + locale;
      const context = await browser.newContext({ viewport: { width, height: 844 } });await displayOnlyOff(context);
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
      // Empty public screens regardless of the build: deploy builds carry live data, this test checks the empty IA.
      await routeEmptyPublicScreens(context);
      const page = await context.newPage();
      page.on("pageerror", () => { traffic.page_errors++; });
      page.on("console", message => { if (/Content Security Policy|violates.*(?:directive|policy)/i.test(message.text())) traffic.console_csp_warnings++; });
      // The optional SEC sidecar is absent from a build without collection; any other failure stays an error.
      page.on("response", response => { if (response.status() >= 400 && !(response.status() === 404 && ["sec-public-inputs.json", "forward-validation-ledger.json", "sec-qgv2.json"].some(name => response.url() === new URL(name, base).href))) traffic.failed_responses++; });
      try {
        await go(page, "home");
        verify(await page.locator("#primary-nav").count() === 1, "primary navigation exists");
        const desktop = width >= 1024, visibleTabs = desktop ? desktopTabs : phoneTabs;
        const primary = page.locator("#primary-nav [data-nav-tab]");
        verify(JSON.stringify(await primary.evaluateAll(nodes => nodes.map(node => node.dataset.navTab))) === JSON.stringify(tabs), "home and the eight menus follow the IA order");
        verify(JSON.stringify(await primary.evaluateAll(nodes => nodes.map(node => node.getAttribute("href")))) === JSON.stringify(tabs.map(tab => tabHref[tab])), "primary links use existing route hashes (system: the n structure tree)");
        verify(JSON.stringify(await page.locator("#primary-nav [data-nav-tab] .nav-num").allTextContents()) === JSON.stringify(numbers), "menus carry the owner numbers 0 · 1~6 · n · n+1");
        verify(JSON.stringify(await primary.evaluateAll(nodes => nodes.filter(node => node.getBoundingClientRect().height > 0).map(node => node.dataset.navTab))) === JSON.stringify(visibleTabs), "phone shows 홈·QGV·뉴스·포트폴리오, PC shows 0 홈 and the eight numbered menus");
        if (!desktop) {
          // Phone tab bar, left to right: 홈 · QGV · 포트폴리오 · 뉴스 · 전체.
          const bar = await page.locator("#primary-nav > a, #primary-nav > button").evaluateAll(nodes => nodes.filter(node => node.getBoundingClientRect().height > 0).map(node => [node.getBoundingClientRect().left, node.dataset.navTab || "more", node.innerText.trim()]).sort((a, b) => a[0] - b[0]));
          verify(JSON.stringify(bar.map(x => x[1])) === JSON.stringify(["home", "qgv", "portfolio", "news", "more"]), "phone tab bar order is 홈 · QGV · 포트폴리오 · 뉴스 · 전체");
          if (locale === "ko-KR") verify(JSON.stringify(bar.map(x => x[2])) === JSON.stringify(["홈", "QGV", "포트폴리오", "뉴스", "전체"]), "phone tab bar labels");
        }
        verify(await page.locator("#more-button").isVisible(), "전체 메뉴 is always reachable");
        verify(await page.locator("#primary-nav [data-nav-tab], #more-button").evaluateAll(nodes => nodes.filter(node => node.getBoundingClientRect().height > 0).every(node => node.getBoundingClientRect().height >= 44 && node.getBoundingClientRect().width >= 44)), "primary targets are touch-sized");
        // Labels must be meaningful in the selected locale, without rejecting optional short labels.
        verify(await primary.evaluateAll((nodes, expected) => nodes.every((node, index) => node.textContent.includes(expected[index])), labels[locale]), "primary destination labels follow the display language");
        verify(await page.locator("#primary-nav").evaluate((nav, desktop) => {
          const box = nav.getBoundingClientRect(), main = document.querySelector("main").getBoundingClientRect(), header = document.querySelector("header").getBoundingClientRect();
          return desktop ? header.top <= box.top && box.bottom <= header.bottom + 1 && box.bottom <= main.top + 1 : Math.abs(box.bottom - innerHeight) <= 2 && box.width <= innerWidth;
        }, desktop), "phone bottom bar or PC header menu occupies its expected area");
        await active(page, "home");
        // 전체 메뉴 lists every existing destination under its menu; Escape closes it and returns focus to the button.
        await page.locator("#more-button").click(); await page.locator("#more-menu").waitFor();
        const moreLinks = await page.locator("#more-menu a").evaluateAll(nodes => nodes.map(node => node.getAttribute("href")));
        for (const href of ["#companies", "#leaderboard", "#watchlist", "#types", "#qgv", "#portfolio", "#actual", "#brief", "#profiles", "#model", "#playbook", "#news", "#macro", "#technical", "#thirteenf", "#report/mock", "#report/real", "#validation", "#research", "#system", "#lab-13f", "#settings",
          "#tree/qgv", "#technical-pattern", "#technical-notes", "#tree/technical", "#macro-cycle", "#macro-rotation", "#macro-industry", "#macro-mine", "#macro-chain", "#tree/macro", "#news-network", "#tree/news", "#tree/portfolio", "#validation-backtest", "#validation-forward"])
          verify(moreLinks.includes(href), "전체 메뉴 lists " + href);
        verify(JSON.stringify(await page.locator("#more-menu [data-menu-group]").evaluateAll(nodes => nodes.map(node => node.dataset.menuGroup))) === JSON.stringify(["qgv", "technical", "macro", "news", "portfolio", "prompts", "system", "lab", "settings"]), "전체 메뉴 groups follow the eight menus, then settings");
        verify(await page.locator("#more-menu [data-menu-pending]").evaluateAll(nodes => nodes.map(node => node.getAttribute("href")).join()) === "#lab-13f,#macro-rotation,#macro-chain", "only screens without implemented controls are marked 준비 중; official macro judgements remain uncomputed");
        verify(await page.locator('#more-menu a[href="#lab-13f"]').evaluate(node => node.closest("[data-menu-group]")?.dataset.menuGroup) === "qgv", "13F weight research is listed under QGV 1.3");
        await page.keyboard.press("Escape");
        verify(await page.locator("#more-menu").isHidden() && await page.evaluate(() => document.activeElement?.id === "more-button"), "Escape closes 전체 메뉴 and returns focus to its button");
        await page.evaluate(() => { window.__iaSpaSentinel = true; });
        for (const tab of tabs) {
          if (visibleTabs.includes(tab)) await page.locator('#primary-nav [data-nav-tab="' + tab + '"]').click();
          else if (tab === "home") await page.locator("header .brand").click();
          else { await page.locator("#more-button").click(); await page.locator('#more-menu a[href="' + tabHref[tab] + '"]').first().click(); }
          await page.waitForFunction(([tab, href]) => location.hash === href && document.querySelector('#primary-nav [data-nav-tab="' + tab + '"]')?.getAttribute("aria-current") === "page", [tab, tabHref[tab]]);
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
          await active(page, tabOf(href));
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
          await go(page, hash); await active(page, tabOf(hash));
          verify(await page.locator('main > .parent-row > .parent-link[href="#qgv"]').count() === 1, "legacy QGV destination offers a parent link");
          verify(await page.locator('main > .parent-row > .parent-link[href="#qgv"]').evaluate(node => { const box = node.getBoundingClientRect(); return box.width >= 44 && box.height >= 44; }), "legacy parent navigation meets minimum target size");
          verify(page.url().endsWith("#" + hash), "legacy deep-link hash is preserved");
        }
        await page.locator('main > .parent-row > .parent-link[href="#qgv"]').click(); await page.locator('[data-hub="qgv"]').waitFor(); await active(page, "qgv");
        await page.goBack(); await page.waitForFunction(() => !!document.querySelector('main > .parent-row > .parent-link[href="#qgv"]')); await active(page, tabOf(routes[1]));
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
        await go(page, "validation"); await active(page, "lab"); await unavailableNewScreen(page, '[data-hub="validation"]');
        verify(await page.locator('[data-hub="validation"] a[href="#research"]').count() === 1, "validation keeps existing research reachable");
        verify(await page.locator('[data-hub="validation"] .card').filter({ hasText: "NOT_AVAILABLE" }).count() === 4, "paper, backtest, track record and trials remain unavailable");
        verify(await page.locator('[data-hub="validation"] a[href="#validation-forward"]').count()===1,"existing forward ledger is reachable from the hub");
        await capture(page, "validation", locale, width);
        await page.locator('[data-hub="validation"] a[href="#research"]').click(); await page.locator("#research-frame").waitFor(); await active(page, "prompts");
        verify(await page.locator('main > .parent-row > .parent-link[href="#validation"]').count() === 1, "existing research offers its validation parent");
        verify(await page.locator('main > .parent-row > .parent-link[href="#validation"]').evaluate(node => { const box = node.getBoundingClientRect(); return box.width >= 44 && box.height >= 44; }), "research parent navigation meets minimum target size");
        await go(page, "settings"); await active(page, null);
        await page.locator("[data-sheet-enabled]").waitFor();
        verify(!await page.locator("[data-sheet-enabled]").isChecked(), "Google integration remains OFF");
        const otherLocale = locale === "ko-KR" ? "en-US" : "ko-KR";
        await page.locator("#display-locale").selectOption(otherLocale); await active(page, null);
        verify(await page.locator("html").getAttribute("lang") === otherLocale, "settings changes display language without selecting a primary tab");
        await page.locator("#display-locale").selectOption(locale);
        // 13F weight research (QGV 1.3) has no screen: a 준비 중 page that states what is missing, with no invented value.
        for (const [hash, tab] of [["lab-13f", "qgv"]]) {
          await go(page, hash); await active(page, tab); await unavailableNewScreen(page, '[data-pending-page="' + hash + '"]');
          verify(await page.locator('[data-pending-page="' + hash + '"] [data-pending-needs] li').count() >= 3, hash + " lists the data and decisions it needs");
          verify(await page.locator('[data-pending-page="' + hash + '"] .pending-links a').count() >= 2, hash + " links the closest existing screens");
        }
        // 13F planned flow ①→④ (owner draft QGV 1.3): one line per step, each marked not built and naming its pending decision IDs.
        {
          const steps = page.locator('[data-pending-page="lab-13f"] ol[data-pending-flow] > li[data-pending-step]');
          verify(JSON.stringify(await steps.evaluateAll(nodes => nodes.map(node => node.dataset.pendingStep))) === '["1","2","3","4"]', "13F flow lists steps 1 to 4 in order");
          verify(JSON.stringify(await steps.locator("b").allTextContents()) === JSON.stringify(locale === "ko-KR" ? ["① 운용사 고르기", "② 학습 기간에 맞추기", "③ 다른 기간에서 확인", "④ 결과"] : ["① Choose managers", "② Fit on the training period", "③ Check in another period", "④ Result"]), "13F flow step titles follow the owner draft in the display language");
          verify(await steps.evaluateAll(nodes => nodes.every(node => node.querySelectorAll(".badge.fn-unconnected").length === 1 && !node.querySelector(".badge.NOT_AVAILABLE"))), "each 13F step is marked not built without adding NOT_AVAILABLE badges");
          verify(JSON.stringify(await steps.locator("[data-decision-ids]").evaluateAll(nodes => nodes.map(node => (node.textContent.match(/13F-R\d+(?:~R?\d+)?|TRACKC-PORT/g) || []).join(" ")))) === JSON.stringify(["13F-R1~R9", "13F-R10~R12", "13F-R13 13F-R16", "13F-R14 13F-R15 TRACKC-PORT"]), "each 13F step names its pending decision IDs");
          const flowText = await page.locator('[data-pending-page="lab-13f"] [data-pending-flow]').textContent();
          verify(!/\d+(?:\.\d+)?\s*%|\b0\.\d+|\b[QGV]\s*\d{2}\b|예시|example|holdout|홀드아웃/i.test(flowText), "13F flow shows no weight, similarity, example value or holdout use");
          const bounds = await page.locator('[data-pending-page="lab-13f"] [data-pending-bounds] li').allTextContents();
          verify(bounds.length === 3 && (locale === "ko-KR" ? bounds[0].includes("실제 기준이 아닙니다") && bounds[1].includes("자동으로 바꾸지 않습니다") && bounds[2].includes("13F-R1~R16") : bounds[0].includes("not the institutions' actual criteria") && bounds[1].includes("never changed automatically") && bounds[2].includes("13F-R1–R16")), "13F flow states results are not institutional criteria, never change official defaults, and decisions 13F-R1~R16 are pending");
          verify(await page.locator('[data-pending-page="lab-13f"]').evaluate(node => node.scrollWidth <= node.clientWidth + 1), "13F flow fits the page width (" + width + "px)");
        }
        if (locale === "ko-KR") {
          // New IA: every route (sections and trees included) maps to exactly one menu, with one aria-current on the page.
          for (const hash of IA_ROUTES) {
            await go(page, hash); await active(page, tabOf(hash));
            // In-screen tabs (e.g. the report sets) keep their own aria-current; the menus (header, sheet, numbered strip) mark exactly one.
            verify(await page.locator("header [aria-current], #more-menu [aria-current], .ia-sub [aria-current]").count() === 1, "one menu aria-current per route (" + hash + ")");
            const flow = tabOf(hash) && tabOf(hash) !== "home" ? numbers[tabs.indexOf(tabOf(hash))] : null;
            verify(flow === null || await page.locator('main .flow-step[data-flow-step="' + flow + '"]').count() === 1, "flow line shows the menu number (" + hash + ")");
            const implemented={"technical-pattern":"[data-pattern-panel]","technical-notes":"[data-user-panel]","macro-cycle":"#macro-cycle-ring-root","macro-industry":"[data-cycle-ring=industry]:not([hidden])","macro-mine":"[data-cycle-ring]:not([hidden]) [data-cycle-user-box]"};
            if(implemented[hash]) verify(await page.locator(implemented[hash]).isVisible(),hash+" reaches its implemented controls");
            else if (/^(technical|macro)-/.test(hash)) verify((await page.locator("#" + hash).textContent()).includes("NOT_AVAILABLE"), hash + " states NOT_AVAILABLE");
          }
          // Structure trees: real engine weights; example values only from loaded data (none here: NA with a reason).
          await go(page, "tree/qgv");
          verify(JSON.stringify(await page.locator('[data-tree="qgv"] [data-weight]').evaluateAll(nodes => nodes.map(node => node.textContent))) === JSON.stringify(await page.evaluate(() => ["Q", "G", "V"].flatMap(a => Object.values(QgvV2.WEIGHTS[a]).map(String)))), "QGV tree weights are the engine's (QgvV2.WEIGHTS)");
          await page.locator('[data-tree-examples="qgv"] [data-example-state]').waitFor();
          verify(await page.locator('[data-tree-examples="qgv"] [data-example-state="NOT_AVAILABLE"]').count() === 1 && (await page.locator('[data-tree-examples="qgv"]').textContent()).includes("NA"), "without sec-qgv2.json the QGV example is NA with a reason, never a constant");
          await go(page, "tree/technical");
          verify(await page.locator('[data-tree-examples="technical"] [data-example-state="NOT_AVAILABLE"]').count() === 1, "technical example is NA (prices stay on the device)");
        }
        await go(page, "qgv"); await page.reload(); await page.locator('[data-hub="qgv"]').waitFor(); await active(page, "qgv");
        verify(await page.locator("html").getAttribute("lang") === locale, "language survives deep-link reload");
        verify(await page.evaluate(() => fetch("data.json").then(response => response.text())) === original, "navigation and language changes preserve the served read model");
      } finally { await context.close(); }
    }
    // Candle colours (Korean default, US toggle stored on this device) and tree examples read from the loaded sec-qgv2.json.
    for (const width of [390, 1280]) {
      current = width + "px candles and tree examples";
      const context = await browser.newContext({ viewport: { width, height: 844 } }); await displayOnlyOff(context);
      await context.route("**/*", async route => { const url = new URL(route.request().url()); if (route.request().method() !== "GET" || url.origin !== base.origin) { traffic.external++; await route.abort(); return; } await route.continue(); });
      await routeEmptyPublicScreens(context);
      // Synthetic Q·G test vector (qgv_v2_fixture.js), served as the published file.
      const payload = QgvFixture.strictPayload();
      await context.route("**/sec-qgv2.json*", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) }));
      const page = await context.newPage(); page.on("pageerror", () => { traffic.page_errors++; });
      try {
        await go(page, "technical");
        // Synthetic index bars (not prices): one rising (close >= open) and one falling candle drawn by the real chart renderer.
        const colours = () => page.evaluate(() => {
          const host = document.createElement("div"); host.id = "ia-candle-probe"; document.querySelector("#technical-price-chart").append(host);
          const day = 86400, bars = [{ timestamp: 20 * day, session_status: "COMPLETE", open: 1, high: 3, low: 1, close: 2, adjusted_close: null }, { timestamp: 21 * day, session_status: "COMPLETE", open: 2, high: 2, low: 1, close: 1, adjusted_close: null }];
          TechnicalChart.render(host, { bars, indicators: ResearchIndicators.calculate(bars), selected: new Set() });
          const fill = cls => getComputedStyle(host.querySelector(".daily-candle." + cls + " rect")).fill; const out = [fill("candle-up"), fill("candle-down"), document.documentElement.dataset.candles]; host.remove(); return out;
        });
        verify(JSON.stringify(await colours()) === JSON.stringify(["rgb(215, 50, 42)", "rgb(36, 87, 197)", "kr"]), "Korean default: rising candle red, falling blue");
        await go(page, "settings"); await page.locator('input[name="candle-choice"][value="us"]').check();
        verify(await page.evaluate(() => localStorage.getItem("investment.web.v1.candle-style")) === "us", "US style is stored in this device's preferences");
        await go(page, "technical"); await page.reload(); await page.locator('[data-ia-screen="technical"]').waitFor();
        verify(JSON.stringify(await colours()) === JSON.stringify(["rgb(31, 138, 76)", "rgb(215, 50, 42)", "us"]), "US style after reload: rising green, falling red");
        await go(page, "settings"); await page.locator('input[name="candle-choice"][value="kr"]').check();
        verify(await page.evaluate(() => document.documentElement.dataset.candles) === "kr", "Korean style restored");
        // Tree example values equal the loaded file's row (same selection rule recomputed in the page from the same payload).
        await go(page, "tree/qgv"); await page.locator('[data-tree-examples="qgv"] [data-example-state]').waitFor();
        const expected = await page.evaluate(p => {
          const inputs = Qgv2Inputs.fromInputs(SecQgv2.toInputs(p)), rows = inputs.records;
          const code = Object.keys(rows).filter(c => !c.startsWith("TARGET:")).sort().find(c => { const r = rows[c]; return r.state === "LIVE" && r.in_cross_section && Number.isFinite(r.qg_axes.Q.score) && Number.isFinite(r.qg_axes.G.score); });
          if (!code) return { code: null };
          return { code, as_of: inputs.as_of, factors: Object.fromEntries(Qgv2Inputs.FACTORS.map(f => [f, rows[code].factors[f] === null ? "NA" : (Math.round(rows[code].factors[f] * 10) / 10).toFixed(1)])) };
        }, payload);
        const shown = await page.evaluate(() => { const b = document.querySelector('[data-tree-examples="qgv"] [data-example-state]');
          return { state: b.dataset.exampleState, code: b.dataset.exampleCode || null, as_of: b.dataset.exampleAsOf || null, factors: Object.fromEntries([...b.querySelectorAll("tr[data-example-factor]")].map(r => [r.dataset.exampleFactor, r.querySelector("[data-example-value]").textContent])) }; });
        if (expected.code) {
          verify(shown.state === "LIVE" && shown.code === expected.code && shown.as_of === expected.as_of, "QGV example is the first LIVE row of the loaded sec-qgv2.json, with its as_of");
          verify(Object.entries(expected.factors).every(([f, v]) => shown.factors[f] === v), "QGV example factor values equal the loaded data");
          verify(["v_earnings_yield", "v_fcf_yield", "v_vs_industry", "v_vs_own_history", "v_expectation_check"].every(f => shown.factors[f] === "NA"), "V examples are NA (device prices only)");
        } else verify(shown.state === "NOT_AVAILABLE", "no LIVE row: the example is NA");
        verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "tree page has no horizontal overflow");
        await go(page, "system");
        verify(await page.locator('[data-tree="system"] [data-menu-col]').count() === 7, "n tree shows menus 1–6 and n+1");
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
