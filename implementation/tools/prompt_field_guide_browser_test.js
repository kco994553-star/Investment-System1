"use strict";
// Public build only. All captures have blank prompt inputs and no device records.
// Validation canaries stay in browser memory; no prompt preview or payload is written.
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const base = new URL(process.env.PROMPT_FIELD_GUIDE_URL || "http://127.0.0.1:9010/Investment-System1/#research");
const evidence = path.resolve(process.env.PROMPT_FIELD_GUIDE_EVIDENCE_DIR || "/tmp/prompt-field-guide-evidence");
const NOW = "2026-10-09T16:00:00.000Z", KST_TODAY = "2026-10-10";
const checks = [], screenshots = [];
const traffic = { external: 0, unsafe: 0, failed_responses: 0, page_errors: 0, csp_violations: 0 };
let browser, current = "browser launch", operation = "launch";
function verify(value, label) { if (!value) { const error = new Error(label); error.safeReason = label; throw error; } checks.push(current + ": " + label); }
async function blankDevice(page) {
  return page.evaluate(async () => {
    if (!(await indexedDB.databases()).some(db => db.name === "investment-device-actual-v1")) return true;
    const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
    try { return await new Promise(resolve => {
      if (!db.objectStoreNames.contains("snapshots")) { resolve(true); return; }
      const tx = db.transaction("snapshots", "readonly"), store = tx.objectStore("snapshots"); let empty = true;
      for (const key of ["actual", "market", "api-settings", "google-sheet-settings", "market-import-history"]) { const request = store.getKey(key); request.onsuccess = () => { if (request.result !== undefined) empty = false; }; }
      tx.oncomplete = () => resolve(empty);
    }); } finally { db.close(); }
  });
}
async function select(page, frame, id) {
  operation = "select a declared Frozen prompt";
  await frame.locator('#list [data-id="' + id + '"]').click();
  await frame.locator("[data-field-guide]").first().waitFor();
  await page.waitForFunction(id => document.getElementById("research-frame")?.contentDocument?.querySelector("#detail .code")?.textContent.includes(id), id);
}
async function emptyCapture(page, frame, locale, width, id) {
  await select(page, frame, id);
  verify(await blankDevice(page), "screenshot requires an empty device");
  verify(await frame.locator("[data-v]").evaluateAll(nodes => nodes.every(node => node.value === "")), "screenshot requires blank prompt inputs");
  verify(await frame.locator("[data-public-import]").count() === 0, "screenshot contains no synthetic imported context");
  const name = "prompt-guide-empty-" + locale + "-" + width + ".png";
  await page.locator("#research-frame").evaluate(node => node.scrollIntoView({block: "start"}));
  await frame.locator('[data-guide-group="target"]').evaluate(node => node.scrollIntoView({block: "start"}));
  await page.mouse.move(0, 0);
  await page.screenshot({ path: path.join(evidence, name), fullPage: false }); screenshots.push(name);
}
async function guideCoverage(page, frame, payload, locale) {
  const seen = new Set(), owners = new Set();
  for (const prompt of payload.prompts) {
    await select(page, frame, prompt.prompt_id);
    verify(await frame.locator("[data-field-guide]").count() === prompt.variables.length, "each declared variable has one guide");
    verify(await frame.locator("[data-v]").evaluateAll(nodes => nodes.every(node => node.value === "")), "examples never become initial input values");
    for (const variable of prompt.variables) {
      seen.add(variable.name); if (variable.owner) owners.add(variable.name);
      const wrapper = frame.locator('[data-field-guide="' + variable.name + '"]'), control = wrapper.locator("[data-v]");
      verify(await control.getAttribute("id") === "plv-" + variable.name, "input has its stable label target");
      verify(await wrapper.locator('label[for="plv-' + variable.name + '"]').count() === 1, "human input label is associated with the control");
      verify(await wrapper.locator("[data-guide-label]").textContent() === variable.guide.label[locale], "guide label uses the chosen display language");
      verify(await wrapper.locator("[data-guide-description]").textContent() === variable.guide.description[locale], "guide explains the expected input");
      verify((await wrapper.locator("[data-guide-source]").textContent()).includes(variable.guide.source[locale]), "guide identifies where input can come from");
      verify(await wrapper.locator("[data-guide-variable]").textContent() === variable.name, "original variable code remains readable");
      verify(await wrapper.evaluate((node, group) => node.closest("[data-guide-group]")?.dataset.guideGroup === group, variable.owner || variable.name === "input_mode" ? "system" : "target"), "target inputs and system context are grouped correctly");
      verify(await wrapper.locator('[data-system-import="' + variable.name + '"]').count() === (variable.owner ? 1 : 0), "only original system-owner variables have an import slot");
      if (variable.owner) verify((await wrapper.locator('[data-import-unavailable="' + variable.name + '"]').textContent()).includes("STANDALONE") === prompt.variables.some(value => value.name === "input_mode"), "missing context explains standalone only where the Frozen prompt supports that mode");
      verify(await control.getAttribute("aria-invalid") === (variable.required ? "true" : "false"), "blank required fields are invalid while the optional field is allowed");
      if (variable.required) verify((await wrapper.locator("[data-field-error]").textContent()).trim().length > 0, "required blank input has a visible field-level explanation");
      if (variable.kind === "INPUT_MODE") {
        verify(await control.inputValue() === "", "input mode has no default selection");
        verify(JSON.stringify(await control.locator("option").evaluateAll(nodes => nodes.map(node => node.value))) === JSON.stringify(["", "SYSTEM_CONTEXT", "STANDALONE"]), "input mode retains only the two Frozen choices");
      } else verify(await control.getAttribute("placeholder") === variable.guide.placeholder[locale], "example stays only in the placeholder");
    }
    verify(await frame.locator("[data-public-import]").count() === 0, "missing public context never offers an automatic import button");
    verify(await frame.locator("[data-import-unavailable]").count() === prompt.variables.filter(variable => variable.owner).length, "each missing system context has an honest availability message");
    verify(await frame.locator("#copy").isDisabled(), "blank required fields keep copy disabled");
  }
  verify(seen.size === 34, "all 34 active Frozen variable names are covered");
  verify(owners.size === 9, "all nine original owner variables are covered");
}
async function validationAndLocale(page, frame, payload, locale) {
  const prompt = payload.prompts.find(prompt => prompt.prompt_id === "plv1.tech.001");
  await select(page, frame, prompt.prompt_id);
  const asOf = frame.locator('[data-v="as_of"]'), mode = frame.locator('[data-v="input_mode"]');
  verify(await asOf.inputValue() === "", "date is blank until the user clicks today");
  operation = "explicit KST today button";
  await frame.locator('[data-guide-today="as_of"]').click();
  verify(await asOf.inputValue() === KST_TODAY, "today uses the explicit KST date across the UTC boundary");
  verify(await frame.locator('[data-v]:not([data-v="as_of"])').evaluateAll(nodes => nodes.every(node => node.value === "")), "today changes only the date field");
  await asOf.fill("2099-01-01");
  verify(await asOf.getAttribute("aria-invalid") === "true" && (await frame.locator('[data-field-error="as_of"]').textContent()).trim().length > 0, "future cutoff gets a field-level error");
  await asOf.fill(KST_TODAY); await mode.selectOption("STANDALONE");
  const ticker = frame.locator('[data-v="ticker"]'); await ticker.fill("{{invalid}}");
  verify(await ticker.getAttribute("aria-invalid") === "true", "placeholder braces are rejected at the input field");
  await ticker.fill("synthetic-context");
  await frame.locator('[data-v="period"]').fill("synthetic-horizon");
  await frame.locator('[data-v="technical_input"]').fill("synthetic supplied evidence");
  verify(await frame.locator("#copy").isEnabled(), "valid explicit input reaches the unchanged copy-ready state");
  const before = await frame.locator("[data-v]").evaluateAll(nodes => nodes.map(node => [node.dataset.v, node.value]));
  const preview = await frame.locator("#pv").textContent(), canonical = await frame.locator("#plv1-data").textContent();
  const otherLocale = locale === "ko-KR" ? "en-US" : "ko-KR";
  operation = "display-locale message to the existing research frame";
  await page.evaluate(locale => document.getElementById("research-frame").contentWindow.postMessage({ type: "display_locale", locale }, location.origin), otherLocale);
  await page.waitForFunction(({label}) => document.getElementById("research-frame")?.contentDocument?.querySelector('[data-guide-label="ticker"]')?.textContent === label, {label: prompt.variables.find(variable => variable.name === "ticker").guide.label[otherLocale]});
  verify(JSON.stringify(await frame.locator("[data-v]").evaluateAll(nodes => nodes.map(node => [node.dataset.v, node.value]))) === JSON.stringify(before), "language changes preserve every entered value");
  verify(await frame.locator("#pv").textContent() === preview, "language changes preserve the canonical filled preview");
  verify(await frame.locator("#plv1-data").textContent() === canonical, "language changes preserve the embedded Frozen payload");
  await page.evaluate(locale => document.getElementById("research-frame").contentWindow.postMessage({ type: "display_locale", locale }, location.origin), locale);
  await page.waitForFunction(({label}) => document.getElementById("research-frame")?.contentDocument?.querySelector('[data-guide-label="ticker"]')?.textContent === label, {label: prompt.variables.find(variable => variable.name === "ticker").guide.label[locale]});
  await select(page, frame, "plv1.idea.005");
  const count = frame.locator('[data-v="candidate_count"]'); await count.fill("0");
  verify(await count.getAttribute("aria-invalid") === "true", "zero maximum candidates remains invalid");
}
async function publicImports(page, frame, payload) {
  operation = "project browser-memory public fixtures through the real parent handler";
  const frozenBefore = await frame.locator("#plv1-data").textContent();
  const fixture = await page.evaluate(() => {
    const selected = D.companies.slice(0, 2), marker = ["private", "fixture", "excluded"].join("-"),
      blockedToken = ["ya", "29."].join("") + marker,
      secretKeys = ["quantity", "amount", "price", "spreadsheet_id", "access_token", "refresh_token", "client_secret", "api_key", "sheet_id", "app_key", "app_secret", "auth_token", "bearer_token", "password", "portfolio_amount", "actual_weight", "token", "credential", "secret"];
    const privateObject = Object.fromEntries(secretKeys.map(key => [key, marker]));
    privateObject.quantity = 987654321; privateObject.amount = 987654322; privateObject.price = 987654323;
    privateObject.evidence = {records: [{...privateObject}]};
    const section = (name, data) => ({state: "DEMO", as_of: "2026-10-09", source: "browser-memory fixture", data,
      producer: {snapshot_id: "mock." + name}, ...privateObject});
    const rows = fn => Object.fromEntries(selected.map((company, index) => [company.company_id, {...fn(index), ...privateObject}]));
    D.qgv = section("qgv", rows(index => ({Q_score: 70 + index, G_score: 60 + index, V_score: 50 + index,
      total_score: 60 + index, confidence: index ? "HIGH" : 0.8, coverage_state: "COVERED"})));
    D.technical = section("technical", rows(() => ({regime: "NEUTRAL", execution_zone: "WATCH"})));
    D.macro = section("macro", {state: "NEUTRAL", regime: "TRANSITION", ...privateObject});
    D.leaderboard = section("leaderboard", {rows: selected.map((company, index) =>
      ({company_id: company.company_id, rank: index + 1, total_score: 60 + index, ...privateObject}))});
    D.universe = section("universe", {universe_id: "mock.universe", ...privateObject});
    delete D.universe.producer.snapshot_id;
    window.__promptGuideFixture = {marker, blockedToken, selected};
    const projected = researchPublicContext(), encoded = JSON.stringify(projected);
    const companyKeys = projected.companies.every(company => Object.keys(company).sort().join(",") === "company_id,ticker");
    const expected = ["existing_system_candidates", "macro_input", "macro_snapshot_summary", "qgv_snapshot_summary",
      "technical_input", "technical_screen_summary"];
    const fieldsExact = JSON.stringify(Object.keys(projected.fields).sort()) === JSON.stringify(expected.sort());
    return {ticker: selected[0].ticker, fieldsExact, companyKeys, noCanary: !encoded.includes(marker),
      noPrivateKeys: secretKeys.every(key => !encoded.includes('"' + key + '"')),
      noInferredIntegratedFields: ["system_summary", "system_coverage_summary", "snapshot_refs"].every(key => !Object.hasOwn(projected.fields, key)),
      explicitSnapshotMetadata: Object.values(projected.fields).every(value => value.snapshot_id === "mock." + value.section),
      metadata: Object.values(projected.fields).filter(value => value.rows || value.values).every(value =>
        value.state === "DEMO" && value.as_of === "2026-10-09" && value.source === "browser-memory fixture"),
      qgvKeys: projected.fields.qgv_snapshot_summary.rows.every(row => Object.keys(row).sort().join(",") ===
        "G_score,Q_score,V_score,company_id,confidence,coverage_state,ticker,total_score"),
      technicalKeys: projected.fields.technical_input.rows.every(row => Object.keys(row).sort().join(",") === "company_id,execution_zone,regime,ticker"),
      candidatesKeys: projected.fields.existing_system_candidates.rows.every(row => Object.keys(row).sort().join(",") === "company_id,rank,ticker,total_score"),
      macroKeys: Object.keys(projected.fields.macro_input.values).sort().join(",") === "regime,state",
      existingConfidenceKinds: projected.fields.qgv_snapshot_summary.rows[0].confidence === 0.8 && projected.fields.qgv_snapshot_summary.rows[1].confidence === "HIGH"};
  });
  for (const [key, value] of Object.entries(fixture)) if (key !== "ticker") verify(value, "public fixture projection: " + key);
  await page.evaluate(() => {
    window.__promptGuideAccess = {device: 0, storage: 0, database: 0, fetch: 0, private_sections: 0};
    const fail = key => { window.__promptGuideAccess[key]++; throw new Error("Forbidden fixture access"); };
    Object.defineProperty(window, "DeviceActual", {configurable: true, get: () => fail("device")});
    for (const key of ["portfolio", "market", "actual", "account"]) Object.defineProperty(D, key, {configurable: true, get: () => fail("private_sections")});
    for (const key of ["getItem", "setItem"]) Storage.prototype[key] = () => fail("storage");
    indexedDB.open = () => fail("database"); window.fetch = () => fail("fetch");
  });
  await frame.locator("html").evaluate(() => {
    window.__promptGuideAccess = {device: 0, storage: 0, database: 0, fetch: 0};
    const fail = key => { window.__promptGuideAccess[key]++; throw new Error("Forbidden fixture access"); };
    Object.defineProperty(window, "DeviceActual", {configurable: true, get: () => fail("device")});
    for (const key of ["getItem", "setItem"]) Storage.prototype[key] = () => fail("storage");
    indexedDB.open = () => fail("database"); window.fetch = () => fail("fetch");
    window.__promptGuideReceipt = {count: 0, context: null};
    addEventListener("message", event => {
      if (event.source === parent && event.origin === location.origin && event.data?.type === "research_public_context") {
        window.__promptGuideReceipt.count++; window.__promptGuideReceipt.context = event.data.context;
      }
    });
  });
  const receiptCount = () => frame.locator("html").evaluate(() => window.__promptGuideReceipt.count);
  async function request() {
    const before = await receiptCount();
    await frame.locator("html").evaluate(() => parent.postMessage({type: "research_public_context_request"}, location.origin));
    await page.waitForFunction(before => document.getElementById("research-frame").contentWindow.__promptGuideReceipt.count > before, before);
  }
  await request();
  verify(await frame.locator("html").evaluate(() => Object.keys(window.__promptGuideReceipt.context.fields).length === 6), "real same-origin parent request delivers six existing public fields");
  const beforeIgnored = await receiptCount();
  await page.evaluate(() => {
    const source = document.getElementById("research-frame").contentWindow, data = {type: "research_public_context_request"};
    dispatchEvent(new MessageEvent("message", {data, origin: location.origin, source: window}));
    dispatchEvent(new MessageEvent("message", {data, origin: "https://wrong-origin.invalid", source}));
  });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  verify(await receiptCount() === beforeIgnored, "parent ignores wrong-source and wrong-origin context requests");
  const childIgnored = await frame.locator("html").evaluate(() => {
    const previous = JSON.stringify(window.__promptGuideReceipt.context), data = {type: "research_public_context", context: {fields: {system_summary: "unexpected fixture"}}};
    dispatchEvent(new MessageEvent("message", {data, origin: location.origin, source: window}));
    dispatchEvent(new MessageEvent("message", {data, origin: "https://wrong-origin.invalid", source: parent}));
    return previous === JSON.stringify(publicResearchContext);
  });
  verify(childIgnored, "research frame ignores wrong-source and wrong-origin context responses");
  for (const field of ["technical_input", "qgv_snapshot_summary"]) {
    const prompt = payload.prompts.find(prompt => prompt.variables.some(variable => variable.name === field) && prompt.variables.some(variable => variable.name === "ticker"));
    verify(!!prompt, "a declared prompt exercises company-specific " + field);
    await select(page, frame, prompt.prompt_id);
    const ticker = frame.locator('[data-v="ticker"]'), target = frame.locator('[data-v="' + field + '"]'), button = frame.locator('[data-public-import="' + field + '"]');
    verify(await button.count() === 0, "company-specific import waits for an explicit ticker");
    await ticker.fill("UNREGISTERED-FIXTURE"); verify(await button.count() === 0, "unknown ticker never receives another company's context");
    await ticker.fill(fixture.ticker.toLowerCase()); await button.waitFor();
    verify(await target.inputValue() === "", "available context never fills a field before a click");
    operation = "explicit click imports a single sanitized public company context";
    await button.click();
    verify(await target.evaluate((node, field) => {
      const value = JSON.parse(node.value), row = value.rows?.[0];
      return value.rows?.length === 1 && row.ticker.toUpperCase() === document.querySelector('[data-v="ticker"]').value.toUpperCase() &&
        value.section === (field === "technical_input" ? "technical" : "qgv") && value.state === "DEMO" && value.as_of === "2026-10-09";
    }, field), "clicked company context keeps the exact ticker, state and cutoff");
    verify((await frame.locator("#pv").textContent()).includes(await target.inputValue()), "import input event inserts the exact projected JSON in the canonical preview");
    await target.fill("manual context preserved");
    await page.evaluate(field => {
      const name = field === "technical_input" ? "technical" : "qgv";
      window.__promptGuideFixture.companiesBefore = D.companies;
      window.__promptGuideFixture.rowsBefore = D[name].data;
      D.companies = D.companies.map(company => company.company_id === window.__promptGuideFixture.selected[1].company_id ?
        {...company, ticker: window.__promptGuideFixture.selected[0].ticker} : company);
      D[name].data = {[window.__promptGuideFixture.selected[0].company_id]: D[name].data[window.__promptGuideFixture.selected[0].company_id]};
    }, field);
    await request();
    verify(await button.count() === 0, "two catalog ticker matches block import even with one public analysis row");
    verify(await target.inputValue() === "manual context preserved", "unavailable or ambiguous import preserves existing manual input");
    await page.evaluate(field => { D.companies = window.__promptGuideFixture.companiesBefore; D[field === "technical_input" ? "technical" : "qgv"].data = window.__promptGuideFixture.rowsBefore; }, field);
    await request();
  }
  for (const field of ["existing_system_candidates", "macro_input", "macro_snapshot_summary", "technical_screen_summary"]) {
    const prompt = payload.prompts.find(prompt => prompt.variables.some(variable => variable.name === field));
    await select(page, frame, prompt.prompt_id);
    const target = frame.locator('[data-v="' + field + '"]'), button = frame.locator('[data-public-import="' + field + '"]'); await button.waitFor();
    verify(await target.inputValue() === "", "available " + field + " remains blank without user action");
    await button.click();
    verify(await target.evaluate(node => { const value = JSON.parse(node.value); return Array.isArray(value.rows) || Array.isArray(value.refs) || !!value.values; }), "explicit " + field + " click imports the projected public structure");
  }
  for (const field of ["system_summary", "system_coverage_summary", "snapshot_refs"]) {
    const integrated = payload.prompts.find(prompt => prompt.variables.some(variable => variable.name === field));
    await select(page, frame, integrated.prompt_id);
    verify(await frame.locator('[data-public-import="' + field + '"]').count() === 0 && await frame.locator('[data-import-unavailable="' + field + '"]').count() === 1,
      "individual public sections never fabricate integrated " + field);
  }
  const restrictions = await page.evaluate(() => {
    const originals = {qgv: D.qgv, technical: D.technical, macro: D.macro, leaderboard: D.leaderboard};
    const secret = window.__promptGuideFixture.blockedToken;
    D.qgv = {...D.qgv, source: secret}; D.technical = {...D.technical, withheld: {reason: "fixture withheld"}};
    D.macro = {...D.macro, state: "NOT_AVAILABLE"}; D.leaderboard = {...D.leaderboard, data: null};
    const unavailable = researchPublicContext();
    const noUnavailableRows = Object.keys(unavailable.fields).length === 0;
    for (const [name, section] of Object.entries(originals)) D[name] = section;
    for (const name of ["qgv", "technical", "macro", "leaderboard"]) D[name].producer.snapshot_id = secret;
    const noTokenSnapshotMetadata = Object.values(researchPublicContext().fields).every(value => value.snapshot_id === null);
    for (const name of ["qgv", "technical", "macro", "leaderboard"]) D[name].producer.snapshot_id = "sheet_id.fixture";
    const noSheetSnapshotMetadata = Object.values(researchPublicContext().fields).every(value => value.snapshot_id === null);
    for (const name of ["qgv", "technical", "macro", "leaderboard"]) D[name].producer.snapshot_id = "mock." + name;
    const originalSource = D.qgv.source, originalAsOf = D.qgv.as_of;
    const aliases = ["api_key", "app_key", "app_secret", "sheet_id", "sheet_url", "auth_token", "bearer_token", "quantity", "amount", "price", "balance", "account_number", "cash", "fx_rate", "portfolio_amount", "portfolio_value", "actual_weight", "token", "credential", "secret", "Authorization: Bearer"];
    const noMixedPrivateMetadata = aliases.every(alias => {
      D.qgv.source = "Public fixture metadata; " + alias + "=" + window.__promptGuideFixture.marker;
      return !researchPublicContext().fields.qgv_snapshot_summary;
    });
    D.qgv.source = originalSource;
    D.qgv.as_of = "not-an-iso-date";
    const noInvalidCutoff = !researchPublicContext().fields.qgv_snapshot_summary;
    D.qgv.as_of = originalAsOf;
    const id = window.__promptGuideFixture.selected[0].company_id, row = D.qgv.data[id], originalScore = row.Q_score, originalCoverage = row.coverage_state;
    row.Q_score = Infinity; row.coverage_state = "portfolio_amount";
    const filtered = researchPublicContext().fields.qgv_snapshot_summary.rows.find(value => value.company_id === id);
    const noNonfiniteOrPrivateCodes = !Object.hasOwn(filtered, "Q_score") && !Object.hasOwn(filtered, "coverage_state") && filtered.G_score === row.G_score;
    row.Q_score = originalScore; row.coverage_state = originalCoverage;
    return {noUnavailableRows, noTokenSnapshotMetadata, noSheetSnapshotMetadata, noMixedPrivateMetadata, noInvalidCutoff, noNonfiniteOrPrivateCodes};
  });
  for (const [name, value] of Object.entries(restrictions)) verify(value, "unavailable or unsafe public context is withheld: " + name);
  verify(await frame.locator("html").evaluate(() => !JSON.stringify(window.__promptGuideReceipt.context).includes(parent.__promptGuideFixture.marker) &&
    !document.querySelector("#detail").textContent.includes(parent.__promptGuideFixture.marker)), "private fixture values never enter received context or form text");
  verify(await page.evaluate(() => Object.values(window.__promptGuideAccess).every(count => count === 0)) &&
    await frame.locator("html").evaluate(() => Object.values(window.__promptGuideAccess).every(count => count === 0)), "public import never reads device, private sections, storage, database or network");
  verify(await frame.locator("#plv1-data").textContent() === frozenBefore, "imports preserve the original Frozen catalog bytes");
}
(async () => {
  fs.mkdirSync(evidence, { recursive: true });
  try {
    browser = await chromium.launch({ headless: true, ...(process.env.WEB_TEST_CHROMIUM_PATH ? { executablePath: process.env.WEB_TEST_CHROMIUM_PATH } : {}) });
    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      current = width + "px " + locale;
      const context = await browser.newContext({ viewport: { width, height: 844 }, timezoneId: "UTC" });
      await context.exposeBinding("__promptGuideCsp", () => { traffic.csp_violations++; });
      await context.addInitScript(locale => {
        localStorage.setItem("investment.web.v1.settings", JSON.stringify({version: 1, display_locale: locale, source_language: "all"}));
        document.addEventListener("securitypolicyviolation", () => window.__promptGuideCsp());
      }, locale);
      await context.route("**/*", async route => {
        const request = route.request(), url = new URL(request.url());
        if (request.method() !== "GET" || request.postData()) { traffic.unsafe++; await route.abort(); return; }
        if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname.replace(/[^/]*$/, ""))) { traffic.external++; await route.abort(); return; }
        await route.continue();
      });
      const page = await context.newPage();
      page.on("pageerror", () => { traffic.page_errors++; });
      page.on("response", response => { if (response.status() >= 400) traffic.failed_responses++; });
      await page.clock.setFixedTime(new Date(NOW));
      try {
        operation = "open the existing research route";
        await page.goto(base.href, {waitUntil: "domcontentloaded"});
        const frame = page.frameLocator("#research-frame"); await frame.locator("#list [data-id]").first().waitFor();
        const payload = JSON.parse(await frame.locator("#plv1-data").textContent());
        verify(payload.prompts.length === 70, "all original active prompts remain present");
        verify(payload.sha256 === "f0a6ed9005e22b8fa534d51135cc3e734aa9577150438a35d65823a4c283e68e", "Frozen catalog SHA remains unchanged");
        await guideCoverage(page, frame, payload, locale);
        verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "app fits the viewport");
        verify(await frame.locator("html").evaluate(node => node.scrollWidth <= innerWidth), "field guides fit the research viewport");
        await emptyCapture(page, frame, locale, width, "plv1.tech.001");
        await validationAndLocale(page, frame, payload, locale);
        await publicImports(page, frame, payload);
      } finally { await context.close(); }
    }
    current = "all viewports and languages";
    verify(Object.values(traffic).every(count => count === 0), "no external calls, unsafe requests, failed resources, runtime errors or CSP violations");
    fs.writeFileSync(path.join(evidence, "prompt-field-guide-browser.json"), JSON.stringify({passed: true, checks, screenshots, screenshot_state: "DEVICE_EMPTY_PROMPT_BLANK", traffic, payload_files_written: 0}, null, 2) + "\n");
    console.log("PASS Prompt field guides: " + checks.length + " checks; " + screenshots.length + " blank screenshots; no external calls");
  } catch (error) {
    const reason = error.safeReason || "browser interaction failed (details omitted)";
    fs.writeFileSync(path.join(evidence, "prompt-field-guide-browser.json"), JSON.stringify({passed: false, failed_check: current + ": " + reason, operation, failure_kind: error.name, checks, screenshots, traffic, payload_files_written: 0}, null, 2) + "\n");
    console.error("FAIL Prompt field guides: " + current + ": " + reason + " (" + operation + ")"); process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
})();
