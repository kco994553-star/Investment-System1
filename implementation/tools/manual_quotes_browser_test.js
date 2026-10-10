"use strict";
// Synthetic positions, prices, FX, keys and exports stay in memory. Screenshots
// are allowed only in fresh contexts with every device record absent.
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
const base = new URL(process.env.MANUAL_QUOTES_URL || process.env.PAGES_COCKPIT_URL || "http://127.0.0.1:8991/Investment-System1/#actual");
const evidence = path.resolve(process.env.EVIDENCE_DIR || process.env.PAGES_COCKPIT_EVIDENCE_DIR || "/tmp/manual-quotes-cycle-evidence/ui");
const NOW = "2030-01-08T12:00:00.000Z", CURRENT = "2030-01-08T10:00:00.000Z";
const VALUES = { USD: { quantity: "2.1973", price: "11.56723", rate: "1400.57319" }, JPY: { quantity: "3.1981", price: "13.34519", rate: "9.517321" }, KRW: { quantity: "5.2179", price: "17.25113" } };
const KEY = "LOCAL_ONLY_KEY_CANARY_7F42", COST = "7.831729";
const canaries = [KEY, COST, ...Object.values(VALUES).flatMap(value => Object.values(value))];
const checks = [], screenshots = [];
const network = { outside_attempts: 0, post_attempts: 0, body_attempts: 0, canary_attempts: 0, console_canary_count: 0 };
let browser, currentCheck = "browser launch", pageErrors = 0;
function verify(value, label) { if (!value) { const error = new Error(label); error.safeReason = label; throw error; } }
async function check(label, run) { currentCheck = label; await run(); checks.push(label); console.log("PASS " + label); }
async function stored(page) {
  return page.evaluate(async () => {
    const db = await new Promise((resolve, reject) => { const request = indexedDB.open("investment-device-actual-v1", 1); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(new Error("storage")); });
    try {
      return await new Promise((resolve, reject) => {
        const tx = db.transaction("snapshots", "readonly"), store = tx.objectStore("snapshots"), result = {};
        for (const key of ["actual", "market", "api-settings"]) { const request = store.get(key); request.onsuccess = () => { result[key] = request.result === undefined ? null : request.result; }; }
        tx.oncomplete = () => resolve(result); tx.onabort = tx.onerror = () => reject(new Error("storage"));
      });
    } finally { db.close(); }
  });
}
async function putRecord(page, key, value) {
  await page.evaluate(async ({ key, value }) => {
    const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
    try { await new Promise((resolve, reject) => { const tx = db.transaction("snapshots", "readwrite"); tx.objectStore("snapshots").put(value, key); tx.oncomplete = resolve; tx.onabort = tx.onerror = () => reject(new Error("storage")); }); }
    finally { db.close(); }
  }, { key, value });
}
async function corruptClone(page, key, kind, marker, inspect = false) {
  return page.evaluate(async ({ key, kind, marker, inspect }) => {
    const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
    try {
      if (!inspect) {
        let value = { schema: "broken" };
        if (kind === "null") value = null;
        if (kind === "undefined") value = undefined;
        if (kind === "cyclic") { value.value = marker; value.self = value; }
        if (kind === "date") value.value = new Date(marker);
        if (kind === "map") value.value = new Map([["marker", marker], ["cycle", value]]);
        if (kind === "set") value.value = new Set([marker, value]);
        if (kind === "bigint") value.value = BigInt(marker);
        if (kind === "binary") value.value = new Uint8Array([marker]);
        if (kind === "non-json") value.value = { marker, nan: NaN, missing: undefined, negativeZero: -0 };
        if (kind === "opaque") value.value = new Blob(["same-size-bounded-" + marker], { type: "text/plain" });
        if (kind === "resizable") value.value = new ArrayBuffer(1, { maxByteLength: marker + 1 });
        if (kind === "tracking") { const buffer = new ArrayBuffer(2, { maxByteLength: 4 }); value.value = marker === 1 ? new Uint8Array(buffer, 0, 2) : new Uint8Array(buffer, 0); }
        await new Promise((resolve, reject) => { const tx = db.transaction("snapshots", "readwrite"); tx.objectStore("snapshots").put(value, key); tx.oncomplete = resolve; tx.onabort = tx.onerror = () => reject(new Error("storage")); }); return true;
      }
      return await new Promise(resolve => {
        const store = db.transaction("snapshots", "readonly").objectStore("snapshots"); let present = false;
        const presence = store.getKey(key); presence.onsuccess = () => { present = presence.result !== undefined; };
        const request = store.get(key);
        request.onsuccess = () => {
          const value = request.result;
          if (kind === "null" || kind === "undefined") { resolve(present && (kind === "null" ? value === null : value === undefined)); return; }
          if (!value || value.schema !== "broken") { resolve(false); return; }
          if (kind === "opaque") { if (value.value instanceof Blob) value.value.text().then(text => resolve(text === "same-size-bounded-" + marker)); else resolve(false); return; }
          if (kind === "resizable") { resolve(value.value.resizable === true && value.value.byteLength === 1 && value.value.maxByteLength === marker + 1); return; }
          if (kind === "tracking") { const view = value.value; if (!view.buffer.resizable) { resolve(false); return; } view.buffer.resize(3); resolve(view.length === (marker === 1 ? 2 : 3)); return; }
          resolve(kind === "cyclic" ? value.value === marker && value.self === value : kind === "date" ? Object.prototype.toString.call(value.value) === '[object Date]' && value.value.getTime() === marker : kind === "map" ? value.value instanceof Map && value.value.get("marker") === marker && value.value.get("cycle") === value : kind === "set" ? value.value instanceof Set && value.value.has(marker) && value.value.has(value) : kind === "bigint" ? value.value === BigInt(marker) : kind === "binary" ? value.value instanceof Uint8Array && value.value[0] === marker : value.value.marker === marker && Number.isNaN(value.value.nan) && value.value.missing === undefined && Object.is(value.value.negativeZero, -0));
        };
      });
    } finally { db.close(); }
  }, { key, kind, marker, inspect });
}
async function waitNotice(page, root, notice) { await page.waitForFunction(({ notice }) => document.querySelector('[data-actual-notice]')?.dataset.notice === notice, { notice }); }
async function save(page, root) { await root.locator('[data-action="save"]').click(); await page.waitForFunction(() => document.querySelector('[data-action="save"]')?.disabled === false); await waitNotice(page, root, "saved"); }
async function dialog(page, run) { const listener = prompt => prompt.accept(); page.on("dialog", listener); try { await run(); } finally { page.off("dialog", listener); } }
async function open(locale, width) {
  const context = await browser.newContext({ viewport: { width, height: 844 }, locale });
  await context.addInitScript(({ locale, now }) => {
    localStorage.setItem("investment.web.v1.settings", JSON.stringify({ version: 1, display_locale: locale, source_language: "all" }));
    const NativeDate = Date; window.Date = class extends NativeDate { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return NativeDate.parse(now); } };
    const blobs = new Map(), create = URL.createObjectURL.bind(URL);
    URL.createObjectURL = blob => { const url = create(blob); blobs.set(url, blob); return url; };
    window.__manualQuoteExports = [];
    const click = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () { const blob = blobs.get(this.href); if (this.download && blob instanceof Blob) window.__manualQuoteExports.push(blob.text()); else click.call(this); };
  }, { locale, now: NOW });
  await context.route("**/*", async route => {
    const request = route.request(), url = request.url(), body = request.postData() || "";
    const outside = new URL(url).origin !== base.origin, post = request.method() === "POST", hasBody = body.length > 0;
    const hasCanary = canaries.some(value => url.includes(value) || url.includes(encodeURIComponent(value)) || body.includes(value));
    if (outside) network.outside_attempts++; if (post) network.post_attempts++; if (hasBody) network.body_attempts++; if (hasCanary) network.canary_attempts++;
    if (outside || post || hasBody || hasCanary) await route.abort(); else await route.continue();
  });
  const page = await context.newPage();
  page.on("pageerror", () => { pageErrors++; });
  page.on("console", message => { if (canaries.some(value => message.text().includes(value))) network.console_canary_count++; });
  const actualURL = new URL(base); actualURL.hash = "actual";
  await page.goto(actualURL.href, { waitUntil: "networkidle" });
  const root = page.locator('.device-actual').filter({ has: page.locator('[data-action="save"]') }).first();
  await root.locator('[data-security-index]').last().waitFor();
  const catalog = await page.evaluate(async () => { const url = new URL("actual-catalog.json", location.href); return (await fetch(url)).json(); });
  return { context, page, root, catalog };
}
async function exportMemory(page, root) {
  await root.locator('[data-action="export"]').click();
  // The device backup is read asynchronously before the in-memory download is created.
  await page.waitForFunction(() => window.__manualQuoteExports.length > 0);
  return page.evaluate(async () => { const value = window.__manualQuoteExports.shift(); return value ? await value : null; });
}
async function importMemory(page, root, bytes) {
  await dialog(page, async () => { await root.locator('[data-action="import"]').setInputFiles({ name: "local-test.json", mimeType: "application/json", buffer: Buffer.from(bytes) }); await waitNotice(page, root, "imported"); });
}
async function settings(page) { const url = new URL(base); url.hash = "settings"; await page.goto(url.href, { waitUntil: "networkidle" }); const root = page.locator('[data-device-api-settings]'); await root.waitFor(); return root; }
async function returnActual(page) { const url = new URL(base); url.hash = "actual"; await page.goto(url.href, { waitUntil: "networkidle" }); const root = page.locator('.device-actual').filter({ has: page.locator('[data-action="save"]') }).first(); await root.locator('[data-security-index]').last().waitFor(); return root; }
async function valuationIs(page, complete) {
  return page.evaluate(async ({ complete, values }) => {
    const catalog = await (await fetch(new URL("actual-catalog.json", location.href))).json();
    const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
    const data = await new Promise(resolve => { const result = {}, tx = db.transaction("snapshots", "readonly"); for (const key of ["actual", "market"]) { const r = tx.objectStore("snapshots").get(key); r.onsuccess = () => { result[key] = r.result; }; } tx.oncomplete = () => resolve(result); }); db.close();
    const actual = DeviceActual.validate(data.actual, catalog), result = DeviceMarket.valuation(actual, catalog, data.market);
    if (!complete) return result.total === null && result.rows.every(row => row.weight === null && row.delta === null);
    const expected = Object.values(values).reduce((sum, value) => sum + Number(value.quantity) * Number(value.price) * Number(value.rate || 1), 0);
    return result.currency === "KRW" && Math.abs(result.total - expected) < 1e-6 && result.rows.length === 3 && result.rows.every(row => {
      const instrument = catalog.instruments.find(item => DeviceMarket.canonical(item.security_reference) === DeviceMarket.canonical(row.security_reference));
      const value = values[instrument.currency], native = Number(value.quantity) * Number(value.price), krw = native * Number(value.rate || 1);
      return Math.abs(row.market_value_native - native) < 1e-6 && row.market_currency_native === instrument.currency && Math.abs(row.market_value - krw) < 1e-6 && Math.abs(row.weight - krw / expected) < 1e-12 && Math.abs(row.delta - (krw / expected - instrument.target_units / catalog.total_units)) < 1e-12;
    });
  }, { complete, values: VALUES });
}
async function main() {
  fs.mkdirSync(evidence, { recursive: true });
  try {
    browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.CHROMIUM_EXECUTABLE_PATH } : {}) });
    await check("storage: resizable buffers and tracking views remain preserved on cleanup", async () => {
      for (const kind of ["resizable", "tracking"]) {
        const probe = await open("ko-KR", 390);
        try {
          await corruptClone(probe.page, "market", kind, 1);
          if (!(await corruptClone(probe.page, "market", kind, 1, true))) continue; // Older browsers may serialize these as fixed buffers.
          await probe.page.reload({ waitUntil: "networkidle" }); await probe.root.locator('[data-security-index]').last().waitFor();
          await corruptClone(probe.page, "market", kind, 2);
          await dialog(probe.page, async () => { await probe.root.locator('[data-action="delete"]').click(); await probe.page.waitForFunction(() => document.querySelector('[data-action="delete"]')?.disabled === false); });
          verify(await corruptClone(probe.page, "market", kind, 2, true), "resizable clone or view tracking state erased"); await waitNotice(probe.page, probe.root, "storage");
          await probe.page.reload({ waitUntil: "networkidle" }); await probe.root.locator('[data-security-index]').last().waitFor();
          await dialog(probe.page, async () => { await probe.root.locator('[data-action="delete"]').click(); await probe.page.waitForFunction(() => document.querySelector('[data-action="delete"]')?.disabled === false); });
          verify(await corruptClone(probe.page, "market", kind, 2, true), "unverifiable resizable clone erased"); await waitNotice(probe.page, probe.root, "storage");
        } finally { await probe.context.close(); }
      }
    });
    for (const width of [390, 1280]) for (const locale of ["ko-KR", "en-US"]) {
      const label = width + "px " + locale, session = await open(locale, width);
      let { page, root, catalog } = session;
      const selected = Object.fromEntries(["USD", "JPY", "KRW"].map(currency => [currency, catalog.instruments.findIndex(row => row.currency === currency)]));
      let backup, legacyFile; // backup: the current unified device backup; legacyFile: a pre-unification device-actual-holdings/2 file with market_data
      const enterMarket = async () => {
        for (const currency of ["USD", "JPY", "KRW"]) {
          const row = root.locator('[data-security-index="' + selected[currency] + '"]');
          await row.locator('[data-field="price"]').fill(VALUES[currency].price); await row.locator('[data-field="price_as_of"]').fill(CURRENT);
        }
        for (const currency of ["USD", "JPY"]) { const fx = root.locator('[data-fx-currency="' + currency + '"]'); await fx.locator('[data-field="rate"]').fill(VALUES[currency].rate); await fx.locator('[data-field="fx_as_of"]').fill(CURRENT); }
        await save(page, root);
      };
      try {
        await check(label + ": every catalog row has manual price, visible timestamp and provenance", async () => {
          verify(await root.locator('[data-field="price"]').count() === 19, "manual prices missing");
          verify(await root.locator('[data-field="price_as_of"]').count() === 19, "price timestamps missing");
          verify(await root.locator('[data-quote-source]').count() === 19, "price sources missing");
          for (const currency of ["USD", "JPY"]) verify(await root.locator('[data-fx-currency="' + currency + '"] [data-field="rate"]').count() === 1, "manual FX missing");
          verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "layout overflow");
        });
        await check(label + ": mixed native prices and explicit FX save, refresh and value in KRW", async () => {
          for (const currency of ["USD", "JPY", "KRW"]) {
            verify(selected[currency] >= 0, "native currency absent in catalog");
            const row = root.locator('[data-security-index="' + selected[currency] + '"]');
            await row.locator('[data-field="quantity"]').fill(VALUES[currency].quantity); await row.locator('[data-field="average_cost"]').fill(COST);
            await row.locator('[data-field="price"]').fill(VALUES[currency].price); await row.locator('[data-field="price_as_of"]').fill(CURRENT);
          }
          for (const currency of ["USD", "JPY"]) { const fx = root.locator('[data-fx-currency="' + currency + '"]'); await fx.locator('[data-field="rate"]').fill(VALUES[currency].rate); await fx.locator('[data-field="fx_as_of"]').fill(CURRENT); }
          await save(page, root); const data = await stored(page);
          verify(data.actual?.schema === "device-actual-holdings/1" && !!data.market, "separate legacy actual and market absent");
          verify(await valuationIs(page, true), "mixed currency valuation incorrect");
          verify((await root.locator('[data-market-total]').textContent()).includes("KRW"), "KRW total absent");
          verify((await root.locator('.actual-value-list').textContent()).includes("%p"), "delta percentage points absent");
          await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
          verify(await valuationIs(page, true), "local valuation did not survive refresh");
          verify(await root.locator('[data-security-index="' + selected.USD + '"] [data-field="price"]').inputValue() === VALUES.USD.price, "price did not survive refresh");
        });
        await check(label + ": legacy external quotes retain native row denominations", async () => {
          await page.evaluate(async ({ values, current, now, locale }) => {
            const catalog = await (await fetch(new URL("actual-catalog.json", location.href))).json(), host = document.createElement("div"); host.dataset.legacyProbe = ""; document.querySelector("main").append(host);
            const quotes = ["USD", "JPY", "KRW"].map(currency => ({ security_reference: catalog.instruments.find(row => row.currency === currency).security_reference, currency, price: values[currency].price, as_of: current, available_at: now }));
            await DeviceActual.mount(host, { catalog, locale, quotes });
          }, { values: VALUES, current: CURRENT, now: NOW, locale });
          const probe = page.locator('[data-legacy-probe]');
          try {
            verify(await probe.locator('.actual-value-row').count() === 3, "legacy valuation rows absent");
            verify(await probe.locator('.actual-value-row dl').evaluateAll(nodes => nodes.every(node => {
              const label = node.querySelectorAll('dt')[2].textContent, value = node.querySelectorAll('dd')[2].textContent;
              return !label.includes('null') && !value.includes('null') && !value.includes('NOT_AVAILABLE') && ['USD', 'JPY', 'KRW'].some(currency => value.endsWith(currency));
            })), "legacy native market value denomination missing");
          } finally { await probe.evaluate(host => host.remove()); }
        });
        await check(label + ": portfolio summary loads market and follows device changes", async () => {
          const original = (await stored(page)).market, url = new URL(base); url.hash = "portfolio";
          await page.goto(url.href, { waitUntil: "networkidle" }); const summary = page.locator('.actual-compact [data-market-total]'); await summary.waitFor();
          const before = await summary.textContent(); verify(before.includes("KRW") && !before.includes("NOT_AVAILABLE"), "portfolio summary ignored market");
          const changed = JSON.parse(JSON.stringify(original)); changed.version++; changed.quotes[0].price = String(Number(changed.quotes[0].price) + 1);
          await putRecord(page, "market", changed); await page.evaluate(() => document.dispatchEvent(new Event("device-actual-changed")));
          await page.waitForFunction(text => document.querySelector('.actual-compact [data-market-total]')?.textContent !== text, before);
          verify(!(await summary.textContent()).includes("NOT_AVAILABLE"), "summary update discarded known market");
          await putRecord(page, "market", original); await page.evaluate(() => document.dispatchEvent(new Event("device-actual-changed")));
          await page.waitForFunction(text => document.querySelector('.actual-compact [data-market-total]')?.textContent === text, before); root = await returnActual(page);
        });
        await check(label + ": local key persists, provider and refresh stay disabled", async () => {
          const api = await settings(page); await api.locator('[data-api-key]').fill(KEY); await api.locator('[data-api-action="save"]').click();
          await page.waitForFunction(() => document.querySelector('[data-api-status]')?.dataset.stored === "yes");
          verify(await api.locator('[data-api-key]').inputValue() === "", "stored key reflected into input");
          verify(await api.locator('[data-api-refresh]').isDisabled(), "API refresh enabled without service");
          verify(await api.locator('[data-api-service]').isDisabled(), "service choice enabled");
          verify(!(await api.textContent()).includes(KEY), "key reflected into settings");
          await page.reload({ waitUntil: "networkidle" }); verify(await api.locator('[data-api-status]').getAttribute('data-stored') === "yes", "key did not persist");
          verify(await api.locator('[data-api-key]').inputValue() === "", "saved key rendered after reload"); root = await returnActual(page);
        });
        await check(label + ": device backup export stays in memory and excludes prices, FX and API settings", async () => {
          // Current contract ("Unify device backups", device_market.exportBackup): quotes, FX and imported prices are never backed up.
          backup = await exportMemory(page, root); const payload = JSON.parse(backup);
          verify(payload.schema === "investment-device-backup/2" && payload.portfolio?.schema === "device-actual-holdings/1" && payload.portfolio.themes.some(theme => theme.holdings.length > 0), "device backup envelope absent");
          verify(!backup.includes("market_data") && !backup.includes("price_as_of") && !backup.includes("fx_as_of"), "backup includes market data");
          verify(!Object.values(VALUES).some(value => backup.includes(value.price) || (value.rate && backup.includes(value.rate))) && !backup.includes(CURRENT), "backup includes a price, FX rate or quote time");
          verify(!backup.includes(KEY) && !backup.includes("api-settings") && !backup.includes("api_key"), "backup includes API key");
          // A file written before the unification still carries market_data (built here in memory only).
          legacyFile = await page.evaluate(async () => {
            const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
            const data = await new Promise(resolve => { const result = {}, tx = db.transaction("snapshots", "readonly"); for (const key of ["actual", "market"]) { const r = tx.objectStore("snapshots").get(key); r.onsuccess = () => { result[key] = r.result; }; } tx.oncomplete = () => resolve(result); }); db.close();
            return JSON.stringify({ ...data.actual, schema: "device-actual-holdings/2", market_data: data.market });
          });
          verify(JSON.parse(legacyFile).market_data?.quotes?.length > 0, "legacy schema two fixture lacks market data");
        });
        await check(label + ": delete clears holdings and market while preserving local key", async () => {
          await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await waitNotice(page, root, "removed"); });
          const data = await stored(page); verify(data.actual === null && data.market === null && !!data['api-settings'], "delete did not isolate key settings");
          await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
          verify((await stored(page)).market === null, "deleted market returned");
        });
        await check(label + ": in-memory device backup restores holdings only and never prices or FX", async () => {
          // Restore asks for confirmation and sets no import notice: wait for the stored holdings instead.
          await dialog(page, async () => {
            await root.locator('[data-action="import"]').setInputFiles({ name: "local-test.json", mimeType: "application/json", buffer: Buffer.from(backup) });
            await page.waitForFunction(async () => { const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); }); try { return await new Promise(resolve => { const r = db.transaction("snapshots", "readonly").objectStore("snapshots").get("actual"); r.onsuccess = () => resolve(r.result !== undefined && r.result !== null); }); } finally { db.close(); } });
          });
          const restored = await stored(page);
          verify(restored.actual?.themes.some(theme => theme.holdings.length > 0) && restored.market === null && !!restored["api-settings"], "restore changed more than the holdings");
          verify((await root.locator('[data-market-total]').textContent()).includes("NOT_AVAILABLE"), "restore fabricated a valuation without prices");
          verify(await root.locator('[data-security-index="' + selected.USD + '"] [data-field="price"]').inputValue() === "", "restore filled a price");
          // The user re-enters prices and FX; their quote times are kept exactly.
          await enterMarket(); verify(await valuationIs(page, true), "re-entered prices did not value the restored holdings");
          const data = await stored(page); verify(data.market.quotes.every(quote => quote.as_of === CURRENT) && data.market.fx.every(fx => fx.as_of === CURRENT), "quote timestamps changed on save");
        });
        await check(label + ": legacy schema two file restores holdings and drops its prices", async () => {
          await importMemory(page, root, legacyFile);
          const data = await stored(page); verify(!!data.actual && !!data.market && data.market.quotes.length === 0 && data.market.fx.length === 0, "legacy file restored prices or FX");
          verify((await root.locator('[data-market-total]').textContent()).includes("NOT_AVAILABLE"), "legacy restore fabricated quotes");
          await enterMarket(); verify(await valuationIs(page, true), "re-entered prices did not value the restored holdings");
        });
        await check(label + ": missing FX or price blocks total and all denominator values", async () => {
          await root.locator('[data-fx-currency="USD"] [data-field="rate"]').fill(""); await save(page, root);
          verify(await valuationIs(page, false), "missing FX renormalized weights");
          verify((await root.locator('[data-market-total]').textContent()).includes("NOT_AVAILABLE"), "missing FX total fabricated");
          await root.locator('[data-fx-currency="USD"] [data-field="rate"]').fill(VALUES.USD.rate);
          await root.locator('[data-security-index="' + selected.KRW + '"] [data-field="price"]').fill(""); await save(page, root);
          verify(await valuationIs(page, false), "missing price renormalized weights");
          await root.locator('[data-security-index="' + selected.KRW + '"] [data-field="price"]').fill(VALUES.KRW.price); await save(page, root);
        });
        await check(label + ": exact seven day boundary is STALE and preserves known value", async () => {
          const row = root.locator('[data-security-index="' + selected.USD + '"]');
          await row.locator('[data-field="price_as_of"]').fill("2030-01-01T12:00:00.001Z"); await save(page, root);
          verify(!(await row.locator('[data-quote-source]').textContent()).includes("STALE"), "fresh boundary incorrectly stale");
          await row.locator('[data-field="price_as_of"]').fill("2030-01-01T12:00:00.000Z"); await save(page, root);
          verify((await row.locator('[data-quote-source]').textContent()).includes("STALE"), "seven day boundary not stale");
          verify(await valuationIs(page, true), "stale known value discarded");
          verify((await root.locator('.actual-value-list').textContent()).includes("STALE"), "summary provenance omits stale");
        });
        await check(label + ": missing or future price timestamps preserve saved records", async () => {
          const before = await stored(page), row = root.locator('[data-security-index="' + selected.USD + '"]');
          for (const timestamp of ["", "2030-01-09T12:00:00.000Z"]) {
            await row.locator('[data-field="price_as_of"]').fill(timestamp); await root.locator('[data-action="save"]').click();
            await page.waitForFunction(() => document.querySelector('[data-action="save"]')?.disabled === false); await waitNotice(page, root, "invalid");
            verify(JSON.stringify(await stored(page)) === JSON.stringify(before), "invalid timestamp erased saved market");
          }
          await row.locator('[data-field="price_as_of"]').fill("2030-01-01T12:00:00.000Z");
        });
        await check(label + ": transaction abort preserves both records", async () => {
          const before = await stored(page);
          await page.evaluate(() => { window.__originalPut = IDBObjectStore.prototype.put; IDBObjectStore.prototype.put = function (...args) { const request = window.__originalPut.apply(this, args); this.transaction.abort(); return request; }; });
          try { await root.locator('[data-action="save"]').click(); await waitNotice(page, root, "storage"); } finally { await page.evaluate(() => { IDBObjectStore.prototype.put = window.__originalPut; delete window.__originalPut; }); }
          verify(JSON.stringify(await stored(page)) === JSON.stringify(before), "abort partially wrote records");
        });
        await check(label + ": explicit key deletion preserves holdings and market", async () => {
          const before = await stored(page), api = await settings(page); await api.locator('[data-api-action="delete"]').click();
          await page.waitForFunction(() => document.querySelector('[data-api-status]')?.dataset.stored === "no");
          const after = await stored(page); verify(after['api-settings'] === null && JSON.stringify(after.actual) === JSON.stringify(before.actual) && JSON.stringify(after.market) === JSON.stringify(before.market), "key delete changed holdings or market");
          verify(await api.locator('[data-api-refresh]').isDisabled(), "refresh reenabled after key delete"); root = await returnActual(page);
        });
        await check(label + ": legacy backup explicitly clears previous market", async () => {
          const legacy = (await stored(page)).actual; await importMemory(page, root, JSON.stringify(legacy));
          verify((await stored(page)).market === null, "legacy import retained unrelated market");
          verify((await root.locator('[data-market-total]').textContent()).includes("NOT_AVAILABLE"), "legacy restore fabricated quotes");
        });
        await check(label + ": market-only concurrent update blocks stale save and deletion", async () => {
          await importMemory(page, root, legacyFile);
          const before = await stored(page), newer = JSON.parse(JSON.stringify(before.market)); newer.version += 1;
          await putRecord(page, "market", newer);
          await root.locator('[data-action="save"]').click(); await waitNotice(page, root, "storage");
          verify(JSON.stringify((await stored(page)).actual) === JSON.stringify(before.actual) && JSON.stringify((await stored(page)).market) === JSON.stringify(newer), "stale save erased newer market");
          await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await page.waitForFunction(() => document.querySelector('[data-action="save"]')?.disabled === false); });
          verify(JSON.stringify((await stored(page)).actual) === JSON.stringify(before.actual) && JSON.stringify((await stored(page)).market) === JSON.stringify(newer), "stale deletion erased newer market");
        });
        await check(label + ": corrupt market is preserved and only explicit deletion clears it", async () => {
          await page.evaluate(async () => {
            const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
            try { await new Promise(resolve => { const tx = db.transaction("snapshots", "readwrite"), corrupt = { schema: "broken" }; corrupt.self = corrupt; tx.objectStore("snapshots").put(corrupt, "market"); tx.oncomplete = resolve; }); } finally { db.close(); }
          });
          await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
          verify(await root.locator('[data-action="save"]').isDisabled() && await root.locator('[data-action="import"]').isDisabled(), "corrupt market permits overwrite");
          verify(await root.locator('[data-actual-notice]').getAttribute('data-notice') === "corrupt", "corrupt market lacks preservation notice");
          const preserved = await page.evaluate(async () => {
            const db = await new Promise(resolve => { const request = indexedDB.open("investment-device-actual-v1"); request.onsuccess = () => resolve(request.result); });
            try { return await new Promise(resolve => { const request = db.transaction("snapshots", "readonly").objectStore("snapshots").get("market"); request.onsuccess = () => resolve(request.result.self === request.result); }); } finally { db.close(); }
          }); verify(preserved, "corrupt original overwritten");
          await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await waitNotice(page, root, "removed"); });
          const cleared = await stored(page); verify(cleared.actual === null && cleared.market === null, "explicit deletion did not clear corrupt market and actual");
        });
        await check(label + ": stale corrupt editor cannot delete another tab's restored pair", async () => {
          await importMemory(page, root, legacyFile); await corruptClone(page, "market", "cyclic", 1);
          await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
          verify(await root.locator('[data-actual-notice]').getAttribute('data-notice') === "corrupt", "stale editor did not observe corruption");
          const other = await session.context.newPage(); other.on("pageerror", () => { pageErrors++; });
          try {
            const recoveredRoot = await returnActual(other);
            await dialog(other, async () => { await recoveredRoot.locator('[data-action="delete"]').click(); await waitNotice(other, recoveredRoot, "removed"); });
            await importMemory(other, recoveredRoot, legacyFile); const recovered = await stored(other);
            await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await page.waitForFunction(() => document.querySelector('[data-action="delete"]')?.disabled === false); });
            verify(JSON.stringify(await stored(other)) === JSON.stringify(recovered), "stale corrupt editor erased restored pair");
            await waitNotice(page, root, "storage");
          } finally { await other.close(); }
          await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
        });
        await check(label + ": stale corrupt settings cannot delete another tab's saved key", async () => {
          await corruptClone(page, "api-settings", "cyclic", 1); const stale = await settings(page);
          const other = await session.context.newPage(); other.on("pageerror", () => { pageErrors++; });
          try {
            const recovered = await settings(other); await recovered.locator('[data-api-action="delete"]').click();
            await other.waitForFunction(() => document.querySelector('[data-api-notice]')?.dataset.notice === "apiRemoved");
            await recovered.locator('[data-api-key]').fill(KEY); await recovered.locator('[data-api-action="save"]').click();
            await other.waitForFunction(() => document.querySelector('[data-api-status]')?.dataset.stored === "yes");
            const before = await stored(other); await stale.locator('[data-api-action="delete"]').click();
            await page.waitForFunction(() => document.querySelector('[data-api-action="delete"]')?.disabled === false);
            verify(JSON.stringify(await stored(other)) === JSON.stringify(before), "stale corrupt settings erased saved key");
            verify(await stale.locator('[data-api-notice]').getAttribute('data-notice') === "apiStorage", "stale key delete claimed success");
          } finally { await other.close(); }
          root = await returnActual(page);
        });
        for (const kind of ["cyclic", "date", "map", "set", "bigint", "binary", "non-json"]) {
          await check(label + ": unchanged corrupt " + kind + " can clear while changed clone is preserved", async () => {
            await corruptClone(page, "market", kind, 1); await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
            verify(await root.locator('[data-actual-notice]').getAttribute('data-notice') === "corrupt", "clone corruption not detected");
            await corruptClone(page, "market", kind, 2);
            await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await page.waitForFunction(() => document.querySelector('[data-action="delete"]')?.disabled === false); });
            verify(await corruptClone(page, "market", kind, 2, true), "changed corrupt clone erased"); await waitNotice(page, root, "storage");
            await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
            await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await waitNotice(page, root, "removed"); });
            const after = await stored(page); verify(after.actual === null && after.market === null, "unchanged corrupt clone could not clear");
          });
        }
        for (const kind of ["null", "undefined"]) {
          await check(label + ": stored " + kind + " remains distinct from absent and can clear", async () => {
            await corruptClone(page, "market", kind, 1); await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
            verify(await root.locator('[data-actual-notice]').getAttribute('data-notice') === "corrupt", "stored nil treated as absent");
            verify(await corruptClone(page, "market", kind, 1, true), "stored nil was not preserved");
            await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await waitNotice(page, root, "removed"); });
          });
        }
        await check(label + ": opaque clone cleanup preserves bytes instead of trusting metadata", async () => {
          await corruptClone(page, "market", "opaque", 1); await page.reload({ waitUntil: "networkidle" }); await root.locator('[data-security-index]').last().waitFor();
          for (const marker of [1, 2]) {
            if (marker === 2) await corruptClone(page, "market", "opaque", 2);
            await dialog(page, async () => { await root.locator('[data-action="delete"]').click(); await page.waitForFunction(() => document.querySelector('[data-action="delete"]')?.disabled === false); });
            verify(await corruptClone(page, "market", "opaque", marker, true), "opaque bytes erased by metadata comparison"); await waitNotice(page, root, "storage");
          }
        });
      } finally { await session.context.close(); }
      await check(label + ": screenshot uses fresh empty storage and fields", async () => {
        const empty = await open(locale, width);
        try {
          const data = await stored(empty.page); verify(Object.values(data).every(value => value === null), "screenshot storage populated");
          verify(await empty.root.locator('[data-field="quantity"], [data-field="average_cost"], [data-field="price"], [data-field="rate"]').evaluateAll(nodes => nodes.every(node => node.value === "")), "screenshot fields populated");
          const filename = "manual-empty-" + width + "-" + locale + ".png"; await empty.page.screenshot({ path: path.join(evidence, filename), fullPage: false }); screenshots.push(filename);
        } finally { await empty.context.close(); }
      });
    }
    await check("privacy: no external traffic, request bodies, POST or console canaries", async () => verify(Object.values(network).every(count => count === 0), "privacy count nonzero"));
    await check("runtime: no unhandled page errors", async () => verify(pageErrors === 0, "runtime errors"));
    fs.writeFileSync(path.join(evidence, "manual-quotes-browser.json"), JSON.stringify({ passed: true, checks, network, page_error_count: pageErrors, screenshots, screenshot_state: "DEVICE_EMPTY", payload_files_written: 0 }, null, 2) + "\n");
  } catch (error) {
    fs.writeFileSync(path.join(evidence, "manual-quotes-browser.json"), JSON.stringify({ passed: false, failed_check: currentCheck, failure_reason: error.safeReason || "browser interaction failed (details redacted)", checks, network, page_error_count: pageErrors, screenshots, payload_files_written: 0 }, null, 2) + "\n");
    console.error("FAIL " + currentCheck + ": " + (error.safeReason || "browser interaction failed (details redacted)")); process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
}
main();
