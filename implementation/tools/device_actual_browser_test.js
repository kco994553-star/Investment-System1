// Device-local ACTUAL browser checks. Synthetic positions stay in memory only.
// No screenshots, download artifacts, populated fixture files, or payload logs.
"use strict";

const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

const URL_UNDER_TEST = process.env.DEVICE_ACTUAL_URL || "http://127.0.0.1:8765/web-mvp-demo/#actual";
const EVIDENCE_DIR = path.resolve(process.env.DEVICE_ACTUAL_EVIDENCE_DIR || "/workspace/device-actual-module-evidence");
const DB_NAME = "investment-device-actual-v1";
const STORE_NAME = "snapshots";
const SETTINGS_KEY = "investment.web.v1.settings";
const CORRUPTION_ONLY = process.env.DEVICE_ACTUAL_CORRUPTION_ONLY === "1";
const CORRUPT_KINDS = process.env.DEVICE_ACTUAL_CORRUPT_KIND
  ? [process.env.DEVICE_ACTUAL_CORRUPT_KIND] : ["circular", "bigint"];
const QUANTITY = "19.875123";
const AVERAGE_COST = "347.9127";
const REPLACEMENT_QUANTITY = "23.625321";
const CANARIES = [QUANTITY, AVERAGE_COST, REPLACEMENT_QUANTITY];

function requireCheck(value, label) {
  // Do not let an assertion library include actual portfolio data in its error.
  if (!value) {
    const error = new Error(label);
    error.safeReason = label;
    throw error;
  }
}

async function readStored(page) {
  return page.evaluate(async ([dbName, storeName]) => {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open(dbName);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    try {
      if (!db.objectStoreNames.contains(storeName)) return null;
      return await new Promise((resolve, reject) => {
        const request = db.transaction(storeName, "readonly").objectStore(storeName).get("actual");
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    } finally { db.close(); }
  }, [DB_NAME, STORE_NAME]);
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}

function checkNormalizedImport(stored, imported, prior, started, ended) {
  requireCheck(!!stored, "import did not persist an ACTUAL snapshot");
  const preserved = (snapshot) => {
    const copy = { ...snapshot };
    delete copy.version;
    delete copy.available_at;
    return JSON.stringify(canonical(copy));
  };
  requireCheck(preserved(stored) === preserved(imported), "import changed effective time or holdings inputs");
  requireCheck(stored.version === (prior ? Math.max(imported.version, prior.version + 1) : imported.version),
    "import did not normalize the stored revision");
  const available = Date.parse(stored.available_at);
  requireCheck(Number.isFinite(available) && available >= started && available <= ended,
    "import availability does not reflect the local import time");
}

async function storedEquals(page, expected) {
  const stored = await readStored(page);
  return JSON.stringify(canonical(stored)) === JSON.stringify(canonical(expected));
}

async function waitStored(page, predicate) {
  const deadline = Date.now() + 5000;
  do {
    if (predicate(await readStored(page))) return;
    await page.waitForTimeout(40);
  } while (Date.now() < deadline);
  requireCheck(false, "stored snapshot did not reach the expected state");
}

async function withDialog(page, accept, operation) {
  let count = 0;
  const listener = async (dialog) => {
    count += 1;
    if (accept) await dialog.accept(); else await dialog.dismiss();
  };
  page.on("dialog", listener);
  try { await operation(); } finally { page.off("dialog", listener); }
  return count;
}

async function importBytes(root, bytes) {
  await root.locator('[data-action="import"]').setInputFiles({
    name: "synthetic-device-actual.json",
    mimeType: "application/json",
    buffer: Buffer.from(bytes, "utf8"),
  });
}

async function corruptRecord(page, action, kind = "circular") {
  // The deliberately corrupt circular object never crosses the browser boundary.
  return page.evaluate(async ([dbName, storeName, action, kind]) => {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open(dbName);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    try {
      if (action === "inject") {
        await new Promise((resolve, reject) => {
          const tx = db.transaction(storeName, "readwrite");
          const value = { schema: "broken" };
          if (kind === "bigint") value.value = 1n; else value.self = value;
          tx.objectStore(storeName).put(value, "actual");
          tx.oncomplete = resolve;
          tx.onabort = tx.onerror = () => reject(tx.error);
        });
        return true;
      }
      const value = await new Promise((resolve, reject) => {
        const request = db.transaction(storeName, "readonly").objectStore(storeName).get("actual");
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      return action === "empty" ? value === undefined : !!value && value.schema === "broken" &&
        (kind === "bigint" ? value.value === 1n : value.self === value);
    } finally { db.close(); }
  }, [DB_NAME, STORE_NAME, action, kind]);
}

async function main() {
  const checks = [];
  const network = { post_attempts: 0, canary_attempts: 0, body_attempts: 0 };
  let pageErrors = 0;
  let currentCheck = "browser launch";
  let browser;

  async function check(name, operation) {
    currentCheck = name;
    await operation();
    checks.push(name);
    console.log("PASS " + name);
  }

  async function openPage(locale, blockedStorage = false) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale });
    await context.addInitScript(({ key, locale, blockedStorage }) => {
      try { localStorage.setItem(key, JSON.stringify({ version: 1, display_locale: locale, source_language: "all" })); }
      catch (_) { /* Preference storage is independent of portfolio persistence. */ }

      // An export is captured as a local Blob and never becomes a download file.
      const blobs = new Map();
      const createObjectURL = URL.createObjectURL.bind(URL);
      const revokeObjectURL = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = (blob) => {
        const url = createObjectURL(blob);
        blobs.set(url, blob);
        return url;
      };
      URL.revokeObjectURL = (url) => revokeObjectURL(url);
      window.__deviceActualExports = [];
      function capture(anchor) {
        const blob = blobs.get(anchor.href);
        if (!(blob instanceof Blob) || !anchor.download) return false;
        window.__deviceActualExports.push(blob.text());
        return true;
      }
      const anchorClick = HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click = function () {
        if (!capture(this)) anchorClick.call(this);
      };
      document.addEventListener("click", (event) => {
        const anchor = event.target instanceof Element ? event.target.closest("a[download]") : null;
        if (anchor && capture(anchor)) { event.preventDefault(); event.stopImmediatePropagation(); }
      }, true);

      if (blockedStorage) {
        Object.defineProperty(IDBFactory.prototype, "open", {
          configurable: true,
          value() { throw new DOMException("Synthetic browser storage denial", "SecurityError"); },
        });
      }
    }, { key: SETTINGS_KEY, locale, blockedStorage });

    // Record counts only. Request URLs and request bodies never enter evidence.
    await context.route("**/*", async (route) => {
      const request = route.request();
      const url = request.url();
      const body = request.postData() || "";
      const post = request.method() === "POST";
      const carriesCanary = CANARIES.some((value) => url.includes(value) || url.includes(encodeURIComponent(value)) || body.includes(value));
      const carriesBody = !["GET", "HEAD"].includes(request.method()) && body.length > 0;
      if (post) network.post_attempts += 1;
      if (carriesCanary) network.canary_attempts += 1;
      if (carriesBody) network.body_attempts += 1;
      if (post || carriesCanary || carriesBody) await route.abort();
      else await route.continue();
    });

    const page = await context.newPage();
    page.on("pageerror", () => { pageErrors += 1; });
    await page.goto(URL_UNDER_TEST, { waitUntil: "networkidle" });
    const apiPresent = await page.evaluate(() => !!window.DeviceActual && typeof window.DeviceActual.mount === "function");
    requireCheck(apiPresent, "DeviceActual public API is missing");
    const root = page.locator(".device-actual").filter({ has: page.locator('[data-action="save"]') }).first();
    await root.waitFor({ state: "visible" });
    await root.locator("[data-actual-status]").waitFor();
    return { context, page, root };
  }

  async function statusIncludes(root, code) {
    const expected = code === "ACTUAL"
      ? /^ACTUAL · (?:이 기기에만 저장됨|Stored only on this device)$/
      : code;
    await root.locator("[data-actual-status]").filter({ hasText: expected }).waitFor();
  }

  async function exportMemory(page, root) {
    const before = await page.evaluate(() => window.__deviceActualExports.length);
    await root.locator('[data-action="export"]').click();
    await page.waitForFunction((count) => window.__deviceActualExports.length > count, before);
    return page.evaluate(async (index) => await window.__deviceActualExports[index], before);
  }

  async function noticeSettled(page, root, before) {
    await page.waitForFunction(({ before }) => {
      const notice = document.querySelector(".device-actual:not(.actual-compact) [data-actual-notice]");
      return !!notice && notice.textContent.trim().length > 0 && notice.textContent !== before;
    }, { before });
  }

  async function waitIdle(root, action = "save") {
    await root.locator(`[data-action="${action}"]`).evaluate(async (button) => {
      const deadline = Date.now() + 5000;
      while (button.disabled && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 20));
      if (button.disabled) throw new Error("operation did not settle");
    });
  }

  try {
    const launch = { headless: true };
    if (process.env.WEB_TEST_CHROMIUM_PATH) launch.executablePath = process.env.WEB_TEST_CHROMIUM_PATH;
    browser = await chromium.launch(launch);

    for (const locale of ["ko-KR", "en-US"]) {
      if (!CORRUPTION_ONLY) {
      let opened;
      await check(`${locale}: public API and mobile empty ACTUAL`, async () => {
        opened = await openPage(locale);
        const { page, root } = opened;
        await statusIncludes(root, "NOT_AVAILABLE");
        requireCheck((await readStored(page)) === null, "fresh context must have no ACTUAL snapshot");
        requireCheck(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "390px layout overflow");
        requireCheck(await root.locator("[data-security-index]").count() > 0, "manual form is missing");
        requireCheck(await page.locator("html").getAttribute("lang") === locale, "display locale did not apply");
        const english = locale === "en-US";
        requireCheck(await root.getByRole("heading", { name: english ? "My actual holdings · ACTUAL" : "내 실제 보유 · ACTUAL", exact: true }).count() === 1,
          "ACTUAL heading did not use the display locale");
        requireCheck(await root.getByRole("button", { name: english ? "Save on this device" : "이 기기에 저장", exact: true }).count() === 1,
          "manual save label did not use the display locale");
        requireCheck(await root.locator('[data-action="export"]').isDisabled(), "empty ACTUAL can be exported");
      });

      const { context, page, root } = opened;
      try {
        let exported;
        let original;
        await check(`${locale}: manual save persists only in IndexedDB after refresh`, async () => {
          const row = root.locator("[data-security-index]").first();
          await row.locator('[data-field="quantity"]').fill(QUANTITY);
          await row.locator('[data-field="average_cost"]').fill(AVERAGE_COST);
          await root.locator('[data-action="save"]').click();
          await statusIncludes(root, "ACTUAL");
          await waitStored(page, (snapshot) => !!snapshot && snapshot.themes?.some((theme) => theme.holdings.length > 0));
          original = await readStored(page);
          await page.reload({ waitUntil: "networkidle" });
          await statusIncludes(root, "ACTUAL");
          requireCheck(await storedEquals(page, original), "refresh changed the stored snapshot");
          requireCheck(await row.locator('[data-field="quantity"]').inputValue() === QUANTITY, "quantity did not survive refresh");
          requireCheck(await row.locator('[data-field="average_cost"]').inputValue() === AVERAGE_COST, "average cost did not survive refresh");
          requireCheck(await page.evaluate(() => {
            const keys = Object.keys(localStorage);
            return !keys.some((key) => /device.*actual|actual.*portfolio/i.test(key)) &&
              !keys.some((key) => /positions|average_cost/.test(localStorage.getItem(key) || ""));
          }), "portfolio data leaked into localStorage");
        });

        await check(`${locale}: export is a local Blob kept entirely in memory`, async () => {
          exported = await exportMemory(page, root);
          const payload = JSON.parse(exported);
          requireCheck(JSON.stringify(canonical(payload)) === JSON.stringify(canonical(original)), "export differs from the saved envelope");
          requireCheck(payload.schema === "device-actual-holdings/1" && payload.kind === "ACTUAL" &&
            payload.ownership === "USER_DEVICE_ONLY" && typeof payload.version === "number" &&
            Array.isArray(payload.themes) && payload.themes.some((theme) => theme.holdings.length > 0), "export envelope is malformed");
        });

        for (const fault of ["quota", "abort"]) {
        await check(`${locale}: ${fault === "quota" ? "quota failures" : "transaction aborts after put"} preserve ACTUAL and never claim save or import success`, async () => {
          const newer = JSON.parse(exported);
          newer.version += 1;
          newer.themes.find((theme) => theme.holdings.length > 0).holdings[0].quantity = REPLACEMENT_QUANTITY;
          await page.evaluate((fault) => {
            window.__deviceActualOriginalPut = IDBObjectStore.prototype.put;
            IDBObjectStore.prototype.put = function (...args) {
              if (fault === "quota") throw new DOMException("Synthetic quota denial", "QuotaExceededError");
              const request = window.__deviceActualOriginalPut.apply(this, args);
              this.transaction.abort();
              return request;
            };
          }, fault);
          let manualPreserved = false;
          let manualStorageNotice = false;
          let importPreserved = false;
          let importStorageNotice = false;
          try {
            const row = root.locator("[data-security-index]").first();
            await row.locator('[data-field="quantity"]').fill(REPLACEMENT_QUANTITY);
            await root.locator('[data-action="save"]').click();
            await waitIdle(root);
            manualPreserved = await storedEquals(page, original);
            manualStorageNotice = await root.locator("[data-actual-notice]").getAttribute("data-notice") === "storage";
            await withDialog(page, true, async () => {
              await importBytes(root, JSON.stringify(newer));
              await waitIdle(root);
            });
            importPreserved = await storedEquals(page, original);
            importStorageNotice = await root.locator("[data-actual-notice]").getAttribute("data-notice") === "storage";
          } finally {
            await page.evaluate(() => {
              IDBObjectStore.prototype.put = window.__deviceActualOriginalPut;
              delete window.__deviceActualOriginalPut;
            });
          }
          requireCheck(manualPreserved && manualStorageNotice, "manual storage failure changed ACTUAL or claimed success");
          requireCheck(importPreserved && importStorageNotice, "import storage failure changed ACTUAL or claimed success");
          await page.reload({ waitUntil: "networkidle" });
          await statusIncludes(root, "ACTUAL");
          requireCheck(await storedEquals(page, original), "storage failure changed persisted ACTUAL after refresh");
        });
        }

        await check(`${locale}: missing quotes preserve unavailable valuation and TARGET deltas`, async () => {
          const unavailable = await page.evaluate(async (snapshot) => {
            const response = await fetch(new URL("actual-catalog.json", location.href));
            if (!response.ok) return false;
            const catalog = await response.json();
            const result = DeviceActual.valuation(snapshot, catalog, []);
            return result.state === "NOT_AVAILABLE" && result.reason === "MISSING_QUOTES" && result.total === null &&
              result.rows.length > 0 && result.rows.every((row) => row.market_value === null && row.weight === null && row.delta === null) &&
              result.themes.every((theme) => theme.market_value === null && theme.weight === null && theme.delta === null);
          }, original);
          requireCheck(unavailable, "average cost or TARGET was substituted for a missing market quote");
          requireCheck((await root.locator("[data-market-total]").textContent()).includes("NOT_AVAILABLE"), "missing total valuation is not labelled unavailable");
          const cells = root.locator(".actual-value-row").first().locator("dd");
          for (const index of [2, 4, 5]) {
            requireCheck(await cells.nth(index).textContent() === "NOT_AVAILABLE", "missing market value, weight, or delta is displayed as a value");
          }
        });

        await check(`${locale}: zero quantity still requires a valid quote before market value is shown`, async () => {
          const correct = await page.evaluate(async () => {
            const response = await fetch(new URL("actual-catalog.json", location.href));
            if (!response.ok) return false;
            const catalog = await response.json();
            const instrument = catalog.instruments[0];
            const row = { security_reference: instrument.security_reference, quantity: "0", average_cost: "0", currency: instrument.currency };
            const snapshot = DeviceActual.makeSnapshot(catalog, [row]);
            const withoutQuote = DeviceActual.valuation(snapshot, catalog, []);
            const now = new Date().toISOString();
            const withQuote = DeviceActual.valuation(snapshot, catalog, [{ security_reference: instrument.security_reference,
              price: "1", currency: instrument.currency, as_of: now, available_at: now }]);
            return withoutQuote.rows.length === 1 && withoutQuote.rows[0].market_value === null &&
              withoutQuote.total === null && withoutQuote.rows[0].weight === null && withoutQuote.rows[0].delta === null &&
              withQuote.rows[0].market_value === 0 && withQuote.state === "NOT_AVAILABLE" &&
              withQuote.rows[0].weight === null && withQuote.rows[0].delta === null;
          });
          requireCheck(correct, "zero quantity displayed a market value without a valid quote");
        });

        await check(`${locale}: invalid imports preserve the existing snapshot`, async () => {
          const invalid = JSON.parse(exported);
          invalid.target_root_sha256 = "invalid-target-root";
          for (const bytes of ["{", JSON.stringify(invalid)]) {
            const before = await root.locator("[data-actual-notice]").textContent();
            await importBytes(root, bytes);
            await noticeSettled(page, root, before);
            requireCheck(await storedEquals(page, original), "invalid import replaced the saved snapshot");
            await statusIncludes(root, "ACTUAL");
          }
        });

        let replacement;
        let replacementStored;
        await check(`${locale}: overwrite confirmation cancel preserves ACTUAL`, async () => {
          replacement = JSON.parse(exported);
          replacement.version += 1;
          replacement.effective_at = new Date().toISOString();
          replacement.available_at = replacement.effective_at;
          replacement.themes.find((theme) => theme.holdings.length > 0).holdings[0].quantity = REPLACEMENT_QUANTITY;
          const count = await withDialog(page, false, async () => {
            const before = await root.locator("[data-actual-notice]").textContent();
            await importBytes(root, JSON.stringify(replacement));
            await noticeSettled(page, root, before);
          });
          requireCheck(count === 1, "overwrite did not request exactly one confirmation");
          requireCheck(await storedEquals(page, original), "cancelled overwrite changed ACTUAL");
        });

        await check(`${locale}: accepted overwrite replaces ACTUAL and survives refresh`, async () => {
          const started = Date.now();
          const count = await withDialog(page, true, async () => {
            await importBytes(root, JSON.stringify(replacement));
            await waitStored(page, (snapshot) => snapshot?.version === replacement.version);
          });
          requireCheck(count === 1, "overwrite confirmation is missing");
          replacementStored = await readStored(page);
          checkNormalizedImport(replacementStored, replacement, original, started, Date.now());
          await page.reload({ waitUntil: "networkidle" });
          await statusIncludes(root, "ACTUAL");
          requireCheck(await storedEquals(page, replacementStored), "import did not survive refresh");
        });

        for (const backupAge of ["older", "same-version"]) {
        await check(`${locale}: ${backupAge} backup cancellation preserves ACTUAL and confirmed restore advances revision`, async () => {
          const backup = JSON.parse(exported);
          if (backupAge === "same-version") backup.version = replacementStored.version;
          const before = replacementStored;
          const canceledCount = await withDialog(page, false, async () => {
            const noticeBefore = await root.locator("[data-actual-notice]").textContent();
            await importBytes(root, JSON.stringify(backup));
            await noticeSettled(page, root, noticeBefore);
          });
          requireCheck(canceledCount === 1, "backup restore confirmation is missing");
          requireCheck(await storedEquals(page, before), "cancelled backup restore changed ACTUAL");
          const started = Date.now();
          const acceptedCount = await withDialog(page, true, async () => {
            await importBytes(root, JSON.stringify(backup));
            await waitStored(page, (snapshot) => snapshot?.version === before.version + 1);
          });
          requireCheck(acceptedCount === 1, "backup restore confirmation is missing");
          replacementStored = await readStored(page);
          checkNormalizedImport(replacementStored, backup, before, started, Date.now());
          await page.reload({ waitUntil: "networkidle" });
          await statusIncludes(root, "ACTUAL");
          requireCheck(await storedEquals(page, replacementStored), "restored backup did not survive refresh");
        });
        }

        await check(`${locale}: deletion cancel preserves ACTUAL`, async () => {
          const count = await withDialog(page, false, async () => {
            await root.locator('[data-action="delete"]').click();
          });
          requireCheck(count === 1, "delete confirmation is missing");
          requireCheck(await storedEquals(page, replacementStored), "cancelled deletion changed ACTUAL");
        });

        await check(`${locale}: delete clears IndexedDB and remains empty after refresh`, async () => {
          const count = await withDialog(page, true, async () => {
            await root.locator('[data-action="delete"]').click();
            await waitStored(page, (snapshot) => snapshot === null);
          });
          requireCheck(count === 1, "delete confirmation is missing");
          await page.reload({ waitUntil: "networkidle" });
          await statusIncludes(root, "NOT_AVAILABLE");
          requireCheck((await readStored(page)) === null, "deleted ACTUAL returned after refresh");
        });

        await check(`${locale}: in-memory exported file restores an empty browser`, async () => {
          const started = Date.now();
          await withDialog(page, true, async () => {
            await importBytes(root, exported);
            await waitStored(page, (snapshot) => snapshot?.version === original.version);
          });
          await statusIncludes(root, "ACTUAL");
          const restored = await readStored(page);
          checkNormalizedImport(restored, original, null, started, Date.now());
          await page.reload({ waitUntil: "networkidle" });
          await statusIncludes(root, "ACTUAL");
          requireCheck(await storedEquals(page, restored), "round-trip import did not survive refresh");
          await withDialog(page, true, async () => {
            await root.locator('[data-action="delete"]').click();
            await waitStored(page, (snapshot) => snapshot === null);
          });
        });
      } finally { await context.close(); }

      await check(`${locale}: blocked IndexedDB fails closed`, async () => {
        const blocked = await openPage(locale, true);
        try {
          await statusIncludes(blocked.root, "NOT_AVAILABLE");
          requireCheck((await blocked.root.locator("[data-actual-notice]").textContent()).trim().length > 0, "storage denial has no user notice");
          const save = blocked.root.locator('[data-action="save"]');
          if (!(await save.isDisabled())) {
            const row = blocked.root.locator("[data-security-index]").first();
            await row.locator('[data-field="quantity"]').fill(QUANTITY);
            await row.locator('[data-field="average_cost"]').fill(AVERAGE_COST);
            await save.click();
            await statusIncludes(blocked.root, "NOT_AVAILABLE");
          }
          await blocked.page.reload({ waitUntil: "networkidle" });
          await statusIncludes(blocked.root, "NOT_AVAILABLE");
        } finally { await blocked.context.close(); }
      });

      await check(`${locale}: stale second editor cannot overwrite a newer ACTUAL snapshot`, async () => {
        const active = await openPage(locale);
        try {
          const firstRow = active.root.locator("[data-security-index]").first();
          await firstRow.locator('[data-field="quantity"]').fill(QUANTITY);
          await firstRow.locator('[data-field="average_cost"]').fill(AVERAGE_COST);
          await active.root.locator('[data-action="save"]').click();
          await waitIdle(active.root);
          const before = await readStored(active.page);
          requireCheck(before?.version === 1, "first editor did not create the initial snapshot");

          const stalePage = await active.context.newPage();
          stalePage.on("pageerror", () => { pageErrors += 1; });
          await stalePage.goto(URL_UNDER_TEST, { waitUntil: "networkidle" });
          const staleRoot = stalePage.locator(".device-actual").filter({ has: stalePage.locator('[data-action="save"]') }).first();
          await staleRoot.waitFor();
          await statusIncludes(staleRoot, "ACTUAL");

          await firstRow.locator('[data-field="quantity"]').fill(REPLACEMENT_QUANTITY);
          await active.root.locator('[data-action="save"]').click();
          await waitIdle(active.root);
          const current = await readStored(active.page);
          requireCheck(current?.version === before.version + 1, "first editor did not commit the newer snapshot");

          await staleRoot.locator('[data-action="save"]').click();
          await waitIdle(staleRoot);
          requireCheck(await staleRoot.locator("[data-actual-notice]").getAttribute("data-notice") === "storage", "stale editor claimed successful storage");
          requireCheck(await storedEquals(active.page, current), "stale editor replaced newer ACTUAL");
          await active.page.reload({ waitUntil: "networkidle" });
          await statusIncludes(active.root, "ACTUAL");
          requireCheck(await storedEquals(active.page, current), "newer ACTUAL did not survive the editor conflict and refresh");
        } finally { await active.context.close(); }
      });
      }

      for (const kind of CORRUPT_KINDS) {
      requireCheck(["circular", "bigint"].includes(kind), "unsupported corrupt-record test kind");
      await check(`${locale}: corrupt ${kind} record stays preserved until explicit deletion`, async () => {
        const corrupt = await openPage(locale);
        try {
          await corruptRecord(corrupt.page, "inject", kind);
          await corrupt.page.reload({ waitUntil: "networkidle" });
          await statusIncludes(corrupt.root, "NOT_AVAILABLE");
          requireCheck(await corruptRecord(corrupt.page, "preserved", kind), "corrupt raw record was overwritten during load");
          requireCheck(await corrupt.root.locator('[data-action="save"]').isDisabled(), "corrupt data permits a manual overwrite");
          requireCheck(await corrupt.root.locator('[data-action="import"]').isDisabled(), "corrupt data permits an import overwrite");
          requireCheck(await corrupt.root.locator("[data-actual-notice]").getAttribute("data-notice") === "corrupt", "corruption has no explicit preservation notice");
          const count = await withDialog(corrupt.page, true, async () => {
            await corrupt.root.locator('[data-action="delete"]').click();
            await waitIdle(corrupt.root, "delete");
          });
          requireCheck(count === 1, "corrupt-record deletion confirmation is missing");
          requireCheck(await corruptRecord(corrupt.page, "empty", kind), "explicit deletion did not remove the corrupt record");
          await corrupt.page.reload({ waitUntil: "networkidle" });
          await statusIncludes(corrupt.root, "NOT_AVAILABLE");
          requireCheck(await corruptRecord(corrupt.page, "empty", kind), "deleted corrupt record returned after refresh");
          requireCheck(!(await corrupt.root.locator('[data-action="save"]').isDisabled()), "manual entry stays blocked after corrupt-record deletion");
        } finally { await corrupt.context.close(); }
      });
      }
    }

    await check("privacy: no POST, request body, or synthetic positions leave the browser", async () => {
      requireCheck(network.post_attempts === 0 && network.body_attempts === 0 && network.canary_attempts === 0,
        "a portfolio upload or network disclosure was attempted");
    });
    await check("runtime: no unhandled page errors", async () => requireCheck(pageErrors === 0, "unhandled page error"));

    fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    fs.writeFileSync(path.join(EVIDENCE_DIR, "device-actual-browser.json"), JSON.stringify({
      passed: true, viewport: { width: 390, height: 844 }, checks, network,
      page_error_count: pageErrors, screenshots: 0, payload_files_written: 0,
    }, null, 2) + "\n");
  } catch (error) {
    // Playwright errors can include input/DOM content. Persist only the check name.
    fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    fs.writeFileSync(path.join(EVIDENCE_DIR, "device-actual-browser.json"), JSON.stringify({
      passed: false, failed_check: currentCheck, failure_reason: error.safeReason || "browser interaction failed (details redacted)", checks, network,
      page_error_count: pageErrors, screenshots: 0, payload_files_written: 0,
    }, null, 2) + "\n");
    console.error("FAIL " + currentCheck + ": " + (error.safeReason || "browser interaction failed (details redacted)"));
    process.exitCode = 1;
  } finally { if (browser) await browser.close(); }
}

main();
